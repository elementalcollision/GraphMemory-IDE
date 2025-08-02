"""
Main Integration Test Runner for CPython-Codon Interoperability

This module provides a comprehensive test runner for all CPython-Codon
interoperability tests, including thread safety, data type conversions,
and service boundary testing.
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List

from tests.utils.interop_tester import InteropTestFramework

from .test_data_type_conversions import run_data_type_conversion_integration_tests
from .test_service_boundaries import run_service_boundary_integration_tests
from .test_thread_safety import run_thread_safety_integration_tests

logger = logging.getLogger(__name__)


class CPythonCodonIntegrationTestRunner:
    """Main test runner for CPython-Codon integration tests"""

    def __init__(self):
        self.framework = InteropTestFramework()
        self.results: Dict[str, Any] = {}
        self.start_time = datetime.now()

    async def run_all_integration_tests(self) -> Dict[str, Any]:
        """Run all CPython-Codon integration tests"""
        logger.info("Starting comprehensive CPython-Codon integration test suite")

        results = {
            "test_suite": "CPython-Codon Integration Tests",
            "start_time": self.start_time.isoformat(),
            "thread_safety": {},
            "data_type_conversion": {},
            "service_boundary": {},
            "comprehensive": {},
            "summary": {},
        }

        try:
            # Run thread safety tests
            logger.info("Running thread safety integration tests...")
            results["thread_safety"] = await run_thread_safety_integration_tests()

            # Run data type conversion tests
            logger.info("Running data type conversion integration tests...")
            results["data_type_conversion"] = (
                await run_data_type_conversion_integration_tests()
            )

            # Run service boundary tests
            logger.info("Running service boundary integration tests...")
            results["service_boundary"] = await run_service_boundary_integration_tests()

            # Run comprehensive framework tests
            logger.info("Running comprehensive interoperability tests...")
            results["comprehensive"] = await self.framework.run_comprehensive_tests()

            # Generate overall summary
            results["summary"] = self._generate_overall_summary(results)

            # Calculate end time and duration
            end_time = datetime.now()
            results["end_time"] = end_time.isoformat()
            results["duration"] = (end_time - self.start_time).total_seconds()

            logger.info("CPython-Codon integration test suite completed")
            return results

        except Exception as e:
            logger.error(f"Integration test suite failed: {e}")
            results["error"] = str(e)
            return results

    def _generate_overall_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        error_tests = 0

        # Aggregate results from all test categories
        categories = ["thread_safety", "data_type_conversion", "service_boundary"]

        for category in categories:
            if category in results and "summary" in results[category]:
                summary = results[category]["summary"]
                total_tests += summary.get("total_tests", 0)
                passed_tests += summary.get("passed_tests", 0)
                failed_tests += summary.get("failed_tests", 0)
                error_tests += summary.get("error_tests", 0)

        # Calculate success rate
        success_rate = 0.0
        if total_tests > 0:
            success_rate = passed_tests / total_tests

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "success_rate": success_rate,
            "test_categories": len(categories),
        }

    def print_results(self, results: Dict[str, Any]) -> None:
        """Print test results in a formatted way"""
        print("\n" + "=" * 80)
        print("CPython-Codon Integration Test Results")
        print("=" * 80)

        # Print summary
        summary = results.get("summary", {})
        print(f"\nOverall Summary:")
        print(f"  Total Tests: {summary.get('total_tests', 0)}")
        print(f"  Passed: {summary.get('passed_tests', 0)}")
        print(f"  Failed: {summary.get('failed_tests', 0)}")
        print(f"  Errors: {summary.get('error_tests', 0)}")
        print(f"  Success Rate: {summary.get('success_rate', 0):.2%}")

        # Print category results
        print(f"\nCategory Results:")
        categories = ["thread_safety", "data_type_conversion", "service_boundary"]

        for category in categories:
            if category in results and "summary" in results[category]:
                cat_summary = results[category]["summary"]
                print(f"  {category.replace('_', ' ').title()}:")
                print(f"    Total: {cat_summary.get('total_tests', 0)}")
                print(f"    Passed: {cat_summary.get('passed_tests', 0)}")
                print(f"    Failed: {cat_summary.get('failed_tests', 0)}")
                print(f"    Success Rate: {cat_summary.get('success_rate', 0):.2%}")

        # Print timing information
        if "duration" in results:
            print(f"\nTest Duration: {results['duration']:.2f} seconds")

        print("=" * 80)


async def run_cpython_codon_integration_tests() -> Dict[str, Any]:
    """Convenience function to run all CPython-Codon integration tests"""
    runner = CPythonCodonIntegrationTestRunner()
    results = await runner.run_all_integration_tests()
    runner.print_results(results)
    return results


def main():
    """Main entry point for running integration tests"""
    try:
        results = asyncio.run(run_cpython_codon_integration_tests())

        # Exit with appropriate code based on test results
        summary = results.get("summary", {})
        success_rate = summary.get("success_rate", 0)

        if success_rate >= 0.8:  # 80% success rate threshold
            print("\n✅ Integration tests passed with high success rate")
            sys.exit(0)
        elif success_rate >= 0.6:  # 60% success rate threshold
            print("\n⚠️  Integration tests passed with moderate success rate")
            sys.exit(0)
        else:
            print("\n❌ Integration tests failed with low success rate")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Integration test runner failed: {e}")
        print(f"\n❌ Integration test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
