from typing import Annotated

from fastapi import Depends

from database import UnitOfWork
from enums.lobby import LobbyStateEnum
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
from sockets.lobby_lifecycle import notify_lobby_deleted_and_disconnect
from utils.game_state import materialize_game_state
from utils.lobby import (
    ensure_owned_lobby,
    get_player_count,
    rank_final_scores,
    validate_category_ids,
    validate_lifecycle_transition,
    validate_lobby_categories_for_start,
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

        return LobbyDetailsSchema.model_validate(
            lobby.model_dump()
            | {
                "player_count": player_count,
                "is_owner": is_owner,
                "is_participant": is_participant,
                "final_rankings": final_rankings,
            },
        )

    async def create_lobby(self, owner_id: int) -> LobbyInDBSchema:
        async with self._uow as uow:
            return await uow.lobby_repo.insert_lobby(owner_id=owner_id)

    async def update_lobby(
        self,
        lobby_id: int,
        user: UserPublicSchema,
        schema: LobbyUpdateSchema,
    ) -> LobbyWithCategoriesInDBSchema:
        async with self._uow as uow:
            lobby = await ensure_owned_lobby(uow, lobby_id, user)

            if schema.prompt_category_ids is not None:
                if lobby.state != LobbyStateEnum.CREATED:
                    raise BadRequestError(
                        "Prompt categories can only be modified while the lobby "
                        "is in the CREATED state",
                    )
                category_ids = await validate_category_ids(
                    uow,
                    schema.prompt_category_ids,
                )
                await uow.lobby_repo.replace_lobby_categories(
                    lobby_id=lobby_id,
                    category_ids=category_ids,
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
                await materialize_game_state(uow, lobby_id)

            updated = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
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
