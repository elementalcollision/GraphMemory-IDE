"""
Memory Field Operations - Phase 2.1 Memory Collaboration Engine

This module implements field-level operations for collaborative memory editing,
including rich text operations for memory content, title operations, tag management,
and metadata operations with permission validation and delta transformation.

Features:
- Rich text operations for memory content fields
- Title editing with concurrent user tracking
- Tag operations (add, remove, modify) with validation
- Metadata operations with timestamp and author tracking
- Permission validation for field-level access
- Delta transformation for conflict-free operations
- Integration with Memory CRDT Core for state management

Author: GraphMemory-IDE Team
Created: January 29, 2025
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum

from .memory_crdt import (
    MemoryDocument, 
    MemoryFieldType, 
    MemoryChangeType, 
    MemoryChange,
    verify_collaboration_permission
)
from .state import UserRole
from .auth import CollaborationPermission


# Configure logging
logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of field operations"""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"
    FORMAT = "format"
    REPLACE = "replace"


class ValidationResult(Enum):
    """Operation validation results"""
    VALID = "valid"
    INVALID_PERMISSION = "invalid_permission"
    INVALID_FORMAT = "invalid_format"
    INVALID_CONTENT = "invalid_content"
    RATE_LIMITED = "rate_limited"


@dataclass
class FieldOperation:
    """Represents a single field operation for collaborative editing"""
    operation_id: str
    user_id: str
    memory_id: str
    field_type: MemoryFieldType
    operation_type: OperationType
    position: int
    content: str
    length: int
    timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "operation_id": self.operation_id,
            "user_id": self.user_id,
            "memory_id": self.memory_id,
            "field_type": self.field_type.value,
            "operation_type": self.operation_type.value,
            "position": self.position,
            "content": self.content,
            "length": self.length,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldOperation":
        """Create from dictionary"""
        return cls(
            operation_id=data["operation_id"],
            user_id=data["user_id"],
            memory_id=data["memory_id"],
            field_type=MemoryFieldType(data["field_type"]),
            operation_type=OperationType(data["operation_type"]),
            position=data["position"],
            content=data["content"],
            length=data["length"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data["metadata"]
        )


@dataclass
class OperationResult:
    """Result of field operation execution"""
    success: bool
    operation: Optional[FieldOperation]
    validation_result: ValidationResult
    error_message: Optional[str]
    transformed_operations: List[FieldOperation]


class TitleOperations:
    """
    Operations for memory title field with concurrent editing support
    
    Provides text insertion, deletion, replacement operations for memory titles
    with user tracking and permission validation.
    """
    
    def __init__(self, document: MemoryDocument):
        self.document = document
        self.field_type = MemoryFieldType.TITLE
        self.max_title_length = 200
        self.rate_limit_operations = 10  # operations per minute
        self.user_operations: Dict[str, List[datetime]] = {}
    
    async def insert_text(self, user_id: str, role: UserRole, position: int, text: str) -> OperationResult:
        """Insert text at specified position in title"""
        try:
            # Validate permission
            if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_PERMISSION,
                    error_message="User lacks WRITE_MEMORY permission",
                    transformed_operations=[]
                )
            
            # Check rate limiting
            if not self._check_rate_limit(user_id):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.RATE_LIMITED,
                    error_message="Rate limit exceeded",
                    transformed_operations=[]
                )
            
            # Validate content
            current_title = str(self.document._doc.get_text("title"))
            if len(current_title) + len(text) > self.max_title_length:
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_CONTENT,
                    error_message=f"Title would exceed {self.max_title_length} characters",
                    transformed_operations=[]
                )
            
            # Create operation
            operation = FieldOperation(
                operation_id=str(uuid.uuid4()),
                user_id=user_id,
                memory_id=self.document.memory_id,
                field_type=self.field_type,
                operation_type=OperationType.INSERT,
                position=position,
                content=text,
                length=len(text),
                timestamp=datetime.now(timezone.utc),
                metadata={"role": role.value}
            )
            
            # Apply operation to document
            title_text = self.document._doc.get_text("title")
            title_text.insert(position, text)
            
            # Record operation
            self._record_operation(user_id)
            
            return OperationResult(
                success=True,
                operation=operation,
                validation_result=ValidationResult.VALID,
                error_message=None,
                transformed_operations=[operation]
            )
            
        except Exception as e:
            logger.error(f"Error inserting text in title: {e}")
            return OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )
    
    async def delete_text(self, user_id: str, role: UserRole, position: int, length: int) -> OperationResult:
        """Delete text at specified position in title"""
        try:
            # Validate permission
            if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_PERMISSION,
                    error_message="User lacks WRITE_MEMORY permission",
                    transformed_operations=[]
                )
            
            # Check rate limiting
            if not self._check_rate_limit(user_id):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.RATE_LIMITED,
                    error_message="Rate limit exceeded",
                    transformed_operations=[]
                )
            
            # Create operation
            operation = FieldOperation(
                operation_id=str(uuid.uuid4()),
                user_id=user_id,
                memory_id=self.document.memory_id,
                field_type=self.field_type,
                operation_type=OperationType.DELETE,
                position=position,
                content="",
                length=length,
                timestamp=datetime.now(timezone.utc),
                metadata={"role": role.value}
            )
            
            # Apply operation to document
            title_text = self.document._doc.get_text("title")
            # Note: Using clear and insert for delete operation as SimpleCRDTText doesn't have delete method
            current_text = str(title_text)
            new_text = current_text[:position] + current_text[position + length:]
            title_text.clear()
            title_text.insert(0, new_text)
            
            # Record operation
            self._record_operation(user_id)
            
            return OperationResult(
                success=True,
                operation=operation,
                validation_result=ValidationResult.VALID,
                error_message=None,
                transformed_operations=[operation]
            )
            
        except Exception as e:
            logger.error(f"Error deleting text in title: {e}")
            return OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )
    
    async def replace_title(self, user_id: str, role: UserRole, new_title: str) -> OperationResult:
        """Replace entire title with new content"""
        try:
            # Validate permission
            if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_PERMISSION,
                    error_message="User lacks WRITE_MEMORY permission",
                    transformed_operations=[]
                )
            
            # Validate content length
            if len(new_title) > self.max_title_length:
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_CONTENT,
                    error_message=f"Title exceeds {self.max_title_length} characters",
                    transformed_operations=[]
                )
            
            # Create operation
            operation = FieldOperation(
                operation_id=str(uuid.uuid4()),
                user_id=user_id,
                memory_id=self.document.memory_id,
                field_type=self.field_type,
                operation_type=OperationType.REPLACE,
                position=0,
                content=new_title,
                length=len(new_title),
                timestamp=datetime.now(timezone.utc),
                metadata={"role": role.value}
            )
            
            # Apply operation to document
            await self.document.update_title(new_title, user_id)
            
            return OperationResult(
                success=True,
                operation=operation,
                validation_result=ValidationResult.VALID,
                error_message=None,
                transformed_operations=[operation]
            )
            
        except Exception as e:
            logger.error(f"Error replacing title: {e}")
            return OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        
        if user_id not in self.user_operations:
            self.user_operations[user_id] = []
        
        # Remove old operations
        self.user_operations[user_id] = [
            op_time for op_time in self.user_operations[user_id]
            if op_time > window_start
        ]
        
        return len(self.user_operations[user_id]) < self.rate_limit_operations
    
    def _record_operation(self, user_id: str):
        """Record operation for rate limiting"""
        if user_id not in self.user_operations:
            self.user_operations[user_id] = []
        self.user_operations[user_id].append(datetime.now(timezone.utc))


