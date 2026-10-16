import random

from configs.constants import BETTING_PROMPT_DEFAULT_PERCENT
from database import UnitOfWork
from errors.request import BadRequestError, NotFoundError
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePromptState,
)
from schemas.lobby.nested import LobbyWithCategoryPromptsInDBSchema
from utils.game_state import round_score_value
from utils.media import build_media_reference


def default_betting_prompt_count(prompt_count: int) -> int:
    return prompt_count * BETTING_PROMPT_DEFAULT_PERCENT // 100


class GameStateMaterializer:
    """Create a live Redis state from an immutable SQL lobby snapshot."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def materialize(self, lobby_id: int) -> GameLobbyState:
        lobby = await self._uow.lobby_repo.select_lobby_with_prompts(lobby_id=lobby_id)
        if lobby is None:
            raise NotFoundError(f"Lobby {lobby_id} not found")
        category_rounds = await self._uow.lobby_repo.select_category_rounds(lobby_id)
        return await self._uow.game_state_repo.initialize_state(
            self.build_game_lobby_state(lobby, category_rounds, lobby.betting_prompt_count),
        )

    @staticmethod
    def build_game_lobby_state(
        lobby: LobbyWithCategoryPromptsInDBSchema,
        category_rounds: dict[int, int],
        betting_prompt_count: int | None,
        rng: random.Random | None = None,
    ) -> GameLobbyState:
        """Build an immutable SQL lobby snapshot into initial Redis game state."""
        if lobby.owner is None:
            raise BadRequestError("Lobby has no owner; cannot start a game")

        categories = sorted(
            lobby.prompt_categories,
            key=lambda category: (category_rounds.get(category.id, 1), category.id),
        )
        state = GameLobbyState(
            lobby_id=lobby.id,
            host=GameHostState(user_id=lobby.owner.id, username=lobby.owner.username),
            total_rounds=max((category_rounds.get(c.id, 1) for c in categories), default=1),
            categories=[
                GameCategoryState(
                    category_id=category.id,
                    name=category.name,
                    round_number=category_rounds.get(category.id, 1),
                    prompts=[
                        GamePromptState(
                            prompt_id=prompt.id,
                            question=prompt.question,
                            answer=prompt.answer,
                            question_type=prompt.question_type,
                            answer_type=prompt.answer_type,
                            question_media=(
                                build_media_reference(prompt.question_media_asset)
                                if prompt.question_media_asset is not None
                                else None
                            ),
                            answer_media=(
                                build_media_reference(prompt.answer_media_asset)
                                if prompt.answer_media_asset is not None
                                else None
                            ),
                            order=prompt.order or 0,
                            score_value=round_score_value(
                                prompt.order or 0,
                                category_rounds.get(category.id, 1),
                            ),
                        )
                        for prompt in category.prompts
                    ],
                )
                for category in categories
            ],
        )
        sampler = rng or random.Random()
        for round_number in range(1, state.total_rounds + 1):
            prompts = [
                prompt
                for category in state.categories
                if category.round_number == round_number
                for prompt in category.prompts
            ]
            count = (
                betting_prompt_count
                if betting_prompt_count is not None
                else default_betting_prompt_count(len(prompts))
            )
            for prompt in sampler.sample(prompts, min(count, len(prompts))):
                prompt.is_betting = True
        return state
