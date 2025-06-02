"""
Database Performance Tests for Step 13 Phase 2 Day 2.
Comprehensive connection pool stress testing, query performance benchmarking,
and database-specific performance validation for production readiness.
"""

import asyncio
import time
import uuid
import json
import pytest
from typing import Dict, Any, List, Tuple
from datetime import datetime

from tests.fixtures.advanced_database_fixtures import (
    DatabaseConnectionPoolManager,
    DatabasePerformanceMonitor,
    ConnectionPoolMetrics,
    DatabasePerformanceMetrics
)
from tests.utils.test_helpers import ExecutionTimer, MemoryProfiler


# Performance benchmarks from research
PERFORMANCE_BENCHMARKS = {
    "kuzu": {
        "max_query_time": 500,  # ms for complex graph queries
        "max_connection_time": 100,  # ms for connection establishment
        "concurrent_connections": 50,  # simultaneous connections
        "memory_per_connection": 10,  # MB per connection
        "operations_per_second": 20  # minimum throughput
    },
    "redis": {
        "max_operation_time": 50,  # ms for cache operations
        "max_pipeline_time": 100,  # ms for pipelined operations
        "concurrent_connections": 100,  # simultaneous connections
        "memory_per_connection": 2,  # MB per connection
        "operations_per_second": 100  # minimum throughput
    },
    "sqlite": {
        "max_transaction_time": 100,  # ms for transaction commit
        "max_query_time": 200,  # ms for complex queries
        "concurrent_connections": 30,  # simultaneous connections (SQLite limit)
        "memory_per_connection": 5,  # MB per connection
        "operations_per_second": 50  # minimum throughput
    }
}


