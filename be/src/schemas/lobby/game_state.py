from datetime import datetime
from functools import cached_property

from pydantic import Field, computed_field

from configs.constants import SCORE_MULTIPLIER
from enums.game import GamePhaseEnum, PlayerConnectionStatusEnum
from schemas.base import BaseSchema


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
    prompt_id: int
    question: str
    answer: str
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


class GameLobbyState(BaseSchema):
    lobby_id: int
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
    # Verbatim text submitted by the answering player; populated while phase
    # is host_judging_answer, cleared once the host judges.
    last_submitted_answer: str | None = None
    timer_deadline: datetime | None = None

    @classmethod
    def redis_key(cls, lobby_id: int) -> str:
        return f"lobby:{lobby_id}"

    @property
    def key(self) -> str:
        return self.redis_key(self.lobby_id)
