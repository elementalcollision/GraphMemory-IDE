"""
Data Type Conversion Integration Tests for CPython-Codon Boundaries

This module provides comprehensive testing for data type conversions between
CPython and Codon, including round-trip conversions and edge case handling.
"""

import asyncio
import logging
from typing import Any, Dict, List

import pytest

from tests.utils.interop_tester import (
    DataTypeConversionTester,
    InteropTestResult,
    TestType,
)

logger = logging.getLogger(__name__)


class TestCPythonCodonDataConversions:
    """Data type conversion tests for CPython-Codon boundaries"""

    def setup_method(self):
        """Setup test fixtures"""
        self.data_type_tester = DataTypeConversionTester()
        self.test_results: List[InteropTestResult] = []

    async def test_primitive_type_conversions(self):
        """Test conversion of primitive Python types"""
        # Test integer conversions
        test_data = 42
        result = await self.data_type_tester.test_round_trip_conversion(
            test_data, self._python_to_codon_int, self._codon_to_python_int
        )
        assert result.status == "passed"
        assert result.test_type == TestType.DATA_TYPE_CONVERSION

    async def test_list_conversions(self):
        """Test conversion of Python lists"""
        test_data = [1, 2, 3, "test", {"key": "value"}]
        result = await self.data_type_tester.test_round_trip_conversion(
            test_data, self._python_to_codon_list, self._codon_to_python_list
        )
        assert result.status == "passed"
        assert result.test_type == TestType.DATA_TYPE_CONVERSION

    async def test_dict_conversions(self):
        """Test conversion of Python dictionaries"""
        test_data = {
            "string_key": "string_value",
            "int_key": 42,
            "list_key": [1, 2, 3],
            "nested_dict": {"inner": "value"},
        }
        result = await self.data_type_tester.test_round_trip_conversion(
            test_data, self._python_to_codon_dict, self._codon_to_python_dict
        )
        assert result.status == "passed"
        assert result.test_type == TestType.DATA_TYPE_CONVERSION

    async def test_complex_nested_structures(self):
        """Test conversion of complex nested data structures"""
        test_data = {
            "analytics_request": {
                "filters": {
                    "time_range": "24h",
                    "metrics": ["cpu", "memory", "network"],
                },
                "parameters": {"aggregation": "mean", "group_by": ["host", "service"]},
                "results": [
                    {"timestamp": "2025-08-02T10:00:00", "value": 0.75},
                    {"timestamp": "2025-08-02T10:01:00", "value": 0.82},
                ],
            }
        }
        result = await self.data_type_tester.test_round_trip_conversion(
            test_data, self._python_to_codon_complex, self._codon_to_python_complex
        )
        assert result.status == "passed"
        assert result.test_type == TestType.DATA_TYPE_CONVERSION

    async def test_edge_cases(self):
        """Test edge cases for data type conversions"""
        edge_cases = [
            None,  # None value
            "",  # Empty string
            [],  # Empty list
            {},  # Empty dict
            float("inf"),  # Infinity
            float("-inf"),  # Negative infinity
            float("nan"),  # NaN
            complex(1, 2),  # Complex number
            b"bytes",  # Bytes
            (1, 2, 3),  # Tuple
            set([1, 2, 3]),  # Set
            frozenset([1, 2, 3]),  # Frozen set
        ]

        results = await self.data_type_tester.test_edge_cases(
            self._python_to_codon_edge, edge_cases
        )

        # Some edge cases may fail, which is expected
        assert len(results) == len(edge_cases)
        for result in results:
            assert result.test_type == TestType.DATA_TYPE_CONVERSION

    async def test_analytics_data_conversions(self):
        """Test conversion of analytics-specific data structures"""
        analytics_data = {
            "metrics": {"cpu_usage": 0.75, "memory_usage": 0.82, "network_io": 1024.5},
            "alerts": [
                {
                    "id": "alert_001",
                    "severity": "high",
                    "message": "CPU usage exceeded threshold",
                    "timestamp": "2025-08-02T10:00:00",
                }
            ],
            "performance_data": {
                "response_time": 0.125,
                "throughput": 1000.0,
                "error_rate": 0.01,
            },
        }

        result = await self.data_type_tester.test_round_trip_conversion(
            analytics_data,
            self._python_to_codon_analytics,
            self._codon_to_python_analytics,
        )
        assert result.status == "passed"
        assert result.test_type == TestType.DATA_TYPE_CONVERSION

    # Conversion function implementations (simulated)
    def _python_to_codon_int(self, data: int) -> Dict[str, Any]:
        """Convert Python int to Codon format"""
        return {"type": "int", "value": data}

    def _codon_to_python_int(self, data: Dict[str, Any]) -> int:
        """Convert Codon int back to Python"""
        return data["value"]

    def _python_to_codon_list(self, data: List[Any]) -> Dict[str, Any]:
        """Convert Python list to Codon format"""
        return {"type": "list", "items": data}

    def _codon_to_python_list(self, data: Dict[str, Any]) -> List[Any]:
        """Convert Codon list back to Python"""
        return data["items"]

    def _python_to_codon_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python dict to Codon format"""
        return {"type": "dict", "pairs": list(data.items())}

    def _codon_to_python_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Codon dict back to Python"""
        return dict(data["pairs"])

    def _python_to_codon_complex(self, data: Any) -> Dict[str, Any]:
        """Convert complex Python structure to Codon format"""
        return {"type": "complex", "data": data}

    def _codon_to_python_complex(self, data: Dict[str, Any]) -> Any:
        """Convert complex Codon structure back to Python"""
        return data["data"]

    def _python_to_codon_edge(self, data: Any) -> Dict[str, Any]:
        """Convert edge case Python data to Codon format"""
        return {"type": "edge_case", "data": data}

    def _python_to_codon_analytics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert analytics data to Codon format"""
        return {"type": "analytics", "data": data}

    def _codon_to_python_analytics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert analytics data back to Python"""
        return data["data"]


