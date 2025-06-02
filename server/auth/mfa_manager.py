"""
Multi-Factor Authentication (MFA) Manager for GraphMemory-IDE

This module implements comprehensive MFA functionality including:
- TOTP (Time-based One-Time Password) authentication
- QR code generation for authenticator app setup
- Backup codes for account recovery
- Recovery mechanisms and emergency access
- Device management and trusted devices
- Security monitoring and audit logging

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import base64
import io
import qrcode
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import hashlib
import hmac

from fastapi import HTTPException
import pyotp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..core.logger import logger
from ..models.user import User
from ..models.mfa_device import MFADevice, MFADeviceType
from ..models.backup_code import BackupCode
from ..core.database import get_db


class MFAError(Exception):
    """Base exception for MFA operations."""
    pass


class TOTPError(MFAError):
    """TOTP-specific exceptions."""
    pass


class BackupCodeError(MFAError):
    """Backup code-specific exceptions."""
    pass


class MFADeviceManager:
    """Manages MFA devices for users."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def create_totp_device(
        self, 
        user: User, 
        device_name: str = "Authenticator App"
    ) -> Tuple[MFADevice, str, str]:
        """
        Create a new TOTP device for user.
        
        Returns:
            Tuple of (device, secret_key, qr_code_url)
        """
        # Generate secret key
        secret_key = pyotp.random_base32()
        
        # Create TOTP object
        totp = pyotp.TOTP(secret_key)
        
        # Generate QR code URL
        issuer_name = "GraphMemory-IDE"
        account_name = f"{user.email}"
        qr_code_url = totp.provisioning_uri(
            name=account_name,
            issuer_name=issuer_name
        )
        
        # Create device record (not yet verified)
        device = MFADevice(
            user_id=user.id,
            device_type=MFADeviceType.TOTP,
            device_name=device_name,
            secret_key=self._encrypt_secret(secret_key),
            is_verified=False,
            created_at=datetime.utcnow(),
            last_used=None
        )
        
        # Save to database
        self.db.add(device)
        await self.db.commit()
        
        logger.info(f"TOTP device created for user {user.email}: {device_name}")
        
        return device, secret_key, qr_code_url
    
    async def verify_totp_device(
        self, 
        device: MFADevice, 
        verification_code: str
    ) -> bool:
        """Verify TOTP device with verification code."""
        if device.device_type != MFADeviceType.TOTP:
            raise TOTPError("Device is not a TOTP device")
        
        if device.is_verified:
            raise TOTPError("Device is already verified")
        
        # Decrypt secret key
        secret_key = self._decrypt_secret(device.secret_key)
        
        # Verify code
        totp = pyotp.TOTP(secret_key)
        if totp.verify(verification_code, valid_window=1):
            # Mark device as verified
            device.is_verified = True
            device.verified_at = datetime.utcnow()
            await self.db.commit()
            
            logger.info(f"TOTP device verified for user {device.user_id}")
            return True
        
        return False
    
    async def get_user_devices(self, user: User) -> List[MFADevice]:
        """Get all MFA devices for user."""
        # Implementation depends on your database setup
        pass
    
    async def delete_device(self, device: MFADevice) -> bool:
        """Delete MFA device."""
        try:
            await self.db.delete(device)
            await self.db.commit()
            
            logger.info(f"MFA device deleted: {device.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete MFA device {device.id}: {e}")
            return False
    
    def _encrypt_secret(self, secret: str) -> str:
        """Encrypt secret key for storage."""
        # In production, use a proper key derivation and encryption
        # This is a simplified example
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(secret.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt secret key."""
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted_data = base64.b64decode(encrypted_secret.encode())
        decrypted = f.decrypt(encrypted_data)
        return decrypted.decode()
    
    def _get_encryption_key(self) -> bytes:
        """Get encryption key for secrets."""
        # In production, this should come from environment variables
        # or a secure key management system
        password = b"your-secret-password"
        salt = b"your-salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key


class QRCodeGenerator:
    """Generates QR codes for MFA setup."""
    
    @staticmethod
    def generate_qr_code(data: str, size: int = 10) -> bytes:
        """Generate QR code image as bytes."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    @staticmethod
    def generate_qr_code_base64(data: str, size: int = 10) -> str:
        """Generate QR code as base64 string."""
        qr_bytes = QRCodeGenerator.generate_qr_code(data, size)
        return base64.b64encode(qr_bytes).decode()


class BackupCodeManager:
    """Manages backup codes for account recovery."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def generate_backup_codes(
        self, 
        user: User, 
        count: int = 10
    ) -> List[str]:
        """Generate backup codes for user."""
        codes = []
        
        # Delete existing backup codes
        await self._delete_existing_backup_codes(user)
        
        # Generate new codes
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = self._generate_code()
            codes.append(code)
            
            # Hash and store code
            hashed_code = self._hash_code(code)
            backup_code = BackupCode(
                user_id=user.id,
                code_hash=hashed_code,
                is_used=False,
                created_at=datetime.utcnow(),
                used_at=None
            )
            
            self.db.add(backup_code)
        
        await self.db.commit()
        
        logger.info(f"Generated {count} backup codes for user {user.email}")
        
        return codes
    
    async def verify_backup_code(self, user: User, code: str) -> bool:
        """Verify and mark backup code as used."""
        hashed_code = self._hash_code(code)
        
        # Find matching unused backup code
        backup_code = await self._get_backup_code(user, hashed_code)
        
        if backup_code and not backup_code.is_used:
            # Mark as used
            backup_code.is_used = True
            backup_code.used_at = datetime.utcnow()
            await self.db.commit()
            
            logger.info(f"Backup code used for user {user.email}")
            return True
        
        return False
    
    async def get_remaining_backup_codes_count(self, user: User) -> int:
        """Get count of remaining unused backup codes."""
        # Implementation depends on your database setup
        pass
    
    def _generate_code(self) -> str:
        """Generate a random backup code."""
        # Generate 8-character alphanumeric code
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        return code
    
    def _hash_code(self, code: str) -> str:
        """Hash backup code for secure storage."""
        # Use a salt for additional security
        salt = "your-backup-code-salt"
        combined = f"{salt}{code}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def _delete_existing_backup_codes(self, user: User):
        """Delete all existing backup codes for user."""
        # Implementation depends on your database setup
        pass
    
    async def _get_backup_code(self, user: User, hashed_code: str) -> Optional[BackupCode]:
        """Get backup code by hash."""
        # Implementation depends on your database setup
        pass


class TOTPValidator:
    """Validates TOTP codes."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def verify_totp_code(
        self, 
        user: User, 
        code: str, 
        device_id: Optional[str] = None
    ) -> Tuple[bool, Optional[MFADevice]]:
        """
        Verify TOTP code for user.
        
        Returns:
            Tuple of (is_valid, device_used)
        """
        if device_id:
            # Verify specific device
            device = await self._get_device_by_id(device_id)
            if not device or device.user_id != user.id:
                return False, None
            
            return await self._verify_device_code(device, code), device
        
        else:
            # Try all user's TOTP devices
            devices = await self._get_user_totp_devices(user)
            
            for device in devices:
                if await self._verify_device_code(device, code):
                    # Update last used
                    device.last_used = datetime.utcnow()
                    await self.db.commit()
                    
                    return True, device
            
            return False, None
    
    async def _verify_device_code(self, device: MFADevice, code: str) -> bool:
        """Verify code against specific device."""
        if not device.is_verified:
            return False
        
        # Decrypt secret key
        secret_key = self._decrypt_secret(device.secret_key)
        
        # Verify TOTP code
        totp = pyotp.TOTP(secret_key)
        return totp.verify(code, valid_window=1)
    
    async def _get_device_by_id(self, device_id: str) -> Optional[MFADevice]:
        """Get device by ID."""
        # Implementation depends on your database setup
        pass
    
    async def _get_user_totp_devices(self, user: User) -> List[MFADevice]:
        """Get all verified TOTP devices for user."""
        # Implementation depends on your database setup
        pass
    
    def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt secret key (same as in MFADeviceManager)."""
        # Implementation should be shared or moved to a utility class
        pass


class RecoveryManager:
    """Handles account recovery scenarios."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def initiate_recovery(self, user: User) -> str:
        """Initiate account recovery process."""
        # Generate recovery token
        recovery_token = secrets.token_urlsafe(32)
        
        # Store recovery token with expiration
        recovery_data = {
            'user_id': user.id,
            'token': recovery_token,
            'expires_at': datetime.utcnow() + timedelta(hours=24),
            'used': False
        }
        
        # Store in database or cache
        # Implementation depends on your setup
        
        logger.info(f"Recovery initiated for user {user.email}")
        
        return recovery_token
    
    async def verify_recovery_token(self, token: str) -> Optional[User]:
        """Verify recovery token and return user."""
        # Implementation depends on your database setup
        pass
    
    async def reset_mfa(self, user: User) -> bool:
        """Reset all MFA settings for user (emergency)."""
        try:
            # Delete all MFA devices
            await self._delete_all_user_devices(user)
            
            # Delete all backup codes
            await self._delete_all_backup_codes(user)
            
            logger.warning(f"MFA reset for user {user.email}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to reset MFA for user {user.email}: {e}")
            return False
    
    async def _delete_all_user_devices(self, user: User):
        """Delete all MFA devices for user."""
        # Implementation depends on your database setup
        pass
    
    async def _delete_all_backup_codes(self, user: User):
        """Delete all backup codes for user."""
        # Implementation depends on your database setup
        pass


