"""
Pytest configuration and fixtures for Codon development testing.
All tests run within the virtual environment for proper isolation.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pytest

# Ensure we're using the virtual environment
VIRTUAL_ENV_PATH = Path("./codon-dev-env/bin/python")
if not VIRTUAL_ENV_PATH.exists():
    pytest.skip("Virtual environment not found", allow_module_level=True)


@dataclass
class CodonTestResult:
    """Result of Codon CLI operation"""

    success: bool
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: List[str]


@pytest.fixture(scope="session")
def virtual_environment():
    """Ensure tests run within virtual environment"""
    python_path = str(VIRTUAL_ENV_PATH)
    expected_msg = f"Tests must run within virtual environment. Expected: {python_path}, Got: {sys.executable}"
    assert python_path in sys.executable, expected_msg
    return python_path


@pytest.fixture(scope="session")
def codon_cli_path():
    """Get the path to the Codon CLI executable"""
    # Check if codon is available in the virtual environment
    codon_path = Path("./codon-dev-env/bin/codon")
    if not codon_path.exists():
        # Try to find codon in PATH
        try:
            result = subprocess.run(
                ["which", "codon"], capture_output=True, text=True, check=True
            )
            codon_path = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            pytest.skip("Codon CLI not found in virtual environment or PATH")

    assert codon_path.exists(), f"Codon CLI not found at {codon_path}"
    return codon_path


@pytest.fixture(scope="function")
def codon_test_environment(codon_cli_path):
    """Fixture for Codon testing within virtual environment"""
    # Setup Codon test environment
    original_codon_python = os.environ.get("CODON_PYTHON")
    original_python_no_user_site = os.environ.get("PYTHONNOUSERSITE")

    os.environ["CODON_PYTHON"] = str(VIRTUAL_ENV_PATH)
    os.environ["PYTHONNOUSERSITE"] = "True"
    os.environ["CODON_CLI_PATH"] = str(codon_cli_path)

    yield {"codon_cli_path": codon_cli_path, "python_path": str(VIRTUAL_ENV_PATH)}

    # Cleanup Codon test environment
    if original_codon_python:
        os.environ["CODON_PYTHON"] = original_codon_python
    else:
        os.environ.pop("CODON_PYTHON", None)

    if original_python_no_user_site:
        os.environ["PYTHONNOUSERSITE"] = original_python_no_user_site
    else:
        os.environ.pop("PYTHONNOUSERSITE", None)

    os.environ.pop("CODON_CLI_PATH", None)


@pytest.fixture(scope="function")
def codon_runner(codon_test_environment):
    """Fixture providing Codon CLI runner utilities"""

    class CodonRunner:
        def __init__(self, cli_path: Path, python_path: str):
            self.cli_path = cli_path
            self.python_path = python_path
            self.last_result: Optional[CodonTestResult] = None

        def run_codon(
            self, args: List[str], timeout: float = 30.0
        ) -> CodonTestResult:
            """Run Codon CLI command and return result"""
            command = [str(self.cli_path)] + args
            start_time = time.time()

            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env={
                        **os.environ,
                        "CODON_PYTHON": self.python_path,
                        "PYTHONNOUSERSITE": "True",
                    },
                )

                execution_time = time.time() - start_time

                self.last_result = CodonTestResult(
                    success=result.returncode == 0,
                    return_code=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    execution_time=execution_time,
                    command=command,
                )

                return self.last_result

            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                self.last_result = CodonTestResult(
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    execution_time=execution_time,
                    command=command,
                )
                return self.last_result

            except Exception as e:
                execution_time = time.time() - start_time
                self.last_result = CodonTestResult(
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr=str(e),
                    execution_time=execution_time,
                    command=command,
                )
                return self.last_result

        def compile_codon_file(
            self, source_file: Path, output_file: Optional[Path] = None
        ) -> CodonTestResult:
            """Compile a Codon source file"""
            args = ["build", str(source_file)]
            if output_file:
                args.extend(["-o", str(output_file)])
            return self.run_codon(args)

        def run_codon_file(self, source_file: Path, *args) -> CodonTestResult:
            """Run a Codon source file directly"""
            cmd_args = ["run", str(source_file)] + list(args)
            return self.run_codon(cmd_args)

        def check_codon_version(self) -> CodonTestResult:
            """Check Codon version"""
            return self.run_codon(["--version"])

        def assert_compilation_success(
            self, result: CodonTestResult, error_msg: str = "Codon compilation failed"
        ):
            """Assert that Codon compilation was successful"""
            assert result.success, f"{error_msg}: {result.stderr}"
            assert (
                result.return_code == 0
            ), f"{error_msg}: return code {result.return_code}"

        def assert_compilation_failure(
            self, result: CodonTestResult, expected_error: Optional[str] = None
        ):
            """Assert that Codon compilation failed as expected"""
            assert (
                not result.success
            ), f"Expected compilation to fail, but it succeeded: {result.stdout}"
            if expected_error:
                assert (
                    expected_error in result.stderr
                ), f"Expected error '{expected_error}' not found in: {result.stderr}"

    return CodonRunner(
        codon_test_environment["codon_cli_path"],
        codon_test_environment["python_path"],
    )


@pytest.fixture(scope="function")
def thread_safety_fixture():
    """Fixture for thread safety testing within virtual environment"""
    # Setup thread-safe test environment
    original_threading_excepthook = threading.excepthook

    def custom_excepthook(args):
        # Custom exception handler for thread safety testing
        print(f"Thread exception: {args.exc_type.__name__}: {args.exc_value}")

    threading.excepthook = custom_excepthook

    yield

    # Cleanup thread-safe test environment
    threading.excepthook = original_threading_excepthook


@pytest.fixture(scope="function")
def performance_test_environment():
    """Fixture for performance testing within virtual environment"""
    # Setup performance test environment
    start_time = time.time()

    yield start_time

    # Cleanup performance test environment
    end_time = time.time()
    print(f"Performance test duration: {end_time - start_time:.4f} seconds")


@pytest.fixture(scope="function")
def isolated_test_environment():
    """Fixture for isolated test environment within virtual environment"""
    # Setup isolated test environment
    original_env = dict(os.environ)

    # Set test-specific environment variables
    os.environ["PYTHONPATH"] = str(Path("./codon-dev-env/lib/python3.13/site-packages"))
    os.environ["TESTING"] = "True"

    yield

    # Cleanup isolated test environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="function")
def temp_codon_project():
    """Fixture providing a temporary directory for Codon project testing"""
    temp_dir = Path(tempfile.mkdtemp(prefix="codon_test_"))

    # Create basic project structure
    (temp_dir / "src").mkdir(exist_ok=True)
    (temp_dir / "tests").mkdir(exist_ok=True)

    yield temp_dir

    # Cleanup temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def codon_test_file(temp_codon_project):
    """Fixture providing a temporary Codon test file"""
    test_file = temp_codon_project / "src" / "test_module.py"

    # Create a simple Codon test file
    test_content = """
