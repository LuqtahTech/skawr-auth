"""
Alembic environment configuration for skawr-auth.

Supports both async (asyncpg) and sync (psycopg2) PostgreSQL connections.
Consuming services should set SKAWR_AUTH_DATABASE_URL environment variable.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models metadata for autogenerate support
from skawr_auth.models.base import get_base

target_metadata = get_base().metadata

# Override sqlalchemy.url from environment variable if set
database_url = os.getenv(
    "SKAWR_AUTH_DATABASE_URL",
    os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url")),
)

# Ensure we're using asyncpg driver for async operations
if database_url and "postgresql://" in database_url and "+asyncpg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

config.set_main_option("sqlalchemy.url", database_url or "")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This generates SQL without connecting to the database.
    Useful for generating migration scripts for review.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
