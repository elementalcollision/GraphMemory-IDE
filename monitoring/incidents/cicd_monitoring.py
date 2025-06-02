"""
CI/CD Observability Pipeline for GraphMemory-IDE
Comprehensive monitoring of development workflows, deployments, and pipeline health
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import subprocess
import os

import httpx

logger = logging.getLogger(__name__)

class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

class DeploymentStage(Enum):
    """Deployment pipeline stages."""
    BUILD = "build"
    TEST = "test"
    SECURITY_SCAN = "security_scan"
    DEPLOY_STAGING = "deploy_staging"
    INTEGRATION_TEST = "integration_test"
    DEPLOY_PRODUCTION = "deploy_production"
    SMOKE_TEST = "smoke_test"

@dataclass
class PipelineExecution:
    """CI/CD pipeline execution record."""
    execution_id: str
    pipeline_name: str
    branch: str
    commit_sha: str
    trigger: str  # push, pull_request, schedule, manual
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    stages: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

@dataclass
class DeploymentRecord:
    """Deployment execution record."""
    deployment_id: str
    environment: str  # staging, production
    version: str
    commit_sha: str
    deployed_by: str
    deployment_status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    rollback_available: bool = True
    health_check_status: str = "pending"

@dataclass
class QualityMetrics:
    """Code quality and testing metrics."""
    test_coverage: float
    test_count: int
    test_pass_rate: float
    code_quality_score: float
    security_vulnerabilities: int
    performance_benchmarks: Dict[str, float] = field(default_factory=dict)

class GitHubActionsMonitor:
    """
    GitHub Actions workflow monitoring.
    
    Monitors CI/CD pipelines, deployments, and provides
    comprehensive observability for development workflows.
    """
    
    def __init__(self, github_token: str, repo_owner: str, repo_name: str) -> None:
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Pipeline monitoring state
        self.pipeline_executions: List[PipelineExecution] = []
        self.deployment_records: List[DeploymentRecord] = []
        self.quality_history: List[QualityMetrics] = []
        
        # Monitoring configuration
        self.monitored_workflows = [
            "build-and-test.yml",
            "security-scan.yml", 
            "deploy-staging.yml",
            "deploy-production.yml"
        ]
        
        # Performance baselines
        self.performance_baselines = {
            "build_time": 300,  # 5 minutes
            "test_time": 600,   # 10 minutes
            "deploy_time": 180, # 3 minutes
            "total_pipeline_time": 1200  # 20 minutes
        }
    
    async def get_workflow_runs(self, workflow_file: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent workflow runs for a specific workflow."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/workflows/{workflow_file}/runs",
                headers=self.headers,
                params={"per_page": limit}
            )
            response.raise_for_status()
            
            return response.json().get("workflow_runs", [])
    
    async def get_workflow_run_details(self, run_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific workflow run."""
        async with httpx.AsyncClient() as client:
            # Get run details
            run_response = await client.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}",
                headers=self.headers
            )
            run_response.raise_for_status()
            run_data = run_response.json()
            
            # Get job details
            jobs_response = await client.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/jobs",
                headers=self.headers
            )
            jobs_response.raise_for_status()
            jobs_data = jobs_response.json()
            
            return {
                "run": run_data,
                "jobs": jobs_data.get("jobs", [])
            }
    
    async def monitor_pipeline_performance(self) -> Dict[str, Any]:
        """Monitor overall pipeline performance metrics."""
        performance_metrics = {
            "total_runs_24h": 0,
            "success_rate_24h": 0.0,
            "average_duration": 0.0,
            "performance_degradation": [],
            "failure_patterns": [],
            "deployment_frequency": 0.0
        }
        
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        recent_executions = [
            exec for exec in self.pipeline_executions 
            if exec.started_at >= twenty_four_hours_ago
        ]
        
        if recent_executions:
            performance_metrics["total_runs_24h"] = len(recent_executions)
            
            successful_runs = [
                exec for exec in recent_executions 
                if exec.status == PipelineStatus.SUCCESS
            ]
            
            performance_metrics["success_rate_24h"] = len(successful_runs) / len(recent_executions)
            
            completed_runs = [
                exec for exec in recent_executions
                if exec.duration_seconds is not None
            ]
            
            if completed_runs:
                performance_metrics["average_duration"] = sum(
                    exec.duration_seconds for exec in completed_runs
                ) / len(completed_runs)
            
            # Check for performance degradation
            for exec in recent_executions:
                if exec.duration_seconds and exec.pipeline_name in self.performance_baselines:
                    baseline = self.performance_baselines.get(exec.pipeline_name.replace(".yml", "_time"), 600)
                    if exec.duration_seconds > baseline * 1.5:  # 50% slower than baseline
                        performance_metrics["performance_degradation"].append({
                            "execution_id": exec.execution_id,
                            "pipeline": exec.pipeline_name,
                            "duration": exec.duration_seconds,
                            "baseline": baseline,
                            "degradation_percent": ((exec.duration_seconds - baseline) / baseline) * 100
                        })
            
            # Analyze failure patterns
            failed_runs = [
                exec for exec in recent_executions
                if exec.status == PipelineStatus.FAILED
            ]
            
            failure_patterns = {}
            for run in failed_runs:
                key = f"{run.pipeline_name}:{run.branch}"
                failure_patterns[key] = failure_patterns.get(key, 0) + 1
            
            performance_metrics["failure_patterns"] = [
                {"pattern": pattern, "count": count}
                for pattern, count in failure_patterns.items()
                if count >= 2  # Only show patterns with 2+ failures
            ]
        
        # Calculate deployment frequency
        recent_deployments = [
            deploy for deploy in self.deployment_records
            if deploy.started_at >= twenty_four_hours_ago and 
               deploy.deployment_status == PipelineStatus.SUCCESS
        ]
        performance_metrics["deployment_frequency"] = len(recent_deployments)
        
        return performance_metrics
    
    async def check_pipeline_health(self) -> Dict[str, Any]:
        """Comprehensive pipeline health check."""
        health_status = {
            "overall_status": "healthy",
            "workflow_status": {},
            "alerts": [],
            "recommendations": []
        }
        
        # Check each monitored workflow
        for workflow in self.monitored_workflows:
            try:
                recent_runs = await self.get_workflow_runs(workflow, 10)
                
                if not recent_runs:
                    health_status["workflow_status"][workflow] = "no_data"
                    health_status["alerts"].append(f"No recent runs for {workflow}")
                    continue
                
                # Check recent failure rate
                failed_runs = [run for run in recent_runs if run["conclusion"] == "failure"]
                failure_rate = len(failed_runs) / len(recent_runs)
                
                if failure_rate > 0.3:  # More than 30% failure rate
                    health_status["workflow_status"][workflow] = "unhealthy"
                    health_status["alerts"].append(f"High failure rate for {workflow}: {failure_rate:.1%}")
                elif failure_rate > 0.1:  # More than 10% failure rate
                    health_status["workflow_status"][workflow] = "degraded"
                    health_status["alerts"].append(f"Elevated failure rate for {workflow}: {failure_rate:.1%}")
                else:
                    health_status["workflow_status"][workflow] = "healthy"
                
                # Check for stuck workflows
                running_runs = [run for run in recent_runs if run["status"] == "in_progress"]
                for run in running_runs:
                    started_at = datetime.fromisoformat(run["created_at"].replace('Z', '+00:00'))
                    if datetime.now() - started_at > timedelta(hours=2):
                        health_status["alerts"].append(f"Workflow {workflow} run {run['id']} stuck for > 2 hours")
                
            except Exception as e:
                health_status["workflow_status"][workflow] = "error"
                health_status["alerts"].append(f"Error checking {workflow}: {str(e)}")
        
        # Determine overall status
        if any(status == "unhealthy" for status in health_status["workflow_status"].values()):
            health_status["overall_status"] = "unhealthy"
        elif any(status in ["degraded", "error"] for status in health_status["workflow_status"].values()):
            health_status["overall_status"] = "degraded"
        
        # Generate recommendations
        if health_status["alerts"]:
            if len([alert for alert in health_status["alerts"] if "failure rate" in alert]) >= 2:
                health_status["recommendations"].append("Review recent code changes for quality issues")
            
            if any("stuck" in alert for alert in health_status["alerts"]):
                health_status["recommendations"].append("Check GitHub Actions runner capacity and queue times")
        
        return health_status
    
    async def analyze_deployment_patterns(self) -> Dict[str, Any]:
        """Analyze deployment patterns and trends."""
        analysis = {
            "deployment_frequency": {},
            "environment_health": {},
            "rollback_frequency": 0.0,
            "deployment_success_rate": {},
            "time_to_production": []
        }
        
        # Analyze by environment
        for env in ["staging", "production"]:
            env_deployments = [
                deploy for deploy in self.deployment_records
                if deploy.environment == env
            ]
            
            if env_deployments:
                successful_deployments = [
                    deploy for deploy in env_deployments
                    if deploy.deployment_status == PipelineStatus.SUCCESS
                ]
                
                analysis["deployment_success_rate"][env] = (
                    len(successful_deployments) / len(env_deployments)
                )
                
                # Calculate deployment frequency (per week)
                one_week_ago = datetime.now() - timedelta(weeks=1)
                recent_deployments = [
                    deploy for deploy in env_deployments
                    if deploy.started_at >= one_week_ago
                ]
                analysis["deployment_frequency"][env] = len(recent_deployments)
                
                # Check environment health
                recent_failures = [
                    deploy for deploy in recent_deployments
                    if deploy.deployment_status == PipelineStatus.FAILED
                ]
                
                if len(recent_failures) > 2:
                    analysis["environment_health"][env] = "unhealthy"
                elif len(recent_failures) > 0:
                    analysis["environment_health"][env] = "degraded"
                else:
                    analysis["environment_health"][env] = "healthy"
        
        # Calculate rollback frequency
        total_deployments = len(self.deployment_records)
        rollbacks = len([deploy for deploy in self.deployment_records if "rollback" in deploy.deployment_id.lower()])
        
        if total_deployments > 0:
            analysis["rollback_frequency"] = rollbacks / total_deployments
        
        return analysis

