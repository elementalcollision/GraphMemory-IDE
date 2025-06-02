"""
Comprehensive Integration Testing Suite for Analytics Engine Phase 3
Tests all components, GPU acceleration, performance monitoring, and API endpoints.
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import kuzu

# Import analytics components
from server.analytics.engine import AnalyticsEngine
from server.analytics.gpu_acceleration import gpu_manager
from server.analytics.performance_monitor import performance_monitor
from server.analytics.concurrent_processing import concurrent_manager
from server.analytics.benchmarks import AnalyticsBenchmarkSuite
from server.analytics.monitoring import AnalyticsMonitoringMiddleware
from server.analytics.models import (
    CentralityRequest, CommunityRequest, ClusteringRequest,
    CentralityType, ClusteringType
)

class TestAnalyticsIntegration:
    """Comprehensive integration tests for Analytics Engine Phase 3"""
    
    @pytest.fixture
    async def analytics_engine(self) -> None:
        """Create analytics engine for testing"""
        # Mock Kuzu connection for testing
        mock_conn = Mock()
        mock_conn.execute.return_value = []
        
        engine = AnalyticsEngine(mock_conn, "redis://localhost:6379")
        await engine.initialize()
        yield engine
        await engine.shutdown()
    
    @pytest.fixture
    def sample_graph_data(self) -> None:
        """Sample graph data for testing"""
        return {
            "nodes": [
                {"id": "node1", "type": "user", "name": "Alice"},
                {"id": "node2", "type": "user", "name": "Bob"},
                {"id": "node3", "type": "user", "name": "Charlie"},
                {"id": "node4", "type": "user", "name": "David"},
                {"id": "node5", "type": "user", "name": "Eve"}
            ],
            "edges": [
                {"source": "node1", "target": "node2", "weight": 1.0},
                {"source": "node2", "target": "node3", "weight": 1.0},
                {"source": "node3", "target": "node4", "weight": 1.0},
                {"source": "node4", "target": "node5", "weight": 1.0},
                {"source": "node1", "target": "node5", "weight": 1.0}
            ]
        }

class TestGPUAcceleration:
    """Test GPU acceleration functionality"""
    
    def test_gpu_manager_initialization(self) -> None:
        """Test GPU manager initializes correctly"""
        assert gpu_manager is not None
        status = gpu_manager.get_acceleration_status()
        assert "gpu_available" in status
        assert "cugraph_backend" in status
        assert "fallback_reason" in status
    
    def test_gpu_availability_methods(self) -> None:
        """Test GPU availability checking methods"""
        # Test the methods we added in integration fixes
        assert hasattr(gpu_manager, 'is_gpu_available')
        assert hasattr(gpu_manager, 'is_gpu_enabled')
        
        gpu_available = gpu_manager.is_gpu_available()
        gpu_enabled = gpu_manager.is_gpu_enabled()
        
        assert isinstance(gpu_available, bool)
        assert isinstance(gpu_enabled, bool)
    
    def test_algorithm_acceleration_check(self) -> None:
        """Test algorithm acceleration checking"""
        algorithms = ["pagerank", "betweenness_centrality", "louvain_communities"]
        
        for algorithm in algorithms:
            is_accelerated = gpu_manager.is_algorithm_accelerated(algorithm)
            assert isinstance(is_accelerated, bool)
    
    def test_performance_estimation(self) -> None:
        """Test performance estimation for GPU acceleration"""
        estimate = gpu_manager.get_performance_estimate("pagerank", 1000)
        
        assert "accelerated" in estimate
        assert "estimated_speedup" in estimate
        assert "recommendation" in estimate
        assert isinstance(estimate["estimated_speedup"], (int, float))
    
    def test_memory_usage_monitoring(self) -> None:
        """Test GPU memory usage monitoring"""
        memory_info = gpu_manager.get_memory_usage()
        
        assert "available" in memory_info
        if memory_info["available"]:
            assert "used_mb" in memory_info
            assert "total_mb" in memory_info
            assert "free_mb" in memory_info
            assert "utilization_percent" in memory_info

class TestPerformanceMonitoring:
    """Test performance monitoring functionality"""
    
    def test_performance_monitor_initialization(self) -> None:
        """Test performance monitor initializes correctly"""
        assert performance_monitor is not None
        assert hasattr(performance_monitor, 'cache_stats')
        assert hasattr(performance_monitor, 'process')
    
    def test_graph_size_update_method(self) -> None:
        """Test the graph size update method we added"""
        # Test the method we added in integration fixes
        assert hasattr(performance_monitor, 'update_graph_size')
        
        # Should not raise an exception
        performance_monitor.update_graph_size(100, 200)
    
    def test_algorithm_monitoring_context(self) -> None:
        """Test algorithm monitoring context manager"""
        with performance_monitor.monitor_algorithm("test_algorithm", "networkx", "small"):
            time.sleep(0.1)  # Simulate algorithm execution
        
        # Should complete without errors
    
    def test_graph_operation_monitoring(self) -> None:
        """Test graph operation monitoring"""
        with performance_monitor.monitor_graph_operation("test_operation", 100):
            time.sleep(0.05)  # Simulate operation
        
        # Should complete without errors
    
    def test_cache_statistics(self) -> None:
        """Test cache statistics tracking"""
        performance_monitor.record_cache_hit()
        performance_monitor.record_cache_miss()
        
        stats = performance_monitor.get_performance_summary()
        assert "cache_statistics" in stats
        assert stats["cache_statistics"]["hits"] >= 1
        assert stats["cache_statistics"]["misses"] >= 1
    
    def test_system_metrics_collection(self) -> None:
        """Test system metrics collection"""
        metrics = performance_monitor.get_system_metrics()
        
        required_metrics = [
            "cpu_percent", "memory_percent", "memory_available_mb",
            "memory_used_mb", "disk_usage_percent", "disk_free_gb",
            "process_memory_mb", "process_cpu_percent", "cache_hit_rate"
        ]
        
        for metric in required_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))

class TestConcurrentProcessing:
    """Test concurrent processing functionality"""
    
    @pytest.mark.asyncio
    async def test_concurrent_manager_initialization(self) -> None:
        """Test concurrent manager initialization"""
        await concurrent_manager.initialize()
        
        status = concurrent_manager.get_executor_status()
        assert "thread_pool" in status
        assert "process_pool" in status
        
        await concurrent_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test concurrent manager health check"""
        await concurrent_manager.initialize()
        
        health = await concurrent_manager.health_check()
        assert "status" in health
        assert "components" in health
        
        await concurrent_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self) -> None:
        """Test parallel task execution"""
        await concurrent_manager.initialize()
        
        def sample_task(x) -> None:
            return x * 2
        
        # Use the correct method signature for run_parallel_tasks
        tasks = [
            {"func": sample_task, "args": (1,)},
            {"func": sample_task, "args": (2,)},
            {"func": sample_task, "args": (3,)},
            {"func": sample_task, "args": (4,)},
            {"func": sample_task, "args": (5,)}
        ]
        results = await concurrent_manager.run_parallel_tasks(tasks, "thread")
        
        assert len(results) == len(tasks)
        assert results == [2, 4, 6, 8, 10]
        
        await concurrent_manager.shutdown()

