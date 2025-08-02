"""
Codon Performance Datasets for Test Fixtures

This module provides comprehensive performance test datasets for Codon components,
including scalable test data, benchmark datasets, and performance metrics.
"""

import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from faker import Faker

# Initialize Faker for generating realistic test data
fake = Faker()


@dataclass
class PerformanceDataset:
    """Performance test dataset"""

    name: str
    size: int
    data: Dict[str, Any]
    expected_performance: Dict[str, float]
    complexity: str  # "low", "medium", "high"


@dataclass
class BenchmarkDataset:
    """Benchmark test dataset"""

    name: str
    interpreted_baseline: float
    compiled_target: float
    memory_limit: float
    iterations: int
    test_data: Dict[str, Any]


class CodonPerformanceDatasets:
    """Comprehensive performance datasets for Codon testing"""

    def __init__(self):
        self.fake = Faker()
        self.complexity_levels = ["low", "medium", "high"]

    def generate_mathematical_datasets(self) -> List[PerformanceDataset]:
        """Generate mathematical computation datasets"""
        datasets = []

        # Small dataset
        datasets.append(
            PerformanceDataset(
                name="small_math_operations",
                size=1000,
                data={
                    "numbers": list(range(1, 1001)),
                    "operations": ["add", "multiply", "divide", "power"],
                    "iterations": 1000,
                },
                expected_performance={
                    "max_time": 0.1,
                    "max_memory": 50.0,
                    "speedup_min": 5.0,
                },
                complexity="low",
            )
        )

        # Medium dataset
        datasets.append(
            PerformanceDataset(
                name="medium_math_operations",
                size=10000,
                data={
                    "numbers": list(range(1, 10001)),
                    "operations": ["add", "multiply", "divide", "power", "sqrt"],
                    "iterations": 5000,
                },
                expected_performance={
                    "max_time": 1.0,
                    "max_memory": 200.0,
                    "speedup_min": 10.0,
                },
                complexity="medium",
            )
        )

        # Large dataset
        datasets.append(
            PerformanceDataset(
                name="large_math_operations",
                size=100000,
                data={
                    "numbers": list(range(1, 100001)),
                    "operations": ["add", "multiply", "divide", "power", "sqrt", "log"],
                    "iterations": 10000,
                },
                expected_performance={
                    "max_time": 5.0,
                    "max_memory": 500.0,
                    "speedup_min": 15.0,
                },
                complexity="high",
            )
        )

        return datasets

    def generate_string_processing_datasets(self) -> List[PerformanceDataset]:
        """Generate string processing datasets"""
        datasets = []

        # Small text dataset
        small_texts = [fake.text(100) for _ in range(100)]
        datasets.append(
            PerformanceDataset(
                name="small_text_processing",
                size=100,
                data={
                    "texts": small_texts,
                    "operations": ["upper", "lower", "replace", "split"],
                    "iterations": 500,
                },
                expected_performance={
                    "max_time": 0.2,
                    "max_memory": 100.0,
                    "speedup_min": 3.0,
                },
                complexity="low",
            )
        )

        # Medium text dataset
        medium_texts = [fake.text(500) for _ in range(500)]
        datasets.append(
            PerformanceDataset(
                name="medium_text_processing",
                size=500,
                data={
                    "texts": medium_texts,
                    "operations": ["upper", "lower", "replace", "split", "join"],
                    "iterations": 1000,
                },
                expected_performance={
                    "max_time": 1.0,
                    "max_memory": 300.0,
                    "speedup_min": 5.0,
                },
                complexity="medium",
            )
        )

        # Large text dataset
        large_texts = [fake.text(1000) for _ in range(1000)]
        datasets.append(
            PerformanceDataset(
                name="large_text_processing",
                size=1000,
                data={
                    "texts": large_texts,
                    "operations": [
                        "upper",
                        "lower",
                        "replace",
                        "split",
                        "join",
                        "strip",
                    ],
                    "iterations": 2000,
                },
                expected_performance={
                    "max_time": 3.0,
                    "max_memory": 600.0,
                    "speedup_min": 8.0,
                },
                complexity="high",
            )
        )

        return datasets

    def generate_array_processing_datasets(self) -> List[PerformanceDataset]:
        """Generate array processing datasets"""
        datasets = []

        # Small arrays
        small_arrays = [[random.randint(1, 100) for _ in range(50)] for _ in range(100)]
        datasets.append(
            PerformanceDataset(
                name="small_array_processing",
                size=100,
                data={
                    "arrays": small_arrays,
                    "operations": ["sum", "max", "min", "sort"],
                    "iterations": 300,
                },
                expected_performance={
                    "max_time": 0.3,
                    "max_memory": 150.0,
                    "speedup_min": 8.0,
                },
                complexity="low",
            )
        )

        # Medium arrays
        medium_arrays = [
            [random.randint(1, 1000) for _ in range(200)] for _ in range(500)
        ]
        datasets.append(
            PerformanceDataset(
                name="medium_array_processing",
                size=500,
                data={
                    "arrays": medium_arrays,
                    "operations": ["sum", "max", "min", "sort", "filter"],
                    "iterations": 600,
                },
                expected_performance={
                    "max_time": 1.5,
                    "max_memory": 400.0,
                    "speedup_min": 12.0,
                },
                complexity="medium",
            )
        )

        # Large arrays
        large_arrays = [
            [random.randint(1, 10000) for _ in range(500)] for _ in range(1000)
        ]
        datasets.append(
            PerformanceDataset(
                name="large_array_processing",
                size=1000,
                data={
                    "arrays": large_arrays,
                    "operations": ["sum", "max", "min", "sort", "filter", "map"],
                    "iterations": 1000,
                },
                expected_performance={
                    "max_time": 4.0,
                    "max_memory": 800.0,
                    "speedup_min": 18.0,
                },
                complexity="high",
            )
        )

        return datasets

    def generate_graph_algorithm_datasets(self) -> List[PerformanceDataset]:
        """Generate graph algorithm datasets"""
        datasets = []

        # Small graph
        small_graph = self._generate_graph_data(100, 300)
        datasets.append(
            PerformanceDataset(
                name="small_graph_algorithms",
                size=100,
                data={
                    "graph": small_graph,
                    "algorithms": ["bfs", "dfs", "shortest_path"],
                    "iterations": 50,
                },
                expected_performance={
                    "max_time": 0.5,
                    "max_memory": 200.0,
                    "speedup_min": 10.0,
                },
                complexity="low",
            )
        )

        # Medium graph
        medium_graph = self._generate_graph_data(500, 1500)
        datasets.append(
            PerformanceDataset(
                name="medium_graph_algorithms",
                size=500,
                data={
                    "graph": medium_graph,
                    "algorithms": [
                        "bfs",
                        "dfs",
                        "shortest_path",
                        "connected_components",
                    ],
                    "iterations": 100,
                },
                expected_performance={
                    "max_time": 2.0,
                    "max_memory": 500.0,
                    "speedup_min": 15.0,
                },
                complexity="medium",
            )
        )

        # Large graph
        large_graph = self._generate_graph_data(2000, 8000)
        datasets.append(
            PerformanceDataset(
                name="large_graph_algorithms",
                size=2000,
                data={
                    "graph": large_graph,
                    "algorithms": [
                        "bfs",
                        "dfs",
                        "shortest_path",
                        "connected_components",
                        "mst",
                    ],
                    "iterations": 200,
                },
                expected_performance={
                    "max_time": 8.0,
                    "max_memory": 1000.0,
                    "speedup_min": 25.0,
                },
                complexity="high",
            )
        )

        return datasets

    def generate_benchmark_datasets(self) -> List[BenchmarkDataset]:
        """Generate benchmark datasets for performance comparison"""
        datasets = []

        # Fibonacci benchmark
        datasets.append(
            BenchmarkDataset(
                name="fibonacci_benchmark",
                interpreted_baseline=10.0,
                compiled_target=0.2,
                memory_limit=100.0,
                iterations=1000,
                test_data={"n": 40},
            )
        )

        # Matrix multiplication benchmark
        datasets.append(
            BenchmarkDataset(
                name="matrix_multiplication_benchmark",
                interpreted_baseline=5.0,
                compiled_target=0.1,
                memory_limit=200.0,
                iterations=500,
                test_data={"size": 100},
            )
        )

        # Sorting benchmark
        datasets.append(
            BenchmarkDataset(
                name="sorting_benchmark",
                interpreted_baseline=3.0,
                compiled_target=0.05,
                memory_limit=150.0,
                iterations=800,
                test_data={"size": 10000},
            )
        )

        # String processing benchmark
        datasets.append(
            BenchmarkDataset(
                name="string_processing_benchmark",
                interpreted_baseline=2.0,
                compiled_target=0.1,
                memory_limit=100.0,
                iterations=1000,
                test_data={"text_count": 1000, "text_length": 500},
            )
        )

        return datasets

    def generate_memory_usage_datasets(self) -> List[PerformanceDataset]:
        """Generate memory usage test datasets"""
        datasets = []

        # Memory-intensive operations
        datasets.append(
            PerformanceDataset(
                name="memory_intensive_operations",
                size=10000,
                data={
                    "large_arrays": [
                        [random.random() for _ in range(1000)] for _ in range(100)
                    ],
                    "operations": ["copy", "transform", "aggregate"],
                    "iterations": 100,
                },
                expected_performance={
                    "max_time": 3.0,
                    "max_memory": 800.0,
                    "speedup_min": 8.0,
                },
                complexity="high",
            )
        )

        return datasets

    def _generate_graph_data(self, nodes: int, edges: int) -> Dict[str, Any]:
        """Generate graph data for testing"""
        adjacency_list = {i: [] for i in range(nodes)}

        for _ in range(edges):
            node1 = random.randint(0, nodes - 1)
            node2 = random.randint(0, nodes - 1)
            if node1 != node2 and node2 not in adjacency_list[node1]:
                adjacency_list[node1].append(node2)

        return {
            "adjacency_list": adjacency_list,
            "nodes": nodes,
            "edges": edges,
            "start_node": 0,
        }

    def get_all_datasets(self) -> Dict[str, List[PerformanceDataset]]:
        """Get all performance datasets organized by category"""
        return {
            "mathematical": self.generate_mathematical_datasets(),
            "string_processing": self.generate_string_processing_datasets(),
            "array_processing": self.generate_array_processing_datasets(),
            "graph_algorithms": self.generate_graph_algorithm_datasets(),
            "memory_usage": self.generate_memory_usage_datasets(),
        }

    def get_benchmark_datasets(self) -> List[BenchmarkDataset]:
        """Get all benchmark datasets"""
        return self.generate_benchmark_datasets()


# Pytest fixtures
@pytest.fixture
def codon_performance_datasets():
    """Fixture providing Codon performance datasets"""
    return CodonPerformanceDatasets()


@pytest.fixture
def mathematical_datasets(codon_performance_datasets):
    """Fixture providing mathematical datasets"""
    return codon_performance_datasets.generate_mathematical_datasets()


@pytest.fixture
def string_processing_datasets(codon_performance_datasets):
    """Fixture providing string processing datasets"""
    return codon_performance_datasets.generate_string_processing_datasets()


@pytest.fixture
def array_processing_datasets(codon_performance_datasets):
    """Fixture providing array processing datasets"""
    return codon_performance_datasets.generate_array_processing_datasets()


@pytest.fixture
def graph_algorithm_datasets(codon_performance_datasets):
    """Fixture providing graph algorithm datasets"""
    return codon_performance_datasets.generate_graph_algorithm_datasets()


@pytest.fixture
def benchmark_datasets(codon_performance_datasets):
    """Fixture providing benchmark datasets"""
    return codon_performance_datasets.generate_benchmark_datasets()


@pytest.fixture
def all_performance_datasets(codon_performance_datasets):
    """Fixture providing all performance datasets"""
    return codon_performance_datasets.get_all_datasets()
