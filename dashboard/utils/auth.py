"""
Dashboard Authentication Utilities

This module provides authentication utilities for the dashboard,
including user management and session handling.
"""

import streamlit as st
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get the current authenticated user"""
    # Mock user for development
    return {
        "user_id": "dev-user-001",
        "username": "developer",
        "email": "dev@graphmemory.com",
        "role": "admin"
    }


def require_authentication() -> bool:
    """Check if user is authenticated, redirect if not"""
    # For development, always return True
    # In production, this would check actual authentication
    return True


def is_authenticated() -> bool:
    """Check if user is currently authenticated"""
    # For development, always return True
    return True


def get_user_permissions() -> Dict[str, bool]:
    """Get current user's permissions"""
    # Mock permissions for development
    return {
        "read_analytics": True,
        "write_analytics": True,
        "admin_access": True,
        "manage_alerts": True
    }


def logout() -> None:
    """Log out the current user"""
    # Clear any session state
    if hasattr(st, 'session_state'):
        # Get all attribute names that are strings starting with 'auth_' or exact matches
        auth_keys = []
        for key in dir(st.session_state):
            if not key.startswith('_'):  # Skip internal attributes
                if key.startswith('auth_') or key in ['user', 'authenticated']:
                    auth_keys.append(key)
        
        # Delete the identified keys
        for key in auth_keys:
            try:
                delattr(st.session_state, key)
            except AttributeError:
                pass  # Key doesn't exist, skip


def login(username: str, password: str) -> bool:
    """Attempt to log in a user"""
    # Mock login for development
    logger.info(f"Mock login attempt for user: {username}")
    return True


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests"""
    # Mock headers for development
    return {
        "Authorization": "Bearer mock-token",
        "X-User-ID": "dev-user-001"
    } 