class ContentOperations:
    """
    Rich text operations for memory content field
    
    Provides collaborative editing for memory content with formatting support,
    link insertion, code blocks, and structured content operations.
    """
    
    def __init__(self, document: MemoryDocument):
        self.document = document
        self.field_type = MemoryFieldType.CONTENT
        self.max_content_length = 10000
        self.supported_formats = {"bold", "italic", "underline", "code", "link"}
    
    async def insert_formatted_text(self, user_id: str, role: UserRole, position: int, 
                                   text: str, format_type: Optional[str] = None) -> OperationResult:
        """Insert formatted text at specified position"""
        try:
            # Validate permission
            if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_PERMISSION,
                    error_message="User lacks WRITE_MEMORY permission",
                    transformed_operations=[]
                )
            
            # Validate format
            if format_type and format_type not in self.supported_formats:
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_FORMAT,
                    error_message=f"Unsupported format: {format_type}",
                    transformed_operations=[]
                )
            
            # Create operation
            operation = FieldOperation(
                operation_id=str(uuid.uuid4()),
                user_id=user_id,
                memory_id=self.document.memory_id,
                field_type=self.field_type,
                operation_type=OperationType.INSERT,
                position=position,
                content=text,
                length=len(text),
                timestamp=datetime.now(timezone.utc),
                metadata={"format": format_type, "role": role.value}
            )
            
            # Apply operation
            content_text = self.document._doc.get_text("content")
            if format_type:
                formatted_text = self._apply_formatting(text, format_type)
                content_text.insert(position, formatted_text)
            else:
                content_text.insert(position, text)
            
            return OperationResult(
                success=True,
                operation=operation,
                validation_result=ValidationResult.VALID,
                error_message=None,
                transformed_operations=[operation]
            )
            
        except Exception as e:
            logger.error(f"Error inserting formatted text: {e}")
            return OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )
    
    def _apply_formatting(self, text: str, format_type: str) -> str:
        """Apply formatting to text"""
        if format_type == "bold":
            return f"**{text}**"
        elif format_type == "italic":
            return f"*{text}*"
        elif format_type == "underline":
            return f"_{text}_"
        elif format_type == "code":
            return f"`{text}`"
        return text


