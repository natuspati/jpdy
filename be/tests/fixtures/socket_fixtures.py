import asyncio
import socket as _socket
import threading
import time
from collections.abc import AsyncGenerator, Callable, Generator

import pytest
import socketio
import uvicorn


def _get_free_port() -> int:
    sock = _socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(scope="session")
def socket_server_url(app) -> Generator[str]:
    port = _get_free_port()
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        lifespan="off",
        ws="wsproto",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    while not server.started:
        time.sleep(0.05)

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture
async def make_socket_client() -> AsyncGenerator[Callable[[], socketio.AsyncClient]]:
    clients: list[socketio.AsyncClient] = []

    def _factory() -> socketio.AsyncClient:
        client = socketio.AsyncClient()
        clients.append(client)
        return client

    try:
        yield _factory
    finally:
        for client in clients:
            if not client.connected:
                continue
            try:
                await client.disconnect()
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
