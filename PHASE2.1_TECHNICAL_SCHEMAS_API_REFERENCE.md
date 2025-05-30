# Phase 2.1 Technical Schemas and API Reference

**Date**: January 29, 2025  
**Version**: 1.0.0  
**Status**: Production Ready  
**Components**: 6/6 Complete

## **API Endpoint Reference**

### **1. Unified Collaboration API**

#### **POST /api/v1/memory/{memory_id}/collaborate**
**Research Basis**: API Gateway Aggregation (22% performance improvement)

```yaml
# Request Schema
CollaborationRequest:
  type: object
  required: [operation, user_id]
  properties:
    operation:
      $ref: '#/components/schemas/CollaborationOperation'
    user_id:
      type: string
      format: uuid
    options:
      type: object
      properties:
        force_sync: { type: boolean, default: false }
        conflict_strategy: { type: string, enum: [merge, overwrite, manual] }
        performance_mode: { type: string, enum: [fast, balanced, consistent] }

# Response Schema
CollaborationResponse:
  type: object
  properties:
    success: { type: boolean }
    data:
      type: object
      properties:
        collaboration_results:
          type: object
          additionalProperties: true
        unified_status: { type: string }
        components_processed: 
          type: array
          items: { type: string }
    components_used: 
      type: array
      items: { type: string }
    performance_metrics:
      $ref: '#/components/schemas/PerformanceMetrics'
    timestamp: { type: string, format: date-time }

# Example Request
{
  "operation": {
    "type": "memory_update",
    "data": {
      "field": "content.description",
      "action": "insert",
      "position": 45,
      "content": "Enhanced AI capabilities",
      "formatting": { "bold": true }
    },
    "collaboration_enabled": true
  },
  "user_id": "user_123",
  "options": {
    "conflict_strategy": "merge",
    "performance_mode": "balanced"
  }
}

# Example Response
{
  "success": true,
  "data": {
    "collaboration_results": {
      "memory_crdt": { "status": "synced", "version": 15 },
      "field_operations": { "status": "applied", "operation_id": "op_456" },
      "conflict_resolution": { "status": "no_conflicts" }
    },
    "unified_status": "success",
    "components_processed": ["memory_crdt", "field_operations", "vector_consistency"]
  },
  "components_used": ["memory_crdt", "field_operations", "vector_consistency"],
  "performance_metrics": {
    "total_time_ms": 78,
    "components_count": 3,
    "aggregation_efficiency": 1.0
  },
  "timestamp": "2025-01-29T12:41:19Z"
}
```

### **2. Memory CRDT API**

#### **GET /api/v1/memory/{memory_id}/crdt/state**
**Purpose**: Retrieve current CRDT state for memory

```yaml
# Response Schema
CRDTStateResponse:
  type: object
  properties:
    memory_id: { type: string, format: uuid }
    version_vector:
      type: object
      additionalProperties: { type: integer }
      example: { "user_1": 15, "user_2": 8, "user_3": 22 }
    content_state:
      type: object
      properties:
        title:
          $ref: '#/components/schemas/CRDTString'
        description:
          $ref: '#/components/schemas/CRDTString'
        tags:
          $ref: '#/components/schemas/CRDTSet'
        metadata:
          $ref: '#/components/schemas/CRDTMap'
    conflict_status:
      type: object
      properties:
        has_conflicts: { type: boolean }
        conflict_count: { type: integer }
        last_resolution: { type: string, format: date-time }
    sync_metadata:
      type: object
      properties:
        last_sync: { type: string, format: date-time }
        sync_source: { type: string }
        pending_operations: { type: integer }
```

#### **POST /api/v1/memory/{memory_id}/crdt/operation**
**Purpose**: Apply CRDT operation to memory state

```yaml
# Request Schema
CRDTOperationRequest:
  type: object
  required: [operation, user_id]
  properties:
    operation:
      $ref: '#/components/schemas/CRDTOperation'
    user_id: { type: string, format: uuid }
    lamport_clock: { type: integer }
    vector_clock:
      type: object
      additionalProperties: { type: integer }

CRDTOperation:
  type: object
  discriminator:
    propertyName: type
  required: [type, target_field]
  properties:
    type: { type: string, enum: [insert, delete, update, merge] }
    target_field: { type: string }
    operation_data: { type: object }
    user_context:
      type: object
      properties:
        user_id: { type: string }
        session_id: { type: string }
        timestamp: { type: string, format: date-time }
```

