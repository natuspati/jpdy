import io
import stat
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

from configs.settings import settings
from fixtures.auth_fixtures import AuthedUser


def _png_bytes(width: int = 1, height: int = 1) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "green").save(buffer, "PNG")
    return buffer.getvalue()


_MINIMAL_PNG = _png_bytes()


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


async def test_upload_image_is_converted_to_webp_and_capped_at_1920px(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    media_root: Path,
):
    response = await http_client.post(
        "/api/v1/media",
        data={"kind": "image"},
        files={"file": ("big.png", _png_bytes(3000, 1000), "image/png")},
        headers=authed_user["headers"],
    )

    assert response.status_code == 201, response.text
    asset = response.json()
    assert asset["mime_type"] == "image/webp"
    assert asset["storage_key"].endswith(".webp")
    assert (asset["width"], asset["height"]) == (1920, 640)
    stored_path = media_root / asset["storage_key"]
    assert asset["byte_size"] == stored_path.stat().st_size
    with Image.open(stored_path) as stored:
        assert stored.format == "WEBP"
        assert stored.size == (1920, 640)
    assert not list(media_root.glob(".upload-*"))


async def test_upload_corrupt_image_is_rejected_without_leftovers(
    http_client: AsyncClient,
    authed_user: AuthedUser,
    media_root: Path,
):
    response = await http_client.post(
        "/api/v1/media",
        data={"kind": "image"},
        files={"file": ("bad.png", _MINIMAL_PNG[:30], "image/png")},
        headers=authed_user["headers"],
    )

    assert response.status_code == 400
    assert not list(media_root.iterdir())


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
        "mime_type": "image/webp",
        "filename": "sample.png",
    }
    assert prompt["answer_content"]["media"] == {
        "asset_id": answer_asset["id"],
        "url": answer_asset["url"],
        "mime_type": "image/webp",
        "filename": "sample.png",
    }
