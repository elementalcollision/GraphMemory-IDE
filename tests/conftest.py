# tests/conftest.py
"""
Production-Ready Async Testing Infrastructure for GraphMemory-IDE
================================================================

Based on industry best practices from:
- TestDriven.io: Function-level scoping, async testing patterns
- FastAPI Official: AsyncClient with HTTPX integration  
- Pytest-asyncio: Modern async testing patterns
- LoadForge: Performance testing optimization

Features:
- Function-level fixture scoping for maximum test isolation
- Real database testing with LadybugDB integration
- DigitalOcean cloud testing support
- Performance-optimized async patterns
- Realistic data factories for testing
"""

import asyncio
import os
import warnings
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import ladybug as lb

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

# Suppress warnings for cleaner test output
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Import application components
from server.main import app
from server.analytics.models import (
    AnalyticsRequest, AnalyticsResponse, AnalyticsType,
    CentralityRequest, CommunityRequest, ClusteringRequest,
    PathAnalysisRequest, GraphMetrics, NodeMetrics
)

# Test database configuration
# LadybugDB stores a single database FILE; only its parent dir must exist
TEST_DATABASE_PATH = os.getenv("TEST_LADYBUG_DB_PATH", "./test_data/ladybug_test.lbdb")
CLOUD_TEST_ENABLED = os.getenv("CLOUD_TEST_ENABLED", "false").lower() == "true"
DIGITALOCEAN_TEST_ENDPOINT = os.getenv("DIGITALOCEAN_TEST_ENDPOINT")


@pytest_asyncio.fixture(scope="function")
async def ladybug_db() -> AsyncGenerator[lb.Database, None]:
    """
    Create LadybugDB database instance with function-level scoping.
    
    Based on best practices for test isolation.
    Each test gets a fresh database that's cleaned up after.
    """
    # Ensure the parent directory of the database file exists
    os.makedirs(os.path.dirname(TEST_DATABASE_PATH) or ".", exist_ok=True)
    
    # Create database
    db = lb.Database(TEST_DATABASE_PATH)
    
    yield db
    
    # Cleanup - remove test database file and its directory
    db.close()
    import shutil
    from pathlib import Path as _P
    _P(TEST_DATABASE_PATH).unlink(missing_ok=True)
    test_dir = _P(TEST_DATABASE_PATH).parent
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest_asyncio.fixture(scope="function")
async def ladybug_connection(ladybug_db: lb.Database) -> AsyncGenerator[lb.Connection, None]:
    """
    Provide LadybugDB database connection.
    
    Creates connection to test database with proper cleanup.
    """
    conn = lb.Connection(ladybug_db)
    conn.init_connection()
    
    # Initialize basic schema for testing
    try:
        # Create basic node tables for testing
        conn.execute("CREATE NODE TABLE IF NOT EXISTS MemoryNode(id STRING, type STRING, content STRING, metadata STRING, PRIMARY KEY(id))")
        conn.execute("CREATE NODE TABLE IF NOT EXISTS Concept(id STRING, name STRING, description STRING, PRIMARY KEY(id))")
        
        # Create relationship tables
        conn.execute("CREATE REL TABLE IF NOT EXISTS RELATES(FROM MemoryNode TO MemoryNode, strength DOUBLE, relation_type STRING)")
        conn.execute("CREATE REL TABLE IF NOT EXISTS IMPLEMENTS(FROM MemoryNode TO Concept)")
        
    except Exception as e:
        # Schema might already exist, continue
        pass
    
    yield conn
    
    conn.close()


