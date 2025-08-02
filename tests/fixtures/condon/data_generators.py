"""
Codon Data Generators for Test Fixtures

This module provides comprehensive data generators for Codon components,
including compilation test data, performance benchmarks, and analytics datasets.
"""

import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytest
from faker import Faker

# Initialize Faker for generating realistic test data
fake = Faker()


@dataclass
class CodonCompilationTest:
    """Test case for Codon compilation"""

    name: str
    source_code: str
    expected_success: bool
    expected_warnings: List[str]
    optimization_level: str
    target_platform: str
    timeout_seconds: int = 30


@dataclass
class CodonPerformanceTest:
    """Test case for Codon performance benchmarking"""

    name: str
    interpreted_code: str
    compiled_code: str
    test_data: Dict[str, Any]
    iterations: int
    expected_speedup_min: float
    expected_memory_usage_max: float


@dataclass
class CodonAnalyticsTest:
    """Test case for Codon analytics components"""

    name: str
    algorithm_type: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    performance_constraints: Dict[str, float]


class CodonDataGenerator:
    """Comprehensive data generator for Codon test fixtures"""

    def __init__(self):
        self.fake = Faker()
        self.algorithm_types = [
            "graph_traversal",
            "pattern_matching",
            "clustering",
            "anomaly_detection",
            "correlation_analysis",
            "prediction",
        ]
        self.optimization_levels = ["O0", "O1", "O2", "O3"]
        self.target_platforms = ["native", "x86_64", "aarch64"]

    def generate_compilation_tests(
        self, count: int = 10
    ) -> List[CodonCompilationTest]:
        """Generate compilation test cases for Codon"""
        tests = []

        # Valid compilation tests
        for i in range(count // 2):
            test = CodonCompilationTest(
                name=f"valid_compilation_{i}",
                source_code=self._generate_valid_codon_code(),
                expected_success=True,
                expected_warnings=[],
                optimization_level=random.choice(self.optimization_levels),
                target_platform=random.choice(self.target_platforms),
            )
            tests.append(test)

        # Invalid compilation tests
        for i in range(count // 2):
            test = CodonCompilationTest(
                name=f"invalid_compilation_{i}",
                source_code=self._generate_invalid_codon_code(),
                expected_success=False,
                expected_warnings=self._generate_expected_warnings(),
                optimization_level=random.choice(self.optimization_levels),
                target_platform=random.choice(self.target_platforms),
            )
            tests.append(test)

        return tests

    def generate_performance_tests(self, count: int = 8) -> List[CodonPerformanceTest]:
        """Generate performance test cases for Codon"""
        tests = []

        # Mathematical operations
        tests.append(
            CodonPerformanceTest(
                name="mathematical_operations",
                interpreted_code=self._generate_math_operations_code(),
                compiled_code=self._generate_math_operations_code(),
                test_data={"iterations": 10000, "numbers": list(range(1, 1001))},
                iterations=1000,
                expected_speedup_min=10.0,
                expected_memory_usage_max=100.0,
            )
        )

        # String processing
        tests.append(
            CodonPerformanceTest(
                name="string_processing",
                interpreted_code=self._generate_string_processing_code(),
                compiled_code=self._generate_string_processing_code(),
                test_data={"strings": [fake.text() for _ in range(1000)]},
                iterations=500,
                expected_speedup_min=5.0,
                expected_memory_usage_max=200.0,
            )
        )

        # Array operations
        tests.append(
            CodonPerformanceTest(
                name="array_operations",
                interpreted_code=self._generate_array_operations_code(),
                compiled_code=self._generate_array_operations_code(),
                test_data={
                    "arrays": [
                        [random.randint(1, 1000) for _ in range(100)] for _ in range(50)
                    ]
                },
                iterations=300,
                expected_speedup_min=15.0,
                expected_memory_usage_max=150.0,
            )
        )

        # Graph algorithms
        tests.append(
            CodonPerformanceTest(
                name="graph_algorithms",
                interpreted_code=self._generate_graph_algorithm_code(),
                compiled_code=self._generate_graph_algorithm_code(),
                test_data={"graph_size": 1000, "edges": 5000},
                iterations=100,
                expected_speedup_min=20.0,
                expected_memory_usage_max=500.0,
            )
        )

        return tests

    def generate_analytics_tests(self, count: int = 6) -> List[CodonAnalyticsTest]:
        """Generate analytics test cases for Codon components"""
        tests = []

        # Graph traversal
        tests.append(
            CodonAnalyticsTest(
                name="graph_traversal_bfs",
                algorithm_type="graph_traversal",
                input_data=self._generate_graph_data(100, 500),
                expected_output={"traversal_order": list(range(100)), "depth": 5},
                performance_constraints={"max_time": 1.0, "max_memory": 100.0},
            )
        )

        # Pattern matching
        tests.append(
            CodonAnalyticsTest(
                name="pattern_matching_kmp",
                algorithm_type="pattern_matching",
                input_data={"text": fake.text(1000), "pattern": fake.word()},
                expected_output={"matches": [10, 25, 40], "count": 3},
                performance_constraints={"max_time": 0.5, "max_memory": 50.0},
            )
        )

        # Clustering
        tests.append(
            CodonAnalyticsTest(
                name="clustering_kmeans",
                algorithm_type="clustering",
                input_data={
                    "points": [
                        [random.uniform(0, 100), random.uniform(0, 100)]
                        for _ in range(1000)
                    ]
                },
                expected_output={
                    "clusters": 5,
                    "centroids": [[50, 50], [25, 25], [75, 75], [25, 75], [75, 25]],
                },
                performance_constraints={"max_time": 2.0, "max_memory": 200.0},
            )
        )

        return tests

    def generate_mock_compilation_results(self) -> Dict[str, Any]:
        """Generate mock compilation results for testing"""
        return {
            "success": random.choice([True, False]),
            "compilation_time": random.uniform(0.1, 10.0),
            "executable_size": random.randint(1000, 1000000),
            "error_message": fake.sentence() if random.random() < 0.3 else None,
            "warnings": [fake.sentence() for _ in range(random.randint(0, 3))],
            "optimization_level": random.choice(self.optimization_levels),
            "target_platform": random.choice(self.target_platforms),
            "memory_usage": random.uniform(10.0, 500.0),
            "cpu_usage": random.uniform(10.0, 100.0),
        }

    def generate_performance_benchmark_data(self) -> Dict[str, Any]:
        """Generate performance benchmark data"""
        return {
            "test_name": fake.word(),
            "interpreted_time": random.uniform(1.0, 100.0),
            "compiled_time": random.uniform(0.01, 10.0),
            "speedup_ratio": random.uniform(5.0, 100.0),
            "memory_usage": random.uniform(10.0, 500.0),
            "cpu_usage": random.uniform(10.0, 100.0),
            "iterations": random.randint(100, 10000),
            "baseline_time": random.uniform(0.5, 50.0),
            "regression_percentage": random.uniform(-10.0, 10.0),
        }

    def _generate_valid_codon_code(self) -> str:
        """Generate valid Codon code for testing"""
        code_templates = [
            """
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def main():
    result = fibonacci(40)
    print(f"Fibonacci(40) = {result}")
""",
            """
def matrix_multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    rows_a = len(a)
    cols_a = len(a[0])
    cols_b = len(b[0])
    
    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    
    return result
""",
            """
def quicksort(arr: List[int]) -> List[int]:
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quicksort(left) + middle + quicksort(right)
""",
        ]
        return random.choice(code_templates)

    def _generate_invalid_codon_code(self) -> str:
        """Generate invalid Codon code for testing"""
        invalid_templates = [
            """
def invalid_function():
    return undefined_variable  # Undefined variable
""",
            """
def type_error_function(x: int) -> str:
    return x + "string"  # Type error
""",
            """
def syntax_error_function(
    # Missing closing parenthesis
""",
            """
def runtime_error_function():
    return 1 / 0  # Division by zero
""",
        ]
        return random.choice(invalid_templates)

    def _generate_expected_warnings(self) -> List[str]:
        """Generate expected warning messages"""
        warnings = [
            "Unused variable 'x'",
            "Function 'test' is never called",
            "Import 'unused_module' is not used",
            "Variable 'result' is assigned but never used",
        ]
        return random.sample(warnings, random.randint(0, 2))

    def _generate_math_operations_code(self) -> str:
        """Generate mathematical operations code"""
        return """
def math_operations():
    result = 0
    for i in range(10000):
        result += i * i
        result -= i
        result *= 2
        result //= 3
    return result
"""

    def _generate_string_processing_code(self) -> str:
        """Generate string processing code"""
        return """
def string_processing(texts: List[str]) -> List[str]:
    results = []
    for text in texts:
        processed = text.upper()
        processed = processed.replace(" ", "_")
        processed = processed[:100]
        results.append(processed)
    return results
"""

    def _generate_array_operations_code(self) -> str:
        """Generate array operations code"""
        return """
def array_operations(arrays: List[List[int]]) -> List[int]:
    results = []
    for arr in arrays:
        total = sum(arr)
        avg = total // len(arr)
        max_val = max(arr)
        min_val = min(arr)
        results.append(total + avg + max_val + min_val)
    return results
"""

    def _generate_graph_algorithm_code(self) -> str:
        """Generate graph algorithm code"""
        return """
def graph_algorithm(adjacency_list: Dict[int, List[int]], start: int) -> List[int]:
    visited = set()
    queue = [start]
    result = []
    
    while queue:
        node = queue.pop(0)
        if node not in visited:
            visited.add(node)
            result.append(node)
            for neighbor in adjacency_list.get(node, []):
                if neighbor not in visited:
                    queue.append(neighbor)
    
    return result
"""

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


# Pytest fixtures
@pytest.fixture
def codon_data_generator():
    """Fixture providing Codon data generator"""
    return CodonDataGenerator()


@pytest.fixture
def compilation_tests(codon_data_generator):
    """Fixture providing compilation test cases"""
    return codon_data_generator.generate_compilation_tests()


@pytest.fixture
def performance_tests(codon_data_generator):
    """Fixture providing performance test cases"""
    return codon_data_generator.generate_performance_tests()


@pytest.fixture
def analytics_tests(codon_data_generator):
    """Fixture providing analytics test cases"""
    return codon_data_generator.generate_analytics_tests()


@pytest.fixture
def mock_compilation_results(codon_data_generator):
    """Fixture providing mock compilation results"""
    return codon_data_generator.generate_mock_compilation_results()


@pytest.fixture
def performance_benchmark_data(codon_data_generator):
    """Fixture providing performance benchmark data"""
    return codon_data_generator.generate_performance_benchmark_data()
