"""
Test Data Generator for Codon Unit Tests

This module provides comprehensive test data generators for Codon unit tests,
including realistic graph data, analytics scenarios, and performance test data.
"""

import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TestDataConfig:
    """Configuration for test data generation"""

    num_nodes: int = 1000
    num_edges: int = 5000
    num_users: int = 100
    num_posts: int = 500
    num_comments: int = 2000
    time_range_days: int = 30
    include_properties: bool = True
    include_timestamps: bool = True


class CodonTestDataGenerator:
    """Generator for Codon unit test data"""

    def __init__(self, config: Optional[TestDataConfig] = None):
        self.config = config or TestDataConfig()
        self.user_names = self._generate_user_names()
        self.post_titles = self._generate_post_titles()
        self.comment_texts = self._generate_comment_texts()

    def generate_graph_data(self) -> Dict[str, Any]:
        """Generate realistic graph data for testing"""
        nodes = []
        edges = []

        # Generate user nodes
        for i in range(self.config.num_users):
            node = {
                "id": f"user_{i}",
                "type": "user",
                "properties": {
                    "name": self.user_names[i % len(self.user_names)],
                    "email": f"user{i}@example.com",
                    "created_at": self._random_timestamp(),
                    "last_login": self._random_timestamp(),
                    "is_active": random.choice([True, False]),
                },
            }
            nodes.append(node)

        # Generate post nodes
        for i in range(self.config.num_posts):
            node = {
                "id": f"post_{i}",
                "type": "post",
                "properties": {
                    "title": self.post_titles[i % len(self.post_titles)],
                    "content": f"Post content {i}",
                    "created_at": self._random_timestamp(),
                    "author_id": f"user_{random.randint(0, self.config.num_users - 1)}",
                    "likes_count": random.randint(0, 100),
                    "comments_count": random.randint(0, 50),
                },
            }
            nodes.append(node)

        # Generate comment nodes
        for i in range(self.config.num_comments):
            node = {
                "id": f"comment_{i}",
                "type": "comment",
                "properties": {
                    "text": self.comment_texts[i % len(self.comment_texts)],
                    "created_at": self._random_timestamp(),
                    "author_id": f"user_{random.randint(0, self.config.num_users - 1)}",
                    "post_id": f"post_{random.randint(0, self.config.num_posts - 1)}",
                    "likes_count": random.randint(0, 20),
                },
            }
            nodes.append(node)

        # Generate edges
        edge_types = ["created", "liked", "commented_on", "follows", "mentions"]

        for i in range(self.config.num_edges):
            edge_type = random.choice(edge_types)

            if edge_type == "created":
                source = f"user_{random.randint(0, self.config.num_users - 1)}"
                target = f"post_{random.randint(0, self.config.num_posts - 1)}"
            elif edge_type == "liked":
                source = f"user_{random.randint(0, self.config.num_users - 1)}"
                target = random.choice(
                    [
                        f"post_{random.randint(0, self.config.num_posts - 1)}",
                        f"comment_{random.randint(0, self.config.num_comments - 1)}",
                    ]
                )
            elif edge_type == "commented_on":
                source = f"user_{random.randint(0, self.config.num_users - 1)}"
                target = f"post_{random.randint(0, self.config.num_posts - 1)}"
            elif edge_type == "follows":
                source = f"user_{random.randint(0, self.config.num_users - 1)}"
                target = f"user_{random.randint(0, self.config.num_users - 1)}"
            else:  # mentions
                source = f"comment_{random.randint(0, self.config.num_comments - 1)}"
                target = f"user_{random.randint(0, self.config.num_users - 1)}"

            edge = {
                "source": source,
                "target": target,
                "type": edge_type,
                "properties": {
                    "created_at": self._random_timestamp(),
                    "weight": random.uniform(0.1, 1.0),
                },
            }
            edges.append(edge)

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_types": list(set(node["type"] for node in nodes)),
                "edge_types": list(set(edge["type"] for edge in edges)),
            },
        }

    def generate_analytics_query_data(self) -> Dict[str, Any]:
        """Generate analytics query test data"""
        queries = [
            {
                "type": "user_activity",
                "parameters": {
                    "user_id": f"user_{random.randint(0, self.config.num_users - 1)}",
                    "time_range": "last_7_days",
                },
            },
            {
                "type": "post_popularity",
                "parameters": {
                    "post_id": f"post_{random.randint(0, self.config.num_posts - 1)}",
                    "metric": "likes",
                },
            },
            {
                "type": "network_analysis",
                "parameters": {"algorithm": "pagerank", "depth": random.randint(1, 3)},
            },
            {
                "type": "recommendation",
                "parameters": {
                    "user_id": f"user_{random.randint(0, self.config.num_users - 1)}",
                    "algorithm": "collaborative_filtering",
                    "limit": random.randint(5, 20),
                },
            },
        ]

        return {
            "queries": queries,
            "expected_results": self._generate_expected_results(queries),
        }

    def generate_performance_test_data(self) -> Dict[str, Any]:
        """Generate performance test data"""
        return {
            "small_dataset": self.generate_graph_data(),
            "medium_dataset": self._generate_larger_dataset(5000, 25000),
            "large_dataset": self._generate_larger_dataset(10000, 50000),
            "stress_test_data": self._generate_stress_test_data(),
        }

    def generate_cache_test_data(self) -> Dict[str, Any]:
        """Generate cache test data"""
        cache_entries = {}

        # Generate cache keys and values
        for i in range(1000):
            key = f"cache_key_{i}"
            value = {
                "id": i,
                "data": f"cached_data_{i}",
                "timestamp": time.time(),
                "expires_at": time.time() + random.randint(300, 3600),
                "access_count": random.randint(0, 100),
            }
            cache_entries[key] = value

        return {
            "cache_entries": cache_entries,
            "cache_keys": list(cache_entries.keys()),
            "cache_values": list(cache_entries.values()),
            "metadata": {
                "total_entries": len(cache_entries),
                "avg_access_count": sum(
                    entry["access_count"] for entry in cache_entries.values()
                )
                / len(cache_entries),
            },
        }

    def generate_error_test_data(self) -> Dict[str, Any]:
        """Generate error test data"""
        return {
            "invalid_graph_data": {"nodes": "invalid_nodes_type", "edges": None},
            "malformed_queries": [
                {"type": "invalid_query_type"},
                {"parameters": "invalid_parameters"},
                {"type": "user_activity", "parameters": None},
            ],
            "invalid_cache_keys": [None, "", {"invalid": "key"}, [1, 2, 3]],
            "corrupted_data": {
                "nodes": [{"id": None, "type": ""}],
                "edges": [{"source": "invalid", "target": None}],
            },
        }

    def _generate_larger_dataset(
        self, num_nodes: int, num_edges: int
    ) -> Dict[str, Any]:
        """Generate a larger dataset for performance testing"""
        config = TestDataConfig(
            num_nodes=num_nodes,
            num_edges=num_edges,
            num_users=num_nodes // 10,
            num_posts=num_nodes // 2,
            num_comments=num_nodes // 2,
        )

        generator = CodonTestDataGenerator(config)
        return generator.generate_graph_data()

    def _generate_stress_test_data(self) -> Dict[str, Any]:
        """Generate stress test data"""
        return {
            "concurrent_queries": [
                {"type": "user_activity", "user_id": f"user_{i}"} for i in range(100)
            ],
            "large_graph": self._generate_larger_dataset(50000, 250000),
            "memory_intensive_data": {
                "large_strings": [f"large_string_{i}" * 1000 for i in range(1000)],
                "nested_objects": [
                    {"level1": {"level2": {"level3": {"data": f"nested_data_{i}"}}}}
                    for i in range(1000)
                ],
            },
        }

    def _generate_expected_results(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate expected results for queries"""
        results = {}

        for query in queries:
            query_type = query["type"]

            if query_type == "user_activity":
                results[query_type] = {
                    "posts_created": random.randint(0, 10),
                    "comments_made": random.randint(0, 50),
                    "likes_given": random.randint(0, 100),
                    "total_engagement": random.randint(0, 200),
                }
            elif query_type == "post_popularity":
                results[query_type] = {
                    "likes_count": random.randint(0, 1000),
                    "comments_count": random.randint(0, 500),
                    "shares_count": random.randint(0, 100),
                    "engagement_rate": random.uniform(0.01, 0.1),
                }
            elif query_type == "network_analysis":
                results[query_type] = {
                    "pagerank_scores": {
                        f"node_{i}": random.uniform(0, 1) for i in range(10)
                    },
                    "centrality_scores": {
                        f"node_{i}": random.uniform(0, 1) for i in range(10)
                    },
                    "community_detection": [f"community_{i}" for i in range(5)],
                }
            elif query_type == "recommendation":
                results[query_type] = {
                    "recommended_items": [f"item_{i}" for i in range(10)],
                    "scores": [random.uniform(0.5, 1.0) for _ in range(10)],
                    "reasoning": "Based on user behavior and preferences",
                }

        return results

    def _generate_user_names(self) -> List[str]:
        """Generate realistic user names"""
        first_names = [
            "Alice",
            "Bob",
            "Charlie",
            "Diana",
            "Eve",
            "Frank",
            "Grace",
            "Henry",
            "Ivy",
            "Jack",
        ]
        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Rodriguez",
            "Martinez",
        ]

        return [
            f"{random.choice(first_names)} {random.choice(last_names)}"
            for _ in range(100)
        ]

    def _generate_post_titles(self) -> List[str]:
        """Generate realistic post titles"""
        titles = [
            "How to Improve Your Productivity",
            "The Future of Technology",
            "Best Practices for Software Development",
            "Understanding Machine Learning",
            "Tips for Remote Work",
            "The Art of Problem Solving",
            "Building Scalable Systems",
            "Data Science Fundamentals",
            "Web Development Trends",
            "Artificial Intelligence Applications",
        ]

        return [f"{title} - Part {i}" for i in range(1, 51) for title in titles]

    def _generate_comment_texts(self) -> List[str]:
        """Generate realistic comment texts"""
        comments = [
            "Great post! Thanks for sharing.",
            "This is really helpful information.",
            "I agree with your points.",
            "Interesting perspective on this topic.",
            "Could you elaborate on this?",
            "I've been looking for this information.",
            "This makes a lot of sense.",
            "Thanks for the detailed explanation.",
            "I'll definitely try this approach.",
            "This is exactly what I needed.",
        ]

        return [f"{comment} {i}" for i in range(1, 201) for comment in comments]

    def _random_timestamp(self) -> str:
        """Generate a random timestamp within the configured time range"""
        end_time = time.time()
        start_time = end_time - (self.config.time_range_days * 24 * 3600)
        random_time = random.uniform(start_time, end_time)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(random_time))


# Convenience functions for easy access
def get_graph_test_data(config: Optional[TestDataConfig] = None) -> Dict[str, Any]:
    """Get graph test data"""
    generator = CodonTestDataGenerator(config)
    return generator.generate_graph_data()


def get_analytics_test_data(config: Optional[TestDataConfig] = None) -> Dict[str, Any]:
    """Get analytics test data"""
    generator = CodonTestDataGenerator(config)
    return generator.generate_analytics_query_data()


def get_performance_test_data(
    config: Optional[TestDataConfig] = None,
) -> Dict[str, Any]:
    """Get performance test data"""
    generator = CodonTestDataGenerator(config)
    return generator.generate_performance_test_data()


def get_cache_test_data(config: Optional[TestDataConfig] = None) -> Dict[str, Any]:
    """Get cache test data"""
    generator = CodonTestDataGenerator(config)
    return generator.generate_cache_test_data()


def get_error_test_data(config: Optional[TestDataConfig] = None) -> Dict[str, Any]:
    """Get error test data"""
    generator = CodonTestDataGenerator(config)
    return generator.generate_error_test_data()
