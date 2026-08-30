from typing import Annotated

from fastapi import Depends

from configs.constants import (
    MAX_CATEGORIES_IN_LOBBY,
    MIN_CATEGORIES_IN_LOBBY,
    NUM_PROMPTS_IN_CATEGORY,
)
from database import UnitOfWork
from enums.lobby import LobbyStateEnum
from errors.request import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
)
from schemas.lobby.base import (
    LobbyFilterSchema,
    LobbyInDBSchema,
    LobbyUpdateSchema,
)
from schemas.lobby.nested import (
    LobbyActiveListItemSchema,
    LobbyDetailsSchema,
    LobbyFinalRankingSchema,
    LobbyMineListItemSchema,
    LobbyWithCategoriesInDBSchema,
    PaginatedLobbyWithCategoriesInDBSchema,
)
from schemas.lobby.participant import LobbyParticipantInDBSchema
from schemas.user.base import UserPublicSchema
from services import game_timers
from services.game import GameService
from sockets.app import sio
from sockets.broadcast import broadcast_lobby_deleted
from sockets.namespace import lobby_namespace


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
                player_count = await self._get_player_count(uow, lobby.id, lobby.state)
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

            player_count = await self._get_player_count(uow, lobby.id, lobby.state)
            final_rankings = None
            if lobby.state == LobbyStateEnum.COMPLETED:
                final_rankings = self._rank_final_scores(
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
            lobby = await self._ensure_owned_lobby(uow, lobby_id, user)

            if schema.prompt_category_ids is not None:
                if lobby.state != LobbyStateEnum.CREATED:
                    raise BadRequestError(
                        "Prompt categories can only be modified while the lobby "
                        "is in the CREATED state",
                    )
                category_ids = await self._validate_category_ids(
                    uow,
                    schema.prompt_category_ids,
                )
                await uow.lobby_repo.replace_lobby_categories(
                    lobby_id=lobby_id,
                    category_ids=category_ids,
                )

            if schema.state is not None:
                await self._validate_lifecycle_transition(
                    current_state=lobby.state,
                    requested_state=schema.state,
                )
                await self._validate_lobby_categories_for_start(uow, lobby_id)
                await uow.lobby_repo.update_lobby_state(
                    lobby_id=lobby_id,
                    state=schema.state,
                )
                await GameService.materialize_state_in_uow(uow, lobby_id)

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
            await self._ensure_owned_lobby(uow, lobby_id, user)
            await uow.lobby_repo.delete_lobby(lobby_id=lobby_id)
            await uow.game_state_repo.delete_state(lobby_id)
        game_timers.cancel(lobby_id)
        await broadcast_lobby_deleted(lobby_id)
        await _disconnect_lobby_sockets(lobby_id)

    @classmethod
    async def _ensure_owned_lobby(
        cls,
        uow: UnitOfWork,
        lobby_id: int,
        user: UserPublicSchema,
    ) -> LobbyWithCategoriesInDBSchema:
        """
        Load a lobby by id and assert it exists and that ``user`` owns it.

        :param uow: active unit of work (already inside ``async with``)
        :param lobby_id: lobby primary key to load
        :param user: authenticated user whose id must match ``owner_id``
        :return: loaded lobby with its prompt categories
        :raises NotFoundError: lobby missing
        :raises ForbiddenError: ``user`` is not the lobby owner
        """
        lobby = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
        if lobby is None:
            raise NotFoundError(f"Lobby {lobby_id} not found")
        if lobby.owner_id != user.id:
            raise ForbiddenError("Only the owner can modify this lobby")
        return lobby

    @classmethod
    async def _validate_category_ids(
        cls,
        uow: UnitOfWork,
        category_ids: list[int],
    ) -> list[int]:
        """
        Validate the proposed prompt category ids for a lobby:

        - deduplicate while preserving caller order
        - enforce ``MIN_CATEGORIES_IN_LOBBY..MAX_CATEGORIES_IN_LOBBY`` bounds
        - verify every id corresponds to an existing ``prompt_category`` row

        :param uow: active unit of work
        :param category_ids: caller-supplied ids
        :return: deduplicated list of ids
        :raises BadRequestError: count outside bounds or unknown ids present
        """
        seen: set[int] = set()
        unique_ids: list[int] = []
        for cid in category_ids:
            if cid not in seen:
                seen.add(cid)
                unique_ids.append(cid)

        if not (MIN_CATEGORIES_IN_LOBBY <= len(unique_ids) <= MAX_CATEGORIES_IN_LOBBY):
            raise BadRequestError(
                f"A lobby must have between {MIN_CATEGORIES_IN_LOBBY} and "
                f"{MAX_CATEGORIES_IN_LOBBY} prompt categories",
            )

        existing = await uow.lobby_repo.select_existing_category_ids(unique_ids)
        missing = sorted(seen - existing)
        if missing:
            raise BadRequestError(f"Prompt categories {missing} do not exist")
        return unique_ids

    @classmethod
    async def _validate_lifecycle_transition(
        cls,
        current_state: LobbyStateEnum,
        requested_state: LobbyStateEnum,
    ) -> None:
        if (
            current_state != LobbyStateEnum.CREATED
            or requested_state != LobbyStateEnum.WAITING_START
        ):
            raise BadRequestError(
                "REST may only transition a lobby from CREATED to WAITING_START",
            )

    @classmethod
    async def _validate_lobby_categories_for_start(
        cls,
        uow: UnitOfWork,
        lobby_id: int,
    ) -> None:
        lobby = await uow.lobby_repo.select_lobby_with_prompts(lobby_id=lobby_id)
        if lobby is None:
            raise NotFoundError(f"Lobby {lobby_id} not found")

        category_count = len(lobby.prompt_categories)
        if not (MIN_CATEGORIES_IN_LOBBY <= category_count <= MAX_CATEGORIES_IN_LOBBY):
            raise BadRequestError(
                f"A lobby must have between {MIN_CATEGORIES_IN_LOBBY} and "
                f"{MAX_CATEGORIES_IN_LOBBY} prompt categories",
            )

        expected_orders = set(range(1, NUM_PROMPTS_IN_CATEGORY + 1))
        incomplete_categories: list[int] = []
        for category in lobby.prompt_categories:
            prompts = category.prompts
            orders = [prompt.order for prompt in prompts]
            has_valid_orders = (
                len(prompts) == NUM_PROMPTS_IN_CATEGORY
                and all(order is not None for order in orders)
                and set(orders) == expected_orders
            )
            if not has_valid_orders:
                incomplete_categories.append(category.id)

        if incomplete_categories:
            raise BadRequestError(
                "Every lobby category must contain exactly five uniquely ordered "
                f"prompts; invalid categories: {incomplete_categories}",
            )

    @classmethod
    async def _get_player_count(
        cls,
        uow: UnitOfWork,
        lobby_id: int,
        lobby_state: LobbyStateEnum,
    ) -> int:
        if lobby_state == LobbyStateEnum.CREATED:
            return 0
        return await uow.lobby_repo.select_eligible_player_count(lobby_id)

    @classmethod
    def _rank_final_scores(
        cls,
        participants: list[LobbyParticipantInDBSchema],
    ) -> list[LobbyFinalRankingSchema]:
        rankings: list[LobbyFinalRankingSchema] = []
        previous_score: int | None = None
        rank = 0
        for index, participant in enumerate(participants, start=1):
            assert participant.final_score is not None
            if participant.final_score != previous_score:
                rank = index
                previous_score = participant.final_score
            rankings.append(
                LobbyFinalRankingSchema(
                    user_id=participant.user_id,
                    username=participant.username_snapshot,
                    final_score=participant.final_score,
                    is_banned=participant.is_banned,
                    rank=rank,
                ),
            )
        return rankings


async def _disconnect_lobby_sockets(lobby_id: int) -> None:
    namespace = lobby_namespace(lobby_id)
    for sid, _ in list(sio.manager.get_participants(namespace, None)):
        await sio.disconnect(sid, namespace=namespace)
