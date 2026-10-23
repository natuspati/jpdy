import random
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from configs.constants import (
    ANSWER_REVEAL_TIME_SECONDS,
    BETTING_ANNOUNCEMENT_SECONDS,
    BETTING_TIME_SECONDS,
    MAX_BET_MULTIPLIER,
    NUM_PROMPTS_IN_CATEGORY,
)
from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from errors.request import BadRequestError, ForbiddenError
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
)
from services.game_state_machine import GameStateMachine
from services.game_state_materializer import GameStateMaterializer, default_betting_prompt_count
from utils.game_state import build_public_game_state, round_score_value

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
HOST, ONE, TWO, THREE = 1, 2, 3, 4
BETTING_PROMPT, NORMAL_PROMPT = 10, 11


def _machine() -> GameStateMachine:
    return GameStateMachine(clock=lambda: NOW)


def _state(*, player_count: int = 3, scores: tuple[int, ...] = (0, 0, 0)) -> GameLobbyState:
    users = [(ONE, "one"), (TWO, "two"), (THREE, "three")][:player_count]
    prompts = [
        GamePromptState(
            prompt_id=prompt_id,
            question=f"Question {prompt_id}",
            answer=f"Answer {prompt_id}",
            order=order,
            score_value=order * 100,
            is_betting=prompt_id == BETTING_PROMPT,
        )
        for order, prompt_id in ((2, BETTING_PROMPT), (3, NORMAL_PROMPT))
    ]
    return GameLobbyState(
        lobby_id=1,
        host=GameHostState(user_id=HOST, username="host"),
        players=[
            GamePlayerState(
                user_id=user_id,
                username=name,
                score=score,
                connection_status=PlayerConnectionStatusEnum.CONNECTED,
            )
            for (user_id, name), score in zip(users, scores, strict=False)
        ],
        categories=[GameCategoryState(category_id=1, name="Category", prompts=prompts)],
        phase=GamePhaseEnum.PLAYER_SELECTING_PROMPT,
        selecting_player_id=ONE,
    )


def _announcement_state(**kwargs) -> GameLobbyState:
    state = _state(**kwargs)
    _machine().select_prompt(state, ONE, BETTING_PROMPT)
    return state


def _betting_state(**kwargs) -> GameLobbyState:
    state = _announcement_state(**kwargs)
    _expire(_machine(), state)
    return state


def _expire(machine: GameStateMachine, state: GameLobbyState) -> None:
    state.timer_deadline = NOW - timedelta(seconds=1)
    machine.expire_timer(state, None, None)


def _lobby(category_count: int, rounds: list[int]) -> tuple[SimpleNamespace, dict[int, int]]:
    categories = [
        SimpleNamespace(
            id=cid,
            name=f"c{cid}",
            kind="standard",
            prompts=[
                SimpleNamespace(
                    id=cid * 10 + order,
                    question="q",
                    answer="a",
                    order=order,
                    question_type=QuestionTypeEnum.TEXT,
                    answer_type=AnswerTypeEnum.TEXT,
                    question_media_asset=None,
                    answer_media_asset=None,
                )
                for order in range(1, 6)
            ],
        )
        for cid in range(1, category_count + 1)
    ]
    lobby = SimpleNamespace(
        id=1,
        owner=SimpleNamespace(id=1, username="host"),
        prompt_categories=categories,
    )
    return lobby, {cid: rounds[cid - 1] for cid in range(1, category_count + 1)}


def _betting_ids(state: GameLobbyState, round_number: int) -> list[int]:
    return [
        p.prompt_id
        for c in state.categories
        if c.round_number == round_number
        for p in c.prompts
        if p.is_betting
    ]


def test_default_count_is_ten_percent_rounded_down() -> None:
    assert default_betting_prompt_count(25) == 2
    assert default_betting_prompt_count(5) == 0


