from datetime import UTC, datetime
from pathlib import Path

import pytest
from fakeredis import FakeAsyncRedis
from httpx import AsyncClient
from polyfactory.factories.pydantic_factory import ModelFactory
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from configs import settings
from enums.lobby import LobbyStateEnum
from fixtures.auth_fixtures import AuthedUser
from models.lobby import Lobby, LobbyParticipant, LobbyRoundResult
from models.media_asset import MediaAsset
from models.prompt import Prompt
from models.prompt_category import PromptCategory
from models.user import User
from repos.game_state import GameStateRepo
from schemas.lobby.game_state import GameLobbyState
from utils.game_state import game_state_key

USERS = "/api/v1/admin/users"


async def _lobby(
    db: AsyncSession,
    owner_id: int,
    state: LobbyStateEnum = LobbyStateEnum.COMPLETED,
) -> int:
    result = await db.execute(insert(Lobby).values(owner_id=owner_id, state=state))
    await db.commit()
    return result.inserted_primary_key[0]


async def _participant(db: AsyncSession, lobby_id: int, user: AuthedUser, **extra) -> None:
    await db.execute(
        insert(LobbyParticipant).values(
            lobby_id=lobby_id,
            user_id=user["user_id"],
            username_snapshot=user["username"],
            **extra,
        ),
    )
    await db.commit()


async def _names(http_client: AsyncClient, admin: AuthedUser, **params) -> list[str]:
    response = await http_client.get(USERS, params=params, headers=admin["headers"])
    assert response.status_code == 200, response.text
    return [u["username"] for u in response.json()["contents"]]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", USERS),
        ("POST", f"{USERS}/1/promote"),
        ("DELETE", f"{USERS}/1"),
    ],
)
async def test_generic_user_gets_403_and_anonymous_401(
    method: str,
    path: str,
    http_client: AsyncClient,
    authed_user: AuthedUser,
):
    generic = await http_client.request(method, path, headers=authed_user["headers"])
    anonymous = await http_client.request(method, path)

    assert generic.status_code == 403
    assert anonymous.status_code == 401


async def test_promotion_applies_to_existing_token_immediately(
    http_client: AsyncClient,
    admin_user: AuthedUser,
    authed_user: AuthedUser,
):
    assert (await http_client.get(USERS, headers=authed_user["headers"])).status_code == 403

    promote = await http_client.post(
        f"{USERS}/{authed_user['user_id']}/promote",
        headers=admin_user["headers"],
    )

    assert promote.status_code == 204
    assert (await http_client.get(USERS, headers=authed_user["headers"])).status_code == 200
    # idempotent
    again = await http_client.post(
        f"{USERS}/{authed_user['user_id']}/promote",
        headers=admin_user["headers"],
    )
    assert again.status_code == 204


async def test_promote_unknown_user_returns_404(http_client: AsyncClient, admin_user: AuthedUser):
    response = await http_client.post(f"{USERS}/9999/promote", headers=admin_user["headers"])
    assert response.status_code == 404


async def test_list_filters_sort_and_paginate(
    http_client: AsyncClient,
    admin_user: AuthedUser,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
    db_session: AsyncSession,
):
    # admin_user: admin_user, owner_user, intruder_user
    await db_session.execute(
        update(User)
        .where(User.id == authed_user["user_id"])
        .values(created_at=datetime(2026, 1, 10, 23, 59, tzinfo=UTC)),
    )
    await db_session.execute(
        update(User)
        .where(User.id == another_authed_user["user_id"])
        .values(created_at=datetime(2026, 1, 11, 0, 1, tzinfo=UTC)),
    )
    await db_session.commit()
    h = admin_user

    assert await _names(http_client, h, role="admin") == ["admin_user"]
    assert await _names(http_client, h, role="generic", sort="username_asc") == [
        "intruder_user",
        "owner_user",
    ]
    assert await _names(http_client, h, username="OWNER") == ["owner_user"]
    # created_to is inclusive of the whole day
    assert await _names(http_client, h, created_to="2026-01-10") == ["owner_user"]
    assert await _names(http_client, h, created_from="2026-01-11", created_to="2026-01-11") == [
        "intruder_user",
    ]
    assert await _names(http_client, h, sort="username_desc") == [
        "owner_user",
        "intruder_user",
        "admin_user",
    ]

    page = await http_client.get(
        USERS,
        params={"sort": "username_asc", "size": 2, "page": 1},
        headers=h["headers"],
    )
    body = page.json()
    assert body["total"] == 3
    assert [u["username"] for u in body["contents"]] == ["owner_user"]


async def test_list_counts_played_and_hosted_lobbies(
    http_client: AsyncClient,
    admin_user: AuthedUser,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
    db_session: AsyncSession,
):
    host = authed_user["user_id"]
    for state in (LobbyStateEnum.IN_PROGRESS, LobbyStateEnum.COMPLETED):
        lobby_id = await _lobby(db_session, host, state)
        await _participant(db_session, lobby_id, another_authed_user)
    waiting = await _lobby(db_session, host, LobbyStateEnum.WAITING_START)
    await _participant(db_session, waiting, another_authed_user)
    banned = await _lobby(db_session, host, LobbyStateEnum.COMPLETED)
    await _participant(db_session, banned, another_authed_user, is_banned=True)

    response = await http_client.get(USERS, headers=admin_user["headers"])

    by_name = {u["username"]: u for u in response.json()["contents"]}
    assert by_name["owner_user"]["lobbies_hosted"] == 3
    assert by_name["owner_user"]["lobbies_played"] == 0
    assert by_name["intruder_user"]["lobbies_played"] == 2
    assert by_name["intruder_user"]["lobbies_hosted"] == 0


