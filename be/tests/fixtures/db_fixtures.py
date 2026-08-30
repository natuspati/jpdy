from collections.abc import AsyncGenerator, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import sqlalchemy
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from configs.settings import settings
from database.session import configure_sqlite_foreign_keys


@contextmanager
def _patched_sync_url(sync_url: sqlalchemy.URL) -> Iterator[None]:
    """
    Temporarily swap ``settings.db_sync_url`` so Alembic's ``env.py`` (which
    reads from settings) targets the per-test DB instead of the development
    file. ``db_sync_url`` is a ``cached_property``, so we mutate ``__dict__``
    directly and restore the prior cache state on exit.
    """
    sentinel = object()
    previous = settings.__dict__.get("db_sync_url", sentinel)
    settings.__dict__["db_sync_url"] = sync_url
    try:
        yield
    finally:
        if previous is sentinel:
            settings.__dict__.pop("db_sync_url", None)
        else:
            settings.__dict__["db_sync_url"] = previous


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Unique SQLite file for the test (auto-cleaned by ``tmp_path``)."""
    return tmp_path / "test_jpdy.db"


@pytest.fixture
def _migrate_db(db_path: Path) -> None:
    """Apply ``alembic upgrade head`` against the per-test DB file."""
    sync_url = sqlalchemy.URL.create("sqlite", database=str(db_path))
    cfg = Config("alembic.ini")
    with _patched_sync_url(sync_url):
        command.upgrade(cfg, "head")


@pytest.fixture
async def test_engine(
    db_path: Path,
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncEngine]:
    """Async engine bound to the migrated per-test DB file."""
    request.getfixturevalue("_migrate_db")
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        future=True,
    )
    configure_sqlite_foreign_keys(engine)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def db_session_maker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the per-test engine."""
    return async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(
    db_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """One ad-hoc session for tests that need to seed or inspect DB state."""
    async with db_session_maker() as session:
        yield session
