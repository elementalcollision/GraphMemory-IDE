"""
WebSocket Routes for Phase 3 Real-time Collaborative UI

This module defines the FastAPI WebSocket endpoints for real-time collaborative editing.
Integrates with the CollaborationWebSocketManager for room management and message handling.

Endpoints:
- /ws/collaborate/{tenant_id}/{memory_id} - Main collaboration WebSocket endpoint

Author: GraphMemory-IDE Team
Created: May 31, 2025
Version: 1.0.0
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends
from fastapi.websockets import WebSocketState

from .websocket_server import (
    CollaborationWebSocketManager,
    get_websocket_manager,
    websocket_auth_dependency
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
router = APIRouter(prefix="/ws", tags=["websocket-collaboration"])

@router.websocket("/collaborate/{tenant_id}/{memory_id}")
async def websocket_collaborate(
    websocket: WebSocket,
    tenant_id: str,
    memory_id: str,
    token: str = Query(...),
    manager: CollaborationWebSocketManager = Depends(get_websocket_manager)
):
    """
    WebSocket endpoint for real-time collaborative editing
    
    Args:
        websocket: WebSocket connection
        tenant_id: Tenant identifier for multi-tenant isolation
        memory_id: Memory document identifier
        token: Authentication token (query parameter)
        manager: WebSocket collaboration manager
    
    Protocol:
        Client sends: {"type": "message_type", "data": {...}}
        Server sends: {"type": "response_type", "data": {...}, "timestamp": float}
    
    Message Types:
        - edit_operation: Collaborative edit operations
        - cursor_update: Cursor position updates
        - presence_update: User presence status
        - conflict_resolution: Manual conflict resolution
    """
    user_id: Optional[str] = None
    room_id: Optional[str] = None
    
    try:
        # Authenticate user
        user_id, user_info = await websocket_auth_dependency(
            websocket, token, memory_id, tenant_id
        )
        
        # Connect user to collaboration room
        room_id = await manager.connect_user(
            websocket, memory_id, tenant_id, user_id, user_info
        )
        
        logger.info(f"WebSocket connected: user={user_id}, room={room_id}")
        
        # Main message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle the message
                await manager.handle_message(websocket, message, user_id, room_id)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: user={user_id}, room={room_id}")
                break
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {user_id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"error": "Invalid JSON format"},
                    "timestamp": time.time()
                }))
                
            except Exception as e:
                logger.error(f"Error handling message from {user_id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "data": {"error": "Message processing failed"},
                    "timestamp": time.time()
                }))
                
    except HTTPException as e:
        # Authentication failed
        logger.warning(f"WebSocket authentication failed: {e.detail}")
        await websocket.close(code=4001, reason=e.detail)
        
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=1011, reason="Internal server error")
        
    finally:
        # Clean up connection
        if user_id and room_id:
            try:
                await manager.disconnect_user(user_id, room_id)
                logger.info(f"Cleaned up WebSocket connection: user={user_id}, room={room_id}")
            except Exception as e:
                logger.error(f"Error cleaning up WebSocket connection: {e}")

@router.get("/collaboration/stats")
async def get_collaboration_stats(
    manager: CollaborationWebSocketManager = Depends(get_websocket_manager)
) -> Dict[str, Any]:
    """Get collaboration server performance statistics"""
    return manager.get_performance_stats()

@router.get("/collaboration/rooms")
async def get_active_rooms(
    manager: CollaborationWebSocketManager = Depends(get_websocket_manager)
) -> Dict[str, Any]:
    """Get information about active collaboration rooms"""
    rooms_info = {}
    
    for room_id, room in manager.active_rooms.items():
        rooms_info[room_id] = {
            "memory_id": room.memory_id,
            "tenant_id": room.tenant_id,
            "connected_users": len(room.connected_users),
            "user_list": list(room.connected_users),
            "created_at": room.created_at,
            "last_activity": room.last_activity
        }
    
    return {
        "total_rooms": len(manager.active_rooms),
        "total_users": manager.connection_count,
        "rooms": rooms_info
    }

@router.get("/collaboration/presence/{room_id}")
async def get_room_presence(
    room_id: str,
    manager: CollaborationWebSocketManager = Depends(get_websocket_manager)
) -> Dict[str, Any]:
    """Get presence information for users in a specific room"""
    room_presence = {}
    
    for user_id, presence in manager.user_presence.items():
        if presence.room_id == room_id:
            room_presence[user_id] = {
                "user_id": presence.user_id,
                "status": presence.status,
                "last_seen": presence.last_seen,
                "cursor_position": presence.cursor_position,
                "selection_range": presence.selection_range,
                "user_info": presence.user_info
            }
    
    return {
        "room_id": room_id,
        "users_online": len(room_presence),
        "presence": room_presence
    }

# Health check endpoint for WebSocket service
@router.get("/health")
async def websocket_health_check(
    manager: CollaborationWebSocketManager = Depends(get_websocket_manager)
) -> Dict[str, Any]:
    """Health check for WebSocket collaboration service"""
    stats = manager.get_performance_stats()
    
    # Determine health status based on performance metrics
    health_status = "healthy"
    issues = []
    
    if stats["average_latency_ms"] > 500:
        health_status = "degraded"
        issues.append("High average latency")
    
    if stats["memory_usage_mb"] > 500:  # 500MB threshold
        health_status = "degraded"
        issues.append("High memory usage")
    
    return {
        "status": health_status,
        "timestamp": time.time(),
        "uptime_seconds": stats["uptime_seconds"],
        "active_connections": stats["connected_users"],
        "active_rooms": stats["active_rooms"],
        "performance": {
            "average_latency_ms": stats["average_latency_ms"],
            "memory_usage_mb": stats["memory_usage_mb"],
            "target_compliance": stats["target_compliance"]
        },
        "issues": issues
    }

# Import time for timestamps
import time 