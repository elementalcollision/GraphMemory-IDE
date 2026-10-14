#!/usr/bin/env python3
"""Initialise the PostgreSQL test database schema.

Part of the Phase 9 test service-orchestration layer: run AFTER
`docker compose -f docker/docker-compose.test.yml up -d` so that
schema-dependent integration tests (which expect the full app schema,
e.g. "at least 8 tables") find an initialised database.

Usage:
    python scripts/init_test_db.py                 # uses TEST_DATABASE_URL or the default
    TEST_DATABASE_URL=postgresql+asyncpg://... python scripts/init_test_db.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Make the repo root importable when invoked as `python scripts/init_test_db.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/graphmemory_test",
)


async def main() -> int:
    from sqlalchemy.ext.asyncio import create_async_engine
    from server.database_models import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(
                text("SELECT count(*) FROM information_schema.tables "
                     "WHERE table_schema = 'public'")
            )
            count = result.scalar()
        print(f"OK: schema created — {count} tables in {TEST_DATABASE_URL}")
        return 0
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
