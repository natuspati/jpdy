import pydantic

from errors.base import BaseError


class SchemaValidationError(BaseError):
    detail = "Schema validation error"


class SQLModelValidationError(SchemaValidationError):
    detail = "Database model validation error"

    def __init__(self, error: pydantic.ValidationError):
        errors = error.errors(include_url=False)
        try:
            for err in errors:
                err["input"] = {
                    "table": err["input"].__table__.fullname,
                    "data": err["input"].to_dict(json=True),
                }
        except KeyError, AttributeError:
            errors = str(errors)
        super().__init__(extra_info={"errors": errors})