### **3. Field Operations API**

#### **POST /api/v1/memory/{memory_id}/field/{field_path}/operation**
**Purpose**: Rich text operations on specific memory fields

```yaml
# Request Schema
FieldOperationRequest:
  type: object
  required: [operation_type, operation_data, user_id]
  properties:
    operation_type: { type: string, enum: [insert, delete, format, replace, validate] }
    operation_data:
      oneOf:
        - $ref: '#/components/schemas/InsertOperation'
        - $ref: '#/components/schemas/DeleteOperation'
        - $ref: '#/components/schemas/FormatOperation'
        - $ref: '#/components/schemas/ReplaceOperation'
    user_id: { type: string, format: uuid }
    validation_rules:
      type: array
      items:
        $ref: '#/components/schemas/ValidationRule'
    transformation_context:
      $ref: '#/components/schemas/TransformationContext'

# Rich Text Operation Schemas
InsertOperation:
  type: object
  required: [position, content]
  properties:
    position: { type: integer, minimum: 0 }
    content: { type: string }
    formatting:
      type: object
      properties:
        bold: { type: boolean }
        italic: { type: boolean }
        underline: { type: boolean }
        strikethrough: { type: boolean }
        color: { type: string, pattern: '^#[0-9A-Fa-f]{6}$' }
        background_color: { type: string, pattern: '^#[0-9A-Fa-f]{6}$' }
        font_size: { type: integer, minimum: 8, maximum: 72 }
        link: { type: string, format: uri }
    metadata:
      type: object
      properties:
        source: { type: string }
        confidence: { type: number, minimum: 0, maximum: 1 }
        suggestions: { type: array, items: { type: string } }

DeleteOperation:
  type: object
  required: [start_position, length]
  properties:
    start_position: { type: integer, minimum: 0 }
    length: { type: integer, minimum: 1 }
    preserve_formatting: { type: boolean, default: false }

FormatOperation:
  type: object
  required: [start_position, end_position, formatting]
  properties:
    start_position: { type: integer, minimum: 0 }
    end_position: { type: integer, minimum: 0 }
    formatting:
      type: object
      properties:
        action: { type: string, enum: [apply, remove, toggle] }
        attributes:
          type: object
          properties:
            bold: { type: boolean }
            italic: { type: boolean }
            link: { type: string, format: uri }

ValidationRule:
  type: object
  required: [type, constraint]
  properties:
    type: { type: string, enum: [length, format, content, pattern] }
    constraint: { type: string }
    error_message: { type: string }
    severity: { type: string, enum: [error, warning, info] }
```

### **4. Relationship OT API**

#### **POST /api/v1/memory/{memory_id}/relationships/operation**
**Purpose**: Operational transformation for memory relationships

```yaml
# Request Schema
RelationshipOperationRequest:
  type: object
  required: [operation, source_memory_id, target_memory_id, user_id]
  properties:
    operation: { type: string, enum: [create, update, delete, strengthen, weaken] }
    relationship_type: { type: string, enum: [connects, references, contains, derives_from, similar_to] }
    source_memory_id: { type: string, format: uuid }
    target_memory_id: { type: string, format: uuid }
    user_id: { type: string, format: uuid }
    relationship_data:
      type: object
      properties:
        strength: { type: number, minimum: 0, maximum: 1 }
        bidirectional: { type: boolean, default: true }
        metadata:
          type: object
          properties:
            description: { type: string }
            tags: { type: array, items: { type: string } }
            confidence: { type: number, minimum: 0, maximum: 1 }
    transformation_context:
      $ref: '#/components/schemas/RelationshipTransformationContext'

RelationshipTransformationContext:
  type: object
  properties:
    user_intent: { type: string }
    context_awareness:
      type: object
      properties:
        semantic_similarity: { type: number, minimum: 0, maximum: 1 }
        temporal_relevance: { type: number, minimum: 0, maximum: 1 }
        user_history:
          type: array
          items:
            type: object
            properties:
              action: { type: string }
              timestamp: { type: string, format: date-time }
              memory_id: { type: string, format: uuid }
    graph_consistency:
      type: object
      properties:
        cycle_detection: { type: boolean, default: true }
        path_validation: { type: boolean, default: true }
        constraint_checking: { type: boolean, default: true }
        max_path_length: { type: integer, minimum: 1, maximum: 10 }

# Response Schema
RelationshipOperationResponse:
  type: object
  properties:
    success: { type: boolean }
    operation_id: { type: string, format: uuid }
    relationship_state:
      type: object
      properties:
        id: { type: string, format: uuid }
        type: { type: string }
        strength: { type: number }
        status: { type: string, enum: [active, pending, conflict, resolved] }
    graph_impact:
      type: object
      properties:
        cycles_created: { type: integer }
        paths_affected: { type: integer }
        constraint_violations: { type: array, items: { type: string } }
    transformation_result:
      type: object
      properties:
        conflicts_detected: { type: integer }
        resolution_strategy: { type: string }
        alternative_suggestions: { type: array, items: { type: string } }
```

