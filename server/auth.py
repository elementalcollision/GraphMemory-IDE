"""
Authentication and Authorization System for GraphMemory-IDE MCP Server

This module provides JWT-based authentication, user management, and authorization
for the GraphMemory-IDE MCP server with secure token handling and user validation.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import ValidationError

from models import User, TokenData

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# JWT authentication is optional by default
JWT_ENABLED = os.environ.get("JWT_ENABLED", "false").lower() == "true"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={
        "read": "Read access to analytics data",
        "write": "Write access to create entities and relations",
        "admin": "Administrative access to all features",
        "analytics": "Access to analytics features and streaming data"
    },
    auto_error=False  # Don't auto-error to support optional authentication
)

# Mock user database - In production, replace with actual database
fake_users_db = {
    "testuser": {
        "username": "testuser",
        "full_name": "Test User",
        "email": "test@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "testpassword"
        "disabled": False,
        "roles": ["user", "analytics"],
    },
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$1234567890abcdef1234567890abcdef12345678",  # "adminpassword"
        "disabled": False,
        "roles": ["admin", "user", "analytics", "write"],
    },
    "analyticsuser": {
        "username": "analyticsuser",
        "full_name": "Analytics User",
        "email": "analytics@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "testpassword"
        "disabled": False,
        "roles": ["analytics", "read"],
    },
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def get_user(username: str) -> Optional[User]:
    """Get user from database by username"""
    user_data = fake_users_db.get(username)
    if user_data:
        return User(
            username=user_data["username"],
            email=user_data.get("email"),
            full_name=user_data.get("full_name"),
            disabled=user_data.get("disabled", False),
            roles=user_data.get("roles", [])
        )
    return None

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user_data = fake_users_db.get(username)
    if not user_data:
        logger.warning(f"Authentication failed: user '{username}' not found")
        return None
    
    if not verify_password(password, str(user_data["hashed_password"])):
        logger.warning(f"Authentication failed: invalid password for user '{username}'")
        return None
    
    if user_data.get("disabled", False):
        logger.warning(f"Authentication failed: user '{username}' is disabled")
        return None
    
    logger.info(f"User '{username}' authenticated successfully")
    return User(
        username=user_data["username"],
        email=user_data.get("email"),
        full_name=user_data.get("full_name"),
        disabled=user_data.get("disabled", False),
        roles=user_data.get("roles", [])
    )

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Add default scopes if not provided
    if "scopes" not in to_encode:
        username = data.get("sub")
        if username:
            user = get_user(str(username))
            if user:
                to_encode["scopes"] = user.roles
            else:
                to_encode["scopes"] = ["read"]
        else:
            to_encode["scopes"] = ["read"]
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug(f"Created access token for user: {data.get('sub')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise

def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scopes: list = payload.get("scopes", [])
        
        if username is None:
            return None
        
        token_data = TokenData(username=username, scopes=scopes)
        return token_data
    
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user from JWT token (required authentication)"""
    if not JWT_ENABLED:
        # Return a default user when JWT is disabled
        return User(
            username="anonymous",
            email="anonymous@localhost",
            full_name="Anonymous User",
            disabled=False,
            roles=["read", "write", "analytics", "admin"]
        )
    
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # Check if user has required scopes
    if security_scopes.scopes:
        for scope in security_scopes.scopes:
            if scope not in token_data.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": f"Bearer scope=\"{security_scopes.scope_str}\""},
                )
    
    return user

async def get_optional_current_user(token: str = Depends(oauth2_scheme)) -> Optional[User]:
    """Get current user from JWT token (optional authentication)"""
    if not JWT_ENABLED:
        # Return a default user when JWT is disabled
        return User(
            username="anonymous",
            email="anonymous@localhost",
            full_name="Anonymous User",
            disabled=False,
            roles=["read", "write", "analytics", "admin"]
        )
    
    if token is None:
        return None
    
    token_data = verify_token(token)
    if token_data is None:
        return None
    
    user = get_user(username=token_data.username)
    return user

