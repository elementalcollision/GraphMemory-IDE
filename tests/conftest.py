# tests/conftest.py
"""
Central pytest configuration for GraphMemory-IDE Integration Testing
Modern async testing infrastructure with comprehensive fixtures and utilities.
"""

import asyncio
import os
import sys
import tempfile
import warnings
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all fixture modules
from tests.fixtures.application import *  # FastAPI app fixtures
from tests.fixtures.database import *     # Database isolation fixtures  
from tests.fixtures.clients import *      # HTTP/WebSocket client fixtures
from tests.fixtures.authentication import *  # Auth and user fixtures
from tests.fixtures.data_factories import *  # Test data generation
from tests.fixtures.services import *     # External service mocks/toggles

# Import utilities
from tests.utils.test_helpers import *
from tests.utils.cleanup import *

# Configure warnings for clean test output
warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")
warnings.filterwarnings("ignore", category=ResourceWarning)

# Test environment configuration
TEST_ENV = os.getenv("TEST_ENV", "local")
USE_REAL_SERVICES = os.getenv("USE_REAL_SERVICES", "false").lower() == "true"
DEBUG_TESTS = os.getenv("DEBUG_TESTS", "false").lower() == "true"

# Global test configuration
pytest_plugins = [
    "pytest_asyncio",
    "pytest_cov",
    "pytest_timeout",
]

# Test session configuration
def pytest_configure(config):
    """Configure pytest session with custom settings."""
    # Set test environment markers
    config.addinivalue_line("markers", f"env_{TEST_ENV}: Tests for {TEST_ENV} environment")
    
    # Configure asyncio for proper event loop handling
    if hasattr(asyncio, 'set_event_loop_policy'):
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        else:
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

def pytest_sessionstart(session):
    """Actions to perform at the start of test session."""
    print(f"\n🚀 Starting GraphMemory-IDE Integration Tests")
    print(f"   Environment: {TEST_ENV}")
    print(f"   Real Services: {USE_REAL_SERVICES}")
    print(f"   Debug Mode: {DEBUG_TESTS}")
    print(f"   Python: {sys.version}")
    print(f"   Working Directory: {os.getcwd()}")

def pytest_sessionfinish(session, exitstatus):
    """Actions to perform at the end of test session."""
    print(f"\n✅ Integration Test Session Complete (Exit Code: {exitstatus})")

# Async event loop configuration for 2025 best practices
@pytest_asyncio.fixture(scope="function")
async def event_loop():
    """Create a new event loop for each test function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        # Clean up any pending tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        
        loop.close()

# Test environment fixtures
@pytest.fixture(scope="function")
def test_env() -> str:
    """Get the current test environment."""
    return TEST_ENV

@pytest.fixture(scope="function")
def use_real_services() -> bool:
    """Determine if tests should use real external services."""
    return USE_REAL_SERVICES

@pytest.fixture(scope="function")
def debug_mode() -> bool:
    """Determine if tests are running in debug mode."""
    return DEBUG_TESTS

# Temporary directory fixture for test isolation
@pytest.fixture(scope="function")
def temp_dir() -> Path:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory(prefix="graphmemory_test_") as tmp_dir:
        yield Path(tmp_dir)

# Test data directory fixture
@pytest.fixture(scope="function")
def test_data_dir() -> Path:
    """Get the test data directory."""
    test_data_path = Path(__file__).parent / "data"
    test_data_path.mkdir(exist_ok=True)
    return test_data_path

# Performance monitoring fixture
@pytest.fixture(scope="function", autouse=True)
async def monitor_test_performance(request):
    """Monitor test performance and resource usage."""
    import time
    import psutil
    
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss
    
    yield
    
    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss
    
    duration = end_time - start_time
    memory_delta = end_memory - start_memory
    
    # Log performance metrics for slow tests
    if duration > 5.0:  # Log tests taking more than 5 seconds
        print(f"\n⚠️  Slow Test: {request.node.name}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Memory Delta: {memory_delta / 1024 / 1024:.2f}MB")

# Test isolation fixture (autouse ensures it runs for every test)
@pytest.fixture(scope="function", autouse=True)
async def ensure_test_isolation():
    """Ensure proper test isolation and cleanup."""
    # Pre-test setup
    original_env = dict(os.environ)
    
    yield
    
    # Post-test cleanup
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)
    
    # Force garbage collection
    import gc
    gc.collect()

# Error handling and reporting
@pytest.fixture(scope="function", autouse=True)
def capture_test_errors(request):
    """Capture and log detailed error information."""
    yield
    
    if request.node.rep_call.failed:
        print(f"\n❌ Test Failed: {request.node.name}")
        print(f"   Error: {request.node.rep_call.longrepr}")

def pytest_runtest_makereport(item, call):
    """Generate detailed test reports."""
    if "rep_" + call.when not in item:
        setattr(item, "rep_" + call.when, call)

# Custom test markers for dynamic configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add dynamic markers."""
    for item in items:
        # Add environment-specific markers
        item.add_marker(pytest.mark.env(TEST_ENV))
        
        # Add service type markers
        if USE_REAL_SERVICES:
            item.add_marker(pytest.mark.real_services)
        else:
            item.add_marker(pytest.mark.mock_services)
        
        # Add component markers based on test file location
        test_file = str(item.fspath)
        if "analytics" in test_file:
            item.add_marker(pytest.mark.analytics)
        elif "dashboard" in test_file:
            item.add_marker(pytest.mark.dashboard)
        elif "alerts" in test_file:
            item.add_marker(pytest.mark.alerts)
        elif "auth" in test_file:
            item.add_marker(pytest.mark.authentication)

# Integration test utilities
@pytest.fixture(scope="function")
def integration_config() -> Dict[str, Any]:
    """Get configuration for integration tests."""
    return {
        "test_env": TEST_ENV,
        "use_real_services": USE_REAL_SERVICES,
        "debug_mode": DEBUG_TESTS,
        "timeout": 300,
        "max_retries": 3,
        "cleanup_timeout": 30,
    }

# Health check fixture for external dependencies
@pytest_asyncio.fixture(scope="session")
async def health_check_external_services():
    """Check health of external services before running tests."""
    if not USE_REAL_SERVICES:
        return True
    
    health_checks = []
    
    # Add health checks for external services here
    # For example: Redis, external APIs, etc.
    
    return all(health_checks) if health_checks else True

# Test data cleanup
@pytest.fixture(scope="function", autouse=True)
async def cleanup_test_data():
    """Ensure test data is cleaned up after each test."""
    yield
    
    # Cleanup logic will be implemented in individual fixture modules
    # This fixture serves as a coordination point for cleanup
    pass

# Logging configuration for tests
@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for test session."""
    import logging
    
    # Set up test-specific logging
    logging.basicConfig(
        level=logging.DEBUG if DEBUG_TESTS else logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# Memory leak detection
@pytest.fixture(scope="function", autouse=True)
def detect_memory_leaks():
    """Detect potential memory leaks in tests."""
    import gc
    import tracemalloc
    
    # Start tracing memory allocations
    tracemalloc.start()
    gc.collect()
    
    yield
    
    # Check for memory leaks
    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Log if memory usage is high
    if peak > 100 * 1024 * 1024:  # 100MB
        print(f"\n⚠️  High memory usage detected: {peak / 1024 / 1024:.2f}MB peak") 