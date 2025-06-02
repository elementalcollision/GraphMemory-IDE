"""
Real-time Collaboration Manager for GraphMemory-IDE

This module provides real-time collaboration features including:
- Multi-user dashboard editing with conflict resolution
- Live cursor tracking and user presence indicators
- Real-time commenting and annotation system
- Collaborative query building and sharing
- Live synchronization across all connected clients

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

from fastapi import WebSocket, WebSocketDisconnect
import asyncpg
import redis.asyncio as redis


class CollaborationEventType(Enum):
    """Types of collaboration events."""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    CURSOR_MOVE = "cursor_move"
    ELEMENT_SELECT = "element_select"
    ELEMENT_EDIT = "element_edit"
    ELEMENT_LOCK = "element_lock"
    ELEMENT_UNLOCK = "element_unlock"
    COMMENT_ADD = "comment_add"
    COMMENT_UPDATE = "comment_update"
    COMMENT_DELETE = "comment_delete"
    PRESENCE_UPDATE = "presence_update"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"


@dataclass
class UserPresence:
    """User presence information."""
    user_id: str
    display_name: str
    avatar_url: Optional[str] = None
    cursor_position: Optional[Dict[str, Any]] = None
    selected_element: Optional[str] = None
    last_activity: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"  # active, idle, away
    color: str = "#007bff"  # User's color for cursors and highlights


@dataclass
class CollaborationEvent:
    """Real-time collaboration event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: CollaborationEventType
    user_id: str
    resource_type: str  # dashboard, query, report
    resource_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    client_id: Optional[str] = None


@dataclass
class ElementLock:
    """Lock on a dashboard element for exclusive editing."""
    element_id: str
    locked_by: str
    locked_at: datetime
    expires_at: datetime
    lock_type: str = "edit"  # edit, view


