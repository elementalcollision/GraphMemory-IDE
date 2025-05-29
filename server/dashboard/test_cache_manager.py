"""
Test Suite for Advanced Cache Manager System

This module contains comprehensive tests for the cache manager functionality
including multi-level caching, circuit breaker integration, cache warming,
invalidation strategies, and performance monitoring.
"""

import asyncio
import pytest
import pytest_asyncio
import time
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from server.dashboard.cache_manager import (
    CacheManager, CacheConfig, CacheStrategy, CacheLevel,
    CacheOperation, InvalidationTrigger, CacheEntry, CacheMetrics,
    CacheWarmer, CacheInvalidator, FallbackCache,
    get_cache_manager, initialize_cache_manager, shutdown_cache_manager,
    cache_get, cache_set, cache_delete, cache_clear,
    AIOCACHE_AVAILABLE
)
from server.dashboard.enhanced_circuit_breaker import get_circuit_breaker_manager


@pytest_asyncio.fixture(autouse=True)
async def cleanup_circuit_breakers():
    """Auto-cleanup circuit breakers before each test to prevent naming conflicts"""
    # Cleanup before test
    manager = get_circuit_breaker_manager()
    manager._breakers.clear()
    yield
    # Cleanup after test
    manager._breakers.clear()


class TestCacheConfig:
    """Test cache configuration functionality"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = CacheConfig()
        
        assert config.enable_l1_memory is True
        assert config.enable_l2_redis is False
        assert config.l1_max_size == 1000
        assert config.l1_ttl_seconds == 300
        assert config.l2_ttl_seconds == 1800
        assert config.enable_metrics is True
        assert config.enable_cache_warming is True
        assert config.enable_circuit_breaker is True
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = CacheConfig(
            enable_l1_memory=False,
            enable_l2_redis=True,
            l1_max_size=2000,
            l1_ttl_seconds=600,
            redis_host="custom-redis",
            redis_port=6380
        )
        
        assert config.enable_l1_memory is False
        assert config.enable_l2_redis is True
        assert config.l1_max_size == 2000
        assert config.l1_ttl_seconds == 600
        assert config.redis_host == "custom-redis"
        assert config.redis_port == 6380


class TestCacheEntry:
    """Test cache entry functionality"""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation and metadata"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            data="test_data",
            created_at=now,
            last_accessed=now,
            ttl_seconds=300,
            tags={"tag1", "tag2"}
        )
        
        assert entry.key == "test_key"
        assert entry.data == "test_data"
        assert entry.ttl_seconds == 300
        assert entry.tags == {"tag1", "tag2"}
        assert entry.access_count == 0
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic"""
        # Create expired entry
        old_time = datetime.now() - timedelta(seconds=400)
        expired_entry = CacheEntry(
            key="expired",
            data="data",
            created_at=old_time,
            last_accessed=old_time,
            ttl_seconds=300
        )
        
        assert expired_entry.is_expired() is True
        
        # Create non-expired entry
        recent_time = datetime.now() - timedelta(seconds=100)
        fresh_entry = CacheEntry(
            key="fresh",
            data="data",
            created_at=recent_time,
            last_accessed=recent_time,
            ttl_seconds=300
        )
        
        assert fresh_entry.is_expired() is False
    
    def test_cache_entry_touch(self):
        """Test cache entry touch functionality"""
        entry = CacheEntry(
            key="test",
            data="data",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl_seconds=300
        )
        
        initial_access_time = entry.last_accessed
        initial_access_count = entry.access_count
        
        time.sleep(0.001)  # Small delay to ensure time difference
        entry.touch()
        
        assert entry.last_accessed > initial_access_time
        assert entry.access_count == initial_access_count + 1


