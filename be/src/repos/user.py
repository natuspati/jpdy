from datetime import UTC, datetime, time, timedelta

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from enums.lobby import LobbyStateEnum
from enums.user import AdminUserSortEnum, UserRole
from errors.base import BaseError
from models.lobby import Lobby, LobbyParticipant
from models.user import User
from schemas.admin import AdminUserFilterSchema, AdminUserListItemSchema, PaginatedAdminUserSchema
from schemas.user.base import UserInDBSchema
from schemas.user.nested import UserWithPromptsLobbiesPublicSchema
from utils.model_validation import validate_model


class UserRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def select_user_for_auth(
        self,
        *,
        user_id: int | None = None,
        username: str | None = None,
    ) -> UserInDBSchema | None:
        if user_id is None and username is None:
            raise BaseError("Provide either user_id or username")
        query = select(User)
        if user_id is not None:
            query = query.where(User.id == user_id)
        if username is not None:
            query = query.where(User.username == username)
        user = (await self._session.execute(query)).scalar_one_or_none()
        return validate_model(user, UserInDBSchema)

    async def select_user_details(
        self,
        user_id: int,
    ) -> UserWithPromptsLobbiesPublicSchema | None:
        query = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.prompt_categories), selectinload(User.lobbies))
        )
        user = (await self._session.execute(query)).scalar_one_or_none()
        return validate_model(user, UserWithPromptsLobbiesPublicSchema)

    async def insert_user(self, *, username: str, hashed_password: str) -> UserInDBSchema:
        stmt = (
            insert(User).values(username=username, hashed_password=hashed_password).returning(User)
        )
        user = (await self._session.execute(stmt)).scalar_one()
        return validate_model(user, UserInDBSchema)

    async def claim_admin_attempt(self, user_id: int) -> bool:
        """Atomically spend the user's single admin-key attempt; ``False`` if already spent."""
        stmt = (
            update(User)
            .where(
                User.id == user_id,
                User.role == UserRole.GENERIC,
                User.admin_key_attempted.is_(False),
            )
            .values(admin_key_attempted=True)
        )
        return (await self._session.execute(stmt)).rowcount > 0

    async def update_role(self, user_id: int, role: UserRole) -> bool:
        stmt = update(User).where(User.id == user_id).values(role=role)
        return (await self._session.execute(stmt)).rowcount > 0

    async def search_users(self, filters: AdminUserFilterSchema) -> PaginatedAdminUserSchema:
        """Admin user list with filters, sorting and on-the-fly hosted/played counts."""
        counted = Lobby.state.in_([LobbyStateEnum.IN_PROGRESS, LobbyStateEnum.COMPLETED])
        hosted = (
            select(func.count(Lobby.id))
            .where(Lobby.owner_id == User.id, counted)
            .correlate(User)
            .scalar_subquery()
        )
        played = (
            select(func.count(LobbyParticipant.id))
            .join(Lobby, Lobby.id == LobbyParticipant.lobby_id)
            .where(
                LobbyParticipant.user_id == User.id,
                LobbyParticipant.is_banned.is_(False),
                counted,
            )
            .correlate(User)
            .scalar_subquery()
        )
        conditions = []
        if filters.role is not None:
            conditions.append(User.role == filters.role)
        if filters.username is not None:
            conditions.append(User.username.ilike(f"%{filters.username}%"))
        if filters.created_from is not None:
            conditions.append(
                User.created_at >= datetime.combine(filters.created_from, time.min, tzinfo=UTC),
            )
        if filters.created_to is not None:
            conditions.append(
                User.created_at
                < datetime.combine(filters.created_to + timedelta(days=1), time.min, tzinfo=UTC),
            )
        order = {
            AdminUserSortEnum.USERNAME_ASC: [func.lower(User.username).asc(), User.id.asc()],
            AdminUserSortEnum.USERNAME_DESC: [func.lower(User.username).desc(), User.id.desc()],
            AdminUserSortEnum.CREATED_AT_ASC: [User.created_at.asc(), User.id.asc()],
            AdminUserSortEnum.CREATED_AT_DESC: [User.created_at.desc(), User.id.desc()],
        }[filters.sort]
        total = (
            await self._session.execute(select(func.count(User.id)).where(*conditions))
        ).scalar_one()
        rows = (
            await self._session.execute(
                select(
                    User.id,
                    User.username,
                    User.role,
                    User.created_at,
                    played.label("lobbies_played"),
                    hosted.label("lobbies_hosted"),
                )
                .where(*conditions)
                .order_by(*order)
                .limit(filters.limit)
                .offset(filters.offset),
            )
        ).all()
        return PaginatedAdminUserSchema(
            contents=validate_model(rows, AdminUserListItemSchema),
            total=total,
            page=filters.page,
            size=filters.size,
        )

    async def delete_user(self, user_id: int) -> bool:
        result = await self._session.execute(delete(User).where(User.id == user_id))
        return result.rowcount > 0
