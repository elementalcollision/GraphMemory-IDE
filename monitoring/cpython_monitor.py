"""
CPython Service Monitoring
Specialized monitoring for CPython services in hybrid architecture
"""

import asyncio
import gc
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psutil
from opentelemetry import trace
from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class CPythonMonitor:
    """
    CPython-specific monitoring for hybrid architecture

    Monitors:
    - GIL contention and thread behavior
    - Memory allocation and garbage collection
    - Async task performance
    - CPU-bound vs I/O-bound operations
    - Python-specific bottlenecks
    """

    def __init__(self, service_name: str = "cpython-service"):
        self.service_name = service_name
        self.process = psutil.Process()

        # CPython-specific metrics
        self.metrics = {
            # GIL metrics
            "gil_contention_time": Histogram(
                "cpython_gil_contention_seconds",
                "Time spent waiting for GIL",
                ["thread_id", "operation"],
            ),
            "gil_acquire_count": Counter(
                "cpython_gil_acquire_total", "Number of GIL acquisitions", ["thread_id"]
            ),
            # Memory metrics
            "memory_allocated": Gauge(
                "cpython_memory_allocated_bytes", "Currently allocated memory"
            ),
            "memory_peak": Gauge("cpython_memory_peak_bytes", "Peak memory usage"),
            "gc_collections": Counter(
                "cpython_gc_collections_total",
                "Garbage collection events",
                ["generation"],
            ),
            "gc_time": Histogram(
                "cpython_gc_duration_seconds",
                "Garbage collection duration",
                ["generation"],
            ),
            # Async metrics
            "async_tasks_active": Gauge(
                "cpython_async_tasks_active", "Number of active async tasks"
            ),
            "async_tasks_completed": Counter(
                "cpython_async_tasks_completed_total", "Number of completed async tasks"
            ),
            "async_task_duration": Histogram(
                "cpython_async_task_duration_seconds", "Async task execution duration"
            ),
            # Thread metrics
            "thread_count": Gauge("cpython_thread_count", "Number of active threads"),
            "thread_cpu_time": Histogram(
                "cpython_thread_cpu_time_seconds", "CPU time per thread", ["thread_id"]
            ),
            # Performance metrics
            "cpu_bound_operations": Counter(
                "cpython_cpu_bound_operations_total",
                "CPU-bound operations",
                ["operation_type"],
            ),
            "io_bound_operations": Counter(
                "cpython_io_bound_operations_total",
                "I/O-bound operations",
                ["operation_type"],
            ),
            "blocking_operations": Counter(
                "cpython_blocking_operations_total",
                "Blocking operations",
                ["operation_type"],
            ),
        }

        # Monitoring state
        self._gil_monitor_active = False
        self._memory_monitor_active = False
        self._async_monitor_active = False
        self._monitoring_thread = None

        logger.info(f"Initialized CPython monitor for {service_name}")

    def start_monitoring(self):
        """Start comprehensive CPython monitoring"""
        if not self._monitoring_thread:
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True
            )
            self._monitoring_thread.start()
            logger.info("Started CPython monitoring")

    def stop_monitoring(self):
        """Stop CPython monitoring"""
        self._gil_monitor_active = False
        self._memory_monitor_active = False
        self._async_monitor_active = False

        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
            self._monitoring_thread = None

        logger.info("Stopped CPython monitoring")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                self._update_memory_metrics()
                self._update_thread_metrics()
                self._update_async_metrics()
                time.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying

    def _update_memory_metrics(self):
        """Update memory-related metrics"""
        try:
            # Get memory info
            memory_info = self.process.memory_info()
            self.metrics["memory_allocated"].set(memory_info.rss)

            # Update peak memory
            current_peak = self.metrics["memory_peak"]._value.get()
            if current_peak is None or memory_info.rss > current_peak:
                self.metrics["memory_peak"].set(memory_info.rss)

            # GC statistics
            gc_stats = gc.get_stats()
            for gen, stats in enumerate(gc_stats):
                self.metrics["gc_collections"].labels(generation=f"gen{gen}").inc(
                    stats.get("collections", 0)
                )

        except Exception as e:
            logger.error(f"Error updating memory metrics: {e}")

    def _update_thread_metrics(self):
        """Update thread-related metrics"""
        try:
            # Thread count
            thread_count = threading.active_count()
            self.metrics["thread_count"].set(thread_count)

            # CPU time per thread (simplified)
            for thread in threading.enumerate():
                if hasattr(thread, "_thread_id"):
                    # This is a simplified approach
                    # In production, you'd use more sophisticated thread monitoring
                    pass

        except Exception as e:
            logger.error(f"Error updating thread metrics: {e}")

    def _update_async_metrics(self):
        """Update async task metrics"""
        try:
            # Get current event loop
            try:
                loop = asyncio.get_running_loop()
                if loop:
                    # Count active tasks (simplified)
                    task_count = len(asyncio.all_tasks(loop))
                    self.metrics["async_tasks_active"].set(task_count)
            except RuntimeError:
                # No running event loop
                self.metrics["async_tasks_active"].set(0)

        except Exception as e:
            logger.error(f"Error updating async metrics: {e}")

    @contextmanager
    def monitor_gil_contention(self, operation: str = "unknown"):
        """Monitor GIL contention for a code block"""
        thread_id = threading.get_ident()
        start_time = time.time()

        try:
            # Record GIL acquisition
            self.metrics["gil_acquire_count"].labels(thread_id=str(thread_id)).inc()

            yield

        finally:
            # Record contention time (simplified)
            duration = time.time() - start_time
            self.metrics["gil_contention_time"].labels(
                thread_id=str(thread_id), operation=operation
            ).observe(duration)

    @contextmanager
    def monitor_gc(self, generation: int = 0):
        """Monitor garbage collection"""
        start_time = time.time()

        try:
            yield

        finally:
            # Record GC duration
            duration = time.time() - start_time
            self.metrics["gc_time"].labels(generation=f"gen{generation}").observe(
                duration
            )

    @contextmanager
    def monitor_async_task(self, task_name: str = "unknown"):
        """Monitor async task execution"""
        start_time = time.time()

        try:
            # Increment active tasks
            self.metrics["async_tasks_active"].inc()

            yield

        finally:
            # Record task completion
            duration = time.time() - start_time
            self.metrics["async_task_duration"].observe(duration)
            self.metrics["async_tasks_completed"].inc()
            self.metrics["async_tasks_active"].dec()

    def record_cpu_bound_operation(self, operation_type: str):
        """Record CPU-bound operation"""
        self.metrics["cpu_bound_operations"].labels(operation_type=operation_type).inc()

    def record_io_bound_operation(self, operation_type: str):
        """Record I/O-bound operation"""
        self.metrics["io_bound_operations"].labels(operation_type=operation_type).inc()

    def record_blocking_operation(self, operation_type: str):
        """Record blocking operation"""
        self.metrics["blocking_operations"].labels(operation_type=operation_type).inc()

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get CPython performance summary"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()

            return {
                "memory": {
                    "allocated_bytes": memory_info.rss,
                    "peak_bytes": self.metrics["memory_peak"]._value.get(),
                    "percent": (memory_info.rss / psutil.virtual_memory().total) * 100,
                },
                "cpu": {
                    "usage_percent": cpu_percent,
                    "thread_count": threading.active_count(),
                },
                "async": {
                    "active_tasks": self.metrics["async_tasks_active"]._value.get() or 0
                },
                "gc": {
                    "collections": sum(self.metrics["gc_collections"]._metrics.values())
                },
            }
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}

    def get_gil_statistics(self) -> Dict[str, Any]:
        """Get GIL contention statistics"""
        try:
            return {
                "contention_time": {
                    "total": sum(
                        metric._sum.get()
                        for metric in self.metrics[
                            "gil_contention_time"
                        ]._metrics.values()
                    ),
                    "count": sum(
                        metric._count.get()
                        for metric in self.metrics[
                            "gil_contention_time"
                        ]._metrics.values()
                    ),
                },
                "acquisitions": sum(
                    metric._value.get()
                    for metric in self.metrics["gil_acquire_count"]._metrics.values()
                ),
            }
        except Exception as e:
            logger.error(f"Error getting GIL statistics: {e}")
            return {}


