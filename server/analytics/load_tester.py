"""
Load Testing Module for GraphMemory-IDE Analytics

This module provides comprehensive load testing capabilities for:
- API endpoint performance testing
- Database query load testing
- Real-time WebSocket connection testing
- Cache performance testing
- Memory usage under load

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import aiohttp
import asyncpg
import json

from .performance_optimizer import get_performance_optimizer


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    concurrent_users: int = 10
    test_duration_seconds: int = 60
    ramp_up_seconds: int = 10
    endpoints_to_test: List[str] = field(default_factory=list)
    request_rate_per_second: int = 5
    include_websocket_tests: bool = True
    include_database_tests: bool = True
    include_cache_tests: bool = True


@dataclass
class LoadTestResult:
    """Results from load testing."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    test_duration: float
    errors: List[str] = field(default_factory=list)


class APILoadTester:
    """Load testing for API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize the load tester."""
        self.session = aiohttp.ClientSession()
    
    async def shutdown(self) -> None:
        """Shutdown the load tester."""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Tuple[float, bool, str]:
        """Make a single request and return response time, success status, and error message."""
        start_time = time.time()
        error_msg = ""
        success = False
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                async with self.session.get(url) as response:
                    await response.text()
                    success = response.status < 400
                    if not success:
                        error_msg = f"HTTP {response.status}"
            elif method == "POST":
                async with self.session.post(url, json=data) as response:
                    await response.text()
                    success = response.status < 400
                    if not success:
                        error_msg = f"HTTP {response.status}"
            
        except Exception as e:
            error_msg = str(e)
        
        response_time = time.time() - start_time
        return response_time, success, error_msg
    
    async def _user_simulation(self, user_id: int, config: LoadTestConfig) -> List[Tuple[float, bool, str]]:
        """Simulate a single user's load testing."""
        results = []
        
        # Ramp up delay
        ramp_delay = (config.ramp_up_seconds / config.concurrent_users) * user_id
        await asyncio.sleep(ramp_delay)
        
        start_time = time.time()
        request_interval = 1.0 / config.request_rate_per_second
        
        while time.time() - start_time < config.test_duration_seconds:
            # Select random endpoint
            endpoint = random.choice(config.endpoints_to_test)
            
            # Make request
            response_time, success, error = await self._make_request(endpoint)
            results.append((response_time, success, error))
            
            # Wait for next request
            await asyncio.sleep(request_interval)
        
        return results
    
    async def run_load_test(self, config: LoadTestConfig) -> LoadTestResult:
        """Run load test with given configuration."""
        print(f"Starting API load test with {config.concurrent_users} users for {config.test_duration_seconds}s")
        
        # Start user simulations
        tasks = []
        for user_id in range(config.concurrent_users):
            task = asyncio.create_task(self._user_simulation(user_id, config))
            tasks.append(task)
        
        # Wait for all users to complete
        start_time = time.time()
        all_results = await asyncio.gather(*tasks)
        test_duration = time.time() - start_time
        
        # Aggregate results
        response_times = []
        successful_requests = 0
        failed_requests = 0
        errors = []
        
        for user_results in all_results:
            for response_time, success, error in user_results:
                response_times.append(response_time)
                if success:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    if error:
                        errors.append(error)
        
        total_requests = successful_requests + failed_requests
        
        # Calculate statistics
        if response_times:
            response_times.sort()
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = response_times[int(len(response_times) * 0.95)]
            p99_response_time = response_times[int(len(response_times) * 0.99)]
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = p99_response_time = 0
        
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Get performance metrics
        performance_optimizer = get_performance_optimizer()
        memory_usage = 0.0
        cpu_usage = 0.0
        
        if performance_optimizer:
            metrics = performance_optimizer.get_current_metrics()
            memory_usage = metrics.memory_usage
        
        return LoadTestResult(
            test_name="API Load Test",
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            test_duration=test_duration,
            errors=list(set(errors))  # Unique errors
        )


