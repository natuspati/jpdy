import asyncio
from datetime import UTC, datetime, timedelta
from functools import partial
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from database import UnitOfWork
from enums.game import GamePhaseEnum
from enums.lobby import LobbyStateEnum
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from errors.request import BadRequestError, ForbiddenError
from models.lobby import Lobby, LobbyRoundResult
from repos.game_state import GameStateRepo
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
)
from schemas.media import MediaReferenceSchema
from schemas.socket.events import (
    BanPlayerPayload,
    JudgeFinalAnswerPayload,
    SubmitFinalAnswerPayload,
    SubmitFinalWagerPayload,
)
from services.game import GameService
from services.game_state_machine import GameStateMachine
from utils.game_state import build_public_game_state, build_round_result

NOW = datetime(2026, 10, 18, tzinfo=UTC)
HOST, ONE, TWO = 1, 2, 3


def _state(scores=(100, 200)) -> GameLobbyState:
    state = GameLobbyState(
        lobby_id=1,
        host=GameHostState(user_id=HOST, username="host"),
        players=[
            GamePlayerState(user_id=index, username=f"player{index}", score=score)
            for index, score in enumerate(scores, start=ONE)
        ],
        categories=[
            GameCategoryState(
                category_id=1,
                name="Normal",
                prompts=[
                    GamePromptState(
                        prompt_id=1,
                        question="q",
                        answer="a",
                        order=1,
                        score_value=100,
                        is_selected=True,
                    ),
                ],
            ),
            GameCategoryState(
                category_id=2,
                name="Final",
                kind="final",
                round_number=2,
                prompts=[
                    GamePromptState(
                        prompt_id=2,
                        question="SECRET QUESTION",
                        answer="SECRET CANONICAL",
                        question_type=QuestionTypeEnum.IMAGE,
                        answer_type=AnswerTypeEnum.IMAGE,
                        question_media=MediaReferenceSchema(
                            asset_id=1,
                            url="/media/final-question.webp",
                            mime_type="image/webp",
                            filename="q.webp",
                        ),
                        answer_media=MediaReferenceSchema(
                            asset_id=2,
                            url="/media/final-answer.webp",
                            mime_type="image/webp",
                            filename="a.webp",
                        ),
                        order=1,
                        score_value=None,
                    ),
                ],
            ),
        ],
        total_rounds=2,
        phase=GamePhaseEnum.ROUND_SUMMARY,
    )
    state.round_results.append(build_round_result(state))
    return state


def _start(scores=(100, 200)):
    state = _state(scores)
    machine = GameStateMachine(clock=lambda: NOW)
    machine.advance_round(state, HOST)
    return machine, state


def _answering():
    machine, state = _start()
    machine.submit_final_wager(state, ONE, 100)
    machine.submit_final_wager(state, TWO, 150)
    return machine, state


def _reveal():
    machine, state = _answering()
    machine.submit_final_answer(state, ONE, "  first response ")
    machine.submit_final_answer(state, TWO, "later response")
    return machine, state


def test_last_normal_reveal_routes_through_summary_before_final():
    machine = GameStateMachine(clock=lambda: NOW)
    state = _state()
    state.round_results = []
    state.phase = GamePhaseEnum.ANSWER_REVEAL
    state.current_prompt_id = 1
    machine.advance_answer_reveal(state, HOST)
    assert state.phase == GamePhaseEnum.ROUND_SUMMARY
    assert state.current_round == 1
    assert state.final_round is None
    assert len(state.round_results) == 1
    machine.advance_round(state, HOST)
    assert state.phase == GamePhaseEnum.FINAL_BETTING
    assert state.current_round == 2


def test_final_freezes_positive_non_banned_roster_even_offline():
    state = _state((100, 0, -10, 20))
    state.players[-1].is_banned = True
    machine = GameStateMachine(clock=lambda: NOW)
    machine.advance_round(state, HOST)

    assert state.phase == GamePhaseEnum.FINAL_BETTING
    assert state.current_round == state.total_rounds == 2
    assert state.final_round is not None
    assert [p.user_id for p in state.final_round.players] == [ONE]
    assert state.final_round.players[0].score_before_final == 100
    assert state.timer_deadline == NOW + timedelta(seconds=30)
    machine.connect_user(state, ONE, "player2")
    assert state.final_round.players[0].score_before_final == 100
    assert state.timer_deadline == NOW + timedelta(seconds=30)
    with pytest.raises(ForbiddenError):
        machine.submit_final_wager(state, TWO, 1)
    with pytest.raises(ForbiddenError):
        machine.submit_final_wager(state, HOST, 1)


