"""
FastAPI routes for GraphMemory-IDE analytics engine.
Provides REST API endpoints for analytics operations and WebSocket support for real-time updates.
Enhanced with Phase 3 endpoints for GPU acceleration, performance monitoring, and benchmarking.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query, Body, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
import kuzu
import redis.asyncio as redis

from .analytics.models import (
    AnalyticsRequest, AnalyticsResponse, AnalyticsType,
    CentralityRequest, CommunityRequest, ClusteringRequest, PathAnalysisRequest,
    RealtimeUpdate
)
from .analytics.engine import AnalyticsEngine
from .analytics.realtime import RealtimeAnalytics
from .analytics.cache import AnalyticsCache

# Phase 3 imports
try:
    from .analytics.benchmarks import benchmark_suite
    from .analytics.monitoring import get_health_endpoint, get_metrics_endpoint
    PHASE3_AVAILABLE = True
except ImportError:
    PHASE3_AVAILABLE = False
    logger.warning("Phase 3 components not available")

logger = logging.getLogger(__name__)

# Global analytics engine instance
analytics_engine: Optional[AnalyticsEngine] = None
realtime_analytics: Optional[RealtimeAnalytics] = None

# Global variables for analytics engine state
analytics_engine_initialized = False
kuzu_connection = None
redis_client = None
analytics_cache = {}
service_start_time = time.time()

def get_analytics_engine() -> AnalyticsEngine:
    """Dependency to get analytics engine instance"""
    global analytics_engine
    if analytics_engine is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialized")
    return analytics_engine

def get_realtime_analytics() -> RealtimeAnalytics:
    """Dependency to get real-time analytics instance"""
    global realtime_analytics
    if realtime_analytics is None:
        raise HTTPException(status_code=503, detail="Real-time analytics not initialized")
    return realtime_analytics

async def initialize_analytics_engine(kuzu_conn, redis_url: str) -> None:
    """Initialize the analytics engine"""
    global analytics_engine, analytics_engine_initialized, kuzu_connection
    
    try:
        logger.info("Initializing analytics engine...")
        
        kuzu_connection = kuzu_conn
        analytics_engine = AnalyticsEngine(kuzu_conn, redis_url)
        
        # Initialize the engine
        success = await analytics_engine.initialize()
        
        if success:
            analytics_engine_initialized = True
            logger.info("Analytics engine initialized successfully")
        else:
            logger.error("Analytics engine initialization failed")
            
        return success
        
    except Exception as e:
        logger.error(f"Analytics engine initialization error: {e}")
        analytics_engine_initialized = False
        return False

async def shutdown_analytics_engine() -> None:
    """Shutdown the analytics engine"""
    global analytics_engine, analytics_engine_initialized
    
    try:
        logger.info("Shutting down analytics engine...")
        
        if analytics_engine and analytics_engine.redis_client:
            await analytics_engine.redis_client.close()
        
        analytics_engine_initialized = False
        analytics_engine = None
        
        logger.info("Analytics engine shutdown complete")
        
    except Exception as e:
        logger.error(f"Analytics engine shutdown error: {e}")

# Create router
router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.post("/analyze", response_model=AnalyticsResponse)
async def analyze(
    request: AnalyticsRequest,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> AnalyticsResponse:
    """
    Perform analytics analysis based on request type.
    Supports centrality, community detection, clustering, and path analysis.
    """
    try:
        result = await engine.process_analytics_request(request)
        return result
    except Exception as e:
        logger.error(f"Analytics analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/centrality", response_model=AnalyticsResponse)
async def analyze_centrality(
    request: CentralityRequest,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> AnalyticsResponse:
    """Perform centrality analysis on the graph"""
    try:
        result = await engine.analyze_centrality(request)
        return result
    except Exception as e:
        logger.error(f"Centrality analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Centrality analysis failed: {str(e)}")

@router.post("/community", response_model=AnalyticsResponse)
async def detect_communities(
    request: CommunityRequest,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> AnalyticsResponse:
    """Perform community detection on the graph"""
    try:
        result = await engine.detect_communities(request)
        return result
    except Exception as e:
        logger.error(f"Community detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Community detection failed: {str(e)}")

@router.post("/paths", response_model=AnalyticsResponse)
async def analyze_paths(
    request: PathAnalysisRequest,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> AnalyticsResponse:
    """Perform path analysis on the graph"""
    try:
        result = await engine.analyze_paths(request)
        return result
    except Exception as e:
        logger.error(f"Path analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Path analysis failed: {str(e)}")

@router.post("/clustering", response_model=AnalyticsResponse)
async def perform_clustering(
    request: ClusteringRequest,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> AnalyticsResponse:
    """Perform ML clustering analysis on the graph"""
    try:
        result = await engine.perform_clustering(request)
        return result
    except Exception as e:
        logger.error(f"Clustering analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Clustering analysis failed: {str(e)}")

@router.post("/anomalies")
async def detect_anomalies(
    filters: Optional[Dict[str, Any]] = None,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> Dict[str, Any]:
    """Detect anomalous nodes using ML techniques"""
    try:
        result = await engine.detect_anomalies(filters)
        return result
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")

@router.get("/metrics")
async def get_graph_metrics(
    filters: Optional[str] = None,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> Dict[str, Any]:
    """Get basic graph metrics and statistics"""
    try:
        filter_dict = {}
        if filters:
            import json
            filter_dict = json.loads(filters)
        
        metrics = await engine.calculate_graph_metrics(filter_dict)
        return {
            "graph_metrics": metrics.dict(),
            "timestamp": metrics.timestamp if hasattr(metrics, 'timestamp') else None
        }
    except Exception as e:
        logger.error(f"Failed to get graph metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/status")
async def get_analytics_status(
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> Dict[str, Any]:
    """Get analytics engine status and statistics"""
    try:
        stats = engine.get_engine_stats()
        
        # Handle async cache stats
        if "cache_stats" in stats and hasattr(stats["cache_stats"], "__await__"):
            stats["cache_stats"] = await stats["cache_stats"]
        
        # Add Phase 3 status if available
        phase3_status = {}
        if hasattr(engine, 'get_phase3_status'):
            try:
                phase3_status = await engine.get_phase3_status()
            except Exception as e:
                logger.warning(f"Failed to get Phase 3 status: {e}")
        
        return {
            "status": "active" if engine.initialized else "inactive",
            "engine_stats": stats,
            "phase3_status": phase3_status,
            "available_analytics": [
                "centrality", "community", "clustering", 
                "path_analysis", "graph_metrics", "anomaly_detection"
            ],
            "ml_capabilities": [
                "spectral_clustering", "kmeans_clustering", "hierarchical_clustering",
                "isolation_forest_anomaly_detection", "feature_extraction"
            ],
            "networkx_algorithms": [
                "pagerank", "betweenness_centrality", "closeness_centrality",
                "eigenvector_centrality", "louvain_communities", "modularity"
            ],
            "phase3_features": [
                "gpu_acceleration", "performance_monitoring", "concurrent_processing",
                "benchmarking_suite", "production_monitoring"
            ] if PHASE3_AVAILABLE else []
        }
    except Exception as e:
        logger.error(f"Failed to get analytics status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.delete("/cache")
async def clear_analytics_cache(
    pattern: Optional[str] = None,
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> Dict[str, Any]:
    """Clear analytics cache entries"""
    try:
        if pattern:
            cleared = await engine.cache.invalidate_pattern(pattern)
            return {"message": f"Cleared {cleared} cache entries matching pattern: {pattern}"}
        else:
            success = await engine.cache.clear_all()
            return {"message": "All analytics cache cleared" if success else "Failed to clear cache"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

# WebSocket endpoint for real-time analytics
@router.websocket("/ws/{connection_id}")
async def websocket_analytics(
    websocket: WebSocket,
    connection_id: str,
    user_id: Optional[str] = None,
    realtime: RealtimeAnalytics = Depends(get_realtime_analytics)
):
    """WebSocket endpoint for real-time analytics updates"""
    try:
        await realtime.handle_websocket_connection(websocket, connection_id, user_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")

# Server-Sent Events endpoint for real-time analytics
@router.get("/stream/{analytics_type}")
async def stream_analytics(
    analytics_type: str,
    realtime: RealtimeAnalytics = Depends(get_realtime_analytics)
):
    """Server-Sent Events stream for analytics updates"""
    try:
        if analytics_type not in ["centrality", "community", "clustering", "path_analysis", "graph_metrics"]:
            raise HTTPException(status_code=400, detail="Invalid analytics type")
        
        async def generate_stream() -> None:
            async for data in realtime.generate_sse_stream(analytics_type):
                yield data
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    except Exception as e:
        logger.error(f"Failed to create SSE stream: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create stream: {str(e)}")

@router.get("/realtime/stats")
async def get_realtime_stats(
    realtime: RealtimeAnalytics = Depends(get_realtime_analytics)
) -> Dict[str, Any]:
    """Get real-time analytics statistics"""
    try:
        return realtime.get_realtime_stats()
    except Exception as e:
        logger.error(f"Failed to get realtime stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.post("/realtime/publish")
async def publish_update(
    analytics_type: str,
    update_data: Dict[str, Any],
    realtime: RealtimeAnalytics = Depends(get_realtime_analytics)
) -> Dict[str, Any]:
    """Manually publish a real-time update (for testing/admin purposes)"""
    try:
        update = RealtimeUpdate(
            update_type="manual",
            data=update_data
        )
        await realtime.publish_update(analytics_type, update)
        return {"message": f"Update published to {analytics_type} stream"}
    except Exception as e:
        logger.error(f"Failed to publish update: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish update: {str(e)}")

# Health check endpoint
@router.get("/health")
async def get_analytics_health() -> None:
    """Get analytics service health status"""
    return {
        "status": "healthy" if analytics_engine_initialized else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - service_start_time
    }

# Phase 3 Endpoints

@router.get("/phase3/status")
async def get_phase3_status(
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> Dict[str, Any]:
    """Get comprehensive Phase 3 status and capabilities"""
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 3 components not available")
    
    try:
        if hasattr(engine, 'get_phase3_status'):
            status = await engine.get_phase3_status()
            status["phase3_available"] = True
            status["components_loaded"] = PHASE3_AVAILABLE
            return status
        else:
            return {
                "phase3_available": False,
                "error": "Phase 3 methods not available in engine"
            }
    except Exception as e:
        logger.error(f"Failed to get Phase 3 status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Phase 3 status: {str(e)}")

@router.get("/gpu/status")
async def get_gpu_status(
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> Dict[str, Any]:
    """Get GPU acceleration status and capabilities"""
    try:
        if hasattr(engine, 'gpu_manager'):
            gpu_status = engine.gpu_manager.get_acceleration_status()
            return {
                "gpu_acceleration": gpu_status,
                "supported_algorithms": [
                    "pagerank", "betweenness_centrality", "louvain_communities",
                    "connected_components", "shortest_paths"
                ],
                "performance_estimate": "10x-500x speedup for supported algorithms"
            }
        else:
            return {
                "gpu_acceleration": {
                    "gpu_available": False,
                    "gpu_enabled": False,
                    "status": "not_available"
                },
                "message": "GPU acceleration not available"
            }
    except Exception as e:
        logger.error(f"Failed to get GPU status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get GPU status: {str(e)}")

@router.get("/performance/metrics")
async def get_performance_metrics(
    engine: AnalyticsEngine = Depends(get_analytics_engine)
) -> Dict[str, Any]:
    """Get real-time performance metrics"""
    try:
        if hasattr(engine, 'performance_monitor'):
            metrics = engine.performance_monitor.get_performance_summary()
            return {
                "performance_metrics": metrics,
                "collection_enabled": True,
                "monitoring_active": True
            }
        else:
            return {
                "performance_metrics": {
                    "status": "basic_monitoring",
                    "uptime": "unknown"
                },
                "collection_enabled": False,
                "monitoring_active": False
            }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.post("/benchmarks/run")
async def run_benchmarks(
    test_types: Optional[list] = None,
    graph_sizes: Optional[list] = None
) -> Dict[str, Any]:
    """Run performance benchmarks"""
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Benchmarking suite not available")
    
    try:
        # Run comprehensive benchmark if no specific tests requested
        if test_types is None:
            results = await benchmark_suite.run_comprehensive_benchmark()
        else:
            results = {}
            if "centrality" in test_types:
                results["centrality"] = await benchmark_suite.benchmark_centrality_algorithms(graph_sizes)
            if "community" in test_types:
                results["community"] = await benchmark_suite.benchmark_community_detection(graph_sizes)
            if "clustering" in test_types:
                results["clustering"] = await benchmark_suite.benchmark_ml_clustering(graph_sizes)
            if "gpu_comparison" in test_types:
                results["gpu_comparison"] = await benchmark_suite.benchmark_gpu_vs_cpu()
            if "concurrent" in test_types:
                results["concurrent"] = await benchmark_suite.benchmark_concurrent_processing()
        
        return {
            "benchmark_results": results,
            "status": "completed",
            "timestamp": results.get("summary", {}).get("timestamp", "unknown")
        }
    except Exception as e:
        logger.error(f"Benchmark execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {str(e)}")

@router.get("/benchmarks/export")
async def export_benchmark_results(
    format: str = "json"
) -> Dict[str, Any]:
    """Export benchmark results in specified format"""
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Benchmarking suite not available")
    
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")
        
        exported_data = benchmark_suite.export_results(format)
        return {
            "format": format,
            "data": exported_data,
            "export_timestamp": "current_time"
        }
    except Exception as e:
        logger.error(f"Benchmark export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Benchmark export failed: {str(e)}")

@router.get("/monitoring/health")
async def get_monitoring_health() -> Dict[str, Any]:
    """Get comprehensive health check for all analytics components"""
    if not PHASE3_AVAILABLE:
        # Fallback basic health check
        return {
            "overall_status": "basic",
            "components": {
                "analytics_engine": {
                    "healthy": analytics_engine_initialized,
                    "status": "operational" if analytics_engine_initialized else "not_initialized"
                }
            },
            "phase3_available": False
        }
    
    try:
        health_status = await get_health_endpoint()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/monitoring/prometheus")
async def get_prometheus_metrics() -> None:
    """Get Prometheus metrics for monitoring"""
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Prometheus monitoring not available")
    
    try:
        return await get_metrics_endpoint()
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}") 