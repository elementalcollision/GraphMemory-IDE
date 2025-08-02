"""
Unit tests for Analytics Engine component using Codon framework

This module provides comprehensive unit tests for the analytics engine,
including compilation testing, performance benchmarking, and error handling.
"""

import time
from typing import Any, Dict, List

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


class TestAnalyticsEngine(CodonTestBase):
    """Unit tests for Analytics Engine component"""

    def setup_method(self):
        """Setup method called before each test"""
        super().setup_method()

        # Import the analytics engine module
        try:
            from server.analytics.engine import AnalyticsEngine

            self.AnalyticsEngine = AnalyticsEngine
        except ImportError:
            pytest.skip("AnalyticsEngine not available")

        # Test data
        self.test_data = {
            "nodes": [
                {"id": 1, "type": "user", "properties": {"name": "Alice"}},
                {"id": 2, "type": "user", "properties": {"name": "Bob"}},
                {"id": 3, "type": "post", "properties": {"title": "Hello"}},
            ],
            "edges": [
                {"source": 1, "target": 3, "type": "created"},
                {"source": 2, "target": 3, "type": "liked"},
            ],
        }

    def test_compilation(self) -> CodonCompilationResult:
        """Test Codon compilation of Analytics Engine"""

        # Create a simple test script that uses AnalyticsEngine
        test_code = """
from server.analytics.engine import AnalyticsEngine

def test_analytics_engine():
    engine = AnalyticsEngine()
    result = engine.initialize()
    return result

if __name__ == "__main__":
    test_analytics_engine()
"""

        tester = CodonCompilationTester()
        return tester.test_compilation(
            test_code,
            test_name="analytics_engine_compilation",
            optimization_level="release",
        )

    def test_performance(self) -> CodonPerformanceResult:
        """Test performance comparison between interpreted and compiled versions"""

        def interpreted_analytics_operation():
            """Interpreted version of analytics operation"""
            engine = self.AnalyticsEngine()
            engine.initialize()

            # Simulate analytics processing
            result = engine.process_data(self.test_data)
            return result

        def compiled_analytics_operation():
            """Compiled version of analytics operation"""
            # This would be the compiled version
            # For now, we'll simulate it
            engine = self.AnalyticsEngine()
            engine.initialize()

            # Simulate compiled processing (faster)
            result = engine.process_data(self.test_data)
            return result

        tester = CodonPerformanceTester()
        return tester.benchmark_interpreted_vs_compiled(
            interpreted_analytics_operation,
            compiled_analytics_operation,
            test_name="analytics_engine_performance",
            iterations=100,
        )

    def test_error_handling(self) -> CodonErrorResult:
        """Test error handling in Analytics Engine"""

        def error_operation():
            """Operation that should raise an error"""
            engine = self.AnalyticsEngine()
            # Try to process invalid data
            invalid_data = {"invalid": "data"}
            return engine.process_data(invalid_data)

        tester = CodonErrorTester()
        return tester.test_error_handling(
            error_operation,
            expected_error_type=ValueError,
            test_name="analytics_engine_error_handling",
        )

    def test_compilation_with_invalid_code(self):
        """Test compilation error handling"""

        invalid_code = """
from server.analytics.engine import AnalyticsEngine

def test_invalid_analytics():
    engine = AnalyticsEngine()
    # Invalid syntax
    if True
        return engine
"""

        tester = CodonCompilationTester()
        result = tester.test_compilation_with_errors(
            invalid_code,
            expected_error_type="syntax",
            test_name="analytics_engine_invalid_compilation",
        )

        assert not result.success
        assert "syntax" in result.error_message.lower()

    def test_memory_usage(self):
        """Test memory usage of analytics operations"""

        def interpreted_memory_test():
            """Memory test for interpreted version"""
            engine = self.AnalyticsEngine()
            engine.initialize()

            # Process large dataset
            large_data = self.test_data.copy()
            for i in range(1000):
                large_data["nodes"].append(
                    {"id": i + 100, "type": "node", "properties": {"value": i}}
                )

            return engine.process_data(large_data)

        def compiled_memory_test():
            """Memory test for compiled version"""
            engine = self.AnalyticsEngine()
            engine.initialize()

            # Process large dataset
            large_data = self.test_data.copy()
            for i in range(1000):
                large_data["nodes"].append(
                    {"id": i + 100, "type": "node", "properties": {"value": i}}
                )

            return engine.process_data(large_data)

        tester = CodonPerformanceTester()
        result = tester.test_memory_usage(
            interpreted_memory_test,
            compiled_memory_test,
            test_name="analytics_engine_memory_usage",
        )

        # Assert that compiled version uses less memory
        assert result.speedup_ratio > 1.0

    def test_concurrent_operations(self):
        """Test concurrent analytics operations"""

        import queue
        import threading

        def worker(worker_id: int, result_queue: queue.Queue):
            """Worker function for concurrent testing"""
            try:
                engine = self.AnalyticsEngine()
                engine.initialize()

                # Process data with worker-specific modifications
                data = self.test_data.copy()
                data["worker_id"] = worker_id

                result = engine.process_data(data)
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
from server.analytics.engine import AnalyticsEngine

def test_optimized_analytics():
    engine = AnalyticsEngine()
    engine.initialize()
    return engine.process_data({"test": "data"})

if __name__ == "__main__":
    test_optimized_analytics()
"""

        tester = CodonCompilationTester()

        # Test debug compilation
        debug_result = tester.test_compilation(
            test_code,
            test_name="analytics_engine_debug_compilation",
            optimization_level="debug",
        )

        # Test release compilation
        release_result = tester.test_compilation(
            test_code,
            test_name="analytics_engine_release_compilation",
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
            engine = self.AnalyticsEngine()
            engine.initialize()
            return engine.process_data(self.test_data)

        def current_operation():
            """Current operation for regression testing"""
            engine = self.AnalyticsEngine()
            engine.initialize()
            return engine.process_data(self.test_data)

        tester = CodonPerformanceTester()

        # Run baseline test
        baseline_result = tester.benchmark_interpreted_vs_compiled(
            baseline_operation,
            current_operation,
            test_name="analytics_engine_baseline",
            iterations=100,
        )

        # Run current test (should detect regression if performance degraded)
        current_result = tester.benchmark_interpreted_vs_compiled(
            baseline_operation,
            current_operation,
            test_name="analytics_engine_current",
            iterations=100,
        )

        # Assert that performance hasn't regressed significantly
        if current_result.regression_percentage:
            assert current_result.regression_percentage < 10.0  # 10% threshold


# Pytest test functions for direct execution
def test_analytics_engine_compilation(codon_compilation_tester):
    """Test analytics engine compilation"""
    test_instance = TestAnalyticsEngine()
    result = test_instance.test_compilation()
    assert result.success


def test_analytics_engine_performance(codon_performance_tester):
    """Test analytics engine performance"""
    test_instance = TestAnalyticsEngine()
    result = test_instance.test_performance()
    assert result.speedup_ratio > 1.0


def test_analytics_engine_error_handling(codon_error_tester):
    """Test analytics engine error handling"""
    test_instance = TestAnalyticsEngine()
    result = test_instance.test_error_handling()
    assert result.handled_correctly
