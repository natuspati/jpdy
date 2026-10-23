from schemas.lobby.base import LobbyInDBSchema
from schemas.prompt.category import PromptCategoryInDBSchema
from schemas.user.base import UserRoleSchema


class UserWithPromptsLobbiesPublicSchema(UserRoleSchema):
    prompt_categories: list[PromptCategoryInDBSchema]
    lobbies: list[LobbyInDBSchema]
