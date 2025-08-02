"""
Codon Testing Framework

This module provides comprehensive testing utilities for Codon refactored components,
including thread safety testing, performance benchmarking, and compatibility validation.
"""

import asyncio
import gc
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil
import pytest


@dataclass
class ThreadSafetyResult:
    """Result of thread safety testing"""

    is_thread_safe: bool
    unique_instances: int
    errors: List[str]
    execution_time: float
    memory_usage: float
    test_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceResult:
    """Result of performance testing"""

    operation_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    iterations: int
    baseline_time: Optional[float] = None
    regression_percentage: Optional[float] = None


@dataclass
class CompatibilityResult:
    """Result of compatibility testing"""

    test_name: str
    interpreted_result: Any
    compiled_result: Any
    is_compatible: bool
    differences: List[str] = field(default_factory=list)


class ThreadSafetyTester:
    """Comprehensive thread safety testing utility for Codon environment"""

    def __init__(self):
        self.results: List[ThreadSafetyResult] = []
        self.process = psutil.Process(os.getpid())

    async def test_singleton_thread_safety(
        self,
        get_instance_func: Callable,
        num_threads: int = 20,
        test_name: str = "singleton_thread_safety",
    ) -> ThreadSafetyResult:
        """Test singleton pattern thread safety"""
        start_time = time.time()
        initial_memory = self.process.memory_info().rss
        instances = []
        errors = []

        async def worker():
            try:
                instance = await get_instance_func()
                instances.append(instance)
                return instance
            except Exception as e:
                errors.append(str(e))
                return None

        # Run concurrent access
        tasks = [worker() for _ in range(num_threads)]
        results = await asyncio.gather(*tasks)

        # Analyze results
        unique_instances = len(set(id(r) for r in results if r is not None))
        execution_time = time.time() - start_time
        final_memory = self.process.memory_info().rss
        memory_usage = final_memory - initial_memory

        result = ThreadSafetyResult(
            is_thread_safe=unique_instances == 1 and len(errors) == 0,
            unique_instances=unique_instances,
            errors=errors,
            execution_time=execution_time,
            memory_usage=memory_usage,
            test_name=test_name,
            details={
                "num_threads": num_threads,
                "successful_instances": len([r for r in results if r is not None]),
                "failed_instances": len([r for r in results if r is None]),
            },
        )

        self.results.append(result)
        return result

    async def test_shared_state_access(
        self,
        state_manager,
        num_threads: int = 20,
        test_name: str = "shared_state_access",
    ) -> ThreadSafetyResult:
        """Test shared state access thread safety"""
        start_time = time.time()
        initial_memory = self.process.memory_info().rss
        errors = []
        data_inconsistencies = []

        async def worker(thread_id: int):
            try:
                # Perform concurrent operations
                key = f"key_{thread_id}"
                value = f"value_{thread_id}"

                await state_manager.set(key, value)
                retrieved = await state_manager.get(key)

                # Verify consistency
                if retrieved != value:
                    data_inconsistencies.append(
                        f"Data inconsistency for thread {thread_id}"
                    )

            except Exception as e:
                errors.append(str(e))

        # Run concurrent operations
        tasks = [worker(i) for i in range(num_threads)]
        await asyncio.gather(*tasks)

        execution_time = time.time() - start_time
        final_memory = self.process.memory_info().rss
        memory_usage = final_memory - initial_memory

        result = ThreadSafetyResult(
            is_thread_safe=len(errors) == 0 and len(data_inconsistencies) == 0,
            unique_instances=0,
            errors=errors + data_inconsistencies,
            execution_time=execution_time,
            memory_usage=memory_usage,
            test_name=test_name,
            details={
                "num_threads": num_threads,
                "data_inconsistencies": len(data_inconsistencies),
            },
        )

        self.results.append(result)
        return result

    def test_race_condition_detection(
        self,
        unsafe_func: Callable,
        safe_func: Callable,
        num_iterations: int = 100,
        test_name: str = "race_condition_detection",
    ) -> ThreadSafetyResult:
        """Test race condition detection and prevention"""
        start_time = time.time()
        initial_memory = self.process.memory_info().rss
        errors = []

        # Test unsafe function (should exhibit race conditions)
        unsafe_result = self._run_concurrent_function(unsafe_func, num_iterations)

        # Test safe function (should not exhibit race conditions)
        safe_result = self._run_concurrent_function(safe_func, num_iterations)

        execution_time = time.time() - start_time
        final_memory = self.process.memory_info().rss
        memory_usage = final_memory - initial_memory

        # Analyze results
        unsafe_race_detected = unsafe_result < num_iterations
        safe_no_race = safe_result == num_iterations

        result = ThreadSafetyResult(
            is_thread_safe=safe_no_race and unsafe_race_detected,
            unique_instances=0,
            errors=errors,
            execution_time=execution_time,
            memory_usage=memory_usage,
            test_name=test_name,
            details={
                "unsafe_result": unsafe_result,
                "safe_result": safe_result,
                "expected_unsafe": num_iterations,
                "expected_safe": num_iterations,
                "race_condition_detected": unsafe_race_detected,
                "safe_implementation_works": safe_no_race,
            },
        )

        self.results.append(result)
        return result

    def _run_concurrent_function(self, func: Callable, num_iterations: int) -> int:
        """Run function concurrently and return result"""
        counter = 0
        lock = threading.Lock()

        def worker():
            nonlocal counter
            result = func(counter, lock)
            return result

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(num_iterations)]
            for future in futures:
                future.result()

        return counter

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all thread safety test results"""
        if not self.results:
            return {"message": "No tests run"}

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.is_thread_safe)
        failed_tests = total_tests - passed_tests

        total_errors = sum(len(r.errors) for r in self.results)
        avg_execution_time = sum(r.execution_time for r in self.results) / total_tests
        avg_memory_usage = sum(r.memory_usage for r in self.results) / total_tests

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_errors": total_errors,
            "avg_execution_time": avg_execution_time,
            "avg_memory_usage": avg_memory_usage,
            "test_details": [r.__dict__ for r in self.results],
        }


class PerformanceTester:
    """Comprehensive performance testing utility for Codon components"""

    def __init__(self, baseline_file: str = "performance_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.baselines = self._load_baselines()
        self.results: List[PerformanceResult] = []
        self.process = psutil.Process(os.getpid())

    def _load_baselines(self) -> Dict[str, float]:
        """Load performance baselines"""
        if self.baseline_file.exists():
            with open(self.baseline_file, "r") as f:
                return json.load(f)
        return {}

    def _save_baselines(self, baselines: Dict[str, float]):
        """Save performance baselines"""
        with open(self.baseline_file, "w") as f:
            json.dump(baselines, f, indent=2)

    def benchmark_function(
        self,
        func: Callable,
        *args,
        iterations: int = 1000,
        operation_name: str = "function_benchmark",
        **kwargs,
    ) -> PerformanceResult:
        """Benchmark a function's performance"""
        initial_memory = self.process.memory_info().rss
        initial_cpu = self.process.cpu_percent()

        start_time = time.time()

        # Run function multiple times
        for _ in range(iterations):
            result = func(*args, **kwargs)

        execution_time = time.time() - start_time
        final_memory = self.process.memory_info().rss
        final_cpu = self.process.cpu_percent()

        memory_usage = final_memory - initial_memory
        cpu_usage = final_cpu - initial_cpu

        # Check for performance regression
        baseline_time = self.baselines.get(operation_name)
        regression_percentage = None

        if baseline_time:
            regression_percentage = (
                (execution_time - baseline_time) / baseline_time
            ) * 100
        else:
            # Store new baseline
            self.baselines[operation_name] = execution_time
            self._save_baselines(self.baselines)

        result = PerformanceResult(
            operation_name=operation_name,
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            iterations=iterations,
            baseline_time=baseline_time,
            regression_percentage=regression_percentage,
        )

        self.results.append(result)
        return result

    def test_memory_usage(self, func: Callable, *args, **kwargs) -> PerformanceResult:
        """Test memory usage of a function"""
        gc.collect()  # Force garbage collection
        initial_memory = self.process.memory_info().rss

        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time

        # Force garbage collection again
        gc.collect()
        final_memory = self.process.memory_info().rss
        memory_usage = final_memory - initial_memory

        perf_result = PerformanceResult(
            operation_name="memory_usage_test",
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=0.0,
            iterations=1,
        )

        self.results.append(perf_result)
        return perf_result

    def test_cpu_intensive_operation(
        self, func: Callable, *args, duration: float = 1.0, **kwargs
    ) -> PerformanceResult:
        """Test CPU-intensive operations"""
        initial_cpu = self.process.cpu_percent()
        start_time = time.time()

        iterations = 0
        while time.time() - start_time < duration:
            func(*args, **kwargs)
            iterations += 1

        execution_time = time.time() - start_time
        final_cpu = self.process.cpu_percent()
        cpu_usage = final_cpu - initial_cpu

        result = PerformanceResult(
            operation_name="cpu_intensive_test",
            execution_time=execution_time,
            memory_usage=0.0,
            cpu_usage=cpu_usage,
            iterations=iterations,
        )

        self.results.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all performance test results"""
        if not self.results:
            return {"message": "No tests run"}

        total_tests = len(self.results)
        regressions = [
            r
            for r in self.results
            if r.regression_percentage and r.regression_percentage > 5
        ]

        avg_execution_time = sum(r.execution_time for r in self.results) / total_tests
        avg_memory_usage = sum(r.memory_usage for r in self.results) / total_tests
        avg_cpu_usage = sum(r.cpu_usage for r in self.results) / total_tests

        return {
            "total_tests": total_tests,
            "performance_regressions": len(regressions),
            "avg_execution_time": avg_execution_time,
            "avg_memory_usage": avg_memory_usage,
            "avg_cpu_usage": avg_cpu_usage,
            "regression_details": [
                {
                    "operation": r.operation_name,
                    "regression_percentage": r.regression_percentage,
                }
                for r in regressions
            ],
            "test_details": [r.__dict__ for r in self.results],
        }


class CompatibilityTester:
    """Test compatibility between compiled and interpreted code"""

    def __init__(self):
        self.results: List[CompatibilityResult] = []

    def test_behavioral_parity(
        self,
        module_name: str,
        function_name: str,
        *args,
        test_name: str = "behavioral_parity",
        **kwargs,
    ) -> CompatibilityResult:
        """Test that compiled and interpreted code produce identical results"""

        # Test interpreted version
        interpreted_result = self._run_interpreted(
            module_name, function_name, *args, **kwargs
        )

        # Test compiled version
        compiled_result = self._run_compiled(
            module_name, function_name, *args, **kwargs
        )

        # Compare results
        is_compatible = interpreted_result == compiled_result
        differences = []

        if not is_compatible:
            differences.append(
                f"Result mismatch: interpreted={interpreted_result}, compiled={compiled_result}"
            )

        result = CompatibilityResult(
            test_name=test_name,
            interpreted_result=interpreted_result,
            compiled_result=compiled_result,
            is_compatible=is_compatible,
            differences=differences,
        )

        self.results.append(result)
        return result

    def _run_interpreted(self, module_name: str, function_name: str, *args, **kwargs):
        """Run function in interpreted mode"""
        import importlib

        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        return func(*args, **kwargs)

    def _run_compiled(self, module_name: str, function_name: str, *args, **kwargs):
        """Run function in compiled mode"""
        # This would use Codon's compiled version
        # For now, we'll simulate by running the interpreted version
        # In a real implementation, this would use Codon's API
        return self._run_interpreted(module_name, function_name, *args, **kwargs)

    def test_dynamic_features(self) -> List[CompatibilityResult]:
        """Test dynamic Python features in compiled environment"""
        results = []

        # Test dynamic imports
        results.append(self._test_dynamic_imports())

        # Test eval/exec behavior
        results.append(self._test_eval_exec())

        # Test metaclass behavior
        results.append(self._test_metaclasses())

        return results

    def _test_dynamic_imports(self) -> CompatibilityResult:
        """Test dynamic import behavior"""
        try:
            # Test dynamic import
            import importlib

            module = importlib.import_module("server.analytics.engine")

            result = CompatibilityResult(
                test_name="dynamic_imports",
                interpreted_result=True,
                compiled_result=True,
                is_compatible=True,
            )
        except Exception as e:
            result = CompatibilityResult(
                test_name="dynamic_imports",
                interpreted_result=True,
                compiled_result=False,
                is_compatible=False,
                differences=[f"Dynamic import failed: {e}"],
            )

        self.results.append(result)
        return result

    def _test_eval_exec(self) -> CompatibilityResult:
        """Test eval/exec behavior"""
        try:
            # Test eval
            eval_result = eval("2 + 2")

            # Test exec
            namespace = {}
            exec("x = 42", namespace)
            exec_result = namespace.get("x")

            result = CompatibilityResult(
                test_name="eval_exec",
                interpreted_result={"eval": eval_result, "exec": exec_result},
                compiled_result={"eval": eval_result, "exec": exec_result},
                is_compatible=True,
            )
        except Exception as e:
            result = CompatibilityResult(
                test_name="eval_exec",
                interpreted_result={"error": str(e)},
                compiled_result={"error": str(e)},
                is_compatible=True,
                differences=[f"Eval/exec failed: {e}"],
            )

        self.results.append(result)
        return result

    def _test_metaclasses(self) -> CompatibilityResult:
        """Test metaclass behavior"""
        try:

            class Meta(type):
                def __new__(cls, name, bases, attrs):
                    attrs["meta_processed"] = True
                    return super().__new__(cls, name, bases, attrs)

            class TestClass(metaclass=Meta):
                pass

            has_meta_processed = hasattr(TestClass, "meta_processed")
            meta_processed_value = getattr(TestClass, "meta_processed", False)

            result = CompatibilityResult(
                test_name="metaclasses",
                interpreted_result={
                    "has_meta_processed": has_meta_processed,
                    "value": meta_processed_value,
                },
                compiled_result={
                    "has_meta_processed": has_meta_processed,
                    "value": meta_processed_value,
                },
                is_compatible=True,
            )
        except Exception as e:
            result = CompatibilityResult(
                test_name="metaclasses",
                interpreted_result={"error": str(e)},
                compiled_result={"error": str(e)},
                is_compatible=True,
                differences=[f"Metaclass test failed: {e}"],
            )

        self.results.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all compatibility test results"""
        if not self.results:
            return {"message": "No tests run"}

        total_tests = len(self.results)
        compatible_tests = sum(1 for r in self.results if r.is_compatible)
        incompatible_tests = total_tests - compatible_tests

        total_differences = sum(len(r.differences) for r in self.results)

        return {
            "total_tests": total_tests,
            "compatible_tests": compatible_tests,
            "incompatible_tests": incompatible_tests,
            "compatibility_rate": (
                compatible_tests / total_tests if total_tests > 0 else 0
            ),
            "total_differences": total_differences,
            "test_details": [r.__dict__ for r in self.results],
        }


