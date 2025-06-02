"""
FastAPI application fixtures for GraphMemory-IDE integration testing.
Provides isolated app instances with dependency overrides and test configurations.
"""

import os
from typing import Dict, Any, AsyncGenerator, Optional
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Test application configuration
TEST_APP_CONFIG = {
    "title": "GraphMemory-IDE Test API",
    "version": "test-1.0.0",
    "debug": True,
    "testing": True,
    "log_level": "DEBUG",
}

@pytest.fixture(scope="function")
def test_app_config() -> Dict[str, Any]:
    """Get test application configuration."""
    return {
        **TEST_APP_CONFIG,
        "database_url": "sqlite:///test.db",
        "redis_url": "redis://localhost:6379/15",
        "secret_key": "test-secret-key-do-not-use-in-production",
        "jwt_algorithm": "HS256",
        "jwt_expiration": 3600,
        "cors_origins": ["http://localhost:3000", "http://localhost:8501"],
        "environment": "test"
    }

@pytest.fixture(scope="function")
def mock_environment_variables(test_app_config: Dict[str, Any]) -> None:
    """Mock environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "test",
        "DEBUG": "true",
        "SECRET_KEY": test_app_config["secret_key"],
        "DATABASE_URL": test_app_config["database_url"],
        "REDIS_URL": test_app_config["redis_url"],
        "JWT_ALGORITHM": test_app_config["jwt_algorithm"],
        "JWT_EXPIRATION": str(test_app_config["jwt_expiration"]),
        "CORS_ORIGINS": ",".join(test_app_config["cors_origins"]),
        "LOG_LEVEL": "DEBUG"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture(scope="function")
def base_app(mock_environment_variables) -> FastAPI:
    """Create a base FastAPI application for testing."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(
        title=TEST_APP_CONFIG["title"],
        version=TEST_APP_CONFIG["version"],
        debug=TEST_APP_CONFIG["debug"]
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in tests
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add basic health check endpoint
    @app.get("/health")
    async def health_check() -> None:
        return {"status": "healthy", "environment": "test"}
    
    return app

@pytest.fixture(scope="function")
def mcp_server_app(base_app: FastAPI, isolated_databases) -> FastAPI:
    """Create MCP server application with test dependencies."""
    # Import MCP server modules (these would be actual imports in real code)
    # For now, creating mock endpoints for testing
    
    @base_app.post("/mcp/memory/create")
    async def create_memory(memory_data: dict) -> None:
        """Mock MCP memory creation endpoint."""
        return {
            "id": "test-memory-001",
            "status": "created",
            "data": memory_data
        }
    
    @base_app.get("/mcp/memory/{memory_id}")
    async def get_memory(memory_id: str) -> None:
        """Mock MCP memory retrieval endpoint."""
        return {
            "id": memory_id,
            "content": "Test memory content",
            "memory_type": "procedural",
            "created_at": "2025-05-29T11:35:32Z"
        }
    
    @base_app.get("/mcp/search")
    async def search_memories(query: str) -> None:
        """Mock MCP memory search endpoint."""
        return {
            "query": query,
            "results": [
                {
                    "id": "test-result-001",
                    "content": f"Search result for: {query}",
                    "relevance": 0.95
                }
            ]
        }
    
    # Override database dependencies with test databases
    def get_test_kuzu_connection() -> None:
        return isolated_databases["kuzu"]
    
    def get_test_redis_client() -> None:
        return isolated_databases["redis"]
    
    def get_test_sqlite_connection() -> None:
        return isolated_databases["sqlite"]
    
    # Add dependency overrides
    base_app.dependency_overrides.update({
        # These would map to actual dependency functions in production
        "get_kuzu_connection": get_test_kuzu_connection,
        "get_redis_client": get_test_redis_client,
        "get_sqlite_connection": get_test_sqlite_connection,
    })
    
    return base_app

@pytest.fixture(scope="function")
def analytics_engine_app(base_app: FastAPI, isolated_databases) -> FastAPI:
    """Create analytics engine application with test dependencies."""
    
    @base_app.post("/analytics/process")
    async def process_analytics(data: dict) -> None:
        """Mock analytics processing endpoint."""
        return {
            "job_id": "test-analytics-001",
            "status": "processing",
            "input_data": data,
            "estimated_completion": "2025-05-29T11:40:32Z"
        }
    
    @base_app.get("/analytics/results/{job_id}")
    async def get_analytics_results(job_id: str) -> None:
        """Mock analytics results endpoint."""
        return {
            "job_id": job_id,
            "status": "completed",
            "results": {
                "insights": ["Test insight 1", "Test insight 2"],
                "metrics": {"accuracy": 0.95, "processing_time": 1.23}
            }
        }
    
    @base_app.get("/analytics/health")
    async def analytics_health() -> None:
        """Mock analytics health check."""
        return {
            "status": "healthy",
            "gpu_available": False,  # Set to False for testing
            "models_loaded": ["test-model-v1"],
            "queue_size": 0
        }
    
    return base_app

