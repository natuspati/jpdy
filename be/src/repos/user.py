from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from enums.user import UserRole
from errors.base import BaseError
from models.user import User
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
