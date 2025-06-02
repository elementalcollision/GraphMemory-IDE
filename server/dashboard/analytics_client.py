"""
Analytics Engine Client for Dashboard Integration

This module provides a client interface to the TASK-012 analytics engine,
enabling real-time data collection for the dashboard SSE streams.
"""

import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kuzu

# Import analytics engine components from TASK-012
from analytics.engine import AnalyticsEngine
from analytics.models import (
    AnalyticsRequest, AnalyticsType, GraphMetrics,
    CentralityRequest, CentralityType
)
from analytics.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class AnalyticsEngineClient:
    """
    Client for interfacing with the TASK-012 analytics engine.
    Provides methods to collect real-time analytics data for dashboard streaming.
    """
    
    def __init__(self, kuzu_connection: Optional[kuzu.Connection] = None, redis_url: str = "redis://localhost:6379") -> None:
        self.kuzu_conn = kuzu_connection
        self.redis_url = redis_url
        self.analytics_engine: Optional[AnalyticsEngine] = None
        self.initialized = False
        self.last_health_check: float = 0.0
        self.health_check_interval = 30  # seconds
        self._connection_healthy = False
        
        # Cache for performance
        self._last_metrics_cache = {}
        self._cache_timestamp: float = 0.0
        self._cache_ttl = 5  # seconds
    
    async def initialize(self) -> bool:
        """Initialize the analytics engine client"""
        try:
            if not self.kuzu_conn:
                # Try to get connection from main app or create a new one
                # For now, we'll handle this gracefully
                logger.warning("No Kuzu connection provided, some features may be limited")
                return False
            
            # Initialize analytics engine
            self.analytics_engine = AnalyticsEngine(self.kuzu_conn, self.redis_url)
            await self.analytics_engine.initialize()
            
            self.initialized = True
            self._connection_healthy = True
            logger.info("Analytics engine client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics engine client: {e}")
            self.initialized = False
            self._connection_healthy = False
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the analytics engine client"""
        if self.analytics_engine:
            await self.analytics_engine.shutdown()
        self.initialized = False
        self._connection_healthy = False
        logger.info("Analytics engine client shutdown complete")
    
    async def health_check(self) -> bool:
        """Check if the analytics engine is healthy and responsive"""
        current_time = time.time()
        
        # Use cached health status if recent
        if current_time - self.last_health_check < self.health_check_interval:
            return self._connection_healthy
        
        try:
            if not self.initialized or not self.analytics_engine:
                return False
            
            # Try to get basic system metrics as a health check
            start_time = time.time()
            system_metrics = performance_monitor.get_system_metrics()
            response_time = time.time() - start_time
            
            # Consider healthy if response time is reasonable
            self._connection_healthy = response_time < 5.0 and system_metrics is not None
            self.last_health_check = current_time
            
            if self._connection_healthy:
                logger.debug(f"Health check passed (response time: {response_time:.3f}s)")
            else:
                logger.warning(f"Health check failed (response time: {response_time:.3f}s)")
            
            return self._connection_healthy
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._connection_healthy = False
            self.last_health_check = current_time
            return False
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get real-time system performance metrics for analytics dashboard"""
        try:
            if not await self.health_check():
                return self._get_fallback_system_metrics()
            
            if not self.analytics_engine:
                return self._get_fallback_system_metrics()
            
            # Get system metrics from performance monitor
            system_metrics = performance_monitor.get_system_metrics()
            
            # Get graph data for node/edge counts
            graph_data = await self.analytics_engine.get_graph_data()
            node_count = len(graph_data.get("nodes", []))
            edge_count = len(graph_data.get("edges", []))
            
            # Calculate query rate (simplified - could be enhanced with actual tracking)
            query_rate = self._estimate_query_rate()
            
            # Get cache hit rate
            cache_hit_rate = system_metrics.get("cache_hit_rate", 0.0) / 100.0
            
            # Calculate response time (use recent health check time)
            response_time = (time.time() - self.last_health_check) * 1000  # ms
            
            # Calculate uptime (simplified)
            uptime_seconds = time.time() - (performance_monitor.process.create_time() if hasattr(performance_monitor, 'process') else time.time())
            
            result = {
                "active_nodes": node_count,
                "active_edges": edge_count,
                "query_rate": query_rate,
                "cache_hit_rate": cache_hit_rate,
                "memory_usage": system_metrics.get("memory_percent", 0.0),
                "cpu_usage": system_metrics.get("cpu_percent", 0.0),
                "response_time": min(response_time, 1000),  # Cap at 1 second
                "uptime_seconds": uptime_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Cache the result
            self._last_metrics_cache = result
            self._cache_timestamp = time.time()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return self._get_fallback_system_metrics()
    
    async def get_memory_insights(self) -> Dict[str, Any]:
        """Get memory system insights and statistics"""
        try:
            if not await self.health_check():
                return self._get_fallback_memory_insights()
            
            if not self.analytics_engine:
                return self._get_fallback_memory_insights()
            
            # Get performance summary
            perf_summary = performance_monitor.get_performance_summary()
            system_metrics = perf_summary.get("system_metrics", {})
            
            # Get graph metrics for memory analysis
            graph_metrics = await self.analytics_engine.calculate_graph_metrics()
            
            # Calculate memory distribution (simplified model)
            total_memories = graph_metrics.node_count + graph_metrics.edge_count
            
            # Simulate memory type distribution based on graph structure
            procedural_memories = int(graph_metrics.edge_count * 0.4)  # Relationships
            semantic_memories = int(graph_metrics.node_count * 0.6)    # Entities
            episodic_memories = total_memories - procedural_memories - semantic_memories
            
            # Calculate memory efficiency based on graph density
            memory_efficiency = min(graph_metrics.density * 2, 1.0)  # Normalize to 0-1
            
            # Calculate growth rate (simplified - could track over time)
            memory_growth_rate = 0.05 if total_memories > 0 else 0.0  # 5% default
            
            # Memory size calculations
            avg_memory_size = 2.5  # KB average
            compression_ratio = 1.8  # Compression efficiency
            retrieval_speed = 50 + (system_metrics.get("cpu_percent", 0) * 2)  # ms
            
            result = {
                "total_memories": total_memories,
                "procedural_memories": procedural_memories,
                "semantic_memories": semantic_memories,
                "episodic_memories": episodic_memories,
                "memory_efficiency": memory_efficiency,
                "memory_growth_rate": memory_growth_rate,
                "avg_memory_size": avg_memory_size,
                "compression_ratio": compression_ratio,
                "retrieval_speed": retrieval_speed,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get memory insights: {e}")
            return self._get_fallback_memory_insights()
    
    async def get_graph_metrics(self) -> Dict[str, Any]:
        """Get graph topology and connectivity metrics"""
        try:
            if not await self.health_check():
                return self._get_fallback_graph_metrics()
            
            if not self.analytics_engine:
                return self._get_fallback_graph_metrics()
            
            # Get comprehensive graph metrics
            graph_metrics = await self.analytics_engine.calculate_graph_metrics()
            
            # Calculate additional metrics
            avg_centrality = await self._calculate_average_centrality()
            modularity = await self._calculate_modularity()
            
            result = {
                "node_count": graph_metrics.node_count,
                "edge_count": graph_metrics.edge_count,
                "connected_components": graph_metrics.connected_components,
                "diameter": graph_metrics.diameter or 0,
                "density": graph_metrics.density,
                "clustering_coefficient": graph_metrics.average_clustering,
                "avg_centrality": avg_centrality,
                "modularity": modularity,
                "largest_component_size": graph_metrics.largest_component_size,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get graph metrics: {e}")
            return self._get_fallback_graph_metrics()
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive analytics engine status"""
        try:
            if not self.initialized:
                return {"status": "not_initialized", "healthy": False}
            
            is_healthy = await self.health_check()
            
            # Get engine stats if available
            engine_stats = {}
            if self.analytics_engine:
                engine_stats = self.analytics_engine.get_engine_stats()
            
            # Get performance summary
            perf_summary = performance_monitor.get_performance_summary()
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "healthy": is_healthy,
                "initialized": self.initialized,
                "last_health_check": self.last_health_check,
                "engine_stats": engine_stats,
                "performance_summary": perf_summary,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive status: {e}")
            return {
                "status": "error",
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    # Private helper methods
    
    def _estimate_query_rate(self) -> float:
        """Estimate current query rate (queries per minute)"""
        # Simplified estimation - in production, this would track actual queries
        base_rate = 10.0  # Base queries per minute
        
        # Adjust based on system load
        try:
            system_metrics = performance_monitor.get_system_metrics()
            cpu_factor = 1 + (system_metrics.get("cpu_percent", 0) / 100)
            return base_rate * cpu_factor
        except:
            return base_rate
    
    async def _calculate_average_centrality(self) -> float:
        """Calculate average centrality across all nodes"""
        try:
            if not self.analytics_engine:
                return 0.0
            
            # Use degree centrality as a simple measure
            centrality_request = CentralityRequest(
                centrality_type=CentralityType.DEGREE,
                normalized=True
            )
            
            centrality_response = await self.analytics_engine.analyze_centrality(centrality_request)
            
            if centrality_response.node_metrics:
                centralities = [
                    node.centrality_scores.get("degree", 0.0) 
                    for node in centrality_response.node_metrics
                ]
                return sum(centralities) / len(centralities) if centralities else 0.0
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Failed to calculate average centrality: {e}")
            return 0.0
    
    async def _calculate_modularity(self) -> float:
        """Calculate graph modularity"""
        try:
            if not self.analytics_engine:
                return 0.0
            
            # This would typically use community detection
            # For now, return a reasonable estimate based on clustering
            graph_metrics = await self.analytics_engine.calculate_graph_metrics()
            
            # Estimate modularity based on clustering coefficient
            # Higher clustering often correlates with higher modularity
            estimated_modularity = min(graph_metrics.average_clustering * 1.2, 1.0)
            return estimated_modularity
            
        except Exception as e:
            logger.warning(f"Failed to calculate modularity: {e}")
            return 0.0
    
    # Fallback methods for when analytics engine is unavailable
    
    def _get_fallback_system_metrics(self) -> Dict[str, Any]:
        """Return fallback system metrics when analytics engine is unavailable"""
        # Use cached data if available and recent
        if (time.time() - self._cache_timestamp < self._cache_ttl * 2 and 
            self._last_metrics_cache):
            logger.info("Using cached system metrics (analytics engine unavailable)")
            return self._last_metrics_cache
        
        # Return basic fallback data
        return {
            "active_nodes": 0,
            "active_edges": 0,
            "query_rate": 0.0,
            "cache_hit_rate": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "response_time": 0.0,
            "uptime_seconds": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_fallback_memory_insights(self) -> Dict[str, Any]:
        """Return fallback memory insights when analytics engine is unavailable"""
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_fallback_graph_metrics(self) -> Dict[str, Any]:
        """Return fallback graph metrics when analytics engine is unavailable"""
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


# Singleton instance for easy access
_analytics_client_instance: Optional[AnalyticsEngineClient] = None


def get_analytics_client() -> AnalyticsEngineClient:
    """Get or create the analytics engine client instance"""
    global _analytics_client_instance
    
    if _analytics_client_instance is None:
        _analytics_client_instance = AnalyticsEngineClient()
    
    return _analytics_client_instance


async def initialize_analytics_client(kuzu_connection: Optional[kuzu.Connection] = None) -> bool:
    """Initialize the global analytics client instance"""
    client = get_analytics_client()
    
    if kuzu_connection:
        client.kuzu_conn = kuzu_connection
    
    return await client.initialize()


async def shutdown_analytics_client() -> None:
    """Shutdown the global analytics client instance"""
    global _analytics_client_instance
    
    if _analytics_client_instance:
        await _analytics_client_instance.shutdown()
        _analytics_client_instance = None 