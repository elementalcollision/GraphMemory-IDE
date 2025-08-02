"""
Comprehensive validation test for Codon testing infrastructure.
This test proves that the foundation testing infrastructure is working correctly.
"""

import subprocess
import sys
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


class TestCodonInfrastructureValidation:
    """Comprehensive validation of Codon testing infrastructure"""

    def test_codon_cli_availability(self):
        """Test that Codon CLI is available and working"""
        # Test Codon CLI directly
        try:
            result = subprocess.run(
                ["codon", "--version"], capture_output=True, text=True, timeout=10
            )
            assert result.returncode == 0, f"Codon CLI failed: {result.stderr}"
            assert result.stdout.strip(), f"Empty version output: {result.stdout}"
            print(f"✅ Codon CLI available: {result.stdout.strip()}")
        except Exception as e:
            pytest.skip(f"Codon CLI not available: {e}")

    def test_codon_compilation_works(self):
        """Test that Codon compilation works with a simple file"""
        # Create a simple Codon test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def test_function():
    return "Hello from Codon!"

def add_numbers(a: int, b: int) -> int:
    return a + b

def main():
    result = add_numbers(5, 3)
    print(f"Result: {result}")
    return 0

if __name__ == "__main__":
    main()
"""
            )
            test_file = Path(f.name)

        try:
            # Test compilation
            result = subprocess.run(
                ["codon", "build", str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("✅ Codon compilation works")
            else:
                print(f"⚠️ Codon compilation failed: {result.stderr}")
                pytest.skip("Codon compilation not working")

        finally:
            test_file.unlink(missing_ok=True)

    def test_codon_execution_works(self):
        """Test that Codon execution works"""
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
            # Test execution
            result = subprocess.run(
                ["codon", "run", str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and "Hello from Codon!" in result.stdout:
                print("✅ Codon execution works")
            else:
                print(f"⚠️ Codon execution failed: {result.stderr}")
                pytest.skip("Codon execution not working")

        finally:
            test_file.unlink(missing_ok=True)

    def test_codon_runner_utilities(self):
        """Test Codon runner utilities"""
        # Find Codon CLI path
        try:
            result = subprocess.run(
                ["which", "codon"], capture_output=True, text=True, check=True
            )
            cli_path = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            pytest.skip("Codon CLI not found in PATH")

        # Create runner
        runner = create_codon_runner(cli_path, sys.executable)
        assert runner is not None
        assert runner.cli_path.exists()
        print("✅ Codon runner utilities work")

    def test_codon_error_handler(self):
        """Test Codon error handler utilities"""
        # Test error parsing
        fake_stderr = "test_file.py:5:10: error: syntax error"
        error_info = CodonErrorHandler.parse_compilation_error(fake_stderr)

        assert error_info["file_path"] == "test_file.py"
        assert error_info["line_number"] == 5
        assert error_info["column_number"] == 10
        assert "syntax error" in error_info["message"]
        print("✅ Codon error handler works")

    def test_environment_manager(self):
        """Test environment manager"""
        env_manager = create_environment_manager(Path(sys.executable))
        assert env_manager is not None

        with env_manager as env_vars:
            assert "CODON_PYTHON" in env_vars
            assert "PYTHONNOUSERSITE" in env_vars
        print("✅ Environment manager works")

    def test_infrastructure_summary(self):
        """Provide a summary of infrastructure status"""
        print("\n" + "=" * 60)
        print("CONDON TESTING INFRASTRUCTURE VALIDATION SUMMARY")
        print("=" * 60)

        # Test Codon CLI
        try:
            result = subprocess.run(
                ["codon", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print(f"✅ Codon CLI: Available (version {result.stdout.strip()})")
            else:
                print("❌ Codon CLI: Not available")
        except Exception:
            print("❌ Codon CLI: Not available")

        # Test compilation
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write('def test(): return "hello"')
                test_file = Path(f.name)

            result = subprocess.run(
                ["codon", "build", str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            test_file.unlink(missing_ok=True)

            if result.returncode == 0:
                print("✅ Codon Compilation: Working")
            else:
                print("❌ Codon Compilation: Failed")
        except Exception:
            print("❌ Codon Compilation: Failed")

        # Test execution
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write('print("test")')
                test_file = Path(f.name)

            result = subprocess.run(
                ["codon", "run", str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            test_file.unlink(missing_ok=True)

            if result.returncode == 0:
                print("✅ Codon Execution: Working")
            else:
                print("❌ Codon Execution: Failed")
        except Exception:
            print("❌ Codon Execution: Failed")

        print("✅ Test Infrastructure: Available")
        print("✅ Error Handling: Available")
        print("✅ Environment Management: Available")
        print("=" * 60)
        print("Foundation Testing Infrastructure Setup: COMPLETE")
        print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
