from typing import Annotated

from fastapi import Depends

from configs.constants import (
    MAX_CATEGORIES_IN_LOBBY,
    MIN_CATEGORIES_IN_LOBBY,
    NUM_PROMPTS_IN_CATEGORY,
)
from database import UnitOfWork
from enums.lobby import LobbyStateEnum
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
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
    LobbyWithCategoriesInDBSchema,
    PaginatedLobbyWithCategoriesInDBSchema,
)
from schemas.user.base import UserPublicSchema
from services.game import GameService


class LobbyService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def search_lobbies(
        self,
        filters: LobbyFilterSchema,
    ) -> PaginatedLobbyWithCategoriesInDBSchema:
        async with self._uow as uow:
            return await uow.lobby_repo.search_lobbies(filters=filters)

    async def get_lobby(self, lobby_id: int) -> LobbyWithCategoriesInDBSchema:
        async with self._uow as uow:
            lobby = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
        if lobby is None:
            raise NotFoundError(f"Lobby {lobby_id} not found")
        return lobby

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
            lobby = await self._ensure_owned_lobby(uow, lobby_id, user)
            if lobby.state != LobbyStateEnum.CREATED:
                raise BadRequestError(
                    "Only lobbies in the CREATED state can be deleted",
                )
            await uow.lobby_repo.delete_lobby(lobby_id=lobby_id)

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
            is_text_only = all(
                prompt.question_type == QuestionTypeEnum.TEXT
                and prompt.answer_type == AnswerTypeEnum.TEXT
                for prompt in prompts
            )
            if not has_valid_orders or not is_text_only:
                incomplete_categories.append(category.id)

        if incomplete_categories:
            raise BadRequestError(
                "Every lobby category must contain exactly five uniquely ordered "
                f"text prompts; invalid categories: {incomplete_categories}",
            )
