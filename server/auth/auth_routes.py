"""
Authentication Routes for GraphMemory-IDE

This module provides comprehensive authentication endpoints including:
- SSO login and callback handling
- MFA setup and verification
- Session management
- Account recovery
- Device management

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import secrets

from fastapi import APIRouter, Request, Response, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import jwt

from ..core.logger import logger
from ..core.database import get_db
from ..core.advanced_config import AdvancedSettings
from .sso_manager import get_sso_manager, SSOError, SAMLError, OAuth2Error
from .mfa_manager import get_mfa_manager, MFAError, TOTPError
from ..models.user import User
from ..middleware.rate_limiter import rate_limit


# Pydantic models for request/response
class LoginRequest(BaseModel):
    provider: str
    return_url: Optional[str] = None


class SSOCallbackRequest(BaseModel):
    provider: str
    saml_response: Optional[str] = None
    code: Optional[str] = None
    state: Optional[str] = None


class MFASetupRequest(BaseModel):
    device_name: str = "Authenticator App"


class MFAVerificationRequest(BaseModel):
    device_id: str
    verification_code: str


class MFALoginRequest(BaseModel):
    code: str
    remember_device: bool = False


class RecoveryRequest(BaseModel):
    email: EmailStr


class RecoveryCompleteRequest(BaseModel):
    recovery_token: str
    new_password: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Security scheme
security = HTTPBearer()

# Router
router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
    settings: AdvancedSettings = Depends()
) -> User:
    """Get current authenticated user from JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is disabled")
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_user_by_id(db: Any, user_id: str) -> Optional[User]:
    """Get user by ID from database."""
    # Implementation depends on your database setup
    pass


# SSO Authentication Routes

@router.post("/sso/login", response_model=AuthResponse)
@rate_limit(requests=5, window=60)  # 5 requests per minute
async def sso_login(
    request: LoginRequest,
    db=Depends(get_db),
    settings: AdvancedSettings = Depends()
) -> AuthResponse:
    """Initiate SSO login flow."""
    try:
        sso_manager = get_sso_manager()
        if not sso_manager:
            raise HTTPException(status_code=503, detail="SSO not available")
        
        # Initiate login
        redirect_url = await sso_manager.initiate_login(
            request.provider, 
            request.return_url
        )
        
        return AuthResponse(
            success=True,
            message="SSO login initiated",
            data={"redirect_url": redirect_url}
        )
        
    except SSOError as e:
        logger.error(f"SSO login error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in SSO login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sso/callback", response_model=AuthResponse)
@rate_limit(requests=10, window=60)  # 10 requests per minute
async def sso_callback(
    callback_data: SSOCallbackRequest,
    db=Depends(get_db),
    settings: AdvancedSettings = Depends()
) -> AuthResponse:
    """Handle SSO callback and complete authentication."""
    try:
        sso_manager = get_sso_manager()
        if not sso_manager:
            raise HTTPException(status_code=503, detail="SSO not available")
        
        # Prepare callback data
        request_data = {}
        if callback_data.saml_response:
            request_data['SAMLResponse'] = callback_data.saml_response
        if callback_data.code:
            request_data['code'] = callback_data.code
        if callback_data.state:
            request_data['state'] = callback_data.state
        
        # Handle callback
        user, session_token = await sso_manager.handle_callback(
            callback_data.provider,
            request_data
        )
        
        # Check if user has MFA enabled
        mfa_manager = get_mfa_manager()
        mfa_required = False
        
        if mfa_manager:
            mfa_status = await mfa_manager.get_user_mfa_status(user)
            mfa_required = mfa_status.get('mfa_enabled', False)
        
        if mfa_required:
            # Store temporary token for MFA verification
            temp_token = create_temporary_token(user, settings)
            
            return AuthResponse(
                success=True,
                message="MFA verification required",
                data={
                    "mfa_required": True,
                    "temp_token": temp_token,
                    "user_id": str(user.id)
                }
            )
        else:
            # Complete login
            return AuthResponse(
                success=True,
                message="Login successful",
                data={
                    "token": session_token,
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": f"{user.first_name} {user.last_name}",
                        "role": user.role.value
                    }
                }
            )
        
    except (SSOError, SAMLError, OAuth2Error) as e:
        logger.error(f"SSO callback error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in SSO callback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sso/metadata/{provider}")
