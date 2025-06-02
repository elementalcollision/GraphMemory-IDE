"""
Collaboration Middleware

Provides authentication and authorization middleware for WebSocket connections
and GraphQL subscriptions with rate limiting and security features.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Awaitable
from functools import wraps

from fastapi import WebSocket, HTTPException, status
from fastapi.websockets import WebSocketDisconnect
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .auth import CollaborationAuthenticator, CollaborationUser, AuthenticationError, AuthorizationError
from .state import UserRole


logger = logging.getLogger(__name__)


class WebSocketAuthenticationMiddleware:
    """
    WebSocket authentication middleware for collaboration features.
    
    Handles:
    - ConnectionParams authentication for WebSocket connections
    - Session validation and renewal
    - Rate limiting per connection
    - Error handling and logging
    """
    
    def __init__(self, authenticator: CollaborationAuthenticator) -> None:
        self.authenticator = authenticator
        self.connection_registry: Dict[str, Dict[str, Any]] = {}
        
        # Rate limiting
        self.connection_limits = {
            UserRole.OWNER: 10,      # 10 connections per user
            UserRole.EDITOR: 5,      # 5 connections per user  
            UserRole.COLLABORATOR: 3, # 3 connections per user
            UserRole.VIEWER: 1       # 1 connection per user
        }

    async def authenticate_connection(
        self,
        websocket: WebSocket,
        connection_params: Optional[Dict[str, Any]] = None
    ) -> CollaborationUser:
        """
        Authenticate WebSocket connection and register it.
        
        Args:
            websocket: WebSocket connection
            connection_params: Connection parameters from client
            
        Returns:
            CollaborationUser: Authenticated user
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Authenticate user
            user = await self.authenticator.authenticate_websocket(
                websocket, connection_params
            )
            
            # Check connection limits
            if not self._check_connection_limit(user):
                raise AuthenticationError(f"Connection limit exceeded for role {user.role.value}")
            
            # Register connection
            connection_id = self._generate_connection_id(websocket)
            self._register_connection(connection_id, user, websocket)
            
            logger.info(f"WebSocket connection authenticated for user {user.username} ({connection_id})")
            return user
            
        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise

    async def handle_connection_lifecycle(
        self,
        websocket: WebSocket,
        user: CollaborationUser,
        handler: Callable[[WebSocket, CollaborationUser], Awaitable[None]]
    ) -> None:
        """
        Handle the complete lifecycle of a WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            user: Authenticated user
            handler: Connection handler function
        """
        connection_id = self._generate_connection_id(websocket)
        
        try:
            # Set up heartbeat
            heartbeat_task = asyncio.create_task(
                self._heartbeat_handler(connection_id, user)
            )
            
            # Run the main handler
            await handler(websocket, user)
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user.username} ({connection_id})")
        except Exception as e:
            logger.error(f"WebSocket error for user {user.username}: {e}")
        finally:
            # Clean up
            heartbeat_task.cancel()
            self._unregister_connection(connection_id)
            try:
                await websocket.close()
            except:
                pass

    def _check_connection_limit(self, user: CollaborationUser) -> bool:
        """Check if user is within connection limits"""
        user_connections = self._get_user_connections(user.user_id)
        limit = self.connection_limits.get(user.role, 1)
        return len(user_connections) < limit

    def _get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user"""
        return [
            conn_id for conn_id, conn_data in self.connection_registry.items()
            if conn_data["user_id"] == user_id
        ]

    def _generate_connection_id(self, websocket: WebSocket) -> str:
        """Generate unique connection ID"""
        client_info = "unknown"
        if hasattr(websocket, "client") and websocket.client:
            client_info = f"{websocket.client.host}:{websocket.client.port}"
        
        return f"ws_{client_info}_{int(datetime.now(timezone.utc).timestamp())}"

    def _register_connection(
        self,
        connection_id: str,
        user: CollaborationUser,
        websocket: WebSocket
    ) -> None:
        """Register a WebSocket connection"""
        self.connection_registry[connection_id] = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "websocket": websocket,
            "connected_at": datetime.now(timezone.utc),
            "last_heartbeat": datetime.now(timezone.utc),
            "is_active": True
        }

    def _unregister_connection(self, connection_id: str) -> None:
        """Unregister a WebSocket connection"""
        if connection_id in self.connection_registry:
            del self.connection_registry[connection_id]

    async def _heartbeat_handler(self, connection_id: str, user: CollaborationUser) -> None:
        """Handle heartbeat for connection health monitoring"""
        while connection_id in self.connection_registry:
            try:
                # Update last heartbeat
                if connection_id in self.connection_registry:
                    self.connection_registry[connection_id]["last_heartbeat"] = datetime.now(timezone.utc)
                
                # Refresh user session
                refreshed_user = await self.authenticator.refresh_session(user.user_id)
                if not refreshed_user:
                    logger.warning(f"Session expired for user {user.username}, closing connection")
                    websocket = self.connection_registry[connection_id]["websocket"]
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    break
                
                # Wait for next heartbeat
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Heartbeat error for connection {connection_id}: {e}")
                break

    def get_connection_metrics(self) -> Dict[str, Any]:
        """Get connection metrics"""
        now = datetime.now(timezone.utc)
        active_connections = len(self.connection_registry)
        
        # Count by role
        role_counts = {}
        total_duration = 0.0
        
        for conn_data in self.connection_registry.values():
            role = conn_data["role"].value
            role_counts[role] = role_counts.get(role, 0) + 1
            
            duration = (now - conn_data["connected_at"]).total_seconds()
            total_duration += duration
        
        avg_duration = total_duration / active_connections if active_connections > 0 else 0
        
        return {
            "active_connections": active_connections,
            "connections_by_role": role_counts,
            "average_connection_duration": avg_duration
        }


class CollaborationRateLimitMiddleware(BaseHTTPMiddleware):
    """
    HTTP rate limiting middleware for collaboration API endpoints.
    """
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts: Dict[str, List[datetime]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting"""
        
        # Skip rate limiting for non-collaboration paths
        if not request.url.path.startswith("/collaboration"):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_id):
            return Response(
                content=json.dumps({"error": "Rate limit exceeded"}),
                status_code=429,
                media_type="application/json"
            )
        
        # Process request
        return await call_next(request)

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from authorization header
        auth_header = request.headers.get("authorization")
        if auth_header:
            return f"user_{hash(auth_header) % 10000}"
        
        # Fallback to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        if client_id in self.request_counts:
            self.request_counts[client_id] = [
                req_time for req_time in self.request_counts[client_id]
                if req_time > cutoff
            ]
        else:
            self.request_counts[client_id] = []
        
        # Check current request count
        if len(self.request_counts[client_id]) >= self.max_requests:
            return False
        
        # Record this request
        self.request_counts[client_id].append(now)
        return True


