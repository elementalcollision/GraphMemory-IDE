"""
DragonflyDB Configuration and Connection Management

This module provides connection management, configuration, and health monitoring
for DragonflyDB in the GraphMemory-IDE streaming analytics pipeline.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import redis.asyncio as redis
from contextlib import asynccontextmanager
import json
import time

logger = logging.getLogger(__name__)

@dataclass
class DragonflyConfig:
    """DragonflyDB configuration settings"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    decode_responses: bool = True
    health_check_interval: int = 30
    max_connections: int = 20
    retry_on_timeout: bool = True
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[int, int] = field(default_factory=lambda: {
        1: 1,  # TCP_KEEPIDLE
        2: 3,  # TCP_KEEPINTVL
        3: 5,  # TCP_KEEPCNT
    })

    @classmethod
    def from_env(cls) -> "DragonflyConfig":
        """Create configuration from environment variables"""
        return cls(
            host=os.environ.get("DRAGONFLY_HOST", "localhost"),
            port=int(os.environ.get("DRAGONFLY_PORT", "6379")),
            password=os.environ.get("DRAGONFLY_PASSWORD"),
            db=int(os.environ.get("DRAGONFLY_DB", "0")),
            decode_responses=os.environ.get("DRAGONFLY_DECODE_RESPONSES", "true").lower() == "true",
            health_check_interval=int(os.environ.get("DRAGONFLY_HEALTH_CHECK_INTERVAL", "30")),
            max_connections=int(os.environ.get("DRAGONFLY_MAX_CONNECTIONS", "20")),
        )

    def to_redis_url(self) -> str:
        """Convert configuration to Redis URL format"""
        auth_part = f":{self.password}@" if self.password else ""
        return f"redis://{auth_part}{self.host}:{self.port}/{self.db}"

