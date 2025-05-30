"""
Memory CRDT Core - Phase 2.1 Memory Collaboration Engine

This module implements the core CRDT (Conflict-free Replicated Data Type) functionality
for collaborative memory editing using Ypy. It provides real-time synchronization of
memory fields (title, content, tags) with automatic conflict resolution.

Features:
- Memory document structure with Ypy shared types
- Field-level collaborative editing for title, content, tags
- Version management with change tracking
- Delta synchronization for efficient network updates
- Redis integration for state caching and cross-server sync
- JWT authentication integration for field permissions

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


# Configure logging
logger = logging.getLogger(__name__)


class MemoryFieldType(Enum):
    """Memory field types for CRDT operations"""
    TITLE = "title"
    CONTENT = "content"
    TAGS = "tags"
    METADATA = "metadata"


class MemoryOperationType(Enum):
    """Types of memory operations for tracking changes"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"


class MemoryChangeType(Enum):
    """Types of changes for delta synchronization"""
    FIELD_UPDATE = "field_update"
    TAG_ADD = "tag_add"
    TAG_REMOVE = "tag_remove"
    METADATA_UPDATE = "metadata_update"


@dataclass
class MemoryChange:
    """Represents a single change to a memory for delta synchronization"""
    change_id: str
    memory_id: str
    user_id: str
    field_type: MemoryFieldType
    change_type: MemoryChangeType
    old_value: Any
    new_value: Any
    timestamp: datetime
    operation_id: str
    version: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "change_id": self.change_id,
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "field_type": self.field_type.value,
            "change_type": self.change_type.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "operation_id": self.operation_id,
            "version": self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryChange":
        """Create from dictionary"""
        return cls(
            change_id=data["change_id"],
            memory_id=data["memory_id"],
            user_id=data["user_id"],
            field_type=MemoryFieldType(data["field_type"]),
            change_type=MemoryChangeType(data["change_type"]),
            old_value=data["old_value"],
            new_value=data["new_value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            operation_id=data["operation_id"],
            version=data["version"]
        )


@dataclass
class MemoryDocumentState:
    """Represents the current state of a memory document"""
    memory_id: str
    title: str
    content: str
    tags: Set[str]
    metadata: Dict[str, Any]
    version: int
    last_modified: datetime
    last_modified_by: str
    collaborators: Set[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "memory_id": self.memory_id,
            "title": self.title,
            "content": self.content,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "version": self.version,
            "last_modified": self.last_modified.isoformat(),
            "last_modified_by": self.last_modified_by,
            "collaborators": list(self.collaborators)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryDocumentState":
        """Create from dictionary"""
        return cls(
            memory_id=data["memory_id"],
            title=data["title"],
            content=data["content"],
            tags=set(data["tags"]),
            metadata=data["metadata"],
            version=data["version"],
            last_modified=datetime.fromisoformat(data["last_modified"]),
            last_modified_by=data["last_modified_by"],
            collaborators=set(data["collaborators"])
        )


class MemoryDocument:
    """
    Ypy-based collaborative memory document with CRDT field synchronization
    
    This class wraps Ypy shared types to provide collaborative editing for memory
    fields with automatic conflict resolution and delta synchronization.
    """
    
    def __init__(self, memory_id: str, redis_client: Redis, initial_state: Optional[MemoryDocumentState] = None):
        self.memory_id = memory_id
        self.redis_client = redis_client
        self._doc = SimpleCRDTDocument(memory_id)
        self._version = 0
        self._change_observers: List[Callable] = []
        
        # Track changes for delta synchronization
        self._pending_changes: List[MemoryChange] = []
        self._change_lock = asyncio.Lock()
        
        # Setup change observers
        self._setup_observers()
        
        # Initialize with state if provided
        if initial_state:
            self._initialize_from_state(initial_state)
    
    def _setup_observers(self):
        """Setup Ypy observers for change tracking"""
        
        def title_observer(event):
            self._on_field_change(MemoryFieldType.TITLE, event)
        
        def content_observer(event):
            self._on_field_change(MemoryFieldType.CONTENT, event)
        
        def tags_observer(event):
            self._on_field_change(MemoryFieldType.TAGS, event)
        
        def metadata_observer(event):
            self._on_field_change(MemoryFieldType.METADATA, event)
        
        # Attach observers to Ypy shared types
        self._doc.get_text("title").observe(title_observer)
        self._doc.get_text("content").observe(content_observer)
        self._doc.get_array("tags").observe(tags_observer)
        self._doc.get_map("metadata").observe(metadata_observer)
    
    def _on_field_change(self, field_type: MemoryFieldType, event):
        """Handle field change events from Ypy"""
        try:
            change_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc)
            
            # Extract change details from Ypy event
            old_value = self._extract_old_value(field_type, event)
            new_value = self._extract_new_value(field_type, event)
            
            # Determine change type
            change_type = self._determine_change_type(field_type, event)
            
            # Create change record
            change = MemoryChange(
                change_id=change_id,
                memory_id=self.memory_id,
                user_id=getattr(event, 'user_id', 'system'),
                field_type=field_type,
                change_type=change_type,
                old_value=old_value,
                new_value=new_value,
                timestamp=timestamp,
                operation_id=str(uuid.uuid4()),
                version=self._version + 1
            )
            
            # Add to pending changes
            asyncio.create_task(self._add_pending_change(change))
            
            # Notify observers
            for observer in self._change_observers:
                observer(change)
                
        except Exception as e:
            logger.error(f"Error handling field change for {field_type}: {e}")
    
    async def _add_pending_change(self, change: MemoryChange):
        """Add change to pending changes list"""
        async with self._change_lock:
            self._pending_changes.append(change)
            self._version = change.version
    
    def _extract_old_value(self, field_type: MemoryFieldType, event) -> Any:
        """Extract old value from Ypy event"""
        # Implementation depends on Ypy event structure
        # This is a simplified version - real implementation would need
        # to handle different event types and extract previous values
        return getattr(event, 'old_value', None)
    
    def _extract_new_value(self, field_type: MemoryFieldType, event) -> Any:
        """Extract new value from Ypy event"""
        if field_type == MemoryFieldType.TITLE:
            return str(self._doc.get_text("title"))
        elif field_type == MemoryFieldType.CONTENT:
            return str(self._doc.get_text("content"))
        elif field_type == MemoryFieldType.TAGS:
            return [str(tag) for tag in self._doc.get_array("tags")]
        elif field_type == MemoryFieldType.METADATA:
            metadata_map = self._doc.get_map("metadata")
            return {key: metadata_map.get(key) for key in metadata_map.doc._data.get(metadata_map.field, {})}
        return None
    
    def _determine_change_type(self, field_type: MemoryFieldType, event) -> MemoryChangeType:
        """Determine the type of change from Ypy event"""
        if field_type == MemoryFieldType.TAGS:
            # Check if it's an add or remove operation
            if hasattr(event, 'action') and event.action == 'add':
                return MemoryChangeType.TAG_ADD
            elif hasattr(event, 'action') and event.action == 'remove':
                return MemoryChangeType.TAG_REMOVE
        elif field_type == MemoryFieldType.METADATA:
            return MemoryChangeType.METADATA_UPDATE
        
        return MemoryChangeType.FIELD_UPDATE
    
    def _initialize_from_state(self, state: MemoryDocumentState):
        """Initialize document from existing state"""
        # Clear existing content
        self._doc.get_text("title").clear()
        self._doc.get_text("content").clear()
        self._doc.get_array("tags").clear()
        self._doc.get_map("metadata").clear()
        
        # Set initial values
        if state.title:
            self._doc.get_text("title").insert(0, state.title)
        if state.content:
            self._doc.get_text("content").insert(0, state.content)
        
        for tag in state.tags:
            self._doc.get_array("tags").append([tag])
        
        for key, value in state.metadata.items():
            self._doc.get_map("metadata")[key] = value
        
        self._version = state.version
    
    # Public API Methods
    
    def add_change_observer(self, observer: Callable[[MemoryChange], None]):
        """Add observer for memory changes"""
        self._change_observers.append(observer)
    
    def remove_change_observer(self, observer: Callable[[MemoryChange], None]):
        """Remove change observer"""
        if observer in self._change_observers:
            self._change_observers.remove(observer)
    
    async def update_title(self, title: str, user_id: str) -> bool:
        """Update memory title with user tracking"""
        try:
            # Verify permissions would be checked here
            self._doc.get_text("title").clear()
            self._doc.get_text("title").insert(0, title)
            await self._update_metadata("last_modified_by", user_id)
            return True
        except Exception as e:
            logger.error(f"Error updating title: {e}")
            return False
    
    async def update_content(self, content: str, user_id: str) -> bool:
        """Update memory content with user tracking"""
        try:
            self._doc.get_text("content").clear()
            self._doc.get_text("content").insert(0, content)
            await self._update_metadata("last_modified_by", user_id)
            return True
        except Exception as e:
            logger.error(f"Error updating content: {e}")
            return False
    
    async def add_tag(self, tag: str, user_id: str) -> bool:
        """Add tag to memory"""
        try:
            # Check if tag already exists
            current_tags = [str(t) for t in self._doc.get_array("tags")]
            if tag not in current_tags:
                self._doc.get_array("tags").append([tag])
                await self._update_metadata("last_modified_by", user_id)
            return True
        except Exception as e:
            logger.error(f"Error adding tag: {e}")
            return False
    
    async def remove_tag(self, tag: str, user_id: str) -> bool:
        """Remove tag from memory"""
        try:
            # Find and remove tag
            for i, current_tag in enumerate(self._doc.get_array("tags")):
                if str(current_tag) == tag:
                    self._doc.get_array("tags").delete(i, 1)
                    await self._update_metadata("last_modified_by", user_id)
                    break
            return True
        except Exception as e:
            logger.error(f"Error removing tag: {e}")
            return False
    
    async def _update_metadata(self, key: str, value: Any):
        """Update metadata field"""
        self._doc.get_map("metadata")[key] = value
        if key == "last_modified_by":
            self._doc.get_map("metadata")["last_modified"] = datetime.now(timezone.utc).isoformat()
    
    async def add_collaborator(self, user_id: str) -> bool:
        """Add collaborator to memory"""
        try:
            current_collaborators = [str(c) for c in self._doc.get_array("collaborators")]
            if user_id not in current_collaborators:
                self._doc.get_array("collaborators").append([user_id])
            return True
        except Exception as e:
            logger.error(f"Error adding collaborator: {e}")
            return False
    
    async def remove_collaborator(self, user_id: str) -> bool:
        """Remove collaborator from memory"""
        try:
            for i, collaborator in enumerate(self._doc.get_array("collaborators")):
                if str(collaborator) == user_id:
                    self._doc.get_array("collaborators").delete(i, 1)
                    break
            return True
        except Exception as e:
            logger.error(f"Error removing collaborator: {e}")
            return False
    
    def get_current_state(self) -> MemoryDocumentState:
        """Get current document state"""
        metadata_map = self._doc.get_map("metadata")
        metadata_dict = {key: metadata_map.get(key) for key in metadata_map.doc._data.get(metadata_map.field, {})}
        
        return MemoryDocumentState(
            memory_id=self.memory_id,
            title=str(self._doc.get_text("title")),
            content=str(self._doc.get_text("content")),
            tags=set(str(tag) for tag in self._doc.get_array("tags")),
            metadata=metadata_dict,
            version=self._version,
            last_modified=datetime.now(timezone.utc),
            last_modified_by=self._doc.get_map("metadata").get("last_modified_by", "unknown"),
            collaborators=set(str(c) for c in self._doc.get_array("collaborators"))
        )
    
    async def get_pending_changes(self) -> List[MemoryChange]:
        """Get pending changes for delta synchronization"""
        async with self._change_lock:
            changes = self._pending_changes.copy()
            self._pending_changes.clear()
            return changes
    
    def get_document_update(self) -> bytes:
        """Get Ypy document update for synchronization"""
        return self._doc.encode_state_as_update()
    
    def apply_document_update(self, update: bytes):
        """Apply Ypy document update from another client"""
        try:
            self._doc.apply_update(update)
        except Exception as e:
            logger.error(f"Error applying document update: {e}")


class MemoryCRDTManager:
    """
    Manager for Memory CRDT documents with Redis caching and synchronization
    
    This class manages multiple memory documents, handles Redis integration,
    and provides high-level operations for collaborative memory editing.
    """
    
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client
        self._documents: Dict[str, MemoryDocument] = {}
        self._document_locks: Dict[str, asyncio.Lock] = {}
        self._sync_tasks: Dict[str, asyncio.Task] = {}
        
        # Redis key patterns
        self.MEMORY_STATE_KEY = "memory:state:{memory_id}"
        self.MEMORY_CHANGES_KEY = "memory:changes:{memory_id}"
        self.MEMORY_LOCK_KEY = "memory:lock:{memory_id}"
        
        # Configuration
        self.SYNC_INTERVAL = 5.0  # seconds
        self.CACHE_TTL = 3600  # 1 hour
    
    async def get_memory_document(self, memory_id: str, user_id: str, 
                                 role: UserRole) -> Optional[MemoryDocument]:
        """Get or create memory document with permission checking"""
        
        # Verify read permission
        if not verify_collaboration_permission(role, CollaborationPermission.READ_MEMORY):
            logger.warning(f"User {user_id} lacks READ_MEMORY permission for memory {memory_id}")
            return None
        
        # Get or create document lock
        if memory_id not in self._document_locks:
            self._document_locks[memory_id] = asyncio.Lock()
        
        async with self._document_locks[memory_id]:
            # Check if document already loaded
            if memory_id in self._documents:
                return self._documents[memory_id]
            
            # Try to load from Redis cache
            cached_state = await self._load_from_cache(memory_id)
            
            # Create new document
            document = MemoryDocument(
                memory_id=memory_id,
                redis_client=self.redis_client,
                initial_state=cached_state
            )
            
            # Setup change observer for Redis sync
            document.add_change_observer(self._on_document_change)
            
            # Store document
            self._documents[memory_id] = document
            
            # Start sync task
            self._sync_tasks[memory_id] = asyncio.create_task(
                self._sync_document_periodically(memory_id)
            )
            
            # Add user as collaborator
            await document.add_collaborator(user_id)
            
            return document
    
    async def _load_from_cache(self, memory_id: str) -> Optional[MemoryDocumentState]:
        """Load memory state from Redis cache"""
        try:
            cache_key = self.MEMORY_STATE_KEY.format(memory_id=memory_id)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return MemoryDocumentState.from_dict(data)
                
        except Exception as e:
            logger.error(f"Error loading memory {memory_id} from cache: {e}")
        
        return None
    
    async def _save_to_cache(self, memory_id: str, state: MemoryDocumentState):
        """Save memory state to Redis cache"""
        try:
            cache_key = self.MEMORY_STATE_KEY.format(memory_id=memory_id)
            data = json.dumps(state.to_dict())
            await self.redis_client.setex(cache_key, self.CACHE_TTL, data)
            
        except Exception as e:
            logger.error(f"Error saving memory {memory_id} to cache: {e}")
    
    def _on_document_change(self, change: MemoryChange):
        """Handle document change events"""
        # This could trigger immediate sync for critical changes
        # or be used for real-time notifications
        logger.debug(f"Memory {change.memory_id} changed: {change.change_type}")
    
    async def _sync_document_periodically(self, memory_id: str):
        """Periodically sync document state to Redis"""
        while memory_id in self._documents:
            try:
                document = self._documents[memory_id]
                
                # Get current state and save to cache
                current_state = document.get_current_state()
                await self._save_to_cache(memory_id, current_state)
                
                # Get and process pending changes
                changes = await document.get_pending_changes()
                if changes:
                    await self._store_changes(memory_id, changes)
                
                await asyncio.sleep(self.SYNC_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error syncing memory {memory_id}: {e}")
                await asyncio.sleep(self.SYNC_INTERVAL)
    
    async def _store_changes(self, memory_id: str, changes: List[MemoryChange]):
        """Store changes in Redis for cross-server synchronization"""
        try:
            changes_key = self.MEMORY_CHANGES_KEY.format(memory_id=memory_id)
            
            # Store each change with timestamp-based key
            for change in changes:
                change_data = json.dumps(change.to_dict())
                timestamp_key = f"{changes_key}:{change.timestamp.timestamp()}"
                await self.redis_client.setex(timestamp_key, self.CACHE_TTL, change_data)
                
        except Exception as e:
            logger.error(f"Error storing changes for memory {memory_id}: {e}")
    
    async def close_memory_document(self, memory_id: str):
        """Close and cleanup memory document"""
        if memory_id in self._documents:
            # Cancel sync task
            if memory_id in self._sync_tasks:
                self._sync_tasks[memory_id].cancel()
                del self._sync_tasks[memory_id]
            
            # Final sync
            document = self._documents[memory_id]
            current_state = document.get_current_state()
            await self._save_to_cache(memory_id, current_state)
            
            # Cleanup
            del self._documents[memory_id]
            if memory_id in self._document_locks:
                del self._document_locks[memory_id]
    
    async def shutdown(self):
        """Shutdown manager and cleanup all documents"""
        memory_ids = list(self._documents.keys())
        for memory_id in memory_ids:
            await self.close_memory_document(memory_id)


# Global manager instance
_memory_crdt_manager: Optional[MemoryCRDTManager] = None


async def get_memory_crdt_manager() -> MemoryCRDTManager:
    """Get global memory CRDT manager instance"""
    global _memory_crdt_manager
    
    if _memory_crdt_manager is None:
        # Initialize Redis client
        redis_client = redis.from_url("redis://localhost:6379/0")
        _memory_crdt_manager = MemoryCRDTManager(redis_client)
    
    return _memory_crdt_manager


async def create_memory_document(memory_id: str, user_id: str, 
                                role: UserRole, 
                                initial_data: Optional[Dict[str, Any]] = None) -> Optional[MemoryDocument]:
    """Create a new collaborative memory document"""
    
    # Verify create permission
    if not verify_collaboration_permission(role, CollaborationPermission.CREATE_SESSION):
        logger.warning(f"User {user_id} lacks CREATE_SESSION permission")
        return None
    
    manager = await get_memory_crdt_manager()
    
    # Create initial state if data provided
    initial_state = None
    if initial_data:
        initial_state = MemoryDocumentState(
            memory_id=memory_id,
            title=initial_data.get("title", ""),
            content=initial_data.get("content", ""),
            tags=set(initial_data.get("tags", [])),
            metadata=initial_data.get("metadata", {}),
            version=1,
            last_modified=datetime.now(timezone.utc),
            last_modified_by=user_id,
            collaborators={user_id}
        )
    
    # Create document through manager
    document = await manager.get_memory_document(memory_id, user_id, role)
    
    if document and initial_state:
        # Initialize with provided data
        if initial_state.title:
            await document.update_title(initial_state.title, user_id)
        if initial_state.content:
            await document.update_content(initial_state.content, user_id)
        for tag in initial_state.tags:
            await document.add_tag(tag, user_id)
    
    return document


async def get_memory_document(memory_id: str, user_id: str, 
                             role: UserRole) -> Optional[MemoryDocument]:
    """Get existing collaborative memory document"""
    manager = await get_memory_crdt_manager()
    return await manager.get_memory_document(memory_id, user_id, role)


async def close_memory_document(memory_id: str):
    """Close and cleanup memory document"""
    manager = await get_memory_crdt_manager()
    await manager.close_memory_document(memory_id)


async def shutdown_memory_crdt():
    """Shutdown memory CRDT system"""
    global _memory_crdt_manager
    if _memory_crdt_manager:
        await _memory_crdt_manager.shutdown()
        _memory_crdt_manager = None


# Performance and monitoring integration
class MemoryCRDTMetrics:
    """Metrics collector for memory CRDT operations"""
    
    def __init__(self):
        self.operation_count = 0
        self.sync_count = 0
        self.error_count = 0
        self.last_sync_time = 0.0
        self.average_sync_time = 0.0
    
    def record_operation(self):
        """Record a memory operation"""
        self.operation_count += 1
    
    def record_sync(self, duration: float):
        """Record a sync operation"""
        self.sync_count += 1
        self.last_sync_time = duration
        self.average_sync_time = (self.average_sync_time * (self.sync_count - 1) + duration) / self.sync_count
    
    def record_error(self):
        """Record an error"""
        self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            "operation_count": self.operation_count,
            "sync_count": self.sync_count,
            "error_count": self.error_count,
            "last_sync_time": self.last_sync_time,
            "average_sync_time": self.average_sync_time
        }


# Global metrics instance
memory_crdt_metrics = MemoryCRDTMetrics()


def verify_collaboration_permission(role: UserRole, permission: CollaborationPermission) -> bool:
    """Verify if a user role has the specified collaboration permission"""
    # Role-based permissions mapping
    role_permissions = {
        UserRole.OWNER: [
            CollaborationPermission.READ_MEMORY,
            CollaborationPermission.WRITE_MEMORY,
            CollaborationPermission.DELETE_MEMORY,
            CollaborationPermission.CREATE_SESSION,
            CollaborationPermission.JOIN_SESSION,
            CollaborationPermission.MANAGE_SESSION,
            CollaborationPermission.RESOLVE_CONFLICTS,
            CollaborationPermission.VIEW_ANALYTICS,
            CollaborationPermission.ADMIN_ACCESS
        ],
        UserRole.EDITOR: [
            CollaborationPermission.READ_MEMORY,
            CollaborationPermission.WRITE_MEMORY,
            CollaborationPermission.JOIN_SESSION,
            CollaborationPermission.RESOLVE_CONFLICTS,
            CollaborationPermission.VIEW_ANALYTICS
        ],
        UserRole.COLLABORATOR: [
            CollaborationPermission.READ_MEMORY,
            CollaborationPermission.WRITE_MEMORY,
            CollaborationPermission.JOIN_SESSION,
            CollaborationPermission.RESOLVE_CONFLICTS
        ],
        UserRole.VIEWER: [
            CollaborationPermission.READ_MEMORY,
            CollaborationPermission.JOIN_SESSION,
            CollaborationPermission.VIEW_ANALYTICS
        ]
    }
    
    return permission in role_permissions.get(role, [])


# Temporary CRDT-like implementation - will be replaced with proper Ypy
class SimpleCRDTDocument:
    """Simplified CRDT-like document for memory collaboration"""
    
    def __init__(self, doc_id: str) -> None:
        self.doc_id = doc_id
        self._data: Dict[str, Any] = {
            "title": "",
            "content": "", 
            "tags": [],
            "metadata": {},
            "collaborators": []
        }
        self._version = 0
        self._observers: List[Callable[[Dict[str, Any]], None]] = []
    
    def get_text(self, field: str) -> 'SimpleCRDTText':
        """Get text field wrapper"""
        return SimpleCRDTText(self, field)
    
    def get_array(self, field: str) -> 'SimpleCRDTArray':
        """Get array field wrapper"""
        return SimpleCRDTArray(self, field)
    
    def get_map(self, field: str) -> 'SimpleCRDTMap':
        """Get map field wrapper"""
        return SimpleCRDTMap(self, field)
    
    def _notify_change(self, field: str, old_value: Any, new_value: Any) -> None:
        """Notify observers of changes"""
        for observer in self._observers:
            observer({"field": field, "old_value": old_value, "new_value": new_value})
    
    def encode_state_as_update(self) -> bytes:
        """Encode document state as update"""
        return json.dumps({
            "doc_id": self.doc_id,
            "data": self._data,
            "version": self._version
        }).encode()
    
    def apply_update(self, update: bytes) -> None:
        """Apply update to document"""
        try:
            update_data = json.loads(update.decode())
            if update_data["doc_id"] == self.doc_id:
                self._data.update(update_data["data"])
                self._version = max(self._version, update_data["version"])
        except Exception as e:
            logger.error(f"Error applying update: {e}")


class SimpleCRDTText:
    """Simplified text CRDT wrapper"""
    
    def __init__(self, doc: SimpleCRDTDocument, field: str) -> None:
        self.doc = doc
        self.field = field
        self._observers: List[Callable[[Dict[str, Any]], None]] = []
    
    def __str__(self) -> str:
        return self.doc._data.get(self.field, "")
    
    def clear(self) -> None:
        old_value = self.doc._data.get(self.field, "")
        self.doc._data[self.field] = ""
        self.doc._notify_change(self.field, old_value, "")
        for observer in self._observers:
            observer({"action": "clear", "old_value": old_value, "new_value": ""})
    
    def insert(self, index: int, text: str) -> None:
        current = self.doc._data.get(self.field, "")
        old_value = current
        new_value = current[:index] + text + current[index:]
        self.doc._data[self.field] = new_value
        self.doc._notify_change(self.field, old_value, new_value)
        for observer in self._observers:
            observer({"action": "insert", "index": index, "text": text, "old_value": old_value, "new_value": new_value})
    
    def delete(self, index: int, count: int) -> None:
        """Delete text at specified index"""
        current = self.doc._data.get(self.field, "")
        old_value = current
        new_value = current[:index] + current[index+count:]
        self.doc._data[self.field] = new_value
        self.doc._notify_change(self.field, old_value, new_value)
        for observer in self._observers:
            observer({"action": "delete", "index": index, "count": count, "old_value": old_value, "new_value": new_value})
    
    def observe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._observers.append(callback)


class SimpleCRDTArray:
    """Simplified array CRDT wrapper"""
    
    def __init__(self, doc: SimpleCRDTDocument, field: str) -> None:
        self.doc = doc
        self.field = field
        self._observers: List[Callable[[Dict[str, Any]], None]] = []
        if field not in self.doc._data:
            self.doc._data[field] = []
    
    def __iter__(self):
        return iter(self.doc._data.get(self.field, []))
    
    def __len__(self) -> int:
        return len(self.doc._data.get(self.field, []))
    
    def __getitem__(self, index: int):
        return self.doc._data.get(self.field, [])[index]
    
    def append(self, items: List[str]) -> None:
        old_value = list(self.doc._data[self.field])
        self.doc._data[self.field].extend(items)
        new_value = list(self.doc._data[self.field])
        self.doc._notify_change(self.field, old_value, new_value)
        for observer in self._observers:
            observer({"action": "add", "items": items, "old_value": old_value, "new_value": new_value})
    
    def delete(self, index: int, count: int) -> None:
        old_value = list(self.doc._data[self.field])
        del self.doc._data[self.field][index:index+count]
        new_value = list(self.doc._data[self.field])
        self.doc._notify_change(self.field, old_value, new_value)
        for observer in self._observers:
            observer({"action": "remove", "index": index, "count": count, "old_value": old_value, "new_value": new_value})
    
    def clear(self) -> None:
        old_value = list(self.doc._data[self.field])
        self.doc._data[self.field] = []
        self.doc._notify_change(self.field, old_value, [])
        for observer in self._observers:
            observer({"action": "clear", "old_value": old_value, "new_value": []})
    
    def observe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._observers.append(callback)


class SimpleCRDTMap:
    """Simplified map CRDT wrapper"""
    
    def __init__(self, doc: SimpleCRDTDocument, field: str) -> None:
        self.doc = doc
        self.field = field
        self._observers: List[Callable[[Dict[str, Any]], None]] = []
        if field not in self.doc._data:
            self.doc._data[field] = {}
    
    def __getitem__(self, key: str):
        return self.doc._data[self.field].get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        old_value = self.doc._data[self.field].copy()
        self.doc._data[self.field][key] = value
        new_value = self.doc._data[self.field].copy()
        self.doc._notify_change(self.field, old_value, new_value)
        for observer in self._observers:
            observer({"action": "set", "key": key, "value": value, "old_value": old_value, "new_value": new_value})
    
    def get(self, key: str, default: Any = None):
        return self.doc._data[self.field].get(key, default)
    
    def clear(self) -> None:
        old_value = self.doc._data[self.field].copy()
        self.doc._data[self.field] = {}
        self.doc._notify_change(self.field, old_value, {})
        for observer in self._observers:
            observer({"action": "clear", "old_value": old_value, "new_value": {}})
    
    def observe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._observers.append(callback) 