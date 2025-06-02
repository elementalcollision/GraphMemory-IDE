"""
Integration tests for Analytics Integration Layer

Tests the complete analytics integration including:
- Analytics Engine functionality
- Gateway orchestration
- Service Registry operations
- End-to-end workflows
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
from datetime import datetime, timezone

# Import the modules we're testing
from server.analytics.kuzu_analytics import KuzuAnalyticsEngine, GraphAnalyticsType, GraphMetrics
from server.analytics.gateway import AnalyticsGateway, GatewayRequest, GatewayResponse
from server.analytics.service_registry import AnalyticsServiceRegistry, ServiceEndpoint, ServiceType, ServiceHealth


class TestKuzuAnalyticsEngine:
    """Test suite for KuzuAnalyticsEngine"""
    
    @pytest.fixture
    def mock_connection(self) -> None:
        """Mock Kuzu database connection"""
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.get_column_names.return_value = ["count"]
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = [42]
        mock_conn.execute.return_value = mock_result
        return mock_conn
    
    @pytest.fixture
    def analytics_engine(self, mock_connection) -> None:
        """Create analytics engine with mocked connection"""
        return KuzuAnalyticsEngine(mock_connection)
    
    @pytest.mark.asyncio
    async def test_execute_graph_analytics_centrality(self, analytics_engine) -> None:
        """Test centrality analysis execution"""
        parameters = {
            "entity_type": "Entity",
            "algorithm": "degree_centrality",
            "limit": 10
        }
        
        with patch.object(analytics_engine, '_compute_centrality') as mock_compute:
            mock_compute.return_value = {
                "entity_type": "Entity",
                "algorithm": "degree_centrality",
                "entities": [{"entity_id": "test", "degree": 5}],
                "entity_count": 1
            }
            
            result = await analytics_engine.execute_graph_analytics(
                GraphAnalyticsType.CENTRALITY,
                parameters
            )
            
            assert result["entity_type"] == "Entity"
            assert "execution_time_ms" in result
            assert "timestamp" in result
            mock_compute.assert_called_once_with(parameters)
    
    @pytest.mark.asyncio
    async def test_get_graph_metrics(self, analytics_engine) -> None:
        """Test graph metrics computation"""
        # Mock the cypher execution for different queries
        with patch.object(analytics_engine, '_execute_cypher') as mock_cypher:
            mock_cypher.side_effect = [
                [{"count": 100}],  # node count
                [{"count": 200}],  # edge count
                [{"components": 5, "largest_component": 80}]  # components
            ]
            
            with patch.object(analytics_engine, '_compute_global_clustering_coefficient') as mock_clustering:
                mock_clustering.return_value = 0.3
                
                with patch.object(analytics_engine, '_estimate_graph_diameter') as mock_diameter:
                    mock_diameter.return_value = 6
                    
                    metrics = await analytics_engine.get_graph_metrics()
                    
                    assert isinstance(metrics, GraphMetrics)
                    assert metrics.node_count == 100
                    assert metrics.edge_count == 200
                    assert metrics.connected_components == 5
                    assert metrics.largest_component_size == 80
                    assert metrics.clustering_coefficient == 0.3
                    assert metrics.diameter == 6
    
    @pytest.mark.asyncio
    async def test_find_shortest_paths(self, analytics_engine) -> None:
        """Test shortest path finding"""
        with patch.object(analytics_engine, '_execute_cypher') as mock_cypher:
            mock_cypher.return_value = [
                {"path": "mock_path", "path_length": 3}
            ]
            
            result = await analytics_engine.find_shortest_paths(
                source_node="A",
                target_node="B",
                max_hops=5
            )
            
            assert result["source_node"] == "A"
            assert result["target_node"] == "B"
            assert result["max_hops"] == 5
            assert result["path_count"] == 1
    
    def test_caching_mechanism(self, analytics_engine) -> None:
        """Test analytics result caching"""
        analytics_type = GraphAnalyticsType.CENTRALITY
        parameters = {"test": "data"}
        result = {"cached": "result"}
        
        # Cache a result
        analytics_engine._cache_result(analytics_type, parameters, result)
        
        # Retrieve cached result
        cached = analytics_engine._get_cached_result(analytics_type, parameters)
        assert cached == result
        
        # Test cache miss
        different_params = {"different": "data"}
        cached_miss = analytics_engine._get_cached_result(analytics_type, different_params)
        assert cached_miss is None


class TestAnalyticsGateway:
    """Test suite for AnalyticsGateway"""
    
    @pytest.fixture
    def mock_service_registry(self) -> None:
        """Mock service registry"""
        registry = Mock()
        registry.discover_services = AsyncMock()
        registry.update_service_metrics = AsyncMock()
        return registry
    
    @pytest.fixture
    def analytics_gateway(self, mock_service_registry) -> None:
        """Create analytics gateway with mocked dependencies"""
        return AnalyticsGateway(mock_service_registry)
    
    @pytest.mark.asyncio
    async def test_gateway_initialization(self, analytics_gateway) -> None:
        """Test gateway initialization and startup"""
        await analytics_gateway.start(num_workers=2)
        
        assert len(analytics_gateway._workers) == 2
        assert not analytics_gateway._shutdown_event.is_set()
        
        await analytics_gateway.stop()
        assert analytics_gateway._shutdown_event.is_set()
        assert len(analytics_gateway._workers) == 0
    
    @pytest.mark.asyncio
    async def test_execute_request_with_cache(self, analytics_gateway) -> None:
        """Test request execution with caching"""
        # Wrap the entire test in a timeout to prevent hanging
        async def run_test() -> None:
            # Start the gateway with workers (this was missing!)
            await analytics_gateway.start(num_workers=1)
            
            try:
                # Setup mock service
                mock_service = Mock()
                mock_service.service_id = "test-service"
                mock_service.endpoint_url = "http://localhost:8000"
                
                analytics_gateway.service_registry.discover_services.return_value = [mock_service]
                
                # Mock the actual HTTP request method directly to avoid complex aiohttp mocking
                async def mock_execute_service_request(request) -> None:
                    """Mock implementation that returns a successful response"""
                    return GatewayResponse(
                        request_id=request.request_id,
                        service=request.service,
                        operation=request.operation,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        execution_time_ms=50.0,
                        status="success",
                        data={"result": "success"},
                        metadata={"selected_service": "test-service"}
                    )
                
                # Replace the actual service request method with our mock
                original_method = analytics_gateway._execute_service_request
                analytics_gateway._execute_service_request = mock_execute_service_request
                
                try:
                    # First request (should hit service)
                    result1 = await analytics_gateway.execute_request(
                        service="analytics_engine",
                        operation="test_operation",
                        data={"test": "data"},
                        use_cache=True
                    )
                    
                    assert result1.status == "success"
                    assert result1.data == {"result": "success"}
                    
                    # Second identical request (should hit cache)
                    result2 = await analytics_gateway.execute_request(
                        service="analytics_engine",
                        operation="test_operation",
                        data={"test": "data"},
                        use_cache=True
                    )
                    
                    assert result2.status == "success"
                    # Check that caching is working (either cache_hit metadata or cached_responses stat)
                    cache_working = (
                        "cache_hit" in result2.metadata 
                        or analytics_gateway.gateway_stats["cached_responses"] > 0
                    )
                    assert cache_working, "Caching should be working for identical requests"
                    
                finally:
                    # Restore original method
                    analytics_gateway._execute_service_request = original_method
                    
            finally:
                # Always stop the gateway
                await analytics_gateway.stop()
        
        # Run the test with a 30-second timeout
        try:
            await asyncio.wait_for(run_test(), timeout=30.0)
        except asyncio.TimeoutError:
            pytest.fail("Test timed out after 30 seconds - indicates a blocking operation")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, analytics_gateway) -> None:
        """Test circuit breaker pattern"""
        service_name = "failing-service"
        
        # Simulate multiple failures
        for _ in range(6):  # Exceed failure threshold
            analytics_gateway._record_failure(service_name)
        
        # Circuit breaker should be open
        assert analytics_gateway._is_circuit_breaker_open(service_name)
        
        # Test that requests are blocked with HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await analytics_gateway.execute_request(
                service=service_name,
                operation="test"
            )
        
        # Verify it's the circuit breaker error
        http_exc = exc_info.value
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 503
        assert "circuit breaker open" in str(http_exc.detail)
    
    @pytest.mark.asyncio
    async def test_batch_request_execution(self, analytics_gateway) -> None:
        """Test batch request processing"""
        requests = [
            {
                "service": "analytics_engine",
                "operation": "centrality",
                "data": {"entity_type": "Entity"}
            },
            {
                "service": "analytics_engine", 
                "operation": "clustering",
                "data": {"min_cluster_size": 3}
            }
        ]
        
        # Mock the individual request execution
        with patch.object(analytics_gateway, 'execute_request') as mock_execute:
            mock_execute.side_effect = [
                GatewayResponse(
                    request_id="1",
                    service="analytics_engine",
                    operation="centrality",
                    timestamp="2025-05-29T12:00:00",
                    execution_time_ms=100.0,
                    status="success",
                    data={"result": "centrality_data"},
                    metadata={}
                ),
                GatewayResponse(
                    request_id="2",
                    service="analytics_engine",
                    operation="clustering",
                    timestamp="2025-05-29T12:00:01",
                    execution_time_ms=150.0,
                    status="success",
                    data={"result": "clustering_data"},
                    metadata={}
                )
            ]
            
            results = await analytics_gateway.execute_batch_requests(requests)
            
            assert len(results) == 2
            assert all(isinstance(r, GatewayResponse) for r in results)
            assert results[0].operation == "centrality"
            assert results[1].operation == "clustering"
    
    def test_load_balancing(self, analytics_gateway) -> None:
        """Test round-robin load balancing"""
        services = [Mock(service_id=f"service-{i}") for i in range(3)]
        service_type = "analytics_engine"
        
        # Test round-robin selection
        selected_services = []
        for _ in range(6):  # Two full rounds
            selected = analytics_gateway._select_service(services, service_type)
            selected_services.append(selected.service_id)
        
        # Should cycle through services
        expected = ["service-0", "service-1", "service-2"] * 2
        assert selected_services == expected


class TestServiceRegistry:
    """Test suite for AnalyticsServiceRegistry"""
    
    @pytest.fixture
    def service_registry(self) -> None:
        """Create service registry"""
        return AnalyticsServiceRegistry()
    
    @pytest.mark.asyncio
    async def test_service_registration(self, service_registry) -> None:
        """Test service registration and discovery"""
        # Disable automatic health checks for testing
        with patch.object(service_registry, '_check_service_health', new_callable=AsyncMock):
            # Register service using the correct method signature
            service = await service_registry.register_service(
                service_id="test-analytics",
                service_name="Test Analytics Service", 
                service_type=ServiceType.ANALYTICS_ENGINE,
                endpoint_url="http://localhost:8001",
                capabilities=["centrality", "clustering"],
                version="1.0.0"
            )
            
            # Manually set as healthy for testing
            service.health_status = ServiceHealth.HEALTHY
            
            # Test discovery
            services = await service_registry.discover_services(
                service_type=ServiceType.ANALYTICS_ENGINE,
                healthy_only=True
            )
            
            assert len(services) == 1
            assert services[0].service_id == "test-analytics"
            assert services[0].service_type == ServiceType.ANALYTICS_ENGINE
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, service_registry) -> None:
        """Test health monitoring functionality"""
        # Register service using the correct method signature
        service = await service_registry.register_service(
            service_id="health-test",
            service_name="Health Test Service",
            service_type=ServiceType.ANALYTICS_ENGINE,
            endpoint_url="http://localhost:8002",
            capabilities=["test"],
            version="1.0.0"
        )
        
        # Mock health check failure
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception("Connection failed")
            
            await service_registry._check_service_health(service)
            
            # Service should be marked as unhealthy
            updated_service = service_registry.services["health-test"]
            assert updated_service.health_status == ServiceHealth.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_service_metrics_update(self, service_registry) -> None:
        """Test service metrics tracking"""
        # Register service using the correct method signature
        service = await service_registry.register_service(
            service_id="metrics-test",
            service_name="Metrics Test Service",
            service_type=ServiceType.ANALYTICS_ENGINE,
            endpoint_url="http://localhost:8003",
            capabilities=["metrics"],
            version="1.0.0"
        )
        
        # Update metrics
        await service_registry.update_service_metrics(
            service_id="metrics-test",
            response_time=150.0,
            request_count_increment=1,
            error_count_increment=0
        )
        
        # Check that metrics were updated
        updated_service = await service_registry.get_service("metrics-test")
        assert updated_service is not None
        assert updated_service.request_count == 1
        assert updated_service.average_response_time == 150.0


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_analytics_workflow(self) -> None:
        """Test complete analytics workflow from request to response"""
        # This would be a comprehensive test that exercises the entire system
        # For now, we'll create a simplified version
        
        # Mock components
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.get_column_names.return_value = ["entity_id", "degree"]
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = ["entity_1", 5]
        mock_connection.execute.return_value = mock_result
        
        # Create analytics engine
        analytics_engine = KuzuAnalyticsEngine(mock_connection)
        
        # Test analytics execution
        result = await analytics_engine.execute_graph_analytics(
            GraphAnalyticsType.CENTRALITY,
            {"entity_type": "Entity", "algorithm": "degree_centrality"}
        )
        
        assert "execution_time_ms" in result
        assert "timestamp" in result
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self) -> None:
        """Test error handling and recovery mechanisms"""
        # Test with failing connection
        mock_connection = Mock()
        mock_connection.execute.side_effect = Exception("Database connection failed")
        
        analytics_engine = KuzuAnalyticsEngine(mock_connection)
        
        # Should handle database errors gracefully
        with pytest.raises(Exception):
            await analytics_engine.execute_graph_analytics(
                GraphAnalyticsType.CENTRALITY,
                {"entity_type": "Entity"}
            )
        
        # Verify error was logged and stats updated appropriately
        assert analytics_engine.analytics_stats["total_queries"] == 0  # No successful queries


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"]) 