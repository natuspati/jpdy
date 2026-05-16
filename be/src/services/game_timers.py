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
    remaining = (deadline - datetime.now(UTC)).total_seconds()
    if remaining > 0:
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
            _timers.pop(lobby_id, None)

    _timers[lobby_id] = asyncio.create_task(_runner())


def cancel(lobby_id: int) -> None:
    task = _timers.pop(lobby_id, None)
    if task is not None and not task.done():
        task.cancel()
