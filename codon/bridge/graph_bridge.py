"""
Graph Algorithm Bridge
======================
Provides Python-callable wrappers for Codon-compiled graph algorithms.
Falls back to NetworkX implementations when Codon is unavailable.

The bridge handles:
1. Loading Codon compiled shared libraries
2. Converting Python graph data to Codon-compatible typed arrays
3. Converting results back to Python dicts
4. Automatic fallback to NetworkX if Codon is unavailable
5. Size-based routing (small graphs stay in Python to avoid conversion overhead)
"""

import logging
from typing import Dict, List, Tuple, Optional, Any

from codon.bridge import CODON_ENABLED, CODON_MIN_GRAPH_SIZE

logger = logging.getLogger(__name__)

# --- Attempt to load Codon compiled modules ---
CODON_GRAPH_AVAILABLE = False

if CODON_ENABLED:
    try:
        from codon.lib.centrality import (
            betweenness_centrality as _codon_betweenness,
            closeness_centrality as _codon_closeness,
            degree_centrality as _codon_degree,
            pagerank as _codon_pagerank,
        )
        from codon.lib.community import (
            label_propagation as _codon_label_propagation,
            louvain_phase1 as _codon_louvain,
            modularity as _codon_modularity,
        )
        from codon.lib.path_analysis import (
            bfs_shortest_path as _codon_bfs,
            dijkstra_shortest_path as _codon_dijkstra,
            graph_diameter as _codon_diameter,
            average_shortest_path_length as _codon_avg_path,
        )
        CODON_GRAPH_AVAILABLE = True
        logger.info("Codon graph kernels loaded successfully")
    except ImportError as e:
        logger.info(f"Codon graph kernels not available, using NetworkX fallback: {e}")


# --- Graph data conversion utilities ---

def _graph_to_adjacency(graph) -> Tuple[Dict[int, List[Tuple[int, float]]], Dict[str, int], Dict[int, str]]:
    """
    Convert a NetworkX graph to Codon-compatible adjacency list.
    Returns (adjacency_dict, name_to_id, id_to_name).
    """
    # Map string node IDs to integers
    name_to_id: Dict[str, int] = {}
    id_to_name: Dict[int, str] = {}
    for idx, node in enumerate(graph.nodes()):
        name_to_id[str(node)] = idx
        id_to_name[idx] = str(node)

    # Build adjacency list with integer keys
    adj: Dict[int, List[Tuple[int, float]]] = {}
    for node in graph.nodes():
        nid = name_to_id[str(node)]
        neighbors: List[Tuple[int, float]] = []
        for neighbor in graph.neighbors(node):
            nid2 = name_to_id[str(neighbor)]
            weight = graph[node][neighbor].get("weight", 1.0)
            neighbors.append((nid2, float(weight)))
        adj[nid] = neighbors

    return adj, name_to_id, id_to_name


def _remap_results(results: Dict[int, float], id_to_name: Dict[int, str]) -> Dict[str, float]:
    """Convert integer-keyed results back to string-keyed."""
    return {id_to_name[k]: v for k, v in results.items()}


def _should_use_codon(graph) -> bool:
    """Determine if graph is large enough to benefit from Codon."""
    return CODON_GRAPH_AVAILABLE and graph.number_of_nodes() >= CODON_MIN_GRAPH_SIZE


# --- Public API (matches NetworkX calling conventions) ---

def betweenness_centrality(graph, normalized: bool = True) -> Dict[str, float]:
    """Calculate betweenness centrality with automatic Codon/NetworkX routing."""
    if _should_use_codon(graph):
        adj, _, id_to_name = _graph_to_adjacency(graph)
        result = _codon_betweenness(adj, normalized)
        return _remap_results(result, id_to_name)

    import networkx as nx
    return nx.betweenness_centrality(graph, normalized=normalized)


def closeness_centrality(graph, normalized: bool = True) -> Dict[str, float]:
    """Calculate closeness centrality with automatic Codon/NetworkX routing."""
    if _should_use_codon(graph):
        adj, _, id_to_name = _graph_to_adjacency(graph)
        result = _codon_closeness(adj, normalized)
        return _remap_results(result, id_to_name)

    import networkx as nx
    return nx.closeness_centrality(graph)


def degree_centrality(graph) -> Dict[str, float]:
    """Calculate degree centrality with automatic Codon/NetworkX routing."""
    if _should_use_codon(graph):
        adj, _, id_to_name = _graph_to_adjacency(graph)
        result = _codon_degree(adj, True)
        return _remap_results(result, id_to_name)

    import networkx as nx
    return nx.degree_centrality(graph)


def pagerank(graph, damping: float = 0.85) -> Dict[str, float]:
    """Calculate PageRank with automatic Codon/NetworkX routing."""
    if _should_use_codon(graph):
        adj, _, id_to_name = _graph_to_adjacency(graph)
        result = _codon_pagerank(adj, damping)
        return _remap_results(result, id_to_name)

    import networkx as nx
    return nx.pagerank(graph, alpha=damping)


def label_propagation_communities(graph) -> Dict[str, int]:
    """Detect communities via label propagation with automatic routing."""
    if _should_use_codon(graph):
        adj, _, id_to_name = _graph_to_adjacency(graph)
        result = _codon_label_propagation(adj)
        return {id_to_name[k]: v for k, v in result.items()}

    import networkx as nx
    communities = nx.community.label_propagation_communities(graph)
    partition = {}
    for i, comm in enumerate(communities):
        for node in comm:
            partition[str(node)] = i
    return partition


def shortest_path(graph, source: str, target: str) -> List[str]:
    """Find shortest unweighted path with automatic routing."""
    if _should_use_codon(graph):
        adj, name_to_id, id_to_name = _graph_to_adjacency(graph)
        if source in name_to_id and target in name_to_id:
            result = _codon_bfs(adj, name_to_id[source], name_to_id[target])
            return [id_to_name[nid] for nid in result]

    import networkx as nx
    try:
        return list(nx.shortest_path(graph, source, target))
    except nx.NetworkXNoPath:
        return []
