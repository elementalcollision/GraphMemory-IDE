# Codon Unit Testing Framework

This directory contains a comprehensive unit testing framework for Codon components, specifically designed for analytics components with compilation testing, performance benchmarking, and error handling.

## Overview

The Codon Unit Testing Framework provides:

- **Compilation Testing**: Test Codon compilation of Python code
- **Performance Benchmarking**: Compare interpreted vs compiled performance
- **Error Handling**: Test error scenarios and recovery
- **Coverage Reporting**: Track code coverage for analytics components
- **Test Data Generation**: Realistic test data for analytics scenarios

## Directory Structure

```
tests/codon/unit/
├── __init__.py                 # Package initialization
├── README.md                   # This documentation
├── test_analytics_engine.py    # Analytics engine unit tests
├── test_algorithms.py          # Algorithms component unit tests
├── test_cache.py               # Cache component unit tests
├── test_runner.py              # Comprehensive test runner
└── test_data_generator.py      # Test data generation utilities
```

## Base Classes

### CodonTestBase

Abstract base class for all Codon unit tests. Provides:

- Setup and teardown methods
- Abstract methods for compilation, performance, and error handling tests
- Resource management and cleanup

### CodonCompilationTester

Utility class for testing Codon compilation:

```python
from tests.codon.base import CodonCompilationTester

tester = CodonCompilationTester()
result = tester.test_compilation(source_code, test_name="my_test")
```

### CodonPerformanceTester

Utility class for performance benchmarking:

```python
from tests.codon.base import CodonPerformanceTester

tester = CodonPerformanceTester()
result = tester.benchmark_interpreted_vs_compiled(
    interpreted_func, compiled_func, test_name="performance_test"
)
```

### CodonErrorTester

Utility class for error handling tests:

```python
from tests.codon.base import CodonErrorTester

tester = CodonErrorTester()
result = tester.test_error_handling(error_func, ValueError)
```

## Test Templates

### Analytics Engine Tests

Located in `test_analytics_engine.py`:

- Compilation testing of analytics engine
- Performance comparison between interpreted and compiled versions
- Error handling for invalid data
- Memory usage testing
- Concurrent operations testing
- Performance regression detection

### Algorithms Tests

Located in `test_algorithms.py`:

- Graph algorithm compilation testing
- Performance benchmarking for graph operations
- Error handling for invalid graph data
- Memory usage for large graphs
- Concurrent algorithm execution

### Cache Tests

Located in `test_cache.py`:

- Cache manager compilation testing
- Performance testing for cache operations
- Error handling for invalid cache keys
- Memory usage for large cache datasets
- Concurrent cache access testing

## Test Runner

The `test_runner.py` provides a comprehensive test runner that:

1. **Executes all compilation tests**
2. **Runs performance benchmarks**
3. **Tests error handling scenarios**
4. **Generates coverage reports**
5. **Saves detailed results**

### Usage

```python
from tests.codon.unit.test_runner import run_codon_unit_tests

results = run_codon_unit_tests()
```

### Output

The test runner generates:

- `test_results/codon_test_results.json` - Detailed test results
- `test_results/codon_test_summary.json` - Test summary
- Console output with progress and summary

## Test Data Generator

The `test_data_generator.py` provides realistic test data:

### Graph Data

```python
from tests.codon.unit.test_data_generator import get_graph_test_data

graph_data = get_graph_test_data()
# Returns realistic graph with users, posts, comments, and relationships
```

### Analytics Data

```python
from tests.codon.unit.test_data_generator import get_analytics_test_data

analytics_data = get_analytics_test_data()
# Returns analytics queries and expected results
```

### Performance Data

```python
from tests.codon.unit.test_data_generator import get_performance_test_data

perf_data = get_performance_test_data()
# Returns small, medium, and large datasets for performance testing
```

## Running Tests

### Individual Test Files

```bash
# Run specific test file
python -m pytest tests/codon/unit/test_analytics_engine.py -v

# Run with coverage
python -m pytest tests/codon/unit/test_analytics_engine.py --cov=server.analytics
```

### All Codon Tests

```bash
# Run all Codon unit tests
python -m pytest tests/codon/unit/ -v

# Run with coverage
python -m pytest tests/codon/unit/ --cov=server.analytics --cov-report=html
```

### Using Test Runner

```bash
# Run comprehensive test suite
python tests/codon/unit/test_runner.py
```

## Configuration

### Test Data Configuration

```python
from tests.codon.unit.test_data_generator import TestDataConfig

config = TestDataConfig(
    num_nodes=1000,
    num_edges=5000,
    num_users=100,
    num_posts=500,
    time_range_days=30
)
```

### Performance Baselines

Performance baselines are automatically saved in `codon_performance_baseline.json` and used for regression detection.

## Success Criteria

The framework is designed to achieve:

- ✅ **80%+ code coverage** for Codon analytics components
- ✅ **Compilation success rate** > 95%
- ✅ **Performance speedup** > 2x for compiled vs interpreted
- ✅ **Error handling success rate** > 90%
- ✅ **Performance regression detection** with 10% threshold

## Integration with CI/CD

The framework integrates with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Codon Unit Tests
  run: |
    python -m pytest tests/codon/unit/ --cov=server.analytics --cov-report=xml
    python tests/codon/unit/test_runner.py
```

## Dependencies

Required dependencies:

- `pytest` - Testing framework
- `psutil` - System monitoring
- `coverage` - Code coverage (optional)
- `codon` - Codon compiler (must be installed)

## Best Practices

1. **Use the base classes** for consistent test structure
2. **Generate realistic test data** using the data generator
3. **Test both interpreted and compiled versions**
4. **Include error handling tests**
5. **Monitor performance regressions**
6. **Maintain high code coverage**

## Troubleshooting

### Common Issues

1. **Codon not found**: Ensure Codon is installed and in PATH
2. **Import errors**: Check that analytics modules are available
3. **Performance test failures**: Verify baseline data exists
4. **Coverage issues**: Install coverage package

### Debug Mode

Run tests with debug output:

```bash
python -m pytest tests/codon/unit/ -v -s --tb=short
```

## Contributing

When adding new tests:

1. Extend the appropriate base class
2. Use the test data generator for realistic data
3. Include compilation, performance, and error handling tests
4. Update this documentation
5. Ensure tests pass in both interpreted and compiled modes

## Future Enhancements

Planned improvements:

- GPU acceleration testing
- Distributed testing support
- Advanced performance profiling
- Integration with monitoring systems
- Automated baseline updates 