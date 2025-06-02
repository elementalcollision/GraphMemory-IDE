"""
Relationship OT Engine - Phase 2.1 Memory Collaboration Engine

This module implements operational transformation for collaborative memory relationship editing.
It handles concurrent relationship operations (create, delete, modify) between multiple users
with automatic conflict resolution and delta synchronization.

Features:
- Memory-to-memory relationship collaboration using operational transformation
- Concurrent relationship creation, deletion, and modification
- Conflict resolution for graph edge operations
- Integration with existing Memory CRDT system
- Redis-based synchronization and state management
- Permission-based relationship editing controls

Author: GraphMemory-IDE Team
Created: January 29, 2025
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib

import redis.asyncio as redis
from redis.asyncio import Redis

from .state import UserRole
from .auth import CollaborationPermission
from .pubsub import CollaborationMessage, MessageType, MessagePriority
from .memory_crdt import MemoryCRDTManager, verify_collaboration_permission

# Configure logging
logger = logging.getLogger(__name__)


class RelationshipOperationType(Enum):
    """Types of relationship operations for operational transformation"""
    CREATE = "create"
    DELETE = "delete"
    MODIFY_STRENGTH = "modify_strength"
    MODIFY_TYPE = "modify_type"
    MODIFY_METADATA = "modify_metadata"


class RelationshipConflictResolution(Enum):
    """Conflict resolution strategies for relationship operations"""
    LAST_WRITER_WINS = "last_writer_wins"
    STRENGTH_PRIORITY = "strength_priority"
    USER_PRIORITY = "user_priority"
    MERGE_METADATA = "merge_metadata"


@dataclass
class RelationshipOperation:
    """
    Represents a single relationship operation for operational transformation
    
    This class implements the OT operation interface with transform, compose,
    and inverse capabilities for relationship editing.
    """
    operation_id: str
    operation_type: RelationshipOperationType
    source_memory_id: str
    target_memory_id: str
    user_id: str
    timestamp: datetime
    version: int
    
    # Operation-specific data
    relationship_type: Optional[str] = None
    strength: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Original values for inverse operations
    original_strength: Optional[float] = None
    original_type: Optional[str] = None
    original_metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate operation data"""
        if self.operation_type == RelationshipOperationType.CREATE:
            if not self.relationship_type or self.strength is None:
                raise ValueError("CREATE operation requires relationship_type and strength")
        elif self.operation_type == RelationshipOperationType.MODIFY_STRENGTH:
            if self.strength is None or self.original_strength is None:
                raise ValueError("MODIFY_STRENGTH operation requires strength and original_strength")
        elif self.operation_type == RelationshipOperationType.MODIFY_TYPE:
            if not self.relationship_type or not self.original_type:
                raise ValueError("MODIFY_TYPE operation requires relationship_type and original_type")

    def get_relationship_id(self) -> str:
        """Generate consistent relationship ID from source and target"""
        # Create deterministic ID regardless of operation order
        memory_ids = sorted([self.source_memory_id, self.target_memory_id])
        return f"rel_{memory_ids[0]}_{memory_ids[1]}"

    def is_concurrent_with(self, other: 'RelationshipOperation') -> bool:
        """Check if this operation is concurrent with another"""
        # Operations are concurrent if they affect the same relationship
        # and neither causally depends on the other
        if self.get_relationship_id() != other.get_relationship_id():
            return False
        
        # Simple timestamp-based concurrency check
        # In production, this would use vector clocks or causal ordering
        time_diff = abs((self.timestamp - other.timestamp).total_seconds())
        return time_diff < 1.0  # Operations within 1 second are considered concurrent

    def transform_against(self, other: 'RelationshipOperation') -> 'RelationshipOperation':
        """
        Transform this operation against another concurrent operation
        
        This implements the operational transformation algorithm for relationship operations.
        """
        if not self.is_concurrent_with(other):
            return self  # No transformation needed for non-concurrent operations
        
        # Handle different operation type combinations
        if self.operation_type == RelationshipOperationType.CREATE:
            return self._transform_create_against(other)
        elif self.operation_type == RelationshipOperationType.DELETE:
            return self._transform_delete_against(other)
        elif self.operation_type == RelationshipOperationType.MODIFY_STRENGTH:
            return self._transform_modify_strength_against(other)
        elif self.operation_type == RelationshipOperationType.MODIFY_TYPE:
            return self._transform_modify_type_against(other)
        elif self.operation_type == RelationshipOperationType.MODIFY_METADATA:
            return self._transform_modify_metadata_against(other)
        
        return self

    def _transform_create_against(self, other: 'RelationshipOperation') -> 'RelationshipOperation':
        """Transform CREATE operation against another operation"""
        if other.operation_type == RelationshipOperationType.CREATE:
            # Both trying to create same relationship - use user priority
            if self.user_id < other.user_id:  # Lexicographic ordering for determinism
                return self  # This operation wins
            else:
                # Other operation wins - convert to no-op or modify existing
                return self._create_no_op()
        elif other.operation_type == RelationshipOperationType.DELETE:
            # Create after delete - create wins
            return self
        else:
            # Create after modify - create wins
            return self

    def _transform_delete_against(self, other: 'RelationshipOperation') -> 'RelationshipOperation':
        """Transform DELETE operation against another operation"""
        if other.operation_type == RelationshipOperationType.DELETE:
            # Both trying to delete - first one wins, second becomes no-op
            if self.timestamp <= other.timestamp:
                return self
            else:
                return self._create_no_op()
        elif other.operation_type == RelationshipOperationType.CREATE:
            # Delete after create - delete wins
            return self
        else:
            # Delete after modify - delete wins
            return self

    def _transform_modify_strength_against(self, other: 'RelationshipOperation') -> 'RelationshipOperation':
        """Transform MODIFY_STRENGTH operation against another operation"""
        if other.operation_type == RelationshipOperationType.DELETE:
            # Modify after delete - becomes no-op
            return self._create_no_op()
        elif other.operation_type == RelationshipOperationType.CREATE:
            # Modify after create - adjust to work with created relationship
            return self
        elif other.operation_type == RelationshipOperationType.MODIFY_STRENGTH:
            # Both modifying strength - use timestamp for ordering
            if self.timestamp <= other.timestamp:
                return self  # This operation wins
            else:
                # Adjust based on other's change
                transformed = self._copy()
                transformed.original_strength = other.strength
                return transformed
        else:
            # Modify strength after other modifications - apply normally
            return self

    def _transform_modify_type_against(self, other: 'RelationshipOperation') -> 'RelationshipOperation':
        """Transform MODIFY_TYPE operation against another operation"""
        if other.operation_type == RelationshipOperationType.DELETE:
            return self._create_no_op()
        elif other.operation_type == RelationshipOperationType.CREATE:
            return self
        elif other.operation_type == RelationshipOperationType.MODIFY_TYPE:
            # Both modifying type - use timestamp for ordering
            if self.timestamp <= other.timestamp:
                return self
            else:
                transformed = self._copy()
                transformed.original_type = other.relationship_type
                return transformed
        else:
            return self

    def _transform_modify_metadata_against(self, other: 'RelationshipOperation') -> 'RelationshipOperation':
        """Transform MODIFY_METADATA operation against another operation"""
        if other.operation_type == RelationshipOperationType.DELETE:
            return self._create_no_op()
        elif other.operation_type == RelationshipOperationType.CREATE:
            return self
        elif other.operation_type == RelationshipOperationType.MODIFY_METADATA:
            # Both modifying metadata - merge the changes
            transformed = self._copy()
            if other.metadata and self.metadata:
                # Merge metadata from both operations
                merged_metadata = {**other.metadata, **self.metadata}
                transformed.metadata = merged_metadata
            return transformed
        else:
            return self

    def _create_no_op(self) -> 'RelationshipOperation':
        """Create a no-operation version of this operation"""
        no_op = self._copy()
        no_op.operation_type = RelationshipOperationType.MODIFY_METADATA
        no_op.metadata = {}  # Empty metadata change = no-op
        return no_op

    def _copy(self) -> 'RelationshipOperation':
        """Create a copy of this operation"""
        return RelationshipOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=self.operation_type,
            source_memory_id=self.source_memory_id,
            target_memory_id=self.target_memory_id,
            user_id=self.user_id,
            timestamp=self.timestamp,
            version=self.version,
            relationship_type=self.relationship_type,
            strength=self.strength,
            metadata=self.metadata.copy() if self.metadata else None,
            original_strength=self.original_strength,
            original_type=self.original_type,
            original_metadata=self.original_metadata.copy() if self.original_metadata else None
        )

    def compose_with(self, other: 'RelationshipOperation') -> Optional['RelationshipOperation']:
        """
        Compose this operation with another sequential operation
        
        Returns composed operation or None if operations cannot be composed.
        """
        if self.get_relationship_id() != other.get_relationship_id():
            return None  # Cannot compose operations on different relationships
        
        if self.user_id != other.user_id:
            return None  # Cannot compose operations from different users
        
        # Check if operations can be composed sequentially
        if other.timestamp < self.timestamp:
            return None  # Wrong order for composition
        
        # Compose based on operation types
        if (self.operation_type == RelationshipOperationType.MODIFY_STRENGTH and 
            other.operation_type == RelationshipOperationType.MODIFY_STRENGTH):
            # Compose two strength modifications
            composed = other._copy()
            composed.original_strength = self.original_strength
            return composed
        
        elif (self.operation_type == RelationshipOperationType.MODIFY_TYPE and 
              other.operation_type == RelationshipOperationType.MODIFY_TYPE):
            # Compose two type modifications
            composed = other._copy()
            composed.original_type = self.original_type
            return composed
        
        elif (self.operation_type == RelationshipOperationType.MODIFY_METADATA and 
              other.operation_type == RelationshipOperationType.MODIFY_METADATA):
            # Compose two metadata modifications
            composed = other._copy()
            if self.metadata and other.metadata:
                composed.metadata = {**self.metadata, **other.metadata}
            return composed
        
        return None  # Operations cannot be composed

    def invert(self) -> 'RelationshipOperation':
        """Create the inverse operation that undoes this operation"""
        inverse = self._copy()
        inverse.operation_id = str(uuid.uuid4())
        
        if self.operation_type == RelationshipOperationType.CREATE:
            inverse.operation_type = RelationshipOperationType.DELETE
        elif self.operation_type == RelationshipOperationType.DELETE:
            inverse.operation_type = RelationshipOperationType.CREATE
        elif self.operation_type == RelationshipOperationType.MODIFY_STRENGTH:
            inverse.strength = self.original_strength
            inverse.original_strength = self.strength
        elif self.operation_type == RelationshipOperationType.MODIFY_TYPE:
            inverse.relationship_type = self.original_type
            inverse.original_type = self.relationship_type
        elif self.operation_type == RelationshipOperationType.MODIFY_METADATA:
            inverse.metadata = self.original_metadata
            inverse.original_metadata = self.metadata
        
        return inverse

    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary for serialization"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "source_memory_id": self.source_memory_id,
            "target_memory_id": self.target_memory_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "metadata": self.metadata,
            "original_strength": self.original_strength,
            "original_type": self.original_type,
            "original_metadata": self.original_metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipOperation':
        """Create operation from dictionary"""
        return cls(
            operation_id=data["operation_id"],
            operation_type=RelationshipOperationType(data["operation_type"]),
            source_memory_id=data["source_memory_id"],
            target_memory_id=data["target_memory_id"],
            user_id=data["user_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data["version"],
            relationship_type=data.get("relationship_type"),
            strength=data.get("strength"),
            metadata=data.get("metadata"),
            original_strength=data.get("original_strength"),
            original_type=data.get("original_type"),
            original_metadata=data.get("original_metadata")
        )


@dataclass
class RelationshipState:
    """Represents the current state of a memory relationship"""
    source_memory_id: str
    target_memory_id: str
    relationship_type: str
    strength: float
    metadata: Dict[str, Any]
    created_by: str
    created_at: datetime
    last_modified_by: str
    last_modified_at: datetime
    version: int
    collaborators: Set[str]

    def get_relationship_id(self) -> str:
        """Generate consistent relationship ID"""
        memory_ids = sorted([self.source_memory_id, self.target_memory_id])
        return f"rel_{memory_ids[0]}_{memory_ids[1]}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "source_memory_id": self.source_memory_id,
            "target_memory_id": self.target_memory_id,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "metadata": self.metadata,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "last_modified_by": self.last_modified_by,
            "last_modified_at": self.last_modified_at.isoformat(),
            "version": self.version,
            "collaborators": list(self.collaborators)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipState':
        """Create from dictionary"""
        return cls(
            source_memory_id=data["source_memory_id"],
            target_memory_id=data["target_memory_id"],
            relationship_type=data["relationship_type"],
            strength=data["strength"],
            metadata=data["metadata"],
            created_by=data["created_by"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_modified_by=data["last_modified_by"],
            last_modified_at=datetime.fromisoformat(data["last_modified_at"]),
            version=data["version"],
            collaborators=set(data["collaborators"])
        )


class RelationshipOTDocument:
    """
    Operational Transformation document for collaborative relationship editing
    
    This class manages a single relationship's collaborative editing state,
    handling operation application, transformation, and conflict resolution.
    """

    def __init__(self, initial_state: Optional[RelationshipState] = None) -> None:
        self.state = initial_state
        self.operation_history: List[RelationshipOperation] = []
        self.pending_operations: List[RelationshipOperation] = []
        self.operation_observers: List[Callable[[RelationshipOperation], None]] = []
        self._lock = asyncio.Lock()

    async def apply_operation(self, operation: RelationshipOperation, 
                            is_local: bool = True) -> bool:
        """
        Apply an operation to the relationship document
        
        Args:
            operation: The operation to apply
            is_local: Whether this operation originated locally
            
        Returns:
            True if operation was applied successfully
        """
        async with self._lock:
            try:
                # Transform operation against pending operations if remote
                if not is_local:
                    operation = await self._transform_against_pending(operation)
                
                # Apply the operation
                success = self._apply_operation_internal(operation)
                
                if success:
                    # Add to history
                    self.operation_history.append(operation)
                    
                    # Remove from pending if it was local
                    if is_local and operation in self.pending_operations:
                        self.pending_operations.remove(operation)
                    
                    # Notify observers
                    for observer in self.operation_observers:
                        observer(operation)
                
                return success
                
            except Exception as e:
                logger.error(f"Error applying relationship operation: {e}")
                return False

    def _apply_operation_internal(self, operation: RelationshipOperation) -> bool:
        """Internal operation application logic"""
        if operation.operation_type == RelationshipOperationType.CREATE:
            return self._apply_create(operation)
        elif operation.operation_type == RelationshipOperationType.DELETE:
            return self._apply_delete(operation)
        elif operation.operation_type == RelationshipOperationType.MODIFY_STRENGTH:
            return self._apply_modify_strength(operation)
        elif operation.operation_type == RelationshipOperationType.MODIFY_TYPE:
            return self._apply_modify_type(operation)
        elif operation.operation_type == RelationshipOperationType.MODIFY_METADATA:
            return self._apply_modify_metadata(operation)
        
        return False

    def _apply_create(self, operation: RelationshipOperation) -> bool:
        """Apply CREATE operation"""
        if self.state is not None:
            return False  # Relationship already exists
        
        self.state = RelationshipState(
            source_memory_id=operation.source_memory_id,
            target_memory_id=operation.target_memory_id,
            relationship_type=operation.relationship_type or "default",
            strength=operation.strength or 0.5,
            metadata=operation.metadata or {},
            created_by=operation.user_id,
            created_at=operation.timestamp,
            last_modified_by=operation.user_id,
            last_modified_at=operation.timestamp,
            version=operation.version,
            collaborators={operation.user_id}
        )
        return True

    def _apply_delete(self, operation: RelationshipOperation) -> bool:
        """Apply DELETE operation"""
        if self.state is None:
            return False  # Relationship doesn't exist
        
        self.state = None
        return True

    def _apply_modify_strength(self, operation: RelationshipOperation) -> bool:
        """Apply MODIFY_STRENGTH operation"""
        if self.state is None or operation.strength is None:
            return False
        
        assert self.state is not None  # Type checker hint
        self.state.strength = operation.strength
        self.state.last_modified_by = operation.user_id
        self.state.last_modified_at = operation.timestamp
        self.state.version = operation.version
        self.state.collaborators.add(operation.user_id)
        return True

    def _apply_modify_type(self, operation: RelationshipOperation) -> bool:
        """Apply MODIFY_TYPE operation"""
        if self.state is None or not operation.relationship_type:
            return False
        
        assert self.state is not None  # Type checker hint
        self.state.relationship_type = operation.relationship_type
        self.state.last_modified_by = operation.user_id
        self.state.last_modified_at = operation.timestamp
        self.state.version = operation.version
        self.state.collaborators.add(operation.user_id)
        return True

    def _apply_modify_metadata(self, operation: RelationshipOperation) -> bool:
        """Apply MODIFY_METADATA operation"""
        if self.state is None:
            return False
        
        assert self.state is not None  # Type checker hint
        if operation.metadata:
            self.state.metadata.update(operation.metadata)
        
        self.state.last_modified_by = operation.user_id
        self.state.last_modified_at = operation.timestamp
        self.state.version = operation.version
        self.state.collaborators.add(operation.user_id)
        return True

    async def _transform_against_pending(self, operation: RelationshipOperation) -> RelationshipOperation:
        """Transform operation against all pending operations"""
        transformed = operation
        for pending_op in self.pending_operations:
            if pending_op.is_concurrent_with(transformed):
                transformed = transformed.transform_against(pending_op)
        return transformed

    def add_operation_observer(self, observer: Callable[[RelationshipOperation], None]) -> None:
        """Add observer for operation events"""
        self.operation_observers.append(observer)

    def remove_operation_observer(self, observer: Callable[[RelationshipOperation], None]) -> None:
        """Remove operation observer"""
        if observer in self.operation_observers:
            self.operation_observers.remove(observer)

    async def add_pending_operation(self, operation: RelationshipOperation) -> None:
        """Add operation to pending list"""
        async with self._lock:
            self.pending_operations.append(operation)

    def get_current_state(self) -> Optional[RelationshipState]:
        """Get current relationship state"""
        return self.state


class RelationshipOTManager:
    """
    Manager for relationship operational transformation with Redis coordination
    
    This class coordinates multiple relationship documents, handles Redis integration,
    and provides high-level operations for collaborative relationship editing.
    """

    def __init__(self, redis_client: Redis, memory_crdt_manager: MemoryCRDTManager) -> None:
        self.redis_client = redis_client
        self.memory_crdt_manager = memory_crdt_manager
        self.documents: Dict[str, RelationshipOTDocument] = {}
        self.document_locks: Dict[str, asyncio.Lock] = {}
        
        # Redis key patterns
        self.RELATIONSHIP_STATE_KEY = "relationship:state:{relationship_id}"
        self.RELATIONSHIP_OPS_KEY = "relationship:ops:{relationship_id}"
        self.RELATIONSHIP_LOCK_KEY = "relationship:lock:{relationship_id}"
        
        # Configuration
        self.CACHE_TTL = 3600  # 1 hour
        self.MAX_OPERATION_HISTORY = 1000

    async def get_relationship_document(self, source_memory_id: str, target_memory_id: str,
                                      user_id: str, role: UserRole) -> Optional[RelationshipOTDocument]:
        """Get or create relationship document with permission checking"""
        
        # Verify read permission
        if not verify_collaboration_permission(role, CollaborationPermission.READ_MEMORY):
            logger.warning(f"User {user_id} lacks READ_MEMORY permission")
            return None
        
        # Generate relationship ID
        memory_ids = sorted([source_memory_id, target_memory_id])
        relationship_id = f"rel_{memory_ids[0]}_{memory_ids[1]}"
        
        # Get or create document lock
        if relationship_id not in self.document_locks:
            self.document_locks[relationship_id] = asyncio.Lock()
        
        async with self.document_locks[relationship_id]:
            # Check if document already loaded
            if relationship_id in self.documents:
                return self.documents[relationship_id]
            
            # Load from Redis cache
            cached_state = await self._load_relationship_from_cache(relationship_id)
            
            # Create document
            document = RelationshipOTDocument(cached_state)
            
            # Setup operation observer for Redis sync
            document.add_operation_observer(self._on_operation_applied)
            
            # Store document
            self.documents[relationship_id] = document
            
            return document

    async def create_relationship(self, source_memory_id: str, target_memory_id: str,
                                relationship_type: str, strength: float,
                                user_id: str, role: UserRole,
                                metadata: Optional[Dict[str, Any]] = None) -> Optional[RelationshipOperation]:
        """Create a new relationship with operational transformation"""
        
        # Verify write permission
        if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
            logger.warning(f"User {user_id} lacks WRITE_MEMORY permission")
            return None
        
        # Create operation
        operation = RelationshipOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=RelationshipOperationType.CREATE,
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            version=1,
            relationship_type=relationship_type,
            strength=strength,
            metadata=metadata or {}
        )
        
        # Get document and apply operation
        document = await self.get_relationship_document(source_memory_id, target_memory_id, user_id, role)
        if document:
            await document.add_pending_operation(operation)
            success = await document.apply_operation(operation, is_local=True)
            if success:
                await self._broadcast_operation(operation)
                return operation
        
        return None

    async def delete_relationship(self, source_memory_id: str, target_memory_id: str,
                                user_id: str, role: UserRole) -> Optional[RelationshipOperation]:
        """Delete a relationship with operational transformation"""
        
        # Verify delete permission
        if not verify_collaboration_permission(role, CollaborationPermission.DELETE_MEMORY):
            logger.warning(f"User {user_id} lacks DELETE_MEMORY permission")
            return None
        
        # Get current state for version
        document = await self.get_relationship_document(source_memory_id, target_memory_id, user_id, role)
        if not document or not document.get_current_state():
            return None  # Relationship doesn't exist
        
        current_state = document.get_current_state()
        assert current_state is not None  # Type checker hint
        
        operation = RelationshipOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=RelationshipOperationType.DELETE,
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            version=current_state.version + 1
        )
        
        await document.add_pending_operation(operation)
        success = await document.apply_operation(operation, is_local=True)
        if success:
            await self._broadcast_operation(operation)
            return operation
        
        return None

    async def modify_relationship_strength(self, source_memory_id: str, target_memory_id: str,
                                         new_strength: float, user_id: str, role: UserRole) -> Optional[RelationshipOperation]:
        """Modify relationship strength with operational transformation"""
        
        if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
            logger.warning(f"User {user_id} lacks WRITE_MEMORY permission")
            return None
        
        document = await self.get_relationship_document(source_memory_id, target_memory_id, user_id, role)
        if not document or not document.get_current_state():
            return None
        
        current_state = document.get_current_state()
        assert current_state is not None  # Type checker hint
        
        operation = RelationshipOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=RelationshipOperationType.MODIFY_STRENGTH,
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            version=current_state.version + 1,
            strength=new_strength,
            original_strength=current_state.strength
        )
        
        await document.add_pending_operation(operation)
        success = await document.apply_operation(operation, is_local=True)
        if success:
            await self._broadcast_operation(operation)
            return operation
        
        return None

    async def _load_relationship_from_cache(self, relationship_id: str) -> Optional[RelationshipState]:
        """Load relationship state from Redis cache"""
        try:
            cache_key = self.RELATIONSHIP_STATE_KEY.format(relationship_id=relationship_id)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return RelationshipState.from_dict(data)
                
        except Exception as e:
            logger.error(f"Error loading relationship {relationship_id} from cache: {e}")
        
        return None

    async def _save_relationship_to_cache(self, relationship_id: str, state: RelationshipState) -> None:
        """Save relationship state to Redis cache"""
        try:
            cache_key = self.RELATIONSHIP_STATE_KEY.format(relationship_id=relationship_id)
            data = json.dumps(state.to_dict())
            await self.redis_client.setex(cache_key, self.CACHE_TTL, data)
            
        except Exception as e:
            logger.error(f"Error saving relationship {relationship_id} to cache: {e}")

    def _on_operation_applied(self, operation: RelationshipOperation) -> None:
        """Handle operation applied events"""
        # This could trigger immediate sync for critical changes
        # or be used for real-time notifications
        logger.debug(f"Relationship operation applied: {operation.operation_type} on {operation.get_relationship_id()}")

    async def _broadcast_operation(self, operation: RelationshipOperation) -> None:
        """Broadcast operation to other collaborators via Redis"""
        try:
            ops_key = self.RELATIONSHIP_OPS_KEY.format(relationship_id=operation.get_relationship_id())
            operation_data = json.dumps(operation.to_dict())
            
            # Store operation with timestamp-based key
            timestamp_key = f"{ops_key}:{operation.timestamp.timestamp()}"
            await self.redis_client.setex(timestamp_key, self.CACHE_TTL, operation_data)
            
            # Also publish for real-time sync
            await self.redis_client.publish(f"relationship_ops:{operation.get_relationship_id()}", operation_data)
            
        except Exception as e:
            logger.error(f"Error broadcasting relationship operation: {e}")

    async def close_relationship_document(self, relationship_id: str) -> None:
        """Close and cleanup relationship document"""
        if relationship_id in self.documents:
            document = self.documents[relationship_id]
            state = document.get_current_state()
            
            if state:
                await self._save_relationship_to_cache(relationship_id, state)
            
            del self.documents[relationship_id]
            if relationship_id in self.document_locks:
                del self.document_locks[relationship_id]

    async def shutdown(self) -> None:
        """Shutdown manager and cleanup all documents"""
        relationship_ids = list(self.documents.keys())
        for relationship_id in relationship_ids:
            await self.close_relationship_document(relationship_id)


