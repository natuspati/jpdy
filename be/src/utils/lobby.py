from collections import Counter
from typing import TYPE_CHECKING

from configs.constants import (
    MAX_CATEGORIES_PER_ROUND,
    MAX_ROUNDS_IN_LOBBY,
    MIN_CATEGORIES_PER_ROUND,
    MIN_ROUNDS_IN_LOBBY,
    NUM_PROMPTS_IN_CATEGORY,
)
from enums.lobby import LobbyStateEnum
from errors.request import BadRequestError, ForbiddenError, NotFoundError
from schemas.lobby.nested import (
    LobbyFinalRankingSchema,
    LobbyRoundResultSchema,
    LobbyRoundSchema,
    LobbyWithCategoriesInDBSchema,
)
from schemas.lobby.participant import LobbyParticipantInDBSchema, LobbyRoundResultInDBSchema
from schemas.prompt.category import PromptCategoryInDBSchema
from schemas.user.base import UserPublicSchema

if TYPE_CHECKING:
    from database import UnitOfWork


async def ensure_owned_lobby(
    uow: UnitOfWork,
    lobby_id: int,
    user: UserPublicSchema,
) -> LobbyWithCategoriesInDBSchema:
    lobby = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
    if lobby is None:
        raise NotFoundError(f"Lobby {lobby_id} not found")
    if lobby.owner_id != user.id:
        raise ForbiddenError("Only the owner can modify this lobby")
    return lobby


def _validate_round_sizes(round_sizes: list[int]) -> None:
    if not (MIN_ROUNDS_IN_LOBBY <= len(round_sizes) <= MAX_ROUNDS_IN_LOBBY):
        raise BadRequestError(
            f"A lobby must have between {MIN_ROUNDS_IN_LOBBY} and {MAX_ROUNDS_IN_LOBBY} rounds",
        )
    if any(
        not (MIN_CATEGORIES_PER_ROUND <= size <= MAX_CATEGORIES_PER_ROUND) for size in round_sizes
    ):
        raise BadRequestError(
            f"Each round must have between {MIN_CATEGORIES_PER_ROUND} and "
            f"{MAX_CATEGORIES_PER_ROUND} prompt categories",
        )


async def validate_rounds(uow: UnitOfWork, rounds: list[list[int]]) -> list[list[int]]:
    _validate_round_sizes([len(round_ids) for round_ids in rounds])
    all_ids = [category_id for round_ids in rounds for category_id in round_ids]
    if len(set(all_ids)) != len(all_ids):
        raise BadRequestError("A prompt category can be used only once per lobby")
    existing = await uow.lobby_repo.select_existing_category_ids(all_ids)
    missing = sorted(set(all_ids) - existing)
    if missing:
        raise BadRequestError(f"Prompt categories {missing} do not exist")
    return rounds


def validate_lifecycle_transition(
    current_state: LobbyStateEnum,
    requested_state: LobbyStateEnum,
) -> None:
    if current_state != LobbyStateEnum.CREATED or requested_state != LobbyStateEnum.WAITING_START:
        raise BadRequestError("REST may only transition a lobby from CREATED to WAITING_START")


async def validate_lobby_categories_for_start(uow: UnitOfWork, lobby_id: int) -> None:
    lobby = await uow.lobby_repo.select_lobby_with_prompts(lobby_id=lobby_id)
    if lobby is None:
        raise NotFoundError(f"Lobby {lobby_id} not found")
    category_rounds = await uow.lobby_repo.select_category_rounds(lobby_id)
    round_sizes = Counter(category_rounds.get(c.id, 1) for c in lobby.prompt_categories)
    total_rounds = max(round_sizes, default=0)
    if set(round_sizes) != set(range(1, total_rounds + 1)):
        raise BadRequestError("Lobby rounds must be numbered consecutively from 1")
    _validate_round_sizes([round_sizes[number] for number in sorted(round_sizes)])
    expected_orders = set(range(1, NUM_PROMPTS_IN_CATEGORY + 1))
    incomplete_categories = [
        category.id
        for category in lobby.prompt_categories
        if len(category.prompts) != NUM_PROMPTS_IN_CATEGORY
        or any(prompt.order is None for prompt in category.prompts)
        or {prompt.order for prompt in category.prompts} != expected_orders
    ]
    if incomplete_categories:
        raise BadRequestError(
            "Every lobby category must contain exactly five uniquely ordered "
            f"prompts; invalid categories: {incomplete_categories}",
        )


async def get_player_count(
    uow: UnitOfWork,
    lobby_id: int,
    lobby_state: LobbyStateEnum,
) -> int:
    if lobby_state == LobbyStateEnum.CREATED:
        return 0
    return await uow.lobby_repo.select_eligible_player_count(lobby_id)


def build_lobby_rounds(
    categories: list[PromptCategoryInDBSchema],
    category_rounds: dict[int, int],
    round_results: list[LobbyRoundResultInDBSchema] | None,
) -> list[LobbyRoundSchema]:
    """Group a lobby's categories (and, once completed, results) by round."""
    round_numbers = sorted({category_rounds.get(category.id, 1) for category in categories})
    return [
        LobbyRoundSchema(
            round_number=number,
            categories=sorted(
                (c for c in categories if category_rounds.get(c.id, 1) == number),
                key=lambda category: category.id,
            ),
            results=(
                None
                if round_results is None
                else [
                    LobbyRoundResultSchema(
                        user_id=result.user_id,
                        username=result.username_snapshot,
                        score=result.score,
                        score_delta=result.score_delta,
                        is_banned=result.is_banned,
                    )
                    for result in round_results
                    if result.round_number == number
                ]
            ),
        )
        for number in round_numbers
    ]


def rank_final_scores(
    participants: list[LobbyParticipantInDBSchema],
) -> list[LobbyFinalRankingSchema]:
    rankings: list[LobbyFinalRankingSchema] = []
    previous_score: int | None = None
    rank = 0
    for index, participant in enumerate(participants, start=1):
        assert participant.final_score is not None
        if participant.final_score != previous_score:
            rank = index
            previous_score = participant.final_score
        rankings.append(
            LobbyFinalRankingSchema(
                user_id=participant.user_id,
                username=participant.username_snapshot,
                final_score=participant.final_score,
                is_banned=participant.is_banned,
                rank=rank,
            ),
        )
    return rankings