class CICDObservabilityEngine:
    """
    Comprehensive CI/CD observability engine.
    
    Orchestrates monitoring of multiple CI/CD platforms and provides
    unified observability for the entire development lifecycle.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.github_monitor = None
        
        # Initialize platform monitors
        if "github" in config:
            self.github_monitor = GitHubActionsMonitor(
                config["github"]["token"],
                config["github"]["repo_owner"],
                config["github"]["repo_name"]
            )
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.check_interval = 300  # 5 minutes
        
        # Alert thresholds
        self.alert_thresholds = {
            "failure_rate": 0.2,        # 20%
            "pipeline_duration": 1800,   # 30 minutes
            "deployment_frequency": 1,   # At least 1 per day
            "rollback_rate": 0.1        # 10%
        }
    
    async def start_monitoring(self) -> None:
        """Start continuous CI/CD monitoring."""
        if self.is_monitoring:
            logger.warning("CI/CD monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started CI/CD observability monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop CI/CD monitoring."""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped CI/CD monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Check pipeline health
                if self.github_monitor:
                    health_status = await self.github_monitor.check_pipeline_health()
                    await self._process_health_alerts(health_status)
                
                # Monitor performance metrics
                if self.github_monitor:
                    performance_metrics = await self.github_monitor.monitor_pipeline_performance()
                    await self._process_performance_alerts(performance_metrics)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in CI/CD monitoring loop: {e}")
                await asyncio.sleep(60)  # Brief pause before retry
    
    async def _process_health_alerts(self, health_status: Dict[str, Any]) -> None:
        """Process health check results and generate alerts."""
        if health_status["overall_status"] != "healthy":
            await self._send_cicd_alert(
                "high" if health_status["overall_status"] == "unhealthy" else "medium",
                f"CI/CD pipeline health status: {health_status['overall_status']}",
                {"details": health_status["alerts"]}
            )
    
    async def _process_performance_alerts(self, performance_metrics: Dict[str, Any]) -> None:
        """Process performance metrics and generate alerts."""
        # Check success rate
        if performance_metrics["success_rate_24h"] < (1 - self.alert_thresholds["failure_rate"]):
            await self._send_cicd_alert(
                "high",
                f"Pipeline success rate below threshold: {performance_metrics['success_rate_24h']:.1%}",
                {"success_rate": performance_metrics["success_rate_24h"]}
            )
        
        # Check average duration
        if performance_metrics["average_duration"] > self.alert_thresholds["pipeline_duration"]:
            await self._send_cicd_alert(
                "medium",
                f"Pipeline duration above threshold: {performance_metrics['average_duration']:.0f}s",
                {"average_duration": performance_metrics["average_duration"]}
            )
        
        # Check performance degradation
        if performance_metrics["performance_degradation"]:
            await self._send_cicd_alert(
                "medium",
                f"Performance degradation detected in {len(performance_metrics['performance_degradation'])} pipelines",
                {"degradations": performance_metrics["performance_degradation"]}
            )
    
    async def _send_cicd_alert(self, severity: str, message: str, context: Dict[str, Any]) -> None:
        """Send CI/CD alert."""
        alert = {
            "type": "cicd_alert",
            "severity": severity,
            "message": message,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "source": "cicd_monitoring"
        }
        
        logger.warning(f"CI/CD ALERT ({severity}): {message}")
        # In production, this would integrate with alerting system
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get CI/CD monitoring statistics."""
        stats = {
            "monitoring_enabled": self.is_monitoring,
            "check_interval": self.check_interval,
            "alert_thresholds": self.alert_thresholds,
            "platforms": {}
        }
        
        if self.github_monitor:
            stats["platforms"]["github"] = {
                "repo": f"{self.github_monitor.repo_owner}/{self.github_monitor.repo_name}",
                "monitored_workflows": self.github_monitor.monitored_workflows,
                "pipeline_executions": len(self.github_monitor.pipeline_executions),
                "deployment_records": len(self.github_monitor.deployment_records)
            }
        
        return stats

# Global CI/CD monitoring
_cicd_monitor = None

def get_cicd_monitor() -> Optional[CICDObservabilityEngine]:
    """Get global CI/CD monitoring instance."""
    return _cicd_monitor

async def initialize_cicd_monitoring(config: Dict[str, Any]) -> CICDObservabilityEngine:
    """Initialize CI/CD observability monitoring."""
    global _cicd_monitor
    
    _cicd_monitor = CICDObservabilityEngine(config)
    
    await _cicd_monitor.start_monitoring()
    
    logger.info("CI/CD observability monitoring initialized successfully")
    return _cicd_monitor 