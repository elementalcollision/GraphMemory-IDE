"""
Test suite for Codon testing infrastructure validation.
This test validates that the foundation testing infrastructure is working correctly.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from tests.utils.codon_runner import (
    CodonCLIRunner,
    CodonEnvironmentManager,
    CodonErrorHandler,
    create_codon_runner,
    create_environment_manager,
)


class TestCodonInfrastructure:
    """Test suite for Codon testing infrastructure"""

    def test_codon_runner_creation(self, codon_runner):
        """Test that Codon runner can be created and configured"""
        assert codon_runner is not None
        assert codon_runner.cli_path.exists()
        assert codon_runner.python_path is not None

    def test_codon_version_check(self, codon_runner):
        """Test that Codon CLI version check works"""
        result = codon_runner.check_codon_version()
        assert result.success, f"Codon version check failed: {result.stderr}"
        # Codon version output is just the version number
        assert (
            result.stdout.strip().replace(".", "").isdigit()
            or "codon" in result.stdout.lower()
        ), f"Unexpected version output: {result.stdout}"

    def test_codon_compilation_basic(self, codon_runner):
        """Test basic Codon compilation"""
        # Create a simple Codon test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def test_function():
    return "Hello from Codon!"

def add_numbers(a: int, b: int) -> int:
    return a + b
"""
            )
            test_file = Path(f.name)

        try:
            result = codon_runner.compile_codon_file(test_file)
            codon_runner.assert_compilation_success(result, "Basic compilation failed")
        finally:
            test_file.unlink(missing_ok=True)

    def test_codon_execution_basic(self, codon_runner):
        """Test basic Codon execution"""
        # Create a simple Codon test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def main():
    print("Hello from Codon!")
    return 0

if __name__ == "__main__":
    main()
"""
            )
            test_file = Path(f.name)

        try:
            result = codon_runner.run_codon_file(test_file)
            codon_runner.assert_compilation_success(result, "Basic execution failed")
            assert "Hello from Codon!" in result.stdout
        finally:
            test_file.unlink(missing_ok=True)

    def test_codon_compilation_error_handling(self, codon_runner):
        """Test Codon compilation error handling"""
        # Create a Codon file with actual syntax errors
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def test_function():
    return "Hello from Codon!"
    # Intentional syntax error - undefined variable
    undefined_variable + 1
    return "This should not execute"
"""
            )
            test_file = Path(f.name)

        try:
            result = codon_runner.compile_codon_file(test_file)
            codon_runner.assert_compilation_failure(
                result, "Expected compilation to fail"
            )

            # Test error parsing
            error_info = CodonErrorHandler.parse_compilation_error(result.stderr)
            assert error_info["message"] is not None
        finally:
            test_file.unlink(missing_ok=True)

    def test_environment_manager(self, virtual_environment):
        """Test Codon environment manager"""
        env_manager = create_environment_manager(Path(virtual_environment))

        with env_manager as env_vars:
            assert env_vars["CODON_PYTHON"] == virtual_environment
            assert env_vars["PYTHONNOUSERSITE"] == "True"

    def test_codon_runner_timeout_handling(self, codon_runner):
        """Test Codon runner timeout handling"""
        # Test with a very short timeout
        result = codon_runner.run_codon(["--help"], timeout=0.001)
        assert not result.success
        assert "timed out" in result.stderr

    def test_codon_runner_error_handling(self, codon_runner):
        """Test Codon runner error handling"""
        # Test with invalid arguments
        result = codon_runner.run_codon(["--invalid-flag"])
        assert not result.success
        assert result.return_code != 0

    def test_codon_error_handler(self):
        """Test Codon error handler utilities"""
        # Test compilation error detection
        fake_result = type(
            "obj",
            (object,),
            {"success": False, "stderr": "compilation error: syntax error at line 5"},
        )()

        assert CodonErrorHandler.is_compilation_error(fake_result)

        # Test runtime error detection
        fake_runtime_result = type(
            "obj",
            (object,),
            {
                "success": False,
                "return_code": 1,
                "stderr": "runtime error: division by zero",
            },
        )()

        assert CodonErrorHandler.is_runtime_error(fake_runtime_result)

    def test_codon_test_file_creation(self, codon_test_file):
        """Test that Codon test files can be created"""
        assert codon_test_file.exists()
        content = codon_test_file.read_text()
        assert "def test_function()" in content
        assert "def add_numbers" in content
        assert "def fibonacci" in content

    def test_virtual_environment_isolation(self, virtual_environment):
        """Test virtual environment isolation"""
        python_executable = virtual_environment
        assert "codon-dev-env" in python_executable
        assert Path(python_executable).exists()

    def test_codon_environment_variables(self, codon_test_environment):
        """Test Codon environment variables are set correctly"""
        env_vars = codon_test_environment
        assert env_vars["codon_cli_path"].exists()
        assert env_vars["python_path"] is not None


