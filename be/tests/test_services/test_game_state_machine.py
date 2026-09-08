from datetime import UTC, datetime, timedelta

import pytest

from configs.constants import (
    ANSWER_REVEAL_TIME_SECONDS,
    ANSWERING_TIME_SECONDS,
    BUZZING_TIME_SECONDS,
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


def test_start_and_selection_require_authorized_eligible_players() -> None:
    machine = _machine()
    state = _state(player_count=1)

    with pytest.raises(ForbiddenError, match="Only the host"):
        machine.start_game(state, PLAYER_ONE_ID)
    machine.start_game(state, HOST_ID)
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

    state.phase = GamePhaseEnum.WAITING_FOR_PLAYERS
    state.timer_deadline = NOW
    assert machine.expire_timer(state, None, None).reason == "timer_phase_not_timed"
    state.timer_deadline = None
    assert machine.expire_timer(state, None, None).reason == "no_timer"


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
