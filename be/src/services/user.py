from typing import Annotated

from fastapi import Depends

from database import UnitOfWork
from errors.request import NotFoundError, ResourceConflictError, UnauthorizedError
from schemas.token import TokenSchema
from schemas.user.base import UserCreateSchema, UserPublicSchema
from schemas.user.nested import UserWithPromptsLobbiesPublicSchema
from utils.auth import create_access_token, validate_password


class UserService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def register(self, schema: UserCreateSchema) -> UserPublicSchema:
        async with self._uow:
            existing = await self._uow.user_repo.select_user(username=schema.username)
            if existing is not None:
                raise ResourceConflictError(
                    f"User '{schema.username}' already exists",
                )
            user = await self._uow.user_repo.insert_user(schema)
        return UserPublicSchema(id=user.id, username=user.username)

    async def sign_in(self, username: str, password: str) -> TokenSchema:
        async with self._uow:
            user = await self._uow.user_repo.select_user(username=username)
        if user is None or not validate_password(password, user.hashed_password):
            raise UnauthorizedError(
                "Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenSchema(access_token=create_access_token(user.id))

    async def get_user(self, user_id: int) -> UserWithPromptsLobbiesPublicSchema:
        async with self._uow:
            user = await self._uow.user_repo.select_user(
                user_id=user_id,
                include_extra=True,
            )
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user
