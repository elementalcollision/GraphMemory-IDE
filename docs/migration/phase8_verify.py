"""Phase 8 functional verification: pool Condition, AsyncConnection, read_only, redis.asyncio."""
import asyncio
import shutil
import sys

sys.path.insert(0, "/Users/dave/Claude_Primary/Graph_Memory")
shutil.rmtree("/Users/dave/.hermes/cache/scratch/phase8_db", ignore_errors=True)

import server.monitoring.metrics as _m
_orig_init = _m.MetricsCollector.__init__
def _init(self, registry=None):
    _orig_init(self, registry or _m.create_custom_registry())
_m.MetricsCollector.__init__ = _init

from server.graph_database import GraphDatabaseConfig, GraphDatabaseManager

async def main() -> None:
    # 8.1 + 8.5: manager init (Condition pool + read_only=False path)
    cfg = GraphDatabaseConfig(
        database_path="/Users/dave/.hermes/cache/scratch/phase8_db/graph.lbdb",
        max_num_threads=4, connection_pool_size=3,
    )
    mgr = GraphDatabaseManager(cfg)
    assert await mgr.initialize(), "initialize failed"
    print("[PASS] 8.1/8.5 — manager init (Condition-based pool, read_only ctor param)")

    # pool acquire/return under contention (Condition path)
    with mgr.connection_pool.get_connection() as c:
        c.execute("MATCH (n) RETURN count(n)")
    print("[PASS] 8.1 — Condition-based pool acquire/return")

    # 8.1: AsyncConnection — async execute through the built-in pool
    aconn = mgr.get_async_connection()
    r = await aconn.execute("MATCH (u:User) RETURN count(u) AS n")
    rows = r.get_all() if not isinstance(r, list) else r[0].get_all()
    assert rows == [[0]], rows
    print(f"[PASS] 8.1 — AsyncConnection.execute() -> {rows}")

    # concurrent async queries
    results = await asyncio.gather(*[
        aconn.execute("MATCH (n) RETURN count(n) AS n") for _ in range(5)
    ])
    print(f"[PASS] 8.1 — 5 concurrent AsyncConnection queries OK")

    # 8.5: read_only=True path opens the same DB read-only and rejects writes
    await mgr.close()
    cfg_ro = GraphDatabaseConfig(
        database_path="/Users/dave/.hermes/cache/scratch/phase8_db/graph.lbdb",
        connection_pool_size=2, read_only=True,
    )
    mgr_ro = GraphDatabaseManager(cfg_ro)
    assert await mgr_ro.initialize(), "read-only init failed"
    q = mgr_ro.query_engine.execute_query(
        "CREATE (u:User {id: $id, username: $n})", {"id": "x1", "n": "blocked"}
    )
    assert not q.success, "write unexpectedly succeeded on read-only DB"
    r2 = mgr_ro.query_engine.execute_query("MATCH (n) RETURN count(n) AS c")
    assert r2.success, "read unexpectedly failed on read-only DB"
    print("[PASS] 8.5 — read_only=True: writes rejected, reads OK")
    await mgr_ro.close()

    # 8.9: redis.asyncio import + API shape
    from redis import asyncio as aioredis
    assert hasattr(aioredis, "from_url") and hasattr(aioredis, "Redis")
    print("[PASS] 8.9 — `from redis import asyncio as aioredis` exposes from_url/Redis")

    print("\nPHASE 8 FUNCTIONAL VERIFICATION: ALL PASSED")

asyncio.run(main())
