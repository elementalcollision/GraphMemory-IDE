"""
Authentication fixtures for GraphMemory-IDE integration testing.
Provides test users, JWT tokens, and permission systems.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pytest
from unittest.mock import patch

# Test user configurations
TEST_USERS = {
    "admin": {
        "id": "test-admin-001",
        "username": "test_admin",
        "email": "admin@test.graphmemory.com",
        "role": "admin",
        "permissions": ["read", "write", "delete", "admin"],
        "is_active": True
    },
    "user": {
        "id": "test-user-001", 
        "username": "test_user",
        "email": "user@test.graphmemory.com",
        "role": "user",
        "permissions": ["read", "write"],
        "is_active": True
    },
    "readonly": {
        "id": "test-readonly-001",
        "username": "test_readonly",
        "email": "readonly@test.graphmemory.com", 
        "role": "readonly",
        "permissions": ["read"],
        "is_active": True
    },
    "inactive": {
        "id": "test-inactive-001",
        "username": "test_inactive",
        "email": "inactive@test.graphmemory.com",
        "role": "user",
        "permissions": ["read"],
        "is_active": False
    }
}

@pytest.fixture(scope="function")
def test_users() -> Dict[str, Dict[str, Any]]:
    """Get test user configurations."""
    return TEST_USERS.copy()

@pytest.fixture(scope="function") 
def admin_user(test_users) -> Dict[str, Any]:
    """Get admin test user."""
    return test_users["admin"]

@pytest.fixture(scope="function")
def regular_user(test_users) -> Dict[str, Any]:
    """Get regular test user."""
    return test_users["user"]

@pytest.fixture(scope="function")
def readonly_user(test_users) -> Dict[str, Any]:
    """Get readonly test user."""
    return test_users["readonly"]

@pytest.fixture(scope="function")
def inactive_user(test_users) -> Dict[str, Any]:
    """Get inactive test user."""
    return test_users["inactive"]

@pytest.fixture(scope="function")
def jwt_secret_key() -> str:
    """Get JWT secret key for testing."""
    return "test-jwt-secret-key-do-not-use-in-production"

@pytest.fixture(scope="function")
def jwt_algorithm() -> str:
    """Get JWT algorithm for testing."""
    return "HS256"

@pytest.fixture(scope="function")
def jwt_expiration_hours() -> int:
    """Get JWT expiration time in hours."""
    return 24

def create_test_jwt_token(user_data: Dict[str, Any], secret_key: str, algorithm: str, 
                         expiration_hours: int = 24) -> str:
    """Create a test JWT token."""
    # Mock JWT token creation (in real implementation would use actual JWT library)
    import base64
    import json
    
    # Create header
    header = {
        "alg": algorithm,
        "typ": "JWT"
    }
    
    # Create payload
    payload = {
        "sub": user_data["id"],
        "username": user_data["username"],
        "email": user_data["email"],
        "role": user_data["role"],
        "permissions": user_data["permissions"],
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=expiration_hours)).timestamp())
    }
    
    # Create mock token (not actual JWT for simplicity in testing)
    header_b64 = base64.b64encode(json.dumps(header).encode()).decode()
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    signature = "mock_signature"
    
    return f"{header_b64}.{payload_b64}.{signature}"

@pytest.fixture(scope="function")
def admin_jwt_token(admin_user, jwt_secret_key, jwt_algorithm, jwt_expiration_hours) -> str:
    """Create JWT token for admin user."""
    return create_test_jwt_token(admin_user, jwt_secret_key, jwt_algorithm, jwt_expiration_hours)

@pytest.fixture(scope="function")
def user_jwt_token(regular_user, jwt_secret_key, jwt_algorithm, jwt_expiration_hours) -> str:
    """Create JWT token for regular user."""
    return create_test_jwt_token(regular_user, jwt_secret_key, jwt_algorithm, jwt_expiration_hours)

@pytest.fixture(scope="function")
def readonly_jwt_token(readonly_user, jwt_secret_key, jwt_algorithm, jwt_expiration_hours) -> str:
    """Create JWT token for readonly user."""
    return create_test_jwt_token(readonly_user, jwt_secret_key, jwt_algorithm, jwt_expiration_hours)

@pytest.fixture(scope="function")
def expired_jwt_token(regular_user, jwt_secret_key, jwt_algorithm) -> str:
    """Create an expired JWT token for testing."""
    return create_test_jwt_token(regular_user, jwt_secret_key, jwt_algorithm, expiration_hours=-1)

@pytest.fixture(scope="function")
def auth_headers(user_jwt_token) -> Dict[str, str]:
    """Create authentication headers for HTTP requests."""
    return {
        "Authorization": f"Bearer {user_jwt_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="function")
def admin_auth_headers(admin_jwt_token) -> Dict[str, str]:
    """Create authentication headers for admin user."""
    return {
        "Authorization": f"Bearer {admin_jwt_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="function")
def readonly_auth_headers(readonly_jwt_token) -> Dict[str, str]:
    """Create authentication headers for readonly user."""
    return {
        "Authorization": f"Bearer {readonly_jwt_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="function") 
def mock_auth_dependencies():
    """Mock authentication dependencies for testing."""
    
    class MockAuthManager:
        def __init__(self):
            self.current_user = None
            self.bypass_auth = False
        
        def set_current_user(self, user_data: Dict[str, Any]):
            """Set the current authenticated user."""
            self.current_user = user_data
        
        def set_bypass_auth(self, bypass: bool):
            """Set whether to bypass authentication."""
            self.bypass_auth = bypass
        
        def get_current_user(self) -> Optional[Dict[str, Any]]:
            """Get the current authenticated user."""
            if self.bypass_auth:
                return TEST_USERS["admin"]  # Default to admin when bypassing
            return self.current_user
        
        def verify_token(self, token: str) -> bool:
            """Mock token verification."""
            if self.bypass_auth:
                return True
            # Simple mock verification
            return token.startswith("Bearer ") and len(token) > 20
        
        def check_permission(self, permission: str) -> bool:
            """Check if current user has permission."""
            if self.bypass_auth:
                return True
            
            if not self.current_user:
                return False
            
            return permission in self.current_user.get("permissions", [])
    
    return MockAuthManager()

@pytest.fixture(scope="function")
def auth_test_scenarios():
    """Provide various authentication test scenarios."""
    return {
        "valid_admin_access": {
            "user": TEST_USERS["admin"],
            "expected_permissions": ["read", "write", "delete", "admin"],
            "should_succeed": True
        },
        "valid_user_access": {
            "user": TEST_USERS["user"],
            "expected_permissions": ["read", "write"],
            "should_succeed": True
        },
        "readonly_write_attempt": {
            "user": TEST_USERS["readonly"],
            "attempted_permission": "write",
            "should_succeed": False
        },
        "inactive_user_access": {
            "user": TEST_USERS["inactive"],
            "should_succeed": False
        },
        "no_auth_protected_resource": {
            "user": None,
            "should_succeed": False
        }
    }

@pytest.fixture(scope="function")
def permission_test_matrix():
    """Provide permission testing matrix."""
    return {
        "endpoints": {
            "/mcp/memory/create": {"required_permission": "write"},
            "/mcp/memory/{id}": {"required_permission": "read"},
            "/analytics/process": {"required_permission": "write"},
            "/analytics/results/{id}": {"required_permission": "read"},
            "/alerts/create": {"required_permission": "write"},
            "/alerts": {"required_permission": "read"},
            "/admin/users": {"required_permission": "admin"},
            "/admin/settings": {"required_permission": "admin"}
        },
        "users": TEST_USERS
    }

@pytest.fixture(scope="function")
def auth_environment_setup(jwt_secret_key, jwt_algorithm):
    """Setup authentication environment variables."""
    auth_env = {
        "JWT_SECRET_KEY": jwt_secret_key,
        "JWT_ALGORITHM": jwt_algorithm,
        "JWT_EXPIRATION_HOURS": "24",
        "AUTH_ENABLED": "true",
        "AUTH_BYPASS_FOR_TESTING": "false"
    }
    
    with patch.dict(os.environ, auth_env):
        yield auth_env

@pytest.fixture(scope="function")
def auth_bypass_mode():
    """Enable authentication bypass for integration tests."""
    bypass_env = {
        "AUTH_BYPASS_FOR_TESTING": "true",
        "AUTH_ENABLED": "false"
    }
    
    with patch.dict(os.environ, bypass_env):
        yield True

# Authentication performance monitoring
@pytest.fixture(scope="function")
def auth_performance_monitor():
    """Monitor authentication performance during tests."""
    
    class AuthPerformanceMonitor:
        def __init__(self):
            self.token_validations = []
            self.permission_checks = []
        
        def record_token_validation(self, duration: float, success: bool):
            """Record token validation performance."""
            self.token_validations.append({
                "duration": duration,
                "success": success,
                "timestamp": datetime.utcnow()
            })
        
        def record_permission_check(self, duration: float, permission: str, success: bool):
            """Record permission check performance."""
            self.permission_checks.append({
                "duration": duration,
                "permission": permission,
                "success": success,
                "timestamp": datetime.utcnow()
            })
        
        def get_auth_stats(self):
            """Get authentication performance statistics."""
            token_times = [v["duration"] for v in self.token_validations]
            permission_times = [p["duration"] for p in self.permission_checks]
            
            return {
                "token_validations": {
                    "count": len(self.token_validations),
                    "avg_duration": sum(token_times) / len(token_times) if token_times else 0,
                    "max_duration": max(token_times) if token_times else 0,
                    "success_rate": len([v for v in self.token_validations if v["success"]]) / len(self.token_validations) if self.token_validations else 0
                },
                "permission_checks": {
                    "count": len(self.permission_checks),
                    "avg_duration": sum(permission_times) / len(permission_times) if permission_times else 0,
                    "max_duration": max(permission_times) if permission_times else 0,
                    "success_rate": len([p for p in self.permission_checks if p["success"]]) / len(self.permission_checks) if self.permission_checks else 0
                }
            }
    
    return AuthPerformanceMonitor() 