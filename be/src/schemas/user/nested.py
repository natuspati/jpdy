from schemas.lobby.base import LobbyInDBSchema
from schemas.prompt.category import PromptCategoryInDBSchema
from schemas.user.base import UserPublicSchema


class UserWithPromptsLobbiesPublicSchema(UserPublicSchema):
    prompt_categories: list[PromptCategoryInDBSchema]
    lobbies: list[LobbyInDBSchema]
