"""
Codon Compilation Fixtures for Test Fixtures

This module provides compilation-specific test fixtures and utilities
for Codon components testing.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


@dataclass
class CompilationFixture:
    """Compilation test fixture"""

    name: str
    source_code: str
    expected_success: bool
    expected_warnings: List[str]
    optimization_level: str
    target_platform: str
    timeout_seconds: int = 30


@dataclass
class CompilationResult:
    """Result of compilation test"""

    success: bool
    compilation_time: float
    executable_size: Optional[int]
    error_message: Optional[str]
    warnings: List[str]
    optimization_level: str
    target_platform: str


class CodonCompilationFixtures:
    """Comprehensive compilation fixtures for Codon testing"""

    def __init__(self):
        self.temp_dir = None
        self.compilation_results = []

    def setup_temp_directory(self):
        """Setup temporary directory for compilation tests"""
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix="codon_compilation_")
        return self.temp_dir

    def cleanup_temp_directory(self):
        """Cleanup temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def create_source_file(self, source_code: str, filename: str = "test.codon") -> str:
        """Create a source file with the given code"""
        temp_dir = self.setup_temp_directory()
        file_path = os.path.join(temp_dir, filename)

        with open(file_path, "w") as f:
            f.write(source_code)

        return file_path

    def compile_source_file(
        self, source_file: str, optimization_level: str = "O2"
    ) -> CompilationResult:
        """Compile a source file using Codon"""
        start_time = os.times()[0]

        try:
            # Run Codon compilation
            cmd = [
                "codon",
                "build",
                f"-{optimization_level.lower()}" if optimization_level != "O0" else "",
                source_file,
            ]
            cmd = [arg for arg in cmd if arg]  # Remove empty strings

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            end_time = os.times()[0]
            compilation_time = end_time - start_time

            success = result.returncode == 0
            executable_size = None
            error_message = None

            if success:
                # Get executable size
                executable_path = source_file.replace(".codon", "")
                if os.path.exists(executable_path):
                    executable_size = os.path.getsize(executable_path)
            else:
                error_message = result.stderr

            # Parse warnings from stderr
            warnings = []
            if result.stderr:
                for line in result.stderr.split("\n"):
                    if "warning" in line.lower():
                        warnings.append(line.strip())

            return CompilationResult(
                success=success,
                compilation_time=compilation_time,
                executable_size=executable_size,
                error_message=error_message,
                warnings=warnings,
                optimization_level=optimization_level,
                target_platform="native",
            )

        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False,
                compilation_time=30.0,
                executable_size=None,
                error_message="Compilation timeout",
                warnings=[],
                optimization_level=optimization_level,
                target_platform="native",
            )
        except Exception as e:
            return CompilationResult(
                success=False,
                compilation_time=0.0,
                executable_size=None,
                error_message=str(e),
                warnings=[],
                optimization_level=optimization_level,
                target_platform="native",
            )

    def generate_basic_compilation_fixtures(self) -> List[CompilationFixture]:
        """Generate basic compilation test fixtures"""
        fixtures = []

        # Valid compilation fixtures
        valid_fixtures = [
            CompilationFixture(
                name="simple_function",
                source_code="""
def hello_world():
    return "Hello, World!"

def main():
    print(hello_world())
""",
                expected_success=True,
                expected_warnings=[],
                optimization_level="O2",
                target_platform="native",
            ),
            CompilationFixture(
                name="mathematical_operations",
                source_code="""
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

def main():
    result = add(5, 3) * multiply(2, 4)
    print(f"Result: {result}")
""",
                expected_success=True,
                expected_warnings=[],
                optimization_level="O3",
                target_platform="native",
            ),
            CompilationFixture(
                name="array_operations",
                source_code="""
def process_array(arr: List[int]) -> int:
    total = 0
    for item in arr:
        total += item
    return total

def main():
    numbers = [1, 2, 3, 4, 5]
    result = process_array(numbers)
    print(f"Sum: {result}")
""",
                expected_success=True,
                expected_warnings=[],
                optimization_level="O2",
                target_platform="native",
            ),
        ]

        fixtures.extend(valid_fixtures)

        # Invalid compilation fixtures
        invalid_fixtures = [
            CompilationFixture(
                name="syntax_error",
                source_code="""
def invalid_function(
    # Missing closing parenthesis
""",
                expected_success=False,
                expected_warnings=[],
                optimization_level="O2",
                target_platform="native",
            ),
            CompilationFixture(
                name="undefined_variable",
                source_code="""
def test_function():
    return undefined_variable
""",
                expected_success=False,
                expected_warnings=[],
                optimization_level="O2",
                target_platform="native",
            ),
            CompilationFixture(
                name="type_error",
                source_code="""
def type_error_function(x: int) -> str:
    return x + "string"
""",
                expected_success=False,
                expected_warnings=[],
                optimization_level="O2",
                target_platform="native",
            ),
        ]

        fixtures.extend(invalid_fixtures)

        return fixtures

    def generate_advanced_compilation_fixtures(self) -> List[CompilationFixture]:
        """Generate advanced compilation test fixtures"""
        fixtures = []

        # Complex algorithms
        fixtures.append(
            CompilationFixture(
                name="recursive_algorithm",
                source_code="""
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def main():
    result = fibonacci(20)
    print(f"Fibonacci(20) = {result}")
""",
                expected_success=True,
                expected_warnings=[],
                optimization_level="O3",
                target_platform="native",
            )
        )

        fixtures.append(
            CompilationFixture(
                name="matrix_operations",
                source_code="""
def matrix_multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    rows_a = len(a)
    cols_a = len(a[0])
    cols_b = len(b[0])
    
    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    
    return result

def main():
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    result = matrix_multiply(a, b)
    print(f"Matrix multiplication result: {result}")
""",
                expected_success=True,
                expected_warnings=[],
                optimization_level="O3",
                target_platform="native",
            )
        )

        return fixtures

    def generate_performance_compilation_fixtures(self) -> List[CompilationFixture]:
        """Generate performance-focused compilation fixtures"""
        fixtures = []

        # Performance-critical code
        fixtures.append(
            CompilationFixture(
                name="performance_critical_loop",
                source_code="""
def performance_test():
    total = 0
    for i in range(1000000):
        total += i * i
    return total

def main():
    result = performance_test()
    print(f"Performance test result: {result}")
""",
                expected_success=True,
                expected_warnings=[],
                optimization_level="O3",
                target_platform="native",
            )
        )

        fixtures.append(
            CompilationFixture(
                name="memory_intensive_operations",
                source_code="""
def memory_test():
    large_array = [i for i in range(100000)]
    processed = [x * 2 for x in large_array]
    return sum(processed)

def main():
    result = memory_test()
    print(f"Memory test result: {result}")
""",
                expected_success=True,
                expected_warnings=[],
                optimization_level="O2",
                target_platform="native",
            )
        )

        return fixtures

    def run_compilation_test(self, fixture: CompilationFixture) -> Dict[str, Any]:
        """Run a compilation test with the given fixture"""
        # Create source file
        source_file = self.create_source_file(
            fixture.source_code, f"{fixture.name}.codon"
        )

        # Compile the source file
        result = self.compile_source_file(source_file, fixture.optimization_level)

        # Validate results
        test_passed = result.success == fixture.expected_success and len(
            result.warnings
        ) >= len(fixture.expected_warnings)

        return {
            "fixture_name": fixture.name,
            "test_passed": test_passed,
            "expected_success": fixture.expected_success,
            "actual_success": result.success,
            "compilation_time": result.compilation_time,
            "executable_size": result.executable_size,
            "error_message": result.error_message,
            "warnings": result.warnings,
            "expected_warnings": fixture.expected_warnings,
        }

    def get_all_fixtures(self) -> Dict[str, List[CompilationFixture]]:
        """Get all compilation fixtures organized by category"""
        return {
            "basic": self.generate_basic_compilation_fixtures(),
            "advanced": self.generate_advanced_compilation_fixtures(),
            "performance": self.generate_performance_compilation_fixtures(),
        }


# Pytest fixtures
@pytest.fixture
def codon_compilation_fixtures():
    """Fixture providing Codon compilation fixtures"""
    fixtures = CodonCompilationFixtures()
    yield fixtures
    fixtures.cleanup_temp_directory()


@pytest.fixture
def basic_compilation_fixtures(codon_compilation_fixtures):
    """Fixture providing basic compilation fixtures"""
    return codon_compilation_fixtures.generate_basic_compilation_fixtures()


@pytest.fixture
def advanced_compilation_fixtures(codon_compilation_fixtures):
    """Fixture providing advanced compilation fixtures"""
    return codon_compilation_fixtures.generate_advanced_compilation_fixtures()


@pytest.fixture
def performance_compilation_fixtures(codon_compilation_fixtures):
    """Fixture providing performance compilation fixtures"""
    return codon_compilation_fixtures.generate_performance_compilation_fixtures()


@pytest.fixture
def all_compilation_fixtures(codon_compilation_fixtures):
    """Fixture providing all compilation fixtures"""
    return codon_compilation_fixtures.get_all_fixtures()
