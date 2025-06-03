"""
Real-time analytics system for GraphMemory-IDE.
Provides WebSocket and Server-Sent Events for live analytics updates.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Any, Optional, Callable, AsyncGenerator
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import weakref

from .models import RealtimeUpdate, AnalyticsType

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time analytics"""
    
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # analytics_type -> set of connection_ids
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None) -> None:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "subscriptions": set()
        }
        logger.info(f"WebSocket connection established: {connection_id}")
    
    def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from all subscriptions
        for analytics_type, subscribers in self.subscriptions.items():
            subscribers.discard(connection_id)
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def subscribe(self, connection_id: str, analytics_type: str) -> None:
        """Subscribe a connection to analytics updates"""
        if analytics_type not in self.subscriptions:
            self.subscriptions[analytics_type] = set()
        
        self.subscriptions[analytics_type].add(connection_id)
        
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscriptions"].add(analytics_type)
        
        logger.info(f"Connection {connection_id} subscribed to {analytics_type}")
    
    async def unsubscribe(self, connection_id: str, analytics_type: str) -> None:
        """Unsubscribe a connection from analytics updates"""
        if analytics_type in self.subscriptions:
            self.subscriptions[analytics_type].discard(connection_id)
        
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscriptions"].discard(analytics_type)
        
        logger.info(f"Connection {connection_id} unsubscribed from {analytics_type}")
    
    async def broadcast_to_subscribers(self, analytics_type: str, update: RealtimeUpdate) -> None:
        """Broadcast an update to all subscribers of an analytics type"""
        if analytics_type not in self.subscriptions:
            return
        
        subscribers = self.subscriptions[analytics_type].copy()
        message = {
            "type": "analytics_update",
            "analytics_type": analytics_type,
            "update": update.dict()
        }
        
        disconnected = []
        for connection_id in subscribers:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send to {connection_id}: {e}")
                    disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.warning(f"Failed to send to {connection_id}: {e}")
                self.disconnect(connection_id)
        return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        return {
            "total_connections": len(self.active_connections),
            "subscriptions_by_type": {
                analytics_type: len(subscribers)
                for analytics_type, subscribers in self.subscriptions.items()
            },
            "connections": [
                {
                    "connection_id": conn_id,
                    "user_id": metadata.get("user_id"),
                    "connected_at": metadata.get("connected_at").isoformat() if metadata.get("connected_at") else None,
                    "subscriptions": list(metadata.get("subscriptions", set()))
                }
                for conn_id, metadata in self.connection_metadata.items()
            ]
        }


