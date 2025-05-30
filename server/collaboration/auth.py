"""
Collaboration Authentication Integration

Provides JWT authentication for WebSocket connections using connectionParams pattern,
role-based access control, and integration with existing authentication system.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

import jwt
from fastapi import WebSocket, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .state import UserRole, SessionState
from ..auth import verify_token  # Import from existing auth system


logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Authentication-related errors"""
    pass


class AuthorizationError(Exception):
    """Authorization-related errors"""
    pass


@dataclass
class CollaborationUser:
    """Authenticated user for collaboration sessions"""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[str]
    session_expires_at: datetime
    is_active: bool = True


class CollaborationPermission(str, Enum):
    """Permissions for collaboration features"""
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    DELETE_MEMORY = "delete_memory"
    CREATE_SESSION = "create_session"
    JOIN_SESSION = "join_session"
    MANAGE_SESSION = "manage_session"
    RESOLVE_CONFLICTS = "resolve_conflicts"
    VIEW_ANALYTICS = "view_analytics"
    ADMIN_ACCESS = "admin_access"


class CollaborationAuthenticator:
    """
    Authentication and authorization for collaboration features.
    
    Features:
    - JWT token verification for WebSocket connections
    - ConnectionParams authentication (browser WebSocket limitation workaround)
    - Role-based access control
    - Session validation and renewal
    - Integration with existing authentication system
    """
    
    def __init__(
        self,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        token_expiry_hours: int = 24
    ):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expiry_hours = token_expiry_hours
        
        # Role-based permissions mapping
        self.role_permissions = {
            UserRole.OWNER: [
                CollaborationPermission.READ_MEMORY,
                CollaborationPermission.WRITE_MEMORY,
                CollaborationPermission.DELETE_MEMORY,
                CollaborationPermission.CREATE_SESSION,
                CollaborationPermission.JOIN_SESSION,
                CollaborationPermission.MANAGE_SESSION,
                CollaborationPermission.RESOLVE_CONFLICTS,
                CollaborationPermission.VIEW_ANALYTICS,
                CollaborationPermission.ADMIN_ACCESS
            ],
            UserRole.EDITOR: [
                CollaborationPermission.READ_MEMORY,
                CollaborationPermission.WRITE_MEMORY,
                CollaborationPermission.JOIN_SESSION,
                CollaborationPermission.RESOLVE_CONFLICTS,
                CollaborationPermission.VIEW_ANALYTICS
            ],
            UserRole.COLLABORATOR: [
                CollaborationPermission.READ_MEMORY,
                CollaborationPermission.WRITE_MEMORY,
                CollaborationPermission.JOIN_SESSION,
                CollaborationPermission.RESOLVE_CONFLICTS
            ],
            UserRole.VIEWER: [
                CollaborationPermission.READ_MEMORY,
                CollaborationPermission.JOIN_SESSION,
                CollaborationPermission.VIEW_ANALYTICS
            ]
        }
        
        # Active sessions cache
        self.active_sessions: Dict[str, CollaborationUser] = {}
        
        # Rate limiting
        self.auth_attempts: Dict[str, List[datetime]] = {}
        self.max_auth_attempts = 5
        self.auth_window_minutes = 15

    async def authenticate_websocket(
        self,
        websocket: WebSocket,
        connection_params: Optional[Dict[str, Any]] = None
    ) -> CollaborationUser:
        """
        Authenticate WebSocket connection using connectionParams.
        
        Args:
            websocket: WebSocket connection
            connection_params: Connection parameters from WebSocket handshake
            
        Returns:
            CollaborationUser: Authenticated user
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Extract authentication token from connectionParams
            if not connection_params:
                raise AuthenticationError("No connection parameters provided")
            
            token = connection_params.get("authToken")
            if not token:
                # Try alternative parameter names
                token = connection_params.get("authorization") or connection_params.get("token")
            
            if not token:
                raise AuthenticationError("No authentication token provided")
            
            # Remove Bearer prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Verify JWT token
            user = await self._verify_jwt_token(token)
            
            # Check rate limiting
            client_ip = self._get_client_ip(websocket)
            if not self._check_rate_limit(client_ip):
                raise AuthenticationError("Too many authentication attempts")
            
            # Store active session
            self.active_sessions[user.user_id] = user
            
            logger.info(f"Successfully authenticated user {user.username} ({user.user_id}) for WebSocket collaboration")
            return user
            
        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            if isinstance(e, (AuthenticationError, AuthorizationError)):
                raise
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def authenticate_http_request(
        self,
        authorization: Optional[HTTPAuthorizationCredentials] = None,
        token: Optional[str] = None
    ) -> CollaborationUser:
        """
        Authenticate HTTP request with JWT token.
        
        Args:
            authorization: HTTP authorization credentials
            token: Direct token string
            
        Returns:
            CollaborationUser: Authenticated user
        """
        try:
            auth_token = None
            
            if authorization:
                auth_token = authorization.credentials
            elif token:
                auth_token = token
            else:
                raise AuthenticationError("No authentication credentials provided")
            
            # Verify JWT token
            user = await self._verify_jwt_token(auth_token)
            
            return user
            
        except Exception as e:
            logger.error(f"HTTP authentication failed: {e}")
            if isinstance(e, (AuthenticationError, AuthorizationError)):
                raise
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def _verify_jwt_token(self, token: str) -> CollaborationUser:
        """Verify JWT token and create CollaborationUser"""
        try:
            # Use existing auth system for initial verification
            token_data = verify_token(token)
            if not token_data:
                raise AuthenticationError("Invalid token")
            
            # Extract user information from TokenData
            username = token_data.username
            user_id = username  # Use username as user_id for now
            email = f"{username}@example.com"  # Default email
            scopes = token_data.scopes or []
            
            if not user_id or not username:
                raise AuthenticationError("Token missing required user information")
            
            # Determine role from scopes
            role = UserRole.COLLABORATOR  # Default role
            if "admin" in scopes:
                role = UserRole.OWNER
            elif "write" in scopes:
                role = UserRole.EDITOR
            elif "read" in scopes:
                role = UserRole.VIEWER
            
            # Get user permissions
            permissions = self._get_user_permissions(role)
            
            # Create session expiry
            session_expires_at = datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours)
            
            return CollaborationUser(
                user_id=user_id,
                username=username,
                email=email,
                role=role,
                permissions=[p.value for p in permissions],
                session_expires_at=session_expires_at,
                is_active=True
            )
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise AuthenticationError(f"Token verification failed: {str(e)}")

    def _get_user_permissions(self, role: UserRole) -> List[CollaborationPermission]:
        """Get permissions for a user role"""
        return self.role_permissions.get(role, [])

    def check_permission(
        self,
        user: CollaborationUser,
        permission: CollaborationPermission
    ) -> bool:
        """Check if user has specific permission"""
        return permission.value in user.permissions

    def require_permission(
        self,
        user: CollaborationUser,
        permission: CollaborationPermission
    ) -> None:
        """Require user to have specific permission"""
        if not self.check_permission(user, permission):
            raise AuthorizationError(f"User {user.username} lacks permission: {permission.value}")

    def check_session_access(
        self,
        user: CollaborationUser,
        resource_type: str,
        resource_id: str,
        action: str
    ) -> bool:
        """Check if user can access a specific collaboration session"""
        # Basic permission checks
        if action == "read":
            return self.check_permission(user, CollaborationPermission.READ_MEMORY)
        elif action == "write":
            return self.check_permission(user, CollaborationPermission.WRITE_MEMORY)
        elif action == "delete":
            return self.check_permission(user, CollaborationPermission.DELETE_MEMORY)
        elif action == "manage":
            return self.check_permission(user, CollaborationPermission.MANAGE_SESSION)
        
        # Default to read permission
        return self.check_permission(user, CollaborationPermission.READ_MEMORY)

    def _get_client_ip(self, websocket: WebSocket) -> str:
        """Extract client IP from WebSocket connection"""
        # Try to get real IP from headers (proxy support)
        forwarded_for = websocket.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = websocket.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client IP
        if hasattr(websocket, "client") and websocket.client:
            return websocket.client.host
        
        return "unknown"

    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client IP is within rate limits"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.auth_window_minutes)
        
        # Clean old attempts
        if client_ip in self.auth_attempts:
            self.auth_attempts[client_ip] = [
                attempt for attempt in self.auth_attempts[client_ip]
                if attempt > cutoff
            ]
        else:
            self.auth_attempts[client_ip] = []
        
        # Check current attempt count
        if len(self.auth_attempts[client_ip]) >= self.max_auth_attempts:
            return False
        
        # Record this attempt
        self.auth_attempts[client_ip].append(now)
        return True

    async def refresh_session(self, user_id: str) -> Optional[CollaborationUser]:
        """Refresh user session if valid"""
        if user_id not in self.active_sessions:
            return None
        
        user = self.active_sessions[user_id]
        
        # Check if session has expired
        if user.session_expires_at < datetime.now(timezone.utc):
            del self.active_sessions[user_id]
            return None
        
        # Extend session
        user.session_expires_at = datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours)
        return user

    async def invalidate_session(self, user_id: str) -> bool:
        """Invalidate user session"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            logger.info(f"Invalidated session for user {user_id}")
            return True
        return False

    def get_active_user(self, user_id: str) -> Optional[CollaborationUser]:
        """Get active user by ID"""
        return self.active_sessions.get(user_id)

    def get_session_metrics(self) -> Dict[str, Any]:
        """Get authentication metrics"""
        now = datetime.now(timezone.utc)
        active_count = len(self.active_sessions)
        
        # Count sessions by role
        role_counts = {}
        expired_count = 0
        
        for user in self.active_sessions.values():
            role_counts[user.role.value] = role_counts.get(user.role.value, 0) + 1
            if user.session_expires_at < now:
                expired_count += 1
        
        return {
            "active_sessions": active_count,
            "expired_sessions": expired_count,
            "sessions_by_role": role_counts,
            "total_auth_attempts": sum(len(attempts) for attempts in self.auth_attempts.values()),
            "rate_limited_ips": len([
                ip for ip, attempts in self.auth_attempts.items()
                if len(attempts) >= self.max_auth_attempts
            ])
        }

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        now = datetime.now(timezone.utc)
        expired_users = [
            user_id for user_id, user in self.active_sessions.items()
            if user.session_expires_at < now
        ]
        
        for user_id in expired_users:
            del self.active_sessions[user_id]
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired sessions")
        
        return len(expired_users) 