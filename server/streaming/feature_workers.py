"""
Feature Engineering Workers for GraphMemory-IDE Analytics Pipeline

This module implements async workers that consume from DragonflyDB streams
and generate real-time features for analytics and pattern detection.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import numpy as np
import redis

from .dragonfly_config import get_dragonfly_client

logger = logging.getLogger(__name__)

@dataclass
class WindowedFeature:
    """A feature computed over a time window"""
    feature_name: str
    window_size_seconds: int
    timestamp: str
    value: Union[int, float, Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PatternDetection:
    """A detected pattern in the data"""
    pattern_type: str
    confidence: float
    timestamp: str
    description: str
    data: Dict[str, Any] = field(default_factory=dict)

class TimeWindow:
    """Implements tumbling and sliding time windows"""
    
    def __init__(self, size_seconds: int, slide_seconds: Optional[int] = None) -> None:
        self.size_seconds = size_seconds
        self.slide_seconds = slide_seconds or size_seconds  # Default to tumbling window
        self.events: deque = deque()
        self._last_slide = time.time()
    
    def add_event(self, event: Dict[str, Any], timestamp: float) -> None:
        """Add event to the window"""
        self.events.append((timestamp, event))
        self._cleanup_old_events()
    
    def _cleanup_old_events(self) -> None:
        """Remove events outside the window"""
        cutoff_time = time.time() - self.size_seconds
        while self.events and self.events[0][0] < cutoff_time:
            self.events.popleft()
    
    def get_events(self) -> List[Tuple[float, Dict[str, Any]]]:
        """Get all events in the current window"""
        self._cleanup_old_events()
        return list(self.events)
    
    def should_slide(self) -> bool:
        """Check if window should slide (for sliding windows)"""
        return time.time() - self._last_slide >= self.slide_seconds
    
    def slide(self) -> None:
        """Slide the window"""
        self._last_slide = time.time()

class MemoryOperationFeatureWorker:
    """Worker for computing memory operation features"""
    
    def __init__(self, consumer_group: str = "memory_features") -> None:
        """Initialize memory operation feature worker"""
        self.consumer_group = consumer_group
        self.consumer_name = f"memory_worker_{int(time.time())}"
        self.stream_name = "analytics:memory_operations"
        self.client: Optional[redis.Redis] = None
        self.running = False
        
        # Time windows for different aggregations
        self.windows = {
            "1min": TimeWindow(60, 30),
            "5min": TimeWindow(300, 150),
            "15min": TimeWindow(900, 450),
            "1hour": TimeWindow(3600, 1800)
        }
        
        # Feature accumulators
        self.features: Dict[str, List[WindowedFeature]] = defaultdict(list)
        self.operation_counts: defaultdict[str, int] = defaultdict(int)
        self.processing_times = deque(maxlen=1000)
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the feature worker"""
        if self._running:
            return
        
        logger.info(f"Starting Memory Operation Feature Worker: {self.consumer_name}")
        
        try:
            client = await get_dragonfly_client()
            
            # Create consumer group if it doesn't exist
            try:
                await client.xgroup_create(
                    name=self.stream_name,
                    groupname=self.consumer_group,
                    id="0",
                    mkstream=True
                )
                logger.info(f"Created consumer group: {self.consumer_group}")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"Failed to create consumer group: {e}")
            
            self._running = True
            self._task = asyncio.create_task(self._process_stream())
            
        except Exception as e:
            logger.error(f"Failed to start memory operation feature worker: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the feature worker"""
        if not self._running:
            return
        
        logger.info(f"Stopping Memory Operation Feature Worker: {self.consumer_name}")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _process_stream(self) -> None:
        """Main processing loop"""
        client = await get_dragonfly_client()
        
        while self._running:
            try:
                # Read from stream
                messages = await client.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_name: ">"},
                    count=10,
                    block=1000  # Block for 1 second
                )
                
                for stream_name, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._process_message(message_id, fields, client)
                
                # Compute windowed features
                await self._compute_windowed_features()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing memory operation stream: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(self, message_id: str, fields: Dict[str, Any], client) -> None:
        """Process a single message"""
        try:
            # Parse timestamp
            timestamp = fields.get("timestamp", datetime.utcnow().isoformat())
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
            
            # Add to time windows
            for window in self.windows.values():
                window.add_event(fields, ts)
            
            # Track operation counts
            operation_type = fields.get("operation_type", "unknown")
            self.operation_counts[operation_type] += 1
            
            # Track processing times
            processing_time = float(fields.get("processing_time_ms", 0))
            self.processing_times.append(processing_time)
            
            # Acknowledge message
            await client.xack(self.stream_name, self.consumer_group, message_id)
            
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
    
    async def _compute_windowed_features(self) -> None:
        """Compute features over time windows"""
        current_time = datetime.utcnow().isoformat()
        
        for window_name, window in self.windows.items():
            if window_name.startswith("sliding") and not window.should_slide():
                continue
            
            events = window.get_events()
            if not events:
                continue
            
            # Compute features for this window
            features = []
            
            # 1. Operation rate (operations per second)
            if events:
                duration = max(1.0, events[-1][0] - events[0][0])  # Avoid division by zero
                operation_rate = len(events) / duration
                features.append(WindowedFeature(
                    feature_name=f"memory_operation_rate_{window_name}",
                    window_size_seconds=window.size_seconds,
                    timestamp=current_time,
                    value=operation_rate,
                    metadata={"unit": "operations_per_second"}
                ))
            
            # 2. Operation type distribution
            op_types = [
                event_data.get("operation_type", "unknown") 
                for _, event_data in events 
                if isinstance(event_data, dict)
            ]
            op_distribution = {}
            for op_type in set(op_types):
                op_distribution[op_type] = op_types.count(op_type) / len(op_types)
            
            features.append(WindowedFeature(
                feature_name=f"operation_type_distribution_{window_name}",
                window_size_seconds=window.size_seconds,
                timestamp=current_time,
                value=op_distribution,
                metadata={"unit": "percentage"}
            ))
            
            # 3. Processing time statistics
            processing_times = [
                float(event_data.get("processing_time_ms", 0)) 
                for _, event_data in events 
                if isinstance(event_data, dict) and event_data.get("processing_time_ms", 0) > 0
            ]
            
            if processing_times:
                features.append(WindowedFeature(
                    feature_name=f"processing_time_stats_{window_name}",
                    window_size_seconds=window.size_seconds,
                    timestamp=current_time,
                    value={
                        "mean": statistics.mean(processing_times),
                        "median": statistics.median(processing_times),
                        "min": min(processing_times),
                        "max": max(processing_times),
                        "std": statistics.stdev(processing_times) if len(processing_times) > 1 else 0
                    },
                    metadata={"sample_size": len(processing_times)}
                ))
            
            # 4. Entity and relation counts
            entity_counts = [
                int(event_data.get("entity_count", 0)) 
                for _, event_data in events
            ]
            relation_counts = [
                int(event_data.get("relation_count", 0)) 
                for _, event_data in events
            ]
            
            if entity_counts:
                features.append(WindowedFeature(
                    feature_name=f"entity_creation_stats_{window_name}",
                    window_size_seconds=window.size_seconds,
                    timestamp=current_time,
                    value={
                        "total_entities": sum(entity_counts),
                        "average_per_operation": sum(entity_counts) / len(entity_counts),
                        "max_per_operation": max(entity_counts)
                    }
                ))
            
            if relation_counts:
                features.append(WindowedFeature(
                    feature_name=f"relation_creation_stats_{window_name}",
                    window_size_seconds=window.size_seconds,
                    timestamp=current_time,
                    value={
                        "total_relations": sum(relation_counts),
                        "average_per_operation": sum(relation_counts) / len(relation_counts),
                        "max_per_operation": max(relation_counts)
                    }
                ))
            
            # Store computed features
            for feature in features:
                self.features[feature.feature_name].append(feature)
                # Keep only last 100 features per type
                if len(self.features[feature.feature_name]) > 100:
                    self.features[feature.feature_name].pop(0)
            
            # Slide window if needed
            if window_name.startswith("sliding"):
                window.slide()
    
    async def get_features(self, feature_names: Optional[List[str]] = None) -> Dict[str, List[WindowedFeature]]:
        """Get computed features"""
        if feature_names:
            return {name: self.features[name] for name in feature_names if name in self.features}
        return dict(self.features)
    
    async def get_latest_features(self) -> Dict[str, WindowedFeature]:
        """Get the latest feature values"""
        latest = {}
        for feature_name, feature_list in self.features.items():
            if feature_list:
                latest[feature_name] = feature_list[-1]
        return latest

