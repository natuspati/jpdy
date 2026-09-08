import pytest
from httpx import AsyncClient
from sqlalchemy import insert, update

from configs.constants import MAX_CATEGORIES_IN_LOBBY, NUM_PROMPTS_IN_CATEGORY
from enums.lobby import LobbyStateEnum
from factories import PromptCategoryCreateSchemaFactory, PromptCreateSchemaFactory
from fixtures.auth_fixtures import AuthedUser
from models.lobby import Lobby, LobbyParticipant
from repos.game_state import GameStateRepo
from schemas.lobby.game_state import GameLobbyState, GamePlayerState
from utils.game_state import game_state_key


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


async def _prepare_lobby(
    client: AsyncClient,
    user: AuthedUser,
    *,
    state: LobbyStateEnum = LobbyStateEnum.WAITING_START,
) -> int:
    lobby_id = await _create_lobby(client, user)
    category_id = await _create_complete_category(client, user)
    attach = await client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [category_id]},
        headers=user["headers"],
    )
    assert attach.status_code == 200, attach.text
    prepare = await client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=user["headers"],
    )
    assert prepare.status_code == 200, prepare.text
    if state != LobbyStateEnum.WAITING_START:
        raise AssertionError("Only waiting lobbies can be prepared through REST")
    return lobby_id


async def _create_complete_category(
    client: AsyncClient,
    user: AuthedUser,
    name: str = "Complete category",
) -> int:
    category_id = await _create_category(client, user, name)
    for order in range(1, NUM_PROMPTS_IN_CATEGORY + 1):
        payload = PromptCreateSchemaFactory.build(
            question_type="text",
            answer_type="text",
            order=order,
        ).model_dump()
        response = await client.post(
            f"/api/v1/category/{category_id}/prompts",
            json=payload,
            headers=user["headers"],
        )
        assert response.status_code == 201, response.text
    return category_id


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
    assert body["owner"] == {
        "id": authed_user["user_id"],
        "username": authed_user["username"],
    }


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


async def test_update_lobby_prepares_complete_categories_and_snapshots_state(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    redis_client,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    category_id = await _create_complete_category(http_client, authed_user)
    attach = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [category_id]},
        headers=authed_user["headers"],
    )
    assert attach.status_code == 200, attach.text

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=authed_user["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == LobbyStateEnum.WAITING_START.value
    assert await redis_client.get(game_state_key(lobby_id)) is not None


async def test_prepared_lobby_keeps_prompt_snapshot_after_category_edit(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    redis_client,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    category_id = await _create_complete_category(http_client, authed_user)
    category = await http_client.get(
        f"/api/v1/category/{category_id}",
        headers=authed_user["headers"],
    )
    assert category.status_code == 200, category.text
    prompt_id = category.json()["prompts"][0]["id"]

    attach = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [category_id]},
        headers=authed_user["headers"],
    )
    assert attach.status_code == 200, attach.text
    prepare = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=authed_user["headers"],
    )
    assert prepare.status_code == 200, prepare.text

    raw_state = await redis_client.get(game_state_key(lobby_id))
    assert raw_state is not None
    original_question = (
        GameLobbyState.model_validate_json(raw_state).categories[0].prompts[0].question
    )

    update = await http_client.patch(
        f"/api/v1/category/{category_id}/prompts/{prompt_id}",
        json={"question": "Edited after game preparation"},
        headers=authed_user["headers"],
    )
    assert update.status_code == 200, update.text

    snapshotted = await redis_client.get(game_state_key(lobby_id))
    assert snapshotted is not None
    assert (
        GameLobbyState.model_validate_json(snapshotted).categories[0].prompts[0].question
        == original_question
    )


async def test_update_lobby_rejects_preparing_incomplete_categories(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    category_id = await _create_category(http_client, authed_user)
    attach = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [category_id]},
        headers=authed_user["headers"],
    )
    assert attach.status_code == 200, attach.text

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=authed_user["headers"],
    )

    assert response.status_code == 400
    assert "exactly five" in response.json()["detail"]


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
    c1 = await _create_complete_category(http_client, authed_user, "C1")
    c2 = await _create_complete_category(http_client, authed_user, "C2")

    attach = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c1]},
        headers=authed_user["headers"],
    )
    assert attach.status_code == 200, attach.text

    advance = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=authed_user["headers"],
    )
    assert advance.status_code == 200, advance.text

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [c2]},
        headers=authed_user["headers"],
    )
    assert response.status_code == 400


