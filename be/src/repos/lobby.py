from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from enums.lobby import LobbyStateEnum
from models.lobby import Lobby, LobbyPromptCategory
from models.prompt_category import PromptCategory
from models.user import User
from schemas.lobby.base import LobbyFilterSchema, LobbyInDBSchema
from schemas.lobby.nested import (
    LobbyWithCategoriesInDBSchema,
    PaginatedLobbyWithCategoriesInDBSchema,
)
from utils.model_validation import validate_model


class LobbyRepo:
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def search_lobbies(
            self,
            filters: LobbyFilterSchema,
    ) -> PaginatedLobbyWithCategoriesInDBSchema:
        """
        Search lobbies with pagination, returning each lobby with its joined
        prompt categories.

        :param filters: validated search/pagination payload
        :return: page of lobbies with categories plus total count
        """
        conditions = []
        if filters.ids is not None:
            conditions.append(Lobby.id.in_(filters.ids))
        if filters.owner_ids is not None:
            conditions.append(Lobby.owner_id.in_(filters.owner_ids))
        if filters.states is not None:
            conditions.append(Lobby.state.in_([s.value for s in filters.states]))
        if filters.updated_at_start is not None:
            conditions.append(Lobby.updated_at >= filters.updated_at_start)
        if filters.updated_at_end is not None:
            conditions.append(Lobby.updated_at <= filters.updated_at_end)
        if filters.owner_username is not None:
            conditions.append(User.username.ilike(f"%{filters.owner_username}%"))
        
        base_query = select(Lobby).where(*conditions)
        if filters.owner_username is not None:
            base_query = base_query.join(User, Lobby.owner_id == User.id)
        
        total_query = select(func.count()).select_from(base_query.subquery())
        total = (await self._session.execute(total_query)).scalar_one()
        
        paginated_query = (
            base_query.options(selectinload(Lobby.prompt_categories))
            .order_by(Lobby.updated_at.desc(), Lobby.id.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        rows = (await self._session.execute(paginated_query)).scalars().all()
        contents = validate_model(rows, LobbyWithCategoriesInDBSchema)
        
        return PaginatedLobbyWithCategoriesInDBSchema(
            contents=contents,
            total=total,
            page=filters.page,
            size=filters.size,
        )
    
    async def select_lobby(
            self,
            lobby_id: int,
    ) -> LobbyWithCategoriesInDBSchema | None:
        """
        Select a lobby by id with its prompt categories eagerly loaded.

        :param lobby_id: lobby primary key
        :return: matched lobby with categories, or ``None`` if no lobby matches
        """
        query = (
            select(Lobby).where(Lobby.id == lobby_id).options(selectinload(Lobby.prompt_categories))
        )
        lobby = (await self._session.execute(query)).scalar_one_or_none()
        return validate_model(lobby, LobbyWithCategoriesInDBSchema)
    
    async def insert_lobby(self, owner_id: int) -> LobbyInDBSchema:
        """
        Insert a new lobby with state ``CREATED`` using SQL ``INSERT ... RETURNING``.

        :param owner_id: id of the user who will own the new lobby
        :return: the inserted lobby as ``LobbyInDBSchema``
        """
        stmt = (
            insert(Lobby)
            .values(owner_id=owner_id, state=LobbyStateEnum.CREATED)
            .returning(Lobby)
        )
        lobby = (await self._session.execute(stmt)).scalar_one()
        return validate_model(lobby, LobbyInDBSchema)
    
    async def update_lobby_state(
            self,
            lobby_id: int,
            state: LobbyStateEnum,
    ) -> bool:
        """
        Update the ``state`` column on a lobby.

        :param lobby_id: lobby primary key
        :param state: new state to write
        :return: ``True`` if a row was updated, ``False`` if no lobby matched
        """
        stmt = update(Lobby).where(Lobby.id == lobby_id).values(state=state)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
    
    async def delete_lobby(self, lobby_id: int) -> bool:
        """
        Delete a lobby by id. Rows in ``lobby_prompt_category`` are cascaded by
        the ``ON DELETE CASCADE`` constraint on ``lobby_id``.

        :param lobby_id: lobby primary key
        :return: ``True`` if a row was deleted, ``False`` if no lobby matched
        """
        stmt = delete(Lobby).where(Lobby.id == lobby_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
    
    async def select_existing_category_ids(self, category_ids: list[int]) -> set[int]:
        """
        Return the subset of ``category_ids`` that actually exist in the
        ``prompt_category`` table. Used by the service layer to validate that
        proposed lobby categories are real before writing to the association
        table.

        :param category_ids: candidate prompt category ids
        :return: set of ids that exist; empty when ``category_ids`` is empty
        """
        if not category_ids:
            return set()
        query = select(PromptCategory.id).where(PromptCategory.id.in_(category_ids))
        return set((await self._session.execute(query)).scalars().all())
    
    async def replace_lobby_categories(
            self,
            lobby_id: int,
            category_ids: list[int],
    ) -> None:
        """
        Replace the full set of categories attached to ``lobby_id`` with
        ``category_ids``. Wipes existing associations first, then inserts the
        new ones in a single statement (skipped when ``category_ids`` is empty).

        :param lobby_id: lobby primary key
        :param category_ids: ids to associate; duplicates should be removed by
            the caller
        """
        await self._session.execute(
            delete(LobbyPromptCategory).where(
                LobbyPromptCategory.lobby_id == lobby_id,
            ),
        )
        if category_ids:
            await self._session.execute(
                insert(LobbyPromptCategory),
                [{"lobby_id": lobby_id, "prompt_category_id": cid} for cid in category_ids],
            )
