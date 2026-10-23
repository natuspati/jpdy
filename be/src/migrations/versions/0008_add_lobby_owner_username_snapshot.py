"""add_lobby_owner_username_snapshot

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-23 12:30:00.000000

Filled when a host's account is deleted, so a kept completed lobby still shows
who hosted it.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "lobby",
        sa.Column("owner_username_snapshot", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lobby", "owner_username_snapshot")
