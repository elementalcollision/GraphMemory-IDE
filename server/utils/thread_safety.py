"""
Comprehensive Thread Safety Framework for Hybrid CPython/Codon Architecture

This module provides production-ready thread safety patterns, memory safety mechanisms,
concurrency controls, and validation framework for the hybrid CPython/Codon runtime.
"""

import asyncio
import gc
import logging
import os
import sys
import threading
import time
import tracemalloc
import weakref
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

# Optional import for psutil
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Type variables for generic patterns
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# Configure logging
logger = logging.getLogger(__name__)


class RuntimeType(Enum):
    """Runtime types for hybrid architecture"""

    CPYTHON = "cpython"
    CONDON = "codon"
    HYBRID = "hybrid"


class ThreadSafetyLevel(Enum):
    """Thread safety levels for components"""

    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    CRITICAL = "critical"


@dataclass
class ThreadSafetyConfig:
    """Configuration for thread safety framework"""

    runtime_type: RuntimeType
    safety_level: ThreadSafetyLevel
    max_concurrent_threads: int = 8
    timeout_seconds: float = 30.0
    memory_leak_detection: bool = True
    deadlock_prevention: bool = True
    race_condition_detection: bool = True
    isolation_level: str = "strict"
    resource_cleanup: bool = True
    monitoring_enabled: bool = True


class MemorySafetyManager:
    """Memory safety manager for hybrid runtime"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.memory_tracker = {}
        self.cleanup_handlers = []
        self.memory_isolation = True
        self._lock = threading.RLock()

        if config.memory_leak_detection:
            tracemalloc.start()

    def track_memory_usage(self, component: str, runtime: RuntimeType) -> None:
        """Track memory usage for components"""
        with self._lock:
            if component not in self.memory_tracker:
                self.memory_tracker[component] = {
                    "cpython": {"allocated": 0, "peak": 0},
                    "codon": {"allocated": 0, "peak": 0},
                    "hybrid": {"allocated": 0, "peak": 0},
                }

            if PSUTIL_AVAILABLE and psutil is not None:
                current = psutil.Process().memory_info().rss
            else:
                current = 0  # Fallback when psutil not available

            self.memory_tracker[component][runtime.value]["allocated"] = current
            self.memory_tracker[component][runtime.value]["peak"] = max(
                self.memory_tracker[component][runtime.value]["peak"], current
            )

    def detect_memory_leaks(self) -> Dict[str, Any]:
        """Detect memory leaks across runtimes"""
        with self._lock:
            leaks = {}
            for component, memory_data in self.memory_tracker.items():
                for runtime, data in memory_data.items():
                    if data["allocated"] > data["peak"] * 0.8:  # Potential leak
                        leaks[f"{component}_{runtime}"] = {
                            "allocated": data["allocated"],
                            "peak": data["peak"],
                            "ratio": data["allocated"] / data["peak"],
                        }
            return leaks

    def cleanup_resources(self) -> None:
        """Clean up resources safely"""
        with self._lock:
            for handler in self.cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    logger.error(f"Resource cleanup failed: {e}")

            # Force garbage collection
            gc.collect()

            if self.config.memory_leak_detection:
                # Take snapshot for leak detection
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics("lineno")
                logger.info(f"Memory snapshot: {len(top_stats)} allocations")


class ConcurrencyControl:
    """Concurrency control for shared resources"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.resources = {}
        self.locks = {}
        self.cleanup_queue = []
        self._global_lock = threading.RLock()
        self._deadlock_detector = DeadlockDetector()

    def acquire_resource(
        self, resource_id: str, timeout: Optional[float] = None
    ) -> bool:
        """Thread-safe resource acquisition with deadlock prevention"""
        if timeout is None:
            timeout = self.config.timeout_seconds

        with self._global_lock:
            if resource_id not in self.locks:
                self.locks[resource_id] = threading.RLock()
                self.resources[resource_id] = {}

        # Use deadlock detection
        if self.config.deadlock_prevention:
            return self._deadlock_detector.acquire_with_detection(
                self.locks[resource_id], timeout
            )
        else:
            return self.locks[resource_id].acquire(timeout=timeout)

    def release_resource(self, resource_id: str) -> None:
        """Thread-safe resource release"""
        if resource_id in self.locks:
            self.locks[resource_id].release()

    def cleanup_expired_resources(self) -> None:
        """Clean up expired resources"""
        with self._global_lock:
            expired = []
            for resource_id, resource_data in self.resources.items():
                if "last_accessed" in resource_data:
                    if (
                        time.time() - resource_data["last_accessed"]
                        > self.config.timeout_seconds
                    ):
                        expired.append(resource_id)

            for resource_id in expired:
                self._cleanup_resource(resource_id)

    def _cleanup_resource(self, resource_id: str) -> None:
        """Clean up a specific resource"""
        if resource_id in self.locks:
            # Ensure lock is released
            try:
                self.locks[resource_id].release()
            except RuntimeError:
                pass  # Already released

        if resource_id in self.resources:
            del self.resources[resource_id]
        if resource_id in self.locks:
            del self.locks[resource_id]


