"""Alembic environment configuration for skawr-auth migrations."""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from skawr_auth.models.base import get_base

# Ensure all models are imported so metadata is populated
import skawr_auth.models.user  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the AuthBase metadata for autogenerate support
Base = get_base()
target_metadata = Base.metadata


def _get_database_url() -> str:
    """Get the database URL from environment or alembic.ini."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        url = config.get_main_option("sqlalchemy.url", "")
    # Convert async URLs to sync for Alembic
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=_get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = _get_database_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.begin() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
