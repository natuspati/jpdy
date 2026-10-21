import logging

from sockets.app import sio
from sockets.broadcast import broadcast_lobby_deleted
from sockets.namespace import LOBBY_LIST_NAMESPACE, lobby_namespace

_logger = logging.getLogger(__name__)

LOBBIES_CHANGED_EVENT = "lobbies_changed"


async def notify_lobbies_changed() -> None:
    """Tell lobby-list clients to refetch; call after the SQL commit. Never fails the caller."""
    try:
        await sio.emit(LOBBIES_CHANGED_EVENT, namespace=LOBBY_LIST_NAMESPACE)
    except Exception:
        _logger.exception("Failed to emit lobbies_changed")


async def notify_lobby_deleted_and_disconnect(lobby_id: int) -> None:
    """Emit deletion event, then close every Socket.IO connection in lobby."""
    namespace = lobby_namespace(lobby_id)
    await broadcast_lobby_deleted(lobby_id)
    for sid, _ in list(sio.manager.get_participants(namespace, None)):
        await sio.disconnect(sid, namespace=namespace)
