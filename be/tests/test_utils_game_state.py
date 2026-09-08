from enums.game import GamePhaseEnum, GameResolutionEnum
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
)
from utils.game_state import build_public_game_state


def _state() -> GameLobbyState:
    return GameLobbyState(
        lobby_id=1,
        state_revision=3,
        host=GameHostState(user_id=1, username="host"),
        players=[
            GamePlayerState(user_id=2, username="visible"),
            GamePlayerState(user_id=3, username="banned", is_banned=True),
        ],
        categories=[
            GameCategoryState(
                category_id=1,
                name="Category",
                prompts=[
                    GamePromptState(
                        prompt_id=10,
                        question="Question",
                        answer="Answer",
                        question_type=QuestionTypeEnum.TEXT,
                        answer_type=AnswerTypeEnum.TEXT,
                        order=1,
                    ),
                ],
            ),
        ],
    )


def test_public_projection_hides_banned_players_and_inactive_questions() -> None:
    projected = build_public_game_state(_state())

    assert [player.user_id for player in projected.players] == [2]
    assert projected.categories[0].prompts[0].question == ""


def test_public_projection_exposes_only_active_question() -> None:
    state = _state()
    state.current_prompt_id = 10
    state.phase = GamePhaseEnum.PLAYER_ANSWERING

    projected = build_public_game_state(state)

    assert projected.categories[0].prompts[0].question == "Question"
    assert projected.resolved_answer is None


def test_public_projection_reveals_answer_only_during_reveal() -> None:
    state = _state()
    state.phase = GamePhaseEnum.ANSWER_REVEAL
    state.resolved_prompt_id = 10
    state.resolved_answer = "Answer"
    state.resolved_answer_type = AnswerTypeEnum.TEXT
    state.resolution = GameResolutionEnum.CORRECT

    projected = build_public_game_state(state, include_banned_players=True)

    assert [player.user_id for player in projected.players] == [2, 3]
    assert projected.resolved_answer == "Answer"
    assert projected.resolution == GameResolutionEnum.CORRECT
