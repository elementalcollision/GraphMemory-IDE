"""
Thread safety validation tests for Codon development.
All tests run within the virtual environment for proper isolation.
"""

import pytest
import threading
import time
import os
import sys
import tempfile
import gc
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

@pytest.mark.thread_safety
def test_thread_safety_validation_within_virtual_environment():
    """Test thread safety validation within virtual environment"""
    # Verify we're in virtual environment
    python_executable = sys.executable
    assert "codon-dev-env" in python_executable, f"Not running in virtual environment: {python_executable}"
    
    # Test thread safety with locks
    shared_counter = 0
    lock = threading.Lock()
    
    def worker_function(thread_id: int) -> int:
        nonlocal shared_counter
        for i in range(100):
            with lock:
                shared_counter += 1
                time.sleep(0.001)  # Simulate work
        return thread_id
    
    # Test with multiple threads
    threads = []
    for i in range(4):
        thread = threading.Thread(target=worker_function, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify thread safety
    assert shared_counter == 400, f"Expected 400, got {shared_counter}"
    print(f"Thread safety validation completed successfully")

@pytest.mark.thread_safety
def test_memory_safety_concurrent_operations():
    """Test memory safety in concurrent operations within virtual environment"""
    # Test memory safety with shared data structures
    shared_list = []
    lock = threading.Lock()
    
    def memory_worker(thread_id: int) -> None:
        for i in range(1000):
            with lock:
                shared_list.append(f"Thread{thread_id}-{i}")
    
    # Run concurrent memory operations
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(memory_worker, i) for i in range(4)]
        for future in futures:
            future.result()
    
    # Verify memory safety
    assert len(shared_list) == 4000, f"Expected 4000 items, got {len(shared_list)}"
    
    # Test garbage collection
    gc.collect()
    print(f"Memory safety test completed successfully")

@pytest.mark.thread_safety
def test_concurrent_access_patterns():
    """Test concurrent access patterns within virtual environment"""
    # Test file system concurrent access
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    temp_file.close()
    
    def file_worker(thread_id: int) -> None:
        for i in range(100):
            with open(temp_file.name, 'a') as f:
                f.write(f"Thread{thread_id}-{i}\n")
    
    # Run concurrent file operations
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(file_worker, i) for i in range(4)]
        for future in futures:
            future.result()
    
    # Verify file operations
    with open(temp_file.name, 'r') as f:
        lines = f.readlines()
    
    assert len(lines) == 400, f"Expected 400 lines, got {len(lines)}"
    
    # Cleanup
    os.unlink(temp_file.name)
    print(f"Concurrent access pattern test completed successfully")

@pytest.mark.thread_safety
def test_thread_isolation():
    """Test thread isolation between test cases within virtual environment"""
    # Test that threads don't interfere with each other
    results = {}
    lock = threading.Lock()
    
    def isolated_worker(thread_id: int) -> None:
        local_data = []
        for i in range(100):
            local_data.append(f"Thread{thread_id}-{i}")
        
        with lock:
            results[thread_id] = len(local_data)
    
    # Run isolated threads
    threads = []
    for i in range(4):
        thread = threading.Thread(target=isolated_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify isolation
    assert len(results) == 4, f"Expected 4 thread results, got {len(results)}"
    for thread_id, count in results.items():
        assert count == 100, f"Thread {thread_id} expected 100 items, got {count}"
    
    print(f"Thread isolation test completed successfully")

@pytest.mark.thread_safety
def test_deadlock_detection():
    """Test deadlock detection within virtual environment"""
    import queue
    
    # Test with potential deadlock scenario
    q1 = queue.Queue()
    q2 = queue.Queue()
    
    def worker1():
        try:
            # Try to get from q1, then put to q2
            item = q1.get(timeout=1)
            q2.put(item)
            q1.task_done()
        except queue.Empty:
            pass
    
    def worker2():
        try:
            # Try to get from q2, then put to q1
            item = q2.get(timeout=1)
            q1.put(item)
            q2.task_done()
        except queue.Empty:
            pass
    
    # Start threads with timeout to prevent actual deadlock
    thread1 = threading.Thread(target=worker1)
    thread2 = threading.Thread(target=worker2)
    
    thread1.start()
    thread2.start()
    
    # Wait with timeout
    thread1.join(timeout=2)
    thread2.join(timeout=2)
    
    # Verify threads completed (no deadlock)
    assert not thread1.is_alive(), "Thread1 did not complete (potential deadlock)"
    assert not thread2.is_alive(), "Thread2 did not complete (potential deadlock)"
    
    print(f"Deadlock detection test completed successfully")

@pytest.mark.thread_safety
def test_memory_leak_detection():
    """Test memory leak detection in threaded code within virtual environment"""
    import weakref
    
    # Track object references
    tracked_objects = []
    
    def memory_worker(thread_id: int) -> None:
        local_objects = []
        for i in range(100):
            # Use a custom class that can have weak references
            class TrackableObject:
                def __init__(self, thread_id, index, data):
                    self.thread_id = thread_id
                    self.index = index
                    self.data = data
            
            obj = TrackableObject(thread_id, i, "x" * 100)
            local_objects.append(obj)
        
        # Add weak references to track
        with threading.Lock():
            for obj in local_objects:
                tracked_objects.append(weakref.ref(obj))
    
    # Run memory workers
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(memory_worker, i) for i in range(4)]
        for future in futures:
            future.result()
    
    # Force garbage collection
    gc.collect()
    
    # Check for memory leaks (weak references should be dead)
    alive_refs = [ref for ref in tracked_objects if ref() is not None]
    assert len(alive_refs) == 0, f"Memory leak detected: {len(alive_refs)} objects still alive"
    
    print(f"Memory leak detection test completed successfully")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-m", "thread_safety"]) 