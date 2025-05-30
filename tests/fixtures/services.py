"""
Service fixtures for GraphMemory-IDE integration testing.
Provides mocks and toggles for external services.
"""

import os
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch

import pytest

@pytest.fixture(scope="function")
def mock_email_service():
    """Mock email service for testing notifications."""
    
    class MockEmailService:
        def __init__(self):
            self.sent_emails = []
            self.config = {
                "smtp_host": "smtp.test.com",
                "smtp_port": 587,
                "username": "test@example.com",
                "password": "test-password"
            }
        
        async def send_email(self, to: str, subject: str, body: str, html: bool = False):
            """Mock sending an email."""
            email = {
                "to": to,
                "subject": subject,
                "body": body,
                "html": html,
                "sent_at": "2025-05-29T11:35:32Z"
            }
            self.sent_emails.append(email)
            return {"status": "sent", "message_id": f"mock-{len(self.sent_emails)}"}
        
        def get_sent_emails(self):
            """Get all sent emails."""
            return self.sent_emails.copy()
        
        def clear_sent_emails(self):
            """Clear sent emails history."""
            self.sent_emails.clear()
    
    return MockEmailService()

@pytest.fixture(scope="function")
def mock_webhook_service():
    """Mock webhook service for testing external integrations."""
    
    class MockWebhookService:
        def __init__(self):
            self.webhook_calls = []
            self.endpoints = {}
        
        def register_endpoint(self, name: str, url: str, secret: str = None):
            """Register a webhook endpoint."""
            self.endpoints[name] = {
                "url": url,
                "secret": secret,
                "active": True
            }
        
        async def send_webhook(self, endpoint_name: str, payload: Dict[str, Any]):
            """Mock sending a webhook."""
            if endpoint_name not in self.endpoints:
                raise ValueError(f"Endpoint {endpoint_name} not registered")
            
            webhook_call = {
                "endpoint": endpoint_name,
                "url": self.endpoints[endpoint_name]["url"],
                "payload": payload,
                "timestamp": "2025-05-29T11:35:32Z",
                "status": "success"
            }
            self.webhook_calls.append(webhook_call)
            return {"status": "success", "response_code": 200}
        
        def get_webhook_calls(self):
            """Get all webhook calls."""
            return self.webhook_calls.copy()
        
        def clear_webhook_history(self):
            """Clear webhook call history."""
            self.webhook_calls.clear()
    
    return MockWebhookService()

@pytest.fixture(scope="function")
def mock_slack_service():
    """Mock Slack service for testing Slack notifications."""
    
    class MockSlackService:
        def __init__(self):
            self.messages = []
            self.channels = ["#alerts", "#general", "#monitoring"]
            self.bot_token = "xoxb-mock-token"
        
        async def send_message(self, channel: str, message: str, blocks: List[Dict] = None):
            """Mock sending a Slack message."""
            slack_message = {
                "channel": channel,
                "message": message,
                "blocks": blocks,
                "timestamp": "2025-05-29T11:35:32Z",
                "message_ts": f"1234567890.{len(self.messages):06d}"
            }
            self.messages.append(slack_message)
            return {"ok": True, "ts": slack_message["message_ts"]}
        
        async def send_alert(self, alert_data: Dict[str, Any]):
            """Mock sending an alert to Slack."""
            message = f"🚨 Alert: {alert_data.get('message', 'Unknown alert')}"
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Severity:* {alert_data.get('severity', 'Unknown')}\n*Source:* {alert_data.get('source', 'Unknown')}"
                    }
                }
            ]
            return await self.send_message("#alerts", message, blocks)
        
        def get_messages(self):
            """Get all sent messages."""
            return self.messages.copy()
        
        def clear_message_history(self):
            """Clear message history."""
            self.messages.clear()
    
    return MockSlackService()

@pytest.fixture(scope="function")
def service_toggle_manager():
    """Manage toggling between real and mock services."""
    
    class ServiceToggleManager:
        def __init__(self):
            self.use_real_services = os.getenv("USE_REAL_SERVICES", "false").lower() == "true"
            self.service_configs = {
                "email": {"enabled": True, "mock_failures": False},
                "webhook": {"enabled": True, "mock_failures": False},
                "slack": {"enabled": True, "mock_failures": False},
                "analytics": {"enabled": True, "use_gpu": False},
                "database": {"enabled": True, "use_memory": True}
            }
        
        def should_use_real_service(self, service_name: str) -> bool:
            """Check if a real service should be used."""
            return self.use_real_services and self.service_configs.get(service_name, {}).get("enabled", False)
        
        def enable_service(self, service_name: str, enabled: bool = True):
            """Enable or disable a service."""
            if service_name in self.service_configs:
                self.service_configs[service_name]["enabled"] = enabled
        
        def set_mock_failures(self, service_name: str, mock_failures: bool = True):
            """Set whether to mock failures for a service."""
            if service_name in self.service_configs:
                self.service_configs[service_name]["mock_failures"] = mock_failures
        
        def get_service_config(self, service_name: str) -> Dict[str, Any]:
            """Get configuration for a service."""
            return self.service_configs.get(service_name, {})
    
    return ServiceToggleManager()

