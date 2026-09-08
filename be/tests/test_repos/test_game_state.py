import asyncio
from datetime import UTC, datetime, timedelta

from fakeredis import FakeAsyncRedis

from enums.game import GamePhaseEnum, PlayerConnectionStatusEnum
from errors.request import BadRequestError
from repos.game_state import GameStateRepo, GameTransition
from schemas.lobby.game_state import GameHostState, GameLobbyState, GamePlayerState


async def test_execute_serializes_simultaneous_buzzes(
    redis_client: FakeAsyncRedis,
) -> None:
    repo = GameStateRepo(redis_client)
    deadline = datetime.now(UTC) + timedelta(seconds=10)
    state = GameLobbyState(
        lobby_id=42,
        host=GameHostState(user_id=1, username="host"),
        players=[
            GamePlayerState(
                user_id=2,
                username="alice",
                connection_status=PlayerConnectionStatusEnum.CONNECTED,
            ),
            GamePlayerState(
                user_id=3,
                username="bob",
                connection_status=PlayerConnectionStatusEnum.CONNECTED,
            ),
        ],
        phase=GamePhaseEnum.BUZZ_OPEN,
        timer_deadline=deadline,
        timer_revision=0,
    )
    await repo.save_state(state)
    barrier = asyncio.Barrier(2)

    def buzz_transition(user_id: int):
        def transition(current: GameLobbyState) -> GameTransition[GameLobbyState]:
            if current.phase != GamePhaseEnum.BUZZ_OPEN:
                raise BadRequestError("Buzz is already closed")
            current.phase = GamePhaseEnum.PLAYER_ANSWERING
            current.answering_player_id = user_id
            return GameTransition(current, current, "buzz_accepted")

        return transition

    async def buzz(user_id: int) -> GameLobbyState:
        await barrier.wait()
        return await repo.execute(
            lobby_id=42,
            command_id=f"buzz-{user_id}",
            command_name="buzz",
            transition=buzz_transition(user_id),
        )

    outcomes = await asyncio.gather(buzz(2), buzz(3), return_exceptions=True)
    accepted = [outcome for outcome in outcomes if isinstance(outcome, GameLobbyState)]
    rejected = [outcome for outcome in outcomes if isinstance(outcome, BadRequestError)]

    assert len(accepted) == 1
    assert len(rejected) == 1
    persisted = await repo.get_state(42)
    assert persisted is not None
    assert persisted.answering_player_id == accepted[0].answering_player_id
    assert persisted.state_revision == 1
    events = await redis_client.xrange(GameStateRepo.events_key(42))
    assert len(events) == 1


async def test_execute_deduplicates_command_id(
    redis_client: FakeAsyncRedis,
) -> None:
    repo = GameStateRepo(redis_client)
    state = GameLobbyState(lobby_id=7, host=GameHostState(user_id=1, username="host"))
    await repo.save_state(state)
    calls = 0

    def transition(current: GameLobbyState) -> GameTransition[GameLobbyState]:
        nonlocal calls
        calls += 1
        current.sound_cue_id += 1
        return GameTransition(current, current, "sound_cue")

    first = await repo.execute(7, "same-command", "sound", transition)
    second = await repo.execute(7, "same-command", "sound", transition)

    assert calls == 1
    assert first.state_revision == second.state_revision == 1
    assert second.sound_cue_id == 1
    assert len(await redis_client.xrange(GameStateRepo.events_key(7))) == 1
