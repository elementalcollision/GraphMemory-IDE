"""
API Contract Validation Utilities

This module provides utilities for validating API contracts between Codon and
CPython implementations, ensuring consistent behavior and interface compatibility.
"""

import inspect
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

import pytest
from jsonschema import Draft7Validator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """API validation levels"""

    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"


@dataclass
class APIContractResult:
    """Result of API contract validation"""

    success: bool
    validation_time: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    compatibility_score: float = 0.0
    tested_endpoints: List[str] = field(default_factory=list)
    failed_endpoints: List[str] = field(default_factory=list)


@dataclass
class FunctionSignature:
    """Function signature information"""

    name: str
    parameters: Dict[str, Type] = field(default_factory=dict)
    return_type: Optional[Type] = None
    docstring: Optional[str] = None
    is_async: bool = False
    is_generator: bool = False
    is_coroutine: bool = False


class APIContractValidator:
    """API contract validation utilities"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.NORMAL):
        self.validation_level = validation_level
        self.schema_cache: Dict[str, dict] = {}
        self.validator_cache: Dict[str, Draft7Validator] = {}

    def validate_function_signatures(
        self, cpython_func: Callable, codon_func: Callable, func_name: str = "function"
    ) -> bool:
        """Validate function signature compatibility between CPython and Codon"""

        try:
            # Extract signatures
            cpython_sig = inspect.signature(cpython_func)
            codon_sig = inspect.signature(codon_func)

            # Compare parameter names and types
            if cpython_sig.parameters != codon_sig.parameters:
                logger.error(f"Parameter mismatch in {func_name}")
                return False

            # Compare return types if available
            if cpython_sig.return_annotation != codon_sig.return_annotation:
                logger.warning(f"Return type mismatch in {func_name}")
                if self.validation_level == ValidationLevel.STRICT:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating function signatures for {func_name}: {e}")
            return False

    def validate_behavioral_parity(
        self,
        cpython_func: Callable,
        codon_func: Callable,
        test_cases: List[Dict[str, Any]],
        func_name: str = "function",
    ) -> APIContractResult:
        """Validate behavioral parity between CPython and Codon implementations"""

        result = APIContractResult(success=True, validation_time=0.0)
        start_time = time.time()

        for i, test_case in enumerate(test_cases):
            try:
                # Test CPython implementation
                cpython_args = test_case.get("args", [])
                cpython_kwargs = test_case.get("kwargs", {})

                cpython_result = cpython_func(*cpython_args, **cpython_kwargs)

                # Test Codon implementation
                codon_args = test_case.get("args", [])
                codon_kwargs = test_case.get("kwargs", {})

                codon_result = codon_func(*codon_args, **codon_kwargs)

                # Compare results
                if not self._compare_results(cpython_result, codon_result):
                    error_msg = f"Behavioral mismatch in test case {i} for {func_name}"
                    result.errors.append(error_msg)
                    result.success = False

            except Exception as e:
                error_msg = f"Exception in test case {i} for {func_name}: {e}"
                result.errors.append(error_msg)
                result.success = False

        result.validation_time = time.time() - start_time
        return result

    def validate_schema_compatibility(
        self, cpython_schema: dict, codon_schema: dict, schema_name: str = "schema"
    ) -> bool:
        """Validate schema compatibility between implementations"""

        try:
            # Basic schema structure validation
            if not self._validate_schema_structure(cpython_schema, codon_schema):
                return False

            # Property compatibility validation
            if not self._validate_property_compatibility(cpython_schema, codon_schema):
                return False

            # Type compatibility validation
            if not self._validate_type_compatibility(cpython_schema, codon_schema):
                return False

            return True

        except Exception as e:
            logger.error(
                f"Error validating schema compatibility for {schema_name}: {e}"
            )
            return False

    def validate_error_handling(
        self,
        cpython_func: Callable,
        codon_func: Callable,
        error_test_cases: List[Dict[str, Any]],
        func_name: str = "function",
    ) -> APIContractResult:
        """Validate error handling compatibility"""

        result = APIContractResult(success=True, validation_time=0.0)
        start_time = time.time()

        for i, test_case in enumerate(error_test_cases):
            try:
                # Test error conditions
                args = test_case.get("args", [])
                kwargs = test_case.get("kwargs", {})
                expected_exception = test_case.get("expected_exception", Exception)

                # Test CPython error handling
                cpython_exception = None
                try:
                    cpython_func(*args, **kwargs)
                except Exception as e:
                    cpython_exception = type(e)

                # Test Codon error handling
                codon_exception = None
                try:
                    codon_func(*args, **kwargs)
                except Exception as e:
                    codon_exception = type(e)

                # Compare exception types
                if cpython_exception != codon_exception:
                    error_msg = (
                        f"Exception type mismatch in test case {i} for {func_name}"
                    )
                    result.errors.append(error_msg)
                    result.success = False

            except Exception as e:
                error_msg = (
                    f"Error in error handling test case {i} for {func_name}: {e}"
                )
                result.errors.append(error_msg)
                result.success = False

        result.validation_time = time.time() - start_time
        return result

    def validate_performance_compatibility(
        self,
        cpython_func: Callable,
        codon_func: Callable,
        test_cases: List[Dict[str, Any]],
        tolerance: float = 0.1,
        func_name: str = "function",
    ) -> APIContractResult:
        """Validate performance compatibility between implementations"""

        result = APIContractResult(success=True, validation_time=0.0)
        start_time = time.time()

        for i, test_case in enumerate(test_cases):
            try:
                args = test_case.get("args", [])
                kwargs = test_case.get("kwargs", {})
                iterations = test_case.get("iterations", 1000)

                # Measure CPython performance
                cpython_start = time.time()
                for _ in range(iterations):
                    cpython_func(*args, **kwargs)
                cpython_time = time.time() - cpython_start

                # Measure Codon performance
                codon_start = time.time()
                for _ in range(iterations):
                    codon_func(*args, **kwargs)
                codon_time = time.time() - codon_start

                # Compare performance (Codon should be faster)
                if codon_time > cpython_time * (1 + tolerance):
                    warning_msg = (
                        f"Performance regression in test case {i} for {func_name}"
                    )
                    result.warnings.append(warning_msg)

            except Exception as e:
                error_msg = f"Error in performance test case {i} for {func_name}: {e}"
                result.errors.append(error_msg)
                result.success = False

        result.validation_time = time.time() - start_time
        return result

    def _compare_results(self, result_a: Any, result_b: Any) -> bool:
        """Compare results for equality"""

        # Handle None values
        if result_a is None and result_b is None:
            return True
        if result_a is None or result_b is None:
            return False

        # Handle basic types
        if type(result_a) != type(result_b):
            return False

        # Handle different data types
        if isinstance(result_a, (dict, list, tuple)):
            return self._compare_structured_data(result_a, result_b)
        else:
            return result_a == result_b

    def _compare_structured_data(self, data_a: Any, data_b: Any) -> bool:
        """Compare structured data (dict, list, tuple)"""

        if isinstance(data_a, dict):
            if not isinstance(data_b, dict):
                return False
            if set(data_a.keys()) != set(data_b.keys()):
                return False
            return all(self._compare_results(data_a[k], data_b[k]) for k in data_a)

        elif isinstance(data_a, (list, tuple)):
            if not isinstance(data_b, type(data_a)):
                return False
            if len(data_a) != len(data_b):
                return False
            return all(self._compare_results(a, b) for a, b in zip(data_a, data_b))

        return data_a == data_b

    def _validate_schema_structure(self, schema_a: dict, schema_b: dict) -> bool:
        """Validate basic schema structure compatibility"""

        # Check required fields
        required_fields = ["type", "properties"]
        for field in required_fields:
            if field in schema_a != field in schema_b:
                return False

        # Check type compatibility
        if schema_a.get("type") != schema_b.get("type"):
            return False

        return True

    def _validate_property_compatibility(self, schema_a: dict, schema_b: dict) -> bool:
        """Validate property compatibility between schemas"""

        props_a = schema_a.get("properties", {})
        props_b = schema_b.get("properties", {})

        # Check if all properties in schema_a exist in schema_b
        for prop_name, prop_schema in props_a.items():
            if prop_name not in props_b:
                if self.validation_level == ValidationLevel.STRICT:
                    return False
                continue

            # Validate property schema compatibility
            if not self._validate_type_compatibility(prop_schema, props_b[prop_name]):
                return False

        return True

    def _validate_type_compatibility(self, schema_a: dict, schema_b: dict) -> bool:
        """Validate type compatibility between schemas"""

        type_a = schema_a.get("type")
        type_b = schema_b.get("type")

        if type_a != type_b:
            return False

        # Handle specific type validations
        if type_a == "object":
            return self._validate_property_compatibility(schema_a, schema_b)
        elif type_a == "array":
            return self._validate_array_compatibility(schema_a, schema_b)
        elif type_a == "string":
            return self._validate_string_compatibility(schema_a, schema_b)
        elif type_a == "number":
            return self._validate_number_compatibility(schema_a, schema_b)

        return True

    def _validate_array_compatibility(self, schema_a: dict, schema_b: dict) -> bool:
        """Validate array schema compatibility"""

        items_a = schema_a.get("items", {})
        items_b = schema_b.get("items", {})

        return self._validate_type_compatibility(items_a, items_b)

    def _validate_string_compatibility(self, schema_a: dict, schema_b: dict) -> bool:
        """Validate string schema compatibility"""

        # Check format compatibility
        format_a = schema_a.get("format")
        format_b = schema_b.get("format")

        if format_a and format_b and format_a != format_b:
            return False

        return True

    def _validate_number_compatibility(self, schema_a: dict, schema_b: dict) -> bool:
        """Validate number schema compatibility"""

        # Check range compatibility
        min_a = schema_a.get("minimum")
        min_b = schema_b.get("minimum")
        max_a = schema_a.get("maximum")
        max_b = schema_b.get("maximum")

        if min_a is not None and min_b is not None and min_a != min_b:
            return False
        if max_a is not None and max_b is not None and max_a != max_b:
            return False

        return True


# Pytest fixtures for easy integration
@pytest.fixture
def api_contract_validator():
    """Fixture for API contract validator"""
    return APIContractValidator()


@pytest.fixture
def strict_api_contract_validator():
    """Fixture for strict API contract validator"""
    return APIContractValidator(ValidationLevel.STRICT)


@pytest.fixture
def lenient_api_contract_validator():
    """Fixture for lenient API contract validator"""
    return APIContractValidator(ValidationLevel.LENIENT)
