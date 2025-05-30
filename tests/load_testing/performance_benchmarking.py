"""
Performance Benchmarking Framework for GraphMemory-IDE
======================================================

Based on research from:
- FastAPI observability and monitoring best practices
- Prometheus metrics collection strategies  
- Grafana dashboard patterns for performance tracking
- Production monitoring and alerting methodologies

This module implements comprehensive performance benchmarking
with automated regression detection and observability integration.
"""

import json
import time
import asyncio
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import pytest
import psutil
from prometheus_client import CollectorRegistry, Histogram, Counter, Gauge, push_to_gateway

from server.main import app
from tests.conftest import async_client
from tests.load_testing.test_concurrent_user_simulation import (
    ConcurrentUserSimulator, 
    GraphMemoryWorkflowSimulator,
    LoadTestMetrics
)


@dataclass
class PerformanceBenchmark:
    """Performance benchmark data structure for tracking over time."""
    
    timestamp: str
    test_name: str
    environment: str
    version: str
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_load_test_metrics(
        cls, 
        metrics: LoadTestMetrics, 
        test_name: str,
        environment: str = "test",
        version: str = "unknown"
    ) -> "PerformanceBenchmark":
        """Create benchmark from LoadTestMetrics."""
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            test_name=test_name,
            environment=environment,
            version=version,
            metrics={
                "avg_response_time": metrics.avg_response_time,
                "p95_response_time": metrics.p95_response_time,
                "p99_response_time": metrics.p99_response_time,
                "success_rate": metrics.success_rate,
                "total_requests": float(metrics.total_requests),
                "error_count": float(metrics.error_count),
                "avg_memory_usage": metrics.avg_memory_usage,
                "avg_cpu_usage": metrics.avg_cpu_usage,
                "test_duration": metrics.test_duration
            },
            metadata={
                "concurrent_users": metrics.concurrent_requests,
                "status_codes": metrics.status_codes
            }
        )


