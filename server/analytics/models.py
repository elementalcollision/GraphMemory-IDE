"""
Analytics data models for GraphMemory-IDE analytics engine.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import datetime

class AnalyticsType(str, Enum):
    """Types of analytics operations"""
    CENTRALITY = "centrality"
    COMMUNITY = "community"
    PATH_ANALYSIS = "path_analysis"
    CLUSTERING = "clustering"
    PATTERN_DETECTION = "pattern_detection"
    GRAPH_METRICS = "graph_metrics"
    REAL_TIME = "real_time"

class CentralityType(str, Enum):
    """Types of centrality measures"""
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"
    DEGREE = "degree"

class ClusteringType(str, Enum):
    """Types of clustering algorithms"""
    SPECTRAL = "spectral"
    KMEANS = "kmeans"
    HIERARCHICAL = "hierarchical"
    LOUVAIN = "louvain"

class AnalyticsRequest(BaseModel):
    """Base request model for analytics operations"""
    analytics_type: AnalyticsType = Field(..., description="Type of analytics to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Algorithm-specific parameters")
    filters: Optional[Dict[str, Any]] = Field(None, description="Data filters to apply")
    cache_key: Optional[str] = Field(None, description="Cache key for result caching")
    real_time: bool = Field(default=False, description="Whether to enable real-time updates")

class CentralityRequest(AnalyticsRequest):
    """Request model for centrality analysis"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.CENTRALITY)
    centrality_type: CentralityType = Field(..., description="Type of centrality measure")
    node_filters: Optional[List[str]] = Field(None, description="Specific nodes to analyze")
    normalized: bool = Field(default=True, description="Whether to normalize results")

class CommunityRequest(AnalyticsRequest):
    """Request model for community detection"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.COMMUNITY)
    algorithm: str = Field(default="louvain", description="Community detection algorithm")
    resolution: float = Field(default=1.0, description="Resolution parameter for modularity")
    min_community_size: int = Field(default=3, description="Minimum community size")

class ClusteringRequest(AnalyticsRequest):
    """Request model for clustering analysis"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.CLUSTERING)
    clustering_type: ClusteringType = Field(..., description="Type of clustering algorithm")
    n_clusters: Optional[int] = Field(None, description="Number of clusters (if applicable)")
    features: List[str] = Field(default_factory=list, description="Features to use for clustering")

class PathAnalysisRequest(AnalyticsRequest):
    """Request model for path analysis"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.PATH_ANALYSIS)
    source_nodes: List[str] = Field(..., description="Source nodes for path analysis")
    target_nodes: Optional[List[str]] = Field(None, description="Target nodes (if None, analyze from sources)")
    max_depth: int = Field(default=5, description="Maximum path depth to explore")
    path_type: str = Field(default="shortest", description="Type of paths to find")

class GraphMetrics(BaseModel):
    """Graph-level metrics and statistics"""
    node_count: int = Field(..., description="Total number of nodes")
    edge_count: int = Field(..., description="Total number of edges")
    density: float = Field(..., description="Graph density")
    average_clustering: float = Field(..., description="Average clustering coefficient")
    average_path_length: Optional[float] = Field(None, description="Average shortest path length")
    diameter: Optional[int] = Field(None, description="Graph diameter")
    connected_components: int = Field(..., description="Number of connected components")
    largest_component_size: int = Field(..., description="Size of largest connected component")

class NodeMetrics(BaseModel):
    """Node-level metrics and analytics results"""
    node_id: str = Field(..., description="Node identifier")
    centrality_scores: Dict[str, float] = Field(default_factory=dict, description="Centrality measure scores")
    community_id: Optional[str] = Field(None, description="Community membership")
    cluster_id: Optional[int] = Field(None, description="Cluster assignment")
    local_clustering: float = Field(..., description="Local clustering coefficient")
    degree: int = Field(..., description="Node degree")
    neighbors: List[str] = Field(default_factory=list, description="Neighbor node IDs")

class CommunityMetrics(BaseModel):
    """Community-level metrics"""
    community_id: str = Field(..., description="Community identifier")
    size: int = Field(..., description="Number of nodes in community")
    density: float = Field(..., description="Internal density of community")
    modularity_contribution: float = Field(..., description="Contribution to overall modularity")
    central_nodes: List[str] = Field(default_factory=list, description="Most central nodes in community")
    keywords: List[str] = Field(default_factory=list, description="Representative keywords/tags")

class AnalyticsResponse(BaseModel):
    """Base response model for analytics operations"""
    analytics_type: AnalyticsType = Field(..., description="Type of analytics performed")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, description="Analysis timestamp")
    execution_time: float = Field(..., description="Execution time in seconds")
    cache_hit: bool = Field(default=False, description="Whether result was served from cache")
    graph_metrics: Optional[GraphMetrics] = Field(None, description="Overall graph metrics")
    node_metrics: List[NodeMetrics] = Field(default_factory=list, description="Node-level results")
    community_metrics: List[CommunityMetrics] = Field(default_factory=list, description="Community-level results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class CentralityResponse(AnalyticsResponse):
    """Response model for centrality analysis"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.CENTRALITY)
    centrality_type: CentralityType = Field(..., description="Type of centrality measure")
    top_nodes: List[Dict[str, Union[str, float]]] = Field(default_factory=list, description="Top nodes by centrality")
    statistics: Dict[str, float] = Field(default_factory=dict, description="Centrality statistics")

class CommunityResponse(AnalyticsResponse):
    """Response model for community detection"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.COMMUNITY)
    algorithm: str = Field(..., description="Algorithm used")
    modularity: float = Field(..., description="Overall modularity score")
    num_communities: int = Field(..., description="Number of communities found")
    community_sizes: List[int] = Field(default_factory=list, description="Sizes of each community")

class ClusteringResponse(AnalyticsResponse):
    """Response model for clustering analysis"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.CLUSTERING)
    clustering_type: ClusteringType = Field(..., description="Type of clustering algorithm")
    n_clusters: int = Field(..., description="Number of clusters found")
    silhouette_score: Optional[float] = Field(None, description="Silhouette score for clustering quality")
    cluster_centers: Optional[List[List[float]]] = Field(None, description="Cluster centers (if applicable)")

class PathAnalysisResponse(AnalyticsResponse):
    """Response model for path analysis"""
    analytics_type: AnalyticsType = Field(default=AnalyticsType.PATH_ANALYSIS)
    paths_found: int = Field(..., description="Number of paths found")
    paths: List[Dict[str, Any]] = Field(default_factory=list, description="Path details")
    path_statistics: Dict[str, float] = Field(default_factory=dict, description="Path analysis statistics")

class RealtimeUpdate(BaseModel):
    """Model for real-time analytics updates"""
    update_type: str = Field(..., description="Type of update")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Update data")
    affected_nodes: List[str] = Field(default_factory=list, description="Nodes affected by update")
    metrics_delta: Optional[Dict[str, float]] = Field(None, description="Changes in metrics")

class AnalyticsError(BaseModel):
    """Error response model for analytics operations"""
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Request identifier for debugging") 