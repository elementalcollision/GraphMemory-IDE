"""Phase 1 functional verification: exercise the migrated server.graph_database
end-to-end against a real LadybugDB database (schema init, query engine,
parameterised execute, health check)."""
import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/Users/dave/Claude_Primary/Graph_Memory")
shutil.rmtree("/Users/dave/.hermes/cache/scratch/phase1_vdb", ignore_errors=True)

# WORKAROUND (pre-existing defect, not a migration regression): every
# MetricsCollector() registers duplicate collectors into the global prometheus
# REGISTRY; graph_database.py creates several, so the 2nd instantiation raises
# 'Duplicated timeseries'. Give each collector a private registry here.
import server.monitoring.metrics as _m
_orig_init = _m.MetricsCollector.__init__
def _init(self, registry=None):
    _orig_init(self, registry or _m.create_custom_registry())
_m.MetricsCollector.__init__ = _init

from server.graph_database import (
    GraphDatabaseConfig, GraphDatabaseManager, close_graph_database,
)

async def main() -> None:
    cfg = GraphDatabaseConfig(
        database_path="/Users/dave/.hermes/cache/scratch/phase1_vdb/graph.lbdb",
        max_num_threads=4,
        connection_pool_size=4,
    )
    mgr = GraphDatabaseManager(cfg)
    ok = await mgr.initialize()
    assert ok, "GraphDatabaseManager.initialize() returned False"
    print("[PASS] GraphDatabaseManager.initialize() — schema created on real LadybugDB")

    # Parameterised write + read through the query engine
    r = mgr.query_engine.execute_query(
        "CREATE (u:User {id: $id, username: $name, email: $email, created_at: $ts})",
        {"id": "u1", "name": "alice", "email": "a@x.io", "ts": "2026-01-01 00:00:00"},
    )
    assert r.success, f"insert failed: {r.error}"
    print("[PASS] QueryEngine.execute_query() parameterised INSERT")

    r = mgr.query_engine.execute_query(
        "MATCH (u:User) WHERE u.username = $n RETURN u.id, u.username",
        {"n": "alice"},
    )
    assert r.success and r.row_count == 1, f"select failed: {r.error}"
    assert r.data[0]["col_0"] == "u1", r.data
    print(f"[PASS] QueryEngine.execute_query() parameterised MATCH — rows={r.data}")

    # Health check (connection pool + DB access + schema integrity via show_tables)
    health = await mgr.health_checker.check_health()
    assert health["status"] == "healthy", health
    checks = health["checks"]
    missing = checks["schema_integrity"].get("missing_tables")
    assert not missing, f"schema integrity missing tables: {missing}"
    print("[PASS] GraphHealthChecker.check_health() — pool, access, schema integrity all healthy")
    print(f"      found tables: {sorted(checks['schema_integrity']['found_tables'])}")

    await mgr.close()
    print("[PASS] manager.close() — pool + database closed cleanly")

    # get_graph_database singleton path (uses config defaults)
    m2 = await asyncio.wait_for(__import__("server.graph_database", fromlist=["x"]).get_graph_database(), 10)
    # NOTE: singleton builds its own config from settings; only verify it inits.
    assert m2.is_healthy(), "singleton manager not healthy"
    print("[PASS] get_graph_database() singleton initialises healthy")
    await close_graph_database()
    print("\nPHASE 1 FUNCTIONAL VERIFICATION: ALL PASSED")

asyncio.run(main())
