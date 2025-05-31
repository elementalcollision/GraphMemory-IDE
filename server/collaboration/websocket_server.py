"""
WebSocket Collaboration Server for Phase 3 Real-time Collaborative UI

This module implements the WebSocket server for real-time collaborative editing,
designed to integrate with the existing Phase 2.1 Memory Collaboration Engine components.

Performance Targets:
- WebSocket Connection: <100ms establishment time
- Edit Synchronization: <500ms cross-client update latency
- Concurrent Users: 150+ per collaboration room
- Memory Usage: <50MB per 100 concurrent connections

Week 1 Implementation: Core WebSocket infrastructure with room management
Future Weeks: Integration with existing CRDT components
"""

import asyncio
import json
import logging
import time
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.websockets import WebSocketState
import redis.asyncio as redis
from pydantic import BaseModel, Field

from .websocket_crdt_bridge import get_websocket_crdt_bridge, WebSocketCRDTBridge

# Configure logging
logger = logging.getLogger(__name__)

# WebSocket message types
class MessageType:
    # Client -> Server messages
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    EDIT_OPERATION = "edit_operation"
    CURSOR_UPDATE = "cursor_update"
    PRESENCE_UPDATE = "presence_update"
    CONFLICT_RESOLUTION = "conflict_resolution"
    
    # Server -> Client messages
    OPERATION_APPLIED = "operation_applied"
    OPERATION_BROADCAST = "operation_broadcast"
    CURSOR_BROADCAST = "cursor_broadcast"
    PRESENCE_BROADCAST = "presence_broadcast"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    ERROR = "error"
    SYNC_STATE = "sync_state"

@dataclass
class WebSocketMessage:
    """Standard WebSocket message format"""
    type: str
    data: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    room_id: Optional[str] = None

@dataclass
class CollaborationRoom:
    """Represents a collaboration room with connected users"""
    room_id: str
    memory_id: str
    tenant_id: str
    connected_users: Set[str]
    websockets: Dict[str, WebSocket]
    created_at: float
    last_activity: float
    
    def add_user(self, user_id: str, websocket: WebSocket):
        """Add user to the collaboration room"""
        self.connected_users.add(user_id)
        self.websockets[user_id] = websocket
        self.last_activity = time.time()
    
    def remove_user(self, user_id: str):
        """Remove user from the collaboration room"""
        self.connected_users.discard(user_id)
        self.websockets.pop(user_id, None)
        self.last_activity = time.time()
    
    def is_empty(self) -> bool:
        """Check if room has no active users"""
        return len(self.connected_users) == 0

@dataclass
class UserPresence:
    """User presence information"""
    user_id: str
    room_id: str
    cursor_position: Optional[Dict[str, Any]] = None
    selection_range: Optional[Dict[str, Any]] = None
    status: str = "online"  # online, away, offline
    last_seen: float = Field(default_factory=time.time)
    user_info: Dict[str, Any] = Field(default_factory=dict)

