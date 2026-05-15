from enums import AnswerTypeEnum, QuestionTypeEnum
from schemas.base import BaseSchema


class PromptInDBSchema(BaseSchema):
    id: int
    question: str
    question_type: QuestionTypeEnum
    answer: str
    answer_type: AnswerTypeEnum
    category_id: int
    order: int | None
