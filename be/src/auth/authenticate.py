import secrets
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBasicCredentials

from auth.scheme import basic_security
from configs import settings
from errors.request import ForbiddenError, UnauthorizedError


def check_basic_auth(
    credentials: Annotated[HTTPBasicCredentials, Depends(basic_security)],
) -> None:
    if not credentials:
        raise UnauthorizedError(
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    is_correct_username = secrets.compare_digest(
        credentials.username,
        settings.openapi_schema_user,
    )
    is_correct_password = secrets.compare_digest(
        credentials.password,
        settings.openapi_schema_password,
    )

    if not (is_correct_username and is_correct_password):
        raise ForbiddenError("Failed to verify credentials")
