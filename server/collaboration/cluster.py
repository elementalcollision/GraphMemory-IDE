"""
Multi-Server Cluster Coordination

Provides multi-server session coordination, load balancing, failover handling,
cross-server user presence synchronization, and distributed session recovery.
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from .state import CollaborationState, UserPresence, SessionState, UserRole
from .pubsub import RedisChannelManager, CollaborationMessage, MessageType, MessagePriority


logger = logging.getLogger(__name__)


class ServerStatus(str, Enum):
    """Server status states"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


@dataclass
class ServerNode:
    """Represents a server node in the cluster"""
    server_id: str
    host: str
    port: int
    status: ServerStatus
    last_heartbeat: datetime
    capabilities: List[str]
    active_sessions: int = 0
    load_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "server_id": self.server_id,
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "capabilities": self.capabilities,
            "active_sessions": self.active_sessions,
            "load_score": self.load_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerNode":
        """Create from dictionary"""
        status_value = data["status"]
        
        # Ensure we have a proper ServerStatus enum
        status: ServerStatus
        try:
            if isinstance(status_value, ServerStatus):
                status = status_value
            else:
                # Try to convert string to enum
                status = ServerStatus(str(status_value))
        except (ValueError, TypeError):
            # Default to offline for any conversion failure
            status = ServerStatus.OFFLINE
            
        return cls(
            server_id=data["server_id"],
            host=data["host"],
            port=data["port"],
            status=status,
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]),
            capabilities=data["capabilities"],
            active_sessions=data.get("active_sessions", 0),
            load_score=data.get("load_score", 0.0)
        )


@dataclass
class SessionDistribution:
    """Tracks session distribution across cluster"""
    session_id: str
    primary_server: str
    replica_servers: List[str]
    user_count: int
    created_at: datetime
    last_activity: datetime


