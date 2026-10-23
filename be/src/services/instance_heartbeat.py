import asyncio
import json
import logging
import resource
import socket
import sys
import uuid
from contextlib import suppress
from datetime import UTC, datetime

from redis.asyncio import Redis

from configs import settings
from configs.constants import (
    INSTANCE_HEARTBEAT_INTERVAL_SECONDS,
    INSTANCE_HEARTBEAT_TTL_SECONDS,
    INSTANCE_KEY_PREFIX,
)
from database.session import redis_pool

_logger = logging.getLogger(__name__)

_instance_id = uuid.uuid4().hex
_started_at = datetime.now(UTC)
_task: asyncio.Task[None] | None = None


def _peak_rss_bytes() -> int:
    # ponytail: ru_maxrss is the peak, not current, RSS (kB on Linux, bytes on macOS)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


async def publish_heartbeat(redis: Redis) -> None:
    payload = {
        "id": _instance_id,
        "hostname": socket.gethostname(),
        "version": settings.version,
        "started_at": _started_at.isoformat(),
        "rss_bytes": _peak_rss_bytes(),
    }
    await redis.set(
        f"{INSTANCE_KEY_PREFIX}{_instance_id}",
        json.dumps(payload),
        ex=INSTANCE_HEARTBEAT_TTL_SECONDS,
    )


def start_heartbeat() -> None:
    global _task
    if _task is not None and not _task.done():
        return

    async def runner() -> None:
        redis = Redis(connection_pool=redis_pool)
        while True:
            try:
                await publish_heartbeat(redis)
            except asyncio.CancelledError:
                raise
            except Exception:
                _logger.exception("Instance heartbeat failed")
            await asyncio.sleep(INSTANCE_HEARTBEAT_INTERVAL_SECONDS)

    _task = asyncio.create_task(runner())


async def stop_heartbeat() -> None:
    global _task
    task, _task = _task, None
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