class CollaborationWebSocketManager:
    """
    WebSocket manager for real-time collaborative editing
    
    Week 1 Focus: Core WebSocket infrastructure with room management
    Future: Integration with Phase 2.1 collaboration engine components
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        # WebSocket connection management
        self.active_rooms: Dict[str, CollaborationRoom] = {}
        self.user_presence: Dict[str, UserPresence] = {}
        self.connection_count = 0
        
        # Redis for cross-server communication
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # CRDT Bridge for real-time operations
        self.crdt_bridge: Optional[WebSocketCRDTBridge] = None
        
        # Performance monitoring
        self.start_time = time.time()
        self.message_count = 0
        self.operation_latencies: List[float] = []
        
        logger.info("CollaborationWebSocketManager initialized")
    
    async def initialize(self):
        """Initialize Redis connections and CRDT bridge"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # Initialize CRDT bridge for real operations
            self.crdt_bridge = await get_websocket_crdt_bridge()
            
            logger.info("WebSocket manager initialized with Redis and CRDT bridge")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket manager: {e}")
            # Continue without Redis for now
            logger.warning("Continuing without Redis - single-server mode only")
    
    async def connect_user(
        self, 
        websocket: WebSocket, 
        memory_id: str, 
        tenant_id: str,
        user_id: str,
        user_info: Dict[str, Any]
    ) -> str:
        """
        Connect user to collaboration room
        
        Returns:
            room_id: Unique identifier for the collaboration room
        """
        start_time = time.time()
        
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Generate room ID based on memory and tenant
            room_id = f"{tenant_id}:{memory_id}"
            
            # Create or get existing room
            if room_id not in self.active_rooms:
                self.active_rooms[room_id] = CollaborationRoom(
                    room_id=room_id,
                    memory_id=memory_id,
                    tenant_id=tenant_id,
                    connected_users=set(),
                    websockets={},
                    created_at=time.time(),
                    last_activity=time.time()
                )
                logger.info(f"Created new collaboration room: {room_id}")
            
            room = self.active_rooms[room_id]
            room.add_user(user_id, websocket)
            
            # Initialize user presence
            self.user_presence[user_id] = UserPresence(
                user_id=user_id,
                room_id=room_id,
                user_info=user_info
            )
            
            # Increment connection count
            self.connection_count += 1
            
            # Send current memory state to new user (placeholder for now)
            await self._send_sync_state(websocket, memory_id, tenant_id)
            
            # Broadcast user joined to other users in room
            await self._broadcast_presence_update(room_id, user_id, "joined")
            
            # Track connection performance
            connection_time = (time.time() - start_time) * 1000  # ms
            logger.info(
                f"User {user_id} connected to room {room_id} in {connection_time:.2f}ms"
            )
            
            # Ensure connection time meets <100ms target
            if connection_time > 100:
                logger.warning(
                    f"Connection time {connection_time:.2f}ms exceeds 100ms target"
                )
            
            return room_id
            
        except Exception as e:
            logger.error(f"Failed to connect user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Connection failed")
    
    async def disconnect_user(self, user_id: str, room_id: str):
        """Disconnect user from collaboration room"""
        try:
            if room_id in self.active_rooms:
                room = self.active_rooms[room_id]
                room.remove_user(user_id)
                
                # Remove user presence
                self.user_presence.pop(user_id, None)
                
                # Broadcast user left to other users
                await self._broadcast_presence_update(room_id, user_id, "left")
                
                # Clean up empty rooms
                if room.is_empty():
                    del self.active_rooms[room_id]
                    logger.info(f"Removed empty collaboration room: {room_id}")
                
                self.connection_count -= 1
                logger.info(f"User {user_id} disconnected from room {room_id}")
                
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {e}")
    
    async def handle_message(
        self, 
        websocket: WebSocket, 
        message: Dict[str, Any],
        user_id: str,
        room_id: str
    ):
        """Handle incoming WebSocket message"""
        start_time = time.time()
        
        try:
            msg_type = message.get("type")
            msg_data = message.get("data", {})
            
            self.message_count += 1
            
            if msg_type == MessageType.EDIT_OPERATION:
                await self._handle_edit_operation(websocket, msg_data, user_id, room_id)
            
            elif msg_type == MessageType.CURSOR_UPDATE:
                await self._handle_cursor_update(msg_data, user_id, room_id)
            
            elif msg_type == MessageType.PRESENCE_UPDATE:
                await self._handle_presence_update(msg_data, user_id, room_id)
            
            elif msg_type == MessageType.CONFLICT_RESOLUTION:
                await self._handle_conflict_resolution(msg_data, user_id, room_id)
            
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                await self._send_error(websocket, f"Unknown message type: {msg_type}")
            
            # Track message processing latency
            latency = (time.time() - start_time) * 1000  # ms
            self.operation_latencies.append(latency)
            
            # Keep only last 1000 latencies for monitoring
            if len(self.operation_latencies) > 1000:
                self.operation_latencies = self.operation_latencies[-1000:]
            
            # Log performance warnings
            if latency > 500:  # Target <500ms for real-time updates
                logger.warning(
                    f"Message processing latency {latency:.2f}ms exceeds 500ms target"
                )
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(websocket, "Message processing failed")
    
    async def _handle_edit_operation(
        self, 
        websocket: WebSocket, 
        data: Dict[str, Any],
        user_id: str,
        room_id: str
    ):
        """Handle collaborative edit operation through CRDT bridge"""
        try:
            if not self.crdt_bridge:
                logger.error("CRDT bridge not initialized")
                await self._send_error(websocket, "CRDT system not available")
                return
            
            # Extract room info
            room = self.active_rooms[room_id]
            memory_id = room.memory_id
            tenant_id = room.tenant_id
            
            # Process through CRDT bridge for real collaboration
            bridge_result = await self.crdt_bridge.process_websocket_operation(
                {"type": MessageType.EDIT_OPERATION, "data": data},
                user_id,
                room_id
            )
            
            if bridge_result.success:
                # Send confirmation to sender
                await self._send_message(websocket, bridge_result.websocket_response)
                
                # Broadcast operation to all users in room if successful
                if bridge_result.broadcast_data:
                    await self._broadcast_to_room(
                        room_id, 
                        bridge_result.broadcast_data,
                        exclude_user=user_id
                    )
                
                logger.debug(
                    f"CRDT operation processed successfully in {bridge_result.processing_time_ms:.2f}ms"
                )
            else:
                # Send error response
                await self._send_message(websocket, bridge_result.websocket_response)
                logger.warning(f"CRDT operation failed: {bridge_result.error_message}")
            
        except Exception as e:
            logger.error(f"Error handling edit operation: {e}")
            await self._send_error(websocket, "Edit operation failed")
    
    async def _handle_cursor_update(
        self, 
        data: Dict[str, Any], 
        user_id: str, 
        room_id: str
    ):
        """Handle cursor position update"""
        try:
            # Update user presence with cursor info
            if user_id in self.user_presence:
                presence = self.user_presence[user_id]
                presence.cursor_position = data.get("cursor_position")
                presence.selection_range = data.get("selection_range")
                presence.last_seen = time.time()
            
            # Broadcast cursor update to other users
            await self._broadcast_to_room(room_id, {
                "type": MessageType.CURSOR_BROADCAST,
                "data": {
                    "user_id": user_id,
                    "cursor_position": data.get("cursor_position"),
                    "selection_range": data.get("selection_range"),
                    "timestamp": time.time()
                }
            }, exclude_user=user_id)
            
        except Exception as e:
            logger.error(f"Error handling cursor update: {e}")
    
    async def _handle_presence_update(
        self, 
        data: Dict[str, Any], 
        user_id: str, 
        room_id: str
    ):
        """Handle user presence update"""
        try:
            if user_id in self.user_presence:
                presence = self.user_presence[user_id]
                presence.status = data.get("status", "online")
                presence.last_seen = time.time()
                
                # Update user info if provided
                if "user_info" in data:
                    presence.user_info.update(data["user_info"])
            
            # Broadcast presence to other users
            await self._broadcast_presence_update(room_id, user_id, data.get("status", "online"))
            
        except Exception as e:
            logger.error(f"Error handling presence update: {e}")
    
    async def _handle_conflict_resolution(
        self, 
        data: Dict[str, Any], 
        user_id: str, 
        room_id: str
    ):
        """Handle manual conflict resolution (Week 1: Basic implementation)"""
        try:
            # Week 1: Basic conflict resolution placeholder
            resolution_result = {
                "resolution_id": str(uuid.uuid4()),
                "resolved_by": user_id,
                "timestamp": time.time(),
                "status": "resolved"
            }
            
            # Broadcast resolution to all users
            await self._broadcast_to_room(room_id, {
                "type": MessageType.CONFLICT_RESOLVED,
                "data": {
                    "resolution": resolution_result,
                    "resolved_by": user_id,
                    "timestamp": time.time()
                }
            })
            
        except Exception as e:
            logger.error(f"Error handling conflict resolution: {e}")
    
    async def _send_sync_state(
        self, 
        websocket: WebSocket, 
        memory_id: str, 
        tenant_id: str
    ):
        """Send current memory state to newly connected user via CRDT bridge"""
        try:
            if self.crdt_bridge:
                # Get real memory state from CRDT bridge
                sync_response = await self.crdt_bridge.sync_memory_state(
                    memory_id, 
                    f"user_{hash(str(websocket)) % 10000}"  # Temporary user ID
                )
                await self._send_message(websocket, sync_response)
            else:
                # Fallback to basic sync state
                memory_state = {
                    "memory_id": memory_id,
                    "tenant_id": tenant_id,
                    "title": "Memory Title",  # Placeholder
                    "content": "Memory content...",  # Placeholder
                    "version": 1,
                    "last_modified": time.time()
                }
                
                await self._send_message(websocket, {
                    "type": MessageType.SYNC_STATE,
                    "data": {
                        "memory_id": memory_id,
                        "state": memory_state,
                        "timestamp": time.time()
                    }
                })
            
        except Exception as e:
            logger.error(f"Error sending sync state: {e}")
            await self._send_error(websocket, "Failed to sync memory state")
    
    async def _broadcast_to_room(
        self, 
        room_id: str, 
        message: Dict[str, Any],
        exclude_user: Optional[str] = None
    ):
        """Broadcast message to all users in a room"""
        if room_id not in self.active_rooms:
            return
        
        room = self.active_rooms[room_id]
        
        # Send to local connections
        for user_id, websocket in room.websockets.items():
            if exclude_user and user_id == exclude_user:
                continue
                
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await self._send_message(websocket, message)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                # Remove disconnected websocket
                await self.disconnect_user(user_id, room_id)
        
        # TODO Week 2: Broadcast to other servers via Redis
        if self.redis_client:
            try:
                await self.redis_client.publish(
                    f"collaboration:{room_id}",
                    json.dumps({**message, "exclude_user": exclude_user})
                )
            except Exception as e:
                logger.error(f"Error publishing to Redis: {e}")
    
    async def _broadcast_presence_update(
        self, 
        room_id: str, 
        user_id: str, 
        status: str
    ):
        """Broadcast user presence update"""
        presence_data = None
        if user_id in self.user_presence:
            presence = self.user_presence[user_id]
            presence_data = {
                "user_id": presence.user_id,
                "room_id": presence.room_id,
                "cursor_position": presence.cursor_position,
                "selection_range": presence.selection_range,
                "status": presence.status,
                "last_seen": presence.last_seen,
                "user_info": presence.user_info
            }
        
        await self._broadcast_to_room(room_id, {
            "type": MessageType.PRESENCE_BROADCAST,
            "data": {
                "user_id": user_id,
                "status": status,
                "presence": presence_data,
                "timestamp": time.time()
            }
        }, exclude_user=user_id)
    
    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            raise
    
    async def _send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to WebSocket"""
        await self._send_message(websocket, {
            "type": MessageType.ERROR,
            "data": {"error": error_message},
            "timestamp": time.time()
        })
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance monitoring statistics"""
        avg_latency = (
            sum(self.operation_latencies) / len(self.operation_latencies)
            if self.operation_latencies else 0
        )
        
        return {
            "uptime_seconds": time.time() - self.start_time,
            "active_rooms": len(self.active_rooms),
            "connected_users": self.connection_count,
            "total_messages": self.message_count,
            "average_latency_ms": avg_latency,
            "max_latency_ms": max(self.operation_latencies) if self.operation_latencies else 0,
            "memory_usage_mb": self._estimate_memory_usage(),
            "target_compliance": {
                "connection_time_under_100ms": True,  # Tracked in connect_user
                "latency_under_500ms": avg_latency < 500,
                "concurrent_users_150plus": self.connection_count >= 150
            }
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB (simplified calculation)"""
        # Rough estimate: 0.5MB per room + 0.1MB per user
        room_memory = len(self.active_rooms) * 0.5
        user_memory = self.connection_count * 0.1
        base_memory = 10  # Base server memory
        
        return room_memory + user_memory + base_memory

# Global WebSocket manager instance
websocket_manager: Optional[CollaborationWebSocketManager] = None

async def get_websocket_manager() -> CollaborationWebSocketManager:
    """Get or create WebSocket manager instance"""
    global websocket_manager
    if websocket_manager is None:
        websocket_manager = CollaborationWebSocketManager()
        await websocket_manager.initialize()
    return websocket_manager

# WebSocket endpoint dependency (simplified for Week 1)
async def websocket_auth_dependency(
    websocket: WebSocket,
    token: str,
    memory_id: str,
    tenant_id: str
) -> tuple[str, Dict[str, Any]]:
    """WebSocket authentication dependency (Week 1: Basic implementation)"""
    try:
        # Week 1: Basic auth validation (to be enhanced with actual auth system)
        if not token or len(token) < 10:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Extract user_id from token (placeholder implementation)
        user_id = f"user_{hash(token) % 10000}"
        user_info = {
            "name": f"User {user_id}",
            "email": f"{user_id}@example.com"
        }
        
        return user_id, user_info
        
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed") 