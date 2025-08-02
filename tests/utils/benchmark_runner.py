"""
Performance Comparison Utilities for Codon vs CPython Benchmarking

This module provides utilities for performance benchmarking, baseline data storage,
and regression detection for Codon vs CPython comparisons.
"""

import asyncio
import gc
import json
import logging
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import psutil

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of performance benchmarks"""

    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    THROUGHPUT = "throughput"
    LATENCY = "latency"


class ImplementationType(Enum):
    """Types of implementations to benchmark"""

    CPYTHON = "cpython"
    CONDON = "codon"


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark"""

    benchmark_name: str
    implementation: ImplementationType
    benchmark_type: BenchmarkType
    execution_time: float
    memory_usage: float
    cpu_usage: float
    throughput: Optional[float] = None
    latency: Optional[float] = None
    iterations: int = 1
    warmup_runs: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BaselineData:
    """Baseline performance data for comparison"""

    benchmark_name: str
    implementation: ImplementationType
    mean_execution_time: float
    std_execution_time: float
    mean_memory_usage: float
    std_memory_usage: float
    mean_cpu_usage: float
    std_cpu_usage: float
    sample_count: int
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmarker:
    """Performance benchmarking utilities for Codon vs CPython comparisons"""

    def __init__(self, baseline_dir: str = "tests/performance/baselines"):
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[BenchmarkResult] = []

    async def benchmark_function(
        self,
        func: Callable,
        benchmark_name: str,
        implementation: ImplementationType,
        iterations: int = 10,
        warmup_runs: int = 3,
        **kwargs,
    ) -> BenchmarkResult:
        """Benchmark a function with proper warmup and multiple iterations"""

        # Warmup runs
        for _ in range(warmup_runs):
            try:
                (
                    await func(**kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(**kwargs)
                )
            except Exception as e:
                logger.warning(f"Warmup run failed: {e}")

        # Force garbage collection before benchmarking
        gc.collect()

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Benchmark runs
        execution_times = []
        memory_usages = []
        cpu_usages = []

        for i in range(iterations):
            # Start CPU monitoring
            cpu_percent_start = process.cpu_percent()

            # Time the execution
            start_time = time.perf_counter()
            try:
                result = (
                    await func(**kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(**kwargs)
                )
            except Exception as e:
                logger.error(f"Benchmark iteration {i} failed: {e}")
                continue
            end_time = time.perf_counter()

            # End CPU monitoring
            cpu_percent_end = process.cpu_percent()

            # Calculate metrics
            execution_time = end_time - start_time
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_usage = current_memory - initial_memory
            cpu_usage = (cpu_percent_start + cpu_percent_end) / 2

            execution_times.append(execution_time)
            memory_usages.append(memory_usage)
            cpu_usages.append(cpu_usage)

            # Small delay between iterations
            await asyncio.sleep(0.01)

        # Calculate averages
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        avg_memory_usage = statistics.mean(memory_usages) if memory_usages else 0
        avg_cpu_usage = statistics.mean(cpu_usages) if cpu_usages else 0

        return BenchmarkResult(
            benchmark_name=benchmark_name,
            implementation=implementation,
            benchmark_type=BenchmarkType.EXECUTION_TIME,
            execution_time=avg_execution_time,
            memory_usage=avg_memory_usage,
            cpu_usage=avg_cpu_usage,
            iterations=iterations,
            warmup_runs=warmup_runs,
            metadata={
                "execution_times": execution_times,
                "memory_usages": memory_usages,
                "cpu_usages": cpu_usages,
                "std_execution_time": (
                    statistics.stdev(execution_times) if len(execution_times) > 1 else 0
                ),
                "std_memory_usage": (
                    statistics.stdev(memory_usages) if len(memory_usages) > 1 else 0
                ),
                "std_cpu_usage": (
                    statistics.stdev(cpu_usages) if len(cpu_usages) > 1 else 0
                ),
            },
        )

    async def benchmark_throughput(
        self,
        func: Callable,
        benchmark_name: str,
        implementation: ImplementationType,
        data_size: int,
        time_limit: float = 10.0,
        **kwargs,
    ) -> BenchmarkResult:
        """Benchmark throughput (operations per second)"""

        # Warmup
        for _ in range(3):
            try:
                (
                    await func(**kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(**kwargs)
                )
            except Exception as e:
                logger.warning(f"Throughput warmup failed: {e}")

        gc.collect()

        # Measure throughput
        start_time = time.perf_counter()
        operations = 0

        while time.perf_counter() - start_time < time_limit:
            try:
                (
                    await func(**kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(**kwargs)
                )
                operations += 1
            except Exception as e:
                logger.error(f"Throughput benchmark failed: {e}")
                break

        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = operations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            benchmark_name=benchmark_name,
            implementation=implementation,
            benchmark_type=BenchmarkType.THROUGHPUT,
            execution_time=total_time,
            memory_usage=0,  # Will be calculated separately if needed
            cpu_usage=0,  # Will be calculated separately if needed
            throughput=throughput,
            metadata={"operations": operations, "data_size": data_size},
        )


class BaselineManager:
    """Manages baseline performance data storage and retrieval"""

    def __init__(self, baseline_dir: str = "tests/performance/baselines"):
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    def save_baseline(self, baseline: BaselineData) -> None:
        """Save baseline data to file"""
        filename = f"{baseline.benchmark_name}_{baseline.implementation.value}.json"
        filepath = self.baseline_dir / filename

        baseline_dict = {
            "benchmark_name": baseline.benchmark_name,
            "implementation": baseline.implementation.value,
            "mean_execution_time": baseline.mean_execution_time,
            "std_execution_time": baseline.std_execution_time,
            "mean_memory_usage": baseline.mean_memory_usage,
            "std_memory_usage": baseline.std_memory_usage,
            "mean_cpu_usage": baseline.mean_cpu_usage,
            "std_cpu_usage": baseline.std_cpu_usage,
            "sample_count": baseline.sample_count,
            "created_at": baseline.created_at.isoformat(),
            "metadata": baseline.metadata,
        }

        with open(filepath, "w") as f:
            json.dump(baseline_dict, f, indent=2)

        logger.info(
            f"Saved baseline for {baseline.benchmark_name} ({baseline.implementation.value})"
        )

    def load_baseline(
        self, benchmark_name: str, implementation: ImplementationType
    ) -> Optional[BaselineData]:
        """Load baseline data from file"""
        filename = f"{benchmark_name}_{implementation.value}.json"
        filepath = self.baseline_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            return BaselineData(
                benchmark_name=data["benchmark_name"],
                implementation=ImplementationType(data["implementation"]),
                mean_execution_time=data["mean_execution_time"],
                std_execution_time=data["std_execution_time"],
                mean_memory_usage=data["mean_memory_usage"],
                std_memory_usage=data["std_memory_usage"],
                mean_cpu_usage=data["mean_cpu_usage"],
                std_cpu_usage=data["std_cpu_usage"],
                sample_count=data["sample_count"],
                created_at=datetime.fromisoformat(data["created_at"]),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Failed to load baseline {filename}: {e}")
            return None

    def create_baseline_from_results(
        self, results: List[BenchmarkResult]
    ) -> BaselineData:
        """Create baseline data from benchmark results"""
        if not results:
            raise ValueError("No results provided for baseline creation")

        # Group results by benchmark name and implementation
        benchmark_name = results[0].benchmark_name
        implementation = results[0].implementation

        execution_times = [r.execution_time for r in results]
        memory_usages = [r.memory_usage for r in results]
        cpu_usages = [r.cpu_usage for r in results]

        return BaselineData(
            benchmark_name=benchmark_name,
            implementation=implementation,
            mean_execution_time=statistics.mean(execution_times),
            std_execution_time=(
                statistics.stdev(execution_times) if len(execution_times) > 1 else 0
            ),
            mean_memory_usage=statistics.mean(memory_usages),
            std_memory_usage=(
                statistics.stdev(memory_usages) if len(memory_usages) > 1 else 0
            ),
            mean_cpu_usage=statistics.mean(cpu_usages),
            std_cpu_usage=statistics.stdev(cpu_usages) if len(cpu_usages) > 1 else 0,
            sample_count=len(results),
            created_at=datetime.now(),
        )


class RegressionDetector:
    """Detects performance regressions by comparing current results to baselines"""

    def __init__(self, baseline_manager: BaselineManager):
        self.baseline_manager = baseline_manager
        self.regression_threshold = 0.05  # 5% regression threshold

    def detect_regression(
        self, current_result: BenchmarkResult, baseline: BaselineData
    ) -> Dict[str, Any]:
        """Detect performance regression by comparing current result to baseline"""

        # Calculate percentage changes
        execution_time_change = (
            current_result.execution_time - baseline.mean_execution_time
        ) / baseline.mean_execution_time
        memory_usage_change = (
            (current_result.memory_usage - baseline.mean_memory_usage)
            / baseline.mean_memory_usage
            if baseline.mean_memory_usage > 0
            else 0
        )
        cpu_usage_change = (
            (current_result.cpu_usage - baseline.mean_cpu_usage)
            / baseline.mean_cpu_usage
            if baseline.mean_cpu_usage > 0
            else 0
        )

        # Check for regressions (worse performance)
        execution_regression = execution_time_change > self.regression_threshold
        memory_regression = memory_usage_change > self.regression_threshold
        cpu_regression = cpu_usage_change > self.regression_threshold

        # Check for improvements (better performance)
        execution_improvement = execution_time_change < -self.regression_threshold
        memory_improvement = memory_usage_change < -self.regression_threshold
        cpu_improvement = cpu_usage_change < -self.regression_threshold

        return {
            "regression_detected": execution_regression
            or memory_regression
            or cpu_regression,
            "improvement_detected": execution_improvement
            or memory_improvement
            or cpu_improvement,
            "execution_time": {
                "change_percent": execution_time_change * 100,
                "regression": execution_regression,
                "improvement": execution_improvement,
            },
            "memory_usage": {
                "change_percent": memory_usage_change * 100,
                "regression": memory_regression,
                "improvement": memory_improvement,
            },
            "cpu_usage": {
                "change_percent": cpu_usage_change * 100,
                "regression": cpu_regression,
                "improvement": cpu_improvement,
            },
            "current_result": current_result,
            "baseline": baseline,
        }


class PerformanceReporter:
    """Generates performance reports and visualizations"""

    def __init__(self, output_dir: str = "tests/performance/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_comparison_report(
        self,
        cpython_results: List[BenchmarkResult],
        codon_results: List[BenchmarkResult],
    ) -> Dict[str, Any]:
        """Generate a comparison report between CPython and Codon results"""

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "detailed_comparisons": [],
            "recommendations": [],
        }

        # Group results by benchmark name
        cpython_by_name = {}
        codon_by_name = {}

        for result in cpython_results:
            if result.benchmark_name not in cpython_by_name:
                cpython_by_name[result.benchmark_name] = []
            cpython_by_name[result.benchmark_name].append(result)

        for result in codon_results:
            if result.benchmark_name not in codon_by_name:
                codon_by_name[result.benchmark_name] = []
            codon_by_name[result.benchmark_name].append(result)

        # Compare each benchmark
        for benchmark_name in set(cpython_by_name.keys()) | set(codon_by_name.keys()):
            cpython_avg = self._calculate_average_result(
                cpython_by_name.get(benchmark_name, [])
            )
            codon_avg = self._calculate_average_result(
                codon_by_name.get(benchmark_name, [])
            )

            if cpython_avg and codon_avg:
                comparison = self._compare_results(cpython_avg, codon_avg)
                report["detailed_comparisons"].append(comparison)

        # Generate summary
        report["summary"] = self._generate_summary(report["detailed_comparisons"])

        return report

    def _calculate_average_result(
        self, results: List[BenchmarkResult]
    ) -> Optional[BenchmarkResult]:
        """Calculate average result from multiple benchmark runs"""
        if not results:
            return None

        avg_execution_time = statistics.mean([r.execution_time for r in results])
        avg_memory_usage = statistics.mean([r.memory_usage for r in results])
        avg_cpu_usage = statistics.mean([r.cpu_usage for r in results])

        return BenchmarkResult(
            benchmark_name=results[0].benchmark_name,
            implementation=results[0].implementation,
            benchmark_type=results[0].benchmark_type,
            execution_time=avg_execution_time,
            memory_usage=avg_memory_usage,
            cpu_usage=avg_cpu_usage,
            metadata={"sample_count": len(results)},
        )

    def _compare_results(
        self, cpython_result: BenchmarkResult, codon_result: BenchmarkResult
    ) -> Dict[str, Any]:
        """Compare CPython and Codon results"""

        # Calculate performance ratios
        execution_ratio = codon_result.execution_time / cpython_result.execution_time
        memory_ratio = (
            codon_result.memory_usage / cpython_result.memory_usage
            if cpython_result.memory_usage > 0
            else 1
        )
        cpu_ratio = (
            codon_result.cpu_usage / cpython_result.cpu_usage
            if cpython_result.cpu_usage > 0
            else 1
        )

        return {
            "benchmark_name": cpython_result.benchmark_name,
            "cpython": {
                "execution_time": cpython_result.execution_time,
                "memory_usage": cpython_result.memory_usage,
                "cpu_usage": cpython_result.cpu_usage,
            },
            "codon": {
                "execution_time": codon_result.execution_time,
                "memory_usage": codon_result.memory_usage,
                "cpu_usage": codon_result.cpu_usage,
            },
            "ratios": {
                "execution_time": execution_ratio,
                "memory_usage": memory_ratio,
                "cpu_usage": cpu_ratio,
            },
            "performance_analysis": {
                "codon_faster": execution_ratio < 1,
                "codon_more_memory_efficient": memory_ratio < 1,
                "codon_more_cpu_efficient": cpu_ratio < 1,
            },
        }

    def _generate_summary(self, comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from comparisons"""

        if not comparisons:
            return {}

        execution_ratios = [c["ratios"]["execution_time"] for c in comparisons]
        memory_ratios = [c["ratios"]["memory_usage"] for c in comparisons]
        cpu_ratios = [c["ratios"]["cpu_usage"] for c in comparisons]

        codon_faster_count = sum(
            1 for c in comparisons if c["performance_analysis"]["codon_faster"]
        )
        codon_memory_efficient_count = sum(
            1
            for c in comparisons
            if c["performance_analysis"]["codon_more_memory_efficient"]
        )
        codon_cpu_efficient_count = sum(
            1
            for c in comparisons
            if c["performance_analysis"]["codon_more_cpu_efficient"]
        )

        return {
            "total_benchmarks": len(comparisons),
            "codon_faster_benchmarks": codon_faster_count,
            "codon_memory_efficient_benchmarks": codon_memory_efficient_count,
            "codon_cpu_efficient_benchmarks": codon_cpu_efficient_count,
            "average_execution_ratio": statistics.mean(execution_ratios),
            "average_memory_ratio": statistics.mean(memory_ratios),
            "average_cpu_ratio": statistics.mean(cpu_ratios),
        }

    def save_report(self, report: Dict[str, Any], filename: str) -> None:
        """Save performance report to file"""
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Saved performance report to {filepath}")


# Convenience functions
def get_performance_benchmarker() -> PerformanceBenchmarker:
    """Get the performance benchmarker instance"""
    return PerformanceBenchmarker()


def get_baseline_manager() -> BaselineManager:
    """Get the baseline manager instance"""
    return BaselineManager()


def get_regression_detector() -> RegressionDetector:
    """Get the regression detector instance"""
    baseline_manager = get_baseline_manager()
    return RegressionDetector(baseline_manager)


def get_performance_reporter() -> PerformanceReporter:
    """Get the performance reporter instance"""
    return PerformanceReporter()