def test_function():
    return "Hello from Codon!"

def add_numbers(a: int, b: int) -> int:
    return a + b

def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""

    test_file.write_text(test_content)
    return test_file


def test_thread_safety_within_virtual_environment():
    """Test thread safety within virtual environment"""
    results = []
    lock = threading.Lock()

    def worker_function(thread_id):
        # Test function that runs in thread
        with lock:
            result = f"Thread {thread_id} completed"
            results.append(result)
            time.sleep(0.01)  # Simulate work
        return result

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker_function, i) for i in range(4)]
        for future in futures:
            future.result()

    assert len(results) == 4
    assert all(f"Thread {i} completed" in results for i in range(4))


def test_virtual_environment_isolation():
    """Test that we're running within the virtual environment"""
    python_executable = sys.executable
    assert (
        "codon-dev-env" in python_executable
    ), f"Not running in virtual environment: {python_executable}"

    # Test that we're using the correct Python version
    assert sys.version_info >= (3, 13), f"Expected Python 3.13+, got {sys.version_info}"


def test_codon_environment_variables():
    """Test that Codon environment variables are set correctly"""
    codon_python = os.environ.get("CODON_PYTHON")
    python_no_user_site = os.environ.get("PYTHONNOUSERSITE")

    assert codon_python is not None, "CODON_PYTHON environment variable not set"
    assert (
        python_no_user_site == "True"
    ), "PYTHONNOUSERSITE should be True for isolation"


def test_codon_cli_availability(codon_runner):
    """Test that Codon CLI is available and working"""
    result = codon_runner.check_codon_version()
    assert result.success, f"Codon CLI not working: {result.stderr}"
    assert (
        "codon" in result.stdout.lower()
    ), f"Unexpected version output: {result.stdout}"


def test_codon_compilation_basic(codon_runner, codon_test_file):
    """Test basic Codon compilation"""
    result = codon_runner.compile_codon_file(codon_test_file)
    codon_runner.assert_compilation_success(result, "Basic Codon compilation failed")


def test_codon_execution_basic(codon_runner, codon_test_file):
    """Test basic Codon execution"""
    result = codon_runner.run_codon_file(codon_test_file)
    codon_runner.assert_compilation_success(result, "Basic Codon execution failed")


@pytest.fixture(scope="function")
def benchmark_fixture():
    """Fixture for benchmarking tests within virtual environment"""
    import time

    class BenchmarkTimer:
        def __init__(self):
            self.start_time: float | None = None
            self.end_time: float | None = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.end_time = time.time()

        @property
        def duration(self) -> float | None:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return BenchmarkTimer()
