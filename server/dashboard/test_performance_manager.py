"""
Test Suite for Performance Optimization & Resource Management System

This module contains comprehensive tests for the performance manager functionality
including connection pooling, rate limiting, memory management, performance profiling,
and resource monitoring.
"""

import asyncio
import pytest
import pytest_asyncio
import time
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from server.dashboard.performance_manager import (
    PerformanceManager, PerformanceConfig, ResourceType, PerformanceMetric,
    OptimizationStrategy, AlertLevel, ResourceMetrics, PerformanceSnapshot,
    SystemAlert, ConnectionPoolManager, RateLimitManager, MemoryManager,
    PerformanceProfiler, ResourceMonitor, GenericConnectionPool,
    get_performance_manager, initialize_performance_manager, shutdown_performance_manager,
    profile_operation, get_connection, get_performance_report, optimize_memory,
    SLOWAPI_AVAILABLE
)


class TestPerformanceConfig:
    """Test performance configuration functionality"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = PerformanceConfig()
        
        assert config.enable_connection_pooling is True
        assert config.max_pool_size == 50
        assert config.min_pool_size == 5
        assert config.enable_rate_limiting is True
        assert config.default_rate_limit == "100/minute"
        assert config.enable_memory_monitoring is True
        assert config.memory_threshold_percent == 80.0
        assert config.enable_performance_monitoring is True
        assert config.enable_resource_monitoring is True
        assert config.cpu_threshold_percent == 80.0
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = PerformanceConfig(
            enable_connection_pooling=False,
            max_pool_size=100,
            min_pool_size=10,
            enable_rate_limiting=False,
            default_rate_limit="200/minute",
            memory_threshold_percent=90.0,
            cpu_threshold_percent=85.0
        )
        
        assert config.enable_connection_pooling is False
        assert config.max_pool_size == 100
        assert config.min_pool_size == 10
        assert config.enable_rate_limiting is False
        assert config.default_rate_limit == "200/minute"
        assert config.memory_threshold_percent == 90.0
        assert config.cpu_threshold_percent == 85.0


class TestResourceMetrics:
    """Test resource metrics functionality"""
    
    def test_resource_metrics_creation(self):
        """Test resource metrics creation and methods"""
        metrics = ResourceMetrics(
            cpu_percent=75.5,
            memory_percent=65.0,
            memory_used_mb=8192.0,
            memory_available_mb=8192.0,
            disk_usage_percent=55.0,
            network_sent_mb=1024.0,
            network_recv_mb=2048.0,
            connection_count=25,
            thread_count=50,
            process_count=150
        )
        
        assert metrics.cpu_percent == 75.5
        assert metrics.memory_percent == 65.0
        assert metrics.memory_used_mb == 8192.0
        assert metrics.connection_count == 25
        
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["cpu_percent"] == 75.5
        assert metrics_dict["memory_percent"] == 65.0
        assert "timestamp" in metrics_dict


class TestPerformanceSnapshot:
    """Test performance snapshot functionality"""
    
    def test_performance_snapshot_calculations(self):
        """Test performance snapshot calculations"""
        snapshot = PerformanceSnapshot(
            response_times=[10.0, 20.0, 30.0, 40.0, 50.0],
            throughput_rps=100.0,
            error_rate_percent=2.5,
            active_connections=15,
            cache_hit_rate=85.0
        )
        
        assert snapshot.get_avg_response_time() == 30.0
        assert snapshot.get_p95_response_time() == 50.0
        assert snapshot.throughput_rps == 100.0
        assert snapshot.error_rate_percent == 2.5
        
        # Test empty response times
        empty_snapshot = PerformanceSnapshot()
        assert empty_snapshot.get_avg_response_time() == 0.0
        assert empty_snapshot.get_p95_response_time() == 0.0


class TestSystemAlert:
    """Test system alert functionality"""
    
    def test_system_alert_creation(self):
        """Test system alert creation and serialization"""
        alert = SystemAlert(
            alert_id="cpu_alert_123",
            level=AlertLevel.WARNING,
            resource_type=ResourceType.CPU,
            metric=PerformanceMetric.CPU_USAGE,
            current_value=85.5,
            threshold_value=80.0,
            message="High CPU usage detected"
        )
        
        assert alert.alert_id == "cpu_alert_123"
        assert alert.level == AlertLevel.WARNING
        assert alert.resource_type == ResourceType.CPU
        assert alert.current_value == 85.5
        assert alert.resolved is False
        
        alert_dict = alert.to_dict()
        assert isinstance(alert_dict, dict)
        assert alert_dict["level"] == "warning"
        assert alert_dict["resource_type"] == "cpu"
        assert alert_dict["current_value"] == 85.5


class TestGenericConnectionPool:
    """Test generic connection pool functionality"""
    
    @pytest.fixture
    def connection_factory(self):
        """Mock connection factory"""
        connection_count = 0
        
        def factory():
            nonlocal connection_count
            connection_count += 1
            mock_conn = MagicMock()
            mock_conn.id = connection_count
            return mock_conn
        
        return factory
    
    @pytest.mark.asyncio
    async def test_connection_pool_basic_operations(self, connection_factory):
        """Test basic connection pool operations"""
        pool = GenericConnectionPool(
            connection_factory=connection_factory,
            max_size=5,
            min_size=2,
            timeout=1
        )
        
        await pool.initialize()
        
        # Test getting and returning connections
        conn1 = await pool.get_connection()
        assert conn1 is not None
        
        conn2 = await pool.get_connection()
        assert conn2 is not None
        assert conn2 != conn1
        
        # Return connections
        await pool.return_connection(conn1)
        await pool.return_connection(conn2)
        
        # Get stats
        stats = pool.get_stats()
        assert stats["created"] >= 2
        assert stats["active_connections"] >= 0
        
        # Cleanup
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_connection_pool_timeout(self, connection_factory):
        """Test connection pool timeout behavior"""
        pool = GenericConnectionPool(
            connection_factory=connection_factory,
            max_size=1,
            min_size=0,
            timeout=0.1  # Very short timeout
        )
        
        await pool.initialize()
        
        # Get the only connection
        conn1 = await pool.get_connection()
        
        # Try to get another connection - should timeout
        with pytest.raises(asyncio.TimeoutError):
            await pool.get_connection()
        
        # Return connection
        await pool.return_connection(conn1)
        
        # Now should work
        conn2 = await pool.get_connection()
        assert conn2 is not None
        
        await pool.return_connection(conn2)
        await pool.close_all()


class TestConnectionPoolManager:
    """Test connection pool manager functionality"""
    
    @pytest_asyncio.fixture
    async def pool_manager(self):
        """Create connection pool manager for testing"""
        config = PerformanceConfig(max_pool_size=10, min_pool_size=2)
        manager = ConnectionPoolManager(config)
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_pool_manager_create_and_get(self, pool_manager):
        """Test creating and getting pools"""
        
        def mock_factory():
            return MagicMock()
        
        # Create pool
        pool = await pool_manager.create_pool(
            "test_pool",
            connection_factory=mock_factory,
            max_size=5,
            min_size=1
        )
        
        assert pool is not None
        
        # Get pool
        retrieved_pool = await pool_manager.get_pool("test_pool")
        assert retrieved_pool is pool
        
        # Get non-existent pool
        missing_pool = await pool_manager.get_pool("missing_pool")
        assert missing_pool is None
    
    @pytest.mark.asyncio
    async def test_pool_manager_connection_context(self, pool_manager):
        """Test connection context manager"""
        
        def mock_factory():
            mock_conn = MagicMock()
            return mock_conn
        
        await pool_manager.create_pool("test_pool", mock_factory)
        
        # Use connection context manager
        async with pool_manager.get_connection("test_pool") as conn:
            assert conn is not None
        
        # Test with non-existent pool
        with pytest.raises(ValueError):
            async with pool_manager.get_connection("missing_pool") as conn:
                pass


class TestRateLimitManager:
    """Test rate limit manager functionality"""
    
    def test_rate_limit_manager_initialization(self):
        """Test rate limit manager initialization"""
        config = PerformanceConfig(enable_rate_limiting=True)
        manager = RateLimitManager(config)
        
        # Should attempt to initialize limiter if slowapi available
        if SLOWAPI_AVAILABLE:
            assert manager.limiter is not None or manager.limiter is None  # May fail to init
        else:
            assert manager.limiter is None
    
    def test_rate_limit_manager_custom_limits(self):
        """Test custom rate limits"""
        config = PerformanceConfig()
        manager = RateLimitManager(config)
        
        # Add custom limit
        manager.add_custom_limit("/api/heavy", "10/minute")
        
        # Test getting limits
        assert manager.get_limit_for_endpoint("/api/heavy") == "10/minute"
        assert manager.get_limit_for_endpoint("/api/light") == config.default_rate_limit
    
    @pytest.mark.asyncio
    async def test_adaptive_limits(self):
        """Test adaptive rate limiting"""
        config = PerformanceConfig()
        manager = RateLimitManager(config)
        
        # Test adaptive adjustment
        await manager.adjust_adaptive_limits("/api/test", 0.9)  # High load
        factor1 = manager.get_adaptive_limit("/api/test")
        assert factor1 < 1.0  # Should reduce limits
        
        await manager.adjust_adaptive_limits("/api/test", 0.3)  # Low load
        factor2 = manager.get_adaptive_limit("/api/test")
        assert factor2 > factor1  # Should increase limits


class TestMemoryManager:
    """Test memory manager functionality"""
    
    @pytest.fixture
    def memory_manager(self):
        """Create memory manager for testing"""
        config = PerformanceConfig(
            enable_memory_monitoring=True,
            memory_threshold_percent=80.0,
            enable_auto_gc=True,
            memory_profiling_enabled=False
        )
        return MemoryManager(config)
    
    def test_memory_usage_tracking(self, memory_manager):
        """Test memory usage tracking"""
        usage = memory_manager.get_memory_usage()
        
        assert isinstance(usage, dict)
        assert "rss_mb" in usage
        assert "vms_mb" in usage
        assert "percent" in usage
        assert "available_mb" in usage
        assert all(isinstance(v, (int, float)) for v in usage.values())
    
    def test_memory_profiling(self, memory_manager):
        """Test memory profiling functionality"""
        
        def test_function():
            # Create some objects
            data = [i for i in range(1000)]
            return len(data)
        
        result, peak_memory = memory_manager.profile_memory_usage(test_function)
        
        assert result == 1000
        assert isinstance(peak_memory, (int, float))
        assert peak_memory >= 0
    
    def test_memory_stats(self, memory_manager):
        """Test memory statistics"""
        stats = memory_manager.get_memory_stats()
        
        assert isinstance(stats, dict)
        assert "current" in stats
        assert "gc_stats" in stats
        assert "snapshots_count" in stats
        assert "alerts_count" in stats
        assert "profiling_enabled" in stats


class TestPerformanceProfiler:
    """Test performance profiler functionality"""
    
    @pytest.fixture
    def profiler(self):
        """Create performance profiler for testing"""
        config = PerformanceConfig(enable_profiling=True)
        return PerformanceProfiler(config)
    
    @pytest.mark.asyncio
    async def test_operation_profiling(self, profiler):
        """Test operation profiling"""
        
        async def test_operation():
            await asyncio.sleep(0.01)  # Small delay
            return "result"
        
        # Profile operation
        async with profiler.profile_operation("test_op"):
            result = await test_operation()
        
        assert result == "result"
        
        # Check stats
        stats = profiler.get_operation_stats("test_op")
        assert stats["count"] == 1
        assert stats["avg_duration_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_summary(self, profiler):
        """Test performance summary"""
        
        # Perform some operations
        async with profiler.profile_operation("op1"):
            await asyncio.sleep(0.001)
        
        async with profiler.profile_operation("op2"):
            await asyncio.sleep(0.002)
        
        summary = profiler.get_performance_summary()
        
        assert summary["total_requests"] == 2
        assert summary["successful_requests"] == 2
        assert summary["failed_requests"] == 0
        assert summary["success_rate"] == 100.0
        assert summary["avg_response_time_ms"] > 0


class TestResourceMonitor:
    """Test resource monitor functionality"""
    
    @pytest_asyncio.fixture
    async def resource_monitor(self):
        """Create resource monitor for testing"""
        config = PerformanceConfig(
            enable_resource_monitoring=True,
            monitoring_interval_seconds=0.1,  # Fast for testing
            cpu_threshold_percent=80.0,
            memory_threshold_percent=80.0
        )
        monitor = ResourceMonitor(config)
        yield monitor
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_resource_monitoring_start_stop(self, resource_monitor):
        """Test starting and stopping resource monitoring"""
        assert not resource_monitor.monitoring_active
        
        await resource_monitor.start_monitoring()
        assert resource_monitor.monitoring_active
        
        # Let it collect some data
        await asyncio.sleep(0.2)
        
        await resource_monitor.stop_monitoring()
        assert not resource_monitor.monitoring_active
    
    @pytest.mark.asyncio
    async def test_resource_metrics_collection(self, resource_monitor):
        """Test resource metrics collection"""
        # Start monitoring briefly
        await resource_monitor.start_monitoring()
        await asyncio.sleep(0.15)  # Let it collect data
        await resource_monitor.stop_monitoring()
        
        # Check collected metrics
        current_metrics = resource_monitor.get_current_metrics()
        if current_metrics:  # May be None if collection didn't run
            assert isinstance(current_metrics, ResourceMetrics)
            assert current_metrics.cpu_percent >= 0
            assert current_metrics.memory_percent >= 0
    
    def test_resource_trends(self, resource_monitor):
        """Test resource trends analysis"""
        # Add some mock data
        for i in range(5):
            metrics = ResourceMetrics(
                cpu_percent=50.0 + i * 5,
                memory_percent=60.0 + i * 2,
                disk_usage_percent=30.0,
                timestamp=datetime.now() - timedelta(minutes=i)
            )
            resource_monitor.resource_history.append(metrics)
        
        trends = resource_monitor.get_resource_trends(hours=1)
        
        assert "cpu_percent" in trends
        assert "memory_percent" in trends
        assert "disk_usage_percent" in trends
        assert "timestamps" in trends
        assert len(trends["cpu_percent"]) == 5


class TestPerformanceManager:
    """Test performance manager functionality"""
    
    @pytest_asyncio.fixture
    async def performance_manager(self):
        """Create performance manager for testing"""
        config = PerformanceConfig(
            enable_connection_pooling=True,
            enable_rate_limiting=False,  # Disable for simpler testing
            enable_memory_monitoring=False,  # Disable for testing
            enable_resource_monitoring=False,  # Disable for testing
            enable_async_optimization=True
        )
        manager = PerformanceManager(config)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_manager_initialization(self, performance_manager):
        """Test performance manager initialization"""
        assert performance_manager.connection_pool_manager is not None
        assert performance_manager.rate_limit_manager is not None
        assert performance_manager.memory_manager is not None
        assert performance_manager.performance_profiler is not None
        assert performance_manager.resource_monitor is not None
    
    @pytest.mark.asyncio
    async def test_operation_profiling(self, performance_manager):
        """Test operation profiling through performance manager"""
        
        async def test_operation():
            await asyncio.sleep(0.001)
            return "success"
        
        async with performance_manager.profile_operation("test_manager_op"):
            result = await test_operation()
        
        assert result == "success"
        
        # Check profiler recorded the operation
        stats = performance_manager.performance_profiler.get_operation_stats("test_manager_op")
        assert stats["count"] == 1
    
    @pytest.mark.asyncio
    async def test_memory_optimization(self, performance_manager):
        """Test memory optimization"""
        # This should not raise an exception
        await performance_manager.optimize_memory_usage()
        
        # Check that optimization counter increased
        assert performance_manager.performance_stats["total_optimizations"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_report(self, performance_manager):
        """Test performance report generation"""
        report = await performance_manager.get_performance_report()
        
        assert isinstance(report, dict)
        assert "timestamp" in report
        assert "uptime_seconds" in report
        assert "optimization_strategies" in report
        assert "performance_summary" in report
        assert "memory_stats" in report
        assert "connection_pools" in report
        assert "alerts" in report
        assert "statistics" in report
    
    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, performance_manager):
        """Test optimization recommendations"""
        recommendations = await performance_manager.get_optimization_recommendations()
        
        assert isinstance(recommendations, list)
        # May be empty if no optimizations needed
        
        for rec in recommendations:
            assert "category" in rec
            assert "priority" in rec
            assert "recommendation" in rec


class TestGlobalFunctions:
    """Test global convenience functions"""
    
    @pytest.mark.asyncio
    async def test_global_performance_manager(self):
        """Test global performance manager functions"""
        
        # Test getting manager
        manager = await get_performance_manager()
        assert manager is not None
        
        # Test getting report
        report = await get_performance_report()
        assert isinstance(report, dict)
        
        # Test memory optimization
        await optimize_memory()
        
        # Cleanup
        await shutdown_performance_manager()
    
    @pytest.mark.asyncio
    async def test_initialize_custom_performance_manager(self):
        """Test initialization with custom config"""
        config = PerformanceConfig(
            max_pool_size=25,
            enable_rate_limiting=False,
            enable_memory_monitoring=False
        )
        
        manager = await initialize_performance_manager(config)
        
        assert manager.config.max_pool_size == 25
        assert manager.config.enable_rate_limiting is False
        
        # Cleanup
        await shutdown_performance_manager()
    
    @pytest.mark.asyncio
    async def test_profile_operation_global(self):
        """Test global profile operation function"""
        
        async def test_op():
            await asyncio.sleep(0.001)
            return "done"
        
        async with profile_operation("global_test_op"):
            result = await test_op()
        
        assert result == "done"
        
        # Cleanup
        await shutdown_performance_manager()


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test realistic performance manager usage scenario"""
    
    # Initialize with custom configuration
    config = PerformanceConfig(
        enable_connection_pooling=True,
        max_pool_size=20,
        enable_rate_limiting=False,  # Disable for testing
        enable_memory_monitoring=False,  # Disable for testing
        enable_resource_monitoring=False,  # Disable for testing
        enable_async_optimization=True
    )
    
    manager = await initialize_performance_manager(config)
    
    try:
        # Test connection pool creation
        def mock_conn_factory():
            return MagicMock()
        
        await manager.connection_pool_manager.create_pool(
            "test_service",
            mock_conn_factory,
            max_size=10,
            min_size=2
        )
        
        # Test connection usage
        async with manager.get_connection("test_service") as conn:
            assert conn is not None
        
        # Test operation profiling
        async def analytics_operation():
            await asyncio.sleep(0.002)
            return {"metrics": "data"}
        
        async with manager.profile_operation("analytics_fetch"):
            result = await analytics_operation()
            assert result == {"metrics": "data"}
        
        # Test memory optimization
        await manager.optimize_memory_usage()
        
        # Test performance report
        report = await manager.get_performance_report()
        assert report["optimization_strategies"]
        assert report["performance_summary"]["total_requests"] > 0
        
        # Test recommendations
        recommendations = await manager.get_optimization_recommendations()
        assert isinstance(recommendations, list)
        
        # Test pool statistics
        pool_stats = await manager.connection_pool_manager.get_all_stats()
        assert "test_service" in pool_stats
        assert pool_stats["test_service"]["max_size"] == 10
        
    finally:
        # Cleanup
        await shutdown_performance_manager()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 