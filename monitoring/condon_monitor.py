"""
Condon Service Monitoring
Specialized monitoring for Condon services in hybrid architecture
"""

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil
from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class CompilationType(Enum):
    """Types of Condon compilation"""

    JIT = "jit"
    AOT = "aot"
    OPTIMIZATION = "optimization"
    DEBUG = "debug"


class ThreadSafetyEvent(Enum):
    """Thread safety event types"""

    LOCK_ACQUISITION = "lock_acquisition"
    LOCK_RELEASE = "lock_release"
    DEADLOCK_DETECTED = "deadlock_detected"
    RACE_CONDITION = "race_condition"
    THREAD_CREATION = "thread_creation"
    THREAD_DESTRUCTION = "thread_destruction"


@dataclass
class CompilationMetrics:
    """Compilation-specific metrics"""

    compilation_type: CompilationType
    duration: float
    memory_usage: int
    thread_count: int
    cache_hits: int
    cache_misses: int


class CondonMonitor:
    """
    Condon-specific monitoring for hybrid architecture

    Monitors:
    - Compilation performance and metrics
    - Thread safety and concurrency
    - Memory management and allocation
    - Cache performance
    - Native code execution
    """

    def __init__(self, service_name: str = "condon-service"):
        self.service_name = service_name
        self.process = psutil.Process()

        # Condon-specific metrics
        self.metrics = {
            # Compilation metrics
            "compilation_duration": Histogram(
                "condon_compilation_duration_seconds",
                "Compilation duration",
                ["compilation_type", "optimization_level"],
            ),
            "compilation_memory": Histogram(
                "condon_compilation_memory_bytes",
                "Memory used during compilation",
                ["compilation_type"],
            ),
            "compilation_threads": Gauge(
                "condon_compilation_threads",
                "Threads used during compilation",
                ["compilation_type"],
            ),
            "compilation_cache_hits": Counter(
                "condon_compilation_cache_hits_total",
                "Compilation cache hits",
                ["cache_type"],
            ),
            "compilation_cache_misses": Counter(
                "condon_compilation_cache_misses_total",
                "Compilation cache misses",
                ["cache_type"],
            ),
            # Thread safety metrics
            "thread_safety_events": Counter(
                "condon_thread_safety_events_total",
                "Thread safety events",
                ["event_type", "severity"],
            ),
            "lock_contention_time": Histogram(
                "condon_lock_contention_seconds",
                "Time spent waiting for locks",
                ["lock_type"],
            ),
            "deadlock_detections": Counter(
                "condon_deadlock_detections_total", "Deadlock detections"
            ),
            "race_condition_detections": Counter(
                "condon_race_condition_detections_total", "Race condition detections"
            ),
            # Memory metrics
            "memory_allocation": Counter(
                "condon_memory_allocation_bytes_total",
                "Memory allocation",
                ["allocation_type"],
            ),
            "memory_deallocation": Counter(
                "condon_memory_deallocation_bytes_total",
                "Memory deallocation",
                ["allocation_type"],
            ),
            "memory_peak": Gauge("condon_memory_peak_bytes", "Peak memory usage"),
            "memory_fragmentation": Gauge(
                "condon_memory_fragmentation_ratio", "Memory fragmentation ratio"
            ),
            # Performance metrics
            "native_execution_time": Histogram(
                "condon_native_execution_seconds",
                "Native code execution time",
                ["function_name", "optimization_level"],
            ),
            "optimization_effectiveness": Gauge(
                "condon_optimization_effectiveness",
                "Optimization effectiveness ratio",
                ["optimization_type"],
            ),
            "cache_efficiency": Gauge(
                "condon_cache_efficiency_ratio",
                "Cache efficiency ratio",
                ["cache_type"],
            ),
        }

        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._compilation_history: List[CompilationMetrics] = []

        logger.info(f"Initialized Condon monitor for {service_name}")

    def start_monitoring(self):
        """Start comprehensive Condon monitoring"""
        if not self._monitoring_thread:
            self._monitoring_active = True
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True
            )
            self._monitoring_thread.start()
            logger.info("Started Condon monitoring")

    def stop_monitoring(self):
        """Stop Condon monitoring"""
        self._monitoring_active = False

        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
            self._monitoring_thread = None

        logger.info("Stopped Condon monitoring")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                self._update_memory_metrics()
                self._update_thread_metrics()
                self._update_cache_metrics()
                time.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying

    def _update_memory_metrics(self):
        """Update memory-related metrics"""
        try:
            memory_info = self.process.memory_info()

            # Update peak memory
            current_peak = self.metrics["memory_peak"]._value.get()
            if current_peak is None or memory_info.rss > current_peak:
                self.metrics["memory_peak"].set(memory_info.rss)

            # Calculate fragmentation (simplified)
            # In production, you'd use more sophisticated fragmentation calculation
            fragmentation_ratio = 0.1  # Placeholder
            self.metrics["memory_fragmentation"].set(fragmentation_ratio)

        except Exception as e:
            logger.error(f"Error updating memory metrics: {e}")

    def _update_thread_metrics(self):
        """Update thread-related metrics"""
        try:
            thread_count = threading.active_count()

            # Update compilation thread metrics
            for compilation_type in CompilationType:
                # This would be updated based on actual compilation state
                pass

        except Exception as e:
            logger.error(f"Error updating thread metrics: {e}")

    def _update_cache_metrics(self):
        """Update cache-related metrics"""
        try:
            # Calculate cache efficiency ratios
            for cache_type in ["compilation", "optimization", "execution"]:
                hits = (
                    self.metrics["compilation_cache_hits"]
                    .labels(cache_type=cache_type)
                    ._value.get()
                    or 0
                )
                misses = (
                    self.metrics["compilation_cache_misses"]
                    .labels(cache_type=cache_type)
                    ._value.get()
                    or 0
                )

                total = hits + misses
                if total > 0:
                    efficiency = hits / total
                    self.metrics["cache_efficiency"].labels(cache_type=cache_type).set(
                        efficiency
                    )

        except Exception as e:
            logger.error(f"Error updating cache metrics: {e}")

    @contextmanager
    def monitor_compilation(
        self, compilation_type: CompilationType, optimization_level: str = "default"
    ):
        """Monitor compilation process"""
        start_time = time.time()
        start_memory = self.process.memory_info().rss
        start_threads = threading.active_count()

        try:
            yield

        finally:
            # Record compilation metrics
            duration = time.time() - start_time
            end_memory = self.process.memory_info().rss
            memory_used = end_memory - start_memory
            end_threads = threading.active_count()
            threads_used = end_threads - start_threads

            # Record metrics
            self.metrics["compilation_duration"].labels(
                compilation_type=compilation_type.value,
                optimization_level=optimization_level,
            ).observe(duration)

            self.metrics["compilation_memory"].labels(
                compilation_type=compilation_type.value
            ).observe(memory_used)

            self.metrics["compilation_threads"].labels(
                compilation_type=compilation_type.value
            ).set(threads_used)

            # Store compilation history
            self._compilation_history.append(
                CompilationMetrics(
                    compilation_type=compilation_type,
                    duration=duration,
                    memory_usage=memory_used,
                    thread_count=threads_used,
                    cache_hits=0,  # Would be updated based on actual cache hits
                    cache_misses=0,  # Would be updated based on actual cache misses
                )
            )

    @contextmanager
    def monitor_lock_contention(self, lock_type: str):
        """Monitor lock contention"""
        start_time = time.time()

        try:
            yield

        finally:
            duration = time.time() - start_time
            self.metrics["lock_contention_time"].labels(lock_type=lock_type).observe(
                duration
            )

    def record_thread_safety_event(
        self, event_type: ThreadSafetyEvent, severity: str = "info"
    ):
        """Record thread safety event"""
        self.metrics["thread_safety_events"].labels(
            event_type=event_type.value, severity=severity
        ).inc()

        # Record specific events
        if event_type == ThreadSafetyEvent.DEADLOCK_DETECTED:
            self.metrics["deadlock_detections"].inc()
        elif event_type == ThreadSafetyEvent.RACE_CONDITION:
            self.metrics["race_condition_detections"].inc()

    def record_memory_allocation(self, allocation_type: str, bytes_allocated: int):
        """Record memory allocation"""
        self.metrics["memory_allocation"].labels(allocation_type=allocation_type).inc(
            bytes_allocated
        )

    def record_memory_deallocation(self, allocation_type: str, bytes_freed: int):
        """Record memory deallocation"""
        self.metrics["memory_deallocation"].labels(allocation_type=allocation_type).inc(
            bytes_freed
        )

    def record_cache_hit(self, cache_type: str):
        """Record cache hit"""
        self.metrics["compilation_cache_hits"].labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str):
        """Record cache miss"""
        self.metrics["compilation_cache_misses"].labels(cache_type=cache_type).inc()

    @contextmanager
    def monitor_native_execution(
        self, function_name: str, optimization_level: str = "default"
    ):
        """Monitor native code execution"""
        start_time = time.time()

        try:
            yield

        finally:
            duration = time.time() - start_time
            self.metrics["native_execution_time"].labels(
                function_name=function_name, optimization_level=optimization_level
            ).observe(duration)

    def record_optimization_effectiveness(
        self, optimization_type: str, effectiveness_ratio: float
    ):
        """Record optimization effectiveness"""
        self.metrics["optimization_effectiveness"].labels(
            optimization_type=optimization_type
        ).set(effectiveness_ratio)

    def get_compilation_summary(self) -> Dict[str, Any]:
        """Get compilation performance summary"""
        try:
            return {
                "recent_compilations": len(self._compilation_history),
                "average_duration": sum(
                    c.duration for c in self._compilation_history[-10:]
                )
                / min(len(self._compilation_history), 10),
                "average_memory_usage": sum(
                    c.memory_usage for c in self._compilation_history[-10:]
                )
                / min(len(self._compilation_history), 10),
                "compilation_types": {
                    comp_type.value: len(
                        [
                            c
                            for c in self._compilation_history
                            if c.compilation_type == comp_type
                        ]
                    )
                    for comp_type in CompilationType
                },
            }
        except Exception as e:
            logger.error(f"Error getting compilation summary: {e}")
            return {}

    def get_thread_safety_summary(self) -> Dict[str, Any]:
        """Get thread safety summary"""
        try:
            return {
                "deadlock_detections": self.metrics["deadlock_detections"]._value.get()
                or 0,
                "race_condition_detections": self.metrics[
                    "race_condition_detections"
                ]._value.get()
                or 0,
                "total_safety_events": sum(
                    metric._value.get()
                    for metric in self.metrics["thread_safety_events"]._metrics.values()
                ),
            }
        except Exception as e:
            logger.error(f"Error getting thread safety summary: {e}")
            return {}

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get Condon performance summary"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()

            return {
                "memory": {
                    "allocated_bytes": memory_info.rss,
                    "peak_bytes": self.metrics["memory_peak"]._value.get(),
                    "fragmentation_ratio": self.metrics[
                        "memory_fragmentation"
                    ]._value.get(),
                },
                "cpu": {
                    "usage_percent": cpu_percent,
                    "thread_count": threading.active_count(),
                },
                "cache": {
                    "efficiency": {
                        cache_type: self.metrics["cache_efficiency"]
                        .labels(cache_type=cache_type)
                        ._value.get()
                        for cache_type in ["compilation", "optimization", "execution"]
                    }
                },
                "compilation": self.get_compilation_summary(),
                "thread_safety": self.get_thread_safety_summary(),
            }
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}


