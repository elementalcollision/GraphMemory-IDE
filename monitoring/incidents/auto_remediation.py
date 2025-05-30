"""
Automated Incident Management and Self-Healing System for GraphMemory-IDE
Kubernetes-native remediation with runbook automation and rollback capabilities
"""

import logging
import asyncio
import json
import yaml
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import subprocess
import tempfile
import os

import httpx
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

class RemediationStrategy(Enum):
    """Remediation strategy types."""
    RESTART_POD = "restart_pod"
    SCALE_DEPLOYMENT = "scale_deployment"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    DRAIN_NODE = "drain_node"
    EXECUTE_RUNBOOK = "execute_runbook"
    CUSTOM_SCRIPT = "custom_script"

class RemediationStatus(Enum):
    """Remediation execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class RemediationAction:
    """Remediation action definition."""
    action_id: str
    strategy: RemediationStrategy
    target: str  # Pod name, deployment name, etc.
    namespace: str = "default"
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300  # seconds
    retry_count: int = 3
    prerequisites: List[str] = field(default_factory=list)

@dataclass
class RemediationResult:
    """Remediation execution result."""
    action_id: str
    status: RemediationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    output: str = ""
    error_message: Optional[str] = None
    kubernetes_events: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class IncidentRemediationPlan:
    """Comprehensive incident remediation plan."""
    incident_id: str
    title: str
    affected_components: List[str]
    remediation_actions: List[RemediationAction]
    rollback_actions: List[RemediationAction] = field(default_factory=list)
    estimated_duration: int = 600  # seconds
    requires_approval: bool = False

class KubernetesRemediationEngine:
    """
    Kubernetes-native remediation engine with self-healing capabilities.
    
    Provides automated incident response through Kubernetes API operations,
    custom resource management, and intelligent failure recovery.
    """
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.kubeconfig_path = kubeconfig_path
        self.k8s_client = None
        self.apps_v1 = None
        self.core_v1 = None
        
        # Remediation history
        self.remediation_history: List[RemediationResult] = []
        self.active_remediations: Dict[str, RemediationResult] = {}
        
        # Success patterns for learning
        self.success_patterns: Dict[str, List[RemediationAction]] = {}
        
        # Initialize Kubernetes client
        self._initialize_kubernetes_client()
    
    def _initialize_kubernetes_client(self) -> None:
        """Initialize Kubernetes client."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                # Try in-cluster config first, then local kubeconfig
                try:
                    config.load_incluster_config()
                except:
                    config.load_kube_config()
            
            self.k8s_client = client.ApiClient()
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            
            logger.info("Kubernetes client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise
    
    async def execute_remediation_action(self, action: RemediationAction) -> RemediationResult:
        """Execute a single remediation action."""
        result = RemediationResult(
            action_id=action.action_id,
            status=RemediationStatus.RUNNING,
            started_at=datetime.now()
        )
        
        self.active_remediations[action.action_id] = result
        
        try:
            logger.info(f"Executing remediation action: {action.strategy.value} for {action.target}")
            
            if action.strategy == RemediationStrategy.RESTART_POD:
                output = await self._restart_pod(action.target, action.namespace)
            elif action.strategy == RemediationStrategy.SCALE_DEPLOYMENT:
                output = await self._scale_deployment(action.target, action.namespace, action.parameters)
            elif action.strategy == RemediationStrategy.ROLLBACK_DEPLOYMENT:
                output = await self._rollback_deployment(action.target, action.namespace)
            elif action.strategy == RemediationStrategy.DRAIN_NODE:
                output = await self._drain_node(action.target)
            elif action.strategy == RemediationStrategy.EXECUTE_RUNBOOK:
                output = await self._execute_runbook(action.parameters.get('runbook_url', ''))
            elif action.strategy == RemediationStrategy.CUSTOM_SCRIPT:
                output = await self._execute_custom_script(action.parameters.get('script', ''))
            else:
                raise ValueError(f"Unknown remediation strategy: {action.strategy}")
            
            result.status = RemediationStatus.SUCCESS
            result.output = output
            result.completed_at = datetime.now()
            
            logger.info(f"Remediation action {action.action_id} completed successfully")
            
        except Exception as e:
            result.status = RemediationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            
            logger.error(f"Remediation action {action.action_id} failed: {e}")
        
        finally:
            # Move from active to history
            if action.action_id in self.active_remediations:
                del self.active_remediations[action.action_id]
            self.remediation_history.append(result)
            
            # Keep history bounded
            if len(self.remediation_history) > 1000:
                self.remediation_history = self.remediation_history[-500:]
        
        return result
    
    async def _restart_pod(self, pod_name: str, namespace: str) -> str:
        """Restart a specific pod."""
        try:
            # Delete the pod - Kubernetes will recreate it
            self.core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Wait for pod to be recreated
            await asyncio.sleep(5)
            
            # Verify pod is running
            for attempt in range(30):  # 30 * 2 = 60 seconds timeout
                try:
                    pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                    if pod.status.phase == "Running":
                        return f"Pod {pod_name} restarted successfully"
                except ApiException:
                    pass  # Pod might not exist yet
                
                await asyncio.sleep(2)
            
            return f"Pod {pod_name} restart initiated, status pending"
            
        except ApiException as e:
            raise Exception(f"Failed to restart pod {pod_name}: {e.reason}")
    
    async def _scale_deployment(self, deployment_name: str, namespace: str, parameters: Dict[str, Any]) -> str:
        """Scale a deployment up or down."""
        try:
            replicas = parameters.get('replicas', 3)
            
            # Patch deployment replicas
            body = {'spec': {'replicas': replicas}}
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body=body
            )
            
            # Wait for scaling to complete
            for attempt in range(60):  # 2 minutes timeout
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name, 
                    namespace=namespace
                )
                
                if deployment.status.ready_replicas == replicas:
                    return f"Deployment {deployment_name} scaled to {replicas} replicas"
                
                await asyncio.sleep(2)
            
            return f"Deployment {deployment_name} scaling to {replicas} replicas in progress"
            
        except ApiException as e:
            raise Exception(f"Failed to scale deployment {deployment_name}: {e.reason}")
    
    async def _rollback_deployment(self, deployment_name: str, namespace: str) -> str:
        """Rollback a deployment to previous version."""
        try:
            # Get rollout history
            rollout_history = await self._run_kubectl_command(
                ['rollout', 'history', f'deployment/{deployment_name}', '-n', namespace]
            )
            
            # Perform rollback
            rollback_result = await self._run_kubectl_command(
                ['rollout', 'undo', f'deployment/{deployment_name}', '-n', namespace]
            )
            
            # Wait for rollback to complete
            await self._run_kubectl_command(
                ['rollout', 'status', f'deployment/{deployment_name}', '-n', namespace]
            )
            
            return f"Deployment {deployment_name} rolled back successfully"
            
        except Exception as e:
            raise Exception(f"Failed to rollback deployment {deployment_name}: {e}")
    
    async def _drain_node(self, node_name: str) -> str:
        """Safely drain a Kubernetes node."""
        try:
            # Cordon the node first
            await self._run_kubectl_command(['cordon', node_name])
            
            # Drain the node
            await self._run_kubectl_command([
                'drain', node_name, 
                '--ignore-daemonsets', 
                '--delete-emptydir-data',
                '--force'
            ])
            
            return f"Node {node_name} drained successfully"
            
        except Exception as e:
            raise Exception(f"Failed to drain node {node_name}: {e}")
    
    async def _execute_runbook(self, runbook_url: str) -> str:
        """Execute automated runbook procedures."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(runbook_url)
                response.raise_for_status()
                
                runbook_content = response.text
                
                # Parse runbook (assuming YAML format)
                runbook_data = yaml.safe_load(runbook_content)
                
                results = []
                for step in runbook_data.get('steps', []):
                    step_result = await self._execute_runbook_step(step)
                    results.append(step_result)
                
                return f"Runbook executed: {len(results)} steps completed"
                
        except Exception as e:
            raise Exception(f"Failed to execute runbook: {e}")
    
    async def _execute_runbook_step(self, step: Dict[str, Any]) -> str:
        """Execute a single runbook step."""
        step_type = step.get('type', 'command')
        
        if step_type == 'kubectl':
            return await self._run_kubectl_command(step['command'].split())
        elif step_type == 'http':
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=step.get('method', 'GET'),
                    url=step['url'],
                    json=step.get('data', {})
                )
                return f"HTTP {step.get('method', 'GET')} {step['url']}: {response.status_code}"
        elif step_type == 'wait':
            await asyncio.sleep(step.get('seconds', 5))
            return f"Waited {step.get('seconds', 5)} seconds"
        else:
            return f"Unknown step type: {step_type}"
    
    async def _execute_custom_script(self, script: str) -> str:
        """Execute custom remediation script."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write("#!/bin/bash\n")
                f.write(script)
                temp_script = f.name
            
            os.chmod(temp_script, 0o755)
            
            result = await self._run_shell_command([temp_script])
            
            os.unlink(temp_script)
            
            return result
            
        except Exception as e:
            raise Exception(f"Failed to execute custom script: {e}")
    
    async def _run_kubectl_command(self, args: List[str]) -> str:
        """Run kubectl command asynchronously."""
        cmd = ['kubectl'] + args
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"kubectl command failed: {stderr.decode()}")
        
        return stdout.decode().strip()
    
    async def _run_shell_command(self, args: List[str]) -> str:
        """Run shell command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Command failed: {stderr.decode()}")
        
        return stdout.decode().strip()

class IntelligentRemediationPlanner:
    """
    AI-powered remediation planning system.
    
    Analyzes incidents and creates appropriate remediation plans
    based on patterns, success history, and system state.
    """
    
    def __init__(self, k8s_engine: KubernetesRemediationEngine):
        self.k8s_engine = k8s_engine
        self.remediation_patterns = self._load_remediation_patterns()
        self.success_rate_threshold = 0.7
    
    def _load_remediation_patterns(self) -> Dict[str, List[RemediationAction]]:
        """Load pre-defined remediation patterns."""
        return {
            "high_cpu_usage": [
                RemediationAction(
                    action_id="scale_up_cpu",
                    strategy=RemediationStrategy.SCALE_DEPLOYMENT,
                    target="graphmemory-api",
                    parameters={'replicas': 5}
                )
            ],
            "pod_crash_loop": [
                RemediationAction(
                    action_id="restart_crashed_pod",
                    strategy=RemediationStrategy.RESTART_POD,
                    target="",  # Will be filled dynamically
                    parameters={}
                )
            ],
            "memory_leak": [
                RemediationAction(
                    action_id="restart_memory_leak",
                    strategy=RemediationStrategy.RESTART_POD,
                    target="",
                    parameters={}
                ),
                RemediationAction(
                    action_id="scale_out_memory",
                    strategy=RemediationStrategy.SCALE_DEPLOYMENT,
                    target="graphmemory-api",
                    parameters={'replicas': 3}
                )
            ],
            "deployment_failure": [
                RemediationAction(
                    action_id="rollback_failed_deployment",
                    strategy=RemediationStrategy.ROLLBACK_DEPLOYMENT,
                    target="",
                    parameters={}
                )
            ],
            "node_not_ready": [
                RemediationAction(
                    action_id="drain_unhealthy_node",
                    strategy=RemediationStrategy.DRAIN_NODE,
                    target="",
                    parameters={}
                )
            ]
        }
    
    def create_remediation_plan(
        self, 
        incident_type: str, 
        affected_components: List[str],
        incident_context: Dict[str, Any]
    ) -> IncidentRemediationPlan:
        """Create remediation plan based on incident analysis."""
        
        # Select appropriate pattern
        pattern_actions = self.remediation_patterns.get(incident_type, [])
        
        # Customize actions for specific components
        remediation_actions = []
        rollback_actions = []
        
        for action_template in pattern_actions:
            action = RemediationAction(
                action_id=f"{action_template.action_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy=action_template.strategy,
                target=action_template.target or affected_components[0] if affected_components else "unknown",
                namespace=action_template.namespace,
                parameters=action_template.parameters.copy(),
                timeout=action_template.timeout,
                retry_count=action_template.retry_count
            )
            
            remediation_actions.append(action)
            
            # Create corresponding rollback action
            rollback_action = self._create_rollback_action(action)
            if rollback_action:
                rollback_actions.append(rollback_action)
        
        # Determine if approval is required
        requires_approval = self._requires_approval(remediation_actions)
        
        plan = IncidentRemediationPlan(
            incident_id=incident_context.get('incident_id', f'INC-{datetime.now().strftime("%Y%m%d-%H%M%S")}'),
            title=f"Auto-remediation for {incident_type}",
            affected_components=affected_components,
            remediation_actions=remediation_actions,
            rollback_actions=rollback_actions,
            estimated_duration=sum(action.timeout for action in remediation_actions),
            requires_approval=requires_approval
        )
        
        return plan
    
    def _create_rollback_action(self, action: RemediationAction) -> Optional[RemediationAction]:
        """Create rollback action for a remediation action."""
        if action.strategy == RemediationStrategy.SCALE_DEPLOYMENT:
            # Store original replica count for rollback
            return RemediationAction(
                action_id=f"rollback_{action.action_id}",
                strategy=RemediationStrategy.SCALE_DEPLOYMENT,
                target=action.target,
                namespace=action.namespace,
                parameters={'replicas': 2}  # Default fallback
            )
        elif action.strategy == RemediationStrategy.ROLLBACK_DEPLOYMENT:
            # Rolling forward would require the next version
            return None
        else:
            return None
    
    def _requires_approval(self, actions: List[RemediationAction]) -> bool:
        """Determine if remediation plan requires human approval."""
        high_risk_strategies = [
            RemediationStrategy.DRAIN_NODE,
            RemediationStrategy.ROLLBACK_DEPLOYMENT
        ]
        
        return any(action.strategy in high_risk_strategies for action in actions)

class AutomatedIncidentManager:
    """
    Main automated incident management system.
    
    Coordinates incident detection, remediation planning, execution,
    and learning from outcomes.
    """
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.k8s_engine = KubernetesRemediationEngine(kubeconfig_path)
        self.planner = IntelligentRemediationPlanner(self.k8s_engine)
        
        # Incident tracking
        self.active_incidents: Dict[str, IncidentRemediationPlan] = {}
        self.completed_incidents: List[IncidentRemediationPlan] = []
        
        # Auto-remediation settings
        self.auto_remediation_enabled = True
        self.approval_required_by_default = False
        
    async def handle_incident(
        self, 
        incident_type: str, 
        affected_components: List[str],
        incident_context: Dict[str, Any],
        auto_execute: bool = True
    ) -> IncidentRemediationPlan:
        """Handle incoming incident with automated remediation."""
        
        logger.info(f"Handling incident: {incident_type} affecting {affected_components}")
        
        # Create remediation plan
        plan = self.planner.create_remediation_plan(
            incident_type, affected_components, incident_context
        )
        
        self.active_incidents[plan.incident_id] = plan
        
        # Execute plan if auto-execution is enabled
        if auto_execute and self.auto_remediation_enabled:
            if plan.requires_approval and not self.approval_required_by_default:
                logger.warning(f"Plan {plan.incident_id} requires approval but auto-approval disabled")
            else:
                await self.execute_remediation_plan(plan)
        
        return plan
    
    async def execute_remediation_plan(self, plan: IncidentRemediationPlan) -> List[RemediationResult]:
        """Execute remediation plan."""
        results = []
        
        logger.info(f"Executing remediation plan {plan.incident_id}")
        
        for action in plan.remediation_actions:
            try:
                result = await self.k8s_engine.execute_remediation_action(action)
                results.append(result)
                
                # If action failed and has rollback, execute rollback
                if result.status == RemediationStatus.FAILED:
                    logger.warning(f"Action {action.action_id} failed, checking for rollback")
                    rollback_action = next(
                        (rb for rb in plan.rollback_actions if rb.action_id.endswith(action.action_id)),
                        None
                    )
                    if rollback_action:
                        logger.info(f"Executing rollback action {rollback_action.action_id}")
                        rollback_result = await self.k8s_engine.execute_remediation_action(rollback_action)
                        results.append(rollback_result)
                
            except Exception as e:
                logger.error(f"Failed to execute action {action.action_id}: {e}")
                
                # Create failed result
                failed_result = RemediationResult(
                    action_id=action.action_id,
                    status=RemediationStatus.FAILED,
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    error_message=str(e)
                )
                results.append(failed_result)
        
        # Move incident to completed
        if plan.incident_id in self.active_incidents:
            del self.active_incidents[plan.incident_id]
        self.completed_incidents.append(plan)
        
        logger.info(f"Remediation plan {plan.incident_id} completed with {len(results)} actions")
        
        return results
    
    def get_incident_stats(self) -> Dict[str, Any]:
        """Get incident management statistics."""
        total_completed = len(self.completed_incidents)
        
        successful_remediations = sum(
            1 for incident in self.completed_incidents
            # This would check remediation success in a real implementation
        )
        
        return {
            "active_incidents": len(self.active_incidents),
            "completed_incidents": total_completed,
            "success_rate": successful_remediations / total_completed if total_completed > 0 else 0.0,
            "auto_remediation_enabled": self.auto_remediation_enabled,
            "total_remediation_actions": len(self.k8s_engine.remediation_history),
            "average_remediation_time": self._calculate_average_remediation_time()
        }
    
    def _calculate_average_remediation_time(self) -> float:
        """Calculate average remediation time in seconds."""
        completed_actions = [
            result for result in self.k8s_engine.remediation_history
            if result.completed_at and result.status == RemediationStatus.SUCCESS
        ]
        
        if not completed_actions:
            return 0.0
        
        total_time = sum(
            (result.completed_at - result.started_at).total_seconds()
            for result in completed_actions
        )
        
        return total_time / len(completed_actions)

# Global incident manager
_incident_manager = None

def get_incident_manager() -> AutomatedIncidentManager:
    """Get or create global incident manager."""
    global _incident_manager
    
    if _incident_manager is None:
        _incident_manager = AutomatedIncidentManager()
    
    return _incident_manager

async def initialize_auto_remediation(kubeconfig_path: Optional[str] = None) -> AutomatedIncidentManager:
    """Initialize automated incident management system."""
    global _incident_manager
    
    _incident_manager = AutomatedIncidentManager(kubeconfig_path)
    
    logger.info("Automated incident management system initialized")
    return _incident_manager 