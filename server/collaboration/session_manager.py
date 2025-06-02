"""
Collaboration Session Manager

Manages the lifecycle of collaborative editing sessions including
creation, persistence, cleanup, and cross-server coordination.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4
import redis.asyncio as redis

from .state import CollaborationState, SessionState, UserRole


logger = logging.getLogger(__name__)


class CollaborationSession:
    """
    Wrapper around CollaborationState that provides session management
    functionality including persistence and lifecycle management.
    """

    def __init__(self, state: CollaborationState, redis_client: redis.Redis[bytes]) -> None:
        self.state = state
        self.redis = redis_client
        self._session_key = f"collaboration:session:{state.session_id}"
        self._last_persisted = datetime.now(timezone.utc)
        self._dirty = False

    @property
    def session_id(self) -> str:
        return self.state.session_id

    @property
    def resource_type(self) -> str:
        return self.state.resource_type

    @property
    def resource_id(self) -> str:
        return self.state.resource_id

    @property
    def users(self) -> Dict[str, Any]:
        return self.state.users

    async def add_user(self, user_id: str, username: str, role: UserRole = UserRole.COLLABORATOR) -> None:
        """Add a user to the session"""
        presence = await self.state.add_user(user_id, username, role)
        self._mark_dirty()
        await self._persist_if_needed()
        return presence

    async def remove_user(self, user_id: str) -> bool:
        """Remove a user from the session"""
        success = await self.state.remove_user(user_id)
        if success:
            self._mark_dirty()
            await self._persist_if_needed()
        return success

    async def update_user_activity(self, user_id: str, activity_type, cursor_position=None, selection=None) -> None:
        """Update user activity"""
        success = await self.state.update_user_activity(user_id, activity_type, cursor_position, selection)
        if success:
            self._mark_dirty()
        return success

    async def get_active_users(self) -> None:
        """Get active users in the session"""
        return await self.state.get_active_users()

    async def register_operation(self, operation_id: str) -> int:
        """Register a new operation"""
        sequence_number = await self.state.register_operation(operation_id)
        self._mark_dirty()
        await self._persist_if_needed()
        return sequence_number

    async def commit_operation(self, operation_id: str) -> bool:
        """Commit an operation"""
        success = await self.state.commit_operation(operation_id)
        if success:
            self._mark_dirty()
            await self._persist_if_needed()
        return success

    async def register_conflict(self, conflict_id: str, conflict_data: Dict[str, Any]) -> None:
        """Register a conflict"""
        await self.state.register_conflict(conflict_id, conflict_data)
        self._mark_dirty()
        await self._persist_if_needed()

    async def resolve_conflict(self, conflict_id: str, resolution_data: Dict[str, Any]) -> bool:
        """Resolve a conflict"""
        success = await self.state.resolve_conflict(conflict_id, resolution_data)
        if success:
            self._mark_dirty()
            await self._persist_if_needed()
        return success

    async def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return await self.state.get_session_summary()

    def _mark_dirty(self) -> None:
        """Mark session as needing persistence"""
        self._dirty = True

    async def _persist_if_needed(self, force: bool = False) -> None:
        """Persist session state if needed"""
        now = datetime.now(timezone.utc)
        
        # Persist if dirty and enough time has passed, or if forced
        if (self._dirty and (now - self._last_persisted).total_seconds() > 1.0) or force:
            await self._persist()

    async def _persist(self, force: bool = False) -> None:
        """Persist session state to Redis"""
        try:
            state_data = self.state.to_dict()
            await self.redis.set(
                self._session_key,
                json.dumps(state_data),
                ex=3600  # Expire after 1 hour of inactivity
            )
            self._last_persisted = datetime.now(timezone.utc)
            self._dirty = False
            
        except Exception as e:
            logger.error(f"Failed to persist session {self.session_id}: {e}")

    async def cleanup(self) -> None:
        """Clean up session resources"""
        try:
            await self.redis.delete(self._session_key)
        except Exception as e:
            logger.error(f"Failed to cleanup session {self.session_id}: {e}")


class SessionManager:
    """
    Manages collaborative editing sessions including creation, persistence,
    lifecycle management, and cleanup operations.
    """

    def __init__(self, redis_client: redis.Redis[bytes]) -> None:
        self.redis = redis_client
        self._sessions: Dict[str, CollaborationSession] = {}
        self._resource_to_session: Dict[str, str] = {}  # Maps resource_type:resource_id -> session_id
        self._cleanup_interval = 300  # 5 minutes
        self._session_timeout = 3600  # 1 hour
        self._locks: Dict[str, asyncio.Lock] = {}

    async def get_or_create_session(
        self,
        resource_type: str,
        resource_id: str,
        session_id: Optional[str] = None
    ) -> CollaborationSession:
        """
        Get an existing session or create a new one for the given resource.
        
        Args:
            resource_type: Type of resource ('memory', 'graph', 'workspace')
            resource_id: Unique identifier for the resource
            session_id: Optional specific session ID to use
            
        Returns:
            CollaborationSession: The session for the resource
        """
        resource_key = f"{resource_type}:{resource_id}"
        
        # Use lock to prevent race conditions
        if resource_key not in self._locks:
            self._locks[resource_key] = asyncio.Lock()
        
        async with self._locks[resource_key]:
            # Check if session already exists for this resource
            if resource_key in self._resource_to_session:
                existing_session_id = self._resource_to_session[resource_key]
                if existing_session_id in self._sessions:
                    return self._sessions[existing_session_id]
            
            # Try to restore from Redis if session_id provided
            if session_id:
                session = await self._restore_session(session_id)
                if session:
                    self._sessions[session_id] = session
                    self._resource_to_session[resource_key] = session_id
                    return session
            
            # Create new session
            if not session_id:
                session_id = str(uuid4())
            
            state = CollaborationState(session_id, resource_type, resource_id)
            state.state = SessionState.ACTIVE
            
            session = CollaborationSession(state, self.redis)
            
            # Store in memory and Redis
            self._sessions[session_id] = session
            self._resource_to_session[resource_key] = session_id
            await session._persist()
            
            logger.info(f"Created new collaboration session {session_id} for {resource_key}")
            return session

    async def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get a session by ID"""
        if session_id in self._sessions:
            return self._sessions[session_id]
        
        # Try to restore from Redis
        session = await self._restore_session(session_id)
        if session:
            self._sessions[session_id] = session
            resource_key = f"{session.resource_type}:{session.resource_id}"
            self._resource_to_session[resource_key] = session_id
        
        return session

    async def get_session_by_resource(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[CollaborationSession]:
        """Get a session by resource type and ID"""
        resource_key = f"{resource_type}:{resource_id}"
        
        if resource_key in self._resource_to_session:
            session_id = self._resource_to_session[resource_key]
            return await self.get_session(session_id)
        
        return None

    async def list_sessions(
        self,
        resource_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List sessions with optional filtering"""
        sessions = []
        
        for session in self._sessions.values():
            if resource_type and session.resource_type != resource_type:
                continue
            
            if active_only and session.state.state != SessionState.ACTIVE:
                continue
            
            summary = await session.get_session_summary()
            sessions.append(summary)
        
        return sessions

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions a user is participating in"""
        user_sessions = []
        
        for session in self._sessions.values():
            if user_id in session.users and session.users[user_id].is_active:
                summary = await session.get_session_summary()
                user_sessions.append(summary)
        
        return user_sessions

    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a session and clean up resources"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            # Mark session as terminated
            session.state.state = SessionState.TERMINATED
            await session._persist(force=True)
            
            # Remove from memory
            if session_id in self._sessions:
                del self._sessions[session_id]
            
            # Remove resource mapping
            resource_key = f"{session.resource_type}:{session.resource_id}"
            if resource_key in self._resource_to_session:
                del self._resource_to_session[resource_key]
            
            # Cleanup Redis data
            await session.cleanup()
            
            logger.info(f"Terminated session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            return False

    async def cleanup_idle_sessions(self) -> int:
        """Clean up idle and expired sessions"""
        cleaned_count = 0
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(seconds=self._session_timeout)
        
        sessions_to_cleanup = []
        
        for session_id, session in self._sessions.items():
            # Check if session is idle (no active users and old)
            active_users = await session.get_active_users()
            if (len(active_users) == 0 and 
                session.state.last_updated < cutoff_time):
                sessions_to_cleanup.append(session_id)
        
        # Clean up identified sessions
        for session_id in sessions_to_cleanup:
            if await self.terminate_session(session_id):
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} idle sessions")
        
        return cleaned_count

    async def get_active_session_count(self) -> int:
        """Get the number of active sessions"""
        count = 0
        for session in self._sessions.values():
            if session.state.state == SessionState.ACTIVE:
                active_users = await session.get_active_users()
                if len(active_users) > 0:
                    count += 1
        return count

    async def get_total_active_users(self) -> int:
        """Get the total number of active users across all sessions"""
        total_users = set()
        
        for session in self._sessions.values():
            active_users = await session.get_active_users()
            for user in active_users:
                total_users.add(user.user_id)
        
        return len(total_users)

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide collaboration metrics"""
        total_sessions = len(self._sessions)
        active_sessions = await self.get_active_session_count()
        total_users = await self.get_total_active_users()
        
        # Calculate operation metrics
        total_operations = 0
        total_conflicts = 0
        
        for session in self._sessions.values():
            total_operations += session.state.metrics.total_operations
            total_conflicts += session.state.metrics.conflicts_resolved
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_active_users": total_users,
            "total_operations": total_operations,
            "total_conflicts_resolved": total_conflicts,
            "conflict_rate": total_conflicts / total_operations if total_operations > 0 else 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _restore_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Restore a session from Redis"""
        try:
            session_key = f"collaboration:session:{session_id}"
            data = await self.redis.get(session_key)
            
            if not data:
                return None
            
            state_data = json.loads(data)
            state = CollaborationState.from_dict(state_data)
            
            session = CollaborationSession(state, self.redis)
            logger.info(f"Restored session {session_id} from Redis")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to restore session {session_id}: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown the session manager and persist all sessions"""
        logger.info("Shutting down session manager")
        
        # Persist all active sessions
        for session in self._sessions.values():
            try:
                await session._persist(force=True)
            except Exception as e:
                logger.error(f"Error persisting session {session.session_id} during shutdown: {e}")
        
        # Clear in-memory state
        self._sessions.clear()
        self._resource_to_session.clear()
        self._locks.clear()
        
        logger.info("Session manager shutdown complete") 