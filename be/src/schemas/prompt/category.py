from datetime import datetime

from pydantic import Field, field_validator

from enums.prompt import PromptCategoryKindEnum, PromptCategorySortEnum
from schemas.base import BaseSchema, OneFieldSetSchemaMixin
from schemas.pagination import PaginationSchema


class PromptCategoryInDBSchema(BaseSchema):
    id: int
    name: str
    kind: PromptCategoryKindEnum = PromptCategoryKindEnum.STANDARD
    owner_id: int | None
    updated_at: datetime


class PromptCategoryCreateSchema(BaseSchema):
    name: str = Field(min_length=1, max_length=256)
    kind: PromptCategoryKindEnum = PromptCategoryKindEnum.STANDARD


class PromptCategoryUpdateSchema(OneFieldSetSchemaMixin):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    prompt_order: dict[int, int] | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _reject_explicit_null(cls, v: object) -> object:
        if v is None:
            raise ValueError("must not be null")
        return v


class PromptCategoryFilterSchema(PaginationSchema):
    ids: list[int] | None = None
    name: str | None = Field(default=None, min_length=1, max_length=256)
    owner_ids: list[int] | None = None
    is_complete: bool | None = None
    kind: PromptCategoryKindEnum | None = None
    sort: PromptCategorySortEnum = PromptCategorySortEnum.UPDATED_DESC
    updated_at_start: datetime | None = None
    updated_at_end: datetime | None = None
