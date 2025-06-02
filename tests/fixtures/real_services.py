"""
Real service integration fixtures for Step 13 Phase 2.
Provides real service connections for component integration testing.
"""

import os
import uuid
import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator, Union

import pytest
import httpx
import kuzu
import redis.asyncio as redis
import sqlite3

from server.analytics.engine import AnalyticsEngine
from server.dashboard.analytics_client import AnalyticsEngineClient


class RealAnalyticsEngineFixture:
    """Real analytics engine integration for testing."""
    
    def __init__(self) -> None:
        self.engine_url = os.getenv("ANALYTICS_ENGINE_URL", "http://localhost:8001")
        self.timeout = 30.0
        self.client: Optional[httpx.AsyncClient] = None
        self.analytics_client: Optional[AnalyticsEngineClient] = None
        self.embedded_engine: Optional[AnalyticsEngine] = None
        
    async def setup(self) -> None:
        """Setup real analytics engine connection."""
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        
        # Test connection to analytics engine
        try:
            response = await self.client.get(f"{self.engine_url}/health")
            response.raise_for_status()
        except Exception:
            # If real engine unavailable, start embedded engine
            await self._setup_embedded_engine()
        
        # Create analytics client with proper constructor
        self.analytics_client = AnalyticsEngineClient()
        
        # Initialize if we have an embedded engine
        if self.embedded_engine:
            await self.analytics_client.initialize()
        
        return self.analytics_client
    
    async def _setup_embedded_engine(self) -> None:
        """Setup embedded analytics engine for testing."""
        # Create test Kuzu database
        test_db_path = f"/tmp/test_kuzu_{uuid.uuid4().hex[:8]}"
        test_db = kuzu.Database(test_db_path)
        test_conn = kuzu.Connection(test_db)
        
        # Create test engine instance with proper constructor
        self.embedded_engine = AnalyticsEngine(test_conn)
        await self.embedded_engine.initialize()
        
        # Mock the HTTP endpoints for testing
        self.engine_url = "http://embedded-test"
        
    async def cleanup(self) -> None:
        """Cleanup analytics engine connection."""
        if self.client:
            await self.client.aclose()
        
        if self.embedded_engine:
            await self.embedded_engine.shutdown()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check real analytics engine health."""
        if self.embedded_engine:
            return {
                "status": "healthy",
                "engine_type": "embedded",
                "version": "test",
                "uptime": 0
            }
        
        try:
            if self.client:
                response = await self.client.get(f"{self.engine_url}/health")
                response.raise_for_status()
                return response.json()
            else:
                return {
                    "status": "unhealthy",
                    "error": "No client available",
                    "engine_type": "external"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "engine_type": "external"
            }


class RealDatabaseFixture:
    """Real database connections for integration testing."""
    
    def __init__(self) -> None:
        self.test_id = str(uuid.uuid4())[:8]
        self.kuzu_db = None
        self.kuzu_conn = None
        self.redis_client = None
        self.sqlite_conn = None
        self.cleanup_tasks = []
    
    async def setup_kuzu_real_connection(self) -> None:
        """Setup real Kuzu database with test data isolation."""
        db_path = Path(f"/tmp/kuzu_integration_test_{self.test_id}")
        
        try:
            # Create database and connection
            self.kuzu_db = kuzu.Database(str(db_path))
            self.kuzu_conn = kuzu.Connection(self.kuzu_db)
            
            # Initialize with real schema
            await self._initialize_kuzu_schema()
            
            # Add cleanup task
            self.cleanup_tasks.append(lambda: shutil.rmtree(db_path, ignore_errors=True))
            
            return self.kuzu_conn
            
        except Exception as e:
            if db_path.exists():
                shutil.rmtree(db_path, ignore_errors=True)
            raise RuntimeError(f"Failed to setup Kuzu database: {e}")
    
    async def setup_redis_real_connection(self) -> None:
        """Setup real Redis with dedicated test database."""
        import random
        
        test_db = random.randint(8, 14)  # Use random test DB (8-14)
        
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=test_db,
                decode_responses=True,
                socket_connect_timeout=5.0,
                socket_timeout=5.0
            )
            
            # Verify connection and clear test database
            await self.redis_client.ping()
            await self.redis_client.flushdb()
            
            # Add cleanup task
            self.cleanup_tasks.append(self._cleanup_redis)
            
            return self.redis_client
            
        except Exception as e:
            if self.redis_client:
                await self.redis_client.aclose()
            raise RuntimeError(f"Failed to setup Redis connection: {e}")
    
    async def setup_sqlite_real_connection(self) -> None:
        """Setup real SQLite database for alerts."""
        db_path = f"/tmp/alerts_integration_test_{self.test_id}.db"
        
        try:
            # Create SQLite connection
            self.sqlite_conn = sqlite3.connect(db_path)
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # Initialize alerts schema
            await self._initialize_sqlite_schema()
            
            # Add cleanup task
            self.cleanup_tasks.append(lambda: self._cleanup_sqlite(db_path))
            
            return self.sqlite_conn
            
        except Exception as e:
            if self.sqlite_conn:
                self.sqlite_conn.close()
            raise RuntimeError(f"Failed to setup SQLite database: {e}")
    
    async def _initialize_kuzu_schema(self) -> None:
        """Initialize Kuzu database schema."""
        if not self.kuzu_conn:
            return
            
        schema_queries = [
            "CREATE NODE TABLE IF NOT EXISTS User(id INT64, name STRING, email STRING, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Memory(id INT64, content STRING, type STRING, timestamp TIMESTAMP, PRIMARY KEY(id))",
            "CREATE REL TABLE IF NOT EXISTS BELONGS_TO(FROM User TO Memory, relationship_type STRING)",
            "CREATE REL TABLE IF NOT EXISTS CONNECTS_TO(FROM Memory TO Memory, strength DOUBLE)"
        ]
        
        for query in schema_queries:
            try:
                self.kuzu_conn.execute(query)
            except Exception as e:
                # Schema might already exist
                if "already exists" not in str(e).lower():
                    raise
    
    async def _initialize_sqlite_schema(self) -> None:
        """Initialize SQLite alerts schema."""
        if not self.sqlite_conn:
            return
            
        schema_sql = """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            source TEXT NOT NULL,
            metadata TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        );
        """
        
        self.sqlite_conn.executescript(schema_sql)
        self.sqlite_conn.commit()
    
    async def _cleanup_redis(self) -> None:
        """Cleanup Redis test database."""
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
                await self.redis_client.aclose()
            except Exception:
                pass  # Ignore cleanup errors
    
    def _cleanup_sqlite(self, db_path: str) -> None:
        """Cleanup SQLite database."""
        if self.sqlite_conn:
            try:
                self.sqlite_conn.close()
            except Exception:
                pass
        
        try:
            Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass
    
    async def cleanup_all(self) -> None:
        """Cleanup all database connections."""
        for cleanup_task in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(cleanup_task):
                    await cleanup_task()
                else:
                    cleanup_task()
            except Exception:
                pass  # Ignore cleanup errors


class RealServiceIntegrationManager:
    """Manages real service integration for testing."""
    
    def __init__(self) -> None:
        self.services = {}
        self.use_real_services = os.getenv("USE_REAL_SERVICES", "false").lower() == "true"
        self.service_health = {}
    
    async def setup_analytics_engine(self) -> AnalyticsEngineClient:
        """Setup real analytics engine."""
        analytics_fixture = RealAnalyticsEngineFixture()
        client = await analytics_fixture.setup()
        
        self.services["analytics_engine"] = {
            "fixture": analytics_fixture,
            "client": client,
            "type": "analytics"
        }
        
        return client
    
    async def setup_databases(self) -> Dict[str, Union[kuzu.Connection, redis.Redis, sqlite3.Connection, None]]:
        """Setup real database connections."""
        db_fixture = RealDatabaseFixture()
        
        databases: Dict[str, Union[kuzu.Connection, redis.Redis, sqlite3.Connection, None]] = {}
        
        # Setup Kuzu
        try:
            databases["kuzu"] = await db_fixture.setup_kuzu_real_connection()
        except Exception as e:
            print(f"Warning: Could not setup Kuzu: {e}")
            databases["kuzu"] = None
        
        # Setup Redis
        try:
            databases["redis"] = await db_fixture.setup_redis_real_connection()
        except Exception as e:
            print(f"Warning: Could not setup Redis: {e}")
            databases["redis"] = None
        
        # Setup SQLite
        try:
            databases["sqlite"] = await db_fixture.setup_sqlite_real_connection()
        except Exception as e:
            print(f"Warning: Could not setup SQLite: {e}")
            databases["sqlite"] = None
        
        self.services["databases"] = {
            "fixture": db_fixture,
            "connections": databases,
            "type": "database"
        }
        
        return databases
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all real services."""
        health_results = {}
        
        for service_name, service_info in self.services.items():
            try:
                if service_name == "analytics_engine":
                    health_results[service_name] = await service_info["fixture"].health_check()
                elif service_name == "databases":
                    health_results[service_name] = await self._check_database_health(service_info)
                else:
                    health_results[service_name] = {"status": "unknown", "type": service_info["type"]}
            except Exception as e:
                health_results[service_name] = {"status": "error", "error": str(e)}
        
        self.service_health = health_results
        return health_results
    
    async def _check_database_health(self, db_service_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of database connections."""
        connections = db_service_info["connections"]
        health = {"status": "healthy", "databases": {}}
        
        # Check Kuzu
        kuzu_conn = connections.get("kuzu")
        if kuzu_conn:
            try:
                kuzu_conn.execute("MATCH (n) RETURN count(n) LIMIT 1")
                health["databases"]["kuzu"] = {"status": "healthy"}
            except Exception as e:
                health["databases"]["kuzu"] = {"status": "unhealthy", "error": str(e)}
        
        # Check Redis
        redis_conn = connections.get("redis")
        if redis_conn:
            try:
                await redis_conn.ping()
                health["databases"]["redis"] = {"status": "healthy"}
            except Exception as e:
                health["databases"]["redis"] = {"status": "unhealthy", "error": str(e)}
        
        # Check SQLite
        sqlite_conn = connections.get("sqlite")
        if sqlite_conn:
            try:
                sqlite_conn.execute("SELECT 1")
                health["databases"]["sqlite"] = {"status": "healthy"}
            except Exception as e:
                health["databases"]["sqlite"] = {"status": "unhealthy", "error": str(e)}
        
        # Overall health based on individual database health
        unhealthy_count = sum(1 for db_health in health["databases"].values() 
                            if db_health.get("status") != "healthy")
        
        if unhealthy_count > 0:
            health["status"] = "degraded" if unhealthy_count < len(health["databases"]) else "unhealthy"
        
        return health
    
    async def cleanup_all(self) -> None:
        """Cleanup all real services."""
        for service_name, service_info in self.services.items():
            try:
                await service_info["fixture"].cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup {service_name}: {e}")
        
        self.services.clear()


# Pytest fixtures for real service integration

@pytest.fixture(scope="function")
async def real_analytics_engine() -> AsyncGenerator[AnalyticsEngineClient, None]:
    """Fixture for real analytics engine integration."""
    manager = RealServiceIntegrationManager()
    
    try:
        client = await manager.setup_analytics_engine()
        yield client
    finally:
        await manager.cleanup_all()


@pytest.fixture(scope="function")
async def real_databases() -> AsyncGenerator[Dict[str, Any], None]:
    """Fixture for real database connections."""
    manager = RealServiceIntegrationManager()
    
    try:
        databases = await manager.setup_databases()
        yield databases
    finally:
        await manager.cleanup_all()


@pytest.fixture(scope="function")
async def real_service_integration() -> AsyncGenerator[RealServiceIntegrationManager, None]:
    """Fixture for complete real service integration."""
    manager = RealServiceIntegrationManager()
    
    try:
        # Setup all services
        await manager.setup_analytics_engine()
        await manager.setup_databases()
        
        # Health check
        await manager.health_check_all()
        
        yield manager
    finally:
        await manager.cleanup_all()


@pytest.fixture(scope="function")
def real_service_config() -> None:
    """Configuration for real services."""
    return {
        "analytics_engine": {
            "url": os.getenv("ANALYTICS_ENGINE_URL", "http://localhost:8001"),
            "timeout": 30.0,
            "health_check_endpoint": "/health"
        },
        "databases": {
            "kuzu": {
                "path_prefix": "/tmp/integration_test_kuzu",
                "buffer_pool_size": 64 * 1024 * 1024  # 64MB
            },
            "redis": {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", 6379)),
                "test_db_range": (8, 14)
            },
            "sqlite": {
                "path_prefix": "/tmp/integration_test_alerts"
            }
        },
        "performance": {
            "max_response_time": 5.0,
            "min_success_rate": 0.95,
            "max_memory_usage": 500 * 1024 * 1024  # 500MB
        }
    } 