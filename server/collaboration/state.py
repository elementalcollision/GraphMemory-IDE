"""
Collaboration State Management

Manages the state of collaborative editing sessions, user presence,
and real-time synchronization for GraphMemory-IDE.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from uuid import UUID, uuid4
import json
import asyncio
from pydantic import BaseModel


class SessionState(str, Enum):
    """Session lifecycle states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"


class UserRole(str, Enum):
    """User roles in collaborative sessions"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    COLLABORATOR = "collaborator"


class ActivityType(str, Enum):
    """Types of collaborative activities"""
    MEMORY_EDIT = "memory_edit"
    GRAPH_EDIT = "graph_edit"
    NODE_CREATE = "node_create"
    RELATIONSHIP_CREATE = "relationship_create"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    COMMENT_ADD = "comment_add"
    TAG_UPDATE = "tag_update"


@dataclass
class UserPresence:
    """Represents a user's presence in a collaboration session"""
    user_id: str
    username: str
    role: UserRole
    session_id: str
    joined_at: datetime
    last_activity: datetime
    is_active: bool = True
    current_activity: Optional[ActivityType] = None
    cursor_position: Optional[Dict[str, Any]] = None
    selection: Optional[Dict[str, Any]] = None
    color: str = "#007acc"  # User color for UI

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "session_id": self.session_id,
            "joined_at": self.joined_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active,
            "current_activity": self.current_activity.value if self.current_activity else None,
            "cursor_position": self.cursor_position,
            "selection": self.selection,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPresence":
        """Create from dictionary"""
        # Handle role conversion
        role = data["role"]
        if isinstance(role, str):
            role = UserRole(role)
        
        # Handle activity type conversion
        current_activity = data.get("current_activity")
        if current_activity and isinstance(current_activity, str):
            current_activity = ActivityType(current_activity)
        
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            role=role,
            session_id=data["session_id"],
            joined_at=datetime.fromisoformat(data["joined_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            is_active=data.get("is_active", True),
            current_activity=current_activity,
            cursor_position=data.get("cursor_position"),
            selection=data.get("selection"),
            color=data.get("color", "#007acc")
        )


@dataclass
class CollaborationMetrics:
    """Real-time metrics for collaboration sessions"""
    total_operations: int = 0
    conflicts_resolved: int = 0
    active_users: int = 0
    session_duration: float = 0.0
    last_operation_time: Optional[datetime] = None
    operations_per_minute: float = 0.0
    conflict_rate: float = 0.0

    def update_operation_metrics(self) -> None:
        """Update operation-based metrics"""
        now = datetime.now(timezone.utc)
        if self.last_operation_time:
            time_diff = (now - self.last_operation_time).total_seconds() / 60.0
            if time_diff > 0:
                self.operations_per_minute = self.total_operations / time_diff
        
        self.last_operation_time = now
        
        if self.total_operations > 0:
            self.conflict_rate = self.conflicts_resolved / self.total_operations


class CollaborationState:
    """
    Central state manager for collaborative editing sessions.
    
    Manages user presence, session state, operation history,
    and real-time synchronization state.
    """

    def __init__(self, session_id: str, resource_type: str, resource_id: str) -> None:
        self.session_id = session_id
        self.resource_type = resource_type  # 'memory', 'graph', 'workspace'
        self.resource_id = resource_id
        self.state = SessionState.INITIALIZING
        self.created_at = datetime.now(timezone.utc)
        self.last_updated = self.created_at
        
        # User management
        self.users: Dict[str, UserPresence] = {}
        self.user_colors: Dict[str, str] = {}
        self._available_colors = [
            "#007acc", "#f44336", "#4caf50", "#ff9800", 
            "#9c27b0", "#2196f3", "#e91e63", "#795548"
        ]
        self._color_index = 0
        
        # Operation tracking
        self.operation_count = 0
        self.last_operation_id = 0
        self.pending_operations: List[str] = []
        self.committed_operations: List[str] = []
        
        # Conflict resolution
        self.active_conflicts: Dict[str, Any] = {}
        self.conflict_history: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.metrics = CollaborationMetrics()
        
        # Locks for thread safety
        self._state_lock = asyncio.Lock()
        self._user_lock = asyncio.Lock()

    async def add_user(self, user_id: str, username: str, role: UserRole = UserRole.COLLABORATOR) -> UserPresence:
        """Add a user to the collaboration session"""
        async with self._user_lock:
            if user_id in self.users:
                # Update existing user
                self.users[user_id].is_active = True
                self.users[user_id].last_activity = datetime.now(timezone.utc)
                return self.users[user_id]
            
            # Assign color
            if user_id not in self.user_colors:
                self.user_colors[user_id] = self._available_colors[self._color_index % len(self._available_colors)]
                self._color_index += 1
            
            # Create new user presence
            presence = UserPresence(
                user_id=user_id,
                username=username,
                role=role,
                session_id=self.session_id,
                joined_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                color=self.user_colors[user_id]
            )
            
            self.users[user_id] = presence
            self.metrics.active_users = len([u for u in self.users.values() if u.is_active])
            self._update_session_state()
            
            return presence

    async def remove_user(self, user_id: str) -> bool:
        """Remove a user from the collaboration session"""
        async with self._user_lock:
            if user_id in self.users:
                self.users[user_id].is_active = False
                self.metrics.active_users = len([u for u in self.users.values() if u.is_active])
                self._update_session_state()
                return True
            return False

    async def update_user_activity(
        self, 
        user_id: str, 
        activity_type: ActivityType,
        cursor_position: Optional[Dict[str, Any]] = None,
        selection: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update user activity and presence"""
        async with self._user_lock:
            if user_id in self.users:
                user = self.users[user_id]
                user.last_activity = datetime.now(timezone.utc)
                user.current_activity = activity_type
                if cursor_position:
                    user.cursor_position = cursor_position
                if selection:
                    user.selection = selection
                return True
            return False

    async def get_active_users(self) -> List[UserPresence]:
        """Get all active users in the session"""
        return [user for user in self.users.values() if user.is_active]

    async def register_operation(self, operation_id: str) -> int:
        """Register a new operation and return operation sequence number"""
        async with self._state_lock:
            self.operation_count += 1
            self.last_operation_id = self.operation_count
            self.pending_operations.append(operation_id)
            self.metrics.total_operations += 1
            self.metrics.update_operation_metrics()
            self._update_session_state()
            return self.operation_count

    async def commit_operation(self, operation_id: str) -> bool:
        """Mark an operation as committed"""
        async with self._state_lock:
            if operation_id in self.pending_operations:
                self.pending_operations.remove(operation_id)
                self.committed_operations.append(operation_id)
                return True
            return False

    async def register_conflict(self, conflict_id: str, conflict_data: Dict[str, Any]) -> None:
        """Register a conflict for resolution"""
        async with self._state_lock:
            self.active_conflicts[conflict_id] = {
                **conflict_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending"
            }

    async def resolve_conflict(self, conflict_id: str, resolution_data: Dict[str, Any]) -> bool:
        """Mark a conflict as resolved"""
        async with self._state_lock:
            if conflict_id in self.active_conflicts:
                conflict = self.active_conflicts.pop(conflict_id)
                conflict["status"] = "resolved"
                conflict["resolved_at"] = datetime.now(timezone.utc).isoformat()
                conflict["resolution"] = resolution_data
                self.conflict_history.append(conflict)
                self.metrics.conflicts_resolved += 1
                self.metrics.update_operation_metrics()
                return True
            return False

    def _update_session_state(self) -> None:
        """Update session state based on current conditions"""
        self.last_updated = datetime.now(timezone.utc)
        active_user_count = len([u for u in self.users.values() if u.is_active])
        
        if active_user_count == 0:
            self.state = SessionState.IDLE
        elif len(self.pending_operations) > 0 or len(self.active_conflicts) > 0:
            self.state = SessionState.ACTIVE
        else:
            self.state = SessionState.ACTIVE if active_user_count > 0 else SessionState.IDLE

    async def get_session_summary(self) -> Dict[str, Any]:
        """Get complete session state summary"""
        active_users = await self.get_active_users()
        
        return {
            "session_id": self.session_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "active_users": [user.to_dict() for user in active_users],
            "total_users": len(self.users),
            "operation_count": self.operation_count,
            "pending_operations": len(self.pending_operations),
            "active_conflicts": len(self.active_conflicts),
            "metrics": {
                "total_operations": self.metrics.total_operations,
                "conflicts_resolved": self.metrics.conflicts_resolved,
                "active_users": self.metrics.active_users,
                "operations_per_minute": self.metrics.operations_per_minute,
                "conflict_rate": self.metrics.conflict_rate
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for persistence"""
        return {
            "session_id": self.session_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "users": {uid: user.to_dict() for uid, user in self.users.items()},
            "operation_count": self.operation_count,
            "last_operation_id": self.last_operation_id,
            "pending_operations": self.pending_operations,
            "committed_operations": self.committed_operations,
            "active_conflicts": self.active_conflicts,
            "conflict_history": self.conflict_history,
            "user_colors": self.user_colors,
            "color_index": self._color_index
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationState":
        """Restore state from serialized data"""
        instance = cls(
            session_id=data["session_id"],
            resource_type=data["resource_type"],
            resource_id=data["resource_id"]
        )
        
        instance.state = SessionState(data["state"]) if isinstance(data["state"], str) else data["state"]
        instance.created_at = datetime.fromisoformat(data["created_at"])
        instance.last_updated = datetime.fromisoformat(data["last_updated"])
        
        # Restore users
        instance.users = {
            uid: UserPresence.from_dict(user_data) 
            for uid, user_data in data.get("users", {}).items()
        }
        
        # Restore operation tracking
        instance.operation_count = data.get("operation_count", 0)
        instance.last_operation_id = data.get("last_operation_id", 0)
        instance.pending_operations = data.get("pending_operations", [])
        instance.committed_operations = data.get("committed_operations", [])
        
        # Restore conflicts
        instance.active_conflicts = data.get("active_conflicts", {})
        instance.conflict_history = data.get("conflict_history", [])
        
        # Restore UI state
        instance.user_colors = data.get("user_colors", {})
        instance._color_index = data.get("color_index", 0)
        
        # Update metrics
        instance.metrics.active_users = len([u for u in instance.users.values() if u.is_active])
        instance.metrics.total_operations = len(instance.committed_operations) + len(instance.pending_operations)
        
        return instance 