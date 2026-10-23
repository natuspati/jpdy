from collections.abc import Awaitable, Callable
from typing import TypedDict

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enums.user import UserRole
from models.user import User


class AuthedUser(TypedDict):
    user_id: int
    username: str
    password: str
    token: str
    headers: dict[str, str]


async def _register_and_sign_in(
    client: AsyncClient,
    username: str,
    password: str,
) -> AuthedUser:
    reg = await client.post(
        "/api/v1/user/register",
        json={"username": username, "password": password},
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]

    sign_in = await client.post(
        "/api/v1/user/sign-in",
        data={"username": username, "password": password},
    )
    assert sign_in.status_code == 200, sign_in.text
    token = sign_in.json()["access_token"]

    return AuthedUser(
        user_id=user_id,
        username=username,
        password=password,
        token=token,
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
async def authed_user(http_client: AsyncClient) -> AuthedUser:
    """Register a default user and return id, token, and Authorization header."""
    return await _register_and_sign_in(http_client, "owner_user", "owner_pw1")


@pytest.fixture
async def another_authed_user(http_client: AsyncClient) -> AuthedUser:
    """A second registered user, useful for owner / non-owner scenarios."""
    return await _register_and_sign_in(http_client, "intruder_user", "intruder_pw1")


@pytest.fixture
def register_user(
    http_client: AsyncClient,
) -> Callable[[str, str], Awaitable[AuthedUser]]:
    """Factory variant: tests can register additional users on demand."""

    async def _make(username: str, password: str) -> AuthedUser:
        return await _register_and_sign_in(http_client, username, password)

    return _make


@pytest.fixture
async def admin_user(
    register_user: Callable[[str, str], Awaitable[AuthedUser]],
    db_session_maker: async_sessionmaker[AsyncSession],
) -> AuthedUser:
    """A registered user promoted straight in the DB (the API has no first-admin path)."""
    user = await register_user("admin_user", "admin_pw1")
    async with db_session_maker() as session:
        await session.execute(
            update(User).where(User.id == user["user_id"]).values(role=UserRole.ADMIN),
        )
        await session.commit()
    return user
