from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from errors.base import BaseError
from models.user import User
from schemas.user.base import UserCreateSchema, UserInDBSchema
from schemas.user.nested import UserWithPromptsLobbiesInDBSchema
from utils.model_validation import validate_model


class UserRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def select_user(
        self,
        *,
        user_id: int | None = None,
        username: str | None = None,
        include_extra: bool = False,
    ) -> UserInDBSchema | UserWithPromptsLobbiesInDBSchema | None:
        """
        Select a user by id or username.

        :param user_id: optional user primary key to filter by
        :param username: optional username to filter by
        :param include_extra: when True, eagerly loads the user's prompt
            categories and lobbies and returns a
            ``UserWithPromptsLobbiesInDBSchema``; when False, returns a plain
            ``UserInDBSchema``
        :return: the matched user schema, or ``None`` if no user matches
        """
        if user_id is None and username is None:
            raise BaseError("Provide either user_id or username")

        query = select(User)
        if user_id is not None:
            query = query.where(User.id == user_id)
        if username is not None:
            query = query.where(User.username == username)
        if include_extra:
            query = query.options(
                selectinload(User.prompt_categories),
                selectinload(User.lobbies),
            )

        user = (await self._session.execute(query)).scalar_one_or_none()
        if include_extra:
            return validate_model(user, UserWithPromptsLobbiesInDBSchema)
        return validate_model(user, UserInDBSchema)

    async def insert_user(self, schema: UserCreateSchema) -> UserInDBSchema:
        """
        Insert a new user using SQL ``INSERT ... RETURNING``.

        :param schema: validated user create payload; the plaintext password
            is hashed via the ``hashed_password`` computed field before being
            written to the database.
        :return: the inserted user as ``UserInDBSchema``
        """
        stmt = (
            insert(User)
            .values(
                username=schema.username,
                hashed_password=schema.hashed_password,
            )
            .returning(User)
        )
        user = (await self._session.execute(stmt)).scalar_one()
        return validate_model(user, UserInDBSchema)