def test_materializer_draws_default_per_round_and_clamps() -> None:
    lobby, rounds = _lobby(6, [1, 1, 1, 1, 1, 2])
    state = GameStateMaterializer.build_game_lobby_state(lobby, rounds, None)
    assert len(_betting_ids(state, 1)) == 2
    assert _betting_ids(state, 2) == []

    custom = GameStateMaterializer.build_game_lobby_state(lobby, rounds, 3)
    assert len(_betting_ids(custom, 1)) == 3
    assert len(_betting_ids(custom, 2)) == 3

    clamped = GameStateMaterializer.build_game_lobby_state(lobby, rounds, 25)
    assert len(_betting_ids(clamped, 1)) == 25
    assert len(_betting_ids(clamped, 2)) == 5

    none = GameStateMaterializer.build_game_lobby_state(lobby, rounds, 0)
    assert _betting_ids(none, 1) == _betting_ids(none, 2) == []


def test_materializer_rng_is_seeded_and_draws_each_round_from_its_own_prompts() -> None:
    lobby, rounds = _lobby(2, [1, 2])
    first = GameStateMaterializer.build_game_lobby_state(lobby, rounds, 2, random.Random(7))
    again = GameStateMaterializer.build_game_lobby_state(lobby, rounds, 2, random.Random(7))
    assert _betting_ids(first, 1) == _betting_ids(again, 1)
    assert all(pid // 10 == 1 for pid in _betting_ids(first, 1))
    assert all(pid // 10 == 2 for pid in _betting_ids(first, 2))


def test_materializer_snapshots_final_without_points_or_random_betting() -> None:
    lobby, rounds = _lobby(2, [1, 2])
    lobby.prompt_categories[1].kind = "final"
    lobby.prompt_categories[1].prompts = lobby.prompt_categories[1].prompts[:1]
    state = GameStateMaterializer.build_game_lobby_state(lobby, rounds, 3)

    assert state.total_rounds == 2
    assert len(_betting_ids(state, 1)) == 3
    assert _betting_ids(state, 2) == []
    final = state.categories[1]
    assert final.kind == "final"
    assert final.prompts[0].score_value is None
    lobby.prompt_categories[1].prompts[0].question = "edited later"
    assert final.prompts[0].question == "q"


def test_public_projection_hides_betting_flag_and_question_until_selected() -> None:
    state = _state()
    assert not any(p.is_betting for p in build_public_game_state(state).categories[0].prompts)

    _machine().select_prompt(state, ONE, BETTING_PROMPT)
    projected = build_public_game_state(state)
    current = projected.categories[0].prompts[0]
    assert current.is_betting
    assert current.question == ""
    assert (projected.min_bet, projected.max_bet) == (200, 2500)


def test_bets_are_private_to_their_owner() -> None:
    state = _betting_state()
    _machine().place_bet(state, ONE, 300)
    assert build_public_game_state(state).categories[0].prompts[0].question == ""
    assert build_public_game_state(state, viewer_user_id=ONE).my_bet == 300
    assert build_public_game_state(state, viewer_user_id=TWO).my_bet is None
    assert build_public_game_state(state).my_bet is None


def test_select_betting_prompt_enters_announcement_then_betting_open() -> None:
    machine = _machine()
    state = _announcement_state()
    assert state.phase == GamePhaseEnum.BETTING_ANNOUNCEMENT
    assert state.answering_player_id is None
    assert state.players[0].is_selected
    assert (state.min_bet, state.bets) == (200, {})
    assert state.timer_deadline == NOW + timedelta(seconds=BETTING_ANNOUNCEMENT_SECONDS)
    with pytest.raises(BadRequestError, match="Action not allowed"):
        machine.place_bet(state, ONE, 200)

    _expire(machine, state)
    assert state.phase == GamePhaseEnum.BETTING_OPEN
    assert state.timer_deadline == NOW + timedelta(seconds=BETTING_TIME_SECONDS)


def test_max_bet_is_the_multiplier_times_the_round_maximum() -> None:
    state = _state()
    state.current_round = state.categories[0].round_number = 2
    _machine().select_prompt(state, ONE, BETTING_PROMPT)
    assert state.max_bet == MAX_BET_MULTIPLIER * round_score_value(NUM_PROMPTS_IN_CATEGORY, 2)


@pytest.mark.parametrize(
    ("amount", "message"),
    [(100, "between"), (2501, "between"), (0, "between")],
)
def test_place_bet_enforces_limits(amount: int, message: str) -> None:
    with pytest.raises(BadRequestError, match=message):
        _machine().place_bet(_betting_state(), ONE, amount)


def test_place_bet_accepts_each_player_once() -> None:
    state = _betting_state()
    _machine().place_bet(state, TWO, 300)
    assert state.bets == {TWO: 300}
    with pytest.raises(BadRequestError, match="already"):
        _machine().place_bet(state, TWO, 400)


def test_place_bet_rejects_ineligible_senders_and_expired_deadline() -> None:
    machine = _machine()
    with pytest.raises(BadRequestError, match="Action not allowed"):
        machine.place_bet(_state(), ONE, 200)
    with pytest.raises(ForbiddenError):
        machine.place_bet(_betting_state(), HOST, 200)
    banned = _betting_state()
    banned.players[1].is_banned = True
    with pytest.raises(ForbiddenError):
        machine.place_bet(banned, TWO, 500)
    expired = _betting_state()
    expired.timer_deadline = NOW
    with pytest.raises(BadRequestError, match="expired"):
        machine.place_bet(expired, ONE, 200)


def test_highest_bet_wins_and_sets_prompt_value() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, TWO, 500)
    machine.place_bet(state, THREE, 800)
    _expire(machine, state)
    assert state.phase == GamePhaseEnum.PLAYER_ANSWERING
    assert state.answering_player_id == state.selecting_player_id == THREE
    assert state.categories[0].prompts[0].score_value == 800
    assert state.attempted_player_ids == []
    assert [p.is_selected for p in state.players] == [False, False, True]
    assert (state.min_bet, state.max_bet, state.bets) == (0, 0, {})


def test_tied_bets_go_to_the_earliest_submitter() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, THREE, 500)
    machine.place_bet(state, TWO, 500)
    _expire(machine, state)
    assert state.answering_player_id == THREE


