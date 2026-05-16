import secrets
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBasicCredentials

from auth.scheme import basic_security, oauth2_scheme
from configs import settings
from database import UnitOfWork
from errors.request import ForbiddenError, UnauthorizedError
from schemas.user.base import UserInDBSchema
from utils.auth import decode_access_token


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


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    uow: Annotated[UnitOfWork, Depends()],
) -> UserInDBSchema:
    """Resolve the authenticated user from the request's Bearer token."""
    if not token:
        raise UnauthorizedError(
            "Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    async with uow:
        user = await uow.user_repo.select_user(user_id=payload.sub)
    if user is None:
        raise UnauthorizedError(
            "User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
