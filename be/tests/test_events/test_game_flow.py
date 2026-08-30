import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import UnitOfWork
from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from enums.lobby import LobbyStateEnum
from fixtures.game_fixtures import SeededLobby, SocketClient
from models.lobby import Lobby, LobbyParticipant
from schemas.lobby.game_state import GamePlayerState
from schemas.socket.events import (
    BanPlayerPayload,
    JudgeAnswerPayload,
    SelectStarterPayload,
    UnbanPlayerPayload,
)
from services import game_timers
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
    state.players = [
        GamePlayerState(
            user_id=player.id,
            username=player.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
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
    participant = (
        await db_session.execute(
            select(LobbyParticipant).where(
                LobbyParticipant.lobby_id == seeded.lobby_id,
                LobbyParticipant.user_id == player.id,
            ),
        )
    ).scalar_one()
    assert participant.final_score == 100


async def test_ban_and_unban_sync_persistent_participant_state(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    state = seeded.state
    state.players = [GamePlayerState(user_id=player.id, username=player.username)]
    await redis_client.set(state.key, state.model_dump_json())
    service = GameService(UnitOfWork(db_session, redis_client))

    banned = await service.ban_player(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=BanPlayerPayload(user_id=player.id),
    )
    assert banned.players[0].is_banned is True

    participant = (
        await db_session.execute(
            select(LobbyParticipant).where(
                LobbyParticipant.lobby_id == seeded.lobby_id,
                LobbyParticipant.user_id == player.id,
            ),
        )
    ).scalar_one()
    assert participant.is_banned is True

    unbanned = await service.unban_player(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=UnbanPlayerPayload(user_id=player.id),
    )
    assert unbanned.players[0].is_banned is False

    await db_session.refresh(participant)
    assert participant.is_banned is False


async def test_ban_current_selector_recovers_to_host_player_selection(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=2)
    selector, replacement = seeded.players
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=selector.id,
            username=selector.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
            is_selected=True,
        ),
        GamePlayerState(
            user_id=replacement.id,
            username=replacement.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
    state.selecting_player_id = selector.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=30)
    await redis_client.set(state.key, state.model_dump_json())

    service = GameService(UnitOfWork(db_session, redis_client))
    result = await service.ban_player(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=BanPlayerPayload(user_id=selector.id),
    )

    assert result.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
    assert result.selecting_player_id is None
    assert result.answering_player_id is None
    assert result.timer_deadline is None
    assert not any(player.is_selected for player in result.players)

    resumed = await service.select_starter(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=SelectStarterPayload(user_id=replacement.id),
    )
    assert resumed.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert resumed.selecting_player_id == replacement.id


async def test_ban_active_answerer_reveals_without_score_change_then_recovers(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=2)
    answerer, replacement = seeded.players
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=answerer.id,
            username=answerer.username,
            score=400,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
            is_selected=True,
        ),
        GamePlayerState(
            user_id=replacement.id,
            username=replacement.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = seeded.prompt_ids[0]
    state.selecting_player_id = answerer.id
    state.answering_player_id = answerer.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=30)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    service = GameService(UnitOfWork(db_session, redis_client))
    revealed = await service.ban_player(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=BanPlayerPayload(user_id=answerer.id),
    )

    assert revealed.phase == GamePhaseEnum.ANSWER_REVEAL
    assert revealed.resolution == GameResolutionEnum.UNANSWERED
    assert revealed.players[0].score == 400
    assert revealed.answering_player_id is None
    assert revealed.selecting_player_id is None
    assert revealed.timer_deadline is not None
    assert 4 <= (revealed.timer_deadline - datetime.now(UTC)).total_seconds() <= 5

    revealed.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    await redis_client.set(revealed.key, revealed.model_dump_json())
    recovered = await service.expire_timer(seeded.lobby_id)

    assert recovered is not None
    assert recovered.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
    assert recovered.selecting_player_id is None
    assert recovered.timer_deadline is None


async def test_ban_pending_selector_during_reveal_returns_control_to_host(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=player.id,
            username=player.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.ANSWER_REVEAL
    state.current_prompt_id = seeded.prompt_ids[0]
    state.selecting_player_id = player.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=5)
    state.categories[0].prompts[0].is_selected = True
    state.resolved_prompt_id = seeded.prompt_ids[0]
    state.resolved_answer = "Category 1 A1"
    state.resolution = GameResolutionEnum.CORRECT
    await redis_client.set(state.key, state.model_dump_json())

    service = GameService(UnitOfWork(db_session, redis_client))
    banned = await service.ban_player(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=BanPlayerPayload(user_id=player.id),
    )
    assert banned.phase == GamePhaseEnum.ANSWER_REVEAL
    assert banned.selecting_player_id is None

    banned.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    await redis_client.set(banned.key, banned.model_dump_json())
    recovered = await service.expire_timer(seeded.lobby_id)

    assert recovered is not None
    assert recovered.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER


async def test_ban_selector_during_buzz_keeps_valid_buzzer_active(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=2)
    selector, buzzer = seeded.players
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=selector.id,
            username=selector.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
        GamePlayerState(
            user_id=buzzer.id,
            username=buzzer.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.BUZZ_OPEN
    state.current_prompt_id = seeded.prompt_ids[0]
    state.selecting_player_id = selector.id
    state.attempted_player_ids = [selector.id]
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=10)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    service = GameService(UnitOfWork(db_session, redis_client))
    banned = await service.ban_player(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=BanPlayerPayload(user_id=selector.id),
    )
    assert banned.phase == GamePhaseEnum.BUZZ_OPEN
    assert banned.selecting_player_id is None

    accepted = await service.buzz(lobby_id=seeded.lobby_id, user_id=buzzer.id)
    assert accepted.phase == GamePhaseEnum.PLAYER_ANSWERING
    assert accepted.answering_player_id == buzzer.id


async def test_ban_leaving_no_eligible_buzzer_reveals_immediately(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    player = seeded.players[0]
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=player.id,
            username=player.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.BUZZ_OPEN
    state.current_prompt_id = seeded.prompt_ids[0]
    state.selecting_player_id = player.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=10)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    result = await GameService(UnitOfWork(db_session, redis_client)).ban_player(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=BanPlayerPayload(user_id=player.id),
    )

    assert result.phase == GamePhaseEnum.ANSWER_REVEAL
    assert result.resolution == GameResolutionEnum.UNANSWERED
    assert result.selecting_player_id is None


async def test_buzz_deadline_is_ten_seconds_after_wrong_judgment(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=2)
    answerer, buzzer = seeded.players
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=answerer.id,
            username=answerer.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
        GamePlayerState(
            user_id=buzzer.id,
            username=buzzer.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = seeded.prompt_ids[0]
    state.selecting_player_id = answerer.id
    state.answering_player_id = answerer.id
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=30)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    result = await GameService(UnitOfWork(db_session, redis_client)).judge_answer(
        lobby_id=seeded.lobby_id,
        user_id=seeded.host.id,
        payload=JudgeAnswerPayload(correct=False),
    )

    assert result.phase == GamePhaseEnum.BUZZ_OPEN
    assert result.timer_deadline is not None
    assert 9 <= (result.timer_deadline - datetime.now(UTC)).total_seconds() <= 10


async def test_buzz_deadline_is_ten_seconds_after_answer_timeout(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=2)
    answerer, buzzer = seeded.players
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=answerer.id,
            username=answerer.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
        GamePlayerState(
            user_id=buzzer.id,
            username=buzzer.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = seeded.prompt_ids[0]
    state.selecting_player_id = answerer.id
    state.answering_player_id = answerer.id
    state.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    result = await GameService(UnitOfWork(db_session, redis_client)).expire_timer(seeded.lobby_id)

    assert result is not None
    assert result.phase == GamePhaseEnum.BUZZ_OPEN
    assert result.timer_deadline is not None
    assert 9 <= (result.timer_deadline - datetime.now(UTC)).total_seconds() <= 10


async def test_ban_broadcast_hides_target_from_players_but_not_host(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
):
    seeded = await seed_lobby(player_count=2)
    host, players = await _connect_all(seeded, connect_socket, player_count=2)
    banned, observer = players

    await host.client.emit(
        "ban_player",
        {"user_id": seeded.players[0].id},
        namespace=f"/lobbies/{seeded.lobby_id}",
    )
    host_state = await host.expect("state_changed")
    observer_state = await observer.expect("state_changed")

    host_row = next(
        player for player in host_state["players"] if player["user_id"] == seeded.players[0].id
    )
    assert host_row["is_banned"] is True
    assert all(player["user_id"] != seeded.players[0].id for player in observer_state["players"])

    await asyncio.sleep(0.05)
    assert not banned.client.connected


async def test_expiry_timer_can_advance_from_answer_reveal_to_next_clue(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1, prompts_per_category=2)
    player = seeded.players[0]
    state = seeded.state
    state.players = [
        GamePlayerState(
            user_id=player.id,
            username=player.username,
            connection_status=PlayerConnectionStatusEnum.CONNECTED,
        ),
    ]
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = seeded.prompt_ids[0]
    state.answering_player_id = player.id
    state.selecting_player_id = player.id
    state.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    state.categories[0].prompts[0].is_selected = True
    await redis_client.set(state.key, state.model_dump_json())

    service = GameService(UnitOfWork(db_session, redis_client))
    reveal = await service.expire_timer(seeded.lobby_id)
    assert reveal is not None
    assert reveal.phase == GamePhaseEnum.ANSWER_REVEAL

    reveal.timer_deadline = datetime.now(UTC) - timedelta(seconds=1)
    await redis_client.set(reveal.key, reveal.model_dump_json())
    advanced = await service.expire_timer(seeded.lobby_id)

    assert advanced is not None
    assert advanced.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert advanced.current_prompt_id is None
    assert advanced.timer_deadline is None


async def test_timer_rearming_from_expiry_keeps_new_timer_registered():
    first_callback_resumed = asyncio.Event()
    replacement_registered = asyncio.Event()
    replacement_expired = asyncio.Event()
    scheduled: list[datetime] = []

    async def _expire(_lobby_id: int) -> None:
        scheduled.append(datetime.now(UTC))
        if len(scheduled) == 1:
            game_timers.arm(987654, datetime.now(UTC) + timedelta(milliseconds=100), _expire)
            await asyncio.sleep(0)
            first_callback_resumed.set()
            return
        replacement_expired.set()

    game_timers.arm(987654, datetime.now(UTC) + timedelta(milliseconds=10), _expire)
    try:
        await asyncio.wait_for(first_callback_resumed.wait(), timeout=1)
        await asyncio.sleep(0)
        if 987654 in game_timers._timers:
            replacement_registered.set()
        await asyncio.wait_for(replacement_registered.wait(), timeout=1)
        await asyncio.wait_for(replacement_expired.wait(), timeout=1)
        assert len(scheduled) == 2
    finally:
        game_timers.cancel(987654)


async def test_sleep_until_retries_when_event_loop_wakes_early(
    monkeypatch: pytest.MonkeyPatch,
):
    real_sleep = asyncio.sleep
    sleep_calls: list[float] = []

    async def _sleep(delay: float) -> None:
        sleep_calls.append(delay)
        if len(sleep_calls) == 1:
            return
        await real_sleep(delay)

    monkeypatch.setattr(game_timers.asyncio, "sleep", _sleep)

    deadline = datetime.now(UTC) + timedelta(milliseconds=25)
    await game_timers._sleep_until(deadline)

    assert len(sleep_calls) >= 2
    assert datetime.now(UTC) >= deadline


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
