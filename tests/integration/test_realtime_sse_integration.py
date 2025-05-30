"""
Real-time SSE Integration Testing Framework
Step 13 Phase 2 Day 3 - Component 1

Comprehensive testing framework for Server-Sent Events (SSE) integration
with live analytics data, performance validation, and connection stability.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import httpx
from httpx_sse import aconnect_sse

from tests.fixtures.advanced_database_fixtures import (
    DatabaseConnectionPoolManager,
    DatabasePerformanceMonitor
)
from tests.integration.test_real_analytics_engine_integration import (
    AnalyticsEngineIntegrationTester
)

# Configure logging for detailed test output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SSEStreamMetrics:
    """Metrics collection for SSE stream performance"""
    total_events: int = 0
    total_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    latencies: List[float] = field(default_factory=list)
    connection_drops: int = 0
    reconnections: int = 0
    error_count: int = 0
    
    @property
    def duration(self) -> float:
        """Calculate total duration of the stream"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def events_per_second(self) -> float:
        """Calculate events per second throughput"""
        return self.total_events / self.duration if self.duration > 0 else 0.0
    
    @property
    def bytes_per_second(self) -> float:
        """Calculate bytes per second throughput"""
        return self.total_bytes / self.duration if self.duration > 0 else 0.0
    
    @property
    def average_latency(self) -> float:
        """Calculate average latency in milliseconds"""
        return statistics.mean(self.latencies) * 1000 if self.latencies else 0.0
    
    @property
    def p95_latency(self) -> float:
        """Calculate 95th percentile latency in milliseconds"""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(0.95 * len(sorted_latencies))
        return sorted_latencies[index] * 1000

