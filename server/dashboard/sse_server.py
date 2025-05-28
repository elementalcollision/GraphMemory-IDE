"""
Server-Sent Events (SSE) Manager for Real-time Dashboard

This module provides SSE streaming capabilities for the analytics dashboard,
enabling real-time updates for analytics data, memory insights, and graph metrics.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Any, AsyncGenerator, Optional
from dataclasses import dataclass

# Import DataAdapter for real data transformation
try:
    from .data_adapter import get_data_adapter, DataAdapter
    from .background_collector import get_background_collector, BackgroundDataCollector
except ImportError:
    from data_adapter import get_data_adapter, DataAdapter
    from background_collector import get_background_collector, BackgroundDataCollector

logger = logging.getLogger(__name__)


@dataclass
class SSEMessage:
    """Structure for SSE messages"""
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None


class DashboardSSEManager:
    """
    Manages Server-Sent Events for real-time dashboard updates
    
    Provides streaming endpoints for:
    - Analytics data (1-second updates)
    - Memory insights (5-second updates) 
    - Graph metrics (2-second updates)
    """
    
    def __init__(self, analytics_engine=None, data_adapter: Optional[DataAdapter] = None, 
                 background_collector: Optional[BackgroundDataCollector] = None):
        self.analytics_engine = analytics_engine
        self.data_adapter = data_adapter or get_data_adapter()
        self.background_collector = background_collector or get_background_collector()
        self.active_connections: Set[str] = set()
        self.data_streams: Dict[str, Any] = {}
        self.connection_stats: Dict[str, Dict] = {}
        self._running = False
        
        # Cache for latest data to avoid redundant queries
        self._analytics_cache = {}
        self._memory_cache = {}
        self._graph_cache = {}
        self._last_update: Dict[str, Optional[datetime]] = {
            "analytics": None,
            "memory": None,
            "graph": None
        }
    
    async def start(self):
        """Start the SSE manager"""
        self._running = True
        logger.info("Dashboard SSE Manager started")
    
    async def stop(self):
        """Stop the SSE manager"""
        self._running = False
        logger.info("Dashboard SSE Manager stopped")
    
    async def analytics_stream(self) -> AsyncGenerator[str, None]:
        """
        Stream analytics data to connected clients using DataAdapter
        Updates every 1 second with real-time analytics metrics
        """
        logger.info("Starting analytics stream with DataAdapter")
        
        while self._running:
            try:
                # Get SSE-formatted analytics data from DataAdapter
                sse_event = await self.data_adapter.get_analytics_sse_event()
                
                # Update cache and timestamp
                self._last_update["analytics"] = datetime.now()
                
                yield sse_event
                
                await asyncio.sleep(1)  # 1-second updates
                
            except Exception as e:
                logger.error(f"Error in analytics stream: {e}")
                # Create error SSE event
                error_event = f"event: error\ndata: {json.dumps({'error': 'Analytics stream error', 'timestamp': datetime.now().isoformat()})}\n\n"
                yield error_event
                await asyncio.sleep(5)  # Wait longer on error
    
    async def memory_stream(self) -> AsyncGenerator[str, None]:
        """
        Stream memory insights using DataAdapter
        Updates every 5 seconds with memory system data
        """
        logger.info("Starting memory stream with DataAdapter")
        
        while self._running:
            try:
                # Get SSE-formatted memory data from DataAdapter
                sse_event = await self.data_adapter.get_memory_sse_event()
                
                # Update cache and timestamp
                self._last_update["memory"] = datetime.now()
                
                yield sse_event
                
                await asyncio.sleep(5)  # 5-second updates
                
            except Exception as e:
                logger.error(f"Error in memory stream: {e}")
                # Create error SSE event
                error_event = f"event: error\ndata: {json.dumps({'error': 'Memory stream error', 'timestamp': datetime.now().isoformat()})}\n\n"
                yield error_event
                await asyncio.sleep(10)  # Wait longer on error
    
    async def graph_stream(self) -> AsyncGenerator[str, None]:
        """
        Stream graph metrics using DataAdapter
        Updates every 2 seconds with graph analytics
        """
        logger.info("Starting graph stream with DataAdapter")
        
        while self._running:
            try:
                # Get SSE-formatted graph data from DataAdapter
                sse_event = await self.data_adapter.get_graph_sse_event()
                
                # Update cache and timestamp
                self._last_update["graph"] = datetime.now()
                
                yield sse_event
                
                await asyncio.sleep(2)  # 2-second updates
                
            except Exception as e:
                logger.error(f"Error in graph stream: {e}")
                # Create error SSE event
                error_event = f"event: error\ndata: {json.dumps({'error': 'Graph stream error', 'timestamp': datetime.now().isoformat()})}\n\n"
                yield error_event
                await asyncio.sleep(5)  # Wait longer on error
    
    async def get_analytics_data(self) -> None:
        """DEPRECATED: Use DataAdapter instead"""
        # This method is kept for backward compatibility but should not be used
        # Use self.data_adapter.get_analytics_sse_event() instead
        pass
    
    async def get_memory_insights(self) -> None:
        """DEPRECATED: Use DataAdapter instead"""
        # This method is kept for backward compatibility but should not be used
        # Use self.data_adapter.get_memory_sse_event() instead
        pass
    
    async def get_graph_metrics(self) -> None:
        """DEPRECATED: Use DataAdapter instead"""
        # This method is kept for backward compatibility but should not be used
        # Use self.data_adapter.get_graph_sse_event() instead
        pass
    
    # Connection management methods
    def add_connection(self, connection_id: str):
        """Add a new SSE connection"""
        self.active_connections.add(connection_id)
        self.connection_stats[connection_id] = {
            "connected_at": datetime.now(),
            "messages_sent": 0
        }
        logger.info(f"SSE connection added: {connection_id}")
    
    def remove_connection(self, connection_id: str):
        """Remove an SSE connection"""
        self.active_connections.discard(connection_id)
        if connection_id in self.connection_stats:
            del self.connection_stats[connection_id]
        logger.info(f"SSE connection removed: {connection_id}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection and performance statistics"""
        adapter_stats = self.data_adapter.get_performance_stats()
        
        return {
            "active_connections": len(self.active_connections),
            "last_updates": {
                "analytics": self._last_update["analytics"].isoformat() if self._last_update["analytics"] else None,
                "memory": self._last_update["memory"].isoformat() if self._last_update["memory"] else None,
                "graph": self._last_update["graph"].isoformat() if self._last_update["graph"] else None
            },
            "data_adapter_performance": adapter_stats,
            "streams_running": self._running
        }
    
    def get_data_adapter_stats(self) -> Dict[str, Any]:
        """Get detailed DataAdapter performance statistics"""
        return self.data_adapter.get_performance_stats()
    
    # Background Collector Integration Methods
    
    def get_background_collector_stats(self) -> Dict[str, Any]:
        """Get background collector statistics"""
        return self.background_collector.get_collection_stats()
    
    def get_recent_collected_data(self, data_type: str, count: int = 10) -> list:
        """Get recent data from background collector buffers"""
        try:
            recent_data = self.background_collector.get_recent_data(data_type, count)
            return [dp.to_dict() for dp in recent_data]
        except Exception as e:
            logger.error(f"Error getting recent data for {data_type}: {e}")
            return []
    
    def get_aggregated_collected_data(self, data_type: str, window_minutes: int = 5) -> Optional[Dict[str, Any]]:
        """Get aggregated data from background collector"""
        try:
            aggregated = self.background_collector.get_aggregated_data(data_type, window_minutes)
            return aggregated.to_dict() if aggregated else None
        except Exception as e:
            logger.error(f"Error getting aggregated data for {data_type}: {e}")
            return None
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            return self.background_collector.get_health_status()
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {"error": str(e), "status": "unknown"}
    
    async def start_background_collection(self):
        """Start background data collection"""
        try:
            await self.background_collector.start_collection()
            logger.info("Background data collection started via SSE manager")
        except Exception as e:
            logger.error(f"Failed to start background collection: {e}")
            raise
    
    async def stop_background_collection(self):
        """Stop background data collection"""
        try:
            await self.background_collector.stop_collection()
            logger.info("Background data collection stopped via SSE manager")
        except Exception as e:
            logger.error(f"Failed to stop background collection: {e}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all components"""
        try:
            return {
                "sse_manager": self.get_connection_stats(),
                "data_adapter": self.get_data_adapter_stats(),
                "background_collector": self.get_background_collector_stats(),
                "system_health": self.get_system_health_status(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 