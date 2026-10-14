#!/usr/bin/env python3
"""Phase 1 resume: remaining files after phase1_edit.py partial run."""
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")

SWEEPS = [
    ("KuzuAnalyticsEngine", "LadybugAnalyticsEngine"),
    ("TestKuzuAnalyticsEngine", "TestLadybugAnalyticsEngine"),
    ("KuzuTenantManager", "LadybugTenantManager"),
    ("KuzuQueryRequest", "LadybugQueryRequest"),
    ("KuzuQueryResult", "LadybugQueryResult"),
    ("KuzuBackupType", "LadybugBackupType"),
    ("KuzuBackupStatus", "LadybugBackupStatus"),
    ("KuzuBackupMetadata", "LadybugBackupMetadata"),
    ("KuzuBackupManager", "LadybugBackupManager"),
    ("KuzuQuery", "LadybugQuery"),
    ("KUZU_DATABASE", "LADYBUG_DATABASE"),
    ("KUZU_DB_PATH", "LADYBUG_DB_PATH"),
    ("KUZU_READ_ONLY", "LADYBUG_READ_ONLY"),
    ("Kuzu GraphDB", "LadybugDB"),
    ("KuzuDB", "LadybugDB"),
    ("kuzu.Database", "lb.Database"),
    ("kuzu.Connection", "lb.Connection"),
    ("kuzu_analytics", "ladybug_analytics"),
    ("kuzu_backup", "ladybug_backup"),
    ("kuzu_tenant_manager", "ladybug_tenant_manager"),
    ("kuzu_queries", "ladybug_queries"),
    ("idx_kuzu", "idx_ladybug"),
    ("ck_kuzu", "ck_ladybug"),
    ("collect_kuzu_metrics", "collect_ladybug_metrics"),
    ("_check_kuzu_health", "_check_ladybug_health"),
    ("_transform_kuzu_query", "_transform_ladybug_query"),
    ("_execute_kuzu_query", "_execute_ladybug_query"),
    ("setup_kuzu_manager", "setup_ladybug_manager"),
    ("test_kuzu_performance_monitoring", "test_ladybug_performance_monitoring"),
    ("kuzu_fs_backup", "ladybug_fs_backup"),
    ("kuzu_export", "ladybug_export"),
    ("kuzu_query_latency", "ladybug_query_latency"),
    ("kuzu_database", "ladybug_database"),
    ("kuzu_manager", "ladybug_manager"),
    ("kuzu_connection", "ladybug_connection"),
    ("kuzu_conn", "ladybug_conn"),
    ("kuzu_db", "ladybug_db"),
    ("kuzu_result", "ladybug_result"),
    ("existing_kuzu", "existing_ladybug"),
    ("kuzu_to_create", "ladybug_to_create"),
    ("kuzu_metrics", "ladybug_metrics"),
    ("kuzu_time", "ladybug_time"),
    ("kuzu_backup", "ladybug_backup"),
    ("kuzu_test", "ladybug_test"),
    ("kuzu_path", "ladybug_path"),
    ("Kuzu", "LadybugDB"),
    ("kuzu", "ladybug"),
    ("KUZU", "LADYBUG"),
]

def apply(path, specific=()):
    p = ROOT / path
    text = p.read_text()
    for old, new in specific:
        if old not in text:
            print(f"ABORT: pattern not found in {path}:\n  {old[:120]!r}")
            sys.exit(1)
        text = text.replace(old, new)
    for old, new in SWEEPS:
        text = text.replace(old, new)
    if re.search(r"kuzu|Kuzu|KUZU", text):
        leftovers = [l for l in text.splitlines() if re.search(r"kuzu|Kuzu|KUZU", l)]
        print(f"ABORT: leftover kuzu refs in {path}:")
        for l in leftovers[:5]:
            print("   ", l.strip()[:100])
        sys.exit(1)
    p.write_text(text)
    print(f"  OK  {path}")

for f in [
    "server/dashboard/test_analytics_client.py",
    "server/collaboration/test_tenant_isolation.py",
    "server/collaboration/test_rbac_integration.py",
]:
    apply(f)

apply("server/core/config.py", [
    ("""    # Kuzu Graph Database
    KUZU_DB_PATH: str = "./data/kuzu"
    KUZU_READ_ONLY: bool = False""",
     """    # LadybugDB Graph Database (Kuzu successor)
    LADYBUG_DB_PATH: str = "./data/ladybug.lbdb"
    LADYBUG_READ_ONLY: bool = False"""),
])

for old, new in [
    ("server/analytics/kuzu_analytics.py", "server/analytics/ladybug_analytics.py"),
    ("server/backup/kuzu_backup.py", "server/backup/ladybug_backup.py"),
    ("server/collaboration/kuzu_tenant_manager.py", "server/collaboration/ladybug_tenant_manager.py"),
]:
    r = subprocess.run(["git", "mv", old, new], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ABORT: git mv {old} -> {new} failed: {r.stderr}")
        sys.exit(1)
    print(f"  OK  renamed {old} -> {new}")

print("\nPhase 1 resume complete.")
