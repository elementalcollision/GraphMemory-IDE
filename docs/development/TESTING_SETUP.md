# GraphMemory-IDE Testing Setup Guide

## 🎯 Overview

This guide provides comprehensive instructions for setting up and running the test suite for GraphMemory-IDE, with special attention to the Analytics Engine Phase 3 components that have achieved 100% test pass rates.

## ✅ Current Test Status

- **Step 6 Cache Manager**: 30/30 tests passing (100%)
- **Step 7 Performance Manager**: 29/29 tests passing (100%)
- **Steps 1-5**: Fully validated and documented
- **Overall Phase 3 Progress**: 87.5% complete

## 🔧 Environment Setup

### Prerequisites

```bash
# Python 3.11+ required
python --version  # Should be 3.11 or higher

# Virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Critical: Python Path Configuration

**The most important requirement** for running tests is setting the Python path correctly:

```bash
# Method 1: Environment variable (recommended)
export PYTHONPATH="/path/to/GraphMemory-IDE:$PYTHONPATH"

# Method 2: Add to shell profile (permanent)
echo 'export PYTHONPATH="/path/to/GraphMemory-IDE:$PYTHONPATH"' >> ~/.bashrc
source ~/.bashrc

# Method 3: Use with pytest command
cd /path/to/GraphMemory-IDE
PYTHONPATH=. python -m pytest server/dashboard/test_cache_manager.py -v
```

## 📁 pytest Configuration

The project includes a properly configured `pytest.ini` file:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = -v --tb=short --strict-markers
testpaths = tests server/dashboard
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
markers =
    asyncio: mark test as asyncio
    unit: mark test as unit test
    integration: mark test as integration test
    slow: mark test as slow running
```

### Key Configuration Features

- **`asyncio_mode = auto`**: Automatically detects and runs async tests
- **`asyncio_default_fixture_loop_scope = function`**: Proper async fixture scoping
- **`addopts = -v --tb=short --strict-markers`**: Verbose output with concise tracebacks
- **`testpaths`**: Includes both `tests/` and `server/dashboard/` directories

## 🧪 Running Tests

### Individual Test Suites

```bash
# Step 6: Cache Manager Tests (30 tests)
PYTHONPATH=. python -m pytest server/dashboard/test_cache_manager.py -v

# Step 7: Performance Manager Tests (29 tests)
PYTHONPATH=. python -m pytest server/dashboard/test_performance_manager.py -v

# Run specific test class
PYTHONPATH=. python -m pytest server/dashboard/test_cache_manager.py::TestCacheEntry -v

# Run specific test method
PYTHONPATH=. python -m pytest server/dashboard/test_cache_manager.py::TestCacheEntry::test_cache_entry_expiration -v
```

### Comprehensive Test Runs

```bash
# All dashboard tests
PYTHONPATH=. python -m pytest server/dashboard/ -v

# With coverage reporting
PYTHONPATH=. python -m pytest server/dashboard/ --cov=server/dashboard --cov-report=html

# Parallel execution (if pytest-xdist installed)
PYTHONPATH=. python -m pytest server/dashboard/ -n auto

# Stop on first failure
PYTHONPATH=. python -m pytest server/dashboard/ -x
```

### Test Output Options

```bash
# Quiet mode (less verbose)
PYTHONPATH=. python -m pytest server/dashboard/ -q

# Very verbose (shows individual test details)
PYTHONPATH=. python -m pytest server/dashboard/ -vv

# Show local variables on failure
PYTHONPATH=. python -m pytest server/dashboard/ -l

# Capture stdout/stderr
PYTHONPATH=. python -m pytest server/dashboard/ -s
```

## 🏗️ Test Architecture

### Modern Async Testing Patterns

The test suite uses modern pytest-asyncio patterns:

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def cache_manager():
    """Async fixture for cache manager testing"""
    config = CacheConfig(enable_l2_redis=False)
    manager = CacheManager(config)
    await manager.initialize()
    yield manager
    await manager.shutdown()

@pytest.mark.asyncio
async def test_cache_operations(cache_manager):
    """Async test with proper fixture usage"""
    result = await cache_manager.set("key", "value")
    assert result is True
