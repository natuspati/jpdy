from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class PromptCategory(Base):
    __tablename__ = "prompt_category"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column()
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[User | None] = relationship(back_populates="prompt_categories")
    prompts: Mapped[list[Prompt]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    lobbies: Mapped[list[Lobby]] = relationship(
        secondary="lobby_prompt_category",
        back_populates="prompt_categories",
        viewonly=True,
    )
