from typing import Annotated

from fastapi import Depends

from database import UnitOfWork
from enums.lobby import LobbyStateEnum
from enums.prompt import PromptCategoryKindEnum
from errors.request import BadRequestError, NotFoundError
from schemas.lobby.base import LobbyFilterSchema, LobbyInDBSchema, LobbyUpdateSchema
from schemas.lobby.nested import (
    LobbyActiveListItemSchema,
    LobbyDetailsSchema,
    LobbyMineListItemSchema,
    LobbyWithCategoriesInDBSchema,
    PaginatedLobbyWithCategoriesInDBSchema,
)
from schemas.user.base import UserPublicSchema
from services import game_timers
from services.game_state_materializer import GameStateMaterializer
from sockets.lobby_lifecycle import notify_lobbies_changed, notify_lobby_deleted_and_disconnect
from utils.lobby import (
    build_lobby_rounds,
    ensure_owned_lobby,
    get_player_count,
    rank_final_scores,
    validate_lifecycle_transition,
    validate_lobby_categories_for_start,
    validate_rounds,
)


class LobbyService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def search_lobbies(
        self,
        filters: LobbyFilterSchema,
        user: UserPublicSchema,
    ) -> PaginatedLobbyWithCategoriesInDBSchema:
        async with self._uow as uow:
            result = await uow.lobby_repo.search_lobbies(filters=filters, user_id=user.id)
            contents: list[LobbyWithCategoriesInDBSchema] = []
            for lobby in result.contents:
                player_count = await get_player_count(uow, lobby.id, lobby.state)
                contents.append(lobby.model_copy(update={"player_count": player_count}))
            return result.model_copy(update={"contents": contents})

    async def get_active_lobbies(self, user: UserPublicSchema) -> list[LobbyActiveListItemSchema]:
        async with self._uow as uow:
            return await uow.lobby_repo.select_active_lobbies(user_id=user.id)

    async def get_my_lobbies(self, user: UserPublicSchema) -> list[LobbyMineListItemSchema]:
        async with self._uow as uow:
            return await uow.lobby_repo.select_my_lobbies(user_id=user.id)

    async def get_lobby(
        self,
        lobby_id: int,
        user: UserPublicSchema,
    ) -> LobbyDetailsSchema:
        async with self._uow as uow:
            lobby = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
            if lobby is None:
                raise NotFoundError(f"Lobby {lobby_id} not found")

            is_owner = lobby.owner_id == user.id
            participant = await uow.lobby_repo.select_participant(
                lobby_id=lobby_id,
                user_id=user.id,
            )
            is_participant = participant is not None and not participant.is_banned

            if lobby.state == LobbyStateEnum.CREATED and not is_owner:
                raise NotFoundError(f"Lobby {lobby_id} not found")
            if lobby.state == LobbyStateEnum.COMPLETED and not (is_owner or is_participant):
                raise NotFoundError(f"Lobby {lobby_id} not found")

            player_count = await get_player_count(uow, lobby.id, lobby.state)
            final_rankings = None
            if lobby.state == LobbyStateEnum.COMPLETED:
                final_rankings = rank_final_scores(
                    await uow.lobby_repo.select_final_rankings(lobby_id),
                )
            category_rounds = await uow.lobby_repo.select_category_rounds(lobby_id)
            round_results = (
                await uow.lobby_repo.select_round_results(lobby_id)
                if lobby.state == LobbyStateEnum.COMPLETED
                else None
            )

        return LobbyDetailsSchema.model_validate(
            lobby.model_dump()
            | {
                "player_count": player_count,
                "is_owner": is_owner,
                "is_participant": is_participant,
                "final_rankings": final_rankings,
                "rounds": build_lobby_rounds(
                    lobby.prompt_categories,
                    category_rounds,
                    round_results,
                ),
            },
        )

    async def create_lobby(self, owner_id: int) -> LobbyInDBSchema:
        async with self._uow as uow:
            lobby = await uow.lobby_repo.insert_lobby(owner_id=owner_id)
        await notify_lobbies_changed()
        return lobby

    async def update_lobby(
        self,
        lobby_id: int,
        user: UserPublicSchema,
        schema: LobbyUpdateSchema,
    ) -> LobbyWithCategoriesInDBSchema:
        async with self._uow as uow:
            lobby = await ensure_owned_lobby(uow, lobby_id, user)

            if "betting_prompt_count" in schema.model_fields_set:
                if lobby.state != LobbyStateEnum.CREATED:
                    raise BadRequestError(
                        "Betting prompts can only be modified while the lobby "
                        "is in the CREATED state",
                    )
                await uow.lobby_repo.update_betting_prompt_count(
                    lobby_id,
                    schema.betting_prompt_count,
                )

            if schema.rounds is not None or "final_category_id" in schema.model_fields_set:
                if lobby.state != LobbyStateEnum.CREATED:
                    raise BadRequestError(
                        "Prompt categories can only be modified while the lobby "
                        "is in the CREATED state",
                    )
                category_rounds = await uow.lobby_repo.select_category_rounds(lobby_id)
                current_rounds: dict[int, list[int]] = {}
                final_category_id = None
                for category in lobby.prompt_categories:
                    if category.kind == PromptCategoryKindEnum.FINAL:
                        final_category_id = category.id
                    else:
                        current_rounds.setdefault(
                            category_rounds.get(category.id, 1),
                            [],
                        ).append(category.id)
                if "final_category_id" in schema.model_fields_set:
                    final_category_id = schema.final_category_id
                rounds = await validate_rounds(
                    uow,
                    (
                        schema.rounds
                        if schema.rounds is not None
                        else [current_rounds[number] for number in sorted(current_rounds)]
                    ),
                    final_category_id,
                )
                await uow.lobby_repo.replace_lobby_categories(
                    lobby_id=lobby_id,
                    rounds=rounds,
                )

            if schema.state is not None:
                validate_lifecycle_transition(
                    current_state=lobby.state,
                    requested_state=schema.state,
                )
                await validate_lobby_categories_for_start(uow, lobby_id)
                await uow.lobby_repo.update_lobby_state(
                    lobby_id=lobby_id,
                    state=schema.state,
                )
                await GameStateMaterializer(uow).materialize(lobby_id)

            updated = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
        await notify_lobbies_changed()
        if updated is None:
            raise NotFoundError(f"Lobby {lobby_id} not found")
        return updated

    async def delete_lobby(
        self,
        lobby_id: int,
        user: UserPublicSchema,
    ) -> None:
        async with self._uow as uow:
            await ensure_owned_lobby(uow, lobby_id, user)
            await uow.lobby_repo.delete_lobby(lobby_id=lobby_id)
            await uow.game_state_repo.delete_state(lobby_id)
        game_timers.cancel(lobby_id)
        await notify_lobby_deleted_and_disconnect(lobby_id)
        await notify_lobbies_changed()