@pytest.mark.parametrize("amount", [True, False, 0, -1, 1.5, "10", 101])
def test_final_rejects_invalid_wagers(amount):
    machine, state = _start()
    with pytest.raises(BadRequestError, match="integer"):
        machine.submit_final_wager(state, ONE, amount)


@pytest.mark.parametrize("amount", [True, False, 0, -1, 1.5, "10"])
def test_socket_wager_validation_is_strict(amount):
    with pytest.raises(ValidationError):
        SubmitFinalWagerPayload(amount=amount)
    with pytest.raises(ValidationError):
        SubmitFinalWagerPayload()
    with pytest.raises(ValidationError):
        SubmitFinalAnswerPayload(answer="x" * 257)


def test_wagers_and_answers_are_final_and_do_not_extend_deadlines():
    machine, state = _start()
    deadline = state.timer_deadline
    machine.submit_final_wager(state, ONE, 100)
    assert state.timer_deadline == deadline
    with pytest.raises(BadRequestError, match="already"):
        machine.submit_final_wager(state, ONE, None)
    machine.submit_final_wager(state, TWO, 1)
    assert state.phase == GamePhaseEnum.FINAL_ANSWERING
    deadline = state.timer_deadline
    machine.submit_final_answer(state, ONE, "submitted")
    assert state.timer_deadline == deadline
    with pytest.raises(BadRequestError, match="already"):
        machine.submit_final_answer(state, ONE, "replacement")
    with pytest.raises(BadRequestError, match="256"):
        machine.submit_final_answer(state, TWO, "x" * 257)


@pytest.mark.parametrize("phase", ["wager", "answer"])
def test_submission_at_deadline_rejected_before_timer_worker(phase):
    machine, state = _start() if phase == "wager" else _answering()
    state.timer_deadline = NOW
    submission = (
        partial(machine.submit_final_wager, state, ONE, 10)
        if phase == "wager"
        else partial(machine.submit_final_answer, state, ONE, "late")
    )
    with pytest.raises(BadRequestError, match="expired"):
        submission()


def test_pass_timeout_and_no_eligible_skip_without_revealing_question():
    machine, state = _start((0, -10))
    assert state.phase == GamePhaseEnum.FINISHED
    assert state.final_round.skipped_reason == "no_eligible_players"
    assert [s.score_delta for s in state.round_results[-1].scores] == [0, 0]

    machine, state = _start()
    machine.submit_final_wager(state, ONE, None)
    state.timer_deadline = NOW
    machine.expire_timer(state, None, None)
    assert state.phase == GamePhaseEnum.FINISHED
    assert state.final_round.skipped_reason == "all_passed"
    assert [p.score for p in state.players] == [100, 200]
    assert len(state.round_results) == 2
    view = build_public_game_state(state, viewer_user_id=HOST)
    prompt = view.categories[-1].prompts[0]
    assert prompt.question == ""
    assert prompt.question_media is None
    assert prompt.answer_media is None
    assert view.final_round.correct_answer is None


def test_reveal_judgment_is_fenced_and_explicit_next_preserves_order():
    machine, state = _reveal()
    assert state.final_round.reveal_order == [ONE, TWO]
    assert state.final_round.players[0].answer == "first response"
    assert state.timer_deadline is None
    with pytest.raises(BadRequestError, match="before advancing"):
        machine.advance_final_reveal(state, HOST, ONE)
    with pytest.raises(ForbiddenError):
        machine.judge_final_answer(state, ONE, ONE, True)
    with pytest.raises(BadRequestError, match="changed"):
        machine.judge_final_answer(state, HOST, TWO, True)
    machine.judge_final_answer(state, HOST, ONE, True)
    assert state.phase == GamePhaseEnum.FINAL_REVEAL
    assert state.players[0].score == 200
    with pytest.raises(BadRequestError, match="already"):
        machine.judge_final_answer(state, HOST, ONE, False)
    machine.advance_final_reveal(state, HOST, ONE)
    with pytest.raises(BadRequestError, match="changed"):
        machine.advance_final_reveal(state, HOST, ONE)
    assert state.final_round.reveal_order == [ONE, TWO]
    machine.judge_final_answer(state, HOST, TWO, False)
    assert state.players[1].score == 50
    assert len(state.round_results) == 1
    machine.advance_final_reveal(state, HOST, TWO)
    assert state.phase == GamePhaseEnum.FINISHED
    assert [s.score_delta for s in state.round_results[-1].scores] == [100, -150]


