from collections.abc import AsyncGenerator

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application import app as asgi_app
from application import fastapi_app as _fastapi_app
from database.session import get_db_session, get_redis_session


@pytest.fixture(scope="session")
def app() -> object:
    """Top-level socketio-wrapped ASGI app (used by the websocket tests)."""
    return asgi_app


@pytest.fixture(scope="session")
def fastapi_app() -> FastAPI:
    """Inner FastAPI app where dependency overrides are registered."""
    return _fastapi_app


@pytest.fixture
async def http_client(
    fastapi_app: FastAPI,
    db_session_maker: async_sessionmaker[AsyncSession],
    redis_client: FakeAsyncRedis,
) -> AsyncGenerator[AsyncClient]:
    """
    ``httpx.AsyncClient`` wired into ``fastapi_app`` via ``ASGITransport`` with
    ``get_db_session`` / ``get_redis_session`` overridden to use the per-test
    SQLite file and in-memory Redis. Overrides are cleared on teardown so
    tests stay isolated.
    """

    async def _override_db_session() -> AsyncGenerator[AsyncSession]:
        async with db_session_maker() as session:
            yield session

    async def _override_redis_session() -> AsyncGenerator[FakeAsyncRedis]:
        yield redis_client

    fastapi_app.dependency_overrides[get_db_session] = _override_db_session
    fastapi_app.dependency_overrides[get_redis_session] = _override_redis_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="http://testserver",
        ) as client:
            yield client
    finally:
        fastapi_app.dependency_overrides.pop(get_db_session, None)
        fastapi_app.dependency_overrides.pop(get_redis_session, None)
