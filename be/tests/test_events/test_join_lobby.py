import asyncio

import pytest
import socketio

_EVENT_WAIT = 0.25


async def _connect(client: socketio.AsyncClient, server_url: str, namespace: str) -> None:
    await client.connect(
        server_url,
        namespaces=[namespace],
        socketio_path="ws",
        transports=["websocket"],
    )


async def test_connect_to_lobby_emits_greeting_to_self(socket_server_url, make_socket_client):
    namespace = "/lobbies/1"
    client = make_socket_client()
    received: list[dict] = []

    @client.on("user_joined", namespace=namespace)
    def _on_joined(data: dict) -> None:
        received.append(data)

    await _connect(client, socket_server_url, namespace)
    await asyncio.sleep(_EVENT_WAIT)

    assert len(received) == 1
    payload = received[0]
    assert payload["lobby_id"] == 1
    assert payload["sid"] == client.get_sid(namespace)
    assert "Hello" in payload["message"]


async def test_existing_member_receives_user_joined_on_new_connect(
    socket_server_url,
    make_socket_client,
):
    namespace = "/lobbies/2"
    client_a = make_socket_client()
    client_b = make_socket_client()
    a_events: list[dict] = []

    @client_a.on("user_joined", namespace=namespace)
    def _on_a_joined(data: dict) -> None:
        a_events.append(data)

    await _connect(client_a, socket_server_url, namespace)
    await asyncio.sleep(_EVENT_WAIT)
    assert len(a_events) == 1

    await _connect(client_b, socket_server_url, namespace)
    await asyncio.sleep(_EVENT_WAIT)

    assert len(a_events) == 2
    second = a_events[1]
    assert second["sid"] == client_b.get_sid(namespace)
    assert second["lobby_id"] == 2


async def test_disconnect_broadcasts_user_disconnected(socket_server_url, make_socket_client):
    namespace = "/lobbies/3"
    client_a = make_socket_client()
    client_b = make_socket_client()
    a_disconnect_events: list[dict] = []

    @client_a.on("user_disconnected", namespace=namespace)
    def _on_a_disconnect(data: dict) -> None:
        a_disconnect_events.append(data)

    await _connect(client_a, socket_server_url, namespace)
    await _connect(client_b, socket_server_url, namespace)
    await asyncio.sleep(_EVENT_WAIT)

    b_sid = client_b.get_sid(namespace)
    await client_b.disconnect()
    await asyncio.sleep(_EVENT_WAIT)

    assert len(a_disconnect_events) == 1
    payload = a_disconnect_events[0]
    assert payload["sid"] == b_sid
    assert payload["lobby_id"] == 3
    assert b_sid in payload["message"]


async def test_invalid_lobby_id_rejected(socket_server_url, make_socket_client):
    client = make_socket_client()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await _connect(client, socket_server_url, "/lobbies/abc")


async def test_separate_lobbies_are_isolated(socket_server_url, make_socket_client):
    namespace_a = "/lobbies/4"
    namespace_b = "/lobbies/5"
    client_a = make_socket_client()
    client_b = make_socket_client()
    a_events: list[dict] = []

    @client_a.on("user_joined", namespace=namespace_a)
    def _on_a_joined(data: dict) -> None:
        a_events.append(data)

    await _connect(client_a, socket_server_url, namespace_a)
    await asyncio.sleep(_EVENT_WAIT)
    assert len(a_events) == 1

    await _connect(client_b, socket_server_url, namespace_b)
    await asyncio.sleep(_EVENT_WAIT)

    assert len(a_events) == 1
