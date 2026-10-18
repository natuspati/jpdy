from typing import TYPE_CHECKING

from configs.constants import (
    MAX_CATEGORIES_PER_ROUND,
    MAX_ROUNDS_IN_LOBBY,
    MIN_CATEGORIES_PER_ROUND,
    MIN_ROUNDS_IN_LOBBY,
)
from enums.lobby import LobbyStateEnum
from enums.prompt import PromptCategoryKindEnum
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
from utils.prompt import prompt_count_for_kind

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


async def validate_rounds(
    uow: UnitOfWork,
    rounds: list[list[int]],
    final_category_id: int | None = None,
) -> list[list[int]]:
    _validate_round_sizes([len(round_ids) for round_ids in rounds])
    all_ids = [category_id for round_ids in rounds for category_id in round_ids]
    if final_category_id is not None:
        all_ids.append(final_category_id)
    if len(set(all_ids)) != len(all_ids):
        raise BadRequestError("A prompt category can be used only once per lobby")
    kinds = await uow.lobby_repo.select_category_kinds(all_ids)
    missing = sorted(set(all_ids) - kinds.keys())
    if missing:
        raise BadRequestError(f"Prompt categories {missing} do not exist")
    if any(
        kinds[category_id] != PromptCategoryKindEnum.STANDARD
        for round_ids in rounds
        for category_id in round_ids
    ):
        raise BadRequestError("Normal rounds require standard categories")
    if final_category_id is not None and kinds[final_category_id] != PromptCategoryKindEnum.FINAL:
        raise BadRequestError("The Final slot requires a final category")
    return [*rounds, [final_category_id]] if final_category_id is not None else rounds


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
    rounds: dict[int, list[int]] = {}
    final_ids = []
    for category in lobby.prompt_categories:
        if category.kind == PromptCategoryKindEnum.FINAL:
            final_ids.append(category.id)
        else:
            rounds.setdefault(category_rounds.get(category.id, 1), []).append(category.id)
    if set(rounds) != set(range(1, len(rounds) + 1)):
        raise BadRequestError("Lobby rounds must be numbered consecutively from 1")
    if len(final_ids) > 1 or any(
        category_rounds.get(category_id, 1) != len(rounds) + 1 for category_id in final_ids
    ):
        raise BadRequestError("The Final category must be alone after all normal rounds")
    await validate_rounds(
        uow,
        [rounds[number] for number in sorted(rounds)],
        final_ids[0] if final_ids else None,
    )
    incomplete_categories = [
        category.id
        for category in lobby.prompt_categories
        if len(category.prompts) != prompt_count_for_kind(category.kind)
        or {prompt.order for prompt in category.prompts}
        != set(range(1, prompt_count_for_kind(category.kind) + 1))
    ]
    if incomplete_categories:
        raise BadRequestError(
            "Every lobby category must contain exactly five uniquely ordered prompts "
            "(one for Final); invalid categories: "
            f"{incomplete_categories}",
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
            kind=next(
                category.kind
                for category in categories
                if category_rounds.get(category.id, 1) == number
            ),
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
