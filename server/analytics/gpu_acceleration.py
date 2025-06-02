import os
import logging
import subprocess
from typing import Optional, Dict, Any, List, Union
import networkx as nx

logger = logging.getLogger(__name__)

class GPUAccelerationManager:
    """Manages GPU acceleration with cuGraph backend for NetworkX"""
    
    def __init__(self) -> None:
        self.gpu_available = False
        self.cugraph_backend = False
        self.fallback_reason: Optional[str] = None
        self.gpu_info: Dict[str, Any] = {}
        self._initialize_gpu_backend()
    
    def _initialize_gpu_backend(self) -> None:
        """Initialize GPU acceleration if available"""
        try:
            # Check for NVIDIA GPU
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                self.fallback_reason = "No NVIDIA GPU detected or nvidia-smi not available"
                logger.info("GPU acceleration unavailable: No NVIDIA GPU detected")
                return
            
            # Parse GPU information
            gpu_lines = result.stdout.strip().split('\n')
            if gpu_lines and gpu_lines[0]:
                gpu_data = gpu_lines[0].split(', ')
                if len(gpu_data) >= 3:
                    self.gpu_info = {
                        "name": gpu_data[0].strip(),
                        "memory_total_mb": int(gpu_data[1].strip()),
                        "driver_version": gpu_data[2].strip()
                    }
            
            # Try to import cuGraph
            try:
                import cugraph
                import nx_cugraph
                self.gpu_available = True
                
                # Enable cuGraph backend
                os.environ['NETWORKX_AUTOMATIC_BACKENDS'] = 'cugraph'
                self.cugraph_backend = True
                
                logger.info(
                    f"GPU acceleration enabled with cuGraph backend. "
                    f"GPU: {self.gpu_info.get('name', 'Unknown')}"
                )
                
            except ImportError as e:
                self.fallback_reason = f"cuGraph not available: {e}"
                logger.warning(f"GPU acceleration unavailable: {e}")
                
        except subprocess.TimeoutExpired:
            self.fallback_reason = "nvidia-smi timeout"
            logger.warning("GPU detection timeout")
        except Exception as e:
            self.fallback_reason = f"GPU initialization failed: {e}"
            logger.error(f"Failed to initialize GPU acceleration: {e}")
    
    def get_acceleration_status(self) -> Dict[str, Any]:
        """Get current GPU acceleration status"""
        status = {
            "gpu_available": self.gpu_available,
            "cugraph_backend": self.cugraph_backend,
            "fallback_reason": self.fallback_reason,
            "backend_info": self._get_backend_info()
        }
        
        if self.gpu_info:
            status["gpu_info"] = self.gpu_info
            
        return status
    
    def _get_backend_info(self) -> Dict[str, Any]:
        """Get detailed backend information"""
        info: Dict[str, Any] = {"networkx_version": nx.__version__}
        
        if self.cugraph_backend:
            try:
                import cugraph
                import nx_cugraph
                info["cugraph_version"] = cugraph.__version__
                info["nx_cugraph_version"] = nx_cugraph.__version__
                info["supported_algorithms"] = self._get_supported_algorithms()
                info["backend_enabled"] = os.environ.get('NETWORKX_AUTOMATIC_BACKENDS', 'none')
            except Exception as e:
                info["backend_error"] = str(e)
        
        return info
    
    def _get_supported_algorithms(self) -> List[str]:
        """Get list of GPU-accelerated algorithms"""
        # These are the main algorithms supported by cuGraph backend
        return [
            "pagerank", "betweenness_centrality", "closeness_centrality",
            "eigenvector_centrality", "louvain_communities", 
            "shortest_path", "connected_components", "triangles",
            "clustering", "core_number", "k_core", "degree_centrality",
            "edge_betweenness_centrality", "katz_centrality"
        ]
    
    def is_algorithm_accelerated(self, algorithm_name: str) -> bool:
        """Check if a specific algorithm is GPU-accelerated"""
        if not self.cugraph_backend:
            return False
        
        supported = self._get_supported_algorithms()
        return algorithm_name.lower() in supported
    
    def get_performance_estimate(self, algorithm_name: str, graph_size: int) -> Dict[str, Any]:
        """Estimate performance improvement for GPU acceleration"""
        if not self.is_algorithm_accelerated(algorithm_name):
            return {
                "accelerated": False,
                "estimated_speedup": 1.0,
                "recommendation": "CPU processing (algorithm not GPU-accelerated)"
            }
        
        # Performance estimates based on cuGraph benchmarks
        speedup_estimates = {
            "pagerank": min(50, max(5, graph_size // 1000)),
            "betweenness_centrality": min(500, max(10, graph_size // 100)),
            "closeness_centrality": min(100, max(5, graph_size // 500)),
            "eigenvector_centrality": min(30, max(3, graph_size // 2000)),
            "louvain_communities": min(200, max(8, graph_size // 200)),
            "connected_components": min(100, max(5, graph_size // 1000))
        }
        
        estimated_speedup = speedup_estimates.get(algorithm_name.lower(), 10.0)
        
        return {
            "accelerated": True,
            "estimated_speedup": round(estimated_speedup, 1),
            "recommendation": f"GPU acceleration recommended (estimated {estimated_speedup:.1f}x speedup)",
            "graph_size": graph_size,
            "gpu_memory_required_mb": self._estimate_memory_usage(graph_size)
        }
    
    def _estimate_memory_usage(self, graph_size: int) -> int:
        """Estimate GPU memory usage for graph processing"""
        # Rough estimate: 8 bytes per edge for adjacency matrix
        # Assume average degree of 10 for estimation
        estimated_edges = graph_size * 10
        memory_mb = (estimated_edges * 8) / (1024 * 1024)
        return int(memory_mb * 1.5)  # Add 50% buffer
    
    def enable_gpu_acceleration(self) -> bool:
        """Manually enable GPU acceleration if available"""
        if self.gpu_available and not self.cugraph_backend:
            try:
                os.environ['NETWORKX_AUTOMATIC_BACKENDS'] = 'cugraph'
                self.cugraph_backend = True
                logger.info("GPU acceleration manually enabled")
                return True
            except Exception as e:
                logger.error(f"Failed to enable GPU acceleration: {e}")
                return False
        return self.cugraph_backend
    
    def disable_gpu_acceleration(self) -> bool:
        """Manually disable GPU acceleration"""
        if self.cugraph_backend:
            try:
                if 'NETWORKX_AUTOMATIC_BACKENDS' in os.environ:
                    del os.environ['NETWORKX_AUTOMATIC_BACKENDS']
                self.cugraph_backend = False
                logger.info("GPU acceleration manually disabled")
                return True
            except Exception as e:
                logger.error(f"Failed to disable GPU acceleration: {e}")
                return False
        return True
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current GPU memory usage if available"""
        if not self.gpu_available:
            return {"available": False, "reason": "No GPU available"}
        
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                memory_data = result.stdout.strip().split(', ')
                if len(memory_data) >= 2:
                    used_mb = int(memory_data[0].strip())
                    total_mb = int(memory_data[1].strip())
                    
                    return {
                        "available": True,
                        "used_mb": used_mb,
                        "total_mb": total_mb,
                        "free_mb": total_mb - used_mb,
                        "utilization_percent": round((used_mb / total_mb) * 100, 1)
                    }
            
            return {"available": False, "reason": "Failed to query GPU memory"}
            
        except Exception as e:
            return {"available": False, "reason": f"Error querying GPU memory: {e}"}
    
    def is_gpu_available(self) -> bool:
        """Check if GPU is available for acceleration"""
        return self.gpu_available
    
    def is_gpu_enabled(self) -> bool:
        """Check if GPU acceleration is currently enabled"""
        return self.cugraph_backend


# Global instance for easy access
gpu_manager = GPUAccelerationManager() 