import logging
from typing import Any
from uuid import uuid4

from socketio.exceptions import ConnectionRefusedError as SocketConnectionRefusedError

from errors.base import BaseError
from schemas.user.base import UserPublicSchema
from services.game import GameService
from sockets.app import sio
from sockets.auth import authenticate_socket
from sockets.broadcast import broadcast_state
from sockets.namespace import parse_lobby_namespace
from sockets.session import (
    get_socket_session,
    lobby_host_room,
    lobby_player_room,
    save_socket_session,
)
from sockets.timer_hooks import arm_timer_if_needed, cancel_timer
from sockets.uow import build_uow

_logger = logging.getLogger(__name__)


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
            service = GameService(uow)
            previous_sid = await uow.game_state_repo.get_connection_sid(lobby_id, user.id)
            state = await service.connect_user(
                lobby_id=lobby_id,
                user=UserPublicSchema(id=user.id, username=user.username),
                command_id=f"connect:{sid}:{uuid4().hex}",
            )
            await uow.game_state_repo.set_connection_sid(lobby_id, user.id, sid)
    except BaseError as e:
        raise SocketConnectionRefusedError(e.detail) from e
    except Exception as e:
        _logger.exception(f"Failed to connect user {user.id} to lobby {lobby_id}")
        raise SocketConnectionRefusedError("Unable to connect to this lobby") from e

    await save_socket_session(
        sid=sid,
        namespace=namespace,
        user_id=user.id,
        username=user.username,
        lobby_id=lobby_id,
    )
    room = (
        lobby_host_room(lobby_id) if user.id == state.host.user_id else lobby_player_room(lobby_id)
    )
    await sio.enter_room(sid, room, namespace=namespace)
    if previous_sid is not None:
        await sio.disconnect(previous_sid, namespace=namespace)
    await broadcast_state(lobby_id, state)
    arm_timer_if_needed(lobby_id, state)
    _logger.info(f"User {user.id} connected to lobby {lobby_id}")


async def on_disconnect(namespace: str, sid: str, reason: Any = None) -> None:
    lobby_id = parse_lobby_namespace(namespace)
    if lobby_id is None:
        return

    session = await get_socket_session(sid, namespace)
    if session is None:
        return
    user_id = session["user_id"]

    async with build_uow() as uow:
        owns_connection = await uow.game_state_repo.clear_connection_sid(
            lobby_id,
            user_id,
            sid,
        )
    if not owns_connection:
        return

    async with build_uow() as uow:
        state = await GameService(uow).disconnect_user(
            lobby_id=lobby_id,
            user_id=user_id,
            command_id=f"disconnect:{sid}:{uuid4().hex}",
        )

    if state is None:
        cancel_timer(lobby_id)
        return

    await broadcast_state(lobby_id, state)
    arm_timer_if_needed(lobby_id, state)
    _logger.info(f"User {user_id} disconnected from lobby {lobby_id} (reason: {reason})")