def test_reveal_ties_use_username_then_id_not_current_score():
    machine, state = _start((100, 100, 100))
    state.final_round.players[0].username = "z"
    for player in state.final_round.players[1:]:
        player.username = "a"
    for user_id in (ONE, TWO, TWO + 1):
        machine.submit_final_wager(state, user_id, 1)
    assert state.final_round.reveal_order == [TWO, TWO + 1, ONE]


def test_empty_and_missing_answers_score_only_when_their_visible_reveal_opens():
    machine, state = _answering()
    machine.submit_final_answer(state, ONE, " \n ")
    assert [p.score for p in state.players] == [100, 200]
    state.timer_deadline = NOW
    machine.expire_timer(state, None, None)
    assert state.final_round.players[0].revealed
    assert state.final_round.players[0].correct is False
    assert state.final_round.players[1].correct is None
    assert [p.score for p in state.players] == [0, 200]
    assert build_public_game_state(state).final_round.current_user_id == ONE
    machine.advance_final_reveal(state, HOST, ONE)
    assert state.phase == GamePhaseEnum.FINAL_REVEAL
    assert state.final_round.players[1].revealed
    assert state.final_round.players[1].correct is False
    assert [p.score for p in state.players] == [0, 50]
    machine.advance_final_reveal(state, HOST, TWO)
    assert state.phase == GamePhaseEnum.FINISHED


def test_final_privacy_for_host_and_players_across_all_phases():
    state = _state()
    before = build_public_game_state(state).model_dump_json()
    assert "SECRET QUESTION" not in before
    assert "SECRET CANONICAL" not in before
    assert "/media/final-" not in before
    machine = GameStateMachine(clock=lambda: NOW)
    machine.advance_round(state, HOST)
    machine.submit_final_wager(state, ONE, 73)
    assert build_public_game_state(state, viewer_user_id=ONE).final_round.players[0].wager == 73
    for viewer in (HOST, TWO):
        view = build_public_game_state(
            state,
            viewer_user_id=viewer,
            include_banned_players=viewer == HOST,
        )
        assert view.final_round.players[0].wager is None
        assert view.categories[-1].prompts[0].question_media is None
    machine.submit_final_wager(state, TWO, 101)
    machine.submit_final_answer(state, TWO, "secret second response")
    for viewer in (HOST, ONE):
        view = build_public_game_state(state, viewer_user_id=viewer)
        assert view.final_round.players[1].answer is None
        assert view.categories[-1].prompts[0].question == "SECRET QUESTION"
        assert view.categories[-1].prompts[0].question_media is not None
        assert view.categories[-1].prompts[0].answer_media is None
    machine.submit_final_answer(state, ONE, "first")
    for viewer in (HOST, ONE):
        view = build_public_game_state(state, viewer_user_id=viewer)
        assert view.final_round.players[0].answer == "first"
        assert view.final_round.players[1].answer is None
        assert view.final_round.correct_answer == "SECRET CANONICAL"
        assert view.final_round.correct_answer_media is not None
        assert view.resolved_answer is None
    assert build_public_game_state(state, viewer_user_id=HOST).final_round.players[0].wager is None
    machine.judge_final_answer(state, HOST, ONE, True)
    assert build_public_game_state(state, viewer_user_id=HOST).final_round.players[0].wager == 73


def test_bans_void_unjudged_wagers_and_unban_does_not_reenter():
    machine, state = _start()
    machine.submit_final_wager(state, ONE, 100)
    machine.ban_player(state, HOST, ONE)
    machine.unban_player(state, HOST, ONE)
    with pytest.raises(ForbiddenError):
        machine.submit_final_wager(state, ONE, 1)
    machine.submit_final_wager(state, TWO, None)
    assert state.phase == GamePhaseEnum.FINISHED
    assert state.players[0].score == 100
    assert state.final_round.players[0].removed
    assert state.final_round.players[0].wager is None

    machine, state = _answering()
    machine.submit_final_answer(state, ONE, "first")
    machine.ban_player(state, HOST, TWO)
    assert state.phase == GamePhaseEnum.FINAL_REVEAL
    assert state.final_round.players[1].correct is None
    assert state.players[1].score == 200
    machine.ban_player(state, HOST, ONE)
    assert state.phase == GamePhaseEnum.FINISHED
    assert [p.score for p in state.players] == [100, 200]
    assert [p.user_id for p in build_public_game_state(state).final_round.players] == []
    assert len(build_public_game_state(state, include_banned_players=True).final_round.players) == 2


