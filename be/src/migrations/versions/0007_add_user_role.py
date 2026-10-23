"""add_user_role

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-23 12:00:00.000000

Existing users become ``generic`` and get the migration time as ``created_at``
(real registration dates were never stored).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("role", sa.String(length=16), server_default="generic", nullable=False),
    )
    op.add_column(
        "user",
        sa.Column("admin_key_attempted", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # SQLite rejects non-constant defaults on ADD COLUMN: add nullable, backfill, then tighten.
    op.add_column("user", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    user = sa.table("user", sa.column("created_at", sa.DateTime(timezone=True)))
    op.execute(sa.update(user).values(created_at=sa.func.now()))
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("admin_key_attempted")
        batch_op.drop_column("role")
