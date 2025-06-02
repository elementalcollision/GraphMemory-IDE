"""
Kuzu GraphDB Analytics Engine for GraphMemory-IDE

This module provides optimized graph analytics queries, advanced graph algorithms,
and specialized analytics operations for the Kuzu GraphDB integration.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from types import TracebackType

logger = logging.getLogger(__name__)


class GraphAnalyticsType(str, Enum):
    """Types of graph analytics operations"""

    CENTRALITY = "centrality"
    COMMUNITY_DETECTION = "community_detection"
    PATH_ANALYSIS = "path_analysis"
    SIMILARITY = "similarity"
    CLUSTERING = "clustering"
    TEMPORAL_ANALYSIS = "temporal_analysis"
    INFLUENCE_ANALYSIS = "influence_analysis"
    NETWORK_STRUCTURE = "network_structure"
    KNOWLEDGE_FLOW = "knowledge_flow"
    PATTERN_MINING = "pattern_mining"


@dataclass
class GraphMetrics:
    """Graph-level metrics and statistics"""

    node_count: int
    edge_count: int
    density: float
    average_degree: float
    clustering_coefficient: float
    diameter: Optional[int]
    connected_components: int
    largest_component_size: int
    timestamp: str


class KuzuAnalyticsEngine:
    """
    Advanced analytics engine for Kuzu GraphDB with optimized graph algorithms
    and specialized analytics operations for memory graphs.
    """

    def __init__(self, kuzu_connection: Any) -> None:
        self.connection = kuzu_connection
        self.query_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.cache_ttl = 600  # 10 minutes for graph analytics

        # Performance tracking
        self.analytics_stats: Dict[str, Any] = {
            "total_queries": 0,
            "cache_hits": 0,
            "average_execution_time": 0.0,
            "query_types": {},
        }

        # Pre-computed metrics cache
        self.graph_metrics_cache: Optional[GraphMetrics] = None
        self.last_metrics_update: Optional[datetime] = None
        self.metrics_cache_ttl = 300  # 5 minutes

        logger.info("Kuzu Analytics Engine initialized")

    async def execute_graph_analytics(
        self,
        analytics_type: GraphAnalyticsType,
        parameters: Dict[str, Any],
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Execute graph analytics query with optimization and caching"""
        start_time = time.time()

        try:
            # Check cache
            if use_cache:
                cached_result = self._get_cached_result(analytics_type, parameters)
                if cached_result:
                    self.analytics_stats["cache_hits"] += 1
                    return cached_result

            # Execute analytics based on type
            if analytics_type == GraphAnalyticsType.CENTRALITY:
                result = await self._compute_centrality(parameters)
            elif analytics_type == GraphAnalyticsType.COMMUNITY_DETECTION:
                result = await self._detect_communities(parameters)
            elif analytics_type == GraphAnalyticsType.PATH_ANALYSIS:
                result = await self._analyze_paths(parameters)
            elif analytics_type == GraphAnalyticsType.SIMILARITY:
                result = await self._compute_similarity(parameters)
            elif analytics_type == GraphAnalyticsType.CLUSTERING:
                result = await self._compute_clustering(parameters)
            elif analytics_type == GraphAnalyticsType.TEMPORAL_ANALYSIS:
                result = await self._analyze_temporal_patterns(parameters)
            elif analytics_type == GraphAnalyticsType.INFLUENCE_ANALYSIS:
                result = await self._analyze_influence(parameters)
            elif analytics_type == GraphAnalyticsType.NETWORK_STRUCTURE:
                result = await self._analyze_network_structure(parameters)
            elif analytics_type == GraphAnalyticsType.KNOWLEDGE_FLOW:
                result = await self._analyze_knowledge_flow(parameters)
            elif analytics_type == GraphAnalyticsType.PATTERN_MINING:
                result = await self._mine_patterns(parameters)
            else:
                raise ValueError(f"Unknown analytics type: {analytics_type}")

            # Cache result
            if use_cache:
                self._cache_result(analytics_type, parameters, result)

            # Update statistics
            execution_time = time.time() - start_time
            self._update_stats(analytics_type.value, execution_time)

            result["execution_time_ms"] = execution_time * 1000
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            result["cache_hit"] = use_cache

            return result

        except Exception as e:
            logger.error(f"Graph analytics failed for {analytics_type}: {e}")
            raise

    async def get_graph_metrics(self, force_refresh: bool = False) -> GraphMetrics:
        """Get comprehensive graph metrics with caching"""
        if not force_refresh and self._is_metrics_cache_valid():
            assert self.graph_metrics_cache is not None  # Type narrowing
            return self.graph_metrics_cache

        try:
            # Basic counts
            node_count_result = await self._execute_cypher(
                "MATCH (n) RETURN count(n) as count"
            )
            node_count = int(node_count_result[0]["count"])

            edge_count_result = await self._execute_cypher(
                "MATCH ()-[r]->() RETURN count(r) as count"
            )
            edge_count = int(edge_count_result[0]["count"])

            # Density calculation
            density = 0.0
            if node_count > 1:
                max_edges = node_count * (node_count - 1)
                density = edge_count / max_edges if max_edges > 0 else 0.0

            # Average degree
            avg_degree = (2 * edge_count) / node_count if node_count > 0 else 0.0

            # Connected components
            components_result = await self._execute_cypher(
                """
                MATCH (n)
                WITH collect(DISTINCT n) as nodes
                UNWIND nodes as node
                MATCH (node)-[*0..]->(connected)
                WITH node, collect(DISTINCT connected) as component
                RETURN count(DISTINCT component) as components,
                       max(size(component)) as largest_component
            """
            )

            connected_components = int(components_result[0].get("components", 1))
            largest_component_size = int(
                components_result[0].get("largest_component", node_count)
            )

            # Clustering coefficient (simplified)
            clustering_coeff = await self._compute_global_clustering_coefficient()

            # Diameter (approximate for performance)
            diameter = await self._estimate_graph_diameter()

            metrics = GraphMetrics(
                node_count=node_count,
                edge_count=edge_count,
                density=density,
                average_degree=avg_degree,
                clustering_coefficient=clustering_coeff,
                diameter=diameter,
                connected_components=connected_components,
                largest_component_size=largest_component_size,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # Cache metrics
            self.graph_metrics_cache = metrics
            self.last_metrics_update = datetime.now(timezone.utc)

            return metrics

        except Exception as e:
            logger.error(f"Failed to compute graph metrics: {e}")
            raise

    async def find_shortest_paths(
        self,
        source_node: str,
        target_node: Optional[str] = None,
        max_hops: int = 6,
        relationship_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find shortest paths between nodes"""
        if target_node:
            # Single target path
            rel_pattern = f"[r:{relationship_filter}]" if relationship_filter else "[r]"
            query = f"""
            MATCH path = shortestPath((source {{id: '{source_node}'}})-{rel_pattern}*1..{max_hops}-(target {{id: '{target_node}'}}))
            RETURN path, length(path) as path_length
            """
        else:
            # All reachable nodes from source
            rel_pattern = f"[r:{relationship_filter}]" if relationship_filter else "[r]"
            query = f"""
            MATCH path = (source {{id: '{source_node}'}})-{rel_pattern}*1..{max_hops}-(target)
            WITH target, min(length(path)) as min_length
            RETURN target.id as target_id, min_length
            ORDER BY min_length, target_id
            LIMIT 100
            """

        results = await self._execute_cypher(query)

        return {
            "source_node": source_node,
            "target_node": target_node,
            "max_hops": max_hops,
            "paths": results,
            "path_count": len(results),
        }

    async def detect_knowledge_clusters(
        self,
        entity_type: str = "Entity",
        similarity_threshold: float = 0.7,
        min_cluster_size: int = 3,
    ) -> Dict[str, Any]:
        """Detect clusters of related knowledge entities"""
        # Use relationship strength and semantic similarity
        query = f"""
        MATCH (a:{entity_type})-[r]-(b:{entity_type})
        WHERE a.id < b.id
        WITH a, b, count(r) as relationship_strength
        WHERE relationship_strength >= {min_cluster_size}
        RETURN a.id as entity_a, b.id as entity_b, relationship_strength
        ORDER BY relationship_strength DESC
        """

        results = await self._execute_cypher(query)

        # Simple clustering algorithm (connected components)
        clusters = self._build_clusters_from_pairs(results, min_cluster_size)

        return {
            "entity_type": entity_type,
            "similarity_threshold": similarity_threshold,
            "min_cluster_size": min_cluster_size,
            "clusters": clusters,
            "cluster_count": len(clusters),
        }

    async def analyze_entity_importance(
        self, entity_type: str = "Entity", algorithm: str = "degree_centrality"
    ) -> Dict[str, Any]:
        """Analyze entity importance using various centrality measures"""
        if algorithm == "degree_centrality":
            query = f"""
            MATCH (n:{entity_type})
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as degree
            RETURN n.id as entity_id, degree
            ORDER BY degree DESC
            LIMIT 50
            """
        elif algorithm == "betweenness_centrality":
            # Simplified betweenness (expensive operation)
            query = f"""
            MATCH (n:{entity_type})
            MATCH path = allShortestPaths((a)-[*]-(b))
            WHERE a <> b AND a <> n AND b <> n
            WITH n, path, nodes(path) as path_nodes
            WHERE n IN path_nodes
            WITH n, count(path) as betweenness
            RETURN n.id as entity_id, betweenness
            ORDER BY betweenness DESC
            LIMIT 50
            """
        elif algorithm == "pagerank":
            # PageRank approximation
            query = f"""
            MATCH (n:{entity_type})
            OPTIONAL MATCH (n)<-[r]-()
            WITH n, count(r) as inbound_degree
            RETURN n.id as entity_id, inbound_degree as pagerank_score
            ORDER BY pagerank_score DESC
            LIMIT 50
            """
        else:
            raise ValueError(f"Unknown centrality algorithm: {algorithm}")

        results = await self._execute_cypher(query)

        return {
            "entity_type": entity_type,
            "algorithm": algorithm,
            "entities": results,
            "entity_count": len(results),
        }

    async def get_analytics_stats(self) -> Dict[str, Any]:
        """Get analytics engine performance statistics"""
        return {
            "analytics_stats": self.analytics_stats,
            "cache_size": len(self.query_cache),
            "metrics_cached": self.graph_metrics_cache is not None,
            "last_metrics_update": (
                self.last_metrics_update.isoformat()
                if self.last_metrics_update
                else None
            ),
        }

    # Private methods

    async def _compute_centrality(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Compute various centrality measures"""
        entity_type = parameters.get("entity_type", "Entity")
        algorithm = parameters.get("algorithm", "degree_centrality")
        limit = parameters.get("limit", 50)

        return await self.analyze_entity_importance(entity_type, algorithm)

    async def _detect_communities(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Detect communities using graph clustering"""
        entity_type = parameters.get("entity_type", "Entity")
        min_cluster_size = parameters.get("min_cluster_size", 3)

        return await self.detect_knowledge_clusters(
            entity_type, min_cluster_size=min_cluster_size
        )

    async def _analyze_paths(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze paths between entities"""
        source = parameters.get("source_node")
        target = parameters.get("target_node")
        max_hops = parameters.get("max_hops", 6)

        if not source:
            raise ValueError("source_node parameter is required for path analysis")

        return await self.find_shortest_paths(source, target, max_hops)

    async def _compute_similarity(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Compute entity similarity"""
        entity_id = parameters.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id parameter is required for similarity analysis")

        # Find entities with similar relationships
        query = f"""
        MATCH (target {{id: '{entity_id}'}})-[r1]-(common)-[r2]-(similar)
        WHERE target <> similar
        WITH similar, count(DISTINCT common) as common_neighbors
        RETURN similar.id as entity_id, common_neighbors
        ORDER BY common_neighbors DESC
        LIMIT 20
        """

        results = await self._execute_cypher(query)

        return {
            "source_entity": entity_id,
            "similar_entities": results,
            "similarity_count": len(results),
        }

    async def _compute_clustering(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Compute clustering metrics"""
        return await self.detect_knowledge_clusters()

    async def _analyze_temporal_patterns(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze temporal patterns in the graph"""
        time_field = parameters.get("time_field", "timestamp")
        interval = parameters.get("interval", "day")

        query = f"""
        MATCH (n)
        WHERE n.{time_field} IS NOT NULL
        WITH date(n.{time_field}) as activity_date, count(n) as activity_count
        RETURN activity_date, activity_count
        ORDER BY activity_date DESC
        LIMIT 30
        """

        results = await self._execute_cypher(query)

        return {
            "time_field": time_field,
            "interval": interval,
            "temporal_data": results,
            "data_points": len(results),
        }

    async def _analyze_influence(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze influence propagation"""
        return await self.analyze_entity_importance(algorithm="pagerank")

    async def _analyze_network_structure(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze network structure properties"""
        metrics = await self.get_graph_metrics()

        # Additional structural analysis
        hub_query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-()
        WITH n, count(r) as degree
        WHERE degree > 10
        RETURN count(n) as hub_count, max(degree) as max_degree
        """

        hub_results = await self._execute_cypher(hub_query)

        return {
            "basic_metrics": {
                "node_count": metrics.node_count,
                "edge_count": metrics.edge_count,
                "density": metrics.density,
                "average_degree": metrics.average_degree,
                "clustering_coefficient": metrics.clustering_coefficient,
            },
            "hub_analysis": hub_results[0] if hub_results else {},
            "connected_components": metrics.connected_components,
        }

    async def _analyze_knowledge_flow(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze knowledge flow patterns"""
        # Track how information flows through the graph
        query = """
        MATCH path = (source)-[*2..4]->(target)
        WHERE source.type = 'concept' AND target.type = 'concept'
        WITH source, target, min(length(path)) as shortest_path
        RETURN source.id as source_concept, target.id as target_concept, shortest_path
        ORDER BY shortest_path
        LIMIT 100
        """

        results = await self._execute_cypher(query)

        return {"knowledge_flows": results, "flow_count": len(results)}

    async def _mine_patterns(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mine frequent patterns in the graph"""
        pattern_type = parameters.get("pattern_type", "relationship")
        min_frequency = parameters.get("min_frequency", 5)

        if pattern_type == "relationship":
            query = f"""
            MATCH (a)-[r]->(b)
            WITH type(r) as relationship_type, count(*) as frequency
            WHERE frequency >= {min_frequency}
            RETURN relationship_type, frequency
            ORDER BY frequency DESC
            """
        else:
            query = f"""
            MATCH (n)
            WITH labels(n) as node_labels, count(*) as frequency
            WHERE frequency >= {min_frequency}
            RETURN node_labels, frequency
            ORDER BY frequency DESC
            """

        results = await self._execute_cypher(query)

        return {
            "pattern_type": pattern_type,
            "min_frequency": min_frequency,
            "patterns": results,
            "pattern_count": len(results),
        }

    async def _execute_cypher(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute Cypher query and return results"""
        try:
            result = self.connection.execute(query, parameters or {})

            # Convert result to list of dictionaries
            rows = []
            if hasattr(result, "get_next"):
                col_names = result.get_column_names()
                while result.has_next():
                    row = result.get_next()
                    row_dict = dict(zip(col_names, row))
                    rows.append(row_dict)

            return rows

        except Exception as e:
            logger.error(f"Cypher query execution failed: {query[:100]}... - {e}")
            raise

    async def _compute_global_clustering_coefficient(self) -> float:
        """Compute global clustering coefficient"""
        try:
            query = """
            MATCH (n)-[r1]-(m)-[r2]-(o)
            WHERE n <> o
            WITH n, count(DISTINCT m) as common_neighbors
            OPTIONAL MATCH (n)-[direct]-(o)
            WITH n, common_neighbors, count(direct) as direct_connections
            RETURN avg(direct_connections / (common_neighbors * (common_neighbors - 1) / 2.0)) as clustering_coeff
            """

            result = await self._execute_cypher(query)
            return result[0].get("clustering_coeff", 0.0) if result else 0.0

        except Exception:
            return 0.0  # Fallback

    async def _estimate_graph_diameter(self) -> Optional[int]:
        """Estimate graph diameter (maximum shortest path)"""
        try:
            # Sample-based diameter estimation for performance
            query = """
            MATCH (n)
            WITH n ORDER BY rand() LIMIT 10
            MATCH path = shortestPath((n)-[*]-(m))
            WHERE n <> m
            RETURN max(length(path)) as max_path_length
            """

            result = await self._execute_cypher(query)
            return result[0].get("max_path_length") if result else None

        except Exception:
            return None

    def _build_clusters_from_pairs(
        self, pairs: List[Dict], min_size: int
    ) -> List[List[str]]:
        """Build clusters from entity pairs using union-find"""
        # Simple clustering implementation
        entity_map: Dict[str, int] = {}
        clusters: List[List[str]] = []

        for pair in pairs:
            entity_a = str(pair["entity_a"])
            entity_b = str(pair["entity_b"])

            cluster_a = entity_map.get(entity_a)
            cluster_b = entity_map.get(entity_b)

            if cluster_a is None and cluster_b is None:
                # Create new cluster
                new_cluster = [entity_a, entity_b]
                clusters.append(new_cluster)
                entity_map[entity_a] = len(clusters) - 1
                entity_map[entity_b] = len(clusters) - 1
            elif cluster_a is not None and cluster_b is None:
                # Add to existing cluster
                clusters[cluster_a].append(entity_b)
                entity_map[entity_b] = cluster_a
            elif cluster_a is None and cluster_b is not None:
                # Add to existing cluster
                clusters[cluster_b].append(entity_a)
                entity_map[entity_a] = cluster_b
            elif (
                cluster_a is not None
                and cluster_b is not None
                and cluster_a != cluster_b
            ):
                # Merge clusters
                clusters[cluster_a].extend(clusters[cluster_b])
                for entity in clusters[cluster_b]:
                    entity_map[entity] = cluster_a
                clusters[cluster_b] = []

        # Filter by minimum size
        return [cluster for cluster in clusters if len(cluster) >= min_size]

    def _get_cached_result(
        self, analytics_type: GraphAnalyticsType, parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached analytics result"""
        cache_key = f"{analytics_type.value}:{hash(str(parameters))}"
        cached_data = self.query_cache.get(cache_key)

        if cached_data:
            result, timestamp = cached_data
            if (time.time() - timestamp) < self.cache_ttl:
                return result
            else:
                del self.query_cache[cache_key]

        return None

    def _cache_result(
        self,
        analytics_type: GraphAnalyticsType,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Cache analytics result"""
        cache_key = f"{analytics_type.value}:{hash(str(parameters))}"
        self.query_cache[cache_key] = (result, time.time())

        # Simple cache cleanup
        if len(self.query_cache) > 100:
            # Remove oldest entries
            sorted_items = sorted(self.query_cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:20]:
                del self.query_cache[key]

    def _is_metrics_cache_valid(self) -> bool:
        """Check if graph metrics cache is still valid"""
        if not self.graph_metrics_cache or not self.last_metrics_update:
            return False

        return (
            datetime.now(timezone.utc) - self.last_metrics_update
        ).total_seconds() < self.metrics_cache_ttl

    def _update_stats(self, query_type: str, execution_time: float) -> None:
        """Update analytics statistics"""
        self.analytics_stats["total_queries"] += 1

        # Update query type stats
        if query_type not in self.analytics_stats["query_types"]:
            self.analytics_stats["query_types"][query_type] = {
                "count": 0,
                "total_time": 0,
            }

        self.analytics_stats["query_types"][query_type]["count"] += 1
        self.analytics_stats["query_types"][query_type]["total_time"] += execution_time

        # Update average execution time
        total_queries = self.analytics_stats["total_queries"]
        current_avg = self.analytics_stats["average_execution_time"]
        self.analytics_stats["average_execution_time"] = (
            current_avg * (total_queries - 1) + execution_time
        ) / total_queries
