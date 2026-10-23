from datetime import datetime

from pydantic import Field

from enums.lobby import LobbyStateEnum
from enums.prompt import PromptCategoryKindEnum
from schemas.base import BaseSchema
from schemas.lobby.base import LobbyInDBSchema
from schemas.pagination import PaginatedResponseSchema
from schemas.prompt.category import PromptCategoryInDBSchema
from schemas.prompt.nested import PromptCategoryWithPromptsInDBSchema
from schemas.user.base import UserPublicSchema


class LobbyActiveListItemSchema(BaseSchema):
    id: int
    host_username: str
    player_count: int
    state: LobbyStateEnum
    created_at: datetime
    can_join: bool = True


class LobbyMineListItemSchema(BaseSchema):
    id: int
    owner_id: int | None
    host_username: str | None
    player_count: int
    state: LobbyStateEnum
    created_at: datetime
    updated_at: datetime
    is_owner: bool
    is_participant: bool


class PaginatedLobbyMineListItemSchema(PaginatedResponseSchema[LobbyMineListItemSchema]):
    pass


class LobbyFinalRankingSchema(BaseSchema):
    user_id: int | None
    username: str
    final_score: int
    is_banned: bool
    rank: int


class LobbyRoundResultSchema(BaseSchema):
    user_id: int | None
    username: str
    score: int
    score_delta: int
    is_banned: bool


class LobbyRoundSchema(BaseSchema):
    round_number: int
    kind: PromptCategoryKindEnum = PromptCategoryKindEnum.STANDARD
    categories: list[PromptCategoryInDBSchema]
    results: list[LobbyRoundResultSchema] | None = None


class LobbyWithCategoriesInDBSchema(LobbyInDBSchema):
    owner: UserPublicSchema | None
    prompt_categories: list[PromptCategoryInDBSchema]
    player_count: int | None = None


class LobbyDetailsSchema(LobbyWithCategoriesInDBSchema):
    is_owner: bool
    is_participant: bool
    final_rankings: list[LobbyFinalRankingSchema] | None = None
    rounds: list[LobbyRoundSchema] = Field(default_factory=list)


class LobbyWithCategoryPromptsInDBSchema(LobbyInDBSchema):
    owner: UserPublicSchema | None
    prompt_categories: list[PromptCategoryWithPromptsInDBSchema]


class PaginatedLobbyWithCategoriesInDBSchema(
    PaginatedResponseSchema[LobbyWithCategoriesInDBSchema],
):
    pass
