"""
MFA Device Model for GraphMemory-IDE

This module defines the database model for MFA devices including
TOTP authenticators and other multi-factor authentication methods.

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class MFADeviceType(Enum):
    """MFA device types."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    HARDWARE_KEY = "hardware_key"


class MFADevice(Base):
    """
    MFA Device model for storing user authentication devices.
    
    Supports TOTP devices (Google Authenticator, Authy, etc.) and other MFA methods.
    """
    __tablename__ = "mfa_devices"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Device information
    device_type = Column(String(50), nullable=False)  # TOTP, SMS, etc.
    device_name = Column(String(255), nullable=False)  # User-friendly name
    device_identifier = Column(String(255))  # Phone number, email, etc.
    
    # TOTP specific fields
    secret_key = Column(Text)  # Encrypted TOTP secret
    backup_tokens = Column(Text)  # Encrypted backup tokens
    
    # Device status
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Usage tracking
    verification_attempts = Column(String(10), default="0")
    last_used = Column(DateTime)
    verified_at = Column(DateTime)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    # user = relationship("User", back_populates="mfa_devices")
    
    def __repr__(self) -> None:
        return f"<MFADevice(id='{self.id}', user_id='{self.user_id}', type='{self.device_type}', verified={self.is_verified})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary (excluding sensitive data)."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'device_type': self.device_type,
            'device_name': self.device_name,
            'device_identifier': self.device_identifier,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_totp_device(self) -> bool:
        """Check if device is a TOTP device."""
        return self.device_type == MFADeviceType.TOTP.value
    
    def can_be_used(self) -> bool:
        """Check if device can be used for authentication."""
        return self.is_verified and self.is_active
    
    @classmethod
    def create_totp_device(
        cls,
        user_id: uuid.UUID,
        device_name: str,
        secret_key: str
    ) -> 'MFADevice':
        """Create a new TOTP device."""
        return cls(
            user_id=user_id,
            device_type=MFADeviceType.TOTP.value,
            device_name=device_name,
            secret_key=secret_key,
            is_verified=False,
            is_active=True
        )
    
    @classmethod
    def create_sms_device(
        cls,
        user_id: uuid.UUID,
        device_name: str,
        phone_number: str
    ) -> 'MFADevice':
        """Create a new SMS device."""
        return cls(
            user_id=user_id,
            device_type=MFADeviceType.SMS.value,
            device_name=device_name,
            device_identifier=phone_number,
            is_verified=False,
            is_active=True
        ) 