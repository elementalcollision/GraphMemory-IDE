"""
Smoke Tests for GraphMemory-IDE
Basic validation that critical functionality is working after deployment.
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any
import os


class TestSmokeTests:
    """Basic smoke tests for critical functionality."""
    
    @pytest.mark.asyncio
    async def test_api_health_check(self) -> None:
        """Test that the API health check endpoint is working."""
        base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            
            health_data = response.json()
            assert "status" in health_data, "Health check response missing status"
            
            print("✅ API health check passed")
    
    @pytest.mark.asyncio
    async def test_api_docs_accessible(self) -> None:
        """Test that API documentation is accessible."""
        base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/docs")
            
            assert response.status_code == 200, f"API docs not accessible: {response.status_code}"
            assert len(response.content) > 1000, "API docs content too small"
            
            print("✅ API documentation accessible")
    
    @pytest.mark.asyncio
    async def test_memory_graph_endpoint(self) -> None:
        """Test that memory graph endpoint is working."""
        base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{base_url}/api/memory/graph")
            
            assert response.status_code == 200, f"Memory graph endpoint failed: {response.status_code}"
            
            graph_data = response.json()
            assert isinstance(graph_data, dict), "Memory graph response should be a dictionary"
            
            print("✅ Memory graph endpoint working")
    
    @pytest.mark.asyncio
    async def test_analytics_dashboard_endpoint(self) -> None:
        """Test that analytics dashboard endpoint is working."""
        base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{base_url}/api/analytics/dashboard")
            
            assert response.status_code == 200, f"Analytics dashboard failed: {response.status_code}"
            
            analytics_data = response.json()
            assert isinstance(analytics_data, dict), "Analytics response should be a dictionary"
            
            print("✅ Analytics dashboard endpoint working")
    
    @pytest.mark.asyncio
    async def test_basic_api_workflow(self) -> None:
        """Test basic API workflow with memory node creation and retrieval."""
        base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
        
        test_node = {
            "content": "Smoke test memory node",
            "type": "procedural",
            "tags": ["smoke-test"],
            "metadata": {
                "file_path": "/test/smoke_test.py",
                "line_numbers": [1, 5],
                "language": "python"
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create node
            create_response = await client.post(
                f"{base_url}/api/memory/nodes",
                json=test_node,
                timeout=15.0
            )
            
            assert create_response.status_code == 201, f"Node creation failed: {create_response.status_code}"
            
            created_node = create_response.json()
            node_id = created_node.get("id")
            assert node_id, "Created node should have an ID"
            
            # Retrieve node
            get_response = await client.get(
                f"{base_url}/api/memory/nodes/{node_id}",
                timeout=10.0
            )
            
            assert get_response.status_code == 200, f"Node retrieval failed: {get_response.status_code}"
            
            retrieved_node = get_response.json()
            assert retrieved_node["content"] == test_node["content"], "Retrieved content doesn't match"
            
            # Cleanup
            await client.delete(f"{base_url}/api/memory/nodes/{node_id}")
            
            print("✅ Basic API workflow test passed") 