class TagOperations:
    """
    Tag management operations for memory collaboration
    
    Provides add, remove, modify operations for memory tags with validation,
    auto-completion suggestions, and collaborative conflict resolution.
    """
    
    def __init__(self, document: MemoryDocument):
        self.document = document
        self.field_type = MemoryFieldType.TAGS
        self.max_tags = 20
        self.max_tag_length = 50
    
    async def add_tag(self, user_id: str, role: UserRole, tag: str) -> OperationResult:
        """Add tag to memory"""
        try:
            # Validate permission
            if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_PERMISSION,
                    error_message="User lacks WRITE_MEMORY permission",
                    transformed_operations=[]
                )
            
            # Validate tag
            if len(tag) > self.max_tag_length:
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_CONTENT,
                    error_message=f"Tag exceeds {self.max_tag_length} characters",
                    transformed_operations=[]
                )
            
            # Check tag count
            current_tags = len(self.document._doc.get_array("tags"))
            if current_tags >= self.max_tags:
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_CONTENT,
                    error_message=f"Maximum {self.max_tags} tags allowed",
                    transformed_operations=[]
                )
            
            # Create operation
            operation = FieldOperation(
                operation_id=str(uuid.uuid4()),
                user_id=user_id,
                memory_id=self.document.memory_id,
                field_type=self.field_type,
                operation_type=OperationType.INSERT,
                position=current_tags,
                content=tag.strip().lower(),
                length=1,
                timestamp=datetime.now(timezone.utc),
                metadata={"role": role.value}
            )
            
            # Apply operation
            success = await self.document.add_tag(tag.strip().lower(), user_id)
            
            if success:
                return OperationResult(
                    success=True,
                    operation=operation,
                    validation_result=ValidationResult.VALID,
                    error_message=None,
                    transformed_operations=[operation]
                )
            else:
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_CONTENT,
                    error_message="Tag already exists",
                    transformed_operations=[]
                )
            
        except Exception as e:
            logger.error(f"Error adding tag: {e}")
            return OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )


class MetadataOperations:
    """
    Metadata operations for memory collaboration
    
    Handles timestamp updates, author tracking, version information,
    and custom metadata fields with type validation and conflict resolution.
    """
    
    def __init__(self, document: MemoryDocument):
        self.document = document
        self.field_type = MemoryFieldType.METADATA
        self.protected_fields = {"created_at", "memory_id", "version"}
        self.max_metadata_fields = 50
    
    async def update_metadata(self, user_id: str, role: UserRole, 
                            key: str, value: Any) -> OperationResult:
        """Update metadata field"""
        try:
            # Validate permission
            if not verify_collaboration_permission(role, CollaborationPermission.WRITE_MEMORY):
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_PERMISSION,
                    error_message="User lacks WRITE_MEMORY permission",
                    transformed_operations=[]
                )
            
            # Check protected fields
            if key in self.protected_fields:
                return OperationResult(
                    success=False,
                    operation=None,
                    validation_result=ValidationResult.INVALID_CONTENT,
                    error_message=f"Cannot modify protected field: {key}",
                    transformed_operations=[]
                )
            
            # Create operation
            operation = FieldOperation(
                operation_id=str(uuid.uuid4()),
                user_id=user_id,
                memory_id=self.document.memory_id,
                field_type=self.field_type,
                operation_type=OperationType.REPLACE,
                position=0,
                content=json.dumps({key: value}),
                length=1,
                timestamp=datetime.now(timezone.utc),
                metadata={"key": key, "role": role.value}
            )
            
            # Apply operation
            metadata_map = self.document._doc.get_map("metadata")
            metadata_map[key] = value
            metadata_map["last_modified"] = datetime.now(timezone.utc).isoformat()
            metadata_map["last_modified_by"] = user_id
            
            return OperationResult(
                success=True,
                operation=operation,
                validation_result=ValidationResult.VALID,
                error_message=None,
                transformed_operations=[operation]
            )
            
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            return OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )


