from datetime import datetime

from pydantic import Field

from enums.lobby import LobbyStateEnum
from schemas.base import BaseSchema, OneFieldSetSchemaMixin
from schemas.pagination import PaginationSchema


class LobbyInDBSchema(BaseSchema):
    id: int
    owner_id: int | None
    state: LobbyStateEnum
    created_at: datetime
    updated_at: datetime


class LobbyCreateSchema(BaseSchema):
    """Empty by design — everything (owner, state, timestamps) is populated server-side."""


class LobbyUpdateSchema(OneFieldSetSchemaMixin):
    state: LobbyStateEnum | None = None
    prompt_category_ids: list[int] | None = None


class LobbyFilterSchema(PaginationSchema):
    ids: list[int] | None = None
    owner_ids: list[int] | None = None
    owner_username: str | None = Field(default=None, min_length=1, max_length=20)
    states: list[LobbyStateEnum] | None = None
    updated_at_start: datetime | None = Field(default=None)
    updated_at_end: datetime | None = Field(default=None)
