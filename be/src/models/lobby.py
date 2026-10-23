from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint, false, func
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
    round_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class LobbyRoundResult(Base):
    __tablename__ = "lobby_round_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lobby_id: Mapped[int] = mapped_column(ForeignKey("lobby.id", ondelete="CASCADE"))
    round_number: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    username_snapshot: Mapped[str] = mapped_column()
    score: Mapped[int] = mapped_column(Integer)
    score_delta: Mapped[int] = mapped_column(Integer)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class Lobby(Base):
    __tablename__ = "lobby"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
    )
    state: Mapped[str] = mapped_column()
    owner_username_snapshot: Mapped[str | None] = mapped_column()
    betting_prompt_count: Mapped[int | None] = mapped_column(Integer)
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
    participants: Mapped[list[LobbyParticipant]] = relationship(
        back_populates="lobby",
        passive_deletes=True,
    )


class LobbyParticipant(Base):
    __tablename__ = "lobby_participant"
    __table_args__ = (
        UniqueConstraint("lobby_id", "user_id", name="uq_lobby_participant_lobby_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lobby_id: Mapped[int] = mapped_column(
        ForeignKey("lobby.id", ondelete="CASCADE"),
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )
    username_snapshot: Mapped[str] = mapped_column()
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    final_score: Mapped[int | None] = mapped_column(Integer)

    lobby: Mapped[Lobby] = relationship(back_populates="participants")
    user: Mapped[User | None] = relationship(back_populates="lobby_participants")