def test_selector_default_wins_a_tie_at_the_minimum() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, TWO, 200)
    _expire(machine, state)
    assert state.answering_player_id == ONE


def test_selector_bet_is_ranked_by_submission_time() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, TWO, 400)
    machine.place_bet(state, ONE, 400)
    _expire(machine, state)
    assert state.answering_player_id == TWO


def test_non_bettors_are_excluded() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, THREE, 300)
    _expire(machine, state)
    assert state.answering_player_id == THREE
    assert state.categories[0].prompts[0].score_value == 300


def test_betting_resolves_early_once_every_eligible_player_has_bet() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, ONE, 300)
    machine.place_bet(state, TWO, 400)
    assert state.phase == GamePhaseEnum.BETTING_OPEN
    machine.place_bet(state, THREE, 350)
    assert state.phase == GamePhaseEnum.PLAYER_ANSWERING
    assert state.answering_player_id == TWO


def test_nobody_bets_selector_answers_at_default_value() -> None:
    machine = _machine()
    state = _betting_state()
    min_bet = state.min_bet
    _expire(machine, state)
    assert state.phase == GamePhaseEnum.PLAYER_ANSWERING
    assert state.answering_player_id == state.selecting_player_id == ONE
    assert state.categories[0].prompts[0].score_value == min_bet
    state.timer_deadline = NOW + timedelta(seconds=10)
    machine.judge_answer(state, HOST, False)
    assert state.players[0].score == -min_bet
    assert state.resolution == GameResolutionEnum.UNANSWERED
    assert state.selecting_player_id == ONE


def _answering_bettor(
    bet: int = 500,
    scores: tuple[int, ...] = (0, 1000, 0),
    rng: random.Random | None = None,
) -> tuple[GameStateMachine, GameLobbyState]:
    machine = GameStateMachine(clock=lambda: NOW, rng=rng)
    state = _betting_state(scores=scores)
    machine.place_bet(state, TWO, bet)
    _expire(machine, state)
    state.timer_deadline = NOW + timedelta(seconds=10)
    return machine, state


def test_correct_bet_adds_bet_and_bettor_selects_next() -> None:
    machine, state = _answering_bettor()
    machine.judge_answer(state, HOST, True)
    assert state.players[1].score == 1500
    assert state.resolution == GameResolutionEnum.CORRECT
    assert state.selecting_player_id == TWO