def test_banning_current_reveal_preserves_judgment_and_opens_next():
    machine, state = _reveal()
    machine.judge_final_answer(state, HOST, ONE, True)
    machine.ban_player(state, HOST, ONE)
    assert state.players[0].score == 200
    assert build_public_game_state(state).final_round.current_user_id == TWO
    machine.ban_player(state, HOST, TWO)
    assert state.phase == GamePhaseEnum.FINISHED
    assert [s.score_delta for s in state.round_results[-1].scores] == [100, 0]


async def test_redis_deduplicates_and_serializes_final_commands(redis_client):
    machine, state = _start()
    repo = GameStateRepo(redis_client)
    await repo.save_state(state)
    wagers = [(ONE, 100), (TWO, 150)]
    await asyncio.gather(
        *(
            repo.execute(
                1,
                f"wager-{user_id}",
                "submit_final_wager",
                partial(machine.submit_final_wager, user_id=user_id, amount=amount),
            )
            for user_id, amount in wagers
        ),
    )
    answers = [
        repo.execute(
            1,
            f"answer-{user_id}",
            "submit_final_answer",
            partial(machine.submit_final_answer, user_id=user_id, answer="answer"),
        )
        for user_id, _ in wagers
    ]
    await asyncio.gather(*answers)
    state = await repo.get_state(1)
    assert state.phase == GamePhaseEnum.FINAL_REVEAL
    assert state.state_revision == 4
    judge = partial(machine.judge_final_answer, user_id=HOST, target_user_id=ONE, correct=True)
    await asyncio.gather(
        repo.execute(1, "same-judgment", "judge_final_answer", judge),
        repo.execute(1, "same-judgment", "judge_final_answer", judge),
    )
    state = await repo.get_state(1)
    assert state.players[0].score == 200
    assert state.state_revision == 5
    for user_id in (ONE, TWO):
        if user_id == TWO:
            await repo.execute(
                1,
                str(uuid4()),
                "judge_final_answer",
                partial(
                    machine.judge_final_answer,
                    user_id=HOST,
                    target_user_id=user_id,
                    correct=False,
                ),
            )
        advance = partial(machine.advance_final_reveal, user_id=HOST, target_user_id=user_id)
        await repo.execute(1, f"advance-{user_id}", "advance_final_reveal", advance)
        await repo.execute(1, f"advance-{user_id}", "advance_final_reveal", advance)
    state = await repo.get_state(1)
    assert state.phase == GamePhaseEnum.FINISHED
    assert [p.score for p in state.players] == [200, 50]
    assert len(state.round_results) == 2


async def test_recovered_final_timer_uses_original_deadline_and_stale_timer_is_noop(redis_client):
    machine, state = _start()
    repo = GameStateRepo(redis_client)
    state.timer_revision = 0
    await repo.save_state(state)
    deadline = state.timer_deadline
    await repo.execute(
        1,
        "wager",
        "submit_final_wager",
        partial(machine.submit_final_wager, user_id=ONE, amount=100),
    )
    recovered = await GameStateRepo(redis_client).get_state(1)
    assert recovered.timer_deadline == deadline
    assert recovered.timer_revision == 1
    expired_machine = GameStateMachine(clock=lambda: deadline)
    assert expired_machine.expire_timer(recovered, 0, deadline).state is None
    expired_machine.expire_timer(recovered, 1, deadline)
    assert recovered.phase == GamePhaseEnum.FINAL_ANSWERING
    assert recovered.final_round.players[1].wager is None
    assert recovered.timer_deadline == deadline + timedelta(seconds=30)


