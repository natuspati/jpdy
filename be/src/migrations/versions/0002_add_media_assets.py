"""Add immutable uploaded media assets and prompt references.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-30 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "media_asset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.String(length=256), nullable=False),
        sa.Column("original_filename", sa.String(length=256), nullable=False),
        sa.Column("media_kind", sa.String(length=256), nullable=False),
        sa.Column("mime_type", sa.String(length=256), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_media_asset_owner_id"), "media_asset", ["owner_id"], unique=False)
    with op.batch_alter_table("prompt") as batch_op:
        batch_op.add_column(sa.Column("question_media_asset_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("answer_media_asset_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_prompt_question_media_asset_id_media_asset",
            "media_asset",
            ["question_media_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_prompt_answer_media_asset_id_media_asset",
            "media_asset",
            ["answer_media_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("prompt") as batch_op:
        batch_op.drop_constraint(
            "fk_prompt_answer_media_asset_id_media_asset",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_prompt_question_media_asset_id_media_asset",
            type_="foreignkey",
        )
        batch_op.drop_column("answer_media_asset_id")
        batch_op.drop_column("question_media_asset_id")
    op.drop_index(op.f("ix_media_asset_owner_id"), table_name="media_asset")
    op.drop_table("media_asset")
