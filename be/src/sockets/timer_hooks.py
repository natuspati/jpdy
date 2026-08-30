import logging

from enums.game import GamePhaseEnum
from schemas.lobby.game_state import GameLobbyState
from schemas.socket.events import GameSoundCueName
from services import game_timers
from services.game import GameService
from sockets.broadcast import broadcast_sound_cue, broadcast_state
from sockets.uow import build_uow

_logger = logging.getLogger(__name__)

_TIMED_PHASES = {
    GamePhaseEnum.PLAYER_ANSWERING,
    GamePhaseEnum.BUZZ_OPEN,
    GamePhaseEnum.ANSWER_REVEAL,
}


def arm_timer_if_needed(lobby_id: int, state: GameLobbyState) -> None:
    """
    Inspect the new state; if its phase implies a server-side countdown, arm
    a timer that re-enters ``GameService.expire_timer`` and broadcasts the
    resulting state. Otherwise cancel any timer that was previously armed.
    """
    if state.phase not in _TIMED_PHASES or state.timer_deadline is None:
        game_timers.cancel(lobby_id)
        return
    game_timers.arm(lobby_id, state.timer_deadline, _on_timer_expire)


def cancel_timer(lobby_id: int) -> None:
    game_timers.cancel(lobby_id)


async def _on_timer_expire(lobby_id: int) -> None:
    try:
        async with build_uow() as uow:
            before = await uow.game_state_repo.get_state(lobby_id)
            state = await GameService(uow).expire_timer(lobby_id=lobby_id)
    except Exception:
        _logger.exception("Failed to expire timer for lobby %s", lobby_id)
        return
    if state is None:
        return
    await broadcast_state(lobby_id, state)
    arm_timer_if_needed(lobby_id, state)
    for cue in _sound_cues_for_expired_timer(before, state):
        try:
            async with build_uow() as uow:
                payload = await GameService(uow).issue_sound_cue(lobby_id, cue)
            await broadcast_sound_cue(lobby_id, payload)
        except Exception:
            _logger.exception("Failed to emit %s sound cue for lobby %s", cue, lobby_id)


def _sound_cues_for_expired_timer(
    before: GameLobbyState | None,
    after: GameLobbyState,
) -> list[GameSoundCueName]:
    if before is None:
        return []
    if before.phase in {GamePhaseEnum.PLAYER_ANSWERING, GamePhaseEnum.BUZZ_OPEN}:
        cues = [GameSoundCueName.ANSWER_EXPIRED]
        if after.phase == GamePhaseEnum.ANSWER_REVEAL:
            cues.append(GameSoundCueName.ANSWER_REVEALED)
        return cues
    if before.phase == GamePhaseEnum.ANSWER_REVEAL:
        if after.phase == GamePhaseEnum.FINISHED:
            return [GameSoundCueName.GAME_COMPLETED]
        return []
    return []
