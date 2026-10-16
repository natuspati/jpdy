from datetime import UTC, datetime, timedelta

import pytest

from configs.constants import (
    ANSWER_REVEAL_TIME_SECONDS,
    ANSWERING_TIME_SECONDS,
    BUZZING_TIME_SECONDS,
    ROUND_SUMMARY_TIME_SECONDS,
)
from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from errors.request import BadRequestError, ForbiddenError
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
)
from services.game_state_machine import GameStateMachine

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
HOST_ID = 1
PLAYER_ONE_ID = 2
PLAYER_TWO_ID = 3
PROMPT_ONE_ID = 10
PROMPT_TWO_ID = 11


def _machine() -> GameStateMachine:
    return GameStateMachine(clock=lambda: NOW)


def _state(*, player_count: int = 2, prompt_count: int = 2) -> GameLobbyState:
    player_specs = [(PLAYER_ONE_ID, "one"), (PLAYER_TWO_ID, "two")][:player_count]
    prompts = [
        GamePromptState(
            prompt_id=prompt_id,
            question=f"Question {prompt_id}",
            answer=f"Answer {prompt_id}",
            order=index,
            score_value=index * 100,
        )
        for index, prompt_id in enumerate([PROMPT_ONE_ID, PROMPT_TWO_ID][:prompt_count], start=1)
    ]
    return GameLobbyState(
        lobby_id=1,
        host=GameHostState(user_id=HOST_ID, username="host"),
        players=[
            GamePlayerState(
                user_id=user_id,
                username=username,
                connection_status=PlayerConnectionStatusEnum.CONNECTED,
            )
            for user_id, username in player_specs
        ],
        categories=[GameCategoryState(category_id=1, name="Category", prompts=prompts)],
    )


def _answering_state(*, player_count: int = 2) -> GameLobbyState:
    state = _state(player_count=player_count)
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.current_prompt_id = PROMPT_ONE_ID
    state.selecting_player_id = PLAYER_ONE_ID
    state.answering_player_id = PLAYER_ONE_ID
    state.timer_deadline = NOW + timedelta(seconds=ANSWERING_TIME_SECONDS)
    state.categories[0].prompts[0].is_selected = True
    state.players[0].is_selected = True
    return state


def test_connect_user_enforces_roster_lock_and_ban() -> None:
    machine = _machine()
    state = _state(player_count=0)

    connected = machine.connect_user(state, PLAYER_ONE_ID, "one")

    assert connected.reason == "user_connected"
    assert state.players[0].connection_status == PlayerConnectionStatusEnum.CONNECTED
    state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
    with pytest.raises(ForbiddenError, match="roster is locked"):
        machine.connect_user(state, PLAYER_TWO_ID, "two")

    state.players[0].is_banned = True
    state.players[0].connection_status = PlayerConnectionStatusEnum.DISCONNECTED
    with pytest.raises(ForbiddenError, match="Player is banned"):
        machine.connect_user(state, PLAYER_ONE_ID, "one")


def test_assets_loaded_is_per_player_waiting_only_and_reset_on_reconnect() -> None:
    machine = _machine()
    state = _state()

    machine.set_assets_loaded(state, PLAYER_ONE_ID, True)
    assert [p.assets_loaded for p in state.players] == [True, False]
    with pytest.raises(ForbiddenError, match="Only lobby players"):
        machine.set_assets_loaded(state, HOST_ID, True)

    machine.disconnect_user(state, PLAYER_ONE_ID)
    assert state.players[0].assets_loaded is False
    machine.set_assets_loaded(state, PLAYER_TWO_ID, True)
    machine.connect_user(state, PLAYER_TWO_ID, "two")
    assert state.players[1].assets_loaded is False

    state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
    with pytest.raises(BadRequestError):
        machine.set_assets_loaded(state, PLAYER_ONE_ID, True)


def test_start_waits_for_loaded_players_unless_forced() -> None:
    machine = _machine()
    state = _state()

    with pytest.raises(BadRequestError, match="finish loading"):
        machine.start_game(state, HOST_ID)
    state.players[0].assets_loaded = True
    with pytest.raises(BadRequestError, match="finish loading"):
        machine.start_game(state, HOST_ID)

    state.players[1].connection_status = PlayerConnectionStatusEnum.DISCONNECTED
    machine.start_game(state, HOST_ID)
    assert state.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER

    forced = _state()
    machine.start_game(forced, HOST_ID, force=True)
    assert forced.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER


