"""
Database isolation fixtures for GraphMemory-IDE integration testing.
Provides isolated test databases for Kuzu, Redis, and SQLite with automatic cleanup.
"""

import asyncio
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator, Optional, Dict, Union, Any
from unittest.mock import patch

import pytest
import pytest_asyncio
import redis.asyncio as redis
import kuzu

# Test database configuration
TEST_DB_CONFIG = {
    "kuzu": {
        "timeout": 30,
        "buffer_pool_size": 128 * 1024 * 1024,  # 128MB in bytes
        "max_connections": 10,
    },
    "redis": {
        "timeout": 30,
        "max_connections": 10,
        "decode_responses": True,
    },
    "sqlite": {
        "timeout": 30.0,
        "check_same_thread": False,
        "isolation_level": None,
    }
}

# Database isolation fixtures for Kuzu GraphDB
@pytest.fixture(scope="function")
def kuzu_test_db_path(temp_dir: Path) -> Path:
    """Create a temporary Kuzu database path for testing."""
    db_path = temp_dir / "test_kuzu_db"
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path

@pytest.fixture(scope="function")
def kuzu_test_database(kuzu_test_db_path: Path) -> Generator[kuzu.Database, None, None]:
    """Create an isolated Kuzu database for testing."""
    database = None
    try:
        # Create Kuzu database with test configuration
        buffer_size = int(TEST_DB_CONFIG["kuzu"]["buffer_pool_size"])
        database = kuzu.Database(
            str(kuzu_test_db_path),
            buffer_pool_size=buffer_size
        )
        yield database
    finally:
        # Cleanup: Close database and remove files
        try:
            if database:
                database.close()
        except Exception:
            pass
        
        # Remove database files
        if kuzu_test_db_path.exists():
            shutil.rmtree(kuzu_test_db_path, ignore_errors=True)

@pytest.fixture(scope="function")
def kuzu_test_connection(kuzu_test_database: kuzu.Database) -> Generator[kuzu.Connection, None, None]:
    """Create a Kuzu connection for testing."""
    connection = None
    try:
        connection = kuzu.Connection(kuzu_test_database)
        
        # Initialize test schema
        _initialize_kuzu_test_schema(connection)
        
        yield connection
    finally:
        # Cleanup connection
        try:
            if connection:
                connection.close()
        except Exception:
            pass

def _initialize_kuzu_test_schema(connection: kuzu.Connection) -> None:
    """Initialize Kuzu database with test schema."""
    try:
        # Create Memory nodes
        connection.execute("""
            CREATE NODE TABLE IF NOT EXISTS Memory(
                id STRING,
                content STRING,
                memory_type STRING,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                metadata STRING,
                PRIMARY KEY(id)
            )
        """)
        
        # Create Entity nodes
        connection.execute("""
            CREATE NODE TABLE IF NOT EXISTS Entity(
                id STRING,
                name STRING,
                entity_type STRING,
                confidence DOUBLE,
                metadata STRING,
                PRIMARY KEY(id)
            )
        """)
        
        # Create relationships
        connection.execute("""
            CREATE REL TABLE IF NOT EXISTS RELATES_TO(
                FROM Memory TO Memory,
                relationship_type STRING,
                strength DOUBLE,
                created_at TIMESTAMP
            )
        """)
        
        connection.execute("""
            CREATE REL TABLE IF NOT EXISTS CONTAINS(
                FROM Memory TO Entity,
                position INT64,
                confidence DOUBLE
            )
        """)
        
        # Create indexes for performance
        connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON Memory(memory_type)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_created ON Memory(created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON Entity(entity_type)")
        
    except Exception as e:
        print(f"Warning: Could not initialize Kuzu test schema: {e}")

# Redis test fixtures
@pytest_asyncio.fixture(scope="function")
async def redis_test_client() -> AsyncGenerator[redis.Redis, None]:
    """Create an isolated Redis client for testing."""
    # Use a test-specific Redis database number
    test_db = 15  # Use database 15 for testing
    
    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=test_db,
        decode_responses=TEST_DB_CONFIG["redis"]["decode_responses"],
        socket_timeout=TEST_DB_CONFIG["redis"]["timeout"],
        max_connections=TEST_DB_CONFIG["redis"]["max_connections"]
    )
    
    try:
        # Test connection
        await client.ping()
        
        # Clear any existing test data
        await client.flushdb()
        
        yield client
        
    except redis.ConnectionError:
        # If Redis is not available, create a mock client
        print("Warning: Redis not available, using mock client")
        from unittest.mock import AsyncMock
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.set = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.delete = AsyncMock(return_value=0)
        mock_client.flushdb = AsyncMock(return_value=True)
        yield mock_client
        
    finally:
        # Cleanup: Clear test data and close connection
        try:
            await client.flushdb()
            await client.close()
        except Exception:
            pass

@pytest.fixture(scope="function")
def redis_test_config() -> dict:
    """Get Redis test configuration."""
    return {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": 15,  # Test database
        "decode_responses": True,
        "socket_timeout": 30,
    }

# SQLite test fixtures for alerts database
@pytest.fixture(scope="function")
def sqlite_test_db_path(temp_dir: Path) -> Path:
    """Create a temporary SQLite database path for testing."""
    return temp_dir / "test_alerts.db"

