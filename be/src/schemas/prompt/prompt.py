from typing import Literal

from pydantic import Field, field_validator

from configs.constants import NUM_PROMPTS_IN_CATEGORY
from enums import AnswerTypeEnum, QuestionTypeEnum
from schemas.base import BaseSchema, OneFieldSetSchemaMixin


class PromptInDBSchema(BaseSchema):
    id: int
    question: str
    question_type: QuestionTypeEnum
    answer: str
    answer_type: AnswerTypeEnum
    category_id: int
    order: int | None


class PromptCreateSchema(BaseSchema):
    question: str = Field(min_length=1, max_length=256)
    question_type: Literal[QuestionTypeEnum.TEXT]
    answer: str = Field(min_length=1, max_length=256)
    answer_type: Literal[AnswerTypeEnum.TEXT]
    order: int = Field(ge=1, le=NUM_PROMPTS_IN_CATEGORY)


class PromptUpdateSchema(OneFieldSetSchemaMixin):
    question: str | None = Field(default=None, min_length=1, max_length=256)
    question_type: Literal[QuestionTypeEnum.TEXT] | None = None
    answer: str | None = Field(default=None, min_length=1, max_length=256)
    answer_type: Literal[AnswerTypeEnum.TEXT] | None = None

    @field_validator(
        "question",
        "question_type",
        "answer",
        "answer_type",
        mode="before",
    )
    @classmethod
    def _reject_explicit_null(cls, v: object) -> object:
        if v is None:
            raise ValueError("must not be null")
        return v