def test_wrong_bet_deducts_without_buzz_window_and_lowest_selects_next() -> None:
    machine, state = _answering_bettor(scores=(100, 1000, 300))
    machine.judge_answer(state, HOST, False)
    assert state.players[1].score == 500
    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.resolution == GameResolutionEnum.UNANSWERED
    assert state.selecting_player_id == ONE


def test_timeout_deducts_bet_and_lowest_selects_next() -> None:
    machine, state = _answering_bettor(scores=(300, 1000, 100))
    _expire(machine, state)
    assert state.players[1].score == 500
    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.resolution == GameResolutionEnum.EXPIRED
    assert state.selecting_player_id == THREE
    assert state.timer_deadline == NOW + timedelta(seconds=ANSWER_REVEAL_TIME_SECONDS)


def test_bettor_who_becomes_uniquely_lowest_keeps_selecting() -> None:
    machine, state = _answering_bettor(scores=(100, 300, 200))
    machine.judge_answer(state, HOST, False)
    assert state.players[1].score == -200
    assert state.selecting_player_id == TWO


def test_tied_lowest_players_are_picked_with_the_seeded_rng() -> None:
    expected = random.Random(3).choice([ONE, TWO])
    machine, state = _answering_bettor(bet=300, scores=(0, 300, 500), rng=random.Random(3))
    machine.judge_answer(state, HOST, False)
    assert state.players[0].score == state.players[1].score == 0
    assert state.selecting_player_id == expected


def test_disconnected_and_banned_players_are_not_picked() -> None:
    machine, state = _answering_bettor(scores=(0, 1000, 100))
    state.players[0].connection_status = PlayerConnectionStatusEnum.DISCONNECTED
    machine.judge_answer(state, HOST, False)
    assert state.selecting_player_id == THREE


def test_no_eligible_player_clears_selector_and_falls_back_to_host() -> None:
    machine, state = _answering_bettor(scores=(0, 1000, 0))
    for player in (state.players[0], state.players[2]):
        player.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
    state.players[1].connection_status = PlayerConnectionStatusEnum.DISCONNECTED
    machine.judge_answer(state, HOST, False)
    assert state.selecting_player_id is None
    machine.advance_answer_reveal(state, HOST)
    assert state.phase == GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER


def test_ban_selector_during_betting_leaves_others_to_compete() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, TWO, 400)
    state.players[0].is_banned = True
    machine.ban_player(state, HOST, ONE)
    assert state.phase == GamePhaseEnum.BETTING_OPEN
    _expire(machine, state)
    assert state.answering_player_id == TWO


def test_ban_selector_with_no_bets_spends_prompt_without_scoring() -> None:
    machine = _machine()
    state = _betting_state()
    state.players[0].is_banned = True
    machine.ban_player(state, HOST, ONE)
    _expire(machine, state)
    assert state.phase == GamePhaseEnum.ANSWER_REVEAL
    assert state.resolution == GameResolutionEnum.EXPIRED
    assert state.categories[0].prompts[0].is_selected
    assert all(p.score == 0 for p in state.players)


def test_ban_bettor_discards_their_bet() -> None:
    machine = _machine()
    state = _betting_state()
    machine.place_bet(state, TWO, 400)
    machine.place_bet(state, THREE, 300)
    machine.ban_player(state, HOST, TWO)
    assert state.bets == {THREE: 300}
    _expire(machine, state)
    assert state.answering_player_id == THREE


async def test_host_receives_answer_key_when_betting_resolves(monkeypatch) -> None:
    from sockets import broadcast

    emit = AsyncMock()
    monkeypatch.setattr(broadcast.sio, "emit", emit)
    _, state = _answering_bettor()

    await broadcast.broadcast_state(state.lobby_id, state)

    key_calls = [c for c in emit.await_args_list if c.args[0] == broadcast.HOST_ANSWER_KEY_EVENT]
    assert len(key_calls) == 1
    assert key_calls[0].args[1]["expected_answer"] == f"Answer {BETTING_PROMPT}"
