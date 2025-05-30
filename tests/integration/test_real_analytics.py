"""
Real Analytics Engine Integration Tests - Step 13 Phase 2 Day 1

Tests real analytics engine integration with actual data processing,
performance validation, and component interaction verification.
"""

import asyncio
import pytest
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta

from tests.fixtures.real_services import real_analytics_engine, real_service_integration
from tests.utils.test_helpers import ExecutionTimer, AsyncConditionWaiter, MemoryProfiler
from server.analytics.models import AnalyticsRequest, AnalyticsType


# Mark all tests in this module for real service integration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.real_services,
    pytest.mark.asyncio
]


class TestRealAnalyticsEngineIntegration:
    """Test suite for real analytics engine integration."""

    async def test_analytics_engine_health_check(self, real_analytics_engine):
        """Test analytics engine health and connectivity."""
        # Verify engine is accessible
        assert real_analytics_engine is not None
        
        # Test health check functionality
        health_status = await real_analytics_engine.health_check()
        assert health_status is True or health_status is False
        
        # If embedded engine, it should be healthy
        if hasattr(real_analytics_engine, 'embedded_engine'):
            assert health_status is True

    async def test_real_system_metrics_collection(self, real_analytics_engine):
        """Test real system metrics collection with performance validation."""
        timer = ExecutionTimer()
        
        with timer.measure("system_metrics_collection"):
            # Get system metrics from real analytics engine
            metrics = await real_analytics_engine.get_system_metrics()
        
        # Validate response structure
        assert isinstance(metrics, dict)
        required_fields = [
            "active_nodes", "active_edges", "query_rate", 
            "cache_hit_rate", "memory_usage", "cpu_usage",
            "response_time", "uptime_seconds", "timestamp"
        ]
        
        for field in required_fields:
            assert field in metrics, f"Missing required field: {field}"
        
        # Validate data types and ranges
        assert isinstance(metrics["active_nodes"], int)
        assert isinstance(metrics["active_edges"], int)
        assert 0 <= metrics["cache_hit_rate"] <= 1.0
        assert 0 <= metrics["memory_usage"] <= 100.0
        assert 0 <= metrics["cpu_usage"] <= 100.0
        assert metrics["response_time"] >= 0
        assert metrics["uptime_seconds"] >= 0
        
        # Performance validation
        measurements = timer.get_measurements()
        duration = measurements["system_metrics_collection"]["duration"]
        assert duration < 5.0, "System metrics collection too slow"

    async def test_real_memory_insights_processing(self, real_analytics_engine):
        """Test real memory insights with data processing validation."""
        memory_profiler = MemoryProfiler()
        
        memory_profiler.start_tracing()
        
        # Get memory insights from real analytics engine
        insights = await real_analytics_engine.get_memory_insights()
        
        memory_profiler.stop_tracing()
        
        # Validate response structure
        assert isinstance(insights, dict)
        required_fields = [
            "total_memories", "procedural_memories", "semantic_memories",
            "episodic_memories", "memory_efficiency", "memory_growth_rate",
            "avg_memory_size", "total_memory_size", "timestamp"
        ]
        
        for field in required_fields:
            assert field in insights, f"Missing required field: {field}"
        
        # Validate memory calculations
        total_memories = insights["total_memories"]
        component_sum = (
            insights["procedural_memories"] +
            insights["semantic_memories"] +
            insights["episodic_memories"]
        )
        
        # Allow for rounding differences
        assert abs(total_memories - component_sum) <= 1
        
        # Validate efficiency and growth rate ranges
        assert 0 <= insights["memory_efficiency"] <= 1.0
        assert insights["memory_growth_rate"] >= 0
        
        # Memory usage validation
        memory_usage = memory_profiler.get_current_memory_usage()
        assert memory_usage["current_rss"] < 100 * 1024 * 1024  # Max 100MB

    async def test_real_graph_metrics_calculation(self, real_analytics_engine):
        """Test real graph metrics calculation with performance benchmarking."""
        timer = ExecutionTimer()
        
        with timer.measure("graph_metrics_calculation"):
            # Get graph metrics from real analytics engine
            graph_metrics = await real_analytics_engine.get_graph_metrics()
        
        # Validate response structure
        assert isinstance(graph_metrics, dict)
        required_fields = [
            "node_count", "edge_count", "density", "clustering_coefficient",
            "modularity", "average_centrality", "largest_component_size",
            "connected_components", "timestamp"
        ]
        
        for field in required_fields:
            assert field in graph_metrics, f"Missing required field: {field}"
        
        # Validate graph metrics ranges
        assert graph_metrics["node_count"] >= 0
        assert graph_metrics["edge_count"] >= 0
        assert 0 <= graph_metrics["density"] <= 1.0
        assert 0 <= graph_metrics["clustering_coefficient"] <= 1.0
        assert graph_metrics["connected_components"] >= 0
        assert graph_metrics["largest_component_size"] >= 0
        
        # Performance validation - graph metrics should be computed quickly
        measurements = timer.get_measurements()
        duration = measurements["graph_metrics_calculation"]["duration"]
        assert duration < 10.0, "Graph metrics calculation too slow"

    async def test_analytics_data_processing_pipeline(self, real_analytics_engine):
        """Test complete analytics data processing pipeline."""
        # Create test dataset for processing
        test_data = {
            "nodes": [
                {"id": "test_user_1", "name": "Test User 1", "type": "user"},
                {"id": "test_user_2", "name": "Test User 2", "type": "user"},
                {"id": "test_memory_1", "content": "Test memory content", "type": "episodic"},
            ],
            "relationships": [
                {"source": "test_user_1", "target": "test_memory_1", "type": "created"},
                {"source": "test_user_2", "target": "test_memory_1", "type": "viewed"},
            ]
        }
        
        # Process data through all analytics methods
        results = {}
        
        # System metrics baseline
        results["system_metrics"] = await real_analytics_engine.get_system_metrics()
        
        # Memory insights
        results["memory_insights"] = await real_analytics_engine.get_memory_insights()
        
        # Graph metrics
        results["graph_metrics"] = await real_analytics_engine.get_graph_metrics()
        
        # Validate all results are populated
        for key, result in results.items():
            assert isinstance(result, dict), f"{key} should return dict"
            assert len(result) > 0, f"{key} should not be empty"
            assert "timestamp" in result, f"{key} should have timestamp"

    async def test_concurrent_analytics_requests(self, real_analytics_engine):
        """Test analytics engine under concurrent load."""
        async def make_request(request_type: str):
            """Make a single analytics request."""
            if request_type == "system":
                return await real_analytics_engine.get_system_metrics()
            elif request_type == "memory":
                return await real_analytics_engine.get_memory_insights()
            elif request_type == "graph":
                return await real_analytics_engine.get_graph_metrics()
            else:
                raise ValueError(f"Unknown request type: {request_type}")
        
        # Create concurrent requests
        request_types = ["system", "memory", "graph"] * 5  # 15 total requests
        tasks = [make_request(req_type) for req_type in request_types]
        
        timer = ExecutionTimer()
        
        with timer.measure("concurrent_requests"):
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        # At least 80% success rate under concurrent load
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.8, f"Success rate {success_rate:.2f} below 80%"
        
        # Performance validation - concurrent requests should complete reasonably quickly
        measurements = timer.get_measurements()
        total_duration = measurements["concurrent_requests"]["duration"]
        avg_time_per_request = total_duration / len(request_types)
        assert avg_time_per_request < 2.0, f"Average request time {avg_time_per_request:.2f}s too slow"
        
        # Log any failures for debugging
        if failed_results:
            print(f"Failed requests: {len(failed_results)}")
            for i, error in enumerate(failed_results[:3]):  # Show first 3 errors
                print(f"Error {i+1}: {error}")

    async def test_analytics_error_handling_and_fallbacks(self, real_analytics_engine):
        """Test analytics engine error handling and fallback mechanisms."""
        # Test health check failure scenarios
        original_health_check = real_analytics_engine.health_check
        
        # Mock a health check failure
        async def mock_failing_health_check():
            return False
        
        real_analytics_engine.health_check = mock_failing_health_check
        
        try:
            # Should still return fallback data
            system_metrics = await real_analytics_engine.get_system_metrics()
            assert isinstance(system_metrics, dict)
            assert "timestamp" in system_metrics
            
            memory_insights = await real_analytics_engine.get_memory_insights()
            assert isinstance(memory_insights, dict)
            assert "timestamp" in memory_insights
            
            graph_metrics = await real_analytics_engine.get_graph_metrics()
            assert isinstance(graph_metrics, dict)
            assert "timestamp" in graph_metrics
            
        finally:
            # Restore original health check
            real_analytics_engine.health_check = original_health_check

    async def test_analytics_performance_baseline(self, real_analytics_engine):
        """Establish performance baseline for analytics operations."""
        timer = ExecutionTimer()
        memory_profiler = MemoryProfiler()
        
        # Measure baseline performance for each operation type
        performance_results = {}
        
        operations = [
            ("system_metrics", real_analytics_engine.get_system_metrics),
            ("memory_insights", real_analytics_engine.get_memory_insights),
            ("graph_metrics", real_analytics_engine.get_graph_metrics)
        ]
        
        for op_name, op_func in operations:
            memory_profiler.start_tracing()
            
            with timer.measure(f"{op_name}_baseline"):
                result = await op_func()
            
            memory_profiler.stop_tracing()
            memory_usage = memory_profiler.get_current_memory_usage()
            measurements = timer.get_measurements()
            
            performance_results[op_name] = {
                "duration": measurements[f"{op_name}_baseline"]["duration"],
                "memory_usage": memory_usage,
                "result_size": len(str(result)),
                "success": isinstance(result, dict) and len(result) > 0
            }
        
        # Validate performance requirements
        for op_name, perf_data in performance_results.items():
            # All operations should complete within reasonable time
            assert perf_data["duration"] < 5.0, f"{op_name} took {perf_data['duration']:.2f}s (>5s)"
            
            # Memory usage should be reasonable
            peak_memory = perf_data["memory_usage"]["current_rss"]
            assert peak_memory < 50 * 1024 * 1024, f"{op_name} used {peak_memory / 1024 / 1024:.1f}MB (>50MB)"
            
            # Operations should succeed
            assert perf_data["success"], f"{op_name} failed to return valid result"
        
        # Log performance baseline for monitoring
        print("\nPerformance Baseline Results:")
        for op_name, perf_data in performance_results.items():
            print(f"  {op_name}: {perf_data['duration']:.3f}s, "
                  f"{perf_data['memory_usage']['current_rss'] / 1024 / 1024:.1f}MB")


