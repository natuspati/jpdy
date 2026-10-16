from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
    GameRoundResult,
    GameRoundScore,
)
from schemas.media import MediaReferenceSchema
from utils.game_state import (
    build_public_game_state,
    clear_game_player_selection_flags,
    current_round_prompts_spent,
    find_game_player,
    find_game_prompt,
    get_eligible_buzzers,
    is_eligible_game_player,
    round_score_value,
)


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
                        score_value=100,
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


def test_public_projection_exposes_question_media_for_whole_board_for_preload() -> None:
    state = _state()
    media = MediaReferenceSchema(
        asset_id=5,
        url="/media/abc.webp",
        mime_type="image/webp",
        filename="clue.png",
    )
    state.categories[0].prompts[0].question_media = media

    prompt = build_public_game_state(state).categories[0].prompts[0]

    assert prompt.question_media == media
    assert prompt.question == ""
    assert prompt.question_type == QuestionTypeEnum.TEXT


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


def test_shared_state_helpers_find_and_filter_live_entities() -> None:
    state = _state()
    state.players[0].connection_status = PlayerConnectionStatusEnum.CONNECTED
    state.players[0].is_selected = True
    state.players[1].connection_status = PlayerConnectionStatusEnum.CONNECTED

    assert find_game_player(state, 2) is state.players[0]
    assert find_game_player(state, None) is None
    assert find_game_prompt(state, 10) is state.categories[0].prompts[0]
    assert find_game_prompt(state, None) is None
    assert is_eligible_game_player(state.players[0]) is True
    assert get_eligible_buzzers(state) == [state.players[0]]

    clear_game_player_selection_flags(state)
    assert not any(player.is_selected for player in state.players)
    assert current_round_prompts_spent(state) is False
    state.categories[0].prompts[0].is_selected = True
    assert current_round_prompts_spent(state) is True


def test_round_score_value_doubles_each_round() -> None:
    assert [round_score_value(order, 1) for order in (1, 5)] == [100, 500]
    assert [round_score_value(order, 2) for order in (1, 5)] == [200, 1000]
    assert [round_score_value(order, 3) for order in (1, 5)] == [400, 2000]


def test_public_projection_hides_banned_scores_in_round_results_for_players_only() -> None:
    state = _state()
    state.total_rounds = 2
    state.round_results = [
        GameRoundResult(
            round_number=1,
            scores=[
                GameRoundScore(user_id=2, username="visible", score=100, score_delta=100),
                GameRoundScore(user_id=3, username="banned", score=300, score_delta=300),
            ],
        ),
    ]

    player_view = build_public_game_state(state)
    host_view = build_public_game_state(state, include_banned_players=True)

    assert [s.user_id for s in player_view.round_results[0].scores] == [2]
    assert [s.user_id for s in host_view.round_results[0].scores] == [2, 3]
    assert player_view.total_rounds == 2
    assert player_view.categories[0].prompts[0].score_value == 100
    assert len(state.round_results[0].scores) == 2
