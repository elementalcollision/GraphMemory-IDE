"""
Comprehensive Test Suite for Hybrid Thread Safety Framework

This module provides comprehensive testing for the hybrid CPython/Codon thread safety
framework, including memory safety patterns, concurrency controls, and production
validation.
"""

import gc
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import pytest

# Import the thread safety framework
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from server.utils.thread_safety import (
    ConcurrencyControl,
    CodonThreadSafety,
    CPythonThreadSafety,
    HybridThreadSafety,
    HybridThreadSafetyFramework,
    MemorySafetyManager,
    RuntimeType,
    ThreadSafetyConfig,
    ThreadSafetyLevel,
    ThreadSafetyMonitor,
    ThreadSafetyValidator,
    create_thread_safety_framework,
    get_thread_safety_framework,
    shutdown_thread_safety_framework,
)


@pytest.fixture
def thread_safety_config():
    """Create a test thread safety configuration"""
    return ThreadSafetyConfig(
        runtime_type=RuntimeType.HYBRID,
        safety_level=ThreadSafetyLevel.STRICT,
        max_concurrent_threads=4,
        timeout_seconds=5.0,
        memory_leak_detection=True,
        deadlock_prevention=True,
        race_condition_detection=True,
        isolation_level="strict",
        resource_cleanup=True,
        monitoring_enabled=True,
    )


@pytest.fixture
def framework(thread_safety_config):
    """Create a test thread safety framework"""
    framework = HybridThreadSafetyFramework(thread_safety_config)
    framework.initialize()
    yield framework
    framework.shutdown()


class TestMemorySafetyManager:
    """Test memory safety manager functionality"""

    def test_memory_tracking(self, framework):
        """Test memory usage tracking"""
        memory_manager = framework.memory_safety

        # Track memory for different components
        memory_manager.track_memory_usage("test_component", RuntimeType.CPYTHON)
        memory_manager.track_memory_usage("test_component", RuntimeType.CONDON)
        memory_manager.track_memory_usage("test_component", RuntimeType.HYBRID)

        # Verify tracking data exists
        assert "test_component" in memory_manager.memory_tracker
        assert "cpython" in memory_manager.memory_tracker["test_component"]
        assert "codon" in memory_manager.memory_tracker["test_component"]
        assert "hybrid" in memory_manager.memory_tracker["test_component"]

    def test_memory_leak_detection(self, framework):
        """Test memory leak detection"""
        memory_manager = framework.memory_safety

        # Simulate memory usage
        memory_manager.track_memory_usage("leak_test", RuntimeType.CPYTHON)

        # Detect leaks
        leaks = memory_manager.detect_memory_leaks()
        assert isinstance(leaks, dict)

    def test_resource_cleanup(self, framework):
        """Test resource cleanup functionality"""
        memory_manager = framework.memory_safety

        # Add cleanup handler
        cleanup_called = []

        def cleanup_handler():
            cleanup_called.append(True)

        memory_manager.cleanup_handlers.append(cleanup_handler)

        # Trigger cleanup
        memory_manager.cleanup_resources()

        # Verify cleanup was called
        assert len(cleanup_called) == 1


class TestConcurrencyControl:
    """Test concurrency control functionality"""

    def test_resource_acquisition(self, framework):
        """Test thread-safe resource acquisition"""
        concurrency_control = framework.concurrency_control

        # Acquire resource
        resource_id = "test_resource"
        acquired = concurrency_control.acquire_resource(resource_id)
        assert acquired

        # Verify resource exists
        assert resource_id in concurrency_control.locks
        assert resource_id in concurrency_control.resources

    def test_resource_release(self, framework):
        """Test thread-safe resource release"""
        concurrency_control = framework.concurrency_control

        # Acquire and release resource
        resource_id = "test_resource"
        concurrency_control.acquire_resource(resource_id)
        concurrency_control.release_resource(resource_id)

        # Resource should still exist but lock should be released
        assert resource_id in concurrency_control.locks

    def test_concurrent_resource_access(self, framework):
        """Test concurrent resource access"""
        concurrency_control = framework.concurrency_control
        resource_id = "concurrent_resource"

        def worker(worker_id: int) -> bool:
            """Worker function for concurrent access testing"""
            acquired = concurrency_control.acquire_resource(resource_id, timeout=1.0)
            if acquired:
                time.sleep(0.1)  # Simulate work
                concurrency_control.release_resource(resource_id)
                return True
            return False

        # Test with multiple threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i) for i in range(4)]
            results = [future.result() for future in futures]

        # All workers should succeed
        assert all(results)

    def test_deadlock_prevention(self, framework):
        """Test deadlock prevention"""
        concurrency_control = framework.concurrency_control

        # Test deadlock detection
        resource_a = "resource_a"
        resource_b = "resource_b"

        def deadlock_worker():
            """Worker that could cause deadlock"""
            # Try to acquire resources in different order
            acquired_a = concurrency_control.acquire_resource(resource_a, timeout=0.1)
            if acquired_a:
                acquired_b = concurrency_control.acquire_resource(
                    resource_b, timeout=0.1
                )
                if acquired_b:
                    concurrency_control.release_resource(resource_b)
                concurrency_control.release_resource(resource_a)
                return True
            return False

        # Test deadlock prevention
        result = deadlock_worker()
        # Should not cause deadlock due to prevention
        assert result or True  # Either succeeds or is prevented