# Global manager instance
_relationship_ot_manager: Optional[RelationshipOTManager] = None


async def get_relationship_ot_manager() -> RelationshipOTManager:
    """Get global relationship OT manager instance"""
    global _relationship_ot_manager
    
    if _relationship_ot_manager is None:
        from .memory_crdt import get_memory_crdt_manager
        
        # Initialize Redis client and get memory CRDT manager
        redis_client = redis.from_url("redis://localhost:6379/0")
        memory_manager = await get_memory_crdt_manager()
        
        _relationship_ot_manager = RelationshipOTManager(redis_client, memory_manager)
    
    return _relationship_ot_manager


async def create_memory_relationship(source_memory_id: str, target_memory_id: str,
                                   relationship_type: str, strength: float,
                                   user_id: str, role: UserRole,
                                   metadata: Optional[Dict[str, Any]] = None) -> Optional[RelationshipOperation]:
    """Create a new collaborative memory relationship"""
    manager = await get_relationship_ot_manager()
    return await manager.create_relationship(
        source_memory_id, target_memory_id, relationship_type, strength, user_id, role, metadata
    )


async def delete_memory_relationship(source_memory_id: str, target_memory_id: str,
                                   user_id: str, role: UserRole) -> Optional[RelationshipOperation]:
    """Delete a collaborative memory relationship"""
    manager = await get_relationship_ot_manager()
    return await manager.delete_relationship(source_memory_id, target_memory_id, user_id, role)