class DatabaseLoadTester:
    """Load testing for database operations."""
    
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.db_pool = db_pool
    
    async def _execute_query(self, query: str, params: List[Any] = None) -> Tuple[float, bool, str]:
        """Execute a query and return execution time, success status, and error message."""
        start_time = time.time()
        error_msg = ""
        success = False
        
        try:
            async with self.db_pool.acquire() as conn:
                if params:
                    await conn.fetch(query, *params)
                else:
                    await conn.fetch(query)
                success = True
        except Exception as e:
            error_msg = str(e)
        
        execution_time = time.time() - start_time
        return execution_time, success, error_msg
    
    async def run_query_load_test(self, queries: List[str], config: LoadTestConfig) -> LoadTestResult:
        """Run load test on database queries."""
        print(f"Starting database load test with {len(queries)} queries")
        
        results = []
        start_time = time.time()
        
        # Create tasks for concurrent query execution
        tasks = []
        for _ in range(config.concurrent_users):
            for query in queries:
                task = asyncio.create_task(self._execute_query(query))
                tasks.append(task)
        
        # Execute all queries
        all_results = await asyncio.gather(*tasks)
        test_duration = time.time() - start_time
        
        # Process results
        execution_times = []
        successful_queries = 0
        failed_queries = 0
        errors = []
        
        for execution_time, success, error in all_results:
            execution_times.append(execution_time)
            if success:
                successful_queries += 1
            else:
                failed_queries += 1
                if error:
                    errors.append(error)
        
        total_queries = successful_queries + failed_queries
        
        # Calculate statistics
        if execution_times:
            execution_times.sort()
            avg_execution_time = sum(execution_times) / len(execution_times)
            min_execution_time = min(execution_times)
            max_execution_time = max(execution_times)
            p95_execution_time = execution_times[int(len(execution_times) * 0.95)]
            p99_execution_time = execution_times[int(len(execution_times) * 0.99)]
        else:
            avg_execution_time = min_execution_time = max_execution_time = p95_execution_time = p99_execution_time = 0
        
        queries_per_second = total_queries / test_duration if test_duration > 0 else 0
        error_rate = (failed_queries / total_queries * 100) if total_queries > 0 else 0
        
        return LoadTestResult(
            test_name="Database Load Test",
            total_requests=total_queries,
            successful_requests=successful_queries,
            failed_requests=failed_queries,
            avg_response_time=avg_execution_time,
            min_response_time=min_execution_time,
            max_response_time=max_execution_time,
            p95_response_time=p95_execution_time,
            p99_response_time=p99_execution_time,
            requests_per_second=queries_per_second,
            error_rate=error_rate,
            memory_usage_mb=0.0,  # Would need to measure separately
            cpu_usage_percent=0.0,
            test_duration=test_duration,
            errors=list(set(errors))
        )


