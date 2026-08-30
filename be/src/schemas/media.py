from datetime import datetime

from pydantic import Field, computed_field

from configs import settings
from enums import MediaKindEnum
from schemas.base import BaseSchema


class MediaAssetInDBSchema(BaseSchema):
    id: int
    owner_id: int | None
    storage_key: str
    original_filename: str
    media_kind: MediaKindEnum
    mime_type: str
    byte_size: int = Field(ge=0)
    duration_seconds: int | None
    width: int | None
    height: int | None
    created_at: datetime

    @computed_field
    @property
    def url(self) -> str:
        return f"{settings.media_url_prefix.rstrip('/')}/{self.storage_key}"


class MediaReferenceSchema(BaseSchema):
    asset_id: int
    url: str
    mime_type: str
    filename: str

    @classmethod
    def from_asset(cls, asset: MediaAssetInDBSchema) -> MediaReferenceSchema:
        return cls(
            asset_id=asset.id,
            url=asset.url,
            mime_type=asset.mime_type,
            filename=asset.original_filename,
        )