class CPythonServiceMonitor:
    """
    Service-specific CPython monitoring

    Provides monitoring for specific CPython services in the hybrid architecture
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.monitor = CPythonMonitor(service_name)
        self.request_metrics = {
            "request_count": Counter(
                f"{service_name}_requests_total",
                "Request count",
                ["endpoint", "method"],
            ),
            "request_duration": Histogram(
                f"{service_name}_request_duration_seconds",
                "Request duration",
                ["endpoint"],
            ),
            "error_count": Counter(
                f"{service_name}_errors_total",
                "Error count",
                ["error_type", "endpoint"],
            ),
            "active_requests": Gauge(
                f"{service_name}_active_requests", "Active requests"
            ),
        }

        logger.info(f"Initialized CPython service monitor for {service_name}")

    def start_monitoring(self):
        """Start monitoring for this service"""
        self.monitor.start_monitoring()

    def stop_monitoring(self):
        """Stop monitoring for this service"""
        self.monitor.stop_monitoring()

    @contextmanager
    def monitor_request(self, endpoint: str, method: str = "GET"):
        """Monitor a service request"""
        start_time = time.time()

        try:
            # Increment active requests
            self.request_metrics["active_requests"].inc()
            self.request_metrics["request_count"].labels(
                endpoint=endpoint, method=method
            ).inc()

            yield

        except Exception as e:
            # Record error
            self.request_metrics["error_count"].labels(
                error_type=type(e).__name__, endpoint=endpoint
            ).inc()
            raise

        finally:
            # Record duration and decrement active requests
            duration = time.time() - start_time
            self.request_metrics["request_duration"].labels(endpoint=endpoint).observe(
                duration
            )
            self.request_metrics["active_requests"].dec()

    @contextmanager
    def monitor_async_operation(self, operation_name: str):
        """Monitor async operations"""
        with self.monitor.monitor_async_task(operation_name):
            yield

    def get_service_summary(self) -> Dict[str, Any]:
        """Get service-specific summary"""
        return {
            "service_name": self.service_name,
            "performance": self.monitor.get_performance_summary(),
            "gil_stats": self.monitor.get_gil_statistics(),
            "requests": {
                "active": self.request_metrics["active_requests"]._value.get() or 0,
                "total": sum(
                    metric._value.get()
                    for metric in self.request_metrics[
                        "request_count"
                    ]._metrics.values()
                ),
            },
        }


# Global CPython monitoring instance
_cpython_monitor = None


def get_cpython_monitor(service_name: str = "cpython-service") -> CPythonServiceMonitor:
    """Get CPython service monitor instance"""
    global _cpython_monitor
    if _cpython_monitor is None:
        _cpython_monitor = CPythonServiceMonitor(service_name)
    return _cpython_monitor


def initialize_cpython_monitoring(service_name: str) -> CPythonServiceMonitor:
    """Initialize CPython monitoring for a service"""
    monitor = CPythonServiceMonitor(service_name)
    monitor.start_monitoring()
    return monitor
