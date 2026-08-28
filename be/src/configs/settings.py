import secrets
from functools import cached_property
from typing import Literal

import sqlalchemy
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

    # Application state
    environment: AppEnvironmentEnum = AppEnvironmentEnum.LOCAL
    name: str = "Jeopardy Back-end"
    version: str = get_version()
    secret_key: str | bytes = secrets.token_bytes(32)

    # Uvicorn
    host: str = "0.0.0.0"
    port: int = 8000
    workers_count: int = 1
    reload: bool = True

    # Authentication
    openapi_schema_user: str = "user"
    openapi_schema_password: str = "password"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS
    allowed_hosts: list[str] = ["*"]

    # Database
    db_apply_migrations: bool = False
    db_driver: str = "sqlite+aiosqlite"
    db_sync_driver: str = "sqlite"
    db_name: str = "jpdy.db"
    db_echo: bool = False
    db_echo_pool: bool = False
    db_expire_on_commit: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    @cached_property
    def db_url(self) -> sqlalchemy.URL:
        return sqlalchemy.URL.create(
            drivername=self.db_driver,
            database=self.db_name,
        )

    @cached_property
    def db_sync_url(self) -> sqlalchemy.URL:
        return sqlalchemy.URL.create(
            drivername=self.db_sync_driver,
            database=self.db_name,
        )

    @cached_property
    def log_level(self) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        return "DEBUG" if self.environment is AppEnvironmentEnum.LOCAL else "INFO"

    @cached_property
    def log_verbosity(self) -> Literal["standard", "verbose"]:
        return "verbose" if self.environment is AppEnvironmentEnum.LOCAL else "standard"


settings = Settings()
