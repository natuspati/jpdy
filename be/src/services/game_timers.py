import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

_logger = logging.getLogger(__name__)

# Single-process registry of per-lobby timer tasks. The current Socket.IO
# deployment runs in one process, so an in-memory dict is enough. Sharding
# across processes would require moving deadlines into Redis with key
# expiration + a notification channel.
_timers: dict[int, asyncio.Task] = {}


async def _sleep_until(deadline: datetime) -> None:
    # Event loops may run a scheduled callback a few clock-resolution ticks
    # before its requested delay. ``expire_timer`` correctly ignores a state
    # whose deadline has not arrived yet, but a one-shot timer would then be
    # lost until another socket event re-armed it. Recheck wall-clock time
    # after every sleep so callbacks never run early.
    while True:
        remaining = (deadline - datetime.now(UTC)).total_seconds()
        if remaining <= 0:
            return
        await asyncio.sleep(remaining)


def arm(
    lobby_id: int,
    deadline: datetime,
    on_expire: Callable[[int], Awaitable[None]],
) -> None:
    """
    Schedule ``on_expire(lobby_id)`` to run when ``deadline`` is reached.
    Cancels any timer already armed for ``lobby_id`` first.
    """
    cancel(lobby_id)

    async def _runner() -> None:
        try:
            await _sleep_until(deadline)
            await on_expire(lobby_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception("Timer callback failed for lobby %s", lobby_id)
        finally:
            # ``on_expire`` can transition into another timed phase. In that
            # case it arms a replacement timer before this runner finishes;
            # never remove that newer task from the registry.
            if _timers.get(lobby_id) is asyncio.current_task():
                _timers.pop(lobby_id, None)

    _timers[lobby_id] = asyncio.create_task(_runner())


def cancel(lobby_id: int) -> None:
    task = _timers.pop(lobby_id, None)
    # Timer-expiry callbacks re-arm the next phase timer themselves. Do not
    # cancel the task currently running that callback, or its next await
    # raises ``CancelledError`` and prevents the newly armed timer from
    # completing its transition.
    if task is not None and task is not asyncio.current_task() and not task.done():
        task.cancel()
