import secrets
from typing import Annotated

from fastapi import Depends

from configs import settings
from database import UnitOfWork
from enums.user import UserRole
from errors.request import (
    ForbiddenError,
    NotFoundError,
    ResourceConflictError,
    UnauthorizedError,
)
from schemas.token import TokenSchema
from schemas.user.base import UserCreateSchema, UserPublicSchema
from schemas.user.nested import UserWithPromptsLobbiesPublicSchema
from utils.auth import create_access_token, hash_password, validate_password


class UserService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def register(self, schema: UserCreateSchema) -> UserPublicSchema:
        if settings.registration_code and not secrets.compare_digest(
            (schema.invite_code or "").encode(),
            settings.registration_code.encode(),
        ):
            raise ForbiddenError("Invalid invite code")
        async with self._uow:
            existing = await self._uow.user_repo.select_user_for_auth(username=schema.username)
            if existing is not None:
                raise ResourceConflictError(
                    f"User '{schema.username}' already exists",
                )
            user = await self._uow.user_repo.insert_user(
                username=schema.username,
                hashed_password=hash_password(schema.password),
            )
        return UserPublicSchema(id=user.id, username=user.username)

    async def sign_in(self, username: str, password: str) -> TokenSchema:
        async with self._uow:
            user = await self._uow.user_repo.select_user_for_auth(username=username)
        if user is None or not validate_password(password, user.hashed_password):
            raise UnauthorizedError(
                "Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenSchema(access_token=create_access_token(user.id))

    async def get_user(self, user_id: int) -> UserWithPromptsLobbiesPublicSchema:
        async with self._uow:
            user = await self._uow.user_repo.select_user_details(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def claim_admin(self, user_id: int, key: str) -> None:
        """Spend the user's one attempt; every failure is the same bare 403."""
        if not settings.admin_key:
            raise ForbiddenError
        async with self._uow as uow:
            if not await uow.user_repo.claim_admin_attempt(user_id):
                raise ForbiddenError
            granted = secrets.compare_digest(key.encode(), settings.admin_key.encode())
            if granted:
                await uow.user_repo.update_role(user_id, UserRole.ADMIN)
        # raised after the commit so a wrong guess stays consumed
        if not granted:
            raise ForbiddenError
