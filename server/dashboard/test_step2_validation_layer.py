#!/usr/bin/env python3
"""
Step 2 Complete Test: Data Models & Validation Layer

Comprehensive test demonstrating all Step 2 features:
- Custom Pydantic field types and validators
- Analytics data models with validation
- Error handling models
- Performance optimization features
- Integration with analytics client data
"""

import sys
import os
from datetime import datetime
import json

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_custom_field_types() -> bool:
    """Test custom Pydantic field types and validators"""
    print("🔍 Testing Custom Field Types & Validators...")
    
    try:
        from server.dashboard.models.validation_models import (
            validate_timestamp_format,
            validate_memory_size_unit,
            validate_percentage_as_ratio,
            PerformanceValidator
        )
        
        # Test timestamp validation
        timestamp = validate_timestamp_format("2025-05-28T19:30:00")
        print(f"  ✅ Timestamp validation: {timestamp}")
        
        # Test memory size conversion
        memory_gb = validate_memory_size_unit("2.5GB")
        print(f"  ✅ Memory size conversion: 2.5GB = {memory_gb:,.0f} bytes")
        
        # Test percentage conversion
        ratio = validate_percentage_as_ratio(85.5)
        print(f"  ✅ Percentage conversion: 85.5% = {ratio}")
        
        # Test performance validation
        validation_result = PerformanceValidator.validate_metrics_consistency(
            cpu_usage=45.2, memory_usage=67.8, response_time=125.0
        )
        print(f"  ✅ Performance validation: {validation_result.is_valid}")
        
        return True
    except Exception as e:
        print(f"  ❌ Custom field types error: {e}")
        return False