class TestCodonInfrastructureIntegration:
    """Integration tests for Codon testing infrastructure"""

    def test_end_to_end_codon_workflow(self, codon_runner, codon_test_file):
        """Test complete Codon workflow from compilation to execution"""
        # Step 1: Compile the test file
        result = codon_runner.compile_codon_file(codon_test_file)
        codon_runner.assert_compilation_success(result, "Compilation failed")

        # Step 2: Run the compiled file
        result = codon_runner.run_codon_file(codon_test_file)
        codon_runner.assert_compilation_success(result, "Execution failed")

        # Step 3: Verify output contains expected content
        assert result.stdout is not None

    def test_codon_performance_basic(self, codon_runner, codon_test_file):
        """Test basic performance characteristics of Codon operations"""
        # Test compilation performance
        result = codon_runner.compile_codon_file(codon_test_file)
        codon_runner.assert_compilation_success(
            result, "Performance test compilation failed"
        )

        # Verify reasonable execution time (should be under 10 seconds for simple file)
        assert (
            result.execution_time < 10.0
        ), f"Compilation took too long: {result.execution_time}s"

        # Test execution performance
        result = codon_runner.run_codon_file(codon_test_file)
        codon_runner.assert_compilation_success(
            result, "Performance test execution failed"
        )

        # Verify reasonable execution time
        assert (
            result.execution_time < 5.0
        ), f"Execution took too long: {result.execution_time}s"


@pytest.mark.codon
class TestCodonSpecificFeatures:
    """Tests for Codon-specific features"""

    def test_codon_python_interoperability(self, codon_runner):
        """Test Codon-Python interoperability features"""
        # Create a test file that uses Python interoperability
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from python import json

def test_json_parsing():
    data = json.loads('{"test": "value"}')
    return data["test"]

def main():
    result = test_json_parsing()
    print(f"Result: {result}")
    return 0

if __name__ == "__main__":
    main()
"""
            )
            test_file = Path(f.name)

        try:
            result = codon_runner.run_codon_file(test_file)
            codon_runner.assert_compilation_success(
                result, "Python interoperability failed"
            )
            assert "Result: value" in result.stdout
        finally:
            test_file.unlink(missing_ok=True)

    def test_codon_error_recovery(self, codon_runner):
        """Test Codon error recovery mechanisms"""
        # Create a file with intentional errors
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def test_function():
    # Intentional error
    undefined_variable + 1
    return "This should not execute"

def main():
    test_function()
    return 0

if __name__ == "__main__":
    main()
"""
            )
            test_file = Path(f.name)

        try:
            result = codon_runner.run_codon_file(test_file)
            codon_runner.assert_compilation_failure(result, "Expected error handling")

            # Verify error information is captured
            error_info = CodonErrorHandler.parse_compilation_error(result.stderr)
            assert error_info["message"] is not None
        finally:
            test_file.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
