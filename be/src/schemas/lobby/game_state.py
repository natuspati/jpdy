from datetime import datetime
from functools import cached_property

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
    # Whether this player is currently the active actor; meaning depends on
    # the lobby's GamePhaseEnum (e.g. picking a prompt vs. answering one).
    is_selected: bool = False
    is_banned: bool = False


class GamePromptState(BaseSchema):
    """Internal, persisted prompt snapshot. Never send this model to clients."""

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
    @cached_property
    def score_value(self) -> int:
        return self.order * SCORE_MULTIPLIER


class GameCategoryState(BaseSchema):
    category_id: int
    name: str
    prompts: list[GamePromptState]


class PublicGamePromptState(BaseSchema):
    """Player-visible prompt state. The expected answer is intentionally absent."""

    prompt_id: int
    question: str
    question_type: QuestionTypeEnum = QuestionTypeEnum.TEXT
    question_media: MediaReferenceSchema | None = None
    order: int
    is_selected: bool = False

    @computed_field
    @cached_property
    def score_value(self) -> int:
        return self.order * SCORE_MULTIPLIER


class PublicGameCategoryState(BaseSchema):
    category_id: int
    name: str
    prompts: list[PublicGamePromptState]


class PublicGameLobbyState(BaseSchema):
    """Full player-visible game snapshot sent with every ``state_changed`` frame."""

    lobby_id: int
    # Client snapshots are whole documents. Recipients discard a frame whose
    # revision is older than one they have already rendered.
    state_revision: int = Field(default=0, ge=0)
    host: GameHostState
    players: list[GamePlayerState] = Field(default_factory=list)
    categories: list[PublicGameCategoryState] = Field(default_factory=list)
    phase: GamePhaseEnum = GamePhaseEnum.WAITING_FOR_PLAYERS
    current_prompt_id: int | None = None
    selecting_player_id: int | None = None
    answering_player_id: int | None = None
    attempted_player_ids: list[int] = Field(default_factory=list)
    timer_deadline: datetime | None = None
    resolved_prompt_id: int | None = None
    resolved_answer: str | None = None
    resolved_answer_type: AnswerTypeEnum | None = None
    resolved_answer_media: MediaReferenceSchema | None = None
    resolution: GameResolutionEnum | None = None
    latest_sound_cue_id: int = 0


class HostAnswerKey(BaseSchema):
    """Private answer key emitted only to the host during spoken answers."""

    lobby_id: int
    prompt_id: int
    expected_answer: str


class GameLobbyState(BaseSchema):
    """Internal state persisted in Redis, including expected prompt answers."""

    lobby_id: int
    # Redis is authoritative for live games. Every accepted command increments
    # this version exactly once.
    state_revision: int = Field(default=0, ge=0)
    host: GameHostState
    players: list[GamePlayerState] = Field(default_factory=list)
    categories: list[GameCategoryState] = Field(default_factory=list)
    phase: GamePhaseEnum = GamePhaseEnum.WAITING_FOR_PLAYERS
    current_prompt_id: int | None = None
    selecting_player_id: int | None = None
    answering_player_id: int | None = None
    # Players who already tried (and failed) on the currently open prompt;
    # cleared whenever a new prompt becomes current.
    attempted_player_ids: list[int] = Field(default_factory=list)
    timer_deadline: datetime | None = None
    # Revision which armed ``timer_deadline``. Timer workers use this fencing
    # value to make old due entries harmless after any newer transition.
    timer_revision: int | None = Field(default=None, ge=0)
    # Resolution data stays private until public_state projects it during
    # answer_reveal, then is cleared before the next clue or final leaderboard.
    resolved_prompt_id: int | None = None
    resolved_answer: str | None = None
    resolved_answer_type: AnswerTypeEnum | None = None
    resolved_answer_media: MediaReferenceSchema | None = None
    resolution: GameResolutionEnum | None = None
    sound_cue_id: int = 0

    @classmethod
    def redis_key(cls, lobby_id: int) -> str:
        return f"game:{{{lobby_id}}}:state"

    @property
    def key(self) -> str:
        return self.redis_key(self.lobby_id)

    def public_state(
        self,
        *,
        include_banned_players: bool = False,
    ) -> PublicGameLobbyState:
        """Return a safe projection of this internal state for one recipient."""
        is_revealing_answer = self.phase == GamePhaseEnum.ANSWER_REVEAL
        players = (
            self.players
            if include_banned_players
            else [player for player in self.players if not player.is_banned]
        )
        visible_player_ids = {player.user_id for player in players}

        return PublicGameLobbyState(
            lobby_id=self.lobby_id,
            state_revision=self.state_revision,
            host=self.host,
            players=players,
            categories=[
                PublicGameCategoryState(
                    category_id=category.category_id,
                    name=category.name,
                    prompts=[
                        PublicGamePromptState(
                            prompt_id=prompt.prompt_id,
                            question=(
                                prompt.question
                                if prompt.prompt_id == self.current_prompt_id
                                else ""
                            ),
                            question_type=(
                                prompt.question_type
                                if prompt.prompt_id == self.current_prompt_id
                                else QuestionTypeEnum.TEXT
                            ),
                            question_media=(
                                prompt.question_media
                                if prompt.prompt_id == self.current_prompt_id
                                else None
                            ),
                            order=prompt.order,
                            is_selected=prompt.is_selected,
                        )
                        for prompt in category.prompts
                    ],
                )
                for category in self.categories
            ],
            phase=self.phase,
            current_prompt_id=self.current_prompt_id,
            selecting_player_id=(
                self.selecting_player_id if self.selecting_player_id in visible_player_ids else None
            ),
            answering_player_id=(
                self.answering_player_id if self.answering_player_id in visible_player_ids else None
            ),
            attempted_player_ids=[
                user_id for user_id in self.attempted_player_ids if user_id in visible_player_ids
            ],
            timer_deadline=self.timer_deadline,
            resolved_prompt_id=(self.resolved_prompt_id if is_revealing_answer else None),
            resolved_answer=self.resolved_answer if is_revealing_answer else None,
            resolved_answer_type=(self.resolved_answer_type if is_revealing_answer else None),
            resolved_answer_media=(self.resolved_answer_media if is_revealing_answer else None),
            resolution=self.resolution if is_revealing_answer else None,
            latest_sound_cue_id=self.sound_cue_id,
        )