async def test_update_lobby_rejects_invalid_rest_lifecycle_transition(
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    lobby_id = await _create_lobby(http_client, authed_user)

    response = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.IN_PROGRESS.value},
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


async def test_delete_lobby_removes_participants_before_sqlite_reuses_its_id(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
    db_session,
):
    deleted_lobby_id = await _prepare_lobby(http_client, authed_user)
    await db_session.execute(
        insert(LobbyParticipant).values(
            lobby_id=deleted_lobby_id,
            user_id=another_authed_user["user_id"],
            username_snapshot=another_authed_user["username"],
        ),
    )
    await db_session.commit()

    delete = await http_client.delete(
        f"/api/v1/lobby/{deleted_lobby_id}",
        headers=authed_user["headers"],
    )
    assert delete.status_code == 204, delete.text

    replacement_lobby_id = await _prepare_lobby(http_client, authed_user)
    assert replacement_lobby_id == deleted_lobby_id

    my_lobbies = await http_client.get(
        "/api/v1/lobby/mine",
        headers=another_authed_user["headers"],
    )
    active_lobbies = await http_client.get(
        "/api/v1/lobby/active",
        headers=another_authed_user["headers"],
    )

    assert my_lobbies.status_code == 200, my_lobbies.text
    assert active_lobbies.status_code == 200, active_lobbies.text
    assert my_lobbies.json() == []
    assert [lobby["id"] for lobby in active_lobbies.json()] == [replacement_lobby_id]


