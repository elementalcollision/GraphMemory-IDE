"""
Data Adapter Layer

This module provides the DataAdapter class that bridges the analytics client,
validation models, and SSE streaming infrastructure. It transforms raw analytics
data into validated Pydantic models and formats them for SSE streaming.
"""

import asyncio
import json
import time
import uuid
from typing import Optional, Dict, Any, Union, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from collections import defaultdict

# Import analytics client
try:
    from .analytics_client import AnalyticsEngineClient, get_analytics_client
except ImportError:
    from analytics_client import AnalyticsEngineClient, get_analytics_client

# Import validation models
try:
    from .models.analytics_models import (
        SystemMetricsData, MemoryInsightsData, GraphMetricsData,
        AnalyticsStatus, create_fallback_system_metrics, 
        create_fallback_memory_insights, create_fallback_graph_metrics
    )
    from .models.error_models import (
        AnalyticsError, ErrorSeverity, ErrorCategory, generate_error_id
    )
    from .models.sse_models import SSEEvent, SSEEventType, SSEFormatter
except ImportError:
    from models.analytics_models import (
        SystemMetricsData, MemoryInsightsData, GraphMetricsData,
        AnalyticsStatus, create_fallback_system_metrics, 
        create_fallback_memory_insights, create_fallback_graph_metrics
    )
    from models.error_models import (
        AnalyticsError, ErrorSeverity, ErrorCategory, generate_error_id
    )
    from models.sse_models import SSEEvent, SSEEventType, SSEFormatter


class DataTransformationError(Exception):
    """Custom exception for data transformation errors"""
    pass


class CacheEntry:
    """Cache entry with TTL support"""
    
    def __init__(self, data: Any, ttl_seconds: int = 300) -> None:
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.created_at > self.ttl_seconds
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.created_at


class PerformanceMonitor:
    """Monitor performance of data transformations"""
    
    def __init__(self) -> None:
        """Initialize performance monitor"""
        self.transform_times: Dict[str, List[float]] = defaultdict(list)
        self.total_transformations: int = 0
        self.failed_transformations: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
    
    def record_transform_time(self, data_type: str, duration: float) -> None:
        """Record transformation time for a data type"""
        self.transform_times[data_type].append(duration)
        if len(self.transform_times[data_type]) > 100:
            self.transform_times[data_type] = self.transform_times[data_type][-100:]
        
        self.total_transformations += 1
    
    def record_failure(self) -> None:
        """Record a failed transformation"""
        self.failed_transformations += 1
    
    def record_cache_hit(self) -> None:
        """Record a cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self) -> None:
        """Record a cache miss"""
        self.cache_misses += 1
    
    def get_average_time(self, data_type: str) -> float:
        """Get average transformation time for a data type"""
        if data_type not in self.transform_times:
            return 0.0
        return sum(self.transform_times[data_type]) / len(self.transform_times[data_type]) if self.transform_times[data_type] else 0.0
    
    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate as percentage"""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0
    
    def get_success_rate(self) -> float:
        """Get transformation success rate as percentage"""
        if self.total_transformations == 0:
            return 100.0
        success = self.total_transformations - self.failed_transformations
        return (success / self.total_transformations * 100)


