"""
Redis Pub/Sub Cross-Server Coordination

Provides Redis-based message routing, delivery guarantees, session synchronization
across server instances, and distributed collaboration support.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool

from .state import CollaborationState, UserPresence, SessionState
from .operational_transform import Operation


logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of collaboration messages"""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    USER_ACTIVITY = "user_activity"
    OPERATION = "operation"
    CONFLICT = "conflict"
    CONFLICT_RESOLVED = "conflict_resolved"
    SESSION_STATE = "session_state"
    HEARTBEAT = "heartbeat"
    SERVER_STATUS = "server_status"


class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CollaborationMessage:
    """Message for cross-server collaboration coordination"""
    message_id: str
    message_type: MessageType
    session_id: str
    user_id: str
    server_id: str
    payload: Dict[str, Any]
    timestamp: datetime
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    expiry: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "server_id": self.server_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "expiry": self.expiry.isoformat() if self.expiry else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationMessage":
        """Create from dictionary"""
        # Handle enum conversions with explicit typing
        message_type_raw = data["message_type"]
        if isinstance(message_type_raw, MessageType):
            message_type: MessageType = message_type_raw
        else:
            message_type = MessageType(str(message_type_raw))
            
        priority_raw = data.get("priority", "normal")
        if isinstance(priority_raw, MessagePriority):
            priority: MessagePriority = priority_raw
        else:
            priority = MessagePriority(str(priority_raw))
            
        return cls(
            message_id=data["message_id"],
            message_type=message_type,
            session_id=data["session_id"],
            user_id=data["user_id"],
            server_id=data["server_id"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=priority,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            expiry=datetime.fromisoformat(data["expiry"]) if data.get("expiry") else None
        )


class RedisChannelManager:
    """
    Manages Redis channels for collaboration coordination.
    
    Channel Patterns:
    - collaboration:session:{session_id} - Session-specific messages
    - collaboration:user:{user_id} - User-specific messages
    - collaboration:global - Global coordination messages
    - collaboration:server:{server_id} - Server-specific messages
    """
    
    def __init__(self, redis_pool: ConnectionPool, server_id: str) -> None:
        self.redis_pool = redis_pool
        self.server_id = server_id
        self.redis: Optional[Redis[bytes]] = None
        
        # Channel subscriptions
        self.subscriptions: Dict[str, Set[Callable[..., Any]]] = {}
        self.pubsub: Optional[redis.client.PubSub] = None
        
        # Message routing
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.delivery_confirmations: Dict[str, bool] = {}
        
        # Performance tracking
        self.messages_sent = 0
        self.messages_received = 0
        self.delivery_failures = 0
        
        # Background tasks
        self._listener_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize Redis connections and start background tasks"""
        self.redis = Redis(connection_pool=self.redis_pool)
        self.pubsub = self.redis.pubsub()
        
        # Subscribe to server-specific channel
        await self.subscribe_to_channel(f"collaboration:server:{self.server_id}")
        
        # Subscribe to global coordination channel
        await self.subscribe_to_channel("collaboration:global")
        
        # Start background tasks
        self._listener_task = asyncio.create_task(self._message_listener())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        
        # Announce server presence
        await self.announce_server_status("online")
        
        logger.info(f"Redis channel manager initialized for server {self.server_id}")

    async def shutdown(self) -> None:
        """Shutdown Redis connections and cleanup"""
        try:
            # Announce server going offline
            await self.announce_server_status("offline")
            
            # Cancel background tasks
            if self._listener_task:
                self._listener_task.cancel()
            if self._cleanup_task:
                self._cleanup_task.cancel()
            
            # Close pubsub connection
            if self.pubsub:
                await self.pubsub.close()
            
            # Close Redis connection
            if self.redis:
                await self.redis.close()
            
            logger.info(f"Redis channel manager shutdown for server {self.server_id}")
            
        except Exception as e:
            logger.error(f"Error during Redis shutdown: {e}")

    async def subscribe_to_channel(self, channel: str) -> None:
        """Subscribe to a Redis channel"""
        try:
            if self.pubsub:
                await self.pubsub.subscribe(channel)
                if channel not in self.subscriptions:
                    self.subscriptions[channel] = set()
                logger.debug(f"Subscribed to channel: {channel}")
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")

    async def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a Redis channel"""
        try:
            if self.pubsub:
                await self.pubsub.unsubscribe(channel)
                self.subscriptions.pop(channel, None)
                logger.debug(f"Unsubscribed from channel: {channel}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel {channel}: {e}")

    async def publish_message(
        self,
        message: CollaborationMessage,
        target_channel: Optional[str] = None
    ) -> bool:
        """
        Publish a collaboration message to Redis.
        
        Args:
            message: The message to publish
            target_channel: Optional specific channel (auto-determined if None)
            
        Returns:
            bool: True if message was published successfully
        """
        try:
            if not self.redis:
                logger.error("Redis not initialized")
                return False
            
            # Determine target channel
            if not target_channel:
                target_channel = self._determine_target_channel(message)
            
            # Serialize message
            message_data = json.dumps(message.to_dict())
            
            # Store message for delivery confirmation (high/critical priority)
            if message.priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]:
                await self._store_for_confirmation(message)
            
            # Publish to Redis
            subscribers = await self.redis.publish(target_channel, message_data)
            
            self.messages_sent += 1
            
            logger.debug(
                f"Published {message.message_type.value} message to {target_channel} "
                f"({subscribers} subscribers)"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message {message.message_id}: {e}")
            self.delivery_failures += 1
            
            # Retry for critical messages
            if message.priority == MessagePriority.CRITICAL and message.retry_count < message.max_retries:
                message.retry_count += 1
                await asyncio.sleep(2 ** message.retry_count)  # Exponential backoff
                return await self.publish_message(message, target_channel)
            
            return False

    async def _message_listener(self) -> None:
        """Background task to listen for Redis messages"""
        try:
            if not self.pubsub:
                return
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_received_message(message)
                    
        except asyncio.CancelledError:
            logger.info("Message listener task cancelled")
        except Exception as e:
            logger.error(f"Error in message listener: {e}")

    async def _handle_received_message(self, redis_message: Dict[str, Any]) -> None:
        """Handle a message received from Redis"""
        try:
            # Parse message data
            message_data = json.loads(redis_message["data"])
            collaboration_message = CollaborationMessage.from_dict(message_data)
            
            # Skip messages from this server (avoid self-processing)
            if collaboration_message.server_id == self.server_id:
                return
            
            self.messages_received += 1
            
            # Send delivery confirmation for high/critical priority messages
            if collaboration_message.priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]:
                await self._send_delivery_confirmation(collaboration_message)
            
            # Route message to registered handlers
            await self._route_message_to_handlers(collaboration_message)
            
            logger.debug(
                f"Processed {collaboration_message.message_type.value} message "
                f"from server {collaboration_message.server_id}"
            )
            
        except Exception as e:
            logger.error(f"Error handling received message: {e}")

    async def _route_message_to_handlers(self, message: CollaborationMessage) -> None:
        """Route message to registered handlers"""
        handlers = self.message_handlers.get(message.message_type, [])
        
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    def register_message_handler(
        self,
        message_type: MessageType,
        handler: Callable[[CollaborationMessage], None]
    ) -> None:
        """Register a handler for specific message type"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type.value} messages")

    def _determine_target_channel(self, message: CollaborationMessage) -> str:
        """Determine the appropriate Redis channel for a message"""
        if message.message_type in [MessageType.SERVER_STATUS]:
            return "collaboration:global"
        elif message.session_id:
            return f"collaboration:session:{message.session_id}"
        elif message.user_id:
            return f"collaboration:user:{message.user_id}"
        else:
            return "collaboration:global"

    async def _store_for_confirmation(self, message: CollaborationMessage) -> None:
        """Store message for delivery confirmation"""
        try:
            if self.redis:
                confirmation_key = f"confirmation:{message.message_id}"
                await self.redis.setex(
                    confirmation_key,
                    300,  # 5 minutes TTL
                    json.dumps(message.to_dict())
                )
        except Exception as e:
            logger.error(f"Failed to store message for confirmation: {e}")

    async def _send_delivery_confirmation(self, message: CollaborationMessage) -> None:
        """Send delivery confirmation for received message"""
        try:
            confirmation_message = CollaborationMessage(
                message_id=str(uuid4()),
                message_type=MessageType.HEARTBEAT,  # Use heartbeat type for confirmations
                session_id=message.session_id,
                user_id=self.server_id,  # Use server_id as user_id for confirmations
                server_id=self.server_id,
                payload={
                    "type": "delivery_confirmation",
                    "original_message_id": message.message_id,
                    "confirmed_by": self.server_id
                },
                timestamp=datetime.now(timezone.utc),
                priority=MessagePriority.NORMAL
            )
            
            target_channel = f"collaboration:server:{message.server_id}"
            await self.publish_message(confirmation_message, target_channel)
            
        except Exception as e:
            logger.error(f"Failed to send delivery confirmation: {e}")

    async def _cleanup_expired_messages(self) -> None:
        """Background task to cleanup expired messages and confirmations"""
        while True:
            try:
                if self.redis:
                    # Clean up expired confirmation keys
                    pattern = "confirmation:*"
                    expired_keys = []
                    
                    async for key in self.redis.scan_iter(match=pattern):
                        ttl = await self.redis.ttl(key)
                        if ttl <= 0:
                            expired_keys.append(key)
                    
                    if expired_keys:
                        await self.redis.delete(*expired_keys)
                        logger.debug(f"Cleaned up {len(expired_keys)} expired confirmation keys")
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def announce_server_status(self, status: str) -> None:
        """Announce server status to other servers"""
        try:
            status_message = CollaborationMessage(
                message_id=str(uuid4()),
                message_type=MessageType.SERVER_STATUS,
                session_id="",
                user_id="",
                server_id=self.server_id,
                payload={
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "capabilities": ["collaboration", "operational_transform", "conflict_resolution"]
                },
                timestamp=datetime.now(timezone.utc),
                priority=MessagePriority.HIGH
            )
            
            await self.publish_message(status_message, "collaboration:global")
            
        except Exception as e:
            logger.error(f"Failed to announce server status: {e}")

    async def broadcast_user_event(
        self,
        session_id: str,
        user_id: str,
        event_type: MessageType,
        event_data: Dict[str, Any]
    ) -> None:
        """Broadcast user event to all servers in session"""
        try:
            user_message = CollaborationMessage(
                message_id=str(uuid4()),
                message_type=event_type,
                session_id=session_id,
                user_id=user_id,
                server_id=self.server_id,
                payload=event_data,
                timestamp=datetime.now(timezone.utc),
                priority=MessagePriority.NORMAL
            )
            
            await self.publish_message(user_message)
            
        except Exception as e:
            logger.error(f"Failed to broadcast user event: {e}")

    async def broadcast_operation(
        self,
        session_id: str,
        user_id: str,
        operation: Operation
    ) -> None:
        """Broadcast operational transform operation to all servers"""
        try:
            operation_message = CollaborationMessage(
                message_id=str(uuid4()),
                message_type=MessageType.OPERATION,
                session_id=session_id,
                user_id=user_id,
                server_id=self.server_id,
                payload={
                    "operation": operation.to_dict(),
                    "sequence_number": operation.sequence_number
                },
                timestamp=datetime.now(timezone.utc),
                priority=MessagePriority.HIGH  # Operations are high priority
            )
            
            await self.publish_message(operation_message)
            
        except Exception as e:
            logger.error(f"Failed to broadcast operation: {e}")

    async def sync_session_state(
        self,
        session_id: str,
        state: CollaborationState
    ) -> None:
        """Synchronize session state across servers"""
        try:
            state_message = CollaborationMessage(
                message_id=str(uuid4()),
                message_type=MessageType.SESSION_STATE,
                session_id=session_id,
                user_id="",
                server_id=self.server_id,
                payload={
                    "session_state": state.to_dict(),
                    "sync_timestamp": datetime.now(timezone.utc).isoformat()
                },
                timestamp=datetime.now(timezone.utc),
                priority=MessagePriority.HIGH
            )
            
            await self.publish_message(state_message)
            
        except Exception as e:
            logger.error(f"Failed to sync session state: {e}")

    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get Redis coordination metrics"""
        return {
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "delivery_failures": self.delivery_failures,
            "active_subscriptions": len(self.subscriptions),
            "registered_handlers": sum(len(handlers) for handlers in self.message_handlers.values()),
            "server_id": self.server_id
        } 