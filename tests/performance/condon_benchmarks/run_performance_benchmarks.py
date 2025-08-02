"""
Main Performance Benchmark Runner for Codon vs CPython Comparisons

This module provides a comprehensive benchmark runner for all Codon vs CPython
performance comparisons, including baseline data storage and regression detection.
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List

from tests.utils.benchmark_runner import (
    BaselineManager,
    ImplementationType,
    PerformanceBenchmarker,
    PerformanceReporter,
    RegressionDetector,
)

from .test_analytics_operations import run_analytics_performance_tests

logger = logging.getLogger(__name__)


class CodonCPythonBenchmarkRunner:
    """Main benchmark runner for Codon vs CPython performance comparisons"""

    def __init__(self):
        self.benchmarker = PerformanceBenchmarker()
        self.baseline_manager = BaselineManager()
        self.regression_detector = RegressionDetector(self.baseline_manager)
        self.reporter = PerformanceReporter()
        self.results: Dict[str, Any] = {}
        self.start_time = datetime.now()

    async def run_comprehensive_benchmarks(self) -> Dict[str, Any]:
        """Run comprehensive Codon vs CPython performance benchmarks"""
        logger.info("Starting comprehensive Codon vs CPython performance benchmarks")

        results = {
            "benchmark_suite": "Codon vs CPython Performance Benchmarks",
            "start_time": self.start_time.isoformat(),
            "analytics_tests": {},
            "baseline_comparisons": {},
            "regression_analysis": {},
            "performance_report": {},
            "summary": {},
        }

        try:
            # Run analytics performance tests
            logger.info("Running analytics performance tests...")
            results["analytics_tests"] = await run_analytics_performance_tests()

            # Perform baseline comparisons
            logger.info("Performing baseline comparisons...")
            results["baseline_comparisons"] = await self._perform_baseline_comparisons(
                results["analytics_tests"]
            )

            # Detect performance regressions
            logger.info("Detecting performance regressions...")
            results["regression_analysis"] = await self._detect_regressions(
                results["analytics_tests"]
            )

            # Generate performance report
            logger.info("Generating performance report...")
            results["performance_report"] = await self._generate_performance_report(
                results["analytics_tests"]
            )

            # Generate overall summary
            results["summary"] = self._generate_overall_summary(results)

            # Calculate end time and duration
            end_time = datetime.now()
            results["end_time"] = end_time.isoformat()
            results["duration"] = (end_time - self.start_time).total_seconds()

            logger.info("Codon vs CPython performance benchmarks completed")
            return results

        except Exception as e:
            logger.error(f"Benchmark suite failed: {e}")
            results["error"] = str(e)
            return results

    async def _perform_baseline_comparisons(
        self, analytics_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comparisons against baseline data"""
        comparisons = {"baseline_checks": [], "improvements": [], "regressions": []}

        # Check each benchmark result against baselines
        for result in analytics_results.get("cpython_results", []):
            baseline = self.baseline_manager.load_baseline(
                result.benchmark_name, result.implementation
            )

            if baseline:
                comparison = self.regression_detector.detect_regression(
                    result, baseline
                )
                comparisons["baseline_checks"].append(comparison)

                if comparison["regression_detected"]:
                    comparisons["regressions"].append(comparison)
                elif comparison["improvement_detected"]:
                    comparisons["improvements"].append(comparison)

        # Check Codon results
        for result in analytics_results.get("codon_results", []):
            baseline = self.baseline_manager.load_baseline(
                result.benchmark_name, result.implementation
            )

            if baseline:
                comparison = self.regression_detector.detect_regression(
                    result, baseline
                )
                comparisons["baseline_checks"].append(comparison)

                if comparison["regression_detected"]:
                    comparisons["regressions"].append(comparison)
                elif comparison["improvement_detected"]:
                    comparisons["improvements"].append(comparison)

        return comparisons

    async def _detect_regressions(
        self, analytics_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect performance regressions in benchmark results"""
        regressions = {
            "total_regressions": 0,
            "cpython_regressions": 0,
            "codon_regressions": 0,
            "regression_details": [],
        }

        # Check CPython regressions
        for result in analytics_results.get("cpython_results", []):
            baseline = self.baseline_manager.load_baseline(
                result.benchmark_name, result.implementation
            )

            if baseline:
                regression = self.regression_detector.detect_regression(
                    result, baseline
                )
                if regression["regression_detected"]:
                    regressions["total_regressions"] += 1
                    regressions["cpython_regressions"] += 1
                    regressions["regression_details"].append(
                        {
                            "implementation": "cpython",
                            "benchmark": result.benchmark_name,
                            "regression": regression,
                        }
                    )

        # Check Codon regressions
        for result in analytics_results.get("codon_results", []):
            baseline = self.baseline_manager.load_baseline(
                result.benchmark_name, result.implementation
            )

            if baseline:
                regression = self.regression_detector.detect_regression(
                    result, baseline
                )
                if regression["regression_detected"]:
                    regressions["total_regressions"] += 1
                    regressions["codon_regressions"] += 1
                    regressions["regression_details"].append(
                        {
                            "implementation": "codon",
                            "benchmark": result.benchmark_name,
                            "regression": regression,
                        }
                    )

        return regressions

    async def _generate_performance_report(
        self, analytics_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        cpython_results = analytics_results.get("cpython_results", [])
        codon_results = analytics_results.get("codon_results", [])

        # Generate comparison report
        report = self.reporter.generate_comparison_report(
            cpython_results, codon_results
        )

        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_report_{timestamp}.json"
        self.reporter.save_report(report, filename)

        return {"report": report, "filename": filename}

    def _generate_overall_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall benchmark summary"""
        analytics_summary = results.get("analytics_tests", {}).get("summary", {})
        regression_summary = results.get("regression_analysis", {})

        return {
            "total_benchmarks": analytics_summary.get("total_tests", 0),
            "cpython_benchmarks": analytics_summary.get("cpython_tests", 0),
            "codon_benchmarks": analytics_summary.get("codon_tests", 0),
            "total_regressions": regression_summary.get("total_regressions", 0),
            "cpython_regressions": regression_summary.get("cpython_regressions", 0),
            "codon_regressions": regression_summary.get("codon_regressions", 0),
            "benchmark_duration": results.get("duration", 0),
        }

    def print_results(self, results: Dict[str, Any]) -> None:
        """Print benchmark results in a formatted way"""
        print("\n" + "=" * 80)
        print("Codon vs CPython Performance Benchmark Results")
        print("=" * 80)

        # Print summary
        summary = results.get("summary", {})
        print(f"\nOverall Summary:")
        print(f"  Total Benchmarks: {summary.get('total_benchmarks', 0)}")
        print(f"  CPython Benchmarks: {summary.get('cpython_benchmarks', 0)}")
        print(f"  Codon Benchmarks: {summary.get('codon_benchmarks', 0)}")
        print(f"  Total Regressions: {summary.get('total_regressions', 0)}")
        print(f"  CPython Regressions: {summary.get('cpython_regressions', 0)}")
        print(f"  Codon Regressions: {summary.get('codon_regressions', 0)}")

        # Print performance report summary
        performance_report = results.get("performance_report", {})
        if "report" in performance_report:
            report_summary = performance_report["report"].get("summary", {})
            print(f"\nPerformance Comparison Summary:")
            print(f"  Total Comparisons: {report_summary.get('total_benchmarks', 0)}")
            print(
                f"  Codon Faster: {report_summary.get('codon_faster_benchmarks', 0)}"
            )
            print(
                f"  Codon Memory Efficient: {report_summary.get('codon_memory_efficient_benchmarks', 0)}"
            )
            print(
                f"  Codon CPU Efficient: {report_summary.get('codon_cpu_efficient_benchmarks', 0)}"
            )
            print(
                f"  Average Execution Ratio: {report_summary.get('average_execution_ratio', 0):.3f}"
            )
            print(
                f"  Average Memory Ratio: {report_summary.get('average_memory_ratio', 0):.3f}"
            )
            print(
                f"  Average CPU Ratio: {report_summary.get('average_cpu_ratio', 0):.3f}"
            )

        # Print timing information
        if "duration" in results:
            print(f"\nBenchmark Duration: {results['duration']:.2f} seconds")

        print("=" * 80)


async def run_codon_cpython_benchmarks() -> Dict[str, Any]:
    """Convenience function to run all Codon vs CPython benchmarks"""
    runner = CodonCPythonBenchmarkRunner()
    results = await runner.run_comprehensive_benchmarks()
    runner.print_results(results)
    return results


def main():
    """Main entry point for running performance benchmarks"""
    try:
        results = asyncio.run(run_codon_cpython_benchmarks())

        # Exit with appropriate code based on benchmark results
        summary = results.get("summary", {})
        total_regressions = summary.get("total_regressions", 0)

        if total_regressions == 0:
            print("\n✅ Performance benchmarks passed with no regressions")
            sys.exit(0)
        elif total_regressions <= 2:
            print(
                f"\n⚠️  Performance benchmarks completed with {total_regressions} regressions"
            )
            sys.exit(0)
        else:
            print(
                f"\n❌ Performance benchmarks failed with {total_regressions} regressions"
            )
            sys.exit(1)

    except Exception as e:
        logger.error(f"Performance benchmark runner failed: {e}")
        print(f"\n❌ Performance benchmark runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
