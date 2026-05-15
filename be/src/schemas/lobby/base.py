from datetime import datetime

from enums.lobby import LobbyStateEnum
from schemas.base import BaseSchema


class LobbyInDBSchema(BaseSchema):
    id: int
    owner_id: int | None
    state: LobbyStateEnum
    created_at: datetime
    updated_at: datetime
