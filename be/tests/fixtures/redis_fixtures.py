from collections.abc import AsyncGenerator

import pytest
from fakeredis import FakeAsyncRedis, FakeServer


@pytest.fixture
def fake_redis_server() -> FakeServer:
    """
    Per-test in-memory state shared by every ``FakeAsyncRedis`` created in
    the test. Sharing the ``FakeServer`` is what lets clients on different
    event loops (e.g. the test loop + the uvicorn server thread loop) see
    the same data — separate ``FakeAsyncRedis`` instances built against this
    server each bind their async primitives to their own loop.
    """
    return FakeServer()


@pytest.fixture
async def redis_client(fake_redis_server: FakeServer) -> AsyncGenerator[FakeAsyncRedis]:
    """
    Convenience client for direct use in the test's loop. Bound to the
    per-test ``FakeServer`` so it shares state with clients created on other
    loops (see ``fake_redis_server``).
    """
    client = FakeAsyncRedis(server=fake_redis_server)
    try:
        yield client
    finally:
        await client.aclose()