class CondonServiceMonitor:
    """
    Service-specific Condon monitoring

    Provides monitoring for specific Condon services in the hybrid architecture
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.monitor = CondonMonitor(service_name)
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

        logger.info(f"Initialized Condon service monitor for {service_name}")

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
    def monitor_compilation(
        self, compilation_type: CompilationType, optimization_level: str = "default"
    ):
        """Monitor compilation process"""
        with self.monitor.monitor_compilation(compilation_type, optimization_level):
            yield

    @contextmanager
    def monitor_native_execution(
        self, function_name: str, optimization_level: str = "default"
    ):
        """Monitor native code execution"""
        with self.monitor.monitor_native_execution(function_name, optimization_level):
            yield

    def record_thread_safety_event(
        self, event_type: ThreadSafetyEvent, severity: str = "info"
    ):
        """Record thread safety event"""
        self.monitor.record_thread_safety_event(event_type, severity)

    def get_service_summary(self) -> Dict[str, Any]:
        """Get service-specific summary"""
        return {
            "service_name": self.service_name,
            "performance": self.monitor.get_performance_summary(),
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


# Global Condon monitoring instance
_condon_monitor = None


def get_condon_monitor(service_name: str = "condon-service") -> CondonServiceMonitor:
    """Get Condon service monitor instance"""
    global _condon_monitor
    if _condon_monitor is None:
        _condon_monitor = CondonServiceMonitor(service_name)
    return _condon_monitor


def initialize_condon_monitoring(service_name: str) -> CondonServiceMonitor:
    """Initialize Condon monitoring for a service"""
    monitor = CondonServiceMonitor(service_name)
    monitor.start_monitoring()
    return monitor
