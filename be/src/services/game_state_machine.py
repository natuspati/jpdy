from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from configs.constants import (
    ANSWER_REVEAL_TIME_SECONDS,
    ANSWERING_TIME_SECONDS,
    BUZZING_TIME_SECONDS,
)
from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from errors.request import BadRequestError, ForbiddenError
from schemas.lobby.game_state import GameLobbyState, GamePlayerState
from utils.game_state import (
    GameCommandOutcome,
    all_board_prompts_spent,
    clear_game_player_selection_flags,
    find_game_player,
    find_game_prompt,
    get_eligible_buzzers,
    is_eligible_game_player,
)


class GameStateMachine:
    """Pure, synchronous transitions for Redis-authoritative game state."""

    def __init__(self, clock: Callable[[], datetime] | None = None):
        self._clock = clock or _utc_now

    def connect_user(
        self,
        state: GameLobbyState,
        user_id: int,
        username: str,
    ) -> GameCommandOutcome:
        if state.phase == GamePhaseEnum.FINISHED:
            raise ForbiddenError("Game has finished")
        if user_id == state.host.user_id:
            state.host.connection_status = PlayerConnectionStatusEnum.CONNECTED
        else:
            player = find_game_player(state, user_id)
            if player is None:
                if state.phase != GamePhaseEnum.WAITING_FOR_PLAYERS:
                    raise ForbiddenError("Lobby roster is locked after the game has started")
                state.players.append(
                    GamePlayerState(
                        user_id=user_id,
                        username=username,
                        connection_status=PlayerConnectionStatusEnum.CONNECTED,
                    ),
                )
            else:
                if player.is_banned:
                    raise ForbiddenError("Player is banned from this lobby")
                player.connection_status = PlayerConnectionStatusEnum.CONNECTED
        return GameCommandOutcome(state=state, result=state, reason="user_connected")

    def disconnect_user(self, state: GameLobbyState, user_id: int) -> GameCommandOutcome:
        if user_id == state.host.user_id:
            state.host.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
        else:
            player = find_game_player(state, user_id)
            if player is None:
                return GameCommandOutcome(state=None, result=state, reason="unknown_disconnect")
            player.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
        return GameCommandOutcome(state=state, result=state, reason="user_disconnected")

    def start_game(self, state: GameLobbyState, user_id: int) -> GameCommandOutcome:
        self._require_host(state, user_id)
        self._require_phase(state, GamePhaseEnum.WAITING_FOR_PLAYERS)
        if not any(is_eligible_game_player(player) for player in state.players):
            raise BadRequestError("At least one connected, non-banned player is required")
        state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
        return GameCommandOutcome(state=state, result=state, reason="game_started")

    def select_starter(
        self,
        state: GameLobbyState,
        user_id: int,
        target_user_id: int,
    ) -> GameCommandOutcome:
        self._require_host(state, user_id)
        self._require_phase(state, GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER)
        target = find_game_player(state, target_user_id)
        if target is None:
            raise BadRequestError(f"Player {target_user_id} is not in this lobby")
        if target.is_banned:
            raise BadRequestError("Cannot select a banned player")
        if target.connection_status != PlayerConnectionStatusEnum.CONNECTED:
            raise BadRequestError("Selected player is not connected")
        clear_game_player_selection_flags(state)
        target.is_selected = True
        state.selecting_player_id = target.user_id
        state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
        return GameCommandOutcome(state=state, result=state, reason="starter_selected")

    def select_prompt(
        self,
        state: GameLobbyState,
        user_id: int,
        prompt_id: int,
    ) -> GameCommandOutcome:
        self._require_phase(state, GamePhaseEnum.PLAYER_SELECTING_PROMPT)
        if state.selecting_player_id != user_id:
            raise ForbiddenError("Only the selecting player may pick a prompt")
        prompt = find_game_prompt(state, prompt_id)
        if prompt is None:
            raise BadRequestError(f"Prompt {prompt_id} is not in this lobby")
        if prompt.is_selected:
            raise BadRequestError("Prompt has already been used")
        prompt.is_selected = True
        state.current_prompt_id = prompt.prompt_id
        state.answering_player_id = state.selecting_player_id
        state.attempted_player_ids = []
        clear_game_player_selection_flags(state)
        answerer = find_game_player(state, state.answering_player_id)
        if answerer is not None:
            answerer.is_selected = True
        self._clear_resolution(state)
        state.phase = GamePhaseEnum.PLAYER_ANSWERING
        state.timer_deadline = self._deadline(ANSWERING_TIME_SECONDS)
        return GameCommandOutcome(state=state, result=state, reason="prompt_selected")

    def judge_answer(
        self,
        state: GameLobbyState,
        user_id: int,
        correct: bool,
    ) -> GameCommandOutcome:
        self._require_host(state, user_id)
        self._require_phase(state, GamePhaseEnum.PLAYER_ANSWERING)
        if state.current_prompt_id is None or state.answering_player_id is None:
            raise BadRequestError("No prompt is currently being judged")
        if state.timer_deadline is None or state.timer_deadline <= self._clock():
            raise BadRequestError("Answer time has expired")
        prompt = find_game_prompt(state, state.current_prompt_id)
        answerer = find_game_player(state, state.answering_player_id)
        if prompt is None or answerer is None:
            raise BadRequestError("Active prompt or player is missing from state")
        if correct:
            answerer.score += prompt.score_value
            clear_game_player_selection_flags(state)
            state.selecting_player_id = answerer.user_id
            state.answering_player_id = None
            self._enter_answer_reveal(state, GameResolutionEnum.CORRECT)
        else:
            answerer.score -= prompt.score_value
            answerer.is_selected = False
            if answerer.user_id not in state.attempted_player_ids:
                state.attempted_player_ids.append(answerer.user_id)
            state.answering_player_id = None
            if get_eligible_buzzers(state):
                state.phase = GamePhaseEnum.BUZZ_OPEN
                state.timer_deadline = self._deadline(BUZZING_TIME_SECONDS)
            else:
                self._enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)
        return GameCommandOutcome(state=state, result=state, reason="answer_judged")

    def buzz(self, state: GameLobbyState, user_id: int) -> GameCommandOutcome:
        self._require_phase(state, GamePhaseEnum.BUZZ_OPEN)
        if state.timer_deadline is None or state.timer_deadline <= self._clock():
            raise BadRequestError("Buzz time has expired")
        player = find_game_player(state, user_id)
        if player is None:
            raise ForbiddenError("Only lobby players may buzz")
        if player.is_banned:
            raise ForbiddenError("Banned players may not buzz")
        if player.connection_status != PlayerConnectionStatusEnum.CONNECTED:
            raise ForbiddenError("Disconnected players may not buzz")
        if user_id in state.attempted_player_ids:
            raise ForbiddenError("You already attempted this prompt")
        clear_game_player_selection_flags(state)
        player.is_selected = True
        state.answering_player_id = user_id
        state.phase = GamePhaseEnum.PLAYER_ANSWERING
        state.timer_deadline = self._deadline(ANSWERING_TIME_SECONDS)
        return GameCommandOutcome(state=state, result=state, reason="buzz_accepted")

    def advance_answer_reveal(self, state: GameLobbyState, user_id: int) -> GameCommandOutcome:
        self._require_host(state, user_id)
        self._require_phase(state, GamePhaseEnum.ANSWER_REVEAL)
        self._advance_after_reveal(state)
        return GameCommandOutcome(state=state, result=state, reason="answer_reveal_advanced")

    def ban_player(
        self,
        state: GameLobbyState,
        user_id: int,
        target_user_id: int,
    ) -> GameCommandOutcome:
        self._require_host(state, user_id)
        target = find_game_player(state, target_user_id)
        if target is None:
            raise BadRequestError(f"Player {target_user_id} is not in this lobby")
        target.is_banned = True
        target.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
        self._recover_from_banned_player(state, target.user_id)
        return GameCommandOutcome(state=state, result=state, reason="player_banned")

    def unban_player(
        self,
        state: GameLobbyState,
        user_id: int,
        target_user_id: int,
    ) -> GameCommandOutcome:
        self._require_host(state, user_id)
        target = find_game_player(state, target_user_id)
        if target is None:
            raise BadRequestError(f"Player {target_user_id} is not in this lobby")
        target.is_banned = False
        return GameCommandOutcome(state=state, result=state, reason="player_unbanned")

    def expire_timer(
        self,
        state: GameLobbyState,
        expected_revision: int | None,
        expected_deadline: datetime | None,
    ) -> GameCommandOutcome:
        if state.timer_deadline is None:
            return GameCommandOutcome(state=None, result=None, reason="no_timer")
        if expected_revision is not None and state.timer_revision != expected_revision:
            return GameCommandOutcome(state=None, result=None, reason="stale_timer_revision")
        if expected_deadline is not None and state.timer_deadline != expected_deadline:
            return GameCommandOutcome(state=None, result=None, reason="stale_timer_deadline")
        if state.timer_deadline > self._clock():
            return GameCommandOutcome(state=None, result=None, reason="timer_not_due")
        if state.phase == GamePhaseEnum.PLAYER_ANSWERING:
            if state.answering_player_id is not None:
                if state.answering_player_id not in state.attempted_player_ids:
                    state.attempted_player_ids.append(state.answering_player_id)
                expired = find_game_player(state, state.answering_player_id)
                if expired is not None:
                    expired.is_selected = False
            state.answering_player_id = None
            if get_eligible_buzzers(state):
                state.phase = GamePhaseEnum.BUZZ_OPEN
                state.timer_deadline = self._deadline(BUZZING_TIME_SECONDS)
            else:
                self._enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
        elif state.phase == GamePhaseEnum.BUZZ_OPEN:
            self._enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
        elif state.phase == GamePhaseEnum.ANSWER_REVEAL:
            self._advance_after_reveal(state)
        else:
            return GameCommandOutcome(state=None, result=None, reason="timer_phase_not_timed")
        return GameCommandOutcome(state=state, result=state, reason="timer_expired")

    def issue_sound_cue(self, state: GameLobbyState, cue: str) -> GameCommandOutcome:
        state.sound_cue_id += 1
        return GameCommandOutcome(state=state, result=state, reason=f"sound_cue:{cue}")

    def _advance_after_reveal(self, state: GameLobbyState) -> None:
        state.current_prompt_id = None
        state.answering_player_id = None
        state.attempted_player_ids = []
        state.timer_deadline = None
        self._clear_resolution(state)
        clear_game_player_selection_flags(state)
        if not all_board_prompts_spent(state):
            selector = find_game_player(state, state.selecting_player_id)
            if is_eligible_game_player(selector):
                state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
                selector.is_selected = True
            else:
                self._enter_host_player_selection(state)
            return
        state.phase = GamePhaseEnum.FINISHED
        state.selecting_player_id = None

    def _enter_host_player_selection(self, state: GameLobbyState) -> None:
        clear_game_player_selection_flags(state)
        state.selecting_player_id = None
        state.answering_player_id = None
        state.timer_deadline = None
        state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER

    def _recover_from_banned_player(self, state: GameLobbyState, user_id: int) -> None:
        is_selector = state.selecting_player_id == user_id
        is_answerer = state.answering_player_id == user_id
        if state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT and is_selector:
            self._enter_host_player_selection(state)
            return
        if state.phase == GamePhaseEnum.PLAYER_ANSWERING and is_answerer:
            state.selecting_player_id = None
            clear_game_player_selection_flags(state)
            self._enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)
            return
        if is_selector:
            state.selecting_player_id = None
            banned_player = find_game_player(state, user_id)
            if banned_player is not None:
                banned_player.is_selected = False
        if state.phase == GamePhaseEnum.BUZZ_OPEN and not get_eligible_buzzers(state):
            self._enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)

    def _enter_answer_reveal(
        self,
        state: GameLobbyState,
        resolution: GameResolutionEnum,
    ) -> None:
        if state.current_prompt_id is None:
            raise BadRequestError("No active prompt to reveal")
        prompt = find_game_prompt(state, state.current_prompt_id)
        if prompt is None:
            raise BadRequestError("Active prompt is missing from state")
        state.answering_player_id = None
        clear_game_player_selection_flags(state)
        state.phase = GamePhaseEnum.ANSWER_REVEAL
        state.timer_deadline = self._deadline(ANSWER_REVEAL_TIME_SECONDS)
        state.resolved_prompt_id = prompt.prompt_id
        state.resolved_answer = prompt.answer
        state.resolved_answer_type = prompt.answer_type
        state.resolved_answer_media = prompt.answer_media
        state.resolution = resolution

    @staticmethod
    def _clear_resolution(state: GameLobbyState) -> None:
        state.resolved_prompt_id = None
        state.resolved_answer = None
        state.resolved_answer_type = None
        state.resolved_answer_media = None
        state.resolution = None

    @staticmethod
    def _require_host(state: GameLobbyState, user_id: int) -> None:
        if user_id != state.host.user_id:
            raise ForbiddenError("Only the host may perform this action")

    @staticmethod
    def _require_phase(state: GameLobbyState, *phases: GamePhaseEnum) -> None:
        if state.phase not in phases:
            raise BadRequestError(f"Action not allowed during phase {state.phase.value}")

    def _deadline(self, seconds: int) -> datetime:
        return self._clock() + timedelta(seconds=seconds)


def _utc_now() -> datetime:
    return datetime.now(UTC)
