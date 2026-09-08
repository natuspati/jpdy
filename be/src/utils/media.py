from typing import TYPE_CHECKING

from configs import settings
from enums import MediaKindEnum
from errors.request import BadRequestError, ForbiddenError
from schemas.media import MediaAssetInDBSchema, MediaAssetResponseSchema, MediaReferenceSchema

if TYPE_CHECKING:
    from database import UnitOfWork


def build_media_url(storage_key: str) -> str:
    """Build public media URL from configured prefix and persisted storage key."""
    return f"{settings.media_url_prefix.rstrip('/')}/{storage_key}"


def build_media_reference(asset: MediaAssetInDBSchema) -> MediaReferenceSchema:
    return MediaReferenceSchema(
        asset_id=asset.id,
        url=build_media_url(asset.storage_key),
        mime_type=asset.mime_type,
        filename=asset.original_filename,
    )


def build_media_response(asset: MediaAssetInDBSchema) -> MediaAssetResponseSchema:
    return MediaAssetResponseSchema(
        **asset.model_dump(),
        url=build_media_url(asset.storage_key),
    )


async def ensure_owned_media_asset(
    *,
    uow: UnitOfWork,
    asset_id: int | None,
    expected_kind: MediaKindEnum | None,
    user_id: int,
    field_name: str,
) -> None:
    if asset_id is None:
        return
    asset = await uow.media_asset_repo.select_media_asset(asset_id)
    if asset is None:
        raise BadRequestError(f"{field_name} does not exist")
    if asset.owner_id != user_id:
        raise ForbiddenError("Only your media assets can be assigned to a prompt")
    if expected_kind is None:
        raise BadRequestError(f"{field_name} is not allowed for text content")
    if asset.media_kind != expected_kind:
        raise BadRequestError(
            f"{field_name} must reference {expected_kind.value} media",
        )
