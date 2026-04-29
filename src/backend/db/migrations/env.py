"""Alembic migration environment.

Supports both offline (SQL script generation) and online (async DB)
migration modes. Uses asyncpg via SQLAlchemy's async engine so that
the same database URL used at runtime is used for migrations.

Run migrations:
    cd /path/to/KyulAI
    alembic -c src/backend/alembic.ini upgrade head

Generate a new migration:
    alembic -c src/backend/alembic.ini revision --autogenerate -m "description"
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import Base + all models so metadata is populated for autogenerate.
from src.backend.db.base import Base
import src.backend.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    """Read DB URL from Settings, falling back to alembic.ini value."""
    try:
        from src.backend.config import get_settings
        return get_settings().database_url
    except Exception:
        url = config.get_main_option("sqlalchemy.url")
        if not url:
            raise RuntimeError(
                "No database URL found. Set DATABASE_URL env var or sqlalchemy.url in alembic.ini."
            )
        return url


def run_migrations_offline() -> None:
    """Generate SQL migration script without connecting to DB."""
    context.configure(
        url=_get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect to DB and run migrations using async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
