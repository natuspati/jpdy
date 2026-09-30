from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

from configs import settings
from factories import UserCreateSchemaFactory
from fixtures.auth_fixtures import AuthedUser


async def test_register_returns_public_user_and_omits_hashed_password(
    http_client: AsyncClient,
):
    payload = UserCreateSchemaFactory.build().model_dump()

    response = await http_client.post("/api/v1/user/register", json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == payload["username"]
    assert isinstance(body["id"], int)
    assert "hashed_password" not in body
    assert "password" not in body


async def test_register_with_duplicate_username_returns_409(http_client: AsyncClient):
    payload = UserCreateSchemaFactory.build().model_dump()

    first = await http_client.post("/api/v1/user/register", json=payload)
    assert first.status_code == 201

    second = await http_client.post("/api/v1/user/register", json=payload)
    assert second.status_code == 409


async def test_register_requires_matching_invite_code_when_configured(
    http_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "registration_code", "friends-only")
    payload = UserCreateSchemaFactory.build(invite_code=None).model_dump()

    missing = await http_client.post("/api/v1/user/register", json=payload)
    wrong = await http_client.post(
        "/api/v1/user/register",
        json={**payload, "invite_code": "guess"},
    )
    right = await http_client.post(
        "/api/v1/user/register",
        json={**payload, "invite_code": "friends-only"},
    )

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert right.status_code == 201, right.text


async def test_register_with_too_short_password_returns_422(http_client: AsyncClient):
    response = await http_client.post(
        "/api/v1/user/register",
        json={"username": "shorty", "password": "123"},
    )
    assert response.status_code == 422


async def test_register_with_too_short_username_returns_422(http_client: AsyncClient):
    response = await http_client.post(
        "/api/v1/user/register",
        json={"username": "ab", "password": "validpw1"},
    )
    assert response.status_code == 422


async def test_sign_in_with_valid_credentials_returns_bearer_token(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    response = await http_client.post(
        "/api/v1/user/sign-in",
        data={"username": authed_user["username"], "password": authed_user["password"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"].count(".") == 2


async def test_sign_in_with_wrong_password_returns_401(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    response = await http_client.post(
        "/api/v1/user/sign-in",
        data={"username": authed_user["username"], "password": "wrongpass1"},
    )
    assert response.status_code == 401


async def test_sign_in_with_unknown_user_returns_401(http_client: AsyncClient):
    response = await http_client.post(
        "/api/v1/user/sign-in",
        data={"username": "nobody", "password": "whatever1"},
    )
    assert response.status_code == 401


async def test_sign_in_missing_form_fields_returns_422(http_client: AsyncClient):
    response = await http_client.post("/api/v1/user/sign-in", data={})
    assert response.status_code == 422


async def test_me_without_token_returns_401(http_client: AsyncClient):
    response = await http_client.get("/api/v1/user/me")
    assert response.status_code == 401


async def test_me_with_invalid_token_returns_401(http_client: AsyncClient):
    response = await http_client.get(
        "/api/v1/user/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


async def test_me_returns_nested_user_without_hashed_password(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    response = await http_client.get("/api/v1/user/me", headers=authed_user["headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == authed_user["user_id"]
    assert body["username"] == authed_user["username"]
    assert body["prompt_categories"] == []
    assert body["lobbies"] == []
    assert "hashed_password" not in body


async def test_me_reflects_categories_after_creation(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    register_user: Callable[[str, str], Awaitable[AuthedUser]],
):
    other = await register_user("third_user", "thirdpw1")

    own = await http_client.post(
        "/api/v1/category",
        json={"name": "Movies"},
        headers=authed_user["headers"],
    )
    assert own.status_code == 201

    # other user's category shouldn't show up under authed_user's /me
    await http_client.post(
        "/api/v1/category",
        json={"name": "Music"},
        headers=other["headers"],
    )

    me = await http_client.get("/api/v1/user/me", headers=authed_user["headers"])
    assert me.status_code == 200
    categories = me.json()["prompt_categories"]
    assert [c["name"] for c in categories] == ["Movies"]