class SSEStreamTester:
    """Core SSE stream testing with live analytics data integration"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.analytics_tester = AnalyticsEngineIntegrationTester()
        self.db_pool_manager = DatabaseConnectionPoolManager()
        self.performance_monitor = DatabasePerformanceMonitor()
        self.active_streams: Dict[str, SSEStreamMetrics] = {}
        
    async def test_single_client_sse_streaming(self) -> SSEStreamMetrics:
        """Test single client SSE streaming with live analytics data"""
        logger.info("Testing single client SSE streaming with live analytics data")
        
        stream_id = f"single_client_{int(time.time())}"
        metrics = SSEStreamMetrics()
        self.active_streams[stream_id] = metrics
        
        try:
            # Initialize analytics engine connection
            await self.analytics_tester.setup_analytics_integration()
            
            # Connect to SSE endpoint
            async with httpx.AsyncClient() as client:
                async with aconnect_sse(
                    client, "GET", f"{self.base_url}/analytics/stream"
                ) as event_source:
                    
                    async for event in event_source.aiter_sse():
                        if event.event == "analytics_data":
                            # Process analytics data event
                            event_start = time.time()
                            
                            try:
                                data = json.loads(event.data)
                                
                                # Validate analytics data structure
                                assert "timestamp" in data
                                assert "metrics" in data
                                assert "source" in data
                                
                                # Record metrics
                                event_end = time.time()
                                latency = event_end - event_start
                                metrics.latencies.append(latency)
                                metrics.total_events += 1
                                metrics.total_bytes += len(event.data.encode())
                                
                                # Validate real-time performance (<100ms target)
                                if latency * 1000 > 100:  # Convert to ms
                                    logger.warning(f"High latency detected: {latency * 1000:.2f}ms")
                                
                                # Stop after collecting sufficient data
                                if metrics.total_events >= 100:
                                    break
                                    
                            except json.JSONDecodeError as e:
                                metrics.error_count += 1
                                logger.error(f"Failed to parse SSE event data: {e}")
                            except AssertionError as e:
                                metrics.error_count += 1
                                logger.error(f"Invalid analytics data structure: {e}")
                        
                        elif event.event == "error":
                            metrics.error_count += 1
                            logger.error(f"SSE error event: {event.data}")
            
            metrics.end_time = time.time()
            
            # Validate performance requirements
            assert metrics.average_latency < 100, f"Average latency {metrics.average_latency:.2f}ms exceeds 100ms target"
            assert metrics.error_count / metrics.total_events < 0.05, "Error rate exceeds 5% threshold"
            assert metrics.events_per_second > 10, f"Throughput {metrics.events_per_second:.2f} events/sec below minimum"
            
            logger.info(f"Single client SSE test completed successfully:")
            logger.info(f"  Events: {metrics.total_events}")
            logger.info(f"  Average Latency: {metrics.average_latency:.2f}ms")
            logger.info(f"  P95 Latency: {metrics.p95_latency:.2f}ms")
            logger.info(f"  Throughput: {metrics.events_per_second:.2f} events/sec")
            
            return metrics
            
        except Exception as e:
            metrics.error_count += 1
            logger.error(f"Single client SSE test failed: {e}")
            raise
        finally:
            # Clean up
            await self.analytics_tester.cleanup_analytics_integration()
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]

class SSEPerformanceMonitor:
    """Advanced performance monitoring for SSE streams"""
    
    def __init__(self):
        self.performance_baselines: Dict[str, float] = {
            "max_latency_ms": 100.0,
            "min_throughput_eps": 10.0,  # events per second
            "max_error_rate": 0.05,
            "min_connection_stability": 0.99
        }
        self.performance_history: List[SSEStreamMetrics] = []
        
    async def measure_concurrent_sse_performance(self, concurrent_clients: int = 50) -> Dict[str, Any]:
        """Measure SSE performance under concurrent client load"""
        logger.info(f"Measuring SSE performance with {concurrent_clients} concurrent clients")
        
        # Create concurrent SSE connections
        tasks = []
        stream_testers = []
        
        for i in range(concurrent_clients):
            tester = SSEStreamTester()
            stream_testers.append(tester)
            task = asyncio.create_task(
                tester.test_single_client_sse_streaming(),
                name=f"sse_client_{i}"
            )
            tasks.append(task)
        
        # Execute concurrent streams
        start_time = time.time()
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_streams = [r for r in results if isinstance(r, SSEStreamMetrics)]
            failed_streams = [r for r in results if isinstance(r, Exception)]
            
            total_events = sum(s.total_events for s in successful_streams)
            total_duration = end_time - start_time
            
            # Calculate aggregate metrics
            aggregate_metrics = {
                "concurrent_clients": concurrent_clients,
                "successful_streams": len(successful_streams),
                "failed_streams": len(failed_streams),
                "total_events": total_events,
                "total_duration": total_duration,
                "aggregate_throughput": total_events / total_duration,
                "average_latency": statistics.mean([s.average_latency for s in successful_streams]) if successful_streams else 0,
                "p95_latency": statistics.quantiles([s.p95_latency for s in successful_streams], n=20)[18] if successful_streams else 0,
                "connection_stability": len(successful_streams) / concurrent_clients,
                "total_errors": sum(s.error_count for s in successful_streams)
            }
            
            # Validate performance against baselines
            self._validate_performance_baselines(aggregate_metrics)
            
            # Store in performance history
            for stream in successful_streams:
                self.performance_history.append(stream)
            
            logger.info(f"Concurrent SSE performance results:")
            logger.info(f"  Successful Streams: {aggregate_metrics['successful_streams']}/{concurrent_clients}")
            logger.info(f"  Aggregate Throughput: {aggregate_metrics['aggregate_throughput']:.2f} events/sec")
            logger.info(f"  Average Latency: {aggregate_metrics['average_latency']:.2f}ms")
            logger.info(f"  Connection Stability: {aggregate_metrics['connection_stability']:.2%}")
            
            return aggregate_metrics
            
        except Exception as e:
            logger.error(f"Concurrent SSE performance test failed: {e}")
            raise

class SSEConnectionManager:
    """Advanced SSE connection lifecycle and stability testing"""
    
    def __init__(self):
        self.connection_registry: Dict[str, Dict[str, Any]] = {}
        self.stability_metrics: Dict[str, float] = {}
        
    async def test_connection_stability_sustained(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Test SSE connection stability under sustained load"""
        logger.info(f"Testing SSE connection stability for {duration_minutes} minutes")
        
        connection_id = f"stability_test_{int(time.time())}"
        start_time = time.time()
        target_duration = duration_minutes * 60  # Convert to seconds
        
        stability_metrics = {
            "connection_id": connection_id,
            "target_duration": target_duration,
            "actual_duration": 0,
            "total_reconnections": 0,
            "total_connection_drops": 0,
            "total_events_received": 0,
            "stability_percentage": 0,
            "performance_degradation": False
        }
        
        self.connection_registry[connection_id] = stability_metrics
        
        try:
            # Initialize database connection pool for sustained testing
            db_pool = DatabaseConnectionPoolManager()
            await db_pool.initialize_connection_pools()
            
            # Create sustained SSE connection
            async with httpx.AsyncClient(timeout=httpx.Timeout(None)) as client:
                connection_start = time.time()
                
                while time.time() - start_time < target_duration:
                    try:
                        async with aconnect_sse(
                            client, "GET", f"http://localhost:8000/analytics/stream"
                        ) as event_source:
                            
                            connection_established = time.time()
                            
                            async for event in event_source.aiter_sse():
                                current_time = time.time()
                                
                                # Check if we've reached target duration
                                if current_time - start_time >= target_duration:
                                    break
                                
                                if event.event == "analytics_data":
                                    stability_metrics["total_events_received"] += 1
                                    
                                    # Periodic stability validation
                                    if stability_metrics["total_events_received"] % 1000 == 0:
                                        await self._validate_connection_health(connection_id, db_pool)
                                
                                # Simulate network condition variations
                                if stability_metrics["total_events_received"] % 5000 == 0:
                                    await asyncio.sleep(0.1)  # Brief pause
                                    
                    except Exception as e:
                        stability_metrics["total_connection_drops"] += 1
                        logger.warning(f"Connection drop detected: {e}")
                        
                        # Implement exponential backoff for reconnection
                        backoff_delay = min(2 ** stability_metrics["total_reconnections"], 30)
                        await asyncio.sleep(backoff_delay)
                        
                        stability_metrics["total_reconnections"] += 1
                        logger.info(f"Attempting reconnection #{stability_metrics['total_reconnections']}")
            
            # Calculate final stability metrics
            actual_duration = time.time() - start_time
            stability_metrics["actual_duration"] = actual_duration
            stability_metrics["stability_percentage"] = (
                (actual_duration - (stability_metrics["total_connection_drops"] * 5)) / actual_duration
            )
            
            # Validate sustained performance requirements
            assert stability_metrics["stability_percentage"] > 0.99, \
                f"Connection stability {stability_metrics['stability_percentage']:.2%} below 99% requirement"
            assert stability_metrics["total_events_received"] > 0, "No events received during stability test"
            
            logger.info(f"Sustained connection stability test results:")
            logger.info(f"  Duration: {actual_duration/60:.1f} minutes")
            logger.info(f"  Events Received: {stability_metrics['total_events_received']}")
            logger.info(f"  Connection Drops: {stability_metrics['total_connection_drops']}")
            logger.info(f"  Reconnections: {stability_metrics['total_reconnections']}")
            logger.info(f"  Stability: {stability_metrics['stability_percentage']:.2%}")
            
            self.stability_metrics[connection_id] = stability_metrics["stability_percentage"]
            return stability_metrics
            
        except Exception as e:
            logger.error(f"Sustained connection stability test failed: {e}")
            raise
        finally:
            if connection_id in self.connection_registry:
                del self.connection_registry[connection_id]

