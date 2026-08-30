from collections.abc import AsyncGenerator
from typing import Any

from redis.asyncio import ConnectionPool, Redis
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from configs import settings


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def configure_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """
    Enable SQLite foreign-key enforcement for every connection from ``engine``.

    SQLite accepts foreign-key declarations but ignores their cascade rules
    until each database connection runs ``PRAGMA foreign_keys=ON``.
    """
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)


engine = create_async_engine(
    settings.db_url,
    echo=settings.db_echo,
    echo_pool=settings.db_echo_pool,
)
configure_sqlite_foreign_keys(engine)

async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=settings.db_expire_on_commit,
    class_=AsyncSession,
)

redis_pool = ConnectionPool.from_url(settings.redis_url)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


async def get_redis_session() -> AsyncGenerator[Redis]:
    client = Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
