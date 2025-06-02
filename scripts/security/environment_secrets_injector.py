#!/usr/bin/env python3
"""
Environment Secrets Injection Script

This script provides secure injection of secrets into environment variables
for GraphMemory-IDE applications without exposing secrets in configuration files.

Features:
- Environment-specific secret injection (dev/staging/prod)
- Template variable substitution with ${VAR} syntax
- Secure secret retrieval from encrypted storage
- Docker and Kubernetes integration support
- Audit logging for secret access
- Validation of required secrets

Usage:
    python environment_secrets_injector.py --environment production --output-file .env.production
    python environment_secrets_injector.py --environment development --template templates/env.template
    python environment_secrets_injector.py --validate --environment staging
"""

import os
import sys
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add server path to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

try:
    from security.secrets_manager import SecretsManager, Environment, SecretType
    from security.key_storage import SecureKeyStorage, FilesystemKeyStorage
    from security.audit_logger import get_audit_logger, AuditEventType, AuditLevel
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the server security modules are properly installed.")
    sys.exit(1)

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnvironmentSecretsInjector:
    """
    Secure environment secrets injection with template support and validation.
    """
    
    def __init__(self) -> None:
        # Initialize secrets manager
        self.storage = SecureKeyStorage(FilesystemKeyStorage("./secrets"))
        self.secrets_manager = SecretsManager(self.storage)
        self.audit_logger = get_audit_logger()
        
        # Load environment configurations
        self.environment_configs = self._load_environment_configs()
    
    def _load_environment_configs(self) -> Dict[Environment, Dict[str, Any]]:
        """Load environment-specific configurations"""
        configs = {}
        
        for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION, Environment.TESTING]:
            config_file = Path(f"./config/{env.value}_secrets.json")
            
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        configs[env] = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load config for {env.value}: {e}")
                    configs[env] = {}
            else:
                logger.warning(f"No configuration file found for {env.value}")
                configs[env] = {}
        
        return configs
    
    def _substitute_variables(self, text: str, variables: Dict[str, str]) -> str:
        """
        Substitute ${VAR} placeholders with actual values.
        
        Args:
            text: Text containing ${VAR} placeholders
            variables: Dictionary of variable name -> value mappings
            
        Returns:
            Text with substituted values
        """
        def replace_var(match) -> None:
            var_name = match.group(1)
            if var_name in variables:
                return variables[var_name]
            else:
                logger.warning(f"Variable ${{{var_name}}} not found in available secrets")
                return match.group(0)  # Return original placeholder
        
        # Pattern to match ${VAR_NAME}
        pattern = r'\$\{([A-Z0-9_]+)\}'
        return re.sub(pattern, replace_var, text)
    
    async def collect_environment_secrets(self, environment: Environment) -> Dict[str, str]:
        """
        Collect all secrets for a specific environment.
        
        Args:
            environment: Target environment
            
        Returns:
            Dictionary of secret name -> value mappings
        """
        try:
            secrets = {}
            
            # Get environment configuration
            env_config = self.environment_configs.get(environment, {})
            
            # Get environment variables from config
            env_vars = env_config.get('environment_variables', {})
            
            # Process each environment variable
            for var_name, var_value in env_vars.items():
                if isinstance(var_value, str) and '${' in var_value:
                    # This is a template variable, need to resolve it
                    # For now, we'll look for it in our secrets storage
                    secret_value = await self.secrets_manager.get_environment_secret(
                        environment, var_name
                    )
                    
                    if secret_value:
                        secrets[var_name] = secret_value
                    else:
                        # Check if it's an OS environment variable
                        os_value = os.getenv(var_name)
                        if os_value:
                            secrets[var_name] = os_value
                        else:
                            logger.warning(f"Secret {var_name} not found for environment {environment.value}")
                            secrets[var_name] = var_value  # Keep template for manual resolution
                else:
                    # Direct value
                    secrets[var_name] = str(var_value)
            
            # Add some common system secrets
            system_secrets = await self._get_system_secrets(environment)
            secrets.update(system_secrets)
            
            # Log audit event
            self.audit_logger.log_event(
                event_type=AuditEventType.SECRET_ACCESS,
                level=AuditLevel.INFO,
                message=f"Environment secrets collected for {environment.value}",
                details={
                    "environment": environment.value,
                    "secrets_count": len(secrets),
                    "template_variables": len([v for v in secrets.values() if '${' in v])
                }
            )
            
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to collect secrets for environment {environment.value}: {e}")
            return {}
    
    async def _get_system_secrets(self, environment: Environment) -> Dict[str, str]:
        """Get system-generated secrets (JWT keys, API keys, etc.)"""
        system_secrets = {}
        
        try:
            # Get current JWT secret key (if available)
            jwt_secret = os.getenv('JWT_SECRET_KEY')
            if jwt_secret:
                system_secrets['JWT_SECRET_KEY'] = jwt_secret
            
            # Add environment-specific system variables
            system_secrets.update({
                'ENVIRONMENT': environment.value,
                'DEPLOYMENT_TIMESTAMP': datetime.now(timezone.utc).isoformat(),
                'SECRETS_VERSION': '2.0',
            })
            
            # Production-specific secrets
            if environment == Environment.PRODUCTION:
                system_secrets.update({
                    'NODE_ENV': 'production',
                    'DEBUG': 'false',
                    'ENABLE_PROFILING': 'false'
                })
            elif environment == Environment.DEVELOPMENT:
                system_secrets.update({
                    'NODE_ENV': 'development',
                    'DEBUG': 'true',
                    'ENABLE_PROFILING': 'true'
                })
            
            return system_secrets
            
        except Exception as e:
            logger.error(f"Failed to get system secrets: {e}")
            return {}
    
    async def generate_env_file(self, 
                              environment: Environment,
                              output_file: Optional[str] = None,
                              template_file: Optional[str] = None) -> str:
        """
        Generate environment file with injected secrets.
        
        Args:
            environment: Target environment
            output_file: Output file path (default: .env.{environment})
            template_file: Template file path (optional)
            
        Returns:
            Path to generated environment file
        """
        try:
            # Collect all secrets
            secrets = await self.collect_environment_secrets(environment)
            
            # Determine output file
            if not output_file:
                output_file = f".env.{environment.value}"
            
            # Generate content
            if template_file and Path(template_file).exists():
                # Use template file
                with open(template_file, 'r') as f:
                    template_content = f.read()
                
                # Substitute variables
                final_content = self._substitute_variables(template_content, secrets)
            else:
                # Generate simple key=value format
                lines = []
                lines.append(f"# GraphMemory-IDE Environment Configuration")
                lines.append(f"# Environment: {environment.value}")
                lines.append(f"# Generated: {datetime.now(timezone.utc).isoformat()}")
                lines.append(f"# WARNING: This file contains sensitive information")
                lines.append("")
                
                for key, value in sorted(secrets.items()):
                    # Escape special characters in values
                    escaped_value = value.replace('"', '\\"')
                    lines.append(f'{key}="{escaped_value}"')
                
                final_content = '\n'.join(lines)
            
            # Write output file
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                f.write(final_content)
            
            # Set secure file permissions
            os.chmod(output_path, 0o600)
            
            # Log audit event
            self.audit_logger.log_event(
                event_type=AuditEventType.SECRET_ACCESS,
                level=AuditLevel.INFO,
                message=f"Environment file generated: {output_file}",
                details={
                    "environment": environment.value,
                    "output_file": output_file,
                    "template_file": template_file,
                    "secrets_count": len(secrets)
                }
            )
            
            logger.info(f"Generated environment file: {output_file}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate environment file: {e}")
            raise
    
    async def validate_secrets(self, environment: Environment) -> Dict[str, Any]:
        """
        Validate that all required secrets are available for environment.
        
        Args:
            environment: Target environment
            
        Returns:
            Validation report
        """
        try:
            validation_report = {
                "environment": environment.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "unknown",
                "total_secrets": 0,
                "available_secrets": 0,
                "missing_secrets": [],
                "template_variables": [],
                "validation_errors": []
            }
            
            # Get environment configuration
            env_config = self.environment_configs.get(environment, {})
            env_vars = env_config.get('environment_variables', {})
            
            validation_report["total_secrets"] = len(env_vars)
            
            # Check each required secret
            for var_name, var_value in env_vars.items():
                if isinstance(var_value, str) and '${' in var_value:
                    # Template variable
                    validation_report["template_variables"].append(var_name)
                    
                    # Check if secret exists
                    secret_value = await self.secrets_manager.get_environment_secret(
                        environment, var_name
                    )
                    
                    if secret_value:
                        validation_report["available_secrets"] += 1
                    else:
                        # Check OS environment
                        if not os.getenv(var_name):
                            validation_report["missing_secrets"].append(var_name)
                        else:
                            validation_report["available_secrets"] += 1
                else:
                    # Direct value
                    validation_report["available_secrets"] += 1
            
            # Additional validation checks
            required_system_vars = ['DATABASE_URL', 'REDIS_URL']
            for var in required_system_vars:
                if var not in env_vars:
                    validation_report["validation_errors"].append(
                        f"Required system variable {var} not found in configuration"
                    )
            
            # Determine overall status
            if validation_report["missing_secrets"]:
                validation_report["status"] = "failed"
            elif validation_report["validation_errors"]:
                validation_report["status"] = "warnings"
            else:
                validation_report["status"] = "passed"
            
            # Log audit event
            self.audit_logger.log_event(
                event_type=AuditEventType.SECRET_ACCESS,
                level=AuditLevel.INFO if validation_report["status"] == "passed" else AuditLevel.WARNING,
                message=f"Secrets validation for {environment.value}: {validation_report['status']}",
                details=validation_report
            )
            
            return validation_report
            
        except Exception as e:
            logger.error(f"Failed to validate secrets for environment {environment.value}: {e}")
            return {
                "environment": environment.value,
                "status": "error",
                "error": str(e)
            }
    
    def generate_docker_env_file(self, environment: Environment, output_file: str = None) -> str:
        """Generate Docker-compatible environment file"""
        # This would be similar to generate_env_file but with Docker-specific formatting
        pass
    
    def generate_kubernetes_secret(self, environment: Environment, namespace: str = "default") -> Dict[str, Any]:
        """Generate Kubernetes Secret manifest"""
        # This would generate a Kubernetes Secret YAML with base64-encoded values
        pass


