import logging
from typing import Any

from socketio.exceptions import ConnectionRefusedError as SocketConnectionRefusedError

from errors.base import BaseError
from schemas.user.base import UserPublicSchema
from services.game import GameService
from sockets.app import sio
from sockets.auth import authenticate_socket
from sockets.broadcast import broadcast_state
from sockets.namespace import parse_lobby_namespace
from sockets.session import get_socket_session, save_socket_session
from sockets.timer_hooks import arm_timer_if_needed, cancel_timer
from sockets.uow import build_uow

_logger = logging.getLogger(__name__)


@sio.on("connect", namespace="*")
async def on_connect(
    namespace: str,
    sid: str,
    environ: dict[str, Any],
    auth: Any = None,
) -> None:
    lobby_id = parse_lobby_namespace(namespace)
    if lobby_id is None:
        raise SocketConnectionRefusedError(f"Invalid namespace: {namespace}")

    async with build_uow() as auth_uow:
        user = await authenticate_socket(environ, auth_uow)

    try:
        async with build_uow() as uow:
            state = await GameService(uow).connect_user(
                lobby_id=lobby_id,
                user=UserPublicSchema(id=user.id, username=user.username),
            )
    except BaseError as e:
        raise SocketConnectionRefusedError(e.detail) from e

    await save_socket_session(
        sid=sid,
        namespace=namespace,
        user_id=user.id,
        username=user.username,
        lobby_id=lobby_id,
    )
    await broadcast_state(lobby_id, state)
    arm_timer_if_needed(lobby_id, state)
    _logger.info("User %s connected to lobby %s", user.id, lobby_id)


@sio.on("disconnect", namespace="*")
async def on_disconnect(namespace: str, sid: str, reason: Any = None) -> None:
    lobby_id = parse_lobby_namespace(namespace)
    if lobby_id is None:
        return

    session = await get_socket_session(sid, namespace)
    if session is None:
        return
    user_id = session["user_id"]

    async with build_uow() as uow:
        state = await GameService(uow).disconnect_user(
            lobby_id=lobby_id,
            user_id=user_id,
        )

    if state is None:
        cancel_timer(lobby_id)
        return

    await broadcast_state(lobby_id, state)
    arm_timer_if_needed(lobby_id, state)
    _logger.info(
        "User %s disconnected from lobby %s (reason: %s)",
        user_id,
        lobby_id,
        reason,
    )
