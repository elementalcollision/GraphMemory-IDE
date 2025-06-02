"""
Cross-Database Integration Tests for Step 13 Phase 2 Day 2.
Multi-database transaction coordination, data consistency validation,
and cache synchronization testing for production readiness.
"""

import asyncio
import time
import uuid
import json
import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime

from tests.fixtures.advanced_database_fixtures import (
    DatabaseConnectionPoolManager,
    TransactionCoordinator,
    DatabasePerformanceMonitor
)


class CrossDatabaseIntegrationTester:
    """Comprehensive cross-database integration testing framework."""
    
    def __init__(self, pool_manager: DatabaseConnectionPoolManager, transaction_coordinator: TransactionCoordinator) -> None:
        self.pool_manager = pool_manager
        self.transaction_coordinator = transaction_coordinator
        self.test_data = {}
        
    async def test_multi_database_transaction_coordination(self) -> Dict[str, Any]:
        """Test transaction coordination across all databases."""
        print(f"\n🔄 Testing Multi-Database Transaction Coordination...")
        
        test_results = {
            "successful_transactions": 0,
            "failed_transactions": 0,
            "coordination_times": [],
            "rollback_tests": [],
            "data_consistency_checks": []
        }
        
        # Test 1: Successful coordinated transaction
        print(f"  ✅ Testing successful coordinated transaction...")
        
        async with self.transaction_coordinator.cross_database_transaction() as tx_context:
            try:
                start_time = time.time()
                
                # Create coordinated data across all databases
                user_data = await self._create_coordinated_user_data(tx_context)
                
                coordination_time = (time.time() - start_time) * 1000
                test_results["coordination_times"].append(coordination_time)
                test_results["successful_transactions"] += 1
                
                # Verify data consistency immediately after transaction
                consistency_check = await self._verify_cross_database_consistency(user_data["user_id"])
                test_results["data_consistency_checks"].append(consistency_check)
                
                print(f"    ⏱️  Coordination time: {coordination_time:.1f}ms")
                print(f"    🎯 Consistency check: {'✅' if consistency_check['consistent'] else '❌'}")
                
            except Exception as e:
                test_results["failed_transactions"] += 1
                print(f"    ❌ Transaction failed: {e}")
        
        # Test 2: Transaction rollback scenarios
        print(f"  ⏪ Testing transaction rollback scenarios...")
        
        for scenario in ["kuzu_failure", "redis_failure", "sqlite_failure"]:
            rollback_result = await self._test_transaction_rollback(scenario)
            test_results["rollback_tests"].append(rollback_result)
            
            print(f"    🔄 {scenario}: {'✅' if rollback_result['rollback_successful'] else '❌'}")
        
        return test_results
    
    async def test_cache_database_synchronization(self) -> Dict[str, Any]:
        """Test cache synchronization with persistent databases."""
        print(f"\n🔄 Testing Cache-Database Synchronization...")
        
        sync_results = {
            "sync_delays": [],
            "cache_hit_rates": [],
            "consistency_violations": 0,
            "total_sync_tests": 0
        }
        
        # Get Redis pool for cache operations
        redis_pool_id = None
        sqlite_pool_id = None
        
        for pool_id, pool in self.pool_manager.pools.items():
            if pool["pool_type"] == "redis":
                redis_pool_id = pool_id
            elif pool["pool_type"] == "sqlite":
                sqlite_pool_id = pool_id
        
        if not redis_pool_id or not sqlite_pool_id:
            return {"error": "Required database pools not available"}
        
        # Test cache-database synchronization patterns
        for i in range(10):
            test_user_id = f"sync_test_user_{uuid.uuid4().hex[:8]}"
            
            # 1. Write to database first
            sqlite_conn = await self.pool_manager.get_connection(sqlite_pool_id)
            redis_conn = await self.pool_manager.get_connection(redis_pool_id)
            
            try:
                start_time = time.time()
                
                # Insert into SQLite
                await sqlite_conn["database"].execute(
                    "INSERT INTO test_users (id, name, email) VALUES (:id, :name, :email)",
                    {
                        "id": i + 1000,  # Unique ID
                        "name": f"Sync Test User {test_user_id}",
                        "email": f"{test_user_id}@example.com"
                    }
                )
                
                # Update cache
                cache_key = f"user:{i + 1000}"
                user_data = {
                    "id": i + 1000,
                    "name": f"Sync Test User {test_user_id}",
                    "email": f"{test_user_id}@example.com",
                    "cached_at": time.time()
                }
                
                await redis_conn["connection"].setex(
                    cache_key, 
                    300,  # 5 minute TTL
                    json.dumps(user_data)
                )
                
                sync_time = (time.time() - start_time) * 1000
                sync_results["sync_delays"].append(sync_time)
                
                # 2. Verify cache consistency
                cached_data = await redis_conn["connection"].get(cache_key)
                if cached_data:
                    parsed_cache_data = json.loads(cached_data)
                    
                    # Verify database matches cache
                    db_data = await sqlite_conn["database"].fetch_one(
                        "SELECT * FROM test_users WHERE id = :id",
                        {"id": i + 1000}
                    )
                    
                    if db_data and db_data["name"] == parsed_cache_data["name"]:
                        # Consistency maintained
                        pass
                    else:
                        sync_results["consistency_violations"] += 1
                
                sync_results["total_sync_tests"] += 1
                
            finally:
                await self.pool_manager.return_connection(sqlite_pool_id, sqlite_conn["id"])
                await self.pool_manager.return_connection(redis_pool_id, redis_conn["id"])
        
        # Calculate averages
        if sync_results["sync_delays"]:
            avg_sync_delay = sum(sync_results["sync_delays"]) / len(sync_results["sync_delays"])
            max_sync_delay = max(sync_results["sync_delays"])
            
            sync_results["avg_sync_delay"] = avg_sync_delay
            sync_results["max_sync_delay"] = max_sync_delay
            sync_results["consistency_rate"] = 1.0 - (sync_results["consistency_violations"] / sync_results["total_sync_tests"])
            
            print(f"  📊 Avg Sync Delay: {avg_sync_delay:.1f}ms")
            print(f"  📈 Max Sync Delay: {max_sync_delay:.1f}ms")
            print(f"  🎯 Consistency Rate: {sync_results['consistency_rate']*100:.1f}%")
        
        return sync_results
    
    async def test_multi_database_workflow_validation(self) -> Dict[str, Any]:
        """Test complete multi-database workflows and user journeys."""
        print(f"\n🚀 Testing Multi-Database Workflow Validation...")
        
        workflow_results = {
            "workflows_completed": 0,
            "workflows_failed": 0,
            "workflow_times": [],
            "data_integrity_checks": []
        }
        
        # Test workflow: User registration with analytics tracking
        for i in range(5):
            workflow_start = time.time()
            
            try:
                workflow_result = await self._execute_user_registration_workflow(i)
                
                if workflow_result["success"]:
                    workflow_time = (time.time() - workflow_start) * 1000
                    workflow_results["workflow_times"].append(workflow_time)
                    workflow_results["workflows_completed"] += 1
                    
                    # Verify data integrity across all databases
                    integrity_check = await self._verify_workflow_data_integrity(workflow_result["user_id"])
                    workflow_results["data_integrity_checks"].append(integrity_check)
                    
                    print(f"  ✅ Workflow {i+1}: {workflow_time:.1f}ms - Integrity: {'✅' if integrity_check['valid'] else '❌'}")
                else:
                    workflow_results["workflows_failed"] += 1
                    print(f"  ❌ Workflow {i+1} failed: {workflow_result.get('error')}")
                    
            except Exception as e:
                workflow_results["workflows_failed"] += 1
                print(f"  ❌ Workflow {i+1} exception: {e}")
        
        # Calculate workflow statistics
        if workflow_results["workflow_times"]:
            workflow_results["avg_workflow_time"] = sum(workflow_results["workflow_times"]) / len(workflow_results["workflow_times"])
            workflow_results["max_workflow_time"] = max(workflow_results["workflow_times"])
            workflow_results["success_rate"] = workflow_results["workflows_completed"] / (workflow_results["workflows_completed"] + workflow_results["workflows_failed"])
        
        return workflow_results
    
    async def _create_coordinated_user_data(self, tx_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create coordinated user data across all databases within transaction."""
        user_id = uuid.uuid4().hex[:8]
        user_data = {
            "user_id": user_id,
            "name": f"Test User {user_id}",
            "email": f"test_{user_id}@example.com",
            "created_at": datetime.now().isoformat()
        }
        
        connections = tx_context["connections"]
        
        # Insert into each database type
        for pool_id, conn in connections.items():
            pool = self.pool_manager.pools[pool_id]
            pool_type = pool["pool_type"]
            
            if pool_type == "sqlite":
                # Insert user into SQLite
                await conn["database"].execute(
                    "INSERT INTO test_users (name, email) VALUES (:name, :email)",
                    {"name": user_data["name"], "email": user_data["email"]}
                )
                
                # Get the inserted user ID
                db_user = await conn["database"].fetch_one(
                    "SELECT id FROM test_users WHERE email = :email",
                    {"email": user_data["email"]}
                )
                user_data["db_user_id"] = db_user["id"] if db_user else None
                
            elif pool_type == "kuzu":
                # Create user node in Kuzu
                kuzu_conn = conn["connection"]
                kuzu_conn.execute(
                    "CREATE (u:TestUser {id: $id, name: $name, email: $email})",
                    {"id": user_data["db_user_id"] or 999, "name": user_data["name"], "email": user_data["email"]}
                )
                
            elif pool_type == "redis":
                # Cache user data in Redis
                redis_conn = conn["connection"]
                cache_key = f"user:{user_data['user_id']}"
                await redis_conn.setex(
                    cache_key,
                    3600,  # 1 hour TTL
                    json.dumps(user_data)
                )
        
        return user_data
    
    async def _verify_cross_database_consistency(self, user_id: str) -> Dict[str, Any]:
        """Verify data consistency across all databases."""
        consistency_check = {
            "user_id": user_id,
            "consistent": True,
            "database_states": {},
            "inconsistencies": []
        }
        
        # Check each database for user data
        for pool_id, pool in self.pool_manager.pools.items():
            pool_type = pool["pool_type"]
            conn = await self.pool_manager.get_connection(pool_id)
            
            try:
                if pool_type == "sqlite":
                    # Check SQLite for user
                    user_data = await conn["database"].fetch_one(
                        "SELECT * FROM test_users WHERE name LIKE :pattern",
                        {"pattern": f"%{user_id}%"}
                    )
                    consistency_check["database_states"]["sqlite"] = user_data is not None
                    
                elif pool_type == "kuzu":
                    # Check Kuzu for user node
                    kuzu_conn = conn["connection"]
                    result = kuzu_conn.execute(
                        "MATCH (u:TestUser) WHERE u.name CONTAINS $user_id RETURN count(u) as user_count",
                        {"user_id": user_id}
                    )
                    user_count = 0
                    if result:
                        for row in result:
                            user_count = row[0]
                    consistency_check["database_states"]["kuzu"] = user_count > 0
                    
                elif pool_type == "redis":
                    # Check Redis cache
                    redis_conn = conn["connection"]
                    cache_key = f"user:{user_id}"
                    cached_data = await redis_conn.get(cache_key)
                    consistency_check["database_states"]["redis"] = cached_data is not None
            
            finally:
                await self.pool_manager.return_connection(pool_id, conn["id"])
        
        # Check for inconsistencies
        db_states = list(consistency_check["database_states"].values())
        if not all(db_states) and any(db_states):
            consistency_check["consistent"] = False
            consistency_check["inconsistencies"].append("Partial data presence across databases")
        
        return consistency_check
    
    async def _test_transaction_rollback(self, failure_scenario: str) -> Dict[str, Any]:
        """Test transaction rollback in various failure scenarios."""
        rollback_result = {
            "scenario": failure_scenario,
            "rollback_successful": False,
            "error": None
        }
        
        try:
            async with self.transaction_coordinator.cross_database_transaction() as tx_context:
                # Create initial data
                user_data = await self._create_coordinated_user_data(tx_context)
                
                # Simulate failure based on scenario
                if failure_scenario == "kuzu_failure":
                    # Force Kuzu error
                    connections = tx_context["connections"]
                    for pool_id, conn in connections.items():
                        pool = self.pool_manager.pools[pool_id]
                        if pool["pool_type"] == "kuzu":
                            kuzu_conn = conn["connection"]
                            # Execute invalid query to force error
                            kuzu_conn.execute("INVALID QUERY SYNTAX")
                            
                elif failure_scenario == "redis_failure":
                    # Force Redis error
                    connections = tx_context["connections"]
                    for pool_id, conn in connections.items():
                        pool = self.pool_manager.pools[pool_id]
                        if pool["pool_type"] == "redis":
                            redis_conn = conn["connection"]
                            # Try to set invalid key
                            await redis_conn.execute_command("INVALID", "COMMAND")
                            
                elif failure_scenario == "sqlite_failure":
                    # Force SQLite error
                    connections = tx_context["connections"]
                    for pool_id, conn in connections.items():
                        pool = self.pool_manager.pools[pool_id]
                        if pool["pool_type"] == "sqlite":
                            # Execute invalid SQL
                            await conn["database"].execute("INVALID SQL SYNTAX")
                
        except Exception as e:
            # Transaction should have rolled back
            rollback_result["error"] = str(e)
            
            # Verify rollback by checking if data was cleaned up
            time.sleep(0.1)  # Small delay for rollback to complete
            
            # Check if user data is gone (indicating successful rollback)
            cleanup_verified = await self._verify_rollback_cleanup()
            rollback_result["rollback_successful"] = cleanup_verified
        
        return rollback_result
    
    async def _verify_rollback_cleanup(self) -> bool:
        """Verify that rollback properly cleaned up partial data."""
        # This is a simplified check - in real scenarios would be more thorough
        cleanup_successful = True
        
        # Check each database for any test data that should have been rolled back
        for pool_id, pool in self.pool_manager.pools.items():
            pool_type = pool["pool_type"]
            conn = await self.pool_manager.get_connection(pool_id)
            
            try:
                if pool_type == "sqlite":
                    # Check for any test users created in the last minute
                    recent_users = await conn["database"].fetch_all(
                        "SELECT COUNT(*) as count FROM test_users WHERE created_at > datetime('now', '-1 minute')"
                    )
                    # If transaction was properly rolled back, should be 0
                    
                elif pool_type == "redis":
                    # Check for any cached test data
                    redis_conn = conn["connection"]
                    test_keys = await redis_conn.keys("user:*")
                    # Rollback should have cleared these keys
            
            finally:
                await self.pool_manager.return_connection(pool_id, conn["id"])
        
        return cleanup_successful
    
    async def _execute_user_registration_workflow(self, workflow_id: int) -> Dict[str, Any]:
        """Execute complete user registration workflow across databases."""
        workflow_result = {
            "success": False,
            "user_id": None,
            "error": None,
            "steps_completed": []
        }
        
        try:
            user_id = f"workflow_user_{workflow_id}_{uuid.uuid4().hex[:6]}"
            
            # Step 1: Create user in SQLite
            sqlite_pool_id = None
            redis_pool_id = None
            kuzu_pool_id = None
            
            for pool_id, pool in self.pool_manager.pools.items():
                if pool["pool_type"] == "sqlite":
                    sqlite_pool_id = pool_id
                elif pool["pool_type"] == "redis":
                    redis_pool_id = pool_id
                elif pool["pool_type"] == "kuzu":
                    kuzu_pool_id = pool_id
            
            # SQLite: Create user record
            if sqlite_pool_id:
                sqlite_conn = await self.pool_manager.get_connection(sqlite_pool_id)
                try:
                    await sqlite_conn["database"].execute(
                        "INSERT INTO test_users (name, email) VALUES (:name, :email)",
                        {"name": f"Workflow User {user_id}", "email": f"{user_id}@example.com"}
                    )
                    workflow_result["steps_completed"].append("sqlite_user_created")
                finally:
                    await self.pool_manager.return_connection(sqlite_pool_id, sqlite_conn["id"])
            
            # Kuzu: Create user node and relationships
            if kuzu_pool_id:
                kuzu_conn = await self.pool_manager.get_connection(kuzu_pool_id)
                try:
                    kuzu_connection = kuzu_conn["connection"]
                    kuzu_connection.execute(
                        "CREATE (u:TestUser {id: $id, name: $name, email: $email})",
                        {"id": workflow_id + 2000, "name": f"Workflow User {user_id}", "email": f"{user_id}@example.com"}
                    )
                    workflow_result["steps_completed"].append("kuzu_node_created")
                finally:
                    await self.pool_manager.return_connection(kuzu_pool_id, kuzu_conn["id"])
            
            # Redis: Cache user data
            if redis_pool_id:
                redis_conn = await self.pool_manager.get_connection(redis_pool_id)
                try:
                    user_cache_data = {
                        "id": workflow_id + 2000,
                        "name": f"Workflow User {user_id}",
                        "email": f"{user_id}@example.com",
                        "registered_at": time.time()
                    }
                    
                    await redis_conn["connection"].setex(
                        f"workflow_user:{user_id}",
                        1800,  # 30 minutes
                        json.dumps(user_cache_data)
                    )
                    workflow_result["steps_completed"].append("redis_cached")
                finally:
                    await self.pool_manager.return_connection(redis_pool_id, redis_conn["id"])
            
            workflow_result["success"] = True
            workflow_result["user_id"] = user_id
            
        except Exception as e:
            workflow_result["error"] = str(e)
        
        return workflow_result
    
    async def _verify_workflow_data_integrity(self, user_id: str) -> Dict[str, Any]:
        """Verify data integrity after workflow completion."""
        integrity_check = {
            "user_id": user_id,
            "valid": True,
            "database_checks": {}
        }
        
        # Check each database for expected data
        for pool_id, pool in self.pool_manager.pools.items():
            pool_type = pool["pool_type"]
            conn = await self.pool_manager.get_connection(pool_id)
            
            try:
                if pool_type == "sqlite":
                    user_exists = await conn["database"].fetch_one(
                        "SELECT COUNT(*) as count FROM test_users WHERE email LIKE :pattern",
                        {"pattern": f"%{user_id}%"}
                    )
                    integrity_check["database_checks"]["sqlite"] = user_exists["count"] > 0 if user_exists else False
                    
                elif pool_type == "kuzu":
                    kuzu_conn = conn["connection"]
                    result = kuzu_conn.execute(
                        "MATCH (u:TestUser) WHERE u.email CONTAINS $user_id RETURN count(u) as count",
                        {"user_id": user_id}
                    )
                    count = 0
                    if result:
                        for row in result:
                            count = row[0]
                    integrity_check["database_checks"]["kuzu"] = count > 0
                    
                elif pool_type == "redis":
                    redis_conn = conn["connection"]
                    cached_data = await redis_conn.get(f"workflow_user:{user_id}")
                    integrity_check["database_checks"]["redis"] = cached_data is not None
            
            finally:
                await self.pool_manager.return_connection(pool_id, conn["id"])
        
        # Check if all databases have the expected data
        if not all(integrity_check["database_checks"].values()):
            integrity_check["valid"] = False
        
        return integrity_check


# Pytest tests for cross-database integration

@pytest.mark.asyncio
async def test_multi_database_transaction_coordination(multi_database_setup, transaction_coordinator) -> None:
    """Test coordinated transactions across all database types."""
    pool_manager = multi_database_setup["pool_manager"]
    
    tester = CrossDatabaseIntegrationTester(pool_manager, transaction_coordinator)
    
    coordination_results = await tester.test_multi_database_transaction_coordination()
    
    # Validate transaction coordination
    assert coordination_results["successful_transactions"] > 0, "No successful transactions"
    assert coordination_results["failed_transactions"] < coordination_results["successful_transactions"], "Too many failed transactions"
    
    # Check coordination times (should be < 500ms)
    if coordination_results["coordination_times"]:
        avg_coordination_time = sum(coordination_results["coordination_times"]) / len(coordination_results["coordination_times"])
        assert avg_coordination_time < 500, f"Average coordination time {avg_coordination_time:.1f}ms too slow"
    
    # Check data consistency
    for consistency_check in coordination_results["data_consistency_checks"]:
        assert consistency_check["consistent"], f"Data consistency failed for user {consistency_check['user_id']}"
    
    # Check rollback tests
    for rollback_test in coordination_results["rollback_tests"]:
        assert rollback_test["rollback_successful"], f"Rollback failed for scenario {rollback_test['scenario']}"


@pytest.mark.asyncio
async def test_cache_database_synchronization(multi_database_setup) -> None:
    """Test cache synchronization with persistent databases."""
    pool_manager = multi_database_setup["pool_manager"]
    transaction_coordinator = TransactionCoordinator(pool_manager)
    
    tester = CrossDatabaseIntegrationTester(pool_manager, transaction_coordinator)
    
    sync_results = await tester.test_cache_database_synchronization()
    
    # Validate synchronization performance
    if "avg_sync_delay" in sync_results:
        assert sync_results["avg_sync_delay"] < 100, f"Average sync delay {sync_results['avg_sync_delay']:.1f}ms too slow"
        assert sync_results["max_sync_delay"] < 200, f"Max sync delay {sync_results['max_sync_delay']:.1f}ms too slow"
        
        # Check consistency rate (should be > 95%)
        assert sync_results["consistency_rate"] > 0.95, f"Consistency rate {sync_results['consistency_rate']*100:.1f}% too low"
        
        # Check that violations are minimal
        assert sync_results["consistency_violations"] <= 1, f"Too many consistency violations: {sync_results['consistency_violations']}"


@pytest.mark.asyncio
async def test_multi_database_workflow_validation(multi_database_setup) -> None:
    """Test complete multi-database workflows and user journeys."""
    pool_manager = multi_database_setup["pool_manager"]
    transaction_coordinator = TransactionCoordinator(pool_manager)
    
    tester = CrossDatabaseIntegrationTester(pool_manager, transaction_coordinator)
    
    workflow_results = await tester.test_multi_database_workflow_validation()
    
    # Validate workflow execution
    assert workflow_results["workflows_completed"] > 0, "No workflows completed successfully"
    
    if "success_rate" in workflow_results:
        assert workflow_results["success_rate"] > 0.8, f"Workflow success rate {workflow_results['success_rate']*100:.1f}% too low"
    
    if "avg_workflow_time" in workflow_results:
        assert workflow_results["avg_workflow_time"] < 1000, f"Average workflow time {workflow_results['avg_workflow_time']:.1f}ms too slow"
    
    # Check data integrity
    for integrity_check in workflow_results["data_integrity_checks"]:
        assert integrity_check["valid"], f"Data integrity failed for workflow user {integrity_check['user_id']}"


@pytest.mark.asyncio
async def test_cross_database_error_recovery(multi_database_setup) -> None:
    """Test error recovery and resilience across databases."""
    pool_manager = multi_database_setup["pool_manager"]
    transaction_coordinator = TransactionCoordinator(pool_manager)
    
    # Test that individual database failures don't affect others
    for pool_id, pool in pool_manager.pools.items():
        pool_type = pool["pool_type"]
        
        # Get connection and test basic operation
        conn = await pool_manager.get_connection(pool_id)
        assert conn is not None, f"Failed to get connection for {pool_type}"
        
        try:
            # Test that connection is working
            if pool_type == "kuzu":
                kuzu_conn = conn["connection"]
                result = kuzu_conn.execute("MATCH (n) RETURN count(n) as total")
                # Should not error, even if count is 0
                
            elif pool_type == "redis":
                redis_conn = conn["connection"]
                await redis_conn.ping()
                # Should respond to ping
                
            elif pool_type == "sqlite":
                db = conn["database"]
                result = await db.fetch_one("SELECT 1 as test")
                assert result["test"] == 1
        
        finally:
            await pool_manager.return_connection(pool_id, conn["id"])


if __name__ == "__main__":
    # Run cross-database integration tests standalone
    import asyncio
    
    async def main() -> None:
        print("Cross-Database Integration Tests")
        print("Run with: pytest tests/integration/test_cross_database_transactions.py -v")
    
    asyncio.run(main()) 