@pytest_asyncio.fixture(scope="function") 
async def async_client(ladybug_connection: lb.Connection) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide FastAPI test client with database override.
    
    Based on FastAPI official docs and TestDriven.io patterns.
    Uses HTTPX AsyncClient for authentic async testing.
    """
    # Phase 9: override the attribute handlers actually use — this
    # previously set a non-existent 'ladybug_connection' attr (no-op) and
    # used base_url 'testserver', which the trusted-host middleware rejects.
    original_conn = getattr(app.state, 'ladybug_conn', None)
    app.state.ladybug_conn = ladybug_connection
    
    # Create async client with ASGI transport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost"
    ) as client:
        yield client
    
    app.state.ladybug_conn = original_conn
    
    # Restore original connection
    if original_conn:
        app.state.ladybug_connection = original_conn


@pytest_asyncio.fixture(scope="function")
async def sample_memory_data(ladybug_connection: lb.Connection) -> Dict[str, Any]:
    """
    Create sample memory data for testing.
    
    Provides realistic test data based on GraphMemory-IDE patterns.
    """
    # Insert sample nodes
    sample_nodes = [
        {
            "id": "node_001",
            "type": "function", 
            "content": "async def process_query(query: str) -> QueryResult:",
            "metadata": '{"file_path": "src/query_processor.py", "complexity": "medium"}'
        },
        {
            "id": "node_002",
            "type": "class",
            "content": "class AnalyticsEngine:",
            "metadata": '{"file_path": "src/analytics/engine.py", "complexity": "high"}'
        },
        {
            "id": "node_003", 
            "type": "concept",
            "content": "Graph traversal algorithm for memory relationships",
            "metadata": '{"domain": "algorithms", "difficulty": "advanced"}'
        }
    ]
    
    # Phase 9: extend to 10 nodes — consumers (e.g. phase1
    # test_sample_data_creation) assert len(nodes) >= 10 but only 3 were
    # ever provided.
    for i in range(4, 11):
        sample_nodes.append({
            "id": f"node_{i:03d}",
            "type": ["function", "class", "concept", "file"][i % 4],
            "content": f"Sample memory node {i} for testing",
            "metadata": f'{{"test_id": {i}, "synthetic": true}}'
        })
    
    # Insert nodes
    for node in sample_nodes:
        ladybug_connection.execute(
            "CREATE (n:MemoryNode {id: $id, type: $type, content: $content, metadata: $metadata})",
            node
        )
    
    # Insert sample relationships
    relationships = [
        {
            "from_id": "node_001",
            "to_id": "node_002", 
            "strength": 0.8,
            "relation_type": "uses"
        },
        {
            "from_id": "node_002",
            "to_id": "node_003",
            "strength": 0.9,
            "relation_type": "implements"
        }
    ]
    
    for rel in relationships:
        ladybug_connection.execute(
            "MATCH (a:MemoryNode {id: $from_id}), (b:MemoryNode {id: $to_id}) CREATE (a)-[:RELATES {strength: $strength, relation_type: $relation_type}]->(b)",
            rel
        )
    
    return {
        "nodes": sample_nodes,
        "relationships": relationships
    }


# Cloud testing fixtures for DigitalOcean integration
@pytest_asyncio.fixture(scope="session")
async def cloud_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide client for DigitalOcean cloud testing.
    
    Only available when CLOUD_TEST_ENABLED=true and endpoint is configured.
    Allows testing against real cloud infrastructure.
    """
    if not CLOUD_TEST_ENABLED or not DIGITALOCEAN_TEST_ENDPOINT:
        pytest.skip("Cloud testing not enabled or endpoint not configured")
    
    # Ensure endpoint is a proper URL string
    endpoint = str(DIGITALOCEAN_TEST_ENDPOINT)
    
    async with AsyncClient(
        base_url=endpoint,
        timeout=30.0  # Extended timeout for cloud requests
    ) as client:
        yield client


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for session.
    
    Required for session-scoped async fixtures.
    Based on pytest-asyncio best practices.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Performance testing utilities
class PerformanceTracker:
    """Track performance metrics during testing."""
    
    def __init__(self) -> None:
        self.response_times = []
        self.memory_usage = []
        self.errors = []
    
    def record_response_time(self, time_ms: float) -> None:
        self.response_times.append(time_ms)
    
    def record_memory_usage(self, usage_mb: float) -> None:
        self.memory_usage.append(usage_mb)
    
    def record_error(self, error: str) -> None:
        self.errors.append(error)
    
    @property
    def avg_response_time(self) -> float:
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0
    
    @property
    def error_rate(self) -> float:
        total_requests = len(self.response_times) + len(self.errors)
        return len(self.errors) / total_requests if total_requests > 0 else 0


