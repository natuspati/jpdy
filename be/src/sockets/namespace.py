import re

LOBBY_NAMESPACE_PATTERN = re.compile(r"^/lobbies/(?P<lobby_id>\d+)$")


def parse_lobby_namespace(namespace: str) -> int | None:
    """
    Extract the ``lobby_id`` from a ``/lobbies/{lobby_id}`` namespace string.
    Returns ``None`` if the namespace does not match the pattern.
    """
    match = LOBBY_NAMESPACE_PATTERN.match(namespace)
    if match is None:
        return None
    return int(match.group("lobby_id"))


def lobby_namespace(lobby_id: int) -> str:
    return f"/lobbies/{lobby_id}"
