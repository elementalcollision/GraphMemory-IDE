"""
Background Data Collection System

This module provides continuous background data collection for the analytics dashboard.
It implements data buffering, health monitoring, and aggregation for real-time streaming.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

# Import DataAdapter for data collection
try:
    from .data_adapter import get_data_adapter, DataAdapter
    from .models.analytics_models import SystemMetricsData, MemoryInsightsData, GraphMetricsData
except ImportError:
    from data_adapter import get_data_adapter, DataAdapter
    from models.analytics_models import SystemMetricsData, MemoryInsightsData, GraphMetricsData

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class CollectionStatus(Enum):
    """Data collection status"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class DataPoint:
    """Single data point with timestamp"""
    timestamp: datetime
    data: Union[SystemMetricsData, MemoryInsightsData, GraphMetricsData]
    collection_time: float  # Time taken to collect this data point
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "data": self.data.to_dict(),
            "collection_time": self.collection_time
        }


@dataclass
class AggregatedData:
    """Aggregated data over a time window"""
    start_time: datetime
    end_time: datetime
    count: int
    avg_collection_time: float
    min_collection_time: float
    max_collection_time: float
    success_rate: float
    data_summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "count": self.count,
            "avg_collection_time": self.avg_collection_time,
            "min_collection_time": self.min_collection_time,
            "max_collection_time": self.max_collection_time,
            "success_rate": self.success_rate,
            "data_summary": self.data_summary
        }