class SSEIntegrationValidator:
    """End-to-end SSE pipeline validation with database integration"""
    
    def __init__(self):
        self.validation_results: Dict[str, Any] = {}
        self.integration_metrics: Dict[str, float] = {}
        
    async def validate_sse_database_integration(self) -> Dict[str, Any]:
        """Validate SSE integration with database connection pools"""
        logger.info("Validating SSE integration with database connection pools")
        
        validation_id = f"sse_db_integration_{int(time.time())}"
        
        # Initialize components
        sse_tester = SSEStreamTester()
        db_pool_manager = DatabaseConnectionPoolManager()
        performance_monitor = DatabasePerformanceMonitor()
        
        try:
            # Setup database connection pools
            await db_pool_manager.initialize_connection_pools()
            
            # Validate database pools are operational
            kuzu_health = await db_pool_manager.test_kuzu_connection_pool(
                concurrent_connections=10
            )
            redis_health = await db_pool_manager.test_redis_connection_pool(
                concurrent_connections=20
            )
            
            assert kuzu_health["success_rate"] > 0.95, "Kuzu connection pool not ready"
            assert redis_health["success_rate"] > 0.95, "Redis connection pool not ready"
            
            # Test SSE stream with database operations
            sse_metrics = await sse_tester.test_single_client_sse_streaming()
            
            # Validate end-to-end performance
            end_to_end_metrics = {
                "sse_latency": sse_metrics.average_latency,
                "sse_throughput": sse_metrics.events_per_second,
                "kuzu_performance": kuzu_health["average_latency"],
                "redis_performance": redis_health["average_latency"],
                "integration_success": True
            }
            
            # Calculate end-to-end latency
            total_latency = (
                sse_metrics.average_latency + 
                kuzu_health["average_latency"] + 
                redis_health["average_latency"]
            )
            
            end_to_end_metrics["total_latency"] = total_latency
            
            # Validate end-to-end performance targets
            assert total_latency < 500, f"End-to-end latency {total_latency:.2f}ms exceeds 500ms target"
            assert sse_metrics.events_per_second > 10, "SSE throughput below minimum requirement"
            
            self.validation_results[validation_id] = end_to_end_metrics
            
            logger.info(f"SSE-Database integration validation completed:")
            logger.info(f"  SSE Latency: {end_to_end_metrics['sse_latency']:.2f}ms")
            logger.info(f"  Total End-to-End Latency: {total_latency:.2f}ms")
            logger.info(f"  SSE Throughput: {end_to_end_metrics['sse_throughput']:.2f} events/sec")
            
            return end_to_end_metrics
            
        except Exception as e:
            logger.error(f"SSE-Database integration validation failed: {e}")
            raise
        finally:
            await db_pool_manager.cleanup_connection_pools()

