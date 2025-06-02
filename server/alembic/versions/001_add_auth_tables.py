"""Add authentication tables for SSO and MFA

Revision ID: 001_add_auth_tables
Revises: 
Create Date: 2025-06-01 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_auth_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add authentication tables."""
    
    # SSO Providers table
    op.create_table(
        'sso_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('enabled', sa.Boolean, default=True, nullable=False),
        
        # SAML specific fields
        sa.Column('sso_url', sa.String(500)),
        sa.Column('slo_url', sa.String(500)),
        sa.Column('entity_id', sa.String(500)),
        sa.Column('x509_cert', sa.Text),
        
        # OAuth2/OIDC specific fields  
        sa.Column('client_id', sa.String(255)),
        sa.Column('client_secret', sa.String(255)),
        sa.Column('auth_url', sa.String(500)),
        sa.Column('token_url', sa.String(500)),
        sa.Column('userinfo_url', sa.String(500)),
        sa.Column('redirect_uri', sa.String(500)),
        sa.Column('scopes', sa.String(500)),
        
        # Configuration
        sa.Column('metadata', sa.JSON),
        sa.Column('attribute_mapping', sa.JSON),
        sa.Column('role_mapping', sa.JSON),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True))
    )
    
    # MFA Devices table
    op.create_table(
        'mfa_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_type', sa.String(50), nullable=False),
        sa.Column('device_name', sa.String(255), nullable=False),
        sa.Column('device_identifier', sa.String(255)),
        sa.Column('secret_key', sa.Text),
        sa.Column('backup_tokens', sa.Text),
        sa.Column('is_verified', sa.Boolean, default=False, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('verification_attempts', sa.String(10), default='0'),
        sa.Column('last_used', sa.DateTime),
        sa.Column('verified_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        
        # Add foreign key when users table exists
        # sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    
    # Backup Codes table
    op.create_table(
        'backup_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code_hash', sa.String(255), nullable=False),
        sa.Column('is_used', sa.Boolean, default=False, nullable=False),
        sa.Column('used_at', sa.DateTime),
        sa.Column('used_from_ip', sa.String(45)),
        sa.Column('created_at', sa.DateTime, nullable=False),
        
        # Add foreign key when users table exists
        # sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    
    # Create indexes for performance
    op.create_index('idx_sso_providers_name', 'sso_providers', ['name'])
    op.create_index('idx_sso_providers_type', 'sso_providers', ['type'])
    op.create_index('idx_sso_providers_enabled', 'sso_providers', ['enabled'])
    
    op.create_index('idx_mfa_devices_user_id', 'mfa_devices', ['user_id'])
    op.create_index('idx_mfa_devices_type', 'mfa_devices', ['device_type'])
    op.create_index('idx_mfa_devices_verified', 'mfa_devices', ['is_verified'])
    
    op.create_index('idx_backup_codes_user_id', 'backup_codes', ['user_id'])
    op.create_index('idx_backup_codes_used', 'backup_codes', ['is_used'])


def downgrade():
    """Remove authentication tables."""
    
    # Drop indexes
    op.drop_index('idx_backup_codes_used')
    op.drop_index('idx_backup_codes_user_id')
    op.drop_index('idx_mfa_devices_verified')
    op.drop_index('idx_mfa_devices_type')
    op.drop_index('idx_mfa_devices_user_id')
    op.drop_index('idx_sso_providers_enabled')
    op.drop_index('idx_sso_providers_type')
    op.drop_index('idx_sso_providers_name')
    
    # Drop tables
    op.drop_table('backup_codes')
    op.drop_table('mfa_devices')
    op.drop_table('sso_providers') 