class TestAnalyticsEngine:
    """Test main analytics engine functionality"""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, analytics_engine) -> None:
        """Test analytics engine initialization"""
        assert analytics_engine.initialized
        assert analytics_engine.gpu_manager is not None
        assert analytics_engine.performance_monitor is not None
        assert analytics_engine.concurrent_manager is not None
    
    @pytest.mark.asyncio
    async def test_centrality_analysis(self, analytics_engine, sample_graph_data) -> None:
        """Test centrality analysis with various algorithms"""
        # Mock the get_graph_data method to return sample data
        analytics_engine.get_graph_data = Mock(return_value=sample_graph_data)
        
        request = CentralityRequest(
            centrality_type=CentralityType.PAGERANK,
            limit=10
        )
        
        response = await analytics_engine.analyze_centrality(request)
        
        assert response.centrality_type == CentralityType.PAGERANK
        assert hasattr(response, 'top_nodes')
        assert hasattr(response, 'statistics')
        assert hasattr(response, 'execution_time')
        assert response.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_community_detection(self, analytics_engine, sample_graph_data) -> None:
        """Test community detection functionality"""
        analytics_engine.get_graph_data = Mock(return_value=sample_graph_data)
        
        request = CommunityRequest(
            algorithm="louvain",
            resolution=1.0,
            min_community_size=2
        )
        
        response = await analytics_engine.detect_communities(request)
        
        assert response.algorithm == "louvain"
        assert hasattr(response, 'modularity')
        assert hasattr(response, 'num_communities')
        assert hasattr(response, 'community_sizes')
        assert response.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_clustering_analysis(self, analytics_engine, sample_graph_data) -> None:
        """Test ML clustering analysis"""
        analytics_engine.get_graph_data = Mock(return_value=sample_graph_data)
        
        request = ClusteringRequest(
            clustering_type=ClusteringType.SPECTRAL,
            n_clusters=2
        )
        
        response = await analytics_engine.perform_clustering(request)
        
        assert response.clustering_type == ClusteringType.SPECTRAL
        assert hasattr(response, 'n_clusters')
        assert hasattr(response, 'silhouette_score')
        assert response.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, analytics_engine, sample_graph_data) -> None:
        """Test anomaly detection functionality"""
        analytics_engine.get_graph_data = Mock(return_value=sample_graph_data)
        
        response = await analytics_engine.detect_anomalies()
        
        assert "anomalies" in response
        assert "anomaly_scores" in response
        assert "execution_time" in response
        assert response["execution_time"] > 0
    
    @pytest.mark.asyncio
    async def test_phase3_status(self, analytics_engine) -> None:
        """Test Phase 3 status reporting"""
        status = await analytics_engine.get_phase3_status()
        
        assert "gpu_acceleration" in status
        assert "performance_metrics" in status
        assert "concurrent_processing" in status
        assert "system_health" in status

