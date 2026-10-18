"""add_prompt_category_kind

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-18 22:26:37.975607

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "prompt_category",
        sa.Column("kind", sa.String(length=8), server_default="standard", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("prompt_category", "kind")
