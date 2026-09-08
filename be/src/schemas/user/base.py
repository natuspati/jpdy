from pydantic import Field

from schemas.base import BaseSchema


class UserCreateSchema(BaseSchema):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=20)


class UserPublicSchema(BaseSchema):
    id: int
    username: str


class UserInDBSchema(UserPublicSchema):
    hashed_password: str