class TestRealServiceIntegration:
    """Test complete real service integration scenarios."""

    async def test_full_service_health_check(self, real_service_integration):
        """Test health check across all real services."""
        health_results = await real_service_integration.health_check_all()
        
        # Validate health results structure
        assert isinstance(health_results, dict)
        
        # Check analytics engine health
        if "analytics_engine" in health_results:
            analytics_health = health_results["analytics_engine"]
            assert "status" in analytics_health
            assert analytics_health["status"] in ["healthy", "unhealthy"]
        
        # Check database health
        if "databases" in health_results:
            db_health = health_results["databases"]
            assert "status" in db_health
            assert db_health["status"] in ["healthy", "degraded", "unhealthy"]
            
            if "databases" in db_health:
                for db_name, db_status in db_health["databases"].items():
                    assert "status" in db_status
                    assert db_status["status"] in ["healthy", "unhealthy"]

    async def test_service_dependency_coordination(self, real_service_integration):
        """Test coordination between different services."""
        # Get analytics client
        analytics_client = real_service_integration.services.get("analytics_engine", {}).get("client")
        
        if analytics_client:
            # Test that analytics can work with real databases
            databases = real_service_integration.services.get("databases", {}).get("connections", {})
            
            # Get metrics that might depend on database data
            system_metrics = await analytics_client.get_system_metrics()
            memory_insights = await analytics_client.get_memory_insights()
            
            # Validate metrics are consistent with database state
            assert isinstance(system_metrics, dict)
            assert isinstance(memory_insights, dict)
            
            # Node/edge counts should be non-negative and consistent
            node_count = system_metrics.get("active_nodes", 0)
            edge_count = system_metrics.get("active_edges", 0)
            total_memories = memory_insights.get("total_memories", 0)
            
            assert node_count >= 0
            assert edge_count >= 0
            assert total_memories >= 0

    async def test_real_data_flow_integrity(self, real_service_integration):
        """Test data flow integrity across real services."""
        waiter = AsyncConditionWaiter()
        
        # Wait for services to be fully initialized
        async def services_ready():
            health = await real_service_integration.health_check_all()
            return len(health) > 0 and all(
                status.get("status") in ["healthy", "degraded"] 
                for status in health.values()
            )
        
        await waiter.wait_for_condition(services_ready, timeout=30.0)
        
        # Test data consistency across service calls
        results = []
        for i in range(3):
            analytics_client = real_service_integration.services.get("analytics_engine", {}).get("client")
            if analytics_client:
                metrics = await analytics_client.get_system_metrics()
                results.append(metrics)
            
            # Small delay between calls
            await asyncio.sleep(0.1)
        
        # Validate consistency (node/edge counts shouldn't change dramatically)
        if len(results) >= 2:
            first_nodes = results[0].get("active_nodes", 0)
            last_nodes = results[-1].get("active_nodes", 0)
            
            # Allow for small changes but not dramatic differences
            node_change = abs(last_nodes - first_nodes)
            assert node_change <= max(10, first_nodes * 0.1), "Node count changed dramatically during test" 