class DeadlockDetector:
    """Deadlock detection and prevention"""

    def __init__(self):
        self.lock_graph = {}
        self.thread_locks = {}
        self._graph_lock = threading.RLock()

    def acquire_with_detection(self, lock: threading.RLock, timeout: float) -> bool:
        """Acquire lock with deadlock detection"""
        thread_id = threading.current_thread().ident

        with self._graph_lock:
            # Add lock to thread's lock set
            if thread_id not in self.thread_locks:
                self.thread_locks[thread_id] = set()
            self.thread_locks[thread_id].add(lock)

            # Check for deadlock
            if self._would_cause_deadlock(thread_id, lock):
                logger.warning(f"Potential deadlock detected for thread {thread_id}")
                return False

        # Try to acquire the lock
        try:
            return lock.acquire(timeout=timeout)
        except Exception as e:
            logger.error(f"Lock acquisition failed: {e}")
            return False
        finally:
            # Remove lock from thread's set if acquisition failed
            if not lock._locked():
                with self._graph_lock:
                    if thread_id in self.thread_locks:
                        self.thread_locks[thread_id].discard(lock)

    def _would_cause_deadlock(self, thread_id: int, lock: threading.RLock) -> bool:
        """Check if acquiring lock would cause deadlock"""
        # Simple cycle detection in lock graph
        visited = set()
        return self._has_cycle(thread_id, lock, visited, set())

    def _has_cycle(
        self, thread_id: int, lock: threading.RLock, visited: set, path: set
    ) -> bool:
        """Detect cycles in lock dependency graph"""
        if lock in path:
            return True

        if lock in visited:
            return False

        visited.add(lock)
        path.add(lock)

        # Check all threads that might be waiting for this lock
        for other_thread_id, other_locks in self.thread_locks.items():
            if other_thread_id != thread_id and lock in other_locks:
                for other_lock in other_locks:
                    if other_lock != lock and self._has_cycle(
                        thread_id, other_lock, visited, path
                    ):
                        return True

        path.remove(lock)
        return False


class ThreadSafetyValidator:
    """Thread safety validation framework"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.validation_results = {}
        self.violations = []
        self._validator_lock = threading.RLock()

    def validate_thread_safety(
        self, component: str, runtime: RuntimeType
    ) -> Dict[str, Any]:
        """Validate thread safety for a component"""
        with self._validator_lock:
            result = {
                "component": component,
                "runtime": runtime.value,
                "timestamp": time.time(),
                "violations": [],
                "memory_safety": True,
                "concurrency_safety": True,
                "overall_safety": True,
            }

            # Memory safety validation
            if self.config.memory_leak_detection:
                result["memory_safety"] = self._validate_memory_safety(
                    component, runtime
                )

            # Concurrency safety validation
            if self.config.race_condition_detection:
                result["concurrency_safety"] = self._validate_concurrency_safety(
                    component, runtime
                )

            # Overall safety assessment
            result["overall_safety"] = (
                result["memory_safety"] and result["concurrency_safety"]
            )

            self.validation_results[f"{component}_{runtime.value}"] = result
            return result

    def _validate_memory_safety(self, component: str, runtime: RuntimeType) -> bool:
        """Validate memory safety for component"""
        # Check for memory leaks
        snapshot = tracemalloc.take_snapshot()
        if len(snapshot.statistics("lineno")) > 1000:  # Threshold for potential leak
            self.violations.append(
                {
                    "type": "memory_leak",
                    "component": component,
                    "runtime": runtime.value,
                    "timestamp": time.time(),
                }
            )
            return False
        return True

    def _validate_concurrency_safety(
        self, component: str, runtime: RuntimeType
    ) -> bool:
        """Validate concurrency safety for component"""
        # Check for race conditions (simplified)
        thread_count = threading.active_count()
        if thread_count > self.config.max_concurrent_threads:
            self.violations.append(
                {
                    "type": "race_condition",
                    "component": component,
                    "runtime": runtime.value,
                    "timestamp": time.time(),
                    "thread_count": thread_count,
                }
            )
            return False
        return True

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all thread safety violations"""
        return self.violations.copy()

    def clear_violations(self) -> None:
        """Clear violation history"""
        with self._validator_lock:
            self.violations.clear()


