"""User onboarding schema additions

Revision ID: 004_user_onboarding
Revises: 003_enhanced_analytics_schema
Create Date: 2025-06-01 12:41:19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_user_onboarding'
down_revision = '003_enhanced_analytics_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add user onboarding related tables"""
    
    # Email verification tokens table
    op.create_table(
        'email_verification_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),  # Support IPv6
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('idx_email_verification_tokens_user_id', 'user_id'),
        sa.Index('idx_email_verification_tokens_token_hash', 'token_hash'),
        sa.Index('idx_email_verification_tokens_expires_at', 'expires_at'),
    )
    
    # Onboarding progress tracking table
    op.create_table(
        'user_onboarding_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(100), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('step_order', sa.Integer, nullable=True),
        sa.Column('skipped', sa.Boolean, nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('idx_user_onboarding_progress_user_id', 'user_id'),
        sa.Index('idx_user_onboarding_progress_step_name', 'step_name'),
        sa.UniqueConstraint('user_id', 'step_name', name='uq_user_onboarding_step'),
    )
    
    # Workspace setup table
    op.create_table(
        'workspace_setup',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),  # Creator user
        sa.Column('setup_completed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('setup_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('workspace_name', sa.String(255), nullable=True),
        sa.Column('workspace_description', sa.Text, nullable=True),
        sa.Column('workspace_type', sa.String(50), nullable=True),  # personal, team, enterprise
        sa.Column('onboarding_flow', sa.String(50), nullable=True),  # guided, self-service, import
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('idx_workspace_setup_tenant_id', 'tenant_id'),
        sa.Index('idx_workspace_setup_user_id', 'user_id'),
        sa.UniqueConstraint('tenant_id', name='uq_workspace_setup_tenant'),
    )
    
    # Team invitations table
    op.create_table(
        'team_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invited_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),  # viewer, editor, collaborator, admin
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, accepted, expired, revoked
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('personal_message', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['accepted_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_team_invitations_tenant_id', 'tenant_id'),
        sa.Index('idx_team_invitations_email', 'email'),
        sa.Index('idx_team_invitations_token_hash', 'token_hash'),
        sa.Index('idx_team_invitations_status', 'status'),
        sa.Index('idx_team_invitations_expires_at', 'expires_at'),
    )
    
    # User preferences table for onboarding customization
    op.create_table(
        'user_onboarding_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('show_tooltips', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('show_guided_tours', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('email_notifications_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('theme_preference', sa.String(20), nullable=False, server_default='auto'),  # light, dark, auto
        sa.Column('experience_level', sa.String(20), nullable=False, server_default='intermediate'),  # beginner, intermediate, advanced
        sa.Column('preferred_features', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('dismissed_hints', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('idx_user_onboarding_preferences_user_id', 'user_id'),
        sa.UniqueConstraint('user_id', name='uq_user_onboarding_preferences_user'),
    )
    
    # Add email verification status to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('registration_completed', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add indexes for the new user columns
    op.create_index('idx_users_email_verified', 'users', ['email_verified'])
    op.create_index('idx_users_registration_completed', 'users', ['registration_completed'])
    op.create_index('idx_users_onboarding_completed', 'users', ['onboarding_completed'])


def downgrade() -> None:
    """Remove user onboarding related tables and columns"""
    
    # Drop indexes first
    op.drop_index('idx_users_onboarding_completed', 'users')
    op.drop_index('idx_users_registration_completed', 'users')
    op.drop_index('idx_users_email_verified', 'users')
    
    # Drop columns from users table
    op.drop_column('users', 'onboarding_completed_at')
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'registration_completed')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')
    
    # Drop tables in reverse order
    op.drop_table('user_onboarding_preferences')
    op.drop_table('team_invitations')
    op.drop_table('workspace_setup')
    op.drop_table('user_onboarding_progress')
    op.drop_table('email_verification_tokens') 