def require_collaboration_permission(permission: str) -> None:
    """
    Decorator to require specific collaboration permission for WebSocket handlers.
    
    Args:
        permission: Required permission string
        
    Returns:
        Decorator function
    """
    def decorator(handler_func: Callable) -> None:
        @wraps(handler_func)
        async def wrapper(websocket: WebSocket, user: CollaborationUser, *args, **kwargs) -> None:
            # Check permission
            if permission not in user.permissions:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"Missing permission: {permission}"
                )
                raise AuthorizationError(f"User {user.username} lacks permission: {permission}")
            
            return await handler_func(websocket, user, *args, **kwargs)
        
        return wrapper
    return decorator


def collaboration_session_access(resource_type: str, action: str = "read") -> None:
    """
    Decorator to check collaboration session access.
    
    Args:
        resource_type: Type of resource (memory, graph, workspace)
        action: Action being performed (read, write, delete, manage)
        
    Returns:
        Decorator function
    """
    def decorator(handler_func: Callable) -> None:
        @wraps(handler_func)
        async def wrapper(websocket: WebSocket, user: CollaborationUser, resource_id: str, *args, **kwargs) -> None:
            # Note: This would integrate with a proper resource access control system
            # For now, we'll use basic permission checking
            
            if action == "write" and "write_memory" not in user.permissions:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"No write access to {resource_type}"
                )
                raise AuthorizationError(f"No write access to {resource_type}")
            elif action == "read" and "read_memory" not in user.permissions:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"No read access to {resource_type}"
                )
                raise AuthorizationError(f"No read access to {resource_type}")
            
            return await handler_func(websocket, user, resource_id, *args, **kwargs)
        
        return wrapper
    return decorator 