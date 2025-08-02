# Thread Safety Guidelines and Documentation

## Overview
This document provides comprehensive guidelines for developing thread-safe code within the Codon virtual environment. These guidelines ensure that concurrent operations are safe, predictable, and production-ready.

## Core Principles

### 1. Thread Isolation
- **Always isolate thread-specific data**: Use `threading.local()` for thread-local storage
- **Avoid global mutable state**: Minimize shared state between threads
- **Use immutable data structures**: Prefer immutable objects for shared data

### 2. Proper Synchronization
- **Use locks for shared resources**: Always protect shared data with appropriate locks
- **Acquire locks in consistent order**: Prevent deadlocks by always acquiring locks in the same order
- **Keep critical sections small**: Minimize the time spent holding locks
- **Use context managers**: Always use `with lock:` syntax for automatic cleanup

### 3. Memory Safety
- **Clean up resources**: Ensure proper cleanup in finally blocks
- **Avoid memory leaks**: Use weak references for tracking objects
- **Monitor garbage collection**: Regularly check for memory leaks in threaded code
- **Use thread-safe data structures**: Prefer `queue.Queue` over custom implementations

## Best Practices

### Lock Usage
```python
# ✅ CORRECT: Use context manager for locks
lock = threading.Lock()
with lock:
    shared_data.append(item)

# ❌ INCORRECT: Manual lock management
lock.acquire()
try:
    shared_data.append(item)
finally:
    lock.release()
```

### Thread-Local Storage
```python
# ✅ CORRECT: Use thread-local storage
thread_local = threading.local()

def worker():
    thread_local.counter = 0
    for i in range(100):
        thread_local.counter += 1

# ❌ INCORRECT: Global mutable state
global_counter = 0  # This is not thread-safe
```

### Resource Management
```python
# ✅ CORRECT: Proper resource cleanup
def safe_file_operation():
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # File operations
        with open(temp_file.name, 'w') as f:
            f.write("data")
    finally:
        # Always cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
```

## Common Patterns

### Producer-Consumer Pattern
```python
import queue
import threading

# Thread-safe queue
task_queue = queue.Queue()

def producer():
    for i in range(100):
        task_queue.put(f"task_{i}")

def consumer():
    while True:
        try:
            task = task_queue.get(timeout=1)
            # Process task
            task_queue.task_done()
        except queue.Empty:
            break

# Start workers
threads = []
for i in range(4):
    thread = threading.Thread(target=consumer)
    thread.start()
    threads.append(thread)

# Wait for completion
task_queue.join()
```

### Thread Pool Pattern
```python
from concurrent.futures import ThreadPoolExecutor

def worker_function(data):
    # Process data
    return processed_result

# Use ThreadPoolExecutor for managed thread pools
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(worker_function, data) for data in data_list]
    results = [future.result() for future in futures]
```

## Error Handling

### Deadlock Prevention
```python
# ✅ CORRECT: Consistent lock ordering
def safe_operation():
    with lock1:
        with lock2:
            # Critical section
            pass

# ❌ INCORRECT: Inconsistent lock ordering can cause deadlocks
def unsafe_operation():
    with lock2:
        with lock1:  # Different order!
            pass
```

### Timeout Handling
```python
# ✅ CORRECT: Use timeouts to prevent infinite waits
def safe_get_with_timeout(queue_obj, timeout=1):
    try:
        return queue_obj.get(timeout=timeout)
    except queue.Empty:
        return None
```

### Exception Safety
```python
# ✅ CORRECT: Exception-safe thread operations
def safe_thread_operation():
    try:
        # Thread operations
        result = perform_operation()
        return result
    except Exception as e:
        # Log error and handle gracefully
        logger.error(f"Thread operation failed: {e}")
        return None
    finally:
        # Always cleanup
        cleanup_resources()
```

## Testing Guidelines

### Thread Safety Testing
```python
import pytest
import threading
import time

@pytest.mark.thread_safety
def test_thread_safety():
    shared_counter = 0
    lock = threading.Lock()
    
    def worker():
        nonlocal shared_counter
        for i in range(100):
            with lock:
                shared_counter += 1
    
    # Start multiple threads
    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # Verify thread safety
    assert shared_counter == 400
```