### **5. Vector Consistency API**

#### **GET /api/v1/memory/{memory_id}/vector/consistency**
**Purpose**: Check vector consistency state

```yaml
# Response Schema
VectorConsistencyResponse:
  type: object
  properties:
    memory_id: { type: string, format: uuid }
    consistency_state:
      type: object
      properties:
        status: { type: string, enum: [consistent, inconsistent, syncing, conflict] }
        last_sync: { type: string, format: date-time }
        sync_version: { type: integer }
        consistency_score: { type: number, minimum: 0, maximum: 1 }
    vector_state:
      $ref: '#/components/schemas/VectorState'
    stakeholder_analysis:
      type: object
      properties:
        total_stakeholders: { type: integer }
        consensus_level: { type: number, minimum: 0, maximum: 1 }
        conflicting_vectors: { type: integer }
        resolution_strategy: { type: string }
    performance_metrics:
      type: object
      properties:
        sync_latency_ms: { type: number }
        embedding_generation_time_ms: { type: number }
        consistency_check_time_ms: { type: number }

VectorState:
  type: object
  properties:
    primary_embedding:
      type: array
      items: { type: number }
      minItems: 1536
      maxItems: 1536
    content_hash: { type: string }
    embedding_model: { type: string, enum: [text-embedding-3-large, text-embedding-3-small] }
    generation_timestamp: { type: string, format: date-time }
    consistency_checksum: { type: string }
    semantic_fingerprint: { type: string }
```

#### **POST /api/v1/memory/{memory_id}/vector/sync**
**Purpose**: Synchronize vector embeddings across stakeholders

```yaml
# Request Schema
VectorSyncRequest:
  type: object
  required: [user_id, sync_strategy]
  properties:
    user_id: { type: string, format: uuid }
    sync_strategy: { type: string, enum: [immediate, batch, scheduled] }
    consistency_requirements:
      type: object
      properties:
        min_consensus: { type: number, minimum: 0.5, maximum: 1.0 }
        max_staleness_ms: { type: integer, minimum: 100 }
        conflict_resolution: { type: string, enum: [weighted_average, latest_wins, manual] }
    performance_options:
      type: object
      properties:
        priority: { type: string, enum: [high, normal, low] }
        timeout_ms: { type: integer, minimum: 1000, maximum: 30000 }
        enable_caching: { type: boolean, default: true }
```

### **6. Conflict Resolution API**

#### **GET /api/v1/memory/{memory_id}/conflicts**
**Purpose**: Retrieve current conflicts across all components

```yaml
# Response Schema
ConflictStatusResponse:
  type: object
  properties:
    memory_id: { type: string, format: uuid }
    total_conflicts: { type: integer }
    conflicts_by_component:
      type: object
      properties:
        memory_crdt: { type: integer }
        field_operations: { type: integer }
        relationship_ot: { type: integer }
        vector_consistency: { type: integer }
    active_conflicts:
      type: array
      items:
        $ref: '#/components/schemas/ConflictDetails'
    resolution_history:
      type: array
      items:
        $ref: '#/components/schemas/ConflictResolution'

ConflictDetails:
  type: object
  properties:
    conflict_id: { type: string, format: uuid }
    component: { type: string }
    type: { type: string }
    severity: { type: string, enum: [low, medium, high, critical] }
    affected_users:
      type: array
      items: { type: string, format: uuid }
    conflict_data:
      type: object
      properties:
        description: { type: string }
        competing_values: { type: array }
        context: { type: object }
    suggested_resolutions:
      type: array
      items:
        type: object
        properties:
          strategy: { type: string }
          confidence: { type: number }
          impact: { type: string }
    created_at: { type: string, format: date-time }
    updated_at: { type: string, format: date-time }
```

