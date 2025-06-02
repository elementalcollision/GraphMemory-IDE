"""
Cache Manager for GraphMemory-IDE Analytics

This module provides comprehensive caching capabilities for:
- Dashboard configurations and data
- Analytics query results
- Real-time metrics
- User session data
- Alert configurations

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import pickle
import gzip

import redis.asyncio as redis
import asyncpg
from fastapi import Request


class CacheType(Enum):
    """Cache type categories for different data types."""
    DASHBOARD_CONFIG = "dashboard_config"
    DASHBOARD_DATA = "dashboard_data"
    QUERY_RESULT = "query_result"
    REAL_TIME_METRICS = "real_time_metrics"
    USER_SESSION = "user_session"
    ALERT_CONFIG = "alert_config"
    API_RESPONSE = "api_response"


@dataclass
class CacheConfig:
    """Cache configuration for different data types."""
    ttl: int  # Time to live in seconds
    compress: bool = False
    serialize_method: str = "json"  # json, pickle
    max_size: Optional[int] = None  # Max size in bytes
    
    
class CacheManager:
    """Centralized cache management for analytics system."""
    
    def __init__(self, redis_client, settings) -> None:
        self.redis_client = redis_client
        self.settings = settings
        
        # Cache configurations for different data types
        self.cache_configs = {
            CacheType.DASHBOARD_CONFIG: CacheConfig(ttl=3600, compress=False),  # 1 hour
            CacheType.DASHBOARD_DATA: CacheConfig(ttl=300, compress=True, max_size=1024*1024),  # 5 minutes, 1MB max
            CacheType.QUERY_RESULT: CacheConfig(ttl=600, compress=True, serialize_method="pickle"),  # 10 minutes
            CacheType.REAL_TIME_METRICS: CacheConfig(ttl=60, compress=False),  # 1 minute
            CacheType.USER_SESSION: CacheConfig(ttl=1800, compress=False),  # 30 minutes
            CacheType.ALERT_CONFIG: CacheConfig(ttl=3600, compress=False),  # 1 hour
            CacheType.API_RESPONSE: CacheConfig(ttl=120, compress=True),  # 2 minutes
        }
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_sets = 0
        self.cache_deletes = 0
    
    def _generate_key(self, cache_type: CacheType, identifier: str, **kwargs) -> str:
        """Generate a cache key with proper namespacing."""
        # Create a deterministic key from parameters
        params_str = json.dumps(sorted(kwargs.items()), sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"analytics:{cache_type.value}:{identifier}:{params_hash}"
    
    def _serialize_data(self, data: Any, config: CacheConfig) -> bytes:
        """Serialize data according to cache configuration."""
        if config.serialize_method == "pickle":
            serialized = pickle.dumps(data)
        else:  # json
            serialized = json.dumps(data, default=str).encode()
        
        if config.compress:
            serialized = gzip.compress(serialized)
        
        # Check size limits
        if config.max_size and len(serialized) > config.max_size:
            raise ValueError(f"Data size {len(serialized)} exceeds max cache size {config.max_size}")
        
        return serialized
    
    def _deserialize_data(self, data: bytes, config: CacheConfig) -> Any:
        """Deserialize data according to cache configuration."""
        if config.compress:
            data = gzip.decompress(data)
        
        if config.serialize_method == "pickle":
            return pickle.loads(data)
        else:  # json
            return json.loads(data.decode())
    
    async def get(self, cache_type: CacheType, identifier: str, **kwargs) -> Optional[Any]:
        """Get data from cache."""
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_key(cache_type, identifier, **kwargs)
            data = await self.redis_client.get(key)
            
            if data is None:
                self.cache_misses += 1
                return None
            
            config = self.cache_configs[cache_type]
            result = self._deserialize_data(data, config)
            self.cache_hits += 1
            return result
            
        except Exception as e:
            print(f"Cache get error: {e}")
            self.cache_misses += 1
            return None
    
    async def set(self, cache_type: CacheType, identifier: str, data: Any, **kwargs) -> bool:
        """Set data in cache."""
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key(cache_type, identifier, **kwargs)
            config = self.cache_configs[cache_type]
            
            serialized_data = self._serialize_data(data, config)
            
            await self.redis_client.setex(key, config.ttl, serialized_data)
            self.cache_sets += 1
            return True
            
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, cache_type: CacheType, identifier: str, **kwargs) -> bool:
        """Delete data from cache."""
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key(cache_type, identifier, **kwargs)
            result = await self.redis_client.delete(key)
            if result:
                self.cache_deletes += 1
            return bool(result)
            
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(f"analytics:{pattern}")
            if keys:
                result = await self.redis_client.delete(*keys)
                self.cache_deletes += result
                return result
            return 0
            
        except Exception as e:
            print(f"Cache pattern invalidation error: {e}")
            return 0
    
    async def get_dashboard_config(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get cached dashboard configuration."""
        result = await self.get(CacheType.DASHBOARD_CONFIG, dashboard_id)
        return result
    
    async def set_dashboard_config(self, dashboard_id: str, config: Dict[str, Any]) -> bool:
        """Cache dashboard configuration."""
        result = await self.set(CacheType.DASHBOARD_CONFIG, dashboard_id, config)
        return result
    
    async def get_dashboard_data(self, dashboard_id: str, time_range: str = "24h") -> Optional[Dict[str, Any]]:
        """Get cached dashboard data."""
        result = await self.get(CacheType.DASHBOARD_DATA, dashboard_id, time_range=time_range)
        return result
    
    async def set_dashboard_data(self, dashboard_id: str, data: Dict[str, Any], time_range: str = "24h") -> bool:
        """Cache dashboard data."""
        result = await self.set(CacheType.DASHBOARD_DATA, dashboard_id, data, time_range=time_range)
        return result
    
    async def get_query_result(self, query_hash: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get cached query result."""
        if params is None:
            params = {}
        result = await self.get(CacheType.QUERY_RESULT, query_hash, **params)
        return result
    
    async def set_query_result(self, query_hash: str, result: Any, params: Optional[Dict[str, Any]] = None) -> bool:
        """Cache query result."""
        if params is None:
            params = {}
        cache_result = await self.set(CacheType.QUERY_RESULT, query_hash, result, **params)
        return cache_result
    
    async def get_real_time_metrics(self, metric_type: str = "current") -> Optional[Dict[str, Any]]:
        """Get cached real-time metrics."""
        result = await self.get(CacheType.REAL_TIME_METRICS, metric_type)
        return result
    
    async def set_real_time_metrics(self, metrics: Dict[str, Any], metric_type: str = "current") -> bool:
        """Cache real-time metrics."""
        result = await self.set(CacheType.REAL_TIME_METRICS, metric_type, metrics)
        return result
    
    async def invalidate_dashboard(self, dashboard_id: str) -> None:
        """Invalidate all cache entries for a dashboard."""
        await self.delete(CacheType.DASHBOARD_CONFIG, dashboard_id)
        await self.invalidate_pattern(f"dashboard_data:{dashboard_id}:*")
    
    async def invalidate_user_data(self, user_id: str) -> None:
        """Invalidate all cache entries for a user."""
        await self.invalidate_pattern(f"*:{user_id}:*")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_operations = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_operations * 100) if total_operations > 0 else 0
        
        redis_info = {}
        if self.redis_client:
            try:
                info = await self.redis_client.info("memory")
                redis_info = {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "max_memory": info.get("maxmemory", 0),
                }
            except Exception as e:
                print(f"Error getting Redis info: {e}")
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_sets": self.cache_sets,
            "cache_deletes": self.cache_deletes,
            "hit_rate_percent": round(float(hit_rate), 2),
            "total_operations": total_operations,
            "redis_info": redis_info,
            "timestamp": datetime.utcnow().isoformat()
        }


class QueryCache:
    """Specialized caching for database queries."""
    
    def __init__(self, cache_manager: CacheManager) -> None:
        self.cache_manager = cache_manager
    
    def _hash_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Create a hash for query and parameters."""
        if params is None:
            params = {}
        
        # Normalize query (remove extra whitespace)
        normalized_query = " ".join(query.split())
        
        # Create hash from query and parameters
        query_data = {
            "query": normalized_query,
            "params": sorted(params.items())
        }
        
        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.sha256(query_str.encode()).hexdigest()
    
    async def get_cached_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached query result."""
        query_hash = self._hash_query(query, params)
        result = await self.cache_manager.get_query_result(query_hash, params or {})
        return result
    
    async def cache_query_result(self, query: str, result: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> None:
        """Cache query result."""
        query_hash = self._hash_query(query, params)
        await self.cache_manager.set_query_result(query_hash, result, params or {})
    
    async def execute_cached_query(self, db_pool: asyncpg.Pool, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute query with caching."""
        if params is None:
            params = []
        
        # Try to get from cache first
        param_dict = {f"param_{i}": str(param) for i, param in enumerate(params)}
        cached_result = await self.get_cached_query(query, param_dict)
        
        if cached_result is not None:
            return cached_result
        
        # Execute query if not cached
        async with db_pool.acquire() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            
            result = [dict(row) for row in rows]
            
            # Cache the result
            await self.cache_query_result(query, result, param_dict)
            
            return result


class APIResponseCache:
    """Caching for API responses."""
    
    def __init__(self, cache_manager: CacheManager) -> None:
        self.cache_manager = cache_manager
    
    def _generate_request_key(self, request: Request) -> str:
        """Generate cache key from request."""
        # Include method, path, and sorted query parameters
        key_data = {
            "method": request.method,
            "path": str(request.url.path),
            "query": sorted(request.query_params.items()) if request.query_params else []
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get_cached_response(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get cached API response."""
        request_key = self._generate_request_key(request)
        return await self.cache_manager.get(CacheType.API_RESPONSE, request_key)
    
    async def cache_response(self, request: Request, response_data: Dict[str, Any]) -> bool:
        """Cache API response."""
        request_key = self._generate_request_key(request)
        return await self.cache_manager.set(CacheType.API_RESPONSE, request_key, response_data)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None
_query_cache: Optional[QueryCache] = None
_api_cache: Optional[APIResponseCache] = None


async def initialize_cache_manager(redis_client, settings) -> None:
    """Initialize the cache manager."""
    global _cache_manager, _query_cache, _api_cache
    
    _cache_manager = CacheManager(redis_client, settings)
    _query_cache = QueryCache(_cache_manager)
    _api_cache = APIResponseCache(_cache_manager)
    
    print("Cache manager initialized successfully")


def get_cache_manager() -> Optional[CacheManager]:
    """Get the global cache manager instance."""
    return _cache_manager


def get_query_cache() -> Optional[QueryCache]:
    """Get the global query cache instance."""
    return _query_cache


def get_api_cache() -> Optional[APIResponseCache]:
    """Get the global API cache instance."""
    return _api_cache


async def shutdown_cache_manager() -> None:
    """Shutdown the cache manager."""
    global _cache_manager, _query_cache, _api_cache
    
    if _cache_manager:
        # Get final stats
        stats = await _cache_manager.get_cache_stats()
        print(f"Cache manager shutdown - Final stats: {stats}")
    
    _cache_manager = None
    _query_cache = None
    _api_cache = None 