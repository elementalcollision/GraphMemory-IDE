#!/usr/bin/env python3
"""
API Key Rotation Automation Script

This script provides automated API key rotation capabilities for GraphMemory-IDE
with environment segregation, scoped permissions, and monitoring.

Features:
- Automated rotation on 90-day schedule (configurable)
- Environment-specific key management (dev/staging/prod)
- Scoped permissions with least-privilege principles
- Zero-downtime rotation with gradual rollover
- Comprehensive audit logging and monitoring
- Integration with existing secrets infrastructure

Usage:
    python api_key_rotation.py --rotate-now --environment production
    python api_key_rotation.py --create-key --environment development --scopes read,write
    python api_key_rotation.py --status --environment all
    python api_key_rotation.py --revoke-key KEY_ID --reason "security_incident"
"""

import os
import sys
import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Set

# Add server path to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

try:
    from security.secrets_manager import (
        SecretsManager, APIKeyManager, APIKeyConfig, 
        SecretType, Environment, PermissionScope, SecretStatus
    )
    from security.key_storage import SecureKeyStorage, FilesystemKeyStorage
    from security.audit_logger import get_audit_logger, AuditEventType, AuditLevel
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the server security modules are properly installed.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/api_key_rotation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class APIKeyRotationManager:
    """
    High-level API key rotation manager with environment segregation and automated lifecycle management.
    """
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        # Initialize storage and managers
        self.storage = SecureKeyStorage(FilesystemKeyStorage("./secrets/api_keys"))
        self.secrets_manager = SecretsManager(self.storage)
        self.audit_logger = get_audit_logger()
        
        # Load environment-specific configurations
        self.environment_configs = self._load_environment_configs()
    
    def _load_environment_configs(self) -> Dict[Environment, Dict[str, Any]]:
        """Load environment-specific API key configurations"""
        configs = {}
        
        for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION, Environment.TESTING]:
            config_file = Path(f"./config/api_keys_{env.value}.json")
            
            if config_file.exists():
                try:
                    import json
                    with open(config_file, 'r') as f:
                        configs[env] = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load config for {env.value}: {e}")
                    configs[env] = self._get_default_config(env)
            else:
                configs[env] = self._get_default_config(env)
        
        return configs
    
    def _get_default_config(self, environment: Environment) -> Dict[str, Any]:
        """Get default configuration for environment"""
        base_config = {
            "rotation_days": 90,
            "default_scopes": ["read"],
            "rate_limit_per_minute": 1000,
            "rate_limit_per_hour": 10000,
            "enable_auto_rotation": True,
            "max_keys_per_project": 10
        }
        
        # Environment-specific overrides
        if environment == Environment.PRODUCTION:
            base_config.update({
                "rotation_days": 60,  # More frequent rotation in production
                "rate_limit_per_minute": 5000,
                "rate_limit_per_hour": 50000,
                "default_scopes": ["read"]  # More restrictive by default
            })
        elif environment == Environment.DEVELOPMENT:
            base_config.update({
                "rotation_days": 180,  # Less frequent for development
                "rate_limit_per_minute": 100,
                "rate_limit_per_hour": 1000,
                "default_scopes": ["read", "write"]  # More permissive for development
            })
        
        return base_config
    
    async def create_api_key(self, 
                           environment: Environment,
                           scopes: Optional[Set[PermissionScope]] = None,
                           description: str = "",
                           owner: Optional[str] = None,
                           project: Optional[str] = None,
                           expires_in_days: Optional[int] = None) -> tuple[str, str]:
        """
        Create new API key with environment-specific configuration.
        
        Args:
            environment: Target environment
            scopes: Permission scopes (uses environment defaults if None)
            description: Human-readable description
            owner: Key owner identifier
            project: Project identifier
            expires_in_days: Custom expiration (uses environment default if None)
            
        Returns:
            Tuple of (key_id, api_key_value)
        """
        try:
            # Get environment configuration
            env_config = self.environment_configs[environment]
            
            # Set defaults from environment config
            if scopes is None:
                scopes = set(PermissionScope(scope) for scope in env_config["default_scopes"])
            
            if expires_in_days is None:
                expires_in_days = env_config["rotation_days"]
            
            # Create API key
            key_id, api_key_value = await self.secrets_manager.create_api_key(
                environment=environment,
                scopes=scopes,
                description=description,
                owner=owner,
                project=project,
                expires_in_days=expires_in_days,
                rate_limit_per_minute=env_config["rate_limit_per_minute"],
                rate_limit_per_hour=env_config["rate_limit_per_hour"],
                tags={
                    "environment": environment.value,
                    "created_by": "api_key_rotation_script",
                    "auto_rotation": str(env_config["enable_auto_rotation"])
                }
            )
            
            # Log audit event
            self.audit_logger.log_api_key_creation(
                key_id=key_id,
                user_id=owner,
                details={
                    "environment": environment.value,
                    "scopes": [scope.value for scope in scopes],
                    "project": project,
                    "expires_in_days": expires_in_days
                }
            )
            
            logger.info(f"Created API key {key_id} for environment {environment.value}")
            return key_id, api_key_value
            
        except Exception as e:
            logger.error(f"Failed to create API key for {environment.value}: {e}")
            raise
    
    async def rotate_api_keys(self, environment: Optional[Environment] = None) -> Dict[str, Any]:
        """
        Rotate API keys that are approaching expiration.
        
        Args:
            environment: Specific environment to rotate (all if None)
            
        Returns:
            Rotation summary with statistics
        """
        try:
            logger.info(f"Starting API key rotation for environment: {environment or 'all'}")
            
            rotation_summary = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "environments_processed": [],
                "keys_rotated": 0,
                "keys_failed": 0,
                "errors": []
            }
            
            # Determine environments to process
            environments = [environment] if environment else list(Environment)
            
            for env in environments:
                if isinstance(env, str):
                    env = Environment(env)
                
                try:
                    env_results = await self._rotate_environment_keys(env)
                    rotation_summary["environments_processed"].append({
                        "environment": env.value,
                        "keys_rotated": env_results["rotated"],
                        "keys_failed": env_results["failed"],
                        "details": env_results
                    })
                    rotation_summary["keys_rotated"] += env_results["rotated"]
                    rotation_summary["keys_failed"] += env_results["failed"]
                    
                except Exception as e:
                    error_msg = f"Failed to rotate keys for {env.value}: {e}"
                    logger.error(error_msg)
                    rotation_summary["errors"].append(error_msg)
            
            rotation_summary["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            # Log audit event for rotation summary
            self.audit_logger.log_event(
                event_type=AuditEventType.SECRET_ROTATION,
                level=AuditLevel.INFO,
                message=f"API key rotation completed: {rotation_summary['keys_rotated']} rotated",
                details=rotation_summary
            )
            
            logger.info(f"API key rotation completed: {rotation_summary['keys_rotated']} keys rotated")
            return rotation_summary
            
        except Exception as e:
            logger.error(f"API key rotation failed: {e}")
            raise
    
    async def _rotate_environment_keys(self, environment: Environment) -> Dict[str, Any]:
        """Rotate keys for a specific environment"""
        results = {
            "environment": environment.value,
            "rotated": 0,
            "failed": 0,
            "skipped": 0,
            "keys_processed": []
        }
        
        try:
            # Get all API keys for this environment
            api_keys = await self.secrets_manager.api_key_manager.list_api_keys(
                environment=environment,
                status=SecretStatus.ACTIVE
            )
            
            for key_metadata in api_keys:
                try:
                    # Check if rotation is needed
                    should_rotate = self._should_rotate_key(key_metadata, environment)
                    
                    if should_rotate:
                        # Rotate the key
                        new_value = await self.secrets_manager.api_key_manager.rotate_api_key(
                            key_metadata.secret_id
                        )
                        
                        if new_value:
                            results["rotated"] += 1
                            results["keys_processed"].append({
                                "key_id": key_metadata.secret_id,
                                "action": "rotated",
                                "new_value_preview": new_value[:8] + "..." if new_value else None
                            })
                            
                            # Log audit event
                            self.audit_logger.log_event(
                                event_type=AuditEventType.SECRET_ROTATION,
                                level=AuditLevel.INFO,
                                message=f"API key rotated: {key_metadata.secret_id}",
                                resource_type="api_key",
                                resource_id=key_metadata.secret_id,
                                details={
                                    "environment": environment.value,
                                    "old_created_at": key_metadata.created_at.isoformat(),
                                    "rotation_reason": "scheduled_rotation"
                                }
                            )
                        else:
                            results["failed"] += 1
                            results["keys_processed"].append({
                                "key_id": key_metadata.secret_id,
                                "action": "failed",
                                "error": "rotation_failed"
                            })
                    else:
                        results["skipped"] += 1
                        results["keys_processed"].append({
                            "key_id": key_metadata.secret_id,
                            "action": "skipped",
                            "reason": "not_due_for_rotation"
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to process key {key_metadata.secret_id}: {e}")
                    results["failed"] += 1
                    results["keys_processed"].append({
                        "key_id": key_metadata.secret_id,
                        "action": "failed",
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to rotate keys for environment {environment.value}: {e}")
            raise
    
    def _should_rotate_key(self, key_metadata, environment: Environment) -> bool:
        """Determine if a key should be rotated"""
        env_config = self.environment_configs[environment]
        
        # Check if auto-rotation is enabled
        if not env_config.get("enable_auto_rotation", True):
            return False
        
        # Check if key is approaching expiration
        if key_metadata.expires_at:
            days_until_expiry = (key_metadata.expires_at - datetime.now(timezone.utc)).days
            rotation_threshold = 7  # Rotate 7 days before expiry
            
            if days_until_expiry <= rotation_threshold:
                return True
        
        # Check rotation frequency based on last rotation
        if key_metadata.last_rotated:
            days_since_rotation = (datetime.now(timezone.utc) - key_metadata.last_rotated).days
            max_rotation_interval = env_config["rotation_days"]
            
            if days_since_rotation >= max_rotation_interval:
                return True
        
        return False
    
    async def revoke_api_key(self, key_id: str, reason: str = "", user_id: Optional[str] = None) -> bool:
        """
        Revoke an API key immediately.
        
        Args:
            key_id: The key ID to revoke
            reason: Reason for revocation
            user_id: User performing the revocation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self.secrets_manager.api_key_manager.revoke_api_key(key_id, reason)
            
            if success:
                # Log audit event
                self.audit_logger.log_event(
                    event_type=AuditEventType.API_KEY_REVOCATION,
                    level=AuditLevel.WARNING,
                    message=f"API key revoked: {key_id}",
                    user_id=user_id,
                    resource_type="api_key",
                    resource_id=key_id,
                    action="revoke",
                    outcome="success",
                    details={"reason": reason}
                )
                
                logger.info(f"Revoked API key {key_id}: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to revoke API key {key_id}: {e}")
            return False
    
    async def get_api_key_status(self, environment: Optional[Environment] = None) -> Dict[str, Any]:
        """Get comprehensive status of API keys"""
        try:
            status = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environments": {},
                "total_keys": 0,
                "active_keys": 0,
                "expired_keys": 0,
                "keys_due_for_rotation": 0
            }
            
            # Process each environment
            environments = [environment] if environment else list(Environment)
            
            for env in environments:
                if isinstance(env, str):
                    env = Environment(env)
                
                env_status = await self._get_environment_status(env)
                status["environments"][env.value] = env_status
                
                # Update totals
                status["total_keys"] += env_status["total_keys"]
                status["active_keys"] += env_status["active_keys"]
                status["expired_keys"] += env_status["expired_keys"]
                status["keys_due_for_rotation"] += env_status["keys_due_for_rotation"]
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get API key status: {e}")
            return {"error": str(e)}
    
    async def _get_environment_status(self, environment: Environment) -> Dict[str, Any]:
        """Get status for a specific environment"""
        try:
            # Get all keys for this environment
            all_keys = await self.secrets_manager.api_key_manager.list_api_keys(environment=environment)
            
            status = {
                "total_keys": len(all_keys),
                "active_keys": 0,
                "expired_keys": 0,
                "revoked_keys": 0,
                "keys_due_for_rotation": 0,
                "keys_by_project": {},
                "keys_by_scope": {},
                "oldest_key": None,
                "newest_key": None
            }
            
            for key_metadata in all_keys:
                # Count by status
                if key_metadata.status == SecretStatus.ACTIVE:
                    status["active_keys"] += 1
                elif key_metadata.status == SecretStatus.EXPIRED:
                    status["expired_keys"] += 1
                elif key_metadata.status == SecretStatus.REVOKED:
                    status["revoked_keys"] += 1
                
                # Check if due for rotation
                if self._should_rotate_key(key_metadata, environment):
                    status["keys_due_for_rotation"] += 1
                
                # Count by project
                project = key_metadata.project or "unassigned"
                status["keys_by_project"][project] = status["keys_by_project"].get(project, 0) + 1
                
                # Count by scope
                for scope in key_metadata.scopes:
                    scope_name = scope.value if hasattr(scope, 'value') else str(scope)
                    status["keys_by_scope"][scope_name] = status["keys_by_scope"].get(scope_name, 0) + 1
                
                # Track oldest and newest
                if not status["oldest_key"] or key_metadata.created_at < datetime.fromisoformat(status["oldest_key"]["created_at"]):
                    status["oldest_key"] = {
                        "key_id": key_metadata.secret_id,
                        "created_at": key_metadata.created_at.isoformat()
                    }
                
                if not status["newest_key"] or key_metadata.created_at > datetime.fromisoformat(status["newest_key"]["created_at"]):
                    status["newest_key"] = {
                        "key_id": key_metadata.secret_id,
                        "created_at": key_metadata.created_at.isoformat()
                    }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get status for environment {environment.value}: {e}")
            return {"error": str(e)}


async def main() -> None:
    """Main entry point for the API key rotation script"""
    parser = argparse.ArgumentParser(description="API Key Rotation Management")
    parser.add_argument('--create-key', action='store_true', help='Create new API key')
    parser.add_argument('--rotate-now', action='store_true', help='Perform immediate key rotation')
    parser.add_argument('--revoke-key', type=str, help='Revoke specific API key by ID')
    parser.add_argument('--status', action='store_true', help='Show current API key status')
    
    parser.add_argument('--environment', type=str, choices=['development', 'staging', 'production', 'testing', 'all'],
                       default='all', help='Target environment')
    parser.add_argument('--scopes', type=str, help='Comma-separated list of scopes for new key')
    parser.add_argument('--description', type=str, default="", help='Description for new key')
    parser.add_argument('--owner', type=str, help='Owner identifier for new key')
    parser.add_argument('--project', type=str, help='Project identifier for new key')
    parser.add_argument('--expires-in-days', type=int, help='Days until expiration for new key')
    parser.add_argument('--reason', type=str, default="", help='Reason for revocation')
    
    args = parser.parse_args()
    
    # Ensure logs directory exists
    os.makedirs('./logs', exist_ok=True)
    
    try:
        rotation_manager = APIKeyRotationManager()
        
        # Parse environment
        environment = None if args.environment == 'all' else Environment(args.environment)
        
        if args.create_key:
            # Parse scopes
            scopes = None
            if args.scopes:
                scope_names = [s.strip() for s in args.scopes.split(',')]
                scopes = set(PermissionScope(scope) for scope in scope_names)
            
            key_id, api_key_value = await rotation_manager.create_api_key(
                environment=environment or Environment.DEVELOPMENT,
                scopes=scopes,
                description=args.description,
                owner=args.owner,
                project=args.project,
                expires_in_days=args.expires_in_days
            )
            
            print(f"\n=== API Key Created ===")
            print(f"Key ID: {key_id}")
            print(f"API Key: {api_key_value}")
            print(f"Environment: {environment.value if environment else 'development'}")
            print("\nIMPORTANT: Store this API key securely. It cannot be retrieved again.")
            
        elif args.rotate_now:
            rotation_summary = await rotation_manager.rotate_api_keys(environment)
            print(f"\n=== API Key Rotation Summary ===")
            print(f"Keys rotated: {rotation_summary['keys_rotated']}")
            print(f"Keys failed: {rotation_summary['keys_failed']}")
            print(f"Environments processed: {len(rotation_summary['environments_processed'])}")
            
        elif args.revoke_key:
            success = await rotation_manager.revoke_api_key(
                args.revoke_key, 
                args.reason, 
                args.owner
            )
            if success:
                print(f"Successfully revoked API key: {args.revoke_key}")
            else:
                print(f"Failed to revoke API key: {args.revoke_key}")
                sys.exit(1)
            
        elif args.status:
            status = await rotation_manager.get_api_key_status(environment)
            print(f"\n=== API Key Status ===")
            print(f"Total keys: {status['total_keys']}")
            print(f"Active keys: {status['active_keys']}")
            print(f"Expired keys: {status['expired_keys']}")
            print(f"Keys due for rotation: {status['keys_due_for_rotation']}")
            
            if status.get('environments'):
                for env_name, env_status in status['environments'].items():
                    print(f"\n{env_name.title()} Environment:")
                    print(f"  Total: {env_status['total_keys']}")
                    print(f"  Active: {env_status['active_keys']}")
                    print(f"  Due for rotation: {env_status['keys_due_for_rotation']}")
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        logger.info("API key rotation script interrupted by user")
    except Exception as e:
        logger.error(f"API key rotation script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 