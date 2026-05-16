from functools import cached_property
from typing import Annotated

from fastapi.params import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db_session, get_redis_session
from repos import GameStateRepo, LobbyRepo, PromptCategoryRepo, PromptRepo, UserRepo


class UnitOfWork:
    def __init__(
        self,
        session: Annotated[AsyncSession, Depends(get_db_session)],
        redis: Annotated[Redis, Depends(get_redis_session)],
    ):
        self._session = session
        self._redis = redis

    @cached_property
    def user_repo(self) -> UserRepo:
        return UserRepo(self._session)

    @cached_property
    def prompt_repo(self) -> PromptRepo:
        return PromptRepo(self._session)

    @cached_property
    def prompt_category_repo(self) -> PromptCategoryRepo:
        return PromptCategoryRepo(self._session)

    @cached_property
    def lobby_repo(self) -> LobbyRepo:
        return LobbyRepo(self._session)

    @cached_property
    def game_state_repo(self) -> GameStateRepo:
        return GameStateRepo(self._redis)

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        if exc:
            await self._session.rollback()
        else:
            await self._session.commit()