class TestCacheMetrics:
    """Test cache metrics functionality"""
    
    def test_metrics_initialization(self):
        """Test metrics initialization"""
        metrics = CacheMetrics()
        
        assert metrics.total_operations == 0
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.get_hit_rate() == 0.0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation"""
        metrics = CacheMetrics()
        metrics.hits = 7
        metrics.misses = 3
        
        assert metrics.get_hit_rate() == 70.0
    
    def test_l1_hit_rate_calculation(self):
        """Test L1 hit rate calculation"""
        metrics = CacheMetrics()
        metrics.l1_hits = 8
        metrics.l1_misses = 2
        
        assert metrics.get_l1_hit_rate() == 80.0
    
    def test_performance_metrics_update(self):
        """Test performance metrics update"""
        metrics = CacheMetrics()
        
        # Add some timing data
        metrics.recent_get_times.extend([10.0, 20.0, 30.0, 40.0, 50.0])
        metrics.recent_set_times.extend([5.0, 15.0, 25.0])
        
        metrics.update_performance_metrics()
        
        assert metrics.avg_get_time_ms == 30.0
        assert metrics.avg_set_time_ms == 15.0
        assert metrics.p95_get_time_ms == 50.0  # 95th percentile of [10,20,30,40,50]


class TestFallbackCache:
    """Test fallback cache implementation"""
    
    @pytest.mark.asyncio
    async def test_fallback_cache_basic_operations(self):
        """Test basic fallback cache operations"""
        cache = FallbackCache(max_size=10)
        
        # Test set and get
        result = await cache.set("key1", "value1", ttl=300)
        assert result is True
        
        value = await cache.get("key1")
        assert value == "value1"
        
        # Test non-existent key
        value = await cache.get("nonexistent")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_fallback_cache_expiration(self):
        """Test fallback cache expiration"""
        cache = FallbackCache()
        
        # Set with very short TTL
        await cache.set("key1", "value1", ttl=0)  # Immediate expiration
        
        # Should return None due to expiration
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_fallback_cache_size_limit(self):
        """Test fallback cache size limit and LRU eviction"""
        cache = FallbackCache(max_size=3)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new key, should evict key2 (oldest)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Still there
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key3") == "value3"  # Still there
        assert await cache.get("key4") == "value4"  # New key
    
    @pytest.mark.asyncio
    async def test_fallback_cache_delete_and_clear(self):
        """Test fallback cache delete and clear operations"""
        cache = FallbackCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Test delete
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None
        
        # Test delete non-existent
        result = await cache.delete("nonexistent")
        assert result is False
        
        # Test clear
        result = await cache.clear()
        assert result is True
        assert await cache.get("key2") is None


class TestCacheManager:
    """Test cache manager functionality"""
    
    @pytest_asyncio.fixture
    async def cache_manager(self):
        """Create cache manager for testing"""
        config = CacheConfig(
            enable_l1_memory=True,
            enable_l2_redis=False,  # Disable Redis for testing
            l1_ttl_seconds=300,
            enable_circuit_breaker=False,  # Disable for simpler testing
            enable_cache_warming=False
        )
        manager = CacheManager(config)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager initialization"""
        assert cache_manager.l1_cache is not None
        assert cache_manager.l2_cache is None  # Disabled in config
        assert cache_manager.config.enable_l1_memory is True
        assert cache_manager.config.enable_l2_redis is False
    
    @pytest.mark.asyncio
    async def test_cache_manager_basic_operations(self, cache_manager):
        """Test basic cache manager operations"""
        
        # Test set
        result = await cache_manager.set("key1", "value1", ttl=300)
        assert result is True
        
        # Test get
        value = await cache_manager.get("key1")
        assert value == "value1"
        
        # Test get with default
        value = await cache_manager.get("nonexistent", "default")
        assert value == "default"
        
        # Test delete
        result = await cache_manager.delete("key1")
        assert result is True
        
        value = await cache_manager.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_manager_with_tags(self, cache_manager):
        """Test cache manager with tags"""
        
        # Set with tags
        await cache_manager.set("key1", "value1", tags={"analytics", "system"})
        await cache_manager.set("key2", "value2", tags={"analytics", "memory"})
        await cache_manager.set("key3", "value3", tags={"graph"})
        
        # Verify data is stored
        assert await cache_manager.get("key1") == "value1"
        assert await cache_manager.get("key2") == "value2"
        assert await cache_manager.get("key3") == "value3"
        
        # Test tag-based invalidation
        invalidated = await cache_manager._invalidate_tags({"analytics"})
        assert len(invalidated) == 2
        assert "key1" in invalidated
        assert "key2" in invalidated
        
        # Verify invalidation worked
        assert await cache_manager.get("key1") is None
        assert await cache_manager.get("key2") is None
        assert await cache_manager.get("key3") == "value3"  # Should still exist
    
    @pytest.mark.asyncio
    async def test_cache_manager_pattern_invalidation(self, cache_manager):
        """Test pattern-based cache invalidation"""
        
        # Set multiple keys with similar patterns
        await cache_manager.set("system_metrics_1", "data1")
        await cache_manager.set("system_metrics_2", "data2")
        await cache_manager.set("memory_insights_1", "data3")
        await cache_manager.set("graph_metrics_1", "data4")
        
        # Test pattern invalidation
        invalidated = await cache_manager._invalidate_pattern("system_metrics")
        assert len(invalidated) == 2
        
        # Verify only matching keys were invalidated
        assert await cache_manager.get("system_metrics_1") is None
        assert await cache_manager.get("system_metrics_2") is None
        assert await cache_manager.get("memory_insights_1") == "data3"
        assert await cache_manager.get("graph_metrics_1") == "data4"
    
    @pytest.mark.asyncio
    async def test_cache_manager_metrics(self, cache_manager):
        """Test cache manager metrics collection"""
        
        # Perform operations to generate metrics
        await cache_manager.set("key1", "value1")
        await cache_manager.get("key1")  # Hit
        await cache_manager.get("key2")  # Miss
        await cache_manager.delete("key1")
        
        metrics = await cache_manager.get_metrics()
        
        assert metrics.total_operations >= 3  # At least get operations
        assert metrics.hits >= 1
        assert metrics.misses >= 1
        assert metrics.sets >= 1
        assert metrics.deletes >= 1
        assert metrics.get_hit_rate() > 0
    
    @pytest.mark.asyncio
    async def test_cache_manager_clear(self, cache_manager):
        """Test cache manager clear functionality"""
        
        # Add some data
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")
        
        # Verify data exists
        assert await cache_manager.get("key1") == "value1"
        assert await cache_manager.get("key2") == "value2"
        
        # Clear cache
        result = await cache_manager.clear()
        assert result is True
        
        # Verify cache is empty
        assert await cache_manager.get("key1") is None
        assert await cache_manager.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_cache_manager_info(self, cache_manager):
        """Test cache manager info functionality"""
        
        info = await cache_manager.get_cache_info()
        
        assert "config" in info
        assert "metrics" in info
        assert "cache_levels" in info
        assert "circuit_breaker" in info
        
        assert info["config"]["l1_enabled"] is True
        assert info["config"]["l2_enabled"] is False
        assert info["cache_levels"]["l1_available"] is True
        assert info["cache_levels"]["aiocache_available"] == AIOCACHE_AVAILABLE


