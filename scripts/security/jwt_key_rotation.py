#!/usr/bin/env python3
"""
JWT Key Rotation Automation Script

This script provides automated JWT key rotation capabilities for GraphMemory-IDE
with EdDSA (Ed25519) algorithm support, monitoring, and alerting.

Features:
- Automated rotation on 30-day schedule (configurable)
- Zero-downtime rotation with multi-key support
- Health monitoring and alerting
- Rollback capabilities
- Comprehensive audit logging
- Integration with existing JWT infrastructure

Usage:
    python jwt_key_rotation.py --rotate-now
    python jwt_key_rotation.py --schedule-rotation --interval 30
    python jwt_key_rotation.py --status
    python jwt_key_rotation.py --health-check
"""

import os
import sys
import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Add server path to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

try:
    from security.jwt_manager import JWTKeyManager, JWTConfig, JWTValidator
    from security.key_storage import SecureKeyStorage, FilesystemKeyStorage, KeyRotationManager
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the server security modules are properly installed.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/jwt_rotation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JWTRotationManager:
    """
    High-level JWT key rotation manager with monitoring and automation.
    """
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize JWT key manager
        self.jwt_manager = JWTKeyManager(self.config)
        self.jwt_validator = JWTValidator(self.jwt_manager)
        
        # Initialize storage and rotation manager
        backend = FilesystemKeyStorage(self.config.key_storage_path)
        self.storage = SecureKeyStorage(backend)
        self.rotation_manager = KeyRotationManager(self.storage)
    
    def _load_config(self, config_path: Optional[str] = None) -> JWTConfig:
        """Load JWT configuration from environment or file"""
        return JWTConfig(
            algorithm=JWTConfig.Algorithm.ED25519,
            key_rotation_days=int(os.getenv('JWT_KEY_ROTATION_DAYS', '30')),
            access_token_expire_minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '60')),
            refresh_token_expire_days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7')),
            key_storage_path=os.getenv('JWT_KEY_STORAGE_PATH', './secrets/jwt'),
            enable_key_rotation=os.getenv('JWT_ENABLE_ROTATION', 'true').lower() == 'true',
            max_key_versions=int(os.getenv('JWT_MAX_KEY_VERSIONS', '5')),
            audit_logging=os.getenv('JWT_AUDIT_LOGGING', 'true').lower() == 'true'
        )
    
    async def rotate_keys_now(self) -> bool:
        """Perform immediate key rotation"""
        try:
            logger.info("Starting immediate JWT key rotation")
            
            # Perform health check first
            if not await self.health_check():
                logger.error("Health check failed - aborting rotation")
                return False
            
            # Get current key info
            current_key = self.jwt_manager.get_current_key_info()
            if current_key:
                logger.info(f"Current key: {current_key.key_id} (created: {current_key.created_at})")
            
            # Rotate keys
            new_key_id = self.jwt_manager.rotate_keys()
            
            # Verify new key works
            test_payload = {"test": "rotation_verification", "timestamp": datetime.now(timezone.utc).isoformat()}
            test_token = self.jwt_manager.create_token(test_payload)
            
            # Validate the test token
            decoded_payload = self.jwt_validator.validate_token(test_token)
            if decoded_payload.get("test") != "rotation_verification":
                raise RuntimeError("Token validation failed after rotation")
            
            logger.info(f"JWT key rotation completed successfully. New key: {new_key_id}")
            
            # Log rotation event
            await self._log_rotation_event(current_key.key_id if current_key else None, new_key_id)
            
            return True
            
        except Exception as e:
            logger.error(f"JWT key rotation failed: {e}")
            return False
    
    async def schedule_rotation(self, interval_days: int = 30) -> None:
        """Schedule automatic key rotation"""
        try:
            logger.info(f"Scheduling JWT key rotation every {interval_days} days")
            
            # Generate EdDSA key material
            def generate_ed25519_key() -> bytes:
                private_key = Ed25519PrivateKey.generate()
                return private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            
            # Schedule rotation for JWT keys
            rotation_interval = timedelta(days=interval_days)
            self.rotation_manager.schedule_rotation(
                key_pattern="jwt_key_*",
                rotation_interval=rotation_interval,
                key_generator=generate_ed25519_key
            )
            
            logger.info("JWT key rotation scheduled successfully")
            
        except Exception as e:
            logger.error(f"Failed to schedule JWT key rotation: {e}")
            raise
    
    async def start_rotation_service(self) -> None:
        """Start the background rotation service"""
        logger.info("Starting JWT key rotation service")
        await self.rotation_manager.start_rotation_service()
    
    def stop_rotation_service(self) -> None:
        """Stop the background rotation service"""
        logger.info("Stopping JWT key rotation service")
        self.rotation_manager.stop_rotation_service()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of JWT key management"""
        try:
            current_key = self.jwt_manager.get_current_key_info()
            all_keys = self.jwt_manager.list_all_keys()
            
            status = {
                'current_key': {
                    'key_id': current_key.key_id if current_key else None,
                    'algorithm': current_key.algorithm.value if current_key else None,
                    'created_at': current_key.created_at.isoformat() if current_key else None,
                    'expires_at': current_key.expires_at.isoformat() if current_key and current_key.expires_at else None,
                    'days_until_expiry': current_key.days_until_expiry() if current_key else None,
                    'usage_count': current_key.usage_count if current_key else 0,
                    'status': current_key.status.value if current_key else None
                },
                'total_keys': len(all_keys),
                'active_keys': len([k for k in all_keys if k.is_active()]),
                'expired_keys': len([k for k in all_keys if k.is_expired()]),
                'rotation_enabled': self.config.enable_key_rotation,
                'rotation_interval_days': self.config.key_rotation_days,
                'max_key_versions': self.config.max_key_versions,
                'storage_path': self.config.key_storage_path,
                'health_status': await self.health_check()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get JWT status: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> bool:
        """Perform comprehensive health check"""
        try:
            logger.info("Performing JWT key management health check")
            
            # Check if current key exists and is valid
            current_key = self.jwt_manager.get_current_key_info()
            if not current_key:
                logger.error("No current active key found")
                return False
            
            if current_key.is_expired():
                logger.error(f"Current key {current_key.key_id} is expired")
                return False
            
            # Test token creation and validation
            test_payload = {"test": "health_check", "timestamp": datetime.now(timezone.utc).isoformat()}
            test_token = self.jwt_manager.create_token(test_payload)
            
            # Validate the token
            decoded_payload = self.jwt_validator.validate_token(test_token)
            if decoded_payload.get("test") != "health_check":
                logger.error("Token validation failed during health check")
                return False
            
            # Check storage accessibility
            storage_path = Path(self.config.key_storage_path)
            if not storage_path.exists() or not os.access(storage_path, os.R_OK | os.W_OK):
                logger.error(f"Storage path {storage_path} is not accessible")
                return False
            
            # Check for upcoming expiration (warn if within 7 days)
            days_until_expiry = current_key.days_until_expiry()
            if days_until_expiry is not None and days_until_expiry <= 7:
                logger.warning(f"Current key expires in {days_until_expiry} days - consider rotation")
            
            logger.info("JWT key management health check passed")
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def _log_rotation_event(self, old_key_id: Optional[str], new_key_id: str) -> None:
        """Log rotation event for audit purposes"""
        event = {
            'event_type': 'jwt_key_rotation',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'old_key_id': old_key_id,
            'new_key_id': new_key_id,
            'rotation_method': 'automated' if self.config.enable_key_rotation else 'manual'
        }
        
        # Log to audit file
        audit_file = Path(self.config.key_storage_path) / "rotation_audit.log"
        with open(audit_file, 'a') as f:
            f.write(f"{event}\n")
        
        logger.info(f"Logged rotation event: {old_key_id} -> {new_key_id}")


async def main() -> None:
    """Main entry point for the rotation script"""
    parser = argparse.ArgumentParser(description="JWT Key Rotation Management")
    parser.add_argument('--rotate-now', action='store_true', help='Perform immediate key rotation')
    parser.add_argument('--schedule-rotation', action='store_true', help='Schedule automatic rotation')
    parser.add_argument('--interval', type=int, default=30, help='Rotation interval in days (default: 30)')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--health-check', action='store_true', help='Perform health check')
    parser.add_argument('--start-service', action='store_true', help='Start rotation service')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Ensure logs directory exists
    os.makedirs('./logs', exist_ok=True)
    
    try:
        rotation_manager = JWTRotationManager(args.config)
        
        if args.rotate_now:
            success = await rotation_manager.rotate_keys_now()
            sys.exit(0 if success else 1)
            
        elif args.schedule_rotation:
            await rotation_manager.schedule_rotation(args.interval)
            print(f"Scheduled JWT key rotation every {args.interval} days")
            
        elif args.status:
            status = await rotation_manager.get_status()
            print("\n=== JWT Key Management Status ===")
            for key, value in status.items():
                if isinstance(value, dict):
                    print(f"{key}:")
                    for sub_key, sub_value in value.items():
                        print(f"  {sub_key}: {sub_value}")
                else:
                    print(f"{key}: {value}")
            
        elif args.health_check:
            health_status = await rotation_manager.health_check()
            print(f"Health check: {'PASSED' if health_status else 'FAILED'}")
            sys.exit(0 if health_status else 1)
            
        elif args.start_service:
            print("Starting JWT key rotation service...")
            await rotation_manager.start_rotation_service()
            
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        logger.info("JWT rotation script interrupted by user")
    except Exception as e:
        logger.error(f"JWT rotation script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 