from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enums.user import UserRole
from models.base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(index=True, unique=True)
    hashed_password: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column(
        String(16),
        default=UserRole.GENERIC,
        server_default=UserRole.GENERIC,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    admin_key_attempted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
    )

    prompt_categories: Mapped[list[PromptCategory]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
    lobbies: Mapped[list[Lobby]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
    lobby_participants: Mapped[list[LobbyParticipant]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    media_assets: Mapped[list[MediaAsset]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
