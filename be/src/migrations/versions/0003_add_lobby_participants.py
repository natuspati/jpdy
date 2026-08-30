"""Add persistent lobby membership and final scores.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-30 00:00:00.000000

Existing Redis-only rosters cannot be backfilled reliably. They remain playable,
but appear in participant history only after a player reconnects or completion
snapshots their final score.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "lobby_participant",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lobby_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username_snapshot", sa.String(length=256), nullable=False),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "is_banned",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["lobby_id"], ["lobby.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lobby_id", "user_id", name="uq_lobby_participant_lobby_user"),
    )
    op.create_index(
        op.f("ix_lobby_participant_user_id"),
        "lobby_participant",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lobby_participant_user_id"), table_name="lobby_participant")
    op.drop_table("lobby_participant")
