"""
Hybrid Monitoring Dashboard
Comprehensive dashboard for CPython/Condon hybrid architecture monitoring
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..condon_monitor import get_condon_monitor
from ..cpython_monitor import get_cpython_monitor
from ..hybrid_monitoring_framework import get_hybrid_monitoring

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    """Dashboard metrics data structure"""

    timestamp: datetime
    system_metrics: Dict[str, Any]
    cpython_metrics: Dict[str, Any]
    condon_metrics: Dict[str, Any]
    hybrid_metrics: Dict[str, Any]
    alerts: List[Dict[str, Any]]


class HybridDashboard:
    """
    Comprehensive dashboard for hybrid monitoring

    Features:
    - Real-time metrics visualization
    - Service boundary monitoring
    - Performance analytics
    - Alert management
    - Historical data analysis
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = FastAPI(title="Hybrid Monitoring Dashboard")
        self.hybrid_monitoring = get_hybrid_monitoring()

        # Dashboard state
        self.metrics_history: List[DashboardMetrics] = []
        self.active_alerts: List[Dict[str, Any]] = []
        self.websocket_connections: List[WebSocket] = []

        # Setup routes
        self._setup_routes()

        # Background tasks
        self._metrics_collection_thread = None
        self._alert_monitoring_thread = None

        logger.info(f"Initialized Hybrid Dashboard on {host}:{port}")

    def _setup_routes(self):
        """Setup FastAPI routes"""

        @self.app.get("/")
        async def dashboard_home():
            """Dashboard home page"""
            return HTMLResponse(self._get_dashboard_html())

        @self.app.get("/metrics")
        async def get_metrics():
            """Get current metrics"""
            return self._get_current_metrics()

        @self.app.get("/metrics/history")
        async def get_metrics_history():
            """Get metrics history"""
            return self._get_metrics_history()

        @self.app.get("/alerts")
        async def get_alerts():
            """Get active alerts"""
            return {"alerts": self.active_alerts}

        @self.app.get("/services")
        async def get_services():
            """Get service information"""
            return self._get_service_info()

        @self.app.get("/performance")
        async def get_performance():
            """Get performance summary"""
            return self._get_performance_summary()

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)

            try:
                while True:
                    # Send periodic updates
                    await websocket.send_text(json.dumps(self._get_current_metrics()))
                    await asyncio.sleep(5)
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    def _get_dashboard_html(self) -> str:
        """Get dashboard HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hybrid Monitoring Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                .metric-card { 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    border-radius: 5px;
                    background: #f9f9f9;
                }
                .alert { 
                    background: #ffebee; 
                    color: #c62828; 
                    padding: 10px; 
                    margin: 10px 0;
                    border-radius: 5px;
                }
                .metric-value { 
                    font-size: 24px; 
                    font-weight: bold; 
                    color: #2196f3;
                }
                .metric-label { 
                    color: #666; 
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <h1>Hybrid Monitoring Dashboard</h1>
            
            <div class="dashboard">
                <div class="metric-card">
                    <h3>System Metrics</h3>
                    <div id="system-metrics"></div>
                </div>
                
                <div class="metric-card">
                    <h3>CPython Services</h3>
                    <div id="cpython-metrics"></div>
                </div>
                
                <div class="metric-card">
                    <h3>Condon Services</h3>
                    <div id="condon-metrics"></div>
                </div>
                
                <div class="metric-card">
                    <h3>Hybrid Metrics</h3>
                    <div id="hybrid-metrics"></div>
                </div>
            </div>
            
            <div class="metric-card">
                <h3>Active Alerts</h3>
                <div id="alerts"></div>
            </div>
            
            <script>
                // Real-time updates via WebSocket
                const ws = new WebSocket('ws://localhost:8080/ws');
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                };
                
                function updateDashboard(data) {
                    // Update system metrics
                    document.getElementById('system-metrics').innerHTML = 
                        `<div class="metric-value">${data.system.cpu_usage}%</div>
                         <div class="metric-label">CPU Usage</div>
                         <div class="metric-value">${data.system.memory_usage} MB</div>
                         <div class="metric-label">Memory Usage</div>`;
                    
                    // Update service metrics
                    document.getElementById('cpython-metrics').innerHTML = 
                        `<div class="metric-value">${data.cpython.services}</div>
                         <div class="metric-label">Active Services</div>`;
                    
                    document.getElementById('condon-metrics').innerHTML = 
                        `<div class="metric-value">${data.condon.services}</div>
                         <div class="metric-label">Active Services</div>`;
                    
                    // Update alerts
                    const alertsHtml = data.alerts.map(alert => 
                        `<div class="alert">${alert.message}</div>`
                    ).join('');
                    document.getElementById('alerts').innerHTML = alertsHtml;
                }
                
                // Initial load
                fetch('/metrics')
                    .then(response => response.json())
                    .then(data => updateDashboard(data));
            </script>
        </body>
        </html>
        """

    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        try:
            # Get hybrid monitoring metrics
            hybrid_summary = self.hybrid_monitoring.get_metrics_summary()

            # Get CPython metrics
            cpython_monitor = get_cpython_monitor()
            cpython_summary = cpython_monitor.get_service_summary()

            # Get Condon metrics
            condon_monitor = get_condon_monitor()
            condon_summary = condon_monitor.get_service_summary()

            return {
                "timestamp": datetime.now().isoformat(),
                "system": hybrid_summary.get("system", {}),
                "cpython": {
                    "services": len(self.hybrid_monitoring.cpython_services),
                    "performance": cpython_summary.get("performance", {}),
                    "gil_stats": cpython_summary.get("gil_stats", {}),
                },
                "condon": {
                    "services": len(self.hybrid_monitoring.condon_services),
                    "performance": condon_summary.get("performance", {}),
                    "compilation": condon_summary.get("performance", {}).get(
                        "compilation", {}
                    ),
                },
                "hybrid": {
                    "services": len(self.hybrid_monitoring.hybrid_services),
                    "boundary_calls": hybrid_summary.get("boundary_calls", 0),
                    "data_transfer": hybrid_summary.get("data_transfer", 0),
                },
                "alerts": self.active_alerts,
            }
        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {"error": str(e)}

    def _get_metrics_history(self) -> List[Dict[str, Any]]:
        """Get metrics history"""
        return [asdict(metrics) for metrics in self.metrics_history[-100:]]

    def _get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            "cpython_services": list(self.hybrid_monitoring.cpython_services.keys()),
            "condon_services": list(self.hybrid_monitoring.condon_services.keys()),
            "hybrid_services": list(self.hybrid_monitoring.hybrid_services.keys()),
            "total_services": (
                len(self.hybrid_monitoring.cpython_services)
                + len(self.hybrid_monitoring.condon_services)
                + len(self.hybrid_monitoring.hybrid_services)
            ),
        }

    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        try:
            cpython_monitor = get_cpython_monitor()
            condon_monitor = get_condon_monitor()

            return {
                "cpython": cpython_monitor.get_service_summary(),
                "condon": condon_monitor.get_service_summary(),
                "hybrid": self.hybrid_monitoring.get_metrics_summary(),
            }
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}

    def start_metrics_collection(self):
        """Start background metrics collection"""

        def collect_metrics():
            while True:
                try:
                    metrics = DashboardMetrics(
                        timestamp=datetime.now(),
                        system_metrics=self.hybrid_monitoring.get_metrics_summary(),
                        cpython_metrics=get_cpython_monitor().get_service_summary(),
                        condon_metrics=get_condon_monitor().get_service_summary(),
                        hybrid_metrics=self.hybrid_monitoring.get_metrics_summary(),
                        alerts=self.active_alerts,
                    )

                    self.metrics_history.append(metrics)

                    # Keep only last 1000 entries
                    if len(self.metrics_history) > 1000:
                        self.metrics_history = self.metrics_history[-1000:]

                    # Send updates to WebSocket connections
                    self._broadcast_metrics(metrics)

                    time.sleep(5)  # Collect every 5 seconds

                except Exception as e:
                    logger.error(f"Error in metrics collection: {e}")
                    time.sleep(10)

        self._metrics_collection_thread = threading.Thread(
            target=collect_metrics, daemon=True
        )
        self._metrics_collection_thread.start()
        logger.info("Started metrics collection")

    def start_alert_monitoring(self):
        """Start alert monitoring"""

        def monitor_alerts():
            while True:
                try:
                    # Check for new alerts
                    self._check_alerts()

                    # Clean up old alerts
                    self._cleanup_alerts()

                    time.sleep(30)  # Check every 30 seconds

                except Exception as e:
                    logger.error(f"Error in alert monitoring: {e}")
                    time.sleep(60)

        self._alert_monitoring_thread = threading.Thread(
            target=monitor_alerts, daemon=True
        )
        self._alert_monitoring_thread.start()
        logger.info("Started alert monitoring")

    def _check_alerts(self):
        """Check for new alerts"""
        try:
            # Check system metrics
            system_metrics = self.hybrid_monitoring.get_metrics_summary()

            # CPU usage alert
            cpu_usage = system_metrics.get("system", {}).get("cpu_usage")
            if cpu_usage and cpu_usage > 80:
                self._add_alert("high_cpu", f"High CPU usage: {cpu_usage}%")

            # Memory usage alert
            memory_usage = system_metrics.get("system", {}).get("memory_usage")
            if memory_usage:
                memory_percent = (memory_usage / (1024 * 1024 * 1024)) * 100
                if memory_percent > 85:
                    self._add_alert(
                        "high_memory", f"High memory usage: {memory_percent:.1f}%"
                    )

            # Service-specific alerts
            for (
                service_name,
                service,
            ) in self.hybrid_monitoring.cpython_services.items():
                error_count = service.metrics.get("error_count")
                if error_count and error_count._value.get() > 10:
                    self._add_alert(
                        "service_errors", f"High error rate in {service_name}"
                    )

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

    def _add_alert(self, alert_type: str, message: str):
        """Add a new alert"""
        alert = {
            "id": f"{alert_type}_{int(time.time())}",
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "severity": "warning",
        }

        # Check if alert already exists
        existing_alert = next(
            (a for a in self.active_alerts if a["type"] == alert_type), None
        )

        if not existing_alert:
            self.active_alerts.append(alert)
            logger.warning(f"New alert: {message}")

    def _cleanup_alerts(self):
        """Clean up old alerts"""
        current_time = datetime.now()
        self.active_alerts = [
            alert
            for alert in self.active_alerts
            if (current_time - datetime.fromisoformat(alert["timestamp"]))
            < timedelta(hours=1)
        ]

    def _broadcast_metrics(self, metrics: DashboardMetrics):
        """Broadcast metrics to WebSocket connections"""
        try:
            message = json.dumps(asdict(metrics))
            for websocket in self.websocket_connections[
                :
            ]:  # Copy list to avoid modification during iteration
                try:
                    asyncio.create_task(websocket.send_text(message))
                except Exception as e:
                    logger.error(f"Error sending to WebSocket: {e}")
                    self.websocket_connections.remove(websocket)
        except Exception as e:
            logger.error(f"Error broadcasting metrics: {e}")

    def start(self):
        """Start the dashboard"""
        # Start background tasks
        self.start_metrics_collection()
        self.start_alert_monitoring()

        # Start the server
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    def stop(self):
        """Stop the dashboard"""
        logger.info("Stopping Hybrid Dashboard")

        # Stop background threads
        if self._metrics_collection_thread:
            self._metrics_collection_thread.join(timeout=5)

        if self._alert_monitoring_thread:
            self._alert_monitoring_thread.join(timeout=5)


# Global dashboard instance
_dashboard = None


def get_dashboard() -> HybridDashboard:
    """Get dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = HybridDashboard()
    return _dashboard


def start_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Start the hybrid monitoring dashboard"""
    dashboard = HybridDashboard(host=host, port=port)
    dashboard.start()


if __name__ == "__main__":
    start_dashboard()