async def modify_relationship_strength(source_memory_id: str, target_memory_id: str,
                                     new_strength: float, user_id: str, role: UserRole) -> Optional[RelationshipOperation]:
    """Modify the strength of a collaborative memory relationship"""
    manager = await get_relationship_ot_manager()
    return await manager.modify_relationship_strength(source_memory_id, target_memory_id, new_strength, user_id, role)


async def shutdown_relationship_ot() -> None:
    """Shutdown relationship OT system"""
    global _relationship_ot_manager
    if _relationship_ot_manager:
        await _relationship_ot_manager.shutdown()
        _relationship_ot_manager = None


# Performance and monitoring integration
class RelationshipOTMetrics:
    """Metrics collector for relationship OT operations"""
    
    def __init__(self) -> None:
        self.operation_count = 0
        self.transform_count = 0
        self.conflict_count = 0
        self.error_count = 0
        self.average_transform_time = 0.0
    
    def record_operation(self) -> None:
        """Record a relationship operation"""
        self.operation_count += 1
    
    def record_transform(self, duration: float) -> None:
        """Record a transform operation"""
        self.transform_count += 1
        self.average_transform_time = ((self.average_transform_time * (self.transform_count - 1) + duration) 
                                     / self.transform_count)
    
    def record_conflict(self) -> None:
        """Record a conflict resolution"""
        self.conflict_count += 1
    
    def record_error(self) -> None:
        """Record an error"""
        self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            "operation_count": self.operation_count,
            "transform_count": self.transform_count,
            "conflict_count": self.conflict_count,
            "error_count": self.error_count,
            "average_transform_time": self.average_transform_time
        }


# Global metrics instance
relationship_ot_metrics = RelationshipOTMetrics() 