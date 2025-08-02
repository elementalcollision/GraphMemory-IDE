"""
API Compatibility Testing Framework

This module provides comprehensive testing utilities for ensuring API contract
compatibility between Codon and CPython implementations, including behavioral
parity testing and dynamic feature compatibility validation.
"""

from .api_validator import APIContractValidator
from .behavioral_parity import BehavioralParityTester
from .dynamic_features import DynamicFeatureValidator
from .exception_handling import ExceptionHandlingValidator
from .function_signatures import FunctionSignatureValidator
from .return_types import ReturnTypeValidator

__all__ = [
    "APIContractValidator",
    "BehavioralParityTester",
    "DynamicFeatureValidator",
    "FunctionSignatureValidator",
    "ReturnTypeValidator",
    "ExceptionHandlingValidator",
]
