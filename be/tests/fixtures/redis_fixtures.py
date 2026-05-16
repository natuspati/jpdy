from collections.abc import AsyncGenerator

import pytest
from fakeredis import FakeAsyncRedis


@pytest.fixture
async def redis_client() -> AsyncGenerator[FakeAsyncRedis]:
    """In-memory Redis emulator; isolated per test (fresh instance)."""
    client = FakeAsyncRedis()
    try:
        yield client
    finally:
        await client.aclose()
