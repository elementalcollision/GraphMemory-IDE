"""
Manual Migration Management for GraphMemory-IDE.

This module provides standalone migration utilities for when alembic auto-generation
is not available or when custom migration logic is needed.
"""

import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, inspect
from sqlalchemy.schema import CreateTable, DropTable
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manual migration management for development and testing"""
    
    def __init__(self, database_url: str):
        """Initialize with database connection"""
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=True)
        self.async_session = async_sessionmaker(self.engine, class_=AsyncSession)

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()

    async def check_database_connection(self) -> bool:
        """Test database connectivity"""
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("✅ Database connection successful")
                return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    async def create_database_if_not_exists(self, database_name: str = "graphmemory_dev"):
        """Create database if it doesn't exist"""
        # Extract connection params without database name
        if "postgresql" in self.database_url:
            base_url = self.database_url.rsplit('/', 1)[0] + "/postgres"
            
            try:
                temp_engine = create_async_engine(base_url)
                async with temp_engine.connect() as conn:
                    # Set autocommit mode
                    await conn.execute(text("COMMIT"))
                    
                    # Check if database exists
                    result = await conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                        {"db_name": database_name}
                    )
                    
                    if not result.fetchone():
                        # Create database
                        await conn.execute(text(f"CREATE DATABASE {database_name}"))
                        logger.info(f"✅ Created database: {database_name}")
                    else:
                        logger.info(f"Database {database_name} already exists")
                
                await temp_engine.dispose()
                
            except Exception as e:
                logger.error(f"❌ Failed to create database: {e}")
                raise

    async def get_table_list(self) -> List[str]:
        """Get list of existing tables"""
        try:
            async with self.engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                tables = inspector.get_table_names()
                logger.info(f"Found {len(tables)} tables: {tables}")
                return tables
        except Exception as e:
            logger.error(f"❌ Failed to get table list: {e}")
            return []

    async def create_schema_tables(self) -> bool:
        """Create all schema tables manually"""
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                full_name VARCHAR(255),
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_superuser BOOLEAN DEFAULT FALSE,
                roles JSONB DEFAULT '[]'::jsonb,
                preferences JSONB DEFAULT '{}'::jsonb,
                last_login_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_users_username_active ON users(username, is_active)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_users_email_active ON users(email, is_active)
            """,
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                session_token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                ip_address VARCHAR(45),
                user_agent TEXT,
                location_data JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_token_active ON user_sessions(session_token, is_active)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON user_sessions(user_id, is_active, expires_at)
            """,
            """
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                event_type VARCHAR(50) NOT NULL,
                user_id UUID REFERENCES users(id),
                session_id VARCHAR(255),
                data JSONB DEFAULT '{}'::jsonb,
                event_metadata JSONB DEFAULT '{}'::jsonb,
                duration_ms INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_telemetry_type_created ON telemetry_events(event_type, created_at)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_telemetry_user_created ON telemetry_events(user_id, created_at)
            """,
            """
            CREATE TABLE IF NOT EXISTS analytics_queries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query_type VARCHAR(100) NOT NULL,
                user_id UUID REFERENCES users(id),
                parameters JSONB DEFAULT '{}'::jsonb,
                filters JSONB DEFAULT '{}'::jsonb,
                result_data JSONB DEFAULT '{}'::jsonb,
                execution_time_ms INTEGER NOT NULL,
                result_count INTEGER DEFAULT 0,
                cache_key VARCHAR(255) UNIQUE,
                cache_expires_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_analytics_type_created ON analytics_queries(query_type, created_at)
            """,
            """
            CREATE TABLE IF NOT EXISTS kuzu_queries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                cypher_query TEXT NOT NULL,
                user_id UUID REFERENCES users(id),
                parameters JSONB DEFAULT '{}'::jsonb,
                is_read_only BOOLEAN DEFAULT TRUE,
                execution_time_ms INTEGER NOT NULL,
                row_count INTEGER DEFAULT 0,
                columns JSONB DEFAULT '[]'::jsonb,
                result_preview JSONB DEFAULT '{}'::jsonb,
                error_message TEXT,
                status VARCHAR(20) DEFAULT 'completed',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT ck_kuzu_status CHECK (status IN ('pending', 'completed', 'failed', 'timeout'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS system_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                metric_name VARCHAR(100) NOT NULL,
                metric_value FLOAT NOT NULL,
                metric_unit VARCHAR(20) NOT NULL,
                component VARCHAR(50) NOT NULL,
                environment VARCHAR(20) NOT NULL,
                metric_metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_metrics_name_component_created ON system_metrics(metric_name, component, created_at)
            """,
            """
            CREATE TABLE IF NOT EXISTS api_request_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                method VARCHAR(10) NOT NULL,
                path VARCHAR(500) NOT NULL,
                status_code INTEGER NOT NULL,
                user_id UUID REFERENCES users(id),
                ip_address VARCHAR(45),
                user_agent TEXT,
                duration_ms FLOAT NOT NULL,
                request_size INTEGER,
                response_size INTEGER,
                headers JSONB DEFAULT '{}'::jsonb,
                error_details JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_requests_method_status_created ON api_request_logs(method, status_code, created_at)
            """
        ]
        
        try:
            async with self.engine.begin() as conn:
                for i, statement in enumerate(sql_statements):
                    try:
                        await conn.execute(text(statement))
                        logger.info(f"✅ Executed statement {i+1}/{len(sql_statements)}")
                    except Exception as e:
                        logger.error(f"❌ Failed to execute statement {i+1}: {e}")
                        logger.error(f"Statement: {statement[:100]}...")
                        raise
                
                logger.info("✅ All schema tables created successfully")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create schema tables: {e}")
            return False

    async def drop_all_tables(self) -> bool:
        """Drop all tables (for development reset)"""
        tables_to_drop = [
            "api_request_logs",
            "system_metrics", 
            "kuzu_queries",
            "analytics_queries",
            "telemetry_events",
            "user_sessions",
            "users"
        ]
        
        try:
            async with self.engine.begin() as conn:
                for table in tables_to_drop:
                    try:
                        await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                        logger.info(f"✅ Dropped table: {table}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to drop table {table}: {e}")
                
                logger.info("✅ All tables dropped")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to drop tables: {e}")
            return False

    async def seed_admin_user(self) -> bool:
        """Create admin user with SQL"""
        admin_sql = """
        INSERT INTO users (username, email, full_name, hashed_password, is_active, is_superuser, roles, preferences)
        VALUES ('admin', 'admin@graphmemory.local', 'System Administrator', 
                '$2b$12$LQv3c1yqBWVHxkd0LQ1Ol.a7h9/XHW5B5HQpHzM3zK.Zv.M2e8mYG',  -- password: admin
                TRUE, TRUE, 
                '["admin", "user"]'::jsonb, 
                '{"theme": "dark", "notifications": true}'::jsonb)
        ON CONFLICT (username) DO NOTHING
        """
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(admin_sql))
                if result.rowcount > 0:
                    logger.info("✅ Created admin user")
                else:
                    logger.info("Admin user already exists")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create admin user: {e}")
            return False

    async def run_full_migration(self, reset: bool = False) -> bool:
        """Run complete migration process"""
        logger.info("🚀 Starting database migration...")
        
        try:
            # Test connection
            if not await self.check_database_connection():
                logger.error("Cannot proceed without database connection")
                return False
            
            # Reset if requested
            if reset:
                logger.warning("⚠️  Resetting database (dropping all tables)")
                await self.drop_all_tables()
            
            # Create tables
            logger.info("📊 Creating schema tables...")
            if not await self.create_schema_tables():
                return False
            
            # Seed admin user
            logger.info("👤 Creating admin user...")
            if not await self.seed_admin_user():
                return False
            
            logger.info("✅ Database migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False


async def main():
    """Main migration function"""
    # Default development database URL
    database_url = "postgresql+asyncpg://graphmemory:graphmemory@localhost:5432/graphmemory_dev"
    
    # Check if we should reset
    import sys
    reset = "--reset" in sys.argv
    
    manager = MigrationManager(database_url)
    
    try:
        success = await manager.run_full_migration(reset=reset)
        if success:
            logger.info("🎉 Migration completed successfully!")
        else:
            logger.error("💥 Migration failed!")
            sys.exit(1)
            
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main()) 