"""
Dashboard Routes for Real-time Analytics

This module provides FastAPI routes for the real-time dashboard,
including SSE endpoints and dashboard data APIs.
"""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from typing import Dict, Any, Optional

from .sse_server import DashboardSSEManager
from ..auth import get_optional_current_user
from ..models import User

logger = logging.getLogger(__name__)

# Create router for dashboard endpoints
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Global SSE manager instance
sse_manager: Optional[DashboardSSEManager] = None


def get_sse_manager() -> DashboardSSEManager:
    """Get the global SSE manager instance"""
    global sse_manager
    if sse_manager is None:
        # Initialize with analytics engine if available
        try:
            from ..analytics.engine import AnalyticsEngine
            analytics_engine = AnalyticsEngine()
            sse_manager = DashboardSSEManager(analytics_engine)
        except ImportError:
            logger.warning("Analytics engine not available, using mock data")
            sse_manager = DashboardSSEManager()
    return sse_manager


@dashboard_router.on_event("startup")
async def startup_dashboard() -> None:
    """Initialize dashboard services on startup"""
    manager = get_sse_manager()
    await manager.start()
    logger.info("Dashboard services started")


@dashboard_router.on_event("shutdown")
async def shutdown_dashboard() -> None:
    """Cleanup dashboard services on shutdown"""
    manager = get_sse_manager()
    await manager.stop()
    logger.info("Dashboard services stopped")


@dashboard_router.get("/stream/analytics")
async def stream_analytics(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Stream real-time analytics data via Server-Sent Events
    
    Provides 1-second updates with:
    - Active nodes and edges
    - Query rate and cache hit rate
    - Memory and CPU usage
    - Response time metrics
    """
    connection_id = str(uuid.uuid4())
    manager = get_sse_manager()
    
    try:
        manager.add_connection(connection_id)
        logger.info(f"Analytics stream started for connection {connection_id}")
        
        return EventSourceResponse(
            manager.analytics_stream(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    except Exception as e:
        logger.error(f"Error starting analytics stream: {e}")
        manager.remove_connection(connection_id)
        raise HTTPException(status_code=500, detail="Failed to start analytics stream")


@dashboard_router.get("/stream/memory")
async def stream_memory(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Stream real-time memory insights via Server-Sent Events
    
    Provides 5-second updates with:
    - Total memories by type
    - Memory growth rate
    - Average memory size
    - Memory efficiency metrics
    """
    connection_id = str(uuid.uuid4())
    manager = get_sse_manager()
    
    try:
        manager.add_connection(connection_id)
        logger.info(f"Memory stream started for connection {connection_id}")
        
        return EventSourceResponse(
            manager.memory_stream(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    except Exception as e:
        logger.error(f"Error starting memory stream: {e}")
        manager.remove_connection(connection_id)
        raise HTTPException(status_code=500, detail="Failed to start memory stream")


@dashboard_router.get("/stream/graphs")
async def stream_graph_data(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Stream real-time graph metrics via Server-Sent Events
    
    Provides 2-second updates with:
    - Node and edge counts
    - Graph topology metrics
    - Centrality statistics
    - Connected components
    """
    connection_id = str(uuid.uuid4())
    manager = get_sse_manager()
    
    try:
        manager.add_connection(connection_id)
        logger.info(f"Graph stream started for connection {connection_id}")
        
        return EventSourceResponse(
            manager.graph_stream(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    except Exception as e:
        logger.error(f"Error starting graph stream: {e}")
        manager.remove_connection(connection_id)
        raise HTTPException(status_code=500, detail="Failed to start graph stream")


@dashboard_router.get("/latest")
async def get_latest_data(
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """
    Get the latest dashboard data (non-streaming)
    
    Returns current snapshot of all dashboard metrics
    for initial page load or fallback scenarios
    """
    try:
        manager = get_sse_manager()
        
        # Get latest data from all streams
        analytics_data = await manager.get_analytics_data()
        memory_data = await manager.get_memory_insights()
        graph_data = await manager.get_graph_metrics()
        
        return {
            "timestamp": manager._last_update,
            "analytics": analytics_data,
            "memory": memory_data,
            "graph": graph_data,
            "connection_stats": manager.get_connection_stats()
        }
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get latest data")


@dashboard_router.get("/status")
async def dashboard_status(
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """
    Get dashboard service status and health information
    """
    try:
        manager = get_sse_manager()
        
        return {
            "status": "healthy" if manager._running else "stopped",
            "connection_stats": manager.get_connection_stats(),
            "last_updates": manager._last_update,
            "services": {
                "sse_manager": "running" if manager._running else "stopped",
                "analytics_engine": "available" if manager.analytics_engine else "mock_data"
            }
        }
    except Exception as e:
        logger.error(f"Error getting dashboard status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@dashboard_router.get("/config")
async def get_dashboard_config(
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """
    Get dashboard configuration and settings
    """
    return {
        "refresh_rates": {
            "analytics": "1s",
            "memory": "5s",
            "graphs": "2s"
        },
        "features": {
            "real_time_streaming": True,
            "authentication": True,
            "caching": True,
            "error_recovery": True
        },
        "endpoints": {
            "analytics_stream": "/dashboard/stream/analytics",
            "memory_stream": "/dashboard/stream/memory",
            "graph_stream": "/dashboard/stream/graphs",
            "latest_data": "/dashboard/latest",
            "status": "/dashboard/status"
        }
    } 