class DataBuffer:
    """
    Rolling buffer for storing time-series data with automatic aggregation
    """
    
    def __init__(self, max_size: int = 3600, name: str = "buffer"):
        self.max_size = max_size
        self.name = name
        self.data: deque[DataPoint] = deque(maxlen=max_size)
        self.failed_collections = 0
        self.total_collections = 0
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    def add_data_point(self, data: Union[SystemMetricsData, MemoryInsightsData, GraphMetricsData], 
                      collection_time: float):
        """Add a new data point to the buffer"""
        data_point = DataPoint(
            timestamp=datetime.now(),
            data=data,
            collection_time=collection_time
        )
        
        self.data.append(data_point)
        self.total_collections += 1
        
        # Periodic cleanup
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_data()
    
    def record_failed_collection(self):
        """Record a failed data collection attempt"""
        self.failed_collections += 1
        self.total_collections += 1
    
    def get_recent_data(self, count: int = 10) -> List[DataPoint]:
        """Get the most recent data points"""
        if count >= len(self.data):
            return list(self.data)
        return list(self.data)[-count:]
    
    def get_data_since(self, since: datetime) -> List[DataPoint]:
        """Get all data points since a specific time"""
        return [dp for dp in self.data if dp.timestamp >= since]
    
    def get_aggregated_data(self, window_minutes: int = 5) -> Optional[AggregatedData]:
        """Get aggregated data over a time window"""
        if not self.data:
            return None
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=window_minutes)
        
        window_data = self.get_data_since(start_time)
        if not window_data:
            return None
        
        collection_times = [dp.collection_time for dp in window_data]
        
        # Calculate success rate for this window
        window_total = len(window_data) + self._count_failures_in_window(start_time, end_time)
        success_rate = len(window_data) / window_total if window_total > 0 else 0.0
        
        # Create data summary based on data type
        data_summary = self._create_data_summary(window_data)
        
        return AggregatedData(
            start_time=start_time,
            end_time=end_time,
            count=len(window_data),
            avg_collection_time=statistics.mean(collection_times),
            min_collection_time=min(collection_times),
            max_collection_time=max(collection_times),
            success_rate=success_rate,
            data_summary=data_summary
        )
    
    def get_success_rate(self) -> float:
        """Get overall success rate"""
        if self.total_collections == 0:
            return 1.0
        successful = self.total_collections - self.failed_collections
        return successful / self.total_collections
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        return {
            "name": self.name,
            "size": len(self.data),
            "max_size": self.max_size,
            "total_collections": self.total_collections,
            "failed_collections": self.failed_collections,
            "success_rate": self.get_success_rate(),
            "oldest_data": self.data[0].timestamp.isoformat() if self.data else None,
            "newest_data": self.data[-1].timestamp.isoformat() if self.data else None
        }
    
    def _cleanup_old_data(self):
        """Clean up old data beyond retention period"""
        # The deque automatically handles max_size, but we can do additional cleanup here
        self.last_cleanup = time.time()
        logger.debug(f"Buffer {self.name} cleanup completed. Size: {len(self.data)}")
    
    def _count_failures_in_window(self, start_time: datetime, end_time: datetime) -> int:
        """Estimate failures in a time window (simplified implementation)"""
        # This is a simplified implementation - in production you might want to track failures with timestamps
        return 0
    
    def _create_data_summary(self, window_data: List[DataPoint]) -> Dict[str, Any]:
        """Create summary statistics for the data in the window"""
        if not window_data:
            return {}
        
        # Get the first data point to determine type
        first_data = window_data[0].data
        
        if isinstance(first_data, SystemMetricsData):
            return self._summarize_system_data(window_data)
        elif isinstance(first_data, MemoryInsightsData):
            return self._summarize_memory_data(window_data)
        elif isinstance(first_data, GraphMetricsData):
            return self._summarize_graph_data(window_data)
        else:
            return {"type": "unknown"}
    
    def _summarize_system_data(self, window_data: List[DataPoint]) -> Dict[str, Any]:
        """Summarize system metrics data"""
        metrics: Dict[str, List[Union[int, float]]] = {
            "active_nodes": [],
            "active_edges": [],
            "query_rate": [],
            "cache_hit_rate": [],
            "memory_usage": [],
            "cpu_usage": [],
            "response_time": []
        }
        
        for dp in window_data:
            data = dp.data
            if isinstance(data, SystemMetricsData):
                metrics["active_nodes"].append(data.active_nodes)
                metrics["active_edges"].append(data.active_edges)
                metrics["query_rate"].append(data.query_rate)
                metrics["cache_hit_rate"].append(data.cache_hit_rate)
                metrics["memory_usage"].append(data.memory_usage)
                metrics["cpu_usage"].append(data.cpu_usage)
                metrics["response_time"].append(data.response_time)
        
        # Only calculate stats if we have data
        if not metrics["active_nodes"]:
            return {"type": "system_metrics", "error": "no_data"}
        
        return {
            "type": "system_metrics",
            "avg_active_nodes": statistics.mean(metrics["active_nodes"]),
            "avg_active_edges": statistics.mean(metrics["active_edges"]),
            "avg_query_rate": statistics.mean(metrics["query_rate"]),
            "avg_cache_hit_rate": statistics.mean(metrics["cache_hit_rate"]),
            "avg_memory_usage": statistics.mean(metrics["memory_usage"]),
            "avg_cpu_usage": statistics.mean(metrics["cpu_usage"]),
            "avg_response_time": statistics.mean(metrics["response_time"]),
            "max_memory_usage": max(metrics["memory_usage"]),
            "max_cpu_usage": max(metrics["cpu_usage"]),
            "max_response_time": max(metrics["response_time"])
        }
    
    def _summarize_memory_data(self, window_data: List[DataPoint]) -> Dict[str, Any]:
        """Summarize memory insights data"""
        metrics: Dict[str, List[Union[int, float]]] = {
            "total_memories": [],
            "memory_efficiency": [],
            "memory_growth_rate": [],
            "retrieval_speed": []
        }
        
        for dp in window_data:
            data = dp.data
            if isinstance(data, MemoryInsightsData):
                metrics["total_memories"].append(data.total_memories)
                metrics["memory_efficiency"].append(data.memory_efficiency)
                metrics["memory_growth_rate"].append(data.memory_growth_rate)
                metrics["retrieval_speed"].append(data.retrieval_speed)
        
        # Only calculate stats if we have data
        if not metrics["total_memories"]:
            return {"type": "memory_insights", "error": "no_data"}
        
        return {
            "type": "memory_insights",
            "avg_total_memories": statistics.mean(metrics["total_memories"]),
            "avg_memory_efficiency": statistics.mean(metrics["memory_efficiency"]),
            "avg_memory_growth_rate": statistics.mean(metrics["memory_growth_rate"]),
            "avg_retrieval_speed": statistics.mean(metrics["retrieval_speed"]),
            "max_total_memories": max(metrics["total_memories"]),
            "min_memory_efficiency": min(metrics["memory_efficiency"])
        }
    
    def _summarize_graph_data(self, window_data: List[DataPoint]) -> Dict[str, Any]:
        """Summarize graph metrics data"""
        metrics: Dict[str, List[Union[int, float]]] = {
            "node_count": [],
            "edge_count": [],
            "density": [],
            "clustering_coefficient": [],
            "avg_centrality": []
        }
        
        for dp in window_data:
            data = dp.data
            if isinstance(data, GraphMetricsData):
                metrics["node_count"].append(data.node_count)
                metrics["edge_count"].append(data.edge_count)
                metrics["density"].append(data.density)
                metrics["clustering_coefficient"].append(data.clustering_coefficient)
                metrics["avg_centrality"].append(data.avg_centrality)
        
        # Only calculate stats if we have data
        if not metrics["node_count"]:
            return {"type": "graph_metrics", "error": "no_data"}
        
        return {
            "type": "graph_metrics",
            "avg_node_count": statistics.mean(metrics["node_count"]),
            "avg_edge_count": statistics.mean(metrics["edge_count"]),
            "avg_density": statistics.mean(metrics["density"]),
            "avg_clustering_coefficient": statistics.mean(metrics["clustering_coefficient"]),
            "avg_centrality": statistics.mean(metrics["avg_centrality"]),
            "max_node_count": max(metrics["node_count"]),
            "max_edge_count": max(metrics["edge_count"])
        }