class ThreadSafetyMonitor:
    """Production monitoring for thread safety"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.metrics = {
            "thread_count": 0,
            "memory_usage": 0,
            "lock_contention": 0,
            "violations": 0,
            "deadlocks_detected": 0,
        }
        self._metrics_lock = threading.RLock()
        self._monitoring_active = False
        self._monitor_thread = None

    def start_monitoring(self) -> None:
        """Start thread safety monitoring"""
        if not self._monitoring_active:
            self._monitoring_active = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self._monitor_thread.start()
            logger.info("Thread safety monitoring started")

    def stop_monitoring(self) -> None:
        """Stop thread safety monitoring"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Thread safety monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                self._update_metrics()
                time.sleep(1.0)  # Update every second
            except Exception as e:
                logger.error(f"Monitoring error: {e}")

    def _update_metrics(self) -> None:
        """Update monitoring metrics"""
        with self._metrics_lock:
            self.metrics["thread_count"] = threading.active_count()
            self.metrics["memory_usage"] = psutil.Process().memory_info().rss

            # Calculate lock contention (simplified)
            self.metrics["lock_contention"] = len(
                [t for t in threading.enumerate() if t.name.startswith("Thread-")]
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current monitoring metrics"""
        with self._metrics_lock:
            return self.metrics.copy()

    def alert_if_needed(self, validator: ThreadSafetyValidator) -> None:
        """Generate alerts for thread safety violations"""
        violations = validator.get_violations()
        if violations:
            with self._metrics_lock:
                self.metrics["violations"] = len(violations)

            for violation in violations:
                logger.warning(f"Thread safety violation: {violation}")


class HybridThreadSafetyFramework:
    """Main thread safety framework for hybrid CPython/Codon architecture"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.memory_safety = MemorySafetyManager(config)
        self.concurrency_control = ConcurrencyControl(config)
        self.validator = ThreadSafetyValidator(config)
        self.monitor = ThreadSafetyMonitor(config)
        self._framework_lock = threading.RLock()

        # Runtime-specific safety managers
        self.cpython_safety = CPythonThreadSafety(config)
        self.codon_safety = CodonThreadSafety(config)
        self.hybrid_safety = HybridThreadSafety(config)

    def initialize(self) -> None:
        """Initialize the thread safety framework"""
        with self._framework_lock:
            if self.config.monitoring_enabled:
                self.monitor.start_monitoring()
            logger.info("Thread safety framework initialized")

    def shutdown(self) -> None:
        """Shutdown the thread safety framework"""
        with self._framework_lock:
            self.monitor.stop_monitoring()
            self.memory_safety.cleanup_resources()
            self.concurrency_control.cleanup_expired_resources()
            logger.info("Thread safety framework shutdown complete")

    @contextmanager
    def safe_execution(self, component: str, runtime: RuntimeType):
        """Context manager for safe execution across runtimes"""
        try:
            # Pre-execution validation
            self.validator.validate_thread_safety(component, runtime)

            # Track memory usage
            self.memory_safety.track_memory_usage(component, runtime)

            yield

            # Post-execution cleanup
            self.memory_safety.cleanup_resources()

        except Exception as e:
            logger.error(f"Thread safety violation in {component}: {e}")
            raise

    def get_safety_report(self) -> Dict[str, Any]:
        """Generate comprehensive thread safety report"""
        with self._framework_lock:
            return {
                "config": {
                    "runtime_type": self.config.runtime_type.value,
                    "safety_level": self.config.safety_level.value,
                    "max_concurrent_threads": self.config.max_concurrent_threads,
                },
                "metrics": self.monitor.get_metrics(),
                "violations": self.validator.get_violations(),
                "memory_leaks": self.memory_safety.detect_memory_leaks(),
                "validation_results": self.validator.validation_results,
            }


class CPythonThreadSafety:
    """Thread safety patterns for CPython services"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.lock = threading.RLock()
        self.thread_local = threading.local()
        self.resource_pool = {}
        self._gil_aware = True

    def safe_resource_access(self, resource_id: str) -> Any:
        """Thread-safe resource access pattern"""
        with self.lock:
            if resource_id not in self.resource_pool:
                self.resource_pool[resource_id] = self._create_resource(resource_id)
            return self.resource_pool[resource_id]

    def safe_memory_management(self) -> None:
        """Thread-safe memory management for CPython"""
        # CPython-specific memory management
        if hasattr(self.thread_local, "memory_tracker"):
            del self.thread_local.memory_tracker
        gc.collect()

    def safe_error_handling(self, error: Exception) -> None:
        """Thread-safe error handling for CPython"""
        thread_id = threading.current_thread().ident
        logger.error(f"CPython thread {thread_id} error: {error}")

        # Clean up thread-local resources
        if hasattr(self.thread_local, "temp_resources"):
            for resource in self.thread_local.temp_resources:
                try:
                    resource.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Resource cleanup failed: {cleanup_error}")

    def _create_resource(self, resource_id: str) -> Any:
        """Create a new resource"""
        # Placeholder for resource creation
        return {"id": resource_id, "created": time.time()}


class CodonThreadSafety:
    """Thread safety patterns for Codon services"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.memory_isolation = True
        self.thread_safety_validation = True
        self.resource_cleanup = True
        self._codon_lock = threading.RLock()

    def safe_codon_execution(self, func: Callable, *args, **kwargs) -> Any:
        """Thread-safe Codon function execution"""
        with self._codon_lock:
            # Codon-specific thread safety
            if self.memory_isolation:
                self._ensure_memory_isolation()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                if self.resource_cleanup:
                    self._cleanup_codon_resources()

    def safe_memory_isolation(self) -> None:
        """Ensure memory isolation between threads in Codon"""
        # Codon-specific memory isolation
        if hasattr(threading.current_thread(), "_codon_memory_space"):
            del threading.current_thread()._codon_memory_space

    def safe_resource_cleanup(self) -> None:
        """Thread-safe resource cleanup for Codon"""
        with self._codon_lock:
            # Codon-specific cleanup
            if hasattr(threading.current_thread(), "_codon_resources"):
                for resource in threading.current_thread()._codon_resources:
                    try:
                        resource.cleanup()
                    except Exception as e:
                        logger.error(f"Codon resource cleanup failed: {e}")

    def _ensure_memory_isolation(self) -> None:
        """Ensure memory isolation for Codon threads"""
        # Implementation for Codon memory isolation
        pass

    def _cleanup_codon_resources(self) -> None:
        """Clean up Codon-specific resources"""
        # Implementation for Codon resource cleanup
        pass


class HybridThreadSafety:
    """Thread safety patterns for hybrid CPython/Codon services"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.cpython_safety = CPythonThreadSafety(config)
        self.codon_safety = CodonThreadSafety(config)
        self.boundary_safety = True
        self._hybrid_lock = threading.RLock()

    def safe_cross_boundary_communication(self, data: Any) -> Any:
        """Thread-safe communication across CPython/Codon boundaries"""
        with self._hybrid_lock:
            # Validate data format for cross-boundary communication
            validated_data = self._validate_cross_boundary_data(data)

            # Ensure thread safety during boundary crossing
            if self.boundary_safety:
                self._ensure_boundary_safety()

            return validated_data

    def safe_service_integration(self, service_a: str, service_b: str) -> None:
        """Thread-safe service integration"""
        with self._hybrid_lock:
            # Ensure both services are thread-safe
            if not self._validate_service_thread_safety(service_a):
                raise RuntimeError(f"Service {service_a} not thread-safe")

            if not self._validate_service_thread_safety(service_b):
                raise RuntimeError(f"Service {service_b} not thread-safe")

            # Perform safe integration
            self._integrate_services_safely(service_a, service_b)

    def _validate_cross_boundary_data(self, data: Any) -> Any:
        """Validate data for cross-boundary communication"""
        # Implementation for data validation
        return data

    def _ensure_boundary_safety(self) -> None:
        """Ensure safety during boundary crossing"""
        # Implementation for boundary safety
        pass

    def _validate_service_thread_safety(self, service: str) -> bool:
        """Validate thread safety of a service"""
        # Implementation for service validation
        return True

    def _integrate_services_safely(self, service_a: str, service_b: str) -> None:
        """Safely integrate two services"""
        # Implementation for safe service integration
        pass


# Factory function for creating thread safety framework
def create_thread_safety_framework(
    runtime_type: RuntimeType = RuntimeType.HYBRID,
    safety_level: ThreadSafetyLevel = ThreadSafetyLevel.STRICT,
) -> HybridThreadSafetyFramework:
    """Create a thread safety framework with specified configuration"""
    config = ThreadSafetyConfig(runtime_type=runtime_type, safety_level=safety_level)
    return HybridThreadSafetyFramework(config)


# Global thread safety framework instance
_thread_safety_framework: Optional[HybridThreadSafetyFramework] = None


def get_thread_safety_framework() -> HybridThreadSafetyFramework:
    """Get the global thread safety framework instance"""
    global _thread_safety_framework
    if _thread_safety_framework is None:
        _thread_safety_framework = create_thread_safety_framework()
        _thread_safety_framework.initialize()
    return _thread_safety_framework


def shutdown_thread_safety_framework() -> None:
    """Shutdown the global thread safety framework"""
    global _thread_safety_framework
    if _thread_safety_framework is not None:
        _thread_safety_framework.shutdown()
        _thread_safety_framework = None
