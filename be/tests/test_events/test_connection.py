from collections.abc import Awaitable, Callable

import pytest
import socketio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enums.game import GamePhaseEnum, PlayerConnectionStatusEnum
from fixtures.game_fixtures import SeededLobby, SocketClient
from models.lobby import LobbyParticipant
from schemas.lobby.game_state import GamePlayerState
from utils.game_state import game_state_key


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
    db_session: AsyncSession,
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    socket = await connect_socket(seeded.lobby_id, player.token)
    state = await socket.expect("state_changed")
    matching = [p for p in state["players"] if p["user_id"] == player.id]
    assert len(matching) == 1
    assert matching[0]["connection_status"] == PlayerConnectionStatusEnum.CONNECTED.value
    participant = (
        await db_session.execute(
            select(LobbyParticipant).where(
                LobbyParticipant.lobby_id == seeded.lobby_id,
                LobbyParticipant.user_id == player.id,
            ),
        )
    ).scalar_one()
    assert participant.username_snapshot == player.username
    assert participant.is_banned is False


async def test_new_connection_replaces_existing_user_connection(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    first = await connect_socket(seeded.lobby_id, player.token)
    await first.expect("state_changed")
    second = await connect_socket(seeded.lobby_id, player.token)
    state = await second.expect("state_changed")
    player_row = next(item for item in state["players"] if item["user_id"] == player.id)
    assert player_row["connection_status"] == PlayerConnectionStatusEnum.CONNECTED.value


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


async def test_existing_player_can_reconnect_after_game_start(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    host_socket = await connect_socket(seeded.lobby_id, seeded.host.token)
    await host_socket.expect("state_changed")
    player = seeded.players[0]
    first_connection = await connect_socket(seeded.lobby_id, player.token)
    await host_socket.expect("state_changed")
    await first_connection.expect("state_changed")

    await host_socket.client.emit("start_game", namespace=f"/lobbies/{seeded.lobby_id}")
    await host_socket.expect("state_changed")
    await first_connection.expect("state_changed")
    await first_connection.client.disconnect()
    await host_socket.expect("state_changed")

    reconnected = await connect_socket(seeded.lobby_id, player.token)
    await reconnected.expect("state_changed")


async def test_host_can_reconnect_when_persisted_status_is_stale(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    seeded.state.host.connection_status = PlayerConnectionStatusEnum.CONNECTED
    await redis_client.set(game_state_key(seeded.state.lobby_id), seeded.state.model_dump_json())

    reconnected = await connect_socket(seeded.lobby_id, seeded.host.token)
    state = await reconnected.expect("state_changed")

    assert state["host"]["connection_status"] == PlayerConnectionStatusEnum.CONNECTED.value


async def test_player_can_reconnect_when_persisted_status_is_stale(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    seeded.state.players = [
        GamePlayerState(
            user_id=player.id,
            username=player.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    await redis_client.set(game_state_key(seeded.state.lobby_id), seeded.state.model_dump_json())

    reconnected = await connect_socket(seeded.lobby_id, player.token)
    state = await reconnected.expect("state_changed")
    player_row = next(item for item in state["players"] if item["user_id"] == player.id)

    assert player_row["connection_status"] == PlayerConnectionStatusEnum.CONNECTED.value


async def test_host_can_reconnect_during_active_game(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    host = await connect_socket(seeded.lobby_id, seeded.host.token)
    await host.expect("state_changed")
    player = await connect_socket(seeded.lobby_id, seeded.players[0].token)
    await host.expect("state_changed")
    await player.expect("state_changed")

    await host.client.emit("start_game", namespace=f"/lobbies/{seeded.lobby_id}")
    await host.expect("state_changed")
    await player.expect("state_changed")
    await host.client.disconnect()
    await player.expect("state_changed")

    reconnected = await connect_socket(seeded.lobby_id, seeded.host.token)
    state = await reconnected.expect("state_changed")

    assert state["phase"] == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER.value
    assert state["host"]["connection_status"] == PlayerConnectionStatusEnum.CONNECTED.value


async def test_new_player_is_rejected_after_game_start(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
):
    seeded = await seed_lobby(player_count=2)
    host_socket = await connect_socket(seeded.lobby_id, seeded.host.token)
    await host_socket.expect("state_changed")
    player_socket = await connect_socket(seeded.lobby_id, seeded.players[0].token)
    await host_socket.expect("state_changed")
    await player_socket.expect("state_changed")

    await host_socket.client.emit("start_game", namespace=f"/lobbies/{seeded.lobby_id}")
    await host_socket.expect("state_changed")
    await player_socket.expect("state_changed")

    client = make_socket_client()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await client.connect(
            f"{socket_server_url}?token={seeded.players[1].token}",
            socketio_path="ws",
            namespaces=[f"/lobbies/{seeded.lobby_id}"],
            wait_timeout=2,
        )
