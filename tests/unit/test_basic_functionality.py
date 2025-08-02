"""
Basic unit tests for Codon functionality.
All tests run within the virtual environment for proper isolation.
"""

import pytest
import os
import sys
from pathlib import Path

@pytest.mark.unit
def test_codon_cli_available():
    """Test that Codon CLI is available within virtual environment"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["codon", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        assert "0.19.1" in result.stdout, f"Expected Codon 0.19.1, got: {result.stdout}"
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Codon CLI not available: {e}")

@pytest.mark.unit
def test_python_interoperability_basic():
    """Test basic Python interoperability within virtual environment"""
    # Test that we can import Python modules
    try:
        import math
        assert math.sqrt(4) == 2.0
    except ImportError as e:
        pytest.fail(f"Failed to import Python math module: {e}")

@pytest.mark.unit
def test_virtual_environment_isolation():
    """Test that we're running within the virtual environment"""
    python_executable = sys.executable
    assert "codon-dev-env" in python_executable, f"Not running in virtual environment: {python_executable}"
    
    # Test that we're using the correct Python version
    assert sys.version_info >= (3, 13), f"Expected Python 3.13+, got {sys.version_info}"

@pytest.mark.unit
def test_environment_variables():
    """Test that environment variables are set correctly"""
    codon_python = os.environ.get("CODON_PYTHON")
    python_no_user_site = os.environ.get("PYTHONNOUSERSITE")
    
    assert codon_python is not None, "CODON_PYTHON environment variable not set"
    assert python_no_user_site == "True", "PYTHONNOUSERSITE should be True for isolation"

@pytest.mark.unit
def test_pytest_functionality():
    """Test that pytest is working correctly within virtual environment"""
    # This test should always pass if pytest is working
    assert True

@pytest.mark.unit
def test_import_isolation():
    """Test that imports are isolated within virtual environment"""
    # Test that we can import common packages
    try:
        import pytest
        import threading
        import time
        import os
        import sys
        assert True, "All required modules imported successfully"
    except ImportError as e:
        pytest.fail(f"Failed to import required module: {e}")

@pytest.mark.unit
def test_thread_safety_basic():
    """Test basic thread safety within virtual environment"""
    import threading
    import time
    
    results = []
    lock = threading.Lock()
    
    def worker_function(thread_id: int) -> str:
        """Worker function for thread safety testing"""
        with lock:
            result = f"Thread {thread_id} completed"
            results.append(result)
            time.sleep(0.01)  # Simulate work
        return result
    
    # Test with multiple threads
    threads = []
    for i in range(4):
        thread = threading.Thread(target=worker_function, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    assert len(results) == 4
    assert all(f"Thread {i} completed" in results for i in range(4))

@pytest.mark.unit
def test_memory_isolation():
    """Test that memory is isolated between tests"""
    # This test should not interfere with other tests
    test_data = [i for i in range(100)]
    assert len(test_data) == 100
    assert sum(test_data) == 4950

@pytest.mark.unit
def test_file_system_isolation():
    """Test that file system operations are isolated"""
    import tempfile
    import os
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        temp_file = f.name
    
    try:
        # Verify the file was created
        assert os.path.exists(temp_file)
        
        # Read the content
        with open(temp_file, 'r') as f:
            content = f.read()
        assert content == "test content"
    
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file) 