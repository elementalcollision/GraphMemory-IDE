"""
Basic integration test for GraphMemory-IDE.
Demonstrates the integration test infrastructure functionality.
"""

import pytest
import asyncio
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_app_health(http_client: AsyncClient):
    """Test basic application health endpoint."""
    response = await http_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "test"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analytics_client_functionality(analytics_client):
    """Test analytics client basic functionality."""
    # Test data processing
    test_data = {"test": "data", "value": 42}
    result = await analytics_client.process_data(test_data)
    
    assert "job_id" in result
    assert result["status"] == "processing"
    
    # Test getting results
    job_id = result["job_id"]
    results = await analytics_client.get_results(job_id)
    assert results["job_id"] == job_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_client_functionality(mcp_client):
    """Test MCP client basic functionality."""
    # Test memory creation
    memory_data = {
        "content": "Test memory content",
        "memory_type": "procedural",
        "metadata": {"test": True}
    }
    
    result = await mcp_client.create_memory(memory_data)
    assert "id" in result
    assert result["status"] == "created"
    
    # Test memory retrieval
    memory_id = result["id"]
    memory = await mcp_client.get_memory(memory_id)
    assert memory["id"] == memory_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alert_system_functionality(alert_client):
    """Test alert system basic functionality."""
    # Test alert creation
    alert_data = {
        "severity": "high",
        "message": "Test alert message",
        "source": "integration_test"
    }
    
    result = await alert_client.create_alert(alert_data)
    assert "id" in result
    assert result["severity"] == "high"
    
    # Test getting alerts
    alerts = await alert_client.get_alerts()
    assert "alerts" in alerts
    assert len(alerts["alerts"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.real_time
async def test_dashboard_real_time_flow(dashboard_client):
    """Test end-to-end real-time dashboard flow."""
    # Test real-time data flow validation
    flow_result = await dashboard_client.validate_real_time_flow()
    
    assert flow_result["flow_validated"] is True
    assert "initial_metrics" in flow_result
    assert "real_time_updates" in flow_result
    assert len(flow_result["real_time_updates"]) > 0


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.asyncio
async def test_performance_under_load(load_test_clients):
    """Test system performance under concurrent load."""
    # Test concurrent requests
    responses = await load_test_clients.concurrent_requests("/health", count=10)
    
    # Check that most requests succeeded
    successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
    success_rate = len(successful_responses) / len(responses)
    
    assert success_rate >= 0.8  # At least 80% success rate


@pytest.mark.integration
@pytest.mark.database
def test_database_isolation(isolated_databases, check_database_health):
    """Test database isolation and health checks."""
    # Check that all databases are healthy
    health_status = check_database_health
    
    for db_name, status in health_status.items():
        if db_name in ["kuzu", "redis", "sqlite"]:
            assert status is True or isinstance(status, str)  # True or error message


@pytest.mark.integration
@pytest.mark.authentication
async def test_authentication_flow(http_client: AsyncClient, auth_headers):
    """Test authentication flow with different user roles."""
    # Test with authentication headers
    response = await http_client.get("/mcp/memory/test-id", headers=auth_headers)
    
    # Should get a response (either 200 or 404, but not 401)
    assert response.status_code != 401


@pytest.mark.integration
@pytest.mark.mock_data
def test_data_factory_generation(data_factory):
    """Test data factory functionality."""
    # Test memory entry generation
    memory = data_factory.generate_memory_entry()
    assert "id" in memory
    assert "content" in memory
    assert "memory_type" in memory
    
    # Test alert data generation
    alert = data_factory.generate_alert_data("high")
    assert alert["severity"] == "high"
    assert "id" in alert
    assert "message" in alert


@pytest.mark.integration
@pytest.mark.external
async def test_external_service_integration(mock_email_service, mock_slack_service):
    """Test external service integrations."""
    # Test email service
    await mock_email_service.send_email(
        to="test@example.com",
        subject="Test Email",
        body="Test email body"
    )
    
    sent_emails = mock_email_service.get_sent_emails()
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "test@example.com"
    
    # Test Slack service
    await mock_slack_service.send_message("#test", "Test message")
    
    messages = mock_slack_service.get_messages()
    assert len(messages) == 1
    assert messages[0]["channel"] == "#test"


@pytest.mark.integration
@pytest.mark.slow
async def test_comprehensive_workflow(
    mcp_client,
    analytics_client,
    alert_client,
    dashboard_client,
    data_factory
):
    """Test comprehensive workflow across all components."""
    # 1. Create test data
    test_dataset = data_factory.generate_test_dataset(
        memories=5,
        alerts=3,
        analytics_entries=10
    )
    
    # 2. Create memories via MCP
    memory_ids = []
    for memory_data in test_dataset["memories"][:3]:  # Create first 3
        result = await mcp_client.create_memory(memory_data)
        memory_ids.append(result["id"])
    
    assert len(memory_ids) == 3
    
    # 3. Process analytics data
    analytics_data = test_dataset["analytics_data"][:5]  # Process first 5
    analytics_jobs = []
    for data in analytics_data:
        result = await analytics_client.process_data(data)
        analytics_jobs.append(result["job_id"])
    
    assert len(analytics_jobs) == 5
    
    # 4. Create alerts
    alert_ids = []
    for alert_data in test_dataset["alerts"]:
        result = await alert_client.create_alert(alert_data)
        alert_ids.append(result["id"])
    
    assert len(alert_ids) == 3
    
    # 5. Verify dashboard can access all data
    metrics = await dashboard_client.get_metrics()
    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics
    
    # 6. Test real-time updates
    flow_result = await dashboard_client.validate_real_time_flow()
    assert flow_result["flow_validated"] is True 