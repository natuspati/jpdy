from collections.abc import Sequence

import pydantic
from sqlalchemy import Row

from errors.validation import SQLModelValidationError
from models.base import Base


def validate_model[T: pydantic.BaseModel](
    data: Sequence[Base] | Sequence[Row] | Base | None,
    dto: type[T],
) -> list[T] | T | None:
    if data is None:
        return None

    if isinstance(data, Sequence):
        return _validate_models(data=data, dto=dto)

    return _validate_model(data=data, dto=dto)


def _validate_model[T: pydantic.BaseModel](
    data: Base | Row,
    dto: type[T],
) -> T:
    if isinstance(data, Row):
        data = data._mapping
    try:
        return dto.model_validate(data, from_attributes=True)
    except pydantic.ValidationError as error:
        raise SQLModelValidationError(error) from error


def _validate_models[T: pydantic.BaseModel](
    data: Sequence[Base] | Sequence[Row],
    dto: type[T],
) -> list[T]:
    if not data:
        return []

    if isinstance(data[0], Row):
        try:
            return [dto.model_validate(obj._mapping, from_attributes=True) for obj in data]
        except pydantic.ValidationError as error:
            raise SQLModelValidationError(error) from error

    try:
        return [dto.model_validate(obj, from_attributes=True) for obj in data]
    except pydantic.ValidationError as error:
        raise SQLModelValidationError(error) from error
