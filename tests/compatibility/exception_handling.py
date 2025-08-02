"""
Exception Handling Validation

This module provides utilities for validating exception handling compatibility
between Codon and CPython implementations.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExceptionHandlingResult:
    """Result of exception handling validation"""

    success: bool
    function_name: str
    test_cases: int
    passed_cases: int
    failed_cases: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExceptionTestCase:
    """Test case for exception handling"""

    name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    expected_exception: Type[Exception]
    expected_message: Optional[str] = None


class ExceptionHandlingValidator:
    """Exception handling validation utilities"""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_results: List[ExceptionHandlingResult] = []

    def validate_exception_handling(
        self,
        cpython_func: Callable,
        codon_func: Callable,
        test_cases: List[ExceptionTestCase],
        func_name: str = "function",
    ) -> ExceptionHandlingResult:
        """Validate exception handling compatibility"""

        result = ExceptionHandlingResult(
            success=True,
            function_name=func_name,
            test_cases=len(test_cases),
            passed_cases=0,
            failed_cases=0,
        )

        for test_case in test_cases:
            try:
                # Test CPython exception handling
                cpython_exception = None
                cpython_message = None

                try:
                    cpython_func(*test_case.args, **test_case.kwargs)
                except Exception as e:
                    cpython_exception = type(e)
                    cpython_message = str(e)

                # Test Codon exception handling
                codon_exception = None
                codon_message = None

                try:
                    codon_func(*test_case.args, **test_case.kwargs)
                except Exception as e:
                    codon_exception = type(e)
                    codon_message = str(e)

                # Compare exception types
                if cpython_exception != codon_exception:
                    result.failed_cases += 1
                    result.success = False
                    error_msg = f"Exception type mismatch in {test_case.name}"
                    result.errors.append(error_msg)
                else:
                    result.passed_cases += 1

                # Compare exception messages if specified
                if test_case.expected_message:
                    if cpython_message != codon_message:
                        warning_msg = (
                            f"Exception message difference in {test_case.name}"
                        )
                        result.warnings.append(warning_msg)

            except Exception as e:
                result.failed_cases += 1
                result.success = False
                error_msg = f"Error in exception test {test_case.name}: {e}"
                result.errors.append(error_msg)

        self.validation_results.append(result)
        return result

    def get_exception_handling_summary(self) -> Dict[str, Any]:
        """Get summary of exception handling validation results"""

        if not self.validation_results:
            return {"error": "No validation results available"}

        total_results = len(self.validation_results)
        total_test_cases = sum(r.test_cases for r in self.validation_results)
        total_passed_cases = sum(r.passed_cases for r in self.validation_results)
        total_failed_cases = sum(r.failed_cases for r in self.validation_results)

        all_errors = []
        all_warnings = []

        for result in self.validation_results:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        return {
            "total_results": total_results,
            "total_test_cases": total_test_cases,
            "total_passed_cases": total_passed_cases,
            "total_failed_cases": total_failed_cases,
            "success_rate": (
                total_passed_cases / total_test_cases if total_test_cases > 0 else 0
            ),
            "total_errors": len(all_errors),
            "total_warnings": len(all_warnings),
            "errors": all_errors,
            "warnings": all_warnings,
        }
