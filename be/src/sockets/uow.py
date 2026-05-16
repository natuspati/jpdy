from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from database import UnitOfWork
from database.session import get_db_session, get_redis_session

# Tests swap these to point at per-test SQLite + fakeredis. Production code
# leaves them at the originals defined in ``database.session``.
db_session_factory: type[AsyncGenerator[AsyncSession]] = get_db_session
redis_session_factory: type[AsyncGenerator[Redis]] = get_redis_session


@asynccontextmanager
async def build_uow() -> AsyncGenerator[UnitOfWork]:
    """
    Construct a ``UnitOfWork`` outside the FastAPI dependency-injection chain
    by manually advancing the configured DB and Redis async generators. Used
    by Socket.IO event handlers, which don't run through ``Depends``.

    The returned UoW is *not* yet entered; callers should still ``async with
    uow:`` to get commit/rollback semantics.
    """
    db_gen = db_session_factory()
    session = await anext(db_gen)
    redis_gen = redis_session_factory()
    redis = await anext(redis_gen)
    try:
        yield UnitOfWork(session=session, redis=redis)
    finally:
        await db_gen.aclose()
        await redis_gen.aclose()