class TestCacheWarmer:
    """Test cache warming functionality"""
    
    @pytest_asyncio.fixture
    async def cache_manager_with_warming(self):
        """Create cache manager with warming enabled"""
        config = CacheConfig(
            enable_cache_warming=True,
            warm_on_startup=False,  # Don't auto-start for testing
            enable_l2_redis=False,
            enable_circuit_breaker=False
        )
        manager = CacheManager(config)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_cache_warmer_basic(self, cache_manager_with_warming):
        """Test basic cache warming functionality"""
        warmer = cache_manager_with_warming.cache_warmer
        
        # Mock data loader
        def data_loader(key: str) -> str:
            return f"data_for_{key}"
        
        # Warm cache with specific keys
        keys = ["key1", "key2", "key3"]
        await warmer.warm_cache(keys, data_loader)
        
        # Verify data was loaded
        for key in keys:
            value = await cache_manager_with_warming.get(key)
            assert value == f"data_for_{key}"
    
    @pytest.mark.asyncio
    async def test_cache_warmer_async_loader(self, cache_manager_with_warming):
        """Test cache warming with async data loader"""
        warmer = cache_manager_with_warming.cache_warmer
        
        # Mock async data loader
        async def async_data_loader(key: str) -> str:
            await asyncio.sleep(0.001)  # Simulate async operation
            return f"async_data_for_{key}"
        
        # Warm cache
        keys = ["async_key1", "async_key2"]
        await warmer.warm_cache(keys, async_data_loader)
        
        # Verify data was loaded
        for key in keys:
            value = await cache_manager_with_warming.get(key)
            assert value == f"async_data_for_{key}"
    
    @pytest.mark.asyncio
    async def test_cache_warmer_error_handling(self, cache_manager_with_warming):
        """Test cache warming error handling"""
        warmer = cache_manager_with_warming.cache_warmer
        
        # Mock data loader that raises exception
        def failing_loader(key: str) -> str:
            if key == "fail":
                raise ValueError("Loader error")
            return f"data_for_{key}"
        
        # Warm cache with mix of good and bad keys
        keys = ["good1", "fail", "good2"]
        await warmer.warm_cache(keys, failing_loader)
        
        # Verify good keys were loaded, bad key wasn't
        assert await cache_manager_with_warming.get("good1") == "data_for_good1"
        assert await cache_manager_with_warming.get("good2") == "data_for_good2"
        assert await cache_manager_with_warming.get("fail") is None