@pytest_asyncio.fixture(scope="function")
async def performance_tracker() -> PerformanceTracker:
    """Provide performance tracking for tests."""
    return PerformanceTracker()


# Database health check utilities  
async def check_ladybug_health(connection: lb.Connection) -> bool:
    """Check if LadybugDB database is accessible and responsive."""
    try:
        result = connection.execute("RETURN 1 AS test")
        # LadybugDB returns a QueryResult object, check if we got results
        return result is not None and len(list(result)) > 0
    except Exception:
        return False


@pytest_asyncio.fixture(scope="function", autouse=True)
async def ensure_database_health(ladybug_connection: lb.Connection) -> None:
    """Ensure database is healthy before each test."""
    if not await check_ladybug_health(ladybug_connection):
        pytest.fail("LadybugDB database health check failed")


# Realistic data factories based on research patterns
class ProjectDataFactory:
    """Factory for creating realistic project test data."""
    
    @staticmethod
    def create_realistic_dataset(
        connection: lb.Connection,
        size: str = "small"
    ) -> Dict[str, Any]:
        """
        Create realistic project dataset for testing.
        
        Args:
            connection: LadybugDB database connection
            size: Dataset size - "small", "medium", "large", "enterprise"
        
        Returns:
            Dictionary containing created data references
        """
        size_configs = {
            "small": {"nodes": 10, "relations": 15},
            "medium": {"nodes": 100, "relations": 150}, 
            "large": {"nodes": 1000, "relations": 1500},
            "enterprise": {"nodes": 10000, "relations": 15000}
        }
        
        config = size_configs.get(size, size_configs["small"])
        
        # Create nodes with realistic content.
        # Phase 9: ids are unique per call — creating two datasets (e.g.
        # "small" then "medium") in one function-scoped DB previously
        # collided on the PRIMARY KEY.
        import uuid as _uuid
        id_prefix = f"test_node_{_uuid.uuid4().hex[:6]}"
        created_nodes = []
        for i in range(config["nodes"]):
            node_data = {
                "id": f"{id_prefix}_{i:06d}",
                "type": ["function", "class", "concept", "file"][i % 4],
                "content": f"Test content for node {i}",
                "metadata": f'{{"test_id": {i}, "batch": "{size}", "synthetic": true}}'
            }
            
            connection.execute(
                "CREATE (n:MemoryNode {id: $id, type: $type, content: $content, metadata: $metadata})",
                node_data
            )
            created_nodes.append(node_data)
        
        # Create relations
        created_relations = []
        for i in range(config["relations"]):
            source_idx = i % len(created_nodes)
            target_idx = (i + 1) % len(created_nodes)
            
            relation_data = {
                "from_id": created_nodes[source_idx]["id"],
                "to_id": created_nodes[target_idx]["id"],
                "strength": 0.5 + (i % 5) * 0.1,
                "relation_type": ["uses", "implements", "contains", "extends"][i % 4]
            }
            
            connection.execute(
                "MATCH (a:MemoryNode {id: $from_id}), (b:MemoryNode {id: $to_id}) CREATE (a)-[:RELATES {strength: $strength, relation_type: $relation_type}]->(b)",
                relation_data
            )
            created_relations.append(relation_data)
        
        return {
            "nodes": created_nodes,
            "relations": created_relations,
            "config": config
        }


@pytest_asyncio.fixture(scope="function")
async def project_data_factory() -> ProjectDataFactory:
    """Provide project data factory for tests."""
    return ProjectDataFactory()