async def get_sso_metadata(provider: str) -> Response:
    """Get SSO metadata (SAML SP metadata)."""
    try:
        sso_manager = get_sso_manager()
        if not sso_manager:
            raise HTTPException(status_code=503, detail="SSO not available")
        
        # For now, return generic SAML metadata
        # In production, this should be provider-specific
        metadata = sso_manager.get_metadata()
        
        return Response(
            content=metadata,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=sp-metadata-{provider}.xml"}
        )
        
    except Exception as e:
        logger.error(f"Error generating SSO metadata: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# MFA Routes

@router.post("/mfa/setup", response_model=AuthResponse)
@rate_limit(requests=3, window=300)  # 3 requests per 5 minutes
async def setup_mfa(
    setup_request: MFASetupRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
) -> AuthResponse:
    """Set up MFA for current user."""
    try:
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA not available")
        
        # Set up TOTP
        setup_data = await mfa_manager.setup_totp(
            current_user, 
            setup_request.device_name
        )
        
        return AuthResponse(
            success=True,
            message="MFA setup initiated",
            data={
                "device_id": setup_data['device_id'],
                "secret_key": setup_data['secret_key'],
                "qr_code_url": setup_data['qr_code_url'],
                "qr_code_image": setup_data['qr_code_image'],
                "backup_codes": setup_data['backup_codes']
            }
        )
        
    except MFAError as e:
        logger.error(f"MFA setup error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in MFA setup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/mfa/verify-setup", response_model=AuthResponse)
@rate_limit(requests=10, window=300)  # 10 requests per 5 minutes
async def verify_mfa_setup(
    verification_request: MFAVerificationRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
) -> AuthResponse:
    """Verify MFA setup with verification code."""
    try:
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA not available")
        
        # Verify setup
        verified = await mfa_manager.verify_setup(
            current_user,
            verification_request.device_id,
            verification_request.verification_code
        )
        
        if verified:
            return AuthResponse(
                success=True,
                message="MFA setup completed successfully"
            )
        else:
            return AuthResponse(
                success=False,
                message="Invalid verification code"
            )
        
    except MFAError as e:
        logger.error(f"MFA verification error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in MFA verification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/mfa/verify", response_model=AuthResponse)
@rate_limit(requests=15, window=300)  # 15 requests per 5 minutes
async def verify_mfa(
    mfa_request: MFALoginRequest,
    temp_token: str = Form(...),
    db=Depends(get_db),
    settings: AdvancedSettings = Depends()
) -> AuthResponse:
    """Verify MFA code during login."""
    try:
        # Validate temporary token
        user = validate_temporary_token(temp_token, settings)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired temporary token")
        
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA not available")
        
        # Verify MFA code
        verification_result = await mfa_manager.verify_code(
            user, 
            mfa_request.code
        )
        
        if verification_result['valid']:
            # Create full session token
            session_token = create_session_token(user, settings)
            
            return AuthResponse(
                success=True,
                message="MFA verification successful",
                data={
                    "token": session_token,
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": f"{user.first_name} {user.last_name}",
                        "role": user.role.value
                    },
                    "verification_method": verification_result.get('method')
                }
            )
        else:
            return AuthResponse(
                success=False,
                message="Invalid MFA code"
            )
        
    except MFAError as e:
        logger.error(f"MFA verification error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in MFA verification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/mfa/status", response_model=AuthResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
) -> AuthResponse:
    """Get MFA status for current user."""
    try:
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            return AuthResponse(
                success=True,
                message="MFA status retrieved",
                data={"mfa_enabled": False}
            )
        
        mfa_status = await mfa_manager.get_user_mfa_status(current_user)
        
        return AuthResponse(
            success=True,
            message="MFA status retrieved",
            data=mfa_status
        )
        
    except Exception as e:
        logger.error(f"Error getting MFA status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/mfa/regenerate-backup-codes", response_model=AuthResponse)
@rate_limit(requests=2, window=3600)  # 2 requests per hour
async def regenerate_backup_codes(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
) -> AuthResponse:
    """Regenerate backup codes for current user."""
    try:
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA not available")
        
        backup_codes = await mfa_manager.regenerate_backup_codes(current_user)
        
        return AuthResponse(
            success=True,
            message="Backup codes regenerated",
            data={"backup_codes": backup_codes}
        )
        
    except MFAError as e:
        logger.error(f"Backup code regeneration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error regenerating backup codes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/mfa/disable", response_model=AuthResponse)
