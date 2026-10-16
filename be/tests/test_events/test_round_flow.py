from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import UnitOfWork
from enums.game import GamePhaseEnum, PlayerConnectionStatusEnum
from enums.lobby import LobbyStateEnum
from fixtures.game_fixtures import SeededLobby, SocketClient
from models.lobby import Lobby, LobbyRoundResult
from repos.game_state import GameStateRepo
from schemas.lobby.game_state import GamePlayerState, GameRoundResult, GameRoundScore
from services.game import GameService
from services.game_projection import GameProjectionService
from test_events.test_game_flow import _connect_all


async def _seed_round_summary(
    seeded: SeededLobby,
    redis_client,
    *,
    scores: list[int],
) -> None:
    state = seeded.state
    state.total_rounds = 2
    state.phase = GamePhaseEnum.ROUND_SUMMARY
    state.timer_deadline = datetime.now(UTC) + timedelta(seconds=10)
    state.players = [
        GamePlayerState(
            user_id=player.id,
            username=player.username,
            score=score,
            connection_status=PlayerConnectionStatusEnum.DISCONNECTED,
        )
        for player, score in zip(seeded.players, scores, strict=False)
    ]
    for category in state.categories:
        for prompt in category.prompts:
            prompt.is_selected = True
    await GameStateRepo(redis_client).save_state(state)


async def test_host_advance_round_event_starts_next_round_with_lowest_scorer(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    connect_socket: Callable[[int, str], Awaitable[SocketClient]],
    redis_client,
):
    seeded = await seed_lobby(player_count=2)
    await _seed_round_summary(seeded, redis_client, scores=[300, -100])
    host, _ = await _connect_all(seeded, connect_socket, player_count=2)

    await host.client.emit("advance_round", namespace=f"/lobbies/{seeded.lobby_id}")
    state = await host.expect("state_changed")

    assert state["phase"] == GamePhaseEnum.PLAYER_SELECTING_PROMPT.value
    assert state["current_round"] == 2
    assert state["selecting_player_id"] == seeded.players[1].id
    assert state["timer_deadline"] is None


async def test_advance_round_service_rejects_non_host_and_wrong_phase(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    service = GameService(UnitOfWork(db_session, redis_client))

    with pytest.raises(Exception, match="Action not allowed during phase"):
        await service.advance_round(lobby_id=seeded.lobby_id, user_id=seeded.host.id)

    await _seed_round_summary(seeded, redis_client, scores=[0])
    with pytest.raises(Exception, match="Only the host"):
        await service.advance_round(lobby_id=seeded.lobby_id, user_id=seeded.players[0].id)


async def test_completion_projection_stores_round_results_idempotently(
    seed_lobby: Callable[..., Awaitable[SeededLobby]],
    db_session: AsyncSession,
    redis_client,
):
    seeded = await seed_lobby(player_count=2)
    first, second = seeded.players
    state = seeded.state
    state.phase = GamePhaseEnum.FINISHED
    state.players = [
        GamePlayerState(user_id=first.id, username=first.username, score=300),
        GamePlayerState(user_id=second.id, username=second.username, score=-50, is_banned=True),
    ]
    state.round_results = [
        GameRoundResult(
            round_number=number,
            scores=[
                GameRoundScore(
                    user_id=first.id,
                    username=first.username,
                    score=100 * number,
                    score_delta=100,
                ),
                GameRoundScore(
                    user_id=second.id,
                    username=second.username,
                    score=-25 * number,
                    score_delta=-25,
                ),
            ],
        )
        for number in (1, 2)
    ]
    projection = GameProjectionService(UnitOfWork(db_session, redis_client))

    await projection.project_completion(state)
    await projection.project_completion(state)

    rows = (
        (
            await db_session.execute(
                select(LobbyRoundResult)
                .where(LobbyRoundResult.lobby_id == seeded.lobby_id)
                .order_by(LobbyRoundResult.round_number, LobbyRoundResult.user_id),
            )
        )
        .scalars()
        .all()
    )
    assert [(r.round_number, r.user_id, r.score, r.score_delta, r.is_banned) for r in rows] == [
        (1, first.id, 100, 100, False),
        (1, second.id, -25, -25, True),
        (2, first.id, 200, 100, False),
        (2, second.id, -50, -25, True),
    ]
    lobby = (
        await db_session.execute(select(Lobby).where(Lobby.id == seeded.lobby_id))
    ).scalar_one()
    assert lobby.state == LobbyStateEnum.COMPLETED.value
