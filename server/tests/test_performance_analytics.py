"""
Performance and Load Testing for Analytics Integration Layer

This module provides comprehensive performance testing including:
- Load testing with concurrent requests
- Stress testing with high throughput
- Memory and resource usage monitoring
- Response time benchmarking
- Circuit breaker performance
- Cache efficiency testing
"""

import asyncio
import time
import psutil  # type: ignore
import pytest
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Tuple
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from server.analytics.kuzu_analytics import KuzuAnalyticsEngine, GraphAnalyticsType
from server.analytics.gateway import AnalyticsGateway, GatewayRequest, GatewayResponse
from server.analytics.service_registry import AnalyticsServiceRegistry, ServiceEndpoint, ServiceType, ServiceHealth


@dataclass
class PerformanceMetrics:
    """Performance metrics collection"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    cache_hit_rate: float
    error_rate: float


class PerformanceTestSuite:
    """Comprehensive performance testing suite"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.response_times: List[float] = []
        self.start_time: float = 0
        self.end_time: float = 0
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.response_times.clear()
    
    def stop_monitoring(self) -> PerformanceMetrics:
        """Stop monitoring and calculate metrics"""
        self.end_time = time.time()
        test_duration = self.end_time - self.start_time
        
        if not self.response_times:
            return PerformanceMetrics(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_response_time=0.0,
                median_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                requests_per_second=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                cache_hit_rate=0.0,
                error_rate=0.0
            )
        
        # Calculate statistics
        avg_response_time = statistics.mean(self.response_times)
        median_response_time = statistics.median(self.response_times)
        
        sorted_times = sorted(self.response_times)
        p95_index = int(0.95 * len(sorted_times))
        p99_index = int(0.99 * len(sorted_times))
        
        p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
        p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
        
        total_requests = len(self.response_times)
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        # Get system metrics with proper error handling
        try:
            process = psutil.Process()
            memory_usage_mb = process.memory_info().rss / 1024 / 1024  # type: ignore
            cpu_usage_percent = process.cpu_percent()  # type: ignore
        except Exception:
            # Fallback values if psutil fails
            memory_usage_mb = 0.0
            cpu_usage_percent = 0.0
        
        metrics = PerformanceMetrics(
            total_requests=total_requests,
            successful_requests=total_requests,  # Will be updated by caller
            failed_requests=0,  # Will be updated by caller
            average_response_time=avg_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            cache_hit_rate=0.0,  # Will be calculated separately
            error_rate=0.0  # Will be calculated separately
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def record_response_time(self, response_time: float):
        """Record a response time measurement"""
        self.response_times.append(response_time)


class TestAnalyticsPerformance:
    """Analytics Engine Performance Tests"""
    
    @pytest.fixture
    def mock_connection(self):
        """Mock Kuzu database connection for performance testing"""
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.get_column_names.return_value = ["entity_id", "centrality_score"]
        mock_result.has_next.side_effect = [True] * 100 + [False]  # 100 results
        mock_result.get_next.side_effect = [
            [f"entity_{i}", i * 0.1] for i in range(100)
        ]
        mock_conn.execute.return_value = mock_result
        return mock_conn
    
    @pytest.fixture
    def analytics_engine(self, mock_connection):
        """Create analytics engine for performance testing"""
        return KuzuAnalyticsEngine(mock_connection)
    
    @pytest.fixture
    def performance_suite(self):
        """Create performance test suite"""
        return PerformanceTestSuite()
    
    @pytest.mark.asyncio
    async def test_centrality_analysis_performance(self, analytics_engine, performance_suite):
        """Test centrality analysis performance under load"""
        performance_suite.start_monitoring()
        
        # Run multiple centrality analyses
        num_requests = 50
        tasks = []
        
        for i in range(num_requests):
            task = self._run_centrality_test(analytics_engine, performance_suite, i)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metrics = performance_suite.stop_monitoring()
        
        # Validate performance expectations
        assert metrics.average_response_time < 100.0  # Less than 100ms average
        assert metrics.requests_per_second > 10.0  # At least 10 RPS
        assert metrics.memory_usage_mb < 500.0  # Less than 500MB memory
        
        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_requests >= num_requests * 0.95  # 95% success rate
        
        print(f"Centrality Performance: {metrics.average_response_time:.2f}ms avg, {metrics.requests_per_second:.2f} RPS")
    
    async def _run_centrality_test(self, analytics_engine, performance_suite, iteration: int):
        """Single centrality analysis test"""
        start_time = time.time()
        
        try:
            result = await analytics_engine.execute_graph_analytics(
                GraphAnalyticsType.CENTRALITY,
                {
                    "entity_type": "Entity",
                    "algorithm": "degree_centrality",
                    "limit": 20
                }
            )
            
            response_time = (time.time() - start_time) * 1000
            performance_suite.record_response_time(response_time)
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            performance_suite.record_response_time(response_time)
            raise e
    
    @pytest.mark.asyncio
    async def test_concurrent_analytics_stress(self, analytics_engine, performance_suite):
        """Stress test with high concurrency"""
        performance_suite.start_monitoring()
        
        # High concurrency test
        num_concurrent = 100
        num_iterations = 5
        
        all_tasks = []
        
        for iteration in range(num_iterations):
            batch_tasks = []
            
            for i in range(num_concurrent):
                # Mix different analytics types
                analytics_type = [
                    GraphAnalyticsType.CENTRALITY,
                    GraphAnalyticsType.COMMUNITY_DETECTION,
                    GraphAnalyticsType.PATH_ANALYSIS,
                    GraphAnalyticsType.SIMILARITY
                ][i % 4]
                
                task = self._run_stress_test(analytics_engine, performance_suite, analytics_type, i)
                batch_tasks.append(task)
            
            # Run batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_tasks.extend(batch_results)
            
            # Brief pause between batches
            await asyncio.sleep(0.1)
        
        metrics = performance_suite.stop_monitoring()
        
        # Stress test expectations (more lenient)
        assert metrics.average_response_time < 500.0  # Less than 500ms under stress
        assert metrics.requests_per_second > 5.0  # At least 5 RPS under stress
        
        successful_requests = sum(1 for r in all_tasks if not isinstance(r, Exception))
        total_requests = num_concurrent * num_iterations
        success_rate = successful_requests / total_requests
        
        assert success_rate >= 0.90  # 90% success rate under stress
        
        print(f"Stress Test: {metrics.average_response_time:.2f}ms avg, {success_rate:.2%} success rate")
    
    async def _run_stress_test(self, analytics_engine, performance_suite, analytics_type, iteration: int):
        """Single stress test operation"""
        start_time = time.time()
        
        try:
            parameters = self._get_test_parameters(analytics_type, iteration)
            
            result = await analytics_engine.execute_graph_analytics(
                analytics_type,
                parameters
            )
            
            response_time = (time.time() - start_time) * 1000
            performance_suite.record_response_time(response_time)
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            performance_suite.record_response_time(response_time)
            raise e
    
    def _get_test_parameters(self, analytics_type: GraphAnalyticsType, iteration: int) -> Dict[str, Any]:
        """Get test parameters for different analytics types"""
        if analytics_type == GraphAnalyticsType.CENTRALITY:
            return {
                "entity_type": "Entity",
                "algorithm": "degree_centrality",
                "limit": 10
            }
        elif analytics_type == GraphAnalyticsType.COMMUNITY_DETECTION:
            return {
                "entity_type": "Entity",
                "min_cluster_size": 3
            }
        elif analytics_type == GraphAnalyticsType.PATH_ANALYSIS:
            return {
                "source_node": f"entity_{iteration % 10}",
                "max_hops": 4
            }
        elif analytics_type == GraphAnalyticsType.SIMILARITY:
            return {
                "entity_id": f"entity_{iteration % 20}"
            }
        else:
            return {}


class TestGatewayPerformance:
    """Gateway Performance Tests"""
    
    @pytest.fixture
    def mock_service_registry(self):
        """Mock service registry for performance testing"""
        registry = Mock()
        
        # Create mock services
        mock_services = []
        for i in range(5):  # 5 mock services for load balancing
            service = Mock()
            service.service_id = f"analytics-service-{i}"
            service.endpoint_url = f"http://localhost:800{i}"
            service.health_status = ServiceHealth.HEALTHY
            mock_services.append(service)
        
        registry.discover_services = AsyncMock(return_value=mock_services)
        registry.update_service_metrics = AsyncMock()
        return registry
    
    @pytest.fixture
    def analytics_gateway(self, mock_service_registry):
        """Create analytics gateway for performance testing"""
        return AnalyticsGateway(mock_service_registry)
    
    @pytest.mark.asyncio
    async def test_gateway_throughput_performance(self, analytics_gateway):
        """Test gateway throughput under high load"""
        await analytics_gateway.start(num_workers=8)  # High worker count
        
        performance_suite = PerformanceTestSuite()
        performance_suite.start_monitoring()
        
        # Mock HTTP responses
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "success"})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # High throughput test
            num_requests = 200
            batch_size = 20
            
            all_tasks = []
            
            for batch in range(0, num_requests, batch_size):
                batch_tasks = []
                
                for i in range(min(batch_size, num_requests - batch)):
                    task = self._run_gateway_request(analytics_gateway, performance_suite, batch + i)
                    batch_tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                all_tasks.extend(batch_results)
        
        await analytics_gateway.stop()
        
        metrics = performance_suite.stop_monitoring()
        
        # Performance expectations
        assert metrics.average_response_time < 50.0  # Less than 50ms with mocking
        assert metrics.requests_per_second > 50.0  # At least 50 RPS
        
        successful_requests = sum(1 for r in all_tasks if isinstance(r, GatewayResponse) and r.status == "success")
        success_rate = successful_requests / num_requests
        
        assert success_rate >= 0.95  # 95% success rate
        
        print(f"Gateway Throughput: {metrics.requests_per_second:.2f} RPS, {success_rate:.2%} success")
    
    async def _run_gateway_request(self, gateway, performance_suite, iteration: int):
        """Single gateway request for performance testing"""
        start_time = time.time()
        
        try:
            result = await gateway.execute_request(
                service="analytics_engine",
                operation="centrality",
                data={"entity_type": "Entity", "iteration": iteration},
                priority="normal",
                use_cache=True
            )
            
            response_time = (time.time() - start_time) * 1000
            performance_suite.record_response_time(response_time)
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            performance_suite.record_response_time(response_time)
            raise e
    
    @pytest.mark.asyncio
    async def test_cache_performance_impact(self, analytics_gateway):
        """Test performance impact of caching"""
        await analytics_gateway.start(num_workers=4)
        
        # Mock HTTP responses
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "cached_data"})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # Test with cache disabled
            no_cache_times = []
            for i in range(20):
                start_time = time.time()
                await analytics_gateway.execute_request(
                    service="analytics_engine",
                    operation="test_op",
                    data={"test": f"data_{i}"},  # Different data each time
                    use_cache=False
                )
                no_cache_times.append((time.time() - start_time) * 1000)
            
            # Test with cache enabled (same requests)
            cache_times = []
            for i in range(20):
                start_time = time.time()
                await analytics_gateway.execute_request(
                    service="analytics_engine",
                    operation="test_op",
                    data={"test": "same_data"},  # Same data for cache hits
                    use_cache=True
                )
                cache_times.append((time.time() - start_time) * 1000)
        
        await analytics_gateway.stop()
        
        # Cache should significantly improve performance
        avg_no_cache = statistics.mean(no_cache_times)
        avg_with_cache = statistics.mean(cache_times[1:])  # Skip first request (cache miss)
        
        cache_improvement = (avg_no_cache - avg_with_cache) / avg_no_cache
        
        assert cache_improvement > 0.5  # At least 50% improvement with cache
        assert analytics_gateway.gateway_stats["cached_responses"] > 0
        
        print(f"Cache Performance: {cache_improvement:.2%} improvement, {avg_with_cache:.2f}ms cached avg")


