"""
GraphMemory-IDE Analytics Engine

This module provides advanced graph analytics capabilities including:
- Graph algorithms (centrality, community detection, path analysis)
- Machine learning for pattern recognition and clustering
- Real-time analytics processing
- Integration with Kuzu GraphDB and FastAPI
"""

from .models import (
    AnalyticsRequest, AnalyticsResponse, AnalyticsType,
    CentralityRequest, CentralityResponse,
    CommunityRequest, CommunityResponse,
    ClusteringRequest, ClusteringResponse,
    PathAnalysisRequest, PathAnalysisResponse,
    GraphMetrics, NodeMetrics, CommunityMetrics,
    RealtimeUpdate, AnalyticsError
)
from .engine import AnalyticsEngine
from .cache import AnalyticsCache
from .realtime import RealtimeAnalytics

__version__ = "1.0.0"
__all__ = [
    "AnalyticsEngine",
    "AnalyticsRequest",
    "AnalyticsResponse", 
    "AnalyticsType",
    "CentralityRequest",
    "CentralityResponse",
    "CommunityRequest", 
    "CommunityResponse",
    "ClusteringRequest",
    "ClusteringResponse",
    "PathAnalysisRequest",
    "PathAnalysisResponse",
    "GraphMetrics",
    "NodeMetrics",
    "CommunityMetrics",
    "RealtimeUpdate",
    "AnalyticsError",
    "AnalyticsCache",
    "RealtimeAnalytics"
] 