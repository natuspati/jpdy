from httpx import AsyncClient

from configs.constants import MAX_CATEGORIES_IN_LOBBY
from enums.lobby import LobbyStateEnum
from factories import PromptCategoryCreateSchemaFactory
from fixtures.auth_fixtures import AuthedUser


async def _create_category(client: AsyncClient, user: AuthedUser, name: str = "Cat") -> int:
    payload = PromptCategoryCreateSchemaFactory.build(name=name).model_dump()
    response = await client.post(
        "/api/v1/category",
        json=payload,
        headers=user["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_lobby(client: AsyncClient, user: AuthedUser) -> int:
    response = await client.post("/api/v1/lobby", headers=user["headers"])
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_create_lobby_requires_auth(http_client: AsyncClient):
    response = await http_client.post("/api/v1/lobby")
    assert response.status_code == 401


async def test_create_lobby_populates_owner_and_initial_state(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    response = await http_client.post("/api/v1/lobby", headers=authed_user["headers"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["owner_id"] == authed_user["user_id"]
    assert body["state"] == LobbyStateEnum.CREATED.value
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert "updated_at" in body


async def test_search_lobbies_returns_paginated_envelope(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    await _create_lobby(http_client, authed_user)
    await _create_lobby(http_client, authed_user)

    response = await http_client.get("/api/v1/lobby", headers=authed_user["headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert {"contents", "total", "page", "size"} <= body.keys()
    assert body["total"] == 2
    assert all("prompt_categories" in row for row in body["contents"])


async def test_search_lobbies_filters_by_owner_username_case_insensitive_partial(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    await _create_lobby(http_client, authed_user)
    await _create_lobby(http_client, another_authed_user)

    # authed_user is "owner_user" — partial, uppercase substring should still match
    response = await http_client.get(
        "/api/v1/lobby",
        params={"owner_username": "OWNER"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["contents"][0]["owner_id"] == authed_user["user_id"]


async def test_search_lobbies_owner_username_no_match_returns_empty(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    await _create_lobby(http_client, authed_user)

    response = await http_client.get(
        "/api/v1/lobby",
        params={"owner_username": "nobody"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0


async def test_search_lobbies_filters_by_state(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    await _create_lobby(http_client, authed_user)

    response = await http_client.get(
        "/api/v1/lobby",
        params={"states": [LobbyStateEnum.COMPLETED.value]},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0


async def test_get_lobby_returns_categories_initially_empty(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    response = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == lobby_id
    assert body["prompt_categories"] == []


async def test_get_unknown_lobby_returns_404(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    response = await http_client.get("/api/v1/lobby/99999", headers=authed_user["headers"])
    assert response.status_code == 404


async def test_update_lobby_attaches_categories(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    c1 = await _create_category(http_client, authed_user, "C1")
    c2 = await _create_category(http_client, authed_user, "C2")

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c1, c2]},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    returned_ids = {c["id"] for c in body["prompt_categories"]}
    assert returned_ids == {c1, c2}


async def test_update_lobby_replaces_existing_categories(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    c1 = await _create_category(http_client, authed_user, "C1")
    c2 = await _create_category(http_client, authed_user, "C2")
    c3 = await _create_category(http_client, authed_user, "C3")

    first = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c1, c2]},
        headers=authed_user["headers"],
    )
    assert first.status_code == 200

    second = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c3]},
        headers=authed_user["headers"],
    )
    assert second.status_code == 200, second.text
    returned_ids = {c["id"] for c in second.json()["prompt_categories"]}
    assert returned_ids == {c3}


async def test_update_lobby_state_only(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == LobbyStateEnum.WAITING_START.value


async def test_update_lobby_empty_body_rejected_by_one_field_set_mixin(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={},
        headers=authed_user["headers"],
    )
    assert response.status_code == 422


async def test_update_lobby_rejects_categories_when_not_in_created(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    c1 = await _create_category(http_client, authed_user, "C1")

    advance = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.IN_PROGRESS.value},
        headers=authed_user["headers"],
    )
    assert advance.status_code == 200

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c1]},
        headers=authed_user["headers"],
    )
    assert response.status_code == 400


async def test_update_lobby_rejects_unknown_category_ids(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    c1 = await _create_category(http_client, authed_user, "C1")

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c1, 99999]},
        headers=authed_user["headers"],
    )
    assert response.status_code == 400


async def test_update_lobby_rejects_too_many_categories(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    ids = [
        await _create_category(http_client, authed_user, f"C{i}")
        for i in range(MAX_CATEGORIES_IN_LOBBY + 1)
    ]

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": ids},
        headers=authed_user["headers"],
    )
    assert response.status_code == 400


async def test_update_lobby_rejects_empty_category_list(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": []},
        headers=authed_user["headers"],
    )
    assert response.status_code == 400


async def test_update_lobby_by_non_owner_returns_403(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=another_authed_user["headers"],
    )
    assert response.status_code == 403


async def test_update_lobby_deduplicates_category_ids(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    c1 = await _create_category(http_client, authed_user, "C1")

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c1, c1, c1]},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    returned = response.json()["prompt_categories"]
    assert [c["id"] for c in returned] == [c1]


async def test_delete_lobby_in_created_returns_204(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    delete = await http_client.delete(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    assert delete.status_code == 204

    after = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    assert after.status_code == 404


async def test_delete_lobby_rejected_when_not_in_created(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    advance = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.IN_PROGRESS.value},
        headers=authed_user["headers"],
    )
    assert advance.status_code == 200

    response = await http_client.delete(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    assert response.status_code == 400


async def test_delete_lobby_by_non_owner_returns_403(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    response = await http_client.delete(
        f"/api/v1/lobby/{lobby_id}",
        headers=another_authed_user["headers"],
    )
    assert response.status_code == 403


async def test_lobby_routes_require_auth(http_client: AsyncClient):
    response = await http_client.get("/api/v1/lobby")
    assert response.status_code == 401