class ClusterCoordinator:
    """
    Multi-server cluster coordinator for collaboration sessions.
    
    Features:
    - Server discovery and health monitoring
    - Session load balancing and distribution
    - Failover and recovery mechanisms
    - Cross-server user presence synchronization
    - Distributed session state management
    """
    
    def __init__(
        self,
        server_id: str,
        redis_manager: RedisChannelManager,
        max_sessions_per_server: int = 1000
    ) -> None:
        self.server_id = server_id
        self.redis_manager = redis_manager
        self.max_sessions_per_server = max_sessions_per_server
        
        # Cluster state
        self.cluster_nodes: Dict[str, ServerNode] = {}
        self.session_distribution: Dict[str, SessionDistribution] = {}
        self.local_sessions: Set[str] = set()
        
        # Load balancing
        self.hash_ring: List[str] = []  # Consistent hashing ring
        self.replication_factor = 2
        
        # Health monitoring
        self.heartbeat_interval = 30  # seconds
        self.node_timeout = 90  # seconds
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize cluster coordinator"""
        # Register message handlers - create wrapper functions for async handlers
        def server_status_handler(message: CollaborationMessage) -> None:
            asyncio.create_task(self._handle_server_status(message))
        
        def session_sync_handler(message: CollaborationMessage) -> None:
            asyncio.create_task(self._handle_session_sync(message))
            
        def user_event_handler(message: CollaborationMessage) -> None:
            asyncio.create_task(self._handle_user_event(message))
        
        self.redis_manager.register_message_handler(
            MessageType.SERVER_STATUS,
            server_status_handler
        )
        self.redis_manager.register_message_handler(
            MessageType.SESSION_STATE,
            session_sync_handler
        )
        self.redis_manager.register_message_handler(
            MessageType.USER_JOIN,
            user_event_handler
        )
        self.redis_manager.register_message_handler(
            MessageType.USER_LEAVE,
            user_event_handler
        )
        
        # Add this server to cluster
        await self._register_server()
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        self._sync_task = asyncio.create_task(self._sync_loop())
        
        logger.info(f"Cluster coordinator initialized for server {self.server_id}")

    async def shutdown(self) -> None:
        """Shutdown cluster coordinator"""
        try:
            # Cancel background tasks
            for task in [self._heartbeat_task, self._health_monitor_task, self._sync_task]:
                if task:
                    task.cancel()
            
            # Announce server going offline
            await self._announce_server_offline()
            
            logger.info(f"Cluster coordinator shutdown for server {self.server_id}")
            
        except Exception as e:
            logger.error(f"Error during cluster coordinator shutdown: {e}")

    async def assign_session(self, session_id: str, user_count: int = 1) -> str:
        """
        Assign a session to the optimal server in the cluster.
        
        Args:
            session_id: Session identifier
            user_count: Expected number of users
            
        Returns:
            str: Server ID that should handle the session
        """
        # Check if session already exists
        if session_id in self.session_distribution:
            distribution = self.session_distribution[session_id]
            # Check if primary server is still available
            if distribution.primary_server in self.cluster_nodes:
                node = self.cluster_nodes[distribution.primary_server]
                if node.status == ServerStatus.ONLINE:
                    return distribution.primary_server
            
            # Primary server unavailable, failover to replica
            for replica_server in distribution.replica_servers:
                if replica_server in self.cluster_nodes:
                    node = self.cluster_nodes[replica_server]
                    if node.status == ServerStatus.ONLINE:
                        # Promote replica to primary
                        await self._promote_replica_to_primary(session_id, replica_server)
                        return replica_server
        
        # New session assignment
        primary_server = self._select_optimal_server(user_count)
        replica_servers = self._select_replica_servers(primary_server, user_count)
        
        # Create session distribution
        distribution = SessionDistribution(
            session_id=session_id,
            primary_server=primary_server,
            replica_servers=replica_servers,
            user_count=user_count,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc)
        )
        
        self.session_distribution[session_id] = distribution
        
        # Track local sessions
        if primary_server == self.server_id:
            self.local_sessions.add(session_id)
        
        logger.info(f"Assigned session {session_id} to server {primary_server} with replicas {replica_servers}")
        return primary_server

    def _select_optimal_server(self, expected_users: int) -> str:
        """Select the optimal server for a new session"""
        available_servers = [
            node for node in self.cluster_nodes.values()
            if node.status == ServerStatus.ONLINE and 
               node.active_sessions < self.max_sessions_per_server
        ]
        
        if not available_servers:
            # Fallback to this server if no others available
            return self.server_id
        
        # Calculate server scores (lower is better)
        scored_servers = []
        for server in available_servers:
            # Score based on load, session count, and expected capacity
            load_score = server.load_score
            session_ratio = server.active_sessions / self.max_sessions_per_server
            capacity_score = session_ratio + (expected_users / 100.0)  # Factor in expected users
            
            total_score = load_score + capacity_score
            scored_servers.append((total_score, server.server_id))
        
        # Sort by score and return best server
        scored_servers.sort()
        return scored_servers[0][1]

    def _select_replica_servers(self, primary_server: str, expected_users: int) -> List[str]:
        """Select replica servers for session replication"""
        available_servers = [
            node.server_id for node in self.cluster_nodes.values()
            if node.status == ServerStatus.ONLINE and 
               node.server_id != primary_server and
               node.active_sessions < self.max_sessions_per_server
        ]
        
        # Select up to replication_factor replicas
        replica_count = min(self.replication_factor, len(available_servers))
        
        if replica_count == 0:
            return []
        
        # Use consistent hashing to select replicas
        session_hash = int(hashlib.md5(primary_server.encode()).hexdigest(), 16)
        
        # Sort servers by hash distance
        server_distances = []
        for server_id in available_servers:
            server_hash = int(hashlib.md5(server_id.encode()).hexdigest(), 16)
            distance = abs(session_hash - server_hash)
            server_distances.append((distance, server_id))
        
        server_distances.sort()
        return [server_id for _, server_id in server_distances[:replica_count]]

    async def _promote_replica_to_primary(self, session_id: str, new_primary: str) -> None:
        """Promote a replica server to primary for a session"""
        if session_id not in self.session_distribution:
            return
        
        distribution = self.session_distribution[session_id]
        old_primary = distribution.primary_server
        
        # Update distribution
        distribution.primary_server = new_primary
        if new_primary in distribution.replica_servers:
            distribution.replica_servers.remove(new_primary)
        
        # Add old primary as replica if it's still available
        if old_primary in self.cluster_nodes:
            node = self.cluster_nodes[old_primary]
            if node.status in [ServerStatus.DEGRADED]:  # Can still serve as replica
                distribution.replica_servers.append(old_primary)
        
        # Track local sessions
        if new_primary == self.server_id:
            self.local_sessions.add(session_id)
        elif session_id in self.local_sessions:
            self.local_sessions.remove(session_id)
        
        logger.info(f"Promoted server {new_primary} to primary for session {session_id}")

    async def sync_user_presence(
        self,
        session_id: str,
        user_presence: UserPresence
    ) -> None:
        """Synchronize user presence across cluster"""
        try:
            # Broadcast user presence update
            await self.redis_manager.broadcast_user_event(
                session_id=session_id,
                user_id=user_presence.user_id,
                event_type=MessageType.USER_ACTIVITY,
                event_data={
                    "presence": user_presence.to_dict(),
                    "sync_type": "presence_update"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to sync user presence: {e}")

    async def handle_session_migration(
        self,
        session_id: str,
        target_server: str
    ) -> bool:
        """
        Migrate a session to a different server.
        
        Args:
            session_id: Session to migrate
            target_server: Target server ID
            
        Returns:
            bool: True if migration successful
        """
        try:
            if session_id not in self.session_distribution:
                logger.error(f"Session {session_id} not found for migration")
                return False
            
            distribution = self.session_distribution[session_id]
            old_primary = distribution.primary_server
            
            # Check if target server is available
            if target_server not in self.cluster_nodes:
                logger.error(f"Target server {target_server} not available")
                return False
            
            target_node = self.cluster_nodes[target_server]
            if target_node.status != ServerStatus.ONLINE:
                logger.error(f"Target server {target_server} not online")
                return False
            
            # Update session distribution
            distribution.primary_server = target_server
            if target_server in distribution.replica_servers:
                distribution.replica_servers.remove(target_server)
            
            # Add old primary as replica
            if old_primary != self.server_id:
                distribution.replica_servers.append(old_primary)
            
            # Update local session tracking
            if target_server == self.server_id:
                self.local_sessions.add(session_id)
            elif session_id in self.local_sessions:
                self.local_sessions.remove(session_id)
            
            logger.info(f"Migrated session {session_id} from {old_primary} to {target_server}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate session {session_id}: {e}")
            return False

    async def _register_server(self) -> None:
        """Register this server with the cluster"""
        server_node = ServerNode(
            server_id=self.server_id,
            host="localhost",  # This would be configurable
            port=8000,         # This would be configurable
            status=ServerStatus.ONLINE,
            last_heartbeat=datetime.now(timezone.utc),
            capabilities=["collaboration", "operational_transform", "conflict_resolution"],
            active_sessions=len(self.local_sessions),
            load_score=0.0
        )
        
        self.cluster_nodes[self.server_id] = server_node
        
        # Announce to cluster
        await self.redis_manager.announce_server_status("online")

    async def _announce_server_offline(self) -> None:
        """Announce this server going offline"""
        if self.server_id in self.cluster_nodes:
            self.cluster_nodes[self.server_id].status = ServerStatus.OFFLINE
        
        await self.redis_manager.announce_server_status("offline")

    async def _heartbeat_loop(self) -> None:
        """Background task for server heartbeat"""
        while True:
            try:
                # Update local server status
                if self.server_id in self.cluster_nodes:
                    node = self.cluster_nodes[self.server_id]
                    node.last_heartbeat = datetime.now(timezone.utc)
                    node.active_sessions = len(self.local_sessions)
                    # Calculate load score (simplified)
                    node.load_score = node.active_sessions / self.max_sessions_per_server
                
                # Send heartbeat
                await self.redis_manager.announce_server_status("online")
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(10)

    async def _health_monitor_loop(self) -> None:
        """Background task for monitoring cluster health"""
        while True:
            try:
                now = datetime.now(timezone.utc)
                timeout_threshold = now - timedelta(seconds=self.node_timeout)
                
                # Check for failed nodes
                failed_nodes = []
                for server_id, node in self.cluster_nodes.items():
                    if server_id != self.server_id and node.last_heartbeat < timeout_threshold:
                        if node.status != ServerStatus.OFFLINE:
                            failed_nodes.append(server_id)
                            node.status = ServerStatus.OFFLINE
                
                # Handle failovers for failed nodes
                for failed_server in failed_nodes:
                    await self._handle_server_failure(failed_server)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(10)

    async def _sync_loop(self) -> None:
        """Background task for periodic cluster synchronization"""
        while True:
            try:
                # Sync session distributions
                await self._sync_session_distributions()
                
                # Clean up old sessions
                await self._cleanup_old_sessions()
                
                await asyncio.sleep(300)  # Sync every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(60)

    async def _handle_server_failure(self, failed_server: str) -> None:
        """Handle failure of a server node"""
        logger.warning(f"Detected failure of server {failed_server}")
        
        # Find sessions that need failover
        sessions_to_failover = []
        for session_id, distribution in self.session_distribution.items():
            if distribution.primary_server == failed_server:
                sessions_to_failover.append(session_id)
        
        # Perform failovers
        for session_id in sessions_to_failover:
            distribution = self.session_distribution[session_id]
            
            # Find available replica
            new_primary = None
            for replica_server in distribution.replica_servers:
                if replica_server in self.cluster_nodes:
                    node = self.cluster_nodes[replica_server]
                    if node.status == ServerStatus.ONLINE:
                        new_primary = replica_server
                        break
            
            if new_primary:
                await self._promote_replica_to_primary(session_id, new_primary)
            else:
                # No replicas available, reassign to a healthy server
                healthy_server = self._select_optimal_server(distribution.user_count)
                distribution.primary_server = healthy_server
                distribution.replica_servers = self._select_replica_servers(healthy_server, distribution.user_count)
                
                if healthy_server == self.server_id:
                    self.local_sessions.add(session_id)

    async def _handle_server_status(self, message: CollaborationMessage) -> None:
        """Handle server status messages"""
        try:
            payload = message.payload
            server_id = message.server_id
            status_value = payload.get("status", "online")
            
            # Safely convert to ServerStatus enum
            status: ServerStatus
            try:
                if isinstance(status_value, ServerStatus):
                    status = status_value
                else:
                    # Try to convert to enum
                    status = ServerStatus(str(status_value))
            except (ValueError, TypeError):
                logger.warning(f"Unknown server status '{status_value}', defaulting to OFFLINE")
                status = ServerStatus.OFFLINE
            
            if server_id not in self.cluster_nodes:
                # New server discovered
                self.cluster_nodes[server_id] = ServerNode(
                    server_id=server_id,
                    host="unknown",
                    port=0,
                    status=status,
                    last_heartbeat=datetime.now(timezone.utc),
                    capabilities=payload.get("capabilities", [])
                )
                logger.info(f"Discovered new server: {server_id}")
            else:
                # Update existing server
                node = self.cluster_nodes[server_id]
                node.status = status
                node.last_heartbeat = datetime.now(timezone.utc)
                node.capabilities = payload.get("capabilities", node.capabilities)
            
        except Exception as e:
            logger.error(f"Error handling server status message: {e}")

    async def _handle_session_sync(self, message: CollaborationMessage) -> None:
        """Handle session state synchronization messages"""
        try:
            payload = message.payload
            session_state_data = payload.get("session_state")
            
            if session_state_data:
                # This would update local session state if this server is a replica
                session_id = message.session_id
                if session_id in self.session_distribution:
                    distribution = self.session_distribution[session_id]
                    if self.server_id in distribution.replica_servers:
                        # Update replica state (implementation would depend on session storage)
                        logger.debug(f"Synced replica state for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling session sync message: {e}")

    async def _handle_user_event(self, message: CollaborationMessage) -> None:
        """Handle user join/leave events"""
        try:
            session_id = message.session_id
            user_id = message.user_id
            event_type = message.message_type
            
            # Update session activity
            if session_id in self.session_distribution:
                self.session_distribution[session_id].last_activity = datetime.now(timezone.utc)
            
            logger.debug(f"Processed user event {event_type.value} for user {user_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling user event: {e}")

    async def _sync_session_distributions(self) -> None:
        """Synchronize session distributions across cluster"""
        # This would implement more sophisticated session distribution sync
        # For now, we rely on Redis pub/sub for coordination
        pass

    async def _cleanup_old_sessions(self) -> None:
        """Clean up old inactive sessions"""
        now = datetime.now(timezone.utc)
        cleanup_threshold = now - timedelta(hours=24)  # 24 hours
        
        sessions_to_remove = []
        for session_id, distribution in self.session_distribution.items():
            if distribution.last_activity < cleanup_threshold:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.session_distribution[session_id]
            self.local_sessions.discard(session_id)
        
        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")

    def get_cluster_metrics(self) -> Dict[str, Any]:
        """Get cluster coordination metrics"""
        total_sessions = len(self.session_distribution)
        local_sessions_count = len(self.local_sessions)
        online_servers = len([n for n in self.cluster_nodes.values() if n.status == ServerStatus.ONLINE])
        
        return {
            "server_id": self.server_id,
            "cluster_size": len(self.cluster_nodes),
            "online_servers": online_servers,
            "total_sessions": total_sessions,
            "local_sessions": local_sessions_count,
            "load_distribution": {
                server_id: node.active_sessions 
                for server_id, node in self.cluster_nodes.items()
            },
            "replication_factor": self.replication_factor
        } 