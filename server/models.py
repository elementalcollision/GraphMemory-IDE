"""
Data Models for GraphMemory-IDE MCP Server

This module defines Pydantic models for all API data structures including
telemetry events, authentication, analytics requests, and integration models.
"""

from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    """Types of telemetry events"""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    ERROR = "error"
    PERFORMANCE = "performance"
    MEMORY_OPERATION = "memory_operation"
    GRAPH_CHANGE = "graph_change"
    ANALYTICS_REQUEST = "analytics_request"

class TelemetryEvent(BaseModel):
    """Telemetry event model for IDE plugin events"""
    event_type: EventType = Field(..., description="Type of telemetry event")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Invalid timestamp format. Use ISO 8601 format.')
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user_action",
                "timestamp": "2025-01-29T18:30:00Z",
                "user_id": "user123",
                "session_id": "session456",
                "data": {
                    "action": "create_entity",
                    "entity_type": "concept",
                    "duration_ms": 150
                }
            }
        }

class User(BaseModel):
    """User model for authentication"""
    username: str = Field(..., description="Unique username")
    email: Optional[str] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    disabled: bool = Field(False, description="Whether the user account is disabled")
    roles: List[str] = Field(default_factory=list, description="User roles")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "testuser",
                "email": "test@example.com",
                "full_name": "Test User",
                "disabled": False,
                "roles": ["user"]
            }
        }

class Token(BaseModel):
    """JWT token response model"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiration in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }

class TokenData(BaseModel):
    """JWT token data model"""
    username: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)

# Analytics Models

class AnalyticsQuery(BaseModel):
    """Analytics query request model"""
    query_type: str = Field(..., description="Type of analytics query")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    filters: Optional[Dict[str, Any]] = Field(None, description="Query filters")
    time_range: Optional[Dict[str, str]] = Field(None, description="Time range for query")
    limit: int = Field(100, description="Maximum number of results")
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate limit range"""
        if v < 1 or v > 10000:
            raise ValueError('limit must be between 1 and 10000')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "query_type": "entity_analytics",
                "parameters": {
                    "entity_type": "concept",
                    "aggregation": "count"
                },
                "time_range": {
                    "start": "2025-01-01T00:00:00Z",
                    "end": "2025-01-29T23:59:59Z"
                },
                "limit": 100
            }
        }

class AnalyticsResult(BaseModel):
    """Analytics query result model"""
    query_id: str = Field(..., description="Unique query identifier")
    query_type: str = Field(..., description="Type of query executed")
    timestamp: str = Field(..., description="Query execution timestamp")
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    result_count: int = Field(..., description="Number of results returned")
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(..., description="Query results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "query_id": "q_12345",
                "query_type": "entity_analytics",
                "timestamp": "2025-01-29T18:30:00Z",
                "execution_time_ms": 45.2,
                "result_count": 25,
                "data": [{"entity_id": "e1", "count": 10}],
                "metadata": {"cache_hit": False}
            }
        }

class ServiceStatus(BaseModel):
    """Service status model"""
    service_name: str = Field(..., description="Name of the service")
    status: str = Field(..., description="Service status (healthy, unhealthy, degraded)")
    version: Optional[str] = Field(None, description="Service version")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    last_health_check: str = Field(..., description="Last health check timestamp")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Service metrics")
    dependencies: List[str] = Field(default_factory=list, description="Service dependencies")
    
    class Config:
        schema_extra = {
            "example": {
                "service_name": "analytics_engine",
                "status": "healthy",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "last_health_check": "2025-01-29T18:30:00Z",
                "metrics": {
                    "requests_per_second": 25.3,
                    "average_response_time_ms": 120.5
                },
                "dependencies": ["kuzu_db", "redis"]
            }
        }

class KuzuQueryRequest(BaseModel):
    """Kuzu GraphDB query request model"""
    cypher_query: str = Field(..., description="Cypher query to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    read_only: bool = Field(True, description="Whether this is a read-only query")
    timeout_seconds: int = Field(30, description="Query timeout in seconds")
    return_format: str = Field("json", description="Result return format")
    
    @validator('cypher_query')
    def validate_cypher_query(cls, v):
        """Basic validation for Cypher query"""
        if not v or not v.strip():
            raise ValueError('Cypher query cannot be empty')
        return v.strip()
    
    @validator('timeout_seconds')
    def validate_timeout(cls, v):
        """Validate timeout range"""
        if v < 1 or v > 300:
            raise ValueError('timeout_seconds must be between 1 and 300')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "cypher_query": "MATCH (n:Entity) RETURN count(n) as entity_count",
                "parameters": {},
                "read_only": True,
                "timeout_seconds": 30,
                "return_format": "json"
            }
        }