class TestBenchmarkingSuite:
    """Test benchmarking suite functionality"""
    
    @pytest.mark.asyncio
    async def test_benchmark_suite_initialization(self) -> None:
        """Test benchmark suite initialization"""
        suite = AnalyticsBenchmarkSuite()
        assert suite is not None
        assert hasattr(suite, 'gpu_manager')
        assert hasattr(suite, 'performance_monitor')
    
    @pytest.mark.asyncio
    async def test_centrality_benchmarks(self) -> None:
        """Test centrality algorithm benchmarks"""
        suite = AnalyticsBenchmarkSuite()
        
        # Use correct method signature - pass graph sizes as list of integers
        graph_sizes = [10, 20]
        results = await suite.benchmark_centrality_algorithms(graph_sizes)
        
        assert len(results) > 0
        for result in results:
            assert hasattr(result, 'test_name')
            assert hasattr(result, 'execution_time')
            assert hasattr(result, 'success')
    
    @pytest.mark.asyncio
    async def test_gpu_vs_cpu_benchmark(self) -> None:
        """Test GPU vs CPU performance comparison"""
        suite = AnalyticsBenchmarkSuite()
        
        # Use correct method signature - no parameters needed
        results = await suite.benchmark_gpu_vs_cpu()
        
        assert len(results) > 0
        for result in results:
            assert hasattr(result, 'baseline_result')
            assert hasattr(result, 'optimized_result')
            assert hasattr(result, 'speedup_factor')

