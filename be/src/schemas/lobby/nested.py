from schemas.lobby.base import LobbyInDBSchema
from schemas.pagination import PaginatedResponseSchema
from schemas.prompt.category import PromptCategoryInDBSchema


class LobbyWithCategoriesInDBSchema(LobbyInDBSchema):
    prompt_categories: list[PromptCategoryInDBSchema]


class PaginatedLobbyWithCategoriesInDBSchema(
    PaginatedResponseSchema[LobbyWithCategoriesInDBSchema],
):
    pass
