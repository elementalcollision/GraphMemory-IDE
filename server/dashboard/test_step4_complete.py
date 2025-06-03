"""
Test Suite for Step 4: Background Data Collection System

This test suite verifies the functionality of the background data collection
system including DataBuffer, HealthMonitor, and BackgroundDataCollector.
"""

import asyncio
import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

# Test imports with fallback
try:
    from server.dashboard.background_collector import (
        DataBuffer, HealthMonitor, BackgroundDataCollector,
        DataPoint, AggregatedData, HealthStatus, CollectionStatus,
        get_background_collector, initialize_background_collector
    )
    from server.dashboard.models.analytics_models import (
        SystemMetricsData, MemoryInsightsData, GraphMetricsData, AnalyticsStatus
    )
    from server.dashboard.data_adapter import DataAdapter
except ImportError as e:
    print(f"Import error: {e}")
    print("This is expected when running tests independently")


def test_1_background_collector_imports() -> bool:
    """Test 1: Verify all background collector imports work correctly"""
    print("\n=== Test 1: Background Collector Imports ===")
    
    try:
        # Test enum imports
        assert HealthStatus.HEALTHY.value == "healthy"
        assert CollectionStatus.RUNNING.value == "running"
        
        # Test class imports
        assert DataBuffer is not None
        assert HealthMonitor is not None
        assert BackgroundDataCollector is not None
        assert DataPoint is not None
        assert AggregatedData is not None
        
        print("✅ All imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


def test_2_data_buffer_functionality() -> bool:
    """Test 2: Verify DataBuffer functionality"""
    print("\n=== Test 2: DataBuffer Functionality ===")
    
    try:
        # Create test data
        system_data = SystemMetricsData(
            active_nodes=100,
            active_edges=200,
            query_rate=50.0,
            cache_hit_rate=0.85,
            memory_usage=75.5,
            cpu_usage=45.2,
            response_time=120.0,
            uptime_seconds=3600.0,
            timestamp=datetime.now().isoformat(),
            status=AnalyticsStatus.HEALTHY
        )
        
        # Create buffer
        buffer = DataBuffer(max_size=10, name="test_buffer")
        
        # Test adding data points
        buffer.add_data_point(system_data, 0.5)
        buffer.add_data_point(system_data, 0.7)
        
        # Test buffer stats
        stats = buffer.get_buffer_stats()
        assert stats["size"] == 2
        assert stats["name"] == "test_buffer"
        assert stats["success_rate"] == 1.0
        
        # Test recent data retrieval
        recent_data = buffer.get_recent_data(1)
        assert len(recent_data) == 1
        assert recent_data[0].collection_time == 0.7
        
        # Test failed collection recording
        buffer.record_failed_collection()
        assert buffer.get_success_rate() < 1.0
        
        print("✅ DataBuffer functionality working correctly")
        return True
        
    except Exception as e:
        print(f"❌ DataBuffer test failed: {e}")
        return False


def test_3_health_monitor_functionality() -> bool:
    """Test 3: Verify HealthMonitor functionality"""
    print("\n=== Test 3: HealthMonitor Functionality ===")
    
    try:
        # Create health monitor
        monitor = HealthMonitor()
        
        # Test initial state
        assert monitor.get_overall_health() == HealthStatus.HEALTHY
        
        # Test component health updates
        monitor.update_component_health("test_component", HealthStatus.HEALTHY)
        assert monitor.get_component_health("test_component") == HealthStatus.HEALTHY
        
        # Test health degradation
        monitor.update_component_health("test_component", HealthStatus.DEGRADED, 
                                      {"reason": "test_degradation"})
        assert monitor.get_overall_health() == HealthStatus.DEGRADED
        
        # Test health summary
        summary = monitor.get_health_summary()
        assert summary["overall_status"] == "degraded"
        assert "test_component" in summary["components"]
        assert summary["components"]["test_component"] == "degraded"
        
        # Test alert generation
        assert len(monitor.alerts) > 0  # Should have generated an alert for status change
        
        print("✅ HealthMonitor functionality working correctly")
        return True
        
    except Exception as e:
        print(f"❌ HealthMonitor test failed: {e}")
        return False


def test_4_background_collector_basic() -> bool:
    """Test 4: Verify BackgroundDataCollector basic functionality"""
    print("\n=== Test 4: BackgroundDataCollector Basic ===")
    
    try:
        # Create mock data adapter
        mock_adapter = MagicMock()
        mock_adapter.get_performance_stats.return_value = {
            "success_rate": 95.0,
            "cache_hit_rate": 80.0
        }
        
        # Create background collector
        collector = BackgroundDataCollector(mock_adapter)
        
        # Test initial state
        assert collector.status == CollectionStatus.STOPPED
        assert len(collector.buffers) == 3  # analytics, memory, graph
        assert "analytics" in collector.buffers
        assert "memory" in collector.buffers
        assert "graph" in collector.buffers
        
        # Test collection intervals
        assert collector.collection_intervals["analytics"] == 1
        assert collector.collection_intervals["memory"] == 5
        assert collector.collection_intervals["graph"] == 2
        
        # Test collection stats
        stats = collector.get_collection_stats()
        assert stats["status"] == "stopped"
        assert "buffer_stats" in stats
        assert "health_summary" in stats
        
        print("✅ BackgroundDataCollector basic functionality working")
        return True
        
    except Exception as e:
        print(f"❌ BackgroundDataCollector basic test failed: {e}")
        return False


def test_5_data_aggregation() -> bool:
    """Test 5: Verify data aggregation functionality"""
    print("\n=== Test 5: Data Aggregation ===")
    
    try:
        # Create test data
        system_data1 = SystemMetricsData(
            active_nodes=100, active_edges=200, query_rate=50.0,
            cache_hit_rate=0.85, memory_usage=75.5, cpu_usage=45.2,
            response_time=120.0, uptime_seconds=3600.0,
            timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
        )
        
        system_data2 = SystemMetricsData(
            active_nodes=110, active_edges=220, query_rate=55.0,
            cache_hit_rate=0.90, memory_usage=80.0, cpu_usage=50.0,
            response_time=110.0, uptime_seconds=3700.0,
            timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
        )
        
        # Create buffer and add data
        buffer = DataBuffer(max_size=100, name="aggregation_test")
        buffer.add_data_point(system_data1, 0.5)
        buffer.add_data_point(system_data2, 0.7)
        
        # Test aggregation
        aggregated = buffer.get_aggregated_data(window_minutes=1)
        assert aggregated is not None
        assert aggregated.count == 2
        assert aggregated.avg_collection_time == 0.6  # (0.5 + 0.7) / 2
        
        # Test data summary
        assert "data_summary" in aggregated.to_dict()
        summary = aggregated.data_summary
        assert summary["type"] == "system_metrics"
        assert "avg_active_nodes" in summary
        assert summary["avg_active_nodes"] == 105.0  # (100 + 110) / 2
        
        print("✅ Data aggregation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Data aggregation test failed: {e}")
        return False


def test_6_async_collection_simulation() -> bool:
    """Test 6: Simulate async collection without actually running background tasks"""
    print("\n=== Test 6: Async Collection Simulation ===")
    
    try:
        # Create mock data adapter with async methods
        mock_adapter = MagicMock()
        
        # Mock the async methods
        async def mock_get_system_metrics() -> SystemMetricsData:
            return SystemMetricsData(
                active_nodes=100, active_edges=200, query_rate=50.0,
                cache_hit_rate=0.85, memory_usage=75.5, cpu_usage=45.2,
                response_time=120.0, uptime_seconds=3600.0,
                timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
            )
        
        async def mock_get_memory_insights() -> MemoryInsightsData:
            return MemoryInsightsData(
                total_memories=1000, procedural_memories=300, semantic_memories=400,
                episodic_memories=300, memory_efficiency=0.85, memory_growth_rate=0.05,
                avg_memory_size=1024.0, compression_ratio=1.4, retrieval_speed=50.0,
                timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
            )
        
        async def mock_get_graph_metrics() -> GraphMetricsData:
            return GraphMetricsData(
                node_count=500, edge_count=1000, connected_components=5,
                largest_component_size=450, diameter=8, density=0.004,
                clustering_coefficient=0.3, avg_centrality=0.02, modularity=0.5,
                timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
            )
        
        mock_adapter._get_validated_system_metrics = mock_get_system_metrics
        mock_adapter._get_validated_memory_insights = mock_get_memory_insights
        mock_adapter._get_validated_graph_metrics = mock_get_graph_metrics
        mock_adapter.get_performance_stats.return_value = {"success_rate": 95.0}
        
        # Create collector
        collector = BackgroundDataCollector(mock_adapter)
        
        # Simulate single collection cycles
        async def simulate_collection() -> None:
            # Simulate analytics collection
            start_time = time.time()
            analytics_data = await mock_adapter._get_validated_system_metrics()
            collection_time = time.time() - start_time
            collector.buffers["analytics"].add_data_point(analytics_data, collection_time)
            
            # Simulate memory collection
            start_time = time.time()
            memory_data = await mock_adapter._get_validated_memory_insights()
            collection_time = time.time() - start_time
            collector.buffers["memory"].add_data_point(memory_data, collection_time)
            
            # Simulate graph collection
            start_time = time.time()
            graph_data = await mock_adapter._get_validated_graph_metrics()
            collection_time = time.time() - start_time
            collector.buffers["graph"].add_data_point(graph_data, collection_time)
        
        # Run simulation
        asyncio.run(simulate_collection())
        
        # Verify data was collected
        assert len(collector.buffers["analytics"].data) == 1
        assert len(collector.buffers["memory"].data) == 1
        assert len(collector.buffers["graph"].data) == 1
        
        # Test recent data retrieval
        recent_analytics = collector.get_recent_data("analytics", 1)
        assert len(recent_analytics) == 1
        assert isinstance(recent_analytics[0].data, SystemMetricsData)
        
        print("✅ Async collection simulation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Async collection simulation failed: {e}")
        return False


def test_7_error_handling() -> bool:
    """Test 7: Verify error handling and fallback mechanisms"""
    print("\n=== Test 7: Error Handling ===")
    
    try:
        # Create mock adapter that raises errors
        mock_adapter = MagicMock()
        
        async def failing_method() -> None:
            raise Exception("Simulated collection failure")
        
        mock_adapter._get_validated_system_metrics = failing_method
        mock_adapter.get_performance_stats.return_value = {"success_rate": 30.0}  # Low success rate
        
        # Create collector
        collector = BackgroundDataCollector(mock_adapter)
        
        # Test error handling in collection stats update
        collector._update_collection_stats("analytics", 0, success=False)
        stats = collector.collection_stats["analytics"]
        assert stats["failed"] == 1
        assert stats["total"] == 1
        
        # Test health monitoring with low success rate
        collector.health_monitor.update_component_health("data_adapter", HealthStatus.CRITICAL,
                                                        {"success_rate": 30.0})
        
        health_summary = collector.get_health_status()
        assert health_summary["overall_status"] == "critical"
        
        # Test buffer failure recording
        buffer = collector.buffers["analytics"]
        initial_success_rate = buffer.get_success_rate()
        buffer.record_failed_collection()
        assert buffer.get_success_rate() < initial_success_rate
        
        print("✅ Error handling working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def test_8_global_instance_management() -> bool:
    """Test 8: Verify global instance management"""
    print("\n=== Test 8: Global Instance Management ===")
    
    try:
        # Test getting global instance
        collector1 = get_background_collector()
        collector2 = get_background_collector()
        
        # Should be the same instance (singleton pattern)
        assert collector1 is collector2
        
        # Test initialization with custom adapter
        mock_adapter = MagicMock()
        collector3 = initialize_background_collector(mock_adapter)
        
        # Should be a new instance with the custom adapter
        assert collector3.data_adapter is mock_adapter
        
        # Getting global instance again should return the new one
        collector4 = get_background_collector()
        assert collector4 is collector3
        
        print("✅ Global instance management working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Global instance management test failed: {e}")
        return False


def test_9_comprehensive_integration() -> bool:
    """Test 9: Comprehensive integration test"""
    print("\n=== Test 9: Comprehensive Integration ===")
    
    try:
        # Create comprehensive mock adapter
        mock_adapter = MagicMock()
        
        # Create realistic test data
        system_data = SystemMetricsData(
            active_nodes=150, active_edges=300, query_rate=75.0,
            cache_hit_rate=0.92, memory_usage=68.5, cpu_usage=42.1,
            response_time=95.0, uptime_seconds=7200.0,
            timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
        )
        
        memory_data = MemoryInsightsData(
            total_memories=1500, procedural_memories=500, semantic_memories=600,
            episodic_memories=400, memory_efficiency=0.88, memory_growth_rate=0.03,
            avg_memory_size=2048.0, compression_ratio=1.5, retrieval_speed=75.0,
            timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
        )
        
        graph_data = GraphMetricsData(
            node_count=750, edge_count=1500, connected_components=3,
            largest_component_size=700, diameter=12, density=0.0027,
            clustering_coefficient=0.35, avg_centrality=0.015, modularity=0.6,
            timestamp=datetime.now().isoformat(), status=AnalyticsStatus.HEALTHY
        )
        
        # Mock async methods
        async def mock_system() -> SystemMetricsData: return system_data
        async def mock_memory() -> MemoryInsightsData: return memory_data
        async def mock_graph() -> GraphMetricsData: return graph_data
        
        mock_adapter._get_validated_system_metrics = mock_system
        mock_adapter._get_validated_memory_insights = mock_memory
        mock_adapter._get_validated_graph_metrics = mock_graph
        mock_adapter.get_performance_stats.return_value = {
            "success_rate": 98.5,
            "cache_hit_rate": 85.0,
            "average_transform_times": {"system": 0.1, "memory": 0.2, "graph": 0.15}
        }
        
        # Initialize collector
        collector = initialize_background_collector(mock_adapter)
        
        # Simulate multiple collection cycles
        async def run_collection_cycles() -> None:
            for i in range(5):
                # Collect all data types
                analytics_data = await mock_adapter._get_validated_system_metrics()
                memory_insights = await mock_adapter._get_validated_memory_insights()
                graph_metrics = await mock_adapter._get_validated_graph_metrics()
                
                # Add to buffers with varying collection times
                collector.buffers["analytics"].add_data_point(analytics_data, 0.1 + i * 0.01)
                collector.buffers["memory"].add_data_point(memory_insights, 0.2 + i * 0.01)
                collector.buffers["graph"].add_data_point(graph_metrics, 0.15 + i * 0.01)
                
                # Update collection stats
                collector._update_collection_stats("analytics", 0.1 + i * 0.01, True)
                collector._update_collection_stats("memory", 0.2 + i * 0.01, True)
                collector._update_collection_stats("graph", 0.15 + i * 0.01, True)
        
        # Run the simulation
        asyncio.run(run_collection_cycles())
        
        # Verify comprehensive functionality
        
        # 1. Data collection
        assert len(collector.buffers["analytics"].data) == 5
        assert len(collector.buffers["memory"].data) == 5
        assert len(collector.buffers["graph"].data) == 5
        
        # 2. Recent data retrieval
        recent_analytics = collector.get_recent_data("analytics", 3)
        assert len(recent_analytics) == 3
        
        # 3. Aggregated data
        agg_analytics = collector.get_aggregated_data("analytics", 1)
        assert agg_analytics is not None
        assert agg_analytics.count == 5
        
        # 4. Collection statistics
        stats = collector.get_collection_stats()
        assert stats["collection_stats"]["analytics"]["total"] == 5
        assert stats["collection_stats"]["analytics"]["failed"] == 0
        
        # 5. Health monitoring
        collector.health_monitor.update_component_health("analytics_collection", HealthStatus.HEALTHY)
        collector.health_monitor.update_component_health("memory_collection", HealthStatus.HEALTHY)
        collector.health_monitor.update_component_health("graph_collection", HealthStatus.HEALTHY)
        
        health_status = collector.get_health_status()
        assert health_status["overall_status"] == "healthy"
        
        # 6. Buffer statistics
        for buffer_name, buffer in collector.buffers.items():
            buffer_stats = buffer.get_buffer_stats()
            assert buffer_stats["success_rate"] == 1.0
            assert buffer_stats["size"] == 5
        
        print("✅ Comprehensive integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive integration test failed: {e}")
        return False


def run_all_tests() -> bool:
    """Run all background collector tests"""
    print("🚀 Starting Background Data Collection System Tests")
    print("=" * 60)
    
    tests = [
        test_1_background_collector_imports,
        test_2_data_buffer_functionality,
        test_3_health_monitor_functionality,
        test_4_background_collector_basic,
        test_5_data_aggregation,
        test_6_async_collection_simulation,
        test_7_error_handling,
        test_8_global_instance_management,
        test_9_comprehensive_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{len(tests)} passed")
    
    if failed == 0:
        print("🎉 All tests passed! Background Data Collection System is ready.")
    else:
        print(f"⚠️  {failed} test(s) failed. Please review the issues above.")
    
    return failed == 0


if __name__ == "__main__":
    run_all_tests() 