# Condon Thread Safety Guidelines

## Overview

This document provides comprehensive guidelines for developing thread-safe code in the Condon free-threaded Python environment. Condon removes the Global Interpreter Lock (GIL), making race conditions much more likely to occur.

## Critical Thread Safety Issues

### 1. Singleton Pattern Race Conditions

**Problem**: Multiple singleton implementations use unsafe check-then-act patterns.

**Thread-Unsafe Pattern**:
```python
# ❌ THREAD-UNSAFE
_health_monitor: Optional[HealthMonitor] = None

async def get_health_monitor() -> HealthMonitor:
    global _health_monitor
    if _health_monitor is None:  # RACE CONDITION HERE
        _health_monitor = HealthMonitor()
    return _health_monitor
```

**Thread-Safe Solution**:
```python
# ✅ THREAD-SAFE
import asyncio
from typing import Optional

_health_monitor: Optional[HealthMonitor] = None
_health_monitor_lock = asyncio.Lock()

async def get_health_monitor() -> HealthMonitor:
    """Get or create health monitor instance with thread safety"""
    global _health_monitor
    
    if _health_monitor is None:
        async with _health_monitor_lock:
            if _health_monitor is None:  # Double-check after acquiring lock
                _health_monitor = HealthMonitor()
    
    return _health_monitor
```

### 2. Global Variable Access

**Problem**: Global variables accessed without proper synchronization.

**Thread-Unsafe Pattern**:
```python
# ❌ THREAD-UNSAFE
global_counter = 0

def increment_counter():
    global global_counter
    global_counter += 1  # Race condition in no-GIL environment
```

**Thread-Safe Solution**:
```python
# ✅ THREAD-SAFE
import threading

global_counter = 0
counter_lock = threading.Lock()

def increment_counter():
    global global_counter
    with counter_lock:
        global_counter += 1
```

### 3. Shared State Access

**Problem**: Collections and shared resources accessed without thread safety.

**Thread-Unsafe Pattern**:
```python
# ❌ THREAD-UNSAFE
class IncidentManager:
    def __init__(self):
        self.incidents: Dict[UUID, Incident] = {}
        # No synchronization for shared collections
```

**Thread-Safe Solution**:
```python
# ✅ THREAD-SAFE
import asyncio
from typing import Dict, UUID
from threading import Lock

class IncidentManager:
    def __init__(self):
        self.incidents: Dict[UUID, Incident] = {}
        self._incidents_lock = Lock()  # Thread-safe access to incidents
    
    async def get_incident(self, incident_id: UUID) -> Optional[Incident]:
        """Thread-safe incident retrieval"""
        with self._incidents_lock:
            return self.incidents.get(incident_id)
    
    async def add_incident(self, incident: Incident) -> None:
        """Thread-safe incident addition"""
        with self._incidents_lock:
            self.incidents[incident.id] = incident
```

## Thread Safety Patterns

### 1. Double-Checked Locking Pattern

Use this pattern for singleton creation:

```python
import asyncio
from typing import Optional, TypeVar, Type

T = TypeVar('T')

class ThreadSafeSingleton:
    """Thread-safe singleton base class for async applications"""
    
    _instance: Optional['ThreadSafeSingleton'] = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls: Type[T]) -> T:
        """Get singleton instance with thread safety"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:  # Double-check after acquiring lock
                    cls._instance = cls()
        return cls._instance
```

### 2. Thread-Safe Singleton Decorator

Use this decorator for thread-safe singletons:

```python
import asyncio
from typing import TypeVar, Type
from functools import wraps

T = TypeVar('T')

def thread_safe_singleton(cls: Type[T]) -> Type[T]:
    """Thread-safe singleton decorator for async classes"""
    
    instances = {}
    locks = {}
    
    @wraps(cls)
    async def get_instance(*args, **kwargs) -> T:
        if cls not in instances:
            if cls not in locks:
                locks[cls] = asyncio.Lock()
            
            async with locks[cls]:
                if cls not in instances:  # Double-check after acquiring lock
                    instances[cls] = cls(*args, **kwargs)
                    if hasattr(instances[cls], 'initialize'):
                        await instances[cls].initialize()
        
        return instances[cls]
    
    # Add get_instance method to the class
    cls.get_instance = classmethod(get_instance)
    return cls
```

### 3. Thread-Safe Global State Management

Use this pattern for global state:

