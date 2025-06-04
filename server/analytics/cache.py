"""
Analytics caching system for GraphMemory-IDE.
Provides Redis-based caching for analytics results to improve performance.
"""

import json
import hashlib
import logging
from typing import Any, Dict, Optional, Union, TYPE_CHECKING
from datetime import datetime, timedelta
import asyncio

if TYPE_CHECKING:
    import redis.asyncio as redis

logger = logging.getLogger(__name__)

class AnalyticsCache:
    """
    Redis-based cache for analytics results.
    Provides automatic expiration and cache invalidation.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 3600) -> None:
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_client: Optional[Any] = None
        self._connected = False
        # Initialize in-memory cache attributes (used as fallback)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
    
    async def connect(self) -> None:
        """Initialize Redis connection"""
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
        except ImportError:
            logger.warning("Redis not available, using in-memory cache")
            self._memory_cache = {}
            self._cache_timestamps = {}
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
            self._memory_cache = {}
            self._cache_timestamps = {}
    
    def _generate_cache_key(self, analytics_type: str, parameters: Dict[str, Any]) -> str:
        """Generate a unique cache key for analytics request"""
        # Create a deterministic hash of the parameters
        param_str = json.dumps(parameters, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"analytics:{analytics_type}:{param_hash}"
    
    async def get(self, analytics_type: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve cached analytics result"""
        cache_key = self._generate_cache_key(analytics_type, parameters)
        
        if self._connected and self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")
        else:
            # Use in-memory cache
            if cache_key in self._memory_cache:
                # Check if expired
                timestamp = self._cache_timestamps.get(cache_key)
                if timestamp and datetime.now() - timestamp < timedelta(seconds=self.default_ttl):
                    return self._memory_cache[cache_key]
                else:
                    # Remove expired entry
                    del self._memory_cache[cache_key]
                    if cache_key in self._cache_timestamps:
                        del self._cache_timestamps[cache_key]
        
        return None
    
    async def set(
        self, 
        analytics_type: str, 
        parameters: Dict[str, Any], 
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Store analytics result in cache"""
        cache_key = self._generate_cache_key(analytics_type, parameters)
        ttl = ttl or self.default_ttl
        
        if self._connected and self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key, 
                    ttl, 
                    json.dumps(result, default=str)
                )
                return True
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        else:
            # Use in-memory cache
            self._memory_cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.now()
            return True
        
        return False
    
    async def invalidate(self, analytics_type: str, parameters: Dict[str, Any]) -> bool:
        """Invalidate specific cache entry"""
        cache_key = self._generate_cache_key(analytics_type, parameters)
        
        if self._connected and self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                return True
            except Exception as e:
                logger.warning(f"Redis cache invalidate error: {e}")
        else:
            # Use in-memory cache
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            if cache_key in self._cache_timestamps:
                del self._cache_timestamps[cache_key]
            return True
        
        return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        if self._connected and self.redis_client:
            try:
                keys = await self.redis_client.keys(f"analytics:{pattern}*")
                if keys:
                    await self.redis_client.delete(*keys)
                return len(keys)
            except Exception as e:
                logger.warning(f"Redis cache pattern invalidate error: {e}")
        else:
            # Use in-memory cache
            keys_to_delete = [
                key for key in self._memory_cache.keys()
                if key.startswith(f"analytics:{pattern}")
            ]
            for key in keys_to_delete:
                del self._memory_cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
            return len(keys_to_delete)
        
        return 0
    
    async def clear_all(self) -> bool:
        """Clear all analytics cache entries"""
        if self._connected and self.redis_client:
            try:
                keys = await self.redis_client.keys("analytics:*")
                if keys:
                    await self.redis_client.delete(*keys)
                return True
            except Exception as e:
                logger.warning(f"Redis cache clear error: {e}")
        else:
            # Use in-memory cache
            analytics_keys = [
                key for key in self._memory_cache.keys()
                if key.startswith("analytics:")
            ]
            for key in analytics_keys:
                del self._memory_cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
            return True
        
        return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self._connected and self.redis_client:
            try:
                info = await self.redis_client.info()
                keys = await self.redis_client.keys("analytics:*")
                return {
                    "type": "redis",
                    "connected": True,
                    "total_keys": len(keys),
                    "memory_usage": info.get("used_memory_human", "unknown"),
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0)
                }
            except Exception as e:
                logger.warning(f"Redis cache stats error: {e}")
        
        # In-memory cache stats
        analytics_keys = [
            key for key in getattr(self, '_memory_cache', {}).keys()
            if key.startswith("analytics:")
        ]
        return {
            "type": "memory",
            "connected": False,
            "total_keys": len(analytics_keys),
            "memory_usage": "unknown",
            "hits": 0,
            "misses": 0
        }
    
    async def close(self) -> None:
        """Close cache connection"""
        if self._connected and self.redis_client:
            await self.redis_client.close()
            self._connected = False 