class MemoryFieldOperationsManager:
    """
    Manager for all memory field operations with unified interface
    
    Coordinates operations across title, content, tags, and metadata fields
    with permission validation, operation transformation, and conflict resolution.
    """
    
    def __init__(self, document: MemoryDocument):
        self.document = document
        self.title_ops = TitleOperations(document)
        self.content_ops = ContentOperations(document)
        self.tag_ops = TagOperations(document)
        self.metadata_ops = MetadataOperations(document)
        
        # Operation history for conflict resolution
        self.operation_history: List[FieldOperation] = []
        self.max_history_size = 1000
    
    async def execute_operation(self, field_type: MemoryFieldType, 
                               operation_type: OperationType,
                               user_id: str, role: UserRole,
                               **kwargs) -> OperationResult:
        """Execute field operation with unified interface"""
        try:
            result = None
            
            if field_type == MemoryFieldType.TITLE:
                if operation_type == OperationType.INSERT:
                    result = await self.title_ops.insert_text(
                        user_id, role, kwargs.get("position", 0), kwargs.get("text", "")
                    )
                elif operation_type == OperationType.DELETE:
                    result = await self.title_ops.delete_text(
                        user_id, role, kwargs.get("position", 0), kwargs.get("length", 0)
                    )
                elif operation_type == OperationType.REPLACE:
                    result = await self.title_ops.replace_title(
                        user_id, role, kwargs.get("content", "")
                    )
            
            elif field_type == MemoryFieldType.CONTENT:
                if operation_type == OperationType.INSERT:
                    result = await self.content_ops.insert_formatted_text(
                        user_id, role, kwargs.get("position", 0), 
                        kwargs.get("text", ""), kwargs.get("format_type")
                    )
            
            elif field_type == MemoryFieldType.TAGS:
                if operation_type == OperationType.INSERT:
                    result = await self.tag_ops.add_tag(
                        user_id, role, kwargs.get("tag", "")
                    )
            
            elif field_type == MemoryFieldType.METADATA:
                if operation_type == OperationType.REPLACE:
                    result = await self.metadata_ops.update_metadata(
                        user_id, role, kwargs.get("key", ""), kwargs.get("value")
                    )
            
            if result and result.success and result.operation:
                self._add_to_history(result.operation)
            
            return result or OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message="Unsupported operation type",
                transformed_operations=[]
            )
            
        except Exception as e:
            logger.error(f"Error executing field operation: {e}")
            return OperationResult(
                success=False,
                operation=None,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )
    
    def _add_to_history(self, operation: FieldOperation):
        """Add operation to history for conflict resolution"""
        self.operation_history.append(operation)
        
        # Maintain history size limit
        if len(self.operation_history) > self.max_history_size:
            self.operation_history = self.operation_history[-self.max_history_size:]
    
    def get_operation_history(self, since: Optional[datetime] = None) -> List[FieldOperation]:
        """Get operation history since specified time"""
        if since:
            return [op for op in self.operation_history if op.timestamp > since]
        return self.operation_history.copy()


# Global operation manager cache
_operation_managers: Dict[str, MemoryFieldOperationsManager] = {}


async def get_field_operations_manager(document: MemoryDocument) -> MemoryFieldOperationsManager:
    """Get field operations manager for memory document"""
    if document.memory_id not in _operation_managers:
        _operation_managers[document.memory_id] = MemoryFieldOperationsManager(document)
    return _operation_managers[document.memory_id]


async def cleanup_field_operations_manager(memory_id: str):
    """Cleanup field operations manager"""
    if memory_id in _operation_managers:
        del _operation_managers[memory_id] 