class KuzuQueryResult(BaseModel):
    """Kuzu GraphDB query result model"""
    query_id: str = Field(..., description="Unique query identifier")
    cypher_query: str = Field(..., description="Executed Cypher query")
    execution_time_ms: float = Field(..., description="Query execution time")
    row_count: int = Field(..., description="Number of rows returned")
    columns: List[str] = Field(..., description="Column names")
    data: List[List[Any]] = Field(..., description="Query result data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "query_id": "kq_67890",
                "cypher_query": "MATCH (n:Entity) RETURN count(n)",
                "execution_time_ms": 12.3,
                "row_count": 1,
                "columns": ["count(n)"],
                "data": [[42]],
                "metadata": {"cache_used": False}
            }
        }

# Streaming Analytics Models

class StreamingEvent(BaseModel):
    """Streaming analytics event model"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of streaming event")
    timestamp: str = Field(..., description="Event timestamp")
    source: str = Field(..., description="Event source identifier")
    data: Dict[str, Any] = Field(..., description="Event data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")

class FeatureVector(BaseModel):
    """Feature vector model for analytics"""
    feature_name: str = Field(..., description="Name of the feature")
    vector_data: List[float] = Field(..., description="Feature vector data")
    timestamp: str = Field(..., description="Feature computation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Feature metadata")

class PatternDetection(BaseModel):
    """Pattern detection result model"""
    pattern_id: str = Field(..., description="Unique pattern identifier")
    pattern_type: str = Field(..., description="Type of detected pattern")
    confidence: float = Field(..., description="Pattern confidence score")
    timestamp: str = Field(..., description="Pattern detection timestamp")
    description: str = Field(..., description="Human-readable pattern description")
    data: Dict[str, Any] = Field(..., description="Pattern data")

# Integration Models

class ServiceRegistry(BaseModel):
    """Service registry entry model"""
    service_id: str = Field(..., description="Unique service identifier")
    service_name: str = Field(..., description="Service name")
    service_type: str = Field(..., description="Type of service")
    endpoint_url: str = Field(..., description="Service endpoint URL")
    health_check_url: Optional[str] = Field(None, description="Health check endpoint")
    version: str = Field(..., description="Service version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Service metadata")
    registered_at: str = Field(..., description="Registration timestamp")
    last_heartbeat: str = Field(..., description="Last heartbeat timestamp")

class APIGatewayRequest(BaseModel):
    """API Gateway request model"""
    service: str = Field(..., description="Target service name")
    operation: str = Field(..., description="Operation to perform")
    data: Dict[str, Any] = Field(default_factory=dict, description="Request data")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    timeout_seconds: int = Field(30, description="Request timeout")

class APIGatewayResponse(BaseModel):
    """API Gateway response model"""
    request_id: str = Field(..., description="Unique request identifier")
    service: str = Field(..., description="Service that handled the request")
    operation: str = Field(..., description="Operation performed")
    timestamp: str = Field(..., description="Response timestamp")
    execution_time_ms: float = Field(..., description="Total execution time")
    status: str = Field(..., description="Response status")
    data: Union[Dict[str, Any], List[Any]] = Field(..., description="Response data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

# Error Models

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "ANALYTICS_001",
                "error_message": "Failed to execute analytics query",
                "timestamp": "2025-01-29T18:30:00Z",
                "request_id": "req_12345",
                "details": {
                    "query_type": "entity_analytics",
                    "error_details": "Database connection timeout"
                }
            }
        }

# Health Check Models

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime")
    services: Dict[str, ServiceStatus] = Field(..., description="Individual service statuses")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="System metrics")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-29T18:30:00Z",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "services": {
                    "analytics_engine": {
                        "service_name": "analytics_engine",
                        "status": "healthy",
                        "last_health_check": "2025-01-29T18:30:00Z",
                        "metrics": {},
                        "dependencies": []
                    }
                },
                "system_metrics": {
                    "memory_usage_mb": 512.3,
                    "cpu_usage_percent": 25.5
                }
            }
        } 