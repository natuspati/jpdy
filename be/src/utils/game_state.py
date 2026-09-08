from dataclasses import dataclass
from typing import TYPE_CHECKING

from enums.game import GamePhaseEnum
from enums.prompt import QuestionTypeEnum
from errors.request import BadRequestError, NotFoundError
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePromptState,
    PublicGameCategoryState,
    PublicGameLobbyState,
    PublicGamePromptState,
)
from schemas.lobby.nested import LobbyWithCategoryPromptsInDBSchema
from utils.media import build_media_reference

if TYPE_CHECKING:
    from database import UnitOfWork


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
                        question_media=(
                            prompt.question_media
                            if prompt.prompt_id == state.current_prompt_id
                            else None
                        ),
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


def build_game_lobby_state(lobby: LobbyWithCategoryPromptsInDBSchema) -> GameLobbyState:
    """Build immutable SQL lobby snapshot into initial Redis game state."""
    if lobby.owner is None:
        raise BadRequestError("Lobby has no owner; cannot start a game")

    return GameLobbyState(
        lobby_id=lobby.id,
        host=GameHostState(user_id=lobby.owner.id, username=lobby.owner.username),
        categories=[
            GameCategoryState(
                category_id=category.id,
                name=category.name,
                prompts=[
                    GamePromptState(
                        prompt_id=prompt.id,
                        question=prompt.question,
                        answer=prompt.answer,
                        question_type=prompt.question_type,
                        answer_type=prompt.answer_type,
                        question_media=(
                            build_media_reference(prompt.question_media_asset)
                            if prompt.question_media_asset is not None
                            else None
                        ),
                        answer_media=(
                            build_media_reference(prompt.answer_media_asset)
                            if prompt.answer_media_asset is not None
                            else None
                        ),
                        order=prompt.order or 0,
                    )
                    for prompt in category.prompts
                ],
            )
            for category in lobby.prompt_categories
        ],
    )


async def materialize_game_state(
    uow: UnitOfWork,
    lobby_id: int,
) -> GameLobbyState:
    """Build SQL lobby snapshot then initialize Redis exactly once."""
    lobby = await uow.lobby_repo.select_lobby_with_prompts(lobby_id=lobby_id)
    if lobby is None:
        raise NotFoundError(f"Lobby {lobby_id} not found")
    return await uow.game_state_repo.initialize_state(build_game_lobby_state(lobby))