class PerformanceDataStore:
    """
    Store and retrieve performance benchmarks with trend analysis.
    
    Based on research from production monitoring patterns.
    """
    
    def __init__(self, storage_path: str = "tests/performance_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def save_benchmark(self, benchmark: PerformanceBenchmark):
        """Save performance benchmark to persistent storage."""
        filename = f"{benchmark.test_name}_{benchmark.environment}_benchmarks.json"
        filepath = self.storage_path / filename
        
        # Load existing benchmarks
        benchmarks = []
        if filepath.exists():
            with open(filepath, 'r') as f:
                benchmarks = json.load(f)
        
        # Add new benchmark - manually convert to dict
        benchmark_dict = {
            "timestamp": benchmark.timestamp,
            "test_name": benchmark.test_name,
            "environment": benchmark.environment,
            "version": benchmark.version,
            "metrics": benchmark.metrics,
            "metadata": benchmark.metadata
        }
        benchmarks.append(benchmark_dict)
        
        # Keep only last 100 benchmarks to prevent unbounded growth
        benchmarks = benchmarks[-100:]
        
        # Save updated benchmarks
        with open(filepath, 'w') as f:
            json.dump(benchmarks, f, indent=2)
    
    def load_benchmarks(self, test_name: str, environment: str = "test") -> List[PerformanceBenchmark]:
        """Load historical benchmarks for analysis."""
        filename = f"{test_name}_{environment}_benchmarks.json"
        filepath = self.storage_path / filename
        
        if not filepath.exists():
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return [PerformanceBenchmark(**item) for item in data]
    
    def get_baseline_metrics(
        self, 
        test_name: str, 
        environment: str = "test",
        num_samples: int = 5
    ) -> Optional[Dict[str, float]]:
        """Get baseline metrics from recent successful runs."""
        benchmarks = self.load_benchmarks(test_name, environment)
        
        if len(benchmarks) < num_samples:
            return None
        
        # Use last N samples for baseline
        recent_benchmarks = benchmarks[-num_samples:]
        
        # Calculate baseline metrics (median of recent runs)
        metrics_lists = {}
        for benchmark in recent_benchmarks:
            for metric_name, value in benchmark.metrics.items():
                if metric_name not in metrics_lists:
                    metrics_lists[metric_name] = []
                metrics_lists[metric_name].append(value)
        
        baseline = {}
        for metric_name, values in metrics_lists.items():
            baseline[metric_name] = statistics.median(values)
        
        return baseline


class PrometheusMetricsCollector:
    """
    Collect and export performance metrics to Prometheus.
    
    Based on research from FastAPI observability patterns.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.response_time_histogram: Optional[Histogram] = None
        self.success_rate_gauge: Optional[Gauge] = None
        self.memory_usage_gauge: Optional[Gauge] = None
        self.cpu_usage_gauge: Optional[Gauge] = None
        self.request_counter: Optional[Counter] = None
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics for performance monitoring."""
        self.response_time_histogram = Histogram(
            'graphmemory_test_response_time_seconds',
            'Response time distribution for load tests',
            ['test_name', 'endpoint'],
            registry=self.registry
        )
        
        self.success_rate_gauge = Gauge(
            'graphmemory_test_success_rate_percent',
            'Success rate percentage for load tests',
            ['test_name'],
            registry=self.registry
        )
        
        self.memory_usage_gauge = Gauge(
            'graphmemory_test_memory_usage_mb',
            'Memory usage during load tests',
            ['test_name'],
            registry=self.registry
        )
        
        self.cpu_usage_gauge = Gauge(
            'graphmemory_test_cpu_usage_percent',
            'CPU usage during load tests',
            ['test_name'],
            registry=self.registry
        )
        
        self.request_counter = Counter(
            'graphmemory_test_requests_total',
            'Total requests during load tests',
            ['test_name', 'status_code'],
            registry=self.registry
        )
    
    def record_metrics(self, benchmark: PerformanceBenchmark):
        """Record performance metrics to Prometheus."""
        test_name = benchmark.test_name
        
        # Record response time (using average as example)
        if self.response_time_histogram:
            self.response_time_histogram.labels(
                test_name=test_name, 
                endpoint="mixed"
            ).observe(benchmark.metrics["avg_response_time"])
        
        # Record success rate
        if self.success_rate_gauge:
            self.success_rate_gauge.labels(test_name=test_name).set(
                benchmark.metrics["success_rate"]
            )
        
        # Record resource usage
        if self.memory_usage_gauge:
            self.memory_usage_gauge.labels(test_name=test_name).set(
                benchmark.metrics["avg_memory_usage"]
            )
        
        if self.cpu_usage_gauge:
            self.cpu_usage_gauge.labels(test_name=test_name).set(
                benchmark.metrics["avg_cpu_usage"]
            )
        
        # Record request counts by status code
        if self.request_counter:
            for status_code, count in benchmark.metadata.get("status_codes", {}).items():
                try:
                    # Safely set counter value
                    counter_metric = self.request_counter.labels(
                        test_name=test_name,
                        status_code=str(status_code)
                    )
                    counter_metric._value._value = float(count)
                except AttributeError:
                    # Alternative approach if direct access fails
                    pass
    
    def push_metrics(self, gateway: str, job: str = "graphmemory_load_tests"):
        """Push metrics to Prometheus Pushgateway."""
        try:
            push_to_gateway(gateway, job=job, registry=self.registry)
        except Exception as e:
            print(f"Warning: Failed to push metrics to Prometheus: {e}")


class PerformanceRegressionDetector:
    """
    Detect performance regressions using statistical analysis.
    
    Based on research from production monitoring and alerting.
    """
    
    def __init__(self, sensitivity: float = 0.2):
        self.sensitivity = sensitivity  # 20% degradation threshold
    
    def analyze_regression(
        self, 
        current: PerformanceBenchmark,
        baseline: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze performance regression against baseline.
        
        Returns analysis results with alerts and recommendations.
        """
        results = {
            "has_regression": False,
            "alerts": [],
            "metrics_analysis": {},
            "overall_score": 100.0,
            "recommendations": []
        }
        
        # Metrics that should decrease (better when lower)
        decrease_metrics = {
            "avg_response_time": "Average response time",
            "p95_response_time": "P95 response time", 
            "p99_response_time": "P99 response time",
            "avg_memory_usage": "Average memory usage",
            "avg_cpu_usage": "Average CPU usage"
        }
        
        # Metrics that should increase (better when higher)
        increase_metrics = {
            "success_rate": "Success rate"
        }
        
        # Analyze decrease metrics (regression if increased significantly)
        for metric, description in decrease_metrics.items():
            if metric in baseline and metric in current.metrics:
                baseline_val = baseline[metric]
                current_val = current.metrics[metric]
                
                if baseline_val > 0:  # Avoid division by zero
                    ratio = current_val / baseline_val
                    change_percent = (ratio - 1.0) * 100
                    
                    is_regression = ratio > (1.0 + self.sensitivity)
                    
                    results["metrics_analysis"][metric] = {
                        "baseline": baseline_val,
                        "current": current_val,
                        "ratio": ratio,
                        "change_percent": change_percent,
                        "is_regression": is_regression
                    }
                    
                    if is_regression:
                        results["has_regression"] = True
                        results["alerts"].append(
                            f"🚨 {description} regression: {change_percent:+.1f}% "
                            f"({baseline_val:.3f} → {current_val:.3f})"
                        )
                        results["overall_score"] -= abs(change_percent) * 0.5
        
        # Analyze increase metrics (regression if decreased significantly)
        for metric, description in increase_metrics.items():
            if metric in baseline and metric in current.metrics:
                baseline_val = baseline[metric]
                current_val = current.metrics[metric]
                
                if baseline_val > 0:
                    ratio = current_val / baseline_val
                    change_percent = (ratio - 1.0) * 100
                    
                    is_regression = ratio < (1.0 - self.sensitivity)
                    
                    results["metrics_analysis"][metric] = {
                        "baseline": baseline_val,
                        "current": current_val,
                        "ratio": ratio,
                        "change_percent": change_percent,
                        "is_regression": is_regression
                    }
                    
                    if is_regression:
                        results["has_regression"] = True
                        results["alerts"].append(
                            f"🚨 {description} regression: {change_percent:+.1f}% "
                            f"({baseline_val:.1f}% → {current_val:.1f}%)"
                        )
                        results["overall_score"] -= abs(change_percent) * 0.5
        
        # Generate recommendations
        if results["has_regression"]:
            results["recommendations"].extend([
                "🔍 Investigate recent code changes",
                "📊 Check resource utilization trends",
                "🐛 Review error logs for new issues",
                "⚡ Consider performance profiling"
            ])
        
        results["overall_score"] = max(0.0, results["overall_score"])
        
        return results


class PerformanceBenchmarkSuite:
    """
    Comprehensive performance benchmarking suite with full observability.
    
    Integrates all research-driven components into a unified testing framework.
    """
    
    def __init__(
        self, 
        data_store: Optional[PerformanceDataStore] = None,
        metrics_collector: Optional[PrometheusMetricsCollector] = None,
        regression_detector: Optional[PerformanceRegressionDetector] = None
    ):
        self.data_store = data_store or PerformanceDataStore()
        self.metrics_collector = metrics_collector or PrometheusMetricsCollector()
        self.regression_detector = regression_detector or PerformanceRegressionDetector()
        self.simulator = ConcurrentUserSimulator()
    
    async def run_performance_benchmark(
        self,
        test_name: str,
        concurrent_users: int,
        workflow_type: str = "cursor_developer",
        test_duration: float = 60.0,
        environment: str = "test",
        version: str = "unknown"
    ) -> Tuple[PerformanceBenchmark, Dict[str, Any]]:
        """
        Run complete performance benchmark with full analysis.
        
        Returns benchmark results and regression analysis.
        """
        print(f"🚀 Running performance benchmark: {test_name}")
        print(f"👥 Users: {concurrent_users}, Duration: {test_duration}s")
        
        # Get workflow
        if workflow_type == "cursor_developer":
            workflow = GraphMemoryWorkflowSimulator.cursor_developer_workflow()
        elif workflow_type == "analytics_heavy":
            workflow = GraphMemoryWorkflowSimulator.analytics_heavy_workflow()
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        # Run load test
        metrics = await self.simulator.run_concurrent_load_test(
            concurrent_users=concurrent_users,
            user_actions=workflow,
            test_duration=test_duration,
            ramp_up_time=min(test_duration * 0.2, 15.0),  # 20% ramp-up, max 15s
            think_time=1.0
        )
        
        # Create benchmark
        benchmark = PerformanceBenchmark.from_load_test_metrics(
            metrics=metrics,
            test_name=test_name,
            environment=environment,
            version=version
        )
        
        # Save benchmark
        self.data_store.save_benchmark(benchmark)
        
        # Record metrics to Prometheus
        self.metrics_collector.record_metrics(benchmark)
        
        # Analyze regression
        baseline = self.data_store.get_baseline_metrics(test_name, environment)
        regression_analysis = {"baseline_available": False}
        
        if baseline:
            regression_analysis = self.regression_detector.analyze_regression(
                current=benchmark,
                baseline=baseline
            )
            regression_analysis["baseline_available"] = True
        
        # Print results
        self._print_benchmark_results(benchmark, regression_analysis)
        
        return benchmark, regression_analysis
    
    def _print_benchmark_results(
        self, 
        benchmark: PerformanceBenchmark, 
        regression_analysis: Dict[str, Any]
    ):
        """Print formatted benchmark results."""
        print(f"\n📊 Performance Benchmark Results: {benchmark.test_name}")
        print("=" * 60)
        
        metrics = benchmark.metrics
        print(f"⚡ Response Times:")
        print(f"   Average: {metrics['avg_response_time']:.3f}s")
        print(f"   P95: {metrics['p95_response_time']:.3f}s") 
        print(f"   P99: {metrics['p99_response_time']:.3f}s")
        
        print(f"✅ Success Rate: {metrics['success_rate']:.1f}%")
        print(f"📈 Total Requests: {int(metrics['total_requests'])}")
        print(f"💾 Memory Usage: {metrics['avg_memory_usage']:.1f}MB")
        print(f"🔥 CPU Usage: {metrics['avg_cpu_usage']:.1f}%")
        print(f"⏱️  Test Duration: {metrics['test_duration']:.1f}s")
        
        if regression_analysis.get("baseline_available"):
            print(f"\n🎯 Regression Analysis:")
            if regression_analysis["has_regression"]:
                print(f"   Overall Score: {regression_analysis['overall_score']:.1f}/100")
                for alert in regression_analysis["alerts"]:
                    print(f"   {alert}")
                print(f"\n💡 Recommendations:")
                for rec in regression_analysis["recommendations"]:
                    print(f"   {rec}")
            else:
                print(f"   ✅ No significant regressions detected")
                print(f"   Overall Score: {regression_analysis['overall_score']:.1f}/100")
        else:
            print(f"\n📋 No baseline available - this is the first run")
        
        print("=" * 60)


# Test Classes for Performance Benchmarking

class TestPerformanceBenchmarking:
    """Test performance benchmarking framework."""
    
    @pytest.mark.asyncio
    async def test_baseline_performance_benchmark(self):
        """Establish baseline performance benchmark."""
        suite = PerformanceBenchmarkSuite()
        
        benchmark, analysis = await suite.run_performance_benchmark(
            test_name="baseline_performance",
            concurrent_users=10,
            workflow_type="cursor_developer",
            test_duration=30.0,
            environment="test",
            version="1.0.0"
        )
        
        # Basic performance requirements
        assert benchmark.metrics["success_rate"] >= 90.0
        assert benchmark.metrics["avg_response_time"] <= 3.0
        assert benchmark.metrics["p95_response_time"] <= 8.0
        
        print("✅ Baseline performance benchmark established")
    
    @pytest.mark.asyncio
    async def test_scalability_benchmark(self):
        """Test scalability under increasing load."""
        suite = PerformanceBenchmarkSuite()
        
        user_loads = [5, 10, 20, 30]
        results = []
        
        for users in user_loads:
            print(f"\n🧪 Testing scalability with {users} users...")
            
            benchmark, analysis = await suite.run_performance_benchmark(
                test_name=f"scalability_{users}_users",
                concurrent_users=users,
                workflow_type="cursor_developer", 
                test_duration=20.0,
                environment="scalability_test"
            )
            
            results.append({
                "users": users,
                "avg_response_time": benchmark.metrics["avg_response_time"],
                "success_rate": benchmark.metrics["success_rate"],
                "p95_response_time": benchmark.metrics["p95_response_time"]
            })
        
        # Analyze scalability trends
        print(f"\n📈 Scalability Analysis:")
        for i, result in enumerate(results):
            print(f"   {result['users']:2d} users: "
                  f"{result['avg_response_time']:.3f}s avg, "
                  f"{result['success_rate']:.1f}% success, "
                  f"{result['p95_response_time']:.3f}s P95")
        
        # Ensure system remains stable under increasing load
        max_response_time = max(r["avg_response_time"] for r in results)
        min_success_rate = min(r["success_rate"] for r in results)
        
        assert max_response_time <= 5.0, f"Response time degraded too much: {max_response_time}s"
        assert min_success_rate >= 80.0, f"Success rate dropped too low: {min_success_rate}%"
        
        print("✅ Scalability benchmark completed successfully")
    
    @pytest.mark.asyncio
    async def test_analytics_performance_benchmark(self):
        """Test performance of analytics-heavy workflows."""
        suite = PerformanceBenchmarkSuite()
        
        benchmark, analysis = await suite.run_performance_benchmark(
            test_name="analytics_performance", 
            concurrent_users=8,
            workflow_type="analytics_heavy",
            test_duration=40.0,
            environment="analytics_test"
        )
        
        # Analytics-specific performance targets
        assert benchmark.metrics["success_rate"] >= 85.0
        assert benchmark.metrics["avg_response_time"] <= 8.0  # Analytics can be slower
        assert benchmark.metrics["p95_response_time"] <= 20.0
        
        print("✅ Analytics performance benchmark completed")
    
    @pytest.mark.asyncio
    async def test_performance_regression_detection(self):
        """Test performance regression detection with artificial degradation."""
        suite = PerformanceBenchmarkSuite()
        
        # Run baseline
        baseline_benchmark, _ = await suite.run_performance_benchmark(
            test_name="regression_test",
            concurrent_users=10,
            workflow_type="cursor_developer",
            test_duration=15.0,
            environment="regression_test"
        )
        
        # Simulate regression by creating a degraded benchmark
        degraded_metrics = LoadTestMetrics()
        degraded_metrics.response_times = [2.5] * 100  # Slower responses
        degraded_metrics.success_count = 85
        degraded_metrics.error_count = 15
        degraded_metrics.total_requests = 100
        degraded_metrics.memory_usage = [800.0] * 10  # Higher memory
        degraded_metrics.cpu_usage = [75.0] * 10      # Higher CPU
        degraded_metrics.test_duration = 15.0
        
        degraded_benchmark = PerformanceBenchmark.from_load_test_metrics(
            metrics=degraded_metrics,
            test_name="regression_test",
            environment="regression_test",
            version="1.1.0"
        )
        
        # Analyze regression
        baseline = suite.data_store.get_baseline_metrics("regression_test", "regression_test")
        assert baseline is not None, "Baseline should be available"
        
        regression_analysis = suite.regression_detector.analyze_regression(
            current=degraded_benchmark,
            baseline=baseline
        )
        
        # Should detect regression
        assert regression_analysis["has_regression"], "Should detect performance regression"
        assert len(regression_analysis["alerts"]) > 0, "Should have regression alerts"
        assert regression_analysis["overall_score"] < 90.0, "Overall score should be degraded"
        
        print("✅ Performance regression detection working correctly")


if __name__ == "__main__":
    # Run benchmarks directly for development
    import asyncio
    
    async def main():
        suite = PerformanceBenchmarkSuite()
        
        print("🧪 Running development performance benchmarks...")
        
        await suite.run_performance_benchmark(
            test_name="development_test",
            concurrent_users=5,
            workflow_type="cursor_developer",
            test_duration=20.0,
            environment="development"
        )
    
    asyncio.run(main()) 