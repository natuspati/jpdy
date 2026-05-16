from schemas.pagination import PaginatedResponseSchema
from schemas.prompt.category import PromptCategoryInDBSchema
from schemas.prompt.prompt import PromptInDBSchema


class PromptCategoryWithPromptsInDBSchema(PromptCategoryInDBSchema):
    prompts: list[PromptInDBSchema]


class PaginatedPromptCategoryWithPromptsInDBSchema(
    PaginatedResponseSchema[PromptCategoryWithPromptsInDBSchema],
):
    pass
