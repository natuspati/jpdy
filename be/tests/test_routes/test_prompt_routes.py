from httpx import AsyncClient

from configs.constants import NUM_PROMPTS_IN_CATEGORY
from factories import PromptCategoryCreateSchemaFactory, PromptCreateSchemaFactory
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


async def _create_prompt(
    client: AsyncClient,
    user: AuthedUser,
    category_id: int,
    order: int,
) -> int:
    payload = PromptCreateSchemaFactory.build(order=order).model_dump()
    response = await client.post(
        f"/api/v1/category/{category_id}/prompts",
        json=payload,
        headers=user["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_create_category_requires_auth(http_client: AsyncClient):
    response = await http_client.post("/api/v1/category", json={"name": "x"})
    assert response.status_code == 401


async def test_create_category_persists_with_current_user_as_owner(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    response = await http_client.post(
        "/api/v1/category",
        json={"name": "Films"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Films"
    assert body["owner_id"] == authed_user["user_id"]


async def test_create_category_ignores_owner_id_from_payload(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    response = await http_client.post(
        "/api/v1/category",
        json={"name": "Spoofed", "owner_id": another_authed_user["user_id"]},
        headers=authed_user["headers"],
    )
    assert response.status_code == 201
    assert response.json()["owner_id"] == authed_user["user_id"]


async def test_search_categories_returns_paginated_envelope(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    await _create_category(http_client, authed_user, "C1")

    response = await http_client.get(
        "/api/v1/category",
        params={"is_complete": "false"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert {"contents", "total", "page", "size"} <= body.keys()
    assert body["total"] == 1
    assert body["contents"][0]["name"] == "C1"


async def test_get_category_returns_prompts_ordered_ascending(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    # Insert out of order to verify ordering happens at the relationship layer.
    await _create_prompt(http_client, authed_user, category_id, order=3)
    await _create_prompt(http_client, authed_user, category_id, order=1)
    await _create_prompt(http_client, authed_user, category_id, order=2)

    response = await http_client.get(
        f"/api/v1/category/{category_id}",
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    orders = [p["order"] for p in response.json()["prompts"]]
    assert orders == [1, 2, 3]


async def test_get_unknown_category_returns_404(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    response = await http_client.get(
        "/api/v1/category/99999",
        headers=authed_user["headers"],
    )
    assert response.status_code == 404


async def test_update_category_returns_joined_view_with_new_order(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user, "Initial")
    p1 = await _create_prompt(http_client, authed_user, category_id, order=1)
    p2 = await _create_prompt(http_client, authed_user, category_id, order=2)

    response = await http_client.patch(
        f"/api/v1/category/{category_id}",
        json={"name": "Renamed", "prompt_order": {str(p1): 2, str(p2): 1}},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Renamed"
    assert "prompts" in body
    order_by_id = {p["id"]: p["order"] for p in body["prompts"]}
    assert order_by_id[p1] == 2
    assert order_by_id[p2] == 1


async def test_update_category_by_non_owner_does_not_mutate_state(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user, "Movies")

    forbidden = await http_client.patch(
        f"/api/v1/category/{category_id}",
        json={"name": "Hacked"},
        headers=another_authed_user["headers"],
    )
    assert forbidden.status_code == 403

    # State must be unchanged.
    state = await http_client.get(
        f"/api/v1/category/{category_id}",
        headers=authed_user["headers"],
    )
    assert state.json()["name"] == "Movies"


async def test_delete_category_by_owner_returns_204(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)

    delete = await http_client.delete(
        f"/api/v1/category/{category_id}",
        headers=authed_user["headers"],
    )
    assert delete.status_code == 204

    after = await http_client.get(
        f"/api/v1/category/{category_id}",
        headers=authed_user["headers"],
    )
    assert after.status_code == 404


async def test_delete_category_by_non_owner_returns_403(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)

    response = await http_client.delete(
        f"/api/v1/category/{category_id}",
        headers=another_authed_user["headers"],
    )
    assert response.status_code == 403


async def test_create_prompt_rejects_missing_order(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    payload = PromptCreateSchemaFactory.build().model_dump()
    payload.pop("order")

    response = await http_client.post(
        f"/api/v1/category/{category_id}/prompts",
        json=payload,
        headers=authed_user["headers"],
    )
    assert response.status_code == 422


async def test_create_prompt_rejects_order_above_max(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    payload = PromptCreateSchemaFactory.build(order=1).model_dump()
    payload["order"] = NUM_PROMPTS_IN_CATEGORY + 1

    response = await http_client.post(
        f"/api/v1/category/{category_id}/prompts",
        json=payload,
        headers=authed_user["headers"],
    )
    assert response.status_code == 422


async def test_create_prompt_rejects_non_text_content_types(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    payload = PromptCreateSchemaFactory.build(order=1).model_dump()
    payload["question_type"] = "image"

    response = await http_client.post(
        f"/api/v1/category/{category_id}/prompts",
        json=payload,
        headers=authed_user["headers"],
    )

    assert response.status_code == 422


async def test_create_prompt_in_other_users_category_returns_403(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    payload = PromptCreateSchemaFactory.build(order=1).model_dump()

    response = await http_client.post(
        f"/api/v1/category/{category_id}/prompts",
        json=payload,
        headers=another_authed_user["headers"],
    )
    assert response.status_code == 403


async def test_create_prompt_with_duplicate_order_returns_409(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    await _create_prompt(http_client, authed_user, category_id, order=2)

    payload = PromptCreateSchemaFactory.build(order=2).model_dump()
    response = await http_client.post(
        f"/api/v1/category/{category_id}/prompts",
        json=payload,
        headers=authed_user["headers"],
    )
    assert response.status_code == 409


async def test_create_prompt_in_unknown_category_returns_404(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    payload = PromptCreateSchemaFactory.build(order=1).model_dump()
    response = await http_client.post(
        "/api/v1/category/99999/prompts",
        json=payload,
        headers=authed_user["headers"],
    )
    assert response.status_code == 404


async def test_update_prompt_modifies_only_supplied_fields(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    prompt_id = await _create_prompt(http_client, authed_user, category_id, order=1)

    response = await http_client.patch(
        f"/api/v1/category/{category_id}/prompts/{prompt_id}",
        json={"question": "What is updated?"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["question"] == "What is updated?"
    assert body["order"] == 1  # unchanged


async def test_update_prompt_rejects_media_type_without_asset(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    prompt_id = await _create_prompt(http_client, authed_user, category_id, order=1)

    response = await http_client.patch(
        f"/api/v1/category/{category_id}/prompts/{prompt_id}",
        json={"answer_type": "audio"},
        headers=authed_user["headers"],
    )

    assert response.status_code == 400


async def test_update_prompt_empty_body_rejected_by_one_field_set_mixin(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    prompt_id = await _create_prompt(http_client, authed_user, category_id, order=1)

    response = await http_client.patch(
        f"/api/v1/category/{category_id}/prompts/{prompt_id}",
        json={},
        headers=authed_user["headers"],
    )
    assert response.status_code == 422


async def test_update_prompt_in_unknown_category_returns_404(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    prompt_id = await _create_prompt(http_client, authed_user, category_id, order=1)

    response = await http_client.patch(
        f"/api/v1/category/99999/prompts/{prompt_id}",
        json={"question": "moved"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 404


async def test_delete_prompt_by_owner_removes_it_from_category(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    prompt_id = await _create_prompt(http_client, authed_user, category_id, order=1)

    delete = await http_client.delete(
        f"/api/v1/category/{category_id}/prompts/{prompt_id}",
        headers=authed_user["headers"],
    )
    assert delete.status_code == 204

    state = await http_client.get(
        f"/api/v1/category/{category_id}",
        headers=authed_user["headers"],
    )
    assert state.json()["prompts"] == []


async def test_delete_prompt_by_non_owner_returns_403(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
):
    category_id = await _create_category(http_client, authed_user)
    prompt_id = await _create_prompt(http_client, authed_user, category_id, order=1)

    response = await http_client.delete(
        f"/api/v1/category/{category_id}/prompts/{prompt_id}",
        headers=another_authed_user["headers"],
    )
    assert response.status_code == 403


async def test_prompt_routes_require_auth(http_client: AsyncClient):
    no_auth = await http_client.get("/api/v1/category")
    assert no_auth.status_code == 401
