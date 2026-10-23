from datetime import date, datetime

from pydantic import Field

from enums.admin import HealthStatusEnum
from enums.prompt import PromptCategoryKindEnum
from enums.user import AdminUserSortEnum, UserRole
from schemas.base import BaseSchema
from schemas.pagination import PaginatedResponseSchema, PaginationSchema


class AdminUserFilterSchema(PaginationSchema):
    size: int = Field(default=20, gt=0, le=100)
    role: UserRole | None = None
    username: str | None = Field(default=None, min_length=1, max_length=20)
    created_from: date | None = None
    created_to: date | None = Field(default=None, description="Inclusive.")
    sort: AdminUserSortEnum | None = Field(default=None, description="Unsorted is by id.")


class AdminUserListItemSchema(BaseSchema):
    id: int
    username: str
    role: UserRole
    created_at: datetime
    lobbies_played: int
    lobbies_hosted: int


class PaginatedAdminUserSchema(PaginatedResponseSchema[AdminUserListItemSchema]):
    pass


class GameStatsSchema(BaseSchema):
    active_lobbies: int
    active_players: int
    completed_lobbies: int


class CategoryStatsFilterSchema(PaginationSchema):
    size: int = Field(default=20, gt=0, le=100)


class CategoryStatsItemSchema(BaseSchema):
    id: int
    name: str
    kind: PromptCategoryKindEnum
    lobbies_played: int


class PaginatedCategoryStatsSchema(PaginatedResponseSchema[CategoryStatsItemSchema]):
    pass


class ProbeSchema(BaseSchema):
    status: HealthStatusEnum
    error: str | None = None


class RedisServerSchema(ProbeSchema):
    ping_ms: float | None = None
    used_memory: int | None = None
    maxmemory: int | None = None
    connected_clients: int | None = None
    ops_per_sec: int | None = None
    uptime_seconds: int | None = None
    evicted_keys: int | None = None
    rejected_connections: int | None = None
    game_state_keys: int | None = None


class DatabaseServerSchema(ProbeSchema):
    dialect: str | None = None
    ping_ms: float | None = None
    pool_size: int | None = None
    pool_checked_out: int | None = None
    pool_overflow: int | None = None
    user_count: int | None = None
    lobby_count: int | None = None
    category_count: int | None = None
    size_bytes: int | None = None
    active_connections: int | None = None


class BackendInstanceSchema(BaseSchema):
    id: str
    hostname: str
    version: str
    started_at: datetime
    rss_bytes: int


class BackendServerSchema(ProbeSchema):
    instances: list[BackendInstanceSchema] = Field(default_factory=list)
    connected_sockets: int | None = None
    live_games: int | None = None


class ServerStatusSchema(BaseSchema):
    status: HealthStatusEnum
    redis: RedisServerSchema
    database: DatabaseServerSchema
    backend: BackendServerSchema
