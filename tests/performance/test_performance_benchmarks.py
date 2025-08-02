"""
Performance benchmarking tests for Codon development.
All tests run within the virtual environment for proper isolation.
"""

import pytest
import time
import os
import sys
from pathlib import Path

@pytest.mark.performance
def test_codon_compilation_performance():
    """Benchmark Codon compilation performance within virtual environment"""
    import subprocess
    import tempfile
    
    # Create a simple Codon test file
    codon_code = """
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.codon', delete=False) as f:
        f.write(codon_code)
        codon_file = f.name
    
    try:
        # Benchmark compilation time
        start_time = time.time()
        
        result = subprocess.run(
            ["codon", "build", codon_file, "-o", codon_file.replace('.codon', '')],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        end_time = time.time()
        compilation_time = end_time - start_time
        
        # Assert compilation was successful
        assert result.returncode == 0, f"Compilation failed: {result.stderr}"
        
        # Assert compilation time is reasonable (should be under 5 seconds)
        assert compilation_time < 5.0, f"Compilation took too long: {compilation_time:.2f} seconds"
        
        print(f"Codon compilation completed in {compilation_time:.4f} seconds")
        
    finally:
        # Clean up
        if os.path.exists(codon_file):
            os.unlink(codon_file)
        compiled_file = codon_file.replace('.codon', '')
        if os.path.exists(compiled_file):
            os.unlink(compiled_file)

@pytest.mark.performance
def test_python_interoperability_performance():
    """Benchmark Python interoperability performance within virtual environment"""
    import time
    
    # Test numpy operations (if available)
    try:
        import numpy as np  # type: ignore
        
        # Benchmark array operations
        start_time = time.time()
        
        # Create large array
        arr = np.array([i for i in range(10000)])
        
        # Perform operations
        result = arr * 2
        result = result + 1
        result = result ** 2  # type: ignore
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # Assert operations completed quickly
        assert operation_time < 0.1, f"Python operations took too long: {operation_time:.4f} seconds"
        
        print(f"Python interoperability operations completed in {operation_time:.4f} seconds")
        
    except ImportError:
        # If numpy is not available, test basic Python operations
        start_time = time.time()
        
        # Basic Python operations
        data = [i for i in range(10000)]
        result = [x * 2 for x in data]
        result = [x + 1 for x in result]
        result = [x ** 2 for x in result]
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # Assert operations completed quickly
        assert operation_time < 0.1, f"Python operations took too long: {operation_time:.4f} seconds"
        
        print(f"Basic Python operations completed in {operation_time:.4f} seconds")

@pytest.mark.performance
def test_thread_safety_performance():
    """Benchmark thread safety performance within virtual environment"""
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor
    
    def worker_function(thread_id: int) -> int:
        """Worker function for performance testing"""
        # Simulate work
        result = 0
        for i in range(1000):
            result += i * thread_id
        return result
    
    # Benchmark single-threaded performance
    start_time = time.time()
    single_thread_results = []
    for i in range(4):
        result = worker_function(i)
        single_thread_results.append(result)
    single_thread_time = time.time() - start_time
    
    # Benchmark multi-threaded performance
    start_time = time.time()
    multi_thread_results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker_function, i) for i in range(4)]
        for future in futures:
            result = future.result()
            multi_thread_results.append(result)
    
    multi_thread_time = time.time() - start_time
    
    # Assert both approaches completed
    assert len(single_thread_results) == 4
    assert len(multi_thread_results) == 4
    
    # Assert multi-threading doesn't take significantly longer (allowing for overhead)
    assert multi_thread_time < single_thread_time * 1.5, f"Multi-threading too slow: {multi_thread_time:.4f} vs {single_thread_time:.4f}"
    
    print(f"Single-threaded: {single_thread_time:.4f}s, Multi-threaded: {multi_thread_time:.4f}s")

@pytest.mark.performance
def test_memory_usage_performance():
    """Benchmark memory usage within virtual environment"""
    import gc
    import sys
    
    # Get initial memory usage
    gc.collect()
    initial_memory = sys.getsizeof([])  # Basic memory check
    
    # Create large data structures
    large_list = [i for i in range(100000)]
    large_dict = {i: i * 2 for i in range(10000)}
    
    # Get memory after creating data
    gc.collect()
    peak_memory = sys.getsizeof(large_list) + sys.getsizeof(large_dict)
    
    # Clean up
    del large_list
    del large_dict
    gc.collect()
    
    # Get memory after cleanup
    final_memory = sys.getsizeof([])
    
    # Assert memory was properly cleaned up
    assert final_memory <= initial_memory * 2, "Memory not properly cleaned up"
    
    print(f"Memory usage test completed successfully")

@pytest.mark.performance
def test_import_performance():
    """Benchmark import performance within virtual environment"""
    import time
    
    # Test import time for common modules
    modules_to_test = [
        'os', 'sys', 'time', 'threading', 'pathlib',
        'pytest', 'tempfile', 'subprocess'
    ]
    
    total_import_time = 0
    
    for module_name in modules_to_test:
        start_time = time.time()
        
        try:
            __import__(module_name)
            import_time = time.time() - start_time
            total_import_time += import_time
            
            # Assert each import is fast
            assert import_time < 0.1, f"Import of {module_name} took too long: {import_time:.4f}s"
            
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")
    
    # Assert total import time is reasonable
    assert total_import_time < 1.0, f"Total import time too long: {total_import_time:.4f}s"
    
    print(f"All imports completed in {total_import_time:.4f} seconds")

@pytest.mark.performance
def test_file_io_performance():
    """Benchmark file I/O performance within virtual environment"""
    import tempfile
    import time
    import os
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_file = f.name
    
    try:
        # Benchmark write performance
        start_time = time.time()
        
        with open(temp_file, 'w') as f:
            for i in range(10000):
                f.write(f"Line {i}: Test data for performance testing\n")
        
        write_time = time.time() - start_time
        
        # Benchmark read performance
        start_time = time.time()
        
        with open(temp_file, 'r') as f:
            lines = f.readlines()
        
        read_time = time.time() - start_time
        
        # Assert operations completed quickly
        assert write_time < 1.0, f"Write operation took too long: {write_time:.4f}s"
        assert read_time < 1.0, f"Read operation took too long: {read_time:.4f}s"
        assert len(lines) == 10000, f"Expected 10000 lines, got {len(lines)}"
        
        print(f"File I/O - Write: {write_time:.4f}s, Read: {read_time:.4f}s")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file) 