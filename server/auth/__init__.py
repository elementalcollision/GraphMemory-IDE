"""
Authentication Module for GraphMemory-IDE

This module provides comprehensive authentication functionality including:
- Single Sign-On (SSO) with SAML 2.0 and OAuth2/OIDC
- Multi-Factor Authentication (MFA) with TOTP
- Authentication routes and middleware
- Session management

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

# Import managers and main components
try:
    from .sso_manager import SSOManager, get_sso_manager, initialize_sso_manager
    from .mfa_manager import MFAManager, get_mfa_manager, initialize_mfa_manager
    from .auth_routes import router as auth_router
    
    # Import exceptions
    from .sso_manager import SSOError, SAMLError, OAuth2Error
    from .mfa_manager import MFAError, TOTPError, BackupCodeError
    
except ImportError as e:
    # Handle missing dependencies gracefully
    print(f"Warning: Some authentication dependencies are missing: {e}")
    print("Please install required packages: pip install aioredis pyotp qrcode[pil] PyJWT")
    
    # Create stub classes to prevent import errors
    class SSOManager:
        """Stub SSO Manager when dependencies are missing."""
        pass
    
    class MFAManager:
        """Stub MFA Manager when dependencies are missing."""
        pass
    
    def get_sso_manager() -> None:
        """Stub function returning None when SSO is not available."""
        return None
    
    def get_mfa_manager() -> None:
        """Stub function returning None when MFA is not available."""
        return None
    
    async def initialize_sso_manager(settings, db_session) -> None:
        """Stub initialization function."""
        print("SSO Manager not available - missing dependencies")
    
    async def initialize_mfa_manager(settings, db_session) -> None:
        """Stub initialization function."""
        print("MFA Manager not available - missing dependencies")
    
    # Stub exceptions
    class SSOError(Exception):
        pass
    
    class SAMLError(SSOError):
        pass
    
    class OAuth2Error(SSOError):
        pass
    
    class MFAError(Exception):
        pass
    
    class TOTPError(MFAError):
        pass
    
    class BackupCodeError(MFAError):
        pass
    
    # Create a stub router
    from fastapi import APIRouter
    auth_router = APIRouter(prefix="/auth", tags=["Authentication - Unavailable"])
    
    @auth_router.get("/status")
    async def auth_status() -> None:
        return {
            "status": "unavailable",
            "message": "Authentication features require additional dependencies",
            "required_packages": ["aioredis", "pyotp", "qrcode[pil]", "PyJWT"]
        }


__all__ = [
    'SSOManager',
    'MFAManager', 
    'get_sso_manager',
    'get_mfa_manager',
    'initialize_sso_manager',
    'initialize_mfa_manager',
    'auth_router',
    'SSOError',
    'SAMLError', 
    'OAuth2Error',
    'MFAError',
    'TOTPError',
    'BackupCodeError'
] 