from datetime import datetime

from schemas.base import BaseSchema


class LobbyParticipantInDBSchema(BaseSchema):
    id: int
    lobby_id: int
    user_id: int | None
    username_snapshot: str
    joined_at: datetime
    is_banned: bool
    final_score: int | None
