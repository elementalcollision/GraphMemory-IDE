"""
DigitalOcean Kubernetes (DOKS) Monitoring Integration for GraphMemory-IDE
Production deployment observability with infrastructure monitoring and alerting
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os

import httpx
from prometheus_client.parser import text_string_to_metric_families

logger = logging.getLogger(__name__)

@dataclass
class DOKSClusterInfo:
    """DigitalOcean Kubernetes cluster information."""
    cluster_id: str
    cluster_name: str
    region: str
    node_count: int
    status: str
    version: str
    endpoint: str
    created_at: datetime

@dataclass
class DONodeMetrics:
    """DigitalOcean node metrics."""
    node_id: str
    node_name: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_in: float
    network_out: float
    status: str
    timestamp: datetime

@dataclass
class DOLoadBalancerMetrics:
    """DigitalOcean Load Balancer metrics."""
    lb_id: str
    lb_name: str
    status: str
    connections_per_second: int
    active_connections: int
    bytes_in: int
    bytes_out: int
    health_check_status: str
    timestamp: datetime

class DigitalOceanMonitoringClient:
    """
    DigitalOcean API client for infrastructure monitoring.
    
    Provides comprehensive monitoring of DOKS clusters, droplets,
    load balancers, and networking components.
    """
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.digitalocean.com/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        # Cache for cluster information
        self.cluster_cache: Dict[str, DOKSClusterInfo] = {}
        self.last_cluster_refresh = datetime.min
        
        # Metrics history
        self.node_metrics_history: List[DONodeMetrics] = []
        self.lb_metrics_history: List[DOLoadBalancerMetrics] = []
    
    async def get_kubernetes_clusters(self) -> List[DOKSClusterInfo]:
        """Get all Kubernetes clusters."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/kubernetes/clusters",
                headers=self.headers
            )
            response.raise_for_status()
            
            clusters_data = response.json()
            clusters = []
            
            for cluster_data in clusters_data.get('kubernetes_clusters', []):
                cluster = DOKSClusterInfo(
                    cluster_id=cluster_data['id'],
                    cluster_name=cluster_data['name'],
                    region=cluster_data['region']['name'],
                    node_count=len(cluster_data.get('node_pools', [{}])[0].get('nodes', [])),
                    status=cluster_data['status']['state'],
                    version=cluster_data['version'],
                    endpoint=cluster_data['endpoint'],
                    created_at=datetime.fromisoformat(cluster_data['created_at'].replace('Z', '+00:00'))
                )
                clusters.append(cluster)
                self.cluster_cache[cluster.cluster_id] = cluster
            
            self.last_cluster_refresh = datetime.now()
            return clusters
    
    async def get_cluster_metrics(self, cluster_id: str) -> Dict[str, Any]:
        """Get detailed metrics for a specific cluster."""
        async with httpx.AsyncClient() as client:
            # Get cluster details
            cluster_response = await client.get(
                f"{self.base_url}/kubernetes/clusters/{cluster_id}",
                headers=self.headers
            )
            cluster_response.raise_for_status()
            cluster_data = cluster_response.json()['kubernetes_cluster']
            
            # Get node pool metrics
            node_pools = cluster_data.get('node_pools', [])
            node_metrics = []
            
            for pool in node_pools:
                for node in pool.get('nodes', []):
                    # DigitalOcean doesn't provide real-time node metrics via API
                    # In production, this would integrate with their monitoring API
                    node_metric = DONodeMetrics(
                        node_id=node['id'],
                        node_name=node['name'],
                        cpu_usage=0.0,  # Would be populated from monitoring API
                        memory_usage=0.0,
                        disk_usage=0.0,
                        network_in=0.0,
                        network_out=0.0,
                        status=node['status']['state'],
                        timestamp=datetime.now()
                    )
                    node_metrics.append(node_metric)
            
            return {
                'cluster_id': cluster_id,
                'cluster_status': cluster_data['status']['state'],
                'node_count': len([node for pool in node_pools for node in pool.get('nodes', [])]),
                'node_metrics': node_metrics,
                'last_updated': datetime.now()
            }
    
    async def get_load_balancer_metrics(self) -> List[DOLoadBalancerMetrics]:
        """Get Load Balancer metrics."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/load_balancers",
                headers=self.headers
            )
            response.raise_for_status()
            
            lb_data = response.json()
            lb_metrics = []
            
            for lb in lb_data.get('load_balancers', []):
                # Get health check status
                health_status = "healthy"
                if lb.get('health_check'):
                    health_status = "configured"
                
                metric = DOLoadBalancerMetrics(
                    lb_id=lb['id'],
                    lb_name=lb['name'],
                    status=lb['status'],
                    connections_per_second=0,  # Would be from monitoring API
                    active_connections=0,
                    bytes_in=0,
                    bytes_out=0,
                    health_check_status=health_status,
                    timestamp=datetime.now()
                )
                lb_metrics.append(metric)
            
            self.lb_metrics_history.extend(lb_metrics)
            
            # Keep history bounded
            if len(self.lb_metrics_history) > 10000:
                self.lb_metrics_history = self.lb_metrics_history[-5000:]
            
            return lb_metrics
    
    async def get_droplet_metrics(self, droplet_ids: List[str]) -> Dict[str, Any]:
        """Get metrics for specific droplets."""
        metrics = {}
        
        async with httpx.AsyncClient() as client:
            for droplet_id in droplet_ids:
                response = await client.get(
                    f"{self.base_url}/droplets/{droplet_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    droplet_data = response.json()['droplet']
                    metrics[droplet_id] = {
                        'name': droplet_data['name'],
                        'status': droplet_data['status'],
                        'region': droplet_data['region']['name'],
                        'size': droplet_data['size']['slug'],
                        'vcpus': droplet_data['vcpus'],
                        'memory': droplet_data['memory'],
                        'disk': droplet_data['disk'],
                        'created_at': droplet_data['created_at']
                    }
        
        return metrics

class DOKSObservabilityEngine:
    """
    DigitalOcean Kubernetes Observability Engine.
    
    Integrates DOKS infrastructure monitoring with application observability
    for comprehensive production monitoring.
    """
    
    def __init__(self, api_token: str, cluster_id: str):
        self.do_client = DigitalOceanMonitoringClient(api_token)
        self.cluster_id = cluster_id
        
        # GraphMemory-specific monitoring
        self.graphmemory_namespaces = ['default', 'graphmemory', 'monitoring']
        self.critical_services = ['graphmemory-api', 'graphmemory-vector-db', 'redis']
        
        # Monitoring intervals
        self.cluster_check_interval = 300  # 5 minutes
        self.infrastructure_check_interval = 60  # 1 minute
        
        # Alert thresholds
        self.node_cpu_threshold = 80.0
        self.node_memory_threshold = 85.0
        self.disk_usage_threshold = 90.0
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self) -> None:
        """Start continuous infrastructure monitoring."""
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started DOKS monitoring for cluster {self.cluster_id}")
    
    async def stop_monitoring(self) -> None:
        """Stop infrastructure monitoring."""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped DOKS monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Check cluster health
                await self._check_cluster_health()
                
                # Check infrastructure metrics
                await self._check_infrastructure_metrics()
                
                # Check load balancer health
                await self._check_load_balancer_health()
                
                # Check critical services
                await self._check_critical_services()
                
                await asyncio.sleep(self.infrastructure_check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Brief pause before retry
    
    async def _check_cluster_health(self) -> None:
        """Check overall cluster health."""
        try:
            cluster_metrics = await self.do_client.get_cluster_metrics(self.cluster_id)
            
            # Check cluster status
            if cluster_metrics['cluster_status'] != 'running':
                await self._send_cluster_alert(
                    'critical',
                    f"Cluster {self.cluster_id} status: {cluster_metrics['cluster_status']}"
                )
            
            # Check node count
            expected_nodes = 3  # Minimum for production
            actual_nodes = cluster_metrics['node_count']
            
            if actual_nodes < expected_nodes:
                await self._send_cluster_alert(
                    'high',
                    f"Node count below expected: {actual_nodes}/{expected_nodes}"
                )
            
            # Check individual node health
            for node_metric in cluster_metrics['node_metrics']:
                if node_metric.status != 'active':
                    await self._send_node_alert(
                        'high',
                        f"Node {node_metric.node_name} status: {node_metric.status}"
                    )
            
        except Exception as e:
            logger.error(f"Failed to check cluster health: {e}")
    
    async def _check_infrastructure_metrics(self) -> None:
        """Check infrastructure-level metrics."""
        try:
            # This would integrate with DigitalOcean's monitoring API
            # For now, we'll simulate basic infrastructure checks
            
            # Check network connectivity
            network_health = await self._check_network_health()
            if not network_health:
                await self._send_infrastructure_alert(
                    'medium',
                    "Network connectivity issues detected"
                )
            
            # Check DNS resolution
            dns_health = await self._check_dns_health()
            if not dns_health:
                await self._send_infrastructure_alert(
                    'medium',
                    "DNS resolution issues detected"
                )
            
        except Exception as e:
            logger.error(f"Failed to check infrastructure metrics: {e}")
    
    async def _check_load_balancer_health(self) -> None:
        """Check load balancer health and performance."""
        try:
            lb_metrics = await self.do_client.get_load_balancer_metrics()
            
            for lb in lb_metrics:
                if lb.status != 'active':
                    await self._send_lb_alert(
                        'critical',
                        f"Load Balancer {lb.lb_name} status: {lb.status}"
                    )
                
                if lb.health_check_status != 'healthy' and lb.health_check_status != 'configured':
                    await self._send_lb_alert(
                        'high',
                        f"Load Balancer {lb.lb_name} health check failing"
                    )
            
        except Exception as e:
            logger.error(f"Failed to check load balancer health: {e}")
    
    async def _check_critical_services(self) -> None:
        """Check GraphMemory critical services availability."""
        try:
            # This would use kubectl or Kubernetes API to check service health
            # For now, we'll simulate service health checks
            
            for service in self.critical_services:
                service_health = await self._check_service_health(service)
                if not service_health:
                    await self._send_service_alert(
                        'critical',
                        f"Critical service {service} is unhealthy"
                    )
            
        except Exception as e:
            logger.error(f"Failed to check critical services: {e}")
    
    async def _check_network_health(self) -> bool:
        """Check network connectivity."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.digitalocean.com/v2", timeout=10.0)
                return response.status_code == 200
        except:
            return False
    
    async def _check_dns_health(self) -> bool:
        """Check DNS resolution."""
        import socket
        try:
            socket.gethostbyname('api.digitalocean.com')
            return True
        except socket.gaierror:
            return False
    
    async def _check_service_health(self, service_name: str) -> bool:
        """Check individual service health."""
        # This would implement actual Kubernetes service health checks
        # For now, return True as placeholder
        return True
    
    async def _send_cluster_alert(self, severity: str, message: str) -> None:
        """Send cluster-level alert."""
        alert = {
            'type': 'cluster_alert',
            'severity': severity,
            'message': message,
            'cluster_id': self.cluster_id,
            'timestamp': datetime.now().isoformat(),
            'source': 'doks_monitoring'
        }
        
        logger.warning(f"CLUSTER ALERT ({severity}): {message}")
        # In production, this would integrate with alerting system
    
    async def _send_node_alert(self, severity: str, message: str) -> None:
        """Send node-level alert."""
        alert = {
            'type': 'node_alert',
            'severity': severity,
            'message': message,
            'cluster_id': self.cluster_id,
            'timestamp': datetime.now().isoformat(),
            'source': 'doks_monitoring'
        }
        
        logger.warning(f"NODE ALERT ({severity}): {message}")
    
    async def _send_infrastructure_alert(self, severity: str, message: str) -> None:
        """Send infrastructure-level alert."""
        alert = {
            'type': 'infrastructure_alert',
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'source': 'doks_monitoring'
        }
        
        logger.warning(f"INFRASTRUCTURE ALERT ({severity}): {message}")
    
    async def _send_lb_alert(self, severity: str, message: str) -> None:
        """Send load balancer alert."""
        alert = {
            'type': 'load_balancer_alert',
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'source': 'doks_monitoring'
        }
        
        logger.warning(f"LOAD BALANCER ALERT ({severity}): {message}")
    
    async def _send_service_alert(self, severity: str, message: str) -> None:
        """Send service-level alert."""
        alert = {
            'type': 'service_alert',
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'source': 'doks_monitoring'
        }
        
        logger.warning(f"SERVICE ALERT ({severity}): {message}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring system statistics."""
        return {
            'monitoring_enabled': self.is_monitoring,
            'cluster_id': self.cluster_id,
            'monitored_namespaces': self.graphmemory_namespaces,
            'critical_services': self.critical_services,
            'check_intervals': {
                'cluster': self.cluster_check_interval,
                'infrastructure': self.infrastructure_check_interval
            },
            'alert_thresholds': {
                'node_cpu': self.node_cpu_threshold,
                'node_memory': self.node_memory_threshold,
                'disk_usage': self.disk_usage_threshold
            },
            'last_cluster_refresh': self.last_cluster_refresh.isoformat() if self.last_cluster_refresh != datetime.min else None
        }

class DOKSIntegrationManager:
    """
    DigitalOcean Kubernetes Integration Manager.
    
    Coordinates between infrastructure monitoring, application observability,
    and incident management for production deployments.
    """
    
    def __init__(self, api_token: str, cluster_id: str):
        self.observability_engine = DOKSObservabilityEngine(api_token, cluster_id)
        self.integration_health = {
            'api_connectivity': False,
            'cluster_access': False,
            'monitoring_active': False,
            'last_health_check': datetime.min
        }
    
    async def initialize(self) -> bool:
        """Initialize DOKS integration."""
        try:
            # Test API connectivity
            clusters = await self.observability_engine.do_client.get_kubernetes_clusters()
            self.integration_health['api_connectivity'] = True
            
            # Verify cluster access
            target_cluster = next(
                (c for c in clusters if c.cluster_id == self.observability_engine.cluster_id),
                None
            )
            
            if target_cluster:
                self.integration_health['cluster_access'] = True
                logger.info(f"Connected to DOKS cluster: {target_cluster.cluster_name}")
            else:
                logger.error(f"Cluster {self.observability_engine.cluster_id} not found")
                return False
            
            # Start monitoring
            await self.observability_engine.start_monitoring()
            self.integration_health['monitoring_active'] = True
            self.integration_health['last_health_check'] = datetime.now()
            
            logger.info("DOKS integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize DOKS integration: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Update health status
            self.integration_health['last_health_check'] = datetime.now()
            
            # Check API connectivity
            try:
                await self.observability_engine.do_client.get_kubernetes_clusters()
                self.integration_health['api_connectivity'] = True
            except:
                self.integration_health['api_connectivity'] = False
            
            # Check monitoring status
            self.integration_health['monitoring_active'] = self.observability_engine.is_monitoring
            
            return {
                'status': 'healthy' if all([
                    self.integration_health['api_connectivity'],
                    self.integration_health['cluster_access'],
                    self.integration_health['monitoring_active']
                ]) else 'degraded',
                'details': self.integration_health,
                'monitoring_stats': self.observability_engine.get_monitoring_stats()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': self.integration_health
            }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown DOKS integration."""
        await self.observability_engine.stop_monitoring()
        logger.info("DOKS integration shutdown complete")

# Global DOKS integration
_doks_integration = None

def get_doks_integration() -> Optional[DOKSIntegrationManager]:
    """Get global DOKS integration instance."""
    return _doks_integration

async def initialize_doks_monitoring(api_token: str, cluster_id: str) -> DOKSIntegrationManager:
    """Initialize DigitalOcean Kubernetes monitoring."""
    global _doks_integration
    
    _doks_integration = DOKSIntegrationManager(api_token, cluster_id)
    
    success = await _doks_integration.initialize()
    if not success:
        logger.error("Failed to initialize DOKS monitoring")
        _doks_integration = None
        raise RuntimeError("DOKS monitoring initialization failed")
    
    logger.info("DigitalOcean Kubernetes monitoring initialized successfully")
    return _doks_integration 