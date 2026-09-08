import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import Depends, UploadFile

from configs import settings
from configs.constants import MEDIA_MAX_BYTES_BY_KIND
from database import UnitOfWork
from enums import MediaKindEnum
from errors.request import BadRequestError, ForbiddenError, NotFoundError
from schemas.media import MediaAssetResponseSchema
from schemas.user.base import UserPublicSchema
from utils.media import build_media_response

_UPLOAD_CHUNK_SIZE = 64 * 1024
_PUBLISHED_MEDIA_MODE = 0o644


@dataclass(frozen=True)
class DetectedMedia:
    media_kind: MediaKindEnum
    mime_type: str
    extension: str


class MediaService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def upload_media_asset(
        self,
        *,
        upload: UploadFile,
        media_kind: MediaKindEnum,
        user: UserPublicSchema,
    ) -> MediaAssetResponseSchema:
        temporary_path: Path | None = None
        final_path: Path | None = None
        try:
            temporary_path, byte_size = await _store_upload_temporarily(upload, media_kind)
            detected = _detect_media(temporary_path)
            if detected.media_kind != media_kind:
                raise BadRequestError(
                    f"Uploaded file is {detected.media_kind.value}, not {media_kind.value}",
                )

            storage_key = f"{uuid.uuid4().hex}{detected.extension}"
            final_path = settings.media_root / storage_key
            original_filename = _safe_original_filename(
                upload.filename,
                detected.extension,
            )

            async with self._uow as uow:
                asset = await uow.media_asset_repo.insert_media_asset(
                    owner_id=user.id,
                    storage_key=storage_key,
                    original_filename=original_filename,
                    media_kind=detected.media_kind.value,
                    mime_type=detected.mime_type,
                    byte_size=byte_size,
                )
                os.chmod(temporary_path, _PUBLISHED_MEDIA_MODE)
                os.replace(temporary_path, final_path)
                temporary_path = None
            return build_media_response(asset)
        except Exception:
            if final_path is not None:
                final_path.unlink(missing_ok=True)
            raise
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            await upload.close()

    async def delete_media_asset(
        self,
        *,
        asset_id: int,
        user: UserPublicSchema,
    ) -> None:
        storage_key: str
        async with self._uow as uow:
            asset = await uow.media_asset_repo.select_media_asset(asset_id)
            if asset is None:
                raise NotFoundError(f"Media asset {asset_id} not found")
            if asset.owner_id != user.id:
                raise ForbiddenError("Only the owner can delete this media asset")
            if await uow.media_asset_repo.media_asset_is_attached(asset_id):
                raise BadRequestError(
                    "Media attached to a prompt cannot be deleted; replace or remove it first",
                )
            storage_key = asset.storage_key
            await uow.media_asset_repo.delete_media_asset(asset_id)
        (settings.media_root / storage_key).unlink(missing_ok=True)


async def _store_upload_temporarily(
    upload: UploadFile,
    media_kind: MediaKindEnum,
) -> tuple[Path, int]:
    settings.media_root.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=settings.media_root,
        prefix=".upload-",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    total = 0
    max_bytes = MEDIA_MAX_BYTES_BY_KIND[media_kind.value]
    try:
        with os.fdopen(descriptor, "wb") as output:
            while chunk := await upload.read(min(_UPLOAD_CHUNK_SIZE, max_bytes - total + 1)):
                total += len(chunk)
                if total > max_bytes:
                    raise BadRequestError(
                        f"{media_kind.value.capitalize()} files must be at most "
                        f"{max_bytes // (1024 * 1024)} MB",
                    )
                output.write(chunk)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    if total == 0:
        temporary_path.unlink(missing_ok=True)
        raise BadRequestError("Uploaded file is empty")
    return temporary_path, total


def _detect_media(path: Path) -> DetectedMedia:
    with path.open("rb") as source:
        header = source.read(64)

    if header.startswith(b"\xff\xd8\xff"):
        return DetectedMedia(MediaKindEnum.IMAGE, "image/jpeg", ".jpg")
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedMedia(MediaKindEnum.IMAGE, "image/png", ".png")
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return DetectedMedia(MediaKindEnum.IMAGE, "image/webp", ".webp")
    if header.startswith(b"ID3") or _looks_like_mpeg_audio(header):
        return DetectedMedia(MediaKindEnum.AUDIO, "audio/mpeg", ".mp3")
    if _looks_like_aac_audio(header):
        return DetectedMedia(MediaKindEnum.AUDIO, "audio/aac", ".aac")
    if header.startswith(b"OggS"):
        return DetectedMedia(MediaKindEnum.AUDIO, "audio/ogg", ".ogg")
    if len(header) >= 12 and header[4:8] == b"ftyp":
        major_brand = header[8:12]
        compatible_brands = header[16:]
        if major_brand in {b"M4A ", b"M4B "} or b"M4A " in compatible_brands:
            return DetectedMedia(MediaKindEnum.AUDIO, "audio/mp4", ".m4a")
        if _is_h264_aac_mp4(path):
            return DetectedMedia(MediaKindEnum.VIDEO, "video/mp4", ".mp4")
        raise BadRequestError("MP4 video must contain browser-compatible H.264 video and AAC audio")
    raise BadRequestError(
        "Unsupported or invalid media file. Use JPEG, PNG, WebP, MP3, M4A/AAC, Ogg, or MP4",
    )


def _looks_like_mpeg_audio(header: bytes) -> bool:
    return (
        len(header) >= 2
        and header[0] == 0xFF
        and header[1] & 0xE0 == 0xE0
        and header[1] & 0x06 != 0
    )


def _looks_like_aac_audio(header: bytes) -> bool:
    return len(header) >= 2 and header[0] == 0xFF and header[1] & 0xF6 == 0xF0


def _is_h264_aac_mp4(path: Path) -> bool:
    has_h264 = False
    has_aac = False
    with path.open("rb") as source:
        while chunk := source.read(_UPLOAD_CHUNK_SIZE):
            has_h264 = has_h264 or b"avc1" in chunk
            has_aac = has_aac or b"mp4a" in chunk
            if has_h264 and has_aac:
                return True
    return False


def _safe_original_filename(filename: str | None, extension: str) -> str:
    candidate = Path(filename or "").name.strip()
    if not candidate:
        return f"upload{extension}"
    return candidate[:256]
