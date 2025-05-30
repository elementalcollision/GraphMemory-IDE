"""
Smart Alerting System for GraphMemory-IDE
Context-aware notification system with intelligent correlation and deduplication
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib

import httpx

logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    SMS = "sms"
    TEAMS = "teams"

class EscalationLevel(Enum):
    """Escalation levels."""
    L1 = "level_1"
    L2 = "level_2"
    L3 = "level_3"
    MANAGEMENT = "management"

@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    metric_pattern: str
    threshold: float
    comparison: str  # gt, lt, eq, ne
    duration: int  # seconds
    severity: str
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    notification_channels: List[NotificationChannel] = field(default_factory=list)

@dataclass
class NotificationTarget:
    """Notification target configuration."""
    target_id: str
    channel: NotificationChannel
    endpoint: str
    credentials: Dict[str, str]
    filters: Dict[str, Any] = field(default_factory=dict)
    rate_limit: Optional[int] = None  # notifications per hour

@dataclass
class AlertCorrelation:
    """Alert correlation result."""
    correlation_id: str
    primary_alert: str
    related_alerts: List[str]
    correlation_strength: float
    correlation_type: str  # temporal, causal, service, metric
    created_at: datetime

@dataclass
class EscalationPolicy:
    """Escalation policy configuration."""
    policy_id: str
    name: str
    steps: List[Dict[str, Any]]
    timeout_minutes: int
    repeat_cycles: int = 1

class AlertCorrelationEngine:
    """
    Advanced alert correlation engine using multiple correlation strategies.
    
    Reduces alert noise by intelligently grouping related alerts
    and identifying root cause relationships.
    """
    
    def __init__(self):
        self.correlation_window = 600  # 10 minutes
        self.correlation_cache = {}
        self.alert_history = []
        self.correlation_rules = self._load_correlation_rules()
        
    def _load_correlation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load alert correlation rules."""
        return {
            "service_correlation": {
                "graphmemory_api": ["graphmemory_search", "database", "redis"],
                "database": ["graphmemory_api", "storage"],
                "load_balancer": ["graphmemory_api", "nginx"]
            },
            "metric_correlation": {
                "response_time": ["cpu_usage", "memory_usage", "database_connections"],
                "error_rate": ["response_time", "database_errors", "network_errors"],
                "memory_usage": ["node_count", "active_sessions", "cache_size"]
            },
            "temporal_patterns": {
                "deployment_window": 1800,  # 30 minutes after deployment
                "maintenance_window": 3600,  # 1 hour during maintenance
                "peak_hours": [9, 10, 11, 14, 15, 16, 17]  # Business hours
            }
        }
    
    def correlate_alerts(self, alerts: List[Dict[str, Any]]) -> List[AlertCorrelation]:
        """Correlate incoming alerts using multiple strategies."""
        correlations = []
        
        if len(alerts) < 2:
            return correlations
        
        # Sort alerts by timestamp
        sorted_alerts = sorted(alerts, key=lambda x: x.get('timestamp', datetime.now()))
        
        # Apply correlation strategies
        temporal_correlations = self._temporal_correlation(sorted_alerts)
        service_correlations = self._service_correlation(sorted_alerts)
        metric_correlations = self._metric_correlation(sorted_alerts)
        causal_correlations = self._causal_correlation(sorted_alerts)
        
        # Merge correlations
        all_correlations = (
            temporal_correlations + 
            service_correlations + 
            metric_correlations + 
            causal_correlations
        )
        
        # Deduplicate and rank correlations
        correlations = self._deduplicate_correlations(all_correlations)
        
        return correlations
    
    def _temporal_correlation(self, alerts: List[Dict[str, Any]]) -> List[AlertCorrelation]:
        """Correlate alerts based on temporal proximity."""
        correlations = []
        
        for i, primary_alert in enumerate(alerts):
            related_alerts = []
            primary_time = primary_alert.get('timestamp', datetime.now())
            
            for j, other_alert in enumerate(alerts):
                if i == j:
                    continue
                
                other_time = other_alert.get('timestamp', datetime.now())
                time_diff = abs((primary_time - other_time).total_seconds())
                
                if time_diff <= self.correlation_window:
                    related_alerts.append(other_alert.get('alert_id', f'alert_{j}'))
            
            if related_alerts:
                correlation = AlertCorrelation(
                    correlation_id=f"temporal_{primary_alert.get('alert_id', f'alert_{i}')}",
                    primary_alert=primary_alert.get('alert_id', f'alert_{i}'),
                    related_alerts=related_alerts,
                    correlation_strength=min(1.0, len(related_alerts) * 0.3),
                    correlation_type="temporal",
                    created_at=datetime.now()
                )
                correlations.append(correlation)
        
        return correlations
    
    def _service_correlation(self, alerts: List[Dict[str, Any]]) -> List[AlertCorrelation]:
        """Correlate alerts based on service relationships."""
        correlations = []
        service_rules = self.correlation_rules["service_correlation"]
        
        for i, primary_alert in enumerate(alerts):
            primary_service = self._extract_service(primary_alert)
            if not primary_service:
                continue
            
            related_alerts = []
            
            for j, other_alert in enumerate(alerts):
                if i == j:
                    continue
                
                other_service = self._extract_service(other_alert)
                
                # Check if services are related
                if (other_service in service_rules.get(primary_service, []) or
                    primary_service in service_rules.get(other_service, [])):
                    related_alerts.append(other_alert.get('alert_id', f'alert_{j}'))
            
            if related_alerts:
                correlation = AlertCorrelation(
                    correlation_id=f"service_{primary_alert.get('alert_id', f'alert_{i}')}",
                    primary_alert=primary_alert.get('alert_id', f'alert_{i}'),
                    related_alerts=related_alerts,
                    correlation_strength=0.8,  # High confidence for service correlation
                    correlation_type="service",
                    created_at=datetime.now()
                )
                correlations.append(correlation)
        
        return correlations
    
    def _metric_correlation(self, alerts: List[Dict[str, Any]]) -> List[AlertCorrelation]:
        """Correlate alerts based on metric relationships."""
        correlations = []
        metric_rules = self.correlation_rules["metric_correlation"]
        
        for i, primary_alert in enumerate(alerts):
            primary_metric = self._extract_metric(primary_alert)
            if not primary_metric:
                continue
            
            related_alerts = []
            
            for j, other_alert in enumerate(alerts):
                if i == j:
                    continue
                
                other_metric = self._extract_metric(other_alert)
                
                # Check if metrics are related
                if (other_metric in metric_rules.get(primary_metric, []) or
                    primary_metric in metric_rules.get(other_metric, [])):
                    related_alerts.append(other_alert.get('alert_id', f'alert_{j}'))
            
            if related_alerts:
                correlation = AlertCorrelation(
                    correlation_id=f"metric_{primary_alert.get('alert_id', f'alert_{i}')}",
                    primary_alert=primary_alert.get('alert_id', f'alert_{i}'),
                    related_alerts=related_alerts,
                    correlation_strength=0.7,
                    correlation_type="metric", 
                    created_at=datetime.now()
                )
                correlations.append(correlation)
        
        return correlations
    
    def _causal_correlation(self, alerts: List[Dict[str, Any]]) -> List[AlertCorrelation]:
        """Correlate alerts based on causal relationships."""
        correlations = []
        
        # Define causal patterns
        causal_patterns = {
            "cpu_high": ["response_time_high", "error_rate_high"],
            "memory_high": ["gc_pressure", "response_time_high"],
            "database_slow": ["response_time_high", "queue_depth_high"],
            "network_error": ["external_api_error", "timeout_error"]
        }
        
        for i, primary_alert in enumerate(alerts):
            primary_pattern = self._extract_pattern(primary_alert)
            if not primary_pattern:
                continue
            
            related_alerts = []
            
            for j, other_alert in enumerate(alerts):
                if i == j:
                    continue
                
                other_pattern = self._extract_pattern(other_alert)
                
                # Check for causal relationship
                if other_pattern in causal_patterns.get(primary_pattern, []):
                    related_alerts.append(other_alert.get('alert_id', f'alert_{j}'))
            
            if related_alerts:
                correlation = AlertCorrelation(
                    correlation_id=f"causal_{primary_alert.get('alert_id', f'alert_{i}')}",
                    primary_alert=primary_alert.get('alert_id', f'alert_{i}'),
                    related_alerts=related_alerts,
                    correlation_strength=0.9,  # Very high confidence for causal
                    correlation_type="causal",
                    created_at=datetime.now()
                )
                correlations.append(correlation)
        
        return correlations
    
    def _extract_service(self, alert: Dict[str, Any]) -> Optional[str]:
        """Extract service name from alert."""
        # Try multiple fields
        for field in ['service', 'component', 'source']:
            if field in alert:
                return alert[field]
        
        # Extract from metric name
        metric = alert.get('metric_name', '')
        if 'graphmemory' in metric:
            return 'graphmemory_api'
        elif 'database' in metric:
            return 'database'
        elif 'redis' in metric:
            return 'redis'
        
        return None
    
    def _extract_metric(self, alert: Dict[str, Any]) -> Optional[str]:
        """Extract metric type from alert."""
        metric_name = alert.get('metric_name', '').lower()
        
        if 'response_time' in metric_name or 'duration' in metric_name:
            return 'response_time'
        elif 'error' in metric_name:
            return 'error_rate'
        elif 'memory' in metric_name:
            return 'memory_usage'
        elif 'cpu' in metric_name:
            return 'cpu_usage'
        
        return metric_name
    
    def _extract_pattern(self, alert: Dict[str, Any]) -> Optional[str]:
        """Extract alert pattern for causal analysis."""
        metric = self._extract_metric(alert)
        severity = alert.get('severity', 'low')
        
        if metric and severity in ['high', 'critical']:
            return f"{metric}_{severity}"
        
        return None
    
    def _deduplicate_correlations(self, correlations: List[AlertCorrelation]) -> List[AlertCorrelation]:
        """Remove duplicate correlations and rank by strength."""
        seen_combinations = set()
        unique_correlations = []
        
        # Sort by correlation strength (descending)
        sorted_correlations = sorted(correlations, key=lambda x: x.correlation_strength, reverse=True)
        
        for correlation in sorted_correlations:
            # Create a signature for the correlation
            alert_set = frozenset([correlation.primary_alert] + correlation.related_alerts)
            
            if alert_set not in seen_combinations:
                seen_combinations.add(alert_set)
                unique_correlations.append(correlation)
        
        return unique_correlations

