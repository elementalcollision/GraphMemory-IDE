"""
Comprehensive benchmarking suite for Analytics Engine Phase 3.
Provides performance testing, GPU vs CPU comparisons, and concurrent processing validation.
"""

import asyncio
import time
import statistics
import psutil
import pytest
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging

from .gpu_acceleration import gpu_manager
from .performance_monitor import performance_monitor
from .concurrent_processing import concurrent_manager
from .algorithms import GraphAlgorithms, MLAnalytics
from .models import CentralityRequest, CommunityRequest, ClusteringRequest, CentralityType, ClusteringType

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    test_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    gpu_usage: Optional[float]
    throughput: Optional[float]
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Result of comparing two benchmark approaches"""
    baseline_result: BenchmarkResult
    optimized_result: BenchmarkResult
    speedup_factor: float
    memory_improvement: float
    success_rate_improvement: float


class AnalyticsBenchmarkSuite:
    """
    Comprehensive benchmarking suite for analytics engine.
    Tests GPU acceleration, concurrent processing, and overall performance.
    """
    
    def __init__(self) -> None:
        self.graph_algorithms = GraphAlgorithms()
        self.ml_analytics = MLAnalytics()
        self.results: List[BenchmarkResult] = []
        self.comparisons: List[ComparisonResult] = []
    
    async def initialize(self) -> None:
        """Initialize benchmarking components"""
        await concurrent_manager.initialize()
        logger.info("Benchmark suite initialized")
    
    def _monitor_system_resources(self) -> Dict[str, Union[float, int]]:
        """Monitor current system resource usage"""
        disk_io = psutil.disk_io_counters()  # type: ignore
        
        # Handle disk I/O stats safely
        disk_read = 0
        disk_write = 0
        if disk_io is not None:
            disk_read = disk_io.read_bytes  # type: ignore
            disk_write = disk_io.write_bytes  # type: ignore
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1, percpu=False),  # type: ignore
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": psutil.virtual_memory().used / (1024**3),
            "disk_io_read": disk_read,
            "disk_io_write": disk_write
        }
    
    async def _run_benchmark(
        self,
        test_name: str,
        test_function: Callable,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """Run a single benchmark test with resource monitoring"""
        start_resources = self._monitor_system_resources()
        start_time = time.time()
        
        try:
            # Run the test function
            if asyncio.iscoroutinefunction(test_function):
                result = await test_function(*args, **kwargs)
            else:
                result = test_function(*args, **kwargs)
            
            end_time = time.time()
            end_resources = self._monitor_system_resources()
            
            execution_time = end_time - start_time
            memory_usage = float(end_resources["memory_used_gb"]) - float(start_resources["memory_used_gb"])
            cpu_usage = float(end_resources["cpu_percent"])
            
            # Get GPU usage if available
            gpu_usage = None
            if hasattr(gpu_manager, 'is_gpu_available') and gpu_manager.is_gpu_available():
                gpu_status = gpu_manager.get_acceleration_status()
                gpu_usage = gpu_status.get("memory_usage", 0)
            
            benchmark_result = BenchmarkResult(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                gpu_usage=gpu_usage,
                throughput=None,  # Will be calculated based on test type
                success=True,
                metadata={"result": result}
            )
            
            self.results.append(benchmark_result)
            return benchmark_result
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            benchmark_result = BenchmarkResult(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage=0,
                cpu_usage=0,
                gpu_usage=None,
                throughput=None,
                success=False,
                error_message=str(e)
            )
            
            self.results.append(benchmark_result)
            return benchmark_result
    
    async def benchmark_centrality_algorithms(self, graph_sizes: Optional[List[int]] = None) -> List[BenchmarkResult]:
        """Benchmark centrality algorithms with different graph sizes"""
        if graph_sizes is None:
            graph_sizes = [100, 500, 1000, 2000]
        
        results = []
        algorithms = [CentralityType.PAGERANK, CentralityType.BETWEENNESS, CentralityType.CLOSENESS, CentralityType.EIGENVECTOR]
        
        for size in graph_sizes:
            # Generate test graph
            test_graph = self._generate_test_graph(size)
            
            for algorithm in algorithms:
                test_name = f"centrality_{algorithm.value}_nodes_{size}"
                
                async def run_centrality() -> Dict[str, float]:
                    return await self.graph_algorithms.calculate_centrality(
                        test_graph, centrality_type=algorithm
                    )
                
                result = await self._run_benchmark(test_name, run_centrality)
                result.throughput = size / result.execution_time  # nodes per second
                results.append(result)
        
        return results
    
    async def benchmark_community_detection(self, graph_sizes: Optional[List[int]] = None) -> List[BenchmarkResult]:
        """Benchmark community detection algorithms"""
        if graph_sizes is None:
            graph_sizes = [100, 500, 1000, 2000]
        
        results = []
        algorithms = ["louvain", "greedy_modularity", "label_propagation"]
        
        for size in graph_sizes:
            test_graph = self._generate_test_graph(size)
            
            for algorithm in algorithms:
                test_name = f"community_{algorithm}_nodes_{size}"
                
                async def run_community() -> Any:
                    return await self.graph_algorithms.detect_communities(
                        test_graph, algorithm=algorithm
                    )
                
                result = await self._run_benchmark(test_name, run_community)
                result.throughput = size / result.execution_time
                results.append(result)
        
        return results
    
    async def benchmark_ml_clustering(self, data_sizes: Optional[List[int]] = None) -> List[BenchmarkResult]:
        """Benchmark ML clustering algorithms"""
        if data_sizes is None:
            data_sizes = [100, 500, 1000, 2000]
        
        results = []
        algorithms = [ClusteringType.SPECTRAL, ClusteringType.KMEANS, ClusteringType.HIERARCHICAL]
        
        for size in data_sizes:
            test_graph = self._generate_test_graph(size)
            # Extract features for clustering
            features, _, node_ids = await self.ml_analytics.extract_node_features(test_graph)
            
            for algorithm in algorithms:
                test_name = f"clustering_{algorithm.value}_nodes_{size}"
                
                async def run_clustering() -> Any:
                    return await self.ml_analytics.cluster_nodes(
                        features, clustering_type=algorithm, n_clusters=5
                    )
                
                result = await self._run_benchmark(test_name, run_clustering)
                result.throughput = size / result.execution_time
                results.append(result)
        
        return results
    
    async def benchmark_gpu_vs_cpu(self) -> List[ComparisonResult]:
        """Compare GPU vs CPU performance for supported algorithms"""
        comparisons = []
        test_sizes = [500, 1000, 2000]
        
        if not (hasattr(gpu_manager, 'is_gpu_available') and gpu_manager.is_gpu_available()):
            logger.warning("GPU not available, skipping GPU vs CPU benchmarks")
            return comparisons
        
        for size in test_sizes:
            test_graph = self._generate_test_graph(size)
            
            # Test PageRank (GPU accelerated)
            # CPU version
            if hasattr(gpu_manager, 'disable_gpu_acceleration'):
                gpu_manager.disable_gpu_acceleration()
            cpu_result = await self._run_benchmark(
                f"pagerank_cpu_nodes_{size}",
                self.graph_algorithms.calculate_centrality,
                test_graph,
                centrality_type=CentralityType.PAGERANK
            )
            
            # GPU version
            if hasattr(gpu_manager, 'enable_gpu_acceleration'):
                gpu_manager.enable_gpu_acceleration()
            gpu_result = await self._run_benchmark(
                f"pagerank_gpu_nodes_{size}",
                self.graph_algorithms.calculate_centrality,
                test_graph,
                centrality_type=CentralityType.PAGERANK
            )
            
            if cpu_result.success and gpu_result.success:
                speedup = cpu_result.execution_time / gpu_result.execution_time
                memory_improvement = (cpu_result.memory_usage - gpu_result.memory_usage) / cpu_result.memory_usage if cpu_result.memory_usage != 0 else 0.0
                
                comparison = ComparisonResult(
                    baseline_result=cpu_result,
                    optimized_result=gpu_result,
                    speedup_factor=speedup,
                    memory_improvement=memory_improvement,
                    success_rate_improvement=0.0
                )
                comparisons.append(comparison)
        
        return comparisons
    
    async def benchmark_concurrent_processing(self) -> List[ComparisonResult]:
        """Compare sequential vs concurrent processing performance"""
        comparisons = []
        test_sizes = [100, 500, 1000]
        
        for size in test_sizes:
            test_graphs = [self._generate_test_graph(size) for _ in range(4)]
            
            # Sequential processing
            start_time = time.time()
            sequential_results = []
            for graph in test_graphs:
                result = await self.graph_algorithms.calculate_centrality(graph, centrality_type=CentralityType.PAGERANK)
                sequential_results.append(result)
            sequential_time = time.time() - start_time
            
            sequential_result = BenchmarkResult(
                test_name=f"sequential_processing_nodes_{size}",
                execution_time=sequential_time,
                memory_usage=0,
                cpu_usage=0,
                gpu_usage=None,
                throughput=len(test_graphs) / sequential_time,
                success=True
            )
            
            # Concurrent processing
            start_time = time.time()
            tasks = [
                self.graph_algorithms.calculate_centrality(graph, centrality_type=CentralityType.PAGERANK)
                for graph in test_graphs
            ]
            concurrent_results = await asyncio.gather(*tasks)
            concurrent_time = time.time() - start_time
            
            concurrent_result = BenchmarkResult(
                test_name=f"concurrent_processing_nodes_{size}",
                execution_time=concurrent_time,
                memory_usage=0,
                cpu_usage=0,
                gpu_usage=None,
                throughput=len(test_graphs) / concurrent_time,
                success=True
            )
            
            speedup = sequential_time / concurrent_time
            comparison = ComparisonResult(
                baseline_result=sequential_result,
                optimized_result=concurrent_result,
                speedup_factor=speedup,
                memory_improvement=0.0,
                success_rate_improvement=0.0
            )
            comparisons.append(comparison)
        
        return comparisons
    
    def _generate_test_graph(self, num_nodes: int) -> Any:
        """Generate a test graph with specified number of nodes"""
        import networkx as nx
        
        # Create a scale-free graph for realistic testing
        graph = nx.barabasi_albert_graph(num_nodes, 3)
        
        # Add some random attributes
        for node in graph.nodes():
            graph.nodes[node]['type'] = f"node_{node % 5}"
            graph.nodes[node]['weight'] = hash(node) % 100
        
        for edge in graph.edges():
            graph.edges[edge]['weight'] = hash(edge) % 10 + 1
        
        return graph
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run all benchmark tests and return comprehensive results"""
        logger.info("Starting comprehensive benchmark suite")
        
        all_results: Dict[str, Any] = {}
        
        # Centrality benchmarks
        logger.info("Running centrality benchmarks")
        centrality_results = await self.benchmark_centrality_algorithms()
        all_results["centrality"] = centrality_results
        
        # Community detection benchmarks
        logger.info("Running community detection benchmarks")
        community_results = await self.benchmark_community_detection()
        all_results["community"] = community_results
        
        # ML clustering benchmarks
        logger.info("Running ML clustering benchmarks")
        clustering_results = await self.benchmark_ml_clustering()
        all_results["clustering"] = clustering_results
        
        # GPU vs CPU comparisons
        logger.info("Running GPU vs CPU comparisons")
        gpu_comparisons = await self.benchmark_gpu_vs_cpu()
        all_results["gpu_comparisons"] = gpu_comparisons
        
        # Concurrent processing comparisons
        logger.info("Running concurrent processing comparisons")
        concurrent_comparisons = await self.benchmark_concurrent_processing()
        all_results["concurrent_comparisons"] = concurrent_comparisons
        
        # Generate summary statistics
        summary = self._generate_benchmark_summary(all_results)
        all_results["summary"] = summary
        
        logger.info("Comprehensive benchmark suite completed")
        return all_results
    
    def _generate_benchmark_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from benchmark results"""
        summary = {
            "total_tests": len(self.results),
            "successful_tests": len([r for r in self.results if r.success]),
            "failed_tests": len([r for r in self.results if not r.success]),
            "average_execution_time": statistics.mean([r.execution_time for r in self.results if r.success]) if self.results else 0,
            "total_execution_time": sum([r.execution_time for r in self.results]),
            "gpu_available": hasattr(gpu_manager, 'is_gpu_available') and gpu_manager.is_gpu_available(),
            "gpu_enabled": hasattr(gpu_manager, 'is_gpu_enabled') and gpu_manager.is_gpu_enabled(),
        }
        
        # Calculate speedup statistics
        if self.comparisons:
            speedups = [c.speedup_factor for c in self.comparisons]
            summary.update({
                "average_speedup": statistics.mean(speedups),
                "max_speedup": max(speedups),
                "min_speedup": min(speedups),
                "total_comparisons": len(self.comparisons)
            })
        
        return summary
    
    def export_results(self, format: str = "json") -> str:
        """Export benchmark results in specified format"""
        if format == "json":
            import json
            return json.dumps({
                "results": [r.__dict__ for r in self.results],
                "comparisons": [c.__dict__ for c in self.comparisons]
            }, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "test_name", "execution_time", "memory_usage", "cpu_usage",
                "gpu_usage", "throughput", "success", "error_message"
            ])
            writer.writeheader()
            for result in self.results:
                writer.writerow(result.__dict__)
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global benchmark suite instance
benchmark_suite = AnalyticsBenchmarkSuite()


# Pytest integration functions
@pytest.mark.asyncio
async def test_centrality_performance(benchmark) -> None:
    """Pytest benchmark for centrality algorithms"""
    await benchmark_suite.initialize()
    test_graph = benchmark_suite._generate_test_graph(500)
    
    result = benchmark(
        lambda: asyncio.run(
            benchmark_suite.graph_algorithms.calculate_centrality(test_graph, centrality_type=CentralityType.PAGERANK)
        )
    )
    assert result is not None


@pytest.mark.asyncio
async def test_community_performance(benchmark) -> None:
    """Pytest benchmark for community detection"""
    await benchmark_suite.initialize()
    test_graph = benchmark_suite._generate_test_graph(500)
    
    result = benchmark(
        lambda: asyncio.run(
            benchmark_suite.graph_algorithms.detect_communities(test_graph, algorithm="louvain")
        )
    )
    assert result is not None


@pytest.mark.asyncio
async def test_clustering_performance(benchmark) -> None:
    """Pytest benchmark for ML clustering"""
    await benchmark_suite.initialize()
    test_graph = benchmark_suite._generate_test_graph(500)
    
    # Extract features first
    features, _, node_ids = await benchmark_suite.ml_analytics.extract_node_features(test_graph)
    
    result = benchmark(
        lambda: asyncio.run(
            benchmark_suite.ml_analytics.cluster_nodes(features, clustering_type=ClusteringType.SPECTRAL, n_clusters=5)
        )
    )
    assert result is not None 