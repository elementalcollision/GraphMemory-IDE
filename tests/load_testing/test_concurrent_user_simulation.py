"""
Advanced Concurrent User Simulation for GraphMemory-IDE
=========================================================

Based on research from:
- pytest-asyncio best practices and concurrency patterns
- LoadForge concurrent testing strategies
- FastAPI production testing methodologies
- Real-world scenario testing patterns

This module implements comprehensive concurrent user simulation
for testing GraphMemory-IDE under realistic production loads.
"""

import asyncio
import time
import statistics
import psutil
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import pytest
import httpx
from fastapi.testclient import TestClient

from server.main import app
from tests.conftest import async_client, sample_memory_data


@dataclass
class LoadTestMetrics:
    """Comprehensive metrics collection for load testing."""
    
    response_times: List[float] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    status_codes: Dict[int, int] = field(default_factory=dict)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    concurrent_requests: int = 0
    total_requests: int = 0
    test_duration: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        return statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else 0.0
    
    @property
    def p99_response_time(self) -> float:
        """Calculate 99th percentile response time."""
        return statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) >= 100 else 0.0
    
    @property
    def avg_memory_usage(self) -> float:
        """Calculate average memory usage in MB."""
        return statistics.mean(self.memory_usage) if self.memory_usage else 0.0
    
    @property
    def avg_cpu_usage(self) -> float:
        """Calculate average CPU usage percentage."""
        return statistics.mean(self.cpu_usage) if self.cpu_usage else 0.0