@pytest.fixture(scope="function")
def external_service_health_checker():
    """Check health of external services."""
    
    class ExternalServiceHealthChecker:
        def __init__(self):
            self.health_checks = {}
        
        async def check_service_health(self, service_name: str) -> Dict[str, Any]:
            """Check health of an external service."""
            # Mock health check results
            health_status = {
                "email": {"status": "healthy", "latency": 50},
                "webhook": {"status": "healthy", "latency": 75},
                "slack": {"status": "healthy", "latency": 100},
                "analytics": {"status": "healthy", "gpu_available": False},
                "database": {"status": "healthy", "connections": 5}
            }
            
            result = health_status.get(service_name, {"status": "unknown"})
            self.health_checks[service_name] = result
            return result
        
        async def check_all_services(self) -> Dict[str, Dict[str, Any]]:
            """Check health of all services."""
            services = ["email", "webhook", "slack", "analytics", "database"]
            results = {}
            for service in services:
                results[service] = await self.check_service_health(service)
            return results
        
        def get_health_summary(self) -> Dict[str, Any]:
            """Get health summary."""
            healthy_services = [
                name for name, status in self.health_checks.items()
                if status.get("status") == "healthy"
            ]
            
            return {
                "total_services": len(self.health_checks),
                "healthy_services": len(healthy_services),
                "unhealthy_services": len(self.health_checks) - len(healthy_services),
                "health_rate": len(healthy_services) / len(self.health_checks) if self.health_checks else 0
            }
    
    return ExternalServiceHealthChecker()

@pytest.fixture(scope="function")
def circuit_breaker_mock():
    """Mock circuit breaker for testing failure scenarios."""
    
    class MockCircuitBreaker:
        def __init__(self):
            self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
            self.failure_count = 0
            self.failure_threshold = 5
            self.success_count = 0
            self.reset_timeout = 60
        
        def call(self, func, *args, **kwargs):
            """Mock circuit breaker call."""
            if self.state == "OPEN":
                raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                self.on_failure()
                raise e
        
        def on_success(self):
            """Handle successful call."""
            self.success_count += 1
            if self.state == "HALF_OPEN" and self.success_count >= 3:
                self.state = "CLOSED"
                self.failure_count = 0
        
        def on_failure(self):
            """Handle failed call."""
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
        
        def reset(self):
            """Reset circuit breaker."""
            self.state = "CLOSED"
            self.failure_count = 0
            self.success_count = 0
        
        def get_state(self):
            """Get current state."""
            return {
                "state": self.state,
                "failure_count": self.failure_count,
                "success_count": self.success_count
            }
    
    return MockCircuitBreaker()

@pytest.fixture(scope="function")
def performance_service_mock():
    """Mock performance monitoring service."""
    
    class MockPerformanceService:
        def __init__(self):
            self.metrics = []
            self.alerts = []
        
        def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
            """Record a performance metric."""
            metric = {
                "name": name,
                "value": value,
                "tags": tags or {},
                "timestamp": "2025-05-29T11:35:32Z"
            }
            self.metrics.append(metric)
        
        def record_request_duration(self, endpoint: str, duration: float, status_code: int):
            """Record request duration."""
            self.record_metric(
                "request_duration",
                duration,
                {"endpoint": endpoint, "status_code": str(status_code)}
            )
        
        def record_database_query(self, query_type: str, duration: float):
            """Record database query performance."""
            self.record_metric(
                "database_query_duration",
                duration,
                {"query_type": query_type}
            )
        
        def get_metrics(self):
            """Get all recorded metrics."""
            return self.metrics.copy()
        
        def get_metric_summary(self):
            """Get metrics summary."""
            if not self.metrics:
                return {"total_metrics": 0}
            
            durations = [m["value"] for m in self.metrics if "duration" in m["name"]]
            return {
                "total_metrics": len(self.metrics),
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0
            }
    
    return MockPerformanceService()

# Environment setup for service testing
@pytest.fixture(scope="function")
def service_test_environment():
    """Setup test environment for service testing."""
    test_env = {
        "EMAIL_ENABLED": "true",
        "EMAIL_MOCK": "true",
        "WEBHOOK_ENABLED": "true",
        "WEBHOOK_MOCK": "true",
        "SLACK_ENABLED": "true",
        "SLACK_MOCK": "true",
        "CIRCUIT_BREAKER_ENABLED": "true",
        "PERFORMANCE_MONITORING_ENABLED": "true"
    }
    
    with patch.dict(os.environ, test_env):
        yield test_env 