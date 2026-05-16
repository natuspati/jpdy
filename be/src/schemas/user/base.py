from functools import cached_property

from pydantic import Field, computed_field

from schemas.base import BaseSchema
from utils.auth import hash_password


class UserCreateSchema(BaseSchema):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=20)

    @computed_field
    @cached_property
    def hashed_password(self) -> str:
        return hash_password(self.password)


class UserPublicSchema(BaseSchema):
    id: int
    username: str


class UserInDBSchema(UserPublicSchema):
    hashed_password: str
