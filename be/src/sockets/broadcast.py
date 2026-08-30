from enums.game import GamePhaseEnum
from schemas.lobby.game_state import GameLobbyState, HostAnswerKey
from schemas.socket.events import GameSoundCuePayload, SocketErrorPayload
from sockets.app import sio
from sockets.namespace import lobby_namespace
from sockets.session import connected_socket_sessions, find_sid_for_user

STATE_CHANGED_EVENT = "state_changed"
HOST_ANSWER_KEY_EVENT = "host_answer_key"
ERROR_EVENT = "error"
GAME_SOUND_CUE_EVENT = "game_sound_cue"
LOBBY_DELETED_EVENT = "lobby_deleted"


async def broadcast_state(lobby_id: int, state: GameLobbyState) -> None:
    """Emit a recipient-specific safe snapshot and host-private answer key."""
    namespace = lobby_namespace(lobby_id)
    player_payload = state.public_state().model_dump(mode="json")
    host_payload = state.public_state(include_banned_players=True).model_dump(mode="json")
    for sid, session in await connected_socket_sessions(namespace):
        payload = host_payload if session["user_id"] == state.host.user_id else player_payload
        await sio.emit(
            STATE_CHANGED_EVENT,
            payload,
            to=sid,
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


async def broadcast_sound_cue(
    lobby_id: int,
    payload: GameSoundCuePayload,
) -> None:
    await sio.emit(
        GAME_SOUND_CUE_EVENT,
        payload.model_dump(mode="json"),
        namespace=lobby_namespace(lobby_id),
    )


async def broadcast_lobby_deleted(lobby_id: int) -> None:
    await sio.emit(
        LOBBY_DELETED_EVENT,
        {"lobby_id": lobby_id},
        namespace=lobby_namespace(lobby_id),
    )
