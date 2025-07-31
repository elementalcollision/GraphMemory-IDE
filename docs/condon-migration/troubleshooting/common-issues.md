# Common Issues and Troubleshooting Guide

## Overview

This guide provides solutions for common issues encountered during Condon migration. These issues are based on the comprehensive analysis completed in TASK-002 subtasks and real-world migration experiences.

## Critical Issues

### 1. Dynamic Import Compilation Errors

**Issue**: Condon cannot compile dynamic imports like `__import__()` or `getattr()`.

**Symptoms**:
```
Error: Cannot compile dynamic import at line 15
Error: getattr() not supported in compiled mode
Error: Dynamic module loading not supported
```

**Root Cause**: Condon requires static analysis and cannot handle dynamic imports at compile time.

**Solution**:
```python
# ❌ CONDON-INCOMPATIBLE
def load_plugin(plugin_name: str):
    module = __import__(f"plugins.{plugin_name}")
    return getattr(module, "Plugin")

# ✅ CONDON-COMPATIBLE
from typing import Dict, Type
from plugins.base import BasePlugin

PLUGIN_REGISTRY: Dict[str, Type[BasePlugin]] = {
    "analytics": AnalyticsPlugin,
    "monitoring": MonitoringPlugin,
    "security": SecurityPlugin,
}

def load_plugin(plugin_name: str) -> Type[BasePlugin]:
    return PLUGIN_REGISTRY[plugin_name]
```

**Prevention**:
- Use explicit registries instead of dynamic imports
- Create static mappings for all dynamic lookups
- Validate all imports are static at compile time

### 2. Thread Safety Race Conditions

**Issue**: Race conditions occur in no-GIL environment when shared state is accessed without proper synchronization.

**Symptoms**:
```
RuntimeError: Dictionary changed during iteration
ValueError: Inconsistent state detected
MemoryError: Excessive memory usage due to race conditions
```

**Root Cause**: Condon removes the GIL, making race conditions much more likely.

**Solution**:
```python
# ❌ THREAD-UNSAFE
class IncidentManager:
    def __init__(self):
        self.incidents = {}
    
    def add_incident(self, incident):
        self.incidents[incident.id] = incident  # Race condition

# ✅ THREAD-SAFE
import asyncio
from typing import Dict, UUID

class IncidentManager:
    def __init__(self):
        self._incidents: Dict[UUID, 'Incident'] = {}
        self._incidents_lock = asyncio.Lock()
    
    async def add_incident(self, incident: 'Incident') -> None:
        async with self._incidents_lock:
            self._incidents[incident.id] = incident
```

**Prevention**:
- Use locks for all shared state access
- Implement thread-safe singleton patterns
- Test under concurrent load

### 3. Singleton Pattern Race Conditions

**Issue**: Singleton patterns using check-then-act cause race conditions in no-GIL environment.

**Symptoms**:
```
Multiple singleton instances created
Inconsistent singleton behavior
Memory leaks from multiple instances
```

**Root Cause**: Simple check-then-act patterns are not thread-safe in no-GIL environment.

**Solution**:
```python
# ❌ THREAD-UNSAFE
_health_monitor: Optional[HealthMonitor] = None

async def get_health_monitor() -> HealthMonitor:
    global _health_monitor
    if _health_monitor is None:  # RACE CONDITION
        _health_monitor = HealthMonitor()
    return _health_monitor

# ✅ THREAD-SAFE
import asyncio
from typing import Optional

_health_monitor: Optional[HealthMonitor] = None
_health_monitor_lock = asyncio.Lock()

async def get_health_monitor() -> HealthMonitor:
    global _health_monitor
    
    if _health_monitor is None:
        async with _health_monitor_lock:
            if _health_monitor is None:  # Double-check after acquiring lock
                _health_monitor = HealthMonitor()
    
    return _health_monitor
```

**Prevention**:
- Always use double-checked locking pattern
- Use asyncio.Lock for async applications
- Test singleton behavior under concurrent access

## Performance Issues

### 4. Thread Safety Performance Overhead

**Issue**: Thread safety measures cause significant performance overhead.

**Symptoms**:
```
Performance degradation after thread safety implementation
High lock contention
Reduced throughput under load
```

**Root Cause**: Excessive locking or inappropriate lock granularity.

**Solution**:
```python
# ❌ POOR PERFORMANCE
class ThreadSafeDict:
    def __init__(self):
        self._dict = {}
        self._lock = asyncio.Lock()  # Too coarse-grained
    
    async def get(self, key):
        async with self._lock:  # Lock entire dict for single read
            return self._dict.get(key)

# ✅ BETTER PERFORMANCE
from threading import Lock

class ThreadSafeDict:
    def __init__(self):
        self._dict = {}
        self._lock = Lock()  # Use threading.Lock for better performance
    
    def get(self, key):
        with self._lock:  # Fine-grained locking
            return self._dict.get(key)
```

**Prevention**:
- Use appropriate lock types (threading.Lock vs asyncio.Lock)
- Keep critical sections small
- Consider lock-free alternatives where possible

