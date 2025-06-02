"""
Error Handling Models

This module contains Pydantic models for structured error handling,
validation errors, and error reporting in the analytics dashboard.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from .validation_models import BaseValidationModel, TimestampStr


class ErrorSeverity(str, Enum):
    """Severity levels for errors and issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Categories of errors that can occur"""
    VALIDATION = "validation"
    ANALYTICS_ENGINE = "analytics_engine"
    MEMORY_SYSTEM = "memory_system"
    GRAPH_SYSTEM = "graph_system"
    SSE_STREAMING = "sse_streaming"
    DATA_PROCESSING = "data_processing"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ValidationErrorDetail(BaseValidationModel):
    """Detailed information about a validation error"""
    
    field_name: str = Field(description="Name of the field that failed validation")
    error_message: str = Field(description="Detailed error message")
    invalid_value: Optional[Any] = Field(default=None, description="The invalid value that caused the error")
    expected_type: Optional[str] = Field(default=None, description="Expected data type or format")
    constraint: Optional[str] = Field(default=None, description="Validation constraint that was violated")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "field_name": self.field_name,
            "error_message": self.error_message
        }
        
        if self.invalid_value is not None:
            result["invalid_value"] = str(self.invalid_value)
        
        if self.expected_type:
            result["expected_type"] = self.expected_type
        
        if self.constraint:
            result["constraint"] = self.constraint
        
        return result


class AnalyticsError(BaseValidationModel):
    """Comprehensive error model for analytics system errors"""
    
    error_id: str = Field(description="Unique error identifier")
    category: ErrorCategory = Field(description="Error category")
    severity: ErrorSeverity = Field(description="Error severity level")
    message: str = Field(description="Human-readable error message")
    details: Optional[str] = Field(default=None, description="Additional error details")
    
    # Context information
    component: Optional[str] = Field(default=None, description="Component where error occurred")
    operation: Optional[str] = Field(default=None, description="Operation that failed")
    user_id: Optional[str] = Field(default=None, description="User ID if applicable")
    session_id: Optional[str] = Field(default=None, description="Session ID if applicable")
    
    # Technical details
    exception_type: Optional[str] = Field(default=None, description="Type of exception")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace for debugging")
    error_code: Optional[str] = Field(default=None, description="Application-specific error code")
    
    # Validation-specific details
    validation_errors: List[ValidationErrorDetail] = Field(
        default_factory=list, 
        description="List of validation errors if applicable"
    )
    
    # Metadata
    timestamp: TimestampStr = Field(description="When the error occurred")
    resolved: bool = Field(default=False, description="Whether the error has been resolved")
    resolution_notes: Optional[str] = Field(default=None, description="Notes about error resolution")
    
    @classmethod
    def create_validation_error(
        cls,
        error_id: str,
        validation_errors: List[ValidationErrorDetail],
        component: Optional[str] = None,
        operation: Optional[str] = None
    ) -> "AnalyticsError":
        """Create a validation error"""
        return cls(
            error_id=error_id,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            message=f"Validation failed with {len(validation_errors)} error(s)",
            component=component,
            operation=operation,
            validation_errors=validation_errors,
            timestamp=datetime.now().isoformat()
        )
    
    @classmethod
    def create_analytics_engine_error(
        cls,
        error_id: str,
        message: str,
        details: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH
    ) -> "AnalyticsError":
        """Create an analytics engine error"""
        return cls(
            error_id=error_id,
            category=ErrorCategory.ANALYTICS_ENGINE,
            severity=severity,
            message=message,
            details=details,
            component="analytics_engine",
            timestamp=datetime.now().isoformat()
        )
    
    @classmethod
    def create_sse_error(
        cls,
        error_id: str,
        message: str,
        operation: Optional[str] = None,
        details: Optional[str] = None
    ) -> "AnalyticsError":
        """Create an SSE streaming error"""
        return cls(
            error_id=error_id,
            category=ErrorCategory.SSE_STREAMING,
            severity=ErrorSeverity.MEDIUM,
            message=message,
            details=details,
            component="sse_server",
            operation=operation,
            timestamp=datetime.now().isoformat()
        )
    
    @classmethod
    def from_exception(
        cls,
        error_id: str,
        exception: Exception,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        component: Optional[str] = None,
        operation: Optional[str] = None
    ) -> "AnalyticsError":
        """Create error from Python exception"""
        import traceback
        
        return cls(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(exception),
            exception_type=type(exception).__name__,
            stack_trace=traceback.format_exc(),
            component=component,
            operation=operation,
            timestamp=datetime.now().isoformat()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "error_id": self.error_id,
            "category": self.category.value if hasattr(self.category, 'value') else str(self.category),
            "severity": self.severity.value if hasattr(self.severity, 'value') else str(self.severity),
            "message": self.message,
            "timestamp": self.timestamp,
            "resolved": self.resolved
        }
        
        # Add optional fields if present
        optional_fields = [
            "details", "component", "operation", "user_id", "session_id",
            "exception_type", "error_code", "resolution_notes"
        ]
        
        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        # Add validation errors if present
        if self.validation_errors:
            result["validation_errors"] = [error.to_dict() for error in self.validation_errors]
        
        # Include stack trace only for debugging (not in production)
        if self.stack_trace and self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            result["stack_trace"] = self.stack_trace
        
        return result
    
    def is_critical(self) -> bool:
        """Check if this is a critical error"""
        return self.severity == ErrorSeverity.CRITICAL
    
    def is_validation_error(self) -> bool:
        """Check if this is a validation error"""
        return self.category == ErrorCategory.VALIDATION
    
    def get_summary(self) -> str:
        """Get a brief summary of the error"""
        severity_str = self.severity.value if hasattr(self.severity, 'value') else str(self.severity)
        category_str = self.category.value if hasattr(self.category, 'value') else str(self.category)
        summary = f"[{severity_str.upper()}] {category_str}: {self.message}"
        if self.component:
            summary = f"{self.component} - {summary}"
        return summary


# Error collection and reporting models
class ErrorReport(BaseValidationModel):
    """Collection of errors for reporting and analysis"""
    
    report_id: str = Field(description="Unique report identifier")
    errors: List[AnalyticsError] = Field(description="List of errors in this report")
    start_time: TimestampStr = Field(description="Start time for error collection")
    end_time: TimestampStr = Field(description="End time for error collection")
    total_errors: int = Field(description="Total number of errors")
    critical_errors: int = Field(description="Number of critical errors")
    high_errors: int = Field(description="Number of high severity errors")
    medium_errors: int = Field(description="Number of medium severity errors")
    low_errors: int = Field(description="Number of low severity errors")
    
    @classmethod
    def from_errors(
        cls,
        report_id: str,
        errors: List[AnalyticsError],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> "ErrorReport":
        """Create error report from list of errors"""
        if not start_time:
            start_time = datetime.now().isoformat()
        if not end_time:
            end_time = datetime.now().isoformat()
        
        # Count errors by severity
        severity_counts = {
            ErrorSeverity.CRITICAL: 0,
            ErrorSeverity.HIGH: 0,
            ErrorSeverity.MEDIUM: 0,
            ErrorSeverity.LOW: 0
        }
        
        for error in errors:
            severity_counts[error.severity] += 1
        
        return cls(
            report_id=report_id,
            errors=errors,
            start_time=start_time,
            end_time=end_time,
            total_errors=len(errors),
            critical_errors=severity_counts[ErrorSeverity.CRITICAL],
            high_errors=severity_counts[ErrorSeverity.HIGH],
            medium_errors=severity_counts[ErrorSeverity.MEDIUM],
            low_errors=severity_counts[ErrorSeverity.LOW]
        )
    
    def get_critical_errors(self) -> List[AnalyticsError]:
        """Get only critical errors"""
        return [error for error in self.errors if error.is_critical()]
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[AnalyticsError]:
        """Get errors by category"""
        return [error for error in self.errors if error.category == category]
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary"""
        return {
            "report_id": self.report_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_errors": self.total_errors,
            "severity_breakdown": {
                "critical": self.critical_errors,
                "high": self.high_errors,
                "medium": self.medium_errors,
                "low": self.low_errors
            },
            "category_breakdown": self._get_category_breakdown()
        }
    
    def _get_category_breakdown(self) -> Dict[str, int]:
        """Get breakdown of errors by category"""
        category_counts = {}
        for error in self.errors:
            category = error.category.value if hasattr(error.category, 'value') else str(error.category)
            category_counts[category] = category_counts.get(category, 0) + 1
        return category_counts