#### **POST /api/v1/memory/{memory_id}/conflicts/{conflict_id}/resolve**
**Purpose**: Apply resolution to specific conflict

```yaml
# Request Schema
ConflictResolutionRequest:
  type: object
  required: [resolution_strategy, user_id]
  properties:
    resolution_strategy: { type: string, enum: [merge, overwrite, manual, ai_assisted] }
    user_id: { type: string, format: uuid }
    resolution_data:
      type: object
      properties:
        selected_value: { type: object }
        merge_rules: { type: object }
        manual_resolution: { type: object }
    apply_to_similar: { type: boolean, default: false }
    create_rule: { type: boolean, default: false }
```

## **Data Schemas Reference**

### **Core Data Types**

```yaml
# CRDT String Schema
CRDTString:
  type: object
  properties:
    value: { type: string }
    operations:
      type: array
      items:
        type: object
        properties:
          type: { type: string, enum: [insert, delete] }
          position: { type: integer }
          content: { type: string }
          user_id: { type: string }
          timestamp: { type: string, format: date-time }
          lamport_clock: { type: integer }
          vector_clock: { type: object }

# CRDT Set Schema
CRDTSet:
  type: object
  properties:
    elements:
      type: array
      items:
        type: object
        properties:
          value: { type: string }
          added_by: { type: string }
          added_at: { type: string, format: date-time }
          removed_by: { type: string, nullable: true }
          removed_at: { type: string, format: date-time, nullable: true }
          lamport_clock: { type: integer }

# CRDT Map Schema
CRDTMap:
  type: object
  properties:
    entries:
      type: object
      additionalProperties:
        type: object
        properties:
          value: { type: object }
          last_updated_by: { type: string }
          last_updated_at: { type: string, format: date-time }
          version: { type: integer }
          conflicts:
            type: array
            items:
              type: object
              properties:
                value: { type: object }
                user_id: { type: string }
                timestamp: { type: string, format: date-time }
```

### **Performance Metrics Schema**

```yaml
PerformanceMetrics:
  type: object
  properties:
    total_time_ms: { type: number }
    components_count: { type: integer }
    aggregation_efficiency: { type: number, minimum: 0, maximum: 1 }
    cache_hit_rate: { type: number, minimum: 0, maximum: 1 }
    database_query_time_ms: { type: number }
    network_latency_ms: { type: number }
    memory_usage_mb: { type: number }
    cpu_utilization: { type: number, minimum: 0, maximum: 1 }
    concurrent_operations: { type: integer }
    error_rate: { type: number, minimum: 0, maximum: 1 }
```

## **Integration Patterns**

### **1. Backward Compatibility Pattern**

```yaml
# Legacy API Translation
LegacyAPITranslation:
  type: object
  properties:
    original_endpoint: { type: string }
    original_data: { type: object }
    translated_operation:
      $ref: '#/components/schemas/CollaborationOperation'
    compatibility_mode: { type: string, enum: [full, partial, fallback] }
    translation_metadata:
      type: object
      properties:
        translation_time_ms: { type: number }
        compatibility_score: { type: number }
        warnings: { type: array, items: { type: string } }

# Example Translation
# Legacy: PUT /api/v1/memory/123 { "title": "New Title" }
# Becomes: POST /api/v1/memory/123/collaborate
{
  "operation": {
    "type": "memory_update",
    "data": {
      "field": "content.title",
      "action": "replace",
      "content": "New Title"
    },
    "collaboration_enabled": true
  },
  "user_id": "user_123",
  "options": {
    "conflict_strategy": "merge"
  }
}
```

### **2. Feature Flag Pattern**

```yaml
# Feature Flag Configuration
FeatureFlagConfig:
  type: object
  properties:
    feature_name: { type: string }
    enabled: { type: boolean }
    rollout_percentage: { type: integer, minimum: 0, maximum: 100 }
    target_users:
      type: array
      items: { type: string, format: uuid }
    conditions:
      type: object
      properties:
        user_segments: { type: array, items: { type: string } }
        geo_regions: { type: array, items: { type: string } }
        plan_types: { type: array, items: { type: string } }
    health_checks:
      type: object
      properties:
        error_rate_threshold: { type: number }
        latency_threshold_ms: { type: number }
        user_satisfaction_threshold: { type: number }

# Usage Example
{
  "feature_name": "memory_collaboration",
  "enabled": true,
  "rollout_percentage": 25,
  "conditions": {
    "plan_types": ["pro", "enterprise"]
  },
  "health_checks": {
    "error_rate_threshold": 0.01,
    "latency_threshold_ms": 100
  }
}
```

