from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from configs import settings

engine = create_async_engine(
    settings.db_url,
    echo=settings.db_echo,
    echo_pool=settings.db_echo_pool,
)

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
