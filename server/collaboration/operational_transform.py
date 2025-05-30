"""
Operational Transformation Engine

Provides Google Docs-style operational transformation for real-time
collaborative editing with conflict resolution and operation composition.
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from uuid import uuid4
import asyncio


logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Types of operations supported by the transformation engine"""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"
    REPLACE = "replace"
    MOVE = "move"
    ATTRIBUTE = "attribute"
    FORMAT = "format"


class OperationTarget(str, Enum):
    """Target types for operations"""
    TEXT = "text"
    OBJECT = "object"
    ARRAY = "array"
    ATTRIBUTE = "attribute"
    METADATA = "metadata"


@dataclass
class Operation:
    """
    Represents a single operation in the operational transformation system.
    
    Based on operational transform theory for real-time collaborative editing.
    Supports rich content editing including text, objects, and metadata.
    """
    
    operation_id: str
    operation_type: OperationType
    target: OperationTarget
    position: int
    length: int = 0
    content: Any = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = ""
    session_id: str = ""
    sequence_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary for serialization"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "target": self.target.value,
            "position": self.position,
            "length": self.length,
            "content": self.content,
            "attributes": self.attributes,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "sequence_number": self.sequence_number
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Operation":
        """Create operation from dictionary"""
        # Handle enum conversions
        operation_type = data["operation_type"]
        if isinstance(operation_type, str):
            operation_type = OperationType(operation_type)
            
        target = data["target"]
        if isinstance(target, str):
            target = OperationTarget(target)
            
        return cls(
            operation_id=data["operation_id"],
            operation_type=operation_type,
            target=target,
            position=data["position"],
            length=data.get("length", 0),
            content=data.get("content"),
            attributes=data.get("attributes", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            sequence_number=data.get("sequence_number", 0)
        )
    
    def copy(self) -> "Operation":
        """Create a copy of this operation"""
        return Operation(
            operation_id=self.operation_id,
            operation_type=self.operation_type,
            target=self.target,
            position=self.position,
            length=self.length,
            content=self.content,
            attributes=self.attributes.copy(),
            timestamp=self.timestamp,
            user_id=self.user_id,
            session_id=self.session_id,
            sequence_number=self.sequence_number
        )


@dataclass
class TransformResult:
    """Result of operational transformation"""
    transformed_op1: Operation
    transformed_op2: Operation
    conflict_detected: bool = False
    conflict_reason: Optional[str] = None
    resolution_strategy: Optional[str] = None


class OperationalTransform:
    """
    Operational Transformation engine for real-time collaborative editing.
    
    Implements the standard OT algorithm with extensions for rich content,
    conflict detection, and resolution strategies. Supports composition
    and decomposition of operations for efficient processing.
    """
    
    def __init__(self):
        self.operation_history: List[Operation] = []
        self.state_vector: Dict[str, int] = {}  # user_id -> latest sequence number
        self.composition_cache: Dict[str, Operation] = {}
        
    def transform(
        self,
        op1: Operation,
        op2: Operation,
        priority: str = "left"
    ) -> TransformResult:
        """
        Transform two concurrent operations against each other.
        
        Args:
            op1: First operation (local)
            op2: Second operation (remote)
            priority: Conflict resolution priority ("left" or "right")
            
        Returns:
            TransformResult: Transformed operations and conflict info
        """
        try:
            # Check if operations conflict
            conflict_detected = self._detect_conflict(op1, op2)
            
            if not conflict_detected:
                # No conflict, simple transformation
                return self._transform_no_conflict(op1, op2)
            
            # Handle conflict based on operation types
            if op1.target != op2.target:
                return self._transform_different_targets(op1, op2)
            
            return self._transform_with_conflict(op1, op2, priority)
            
        except Exception as e:
            logger.error(f"Error transforming operations: {e}")
            # Return operations unchanged in case of error
            return TransformResult(
                transformed_op1=op1.copy(),
                transformed_op2=op2.copy(),
                conflict_detected=True,
                conflict_reason=f"Transform error: {str(e)}"
            )
    
    def _detect_conflict(self, op1: Operation, op2: Operation) -> bool:
        """Detect if two operations conflict"""
        # Different targets don't conflict
        if op1.target != op2.target:
            return False
        
        # Different operation types may conflict
        if op1.operation_type == op2.operation_type:
            # Same operation type - check position overlap
            return self._positions_overlap(op1, op2)
        
        # Different operation types - check for conflicts
        conflicting_pairs = [
            (OperationType.INSERT, OperationType.DELETE),
            (OperationType.DELETE, OperationType.INSERT),
            (OperationType.REPLACE, OperationType.DELETE),
            (OperationType.REPLACE, OperationType.INSERT),
            (OperationType.MOVE, OperationType.DELETE),
            (OperationType.MOVE, OperationType.INSERT)
        ]
        
        return (op1.operation_type, op2.operation_type) in conflicting_pairs
    
    def _positions_overlap(self, op1: Operation, op2: Operation) -> bool:
        """Check if operation positions overlap"""
        if op1.target == OperationTarget.TEXT:
            # For text operations, check character position overlap
            op1_end = op1.position + op1.length
            op2_end = op2.position + op2.length
            
            return not (op1_end <= op2.position or op2_end <= op1.position)
        
        # For object operations, exact position match is overlap
        return op1.position == op2.position
    
    def _transform_no_conflict(self, op1: Operation, op2: Operation) -> TransformResult:
        """Transform operations with no conflict"""
        transformed_op1 = op1.copy()
        transformed_op2 = op2.copy()
        
        # Adjust positions based on operation types
        if op1.target == op2.target == OperationTarget.TEXT:
            transformed_op1, transformed_op2 = self._transform_text_positions(op1, op2)
        
        return TransformResult(
            transformed_op1=transformed_op1,
            transformed_op2=transformed_op2,
            conflict_detected=False
        )
    
    def _transform_text_positions(
        self,
        op1: Operation,
        op2: Operation
    ) -> Tuple[Operation, Operation]:
        """Transform text operation positions"""
        transformed_op1 = op1.copy()
        transformed_op2 = op2.copy()
        
        # Apply standard operational transform rules for text
        if op1.operation_type == OperationType.INSERT:
            if op2.position >= op1.position:
                transformed_op2.position += op1.length
        elif op1.operation_type == OperationType.DELETE:
            if op2.position >= op1.position + op1.length:
                transformed_op2.position -= op1.length
            elif op2.position >= op1.position:
                transformed_op2.position = op1.position
        
        if op2.operation_type == OperationType.INSERT:
            if op1.position > op2.position:
                transformed_op1.position += op2.length
        elif op2.operation_type == OperationType.DELETE:
            if op1.position >= op2.position + op2.length:
                transformed_op1.position -= op2.length
            elif op1.position >= op2.position:
                transformed_op1.position = op2.position
        
        return transformed_op1, transformed_op2
    
    def _transform_different_targets(
        self,
        op1: Operation,
        op2: Operation
    ) -> TransformResult:
        """Transform operations on different targets"""
        # Operations on different targets don't interfere
        return TransformResult(
            transformed_op1=op1.copy(),
            transformed_op2=op2.copy(),
            conflict_detected=False
        )
    
    def _transform_with_conflict(
        self,
        op1: Operation,
        op2: Operation,
        priority: str
    ) -> TransformResult:
        """Transform operations with conflict resolution"""
        transformed_op1 = op1.copy()
        transformed_op2 = op2.copy()
        
        conflict_reason = f"Operations conflict: {op1.operation_type} vs {op2.operation_type}"
        resolution_strategy = f"priority_{priority}"
        
        # Handle specific conflict cases
        if op1.operation_type == OperationType.INSERT and op2.operation_type == OperationType.DELETE:
            return self._resolve_insert_delete_conflict(op1, op2, priority)
        elif op1.operation_type == OperationType.DELETE and op2.operation_type == OperationType.INSERT:
            return self._resolve_delete_insert_conflict(op1, op2, priority)
        elif op1.operation_type == OperationType.REPLACE and op2.operation_type == OperationType.REPLACE:
            return self._resolve_replace_replace_conflict(op1, op2, priority)
        else:
            # Default conflict resolution: use priority
            if priority == "left":
                # Apply op1, then adjust op2
                transformed_op2 = self._adjust_operation_after(op2, op1)
            else:
                # Apply op2, then adjust op1
                transformed_op1 = self._adjust_operation_after(op1, op2)
        
        return TransformResult(
            transformed_op1=transformed_op1,
            transformed_op2=transformed_op2,
            conflict_detected=True,
            conflict_reason=conflict_reason,
            resolution_strategy=resolution_strategy
        )
    
    def _resolve_insert_delete_conflict(
        self,
        insert_op: Operation,
        delete_op: Operation,
        priority: str
    ) -> TransformResult:
        """Resolve INSERT vs DELETE conflict"""
        if priority == "left":
            # INSERT wins - adjust DELETE position
            transformed_delete = delete_op.copy()
            if delete_op.position >= insert_op.position:
                transformed_delete.position += insert_op.length
            
            return TransformResult(
                transformed_op1=insert_op.copy(),
                transformed_op2=transformed_delete,
                conflict_detected=True,
                conflict_reason="Insert-Delete conflict",
                resolution_strategy="insert_priority"
            )
        else:
            # DELETE wins - INSERT position may need adjustment
            transformed_insert = insert_op.copy()
            if insert_op.position >= delete_op.position:
                if insert_op.position >= delete_op.position + delete_op.length:
                    transformed_insert.position -= delete_op.length
                else:
                    transformed_insert.position = delete_op.position
            
            return TransformResult(
                transformed_op1=transformed_insert,
                transformed_op2=delete_op.copy(),
                conflict_detected=True,
                conflict_reason="Insert-Delete conflict",
                resolution_strategy="delete_priority"
            )
    
    def _resolve_delete_insert_conflict(
        self,
        delete_op: Operation,
        insert_op: Operation,
        priority: str
    ) -> TransformResult:
        """Resolve DELETE vs INSERT conflict"""
        # Delegate to insert_delete with swapped parameters and priority
        result = self._resolve_insert_delete_conflict(
            insert_op, delete_op, "right" if priority == "left" else "left"
        )
        
        return TransformResult(
            transformed_op1=result.transformed_op2,
            transformed_op2=result.transformed_op1,
            conflict_detected=result.conflict_detected,
            conflict_reason=result.conflict_reason,
            resolution_strategy=result.resolution_strategy
        )
    
    def _resolve_replace_replace_conflict(
        self,
        op1: Operation,
        op2: Operation,
        priority: str
    ) -> TransformResult:
        """Resolve REPLACE vs REPLACE conflict"""
        if priority == "left":
            # op1 wins, op2 becomes no-op or adjusted
            return TransformResult(
                transformed_op1=op1.copy(),
                transformed_op2=self._create_noop(op2),
                conflict_detected=True,
                conflict_reason="Replace-Replace conflict",
                resolution_strategy="left_replace_wins"
            )
        else:
            # op2 wins, op1 becomes no-op or adjusted
            return TransformResult(
                transformed_op1=self._create_noop(op1),
                transformed_op2=op2.copy(),
                conflict_detected=True,
                conflict_reason="Replace-Replace conflict",
                resolution_strategy="right_replace_wins"
            )
    
    def _adjust_operation_after(self, op: Operation, applied_op: Operation) -> Operation:
        """Adjust an operation after another operation has been applied"""
        adjusted = op.copy()
        
        if op.target == applied_op.target == OperationTarget.TEXT:
            if applied_op.operation_type == OperationType.INSERT:
                if op.position >= applied_op.position:
                    adjusted.position += applied_op.length
            elif applied_op.operation_type == OperationType.DELETE:
                if op.position >= applied_op.position + applied_op.length:
                    adjusted.position -= applied_op.length
                elif op.position >= applied_op.position:
                    adjusted.position = applied_op.position
        
        return adjusted
    
    def _create_noop(self, op: Operation) -> Operation:
        """Create a no-operation from an existing operation"""
        noop = op.copy()
        noop.operation_type = OperationType.RETAIN
        noop.content = None
        noop.length = 0
        return noop
    
    def compose_operations(self, ops: List[Operation]) -> Operation:
        """
        Compose multiple operations into a single operation.
        
        This is useful for optimizing operation sequences and
        reducing the number of operations that need to be applied.
        """
        if not ops:
            raise ValueError("Cannot compose empty operation list")
        
        if len(ops) == 1:
            return ops[0].copy()
        
        # Start with the first operation
        composed = ops[0].copy()
        composed.operation_id = str(uuid4())
        
        for op in ops[1:]:
            composed = self._compose_two_operations(composed, op)
        
        return composed
    
    def _compose_two_operations(self, op1: Operation, op2: Operation) -> Operation:
        """Compose two operations into one"""
        # This is a simplified composition - full implementation would
        # handle all operation type combinations
        
        if op1.target != op2.target:
            # Cannot compose operations on different targets
            return op1
        
        if op1.operation_type == op2.operation_type == OperationType.INSERT:
            # Combine adjacent inserts
            if op1.position + op1.length == op2.position:
                composed = op1.copy()
                composed.content = str(op1.content or "") + str(op2.content or "")
                composed.length += op2.length
                return composed
        
        elif op1.operation_type == op2.operation_type == OperationType.DELETE:
            # Combine adjacent deletes
            if op1.position == op2.position:
                composed = op1.copy()
                composed.length += op2.length
                return composed
        
        # Default: return the second operation (it overwrites the first)
        return op2.copy()
    
    def apply_operation(self, content: Any, operation: Operation) -> Any:
        """
        Apply an operation to content and return the result.
        
        This is a simplified implementation - full version would
        handle all content types and operation combinations.
        """
        if operation.target == OperationTarget.TEXT and isinstance(content, str):
            return self._apply_text_operation(content, operation)
        elif operation.target == OperationTarget.OBJECT and isinstance(content, dict):
            return self._apply_object_operation(content, operation)
        elif operation.target == OperationTarget.ARRAY and isinstance(content, list):
            return self._apply_array_operation(content, operation)
        
        return content
    
    def _apply_text_operation(self, text: str, operation: Operation) -> str:
        """Apply operation to text content"""
        if operation.operation_type == OperationType.INSERT:
            return (text[:operation.position] + 
                   str(operation.content or "") + 
                   text[operation.position:])
        elif operation.operation_type == OperationType.DELETE:
            return (text[:operation.position] + 
                   text[operation.position + operation.length:])
        elif operation.operation_type == OperationType.REPLACE:
            return (text[:operation.position] + 
                   str(operation.content or "") + 
                   text[operation.position + operation.length:])
        
        return text
    
    def _apply_object_operation(self, obj: dict, operation: Operation) -> dict:
        """Apply operation to object content"""
        result = obj.copy()
        
        if operation.operation_type == OperationType.INSERT:
            # Add new key-value pair
            if operation.attributes and "key" in operation.attributes:
                result[operation.attributes["key"]] = operation.content
        elif operation.operation_type == OperationType.DELETE:
            # Remove key
            if operation.attributes and "key" in operation.attributes:
                result.pop(operation.attributes["key"], None)
        elif operation.operation_type == OperationType.REPLACE:
            # Update existing key
            if operation.attributes and "key" in operation.attributes:
                result[operation.attributes["key"]] = operation.content
        
        return result
    
    def _apply_array_operation(self, arr: list, operation: Operation) -> list:
        """Apply operation to array content"""
        result = arr.copy()
        
        if operation.operation_type == OperationType.INSERT:
            result.insert(operation.position, operation.content)
        elif operation.operation_type == OperationType.DELETE:
            if 0 <= operation.position < len(result):
                del result[operation.position]
        elif operation.operation_type == OperationType.REPLACE:
            if 0 <= operation.position < len(result):
                result[operation.position] = operation.content
        
        return result
    
    def get_operation_history(self) -> List[Operation]:
        """Get the complete operation history"""
        return self.operation_history.copy()
    
    def add_to_history(self, operation: Operation) -> None:
        """Add an operation to the history"""
        self.operation_history.append(operation)
        
        # Update state vector
        if operation.user_id:
            self.state_vector[operation.user_id] = max(
                self.state_vector.get(operation.user_id, 0),
                operation.sequence_number
            )
    
    def can_apply_operation(self, operation: Operation) -> bool:
        """Check if an operation can be applied based on state vector"""
        if not operation.user_id:
            return True
        
        expected_sequence = self.state_vector.get(operation.user_id, 0) + 1
        return operation.sequence_number == expected_sequence 