"""
Test suite for Analytics Engine Client

Tests the analytics client functionality including initialization,
data collection, error handling, and fallback mechanisms.
"""

import asyncio
import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Optional

from analytics_client import (
    AnalyticsEngineClient, 
    get_analytics_client, 
    initialize_analytics_client,
    shutdown_analytics_client
)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAnalyticsEngineClient:
    """Test cases for AnalyticsEngineClient"""
    
    def __init__(self):
        self.client: Optional[AnalyticsEngineClient] = None
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = AnalyticsEngineClient()
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Reset any global state
        pass
    
    def test_client_initialization(self):
        """Test client initialization without Kuzu connection"""
        assert self.client is not None
        assert not self.client.initialized
        assert not self.client._connection_healthy
        assert self.client.analytics_engine is None
    
    async def test_health_check_uninitialized(self):
        """Test health check when client is not initialized"""
        assert self.client is not None
        result = await self.client.health_check()
        assert result is False
        assert not self.client._connection_healthy
    
    async def test_fallback_system_metrics(self):
        """Test fallback system metrics when analytics engine is unavailable"""
        assert self.client is not None
        result = await self.client.get_system_metrics()
        
        # Should return fallback data structure
        assert isinstance(result, dict)
        assert "active_nodes" in result
        assert "active_edges" in result
        assert "query_rate" in result
        assert "cache_hit_rate" in result
        assert "memory_usage" in result
        assert "cpu_usage" in result
        assert "response_time" in result
        assert "uptime_seconds" in result
        assert "timestamp" in result
        
        # Fallback values should be zeros
        assert result["active_nodes"] == 0
        assert result["active_edges"] == 0
        assert result["query_rate"] == 0.0
        
        logger.info(f"Fallback system metrics: {result}")
    
    async def test_fallback_memory_insights(self):
        """Test fallback memory insights when analytics engine is unavailable"""
        assert self.client is not None
        result = await self.client.get_memory_insights()
        
        # Should return fallback data structure
        assert isinstance(result, dict)
        assert "total_memories" in result
        assert "procedural_memories" in result
        assert "semantic_memories" in result
        assert "episodic_memories" in result
        assert "memory_efficiency" in result
        assert "memory_growth_rate" in result
        assert "avg_memory_size" in result
        assert "compression_ratio" in result
        assert "retrieval_speed" in result
        assert "timestamp" in result
        
        # Fallback values should be zeros/defaults
        assert result["total_memories"] == 0
        assert result["memory_efficiency"] == 0.0
        assert result["compression_ratio"] == 1.0
        
        logger.info(f"Fallback memory insights: {result}")
    
    async def test_fallback_graph_metrics(self):
        """Test fallback graph metrics when analytics engine is unavailable"""
        assert self.client is not None
        result = await self.client.get_graph_metrics()
        
        # Should return fallback data structure
        assert isinstance(result, dict)
        assert "node_count" in result
        assert "edge_count" in result
        assert "connected_components" in result
        assert "diameter" in result
        assert "density" in result
        assert "clustering_coefficient" in result
        assert "avg_centrality" in result
        assert "modularity" in result
        assert "largest_component_size" in result
        assert "timestamp" in result
        
        # Fallback values should be zeros
        assert result["node_count"] == 0
        assert result["edge_count"] == 0
        assert result["density"] == 0.0
        
        logger.info(f"Fallback graph metrics: {result}")
    
    async def test_comprehensive_status_uninitialized(self):
        """Test comprehensive status when client is not initialized"""
        assert self.client is not None
        result = await self.client.get_comprehensive_status()
        
        assert isinstance(result, dict)
        assert result["status"] == "not_initialized"
        assert result["healthy"] is False
        
        logger.info(f"Uninitialized status: {result}")
    
    def test_query_rate_estimation(self):
        """Test query rate estimation"""
        assert self.client is not None
        rate = self.client._estimate_query_rate()
        assert isinstance(rate, float)
        assert rate >= 0
        
        logger.info(f"Estimated query rate: {rate}")
    
    async def test_centrality_calculation_fallback(self):
        """Test centrality calculation fallback"""
        assert self.client is not None
        result = await self.client._calculate_average_centrality()
        assert isinstance(result, float)
        assert result == 0.0  # Should be 0 when no analytics engine
    
    async def test_modularity_calculation_fallback(self):
        """Test modularity calculation fallback"""
        assert self.client is not None
        result = await self.client._calculate_modularity()
        assert isinstance(result, float)
        assert result == 0.0  # Should be 0 when no analytics engine
    
    async def test_caching_mechanism(self):
        """Test caching mechanism for system metrics"""
        assert self.client is not None
        # First call should populate cache
        result1 = await self.client.get_system_metrics()
        
        # Cache should be populated
        assert self.client._last_metrics_cache
        assert self.client._cache_timestamp > 0
        
        # Second call should use cache (within TTL)
        result2 = await self.client.get_system_metrics()
        
        # Results should be identical (from cache)
        assert result1 == result2
        
        logger.info("Caching mechanism working correctly")


class TestGlobalFunctions:
    """Test global utility functions"""
    
    def test_get_analytics_client_singleton(self):
        """Test that get_analytics_client returns singleton instance"""
        client1 = get_analytics_client()
        client2 = get_analytics_client()
        
        assert client1 is client2
        assert isinstance(client1, AnalyticsEngineClient)
    
    async def test_initialize_analytics_client(self):
        """Test global client initialization"""
        # Should handle None connection gracefully
        result = await initialize_analytics_client(None)
        assert result is False  # Should fail without connection
        
        logger.info("Global client initialization test completed")
    
    async def test_shutdown_analytics_client(self):
        """Test global client shutdown"""
        # Should handle shutdown gracefully even if not initialized
        await shutdown_analytics_client()
        logger.info("Global client shutdown test completed")


async def run_all_tests():
    """Run all tests manually"""
    logger.info("Starting Analytics Client Tests...")
    
    # Test client functionality
    client_tests = TestAnalyticsEngineClient()
    
    logger.info("Testing client initialization...")
    client_tests.test_client_initialization()
    
    logger.info("Testing health check (uninitialized)...")
    await client_tests.test_health_check_uninitialized()
    
    logger.info("Testing fallback system metrics...")
    await client_tests.test_fallback_system_metrics()
    
    logger.info("Testing fallback memory insights...")
    await client_tests.test_fallback_memory_insights()
    
    logger.info("Testing fallback graph metrics...")
    await client_tests.test_fallback_graph_metrics()
    
    logger.info("Testing comprehensive status...")
    await client_tests.test_comprehensive_status_uninitialized()
    
    logger.info("Testing query rate estimation...")
    client_tests.test_query_rate_estimation()
    
    logger.info("Testing centrality calculation fallback...")
    await client_tests.test_centrality_calculation_fallback()
    
    logger.info("Testing modularity calculation fallback...")
    await client_tests.test_modularity_calculation_fallback()
    
    logger.info("Testing caching mechanism...")
    await client_tests.test_caching_mechanism()
    
    # Test global functions
    global_tests = TestGlobalFunctions()
    
    logger.info("Testing singleton pattern...")
    global_tests.test_get_analytics_client_singleton()
    
    logger.info("Testing global initialization...")
    await global_tests.test_initialize_analytics_client()
    
    logger.info("Testing global shutdown...")
    await global_tests.test_shutdown_analytics_client()
    
    logger.info("✅ All Analytics Client Tests Passed!")


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(run_all_tests()) 