class TestCacheInvalidator:
    """Test cache invalidation functionality"""
    
    @pytest_asyncio.fixture
    async def cache_manager_with_data(self):
        """Create cache manager with test data"""
        config = CacheConfig(
            enable_l2_redis=False,
            enable_circuit_breaker=False,
            enable_cache_warming=False
        )
        manager = CacheManager(config)
        await manager.initialize()
        
        # Add test data
        await manager.set("system_metrics", "system_data", tags={"analytics"})
        await manager.set("memory_insights", "memory_data", tags={"analytics"})
        await manager.set("graph_metrics", "graph_data", tags={"graph"})
        await manager.set("user_data", "user_info", tags={"user"})
        
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_invalidator_by_key(self, cache_manager_with_data):
        """Test invalidation by specific key"""
        invalidator = cache_manager_with_data.cache_invalidator
        
        # Verify data exists
        assert await cache_manager_with_data.get("system_metrics") == "system_data"
        
        # Invalidate specific key
        await invalidator.invalidate_by_key("system_metrics")
        
        # Verify invalidation
        assert await cache_manager_with_data.get("system_metrics") is None
        assert await cache_manager_with_data.get("memory_insights") == "memory_data"  # Should still exist
    
    @pytest.mark.asyncio
    async def test_invalidator_by_pattern(self, cache_manager_with_data):
        """Test invalidation by pattern"""
        invalidator = cache_manager_with_data.cache_invalidator
        
        # Invalidate by pattern
        await invalidator.invalidate_by_pattern("metrics")
        
        # Verify pattern-based invalidation
        assert await cache_manager_with_data.get("system_metrics") is None
        assert await cache_manager_with_data.get("graph_metrics") is None
        assert await cache_manager_with_data.get("memory_insights") == "memory_data"  # Doesn't match pattern
        assert await cache_manager_with_data.get("user_data") == "user_info"  # Doesn't match pattern
    
    @pytest.mark.asyncio
    async def test_invalidator_by_tags(self, cache_manager_with_data):
        """Test invalidation by tags"""
        invalidator = cache_manager_with_data.cache_invalidator
        
        # Invalidate by tags
        await invalidator.invalidate_by_tags({"analytics"})
        
        # Verify tag-based invalidation
        assert await cache_manager_with_data.get("system_metrics") is None
        assert await cache_manager_with_data.get("memory_insights") is None
        assert await cache_manager_with_data.get("graph_metrics") == "graph_data"  # Different tag
        assert await cache_manager_with_data.get("user_data") == "user_info"  # Different tag