@dataclass
class Comment:
    """Collaboration comment/annotation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    display_name: str
    resource_type: str
    resource_id: str
    element_id: Optional[str] = None  # For element-specific comments
    content: str
    position: Optional[Dict[str, Any]] = None  # x, y coordinates for positioning
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_resolved: bool = False
    thread_id: Optional[str] = None  # For comment threads


class RealTimeCollaborationManager:
    """Manager for real-time collaboration features."""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: Optional[redis.Redis] = None):
        self.db_pool = db_pool
        self.redis_client = redis_client
        
        # WebSocket connections by resource
        self.resource_connections: Dict[str, Set[WebSocket]] = {}
        
        # User presence tracking
        self.user_presence: Dict[str, UserPresence] = {}
        
        # Element locks
        self.element_locks: Dict[str, ElementLock] = {}
        
        # Lock expiration (5 minutes default)
        self.lock_timeout = 300
        
        # Colors for users
        self.user_colors = [
            "#007bff", "#28a745", "#dc3545", "#ffc107", "#6f42c1",
            "#fd7e14", "#20c997", "#6c757d", "#e83e8c", "#17a2b8"
        ]
        self.color_index = 0
    
    async def initialize(self):
        """Initialize the collaboration manager."""
        await self._create_database_tables()
        
        # Start background tasks
        asyncio.create_task(self._cleanup_expired_locks())
        asyncio.create_task(self._cleanup_inactive_presence())
        
        print("Real-time collaboration manager initialized")
    
    async def _create_database_tables(self):
        """Create database tables for collaboration features."""
        try:
            async with self.db_pool.acquire() as conn:
                # Collaboration comments table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS collaboration_comments (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        display_name VARCHAR(255) NOT NULL,
                        resource_type VARCHAR(50) NOT NULL,
                        resource_id VARCHAR(255) NOT NULL,
                        element_id VARCHAR(255),
                        content TEXT NOT NULL,
                        position JSONB,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        is_resolved BOOLEAN DEFAULT FALSE,
                        thread_id VARCHAR(255)
                    )
                """)
                
                # Collaboration sessions table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS collaboration_sessions (
                        id VARCHAR(255) PRIMARY KEY,
                        resource_type VARCHAR(50) NOT NULL,
                        resource_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        started_at TIMESTAMP DEFAULT NOW(),
                        ended_at TIMESTAMP,
                        duration_seconds INTEGER,
                        events_count INTEGER DEFAULT 0
                    )
                """)
                
                # Create indexes
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_resource ON collaboration_comments(resource_type, resource_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_user ON collaboration_comments(user_id, created_at)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_resource ON collaboration_sessions(resource_type, resource_id)")
                
        except Exception as e:
            print(f"Error creating collaboration tables: {e}")
            raise
    
    async def connect_user(self, websocket: WebSocket, user_id: str, display_name: str, 
                          resource_type: str, resource_id: str) -> str:
        """Connect a user to a collaborative resource."""
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Create resource key
            resource_key = f"{resource_type}:{resource_id}"
            
            # Add connection to resource
            if resource_key not in self.resource_connections:
                self.resource_connections[resource_key] = set()
            self.resource_connections[resource_key].add(websocket)
            
            # Assign user color if not already assigned
            if user_id not in self.user_presence:
                color = self.user_colors[self.color_index % len(self.user_colors)]
                self.color_index += 1
            else:
                color = self.user_presence[user_id].color
            
            # Update user presence
            self.user_presence[user_id] = UserPresence(
                user_id=user_id,
                display_name=display_name,
                color=color,
                last_activity=datetime.utcnow()
            )
            
            # Notify other users of join
            await self._broadcast_event(
                resource_type, resource_id,
                CollaborationEvent(
                    event_type=CollaborationEventType.USER_JOIN,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    data={
                        "display_name": display_name,
                        "color": color,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ),
                exclude_user=user_id
            )
            
            # Send current presence to new user
            await self._send_current_presence(websocket, resource_type, resource_id)
            
            # Start collaboration session
            session_id = await self._start_collaboration_session(user_id, resource_type, resource_id)
            
            return session_id
            
        except Exception as e:
            print(f"Error connecting user: {e}")
            raise
    
    async def disconnect_user(self, websocket: WebSocket, user_id: str, 
                            resource_type: str, resource_id: str):
        """Disconnect a user from a collaborative resource."""
        try:
            resource_key = f"{resource_type}:{resource_id}"
            
            # Remove connection
            if resource_key in self.resource_connections:
                self.resource_connections[resource_key].discard(websocket)
                if not self.resource_connections[resource_key]:
                    del self.resource_connections[resource_key]
            
            # Remove user presence if no more connections
            if user_id in self.user_presence:
                del self.user_presence[user_id]
            
            # Release any locks held by user
            await self._release_user_locks(user_id)
            
            # Notify other users of leave
            await self._broadcast_event(
                resource_type, resource_id,
                CollaborationEvent(
                    event_type=CollaborationEventType.USER_LEAVE,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    data={"timestamp": datetime.utcnow().isoformat()}
                ),
                exclude_user=user_id
            )
            
            # End collaboration session
            await self._end_collaboration_session(user_id, resource_type, resource_id)
            
        except Exception as e:
            print(f"Error disconnecting user: {e}")
    
    async def handle_cursor_move(self, user_id: str, resource_type: str, resource_id: str,
                                cursor_data: Dict[str, Any]):
        """Handle cursor movement events."""
        try:
            # Update user presence
            if user_id in self.user_presence:
                self.user_presence[user_id].cursor_position = cursor_data
                self.user_presence[user_id].last_activity = datetime.utcnow()
            
            # Broadcast cursor movement
            await self._broadcast_event(
                resource_type, resource_id,
                CollaborationEvent(
                    event_type=CollaborationEventType.CURSOR_MOVE,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    data={
                        "cursor": cursor_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ),
                exclude_user=user_id
            )
            
        except Exception as e:
            print(f"Error handling cursor move: {e}")
    
    async def handle_element_selection(self, user_id: str, resource_type: str, resource_id: str,
                                     element_id: Optional[str]):
        """Handle element selection events."""
        try:
            # Update user presence
            if user_id in self.user_presence:
                self.user_presence[user_id].selected_element = element_id
                self.user_presence[user_id].last_activity = datetime.utcnow()
            
            # Broadcast element selection
            await self._broadcast_event(
                resource_type, resource_id,
                CollaborationEvent(
                    event_type=CollaborationEventType.ELEMENT_SELECT,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    data={
                        "element_id": element_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ),
                exclude_user=user_id
            )
            
        except Exception as e:
            print(f"Error handling element selection: {e}")
    
    async def lock_element(self, user_id: str, element_id: str, lock_type: str = "edit") -> bool:
        """Lock an element for exclusive editing."""
        try:
            # Check if element is already locked
            if element_id in self.element_locks:
                existing_lock = self.element_locks[element_id]
                if existing_lock.expires_at > datetime.utcnow():
                    return False  # Element is locked by another user
                else:
                    # Lock expired, remove it
                    del self.element_locks[element_id]
            
            # Create new lock
            lock = ElementLock(
                element_id=element_id,
                locked_by=user_id,
                locked_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=self.lock_timeout),
                lock_type=lock_type
            )
            
            self.element_locks[element_id] = lock
            return True
            
        except Exception as e:
            print(f"Error locking element: {e}")
            return False
    
    async def unlock_element(self, user_id: str, element_id: str) -> bool:
        """Unlock an element."""
        try:
            if element_id in self.element_locks:
                lock = self.element_locks[element_id]
                if lock.locked_by == user_id:
                    del self.element_locks[element_id]
                    return True
            return False
            
        except Exception as e:
            print(f"Error unlocking element: {e}")
            return False
    
    async def add_comment(self, user_id: str, display_name: str, resource_type: str,
                         resource_id: str, content: str, element_id: Optional[str] = None,
                         position: Optional[Dict[str, Any]] = None,
                         thread_id: Optional[str] = None) -> str:
        """Add a comment to a resource."""
        try:
            comment = Comment(
                user_id=user_id,
                display_name=display_name,
                resource_type=resource_type,
                resource_id=resource_id,
                element_id=element_id,
                content=content,
                position=position,
                thread_id=thread_id
            )
            
            # Save to database
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO collaboration_comments
                    (id, user_id, display_name, resource_type, resource_id, element_id,
                     content, position, created_at, updated_at, thread_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, comment.id, user_id, display_name, resource_type, resource_id,
                    element_id, content, json.dumps(position) if position else None,
                    comment.created_at, comment.updated_at, thread_id)
            
            # Broadcast comment addition
            await self._broadcast_event(
                resource_type, resource_id,
                CollaborationEvent(
                    event_type=CollaborationEventType.COMMENT_ADD,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    data={
                        "comment_id": comment.id,
                        "content": content,
                        "element_id": element_id,
                        "position": position,
                        "display_name": display_name,
                        "timestamp": comment.created_at.isoformat()
                    }
                )
            )
            
            return comment.id
            
        except Exception as e:
            print(f"Error adding comment: {e}")
            raise
    
    async def get_comments(self, resource_type: str, resource_id: str,
                          element_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get comments for a resource."""
        try:
            async with self.db_pool.acquire() as conn:
                if element_id:
                    comments = await conn.fetch("""
                        SELECT * FROM collaboration_comments
                        WHERE resource_type = $1 AND resource_id = $2 AND element_id = $3
                        AND is_resolved = FALSE
                        ORDER BY created_at ASC
                    """, resource_type, resource_id, element_id)
                else:
                    comments = await conn.fetch("""
                        SELECT * FROM collaboration_comments
                        WHERE resource_type = $1 AND resource_id = $2
                        AND is_resolved = FALSE
                        ORDER BY created_at ASC
                    """, resource_type, resource_id)
                
                return [
                    {
                        "id": comment["id"],
                        "user_id": comment["user_id"],
                        "display_name": comment["display_name"],
                        "content": comment["content"],
                        "element_id": comment["element_id"],
                        "position": json.loads(comment["position"]) if comment["position"] else None,
                        "created_at": comment["created_at"].isoformat(),
                        "updated_at": comment["updated_at"].isoformat(),
                        "thread_id": comment["thread_id"]
                    }
                    for comment in comments
                ]
                
        except Exception as e:
            print(f"Error getting comments: {e}")
            return []
    
    async def _broadcast_event(self, resource_type: str, resource_id: str,
                             event: CollaborationEvent, exclude_user: Optional[str] = None):
        """Broadcast an event to all connected users for a resource."""
        try:
            resource_key = f"{resource_type}:{resource_id}"
            if resource_key not in self.resource_connections:
                return
            
            event_data = {
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "data": event.data,
                "timestamp": event.timestamp.isoformat()
            }
            
            message = json.dumps(event_data)
            
            # Send to all connected clients
            for websocket in list(self.resource_connections[resource_key]):
                try:
                    # Skip sender if specified
                    if exclude_user and hasattr(websocket, 'user_id') and websocket.user_id == exclude_user:
                        continue
                    
                    await websocket.send_text(message)
                except Exception as e:
                    print(f"Error sending message to client: {e}")
                    # Remove disconnected websocket
                    self.resource_connections[resource_key].discard(websocket)
            
        except Exception as e:
            print(f"Error broadcasting event: {e}")
    
    async def _send_current_presence(self, websocket: WebSocket, resource_type: str, resource_id: str):
        """Send current user presence to a newly connected user."""
        try:
            presence_data = []
            
            for user_id, presence in self.user_presence.items():
                presence_data.append({
                    "user_id": user_id,
                    "display_name": presence.display_name,
                    "color": presence.color,
                    "cursor_position": presence.cursor_position,
                    "selected_element": presence.selected_element,
                    "status": presence.status,
                    "last_activity": presence.last_activity.isoformat()
                })
            
            message = json.dumps({
                "event_type": "initial_presence",
                "data": {"users": presence_data}
            })
            
            await websocket.send_text(message)
            
        except Exception as e:
            print(f"Error sending current presence: {e}")
    
    async def _release_user_locks(self, user_id: str):
        """Release all locks held by a user."""
        try:
            locks_to_remove = []
            for element_id, lock in self.element_locks.items():
                if lock.locked_by == user_id:
                    locks_to_remove.append(element_id)
            
            for element_id in locks_to_remove:
                del self.element_locks[element_id]
                
        except Exception as e:
            print(f"Error releasing user locks: {e}")
    
    async def _cleanup_expired_locks(self):
        """Background task to clean up expired locks."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                expired_locks = []
                
                for element_id, lock in self.element_locks.items():
                    if lock.expires_at <= current_time:
                        expired_locks.append(element_id)
                
                for element_id in expired_locks:
                    del self.element_locks[element_id]
                
            except Exception as e:
                print(f"Error cleaning up expired locks: {e}")
    
    async def _cleanup_inactive_presence(self):
        """Background task to clean up inactive user presence."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = datetime.utcnow()
                inactive_threshold = timedelta(minutes=10)
                
                inactive_users = []
                for user_id, presence in self.user_presence.items():
                    if current_time - presence.last_activity > inactive_threshold:
                        inactive_users.append(user_id)
                
                for user_id in inactive_users:
                    del self.user_presence[user_id]
                
            except Exception as e:
                print(f"Error cleaning up inactive presence: {e}")
    
    async def _start_collaboration_session(self, user_id: str, resource_type: str, resource_id: str) -> str:
        """Start a collaboration session."""
        try:
            session_id = str(uuid.uuid4())
            
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO collaboration_sessions
                    (id, resource_type, resource_id, user_id, started_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, session_id, resource_type, resource_id, user_id, datetime.utcnow())
            
            return session_id
            
        except Exception as e:
            print(f"Error starting collaboration session: {e}")
            return ""
    
    async def _end_collaboration_session(self, user_id: str, resource_type: str, resource_id: str):
        """End a collaboration session."""
        try:
            async with self.db_pool.acquire() as conn:
                # Find active session
                session = await conn.fetchrow("""
                    SELECT id, started_at FROM collaboration_sessions
                    WHERE user_id = $1 AND resource_type = $2 AND resource_id = $3
                    AND ended_at IS NULL
                    ORDER BY started_at DESC
                    LIMIT 1
                """, user_id, resource_type, resource_id)
                
                if session:
                    ended_at = datetime.utcnow()
                    duration = int((ended_at - session['started_at']).total_seconds())
                    
                    await conn.execute("""
                        UPDATE collaboration_sessions
                        SET ended_at = $1, duration_seconds = $2
                        WHERE id = $3
                    """, ended_at, duration, session['id'])
            
        except Exception as e:
            print(f"Error ending collaboration session: {e}")


# Global collaboration manager instance
_collaboration_manager: Optional[RealTimeCollaborationManager] = None


async def initialize_collaboration_manager(db_pool: asyncpg.Pool, redis_client: Optional[redis.Redis] = None):
    """Initialize the collaboration manager."""
    global _collaboration_manager
    _collaboration_manager = RealTimeCollaborationManager(db_pool, redis_client)
    await _collaboration_manager.initialize()


def get_collaboration_manager() -> Optional[RealTimeCollaborationManager]:
    """Get the global collaboration manager instance."""
    return _collaboration_manager


async def shutdown_collaboration_manager():
    """Shutdown the collaboration manager."""
    global _collaboration_manager
    if _collaboration_manager:
        # Disconnect all users
        for resource_key, connections in _collaboration_manager.resource_connections.items():
            for websocket in list(connections):
                try:
                    await websocket.close()
                except:
                    pass
        
        _collaboration_manager = None 