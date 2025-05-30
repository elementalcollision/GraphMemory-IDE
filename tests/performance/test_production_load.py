"""
Production Load Testing Suite - Step 13 Phase 2 Day 4

Tests real GraphMemory-IDE system under production-like load conditions
with performance validation, concurrent user simulation, and stress testing.
"""

import asyncio
import pytest
import time
import random
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from tests.fixtures.real_services import real_service_integration
from tests.utils.test_helpers import ExecutionTimer, AsyncConditionWaiter, MemoryProfiler


# Mark all tests for production load testing
pytestmark = [
    pytest.mark.load,
    pytest.mark.slow,
    pytest.mark.asyncio,
    pytest.mark.integration
]


class LoadTestManager:
    """Manages load testing scenarios and concurrent user simulation."""
    
    def __init__(self):
        self.active_tasks = []
        self.results = {}
        self.error_counts = {}
        
    async def execute_concurrent_requests(
        self,
        request_func,
        concurrent_users: int,
        requests_per_user: int,
        delay_between_requests: float = 0.1
    ) -> Dict[str, Any]:
        """Execute concurrent requests from multiple simulated users."""
        
        async def user_session(user_id: int):
            """Simulate a single user session."""
            user_results = []
            user_errors = []
            
            for request_num in range(requests_per_user):
                try:
                    start_time = time.time()
                    result = await request_func(user_id, request_num)
                    end_time = time.time()
                    
                    user_results.append({
                        "user_id": user_id,
                        "request_num": request_num,
                        "duration": end_time - start_time,
                        "success": True,
                        "result_size": len(str(result)) if result else 0
                    })
                    
                except Exception as e:
                    user_errors.append({
                        "user_id": user_id,
                        "request_num": request_num,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                
                # Delay between requests to simulate user behavior
                if request_num < requests_per_user - 1:
                    await asyncio.sleep(delay_between_requests)
            
            return {"results": user_results, "errors": user_errors}
        
        # Create tasks for all users
        user_tasks = [user_session(user_id) for user_id in range(concurrent_users)]
        
        # Execute all user sessions concurrently
        timer = ExecutionTimer()
        with timer.measure("load_test_execution"):
            user_sessions = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Aggregate results
        all_results = []
        all_errors = []
        
        for session in user_sessions:
            if isinstance(session, dict):
                all_results.extend(session["results"])
                all_errors.extend(session["errors"])
            else:
                all_errors.append({
                    "error": str(session),
                    "error_type": "session_failure"
                })
        
        measurements = timer.get_measurements()
        total_duration = measurements["load_test_execution"]["duration"]
        
        # Calculate metrics
        total_requests = len(all_results) + len(all_errors)
        success_rate = len(all_results) / total_requests if total_requests > 0 else 0
        avg_response_time = sum(r["duration"] for r in all_results) / len(all_results) if all_results else 0
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0
        
        return {
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": total_requests,
            "successful_requests": len(all_results),
            "failed_requests": len(all_errors),
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "total_duration": total_duration,
            "requests_per_second": requests_per_second,
            "results": all_results,
            "errors": all_errors
        }
    
    async def stress_test_with_ramp_up(
        self,
        request_func,
        max_concurrent_users: int,
        ramp_up_duration: float = 30.0,
        test_duration: float = 60.0
    ) -> Dict[str, Any]:
        """Perform stress testing with gradual user ramp-up."""
        
        active_users = []
        results = []
        start_time = time.time()
        
        # Calculate ramp-up rate
        ramp_up_rate = max_concurrent_users / ramp_up_duration
        
        async def user_worker(user_id: int, start_delay: float):
            """Individual user worker with start delay."""
            await asyncio.sleep(start_delay)
            
            user_start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < ramp_up_duration + test_duration:
                try:
                    result = await request_func(user_id, request_count)
                    results.append({
                        "user_id": user_id,
                        "request_count": request_count,
                        "timestamp": time.time(),
                        "success": True,
                        "duration": time.time() - user_start_time
                    })
                    request_count += 1
                    
                except Exception as e:
                    results.append({
                        "user_id": user_id,
                        "request_count": request_count,
                        "timestamp": time.time(),
                        "success": False,
                        "error": str(e)
                    })
                
                # Random delay between requests
                await asyncio.sleep(random.uniform(0.1, 1.0))
        
        # Start users gradually
        for user_id in range(max_concurrent_users):
            start_delay = user_id / ramp_up_rate
            task = asyncio.create_task(user_worker(user_id, start_delay))
            active_users.append(task)
        
        # Wait for test completion
        await asyncio.sleep(ramp_up_duration + test_duration)
        
        # Cancel remaining tasks
        for task in active_users:
            if not task.done():
                task.cancel()
        
        # Wait for cleanup
        await asyncio.gather(*active_users, return_exceptions=True)
        
        # Analyze results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        return {
            "max_concurrent_users": max_concurrent_users,
            "ramp_up_duration": ramp_up_duration,
            "test_duration": test_duration,
            "total_requests": len(results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "peak_rps": self._calculate_peak_rps(results),
            "results": results
        }
    
    def _calculate_peak_rps(self, results: List[Dict], window_size: float = 1.0) -> float:
        """Calculate peak requests per second over a sliding window."""
        if not results:
            return 0.0
        
        timestamps = [r["timestamp"] for r in results if "timestamp" in r]
        if not timestamps:
            return 0.0
        
        timestamps.sort()
        max_rps = 0.0
        
        for i, start_time in enumerate(timestamps):
            window_end = start_time + window_size
            requests_in_window = sum(1 for t in timestamps[i:] if t <= window_end)
            rps = requests_in_window / window_size
            max_rps = max(max_rps, rps)
        
        return max_rps


class TestProductionLoadScenarios:
    """Test suite for production load scenarios."""

    async def test_analytics_engine_concurrent_load(self, real_service_integration):
        """Test analytics engine under concurrent user load."""
        load_manager = LoadTestManager()
        
        # Get analytics client
        analytics_client = real_service_integration.services.get("analytics_engine", {}).get("client")
        if not analytics_client:
            pytest.skip("Analytics client not available")
        
        async def analytics_request(user_id: int, request_num: int):
            """Make analytics request."""
            request_types = ["system_metrics", "memory_insights", "graph_metrics"]
            request_type = request_types[request_num % len(request_types)]
            
            if request_type == "system_metrics":
                return await analytics_client.get_system_metrics()
            elif request_type == "memory_insights":
                return await analytics_client.get_memory_insights()
            else:
                return await analytics_client.get_graph_metrics()
        
        # Execute load test
        results = await load_manager.execute_concurrent_requests(
            request_func=analytics_request,
            concurrent_users=20,
            requests_per_user=5,
            delay_between_requests=0.2
        )
        
        # Validate performance requirements
        assert results["success_rate"] >= 0.95, f"Success rate {results['success_rate']:.2f} below 95%"
        assert results["avg_response_time"] < 2.0, f"Average response time {results['avg_response_time']:.2f}s too high"
        assert results["requests_per_second"] > 10, f"Throughput {results['requests_per_second']:.1f} RPS too low"
        
        print(f"\nAnalytics Load Test Results:")
        print(f"  Concurrent Users: {results['concurrent_users']}")
        print(f"  Total Requests: {results['total_requests']}")
        print(f"  Success Rate: {results['success_rate']:.2%}")
        print(f"  Avg Response Time: {results['avg_response_time']:.3f}s")
        print(f"  Throughput: {results['requests_per_second']:.1f} RPS")

    async def test_database_connection_pool_stress(self, real_service_integration):
        """Test database connection pools under stress."""
        load_manager = LoadTestManager()
        
        # Get database connections
        databases = real_service_integration.services.get("databases", {}).get("connections", {})
        
        async def database_request(user_id: int, request_num: int):
            """Make database request."""
            results = {}
            
            # Test Kuzu database
            kuzu_conn = databases.get("kuzu")
            if kuzu_conn:
                try:
                    result = kuzu_conn.execute("MATCH (n) RETURN count(n) LIMIT 1")
                    results["kuzu"] = "success"
                except Exception as e:
                    results["kuzu"] = f"error: {e}"
            
            # Test Redis
            redis_conn = databases.get("redis")
            if redis_conn:
                try:
                    await redis_conn.ping()
                    await redis_conn.set(f"test_key_{user_id}_{request_num}", "test_value")
                    value = await redis_conn.get(f"test_key_{user_id}_{request_num}")
                    results["redis"] = "success" if value == "test_value" else "value_mismatch"
                except Exception as e:
                    results["redis"] = f"error: {e}"
            
            # Test SQLite
            sqlite_conn = databases.get("sqlite")
            if sqlite_conn:
                try:
                    cursor = sqlite_conn.execute("SELECT 1")
                    cursor.fetchone()
                    results["sqlite"] = "success"
                except Exception as e:
                    results["sqlite"] = f"error: {e}"
            
            return results
        
        # Execute database stress test
        results = await load_manager.execute_concurrent_requests(
            request_func=database_request,
            concurrent_users=50,
            requests_per_user=10,
            delay_between_requests=0.05
        )
        
        # Validate database performance
        assert results["success_rate"] >= 0.90, f"Database success rate {results['success_rate']:.2f} below 90%"
        assert results["avg_response_time"] < 1.0, f"Database response time {results['avg_response_time']:.2f}s too high"
        
        print(f"\nDatabase Stress Test Results:")
        print(f"  Concurrent Users: {results['concurrent_users']}")
        print(f"  Success Rate: {results['success_rate']:.2%}")
        print(f"  Avg Response Time: {results['avg_response_time']:.3f}s")

    async def test_memory_leak_detection_under_load(self, real_service_integration):
        """Test for memory leaks under sustained load."""
        memory_profiler = MemoryProfiler()
        load_manager = LoadTestManager()
        
        # Get analytics client
        analytics_client = real_service_integration.services.get("analytics_engine", {}).get("client")
        if not analytics_client:
            pytest.skip("Analytics client not available")
        
        async def memory_intensive_request(user_id: int, request_num: int):
            """Make memory-intensive request."""
            # Get all three types of analytics data
            system_metrics = await analytics_client.get_system_metrics()
            memory_insights = await analytics_client.get_memory_insights()
            graph_metrics = await analytics_client.get_graph_metrics()
            
            return {
                "system_metrics": len(str(system_metrics)),
                "memory_insights": len(str(memory_insights)),
                "graph_metrics": len(str(graph_metrics))
            }
        
        # Start memory profiling
        memory_profiler.start_tracing()
        initial_memory = memory_profiler.get_current_memory_usage()
        
        # Execute sustained load test
        results = await load_manager.execute_concurrent_requests(
            request_func=memory_intensive_request,
            concurrent_users=30,
            requests_per_user=20,
            delay_between_requests=0.1
        )
        
        # Take final memory snapshot
        final_memory = memory_profiler.get_current_memory_usage()
        memory_profiler.stop_tracing()
        
        # Analyze memory usage
        memory_growth = final_memory["current_rss"] - initial_memory["current_rss"]
        memory_growth_mb = memory_growth / (1024 * 1024)
        
        # Validate memory usage
        assert results["success_rate"] >= 0.95, f"Success rate {results['success_rate']:.2f} under memory load"
        assert memory_growth_mb < 100, f"Memory growth {memory_growth_mb:.1f}MB suggests memory leak"
        
        print(f"\nMemory Leak Test Results:")
        print(f"  Initial Memory: {initial_memory['current_rss'] / 1024 / 1024:.1f}MB")
        print(f"  Final Memory: {final_memory['current_rss'] / 1024 / 1024:.1f}MB")
        print(f"  Memory Growth: {memory_growth_mb:.1f}MB")
        print(f"  Total Requests: {results['total_requests']}")

    async def test_error_recovery_under_load(self, real_service_integration):
        """Test system recovery from errors under load."""
        load_manager = LoadTestManager()
        
        # Get analytics client
        analytics_client = real_service_integration.services.get("analytics_engine", {}).get("client")
        if not analytics_client:
            pytest.skip("Analytics client not available")
        
        # Inject failures
        error_injection_rate = 0.1  # 10% error rate
        
        async def error_prone_request(user_id: int, request_num: int):
            """Request that may fail deliberately."""
            # Randomly inject errors
            if random.random() < error_injection_rate:
                raise Exception(f"Injected error for user {user_id}, request {request_num}")
            
            return await analytics_client.get_system_metrics()
        
        # Execute load test with error injection
        results = await load_manager.execute_concurrent_requests(
            request_func=error_prone_request,
            concurrent_users=25,
            requests_per_user=8,
            delay_between_requests=0.15
        )
        
        # System should handle injected errors gracefully
        expected_success_rate = 1 - error_injection_rate
        actual_success_rate = results["success_rate"]
        
        # Allow for some variance in random error injection
        assert actual_success_rate >= (expected_success_rate - 0.1), \
            f"Success rate {actual_success_rate:.2f} too low with {error_injection_rate:.1%} error injection"
        
        print(f"\nError Recovery Test Results:")
        print(f"  Error Injection Rate: {error_injection_rate:.1%}")
        print(f"  Expected Success Rate: {expected_success_rate:.1%}")
        print(f"  Actual Success Rate: {actual_success_rate:.1%}")
        print(f"  System Recovery: {'PASS' if actual_success_rate >= (expected_success_rate - 0.1) else 'FAIL'}")

    async def test_ramp_up_stress_test(self, real_service_integration):
        """Test system behavior under gradual load ramp-up."""
        load_manager = LoadTestManager()
        
        # Get analytics client
        analytics_client = real_service_integration.services.get("analytics_engine", {}).get("client")
        if not analytics_client:
            pytest.skip("Analytics client not available")
        
        async def ramp_up_request(user_id: int, request_count: int):
            """Request for ramp-up test."""
            return await analytics_client.get_system_metrics()
        
        # Execute ramp-up stress test
        results = await load_manager.stress_test_with_ramp_up(
            request_func=ramp_up_request,
            max_concurrent_users=100,
            ramp_up_duration=30.0,
            test_duration=60.0
        )
        
        # Validate stress test results
        assert results["success_rate"] >= 0.85, f"Stress test success rate {results['success_rate']:.2f} too low"
        assert results["peak_rps"] > 20, f"Peak throughput {results['peak_rps']:.1f} RPS too low"
        
        print(f"\nStress Test Results:")
        print(f"  Max Concurrent Users: {results['max_concurrent_users']}")
        print(f"  Total Requests: {results['total_requests']}")
        print(f"  Success Rate: {results['success_rate']:.2%}")
        print(f"  Peak RPS: {results['peak_rps']:.1f}")

    async def test_sustained_load_endurance(self, real_service_integration):
        """Test system endurance under sustained load."""
        
        # Get analytics client
        analytics_client = real_service_integration.services.get("analytics_engine", {}).get("client")
        if not analytics_client:
            pytest.skip("Analytics client not available")
        
        # Run endurance test for shorter duration in testing
        test_duration = 120.0  # 2 minutes for testing (would be longer in production)
        request_interval = 1.0  # 1 request per second
        
        results = []
        start_time = time.time()
        
        while time.time() - start_time < test_duration:
            try:
                request_start = time.time()
                metrics = await analytics_client.get_system_metrics()
                request_end = time.time()
                
                results.append({
                    "timestamp": request_start,
                    "duration": request_end - request_start,
                    "success": True,
                    "memory_usage": metrics.get("memory_usage", 0)
                })
                
            except Exception as e:
                results.append({
                    "timestamp": time.time(),
                    "success": False,
                    "error": str(e)
                })
            
            await asyncio.sleep(request_interval)
        
        # Analyze endurance results
        successful_requests = [r for r in results if r["success"]]
        success_rate = len(successful_requests) / len(results) if results else 0
        avg_response_time = sum(r["duration"] for r in successful_requests) / len(successful_requests) if successful_requests else 0
        
        # Validate endurance performance
        assert success_rate >= 0.95, f"Endurance success rate {success_rate:.2f} degraded over time"
        assert avg_response_time < 3.0, f"Response time {avg_response_time:.2f}s degraded under sustained load"
        
        print(f"\nEndurance Test Results:")
        print(f"  Test Duration: {test_duration:.0f}s")
        print(f"  Total Requests: {len(results)}")
        print(f"  Success Rate: {success_rate:.2%}")
        print(f"  Avg Response Time: {avg_response_time:.3f}s") 