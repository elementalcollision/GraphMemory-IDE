"""
User Onboarding API Endpoints

Provides comprehensive user onboarding API including:
- Enhanced user registration with validation
- Email verification flow
- Onboarding progress tracking
- User preferences management
- Progressive onboarding steps

Created as part of TASK-021: User Onboarding Flow & Tenant Management
Research foundation: Progressive onboarding best practices, security patterns
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth import get_current_user, create_user, get_password_hash
from server.auth.email_verification import (
    get_email_verification_service, 
    EmailVerificationRequest,
    EmailVerificationResponse
)
from server.database import get_async_session
from server.database_models import (
    User, 
    UserOnboardingProgress, 
    UserOnboardingPreferences,
    WorkspaceSetup
)
from server.models import User as UserResponse

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/auth", tags=["User Onboarding"])
security = HTTPBearer()


# ================================
# Request/Response Models
# ================================

class UserRegistrationRequest(BaseModel):
    """Enhanced user registration request"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    accept_terms: bool = Field(..., description="Must accept terms and conditions")
    subscribe_newsletter: bool = Field(default=True)
    referral_code: Optional[str] = Field(None, max_length=50)
    
    # Onboarding preferences
    experience_level: str = Field(default="intermediate", pattern=r'^(beginner|intermediate|advanced)$')
    preferred_features: List[str] = Field(default_factory=list)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for required character types
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numeric characters')
        
        # Check for common patterns
        if v.lower() in ['password', '12345678', 'qwerty123']:
            raise ValueError('Password is too common')
        
        return v
    
    @validator('accept_terms')
    def validate_terms_acceptance(cls, v):
        """Ensure terms are accepted"""
        if not v:
            raise ValueError('You must accept the terms and conditions')
        return v


class UserRegistrationResponse(BaseModel):
    """User registration response"""
    success: bool
    message: str
    user_id: Optional[str] = None
    email_verification_required: bool = True
    next_step: str = "verify_email"


class OnboardingStepRequest(BaseModel):
    """Request to complete an onboarding step"""
    step_name: str = Field(..., max_length=100)
    data: Dict[str, Any] = Field(default_factory=dict)
    skipped: bool = Field(default=False)


class OnboardingStepResponse(BaseModel):
    """Response for onboarding step completion"""
    success: bool
    message: str
    step_name: str
    completed: bool
    next_step: Optional[str] = None


class OnboardingProgressResponse(BaseModel):
    """User onboarding progress response"""
    user_id: str
    total_steps: int
    completed_steps: int
    completion_percentage: float
    current_step: Optional[str] = None
    steps: List[Dict[str, Any]]


class UserPreferencesRequest(BaseModel):
    """Request to update user preferences"""
    show_tooltips: Optional[bool] = None
    show_guided_tours: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    theme_preference: Optional[str] = Field(None, pattern=r'^(light|dark|auto)$')
    experience_level: Optional[str] = Field(None, pattern=r'^(beginner|intermediate|advanced)$')
    preferred_features: Optional[List[str]] = None


class UserPreferencesResponse(BaseModel):
    """User preferences response"""
    show_tooltips: bool
    show_guided_tours: bool
    email_notifications_enabled: bool
    theme_preference: str
    experience_level: str
    preferred_features: List[str]
    dismissed_hints: List[str]


# ================================
# API Endpoints
# ================================

