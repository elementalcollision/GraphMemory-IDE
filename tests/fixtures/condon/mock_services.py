"""
Codon Mock Services for Test Fixtures

This module provides mock implementations of Codon-related services
for comprehensive testing of Codon components.
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


@dataclass
class MockCompilationService:
    """Mock service for Codon compilation operations"""

    def __init__(self):
        self.compilation_history = []
        self.success_rate = 0.9
        self.avg_compilation_time = 2.0

    async def compile_code(
        self, source_code: str, optimization_level: str = "O2"
    ) -> Dict[str, Any]:
        """Mock compilation of Codon code"""
        start_time = time.time()

        # Simulate compilation time
        await asyncio.sleep(random.uniform(0.1, 0.5))

        success = random.random() < self.success_rate
        compilation_time = time.time() - start_time

        result = {
            "success": success,
            "compilation_time": compilation_time,
            "executable_size": random.randint(1000, 1000000) if success else None,
            "error_message": None if success else "Mock compilation error",
            "warnings": [],
            "optimization_level": optimization_level,
            "target_platform": "native",
        }

        self.compilation_history.append(
            {
                "source_code": source_code[:100],  # Truncate for storage
                "result": result,
                "timestamp": time.time(),
            }
        )

        return result

    def get_compilation_stats(self) -> Dict[str, Any]:
        """Get compilation statistics"""
        if not self.compilation_history:
            return {"total_compilations": 0, "success_rate": 0.0}

        total = len(self.compilation_history)
        successful = sum(1 for h in self.compilation_history if h["result"]["success"])

        return {
            "total_compilations": total,
            "successful_compilations": successful,
            "success_rate": successful / total,
            "avg_compilation_time": sum(
                h["result"]["compilation_time"] for h in self.compilation_history
            )
            / total,
        }


@dataclass
class MockPerformanceService:
    """Mock service for Codon performance monitoring"""

    def __init__(self):
        self.performance_history = []
        self.baseline_metrics = {}

    async def benchmark_code(
        self,
        interpreted_func: Callable,
        compiled_func: Callable,
        test_data: Dict[str, Any],
        iterations: int = 1000,
    ) -> Dict[str, Any]:
        """Mock performance benchmarking"""
        start_time = time.time()

        # Simulate benchmark execution
        await asyncio.sleep(random.uniform(0.1, 0.3))

        interpreted_time = random.uniform(1.0, 10.0)
        compiled_time = interpreted_time / random.uniform(5.0, 50.0)  # Speedup
        speedup_ratio = interpreted_time / compiled_time

        result = {
            "test_name": f"benchmark_{int(time.time())}",
            "interpreted_time": interpreted_time,
            "compiled_time": compiled_time,
            "speedup_ratio": speedup_ratio,
            "memory_usage": random.uniform(10.0, 500.0),
            "cpu_usage": random.uniform(10.0, 100.0),
            "iterations": iterations,
            "baseline_time": interpreted_time,
            "regression_percentage": random.uniform(-5.0, 5.0),
        }

        self.performance_history.append(
            {
                "result": result,
                "timestamp": time.time(),
                "test_data_keys": list(test_data.keys()),
            }
        )

        return result

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.performance_history:
            return {"total_benchmarks": 0, "avg_speedup": 0.0}

        total = len(self.performance_history)
        avg_speedup = (
            sum(h["result"]["speedup_ratio"] for h in self.performance_history) / total
        )

        return {
            "total_benchmarks": total,
            "avg_speedup": avg_speedup,
            "max_speedup": max(
                h["result"]["speedup_ratio"] for h in self.performance_history
            ),
            "min_speedup": min(
                h["result"]["speedup_ratio"] for h in self.performance_history
            ),
        }


@dataclass
class MockAnalyticsService:
    """Mock service for Codon analytics components"""

    def __init__(self):
        self.analytics_history = []
        self.algorithm_performance = {}

    async def execute_algorithm(
        self, algorithm_type: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock analytics algorithm execution"""
        start_time = time.time()

        # Simulate algorithm execution time based on type
        execution_times = {
            "graph_traversal": random.uniform(0.1, 1.0),
            "pattern_matching": random.uniform(0.05, 0.5),
            "clustering": random.uniform(0.5, 2.0),
            "anomaly_detection": random.uniform(0.2, 1.5),
            "correlation_analysis": random.uniform(0.3, 1.0),
            "prediction": random.uniform(0.1, 0.8),
        }

        execution_time = execution_times.get(algorithm_type, random.uniform(0.1, 1.0))
        await asyncio.sleep(execution_time)

        # Generate mock results based on algorithm type
        result = self._generate_algorithm_result(algorithm_type, input_data)
        result["execution_time"] = execution_time
        result["memory_usage"] = random.uniform(10.0, 200.0)

        self.analytics_history.append(
            {
                "algorithm_type": algorithm_type,
                "input_data_keys": list(input_data.keys()),
                "result": result,
                "timestamp": time.time(),
            }
        )

        return result

    def _generate_algorithm_result(
        self, algorithm_type: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate mock algorithm results"""
        if algorithm_type == "graph_traversal":
            nodes = input_data.get("nodes", [])
            max_nodes = min(100, len(nodes)) if nodes else 100
            return {
                "traversal_order": list(range(max_nodes)),
                "depth": random.randint(3, 10),
                "visited_nodes": random.randint(50, 200),
                "path_length": random.randint(10, 50),
            }
        elif algorithm_type == "pattern_matching":
            return {
                "matches": [
                    random.randint(0, 100) for _ in range(random.randint(1, 5))
                ],
                "count": random.randint(1, 10),
                "pattern_length": len(input_data.get("pattern", "")),
                "text_length": len(input_data.get("text", "")),
            }
        elif algorithm_type == "clustering":
            return {
                "clusters": random.randint(3, 8),
                "centroids": [
                    [random.uniform(0, 100), random.uniform(0, 100)] for _ in range(5)
                ],
                "silhouette_score": random.uniform(0.3, 0.9),
                "inertia": random.uniform(100, 1000),
            }
        else:
            return {
                "result": "mock_result",
                "confidence": random.uniform(0.5, 1.0),
                "processing_time": random.uniform(0.1, 1.0),
            }

    def get_analytics_stats(self) -> Dict[str, Any]:
        """Get analytics statistics"""
        if not self.analytics_history:
            return {"total_executions": 0, "algorithm_counts": {}}

        algorithm_counts = {}
        for entry in self.analytics_history:
            algo_type = entry["algorithm_type"]
            algorithm_counts[algo_type] = algorithm_counts.get(algo_type, 0) + 1

        return {
            "total_executions": len(self.analytics_history),
            "algorithm_counts": algorithm_counts,
            "avg_execution_time": sum(
                h["result"]["execution_time"] for h in self.analytics_history
            )
            / len(self.analytics_history),
        }


@dataclass
class MockErrorHandlingService:
    """Mock service for Codon error handling"""

    def __init__(self):
        self.error_history = []
        self.recovery_success_rate = 0.8

    async def test_error_handling(
        self, error_func: Callable, expected_error_type: type
    ) -> Dict[str, Any]:
        """Mock error handling test"""
        start_time = time.time()

        try:
            await error_func()
            error_occurred = False
            actual_error_type = None
            error_message = None
        except Exception as e:
            error_occurred = True
            actual_error_type = type(e)
            error_message = str(e)

        execution_time = time.time() - start_time

        # Determine if error was handled correctly
        handled_correctly = error_occurred and isinstance(
            actual_error_type, expected_error_type
        )

        # Simulate recovery attempt
        recovery_successful = (
            random.random() < self.recovery_success_rate if handled_correctly else False
        )

        result = {
            "test_name": f"error_test_{int(time.time())}",
            "error_type": actual_error_type.__name__ if actual_error_type else None,
            "error_message": error_message,
            "handled_correctly": handled_correctly,
            "recovery_successful": recovery_successful,
            "execution_time": execution_time,
        }

        self.error_history.append({"result": result, "timestamp": time.time()})

        return result

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        if not self.error_history:
            return {"total_tests": 0, "success_rate": 0.0}

        total = len(self.error_history)
        successful = sum(
            1 for h in self.error_history if h["result"]["handled_correctly"]
        )

        return {
            "total_tests": total,
            "successful_tests": successful,
            "success_rate": successful / total,
            "recovery_success_rate": sum(
                1 for h in self.error_history if h["result"]["recovery_successful"]
            )
            / total,
        }


class CodonMockServices:
    """Comprehensive mock services for Codon testing"""

    def __init__(self):
        self.compilation_service = MockCompilationService()
        self.performance_service = MockPerformanceService()
        self.analytics_service = MockAnalyticsService()
        self.error_handling_service = MockErrorHandlingService()

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run a comprehensive test using all mock services"""
        results = {}

        # Test compilation
        test_code = "def test_func(): return 42"
        compilation_result = await self.compilation_service.compile_code(test_code)
        results["compilation"] = compilation_result

        # Test performance
        def mock_func():
            return sum(range(1000))

        performance_result = await self.performance_service.benchmark_code(
            mock_func, mock_func, {"test": "data"}, 100
        )
        results["performance"] = performance_result

        # Test analytics
        analytics_result = await self.analytics_service.execute_algorithm(
            "graph_traversal", {"nodes": list(range(100))}
        )
        results["analytics"] = analytics_result

        # Test error handling
        def error_func():
            raise ValueError("Test error")

        error_result = await self.error_handling_service.test_error_handling(
            error_func, ValueError
        )
        results["error_handling"] = error_result

        return results

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics from all mock services"""
        return {
            "compilation": self.compilation_service.get_compilation_stats(),
            "performance": self.performance_service.get_performance_stats(),
            "analytics": self.analytics_service.get_analytics_stats(),
            "error_handling": self.error_handling_service.get_error_stats(),
        }


# Pytest fixtures
@pytest.fixture
def mock_compilation_service():
    """Fixture providing mock compilation service"""
    return MockCompilationService()


@pytest.fixture
def mock_performance_service():
    """Fixture providing mock performance service"""
    return MockPerformanceService()


@pytest.fixture
def mock_analytics_service():
    """Fixture providing mock analytics service"""
    return MockAnalyticsService()


@pytest.fixture
def mock_error_handling_service():
    """Fixture providing mock error handling service"""
    return MockErrorHandlingService()


@pytest.fixture
def codon_mock_services():
    """Fixture providing comprehensive mock services"""
    return CodonMockServices()


@pytest.fixture
async def comprehensive_test_results(codon_mock_services):
    """Fixture providing comprehensive test results"""
    return await codon_mock_services.run_comprehensive_test()


@pytest.fixture
def mock_services_stats(codon_mock_services):
    """Fixture providing mock services statistics"""
    return codon_mock_services.get_all_stats()
