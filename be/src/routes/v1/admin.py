from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from auth.authenticate import require_admin
from schemas.admin import AdminUserFilterSchema, PaginatedAdminUserSchema
from schemas.error import ErrorResponse
from schemas.user.base import UserInDBSchema
from services import AdminService
from utils.route_response import generate_responses

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

_ADMIN_ONLY = [
    ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Missing, expired, or invalid bearer token"),
    ErrorResponse(status.HTTP_403_FORBIDDEN, "Admin access required"),
]
_USER_NOT_FOUND = ErrorResponse(status.HTTP_404_NOT_FOUND, "User not found")


@router.get("/users", responses=generate_responses(*_ADMIN_ONLY))
async def search_users(
    filters: Annotated[AdminUserFilterSchema, Query()],
    service: Annotated[AdminService, Depends()],
) -> PaginatedAdminUserSchema:
    return await service.search_users(filters)


@router.post(
    "/users/{user_id}/promote",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=generate_responses(*_ADMIN_ONLY, _USER_NOT_FOUND),
)
async def promote_user(user_id: int, service: Annotated[AdminService, Depends()]) -> None:
    await service.promote_user(user_id)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=generate_responses(
        *_ADMIN_ONLY,
        _USER_NOT_FOUND,
    ),
)
async def delete_user(
    user_id: int,
    caller: Annotated[UserInDBSchema, Depends(require_admin)],
    service: Annotated[AdminService, Depends()],
) -> None:
    await service.delete_user(user_id, caller.id)
