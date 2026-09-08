from schemas.pagination import PaginatedResponseSchema
from schemas.prompt.category import PromptCategoryInDBSchema
from schemas.prompt.prompt import PromptInDBSchema, PromptResponseSchema


class PromptCategoryWithPromptsInDBSchema(PromptCategoryInDBSchema):
    prompts: list[PromptInDBSchema]


class PaginatedPromptCategoryWithPromptsInDBSchema(
    PaginatedResponseSchema[PromptCategoryWithPromptsInDBSchema],
):
    pass


class PromptCategoryResponseSchema(PromptCategoryInDBSchema):
    prompts: list[PromptResponseSchema]


class PaginatedPromptCategoryResponseSchema(
    PaginatedResponseSchema[PromptCategoryResponseSchema],
):
    pass