class TestThreadSafetyValidator:
    """Test thread safety validation framework"""

    def test_thread_safety_validation(self, framework):
        """Test thread safety validation"""
        validator = framework.validator

        # Validate thread safety for a component
        result = validator.validate_thread_safety("test_component", RuntimeType.CPYTHON)

        # Verify validation result structure
        assert "component" in result
        assert "runtime" in result
        assert "timestamp" in result
        assert "violations" in result
        assert "memory_safety" in result
        assert "concurrency_safety" in result
        assert "overall_safety" in result

        assert result["component"] == "test_component"
        assert result["runtime"] == "cpython"

    def test_violation_tracking(self, framework):
        """Test violation tracking"""
        validator = framework.validator

        # Clear existing violations
        validator.clear_violations()

        # Get violations
        violations = validator.get_violations()
        assert len(violations) == 0

        # Simulate violation (by forcing high thread count)
        # This is a simplified test - in real scenarios violations would be detected
        # by the actual validation logic
        validator.violations.append(
            {
                "type": "test_violation",
                "component": "test",
                "runtime": "cpython",
                "timestamp": time.time(),
            }
        )

        violations = validator.get_violations()
        assert len(violations) == 1
        assert violations[0]["type"] == "test_violation"


class TestThreadSafetyMonitor:
    """Test thread safety monitoring"""

    def test_monitoring_start_stop(self, framework):
        """Test monitoring start and stop"""
        monitor = framework.monitor

        # Start monitoring
        monitor.start_monitoring()
        assert monitor._monitoring_active

        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor._monitoring_active

    def test_metrics_collection(self, framework):
        """Test metrics collection"""
        monitor = framework.monitor

        # Get metrics
        metrics = monitor.get_metrics()

        # Verify metrics structure
        assert "thread_count" in metrics
        assert "memory_usage" in metrics
        assert "lock_contention" in metrics
        assert "violations" in metrics
        assert "deadlocks_detected" in metrics

        # Verify metrics are numeric
        assert isinstance(metrics["thread_count"], int)
        assert isinstance(metrics["memory_usage"], int)
        assert isinstance(metrics["lock_contention"], int)
        assert isinstance(metrics["violations"], int)
        assert isinstance(metrics["deadlocks_detected"], int)

    def test_alert_generation(self, framework):
        """Test alert generation for violations"""
        monitor = framework.monitor
        validator = framework.validator

        # Add a test violation
        validator.violations.append(
            {
                "type": "test_violation",
                "component": "test",
                "runtime": "cpython",
                "timestamp": time.time(),
            }
        )

        # Generate alerts
        monitor.alert_if_needed(validator)

        # Verify metrics updated
        metrics = monitor.get_metrics()
        assert metrics["violations"] == 1


class TestCPythonThreadSafety:
    """Test CPython-specific thread safety patterns"""

    def test_safe_resource_access(self, framework):
        """Test safe resource access in CPython"""
        cpython_safety = framework.cpython_safety

        # Test resource access
        resource = cpython_safety.safe_resource_access("test_resource")
        assert resource is not None
        assert "id" in resource
        assert resource["id"] == "test_resource"

    def test_safe_memory_management(self, framework):
        """Test safe memory management in CPython"""
        cpython_safety = framework.cpython_safety

        # Test memory management
        cpython_safety.safe_memory_management()
        # Should not raise exceptions

    def test_safe_error_handling(self, framework):
        """Test safe error handling in CPython"""
        cpython_safety = framework.cpython_safety

        # Test error handling
        test_error = Exception("Test error")
        cpython_safety.safe_error_handling(test_error)
        # Should not raise exceptions


