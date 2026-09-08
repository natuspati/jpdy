from datetime import datetime

from pydantic import Field

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


class MediaAssetResponseSchema(MediaAssetInDBSchema):
    url: str


class MediaReferenceSchema(BaseSchema):
    asset_id: int
    url: str
    mime_type: str
    filename: str
