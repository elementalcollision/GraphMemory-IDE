"""
Production Data Seeding for GraphMemory-IDE.

This module provides idempotent data seeding operations for production deployment.
All operations are designed to be safely run multiple times without side effects.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, delete, func
from passlib.context import CryptContext
import logging

# Import our models and configuration
from server.database_models import (
    User, UserSession, TelemetryEvent, AnalyticsQuery, 
    KuzuQuery, CollaborationSession, CollaborationParticipant,
    SystemMetrics, APIRequestLog
)
from server.core.config import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class DataSeeder:
    """Production data seeding manager"""
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        """Initialize seeder with database connection"""
        if not database_url:
            settings = get_settings()
            database_url = settings.get_database_url()
        
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10
        )
        self.async_session = async_sessionmaker(
            self.engine, 
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def close(self) -> None:
        """Close database connections"""
        await self.engine.dispose()

    async def seed_admin_user(self) -> User:
        """Create default admin user if not exists"""
        async with self.async_session() as session:
            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = result.scalar_one_or_none()
            
            if admin_user:
                logger.info("Admin user already exists")
                return admin_user
            
            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@graphmemory.local",
                full_name="System Administrator",
                hashed_password=pwd_context.hash("graphmemory_admin_2025"),
                is_active=True,
                is_superuser=True,
                roles=["admin", "user"],
                preferences={
                    "theme": "dark",
                    "notifications": True,
                    "analytics": True
                }
            )
            
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            logger.info(f"Created admin user: {admin_user.id}")
            return admin_user

    async def seed_demo_users(self) -> List[User]:
        """Create demo users for development/staging"""
        demo_users_data = [
            {
                "username": "demo_user",
                "email": "demo@graphmemory.local",
                "full_name": "Demo User",
                "roles": ["user"]
            },
            {
                "username": "analyst",
                "email": "analyst@graphmemory.local", 
                "full_name": "Data Analyst",
                "roles": ["user", "analyst"]
            },
            {
                "username": "researcher",
                "email": "researcher@graphmemory.local",
                "full_name": "Research Scientist",
                "roles": ["user", "researcher"]
            }
        ]
        
        created_users = []
        async with self.async_session() as session:
            for user_data in demo_users_data:
                # Check if user exists
                result = await session.execute(
                    select(User).where(User.username == user_data["username"])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    logger.info(f"Demo user {user_data['username']} already exists")
                    created_users.append(existing_user)
                    continue
                
                # Create demo user
                demo_user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    hashed_password=pwd_context.hash("demo_password_2025"),
                    is_active=True,
                    is_superuser=False,
                    roles=user_data["roles"],
                    preferences={
                        "theme": "light",
                        "notifications": True,
                        "analytics": False
                    }
                )
                
                session.add(demo_user)
                created_users.append(demo_user)
                logger.info(f"Created demo user: {user_data['username']}")
            
            await session.commit()
            
            # Refresh all users
            for user in created_users:
                if user.id:  # Already persisted
                    await session.refresh(user)
        
        return created_users

    async def seed_sample_telemetry(self, users: List[User], count: int = 100) -> None:
        """Seed sample telemetry events"""
        event_types = [
            "user_action", "system_event", "error", 
            "performance", "memory_operation", "graph_change"
        ]
        
        actions = [
            "create_entity", "edit_entity", "delete_entity",
            "search_query", "graph_navigation", "collaboration_join",
            "analytics_request", "export_data", "import_data"
        ]
        
        async with self.async_session() as session:
            # Check if telemetry already exists
            result = await session.execute(
                select(func.count(TelemetryEvent.id))
            )
            existing_count = result.scalar()
            
            if existing_count >= count:
                logger.info(f"Telemetry data already seeded ({existing_count} events)")
                return
            
            events_to_create = []
            for i in range(count - existing_count):
                user = users[i % len(users)] if users else None
                event_type = event_types[i % len(event_types)]
                action = actions[i % len(actions)]
                
                event = TelemetryEvent(
                    event_type=event_type,
                    user_id=user.id if user else None,
                    session_id=f"session_{i % 10}",
                    data={
                        "action": action,
                        "component": "ide_plugin",
                        "version": "1.0.0",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    event_metadata={
                        "browser": "cursor" if i % 2 == 0 else "vscode",
                        "platform": "darwin",
                        "plugin_version": "1.0.0"
                    },
                    duration_ms=50 + (i % 500)  # 50-550ms
                )
                events_to_create.append(event)
            
            if events_to_create:
                session.add_all(events_to_create)
                await session.commit()
                logger.info(f"Created {len(events_to_create)} telemetry events")

    async def seed_sample_queries(self, users: List[User], count: int = 50) -> None:
        """Seed sample analytics and Kuzu queries"""
        query_types = [
            "entity_analytics", "user_behavior", "performance_metrics",
            "collaboration_stats", "usage_patterns", "error_analysis"
        ]
        
        cypher_queries = [
            "MATCH (n:Entity) RETURN COUNT(n)",
            "MATCH (u:User)-[:CREATED]->(e:Entity) RETURN u.name, COUNT(e)",
            "MATCH (a:Entity)-[:RELATES_TO]->(b:Entity) RETURN a, b LIMIT 10",
            "MATCH (n:Entity) WHERE n.created_at > datetime() - duration('PT24H') RETURN n",
            "MATCH (u:User)-[:COLLABORATED_ON]->(s:Session) RETURN u, s"
        ]
        
        async with self.async_session() as session:
            # Analytics queries
            analytics_result = await session.execute(
                select(func.count(AnalyticsQuery.id))
            )
            existing_analytics = analytics_result.scalar()
            
            if existing_analytics < count // 2:
                analytics_to_create = []
                for i in range((count // 2) - existing_analytics):
                    user = users[i % len(users)] if users else None
                    query_type = query_types[i % len(query_types)]
                    
                    query = AnalyticsQuery(
                        query_type=query_type,
                        user_id=user.id if user else None,
                        parameters={
                            "aggregation": "count" if i % 2 == 0 else "sum",
                            "time_range": "24h",
                            "filters": {"active": True}
                        },
                        filters={"entity_type": "concept" if i % 3 == 0 else "relation"},
                        result_data={
                            "total": 100 + i,
                            "breakdown": {"concepts": 60 + i, "relations": 40 + i}
                        },
                        execution_time_ms=50 + (i % 200),
                        result_count=100 + i,
                        cache_key=f"analytics_{query_type}_{i}",
                        cache_expires_at=datetime.utcnow() + timedelta(hours=1)
                    )
                    analytics_to_create.append(query)
                
                if analytics_to_create:
                    session.add_all(analytics_to_create)
                    logger.info(f"Created {len(analytics_to_create)} analytics queries")
            
            # Kuzu queries
            kuzu_result = await session.execute(
                select(func.count(KuzuQuery.id))
            )
            existing_kuzu = kuzu_result.scalar()
            
            if existing_kuzu < count // 2:
                kuzu_to_create = []
                for i in range((count // 2) - existing_kuzu):
                    user = users[i % len(users)] if users else None
                    cypher_query = cypher_queries[i % len(cypher_queries)]
                    
                    query = KuzuQuery(
                        cypher_query=cypher_query,
                        user_id=user.id if user else None,
                        parameters={"limit": 100, "offset": 0},
                        is_read_only=True,
                        execution_time_ms=25 + (i % 100),
                        row_count=10 + (i % 50),
                        columns=["id", "name", "created_at"],
                        result_preview={
                            "sample_rows": [
                                {"id": f"entity_{i}", "name": f"Sample Entity {i}"}
                            ]
                        },
                        status="completed"
                    )
                    kuzu_to_create.append(query)
                
                if kuzu_to_create:
                    session.add_all(kuzu_to_create)
                    logger.info(f"Created {len(kuzu_to_create)} Kuzu queries")
            
            await session.commit()

    async def seed_system_metrics(self, count: int = 200) -> None:
        """Seed sample system metrics"""
        metric_names = [
            "cpu_usage", "memory_usage", "disk_usage", "network_io",
            "request_rate", "response_time", "error_rate", "active_users"
        ]
        
        components = [
            "web_server", "database", "cache", "graph_db",
            "analytics_engine", "collaboration_service"
        ]
        
        async with self.async_session() as session:
            result = await session.execute(
                select(func.count(SystemMetrics.id))
            )
            existing_count = result.scalar()
            
            if existing_count >= count:
                logger.info(f"System metrics already seeded ({existing_count} metrics)")
                return
            
            metrics_to_create = []
            settings = get_settings()
            environment = settings.ENVIRONMENT.value
            
            for i in range(count - existing_count):
                metric_name = metric_names[i % len(metric_names)]
                component = components[i % len(components)]
                
                # Generate realistic metric values
                if metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
                    value = 20 + (i % 60)  # 20-80%
                    unit = "percent"
                elif metric_name == "response_time":
                    value = 50 + (i % 200)  # 50-250ms
                    unit = "milliseconds"
                elif metric_name == "request_rate":
                    value = 10 + (i % 100)  # 10-110 req/sec
                    unit = "requests_per_second"
                else:
                    value = 1 + (i % 100)
                    unit = "count"
                
                metric = SystemMetrics(
                    metric_name=metric_name,
                    metric_value=value,
                    metric_unit=unit,
                    component=component,
                    environment=environment,
                    metric_metadata={
                        "collection_method": "prometheus",
                        "aggregation": "average",
                        "interval": "1m"
                    }
                )
                metrics_to_create.append(metric)
            
            if metrics_to_create:
                session.add_all(metrics_to_create)
                await session.commit()
                logger.info(f"Created {len(metrics_to_create)} system metrics")

    async def cleanup_test_data(self) -> None:
        """Remove test/demo data (for production cleanup)"""
        async with self.async_session() as session:
            # Delete demo users (keep admin)
            await session.execute(
                delete(User).where(User.username.in_(["demo_user", "analyst", "researcher"]))
            )
            
            # Delete old telemetry (keep last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            await session.execute(
                delete(TelemetryEvent).where(TelemetryEvent.created_at < cutoff_date)
            )
            
            # Delete old analytics queries (keep last 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            await session.execute(
                delete(AnalyticsQuery).where(AnalyticsQuery.created_at < cutoff_date)
            )
            
            await session.commit()
            logger.info("Cleaned up test/demo data")

    async def seed_all(self, include_demo: bool = True) -> None:
        """Run all seeding operations"""
        logger.info("Starting production data seeding...")
        
        try:
            # Create admin user
            admin_user = await self.seed_admin_user()
            users = [admin_user]
            
            # Create demo users if requested
            if include_demo:
                demo_users = await self.seed_demo_users()
                users.extend(demo_users)
            
            # Seed sample data
            await self.seed_sample_telemetry(users, count=500)
            await self.seed_sample_queries(users, count=100)
            await self.seed_system_metrics(count=1000)
            
            logger.info("Production data seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during data seeding: {e}")
            raise


async def main() -> None:
    """Main seeding function for direct execution"""
    seeder = DataSeeder()
    
    try:
        # Check environment
        settings = get_settings()
        is_production = settings.is_production()
        
        if is_production:
            logger.warning("Running in PRODUCTION mode - only essential data will be seeded")
            await seeder.seed_all(include_demo=False)
        else:
            logger.info("Running in DEVELOPMENT mode - including demo data")
            await seeder.seed_all(include_demo=True)
            
    finally:
        await seeder.close()


if __name__ == "__main__":
    asyncio.run(main()) 