"""
Backup Code Model for GraphMemory-IDE

This module defines the database model for MFA backup codes
used for account recovery when primary MFA devices are unavailable.

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BackupCode(Base):
    """
    Backup Code model for storing MFA recovery codes.
    
    These codes provide emergency access when primary MFA devices are unavailable.
    """
    __tablename__ = "backup_codes"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Code information
    code_hash = Column(String(255), nullable=False)  # Hashed backup code
    is_used = Column(Boolean, default=False, nullable=False)
    
    # Usage tracking
    used_at = Column(DateTime)
    used_from_ip = Column(String(45))  # IPv4/IPv6 address
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> None:
        return f"<BackupCode(id='{self.id}', user_id='{self.user_id}', used={self.is_used})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert backup code to dictionary (excluding sensitive data)."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'is_used': self.is_used,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def mark_as_used(self, ip_address: Optional[str] = None) -> None:
        """Mark backup code as used."""
        self.is_used = True
        self.used_at = datetime.utcnow()
        if ip_address:
            self.used_from_ip = ip_address
    
    @classmethod
    def create_backup_code(
        cls,
        user_id: uuid.UUID,
        code_hash: str
    ) -> 'BackupCode':
        """Create a new backup code."""
        return cls(
            user_id=user_id,
            code_hash=code_hash,
            is_used=False
        ) 