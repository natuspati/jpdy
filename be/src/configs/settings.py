import secrets
from functools import cached_property
from pathlib import Path
from typing import Literal

import sqlalchemy
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from enums import AppEnvironmentEnum
from utils.application_version import get_version


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BE_",
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
        env_parse_none_str="null",
    )

    environment: AppEnvironmentEnum = AppEnvironmentEnum.LOCAL
    name: str = "Jeopardy Back-end"
    version: str = get_version()
    secret_key: str | bytes = secrets.token_bytes(32)

    host: str = "0.0.0.0"
    port: int = 8000
    workers_count: int = 1
    reload: bool = True

    openapi_schema_user: str = "user"
    openapi_schema_password: str = "password"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    allowed_hosts: list[str] = ["*"]
    registration_code: str | None = Field(
        default=None,
        description="When set, registration requires this invite code.",
    )

    db_apply_migrations: bool = False
    db_driver: str = "sqlite+aiosqlite"
    db_sync_driver: str = "sqlite"
    db_host: str | None = None
    db_port: int | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_name: str = "jpdy.db"
    db_echo: bool = False
    db_echo_pool: bool = False
    db_expire_on_commit: bool = False

    redis_url: str = "redis://localhost:6379/0"
    socketio_redis_url: str | None = None
    socketio_redis_channel: str = "jpdy.socketio"

    media_root: Path = Field(
        default=Path("media"),
        description="Directory FastAPI uses to validate and write media files.",
    )
    media_url_prefix: str = "/media"

    @cached_property
    def db_url(self) -> sqlalchemy.URL:
        return sqlalchemy.URL.create(
            drivername=self.db_driver,
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @cached_property
    def db_sync_url(self) -> sqlalchemy.URL:
        return sqlalchemy.URL.create(
            drivername=self.db_sync_driver,
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @cached_property
    def log_level(self) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        return "DEBUG" if self.environment is AppEnvironmentEnum.LOCAL else "INFO"

    @cached_property
    def log_verbosity(self) -> Literal["standard", "verbose"]:
        return "verbose" if self.environment is AppEnvironmentEnum.LOCAL else "standard"


settings = Settings()
