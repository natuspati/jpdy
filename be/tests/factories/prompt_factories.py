from polyfactory.factories.pydantic_factory import ModelFactory

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


class PromptUpdateSchemaFactory(ModelFactory[PromptUpdateSchema]):
    __model__ = PromptUpdateSchema
