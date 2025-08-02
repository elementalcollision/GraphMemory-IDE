"""
Enhanced Test Data Generators for Codon Components

This module provides comprehensive test data generators for Codon components,
including analytics data, performance metrics, and validation utilities.
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
class CodonTestData:
    """Comprehensive test data for Codon components"""

    compilation_data: Dict[str, Any]
    performance_data: Dict[str, Any]
    analytics_data: Dict[str, Any]
    error_data: Dict[str, Any]
    validation_data: Dict[str, Any]


class CodonDataGenerators:
    """Enhanced data generators for Codon testing"""

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

    def generate_compilation_test_data(self, count: int = 20) -> List[Dict[str, Any]]:
        """Generate comprehensive compilation test data"""
        test_data = []

        # Valid compilation tests
        for i in range(count // 2):
            test_data.append(
                {
                    "test_id": f"compilation_valid_{i}",
                    "source_code": self._generate_valid_codon_code(),
                    "expected_success": True,
                    "expected_warnings": [],
                    "optimization_level": random.choice(self.optimization_levels),
                    "target_platform": random.choice(self.target_platforms),
                    "timeout_seconds": random.randint(10, 60),
                    "complexity": random.choice(["low", "medium", "high"]),
                }
            )

        # Invalid compilation tests
        for i in range(count // 2):
            test_data.append(
                {
                    "test_id": f"compilation_invalid_{i}",
                    "source_code": self._generate_invalid_codon_code(),
                    "expected_success": False,
                    "expected_warnings": self._generate_expected_warnings(),
                    "optimization_level": random.choice(self.optimization_levels),
                    "target_platform": random.choice(self.target_platforms),
                    "timeout_seconds": random.randint(10, 60),
                    "complexity": random.choice(["low", "medium", "high"]),
                }
            )

        return test_data

    def generate_performance_test_data(self, count: int = 15) -> List[Dict[str, Any]]:
        """Generate comprehensive performance test data"""
        test_data = []

        # Mathematical operations
        for i in range(count // 3):
            test_data.append(
                {
                    "test_id": f"performance_math_{i}",
                    "test_type": "mathematical",
                    "interpreted_code": self._generate_math_operations_code(),
                    "compiled_code": self._generate_math_operations_code(),
                    "test_data": {
                        "iterations": random.randint(1000, 10000),
                        "numbers": list(range(1, random.randint(100, 1001))),
                    },
                    "expected_speedup_min": random.uniform(5.0, 50.0),
                    "expected_memory_usage_max": random.uniform(50.0, 500.0),
                    "complexity": random.choice(["low", "medium", "high"]),
                }
            )

        # String processing
        for i in range(count // 3):
            test_data.append(
                {
                    "test_id": f"performance_string_{i}",
                    "test_type": "string_processing",
                    "interpreted_code": self._generate_string_processing_code(),
                    "compiled_code": self._generate_string_processing_code(),
                    "test_data": {
                        "strings": [
                            fake.text() for _ in range(random.randint(100, 1000))
                        ],
                        "operations": ["upper", "lower", "replace", "split"],
                    },
                    "expected_speedup_min": random.uniform(3.0, 20.0),
                    "expected_memory_usage_max": random.uniform(100.0, 800.0),
                    "complexity": random.choice(["low", "medium", "high"]),
                }
            )

        # Array operations
        for i in range(count // 3):
            test_data.append(
                {
                    "test_id": f"performance_array_{i}",
                    "test_type": "array_processing",
                    "interpreted_code": self._generate_array_operations_code(),
                    "compiled_code": self._generate_array_operations_code(),
                    "test_data": {
                        "arrays": [
                            [
                                random.randint(1, 1000)
                                for _ in range(random.randint(50, 500))
                            ]
                            for _ in range(random.randint(20, 100))
                        ],
                        "operations": ["sum", "max", "min", "sort", "filter"],
                    },
                    "expected_speedup_min": random.uniform(8.0, 30.0),
                    "expected_memory_usage_max": random.uniform(150.0, 1000.0),
                    "complexity": random.choice(["low", "medium", "high"]),
                }
            )

        return test_data

    def generate_analytics_test_data(self, count: int = 12) -> List[Dict[str, Any]]:
        """Generate comprehensive analytics test data"""
        test_data = []

        # Graph algorithms
        for i in range(count // 3):
            graph_size = random.randint(50, 1000)
            test_data.append(
                {
                    "test_id": f"analytics_graph_{i}",
                    "algorithm_type": "graph_traversal",
                    "input_data": self._generate_graph_data(graph_size, graph_size * 3),
                    "expected_output": {
                        "traversal_order": list(range(min(100, graph_size))),
                        "depth": random.randint(3, 10),
                        "visited_nodes": random.randint(graph_size // 2, graph_size),
                    },
                    "performance_constraints": {
                        "max_time": random.uniform(0.5, 5.0),
                        "max_memory": random.uniform(100.0, 1000.0),
                    },
                    "complexity": "high" if graph_size > 500 else "medium",
                }
            )

        # Pattern matching
        for i in range(count // 3):
            test_data.append(
                {
                    "test_id": f"analytics_pattern_{i}",
                    "algorithm_type": "pattern_matching",
                    "input_data": {
                        "text": fake.text(random.randint(500, 2000)),
                        "pattern": fake.word(),
                    },
                    "expected_output": {
                        "matches": [
                            random.randint(0, 100) for _ in range(random.randint(1, 5))
                        ],
                        "count": random.randint(1, 10),
                    },
                    "performance_constraints": {
                        "max_time": random.uniform(0.1, 1.0),
                        "max_memory": random.uniform(50.0, 300.0),
                    },
                    "complexity": random.choice(["low", "medium"]),
                }
            )

        # Clustering
        for i in range(count // 3):
            point_count = random.randint(100, 2000)
            test_data.append(
                {
                    "test_id": f"analytics_clustering_{i}",
                    "algorithm_type": "clustering",
                    "input_data": {
                        "points": [
                            [random.uniform(0, 100), random.uniform(0, 100)]
                            for _ in range(point_count)
                        ]
                    },
                    "expected_output": {
                        "clusters": random.randint(3, 8),
                        "centroids": [
                            [random.uniform(0, 100), random.uniform(0, 100)]
                            for _ in range(5)
                        ],
                        "silhouette_score": random.uniform(0.3, 0.9),
                    },
                    "performance_constraints": {
                        "max_time": random.uniform(1.0, 10.0),
                        "max_memory": random.uniform(200.0, 1500.0),
                    },
                    "complexity": "high" if point_count > 1000 else "medium",
                }
            )

        return test_data

    def generate_error_test_data(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate comprehensive error test data"""
        test_data = []

        # Compilation errors
        for i in range(count // 2):
            test_data.append(
                {
                    "test_id": f"error_compilation_{i}",
                    "error_type": "compilation",
                    "invalid_code": self._generate_invalid_codon_code(),
                    "expected_error_type": random.choice(
                        ["syntax", "type", "semantic"]
                    ),
                    "expected_error_pattern": random.choice(
                        [
                            "undefined variable",
                            "type mismatch",
                            "syntax error",
                            "missing import",
                        ]
                    ),
                    "recovery_strategy": random.choice(["skip", "retry", "fallback"]),
                    "complexity": random.choice(["low", "medium", "high"]),
                }
            )

        # Runtime errors
        for i in range(count // 2):
            test_data.append(
                {
                    "test_id": f"error_runtime_{i}",
                    "error_type": "runtime",
                    "error_func": self._generate_error_function(),
                    "expected_error_type": random.choice(
                        ["ValueError", "TypeError", "IndexError", "KeyError"]
                    ),
                    "expected_error_message": fake.sentence(),
                    "recovery_strategy": random.choice(["skip", "retry", "fallback"]),
                    "complexity": random.choice(["low", "medium", "high"]),
                }
            )

        return test_data

    def generate_validation_test_data(self) -> Dict[str, Any]:
        """Generate validation test data"""
        return {
            "data_validators": {
                "compilation_result": self._generate_compilation_validator(),
                "performance_result": self._generate_performance_validator(),
                "analytics_result": self._generate_analytics_validator(),
                "error_result": self._generate_error_validator(),
            },
            "test_scenarios": [
                "normal_operation",
                "edge_cases",
                "error_conditions",
                "performance_regression",
                "memory_leaks",
                "thread_safety",
            ],
            "validation_rules": {
                "compilation_success_rate": 0.9,
                "performance_speedup_min": 5.0,
                "memory_usage_max": 1000.0,
                "error_recovery_rate": 0.8,
            },
        }

    def generate_comprehensive_test_data(self) -> CodonTestData:
        """Generate comprehensive test data for all Codon components"""
        return CodonTestData(
            compilation_data=self.generate_compilation_test_data(),
            performance_data=self.generate_performance_test_data(),
            analytics_data=self.generate_analytics_test_data(),
            error_data=self.generate_error_test_data(),
            validation_data=self.generate_validation_test_data(),
        )

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

    def _generate_error_function(self) -> str:
        """Generate error function for testing"""
        error_functions = [
            "def error_func(): raise ValueError('Test error')",
            "def error_func(): return 1 / 0",
            "def error_func(): return undefined_var",
            "def error_func(): return [1, 2, 3][10]",
        ]
        return random.choice(error_functions)

    def _generate_compilation_validator(self) -> Dict[str, Any]:
        """Generate compilation result validator"""
        return {
            "required_fields": ["success", "compilation_time", "optimization_level"],
            "success_criteria": {
                "success_rate_min": 0.9,
                "compilation_time_max": 10.0,
                "warning_count_max": 5,
            },
        }

    def _generate_performance_validator(self) -> Dict[str, Any]:
        """Generate performance result validator"""
        return {
            "required_fields": ["speedup_ratio", "memory_usage", "cpu_usage"],
            "success_criteria": {
                "speedup_ratio_min": 5.0,
                "memory_usage_max": 1000.0,
                "cpu_usage_max": 100.0,
            },
        }

    def _generate_analytics_validator(self) -> Dict[str, Any]:
        """Generate analytics result validator"""
        return {
            "required_fields": ["execution_time", "memory_usage", "result"],
            "success_criteria": {
                "execution_time_max": 10.0,
                "memory_usage_max": 2000.0,
                "accuracy_min": 0.8,
            },
        }

    def _generate_error_validator(self) -> Dict[str, Any]:
        """Generate error result validator"""
        return {
            "required_fields": ["error_type", "error_message", "handled_correctly"],
            "success_criteria": {
                "error_detection_rate": 0.95,
                "recovery_success_rate": 0.8,
                "false_positive_rate_max": 0.1,
            },
        }


# Pytest fixtures
@pytest.fixture
def codon_data_generators():
    """Fixture providing Codon data generators"""
    return CodonDataGenerators()


@pytest.fixture
def compilation_test_data(codon_data_generators):
    """Fixture providing compilation test data"""
    return codon_data_generators.generate_compilation_test_data()


@pytest.fixture
def performance_test_data(codon_data_generators):
    """Fixture providing performance test data"""
    return codon_data_generators.generate_performance_test_data()


@pytest.fixture
def analytics_test_data(codon_data_generators):
    """Fixture providing analytics test data"""
    return codon_data_generators.generate_analytics_test_data()


@pytest.fixture
def error_test_data(codon_data_generators):
    """Fixture providing error test data"""
    return codon_data_generators.generate_error_test_data()


@pytest.fixture
def validation_test_data(codon_data_generators):
    """Fixture providing validation test data"""
    return codon_data_generators.generate_validation_test_data()


@pytest.fixture
def comprehensive_test_data(codon_data_generators):
    """Fixture providing comprehensive test data"""
    return codon_data_generators.generate_comprehensive_test_data()
