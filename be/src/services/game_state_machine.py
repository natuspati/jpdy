from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from configs.constants import (
    ANSWER_REVEAL_TIME_SECONDS,
    ANSWERING_TIME_SECONDS,
    BETTING_TIME_SECONDS,
    BUZZING_TIME_SECONDS,
    FINAL_ANSWERING_TIME_SECONDS,
    FINAL_BETTING_TIME_SECONDS,
    NUM_PROMPTS_IN_CATEGORY,
    ROUND_SUMMARY_TIME_SECONDS,
)
from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from errors.request import BadRequestError, ForbiddenError
from schemas.lobby.game_state import (
    FinalPlayerState,
    FinalRoundState,
    GameLobbyState,
    GamePlayerState,
)
from utils.game_state import (
    GameCommandOutcome,
    build_round_result,
    clear_game_player_selection_flags,
    current_round_prompts_spent,
    find_game_category_of_prompt,
    find_game_player,
    find_game_prompt,
    get_eligible_buzzers,
    is_eligible_game_player,
    round_score_value,
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
                player.assets_loaded = False
        return GameCommandOutcome(state=state, result=state, reason="user_connected")

    def disconnect_user(self, state: GameLobbyState, user_id: int) -> GameCommandOutcome:
        if user_id == state.host.user_id:
            state.host.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
        else:
            player = find_game_player(state, user_id)
            if player is None:
                return GameCommandOutcome(state=None, result=state, reason="unknown_disconnect")
            player.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
            player.assets_loaded = False
        return GameCommandOutcome(state=state, result=state, reason="user_disconnected")

    def set_assets_loaded(
        self,
        state: GameLobbyState,
        user_id: int,
        loaded: bool,
    ) -> GameCommandOutcome:
        self._require_phase(state, GamePhaseEnum.WAITING_FOR_PLAYERS)
        player = find_game_player(state, user_id)
        if player is None:
            raise ForbiddenError("Only lobby players report loaded assets")
        player.assets_loaded = loaded
        return GameCommandOutcome(state=state, result=state, reason="assets_loaded_set")

    def start_game(
        self,
        state: GameLobbyState,
        user_id: int,
        force: bool = False,
    ) -> GameCommandOutcome:
        self._require_host(state, user_id)
        self._require_phase(state, GamePhaseEnum.WAITING_FOR_PLAYERS)
        if not any(is_eligible_game_player(player) for player in state.players):
            raise BadRequestError("At least one connected, non-banned player is required")
        if not force and not all(
            player.assets_loaded for player in state.players if is_eligible_game_player(player)
        ):
            raise BadRequestError("Wait for all players to finish loading")
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
        category = find_game_category_of_prompt(state, prompt_id)
        if category is not None and category.kind == "final":
            raise BadRequestError("Final prompts cannot be selected from the board")
        if category is not None and category.round_number != state.current_round:
            raise BadRequestError("Prompt belongs to another round")
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
        if prompt.is_betting:
            state.answering_player_id = None
            state.min_bet = prompt.score_value
            state.current_bet = 0
            state.betting_player_id = None
            state.max_bet = max(
                round_score_value(NUM_PROMPTS_IN_CATEGORY, state.current_round),
                max((p.score for p in state.players if not p.is_banned), default=0),
            )
            state.phase = GamePhaseEnum.PLAYER_BETTING
            state.timer_deadline = self._deadline(BETTING_TIME_SECONDS)
            return GameCommandOutcome(state=state, result=state, reason="prompt_selected")
        state.phase = GamePhaseEnum.PLAYER_ANSWERING
        state.timer_deadline = self._deadline(ANSWERING_TIME_SECONDS)
        return GameCommandOutcome(state=state, result=state, reason="prompt_selected")

    def place_bet(self, state: GameLobbyState, user_id: int, amount: int) -> GameCommandOutcome:
        self._require_phase(state, GamePhaseEnum.PLAYER_BETTING, GamePhaseEnum.BETTING_OPEN)
        if state.timer_deadline is None or state.timer_deadline <= self._clock():
            raise BadRequestError("Betting time has expired")
        if not is_eligible_game_player(find_game_player(state, user_id)):
            raise ForbiddenError("Only connected, non-banned players may bet")
        is_selector = user_id == state.selecting_player_id
        if state.phase == GamePhaseEnum.PLAYER_BETTING and not is_selector:
            raise ForbiddenError("Only the selecting player may bet right now")
        if state.phase == GamePhaseEnum.BETTING_OPEN and is_selector:
            raise ForbiddenError("The selecting player already had their turn to bet")
        if not state.min_bet <= amount <= state.max_bet:
            raise BadRequestError(f"Bet must be between {state.min_bet} and {state.max_bet}")
        if amount <= state.current_bet:
            raise BadRequestError(f"Bet must be higher than {state.current_bet}")
        state.current_bet = amount
        state.betting_player_id = user_id
        if state.phase == GamePhaseEnum.PLAYER_BETTING:
            self._open_challenger_window(state)
        return GameCommandOutcome(state=state, result=state, reason="bet_placed")

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
            if prompt.is_betting:
                state.selecting_player_id = answerer.user_id
                self._enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)
            elif get_eligible_buzzers(state):
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

    def advance_round(self, state: GameLobbyState, user_id: int) -> GameCommandOutcome:
        self._require_host(state, user_id)
        self._require_phase(state, GamePhaseEnum.ROUND_SUMMARY)
        self._start_next_round(state)
        return GameCommandOutcome(state=state, result=state, reason="round_advanced")

    def submit_final_wager(
        self,
        state: GameLobbyState,
        user_id: int,
        amount: int | None,
    ) -> GameCommandOutcome:
        self._require_phase(state, GamePhaseEnum.FINAL_BETTING)
        self._require_final_deadline(state)
        player = self._final_player(state, user_id)
        if player.decision_submitted:
            raise BadRequestError("Final decision has already been submitted")
        if amount is not None and (
            type(amount) is not int or not 1 <= amount <= player.score_before_final
        ):
            raise BadRequestError("Wager must be an integer between 1 and your starting score")
        player.decision_submitted = True
        player.wager = amount
        final = state.final_round
        assert final is not None
        if all(p.decision_submitted for p in final.players if not p.removed):
            self._lock_final_wagers(state)
        return GameCommandOutcome(state=state, result=state, reason="final_wager_submitted")

    def submit_final_answer(
        self,
        state: GameLobbyState,
        user_id: int,
        answer: str,
    ) -> GameCommandOutcome:
        self._require_phase(state, GamePhaseEnum.FINAL_ANSWERING)
        self._require_final_deadline(state)
        player = self._final_player(state, user_id)
        if player.wager is None:
            raise ForbiddenError("Only players who wagered may submit an answer")
        if player.answer_submitted:
            raise BadRequestError("Final answer has already been submitted")
        if not isinstance(answer, str) or len(answer) > 256:
            raise BadRequestError("Final answer must be text of at most 256 characters")
        player.answer_submitted = True
        player.answer = answer.strip()
        final = state.final_round
        assert final is not None
        if all(p.answer_submitted for p in final.players if not p.removed and p.wager is not None):
            self._lock_final_answers(state)
        return GameCommandOutcome(state=state, result=state, reason="final_answer_submitted")

    def judge_final_answer(
        self,
        state: GameLobbyState,
        user_id: int,
        target_user_id: int,
        correct: bool,
    ) -> GameCommandOutcome:
        self._require_host(state, user_id)
        player = self._current_final_reveal(state, target_user_id)
        if player.correct is not None:
            raise BadRequestError("This Final answer has already been judged")
        if not player.answer:
            raise BadRequestError("Missing Final answers are automatically incorrect")
        self._apply_final_judgment(state, player, correct)
        return GameCommandOutcome(state=state, result=state, reason="final_answer_judged")

    def advance_final_reveal(
        self,
        state: GameLobbyState,
        user_id: int,
        target_user_id: int,
    ) -> GameCommandOutcome:
        self._require_host(state, user_id)
        player = self._current_final_reveal(state, target_user_id)
        if player.correct is None:
            raise BadRequestError("Judge the current Final answer before advancing")
        assert state.final_round is not None
        state.final_round.reveal_index += 1
        self._open_final_reveal(state)
        return GameCommandOutcome(state=state, result=state, reason="final_reveal_advanced")

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
        if state.phase == GamePhaseEnum.PLAYER_BETTING:
            self._open_challenger_window(state)
        elif state.phase == GamePhaseEnum.BETTING_OPEN:
            self._resolve_betting(state)
        elif state.phase == GamePhaseEnum.PLAYER_ANSWERING:
            prompt = find_game_prompt(state, state.current_prompt_id)
            if state.answering_player_id is not None:
                if state.answering_player_id not in state.attempted_player_ids:
                    state.attempted_player_ids.append(state.answering_player_id)
                expired = find_game_player(state, state.answering_player_id)
                if expired is not None:
                    expired.is_selected = False
                    # Timing out counts as a host decline.
                    if prompt is not None:
                        expired.score -= prompt.score_value
                    if prompt is not None and prompt.is_betting:
                        state.selecting_player_id = expired.user_id
            state.answering_player_id = None
            if prompt is not None and prompt.is_betting:
                self._enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
            elif get_eligible_buzzers(state):
                state.phase = GamePhaseEnum.BUZZ_OPEN
                state.timer_deadline = self._deadline(BUZZING_TIME_SECONDS)
            else:
                self._enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
        elif state.phase == GamePhaseEnum.BUZZ_OPEN:
            self._enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
        elif state.phase == GamePhaseEnum.ANSWER_REVEAL:
            self._advance_after_reveal(state)
        elif state.phase == GamePhaseEnum.ROUND_SUMMARY:
            self._start_next_round(state)
        elif state.phase == GamePhaseEnum.FINAL_BETTING:
            self._lock_final_wagers(state)
        elif state.phase == GamePhaseEnum.FINAL_ANSWERING:
            self._lock_final_answers(state)
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
        if not current_round_prompts_spent(state):
            selector = find_game_player(state, state.selecting_player_id)
            if is_eligible_game_player(selector):
                state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
                selector.is_selected = True
            else:
                self._enter_host_player_selection(state)
            return
        state.round_results.append(build_round_result(state))
        state.selecting_player_id = None
        if state.current_round < state.total_rounds:
            state.phase = GamePhaseEnum.ROUND_SUMMARY
            state.timer_deadline = self._deadline(ROUND_SUMMARY_TIME_SECONDS)
        else:
            state.phase = GamePhaseEnum.FINISHED

    def _start_next_round(self, state: GameLobbyState) -> None:
        state.current_round += 1
        state.timer_deadline = None
        clear_game_player_selection_flags(state)
        if any(
            category.kind == "final" and category.round_number == state.current_round
            for category in state.categories
        ):
            self._start_final(state)
            return
        eligible = [player for player in state.players if is_eligible_game_player(player)]
        lowest = min((player.score for player in eligible), default=None)
        lowest_players = [player for player in eligible if player.score == lowest]
        if len(lowest_players) != 1:
            self._enter_host_player_selection(state)
            return
        selector = lowest_players[0]
        selector.is_selected = True
        state.selecting_player_id = selector.user_id
        state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT

    def _open_challenger_window(self, state: GameLobbyState) -> None:
        if any(
            is_eligible_game_player(player) and player.user_id != state.selecting_player_id
            for player in state.players
        ):
            state.phase = GamePhaseEnum.BETTING_OPEN
            state.timer_deadline = self._deadline(BETTING_TIME_SECONDS)
        else:
            self._resolve_betting(state)

    def _resolve_betting(self, state: GameLobbyState) -> None:
        bettor_id = state.betting_player_id
        prompt = find_game_prompt(state, state.current_prompt_id)
        if bettor_id is None and is_eligible_game_player(
            find_game_player(state, state.selecting_player_id),
        ):
            # Nobody bet: the selector answers at the prompt's default value.
            bettor_id = state.selecting_player_id
            state.current_bet = state.min_bet
        if bettor_id is None or prompt is None:
            self._clear_betting(state)
            self._enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
            return
        prompt.score_value = state.current_bet
        state.answering_player_id = state.selecting_player_id = bettor_id
        state.attempted_player_ids = []
        clear_game_player_selection_flags(state)
        bettor = find_game_player(state, bettor_id)
        if bettor is not None:
            bettor.is_selected = True
        self._clear_betting(state)
        state.phase = GamePhaseEnum.PLAYER_ANSWERING
        state.timer_deadline = self._deadline(ANSWERING_TIME_SECONDS)

    @staticmethod
    def _clear_betting(state: GameLobbyState) -> None:
        state.min_bet = state.max_bet = state.current_bet = 0
        state.betting_player_id = None

    def _enter_host_player_selection(self, state: GameLobbyState) -> None:
        clear_game_player_selection_flags(state)
        state.selecting_player_id = None
        state.answering_player_id = None
        state.timer_deadline = None
        state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER

    def _recover_from_banned_player(self, state: GameLobbyState, user_id: int) -> None:
        if state.phase in {
            GamePhaseEnum.FINAL_BETTING,
            GamePhaseEnum.FINAL_ANSWERING,
            GamePhaseEnum.FINAL_REVEAL,
        }:
            self._remove_final_player(state, user_id)
            return
        is_selector = state.selecting_player_id == user_id
        is_answerer = state.answering_player_id == user_id
        if state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT and is_selector:
            self._enter_host_player_selection(state)
            return
        if state.phase == GamePhaseEnum.PLAYER_BETTING and is_selector:
            state.selecting_player_id = None
            clear_game_player_selection_flags(state)
            self._clear_betting(state)
            self._enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)
            return
        if state.phase == GamePhaseEnum.BETTING_OPEN and state.betting_player_id == user_id:
            state.current_bet = 0
            state.betting_player_id = None
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

    def _start_final(self, state: GameLobbyState) -> None:
        state.selecting_player_id = state.answering_player_id = None
        state.current_prompt_id = None
        self._clear_betting(state)
        self._clear_resolution(state)
        state.final_round = FinalRoundState(
            players=[
                FinalPlayerState(
                    user_id=player.user_id,
                    username=player.username,
                    score_before_final=player.score,
                )
                for player in state.players
                if not player.is_banned
                and player.user_id != state.host.user_id
                and player.score > 0
            ],
        )
        if not state.final_round.players:
            self._finish_final(state, skipped_reason="no_eligible_players")
            return
        state.phase = GamePhaseEnum.FINAL_BETTING
        state.timer_deadline = self._deadline(FINAL_BETTING_TIME_SECONDS)

    def _lock_final_wagers(self, state: GameLobbyState) -> None:
        final = state.final_round
        assert final is not None
        for player in final.players:
            if not player.removed:
                player.decision_submitted = True
        participants = [p for p in final.players if not p.removed and p.wager is not None]
        if not participants:
            self._finish_final(state, skipped_reason="all_passed")
            return
        final.reveal_order = [
            p.user_id
            for p in sorted(
                participants,
                key=lambda p: (p.score_before_final, p.username, p.user_id),
            )
        ]
        category = next(
            c
            for c in state.categories
            if c.kind == "final" and c.round_number == state.current_round
        )
        state.current_prompt_id = category.prompts[0].prompt_id
        state.phase = GamePhaseEnum.FINAL_ANSWERING
        state.timer_deadline = self._deadline(FINAL_ANSWERING_TIME_SECONDS)

    def _lock_final_answers(self, state: GameLobbyState) -> None:
        state.timer_deadline = None
        state.phase = GamePhaseEnum.FINAL_REVEAL
        self._open_final_reveal(state)

    def _open_final_reveal(self, state: GameLobbyState) -> None:
        final = state.final_round
        assert final is not None
        while final.reveal_index < len(final.reveal_order):
            player = next(
                p for p in final.players if p.user_id == final.reveal_order[final.reveal_index]
            )
            if player.removed:
                final.reveal_index += 1
                continue
            player.revealed = True
            if not player.answer and player.correct is None:
                self._apply_final_judgment(state, player, False)
            return
        self._finish_final(state)

    @staticmethod
    def _apply_final_judgment(
        state: GameLobbyState,
        player: FinalPlayerState,
        correct: bool,
    ) -> None:
        assert player.correct is None
        assert player.wager is not None
        live_player = find_game_player(state, player.user_id)
        assert live_player is not None
        live_player.score += player.wager if correct else -player.wager
        player.correct = correct

    @staticmethod
    def _finish_final(state: GameLobbyState, skipped_reason: str | None = None) -> None:
        assert state.final_round is not None
        state.final_round.skipped_reason = skipped_reason
        state.timer_deadline = None
        state.phase = GamePhaseEnum.FINISHED
        if not any(result.round_number == state.current_round for result in state.round_results):
            state.round_results.append(build_round_result(state))

    def _remove_final_player(self, state: GameLobbyState, user_id: int) -> None:
        final = state.final_round
        assert final is not None
        player = next((p for p in final.players if p.user_id == user_id), None)
        if player is None or player.removed:
            return
        player.removed = True
        if player.correct is None:
            player.wager = None
            player.answer = None
        if state.phase == GamePhaseEnum.FINAL_BETTING:
            if not any(not p.removed for p in final.players):
                self._finish_final(state, skipped_reason="no_participants")
            elif all(p.decision_submitted for p in final.players if not p.removed):
                self._lock_final_wagers(state)
        elif not any(not p.removed and p.wager is not None for p in final.players):
            self._finish_final(
                state,
                skipped_reason="no_participants"
                if not any(p.revealed for p in final.players)
                else None,
            )
        elif state.phase == GamePhaseEnum.FINAL_ANSWERING:
            if all(
                p.answer_submitted for p in final.players if not p.removed and p.wager is not None
            ):
                self._lock_final_answers(state)
        elif final.reveal_order[final.reveal_index] == user_id:
            final.reveal_index += 1
            self._open_final_reveal(state)

    def _require_final_deadline(self, state: GameLobbyState) -> None:
        if state.timer_deadline is None or self._clock() >= state.timer_deadline:
            raise BadRequestError("Final submission time has expired")

    @staticmethod
    def _final_player(state: GameLobbyState, user_id: int) -> FinalPlayerState:
        final = state.final_round
        assert final is not None
        player = next((p for p in final.players if p.user_id == user_id and not p.removed), None)
        live_player = find_game_player(state, user_id)
        if (
            player is None
            or live_player is None
            or live_player.is_banned
            or user_id == state.host.user_id
        ):
            raise ForbiddenError("You are not eligible for this Final")
        return player

    def _current_final_reveal(self, state: GameLobbyState, target_user_id: int) -> FinalPlayerState:
        self._require_phase(state, GamePhaseEnum.FINAL_REVEAL)
        final = state.final_round
        assert final is not None
        if final.reveal_order[final.reveal_index] != target_user_id:
            raise BadRequestError("The current Final reveal has changed")
        return self._final_player(state, target_user_id)

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