```python
import asyncio
from typing import Dict, Any, Optional
from threading import Lock

class ThreadSafeGlobalState:
    """Thread-safe global state manager"""
    
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._lock = Lock()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Thread-safe get operation"""
        with self._lock:
            return self._state.get(key, default)
    
    async def set(self, key: str, value: Any) -> None:
        """Thread-safe set operation"""
        with self._lock:
            self._state[key] = value
```

### 4. Thread-Safe Collection Wrappers

Use thread-safe collection wrappers:

```python
from threading import Lock

class ThreadSafeDict:
    """Thread-safe dictionary wrapper"""
    
    def __init__(self, *args, **kwargs):
        self._dict = dict(*args, **kwargs)
        self._lock = Lock()
    
    def __getitem__(self, key):
        """Thread-safe getitem operation"""
        with self._lock:
            return self._dict[key]
    
    def __setitem__(self, key, value):
        """Thread-safe setitem operation"""
        with self._lock:
            self._dict[key] = value
```

## Best Practices

### 1. Singleton Pattern Guidelines

**✅ DO**:
- Use double-checked locking pattern
- Implement with asyncio.Lock for async applications
- Use thread-safe decorators for reusable patterns
- Test singleton behavior under concurrent access

**❌ DON'T**:
- Use simple check-then-act patterns
- Access global variables without synchronization
- Assume GIL protection in no-GIL environments
- Create singletons without proper locking

### 2. Shared State Access Guidelines

**✅ DO**:
- Use locks for all shared state access
- Implement thread-safe collections
- Use atomic operations where possible
- Test concurrent access patterns

**❌ DON'T**:
- Access shared collections without synchronization
- Use global variables for mutable state
- Assume operations are atomic
- Ignore race condition possibilities

### 3. Performance Considerations

**✅ DO**:
- Keep critical sections small
- Use appropriate lock granularity
- Consider lock-free alternatives where possible
- Profile thread-safe implementations

**❌ DON'T**:
- Hold locks for extended periods
- Use overly broad locking strategies
- Ignore performance impact of thread safety
- Skip performance testing

## Testing Thread Safety

### 1. Race Condition Detection

```python
import asyncio
from typing import List, Callable

class ThreadSafetyTester:
    """Framework for testing thread safety"""
    
    async def test_singleton_thread_safety(self, get_instance_func: Callable, 
                                         num_threads: int = 10) -> Dict[str, Any]:
        """Test singleton pattern for thread safety"""
        
        instances = []
        errors = []
        
        async def worker():
            try:
                instance = await get_instance_func()
                instances.append(id(instance))
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads to test singleton creation
        tasks = [worker() for _ in range(num_threads)]
        await asyncio.gather(*tasks)
        
        # Check if all instances are the same (singleton property)
        unique_instances = len(set(instances))
        is_thread_safe = unique_instances == 1 and len(errors) == 0
        
        return {
            'test_type': 'singleton_thread_safety',
            'num_threads': num_threads,
            'unique_instances': unique_instances,
            'errors': errors,
            'is_thread_safe': is_thread_safe
        }
```

### 2. Performance Testing

```python
import time
import asyncio

class ThreadSafetyPerformanceTester:
    """Performance testing for thread-safe implementations"""
    
    async def benchmark_singleton_access(self, get_instance_func: Callable, 
                                       num_operations: int = 10000) -> Dict[str, Any]:
        """Benchmark singleton access performance"""
        
        start_time = time.time()
        
        # Perform multiple singleton access operations
        tasks = [get_instance_func() for _ in range(num_operations)]
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        operations_per_second = num_operations / total_time
        
        return {
            'test_type': 'singleton_performance',
            'num_operations': num_operations,
            'total_time': total_time,
            'operations_per_second': operations_per_second
        }
```

## Implementation Checklist

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

Following these guidelines ensures that your threaded code is safe, predictable, and production-ready in the Condon no-GIL environment. Always test thoroughly and monitor performance in production environments.

**Key Takeaways**:
- Condon's no-GIL environment requires explicit thread safety measures
- Singleton patterns must use double-checked locking
- Shared state access requires proper synchronization
- Performance impact of thread safety measures is acceptable
- Comprehensive testing is essential for production deployment

---

**Document Version**: 1.0  
**Last Updated**: 2025-03-05T12:41:19  
**Environment**: Condon no-GIL Python build  
**Status**: Production Ready 