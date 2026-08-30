from sqlalchemy import and_, case, delete, exists, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.selectable import ScalarSelect

from enums.lobby import LobbyStateEnum
from models.lobby import Lobby, LobbyParticipant, LobbyPromptCategory
from models.prompt import Prompt
from models.prompt_category import PromptCategory
from models.user import User
from schemas.lobby.base import LobbyFilterSchema, LobbyInDBSchema
from schemas.lobby.nested import (
    LobbyActiveListItemSchema,
    LobbyMineListItemSchema,
    LobbyWithCategoriesInDBSchema,
    LobbyWithCategoryPromptsInDBSchema,
    PaginatedLobbyWithCategoriesInDBSchema,
)
from schemas.lobby.participant import LobbyParticipantInDBSchema
from schemas.user.base import UserPublicSchema
from utils.model_validation import validate_model


class LobbyRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search_lobbies(
        self,
        filters: LobbyFilterSchema,
        user_id: int,
    ) -> PaginatedLobbyWithCategoriesInDBSchema:
        """
        Search lobbies with pagination, returning each lobby with its joined
        prompt categories.

        :param filters: validated search/pagination payload
        :return: page of lobbies with categories plus total count
        """
        conditions = []
        conditions.append(
            (Lobby.state != LobbyStateEnum.CREATED) | (Lobby.owner_id == user_id),
        )
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
            base_query.options(
                selectinload(Lobby.prompt_categories),
                selectinload(Lobby.owner),
            )
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
            select(Lobby)
            .where(Lobby.id == lobby_id)
            .options(
                selectinload(Lobby.prompt_categories),
                selectinload(Lobby.owner),
            )
        )
        lobby = (await self._session.execute(query)).scalar_one_or_none()
        return validate_model(lobby, LobbyWithCategoriesInDBSchema)

    async def select_active_lobbies(self, user_id: int) -> list[LobbyActiveListItemSchema]:
        player_count = _eligible_player_count_query()
        participant_exists = exists(
            select(LobbyParticipant.id).where(
                LobbyParticipant.lobby_id == Lobby.id,
                LobbyParticipant.user_id == user_id,
            ),
        )
        query = (
            select(
                Lobby.id.label("id"),
                User.username.label("host_username"),
                player_count.label("player_count"),
                Lobby.state.label("state"),
            )
            .join(User, Lobby.owner_id == User.id)
            .where(
                Lobby.state == LobbyStateEnum.WAITING_START,
                Lobby.owner_id != user_id,
                ~participant_exists,
            )
            .order_by(Lobby.updated_at.desc(), Lobby.id.desc())
        )
        rows = (await self._session.execute(query)).all()
        return validate_model(rows, LobbyActiveListItemSchema)

    async def select_my_lobbies(self, user_id: int) -> list[LobbyMineListItemSchema]:
        participant = LobbyParticipant
        player_count = _eligible_player_count_query()
        is_owner = case((Lobby.owner_id == user_id, True), else_=False)
        is_participant = case(
            (
                and_(
                    participant.user_id.is_not(None),
                    participant.is_banned.is_(False),
                ),
                True,
            ),
            else_=False,
        )
        query = (
            select(
                Lobby.id.label("id"),
                Lobby.owner_id.label("owner_id"),
                User.username.label("host_username"),
                player_count.label("player_count"),
                Lobby.state.label("state"),
                Lobby.created_at.label("created_at"),
                Lobby.updated_at.label("updated_at"),
                is_owner.label("is_owner"),
                is_participant.label("is_participant"),
            )
            .outerjoin(User, Lobby.owner_id == User.id)
            .outerjoin(
                participant,
                and_(
                    participant.lobby_id == Lobby.id,
                    participant.user_id == user_id,
                ),
            )
            .where(
                or_(
                    Lobby.owner_id == user_id,
                    and_(
                        participant.user_id.is_not(None),
                        participant.is_banned.is_(False),
                    ),
                ),
            )
            .order_by(Lobby.updated_at.desc(), Lobby.id.desc())
        )
        rows = (await self._session.execute(query)).all()
        return validate_model(rows, LobbyMineListItemSchema)

    async def select_eligible_player_count(self, lobby_id: int) -> int:
        query = select(func.count(LobbyParticipant.id)).where(
            LobbyParticipant.lobby_id == lobby_id,
            LobbyParticipant.is_banned.is_(False),
        )
        return (await self._session.execute(query)).scalar_one()

    async def select_participant(
        self,
        lobby_id: int,
        user_id: int,
    ) -> LobbyParticipantInDBSchema | None:
        query = select(LobbyParticipant).where(
            LobbyParticipant.lobby_id == lobby_id,
            LobbyParticipant.user_id == user_id,
        )
        participant = (await self._session.execute(query)).scalar_one_or_none()
        return validate_model(participant, LobbyParticipantInDBSchema)

    async def ensure_participant(
        self,
        lobby_id: int,
        user: UserPublicSchema,
    ) -> LobbyParticipantInDBSchema:
        participant = await self.select_participant(lobby_id=lobby_id, user_id=user.id)
        if participant is not None:
            if participant.username_snapshot != user.username:
                await self._session.execute(
                    update(LobbyParticipant)
                    .where(LobbyParticipant.id == participant.id)
                    .values(username_snapshot=user.username),
                )
                return participant.model_copy(update={"username_snapshot": user.username})
            return participant

        stmt = (
            insert(LobbyParticipant)
            .values(
                lobby_id=lobby_id,
                user_id=user.id,
                username_snapshot=user.username,
            )
            .returning(LobbyParticipant)
        )
        inserted = (await self._session.execute(stmt)).scalar_one()
        return validate_model(inserted, LobbyParticipantInDBSchema)

    async def update_participant_ban(
        self,
        lobby_id: int,
        user_id: int,
        is_banned: bool,
    ) -> bool:
        result = await self._session.execute(
            update(LobbyParticipant)
            .where(
                LobbyParticipant.lobby_id == lobby_id,
                LobbyParticipant.user_id == user_id,
            )
            .values(is_banned=is_banned),
        )
        return result.rowcount > 0

    async def snapshot_final_results(
        self,
        lobby_id: int,
        players: list[tuple[int, str, int, bool]],
    ) -> None:
        for user_id, username, score, is_banned in players:
            participant = await self.select_participant(lobby_id=lobby_id, user_id=user_id)
            if participant is None:
                participant = await self.ensure_participant(
                    lobby_id=lobby_id,
                    user=UserPublicSchema(id=user_id, username=username),
                )
            await self._session.execute(
                update(LobbyParticipant)
                .where(LobbyParticipant.id == participant.id)
                .values(
                    username_snapshot=username,
                    is_banned=is_banned,
                    final_score=score,
                ),
            )

    async def select_final_rankings(
        self,
        lobby_id: int,
    ) -> list[LobbyParticipantInDBSchema]:
        query = (
            select(LobbyParticipant)
            .where(
                LobbyParticipant.lobby_id == lobby_id,
                LobbyParticipant.final_score.is_not(None),
            )
            .order_by(
                LobbyParticipant.final_score.desc(),
                LobbyParticipant.username_snapshot.asc(),
                LobbyParticipant.id.asc(),
            )
        )
        rows = (await self._session.execute(query)).scalars().all()
        return validate_model(rows, LobbyParticipantInDBSchema)

    async def select_lobby_with_prompts(
        self,
        lobby_id: int,
    ) -> LobbyWithCategoryPromptsInDBSchema | None:
        """
        Select a lobby by id with its prompt categories *and* the prompts
        belonging to each category eagerly loaded. Used to snapshot a lobby
        into Redis when the game starts.

        :param lobby_id: lobby primary key
        :return: matched lobby with categories and prompts, or ``None`` if no
            lobby matches
        """
        query = (
            select(Lobby)
            .where(Lobby.id == lobby_id)
            .options(
                selectinload(Lobby.owner),
                selectinload(Lobby.prompt_categories)
                .selectinload(
                    PromptCategory.prompts,
                )
                .selectinload(Prompt.question_media_asset),
                selectinload(Lobby.prompt_categories)
                .selectinload(
                    PromptCategory.prompts,
                )
                .selectinload(Prompt.answer_media_asset),
            )
        )
        lobby = (await self._session.execute(query)).scalar_one_or_none()
        return validate_model(lobby, LobbyWithCategoryPromptsInDBSchema)

    async def insert_lobby(self, owner_id: int) -> LobbyInDBSchema:
        """
        Insert a new lobby with state ``CREATED`` using SQL ``INSERT ... RETURNING``.

        :param owner_id: id of the user who will own the new lobby
        :return: the inserted lobby as ``LobbyInDBSchema``
        """
        stmt = (
            insert(Lobby).values(owner_id=owner_id, state=LobbyStateEnum.CREATED).returning(Lobby)
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


def _eligible_player_count_query() -> ScalarSelect[int]:
    return (
        select(func.count(LobbyParticipant.id))
        .where(
            LobbyParticipant.lobby_id == Lobby.id,
            LobbyParticipant.is_banned.is_(False),
        )
        .correlate(Lobby)
        .scalar_subquery()
    )
