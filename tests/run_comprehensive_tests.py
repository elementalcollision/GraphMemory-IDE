#!/usr/bin/env python3
"""
Comprehensive test runner for hybrid CPython/Codon architecture.
This script provides a unified interface for running all types of tests.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add the framework directory to the path
sys.path.insert(0, str(Path(__file__).parent / "framework"))

from framework.automated_testing_framework import AutomatedTestingFramework
from framework.hybrid_testing_framework import HybridTestingFramework
from framework.test_coverage_analyzer import TestCoverageAnalyzer
from framework.testing_guidelines import TestingGuidelines

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ComprehensiveTestRunner:
    """Comprehensive test runner for hybrid architecture"""

    def __init__(self):
        self.hybrid_framework = HybridTestingFramework()
        self.automated_framework = AutomatedTestingFramework()
        self.coverage_analyzer = TestCoverageAnalyzer()
        self.testing_guidelines = TestingGuidelines()

    async def run_all_tests(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Run all types of tests based on options"""
        logger.info("Starting comprehensive test suite")

        results = {
            "unit_tests": None,
            "integration_tests": None,
            "performance_tests": None,
            "thread_safety_tests": None,
            "coverage_analysis": None,
            "automated_tests": None,
            "summary": {},
        }

        start_time = time.time()

        try:
            # Run unit tests if requested
            if options.get("run_unit_tests", True):
                logger.info("Running unit tests...")
                results["unit_tests"] = await self.hybrid_framework.run_cpython_tests()
                results["unit_tests"].extend(
                    await self.hybrid_framework.run_codon_tests()
                )

            # Run integration tests if requested
            if options.get("run_integration_tests", True):
                logger.info("Running integration tests...")
                results["integration_tests"] = (
                    await self.hybrid_framework.run_integration_tests()
                )

            # Run performance tests if requested
            if options.get("run_performance_tests", True):
                logger.info("Running performance tests...")
                results["performance_tests"] = (
                    await self.hybrid_framework.run_performance_tests()
                )

            # Run thread safety tests if requested
            if options.get("run_thread_safety_tests", True):
                logger.info("Running thread safety tests...")
                results["thread_safety_tests"] = (
                    await self.hybrid_framework.run_thread_safety_tests()
                )

            # Run coverage analysis if requested
            if options.get("run_coverage_analysis", True):
                logger.info("Running coverage analysis...")
                results["coverage_analysis"] = (
                    await self.coverage_analyzer.run_coverage_analysis()
                )

            # Run automated tests if requested
            if options.get("run_automated_tests", True):
                logger.info("Running automated tests...")
                results["automated_tests"] = (
                    await self.automated_framework.run_automated_tests()
                )

            # Generate summary
            duration = time.time() - start_time
            results["summary"] = self._generate_summary(results, duration)

            logger.info(f"Comprehensive test suite completed in {duration:.2f} seconds")

        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            results["error"] = str(e)

        return results

    async def run_unit_tests_only(self) -> Dict[str, Any]:
        """Run only unit tests"""
        logger.info("Running unit tests only")

        results = {
            "cpython_tests": await self.hybrid_framework.run_cpython_tests(),
            "codon_tests": await self.hybrid_framework.run_codon_tests(),
        }

        # Generate summary
        all_tests = results["cpython_tests"] + results["codon_tests"]
        total_tests = len(all_tests)
        passed_tests = len([t for t in all_tests if t.status == "passed"])
        failed_tests = len([t for t in all_tests if t.status == "failed"])

        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (
                (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            ),
        }

        return results

    async def run_integration_tests_only(self) -> Dict[str, Any]:
        """Run only integration tests"""
        logger.info("Running integration tests only")

        results = {
            "integration_tests": await self.hybrid_framework.run_integration_tests()
        }

        # Generate summary
        all_tests = results["integration_tests"]
        total_tests = len(all_tests)
        passed_tests = len([t for t in all_tests if t.status == "passed"])
        failed_tests = len([t for t in all_tests if t.status == "failed"])

        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (
                (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            ),
        }

        return results

    async def run_performance_tests_only(self) -> Dict[str, Any]:
        """Run only performance tests"""
        logger.info("Running performance tests only")

        results = {
            "performance_tests": await self.hybrid_framework.run_performance_tests()
        }

        # Generate summary
        all_tests = results["performance_tests"]
        total_tests = len(all_tests)
        passed_tests = len([t for t in all_tests if t.status == "passed"])
        failed_tests = len([t for t in all_tests if t.status == "failed"])

        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (
                (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            ),
        }

        return results

    async def run_thread_safety_tests_only(self) -> Dict[str, Any]:
        """Run only thread safety tests"""
        logger.info("Running thread safety tests only")

        results = {
            "thread_safety_tests": await self.hybrid_framework.run_thread_safety_tests()
        }

        # Generate summary
        all_tests = results["thread_safety_tests"]
        total_tests = len(all_tests)
        passed_tests = len([t for t in all_tests if t.status == "passed"])
        failed_tests = len([t for t in all_tests if t.status == "failed"])

        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (
                (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            ),
        }

        return results

    async def run_coverage_analysis_only(self) -> Dict[str, Any]:
        """Run only coverage analysis"""
        logger.info("Running coverage analysis only")

        results = await self.coverage_analyzer.run_coverage_analysis()

        return results

    def _generate_summary(
        self, results: Dict[str, Any], duration: float
    ) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        summary = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "success_rate": 0.0,
            "duration": duration,
            "components_tested": [],
            "coverage_met": False,
            "performance_met": False,
            "thread_safety_met": False,
        }

        # Aggregate test results
        for test_type, test_results in results.items():
            if (
                test_type == "summary"
                or test_type == "coverage_analysis"
                or test_type == "automated_tests"
            ):
                continue

            if test_results:
                if isinstance(test_results, list):
                    summary["total_tests"] += len(test_results)
                    summary["passed_tests"] += len(
                        [t for t in test_results if t.status == "passed"]
                    )
                    summary["failed_tests"] += len(
                        [t for t in test_results if t.status == "failed"]
                    )
                    summary["skipped_tests"] += len(
                        [t for t in test_results if t.status == "skipped"]
                    )
                    summary["components_tested"].append(test_type)

        # Calculate success rate
        if summary["total_tests"] > 0:
            summary["success_rate"] = (
                summary["passed_tests"] / summary["total_tests"]
            ) * 100

        # Check coverage
        if results.get("coverage_analysis"):
            coverage_report = results["coverage_analysis"].get("report")
            if coverage_report:
                summary["coverage_met"] = coverage_report.meets_threshold

        # Check performance
        if results.get("performance_tests"):
            performance_tests = results["performance_tests"]
            if performance_tests:
                summary["performance_met"] = all(
                    t.status == "passed" for t in performance_tests
                )

        # Check thread safety
        if results.get("thread_safety_tests"):
            thread_safety_tests = results["thread_safety_tests"]
            if thread_safety_tests:
                summary["thread_safety_met"] = all(
                    t.status == "passed" for t in thread_safety_tests
                )

        return summary

    def print_results(self, results: Dict[str, Any]) -> None:
        """Print test results in a formatted way"""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE TEST RESULTS")
        print("=" * 60)

        if "error" in results:
            print(f"❌ ERROR: {results['error']}")
            return

        summary = results.get("summary", {})

        print(f"📊 Total Tests: {summary.get('total_tests', 0)}")
        print(f"✅ Passed: {summary.get('passed_tests', 0)}")
        print(f"❌ Failed: {summary.get('failed_tests', 0)}")
        print(f"⏭️  Skipped: {summary.get('skipped_tests', 0)}")
        print(f"📈 Success Rate: {summary.get('success_rate', 0):.2f}%")
        print(f"⏱️  Duration: {summary.get('duration', 0):.2f}s")

        print("\n📋 Component Results:")
        for test_type, test_results in results.items():
            if test_type in ["summary", "coverage_analysis", "automated_tests"]:
                continue

            if test_results:
                if isinstance(test_results, list):
                    passed = len([t for t in test_results if t.status == "passed"])
                    failed = len([t for t in test_results if t.status == "failed"])
                    total = len(test_results)
                    success_rate = (passed / total) * 100 if total > 0 else 0
                    status = "✅" if failed == 0 else "❌"
                    print(
                        f"  {status} {test_type}: {passed}/{total} passed ({success_rate:.1f}%)"
                    )

        print("\n🎯 Quality Gates:")
        coverage_status = "✅" if summary.get("coverage_met", False) else "❌"
        performance_status = "✅" if summary.get("performance_met", False) else "❌"
        thread_safety_status = "✅" if summary.get("thread_safety_met", False) else "❌"

        print(f"  {coverage_status} Coverage Threshold Met")
        print(f"  {performance_status} Performance Requirements Met")
        print(f"  {thread_safety_status} Thread Safety Requirements Met")

        print("\n" + "=" * 60)

        # Overall success
        overall_success = summary.get("failed_tests", 0) == 0
        if overall_success:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️  SOME TESTS FAILED")

        print("=" * 60 + "\n")


