"""
Unit tests for Algorithms component using Codon framework

This module provides comprehensive unit tests for the algorithms component,
including compilation testing, performance benchmarking, and error handling.
"""

import pytest

from tests.codon.base import (
    CodonCompilationResult,
    CodonCompilationTester,
    CodonErrorResult,
    CodonErrorTester,
    CodonPerformanceResult,
    CodonPerformanceTester,
    CodonTestBase,
)


class TestAlgorithms(CodonTestBase):
    """Unit tests for Algorithms component"""

    def setup_method(self):
        """Setup method called before each test"""
        super().setup_method()

        # Import the algorithms module
        try:
            from server.analytics.algorithms import GraphAlgorithms

            self.GraphAlgorithms = GraphAlgorithms
        except ImportError:
            pytest.skip("GraphAlgorithms not available")

        # Test graph data
        self.test_graph = {
            "nodes": [
                {"id": 1, "type": "user"},
                {"id": 2, "type": "user"},
                {"id": 3, "type": "post"},
                {"id": 4, "type": "post"},
            ],
            "edges": [
                {"source": 1, "target": 3, "type": "created"},
                {"source": 2, "target": 3, "type": "liked"},
                {"source": 1, "target": 4, "type": "created"},
                {"source": 2, "target": 4, "type": "liked"},
            ],
        }

    def test_compilation(self) -> CodonCompilationResult:
        """Test Codon compilation of Algorithms component"""

        test_code = """
from server.analytics.algorithms import GraphAlgorithms

def test_algorithms():
    algorithms = GraphAlgorithms()
    result = algorithms.initialize()
    return result

if __name__ == "__main__":
    test_algorithms()
"""

        tester = CodonCompilationTester()
        return tester.test_compilation(
            test_code, test_name="algorithms_compilation", optimization_level="release"
        )

    def test_performance(self) -> CodonPerformanceResult:
        """Test performance comparison between interpreted and compiled versions"""

        def interpreted_algorithm_operation():
            """Interpreted version of algorithm operation"""
            algorithms = self.GraphAlgorithms()
            algorithms.initialize()

            # Simulate algorithm processing
            result = algorithms.process_graph(self.test_graph)
            return result

        def compiled_algorithm_operation():
            """Compiled version of algorithm operation"""
            algorithms = self.GraphAlgorithms()
            algorithms.initialize()

            # Simulate compiled processing (faster)
            result = algorithms.process_graph(self.test_graph)
            return result

        tester = CodonPerformanceTester()
        return tester.benchmark_interpreted_vs_compiled(
            interpreted_algorithm_operation,
            compiled_algorithm_operation,
            test_name="algorithms_performance",
            iterations=100,
        )

    def test_error_handling(self) -> CodonErrorResult:
        """Test error handling in Algorithms component"""

        def error_operation():
            """Operation that should raise an error"""
            algorithms = self.GraphAlgorithms()
            # Try to process invalid graph data
            invalid_graph = {"invalid": "graph"}
            return algorithms.process_graph(invalid_graph)

        tester = CodonErrorTester()
        return tester.test_error_handling(
            error_operation,
            expected_error_type=ValueError,
            test_name="algorithms_error_handling",
        )

    def test_compilation_with_invalid_code(self):
        """Test compilation error handling"""

        invalid_code = """
from server.analytics.algorithms import GraphAlgorithms

def test_invalid_algorithms():
    algorithms = GraphAlgorithms()
    # Invalid syntax
    if True
        return algorithms
"""

        tester = CodonCompilationTester()
        result = tester.test_compilation_with_errors(
            invalid_code,
            expected_error_type="syntax",
            test_name="algorithms_invalid_compilation",
        )

        assert not result.success
        assert "syntax" in result.error_message.lower()

    def test_memory_usage(self):
        """Test memory usage of algorithm operations"""

        def interpreted_memory_test():
            """Memory test for interpreted version"""
            algorithms = self.GraphAlgorithms()
            algorithms.initialize()

            # Process large graph
            large_graph = self.test_graph.copy()
            for i in range(1000):
                large_graph["nodes"].append({"id": i + 100, "type": "node"})

            return algorithms.process_graph(large_graph)

        def compiled_memory_test():
            """Memory test for compiled version"""
            algorithms = self.GraphAlgorithms()
            algorithms.initialize()

            # Process large graph
            large_graph = self.test_graph.copy()
            for i in range(1000):
                large_graph["nodes"].append({"id": i + 100, "type": "node"})

            return algorithms.process_graph(large_graph)

        tester = CodonPerformanceTester()
        result = tester.test_memory_usage(
            interpreted_memory_test,
            compiled_memory_test,
            test_name="algorithms_memory_usage",
        )

        # Assert that compiled version uses less memory
        assert result.speedup_ratio > 1.0

    def test_concurrent_operations(self):
        """Test concurrent algorithm operations"""

        import queue
        import threading

        def worker(worker_id: int, result_queue: queue.Queue):
            """Worker function for concurrent testing"""
            try:
                algorithms = self.GraphAlgorithms()
                algorithms.initialize()

                # Process graph with worker-specific modifications
                graph = self.test_graph.copy()
                graph["worker_id"] = worker_id

                result = algorithms.process_graph(graph)
                result_queue.put((worker_id, result, None))
            except Exception as e:
                result_queue.put((worker_id, None, e))

        # Run concurrent operations
        num_workers = 5
        result_queue = queue.Queue()
        threads = []

        for i in range(num_workers):
            thread = threading.Thread(target=worker, args=(i, result_queue))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results
        results = []
        errors = []

        while not result_queue.empty():
            worker_id, result, error = result_queue.get()
            if error:
                errors.append((worker_id, error))
            else:
                results.append((worker_id, result))

        # Assert that all operations completed successfully
        assert len(results) == num_workers
        assert len(errors) == 0

    def test_compilation_optimization_levels(self):
        """Test compilation with different optimization levels"""

        test_code = """
from server.analytics.algorithms import GraphAlgorithms

def test_optimized_algorithms():
    algorithms = GraphAlgorithms()
    algorithms.initialize()
    return algorithms.process_graph({"test": "graph"})

if __name__ == "__main__":
    test_optimized_algorithms()
"""

        tester = CodonCompilationTester()

        # Test debug compilation
        debug_result = tester.test_compilation(
            test_code,
            test_name="algorithms_debug_compilation",
            optimization_level="debug",
        )

        # Test release compilation
        release_result = tester.test_compilation(
            test_code,
            test_name="algorithms_release_compilation",
            optimization_level="release",
        )

        # Assert both compilations succeeded
        assert debug_result.success
        assert release_result.success

        # Release compilation should be faster
        assert release_result.compilation_time <= debug_result.compilation_time

    def test_performance_regression_detection(self):
        """Test performance regression detection"""

        def baseline_operation():
            """Baseline operation for regression testing"""
            algorithms = self.GraphAlgorithms()
            algorithms.initialize()
            return algorithms.process_graph(self.test_graph)

        def current_operation():
            """Current operation for regression testing"""
            algorithms = self.GraphAlgorithms()
            algorithms.initialize()
            return algorithms.process_graph(self.test_graph)

        tester = CodonPerformanceTester()

        # Run baseline test
        baseline_result = tester.benchmark_interpreted_vs_compiled(
            baseline_operation,
            current_operation,
            test_name="algorithms_baseline",
            iterations=100,
        )

        # Run current test (should detect regression if performance degraded)
        current_result = tester.benchmark_interpreted_vs_compiled(
            baseline_operation,
            current_operation,
            test_name="algorithms_current",
            iterations=100,
        )

        # Assert that performance hasn't regressed significantly
        if current_result.regression_percentage:
            assert current_result.regression_percentage < 10.0  # 10% threshold


# Pytest test functions for direct execution
def test_algorithms_compilation(codon_compilation_tester):
    """Test algorithms compilation"""
    test_instance = TestAlgorithms()
    result = test_instance.test_compilation()
    assert result.success


def test_algorithms_performance(codon_performance_tester):
    """Test algorithms performance"""
    test_instance = TestAlgorithms()
    result = test_instance.test_performance()
    assert result.speedup_ratio > 1.0


def test_algorithms_error_handling(codon_error_tester):
    """Test algorithms error handling"""
    test_instance = TestAlgorithms()
    result = test_instance.test_error_handling()
    assert result.handled_correctly
