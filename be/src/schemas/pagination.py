from pydantic import Field

from schemas.base import BaseSchema


class PaginationSchema(BaseSchema):
    page: int = Field(default=0, ge=0)
    size: int = Field(default=100, gt=0, le=1000)

    @property
    def offset(self) -> int:
        return self.page * self.size

    @property
    def limit(self) -> int:
        return self.size


class PaginatedResponseSchema[T](BaseSchema):
    contents: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 0
    size: int = 0
