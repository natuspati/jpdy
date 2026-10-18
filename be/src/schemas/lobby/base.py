from datetime import datetime

from pydantic import Field

from configs.constants import MAX_BETTING_PROMPTS_PER_ROUND
from enums.lobby import LobbyStateEnum
from schemas.base import BaseSchema, OneFieldSetSchemaMixin
from schemas.pagination import PaginationSchema


class LobbyInDBSchema(BaseSchema):
    id: int
    owner_id: int | None
    state: LobbyStateEnum
    created_at: datetime
    updated_at: datetime
    betting_prompt_count: int | None = None


class LobbyCreateSchema(BaseSchema):
    """Empty by design — everything (owner, state, timestamps) is populated server-side."""


class LobbyUpdateSchema(OneFieldSetSchemaMixin):
    state: LobbyStateEnum | None = None
    rounds: list[list[int]] | None = Field(
        default=None,
        description="Standard category ids for 1-3 normal rounds; index + 1 is the round number.",
    )
    final_category_id: int | None = Field(
        default=None,
        description="Final category id; omitted preserves the selection, null removes it.",
    )
    betting_prompt_count: int | None = Field(
        default=None,
        ge=0,
        le=MAX_BETTING_PROMPTS_PER_ROUND,
        description="Betting prompts per round; null uses the default percentage.",
    )


class LobbyFilterSchema(PaginationSchema):
    ids: list[int] | None = None
    owner_ids: list[int] | None = None
    owner_username: str | None = Field(default=None, min_length=1, max_length=20)
    states: list[LobbyStateEnum] | None = None
    updated_at_start: datetime | None = Field(default=None)
    updated_at_end: datetime | None = Field(default=None)
