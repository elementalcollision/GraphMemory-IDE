#!/usr/bin/env python3
"""
Analytics Performance Benchmark Script

Comprehensive benchmarking for the Analytics Integration Layer
Run with: python server/tests/benchmark_analytics.py
"""

import asyncio
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Union
from unittest.mock import Mock, AsyncMock

# Import with error handling for psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from server.analytics.kuzu_analytics import KuzuAnalyticsEngine, GraphAnalyticsType
from server.analytics.gateway import AnalyticsGateway
from server.analytics.service_registry import AnalyticsServiceRegistry, ServiceEndpoint, ServiceType, ServiceHealth


@dataclass
class BenchmarkResult:
    """Benchmark result data structure"""
    test_name: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_time_seconds: float
    average_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    operations_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_rate: float
    additional_metrics: Dict[str, Any]


class AnalyticsBenchmark:
    """Main benchmark orchestrator"""
    
    def __init__(self) -> None:
        self.results: List[BenchmarkResult] = []
        # Properly type these attributes as Optional initially
        self.mock_connection: Optional[Mock] = None
        self.analytics_engine: Optional[KuzuAnalyticsEngine] = None
        self.gateway: Optional[AnalyticsGateway] = None
        self.service_registry: Optional[AnalyticsServiceRegistry] = None
    
    async def setup(self) -> None:
        """Setup benchmark environment"""
        print("Setting up benchmark environment...")
        
        # Setup mock Kuzu connection
        self.mock_connection = Mock()
        mock_result = Mock()
        mock_result.get_column_names.return_value = ["entity_id", "score"]
        mock_result.has_next.side_effect = lambda: True  # Endless data for stress testing
        mock_result.get_next.side_effect = lambda: [f"entity_{int(time.time() * 1000000) % 10000}", 0.5]
        self.mock_connection.execute.return_value = mock_result
        
        # Setup analytics engine
        self.analytics_engine = KuzuAnalyticsEngine(self.mock_connection)
        
        # Setup service registry
        self.service_registry = AnalyticsServiceRegistry()
        await self.service_registry.start()
        
        # Register mock services
        for i in range(3):
            await self.service_registry.register_service(
                service_id=f"analytics-service-{i}",
                service_name=f"Analytics Service {i}",
                service_type=ServiceType.ANALYTICS_ENGINE,
                endpoint_url=f"http://localhost:800{i}",
                capabilities=["centrality", "clustering", "path_analysis"],
                tags=["benchmark", "test"]
            )
        
        # Setup gateway
        self.gateway = AnalyticsGateway(self.service_registry)
        await self.gateway.start(num_workers=8)
        
        print("✓ Benchmark environment ready")
    
    async def cleanup(self) -> None:
        """Cleanup benchmark environment"""
        if self.gateway:
            await self.gateway.stop()
        if self.service_registry:
            await self.service_registry.stop()
        print("✓ Benchmark environment cleaned up")
    
    async def run_all_benchmarks(self) -> None:
        """Run all benchmark tests"""
        print("\n" + "="*80)
        print("ANALYTICS INTEGRATION LAYER - PERFORMANCE BENCHMARK")
        print("="*80)
        
        await self.setup()
        
        try:
            # Analytics Engine Benchmarks
            print("\n📊 ANALYTICS ENGINE BENCHMARKS")
            print("-" * 50)
            
            await self.benchmark_centrality_analysis()
            await self.benchmark_community_detection()
            await self.benchmark_path_analysis()
            await self.benchmark_mixed_analytics_load()
            
            # Gateway Benchmarks
            print("\n🔄 GATEWAY BENCHMARKS")
            print("-" * 50)
            
            await self.benchmark_gateway_throughput()
            await self.benchmark_gateway_caching()
            await self.benchmark_gateway_load_balancing()
            
            # Stress Tests
            print("\n🔥 STRESS TESTS")
            print("-" * 50)
            
            await self.benchmark_high_concurrency()
            await self.benchmark_memory_efficiency()
            
            # Performance Summary
            print("\n📈 BENCHMARK SUMMARY")
            print("-" * 50)
            self.print_summary()
            
        finally:
            await self.cleanup()
    
    async def benchmark_centrality_analysis(self) -> None:
        """Benchmark centrality analysis performance"""
        # Ensure setup has been called
        assert self.analytics_engine is not None, "Setup must be called before benchmarking"
        
        test_name = "Centrality Analysis"
        print(f"Running {test_name}...")
        
        response_times = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for i in range(50):
            operation_start = time.time()
            
            try:
                result = await self.analytics_engine.execute_graph_analytics(
                    GraphAnalyticsType.CENTRALITY,
                    {
                        "entity_type": "Entity",
                        "algorithm": "degree_centrality",
                        "limit": 25
                    }
                )
                
                if result and "execution_time_ms" in result:
                    successful += 1
                    response_time = (time.time() - operation_start) * 1000
                    response_times.append(response_time)
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                print(f"  Error in iteration {i}: {e}")
        
        total_time = time.time() - start_time
        
        result = self._create_benchmark_result(
            test_name=test_name,
            total_operations=50,
            successful_operations=successful,
            failed_operations=failed,
            total_time_seconds=total_time,
            response_times=response_times,
            additional_metrics={
                "cache_hits": self.analytics_engine.analytics_stats.get("cache_hits", 0),
                "total_queries": self.analytics_engine.analytics_stats.get("total_queries", 0)
            }
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_community_detection(self) -> None:
        """Benchmark community detection performance"""
        # Ensure setup has been called
        assert self.analytics_engine is not None, "Setup must be called before benchmarking"
        
        test_name = "Community Detection"
        print(f"Running {test_name}...")
        
        response_times = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for i in range(25):  # Fewer iterations as community detection is more expensive
            operation_start = time.time()
            
            try:
                result = await self.analytics_engine.execute_graph_analytics(
                    GraphAnalyticsType.COMMUNITY_DETECTION,
                    {
                        "entity_type": "Entity",
                        "min_cluster_size": 3
                    }
                )
                
                if result:
                    successful += 1
                    response_time = (time.time() - operation_start) * 1000
                    response_times.append(response_time)
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                print(f"  Error in iteration {i}: {e}")
        
        total_time = time.time() - start_time
        
        result = self._create_benchmark_result(
            test_name=test_name,
            total_operations=25,
            successful_operations=successful,
            failed_operations=failed,
            total_time_seconds=total_time,
            response_times=response_times,
            additional_metrics={}
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_path_analysis(self) -> None:
        """Benchmark path analysis performance"""
        # Ensure setup has been called
        assert self.analytics_engine is not None, "Setup must be called before benchmarking"
        
        test_name = "Path Analysis"
        print(f"Running {test_name}...")
        
        response_times = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for i in range(30):
            operation_start = time.time()
            
            try:
                result = await self.analytics_engine.execute_graph_analytics(
                    GraphAnalyticsType.PATH_ANALYSIS,
                    {
                        "source_node": f"entity_{i % 10}",
                        "target_node": f"entity_{(i + 5) % 10}",
                        "max_hops": 5
                    }
                )
                
                if result:
                    successful += 1
                    response_time = (time.time() - operation_start) * 1000
                    response_times.append(response_time)
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                print(f"  Error in iteration {i}: {e}")
        
        total_time = time.time() - start_time
        
        result = self._create_benchmark_result(
            test_name=test_name,
            total_operations=30,
            successful_operations=successful,
            failed_operations=failed,
            total_time_seconds=total_time,
            response_times=response_times,
            additional_metrics={}
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_mixed_analytics_load(self) -> None:
        """Benchmark mixed analytics workload"""
        test_name = "Mixed Analytics Load"
        print(f"Running {test_name}...")
        
        response_times = []
        successful = 0
        failed = 0
        
        analytics_types = [
            GraphAnalyticsType.CENTRALITY,
            GraphAnalyticsType.SIMILARITY,
            GraphAnalyticsType.CLUSTERING,
            GraphAnalyticsType.NETWORK_STRUCTURE
        ]
        
        start_time = time.time()
        
        tasks = []
        for i in range(40):
            analytics_type = analytics_types[i % len(analytics_types)]
            task = self._run_analytics_operation(analytics_type, i)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            else:
                successful += 1
                if isinstance(result, float):
                    response_times.append(result)
        
        total_time = time.time() - start_time
        
        result = self._create_benchmark_result(
            test_name=test_name,
            total_operations=40,
            successful_operations=successful,
            failed_operations=failed,
            total_time_seconds=total_time,
            response_times=response_times,
            additional_metrics={
                "concurrency_level": len(tasks),
                "analytics_types_tested": len(analytics_types)
            }
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_gateway_throughput(self) -> None:
        """Benchmark gateway throughput"""
        test_name = "Gateway Throughput"
        print(f"Running {test_name}...")
        
        # Mock HTTP responses for gateway
        import aiohttp
        from unittest.mock import patch
        
        response_times = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "success", "data": []})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            tasks = []
            for i in range(100):  # High volume
                task = self._run_gateway_request(i)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                else:
                    successful += 1
                    if isinstance(result, float):
                        response_times.append(result)
        
        total_time = time.time() - start_time
        
        result = self._create_benchmark_result(
            test_name=test_name,
            total_operations=100,
            successful_operations=successful,
            failed_operations=failed,
            total_time_seconds=total_time,
            response_times=response_times,
            additional_metrics={
                "gateway_workers": 8,
                "cache_enabled": True
            }
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_gateway_caching(self) -> None:
        """Benchmark gateway caching performance"""
        test_name = "Gateway Caching"
        print(f"Running {test_name}...")
        
        import aiohttp
        from unittest.mock import patch
        
        cache_hit_times = []
        cache_miss_times = []
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "cached_data"})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # Test cache misses (different requests)
            for i in range(10):
                start = time.time()
                await self.gateway.execute_request(
                    service="analytics_engine",
                    operation="test_op",
                    data={"unique_id": i},
                    use_cache=True
                )
                cache_miss_times.append((time.time() - start) * 1000)
            
            # Test cache hits (same request)
            for i in range(20):
                start = time.time()
                await self.gateway.execute_request(
                    service="analytics_engine",
                    operation="test_op",
                    data={"same_data": "test"},
                    use_cache=True
                )
                cache_hit_times.append((time.time() - start) * 1000)
        
        cache_improvement = 0.0
        if cache_miss_times and cache_hit_times:
            avg_miss = statistics.mean(cache_miss_times)
            avg_hit = statistics.mean(cache_hit_times[1:])  # Skip first (cache miss)
            cache_improvement = (avg_miss - avg_hit) / avg_miss * 100
        
        result = BenchmarkResult(
            test_name=test_name,
            total_operations=30,
            successful_operations=30,
            failed_operations=0,
            total_time_seconds=0.0,
            average_response_time_ms=statistics.mean(cache_hit_times) if cache_hit_times else 0.0,
            median_response_time_ms=statistics.median(cache_hit_times) if cache_hit_times else 0.0,
            p95_response_time_ms=0.0,
            p99_response_time_ms=0.0,
            operations_per_second=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            error_rate=0.0,
            additional_metrics={
                "cache_improvement_percent": cache_improvement,
                "avg_cache_miss_ms": statistics.mean(cache_miss_times) if cache_miss_times else 0.0,
                "avg_cache_hit_ms": statistics.mean(cache_hit_times[1:]) if len(cache_hit_times) > 1 else 0.0,
                "cache_hit_count": len(cache_hit_times),
                "cache_miss_count": len(cache_miss_times)
            }
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_gateway_load_balancing(self) -> None:
        """Benchmark gateway load balancing"""
        test_name = "Gateway Load Balancing"
        print(f"Running {test_name}...")
        
        # Test that gateway distributes load across services
        service_counts = {}
        
        import aiohttp
        from unittest.mock import patch
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "success"})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            for i in range(30):
                await self.gateway.execute_request(
                    service="analytics_engine",
                    operation="load_balance_test",
                    data={"request_id": i},
                    use_cache=False  # Disable cache to ensure load balancing
                )
        
        # Check load balancing statistics
        load_balance_stats = self.gateway.gateway_stats.get("load_balanced_requests", 0)
        
        result = BenchmarkResult(
            test_name=test_name,
            total_operations=30,
            successful_operations=30,
            failed_operations=0,
            total_time_seconds=0.0,
            average_response_time_ms=0.0,
            median_response_time_ms=0.0,
            p95_response_time_ms=0.0,
            p99_response_time_ms=0.0,
            operations_per_second=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            error_rate=0.0,
            additional_metrics={
                "load_balanced_requests": load_balance_stats,
                "registered_services": len(self.service_registry.services),
                "healthy_services": sum(1 for s in self.service_registry.services.values() 
                                      if s.health_status == ServiceHealth.HEALTHY)
            }
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_high_concurrency(self) -> None:
        """Benchmark high concurrency performance"""
        test_name = "High Concurrency Stress"
        print(f"Running {test_name}...")
        
        response_times = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        # Create many concurrent tasks
        tasks = []
        for i in range(200):  # High concurrency
            task = self._run_analytics_operation(GraphAnalyticsType.CENTRALITY, i)
            tasks.append(task)
        
        # Execute in batches to avoid overwhelming the system
        batch_size = 50
        for batch_start in range(0, len(tasks), batch_size):
            batch_end = min(batch_start + batch_size, len(tasks))
            batch_tasks = tasks[batch_start:batch_end]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    failed += 1
                else:
                    successful += 1
                    if isinstance(result, float):
                        response_times.append(result)
            
            # Brief pause between batches
            await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        
        result = self._create_benchmark_result(
            test_name=test_name,
            total_operations=200,
            successful_operations=successful,
            failed_operations=failed,
            total_time_seconds=total_time,
            response_times=response_times,
            additional_metrics={
                "concurrency_level": 200,
                "batch_size": batch_size,
                "batches_executed": len(range(0, 200, batch_size))
            }
        )
        
        self.results.append(result)
        self._print_result(result)
    
    async def benchmark_memory_efficiency(self) -> None:
        """Benchmark memory efficiency"""
        test_name = "Memory Efficiency"
        print(f"Running {test_name}...")
        
        if not PSUTIL_AVAILABLE:
            print("psutil is not available. Skipping memory efficiency benchmark.")
            return
        
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run many operations to test memory usage
        for i in range(100):
            await self.analytics_engine.execute_graph_analytics(
                GraphAnalyticsType.CENTRALITY,
                {"entity_type": "Entity", "iteration": i}
            )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        result = BenchmarkResult(
            test_name=test_name,
            total_operations=100,
            successful_operations=100,
            failed_operations=0,
            total_time_seconds=0.0,
            average_response_time_ms=0.0,
            median_response_time_ms=0.0,
            p95_response_time_ms=0.0,
            p99_response_time_ms=0.0,
            operations_per_second=0.0,
            memory_usage_mb=final_memory,
            cpu_usage_percent=0.0,
            error_rate=0.0,
            additional_metrics={
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "memory_growth_mb": memory_growth,
                "cache_size": len(self.analytics_engine.query_cache),
                "operations_per_mb": 100 / memory_growth if memory_growth > 0 else float('inf')
            }
        )
        
        self.results.append(result)
        self._print_result(result)
    
    # Helper methods
    
    async def _run_analytics_operation(self, analytics_type: GraphAnalyticsType, iteration: int) -> float:
        """Run a single analytics operation and return response time"""
        start_time = time.time()
        
        parameters = self._get_test_parameters(analytics_type, iteration)
        
        await self.analytics_engine.execute_graph_analytics(analytics_type, parameters)
        
        return (time.time() - start_time) * 1000  # Return ms
    
    async def _run_gateway_request(self, iteration: int) -> float:
        """Run a single gateway request and return response time"""
        start_time = time.time()
        
        await self.gateway.execute_request(
            service="analytics_engine",
            operation="benchmark_test",
            data={"iteration": iteration},
            use_cache=True
        )
        
        return (time.time() - start_time) * 1000  # Return ms
    
    def _get_test_parameters(self, analytics_type: GraphAnalyticsType, iteration: int) -> Dict[str, Any]:
        """Get test parameters for analytics type"""
        if analytics_type == GraphAnalyticsType.CENTRALITY:
            return {
                "entity_type": "Entity",
                "algorithm": "degree_centrality",
                "limit": 20
            }
        elif analytics_type == GraphAnalyticsType.SIMILARITY:
            return {
                "entity_id": f"entity_{iteration % 10}"
            }
        elif analytics_type == GraphAnalyticsType.CLUSTERING:
            return {
                "entity_type": "Entity",
                "min_cluster_size": 3
            }
        elif analytics_type == GraphAnalyticsType.NETWORK_STRUCTURE:
            return {}
        else:
            return {}
    
    def _create_benchmark_result(
        self,
        test_name: str,
        total_operations: int,
        successful_operations: int,
        failed_operations: int,
        total_time_seconds: float,
        response_times: List[float],
        additional_metrics: Dict[str, Any]
    ) -> BenchmarkResult:
        """Create a benchmark result from measurements"""
        
        if not response_times:
            response_times = [0.0]
        
        sorted_times = sorted(response_times)
        p95_index = int(0.95 * len(sorted_times))
        p99_index = int(0.99 * len(sorted_times))
        
        return BenchmarkResult(
            test_name=test_name,
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            total_time_seconds=total_time_seconds,
            average_response_time_ms=statistics.mean(response_times),
            median_response_time_ms=statistics.median(response_times),
            p95_response_time_ms=sorted_times[min(p95_index, len(sorted_times) - 1)],
            p99_response_time_ms=sorted_times[min(p99_index, len(sorted_times) - 1)],
            operations_per_second=successful_operations / total_time_seconds if total_time_seconds > 0 else 0,
            memory_usage_mb=0.0,  # Will be set separately if needed
            cpu_usage_percent=0.0,  # Will be set separately if needed
            error_rate=failed_operations / total_operations if total_operations > 0 else 0,
            additional_metrics=additional_metrics
        )
    
    def _print_result(self, result: BenchmarkResult) -> None:
        """Print benchmark result"""
        print(f"  ✓ {result.test_name}")
        print(f"    Operations: {result.successful_operations}/{result.total_operations} successful")
        print(f"    Response Time: {result.average_response_time_ms:.2f}ms avg, {result.median_response_time_ms:.2f}ms median")
        print(f"    Throughput: {result.operations_per_second:.2f} ops/sec")
        print(f"    Error Rate: {result.error_rate:.2%}")
        
        if result.additional_metrics:
            for key, value in result.additional_metrics.items():
                if isinstance(value, float):
                    print(f"    {key.replace('_', ' ').title()}: {value:.2f}")
                else:
                    print(f"    {key.replace('_', ' ').title()}: {value}")
        print()
    
    def print_summary(self) -> None:
        """Print benchmark summary"""
        if not self.results:
            print("No benchmark results available")
            return
        
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        
        # Overall statistics
        total_ops = sum(r.total_operations for r in self.results)
        total_successful = sum(r.successful_operations for r in self.results)
        avg_response_time = statistics.mean([r.average_response_time_ms for r in self.results])
        avg_throughput = statistics.mean([r.operations_per_second for r in self.results if r.operations_per_second > 0])
        
        print(f"Total Operations: {total_ops}")
        print(f"Successful Operations: {total_successful} ({total_successful/total_ops:.2%})")
        print(f"Average Response Time: {avg_response_time:.2f}ms")
        print(f"Average Throughput: {avg_throughput:.2f} ops/sec")
        print()
        
        # Per-test breakdown
        print("PER-TEST BREAKDOWN")
        print("-" * 40)
        for result in self.results:
            print(f"{result.test_name:25} | {result.average_response_time_ms:8.2f}ms | {result.operations_per_second:8.2f} ops/sec | {result.error_rate:6.2%}")
        
        print()
        
        # Save results to file
        self.save_results()
    
    def save_results(self) -> None:
        """Save benchmark results to JSON file"""
        timestamp = int(time.time())
        filename = f"benchmark_results_{timestamp}.json"
        
        results_data = {
            "timestamp": timestamp,
            "benchmark_version": "1.0",
            "results": [asdict(result) for result in self.results]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"📄 Results saved to {filename}")


async def main() -> None:
    """Main benchmark execution"""
    benchmark = AnalyticsBenchmark()
    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main()) 