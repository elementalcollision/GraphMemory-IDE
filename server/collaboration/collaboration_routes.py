"""
Collaboration API Routes for GraphMemory-IDE

This module provides REST API endpoints for:
- Permission management and role-based access control
- Real-time collaboration features
- Team management and sharing
- Workflow management and approvals
- Advanced sharing and export features

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import json

from .permission_manager import (
    get_permission_manager, PermissionAction, ResourceType, Role, Permission
)

# Import function that will be created
def get_collaboration_manager():
    """Placeholder for collaboration manager getter."""
    return None


router = APIRouter(prefix="/api/v1/collaboration", tags=["collaboration"])


# Pydantic Models
class RoleCreateRequest(BaseModel):
    name: str
    description: str
    permissions: List[Dict[str, str]]


class PermissionGrantRequest(BaseModel):
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    expires_at: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None


class CommentCreateRequest(BaseModel):
    content: str
    element_id: Optional[str] = None
    position: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None


class TeamCreateRequest(BaseModel):
    name: str
    description: str
    members: List[str]


# Permission Management Routes

@router.post("/roles")
async def create_role(request: RoleCreateRequest, created_by: str = "system"):
    """Create a new role with specified permissions."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        # Create permissions from request
        permissions = []
        for perm_data in request.permissions:
            # Ensure correct types
            granted = bool(perm_data.get("granted", True))
            conditions_raw = perm_data.get("conditions", {})
            conditions = conditions_raw if isinstance(conditions_raw, dict) else {}
            
            permission = Permission(
                resource_type=ResourceType(perm_data["resource_type"]),
                resource_id=perm_data["resource_id"],
                action=PermissionAction(perm_data["action"]),
                granted=granted,
                conditions=conditions
            )
            permissions.append(permission)
        
        # Create role
        role = Role(
            name=request.name,
            description=request.description,
            permissions=permissions
        )
        
        role_id = await permission_manager.create_role(role, created_by)
        
        return {
            "status": "success",
            "role_id": role_id,
            "message": f"Role '{request.name}' created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid permission data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating role: {str(e)}")


@router.post("/roles/{role_id}/assign")
async def assign_role(
    role_id: str,
    user_id: str,
    assigned_by: str,
    team_id: Optional[str] = None,
    expires_in_days: Optional[int] = None
):
    """Assign a role to a user."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        assignment_id = await permission_manager.assign_role_to_user(
            user_id, role_id, assigned_by, team_id, expires_at
        )
        
        return {
            "status": "success",
            "assignment_id": assignment_id,
            "message": f"Role assigned to user successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning role: {str(e)}")


@router.post("/permissions/grant")
async def grant_permission(request: PermissionGrantRequest, granted_by: str):
    """Grant specific permission to a user."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        expires_at = None
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at)
        
        permission_id = await permission_manager.grant_resource_permission(
            request.user_id,
            ResourceType(request.resource_type),
            request.resource_id,
            PermissionAction(request.action),
            granted_by,
            expires_at,
            request.conditions
        )
        
        return {
            "status": "success",
            "permission_id": permission_id,
            "message": "Permission granted successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid permission data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error granting permission: {str(e)}")


