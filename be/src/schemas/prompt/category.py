from datetime import datetime

from schemas.base import BaseSchema


class PromptCategoryInDBSchema(BaseSchema):
    id: int
    name: str
    owner_id: int | None
    updated_at: datetime
