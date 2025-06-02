"""
SQLAlchemy Database Models for GraphMemory-IDE Production Environment.

This module defines the database schema for PostgreSQL using SQLAlchemy ORM.
These models support the analytics, collaboration, and memory management features.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    JSON,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# Base class for all ORM models
Base = declarative_base()

class BaseModel(Base):
    """Abstract base model with common fields"""
    __abstract__ = True
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class User(BaseModel):
    """User model for authentication and collaboration"""
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    roles: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    
    # User preferences and settings
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    analytics_queries = relationship("AnalyticsQuery", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
        Index("idx_users_username_active", "username", "is_active"),
    )


class UserSession(BaseModel):
    """User session tracking for security and analytics"""
    __tablename__ = "user_sessions"
    
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    
    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 support
    user_agent: Mapped[Optional[str]] = mapped_column(Text())
    location_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index("idx_sessions_token_active", "session_token", "is_active"),
        Index("idx_sessions_user_active", "user_id", "is_active", "expires_at"),
    )


class TelemetryEvent(BaseModel):
    """Telemetry events from IDE plugins"""
    __tablename__ = "telemetry_events"
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # Event data
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Performance tracking
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer())
    
    __table_args__ = (
        Index("idx_telemetry_type_created", "event_type", "created_at"),
        Index("idx_telemetry_user_created", "user_id", "created_at"),
        Index("idx_telemetry_session_created", "session_id", "created_at"),
    )


class AnalyticsQuery(BaseModel):
    """Analytics query tracking and caching"""
    __tablename__ = "analytics_queries"
    
    query_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Query details
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Results and performance
    result_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Integer(), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer(), default=0, nullable=False)
    
    # Caching
    cache_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    cache_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="analytics_queries")
    
    __table_args__ = (
        Index("idx_analytics_type_created", "query_type", "created_at"),
        Index("idx_analytics_cache_expires", "cache_key", "cache_expires_at"),
        Index("idx_analytics_user_created", "user_id", "created_at"),
    )


class KuzuQuery(BaseModel):
    """Kuzu graph database query tracking"""
    __tablename__ = "kuzu_queries"
    
    cypher_query: Mapped[str] = mapped_column(Text(), nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Query execution details
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_read_only: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    
    # Results and performance
    execution_time_ms: Mapped[float] = mapped_column(Integer(), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer(), default=0, nullable=False)
    columns: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    result_preview: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    
    __table_args__ = (
        Index("idx_kuzu_user_created", "user_id", "created_at"),
        Index("idx_kuzu_readonly_created", "is_read_only", "created_at"),
        Index("idx_kuzu_status_created", "status", "created_at"),
        CheckConstraint("status IN ('pending', 'completed', 'failed', 'timeout')", name="ck_kuzu_status"),
    )


class CollaborationSession(BaseModel):
    """Real-time collaboration sessions"""
    __tablename__ = "collaboration_sessions"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text())
    creator_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Session state
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    max_participants: Mapped[int] = mapped_column(Integer(), default=10, nullable=False)
    session_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    participants = relationship("CollaborationParticipant", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_collab_creator_active", "creator_id", "is_active"),
        Index("idx_collab_active_created", "is_active", "created_at"),
    )


class CollaborationParticipant(BaseModel):
    """Collaboration session participants"""
    __tablename__ = "collaboration_participants"
    
    session_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collaboration_sessions.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Participation details
    role: Mapped[str] = mapped_column(String(50), default="participant", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    
    # Relationships
    session = relationship("CollaborationSession", back_populates="participants")
    
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_user"),
        Index("idx_participant_session_active", "session_id", "is_active"),
        Index("idx_participant_user_active", "user_id", "is_active"),
        CheckConstraint("role IN ('creator', 'moderator', 'participant', 'observer')", name="ck_participant_role"),
    )


class SystemMetrics(BaseModel):
    """System performance and health metrics"""
    __tablename__ = "system_metrics"
    
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Integer(), nullable=False)
    metric_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Metric metadata
    component: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    metric_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    __table_args__ = (
        Index("idx_metrics_name_component_created", "metric_name", "component", "created_at"),
        Index("idx_metrics_env_created", "environment", "created_at"),
    )


class APIRequestLog(BaseModel):
    """API request logging and analytics"""
    __tablename__ = "api_request_logs"
    
    method: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer(), nullable=False, index=True)
    
    # Request details
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text())
    
    # Performance metrics
    duration_ms: Mapped[float] = mapped_column(Integer(), nullable=False)
    request_size: Mapped[Optional[int]] = mapped_column(Integer())
    response_size: Mapped[Optional[int]] = mapped_column(Integer())
    
    # Additional data
    headers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_details: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    __table_args__ = (
        Index("idx_requests_method_status_created", "method", "status_code", "created_at"),
        Index("idx_requests_path_created", "path", "created_at"),
        Index("idx_requests_user_created", "user_id", "created_at"),
        Index("idx_requests_duration_created", "duration_ms", "created_at"),
    )


class EmailVerificationToken(BaseModel):
    """Email verification token model"""
    __tablename__ = "email_verification_tokens"
    
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # Support IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="email_verification_tokens")
    
    __table_args__ = (
        Index("idx_email_verification_tokens_user_id", "user_id"),
        Index("idx_email_verification_tokens_token_hash", "token_hash"),
        Index("idx_email_verification_tokens_expires_at", "expires_at"),
    )


class UserOnboardingProgress(BaseModel):
    """User onboarding progress tracking model"""
    __tablename__ = "user_onboarding_progress"
    
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    step_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skipped: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="onboarding_progress")
    
    __table_args__ = (
        Index("idx_user_onboarding_progress_user_id", "user_id"),
        Index("idx_user_onboarding_progress_step_name", "step_name"),
        UniqueConstraint("user_id", "step_name", name="uq_user_onboarding_step"),
    )


class WorkspaceSetup(BaseModel):
    """Workspace setup configuration model"""
    __tablename__ = "workspace_setup"
    
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    setup_completed: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    setup_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    workspace_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    workspace_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workspace_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # personal, team, enterprise
    onboarding_flow: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # guided, self-service, import
    
    # Relationships
    user = relationship("User", back_populates="workspace_setups")
    
    __table_args__ = (
        Index("idx_workspace_setup_tenant_id", "tenant_id"),
        Index("idx_workspace_setup_user_id", "user_id"),
        UniqueConstraint("tenant_id", name="uq_workspace_setup_tenant"),
    )


class TeamInvitation(BaseModel):
    """Team invitation model"""
    __tablename__ = "team_invitations"
    
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    invited_by_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # viewer, editor, collaborator, admin
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)  # pending, accepted, expired, revoked
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey("users.id"), nullable=True)
    personal_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Relationships
    invited_by = relationship("User", foreign_keys=[invited_by_user_id], back_populates="sent_invitations")
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id], back_populates="accepted_invitations")
    
    __table_args__ = (
        Index("idx_team_invitations_tenant_id", "tenant_id"),
        Index("idx_team_invitations_email", "email"),
        Index("idx_team_invitations_token_hash", "token_hash"),
        Index("idx_team_invitations_status", "status"),
        Index("idx_team_invitations_expires_at", "expires_at"),
    )


class UserOnboardingPreferences(BaseModel):
    """User onboarding preferences model"""
    __tablename__ = "user_onboarding_preferences"
    
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    show_tooltips: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    show_guided_tours: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    theme_preference: Mapped[str] = mapped_column(String(20), default="auto", nullable=False)  # light, dark, auto
    experience_level: Mapped[str] = mapped_column(String(20), default="intermediate", nullable=False)  # beginner, intermediate, advanced
    preferred_features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    dismissed_hints: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="onboarding_preferences", uselist=False)
    
    __table_args__ = (
        Index("idx_user_onboarding_preferences_user_id", "user_id"),
        UniqueConstraint("user_id", name="uq_user_onboarding_preferences_user"),
    )


# Export all models for alembic discovery
__all__ = [
    "Base",
    "BaseModel", 
    "User",
    "UserSession",
    "TelemetryEvent",
    "AnalyticsQuery",
    "KuzuQuery",
    "CollaborationSession",
    "CollaborationParticipant",
    "SystemMetrics",
    "APIRequestLog",
    "EmailVerificationToken",
    "UserOnboardingProgress",
    "WorkspaceSetup",
    "TeamInvitation",
    "UserOnboardingPreferences",
] 