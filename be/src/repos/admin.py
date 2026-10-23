import json
import time

from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import distinct, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.pool import QueuePool

from configs.constants import INSTANCE_KEY_PREFIX
from enums.admin import HealthStatusEnum
from enums.lobby import LobbyStateEnum
from models.lobby import Lobby, LobbyPromptCategory
from models.prompt_category import PromptCategory
from models.user import User
from repos.game_state import GameStateRepo
from schemas.admin import (
    BackendInstanceSchema,
    BackendServerSchema,
    CategoryStatsFilterSchema,
    CategoryStatsItemSchema,
    DatabaseServerSchema,
    GameStatsSchema,
    PaginatedCategoryStatsSchema,
    RedisServerSchema,
)
from utils.model_validation import validate_model

_PLAYED_STATES = [LobbyStateEnum.IN_PROGRESS, LobbyStateEnum.COMPLETED]


def _describe(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:200]


class AdminRepo:
    """Admin stats and server probes; each probe reports its own failure instead of raising."""

    def __init__(self, session: AsyncSession, redis: Redis):
        self._session = session
        self._redis = redis

    async def _count_keys(self, pattern: str) -> int:
        return sum([1 async for _ in self._redis.scan_iter(match=pattern)])

    async def _count_lobbies(self, *states: LobbyStateEnum) -> int:
        query = select(func.count(Lobby.id)).where(Lobby.state.in_(states))
        return (await self._session.execute(query)).scalar_one()

    async def select_game_stats(self) -> GameStatsSchema:
        # SQL, not Redis: finished games linger in Redis for 24h
        active = await self._count_lobbies(LobbyStateEnum.WAITING_START, LobbyStateEnum.IN_PROGRESS)
        completed = await self._count_lobbies(LobbyStateEnum.COMPLETED)
        return GameStatsSchema(
            active_lobbies=active,
            active_players=await self._count_keys("game:*:connection:*"),
            completed_lobbies=completed,
        )

    async def select_category_stats(
        self,
        filters: CategoryStatsFilterSchema,
    ) -> PaginatedCategoryStatsSchema:
        played = func.count(distinct(Lobby.id))
        grouped = (
            select(
                PromptCategory.id.label("id"),
                PromptCategory.name.label("name"),
                PromptCategory.kind.label("kind"),
                played.label("lobbies_played"),
            )
            .join(LobbyPromptCategory, LobbyPromptCategory.prompt_category_id == PromptCategory.id)
            .join(Lobby, Lobby.id == LobbyPromptCategory.lobby_id)
            .where(Lobby.state.in_(_PLAYED_STATES))
            .group_by(PromptCategory.id)
        )
        total = (
            await self._session.execute(select(func.count()).select_from(grouped.subquery()))
        ).scalar_one()
        rows = (
            await self._session.execute(
                grouped.order_by(played.desc(), PromptCategory.id.asc())
                .limit(filters.limit)
                .offset(filters.offset),
            )
        ).all()
        return PaginatedCategoryStatsSchema(
            contents=validate_model(rows, CategoryStatsItemSchema),
            total=total,
            page=filters.page,
            size=filters.size,
        )

    async def probe_redis(self) -> RedisServerSchema:
        try:
            started = time.perf_counter()
            await self._redis.ping()
            ping_ms = (time.perf_counter() - started) * 1000
            info = await self._redis.info()
            return RedisServerSchema(
                status=HealthStatusEnum.OK,
                ping_ms=round(ping_ms, 2),
                used_memory=info.get("used_memory"),
                maxmemory=info.get("maxmemory"),
                connected_clients=info.get("connected_clients"),
                ops_per_sec=info.get("instantaneous_ops_per_sec"),
                uptime_seconds=info.get("uptime_in_seconds"),
                evicted_keys=info.get("evicted_keys"),
                rejected_connections=info.get("rejected_connections"),
                game_state_keys=len(await GameStateRepo(self._redis).scan_active_lobby_ids()),
            )
        except Exception as exc:
            return RedisServerSchema(status=HealthStatusEnum.DOWN, error=_describe(exc))

    async def probe_database(self) -> DatabaseServerSchema:
        bind = self._session.get_bind()
        dialect = bind.dialect.name
        try:
            started = time.perf_counter()
            await self._session.execute(select(1))
            ping_ms = (time.perf_counter() - started) * 1000
            result = DatabaseServerSchema(
                status=HealthStatusEnum.OK,
                dialect=dialect,
                ping_ms=round(ping_ms, 2),
                user_count=await self._count_rows(User.id),
                lobby_count=await self._count_rows(Lobby.id),
                category_count=await self._count_rows(PromptCategory.id),
            )
            pool = bind.pool
            if isinstance(pool, QueuePool):
                result.pool_size = pool.size()
                result.pool_checked_out = pool.checkedout()
                result.pool_overflow = max(pool.overflow(), 0)
            if dialect == "postgresql":
                result.size_bytes = (
                    await self._session.execute(
                        select(func.pg_database_size(func.current_database())),
                    )
                ).scalar_one()
                result.active_connections = (
                    await self._session.execute(
                        select(func.count()).select_from(table("pg_stat_activity")),
                    )
                ).scalar_one()
            return result
        except Exception as exc:
            return DatabaseServerSchema(
                status=HealthStatusEnum.DOWN,
                dialect=dialect,
                error=_describe(exc),
            )

    async def _count_rows(self, column: InstrumentedAttribute[int]) -> int:
        return (await self._session.execute(select(func.count(column)))).scalar_one()

    async def probe_backend(self) -> BackendServerSchema:
        try:
            keys = [key async for key in self._redis.scan_iter(match=f"{INSTANCE_KEY_PREFIX}*")]
            raw_values = await self._redis.mget(keys) if keys else []
            instances = []
            for raw in raw_values:
                if raw is None:  # expired between SCAN and MGET
                    continue
                try:
                    instances.append(BackendInstanceSchema.model_validate(json.loads(raw)))
                except ValueError, ValidationError:
                    continue
            instances.sort(key=lambda instance: (instance.started_at, instance.id))
            return BackendServerSchema(
                status=HealthStatusEnum.OK,
                instances=instances,
                connected_sockets=await self._count_keys("game:*:connection:*"),
                live_games=await self._count_lobbies(LobbyStateEnum.IN_PROGRESS),
            )
        except Exception as exc:
            return BackendServerSchema(status=HealthStatusEnum.DOWN, error=_describe(exc))
