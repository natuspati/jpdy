from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enums.game import GamePhaseEnum
from enums.lobby import LobbyStateEnum
from fixtures.game_fixtures import SeededLobby, SocketClient
from models.lobby import Lobby
from schemas.lobby.game_state import GameLobbyState


async def _drain(socket: SocketClient, count: int) -> dict:
    last = None
    for _ in range(count):
        last = await socket.expect("state_changed")
    assert last is not None
    return last


async def _connect_all(
    seeded: SeededLobby,
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
    player_count: int,
) -> tuple[SocketClient, list[SocketClient]]:
    """
    Connect host first, then ``player_count`` players. Returns (host, players).
    Each connect produces one ``state_changed`` broadcast that every already-
    connected socket receives — this helper drains those so the queues are
    empty when the test starts issuing events.
    """
    host_socket = await connect_socket(seeded.lobby_id, seeded.host.token)
    await host_socket.expect("state_changed")

    players: list[SocketClient] = []
    for i, player in enumerate(seeded.players[:player_count]):
        ps = await connect_socket(seeded.lobby_id, player.token)
        # Each new connect broadcasts to everyone already in the namespace.
        # Drain host + previously-connected players + the new one itself.
        await host_socket.expect("state_changed")
        for prev in players:
            await prev.expect("state_changed")
        await ps.expect("state_changed")
        players.append(ps)
        _ = i  # silence linter
    return host_socket, players


async def test_start_game_transitions_db_and_phase(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
    db_session: AsyncSession,
):
    seeded = await seed_lobby(player_count=1)
    host_socket, _ = await _connect_all(seeded, connect_socket, player_count=1)

    await host_socket.client.emit(
        "start_game",
        namespace=f"/lobbies/{seeded.lobby_id}",
    )
    new_state = await host_socket.expect("state_changed")
    assert new_state["phase"] == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER.value

    db_row = (
        await db_session.execute(select(Lobby).where(Lobby.id == seeded.lobby_id))
    ).scalar_one()
    assert db_row.state == LobbyStateEnum.IN_PROGRESS.value


async def test_select_starter_sets_selecting_player(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1)
    host_socket, players = await _connect_all(seeded, connect_socket, player_count=1)
    player_id = seeded.players[0].id

    await host_socket.client.emit("start_game", namespace=f"/lobbies/{seeded.lobby_id}")
    await _drain(host_socket, 1)
    await _drain(players[0], 1)

    await host_socket.client.emit(
        "select_starter",
        {"user_id": player_id},
        namespace=f"/lobbies/{seeded.lobby_id}",
    )
    new_state = await host_socket.expect("state_changed")
    assert new_state["phase"] == GamePhaseEnum.PLAYER_SELECTING_PROMPT.value
    assert new_state["selecting_player_id"] == player_id


async def test_select_prompt_opens_prompt_and_starts_timer(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=2)
    host_socket, players = await _connect_all(seeded, connect_socket, player_count=1)
    player = players[0]
    player_id = seeded.players[0].id
    namespace = f"/lobbies/{seeded.lobby_id}"

    await host_socket.client.emit("start_game", namespace=namespace)
    await _drain(host_socket, 1)
    await _drain(player, 1)

    await host_socket.client.emit(
        "select_starter",
        {"user_id": player_id},
        namespace=namespace,
    )
    await _drain(host_socket, 1)
    await _drain(player, 1)

    prompt_id = seeded.prompt_ids[0]
    await player.client.emit(
        "select_prompt",
        {"prompt_id": prompt_id},
        namespace=namespace,
    )
    state = await player.expect("state_changed")
    assert state["phase"] == GamePhaseEnum.PLAYER_ANSWERING.value
    assert state["current_prompt_id"] == prompt_id
    assert state["timer_deadline"] is not None
    assert state["answering_player_id"] == player_id


async def test_judge_correct_increments_score_and_advances(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=2)
    host_socket, players = await _connect_all(seeded, connect_socket, player_count=1)
    player = players[0]
    player_id = seeded.players[0].id
    namespace = f"/lobbies/{seeded.lobby_id}"
    prompt_id = seeded.prompt_ids[0]

    await host_socket.client.emit("start_game", namespace=namespace)
    await _drain(host_socket, 1)
    await _drain(player, 1)
    await host_socket.client.emit(
        "select_starter",
        {"user_id": player_id},
        namespace=namespace,
    )
    await _drain(host_socket, 1)
    await _drain(player, 1)
    await player.client.emit("select_prompt", {"prompt_id": prompt_id}, namespace=namespace)
    await _drain(host_socket, 1)
    await _drain(player, 1)
    await player.client.emit("submit_answer", {"text": "guess"}, namespace=namespace)
    await _drain(host_socket, 1)
    await _drain(player, 1)
    await host_socket.client.emit(
        "judge_answer",
        {"correct": True},
        namespace=namespace,
    )
    state = await host_socket.expect("state_changed")

    assert state["phase"] == GamePhaseEnum.PLAYER_SELECTING_PROMPT.value
    expected_score = GameLobbyState.model_validate(state).categories[0].prompts[0].score_value
    assert any(p["user_id"] == player_id and p["score"] == expected_score for p in state["players"])


async def test_judge_wrong_opens_buzz_when_others_eligible(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=2, prompts_per_category=2)
    host_socket, players = await _connect_all(seeded, connect_socket, player_count=2)
    selector, other = players
    selector_id = seeded.players[0].id
    namespace = f"/lobbies/{seeded.lobby_id}"
    prompt_id = seeded.prompt_ids[0]

    await host_socket.client.emit("start_game", namespace=namespace)
    await _drain(host_socket, 1)
    await _drain(selector, 1)
    await _drain(other, 1)
    await host_socket.client.emit(
        "select_starter",
        {"user_id": selector_id},
        namespace=namespace,
    )
    await _drain(host_socket, 1)
    await _drain(selector, 1)
    await _drain(other, 1)
    await selector.client.emit("select_prompt", {"prompt_id": prompt_id}, namespace=namespace)
    await _drain(host_socket, 1)
    await _drain(selector, 1)
    await _drain(other, 1)
    await selector.client.emit("submit_answer", {"text": "wrong"}, namespace=namespace)
    await _drain(host_socket, 1)
    await _drain(selector, 1)
    await _drain(other, 1)
    await host_socket.client.emit("judge_answer", {"correct": False}, namespace=namespace)
    state = await host_socket.expect("state_changed")

    assert state["phase"] == GamePhaseEnum.BUZZ_OPEN.value
    assert selector_id in state["attempted_player_ids"]
    assert state["answering_player_id"] is None
