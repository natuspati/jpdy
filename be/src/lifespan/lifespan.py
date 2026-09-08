import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lifespan.database import apply_migrations
from services import game_timers
from sockets.timer_hooks import run_redis_schedule_pass

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Context manager to manage the lifecycle of a FastAPI application.

    Upon entering the context, it runs the startup events, and upon exiting,
    it runs the shutdown events.

    :param app: FastAPI application instance to manage
    :yield:
    """
    await run_startup_events(app)
    try:
        yield
    finally:
        await run_shutdown_events(app)


async def run_startup_events(app: FastAPI) -> None:
    """
    Perform startup events.

    :param app: application
    :return:
    """
    await apply_migrations()
    game_timers.start_scheduler(run_redis_schedule_pass)


async def run_shutdown_events(app: FastAPI) -> None:
    """
    Perform shutdown events.

    :param app: application
    :return:
    """
    await game_timers.stop_scheduler()