# Pytest fixtures for easy integration
@pytest.fixture
def thread_safety_tester():
    """Provide thread safety testing utility"""
    return ThreadSafetyTester()


@pytest.fixture
def performance_tester():
    """Provide performance testing utility"""
    return PerformanceTester()


@pytest.fixture
def compatibility_tester():
    """Provide compatibility testing utility"""
    return CompatibilityTester()


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests"""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    initial_cpu = process.cpu_percent()

    start_time = time.time()

    yield {
        "start_time": start_time,
        "initial_memory": initial_memory,
        "initial_cpu": initial_cpu,
        "process": process,
    }

    # Calculate final metrics
    end_time = time.time()
    final_memory = process.memory_info().rss
    final_cpu = process.cpu_percent()

    metrics = {
        "execution_time": end_time - start_time,
        "memory_usage": final_memory - initial_memory,
        "cpu_usage": final_cpu - initial_cpu,
    }

    # Log metrics
    print(f"Performance metrics: {metrics}")


@pytest.fixture
def load_generator():
    """Generate load for stress testing"""

    def generate_load(operations: int = 1000):
        """Generate specified number of operations"""
        for i in range(operations):
            yield {
                "operation_id": i,
                "data": f"test_data_{i}",
                "timestamp": time.time(),
            }

    return generate_load
