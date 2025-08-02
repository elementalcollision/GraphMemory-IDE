"""
Codon Unit Testing Base Classes

This module provides comprehensive base classes and utilities for unit testing
Codon components, including compilation testing, performance monitoring, and
error handling.
"""

import gc
import json
import os
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil
import pytest


@dataclass
class CodonCompilationResult:
    """Result of Codon compilation test"""

    success: bool
    compilation_time: float
    executable_size: Optional[int] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    optimization_level: str = "default"
    target_platform: str = "native"


@dataclass
class CodonPerformanceResult:
    """Result of Codon performance test"""

    test_name: str
    interpreted_time: float
    compiled_time: float
    speedup_ratio: float
    memory_usage: float
    cpu_usage: float
    iterations: int
    baseline_time: Optional[float] = None
    regression_percentage: Optional[float] = None


@dataclass
class CodonErrorResult:
    """Result of Codon error handling test"""

    test_name: str
    error_type: str
    error_message: str
    handled_correctly: bool
    recovery_successful: bool
    execution_time: float


class CodonTestBase(ABC):
    """Base class for Codon unit tests"""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.temp_dir = None
        self.compilation_results: List[CodonCompilationResult] = []
        self.performance_results: List[CodonPerformanceResult] = []
        self.error_results: List[CodonErrorResult] = []

    def setup_method(self):
        """Setup method called before each test"""
        self.temp_dir = tempfile.mkdtemp(prefix="codon_test_")
        gc.collect()  # Force garbage collection

    def teardown_method(self):
        """Teardown method called after each test"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)
        gc.collect()  # Force garbage collection

    @abstractmethod
    def test_compilation(self) -> CodonCompilationResult:
        """Test Codon compilation of the component"""
        pass

    @abstractmethod
    def test_performance(self) -> CodonPerformanceResult:
        """Test performance comparison between interpreted and compiled versions"""
        pass

    @abstractmethod
    def test_error_handling(self) -> CodonErrorResult:
        """Test error handling in compiled version"""
        pass


class CodonCompilationTester:
    """Utility class for testing Codon compilation"""

    def __init__(self, codon_path: Optional[str] = None):
        self.codon_path = codon_path or self._find_codon_path()
        self.results: List[CodonCompilationResult] = []

    def _find_codon_path(self) -> str:
        """Find Codon executable path"""
        # Check common installation paths
        possible_paths = [
            "codon",
            "/usr/local/bin/codon",
            "/opt/homebrew/bin/codon",
            os.path.expanduser("~/.local/bin/codon"),
        ]

        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        raise RuntimeError("Codon executable not found. Please install Codon first.")

    def test_compilation(
        self,
        source_code: str,
        test_name: str = "compilation_test",
        optimization_level: str = "default",
        target_platform: str = "native",
    ) -> CodonCompilationResult:
        """Test compilation of source code with Codon"""

        start_time = time.time()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            # Build command
            cmd = [self.codon_path, "build"]

            if optimization_level == "release":
                cmd.append("-release")
            elif optimization_level == "debug":
                cmd.append("-debug")

            if target_platform != "native":
                cmd.extend(["-target", target_platform])

            cmd.append(temp_file)

            # Run compilation
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60  # 60 second timeout
            )

            compilation_time = time.time() - start_time

            # Check if compilation was successful
            if result.returncode == 0:
                # Get executable size
                executable_path = temp_file.replace(".py", "")
                executable_size = (
                    os.path.getsize(executable_path)
                    if os.path.exists(executable_path)
                    else None
                )

                # Parse warnings
                warnings = []
                for line in result.stderr.split("\n"):
                    if "warning" in line.lower():
                        warnings.append(line.strip())

                compilation_result = CodonCompilationResult(
                    success=True,
                    compilation_time=compilation_time,
                    executable_size=executable_size,
                    warnings=warnings,
                    optimization_level=optimization_level,
                    target_platform=target_platform,
                )
            else:
                compilation_result = CodonCompilationResult(
                    success=False,
                    compilation_time=compilation_time,
                    error_message=result.stderr,
                    optimization_level=optimization_level,
                    target_platform=target_platform,
                )

            self.results.append(compilation_result)
            return compilation_result

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)

            # Clean up executable
            executable_path = temp_file.replace(".py", "")
            if os.path.exists(executable_path):
                os.unlink(executable_path)

    def test_compilation_with_errors(
        self,
        invalid_code: str,
        expected_error_type: str = "syntax",
        test_name: str = "compilation_error_test",
    ) -> CodonCompilationResult:
        """Test that invalid code fails compilation with expected error"""

        result = self.test_compilation(invalid_code, test_name)

        # Verify that compilation failed as expected
        if result.success:
            raise AssertionError(f"Expected compilation to fail, but it succeeded")

        if (
            expected_error_type == "syntax"
            and "syntax" not in result.error_message.lower()
        ):
            raise AssertionError(f"Expected syntax error, got: {result.error_message}")

        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all compilation test results"""
        if not self.results:
            return {"message": "No compilation tests run"}

        total_tests = len(self.results)
        successful_compilations = sum(1 for r in self.results if r.success)
        failed_compilations = total_tests - successful_compilations

        avg_compilation_time = (
            sum(r.compilation_time for r in self.results) / total_tests
        )

        return {
            "total_tests": total_tests,
            "successful_compilations": successful_compilations,
            "failed_compilations": failed_compilations,
            "success_rate": (
                successful_compilations / total_tests if total_tests > 0 else 0
            ),
            "avg_compilation_time": avg_compilation_time,
            "test_details": [r.__dict__ for r in self.results],
        }