class ConcurrentUserSimulator:
    """
    Advanced concurrent user simulator for GraphMemory-IDE testing.
    
    Implements patterns from research:
    - FastAPI concurrent testing best practices
    - Real-world load testing scenarios  
    - Production performance monitoring
    """
    
    def __init__(self, base_url: str = "http://testserver") -> None:
        self.base_url = base_url
        self.metrics = LoadTestMetrics()
        self.running = False
        
    async def simulate_user_session(
        self, 
        client: httpx.AsyncClient,
        session_id: int,
        actions: List[Dict[str, Any]],
        think_time: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Simulate a complete user session with realistic actions.
        
        Based on research from production FastAPI testing patterns.
        """
        session_results = []
        
        for action in actions:
            start_time = time.perf_counter()
            
            try:
                # Execute user action
                response = await self._execute_action(client, action)
                response_time = time.perf_counter() - start_time
                
                # Record metrics
                self.metrics.response_times.append(response_time)
                self.metrics.total_requests += 1
                
                if response.status_code < 400:
                    self.metrics.success_count += 1
                else:
                    self.metrics.error_count += 1
                
                # Track status codes
                status = response.status_code
                self.metrics.status_codes[status] = self.metrics.status_codes.get(status, 0) + 1
                
                session_results.append({
                    "session_id": session_id,
                    "action": action["name"],
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "timestamp": time.time()
                })
                
                # Realistic think time between actions
                await asyncio.sleep(think_time)
                
            except asyncio.TimeoutError:
                self.metrics.timeout_count += 1
                self.metrics.error_count += 1
                session_results.append({
                    "session_id": session_id,
                    "action": action["name"],
                    "status_code": 408,
                    "response_time": 30.0,  # Timeout threshold
                    "error": "timeout"
                })
            except Exception as e:
                self.metrics.error_count += 1
                session_results.append({
                    "session_id": session_id,
                    "action": action["name"],
                    "status_code": 500,
                    "response_time": time.perf_counter() - start_time,
                    "error": str(e)
                })
        
        return session_results
    
    async def _execute_action(self, client: httpx.AsyncClient, action: Dict[str, Any]) -> httpx.Response:
        """Execute a user action against the API."""
        method = action.get("method", "GET")
        endpoint = action["endpoint"]
        headers = action.get("headers", {})
        params = action.get("params", {})
        json_data = action.get("json", None)
        timeout = action.get("timeout", 30.0)
        
        url = f"{self.base_url}{endpoint}"
        
        if method.upper() == "GET":
            return await client.get(url, headers=headers, params=params, timeout=timeout)
        elif method.upper() == "POST":
            return await client.post(url, headers=headers, json=json_data, timeout=timeout)
        elif method.upper() == "PUT":
            return await client.put(url, headers=headers, json=json_data, timeout=timeout)
        elif method.upper() == "DELETE":
            return await client.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    async def monitor_system_resources(self, duration: float, interval: float = 1.0) -> None:
        """Monitor system resources during load testing."""
        start_time = time.time()
        
        while time.time() - start_time < duration and self.running:
            try:
                # Memory usage
                memory_info = psutil.virtual_memory()
                self.metrics.memory_usage.append(memory_info.used / 1024 / 1024)  # MB
                
                # CPU usage - ensure we get a single float value
                cpu_percent = psutil.cpu_percent(interval=0.1)
                if isinstance(cpu_percent, (int, float)):
                    self.metrics.cpu_usage.append(float(cpu_percent))
                
                await asyncio.sleep(interval)
            except Exception:
                # Continue monitoring even if individual readings fail
                pass
    
    async def run_concurrent_load_test(
        self,
        concurrent_users: int,
        user_actions: List[Dict[str, Any]],
        test_duration: float = 60.0,
        ramp_up_time: float = 10.0,
        think_time: float = 1.0
    ) -> LoadTestMetrics:
        """
        Run comprehensive concurrent load test.
        
        Implements patterns from LoadForge and production testing research.
        """
        self.running = True
        self.metrics = LoadTestMetrics()
        self.metrics.concurrent_requests = concurrent_users
        start_time = time.time()
        
        print(f"🚀 Starting load test with {concurrent_users} concurrent users")
        print(f"📊 Test duration: {test_duration}s, Ramp-up: {ramp_up_time}s")
        
        # Start system monitoring
        monitor_task = asyncio.create_task(
            self.monitor_system_resources(test_duration + ramp_up_time + 10)
        )
        
        try:
            async with httpx.AsyncClient(base_url=self.base_url) as client:
                # Create user sessions with staggered start (ramp-up)
                user_tasks = []
                ramp_delay = ramp_up_time / concurrent_users if concurrent_users > 0 else 0
                
                for user_id in range(concurrent_users):
                    # Stagger user starts for realistic ramp-up
                    await asyncio.sleep(ramp_delay)
                    
                    task = asyncio.create_task(
                        self.simulate_user_session(
                            client=client,
                            session_id=user_id,
                            actions=user_actions,
                            think_time=think_time
                        )
                    )
                    user_tasks.append(task)
                
                # Wait for test duration
                await asyncio.sleep(test_duration)
                
                # Cancel remaining tasks
                for task in user_tasks:
                    if not task.done():
                        task.cancel()
                
                # Collect results from completed tasks
                results = []
                for task in user_tasks:
                    try:
                        if task.done() and not task.cancelled():
                            result = await task
                            results.extend(result)
                    except Exception:
                        pass  # Individual task failures already recorded in metrics
        
        finally:
            self.running = False
            monitor_task.cancel()
        
        self.metrics.test_duration = time.time() - start_time
        
        print(f"✅ Load test completed in {self.metrics.test_duration:.2f}s")
        print(f"📈 Success rate: {self.metrics.success_rate:.1f}%")
        print(f"⚡ Avg response time: {self.metrics.avg_response_time:.3f}s")
        print(f"🎯 P95 response time: {self.metrics.p95_response_time:.3f}s")
        print(f"💾 Avg memory usage: {self.metrics.avg_memory_usage:.1f}MB")
        print(f"🔥 Avg CPU usage: {self.metrics.avg_cpu_usage:.1f}%")
        
        return self.metrics


class GraphMemoryWorkflowSimulator:
    """
    Simulate realistic GraphMemory-IDE workflows for load testing.
    
    Based on research from Cursor IDE workflow analysis and 
    real-world usage patterns.
    """
    
    @staticmethod
    def cursor_developer_workflow() -> List[Dict[str, Any]]:
        """Simulate typical Cursor developer workflow with GraphMemory-IDE."""
        return [
            {
                "name": "health_check",
                "method": "GET",
                "endpoint": "/health",
                "timeout": 5.0
            },
            {
                "name": "list_projects",
                "method": "GET", 
                "endpoint": "/api/projects",
                "timeout": 10.0
            },
            {
                "name": "get_memory_graph",
                "method": "GET",
                "endpoint": "/api/memory/graph",
                "params": {"limit": 50},
                "timeout": 15.0
            },
            {
                "name": "create_memory_node",
                "method": "POST",
                "endpoint": "/api/memory/nodes",
                "json": {
                    "content": "Test memory node for load testing",
                    "type": "procedural",
                    "tags": ["load-test", "performance"]
                },
                "timeout": 10.0
            },
            {
                "name": "search_memories",
                "method": "GET",
                "endpoint": "/api/memory/search",
                "params": {"query": "load testing", "limit": 20},
                "timeout": 20.0
            },
            {
                "name": "update_memory_node",
                "method": "PUT",
                "endpoint": "/api/memory/nodes/1",
                "json": {
                    "content": "Updated memory node content",
                    "tags": ["updated", "load-test"]
                },
                "timeout": 10.0
            }
        ]
    
    @staticmethod
    def analytics_heavy_workflow() -> List[Dict[str, Any]]:
        """Simulate analytics-heavy workflow for performance testing."""
        return [
            {
                "name": "analytics_dashboard",
                "method": "GET",
                "endpoint": "/api/analytics/dashboard",
                "timeout": 30.0
            },
            {
                "name": "memory_analytics",
                "method": "GET",
                "endpoint": "/api/analytics/memory",
                "params": {"timeframe": "7d"},
                "timeout": 25.0
            },
            {
                "name": "performance_metrics",
                "method": "GET",
                "endpoint": "/api/analytics/performance",
                "timeout": 20.0
            },
            {
                "name": "export_data",
                "method": "POST",
                "endpoint": "/api/analytics/export",
                "json": {"format": "json", "date_range": "last_week"},
                "timeout": 45.0
            }
        ]


# Test Classes implementing research-driven patterns

class TestConcurrentUserSimulation:
    """Test concurrent user simulation with realistic scenarios."""
    
    @pytest.mark.asyncio
    async def test_light_concurrent_load(self) -> None:
        """Test light concurrent load (5 users) - baseline performance."""
        simulator = ConcurrentUserSimulator()
        workflow = GraphMemoryWorkflowSimulator.cursor_developer_workflow()
        
        metrics = await simulator.run_concurrent_load_test(
            concurrent_users=5,
            user_actions=workflow,
            test_duration=30.0,
            ramp_up_time=5.0,
            think_time=2.0
        )
        
        # Performance assertions based on research benchmarks
        assert metrics.success_rate >= 95.0, f"Success rate too low: {metrics.success_rate}%"
        assert metrics.avg_response_time <= 2.0, f"Average response time too high: {metrics.avg_response_time}s"
        assert metrics.p95_response_time <= 5.0, f"P95 response time too high: {metrics.p95_response_time}s"
        
        print(f"✅ Light load test passed - {metrics.success_rate:.1f}% success rate")
    
    @pytest.mark.asyncio
    async def test_moderate_concurrent_load(self) -> None:
        """Test moderate concurrent load (20 users) - typical production load."""
        simulator = ConcurrentUserSimulator()
        workflow = GraphMemoryWorkflowSimulator.cursor_developer_workflow()
        
        metrics = await simulator.run_concurrent_load_test(
            concurrent_users=20,
            user_actions=workflow,
            test_duration=60.0,
            ramp_up_time=10.0,
            think_time=1.5
        )
        
        # Moderate load performance targets
        assert metrics.success_rate >= 90.0, f"Success rate too low: {metrics.success_rate}%"
        assert metrics.avg_response_time <= 3.0, f"Average response time too high: {metrics.avg_response_time}s"
        assert metrics.p95_response_time <= 8.0, f"P95 response time too high: {metrics.p95_response_time}s"
        assert metrics.avg_memory_usage <= 1000.0, f"Memory usage too high: {metrics.avg_memory_usage}MB"
        
        print(f"✅ Moderate load test passed - {metrics.success_rate:.1f}% success rate")
    
    @pytest.mark.asyncio 
    async def test_heavy_concurrent_load(self) -> None:
        """Test heavy concurrent load (50 users) - stress testing."""
        simulator = ConcurrentUserSimulator()
        workflow = GraphMemoryWorkflowSimulator.cursor_developer_workflow()
        
        metrics = await simulator.run_concurrent_load_test(
            concurrent_users=50,
            user_actions=workflow,
            test_duration=90.0,
            ramp_up_time=15.0,
            think_time=1.0
        )
        
        # Heavy load performance targets (more lenient)
        assert metrics.success_rate >= 80.0, f"Success rate too low: {metrics.success_rate}%"
        assert metrics.avg_response_time <= 5.0, f"Average response time too high: {metrics.avg_response_time}s"
        assert metrics.p95_response_time <= 15.0, f"P95 response time too high: {metrics.p95_response_time}s"
        
        print(f"✅ Heavy load test passed - {metrics.success_rate:.1f}% success rate")
    
    @pytest.mark.asyncio
    async def test_analytics_workflow_performance(self) -> None:
        """Test analytics-heavy workflow performance."""
        simulator = ConcurrentUserSimulator()
        workflow = GraphMemoryWorkflowSimulator.analytics_heavy_workflow()
        
        metrics = await simulator.run_concurrent_load_test(
            concurrent_users=10,
            user_actions=workflow,
            test_duration=45.0,
            ramp_up_time=8.0,
            think_time=3.0
        )
        
        # Analytics workflow specific targets
        assert metrics.success_rate >= 85.0, f"Analytics success rate too low: {metrics.success_rate}%"
        assert metrics.avg_response_time <= 10.0, f"Analytics response time too high: {metrics.avg_response_time}s"
        
        print(f"✅ Analytics workflow test passed - {metrics.success_rate:.1f}% success rate")


class TestPerformanceRegression:
    """Test performance regression detection with baseline comparisons."""
    
    @pytest.mark.asyncio
    async def test_performance_baseline_comparison(self) -> None:
        """Compare current performance against established baseline."""
        # Baseline metrics from previous test runs (would be stored/loaded in real implementation)
        baseline_metrics = {
            "avg_response_time": 1.5,
            "p95_response_time": 4.0,
            "success_rate": 95.0,
            "avg_memory_usage": 500.0
        }
        
        simulator = ConcurrentUserSimulator()
        workflow = GraphMemoryWorkflowSimulator.cursor_developer_workflow()
        
        current_metrics = await simulator.run_concurrent_load_test(
            concurrent_users=15,
            user_actions=workflow,
            test_duration=30.0,
            ramp_up_time=5.0
        )
        
        # Performance regression checks (allow 20% degradation)
        degradation_threshold = 1.2
        
        response_time_ratio = current_metrics.avg_response_time / baseline_metrics["avg_response_time"]
        assert response_time_ratio <= degradation_threshold, \
            f"Response time regression detected: {response_time_ratio:.2f}x baseline"
        
        p95_ratio = current_metrics.p95_response_time / baseline_metrics["p95_response_time"]
        assert p95_ratio <= degradation_threshold, \
            f"P95 response time regression detected: {p95_ratio:.2f}x baseline"
        
        success_rate_diff = baseline_metrics["success_rate"] - current_metrics.success_rate
        assert success_rate_diff <= 5.0, \
            f"Success rate regression detected: -{success_rate_diff:.1f}%"
        
        print(f"✅ Performance regression test passed - within acceptable thresholds")


if __name__ == "__main__":
    # Run load tests directly for development/debugging
    import asyncio
    
    async def main() -> None:
        simulator = ConcurrentUserSimulator()
        workflow = GraphMemoryWorkflowSimulator.cursor_developer_workflow()
        
        print("🧪 Running development load test...")
        await simulator.run_concurrent_load_test(
            concurrent_users=10,
            user_actions=workflow,
            test_duration=30.0,
            ramp_up_time=5.0
        )
    
    asyncio.run(main()) 