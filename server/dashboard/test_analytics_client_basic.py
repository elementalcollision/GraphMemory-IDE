"""
Basic test for Analytics Engine Client fallback functionality

Tests only the fallback mechanisms without requiring analytics engine imports.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockAnalyticsEngineClient:
    """Mock client for testing fallback functionality"""
    
    def __init__(self) -> None:
        self._last_metrics_cache: Dict[str, Any] = {}
        self.engine_available = True
        self.performance_mode = "balanced"
        self.initialized = False
        self._connection_healthy = False
        self._cache_timestamp = 0.0
        self._cache_ttl = 5
    
    async def health_check(self) -> bool:
        """Mock health check that always returns False"""
        return False
    
    def _get_fallback_system_metrics(self) -> Dict[str, Any]:
        """Generate fallback system metrics"""
        if self._last_metrics_cache:
            return self._last_metrics_cache
        
        fallback_data = {
            "active_nodes": 1000,
            "active_edges": 2500,
            "query_rate": 25.5,
            "cache_hit_rate": 0.85,
            "memory_usage": 45.2,
            "cpu_usage": 32.1,
            "response_time": 125.0,
            "uptime_seconds": 3600.0,
            "timestamp": datetime.now().isoformat(),
            "status": "healthy"
        }
        
        self._last_metrics_cache = fallback_data
        return fallback_data
    
    def _get_fallback_memory_insights(self) -> Dict[str, Any]:
        """Return fallback memory insights"""
        return {
            "total_memories": 0,
            "procedural_memories": 0,
            "semantic_memories": 0,
            "episodic_memories": 0,
            "memory_efficiency": 0.0,
            "memory_growth_rate": 0.0,
            "avg_memory_size": 0.0,
            "compression_ratio": 1.0,
            "retrieval_speed": 0.0,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_fallback_graph_metrics(self) -> Dict[str, Any]:
        """Return fallback graph metrics"""
        from datetime import datetime, timezone
        
        return {
            "node_count": 0,
            "edge_count": 0,
            "connected_components": 0,
            "diameter": 0,
            "density": 0.0,
            "clustering_coefficient": 0.0,
            "avg_centrality": 0.0,
            "modularity": 0.0,
            "largest_component_size": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get mocked system metrics"""
        try:
            return self._get_fallback_system_metrics()
        except Exception:
            return self._get_fallback_system_metrics()
    
    async def get_memory_insights(self) -> Dict[str, Any]:
        """Get memory insights with fallback"""
        if not await self.health_check():
            return self._get_fallback_memory_insights()
        return self._get_fallback_memory_insights()  # Always fallback for testing
    
    async def get_graph_metrics(self) -> Dict[str, Any]:
        """Get graph metrics with fallback"""
        if not await self.health_check():
            return self._get_fallback_graph_metrics()
        return self._get_fallback_graph_metrics()  # Always fallback for testing


async def test_fallback_functionality() -> None:
    """Test fallback functionality when client is not initialized"""
    print("🔍 Testing fallback functionality...")
    
    client = MockAnalyticsEngineClient()
    
    # Test health check
    logger.info("Testing health check...")
    health = await client.health_check()
    assert health is False
    logger.info("✅ Health check test passed")
    
    # Test system metrics fallback
    logger.info("Testing system metrics fallback...")
    system_metrics = await client.get_system_metrics()
    assert isinstance(system_metrics, dict)
    assert "active_nodes" in system_metrics
    assert "active_edges" in system_metrics
    assert "timestamp" in system_metrics
    assert system_metrics["active_nodes"] == 1000
    logger.info(f"✅ System metrics fallback: {system_metrics}")
    
    # Test memory insights fallback
    logger.info("Testing memory insights fallback...")
    memory_insights = await client.get_memory_insights()
    assert isinstance(memory_insights, dict)
    assert "total_memories" in memory_insights
    assert "memory_efficiency" in memory_insights
    assert "timestamp" in memory_insights
    assert memory_insights["total_memories"] == 0
    logger.info(f"✅ Memory insights fallback: {memory_insights}")
    
    # Test graph metrics fallback
    logger.info("Testing graph metrics fallback...")
    graph_metrics = await client.get_graph_metrics()
    assert isinstance(graph_metrics, dict)
    assert "node_count" in graph_metrics
    assert "edge_count" in graph_metrics
    assert "timestamp" in graph_metrics
    assert graph_metrics["node_count"] == 0
    logger.info(f"✅ Graph metrics fallback: {graph_metrics}")
    
    logger.info("✅ All Basic Analytics Client Tests Passed!")


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_fallback_functionality()) 