class DragonflyConnectionManager:
    """
    Manages DragonflyDB connections with health monitoring, 
    connection pooling, and performance metrics.
    """
    
    def __init__(self, config: DragonflyConfig):
        self.config = config
        self.pool: Optional[redis.ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._performance_stats: Dict[str, Union[int, float, str, None]] = {
            "connection_count": 0,
            "total_commands": 0,
            "failed_commands": 0,
            "last_health_check": None,
            "average_latency_ms": 0.0,
            "peak_memory_usage": 0,
        }
        self._is_healthy = False
        
    async def initialize(self):
        """Initialize DragonflyDB connection pool"""
        try:
            logger.info(f"Initializing DragonflyDB connection to {self.config.host}:{self.config.port}")
            
            # Create connection pool
            self.pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                decode_responses=self.config.decode_responses,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                socket_keepalive=self.config.socket_keepalive,
                socket_keepalive_options=self.config.socket_keepalive_options,
                health_check_interval=self.config.health_check_interval,
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self._test_connection()
            
            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_monitor())
            
            logger.info("DragonflyDB connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DragonflyDB connection: {e}")
            raise
    
    async def _test_connection(self):
        """Test the DragonflyDB connection"""
        if not self.redis_client:
            raise ConnectionError("Redis client not initialized")
            
        start_time = time.time()
        try:
            response = await self.redis_client.ping()
            latency = (time.time() - start_time) * 1000
            
            if response:
                self._is_healthy = True
                self._update_performance_stats(command_success=True, latency_ms=latency)
                logger.info(f"DragonflyDB connection test successful (latency: {latency:.2f}ms)")
                return True
            else:
                raise ConnectionError("Ping failed")
                
        except Exception as e:
            self._is_healthy = False
            self._update_performance_stats(command_success=False)
            logger.error(f"DragonflyDB connection test failed: {e}")
            raise
    
    async def _health_monitor(self):
        """Background task to monitor DragonflyDB health"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._test_connection()
                
                # Get memory stats
                if self.redis_client:
                    memory_info = await self.redis_client.info("memory")
                    if memory_info:
                        used_memory = memory_info.get("used_memory", 0)
                        current_peak = self._performance_stats["peak_memory_usage"]
                        if isinstance(current_peak, (int, float)) and isinstance(used_memory, (int, float)):
                            self._performance_stats["peak_memory_usage"] = max(current_peak, used_memory)
                
                self._performance_stats["last_health_check"] = datetime.utcnow().isoformat()
                
            except Exception as e:
                logger.warning(f"Health check failed: {e}")
                self._is_healthy = False
    
    def _update_performance_stats(self, command_success: bool = True, latency_ms: float = 0.0):
        """Update performance statistics"""
        total_commands = self._performance_stats["total_commands"]
        if isinstance(total_commands, (int, float)):
            self._performance_stats["total_commands"] = total_commands + 1
        
        if not command_success:
            failed_commands = self._performance_stats["failed_commands"]
            if isinstance(failed_commands, (int, float)):
                self._performance_stats["failed_commands"] = failed_commands + 1
        
        if latency_ms > 0:
            current_avg = self._performance_stats["average_latency_ms"]
            new_total = self._performance_stats["total_commands"]
            if isinstance(current_avg, (int, float)) and isinstance(new_total, (int, float)) and new_total > 0:
                self._performance_stats["average_latency_ms"] = (
                    (current_avg * (new_total - 1) + latency_ms) / new_total
                )
    
    @asynccontextmanager
    async def get_client(self):
        """Get Redis client with performance tracking"""
        if not self.redis_client:
            raise ConnectionError("DragonflyDB client not initialized")
        
        start_time = time.time()
        try:
            yield self.redis_client
            latency = (time.time() - start_time) * 1000
            self._update_performance_stats(command_success=True, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._update_performance_stats(command_success=False, latency_ms=latency)
            raise
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        stats = self._performance_stats.copy()
        stats["is_healthy"] = self._is_healthy
        stats["connection_pool_size"] = self.pool.connection_kwargs if self.pool else 0
        
        # Add real-time stats
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats.update({
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                })
            except Exception as e:
                logger.warning(f"Failed to get real-time stats: {e}")
        
        return stats
    
    async def benchmark_performance(self, num_operations: int = 1000) -> Dict[str, float]:
        """Run performance benchmark"""
        logger.info(f"Starting DragonflyDB performance benchmark with {num_operations} operations")
        
        benchmark_results = {
            "set_operations_per_sec": 0.0,
            "get_operations_per_sec": 0.0,
            "pipeline_operations_per_sec": 0.0,
            "average_latency_ms": 0.0,
        }
        
        async with self.get_client() as client:
            # Test SET operations
            start_time = time.time()
            for i in range(num_operations):
                await client.set(f"benchmark:set:{i}", f"value_{i}")
            set_duration = time.time() - start_time
            benchmark_results["set_operations_per_sec"] = num_operations / set_duration
            
            # Test GET operations
            start_time = time.time()
            for i in range(num_operations):
                await client.get(f"benchmark:set:{i}")
            get_duration = time.time() - start_time
            benchmark_results["get_operations_per_sec"] = num_operations / get_duration
            
            # Test Pipeline operations
            pipe = client.pipeline()
            start_time = time.time()
            for i in range(num_operations):
                pipe.set(f"benchmark:pipe:{i}", f"value_{i}")
            await pipe.execute()
            pipeline_duration = time.time() - start_time
            benchmark_results["pipeline_operations_per_sec"] = num_operations / pipeline_duration
            
            # Calculate average latency
            total_duration = set_duration + get_duration + pipeline_duration
            total_ops = num_operations * 3
            benchmark_results["average_latency_ms"] = (total_duration / total_ops) * 1000
            
            # Cleanup benchmark keys
            await client.delete(*[f"benchmark:set:{i}" for i in range(num_operations)])
            await client.delete(*[f"benchmark:pipe:{i}" for i in range(num_operations)])
        
        logger.info(f"Benchmark completed: {benchmark_results}")
        return benchmark_results
    
    async def close(self):
        """Close DragonflyDB connections"""
        try:
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self.redis_client:
                await self.redis_client.close()
            
            if self.pool:
                await self.pool.disconnect()
            
            logger.info("DragonflyDB connections closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing DragonflyDB connections: {e}")

# Global connection manager instance
_connection_manager: Optional[DragonflyConnectionManager] = None

async def get_dragonfly_client() -> redis.Redis:
    """Get the global DragonflyDB client"""
    global _connection_manager
    if not _connection_manager:
        raise ConnectionError("DragonflyDB connection manager not initialized")
    
    if not _connection_manager.redis_client:
        raise ConnectionError("DragonflyDB client not available")
    
    return _connection_manager.redis_client

async def initialize_dragonfly(config: Optional[DragonflyConfig] = None):
    """Initialize global DragonflyDB connection"""
    global _connection_manager
    
    if config is None:
        config = DragonflyConfig.from_env()
    
    _connection_manager = DragonflyConnectionManager(config)
    await _connection_manager.initialize()

async def close_dragonfly():
    """Close global DragonflyDB connection"""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.close()
        _connection_manager = None

async def get_dragonfly_stats() -> Dict[str, Any]:
    """Get DragonflyDB performance statistics"""
    global _connection_manager
    if not _connection_manager:
        return {"error": "Connection manager not initialized"}
    
    return await _connection_manager.get_performance_stats()

async def benchmark_dragonfly(num_operations: int = 1000) -> Dict[str, float]:
    """Run DragonflyDB performance benchmark"""
    global _connection_manager
    if not _connection_manager:
        raise ConnectionError("Connection manager not initialized")
    
    return await _connection_manager.benchmark_performance(num_operations) 