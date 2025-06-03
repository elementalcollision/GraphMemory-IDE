"""
Custom Validation Models and Field Types

This module provides custom Pydantic field types and validators optimized
for analytics data validation with performance considerations.
"""

import re
from typing import Annotated, Any
from datetime import datetime, timezone
from pydantic import (
    BaseModel, 
    Field, 
    validator, 
    root_validator,
    ValidationError,
    AfterValidator,
    BeforeValidator,
    PlainValidator
)
from pydantic.types import confloat, conint, constr


# Custom field type definitions using Annotated for performance
PositiveFloat = Annotated[
    float, 
    Field(gt=0.0, description="Must be a positive floating point number")
]

PercentageFloat = Annotated[
    float,
    Field(ge=0.0, le=100.0, description="Percentage value between 0.0 and 100.0")
]

NonNegativeInt = Annotated[
    int,
    Field(ge=0, description="Must be a non-negative integer")
]

NonNegativeFloat = Annotated[
    float,
    Field(ge=0.0, description="Must be a non-negative floating point number")
]

# Memory size in bytes (can be very large)
MemorySize = Annotated[
    float,
    Field(ge=0.0, description="Memory size in bytes")
]

# Response time in milliseconds
ResponseTime = Annotated[
    float,
    Field(ge=0.0, le=60000.0, description="Response time in milliseconds (max 60 seconds)")
]

# Uptime in seconds
UptimeSeconds = Annotated[
    float,
    Field(ge=0.0, description="Uptime in seconds")
]

# Query rate (queries per minute)
QueryRate = Annotated[
    float,
    Field(ge=0.0, le=10000.0, description="Query rate in queries per minute")
]

# Cache hit rate as a ratio (0.0 to 1.0)
CacheHitRate = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Cache hit rate as a ratio between 0.0 and 1.0")
]

# Node/Edge counts
NodeCount = Annotated[
    int,
    Field(ge=0, description="Number of nodes in the graph")
]

EdgeCount = Annotated[
    int,
    Field(ge=0, description="Number of edges in the graph")
]

# Graph density (0.0 to 1.0)
GraphDensity = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Graph density between 0.0 and 1.0")
]

# Clustering coefficient (0.0 to 1.0)
ClusteringCoefficient = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Clustering coefficient between 0.0 and 1.0")
]

# Centrality measures (0.0 to 1.0 for normalized)
CentralityScore = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Normalized centrality score between 0.0 and 1.0")
]

# Modularity (-1.0 to 1.0)
Modularity = Annotated[
    float,
    Field(ge=-1.0, le=1.0, description="Modularity score between -1.0 and 1.0")
]

# Memory efficiency ratio (0.0 to 1.0)
MemoryEfficiency = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Memory efficiency ratio between 0.0 and 1.0")
]

# Growth rate (can be negative for shrinking)
GrowthRate = Annotated[
    float,
    Field(ge=-1.0, le=10.0, description="Growth rate between -100% and 1000%")
]

# Compression ratio (typically >= 1.0)
CompressionRatio = Annotated[
    float,
    Field(ge=1.0, le=100.0, description="Compression ratio (1.0 = no compression)")
]


# Custom validator functions
def validate_timestamp_format(value: Any) -> str:
    """Validate and normalize timestamp strings to ISO 8601 format"""
    if isinstance(value, str):
        try:
            # Try to parse the timestamp
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            # Return normalized ISO format with timezone
            return str(dt.isoformat())
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {value}")
    elif isinstance(value, datetime):
        # Convert datetime to ISO string
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return str(value.isoformat())
    else:
        raise ValueError(f"Timestamp must be string or datetime, got {type(value)}")


def validate_memory_size_unit(value: Any) -> float:
    """Validate memory size and convert to bytes if needed"""
    if isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, str):
        # Handle memory size strings like "1.5GB", "512MB", etc.
        value = value.strip().upper()
        
        # Extract number and unit
        match = re.match(r'^(\d+\.?\d*)\s*([KMGT]?B?)$', value)
        if not match:
            raise ValueError(f"Invalid memory size format: {value}")
        
        number, unit = match.groups()
        number = float(number)
        
        # Convert to bytes
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
            '': 1  # No unit assumes bytes
        }
        
        if unit not in multipliers:
            raise ValueError(f"Unknown memory unit: {unit}")
        
        return number * multipliers[unit]
    else:
        raise ValueError(f"Memory size must be number or string, got {type(value)}")


