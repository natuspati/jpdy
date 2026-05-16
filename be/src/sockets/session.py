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


async def find_sid_for_user(namespace: str, user_id: int) -> str | None:
    """
    Walk the namespace's participants and return the sid of the socket whose
    session belongs to ``user_id``, or ``None`` if no such socket is connected.
    """
    for sid, _ in list(sio.manager.get_participants(namespace, None)):
        session = await get_socket_session(sid, namespace)
        if session and session["user_id"] == user_id:
            return sid
    return None
