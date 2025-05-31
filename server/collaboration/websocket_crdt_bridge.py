"""
WebSocket-CRDT Message Bridge for Phase 3 Real-time Collaborative UI

This module implements the bridge between WebSocket real-time events and existing
Phase 2.1 Memory Collaboration Engine CRDT components. It handles message format
transformation, operation routing, and performance optimization.

Integration Targets:
- MemoryCRDTManager: Document management and Redis integration
- MemoryFieldOperationsManager: Field-level operation execution
- Phase1Integration: Gateway aggregation and backward compatibility
- CollaborationWebSocketManager: Real-time WebSocket communication

Performance Targets:
- Message Transformation: <50ms per operation
- CRDT Operation Execution: <200ms end-to-end
- Real-time Broadcast: <500ms cross-client latency

Author: GraphMemory-IDE Team
Created: May 31, 2025
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import uuid

# Import existing CRDT components
from .memory_crdt import (
    MemoryCRDTManager, MemoryDocument, MemoryDocumentState,
    MemoryFieldType, MemoryChangeType, get_memory_crdt_manager
)
from .memory_operations import (
    MemoryFieldOperationsManager, FieldOperation, OperationType,
    OperationResult, ValidationResult, get_field_operations_manager
)
from .phase1_integration import (
    CollaborationIntegrationManager, CollaborationResponse,
    get_phase1_integration_manager
)
from .state import UserRole
from .auth import CollaborationPermission

# Configure logging
logger = logging.getLogger(__name__)


class WebSocketMessageType(Enum):
    """WebSocket message types for real-time collaboration"""
    # Client → Server
    EDIT_OPERATION = "edit_operation"
    CURSOR_UPDATE = "cursor_update"
    PRESENCE_UPDATE = "presence_update"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SYNC_REQUEST = "sync_request"
    
    # Server → Client
    OPERATION_APPLIED = "operation_applied"
    OPERATION_BROADCAST = "operation_broadcast"
    CURSOR_BROADCAST = "cursor_broadcast"
    PRESENCE_BROADCAST = "presence_broadcast"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    SYNC_STATE = "sync_state"
    ERROR = "error"


@dataclass
class WebSocketOperation:
    """Standardized WebSocket operation format"""
    operation_id: str
    user_id: str
    room_id: str
    memory_id: str
    tenant_id: str
    operation_type: str  # insert, delete, replace, format
    field_type: str     # title, content, tags, metadata
    position: int
    content: str
    length: int
    metadata: Dict[str, Any]
    timestamp: float


@dataclass
class CRDTBridgeResult:
    """Result from WebSocket-CRDT bridge operation"""
    success: bool
    operation_id: str
    crdt_result: Optional[OperationResult]
    websocket_response: Dict[str, Any]
    broadcast_data: Optional[Dict[str, Any]]
    processing_time_ms: float
    error_message: Optional[str] = None


class WebSocketCRDTBridge:
    """
    Bridge between WebSocket real-time events and CRDT operations
    
    Transforms WebSocket message formats to FieldOperation format and routes
    operations through existing Phase 2.1 collaboration engine components.
    """
    
    def __init__(self, integration_manager: CollaborationIntegrationManager):
        self.integration_manager = integration_manager
        self.crdt_manager: Optional[MemoryCRDTManager] = None
        self.operation_managers: Dict[str, MemoryFieldOperationsManager] = {}
        
        # Performance tracking
        self.transformation_times: List[float] = []
        self.operation_times: List[float] = []
        
        # Operation mapping
        self.websocket_to_crdt_type = {
            "insert": OperationType.INSERT,
            "delete": OperationType.DELETE,
            "replace": OperationType.REPLACE,
            "format": OperationType.FORMAT
        }
        
        self.websocket_to_field_type = {
            "title": MemoryFieldType.TITLE,
            "content": MemoryFieldType.CONTENT,
            "tags": MemoryFieldType.TAGS,
            "metadata": MemoryFieldType.METADATA
        }
        
        logger.info("WebSocketCRDTBridge initialized")
    
    async def initialize(self):
        """Initialize CRDT manager and dependencies"""
        try:
            self.crdt_manager = await get_memory_crdt_manager()
            logger.info("WebSocket-CRDT bridge initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket-CRDT bridge: {e}")
            raise
    
    async def process_websocket_operation(
        self, 
        ws_message: Dict[str, Any],
        user_id: str,
        room_id: str
    ) -> CRDTBridgeResult:
        """
        Process WebSocket operation through CRDT engine
        
        Main entry point for transforming WebSocket events into CRDT operations
        and executing them through existing collaboration components.
        """
        start_time = time.time()
        operation_id = str(uuid.uuid4())
        
        try:
            # Parse WebSocket message into standardized operation
            ws_operation = await self._parse_websocket_message(
                ws_message, user_id, room_id, operation_id
            )
            
            # Transform to CRDT operation format
            field_operation = await self._transform_to_crdt_operation(ws_operation)
            
            # Execute through CRDT components
            crdt_result = await self._execute_crdt_operation(
                ws_operation.memory_id, ws_operation.tenant_id, 
                field_operation, user_id
            )
            
            # Transform result back to WebSocket format
            websocket_response = await self._transform_crdt_result_to_websocket(
                crdt_result, ws_operation
            )
            
            # Prepare broadcast data
            broadcast_data = await self._prepare_broadcast_data(
                crdt_result, ws_operation
            ) if crdt_result.success else None
            
            # Record performance metrics
            processing_time = (time.time() - start_time) * 1000
            self.operation_times.append(processing_time)
            
            # Keep last 1000 measurements
            if len(self.operation_times) > 1000:
                self.operation_times = self.operation_times[-1000:]
            
            # Performance warning
            if processing_time > 200:  # Target <200ms for CRDT operations
                logger.warning(
                    f"CRDT operation {operation_id} took {processing_time:.2f}ms (>200ms target)"
                )
            
            return CRDTBridgeResult(
                success=crdt_result.success,
                operation_id=operation_id,
                crdt_result=crdt_result,
                websocket_response=websocket_response,
                broadcast_data=broadcast_data,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Error processing WebSocket operation {operation_id}: {e}")
            
            return CRDTBridgeResult(
                success=False,
                operation_id=operation_id,
                crdt_result=None,
                websocket_response={
                    "type": WebSocketMessageType.ERROR.value,
                    "data": {"error": str(e), "operation_id": operation_id},
                    "timestamp": time.time()
                },
                broadcast_data=None,
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    async def _parse_websocket_message(
        self,
        ws_message: Dict[str, Any],
        user_id: str,
        room_id: str,
        operation_id: str
    ) -> WebSocketOperation:
        """Parse and validate WebSocket message into standardized operation"""
        try:
            # Extract room info (format: tenant_id:memory_id)
            tenant_id, memory_id = room_id.split(":", 1)
            
            # Extract operation data
            data = ws_message.get("data", {})
            
            return WebSocketOperation(
                operation_id=operation_id,
                user_id=user_id,
                room_id=room_id,
                memory_id=memory_id,
                tenant_id=tenant_id,
                operation_type=data.get("operation_type", "insert"),
                field_type=data.get("field_type", "content"),
                position=data.get("position", 0),
                content=data.get("content", ""),
                length=data.get("length", len(data.get("content", ""))),
                metadata=data.get("metadata", {}),
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Error parsing WebSocket message: {e}")
            raise ValueError(f"Invalid WebSocket message format: {e}")
    
    async def _transform_to_crdt_operation(self, ws_op: WebSocketOperation) -> FieldOperation:
        """Transform WebSocket operation to CRDT FieldOperation format"""
        transform_start = time.time()
        
        try:
            # Map WebSocket types to CRDT types
            crdt_operation_type = self.websocket_to_crdt_type.get(
                ws_op.operation_type, OperationType.INSERT
            )
            crdt_field_type = self.websocket_to_field_type.get(
                ws_op.field_type, MemoryFieldType.CONTENT
            )
            
            # Create FieldOperation
            field_operation = FieldOperation(
                operation_id=ws_op.operation_id,
                user_id=ws_op.user_id,
                memory_id=ws_op.memory_id,
                field_type=crdt_field_type,
                operation_type=crdt_operation_type,
                position=ws_op.position,
                content=ws_op.content,
                length=ws_op.length,
                timestamp=datetime.fromtimestamp(ws_op.timestamp, tz=timezone.utc),
                metadata={
                    **ws_op.metadata,
                    "tenant_id": ws_op.tenant_id,
                    "room_id": ws_op.room_id,
                    "source": "websocket"
                }
            )
            
            # Record transformation time
            transform_time = (time.time() - transform_start) * 1000
            self.transformation_times.append(transform_time)
            
            if len(self.transformation_times) > 1000:
                self.transformation_times = self.transformation_times[-1000:]
            
            # Performance check
            if transform_time > 50:  # Target <50ms for transformations
                logger.warning(
                    f"Message transformation took {transform_time:.2f}ms (>50ms target)"
                )
            
            return field_operation
            
        except Exception as e:
            logger.error(f"Error transforming WebSocket operation to CRDT: {e}")
            raise
    
    async def _execute_crdt_operation(
        self,
        memory_id: str,
        tenant_id: str,
        field_operation: FieldOperation,
        user_id: str
    ) -> OperationResult:
        """Execute CRDT operation through existing collaboration components"""
        try:
            # Ensure CRDT manager is initialized
            if not self.crdt_manager:
                raise ValueError("CRDT manager not initialized")
            
            # Get or create memory document (use COLLABORATOR role for WebSocket operations)
            document = await self.crdt_manager.get_memory_document(
                memory_id, user_id, role=UserRole.COLLABORATOR
            )
            
            if not document:
                raise ValueError(f"Failed to get memory document {memory_id}")
            
            # Get field operations manager for this document
            if memory_id not in self.operation_managers:
                self.operation_managers[memory_id] = await get_field_operations_manager(document)
            
            operations_manager = self.operation_managers[memory_id]
            
            # Execute operation through field operations manager (use COLLABORATOR role)
            result = await operations_manager.execute_operation(
                field_type=field_operation.field_type,
                operation_type=field_operation.operation_type,
                user_id=user_id,
                role=UserRole.COLLABORATOR,
                position=field_operation.position,
                text=field_operation.content,
                content=field_operation.content,
                length=field_operation.length,
                tag=field_operation.content if field_operation.field_type == MemoryFieldType.TAGS else None,
                key=field_operation.metadata.get("key") if field_operation.field_type == MemoryFieldType.METADATA else None,
                value=field_operation.content if field_operation.field_type == MemoryFieldType.METADATA else None
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing CRDT operation: {e}")
            return OperationResult(
                success=False,
                operation=field_operation,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=str(e),
                transformed_operations=[]
            )
    
    async def _transform_crdt_result_to_websocket(
        self,
        crdt_result: OperationResult,
        ws_operation: WebSocketOperation
    ) -> Dict[str, Any]:
        """Transform CRDT operation result back to WebSocket message format"""
        return {
            "type": WebSocketMessageType.OPERATION_APPLIED.value if crdt_result.success 
                   else WebSocketMessageType.ERROR.value,
            "data": {
                "operation_id": ws_operation.operation_id,
                "success": crdt_result.success,
                "validation_result": crdt_result.validation_result.value if crdt_result.validation_result else None,
                "error_message": crdt_result.error_message,
                "memory_id": ws_operation.memory_id,
                "field_type": ws_operation.field_type,
                "operation_type": ws_operation.operation_type,
                "position": ws_operation.position,
                "content": ws_operation.content,
                "timestamp": ws_operation.timestamp,
                "transformed_operations_count": len(crdt_result.transformed_operations) if crdt_result.transformed_operations else 0
            },
            "timestamp": time.time()
        }
    
    async def _prepare_broadcast_data(
        self,
        crdt_result: OperationResult,
        ws_operation: WebSocketOperation
    ) -> Dict[str, Any]:
        """Prepare data for broadcasting to other clients in the room"""
        return {
            "type": WebSocketMessageType.OPERATION_BROADCAST.value,
            "data": {
                "operation_id": ws_operation.operation_id,
                "user_id": ws_operation.user_id,
                "memory_id": ws_operation.memory_id,
                "field_type": ws_operation.field_type,
                "operation_type": ws_operation.operation_type,
                "position": ws_operation.position,
                "content": ws_operation.content,
                "length": ws_operation.length,
                "timestamp": ws_operation.timestamp,
                "success": crdt_result.success,
                "transformed_operations": [
                    {
                        "operation_id": op.operation_id,
                        "field_type": op.field_type.value,
                        "operation_type": op.operation_type.value,
                        "position": op.position,
                        "content": op.content,
                        "timestamp": op.timestamp.isoformat()
                    }
                    for op in (crdt_result.transformed_operations or [])
                ]
            },
            "timestamp": time.time()
        }
    
    async def sync_memory_state(self, memory_id: str, user_id: str) -> Dict[str, Any]:
        """Get current memory state for WebSocket sync"""
        try:
            # Ensure CRDT manager is initialized
            if not self.crdt_manager:
                raise ValueError("CRDT manager not initialized")
            
            document = await self.crdt_manager.get_memory_document(memory_id, user_id, role=UserRole.COLLABORATOR)
            
            if not document:
                raise ValueError(f"Memory document {memory_id} not found")
            
            current_state = document.get_current_state()
            
            return {
                "type": WebSocketMessageType.SYNC_STATE.value,
                "data": {
                    "memory_id": memory_id,
                    "state": {
                        "title": current_state.title,
                        "content": current_state.content,
                        "tags": list(current_state.tags),
                        "metadata": current_state.metadata,
                        "version": current_state.version,
                        "last_modified": current_state.last_modified.isoformat(),
                        "last_modified_by": current_state.last_modified_by,
                        "collaborators": list(current_state.collaborators)
                    },
                    "timestamp": time.time()
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error syncing memory state for {memory_id}: {e}")
            return {
                "type": WebSocketMessageType.ERROR.value,
                "data": {
                    "error": f"Failed to sync memory state: {e}",
                    "memory_id": memory_id
                },
                "timestamp": time.time()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the bridge"""
        avg_transform_time = (
            sum(self.transformation_times) / len(self.transformation_times)
            if self.transformation_times else 0
        )
        avg_operation_time = (
            sum(self.operation_times) / len(self.operation_times)
            if self.operation_times else 0
        )
        
        return {
            "bridge_performance": {
                "average_transformation_time_ms": avg_transform_time,
                "average_operation_time_ms": avg_operation_time,
                "max_transformation_time_ms": max(self.transformation_times) if self.transformation_times else 0,
                "max_operation_time_ms": max(self.operation_times) if self.operation_times else 0,
                "total_operations_processed": len(self.operation_times),
                "target_compliance": {
                    "transformation_under_50ms": avg_transform_time < 50,
                    "operation_under_200ms": avg_operation_time < 200,
                    "end_to_end_under_500ms": (avg_transform_time + avg_operation_time) < 500
                }
            },
            "component_status": {
                "crdt_manager_initialized": self.crdt_manager is not None,
                "active_operation_managers": len(self.operation_managers),
                "integration_manager_available": self.integration_manager is not None
            }
        }
    
    async def cleanup_memory_resources(self, memory_id: str):
        """Cleanup resources for a specific memory"""
        if memory_id in self.operation_managers:
            del self.operation_managers[memory_id]
        
        if self.crdt_manager:
            await self.crdt_manager.close_memory_document(memory_id)


# Global bridge instance
_websocket_crdt_bridge: Optional[WebSocketCRDTBridge] = None


async def get_websocket_crdt_bridge() -> WebSocketCRDTBridge:
    """Get global WebSocket-CRDT bridge instance"""
    global _websocket_crdt_bridge
    
    if _websocket_crdt_bridge is None:
        integration_manager = await get_phase1_integration_manager()
        _websocket_crdt_bridge = WebSocketCRDTBridge(integration_manager)
        await _websocket_crdt_bridge.initialize()
    
    return _websocket_crdt_bridge


async def cleanup_websocket_crdt_bridge():
    """Cleanup global bridge instance"""
    global _websocket_crdt_bridge
    if _websocket_crdt_bridge is not None:
        # Cleanup operation managers
        for memory_id in list(_websocket_crdt_bridge.operation_managers.keys()):
            await _websocket_crdt_bridge.cleanup_memory_resources(memory_id)
        
        _websocket_crdt_bridge = None 