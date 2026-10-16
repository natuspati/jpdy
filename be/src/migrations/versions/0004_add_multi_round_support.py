"""Add multi-round games: per-round lobby categories and round results.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16 00:00:00.000000

Existing lobby categories become round 1.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "lobby_round_result",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lobby_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username_snapshot", sa.String(length=256), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("score_delta", sa.Integer(), nullable=False),
        sa.Column("is_banned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["lobby_id"], ["lobby.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "lobby_prompt_category",
        sa.Column("round_number", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("lobby_prompt_category", "round_number")
    op.drop_table("lobby_round_result")
