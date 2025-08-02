"""
Dynamic Feature Compatibility Validation

This module provides utilities for validating dynamic feature compatibility
between Codon and CPython implementations.
"""

import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DynamicFeatureResult:
    """Result of dynamic feature validation"""

    success: bool
    validation_time: float
    supported_features: List[str] = field(default_factory=list)
    unsupported_features: List[str] = field(default_factory=list)
    compatibility_score: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class FeatureTest:
    """Test for a dynamic feature"""

    name: str
    test_func: Callable
    required: bool = False
    description: str = ""


class DynamicFeatureValidator:
    """Dynamic feature compatibility validator"""

    def __init__(self):
        self.feature_tests: List[FeatureTest] = []
        self.validation_results: List[DynamicFeatureResult] = []

    def register_feature_test(
        self,
        name: str,
        test_func: Callable,
        required: bool = False,
        description: str = "",
    ):
        """Register a feature test"""

        feature_test = FeatureTest(
            name=name, test_func=test_func, required=required, description=description
        )
        self.feature_tests.append(feature_test)

    def validate_cpython_features(self) -> DynamicFeatureResult:
        """Validate features available in CPython"""

        result = DynamicFeatureResult(success=True, validation_time=0.0)
        start_time = time.time()

        for feature_test in self.feature_tests:
            try:
                if feature_test.test_func():
                    result.supported_features.append(feature_test.name)
                else:
                    result.unsupported_features.append(feature_test.name)
                    if feature_test.required:
                        result.success = False
                        error_msg = (
                            f"Required feature {feature_test.name} not supported"
                        )
                        result.errors.append(error_msg)

            except Exception as e:
                result.unsupported_features.append(feature_test.name)
                error_msg = f"Error testing feature {feature_test.name}: {e}"
                result.errors.append(error_msg)
                if feature_test.required:
                    result.success = False

        result.validation_time = time.time() - start_time
        result.compatibility_score = len(result.supported_features) / len(
            self.feature_tests
        )

        self.validation_results.append(result)
        return result

    def validate_codon_features(self) -> DynamicFeatureResult:
        """Validate features available in Codon"""

        result = DynamicFeatureResult(success=True, validation_time=0.0)
        start_time = time.time()

        for feature_test in self.feature_tests:
            try:
                if feature_test.test_func():
                    result.supported_features.append(feature_test.name)
                else:
                    result.unsupported_features.append(feature_test.name)
                    if feature_test.required:
                        result.success = False
                        error_msg = (
                            f"Required feature {feature_test.name} not supported"
                        )
                        result.errors.append(error_msg)

            except Exception as e:
                result.unsupported_features.append(feature_test.name)
                error_msg = f"Error testing feature {feature_test.name}: {e}"
                result.errors.append(error_msg)
                if feature_test.required:
                    result.success = False

        result.validation_time = time.time() - start_time
        result.compatibility_score = len(result.supported_features) / len(
            self.feature_tests
        )

        self.validation_results.append(result)
        return result

    def compare_feature_compatibility(
        self, cpython_result: DynamicFeatureResult, codon_result: DynamicFeatureResult
    ) -> DynamicFeatureResult:
        """Compare feature compatibility between implementations"""

        result = DynamicFeatureResult(success=True, validation_time=0.0)

        # Find common supported features
        cpython_supported = set(cpython_result.supported_features)
        codon_supported = set(codon_result.supported_features)

        common_features = cpython_supported.intersection(codon_supported)
        cpython_only = cpython_supported - codon_supported
        codon_only = codon_supported - cpython_supported

        result.supported_features = list(common_features)
        result.unsupported_features = list(cpython_only | codon_only)

        # Check for compatibility issues
        if cpython_only:
            warning_msg = f"Features only in CPython: {list(cpython_only)}"
            result.warnings.append(warning_msg)

        if codon_only:
            warning_msg = f"Features only in Codon: {list(codon_only)}"
            result.warnings.append(warning_msg)

        # Calculate compatibility score
        total_features = len(self.feature_tests)
        if total_features > 0:
            result.compatibility_score = len(common_features) / total_features

        # Check if all required features are supported in both
        required_features = [ft.name for ft in self.feature_tests if ft.required]
        missing_required = []

        for feature in required_features:
            if feature not in common_features:
                missing_required.append(feature)

        if missing_required:
            result.success = False
            error_msg = f"Missing required features: {missing_required}"
            result.errors.append(error_msg)

        self.validation_results.append(result)
        return result

    def get_feature_summary(self) -> Dict[str, Any]:
        """Get summary of feature validation results"""

        if not self.validation_results:
            return {"error": "No validation results available"}

        latest_result = self.validation_results[-1]

        return {
            "total_features": len(self.feature_tests),
            "supported_features": len(latest_result.supported_features),
            "unsupported_features": len(latest_result.unsupported_features),
            "compatibility_score": latest_result.compatibility_score,
            "success": latest_result.success,
            "errors": latest_result.errors,
            "warnings": latest_result.warnings,
        }


