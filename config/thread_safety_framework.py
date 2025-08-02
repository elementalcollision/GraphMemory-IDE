"""
Thread Safety Framework for GraphMemory-IDE

This module defines comprehensive thread safety patterns and requirements
for components running on both CPython and Codon runtimes, ensuring
safe concurrent operations and memory management.

Based on Task 3-B requirements and industry best practices.
"""

import asyncio
import logging
import queue
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ThreadSafetyLevel(Enum):
    """Thread safety levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LockType(Enum):
    """Types of locks for different scenarios"""

    MUTEX = "mutex"
    READ_WRITE = "read_write"
    SEMAPHORE = "semaphore"
    SPIN_LOCK = "spin_lock"


@dataclass
class ThreadSafetyConfig:
    """Thread safety configuration for components"""

    level: ThreadSafetyLevel
    max_concurrent_operations: int = 10
    lock_timeout_seconds: float = 30.0
    deadlock_detection_enabled: bool = True
    memory_safety_checks: bool = True
    performance_isolation: bool = True
    error_recovery_enabled: bool = True


@dataclass
class LockInfo:
    """Information about a lock"""

    lock_id: str
    lock_type: LockType
    acquired_at: Optional[float] = None
    timeout_seconds: float = 30.0
    owner_thread: Optional[int] = None


class DeadlockDetector:
    """Detects and prevents deadlocks"""

    def __init__(self):
        self.lock_graph: Dict[str, List[str]] = {}
        self.thread_locks: Dict[int, List[str]] = {}
        self.lock_owners: Dict[str, int] = {}

    def add_lock_dependency(
        self, thread_id: int, lock_id: str, dependency_lock_id: str
    ) -> bool:
        """Add a lock dependency and check for deadlock"""
        if thread_id not in self.thread_locks:
            self.thread_locks[thread_id] = []

        self.thread_locks[thread_id].append(lock_id)
        self.lock_owners[lock_id] = thread_id

        # Check for deadlock
        if self._has_deadlock():
            logger.warning(f"Deadlock detected for thread {thread_id}")
            return False

        return True

    def _has_deadlock(self) -> bool:
        """Check if there's a deadlock in the lock graph"""
        # Simple cycle detection
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.lock_graph.get(node, []):
                if has_cycle(neighbor):
                    return True

            rec_stack.remove(node)
            return False

        for lock_id in self.lock_graph:
            if lock_id not in visited:
                if has_cycle(lock_id):
                    return True

        return False

    def release_lock(self, thread_id: int, lock_id: str) -> None:
        """Release a lock and update the graph"""
        if thread_id in self.thread_locks:
            if lock_id in self.thread_locks[thread_id]:
                self.thread_locks[thread_id].remove(lock_id)

        if lock_id in self.lock_owners:
            del self.lock_owners[lock_id]


class ThreadSafeResource:
    """Base class for thread-safe resources"""

    def __init__(self, resource_id: str, config: ThreadSafetyConfig):
        self.resource_id = resource_id
        self.config = config
        self.lock = threading.RLock()
        self.deadlock_detector = DeadlockDetector()
        self.operation_count = 0
        self.error_count = 0

    @contextmanager
    def acquire(self, timeout: Optional[float] = None):
        """Context manager for acquiring the resource"""
        timeout = timeout or self.config.lock_timeout_seconds
        thread_id = threading.get_ident()

        try:
            if self.lock.acquire(timeout=timeout):
                self.operation_count += 1
                yield self
            else:
                raise TimeoutError(f"Failed to acquire lock for {self.resource_id}")
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error in thread-safe operation: {e}")
            raise
        finally:
            if self.lock.locked():
                self.lock.release()


