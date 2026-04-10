"""Async Alembic environment.

Reads the database URL from the application settings (never from alembic.ini)
so migrations always target the same database as the running app. Importing
``gisst.db.models`` registers every table on ``Base.metadata``, which Alembic
uses both for ``--autogenerate`` diffs and as the source of truth.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import the metadata + all models so every table is registered on Base.
from gisst.config import get_settings
from gisst.db import models as _models  # noqa: F401  (import side effect: table registration)
from gisst.db.base import Base

# Alembic Config object, providing access to values within alembic.ini.
config = context.config

# Resolve the runtime URL from settings and inject it into the Alembic config.
_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.database.url)

# Wire up Python logging from the ini file if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata that autogenerate compares against.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DBAPI connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure the context against a live (sync-facing) connection and run."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # batch mode is required for SQLite ALTER support.
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within a sync-bridged conn."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode via the async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