# Built-in feature tests
def test_async_await_support() -> bool:
    """Test async/await support"""
    try:
        import asyncio

        return True
    except ImportError:
        return False


def test_type_hints_support() -> bool:
    """Test type hints support"""
    try:
        from typing import Dict, List, Optional

        return True
    except ImportError:
        return False


def test_dataclasses_support() -> bool:
    """Test dataclasses support"""
    try:
        from dataclasses import dataclass

        return True
    except ImportError:
        return False


def test_f_strings_support() -> bool:
    """Test f-string support"""
    try:
        name = "test"
        f"Hello {name}"
        return True
    except SyntaxError:
        return False


def test_walrus_operator_support() -> bool:
    """Test walrus operator support"""
    try:
        if (x := 1) > 0:
            pass
        return True
    except SyntaxError:
        return False


def test_pattern_matching_support() -> bool:
    """Test pattern matching support"""
    try:
        match 1:
            case 1:
                pass
        return True
    except SyntaxError:
        return False


def test_generics_support() -> bool:
    """Test generics support"""
    try:
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class Test(Generic[T]):
            pass

        return True
    except (ImportError, SyntaxError):
        return False


def test_contextlib_support() -> bool:
    """Test contextlib support"""
    try:
        from contextlib import contextmanager

        return True
    except ImportError:
        return False


def test_pathlib_support() -> bool:
    """Test pathlib support"""
    try:
        from pathlib import Path

        return True
    except ImportError:
        return False


def test_json_support() -> bool:
    """Test JSON support"""
    try:
        import json

        json.dumps({"test": "value"})
        return True
    except ImportError:
        return False


# Pytest fixtures
@pytest.fixture
def dynamic_feature_validator():
    """Fixture for dynamic feature validator"""
    validator = DynamicFeatureValidator()

    # Register built-in feature tests
    validator.register_feature_test(
        "async_await",
        test_async_await_support,
        required=False,
        description="Async/await syntax support",
    )
    validator.register_feature_test(
        "type_hints",
        test_type_hints_support,
        required=True,
        description="Type hints support",
    )
    validator.register_feature_test(
        "dataclasses",
        test_dataclasses_support,
        required=False,
        description="Dataclasses support",
    )
    validator.register_feature_test(
        "f_strings",
        test_f_strings_support,
        required=False,
        description="F-string syntax support",
    )
    validator.register_feature_test(
        "walrus_operator",
        test_walrus_operator_support,
        required=False,
        description="Walrus operator support",
    )
    validator.register_feature_test(
        "pattern_matching",
        test_pattern_matching_support,
        required=False,
        description="Pattern matching support",
    )
    validator.register_feature_test(
        "generics",
        test_generics_support,
        required=False,
        description="Generics support",
    )
    validator.register_feature_test(
        "contextlib",
        test_contextlib_support,
        required=False,
        description="Contextlib support",
    )
    validator.register_feature_test(
        "pathlib", test_pathlib_support, required=False, description="Pathlib support"
    )
    validator.register_feature_test(
        "json", test_json_support, required=True, description="JSON support"
    )

    return validator
