"""
Unit tests for Cache component using Codon framework

This module provides comprehensive unit tests for the cache component,
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


class TestCache(CodonTestBase):
    """Unit tests for Cache component"""

    def setup_method(self):
        """Setup method called before each test"""
        super().setup_method()

        # Import the cache module
        try:
            from server.analytics.cache import CacheManager

            self.CacheManager = CacheManager
        except ImportError:
            pytest.skip("CacheManager not available")

        # Test cache data
        self.test_cache_data = {
            "key1": "value1",
            "key2": "value2",
            "key3": {"nested": "data"},
        }

    def test_compilation(self) -> CodonCompilationResult:
        """Test Codon compilation of Cache component"""

        test_code = """
from server.analytics.cache import CacheManager

def test_cache():
    cache = CacheManager()
    result = cache.initialize()
    return result

if __name__ == "__main__":
    test_cache()
"""

        tester = CodonCompilationTester()
        return tester.test_compilation(
            test_code, test_name="cache_compilation", optimization_level="release"
        )

    def test_performance(self) -> CodonPerformanceResult:
        """Test performance comparison between interpreted and compiled versions"""

        def interpreted_cache_operation():
            """Interpreted version of cache operation"""
            cache = self.CacheManager()
            cache.initialize()

            # Simulate cache operations
            for key, value in self.test_cache_data.items():
                cache.set(key, value)

            result = cache.get("key1")
            return result

        def compiled_cache_operation():
            """Compiled version of cache operation"""
            cache = self.CacheManager()
            cache.initialize()

            # Simulate compiled cache operations (faster)
            for key, value in self.test_cache_data.items():
                cache.set(key, value)

            result = cache.get("key1")
            return result

        tester = CodonPerformanceTester()
        return tester.benchmark_interpreted_vs_compiled(
            interpreted_cache_operation,
            compiled_cache_operation,
            test_name="cache_performance",
            iterations=100,
        )

    def test_error_handling(self) -> CodonErrorResult:
        """Test error handling in Cache component"""

        def error_operation():
            """Operation that should raise an error"""
            cache = self.CacheManager()
            # Try to access non-existent key
            return cache.get("non_existent_key")

        tester = CodonErrorTester()
        return tester.test_error_handling(
            error_operation,
            expected_error_type=KeyError,
            test_name="cache_error_handling",
        )

    def test_compilation_with_invalid_code(self):
        """Test compilation error handling"""

        invalid_code = """
from server.analytics.cache import CacheManager

def test_invalid_cache():
    cache = CacheManager()
    # Invalid syntax
    if True
        return cache
"""

        tester = CodonCompilationTester()
        result = tester.test_compilation_with_errors(
            invalid_code,
            expected_error_type="syntax",
            test_name="cache_invalid_compilation",
        )

        assert not result.success
        assert "syntax" in result.error_message.lower()

    def test_memory_usage(self):
        """Test memory usage of cache operations"""

        def interpreted_memory_test():
            """Memory test for interpreted version"""
            cache = self.CacheManager()
            cache.initialize()

            # Store large amount of data
            for i in range(1000):
                cache.set(f"key_{i}", f"value_{i}" * 100)

            return cache.get("key_500")

        def compiled_memory_test():
            """Memory test for compiled version"""
            cache = self.CacheManager()
            cache.initialize()

            # Store large amount of data
            for i in range(1000):
                cache.set(f"key_{i}", f"value_{i}" * 100)

            return cache.get("key_500")

        tester = CodonPerformanceTester()
        result = tester.test_memory_usage(
            interpreted_memory_test,
            compiled_memory_test,
            test_name="cache_memory_usage",
        )

        # Assert that compiled version uses less memory
        assert result.speedup_ratio > 1.0

    def test_concurrent_operations(self):
        """Test concurrent cache operations"""

        import queue
        import threading

        def worker(worker_id: int, result_queue: queue.Queue):
            """Worker function for concurrent testing"""
            try:
                cache = self.CacheManager()
                cache.initialize()

                # Perform cache operations
                cache.set(f"worker_{worker_id}", f"data_{worker_id}")
                result = cache.get(f"worker_{worker_id}")

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
from server.analytics.cache import CacheManager

def test_optimized_cache():
    cache = CacheManager()
    cache.initialize()
    cache.set("test", "data")
    return cache.get("test")

if __name__ == "__main__":
    test_optimized_cache()
"""

        tester = CodonCompilationTester()

        # Test debug compilation
        debug_result = tester.test_compilation(
            test_code, test_name="cache_debug_compilation", optimization_level="debug"
        )

        # Test release compilation
        release_result = tester.test_compilation(
            test_code,
            test_name="cache_release_compilation",
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
            cache = self.CacheManager()
            cache.initialize()
            cache.set("test", "data")
            return cache.get("test")

        def current_operation():
            """Current operation for regression testing"""
            cache = self.CacheManager()
            cache.initialize()
            cache.set("test", "data")
            return cache.get("test")

        tester = CodonPerformanceTester()

        # Run baseline test
        baseline_result = tester.benchmark_interpreted_vs_compiled(
            baseline_operation,
            current_operation,
            test_name="cache_baseline",
            iterations=100,
        )

        # Run current test (should detect regression if performance degraded)
        current_result = tester.benchmark_interpreted_vs_compiled(
            baseline_operation,
            current_operation,
            test_name="cache_current",
            iterations=100,
        )

        # Assert that performance hasn't regressed significantly
        if current_result.regression_percentage:
            assert current_result.regression_percentage < 10.0  # 10% threshold


# Pytest test functions for direct execution
def test_cache_compilation(codon_compilation_tester):
    """Test cache compilation"""
    test_instance = TestCache()
    result = test_instance.test_compilation()
    assert result.success


def test_cache_performance(codon_performance_tester):
    """Test cache performance"""
    test_instance = TestCache()
    result = test_instance.test_performance()
    assert result.speedup_ratio > 1.0


def test_cache_error_handling(codon_error_tester):
    """Test cache error handling"""
    test_instance = TestCache()
    result = test_instance.test_error_handling()
    assert result.handled_correctly
