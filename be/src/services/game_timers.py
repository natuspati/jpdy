import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime

_logger = logging.getLogger(__name__)

"""Process-local wakeups complement durable Redis timer schedules."""
_timers: dict[int, asyncio.Task[None]] = {}
_scheduler_task: asyncio.Task[None] | None = None


async def _sleep_until(deadline: datetime) -> None:
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
    cancel(lobby_id)

    async def runner() -> None:
        try:
            await _sleep_until(deadline)
            await on_expire(lobby_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception(f"Timer callback failed for lobby {lobby_id}")
        finally:
            if _timers.get(lobby_id) is asyncio.current_task():
                _timers.pop(lobby_id, None)

    _timers[lobby_id] = asyncio.create_task(runner())


def cancel(lobby_id: int) -> None:
    task = _timers.pop(lobby_id, None)
    if task is not None and task is not asyncio.current_task() and not task.done():
        task.cancel()


def start_scheduler(run_schedule_pass: Callable[[], Awaitable[None]]) -> None:
    """Start one process-local poller over durable Redis timer schedules."""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        return

    async def runner() -> None:
        while True:
            try:
                await run_schedule_pass()
            except asyncio.CancelledError:
                raise
            except Exception:
                _logger.exception("Redis timer scheduler pass failed")
            await asyncio.sleep(1)

    _scheduler_task = asyncio.create_task(runner())


async def stop_scheduler() -> None:
    global _scheduler_task
    task = _scheduler_task
    _scheduler_task = None
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    for lobby_id in list(_timers):
        cancel(lobby_id)