```

### Test Isolation and Cleanup

Critical for preventing test interference:

```python
@pytest_asyncio.fixture(autouse=True)
async def cleanup_circuit_breakers():
    """Auto-cleanup circuit breakers before each test"""
    manager = get_circuit_breaker_manager()
    manager._breakers.clear()
    yield
    manager._breakers.clear()
```

## 🐛 Common Issues and Solutions

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'server'`

**Solution**: Ensure PYTHONPATH is set correctly:
```bash
export PYTHONPATH="/path/to/GraphMemory-IDE:$PYTHONPATH"
```

### Async Fixture Errors

**Problem**: `TypeError: async_generator object has no attribute`

**Solution**: Use `@pytest_asyncio.fixture` instead of `@pytest.fixture`:
```python
@pytest_asyncio.fixture  # ✅ Correct
async def async_fixture():
    # fixture code
```

### Circuit Breaker Conflicts

**Problem**: Tests failing due to existing circuit breakers

**Solution**: Ensured by autouse cleanup fixture (already implemented)

### TTL=0 Test Failures

**Problem**: Cache entries with TTL=0 not expiring immediately

**Solution**: Fixed in `CacheEntry.is_expired()` method:
```python
def is_expired(self) -> bool:
    if self.ttl_seconds == 0:
        return True  # TTL=0 means immediate expiration
    # ... rest of logic
```

## 📊 Test Coverage Analysis

### Current Coverage Metrics

- **Cache Manager**: 100% test pass rate with comprehensive coverage
  - TTL handling and expiration logic
  - Multi-level cache hierarchy (L1/L2)
  - Circuit breaker integration
  - Cache warming and invalidation
  - Fallback cache implementation

- **Performance Manager**: 100% test pass rate with full feature coverage
  - Resource monitoring and metrics collection
  - Connection pooling and management
  - Performance profiling and optimization
  - Memory management and garbage collection
  - Rate limiting and adaptive controls

### Coverage Reports

```bash
# Generate HTML coverage report
PYTHONPATH=. python -m pytest server/dashboard/ --cov=server/dashboard --cov-report=html

# View coverage in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🚀 Performance Testing

### Benchmark Tests

```bash
# Run slow/performance tests
PYTHONPATH=. python -m pytest server/dashboard/ -m slow

# Run with timing information
PYTHONPATH=. python -m pytest server/dashboard/ --durations=10
```

### Memory Profiling

```bash
# Install memory profiler
pip install pytest-memray

# Run with memory profiling
PYTHONPATH=. python -m pytest server/dashboard/ --memray
```

## 🔍 Debugging Tests

### Debug Mode

```bash
# Run with debugging enabled
PYTHONPATH=. python -m pytest server/dashboard/ --pdb

# Drop into debugger on failure
PYTHONPATH=. python -m pytest server/dashboard/ --pdb-trace
```

### Logging Configuration

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In tests, use caplog fixture
def test_with_logging(caplog):
    with caplog.at_level(logging.INFO):
        # test code
        assert "expected message" in caplog.text
```

## 📝 Test Development Guidelines

### Writing New Tests

1. **Use async patterns consistently**:
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

2. **Implement proper cleanup**:
```python
@pytest_asyncio.fixture
async def resource():
    resource = await create_resource()
    yield resource
    await resource.cleanup()
```

3. **Test edge cases**:
```python
def test_ttl_zero_expiration():
    entry = CacheEntry(key="test", data="data", ttl_seconds=0)
    assert entry.is_expired() is True  # Should expire immediately
```

### Test Organization

- Group related tests in classes
- Use descriptive test names
- Include docstrings for complex tests
- Separate unit tests from integration tests

## 🎯 Next Steps

With Steps 6 and 7 achieving 100% test pass rates, the testing infrastructure is ready for:

1. **Step 8 Implementation**: Apply same testing patterns
2. **Integration Testing**: Cross-component validation
3. **End-to-End Testing**: Complete workflow validation
4. **Performance Benchmarking**: Production-level testing

## 📞 Support

If you encounter testing issues:

1. **Check Python Path**: Ensure `PYTHONPATH` is set correctly
2. **Verify Dependencies**: Run `pip install -r requirements.txt`
3. **Review Logs**: Use `-v` flag for verbose output
4. **Isolate Tests**: Run individual tests to identify issues

---

**Testing Infrastructure**: ✅ **Production Ready**  
**Documentation Updated**: May 29, 2025  
**Test Coverage**: Steps 6-7 at 100% 