@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    client_request: Request,
    db_session: AsyncSession = Depends(get_async_session)
):
    """
    Enhanced user registration with progressive onboarding
    
    Features:
    - Strong password validation
    - Email verification trigger
    - Onboarding preferences setup
    - Security logging
    """
    try:
        # Check if username already exists
        username_stmt = select(User).where(User.username == request.username)
        username_result = await db_session.execute(username_stmt)
        if username_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        email_stmt = select(User).where(User.email == request.email)
        email_result = await db_session.execute(email_stmt)
        if email_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        hashed_password = get_password_hash(request.password)
        user_id = str(uuid4())
        
        new_user = User(
            id=user_id,
            username=request.username,
            email=request.email,
            full_name=request.full_name,
            hashed_password=hashed_password,
            email_verified=False,
            registration_completed=True,
            onboarding_completed=False,
            is_active=True,
            is_superuser=False,
            roles=["user"],
            preferences={
                "newsletter_subscription": request.subscribe_newsletter,
                "referral_code": request.referral_code
            }
        )
        
        db_session.add(new_user)
        
        # Create onboarding preferences
        onboarding_prefs = UserOnboardingPreferences(
            id=str(uuid4()),
            user_id=user_id,
            experience_level=request.experience_level,
            preferred_features=request.preferred_features,
            show_tooltips=True,
            show_guided_tours=True,
            email_notifications_enabled=True,
            theme_preference="auto",
            dismissed_hints=[]
        )
        
        db_session.add(onboarding_prefs)
        
        # Initialize onboarding steps
        await _initialize_onboarding_steps(db_session, user_id)
        
        await db_session.commit()
        
        # Send verification email
        email_service = await get_email_verification_service()
        verification_request = EmailVerificationRequest(
            email=request.email,
            user_id=user_id
        )
        
        verification_response = await email_service.send_verification_email(
            db_session, verification_request, client_request
        )
        
        logger.info(f"User registration successful: {request.username} ({user_id})")
        
        return UserRegistrationResponse(
            success=True,
            message="Registration successful! Please check your email to verify your account.",
            user_id=user_id,
            email_verification_required=True,
            next_step="verify_email"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/verify-email", response_model=Dict[str, Any])
async def verify_email(
    token: str,
    client_request: Request,
    db_session: AsyncSession = Depends(get_async_session)
):
    """
    Verify user email address with token
    
    Args:
        token: Email verification token
    """
    try:
        email_service = await get_email_verification_service()
        result = await email_service.verify_email_token(
            db_session, token, client_request
        )
        
        if result['success']:
            # Update onboarding progress
            await _complete_onboarding_step(
                db_session, result['user_id'], "email_verification"
            )
            
            return {
                **result,
                "next_step": "welcome_tour"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/resend-verification", response_model=EmailVerificationResponse)
async def resend_verification_email(
    request: EmailVerificationRequest,
    client_request: Request,
    db_session: AsyncSession = Depends(get_async_session)
):
    """Resend email verification"""
    try:
        email_service = await get_email_verification_service()
        result = await email_service.send_verification_email(
            db_session, request, client_request
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Resend verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email"
        )


@router.get("/onboarding/progress", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session)
):
    """Get user's onboarding progress"""
    try:
        # Get all onboarding steps for user
        stmt = select(UserOnboardingProgress).where(
            UserOnboardingProgress.user_id == current_user.id
        ).order_by(UserOnboardingProgress.step_order)
        
        result = await db_session.execute(stmt)
        progress_records = result.scalars().all()
        
        # Calculate progress
        total_steps = len(progress_records)
        completed_steps = sum(1 for record in progress_records if record.completed_at)
        completion_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Find current step
        current_step = None
        for record in progress_records:
            if not record.completed_at and not record.skipped:
                current_step = record.step_name
                break
        
        # Format steps
        steps = []
        for record in progress_records:
            steps.append({
                "step_name": record.step_name,
                "completed": record.completed_at is not None,
                "skipped": record.skipped,
                "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                "data": record.data
            })
        
        return OnboardingProgressResponse(
            user_id=current_user.id,
            total_steps=total_steps,
            completed_steps=completed_steps,
            completion_percentage=completion_percentage,
            current_step=current_step,
            steps=steps
        )
    
    except Exception as e:
        logger.error(f"Get onboarding progress failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get onboarding progress"
        )


@router.post("/onboarding/complete-step", response_model=OnboardingStepResponse)
async def complete_onboarding_step(
    request: OnboardingStepRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session)
):
    """Complete an onboarding step"""
    try:
        # Find the step
        stmt = select(UserOnboardingProgress).where(
            UserOnboardingProgress.user_id == current_user.id,
            UserOnboardingProgress.step_name == request.step_name
        )
        
        result = await db_session.execute(stmt)
        step_record = result.scalar_one_or_none()
        
        if not step_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Onboarding step not found"
            )
        
        # Update step
        if request.skipped:
            step_record.skipped = True
        else:
            step_record.completed_at = datetime.now(timezone.utc)
        
        step_record.data = request.data
        step_record.updated_at = datetime.now(timezone.utc)
        
        await db_session.commit()
        
        # Determine next step
        next_step = await _get_next_onboarding_step(db_session, current_user.id)
        
        # Check if onboarding is complete
        if not next_step:
            await _complete_user_onboarding(db_session, current_user.id)
        
        logger.info(f"Onboarding step completed: {request.step_name} for user {current_user.id}")
        
        return OnboardingStepResponse(
            success=True,
            message="Step completed successfully",
            step_name=request.step_name,
            completed=not request.skipped,
            next_step=next_step
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete onboarding step failed: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete onboarding step"
        )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session)
):
    """Get user onboarding preferences"""
    try:
        stmt = select(UserOnboardingPreferences).where(
            UserOnboardingPreferences.user_id == current_user.id
        )
        
        result = await db_session.execute(stmt)
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            # Create default preferences
            prefs = UserOnboardingPreferences(
                id=str(uuid4()),
                user_id=current_user.id,
                show_tooltips=True,
                show_guided_tours=True,
                email_notifications_enabled=True,
                theme_preference="auto",
                experience_level="intermediate",
                preferred_features=[],
                dismissed_hints=[]
            )
            db_session.add(prefs)
            await db_session.commit()
        
        return UserPreferencesResponse(
            show_tooltips=prefs.show_tooltips,
            show_guided_tours=prefs.show_guided_tours,
            email_notifications_enabled=prefs.email_notifications_enabled,
            theme_preference=prefs.theme_preference,
            experience_level=prefs.experience_level,
            preferred_features=prefs.preferred_features,
            dismissed_hints=prefs.dismissed_hints
        )
    
    except Exception as e:
        logger.error(f"Get user preferences failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user preferences"
        )


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    request: UserPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session)
):
    """Update user onboarding preferences"""
    try:
        stmt = select(UserOnboardingPreferences).where(
            UserOnboardingPreferences.user_id == current_user.id
        )
        
        result = await db_session.execute(stmt)
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        
        # Update preferences
        if request.show_tooltips is not None:
            prefs.show_tooltips = request.show_tooltips
        if request.show_guided_tours is not None:
            prefs.show_guided_tours = request.show_guided_tours
        if request.email_notifications_enabled is not None:
            prefs.email_notifications_enabled = request.email_notifications_enabled
        if request.theme_preference is not None:
            prefs.theme_preference = request.theme_preference
        if request.experience_level is not None:
            prefs.experience_level = request.experience_level
        if request.preferred_features is not None:
            prefs.preferred_features = request.preferred_features
        
        prefs.updated_at = datetime.now(timezone.utc)
        
        await db_session.commit()
        
        return UserPreferencesResponse(
            show_tooltips=prefs.show_tooltips,
            show_guided_tours=prefs.show_guided_tours,
            email_notifications_enabled=prefs.email_notifications_enabled,
            theme_preference=prefs.theme_preference,
            experience_level=prefs.experience_level,
            preferred_features=prefs.preferred_features,
            dismissed_hints=prefs.dismissed_hints
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user preferences failed: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )


