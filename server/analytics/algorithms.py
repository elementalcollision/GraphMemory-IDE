"""
Graph algorithms and machine learning analytics implementations.
Uses NetworkX for graph analysis and scikit-learn for ML capabilities.
"""

import networkx as nx
import numpy as np
from sklearn.cluster import SpectralClustering, KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import asyncio

from .models import (
    GraphMetrics, NodeMetrics, CommunityMetrics,
    CentralityType, ClusteringType
)

logger = logging.getLogger(__name__)

class GraphAlgorithms:
    """
    Graph analytics algorithms using NetworkX.
    Provides centrality measures, community detection, and path analysis.
    """
    
    def __init__(self) -> None:
        self.graph_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def build_networkx_graph(self, nodes: List[Dict], edges: List[Dict]) -> nx.Graph:
        """Build NetworkX graph from node and edge data"""
        G = nx.Graph()
        
        # Add nodes with attributes
        for node in nodes:
            node_id = node.get('id') or node.get('node_id')
            attributes = {k: v for k, v in node.items() if k not in ['id', 'node_id']}
            G.add_node(node_id, **attributes)
        
        # Add edges with attributes
        for edge in edges:
            source = edge.get('source') or edge.get('from')
            target = edge.get('target') or edge.get('to')
            weight = edge.get('weight', 1.0)
            attributes = {k: v for k, v in edge.items() 
                         if k not in ['source', 'target', 'from', 'to']}
            G.add_edge(source, target, weight=weight, **attributes)
        
        return G
    
    async def calculate_centrality(
        self, 
        graph: nx.Graph, 
        centrality_type: CentralityType,
        normalized: bool = True,
        node_filters: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """Calculate centrality measures for graph nodes"""
        
        def _calculate() -> Dict[str, float]:
            if centrality_type == CentralityType.BETWEENNESS:
                return nx.betweenness_centrality(graph, normalized=normalized)
            elif centrality_type == CentralityType.CLOSENESS:
                return nx.closeness_centrality(graph, normalized=normalized)
            elif centrality_type == CentralityType.EIGENVECTOR:
                try:
                    return nx.eigenvector_centrality(graph, max_iter=1000)
                except nx.PowerIterationFailedConvergence:
                    logger.warning("Eigenvector centrality failed to converge, using degree centrality")
                    return nx.degree_centrality(graph)
            elif centrality_type == CentralityType.PAGERANK:
                return nx.pagerank(graph)
            elif centrality_type == CentralityType.DEGREE:
                return nx.degree_centrality(graph)
            else:
                raise ValueError(f"Unknown centrality type: {centrality_type}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        centrality_scores = await loop.run_in_executor(self.executor, _calculate)
        
        # Filter nodes if specified
        if node_filters:
            centrality_scores = {
                node: score for node, score in centrality_scores.items()
                if node in node_filters
            }
        
        return centrality_scores
    
    async def detect_communities(
        self, 
        graph: nx.Graph,
        algorithm: str = "louvain",
        resolution: float = 1.0,
        min_community_size: int = 3
    ) -> Tuple[Dict[str, str], float, List[CommunityMetrics]]:
        """Detect communities in the graph"""
        
        def _detect() -> Tuple[Dict[str, str], float]:
            if algorithm == "louvain":
                try:
                    import community as community_louvain
                    partition = community_louvain.best_partition(graph, resolution=resolution)
                    modularity = community_louvain.modularity(partition, graph)
                except ImportError:
                    logger.warning("python-louvain not available, using greedy modularity")
                    communities = nx.community.greedy_modularity_communities(graph, resolution=resolution)
                    partition = {}
                    for i, community in enumerate(communities):
                        for node in community:
                            partition[node] = str(i)
                    modularity = nx.community.modularity(graph, communities)
            else:
                # Use NetworkX built-in algorithms
                if algorithm == "greedy_modularity":
                    communities = nx.community.greedy_modularity_communities(graph, resolution=resolution)
                elif algorithm == "label_propagation":
                    communities = nx.community.label_propagation_communities(graph)
                else:
                    raise ValueError(f"Unknown community detection algorithm: {algorithm}")
                
                partition = {}
                for i, community in enumerate(communities):
                    for node in community:
                        partition[node] = str(i)
                modularity = nx.community.modularity(graph, communities)
            
            return partition, modularity
        
        loop = asyncio.get_event_loop()
        partition, modularity = await loop.run_in_executor(self.executor, _detect)
        
        # Filter small communities
        community_sizes = {}
        for node, comm_id in partition.items():
            community_sizes[comm_id] = community_sizes.get(comm_id, 0) + 1
        
        filtered_partition = {
            node: comm_id for node, comm_id in partition.items()
            if community_sizes[comm_id] >= min_community_size
        }
        
        # Calculate community metrics
        community_metrics = await self._calculate_community_metrics(
            graph, filtered_partition
        )
        
        return filtered_partition, modularity, community_metrics
    
    async def _calculate_community_metrics(
        self, 
        graph: nx.Graph, 
        partition: Dict[str, str]
    ) -> List[CommunityMetrics]:
        """Calculate metrics for each community"""
        
        def _calculate() -> List[CommunityMetrics]:
            communities = {}
            for node, comm_id in partition.items():
                if comm_id not in communities:
                    communities[comm_id] = []
                communities[comm_id].append(node)
            
            metrics = []
            for comm_id, nodes in communities.items():
                subgraph = graph.subgraph(nodes)
                
                # Calculate community density
                possible_edges = len(nodes) * (len(nodes) - 1) / 2
                actual_edges = subgraph.number_of_edges()
                density = actual_edges / possible_edges if possible_edges > 0 else 0
                
                # Find central nodes (by degree within community)
                degrees = dict(subgraph.degree())
                central_nodes = sorted(degrees.keys(), key=lambda x: degrees[x], reverse=True)[:5]
                
                # Extract keywords from node attributes (if available)
                keywords = []
                for node in nodes:
                    node_data = graph.nodes[node]
                    if 'tags' in node_data:
                        keywords.extend(node_data['tags'])
                    if 'keywords' in node_data:
                        keywords.extend(node_data['keywords'])
                
                # Get most common keywords
                from collections import Counter
                keyword_counts = Counter(keywords)
                top_keywords = [kw for kw, _ in keyword_counts.most_common(10)]
                
                metrics.append(CommunityMetrics(
                    community_id=comm_id,
                    size=len(nodes),
                    density=density,
                    modularity_contribution=0.0,  # Would need full modularity calculation
                    central_nodes=central_nodes,
                    keywords=top_keywords
                ))
            
            return metrics
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _calculate)
    
    async def analyze_paths(
        self,
        graph: nx.Graph,
        source_nodes: List[str],
        target_nodes: Optional[List[str]] = None,
        max_depth: int = 5,
        path_type: str = "shortest"
    ) -> Dict[str, Any]:
        """Analyze paths between nodes"""
        
        def _analyze() -> Dict[str, Any]:
            results = {
                "paths": [],
                "statistics": {},
                "paths_found": 0
            }
            
            if target_nodes is None:
                target_nodes_list = list(graph.nodes())
            else:
                target_nodes_list = target_nodes
            
            for source in source_nodes:
                if source not in graph:
                    continue
                    
                for target in target_nodes_list:
                    if target not in graph or source == target:
                        continue
                    
                    try:
                        if path_type == "shortest":
                            if nx.has_path(graph, source, target):
                                path = nx.shortest_path(graph, source, target)
                                length = len(path) - 1
                                if length <= max_depth:
                                    results["paths"].append({
                                        "source": source,
                                        "target": target,
                                        "path": path,
                                        "length": length
                                    })
                                    results["paths_found"] += 1
                        elif path_type == "all_simple":
                            paths = list(nx.all_simple_paths(
                                graph, source, target, cutoff=max_depth
                            ))
                            for path in paths:
                                results["paths"].append({
                                    "source": source,
                                    "target": target,
                                    "path": path,
                                    "length": len(path) - 1
                                })
                                results["paths_found"] += 1
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue
            
            # Calculate statistics
            if results["paths"]:
                lengths = [p["length"] for p in results["paths"]]
                results["statistics"] = {
                    "average_path_length": float(np.mean(lengths)),
                    "min_path_length": int(min(lengths)),
                    "max_path_length": int(max(lengths)),
                    "total_paths": len(results["paths"])
                }
            
            return results
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _analyze)
    
    async def calculate_graph_metrics(self, graph: nx.Graph) -> GraphMetrics:
        """Calculate overall graph metrics"""
        
        def _calculate() -> GraphMetrics:
            # Basic metrics
            node_count = graph.number_of_nodes()
            edge_count = graph.number_of_edges()
            
            if node_count == 0:
                return GraphMetrics(
                    node_count=0, edge_count=0, density=0.0,
                    average_clustering=0.0, connected_components=0,
                    largest_component_size=0
                )
            
            # Density
            density = nx.density(graph)
            
            # Clustering
            try:
                average_clustering = nx.average_clustering(graph)
            except:
                average_clustering = 0.0
            
            # Connected components
            components = list(nx.connected_components(graph))
            connected_components = len(components)
            largest_component_size = max(len(c) for c in components) if components else 0
            
            # Path metrics (only for largest component if graph is disconnected)
            average_path_length = None
            diameter = None
            
            if connected_components == 1:
                try:
                    average_path_length = nx.average_shortest_path_length(graph)
                    diameter = nx.diameter(graph)
                except:
                    pass
            elif components:
                # Use largest component
                largest_component = max(components, key=len)
                subgraph = graph.subgraph(largest_component)
                try:
                    average_path_length = nx.average_shortest_path_length(subgraph)
                    diameter = nx.diameter(subgraph)
                except:
                    pass
            
            return GraphMetrics(
                node_count=node_count,
                edge_count=edge_count,
                density=density,
                average_clustering=average_clustering,
                average_path_length=average_path_length,
                diameter=diameter,
                connected_components=connected_components,
                largest_component_size=largest_component_size
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _calculate)