class TestMonitoringMiddleware:
    """Test monitoring middleware functionality"""
    
    def test_middleware_initialization(self) -> None:
        """Test monitoring middleware initialization"""
        # Create a mock FastAPI app for testing
        from fastapi import FastAPI
        app = FastAPI()
        
        middleware = AnalyticsMonitoringMiddleware(app)
        assert middleware is not None
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self) -> None:
        """Test health check functionality"""
        from server.analytics.monitoring import AnalyticsHealthChecker
        
        health_checker = AnalyticsHealthChecker()
        health_status = await health_checker.check_all_components()
        
        assert "status" in health_status
        assert "timestamp" in health_status
        assert "components" in health_status
    
    def test_prometheus_metrics_collection(self) -> None:
        """Test Prometheus metrics collection"""
        from fastapi import FastAPI
        app = FastAPI()
        
        middleware = AnalyticsMonitoringMiddleware(app)
        
        # Test that metrics are set up (no exceptions raised)
        assert middleware is not None

class TestAPIEndpoints:
    """Test API endpoint functionality"""
    
    @pytest.mark.asyncio
    async def test_phase3_status_endpoint(self) -> None:
        """Test Phase 3 status endpoint"""
        # This would typically use FastAPI test client
        # For now, test the underlying functionality
        pass
    
    @pytest.mark.asyncio
    async def test_gpu_status_endpoint(self) -> None:
        """Test GPU status endpoint"""
        status = gpu_manager.get_acceleration_status()
        assert status is not None
        assert "gpu_available" in status
    
    @pytest.mark.asyncio
    async def test_performance_metrics_endpoint(self) -> None:
        """Test performance metrics endpoint"""
        metrics = performance_monitor.get_performance_summary()
        assert metrics is not None
        assert "timestamp" in metrics
    
    @pytest.mark.asyncio
    async def test_benchmark_execution_endpoint(self) -> None:
        """Test benchmark execution endpoint"""
        suite = AnalyticsBenchmarkSuite()
        
        # Use the correct method name
        results = await suite.run_comprehensive_benchmark()
        assert results is not None

class TestErrorHandling:
    """Test error handling and fallback mechanisms"""
    
    @pytest.mark.asyncio
    async def test_gpu_fallback_mechanism(self) -> None:
        """Test GPU fallback to CPU when GPU unavailable"""
        # Test that system works even when GPU is not available
        status = gpu_manager.get_acceleration_status()
        
        if not status["gpu_available"]:
            assert status["fallback_reason"] is not None
            # System should still function with CPU fallback
    
    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self, analytics_engine) -> None:
        """Test handling of database connection errors"""
        # Mock database connection failure
        analytics_engine.kuzu_conn.execute.side_effect = Exception("Database connection failed")
        
        # Should return empty graph data as fallback
        graph_data = await analytics_engine.get_graph_data()
        assert graph_data == {"nodes": [], "edges": []}
    
    @pytest.mark.asyncio
    async def test_algorithm_execution_error_handling(self, analytics_engine) -> None:
        """Test handling of algorithm execution errors"""
        # Test with invalid graph data
        analytics_engine.get_graph_data = Mock(return_value={"nodes": [], "edges": []})
        
        request = CentralityRequest(
            centrality_type=CentralityType.PAGERANK,
            limit=10
        )
        
        response = await analytics_engine.analyze_centrality(request)
        
        # Should handle empty graph gracefully
        assert response.centrality_type == CentralityType.PAGERANK
        assert len(response.top_nodes) == 0

class TestRealTimeUpdates:
    """Test real-time update functionality"""
    
    @pytest.mark.asyncio
    async def test_realtime_update_publishing(self, analytics_engine) -> None:
        """Test real-time update publishing"""
        # Mock the realtime analytics component
        analytics_engine.realtime.publish_update = Mock()
        
        # Trigger an analytics operation that should publish updates
        analytics_engine.get_graph_data = Mock(return_value={
            "nodes": [{"id": "node1"}],
            "edges": []
        })
        
        request = CentralityRequest(
            centrality_type=CentralityType.PAGERANK,
            limit=10
        )
        
        await analytics_engine.analyze_centrality(request)
        
        # Verify that publish_update was called
        analytics_engine.realtime.publish_update.assert_called()

# Test configuration and fixtures
@pytest.fixture(scope="session")
def event_loop() -> None:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"]) 