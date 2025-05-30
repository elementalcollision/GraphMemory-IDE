"""
GraphMemory-IDE Collaboration Engine

Core coordination system for multi-user real-time collaboration.
Integrates with existing WebSocket/Redis infrastructure and manages
session lifecycle, user coordination, and operation broadcasting.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Set
from uuid import uuid4
import redis.asyncio as redis
from fastapi import WebSocket

from .state import (
    CollaborationState, SessionState, UserRole, ActivityType,
    UserPresence, CollaborationMetrics
)
from .session_manager import SessionManager
from ..auth import verify_jwt_token


logger = logging.getLogger(__name__)


class CollaborationEngine:
    """
    Central coordination engine for multi-user collaboration.
    
    Features:
    - Session lifecycle management
    - Real-time operation broadcasting via Redis pub/sub
    - User presence and activity tracking
    - Integration with existing authentication
    - WebSocket connection management
    - Performance monitoring and metrics
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        session_manager: Optional[SessionManager] = None
    ):
        self.redis = redis_client
        self.session_manager = session_manager or SessionManager(redis_client)
        
        # Active WebSocket connections by user_id
        self.connections: Dict[str, WebSocket] = {}
        
        # User to sessions mapping
        self.user_sessions: Dict[str, Set[str]] = {}
        
        # Session event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "user_joined": [],
            "user_left": [],
            "operation_created": [],
            "conflict_detected": [],
            "conflict_resolved": [],
            "session_state_changed": []
        }
        
        # Performance tracking
        self.metrics = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_users": 0,
            "operations_per_second": 0.0,
            "average_latency": 0.0
        }
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize the collaboration engine"""
        logger.info("Initializing GraphMemory-IDE Collaboration Engine")
        
        # Start background tasks
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        metrics_task = asyncio.create_task(self._metrics_loop())
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self._background_tasks.update([heartbeat_task, metrics_task, cleanup_task])
        
        # Subscribe to Redis channels for cross-server coordination
        await self._setup_redis_subscriptions()
        
        logger.info("Collaboration engine initialized successfully")

    async def shutdown(self) -> None:
        """Graceful shutdown of the collaboration engine"""
        logger.info("Shutting down collaboration engine")
        
        self._shutdown_event.set()
        
        # Close all WebSocket connections
        for user_id, websocket in self.connections.items():
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket for user {user_id}: {e}")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("Collaboration engine shutdown complete")

    async def connect_user(
        self, 
        websocket: WebSocket, 
        user_id: str, 
        username: str,
        token: Optional[str] = None
    ) -> bool:
        """
        Connect a user to the collaboration system.
        
        Args:
            websocket: WebSocket connection
            user_id: Unique user identifier
            username: Display name
            token: JWT authentication token
            
        Returns:
            bool: True if connection successful
        """
        try:
            # Verify authentication if token provided
            if token:
                payload = verify_jwt_token(token)
                if not payload or payload.get("user_id") != user_id:
                    logger.warning(f"Authentication failed for user {user_id}")
                    return False
            
            # Accept WebSocket connection
            await websocket.accept()
            
            # Store connection
            self.connections[user_id] = websocket
            
            # Initialize user session tracking
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            
            # Notify event handlers
            await self._emit_event("user_connected", {
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"User {username} ({user_id}) connected to collaboration system")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect user {user_id}: {e}")
            return False

    async def disconnect_user(self, user_id: str) -> None:
        """Disconnect a user and clean up their sessions"""
        try:
            # Remove from all active sessions
            if user_id in self.user_sessions:
                sessions_to_leave = list(self.user_sessions[user_id])
                for session_id in sessions_to_leave:
                    await self.leave_session(user_id, session_id)
            
            # Remove connection
            if user_id in self.connections:
                del self.connections[user_id]
            
            # Remove session tracking
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            
            await self._emit_event("user_disconnected", {
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"User {user_id} disconnected from collaboration system")
            
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {e}")

    async def join_session(
        self,
        user_id: str,
        username: str,
        resource_type: str,
        resource_id: str,
        role: UserRole = UserRole.COLLABORATOR
    ) -> Optional[str]:
        """
        Join a collaborative editing session.
        
        Args:
            user_id: User identifier
            username: Display name
            resource_type: Type of resource ('memory', 'graph', 'workspace')
            resource_id: Resource identifier
            role: User role in the session
            
        Returns:
            Optional[str]: Session ID if successful
        """
        try:
            # Create or get existing session
            session = await self.session_manager.get_or_create_session(
                resource_type, resource_id
            )
            
            # Add user to session
            presence = await session.add_user(user_id, username, role)
            
            # Track user session membership
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session.session_id)
            
            # Broadcast user joined event
            await self._broadcast_to_session(session.session_id, {
                "type": "user_joined",
                "user": presence.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, exclude_user=user_id)
            
            # Send session state to new user
            if user_id in self.connections:
                session_summary = await session.get_session_summary()
                await self._send_to_user(user_id, {
                    "type": "session_joined",
                    "session": session_summary,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            await self._emit_event("user_joined", {
                "session_id": session.session_id,
                "user_id": user_id,
                "username": username,
                "role": role.value,
                "resource_type": resource_type,
                "resource_id": resource_id
            })
            
            logger.info(f"User {username} joined session {session.session_id}")
            return session.session_id
            
        except Exception as e:
            logger.error(f"Error joining session for user {user_id}: {e}")
            return None

    async def leave_session(self, user_id: str, session_id: str) -> bool:
        """Remove a user from a collaborative session"""
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                return False
            
            # Get user info before removal
            user_info = None
            if user_id in session.users:
                user_info = session.users[user_id].to_dict()
            
            # Remove user from session
            success = await session.remove_user(user_id)
            if not success:
                return False
            
            # Update user session tracking
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
            
            # Broadcast user left event
            if user_info:
                await self._broadcast_to_session(session_id, {
                    "type": "user_left",
                    "user": user_info,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, exclude_user=user_id)
            
            await self._emit_event("user_left", {
                "session_id": session_id,
                "user_id": user_id
            })
            
            logger.info(f"User {user_id} left session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error leaving session {session_id} for user {user_id}: {e}")
            return False

    async def update_user_activity(
        self,
        user_id: str,
        session_id: str,
        activity_type: ActivityType,
        activity_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update user activity and broadcast to other session participants"""
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                return False
            
            # Extract cursor and selection from activity data
            cursor_position = activity_data.get("cursor_position") if activity_data else None
            selection = activity_data.get("selection") if activity_data else None
            
            # Update user activity
            success = await session.update_user_activity(
                user_id, activity_type, cursor_position, selection
            )
            
            if success:
                # Broadcast activity update
                await self._broadcast_to_session(session_id, {
                    "type": "user_activity",
                    "user_id": user_id,
                    "activity_type": activity_type.value,
                    "activity_data": activity_data or {},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, exclude_user=user_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
            return False

    async def broadcast_operation(
        self,
        session_id: str,
        operation_data: Dict[str, Any],
        source_user_id: str
    ) -> bool:
        """
        Broadcast an operation to all session participants.
        
        Args:
            session_id: Target session
            operation_data: Operation details
            source_user_id: User who initiated the operation
            
        Returns:
            bool: True if broadcast successful
        """
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for operation broadcast")
                return False
            
            # Register operation in session
            operation_id = str(uuid4())
            sequence_number = await session.register_operation(operation_id)
            
            # Prepare broadcast message
            message = {
                "type": "operation",
                "operation_id": operation_id,
                "sequence_number": sequence_number,
                "source_user_id": source_user_id,
                "session_id": session_id,
                "data": operation_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to all session participants except source
            await self._broadcast_to_session(session_id, message, exclude_user=source_user_id)
            
            # Emit event for handlers
            await self._emit_event("operation_created", {
                "session_id": session_id,
                "operation_id": operation_id,
                "operation_data": operation_data,
                "source_user_id": source_user_id
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error broadcasting operation: {e}")
            return False

    async def handle_conflict(
        self,
        session_id: str,
        conflict_data: Dict[str, Any]
    ) -> Optional[str]:
        """Handle and track operation conflicts"""
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                return None
            
            conflict_id = str(uuid4())
            await session.register_conflict(conflict_id, conflict_data)
            
            # Broadcast conflict notification
            await self._broadcast_to_session(session_id, {
                "type": "conflict_detected",
                "conflict_id": conflict_id,
                "conflict_data": conflict_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            await self._emit_event("conflict_detected", {
                "session_id": session_id,
                "conflict_id": conflict_id,
                "conflict_data": conflict_data
            })
            
            return conflict_id
            
        except Exception as e:
            logger.error(f"Error handling conflict: {e}")
            return None

    async def resolve_conflict(
        self,
        session_id: str,
        conflict_id: str,
        resolution_data: Dict[str, Any],
        resolver_user_id: str
    ) -> bool:
        """Resolve a conflict and broadcast the resolution"""
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                return False
            
            success = await session.resolve_conflict(conflict_id, resolution_data)
            if success:
                # Broadcast resolution
                await self._broadcast_to_session(session_id, {
                    "type": "conflict_resolved",
                    "conflict_id": conflict_id,
                    "resolution_data": resolution_data,
                    "resolver_user_id": resolver_user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                await self._emit_event("conflict_resolved", {
                    "session_id": session_id,
                    "conflict_id": conflict_id,
                    "resolution_data": resolution_data,
                    "resolver_user_id": resolver_user_id
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error resolving conflict: {e}")
            return False

    async def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a session"""
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                return None
            
            return await session.get_session_summary()
            
        except Exception as e:
            logger.error(f"Error getting session metrics: {e}")
            return None

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add an event handler for collaboration events"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)

    async def _broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None
    ) -> None:
        """Broadcast a message to all users in a session"""
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                return
            
            active_users = await session.get_active_users()
            
            for user in active_users:
                if exclude_user and user.user_id == exclude_user:
                    continue
                
                await self._send_to_user(user.user_id, message)
                
        except Exception as e:
            logger.error(f"Error broadcasting to session {session_id}: {e}")

    async def _send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific user"""
        try:
            if user_id in self.connections:
                websocket = self.connections[user_id]
                await websocket.send_text(json.dumps(message))
                return True
            else:
                # User not connected to this server instance
                # Publish to Redis for cross-server delivery
                await self.redis.publish(
                    f"collaboration:user:{user_id}",
                    json.dumps(message)
                )
                return True
                
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            return False

    async def _emit_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Emit an event to all registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

    async def _setup_redis_subscriptions(self) -> None:
        """Setup Redis pub/sub for cross-server coordination"""
        # This would be implemented to handle cross-server message routing
        # For now, we focus on single-server operation
        pass

    async def _heartbeat_loop(self) -> None:
        """Background heartbeat to maintain session health"""
        while not self._shutdown_event.is_set():
            try:
                # Update session health metrics
                active_sessions = await self.session_manager.get_active_session_count()
                self.metrics["active_sessions"] = active_sessions
                self.metrics["total_users"] = len(self.connections)
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)

    async def _metrics_loop(self) -> None:
        """Background metrics collection"""
        while not self._shutdown_event.is_set():
            try:
                # Collect and publish metrics
                # This would integrate with the Day 8 observability platform
                await asyncio.sleep(60)  # Metrics every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(10)

    async def _cleanup_loop(self) -> None:
        """Background cleanup of idle sessions and expired data"""
        while not self._shutdown_event.is_set():
            try:
                # Clean up idle sessions
                await self.session_manager.cleanup_idle_sessions()
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(30) 