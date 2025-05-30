"""
HTTP and WebSocket client fixtures for GraphMemory-IDE integration testing.
Provides test clients for various communication protocols.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Optional
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from fastapi.testclient import TestClient
import websockets
from websockets.legacy.client import WebSocketClientProtocol

@pytest_asyncio.fixture(scope="function")
async def http_client(integrated_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for API testing."""
    transport = ASGITransport(app=integrated_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=30.0,
        headers={"User-Agent": "GraphMemory-IDE-Test-Client"}
    ) as client:
        yield client

@pytest.fixture(scope="function")
def sync_client(integrated_app: FastAPI) -> TestClient:
    """Create a synchronous HTTP client for simple API testing."""
    return TestClient(
        integrated_app,
        base_url="http://testserver",
        headers={"User-Agent": "GraphMemory-IDE-Test-Client-Sync"}
    )

@pytest_asyncio.fixture(scope="function")
async def authenticated_client(http_client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated HTTP client with JWT token."""
    # Mock authentication - in real tests this would get a real token
    test_token = "test-jwt-token-do-not-use-in-production"
    
    # Add authentication header
    http_client.headers.update({
        "Authorization": f"Bearer {test_token}"
    })
    
    yield http_client

@pytest_asyncio.fixture(scope="function")
async def websocket_client():
    """Create a WebSocket client for testing real-time communications."""
    
    class MockWebSocketClient:
        def __init__(self):
            self.connected = False
            self.messages = []
            self.connection = None
        
        async def connect(self, uri: str):
            """Mock WebSocket connection."""
            self.connected = True
            self.uri = uri
            print(f"Mock WebSocket connected to {uri}")
        
        async def send(self, message: str):
            """Mock sending a message."""
            if not self.connected:
                raise ConnectionError("WebSocket not connected")
            self.messages.append({"type": "sent", "data": message})
        
        async def receive(self) -> str:
            """Mock receiving a message."""
            if not self.connected:
                raise ConnectionError("WebSocket not connected")
            
            # Return a mock message
            mock_message = {
                "event": "test_event",
                "data": {"timestamp": "2025-05-29T11:35:32Z", "status": "connected"}
            }
            return json.dumps(mock_message)
        
        async def close(self):
            """Mock closing the connection."""
            self.connected = False
            print("Mock WebSocket connection closed")
        
        def get_sent_messages(self):
            """Get all sent messages."""
            return [msg["data"] for msg in self.messages if msg["type"] == "sent"]
    
    client = MockWebSocketClient()
    yield client
    
    # Cleanup
    if client.connected:
        await client.close()

@pytest_asyncio.fixture(scope="function")
async def sse_client():
    """Create an SSE (Server-Sent Events) client for testing real-time updates."""
    
    class MockSSEClient:
        def __init__(self):
            self.connected = False
            self.events = []
            self.url = None
        
        async def connect(self, url: str):
            """Mock SSE connection."""
            self.connected = True
            self.url = url
            print(f"Mock SSE client connected to {url}")
        
        async def listen(self, timeout: float = 10.0):
            """Mock listening for SSE events."""
            if not self.connected:
                raise ConnectionError("SSE client not connected")
            
            # Generate mock events
            events = []
            for i in range(3):
                event = {
                    "id": f"event-{i}",
                    "event": "dashboard_update",
                    "data": {
                        "timestamp": "2025-05-29T11:35:32Z",
                        "metric": "test_metric",
                        "value": i * 10
                    }
                }
                events.append(event)
                await asyncio.sleep(0.1)  # Simulate delay between events
            
            self.events.extend(events)
            return events
        
        async def close(self):
            """Mock closing the SSE connection."""
            self.connected = False
            print("Mock SSE client connection closed")
        
        def get_received_events(self):
            """Get all received events."""
            return self.events.copy()
    
    client = MockSSEClient()
    yield client
    
    # Cleanup
    if client.connected:
        await client.close()

@pytest_asyncio.fixture(scope="function")
async def analytics_client(http_client: AsyncClient):
    """Create a specialized client for analytics engine testing."""
    
    class AnalyticsTestClient:
        def __init__(self, http_client: AsyncClient):
            self.client = http_client
            self.base_path = "/analytics"
        
        async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
            """Send data for analytics processing."""
            response = await self.client.post(f"{self.base_path}/process", json=data)
            response.raise_for_status()
            return response.json()
        
        async def get_results(self, job_id: str) -> Dict[str, Any]:
            """Get analytics results."""
            response = await self.client.get(f"{self.base_path}/results/{job_id}")
            response.raise_for_status()
            return response.json()
        
        async def health_check(self) -> Dict[str, Any]:
            """Check analytics engine health."""
            response = await self.client.get(f"{self.base_path}/health")
            response.raise_for_status()
            return response.json()
        
        async def submit_batch_job(self, batch_data: List[Dict[str, Any]]) -> List[str]:
            """Submit multiple analytics jobs."""
            job_ids = []
            for data in batch_data:
                result = await self.process_data(data)
                job_ids.append(result["job_id"])
            return job_ids
    
    yield AnalyticsTestClient(http_client)

@pytest_asyncio.fixture(scope="function")
async def mcp_client(authenticated_client: AsyncClient):
    """Create a specialized client for MCP server testing."""
    
    class MCPTestClient:
        def __init__(self, http_client: AsyncClient):
            self.client = http_client
            self.base_path = "/mcp"
        
        async def create_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
            """Create a new memory entry."""
            response = await self.client.post(f"{self.base_path}/memory/create", json=memory_data)
            response.raise_for_status()
            return response.json()
        
        async def get_memory(self, memory_id: str) -> Dict[str, Any]:
            """Retrieve a memory entry."""
            response = await self.client.get(f"{self.base_path}/memory/{memory_id}")
            response.raise_for_status()
            return response.json()
        
        async def search_memories(self, query: str) -> Dict[str, Any]:
            """Search for memories."""
            response = await self.client.get(f"{self.base_path}/search", params={"query": query})
            response.raise_for_status()
            return response.json()
        
        async def create_test_dataset(self, size: int = 10) -> List[str]:
            """Create a test dataset of memories."""
            memory_ids = []
            for i in range(size):
                memory_data = {
                    "content": f"Test memory content {i}",
                    "memory_type": "procedural",
                    "metadata": {"test_index": i}
                }
                result = await self.create_memory(memory_data)
                memory_ids.append(result["id"])
            return memory_ids
    
    yield MCPTestClient(authenticated_client)

@pytest_asyncio.fixture(scope="function")
async def alert_client(authenticated_client: AsyncClient):
    """Create a specialized client for alert system testing."""
    
    class AlertTestClient:
        def __init__(self, http_client: AsyncClient):
            self.client = http_client
            self.base_path = "/alerts"
        
        async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
            """Create a new alert."""
            response = await self.client.post(f"{self.base_path}/create", json=alert_data)
            response.raise_for_status()
            return response.json()
        
        async def get_alerts(self, status: str = "all") -> Dict[str, Any]:
            """Get alerts with optional status filter."""
            response = await self.client.get(f"{self.base_path}", params={"status": status})
            response.raise_for_status()
            return response.json()
        
        async def acknowledge_alert(self, alert_id: str) -> Dict[str, Any]:
            """Acknowledge an alert."""
            response = await self.client.post(f"{self.base_path}/{alert_id}/acknowledge")
            response.raise_for_status()
            return response.json()
        
        async def create_test_alerts(self, count: int = 5) -> List[str]:
            """Create multiple test alerts."""
            alert_ids = []
            severities = ["low", "medium", "high", "critical"]
            
            for i in range(count):
                alert_data = {
                    "severity": severities[i % len(severities)],
                    "message": f"Test alert {i + 1}",
                    "source": "test_client",
                    "metric_name": f"test_metric_{i}",
                    "metric_value": i * 10,
                    "threshold": (i + 1) * 5
                }
                result = await self.create_alert(alert_data)
                alert_ids.append(result["id"])
            
            return alert_ids
    
    yield AlertTestClient(authenticated_client)

@pytest_asyncio.fixture(scope="function")
async def dashboard_client(http_client: AsyncClient, sse_client):
    """Create a specialized client for dashboard testing."""
    
    class DashboardTestClient:
        def __init__(self, http_client: AsyncClient, sse_client):
            self.client = http_client
            self.sse_client = sse_client
            self.base_path = "/dashboard"
        
        async def get_metrics(self) -> Dict[str, Any]:
            """Get dashboard metrics."""
            response = await self.client.get(f"{self.base_path}/metrics")
            response.raise_for_status()
            return response.json()
        
        async def connect_sse(self):
            """Connect to dashboard SSE stream."""
            await self.sse_client.connect(f"{self.base_path}/sse")
        
        async def listen_for_updates(self, timeout: float = 5.0) -> List[Dict[str, Any]]:
            """Listen for real-time dashboard updates."""
            if not self.sse_client.connected:
                await self.connect_sse()
            
            return await self.sse_client.listen(timeout)
        
        async def validate_real_time_flow(self) -> Dict[str, Any]:
            """Validate end-to-end real-time data flow."""
            # Get initial metrics
            initial_metrics = await self.get_metrics()
            
            # Connect to SSE stream
            await self.connect_sse()
            
            # Listen for updates
            updates = await self.listen_for_updates()
            
            # Get final metrics
            final_metrics = await self.get_metrics()
            
            return {
                "initial_metrics": initial_metrics,
                "real_time_updates": updates,
                "final_metrics": final_metrics,
                "flow_validated": len(updates) > 0
            }
    
    yield DashboardTestClient(http_client, sse_client)

# Performance testing client fixtures
@pytest_asyncio.fixture(scope="function")
async def load_test_clients(integrated_app: FastAPI):
    """Create multiple clients for load testing."""
    
    class LoadTestManager:
        def __init__(self, app: FastAPI, client_count: int = 10):
            self.app = app
            self.client_count = client_count
            self.clients = []
        
        async def __aenter__(self):
            """Create multiple async clients."""
            for i in range(self.client_count):
                transport = ASGITransport(app=self.app)
                client = AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                    timeout=30.0,
                    headers={"User-Agent": f"LoadTest-Client-{i}"}
                )
                self.clients.append(client)
            
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Close all clients."""
            for client in self.clients:
                await client.aclose()
        
        async def concurrent_requests(self, endpoint: str, count: int = None):
            """Make concurrent requests to an endpoint."""
            if count is None:
                count = self.client_count
            
            tasks = []
            for i in range(count):
                client = self.clients[i % len(self.clients)]
                task = asyncio.create_task(client.get(endpoint))
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            return responses
    
    async with LoadTestManager(integrated_app) as manager:
        yield manager

# Client health monitoring
@pytest.fixture(scope="function")
def client_health_monitor():
    """Monitor client connection health during tests."""
    
    class ClientHealthMonitor:
        def __init__(self):
            self.connection_attempts = 0
            self.successful_connections = 0
            self.failed_connections = 0
            self.response_times = []
        
        def record_connection_attempt(self, success: bool, response_time: float = None):
            """Record a connection attempt."""
            self.connection_attempts += 1
            if success:
                self.successful_connections += 1
                if response_time:
                    self.response_times.append(response_time)
            else:
                self.failed_connections += 1
        
        def get_health_stats(self):
            """Get connection health statistics."""
            success_rate = (
                self.successful_connections / self.connection_attempts
                if self.connection_attempts > 0 else 0
            )
            
            avg_response_time = (
                sum(self.response_times) / len(self.response_times)
                if self.response_times else 0
            )
            
            return {
                "total_attempts": self.connection_attempts,
                "successful_connections": self.successful_connections,
                "failed_connections": self.failed_connections,
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "max_response_time": max(self.response_times) if self.response_times else 0
            }
    
    return ClientHealthMonitor() 