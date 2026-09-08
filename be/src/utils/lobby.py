from typing import TYPE_CHECKING

from configs.constants import (
    MAX_CATEGORIES_IN_LOBBY,
    MIN_CATEGORIES_IN_LOBBY,
    NUM_PROMPTS_IN_CATEGORY,
)
from enums.lobby import LobbyStateEnum
from errors.request import BadRequestError, ForbiddenError, NotFoundError
from schemas.lobby.nested import LobbyFinalRankingSchema, LobbyWithCategoriesInDBSchema
from schemas.lobby.participant import LobbyParticipantInDBSchema
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


async def validate_category_ids(uow: UnitOfWork, category_ids: list[int]) -> list[int]:
    unique_ids = list(dict.fromkeys(category_ids))
    if not (MIN_CATEGORIES_IN_LOBBY <= len(unique_ids) <= MAX_CATEGORIES_IN_LOBBY):
        raise BadRequestError(
            f"A lobby must have between {MIN_CATEGORIES_IN_LOBBY} and "
            f"{MAX_CATEGORIES_IN_LOBBY} prompt categories",
        )
    existing = await uow.lobby_repo.select_existing_category_ids(unique_ids)
    missing = sorted(set(unique_ids) - existing)
    if missing:
        raise BadRequestError(f"Prompt categories {missing} do not exist")
    return unique_ids


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
    category_count = len(lobby.prompt_categories)
    if not (MIN_CATEGORIES_IN_LOBBY <= category_count <= MAX_CATEGORIES_IN_LOBBY):
        raise BadRequestError(
            f"A lobby must have between {MIN_CATEGORIES_IN_LOBBY} and "
            f"{MAX_CATEGORIES_IN_LOBBY} prompt categories",
        )
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
