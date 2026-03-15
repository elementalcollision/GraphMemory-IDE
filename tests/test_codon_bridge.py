"""
Codon Bridge Comparison Tests
=============================
Validates that Codon-accelerated functions produce results identical
(within floating-point tolerance) to their NetworkX/Python counterparts.

These tests always run using the Python fallback path, ensuring
the bridge layer works correctly regardless of whether Codon
shared libraries are compiled.
"""

import math
import random
import time
import pytest
from typing import Dict, List, Tuple

# ---- Graph Bridge Tests ----

class TestGraphBridgeFallback:
    """Test graph bridge functions using Python/NetworkX fallback."""

    @staticmethod
    def _make_random_graph(n_nodes: int, edge_prob: float = 0.3, seed: int = 42):
        """Create a random graph using NetworkX for testing."""
        import networkx as nx
        random.seed(seed)
        G = nx.erdos_renyi_graph(n_nodes, edge_prob, seed=seed)
        # Add weights
        for u, v in G.edges():
            G[u][v]["weight"] = round(random.uniform(0.1, 5.0), 2)
        # Relabel nodes to strings (matching real-world usage)
        mapping = {i: f"node_{i}" for i in range(n_nodes)}
        G = nx.relabel_nodes(G, mapping)
        return G

    def test_betweenness_centrality(self):
        """Betweenness centrality bridge matches NetworkX."""
        import networkx as nx
        from codon.bridge.graph_bridge import betweenness_centrality

        G = self._make_random_graph(50)
        bridge_result = betweenness_centrality(G, normalized=True)
        nx_result = nx.betweenness_centrality(G, normalized=True)

        assert set(bridge_result.keys()) == set(nx_result.keys())
        for node in bridge_result:
            assert bridge_result[node] == pytest.approx(nx_result[node], abs=1e-6), \
                f"Mismatch at {node}: bridge={bridge_result[node]}, nx={nx_result[node]}"

    def test_closeness_centrality(self):
        """Closeness centrality bridge matches NetworkX."""
        import networkx as nx
        from codon.bridge.graph_bridge import closeness_centrality

        G = self._make_random_graph(50)
        bridge_result = closeness_centrality(G, normalized=True)
        nx_result = nx.closeness_centrality(G)

        assert set(bridge_result.keys()) == set(nx_result.keys())
        for node in bridge_result:
            assert bridge_result[node] == pytest.approx(nx_result[node], abs=1e-6)

    def test_degree_centrality(self):
        """Degree centrality bridge matches NetworkX."""
        import networkx as nx
        from codon.bridge.graph_bridge import degree_centrality

        G = self._make_random_graph(50)
        bridge_result = degree_centrality(G)
        nx_result = nx.degree_centrality(G)

        for node in bridge_result:
            assert bridge_result[node] == pytest.approx(nx_result[node], abs=1e-6)

    def test_pagerank(self):
        """PageRank bridge matches NetworkX."""
        import networkx as nx
        from codon.bridge.graph_bridge import pagerank

        G = self._make_random_graph(50)
        bridge_result = pagerank(G, damping=0.85)
        nx_result = nx.pagerank(G, alpha=0.85)

        for node in bridge_result:
            assert bridge_result[node] == pytest.approx(nx_result[node], abs=1e-4)

    def test_shortest_path(self):
        """Shortest path bridge matches NetworkX."""
        import networkx as nx
        from codon.bridge.graph_bridge import shortest_path

        G = self._make_random_graph(30, edge_prob=0.4)
        # Pick two connected nodes
        nodes = list(G.nodes())
        source, target = nodes[0], nodes[-1]

        bridge_result = shortest_path(G, source, target)
        try:
            nx_result = list(nx.shortest_path(G, source, target))
        except nx.NetworkXNoPath:
            nx_result = []

        # Both should find a path or both fail
        assert len(bridge_result) == len(nx_result)
        if bridge_result:
            assert bridge_result[0] == source
            assert bridge_result[-1] == target

    def test_label_propagation(self):
        """Label propagation communities bridge produces valid partition."""
        from codon.bridge.graph_bridge import label_propagation_communities

        G = self._make_random_graph(50, edge_prob=0.15)
        result = label_propagation_communities(G)

        # Every node should be assigned a community
        assert set(result.keys()) == set(str(n) for n in G.nodes())
        # Community IDs should be non-negative integers
        assert all(isinstance(v, int) for v in result.values())

    def test_empty_graph(self):
        """Bridge handles empty graph gracefully."""
        import networkx as nx
        from codon.bridge.graph_bridge import betweenness_centrality

        G = nx.Graph()
        result = betweenness_centrality(G)
        assert result == {}

    def test_single_node(self):
        """Bridge handles single-node graph."""
        import networkx as nx
        from codon.bridge.graph_bridge import degree_centrality

        G = nx.Graph()
        G.add_node("a")
        result = degree_centrality(G)
        assert result == {"a": 0.0}