def test_start_and_selection_require_authorized_eligible_players() -> None:
    machine = _machine()
    state = _state(player_count=1)

    with pytest.raises(ForbiddenError, match="Only the host"):
        machine.start_game(state, PLAYER_ONE_ID)
    machine.start_game(state, HOST_ID, force=True)
    assert state.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER

    with pytest.raises(BadRequestError, match="not in this lobby"):
        machine.select_starter(state, HOST_ID, PLAYER_TWO_ID)
    machine.select_starter(state, HOST_ID, PLAYER_ONE_ID)
    assert state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert state.players[0].is_selected is True

    with pytest.raises(ForbiddenError, match="Only the selecting player"):
        machine.select_prompt(state, HOST_ID, PROMPT_ONE_ID)
    machine.select_prompt(state, PLAYER_ONE_ID, PROMPT_ONE_ID)
    assert state.phase == GamePhaseEnum.PLAYER_ANSWERING
    assert state.timer_deadline == NOW + timedelta(seconds=ANSWERING_TIME_SECONDS)


def test_judging_updates_score_and_opens_buzz_or_reveals() -> None:
    machine = _machine()
    state = _answering_state()

    judged = machine.judge_answer(state, HOST_ID, correct=False)

    assert judged.reason == "answer_judged"
    assert state.players[0].score == -100
    assert state.attempted_player_ids == [PLAYER_ONE_ID]
    assert state.phase == GamePhaseEnum.BUZZ_OPEN
    assert state.timer_deadline == NOW + timedelta(seconds=BUZZING_TIME_SECONDS)

    machine.buzz(state, PLAYER_TWO_ID)
    assert state.answering_player_id == PLAYER_TWO_ID
    assert state.phase == GamePhaseEnum.PLAYER_ANSWERING
    assert state.timer_deadline == NOW + timedelta(seconds=ANSWERING_TIME_SECONDS)

    state = _answering_state(player_count=1)
    machine.judge_answer(state, HOST_ID, correct=False)
    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.resolution == GameResolutionEnum.UNANSWERED
    assert state.resolved_answer == "Answer 10"


def test_buzz_checks_eligibility_and_uses_separate_answer_deadline() -> None:
    machine = _machine()
    state = _answering_state()
    machine.judge_answer(state, HOST_ID, correct=False)

    with pytest.raises(ForbiddenError, match="already attempted"):
        machine.buzz(state, PLAYER_ONE_ID)
    state.players[1].connection_status = PlayerConnectionStatusEnum.DISCONNECTED
    with pytest.raises(ForbiddenError, match="Disconnected"):
        machine.buzz(state, PLAYER_TWO_ID)

    state.players[1].connection_status = PlayerConnectionStatusEnum.CONNECTED
    machine.buzz(state, PLAYER_TWO_ID)
    assert state.timer_deadline == NOW + timedelta(seconds=ANSWERING_TIME_SECONDS)


def test_expire_timer_noops_are_fenced_and_timed_phases_progress() -> None:
    machine = _machine()
    state = _answering_state()

    state.timer_revision = 7
    assert machine.expire_timer(state, 8, None).reason == "stale_timer_revision"
    assert machine.expire_timer(state, 7, NOW).reason == "stale_timer_deadline"
    assert machine.expire_timer(state, 7, state.timer_deadline).reason == "timer_not_due"

    state.timer_deadline = NOW
    expired = machine.expire_timer(state, 7, NOW)
    assert expired.reason == "timer_expired"
    assert state.phase == GamePhaseEnum.BUZZ_OPEN
    assert state.attempted_player_ids == [PLAYER_ONE_ID]
    assert state.players[0].score == -100

    state.phase = GamePhaseEnum.WAITING_FOR_PLAYERS
    state.timer_deadline = NOW
    assert machine.expire_timer(state, None, None).reason == "timer_phase_not_timed"
    state.timer_deadline = None
    assert machine.expire_timer(state, None, None).reason == "no_timer"


def test_buzz_winner_timing_out_loses_points() -> None:
    machine = _machine()
    state = _answering_state()
    machine.judge_answer(state, HOST_ID, correct=False)
    machine.buzz(state, PLAYER_TWO_ID)
    state.timer_deadline = NOW

    machine.expire_timer(state, None, None)

    assert state.players[0].score == -100
    assert state.players[1].score == -100
    assert state.attempted_player_ids == [PLAYER_ONE_ID, PLAYER_TWO_ID]


def test_expire_timer_progresses_buzz_and_answer_reveal() -> None:
    machine = _machine()
    state = _answering_state()
    state.phase = GamePhaseEnum.BUZZ_OPEN
    state.answering_player_id = None
    state.timer_deadline = NOW

    machine.expire_timer(state, None, None)

    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.resolution == GameResolutionEnum.EXPIRED
    assert state.timer_deadline == NOW + timedelta(seconds=ANSWER_REVEAL_TIME_SECONDS)

    state.timer_deadline = NOW
    machine.expire_timer(state, None, None)

    assert state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert state.current_prompt_id is None
    assert state.timer_deadline is None


