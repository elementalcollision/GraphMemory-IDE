"""
Performance Test Scenarios for Analytics Operations

This module provides comprehensive performance testing for analytics operations
comparing Codon vs CPython implementations.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np
import pytest

from tests.utils.benchmark_runner import (
    BenchmarkResult,
    ImplementationType,
    PerformanceBenchmarker,
)

logger = logging.getLogger(__name__)


class TestAnalyticsOperationsPerformance:
    """Performance tests for analytics operations"""

    def setup_method(self):
        """Setup test fixtures"""
        self.benchmarker = PerformanceBenchmarker()
        self.test_results: List[BenchmarkResult] = []

        # Create test data
        self.small_graph = self._create_test_graph(100, 500)
        self.medium_graph = self._create_test_graph(1000, 5000)
        self.large_graph = self._create_test_graph(5000, 25000)

    def _create_test_graph(self, num_nodes: int, num_edges: int) -> nx.Graph:
        """Create a test graph with specified number of nodes and edges"""
        G = nx.Graph()

        # Add nodes
        for i in range(num_nodes):
            G.add_node(f"node_{i}", weight=float(i), label=f"Node {i}")

        # Add edges
        edges_added = 0
        while edges_added < num_edges:
            source = f"node_{np.random.randint(0, num_nodes)}"
            target = f"node_{np.random.randint(0, num_nodes)}"
            if source != target and not G.has_edge(source, target):
                G.add_edge(source, target, weight=np.random.random())
                edges_added += 1

        return G

    async def test_graph_construction_performance(self):
        """Test performance of graph construction operations"""

        def build_graph_cpython(nodes: List[Dict], edges: List[Dict]) -> nx.Graph:
            """CPython implementation of graph construction"""
            G = nx.Graph()

            # Add nodes with attributes
            for node in nodes:
                node_id = node.get("id") or node.get("node_id")
                attributes = {
                    k: v for k, v in node.items() if k not in ["id", "node_id"]
                }
                G.add_node(node_id, **attributes)

            # Add edges with attributes
            for edge in edges:
                source = edge.get("source") or edge.get("from")
                target = edge.get("target") or edge.get("to")
                weight = edge.get("weight", 1.0)
                attributes = {
                    k: v
                    for k, v in edge.items()
                    if k not in ["source", "target", "from", "to"]
                }
                G.add_edge(source, target, weight=weight, **attributes)

            return G

        # Prepare test data
        nodes = [
            {"id": f"node_{i}", "weight": float(i), "label": f"Node {i}"}
            for i in range(1000)
        ]
        edges = [
            {"source": f"node_{i}", "target": f"node_{i+1}", "weight": 1.0}
            for i in range(999)
        ]

        # Benchmark CPython implementation
        cpython_result = await self.benchmarker.benchmark_function(
            build_graph_cpython,
            "graph_construction",
            ImplementationType.CPYTHON,
            iterations=5,
            nodes=nodes,
            edges=edges,
        )

        self.test_results.append(cpython_result)
        assert cpython_result.execution_time > 0

    async def test_centrality_calculation_performance(self):
        """Test performance of centrality calculations"""

        def calculate_centrality_cpython(graph: nx.Graph) -> Dict[str, float]:
            """CPython implementation of centrality calculation"""
            return nx.betweenness_centrality(graph, normalized=True)

        # Benchmark with different graph sizes
        for graph_name, graph in [
            ("small", self.small_graph),
            ("medium", self.medium_graph),
        ]:

            cpython_result = await self.benchmarker.benchmark_function(
                calculate_centrality_cpython,
                f"centrality_calculation_{graph_name}",
                ImplementationType.CPYTHON,
                iterations=3,
                graph=graph,
            )

            self.test_results.append(cpython_result)
            assert cpython_result.execution_time > 0

    async def test_community_detection_performance(self):
        """Test performance of community detection algorithms"""

        def detect_communities_cpython(graph: nx.Graph) -> Dict[str, str]:
            """CPython implementation of community detection"""
            from community import best_partition

            return best_partition(graph)

        # Test with different graph sizes
        for graph_name, graph in [
            ("small", self.small_graph),
            ("medium", self.medium_graph),
        ]:

            try:
                cpython_result = await self.benchmarker.benchmark_function(
                    detect_communities_cpython,
                    f"community_detection_{graph_name}",
                    ImplementationType.CPYTHON,
                    iterations=3,
                    graph=graph,
                )

                self.test_results.append(cpython_result)
                assert cpython_result.execution_time > 0
            except ImportError:
                logger.warning(
                    "python-louvain not available, skipping community detection test"
                )

    async def test_path_analysis_performance(self):
        """Test performance of path analysis algorithms"""

        def analyze_paths_cpython(graph: nx.Graph) -> Dict[str, Any]:
            """CPython implementation of path analysis"""
            # Find shortest paths between some nodes
            nodes = list(graph.nodes())
            if len(nodes) < 2:
                return {"paths": []}

            source = nodes[0]
            targets = nodes[1 : min(10, len(nodes))]

            paths = {}
            for target in targets:
                try:
                    path = nx.shortest_path(graph, source, target)
                    paths[f"{source}_to_{target}"] = path
                except nx.NetworkXNoPath:
                    continue

            return {"paths": paths}

        # Test with different graph sizes
        for graph_name, graph in [
            ("small", self.small_graph),
            ("medium", self.medium_graph),
        ]:

            cpython_result = await self.benchmarker.benchmark_function(
                analyze_paths_cpython,
                f"path_analysis_{graph_name}",
                ImplementationType.CPYTHON,
                iterations=3,
                graph=graph,
            )

            self.test_results.append(cpython_result)
            assert cpython_result.execution_time > 0

    async def test_memory_intensive_operations(self):
        """Test performance of memory-intensive operations"""

        def memory_intensive_cpython(data_size: int) -> List[float]:
            """CPython implementation of memory-intensive operations"""
            # Create large arrays and perform operations
            data = np.random.random(data_size)
            result = np.sin(data) + np.cos(data) * 2
            return result.tolist()

        # Test with different data sizes
        for size_name, size in [
            ("small", 10000),
            ("medium", 100000),
            ("large", 1000000),
        ]:

            cpython_result = await self.benchmarker.benchmark_function(
                memory_intensive_cpython,
                f"memory_intensive_{size_name}",
                ImplementationType.CPYTHON,
                iterations=3,
                data_size=size,
            )

            self.test_results.append(cpython_result)
            assert cpython_result.execution_time > 0

    async def test_cpu_intensive_operations(self):
        """Test performance of CPU-intensive operations"""

        def cpu_intensive_cpython(iterations: int) -> float:
            """CPython implementation of CPU-intensive operations"""
            result = 0.0
            for i in range(iterations):
                result += np.sin(i) * np.cos(i) + np.sqrt(i + 1)
            return result

        # Test with different iteration counts
        for iter_name, iterations in [
            ("low", 1000),
            ("medium", 10000),
            ("high", 100000),
        ]:

            cpython_result = await self.benchmarker.benchmark_function(
                cpu_intensive_cpython,
                f"cpu_intensive_{iter_name}",
                ImplementationType.CPYTHON,
                iterations=3,
                iterations_count=iterations,
            )

            self.test_results.append(cpython_result)
            assert cpython_result.execution_time > 0

    async def test_throughput_benchmarks(self):
        """Test throughput performance for analytics operations"""

        def throughput_operation_cpython(data_size: int) -> List[float]:
            """CPython implementation for throughput testing"""
            return [np.random.random() for _ in range(data_size)]

        # Test throughput with different data sizes
        for size_name, size in [("small", 100), ("medium", 1000), ("large", 10000)]:

            cpython_result = await self.benchmarker.benchmark_throughput(
                throughput_operation_cpython,
                f"throughput_{size_name}",
                ImplementationType.CPYTHON,
                data_size=size,
                time_limit=5.0,
                data_size_param=size,
            )

            self.test_results.append(cpython_result)
            assert cpython_result.throughput is not None
            assert cpython_result.throughput > 0


class TestCodonAnalyticsOperations:
    """Performance tests for Codon analytics operations (simulated)"""

    def setup_method(self):
        """Setup test fixtures"""
        self.benchmarker = PerformanceBenchmarker()
        self.test_results: List[BenchmarkResult] = []

        # Create test data
        self.small_graph = self._create_test_graph(100, 500)
        self.medium_graph = self._create_test_graph(1000, 5000)
        self.large_graph = self._create_test_graph(5000, 25000)

    def _create_test_graph(self, num_nodes: int, num_edges: int) -> Dict[str, Any]:
        """Create a test graph representation for Codon"""
        # Simulate Codon graph structure
        nodes = [
            {"id": f"node_{i}", "weight": float(i), "label": f"Node {i}"}
            for i in range(num_nodes)
        ]
        edges = [
            {"source": f"node_{i}", "target": f"node_{i+1}", "weight": 1.0}
            for i in range(min(num_edges, num_nodes - 1))
        ]

        return {"nodes": nodes, "edges": edges}

    async def test_codon_graph_construction_performance(self):
        """Test performance of Codon graph construction operations"""

        def build_graph_codon(graph_data: Dict[str, Any]) -> Dict[str, Any]:
            """Simulated Codon implementation of graph construction"""
            # Simulate Codon processing
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]

            # Simulate processing time
            import time

            time.sleep(0.001 * len(nodes))  # Simulate Codon processing

            return {"nodes": nodes, "edges": edges, "processed": True}

        # Prepare test data
        graph_data = self.small_graph

        # Benchmark Codon implementation
        codon_result = await self.benchmarker.benchmark_function(
            build_graph_codon,
            "graph_construction",
            ImplementationType.CONDON,
            iterations=5,
            graph_data=graph_data,
        )

        self.test_results.append(codon_result)
        assert codon_result.execution_time > 0

    async def test_codon_centrality_calculation_performance(self):
        """Test performance of Codon centrality calculations"""

        def calculate_centrality_codon(graph_data: Dict[str, Any]) -> Dict[str, float]:
            """Simulated Codon implementation of centrality calculation"""
            # Simulate Codon processing
            nodes = graph_data["nodes"]

            # Simulate processing time
            import time

            time.sleep(0.002 * len(nodes))  # Simulate Codon processing

            # Return simulated centrality scores
            centrality_scores = {}
            for node in nodes:
                centrality_scores[node["id"]] = float(node["weight"]) / 1000.0

            return centrality_scores

        # Test with different graph sizes
        for graph_name, graph in [
            ("small", self.small_graph),
            ("medium", self.medium_graph),
        ]:

            codon_result = await self.benchmarker.benchmark_function(
                calculate_centrality_codon,
                f"centrality_calculation_{graph_name}",
                ImplementationType.CONDON,
                iterations=3,
                graph_data=graph,
            )

            self.test_results.append(codon_result)
            assert codon_result.execution_time > 0

    async def test_codon_memory_intensive_operations(self):
        """Test performance of Codon memory-intensive operations"""

        def memory_intensive_codon(data_size: int) -> List[float]:
            """Simulated Codon implementation of memory-intensive operations"""
            # Simulate Codon processing
            import time

            time.sleep(0.001 * data_size / 1000)  # Simulate Codon processing

            # Return simulated results
            return [float(i) / data_size for i in range(data_size)]

        # Test with different data sizes
        for size_name, size in [
            ("small", 10000),
            ("medium", 100000),
            ("large", 1000000),
        ]:

            codon_result = await self.benchmarker.benchmark_function(
                memory_intensive_codon,
                f"memory_intensive_{size_name}",
                ImplementationType.CONDON,
                iterations=3,
                data_size=size,
            )

            self.test_results.append(codon_result)
            assert codon_result.execution_time > 0

    async def test_codon_throughput_benchmarks(self):
        """Test throughput performance for Codon analytics operations"""

        def throughput_operation_codon(data_size: int) -> List[float]:
            """Simulated Codon implementation for throughput testing"""
            # Simulate Codon processing
            import time

            time.sleep(0.0001 * data_size / 100)  # Simulate Codon processing

            return [float(i) / data_size for i in range(data_size)]

        # Test throughput with different data sizes
        for size_name, size in [("small", 100), ("medium", 1000), ("large", 10000)]:

            codon_result = await self.benchmarker.benchmark_throughput(
                throughput_operation_codon,
                f"throughput_{size_name}",
                ImplementationType.CONDON,
                data_size=size,
                time_limit=5.0,
                data_size_param=size,
            )

            self.test_results.append(codon_result)
            assert codon_result.throughput is not None
            assert codon_result.throughput > 0


# Integration test utilities
async def run_analytics_performance_tests() -> Dict[str, Any]:
    """Run comprehensive analytics performance tests"""
    logger.info("Running analytics performance tests")

    results = {
        "cpython_results": [],
        "codon_results": [],
        "summary": {"total_tests": 0, "cpython_tests": 0, "codon_tests": 0},
    }

    # Run CPython tests
    cpython_tester = TestAnalyticsOperationsPerformance()
    cpython_tester.setup_method()

    cpython_test_methods = [
        cpython_tester.test_graph_construction_performance,
        cpython_tester.test_centrality_calculation_performance,
        cpython_tester.test_community_detection_performance,
        cpython_tester.test_path_analysis_performance,
        cpython_tester.test_memory_intensive_operations,
        cpython_tester.test_cpu_intensive_operations,
        cpython_tester.test_throughput_benchmarks,
    ]

    for test_method in cpython_test_methods:
        try:
            await test_method()
            results["cpython_results"].extend(cpython_tester.test_results)
            results["summary"]["cpython_tests"] += 1
        except Exception as e:
            logger.error(f"CPython test {test_method.__name__} failed: {e}")
        finally:
            results["summary"]["total_tests"] += 1

    # Run Codon tests
    codon_tester = TestCodonAnalyticsOperations()
    codon_tester.setup_method()

    codon_test_methods = [
        codon_tester.test_codon_graph_construction_performance,
        codon_tester.test_codon_centrality_calculation_performance,
        codon_tester.test_codon_memory_intensive_operations,
        codon_tester.test_codon_throughput_benchmarks,
    ]

    for test_method in codon_test_methods:
        try:
            await test_method()
            results["codon_results"].extend(codon_tester.test_results)
            results["summary"]["codon_tests"] += 1
        except Exception as e:
            logger.error(f"Codon test {test_method.__name__} failed: {e}")
        finally:
            results["summary"]["total_tests"] += 1

    return results


if __name__ == "__main__":
    # Run the performance tests
    asyncio.run(run_analytics_performance_tests())
