from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import UnitOfWork
from enums.game import GamePhaseEnum, GameResolutionEnum
from enums.lobby import LobbyStateEnum
from fixtures.game_fixtures import SeededLobby, SocketClient
from models.lobby import Lobby
from schemas.lobby.game_state import GamePlayerState
from schemas.socket.events import JudgeAnswerPayload
from services.game import GameService


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
    host_socket = await connect_socket(seeded.lobby_id, seeded.host.token)
    await host_socket.expect("state_changed")

    players: list[SocketClient] = []
    for player in seeded.players[:player_count]:
        player_socket = await connect_socket(seeded.lobby_id, player.token)
        await host_socket.expect("state_changed")
        for previous in players:
            await previous.expect("state_changed")
        await player_socket.expect("state_changed")
        players.append(player_socket)
    return host_socket, players


async def _start_on_first_prompt(
    seeded: SeededLobby,
    host: SocketClient,
    players: list[SocketClient],
) -> None:
    namespace = f"/lobbies/{seeded.lobby_id}"
    await host.client.emit("start_game", namespace=namespace)
    await _drain(host, 1)
    for player in players:
        await _drain(player, 1)

    await host.client.emit(
        "select_starter",
        {"user_id": seeded.players[0].id},
        namespace=namespace,
    )
    await _drain(host, 1)
    for player in players:
        await _drain(player, 1)

    await players[0].client.emit(
        "select_prompt",
        {"prompt_id": seeded.prompt_ids[0]},
        namespace=namespace,
    )


async def test_start_game_transitions_db_and_phase(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
    db_session: AsyncSession,
):
    seeded = await seed_lobby(player_count=1)
    host_socket, _ = await _connect_all(seeded, connect_socket, player_count=1)

    await host_socket.client.emit("start_game", namespace=f"/lobbies/{seeded.lobby_id}")
    state = await host_socket.expect("state_changed")

    assert state["phase"] == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER.value
    db_row = (
        await db_session.execute(select(Lobby).where(Lobby.id == seeded.lobby_id))
    ).scalar_one()
    assert db_row.state == LobbyStateEnum.IN_PROGRESS.value


async def test_host_answer_key_is_private_and_player_frame_never_leaks_answer(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=2)
    host, players = await _connect_all(seeded, connect_socket, player_count=1)
    player = players[0]
    await _start_on_first_prompt(seeded, host, players)

    host_state = await host.expect("state_changed")
    player_state = await player.expect("state_changed")
    host_answer_key = await host.expect("host_answer_key")

    assert host_state == player_state
    assert host_state["phase"] == GamePhaseEnum.PLAYER_ANSWERING.value
    assert host_state["current_prompt_id"] == seeded.prompt_ids[0]
    assert host_state["resolved_answer"] is None
    assert all(
        "answer" not in prompt
        for category in player_state["categories"]
        for prompt in category["prompts"]
    )
    assert host_answer_key == {
        "lobby_id": seeded.lobby_id,
        "prompt_id": seeded.prompt_ids[0],
        "expected_answer": "Category 1 A1",
    }


async def test_correct_judgment_enters_public_answer_reveal(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=2)
    host, players = await _connect_all(seeded, connect_socket, player_count=1)
    await _start_on_first_prompt(seeded, host, players)
    await _drain(host, 1)
    await _drain(players[0], 1)

    await host.client.emit(
        "judge_answer",
        {"correct": True},
        namespace=f"/lobbies/{seeded.lobby_id}",
    )
    host_state = await host.expect("state_changed")
    player_state = await players[0].expect("state_changed")

    assert host_state == player_state
    assert host_state["phase"] == GamePhaseEnum.ANSWER_REVEAL.value
    assert host_state["resolved_prompt_id"] == seeded.prompt_ids[0]
    assert host_state["resolved_answer"] == "Category 1 A1"
    assert host_state["resolution"] == GameResolutionEnum.CORRECT.value
    assert host_state["current_prompt_id"] == seeded.prompt_ids[0]
    assert any(
        player["user_id"] == seeded.players[0].id and player["score"] == 100
        for player in host_state["players"]
    )


