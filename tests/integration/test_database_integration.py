"""
Integration Tests for Multi-Database System

Tests the integration between PostgreSQL, Kuzu graph database, and synchronization:
- Database connectivity and health checks
- Schema creation and validation
- Data synchronization between systems
- Performance benchmarks
- Error handling and recovery
"""

import pytest
import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
from pathlib import Path

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text, select

# Test fixtures and utilities
from tests.fixtures.database_fixtures import (
    async_session, postgres_engine, test_database_url,
    sample_users, sample_telemetry_events
)

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Integration tests for multi-database system"""
    
    async def test_postgresql_connectivity(self, async_session: AsyncSession):
        """Test PostgreSQL database connectivity"""
        # Test basic connection
        result = await async_session.execute(text("SELECT 1 as test"))
        assert result.scalar() == 1
        
        # Test database version
        result = await async_session.execute(text("SELECT version()"))
        version = result.scalar()
        assert "PostgreSQL" in version
        
        logger.info(f"PostgreSQL connected: {version}")
    
    async def test_postgresql_schema_creation(self, async_session: AsyncSession):
        """Test PostgreSQL schema creation and validation"""
        # Check if all required tables exist
        expected_tables = [
            'users', 'user_sessions', 'telemetry_events',
            'analytics_queries', 'kuzu_queries', 'collaboration_sessions',
            'collaboration_participants', 'system_metrics', 'api_request_logs'
        ]
        
        for table_name in expected_tables:
            result = await async_session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """))
            exists = result.scalar()
            assert exists, f"Table {table_name} does not exist"
        
        logger.info("All PostgreSQL tables exist")
    
    async def test_postgresql_indexes(self, async_session: AsyncSession):
        """Test PostgreSQL index creation and validation"""
        # Check for important indexes
        result = await async_session.execute(text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """))
        
        indexes = result.fetchall()
        index_count = len(indexes)
        
        # Should have at least primary key indexes plus additional ones
        assert index_count >= 9, f"Expected at least 9 indexes, found {index_count}"
        
        logger.info(f"Found {index_count} indexes in PostgreSQL")
    
    @pytest.mark.skipif(not pytest.kuzu_available, reason="Kuzu not available")
    async def test_kuzu_connectivity(self):
        """Test Kuzu graph database connectivity"""
        try:
            from server.graph_database import get_graph_database
            
            graph_db = await get_graph_database()
            assert graph_db is not None
            assert graph_db.is_healthy()
            
            # Test basic query
            result = graph_db.query_engine.execute_query("MATCH (n) RETURN count(n) as node_count")
            assert result.success
            
            logger.info("Kuzu graph database connected successfully")
            
        except ImportError:
            pytest.skip("Kuzu dependencies not available")
    
    @pytest.mark.skipif(not pytest.kuzu_available, reason="Kuzu not available")
    async def test_kuzu_schema_creation(self):
        """Test Kuzu graph database schema creation"""
        try:
            from server.graph_database import get_graph_database
            
            graph_db = await get_graph_database()
            
            # Check schema health
            health_status = await graph_db.health_checker.check_health()
            assert health_status["status"] == "healthy"
            
            # Verify expected tables exist
            schema_check = health_status["checks"]["schema_integrity"]
            assert schema_check["healthy"]
            
            expected_tables = {"User", "Project", "Memory", "OWNS", "COLLABORATES", "CONTAINS", "RELATES_TO", "ACCESSED_BY"}
            found_tables = set(schema_check["found_tables"])
            
            missing_tables = expected_tables - found_tables
            assert len(missing_tables) == 0, f"Missing tables: {missing_tables}"
            
            logger.info("Kuzu schema validation passed")
            
        except ImportError:
            pytest.skip("Kuzu dependencies not available")
    
    async def test_data_insertion_postgresql(self, async_session: AsyncSession, sample_users: List[Dict]):
        """Test data insertion into PostgreSQL"""
        from server.database_models import User
        
        # Insert test users
        for user_data in sample_users:
            user = User(**user_data)
            async_session.add(user)
        
        await async_session.commit()
        
        # Verify insertion
        result = await async_session.execute(select(User))
        users = result.scalars().all()
        
        assert len(users) >= len(sample_users)
        
        logger.info(f"Inserted {len(sample_users)} users into PostgreSQL")
    
    @pytest.mark.skipif(not pytest.kuzu_available, reason="Kuzu not available")
    async def test_data_insertion_kuzu(self):
        """Test data insertion into Kuzu graph database"""
        try:
            from server.graph_database import get_graph_database
            
            graph_db = await get_graph_database()
            
            # Insert test user node
            test_user = {
                'id': str(uuid.uuid4()),
                'username': 'test_user',
                'email': 'test@example.com',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            query = """
            CREATE (u:User {
                id: $id,
                username: $username,
                email: $email,
                created_at: $created_at
            })
            """
            
            result = graph_db.query_engine.execute_query(query, test_user)
            assert result.success, f"Failed to insert user: {result.error}"
            
            # Verify insertion
            verify_query = "MATCH (u:User {id: $id}) RETURN u"
            verify_result = graph_db.query_engine.execute_query(verify_query, {'id': test_user['id']})
            assert verify_result.success
            assert verify_result.row_count == 1
            
            logger.info("Successfully inserted and verified user in Kuzu")
            
        except ImportError:
            pytest.skip("Kuzu dependencies not available")
    
    @pytest.mark.skipif(not pytest.kuzu_available, reason="Kuzu not available")
    async def test_database_synchronization(self, async_session: AsyncSession):
        """Test data synchronization between PostgreSQL and Kuzu"""
        try:
            from server.database_sync import get_database_synchronizer
            from server.database_models import User
            
            # Create test user in PostgreSQL
            test_user_data = {
                'id': uuid.uuid4(),
                'username': 'sync_test_user',
                'email': 'sync_test@example.com',
                'role': 'user',
                'is_active': True,
                'preferences': {'theme': 'dark'},
                'created_at': datetime.now(timezone.utc)
            }
            
            user = User(**test_user_data)
            async_session.add(user)
            await async_session.commit()
            
            # Start synchronization
            synchronizer = await get_database_synchronizer()
            await synchronizer.start()
            
            # Wait for sync to process
            await asyncio.sleep(2)
            
            # Check if user was synced to Kuzu
            from server.graph_database import get_graph_database
            graph_db = await get_graph_database()
            
            verify_query = "MATCH (u:User {id: $id}) RETURN u"
            result = graph_db.query_engine.execute_query(verify_query, {'id': str(test_user_data['id'])})
            
            # Stop synchronization
            await synchronizer.stop()
            
            assert result.success, f"Sync verification failed: {result.error}"
            assert result.row_count == 1, "User not found in graph database after sync"
            
            logger.info("Database synchronization test passed")
            
        except ImportError:
            pytest.skip("Synchronization dependencies not available")
    
    async def test_transaction_handling(self, async_session: AsyncSession):
        """Test transaction handling and rollback"""
        from server.database_models import User
        
        # Test successful transaction
        user1 = User(
            id=uuid.uuid4(),
            username='tx_user1',
            email='tx1@example.com',
            role='user',
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user1)
        await async_session.commit()
        
        # Verify user was created
        result = await async_session.execute(select(User).where(User.username == 'tx_user1'))
        assert result.scalar_one_or_none() is not None
        
        # Test transaction rollback
        try:
            # Start a transaction that will fail
            user2 = User(
                id=uuid.uuid4(),
                username='tx_user2',
                email='invalid_email_that_should_fail_constraint',  # This might cause issues
                role='user',
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            
            async_session.add(user2)
            
            # Force a constraint violation
            await async_session.execute(text("INSERT INTO users (id, username, email) VALUES (NULL, NULL, NULL)"))
            await async_session.commit()
            
        except Exception:
            # Expected to fail, rollback should occur
            await async_session.rollback()
        
        # Verify rollback worked
        result = await async_session.execute(select(User).where(User.username == 'tx_user2'))
        assert result.scalar_one_or_none() is None
        
        logger.info("Transaction handling test passed")
    
    async def test_performance_benchmarks(self, async_session: AsyncSession):
        """Test performance benchmarks for database operations"""
        from server.database_models import TelemetryEvent
        
        # Benchmark: Bulk insert performance
        start_time = time.time()
        
        events = []
        for i in range(100):
            event = TelemetryEvent(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                event_type='test_event',
                event_data={'index': i},
                timestamp=datetime.now(timezone.utc),
                session_id=uuid.uuid4(),
                ip_address='127.0.0.1',
                user_agent='test-agent'
            )
            events.append(event)
        
        async_session.add_all(events)
        await async_session.commit()
        
        insert_time = time.time() - start_time
        
        # Benchmark: Query performance
        start_time = time.time()
        
        result = await async_session.execute(
            select(TelemetryEvent)
            .where(TelemetryEvent.event_type == 'test_event')
            .limit(50)
        )
        
        fetched_events = result.scalars().all()
        query_time = time.time() - start_time
        
        # Performance assertions
        assert insert_time < 5.0, f"Bulk insert took too long: {insert_time:.3f}s"
        assert query_time < 1.0, f"Query took too long: {query_time:.3f}s"
        assert len(fetched_events) == 50
        
        logger.info(f"Performance: Insert {len(events)} events in {insert_time:.3f}s, Query in {query_time:.3f}s")
    
    async def test_concurrent_operations(self, async_session: AsyncSession):
        """Test concurrent database operations"""
        from server.database_models import User
        
        async def create_users(session: AsyncSession, start_idx: int, count: int):
            """Helper function to create users concurrently"""
            users = []
            for i in range(count):
                user = User(
                    id=uuid.uuid4(),
                    username=f'concurrent_user_{start_idx}_{i}',
                    email=f'concurrent_{start_idx}_{i}@example.com',
                    role='user',
                    is_active=True,
                    created_at=datetime.now(timezone.utc)
                )
                users.append(user)
            
            session.add_all(users)
            await session.commit()
            return len(users)
        
        # Create multiple concurrent sessions
        from server.core.database import get_async_session
        
        tasks = []
        for i in range(3):
            async with get_async_session() as session:
                task = asyncio.create_task(create_users(session, i, 10))
                tasks.append(task)
        
        # Wait for all concurrent operations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        successful_operations = [r for r in results if isinstance(r, int)]
        assert len(successful_operations) == 3, "Not all concurrent operations succeeded"
        
        total_users_created = sum(successful_operations)
        assert total_users_created == 30, f"Expected 30 users, created {total_users_created}"
        
        logger.info(f"Concurrent operations test passed: {total_users_created} users created")
    
    async def test_error_handling_and_recovery(self, async_session: AsyncSession):
        """Test error handling and recovery mechanisms"""
        from server.database_models import User
        
        # Test duplicate key error handling
        user_id = uuid.uuid4()
        
        user1 = User(
            id=user_id,
            username='error_test_user',
            email='error_test@example.com',
            role='user',
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user1)
        await async_session.commit()
        
        # Try to insert duplicate
        try:
            user2 = User(
                id=user_id,  # Same ID - should cause conflict
                username='error_test_user2',
                email='error_test2@example.com',
                role='user',
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            
            async_session.add(user2)
            await async_session.commit()
            
            # Should not reach here
            assert False, "Expected duplicate key error"
            
        except sqlalchemy.exc.IntegrityError:
            # Expected error
            await async_session.rollback()
            logger.info("Duplicate key error handled correctly")
        
        # Test connection recovery
        try:
            # Force a bad query
            await async_session.execute(text("SELECT * FROM non_existent_table"))
            assert False, "Expected error for non-existent table"
            
        except sqlalchemy.exc.ProgrammingError:
            # Expected error
            await async_session.rollback()
            logger.info("Connection recovery test passed")
        
        # Verify session is still usable
        result = await async_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
        logger.info("Error handling and recovery test passed")
    
    async def test_data_consistency(self, async_session: AsyncSession):
        """Test data consistency across operations"""
        from server.database_models import User, TelemetryEvent
        
        # Create user
        user = User(
            id=uuid.uuid4(),
            username='consistency_user',
            email='consistency@example.com',
            role='user',
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        await async_session.flush()  # Flush to get the ID
        
        # Create related telemetry events
        events = []
        for i in range(5):
            event = TelemetryEvent(
                id=uuid.uuid4(),
                user_id=user.id,
                event_type='consistency_test',
                event_data={'test_index': i},
                timestamp=datetime.now(timezone.utc),
                session_id=uuid.uuid4(),
                ip_address='127.0.0.1',
                user_agent='consistency-test'
            )
            events.append(event)
        
        async_session.add_all(events)
        await async_session.commit()
        
        # Verify consistency
        user_count = await async_session.execute(
            select(sqlalchemy.func.count(User.id)).where(User.username == 'consistency_user')
        )
        assert user_count.scalar() == 1
        
        event_count = await async_session.execute(
            select(sqlalchemy.func.count(TelemetryEvent.id)).where(TelemetryEvent.user_id == user.id)
        )
        assert event_count.scalar() == 5
        
        logger.info("Data consistency test passed")

@pytest.mark.asyncio
class TestDatabaseHealth:
    """Health check tests for database systems"""
    
    async def test_postgresql_health_check(self, async_session: AsyncSession):
        """Test PostgreSQL health check functionality"""
        # Basic connectivity
        result = await async_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
        # Check database stats
        result = await async_session.execute(text("""
            SELECT 
                count(*) as table_count
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        
        table_count = result.scalar()
        assert table_count >= 8, f"Expected at least 8 tables, found {table_count}"
        
        # Check active connections
        result = await async_session.execute(text("""
            SELECT count(*) as connection_count
            FROM pg_stat_activity
            WHERE state = 'active'
        """))
        
        connection_count = result.scalar()
        assert connection_count >= 1, "No active connections found"
        
        logger.info(f"PostgreSQL health check passed: {table_count} tables, {connection_count} connections")
    
    @pytest.mark.skipif(not pytest.kuzu_available, reason="Kuzu not available")
    async def test_kuzu_health_check(self):
        """Test Kuzu graph database health check"""
        try:
            from server.graph_database import get_graph_database
            
            graph_db = await get_graph_database()
            health_status = await graph_db.health_checker.check_health()
            
            assert health_status["status"] == "healthy"
            assert "checks" in health_status
            assert "connection_pool" in health_status["checks"]
            assert "database_access" in health_status["checks"]
            assert "schema_integrity" in health_status["checks"]
            
            # Verify each check passed
            for check_name, check_result in health_status["checks"].items():
                assert check_result["healthy"], f"Health check failed: {check_name}"
            
            logger.info("Kuzu health check passed")
            
        except ImportError:
            pytest.skip("Kuzu dependencies not available")
    
    async def test_system_resource_monitoring(self):
        """Test system resource monitoring capabilities"""
        import psutil
        
        # Check system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Basic resource checks
        assert cpu_percent >= 0 and cpu_percent <= 100
        assert memory.percent >= 0 and memory.percent <= 100
        assert disk.percent >= 0 and disk.percent <= 100
        
        # Log resource usage
        logger.info(f"System resources - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%")
        
        # Performance thresholds for CI/CD
        if cpu_percent > 90:
            logger.warning(f"High CPU usage: {cpu_percent}%")
        
        if memory.percent > 90:
            logger.warning(f"High memory usage: {memory.percent}%")
        
        if disk.percent > 90:
            logger.warning(f"High disk usage: {disk.percent}%")

# Pytest configuration and fixtures
def pytest_configure(config):
    """Configure pytest for database integration tests"""
    # Check if Kuzu is available
    try:
        import kuzu
        pytest.kuzu_available = True
    except ImportError:
        pytest.kuzu_available = False
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v", "--tb=short"]) 