@pytest.fixture(scope="function")
def dashboard_sse_app(base_app: FastAPI) -> FastAPI:
    """Create dashboard SSE application for real-time testing."""
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    @base_app.get("/dashboard/sse")
    async def dashboard_sse() -> None:
        """Mock SSE endpoint for dashboard updates."""
        async def event_stream() -> None:
            for i in range(5):  # Send 5 test events
                event_data = {
                    "event": "dashboard_update",
                    "data": {
                        "timestamp": "2025-05-29T11:35:32Z",
                        "metric": "test_metric",
                        "value": i * 10,
                        "status": "active"
                    }
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(0.1)  # Small delay between events
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    @base_app.get("/dashboard/metrics")
    async def get_dashboard_metrics() -> None:
        """Mock dashboard metrics endpoint."""
        return {
            "cpu_usage": 45.2,
            "memory_usage": 62.1,
            "active_connections": 12,
            "alerts_count": 3,
            "last_updated": "2025-05-29T11:35:32Z"
        }
    
    return base_app

@pytest.fixture(scope="function")
def alert_system_app(base_app: FastAPI, isolated_databases) -> FastAPI:
    """Create alert system application with test dependencies."""
    
    @base_app.post("/alerts/create")
    async def create_alert(alert_data: dict) -> None:
        """Mock alert creation endpoint."""
        return {
            "id": "test-alert-001",
            "status": "created",
            "severity": alert_data.get("severity", "medium"),
            "message": alert_data.get("message", "Test alert"),
            "created_at": "2025-05-29T11:35:32Z"
        }
    
    @base_app.get("/alerts")
    async def get_alerts(status: str = "all") -> None:
        """Mock alerts listing endpoint."""
        return {
            "alerts": [
                {
                    "id": "test-alert-001",
                    "severity": "high",
                    "status": "pending",
                    "message": "Test alert message",
                    "created_at": "2025-05-29T11:35:32Z"
                }
            ],
            "total": 1,
            "status_filter": status
        }
    
    @base_app.post("/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(alert_id: str) -> None:
        """Mock alert acknowledgment endpoint."""
        return {
            "id": alert_id,
            "status": "acknowledged",
            "acknowledged_at": "2025-05-29T11:35:32Z"
        }
    
    return base_app

# Combined application fixture for full integration tests
@pytest.fixture(scope="function")
def integrated_app(
    mcp_server_app: FastAPI,
    analytics_engine_app: FastAPI,
    dashboard_sse_app: FastAPI,
    alert_system_app: FastAPI
) -> FastAPI:
    """Create a fully integrated application with all components."""
    # In a real implementation, this would combine all the separate apps
    # For testing, we'll use the MCP server app as the base and add routes
    app = mcp_server_app
    
    # Add integration endpoint
    @app.get("/integration/status")
    async def integration_status() -> None:
        """Check status of all integrated components."""
        return {
            "mcp_server": "healthy",
            "analytics_engine": "healthy",
            "dashboard_sse": "healthy",
            "alert_system": "healthy",
            "integration_status": "fully_operational"
        }
    
    return app

# Test client fixtures
@pytest.fixture(scope="function")
def test_client(integrated_app: FastAPI) -> TestClient:
    """Create a synchronous test client."""
    return TestClient(integrated_app)

@pytest_asyncio.fixture(scope="function")
async def async_client(integrated_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an asynchronous test client for async testing."""
    transport = ASGITransport(app=integrated_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=30.0
    ) as client:
        yield client

# Application lifecycle fixtures
@pytest_asyncio.fixture(scope="function")
async def app_with_startup_shutdown(base_app: FastAPI) -> None:
    """Test application startup and shutdown events."""
    startup_completed = False
    shutdown_completed = False
    
    @base_app.on_event("startup")
    async def startup_event() -> None:
        nonlocal startup_completed
        startup_completed = True
        print("Test app startup completed")
    
    @base_app.on_event("shutdown")
    async def shutdown_event() -> None:
        nonlocal shutdown_completed
        shutdown_completed = True
        print("Test app shutdown completed")
    
    # Simulate app lifecycle
    async with AsyncClient(
        transport=ASGITransport(app=base_app),
        base_url="http://testserver"
    ) as client:
        yield {
            "app": base_app,
            "client": client,
            "startup_completed": startup_completed,
            "shutdown_completed": shutdown_completed
        }

# Performance testing fixture
@pytest.fixture(scope="function")
def app_performance_monitor() -> None:
    """Monitor application performance during tests."""
    import time
    from collections import defaultdict
    
    class AppPerformanceMonitor:
        def __init__(self) -> None:
            self.request_times = defaultdict(list)
            self.error_counts = defaultdict(int)
        
        def record_request(self, endpoint: str, duration: float, status_code: int) -> None:
            """Record request performance metrics."""
            self.request_times[endpoint].append(duration)
            if status_code >= 400:
                self.error_counts[endpoint] += 1
        
        def get_stats(self) -> None:
            """Get performance statistics."""
            stats = {}
            for endpoint, times in self.request_times.items():
                if times:
                    stats[endpoint] = {
                        "avg_response_time": sum(times) / len(times),
                        "max_response_time": max(times),
                        "min_response_time": min(times),
                        "total_requests": len(times),
                        "error_count": self.error_counts[endpoint],
                        "error_rate": self.error_counts[endpoint] / len(times)
                    }
            return stats
    
    return AppPerformanceMonitor() 