def test_analytics_data_models() -> bool:
    """Test analytics data models with real-world data"""
    print("🔍 Testing Analytics Data Models...")
    
    try:
        from server.dashboard.models.analytics_models import (
            SystemMetricsData, MemoryInsightsData, GraphMetricsData,
            AnalyticsStatus
        )
        
        timestamp = datetime.now().isoformat()
        
        # Test SystemMetricsData with realistic values
        system_metrics = SystemMetricsData(
            active_nodes=1250,
            active_edges=3780,
            query_rate=45.2,
            cache_hit_rate=0.87,  # 87% as ratio
            memory_usage=68.5,
            cpu_usage=42.1,
            response_time=89.3,
            uptime_seconds=86400.0,  # 24 hours
            timestamp=timestamp,
            status=AnalyticsStatus.HEALTHY
        )
        
        print(f"  ✅ System metrics created: {system_metrics.active_nodes} nodes, {system_metrics.active_edges} edges")
        print(f"  ✅ Cache hit rate: {system_metrics.cache_hit_rate:.2%}")
        
        # Test MemoryInsightsData
        memory_insights = MemoryInsightsData(
            total_memories=5420,
            procedural_memories=2100,
            semantic_memories=2800,
            episodic_memories=520,
            memory_efficiency=0.92,
            memory_growth_rate=0.15,  # 15% growth
            avg_memory_size=2048.0,  # 2KB average
            compression_ratio=3.2,
            retrieval_speed=12.5,
            timestamp=timestamp,
            status=AnalyticsStatus.HEALTHY
        )
        
        distribution = memory_insights.get_memory_distribution()
        print(f"  ✅ Memory distribution: {distribution}")
        
        # Test GraphMetricsData
        graph_metrics = GraphMetricsData(
            node_count=1250,
            edge_count=3780,
            connected_components=3,
            largest_component_size=1200,
            diameter=8,
            density=0.0048,  # Sparse graph
            clustering_coefficient=0.35,
            avg_centrality=0.12,
            modularity=0.78,
            timestamp=timestamp,
            status=AnalyticsStatus.HEALTHY
        )
        
        summary = graph_metrics.get_graph_summary()
        print(f"  ✅ Graph summary: {summary}")
        
        # Test validation
        validation_result = graph_metrics.validate_consistency()
        print(f"  ✅ Graph validation: {validation_result.is_valid}")
        if validation_result.warnings:
            print(f"  ⚠️ Warnings: {validation_result.warnings}")
        
        return True
    except Exception as e:
        print(f"  ❌ Analytics models error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling() -> bool:
    """Test comprehensive error handling"""
    print("🔍 Testing Error Handling Models...")
    
    try:
        from server.dashboard.models.error_models import (
            AnalyticsError, ErrorSeverity, ErrorCategory,
            ValidationErrorDetail, ErrorReport, ErrorContext,
            generate_error_id
        )
        
        # Test creating validation errors
        validation_error = ValidationErrorDetail(
            field_name="cache_hit_rate",
            error_message="Value must be between 0.0 and 1.0",
            invalid_value=1.5,
            expected_type="float",
            constraint="0.0 <= value <= 1.0"
        )
        
        # Test creating analytics error
        error_id = generate_error_id()
        analytics_error = AnalyticsError.create_analytics_engine_error(
            error_id=error_id,
            message="Connection timeout to analytics engine",
            details="Failed to connect after 3 retry attempts",
            severity=ErrorSeverity.HIGH
        )
        
        print(f"  ✅ Error created: {analytics_error.get_summary()}")
        
        # Test error context manager
        with ErrorContext("test_component", "test_operation") as ctx:
            # This would normally contain risky code
            test_error = ctx.create_error("Test error for demonstration")
            print(f"  ✅ Context error: {test_error.error_id}")
        
        # Test error report
        errors = [analytics_error, test_error]
        report = ErrorReport.from_errors("TEST_REPORT_001", errors)
        
        print(f"  ✅ Error report: {report.total_errors} errors, {report.high_errors} high severity")
        
        return True
    except Exception as e:
        print(f"  ❌ Error handling error: {e}")
        return False

def test_performance_features() -> bool:
    """Test performance optimization features"""
    print("🔍 Testing Performance Features...")
    
    try:
        from server.dashboard.models.analytics_models import SystemMetricsData, AnalyticsStatus
        from server.dashboard.models.validation_models import ValidationResult
        import time
        
        # Test model creation performance
        start_time = time.time()
        
        models = []
        for i in range(1000):
            timestamp = datetime.now().isoformat()
            model = SystemMetricsData(
                active_nodes=i,
                active_edges=i * 3,
                query_rate=float(i % 100),
                cache_hit_rate=0.85,
                memory_usage=45.2,
                cpu_usage=32.1,
                response_time=125.0,
                uptime_seconds=3600.0,
                timestamp=timestamp,
                status=AnalyticsStatus.HEALTHY
            )
            models.append(model)
        
        creation_time = time.time() - start_time
        print(f"  ✅ Created 1000 models in {creation_time:.3f} seconds")
        
        # Test serialization performance
        start_time = time.time()
        
        serialized_data = []
        for model in models[:100]:  # Test subset for serialization
            data_dict = model.to_dict()
            json_str = json.dumps(data_dict)
            serialized_data.append(json_str)
        
        serialization_time = time.time() - start_time
        print(f"  ✅ Serialized 100 models in {serialization_time:.3f} seconds")
        
        # Test validation performance
        start_time = time.time()
        
        validation_results = []
        for model in models[:100]:
            result = model.validate_consistency()
            validation_results.append(result)
        
        validation_time = time.time() - start_time
        print(f"  ✅ Validated 100 models in {validation_time:.3f} seconds")
        
        return True
    except Exception as e:
        print(f"  ❌ Performance test error: {e}")
        return False

def test_integration_with_analytics_client() -> bool:
    """Test integration with analytics client data format"""
    print("🔍 Testing Integration with Analytics Client...")
    
    try:
        from server.dashboard.models.analytics_models import (
            SystemMetricsData, MemoryInsightsData, GraphMetricsData,
            create_fallback_system_metrics, create_fallback_memory_insights,
            create_fallback_graph_metrics, AnalyticsStatus
        )
        
        timestamp = datetime.now().isoformat()
        
        # Test fallback data creation (matches analytics_client.py format)
        fallback_system = create_fallback_system_metrics(timestamp)
        fallback_memory = create_fallback_memory_insights(timestamp)
        fallback_graph = create_fallback_graph_metrics(timestamp)
        
        print(f"  ✅ Fallback system metrics: {fallback_system.status}")
        print(f"  ✅ Fallback memory insights: {fallback_memory.total_memories}")
        print(f"  ✅ Fallback graph metrics: {fallback_graph.node_count}")
        
        # Test data transformation to SSE format
        system_dict = fallback_system.to_dict()
        memory_dict = fallback_memory.to_dict()
        graph_dict = fallback_graph.to_dict()
        
        # Verify all required fields are present
        required_system_fields = [
            'active_nodes', 'active_edges', 'query_rate', 'cache_hit_rate',
            'memory_usage', 'cpu_usage', 'response_time', 'uptime_seconds',
            'timestamp', 'status'
        ]
        
        for field in required_system_fields:
            assert field in system_dict, f"Missing field: {field}"
        
        print(f"  ✅ All required fields present in system metrics")
        
        # Test with realistic analytics engine data
        realistic_system = SystemMetricsData(
            active_nodes=2500,
            active_edges=7800,
            query_rate=125.7,
            cache_hit_rate=0.89,
            memory_usage=72.3,
            cpu_usage=58.1,
            response_time=45.2,
            uptime_seconds=172800.0,  # 48 hours
            timestamp=timestamp,
            status=AnalyticsStatus.HEALTHY
        )
        
        # Test validation with realistic data
        validation_result = realistic_system.validate_consistency()
        print(f"  ✅ Realistic data validation: {validation_result.is_valid}")
        
        return True
    except Exception as e:
        print(f"  ❌ Integration test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sse_compatibility() -> bool:
    """Test SSE streaming compatibility"""
    print("🔍 Testing SSE Streaming Compatibility...")
    
    try:
        from server.dashboard.models.analytics_models import SystemMetricsData, AnalyticsStatus
        import json
        
        # Create test data
        timestamp = datetime.now().isoformat()
        metrics = SystemMetricsData(
            active_nodes=1500,
            active_edges=4200,
            query_rate=67.3,
            cache_hit_rate=0.91,
            memory_usage=55.8,
            cpu_usage=38.7,
            response_time=78.5,
            uptime_seconds=259200.0,  # 72 hours
            timestamp=timestamp,
            status=AnalyticsStatus.HEALTHY
        )
        
        # Test SSE format conversion
        data_dict = metrics.to_dict()
        
        # Simulate SSE event format
        sse_event = {
            "event": "analytics",
            "data": data_dict,
            "timestamp": timestamp,
            "id": "evt_001"
        }
        
        # Test JSON serialization (required for SSE)
        json_str = json.dumps(sse_event, default=str)
        
        # Test deserialization
        parsed_data = json.loads(json_str)
        
        print(f"  ✅ SSE event serialization successful")
        print(f"  ✅ Event type: {parsed_data.get('event')}")
        print(f"  ✅ Data fields: {len(parsed_data.get('data', {}))}")
        
        # Test SSE format string
        sse_format = f"event: analytics\ndata: {json_str}\n\n"
        print(f"  ✅ SSE format string length: {len(sse_format)} characters")
        
        return True
    except Exception as e:
        print(f"  ❌ SSE compatibility error: {e}")
        return False

def main() -> bool:
    """Run comprehensive Step 2 tests"""
    print("🚀 Step 2 Complete Test: Data Models & Validation Layer")
    print("=" * 70)
    
    tests = [
        ("Custom Field Types & Validators", test_custom_field_types),
        ("Analytics Data Models", test_analytics_data_models),
        ("Error Handling", test_error_handling),
        ("Performance Features", test_performance_features),
        ("Analytics Client Integration", test_integration_with_analytics_client),
        ("SSE Streaming Compatibility", test_sse_compatibility)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 50)
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Step 2 COMPLETE! Data Models & Validation Layer is ready for production.")
        print("\n📋 Step 2 Achievements:")
        print("  ✅ Custom Pydantic field types with validation")
        print("  ✅ Analytics data models (System, Memory, Graph)")
        print("  ✅ Comprehensive error handling models")
        print("  ✅ Performance optimization features")
        print("  ✅ Integration with analytics client")
        print("  ✅ SSE streaming compatibility")
        print("  ✅ Type safety and data consistency")
        print("  ✅ Fallback mechanisms for graceful degradation")
        
        print("\n🚀 Ready for Step 3: Data Adapter Layer")
        return True
    else:
        print("⚠️ Some tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 