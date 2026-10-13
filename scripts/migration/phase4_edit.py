#!/usr/bin/env python3
"""Phase 4 batch edit: Kuzu -> LadybugDB across tests/."""
import re
import sys
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")

SWEEPS = [
    ("TEST_KUZU_DB_PATH", "TEST_LADYBUG_DB_PATH"),
    ("_initialize_kuzu_test_schema", "_initialize_ladybug_test_schema"),
    ("check_kuzu_health", "check_ladybug_health"),
    ("KuzuAnalyticsEngine", "LadybugAnalyticsEngine"),
    ("KuzuTenantManager", "LadybugTenantManager"),
    ("KuzuQueryRequest", "LadybugQueryRequest"),
    ("KuzuQueryResult", "LadybugQueryResult"),
    ("KuzuQuery", "LadybugQuery"),
    ("KUZU_DB_PATH", "LADYBUG_DB_PATH"),
    ("KuzuDB", "LadybugDB"),
    ("kuzu.Database", "lb.Database"),
    ("kuzu.Connection", "lb.Connection"),
    ("kuzu_test", "ladybug_test"),
    ("kuzu_db", "ladybug_db"),
    ("kuzu_connection", "ladybug_connection"),
    ("kuzu_conn", "ladybug_conn"),
    ("kuzu_queries", "ladybug_queries"),
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
        for l in text.splitlines():
            if re.search(r"kuzu|Kuzu|KUZU", l):
                print("   leftover:", l.strip()[:100])
        print(f"ABORT: leftover kuzu refs in {path}")
        sys.exit(1)
    p.write_text(text)
    print(f"  OK  {path}")

# ---------------------------------------------------------------
# 1. tests/conftest.py — explicit path/ctor/cleanup fixes
#    LadybugDB: DB path is a FILE; the parent dir must exist.
# ---------------------------------------------------------------
apply("tests/conftest.py", specific=[
    ("""import kuzu
""",
     """import ladybug as lb
"""),
    ("""TEST_DATABASE_PATH = os.getenv("TEST_KUZU_DB_PATH", "./test_data")""",
     """# LadybugDB stores a single database FILE; only its parent dir must exist
TEST_DATABASE_PATH = os.getenv("TEST_LADYBUG_DB_PATH", "./test_data/ladybug_test.lbdb")"""),
    ("""    # Ensure test directory exists
    os.makedirs(TEST_DATABASE_PATH, exist_ok=True)
    
    # Create database
    db = kuzu.Database(TEST_DATABASE_PATH)""",
     """    # Ensure the parent directory of the database file exists
    os.makedirs(os.path.dirname(TEST_DATABASE_PATH) or ".", exist_ok=True)
    
    # Create database
    db = lb.Database(TEST_DATABASE_PATH)"""),
    ("""    # Cleanup - remove test database files
    db.close()
    import shutil
    if os.path.exists(TEST_DATABASE_PATH):
        shutil.rmtree(TEST_DATABASE_PATH, ignore_errors=True)""",
     """    # Cleanup - remove test database file and its directory
    db.close()
    import shutil
    from pathlib import Path as _P
    _P(TEST_DATABASE_PATH).unlink(missing_ok=True)
    test_dir = _P(TEST_DATABASE_PATH).parent
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)"""),
    ("""    conn = kuzu.Connection(kuzu_db)
    
    # Initialize basic schema for testing""",
     """    conn = lb.Connection(ladybug_db)
    conn.init_connection()
    
    # Initialize basic schema for testing"""),
])

# ---------------------------------------------------------------
# 2. tests/fixtures/database.py — explicit path/cleanup fixes
# ---------------------------------------------------------------
apply("tests/fixtures/database.py", specific=[
    ("""import kuzu
""",
     """import ladybug as lb
"""),
    ("""    db_path = temp_dir / "test_kuzu_db"
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path""",
     """    # LadybugDB: single database file inside the existing temp dir
    db_path = temp_dir / "test_ladybug_db.lbdb"
    return db_path"""),
    ("""        database = kuzu.Database(
            str(kuzu_test_db_path),
            buffer_pool_size=buffer_size
        )""",
     """        database = lb.Database(
            str(ladybug_test_db_path),
            buffer_pool_size=buffer_size
        )"""),
    ("""        # Remove database files
        if kuzu_test_db_path.exists():
            shutil.rmtree(kuzu_test_db_path, ignore_errors=True)""",
     """        # Remove database files
        if ladybug_test_db_path.exists():
            ladybug_test_db_path.unlink(missing_ok=True)"""),
    ("""        connection = kuzu.Connection(kuzu_test_database)""",
     """        connection = lb.Connection(ladybug_test_database)
        connection.init_connection()"""),
])

# ---------------------------------------------------------------
# 3. Everything else — sweeps only
# ---------------------------------------------------------------
for f in [
    "tests/fixtures/advanced_database_fixtures.py",
    "tests/fixtures/real_services.py",
    "tests/fixtures/application.py",
    "tests/integration/test_database_integration.py",
    "tests/integration/test_realtime_sse_integration.py",
    "tests/integration/test_realtime_performance_monitoring.py",
    "tests/integration/test_end_to_end_dashboard_integration.py",
    "tests/integration/test_cross_database_transactions.py",
    "tests/integration/test_basic_integration.py",
    "tests/integration/test_database_performance.py",
    "tests/utils/cleanup.py",
    "tests/performance/test_production_load.py",
    "tests/test_main.py",
    "tests/functional/test_phase1_async_infrastructure.py",
    "tests/integration_test.py",
    "tests/analytics/test_integration_suite.py",
]:
    apply(f)

print("\nPhase 4 edits complete.")