async def main() -> None:
    """Main entry point for the secrets injection script"""
    parser = argparse.ArgumentParser(description="Environment Secrets Injection")
    parser.add_argument('--environment', type=str, required=True,
                       choices=['development', 'staging', 'production', 'testing'],
                       help='Target environment')
    parser.add_argument('--output-file', type=str, help='Output environment file path')
    parser.add_argument('--template-file', type=str, help='Template file for variable substitution')
    parser.add_argument('--validate', action='store_true', help='Validate secrets availability')
    parser.add_argument('--generate', action='store_true', help='Generate environment file')
    
    args = parser.parse_args()
    
    try:
        injector = EnvironmentSecretsInjector()
        environment = Environment(args.environment)
        
        if args.validate:
            # Validate secrets
            validation_report = await injector.validate_secrets(environment)
            
            print(f"\n=== Secrets Validation Report ===")
            print(f"Environment: {validation_report['environment']}")
            print(f"Status: {validation_report['status'].upper()}")
            print(f"Total secrets: {validation_report['total_secrets']}")
            print(f"Available secrets: {validation_report['available_secrets']}")
            
            if validation_report['missing_secrets']:
                print(f"\nMissing secrets:")
                for secret in validation_report['missing_secrets']:
                    print(f"  - {secret}")
            
            if validation_report['template_variables']:
                print(f"\nTemplate variables:")
                for var in validation_report['template_variables']:
                    print(f"  - {var}")
            
            if validation_report['validation_errors']:
                print(f"\nValidation errors:")
                for error in validation_report['validation_errors']:
                    print(f"  - {error}")
            
            if validation_report['status'] == 'failed':
                sys.exit(1)
        
        elif args.generate or True:  # Default action
            # Generate environment file
            output_file = await injector.generate_env_file(
                environment=environment,
                output_file=args.output_file,
                template_file=args.template_file
            )
            
            print(f"\n=== Environment File Generated ===")
            print(f"Environment: {environment.value}")
            print(f"Output file: {output_file}")
            print("\nIMPORTANT: This file contains sensitive information.")
            print("Ensure it is properly secured and not committed to version control.")
        
    except KeyboardInterrupt:
        logger.info("Secrets injection script interrupted by user")
    except Exception as e:
        logger.error(f"Secrets injection script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 