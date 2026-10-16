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


class LobbyRoundResultInDBSchema(BaseSchema):
    id: int
    lobby_id: int
    round_number: int
    user_id: int | None
    username_snapshot: str
    score: int
    score_delta: int
    is_banned: bool
