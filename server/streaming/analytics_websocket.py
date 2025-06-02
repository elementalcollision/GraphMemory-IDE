"""
Real-time Analytics WebSocket API for GraphMemory-IDE

This module provides WebSocket endpoints for streaming real-time analytics
features and patterns to dashboard clients with authentication and connection management.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import asdict
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .dragonfly_config import get_dragonfly_stats, benchmark_dragonfly
from .stream_producer import get_stream_producer
from .feature_workers import get_worker_manager
from ..auth import get_optional_current_user

logger = logging.getLogger(__name__)

class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str
    data: Dict[str, Any]
    timestamp: str
    client_id: Optional[str] = None

class SubscriptionRequest(BaseModel):
    """Client subscription request"""
    event_types: List[str]
    feature_names: Optional[List[str]] = None
    pattern_types: Optional[List[str]] = None
    update_interval: int = 1000  # milliseconds

class ConnectionManager:
    """Manages WebSocket connections for real-time analytics"""
    
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, SubscriptionRequest] = {}
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_failed": 0,
        }
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the connection manager"""
        if self._running:
            return
        
        logger.info("Starting WebSocket Connection Manager")
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("WebSocket Connection Manager started")
    
    async def stop(self) -> None:
        """Stop the connection manager"""
        if not self._running:
            return
        
        logger.info("Stopping WebSocket Connection Manager")
        self._running = False
        
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing connection {client_id}: {e}")
        
        self.active_connections.clear()
        self.client_subscriptions.clear()
        logger.info("WebSocket Connection Manager stopped")
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_stats["total_connections"] += 1
        self.connection_stats["active_connections"] = len(self.active_connections)
        
        logger.info(f"WebSocket connected: {client_id} (total: {len(self.active_connections)})")
        
        # Send welcome message
        welcome_msg = WebSocketMessage(
            type="connection_established",
            data={
                "client_id": client_id,
                "server_time": datetime.utcnow().isoformat(),
                "available_subscriptions": [
                    "features", "patterns", "stream_stats", "system_status"
                ]
            },
            timestamp=datetime.utcnow().isoformat(),
            client_id=client_id
        )
        await self._send_to_client(client_id, welcome_msg)
    
    async def disconnect(self, client_id: str) -> None:
        """Handle WebSocket disconnection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
        
        self.connection_stats["active_connections"] = len(self.active_connections)
        logger.info(f"WebSocket disconnected: {client_id} (remaining: {len(self.active_connections)})")
    
    async def subscribe(self, client_id: str, subscription: SubscriptionRequest) -> None:
        """Subscribe client to specific data streams"""
        if client_id not in self.active_connections:
            return False
        
        self.client_subscriptions[client_id] = subscription
        logger.info(f"Client {client_id} subscribed to: {subscription.event_types}")
        
        # Send subscription confirmation
        confirmation = WebSocketMessage(
            type="subscription_confirmed",
            data={
                "event_types": subscription.event_types,
                "update_interval": subscription.update_interval
            },
            timestamp=datetime.utcnow().isoformat(),
            client_id=client_id
        )
        await self._send_to_client(client_id, confirmation)
        return True
    
    async def _send_to_client(self, client_id: str, message: WebSocketMessage) -> None:
        """Send message to a specific client"""
        if client_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message.json())
            self.connection_stats["messages_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
            self.connection_stats["messages_failed"] += 1
            await self.disconnect(client_id)
            return False
    
    async def broadcast(self, message: WebSocketMessage, event_type: str) -> None:
        """Broadcast message to subscribed clients"""
        if not self.active_connections:
            return
        
        # Find clients subscribed to this event type
        target_clients = []
        for client_id, subscription in self.client_subscriptions.items():
            if event_type in subscription.event_types:
                target_clients.append(client_id)
        
        # Send to target clients
        send_tasks = []
        for client_id in target_clients:
            send_tasks.append(self._send_to_client(client_id, message))
        
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
    
    async def _broadcast_loop(self) -> None:
        """Main broadcasting loop"""
        last_feature_update = 0
        last_pattern_update = 0
        last_stats_update = 0
        
        while self._running:
            try:
                current_time = time.time()
                
                # Check if we have any subscribed clients
                if not self.client_subscriptions:
                    await asyncio.sleep(1)
                    continue
                
                # Broadcast features (every 2 seconds)
                if current_time - last_feature_update >= 2:
                    await self._broadcast_features()
                    last_feature_update = current_time
                
                # Broadcast patterns (every 5 seconds)
                if current_time - last_pattern_update >= 5:
                    await self._broadcast_patterns()
                    last_pattern_update = current_time
                
                # Broadcast stats (every 10 seconds)
                if current_time - last_stats_update >= 10:
                    await self._broadcast_stats()
                    last_stats_update = current_time
                
                await asyncio.sleep(0.5)  # Check every 500ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                await asyncio.sleep(1)
    
    async def _broadcast_features(self) -> None:
        """Broadcast latest features to subscribed clients"""
        try:
            worker_manager = await get_worker_manager()
            latest_features = await worker_manager.memory_worker.get_latest_features()
            
            if latest_features:
                # Convert WindowedFeature objects to dict
                features_data = {}
                for name, feature in latest_features.items():
                    features_data[name] = {
                        "feature_name": feature.feature_name,
                        "window_size_seconds": feature.window_size_seconds,
                        "timestamp": feature.timestamp,
                        "value": feature.value,
                        "metadata": feature.metadata
                    }
                
                message = WebSocketMessage(
                    type="features_update",
                    data={
                        "features": features_data,
                        "update_time": datetime.utcnow().isoformat()
                    },
                    timestamp=datetime.utcnow().isoformat()
                )
                
                await self.broadcast(message, "features")
                
        except Exception as e:
            logger.error(f"Error broadcasting features: {e}")
    
    async def _broadcast_patterns(self) -> None:
        """Broadcast detected patterns to subscribed clients"""
        try:
            worker_manager = await get_worker_manager()
            recent_patterns = await worker_manager.pattern_worker.get_patterns()
            
            # Get patterns from last 5 minutes
            cutoff_time = datetime.utcnow().timestamp() - 300  # 5 minutes
            recent_patterns = [
                p for p in recent_patterns 
                if datetime.fromisoformat(p.timestamp.replace('Z', '+00:00')).timestamp() > cutoff_time
            ]
            
            if recent_patterns:
                patterns_data = []
                for pattern in recent_patterns:
                    patterns_data.append({
                        "pattern_type": pattern.pattern_type,
                        "confidence": pattern.confidence,
                        "timestamp": pattern.timestamp,
                        "description": pattern.description,
                        "data": pattern.data
                    })
                
                message = WebSocketMessage(
                    type="patterns_update",
                    data={
                        "patterns": patterns_data,
                        "update_time": datetime.utcnow().isoformat()
                    },
                    timestamp=datetime.utcnow().isoformat()
                )
                
                await self.broadcast(message, "patterns")
                
        except Exception as e:
            logger.error(f"Error broadcasting patterns: {e}")
    
    async def _broadcast_stats(self) -> None:
        """Broadcast system statistics to subscribed clients"""
        try:
            # Get DragonflyDB stats
            dragonfly_stats = await get_dragonfly_stats()
            
            # Get stream producer stats
            try:
                producer = await get_stream_producer()
                producer_stats = await producer.get_stats()
                stream_info = await producer.get_stream_info()
            except Exception:
                producer_stats = {"error": "Producer not available"}
                stream_info = {}
            
            # Get worker stats
            try:
                worker_manager = await get_worker_manager()
                worker_stats = await worker_manager.get_system_status()
            except Exception:
                worker_stats = {"error": "Workers not available"}
            
            message = WebSocketMessage(
                type="system_stats_update",
                data={
                    "dragonfly": dragonfly_stats,
                    "stream_producer": producer_stats,
                    "stream_info": stream_info,
                    "feature_workers": worker_stats,
                    "websocket_connections": self.connection_stats,
                    "update_time": datetime.utcnow().isoformat()
                },
                timestamp=datetime.utcnow().isoformat()
            )
            
            await self.broadcast(message, "system_status")
            
        except Exception as e:
            logger.error(f"Error broadcasting stats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        return {
            **self.connection_stats,
            "subscribed_clients": len(self.client_subscriptions),
            "running": self._running
        }

# Global connection manager
connection_manager = ConnectionManager()

# FastAPI router for analytics endpoints
def create_analytics_router() -> FastAPI:
    """Create FastAPI router with analytics endpoints"""
    
    router = FastAPI()
    
    @router.websocket("/ws/analytics/{client_id}")
    async def analytics_websocket(websocket: WebSocket, client_id: str) -> None:
        """WebSocket endpoint for real-time analytics"""
        await connection_manager.connect(websocket, client_id)
        try:
            while True:
                # Receive subscription requests from client
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    
                    if message.get("type") == "subscribe":
                        subscription_data = message.get("data", {})
                        subscription = SubscriptionRequest(**subscription_data)
                        await connection_manager.subscribe(client_id, subscription)
                    
                    elif message.get("type") == "ping":
                        # Respond to ping with pong
                        pong = WebSocketMessage(
                            type="pong",
                            data={"server_time": datetime.utcnow().isoformat()},
                            timestamp=datetime.utcnow().isoformat(),
                            client_id=client_id
                        )
                        await connection_manager._send_to_client(client_id, pong)
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from client {client_id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}")
                    
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
        finally:
            await connection_manager.disconnect(client_id)
    
    @router.get("/api/analytics/features")
    async def get_features(
        feature_names: Optional[str] = Query(None, description="Comma-separated feature names"),
        window: Optional[str] = Query(None, description="Time window (1min, 5min, 1hour)"),
        current_user = Depends(get_optional_current_user)
    ):
        """Get computed features"""
        try:
            worker_manager = await get_worker_manager()
            
            # Parse feature names
            requested_features = None
            if feature_names:
                requested_features = [name.strip() for name in feature_names.split(",")]
            
            # Filter by window if specified
            if window and requested_features:
                requested_features = [
                    name for name in requested_features 
                    if window in name
                ]
            
            features = await worker_manager.memory_worker.get_features(requested_features)
            
            # Convert to JSON-serializable format
            result = {}
            for name, feature_list in features.items():
                result[name] = []
                for feature in feature_list:
                    result[name].append({
                        "feature_name": feature.feature_name,
                        "window_size_seconds": feature.window_size_seconds,
                        "timestamp": feature.timestamp,
                        "value": feature.value,
                        "metadata": feature.metadata
                    })
            
            return {"features": result, "timestamp": datetime.utcnow().isoformat()}
            
        except Exception as e:
            logger.error(f"Error getting features: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/api/analytics/patterns")
    async def get_patterns(
        pattern_types: Optional[str] = Query(None, description="Comma-separated pattern types"),
        limit: int = Query(100, description="Maximum number of patterns to return"),
        current_user = Depends(get_optional_current_user)
    ):
        """Get detected patterns"""
        try:
            worker_manager = await get_worker_manager()
            
            # Parse pattern types
            requested_types = None
            if pattern_types:
                requested_types = [ptype.strip() for ptype in pattern_types.split(",")]
            
            patterns = await worker_manager.pattern_worker.get_patterns(requested_types)
            
            # Limit results
            patterns = patterns[-limit:] if len(patterns) > limit else patterns
            
            # Convert to JSON-serializable format
            result = []
            for pattern in patterns:
                result.append({
                    "pattern_type": pattern.pattern_type,
                    "confidence": pattern.confidence,
                    "timestamp": pattern.timestamp,
                    "description": pattern.description,
                    "data": pattern.data
                })
            
            return {"patterns": result, "timestamp": datetime.utcnow().isoformat()}
            
        except Exception as e:
            logger.error(f"Error getting patterns: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/api/analytics/streams/info")
    async def get_stream_info(current_user = Depends(get_optional_current_user)):
        """Get information about all analytics streams"""
        try:
            producer = await get_stream_producer()
            stream_info = await producer.get_stream_info()
            producer_stats = await producer.get_stats()
            
            return {
                "streams": stream_info,
                "producer_stats": producer_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/api/analytics/system/status")
    async def get_system_status(current_user = Depends(get_optional_current_user)):
        """Get overall system status"""
        try:
            # DragonflyDB stats
            dragonfly_stats = await get_dragonfly_stats()
            
            # Stream producer stats
            try:
                producer = await get_stream_producer()
                producer_stats = await producer.get_stats()
            except Exception:
                producer_stats = {"error": "Producer not available"}
            
            # Worker stats
            try:
                worker_manager = await get_worker_manager()
                worker_stats = await worker_manager.get_system_status()
            except Exception:
                worker_stats = {"error": "Workers not available"}
            
            # WebSocket stats
            websocket_stats = connection_manager.get_stats()
            
            return {
                "dragonfly": dragonfly_stats,
                "stream_producer": producer_stats,
                "feature_workers": worker_stats,
                "websocket_connections": websocket_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/api/analytics/benchmark")
    async def run_benchmark(
        operations: int = Query(1000, description="Number of operations to benchmark"),
        current_user = Depends(get_optional_current_user)
    ):
        """Run DragonflyDB performance benchmark"""
        try:
            results = await benchmark_dragonfly(operations)
            return {
                "benchmark_results": results,
                "operations": operations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running benchmark: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router

async def initialize_analytics_websocket() -> None:
    """Initialize analytics WebSocket service"""
    await connection_manager.start()

async def shutdown_analytics_websocket() -> None:
    """Shutdown analytics WebSocket service"""
    await connection_manager.stop() 