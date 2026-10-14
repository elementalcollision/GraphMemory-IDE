"""
PostgreSQL and sample-data fixtures for database integration tests.

NOTE: this module was imported by tests/integration/test_database_integration.py
from the day that module was written but never existed, so the test module
always failed collection (pre-existing breakage, repaired during Phase 4 of
the Kuzu -> LadybugDB migration). The PostgreSQL fixtures SKIP when no server
is reachable so the remainder of the suite can still run.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/graphmemory_test",
)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """PostgreSQL URL used by the integration tests (TEST_DATABASE_URL env)."""
    return TEST_DATABASE_URL


@pytest_asyncio.fixture(scope="function")
async def postgres_engine(test_database_url: str):
    """Async SQLAlchemy engine; skips if PG is unreachable.

    Function-scoped to match the `asyncio_default_fixture_loop_scope =
    function` setting in pytest.ini (session-scoped async fixtures error
    under pytest-asyncio's function-scoped loop runner).
    """
    engine = create_async_engine(test_database_url, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:  # noqa: BLE001 - any connectivity failure -> skip
        await engine.dispose()
        pytest.skip(
            f"PostgreSQL not reachable at {test_database_url!r}: {e}"
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(postgres_engine) -> AsyncSession:
    """Function-scoped async session with rollback on teardown."""
    maker = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with maker() as session:
        yield session
        await session.rollback()

    # Tests commit their inserts; truncate all public tables between tests so
    # unique constraints (users.email etc.) do not collide across the suite
    from sqlalchemy import text as _text
    from server.database_models import Base
    table_list = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    async with postgres_engine.begin() as conn:
        await conn.execute(_text(
            f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"
        ))


@pytest.fixture
def sample_users() -> List[Dict[str, Any]]:
    """Sample user records matching server.database_models.User columns."""
    now = datetime.now(timezone.utc)
    return [
        {
            "username": f"testuser_{i}",
            "email": f"testuser_{i}@example.com",
            "full_name": f"Test User {i}",
            "hashed_password": "$2b$12$KIXQxJm/QmViJgQsT5FMeu/QGJaSBQF0yV9mLLqXWpG0Vq2pOy0Pm",
            "is_active": True,
            "is_superuser": False,
            "roles": ["user"],
            "preferences": {"theme": "light"},
            "last_login_at": now,
        }
        for i in range(5)
    ]


@pytest.fixture
def sample_telemetry_events() -> List[Dict[str, Any]]:
    """Sample telemetry-event records matching TelemetryEvent columns."""
    return [
        {
            "event_type": "page_view",
            "session_id": f"sess_{i}",
            "data": {"page": f"/page/{i}"},
            "event_metadata": {"source": "fixture"},
            "duration_ms": 100 + i,
        }
        for i in range(10)
    ]
