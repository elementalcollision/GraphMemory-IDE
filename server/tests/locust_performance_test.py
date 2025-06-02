"""
Locust Load Testing for Analytics Integration Layer

This script provides realistic load testing scenarios using Locust framework.
Run with: locust -f server/tests/locust_performance_test.py --host=http://localhost:8000
"""

import json
import random
import time
from locust import HttpUser, task, between
from typing import Dict, Any, List


class AnalyticsUser(HttpUser):
    """Simulated user for analytics operations"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    # Initialize attributes with proper typing
    entity_ids: List[str]
    analytics_types: List[str]
    
    def on_start(self) -> None:
        """Setup for each user session"""
        self.entity_ids = [f"entity_{i}" for i in range(1, 101)]
        self.analytics_types = [
            "centrality",
            "community_detection", 
            "path_analysis",
            "similarity",
            "clustering"
        ]
    
    @task
    def test_centrality_analysis_high_weight(self) -> None:
        """Test centrality analysis endpoint - high frequency"""
        # Execute 3 times to simulate higher weight
        for _ in range(3):
            self._test_centrality_analysis()
    
    @task
    def test_community_detection_medium_weight(self) -> None:
        """Test community detection endpoint - medium frequency"""
        # Execute 2 times to simulate medium weight
        for _ in range(2):
            self._test_community_detection()
    
    @task
    def test_path_analysis_medium_weight(self) -> None:
        """Test path analysis endpoint - medium frequency"""
        # Execute 2 times to simulate medium weight
        for _ in range(2):
            self._test_path_analysis()
    
    @task
    def test_similarity_analysis(self) -> None:
        """Test similarity analysis endpoint"""
        self._test_similarity_analysis()
    
    @task
    def test_graph_metrics(self) -> None:
        """Test graph metrics endpoint"""
        self._test_graph_metrics()
    
    @task
    def test_batch_analytics(self) -> None:
        """Test batch analytics endpoint"""
        self._test_batch_analytics()
    
    def _test_centrality_analysis(self) -> None:
        """Test centrality analysis endpoint"""
        payload = {
            "analytics_type": "centrality",
            "parameters": {
                "entity_type": "Entity",
                "algorithm": random.choice(["degree_centrality", "betweenness_centrality", "pagerank"]),
                "limit": random.randint(10, 50)
            }
        }
        
        with self.client.post(
            "/analytics/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "execution_time_ms" in result:
                        response.success()
                    else:
                        response.failure("Missing execution_time_ms in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_community_detection(self) -> None:
        """Test community detection endpoint"""
        payload = {
            "analytics_type": "community_detection",
            "parameters": {
                "entity_type": "Entity",
                "min_cluster_size": random.randint(3, 10),
                "similarity_threshold": random.uniform(0.5, 0.9)
            }
        }
        
        with self.client.post(
            "/analytics/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "clusters" in result:
                        response.success()
                    else:
                        response.failure("Missing clusters in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_path_analysis(self) -> None:
        """Test path analysis endpoint"""
        source_entity = random.choice(self.entity_ids)
        target_entity = random.choice(self.entity_ids)
        
        payload = {
            "analytics_type": "path_analysis",
            "parameters": {
                "source_node": source_entity,
                "target_node": target_entity if random.random() > 0.3 else None,
                "max_hops": random.randint(3, 8)
            }
        }
        
        with self.client.post(
            "/analytics/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "paths" in result:
                        response.success()
                    else:
                        response.failure("Missing paths in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_similarity_analysis(self) -> None:
        """Test similarity analysis endpoint"""
        entity_id = random.choice(self.entity_ids)
        
        payload = {
            "analytics_type": "similarity",
            "parameters": {
                "entity_id": entity_id,
                "similarity_metric": random.choice(["jaccard", "cosine", "euclidean"]),
                "top_k": random.randint(5, 20)
            }
        }
        
        with self.client.post(
            "/analytics/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "similar_entities" in result:
                        response.success()
                    else:
                        response.failure("Missing similar_entities in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_graph_metrics(self) -> None:
        """Test graph metrics endpoint"""
        with self.client.get(
            "/analytics/graph-metrics",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "node_count" in result and "edge_count" in result:
                        response.success()
                    else:
                        response.failure("Missing node_count or edge_count in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_batch_analytics(self) -> None:
        """Test batch analytics endpoint"""
        batch_requests = []
        
        for i in range(random.randint(2, 5)):
            request = {
                "analytics_type": random.choice(self.analytics_types),
                "parameters": self._get_random_parameters()
            }
            batch_requests.append(request)
        
        payload = {"requests": batch_requests}
        
        with self.client.post(
            "/analytics/batch",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "results" in result and len(result["results"]) == len(batch_requests):
                        response.success()
                    else:
                        response.failure("Invalid batch response structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _get_random_parameters(self) -> Dict[str, Any]:
        """Generate random parameters for analytics requests"""
        return {
            "entity_type": "Entity",
            "limit": random.randint(5, 25),
            "algorithm": random.choice(["degree_centrality", "pagerank"]),
            "entity_id": random.choice(self.entity_ids),
            "max_hops": random.randint(3, 6)
        }


class HighVolumeUser(HttpUser):
    """High-volume user for stress testing"""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    # Initialize attributes with proper typing
    cached_requests: List[Dict[str, Any]]
    
    def on_start(self) -> None:
        """Setup for high-volume testing"""
        self.cached_requests = [
            {
                "analytics_type": "centrality",
                "parameters": {
                    "entity_type": "Entity",
                    "algorithm": "degree_centrality",
                    "limit": 20
                }
            }
        ] * 10  # Same request to test caching
    
    @task
    def test_high_volume_centrality(self) -> None:
        """High-volume centrality requests for stress testing"""
        payload = random.choice(self.cached_requests)
        
        start_time = time.time()
        
        with self.client.post(
            "/analytics/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time < 100:  # Less than 100ms expected for cached
                    response.success()
                else:
                    response.failure(f"Slow response: {response_time:.2f}ms")
            else:
                response.failure(f"HTTP {response.status_code}")


class RealtimeAnalyticsUser(HttpUser):
    """User simulating real-time analytics scenarios"""
    
    wait_time = between(0.5, 2)  # Real-time expectations
    
    # Initialize attributes with proper typing
    session_id: str
    entity_sequence: List[str]
    
    def on_start(self) -> None:
        """Setup for real-time testing"""
        self.session_id = f"session_{random.randint(1000, 9999)}"
        self.entity_sequence = []
    
    @task
    def test_realtime_pattern_detection_high_priority(self) -> None:
        """Test real-time pattern detection - high priority"""
        # Execute 4 times to simulate higher priority
        for _ in range(4):
            self._test_realtime_pattern_detection()
    
    @task
    def test_realtime_recommendations_medium_priority(self) -> None:
        """Test real-time recommendation generation - medium priority"""
        # Execute 2 times to simulate medium priority
        for _ in range(2):
            self._test_realtime_recommendations()
    
    def _test_realtime_pattern_detection(self) -> None:
        """Test real-time pattern detection"""
        # Simulate user behavior pattern
        entity_id = f"user_action_{len(self.entity_sequence)}"
        self.entity_sequence.append(entity_id)
        
        payload = {
            "analytics_type": "pattern_mining",
            "parameters": {
                "session_id": self.session_id,
                "entity_sequence": self.entity_sequence[-10:],  # Last 10 actions
                "pattern_type": "behavioral",
                "min_frequency": 2
            }
        }
        
        with self.client.post(
            "/analytics/streaming/pattern-detection",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "patterns" in result:
                        response.success()
                    else:
                        response.failure("Missing patterns in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_realtime_recommendations(self) -> None:
        """Test real-time recommendation generation"""
        if not self.entity_sequence:
            return
        
        payload = {
            "analytics_type": "similarity",
            "parameters": {
                "entity_id": self.entity_sequence[-1],
                "context": "real_time",
                "max_response_time_ms": 50,
                "top_k": 5
            }
        }
        
        start_time = time.time()
        
        with self.client.post(
            "/analytics/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time < 50:  # Real-time requirement
                    response.success()
                else:
                    response.failure(f"Too slow for real-time: {response_time:.2f}ms")
            else:
                response.failure(f"HTTP {response.status_code}")


class AdminUser(HttpUser):
    """Administrative user for monitoring and management"""
    
    wait_time = between(5, 15)  # Admin checks are less frequent
    
    @task
    def test_gateway_stats_medium_priority(self) -> None:
        """Check gateway statistics - medium priority"""
        # Execute 2 times for medium priority
        for _ in range(2):
            self._test_gateway_stats()
    
    @task
    def test_service_registry_status_medium_priority(self) -> None:
        """Check service registry status - medium priority"""
        # Execute 2 times for medium priority
        for _ in range(2):
            self._test_service_registry_status()
    
    @task
    def test_analytics_engine_health(self) -> None:
        """Check analytics engine health"""
        self._test_analytics_engine_health()
    
    def _test_gateway_stats(self) -> None:
        """Check gateway statistics"""
        with self.client.get(
            "/analytics/gateway/stats",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "gateway_stats" in result:
                        response.success()
                    else:
                        response.failure("Missing gateway_stats in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_service_registry_status(self) -> None:
        """Check service registry status"""
        with self.client.get(
            "/analytics/services/status",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "total_services" in result:
                        response.success()
                    else:
                        response.failure("Missing total_services in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def _test_analytics_engine_health(self) -> None:
        """Check analytics engine health"""
        with self.client.get(
            "/analytics/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "status" in result and result["status"] == "healthy":
                        response.success()
                    else:
                        response.failure("Analytics engine not healthy")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")


# Locust test configuration
if __name__ == "__main__":
    import sys
    
    print("Analytics Integration Layer - Locust Load Testing")
    print("=" * 60)
    print("Available test scenarios:")
    print("1. AnalyticsUser - Standard analytics operations")
    print("2. HighVolumeUser - High-volume stress testing") 
    print("3. RealtimeAnalyticsUser - Real-time analytics scenarios")
    print("4. AdminUser - Administrative monitoring")
    print("")
    print("Usage examples:")
    print("# Standard load test (mixed users)")
    print("locust -f server/tests/locust_performance_test.py --host=http://localhost:8000")
    print("")
    print("# High-volume stress test")
    print("locust -f server/tests/locust_performance_test.py --host=http://localhost:8000 HighVolumeUser")
    print("")
    print("# Real-time analytics test")
    print("locust -f server/tests/locust_performance_test.py --host=http://localhost:8000 RealtimeAnalyticsUser")
    print("")
    print("# Admin monitoring test")
    print("locust -f server/tests/locust_performance_test.py --host=http://localhost:8000 AdminUser") 