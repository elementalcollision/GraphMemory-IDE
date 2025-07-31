"""
Performance Monitoring Framework for Hybrid Architecture

This module provides comprehensive performance monitoring, alerting, and reporting
for the hybrid CPython/Condon architecture, including real-time metrics collection,
performance analysis, and automated alerting.
"""

import asyncio
import datetime
import json
import logging
import statistics
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""

    component: str
    metric_name: str
    value: float
    unit: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AlertRule:
    """Alert rule data structure"""

    name: str
    component: str
    metric_name: str
    threshold: float
    operator: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    severity: str  # 'low', 'medium', 'high', 'critical'
    enabled: bool = True


@dataclass
class Alert:
    """Alert data structure"""

    rule_name: str
    component: str
    metric_name: str
    current_value: float
    threshold: float
    severity: str
    timestamp: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class MetricsCollector:
    """Collect performance metrics from hybrid architecture"""

    def __init__(self):
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.collection_interval = 1.0  # seconds
        self.is_collecting = False
        self.collection_thread = None

    async def start_collection(self):
        """Start metrics collection"""
        logger.info("Starting performance metrics collection")
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()

    async def stop_collection(self):
        """Stop metrics collection"""
        logger.info("Stopping performance metrics collection")
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join()

    def _collection_loop(self):
        """Main collection loop"""
        while self.is_collecting:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()

                # Collect CPython metrics
                cpython_metrics = self._collect_cpython_metrics()

                # Collect Condon metrics
                condon_metrics = self._collect_condon_metrics()

                # Collect hybrid metrics
                hybrid_metrics = self._collect_hybrid_metrics()

                # Store all metrics
                all_metrics = (
                    system_metrics + cpython_metrics + condon_metrics + hybrid_metrics
                )

                for metric in all_metrics:
                    key = f"{metric.component}_{metric.metric_name}"
                    self.metrics_history[key].append(metric)

                time.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                time.sleep(self.collection_interval)

    def _collect_system_metrics(self) -> List[PerformanceMetric]:
        """Collect system-level performance metrics"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        metrics = []

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics.append(
                PerformanceMetric(
                    component="system",
                    metric_name="cpu_usage",
                    value=cpu_percent,
                    unit="percent",
                    timestamp=timestamp,
                )
            )

            # Memory usage
            memory = psutil.virtual_memory()
            metrics.append(
                PerformanceMetric(
                    component="system",
                    metric_name="memory_usage",
                    value=memory.percent,
                    unit="percent",
                    timestamp=timestamp,
                )
            )

            # Memory available
            metrics.append(
                PerformanceMetric(
                    component="system",
                    metric_name="memory_available",
                    value=memory.available / (1024 * 1024 * 1024),  # GB
                    unit="GB",
                    timestamp=timestamp,
                )
            )

            # Disk usage
            disk = psutil.disk_usage("/")
            metrics.append(
                PerformanceMetric(
                    component="system",
                    metric_name="disk_usage",
                    value=disk.percent,
                    unit="percent",
                    timestamp=timestamp,
                )
            )

            # Network I/O
            network = psutil.net_io_counters()
            metrics.append(
                PerformanceMetric(
                    component="system",
                    metric_name="network_bytes_sent",
                    value=network.bytes_sent,
                    unit="bytes",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="system",
                    metric_name="network_bytes_recv",
                    value=network.bytes_recv,
                    unit="bytes",
                    timestamp=timestamp,
                )
            )

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

        return metrics

    def _collect_cpython_metrics(self) -> List[PerformanceMetric]:
        """Collect CPython component metrics"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        metrics = []

        try:
            # Mock CPython metrics for demonstration
            # In a real implementation, these would be collected from actual CPython components

            # Auth service metrics
            metrics.append(
                PerformanceMetric(
                    component="cpython",
                    metric_name="auth_service_latency",
                    value=5.2,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="cpython",
                    metric_name="auth_service_throughput",
                    value=1000,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

            # Dashboard service metrics
            metrics.append(
                PerformanceMetric(
                    component="cpython",
                    metric_name="dashboard_service_latency",
                    value=12.5,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="cpython",
                    metric_name="dashboard_service_throughput",
                    value=500,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

            # Streaming service metrics
            metrics.append(
                PerformanceMetric(
                    component="cpython",
                    metric_name="streaming_service_latency",
                    value=2.1,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="cpython",
                    metric_name="streaming_service_throughput",
                    value=2000,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

        except Exception as e:
            logger.error(f"Error collecting CPython metrics: {e}")

        return metrics

    def _collect_condon_metrics(self) -> List[PerformanceMetric]:
        """Collect Condon component metrics"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        metrics = []

        try:
            # Mock Condon metrics for demonstration
            # In a real implementation, these would be collected from actual Condon components

            # Analytics engine metrics
            metrics.append(
                PerformanceMetric(
                    component="condon",
                    metric_name="analytics_engine_latency",
                    value=15.2,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="condon",
                    metric_name="analytics_engine_throughput",
                    value=300,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

            # AI detection metrics
            metrics.append(
                PerformanceMetric(
                    component="condon",
                    metric_name="ai_detection_latency",
                    value=8.5,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="condon",
                    metric_name="ai_detection_throughput",
                    value=400,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

            # Monitoring system metrics
            metrics.append(
                PerformanceMetric(
                    component="condon",
                    metric_name="monitoring_system_latency",
                    value=2.1,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="condon",
                    metric_name="monitoring_system_throughput",
                    value=1500,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

        except Exception as e:
            logger.error(f"Error collecting Condon metrics: {e}")

        return metrics

    def _collect_hybrid_metrics(self) -> List[PerformanceMetric]:
        """Collect hybrid component metrics"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        metrics = []

        try:
            # Mock hybrid metrics for demonstration
            # In a real implementation, these would be collected from actual hybrid components

            # Service boundary metrics
            metrics.append(
                PerformanceMetric(
                    component="hybrid",
                    metric_name="service_boundary_latency",
                    value=9.5,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="hybrid",
                    metric_name="service_boundary_throughput",
                    value=350,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

            # Communication metrics
            metrics.append(
                PerformanceMetric(
                    component="hybrid",
                    metric_name="communication_latency",
                    value=5.2,
                    unit="ms",
                    timestamp=timestamp,
                )
            )

            metrics.append(
                PerformanceMetric(
                    component="hybrid",
                    metric_name="communication_throughput",
                    value=600,
                    unit="ops/sec",
                    timestamp=timestamp,
                )
            )

        except Exception as e:
            logger.error(f"Error collecting hybrid metrics: {e}")

        return metrics

    def get_metrics(
        self, component: str = None, metric_name: str = None, time_range: int = 60
    ) -> List[PerformanceMetric]:
        """Get metrics for specified component and time range"""
        current_time = time.time()
        cutoff_time = current_time - time_range

        all_metrics = []

        for key, metrics_deque in self.metrics_history.items():
            if component and not key.startswith(component):
                continue

            if metric_name and metric_name not in key:
                continue

            for metric in metrics_deque:
                # Convert timestamp to time for comparison
                try:
                    metric_time = time.mktime(
                        time.strptime(metric.timestamp, "%Y-%m-%d %H:%M:%S")
                    )
                    if metric_time >= cutoff_time:
                        all_metrics.append(metric)
                except ValueError:
                    # Skip metrics with invalid timestamps
                    continue

        return all_metrics


class PerformanceAnalyzer:
    """Analyze performance metrics and detect patterns"""

    def __init__(self):
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5 minutes

    def analyze_latency_trends(
        self, metrics: List[PerformanceMetric]
    ) -> Dict[str, Any]:
        """Analyze latency trends"""
        if not metrics:
            return {"error": "No metrics available"}

        # Group metrics by component and metric name
        grouped_metrics = defaultdict(list)
        for metric in metrics:
            if "latency" in metric.metric_name.lower():
                key = f"{metric.component}_{metric.metric_name}"
                grouped_metrics[key].append(metric)

        analysis = {
            "total_latency_metrics": len(
                [m for m in metrics if "latency" in m.metric_name.lower()]
            ),
            "components_analyzed": list(
                set(m.component for m in metrics if "latency" in m.metric_name.lower())
            ),
            "trends": {},
            "anomalies": [],
        }

        for key, component_metrics in grouped_metrics.items():
            if len(component_metrics) < 2:
                continue

            values = [m.value for m in component_metrics]

            trend_analysis = {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "trend": self._calculate_trend(values),
                "anomaly_score": self._calculate_anomaly_score(values),
            }

            analysis["trends"][key] = trend_analysis

            # Detect anomalies
            if trend_analysis["anomaly_score"] > 2.0:  # 2 standard deviations
                analysis["anomalies"].append(
                    {
                        "metric": key,
                        "anomaly_score": trend_analysis["anomaly_score"],
                        "current_value": values[-1],
                        "expected_range": f"{trend_analysis['mean'] - 2 * trend_analysis['std_dev']:.2f} - {trend_analysis['mean'] + 2 * trend_analysis['std_dev']:.2f}",
                    }
                )

        return analysis

    def analyze_throughput_trends(
        self, metrics: List[PerformanceMetric]
    ) -> Dict[str, Any]:
        """Analyze throughput trends"""
        if not metrics:
            return {"error": "No metrics available"}

        # Group metrics by component and metric name
        grouped_metrics = defaultdict(list)
        for metric in metrics:
            if "throughput" in metric.metric_name.lower():
                key = f"{metric.component}_{metric.metric_name}"
                grouped_metrics[key].append(metric)

        analysis = {
            "total_throughput_metrics": len(
                [m for m in metrics if "throughput" in m.metric_name.lower()]
            ),
            "components_analyzed": list(
                set(
                    m.component
                    for m in metrics
                    if "throughput" in m.metric_name.lower()
                )
            ),
            "trends": {},
            "bottlenecks": [],
        }

        for key, component_metrics in grouped_metrics.items():
            if len(component_metrics) < 2:
                continue

            values = [m.value for m in component_metrics]

            trend_analysis = {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "trend": self._calculate_trend(values),
                "efficiency_score": self._calculate_efficiency_score(values),
            }

            analysis["trends"][key] = trend_analysis

            # Detect bottlenecks
            if trend_analysis["efficiency_score"] < 0.7:  # Less than 70% efficiency
                analysis["bottlenecks"].append(
                    {
                        "metric": key,
                        "efficiency_score": trend_analysis["efficiency_score"],
                        "current_throughput": values[-1],
                        "recommendation": "Consider optimization or scaling",
                    }
                )

        return analysis

    def analyze_resource_usage(
        self, metrics: List[PerformanceMetric]
    ) -> Dict[str, Any]:
        """Analyze resource usage patterns"""
        if not metrics:
            return {"error": "No metrics available"}

        # Filter for resource metrics
        resource_metrics = [
            m
            for m in metrics
            if any(
                keyword in m.metric_name.lower()
                for keyword in ["cpu", "memory", "disk"]
            )
        ]

        analysis = {
            "total_resource_metrics": len(resource_metrics),
            "resource_usage": {},
            "alerts": [],
        }

        # Group by resource type
        for metric in resource_metrics:
            if "cpu" in metric.metric_name.lower():
                resource_type = "cpu"
            elif "memory" in metric.metric_name.lower():
                resource_type = "memory"
            elif "disk" in metric.metric_name.lower():
                resource_type = "disk"
            else:
                resource_type = "other"

            if resource_type not in analysis["resource_usage"]:
                analysis["resource_usage"][resource_type] = []

            analysis["resource_usage"][resource_type].append(metric.value)

        # Analyze each resource type
        for resource_type, values in analysis["resource_usage"].items():
            if not values:
                continue

            avg_usage = statistics.mean(values)
            max_usage = max(values)

            analysis["resource_usage"][resource_type] = {
                "average": avg_usage,
                "maximum": max_usage,
                "current": values[-1] if values else 0,
            }

            # Generate alerts for high usage
            if avg_usage > 80:  # 80% threshold
                analysis["alerts"].append(
                    {
                        "resource": resource_type,
                        "usage": avg_usage,
                        "severity": "high" if avg_usage > 90 else "medium",
                        "message": f"High {resource_type} usage detected: {avg_usage:.1f}%",
                    }
                )

        return analysis

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return "stable"

        # Simple linear trend calculation
        recent_values = values[-10:] if len(values) > 10 else values
        if len(recent_values) < 2:
            return "stable"

        # Calculate slope
        x_values = list(range(len(recent_values)))
        slope = self._calculate_slope(x_values, recent_values)

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    def _calculate_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate linear regression slope"""
        n = len(x_values)
        if n != len(y_values) or n < 2:
            return 0.0

        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def _calculate_anomaly_score(self, values: List[float]) -> float:
        """Calculate anomaly score based on standard deviation"""
        if len(values) < 2:
            return 0.0

        mean = statistics.mean(values)
        std_dev = statistics.stdev(values)

        if std_dev == 0:
            return 0.0

        # Calculate z-score for the most recent value
        latest_value = values[-1]
        z_score = abs(latest_value - mean) / std_dev

        return z_score

    def _calculate_efficiency_score(self, values: List[float]) -> float:
        """Calculate efficiency score (0-1)"""
        if not values:
            return 0.0

        # Simple efficiency calculation based on consistency
        mean = statistics.mean(values)
        if mean == 0:
            return 0.0

        # Calculate coefficient of variation
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        cv = std_dev / mean if mean > 0 else 0

        # Efficiency score decreases with higher variation
        efficiency = max(0, 1 - cv)
        return efficiency


class AlertManager:
    """Manage performance alerts and notifications"""

    def __init__(self):
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.notification_channels = ["console", "email", "slack"]

    def add_alert_rule(self, rule: AlertRule):
        """Add a new alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule"""
        self.alert_rules = [r for r in self.alert_rules if r.name != rule_name]
        logger.info(f"Removed alert rule: {rule_name}")

    def check_alerts(self, metrics: List[PerformanceMetric]) -> List[Alert]:
        """Check metrics against alert rules"""
        new_alerts = []

        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            # Find matching metrics
            matching_metrics = [
                m
                for m in metrics
                if m.component == rule.component and m.metric_name == rule.metric_name
            ]

            if not matching_metrics:
                continue

            # Get the most recent metric
            latest_metric = max(matching_metrics, key=lambda m: m.timestamp)

            # Check if alert condition is met
            alert_triggered = self._check_alert_condition(
                latest_metric.value, rule.threshold, rule.operator
            )

            if alert_triggered:
                # Check if this alert is already active
                existing_alert = next(
                    (a for a in self.active_alerts if a.rule_name == rule.name), None
                )

                if not existing_alert:
                    # Create new alert
                    alert = Alert(
                        rule_name=rule.name,
                        component=rule.component,
                        metric_name=rule.metric_name,
                        current_value=latest_metric.value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                        message=f"{rule.metric_name} exceeded threshold: {latest_metric.value} {latest_metric.unit} > {rule.threshold} {latest_metric.unit}",
                    )

                    new_alerts.append(alert)
                    self.active_alerts.append(alert)
                    self.alert_history.append(alert)

                    # Send notification
                    self._send_notification(alert)

        # Check for resolved alerts
        resolved_alerts = []
        for alert in self.active_alerts[:]:
            # Find the rule for this alert
            rule = next(
                (r for r in self.alert_rules if r.name == alert.rule_name), None
            )
            if not rule:
                continue

            # Find current metric value
            current_metrics = [
                m
                for m in metrics
                if m.component == alert.component and m.metric_name == alert.metric_name
            ]

            if current_metrics:
                current_value = max(current_metrics, key=lambda m: m.timestamp).value

                # Check if alert condition is no longer met
                if not self._check_alert_condition(
                    current_value, rule.threshold, rule.operator
                ):
                    resolved_alerts.append(alert)
                    self.active_alerts.remove(alert)

        if resolved_alerts:
            logger.info(f"Resolved {len(resolved_alerts)} alerts")

        return new_alerts

    def _check_alert_condition(
        self, value: float, threshold: float, operator: str
    ) -> bool:
        """Check if alert condition is met"""
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "eq":
            return value == threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        else:
            return False

    def _send_notification(self, alert: Alert):
        """Send alert notification"""
        logger.warning(f"ALERT: {alert.message}")

        for channel in self.notification_channels:
            if channel == "console":
                self._send_console_notification(alert)
            elif channel == "email":
                self._send_email_notification(alert)
            elif channel == "slack":
                self._send_slack_notification(alert)

    def _send_console_notification(self, alert: Alert):
        """Send console notification"""
        print(f"\n{'='*60}")
        print(f"PERFORMANCE ALERT - {alert.severity.upper()}")
        print(f"{'='*60}")
        print(f"Component: {alert.component}")
        print(f"Metric: {alert.metric_name}")
        print(f"Current Value: {alert.current_value}")
        print(f"Threshold: {alert.threshold}")
        print(f"Message: {alert.message}")
        print(f"Timestamp: {alert.timestamp}")
        print(f"{'='*60}\n")

    def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        # Mock implementation for demonstration
        logger.info(f"Email alert sent: {alert.message}")

    def _send_slack_notification(self, alert: Alert):
        """Send Slack notification"""
        # Mock implementation for demonstration
        logger.info(f"Slack alert sent: {alert.message}")

    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts"""
        return self.active_alerts.copy()

    def get_alert_history(self, time_range: int = 3600) -> List[Alert]:
        """Get alert history within time range"""
        current_time = time.time()
        cutoff_time = current_time - time_range

        recent_alerts = []
        for alert in self.alert_history:
            try:
                alert_time = time.mktime(
                    time.strptime(alert.timestamp, "%Y-%m-%d %H:%M:%S")
                )
                if alert_time >= cutoff_time:
                    recent_alerts.append(alert)
            except ValueError:
                continue

        return recent_alerts


class ReportGenerator:
    """Generate performance reports"""

    def __init__(self):
        self.output_dir = Path("performance_reports")
        self.output_dir.mkdir(exist_ok=True)

    def generate_performance_report(
        self, metrics: List[PerformanceMetric], alerts: List[Alert] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not metrics:
            return {"error": "No metrics available"}

        # Group metrics by component
        component_metrics = defaultdict(list)
        for metric in metrics:
            component_metrics[metric.component].append(metric)

        # Calculate summary statistics
        summary = {
            "total_metrics": len(metrics),
            "components_monitored": list(component_metrics.keys()),
            "time_range": self._calculate_time_range(metrics),
            "active_alerts": len(alerts) if alerts else 0,
        }

        # Component-specific analysis
        component_analysis = {}
        for component, component_metrics_list in component_metrics.items():
            analysis = self._analyze_component_metrics(component_metrics_list)
            component_analysis[component] = analysis

        report = {
            "summary": summary,
            "component_analysis": component_analysis,
            "alerts": [asdict(alert) for alert in alerts] if alerts else [],
            "recommendations": self._generate_recommendations(
                component_analysis, alerts
            ),
        }

        return report

    def _calculate_time_range(self, metrics: List[PerformanceMetric]) -> str:
        """Calculate the time range of metrics"""
        if not metrics:
            return "No metrics"

        timestamps = [m.timestamp for m in metrics]
        try:
            start_time = min(timestamps)
            end_time = max(timestamps)
            return f"{start_time} to {end_time}"
        except:
            return "Unknown"

    def _analyze_component_metrics(
        self, metrics: List[PerformanceMetric]
    ) -> Dict[str, Any]:
        """Analyze metrics for a specific component"""
        if not metrics:
            return {"error": "No metrics available"}

        # Group by metric name
        metric_groups = defaultdict(list)
        for metric in metrics:
            metric_groups[metric.metric_name].append(metric)

        analysis = {
            "total_metrics": len(metrics),
            "metric_types": list(metric_groups.keys()),
            "metric_analysis": {},
        }

        for metric_name, metric_list in metric_groups.items():
            values = [m.value for m in metric_list]

            metric_analysis = {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "latest_value": values[-1] if values else 0,
            }

            analysis["metric_analysis"][metric_name] = metric_analysis

        return analysis

    def _generate_recommendations(
        self, component_analysis: Dict[str, Any], alerts: List[Alert] = None
    ) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        # Analyze each component
        for component, analysis in component_analysis.items():
            if "error" in analysis:
                continue

            metric_analysis = analysis.get("metric_analysis", {})

            # Check for high latency
            for metric_name, metrics in metric_analysis.items():
                if "latency" in metric_name.lower():
                    latest_value = metrics.get("latest_value", 0)
                    mean_value = metrics.get("mean", 0)

                    if latest_value > mean_value * 1.5:  # 50% increase
                        recommendations.append(
                            f"High latency detected in {component} {metric_name}: "
                            f"{latest_value:.2f} (avg: {mean_value:.2f})"
                        )

            # Check for low throughput
            for metric_name, metrics in metric_analysis.items():
                if "throughput" in metric_name.lower():
                    latest_value = metrics.get("latest_value", 0)
                    mean_value = metrics.get("mean", 0)

                    if latest_value < mean_value * 0.7:  # 30% decrease
                        recommendations.append(
                            f"Low throughput detected in {component} {metric_name}: "
                            f"{latest_value:.2f} (avg: {mean_value:.2f})"
                        )

        # Add recommendations based on alerts
        if alerts:
            high_severity_alerts = [
                a for a in alerts if a.severity in ["high", "critical"]
            ]
            if high_severity_alerts:
                recommendations.append(
                    f"Immediate attention required: {len(high_severity_alerts)} high-severity alerts active"
                )

        return recommendations

    def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """Save performance report to file"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Performance report saved: {filepath}")
        return str(filepath)


class PerformanceMonitor:
    """Real-time performance monitoring for hybrid architecture"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.performance_analyzer = PerformanceAnalyzer()
        self.alert_manager = AlertManager()
        self.report_generator = ReportGenerator()
        self.is_monitoring = False

    async def start_monitoring(self):
        """Start performance monitoring"""
        logger.info("Starting performance monitoring")

        # Set up default alert rules
        self._setup_default_alert_rules()

        # Start metrics collection
        await self.metrics_collector.start_collection()

        self.is_monitoring = True
        logger.info("Performance monitoring started")

    async def stop_monitoring(self):
        """Stop performance monitoring"""
        logger.info("Stopping performance monitoring")

        # Stop metrics collection
        await self.metrics_collector.stop_collection()

        self.is_monitoring = False
        logger.info("Performance monitoring stopped")

    def _setup_default_alert_rules(self):
        """Set up default alert rules"""
        default_rules = [
            AlertRule("high_cpu_usage", "system", "cpu_usage", 80.0, "gt", "medium"),
            AlertRule(
                "high_memory_usage", "system", "memory_usage", 85.0, "gt", "high"
            ),
            AlertRule("high_disk_usage", "system", "disk_usage", 90.0, "gt", "high"),
            AlertRule(
                "high_latency_cpython",
                "cpython",
                "auth_service_latency",
                50.0,
                "gt",
                "medium",
            ),
            AlertRule(
                "high_latency_condon",
                "condon",
                "analytics_engine_latency",
                100.0,
                "gt",
                "medium",
            ),
            AlertRule(
                "low_throughput_cpython",
                "cpython",
                "auth_service_throughput",
                500.0,
                "lt",
                "medium",
            ),
            AlertRule(
                "low_throughput_condon",
                "condon",
                "analytics_engine_throughput",
                200.0,
                "lt",
                "medium",
            ),
        ]

        for rule in default_rules:
            self.alert_manager.add_alert_rule(rule)

    async def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        if not self.is_monitoring:
            return {"status": "not_monitoring"}

        # Get recent metrics
        metrics = self.metrics_collector.get_metrics(time_range=60)  # Last 60 seconds

        # Check for alerts
        alerts = self.alert_manager.check_alerts(metrics)

        # Generate status report
        status = {
            "status": "monitoring",
            "metrics_collected": len(metrics),
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "recent_alerts": len(alerts),
            "components_monitored": list(set(m.component for m in metrics)),
        }

        return status

    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.is_monitoring:
            return {"error": "Monitoring not active"}

        # Get metrics from last hour
        metrics = self.metrics_collector.get_metrics(time_range=3600)

        # Get active alerts
        active_alerts = self.alert_manager.get_active_alerts()

        # Generate report
        report = self.report_generator.generate_performance_report(
            metrics, active_alerts
        )

        return report

    async def get_alert_history(self, time_range: int = 3600) -> List[Alert]:
        """Get alert history"""
        return self.alert_manager.get_alert_history(time_range)


async def main():
    """Main function for testing"""
    monitor = PerformanceMonitor()

    # Start monitoring
    await monitor.start_monitoring()

    # Let it run for a few seconds
    await asyncio.sleep(5)

    # Get current status
    status = await monitor.get_current_status()
    print(f"Monitoring Status: {status}")

    # Generate report
    report = await monitor.generate_performance_report()
    print(f"Performance Report: {report}")

    # Stop monitoring
    await monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
