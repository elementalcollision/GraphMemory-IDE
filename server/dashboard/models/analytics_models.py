"""
Analytics Data Models

This module contains Pydantic models for analytics data structures that match
the output from the analytics engine client and provide validation for real-time streaming.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

from .validation_models import (
    BaseValidationModel,
    PositiveFloat,
    PercentageFloat,
    NonNegativeInt,
    NonNegativeFloat,
    MemorySize,
    ResponseTime,
    UptimeSeconds,
    QueryRate,
    CacheHitRate,
    NodeCount,
    EdgeCount,
    GraphDensity,
    ClusteringCoefficient,
    CentralityScore,
    Modularity,
    MemoryEfficiency,
    GrowthRate,
    CompressionRatio,
    TimestampStr,
    ValidationResult,
    PerformanceValidator
)


class AnalyticsStatus(str, Enum):
    """Status of the analytics engine"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class SystemMetricsData(BaseValidationModel):
    """System performance metrics from analytics engine"""
    
    # Core system metrics
    active_nodes: NodeCount = Field(description="Number of active nodes in the system")
    active_edges: EdgeCount = Field(description="Number of active edges in the system")
    query_rate: QueryRate = Field(description="Current query rate (queries per minute)")
    cache_hit_rate: CacheHitRate = Field(description="Cache hit rate as ratio (0.0-1.0)")
    
    # Performance metrics
    memory_usage: PercentageFloat = Field(description="Memory usage percentage (0.0-100.0)")
    cpu_usage: PercentageFloat = Field(description="CPU usage percentage (0.0-100.0)")
    response_time: ResponseTime = Field(description="Average response time in milliseconds")
    uptime_seconds: UptimeSeconds = Field(description="System uptime in seconds")
    
    # Metadata
    timestamp: TimestampStr = Field(description="Timestamp when metrics were collected")
    status: AnalyticsStatus = Field(default=AnalyticsStatus.HEALTHY, description="System status")
    
    @validator('cache_hit_rate', pre=True)
    def validate_cache_hit_rate(cls, v) -> None:
        """Convert percentage to ratio if needed"""
        if isinstance(v, (int, float)) and v > 1.0:
            return v / 100.0
        return v
    
    def validate_consistency(self) -> ValidationResult:
        """Validate that metrics are internally consistent"""
        return PerformanceValidator.validate_metrics_consistency(
            cpu_usage=self.cpu_usage,
            memory_usage=self.memory_usage,
            response_time=self.response_time
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SSE streaming"""
        return {
            "active_nodes": self.active_nodes,
            "active_edges": self.active_edges,
            "query_rate": self.query_rate,
            "cache_hit_rate": self.cache_hit_rate,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "response_time": self.response_time,
            "uptime_seconds": self.uptime_seconds,
            "timestamp": self.timestamp,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status)
        }


class MemoryInsightsData(BaseValidationModel):
    """Memory system insights and statistics"""
    
    # Memory counts
    total_memories: NonNegativeInt = Field(description="Total number of memories in system")
    procedural_memories: NonNegativeInt = Field(description="Number of procedural memories")
    semantic_memories: NonNegativeInt = Field(description="Number of semantic memories")
    episodic_memories: NonNegativeInt = Field(description="Number of episodic memories")
    
    # Memory performance metrics
    memory_efficiency: MemoryEfficiency = Field(description="Memory system efficiency ratio")
    memory_growth_rate: GrowthRate = Field(description="Memory growth rate")
    avg_memory_size: MemorySize = Field(description="Average memory size in bytes")
    compression_ratio: CompressionRatio = Field(description="Memory compression ratio")
    retrieval_speed: ResponseTime = Field(description="Average memory retrieval time in ms")
    
    # Metadata
    timestamp: TimestampStr = Field(description="Timestamp when insights were collected")
    status: AnalyticsStatus = Field(default=AnalyticsStatus.HEALTHY, description="Memory system status")
    
    @validator('total_memories')
    def validate_total_memories(cls, v, values) -> None:
        """Ensure total memories equals sum of memory types"""
        if 'procedural_memories' in values and 'semantic_memories' in values and 'episodic_memories' in values:
            expected_total = values['procedural_memories'] + values['semantic_memories'] + values['episodic_memories']
            if v != expected_total:
                # Allow some tolerance for concurrent updates
                if abs(v - expected_total) > 10:  # Allow up to 10 memory difference
                    raise ValueError(f"Total memories {v} doesn't match sum of types {expected_total}")
        return v
    
    def get_memory_distribution(self) -> Dict[str, float]:
        """Get memory type distribution as percentages"""
        if self.total_memories == 0:
            return {"procedural": 0.0, "semantic": 0.0, "episodic": 0.0}
        
        return {
            "procedural": (self.procedural_memories / self.total_memories) * 100.0,
            "semantic": (self.semantic_memories / self.total_memories) * 100.0,
            "episodic": (self.episodic_memories / self.total_memories) * 100.0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SSE streaming"""
        return {
            "total_memories": self.total_memories,
            "procedural_memories": self.procedural_memories,
            "semantic_memories": self.semantic_memories,
            "episodic_memories": self.episodic_memories,
            "memory_efficiency": self.memory_efficiency,
            "memory_growth_rate": self.memory_growth_rate,
            "avg_memory_size": self.avg_memory_size,
            "compression_ratio": self.compression_ratio,
            "retrieval_speed": self.retrieval_speed,
            "timestamp": self.timestamp,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "distribution": self.get_memory_distribution()
        }


class GraphMetricsData(BaseValidationModel):
    """Graph topology and structure metrics"""
    
    # Basic graph structure
    node_count: NodeCount = Field(description="Total number of nodes in graph")
    edge_count: EdgeCount = Field(description="Total number of edges in graph")
    connected_components: NonNegativeInt = Field(description="Number of connected components")
    largest_component_size: NonNegativeInt = Field(description="Size of largest connected component")
    
    # Graph topology metrics
    diameter: NonNegativeInt = Field(description="Graph diameter (longest shortest path)")
    density: GraphDensity = Field(description="Graph density (0.0-1.0)")
    clustering_coefficient: ClusteringCoefficient = Field(description="Average clustering coefficient")
    
    # Centrality and community metrics
    avg_centrality: CentralityScore = Field(description="Average centrality score")
    modularity: Modularity = Field(description="Modularity score (-1.0 to 1.0)")
    
    # Metadata
    timestamp: TimestampStr = Field(description="Timestamp when metrics were collected")
    status: AnalyticsStatus = Field(default=AnalyticsStatus.HEALTHY, description="Graph analysis status")
    
    @validator('largest_component_size')
    def validate_largest_component_size(cls, v, values) -> None:
        """Ensure largest component size doesn't exceed total nodes"""
        if 'node_count' in values and v > values['node_count']:
            raise ValueError(f"Largest component size {v} cannot exceed total nodes {values['node_count']}")
        return v
    
    @validator('connected_components')
    def validate_connected_components(cls, v, values) -> None:
        """Validate connected components count"""
        if 'node_count' in values:
            if values['node_count'] == 0 and v != 0:
                raise ValueError("Cannot have connected components without nodes")
            if v > values['node_count']:
                raise ValueError(f"Connected components {v} cannot exceed node count {values['node_count']}")
        return v
    
    def validate_consistency(self) -> ValidationResult:
        """Validate that graph metrics are mathematically consistent"""
        return PerformanceValidator.validate_graph_metrics_consistency(
            node_count=self.node_count,
            edge_count=self.edge_count,
            density=self.density,
            clustering=self.clustering_coefficient
        )
    
    def get_graph_summary(self) -> Dict[str, Any]:
        """Get summary statistics about the graph"""
        node_count_safe = max(self.node_count, 1)
        return {
            "total_elements": self.node_count + self.edge_count,
            "connectivity": float(self.edge_count) / node_count_safe,
            "fragmentation": float(self.connected_components) / node_count_safe,
            "largest_component_ratio": float(self.largest_component_size) / node_count_safe
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SSE streaming"""
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "connected_components": self.connected_components,
            "largest_component_size": self.largest_component_size,
            "diameter": self.diameter,
            "density": self.density,
            "clustering_coefficient": self.clustering_coefficient,
            "avg_centrality": self.avg_centrality,
            "modularity": self.modularity,
            "timestamp": self.timestamp,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "summary": self.get_graph_summary()
        }


class PerformanceMetrics(BaseValidationModel):
    """Combined performance metrics for overall system health"""
    
    # System health indicators
    overall_health_score: PercentageFloat = Field(description="Overall system health score (0-100)")
    response_time_p95: ResponseTime = Field(description="95th percentile response time")
    error_rate: PercentageFloat = Field(description="Error rate percentage")
    throughput: PositiveFloat = Field(description="System throughput (operations per second)")
    
    # Resource utilization
    memory_utilization: PercentageFloat = Field(description="Memory utilization percentage")
    cpu_utilization: PercentageFloat = Field(description="CPU utilization percentage")
    disk_utilization: PercentageFloat = Field(description="Disk utilization percentage")
    network_utilization: PercentageFloat = Field(description="Network utilization percentage")
    
    # Metadata
    timestamp: TimestampStr = Field(description="Timestamp when metrics were collected")
    collection_duration_ms: ResponseTime = Field(description="Time taken to collect metrics")
    
    def calculate_health_score(self) -> float:
        """Calculate overall health score based on metrics"""
        # Simple health scoring algorithm
        health_factors = [
            100 - self.error_rate,  # Lower error rate = better health
            100 - min(self.memory_utilization, 100),  # Lower memory usage = better health
            100 - min(self.cpu_utilization, 100),  # Lower CPU usage = better health
            min(100.0, max(0.0, 100 - (self.response_time_p95 / 10)))  # Lower response time = better health
        ]
        
        return sum(health_factors) / len(health_factors)
    
    def get_resource_pressure(self) -> Dict[str, str]:
        """Get resource pressure indicators"""
        def pressure_level(utilization: float) -> str:
            if utilization < 50:
                return "low"
            elif utilization < 80:
                return "medium"
            else:
                return "high"
        
        return {
            "memory": pressure_level(self.memory_utilization),
            "cpu": pressure_level(self.cpu_utilization),
            "disk": pressure_level(self.disk_utilization),
            "network": pressure_level(self.network_utilization)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SSE streaming"""
        return {
            "overall_health_score": self.overall_health_score,
            "response_time_p95": self.response_time_p95,
            "error_rate": self.error_rate,
            "throughput": self.throughput,
            "memory_utilization": self.memory_utilization,
            "cpu_utilization": self.cpu_utilization,
            "disk_utilization": self.disk_utilization,
            "network_utilization": self.network_utilization,
            "timestamp": self.timestamp,
            "collection_duration_ms": self.collection_duration_ms,
            "calculated_health": self.calculate_health_score(),
            "resource_pressure": self.get_resource_pressure()
        }


# Utility functions for creating fallback data
def create_fallback_system_metrics(timestamp: str) -> SystemMetricsData:
    """Create fallback system metrics when analytics engine is unavailable"""
    return SystemMetricsData(
        active_nodes=0,
        active_edges=0,
        query_rate=0.0,
        cache_hit_rate=0.0,
        memory_usage=0.0,
        cpu_usage=0.0,
        response_time=0.0,
        uptime_seconds=0.0,
        timestamp=timestamp,
        status=AnalyticsStatus.UNAVAILABLE
    )


def create_fallback_memory_insights(timestamp: str) -> MemoryInsightsData:
    """Create fallback memory insights when analytics engine is unavailable"""
    return MemoryInsightsData(
        total_memories=0,
        procedural_memories=0,
        semantic_memories=0,
        episodic_memories=0,
        memory_efficiency=0.0,
        memory_growth_rate=0.0,
        avg_memory_size=0.0,
        compression_ratio=1.0,
        retrieval_speed=0.0,
        timestamp=timestamp,
        status=AnalyticsStatus.UNAVAILABLE
    )


def create_fallback_graph_metrics(timestamp: str) -> GraphMetricsData:
    """Create fallback graph metrics when analytics engine is unavailable"""
    return GraphMetricsData(
        node_count=0,
        edge_count=0,
        connected_components=0,
        largest_component_size=0,
        diameter=0,
        density=0.0,
        clustering_coefficient=0.0,
        avg_centrality=0.0,
        modularity=0.0,
        timestamp=timestamp,
        status=AnalyticsStatus.UNAVAILABLE
    ) 