class DataAdapter:
    """
    Data Adapter Layer for transforming analytics data to SSE format
    
    This class bridges the analytics client, validation models, and SSE streaming
    infrastructure. It provides validated, cached, and SSE-formatted data for
    real-time dashboard streaming.
    """
    
    def __init__(self, analytics_client: Optional[AnalyticsEngineClient] = None) -> None:
        self.analytics_client = analytics_client or get_analytics_client()
        self.cache: Dict[str, CacheEntry] = {}
        self.performance_monitor = PerformanceMonitor()
        self.last_successful_data: Dict[str, Any] = {}
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_time: Optional[float] = None
        self.cache_ttl = 60  # Cache TTL in seconds
        
    async def get_analytics_sse_event(self) -> str:
        """Get system metrics as SSE formatted event"""
        try:
            start_time = time.time()
            
            # Check cache first
            cache_key = "system_metrics"
            if self._is_cache_valid(cache_key):
                self.performance_monitor.record_cache_hit()
                cached_data = self.cache[cache_key].data
                return self._create_sse_event(cached_data, SSEEventType.ANALYTICS)
            
            self.performance_monitor.record_cache_miss()
            
            # Get validated system metrics
            system_metrics = await self._get_validated_system_metrics()
            
            # Cache the result
            self.cache[cache_key] = CacheEntry(system_metrics, self.cache_ttl)
            self.last_successful_data[cache_key] = system_metrics
            
            # Record performance
            duration = time.time() - start_time
            self.performance_monitor.record_transform_time("system", duration)
            
            return self._create_sse_event(system_metrics, SSEEventType.ANALYTICS)
            
        except Exception as e:
            self.performance_monitor.record_failure()
            return await self._handle_error("system_metrics", e, SSEEventType.ANALYTICS)
    
    async def get_memory_sse_event(self) -> str:
        """Get memory insights as SSE formatted event"""
        try:
            start_time = time.time()
            
            # Check cache first
            cache_key = "memory_insights"
            if self._is_cache_valid(cache_key):
                self.performance_monitor.record_cache_hit()
                cached_data = self.cache[cache_key].data
                return self._create_sse_event(cached_data, SSEEventType.MEMORY)
            
            self.performance_monitor.record_cache_miss()
            
            # Get validated memory insights
            memory_insights = await self._get_validated_memory_insights()
            
            # Cache the result
            self.cache[cache_key] = CacheEntry(memory_insights, self.cache_ttl)
            self.last_successful_data[cache_key] = memory_insights
            
            # Record performance
            duration = time.time() - start_time
            self.performance_monitor.record_transform_time("memory", duration)
            
            return self._create_sse_event(memory_insights, SSEEventType.MEMORY)
            
        except Exception as e:
            self.performance_monitor.record_failure()
            return await self._handle_error("memory_insights", e, SSEEventType.MEMORY)
    
    async def get_graph_sse_event(self) -> str:
        """Get graph metrics as SSE formatted event"""
        try:
            start_time = time.time()
            
            # Check cache first
            cache_key = "graph_metrics"
            if self._is_cache_valid(cache_key):
                self.performance_monitor.record_cache_hit()
                cached_data = self.cache[cache_key].data
                return self._create_sse_event(cached_data, SSEEventType.GRAPH)
            
            self.performance_monitor.record_cache_miss()
            
            # Get validated graph metrics
            graph_metrics = await self._get_validated_graph_metrics()
            
            # Cache the result
            self.cache[cache_key] = CacheEntry(graph_metrics, self.cache_ttl)
            self.last_successful_data[cache_key] = graph_metrics
            
            # Record performance
            duration = time.time() - start_time
            self.performance_monitor.record_transform_time("graph", duration)
            
            return self._create_sse_event(graph_metrics, SSEEventType.GRAPH)
            
        except Exception as e:
            self.performance_monitor.record_failure()
            return await self._handle_error("graph_metrics", e, SSEEventType.GRAPH)
    
    async def _get_validated_system_metrics(self) -> SystemMetricsData:
        """Get and validate system metrics from analytics client"""
        if self._is_circuit_breaker_open():
            raise DataTransformationError("Circuit breaker is open")
        
        try:
            # Get raw data from analytics client
            raw_data = await self.analytics_client.get_system_metrics()
            
            # Transform to validated model
            system_metrics = self._transform_system_data(raw_data)
            
            # Reset circuit breaker on success
            self.circuit_breaker_failures = 0
            self.circuit_breaker_reset_time = None
            
            return system_metrics
            
        except Exception as e:
            self._record_circuit_breaker_failure()
            raise DataTransformationError(f"Failed to get system metrics: {e}")
    
    async def _get_validated_memory_insights(self) -> MemoryInsightsData:
        """Get and validate memory insights from analytics client"""
        if self._is_circuit_breaker_open():
            raise DataTransformationError("Circuit breaker is open")
        
        try:
            # Get raw data from analytics client
            raw_data = await self.analytics_client.get_memory_insights()
            
            # Transform to validated model
            memory_insights = self._transform_memory_data(raw_data)
            
            # Reset circuit breaker on success
            self.circuit_breaker_failures = 0
            self.circuit_breaker_reset_time = None
            
            return memory_insights
            
        except Exception as e:
            self._record_circuit_breaker_failure()
            raise DataTransformationError(f"Failed to get memory insights: {e}")
    
    async def _get_validated_graph_metrics(self) -> GraphMetricsData:
        """Get and validate graph metrics from analytics client"""
        if self._is_circuit_breaker_open():
            raise DataTransformationError("Circuit breaker is open")
        
        try:
            # Get raw data from analytics client
            raw_data = await self.analytics_client.get_graph_metrics()
            
            # Transform to validated model
            graph_metrics = self._transform_graph_data(raw_data)
            
            # Reset circuit breaker on success
            self.circuit_breaker_failures = 0
            self.circuit_breaker_reset_time = None
            
            return graph_metrics
            
        except Exception as e:
            self._record_circuit_breaker_failure()
            raise DataTransformationError(f"Failed to get graph metrics: {e}")
    
    def _transform_system_data(self, raw_data: Dict[str, Any]) -> SystemMetricsData:
        """Transform raw system data to SystemMetricsData model"""
        try:
            # Handle both direct data and nested data structures
            if isinstance(raw_data, dict) and 'data' in raw_data:
                data = raw_data['data']
            else:
                data = raw_data
            
            # Create SystemMetricsData with validation
            return SystemMetricsData(
                active_nodes=data.get('active_nodes', 0),
                active_edges=data.get('active_edges', 0),
                query_rate=data.get('query_rate', 0.0),
                cache_hit_rate=data.get('cache_hit_rate', 0.0),
                memory_usage=data.get('memory_usage', 0.0),
                cpu_usage=data.get('cpu_usage', 0.0),
                response_time=data.get('response_time', 0.0),
                uptime_seconds=data.get('uptime_seconds', 0.0),
                timestamp=data.get('timestamp', datetime.now().isoformat()),
                status=AnalyticsStatus(data.get('status', 'healthy'))
            )
            
        except Exception as e:
            raise DataTransformationError(f"Failed to transform system data: {e}")
    
    def _transform_memory_data(self, raw_data: Dict[str, Any]) -> MemoryInsightsData:
        """Transform raw memory data to MemoryInsightsData model"""
        try:
            # Handle both direct data and nested data structures
            if isinstance(raw_data, dict) and 'data' in raw_data:
                data = raw_data['data']
            else:
                data = raw_data
            
            # Create MemoryInsightsData with validation
            return MemoryInsightsData(
                total_memories=data.get('total_memories', 0),
                procedural_memories=data.get('procedural_memories', 0),
                semantic_memories=data.get('semantic_memories', 0),
                episodic_memories=data.get('episodic_memories', 0),
                memory_efficiency=data.get('memory_efficiency', 0.0),
                memory_growth_rate=data.get('memory_growth_rate', 0.0),
                avg_memory_size=data.get('avg_memory_size', 0.0),
                compression_ratio=data.get('compression_ratio', 1.0),
                retrieval_speed=data.get('retrieval_speed', 0.0),
                timestamp=data.get('timestamp', datetime.now().isoformat()),
                status=AnalyticsStatus(data.get('status', 'healthy'))
            )
            
        except Exception as e:
            raise DataTransformationError(f"Failed to transform memory data: {e}")
    
    def _transform_graph_data(self, raw_data: Dict[str, Any]) -> GraphMetricsData:
        """Transform raw graph data to GraphMetricsData model"""
        try:
            # Handle both direct data and nested data structures
            if isinstance(raw_data, dict) and 'data' in raw_data:
                data = raw_data['data']
            else:
                data = raw_data
            
            # Create GraphMetricsData with validation
            return GraphMetricsData(
                node_count=data.get('node_count', 0),
                edge_count=data.get('edge_count', 0),
                connected_components=data.get('connected_components', 0),
                largest_component_size=data.get('largest_component_size', 0),
                diameter=data.get('diameter', 0),
                density=data.get('density', 0.0),
                clustering_coefficient=data.get('clustering_coefficient', 0.0),
                avg_centrality=data.get('avg_centrality', 0.0),
                modularity=data.get('modularity', 0.0),
                timestamp=data.get('timestamp', datetime.now().isoformat()),
                status=AnalyticsStatus(data.get('status', 'healthy'))
            )
            
        except Exception as e:
            raise DataTransformationError(f"Failed to transform graph data: {e}")
    
    def _create_sse_event(self, data: Union[SystemMetricsData, MemoryInsightsData, GraphMetricsData], event_type: SSEEventType) -> str:
        """Create SSE formatted event from validated data"""
        try:
            # Create SSE event
            event = SSEEvent(
                event_type=event_type,
                data=data,
                timestamp=data.timestamp,
                event_id=str(uuid.uuid4())[:8]
            )
            
            return event.to_sse_format()
            
        except Exception as e:
            # Fallback to simple SSE format
            return SSEFormatter.format_error(f"Failed to create SSE event: {e}")
    
    async def _handle_error(self, data_type: str, error: Exception, event_type: SSEEventType) -> str:
        """Handle errors with fallback mechanisms"""
        try:
            # Try to use last successful data
            if data_type in self.last_successful_data:
                cached_data = self.last_successful_data[data_type]
                return self._create_sse_event(cached_data, event_type)
            
            # Create fallback data
            timestamp = datetime.now().isoformat()
            
            if data_type == "system_metrics":
                fallback_data = create_fallback_system_metrics(timestamp)
            elif data_type == "memory_insights":
                fallback_data = create_fallback_memory_insights(timestamp)
            elif data_type == "graph_metrics":
                fallback_data = create_fallback_graph_metrics(timestamp)
            else:
                raise ValueError(f"Unknown data type: {data_type}")
            
            return self._create_sse_event(fallback_data, event_type)
            
        except Exception as fallback_error:
            # Last resort: return error event
            error_data = {
                "error": str(error),
                "fallback_error": str(fallback_error),
                "timestamp": datetime.now().isoformat(),
                "data_type": data_type
            }
            return SSEFormatter.format_data_only(error_data, "error")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid and not expired"""
        if cache_key not in self.cache:
            return False
        
        entry = self.cache[cache_key]
        if entry.is_expired():
            del self.cache[cache_key]
            return False
        
        return True
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.circuit_breaker_failures < self.circuit_breaker_threshold:
            return False
        
        if self.circuit_breaker_reset_time is None:
            self.circuit_breaker_reset_time = time.time() + 60  # Reset after 60 seconds
            return True
        
        if time.time() > self.circuit_breaker_reset_time:
            # Reset circuit breaker
            self.circuit_breaker_failures = 0
            self.circuit_breaker_reset_time = None
            return False
        
        return True
    
    def _record_circuit_breaker_failure(self) -> None:
        """Record a circuit breaker failure"""
        self.circuit_breaker_failures += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "cache_hit_rate": self.performance_monitor.get_cache_hit_rate(),
            "success_rate": self.performance_monitor.get_success_rate(),
            "average_transform_times": {
                "system": self.performance_monitor.get_average_time("system"),
                "memory": self.performance_monitor.get_average_time("memory"),
                "graph": self.performance_monitor.get_average_time("graph")
            },
            "circuit_breaker": {
                "failures": self.circuit_breaker_failures,
                "is_open": self._is_circuit_breaker_open(),
                "reset_time": self.circuit_breaker_reset_time
            },
            "cache_entries": len(self.cache),
            "total_transformations": self.performance_monitor.total_transformations
        }
    
    def clear_cache(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
    
    def set_cache_ttl(self, ttl_seconds: int) -> None:
        """Set cache TTL in seconds"""
        self.cache_ttl = ttl_seconds


# Global data adapter instance
_data_adapter: Optional[DataAdapter] = None


def get_data_adapter() -> DataAdapter:
    """Get the global data adapter instance"""
    global _data_adapter
    if _data_adapter is None:
        _data_adapter = DataAdapter()
    return _data_adapter


def initialize_data_adapter(analytics_client: Optional[AnalyticsEngineClient] = None) -> DataAdapter:
    """Initialize the global data adapter instance"""
    global _data_adapter
    _data_adapter = DataAdapter(analytics_client)
    return _data_adapter


async def shutdown_data_adapter() -> None:
    """Shutdown the global data adapter instance"""
    global _data_adapter
    if _data_adapter is not None:
        _data_adapter.clear_cache()
        _data_adapter = None 