def test_older_snapshot_defaults_final_fields_to_ordinary_game():
    raw = _state().model_dump()
    raw.pop("final_round")
    raw["categories"] = raw["categories"][:1]
    raw["categories"][0].pop("kind")
    state = GameLobbyState.model_validate(raw)
    assert state.final_round is None
    assert state.categories[0].kind == "standard"


@pytest.mark.parametrize(
    "path",
    [
        "advance_no_eligible",
        "timer_no_eligible",
        "all_pass",
        "timer_all_pass",
        "ban_betting",
        "ban_answering",
        "ban_reveal",
    ],
)
async def test_every_final_skip_and_ban_finish_projects_completion(
    path,
    seed_lobby,
    db_session,
    redis_client,
):
    seeded = await seed_lobby(player_count=1)
    user = seeded.players[0]
    state = _state((0 if path.endswith("no_eligible") else 100,))
    state.lobby_id = seeded.lobby_id
    state.host.user_id = seeded.host.id
    state.players[0].user_id = user.id
    state.players[0].username = user.username
    state.round_results = [build_round_result(state)]
    state.timer_deadline = NOW
    await GameStateRepo(redis_client).save_state(state)
    service = GameService(UnitOfWork(db_session, redis_client))
    service._state_machine = GameStateMachine(clock=lambda: NOW)
    if path == "timer_no_eligible":
        finished = await service.expire_timer(state.lobby_id)
    else:
        finished = await service.advance_round(state.lobby_id, seeded.host.id)
        if path == "all_pass":
            finished = await service.submit_final_wager(
                state.lobby_id,
                user.id,
                SubmitFinalWagerPayload(amount=None),
            )
        elif path == "timer_all_pass":
            service._state_machine = GameStateMachine(clock=lambda: NOW + timedelta(seconds=30))
            finished = await service.expire_timer(state.lobby_id)
        elif path.startswith("ban_"):
            if path != "ban_betting":
                await service.submit_final_wager(
                    state.lobby_id,
                    user.id,
                    SubmitFinalWagerPayload(amount=50),
                )
            if path == "ban_reveal":
                await service.submit_final_answer(
                    state.lobby_id,
                    user.id,
                    SubmitFinalAnswerPayload(answer="manual judgment"),
                )
                await service.judge_final_answer(
                    state.lobby_id,
                    seeded.host.id,
                    JudgeFinalAnswerPayload(user_id=user.id, correct=True),
                )
            finished = await service.ban_player(
                state.lobby_id,
                seeded.host.id,
                BanPlayerPayload(user_id=user.id),
            )
    assert finished.phase == GamePhaseEnum.FINISHED
    if path in {"ban_betting", "ban_answering"}:
        assert finished.final_round.skipped_reason == "no_participants"
    await service._projections.project_completion(finished)
    await service._projections.project_completion(finished)
    assert (
        await db_session.scalar(
            select(Lobby.state).where(Lobby.id == state.lobby_id),
        )
        == LobbyStateEnum.COMPLETED
    )
    results = (
        await db_session.scalars(
            select(LobbyRoundResult)
            .where(LobbyRoundResult.lobby_id == state.lobby_id)
            .order_by(LobbyRoundResult.round_number),
        )
    ).all()
    assert len(results) == 2
    assert results[-1].score_delta == (50 if path == "ban_reveal" else 0)


async def test_last_submission_racing_expiry_opens_one_reveal_and_applies_once(redis_client):
    machine, state = _answering()
    machine.submit_final_answer(state, ONE, "")
    repo = GameStateRepo(redis_client)
    await repo.save_state(state)
    timer = GameStateMachine(clock=lambda: state.timer_deadline)
    outcomes = await asyncio.gather(
        repo.execute(
            1,
            "last-submission",
            "submit_final_answer",
            partial(machine.submit_final_answer, user_id=TWO, answer="answer"),
        ),
        repo.execute(
            1,
            "expiry",
            "expire_timer",
            partial(
                timer.expire_timer,
                expected_revision=None,
                expected_deadline=state.timer_deadline,
            ),
        ),
        return_exceptions=True,
    )
    assert any(isinstance(outcome, GameLobbyState) for outcome in outcomes)
    persisted = await repo.get_state(1)
    assert persisted.phase == GamePhaseEnum.FINAL_REVEAL
    assert [p.score for p in persisted.players] == [0, 200]
    assert persisted.final_round.players[0].correct is False
    assert persisted.final_round.players[1].correct is None
    assert len(persisted.round_results) == 1