async def test_wrong_judgment_opens_buzz_when_player_remains_eligible(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=2, prompts_per_category=2)
    host, players = await _connect_all(seeded, connect_socket, player_count=2)
    await _start_on_first_prompt(seeded, host, players)
    await _drain(host, 1)
    for player in players:
        await _drain(player, 1)

    await host.client.emit(
        "judge_answer",
        {"correct": False},
        namespace=f"/lobbies/{seeded.lobby_id}",
    )
    state = await host.expect("state_changed")

    assert state["phase"] == GamePhaseEnum.BUZZ_OPEN.value
    assert seeded.players[0].id in state["attempted_player_ids"]
    assert state["resolved_answer"] is None


async def test_wrong_without_eligible_buzzer_reveals_answer(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=2)
    player = seeded.players[0]
    state = seeded.state
    state.players = [GamePlayerState(user_id=player.id, username=player.username)]
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = seeded.prompt_ids[0]
    state.answering_player_id = player.id
    state.selecting_player_id = player.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=10)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    result = await GameService(UnitOfWork(db_session, redis_client)).judge_answer(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=JudgeAnswerPayload(correct=False),
    )

    assert result.phase == GamePhaseEnum.ANSWER_REVEAL
    assert result.resolution == GameResolutionEnum.UNANSWERED
    assert result.resolved_answer == "Category 1 A1"


@pytest.mark.parametrize("phase", [GamePhaseEnum.PLAYER_ANSWERING, GamePhaseEnum.BUZZ_OPEN])
async def test_expired_clue_without_eligible_buzzer_reveals_answer(
    phase: GamePhaseEnum,
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=2)
    player = seeded.players[0]
    state = seeded.state
    state.players = [GamePlayerState(user_id=player.id, username=player.username)]
    state.phase = phase
    state.current_prompt_id = seeded.prompt_ids[0]
    state.selecting_player_id = player.id
    state.answering_player_id = player.id if phase == GamePhaseEnum.PLAYER_ANSWERING else None
    state.categories[0].prompts[0].is_selected = True
    state.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    await redis_client.set(state.key, state.model_dump_json())

    result = await GameService(UnitOfWork(db_session, redis_client)).expire_timer(
        seeded.lobby_id,
    )

    assert result is not None
    assert result.phase == GamePhaseEnum.ANSWER_REVEAL
    assert result.resolution == GameResolutionEnum.EXPIRED
    assert result.resolved_answer == "Category 1 A1"


async def test_final_clue_finishes_only_after_answer_reveal(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=1)
    player = seeded.players[0]
    state = seeded.state
    state.players = [GamePlayerState(user_id=player.id, username=player.username)]
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = seeded.prompt_ids[0]
    state.answering_player_id = player.id
    state.selecting_player_id = player.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=10)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    service = GameService(UnitOfWork(db_session, redis_client))
    reveal = await service.judge_answer(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=JudgeAnswerPayload(correct=True),
    )
    assert reveal.phase == GamePhaseEnum.ANSWER_REVEAL

    reveal.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    await redis_client.set(reveal.key, reveal.model_dump_json())
    finished = await service.expire_timer(seeded.lobby_id)

    assert finished is not None
    assert finished.phase == GamePhaseEnum.FINISHED
    assert finished.resolved_answer is None
    db_row = (
        await db_session.execute(select(Lobby).where(Lobby.id == seeded.lobby_id))
    ).scalar_one()
    assert db_row.state == LobbyStateEnum.COMPLETED.value


async def test_only_host_can_judge_and_late_judgment_is_rejected(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    state = seeded.state
    state.players = [GamePlayerState(user_id=player.id, username=player.username)]
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = seeded.prompt_ids[0]
    state.answering_player_id = player.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=10)
    await redis_client.set(state.key, state.model_dump_json())
    service = GameService(UnitOfWork(db_session, redis_client))

    with pytest.raises(Exception, match="Only the host"):
        await service.judge_answer(
            lobby_id=seeded.lobby_id,
            user_id=player.id,
            payload=JudgeAnswerPayload(correct=True),
        )

    state.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    await redis_client.set(state.key, state.model_dump_json())
    with pytest.raises(Exception, match="Answer time has expired"):
        await service.judge_answer(
            lobby_id=seeded.lobby_id,
            user_id=seeded.host.id,
            payload=JudgeAnswerPayload(correct=True),
        )
