from datetime import date, datetime

from pydantic import Field

from enums.user import AdminUserSortEnum, UserRole
from schemas.base import BaseSchema
from schemas.pagination import PaginatedResponseSchema, PaginationSchema


class AdminUserFilterSchema(PaginationSchema):
    size: int = Field(default=20, gt=0, le=100)
    role: UserRole | None = None
    username: str | None = Field(default=None, min_length=1, max_length=20)
    created_from: date | None = None
    created_to: date | None = Field(default=None, description="Inclusive.")
    sort: AdminUserSortEnum = AdminUserSortEnum.CREATED_AT_DESC


class AdminUserListItemSchema(BaseSchema):
    id: int
    username: str
    role: UserRole
    created_at: datetime
    lobbies_played: int
    lobbies_hosted: int


class PaginatedAdminUserSchema(PaginatedResponseSchema[AdminUserListItemSchema]):
    pass