### **3. Circuit Breaker Pattern**

```yaml
# Circuit Breaker State
CircuitBreakerState:
  type: object
  properties:
    component: { type: string }
    state: { type: string, enum: [closed, open, half_open] }
    failure_count: { type: integer }
    failure_threshold: { type: integer }
    success_threshold: { type: integer }
    timeout_duration_ms: { type: integer }
    last_failure: { type: string, format: date-time }
    last_success: { type: string, format: date-time }
    health_metrics:
      type: object
      properties:
        success_rate: { type: number }
        average_response_time: { type: number }
        recent_errors: { type: array, items: { type: string } }
```

## **Error Handling Schemas**

### **Standard Error Response**

```yaml
ErrorResponse:
  type: object
  properties:
    error:
      type: object
      properties:
        code: { type: string }
        message: { type: string }
        details: { type: string }
        component: { type: string }
        timestamp: { type: string, format: date-time }
        trace_id: { type: string }
        suggestions:
          type: array
          items: { type: string }
    context:
      type: object
      properties:
        request_id: { type: string }
        user_id: { type: string }
        memory_id: { type: string }
        operation: { type: string }
    recovery:
      type: object
      properties:
        retry_after_ms: { type: integer }
        alternative_endpoints: { type: array, items: { type: string } }
        rollback_available: { type: boolean }
```

### **Common Error Codes**

| Code | Description | Recovery Strategy |
|------|-------------|-------------------|
| COLLAB_001 | Memory CRDT sync failure | Retry with exponential backoff |
| COLLAB_002 | Field operation validation error | Check field constraints |
| COLLAB_003 | Relationship OT conflict | Use manual resolution |
| COLLAB_004 | Vector consistency timeout | Reduce consistency requirements |
| COLLAB_005 | Cross-component conflict | Apply conflict resolution |
| COLLAB_006 | Integration gateway timeout | Use fallback endpoints |
| COLLAB_007 | Performance threshold exceeded | Enable performance mode |
| COLLAB_008 | Feature flag disabled | Check feature availability |

## **WebSocket Real-time API (Phase 3 Ready)**

### **Connection Schema**

```yaml
# WebSocket Connection
WebSocketConnection:
  type: object
  properties:
    connection_id: { type: string, format: uuid }
    user_id: { type: string, format: uuid }
    memory_id: { type: string, format: uuid }
    subscriptions:
      type: array
      items:
        type: string
        enum: [crdt_updates, field_operations, relationship_changes, vector_sync, conflicts]
    connection_metadata:
      type: object
      properties:
        client_type: { type: string }
        protocol_version: { type: string }
        capabilities: { type: array, items: { type: string } }

# Real-time Message Schema
RealtimeMessage:
  type: object
  properties:
    message_id: { type: string, format: uuid }
    type: { type: string }
    component: { type: string }
    data: { type: object }
    timestamp: { type: string, format: date-time }
    user_id: { type: string, format: uuid }
    memory_id: { type: string, format: uuid }
```

## **Security Schemas**

### **Authentication & Authorization**

```yaml
# User Context
UserContext:
  type: object
  properties:
    user_id: { type: string, format: uuid }
    session_id: { type: string, format: uuid }
    permissions:
      type: array
      items:
        type: string
        enum: [read, write, collaborate, admin]
    collaboration_role:
      type: string
      enum: [viewer, editor, collaborator, owner]
    rate_limits:
      type: object
      properties:
        requests_per_minute: { type: integer }
        operations_per_hour: { type: integer }
        concurrent_connections: { type: integer }

# Security Context
SecurityContext:
  type: object
  properties:
    ip_address: { type: string }
    user_agent: { type: string }
    geo_location: { type: string }
    risk_score: { type: number, minimum: 0, maximum: 1 }
    authentication_method: { type: string }
    multi_factor_verified: { type: boolean }
```

---

This comprehensive technical documentation provides complete schemas, API references, and integration patterns for the entire Phase 2.1 Memory Collaboration Engine. The APIs are production-ready with comprehensive error handling, performance optimization, and extensibility for future enhancements. 