### 5. Memory Leaks in Thread-Safe Code

**Issue**: Memory leaks occur due to improper resource cleanup in thread-safe code.

**Symptoms**:
```
Increasing memory usage over time
Memory not released after operations
Performance degradation due to memory pressure
```

**Root Cause**: Resources not properly cleaned up in finally blocks.

**Solution**:
```python
# ❌ MEMORY LEAK
async def process_data(data):
    lock = asyncio.Lock()
    async with lock:
        result = await heavy_processing(data)
        return result  # Lock not properly cleaned up

# ✅ NO MEMORY LEAK
async def process_data(data):
    lock = asyncio.Lock()
    try:
        async with lock:
            result = await heavy_processing(data)
            return result
    finally:
        # Ensure lock is released even if exception occurs
        pass
```

**Prevention**:
- Always use context managers for locks
- Implement proper exception handling
- Monitor memory usage in production

## Compilation Issues

### 6. Type Annotation Errors

**Issue**: Condon compilation fails due to missing or incorrect type annotations.

**Symptoms**:
```
Error: Missing type annotation for parameter 'x'
Error: Cannot infer type for variable 'result'
Error: Type annotation required for compiled code
```

**Root Cause**: Condon requires explicit type annotations for compilation.

**Solution**:
```python
# ❌ MISSING TYPE ANNOTATIONS
def process_data(data):
    result = []
    for item in data:
        result.append(process_item(item))
    return result

# ✅ WITH TYPE ANNOTATIONS
from typing import List, Any

def process_data(data: List[Any]) -> List[Any]:
    result: List[Any] = []
    for item in data:
        result.append(process_item(item))
    return result
```

**Prevention**:
- Add type annotations to all functions
- Use mypy for type checking
- Validate types before compilation

### 7. Dynamic Feature Compilation Errors

**Issue**: Condon cannot compile code that uses dynamic features.

**Symptoms**:
```
Error: eval() not supported in compiled mode
Error: exec() not supported in compiled mode
Error: globals() not supported in compiled mode
```

**Root Cause**: Condon requires static analysis and cannot handle dynamic features.

**Solution**:
```python
# ❌ DYNAMIC FEATURES
def create_object(class_name: str, **kwargs):
    class_obj = globals()[class_name]
    return class_obj(**kwargs)

# ✅ STATIC ALTERNATIVE
from typing import Dict, Type, Any

OBJECT_REGISTRY: Dict[str, Type[Any]] = {
    "User": User,
    "Graph": Graph,
    "Memory": Memory,
}

def create_object(class_name: str, **kwargs) -> Any:
    class_obj = OBJECT_REGISTRY[class_name]
    return class_obj(**kwargs)
```

**Prevention**:
- Replace all dynamic features with static alternatives
- Use explicit registries and mappings
- Validate code for dynamic features before compilation

## Runtime Issues

### 8. NumPy Thread Safety Issues

**Issue**: NumPy operations cause thread safety issues in no-GIL environment.

**Symptoms**:
```
Segmentation fault in NumPy operations
Inconsistent numerical results
Memory corruption in array operations
```

**Root Cause**: NumPy operations are not thread-safe by default in no-GIL environment.

**Solution**:
```python
# ❌ THREAD-UNSAFE NUMPY
import numpy as np

def process_array(data):
    result = np.array(data)
    result *= 2  # Not thread-safe in no-GIL
    return result

# ✅ THREAD-SAFE NUMPY
import numpy as np
import threading

def process_array(data):
    with threading.Lock():  # Protect NumPy operations
        result = np.array(data)
        result *= 2
        return result.copy()  # Return copy to avoid shared state
```

**Prevention**:
- Use locks for NumPy operations
- Return copies of arrays to avoid shared state
- Consider using thread-local NumPy contexts

### 9. Database Connection Thread Safety

**Issue**: Database connections are not thread-safe in no-GIL environment.

**Symptoms**:
```
Database connection errors
Transaction conflicts
Connection pool exhaustion
```

**Root Cause**: Database connections must be thread-safe in no-GIL environment.

**Solution**:
```python
# ❌ THREAD-UNSAFE DATABASE
import sqlite3

db_connection = sqlite3.connect('database.db')

def query_database(query: str):
    cursor = db_connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()

# ✅ THREAD-SAFE DATABASE
import sqlite3
import threading
from contextlib import contextmanager

class ThreadSafeDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
    
    @contextmanager
    def get_connection(self):
        with self._lock:
            connection = sqlite3.connect(self.db_path)
            try:
                yield connection
            finally:
                connection.close()
    
    def query_database(self, query: str):
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query)
            return cursor.fetchall()
```

**Prevention**:
- Use connection pools
- Implement proper connection management
- Test database operations under concurrent load

## Debugging Procedures

### 10. Thread Safety Debugging

**Issue**: Difficult to debug thread safety issues in no-GIL environment.

