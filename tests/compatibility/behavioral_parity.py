"""
Behavioral Parity Testing Framework

This module provides comprehensive testing utilities for ensuring behavioral
parity between Codon and CPython implementations.
"""

import inspect
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BehavioralParityResult:
    """Result of behavioral parity testing"""

    success: bool
    test_time: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    performance_differences: Dict[str, float] = field(default_factory=dict)


@dataclass
class TestCase:
    """Test case for behavioral parity testing"""

    name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    expected_result: Optional[Any] = None
    expected_exception: Optional[Type[Exception]] = None
    tolerance: float = 0.001
    iterations: int = 1


class BehavioralParityTester:
    """Behavioral parity testing framework"""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.test_results: List[BehavioralParityResult] = []

    def test_function_parity(
        self,
        cpython_func: Callable,
        codon_func: Callable,
        test_cases: List[TestCase],
        func_name: str = "function",
    ) -> BehavioralParityResult:
        """Test behavioral parity between CPython and Codon functions"""

        result = BehavioralParityResult(
            success=True,
            test_time=0.0,
            total_tests=len(test_cases),
            passed_tests=0,
            failed_tests=0,
        )

        start_time = time.time()

        for test_case in test_cases:
            try:
                test_result = self._test_single_case(
                    cpython_func, codon_func, test_case, func_name
                )

                if test_result:
                    result.passed_tests += 1
                else:
                    result.failed_tests += 1
                    result.success = False

            except Exception as e:
                error_msg = f"Error in test case '{test_case.name}': {e}"
                result.errors.append(error_msg)
                result.failed_tests += 1
                result.success = False

        result.test_time = time.time() - start_time
        self.test_results.append(result)

        return result

    def test_class_parity(
        self,
        cpython_class: Type,
        codon_class: Type,
        test_cases: List[Dict[str, Any]],
        class_name: str = "class",
    ) -> BehavioralParityResult:
        """Test behavioral parity between CPython and Codon classes"""

        result = BehavioralParityResult(
            success=True,
            test_time=0.0,
            total_tests=len(test_cases),
            passed_tests=0,
            failed_tests=0,
        )

        start_time = time.time()

        for i, test_case in enumerate(test_cases):
            try:
                # Test instantiation
                cpython_instance = cpython_class(**test_case.get("init_args", {}))
                codon_instance = codon_class(**test_case.get("init_args", {}))

                # Test method calls
                methods = test_case.get("methods", [])
                for method_test in methods:
                    method_name = method_test["name"]
                    method_args = method_test.get("args", [])
                    method_kwargs = method_test.get("kwargs", {})

                    # Call methods
                    cpython_method = getattr(cpython_instance, method_name)
                    codon_method = getattr(codon_instance, method_name)

                    cpython_result = cpython_method(*method_args, **method_kwargs)
                    codon_result = codon_method(*method_args, **method_kwargs)

                    # Compare results
                    if not self._compare_results(cpython_result, codon_result):
                        error_msg = f"Method {method_name} mismatch in test case {i}"
                        result.errors.append(error_msg)
                        result.failed_tests += 1
                        result.success = False
                    else:
                        result.passed_tests += 1

            except Exception as e:
                error_msg = f"Error in class test case {i}: {e}"
                result.errors.append(error_msg)
                result.failed_tests += 1
                result.success = False

        result.test_time = time.time() - start_time
        self.test_results.append(result)

        return result

    def test_module_parity(
        self,
        cpython_module,
        codon_module,
        function_names: List[str],
        test_cases: Dict[str, List[TestCase]],
    ) -> BehavioralParityResult:
        """Test behavioral parity between CPython and Codon modules"""

        result = BehavioralParityResult(
            success=True, test_time=0.0, total_tests=0, passed_tests=0, failed_tests=0
        )

        start_time = time.time()

        for func_name in function_names:
            if func_name not in test_cases:
                continue

            try:
                cpython_func = getattr(cpython_module, func_name)
                codon_func = getattr(codon_module, func_name)

                func_test_cases = test_cases[func_name]
                result.total_tests += len(func_test_cases)

                func_result = self.test_function_parity(
                    cpython_func, codon_func, func_test_cases, func_name
                )

                result.passed_tests += func_result.passed_tests
                result.failed_tests += func_result.failed_tests
                result.errors.extend(func_result.errors)
                result.warnings.extend(func_result.warnings)

                if not func_result.success:
                    result.success = False

            except Exception as e:
                error_msg = f"Error testing function {func_name}: {e}"
                result.errors.append(error_msg)
                result.failed_tests += 1
                result.success = False

        result.test_time = time.time() - start_time
        self.test_results.append(result)

        return result

    def test_performance_parity(
        self,
        cpython_func: Callable,
        codon_func: Callable,
        test_cases: List[TestCase],
        func_name: str = "function",
    ) -> BehavioralParityResult:
        """Test performance parity between implementations"""

        result = BehavioralParityResult(
            success=True,
            test_time=0.0,
            total_tests=len(test_cases),
            passed_tests=0,
            failed_tests=0,
        )

        start_time = time.time()

        for test_case in test_cases:
            try:
                # Measure CPython performance
                cpython_start = time.time()
                for _ in range(test_case.iterations):
                    cpython_func(*test_case.args, **test_case.kwargs)
                cpython_time = time.time() - cpython_start

                # Measure Codon performance
                codon_start = time.time()
                for _ in range(test_case.iterations):
                    codon_func(*test_case.args, **test_case.kwargs)
                codon_time = time.time() - codon_start

                # Calculate performance difference
                if cpython_time > 0:
                    performance_ratio = codon_time / cpython_time
                    result.performance_differences[test_case.name] = performance_ratio

                    # Check if Codon is significantly slower
                    if performance_ratio > 1.5:  # 50% slower threshold
                        warning_msg = f"Performance regression in {test_case.name}: {performance_ratio:.2f}x"
                        result.warnings.append(warning_msg)

                result.passed_tests += 1

            except Exception as e:
                error_msg = f"Error in performance test {test_case.name}: {e}"
                result.errors.append(error_msg)
                result.failed_tests += 1
                result.success = False

        result.test_time = time.time() - start_time
        self.test_results.append(result)

        return result

    def _test_single_case(
        self,
        cpython_func: Callable,
        codon_func: Callable,
        test_case: TestCase,
        func_name: str,
    ) -> bool:
        """Test a single test case"""

        try:
            # Test CPython implementation
            cpython_result = cpython_func(*test_case.args, **test_case.kwargs)

            # Test Codon implementation
            codon_result = codon_func(*test_case.args, **test_case.kwargs)

            # Compare results
            if test_case.expected_result is not None:
                if not self._compare_with_tolerance(
                    cpython_result, test_case.expected_result, test_case.tolerance
                ):
                    logger.error(
                        f"CPython result doesn't match expected for {test_case.name}"
                    )
                    return False

                if not self._compare_with_tolerance(
                    codon_result, test_case.expected_result, test_case.tolerance
                ):
                    logger.error(
                        f"Codon result doesn't match expected for {test_case.name}"
                    )
                    return False
            else:
                # Compare CPython and Codon results
                if not self._compare_results(cpython_result, codon_result):
                    logger.error(f"Result mismatch in {test_case.name}")
                    return False

            return True

        except Exception as e:
            if test_case.expected_exception:
                # Check if both implementations raise the same exception
                cpython_exception = None
                codon_exception = None

                try:
                    cpython_func(*test_case.args, **test_case.kwargs)
                except Exception as e_cp:
                    cpython_exception = type(e_cp)

                try:
                    codon_func(*test_case.args, **test_case.kwargs)
                except Exception as e_codon:
                    codon_exception = type(e_codon)

                if cpython_exception != codon_exception:
                    logger.error(f"Exception type mismatch in {test_case.name}")
                    return False

                return True
            else:
                logger.error(f"Unexpected exception in {test_case.name}: {e}")
                return False

    def _compare_results(self, result_a: Any, result_b: Any) -> bool:
        """Compare results for equality"""

        # Handle None values
        if result_a is None and result_b is None:
            return True
        if result_a is None or result_b is None:
            return False

        # Handle basic types
        if type(result_a) != type(result_b):
            return False

        # Handle different data types
        if isinstance(result_a, (dict, list, tuple)):
            return self._compare_structured_data(result_a, result_b)
        else:
            return result_a == result_b

    def _compare_structured_data(self, data_a: Any, data_b: Any) -> bool:
        """Compare structured data (dict, list, tuple)"""

        if isinstance(data_a, dict):
            if not isinstance(data_b, dict):
                return False
            if set(data_a.keys()) != set(data_b.keys()):
                return False
            return all(self._compare_results(data_a[k], data_b[k]) for k in data_a)

        elif isinstance(data_a, (list, tuple)):
            if not isinstance(data_b, type(data_a)):
                return False
            if len(data_a) != len(data_b):
                return False
            return all(self._compare_results(a, b) for a, b in zip(data_a, data_b))

        return data_a == data_b

    def _compare_with_tolerance(
        self, result: Any, expected: Any, tolerance: float
    ) -> bool:
        """Compare results with tolerance for floating point values"""

        if isinstance(result, (int, float)) and isinstance(expected, (int, float)):
            return abs(result - expected) <= tolerance
        else:
            return self._compare_results(result, expected)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all test results"""

        total_results = len(self.test_results)
        total_tests = sum(r.total_tests for r in self.test_results)
        total_passed = sum(r.passed_tests for r in self.test_results)
        total_failed = sum(r.failed_tests for r in self.test_results)
        total_time = sum(r.test_time for r in self.test_results)

        all_errors = []
        all_warnings = []
        all_performance = {}

        for result in self.test_results:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_performance.update(result.performance_differences)

        return {
            "total_results": total_results,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_time": total_time,
            "success_rate": total_passed / total_tests if total_tests > 0 else 0,
            "errors": all_errors,
            "warnings": all_warnings,
            "performance_differences": all_performance,
        }


# Pytest fixtures
@pytest.fixture
def behavioral_parity_tester():
    """Fixture for behavioral parity tester"""
    return BehavioralParityTester()


@pytest.fixture
def strict_behavioral_parity_tester():
    """Fixture for strict behavioral parity tester"""
    return BehavioralParityTester(strict_mode=True)