class HealthMonitor:
    """
    System health monitoring with status tracking and alerting
    """
    
    def __init__(self):
        self.component_health: Dict[str, HealthStatus] = {}
        self.health_history: deque = deque(maxlen=100)  # Keep last 100 health checks
        self.last_health_check = time.time()
        self.health_check_interval = 30  # 30 seconds
        self.alerts: List[Dict[str, Any]] = []
        self.max_alerts = 50
    
    def update_component_health(self, component: str, status: HealthStatus, 
                              details: Optional[Dict[str, Any]] = None):
        """Update health status for a component"""
        old_status = self.component_health.get(component)
        self.component_health[component] = status
        
        # Record health change
        health_record = {
            "timestamp": datetime.now(),
            "component": component,
            "status": status.value,
            "old_status": old_status.value if old_status else None,
            "details": details or {}
        }
        
        self.health_history.append(health_record)
        
        # Generate alert if status degraded
        if old_status and status.value != old_status.value:
            self._generate_alert(component, old_status, status, details)
        
        logger.info(f"Health update: {component} -> {status.value}")
    
    def get_overall_health(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.component_health:
            return HealthStatus.HEALTHY
        
        statuses = list(self.component_health.values())
        
        # If any component is critical, system is critical
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        
        # If any component is unhealthy, system is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        
        # If any component is degraded, system is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        overall_health = self.get_overall_health()
        
        return {
            "overall_status": overall_health.value,
            "components": {comp: status.value for comp, status in self.component_health.items()},
            "last_check": datetime.now().isoformat(),
            "total_alerts": len(self.alerts),
            "recent_alerts": self.alerts[-5:] if self.alerts else [],
            "health_trend": self._get_health_trend()
        }
    
    def get_component_health(self, component: str) -> Optional[HealthStatus]:
        """Get health status for a specific component"""
        return self.component_health.get(component)
    
    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()
        logger.info("Health alerts cleared")
    
    def _generate_alert(self, component: str, old_status: HealthStatus, 
                       new_status: HealthStatus, details: Optional[Dict[str, Any]]):
        """Generate an alert for health status change"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "severity": self._get_alert_severity(new_status),
            "details": details or {}
        }
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        logger.warning(f"Health alert: {component} changed from {old_status.value} to {new_status.value}")
    
    def _get_alert_severity(self, status: HealthStatus) -> str:
        """Get alert severity based on health status"""
        severity_map = {
            HealthStatus.HEALTHY: "info",
            HealthStatus.DEGRADED: "warning",
            HealthStatus.UNHEALTHY: "error",
            HealthStatus.CRITICAL: "critical"
        }
        return severity_map.get(status, "info")
    
    def _get_health_trend(self) -> str:
        """Analyze health trend from recent history"""
        if len(self.health_history) < 2:
            return "stable"
        
        recent_records = list(self.health_history)[-10:]  # Last 10 records
        
        # Simple trend analysis
        improving = 0
        degrading = 0
        
        for i in range(1, len(recent_records)):
            current = recent_records[i]
            previous = recent_records[i-1]
            
            if current["status"] == "healthy" and previous["status"] != "healthy":
                improving += 1
            elif current["status"] != "healthy" and previous["status"] == "healthy":
                degrading += 1
        
        if improving > degrading:
            return "improving"
        elif degrading > improving:
            return "degrading"
        else:
            return "stable"


class BackgroundDataCollector:
    """
    Main background data collection orchestrator
    
    Manages continuous data collection from the analytics engine with
    buffering, health monitoring, and performance tracking.
    """
    
    def __init__(self, data_adapter: Optional[DataAdapter] = None):
        self.data_adapter = data_adapter or get_data_adapter()
        self.status = CollectionStatus.STOPPED
        
        # Data buffers for different data types
        self.buffers = {
            "analytics": DataBuffer(max_size=3600, name="analytics"),    # 1 hour at 1s intervals
            "memory": DataBuffer(max_size=720, name="memory"),           # 1 hour at 5s intervals
            "graph": DataBuffer(max_size=1800, name="graph")             # 1 hour at 2s intervals
        }
        
        # Health monitoring
        self.health_monitor = HealthMonitor()
        
        # Collection tasks
        self.collection_tasks: Dict[str, asyncio.Task] = {}
        
        # Collection intervals (seconds)
        self.collection_intervals = {
            "analytics": 1,    # Every 1 second
            "memory": 5,       # Every 5 seconds
            "graph": 2,        # Every 2 seconds
            "health": 30       # Every 30 seconds
        }
        
        # Performance tracking
        self.collection_stats = {
            "analytics": {"total": 0, "failed": 0, "avg_time": 0.0},
            "memory": {"total": 0, "failed": 0, "avg_time": 0.0},
            "graph": {"total": 0, "failed": 0, "avg_time": 0.0}
        }
        
        self.start_time: Optional[datetime] = None
        self.last_health_check = time.time()
    
    async def start_collection(self):
        """Start background data collection"""
        if self.status == CollectionStatus.RUNNING:
            logger.warning("Background collection already running")
            return
        
        logger.info("Starting background data collection...")
        self.status = CollectionStatus.STARTING
        self.start_time = datetime.now()
        
        try:
            # Start collection tasks for each data type
            self.collection_tasks["analytics"] = asyncio.create_task(
                self._collect_analytics_data()
            )
            self.collection_tasks["memory"] = asyncio.create_task(
                self._collect_memory_data()
            )
            self.collection_tasks["graph"] = asyncio.create_task(
                self._collect_graph_data()
            )
            self.collection_tasks["health"] = asyncio.create_task(
                self._monitor_health()
            )
            
            self.status = CollectionStatus.RUNNING
            self.health_monitor.update_component_health("background_collector", HealthStatus.HEALTHY)
            logger.info("Background data collection started successfully")
            
        except Exception as e:
            self.status = CollectionStatus.ERROR
            self.health_monitor.update_component_health("background_collector", HealthStatus.CRITICAL, 
                                                      {"error": str(e)})
            logger.error(f"Failed to start background collection: {e}")
            raise
    
    async def stop_collection(self):
        """Stop background data collection"""
        if self.status == CollectionStatus.STOPPED:
            logger.warning("Background collection already stopped")
            return
        
        logger.info("Stopping background data collection...")
        self.status = CollectionStatus.STOPPING
        
        # Cancel all collection tasks
        for task_name, task in self.collection_tasks.items():
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"Collection task {task_name} cancelled")
        
        self.collection_tasks.clear()
        self.status = CollectionStatus.STOPPED
        self.health_monitor.update_component_health("background_collector", HealthStatus.DEGRADED)
        logger.info("Background data collection stopped")
    
    async def _collect_analytics_data(self):
        """Continuously collect analytics data"""
        logger.info("Starting analytics data collection")
        
        while self.status == CollectionStatus.RUNNING:
            try:
                start_time = time.time()
                
                # Get analytics data through DataAdapter
                analytics_data = await self.data_adapter._get_validated_system_metrics()
                
                collection_time = time.time() - start_time
                
                # Add to buffer
                self.buffers["analytics"].add_data_point(analytics_data, collection_time)
                
                # Update stats
                self._update_collection_stats("analytics", collection_time, success=True)
                
                # Update health status
                if collection_time > 2.0:  # Slow collection
                    self.health_monitor.update_component_health("analytics_collection", 
                                                              HealthStatus.DEGRADED,
                                                              {"slow_collection": collection_time})
                else:
                    self.health_monitor.update_component_health("analytics_collection", 
                                                              HealthStatus.HEALTHY)
                
                await asyncio.sleep(self.collection_intervals["analytics"])
                
            except asyncio.CancelledError:
                logger.info("Analytics collection cancelled")
                break
            except Exception as e:
                logger.error(f"Error collecting analytics data: {e}")
                self.buffers["analytics"].record_failed_collection()
                self._update_collection_stats("analytics", 0, success=False)
                self.health_monitor.update_component_health("analytics_collection", 
                                                          HealthStatus.UNHEALTHY,
                                                          {"error": str(e)})
                
                # Exponential backoff on error
                await asyncio.sleep(min(self.collection_intervals["analytics"] * 2, 10))
    
    async def _collect_memory_data(self):
        """Continuously collect memory data"""
        logger.info("Starting memory data collection")
        
        while self.status == CollectionStatus.RUNNING:
            try:
                start_time = time.time()
                
                # Get memory data through DataAdapter
                memory_data = await self.data_adapter._get_validated_memory_insights()
                
                collection_time = time.time() - start_time
                
                # Add to buffer
                self.buffers["memory"].add_data_point(memory_data, collection_time)
                
                # Update stats
                self._update_collection_stats("memory", collection_time, success=True)
                
                # Update health status
                if collection_time > 3.0:  # Slow collection
                    self.health_monitor.update_component_health("memory_collection", 
                                                              HealthStatus.DEGRADED,
                                                              {"slow_collection": collection_time})
                else:
                    self.health_monitor.update_component_health("memory_collection", 
                                                              HealthStatus.HEALTHY)
                
                await asyncio.sleep(self.collection_intervals["memory"])
                
            except asyncio.CancelledError:
                logger.info("Memory collection cancelled")
                break
            except Exception as e:
                logger.error(f"Error collecting memory data: {e}")
                self.buffers["memory"].record_failed_collection()
                self._update_collection_stats("memory", 0, success=False)
                self.health_monitor.update_component_health("memory_collection", 
                                                          HealthStatus.UNHEALTHY,
                                                          {"error": str(e)})
                
                # Exponential backoff on error
                await asyncio.sleep(min(self.collection_intervals["memory"] * 2, 15))
    
    async def _collect_graph_data(self):
        """Continuously collect graph data"""
        logger.info("Starting graph data collection")
        
        while self.status == CollectionStatus.RUNNING:
            try:
                start_time = time.time()
                
                # Get graph data through DataAdapter
                graph_data = await self.data_adapter._get_validated_graph_metrics()
                
                collection_time = time.time() - start_time
                
                # Add to buffer
                self.buffers["graph"].add_data_point(graph_data, collection_time)
                
                # Update stats
                self._update_collection_stats("graph", collection_time, success=True)
                
                # Update health status
                if collection_time > 3.0:  # Slow collection
                    self.health_monitor.update_component_health("graph_collection", 
                                                              HealthStatus.DEGRADED,
                                                              {"slow_collection": collection_time})
                else:
                    self.health_monitor.update_component_health("graph_collection", 
                                                              HealthStatus.HEALTHY)
                
                await asyncio.sleep(self.collection_intervals["graph"])
                
            except asyncio.CancelledError:
                logger.info("Graph collection cancelled")
                break
            except Exception as e:
                logger.error(f"Error collecting graph data: {e}")
                self.buffers["graph"].record_failed_collection()
                self._update_collection_stats("graph", 0, success=False)
                self.health_monitor.update_component_health("graph_collection", 
                                                          HealthStatus.UNHEALTHY,
                                                          {"error": str(e)})
                
                # Exponential backoff on error
                await asyncio.sleep(min(self.collection_intervals["graph"] * 2, 15))
    
    async def _monitor_health(self):
        """Monitor overall system health"""
        logger.info("Starting health monitoring")
        
        while self.status == CollectionStatus.RUNNING:
            try:
                # Check DataAdapter performance
                adapter_stats = self.data_adapter.get_performance_stats()
                
                # Update health based on success rates
                if adapter_stats["success_rate"] < 50:
                    self.health_monitor.update_component_health("data_adapter", 
                                                              HealthStatus.CRITICAL,
                                                              {"success_rate": adapter_stats["success_rate"]})
                elif adapter_stats["success_rate"] < 80:
                    self.health_monitor.update_component_health("data_adapter", 
                                                              HealthStatus.DEGRADED,
                                                              {"success_rate": adapter_stats["success_rate"]})
                else:
                    self.health_monitor.update_component_health("data_adapter", 
                                                              HealthStatus.HEALTHY)
                
                # Check buffer health
                for buffer_name, buffer in self.buffers.items():
                    success_rate = buffer.get_success_rate()
                    if success_rate < 0.5:
                        self.health_monitor.update_component_health(f"{buffer_name}_buffer", 
                                                                  HealthStatus.UNHEALTHY,
                                                                  {"success_rate": success_rate})
                    elif success_rate < 0.8:
                        self.health_monitor.update_component_health(f"{buffer_name}_buffer", 
                                                                  HealthStatus.DEGRADED,
                                                                  {"success_rate": success_rate})
                    else:
                        self.health_monitor.update_component_health(f"{buffer_name}_buffer", 
                                                                  HealthStatus.HEALTHY)
                
                await asyncio.sleep(self.collection_intervals["health"])
                
            except asyncio.CancelledError:
                logger.info("Health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(self.collection_intervals["health"])
    
    def _update_collection_stats(self, data_type: str, collection_time: float, success: bool):
        """Update collection statistics"""
        stats = self.collection_stats[data_type]
        stats["total"] += 1
        
        if success:
            # Update average collection time
            if stats["avg_time"] == 0:
                stats["avg_time"] = collection_time
            else:
                stats["avg_time"] = (stats["avg_time"] + collection_time) / 2
        else:
            stats["failed"] += 1
    
    def get_recent_data(self, data_type: str, count: int = 10) -> List[DataPoint]:
        """Get recent data from a specific buffer"""
        if data_type not in self.buffers:
            return []
        return self.buffers[data_type].get_recent_data(count)
    
    def get_aggregated_data(self, data_type: str, window_minutes: int = 5) -> Optional[AggregatedData]:
        """Get aggregated data for a specific data type"""
        if data_type not in self.buffers:
            return None
        return self.buffers[data_type].get_aggregated_data(window_minutes)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get comprehensive collection statistics"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            "status": self.status.value,
            "uptime_seconds": uptime,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "collection_intervals": self.collection_intervals,
            "collection_stats": self.collection_stats,
            "buffer_stats": {name: buffer.get_buffer_stats() for name, buffer in self.buffers.items()},
            "health_summary": self.health_monitor.get_health_summary(),
            "active_tasks": len([task for task in self.collection_tasks.values() if task and not task.done()])
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return self.health_monitor.get_health_summary()


# Global background collector instance
_background_collector: Optional[BackgroundDataCollector] = None


def get_background_collector() -> BackgroundDataCollector:
    """Get the global background collector instance"""
    global _background_collector
    if _background_collector is None:
        _background_collector = BackgroundDataCollector()
    return _background_collector


def initialize_background_collector(data_adapter: Optional[DataAdapter] = None) -> BackgroundDataCollector:
    """Initialize the global background collector instance"""
    global _background_collector
    _background_collector = BackgroundDataCollector(data_adapter)
    return _background_collector


async def start_background_collection():
    """Start the global background collection"""
    collector = get_background_collector()
    await collector.start_collection()


async def stop_background_collection():
    """Stop the global background collection"""
    global _background_collector
    if _background_collector is not None:
        await _background_collector.stop_collection()
        _background_collector = None 