@pytest.fixture(scope="function")
def sqlite_test_connection(sqlite_test_db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Create an isolated SQLite connection for testing."""
    connection = None
    try:
        connection = sqlite3.connect(
            str(sqlite_test_db_path),
            timeout=float(TEST_DB_CONFIG["sqlite"]["timeout"]),
            check_same_thread=bool(TEST_DB_CONFIG["sqlite"]["check_same_thread"]),
            isolation_level=TEST_DB_CONFIG["sqlite"]["isolation_level"]
        )
        
        # Enable foreign keys
        connection.execute("PRAGMA foreign_keys = ON")
        
        # Initialize test schema
        _initialize_sqlite_test_schema(connection)
        
        yield connection
        
    finally:
        # Cleanup connection and database file
        try:
            if connection:
                connection.close()
        except Exception:
            pass
        
        if sqlite_test_db_path.exists():
            sqlite_test_db_path.unlink(missing_ok=True)

def _initialize_sqlite_test_schema(connection: sqlite3.Connection) -> None:
    """Initialize SQLite database with test schema for alerts."""
    try:
        # Create alerts table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                message TEXT NOT NULL,
                source TEXT,
                metric_name TEXT,
                metric_value REAL,
                threshold REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TIMESTAMP,
                resolved_at TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Create incidents table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                assigned_to TEXT,
                metadata TEXT
            )
        """)
        
        # Create alert_incidents relationship table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS alert_incidents (
                alert_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (alert_id, incident_id),
                FOREIGN KEY (alert_id) REFERENCES alerts(id),
                FOREIGN KEY (incident_id) REFERENCES incidents(id)
            )
        """)
        
        # Create correlations table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS correlations (
                id TEXT PRIMARY KEY,
                alert_id_1 TEXT NOT NULL,
                alert_id_2 TEXT NOT NULL,
                correlation_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (alert_id_1) REFERENCES alerts(id),
                FOREIGN KEY (alert_id_2) REFERENCES alerts(id)
            )
        """)
        
        # Create indexes for performance
        connection.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(priority)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_correlations_alert1 ON correlations(alert_id_1)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_correlations_alert2 ON correlations(alert_id_2)")
        
        connection.commit()
        
    except Exception as e:
        print(f"Warning: Could not initialize SQLite test schema: {e}")

# Database configuration override fixtures
@pytest.fixture(scope="function")
def mock_database_config(kuzu_test_db_path: Path, redis_test_config: dict, sqlite_test_db_path: Path):
    """Override database configuration for testing."""
    test_config = {
        "KUZU_DB_PATH": str(kuzu_test_db_path),
        "REDIS_HOST": redis_test_config["host"],
        "REDIS_PORT": str(redis_test_config["port"]),
        "REDIS_DB": str(redis_test_config["db"]),
        "ALERT_DB_PATH": str(sqlite_test_db_path),
    }
    
    with patch.dict(os.environ, test_config):
        yield test_config

# Combined database fixture for full integration tests
@pytest_asyncio.fixture(scope="function")
async def isolated_databases(
    kuzu_test_connection: kuzu.Connection,
    redis_test_client: redis.Redis,
    sqlite_test_connection: sqlite3.Connection,
    mock_database_config: dict
):
    """Provide all isolated databases for comprehensive integration testing."""
    databases = {
        "kuzu": kuzu_test_connection,
        "redis": redis_test_client,
        "sqlite": sqlite_test_connection,
        "config": mock_database_config
    }
    
    yield databases
    
    # Final cleanup (individual fixtures handle their own cleanup)
    pass

# Database health check fixtures
@pytest_asyncio.fixture(scope="function")
async def check_database_health(isolated_databases) -> Dict[str, Union[bool, str]]:
    """Check health of all test databases."""
    health_status: Dict[str, Union[bool, str]] = {}
    
    # Check Kuzu
    try:
        kuzu_conn = isolated_databases["kuzu"]
        result = kuzu_conn.execute("RETURN 1 AS test")
        health_status["kuzu"] = True
    except Exception as e:
        health_status["kuzu"] = f"Error: {e}"
    
    # Check Redis
    try:
        redis_client = isolated_databases["redis"]
        await redis_client.ping()
        health_status["redis"] = True
    except Exception as e:
        health_status["redis"] = f"Error: {e}"
    
    # Check SQLite
    try:
        sqlite_conn = isolated_databases["sqlite"]
        sqlite_conn.execute("SELECT 1")
        health_status["sqlite"] = True
    except Exception as e:
        health_status["sqlite"] = f"Error: {e}"
    
    return health_status

# Performance monitoring for database operations
@pytest.fixture(scope="function")
def database_performance_monitor():
    """Monitor database operation performance during tests."""
    import time
    
    class DatabasePerformanceMonitor:
        def __init__(self):
            self.operations = []
        
        def time_operation(self, operation_name: str):
            """Context manager to time database operations."""
            from contextlib import contextmanager
            
            @contextmanager
            def timer():
                start_time = time.time()
                yield
                end_time = time.time()
                duration = end_time - start_time
                self.operations.append({
                    "operation": operation_name,
                    "duration": duration,
                    "timestamp": start_time
                })
                
                # Log slow operations
                if duration > 1.0:  # Operations taking more than 1 second
                    print(f"⚠️  Slow database operation: {operation_name} took {duration:.2f}s")
            
            return timer()
        
        def get_summary(self):
            """Get performance summary."""
            if not self.operations:
                return {"total_operations": 0}
            
            durations = [op["duration"] for op in self.operations]
            return {
                "total_operations": len(self.operations),
                "total_time": sum(durations),
                "average_time": sum(durations) / len(durations),
                "max_time": max(durations),
                "slow_operations": [op for op in self.operations if op["duration"] > 1.0]
            }
    
    return DatabasePerformanceMonitor() 