import logging
import re
from typing import Any

from socketio.exceptions import ConnectionRefusedError as SocketConnectionRefusedError

from sockets.app import sio

_logger = logging.getLogger(__name__)

_LOBBY_NAMESPACE_PATTERN = re.compile(r"^/lobbies/(?P<lobby_id>\d+)$")


def _parse_lobby_id(namespace: str) -> int | None:
    match = _LOBBY_NAMESPACE_PATTERN.match(namespace)
    if match is None:
        return None
    return int(match.group("lobby_id"))


@sio.on("connect", namespace="*")
async def on_connect(
    namespace: str,
    sid: str,
    environ: dict[str, Any],
    auth: Any = None,
) -> None:
    lobby_id = _parse_lobby_id(namespace)
    if lobby_id is None:
        raise SocketConnectionRefusedError(f"Invalid lobby namespace: {namespace}")

    _logger.info("User %s connected to lobby %s", sid, lobby_id)
    await sio.emit(
        "user_joined",
        {
            "sid": sid,
            "lobby_id": lobby_id,
            "message": f"Hello, user {sid}!",
        },
        namespace=namespace,
    )


@sio.on("disconnect", namespace="*")
async def on_disconnect(namespace: str, sid: str, reason: Any = None) -> None:
    lobby_id = _parse_lobby_id(namespace)
    if lobby_id is None:
        return

    _logger.info("User %s disconnected from lobby %s (reason: %s)", sid, lobby_id, reason)
    await sio.emit(
        "user_disconnected",
        {
            "sid": sid,
            "lobby_id": lobby_id,
            "message": f"User {sid} has been disconnected",
        },
        namespace=namespace,
    )