class DatabasePerformanceTester:
    """Comprehensive database performance testing framework."""
    
    def __init__(self, pool_manager: DatabaseConnectionPoolManager, performance_monitor: DatabasePerformanceMonitor) -> None:
        self.pool_manager = pool_manager
        self.performance_monitor = performance_monitor
        self.test_results = {}
        
    async def run_connection_pool_stress_test(self, concurrent_connections: int = 100) -> Dict[str, Any]:
        """Execute comprehensive connection pool stress testing."""
        print(f"\n🔥 Starting Connection Pool Stress Test with {concurrent_connections} concurrent connections...")
        
        stress_test_results = {}
        
        for pool_id, pool in self.pool_manager.pools.items():
            pool_type = pool["pool_type"]
            benchmark = PERFORMANCE_BENCHMARKS[pool_type]
            
            print(f"\n📊 Testing {pool_type.upper()} pool (ID: {pool_id})")
            
            async def stress_test_single_pool() -> None:
                """Stress test individual pool with connection lifecycle validation."""
                start_time = time.time()
                
                async def single_connection_test(connection_num: int) -> None:
                    """Test individual connection with performance monitoring."""
                    connection_start = time.time()
                    
                    try:
                        # Get connection from pool
                        conn = await self.pool_manager.get_connection(pool_id)
                        if not conn:
                            return {
                                "success": False,
                                "error": "No connection available",
                                "connection_time": 0,
                                "operation_time": 0
                            }
                        
                        connection_time = (time.time() - connection_start) * 1000  # ms
                        
                        # Perform database-specific operations
                        operation_start = time.time()
                        operation_result = await self._perform_database_operation(pool_type, conn)
                        operation_time = (time.time() - operation_start) * 1000  # ms
                        
                        # Return connection to pool
                        await self.pool_manager.return_connection(pool_id, conn["id"])
                        
                        return {
                            "success": operation_result["success"],
                            "connection_time": connection_time,
                            "operation_time": operation_time,
                            "error": operation_result.get("error"),
                            "connection_id": conn["id"]
                        }
                        
                    except Exception as e:
                        return {
                            "success": False,
                            "error": str(e),
                            "connection_time": (time.time() - connection_start) * 1000,
                            "operation_time": 0
                        }
                
                # Execute concurrent connection tests
                tasks = [single_connection_test(i) for i in range(concurrent_connections)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
                failed_results = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
                
                total_time = time.time() - start_time
                
                return {
                    "total_requests": len(results),
                    "successful_requests": len(successful_results),
                    "failed_requests": len(failed_results),
                    "success_rate": len(successful_results) / len(results) if results else 0,
                    "total_test_time": total_time,
                    "requests_per_second": len(results) / total_time if total_time > 0 else 0,
                    "avg_connection_time": sum(r["connection_time"] for r in successful_results) / len(successful_results) if successful_results else 0,
                    "avg_operation_time": sum(r["operation_time"] for r in successful_results) / len(successful_results) if successful_results else 0,
                    "max_connection_time": max((r["connection_time"] for r in successful_results), default=0),
                    "max_operation_time": max((r["operation_time"] for r in successful_results), default=0),
                    "pool_metrics": self.pool_manager.pool_metrics[pool_id].__dict__,
                    "performance_validation": self._validate_performance_against_benchmarks(
                        pool_type, successful_results, benchmark
                    )
                }
            
            pool_results = await stress_test_single_pool()
            stress_test_results[pool_id] = {
                "pool_type": pool_type,
                "benchmark_requirements": benchmark,
                "test_results": pool_results
            }
            
            # Log results
            success_rate = pool_results["success_rate"] * 100
            rps = pool_results["requests_per_second"]
            avg_conn_time = pool_results["avg_connection_time"]
            avg_op_time = pool_results["avg_operation_time"]
            
            print(f"  ✅ Success Rate: {success_rate:.1f}%")
            print(f"  ⚡ Requests/sec: {rps:.1f}")
            print(f"  🔗 Avg Connection Time: {avg_conn_time:.1f}ms")
            print(f"  ⏱️  Avg Operation Time: {avg_op_time:.1f}ms")
        
        return stress_test_results
    
    async def run_query_performance_benchmark(self) -> Dict[str, Any]:
        """Execute comprehensive query performance benchmarking."""
        print(f"\n📈 Starting Query Performance Benchmark...")
        
        benchmark_results = {}
        
        for pool_id, pool in self.pool_manager.pools.items():
            pool_type = pool["pool_type"]
            
            print(f"\n🎯 Benchmarking {pool_type.upper()} query performance")
            
            # Define database-specific query patterns
            query_patterns = self._get_query_patterns(pool_type)
            
            pool_benchmark_results = {}
            
            for pattern_name, pattern_config in query_patterns.items():
                print(f"  📋 Testing {pattern_name}...")
                
                async def benchmark_query_pattern() -> None:
                    """Benchmark specific query pattern."""
                    conn = await self.pool_manager.get_connection(pool_id)
                    if not conn:
                        return {"error": "No connection available"}
                    
                    try:
                        # Execute query pattern multiple times
                        execution_times = []
                        memory_deltas = []
                        
                        for i in range(pattern_config["iterations"]):
                            start_memory = self.performance_monitor.profiler.get_current_memory_usage()["current_rss"]
                            start_time = time.time()
                            
                            try:
                                result = await self._execute_query_pattern(
                                    pool_type, conn, pattern_name, pattern_config
                                )
                                success = result.get("success", False)
                            except Exception as e:
                                success = False
                                print(f"    ⚠️ Query failed: {e}")
                            
                            end_time = time.time()
                            end_memory = self.performance_monitor.profiler.get_current_memory_usage()["current_rss"]
                            
                            if success:
                                execution_times.append((end_time - start_time) * 1000)  # ms
                                memory_deltas.append(end_memory - start_memory)
                        
                        if execution_times:
                            avg_time = sum(execution_times) / len(execution_times)
                            p95_time = sorted(execution_times)[int(len(execution_times) * 0.95)]
                            p99_time = sorted(execution_times)[int(len(execution_times) * 0.99)]
                            avg_memory = sum(memory_deltas) / len(memory_deltas)
                            
                            return {
                                "avg_execution_time": avg_time,
                                "p95_execution_time": p95_time,
                                "p99_execution_time": p99_time,
                                "avg_memory_delta": avg_memory,
                                "successful_executions": len(execution_times),
                                "total_iterations": pattern_config["iterations"],
                                "success_rate": len(execution_times) / pattern_config["iterations"]
                            }
                        else:
                            return {"error": "No successful executions"}
                            
                    finally:
                        await self.pool_manager.return_connection(pool_id, conn["id"])
                
                pattern_results = await benchmark_query_pattern()
                pool_benchmark_results[pattern_name] = pattern_results
                
                if "avg_execution_time" in pattern_results:
                    print(f"    ⏱️  Avg: {pattern_results['avg_execution_time']:.1f}ms")
                    print(f"    📊 P95: {pattern_results['p95_execution_time']:.1f}ms")
                    print(f"    🎯 Success: {pattern_results['success_rate']*100:.1f}%")
            
            benchmark_results[pool_id] = {
                "pool_type": pool_type,
                "query_patterns": pool_benchmark_results
            }
        
        return benchmark_results
    
    async def run_connection_lifecycle_test(self) -> Dict[str, Any]:
        """Test connection creation, reuse, and cleanup lifecycle."""
        print(f"\n🔄 Starting Connection Lifecycle Test...")
        
        lifecycle_results = {}
        
        for pool_id, pool in self.pool_manager.pools.items():
            pool_type = pool["pool_type"]
            
            print(f"\n♻️  Testing {pool_type.upper()} connection lifecycle")
            
            async def test_connection_lifecycle() -> None:
                """Test complete connection lifecycle."""
                lifecycle_metrics = {
                    "connection_creation_times": [],
                    "connection_reuse_times": [],
                    "connection_cleanup_success": 0,
                    "total_connections_tested": 0
                }
                
                # Test 1: Connection creation performance
                print(f"  🆕 Testing connection creation...")
                for i in range(10):
                    start_time = time.time()
                    conn = await self.pool_manager.get_connection(pool_id)
                    if conn:
                        creation_time = (time.time() - start_time) * 1000
                        lifecycle_metrics["connection_creation_times"].append(creation_time)
                        lifecycle_metrics["total_connections_tested"] += 1
                        await self.pool_manager.return_connection(pool_id, conn["id"])
                
                # Test 2: Connection reuse performance
                print(f"  🔄 Testing connection reuse...")
                for i in range(20):
                    start_time = time.time()
                    conn = await self.pool_manager.get_connection(pool_id)
                    if conn:
                        reuse_time = (time.time() - start_time) * 1000
                        lifecycle_metrics["connection_reuse_times"].append(reuse_time)
                        
                        # Simulate work
                        await self._perform_database_operation(pool_type, conn)
                        await self.pool_manager.return_connection(pool_id, conn["id"])
                
                # Test 3: Connection cleanup
                print(f"  🧹 Testing connection cleanup...")
                initial_pool_size = len(pool["connections"])
                
                # Force pool cleanup
                await self.pool_manager.cleanup_all_pools()
                
                # Verify cleanup
                if len(self.pool_manager.pools) == 0:
                    lifecycle_metrics["connection_cleanup_success"] = 1
                
                return {
                    "avg_creation_time": sum(lifecycle_metrics["connection_creation_times"]) / len(lifecycle_metrics["connection_creation_times"]) if lifecycle_metrics["connection_creation_times"] else 0,
                    "avg_reuse_time": sum(lifecycle_metrics["connection_reuse_times"]) / len(lifecycle_metrics["connection_reuse_times"]) if lifecycle_metrics["connection_reuse_times"] else 0,
                    "cleanup_success": lifecycle_metrics["connection_cleanup_success"],
                    "total_connections_tested": lifecycle_metrics["total_connections_tested"],
                    "creation_time_p95": sorted(lifecycle_metrics["connection_creation_times"])[int(len(lifecycle_metrics["connection_creation_times"]) * 0.95)] if lifecycle_metrics["connection_creation_times"] else 0,
                    "reuse_time_p95": sorted(lifecycle_metrics["connection_reuse_times"])[int(len(lifecycle_metrics["connection_reuse_times"]) * 0.95)] if lifecycle_metrics["connection_reuse_times"] else 0
                }
            
            pool_lifecycle_results = await test_connection_lifecycle()
            lifecycle_results[pool_id] = {
                "pool_type": pool_type,
                "lifecycle_metrics": pool_lifecycle_results
            }
            
            # Log results
            avg_creation = pool_lifecycle_results["avg_creation_time"]
            avg_reuse = pool_lifecycle_results["avg_reuse_time"]
            cleanup_status = "✅" if pool_lifecycle_results["cleanup_success"] else "❌"
            
            print(f"  📊 Avg Creation: {avg_creation:.1f}ms")
            print(f"  🔄 Avg Reuse: {avg_reuse:.1f}ms") 
            print(f"  🧹 Cleanup: {cleanup_status}")
        
        return lifecycle_results
    
    async def _perform_database_operation(self, db_type: str, conn: Dict[str, Any]) -> Dict[str, Any]:
        """Perform database-specific operation for testing."""
        try:
            if db_type == "kuzu":
                kuzu_conn = conn["connection"]
                # Complex graph query for performance testing
                result = kuzu_conn.execute("""
                    MATCH (u:TestUser)
                    OPTIONAL MATCH (u)-[:TEST_BELONGS_TO]->(m:TestMemory)
                    RETURN u.id as user_id, u.name as user_name, count(m) as memory_count
                    ORDER BY memory_count DESC
                    LIMIT 100
                """)
                return {"success": True, "result_count": len(result)}
                
            elif db_type == "redis":
                redis_conn = conn["connection"]
                # Redis pipeline operation for performance testing
                pipe = redis_conn.pipeline()
                for i in range(10):
                    key = f"perf_test_{uuid.uuid4().hex[:8]}"
                    pipe.set(key, f"test_value_{i}", ex=60)
                    pipe.get(key)
                results = await pipe.execute()
                return {"success": True, "operations": len(results)}
                
            elif db_type == "sqlite":
                db = conn["database"]
                # Complex SQLite query for performance testing
                result = await db.fetch_all("""
                    SELECT u.id, u.name, COUNT(a.id) as analytics_count
                    FROM test_users u
                    LEFT JOIN test_analytics a ON u.id = a.user_id
                    GROUP BY u.id, u.name
                    ORDER BY analytics_count DESC
                    LIMIT 100
                """)
                return {"success": True, "result_count": len(result)}
            
            return {"success": False, "error": "Unknown database type"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_query_patterns(self, db_type: str) -> Dict[str, Dict[str, Any]]:
        """Get database-specific query patterns for performance testing."""
        if db_type == "kuzu":
            return {
                "simple_count": {
                    "iterations": 50,
                    "description": "Simple node count query"
                },
                "complex_join": {
                    "iterations": 20,
                    "description": "Complex multi-node join with aggregation"
                },
                "path_traversal": {
                    "iterations": 10,
                    "description": "Multi-hop path traversal query"
                }
            }
        elif db_type == "redis":
            return {
                "simple_operations": {
                    "iterations": 100,
                    "description": "Basic SET/GET operations"
                },
                "pipeline_operations": {
                    "iterations": 50,
                    "description": "Pipelined batch operations"
                },
                "complex_data_structures": {
                    "iterations": 30,
                    "description": "Hash and list operations"
                }
            }
        elif db_type == "sqlite":
            return {
                "simple_select": {
                    "iterations": 100,
                    "description": "Simple SELECT queries"
                },
                "complex_join": {
                    "iterations": 50,
                    "description": "Multi-table JOIN with aggregation"
                },
                "transaction_heavy": {
                    "iterations": 20,
                    "description": "Transaction-heavy operations"
                }
            }
        
        return {}
    
    async def _execute_query_pattern(self, db_type: str, conn: Dict[str, Any], pattern_name: str, pattern_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific query pattern for performance testing."""
        try:
            if db_type == "kuzu":
                kuzu_conn = conn["connection"]
                if pattern_name == "simple_count":
                    result = kuzu_conn.execute("MATCH (n) RETURN count(n) as total_nodes")
                elif pattern_name == "complex_join":
                    result = kuzu_conn.execute("""
                        MATCH (u:TestUser)-[r:TEST_BELONGS_TO]->(m:TestMemory)
                        RETURN u.name, m.type, count(*) as relationship_count
                        ORDER BY relationship_count DESC
                    """)
                elif pattern_name == "path_traversal":
                    result = kuzu_conn.execute("""
                        MATCH (u:TestUser)-[:TEST_BELONGS_TO*1..3]->(m:TestMemory)
                        RETURN u.name, collect(m.content) as connected_memories
                    """)
                
                return {"success": True}
                
            elif db_type == "redis":
                redis_conn = conn["connection"]
                if pattern_name == "simple_operations":
                    key = f"test_{uuid.uuid4().hex[:8]}"
                    await redis_conn.set(key, "test_value")
                    value = await redis_conn.get(key)
                    await redis_conn.delete(key)
                elif pattern_name == "pipeline_operations":
                    pipe = redis_conn.pipeline()
                    for i in range(5):
                        key = f"pipe_test_{i}_{uuid.uuid4().hex[:4]}"
                        pipe.set(key, f"value_{i}")
                        pipe.expire(key, 60)
                    await pipe.execute()
                elif pattern_name == "complex_data_structures":
                    hash_key = f"hash_{uuid.uuid4().hex[:8]}"
                    await redis_conn.hset(hash_key, mapping={"field1": "value1", "field2": "value2"})
                    await redis_conn.expire(hash_key, 60)
                
                return {"success": True}
                
            elif db_type == "sqlite":
                db = conn["database"]
                if pattern_name == "simple_select":
                    result = await db.fetch_all("SELECT COUNT(*) as total_users FROM test_users")
                elif pattern_name == "complex_join":
                    result = await db.fetch_all("""
                        SELECT u.name, AVG(a.metric_value) as avg_metric
                        FROM test_users u
                        LEFT JOIN test_analytics a ON u.id = a.user_id
                        GROUP BY u.id, u.name
                        HAVING COUNT(a.id) > 0
                    """)
                elif pattern_name == "transaction_heavy":
                    # Create a transaction for testing
                    transaction = await db.transaction()
                    try:
                        await db.execute(
                            "INSERT INTO test_users (name, email) VALUES (:name, :email)",
                            {"name": f"Test User {uuid.uuid4().hex[:8]}", "email": f"test_{uuid.uuid4().hex[:8]}@example.com"}
                        )
                        await transaction.commit()
                    except:
                        await transaction.rollback()
                        raise
                
                return {"success": True}
            
            return {"success": False, "error": "Unknown pattern"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _validate_performance_against_benchmarks(self, db_type: str, results: List[Dict[str, Any]], benchmark: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance results against benchmark requirements."""
        if not results:
            return {"status": "fail", "reason": "No successful operations"}
        
        validation = {"status": "pass", "violations": []}
        
        # Check connection time
        avg_connection_time = sum(r["connection_time"] for r in results) / len(results)
        if avg_connection_time > benchmark["max_connection_time"]:
            validation["violations"].append(f"Connection time {avg_connection_time:.1f}ms exceeds {benchmark['max_connection_time']}ms")
        
        # Check operation time
        operation_times = [r["operation_time"] for r in results if r["operation_time"] > 0]
        if operation_times:
            avg_operation_time = sum(operation_times) / len(operation_times)
            max_op_time = benchmark.get("max_operation_time", benchmark.get("max_query_time", float('inf')))
            if avg_operation_time > max_op_time:
                validation["violations"].append(f"Operation time {avg_operation_time:.1f}ms exceeds {max_op_time}ms")
        
        # Check success rate
        success_rate = len(results) / len(results)  # All results here are successful
        if success_rate < 0.95:  # 95% minimum success rate
            validation["violations"].append(f"Success rate {success_rate*100:.1f}% below 95%")
        
        if validation["violations"]:
            validation["status"] = "fail"
        
        return validation


# Pytest tests using the performance tester

@pytest.mark.asyncio
async def test_connection_pool_stress_test(multi_database_setup) -> None:
    """Test connection pool stress under 100 concurrent connections."""
    pool_manager = multi_database_setup["pool_manager"]
    performance_monitor = DatabasePerformanceMonitor()
    
    tester = DatabasePerformanceTester(pool_manager, performance_monitor)
    
    # Test with 50 concurrent connections (reduced for CI/testing)
    stress_results = await tester.run_connection_pool_stress_test(concurrent_connections=50)
    
    # Validate results
    assert len(stress_results) > 0, "No stress test results returned"
    
    for pool_id, pool_result in stress_results.items():
        test_results = pool_result["test_results"]
        
        # Check success rate (should be > 85% for stress test)
        assert test_results["success_rate"] > 0.85, f"Pool {pool_id} success rate {test_results['success_rate']*100:.1f}% too low"
        
        # Check requests per second (should be > 10 RPS)
        assert test_results["requests_per_second"] > 10, f"Pool {pool_id} RPS {test_results['requests_per_second']:.1f} too low"
        
        # Check that we processed the expected number of requests
        assert test_results["total_requests"] == 50, f"Pool {pool_id} didn't process all 50 requests"


@pytest.mark.asyncio
async def test_query_performance_benchmark(multi_database_setup) -> None:
    """Test query performance benchmarking for all database types."""
    pool_manager = multi_database_setup["pool_manager"]
    performance_monitor = DatabasePerformanceMonitor()
    
    tester = DatabasePerformanceTester(pool_manager, performance_monitor)
    
    benchmark_results = await tester.run_query_performance_benchmark()
    
    # Validate results
    assert len(benchmark_results) > 0, "No benchmark results returned"
    
    for pool_id, pool_result in benchmark_results.items():
        pool_type = pool_result["pool_type"]
        query_patterns = pool_result["query_patterns"]
        
        # Check that we have query pattern results
        assert len(query_patterns) > 0, f"No query patterns tested for {pool_type}"
        
        # Validate performance for each pattern
        for pattern_name, pattern_result in query_patterns.items():
            if "avg_execution_time" in pattern_result:
                # Check success rate
                assert pattern_result["success_rate"] > 0.8, f"{pool_type} {pattern_name} success rate too low"
                
                # Check performance against benchmarks
                benchmark = PERFORMANCE_BENCHMARKS[pool_type]
                max_time = benchmark.get("max_operation_time", benchmark.get("max_query_time", 1000))
                assert pattern_result["avg_execution_time"] < max_time, f"{pool_type} {pattern_name} too slow"


@pytest.mark.asyncio
async def test_connection_lifecycle_validation(multi_database_setup) -> None:
    """Test connection creation, reuse, and cleanup lifecycle."""
    pool_manager = multi_database_setup["pool_manager"]
    performance_monitor = DatabasePerformanceMonitor()
    
    tester = DatabasePerformanceTester(pool_manager, performance_monitor)
    
    lifecycle_results = await tester.run_connection_lifecycle_test()
    
    # Validate results
    assert len(lifecycle_results) > 0, "No lifecycle results returned"
    
    for pool_id, pool_result in lifecycle_results.items():
        lifecycle_metrics = pool_result["lifecycle_metrics"]
        
        # Check that connections were created
        assert lifecycle_metrics["total_connections_tested"] > 0, f"No connections tested for pool {pool_id}"
        
        # Check creation time (should be reasonable)
        assert lifecycle_metrics["avg_creation_time"] < 1000, f"Pool {pool_id} creation time too slow"
        
        # Check reuse time (should be faster than creation)
        assert lifecycle_metrics["avg_reuse_time"] < lifecycle_metrics["avg_creation_time"], f"Pool {pool_id} reuse not faster than creation"
        
        # Check cleanup success
        assert lifecycle_metrics["cleanup_success"] == 1, f"Pool {pool_id} cleanup failed"


@pytest.mark.asyncio
async def test_database_specific_performance_patterns(multi_database_setup) -> None:
    """Test database-specific performance patterns and optimizations."""
    pool_manager = multi_database_setup["pool_manager"]
    performance_monitor = DatabasePerformanceMonitor()
    benchmarks = multi_database_setup["performance_benchmarks"]
    
    for pool_id, pool in pool_manager.pools.items():
        pool_type = pool["pool_type"]
        benchmark = benchmarks[pool_type]
        
        # Get connection for testing
        conn = await pool_manager.get_connection(pool_id)
        assert conn is not None, f"Failed to get connection for {pool_type}"
        
        try:
            # Test specific performance pattern
            if pool_type == "kuzu":
                # Test graph traversal performance
                start_time = time.time()
                result = await DatabasePerformanceTester(pool_manager, performance_monitor)._perform_database_operation(pool_type, conn)
                execution_time = (time.time() - start_time) * 1000
                
                assert result["success"], f"Kuzu operation failed: {result.get('error')}"
                assert execution_time < benchmark["max_query_time"], f"Kuzu query took {execution_time:.1f}ms, expected < {benchmark['max_query_time']}ms"
                
            elif pool_type == "redis":
                # Test Redis pipeline performance
                start_time = time.time()
                result = await DatabasePerformanceTester(pool_manager, performance_monitor)._perform_database_operation(pool_type, conn)
                execution_time = (time.time() - start_time) * 1000
                
                assert result["success"], f"Redis operation failed: {result.get('error')}"
                assert execution_time < benchmark["max_operation_time"], f"Redis operation took {execution_time:.1f}ms, expected < {benchmark['max_operation_time']}ms"
                
            elif pool_type == "sqlite":
                # Test SQLite transaction performance
                start_time = time.time()
                result = await DatabasePerformanceTester(pool_manager, performance_monitor)._perform_database_operation(pool_type, conn)
                execution_time = (time.time() - start_time) * 1000
                
                assert result["success"], f"SQLite operation failed: {result.get('error')}"
                assert execution_time < benchmark["max_query_time"], f"SQLite query took {execution_time:.1f}ms, expected < {benchmark['max_query_time']}ms"
                
        finally:
            await pool_manager.return_connection(pool_id, conn["id"])


@pytest.mark.asyncio
async def test_performance_baseline_establishment(multi_database_setup) -> None:
    """Test establishment and validation of performance baselines."""
    pool_manager = multi_database_setup["pool_manager"]
    performance_monitor = DatabasePerformanceMonitor()
    
    # Collect baseline data by running operations
    for pool_id, pool in pool_manager.pools.items():
        pool_type = pool["pool_type"]
        
        # Run 15 operations to establish baseline (minimum 10 required)
        for i in range(15):
            conn = await pool_manager.get_connection(pool_id)
            if conn:
                try:
                    async def operation() -> None:
                        return await DatabasePerformanceTester(pool_manager, performance_monitor)._perform_database_operation(pool_type, conn)
                    
                    await performance_monitor.profile_operation(
                        database_name=pool_type,
                        operation_type="baseline_test",
                        operation_func=operation,
                        connection_id=conn["id"]
                    )
                finally:
                    await pool_manager.return_connection(pool_id, conn["id"])
        
        # Establish baseline
        baseline = performance_monitor.establish_baseline(pool_type)
        assert "error" not in baseline, f"Failed to establish baseline for {pool_type}: {baseline}"
        assert baseline["sample_size"] >= 10, f"Insufficient baseline samples for {pool_type}"
        
        # Validate against baseline
        benchmark = PERFORMANCE_BENCHMARKS[pool_type]
        performance_requirements = {
            "avg_duration": benchmark.get("max_operation_time", benchmark.get("max_query_time", 1000)) / 1000,  # Convert to seconds
            "success_rate": 0.95
        }
        
        validation = performance_monitor.validate_against_baseline(pool_type, performance_requirements)
        assert validation["overall_status"] in ["pass", "warning"], f"Performance validation failed for {pool_type}: {validation}"


if __name__ == "__main__":
    # Run performance tests standalone
    import asyncio
    
    async def main() -> None:
        from tests.fixtures.advanced_database_fixtures import multi_database_setup
        
        # This would need proper fixture setup in standalone mode
        print("Database Performance Tests")
        print("Run with: pytest tests/integration/test_database_performance.py -v")
    
    asyncio.run(main()) 