def test_reveal_advances_to_selector_or_finishes_after_final_reveal() -> None:
    machine = _machine()
    state = _answering_state()
    machine.judge_answer(state, HOST_ID, correct=True)

    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.players[0].score == 100
    machine.advance_answer_reveal(state, HOST_ID)
    assert state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert state.current_prompt_id is None
    assert state.selecting_player_id == PLAYER_ONE_ID

    state = _answering_state(player_count=1)
    state.categories[0].prompts = state.categories[0].prompts[:1]
    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)
    assert state.phase == GamePhaseEnum.FINISHED
    assert state.resolved_answer is None


def test_reveal_falls_back_to_host_when_selector_is_ineligible() -> None:
    machine = _machine()
    state = _answering_state()
    machine.judge_answer(state, HOST_ID, correct=True)
    state.players[0].connection_status = PlayerConnectionStatusEnum.DISCONNECTED

    machine.advance_answer_reveal(state, HOST_ID)

    assert state.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
    assert state.selecting_player_id is None
    assert not any(player.is_selected for player in state.players)


def test_banning_recovers_each_active_ownership_branch() -> None:
    machine = _machine()

    state = _state()
    state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
    state.selecting_player_id = PLAYER_ONE_ID
    state.players[0].is_selected = True
    machine.ban_player(state, HOST_ID, PLAYER_ONE_ID)
    assert state.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
    assert state.timer_deadline is None

    state = _answering_state()
    machine.ban_player(state, HOST_ID, PLAYER_ONE_ID)
    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.resolution == GameResolutionEnum.UNANSWERED
    assert state.selecting_player_id is None
    assert state.players[0].score == 0

    state = _answering_state()
    state.phase = GamePhaseEnum.BUZZ_OPEN
    state.answering_player_id = None
    state.attempted_player_ids = [PLAYER_ONE_ID]
    state.timer_deadline = NOW + timedelta(seconds=BUZZING_TIME_SECONDS)
    machine.ban_player(state, HOST_ID, PLAYER_TWO_ID)
    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.resolution == GameResolutionEnum.UNANSWERED


def test_banning_pending_selector_keeps_other_buzzers_eligible() -> None:
    machine = _machine()
    state = _answering_state()
    state.phase = GamePhaseEnum.BUZZ_OPEN
    state.answering_player_id = None
    state.attempted_player_ids = [PLAYER_ONE_ID]
    state.timer_deadline = NOW + timedelta(seconds=BUZZING_TIME_SECONDS)

    machine.ban_player(state, HOST_ID, PLAYER_ONE_ID)

    assert state.phase == GamePhaseEnum.BUZZ_OPEN
    assert state.selecting_player_id is None
    machine.buzz(state, PLAYER_TWO_ID)
    assert state.answering_player_id == PLAYER_TWO_ID


def test_unknown_disconnect_is_a_non_mutating_outcome() -> None:
    state = _state(player_count=1)

    outcome = _machine().disconnect_user(state, PLAYER_TWO_ID)

    assert outcome.reason == "unknown_disconnect"
    assert outcome.state is None
    assert outcome.result is state


def test_sound_cue_increments_with_existing_reason_name() -> None:
    state = _state()

    outcome = _machine().issue_sound_cue(state, "game_started")

    assert outcome.reason == "sound_cue:game_started"
    assert state.sound_cue_id == 1


ROUND_TWO_PROMPT_ID = 20


def _round_reveal_state(*, current_round: int = 1, total_rounds: int = 2) -> GameLobbyState:
    """Last prompt of ``current_round`` resolved and in answer reveal."""
    state = _state()
    state.categories[0].prompts = state.categories[0].prompts[:1]
    state.categories.append(
        GameCategoryState(
            category_id=2,
            name="Round two",
            round_number=2,
            prompts=[
                GamePromptState(
                    prompt_id=ROUND_TWO_PROMPT_ID,
                    question="Q",
                    answer="A",
                    order=1,
                    score_value=200,
                ),
            ],
        ),
    )
    state.total_rounds = total_rounds
    state.current_round = current_round
    state.phase = GamePhaseEnum.PLAYER_ANSWERING
    state.selecting_player_id = PLAYER_ONE_ID
    state.answering_player_id = PLAYER_ONE_ID
    state.timer_deadline = NOW + timedelta(seconds=ANSWERING_TIME_SECONDS)
    prompt_id = PROMPT_ONE_ID if current_round == 1 else ROUND_TWO_PROMPT_ID
    state.current_prompt_id = prompt_id
    for category in state.categories:
        for prompt in category.prompts:
            prompt.is_selected = category.round_number <= current_round
    return state


