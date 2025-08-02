# Codon Team Training Materials

## Overview

This comprehensive training guide provides hands-on learning materials for teams working with Codon testing in the GraphMemory-IDE project. It includes practical exercises, tutorials, and resources to build expertise in Codon testing.

## Table of Contents

1. [Training Philosophy](#training-philosophy)
2. [Prerequisites](#prerequisites)
3. [Module 1: Codon Basics](#module-1-codon-basics)
4. [Module 2: Testing Fundamentals](#module-2-testing-fundamentals)
5. [Module 3: Advanced Testing](#module-3-advanced-testing)
6. [Module 4: Performance Testing](#module-4-performance-testing)
7. [Module 5: Troubleshooting](#module-5-troubleshooting)
8. [Practical Exercises](#practical-exercises)
9. [Assessment and Certification](#assessment-and-certification)
10. [Resources and References](#resources-and-references)

## Training Philosophy

### Learning Objectives

1. **Understanding**: Deep comprehension of Codon compilation and testing
2. **Practical Skills**: Hands-on experience with testing tools and frameworks
3. **Problem Solving**: Ability to diagnose and resolve testing issues
4. **Best Practices**: Application of industry-standard testing methodologies
5. **Continuous Learning**: Development of ongoing learning habits

### Training Approach

- **Hands-on Learning**: 70% practical exercises, 30% theory
- **Progressive Complexity**: Start simple, build to advanced concepts
- **Real-world Scenarios**: Use actual project examples and cases
- **Collaborative Learning**: Team-based exercises and peer review
- **Continuous Assessment**: Regular checkpoints and feedback

## Prerequisites

### Technical Requirements

- Python 3.8+ installed
- Virtual environment setup
- Basic understanding of Python testing
- Familiarity with command-line tools
- Git version control experience

### Pre-training Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd GraphMemory-IDE-1

# 2. Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Codon
/bin/bash -c "$(curl -fsSL https://exaloop.io/install.sh)"

# 5. Verify installation
codon --version
pytest --version
```

### Pre-training Assessment

Complete this quick assessment to gauge your starting level:

```python
# Pre-training Assessment
def pre_training_assessment():
    """Assess current knowledge level"""
    questions = [
        "Have you used pytest before? (Y/N)",
        "Are you familiar with Python type hints? (Y/N)",
        "Have you worked with performance testing? (Y/N)",
        "Do you understand compilation concepts? (Y/N)",
        "Have you used virtual environments? (Y/N)"
    ]
    
    score = 0
    for question in questions:
        answer = input(question)
        if answer.upper() == 'Y':
            score += 1
    
    print(f"Pre-training score: {score}/5")
    return score
```

## Module 1: Codon Basics

### Learning Objectives

- Understand what Codon is and how it works
- Learn basic compilation concepts
- Practice simple Codon operations
- Understand the testing environment

### Theory: What is Codon?

Codon (Codon) is a high-performance Python compiler that:
- Compiles Python code to native machine code
- Provides significant performance improvements (10-100x speedup)
- Supports Python interoperability
- Enables static compilation of Python programs

### Hands-on Exercise 1.1: First Codon Compilation

```python
# Exercise 1.1: Your First Codon Compilation
def exercise_1_1():
    """Create and compile your first Codon program"""
    
    # Step 1: Create a simple Python function
    source_code = """
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def main():
    result = fibonacci(40)
    print(f"Fibonacci(40) = {result}")

if __name__ == "__main__":
    main()
"""
    
    # Step 2: Save to file
    with open("fibonacci.codon", "w") as f:
        f.write(source_code)
    
    # Step 3: Compile with Codon
    import subprocess
    result = subprocess.run(
        ["codon", "build", "fibonacci.codon"],
        capture_output=True,
        text=True
    )
    
    # Step 4: Check compilation result
    if result.returncode == 0:
        print("✓ Compilation successful!")
        
        # Step 5: Run the compiled program
        exec_result = subprocess.run(
            ["./fibonacci"],
            capture_output=True,
            text=True
        )
        print(f"Output: {exec_result.stdout}")
    else:
        print(f"✗ Compilation failed: {result.stderr}")
    
    return result.returncode == 0

# Run the exercise
if __name__ == "__main__":
    exercise_1_1()
```

### Exercise 1.2: Understanding Compilation Errors

```python
# Exercise 1.2: Learning from Compilation Errors
def exercise_1_2():
    """Practice with compilation errors and debugging"""
    
    # Create code with intentional errors
    error_examples = [
        {
            "name": "syntax_error",
            "code": """
def invalid_function(
    # Missing closing parenthesis
""",
            "expected_error": "syntax"
        },
        {
            "name": "type_error", 
            "code": """
def type_error_function(x: int) -> str:
    return x + "string"  # Type error
""",
            "expected_error": "type"
        },
        {
            "name": "undefined_variable",
            "code": """
def undefined_function():
    return undefined_variable
""",
            "expected_error": "undefined"
        }
    ]
    
    for example in error_examples:
        print(f"\nTesting: {example['name']}")
        
        # Save error code to file
        filename = f"{example['name']}.codon"
        with open(filename, "w") as f:
            f.write(example["code"])
        
        # Try to compile
        result = subprocess.run(
            ["codon", "build", filename],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✓ Expected error occurred: {example['expected_error']}")
            print(f"Error message: {result.stderr[:200]}...")
        else:
            print(f"✗ Unexpected success for {example['name']}")
    
    return True
```

### Module 1 Assessment

```python
def module_1_assessment():
    """Assessment for Module 1"""
    questions = [
        {
            "question": "What is the primary benefit of Codon compilation?",
            "options": [
                "Reduced code size",
                "Improved performance",
                "Better error messages", 
                "Easier debugging"
            ],
            "correct": 1
        },
        {
            "question": "Which command compiles a Codon program?",
            "options": [
                "codon run file.codon",
                "codon build file.codon",
                "codon compile file.codon",
                "codon execute file.codon"
            ],
            "correct": 1
        },
        {
            "question": "What file extension is used for Codon source files?",
            "options": [
                ".py",
                ".codon", 
                ".codon",
                ".c"
            ],
            "correct": 1
        }
    ]
    
    score = 0
    for i, q in enumerate(questions):
        print(f"\nQuestion {i+1}: {q['question']}")
        for j, option in enumerate(q['options']):
            print(f"  {j+1}. {option}")
        
        answer = int(input("Your answer (1-4): ")) - 1
        if answer == q['correct']:
            score += 1
            print("✓ Correct!")
        else:
            print(f"✗ Incorrect. Correct answer: {q['correct']+1}")
    
    print(f"\nModule 1 Score: {score}/{len(questions)}")
    return score >= 2  # Pass if 2/3 or better
```

## Module 2: Testing Fundamentals

### Learning Objectives

- Understand testing principles and methodologies
- Learn pytest framework basics
- Practice writing effective tests
- Understand test data management

### Theory: Testing Principles

1. **Test-Driven Development (TDD)**: Write tests before code
2. **Test Coverage**: Ensure comprehensive code coverage
3. **Test Isolation**: Each test should be independent
4. **Test Readability**: Tests should be clear and maintainable
5. **Test Reliability**: Tests should be stable and repeatable

### Exercise 2.1: Writing Your First Test

```python
# Exercise 2.1: Basic Test Writing
import pytest
import subprocess
import tempfile
import os

def test_basic_compilation():
    """Test basic Codon compilation"""
    
    # Arrange: Create test source code
    source_code = """
def add(a: int, b: int) -> int:
    return a + b

def main():
    result = add(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.codon', delete=False) as f:
        f.write(source_code)
        temp_file = f.name
    
    try:
        # Act: Compile the code
        result = subprocess.run(
            ["codon", "build", temp_file],
            capture_output=True,
            text=True
        )
        
        # Assert: Check compilation success
        assert result.returncode == 0, f"Compilation failed: {result.stderr}"
        
        # Execute the compiled program
        executable = temp_file.replace('.codon', '')
        exec_result = subprocess.run(
            [executable],
            capture_output=True,
            text=True
        )
        
        # Assert: Check execution success
        assert exec_result.returncode == 0, f"Execution failed: {exec_result.stderr}"
        assert "Result: 8" in exec_result.stdout
        
        print("✓ Basic compilation test passed!")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        if os.path.exists(executable):
            os.unlink(executable)

# Run the test
if __name__ == "__main__":
    test_basic_compilation()
```

### Exercise 2.2: Test Data Management

```python
# Exercise 2.2: Working with Test Data
from tests.fixtures.codon.data_generators import CodonDataGenerator

def test_with_generated_data():
    """Test using generated test data"""
    
    # Create data generator
    generator = CodonDataGenerator()
    
    # Generate compilation test data
    compilation_tests = generator.generate_compilation_tests(count=5)
    
    # Test each compilation case
    for test_case in compilation_tests:
        print(f"\nTesting: {test_case.name}")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.codon', delete=False) as f:
            f.write(test_case.source_code)
            temp_file = f.name
        
        try:
            # Compile
            result = subprocess.run(
                ["codon", "build", temp_file],
                capture_output=True,
                text=True
            )
            
            # Check expected result
            if test_case.expected_success:
                assert result.returncode == 0, f"Expected success but failed: {result.stderr}"
                print("✓ Expected success - passed")
            else:
                assert result.returncode != 0, "Expected failure but succeeded"
                print("✓ Expected failure - passed")
                
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    print("\n✓ All test data cases processed!")

# Run the exercise
if __name__ == "__main__":
    test_with_generated_data()
```

### Exercise 2.3: Test Fixtures and Setup

```python
# Exercise 2.3: Using Test Fixtures
import pytest
import tempfile
import shutil

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing"""
    temp_dir = tempfile.mkdtemp(prefix="codon_test_")
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_source_code():
    """Provide sample source code for testing"""
    return """
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def main():
    result = fibonacci(10)
    print(f"Fibonacci(10) = {result}")

if __name__ == "__main__":
    main()
"""

def test_with_fixtures(temp_workspace, sample_source_code):
    """Test using fixtures"""
    
    # Create source file in temp workspace
    source_file = os.path.join(temp_workspace, "test.codon")
    with open(source_file, 'w') as f:
        f.write(sample_source_code)
    
    # Compile
    result = subprocess.run(
        ["codon", "build", source_file],
        capture_output=True,
        text=True,
        cwd=temp_workspace
    )
    
    # Assert compilation success
    assert result.returncode == 0, f"Compilation failed: {result.stderr}"
    
    # Execute
    executable = os.path.join(temp_workspace, "test")
    exec_result = subprocess.run(
        [executable],
        capture_output=True,
        text=True,
        cwd=temp_workspace
    )
    
    # Assert execution success
    assert exec_result.returncode == 0
    assert "Fibonacci(10) = 55" in exec_result.stdout
    
    print("✓ Fixture-based test passed!")

# Run the test
if __name__ == "__main__":
    test_with_fixtures(tempfile.mkdtemp(), sample_source_code())
```

## Module 3: Advanced Testing

### Learning Objectives

- Master advanced testing techniques
- Learn integration testing strategies
- Understand error handling testing
- Practice complex test scenarios

### Exercise 3.1: Integration Testing

```python
# Exercise 3.1: Integration Testing
from tests.fixtures.codon.mock_services import CodonMockServices

async def test_integration_workflow():
    """Test complete integration workflow"""
    
    # Create mock services
    mock_services = CodonMockServices()
    
    # Test comprehensive workflow
    results = await mock_services.run_comprehensive_test()
    
    # Validate each component
    assert "compilation" in results
    assert "performance" in results
    assert "analytics" in results
    assert "error_handling" in results
    
    # Check compilation results
    compilation = results["compilation"]
    assert "success" in compilation
    assert "compilation_time" in compilation
    
    # Check performance results
    performance = results["performance"]
    assert "speedup_ratio" in performance
    assert performance["speedup_ratio"] > 1.0
    
    # Check analytics results
    analytics = results["analytics"]
    assert "execution_time" in analytics
    assert "memory_usage" in analytics
    
    # Check error handling results
    error_handling = results["error_handling"]
    assert "handled_correctly" in error_handling
    
    print("✓ Integration test passed!")
    return results

# Run the exercise
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_integration_workflow())
```

### Exercise 3.2: Error Handling Testing

```python
# Exercise 3.2: Error Handling Testing
def test_error_scenarios():
    """Test various error scenarios"""
    
    error_scenarios = [
        {
            "name": "compilation_error",
            "source_code": "def invalid(",
            "expected_error": "syntax"
        },
        {
            "name": "runtime_error",
            "source_code": """
def divide_by_zero():
    return 1 / 0

def main():
    divide_by_zero()
""",
            "expected_error": "ZeroDivisionError"
        },
        {
            "name": "type_error",
            "source_code": """
def type_error():
    x: int = "string"
    return x

def main():
    type_error()
""",
            "expected_error": "type"
        }
    ]
    
    for scenario in error_scenarios:
        print(f"\nTesting: {scenario['name']}")
        
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.codon', delete=False) as f:
            f.write(scenario["source_code"])
            temp_file = f.name
        
        try:
            # Test compilation
            result = subprocess.run(
                ["codon", "build", temp_file],
                capture_output=True,
                text=True
            )
            
            # Validate error handling
            if scenario["expected_error"] == "syntax":
                assert result.returncode != 0, "Expected compilation error"
                print("✓ Compilation error handled correctly")
            else:
                # For runtime errors, compilation should succeed
                assert result.returncode == 0, f"Compilation failed: {result.stderr}"
                
                # Test execution
                executable = temp_file.replace('.codon', '')
                exec_result = subprocess.run(
                    [executable],
                    capture_output=True,
                    text=True
                )
                
                # Check for expected runtime error
                if scenario["expected_error"] in ["ZeroDivisionError", "type"]:
                    assert exec_result.returncode != 0, "Expected runtime error"
                    print("✓ Runtime error handled correctly")
                
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            executable = temp_file.replace('.codon', '')
            if os.path.exists(executable):
                os.unlink(executable)
    
    print("\n✓ All error scenarios tested!")

# Run the exercise
if __name__ == "__main__":
    test_error_scenarios()
```

## Module 4: Performance Testing

### Learning Objectives

- Understand performance testing principles
- Learn benchmarking techniques
- Practice performance analysis
- Master performance regression detection

### Exercise 4.1: Basic Performance Testing

```python
# Exercise 4.1: Performance Benchmarking
import time
import psutil

def benchmark_performance():
    """Basic performance benchmarking exercise"""
    
    # Test function to benchmark
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)
    
    # Performance test parameters
    test_cases = [30, 35, 40]
    iterations = 3
    
    results = {}
    
    for n in test_cases:
        print(f"\nBenchmarking fibonacci({n})")
        
        # Measure interpreted Python performance
        interpreted_times = []
        for i in range(iterations):
            start_time = time.time()
            result = fibonacci(n)
            end_time = time.time()
            interpreted_times.append(end_time - start_time)
        
        avg_interpreted = sum(interpreted_times) / len(interpreted_times)
        
        # Create Codon version
        codon_source = f"""
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def main():
    result = fibonacci({n})
    print(f"Result: {{result}}")

if __name__ == "__main__":
    main()
"""
        
        # Compile Codon version
        with tempfile.NamedTemporaryFile(mode='w', suffix='.codon', delete=False) as f:
            f.write(codon_source)
            temp_file = f.name
        
        try:
            # Compile
            compile_result = subprocess.run(
                ["codon", "build", temp_file],
                capture_output=True,
                text=True
            )
            
            if compile_result.returncode == 0:
                # Measure compiled performance
                executable = temp_file.replace('.codon', '')
                compiled_times = []
                
                for i in range(iterations):
                    start_time = time.time()
                    exec_result = subprocess.run(
                        [executable],
                        capture_output=True,
                        text=True
                    )
                    end_time = time.time()
                    compiled_times.append(end_time - start_time)
                
                avg_compiled = sum(compiled_times) / len(compiled_times)
                
                # Calculate speedup
                speedup = avg_interpreted / avg_compiled
                
                results[n] = {
                    "interpreted_time": avg_interpreted,
                    "compiled_time": avg_compiled,
                    "speedup": speedup
                }
                
                print(f"  Interpreted: {avg_interpreted:.3f}s")
                print(f"  Compiled: {avg_compiled:.3f}s")
                print(f"  Speedup: {speedup:.1f}x")
                
            else:
                print(f"  Compilation failed: {compile_result.stderr}")
                
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            executable = temp_file.replace('.codon', '')
            if os.path.exists(executable):
                os.unlink(executable)
    
    return results

# Run the exercise
if __name__ == "__main__":
    results = benchmark_performance()
    print(f"\nPerformance Results: {results}")
```

### Exercise 4.2: Performance Regression Testing

```python
# Exercise 4.2: Performance Regression Detection
def test_performance_regression():
    """Test performance regression detection"""
    
    # Baseline performance data
    baseline = {
        "fibonacci_30": 0.5,  # seconds
        "fibonacci_35": 2.0,
        "fibonacci_40": 8.0
    }
    
    # Current performance measurement
    current_results = benchmark_performance()
    
    # Check for regressions
    regressions = []
    
    for test_name, baseline_time in baseline.items():
        if test_name in current_results:
            current_time = current_results[test_name]["compiled_time"]
            regression_ratio = current_time / baseline_time
            
            if regression_ratio > 1.2:  # 20% threshold
                regressions.append({
                    "test": test_name,
                    "baseline": baseline_time,
                    "current": current_time,
                    "regression": regression_ratio
                })
    
    # Report results
    if regressions:
        print("\n⚠️  Performance regressions detected:")
        for reg in regressions:
            print(f"  {reg['test']}: {reg['regression']:.1f}x slower")
    else:
        print("\n✓ No performance regressions detected")
    
    return regressions

# Run the exercise
if __name__ == "__main__":
    test_performance_regression()
```

## Module 5: Troubleshooting

### Learning Objectives

- Master debugging techniques
- Learn systematic troubleshooting approaches
- Practice error diagnosis and resolution
- Understand preventive measures

### Exercise 5.1: Debugging Practice

```python
# Exercise 5.1: Debugging Real Issues
def debugging_practice():
    """Practice debugging common issues"""
    
    # Simulate common problems
    problems = [
        {
            "name": "compilation_timeout",
            "description": "Compilation hangs indefinitely",
            "source_code": """
def infinite_recursion(n: int) -> int:
    return infinite_recursion(n)  # Infinite recursion

def main():
    result = infinite_recursion(10)
    print(f"Result: {result}")
""",
            "solution": "Fix infinite recursion by adding base case"
        },
        {
            "name": "memory_error",
            "description": "Out of memory during compilation",
            "source_code": """
def memory_intensive():
    # Create very large data structure
    data = [0] * (10**9)  # 1 billion elements
    return sum(data)

def main():
    result = memory_intensive()
    print(f"Result: {result}")
""",
            "solution": "Reduce memory usage or use streaming"
        },
        {
            "name": "type_error",
            "description": "Type annotation mismatch",
            "source_code": """
def type_mismatch(x: int) -> str:
    return x + "string"  # Type error

def main():
    result = type_mismatch(5)
    print(f"Result: {result}")
""",
            "solution": "Fix type annotations or use proper type conversion"
        }
    ]
    
    for problem in problems:
        print(f"\n=== Debugging: {problem['name']} ===")
        print(f"Description: {problem['description']}")
        
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.codon', delete=False) as f:
            f.write(problem["source_code"])
            temp_file = f.name
        
        try:
            # Try to compile
            result = subprocess.run(
                ["codon", "build", temp_file],
                capture_output=True,
                text=True,
                timeout=30  # Add timeout
            )
            
            # Analyze the problem
            if result.returncode != 0:
                print(f"Error detected: {result.stderr[:200]}...")
                
                # Practice debugging steps
                print("\nDebugging steps:")
                print("1. Analyze error message")
                print("2. Identify root cause")
                print("3. Apply solution")
                print(f"4. Solution: {problem['solution']}")
                
                # Apply solution (simplified)
                print("5. Testing solution...")
                
            else:
                print("✓ No error detected (unexpected)")
                
        except subprocess.TimeoutExpired:
            print("⚠️  Compilation timed out")
            print("Debugging steps:")
            print("1. Check for infinite loops")
            print("2. Reduce complexity")
            print("3. Add timeouts")
            print(f"4. Solution: {problem['solution']}")
            
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    print("\n✓ Debugging practice completed!")

# Run the exercise
if __name__ == "__main__":
    debugging_practice()
```

### Exercise 5.2: System Diagnostics

```python
# Exercise 5.2: System Health Check
def system_diagnostics_practice():
    """Practice system diagnostics"""
    
    import psutil
    import os
    
    print("=== System Diagnostics Practice ===")
    
    # Check system resources
    print("\n1. System Resources:")
    print(f"  CPU Cores: {psutil.cpu_count()}")
    print(f"  Memory: {psutil.virtual_memory().total / 1024**3:.1f} GB")
    print(f"  Available Memory: {psutil.virtual_memory().available / 1024**3:.1f} GB")
    print(f"  Disk Free: {psutil.disk_usage('/').free / 1024**3:.1f} GB")
    
    # Check Codon installation
    print("\n2. Codon Installation:")
    try:
        result = subprocess.run(
            ["codon", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  ✓ Codon installed: {result.stdout.strip()}")
        else:
            print("  ✗ Codon not properly installed")
    except FileNotFoundError:
        print("  ✗ Codon not found in PATH")
    
    # Check Python environment
    print("\n3. Python Environment:")
    print(f"  Python Version: {sys.version}")
    print(f"  Python Path: {sys.executable}")
    print(f"  Virtual Env: {os.environ.get('VIRTUAL_ENV', 'None')}")
    
    # Check dependencies
    print("\n4. Dependencies:")
    try:
        import pytest
        print(f"  ✓ pytest: {pytest.__version__}")
    except ImportError:
        print("  ✗ pytest not installed")
    
    try:
        import faker
        print(f"  ✓ faker: {faker.__version__}")
    except ImportError:
        print("  ✗ faker not installed")
    
    # Check permissions
    print("\n5. Permissions:")
    temp_dir = tempfile.gettempdir()
    can_write_temp = os.access(temp_dir, os.W_OK)
    print(f"  Can write to temp: {'✓' if can_write_temp else '✗'}")
    
    can_execute = os.access(sys.executable, os.X_OK)
    print(f"  Can execute Python: {'✓' if can_execute else '✗'}")
    
    print("\n✓ System diagnostics completed!")

# Run the exercise
if __name__ == "__main__":
    system_diagnostics_practice()
```

## Practical Exercises

### Exercise A: Complete Testing Workflow

```python
# Exercise A: End-to-End Testing Workflow
def complete_testing_workflow():
    """Complete testing workflow exercise"""
    
    print("=== Complete Testing Workflow ===")
    
    # Step 1: Setup test environment
    print("\n1. Setting up test environment...")
    temp_dir = tempfile.mkdtemp(prefix="codon_workflow_")
    
    try:
        # Step 2: Create test source code
        print("2. Creating test source code...")
        source_code = """
def matrix_multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    rows_a = len(a)
    cols_a = len(a[0])
    cols_b = len(b[0])
    
    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    
    return result

def main():
    # Test matrix multiplication
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    result = matrix_multiply(a, b)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""
        
        source_file = os.path.join(temp_dir, "matrix_test.codon")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        # Step 3: Compilation testing
        print("3. Testing compilation...")
        compile_result = subprocess.run(
            ["codon", "build", source_file],
            capture_output=True,
            text=True
        )
        
        assert compile_result.returncode == 0, f"Compilation failed: {compile_result.stderr}"
        print("  ✓ Compilation successful")
        
        # Step 4: Performance testing
        print("4. Testing performance...")
        executable = os.path.join(temp_dir, "matrix_test")
        
        # Measure execution time
        start_time = time.time()
        exec_result = subprocess.run(
            [executable],
            capture_output=True,
            text=True
        )
        execution_time = time.time() - start_time
        
        assert exec_result.returncode == 0, f"Execution failed: {exec_result.stderr}"
        print(f"  ✓ Execution successful in {execution_time:.3f}s")
        
        # Step 5: Result validation
        print("5. Validating results...")
        assert "Result:" in exec_result.stdout
        print("  ✓ Results validated")
        
        # Step 6: Error handling test
        print("6. Testing error handling...")
        error_source = """
def error_function():
    return 1 / 0

def main():
    error_function()
"""
        
        error_file = os.path.join(temp_dir, "error_test.codon")
        with open(error_file, 'w') as f:
            f.write(error_source)
        
        error_compile = subprocess.run(
            ["codon", "build", error_file],
            capture_output=True,
            text=True
        )
        
        # Should compile successfully but fail at runtime
        assert error_compile.returncode == 0, "Error test should compile"
        
        error_executable = os.path.join(temp_dir, "error_test")
        error_exec = subprocess.run(
            [error_executable],
            capture_output=True,
            text=True
        )
        
        # Should fail at runtime
        assert error_exec.returncode != 0, "Error test should fail at runtime"
        print("  ✓ Error handling validated")
        
        print("\n✓ Complete testing workflow successful!")
        return True
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

# Run the exercise
if __name__ == "__main__":
    complete_testing_workflow()
```

### Exercise B: Team Collaboration

```python
# Exercise B: Team Collaboration Exercise
def team_collaboration_exercise():
    """Team collaboration exercise"""
    
    print("=== Team Collaboration Exercise ===")
    
    # Simulate team roles
    roles = [
        "Test Developer",
        "Performance Engineer", 
        "DevOps Engineer",
        "Quality Assurance"
    ]
    
    # Assign tasks to team members
    tasks = {
        "Test Developer": [
            "Write unit tests for compilation",
            "Create integration tests",
            "Implement test fixtures"
        ],
        "Performance Engineer": [
            "Design performance benchmarks",
            "Implement regression detection",
            "Optimize test execution"
        ],
        "DevOps Engineer": [
            "Set up CI/CD pipeline",
            "Configure test environments",
            "Implement monitoring"
        ],
        "Quality Assurance": [
            "Review test coverage",
            "Validate test results",
            "Document test procedures"
        ]
    }
    
    print("\nTeam Roles and Responsibilities:")
    for role, role_tasks in tasks.items():
        print(f"\n{role}:")
        for task in role_tasks:
            print(f"  - {task}")
    
    # Simulate collaborative testing
    print("\nSimulating collaborative testing...")
    
    # 1. Test Developer creates tests
    print("1. Test Developer creating tests...")
    test_code = create_sample_tests()
    
    # 2. Performance Engineer benchmarks
    print("2. Performance Engineer benchmarking...")
    perf_results = run_performance_benchmarks()
    
    # 3. DevOps Engineer sets up CI
    print("3. DevOps Engineer setting up CI...")
    ci_config = create_ci_configuration()
    
    # 4. QA validates results
    print("4. QA validating results...")
    qa_report = validate_test_results()
    
    print("\n✓ Team collaboration exercise completed!")
    return {
        "tests": test_code,
        "performance": perf_results,
        "ci_config": ci_config,
        "qa_report": qa_report
    }

def create_sample_tests():
    """Create sample tests for collaboration exercise"""
    return """
def test_compilation_success():
    assert compile_codon_code("def test(): return 42").success

def test_performance_benchmark():
    result = benchmark_performance()
    assert result["speedup"] > 1.0

def test_error_handling():
    assert not compile_codon_code("def invalid(").success
"""

def run_performance_benchmarks():
    """Run performance benchmarks for collaboration exercise"""
    return {
        "compilation_time": 2.5,
        "execution_speedup": 15.3,
        "memory_usage": 150.0
    }

def create_ci_configuration():
    """Create CI configuration for collaboration exercise"""
    return """
test_codon:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Setup Codon
      run: curl -fsSL https://exaloop.io/install.sh | bash
    - name: Run Tests
      run: pytest tests/codon/
"""

def validate_test_results():
    """Validate test results for collaboration exercise"""
    return {
        "test_coverage": 95.2,
        "performance_regression": False,
        "all_tests_passing": True,
        "documentation_complete": True
    }

# Run the exercise
if __name__ == "__main__":
    team_collaboration_exercise()
```

## Assessment and Certification

### Final Assessment

```python
def final_assessment():
    """Final assessment for Codon testing training"""
    
    print("=== Final Assessment ===")
    
    assessment_questions = [
        {
            "question": "What is the primary purpose of Codon testing?",
            "options": [
                "To find bugs in Python code",
                "To validate compilation and performance",
                "To reduce code size",
                "To improve documentation"
            ],
            "correct": 1,
            "points": 10
        },
        {
            "question": "Which testing approach is recommended for Codon components?",
            "options": [
                "Manual testing only",
                "Automated testing with comprehensive coverage",
                "Random testing",
                "No testing required"
            ],
            "correct": 1,
            "points": 10
        },
        {
            "question": "What is the minimum acceptable test coverage for Codon components?",
            "options": [
                "50%",
                "70%",
                "90%",
                "100%"
            ],
            "correct": 2,
            "points": 10
        },
        {
            "question": "How should performance regressions be handled?",
            "options": [
                "Ignore them",
                "Automatically detect and alert",
                "Only check manually",
                "Disable performance tests"
            ],
            "correct": 1,
            "points": 10
        },
        {
            "question": "What is the best practice for error handling in Codon tests?",
            "options": [
                "Ignore errors",
                "Test all error scenarios systematically",
                "Only test happy path",
                "Let errors occur naturally"
            ],
            "correct": 1,
            "points": 10
        }
    ]
    
    total_score = 0
    max_score = sum(q["points"] for q in assessment_questions)
    
    print(f"\nAssessment consists of {len(assessment_questions)} questions.")
    print(f"Total possible score: {max_score} points")
    print("Passing score: 80% ({:.0f} points)\n".format(max_score * 0.8))
    
    for i, question in enumerate(assessment_questions, 1):
        print(f"Question {i}: {question['question']}")
        for j, option in enumerate(question['options']):
            print(f"  {j+1}. {option}")
        
        while True:
            try:
                answer = int(input("Your answer (1-4): ")) - 1
                if 0 <= answer <= 3:
                    break
                else:
                    print("Please enter a number between 1 and 4.")
            except ValueError:
                print("Please enter a valid number.")
        
        if answer == question["correct"]:
            total_score += question["points"]
            print("✓ Correct!")
        else:
            print(f"✗ Incorrect. Correct answer: {question['correct']+1}")
        
        print()
    
    # Calculate percentage
    percentage = (total_score / max_score) * 100
    
    print(f"Final Score: {total_score}/{max_score} ({percentage:.1f}%)")
    
    if percentage >= 80:
        print("🎉 CONGRATULATIONS! You have passed the Codon Testing Certification!")
        print("You are now certified in Codon testing best practices.")
    else:
        print("📚 Keep studying! Review the materials and try again.")
        print("You need 80% to pass the certification.")
    
    return percentage >= 80

# Run the assessment
if __name__ == "__main__":
    final_assessment()
```

## Resources and References

### Additional Learning Resources

1. **Official Documentation**
   - [Codon Documentation](https://docs.exaloop.io/codon)
   - [Python Testing with pytest](https://docs.pytest.org/)
   - [Performance Testing Best Practices](https://realpython.com/python-performance-testing/)

2. **Recommended Books**
   - "Python Testing with pytest" by Brian Okken
   - "Effective Python" by Brett Slatkin
   - "High Performance Python" by Micha Gorelick

3. **Online Courses**
   - Python Testing Fundamentals
   - Performance Testing and Optimization
   - Advanced Python Programming

4. **Community Resources**
   - Python Testing Community
   - Performance Engineering Forums
   - Codon/Codon User Groups

### Practice Projects

1. **Beginner Projects**
   - Create a simple calculator with Codon
   - Build a basic data processing pipeline
   - Implement sorting algorithms

2. **Intermediate Projects**
   - Develop a performance benchmarking framework
   - Create comprehensive test suites
   - Build integration testing tools

3. **Advanced Projects**
   - Design a complete testing framework
   - Implement automated performance monitoring
   - Create CI/CD pipelines for Codon

### Certification Path

1. **Foundation Level**
   - Complete Module 1-2 exercises
   - Pass basic assessment
   - Demonstrate basic testing skills

2. **Intermediate Level**
   - Complete Module 3-4 exercises
   - Pass intermediate assessment
   - Show proficiency in advanced testing

3. **Expert Level**
   - Complete all modules and exercises
   - Pass final assessment with 90%+
   - Contribute to testing framework development

### Continuing Education

1. **Regular Updates**
   - Stay current with Codon/Codon updates
   - Follow testing best practices evolution
   - Participate in community discussions

2. **Skill Development**
   - Practice with real-world projects
   - Contribute to open source testing tools
   - Mentor other team members

3. **Knowledge Sharing**
   - Present testing findings to team
   - Write testing documentation
   - Conduct training sessions

## Conclusion

This comprehensive training program provides teams with the knowledge, skills, and practical experience needed to excel in Codon testing. By following this structured approach, participants will:

- **Master Testing Fundamentals**: Understand core testing principles and methodologies
- **Develop Practical Skills**: Gain hands-on experience with real testing scenarios
- **Build Problem-Solving Abilities**: Learn to diagnose and resolve testing issues
- **Apply Best Practices**: Implement industry-standard testing approaches
- **Contribute to Team Success**: Work effectively in collaborative testing environments

The training materials are designed to be practical, engaging, and immediately applicable to real-world Codon testing challenges. Regular practice and continuous learning will ensure ongoing success in Codon testing endeavors.

For additional support or questions about the training materials, please refer to the testing guide and troubleshooting documentation. 