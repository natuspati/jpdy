from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from auth import get_current_user
from enums import MediaKindEnum
from schemas.error import ErrorResponse
from schemas.media import MediaAssetInDBSchema
from schemas.user.base import UserInDBSchema
from services.media import MediaService
from utils.route_response import generate_responses

router = APIRouter(prefix="/media", tags=["media"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=generate_responses(
        ErrorResponse(status.HTTP_400_BAD_REQUEST, "Invalid media upload"),
        ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Missing, expired, or invalid bearer token"),
    ),
)
async def upload_media(
    file: Annotated[UploadFile, File()],
    kind: Annotated[MediaKindEnum, Form()],
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[MediaService, Depends()],
) -> MediaAssetInDBSchema:
    return await service.upload_media_asset(
        upload=file,
        media_kind=kind,
        user=current_user,
    )


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=generate_responses(
        ErrorResponse(status.HTTP_400_BAD_REQUEST, "Media asset is attached to a prompt"),
        ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Missing, expired, or invalid bearer token"),
        ErrorResponse(status.HTTP_403_FORBIDDEN, "Only the owner can delete this media asset"),
        ErrorResponse(status.HTTP_404_NOT_FOUND, "Media asset not found"),
    ),
)
async def delete_media(
    asset_id: int,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[MediaService, Depends()],
) -> None:
    await service.delete_media_asset(asset_id=asset_id, user=current_user)
