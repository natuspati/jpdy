from sockets.app import sio
from sockets.broadcast import broadcast_lobby_deleted
from sockets.namespace import lobby_namespace


async def notify_lobby_deleted_and_disconnect(lobby_id: int) -> None:
    """Emit deletion event, then close every Socket.IO connection in lobby."""
    namespace = lobby_namespace(lobby_id)
    await broadcast_lobby_deleted(lobby_id)
    for sid, _ in list(sio.manager.get_participants(namespace, None)):
        await sio.disconnect(sid, namespace=namespace)