class TestGlobalCacheFunctions:
    """Test global cache functions"""
    
    @pytest.mark.asyncio
    async def test_global_cache_manager_singleton(self):
        """Test global cache manager is singleton"""
        manager1 = await get_cache_manager()
        manager2 = await get_cache_manager()
        
        assert manager1 is manager2
        
        # Cleanup
        await shutdown_cache_manager()
    
    @pytest.mark.asyncio
    async def test_global_cache_functions(self):
        """Test global cache convenience functions"""
        
        # Test cache_set
        result = await cache_set("global_key", "global_value", ttl=300)
        assert result is True
        
        # Test cache_get
        value = await cache_get("global_key")
        assert value == "global_value"
        
        # Test cache_get with default
        value = await cache_get("nonexistent", "default_value")
        assert value == "default_value"
        
        # Test cache_delete
        result = await cache_delete("global_key")
        assert result is True
        
        # Verify deletion
        value = await cache_get("global_key")
        assert value is None
        
        # Test cache_clear
        await cache_set("key1", "value1")
        await cache_set("key2", "value2")
        
        result = await cache_clear()
        assert result is True
        
        assert await cache_get("key1") is None
        assert await cache_get("key2") is None
        
        # Cleanup
        await shutdown_cache_manager()
    
    @pytest.mark.asyncio
    async def test_initialize_custom_cache_manager(self):
        """Test initialization with custom config"""
        config = CacheConfig(
            l1_max_size=500,
            l1_ttl_seconds=600,
            enable_l2_redis=False
        )
        
        manager = await initialize_cache_manager(config)
        
        assert manager.config.l1_max_size == 500
        assert manager.config.l1_ttl_seconds == 600
        assert manager.config.enable_l2_redis is False
        
        # Cleanup
        await shutdown_cache_manager()


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test realistic cache manager usage scenario"""
    
    # Initialize cache manager
    config = CacheConfig(
        enable_l1_memory=True,
        enable_l2_redis=False,  # Disable for testing
        l1_ttl_seconds=300,
        enable_cache_warming=True,
        warm_on_startup=False,
        enable_circuit_breaker=False  # Disable for simpler testing
    )
    
    manager = await initialize_cache_manager(config)
    
    try:
        # Simulate analytics data caching
        analytics_data = {
            "system_metrics": {"cpu": 50.0, "memory": 75.0, "disk": 80.0},
            "memory_insights": {"total": 16000, "used": 12000, "free": 4000},
            "graph_metrics": {"nodes": 1000, "edges": 5000, "components": 10}
        }
        
        # Store analytics data with appropriate tags
        for key, data in analytics_data.items():
            tags = {"analytics"}
            if "metrics" in key:
                tags.add("metrics")
            
            await cache_set(key, data, ttl=300, tags=tags)
        
        # Verify data retrieval
        for key, expected_data in analytics_data.items():
            cached_data = await cache_get(key)
            assert cached_data == expected_data
        
        # Test cache warming
        warmer = manager.cache_warmer
        def loader(key: str):
            return f"warmed_data_for_{key}"
        
        await warmer.warm_cache(["warm_key1", "warm_key2"], loader)
        
        assert await cache_get("warm_key1") == "warmed_data_for_warm_key1"
        assert await cache_get("warm_key2") == "warmed_data_for_warm_key2"
        
        # Test pattern invalidation
        invalidator = manager.cache_invalidator
        await invalidator.invalidate_by_pattern("metrics")
        
        # Verify metrics were invalidated
        assert await cache_get("system_metrics") is None
        assert await cache_get("graph_metrics") is None
        assert await cache_get("memory_insights") is not None  # Doesn't match pattern
        
        # Test performance metrics
        metrics = await manager.get_metrics()
        assert metrics.total_operations > 0
        assert metrics.hits > 0
        assert metrics.sets > 0
        
        # Test cache info
        info = await manager.get_cache_info()
        assert info["metrics"]["total_operations"] > 0
        assert info["config"]["l1_enabled"] is True
        
    finally:
        # Cleanup
        await shutdown_cache_manager()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 