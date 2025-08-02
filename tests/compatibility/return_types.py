"""
Return Type Validation

This module provides utilities for validating return type compatibility
between Codon and CPython implementations.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReturnTypeValidationResult:
    """Result of return type validation"""

    success: bool
    function_name: str
    cpython_return_type: Optional[Type]
    codon_return_type: Optional[Type]
    differences: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ReturnTypeValidator:
    """Return type validation utilities"""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_results: List[ReturnTypeValidationResult] = []

    def validate_return_types(
        self, cpython_func: Callable, codon_func: Callable, func_name: str = "function"
    ) -> ReturnTypeValidationResult:
        """Validate return type compatibility"""

        result = ReturnTypeValidationResult(
            success=True,
            function_name=func_name,
            cpython_return_type=None,
            codon_return_type=None,
        )

        try:
            import inspect

            # Extract return types from signatures
            cpython_sig = inspect.signature(cpython_func)
            codon_sig = inspect.signature(codon_func)

            result.cpython_return_type = cpython_sig.return_annotation
            result.codon_return_type = codon_sig.return_annotation

            # Compare return types
            if result.cpython_return_type != result.codon_return_type:
                if self.strict_mode:
                    result.success = False
                    diff_msg = f"Return type mismatch in {func_name}"
                    result.differences.append(diff_msg)
                else:
                    warning_msg = f"Return type difference in {func_name}"
                    result.warnings.append(warning_msg)

        except Exception as e:
            result.success = False
            error_msg = f"Error validating return types for {func_name}: {e}"
            result.differences.append(error_msg)

        self.validation_results.append(result)
        return result

    def get_return_type_summary(self) -> Dict[str, Any]:
        """Get summary of return type validation results"""

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