@rate_limit(requests=2, window=3600)  # 2 requests per hour
async def disable_mfa(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
) -> AuthResponse:
    """Disable MFA for current user."""
    try:
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA not available")
        
        disabled = await mfa_manager.disable_mfa(current_user)
        
        if disabled:
            return AuthResponse(
                success=True,
                message="MFA disabled successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to disable MFA")
        
    except MFAError as e:
        logger.error(f"MFA disable error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error disabling MFA: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Recovery Routes

@router.post("/recovery/initiate", response_model=AuthResponse)
@rate_limit(requests=3, window=3600)  # 3 requests per hour
async def initiate_recovery(
    recovery_request: RecoveryRequest,
    db=Depends(get_db)
) -> AuthResponse:
    """Initiate account recovery process."""
    try:
        # Get user by email
        user = await get_user_by_email(db, recovery_request.email)
        if not user:
            # Don't reveal whether email exists
            return AuthResponse(
                success=True,
                message="If an account exists with this email, recovery instructions have been sent"
            )
        
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="Recovery not available")
        
        # Initiate recovery
        recovery_token = await mfa_manager.initiate_recovery(user)
        
        # In production, send email with recovery token
        # For now, return it in response (NOT secure for production)
        logger.info(f"Recovery initiated for {user.email}, token: {recovery_token}")
        
        return AuthResponse(
            success=True,
            message="Recovery instructions sent",
            data={"recovery_token": recovery_token}  # Remove this in production
        )
        
    except Exception as e:
        logger.error(f"Error initiating recovery: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/recovery/complete", response_model=AuthResponse)
@rate_limit(requests=5, window=3600)  # 5 requests per hour
async def complete_recovery(
    recovery_complete: RecoveryCompleteRequest,
    db=Depends(get_db),
    settings: AdvancedSettings = Depends()
) -> AuthResponse:
    """Complete account recovery process."""
    try:
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="Recovery not available")
        
        # Complete recovery
        user = await mfa_manager.complete_recovery(recovery_complete.recovery_token)
        
        if user:
            # Create session token
            session_token = create_session_token(user, settings)
            
            return AuthResponse(
                success=True,
                message="Account recovery completed",
                data={
                    "token": session_token,
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": f"{user.first_name} {user.last_name}",
                        "role": user.role.value
                    }
                }
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired recovery token")
        
    except Exception as e:
        logger.error(f"Error completing recovery: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Logout Route

@router.post("/logout", response_model=AuthResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
) -> AuthResponse:
    """Logout current user."""
    try:
        token = credentials.credentials
        
        # Handle SSO logout if applicable
        sso_manager = get_sso_manager()
        slo_url = None
        
        if sso_manager:
            slo_url = await sso_manager.logout(token)
        
        # Invalidate token (add to blacklist in production)
        # Implementation depends on your token management strategy
        
        logger.info(f"User {current_user.email} logged out")
        
        response_data = {"message": "Logout successful"}
        if slo_url:
            response_data["slo_url"] = slo_url
        
        return AuthResponse(
            success=True,
            message="Logout successful",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Utility Functions

def create_temporary_token(user: User, settings: AdvancedSettings) -> str:
    """Create temporary token for MFA verification."""
    payload = {
        "user_id": str(user.id),
        "email": user.email,
        "type": "temp_mfa",
        "exp": datetime.utcnow() + timedelta(minutes=10)  # 10 minute expiry
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def validate_temporary_token(token: str, settings: AdvancedSettings) -> Optional[User]:
    """Validate temporary token and return user."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        if payload.get("type") != "temp_mfa":
            return None
        
        # Get user from payload (simplified)
        # In production, query database
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        # Return mock user for now
        # Implementation depends on your user model
        return None
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_session_token(user: User, settings: AdvancedSettings) -> str:
    """Create full session token."""
    payload = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_user_by_email(db: Any, email: str) -> Optional[User]:
    """Get user by email address."""
    # Implementation depends on your database setup
    pass


# Health check route
@router.get("/health")
async def auth_health_check() -> Dict[str, Any]:
    """Health check for authentication service."""
    sso_available = get_sso_manager() is not None
    mfa_available = get_mfa_manager() is not None
    
    return {
        "status": "healthy",
        "sso_available": sso_available,
        "mfa_available": mfa_available,
        "timestamp": datetime.utcnow().isoformat()
    } 