class SmartAlertingSystem:
    """
    Intelligent alerting system with context-aware notifications.
    
    Features:
    - Alert correlation and deduplication
    - ML-based severity classification
    - Context-aware routing
    - Escalation management
    - Rate limiting and noise reduction
    """
    
    def __init__(self):
        self.correlation_engine = AlertCorrelationEngine()
        self.notification_targets = {}
        self.escalation_policies = {}
        self.alert_rules = {}
        self.rate_limiters = {}
        self.notification_history = []
        
        # Load configuration
        self._load_configuration()
        
    def _load_configuration(self):
        """Load alerting configuration."""
        # Load notification targets
        self.notification_targets = {
            "ops_team_slack": NotificationTarget(
                target_id="ops_team_slack",
                channel=NotificationChannel.SLACK,
                endpoint="https://hooks.slack.com/services/...",
                credentials={"webhook_url": "https://hooks.slack.com/services/..."},
                rate_limit=60  # 60 notifications per hour
            ),
            "pagerduty_oncall": NotificationTarget(
                target_id="pagerduty_oncall",
                channel=NotificationChannel.PAGERDUTY,
                endpoint="https://events.pagerduty.com/v2/enqueue",
                credentials={"routing_key": "your_routing_key"},
                rate_limit=20
            ),
            "email_alerts": NotificationTarget(
                target_id="email_alerts",
                channel=NotificationChannel.EMAIL,
                endpoint="smtp://smtp.gmail.com:587",
                credentials={"username": "alerts@example.com", "password": "app_password"},
                rate_limit=100
            )
        }
        
        # Load escalation policies
        self.escalation_policies = {
            "critical_escalation": EscalationPolicy(
                policy_id="critical_escalation",
                name="Critical Issue Escalation",
                steps=[
                    {"level": EscalationLevel.L1, "targets": ["ops_team_slack"], "timeout": 5},
                    {"level": EscalationLevel.L2, "targets": ["pagerduty_oncall"], "timeout": 10},
                    {"level": EscalationLevel.L3, "targets": ["email_alerts"], "timeout": 15}
                ],
                timeout_minutes=30,
                repeat_cycles=3
            )
        }
        
        # Load alert rules
        self.alert_rules = {
            "high_response_time": AlertRule(
                rule_id="high_response_time",
                name="High Response Time",
                metric_pattern="graphmemory_http_request_duration_seconds",
                threshold=2.0,
                comparison="gt",
                duration=300,
                severity="high",
                notification_channels=[NotificationChannel.SLACK, NotificationChannel.PAGERDUTY]
            ),
            "error_rate_spike": AlertRule(
                rule_id="error_rate_spike",
                name="Error Rate Spike",
                metric_pattern="graphmemory_http_exceptions_total",
                threshold=10.0,
                comparison="gt",
                duration=180,
                severity="critical",
                notification_channels=[NotificationChannel.PAGERDUTY, NotificationChannel.EMAIL]
            )
        }
    
    async def process_alerts(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process incoming alerts with intelligent correlation and routing."""
        logger.info(f"Processing {len(alerts)} alerts")
        
        processing_result = {
            "alerts_processed": len(alerts),
            "correlations_found": 0,
            "notifications_sent": 0,
            "escalations_triggered": 0,
            "alerts_suppressed": 0
        }
        
        if not alerts:
            return processing_result
        
        # Correlate alerts
        correlations = self.correlation_engine.correlate_alerts(alerts)
        processing_result["correlations_found"] = len(correlations)
        
        # Group alerts by correlation
        alert_groups = self._group_alerts_by_correlation(alerts, correlations)
        
        # Process each group
        for group in alert_groups:
            try:
                await self._process_alert_group(group)
                processing_result["notifications_sent"] += 1
                
                # Check for escalation
                if self._should_escalate(group):
                    await self._trigger_escalation(group)
                    processing_result["escalations_triggered"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing alert group: {e}")
        
        # Update statistics
        processing_result["alerts_suppressed"] = len(alerts) - len(alert_groups)
        
        logger.info(f"Alert processing completed: {processing_result}")
        return processing_result
    
    def _group_alerts_by_correlation(
        self, 
        alerts: List[Dict[str, Any]], 
        correlations: List[AlertCorrelation]
    ) -> List[List[Dict[str, Any]]]:
        """Group alerts based on correlations."""
        groups = []
        processed_alerts = set()
        
        # Create groups from correlations
        for correlation in correlations:
            group_alerts = []
            
            # Find primary alert
            primary_alert = next(
                (alert for alert in alerts 
                 if alert.get('alert_id') == correlation.primary_alert),
                None
            )
            
            if primary_alert and correlation.primary_alert not in processed_alerts:
                group_alerts.append(primary_alert)
                processed_alerts.add(correlation.primary_alert)
                
                # Add related alerts
                for related_id in correlation.related_alerts:
                    related_alert = next(
                        (alert for alert in alerts 
                         if alert.get('alert_id') == related_id),
                        None
                    )
                    
                    if related_alert and related_id not in processed_alerts:
                        group_alerts.append(related_alert)
                        processed_alerts.add(related_id)
                
                if group_alerts:
                    groups.append(group_alerts)
        
        # Add ungrouped alerts as individual groups
        for alert in alerts:
            alert_id = alert.get('alert_id')
            if alert_id not in processed_alerts:
                groups.append([alert])
        
        return groups
    
    async def _process_alert_group(self, alert_group: List[Dict[str, Any]]) -> None:
        """Process a group of correlated alerts."""
        if not alert_group:
            return
        
        # Determine primary alert (highest severity)
        primary_alert = max(alert_group, key=lambda x: self._severity_score(x.get('severity', 'low')))
        
        # Create consolidated notification
        notification = self._create_consolidated_notification(alert_group, primary_alert)
        
        # Determine notification targets
        targets = self._determine_notification_targets(primary_alert)
        
        # Send notifications
        for target in targets:
            if self._check_rate_limit(target):
                await self._send_notification(target, notification)
            else:
                logger.warning(f"Rate limit exceeded for target {target.target_id}")
    
    def _severity_score(self, severity: str) -> int:
        """Convert severity to numeric score."""
        severity_scores = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        return severity_scores.get(severity.lower(), 1)
    
    def _create_consolidated_notification(
        self, 
        alert_group: List[Dict[str, Any]], 
        primary_alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a consolidated notification for an alert group."""
        alert_count = len(alert_group)
        severity = primary_alert.get('severity', 'unknown')
        
        if alert_count == 1:
            title = f"🚨 {severity.title()} Alert: {primary_alert.get('title', 'Unknown Alert')}"
            summary = primary_alert.get('description', 'No description available')
        else:
            title = f"🚨 {severity.title()} Alert Group: {alert_count} Related Alerts"
            summary = f"Multiple related alerts detected. Primary: {primary_alert.get('title', 'Unknown')}"
        
        notification = {
            "title": title,
            "summary": summary,
            "severity": severity,
            "alert_count": alert_count,
            "primary_alert": primary_alert,
            "related_alerts": alert_group[1:] if alert_count > 1 else [],
            "timestamp": datetime.now().isoformat(),
            "dashboard_url": self._generate_dashboard_url(primary_alert),
            "runbook_url": self._get_runbook_url(primary_alert)
        }
        
        return notification
    
    def _determine_notification_targets(self, alert: Dict[str, Any]) -> List[NotificationTarget]:
        """Determine notification targets based on alert context."""
        targets = []
        severity = alert.get('severity', 'low').lower()
        
        # Determine targets based on severity
        if severity == 'critical':
            targets.extend([
                self.notification_targets.get("pagerduty_oncall"),
                self.notification_targets.get("ops_team_slack")
            ])
        elif severity == 'high':
            targets.extend([
                self.notification_targets.get("ops_team_slack"),
                self.notification_targets.get("email_alerts")
            ])
        else:
            targets.append(self.notification_targets.get("ops_team_slack"))
        
        # Filter out None targets
        return [target for target in targets if target is not None]
    
    def _check_rate_limit(self, target: NotificationTarget) -> bool:
        """Check if notification target is within rate limits."""
        if not target.rate_limit:
            return True
        
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        rate_key = f"{target.target_id}_{current_hour}"
        
        current_count = self.rate_limiters.get(rate_key, 0)
        
        if current_count >= target.rate_limit:
            return False
        
        self.rate_limiters[rate_key] = current_count + 1
        return True
    
    async def _send_notification(self, target: NotificationTarget, notification: Dict[str, Any]) -> None:
        """Send notification to target."""
        try:
            if target.channel == NotificationChannel.SLACK:
                await self._send_slack_notification(target, notification)
            elif target.channel == NotificationChannel.PAGERDUTY:
                await self._send_pagerduty_notification(target, notification)
            elif target.channel == NotificationChannel.EMAIL:
                await self._send_email_notification(target, notification)
            else:
                logger.warning(f"Unsupported notification channel: {target.channel}")
            
            # Record notification
            self.notification_history.append({
                "target_id": target.target_id,
                "channel": target.channel.value,
                "notification": notification,
                "timestamp": datetime.now(),
                "status": "sent"
            })
            
        except Exception as e:
            logger.error(f"Failed to send notification to {target.target_id}: {e}")
    
    async def _send_slack_notification(self, target: NotificationTarget, notification: Dict[str, Any]) -> None:
        """Send Slack notification."""
        webhook_url = target.credentials.get("webhook_url")
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")
        
        # Format Slack message
        severity_emoji = {
            'low': '🟡',
            'medium': '🟠', 
            'high': '🔴',
            'critical': '🚨'
        }
        
        emoji = severity_emoji.get(notification['severity'].lower(), '⚠️')
        
        slack_message = {
            "text": notification["title"],
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {notification['title']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": notification["summary"]
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:* {notification['severity'].title()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Alert Count:* {notification['alert_count']}"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Dashboard"
                            },
                            "url": notification.get("dashboard_url", "#")
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Runbook"
                            },
                            "url": notification.get("runbook_url", "#")
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=slack_message)
            response.raise_for_status()
    
    async def _send_pagerduty_notification(self, target: NotificationTarget, notification: Dict[str, Any]) -> None:
        """Send PagerDuty notification."""
        routing_key = target.credentials.get("routing_key")
        if not routing_key:
            raise ValueError("PagerDuty routing key not configured")
        
        pagerduty_payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": notification["title"],
                "severity": notification["severity"],
                "source": "GraphMemory-IDE",
                "component": notification["primary_alert"].get("component", "unknown"),
                "group": "graphmemory",
                "class": "alert",
                "custom_details": {
                    "alert_count": notification["alert_count"],
                    "description": notification["summary"],
                    "dashboard_url": notification.get("dashboard_url"),
                    "runbook_url": notification.get("runbook_url")
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(target.endpoint, json=pagerduty_payload)
            response.raise_for_status()
    
    async def _send_email_notification(self, target: NotificationTarget, notification: Dict[str, Any]) -> None:
        """Send email notification."""
        # Email implementation would go here
        # For now, just log the notification
        logger.info(f"Email notification: {notification['title']}")
    
    def _should_escalate(self, alert_group: List[Dict[str, Any]]) -> bool:
        """Determine if alert group should trigger escalation."""
        # Check if any alert in group has critical severity
        has_critical = any(
            alert.get('severity', '').lower() == 'critical' 
            for alert in alert_group
        )
        
        # Check if group has multiple high-severity alerts
        high_severity_count = sum(
            1 for alert in alert_group 
            if alert.get('severity', '').lower() in ['high', 'critical']
        )
        
        return has_critical or high_severity_count >= 3
    
    async def _trigger_escalation(self, alert_group: List[Dict[str, Any]]) -> None:
        """Trigger escalation for alert group."""
        primary_alert = max(alert_group, key=lambda x: self._severity_score(x.get('severity', 'low')))
        
        # Use critical escalation policy
        escalation_policy = self.escalation_policies.get("critical_escalation")
        if not escalation_policy:
            logger.warning("No escalation policy found")
            return
        
        logger.warning(f"Triggering escalation for alert group: {primary_alert.get('title')}")
        
        # This would implement the escalation logic
        # For now, just log the escalation
    
    def _generate_dashboard_url(self, alert: Dict[str, Any]) -> str:
        """Generate dashboard URL for alert."""
        return f"http://localhost:3000/d/graphmemory/graphmemory-overview"
    
    def _get_runbook_url(self, alert: Dict[str, Any]) -> str:
        """Get runbook URL for alert type."""
        metric = alert.get('metric_name', '')
        
        runbook_mapping = {
            'response_time': 'https://runbooks.example.com/performance',
            'error_rate': 'https://runbooks.example.com/errors',
            'memory_usage': 'https://runbooks.example.com/capacity'
        }
        
        for pattern, url in runbook_mapping.items():
            if pattern in metric:
                return url
        
        return 'https://runbooks.example.com/general'
    
    def get_alerting_stats(self) -> Dict[str, Any]:
        """Get comprehensive alerting system statistics."""
        # Calculate recent notification metrics (last hour)
        current_time = datetime.now()
        recent_notifications = [
            notif for notif in self.notification_history
            if isinstance(notif.get('timestamp'), datetime) and 
               (current_time - notif['timestamp']).total_seconds() <= 3600
        ]
        
        return {
            'active_alert_groups': len(self.active_alert_groups),
            'total_notifications_sent': len(self.notification_history),
            'recent_notifications_1h': len(recent_notifications),
            'alert_correlations_active': len(self.correlation_cache),
            'escalation_policies': len(self.escalation_policies),
            'notification_targets': len(self.notification_targets),
            'average_correlation_time': sum(
                corr.get('processing_time', 0) for corr in self.correlation_cache.values()
            ) / max(len(self.correlation_cache), 1),
            'system_health': 'operational' if len(recent_notifications) < 100 else 'high_load'
        }

# Global alerting system
_alerting_system = None

def get_alerting_system() -> SmartAlertingSystem:
    """Get or create global alerting system."""
    global _alerting_system
    
    if _alerting_system is None:
        _alerting_system = SmartAlertingSystem()
    
    return _alerting_system

def initialize_smart_alerting() -> SmartAlertingSystem:
    """Initialize smart alerting system."""
    global _alerting_system
    
    _alerting_system = SmartAlertingSystem()
    logger.info("Smart alerting system initialized")
    
    return _alerting_system 