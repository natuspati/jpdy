from database import UnitOfWork
from enums.game import GamePhaseEnum
from enums.lobby import LobbyStateEnum
from schemas.lobby.game_state import GameLobbyState
from schemas.user.base import UserPublicSchema
from utils.game_state import find_game_player


class GameProjectionService:
    """Idempotent SQL projections for Redis-accepted game commands."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def project_connected_player(self, state: GameLobbyState, user: UserPublicSchema) -> None:
        async with self._uow as uow:
            await uow.lobby_repo.ensure_participant(lobby_id=state.lobby_id, user=user)

    async def project_game_started(self, state: GameLobbyState) -> None:
        async with self._uow as uow:
            await uow.lobby_repo.update_lobby_state(state.lobby_id, LobbyStateEnum.IN_PROGRESS)

    async def project_participant(self, state: GameLobbyState, user_id: int) -> None:
        player = find_game_player(state, user_id)
        if player is None:
            return
        async with self._uow as uow:
            await uow.lobby_repo.ensure_participant(
                lobby_id=state.lobby_id,
                user=UserPublicSchema(id=player.user_id, username=player.username),
            )
            await uow.lobby_repo.update_participant_ban(
                lobby_id=state.lobby_id,
                user_id=player.user_id,
                is_banned=player.is_banned,
            )

    async def project_completion(self, state: GameLobbyState) -> None:
        if state.phase != GamePhaseEnum.FINISHED:
            return
        async with self._uow as uow:
            await uow.lobby_repo.snapshot_final_results(
                lobby_id=state.lobby_id,
                players=[
                    (player.user_id, player.username, player.score, player.is_banned)
                    for player in state.players
                ],
            )
            banned_ids = {player.user_id for player in state.players if player.is_banned}
            await uow.lobby_repo.replace_round_results(
                lobby_id=state.lobby_id,
                results=[
                    (
                        result.round_number,
                        score.user_id,
                        score.username,
                        score.score,
                        score.score_delta,
                        score.user_id in banned_ids,
                    )
                    for result in state.round_results
                    for score in result.scores
                ],
            )
            await uow.lobby_repo.update_lobby_state(
                lobby_id=state.lobby_id,
                state=LobbyStateEnum.COMPLETED,
            )
