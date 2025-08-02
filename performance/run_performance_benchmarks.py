"""
Performance Benchmarking Runner for Hybrid Architecture

This script provides a comprehensive performance benchmarking and optimization
runner for the hybrid CPython/Codon architecture, including performance monitoring,
optimization techniques, and production-ready performance validation.
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

from framework.hybrid_performance_framework import HybridPerformanceFramework
from framework.performance_monitoring import PerformanceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceBenchmarkRunner:
    """Comprehensive performance benchmarking runner"""

    def __init__(self):
        self.performance_framework = HybridPerformanceFramework()
        self.performance_monitor = PerformanceMonitor()
        self.results = {}

    async def run_comprehensive_benchmarks(
        self, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks"""
        logger.info("Starting comprehensive performance benchmarks")

        results = {
            "benchmarks": None,
            "optimizations": None,
            "monitoring": None,
            "validation": None,
            "summary": {},
        }

        start_time = time.time()

        try:
            # Run performance benchmarks if requested
            if options.get("run_benchmarks", True):
                logger.info("Running performance benchmarks...")
                benchmark_results = (
                    await self.performance_framework.run_comprehensive_benchmarks()
                )
                results["benchmarks"] = benchmark_results

                # Validate performance
                validation_results = (
                    await self.performance_framework.validate_performance(
                        benchmark_results
                    )
                )
                results["validation"] = validation_results

            # Run performance optimizations if requested
            if options.get("run_optimizations", True):
                logger.info("Running performance optimizations...")
                optimization_results = []

                for component in ["cpython", "codon", "hybrid"]:
                    component_optimizations = (
                        await self.performance_framework.optimize_performance(component)
                    )
                    optimization_results.extend(component_optimizations)

                results["optimizations"] = optimization_results

            # Run performance monitoring if requested
            if options.get("run_monitoring", True):
                logger.info("Running performance monitoring...")
                monitoring_results = await self._run_performance_monitoring()
                results["monitoring"] = monitoring_results

            # Generate summary
            duration = time.time() - start_time
            results["summary"] = self._generate_summary(results, duration)

            logger.info(
                f"Comprehensive performance benchmarks completed in {duration:.2f} seconds"
            )

        except Exception as e:
            logger.error(f"Performance benchmarking failed: {e}")
            results["error"] = str(e)

        return results

    async def run_benchmarks_only(self) -> Dict[str, Any]:
        """Run only performance benchmarks"""
        logger.info("Running performance benchmarks only")

        results = await self.performance_framework.run_comprehensive_benchmarks()
        validation = await self.performance_framework.validate_performance(results)

        return {
            "benchmarks": results,
            "validation": validation,
            "summary": self._generate_benchmark_summary(results, validation),
        }

    async def run_optimizations_only(self) -> Dict[str, Any]:
        """Run only performance optimizations"""
        logger.info("Running performance optimizations only")

        all_optimizations = []

        for component in ["cpython", "codon", "hybrid"]:
            component_optimizations = (
                await self.performance_framework.optimize_performance(component)
            )
            all_optimizations.extend(component_optimizations)

        return {
            "optimizations": all_optimizations,
            "summary": self._generate_optimization_summary(all_optimizations),
        }

    async def run_monitoring_only(self) -> Dict[str, Any]:
        """Run only performance monitoring"""
        logger.info("Running performance monitoring only")

        return await self._run_performance_monitoring()

    async def _run_performance_monitoring(self) -> Dict[str, Any]:
        """Run performance monitoring"""
        try:
            # Start monitoring
            await self.performance_monitor.start_monitoring()

            # Let it run for a few seconds to collect data
            await asyncio.sleep(5)

            # Get current status
            status = await self.performance_monitor.get_current_status()

            # Generate performance report
            report = await self.performance_monitor.generate_performance_report()

            # Get alert history
            alert_history = await self.performance_monitor.get_alert_history()

            # Stop monitoring
            await self.performance_monitor.stop_monitoring()

            return {
                "status": status,
                "report": report,
                "alert_history": [asdict(alert) for alert in alert_history],
            }

        except Exception as e:
            logger.error(f"Performance monitoring failed: {e}")
            return {"error": str(e)}

    def _generate_summary(
        self, results: Dict[str, Any], duration: float
    ) -> Dict[str, Any]:
        """Generate comprehensive summary"""
        summary = {
            "total_duration": duration,
            "benchmarks_run": False,
            "optimizations_run": False,
            "monitoring_run": False,
            "validation_passed": False,
            "total_benchmarks": 0,
            "successful_benchmarks": 0,
            "failed_benchmarks": 0,
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "failed_optimizations": 0,
            "active_alerts": 0,
            "performance_score": 0.0,
        }

        # Analyze benchmark results
        if results.get("benchmarks"):
            benchmarks = results["benchmarks"]
            summary["benchmarks_run"] = True
            summary["total_benchmarks"] = len(benchmarks)
            summary["successful_benchmarks"] = len([b for b in benchmarks if b.success])
            summary["failed_benchmarks"] = (
                summary["total_benchmarks"] - summary["successful_benchmarks"]
            )

        # Analyze optimization results
        if results.get("optimizations"):
            optimizations = results["optimizations"]
            summary["optimizations_run"] = True
            summary["total_optimizations"] = len(optimizations)
            summary["successful_optimizations"] = len(
                [o for o in optimizations if o.success]
            )
            summary["failed_optimizations"] = (
                summary["total_optimizations"] - summary["successful_optimizations"]
            )

        # Analyze monitoring results
        if results.get("monitoring"):
            monitoring = results["monitoring"]
            summary["monitoring_run"] = True
            if "status" in monitoring:
                summary["active_alerts"] = monitoring["status"].get("active_alerts", 0)

        # Analyze validation results
        if results.get("validation"):
            validation = results["validation"]
            summary["validation_passed"] = validation.get("passed_benchmarks", 0) > 0

        # Calculate performance score
        if summary["total_benchmarks"] > 0:
            benchmark_success_rate = (
                summary["successful_benchmarks"] / summary["total_benchmarks"]
            )
            optimization_success_rate = (
                summary["successful_optimizations"] / summary["total_optimizations"]
                if summary["total_optimizations"] > 0
                else 1.0
            )
            alert_score = max(
                0, 1 - (summary["active_alerts"] / 10)
            )  # Reduce score for each alert

            summary["performance_score"] = (
                benchmark_success_rate * 0.4
                + optimization_success_rate * 0.3
                + alert_score * 0.3
            )

        return summary

    def _generate_benchmark_summary(
        self, benchmarks: List[Any], validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate benchmark summary"""
        total_benchmarks = len(benchmarks)
        successful_benchmarks = len([b for b in benchmarks if b.success])
        failed_benchmarks = total_benchmarks - successful_benchmarks

        # Calculate average performance metrics
        successful_benchmarks_list = [b for b in benchmarks if b.success]
        avg_latency = (
            sum(b.mean_time_ms for b in successful_benchmarks_list)
            / len(successful_benchmarks_list)
            if successful_benchmarks_list
            else 0
        )
        avg_throughput = (
            sum(b.throughput_ops_per_sec for b in successful_benchmarks_list)
            / len(successful_benchmarks_list)
            if successful_benchmarks_list
            else 0
        )
        avg_memory = (
            sum(b.memory_average_mb for b in successful_benchmarks_list)
            / len(successful_benchmarks_list)
            if successful_benchmarks_list
            else 0
        )

        return {
            "total_benchmarks": total_benchmarks,
            "successful_benchmarks": successful_benchmarks,
            "failed_benchmarks": failed_benchmarks,
            "success_rate": (
                (successful_benchmarks / total_benchmarks) * 100
                if total_benchmarks > 0
                else 0
            ),
            "avg_latency_ms": avg_latency,
            "avg_throughput_ops_per_sec": avg_throughput,
            "avg_memory_mb": avg_memory,
            "validation_passed": validation.get("passed_benchmarks", 0),
            "validation_failed": validation.get("failed_benchmarks", 0),
        }

    def _generate_optimization_summary(
        self, optimizations: List[Any]
    ) -> Dict[str, Any]:
        """Generate optimization summary"""
        total_optimizations = len(optimizations)
        successful_optimizations = len([o for o in optimizations if o.success])
        failed_optimizations = total_optimizations - successful_optimizations

        # Calculate average improvement
        successful_optimizations_list = [o for o in optimizations if o.success]
        avg_improvement = (
            sum(o.improvement_percent for o in successful_optimizations_list)
            / len(successful_optimizations_list)
            if successful_optimizations_list
            else 0
        )

        return {
            "total_optimizations": total_optimizations,
            "successful_optimizations": successful_optimizations,
            "failed_optimizations": failed_optimizations,
            "success_rate": (
                (successful_optimizations / total_optimizations) * 100
                if total_optimizations > 0
                else 0
            ),
            "avg_improvement_percent": avg_improvement,
        }

    def print_results(self, results: Dict[str, Any]) -> None:
        """Print performance results in a formatted way"""
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARKING RESULTS")
        print("=" * 60)

        if "error" in results:
            print(f"❌ ERROR: {results['error']}")
            return

        summary = results.get("summary", {})

        print(f"⏱️  Total Duration: {summary.get('total_duration', 0):.2f}s")
        print(f"📊 Performance Score: {summary.get('performance_score', 0):.2f}%")

        print("\n📋 Benchmark Results:")
        if results.get("benchmarks"):
            benchmark_summary = self._generate_benchmark_summary(
                results["benchmarks"], results.get("validation", {})
            )
            print(
                f"  ✅ Successful: {benchmark_summary['successful_benchmarks']}/{benchmark_summary['total_benchmarks']}"
            )
            print(f"  ❌ Failed: {benchmark_summary['failed_benchmarks']}")
            print(f"  📈 Success Rate: {benchmark_summary['success_rate']:.1f}%")
            print(f"  ⏱️  Avg Latency: {benchmark_summary['avg_latency_ms']:.2f}ms")
            print(
                f"  🚀 Avg Throughput: {benchmark_summary['avg_throughput_ops_per_sec']:.0f} ops/sec"
            )
            print(f"  💾 Avg Memory: {benchmark_summary['avg_memory_mb']:.2f} MB")
        else:
            print("  ⏭️  Skipped")

        print("\n🔧 Optimization Results:")
        if results.get("optimizations"):
            optimization_summary = self._generate_optimization_summary(
                results["optimizations"]
            )
            print(
                f"  ✅ Successful: {optimization_summary['successful_optimizations']}/{optimization_summary['total_optimizations']}"
            )
            print(f"  ❌ Failed: {optimization_summary['failed_optimizations']}")
            print(f"  📈 Success Rate: {optimization_summary['success_rate']:.1f}%")
            print(
                f"  🚀 Avg Improvement: {optimization_summary['avg_improvement_percent']:.1f}%"
            )
        else:
            print("  ⏭️  Skipped")

        print("\n📊 Monitoring Results:")
        if results.get("monitoring"):
            monitoring = results["monitoring"]
            if "status" in monitoring:
                status = monitoring["status"]
                print(f"  📊 Metrics Collected: {status.get('metrics_collected', 0)}")
                print(f"  ⚠️  Active Alerts: {status.get('active_alerts', 0)}")
                print(f"  🔔 Recent Alerts: {status.get('recent_alerts', 0)}")
                print(
                    f"  🎯 Components Monitored: {', '.join(status.get('components_monitored', []))}"
                )
        else:
            print("  ⏭️  Skipped")

        print("\n🎯 Quality Gates:")
        validation_passed = "✅" if summary.get("validation_passed", False) else "❌"
        benchmarks_run = "✅" if summary.get("benchmarks_run", False) else "❌"
        optimizations_run = "✅" if summary.get("optimizations_run", False) else "❌"
        monitoring_run = "✅" if summary.get("monitoring_run", False) else "❌"

        print(f"  {validation_passed} Performance Validation Passed")
        print(f"  {benchmarks_run} Benchmarks Executed")
        print(f"  {optimizations_run} Optimizations Applied")
        print(f"  {monitoring_run} Monitoring Active")

        print("\n" + "=" * 60)

        # Overall success
        performance_score = summary.get("performance_score", 0)
        if performance_score >= 80:
            print("🎉 EXCELLENT PERFORMANCE")
        elif performance_score >= 60:
            print("✅ GOOD PERFORMANCE")
        elif performance_score >= 40:
            print("⚠️  ACCEPTABLE PERFORMANCE")
        else:
            print("❌ POOR PERFORMANCE - IMMEDIATE ATTENTION REQUIRED")

        print("=" * 60 + "\n")


def main():
    """Main entry point for the performance benchmark runner"""
    parser = argparse.ArgumentParser(
        description="Performance Benchmarking Runner for Hybrid Architecture"
    )

    parser.add_argument(
        "--mode",
        choices=["comprehensive", "benchmarks", "optimizations", "monitoring"],
        default="comprehensive",
        help="Performance testing mode",
    )

    parser.add_argument(
        "--skip-benchmarks", action="store_true", help="Skip performance benchmarks"
    )

    parser.add_argument(
        "--skip-optimizations",
        action="store_true",
        help="Skip performance optimizations",
    )

    parser.add_argument(
        "--skip-monitoring", action="store_true", help="Skip performance monitoring"
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

    # Create benchmark runner
    runner = PerformanceBenchmarkRunner()

    # Determine options based on mode and flags
    options = {
        "run_benchmarks": not args.skip_benchmarks,
        "run_optimizations": not args.skip_optimizations,
        "run_monitoring": not args.skip_monitoring,
    }

    async def run_benchmarks():
        """Run benchmarks based on command line arguments"""
        if args.mode == "comprehensive":
            results = await runner.run_comprehensive_benchmarks(options)
        elif args.mode == "benchmarks":
            results = await runner.run_benchmarks_only()
        elif args.mode == "optimizations":
            results = await runner.run_optimizations_only()
        elif args.mode == "monitoring":
            results = await runner.run_monitoring_only()
        else:
            print(f"Unknown mode: {args.mode}")
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
        failed_benchmarks = summary.get("failed_benchmarks", 0)
        failed_optimizations = summary.get("failed_optimizations", 0)
        performance_score = summary.get("performance_score", 0)

        # Exit with error if performance is poor or there are failures
        if performance_score < 40 or (
            failed_benchmarks > 0 and failed_optimizations > 0
        ):
            sys.exit(1)
        else:
            sys.exit(0)

    # Run the benchmarks
    asyncio.run(run_benchmarks())


if __name__ == "__main__":
    main()
