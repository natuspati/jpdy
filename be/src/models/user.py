from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(index=True, unique=True)
    hashed_password: Mapped[str] = mapped_column()

    prompt_categories: Mapped[list[PromptCategory]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
    lobbies: Mapped[list[Lobby]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
