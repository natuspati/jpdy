from dataclasses import dataclass

from configs.constants import ROUND_SCORE_MULTIPLIER, SCORE_MULTIPLIER
from enums.game import GamePhaseEnum, PlayerConnectionStatusEnum
from enums.prompt import QuestionTypeEnum
from schemas.lobby.game_state import (
    GameCategoryState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
    GameRoundResult,
    GameRoundScore,
    PublicFinalPlayerState,
    PublicFinalRoundState,
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


def round_score_value(order: int, round_number: int) -> int:
    return order * SCORE_MULTIPLIER * ROUND_SCORE_MULTIPLIER ** (round_number - 1)


def find_game_category_of_prompt(state: GameLobbyState, prompt_id: int) -> GameCategoryState | None:
    return next(
        (
            category
            for category in state.categories
            if any(prompt.prompt_id == prompt_id for prompt in category.prompts)
        ),
        None,
    )


def current_round_prompts_spent(state: GameLobbyState) -> bool:
    return all(
        prompt.is_selected
        for category in state.categories
        if category.round_number == state.current_round
        for prompt in category.prompts
    )


def build_round_result(state: GameLobbyState) -> GameRoundResult:
    """Snapshot every player's cumulative score and this round's delta."""
    previous = {
        score.user_id: score.score
        for score in (state.round_results[-1].scores if state.round_results else [])
    }
    return GameRoundResult(
        round_number=state.current_round,
        scores=[
            GameRoundScore(
                user_id=player.user_id,
                username=player.username,
                score=player.score,
                score_delta=player.score - previous.get(player.user_id, 0),
                is_banned=player.is_banned,
            )
            for player in state.players
        ],
    )


def _is_question_visible(state: GameLobbyState, prompt: GamePromptState, is_betting: bool) -> bool:
    return prompt.prompt_id == state.current_prompt_id and not is_betting


def build_public_game_state(
    state: GameLobbyState,
    *,
    include_banned_players: bool = False,
    viewer_user_id: int | None = None,
) -> PublicGameLobbyState:
    """Project internal Redis state into a recipient-safe Socket.IO payload."""
    is_revealing_answer = state.phase == GamePhaseEnum.ANSWER_REVEAL
    is_betting = state.phase in {GamePhaseEnum.BETTING_ANNOUNCEMENT, GamePhaseEnum.BETTING_OPEN}
    players = (
        state.players
        if include_banned_players
        else [player for player in state.players if not player.is_banned]
    )
    visible_player_ids = {player.user_id for player in players}
    banned_ids = {player.user_id for player in state.players if player.is_banned}
    final_question_visible = (
        state.final_round is not None
        and state.final_round.skipped_reason is None
        and state.phase
        in {GamePhaseEnum.FINAL_ANSWERING, GamePhaseEnum.FINAL_REVEAL, GamePhaseEnum.FINISHED}
    )
    final_answer_visible = state.final_round is not None and any(
        player.revealed for player in state.final_round.players
    )
    round_results = [
        result.model_copy(
            update={
                "scores": [
                    score
                    for score in result.scores
                    if include_banned_players or score.user_id not in banned_ids
                ],
            },
        )
        for result in state.round_results
    ]

    return PublicGameLobbyState(
        lobby_id=state.lobby_id,
        state_revision=state.state_revision,
        host=state.host,
        players=players,
        categories=[
            PublicGameCategoryState(
                category_id=category.category_id,
                name=category.name,
                round_number=category.round_number,
                kind=category.kind,
                prompts=[
                    PublicGamePromptState(
                        prompt_id=prompt.prompt_id,
                        question=prompt.question
                        if (
                            final_question_visible
                            if category.kind == "final"
                            else _is_question_visible(state, prompt, is_betting)
                        )
                        else "",
                        question_type=(
                            prompt.question_type
                            if (
                                final_question_visible
                                if category.kind == "final"
                                else _is_question_visible(state, prompt, is_betting)
                            )
                            else QuestionTypeEnum.TEXT
                        ),
                        question_media=(
                            prompt.question_media
                            if category.kind != "final" or final_question_visible
                            else None
                        ),
                        answer_media=(
                            prompt.answer_media
                            if category.kind != "final" or final_answer_visible
                            else None
                        ),
                        order=prompt.order,
                        score_value=prompt.score_value,
                        is_selected=prompt.is_selected,
                        is_betting=prompt.is_betting
                        and prompt.prompt_id == state.current_prompt_id,
                    )
                    for prompt in category.prompts
                ],
            )
            for category in state.categories
        ],
        phase=state.phase,
        current_round=state.current_round,
        total_rounds=state.total_rounds,
        round_results=round_results,
        final_round=_build_public_final_round(state, viewer_user_id, visible_player_ids),
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
        min_bet=state.min_bet,
        max_bet=state.max_bet,
        my_bet=state.bets.get(viewer_user_id) if viewer_user_id is not None else None,
        timer_deadline=state.timer_deadline,
        resolved_prompt_id=state.resolved_prompt_id if is_revealing_answer else None,
        resolved_answer=state.resolved_answer if is_revealing_answer else None,
        resolved_answer_type=state.resolved_answer_type if is_revealing_answer else None,
        resolved_answer_media=state.resolved_answer_media if is_revealing_answer else None,
        resolution=state.resolution if is_revealing_answer else None,
        latest_sound_cue_id=state.sound_cue_id,
    )


def _build_public_final_round(
    state: GameLobbyState,
    viewer_user_id: int | None,
    visible_player_ids: set[int],
) -> PublicFinalRoundState | None:
    final = state.final_round
    if final is None:
        return None
    current_user_id = (
        final.reveal_order[final.reveal_index]
        if state.phase == GamePhaseEnum.FINAL_REVEAL
        and final.reveal_index < len(final.reveal_order)
        else None
    )
    has_revealed = any(p.revealed for p in final.players)
    prompt = next(
        (p for c in state.categories if c.kind == "final" for p in c.prompts),
        None,
    )
    return PublicFinalRoundState(
        players=[
            PublicFinalPlayerState(
                user_id=player.user_id,
                username=player.username,
                score_before_final=player.score_before_final,
                decision_submitted=player.decision_submitted,
                answer_submitted=player.answer_submitted,
                removed=player.removed,
                revealed=player.revealed,
                wager=(
                    player.wager
                    if player.correct is not None or player.user_id == viewer_user_id
                    else None
                ),
                answer=(
                    player.answer if player.revealed or player.user_id == viewer_user_id else None
                ),
                correct=player.correct,
                score_delta=(
                    (player.wager if player.correct else -player.wager)
                    if player.correct is not None and player.wager is not None
                    else None
                ),
                updated_score=(
                    find_game_player(state, player.user_id).score
                    if player.correct is not None
                    else None
                ),
            )
            for player in final.players
            if player.user_id in visible_player_ids
        ],
        current_user_id=current_user_id if current_user_id in visible_player_ids else None,
        is_last_reveal=current_user_id is not None
        and not any(
            not p.removed and p.user_id in final.reveal_order[final.reveal_index + 1 :]
            for p in final.players
        ),
        skipped_reason=final.skipped_reason,
        correct_answer=prompt.answer if prompt is not None and has_revealed else None,
        correct_answer_type=prompt.answer_type if prompt is not None and has_revealed else None,
        correct_answer_media=prompt.answer_media if prompt is not None and has_revealed else None,
    )