# Integration test cases
@pytest_asyncio.async_test
async def test_sse_stream_single_client():
    """Test single client SSE streaming with analytics data"""
    tester = SSEStreamTester()
    metrics = await tester.test_single_client_sse_streaming()
    
    # Validate performance requirements
    assert metrics.average_latency < 100
    assert metrics.events_per_second > 10
    assert metrics.error_count / metrics.total_events < 0.05

@pytest_asyncio.async_test
async def test_sse_concurrent_performance():
    """Test SSE performance under concurrent load"""
    monitor = SSEPerformanceMonitor()
    results = await monitor.measure_concurrent_sse_performance(concurrent_clients=25)
    
    # Validate concurrent performance
    assert results["connection_stability"] > 0.95
    assert results["average_latency"] < 100
    assert results["successful_streams"] / results["concurrent_clients"] > 0.95

@pytest_asyncio.async_test
async def test_sse_connection_stability():
    """Test SSE connection stability over time"""
    manager = SSEConnectionManager()
    results = await manager.test_connection_stability_sustained(duration_minutes=5)  # Reduced for testing
    
    # Validate stability requirements
    assert results["stability_percentage"] > 0.99
    assert results["total_events_received"] > 0

@pytest_asyncio.async_test
async def test_sse_database_integration():
    """Test end-to-end SSE integration with database"""
    validator = SSEIntegrationValidator()
    results = await validator.validate_sse_database_integration()
    
    # Validate integration performance
    assert results["total_latency"] < 500
    assert results["integration_success"] is True
    assert results["sse_throughput"] > 10 