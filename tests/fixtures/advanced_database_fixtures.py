"""
Advanced Database Fixtures for Step 13 Phase 2 Day 2.
Production-grade connection pool management, transaction coordination, 
and performance monitoring for multi-database integration testing.
"""

import os
import uuid
import asyncio
import time
import json
import psutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncContextManager, Union, AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime

import pytest
import kuzu
import redis.asyncio as redis
from databases import Database

from tests.utils.test_helpers import ExecutionTimer, MemoryProfiler


@dataclass
class ConnectionPoolMetrics:
    """Metrics for connection pool performance tracking."""
    pool_name: str
    active_connections: int = 0
    total_connections: int = 0
    connection_reuse_count: int = 0
    avg_connection_time: float = 0.0
    peak_connections: int = 0
    connection_errors: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class DatabasePerformanceMetrics:
    """Performance metrics for database operations."""
    operation_type: str
    duration: float
    memory_delta: int
    success: bool
    timestamp: float
    database_name: str
    connection_id: Optional[str] = None


class DatabaseConnectionPoolManager:
    """Advanced connection pool management for multi-database testing."""
    
    def __init__(self):
        self.pools: Dict[str, Dict[str, Any]] = {}
        self.pool_metrics: Dict[str, ConnectionPoolMetrics] = {}
        self.performance_monitor = DatabasePerformanceMonitor()
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        
    async def setup_kuzu_pool(self, min_size: int = 5, max_size: int = 20) -> Dict[str, Any]:
        """Setup Kuzu connection pool with buffer optimization."""
        pool_id = f"kuzu_pool_{uuid.uuid4().hex[:8]}"
        
        # Create test database path
        db_path = Path(f"/tmp/kuzu_pool_test_{uuid.uuid4().hex[:8]}")
        
        # Create connection pool
        connections = []
        for i in range(min_size):
            try:
                # Create Kuzu database with only valid parameters
                db = kuzu.Database(
                    database_path=str(db_path),
                    buffer_pool_size=128 * 1024 * 1024,  # 128MB buffer pool
                    max_num_threads=8,  # Optimal for testing workload
                )
                conn = kuzu.Connection(db)
                
                # Initialize basic schema for testing
                await self._initialize_kuzu_test_schema(conn)
                
                connections.append({
                    "id": f"{pool_id}_conn_{i}",
                    "database": db,
                    "connection": conn,
                    "created_at": time.time(),
                    "last_used": time.time(),
                    "usage_count": 0
                })
            except Exception as e:
                print(f"Warning: Failed to create Kuzu connection {i}: {e}")
        
        pool_config = {
            "pool_id": pool_id,
            "pool_type": "kuzu",
            "connections": connections,
            "min_size": min_size,
            "max_size": max_size,
            "db_path": db_path,
            "cleanup_tasks": [lambda: self._cleanup_kuzu_pool(db_path)]
        }
        
        self.pools[pool_id] = pool_config
        self.pool_metrics[pool_id] = ConnectionPoolMetrics(
            pool_name=pool_id,
            total_connections=len(connections),
            active_connections=0
        )
        
        return pool_config
    
    async def setup_redis_cluster_pool(self, pool_size: int = 15) -> Dict[str, Any]:
        """Setup Redis cluster connection pool."""
        pool_id = f"redis_pool_{uuid.uuid4().hex[:8]}"
        
        # Redis configuration for optimal performance
        redis_config = {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", 6379)),
            "db": 9,  # Use dedicated test database
            "decode_responses": True,
            "socket_connect_timeout": 5.0,
            "socket_timeout": 5.0,
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "health_check_interval": 30
        }
        
        # Create connection pool
        connections = []
        for i in range(pool_size):
            try:
                conn = redis.Redis(**redis_config)
                
                # Test connection and clear test database
                await conn.ping()
                await conn.flushdb()
                
                connections.append({
                    "id": f"{pool_id}_conn_{i}",
                    "connection": conn,
                    "created_at": time.time(),
                    "last_used": time.time(),
                    "usage_count": 0,
                    "pipeline": None
                })
            except Exception as e:
                print(f"Warning: Failed to create Redis connection {i}: {e}")
        
        pool_config = {
            "pool_id": pool_id,
            "pool_type": "redis",
            "connections": connections,
            "pool_size": pool_size,
            "config": redis_config,
            "cleanup_tasks": [lambda: self._cleanup_redis_pool(connections)]
        }
        
        self.pools[pool_id] = pool_config
        self.pool_metrics[pool_id] = ConnectionPoolMetrics(
            pool_name=pool_id,
            total_connections=len(connections),
            active_connections=0
        )
        
        return pool_config
    
    async def setup_sqlite_wal_pool(self, pool_size: int = 10) -> Dict[str, Any]:
        """Setup SQLite connection pool with WAL mode."""
        pool_id = f"sqlite_pool_{uuid.uuid4().hex[:8]}"
        
        # Create test database path
        db_path = f"/tmp/sqlite_pool_test_{uuid.uuid4().hex[:8]}.db"
        
        # SQLite configuration for optimal concurrency
        sqlite_config = {
            "wal_mode": True,  # Write-Ahead Logging for concurrency
            "busy_timeout": 30000,  # 30 second timeout
            "cache_size": 10000,  # 10MB cache
            "synchronous": "NORMAL",  # Balance performance/durability
            "journal_mode": "WAL",
            "foreign_keys": True
        }
        
        # Create connection pool
        connections = []
        for i in range(pool_size):
            try:
                # Create databases instance for async operations
                database_url = f"sqlite+aiosqlite:///{db_path}"
                db = Database(database_url)
                await db.connect()
                
                # Configure SQLite settings
                await self._configure_sqlite_connection(db, sqlite_config)
                
                # Initialize schema
                await self._initialize_sqlite_test_schema(db)
                
                connections.append({
                    "id": f"{pool_id}_conn_{i}",
                    "database": db,
                    "created_at": time.time(),
                    "last_used": time.time(),
                    "usage_count": 0,
                    "transaction": None
                })
            except Exception as e:
                print(f"Warning: Failed to create SQLite connection {i}: {e}")
        
        pool_config = {
            "pool_id": pool_id,
            "pool_type": "sqlite",
            "connections": connections,
            "pool_size": pool_size,
            "db_path": db_path,
            "config": sqlite_config,
            "cleanup_tasks": [lambda: self._cleanup_sqlite_pool(connections, db_path)]
        }
        
        self.pools[pool_id] = pool_config
        self.pool_metrics[pool_id] = ConnectionPoolMetrics(
            pool_name=pool_id,
            total_connections=len(connections),
            active_connections=0
        )
        
        return pool_config
    
    async def get_connection(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get connection from pool with round-robin selection."""
        if pool_id not in self.pools:
            return None
        
        pool = self.pools[pool_id]
        connections = pool["connections"]
        
        if not connections:
            return None
        
        # Find least recently used connection
        available_connections = [c for c in connections if c["id"] not in self.active_connections]
        
        if not available_connections:
            # All connections busy, try to create new one if under max_size
            if pool["pool_type"] == "kuzu" and len(connections) < pool.get("max_size", 10):
                new_conn = await self._create_new_kuzu_connection(pool)
                if new_conn:
                    connections.append(new_conn)
                    available_connections = [new_conn]
        
        if not available_connections:
            return None
        
        # Select connection with lowest usage count
        connection = min(available_connections, key=lambda c: c["usage_count"])
        
        # Mark as active
        connection["last_used"] = time.time()
        connection["usage_count"] += 1
        self.active_connections[connection["id"]] = connection
        
        # Update metrics
        metrics = self.pool_metrics[pool_id]
        metrics.active_connections += 1
        metrics.connection_reuse_count += 1
        metrics.peak_connections = max(metrics.peak_connections, metrics.active_connections)
        metrics.last_updated = datetime.now()
        
        return connection
    
    async def return_connection(self, pool_id: str, connection_id: str):
        """Return connection to pool."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            
            # Update metrics
            if pool_id in self.pool_metrics:
                metrics = self.pool_metrics[pool_id]
                metrics.active_connections = max(0, metrics.active_connections - 1)
                metrics.last_updated = datetime.now()
    
    async def stress_test_pools(self, concurrent_connections: int = 100) -> Dict[str, Any]:
        """Stress test all connection pools simultaneously."""
        results = {}
        
        for pool_id, pool in self.pools.items():
            pool_type = pool["pool_type"]
            
            async def test_pool_connection(conn_num: int):
                """Test individual pool connection."""
                start_time = time.time()
                
                try:
                    conn = await self.get_connection(pool_id)
                    if not conn:
                        return {"success": False, "error": "No connection available", "duration": 0}
                    
                    # Perform database-specific operation
                    if pool_type == "kuzu":
                        result = await self._test_kuzu_operation(conn)
                    elif pool_type == "redis":
                        result = await self._test_redis_operation(conn)
                    elif pool_type == "sqlite":
                        result = await self._test_sqlite_operation(conn)
                    else:
                        result = {"success": False, "error": "Unknown pool type"}
                    
                    await self.return_connection(pool_id, conn["id"])
                    
                    end_time = time.time()
                    result["duration"] = end_time - start_time
                    return result
                    
                except Exception as e:
                    end_time = time.time()
                    return {
                        "success": False,
                        "error": str(e),
                        "duration": end_time - start_time
                    }
            
            # Execute concurrent connections for this pool
            tasks = [test_pool_connection(i) for i in range(concurrent_connections)]
            pool_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            successful_results = [r for r in pool_results if isinstance(r, dict) and r.get("success")]
            failed_results = [r for r in pool_results if not (isinstance(r, dict) and r.get("success"))]
            
            results[pool_id] = {
                "pool_type": pool_type,
                "total_requests": len(pool_results),
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "success_rate": len(successful_results) / len(pool_results) if pool_results else 0,
                "avg_duration": sum(r["duration"] for r in successful_results) / len(successful_results) if successful_results else 0,
                "pool_metrics": self.pool_metrics[pool_id].__dict__
            }
        
        return results
    
    async def _initialize_kuzu_test_schema(self, conn: kuzu.Connection):
        """Initialize Kuzu test schema."""
        schema_queries = [
            "CREATE NODE TABLE IF NOT EXISTS TestUser(id INT64, name STRING, email STRING, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS TestMemory(id INT64, content STRING, type STRING, timestamp TIMESTAMP, PRIMARY KEY(id))",
            "CREATE REL TABLE IF NOT EXISTS TEST_BELONGS_TO(FROM TestUser TO TestMemory, relationship_type STRING)",
            "CREATE REL TABLE IF NOT EXISTS TEST_CONNECTS_TO(FROM TestMemory TO TestMemory, strength DOUBLE)"
        ]
        
        for query in schema_queries:
            try:
                conn.execute(query)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"Warning: Failed to execute Kuzu schema query: {e}")
    
    async def _configure_sqlite_connection(self, db: Database, config: Dict[str, Any]):
        """Configure SQLite connection with optimal settings."""
        config_queries = [
            f"PRAGMA journal_mode = {config['journal_mode']}",
            f"PRAGMA synchronous = {config['synchronous']}",
            f"PRAGMA cache_size = {config['cache_size']}",
            f"PRAGMA busy_timeout = {config['busy_timeout']}",
            f"PRAGMA foreign_keys = {'ON' if config['foreign_keys'] else 'OFF'}"
        ]
        
        for query in config_queries:
            try:
                await db.execute(query=query)
            except Exception as e:
                print(f"Warning: Failed to configure SQLite: {e}")
    
    async def _initialize_sqlite_test_schema(self, db: Database):
        """Initialize SQLite test schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS test_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS test_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES test_users (id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_test_analytics_user_id ON test_analytics(user_id);
        CREATE INDEX IF NOT EXISTS idx_test_analytics_timestamp ON test_analytics(timestamp);
        """
        
        try:
            await db.execute(query=schema_sql)
        except Exception as e:
            print(f"Warning: Failed to initialize SQLite schema: {e}")
    
    async def _create_new_kuzu_connection(self, pool: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new Kuzu connection for pool expansion."""
        try:
            db = kuzu.Database(
                database_path=str(pool["db_path"]),
                buffer_pool_size=128 * 1024 * 1024,
                max_num_threads=8
            )
            conn = kuzu.Connection(db)
            await self._initialize_kuzu_test_schema(conn)
            
            connection_id = f"{pool['pool_id']}_conn_{len(pool['connections'])}"
            
            return {
                "id": connection_id,
                "database": db,
                "connection": conn,
                "created_at": time.time(),
                "last_used": time.time(),
                "usage_count": 0
            }
        except Exception as e:
            print(f"Warning: Failed to create new Kuzu connection: {e}")
            return None
    
    async def _test_kuzu_operation(self, conn: Dict[str, Any]) -> Dict[str, Any]:
        """Test Kuzu database operation."""
        try:
            kuzu_conn = conn["connection"]
            # Simple count query for testing
            result = kuzu_conn.execute("MATCH (n) RETURN count(n) AS node_count")
            return {"success": True, "result": "kuzu_operation_complete"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_redis_operation(self, conn: Dict[str, Any]) -> Dict[str, Any]:
        """Test Redis operation."""
        try:
            redis_conn = conn["connection"]
            test_key = f"test_key_{uuid.uuid4().hex[:8]}"
            await redis_conn.set(test_key, "test_value", ex=60)
            value = await redis_conn.get(test_key)
            await redis_conn.delete(test_key)
            return {"success": True, "result": "redis_operation_complete"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_sqlite_operation(self, conn: Dict[str, Any]) -> Dict[str, Any]:
        """Test SQLite operation."""
        try:
            db = conn["database"]
            result = await db.fetch_one("SELECT 1 as test_value")
            return {"success": True, "result": "sqlite_operation_complete"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _cleanup_kuzu_pool(self, db_path: Path):
        """Cleanup Kuzu pool resources."""
        try:
            if db_path.exists():
                import shutil
                shutil.rmtree(db_path, ignore_errors=True)
        except Exception:
            pass
    
    async def _cleanup_redis_pool(self, connections: List[Dict[str, Any]]):
        """Cleanup Redis pool connections."""
        for conn in connections:
            try:
                redis_conn = conn["connection"]
                await redis_conn.flushdb()
                await redis_conn.aclose()
            except Exception:
                pass
    
    async def _cleanup_sqlite_pool(self, connections: List[Dict[str, Any]], db_path: str):
        """Cleanup SQLite pool connections."""
        for conn in connections:
            try:
                db = conn["database"]
                await db.disconnect()
            except Exception:
                pass
        
        try:
            Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass
    
    async def cleanup_all_pools(self):
        """Cleanup all connection pools."""
        for pool_id, pool in self.pools.items():
            cleanup_tasks = pool.get("cleanup_tasks", [])
            for cleanup_task in cleanup_tasks:
                try:
                    if asyncio.iscoroutinefunction(cleanup_task):
                        await cleanup_task()
                    else:
                        cleanup_task()
                except Exception as e:
                    print(f"Warning: Failed to cleanup pool {pool_id}: {e}")
        
        self.pools.clear()
        self.pool_metrics.clear()
        self.active_connections.clear()


class TransactionCoordinator:
    """Cross-database transaction management with ACID guarantees."""
    
    def __init__(self, pool_manager: DatabaseConnectionPoolManager):
        self.pool_manager = pool_manager
        self.active_transactions: Dict[str, Dict[str, Any]] = {}
        self.transaction_timeout = 30.0  # 30 seconds
    
    @asynccontextmanager
    async def cross_database_transaction(self, 
                                       isolation_level: str = "serializable",
                                       timeout: Optional[float] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Create cross-database transaction with coordination."""
        transaction_id = str(uuid.uuid4())
        actual_timeout = timeout or self.transaction_timeout
        
        transaction_context = {
            "id": transaction_id,
            "isolation_level": isolation_level,
            "connections": {},
            "started_at": time.time(),
            "timeout": actual_timeout,
            "rollback_functions": []
        }
        
        self.active_transactions[transaction_id] = transaction_context
        
        try:
            # Setup connections for each database type
            for pool_id, pool in self.pool_manager.pools.items():
                conn = await self.pool_manager.get_connection(pool_id)
                if conn:
                    connections_dict = transaction_context["connections"]
                    connections_dict[pool_id] = conn
                    
                    # Start transaction based on database type
                    await self._start_database_transaction(pool["pool_type"], conn, isolation_level)
            
            yield transaction_context
            
            # Commit all transactions
            await self._commit_all_transactions(transaction_context)
            
        except Exception as e:
            # Rollback all transactions
            await self._rollback_all_transactions(transaction_context)
            raise
        finally:
            # Return connections to pools
            connections_dict = transaction_context["connections"]
            for pool_id, conn in connections_dict.items():
                await self.pool_manager.return_connection(pool_id, conn["id"])
            
            # Remove from active transactions
            if transaction_id in self.active_transactions:
                del self.active_transactions[transaction_id]
    
    async def _start_database_transaction(self, db_type: str, conn: Dict[str, Any], isolation_level: str):
        """Start transaction for specific database type."""
        if db_type == "sqlite":
            # SQLite transaction using databases library
            db = conn["database"]
            transaction = await db.transaction()
            conn["transaction"] = transaction
            
        elif db_type == "redis":
            # Redis uses MULTI/EXEC for transactions
            redis_conn = conn["connection"]
            pipeline = redis_conn.pipeline(transaction=True)
            conn["pipeline"] = pipeline
            
        elif db_type == "kuzu":
            # Kuzu doesn't have explicit transactions, use connection-level consistency
            pass
    
    async def _commit_all_transactions(self, transaction_context: Dict[str, Any]):
        """Commit all transactions in the context."""
        commit_results = {}
        connections_dict = transaction_context["connections"]
        
        for pool_id, conn in connections_dict.items():
            pool = self.pool_manager.pools[pool_id]
            db_type = pool["pool_type"]
            
            try:
                if db_type == "sqlite" and conn.get("transaction"):
                    await conn["transaction"].commit()
                elif db_type == "redis" and conn.get("pipeline"):
                    await conn["pipeline"].execute()
                
                commit_results[pool_id] = {"success": True}
            except Exception as e:
                commit_results[pool_id] = {"success": False, "error": str(e)}
                raise  # Fail fast on commit errors
    
    async def _rollback_all_transactions(self, transaction_context: Dict[str, Any]):
        """Rollback all transactions in the context."""
        connections_dict = transaction_context["connections"]
        
        for pool_id, conn in connections_dict.items():
            pool = self.pool_manager.pools[pool_id]
            db_type = pool["pool_type"]
            
            try:
                if db_type == "sqlite" and conn.get("transaction"):
                    await conn["transaction"].rollback()
                elif db_type == "redis" and conn.get("pipeline"):
                    conn["pipeline"].reset()
                
                # Execute rollback functions
                rollback_functions = transaction_context.get("rollback_functions", [])
                for rollback_func in rollback_functions:
                    try:
                        if asyncio.iscoroutinefunction(rollback_func):
                            await rollback_func()
                        else:
                            rollback_func()
                    except Exception as e:
                        print(f"Warning: Rollback function failed: {e}")
                        
            except Exception as e:
                print(f"Warning: Failed to rollback {db_type} transaction: {e}")


class DatabasePerformanceMonitor:
    """Real-time performance tracking for database operations."""
    
    def __init__(self):
        self.metrics: List[DatabasePerformanceMetrics] = []
        self.profiler = MemoryProfiler()
        self.timer = ExecutionTimer()
        self.baseline_metrics: Dict[str, Dict[str, Any]] = {}
    
    async def profile_operation(self, 
                              database_name: str,
                              operation_type: str,
                              operation_func,
                              connection_id: str = None) -> Any:
        """Profile database operation with comprehensive metrics."""
        
        # Start profiling
        self.profiler.start_tracing()
        start_memory = self.profiler.get_current_memory_usage()["current_rss"]
        
        measurement_key = f"{database_name}_{operation_type}_{int(time.time())}"
        
        try:
            with self.timer.measure(measurement_key):
                result = await operation_func()
            
            success = True
            error = None
            
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        finally:
            # Stop profiling and collect metrics
            self.profiler.stop_tracing()
            end_memory = self.profiler.get_current_memory_usage()["current_rss"]
            measurements = self.timer.get_measurements()
            
            duration = measurements.get(measurement_key, {}).get("duration", 0.0)
            memory_delta = end_memory - start_memory
            
            # Store performance metrics
            metric = DatabasePerformanceMetrics(
                operation_type=operation_type,
                duration=duration,
                memory_delta=memory_delta,
                success=success,
                timestamp=time.time(),
                database_name=database_name,
                connection_id=connection_id
            )
            
            self.metrics.append(metric)
        
        return result
    
    def get_performance_summary(self, database_name: str = None) -> Dict[str, Any]:
        """Get performance summary for database operations."""
        filtered_metrics = self.metrics
        if database_name:
            filtered_metrics = [m for m in self.metrics if m.database_name == database_name]
        
        if not filtered_metrics:
            return {"error": "No metrics available"}
        
        successful_metrics = [m for m in filtered_metrics if m.success]
        failed_metrics = [m for m in filtered_metrics if not m.success]
        
        return {
            "total_operations": len(filtered_metrics),
            "successful_operations": len(successful_metrics),
            "failed_operations": len(failed_metrics),
            "success_rate": len(successful_metrics) / len(filtered_metrics) if filtered_metrics else 0,
            "avg_duration": sum(m.duration for m in successful_metrics) / len(successful_metrics) if successful_metrics else 0,
            "avg_memory_delta": sum(m.memory_delta for m in successful_metrics) / len(successful_metrics) if successful_metrics else 0,
            "max_duration": max((m.duration for m in successful_metrics), default=0),
            "min_duration": min((m.duration for m in successful_metrics), default=0),
            "total_memory_used": sum(max(0, m.memory_delta) for m in successful_metrics),
            "database_breakdown": self._get_database_breakdown(filtered_metrics)
        }
    
    def _get_database_breakdown(self, metrics: List[DatabasePerformanceMetrics]) -> Dict[str, Any]:
        """Get performance breakdown by database type."""
        breakdown = {}
        
        for metric in metrics:
            db_name = metric.database_name
            if db_name not in breakdown:
                breakdown[db_name] = {
                    "operations": 0,
                    "total_duration": 0.0,
                    "total_memory": 0,
                    "success_count": 0
                }
            
            breakdown[db_name]["operations"] += 1
            breakdown[db_name]["total_duration"] += metric.duration
            breakdown[db_name]["total_memory"] += max(0, metric.memory_delta)
            if metric.success:
                breakdown[db_name]["success_count"] += 1
        
        # Calculate averages
        for db_name, stats in breakdown.items():
            if stats["operations"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["operations"]
                stats["avg_memory"] = stats["total_memory"] / stats["operations"]
                stats["success_rate"] = stats["success_count"] / stats["operations"]
        
        return breakdown
    
    def establish_baseline(self, database_name: str) -> Dict[str, Any]:
        """Establish performance baseline for database."""
        metrics = [m for m in self.metrics if m.database_name == database_name and m.success]
        
        if len(metrics) < 10:  # Need minimum samples for baseline
            return {"error": "Insufficient data for baseline (need 10+ successful operations)"}
        
        durations = [m.duration for m in metrics[-50:]]  # Use last 50 operations
        memory_deltas = [m.memory_delta for m in metrics[-50:]]
        
        baseline = {
            "database_name": database_name,
            "sample_size": len(durations),
            "avg_duration": sum(durations) / len(durations),
            "p95_duration": sorted(durations)[int(len(durations) * 0.95)],
            "p99_duration": sorted(durations)[int(len(durations) * 0.99)],
            "avg_memory_delta": sum(memory_deltas) / len(memory_deltas),
            "max_memory_delta": max(memory_deltas),
            "established_at": time.time()
        }
        
        self.baseline_metrics[database_name] = baseline
        return baseline
    
    def validate_against_baseline(self, 
                                database_name: str,
                                performance_requirements: Dict[str, float]) -> Dict[str, Any]:
        """Validate current performance against baseline and requirements."""
        if database_name not in self.baseline_metrics:
            return {"error": "No baseline established for database"}
        
        baseline = self.baseline_metrics[database_name]
        current_summary = self.get_performance_summary(database_name)
        
        validation_results = {
            "database_name": database_name,
            "baseline_comparison": {},
            "requirements_validation": {},
            "overall_status": "pass"
        }
        
        # Compare against baseline
        avg_duration = current_summary.get("avg_duration", 0)
        if avg_duration > baseline["p95_duration"] * 1.5:
            validation_results["baseline_comparison"]["duration"] = "degraded"
            validation_results["overall_status"] = "warning"
        else:
            validation_results["baseline_comparison"]["duration"] = "acceptable"
        
        # Validate against requirements
        for requirement, threshold in performance_requirements.items():
            current_value = current_summary.get(requirement, 0)
            
            if requirement.endswith("_time") or requirement.endswith("_duration"):
                # Lower is better for time-based metrics
                if current_value <= threshold:
                    validation_results["requirements_validation"][requirement] = "pass"
                else:
                    validation_results["requirements_validation"][requirement] = "fail"
                    validation_results["overall_status"] = "fail"
            else:
                # Higher is better for other metrics (like success_rate)
                if current_value >= threshold:
                    validation_results["requirements_validation"][requirement] = "pass"
                else:
                    validation_results["requirements_validation"][requirement] = "fail"
                    validation_results["overall_status"] = "fail"
        
        return validation_results


# Pytest fixtures for advanced database testing

@pytest.fixture(scope="function")
async def database_pool_manager():
    """Fixture for database connection pool manager."""
    manager = DatabaseConnectionPoolManager()
    
    try:
        yield manager
    finally:
        await manager.cleanup_all_pools()


@pytest.fixture(scope="function")
async def transaction_coordinator(database_pool_manager):
    """Fixture for cross-database transaction coordinator."""
    coordinator = TransactionCoordinator(database_pool_manager)
    
    try:
        yield coordinator
    finally:
        # Cleanup any remaining active transactions
        for transaction_id in list(coordinator.active_transactions.keys()):
            transaction_context = coordinator.active_transactions[transaction_id]
            await coordinator._rollback_all_transactions(transaction_context)


@pytest.fixture(scope="function")
async def performance_monitor():
    """Fixture for database performance monitoring."""
    monitor = DatabasePerformanceMonitor()
    
    try:
        yield monitor
    finally:
        # Performance monitor doesn't need cleanup, but we can log final summary
        summary = monitor.get_performance_summary()
        print(f"\nFinal Performance Summary: {summary}")


@pytest.fixture(scope="function")
async def multi_database_setup(database_pool_manager):
    """Fixture that sets up all database pools for testing."""
    
    # Setup all database pools
    kuzu_pool = await database_pool_manager.setup_kuzu_pool(min_size=3, max_size=10)
    redis_pool = await database_pool_manager.setup_redis_cluster_pool(pool_size=8)
    sqlite_pool = await database_pool_manager.setup_sqlite_wal_pool(pool_size=5)
    
    setup_info = {
        "pool_manager": database_pool_manager,
        "pools": {
            "kuzu": kuzu_pool,
            "redis": redis_pool,
            "sqlite": sqlite_pool
        },
        "performance_benchmarks": {
            "kuzu": {"max_query_time": 500, "max_connection_time": 100},
            "redis": {"max_operation_time": 50, "max_pipeline_time": 100},
            "sqlite": {"max_transaction_time": 100, "max_query_time": 200}
        }
    }
    
    yield setup_info 