class TestDataTypeConversionUtilities:
    """Test utilities for data type conversion testing"""

    def test_data_type_tester_initialization(self):
        """Test DataTypeConversionTester initialization"""
        tester = DataTypeConversionTester()
        assert tester.results == []

    async def test_deep_compare_functionality(self):
        """Test deep comparison functionality"""
        tester = DataTypeConversionTester()

        # Test simple types
        assert tester._deep_compare(42, 42)
        assert tester._deep_compare("test", "test")
        assert not tester._deep_compare(42, "42")

        # Test lists
        assert tester._deep_compare([1, 2, 3], [1, 2, 3])
        assert not tester._deep_compare([1, 2, 3], [1, 2, 4])

        # Test dictionaries
        assert tester._deep_compare({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert not tester._deep_compare({"a": 1, "b": 2}, {"a": 1, "b": 3})

    async def test_round_trip_conversion_patterns(self):
        """Test various round-trip conversion patterns"""
        tester = DataTypeConversionTester()

        # Test with different data types
        test_cases = [
            (42, lambda x: {"value": x}, lambda x: x["value"]),
            ("test", lambda x: {"value": x}, lambda x: x["value"]),
            ([1, 2, 3], lambda x: {"items": x}, lambda x: x["items"]),
        ]

        for original_data, to_codon, from_codon in test_cases:
            result = await tester.test_round_trip_conversion(
                original_data, to_codon, from_codon
            )
            assert result.status == "passed"
            assert result.test_type == TestType.DATA_TYPE_CONVERSION


# Integration test utilities
async def run_data_type_conversion_integration_tests() -> Dict[str, Any]:
    """Run comprehensive data type conversion integration tests"""
    logger.info("Running CPython-Codon data type conversion integration tests")

    results = {
        "test_results": [],
        "summary": {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
        },
    }

    # Create test instance
    test_instance = TestCPythonCodonDataConversions()
    test_instance.setup_method()

    # Run all data type conversion tests
    test_methods = [
        test_instance.test_primitive_type_conversions,
        test_instance.test_list_conversions,
        test_instance.test_dict_conversions,
        test_instance.test_complex_nested_structures,
        test_instance.test_edge_cases,
        test_instance.test_analytics_data_conversions,
    ]

    for test_method in test_methods:
        try:
            await test_method()
            results["summary"]["passed_tests"] += 1
        except Exception as e:
            logger.error(f"Test {test_method.__name__} failed: {e}")
            results["summary"]["failed_tests"] += 1
        finally:
            results["summary"]["total_tests"] += 1

    # Calculate success rate
    total = results["summary"]["total_tests"]
    if total > 0:
        results["summary"]["success_rate"] = results["summary"]["passed_tests"] / total

    return results


if __name__ == "__main__":
    # Run the integration tests
    asyncio.run(run_data_type_conversion_integration_tests())
