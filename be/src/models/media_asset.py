from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class MediaAsset(Base):
    __tablename__ = "media_asset"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(unique=True)
    original_filename: Mapped[str] = mapped_column()
    media_kind: Mapped[str] = mapped_column()
    mime_type: Mapped[str] = mapped_column()
    byte_size: Mapped[int] = mapped_column()
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    owner: Mapped[User | None] = relationship(back_populates="media_assets")
    question_prompts: Mapped[list[Prompt]] = relationship(
        foreign_keys="Prompt.question_media_asset_id",
        back_populates="question_media_asset",
    )
    answer_prompts: Mapped[list[Prompt]] = relationship(
        foreign_keys="Prompt.answer_media_asset_id",
        back_populates="answer_media_asset",
    )
