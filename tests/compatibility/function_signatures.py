"""
Function Signature Validation

This module provides utilities for validating function signature compatibility
between Codon and CPython implementations.
"""

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SignatureValidationResult:
    """Result of function signature validation"""

    success: bool
    function_name: str
    cpython_signature: str
    codon_signature: str
    differences: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class FunctionSignature:
    """Function signature information"""

    name: str
    parameters: Dict[str, inspect.Parameter] = field(default_factory=dict)
    return_annotation: Optional[Type] = None
    docstring: Optional[str] = None
    is_async: bool = False
    is_generator: bool = False
    is_coroutine: bool = False


class FunctionSignatureValidator:
    """Function signature validation utilities"""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_results: List[SignatureValidationResult] = []

    def validate_function_signatures(
        self, cpython_func: Callable, codon_func: Callable, func_name: str = "function"
    ) -> SignatureValidationResult:
        """Validate function signature compatibility"""

        result = SignatureValidationResult(
            success=True,
            function_name=func_name,
            cpython_signature=str(inspect.signature(cpython_func)),
            codon_signature=str(inspect.signature(codon_func)),
        )

        try:
            # Extract signatures
            cpython_sig = inspect.signature(cpython_func)
            codon_sig = inspect.signature(codon_func)

            # Compare parameters
            if cpython_sig.parameters != codon_sig.parameters:
                result.success = False
                diff_msg = f"Parameter mismatch in {func_name}"
                result.differences.append(diff_msg)

            # Compare return types
            if cpython_sig.return_annotation != codon_sig.return_annotation:
                if self.strict_mode:
                    result.success = False
                    diff_msg = f"Return type mismatch in {func_name}"
                    result.differences.append(diff_msg)
                else:
                    warning_msg = f"Return type difference in {func_name}"
                    result.warnings.append(warning_msg)

            # Check for async differences
            cpython_is_async = inspect.iscoroutinefunction(cpython_func)
            codon_is_async = inspect.iscoroutinefunction(codon_func)

            if cpython_is_async != codon_is_async:
                result.success = False
                diff_msg = f"Async/await mismatch in {func_name}"
                result.differences.append(diff_msg)

            # Check for generator differences
            cpython_is_gen = inspect.isgeneratorfunction(cpython_func)
            codon_is_gen = inspect.isgeneratorfunction(codon_func)

            if cpython_is_gen != codon_is_gen:
                result.success = False
                diff_msg = f"Generator function mismatch in {func_name}"
                result.differences.append(diff_msg)

        except Exception as e:
            result.success = False
            error_msg = f"Error validating signatures for {func_name}: {e}"
            result.differences.append(error_msg)

        self.validation_results.append(result)
        return result

    def validate_module_signatures(
        self, cpython_module, codon_module, function_names: List[str]
    ) -> List[SignatureValidationResult]:
        """Validate signatures for multiple functions in a module"""

        results = []

        for func_name in function_names:
            try:
                cpython_func = getattr(cpython_module, func_name)
                codon_func = getattr(codon_module, func_name)

                result = self.validate_function_signatures(
                    cpython_func, codon_func, func_name
                )
                results.append(result)

            except AttributeError as e:
                # Function doesn't exist in one of the modules
                result = SignatureValidationResult(
                    success=False,
                    function_name=func_name,
                    cpython_signature="N/A",
                    codon_signature="N/A",
                )
                result.differences.append(f"Function not found: {e}")
                results.append(result)

        return results

    def get_signature_summary(self) -> Dict[str, Any]:
        """Get summary of signature validation results"""

        if not self.validation_results:
            return {"error": "No validation results available"}

        total_functions = len(self.validation_results)
        successful_validations = sum(1 for r in self.validation_results if r.success)
        failed_validations = total_functions - successful_validations

        all_differences = []
        all_warnings = []

        for result in self.validation_results:
            all_differences.extend(result.differences)
            all_warnings.extend(result.warnings)

        return {
            "total_functions": total_functions,
            "successful_validations": successful_validations,
            "failed_validations": failed_validations,
            "success_rate": (
                successful_validations / total_functions if total_functions > 0 else 0
            ),
            "total_differences": len(all_differences),
            "total_warnings": len(all_warnings),
            "differences": all_differences,
            "warnings": all_warnings,
        }


# Pytest fixtures
@pytest.fixture
def function_signature_validator():
    """Fixture for function signature validator"""
    return FunctionSignatureValidator()


@pytest.fixture
def strict_function_signature_validator():
    """Fixture for strict function signature validator"""
    return FunctionSignatureValidator(strict_mode=True)
