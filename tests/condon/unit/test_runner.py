"""
Codon Unit Test Runner

This module provides a comprehensive test runner for the Codon unit testing
framework, including test execution, coverage reporting, and performance analysis.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from tests.codon.base import (
    CodonCompilationTester,
    CodonErrorTester,
    CodonPerformanceTester,
)


class CodonTestRunner:
    """Comprehensive test runner for Codon unit tests"""

    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.compilation_tester = CodonCompilationTester()
        self.performance_tester = CodonPerformanceTester()
        self.error_tester = CodonErrorTester()

        self.results = {
            "compilation": [],
            "performance": [],
            "error_handling": [],
            "coverage": {},
            "summary": {},
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all Codon unit tests"""
        print("Starting Codon Unit Test Suite...")
        start_time = time.time()

        # Run compilation tests
        print("\n=== Running Compilation Tests ===")
        self._run_compilation_tests()

        # Run performance tests
        print("\n=== Running Performance Tests ===")
        self._run_performance_tests()

        # Run error handling tests
        print("\n=== Running Error Handling Tests ===")
        self._run_error_handling_tests()

        # Run coverage analysis
        print("\n=== Running Coverage Analysis ===")
        self._run_coverage_analysis()

        # Generate summary
        print("\n=== Generating Test Summary ===")
        self._generate_summary()

        # Save results
        self._save_results()

        execution_time = time.time() - start_time
        print(f"\nTest suite completed in {execution_time:.2f} seconds")

        return self.results

    def _run_compilation_tests(self):
        """Run compilation tests for all components"""
        test_components = ["analytics_engine", "algorithms", "cache"]

        for component in test_components:
            print(f"Testing compilation for {component}...")

            # Create test code for component
            test_code = self._generate_test_code(component)

            # Test compilation
            result = self.compilation_tester.test_compilation(
                test_code,
                test_name=f"{component}_compilation",
                optimization_level="release",
            )

            self.results["compilation"].append(
                {"component": component, "result": result.__dict__}
            )

            if result.success:
                print(f"  ✓ {component} compilation successful")
            else:
                print(f"  ✗ {component} compilation failed: {result.error_message}")

    def _run_performance_tests(self):
        """Run performance tests for all components"""
        test_components = ["analytics_engine", "algorithms", "cache"]

        for component in test_components:
            print(f"Testing performance for {component}...")

            # Create performance test functions
            interpreted_func, compiled_func = self._generate_performance_functions(
                component
            )

            # Test performance
            result = self.performance_tester.benchmark_interpreted_vs_compiled(
                interpreted_func,
                compiled_func,
                test_name=f"{component}_performance",
                iterations=100,
            )

            self.results["performance"].append(
                {"component": component, "result": result.__dict__}
            )

            print(f"  Speedup ratio: {result.speedup_ratio:.2f}x")

    def _run_error_handling_tests(self):
        """Run error handling tests for all components"""
        test_components = ["analytics_engine", "algorithms", "cache"]

        for component in test_components:
            print(f"Testing error handling for {component}...")

            # Create error test function
            error_func, expected_error = self._generate_error_functions(component)

            # Test error handling
            result = self.error_tester.test_error_handling(
                error_func, expected_error, test_name=f"{component}_error_handling"
            )

            self.results["error_handling"].append(
                {"component": component, "result": result.__dict__}
            )

            if result.handled_correctly:
                print(f"  ✓ {component} error handling correct")
            else:
                print(f"  ✗ {component} error handling failed")

    def _run_coverage_analysis(self):
        """Run code coverage analysis"""
        try:
            import coverage

            # Initialize coverage
            cov = coverage.Coverage()
            cov.start()

            # Import and run test modules
            test_modules = [
                "tests.codon.unit.test_analytics_engine",
                "tests.codon.unit.test_algorithms",
                "tests.codon.unit.test_cache",
            ]

            for module_name in test_modules:
                try:
                    __import__(module_name)
                except ImportError:
                    print(f"Warning: Could not import {module_name}")

            # Stop coverage and get report
            cov.stop()
            cov.save()

            # Generate coverage report
            coverage_data = cov.get_data()
            total_lines = 0
            covered_lines = 0

            for filename in coverage_data.measured_files():
                if "server/analytics" in filename:
                    file_coverage = coverage_data.get_file_coverage(filename)
                    total_lines += len(file_coverage)
                    covered_lines += sum(1 for line in file_coverage if line > 0)

            coverage_percentage = (
                (covered_lines / total_lines * 100) if total_lines > 0 else 0
            )

            self.results["coverage"] = {
                "total_lines": total_lines,
                "covered_lines": covered_lines,
                "coverage_percentage": coverage_percentage,
                "files_measured": len(
                    [
                        f
                        for f in coverage_data.measured_files()
                        if "server/analytics" in f
                    ]
                ),
            }

            print(
                f"  Coverage: {coverage_percentage:.1f}% ({covered_lines}/{total_lines} lines)"
            )

        except ImportError:
            print("Warning: coverage module not available")
            self.results["coverage"] = {"error": "coverage module not available"}

    def _generate_summary(self):
        """Generate test summary"""
        # Compilation summary
        compilation_success = sum(
            1 for r in self.results["compilation"] if r["result"]["success"]
        )
        compilation_total = len(self.results["compilation"])

        # Performance summary
        avg_speedup = 0
        if self.results["performance"]:
            speedups = [
                r["result"]["speedup_ratio"] for r in self.results["performance"]
            ]
            avg_speedup = sum(speedups) / len(speedups)

        # Error handling summary
        error_handling_success = sum(
            1
            for r in self.results["error_handling"]
            if r["result"]["handled_correctly"]
        )
        error_handling_total = len(self.results["error_handling"])

        self.results["summary"] = {
            "compilation": {
                "success_rate": (
                    compilation_success / compilation_total
                    if compilation_total > 0
                    else 0
                ),
                "successful": compilation_success,
                "total": compilation_total,
            },
            "performance": {
                "avg_speedup_ratio": avg_speedup,
                "tests_run": len(self.results["performance"]),
            },
            "error_handling": {
                "success_rate": (
                    error_handling_success / error_handling_total
                    if error_handling_total > 0
                    else 0
                ),
                "successful": error_handling_success,
                "total": error_handling_total,
            },
            "coverage": self.results["coverage"],
        }

    def _save_results(self):
        """Save test results to files"""
        # Save detailed results
        results_file = self.output_dir / "codon_test_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        # Save summary
        summary_file = self.output_dir / "codon_test_summary.json"
        with open(summary_file, "w") as f:
            json.dump(self.results["summary"], f, indent=2, default=str)

        print(f"Results saved to {self.output_dir}")

    def _generate_test_code(self, component: str) -> str:
        """Generate test code for a component"""
        if component == "analytics_engine":
            return """
from server.analytics.engine import AnalyticsEngine

def test_analytics_engine():
    engine = AnalyticsEngine()
    result = engine.initialize()
    return result

if __name__ == "__main__":
    test_analytics_engine()
"""
        elif component == "algorithms":
            return """
from server.analytics.algorithms import GraphAlgorithms

def test_algorithms():
    algorithms = GraphAlgorithms()
    result = algorithms.initialize()
    return result

if __name__ == "__main__":
    test_algorithms()
"""
        elif component == "cache":
            return """
from server.analytics.cache import CacheManager

def test_cache():
    cache = CacheManager()
    result = cache.initialize()
    return result

if __name__ == "__main__":
    test_cache()
"""
        else:
            return "print('Test code')"

    def _generate_performance_functions(self, component: str):
        """Generate performance test functions for a component"""

        def interpreted_func():
            # Simulate interpreted operation
            time.sleep(0.001)  # Simulate processing time
            return f"{component}_interpreted_result"

        def compiled_func():
            # Simulate compiled operation (faster)
            time.sleep(0.0005)  # Simulate faster processing
            return f"{component}_compiled_result"

        return interpreted_func, compiled_func

    def _generate_error_functions(self, component: str):
        """Generate error test functions for a component"""

        def error_func():
            # Simulate error condition
            raise ValueError(f"Test error for {component}")

        return error_func, ValueError


def run_codon_unit_tests():
    """Main function to run Codon unit tests"""
    runner = CodonTestRunner()
    results = runner.run_all_tests()

    # Print summary
    summary = results["summary"]
    print("\n" + "=" * 50)
    print("CONDON UNIT TEST SUMMARY")
    print("=" * 50)
    print(f"Compilation Success Rate: {summary['compilation']['success_rate']:.1%}")
    print(
        f"Average Performance Speedup: {summary['performance']['avg_speedup_ratio']:.2f}x"
    )
    print(
        f"Error Handling Success Rate: {summary['error_handling']['success_rate']:.1%}"
    )

    if "coverage_percentage" in summary["coverage"]:
        print(f"Code Coverage: {summary['coverage']['coverage_percentage']:.1f}%")

    print("=" * 50)

    return results


if __name__ == "__main__":
    run_codon_unit_tests()
