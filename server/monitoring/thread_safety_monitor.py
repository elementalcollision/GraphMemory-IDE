"""
Production Thread Safety Monitoring System

This module provides production-ready monitoring for the hybrid CPython/Codon thread safety
framework, including real-time metrics, alerting, and integration with existing monitoring
infrastructure.
"""

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

# Import existing monitoring components
from server.monitoring.alerting_system import AlertingSystem
from server.monitoring.metrics_collector import MetricsCollector

# Import thread safety framework
from server.utils.thread_safety import (
    HybridThreadSafetyFramework,
    RuntimeType,
    ThreadSafetyConfig,
    ThreadSafetyLevel,
    get_thread_safety_framework,
)

logger = logging.getLogger(__name__)


@dataclass
class ThreadSafetyAlert:
    """Thread safety alert configuration"""

    alert_type: str
    severity: str
    component: str
    runtime: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreadSafetyMetrics:
    """Thread safety metrics data"""

    thread_count: int
    memory_usage: int
    lock_contention: int
    violations: int
    deadlocks_detected: int
    memory_leaks: int
    runtime_performance: Dict[str, float]
    component_safety: Dict[str, bool]
    timestamp: datetime


class ThreadSafetyMonitor:
    """Production thread safety monitoring system"""

    def __init__(self, config: Optional[ThreadSafetyConfig] = None):
        self.config = config or ThreadSafetyConfig(
            runtime_type=RuntimeType.HYBRID, safety_level=ThreadSafetyLevel.STRICT
        )
        self.framework = get_thread_safety_framework()
        self.alerting_system = AlertingSystem()
        self.metrics_collector = MetricsCollector()

        # Monitoring state
        self._monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._alert_handlers: List[Callable[[ThreadSafetyAlert], None]] = []
        self._metrics_history: List[ThreadSafetyMetrics] = []
        self._max_history_size = 1000

        # Alert thresholds
        self.alert_thresholds = {
            "thread_count": 100,
            "memory_usage_mb": 1024,
            "lock_contention": 50,
            "violations": 10,
            "deadlocks_detected": 1,
            "memory_leaks": 5,
        }

    async def start_monitoring(self) -> None:
        """Start thread safety monitoring"""
        if self._monitoring_active:
            logger.warning("Thread safety monitoring already active")
            return

        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Thread safety monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop thread safety monitoring"""
        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Thread safety monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()

                # Store metrics
                self._store_metrics(metrics)

                # Check for alerts
                alerts = await self._check_alerts(metrics)

                # Send alerts
                for alert in alerts:
                    await self._send_alert(alert)

                # Update monitoring systems
                await self._update_monitoring_systems(metrics)

                # Wait for next cycle
                await asyncio.sleep(1.0)  # 1 second monitoring interval

            except Exception as e:
                logger.error(f"Thread safety monitoring error: {e}")
                await asyncio.sleep(5.0)  # Wait before retry

    async def _collect_metrics(self) -> ThreadSafetyMetrics:
        """Collect thread safety metrics"""
        # Get framework metrics
        framework_metrics = self.framework.monitor.get_metrics()

        # Get safety report
        safety_report = self.framework.get_safety_report()

        # Calculate runtime performance
        runtime_performance = {}
        for runtime in [RuntimeType.CPYTHON, RuntimeType.CONDON, RuntimeType.HYBRID]:
            runtime_performance[runtime.value] = self._calculate_runtime_performance(
                runtime
            )

        # Calculate component safety
        component_safety = {}
        for component, result in safety_report.get("validation_results", {}).items():
            component_safety[component] = result.get("overall_safety", False)

        return ThreadSafetyMetrics(
            thread_count=framework_metrics.get("thread_count", 0),
            memory_usage=framework_metrics.get("memory_usage", 0),
            lock_contention=framework_metrics.get("lock_contention", 0),
            violations=framework_metrics.get("violations", 0),
            deadlocks_detected=framework_metrics.get("deadlocks_detected", 0),
            memory_leaks=len(safety_report.get("memory_leaks", {})),
            runtime_performance=runtime_performance,
            component_safety=component_safety,
            timestamp=datetime.now(),
        )

    def _calculate_runtime_performance(self, runtime: RuntimeType) -> float:
        """Calculate performance score for a runtime"""
        # Simplified performance calculation
        # In production, this would use actual performance metrics
        base_performance = {
            RuntimeType.CPYTHON: 0.8,
            RuntimeType.CONDON: 0.95,
            RuntimeType.HYBRID: 0.85,
        }
        return base_performance.get(runtime, 0.5)

    def _store_metrics(self, metrics: ThreadSafetyMetrics) -> None:
        """Store metrics in history"""
        self._metrics_history.append(metrics)

        # Maintain history size
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history.pop(0)

    async def _check_alerts(
        self, metrics: ThreadSafetyMetrics
    ) -> List[ThreadSafetyAlert]:
        """Check for thread safety alerts"""
        alerts = []

        # Check thread count
        if metrics.thread_count > self.alert_thresholds["thread_count"]:
            alerts.append(
                ThreadSafetyAlert(
                    alert_type="high_thread_count",
                    severity="warning",
                    component="system",
                    runtime="all",
                    message=f"High thread count: {metrics.thread_count}",
                    timestamp=metrics.timestamp,
                    metadata={"thread_count": metrics.thread_count},
                )
            )

        # Check memory usage
        memory_mb = metrics.memory_usage / (1024 * 1024)
        if memory_mb > self.alert_thresholds["memory_usage_mb"]:
            alerts.append(
                ThreadSafetyAlert(
                    alert_type="high_memory_usage",
                    severity="warning",
                    component="system",
                    runtime="all",
                    message=f"High memory usage: {memory_mb:.2f} MB",
                    timestamp=metrics.timestamp,
                    metadata={"memory_usage_mb": memory_mb},
                )
            )

        # Check lock contention
        if metrics.lock_contention > self.alert_thresholds["lock_contention"]:
            alerts.append(
                ThreadSafetyAlert(
                    alert_type="high_lock_contention",
                    severity="warning",
                    component="system",
                    runtime="all",
                    message=f"High lock contention: {metrics.lock_contention}",
                    timestamp=metrics.timestamp,
                    metadata={"lock_contention": metrics.lock_contention},
                )
            )

        # Check violations
        if metrics.violations > self.alert_thresholds["violations"]:
            alerts.append(
                ThreadSafetyAlert(
                    alert_type="thread_safety_violations",
                    severity="error",
                    component="system",
                    runtime="all",
                    message=f"Thread safety violations: {metrics.violations}",
                    timestamp=metrics.timestamp,
                    metadata={"violations": metrics.violations},
                )
            )

        # Check deadlocks
        if metrics.deadlocks_detected > self.alert_thresholds["deadlocks_detected"]:
            alerts.append(
                ThreadSafetyAlert(
                    alert_type="deadlock_detected",
                    severity="critical",
                    component="system",
                    runtime="all",
                    message=f"Deadlock detected: {metrics.deadlocks_detected}",
                    timestamp=metrics.timestamp,
                    metadata={"deadlocks_detected": metrics.deadlocks_detected},
                )
            )

        # Check memory leaks
        if metrics.memory_leaks > self.alert_thresholds["memory_leaks"]:
            alerts.append(
                ThreadSafetyAlert(
                    alert_type="memory_leaks",
                    severity="error",
                    component="system",
                    runtime="all",
                    message=f"Memory leaks detected: {metrics.memory_leaks}",
                    timestamp=metrics.timestamp,
                    metadata={"memory_leaks": metrics.memory_leaks},
                )
            )

        # Check component safety
        unsafe_components = [
            component
            for component, safe in metrics.component_safety.items()
            if not safe
        ]
        if unsafe_components:
            alerts.append(
                ThreadSafetyAlert(
                    alert_type="unsafe_components",
                    severity="warning",
                    component="system",
                    runtime="all",
                    message=f"Unsafe components: {', '.join(unsafe_components)}",
                    timestamp=metrics.timestamp,
                    metadata={"unsafe_components": unsafe_components},
                )
            )

        return alerts

    async def _send_alert(self, alert: ThreadSafetyAlert) -> None:
        """Send thread safety alert"""
        # Log alert
        logger.warning(f"Thread safety alert: {alert.alert_type} - {alert.message}")

        # Send to alerting system
        await self.alerting_system.send_alert(
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            metadata=alert.metadata,
        )

        # Call alert handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    async def _update_monitoring_systems(self, metrics: ThreadSafetyMetrics) -> None:
        """Update external monitoring systems"""
        # Update metrics collector
        await self.metrics_collector.record_metric(
            "thread_safety.thread_count",
            metrics.thread_count,
            tags={"component": "thread_safety"},
        )

        await self.metrics_collector.record_metric(
            "thread_safety.memory_usage",
            metrics.memory_usage,
            tags={"component": "thread_safety"},
        )

        await self.metrics_collector.record_metric(
            "thread_safety.lock_contention",
            metrics.lock_contention,
            tags={"component": "thread_safety"},
        )

        await self.metrics_collector.record_metric(
            "thread_safety.violations",
            metrics.violations,
            tags={"component": "thread_safety"},
        )

        await self.metrics_collector.record_metric(
            "thread_safety.deadlocks_detected",
            metrics.deadlocks_detected,
            tags={"component": "thread_safety"},
        )

        await self.metrics_collector.record_metric(
            "thread_safety.memory_leaks",
            metrics.memory_leaks,
            tags={"component": "thread_safety"},
        )

        # Record runtime performance metrics
        for runtime, performance in metrics.runtime_performance.items():
            await self.metrics_collector.record_metric(
                f"thread_safety.runtime_performance.{runtime}",
                performance,
                tags={"component": "thread_safety", "runtime": runtime},
            )

        # Record component safety metrics
        safe_components = sum(1 for safe in metrics.component_safety.values() if safe)
        total_components = len(metrics.component_safety)
        safety_ratio = (
            safe_components / total_components if total_components > 0 else 1.0
        )

        await self.metrics_collector.record_metric(
            "thread_safety.component_safety_ratio",
            safety_ratio,
            tags={"component": "thread_safety"},
        )

    def add_alert_handler(self, handler: Callable[[ThreadSafetyAlert], None]) -> None:
        """Add custom alert handler"""
        self._alert_handlers.append(handler)

    def get_metrics_history(
        self, limit: Optional[int] = None
    ) -> List[ThreadSafetyMetrics]:
        """Get metrics history"""
        if limit is None:
            return self._metrics_history.copy()
        return self._metrics_history[-limit:]

    def get_current_metrics(self) -> Optional[ThreadSafetyMetrics]:
        """Get current metrics"""
        if not self._metrics_history:
            return None
        return self._metrics_history[-1]

    def set_alert_threshold(self, alert_type: str, threshold: Any) -> None:
        """Set alert threshold"""
        if alert_type in self.alert_thresholds:
            self.alert_thresholds[alert_type] = threshold
            logger.info(f"Updated alert threshold for {alert_type}: {threshold}")

    def get_alert_thresholds(self) -> Dict[str, Any]:
        """Get current alert thresholds"""
        return self.alert_thresholds.copy()

    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive thread safety report"""
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return {"error": "No metrics available"}

        # Calculate statistics
        history = self.get_metrics_history(100)  # Last 100 metrics
        if not history:
            return {"error": "No history available"}

        # Calculate averages
        avg_thread_count = sum(m.thread_count for m in history) / len(history)
        avg_memory_usage = sum(m.memory_usage for m in history) / len(history)
        avg_lock_contention = sum(m.lock_contention for m in history) / len(history)
        avg_violations = sum(m.violations for m in history) / len(history)

        # Calculate trends
        recent_metrics = history[-10:] if len(history) >= 10 else history
        thread_count_trend = self._calculate_trend(
            [m.thread_count for m in recent_metrics]
        )
        memory_usage_trend = self._calculate_trend(
            [m.memory_usage for m in recent_metrics]
        )

        return {
            "current_metrics": {
                "thread_count": current_metrics.thread_count,
                "memory_usage_mb": current_metrics.memory_usage / (1024 * 1024),
                "lock_contention": current_metrics.lock_contention,
                "violations": current_metrics.violations,
                "deadlocks_detected": current_metrics.deadlocks_detected,
                "memory_leaks": current_metrics.memory_leaks,
                "runtime_performance": current_metrics.runtime_performance,
                "component_safety": current_metrics.component_safety,
            },
            "averages": {
                "thread_count": avg_thread_count,
                "memory_usage": avg_memory_usage,
                "lock_contention": avg_lock_contention,
                "violations": avg_violations,
            },
            "trends": {
                "thread_count": thread_count_trend,
                "memory_usage": memory_usage_trend,
            },
            "alert_thresholds": self.alert_thresholds,
            "monitoring_active": self._monitoring_active,
            "history_size": len(self._metrics_history),
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from list of values"""
        if len(values) < 2:
            return "stable"

        # Simple trend calculation
        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"


# Global thread safety monitor instance
_thread_safety_monitor: Optional[ThreadSafetyMonitor] = None


async def get_thread_safety_monitor() -> ThreadSafetyMonitor:
    """Get the global thread safety monitor instance"""
    global _thread_safety_monitor
    if _thread_safety_monitor is None:
        _thread_safety_monitor = ThreadSafetyMonitor()
        await _thread_safety_monitor.start_monitoring()
    return _thread_safety_monitor


async def shutdown_thread_safety_monitor() -> None:
    """Shutdown the global thread safety monitor"""
    global _thread_safety_monitor
    if _thread_safety_monitor is not None:
        await _thread_safety_monitor.stop_monitoring()
        _thread_safety_monitor = None


# Convenience functions for monitoring
async def record_thread_safety_event(
    event_type: str, component: str, runtime: str, metadata: Dict[str, Any] = None
) -> None:
    """Record a thread safety event"""
    monitor = await get_thread_safety_monitor()
    # This would integrate with the monitoring system
    logger.info(f"Thread safety event: {event_type} for {component} ({runtime})")


async def check_thread_safety_status() -> Dict[str, Any]:
    """Check current thread safety status"""
    monitor = await get_thread_safety_monitor()
    return await monitor.generate_report()


async def set_thread_safety_alert_threshold(alert_type: str, threshold: Any) -> None:
    """Set thread safety alert threshold"""
    monitor = await get_thread_safety_monitor()
    monitor.set_alert_threshold(alert_type, threshold)
