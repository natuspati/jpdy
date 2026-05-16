from schemas.lobby.game_state import GameLobbyState
from schemas.socket.events import SocketErrorPayload
from sockets.app import sio
from sockets.namespace import lobby_namespace

STATE_CHANGED_EVENT = "state_changed"
ERROR_EVENT = "error"


async def broadcast_state(lobby_id: int, state: GameLobbyState) -> None:
    """Emit the full game state to every socket on this lobby's namespace."""
    await sio.emit(
        STATE_CHANGED_EVENT,
        state.model_dump(mode="json"),
        namespace=lobby_namespace(lobby_id),
    )


async def emit_error(
    namespace: str,
    sid: str,
    code: str,
    detail: str,
) -> None:
    """Send a structured error payload to just the calling client."""
    payload = SocketErrorPayload(code=code, detail=detail)
    await sio.emit(
        ERROR_EVENT,
        payload.model_dump(mode="json"),
        to=sid,
        namespace=namespace,
    )