# Utility functions for error handling
def create_validation_error_detail(
    field_name: str,
    error_message: str,
    invalid_value: Any = None,
    expected_type: Optional[str] = None,
    constraint: Optional[str] = None
) -> ValidationErrorDetail:
    """Create a validation error detail"""
    return ValidationErrorDetail(
        field_name=field_name,
        error_message=error_message,
        invalid_value=invalid_value,
        expected_type=expected_type,
        constraint=constraint
    )


def generate_error_id() -> str:
    """Generate a unique error ID"""
    import uuid
    return f"ERR_{uuid.uuid4().hex[:8].upper()}"


# Error context manager for automatic error handling
class ErrorContext:
    """Context manager for automatic error handling and reporting"""
    
    def __init__(
        self,
        component: str,
        operation: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> None:
        self.component = component
        self.operation = operation
        self.category = category
        self.severity = severity
        self.error_id = generate_error_id()
    
    def __enter__(self) -> "ErrorContext":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            # An exception occurred, create an error
            error = AnalyticsError.from_exception(
                error_id=self.error_id,
                exception=exc_val,
                category=self.category,
                severity=self.severity,
                component=self.component,
                operation=self.operation
            )
            
            # Log the error (in a real implementation, this would go to a logging system)
            print(f"Error occurred: {error.get_summary()}")
            
            # Don't suppress the exception
            return False
        return False
    
    def create_error(self, message: str, details: Optional[str] = None) -> AnalyticsError:
        """Create an error within this context"""
        return AnalyticsError(
            error_id=self.error_id,
            category=self.category,
            severity=self.severity,
            message=message,
            details=details,
            component=self.component,
            operation=self.operation,
            timestamp=datetime.now().isoformat()
        ) 