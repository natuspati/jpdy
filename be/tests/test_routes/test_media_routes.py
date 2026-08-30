import stat
from pathlib import Path

import pytest
from httpx import AsyncClient

from configs.settings import settings
from fixtures.auth_fixtures import AuthedUser

_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\x0dIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def media_root(tmp_path: Path):
    original = settings.media_root
    settings.media_root = tmp_path / "media"
    try:
        yield settings.media_root
    finally:
        settings.media_root = original


async def _upload_png(client: AsyncClient, user: AuthedUser) -> dict[str, object]:
    response = await client.post(
        "/api/v1/media",
        data={"kind": "image"},
        files={"file": ("sample.png", _MINIMAL_PNG, "image/png")},
        headers=user["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_category(client: AsyncClient, user: AuthedUser) -> int:
    response = await client.post(
        "/api/v1/category",
        json={"name": "Media category"},
        headers=user["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_upload_media_stores_world_readable_file(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    media_root: Path,
):
    asset = await _upload_png(http_client, authed_user)

    assert asset["url"] == f"/media/{asset['storage_key']}"
    stored_path = media_root / str(asset["storage_key"])
    assert stored_path.exists()
    assert stat.S_IMODE(stored_path.stat().st_mode) == 0o644


async def test_media_assets_can_only_be_assigned_by_their_owner(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    another_authed_user: AuthedUser,
    media_root: Path,
):
    asset = await _upload_png(http_client, authed_user)
    category_id = await _create_category(http_client, another_authed_user)

    response = await http_client.post(
        f"/api/v1/category/{category_id}/prompts",
        json={
            "question": "Name this image",
            "question_type": "image",
            "question_media_asset_id": asset["id"],
            "answer": "Answer",
            "answer_type": "text",
            "answer_media_asset_id": None,
            "order": 1,
        },
        headers=another_authed_user["headers"],
    )

    assert response.status_code == 403


async def test_category_get_returns_question_and_answer_media_references(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    media_root: Path,
):
    question_asset = await _upload_png(http_client, authed_user)
    answer_asset = await _upload_png(http_client, authed_user)
    category_id = await _create_category(http_client, authed_user)

    create = await http_client.post(
        f"/api/v1/category/{category_id}/prompts",
        json={
            "question": "Name this image",
            "question_type": "image",
            "question_media_asset_id": question_asset["id"],
            "answer": "A green square",
            "answer_type": "image",
            "answer_media_asset_id": answer_asset["id"],
            "order": 1,
        },
        headers=authed_user["headers"],
    )
    assert create.status_code == 201, create.text

    category = await http_client.get(
        f"/api/v1/category/{category_id}",
        headers=authed_user["headers"],
    )
    assert category.status_code == 200, category.text
    prompt = category.json()["prompts"][0]
    assert prompt["question_content"]["media"] == {
        "asset_id": question_asset["id"],
        "url": question_asset["url"],
        "mime_type": "image/png",
        "filename": "sample.png",
    }
    assert prompt["answer_content"]["media"] == {
        "asset_id": answer_asset["id"],
        "url": answer_asset["url"],
        "mime_type": "image/png",
        "filename": "sample.png",
    }
