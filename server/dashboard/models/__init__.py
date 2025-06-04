"""
Data Models and Validation Layer for Dashboard

This package contains Pydantic models for data validation and transformation
between the analytics engine and SSE streaming infrastructure.
"""

# Import validation models first (no dependencies)
from .validation_models import (
    PositiveFloat,
    PercentageFloat,
    TimestampStr,
    NonNegativeInt,
    MemorySize,
    ResponseTime
)

# Import error models (depends on validation models)
from .error_models import (
    ValidationErrorDetail,
    AnalyticsError,
    ErrorSeverity,
    ErrorCategory
)

# Import analytics models (depends on validation models)
from .analytics_models import (
    SystemMetricsData,
    MemoryInsightsData,
    GraphMetricsData,
    AnalyticsStatus,
    PerformanceMetrics
)

# Import SSE models (depends on analytics and validation models)
from typing import Optional, Any, Type

try:
    from .sse_models import (
        SSEResponse,
        SSEEvent,
        SSEEventType,
        AnalyticsSSEResponse,
        MemorySSEResponse,
        GraphSSEResponse,
        ErrorSSEResponse
    )
except ImportError:
    # SSE models may have issues, provide fallbacks
    SSEResponse: Optional[Type[Any]] = None
    SSEEvent: Optional[Type[Any]] = None
    SSEEventType: Optional[Type[Any]] = None
    AnalyticsSSEResponse: Optional[Type[Any]] = None
    MemorySSEResponse: Optional[Type[Any]] = None
    GraphSSEResponse: Optional[Type[Any]] = None
    ErrorSSEResponse: Optional[Type[Any]] = None

__all__ = [
    # Validation Models
    "PositiveFloat",
    "PercentageFloat",
    "TimestampStr",
    "NonNegativeInt",
    "MemorySize",
    "ResponseTime",
    
    # Error Models
    "ValidationErrorDetail",
    "AnalyticsError",
    "ErrorSeverity",
    "ErrorCategory",
    
    # Analytics Models
    "SystemMetricsData",
    "MemoryInsightsData", 
    "GraphMetricsData",
    "AnalyticsStatus",
    "PerformanceMetrics",
    
    # SSE Models (may be None if import failed)
    "SSEResponse",
    "SSEEvent", 
    "SSEEventType",
    "AnalyticsSSEResponse",
    "MemorySSEResponse",
    "GraphSSEResponse",
    "ErrorSSEResponse"
] 