class PatternDetectionWorker:
    """Worker for detecting patterns across all streams"""
    
    def __init__(self, consumer_group: str = "pattern_detection") -> None:
        self.consumer_group = consumer_group
        self.consumer_name = f"pattern_worker_{int(time.time())}"
        self.streams = [
            "analytics:memory_operations",
            "analytics:user_interactions",
            "analytics:system_metrics"
        ]
        
        self.patterns: List[PatternDetection] = []
        self.anomaly_thresholds = {
            "memory_operation_rate": {"min": 0.1, "max": 10.0},  # ops/sec
            "processing_time_mean": {"max": 1000.0},  # ms
            "entity_creation_rate": {"max": 100.0},  # entities/sec
        }
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the pattern detection worker"""
        if self._running:
            return
        
        logger.info(f"Starting Pattern Detection Worker: {self.consumer_name}")
        
        try:
            client = await get_dragonfly_client()
            
            # Create consumer groups for all streams
            for stream_name in self.streams:
                try:
                    await client.xgroup_create(
                        name=stream_name,
                        groupname=self.consumer_group,
                        id="0",
                        mkstream=True
                    )
                except Exception as e:
                    if "BUSYGROUP" not in str(e):
                        logger.warning(f"Failed to create consumer group for {stream_name}: {e}")
            
            self._running = True
            self._task = asyncio.create_task(self._detect_patterns())
            
        except Exception as e:
            logger.error(f"Failed to start pattern detection worker: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the pattern detection worker"""
        if not self._running:
            return
        
        logger.info(f"Stopping Pattern Detection Worker: {self.consumer_name}")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _detect_patterns(self) -> None:
        """Main pattern detection loop"""
        client = await get_dragonfly_client()
        
        while self._running:
            try:
                # Read from all streams
                stream_dict = {stream: ">" for stream in self.streams}
                messages = await client.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams=stream_dict,
                    count=10,
                    block=1000
                )
                
                for stream_name, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._analyze_for_patterns(stream_name, fields, client)
                        await client.xack(stream_name, self.consumer_group, message_id)
                
                # Periodic pattern analysis
                await self._periodic_analysis()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pattern detection: {e}")
                await asyncio.sleep(1)
    
    async def _analyze_for_patterns(self, stream_name: str, fields: Dict[str, Any], client) -> None:
        """Analyze individual events for patterns"""
        try:
            timestamp = fields.get("timestamp", datetime.utcnow().isoformat())
            
            # Anomaly detection for memory operations
            if stream_name == "analytics:memory_operations":
                await self._detect_memory_anomalies(fields, timestamp)
            
            # User behavior pattern detection
            elif stream_name == "analytics:user_interactions":
                await self._detect_user_patterns(fields, timestamp)
            
            # System metric anomalies
            elif stream_name == "analytics:system_metrics":
                await self._detect_system_anomalies(fields, timestamp)
                
        except Exception as e:
            logger.error(f"Error analyzing pattern for {stream_name}: {e}")
    
    async def _detect_memory_anomalies(self, fields: Dict[str, Any], timestamp: str) -> None:
        """Detect anomalies in memory operations"""
        processing_time = float(fields.get("processing_time_ms", 0))
        
        # High processing time anomaly
        if processing_time > self.anomaly_thresholds["processing_time_mean"]["max"]:
            pattern = PatternDetection(
                pattern_type="high_processing_time_anomaly",
                confidence=min(1.0, processing_time / 2000.0),  # Scale confidence
                timestamp=timestamp,
                description=f"High processing time detected: {processing_time:.2f}ms",
                data={
                    "processing_time_ms": processing_time,
                    "threshold": self.anomaly_thresholds["processing_time_mean"]["max"],
                    "operation_type": fields.get("operation_type")
                }
            )
            self.patterns.append(pattern)
    
    async def _detect_user_patterns(self, fields: Dict[str, Any], timestamp: str) -> None:
        """Detect patterns in user interactions"""
        # Implement user pattern detection
        interaction_type = fields.get("interaction_type")
        duration = float(fields.get("duration_ms", 0))
        
        # Long interaction pattern
        if duration > 30000:  # 30 seconds
            pattern = PatternDetection(
                pattern_type="long_user_interaction",
                confidence=0.8,
                timestamp=timestamp,
                description=f"Long user interaction detected: {duration/1000:.1f}s",
                data={
                    "interaction_type": interaction_type,
                    "duration_ms": duration,
                    "user_id": fields.get("user_id")
                }
            )
            self.patterns.append(pattern)
    
    async def _detect_system_anomalies(self, fields: Dict[str, Any], timestamp: str) -> None:
        """Detect system metric anomalies"""
        metric_name = fields.get("metric_name")
        metric_value = fields.get("metric_value")
        
        # Implement system anomaly detection based on metric type
        if metric_name and metric_value is not None:
            # CPU usage spike
            if metric_name == "cpu_usage" and float(metric_value) > 90.0:
                pattern = PatternDetection(
                    pattern_type="high_cpu_usage",
                    confidence=0.9,
                    timestamp=timestamp,
                    description=f"High CPU usage detected: {metric_value}%",
                    data={
                        "metric_name": metric_name,
                        "metric_value": metric_value,
                        "threshold": 90.0
                    }
                )
                self.patterns.append(pattern)
    
    async def _periodic_analysis(self) -> None:
        """Perform periodic pattern analysis"""
        # Clean up old patterns (keep last 1000)
        if len(self.patterns) > 1000:
            self.patterns = self.patterns[-1000:]
    
    async def get_patterns(self, pattern_types: Optional[List[str]] = None) -> List[PatternDetection]:
        """Get detected patterns"""
        if pattern_types:
            return [p for p in self.patterns if p.pattern_type in pattern_types]
        return self.patterns.copy()