# ---- Data Bridge Tests ----

class TestDataBridgeFallback:
    """Test data bridge functions using Python fallback."""

    def test_cosine_similarity_identical(self):
        """Cosine similarity of identical vectors is 1.0."""
        from codon.bridge.data_bridge import cosine_similarity

        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-10)

    def test_cosine_similarity_orthogonal(self):
        """Cosine similarity of orthogonal vectors is 0.0."""
        from codon.bridge.data_bridge import cosine_similarity

        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-10)

    def test_cosine_similarity_opposite(self):
        """Cosine similarity of opposite vectors is -1.0."""
        from codon.bridge.data_bridge import cosine_similarity

        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0, abs=1e-10)

    def test_batch_cosine_similarity(self):
        """Batch cosine similarity matches individual calls."""
        from codon.bridge.data_bridge import cosine_similarity, batch_cosine_similarity

        query = [1.0, 0.5, 0.3]
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 0.5, 0.3],
            [-1.0, -0.5, -0.3],
        ]

        batch_result = batch_cosine_similarity(query, vectors)
        individual_results = [cosine_similarity(query, v) for v in vectors]

        for br, ir in zip(batch_result, individual_results):
            assert br == pytest.approx(ir, abs=1e-10)

    def test_topk_similar(self):
        """Top-k returns correct top matches."""
        from codon.bridge.data_bridge import topk_similar

        query = [1.0, 0.0, 0.0]
        vectors = [
            [0.0, 1.0, 0.0],  # orthogonal
            [1.0, 0.1, 0.0],  # very similar
            [1.0, 0.0, 0.0],  # identical
            [-1.0, 0.0, 0.0],  # opposite
        ]

        result = topk_similar(query, vectors, k=2)
        assert len(result) == 2
        # Most similar should be index 2 (identical)
        assert result[0][0] == 2
        assert result[0][1] == pytest.approx(1.0, abs=1e-6)
        # Second most similar should be index 1
        assert result[1][0] == 1

    def test_normalize_vector(self):
        """Normalized vector has unit length."""
        from codon.bridge.data_bridge import normalize_vector

        v = [3.0, 4.0]
        normalized = normalize_vector(v)
        length = math.sqrt(sum(x * x for x in normalized))
        assert length == pytest.approx(1.0, abs=1e-10)

    def test_normalize_zero_vector(self):
        """Normalizing zero vector returns zero vector."""
        from codon.bridge.data_bridge import normalize_vector

        v = [0.0, 0.0, 0.0]
        result = normalize_vector(v)
        assert result == [0.0, 0.0, 0.0]

    def test_hash_cache_key_deterministic(self):
        """Cache key generation is deterministic."""
        from codon.bridge.data_bridge import hash_cache_key

        key1 = hash_cache_key("centrality", '{"type":"betweenness"}')
        key2 = hash_cache_key("centrality", '{"type":"betweenness"}')
        assert key1 == key2

    def test_hash_cache_key_different_inputs(self):
        """Different inputs produce different cache keys."""
        from codon.bridge.data_bridge import hash_cache_key

        key1 = hash_cache_key("centrality", '{"type":"betweenness"}')
        key2 = hash_cache_key("centrality", '{"type":"closeness"}')
        assert key1 != key2


# ---- Performance Benchmark Tests ----

class TestPerformanceBenchmarks:
    """Performance comparison tests (informational, not strict assertions)."""

    @pytest.mark.slow
    def test_centrality_benchmark(self):
        """Benchmark centrality calculation on larger graph."""
        import networkx as nx
        from codon.bridge.graph_bridge import betweenness_centrality

        G = nx.erdos_renyi_graph(500, 0.1, seed=42)
        mapping = {i: f"node_{i}" for i in range(500)}
        G = nx.relabel_nodes(G, mapping)

        start = time.time()
        result = betweenness_centrality(G, normalized=True)
        elapsed = time.time() - start

        assert len(result) == 500
        # Just verify it completes; actual speedup depends on Codon availability
        print(f"\nBetweenness centrality (500 nodes): {elapsed:.3f}s")

    @pytest.mark.slow
    def test_similarity_benchmark(self):
        """Benchmark batch cosine similarity."""
        from codon.bridge.data_bridge import batch_cosine_similarity

        random.seed(42)
        dim = 384  # typical embedding dimension
        query = [random.random() for _ in range(dim)]
        vectors = [[random.random() for _ in range(dim)] for _ in range(10000)]

        start = time.time()
        result = batch_cosine_similarity(query, vectors)
        elapsed = time.time() - start

        assert len(result) == 10000
        print(f"\nBatch cosine similarity (10K x 384): {elapsed:.3f}s")
