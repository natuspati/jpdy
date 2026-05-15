from typing import Annotated

from fastapi.params import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db_session, get_redis_session


class UnitOfWork:
    def __init__(
        self,
        session: Annotated[AsyncSession, Depends(get_db_session)],
        redis: Annotated[Redis, Depends(get_redis_session)],
    ):
        self._session = session
        self._redis = redis

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
