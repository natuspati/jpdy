from sqlalchemy import ForeignKey, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Prompt(Base):
    __tablename__ = "prompt"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column()
    question_type: Mapped[str] = mapped_column()
    answer: Mapped[str] = mapped_column()
    answer_type: Mapped[str] = mapped_column()
    category_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_category.id", ondelete="CASCADE"),
    )
    order: Mapped[int | None] = mapped_column(SmallInteger)

    category: Mapped[PromptCategory] = relationship(back_populates="prompts")
