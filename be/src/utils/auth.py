from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pydantic

from configs import settings
from errors.request import UnauthorizedError
from schemas.token import TokenPayloadSchema


def hash_password(password: str) -> str:
    """Hash a plaintext password with a freshly generated bcrypt salt.

    :param password: plaintext password
    :return: bcrypt hash (salt is embedded in the returned string)
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def validate_password(password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a previously hashed value.

    :param password: plaintext password to verify
    :param hashed_password: value produced by :func:`hash_password`
    :return: ``True`` if the password matches the hash
    """
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(user_id: int) -> str:
    """Sign a JWT access token for ``user_id``, expiring per settings."""
    expires_at = datetime.now(UTC) + timedelta(hours=settings.jwt_expiration_hours)
    payload = {"sub": str(user_id), "exp": int(expires_at.timestamp())}
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenPayloadSchema:
    """Verify and decode a JWT; raise ``UnauthorizedError`` on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as e:
        raise UnauthorizedError(
            "Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(
            "Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    try:
        return TokenPayloadSchema.model_validate(payload)
    except pydantic.ValidationError as e:
        raise UnauthorizedError(
            "Malformed token payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
