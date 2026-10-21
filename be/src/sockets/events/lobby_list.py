from typing import Any

from sockets.auth import authenticate_socket
from sockets.uow import build_uow


async def on_lobby_list_connect(sid: str, environ: dict[str, Any], auth: Any = None) -> None:
    """Authenticate only; the namespace carries no data, just ``lobbies_changed`` pings."""
    async with build_uow() as uow:
        await authenticate_socket(environ, uow)
