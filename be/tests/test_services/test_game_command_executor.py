import pytest

from errors.request import BadRequestError, ForbiddenError, NotFoundError
from repos.game_state import GameStateConflictError, GameStateMissingError
from schemas.lobby.game_state import GameHostState, GameLobbyState
from services.game_command_executor import GameCommandExecutor
from utils.game_state import GameCommandOutcome


class _GameStateRepo:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.command_id: str | None = None

    async def execute(self, **kwargs):
        self.command_id = kwargs["command_id"]
        if self.error is not None:
            raise self.error
        state = GameLobbyState(lobby_id=1, host=GameHostState(user_id=1, username="host"))
        return kwargs["transition"](state).result


class _Uow:
    def __init__(self, repo: _GameStateRepo):
        self.game_state_repo = repo

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


async def test_executor_generates_missing_command_id() -> None:
    repo = _GameStateRepo()
    executor = GameCommandExecutor(_Uow(repo))

    result = await executor.execute(
        1,
        None,
        "test",
        lambda state: GameCommandOutcome(state, state, "accepted"),
    )

    assert result is not None
    assert repo.command_id is not None
    assert len(repo.command_id) == 32


async def test_executor_preserves_explicit_command_id_and_transition_error() -> None:
    repo = _GameStateRepo()
    executor = GameCommandExecutor(_Uow(repo))

    with pytest.raises(ForbiddenError, match="rejected"):
        await executor.execute(
            1,
            "explicit-command",
            "test",
            lambda _state: (_ for _ in ()).throw(ForbiddenError("rejected")),
        )

    assert repo.command_id == "explicit-command"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (GameStateMissingError(1), NotFoundError),
        (GameStateConflictError(1), BadRequestError),
    ],
)
async def test_executor_translates_repository_errors(
    error: Exception,
    expected: type[Exception],
) -> None:
    executor = GameCommandExecutor(_Uow(_GameStateRepo(error)))

    with pytest.raises(expected):
        await executor.execute(
            1,
            "command",
            "test",
            lambda state: GameCommandOutcome(state, state, "accepted"),
        )
