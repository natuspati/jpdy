"""Create user, lobby and promp tables.

Revision ID: 0001
Revises:
Create Date: 2026-05-15 17:07:01.621923

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=256), nullable=False),
        sa.Column("hashed_password", sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)
    op.create_table(
        "lobby",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "prompt_category",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lobby_prompt_category",
        sa.Column("lobby_id", sa.Integer(), nullable=False),
        sa.Column("prompt_category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lobby_id"], ["lobby.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_category_id"], ["prompt_category.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("lobby_id", "prompt_category_id"),
    )
    op.create_table(
        "prompt",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question", sa.String(length=256), nullable=False),
        sa.Column("question_type", sa.String(length=256), nullable=False),
        sa.Column("answer", sa.String(length=256), nullable=False),
        sa.Column("answer_type", sa.String(length=256), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["prompt_category.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("prompt")
    op.drop_table("lobby_prompt_category")
    op.drop_table("prompt_category")
    op.drop_table("lobby")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_table("user")
