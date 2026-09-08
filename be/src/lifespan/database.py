import anyio
from alembic import command
from alembic.config import Config

from configs.settings import settings


async def apply_migrations() -> None:
    """
    Apply database migrations.
    """
    if settings.db_apply_migrations:
        alembic_cfg = Config("alembic.ini")

        def _run_upgrade() -> None:
            command.upgrade(alembic_cfg, "head")

        await anyio.to_thread.run_sync(_run_upgrade)