def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Test Runner for Hybrid Architecture"
    )

    parser.add_argument(
        "--test-type",
        choices=[
            "all",
            "unit",
            "integration",
            "performance",
            "thread-safety",
            "coverage",
        ],
        default="all",
        help="Type of tests to run",
    )

    parser.add_argument(
        "--skip-unit-tests", action="store_true", help="Skip unit tests"
    )

    parser.add_argument(
        "--skip-integration-tests", action="store_true", help="Skip integration tests"
    )

    parser.add_argument(
        "--skip-performance-tests", action="store_true", help="Skip performance tests"
    )

    parser.add_argument(
        "--skip-thread-safety-tests",
        action="store_true",
        help="Skip thread safety tests",
    )

    parser.add_argument(
        "--skip-coverage-analysis", action="store_true", help="Skip coverage analysis"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "--output-format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format for results",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create test runner
    runner = ComprehensiveTestRunner()

    # Determine test options
    options = {
        "run_unit_tests": not args.skip_unit_tests,
        "run_integration_tests": not args.skip_integration_tests,
        "run_performance_tests": not args.skip_performance_tests,
        "run_thread_safety_tests": not args.skip_thread_safety_tests,
        "run_coverage_analysis": not args.skip_coverage_analysis,
        "run_automated_tests": True,
    }

    async def run_tests():
        """Run tests based on command line arguments"""
        if args.test_type == "all":
            results = await runner.run_all_tests(options)
        elif args.test_type == "unit":
            results = await runner.run_unit_tests_only()
        elif args.test_type == "integration":
            results = await runner.run_integration_tests_only()
        elif args.test_type == "performance":
            results = await runner.run_performance_tests_only()
        elif args.test_type == "thread-safety":
            results = await runner.run_thread_safety_tests_only()
        elif args.test_type == "coverage":
            results = await runner.run_coverage_analysis_only()
        else:
            print(f"Unknown test type: {args.test_type}")
            return

        # Print results
        if args.output_format == "text":
            runner.print_results(results)
        elif args.output_format == "json":
            import json

            print(json.dumps(results, indent=2, default=str))
        elif args.output_format == "html":
            # Generate HTML report
            print("HTML report generation not implemented yet")

        # Exit with appropriate code
        summary = results.get("summary", {})
        failed_tests = summary.get("failed_tests", 0)
        sys.exit(1 if failed_tests > 0 else 0)

    # Run the tests
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
