from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class LobbyPromptCategory(Base):
    __tablename__ = "lobby_prompt_category"

    lobby_id: Mapped[int] = mapped_column(
        ForeignKey("lobby.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prompt_category_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_category.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Lobby(Base):
    __tablename__ = "lobby"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
    )
    state: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[User | None] = relationship(back_populates="lobbies")
    prompt_categories: Mapped[list[PromptCategory]] = relationship(
        secondary=LobbyPromptCategory.__table__,
        back_populates="lobbies",
        viewonly=True,
    )
