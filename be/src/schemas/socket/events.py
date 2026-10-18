from enum import StrEnum, auto
from uuid import UUID

from pydantic import Field, StrictBool, StrictInt

from schemas.base import BaseSchema


class SelectStarterPayload(BaseSchema):
    user_id: int
    command_id: UUID | None = None


class SelectPromptPayload(BaseSchema):
    prompt_id: int
    command_id: UUID | None = None


class PlaceBetPayload(BaseSchema):
    amount: int
    command_id: UUID | None = None


class JudgeAnswerPayload(BaseSchema):
    correct: bool
    command_id: UUID | None = None


class BanPlayerPayload(BaseSchema):
    user_id: int
    command_id: UUID | None = None


class UnbanPlayerPayload(BaseSchema):
    user_id: int
    command_id: UUID | None = None


class StartGamePayload(BaseSchema):
    force: bool = False
    command_id: UUID | None = None


class SetAssetsLoadedPayload(BaseSchema):
    loaded: bool
    command_id: UUID | None = None


class SubmitFinalWagerPayload(BaseSchema):
    amount: StrictInt | None = Field(ge=1)
    command_id: UUID | None = None


class SubmitFinalAnswerPayload(BaseSchema):
    answer: str = Field(max_length=256)
    command_id: UUID | None = None


class AdvanceFinalRevealPayload(BaseSchema):
    user_id: int
    command_id: UUID | None = None


class JudgeFinalAnswerPayload(AdvanceFinalRevealPayload):
    correct: StrictBool


class SocketErrorPayload(BaseSchema):
    code: str
    detail: str


class GameSoundCueName(StrEnum):
    GAME_STARTED = auto()
    CLUE_SELECTED = auto()
    BUZZ_ACCEPTED = auto()
    ANSWER_CORRECT = auto()
    ANSWER_WRONG = auto()
    ANSWER_EXPIRED = auto()
    ANSWER_REVEALED = auto()
    GAME_COMPLETED = auto()


class GameSoundCuePayload(BaseSchema):
    cue_id: int = Field(ge=1)
    cue: GameSoundCueName