def test_end_of_non_final_round_enters_round_summary_with_scores_and_deltas() -> None:
    machine = _machine()
    state = _round_reveal_state()
    machine.judge_answer(state, HOST_ID, correct=True)
    state.players[1].score = 40

    machine.advance_answer_reveal(state, HOST_ID)

    assert state.phase == GamePhaseEnum.ROUND_SUMMARY
    assert state.selecting_player_id is None
    assert not any(player.is_selected for player in state.players)
    assert state.timer_deadline == NOW + timedelta(seconds=ROUND_SUMMARY_TIME_SECONDS)
    [result] = state.round_results
    assert result.round_number == 1
    assert [(s.user_id, s.score, s.score_delta) for s in result.scores] == [
        (PLAYER_ONE_ID, 100, 100),
        (PLAYER_TWO_ID, 40, 40),
    ]


def test_round_two_delta_is_relative_to_round_one() -> None:
    machine = _machine()
    state = _round_reveal_state()
    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)
    machine.advance_round(state, HOST_ID)

    state.categories[1].prompts[0].is_selected = True
    state.phase = GamePhaseEnum.ANSWER_REVEAL
    state.players[0].score = 100 + 200
    state.players[1].score = -50
    machine.advance_answer_reveal(state, HOST_ID)

    assert state.phase == GamePhaseEnum.FINISHED
    last = state.round_results[-1]
    assert last.round_number == 2
    assert [(s.score, s.score_delta) for s in last.scores] == [(300, 200), (-50, -50)]


def test_final_round_goes_straight_to_finished_and_records_result() -> None:
    machine = _machine()
    state = _round_reveal_state(current_round=2)
    state.round_results = []

    machine.judge_answer(state, HOST_ID, correct=True)
    assert state.players[0].score == 200
    machine.advance_answer_reveal(state, HOST_ID)

    assert state.phase == GamePhaseEnum.FINISHED
    assert state.selecting_player_id is None
    assert state.timer_deadline is None
    assert [r.round_number for r in state.round_results] == [2]


def test_single_round_game_still_finishes_directly() -> None:
    machine = _machine()
    state = _round_reveal_state(total_rounds=1)
    state.categories = state.categories[:1]

    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)

    assert state.phase == GamePhaseEnum.FINISHED
    assert len(state.round_results) == 1


def test_round_summary_expiry_starts_next_round_with_lowest_scorer() -> None:
    machine = _machine()
    state = _round_reveal_state()
    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)
    state.timer_deadline = NOW

    machine.expire_timer(state, state.timer_revision, state.timer_deadline)

    assert state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert state.current_round == 2
    assert state.selecting_player_id == PLAYER_TWO_ID
    assert state.players[1].is_selected is True
    assert state.timer_deadline is None


def test_advance_round_is_host_only_and_phase_gated() -> None:
    machine = _machine()
    state = _round_reveal_state()

    with pytest.raises(ForbiddenError, match="Only the host"):
        machine.advance_round(state, PLAYER_ONE_ID)
    with pytest.raises(BadRequestError, match="Action not allowed during phase"):
        machine.advance_round(state, HOST_ID)

    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)
    machine.advance_round(state, HOST_ID)
    assert state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert state.current_round == 2


def test_next_round_selector_falls_back_to_host_on_tied_lowest_score() -> None:
    machine = _machine()
    state = _round_reveal_state()
    machine.judge_answer(state, HOST_ID, correct=False)
    state.phase = GamePhaseEnum.ANSWER_REVEAL
    machine.advance_answer_reveal(state, HOST_ID)
    state.players[0].score = 0
    state.players[1].score = 0

    machine.advance_round(state, HOST_ID)

    assert state.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
    assert state.selecting_player_id is None
    assert state.current_round == 2


def test_next_round_selector_ignores_ineligible_and_falls_back_without_players() -> None:
    machine = _machine()
    state = _round_reveal_state()
    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)
    state.players[1].is_banned = True  # lowest scorer is banned

    machine.advance_round(state, HOST_ID)
    assert state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT
    assert state.selecting_player_id == PLAYER_ONE_ID

    state = _round_reveal_state()
    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)
    for player in state.players:
        player.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
    machine.advance_round(state, HOST_ID)
    assert state.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER


def test_select_prompt_rejects_prompt_from_another_round() -> None:
    machine = _machine()
    state = _round_reveal_state()
    machine.judge_answer(state, HOST_ID, correct=True)
    machine.advance_answer_reveal(state, HOST_ID)
    machine.advance_round(state, HOST_ID)

    with pytest.raises(BadRequestError, match="another round"):
        machine.select_prompt(state, PLAYER_TWO_ID, PROMPT_ONE_ID)

    machine.select_prompt(state, PLAYER_TWO_ID, ROUND_TWO_PROMPT_ID)
    assert state.phase == GamePhaseEnum.PLAYER_ANSWERING