class FeatureWorkerManager:
    """Manages all feature engineering workers"""
    
    def __init__(self) -> None:
        """Initialize feature worker manager"""
        self.workers: Dict[str, Union[MemoryOperationFeatureWorker, PatternDetectionWorker]] = {}
        self.running = False
        self.memory_worker = MemoryOperationFeatureWorker()
        self.pattern_worker = PatternDetectionWorker()
        self._workers: List[Union[MemoryOperationFeatureWorker, PatternDetectionWorker]] = [self.memory_worker, self.pattern_worker]
    
    async def start(self) -> None:
        """Start all workers"""
        if self.running:
            return
        
        logger.info("Starting Feature Worker Manager")
        
        for worker in self._workers:
            await worker.start()
        
        self.running = True
        logger.info("All feature workers started")
    
    async def stop(self) -> None:
        """Stop all workers"""
        if not self.running:
            return
        
        logger.info("Stopping Feature Worker Manager")
        
        for worker in self._workers:
            await worker.stop()
        
        self.running = False
        logger.info("All feature workers stopped")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get status of all workers"""
        return {
            "running": self.running,
            "workers": {
                "memory_feature_worker": {
                    "running": self.memory_worker._running,
                    "features_computed": len(self.memory_worker.features)
                },
                "pattern_detection_worker": {
                    "running": self.pattern_worker._running,
                    "patterns_detected": len(self.pattern_worker.patterns)
                }
            }
        }

# Global worker manager
_worker_manager: Optional[FeatureWorkerManager] = None

async def get_worker_manager() -> FeatureWorkerManager:
    """Get the global worker manager"""
    global _worker_manager
    if not _worker_manager:
        raise RuntimeError("Feature worker manager not initialized")
    return _worker_manager

async def initialize_feature_workers() -> None:
    """Initialize feature workers"""
    global _worker_manager
    _worker_manager = FeatureWorkerManager()
    await _worker_manager.start()

async def shutdown_feature_workers() -> None:
    """Shutdown feature workers"""
    global _worker_manager
    if _worker_manager:
        await _worker_manager.stop()
        _worker_manager = None 