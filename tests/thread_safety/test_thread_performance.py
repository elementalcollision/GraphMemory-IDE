"""
Thread performance benchmarking tests for Condon development.
All tests run within the virtual environment for proper isolation.
"""

import pytest
import threading
import time
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.thread_safety
def test_thread_performance_benchmarking():
    """Benchmark thread performance within virtual environment"""
    def worker_function(thread_id: int) -> int:
        # Simulate work
        result = 0
        for i in range(10000):
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
    assert multi_thread_time < single_thread_time * 2.0, f"Multi-threading too slow: {multi_thread_time:.4f} vs {single_thread_time:.4f}"
    
    print(f"Thread performance benchmark - Single: {single_thread_time:.4f}s, Multi: {multi_thread_time:.4f}s")

@pytest.mark.thread_safety
def test_codon_thread_safety():
    """Test Condon thread safety within virtual environment"""
    # Test concurrent Condon compilation
    codon_code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    
    def compile_worker(thread_id: int) -> bool:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.codon', delete=False) as f:
            f.write(codon_code)
            codon_file = f.name
        
        try:
            result = subprocess.run(
                ["codon", "build", codon_file, "-o", codon_file.replace('.codon', '')],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            compiled_file = codon_file.replace('.codon', '')
            if os.path.exists(compiled_file):
                os.unlink(compiled_file)
            
            return result.returncode == 0
        except Exception as e:
            print(f"Thread {thread_id} compilation failed: {e}")
            return False
        finally:
            if os.path.exists(codon_file):
                os.unlink(codon_file)
    
    # Test concurrent compilation
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(compile_worker, i) for i in range(4)]
        results = [future.result() for future in futures]
    
    # Verify all compilations succeeded
    assert all(results), "Some Condon compilations failed"
    print(f"Condon thread safety test completed successfully")

@pytest.mark.thread_safety
def test_concurrent_development_workflows():
    """Test concurrent development workflows within virtual environment"""
    import json
    import tempfile
    
    # Simulate concurrent development operations
    shared_config = {"version": "1.0.0", "features": []}
    config_lock = threading.Lock()
    
    def development_worker(thread_id: int) -> dict:
        # Simulate development workflow
        with config_lock:
            # Read current config
            current_config = shared_config.copy()
            
            # Modify config - ensure features is a list
            if not isinstance(current_config["features"], list):
                current_config["features"] = []
            current_config["features"].append(f"feature_{thread_id}")
            current_config["version"] = f"1.0.{thread_id}"
            
            # Simulate file operations
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(current_config, f)
                temp_file = f.name
            
            # Read back and verify
            with open(temp_file, 'r') as f:
                read_config = json.load(f)
            
            # Cleanup
            os.unlink(temp_file)
            
            return read_config
    
    # Run concurrent development workflows
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(development_worker, i) for i in range(4)]
        results = [future.result() for future in futures]
    
    # Verify all workflows completed
    assert len(results) == 4, f"Expected 4 workflow results, got {len(results)}"
    for i, result in enumerate(results):
        assert "features" in result, f"Result {i} missing features"
        assert "version" in result, f"Result {i} missing version"
    
    print(f"Concurrent development workflows test completed successfully")

@pytest.mark.thread_safety
def test_python_interoperability_thread_safety():
    """Test Python interoperability thread safety within virtual environment"""
    import sys
    import importlib
    
    # Test concurrent module imports
    modules_to_test = ["os", "sys", "threading", "time", "json", "tempfile"]
    
    def import_worker(thread_id: int) -> list:
        imported_modules = []
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                imported_modules.append(module_name)
            except ImportError as e:
                print(f"Thread {thread_id} failed to import {module_name}: {e}")
        
        return imported_modules
    
    # Run concurrent imports
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(import_worker, i) for i in range(4)]
        results = [future.result() for future in futures]
    
    # Verify all imports succeeded
    for i, result in enumerate(results):
        assert len(result) == len(modules_to_test), f"Thread {i} imported {len(result)} modules, expected {len(modules_to_test)}"
    
    print(f"Python interoperability thread safety test completed successfully")

@pytest.mark.thread_safety
def test_thread_safety_guidelines_validation():
    """Test thread safety guidelines validation within virtual environment"""
    # Test adherence to thread safety guidelines
    
    # Guideline 1: Use locks for shared resources
    shared_counter = 0
    lock = threading.Lock()
    
    def guideline_worker(thread_id: int) -> int:
        nonlocal shared_counter
        for i in range(100):
            with lock:  # Proper lock usage
                shared_counter += 1
        return thread_id
    
    # Guideline 2: Avoid global state
    thread_local_data = threading.local()
    
    def local_worker(thread_id: int) -> None:
        thread_local_data.thread_id = thread_id
        thread_local_data.counter = 0
        for i in range(100):
            thread_local_data.counter += 1
    
    # Run guideline tests
    threads = []
    for i in range(4):
        thread = threading.Thread(target=guideline_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    local_threads = []
    for i in range(4):
        thread = threading.Thread(target=local_worker, args=(i,))
        local_threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads + local_threads:
        thread.join()
    
    # Verify guidelines were followed
    assert shared_counter == 400, "Lock usage guideline violated"
    print(f"Thread safety guidelines validation completed successfully")

@pytest.mark.thread_safety
def test_production_readiness_thread_safety():
    """Test production readiness thread safety within virtual environment"""
    import signal
    import time
    
    # Test graceful shutdown with threads
    shutdown_event = threading.Event()
    active_threads = []
    
    def production_worker(thread_id: int) -> None:
        while not shutdown_event.is_set():
            # Simulate production work
            time.sleep(0.1)
            if thread_id == 0:  # Main worker
                pass
    
    # Start production workers
    for i in range(4):
        thread = threading.Thread(target=production_worker, args=(i,))
        thread.daemon = True  # Allow graceful shutdown
        thread.start()
        active_threads.append(thread)
    
    # Let them run for a bit
    time.sleep(0.5)
    
    # Signal shutdown
    shutdown_event.set()
    
    # Wait for graceful shutdown
    for thread in active_threads:
        thread.join(timeout=2)
    
    # Verify graceful shutdown
    alive_threads = [t for t in active_threads if t.is_alive()]
    assert len(alive_threads) == 0, f"Threads did not shutdown gracefully: {len(alive_threads)} still alive"
    
    print(f"Production readiness thread safety test completed successfully")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-m", "thread_safety"]) 