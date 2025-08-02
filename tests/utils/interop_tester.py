"""
Interoperability Test Utilities for CPython-Codon Integration

This module provides utilities for testing CPython-Codon interoperability,
including thread safety testing, data type conversions, and service 
boundary testing.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of interoperability tests"""

    THREAD_SAFETY = "thread_safety"
    DATA_TYPE_CONVERSION = "data_type_conversion"
    SERVICE_BOUNDARY = "service_boundary"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE = "performance"


@dataclass
class InteropTestResult:
    """Result of an interoperability test"""

    test_name: str
    test_type: TestType
    status: str  # "passed", "failed", "error"
    duration: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ThreadSafetyTester:
    """Thread safety testing utilities for CPython-Codon boundaries"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.results: List[InteropTestResult] = []

    async def test_concurrent_access(
        self, test_func: Callable, num_threads: int = 5, iterations: int = 100
    ) -> InteropTestResult:
        """Test concurrent access to CPython-Codon boundaries"""
        start_time = time.time()
        test_name = f"concurrent_access_{test_func.__name__}"

        try:
            # Create tasks for concurrent execution
            tasks = []
            for i in range(num_threads):
                task = asyncio.create_task(
                    self._run_concurrent_test(test_func, iterations)
                )
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for exceptions
            exceptions = [r for r in results if isinstance(r, Exception)]
            if exceptions:
                return InteropTestResult(
                    test_name=test_name,
                    test_type=TestType.THREAD_SAFETY,
                    status="failed",
                    duration=time.time() - start_time,
                    error_message=f"Thread safety test failed: {exceptions[0]}",
                    metrics={
                        "exceptions": len(exceptions),
                        "total_threads": num_threads,
                    },
                )

            return InteropTestResult(
                test_name=test_name,
                test_type=TestType.THREAD_SAFETY,
                status="passed",
                duration=time.time() - start_time,
                metrics={"total_threads": num_threads, "iterations": iterations},
            )

        except Exception as e:
            return InteropTestResult(
                test_name=test_name,
                test_type=TestType.THREAD_SAFETY,
                status="error",
                duration=time.time() - start_time,
                error_message=str(e),
            )

    async def _run_concurrent_test(self, test_func: Callable, iterations: int) -> None:
        """Run a test function concurrently"""
        for _ in range(iterations):
            await test_func()

    def test_race_condition(
        self, shared_resource: Any, access_func: Callable, num_threads: int = 10
    ) -> InteropTestResult:
        """Test for race conditions in shared resources"""
        start_time = time.time()
        test_name = "race_condition_test"

        try:
            # Create threads that access the shared resource
            threads = []
            for i in range(num_threads):
                thread = threading.Thread(
                    target=self._access_shared_resource,
                    args=(shared_resource, access_func, i),
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            return InteropTestResult(
                test_name=test_name,
                test_type=TestType.THREAD_SAFETY,
                status="passed",
                duration=time.time() - start_time,
                metrics={"total_threads": num_threads},
            )

        except Exception as e:
            return InteropTestResult(
                test_name=test_name,
                test_type=TestType.THREAD_SAFETY,
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _access_shared_resource(
        self, resource: Any, access_func: Callable, thread_id: int
    ) -> None:
        """Access shared resource from a thread"""
        try:
            access_func(resource, thread_id)
        except Exception as e:
            logger.error(f"Thread {thread_id} failed: {e}")
            raise


class DataTypeConversionTester:
    """Data type conversion testing utilities"""

    def __init__(self):
        self.results: List[InteropTestResult] = []

    async def test_round_trip_conversion(
        self,
        python_data: Any,
        conversion_func: Callable,
        reverse_conversion_func: Callable,
    ) -> InteropTestResult:
        """Test round-trip data conversion between CPython and Codon"""
        start_time = time.time()
        test_name = f"round_trip_conversion_{type(python_data).__name__}"

        try:
            # Convert Python data to Codon format
            codon_data = conversion_func(python_data)

            # Convert back to Python format
            converted_back = reverse_conversion_func(codon_data)

            # Compare original and converted data
            if self._deep_compare(python_data, converted_back):
                return InteropTestResult(
                    test_name=test_name,
                    test_type=TestType.DATA_TYPE_CONVERSION,
                    status="passed",
                    duration=time.time() - start_time,
                    metrics={"original_type": str(type(python_data))},
                )
            else:
                return InteropTestResult(
                    test_name=test_name,
                    test_type=TestType.DATA_TYPE_CONVERSION,
                    status="failed",
                    duration=time.time() - start_time,
                    error_message="Data mismatch after round-trip conversion",
                )

        except Exception as e:
            return InteropTestResult(
                test_name=test_name,
                test_type=TestType.DATA_TYPE_CONVERSION,
                status="error",
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _deep_compare(self, obj1: Any, obj2: Any) -> bool:
        """Deep comparison of objects"""
        if not isinstance(obj2, type(obj1)):
            return False

        if isinstance(obj1, (list, tuple)):
            if len(obj1) != len(obj2):
                return False
            return all(self._deep_compare(a, b) for a, b in zip(obj1, obj2))

        elif isinstance(obj1, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(self._deep_compare(obj1[k], obj2[k]) for k in obj1)

        else:
            return obj1 == obj2

    async def test_edge_cases(
        self, conversion_func: Callable, edge_cases: List[Any]
    ) -> List[InteropTestResult]:
        """Test data conversion with edge cases"""
        results = []

        for i, edge_case in enumerate(edge_cases):
            start_time = time.time()
            test_name = f"edge_case_{i}_{type(edge_case).__name__}"

            try:
                # Test the conversion
                conversion_func(edge_case)
                results.append(
                    InteropTestResult(
                        test_name=test_name,
                        test_type=TestType.DATA_TYPE_CONVERSION,
                        status="passed",
                        duration=time.time() - start_time,
                        metrics={"edge_case_type": str(type(edge_case))},
                    )
                )
            except Exception as e:
                results.append(
                    InteropTestResult(
                        test_name=test_name,
                        test_type=TestType.DATA_TYPE_CONVERSION,
                        status="failed",
                        duration=time.time() - start_time,
                        error_message=str(e),
                    )
                )

        return results


class ServiceBoundaryTester:
    """Service boundary testing utilities"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[InteropTestResult] = []

    async def test_service_boundary(
        self,
        endpoint: str,
        test_data: Dict[str, Any],
        expected_response: Dict[str, Any],
    ) -> InteropTestResult:
        """Test service boundary between CPython and Codon"""
        start_time = time.time()
        test_name = f"service_boundary_{endpoint}"

        try:
            # This would typically make an HTTP request to the service
            # For now, we'll simulate the test
            response = await self._make_request(endpoint, test_data)

            if self._validate_response(response, expected_response):
                return InteropTestResult(
                    test_name=test_name,
                    test_type=TestType.SERVICE_BOUNDARY,
                    status="passed",
                    duration=time.time() - start_time,
                    metrics={"endpoint": endpoint},
                )
            else:
                return InteropTestResult(
                    test_name=test_name,
                    test_type=TestType.SERVICE_BOUNDARY,
                    status="failed",
                    duration=time.time() - start_time,
                    error_message="Response validation failed",
                )

        except Exception as e:
            return InteropTestResult(
                test_name=test_name,
                test_type=TestType.SERVICE_BOUNDARY,
                status="error",
                duration=time.time() - start_time,
                error_message=str(e),
            )

    async def _make_request(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a request to the service (placeholder implementation)"""
        # This would be implemented with actual HTTP client
        return {"status": "success", "data": data}

    def _validate_response(
        self, response: Dict[str, Any], expected: Dict[str, Any]
    ) -> bool:
        """Validate service response"""
        return response.get("status") == expected.get("status")


class InteropTestFramework:
    """Main interoperability testing framework"""

    def __init__(self):
        self.thread_safety_tester = ThreadSafetyTester()
        self.data_type_tester = DataTypeConversionTester()
        self.service_boundary_tester = ServiceBoundaryTester()
        self.all_results: List[InteropTestResult] = []

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive interoperability tests"""
        logger.info("Starting comprehensive CPython-Codon interoperability tests")

        results = {
            "thread_safety": [],
            "data_type_conversion": [],
            "service_boundary": [],
            "summary": {},
        }

        # Run thread safety tests
        results["thread_safety"] = await self._run_thread_safety_tests()

        # Run data type conversion tests
        results["data_type_conversion"] = await self._run_data_type_tests()

        # Run service boundary tests
        results["service_boundary"] = await self._run_service_boundary_tests()

        # Generate summary
        results["summary"] = self._generate_summary(results)

        return results

    async def _run_thread_safety_tests(self) -> List[InteropTestResult]:
        """Run thread safety tests"""
        # Placeholder for actual thread safety tests
        return []

    async def _run_data_type_tests(self) -> List[InteropTestResult]:
        """Run data type conversion tests"""
        # Placeholder for actual data type tests
        return []

    async def _run_service_boundary_tests(self) -> List[InteropTestResult]:
        """Run service boundary tests"""
        # Placeholder for actual service boundary tests
        return []

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        for category in ["thread_safety", "data_type_conversion", "service_boundary"]:
            for result in results[category]:
                total_tests += 1
                if result.status == "passed":
                    passed_tests += 1
                else:
                    failed_tests += 1

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
        }


# Convenience functions
def get_interop_test_framework() -> InteropTestFramework:
    """Get the interoperability test framework instance"""
    return InteropTestFramework()


async def run_interop_tests() -> Dict[str, Any]:
    """Run interoperability tests"""
    framework = get_interop_test_framework()
    return await framework.run_comprehensive_tests()
