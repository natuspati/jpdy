import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
import socketio
from fakeredis import FakeAsyncRedis, FakeServer
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import sockets.uow as sockets_uow
from enums.lobby import LobbyStateEnum
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from models.lobby import Lobby, LobbyPromptCategory
from models.prompt import Prompt
from models.prompt_category import PromptCategory
from models.user import User
from repos.game_state import GameStateRepo
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePromptState,
)
from utils.auth import create_access_token, hash_password


@dataclass(slots=True)
class SeededUser:
    id: int
    username: str
    token: str


@dataclass(slots=True)
class SeededLobby:
    lobby_id: int
    host: SeededUser
    players: list[SeededUser]
    state: GameLobbyState
    category_ids: list[int]
    prompt_ids: list[int]


@pytest.fixture
async def socket_session_overrides(
    db_path: Path,
    fake_redis_server: FakeServer,
) -> AsyncGenerator[None]:
    """
    Repoint ``sockets.uow``'s session factories so each socket handler call
    gets a fresh async SQLAlchemy engine and fakeredis client bound to the
    *handler's* event loop. The socket server runs in a separate uvicorn
    thread with its own loop, so reusing engine/redis instances created on
    the test loop would explode with ``MissingGreenlet`` — instead we build
    them per call and dispose after.

    xdist workers are separate processes, so module-level mutation is safe
    within a worker.
    """
    db_url = f"sqlite+aiosqlite:///{db_path}"
    original_db = sockets_uow.db_session_factory
    original_redis = sockets_uow.redis_session_factory

    async def _db_factory() -> AsyncGenerator[AsyncSession]:
        engine = create_async_engine(db_url, future=True)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session
        finally:
            await engine.dispose()

    async def _redis_factory() -> AsyncGenerator[FakeAsyncRedis]:
        client = FakeAsyncRedis(server=fake_redis_server)
        try:
            yield client
        finally:
            await client.aclose()

    sockets_uow.db_session_factory = _db_factory  # type: ignore[assignment]
    sockets_uow.redis_session_factory = _redis_factory  # type: ignore[assignment]
    try:
        yield
    finally:
        sockets_uow.db_session_factory = original_db
        sockets_uow.redis_session_factory = original_redis


async def _insert_user(session: AsyncSession, username: str) -> SeededUser:
    row = (
        await session.execute(
            insert(User)
            .values(username=username, hashed_password=hash_password("pw" + username))
            .returning(User),
        )
    ).scalar_one()
    return SeededUser(id=row.id, username=row.username, token=create_access_token(row.id))


async def _insert_lobby(
    session: AsyncSession,
    owner_id: int,
    state: LobbyStateEnum,
) -> Lobby:
    return (
        await session.execute(
            insert(Lobby).values(owner_id=owner_id, state=state).returning(Lobby),
        )
    ).scalar_one()


@dataclass(slots=True)
class _SeededCategory:
    id: int
    name: str
    prompts: list[Prompt]


async def _insert_category(
    session: AsyncSession,
    owner_id: int,
    name: str,
    prompts: int,
) -> _SeededCategory:
    category = (
        await session.execute(
            insert(PromptCategory).values(name=name, owner_id=owner_id).returning(PromptCategory),
        )
    ).scalar_one()
    inserted_prompts: list[Prompt] = []
    for order in range(1, prompts + 1):
        prompt = (
            await session.execute(
                insert(Prompt)
                .values(
                    question=f"{name} Q{order}",
                    question_type=QuestionTypeEnum.TEXT,
                    answer=f"{name} A{order}",
                    answer_type=AnswerTypeEnum.TEXT,
                    category_id=category.id,
                    order=order,
                )
                .returning(Prompt),
            )
        ).scalar_one()
        inserted_prompts.append(prompt)
    return _SeededCategory(id=category.id, name=category.name, prompts=inserted_prompts)


@pytest.fixture
async def seed_lobby(
    db_session: AsyncSession,
    redis_client: FakeAsyncRedis,
) -> Callable[..., Awaitable[SeededLobby]]:
    """
    Factory: insert host + N players + categories + prompts directly via
    SQLAlchemy and seed ``GameLobbyState`` into Redis. Skips REST entirely so
    socket tests run against a known starting state.
    """

    async def _make(
        *,
        lobby_state: LobbyStateEnum = LobbyStateEnum.WAITING_START,
        player_count: int = 2,
        category_count: int = 1,
        prompts_per_category: int = 2,
        host_username: str = "host",
        player_username_prefix: str = "player",
    ) -> SeededLobby:
        host = await _insert_user(db_session, host_username)
        players = [
            await _insert_user(db_session, f"{player_username_prefix}{i}")
            for i in range(1, player_count + 1)
        ]
        lobby = await _insert_lobby(db_session, owner_id=host.id, state=lobby_state)
        categories: list[_SeededCategory] = []
        for i in range(1, category_count + 1):
            category = await _insert_category(
                db_session,
                owner_id=host.id,
                name=f"Category {i}",
                prompts=prompts_per_category,
            )
            categories.append(category)
            await db_session.execute(
                insert(LobbyPromptCategory).values(
                    lobby_id=lobby.id,
                    prompt_category_id=category.id,
                ),
            )
        await db_session.commit()

        category_states: list[GameCategoryState] = []
        prompt_ids: list[int] = []
        for category in categories:
            ordered = sorted(category.prompts, key=lambda p: p.order or 0)
            category_states.append(
                GameCategoryState(
                    category_id=category.id,
                    name=category.name,
                    prompts=[
                        GamePromptState(
                            prompt_id=prompt.id,
                            question=prompt.question,
                            answer=prompt.answer,
                            order=prompt.order or 0,
                        )
                        for prompt in ordered
                    ],
                ),
            )
            prompt_ids.extend(prompt.id for prompt in ordered)
        state = GameLobbyState(
            lobby_id=lobby.id,
            host=GameHostState(user_id=host.id, username=host.username),
            categories=category_states,
        )
        await GameStateRepo(redis_client).save_state(state)
        return SeededLobby(
            lobby_id=lobby.id,
            host=host,
            players=players,
            state=state,
            category_ids=[c.id for c in categories],
            prompt_ids=prompt_ids,
        )

    return _make


@dataclass(slots=True)
class SocketClient:
    client: socketio.AsyncClient
    events: dict[str, asyncio.Queue]

    async def expect(self, event: str, timeout: float = 2.0) -> dict:
        queue = self.events.setdefault(event, asyncio.Queue())
        return await asyncio.wait_for(queue.get(), timeout=timeout)


@pytest.fixture
async def connect_socket(
    socket_server_url: str,
    socket_session_overrides: None,
    make_socket_client: Callable[[], socketio.AsyncClient],
) -> Callable[..., Awaitable[SocketClient]]:
    async def _connect(lobby_id: int, token: str) -> SocketClient:
        client = make_socket_client()
        events: dict[str, asyncio.Queue] = {
            "state_changed": asyncio.Queue(),
            "error": asyncio.Queue(),
        }

        @client.on("state_changed", namespace=f"/lobbies/{lobby_id}")
        async def _on_state_changed(data: dict) -> None:
            await events["state_changed"].put(data)

        @client.on("error", namespace=f"/lobbies/{lobby_id}")
        async def _on_error(data: dict) -> None:
            await events["error"].put(data)

        await client.connect(
            f"{socket_server_url}?token={token}",
            socketio_path="ws",
            namespaces=[f"/lobbies/{lobby_id}"],
            wait_timeout=2,
        )
        return SocketClient(client=client, events=events)

    return _connect
