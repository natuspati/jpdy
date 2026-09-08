from database import UnitOfWork
from errors.request import BadRequestError, NotFoundError
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePromptState,
)
from schemas.lobby.nested import LobbyWithCategoryPromptsInDBSchema
from utils.media import build_media_reference


class GameStateMaterializer:
    """Create a live Redis state from an immutable SQL lobby snapshot."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def materialize(self, lobby_id: int) -> GameLobbyState:
        lobby = await self._uow.lobby_repo.select_lobby_with_prompts(lobby_id=lobby_id)
        if lobby is None:
            raise NotFoundError(f"Lobby {lobby_id} not found")
        return await self._uow.game_state_repo.initialize_state(self.build_game_lobby_state(lobby))

    @staticmethod
    def build_game_lobby_state(lobby: LobbyWithCategoryPromptsInDBSchema) -> GameLobbyState:
        """Build an immutable SQL lobby snapshot into initial Redis game state."""
        if lobby.owner is None:
            raise BadRequestError("Lobby has no owner; cannot start a game")

        return GameLobbyState(
            lobby_id=lobby.id,
            host=GameHostState(user_id=lobby.owner.id, username=lobby.owner.username),
            categories=[
                GameCategoryState(
                    category_id=category.id,
                    name=category.name,
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
                        )
                        for prompt in category.prompts
                    ],
                )
                for category in lobby.prompt_categories
            ],
        )
