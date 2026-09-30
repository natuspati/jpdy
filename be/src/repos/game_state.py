from collections.abc import Callable
from datetime import datetime

from redis.asyncio import Redis
from redis.asyncio.client import Pipeline
from redis.exceptions import WatchError

from schemas.lobby.game_state import GameLobbyState
from utils.game_state import (
    GameCommandOutcome,
    game_command_key,
    game_connection_key,
    game_events_key,
    game_state_key,
    game_timer_schedule_key,
    set_timer_revision,
    timer_schedule_member,
)


class GameStateRepo:
    """Redis-authoritative live state with optimistic command serialization."""

    _COMMAND_TTL_SECONDS = 60 * 60
    _MAX_WATCH_RETRIES = 12

    def __init__(self, redis: Redis):
        self._redis = redis

    async def get_state(self, lobby_id: int) -> GameLobbyState | None:
        raw = await self._redis.get(game_state_key(lobby_id))
        if raw is None:
            return None
        return GameLobbyState.model_validate_json(raw)

    async def save_state(self, state: GameLobbyState) -> None:
        """Bootstrap/test helper. Live commands must use :meth:`execute`."""
        previous = await self.get_state(state.lobby_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(game_state_key(state.lobby_id), state.model_dump_json())
            self._queue_timer_schedule(pipe, state, previous)
            await pipe.execute()

    async def initialize_state(self, state: GameLobbyState) -> GameLobbyState:
        """Create materialized lobby once without clobbering active game."""
        state_key = game_state_key(state.lobby_id)
        created = await self._redis.set(state_key, state.model_dump_json(), nx=True)
        if not created:
            existing = await self.get_state(state.lobby_id)
            if existing is None:
                raise RuntimeError(
                    f"Game state disappeared while initializing lobby {state.lobby_id}",
                )
            return existing
        async with self._redis.pipeline(transaction=True) as pipe:
            self._queue_timer_schedule(pipe, state, None)
            await pipe.execute()
        return state

    async def delete_state(self, lobby_id: int) -> None:
        state = await self.get_state(lobby_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(
                game_state_key(lobby_id),
                game_events_key(lobby_id),
                game_timer_schedule_key(lobby_id),
            )
            if state is not None:
                old_timer = timer_schedule_member(state)
                if old_timer is not None:
                    pipe.zrem(game_timer_schedule_key(lobby_id), old_timer)
            await pipe.execute()

    async def execute(
        self,
        lobby_id: int,
        command_id: str,
        command_name: str,
        transition: Callable[[GameLobbyState], GameCommandOutcome],
    ) -> GameLobbyState | None:
        """Commit state, dedup result, event, and timer schedule atomically."""
        state_key = game_state_key(lobby_id)
        command_key = game_command_key(lobby_id, command_id)

        for _ in range(self._MAX_WATCH_RETRIES):
            async with self._redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(state_key, command_key)
                    cached = await pipe.get(command_key)
                    if cached is not None:
                        return GameLobbyState.model_validate_json(cached)

                    raw_state = await pipe.get(state_key)
                    if raw_state is None:
                        raise GameStateMissingError(lobby_id)
                    current = GameLobbyState.model_validate_json(raw_state)
                    outcome = transition(current)
                    if outcome.state is None:
                        return outcome.result

                    next_state = outcome.state
                    next_state.state_revision = current.state_revision + 1
                    set_timer_revision(next_state)

                    pipe.multi()
                    pipe.set(state_key, next_state.model_dump_json())
                    pipe.set(
                        command_key,
                        _serialize_game_state(outcome.result),
                        ex=self._COMMAND_TTL_SECONDS,
                    )
                    pipe.xadd(
                        game_events_key(lobby_id),
                        {
                            "command_id": command_id,
                            "command": command_name,
                            "reason": outcome.reason,
                            "revision": str(next_state.state_revision),
                            "state": next_state.model_dump_json(),
                        },
                    )
                    self._queue_timer_schedule(pipe, next_state, current)
                    await pipe.execute()
                    return outcome.result
                except WatchError:
                    continue

        raise GameStateConflictError(lobby_id)

    async def due_timer_members(self, lobby_id: int, now: datetime) -> list[str]:
        raw = await self._redis.zrangebyscore(
            game_timer_schedule_key(lobby_id),
            min="-inf",
            max=now.timestamp(),
        )
        return [item.decode() if isinstance(item, bytes) else item for item in raw]

    async def remove_timer_member(self, lobby_id: int, member: str) -> None:
        await self._redis.zrem(game_timer_schedule_key(lobby_id), member)

    async def get_connection_sid(self, lobby_id: int, user_id: int) -> str | None:
        raw = await self._redis.get(game_connection_key(lobby_id, user_id))
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    async def swap_connection_sid(self, lobby_id: int, user_id: int, sid: str) -> str | None:
        """Atomically claim ownership; returns the sid it replaced, if any."""
        raw = await self._redis.set(game_connection_key(lobby_id, user_id), sid, get=True)
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    async def clear_connection_sid(
        self,
        lobby_id: int,
        user_id: int,
        expected_sid: str,
    ) -> bool:
        """Fenced cleanup: old socket cannot remove newer reconnect ownership."""
        key = game_connection_key(lobby_id, user_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(key)
                raw = await pipe.get(key)
                actual_sid = raw.decode() if isinstance(raw, bytes) else raw
                if actual_sid != expected_sid:
                    return False
                pipe.multi()
                pipe.delete(key)
                await pipe.execute()
                return True
            except WatchError:
                return False

    async def scan_active_lobby_ids(self) -> list[int]:
        lobby_ids: list[int] = []
        async for raw_key in self._redis.scan_iter(match="game:*:state"):
            key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
            if not key.startswith("game:{") or not key.endswith("}:state"):
                continue
            lobby_id = key.removeprefix("game:{").removesuffix("}:state")
            if lobby_id.isdigit():
                lobby_ids.append(int(lobby_id))
        return lobby_ids

    async def reconcile_timer_schedule(self) -> None:
        """Recreate timer sorted-set entries after worker/process restart."""
        for lobby_id in await self.scan_active_lobby_ids():
            state = await self.get_state(lobby_id)
            if state is None:
                continue
            member = timer_schedule_member(state)
            if member is None or state.timer_deadline is None:
                continue
            await self._redis.zadd(
                game_timer_schedule_key(lobby_id),
                {member: state.timer_deadline.timestamp()},
            )

    def _queue_timer_schedule(
        self,
        pipe: Pipeline,
        state: GameLobbyState,
        previous: GameLobbyState | None,
    ) -> None:
        if previous is not None:
            old_member = timer_schedule_member(previous)
            if old_member is not None:
                pipe.zrem(game_timer_schedule_key(state.lobby_id), old_member)
        member = timer_schedule_member(state)
        if member is not None and state.timer_deadline is not None:
            pipe.zadd(
                game_timer_schedule_key(state.lobby_id),
                {member: state.timer_deadline.timestamp()},
            )


def _serialize_game_state(state: GameLobbyState | None) -> str:
    if state is None:
        raise TypeError("Accepted game commands must return a game state")
    return state.model_dump_json()


class GameStateMissingError(RuntimeError):
    def __init__(self, lobby_id: int):
        super().__init__(f"Game state for lobby {lobby_id} not found")


class GameStateConflictError(RuntimeError):
    def __init__(self, lobby_id: int):
        super().__init__(f"Game state for lobby {lobby_id} is busy; retry the command")
