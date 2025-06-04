"""
Advanced Caching Layer for Real-time Analytics Dashboard

This module provides a comprehensive caching system with multi-level cache hierarchy,
intelligent invalidation strategies, cache warming, and performance monitoring.
Integrates with the enhanced circuit breaker system for optimal reliability.
"""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union, Tuple, TYPE_CHECKING
from contextlib import asynccontextmanager

try:
    # Import aiocache for multi-backend caching
    from aiocache import SimpleMemoryCache, RedisCache, Cache
    from aiocache.serializers import PickleSerializer, JsonSerializer
    from aiocache.plugins import TimingPlugin, HitMissRatioPlugin
    AIOCACHE_AVAILABLE = True
except ImportError:
    # Fallback to basic caching if aiocache not available
    AIOCACHE_AVAILABLE = False
    if TYPE_CHECKING:
        from aiocache import SimpleMemoryCache, RedisCache, Cache
    else:
        SimpleMemoryCache = None
        RedisCache = None
        Cache = None

try:
    from .enhanced_circuit_breaker import (
        EnhancedCircuitBreaker, CircuitBreakerConfig, CircuitState,
        get_circuit_breaker_manager, ErrorType
    )
    from .models.analytics_models import SystemMetricsData, MemoryInsightsData, GraphMetricsData
    from .models.error_models import AnalyticsError, ErrorSeverity, ErrorCategory
except ImportError:
    from enhanced_circuit_breaker import (
        EnhancedCircuitBreaker, CircuitBreakerConfig, CircuitState,
        get_circuit_breaker_manager, ErrorType
    )
    from models.analytics_models import SystemMetricsData, MemoryInsightsData, GraphMetricsData
    from models.error_models import AnalyticsError, ErrorSeverity, ErrorCategory


class CacheStrategy(Enum):
    """Cache strategy patterns"""
    WRITE_THROUGH = "write_through"       # Write to cache and backend simultaneously
    WRITE_BACK = "write_back"             # Write to cache, backend later
    WRITE_AROUND = "write_around"         # Write to backend, invalidate cache
    READ_THROUGH = "read_through"         # Read from cache, load from backend if miss
    CACHE_ASIDE = "cache_aside"           # Application manages cache and backend
    REFRESH_AHEAD = "refresh_ahead"       # Proactively refresh before expiration


class CacheLevel(Enum):
    """Cache hierarchy levels"""
    L1_MEMORY = "l1_memory"      # Ultra-fast memory cache
    L2_REDIS = "l2_redis"        # Distributed Redis cache
    L3_BACKEND = "l3_backend"    # Original data source


class CacheOperation(Enum):
    """Cache operation types"""
    GET = "get"
    SET = "set"
    DELETE = "delete"
    CLEAR = "clear"
    INVALIDATE = "invalidate"
    WARM = "warm"
    PRELOAD = "preload"


class InvalidationTrigger(Enum):
    """Cache invalidation triggers"""
    TTL_EXPIRED = "ttl_expired"           # Time-based expiration
    MANUAL = "manual"                     # Manual invalidation
    DATA_CHANGED = "data_changed"         # Data source changed
    CAPACITY_LIMIT = "capacity_limit"     # Cache size limit reached
    ERROR_THRESHOLD = "error_threshold"   # Error rate too high
    PATTERN_BASED = "pattern_based"       # Pattern-based invalidation


@dataclass
class CacheConfig:
    """Configuration for cache behavior"""
    
    # Cache hierarchy settings
    enable_l1_memory: bool = True
    enable_l2_redis: bool = False  # Disabled by default for simplicity
    
    # Memory cache settings
    l1_max_size: int = 1000
    l1_ttl_seconds: int = 300  # 5 minutes
    
    # Redis cache settings (if enabled)
    l2_max_size: int = 10000
    l2_ttl_seconds: int = 1800  # 30 minutes
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Performance settings
    enable_compression: bool = True
    enable_serialization: bool = True
    batch_operations: bool = True
    
    # Monitoring settings
    enable_metrics: bool = True
    metrics_window_size: int = 1000
    performance_tracking: bool = True
    
    # Cache warming settings
    enable_cache_warming: bool = True
    warm_on_startup: bool = True
    warm_interval_seconds: int = 600  # 10 minutes
    
    # Invalidation settings
    enable_pattern_invalidation: bool = True
    invalidation_batch_size: int = 100
    
    # Circuit breaker integration
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 30


