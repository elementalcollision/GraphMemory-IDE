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
- Real database testing with Kuzu integration
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
import kuzu

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
TEST_DATABASE_PATH = os.getenv("TEST_KUZU_DB_PATH", "./test_data")
CLOUD_TEST_ENABLED = os.getenv("CLOUD_TEST_ENABLED", "false").lower() == "true"
DIGITALOCEAN_TEST_ENDPOINT = os.getenv("DIGITALOCEAN_TEST_ENDPOINT")


@pytest_asyncio.fixture(scope="function")
async def kuzu_db() -> AsyncGenerator[kuzu.Database, None]:
    """
    Create Kuzu database instance with function-level scoping.
    
    Based on best practices for test isolation.
    Each test gets a fresh database that's cleaned up after.
    """
    # Ensure test directory exists
    os.makedirs(TEST_DATABASE_PATH, exist_ok=True)
    
    # Create database
    db = kuzu.Database(TEST_DATABASE_PATH)
    
    yield db
    
    # Cleanup - remove test database files
    db.close()
    import shutil
    if os.path.exists(TEST_DATABASE_PATH):
        shutil.rmtree(TEST_DATABASE_PATH, ignore_errors=True)


@pytest_asyncio.fixture(scope="function")
async def kuzu_connection(kuzu_db: kuzu.Database) -> AsyncGenerator[kuzu.Connection, None]:
    """
    Provide Kuzu database connection.
    
    Creates connection to test database with proper cleanup.
    """
    conn = kuzu.Connection(kuzu_db)
    
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
async def async_client(kuzu_connection: kuzu.Connection) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide FastAPI test client with database override.
    
    Based on FastAPI official docs and TestDriven.io patterns.
    Uses HTTPX AsyncClient for authentic async testing.
    """
    # Override the database connection in the app
    original_conn = getattr(app.state, 'kuzu_connection', None)
    app.state.kuzu_connection = kuzu_connection
    
    # Create async client with ASGI transport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client
    
    # Restore original connection
    if original_conn:
        app.state.kuzu_connection = original_conn


@pytest_asyncio.fixture(scope="function")
async def sample_memory_data(kuzu_connection: kuzu.Connection) -> Dict[str, Any]:
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
    
    # Insert nodes
    for node in sample_nodes:
        kuzu_connection.execute(
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
        kuzu_connection.execute(
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
    
    def __init__(self):
        self.response_times = []
        self.memory_usage = []
        self.errors = []
    
    def record_response_time(self, time_ms: float):
        self.response_times.append(time_ms)
    
    def record_memory_usage(self, usage_mb: float):
        self.memory_usage.append(usage_mb)
    
    def record_error(self, error: str):
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
async def check_kuzu_health(connection: kuzu.Connection) -> bool:
    """Check if Kuzu database is accessible and responsive."""
    try:
        result = connection.execute("RETURN 1 AS test")
        # Kuzu returns a QueryResult object, check if we got results
        return result is not None and len(list(result)) > 0
    except Exception:
        return False


@pytest_asyncio.fixture(scope="function", autouse=True)
async def ensure_database_health(kuzu_connection: kuzu.Connection):
    """Ensure database is healthy before each test."""
    if not await check_kuzu_health(kuzu_connection):
        pytest.fail("Kuzu database health check failed")


# Realistic data factories based on research patterns
class ProjectDataFactory:
    """Factory for creating realistic project test data."""
    
    @staticmethod
    def create_realistic_dataset(
        connection: kuzu.Connection,
        size: str = "small"
    ) -> Dict[str, Any]:
        """
        Create realistic project dataset for testing.
        
        Args:
            connection: Kuzu database connection
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
        
        # Create nodes with realistic content
        created_nodes = []
        for i in range(config["nodes"]):
            node_data = {
                "id": f"test_node_{i:06d}",
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
def monitor_memory_usage():
    """Monitor memory usage for each test."""
    initial_memory = get_memory_usage()
    yield
    final_memory = get_memory_usage()
    peak = max(initial_memory, final_memory)
    
    if peak > 100:  # 100MB threshold
        print(f"\n⚠️  High memory usage detected: {peak:.2f}MB peak") 