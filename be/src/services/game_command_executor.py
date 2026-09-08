from collections.abc import Callable
from uuid import uuid4

from database import UnitOfWork
from errors.request import BadRequestError, NotFoundError
from repos.game_state import GameStateConflictError, GameStateMissingError
from schemas.lobby.game_state import GameLobbyState
from utils.game_state import GameCommandOutcome


class GameCommandExecutor:
    """Run one pure game transition through Redis command serialization."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        lobby_id: int,
        command_id: str | None,
        command_name: str,
        transition: Callable[[GameLobbyState], GameCommandOutcome],
    ) -> GameLobbyState | None:
        try:
            async with self._uow as uow:
                return await uow.game_state_repo.execute(
                    lobby_id=lobby_id,
                    command_id=command_id or uuid4().hex,
                    command_name=command_name,
                    transition=transition,
                )
        except GameStateMissingError as error:
            raise NotFoundError(str(error)) from error
        except GameStateConflictError as error:
            raise BadRequestError("Game is busy; retry the command") from error