class RealtimeAnalytics:
    """
    Real-time analytics system with WebSocket and SSE support.
    Manages live updates and streaming analytics data.
    """
    
    def __init__(self) -> None:
        self.connection_manager = ConnectionManager()
        self.update_handlers: Dict[str, List[Callable]] = {}
        self.analytics_streams: Dict[str, asyncio.Queue] = {}
        self.background_tasks: Set[asyncio.Task] = set()
    
    def register_update_handler(self, analytics_type: str, handler: Callable) -> None:
        """Register a handler for analytics updates"""
        if analytics_type not in self.update_handlers:
            self.update_handlers[analytics_type] = []
        self.update_handlers[analytics_type].append(handler)
    
    async def start_analytics_stream(self, analytics_type: str, interval: float = 1.0) -> None:
        """Start a background stream for analytics updates"""
        if analytics_type in self.analytics_streams:
            return  # Already running
        
        queue = asyncio.Queue()
        self.analytics_streams[analytics_type] = queue
        
        # Start background task to process the stream
        task = asyncio.create_task(
            self._process_analytics_stream(analytics_type, queue, interval)
        )
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def stop_analytics_stream(self, analytics_type: str) -> None:
        """Stop a background analytics stream"""
        if analytics_type in self.analytics_streams:
            queue = self.analytics_streams[analytics_type]
            await queue.put(None)  # Signal to stop
            del self.analytics_streams[analytics_type]
    
    async def _process_analytics_stream(self, analytics_type: str, queue: asyncio.Queue, interval: float) -> None:
        """Process analytics stream updates"""
        logger.info(f"Started analytics stream for {analytics_type}")
        
        while True:
            try:
                # Wait for update or timeout
                update = await asyncio.wait_for(queue.get(), timeout=interval)
                
                if update is None:  # Stop signal
                    break
                
                # Broadcast to subscribers
                await self.connection_manager.broadcast_to_subscribers(analytics_type, update)
                
                # Call registered handlers
                if analytics_type in self.update_handlers:
                    for handler in self.update_handlers[analytics_type]:
                        try:
                            await handler(update)
                        except Exception as e:
                            logger.error(f"Update handler error: {e}")
                
            except asyncio.TimeoutError:
                # Generate periodic update if no data received
                await self._generate_periodic_update(analytics_type)
            except Exception as e:
                logger.error(f"Analytics stream error for {analytics_type}: {e}")
                break
        
        logger.info(f"Stopped analytics stream for {analytics_type}")
    
    async def _generate_periodic_update(self, analytics_type: str) -> None:
        """Generate a periodic heartbeat or status update"""
        update = RealtimeUpdate(
            update_type="heartbeat",
            data={
                "analytics_type": analytics_type,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active"
            }
        )
        await self.connection_manager.broadcast_to_subscribers(analytics_type, update)
    
    async def publish_update(self, analytics_type: str, update: RealtimeUpdate) -> None:
        """Publish an analytics update to the stream"""
        if analytics_type in self.analytics_streams:
            await self.analytics_streams[analytics_type].put(update)
        else:
            # Direct broadcast if no stream is running
            await self.connection_manager.broadcast_to_subscribers(analytics_type, update)
    
    async def handle_websocket_connection(
        self, 
        websocket: WebSocket, 
        connection_id: str,
        user_id: Optional[str] = None
    ) -> None:
        """Handle a WebSocket connection for real-time analytics"""
        await self.connection_manager.connect(websocket, connection_id, user_id)
        
        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await self._handle_client_message(connection_id, message)
                
        except WebSocketDisconnect:
            self.connection_manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
            self.connection_manager.disconnect(connection_id)
    
    async def _handle_client_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Handle messages from WebSocket clients"""
        message_type = message.get("type")
        
        if message_type == "subscribe":
            analytics_type = message.get("analytics_type")
            if analytics_type:
                await self.connection_manager.subscribe(connection_id, analytics_type)
                
                # Start stream if not already running
                await self.start_analytics_stream(analytics_type)
                
                # Send confirmation
                await self.connection_manager.send_to_connection(connection_id, {
                    "type": "subscription_confirmed",
                    "analytics_type": analytics_type
                })
        
        elif message_type == "unsubscribe":
            analytics_type = message.get("analytics_type")
            if analytics_type:
                await self.connection_manager.unsubscribe(connection_id, analytics_type)
                
                # Send confirmation
                await self.connection_manager.send_to_connection(connection_id, {
                    "type": "unsubscription_confirmed",
                    "analytics_type": analytics_type
                })
        
        elif message_type == "ping":
            # Respond to ping with pong
            await self.connection_manager.send_to_connection(connection_id, {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def generate_sse_stream(self, analytics_type: str) -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events stream for analytics"""
        # This would be used with FastAPI's StreamingResponse
        queue = asyncio.Queue()
        
        # Subscribe to updates
        def update_handler(update: RealtimeUpdate) -> None:
            asyncio.create_task(queue.put(update))
        
        self.register_update_handler(analytics_type, update_handler)
        
        try:
            while True:
                update = await queue.get()
                yield f"data: {json.dumps(update.dict())}\n\n"
        except asyncio.CancelledError:
            pass
    
    def get_realtime_stats(self) -> Dict[str, Any]:
        """Get real-time analytics statistics"""
        return {
            "connection_stats": self.connection_manager.get_connection_stats(),
            "active_streams": list(self.analytics_streams.keys()),
            "background_tasks": len(self.background_tasks),
            "update_handlers": {
                analytics_type: len(handlers)
                for analytics_type, handlers in self.update_handlers.items()
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown real-time analytics system"""
        # Stop all streams
        for analytics_type in list(self.analytics_streams.keys()):
            await self.stop_analytics_stream(analytics_type)
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("Real-time analytics system shutdown complete") 