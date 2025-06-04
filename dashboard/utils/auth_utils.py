"""
Authentication Utilities

This module provides utilities for JWT token management and user authentication
in the Streamlit dashboard.
"""

import streamlit as st
import jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def store_token(token: str) -> None:
    """Store JWT token in session state"""
    try:
        setattr(st.session_state, 'access_token', token)
        setattr(st.session_state, 'token_expires', extract_expiry(token))
        logger.info("Token stored successfully")
    except Exception as e:
        logger.error(f"Error storing token: {e}")


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests"""
    if hasattr(st.session_state, 'access_token'):
        return {"Authorization": f"Bearer {getattr(st.session_state, 'access_token')}"}
    return {}


def validate_token() -> bool:
    """Validate if current token is still valid"""
    if not hasattr(st.session_state, 'access_token'):
        return False
    
    if hasattr(st.session_state, 'token_expires'):
        if datetime.now(timezone.utc) > getattr(st.session_state, 'token_expires'):
            logger.warning("Token has expired")
            return False
    
    return True


def extract_expiry(token: str) -> Optional[datetime]:
    """Extract expiry time from JWT token"""
    try:
        # Decode without verification to get expiry
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded.get('exp')
        
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    except Exception as e:
        logger.error(f"Error extracting token expiry: {e}")
    
    return None


def clear_auth_session() -> None:
    """
    Clear all authentication session data from Streamlit session state
    """
    auth_keys = [
        'authenticated', 'username', 'user_role', 'sso_provider',
        'mfa_enabled', 'auth_timestamp', 'session_token', 'user_permissions'
    ]
    
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]
    logger.info("Authentication session cleared")


def get_user_info() -> Optional[Dict[str, Any]]:
    """Extract user information from JWT token"""
    if not hasattr(st.session_state, 'access_token'):
        return None
    
    try:
        # Decode without verification to get user info
        decoded = jwt.decode(getattr(st.session_state, 'access_token'), options={"verify_signature": False})
        return {
            "username": decoded.get('sub'),
            "expires": decoded.get('exp'),
            "issued_at": decoded.get('iat')
        }
    except Exception as e:
        logger.error(f"Error extracting user info: {e}")
        return None


def is_authenticated() -> bool:
    """Check if user is currently authenticated"""
    return (
        getattr(st.session_state, 'authenticated', False) and
        validate_token()
    ) 