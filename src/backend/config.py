"""Application configuration.

Reads from environment variables and .env file. Instantiate via
``get_settings()`` everywhere — the result is cached so settings are
read only once per process.

Environment hierarchy (lowest → highest priority):
  defaults in this file → .env file → actual environment variables
"""

from enum import Enum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────────────────────
    env: Environment = Environment.DEV
    app_name: str = "KyulAI"
    version: str = "0.1.0"
    debug: bool = True
    log_level: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:8080"])

    # ── Database (PostgreSQL via asyncpg) ─────────────────────────────────────
    database_url: str = "postgresql+asyncpg://kyulai:kyulai@localhost:5432/kyulai_dev"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False  # Set True to log all SQL in dev

    # ── Celery / Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── MinIO / S3 object storage ─────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_datasets: str = "kyulai-datasets"
    minio_bucket_models: str = "kyulai-models"
    minio_bucket_results: str = "kyulai-results"
    minio_secure: bool = False

    # ── MLflow experiment tracking ────────────────────────────────────────────
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "kyulai-default"

    # ── Security (JWT auth — implement in Phase 2) ────────────────────────────
    secret_key: str = "dev-secret-key-CHANGE-IN-PRODUCTION"
    access_token_expire_minutes: int = 60

    @field_validator("debug", mode="before")
    @classmethod
    def _no_debug_in_prod(cls, v: bool, info) -> bool:
        # Validated after env is known — enforced in startup lifespan instead.
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