@dataclass
class CacheEntry:
    """Enhanced cache entry with metadata"""
    
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    cache_level: CacheLevel = CacheLevel.L1_MEMORY
    ttl_seconds: int = 300
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl_seconds == 0:
            return True  # TTL=0 means immediate expiration
        if self.ttl_seconds < 0:
            return False  # Negative TTL means no expiration
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_time_to_expiry_seconds(self) -> float:
        """Get time until expiration in seconds"""
        if self.ttl_seconds == 0:
            return 0.0  # TTL=0 means already expired
        if self.ttl_seconds < 0:
            return float('inf')  # No expiration
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return (expiry_time - datetime.now()).total_seconds()
    
    def touch(self) -> None:
        """Update last accessed time and increment access count"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheMetrics:
    """Comprehensive cache analytics"""
    
    # Operation counters
    total_operations: int = 0
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    invalidations: int = 0
    
    # Performance metrics
    avg_get_time_ms: float = 0.0
    avg_set_time_ms: float = 0.0
    p95_get_time_ms: float = 0.0
    p95_set_time_ms: float = 0.0
    
    # Cache level metrics
    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    
    # Error metrics
    cache_errors: int = 0
    circuit_breaker_trips: int = 0
    
    # Memory usage
    memory_usage_bytes: int = 0
    entry_count: int = 0
    
    # Recent operation times
    recent_get_times: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    recent_set_times: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate as percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def get_l1_hit_rate(self) -> float:
        """Get L1 cache hit rate"""
        total = self.l1_hits + self.l1_misses
        return (self.l1_hits / total * 100) if total > 0 else 0.0
    
    def get_l2_hit_rate(self) -> float:
        """Get L2 cache hit rate"""
        total = self.l2_hits + self.l2_misses
        return (self.l2_hits / total * 100) if total > 0 else 0.0
    
    def update_performance_metrics(self) -> None:
        """Update calculated performance metrics"""
        if self.recent_get_times:
            self.avg_get_time_ms = sum(self.recent_get_times) / len(self.recent_get_times)
            sorted_times = sorted(self.recent_get_times)
            p95_index = int(len(sorted_times) * 0.95)
            self.p95_get_time_ms = sorted_times[p95_index] if sorted_times else 0.0
        
        if self.recent_set_times:
            self.avg_set_time_ms = sum(self.recent_set_times) / len(self.recent_set_times)
            sorted_times = sorted(self.recent_set_times)
            p95_index = int(len(sorted_times) * 0.95)
            self.p95_set_time_ms = sorted_times[p95_index] if sorted_times else 0.0


class CacheWarmer:
    """Cache warming and preloading strategies"""
    
    def __init__(self, cache_manager: 'CacheManager') -> None:
        self.cache_manager = cache_manager
        self.warming_tasks: Dict[str, asyncio.Task[None]] = {}
        self.warming_enabled = True
        
    async def warm_cache(self, keys: List[str], data_loader: Callable[..., Any]) -> None:
        """Warm cache with specific keys"""
        if not self.warming_enabled:
            return
        
        for key in keys:
            try:
                # Load data using provided loader function
                if asyncio.iscoroutinefunction(data_loader):
                    data = await data_loader(key)
                else:
                    data = data_loader(key)
                
                # Store in cache
                await self.cache_manager.set(key, data)
                
            except Exception as e:
                print(f"Cache warming failed for key {key}: {e}")
    
    async def preload_analytics_data(self) -> None:
        """Preload common analytics data"""
        if not self.warming_enabled:
            return
        
        # Define common analytics keys to preload
        analytics_keys = [
            "system_metrics",
            "memory_insights", 
            "graph_metrics"
        ]
        
        for key in analytics_keys:
            try:
                # Trigger cache loading through cache manager
                await self.cache_manager.get(key)
            except Exception as e:
                print(f"Preload failed for {key}: {e}")
    
    async def start_background_warming(self, interval_seconds: int = 600) -> Optional[asyncio.Task[None]]:
        """Start background cache warming task"""
        if not self.warming_enabled:
            return None
        
        async def warming_loop() -> None:
            while self.warming_enabled:
                try:
                    await self.preload_analytics_data()
                    await asyncio.sleep(interval_seconds)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Background warming error: {e}")
                    await asyncio.sleep(60)  # Wait before retry
        
        task = asyncio.create_task(warming_loop())
        self.warming_tasks["background"] = task
        return task
    
    async def stop_all_warming(self) -> None:
        """Stop all cache warming tasks"""
        self.warming_enabled = False
        for task in self.warming_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.warming_tasks.clear()


class CacheInvalidator:
    """Intelligent cache invalidation strategies"""
    
    def __init__(self, cache_manager: 'CacheManager') -> None:
        self.cache_manager = cache_manager
        self.invalidation_patterns: Dict[str, Set[str]] = defaultdict(set)
        self.invalidation_history: List[Dict[str, Any]] = []
        
    async def invalidate_by_key(self, key: str, trigger: InvalidationTrigger = InvalidationTrigger.MANUAL) -> None:
        """Invalidate specific cache key"""
        try:
            await self.cache_manager._invalidate_key(key)
            self._record_invalidation(key, trigger)
        except Exception as e:
            print(f"Invalidation failed for key {key}: {e}")
    
    async def invalidate_by_pattern(self, pattern: str, trigger: InvalidationTrigger = InvalidationTrigger.PATTERN_BASED) -> None:
        """Invalidate keys matching pattern"""
        try:
            invalidated_keys = await self.cache_manager._invalidate_pattern(pattern)
            for key in invalidated_keys:
                self._record_invalidation(key, trigger)
        except Exception as e:
            print(f"Pattern invalidation failed for {pattern}: {e}")
    
    async def invalidate_by_tags(self, tags: Set[str], trigger: InvalidationTrigger = InvalidationTrigger.PATTERN_BASED) -> None:
        """Invalidate keys with specific tags"""
        try:
            invalidated_keys = await self.cache_manager._invalidate_tags(tags)
            for key in invalidated_keys:
                self._record_invalidation(key, trigger)
        except Exception as e:
            print(f"Tag invalidation failed for {tags}: {e}")
    
    def register_invalidation_pattern(self, pattern: str, related_keys: Set[str]) -> None:
        """Register keys that should be invalidated together"""
        self.invalidation_patterns[pattern].update(related_keys)
    
    def _record_invalidation(self, key: str, trigger: InvalidationTrigger) -> None:
        """Record invalidation event"""
        self.invalidation_history.append({
            "key": key,
            "trigger": trigger.value,
            "timestamp": datetime.now().isoformat(),
            "invalidation_id": str(uuid.uuid4())[:8]
        })
        
        # Keep only last 1000 invalidations
        if len(self.invalidation_history) > 1000:
            self.invalidation_history = self.invalidation_history[-1000:]


class FallbackCache:
    """Simple fallback cache when aiocache is not available"""
    
    def __init__(self, max_size: int = 1000) -> None:
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from fallback cache"""
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired():
                entry.touch()
                return entry.data
            else:
                del self.cache[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in fallback cache"""
        # Simple LRU eviction if max size reached
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].last_accessed)
            del self.cache[oldest_key]
        
        entry = CacheEntry(
            key=key,
            data=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl_seconds=ttl
        )
        self.cache[key] = entry
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from fallback cache"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        self.cache.clear()
        return True


class CacheManager:
    """
    Advanced multi-level cache manager with comprehensive features
    
    Provides L1 (memory) and L2 (Redis) cache hierarchy, intelligent invalidation,
    cache warming, performance monitoring, and circuit breaker integration.
    """
    
    def __init__(self, config: Optional[CacheConfig] = None) -> None:
        self.config = config or CacheConfig()
        self.metrics = CacheMetrics()
        
        # Cache instances
        self.l1_cache: Optional[Any] = None  # Use Any to avoid aiocache type issues
        self.l2_cache: Optional[Any] = None  # Use Any to avoid aiocache type issues
        
        # Management components
        self.cache_warmer = CacheWarmer(self)
        self.cache_invalidator = CacheInvalidator(self)
        
        # Circuit breaker integration
        self.circuit_breaker: Optional[EnhancedCircuitBreaker] = None
        
        # Entry metadata tracking
        self.entry_metadata: Dict[str, CacheEntry] = {}
        
        # Performance tracking
        self.operation_times: Dict[str, deque[float]] = {
            "get": deque(maxlen=100),
            "set": deque(maxlen=100),
            "delete": deque(maxlen=100)
        }
        
        # Locks for thread safety
        self._metadata_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize cache backend instances"""
        try:
            if AIOCACHE_AVAILABLE and self.config.enable_l1_memory:
                # Initialize L1 memory cache with plugins
                plugins = []
                if self.config.enable_metrics:
                    plugins.extend([TimingPlugin(), HitMissRatioPlugin()])
                
                self.l1_cache = SimpleMemoryCache(
                    serializer=PickleSerializer() if self.config.enable_serialization else None,
                    plugins=plugins
                )
                
                # Initialize L2 Redis cache if enabled
                if self.config.enable_l2_redis:
                    try:
                        self.l2_cache = RedisCache(
                            endpoint=self.config.redis_host,
                            port=self.config.redis_port,
                            db=self.config.redis_db,
                            serializer=PickleSerializer() if self.config.enable_serialization else JsonSerializer(),
                            plugins=plugins
                        )
                    except Exception as e:
                        print(f"Redis cache initialization failed, using memory only: {e}")
                        self.config.enable_l2_redis = False
            
            else:
                # Use fallback cache
                self.l1_cache = FallbackCache(max_size=self.config.l1_max_size)
            
            # Initialize circuit breaker if enabled
            if self.config.enable_circuit_breaker:
                breaker_config = CircuitBreakerConfig(
                    failure_threshold=self.config.circuit_breaker_failure_threshold,
                    open_timeout_seconds=self.config.circuit_breaker_timeout_seconds
                )
                manager = get_circuit_breaker_manager()
                self.circuit_breaker = manager.create_breaker("cache_manager", breaker_config)
            
            # Start cache warming if enabled
            if self.config.enable_cache_warming and self.config.warm_on_startup:
                asyncio.create_task(self.cache_warmer.preload_analytics_data())
                if self.config.warm_interval_seconds > 0:
                    asyncio.create_task(
                        self.cache_warmer.start_background_warming(
                            self.config.warm_interval_seconds
                        )
                    )
            
        except Exception as e:
            raise RuntimeError(f"Cache manager initialization failed: {e}")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with L1/L2 hierarchy"""
        start_time = time.time()
        
        try:
            # Try circuit breaker protection if enabled
            if self.circuit_breaker:
                async with self.circuit_breaker.protect():
                    return await self._get_internal(key, default)
            else:
                return await self._get_internal(key, default)
                
        except Exception as e:
            await self._record_cache_error(e)
            return default
        finally:
            # Record timing
            duration_ms = (time.time() - start_time) * 1000
            self.operation_times["get"].append(duration_ms)
            async with self._metrics_lock:
                self.metrics.recent_get_times.append(duration_ms)
                self.metrics.total_operations += 1
    
    async def _get_internal(self, key: str, default: Any = None) -> Any:
        """Internal get method with cache hierarchy"""
        
        # Try L1 cache first
        if self.l1_cache:
            try:
                value = await self.l1_cache.get(key)
                if value is not None:
                    async with self._metrics_lock:
                        self.metrics.hits += 1
                        self.metrics.l1_hits += 1
                    
                    # Update metadata
                    await self._update_access_metadata(key)
                    return value
                    
            except Exception as e:
                print(f"L1 cache get error for key {key}: {e}")
        
        # Try L2 cache if L1 miss
        if self.l2_cache:
            try:
                value = await self.l2_cache.get(key)
                if value is not None:
                    async with self._metrics_lock:
                        self.metrics.hits += 1
                        self.metrics.l2_hits += 1
                    
                    # Promote to L1 cache
                    if self.l1_cache:
                        try:
                            await self.l1_cache.set(key, value, ttl=self.config.l1_ttl_seconds)
                        except Exception as e:
                            print(f"L1 cache promotion error for key {key}: {e}")
                    
                    await self._update_access_metadata(key)
                    return value
                    
            except Exception as e:
                print(f"L2 cache get error for key {key}: {e}")
        
        # Cache miss
        async with self._metrics_lock:
            self.metrics.misses += 1
            if self.l1_cache:
                self.metrics.l1_misses += 1
            if self.l2_cache:
                self.metrics.l2_misses += 1
        
        return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None) -> bool:
        """Set value in cache with L1/L2 hierarchy"""
        start_time = time.time()
        
        try:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.config.l1_ttl_seconds
            
            # Try circuit breaker protection if enabled
            if self.circuit_breaker:
                async with self.circuit_breaker.protect():
                    result = await self._set_internal(key, value, ttl, tags)
            else:
                result = await self._set_internal(key, value, ttl, tags)
            return result
                
        except Exception as e:
            await self._record_cache_error(e)
            return False
        finally:
            # Record timing
            duration_ms = (time.time() - start_time) * 1000
            self.operation_times["set"].append(duration_ms)
            async with self._metrics_lock:
                self.metrics.recent_set_times.append(duration_ms)
                self.metrics.total_operations += 1
                self.metrics.sets += 1
    
    async def _set_internal(self, key: str, value: Any, ttl: int, tags: Optional[Set[str]] = None) -> bool:
        """Internal set method with cache hierarchy"""
        
        success = True
        
        # Set in L1 cache
        if self.l1_cache:
            try:
                await self.l1_cache.set(key, value, ttl=ttl)
            except Exception as e:
                print(f"L1 cache set error for key {key}: {e}")
                success = False
        
        # Set in L2 cache
        if self.l2_cache:
            try:
                l2_ttl = max(ttl, self.config.l2_ttl_seconds)
                await self.l2_cache.set(key, value, ttl=l2_ttl)
            except Exception as e:
                print(f"L2 cache set error for key {key}: {e}")
                success = False
        
        # Update metadata
        await self._update_set_metadata(key, ttl, tags)
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels"""
        start_time = time.time()
        
        try:
            success = True
            
            # Delete from L1
            if self.l1_cache:
                try:
                    await self.l1_cache.delete(key)
                except Exception as e:
                    print(f"L1 cache delete error for key {key}: {e}")
                    success = False
            
            # Delete from L2
            if self.l2_cache:
                try:
                    await self.l2_cache.delete(key)
                except Exception as e:
                    print(f"L2 cache delete error for key {key}: {e}")
                    success = False
            
            # Remove metadata
            async with self._metadata_lock:
                self.entry_metadata.pop(key, None)
            
            async with self._metrics_lock:
                self.metrics.deletes += 1
            
            return success
            
        except Exception as e:
            await self._record_cache_error(e)
            return False
        finally:
            # Record timing
            duration_ms = (time.time() - start_time) * 1000
            self.operation_times["delete"].append(duration_ms)
    
    async def clear(self) -> bool:
        """Clear all cache levels"""
        try:
            success = True
            
            # Clear L1
            if self.l1_cache:
                try:
                    await self.l1_cache.clear()
                except Exception as e:
                    print(f"L1 cache clear error: {e}")
                    success = False
            
            # Clear L2
            if self.l2_cache:
                try:
                    await self.l2_cache.clear()
                except Exception as e:
                    print(f"L2 cache clear error: {e}")
                    success = False
            
            # Clear metadata
            async with self._metadata_lock:
                self.entry_metadata.clear()
            
            return success
            
        except Exception as e:
            await self._record_cache_error(e)
            return False
    
    async def _invalidate_key(self, key: str) -> bool:
        """Invalidate specific key (used by invalidator)"""
        return await self.delete(key)
    
    async def _invalidate_pattern(self, pattern: str) -> List[str]:
        """Invalidate keys matching pattern (used by invalidator)"""
        # For simplicity, this is a basic implementation
        # In production, you'd want more sophisticated pattern matching
        invalidated = []
        
        async with self._metadata_lock:
            keys_to_delete = [key for key in self.entry_metadata.keys() 
                            if pattern in key]
        
        for key in keys_to_delete:
            if await self.delete(key):
                invalidated.append(key)
        
        return invalidated
    
    async def _invalidate_tags(self, tags: Set[str]) -> List[str]:
        """Invalidate keys with specific tags (used by invalidator)"""
        invalidated = []
        
        async with self._metadata_lock:
            keys_to_delete = [
                key for key, entry in self.entry_metadata.items()
                if tags.intersection(entry.tags)
            ]
        
        for key in keys_to_delete:
            if await self.delete(key):
                invalidated.append(key)
        
        return invalidated
    
    async def _update_access_metadata(self, key: str) -> None:
        """Update access metadata for cache entry"""
        async with self._metadata_lock:
            if key in self.entry_metadata:
                self.entry_metadata[key].touch()
    
    async def _update_set_metadata(self, key: str, ttl: int, tags: Optional[Set[str]] = None) -> None:
        """Update set metadata for cache entry"""
        async with self._metadata_lock:
            entry = CacheEntry(
                key=key,
                data=None,  # We don't store actual data in metadata
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl,
                tags=tags or set()
            )
            self.entry_metadata[key] = entry
    
    async def _record_cache_error(self, error: Exception) -> None:
        """Record cache error for monitoring"""
        async with self._metrics_lock:
            self.metrics.cache_errors += 1
        
        print(f"Cache error: {error}")
    
    async def get_metrics(self) -> CacheMetrics:
        """Get comprehensive cache metrics"""
        async with self._metrics_lock:
            # Update calculated metrics
            self.metrics.update_performance_metrics()
            
            # Update entry count
            self.metrics.entry_count = len(self.entry_metadata)
            
            return self.metrics
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        metrics = await self.get_metrics()
        
        return {
            "config": {
                "l1_enabled": self.config.enable_l1_memory,
                "l2_enabled": self.config.enable_l2_redis,
                "l1_max_size": self.config.l1_max_size,
                "l1_ttl_seconds": self.config.l1_ttl_seconds,
                "circuit_breaker_enabled": self.config.enable_circuit_breaker
            },
            "metrics": {
                "hit_rate": metrics.get_hit_rate(),
                "l1_hit_rate": metrics.get_l1_hit_rate(),
                "l2_hit_rate": metrics.get_l2_hit_rate(),
                "total_operations": metrics.total_operations,
                "cache_errors": metrics.cache_errors,
                "avg_get_time_ms": metrics.avg_get_time_ms,
                "avg_set_time_ms": metrics.avg_set_time_ms,
                "entry_count": metrics.entry_count
            },
            "cache_levels": {
                "l1_available": self.l1_cache is not None,
                "l2_available": self.l2_cache is not None,
                "aiocache_available": AIOCACHE_AVAILABLE
            },
            "circuit_breaker": {
                "enabled": self.circuit_breaker is not None,
                "state": self.circuit_breaker.state.value if self.circuit_breaker else None
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown cache manager and cleanup resources"""
        try:
            # Stop cache warming
            await self.cache_warmer.stop_all_warming()
            
            # Clear caches
            await self.clear()
            
            # Close connections if needed
            if self.l2_cache and hasattr(self.l2_cache, 'close'):
                await self.l2_cache.close()
            
        except Exception as e:
            print(f"Cache manager shutdown error: {e}")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()
    return _cache_manager


async def initialize_cache_manager(config: Optional[CacheConfig] = None) -> CacheManager:
    """Initialize global cache manager instance"""
    global _cache_manager
    _cache_manager = CacheManager(config)
    await _cache_manager.initialize()
    return _cache_manager


async def shutdown_cache_manager() -> None:
    """Shutdown global cache manager instance"""
    global _cache_manager
    if _cache_manager:
        await _cache_manager.shutdown()
        _cache_manager = None


# Convenience functions for direct cache access
async def cache_get(key: str, default: Any = None) -> Any:
    """Get value from global cache manager"""
    manager = await get_cache_manager()
    return await manager.get(key, default)


async def cache_set(key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None) -> bool:
    """Set value in global cache manager"""
    manager = await get_cache_manager()
    return await manager.set(key, value, ttl, tags)


async def cache_delete(key: str) -> bool:
    """Delete key from global cache manager"""
    manager = await get_cache_manager()
    return await manager.delete(key)


async def cache_clear() -> bool:
    """Clear global cache manager"""
    manager = await get_cache_manager()
    return await manager.clear() 