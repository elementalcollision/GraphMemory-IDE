"""
Test Hybrid Monitoring Framework
Comprehensive tests for CPython/Condon hybrid monitoring
"""

import asyncio
import threading
import time
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from .condon_monitor import (
    CompilationType,
    CondonMonitor,
    CondonServiceMonitor,
    ThreadSafetyEvent,
    get_condon_monitor,
    initialize_condon_monitoring,
)
from .cpython_monitor import (
    CPythonMonitor,
    CPythonServiceMonitor,
    get_cpython_monitor,
    initialize_cpython_monitoring,
)
from .hybrid_monitoring_framework import (
    HybridMonitoringFramework,
    get_hybrid_monitoring,
    initialize_hybrid_monitoring,
    shutdown_hybrid_monitoring,
)


class TestHybridMonitoringFramework:
    """Test hybrid monitoring framework"""

    def setup_method(self):
        """Setup test environment"""
        # Reset global instances
        shutdown_hybrid_monitoring()

        # Create test framework
        self.framework = HybridMonitoringFramework(
            service_name="test-hybrid", enable_prometheus=False, enable_otel=False
        )

    def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, "framework"):
            self.framework.shutdown()
        shutdown_hybrid_monitoring()

    def test_framework_initialization(self):
        """Test framework initialization"""
        # Test basic initialization
        assert self.framework.service_name == "test-hybrid"
        assert len(self.framework.cpython_services) == 0
        assert len(self.framework.condon_services) == 0
        assert len(self.framework.hybrid_services) == 0

    def test_service_registration(self):
        """Test service registration"""
        # Register CPython service
        cpython_service = self.framework.register_cpython_service(
            "test-cpython", {"environment": "test"}
        )
        assert cpython_service.service_name == "test-cpython"
        assert len(self.framework.cpython_services) == 1

        # Register Condon service
        condon_service = self.framework.register_condon_service(
            "test-condon", {"environment": "test"}
        )
        assert condon_service.service_name == "test-condon"
        assert len(self.framework.condon_services) == 1

        # Register hybrid service
        hybrid_service = self.framework.register_hybrid_service(
            "test-hybrid", {"environment": "test"}
        )
        assert hybrid_service.service_name == "test-hybrid"
        assert len(self.framework.hybrid_services) == 1

    def test_request_monitoring(self):
        """Test request monitoring"""
        # Register a service
        service = self.framework.register_cpython_service("test-service")

        # Test request monitoring
        with self.framework.monitor_request("test-service", "/test", "GET"):
            time.sleep(0.1)  # Simulate work

        # Verify metrics were recorded
        assert service.metrics["request_count"]._value.get() > 0
        assert service.metrics["request_duration"]._sum.get() > 0

    def test_boundary_call_monitoring(self):
        """Test service boundary call monitoring"""
        with self.framework.monitor_boundary_call("service-a", "service-b"):
            time.sleep(0.1)  # Simulate work

        # Verify boundary metrics were recorded
        boundary_calls = self.framework.hybrid_metrics["service_boundary_calls"]
        assert boundary_calls._value.get() > 0

    def test_system_metrics_update(self):
        """Test system metrics update"""
        self.framework.update_system_metrics()

        # Verify system metrics were updated
        cpu_usage = self.framework.system_metrics["cpu_usage"]._value.get()
        memory_usage = self.framework.system_metrics["memory_usage"]._value.get()

        assert cpu_usage is not None
        assert memory_usage is not None

    def test_metrics_summary(self):
        """Test metrics summary generation"""
        # Register some services
        self.framework.register_cpython_service("test-cpython")
        self.framework.register_condon_service("test-condon")

        # Get summary
        summary = self.framework.get_metrics_summary()

        assert "system" in summary
        assert "services" in summary
        assert "alerts" in summary
        assert summary["services"]["cpython"] == 1
        assert summary["services"]["condon"] == 1