# Annotated types with custom validators
TimestampStr = Annotated[
    str,
    BeforeValidator(validate_timestamp_format),
    Field(description="ISO 8601 timestamp string")
]

MemorySizeWithUnit = Annotated[
    float,
    BeforeValidator(validate_memory_size_unit),
    Field(description="Memory size in bytes (supports unit suffixes like GB, MB)")
]


# Validation utility functions
def validate_percentage_as_ratio(value: float) -> float:
    """Convert percentage (0-100) to ratio (0.0-1.0) if needed"""
    if value > 1.0:
        # Assume it's a percentage, convert to ratio
        return value / 100.0
    return value


def validate_response_time_unit(value: float) -> float:
    """Ensure response time is in milliseconds"""
    # If value is very small, it might be in seconds, convert to ms
    if value < 1.0 and value > 0:
        return value * 1000.0
    return value


# Additional annotated types with conversion
CacheHitRateFromPercentage = Annotated[
    float,
    BeforeValidator(validate_percentage_as_ratio),
    Field(ge=0.0, le=1.0, description="Cache hit rate (auto-converts from percentage)")
]

ResponseTimeMs = Annotated[
    float,
    BeforeValidator(validate_response_time_unit),
    Field(ge=0.0, le=60000.0, description="Response time in milliseconds")
]


# Base validation model for common patterns
class BaseValidationModel(BaseModel):
    """Base model with common validation configuration"""
    
    class Config:
        # Enable validation on assignment
        validate_assignment = True
        # Use enum values for serialization
        use_enum_values = True
        # Allow population by field name or alias
        allow_population_by_field_name = True
        # Validate default values
        validate_default = True
        # Extra fields are forbidden by default
        extra = "forbid"
        # Use fast JSON serialization
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


# Validation error collection model
class ValidationResult(BaseValidationModel):
    """Result of validation with success status and errors"""
    
    is_valid: bool = Field(description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")
    warnings: list[str] = Field(default_factory=list, description="List of validation warnings")
    
    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result"""
        return cls(is_valid=True)
    
    @classmethod
    def failure(cls, errors: list[str], warnings: list[str] | None = None) -> "ValidationResult":
        """Create a failed validation result"""
        return cls(
            is_valid=False,
            errors=errors,
            warnings=warnings or []
        )
    
    def add_error(self, error: str) -> None:
        """Add an error to the result"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result"""
        self.warnings.append(warning)


# Performance validation utilities
class PerformanceValidator:
    """Utility class for performance-related validations"""
    
    @staticmethod
    def validate_metrics_consistency(
        cpu_usage: float,
        memory_usage: float,
        response_time: float
    ) -> ValidationResult:
        """Validate that performance metrics are consistent"""
        result = ValidationResult.success()
        
        # Check for unrealistic combinations
        if cpu_usage > 95.0 and response_time < 10.0:
            result.add_warning("High CPU usage with very low response time seems unusual")
        
        if memory_usage > 90.0 and cpu_usage < 5.0:
            result.add_warning("High memory usage with very low CPU usage seems unusual")
        
        if response_time > 5000.0:  # 5 seconds
            result.add_error("Response time exceeds acceptable threshold (5 seconds)")
        
        return result
    
    @staticmethod
    def validate_graph_metrics_consistency(
        node_count: int,
        edge_count: int,
        density: float,
        clustering: float
    ) -> ValidationResult:
        """Validate that graph metrics are mathematically consistent"""
        result = ValidationResult.success()
        
        if node_count == 0 and edge_count > 0:
            result.add_error("Cannot have edges without nodes")
        
        if node_count > 0:
            max_edges = node_count * (node_count - 1) // 2
            if edge_count > max_edges:
                result.add_error(f"Edge count {edge_count} exceeds maximum possible {max_edges}")
            
            # Check density calculation
            if max_edges > 0:
                expected_density = edge_count / max_edges
                if abs(density - expected_density) > 0.01:  # Allow small floating point errors
                    result.add_warning(f"Density {density} doesn't match calculated {expected_density:.3f}")
        
        return result 