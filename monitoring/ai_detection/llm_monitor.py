"""
LLM-Assisted Monitoring System for GraphMemory-IDE
Intelligent log analysis and automated incident description generation
"""

import logging
import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

class IncidentSeverity(Enum):
    """Incident severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertCategory(Enum):
    """Alert categorization."""
    PERFORMANCE = "performance"
    ERROR = "error"
    SECURITY = "security"
    CAPACITY = "capacity"
    AVAILABILITY = "availability"

@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime
    level: str
    message: str
    service: str
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IncidentContext:
    """Rich incident context for LLM analysis."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    category: AlertCategory
    affected_services: List[str]
    metrics_snapshot: Dict[str, float]
    related_logs: List[LogEntry]
    timestamp: datetime = field(default_factory=datetime.now)
    trace_data: Optional[Dict[str, Any]] = None
    user_impact: Optional[str] = None
    business_impact: Optional[str] = None
    additional_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnalysisResult:
    """LLM analysis result."""
    incident_summary: str
    root_cause_hypothesis: List[str]
    impact_assessment: str
    recommended_actions: List[str]
    escalation_needed: bool
    confidence_score: float
    analysis_timestamp: datetime

class LLMAnalysisEngine:
    """
    LLM-powered analysis engine for incident investigation.
    
    Uses language models to analyze logs, metrics, and traces
    to provide intelligent incident analysis and recommendations.
    """
    
    def __init__(self, model_endpoint: Optional[str] = None) -> None:
        self.model_endpoint = model_endpoint or "http://localhost:11434"  # Ollama default
        self.model_name = "llama2"  # Default model
        self.analysis_templates = self._load_analysis_templates()
        self.context_cache = {}
        
    def _load_analysis_templates(self) -> Dict[str, str]:
        """Load analysis prompt templates."""
        return {
            "incident_analysis": """
You are an expert SRE analyzing a system incident. Based on the following information, provide a comprehensive analysis:

INCIDENT DETAILS:
- Title: {title}
- Severity: {severity}
- Category: {category}
- Affected Services: {services}

METRICS SNAPSHOT:
{metrics}

RECENT LOG ENTRIES:
{logs}

TRACE DATA:
{traces}

Please provide:
1. A concise incident summary (2-3 sentences)
2. Possible root causes (ranked by likelihood)
3. Impact assessment on users and business
4. Immediate recommended actions
5. Whether escalation is needed (yes/no)
6. Confidence level (0-100%)

Format your response as JSON with the following structure:
{{
    "summary": "...",
    "root_causes": ["cause1", "cause2", ...],
    "impact": "...",
    "actions": ["action1", "action2", ...],
    "escalate": true/false,
    "confidence": 85
}}
""",
            
            "log_analysis": """
Analyze the following log entries for patterns, errors, and anomalies:

LOG ENTRIES:
{logs}

Identify:
1. Error patterns and frequencies
2. Performance anomalies
3. Security concerns
4. Unusual behavior patterns
5. Correlation with time periods

Provide insights in JSON format:
{{
    "patterns": ["pattern1", "pattern2"],
    "errors": ["error1", "error2"],
    "anomalies": ["anomaly1", "anomaly2"],
    "security_flags": ["flag1", "flag2"],
    "insights": "Overall analysis summary"
}}
""",
            
            "alert_enrichment": """
Given this alert and context, provide enriched information:

ALERT:
- Metric: {metric}
- Value: {value}
- Threshold: {threshold}
- Timestamp: {timestamp}

CONTEXT:
{context}

Enrich this alert with:
1. Business impact explanation
2. Likely causes
3. Urgency assessment
4. Recommended immediate actions
5. Additional monitoring suggestions

Format as JSON:
{{
    "business_impact": "...",
    "likely_causes": ["cause1", "cause2"],
    "urgency": "low/medium/high/critical",
    "immediate_actions": ["action1", "action2"],
    "additional_monitoring": ["metric1", "metric2"]
}}
"""
        }
    
    async def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call LLM API with the given prompt."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent analysis
                        "top_p": 0.9,
                        "num_predict": 1000
                    }
                }
                
                if system_prompt:
                    payload["system"] = system_prompt
                
                response = await client.post(
                    f"{self.model_endpoint}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    logger.error(f"LLM API error: {response.status_code}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return ""
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback: try to parse the entire response
                return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response")
            return {}
    
    async def analyze_incident(self, incident: IncidentContext) -> AnalysisResult:
        """Perform comprehensive incident analysis using LLM."""
        logger.info(f"Analyzing incident: {incident.incident_id}")
        
        # Prepare context data
        metrics_text = "\n".join([f"- {k}: {v}" for k, v in incident.metrics_snapshot.items()])
        
        logs_text = "\n".join([
            f"[{log.timestamp}] {log.level}: {log.message}"
            for log in incident.related_logs[-10:]  # Last 10 logs
        ])
        
        traces_text = json.dumps(incident.trace_data, indent=2) if incident.trace_data else "No trace data available"
        
        # Format the prompt
        prompt = self.analysis_templates["incident_analysis"].format(
            title=incident.title,
            severity=incident.severity.value,
            category=incident.category.value,
            services=", ".join(incident.affected_services),
            metrics=metrics_text,
            logs=logs_text,
            traces=traces_text
        )
        
        # Get LLM analysis
        response = await self._call_llm(prompt)
        
        if not response:
            # Fallback analysis
            return self._fallback_analysis(incident)
        
        # Parse LLM response
        analysis_data = self._extract_json_from_response(response)
        
        if not analysis_data:
            return self._fallback_analysis(incident)
        
        # Create analysis result
        return AnalysisResult(
            incident_summary=analysis_data.get("summary", "Analysis failed"),
            root_cause_hypothesis=analysis_data.get("root_causes", []),
            impact_assessment=analysis_data.get("impact", "Unknown impact"),
            recommended_actions=analysis_data.get("actions", []),
            escalation_needed=analysis_data.get("escalate", True),
            confidence_score=analysis_data.get("confidence", 50.0) / 100.0,
            analysis_timestamp=datetime.now()
        )
    
    def _fallback_analysis(self, incident: IncidentContext) -> AnalysisResult:
        """Provide fallback analysis when LLM is unavailable."""
        fallback_actions = [
            "Check system logs for errors",
            "Review recent deployments",
            "Monitor key metrics",
            "Verify system connectivity"
        ]
        
        if incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
            fallback_actions.insert(0, "Escalate to on-call engineer immediately")
        
        return AnalysisResult(
            incident_summary=f"Automated analysis for {incident.category.value} incident affecting {', '.join(incident.affected_services)}",
            root_cause_hypothesis=[
                "System resource exhaustion",
                "Network connectivity issues",
                "Application-level errors",
                "Configuration changes"
            ],
            impact_assessment="Potential service degradation detected",
            recommended_actions=fallback_actions,
            escalation_needed=incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL],
            confidence_score=0.3,  # Low confidence for fallback
            analysis_timestamp=datetime.now()
        )
    
    async def analyze_logs(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Analyze log entries for patterns and anomalies."""
        if not logs:
            return {}
        
        logs_text = "\n".join([
            f"[{log.timestamp}] {log.level} [{log.service}]: {log.message}"
            for log in logs[-50:]  # Analyze last 50 logs
        ])
        
        prompt = self.analysis_templates["log_analysis"].format(logs=logs_text)
        
        response = await self._call_llm(prompt)
        
        if response:
            return self._extract_json_from_response(response)
        
        return {}
    
    async def enrich_alert(
        self,
        metric_name: str,
        value: float,
        threshold: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich alert with LLM-generated context and recommendations."""
        context_text = json.dumps(context, indent=2)
        
        prompt = self.analysis_templates["alert_enrichment"].format(
            metric=metric_name,
            value=value,
            threshold=threshold,
            timestamp=datetime.now().isoformat(),
            context=context_text
        )
        
        response = await self._call_llm(prompt)
        
        if response:
            enrichment = self._extract_json_from_response(response)
            if enrichment:
                return enrichment
        
        # Fallback enrichment
        return {
            "business_impact": f"Metric {metric_name} exceeded threshold",
            "likely_causes": ["Resource constraint", "Increased load", "System degradation"],
            "urgency": "medium",
            "immediate_actions": ["Monitor trend", "Check logs", "Review system health"],
            "additional_monitoring": [f"{metric_name}_related_metrics"]
        }

class ContextualAlertManager:
    """
    Manages alerts with rich context and LLM-powered enrichment.
    """
    
    def __init__(self, llm_engine: Optional[LLMAnalysisEngine] = None) -> None:
        self.llm_engine = llm_engine or LLMAnalysisEngine()
        self.active_incidents = {}
        self.alert_history = []
        self.correlation_rules = self._load_correlation_rules()
        
    def _load_correlation_rules(self) -> Dict[str, List[str]]:
        """Load alert correlation rules."""
        return {
            "response_time": ["cpu_usage", "memory_usage", "active_sessions"],
            "error_rate": ["response_time", "database_connections", "external_api_errors"],
            "memory_usage": ["node_count", "active_sessions", "cache_size"],
            "cpu_usage": ["request_rate", "background_jobs", "concurrent_users"]
        }
    
    async def process_alert(
        self,
        metric_name: str,
        value: float,
        threshold: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IncidentContext:
        """Process incoming alert with contextual enrichment."""
        logger.info(f"Processing alert: {metric_name} = {value} (threshold: {threshold})")
        
        # Determine severity
        severity = self._calculate_severity(value, threshold)
        
        # Categorize alert
        category = self._categorize_alert(metric_name)
        
        # Collect related metrics
        related_metrics = await self._collect_related_metrics(metric_name)
        
        # Get recent logs
        recent_logs = await self._get_recent_logs(metric_name)
        
        # Create incident context
        incident = IncidentContext(
            incident_id=f"INC-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{metric_name}",
            title=f"{metric_name.replace('_', ' ').title()} Alert",
            description=f"Metric {metric_name} exceeded threshold: {value} > {threshold}",
            severity=severity,
            category=category,
            affected_services=self._identify_affected_services(metric_name),
            metrics_snapshot=related_metrics,
            related_logs=recent_logs,
            additional_metadata=metadata or {}
        )
        
        # Enrich with LLM analysis
        enrichment = await self.llm_engine.enrich_alert(
            metric_name, value, threshold, {
                "related_metrics": related_metrics,
                "recent_logs": [log.message for log in recent_logs[-5:]],
                "severity": severity.value,
                "category": category.value
            }
        )
        
        # Update incident with enrichment
        incident.business_impact = enrichment.get("business_impact")
        incident.user_impact = self._assess_user_impact(category, severity)
        
        # Store incident
        self.active_incidents[incident.incident_id] = incident
        self.alert_history.append(incident)
        
        # Keep history bounded
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]
        
        logger.info(f"Created incident {incident.incident_id} with severity {severity.value}")
        
        return incident
    
    def _calculate_severity(self, value: float, threshold: float) -> IncidentSeverity:
        """Calculate alert severity based on threshold breach."""
        ratio = value / threshold if threshold > 0 else 1.0
        
        if ratio >= 3.0:
            return IncidentSeverity.CRITICAL
        elif ratio >= 2.0:
            return IncidentSeverity.HIGH
        elif ratio >= 1.5:
            return IncidentSeverity.MEDIUM
        else:
            return IncidentSeverity.LOW
    
    def _categorize_alert(self, metric_name: str) -> AlertCategory:
        """Categorize alert based on metric name."""
        metric_lower = metric_name.lower()
        
        if any(term in metric_lower for term in ['duration', 'latency', 'response_time']):
            return AlertCategory.PERFORMANCE
        elif any(term in metric_lower for term in ['error', 'exception', 'failed']):
            return AlertCategory.ERROR
        elif any(term in metric_lower for term in ['memory', 'cpu', 'disk', 'capacity']):
            return AlertCategory.CAPACITY
        elif any(term in metric_lower for term in ['auth', 'security', 'unauthorized']):
            return AlertCategory.SECURITY
        elif any(term in metric_lower for term in ['availability', 'uptime', 'health']):
            return AlertCategory.AVAILABILITY
        else:
            return AlertCategory.PERFORMANCE  # Default
    
    def _identify_affected_services(self, metric_name: str) -> List[str]:
        """Identify services affected by the metric."""
        # Extract service name from metric
        if 'graphmemory' in metric_name:
            return ['graphmemory-api', 'graphmemory-search']
        elif 'database' in metric_name:
            return ['database', 'graphmemory-api']
        elif 'redis' in metric_name:
            return ['redis', 'graphmemory-cache']
        else:
            return ['graphmemory-api']  # Default
    
    async def _collect_related_metrics(self, metric_name: str) -> Dict[str, float]:
        """Collect metrics related to the alerting metric."""
        related_metrics = {}
        
        # Get correlation rules
        correlations = self.correlation_rules.get(metric_name, [])
        
        # Simulate metric collection (in production, query Prometheus)
        base_metrics = {
            'cpu_usage': 45.2,
            'memory_usage': 67.8,
            'response_time': 0.8,
            'error_rate': 2.1,
            'active_sessions': 156,
            'node_count': 1234
        }
        
        related_metrics[metric_name] = base_metrics.get(metric_name, 0.0)
        
        for correlation in correlations:
            related_metrics[correlation] = base_metrics.get(correlation, 0.0)
        
        return related_metrics
    
    async def _get_recent_logs(self, metric_name: str, hours: int = 1) -> List[LogEntry]:
        """Get recent log entries related to the metric."""
        # Simulate log collection (in production, query log aggregation system)
        base_time = datetime.now()
        
        sample_logs = [
            LogEntry(
                timestamp=base_time - timedelta(minutes=5),
                level="WARN",
                message=f"High {metric_name} detected",
                service="graphmemory-api"
            ),
            LogEntry(
                timestamp=base_time - timedelta(minutes=10),
                level="INFO",
                message="Processing search request",
                service="graphmemory-search"
            ),
            LogEntry(
                timestamp=base_time - timedelta(minutes=15),
                level="ERROR",
                message="Database connection timeout",
                service="graphmemory-api"
            )
        ]
        
        return sample_logs
    
    def _assess_user_impact(self, category: AlertCategory, severity: IncidentSeverity) -> str:
        """Assess impact on users."""
        impact_matrix = {
            (AlertCategory.PERFORMANCE, IncidentSeverity.CRITICAL): "Severe performance degradation affecting all users",
            (AlertCategory.PERFORMANCE, IncidentSeverity.HIGH): "Noticeable performance issues for most users",
            (AlertCategory.ERROR, IncidentSeverity.CRITICAL): "Service unavailable for all users",
            (AlertCategory.ERROR, IncidentSeverity.HIGH): "Intermittent failures affecting many users",
            (AlertCategory.CAPACITY, IncidentSeverity.HIGH): "System approaching capacity limits",
            (AlertCategory.SECURITY, IncidentSeverity.CRITICAL): "Potential security breach detected",
            (AlertCategory.AVAILABILITY, IncidentSeverity.CRITICAL): "Service completely unavailable"
        }
        
        return impact_matrix.get((category, severity), "Minimal user impact expected")
    
    async def correlate_alerts(self, time_window: int = 300) -> List[List[IncidentContext]]:
        """Correlate related alerts within a time window."""
        correlated_groups = []
        current_time = datetime.now()
        
        # Get recent incidents
        recent_incidents = [
            incident for incident in self.active_incidents.values()
            if (current_time - incident.timestamp).total_seconds() <= time_window
        ]
        
        # Group by service and category
        groups = {}
        for incident in recent_incidents:
            for service in incident.affected_services:
                key = (service, incident.category)
                if key not in groups:
                    groups[key] = []
                groups[key].append(incident)
        
        # Filter groups with multiple incidents
        for group in groups.values():
            if len(group) > 1:
                correlated_groups.append(group)
        
        return correlated_groups
    
    def get_incident_summary(self) -> Dict[str, Any]:
        """Get summary of current incidents."""
        active_count = len(self.active_incidents)
        
        severity_counts = {}
        category_counts = {}
        
        for incident in self.active_incidents.values():
            severity = incident.severity.value
            category = incident.category.value
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "active_incidents": active_count,
            "total_alerts_today": len([
                alert for alert in self.alert_history
                if alert.timestamp.date() == datetime.now().date()
            ]),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "average_resolution_time": "N/A",  # Would calculate from resolved incidents
            "escalation_rate": "N/A"  # Would calculate from escalated incidents
        }

# Global alert manager
_alert_manager = None

def get_alert_manager() -> ContextualAlertManager:
    """Get or create global alert manager."""
    global _alert_manager
    
    if _alert_manager is None:
        _alert_manager = ContextualAlertManager()
    
    return _alert_manager

async def initialize_llm_monitoring(
    model_endpoint: str = "http://localhost:11434",
    model_name: str = "llama2"
) -> ContextualAlertManager:
    """Initialize LLM-assisted monitoring system."""
    global _alert_manager
    
    llm_engine = LLMAnalysisEngine(model_endpoint)
    llm_engine.model_name = model_name
    
    _alert_manager = ContextualAlertManager(llm_engine)
    
    logger.info("LLM-assisted monitoring system initialized")
    return _alert_manager 