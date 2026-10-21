import asyncio
from collections.abc import Awaitable, Callable

import pytest
import socketio

from fixtures.game_fixtures import SeededLobby, SocketClient

LIST_NAMESPACE = "/lobby-list"


async def test_lobby_list_rejects_invalid_token(
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
):
    client = make_socket_client()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await client.connect(
            f"{socket_server_url}?token=garbage",
            socketio_path="ws",
            namespaces=[LIST_NAMESPACE],
            wait_timeout=2,
        )


async def test_player_joining_pings_lobby_list(
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    pings: asyncio.Queue[None] = asyncio.Queue()
    watcher = make_socket_client()

    @watcher.on("lobbies_changed", namespace=LIST_NAMESPACE)
    async def _on_changed(*_: object) -> None:
        await pings.put(None)

    await watcher.connect(
        f"{socket_server_url}?token={seeded.host.token}",
        socketio_path="ws",
        namespaces=[LIST_NAMESPACE],
        wait_timeout=2,
    )

    await connect_socket(seeded.lobby_id, seeded.players[0].token)

    await asyncio.wait_for(pings.get(), timeout=2)
