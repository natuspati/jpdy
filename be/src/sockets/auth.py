from typing import Any
from urllib.parse import parse_qs

from socketio.exceptions import ConnectionRefusedError as SocketConnectionRefusedError

from database import UnitOfWork
from errors.base import BaseError
from schemas.user.base import UserInDBSchema
from utils.auth import decode_access_token


def extract_token_from_environ(environ: dict[str, Any]) -> str | None:
    """
    Pull the ``token`` query parameter out of the socket connection environ.
    Returns ``None`` if no usable value is present.
    """
    query_string = environ.get("QUERY_STRING") or ""
    if not query_string:
        return None
    parsed = parse_qs(query_string)
    values = parsed.get("token")
    if not values:
        return None
    token = values[0]
    return token or None


async def authenticate_socket(
    environ: dict[str, Any],
    uow: UnitOfWork,
) -> UserInDBSchema:
    """
    Decode the bearer token from the socket's query string and resolve the
    authenticated user. Raises ``ConnectionRefusedError`` so Socket.IO rejects
    the connection cleanly on any auth failure.
    """
    token = extract_token_from_environ(environ)
    if not token:
        raise SocketConnectionRefusedError("Missing token")

    try:
        payload = decode_access_token(token)
    except BaseError as e:
        raise SocketConnectionRefusedError(e.detail) from e

    async with uow:
        user = await uow.user_repo.select_user(user_id=payload.sub)
    if user is None:
        raise SocketConnectionRefusedError("User no longer exists")
    return user
