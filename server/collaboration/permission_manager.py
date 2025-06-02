"""
Advanced Permission Manager for GraphMemory-IDE Collaboration

This module provides comprehensive permission management including:
- Granular role-based access control (RBAC)
- Resource-level permissions management
- Dynamic permission inheritance
- Permission audit logging and tracking
- Team-based permission hierarchies

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

from fastapi import HTTPException
import asyncpg


class PermissionAction(Enum):
    """Supported permission actions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"
    EXECUTE = "execute"
    EXPORT = "export"
    COMMENT = "comment"
    APPROVE = "approve"


class ResourceType(Enum):
    """Types of resources that can have permissions."""
    DASHBOARD = "dashboard"
    QUERY = "query"
    DATASET = "dataset"
    REPORT = "report"
    TEAM = "team"
    WORKFLOW = "workflow"
    ANALYTICS = "analytics"
    ALERT = "alert"


class PermissionLevel(Enum):
    """Permission levels for hierarchical access."""
    NONE = 0
    VIEWER = 1
    EDITOR = 2
    ADMIN = 3
    OWNER = 4


@dataclass
class Permission:
    """Individual permission definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource_type: ResourceType
    resource_id: str
    action: PermissionAction
    granted: bool = True
    granted_by: Optional[str] = None
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Role:
    """Role definition with associated permissions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    permissions: List[Permission] = field(default_factory=list)
    is_system_role: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserRole:
    """User role assignment."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role_id: str
    assigned_by: str
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    team_id: Optional[str] = None  # For team-scoped roles


@dataclass
class PermissionAuditLog:
    """Audit log entry for permission changes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str  # granted, revoked, modified
    user_id: str
    target_user_id: Optional[str] = None
    resource_type: ResourceType
    resource_id: str
    permission_action: PermissionAction
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    performed_by: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class PermissionManager:
    """Advanced permission management system."""
    
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.db_pool = db_pool
        self.system_roles: Dict[str, Role] = {}
        self.permission_cache: Dict[str, Dict[str, Set[str]]] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = datetime.utcnow()
        
    async def initialize(self) -> None:
        """Initialize the permission system with default roles."""
        await self._create_system_roles()
        await self._create_database_tables()
        print("Permission manager initialized with system roles")
    
    async def _create_system_roles(self) -> None:
        """Create default system roles."""
        # System Administrator
        admin_permissions = [
            Permission(resource_type=ResourceType.DASHBOARD, resource_id="*", action=PermissionAction.ADMIN),
            Permission(resource_type=ResourceType.QUERY, resource_id="*", action=PermissionAction.ADMIN),
            Permission(resource_type=ResourceType.DATASET, resource_id="*", action=PermissionAction.ADMIN),
            Permission(resource_type=ResourceType.REPORT, resource_id="*", action=PermissionAction.ADMIN),
            Permission(resource_type=ResourceType.TEAM, resource_id="*", action=PermissionAction.ADMIN),
            Permission(resource_type=ResourceType.WORKFLOW, resource_id="*", action=PermissionAction.ADMIN),
            Permission(resource_type=ResourceType.ANALYTICS, resource_id="*", action=PermissionAction.ADMIN),
            Permission(resource_type=ResourceType.ALERT, resource_id="*", action=PermissionAction.ADMIN),
        ]
        
        self.system_roles["system_admin"] = Role(
            id="system_admin",
            name="System Administrator",
            description="Full system access with all permissions",
            permissions=admin_permissions,
            is_system_role=True
        )
        
        # Analytics Manager
        analytics_permissions = [
            Permission(ResourceType.DASHBOARD, "*", PermissionAction.READ),
            Permission(ResourceType.DASHBOARD, "*", PermissionAction.WRITE),
            Permission(ResourceType.DASHBOARD, "*", PermissionAction.SHARE),
            Permission(ResourceType.QUERY, "*", PermissionAction.READ),
            Permission(ResourceType.QUERY, "*", PermissionAction.WRITE),
            Permission(ResourceType.QUERY, "*", PermissionAction.EXECUTE),
            Permission(ResourceType.DATASET, "*", PermissionAction.READ),
            Permission(ResourceType.REPORT, "*", PermissionAction.READ),
            Permission(ResourceType.REPORT, "*", PermissionAction.WRITE),
            Permission(ResourceType.REPORT, "*", PermissionAction.EXPORT),
            Permission(ResourceType.ANALYTICS, "*", PermissionAction.READ),
            Permission(ResourceType.ALERT, "*", PermissionAction.READ),
            Permission(ResourceType.ALERT, "*", PermissionAction.WRITE),
        ]
        
        self.system_roles["analytics_manager"] = Role(
            id="analytics_manager",
            name="Analytics Manager",
            description="Manage analytics dashboards, queries, and reports",
            permissions=analytics_permissions,
            is_system_role=True
        )
        
        # Data Analyst
        analyst_permissions = [
            Permission(ResourceType.DASHBOARD, "*", PermissionAction.READ),
            Permission(ResourceType.DASHBOARD, "*", PermissionAction.WRITE),
            Permission(ResourceType.QUERY, "*", PermissionAction.READ),
            Permission(ResourceType.QUERY, "*", PermissionAction.WRITE),
            Permission(ResourceType.QUERY, "*", PermissionAction.EXECUTE),
            Permission(ResourceType.DATASET, "*", PermissionAction.READ),
            Permission(ResourceType.REPORT, "*", PermissionAction.READ),
            Permission(ResourceType.REPORT, "*", PermissionAction.EXPORT),
            Permission(ResourceType.ANALYTICS, "*", PermissionAction.READ),
        ]
        
        self.system_roles["data_analyst"] = Role(
            id="data_analyst",
            name="Data Analyst",
            description="Create and analyze dashboards and queries",
            permissions=analyst_permissions,
            is_system_role=True
        )
        
        # Viewer
        viewer_permissions = [
            Permission(ResourceType.DASHBOARD, "*", PermissionAction.READ),
            Permission(ResourceType.QUERY, "*", PermissionAction.READ),
            Permission(ResourceType.DATASET, "*", PermissionAction.READ),
            Permission(ResourceType.REPORT, "*", PermissionAction.READ),
            Permission(ResourceType.ANALYTICS, "*", PermissionAction.READ),
        ]
        
        self.system_roles["viewer"] = Role(
            id="viewer",
            name="Viewer",
            description="Read-only access to dashboards and reports",
            permissions=viewer_permissions,
            is_system_role=True
        )
    
    async def _create_database_tables(self) -> None:
        """Create database tables for permission management."""
        try:
            async with self.db_pool.acquire() as conn:
                # Roles table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS roles (
                        id VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT,
                        permissions JSONB DEFAULT '[]',
                        is_system_role BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # User roles table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_roles (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        role_id VARCHAR(255) NOT NULL REFERENCES roles(id),
                        assigned_by VARCHAR(255) NOT NULL,
                        assigned_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP,
                        team_id VARCHAR(255),
                        UNIQUE(user_id, role_id, team_id)
                    )
                """)
                
                # Resource permissions table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS resource_permissions (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255),
                        team_id VARCHAR(255),
                        resource_type VARCHAR(50) NOT NULL,
                        resource_id VARCHAR(255) NOT NULL,
                        permission_action VARCHAR(50) NOT NULL,
                        granted BOOLEAN DEFAULT TRUE,
                        granted_by VARCHAR(255),
                        granted_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP,
                        conditions JSONB DEFAULT '{}'
                    )
                """)
                
                # Permission audit log table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS permission_audit_log (
                        id VARCHAR(255) PRIMARY KEY,
                        action VARCHAR(50) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        target_user_id VARCHAR(255),
                        resource_type VARCHAR(50) NOT NULL,
                        resource_id VARCHAR(255) NOT NULL,
                        permission_action VARCHAR(50) NOT NULL,
                        old_value JSONB,
                        new_value JSONB,
                        performed_by VARCHAR(255) NOT NULL,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        ip_address INET,
                        user_agent TEXT
                    )
                """)
                
                # Create indexes for performance
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_resource_permissions_user_resource ON resource_permissions(user_id, resource_type, resource_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_permission_audit_log_user_time ON permission_audit_log(user_id, timestamp)")
                
        except Exception as e:
            print(f"Error creating permission tables: {e}")
            raise
    
    async def create_role(self, role: Role, created_by: str) -> str:
        """Create a new role."""
        try:
            async with self.db_pool.acquire() as conn:
                permissions_json = json.dumps([
                    {
                        "resource_type": p.resource_type.value,
                        "resource_id": p.resource_id,
                        "action": p.action.value,
                        "granted": p.granted,
                        "conditions": p.conditions
                    } for p in role.permissions
                ])
                
                await conn.execute("""
                    INSERT INTO roles (id, name, description, permissions, is_system_role, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, role.id, role.name, role.description, permissions_json, 
                    role.is_system_role, role.created_at, role.updated_at)
                
                # Log the role creation
                await self._log_permission_change(
                    "role_created", created_by, None, ResourceType.TEAM, role.id,
                    PermissionAction.ADMIN, None, {"role_name": role.name}, created_by
                )
                
                self._invalidate_cache()
                return role.id
                
        except Exception as e:
            print(f"Error creating role: {e}")
            raise
    
    async def assign_role_to_user(self, user_id: str, role_id: str, assigned_by: str, 
                                team_id: Optional[str] = None, expires_at: Optional[datetime] = None) -> str:
        """Assign a role to a user."""
        try:
            async with self.db_pool.acquire() as conn:
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    assigned_by=assigned_by,
                    expires_at=expires_at,
                    team_id=team_id
                )
                
                await conn.execute("""
                    INSERT INTO user_roles (id, user_id, role_id, assigned_by, assigned_at, expires_at, team_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (user_id, role_id, team_id) 
                    DO UPDATE SET assigned_by = $4, assigned_at = $5, expires_at = $6
                """, user_role.id, user_id, role_id, assigned_by, 
                    user_role.assigned_at, expires_at, team_id)
                
                # Log the role assignment
                await self._log_permission_change(
                    "role_assigned", user_id, user_id, ResourceType.TEAM, role_id,
                    PermissionAction.ADMIN, None, {"assigned_by": assigned_by}, assigned_by
                )
                
                self._invalidate_cache_for_user(user_id)
                return user_role.id
                
        except Exception as e:
            print(f"Error assigning role: {e}")
            raise
    
    async def grant_resource_permission(self, user_id: str, resource_type: ResourceType, 
                                      resource_id: str, action: PermissionAction, 
                                      granted_by: str, expires_at: Optional[datetime] = None,
                                      conditions: Optional[Dict[str, Any]] = None) -> str:
        """Grant specific resource permission to a user."""
        try:
            async with self.db_pool.acquire() as conn:
                permission = Permission(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    granted_by=granted_by,
                    expires_at=expires_at,
                    conditions=conditions or {}
                )
                
                await conn.execute("""
                    INSERT INTO resource_permissions 
                    (id, user_id, resource_type, resource_id, permission_action, granted, 
                     granted_by, granted_at, expires_at, conditions)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (user_id, resource_type, resource_id, permission_action)
                    DO UPDATE SET granted = $6, granted_by = $7, granted_at = $8, 
                                  expires_at = $9, conditions = $10
                """, permission.id, user_id, resource_type.value, resource_id, 
                    action.value, True, granted_by, permission.granted_at, 
                    expires_at, json.dumps(conditions or {}))
                
                # Log the permission grant
                await self._log_permission_change(
                    "permission_granted", user_id, user_id, resource_type, resource_id,
                    action, None, {"granted_by": granted_by}, granted_by
                )
                
                self._invalidate_cache_for_user(user_id)
                return permission.id
                
        except Exception as e:
            print(f"Error granting resource permission: {e}")
            raise
    
    async def revoke_resource_permission(self, user_id: str, resource_type: ResourceType,
                                       resource_id: str, action: PermissionAction,
                                       revoked_by: str) -> bool:
        """Revoke specific resource permission from a user."""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM resource_permissions
                    WHERE user_id = $1 AND resource_type = $2 AND resource_id = $3 AND permission_action = $4
                """, user_id, resource_type.value, resource_id, action.value)
                
                if result == "DELETE 1":
                    # Log the permission revocation
                    await self._log_permission_change(
                        "permission_revoked", user_id, user_id, resource_type, resource_id,
                        action, {"had_permission": True}, None, revoked_by
                    )
                    
                    self._invalidate_cache_for_user(user_id)
                    return True
                
                return False
                
        except Exception as e:
            print(f"Error revoking resource permission: {e}")
            raise
    
    async def check_permission(self, user_id: str, resource_type: ResourceType,
                             resource_id: str, action: PermissionAction,
                             team_id: Optional[str] = None) -> bool:
        """Check if a user has permission for a specific action on a resource."""
        try:
            # Check cache first
            cache_key = f"{user_id}:{team_id or 'global'}"
            if cache_key in self.permission_cache and self._is_cache_valid():
                user_permissions = self.permission_cache[cache_key]
                permission_key = f"{resource_type.value}:{resource_id}:{action.value}"
                wildcard_key = f"{resource_type.value}:*:{action.value}"
                
                if permission_key in user_permissions or wildcard_key in user_permissions:
                    return True
            
            # Check database
            async with self.db_pool.acquire() as conn:
                # Check direct resource permissions
                direct_permission = await conn.fetchval("""
                    SELECT granted FROM resource_permissions
                    WHERE user_id = $1 AND resource_type = $2 
                    AND (resource_id = $3 OR resource_id = '*')
                    AND permission_action = $4
                    AND (expires_at IS NULL OR expires_at > NOW())
                    AND granted = TRUE
                    ORDER BY resource_id DESC
                    LIMIT 1
                """, user_id, resource_type.value, resource_id, action.value)
                
                if direct_permission:
                    self._cache_user_permission(user_id, resource_type, resource_id, action, team_id)
                    return True
                
                # Check role-based permissions
                role_permissions = await conn.fetch("""
                    SELECT r.permissions FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1 
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    AND (ur.team_id = $2 OR ur.team_id IS NULL)
                """, user_id, team_id)
                
                for row in role_permissions:
                    permissions = json.loads(row['permissions'])
                    for perm in permissions:
                        if (perm['resource_type'] == resource_type.value and
                            (perm['resource_id'] == resource_id or perm['resource_id'] == '*') and
                            perm['action'] == action.value and perm['granted']):
                            
                            self._cache_user_permission(user_id, resource_type, resource_id, action, team_id)
                            return True
                
                return False
                
        except Exception as e:
            print(f"Error checking permission: {e}")
            return False
    
    async def get_user_permissions(self, user_id: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all permissions for a user."""
        try:
            async with self.db_pool.acquire() as conn:
                # Get direct resource permissions
                direct_permissions = await conn.fetch("""
                    SELECT resource_type, resource_id, permission_action, granted, expires_at, conditions
                    FROM resource_permissions
                    WHERE user_id = $1 AND granted = TRUE
                    AND (expires_at IS NULL OR expires_at > NOW())
                """, user_id)
                
                # Get role-based permissions
                role_permissions = await conn.fetch("""
                    SELECT r.name as role_name, r.permissions, ur.expires_at as role_expires_at
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1 
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    AND (ur.team_id = $2 OR ur.team_id IS NULL)
                """, user_id, team_id)
                
                all_permissions = []
                
                # Add direct permissions
                for perm in direct_permissions:
                    all_permissions.append({
                        "source": "direct",
                        "resource_type": perm['resource_type'],
                        "resource_id": perm['resource_id'],
                        "action": perm['permission_action'],
                        "expires_at": perm['expires_at'].isoformat() if perm['expires_at'] else None,
                        "conditions": json.loads(perm['conditions']) if perm['conditions'] else {}
                    })
                
                # Add role-based permissions
                for role in role_permissions:
                    permissions = json.loads(role['permissions'])
                    for perm in permissions:
                        if perm['granted']:
                            all_permissions.append({
                                "source": "role",
                                "role_name": role['role_name'],
                                "resource_type": perm['resource_type'],
                                "resource_id": perm['resource_id'],
                                "action": perm['action'],
                                "expires_at": role['role_expires_at'].isoformat() if role['role_expires_at'] else None,
                                "conditions": perm.get('conditions', {})
                            })
                
                return all_permissions
                
        except Exception as e:
            print(f"Error getting user permissions: {e}")
            return []
    
    async def get_permission_audit_log(self, user_id: Optional[str] = None, 
                                     resource_type: Optional[ResourceType] = None,
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get permission audit log entries."""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM permission_audit_log
                    WHERE 1=1
                """
                params = []
                
                if user_id:
                    query += " AND (user_id = $1 OR target_user_id = $1)"
                    params.append(user_id)
                
                if resource_type:
                    param_num = len(params) + 1
                    query += f" AND resource_type = ${param_num}"
                    params.append(resource_type.value)
                
                query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
                params.append(limit)
                
                logs = await conn.fetch(query, *params)
                
                return [dict(log) for log in logs]
                
        except Exception as e:
            print(f"Error getting audit log: {e}")
            return []
    
    async def _log_permission_change(self, action: str, user_id: str, target_user_id: Optional[str],
                                   resource_type: ResourceType, resource_id: str,
                                   permission_action: PermissionAction, old_value: Optional[Dict[str, Any]],
                                   new_value: Optional[Dict[str, Any]], performed_by: str,
                                   ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Log permission changes for audit purposes."""
        try:
            async with self.db_pool.acquire() as conn:
                audit_log = PermissionAuditLog(
                    action=action,
                    user_id=user_id,
                    target_user_id=target_user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    permission_action=permission_action,
                    old_value=old_value,
                    new_value=new_value,
                    performed_by=performed_by,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                await conn.execute("""
                    INSERT INTO permission_audit_log
                    (id, action, user_id, target_user_id, resource_type, resource_id,
                     permission_action, old_value, new_value, performed_by, timestamp, ip_address, user_agent)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """, audit_log.id, action, user_id, target_user_id, resource_type.value,
                    resource_id, permission_action.value, json.dumps(old_value) if old_value else None,
                    json.dumps(new_value) if new_value else None, performed_by,
                    audit_log.timestamp, ip_address, user_agent)
                    
        except Exception as e:
            print(f"Error logging permission change: {e}")
    
    def _cache_user_permission(self, user_id: str, resource_type: ResourceType,
                             resource_id: str, action: PermissionAction, team_id: Optional[str]) -> None:
        """Cache a user permission for faster subsequent checks."""
        cache_key = f"{user_id}:{team_id or 'global'}"
        permission_key = f"{resource_type.value}:{resource_id}:{action.value}"
        
        if cache_key not in self.permission_cache:
            self.permission_cache[cache_key] = set()
        
        self.permission_cache[cache_key].add(permission_key)
    
    def _invalidate_cache(self) -> None:
        """Invalidate the entire permission cache."""
        self.permission_cache.clear()
        self.last_cache_update = datetime.utcnow()
    
    def _invalidate_cache_for_user(self, user_id: str) -> None:
        """Invalidate permission cache for a specific user."""
        keys_to_remove = [key for key in self.permission_cache.keys() if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self.permission_cache[key]
    
    def _is_cache_valid(self) -> bool:
        """Check if the permission cache is still valid."""
        return (datetime.utcnow() - self.last_cache_update).total_seconds() < self.cache_ttl


# Global permission manager instance
_permission_manager: Optional[PermissionManager] = None


async def initialize_permission_manager(db_pool: asyncpg.Pool) -> None:
    """Initialize the permission manager."""
    global _permission_manager
    _permission_manager = PermissionManager(db_pool)
    await _permission_manager.initialize()


def get_permission_manager() -> Optional[PermissionManager]:
    """Get the global permission manager instance."""
    return _permission_manager


async def shutdown_permission_manager() -> None:
    """Shutdown the permission manager."""
    global _permission_manager
    if _permission_manager:
        _permission_manager._invalidate_cache()
        _permission_manager = None 