"""Alembic async env for PostgreSQL + asyncpg."""

import asyncio
import sys
from pathlib import Path
from logging.config import fileConfig

# Add backend directory to Python path so imports work
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.infra.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_migrations_url = settings.database_url_migrations or settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in offline mode (emit SQL to stdout)."""
    context.configure(
        url=_migrations_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in online mode with async engine."""
    connectable = create_async_engine(
        _migrations_url,
        connect_args={"ssl": "require"},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