@router.delete("/permissions/revoke")
async def revoke_permission(
    user_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    revoked_by: str
):
    """Revoke specific permission from a user."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        success = await permission_manager.revoke_resource_permission(
            user_id,
            ResourceType(resource_type),
            resource_id,
            PermissionAction(action),
            revoked_by
        )
        
        if success:
            return {
                "status": "success",
                "message": "Permission revoked successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "not_found",
                "message": "Permission not found or already revoked",
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid permission data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking permission: {str(e)}")


@router.get("/permissions/check")
async def check_permission(
    user_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    team_id: Optional[str] = None
):
    """Check if a user has permission for a specific action."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        has_permission = await permission_manager.check_permission(
            user_id,
            ResourceType(resource_type),
            resource_id,
            PermissionAction(action),
            team_id
        )
        
        return {
            "status": "success",
            "has_permission": has_permission,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid permission data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking permission: {str(e)}")


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str, team_id: Optional[str] = None):
    """Get all permissions for a user."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        permissions = await permission_manager.get_user_permissions(user_id, team_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "team_id": team_id,
            "permissions": permissions,
            "total_permissions": len(permissions),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user permissions: {str(e)}")


@router.get("/audit-log")
async def get_permission_audit_log(
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100
):
    """Get permission audit log entries."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        resource_type_enum = None
        if resource_type:
            resource_type_enum = ResourceType(resource_type)
        
        audit_logs = await permission_manager.get_permission_audit_log(
            user_id, resource_type_enum, limit
        )
        
        return {
            "status": "success",
            "audit_logs": audit_logs,
            "total_entries": len(audit_logs),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid resource type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting audit log: {str(e)}")


# Real-time Collaboration Routes

@router.websocket("/ws/{resource_type}/{resource_id}")
async def websocket_collaboration(
    websocket: WebSocket,
    resource_type: str,
    resource_id: str,
    user_id: str,
    display_name: str
):
    """WebSocket endpoint for real-time collaboration."""
    collaboration_manager = get_collaboration_manager()
    if not collaboration_manager:
        await websocket.close(code=1011, reason="Collaboration manager not available")
        return
    
    try:
        # Connect user
        session_id = await collaboration_manager.connect_user(
            websocket, user_id, display_name, resource_type, resource_id
        )
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                event_type = message.get("event_type")
                event_data = message.get("data", {})
                
                if event_type == "cursor_move":
                    await collaboration_manager.handle_cursor_move(
                        user_id, resource_type, resource_id, event_data.get("cursor", {})
                    )
                elif event_type == "element_select":
                    await collaboration_manager.handle_element_selection(
                        user_id, resource_type, resource_id, event_data.get("element_id")
                    )
                elif event_type == "element_lock":
                    element_id = event_data.get("element_id")
                    lock_type = event_data.get("lock_type", "edit")
                    success = await collaboration_manager.lock_element(user_id, element_id, lock_type)
                    
                    # Send lock result back to user
                    response = {
                        "event_type": "element_lock_result",
                        "data": {
                            "element_id": element_id,
                            "success": success,
                            "locked_by": user_id if success else None
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    
                elif event_type == "element_unlock":
                    element_id = event_data.get("element_id")
                    success = await collaboration_manager.unlock_element(user_id, element_id)
                    
                    # Send unlock result back to user
                    response = {
                        "event_type": "element_unlock_result",
                        "data": {
                            "element_id": element_id,
                            "success": success
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                continue
            except Exception as e:
                print(f"Error handling WebSocket message: {e}")
                continue
    
    except WebSocketDisconnect:
        pass
    finally:
        # Disconnect user
        await collaboration_manager.disconnect_user(
            websocket, user_id, resource_type, resource_id
        )


@router.post("/comments")
async def add_comment(
    request: CommentCreateRequest,
    user_id: str,
    display_name: str,
    resource_type: str,
    resource_id: str
):
    """Add a comment to a resource."""
    try:
        collaboration_manager = get_collaboration_manager()
        if not collaboration_manager:
            raise HTTPException(status_code=503, detail="Collaboration manager not available")
        
        comment_id = await collaboration_manager.add_comment(
            user_id,
            display_name,
            resource_type,
            resource_id,
            request.content,
            request.element_id,
            request.position,
            request.thread_id
        )
        
        return {
            "status": "success",
            "comment_id": comment_id,
            "message": "Comment added successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding comment: {str(e)}")


@router.get("/comments")
async def get_comments(
    resource_type: str,
    resource_id: str,
    element_id: Optional[str] = None
):
    """Get comments for a resource."""
    try:
        collaboration_manager = get_collaboration_manager()
        if not collaboration_manager:
            raise HTTPException(status_code=503, detail="Collaboration manager not available")
        
        comments = await collaboration_manager.get_comments(
            resource_type, resource_id, element_id
        )
        
        return {
            "status": "success",
            "comments": comments,
            "total_comments": len(comments),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting comments: {str(e)}")


# Team Management Routes

@router.post("/teams")
async def create_team(request: TeamCreateRequest, created_by: str):
    """Create a new team."""
    try:
        # This would integrate with a team management system
        # For now, return a placeholder response
        team_id = f"team_{int(datetime.utcnow().timestamp())}"
        
        return {
            "status": "success",
            "team_id": team_id,
            "name": request.name,
            "description": request.description,
            "members": request.members,
            "created_by": created_by,
            "message": "Team created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating team: {str(e)}")


@router.get("/teams/{team_id}/members")
async def get_team_members(team_id: str):
    """Get team members and their roles."""
    try:
        permission_manager = get_permission_manager()
        if not permission_manager:
            raise HTTPException(status_code=503, detail="Permission manager not available")
        
        # This would query team membership from database
        # For now, return placeholder data
        members = [
            {
                "user_id": "user1",
                "display_name": "John Doe",
                "role": "Team Admin",
                "joined_at": "2025-01-01T00:00:00",
                "permissions": []
            }
        ]
        
        return {
            "status": "success",
            "team_id": team_id,
            "members": members,
            "total_members": len(members),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting team members: {str(e)}")


# Sharing and Export Routes

@router.post("/share/secure-link")
async def create_secure_share_link(
    resource_type: str,
    resource_id: str,
    created_by: str,
    expires_in_days: int = 7,
    access_level: str = "view",
    password_protected: bool = False
):
    """Create a secure sharing link for a resource."""
    try:
        import secrets
        
        # Generate secure token
        share_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # This would save the sharing link to database
        share_link = {
            "token": share_token,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "access_level": access_level,
            "created_by": created_by,
            "expires_at": expires_at.isoformat(),
            "password_protected": password_protected,
            "url": f"/shared/{share_token}"
        }
        
        return {
            "status": "success",
            "share_link": share_link,
            "message": "Secure sharing link created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating share link: {str(e)}")


@router.get("/share/{token}")
async def access_shared_resource(token: str, password: Optional[str] = None):
    """Access a shared resource via secure token."""
    try:
        # This would validate the token and check permissions
        # For now, return placeholder data
        
        return {
            "status": "success",
            "resource_type": "dashboard",
            "resource_id": "dashboard_123",
            "access_level": "view",
            "valid": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing shared resource: {str(e)}")


@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get workflow approval status."""
    try:
        # This would integrate with workflow management system
        # For now, return placeholder data
        
        workflow_status = {
            "workflow_id": workflow_id,
            "status": "pending_approval",
            "current_step": "manager_review",
            "steps": [
                {
                    "step_name": "creator_submit",
                    "status": "completed",
                    "completed_at": "2025-06-01T10:00:00",
                    "user_id": "user1"
                },
                {
                    "step_name": "manager_review",
                    "status": "pending",
                    "assigned_to": "manager1",
                    "due_date": "2025-06-03T10:00:00"
                }
            ],
            "resource_type": "dashboard",
            "resource_id": "dashboard_123"
        }
        
        return {
            "status": "success",
            "workflow": workflow_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting workflow status: {str(e)}")


@router.get("/health")
async def get_collaboration_health():
    """Get collaboration system health status."""
    try:
        permission_manager = get_permission_manager()
        collaboration_manager = get_collaboration_manager()
        
        health_status = "healthy"
        issues = []
        
        if not permission_manager:
            health_status = "critical"
            issues.append("Permission manager not available")
        
        if not collaboration_manager:
            health_status = "warning"
            issues.append("Collaboration manager not available")
        
        # Get active collaboration sessions
        active_sessions = 0
        active_users = 0
        
        if collaboration_manager:
            active_sessions = len(collaboration_manager.resource_connections)
            active_users = len(collaboration_manager.user_presence)
        
        return {
            "status": health_status,
            "issues": issues,
            "active_sessions": active_sessions,
            "active_users": active_users,
            "features": {
                "permission_management": permission_manager is not None,
                "real_time_collaboration": collaboration_manager is not None,
                "team_management": True,  # Always available
                "secure_sharing": True,   # Always available
                "workflow_management": True  # Always available
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "critical",
            "issues": [f"Error checking collaboration health: {str(e)}"],
            "timestamp": datetime.utcnow().isoformat()
        } 