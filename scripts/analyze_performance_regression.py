#!/usr/bin/env python3
"""
Performance Regression Analyzer

This script analyzes performance test results and detects regressions
for CI/CD pipeline integration.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_performance_metrics(metrics_file: str) -> Dict[str, Any]:
    """Load performance metrics from JSON file"""

    try:
        with open(metrics_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading metrics file {metrics_file}: {e}", file=sys.stderr)
        return {}


def load_baseline_metrics(baseline_file: str) -> Dict[str, Any]:
    """Load baseline performance metrics"""

    try:
        with open(baseline_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading baseline file {baseline_file}: {e}", file=sys.stderr)
        return {}


def analyze_performance_regression(
    current_metrics: Dict[str, Any],
    baseline_metrics: Dict[str, Any],
    threshold: float = 0.15,
) -> Dict[str, Any]:
    """Analyze performance regression between current and baseline metrics"""

    analysis = {
        "regressions_detected": [],
        "improvements_detected": [],
        "overall_status": "PASS",
        "regression_count": 0,
        "improvement_count": 0,
        "metrics_compared": 0,
        "analysis_timestamp": datetime.now().isoformat(),
    }

    # Compare response times
    if "response_times" in current_metrics and "response_times" in baseline_metrics:
        current_rt = current_metrics["response_times"]
        baseline_rt = baseline_metrics["response_times"]

        for endpoint, current_time in current_rt.items():
            if endpoint in baseline_rt:
                baseline_time = baseline_rt[endpoint]
                change_percentage = (current_time - baseline_time) / baseline_time

                analysis["metrics_compared"] += 1

                if change_percentage > threshold:
                    # Performance regression detected
                    regression_info = {
                        "metric": "response_time",
                        "endpoint": endpoint,
                        "current_value": current_time,
                        "baseline_value": baseline_time,
                        "change_percentage": change_percentage,
                        "severity": "HIGH" if change_percentage > 0.5 else "MEDIUM",
                    }
                    analysis["regressions_detected"].append(regression_info)
                    analysis["regression_count"] += 1
                elif change_percentage < -threshold:
                    # Performance improvement detected
                    improvement_info = {
                        "metric": "response_time",
                        "endpoint": endpoint,
                        "current_value": current_time,
                        "baseline_value": baseline_time,
                        "change_percentage": change_percentage,
                    }
                    analysis["improvements_detected"].append(improvement_info)
                    analysis["improvement_count"] += 1

    # Compare throughput
    if "throughput" in current_metrics and "throughput" in baseline_metrics:
        current_tp = current_metrics["throughput"]
        baseline_tp = baseline_metrics["throughput"]

        for endpoint, current_rate in current_tp.items():
            if endpoint in baseline_tp:
                baseline_rate = baseline_tp[endpoint]
                change_percentage = (baseline_rate - current_rate) / baseline_rate

                analysis["metrics_compared"] += 1

                if change_percentage > threshold:
                    # Throughput regression detected
                    regression_info = {
                        "metric": "throughput",
                        "endpoint": endpoint,
                        "current_value": current_rate,
                        "baseline_value": baseline_rate,
                        "change_percentage": change_percentage,
                        "severity": "HIGH" if change_percentage > 0.5 else "MEDIUM",
                    }
                    analysis["regressions_detected"].append(regression_info)
                    analysis["regression_count"] += 1
                elif change_percentage < -threshold:
                    # Throughput improvement detected
                    improvement_info = {
                        "metric": "throughput",
                        "endpoint": endpoint,
                        "current_value": current_rate,
                        "baseline_value": baseline_rate,
                        "change_percentage": change_percentage,
                    }
                    analysis["improvements_detected"].append(improvement_info)
                    analysis["improvement_count"] += 1

    # Compare error rates
    if "error_rates" in current_metrics and "error_rates" in baseline_metrics:
        current_er = current_metrics["error_rates"]
        baseline_er = baseline_metrics["error_rates"]

        for endpoint, current_rate in current_er.items():
            if endpoint in baseline_er:
                baseline_rate = baseline_er[endpoint]
                change_percentage = (current_rate - baseline_rate) / max(
                    baseline_rate, 0.001
                )

                analysis["metrics_compared"] += 1

                if change_percentage > threshold:
                    # Error rate regression detected
                    regression_info = {
                        "metric": "error_rate",
                        "endpoint": endpoint,
                        "current_value": current_rate,
                        "baseline_value": baseline_rate,
                        "change_percentage": change_percentage,
                        "severity": "HIGH" if change_percentage > 0.5 else "MEDIUM",
                    }
                    analysis["regressions_detected"].append(regression_info)
                    analysis["regression_count"] += 1

    # Determine overall status
    if analysis["regression_count"] > 0:
        analysis["overall_status"] = "FAIL"

    return analysis


def generate_performance_report(
    metrics_file: str, baseline_file: str, output_file: str, threshold: float = 0.15
):
    """Generate a comprehensive performance regression report"""

    # Load metrics
    current_metrics = load_performance_metrics(metrics_file)
    baseline_metrics = load_baseline_metrics(baseline_file)

    if not current_metrics:
        print("Error: Could not load current metrics", file=sys.stderr)
        sys.exit(1)

    if not baseline_metrics:
        print(
            "Warning: Could not load baseline metrics, creating empty baseline",
            file=sys.stderr,
        )
        baseline_metrics = {}

    # Analyze performance regression
    analysis = analyze_performance_regression(
        current_metrics, baseline_metrics, threshold
    )

    # Add metadata
    analysis["metrics_file"] = metrics_file
    analysis["baseline_file"] = baseline_file
    analysis["threshold"] = threshold

    # Write analysis to JSON file
    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"Performance analysis generated: {output_file}")
    print(f"Overall status: {analysis['overall_status']}")
    print(f"Metrics compared: {analysis['metrics_compared']}")
    print(f"Regressions detected: {analysis['regression_count']}")
    print(f"Improvements detected: {analysis['improvement_count']}")

    if analysis["regressions_detected"]:
        print("\nPerformance regressions:")
        for regression in analysis["regressions_detected"]:
            print(
                f"  - {regression['metric']} for {regression['endpoint']}: "
                f"{regression['change_percentage']:.1%} change "
                f"({regression['severity']} severity)"
            )


def main():
    """Main function"""
    if len(sys.argv) != 4:
        print(
            "Usage: python analyze_performance_regression.py <metrics_file> <baseline_file> <output_file>"
        )
        sys.exit(1)

    metrics_file = sys.argv[1]
    baseline_file = sys.argv[2]
    output_file = sys.argv[3]

    if not Path(metrics_file).exists():
        print(f"Error: Metrics file {metrics_file} does not exist", file=sys.stderr)
        sys.exit(1)

    generate_performance_report(metrics_file, baseline_file, output_file)


if __name__ == "__main__":
    main()
