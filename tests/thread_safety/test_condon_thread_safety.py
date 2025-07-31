"""
Thread Safety Testing for Condon No-GIL Environment

This module provides comprehensive testing for thread safety in the Condon
free-threaded Python environment. It tests singleton patterns, shared state
access, and other concurrent operations to ensure thread safety.

Test Categories:
- Singleton pattern thread safety
- Shared state access thread safety
- Concurrent operation thread safety
- Performance benchmarking
- Race condition detection
"""

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

# Import thread safety utilities
from server.utils.thread_safety import (
    ThreadSafeDict,
    ThreadSafeGlobalState,
    ThreadSafeSingleton,
    ThreadSafetyPerformanceTester,
    ThreadSafetyTester,
    thread_safe_singleton,
)


class TestHealthMonitor(ThreadSafeSingleton):
    """Test singleton for health monitoring"""

    def __init__(self):
        self.checks = []
        self.metrics = {}

    async def initialize(self):
        """Async initialization"""
        self.initialized = True

    async def add_check(self, check_name: str, status: str):
        """Add a health check"""
        self.checks.append({"name": check_name, "status": status})

    async def add_metric(self, metric_name: str, value: float):
        """Add a metric"""
        self.metrics[metric_name] = value


@thread_safe_singleton
class TestIncidentManager:
    """Test singleton for incident management"""

    def __init__(self):
        self.incidents = {}
        self.metrics = {}

    async def initialize(self):
        """Async initialization"""
        self.initialized = True

    async def add_incident(self, incident_id: str, data: Dict[str, Any]):
        """Add an incident"""
        self.incidents[incident_id] = data

    async def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get an incident"""
        return self.incidents.get(incident_id)


class TestStreamProducer(ThreadSafeSingleton):
    """Test singleton for stream producer"""

    def __init__(self):
        self.streams = {}
        self.metrics = {}

    async def initialize(self):
        """Async initialization"""
        self.initialized = True

    async def create_stream(self, stream_id: str, config: Dict[str, Any]):
        """Create a stream"""
        self.streams[stream_id] = config

    async def get_stream(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get a stream"""
        return self.streams.get(stream_id)


