"""
GraphMemory-IDE Multi-User Collaboration Platform

A comprehensive real-time collaboration system for AI-powered knowledge management
with operational transformation, conflict resolution, and enterprise-grade features.

Version: 1.2.0 (Phase 1.2 - Authentication Integration Complete)
"""

__version__ = "1.2.0"

# Core collaboration infrastructure
from .state import (
    CollaborationState,
    UserPresence,
    CollaborationMetrics,
    SessionState,
    UserRole,
    ActivityType
)

from .engine import CollaborationEngine
from .session_manager import SessionManager
from .operational_transform import (
    OperationalTransform,
    Operation,
    TransformResult,
    OperationType,
    OperationTarget
)

# Advanced conflict resolution
from .conflict_resolution import (
    ConflictResolver,
    ConflictContext,
    ConflictResolution,
    ConflictType,
    ResolutionStrategy,
    ConflictSeverity
)

# Authentication and authorization
from .auth import (
    CollaborationAuthenticator,
    CollaborationUser,
    CollaborationPermission,
    AuthenticationError,
    AuthorizationError
)

# Middleware and security
from .middleware import (
    WebSocketAuthenticationMiddleware,
    CollaborationRateLimitMiddleware,
    require_collaboration_permission,
    collaboration_session_access
)

__all__ = [
    # Core infrastructure
    "CollaborationState",
    "UserPresence", 
    "CollaborationMetrics",
    "SessionState",
    "UserRole",
    "ActivityType",
    "CollaborationEngine",
    "SessionManager",
    
    # Operational transformation
    "OperationalTransform",
    "Operation",
    "TransformResult", 
    "OperationType",
    "OperationTarget",
    
    # Conflict resolution
    "ConflictResolver",
    "ConflictContext",
    "ConflictResolution",
    "ConflictType",
    "ResolutionStrategy",
    "ConflictSeverity",
    
    # Authentication
    "CollaborationAuthenticator",
    "CollaborationUser",
    "CollaborationPermission",
    "AuthenticationError",
    "AuthorizationError",
    
    # Middleware
    "WebSocketAuthenticationMiddleware",
    "CollaborationRateLimitMiddleware", 
    "require_collaboration_permission",
    "collaboration_session_access"
] 