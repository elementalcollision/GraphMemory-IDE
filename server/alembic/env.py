"""
Alembic environment configuration for GraphMemory-IDE.
Configured for async SQLAlchemy with environment-aware database connections.
"""

import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import os
import sys
from typing import Any, Dict

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our models and configuration
try:
    from server.database_models import Base
    from server.core.config import get_settings
    HAS_MODELS = True
except ImportError:
    # Fallback for standalone alembic usage without the full application
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
    HAS_MODELS = False
    
    def get_settings():
        class MockDatabase:
            DATABASE_URL = "postgresql+asyncpg://graphmemory:graphmemory@localhost:5432/graphmemory_dev"
        
        class MockSettings:
            database = MockDatabase()
        
        return MockSettings()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get database URL from settings with environment awareness"""
    if HAS_MODELS:
        settings = get_settings()
        db_url = settings.database.DATABASE_URL
    else:
        # Fallback URL from alembic.ini
        db_url = config.get_main_option("sqlalchemy.url") or "postgresql+asyncpg://graphmemory:graphmemory@localhost:5432/graphmemory_dev"
    
    # Ensure async URL format
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not db_url.startswith("postgresql+asyncpg://"):
        # Default fallback
        db_url = "postgresql+asyncpg://graphmemory:graphmemory@localhost:5432/graphmemory_dev"
    
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        render_as_batch=True,  # For SQLite compatibility during development
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    # Get configuration section safely
    ini_section = config.get_section(config.config_ini_section)
    configuration: Dict[str, Any] = dict(ini_section) if ini_section else {}
    
    # Override database URL with our settings-aware URL
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
