from schemas.lobby.base import LobbyInDBSchema
from schemas.pagination import PaginatedResponseSchema
from schemas.prompt.category import PromptCategoryInDBSchema
from schemas.prompt.nested import PromptCategoryWithPromptsInDBSchema
from schemas.user.base import UserPublicSchema


class LobbyWithCategoriesInDBSchema(LobbyInDBSchema):
    owner: UserPublicSchema | None
    prompt_categories: list[PromptCategoryInDBSchema]


class LobbyWithCategoryPromptsInDBSchema(LobbyInDBSchema):
    owner: UserPublicSchema | None
    prompt_categories: list[PromptCategoryWithPromptsInDBSchema]


class PaginatedLobbyWithCategoriesInDBSchema(
    PaginatedResponseSchema[LobbyWithCategoriesInDBSchema],
):
    pass