# ================================
# Helper Functions
# ================================

async def _initialize_onboarding_steps(db_session: AsyncSession, user_id: str):
    """Initialize onboarding steps for new user"""
    steps = [
        ("email_verification", 1, "Verify your email address"),
        ("welcome_tour", 2, "Take the welcome tour"),
        ("profile_setup", 3, "Complete your profile"),
        ("workspace_creation", 4, "Create your first workspace"),
        ("feature_discovery", 5, "Discover key features"),
        ("collaboration_setup", 6, "Set up collaboration"),
        ("completion", 7, "Finish onboarding")
    ]
    
    for step_name, order, description in steps:
        progress = UserOnboardingProgress(
            id=str(uuid4()),
            user_id=user_id,
            step_name=step_name,
            step_order=order,
            data={"description": description},
            skipped=False
        )
        db_session.add(progress)


async def _complete_onboarding_step(
    db_session: AsyncSession, 
    user_id: str, 
    step_name: str
):
    """Mark an onboarding step as completed"""
    stmt = update(UserOnboardingProgress).where(
        UserOnboardingProgress.user_id == user_id,
        UserOnboardingProgress.step_name == step_name
    ).values(
        completed_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    await db_session.execute(stmt)
    await db_session.commit()


async def _get_next_onboarding_step(
    db_session: AsyncSession, 
    user_id: str
) -> Optional[str]:
    """Get the next incomplete onboarding step"""
    stmt = select(UserOnboardingProgress).where(
        UserOnboardingProgress.user_id == user_id,
        UserOnboardingProgress.completed_at.is_(None),
        UserOnboardingProgress.skipped == False
    ).order_by(UserOnboardingProgress.step_order).limit(1)
    
    result = await db_session.execute(stmt)
    next_step = result.scalar_one_or_none()
    
    return next_step.step_name if next_step else None


async def _complete_user_onboarding(db_session: AsyncSession, user_id: str):
    """Mark user onboarding as complete"""
    stmt = update(User).where(
        User.id == user_id
    ).values(
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(timezone.utc)
    )
    
    await db_session.execute(stmt)
    await db_session.commit()
    
    logger.info(f"User onboarding completed: {user_id}")


# Export router
__all__ = ["router"] 