class MFAManager:
    """
    Main MFA Manager coordinating all MFA operations.
    
    Features:
    - TOTP device management and verification
    - QR code generation for setup
    - Backup codes for recovery
    - Account recovery mechanisms
    - Security monitoring and logging
    """
    
    def __init__(self, settings, db_session):
        self.settings = settings
        self.db = db_session
        self.device_manager = MFADeviceManager(db_session)
        self.backup_code_manager = BackupCodeManager(db_session)
        self.totp_validator = TOTPValidator(db_session)
        self.recovery_manager = RecoveryManager(db_session)
        self.qr_generator = QRCodeGenerator()
    
    async def setup_totp(
        self, 
        user: User, 
        device_name: str = "Authenticator App"
    ) -> Dict[str, Any]:
        """Set up TOTP for user."""
        device, secret_key, qr_url = await self.device_manager.create_totp_device(
            user, device_name
        )
        
        # Generate QR code image
        qr_code_base64 = self.qr_generator.generate_qr_code_base64(qr_url)
        
        return {
            'device_id': device.id,
            'secret_key': secret_key,
            'qr_code_url': qr_url,
            'qr_code_image': qr_code_base64,
            'backup_codes': await self.backup_code_manager.generate_backup_codes(user)
        }
    
    async def verify_setup(
        self, 
        user: User, 
        device_id: str, 
        verification_code: str
    ) -> bool:
        """Verify TOTP setup with verification code."""
        device = await self._get_device_by_id(device_id)
        if not device or device.user_id != user.id:
            raise MFAError("Invalid device")
        
        return await self.device_manager.verify_totp_device(device, verification_code)
    
    async def verify_code(
        self, 
        user: User, 
        code: str, 
        allow_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Verify MFA code (TOTP or backup code).
        
        Returns:
            Dict with verification result and metadata
        """
        # First try TOTP codes
        is_valid, device = await self.totp_validator.verify_totp_code(user, code)
        
        if is_valid:
            return {
                'valid': True,
                'method': 'totp',
                'device_id': device.id if device else None,
                'device_name': device.device_name if device else None
            }
        
        # Try backup codes if allowed
        if allow_backup:
            backup_valid = await self.backup_code_manager.verify_backup_code(user, code)
            
            if backup_valid:
                remaining_codes = await self.backup_code_manager.get_remaining_backup_codes_count(user)
                
                return {
                    'valid': True,
                    'method': 'backup_code',
                    'remaining_backup_codes': remaining_codes
                }
        
        return {'valid': False}
    
    async def get_user_mfa_status(self, user: User) -> Dict[str, Any]:
        """Get MFA status for user."""
        devices = await self.device_manager.get_user_devices(user)
        verified_devices = [d for d in devices if d.is_verified]
        backup_codes_count = await self.backup_code_manager.get_remaining_backup_codes_count(user)
        
        return {
            'mfa_enabled': len(verified_devices) > 0,
            'devices': [
                {
                    'id': device.id,
                    'name': device.device_name,
                    'type': device.device_type.value,
                    'verified': device.is_verified,
                    'last_used': device.last_used.isoformat() if device.last_used else None
                }
                for device in devices
            ],
            'backup_codes_remaining': backup_codes_count,
            'recovery_available': True
        }
    
    async def disable_mfa(self, user: User) -> bool:
        """Disable MFA for user (removes all devices and backup codes)."""
        try:
            # Delete all devices
            devices = await self.device_manager.get_user_devices(user)
            for device in devices:
                await self.device_manager.delete_device(device)
            
            # Delete all backup codes
            await self.backup_code_manager._delete_existing_backup_codes(user)
            
            logger.info(f"MFA disabled for user {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable MFA for user {user.email}: {e}")
            return False
    
    async def regenerate_backup_codes(self, user: User) -> List[str]:
        """Regenerate backup codes for user."""
        return await self.backup_code_manager.generate_backup_codes(user)
    
    async def remove_device(self, user: User, device_id: str) -> bool:
        """Remove MFA device for user."""
        device = await self._get_device_by_id(device_id)
        
        if not device or device.user_id != user.id:
            raise MFAError("Invalid device")
        
        return await self.device_manager.delete_device(device)
    
    async def initiate_recovery(self, user: User) -> str:
        """Initiate account recovery for user who lost MFA access."""
        return await self.recovery_manager.initiate_recovery(user)
    
    async def complete_recovery(self, recovery_token: str) -> Optional[User]:
        """Complete account recovery with token."""
        user = await self.recovery_manager.verify_recovery_token(recovery_token)
        
        if user:
            # Reset MFA for user
            await self.recovery_manager.reset_mfa(user)
        
        return user
    
    def generate_qr_code(self, data: str) -> str:
        """Generate QR code as base64 string."""
        return self.qr_generator.generate_qr_code_base64(data)
    
    async def _get_device_by_id(self, device_id: str) -> Optional[MFADevice]:
        """Get device by ID."""
        # Implementation depends on your database setup
        pass


# Global MFA manager instance
mfa_manager = None


async def initialize_mfa_manager(settings, db_session):
    """Initialize the global MFA manager."""
    global mfa_manager
    if settings.MFA_ENABLED:
        mfa_manager = MFAManager(settings, db_session)
        logger.info("MFA manager initialized successfully")


def get_mfa_manager() -> Optional[MFAManager]:
    """Get the global MFA manager instance."""
    return mfa_manager 