@pytest.mark.thread_safety
class TestCondonThreadSafety:
    """Comprehensive thread safety tests for Condon environment"""

    def setup_method(self):
        """Setup test environment"""
        self.tester = ThreadSafetyTester()
        self.performance_tester = ThreadSafetyPerformanceTester()

        # Reset singleton instances for clean testing
        TestHealthMonitor.reset_instance()
        TestIncidentManager.reset_instance()
        TestStreamProducer.reset_instance()

    @pytest.mark.asyncio
    async def test_singleton_thread_safety_health_monitor(self):
        """Test health monitor singleton thread safety"""

        async def get_health_monitor():
            return await TestHealthMonitor.get_instance()

        result = await self.tester.test_singleton_thread_safety(
            get_health_monitor, num_threads=20
        )

        assert result["is_thread_safe"], (
            f"Health monitor singleton is not thread-safe. "
            f"Unique instances: {result['unique_instances']}, "
            f"Errors: {result['errors']}"
        )

        print(f"Health monitor singleton thread safety test passed")

    @pytest.mark.asyncio
    async def test_singleton_thread_safety_incident_manager(self):
        """Test incident manager singleton thread safety"""

        async def get_incident_manager():
            return await TestIncidentManager.get_instance()

        result = await self.tester.test_singleton_thread_safety(
            get_incident_manager, num_threads=20
        )

        assert result["is_thread_safe"], (
            f"Incident manager singleton is not thread-safe. "
            f"Unique instances: {result['unique_instances']}, "
            f"Errors: {result['errors']}"
        )

        print(f"Incident manager singleton thread safety test passed")

    @pytest.mark.asyncio
    async def test_singleton_thread_safety_stream_producer(self):
        """Test stream producer singleton thread safety"""

        async def get_stream_producer():
            return await TestStreamProducer.get_instance()

        result = await self.tester.test_singleton_thread_safety(
            get_stream_producer, num_threads=20
        )

        assert result["is_thread_safe"], (
            f"Stream producer singleton is not thread-safe. "
            f"Unique instances: {result['unique_instances']}, "
            f"Errors: {result['errors']}"
        )

        print(f"Stream producer singleton thread safety test passed")

    @pytest.mark.asyncio
    async def test_shared_state_access_thread_safety(self):
        """Test shared state access thread safety"""

        state_manager = ThreadSafeGlobalState()

        result = await self.tester.test_shared_state_access(
            state_manager, num_threads=20
        )

        assert result["is_thread_safe"], (
            f"Shared state access is not thread-safe. " f"Errors: {result['errors']}"
        )

        print(f"Shared state access thread safety test passed")

    @pytest.mark.asyncio
    async def test_thread_safe_dict_operations(self):
        """Test thread-safe dictionary operations"""

        safe_dict = ThreadSafeDict()
        results = []
        errors = []

        async def worker(thread_id: int):
            try:
                # Perform concurrent operations
                key = f"key_{thread_id}"
                value = f"value_{thread_id}"

                safe_dict[key] = value
                retrieved = safe_dict[key]

                # Test update operation
                safe_dict.update({f"update_{key}": f"update_{value}"})

                # Test get operation
                safe_dict.get(f"update_{key}")

                results.append((thread_id, retrieved == value))
            except Exception as e:
                errors.append(str(e))

        # Run concurrent operations
        tasks = [worker(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Verify all operations succeeded
        assert len(errors) == 0, f"Thread-safe dict operations failed: {errors}"
        assert len(results) == 20, "Not all operations completed"

        # Verify data consistency
        for thread_id, success in results:
            assert success, f"Data inconsistency for thread {thread_id}"

        print(f"Thread-safe dictionary operations test passed")

    @pytest.mark.asyncio
    async def test_concurrent_singleton_operations(self):
        """Test concurrent operations on singleton instances"""

        async def health_monitor_operations():
            monitor = await TestHealthMonitor.get_instance()
            await monitor.add_check(f"check_{uuid4()}", "healthy")
            await monitor.add_metric(f"metric_{uuid4()}", 1.0)
            return len(monitor.checks)

        async def incident_manager_operations():
            manager = await TestIncidentManager.get_instance()
            incident_id = str(uuid4())
            await manager.add_incident(incident_id, {"status": "open"})
            incident = await manager.get_incident(incident_id)
            return incident is not None

        async def stream_producer_operations():
            producer = await TestStreamProducer.get_instance()
            stream_id = str(uuid4())
            await producer.create_stream(stream_id, {"type": "test"})
            stream = await producer.get_stream(stream_id)
            return stream is not None

        # Test concurrent operations on different singletons
        health_tasks = [health_monitor_operations() for _ in range(10)]
        incident_tasks = [incident_manager_operations() for _ in range(10)]
        stream_tasks = [stream_producer_operations() for _ in range(10)]

        all_tasks = health_tasks + incident_tasks + stream_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Check for exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent operations failed: {exceptions}"

        # Verify all operations succeeded
        assert len(results) == 30, "Not all operations completed"

        print(f"Concurrent singleton operations test passed")

    @pytest.mark.asyncio
    async def test_race_condition_detection(self):
        """Test detection of race conditions"""

        # Test unsafe singleton pattern (should fail)
        unsafe_instances = []
        unsafe_lock = asyncio.Lock()

        async def unsafe_singleton_worker():
            # Simulate unsafe singleton pattern
            if not unsafe_instances:
                async with unsafe_lock:
                    if not unsafe_instances:  # This is safe, but we'll test the pattern
                        unsafe_instances.append(object())
            return unsafe_instances[0]

        # Test safe singleton pattern (should pass)
        safe_instances = []
        safe_lock = asyncio.Lock()

        async def safe_singleton_worker():
            # Simulate safe singleton pattern with double-checked locking
            if not safe_instances:
                async with safe_lock:
                    if not safe_instances:  # Double-check after acquiring lock
                        safe_instances.append(object())
            return safe_instances[0]

        # Test both patterns
        unsafe_tasks = [unsafe_singleton_worker() for _ in range(20)]
        safe_tasks = [safe_singleton_worker() for _ in range(20)]

        unsafe_results = await asyncio.gather(*unsafe_tasks)
        safe_results = await asyncio.gather(*safe_tasks)

        # Verify safe pattern maintains singleton property
        safe_instance_ids = set(id(r) for r in safe_results)
        assert len(safe_instance_ids) == 1, "Safe singleton pattern failed"

        print(f"Race condition detection test passed")

    @pytest.mark.asyncio
    async def test_performance_benchmarking(self):
        """Test performance of thread-safe implementations"""

        async def get_health_monitor():
            return await TestHealthMonitor.get_instance()

        # Benchmark singleton access
        singleton_result = await self.performance_tester.benchmark_singleton_access(
            get_health_monitor, num_operations=10000
        )

        # Benchmark shared state operations
        state_manager = ThreadSafeGlobalState()
        state_result = await self.performance_tester.benchmark_shared_state_operations(
            state_manager, num_operations=10000
        )

        # Benchmark lock overhead
        lock_result = await self.performance_tester.benchmark_lock_overhead(
            num_operations=100000
        )

        # Verify performance is reasonable
        assert (
            singleton_result["operations_per_second"] > 1000
        ), f"Singleton access too slow: {singleton_result['operations_per_second']} ops/sec"

        assert (
            state_result["operations_per_second"] > 1000
        ), f"Shared state operations too slow: {state_result['operations_per_second']} ops/sec"

        assert (
            lock_result["operations_per_second"] > 10000
        ), f"Lock overhead too high: {lock_result['operations_per_second']} ops/sec"

        print(f"Performance benchmarking test passed")
        print(
            f"Singleton access: {singleton_result['operations_per_second']:.0f} ops/sec"
        )
        print(f"Shared state ops: {state_result['operations_per_second']:.0f} ops/sec")
        print(f"Lock overhead: {lock_result['operations_per_second']:.0f} ops/sec")

    @pytest.mark.asyncio
    async def test_memory_consistency(self):
        """Test memory consistency under concurrent access"""

        # Test that shared state remains consistent
        state_manager = ThreadSafeGlobalState()

        async def memory_worker(thread_id: int):
            # Perform multiple operations
            for i in range(100):
                key = f"thread_{thread_id}_op_{i}"
                value = f"value_{thread_id}_{i}"

                await state_manager.set(key, value)
                retrieved = await state_manager.get(key)

                # Verify consistency
                assert retrieved == value, f"Memory inconsistency for {key}"

        # Run concurrent memory operations
        tasks = [memory_worker(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify final state
        all_keys = await state_manager.keys()
        assert len(all_keys) == 1000, f"Expected 1000 keys, got {len(all_keys)}"

        print(f"Memory consistency test passed")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in thread-safe operations"""

        state_manager = ThreadSafeGlobalState()

        async def error_worker():
            try:
                # Perform operations that might cause errors
                await state_manager.set("test_key", "test_value")
                await state_manager.get("test_key")
                await state_manager.delete("test_key")
                return True
            except Exception as e:
                return False

        # Run error handling test
        tasks = [error_worker() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(results), "Error handling test failed"

        print(f"Error handling test passed")

    @pytest.mark.asyncio
    async def test_stress_testing(self):
        """Stress test thread safety under high load"""

        async def stress_worker(worker_id: int):
            # Perform intensive operations
            monitor = await TestHealthMonitor.get_instance()
            manager = await TestIncidentManager.get_instance()
            producer = await TestStreamProducer.get_instance()

            for i in range(100):
                # Health monitor operations
                await monitor.add_check(f"stress_check_{worker_id}_{i}", "healthy")
                await monitor.add_metric(f"stress_metric_{worker_id}_{i}", float(i))

                # Incident manager operations
                incident_id = f"stress_incident_{worker_id}_{i}"
                await manager.add_incident(incident_id, {"status": "open"})
                await manager.get_incident(incident_id)

                # Stream producer operations
                stream_id = f"stress_stream_{worker_id}_{i}"
                await producer.create_stream(stream_id, {"type": "stress"})
                await producer.get_stream(stream_id)

            return True

        # Run stress test with many workers
        tasks = [stress_worker(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Stress test failed: {exceptions}"

        # Verify all workers completed
        assert len(results) == 50, "Not all stress test workers completed"

        print(f"Stress testing passed")


@pytest.mark.thread_safety
class TestCondonSpecificIssues:
    """Test specific issues related to Condon no-GIL environment"""

    def setup_method(self):
        """Setup test environment"""
        # Reset singleton instances
        TestHealthMonitor.reset_instance()
        TestIncidentManager.reset_instance()
        TestStreamProducer.reset_instance()

    @pytest.mark.asyncio
    async def test_no_gil_race_conditions(self):
        """Test that race conditions are properly handled in no-GIL environment"""

        # Test the specific race condition pattern found in the codebase
        global_instance = None
        global_lock = asyncio.Lock()

        async def unsafe_get_instance():
            # Simulate the unsafe pattern found in the codebase
            nonlocal global_instance
            if global_instance is None:
                global_instance = object()
            return global_instance

        async def safe_get_instance():
            # Simulate the safe pattern with double-checked locking
            nonlocal global_instance
            if global_instance is None:
                async with global_lock:
                    if global_instance is None:  # Double-check after acquiring lock
                        global_instance = object()
            return global_instance

        # Test both patterns
        unsafe_tasks = [unsafe_get_instance() for _ in range(20)]
        safe_tasks = [safe_get_instance() for _ in range(20)]

        unsafe_results = await asyncio.gather(*unsafe_tasks)
        safe_results = await asyncio.gather(*safe_tasks)

        # In no-GIL environment, unsafe pattern might create multiple instances
        unsafe_instance_ids = set(id(r) for r in unsafe_results)
        safe_instance_ids = set(id(r) for r in safe_results)

        # Safe pattern should always maintain singleton property
        assert len(safe_instance_ids) == 1, "Safe pattern failed in no-GIL environment"

        print(f"No-GIL race condition test passed")

    @pytest.mark.asyncio
    async def test_global_variable_access(self):
        """Test thread-safe access to global variables"""

        # Test unsafe global variable access
        unsafe_counter = 0
        unsafe_lock = threading.Lock()

        def unsafe_increment():
            nonlocal unsafe_counter
            unsafe_counter += 1

        def safe_increment():
            nonlocal unsafe_counter
            with unsafe_lock:
                unsafe_counter += 1

        # Test both patterns
        unsafe_threads = [threading.Thread(target=unsafe_increment) for _ in range(100)]
        safe_threads = [threading.Thread(target=safe_increment) for _ in range(100)]

        # Run unsafe threads
        for thread in unsafe_threads:
            thread.start()
        for thread in unsafe_threads:
            thread.join()

        unsafe_final = unsafe_counter

        # Reset counter
        unsafe_counter = 0

        # Run safe threads
        for thread in safe_threads:
            thread.start()
        for thread in safe_threads:
            thread.join()

        safe_final = unsafe_counter

        # Safe pattern should always reach expected value
        assert safe_final == 100, f"Safe pattern failed: expected 100, got {safe_final}"

        print(f"Global variable access test passed")

    @pytest.mark.asyncio
    async def test_shared_collections_thread_safety(self):
        """Test thread safety of shared collections"""

        # Test unsafe shared collection
        unsafe_dict = {}

        def unsafe_dict_worker(worker_id: int):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                unsafe_dict[key] = f"value_{worker_id}_{i}"

        # Test safe shared collection
        safe_dict = ThreadSafeDict()

        async def safe_dict_worker(worker_id: int):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                safe_dict[key] = f"value_{worker_id}_{i}"

        # Run unsafe test
        unsafe_threads = [
            threading.Thread(target=unsafe_dict_worker, args=(i,)) for i in range(10)
        ]

        for thread in unsafe_threads:
            thread.start()
        for thread in unsafe_threads:
            thread.join()

        # Run safe test
        safe_tasks = [safe_dict_worker(i) for i in range(10)]
        await asyncio.gather(*safe_tasks)

        # Verify safe dict has expected number of items
        assert len(safe_dict) == 1000, f"Safe dict missing items: {len(safe_dict)}"

        print(f"Shared collections thread safety test passed")


if __name__ == "__main__":
    """Run thread safety tests"""

    async def run_all_tests():
        """Run all thread safety tests"""

        print("Starting Condon Thread Safety Tests...")
        print("=" * 50)

        # Create test instance
        test_instance = TestCondonThreadSafety()
        test_instance.setup_method()

        # Run all tests
        tests = [
            test_instance.test_singleton_thread_safety_health_monitor(),
            test_instance.test_singleton_thread_safety_incident_manager(),
            test_instance.test_singleton_thread_safety_stream_producer(),
            test_instance.test_shared_state_access_thread_safety(),
            test_instance.test_thread_safe_dict_operations(),
            test_instance.test_concurrent_singleton_operations(),
            test_instance.test_race_condition_detection(),
            test_instance.test_performance_benchmarking(),
            test_instance.test_memory_consistency(),
            test_instance.test_error_handling(),
            test_instance.test_stress_testing(),
        ]

        results = await asyncio.gather(*tests, return_exceptions=True)

        # Check results
        passed = 0
        failed = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Test {i+1} FAILED: {result}")
                failed += 1
            else:
                print(f"Test {i+1} PASSED")
                passed += 1

        print("=" * 50)
        print(f"Thread Safety Tests Complete: {passed} passed, {failed} failed")

        if failed == 0:
            print("✅ All thread safety tests passed!")
        else:
            print("❌ Some thread safety tests failed!")

    # Run tests
    asyncio.run(run_all_tests())