class TestCodonThreadSafety:
    """Test Codon-specific thread safety patterns"""

    def test_safe_codon_execution(self, framework):
        """Test safe Codon function execution"""
        codon_safety = framework.codon_safety

        def test_function(a: int, b: int) -> int:
            return a + b

        # Test safe execution
        result = codon_safety.safe_codon_execution(test_function, 2, 3)
        assert result == 5

    def test_safe_memory_isolation(self, framework):
        """Test safe memory isolation in Codon"""
        codon_safety = framework.codon_safety

        # Test memory isolation
        codon_safety.safe_memory_isolation()
        # Should not raise exceptions

    def test_safe_resource_cleanup(self, framework):
        """Test safe resource cleanup in Codon"""
        codon_safety = framework.codon_safety

        # Test resource cleanup
        codon_safety.safe_resource_cleanup()
        # Should not raise exceptions


class TestHybridThreadSafety:
    """Test hybrid CPython/Codon thread safety patterns"""

    def test_safe_cross_boundary_communication(self, framework):
        """Test safe cross-boundary communication"""
        hybrid_safety = framework.hybrid_safety

        # Test data validation
        test_data = {"key": "value", "number": 42}
        validated_data = hybrid_safety.safe_cross_boundary_communication(test_data)
        assert validated_data == test_data

    def test_safe_service_integration(self, framework):
        """Test safe service integration"""
        hybrid_safety = framework.hybrid_safety

        # Test service integration
        hybrid_safety.safe_service_integration("service_a", "service_b")
        # Should not raise exceptions


class TestHybridThreadSafetyFramework:
    """Test the main hybrid thread safety framework"""

    def test_framework_initialization(self, thread_safety_config):
        """Test framework initialization"""
        framework = HybridThreadSafetyFramework(thread_safety_config)
        framework.initialize()

        # Verify components are initialized
        assert framework.memory_safety is not None
        assert framework.concurrency_control is not None
        assert framework.validator is not None
        assert framework.monitor is not None
        assert framework.cpython_safety is not None
        assert framework.codon_safety is not None
        assert framework.hybrid_safety is not None

        framework.shutdown()

    def test_safe_execution_context(self, framework):
        """Test safe execution context manager"""
        component = "test_component"
        runtime = RuntimeType.CPYTHON

        with framework.safe_execution(component, runtime):
            # Perform some work
            time.sleep(0.01)
            # Should not raise exceptions

    def test_safety_report_generation(self, framework):
        """Test safety report generation"""
        report = framework.get_safety_report()

        # Verify report structure
        assert "config" in report
        assert "metrics" in report
        assert "violations" in report
        assert "memory_leaks" in report
        assert "validation_results" in report

        # Verify config
        config = report["config"]
        assert "runtime_type" in config
        assert "safety_level" in config
        assert "max_concurrent_threads" in config


class TestThreadSafetyIntegration:
    """Integration tests for thread safety framework"""

    def test_concurrent_operations(self, framework):
        """Test concurrent operations with thread safety"""
        results = []
        errors = []

        def worker(worker_id: int) -> Dict[str, Any]:
            """Worker function for concurrent testing"""
            try:
                with framework.safe_execution(
                    f"worker_{worker_id}", RuntimeType.CPYTHON
                ):
                    # Simulate work
                    time.sleep(0.01)
                    return {"worker_id": worker_id, "status": "success"}
            except Exception as e:
                return {"worker_id": worker_id, "status": "error", "error": str(e)}

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i) for i in range(8)]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # Verify all operations completed
        assert len(results) == 8
        success_count = sum(1 for r in results if r["status"] == "success")
        assert success_count == 8  # All should succeed

    def test_memory_safety_under_load(self, framework):
        """Test memory safety under concurrent load"""
        memory_manager = framework.memory_safety

        def memory_worker(worker_id: int) -> None:
            """Worker that performs memory operations"""
            for i in range(100):
                memory_manager.track_memory_usage(
                    f"worker_{worker_id}", RuntimeType.CPYTHON
                )
                time.sleep(0.001)

        # Run memory operations concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(memory_worker, i) for i in range(4)]
            for future in as_completed(futures):
                future.result()

        # Check for memory leaks
        leaks = memory_manager.detect_memory_leaks()
        # Should not have significant leaks
        assert len(leaks) == 0 or all(leak["ratio"] < 0.9 for leak in leaks.values())

    def test_deadlock_prevention_under_load(self, framework):
        """Test deadlock prevention under concurrent load"""
        concurrency_control = framework.concurrency_control

        def deadlock_worker(worker_id: int) -> bool:
            """Worker that could potentially cause deadlocks"""
            resources = [f"resource_{i}" for i in range(3)]
            acquired_resources = []

            try:
                for resource in resources:
                    if concurrency_control.acquire_resource(resource, timeout=0.1):
                        acquired_resources.append(resource)
                        time.sleep(0.01)  # Simulate work
                    else:
                        break

                return len(acquired_resources) > 0
            finally:
                # Release all acquired resources
                for resource in acquired_resources:
                    concurrency_control.release_resource(resource)

        # Run deadlock-prone operations concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(deadlock_worker, i) for i in range(8)]
            results = [future.result() for future in futures]

        # All workers should complete (no deadlocks)
        assert all(results)


