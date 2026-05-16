from collections.abc import Awaitable, Callable

import pytest
import socketio

from enums.game import PlayerConnectionStatusEnum
from fixtures.game_fixtures import SeededLobby, SocketClient


async def test_connect_with_invalid_token_is_rejected(
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
):
    seeded = await seed_lobby()
    client = make_socket_client()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await client.connect(
            f"{socket_server_url}?token=garbage",
            socketio_path="ws",
            namespaces=[f"/lobbies/{seeded.lobby_id}"],
            wait_timeout=2,
        )


async def test_connect_without_token_is_rejected(
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
):
    seeded = await seed_lobby()
    client = make_socket_client()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await client.connect(
            socket_server_url,
            socketio_path="ws",
            namespaces=[f"/lobbies/{seeded.lobby_id}"],
            wait_timeout=2,
        )


async def test_connect_to_missing_lobby_is_rejected(
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
):
    seeded = await seed_lobby(player_count=1)
    client = make_socket_client()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await client.connect(
            f"{socket_server_url}?token={seeded.host.token}",
            socketio_path="ws",
            namespaces=["/lobbies/9999999"],
            wait_timeout=2,
        )


async def test_host_connect_flips_connection_status(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    socket = await connect_socket(seeded.lobby_id, seeded.host.token)
    state = await socket.expect("state_changed")
    assert state["host"]["user_id"] == seeded.host.id
    assert state["host"]["connection_status"] == PlayerConnectionStatusEnum.CONNECTED.value


async def test_player_connect_appends_to_players(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    socket = await connect_socket(seeded.lobby_id, player.token)
    state = await socket.expect("state_changed")
    matching = [p for p in state["players"] if p["user_id"] == player.id]
    assert len(matching) == 1
    assert matching[0]["connection_status"] == PlayerConnectionStatusEnum.CONNECTED.value


async def test_duplicate_device_connect_is_rejected(
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    first = await connect_socket(seeded.lobby_id, player.token)
    await first.expect("state_changed")
    second = make_socket_client()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await second.connect(
            f"{socket_server_url}?token={player.token}",
            socketio_path="ws",
            namespaces=[f"/lobbies/{seeded.lobby_id}"],
            wait_timeout=2,
        )


async def test_player_disconnect_flips_state(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    player_socket = await connect_socket(seeded.lobby_id, player.token)
    await player_socket.expect("state_changed")

    host_socket = await connect_socket(seeded.lobby_id, seeded.host.token)
    await host_socket.expect("state_changed")  # state after host connect

    await player_socket.client.disconnect()
    final_state = await host_socket.expect("state_changed")
    player_row = next(p for p in final_state["players"] if p["user_id"] == player.id)
    assert player_row["connection_status"] == PlayerConnectionStatusEnum.DISCONNECTED.value
