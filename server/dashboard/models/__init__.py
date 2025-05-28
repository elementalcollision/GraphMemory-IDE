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
    SSEResponse = None
    SSEEvent = None
    SSEEventType = None
    AnalyticsSSEResponse = None
    MemorySSEResponse = None
    GraphSSEResponse = None
    ErrorSSEResponse = None

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