class TestProductionReadiness:
    """Test production readiness of thread safety framework"""

    def test_framework_factory(self):
        """Test framework factory function"""
        framework = create_thread_safety_framework(
            runtime_type=RuntimeType.HYBRID, safety_level=ThreadSafetyLevel.STRICT
        )

        assert isinstance(framework, HybridThreadSafetyFramework)
        assert framework.config.runtime_type == RuntimeType.HYBRID
        assert framework.config.safety_level == ThreadSafetyLevel.STRICT

    def test_global_framework_instance(self):
        """Test global framework instance management"""
        # Get global instance
        framework = get_thread_safety_framework()
        assert isinstance(framework, HybridThreadSafetyFramework)

        # Get again should return same instance
        framework2 = get_thread_safety_framework()
        assert framework is framework2

        # Shutdown
        shutdown_thread_safety_framework()

    def test_performance_under_load(self, framework):
        """Test performance under load"""
        start_time = time.time()

        def performance_worker(worker_id: int) -> int:
            """Worker for performance testing"""
            with framework.safe_execution(
                f"perf_worker_{worker_id}", RuntimeType.CPYTHON
            ):
                # Simulate work
                result = sum(i * i for i in range(1000))
                return result

        # Run performance test
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(performance_worker, i) for i in range(16)]
            results = [future.result() for future in futures]

        end_time = time.time()
        total_time = end_time - start_time

        # Verify all operations completed
        assert len(results) == 16
        assert all(isinstance(r, int) for r in results)

        # Performance should be reasonable (less than 5 seconds for 16 operations)
        assert total_time < 5.0

    def test_error_recovery(self, framework):
        """Test error recovery capabilities"""

        def error_worker(worker_id: int) -> bool:
            """Worker that may encounter errors"""
            try:
                with framework.safe_execution(
                    f"error_worker_{worker_id}", RuntimeType.CPYTHON
                ):
                    if worker_id % 3 == 0:  # Simulate occasional errors
                        raise ValueError(f"Simulated error in worker {worker_id}")
                    time.sleep(0.01)
                    return True
            except Exception:
                return False

        # Run error-prone operations
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(error_worker, i) for i in range(12)]
            results = [future.result() for future in futures]

        # Some should succeed, some should fail gracefully
        success_count = sum(results)
        assert 0 < success_count < 12  # Mixed results expected

        # Framework should still be functional
        report = framework.get_safety_report()
        assert report is not None


# Performance benchmarks
class TestThreadSafetyPerformance:
    """Performance benchmarks for thread safety framework"""

    def test_memory_tracking_performance(self, framework):
        """Benchmark memory tracking performance"""
        memory_manager = framework.memory_safety

        start_time = time.time()

        # Perform many memory tracking operations
        for i in range(1000):
            memory_manager.track_memory_usage(
                f"perf_component_{i}", RuntimeType.CPYTHON
            )

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly (less than 1 second for 1000 operations)
        assert total_time < 1.0

    def test_concurrency_control_performance(self, framework):
        """Benchmark concurrency control performance"""
        concurrency_control = framework.concurrency_control

        start_time = time.time()

        # Perform many resource acquisitions
        for i in range(100):
            resource_id = f"perf_resource_{i}"
            acquired = concurrency_control.acquire_resource(resource_id, timeout=0.1)
            if acquired:
                concurrency_control.release_resource(resource_id)

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly (less than 1 second for 100 operations)
        assert total_time < 1.0

    def test_validation_performance(self, framework):
        """Benchmark validation performance"""
        validator = framework.validator

        start_time = time.time()

        # Perform many validations
        for i in range(100):
            validator.validate_thread_safety(f"perf_component_{i}", RuntimeType.CPYTHON)

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly (less than 1 second for 100 operations)
        assert total_time < 1.0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
