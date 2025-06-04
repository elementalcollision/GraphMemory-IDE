"""
Main analytics engine for GraphMemory-IDE.
Coordinates graph algorithms, ML analytics, caching, and real-time updates.
Enhanced with Phase 3 capabilities: GPU acceleration, performance monitoring, and concurrent processing.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union
import kuzu
import numpy as np

from .models import (
    AnalyticsRequest, AnalyticsResponse, AnalyticsType,
    CentralityRequest, CentralityResponse,
    CommunityRequest, CommunityResponse,
    ClusteringRequest, ClusteringResponse,
    PathAnalysisRequest, PathAnalysisResponse,
    GraphMetrics, NodeMetrics, RealtimeUpdate,
    CentralityType, ClusteringType
)
from .cache import AnalyticsCache
from .realtime import RealtimeAnalytics
from .algorithms import GraphAlgorithms, MLAnalytics

# Phase 3 imports
from .gpu_acceleration import gpu_manager
from .performance_monitor import performance_monitor
from .concurrent_processing import concurrent_manager

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """
    Main analytics engine that coordinates all analytics operations.
    Provides unified interface for graph analytics, ML, caching, and real-time updates.
    Enhanced with Phase 3 capabilities for production deployment.
    """
    
    def __init__(self, kuzu_connection: kuzu.Connection, redis_url: str = "redis://localhost:6379") -> None:
        self.kuzu_conn = kuzu_connection
        self.cache = AnalyticsCache(redis_url)
        self.realtime = RealtimeAnalytics()
        
        # Initialize advanced algorithm engines
        self.graph_algorithms = GraphAlgorithms()
        self.ml_analytics = MLAnalytics()
        
        # Phase 3 components
        self.gpu_manager = gpu_manager
        self.performance_monitor = performance_monitor
        self.concurrent_manager = concurrent_manager
        
        self.initialized = False
        
        # Simple in-memory implementations to avoid complex dependencies for now
        self._graph_cache = {}
        self._last_graph_update = 0
    
    async def initialize(self) -> None:
        """Initialize the analytics engine with Phase 3 components"""
        if self.initialized:
            return
        
        try:
            logger.info("Initializing analytics engine...")
            
            # Initialize database connection
            await self.kuzu_conn.connect()
            
            # Initialize core components
            await self.cache.connect()
            
            # Initialize Phase 3 components
            await self.concurrent_manager.initialize()
            
            # Update GPU info in performance monitoring
            gpu_status = self.gpu_manager.get_acceleration_status()
            self.performance_monitor.update_gpu_memory_usage(0)  # Initialize metric
            
            logger.info(
                f"Analytics engine initialized successfully. "
                f"GPU acceleration: {'enabled' if gpu_status['gpu_available'] else 'disabled'}"
            )
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics engine: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the analytics engine and Phase 3 components"""
        await self.realtime.shutdown()
        await self.cache.close()
        await self.concurrent_manager.shutdown()
        self.initialized = False
        logger.info("Analytics engine shutdown complete")
    
    async def get_graph_data(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict]]:
        """Retrieve graph data from Kuzu database with performance monitoring"""
        with self.performance_monitor.monitor_graph_operation("data_retrieval", 0):
            try:
                # Get nodes
                node_query = "MATCH (n) RETURN n"
                node_result = self.kuzu_conn.execute(node_query)
                
                nodes = []
                # Handle both QueryResult objects and list results
                if hasattr(node_result, 'has_next'):
                    # QueryResult object with iterator interface
                    while node_result.has_next():
                        row = node_result.get_next()
                        if row and len(row) > 0:
                            node_data = row[0] if isinstance(row[0], dict) else {"id": str(row[0])}
                            nodes.append(node_data)
                elif isinstance(node_result, list):
                    # Direct list result
                    for row in node_result:
                        if row and len(row) > 0:
                            node_data = row[0] if isinstance(row[0], dict) else {"id": str(row[0])}
                            nodes.append(node_data)
                
                # Get edges/relationships
                edge_query = "MATCH (a)-[r]->(b) RETURN a, r, b"
                edge_result = self.kuzu_conn.execute(edge_query)
                
                edges = []
                # Handle both QueryResult objects and list results
                if hasattr(edge_result, 'has_next'):
                    # QueryResult object with iterator interface
                    while edge_result.has_next():
                        row = edge_result.get_next()
                        if row and len(row) >= 3:
                            source_id = row[0].get('id') if isinstance(row[0], dict) else str(row[0])
                            target_id = row[2].get('id') if isinstance(row[2], dict) else str(row[2])
                            rel_data = row[1] if isinstance(row[1], dict) else {}
                            
                            edge = {
                                "source": source_id,
                                "target": target_id,
                                **rel_data
                            }
                            edges.append(edge)
                elif isinstance(edge_result, list):
                    # Direct list result
                    for row in edge_result:
                        if row and len(row) >= 3:
                            source_id = row[0].get('id') if isinstance(row[0], dict) else str(row[0])
                            target_id = row[2].get('id') if isinstance(row[2], dict) else str(row[2])
                            rel_data = row[1] if isinstance(row[1], dict) else {}
                            
                            edge = {
                                "source": source_id,
                                "target": target_id,
                                **rel_data
                            }
                            edges.append(edge)
                
                # Update graph size metrics
                self.performance_monitor.update_graph_size(len(nodes), len(edges))
                
                return {"nodes": nodes, "edges": edges}
                
            except Exception as e:
                logger.error(f"Failed to retrieve graph data: {e}")
                # Return empty graph as fallback
                return {"nodes": [], "edges": []}
    
    async def calculate_graph_metrics(self, filters: Optional[Dict[str, Any]] = None) -> GraphMetrics:
        """Calculate basic graph metrics with performance monitoring"""
        with self.performance_monitor.monitor_graph_operation("metrics_calculation", 0):
            graph_data = await self.get_graph_data(filters)
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]
            
            node_count = len(nodes)
            edge_count = len(edges)
            
            if node_count == 0:
                return GraphMetrics(
                    node_count=0, edge_count=0, density=0.0,
                    average_clustering=0.0, connected_components=0,
                    largest_component_size=0
                )
            
            # Calculate density
            max_edges = node_count * (node_count - 1) / 2
            density = edge_count / max_edges if max_edges > 0 else 0.0
            
            # Basic connected components analysis
            # Build adjacency list
            adjacency = {}
            for node in nodes:
                node_id = node.get('id', str(node))
                adjacency[node_id] = set()
            
            for edge in edges:
                source = edge.get('source')
                target = edge.get('target')
                if source in adjacency and target in adjacency:
                    adjacency[source].add(target)
                    adjacency[target].add(source)
            
            # Find connected components using DFS
            visited = set()
            components = []
            
            def dfs(node, component) -> None:
                if node in visited:
                    return
                visited.add(node)
                component.append(node)
                for neighbor in adjacency.get(node, []):
                    dfs(neighbor, component)
            
            for node_id in adjacency:
                if node_id not in visited:
                    component = []
                    dfs(node_id, component)
                    if component:
                        components.append(component)
            
            connected_components = len(components)
            largest_component_size = max(len(c) for c in components) if components else 0
            
            return GraphMetrics(
                node_count=node_count,
                edge_count=edge_count,
                density=density,
                average_clustering=0.0,  # Would need more complex calculation
                connected_components=connected_components,
                largest_component_size=largest_component_size
            )
    
    async def analyze_centrality(self, request: CentralityRequest) -> CentralityResponse:
        """Perform centrality analysis using advanced NetworkX algorithms with GPU acceleration"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"centrality_{request.centrality_type}_{hash(str(request.dict()))}"
        cached_result = await self.cache.get("centrality", {"key": cache_key})
        
        if cached_result:
            self.performance_monitor.record_cache_hit()
            cached_result["cache_hit"] = True
            return CentralityResponse(**cached_result)
        
        self.performance_monitor.record_cache_miss()
        
        try:
            # Get graph data
            graph_data = await self.get_graph_data(request.filters)
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]
            
            if not nodes:
                return CentralityResponse(
                    centrality_type=request.centrality_type,
                    top_nodes=[],
                    statistics={},
                    graph_metrics=GraphMetrics(
                        node_count=0, edge_count=0, density=0.0,
                        average_clustering=0.0, connected_components=0,
                        largest_component_size=0
                    ),
                    execution_time=time.time() - start_time,
                    cache_hit=False
                )
            
            # Determine backend and graph size category
            graph_size = len(nodes)
            backend = "cugraph" if self.gpu_manager.cugraph_backend else "networkx"
            size_category = self._get_graph_size_category(graph_size)
            
            # Monitor algorithm execution
            algorithm_name = f"{request.centrality_type}_centrality"
            with self.performance_monitor.monitor_algorithm(algorithm_name, backend, size_category):
                # Use advanced algorithms with potential GPU acceleration
                # Add default limit if not provided
                limit = getattr(request, 'limit', 50)  # Default to 50 if limit not specified
                centrality_result = await self.graph_algorithms.calculate_centrality(
                    graph_data, request.centrality_type, limit
                )
            
            # Calculate graph metrics
            graph_metrics = await self.calculate_graph_metrics(request.filters)
            
            # Prepare response
            response_data = {
                "centrality_type": request.centrality_type,
                "top_nodes": centrality_result.get("top_nodes", []),
                "statistics": centrality_result.get("statistics", {}),
                "graph_metrics": graph_metrics,
                "execution_time": time.time() - start_time,
                "cache_hit": False,
                "backend_used": backend,
                "gpu_accelerated": self.gpu_manager.is_algorithm_accelerated(algorithm_name)
            }
            
            # Cache the result
            await self.cache.set("centrality", {"key": cache_key}, response_data, ttl=3600)
            
            # Send real-time update
            update = RealtimeUpdate(
                type="centrality_analysis",
                data={"centrality_type": request.centrality_type, "node_count": len(nodes)},
                timestamp=time.time()
            )
            await self.realtime.publish_update("centrality", update)
            
            return CentralityResponse(**response_data)
            
        except Exception as e:
            logger.error(f"Centrality analysis failed: {e}")
            raise
    
    def _get_graph_size_category(self, node_count: int) -> str:
        """Categorize graph size for monitoring"""
        if node_count < 1000:
            return "small"
        elif node_count < 10000:
            return "medium"
        elif node_count < 100000:
            return "large"
        else:
            return "xlarge"
    
    async def get_phase3_status(self) -> Dict[str, Any]:
        """Get comprehensive Phase 3 status information"""
        return {
            "gpu_acceleration": self.gpu_manager.get_acceleration_status(),
            "performance_metrics": self.performance_monitor.get_performance_summary(),
            "concurrent_processing": self.concurrent_manager.get_executor_status(),
            "system_health": await self.concurrent_manager.health_check()
        }

    async def detect_communities(self, request: CommunityRequest) -> CommunityResponse:
        """Perform community detection using advanced NetworkX algorithms"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"community_{request.algorithm}_{hash(str(request.dict()))}"
        cached_result = await self.cache.get("community", {"key": cache_key})
        
        if cached_result:
            cached_result["cache_hit"] = True
            return CommunityResponse(**cached_result)
        
        try:
            # Get graph data
            graph_data = await self.get_graph_data(request.filters)
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]
            
            if not nodes:
                return CommunityResponse(
                    algorithm=request.algorithm,
                    modularity=0.0,
                    num_communities=0,
                    community_sizes=[],
                    graph_metrics=GraphMetrics(
                        node_count=0, edge_count=0, density=0.0,
                        average_clustering=0.0, connected_components=0,
                        largest_component_size=0
                    ),
                    execution_time=time.time() - start_time,
                    cache_hit=False
                )
            
            # Build NetworkX graph
            nx_graph = self.graph_algorithms.build_networkx_graph(nodes, edges)
            
            # Detect communities using advanced algorithms
            partition, modularity, community_metrics = await self.graph_algorithms.detect_communities(
                nx_graph,
                algorithm=request.algorithm,
                resolution=request.resolution,
                min_community_size=request.min_community_size
            )
            
            # Calculate community sizes
            community_sizes = {}
            for node, comm_id in partition.items():
                community_sizes[comm_id] = community_sizes.get(comm_id, 0) + 1
            
            community_size_list = list(community_sizes.values())
            num_communities = len(community_size_list)
            
            # Calculate graph metrics
            graph_metrics = await self.graph_algorithms.calculate_graph_metrics(nx_graph)
            
            execution_time = time.time() - start_time
            
            result = CommunityResponse(
                algorithm=request.algorithm,
                modularity=modularity,
                num_communities=num_communities,
                community_sizes=community_size_list,
                community_metrics=community_metrics,
                graph_metrics=graph_metrics,
                execution_time=execution_time,
                cache_hit=False
            )
            
            # Cache the result
            await self.cache.set("community", {"key": cache_key}, result.dict(), ttl=3600)
            
            # Send real-time update
            update = RealtimeUpdate(
                update_type="community_complete",
                data={
                    "algorithm": request.algorithm,
                    "num_communities": num_communities,
                    "modularity": modularity,
                    "execution_time": execution_time
                }
            )
            await self.realtime.publish_update("community", update)
            
            return result
            
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            raise
    
    async def analyze_paths(self, request: PathAnalysisRequest) -> PathAnalysisResponse:
        """Perform path analysis"""
        start_time = time.time()
        
        try:
            # Get graph data
            graph_data = await self.get_graph_data(request.filters)
            graph_metrics = await self.calculate_graph_metrics(request.filters)
            
            # Simple shortest path analysis
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]
            
            # Build adjacency list
            adjacency = {}
            for node in nodes:
                node_id = node.get('id', str(node))
                adjacency[node_id] = []
            
            for edge in edges:
                source = edge.get('source')
                target = edge.get('target')
                if source in adjacency and target in adjacency:
                    adjacency[source].append(target)
                    adjacency[target].append(source)
            
            # Simple BFS for shortest paths
            paths = []
            target_nodes = request.target_nodes or list(adjacency.keys())
            
            for source in request.source_nodes:
                if source not in adjacency:
                    continue
                
                # BFS from source
                queue = [(source, [source])]
                visited = {source}
                
                while queue:
                    current, path = queue.pop(0)
                    
                    if len(path) > request.max_depth + 1:
                        continue
                    
                    for neighbor in adjacency.get(current, []):
                        if neighbor not in visited:
                            new_path = path + [neighbor]
                            
                            if neighbor in target_nodes and neighbor != source:
                                paths.append({
                                    "source": source,
                                    "target": neighbor,
                                    "path": new_path,
                                    "length": len(new_path) - 1
                                })
                            
                            if len(new_path) <= request.max_depth + 1:
                                queue.append((neighbor, new_path))
                                visited.add(neighbor)
            
            # Calculate statistics
            path_statistics = {}
            if paths:
                lengths = [p["length"] for p in paths]
                path_statistics = {
                    "average_path_length": sum(lengths) / len(lengths),
                    "min_path_length": min(lengths),
                    "max_path_length": max(lengths),
                    "total_paths": len(paths)
                }
            
            execution_time = time.time() - start_time
            
            response = PathAnalysisResponse(
                paths_found=len(paths),
                paths=paths[:100],  # Limit to first 100 paths
                path_statistics=path_statistics,
                execution_time=execution_time,
                graph_metrics=graph_metrics
            )
            
            # Publish real-time update
            update = RealtimeUpdate(
                update_type="path_analysis_complete",
                data={
                    "paths_found": len(paths),
                    "execution_time": execution_time
                }
            )
            await self.realtime.publish_update("path_analysis", update)
            
            return response
            
        except Exception as e:
            logger.error(f"Path analysis failed: {e}")
            raise
    
    async def process_analytics_request(self, request: AnalyticsRequest) -> AnalyticsResponse:
        """Process any analytics request and route to appropriate handler"""
        if not self.initialized:
            await self.initialize()
        
        if request.analytics_type == AnalyticsType.CENTRALITY:
            return await self.analyze_centrality(CentralityRequest(**request.dict()))
        elif request.analytics_type == AnalyticsType.COMMUNITY:
            return await self.detect_communities(CommunityRequest(**request.dict()))
        elif request.analytics_type == AnalyticsType.PATH_ANALYSIS:
            return await self.analyze_paths(PathAnalysisRequest(**request.dict()))
        elif request.analytics_type == AnalyticsType.GRAPH_METRICS:
            start_time = time.time()
            metrics = await self.calculate_graph_metrics(request.filters)
            execution_time = time.time() - start_time
            
            return AnalyticsResponse(
                analytics_type=AnalyticsType.GRAPH_METRICS,
                execution_time=execution_time,
                graph_metrics=metrics
            )
        else:
            raise ValueError(f"Unsupported analytics type: {request.analytics_type}")
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get analytics engine statistics"""
        return {
            "initialized": self.initialized,
            "cache_stats": asyncio.create_task(self.cache.get_cache_stats()),
            "realtime_stats": self.realtime.get_realtime_stats(),
            "graph_cache_size": len(self._graph_cache)
        }

    async def perform_clustering(self, request: ClusteringRequest) -> ClusteringResponse:
        """Perform ML clustering analysis using scikit-learn algorithms"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"clustering_{request.clustering_type}_{hash(str(request.dict()))}"
        cached_result = await self.cache.get("clustering", {"key": cache_key})
        
        if cached_result:
            cached_result["cache_hit"] = True
            return ClusteringResponse(**cached_result)
        
        try:
            # Get graph data
            graph_data = await self.get_graph_data(request.filters)
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]
            
            if not nodes:
                return ClusteringResponse(
                    clustering_type=request.clustering_type,
                    n_clusters=0,
                    silhouette_score=None,
                    cluster_centers=None,
                    graph_metrics=GraphMetrics(
                        node_count=0, edge_count=0, density=0.0,
                        average_clustering=0.0, connected_components=0,
                        largest_component_size=0
                    ),
                    execution_time=time.time() - start_time,
                    cache_hit=False
                )
            
            # Build NetworkX graph
            nx_graph = self.graph_algorithms.build_networkx_graph(nodes, edges)
            
            # Extract features for ML analysis
            features, node_ids, feature_names = await self.ml_analytics.extract_node_features(
                nx_graph,
                include_centrality=True,
                include_local_metrics=True
            )
            
            # Perform clustering
            labels, silhouette, centers = await self.ml_analytics.cluster_nodes(
                features,
                request.clustering_type,
                n_clusters=request.n_clusters,
                node_ids=node_ids
            )
            
            # Create node metrics with cluster assignments
            node_metrics = []
            for i, node_id in enumerate(node_ids):
                node_metrics.append(NodeMetrics(
                    node_id=node_id,
                    cluster_id=int(labels[i]),
                    local_clustering=0.0,  # Would need to calculate
                    degree=int(nx_graph.degree(node_id)) if node_id in nx_graph else 0,
                    neighbors=list(nx_graph.neighbors(node_id)) if node_id in nx_graph else []
                ))
            
            # Calculate graph metrics
            graph_metrics = await self.graph_algorithms.calculate_graph_metrics(nx_graph)
            
            execution_time = time.time() - start_time
            
            result = ClusteringResponse(
                clustering_type=request.clustering_type,
                n_clusters=len(set(labels)),
                silhouette_score=silhouette,
                cluster_centers=centers.tolist() if centers is not None else None,
                node_metrics=node_metrics,
                graph_metrics=graph_metrics,
                execution_time=execution_time,
                cache_hit=False,
                metadata={
                    "feature_names": feature_names,
                    "feature_count": len(feature_names)
                }
            )
            
            # Cache the result
            await self.cache.set("clustering", {"key": cache_key}, result.dict(), ttl=3600)
            
            # Send real-time update
            update = RealtimeUpdate(
                update_type="clustering_complete",
                data={
                    "clustering_type": request.clustering_type.value,
                    "n_clusters": len(set(labels)),
                    "silhouette_score": silhouette,
                    "execution_time": execution_time
                }
            )
            await self.realtime.publish_update("clustering", update)
            
            return result
            
        except Exception as e:
            logger.error(f"Clustering analysis failed: {e}")
            raise

    async def detect_anomalies(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Detect anomalous nodes using ML techniques"""
        start_time = time.time()
        
        try:
            # Get graph data
            graph_data = await self.get_graph_data(filters)
            nodes = graph_data["nodes"]
            edges = graph_data["edges"]
            
            if not nodes:
                return {
                    "anomalies": [],
                    "anomaly_scores": [],
                    "execution_time": time.time() - start_time
                }
            
            # Build NetworkX graph
            nx_graph = self.graph_algorithms.build_networkx_graph(nodes, edges)
            
            # Extract features for anomaly detection
            features, node_ids, feature_names = await self.ml_analytics.extract_node_features(
                nx_graph,
                include_centrality=True,
                include_local_metrics=True
            )
            
            # Detect anomalies
            anomaly_labels, anomaly_scores = await self.ml_analytics.detect_anomalies(
                features,
                contamination=0.1
            )
            
            # Identify anomalous nodes
            anomalous_nodes = []
            for i, (node_id, label, score) in enumerate(zip(node_ids, anomaly_labels, anomaly_scores)):
                if label == -1:  # Anomaly
                    anomalous_nodes.append({
                        "node_id": node_id,
                        "anomaly_score": float(score),
                        "features": features[i].tolist()
                    })
            
            execution_time = time.time() - start_time
            
            # Send real-time update
            update = RealtimeUpdate(
                update_type="anomaly_detection_complete",
                data={
                    "anomalies_found": len(anomalous_nodes),
                    "total_nodes": len(nodes),
                    "execution_time": execution_time
                }
            )
            await self.realtime.publish_update("anomaly_detection", update)
            
            return {
                "anomalies": anomalous_nodes,
                "anomaly_scores": anomaly_scores.tolist(),
                "feature_names": feature_names,
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            raise 