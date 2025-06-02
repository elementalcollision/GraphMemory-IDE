"""
Authentication Integration for GraphMemory-IDE

This module handles the integration and initialization of all authentication
components including SSO, MFA, security middleware, and rate limiting.

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import logging
from typing import Optional
from fastapi import FastAPI

# Import core components
try:
    from ..core.advanced_config import AdvancedSettings
    from ..auth import (
        initialize_sso_manager,
        initialize_mfa_manager,
        auth_router,
        get_sso_manager,
        get_mfa_manager
    )
    from ..security.rate_limiter import RateLimitMiddleware, get_rate_limiter
    from ..security.security_middleware import SecurityMiddleware
    
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    logging.warning(f"Authentication dependencies not available: {e}")

logger = logging.getLogger(__name__)


class AuthenticationIntegration:
    """
    Manages integration of all authentication components.
    
    Coordinates SSO, MFA, security middleware, and rate limiting.
    """
    
    def __init__(self, app: FastAPI, settings: AdvancedSettings, db_session=None) -> None:
        self.app = app
        self.settings = settings
        self.db_session = db_session
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all authentication components."""
        if not DEPENDENCIES_AVAILABLE:
            logger.warning("Authentication integration skipped - missing dependencies")
            logger.info("Please install: pip install aioredis pyotp qrcode[pil] PyJWT python-multipart email-validator")
            return False
        
        try:
            # Initialize security middleware
            await self._setup_security_middleware()
            
            # Initialize rate limiting
            await self._setup_rate_limiting()
            
            # Initialize SSO if enabled
            if self.settings.SSO_ENABLED:
                await self._setup_sso()
            
            # Initialize MFA if enabled  
            if self.settings.MFA_ENABLED:
                await self._setup_mfa()
            
            # Register authentication routes
            await self._register_routes()
            
            self.initialized = True
            logger.info("Authentication integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Authentication integration failed: {e}")
            return False
    
    async def _setup_security_middleware(self) -> None:
        """Setup security middleware."""
        try:
            # Add security headers middleware
            security_middleware = SecurityMiddleware(self.settings)
            self.app.add_middleware(
                type(security_middleware),
                config=self.settings
            )
            logger.info("Security middleware initialized")
        except Exception as e:
            logger.error(f"Failed to setup security middleware: {e}")
            raise
    
    async def _setup_rate_limiting(self) -> None:
        """Setup rate limiting middleware."""
        try:
            # Get the rate limiter instance
            rate_limiter = get_rate_limiter()
            if rate_limiter:
                # Add rate limiting middleware
                self.app.add_middleware(
                    RateLimitMiddleware,
                    rate_limiter=rate_limiter
                )
                logger.info("Rate limiting middleware initialized")
            else:
                logger.warning("Rate limiter not available")
        except Exception as e:
            logger.error(f"Failed to setup rate limiting: {e}")
            raise
    
    async def _setup_sso(self) -> None:
        """Setup SSO manager."""
        try:
            await initialize_sso_manager(self.settings, self.db_session)
            sso_manager = get_sso_manager()
            
            if sso_manager:
                logger.info("SSO manager initialized successfully")
                logger.info(f"SSO enabled for providers: {self.settings.SSO_PROVIDERS}")
            else:
                logger.warning("SSO manager initialization returned None")
                
        except Exception as e:
            logger.error(f"Failed to setup SSO: {e}")
            raise
    
    async def _setup_mfa(self) -> None:
        """Setup MFA manager."""
        try:
            await initialize_mfa_manager(self.settings, self.db_session)
            mfa_manager = get_mfa_manager()
            
            if mfa_manager:
                logger.info("MFA manager initialized successfully")
                logger.info("MFA features: TOTP, backup codes, recovery")
            else:
                logger.warning("MFA manager initialization returned None")
                
        except Exception as e:
            logger.error(f"Failed to setup MFA: {e}")
            raise
    
    async def _register_routes(self) -> None:
        """Register authentication routes."""
        try:
            # Include authentication router
            self.app.include_router(auth_router)
            logger.info("Authentication routes registered")
            
            # Add authentication status endpoint
            @self.app.get("/api/auth/integration/status")
            async def get_auth_integration_status() -> None:
                """Get authentication integration status."""
                sso_manager = get_sso_manager()
                mfa_manager = get_mfa_manager()
                
                return {
                    "integration": {
                        "initialized": self.initialized,
                        "dependencies_available": DEPENDENCIES_AVAILABLE
                    },
                    "features": {
                        "sso": {
                            "enabled": self.settings.SSO_ENABLED,
                            "available": sso_manager is not None,
                            "providers": getattr(self.settings, 'SSO_PROVIDERS', [])
                        },
                        "mfa": {
                            "enabled": self.settings.MFA_ENABLED,
                            "available": mfa_manager is not None,
                            "methods": ["totp", "backup_codes"]
                        },
                        "security": {
                            "rate_limiting": True,
                            "security_headers": True,
                            "cors_enabled": getattr(self.settings, 'CORS_ENABLED', False)
                        }
                    },
                    "configuration": {
                        "jwt_algorithm": getattr(self.settings, 'JWT_ALGORITHM', 'HS256'),
                        "jwt_expiration_hours": getattr(self.settings, 'JWT_EXPIRATION_HOURS', 24),
                        "redis_enabled": getattr(self.settings, 'REDIS_ENABLED', False)
                    }
                }
            
            logger.info("Authentication status endpoint registered")
            
        except Exception as e:
            logger.error(f"Failed to register authentication routes: {e}")
            raise
    
    def get_integration_status(self) -> dict:
        """Get current integration status."""
        return {
            "initialized": self.initialized,
            "dependencies_available": DEPENDENCIES_AVAILABLE,
            "sso_available": get_sso_manager() is not None,
            "mfa_available": get_mfa_manager() is not None
        }


async def setup_authentication_integration(
    app: FastAPI, 
    settings: AdvancedSettings, 
    db_session=None
) -> AuthenticationIntegration:
    """
    Setup complete authentication integration.
    
    Args:
        app: FastAPI application instance
        settings: Application settings
        db_session: Database session
        
    Returns:
        AuthenticationIntegration instance
    """
    integration = AuthenticationIntegration(app, settings, db_session)
    
    # Initialize the integration
    success = await integration.initialize()
    
    if success:
        logger.info("Authentication integration setup completed")
    else:
        logger.warning("Authentication integration setup failed or incomplete")
    
    return integration


# Integration status function for health checks
def get_auth_integration_health() -> dict:
    """Get authentication integration health status."""
    try:
        sso_available = get_sso_manager() is not None
        mfa_available = get_mfa_manager() is not None
        
        status = "healthy" if DEPENDENCIES_AVAILABLE else "degraded"
        if not DEPENDENCIES_AVAILABLE:
            status = "unhealthy"
        
        return {
            "status": status,
            "dependencies_available": DEPENDENCIES_AVAILABLE,
            "components": {
                "sso": "available" if sso_available else "unavailable",
                "mfa": "available" if mfa_available else "unavailable",
                "security_middleware": "available",
                "rate_limiting": "available"
            },
            "required_dependencies": [
                "aioredis", "pyotp", "qrcode[pil]", "PyJWT", 
                "python-multipart", "email-validator"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "dependencies_available": False
        } 