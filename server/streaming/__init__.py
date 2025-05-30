"""
GraphMemory-IDE Streaming Analytics Pipeline

This package provides a complete streaming analytics solution for GraphMemory-IDE
using DragonflyDB for high-performance data streaming and real-time analytics.

Components:
- DragonflyDB connection management and performance monitoring
- Stream producers for event collection and buffering
- Feature engineering workers with windowing and pattern detection
- WebSocket API for real-time dashboard updates
- Integration with existing MCP server operations
"""

import asyncio
import logging
from typing import Dict, Any, Optional

# Import all components
from .dragonfly_config import (
    initialize_dragonfly,
    close_dragonfly,
    get_dragonfly_stats,
    benchmark_dragonfly,
    DragonflyConfig
)
from .stream_producer import (
    initialize_stream_producer,
    shutdown_stream_producer,
    get_stream_producer,
    OperationType
)
from .feature_workers import (
    initialize_feature_workers,
    shutdown_feature_workers,
    get_worker_manager
)
from .analytics_websocket import (
    initialize_analytics_websocket,
    shutdown_analytics_websocket,
    create_analytics_router,
    connection_manager
)

logger = logging.getLogger(__name__)

class StreamingAnalyticsPipeline:
    """
    Main orchestrator for the streaming analytics pipeline
    """
    
    def __init__(self, dragonfly_config: Optional[DragonflyConfig] = None):
        self.dragonfly_config = dragonfly_config or DragonflyConfig.from_env()
        self._initialized = False
        self._components_status = {
            "dragonfly": False,
            "stream_producer": False,
            "feature_workers": False,
            "websocket_service": False
        }
    
    async def initialize(self):
        """Initialize the complete streaming analytics pipeline"""
        if self._initialized:
            logger.warning("Streaming analytics pipeline already initialized")
            return
        
        logger.info("🚀 Initializing GraphMemory-IDE Streaming Analytics Pipeline")
        
        try:
            # 1. Initialize DragonflyDB
            logger.info("1️⃣ Initializing DragonflyDB connection...")
            await initialize_dragonfly(self.dragonfly_config)
            self._components_status["dragonfly"] = True
            logger.info("✅ DragonflyDB initialized successfully")
            
            # Test connection and get initial stats
            stats = await get_dragonfly_stats()
            logger.info(f"DragonflyDB Status: {stats.get('is_healthy', 'Unknown')}")
            
            # 2. Initialize Stream Producer
            logger.info("2️⃣ Initializing stream producer...")
            await initialize_stream_producer("graphmemory-mcp-server")
            self._components_status["stream_producer"] = True
            logger.info("✅ Stream producer initialized successfully")
            
            # 3. Initialize Feature Workers
            logger.info("3️⃣ Initializing feature engineering workers...")
            await initialize_feature_workers()
            self._components_status["feature_workers"] = True
            logger.info("✅ Feature workers initialized successfully")
            
            # 4. Initialize WebSocket Service
            logger.info("4️⃣ Initializing WebSocket analytics service...")
            await initialize_analytics_websocket()
            self._components_status["websocket_service"] = True
            logger.info("✅ WebSocket service initialized successfully")
            
            self._initialized = True
            
            logger.info("🎉 Streaming Analytics Pipeline fully initialized!")
            logger.info("📊 Real-time analytics now available for GraphMemory-IDE")
            
            # Log configuration summary
            await self._log_initialization_summary()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize streaming analytics pipeline: {e}")
            await self.shutdown()  # Clean up partial initialization
            raise
    
    async def shutdown(self):
        """Shutdown the streaming analytics pipeline"""
        if not self._initialized:
            return
        
        logger.info("🛑 Shutting down Streaming Analytics Pipeline...")
        
        # Shutdown in reverse order
        if self._components_status["websocket_service"]:
            try:
                logger.info("Shutting down WebSocket service...")
                await shutdown_analytics_websocket()
                self._components_status["websocket_service"] = False
                logger.info("✅ WebSocket service shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down WebSocket service: {e}")
        
        if self._components_status["feature_workers"]:
            try:
                logger.info("Shutting down feature workers...")
                await shutdown_feature_workers()
                self._components_status["feature_workers"] = False
                logger.info("✅ Feature workers shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down feature workers: {e}")
        
        if self._components_status["stream_producer"]:
            try:
                logger.info("Shutting down stream producer...")
                await shutdown_stream_producer()
                self._components_status["stream_producer"] = False
                logger.info("✅ Stream producer shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down stream producer: {e}")
        
        if self._components_status["dragonfly"]:
            try:
                logger.info("Closing DragonflyDB connections...")
                await close_dragonfly()
                self._components_status["dragonfly"] = False
                logger.info("✅ DragonflyDB connections closed")
            except Exception as e:
                logger.error(f"Error closing DragonflyDB: {e}")
        
        self._initialized = False
        logger.info("✅ Streaming Analytics Pipeline shutdown complete")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self._initialized:
            return {
                "initialized": False,
                "components": self._components_status,
                "error": "Pipeline not initialized"
            }
        
        try:
            # Get detailed status from each component
            dragonfly_stats = await get_dragonfly_stats()
            
            producer_stats = {}
            try:
                producer = await get_stream_producer()
                producer_stats = await producer.get_stats()
                stream_info = await producer.get_stream_info()
                producer_stats["streams"] = stream_info
            except Exception as e:
                producer_stats = {"error": str(e)}
            
            worker_stats = {}
            try:
                worker_manager = await get_worker_manager()
                worker_stats = await worker_manager.get_system_status()
            except Exception as e:
                worker_stats = {"error": str(e)}
            
            websocket_stats = connection_manager.get_stats()
            
            return {
                "initialized": True,
                "components": self._components_status,
                "dragonfly": dragonfly_stats,
                "stream_producer": producer_stats,
                "feature_workers": worker_stats,
                "websocket_service": websocket_stats,
                "pipeline_healthy": all(self._components_status.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "initialized": self._initialized,
                "components": self._components_status,
                "error": str(e)
            }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        health_report = {
            "overall_health": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "checks": {}
        }
        
        try:
            # Check DragonflyDB
            try:
                dragonfly_stats = await get_dragonfly_stats()
                health_report["checks"]["dragonfly"] = {
                    "status": "healthy" if dragonfly_stats.get("is_healthy") else "unhealthy",
                    "details": dragonfly_stats
                }
            except Exception as e:
                health_report["checks"]["dragonfly"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_report["overall_health"] = "degraded"
            
            # Check Stream Producer
            try:
                producer = await get_stream_producer()
                producer_stats = await producer.get_stats()
                health_report["checks"]["stream_producer"] = {
                    "status": "healthy",
                    "details": producer_stats
                }
            except Exception as e:
                health_report["checks"]["stream_producer"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_report["overall_health"] = "degraded"
            
            # Check Feature Workers
            try:
                worker_manager = await get_worker_manager()
                worker_stats = await worker_manager.get_system_status()
                health_report["checks"]["feature_workers"] = {
                    "status": "healthy" if worker_stats.get("running") else "unhealthy",
                    "details": worker_stats
                }
            except Exception as e:
                health_report["checks"]["feature_workers"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_report["overall_health"] = "degraded"
            
            # Check WebSocket Service
            websocket_stats = connection_manager.get_stats()
            health_report["checks"]["websocket_service"] = {
                "status": "healthy" if websocket_stats.get("running") else "unhealthy",
                "details": websocket_stats
            }
            
        except Exception as e:
            health_report["overall_health"] = "unhealthy"
            health_report["error"] = str(e)
        
        return health_report
    
    async def run_performance_benchmark(self, operations: int = 1000) -> Dict[str, Any]:
        """Run performance benchmark on the pipeline"""
        logger.info(f"Running performance benchmark with {operations} operations")
        
        try:
            # DragonflyDB benchmark
            dragonfly_results = await benchmark_dragonfly(operations)
            
            # Stream producer benchmark (simulate events)
            producer = await get_stream_producer()
            start_time = asyncio.get_event_loop().time()
            
            for i in range(min(100, operations)):  # Limit to 100 for stream test
                await producer.produce_memory_operation(
                    operation_type=OperationType.CREATE_ENTITY,
                    user_id="benchmark_user",
                    session_id="benchmark_session",
                    entity_count=1,
                    processing_time_ms=1.0
                )
            
            stream_duration = asyncio.get_event_loop().time() - start_time
            stream_ops_per_sec = 100 / stream_duration if stream_duration > 0 else 0
            
            return {
                "benchmark_timestamp": asyncio.get_event_loop().time(),
                "operations_tested": operations,
                "dragonfly_performance": dragonfly_results,
                "stream_producer_performance": {
                    "operations_per_second": stream_ops_per_sec,
                    "duration_seconds": stream_duration,
                    "operations_tested": 100
                }
            }
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return {"error": str(e)}
    
    async def _log_initialization_summary(self):
        """Log initialization summary"""
        try:
            system_status = await self.get_system_status()
            
            logger.info("📋 Streaming Analytics Pipeline Summary:")
            logger.info(f"   🔧 DragonflyDB: {'✅ Connected' if system_status.get('dragonfly', {}).get('is_healthy') else '❌ Not connected'}")
            logger.info(f"   🚀 Stream Producer: {'✅ Running' if self._components_status['stream_producer'] else '❌ Not running'}")
            logger.info(f"   ⚙️ Feature Workers: {'✅ Running' if self._components_status['feature_workers'] else '❌ Not running'}")
            logger.info(f"   🌐 WebSocket Service: {'✅ Running' if self._components_status['websocket_service'] else '❌ Not running'}")
            
            dragonfly_stats = system_status.get('dragonfly', {})
            if dragonfly_stats:
                logger.info(f"   📊 DragonflyDB Memory: {dragonfly_stats.get('used_memory_human', 'Unknown')}")
                logger.info(f"   ⚡ Operations/sec: {dragonfly_stats.get('instantaneous_ops_per_sec', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"Could not log initialization summary: {e}")

# Global pipeline instance
_streaming_pipeline: Optional[StreamingAnalyticsPipeline] = None

async def initialize_streaming_analytics(dragonfly_config: Optional[DragonflyConfig] = None):
    """Initialize the global streaming analytics pipeline"""
    global _streaming_pipeline
    
    if _streaming_pipeline and _streaming_pipeline._initialized:
        logger.warning("Streaming analytics already initialized")
        return _streaming_pipeline
    
    _streaming_pipeline = StreamingAnalyticsPipeline(dragonfly_config)
    await _streaming_pipeline.initialize()
    return _streaming_pipeline

async def shutdown_streaming_analytics():
    """Shutdown the global streaming analytics pipeline"""
    global _streaming_pipeline
    
    if _streaming_pipeline:
        await _streaming_pipeline.shutdown()
        _streaming_pipeline = None

async def get_streaming_pipeline() -> StreamingAnalyticsPipeline:
    """Get the global streaming analytics pipeline"""
    global _streaming_pipeline
    
    if not _streaming_pipeline:
        raise RuntimeError("Streaming analytics pipeline not initialized")
    
    return _streaming_pipeline

# Convenience functions for easy integration
async def produce_memory_operation_event(
    operation_type: OperationType,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    entity_count: int = 0,
    relation_count: int = 0,
    processing_time_ms: float = 0.0,
    additional_data: Optional[Dict[str, Any]] = None
):
    """Convenience function to produce memory operation events"""
    try:
        producer = await get_stream_producer()
        await producer.produce_memory_operation(
            operation_type=operation_type,
            user_id=user_id,
            session_id=session_id,
            entity_count=entity_count,
            relation_count=relation_count,
            processing_time_ms=processing_time_ms,
            additional_data=additional_data
        )
    except Exception as e:
        logger.error(f"Failed to produce memory operation event: {e}")

async def produce_user_interaction_event(
    interaction_type: str,
    target_resource: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    duration_ms: float = 0.0,
    additional_data: Optional[Dict[str, Any]] = None
):
    """Convenience function to produce user interaction events"""
    try:
        producer = await get_stream_producer()
        await producer.produce_user_interaction(
            interaction_type=interaction_type,
            target_resource=target_resource,
            user_id=user_id,
            session_id=session_id,
            duration_ms=duration_ms,
            additional_data=additional_data
        )
    except Exception as e:
        logger.error(f"Failed to produce user interaction event: {e}")

async def produce_system_metric_event(
    metric_name: str,
    metric_value: float,
    metric_unit: str = "count",
    additional_data: Optional[Dict[str, Any]] = None
):
    """Convenience function to produce system metric events"""
    try:
        producer = await get_stream_producer()
        await producer.produce_system_metric(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            additional_data=additional_data
        )
    except Exception as e:
        logger.error(f"Failed to produce system metric event: {e}")

# Export all the important components and functions
__all__ = [
    # Main pipeline
    "StreamingAnalyticsPipeline",
    "initialize_streaming_analytics",
    "shutdown_streaming_analytics", 
    "get_streaming_pipeline",
    
    # Convenience functions
    "produce_memory_operation_event",
    "produce_user_interaction_event",
    "produce_system_metric_event",
    
    # Configuration
    "DragonflyConfig",
    
    # Enums
    "OperationType",
    
    # Router for FastAPI integration
    "create_analytics_router",
] 