class WebSocketLoadTester:
    """Load testing for WebSocket connections."""
    
    def __init__(self, ws_url: str = "ws://localhost:8000/ws") -> None:
        self.ws_url = ws_url
    
    async def _websocket_client(self, client_id: int, config: LoadTestConfig) -> List[Tuple[float, bool, str]]:
        """Simulate a WebSocket client."""
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.ws_url) as ws:
                    start_time = time.time()
                    
                    while time.time() - start_time < config.test_duration_seconds:
                        # Send message
                        message_start = time.time()
                        await ws.send_str(json.dumps({
                            "type": "ping",
                            "client_id": client_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                        
                        # Wait for response
                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                            response_time = time.time() - message_start
                            
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                results.append((response_time, True, ""))
                            else:
                                results.append((response_time, False, f"Unexpected message type: {msg.type}"))
                        except asyncio.TimeoutError:
                            results.append((5.0, False, "Timeout"))
                        
                        await asyncio.sleep(1.0)  # 1 message per second
                        
        except Exception as e:
            results.append((0.0, False, str(e)))
        
        return results
    
    async def run_websocket_load_test(self, config: LoadTestConfig) -> LoadTestResult:
        """Run WebSocket load test."""
        print(f"Starting WebSocket load test with {config.concurrent_users} connections")
        
        # Start WebSocket clients
        tasks = []
        for client_id in range(config.concurrent_users):
            task = asyncio.create_task(self._websocket_client(client_id, config))
            tasks.append(task)
        
        start_time = time.time()
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        test_duration = time.time() - start_time
        
        # Process results
        response_times = []
        successful_messages = 0
        failed_messages = 0
        errors = []
        
        for client_results in all_results:
            if isinstance(client_results, Exception):
                errors.append(str(client_results))
                continue
                
            for response_time, success, error in client_results:
                response_times.append(response_time)
                if success:
                    successful_messages += 1
                else:
                    failed_messages += 1
                    if error:
                        errors.append(error)
        
        total_messages = successful_messages + failed_messages
        
        # Calculate statistics
        if response_times:
            response_times.sort()
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = response_times[int(len(response_times) * 0.95)]
            p99_response_time = response_times[int(len(response_times) * 0.99)]
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = p99_response_time = 0
        
        messages_per_second = total_messages / test_duration if test_duration > 0 else 0
        error_rate = (failed_messages / total_messages * 100) if total_messages > 0 else 0
        
        return LoadTestResult(
            test_name="WebSocket Load Test",
            total_requests=total_messages,
            successful_requests=successful_messages,
            failed_requests=failed_messages,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=messages_per_second,
            error_rate=error_rate,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            test_duration=test_duration,
            errors=list(set(errors))
        )


class LoadTestSuite:
    """Comprehensive load testing suite."""
    
    def __init__(self, db_pool: asyncpg.Pool, base_url: str = "http://localhost:8000") -> None:
        self.db_pool = db_pool
        self.api_tester = APILoadTester(base_url)
        self.db_tester = DatabaseLoadTester(db_pool)
        self.ws_tester = WebSocketLoadTester(base_url.replace("http", "ws") + "/ws")
    
    async def initialize(self) -> None:
        """Initialize all testers."""
        await self.api_tester.initialize()
    
    async def shutdown(self) -> None:
        """Shutdown all testers."""
        await self.api_tester.shutdown()
    
    async def run_comprehensive_load_test(self, config: LoadTestConfig) -> Dict[str, LoadTestResult]:
        """Run comprehensive load test suite."""
        results = {}
        
        # API Load Test
        if config.endpoints_to_test:
            print("Running API load tests...")
            results["api"] = await self.api_tester.run_load_test(config)
        
        # Database Load Test
        if config.include_database_tests:
            print("Running database load tests...")
            test_queries = [
                "SELECT COUNT(*) FROM analytics_events WHERE timestamp > NOW() - INTERVAL '1 hour'",
                "SELECT event_type, COUNT(*) FROM analytics_events GROUP BY event_type",
                "SELECT user_id, COUNT(*) FROM analytics_events WHERE user_id IS NOT NULL GROUP BY user_id LIMIT 10",
                "SELECT * FROM dashboards ORDER BY updated_at DESC LIMIT 20",
                "SELECT * FROM real_time_metrics WHERE timestamp > NOW() - INTERVAL '5 minutes'"
            ]
            results["database"] = await self.db_tester.run_query_load_test(test_queries, config)
        
        # WebSocket Load Test
        if config.include_websocket_tests:
            print("Running WebSocket load tests...")
            ws_config = LoadTestConfig(
                concurrent_users=min(config.concurrent_users, 20),  # Limit WebSocket connections
                test_duration_seconds=30,  # Shorter test for WebSocket
                ramp_up_seconds=5
            )
            results["websocket"] = await self.ws_tester.run_websocket_load_test(ws_config)
        
        return results
    
    def generate_load_test_report(self, results: Dict[str, LoadTestResult]) -> str:
        """Generate a comprehensive load test report."""
        report = []
        report.append("=" * 80)
        report.append("LOAD TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        for test_name, result in results.items():
            report.append(f"--- {test_name.upper()} LOAD TEST ---")
            report.append(f"Test Duration: {result.test_duration:.2f}s")
            report.append(f"Total Requests: {result.total_requests}")
            report.append(f"Successful: {result.successful_requests}")
            report.append(f"Failed: {result.failed_requests}")
            report.append(f"Error Rate: {result.error_rate:.2f}%")
            report.append(f"Requests/Second: {result.requests_per_second:.2f}")
            report.append("")
            report.append("Response Times:")
            report.append(f"  Average: {result.avg_response_time:.3f}s")
            report.append(f"  Minimum: {result.min_response_time:.3f}s")
            report.append(f"  Maximum: {result.max_response_time:.3f}s")
            report.append(f"  95th Percentile: {result.p95_response_time:.3f}s")
            report.append(f"  99th Percentile: {result.p99_response_time:.3f}s")
            report.append("")
            
            if result.errors:
                report.append("Errors:")
                for error in result.errors[:10]:  # Show first 10 errors
                    report.append(f"  - {error}")
                if len(result.errors) > 10:
                    report.append(f"  ... and {len(result.errors) - 10} more errors")
                report.append("")
            
            report.append("-" * 40)
            report.append("")
        
        return "\n".join(report)


# Global load test suite instance
_load_test_suite: Optional[LoadTestSuite] = None


async def initialize_load_test_suite(db_pool: asyncpg.Pool, base_url: str = "http://localhost:8000") -> None:
    """Initialize load test suite."""
    global _load_test_suite
    _load_test_suite = LoadTestSuite(db_pool, base_url)
    await _load_test_suite.initialize()


def get_load_test_suite() -> Optional[LoadTestSuite]:
    """Get load test suite instance."""
    return _load_test_suite


async def shutdown_load_test_suite() -> None:
    """Shutdown load test suite."""
    global _load_test_suite
    if _load_test_suite:
        await _load_test_suite.shutdown()
        _load_test_suite = None 