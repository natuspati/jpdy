from datetime import datetime

from pydantic import Field, computed_field

from configs.constants import SCORE_MULTIPLIER
from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from schemas.base import BaseSchema
from schemas.media import MediaReferenceSchema


class GameHostState(BaseSchema):
    user_id: int
    username: str
    connection_status: PlayerConnectionStatusEnum = PlayerConnectionStatusEnum.DISCONNECTED


class GamePlayerState(BaseSchema):
    user_id: int
    username: str
    score: int = 0
    connection_status: PlayerConnectionStatusEnum = PlayerConnectionStatusEnum.DISCONNECTED
    is_selected: bool = Field(
        default=False,
        description="Whether player is active for current game phase.",
    )
    is_banned: bool = False


class GamePromptState(BaseSchema):
    """Internal persisted prompt snapshot. Never send this model to clients."""

    prompt_id: int
    question: str
    answer: str
    question_type: QuestionTypeEnum = QuestionTypeEnum.TEXT
    answer_type: AnswerTypeEnum = AnswerTypeEnum.TEXT
    question_media: MediaReferenceSchema | None = None
    answer_media: MediaReferenceSchema | None = None
    order: int
    is_selected: bool = False

    @computed_field
    @property
    def score_value(self) -> int:
        return self.order * SCORE_MULTIPLIER


class GameCategoryState(BaseSchema):
    category_id: int
    name: str
    prompts: list[GamePromptState]


class PublicGamePromptState(BaseSchema):
    """Player-visible prompt state. Expected answer is intentionally absent."""

    prompt_id: int
    question: str
    question_type: QuestionTypeEnum = QuestionTypeEnum.TEXT
    question_media: MediaReferenceSchema | None = None
    order: int
    is_selected: bool = False

    @computed_field
    @property
    def score_value(self) -> int:
        return self.order * SCORE_MULTIPLIER


class PublicGameCategoryState(BaseSchema):
    category_id: int
    name: str
    prompts: list[PublicGamePromptState]


class PublicGameLobbyState(BaseSchema):
    """Player-visible game snapshot sent with every ``state_changed`` frame."""

    lobby_id: int
    state_revision: int = Field(
        default=0,
        ge=0,
        description="Monotonic state version used to discard stale snapshots.",
    )
    host: GameHostState
    players: list[GamePlayerState] = Field(default_factory=list)
    categories: list[PublicGameCategoryState] = Field(default_factory=list)
    phase: GamePhaseEnum = GamePhaseEnum.WAITING_FOR_PLAYERS
    current_prompt_id: int | None = None
    selecting_player_id: int | None = None
    answering_player_id: int | None = None
    attempted_player_ids: list[int] = Field(
        default_factory=list,
        description="Visible players who already failed the active prompt.",
    )
    timer_deadline: datetime | None = None
    resolved_prompt_id: int | None = Field(
        default=None,
        description="Prompt revealed during answer-reveal phase.",
    )
    resolved_answer: str | None = Field(
        default=None,
        description="Expected answer visible only during answer-reveal phase.",
    )
    resolved_answer_type: AnswerTypeEnum | None = Field(
        default=None,
        description="Content type of revealed answer.",
    )
    resolved_answer_media: MediaReferenceSchema | None = Field(
        default=None,
        description="Media attached to revealed answer.",
    )
    resolution: GameResolutionEnum | None = Field(
        default=None,
        description="How current prompt was resolved.",
    )
    latest_sound_cue_id: int = 0


class HostAnswerKey(BaseSchema):
    """Private answer key emitted only to host during spoken answers."""

    lobby_id: int
    prompt_id: int
    expected_answer: str


class GameLobbyState(BaseSchema):
    """Internal Redis state, including expected prompt answers."""

    lobby_id: int
    state_revision: int = Field(
        default=0,
        ge=0,
        description="Monotonic revision incremented for each accepted command.",
    )
    host: GameHostState
    players: list[GamePlayerState] = Field(default_factory=list)
    categories: list[GameCategoryState] = Field(default_factory=list)
    phase: GamePhaseEnum = GamePhaseEnum.WAITING_FOR_PLAYERS
    current_prompt_id: int | None = None
    selecting_player_id: int | None = None
    answering_player_id: int | None = None
    attempted_player_ids: list[int] = Field(
        default_factory=list,
        description="Players who failed current prompt; cleared for next prompt.",
    )
    timer_deadline: datetime | None = None
    timer_revision: int | None = Field(
        default=None,
        ge=0,
        description="State revision that armed timer deadline for stale-timer fencing.",
    )
    resolved_prompt_id: int | None = Field(
        default=None,
        description="Prompt whose answer is awaiting public reveal.",
    )
    resolved_answer: str | None = Field(
        default=None,
        description="Expected answer held until answer-reveal phase.",
    )
    resolved_answer_type: AnswerTypeEnum | None = Field(
        default=None,
        description="Content type of pending revealed answer.",
    )
    resolved_answer_media: MediaReferenceSchema | None = Field(
        default=None,
        description="Media attached to pending revealed answer.",
    )
    resolution: GameResolutionEnum | None = Field(
        default=None,
        description="Outcome assigned to current prompt resolution.",
    )
    sound_cue_id: int = 0
