from polyfactory.factories.pydantic_factory import ModelFactory

from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from schemas.prompt.category import (
    PromptCategoryCreateSchema,
    PromptCategoryUpdateSchema,
)
from schemas.prompt.prompt import PromptCreateSchema, PromptUpdateSchema


class PromptCategoryCreateSchemaFactory(ModelFactory[PromptCategoryCreateSchema]):
    __model__ = PromptCategoryCreateSchema


class PromptCategoryUpdateSchemaFactory(ModelFactory[PromptCategoryUpdateSchema]):
    __model__ = PromptCategoryUpdateSchema


class PromptCreateSchemaFactory(ModelFactory[PromptCreateSchema]):
    __model__ = PromptCreateSchema
    question_type = QuestionTypeEnum.TEXT
    answer_type = AnswerTypeEnum.TEXT
    question_media_asset_id = None
    answer_media_asset_id = None


class PromptUpdateSchemaFactory(ModelFactory[PromptUpdateSchema]):
    __model__ = PromptUpdateSchema