class MLAnalytics:
    """
    Machine learning analytics using scikit-learn.
    Provides clustering, pattern detection, and predictive analytics.
    """
    
    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.models = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def cluster_nodes(
        self,
        features: np.ndarray,
        clustering_type: ClusteringType,
        n_clusters: Optional[int] = None,
        node_ids: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, float, Optional[np.ndarray]]:
        """Perform clustering on node features"""
        
        def _cluster() -> None:
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Determine number of clusters if not specified
            if n_clusters is None:
                n_clusters_auto = min(10, max(2, int(np.sqrt(len(features) / 2))))
            else:
                n_clusters_auto = n_clusters
            
            # Perform clustering
            if clustering_type == ClusteringType.SPECTRAL:
                clusterer = SpectralClustering(
                    n_clusters=n_clusters_auto, 
                    random_state=42,
                    affinity='nearest_neighbors'
                )
            elif clustering_type == ClusteringType.KMEANS:
                clusterer = KMeans(n_clusters=n_clusters_auto, random_state=42)
            elif clustering_type == ClusteringType.HIERARCHICAL:
                clusterer = AgglomerativeClustering(n_clusters=n_clusters_auto)
            else:
                raise ValueError(f"Unknown clustering type: {clustering_type}")
            
            labels = clusterer.fit_predict(features_scaled)
            
            # Calculate silhouette score
            if len(set(labels)) > 1:
                silhouette = silhouette_score(features_scaled, labels)
            else:
                silhouette = 0.0
            
            # Get cluster centers if available
            centers = None
            if hasattr(clusterer, 'cluster_centers_'):
                centers = clusterer.cluster_centers_
            
            return labels, silhouette, centers
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _cluster)
    
    async def detect_anomalies(
        self,
        features: np.ndarray,
        contamination: float = 0.1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Detect anomalous nodes using isolation forest"""
        
        def _detect() -> None:
            from sklearn.ensemble import IsolationForest
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Fit isolation forest
            iso_forest = IsolationForest(
                contamination=contamination,
                random_state=42
            )
            
            anomaly_labels = iso_forest.fit_predict(features_scaled)
            anomaly_scores = iso_forest.score_samples(features_scaled)
            
            return anomaly_labels, anomaly_scores
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _detect)
    
    async def extract_node_features(
        self,
        graph: nx.Graph,
        include_centrality: bool = True,
        include_local_metrics: bool = True
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """Extract numerical features from graph nodes for ML analysis"""
        
        def _extract() -> None:
            nodes = list(graph.nodes())
            features = []
            feature_names = []
            
            # Basic structural features
            degrees = dict(graph.degree())
            clustering_coeffs = nx.clustering(graph)
            
            for node in nodes:
                node_features = []
                
                # Degree
                node_features.append(degrees[node])
                if not feature_names or len(feature_names) == len(node_features) - 1:
                    feature_names.append("degree")
                
                # Local clustering coefficient
                if include_local_metrics:
                    node_features.append(clustering_coeffs[node])
                    if len(feature_names) == len(node_features) - 1:
                        feature_names.append("clustering_coefficient")
                
                # Centrality measures
                if include_centrality:
                    try:
                        betweenness = nx.betweenness_centrality(graph)
                        closeness = nx.closeness_centrality(graph)
                        
                        node_features.append(betweenness.get(node, 0))
                        node_features.append(closeness.get(node, 0))
                        
                        if len(feature_names) == len(node_features) - 2:
                            feature_names.extend(["betweenness_centrality", "closeness_centrality"])
                    except:
                        # Fallback if centrality calculation fails
                        node_features.extend([0, 0])
                        if len(feature_names) == len(node_features) - 2:
                            feature_names.extend(["betweenness_centrality", "closeness_centrality"])
                
                # Node attributes (if numerical)
                node_data = graph.nodes[node]
                for attr, value in node_data.items():
                    if isinstance(value, (int, float)):
                        node_features.append(value)
                        if len(feature_names) == len(node_features) - 1:
                            feature_names.append(f"attr_{attr}")
                
                features.append(node_features)
            
            return np.array(features), nodes, feature_names
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _extract) 