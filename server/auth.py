"""
JWT Authentication utilities for GraphMemory-IDE MCP Server.
Provides secure token-based authentication for IDE plugin communication.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from models import TokenData, User, UserInDB

# JWT Configuration from environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_ENABLED = os.getenv("JWT_ENABLED", "true").lower() == "true"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Optional OAuth2 scheme that doesn't auto-redirect to login
optional_oauth2_scheme = HTTPBearer(auto_error=False)

# Simple in-memory user database for development/testing
# In production, this should be replaced with a proper database
fake_users_db: Dict[str, UserInDB] = {
    "testuser": UserInDB(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        disabled=False,
        hashed_password=pwd_context.hash("testpassword")
    ),
    "admin": UserInDB(
        username="admin",
        email="admin@example.com",
        full_name="Administrator",
        disabled=False,
        hashed_password=pwd_context.hash("adminpassword")
    )
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a hash for a password."""
    return pwd_context.hash(password)

def get_user(username: str) -> Optional[UserInDB]:
    """Retrieve a user from the database by username."""
    return fake_users_db.get(username)

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user with username and password."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with optional expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    Raises HTTPException if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # Return User model (without hashed_password)
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled
    )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current active user.
    Raises HTTPException if user is disabled.
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_auth_dependency():
    """
    Returns the appropriate authentication dependency based on JWT_ENABLED setting.
    If JWT is disabled, returns None (no authentication required).
    If JWT is enabled, returns the active user dependency.
    """
    if not JWT_ENABLED:
        return None
    return get_current_active_user

def require_auth(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Explicit authentication dependency that always requires authentication.
    Use this for endpoints that should always be protected regardless of JWT_ENABLED.
    """
    return current_user

# Utility function to generate a secure secret key
def generate_secret_key() -> str:
    """Generate a secure secret key for JWT signing."""
    import secrets
    return secrets.token_urlsafe(32)

# Development helper to create test users
def create_test_user(username: str, password: str, email: str = None, full_name: str = None) -> UserInDB:
    """Create a test user for development purposes."""
    user = UserInDB(
        username=username,
        email=email or f"{username}@example.com",
        full_name=full_name or username.title(),
        disabled=False,
        hashed_password=get_password_hash(password)
    )
    fake_users_db[username] = user
    return user

async def get_optional_current_user(
    request: Request,
    token_data: Optional[HTTPBearer] = Depends(optional_oauth2_scheme)
) -> Optional[User]:
    """
    Optional authentication dependency that respects JWT_ENABLED setting.
    
    - If JWT_ENABLED=false: Returns None (no authentication required)
    - If JWT_ENABLED=true and no token: Returns None (allows anonymous access)
    - If JWT_ENABLED=true and valid token: Returns authenticated User
    - If JWT_ENABLED=true and invalid token: Raises 401 HTTPException
    
    This allows endpoints to work in both authenticated and unauthenticated modes.
    """
    if not JWT_ENABLED:
        return None
    
    if token_data is None:
        # No token provided, allow anonymous access when JWT is enabled
        return None
    
    # Token provided, validate it
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract token from HTTPBearer credentials
        token = token_data.credentials if hasattr(token_data, 'credentials') else None
        if not token:
            return None
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data_obj = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data_obj.username)
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Return User model (without hashed_password)
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled
    )

async def get_required_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Required authentication dependency that always validates JWT tokens.
    Use this for endpoints that must always be protected regardless of JWT_ENABLED.
    This is an alias for get_current_user for clarity.
    """
    return await get_current_user(token)

def create_auth_dependency(required: bool = False):
    """
    Factory function to create authentication dependencies.
    
    Args:
        required: If True, always require authentication regardless of JWT_ENABLED
                 If False, respect JWT_ENABLED setting for optional authentication
    
    Returns:
        Authentication dependency function
    """
    if required:
        return get_required_current_user
    else:
        return get_optional_current_user 