"""
Data factory fixtures for GraphMemory-IDE integration testing.
Generates realistic test data for all system components.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from faker import Faker

import pytest

# Initialize Faker for generating realistic test data
fake = Faker()

@pytest.fixture(scope="function")
def data_factory():
    """Main data factory for generating test data."""
    
    class TestDataFactory:
        def __init__(self):
            self.fake = Faker()
            self.memory_types = ["procedural", "semantic", "episodic"]
            self.alert_severities = ["low", "medium", "high", "critical"]
            self.alert_statuses = ["pending", "acknowledged", "resolved", "escalated"]
            self.metric_names = [
                "cpu_usage", "memory_usage", "disk_usage", "network_latency",
                "response_time", "error_rate", "throughput", "connection_count"
            ]
        
        def generate_memory_entry(self, memory_type: str = None) -> Dict[str, Any]:
            """Generate a realistic memory entry."""
            if memory_type is None:
                memory_type = random.choice(self.memory_types)
            
            return {
                "id": str(uuid.uuid4()),
                "content": self.fake.text(max_nb_chars=200),
                "memory_type": memory_type,
                "created_at": self.fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "source": self.fake.word(),
                    "confidence": round(random.uniform(0.1, 1.0), 2),
                    "tags": [self.fake.word() for _ in range(random.randint(1, 5))],
                    "category": self.fake.word()
                }
            }
        
        def generate_analytics_data(self, size: int = 100) -> List[Dict[str, Any]]:
            """Generate analytics input data."""
            data = []
            for _ in range(size):
                entry = {
                    "id": str(uuid.uuid4()),
                    "timestamp": self.fake.date_time_between(start_date="-7d", end_date="now").isoformat(),
                    "user_id": str(uuid.uuid4()),
                    "session_id": str(uuid.uuid4()),
                    "event_type": random.choice(["click", "view", "search", "create", "update", "delete"]),
                    "page": self.fake.url(),
                    "duration": random.randint(100, 5000),
                    "metadata": {
                        "browser": self.fake.user_agent(),
                        "ip_address": self.fake.ipv4(),
                        "location": self.fake.city()
                    }
                }
                data.append(entry)
            return data
        
        def generate_alert_data(self, severity: str = None, status: str = None) -> Dict[str, Any]:
            """Generate realistic alert data."""
            if severity is None:
                severity = random.choice(self.alert_severities)
            if status is None:
                status = random.choice(self.alert_statuses)
            
            metric_name = random.choice(self.metric_names)
            threshold = random.randint(50, 95)
            metric_value = threshold + random.randint(1, 20) if severity in ["high", "critical"] else threshold - random.randint(1, 20)
            
            return {
                "id": str(uuid.uuid4()),
                "alert_type": "threshold_breach",
                "severity": severity,
                "status": status,
                "message": f"{metric_name} exceeded threshold: {metric_value}% > {threshold}%",
                "source": f"monitor_{metric_name}",
                "metric_name": metric_name,
                "metric_value": metric_value,
                "threshold": threshold,
                "created_at": self.fake.date_time_between(start_date="-24h", end_date="now").isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "node": self.fake.hostname(),
                    "environment": random.choice(["production", "staging", "development"]),
                    "service": self.fake.word()
                }
            }
        
        def generate_user_activity_data(self, user_count: int = 10, days: int = 7) -> List[Dict[str, Any]]:
            """Generate user activity data for testing."""
            activities = []
            user_ids = [str(uuid.uuid4()) for _ in range(user_count)]
            
            for _ in range(days * user_count * random.randint(5, 20)):
                activity = {
                    "id": str(uuid.uuid4()),
                    "user_id": random.choice(user_ids),
                    "action": random.choice(["login", "logout", "create_memory", "search", "view_dashboard", "create_alert"]),
                    "timestamp": self.fake.date_time_between(start_date=f"-{days}d", end_date="now").isoformat(),
                    "resource": self.fake.url(),
                    "ip_address": self.fake.ipv4(),
                    "user_agent": self.fake.user_agent(),
                    "success": random.choice([True, True, True, False]),  # 75% success rate
                    "response_time": random.randint(50, 2000),
                    "metadata": {
                        "session_id": str(uuid.uuid4()),
                        "location": self.fake.city()
                    }
                }
                activities.append(activity)
            
            return sorted(activities, key=lambda x: x["timestamp"])
        
        def generate_performance_metrics(self, duration_hours: int = 24) -> List[Dict[str, Any]]:
            """Generate performance metrics data."""
            metrics = []
            start_time = datetime.utcnow() - timedelta(hours=duration_hours)
            
            for minute in range(duration_hours * 60):
                timestamp = start_time + timedelta(minutes=minute)
                
                metric = {
                    "timestamp": timestamp.isoformat(),
                    "cpu_usage": round(random.uniform(10, 80), 2),
                    "memory_usage": round(random.uniform(20, 90), 2),
                    "disk_usage": round(random.uniform(15, 95), 2),
                    "network_latency": round(random.uniform(1, 100), 2),
                    "response_time": round(random.uniform(50, 500), 2),
                    "error_rate": round(random.uniform(0, 5), 3),
                    "throughput": random.randint(100, 1000),
                    "connection_count": random.randint(50, 500),
                    "metadata": {
                        "node_id": random.choice(["node-1", "node-2", "node-3"]),
                        "service": random.choice(["mcp-server", "analytics", "dashboard", "alerts"])
                    }
                }
                metrics.append(metric)
            
            return metrics
        
        def generate_test_dataset(self, 
                                memories: int = 50,
                                alerts: int = 20,
                                analytics_entries: int = 100,
                                users: int = 10) -> Dict[str, List[Dict[str, Any]]]:
            """Generate a complete test dataset."""
            return {
                "memories": [self.generate_memory_entry() for _ in range(memories)],
                "alerts": [self.generate_alert_data() for _ in range(alerts)],
                "analytics_data": self.generate_analytics_data(analytics_entries),
                "user_activities": self.generate_user_activity_data(users, 7),
                "performance_metrics": self.generate_performance_metrics(24)
            }
        
        def generate_correlation_test_data(self) -> Dict[str, Any]:
            """Generate data for testing alert correlation."""
            base_time = datetime.utcnow()
            
            # Create related alerts that should be correlated
            related_alerts = []
            
            # CPU and Memory alerts on the same node (temporal correlation)
            node_id = "production-node-1"
            for i, metric in enumerate(["cpu_usage", "memory_usage"]):
                alert = self.generate_alert_data("high", "pending")
                alert["metric_name"] = metric
                alert["metadata"]["node"] = node_id
                alert["created_at"] = (base_time + timedelta(minutes=i*2)).isoformat()
                related_alerts.append(alert)
            
            # Similar alerts on different nodes (spatial correlation)
            for i, node in enumerate(["production-node-2", "production-node-3"]):
                alert = self.generate_alert_data("medium", "pending")
                alert["metric_name"] = "disk_usage"
                alert["metadata"]["node"] = node
                alert["created_at"] = (base_time + timedelta(minutes=i*5)).isoformat()
                related_alerts.append(alert)
            
            return {
                "related_alerts": related_alerts,
                "unrelated_alerts": [self.generate_alert_data() for _ in range(5)]
            }
    
    return TestDataFactory()

@pytest.fixture(scope="function")
def sample_memories(data_factory) -> List[Dict[str, Any]]:
    """Generate sample memory entries for testing."""
    return [data_factory.generate_memory_entry() for _ in range(10)]

@pytest.fixture(scope="function")
def sample_alerts(data_factory) -> List[Dict[str, Any]]:
    """Generate sample alerts for testing."""
    return [data_factory.generate_alert_data() for _ in range(5)]

@pytest.fixture(scope="function")
def sample_analytics_data(data_factory) -> List[Dict[str, Any]]:
    """Generate sample analytics data for testing."""
    return data_factory.generate_analytics_data(50)

@pytest.fixture(scope="function")
def performance_test_data(data_factory) -> List[Dict[str, Any]]:
    """Generate performance metrics for testing."""
    return data_factory.generate_performance_metrics(2)  # 2 hours of data

@pytest.fixture(scope="function")
def large_dataset(data_factory) -> Dict[str, List[Dict[str, Any]]]:
    """Generate a large dataset for stress testing."""
    return data_factory.generate_test_dataset(
        memories=500,
        alerts=100,
        analytics_entries=1000,
        users=50
    )

@pytest.fixture(scope="function")
def correlation_test_data(data_factory) -> Dict[str, Any]:
    """Generate data for testing alert correlation algorithms."""
    return data_factory.generate_correlation_test_data()

# Specialized data generators
@pytest.fixture(scope="function")
def memory_search_test_data():
    """Generate data specifically for testing memory search functionality."""
    return {
        "queries": [
            "machine learning algorithms",
            "database optimization",
            "user interface design",
            "security protocols",
            "performance monitoring"
        ],
        "expected_results": {
            "machine learning": ["neural networks", "deep learning", "classification"],
            "database": ["SQL", "NoSQL", "indexing", "optimization"],
            "interface": ["UX", "UI", "design patterns", "accessibility"],
            "security": ["authentication", "encryption", "protocols", "vulnerabilities"],
            "performance": ["monitoring", "metrics", "optimization", "benchmarking"]
        }
    }

@pytest.fixture(scope="function")
def real_time_test_data():
    """Generate data for testing real-time features."""
    return {
        "events": [
            {
                "type": "metric_update",
                "data": {"cpu": 75, "memory": 82, "timestamp": datetime.utcnow().isoformat()}
            },
            {
                "type": "alert_created",
                "data": {"id": str(uuid.uuid4()), "severity": "high", "message": "High CPU usage detected"}
            },
            {
                "type": "user_activity",
                "data": {"user_id": str(uuid.uuid4()), "action": "login", "timestamp": datetime.utcnow().isoformat()}
            }
        ],
        "stream_duration": 30,  # seconds
        "event_frequency": 2    # events per second
    }

@pytest.fixture(scope="function")
def edge_case_test_data():
    """Generate edge case data for robust testing."""
    return {
        "empty_data": [],
        "null_values": [None, "", {}, []],
        "large_strings": ["x" * 10000, "🚀" * 1000],  # Large text and unicode
        "special_characters": ["<script>alert('xss')</script>", "'; DROP TABLE users; --"],
        "extreme_numbers": [0, -1, 999999999, 1.7976931348623157e+308],
        "malformed_dates": ["not-a-date", "2025-13-45", "2025-02-30T25:61:61Z"],
        "unicode_content": ["测试数据", "🔥💯🚀", "Здравствуй мир", "مرحبا بالعالم"]
    }

# Data validation fixtures
@pytest.fixture(scope="function")
def data_validator():
    """Provide data validation utilities for tests."""
    
    class DataValidator:
        @staticmethod
        def validate_memory_entry(entry: Dict[str, Any]) -> bool:
            """Validate memory entry structure."""
            required_fields = ["id", "content", "memory_type", "created_at"]
            return all(field in entry for field in required_fields)
        
        @staticmethod
        def validate_alert_data(alert: Dict[str, Any]) -> bool:
            """Validate alert data structure."""
            required_fields = ["id", "severity", "status", "message", "created_at"]
            return all(field in alert for field in required_fields)
        
        @staticmethod
        def validate_analytics_result(result: Dict[str, Any]) -> bool:
            """Validate analytics result structure."""
            required_fields = ["job_id", "status", "results"]
            return all(field in result for field in required_fields)
        
        @staticmethod
        def validate_performance_metric(metric: Dict[str, Any]) -> bool:
            """Validate performance metric structure."""
            required_fields = ["timestamp", "cpu_usage", "memory_usage"]
            return all(field in metric for field in required_fields)
    
    return DataValidator() 