def require_scopes(*required_scopes: str) -> None:
    """Decorator factory to require specific scopes"""
    def dependency(current_user: User = Depends(get_current_user)):
        if not JWT_ENABLED:
            return current_user
        
        user_scopes = set(current_user.roles)
        required_scopes_set = set(required_scopes)
        
        if not required_scopes_set.issubset(user_scopes):
            missing_scopes = required_scopes_set - user_scopes
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing_scopes)}",
            )
        
        return current_user
    
    return dependency

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if not JWT_ENABLED:
        return current_user
    
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return current_user

def require_analytics(current_user: User = Depends(get_current_user)) -> User:
    """Require analytics role"""
    if not JWT_ENABLED:
        return current_user
    
    if "analytics" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics access required",
        )
    
    return current_user

# User management functions

def create_user(username: str, password: str, email: Optional[str] = None, 
                full_name: Optional[str] = None, roles: Optional[list] = None) -> User:
    """Create a new user (for admin use)"""
    if username in fake_users_db:
        raise ValueError(f"User '{username}' already exists")
    
    hashed_password = get_password_hash(password)
    user_roles = roles or ["read"]
    
    fake_users_db[username] = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "hashed_password": hashed_password,
        "disabled": False,
        "roles": user_roles,
    }
    
    logger.info(f"Created new user: {username}")
    return User(
        username=username,
        email=email,
        full_name=full_name,
        disabled=False,
        roles=user_roles
    )

def update_user_roles(username: str, roles: list) -> Optional[User]:
    """Update user roles (for admin use)"""
    if username not in fake_users_db:
        return None
    
    fake_users_db[username]["roles"] = roles
    logger.info(f"Updated roles for user '{username}': {roles}")
    
    return get_user(username)

def disable_user(username: str) -> Optional[User]:
    """Disable a user account (for admin use)"""
    if username not in fake_users_db:
        return None
    
    fake_users_db[username]["disabled"] = True
    logger.info(f"Disabled user: {username}")
    
    return get_user(username)

def enable_user(username: str) -> Optional[User]:
    """Enable a user account (for admin use)"""
    if username not in fake_users_db:
        return None
    
    fake_users_db[username]["disabled"] = False
    logger.info(f"Enabled user: {username}")
    
    return get_user(username)

def list_users() -> Dict[str, User]:
    """List all users (for admin use)"""
    return {username: get_user(username) for username in fake_users_db.keys()}

# Security utilities

def validate_token_scopes(token: str, required_scopes: list) -> bool:
    """Validate that a token has required scopes"""
    token_data = verify_token(token)
    if not token_data:
        return False
    
    user_scopes = set(token_data.scopes)
    required_scopes_set = set(required_scopes)
    
    return required_scopes_set.issubset(user_scopes)

def get_token_info(token: str) -> Optional[Dict[str, Any]]:
    """Get information about a token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "username": payload.get("sub"),
            "scopes": payload.get("scopes", []),
            "expires": payload.get("exp"),
            "issued_at": payload.get("iat"),
        }
    except JWTError:
        return None

def is_token_expired(token: str) -> bool:
    """Check if a token is expired"""
    token_info = get_token_info(token)
    if not token_info:
        return True
    
    exp = token_info.get("exp")
    if not exp:
        return True
    
    return datetime.utcnow().timestamp() > exp

# Security headers and middleware utilities

def get_security_headers() -> Dict[str, str]:
    """Get security headers for responses"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }

# Initialize default admin user if not exists
def initialize_default_users() -> None:
    """Initialize default users for development"""
    if not fake_users_db:
        logger.info("Initializing default users")
        
        # Create admin user with a secure password
        admin_password = os.environ.get("ADMIN_PASSWORD", "adminpassword")
        fake_users_db["admin"] = {
            "username": "admin",
            "full_name": "Administrator", 
            "email": "admin@graphmemory.com",
            "hashed_password": get_password_hash(admin_password),
            "disabled": False,
            "roles": ["admin", "user", "analytics", "write", "read"],
        }
        
        # Create test user
        test_password = os.environ.get("TEST_PASSWORD", "testpassword")
        fake_users_db["testuser"] = {
            "username": "testuser",
            "full_name": "Test User",
            "email": "test@graphmemory.com", 
            "hashed_password": get_password_hash(test_password),
            "disabled": False,
            "roles": ["user", "analytics", "read"],
        }
        
        logger.info("Default users created successfully")

# Initialize users on module import
initialize_default_users() 