### Memory Leak Testing
```python
import weakref
import gc

def test_memory_safety():
    tracked_objects = []
    
    def memory_worker():
        obj = {"data": "x" * 1000}
        tracked_objects.append(weakref.ref(obj))
    
    # Run workers
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(memory_worker) for _ in range(4)]
        for future in futures:
            future.result()
    
    # Force garbage collection
    gc.collect()
    
    # Check for memory leaks
    alive_refs = [ref for ref in tracked_objects if ref() is not None]
    assert len(alive_refs) == 0, "Memory leak detected"
```

## Performance Considerations

### Thread Pool Sizing
- **CPU-bound tasks**: Use `max_workers = CPU_count`
- **I/O-bound tasks**: Use `max_workers = CPU_count * 2`
- **Monitor thread usage**: Avoid creating too many threads

### Lock Contention
- **Minimize lock scope**: Keep critical sections as small as possible
- **Use read-write locks**: For read-heavy workloads
- **Consider lock-free data structures**: When appropriate

### Memory Usage
- **Monitor memory per thread**: Each thread has overhead
- **Use thread pools**: Reuse threads instead of creating new ones
- **Profile memory usage**: Regularly check for memory leaks

## Production Readiness

### Graceful Shutdown
```python
import threading
import time

class ThreadManager:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.threads = []
    
    def start_workers(self, num_workers):
        for i in range(num_workers):
            thread = threading.Thread(target=self.worker, args=(i,))
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
    
    def worker(self, worker_id):
        while not self.shutdown_event.is_set():
            # Do work
            time.sleep(0.1)
    
    def shutdown(self, timeout=5):
        self.shutdown_event.set()
        for thread in self.threads:
            thread.join(timeout=timeout)
```

### Monitoring and Logging
```python
import logging
import threading

# Thread-safe logging
logger = logging.getLogger(__name__)

def thread_safe_operation():
    thread_id = threading.current_thread().ident
    logger.info(f"Thread {thread_id} starting operation")
    
    try:
        # Operation
        result = perform_operation()
        logger.info(f"Thread {thread_id} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Thread {thread_id} failed: {e}")
        raise
```

## Virtual Environment Considerations

### Environment Isolation
- **Verify virtual environment**: Always check `sys.executable` for virtual environment path
- **Isolate dependencies**: Ensure thread operations don't interfere with environment
- **Clean state**: Reset environment state between thread operations

### Codon Integration
- **Thread-safe compilation**: Ensure Codon compilation is thread-safe
- **Resource management**: Properly manage Codon compiler resources
- **Error isolation**: Prevent Codon errors from affecting other threads

## Checklist for Thread-Safe Code

### Before Implementation
- [ ] Identify shared resources
- [ ] Plan synchronization strategy
- [ ] Design thread-local storage needs
- [ ] Plan error handling approach

### During Implementation
- [ ] Use appropriate locks for shared data
- [ ] Implement proper resource cleanup
- [ ] Add timeout handling
- [ ] Include comprehensive error handling

### After Implementation
- [ ] Write thread safety tests
- [ ] Test memory leak scenarios
- [ ] Verify performance under load
- [ ] Document thread safety guarantees

### Before Production
- [ ] Run comprehensive thread safety tests
- [ ] Verify graceful shutdown behavior
- [ ] Monitor memory usage patterns
- [ ] Test under production-like load

## Common Pitfalls

### ❌ Avoid These Patterns
1. **Global mutable state**: Use thread-local storage instead
2. **Manual lock management**: Always use context managers
3. **Inconsistent lock ordering**: Always acquire locks in the same order
4. **Long critical sections**: Keep lock-held time minimal
5. **Unbounded thread creation**: Use thread pools instead
6. **Ignoring exceptions**: Always handle thread exceptions
7. **Resource leaks**: Always cleanup in finally blocks

### ✅ Use These Patterns
1. **Thread-local storage**: For thread-specific data
2. **Context managers**: For automatic resource management
3. **Thread pools**: For managed concurrency
4. **Timeout handling**: For preventing infinite waits
5. **Exception safety**: For robust error handling
6. **Graceful shutdown**: For production readiness
7. **Comprehensive testing**: For thread safety validation

## Conclusion

Following these guidelines ensures that your threaded code is safe, predictable, and production-ready. Always test thoroughly and monitor performance in production environments.

Remember: Thread safety is not optional - it's essential for reliable concurrent applications. 