async def test_delete_waiting_lobby_returns_204(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    redis_client,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    category_id = await _create_complete_category(http_client, authed_user)
    attach = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"prompt_category_ids": [category_id]},
        headers=authed_user["headers"],
    )
    assert attach.status_code == 200, attach.text

    advance = await http_client.patch(
        f"/api/v1/lobby/{lobby_id}",
        json={"state": LobbyStateEnum.WAITING_START.value},
        headers=authed_user["headers"],
    )
    assert advance.status_code == 200, advance.text

    response = await http_client.delete(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    assert response.status_code == 204
    assert await redis_client.get(game_state_key(lobby_id)) is None

    after = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    assert after.status_code == 404


@pytest.mark.parametrize(
    "lobby_state",
    [LobbyStateEnum.IN_PROGRESS, LobbyStateEnum.COMPLETED],
)
async def test_delete_active_or_completed_lobby_returns_204(
    lobby_state: LobbyStateEnum,
    http_client: AsyncClient,
    authed_user: AuthedUser,
    db_session,
):
    lobby_id = await _create_lobby(http_client, authed_user)
    await db_session.execute(
        update(Lobby).where(Lobby.id == lobby_id).values(state=lobby_state),
    )
    await db_session.commit()

    response = await http_client.delete(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )

    assert response.status_code == 204

    after = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    assert after.status_code == 404


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


async def test_active_lobbies_returns_only_newly_joinable_waiting_lobbies(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
    register_user,
    db_session,
):
    joined_user = await register_user("joined_user", "joined_pw1")

    joinable_id = await _prepare_lobby(http_client, another_authed_user)
    owned_id = await _prepare_lobby(http_client, authed_user)
    joined_id = await _prepare_lobby(http_client, another_authed_user)
    banned_id = await _prepare_lobby(http_client, another_authed_user)
    created_id = await _create_lobby(http_client, another_authed_user)
    in_progress_id = await _prepare_lobby(http_client, another_authed_user)
    completed_id = await _prepare_lobby(http_client, another_authed_user)

    await db_session.execute(
        insert(LobbyParticipant).values(
            lobby_id=joined_id,
            user_id=authed_user["user_id"],
            username_snapshot=authed_user["username"],
        ),
    )
    await db_session.execute(
        insert(LobbyParticipant).values(
            lobby_id=banned_id,
            user_id=authed_user["user_id"],
            username_snapshot=authed_user["username"],
            is_banned=True,
        ),
    )
    await db_session.execute(
        insert(LobbyParticipant).values(
            lobby_id=joinable_id,
            user_id=joined_user["user_id"],
            username_snapshot=joined_user["username"],
        ),
    )
    await db_session.execute(
        update(Lobby).where(Lobby.id == in_progress_id).values(state=LobbyStateEnum.IN_PROGRESS),
    )
    await db_session.execute(
        update(Lobby).where(Lobby.id == completed_id).values(state=LobbyStateEnum.COMPLETED),
    )
    await db_session.commit()

    response = await http_client.get("/api/v1/lobby/active", headers=authed_user["headers"])

    assert response.status_code == 200, response.text
    ids = [row["id"] for row in response.json()]
    assert ids == [joinable_id]
    assert response.json()[0]["player_count"] == 1
    assert "created_at" in response.json()[0]
    assert {owned_id, joined_id, banned_id, created_id, in_progress_id, completed_id}.isdisjoint(
        ids,
    )


async def test_my_lobbies_returns_owned_and_allowed_participant_lobbies(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
    db_session,
):
    owned_draft_id = await _create_lobby(http_client, authed_user)
    owned_waiting_id = await _prepare_lobby(http_client, authed_user)
    participant_waiting_id = await _prepare_lobby(http_client, another_authed_user)
    participant_completed_id = await _prepare_lobby(http_client, another_authed_user)
    banned_id = await _prepare_lobby(http_client, another_authed_user)

    for lobby_id, is_banned in [
        (participant_waiting_id, False),
        (participant_completed_id, False),
        (banned_id, True),
    ]:
        await db_session.execute(
            insert(LobbyParticipant).values(
                lobby_id=lobby_id,
                user_id=authed_user["user_id"],
                username_snapshot=authed_user["username"],
                is_banned=is_banned,
            ),
        )
    await db_session.execute(
        update(Lobby)
        .where(Lobby.id == participant_completed_id)
        .values(state=LobbyStateEnum.COMPLETED),
    )
    await db_session.commit()

    response = await http_client.get("/api/v1/lobby/mine", headers=authed_user["headers"])

    assert response.status_code == 200, response.text
    by_id = {row["id"]: row for row in response.json()}
    assert {
        owned_draft_id,
        owned_waiting_id,
        participant_waiting_id,
        participant_completed_id,
    } <= by_id.keys()
    assert banned_id not in by_id
    assert by_id[owned_draft_id]["is_owner"] is True
    assert by_id[participant_waiting_id]["is_owner"] is False
    assert by_id[participant_waiting_id]["is_participant"] is True


async def test_completed_lobby_details_returns_competition_rankings_to_allowed_users(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    register_user,
    db_session,
    redis_client,
):
    player_one = await register_user("rank_one", "rank_pw1")
    player_two = await register_user("rank_two", "rank_pw2")
    banned_player = await register_user("rank_banned", "rank_pw3")
    outsider = await register_user("rank_out", "rank_pw4")
    lobby_id = await _prepare_lobby(http_client, authed_user)

    state = await GameStateRepo(redis_client).get_state(lobby_id)
    assert state is not None
    state.players = [
        GamePlayerState(user_id=player_one["user_id"], username=player_one["username"], score=500),
        GamePlayerState(user_id=player_two["user_id"], username=player_two["username"], score=500),
        GamePlayerState(
            user_id=banned_player["user_id"],
            username=banned_player["username"],
            score=100,
            is_banned=True,
        ),
    ]
    for player in state.players:
        await db_session.execute(
            insert(LobbyParticipant).values(
                lobby_id=lobby_id,
                user_id=player.user_id,
                username_snapshot=player.username,
                is_banned=player.is_banned,
                final_score=player.score,
            ),
        )
    await db_session.execute(
        update(Lobby).where(Lobby.id == lobby_id).values(state=LobbyStateEnum.COMPLETED),
    )
    await db_session.commit()

    owner_response = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=authed_user["headers"],
    )
    participant_response = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=player_one["headers"],
    )
    banned_response = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=banned_player["headers"],
    )
    outsider_response = await http_client.get(
        f"/api/v1/lobby/{lobby_id}",
        headers=outsider["headers"],
    )

    assert owner_response.status_code == 200, owner_response.text
    assert participant_response.status_code == 200, participant_response.text
    assert banned_response.status_code == 404
    assert outsider_response.status_code == 404
    rankings = owner_response.json()["final_rankings"]
    assert [(row["username"], row["rank"]) for row in rankings] == [
        ("rank_one", 1),
        ("rank_two", 1),
        ("rank_banned", 3),
    ]
    assert rankings[-1]["is_banned"] is True
