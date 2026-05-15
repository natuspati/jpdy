from errors.base import BaseError


class SchemaValidationError(BaseError):
    detail = "Schema validation error"