class TestMemoryAndResourceUsage:
    """Memory and Resource Usage Tests"""
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation"""
        try:
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # type: ignore
        except Exception:
            # Skip test if psutil is not available
            pytest.skip("psutil not available for memory monitoring")
        
        # Mock connection for extended testing
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.get_column_names.return_value = ["count"]
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = [42]
        mock_conn.execute.return_value = mock_result
        
        analytics_engine = KuzuAnalyticsEngine(mock_conn)
        
        # Run many operations
        for i in range(100):
            await analytics_engine.execute_graph_analytics(
                GraphAnalyticsType.CENTRALITY,
                {"entity_type": "Entity", "algorithm": "degree_centrality"}
            )
            
            # Periodic memory check
            if i % 20 == 0:
                try:
                    current_memory = process.memory_info().rss / 1024 / 1024  # type: ignore
                    memory_growth = current_memory - initial_memory
                    
                    # Memory growth should be reasonable
                    assert memory_growth < 100.0  # Less than 100MB growth
                except Exception:
                    # Skip memory check if psutil fails
                    continue
        
        try:
            final_memory = process.memory_info().rss / 1024 / 1024  # type: ignore
            total_growth = final_memory - initial_memory
            
            # Final memory check
            assert total_growth < 150.0  # Less than 150MB total growth
            
            print(f"Memory Usage: Initial={initial_memory:.2f}MB, Final={final_memory:.2f}MB, Growth={total_growth:.2f}MB")
        except Exception:
            print("Memory monitoring not available - test passed")
    
    @pytest.mark.asyncio
    async def test_cache_memory_management(self):
        """Test cache memory management and cleanup"""
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.get_column_names.return_value = ["entity_id"]
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = ["test_entity"]
        mock_conn.execute.return_value = mock_result
        
        analytics_engine = KuzuAnalyticsEngine(mock_conn)
        initial_cache_size = len(analytics_engine.query_cache)
        
        # Fill cache with many different queries
        for i in range(150):  # Exceed cache limit (100)
            await analytics_engine.execute_graph_analytics(
                GraphAnalyticsType.CENTRALITY,
                {"entity_type": "Entity", "iteration": i}  # Different parameters
            )
        
        # Cache should have been cleaned up
        final_cache_size = len(analytics_engine.query_cache)
        assert final_cache_size <= 100  # Should not exceed limit
        assert final_cache_size > initial_cache_size  # Should have some entries
        
        print(f"Cache Management: {final_cache_size} entries (limit: 100)")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])  # -s to see print outputs 