class TestCPythonMonitor:
    """Test CPython monitoring"""

    def setup_method(self):
        """Setup test environment"""
        self.monitor = CPythonMonitor("test-cpython")

    def teardown_method(self):
        """Cleanup test environment"""
        self.monitor.stop_monitoring()

    def test_monitor_initialization(self):
        """Test monitor initialization"""
        assert self.monitor.service_name == "test-cpython"
        assert "gil_contention_time" in self.monitor.metrics
        assert "memory_allocated" in self.monitor.metrics
        assert "async_tasks_active" in self.monitor.metrics

    def test_gil_contention_monitoring(self):
        """Test GIL contention monitoring"""
        with self.monitor.monitor_gil_contention("test_operation"):
            time.sleep(0.1)  # Simulate work

        # Verify GIL metrics were recorded
        gil_contention = self.monitor.metrics["gil_contention_time"]
        gil_acquire = self.monitor.metrics["gil_acquire_count"]

        assert gil_contention._sum.get() > 0
        assert gil_acquire._value.get() > 0

    def test_memory_monitoring(self):
        """Test memory monitoring"""
        self.monitor._update_memory_metrics()

        # Verify memory metrics were updated
        memory_allocated = self.monitor.metrics["memory_allocated"]._value.get()
        memory_peak = self.monitor.metrics["memory_peak"]._value.get()

        assert memory_allocated is not None
        assert memory_peak is not None

    def test_async_task_monitoring(self):
        """Test async task monitoring"""
        with self.monitor.monitor_async_task("test_task"):
            time.sleep(0.1)  # Simulate work

        # Verify async metrics were recorded
        task_duration = self.monitor.metrics["async_task_duration"]
        tasks_completed = self.monitor.metrics["async_tasks_completed"]

        assert task_duration._sum.get() > 0
        assert tasks_completed._value.get() > 0

    def test_performance_summary(self):
        """Test performance summary generation"""
        summary = self.monitor.get_performance_summary()

        assert "memory" in summary
        assert "cpu" in summary
        assert "async" in summary
        assert "gc" in summary

    def test_gil_statistics(self):
        """Test GIL statistics generation"""
        # Record some GIL events
        with self.monitor.monitor_gil_contention("test"):
            time.sleep(0.1)

        stats = self.monitor.get_gil_statistics()

        assert "contention_time" in stats
        assert "acquisitions" in stats


class TestCondonMonitor:
    """Test Condon monitoring"""

    def setup_method(self):
        """Setup test environment"""
        self.monitor = CondonMonitor("test-condon")

    def teardown_method(self):
        """Cleanup test environment"""
        self.monitor.stop_monitoring()

    def test_monitor_initialization(self):
        """Test monitor initialization"""
        assert self.monitor.service_name == "test-condon"
        assert "compilation_duration" in self.monitor.metrics
        assert "thread_safety_events" in self.monitor.metrics
        assert "memory_allocation" in self.monitor.metrics

    def test_compilation_monitoring(self):
        """Test compilation monitoring"""
        with self.monitor.monitor_compilation(CompilationType.JIT, "optimized"):
            time.sleep(0.1)  # Simulate compilation

        # Verify compilation metrics were recorded
        compilation_duration = self.monitor.metrics["compilation_duration"]
        compilation_memory = self.monitor.metrics["compilation_memory"]

        assert compilation_duration._sum.get() > 0
        assert compilation_memory._sum.get() >= 0

    def test_thread_safety_monitoring(self):
        """Test thread safety monitoring"""
        self.monitor.record_thread_safety_event(
            ThreadSafetyEvent.LOCK_ACQUISITION, "info"
        )

        # Verify thread safety metrics were recorded
        safety_events = self.monitor.metrics["thread_safety_events"]
        assert safety_events._value.get() > 0

    def test_memory_allocation_monitoring(self):
        """Test memory allocation monitoring"""
        self.monitor.record_memory_allocation("test_allocation", 1024)
        self.monitor.record_memory_deallocation("test_allocation", 512)

        # Verify memory metrics were recorded
        allocation = self.monitor.metrics["memory_allocation"]
        deallocation = self.monitor.metrics["memory_deallocation"]

        assert allocation._value.get() == 1024
        assert deallocation._value.get() == 512

    def test_cache_monitoring(self):
        """Test cache monitoring"""
        self.monitor.record_cache_hit("compilation")
        self.monitor.record_cache_miss("compilation")

        # Verify cache metrics were recorded
        cache_hits = self.monitor.metrics["compilation_cache_hits"]
        cache_misses = self.monitor.metrics["compilation_cache_misses"]

        assert cache_hits._value.get() > 0
        assert cache_misses._value.get() > 0

    def test_native_execution_monitoring(self):
        """Test native execution monitoring"""
        with self.monitor.monitor_native_execution("test_function", "optimized"):
            time.sleep(0.1)  # Simulate execution

        # Verify execution metrics were recorded
        execution_time = self.monitor.metrics["native_execution_time"]
        assert execution_time._sum.get() > 0

    def test_performance_summary(self):
        """Test performance summary generation"""
        summary = self.monitor.get_performance_summary()

        assert "memory" in summary
        assert "cpu" in summary
        assert "cache" in summary
        assert "compilation" in summary
        assert "thread_safety" in summary