class ThreadSafeCache:
    """Thread-safe cache implementation"""

    def __init__(self, max_size: int = 1000, config: ThreadSafetyConfig = None):
        self.max_size = max_size
        self.config = config or ThreadSafetyConfig(ThreadSafetyLevel.HIGH)
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()

    def get(self, key: str, default: Any = None) -> Any:
        """Thread-safe get operation"""
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return default

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Thread-safe set operation"""
        with self.lock:
            # Evict if necessary
            if len(self.cache) >= self.max_size:
                self._evict_oldest()

            self.cache[key] = value
            self.access_times[key] = time.time()

    def _evict_oldest(self) -> None:
        """Evict the oldest entry"""
        if not self.access_times:
            return

        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]


class ThreadSafeQueue:
    """Thread-safe queue implementation"""

    def __init__(self, maxsize: int = 1000, config: ThreadSafetyConfig = None):
        self.maxsize = maxsize
        self.config = config or ThreadSafetyConfig(ThreadSafetyLevel.HIGH)
        self.queue = queue.Queue(maxsize=maxsize)
        self.stats = {"put_count": 0, "get_count": 0, "error_count": 0}

    def put(self, item: Any, timeout: Optional[float] = None) -> None:
        """Thread-safe put operation"""
        try:
            self.queue.put(item, timeout=timeout)
            self.stats["put_count"] += 1
        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"Error in queue put operation: {e}")
            raise

    def get(self, timeout: Optional[float] = None) -> Any:
        """Thread-safe get operation"""
        try:
            item = self.queue.get(timeout=timeout)
            self.stats["get_count"] += 1
            return item
        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"Error in queue get operation: {e}")
            raise


class CPythonThreadSafety:
    """Thread safety patterns for CPython runtime"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.gil_aware = True  # CPython has GIL
        self.resources: Dict[str, ThreadSafeResource] = {}
        self.caches: Dict[str, ThreadSafeCache] = {}
        self.queues: Dict[str, ThreadSafeQueue] = {}

    def create_resource(self, resource_id: str) -> ThreadSafeResource:
        """Create a thread-safe resource"""
        resource = ThreadSafeResource(resource_id, self.config)
        self.resources[resource_id] = resource
        return resource

    def create_cache(self, cache_id: str, max_size: int = 1000) -> ThreadSafeCache:
        """Create a thread-safe cache"""
        cache = ThreadSafeCache(max_size, self.config)
        self.caches[cache_id] = cache
        return cache

    def create_queue(self, queue_id: str, maxsize: int = 1000) -> ThreadSafeQueue:
        """Create a thread-safe queue"""
        queue = ThreadSafeQueue(maxsize, self.config)
        self.queues[queue_id] = queue
        return queue

    @contextmanager
    def gil_aware_operation(self):
        """Context manager for GIL-aware operations"""
        # In CPython, the GIL ensures thread safety for most operations
        # This is mainly for documentation and consistency
        yield

    def execute_with_timeout(self, func: Callable, timeout: float) -> Any:
        """Execute function with timeout"""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Operation timed out")

        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            result = func()
            signal.alarm(0)  # Cancel timeout
            return result
        finally:
            signal.signal(signal.SIGALRM, old_handler)


