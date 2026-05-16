from pydantic import BaseModel, model_validator


class BaseSchema(BaseModel):
    pass


class OneFieldSetSchemaMixin(BaseSchema):
    """
    Reject inputs where the caller supplied no fields. Intended for update
    payloads — without this, an empty body would silently no-op.

    Raises ``ValueError`` so FastAPI surfaces it as a 422 validation error
    rather than a 500 application error.
    """

    @model_validator(mode="after")
    def _ensure_at_least_one_field_set(self) -> OneFieldSetSchemaMixin:
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self