async def test_delete_rejects_self_admins_and_unknown(
    http_client: AsyncClient,
    admin_user: AuthedUser,
    authed_user: AuthedUser,
    db_session: AsyncSession,
):
    await db_session.execute(
        update(User).where(User.id == authed_user["user_id"]).values(role="admin"),
    )
    await db_session.commit()
    headers = admin_user["headers"]

    own = await http_client.delete(f"{USERS}/{admin_user['user_id']}", headers=headers)
    other_admin = await http_client.delete(f"{USERS}/{authed_user['user_id']}", headers=headers)
    unknown = await http_client.delete(f"{USERS}/9999", headers=headers)

    assert (own.status_code, other_admin.status_code, unknown.status_code) == (403, 403, 404)


async def test_delete_user_removes_unfinished_keeps_completed_history(
    http_client: AsyncClient,
    admin_user: AuthedUser,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
    db_session: AsyncSession,
    redis_client: FakeAsyncRedis,
):
    victim = authed_user["user_id"]
    live = await _lobby(db_session, victim, LobbyStateEnum.IN_PROGRESS)
    waiting = await _lobby(db_session, victim, LobbyStateEnum.WAITING_START)
    done = await _lobby(db_session, victim, LobbyStateEnum.COMPLETED)
    await _participant(db_session, done, another_authed_user, final_score=100)
    await db_session.execute(
        insert(LobbyRoundResult).values(
            lobby_id=done,
            round_number=1,
            user_id=another_authed_user["user_id"],
            username_snapshot="intruder_user",
            score=100,
            score_delta=100,
        ),
    )
    # the victim also played in somebody else's lobby
    elsewhere = await _lobby(db_session, another_authed_user["user_id"])
    await _participant(db_session, elsewhere, authed_user)
    state_factory = ModelFactory.create_factory(GameLobbyState)
    await GameStateRepo(redis_client).save_state(state_factory.build(lobby_id=live))

    response = await http_client.delete(f"{USERS}/{victim}", headers=admin_user["headers"])

    assert response.status_code == 204, response.text
    db_session.expire_all()
    assert await db_session.get(User, victim) is None
    assert await db_session.get(Lobby, live) is None
    assert await db_session.get(Lobby, waiting) is None
    assert await redis_client.get(game_state_key(live)) is None
    kept = await db_session.get(Lobby, done)
    assert kept is not None
    assert kept.owner_id is None
    assert kept.owner_username_snapshot == "owner_user"
    participants = (
        await db_session.execute(
            select(
                LobbyParticipant.lobby_id,
                LobbyParticipant.user_id,
                LobbyParticipant.final_score,
            ),
        )
    ).all()
    assert (done, another_authed_user["user_id"], 100) in participants
    assert (elsewhere, None, None) in participants
    assert (await db_session.execute(select(LobbyRoundResult))).scalars().one().score == 100

    mine = await http_client.get("/api/v1/lobby/mine", headers=another_authed_user["headers"])
    hosts = {lobby["id"]: lobby["host_username"] for lobby in mine.json()["contents"]}
    assert hosts[done] == "owner_user"


async def test_delete_user_removes_unattached_media_and_keeps_attached(
    http_client: AsyncClient,
    admin_user: AuthedUser,
    authed_user: AuthedUser,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "media_root", tmp_path)
    owner = authed_user["user_id"]
    category = (
        await db_session.execute(
            insert(PromptCategory).values(name="Kept", owner_id=owner),
        )
    ).inserted_primary_key[0]
    ids = {}
    for key in ("loose.png", "used.png"):
        (tmp_path / key).write_bytes(b"x")
        ids[key] = (
            await db_session.execute(
                insert(MediaAsset).values(
                    owner_id=owner,
                    storage_key=key,
                    original_filename=key,
                    media_kind="image",
                    mime_type="image/png",
                    byte_size=1,
                ),
            )
        ).inserted_primary_key[0]
    await db_session.execute(
        insert(Prompt).values(
            category_id=category,
            question="q",
            answer="a",
            question_type="image",
            answer_type="text",
            question_media_asset_id=ids["used.png"],
            order=1,
        ),
    )
    await db_session.commit()

    response = await http_client.delete(f"{USERS}/{owner}", headers=admin_user["headers"])

    assert response.status_code == 204, response.text
    db_session.expire_all()
    assert await db_session.get(MediaAsset, ids["loose.png"]) is None
    assert not (tmp_path / "loose.png").exists()
    attached = await db_session.get(MediaAsset, ids["used.png"])
    assert attached is not None
    assert attached.owner_id is None
    assert (tmp_path / "used.png").exists()
