from typing import TypedDict

from sockets.app import sio


class SocketSession(TypedDict):
    user_id: int
    username: str
    lobby_id: int


async def save_socket_session(
    sid: str,
    namespace: str,
    user_id: int,
    username: str,
    lobby_id: int,
) -> None:
    session: SocketSession = {
        "user_id": user_id,
        "username": username,
        "lobby_id": lobby_id,
    }
    await sio.save_session(sid, session, namespace=namespace)
    await sio.enter_room(sid, lobby_user_room(lobby_id, user_id), namespace=namespace)


async def get_socket_session(sid: str, namespace: str) -> SocketSession | None:
    """
    Read the per-(sid, namespace) session set on connect. Returns ``None`` if
    the socket is no longer connected to that namespace (e.g. after a forced
    disconnect during a ban).
    """
    try:
        session = await sio.get_session(sid, namespace=namespace)
    except KeyError:
        return None
    if not session:
        return None
    return session


def lobby_player_room(lobby_id: int) -> str:
    return f"lobby:{lobby_id}:players"


def lobby_host_room(lobby_id: int) -> str:
    return f"lobby:{lobby_id}:host"


def lobby_user_room(lobby_id: int, user_id: int) -> str:
    return f"lobby:{lobby_id}:user:{user_id}"
