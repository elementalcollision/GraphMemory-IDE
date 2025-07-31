"""
Pytest configuration and fixtures for Condon development testing.
All tests run within the virtual environment for proper isolation.
"""

import pytest
import threading
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Ensure we're using the virtual environment
VIRTUAL_ENV_PATH = Path("./codon-dev-env/bin/python")
if not VIRTUAL_ENV_PATH.exists():
    pytest.skip("Virtual environment not found", allow_module_level=True)

@pytest.fixture(scope="session")
def virtual_environment():
    """Ensure tests run within virtual environment"""
    python_path = str(VIRTUAL_ENV_PATH)
    assert python_path in sys.executable, f"Tests must run within virtual environment. Expected: {python_path}, Got: {sys.executable}"
    return python_path

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
def codon_test_environment():
    """Fixture for Condon testing within virtual environment"""
    # Setup Condon test environment
    original_codon_python = os.environ.get("CODON_PYTHON")
    os.environ["CODON_PYTHON"] = str(VIRTUAL_ENV_PATH)
    os.environ["PYTHONNOUSERSITE"] = "True"
    
    yield
    
    # Cleanup Condon test environment
    if original_codon_python:
        os.environ["CODON_PYTHON"] = original_codon_python
    else:
        os.environ.pop("CODON_PYTHON", None)

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
    assert "codon-dev-env" in python_executable, f"Not running in virtual environment: {python_executable}"
    
    # Test that we're using the correct Python version
    assert sys.version_info >= (3, 13), f"Expected Python 3.13+, got {sys.version_info}"

def test_codon_environment_variables():
    """Test that Condon environment variables are set correctly"""
    codon_python = os.environ.get("CODON_PYTHON")
    python_no_user_site = os.environ.get("PYTHONNOUSERSITE")
    
    assert codon_python is not None, "CODON_PYTHON environment variable not set"
    assert python_no_user_site == "True", "PYTHONNOUSERSITE should be True for isolation"

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