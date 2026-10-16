"""Add per-lobby betting prompt count.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-16 00:00:00.000000

NULL means "use the default percentage of each round's prompts".
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column("lobby", sa.Column("betting_prompt_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("lobby", "betting_prompt_count")