# Memory usage monitoring
def get_memory_usage() -> float:
    """Get current memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        # Fallback if psutil not available
        return 0.0


@pytest.fixture(autouse=True)
def monitor_memory_usage() -> None:
    """Monitor memory usage for each test."""
    initial_memory = get_memory_usage()
    yield
    final_memory = get_memory_usage()
    peak = max(initial_memory, final_memory)
    
    if peak > 100:  # 100MB threshold
        print(f"\n⚠️  High memory usage detected: {peak:.2f}MB peak") 

# ---------------------------------------------------------------------------
# Phase 9 fixtures: previously-missing test infrastructure (32 tests errored)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def http_client(ladybug_connection: lb.Connection) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTPX async client over the FastAPI app with the test LadybugDB connection.

    Requested by tests/integration/test_basic_integration.py since inception
    but never existed. Overrides `app.state.ladybug_conn` — the attribute the
    handlers actually use (the older `async_client` fixture overrode a
    non-existent `ladybug_connection` attribute, a no-op).
    """
    original_conn = getattr(app.state, "ladybug_conn", None)
    app.state.ladybug_conn = ladybug_connection

    # NOTE: base_url must be an allowed host — the trusted-host middleware
    # rejects the default "testserver" Host header with 400
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        yield client

    app.state.ladybug_conn = original_conn


@pytest.fixture(scope="session")
def docker_client():
    """Docker (OrbStack) client for container-security tests; skips if unavailable."""
    try:
        import docker
    except ImportError:
        pytest.skip("docker package not installed")
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:  # noqa: BLE001 - any daemon failure -> skip
        pytest.skip(f"Docker/OrbStack not reachable: {e}")


@pytest.fixture(scope="session")
def kestra_container(docker_client):
    """Locate the running kestra container; skips when the stack is not up."""
    try:
        containers = docker_client.containers.list(filters={"name": "kestra"})
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Cannot list containers: {e}")
    if not containers:
        pytest.skip("No running kestra container (start the compose stack first)")
    return containers[0]


@pytest.fixture
def performance_data() -> Dict[str, Any]:
    """1000-node dataset for insertion-performance tests (previously missing)."""
    return {
        "nodes": [
            {
                "id": f"perf_node_{i:06d}",
                "content": f"Performance test node {i}: " + "lorem ipsum graph memory " * 5,
                "timestamp": 1700000000 + i,
            }
            for i in range(1000)
        ]
    }


@pytest_asyncio.fixture(scope="function")
async def multi_database_setup(tmp_path):
    """
    Multi-database pool setup for performance/cross-database tests
    (previously missing — 9 tests errored on it).

    A real LadybugDB pool is always provided; redis/sqlite pools are
    best-effort (skipped with a warning when the services are unreachable).
    """
    from tests.fixtures.advanced_database_fixtures import DatabaseConnectionPoolManager
    from tests.integration.test_database_performance import PERFORMANCE_BENCHMARKS

    pool_manager = DatabaseConnectionPoolManager()
    ladybug_pool = await pool_manager.setup_ladybug_pool(min_size=2, max_size=5)

    for setup, name in (
        (pool_manager.setup_redis_cluster_pool, "redis"),
        (pool_manager.setup_sqlite_wal_pool, "sqlite"),
    ):
        try:
            await setup(pool_size=3)
        except Exception as e:  # noqa: BLE001 - optional backend
            print(f"multi_database_setup: {name} pool unavailable: {e}")

    yield {
        "pool_manager": pool_manager,
        "ladybug_pool": ladybug_pool,
        "performance_benchmarks": PERFORMANCE_BENCHMARKS,
    }

    # Best-effort cleanup of pool connections
    for pool in list(pool_manager.pools.values()):
        for conn_entry in pool.get("connections", []):
            try:
                conn_entry.get("connection") and conn_entry["connection"].close()
            except Exception:
                pass
            try:
                conn_entry.get("database") and conn_entry["database"].close()
            except Exception:
                pass


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Bearer JWT headers for authenticated endpoints (Phase 9: previously
    missing — requested by test_basic_integration.test_authentication_flow)."""
    try:
        from server.auth_jwt import create_access_token
        token = create_access_token({"sub": "test-user"})
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Cannot create JWT for tests: {e}")