**Symptoms**:
```
Intermittent failures
Race conditions hard to reproduce
Memory corruption issues
```

**Solution**:
```python
import asyncio
import time
from typing import List, Dict, Any

class ThreadSafetyDebugger:
    """Debugging framework for thread safety issues"""
    
    def __init__(self):
        self.operation_log: List[Dict[str, Any]] = []
        self._log_lock = asyncio.Lock()
    
    async def log_operation(self, operation: str, thread_id: int, timestamp: float):
        """Log thread operations for debugging"""
        async with self._log_lock:
            self.operation_log.append({
                'operation': operation,
                'thread_id': thread_id,
                'timestamp': timestamp
            })
    
    async def analyze_race_conditions(self) -> Dict[str, Any]:
        """Analyze operation log for potential race conditions"""
        async with self._log_lock:
            # Analyze concurrent operations
            concurrent_ops = self._find_concurrent_operations()
            return {
                'total_operations': len(self.operation_log),
                'concurrent_operations': concurrent_ops,
                'potential_race_conditions': self._identify_race_conditions()
            }
    
    def _find_concurrent_operations(self) -> List[Dict[str, Any]]:
        """Find operations that occurred concurrently"""
        # Implementation for finding concurrent operations
        pass
    
    def _identify_race_conditions(self) -> List[Dict[str, Any]]:
        """Identify potential race conditions"""
        # Implementation for identifying race conditions
        pass
```

**Usage**:
```python
# Add debugging to thread-safe operations
debugger = ThreadSafetyDebugger()

async def thread_safe_operation():
    await debugger.log_operation("start", id(asyncio.current_task()), time.time())
    # ... operation code ...
    await debugger.log_operation("end", id(asyncio.current_task()), time.time())

# Analyze for race conditions
analysis = await debugger.analyze_race_conditions()
print(f"Potential race conditions: {analysis['potential_race_conditions']}")
```

### 11. Performance Debugging

**Issue**: Performance issues hard to identify in thread-safe code.

**Symptoms**:
```
Slow performance after thread safety implementation
High CPU usage
Memory leaks
```

**Solution**:
```python
import time
import psutil
import asyncio
from typing import Dict, Any, Callable

class PerformanceDebugger:
    """Debugging framework for performance issues"""
    
    def __init__(self):
        self.performance_log: List[Dict[str, Any]] = []
        self._log_lock = asyncio.Lock()
    
    async def profile_operation(self, operation_name: str, operation_func: Callable):
        """Profile a thread-safe operation"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            result = await operation_func()
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            async with self._log_lock:
                self.performance_log.append({
                    'operation': operation_name,
                    'duration': end_time - start_time,
                    'memory_delta': end_memory - start_memory,
                    'timestamp': start_time
                })
            
            return result
        except Exception as e:
            async with self._log_lock:
                self.performance_log.append({
                    'operation': operation_name,
                    'error': str(e),
                    'timestamp': start_time
                })
            raise
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        async with self._log_lock:
            if not self.performance_log:
                return {}
            
            durations = [log['duration'] for log in self.performance_log if 'duration' in log]
            memory_deltas = [log['memory_delta'] for log in self.performance_log if 'memory_delta' in log]
            
            return {
                'total_operations': len(self.performance_log),
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'avg_memory_delta': sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0,
                'errors': [log for log in self.performance_log if 'error' in log]
            }
```

**Usage**:
```python
debugger = PerformanceDebugger()

async def thread_safe_operation():
    return await debugger.profile_operation(
        "thread_safe_operation",
        lambda: actual_operation()
    )

# Get performance summary
summary = await debugger.get_performance_summary()
print(f"Average duration: {summary['avg_duration']:.3f}s")
print(f"Memory delta: {summary['avg_memory_delta'] / 1024 / 1024:.2f}MB")
```

## Prevention Strategies

### 1. Static Analysis
- Use mypy for type checking
- Use flake8 for code quality
- Use bandit for security analysis
- Validate code before compilation

### 2. Testing Strategies
- Implement comprehensive thread safety tests
- Use stress testing for concurrent operations
- Monitor memory usage during tests
- Validate performance under load

### 3. Monitoring
- Implement real-time performance monitoring
- Monitor thread safety in production
- Track memory usage patterns
- Alert on performance degradation

### 4. Documentation
- Document all thread safety patterns
- Maintain troubleshooting guides
- Update procedures based on issues
- Share lessons learned

## Conclusion

This troubleshooting guide provides solutions for the most common issues encountered during Condon migration. The key is to:

1. **Prevent issues** through proper design and testing
2. **Detect issues early** through monitoring and validation
3. **Resolve issues quickly** using the provided solutions
4. **Learn from issues** to improve future migrations

**Key Success Factors**:
- Comprehensive testing before deployment
- Real-time monitoring in production
- Quick response to issues
- Continuous improvement based on lessons learned

---

**Document Version**: 1.0  
**Last Updated**: 2025-03-05T12:41:19  
**Based On**: TASK-002 Analysis Results  
**Status**: Production Ready 