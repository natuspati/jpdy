from pydantic import Field

from enums.user import UserRole
from schemas.base import BaseSchema


class UserCreateSchema(BaseSchema):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=20)
    invite_code: str | None = None


class AdminKeySchema(BaseSchema):
    key: str = Field(max_length=256)


class UserPublicSchema(BaseSchema):
    id: int
    username: str


class UserRoleSchema(UserPublicSchema):
    role: UserRole
    admin_key_attempted: bool


class UserInDBSchema(UserRoleSchema):
    hashed_password: str
