from enums.game import GamePhaseEnum
from schemas.lobby.game_state import GameLobbyState, HostAnswerKey
from schemas.socket.events import SocketErrorPayload
from sockets.app import sio
from sockets.namespace import lobby_namespace
from sockets.session import find_sid_for_user

STATE_CHANGED_EVENT = "state_changed"
HOST_ANSWER_KEY_EVENT = "host_answer_key"
ERROR_EVENT = "error"


async def broadcast_state(lobby_id: int, state: GameLobbyState) -> None:
    """Emit a safe state snapshot and the active clue's host-private key."""
    namespace = lobby_namespace(lobby_id)
    await sio.emit(
        STATE_CHANGED_EVENT,
        state.public_state().model_dump(mode="json"),
        namespace=namespace,
    )
    await _emit_host_answer_key(namespace, state)


async def _emit_host_answer_key(namespace: str, state: GameLobbyState) -> None:
    if state.phase != GamePhaseEnum.PLAYER_ANSWERING or state.current_prompt_id is None:
        return

    prompt = next(
        (
            prompt
            for category in state.categories
            for prompt in category.prompts
            if prompt.prompt_id == state.current_prompt_id
        ),
        None,
    )
    if prompt is None:
        return

    host_sid = await find_sid_for_user(namespace, state.host.user_id)
    if host_sid is None:
        return

    payload = HostAnswerKey(
        lobby_id=state.lobby_id,
        prompt_id=prompt.prompt_id,
        expected_answer=prompt.answer,
    )
    await sio.emit(
        HOST_ANSWER_KEY_EVENT,
        payload.model_dump(mode="json"),
        to=host_sid,
        namespace=namespace,
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
