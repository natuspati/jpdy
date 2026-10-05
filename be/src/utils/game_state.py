from dataclasses import dataclass

from enums.game import GamePhaseEnum, PlayerConnectionStatusEnum
from enums.prompt import QuestionTypeEnum
from schemas.lobby.game_state import (
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
    PublicGameCategoryState,
    PublicGameLobbyState,
    PublicGamePromptState,
)


@dataclass(frozen=True, slots=True)
class GameCommandOutcome:
    """Pure game-command result consumed by optimistic Redis execution."""

    state: GameLobbyState | None
    result: GameLobbyState | None
    reason: str


def game_state_key(lobby_id: int) -> str:
    return f"game:{{{lobby_id}}}:state"


def game_events_key(lobby_id: int) -> str:
    return f"game:{{{lobby_id}}}:events"


def game_command_key(lobby_id: int, command_id: str) -> str:
    return f"game:{{{lobby_id}}}:command:{command_id}"


def game_timer_schedule_key(lobby_id: int) -> str:
    return f"game:{{{lobby_id}}}:timers"


def game_connection_key(lobby_id: int, user_id: int) -> str:
    return f"game:{{{lobby_id}}}:connection:{user_id}"


def timer_schedule_member(state: GameLobbyState) -> str | None:
    if state.timer_deadline is None or state.timer_revision is None:
        return None
    return f"{state.timer_revision}:{state.timer_deadline.isoformat()}"


def set_timer_revision(state: GameLobbyState) -> None:
    state.timer_revision = state.state_revision if state.timer_deadline is not None else None


def find_game_player(
    state: GameLobbyState,
    user_id: int | None,
) -> GamePlayerState | None:
    if user_id is None:
        return None
    return next((player for player in state.players if player.user_id == user_id), None)


def find_game_prompt(
    state: GameLobbyState,
    prompt_id: int | None,
) -> GamePromptState | None:
    if prompt_id is None:
        return None
    for category in state.categories:
        for prompt in category.prompts:
            if prompt.prompt_id == prompt_id:
                return prompt
    return None


def clear_game_player_selection_flags(state: GameLobbyState) -> None:
    for player in state.players:
        player.is_selected = False


def is_eligible_game_player(player: GamePlayerState | None) -> bool:
    return (
        player is not None
        and not player.is_banned
        and player.connection_status == PlayerConnectionStatusEnum.CONNECTED
    )


def get_eligible_buzzers(state: GameLobbyState) -> list[GamePlayerState]:
    return [
        player
        for player in state.players
        if is_eligible_game_player(player) and player.user_id not in state.attempted_player_ids
    ]


def all_board_prompts_spent(state: GameLobbyState) -> bool:
    return all(prompt.is_selected for category in state.categories for prompt in category.prompts)


def build_public_game_state(
    state: GameLobbyState,
    *,
    include_banned_players: bool = False,
) -> PublicGameLobbyState:
    """Project internal Redis state into a recipient-safe Socket.IO payload."""
    is_revealing_answer = state.phase == GamePhaseEnum.ANSWER_REVEAL
    players = (
        state.players
        if include_banned_players
        else [player for player in state.players if not player.is_banned]
    )
    visible_player_ids = {player.user_id for player in players}

    return PublicGameLobbyState(
        lobby_id=state.lobby_id,
        state_revision=state.state_revision,
        host=state.host,
        players=players,
        categories=[
            PublicGameCategoryState(
                category_id=category.category_id,
                name=category.name,
                prompts=[
                    PublicGamePromptState(
                        prompt_id=prompt.prompt_id,
                        question=(
                            prompt.question if prompt.prompt_id == state.current_prompt_id else ""
                        ),
                        question_type=(
                            prompt.question_type
                            if prompt.prompt_id == state.current_prompt_id
                            else QuestionTypeEnum.TEXT
                        ),
                        question_media=prompt.question_media,
                        order=prompt.order,
                        is_selected=prompt.is_selected,
                    )
                    for prompt in category.prompts
                ],
            )
            for category in state.categories
        ],
        phase=state.phase,
        current_prompt_id=state.current_prompt_id,
        selecting_player_id=(
            state.selecting_player_id if state.selecting_player_id in visible_player_ids else None
        ),
        answering_player_id=(
            state.answering_player_id if state.answering_player_id in visible_player_ids else None
        ),
        attempted_player_ids=[
            user_id for user_id in state.attempted_player_ids if user_id in visible_player_ids
        ],
        timer_deadline=state.timer_deadline,
        resolved_prompt_id=state.resolved_prompt_id if is_revealing_answer else None,
        resolved_answer=state.resolved_answer if is_revealing_answer else None,
        resolved_answer_type=state.resolved_answer_type if is_revealing_answer else None,
        resolved_answer_media=state.resolved_answer_media if is_revealing_answer else None,
        resolution=state.resolution if is_revealing_answer else None,
        latest_sound_cue_id=state.sound_cue_id,
    )