class TestServiceMonitors:
    """Test service-specific monitors"""

    def setup_method(self):
        """Setup test environment"""
        self.cpython_service = CPythonServiceMonitor("test-cpython-service")
        self.condon_service = CondonServiceMonitor("test-condon-service")

    def teardown_method(self):
        """Cleanup test environment"""
        self.cpython_service.stop_monitoring()
        self.condon_service.stop_monitoring()

    def test_cpython_service_monitoring(self):
        """Test CPython service monitoring"""
        # Test request monitoring
        with self.cpython_service.monitor_request("/test", "GET"):
            time.sleep(0.1)

        # Verify request metrics were recorded
        request_count = self.cpython_service.request_metrics["request_count"]
        request_duration = self.cpython_service.request_metrics["request_duration"]

        assert request_count._value.get() > 0
        assert request_duration._sum.get() > 0

    def test_condon_service_monitoring(self):
        """Test Condon service monitoring"""
        # Test request monitoring
        with self.condon_service.monitor_request("/test", "GET"):
            time.sleep(0.1)

        # Verify request metrics were recorded
        request_count = self.condon_service.request_metrics["request_count"]
        request_duration = self.condon_service.request_metrics["request_duration"]

        assert request_count._value.get() > 0
        assert request_duration._sum.get() > 0

        # Test compilation monitoring
        with self.condon_service.monitor_compilation(CompilationType.AOT):
            time.sleep(0.1)

        # Test thread safety event recording
        self.condon_service.record_thread_safety_event(
            ThreadSafetyEvent.RACE_CONDITION, "warning"
        )

    def test_service_summaries(self):
        """Test service summary generation"""
        cpython_summary = self.cpython_service.get_service_summary()
        condon_summary = self.condon_service.get_service_summary()

        assert cpython_summary["service_name"] == "test-cpython-service"
        assert condon_summary["service_name"] == "test-condon-service"
        assert "performance" in cpython_summary
        assert "performance" in condon_summary


class TestIntegration:
    """Integration tests for the complete monitoring system"""

    def setup_method(self):
        """Setup test environment"""
        self.framework = initialize_hybrid_monitoring(
            service_name="test-integration", enable_prometheus=False, enable_otel=False
        )

    def teardown_method(self):
        """Cleanup test environment"""
        shutdown_hybrid_monitoring()

    def test_complete_monitoring_workflow(self):
        """Test complete monitoring workflow"""
        # Register services
        cpython_service = self.framework.register_cpython_service("test-cpython")
        condon_service = self.framework.register_condon_service("test-condon")

        # Simulate CPython service activity
        with self.framework.monitor_request("test-cpython", "/api/test", "POST"):
            time.sleep(0.1)

        # Simulate Condon service activity
        with self.framework.monitor_request("test-condon", "/compile", "POST"):
            time.sleep(0.1)

        # Simulate service boundary call
        with self.framework.monitor_boundary_call("test-cpython", "test-condon"):
            time.sleep(0.1)

        # Update system metrics
        self.framework.update_system_metrics()

        # Get comprehensive summary
        summary = self.framework.get_metrics_summary()

        # Verify all components are working
        assert summary["services"]["cpython"] == 1
        assert summary["services"]["condon"] == 1
        assert "system" in summary
        assert "alerts" in summary

    def test_concurrent_monitoring(self):
        """Test concurrent monitoring operations"""
        # Register services
        self.framework.register_cpython_service("service-1")
        self.framework.register_cpython_service("service-2")
        self.framework.register_condon_service("service-3")

        # Simulate concurrent requests
        def make_requests(service_name: str, count: int):
            for i in range(count):
                with self.framework.monitor_request(service_name, f"/req/{i}"):
                    time.sleep(0.01)

        # Start concurrent threads
        threads = []
        for service_name in ["service-1", "service-2", "service-3"]:
            thread = threading.Thread(target=make_requests, args=(service_name, 5))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify metrics were recorded correctly
        summary = self.framework.get_metrics_summary()
        assert summary["services"]["cpython"] == 2
        assert summary["services"]["condon"] == 1


class TestErrorHandling:
    """Test error handling in monitoring framework"""

    def setup_method(self):
        """Setup test environment"""
        self.framework = HybridMonitoringFramework(
            service_name="test-errors", enable_prometheus=False, enable_otel=False
        )

    def teardown_method(self):
        """Cleanup test environment"""
        self.framework.shutdown()

    def test_request_error_monitoring(self):
        """Test error monitoring in requests"""
        service = self.framework.register_cpython_service("test-service")

        # Simulate request with error
        try:
            with self.framework.monitor_request("test-service", "/error", "GET"):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify error was recorded
        error_count = service.metrics["error_count"]
        assert error_count._value.get() > 0

    def test_framework_error_recovery(self):
        """Test framework error recovery"""
        # Test with invalid service name
        with pytest.raises(Exception):
            with self.framework.monitor_request("nonexistent-service", "/test"):
                pass

        # Framework should still be functional
        summary = self.framework.get_metrics_summary()
        assert "system" in summary


if __name__ == "__main__":
    pytest.main([__file__])