class CodonThreadSafety:
    """Thread safety patterns for Codon runtime"""

    def __init__(self, config: ThreadSafetyConfig):
        self.config = config
        self.gil_aware = False  # Codon has no GIL
        self.resources: Dict[str, ThreadSafeResource] = {}
        self.caches: Dict[str, ThreadSafeCache] = {}
        self.queues: Dict[str, ThreadSafeQueue] = {}
        self.thread_pool = ThreadPoolExecutor(
            max_workers=config.max_concurrent_operations
        )

    def create_resource(self, resource_id: str) -> ThreadSafeResource:
        """Create a thread-safe resource for Codon"""
        resource = ThreadSafeResource(resource_id, self.config)
        self.resources[resource_id] = resource
        return resource

    def create_cache(self, cache_id: str, max_size: int = 1000) -> ThreadSafeCache:
        """Create a thread-safe cache for Codon"""
        cache = ThreadSafeCache(max_size, self.config)
        self.caches[cache_id] = cache
        return cache

    def create_queue(self, queue_id: str, maxsize: int = 1000) -> ThreadSafeQueue:
        """Create a thread-safe queue for Codon"""
        queue = ThreadSafeQueue(maxsize, self.config)
        self.queues[queue_id] = queue
        return queue

    async def execute_concurrent(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function concurrently in Codon"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)

    def memory_safety_check(self, operation: str) -> bool:
        """Perform memory safety checks for Codon operations"""
        if not self.config.memory_safety_checks:
            return True

        # Placeholder for memory safety checks
        # In practice, this would check for memory leaks, buffer overflows, etc.
        return True


class HybridThreadSafety:
    """Thread safety patterns for hybrid components"""

    def __init__(
        self, cpython_config: ThreadSafetyConfig, codon_config: ThreadSafetyConfig
    ):
        self.cpython_safety = CPythonThreadSafety(cpython_config)
        self.codon_safety = CodonThreadSafety(codon_config)
        self.cross_runtime_locks: Dict[str, threading.Lock] = {}

    def create_cross_runtime_lock(self, lock_id: str) -> threading.Lock:
        """Create a lock that works across both runtimes"""
        if lock_id not in self.cross_runtime_locks:
            self.cross_runtime_locks[lock_id] = threading.Lock()
        return self.cross_runtime_locks[lock_id]

    @contextmanager
    def cross_runtime_operation(self, lock_id: str):
        """Context manager for cross-runtime operations"""
        lock = self.create_cross_runtime_lock(lock_id)

        try:
            with lock:
                yield
        except Exception as e:
            logger.error(f"Cross-runtime operation failed: {e}")
            raise

    async def execute_hybrid_operation(
        self, cpython_func: Callable, codon_func: Callable, data: Any
    ) -> Dict[str, Any]:
        """Execute operation on both runtimes safely"""
        results = {}

        # Execute CPython operation
        try:
            with self.cpython_safety.gil_aware_operation():
                cpython_result = cpython_func(data)
                results["cpython_result"] = cpython_result
        except Exception as e:
            results["cpython_error"] = str(e)

        # Execute Codon operation
try:
    codon_result = await self.codon_safety.execute_concurrent(
        codon_func, data
    )
    results["codon_result"] = codon_result
except Exception as e:
    results["codon_error"] = str(e)

        return results


class ThreadSafetyManager:
    """Main thread safety manager"""

    def __init__(self):
        self.cpython_safety = CPythonThreadSafety(
            ThreadSafetyConfig(ThreadSafetyLevel.HIGH)
        )
        self.codon_safety = CodonThreadSafety(
            ThreadSafetyConfig(ThreadSafetyLevel.CRITICAL)
        )
        self.hybrid_safety = HybridThreadSafety(
            ThreadSafetyConfig(ThreadSafetyLevel.HIGH),
            ThreadSafetyConfig(ThreadSafetyLevel.CRITICAL),
        )
        self.component_safety: Dict[str, Any] = {}

    def get_safety_for_component(
        self, component_name: str, runtime: str
    ) -> Union[CPythonThreadSafety, CodonThreadSafety, HybridThreadSafety]:
        """Get thread safety implementation for component"""
        if component_name in self.component_safety:
            return self.component_safety[component_name]

        if runtime == "cpython":
            safety = self.cpython_safety
        elif runtime == "codon":
            safety = self.codon_safety
        elif runtime == "hybrid":
            safety = self.hybrid_safety
        else:
            raise ValueError(f"Unknown runtime: {runtime}")

        self.component_safety[component_name] = safety
        return safety

    def validate_thread_safety(
        self, component_name: str, operations: List[str]
    ) -> List[str]:
        """Validate thread safety for component operations"""
        issues = []

        # Check for potential race conditions
        for operation in operations:
            if "write" in operation.lower() and "read" in operation.lower():
                issues.append(f"Potential race condition in {operation}")

        # Check for deadlock potential
        if len(operations) > 1:
            issues.append(f"Multiple operations may cause deadlock in {component_name}")

        return issues


# Global thread safety manager
thread_safety_manager = ThreadSafetyManager()


def get_thread_safety_manager() -> ThreadSafetyManager:
    """Get the global thread safety manager"""
    return thread_safety_manager