class CodonPerformanceTester:
    """Utility class for testing Codon performance"""

    def __init__(self, baseline_file: str = "codon_performance_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.baselines = self._load_baselines()
        self.results: List[CodonPerformanceResult] = []
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

    def benchmark_interpreted_vs_compiled(
        self,
        interpreted_func: Callable,
        compiled_func: Callable,
        *args,
        iterations: int = 1000,
        test_name: str = "performance_benchmark",
        **kwargs,
    ) -> CodonPerformanceResult:
        """Benchmark interpreted vs compiled function performance"""

        # Benchmark interpreted version
        initial_memory = self.process.memory_info().rss
        initial_cpu = self.process.cpu_percent()

        start_time = time.time()
        for _ in range(iterations):
            interpreted_func(*args, **kwargs)
        interpreted_time = time.time() - start_time

        # Benchmark compiled version
        start_time = time.time()
        for _ in range(iterations):
            compiled_func(*args, **kwargs)
        compiled_time = time.time() - start_time

        # Calculate metrics
        speedup_ratio = interpreted_time / compiled_time if compiled_time > 0 else 0
        final_memory = self.process.memory_info().rss
        final_cpu = self.process.cpu_percent()

        memory_usage = final_memory - initial_memory
        cpu_usage = final_cpu - initial_cpu

        # Check for performance regression
        baseline_time = self.baselines.get(test_name)
        regression_percentage = None

        if baseline_time:
            regression_percentage = (
                (compiled_time - baseline_time) / baseline_time
            ) * 100
        else:
            # Store new baseline
            self.baselines[test_name] = compiled_time
            self._save_baselines(self.baselines)

        result = CodonPerformanceResult(
            test_name=test_name,
            interpreted_time=interpreted_time,
            compiled_time=compiled_time,
            speedup_ratio=speedup_ratio,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            iterations=iterations,
            baseline_time=baseline_time,
            regression_percentage=regression_percentage,
        )

        self.results.append(result)
        return result

    def test_memory_usage(
        self,
        interpreted_func: Callable,
        compiled_func: Callable,
        *args,
        test_name: str = "memory_usage_test",
        **kwargs,
    ) -> CodonPerformanceResult:
        """Test memory usage comparison"""

        gc.collect()  # Force garbage collection
        initial_memory = self.process.memory_info().rss

        # Test interpreted version
        start_time = time.time()
        interpreted_func(*args, **kwargs)
        interpreted_time = time.time() - start_time

        gc.collect()
        interpreted_memory = self.process.memory_info().rss

        # Test compiled version
        start_time = time.time()
        compiled_func(*args, **kwargs)
        compiled_time = time.time() - start_time

        gc.collect()
        compiled_memory = self.process.memory_info().rss

        memory_usage = compiled_memory - initial_memory
        speedup_ratio = interpreted_time / compiled_time if compiled_time > 0 else 0

        result = CodonPerformanceResult(
            test_name=test_name,
            interpreted_time=interpreted_time,
            compiled_time=compiled_time,
            speedup_ratio=speedup_ratio,
            memory_usage=memory_usage,
            cpu_usage=0.0,
            iterations=1,
        )

        self.results.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all performance test results"""
        if not self.results:
            return {"message": "No performance tests run"}

        total_tests = len(self.results)
        regressions = [
            r
            for r in self.results
            if r.regression_percentage and r.regression_percentage > 5
        ]

        avg_speedup = sum(r.speedup_ratio for r in self.results) / total_tests
        avg_memory_usage = sum(r.memory_usage for r in self.results) / total_tests
        avg_cpu_usage = sum(r.cpu_usage for r in self.results) / total_tests

        return {
            "total_tests": total_tests,
            "performance_regressions": len(regressions),
            "avg_speedup_ratio": avg_speedup,
            "avg_memory_usage": avg_memory_usage,
            "avg_cpu_usage": avg_cpu_usage,
            "regression_details": [
                {
                    "test_name": r.test_name,
                    "regression_percentage": r.regression_percentage,
                }
                for r in regressions
            ],
            "test_details": [r.__dict__ for r in self.results],
        }


class CodonErrorTester:
    """Utility class for testing Codon error handling"""

    def __init__(self):
        self.results: List[CodonErrorResult] = []

    def test_error_handling(
        self,
        error_func: Callable,
        expected_error_type: type,
        test_name: str = "error_handling_test",
    ) -> CodonErrorResult:
        """Test error handling in compiled functions"""

        start_time = time.time()

        try:
            error_func()
            # If we get here, no error was raised
            result = CodonErrorResult(
                test_name=test_name,
                error_type="None",
                error_message="No error raised",
                handled_correctly=False,
                recovery_successful=False,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)

            # Check if error is of expected type
            handled_correctly = isinstance(e, expected_error_type)

            # Try to recover from error
            recovery_successful = self._test_error_recovery(error_func, e)

            result = CodonErrorResult(
                test_name=test_name,
                error_type=error_type,
                error_message=error_message,
                handled_correctly=handled_correctly,
                recovery_successful=recovery_successful,
                execution_time=time.time() - start_time,
            )

        self.results.append(result)
        return result

    def _test_error_recovery(
        self, error_func: Callable, original_error: Exception
    ) -> bool:
        """Test if error recovery is possible"""
        try:
            # This is a simplified recovery test
            # In practice, you might want to implement specific recovery strategies
            return False
        except Exception:
            return False

    def test_compilation_errors(
        self,
        invalid_code: str,
        expected_error_pattern: str,
        test_name: str = "compilation_error_test",
    ) -> CodonErrorResult:
        """Test compilation error handling"""

        start_time = time.time()

        # Use CodonCompilationTester to test compilation
        tester = CodonCompilationTester()
        compilation_result = tester.test_compilation(invalid_code, test_name)

        # Check if compilation failed as expected
        handled_correctly = not compilation_result.success
        error_message = compilation_result.error_message or "Unknown compilation error"

        # Check if error message matches expected pattern
        pattern_found = expected_error_pattern.lower() in error_message.lower()

        result = CodonErrorResult(
            test_name=test_name,
            error_type="CompilationError",
            error_message=error_message,
            handled_correctly=handled_correctly and pattern_found,
            recovery_successful=False,  # Compilation errors typically can't be recovered from
            execution_time=time.time() - start_time,
        )

        self.results.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all error handling test results"""
        if not self.results:
            return {"message": "No error handling tests run"}

        total_tests = len(self.results)
        correctly_handled = sum(1 for r in self.results if r.handled_correctly)
        successful_recoveries = sum(1 for r in self.results if r.recovery_successful)

        return {
            "total_tests": total_tests,
            "correctly_handled_errors": correctly_handled,
            "successful_recoveries": successful_recoveries,
            "error_handling_rate": (
                correctly_handled / total_tests if total_tests > 0 else 0
            ),
            "recovery_rate": (
                successful_recoveries / total_tests if total_tests > 0 else 0
            ),
            "test_details": [r.__dict__ for r in self.results],
        }


# Pytest fixtures for easy integration
@pytest.fixture
def codon_compilation_tester():
    """Provide Codon compilation testing utility"""
    return CodonCompilationTester()


@pytest.fixture
def codon_performance_tester():
    """Provide Codon performance testing utility"""
    return CodonPerformanceTester()


@pytest.fixture
def codon_error_tester():
    """Provide Codon error handling testing utility"""
    return CodonErrorTester()


@pytest.fixture
def codon_test_base():
    """Provide base class for Codon tests"""

    class TestCodonBase(CodonTestBase):
        def test_compilation(self) -> CodonCompilationResult:
            # Default implementation - override in subclasses
            return CodonCompilationResult(success=True, compilation_time=0.0)

        def test_performance(self) -> CodonPerformanceResult:
            # Default implementation - override in subclasses
            return CodonPerformanceResult(
                test_name="default",
                interpreted_time=1.0,
                compiled_time=0.5,
                speedup_ratio=2.0,
                memory_usage=0.0,
                cpu_usage=0.0,
                iterations=1,
            )

        def test_error_handling(self) -> CodonErrorResult:
            # Default implementation - override in subclasses
            return CodonErrorResult(
                test_name="default",
                error_type="None",
                error_message="No error",
                handled_correctly=True,
                recovery_successful=True,
                execution_time=0.0,
            )

    return TestCodonBase()


@pytest.fixture
def codon_performance_monitor():
    """Monitor performance metrics during Codon tests"""
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
    print(f"Codon performance metrics: {metrics}")
