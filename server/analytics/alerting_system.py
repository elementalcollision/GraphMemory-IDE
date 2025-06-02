"""
Alerting System for GraphMemory-IDE

This module provides comprehensive alerting capabilities including:
- Security alert monitoring
- Performance threshold alerts
- Anomaly detection
- Multi-channel notifications
- Alert escalation
- Silence and acknowledgment

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import asyncpg
import redis.asyncio as redis
from fastapi import BackgroundTasks

from .analytics_engine import AnalyticsEngine


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class NotificationChannel(Enum):
    """Notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"
    DASHBOARD = "dashboard"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    metric_query: str = ""
    condition: str = "gt"  # gt, lt, eq, ne, contains, anomaly
    threshold: Union[float, str] = 0
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    check_interval: int = 300  # seconds
    notification_channels: List[str] = field(default_factory=list)
    escalation_rules: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    owner_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'metric_query': self.metric_query,
            'condition': self.condition,
            'threshold': self.threshold,
            'severity': self.severity.value,
            'enabled': self.enabled,
            'check_interval': self.check_interval,
            'notification_channels': self.notification_channels,
            'escalation_rules': self.escalation_rules,
            'tags': self.tags,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class Alert:
    """Active alert instance."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    title: str = ""
    description: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.ACTIVE
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    notification_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'status': self.status.value,
            'triggered_at': self.triggered_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_by': self.acknowledged_by,
            'metric_value': self.metric_value,
            'threshold_value': self.threshold_value,
            'context': self.context,
            'notification_history': self.notification_history
        }


class MetricEvaluator:
    """Evaluates metrics against alert rules."""
    
    def __init__(self, analytics_engine: AnalyticsEngine, db_pool: asyncpg.Pool):
        self.analytics_engine = analytics_engine
        self.db_pool = db_pool
    
    async def evaluate_rule(self, rule: AlertRule) -> Optional[Alert]:
        """Evaluate an alert rule and return alert if triggered."""
        try:
            # Execute metric query
            metric_value = await self._execute_metric_query(rule.metric_query)
            
            if metric_value is None:
                return None
            
            # Check condition
            triggered = await self._check_condition(
                metric_value, 
                rule.condition, 
                rule.threshold
            )
            
            if triggered:
                return Alert(
                    rule_id=rule.rule_id,
                    title=f"Alert: {rule.name}",
                    description=rule.description,
                    severity=rule.severity,
                    metric_value=metric_value,
                    threshold_value=float(rule.threshold) if isinstance(rule.threshold, (int, float)) else None,
                    context={
                        'rule_name': rule.name,
                        'metric_query': rule.metric_query,
                        'condition': rule.condition,
                        'threshold': rule.threshold
                    }
                )
            
            return None
            
        except Exception as e:
            print(f"Error evaluating rule {rule.rule_id}: {e}")
            return None
    
    async def _execute_metric_query(self, query: str) -> Optional[float]:
        """Execute a metric query and return the result."""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval(query)
                return float(result) if result is not None else None
        except Exception as e:
            print(f"Error executing metric query: {e}")
            return None
    
    async def _check_condition(
        self, 
        value: float, 
        condition: str, 
        threshold: Union[float, str]
    ) -> bool:
        """Check if the condition is met."""
        try:
            if condition == "gt":
                return value > float(threshold)
            elif condition == "lt":
                return value < float(threshold)
            elif condition == "eq":
                return value == float(threshold)
            elif condition == "ne":
                return value != float(threshold)
            elif condition == "contains" and isinstance(threshold, str):
                return str(threshold).lower() in str(value).lower()
            elif condition == "anomaly":
                return await self._detect_anomaly(value)
            else:
                print(f"Unknown condition: {condition}")
                return False
        except Exception as e:
            print(f"Error checking condition: {e}")
            return False
    
    async def _detect_anomaly(self, current_value: float) -> bool:
        """Simple anomaly detection using historical data."""
        try:
            # Get historical values (last 24h)
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            
            async with self.db_pool.acquire() as conn:
                historical_values = await conn.fetch("""
                    SELECT value FROM real_time_metrics 
                    WHERE timestamp >= $1 
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, one_day_ago)
            
            if len(historical_values) < 10:
                return False  # Not enough data
            
            values = [row['value'] for row in historical_values]
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            # Consider it an anomaly if it's more than 2 standard deviations from the mean
            return abs(current_value - mean) > (2 * stdev)
            
        except Exception as e:
            print(f"Error in anomaly detection: {e}")
            return False


class NotificationService:
    """Handles sending notifications through various channels."""
    
    def __init__(self, settings):
        self.settings = settings
        self.notification_handlers = {
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.WEBHOOK: self._send_webhook,
            NotificationChannel.SLACK: self._send_slack,
            NotificationChannel.DASHBOARD: self._send_dashboard
        }
    
    async def send_notification(
        self, 
        alert: Alert, 
        channels: List[str],
        rule: AlertRule
    ) -> Dict[str, bool]:
        """Send notification through specified channels."""
        results = {}
        
        for channel_name in channels:
            try:
                channel = NotificationChannel(channel_name)
                handler = self.notification_handlers.get(channel)
                
                if handler:
                    success = await handler(alert, rule)
                    results[channel_name] = success
                else:
                    print(f"No handler for notification channel: {channel_name}")
                    results[channel_name] = False
                    
            except Exception as e:
                print(f"Error sending notification to {channel_name}: {e}")
                results[channel_name] = False
        
        return results
    
    async def _send_email(self, alert: Alert, rule: AlertRule) -> bool:
        """Send email notification."""
        try:
            if not hasattr(self.settings, 'SMTP_HOST') or not self.settings.SMTP_HOST:
                print("SMTP not configured, skipping email notification")
                return False
            
            subject = f"[{alert.severity.value.upper()}] {alert.title}"
            
            body = f"""
            Alert: {alert.title}
            
            Severity: {alert.severity.value.upper()}
            Description: {alert.description}
            
            Metric Value: {alert.metric_value}
            Threshold: {alert.threshold_value}
            
            Triggered At: {alert.triggered_at}
            
            Rule: {rule.name}
            Query: {rule.metric_query}
            
            Context: {json.dumps(alert.context, indent=2)}
            """
            
            msg = MIMEMultipart()
            msg['From'] = getattr(self.settings, 'SMTP_FROM', 'alerts@graphmemory.com')
            msg['To'] = getattr(self.settings, 'ALERT_EMAIL', 'admin@graphmemory.com')
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.settings.SMTP_HOST, getattr(self.settings, 'SMTP_PORT', 587))
            if getattr(self.settings, 'SMTP_TLS', True):
                server.starttls()
            if hasattr(self.settings, 'SMTP_USER') and self.settings.SMTP_USER:
                server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)
            
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Failed to send email notification: {e}")
            return False
    
    async def _send_webhook(self, alert: Alert, rule: AlertRule) -> bool:
        """Send webhook notification."""
        try:
            if not hasattr(self.settings, 'WEBHOOK_URL') or not self.settings.WEBHOOK_URL:
                print("Webhook URL not configured")
                return False
            
            import httpx
            
            payload = {
                'alert': alert.to_dict(),
                'rule': rule.to_dict(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.settings.WEBHOOK_URL,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Failed to send webhook notification: {e}")
            return False
    
    async def _send_slack(self, alert: Alert, rule: AlertRule) -> bool:
        """Send Slack notification."""
        try:
            if not hasattr(self.settings, 'SLACK_WEBHOOK_URL') or not self.settings.SLACK_WEBHOOK_URL:
                print("Slack webhook URL not configured")
                return False
            
            import httpx
            
            color = {
                AlertSeverity.INFO: "good",
                AlertSeverity.WARNING: "warning", 
                AlertSeverity.ERROR: "danger",
                AlertSeverity.CRITICAL: "danger"
            }.get(alert.severity, "warning")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": alert.title,
                    "text": alert.description,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Metric Value", "value": str(alert.metric_value), "short": True},
                        {"title": "Threshold", "value": str(alert.threshold_value), "short": True},
                        {"title": "Triggered At", "value": alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True}
                    ]
                }]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Failed to send Slack notification: {e}")
            return False
    
    async def _send_dashboard(self, alert: Alert, rule: AlertRule) -> bool:
        """Send dashboard notification (store in database for dashboard display)."""
        try:
            # This would integrate with the real-time tracker to show alerts in dashboard
            from .real_time_tracker import get_real_time_tracker
            
            tracker = get_real_time_tracker()
            if tracker:
                await tracker.websocket_manager.broadcast({
                    'type': 'alert',
                    'alert': alert.to_dict(),
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            return True
            
        except Exception as e:
            print(f"Failed to send dashboard notification: {e}")
            return False


class AlertingSystem:
    """Main alerting system coordinator."""
    
    def __init__(
        self, 
        analytics_engine: AnalyticsEngine, 
        db_pool: asyncpg.Pool,
        redis_client,
        settings
    ):
        self.analytics_engine = analytics_engine
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.settings = settings
        
        self.metric_evaluator = MetricEvaluator(analytics_engine, db_pool)
        self.notification_service = NotificationService(settings)
        
        # In-memory stores
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the alerting system."""
        try:
            # Create database tables
            await self._create_tables()
            
            # Load existing rules and alerts
            await self._load_alert_rules()
            await self._load_active_alerts()
            
            # Start background monitoring
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Create default alert rules
            await self._create_default_rules()
            
            print("Alerting system initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize alerting system: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the alerting system."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    async def _create_tables(self):
        """Create necessary database tables."""
        async with self.db_pool.acquire() as conn:
            # Alert rules table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    metric_query TEXT NOT NULL,
                    condition VARCHAR(50) NOT NULL,
                    threshold TEXT NOT NULL,
                    severity VARCHAR(50) NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    check_interval INTEGER DEFAULT 300,
                    notification_channels TEXT[],
                    escalation_rules JSONB,
                    tags TEXT[],
                    owner_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Active alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS active_alerts (
                    alert_id VARCHAR(255) PRIMARY KEY,
                    rule_id VARCHAR(255) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    severity VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    triggered_at TIMESTAMP NOT NULL,
                    acknowledged_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    acknowledged_by VARCHAR(255),
                    metric_value DOUBLE PRECISION,
                    threshold_value DOUBLE PRECISION,
                    context JSONB,
                    notification_history JSONB
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_active_alerts_status ON active_alerts(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_active_alerts_severity ON active_alerts(severity)")
    
    async def _load_alert_rules(self):
        """Load alert rules from database."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM alert_rules WHERE enabled = TRUE")
            
            for row in rows:
                rule = AlertRule(
                    rule_id=row['rule_id'],
                    name=row['name'],
                    description=row['description'] or "",
                    metric_query=row['metric_query'],
                    condition=row['condition'],
                    threshold=row['threshold'],
                    severity=AlertSeverity(row['severity']),
                    enabled=row['enabled'],
                    check_interval=row['check_interval'],
                    notification_channels=list(row['notification_channels']) if row['notification_channels'] else [],
                    escalation_rules=row['escalation_rules'] or [],
                    tags=list(row['tags']) if row['tags'] else [],
                    owner_id=row['owner_id'] or "",
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                self.alert_rules[rule.rule_id] = rule
    
    async def _load_active_alerts(self):
        """Load active alerts from database."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM active_alerts WHERE status = 'active'")
            
            for row in rows:
                alert = Alert(
                    alert_id=row['alert_id'],
                    rule_id=row['rule_id'],
                    title=row['title'],
                    description=row['description'] or "",
                    severity=AlertSeverity(row['severity']),
                    status=AlertStatus(row['status']),
                    triggered_at=row['triggered_at'],
                    acknowledged_at=row['acknowledged_at'],
                    resolved_at=row['resolved_at'],
                    acknowledged_by=row['acknowledged_by'],
                    metric_value=row['metric_value'],
                    threshold_value=row['threshold_value'],
                    context=row['context'] or {},
                    notification_history=row['notification_history'] or []
                )
                
                self.active_alerts[alert.alert_id] = alert
    
    async def _create_default_rules(self):
        """Create default alert rules for common scenarios."""
        from typing import cast
        
        default_rules = [
            {
                'name': 'High Error Rate',
                'description': 'Alert when error rate exceeds 5% in the last hour',
                'metric_query': '''
                    SELECT 
                        CASE 
                            WHEN total_events = 0 THEN 0
                            ELSE (error_events::float / total_events::float) * 100
                        END as error_rate
                    FROM (
                        SELECT 
                            COUNT(*) as total_events,
                            COUNT(*) FILTER (WHERE event_type = 'error') as error_events
                        FROM analytics_events 
                        WHERE timestamp >= NOW() - INTERVAL '1 hour'
                    ) subq
                ''',
                'condition': 'gt',
                'threshold': 5.0,
                'severity': AlertSeverity.ERROR,
                'notification_channels': ['email', 'dashboard']
            },
            {
                'name': 'Authentication Failures',
                'description': 'Alert on multiple authentication failures',
                'metric_query': '''
                    SELECT COUNT(*) 
                    FROM analytics_events 
                    WHERE event_type = 'user_action' 
                    AND event_name LIKE '%login%' 
                    AND properties->>'success' = 'false'
                    AND timestamp >= NOW() - INTERVAL '15 minutes'
                ''',
                'condition': 'gt',
                'threshold': 10,
                'severity': AlertSeverity.WARNING,
                'notification_channels': ['email', 'dashboard']
            },
            {
                'name': 'Low Active Users',
                'description': 'Alert when active users drop significantly',
                'metric_query': '''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM analytics_events 
                    WHERE timestamp >= NOW() - INTERVAL '1 hour'
                    AND user_id IS NOT NULL
                ''',
                'condition': 'anomaly',
                'threshold': 0,
                'severity': AlertSeverity.INFO,
                'notification_channels': ['dashboard']
            },
            {
                'name': 'Database Connection Issues',
                'description': 'Alert on database connection problems',
                'metric_query': '''
                    SELECT COUNT(*) 
                    FROM analytics_events 
                    WHERE event_type = 'error' 
                    AND event_name LIKE '%database%'
                    AND timestamp >= NOW() - INTERVAL '5 minutes'
                ''',
                'condition': 'gt',
                'threshold': 5,
                'severity': AlertSeverity.CRITICAL,
                'notification_channels': ['email', 'webhook', 'dashboard']
            }
        ]
        
        for rule_data in default_rules:
            # Check if rule already exists
            existing = any(rule.name == str(rule_data['name']) for rule in self.alert_rules.values())
            if not existing:
                rule = AlertRule(
                    name=str(rule_data['name']),
                    description=str(rule_data['description']),
                    metric_query=str(rule_data['metric_query']),
                    condition=str(rule_data['condition']),
                    threshold=cast(Union[float, str], rule_data['threshold']),
                    severity=cast(AlertSeverity, rule_data['severity']),
                    notification_channels=cast(List[str], rule_data['notification_channels']),
                    owner_id='system'
                )
                
                await self.create_alert_rule(rule)
    
    async def create_alert_rule(self, rule: AlertRule) -> bool:
        """Create a new alert rule."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO alert_rules (
                        rule_id, name, description, metric_query, condition,
                        threshold, severity, enabled, check_interval,
                        notification_channels, escalation_rules, tags, owner_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                rule.rule_id, rule.name, rule.description, rule.metric_query,
                rule.condition, str(rule.threshold), rule.severity.value,
                rule.enabled, rule.check_interval, rule.notification_channels,
                json.dumps(rule.escalation_rules), rule.tags, rule.owner_id
                )
            
            self.alert_rules[rule.rule_id] = rule
            return True
            
        except Exception as e:
            print(f"Failed to create alert rule: {e}")
            return False
    
    async def _monitoring_loop(self):
        """Main monitoring loop that checks all alert rules."""
        while True:
            try:
                current_time = datetime.utcnow()
                
                for rule in self.alert_rules.values():
                    if not rule.enabled:
                        continue
                    
                    # Check if it's time to evaluate this rule
                    last_check_key = f"alert:last_check:{rule.rule_id}"
                    
                    if self.redis_client:
                        last_check_str = await self.redis_client.get(last_check_key)
                        if last_check_str:
                            last_check = datetime.fromisoformat(last_check_str.decode())
                            if (current_time - last_check).total_seconds() < rule.check_interval:
                                continue
                    
                    # Evaluate the rule
                    alert = await self.metric_evaluator.evaluate_rule(rule)
                    
                    if alert:
                        await self._handle_triggered_alert(alert, rule)
                    
                    # Update last check time
                    if self.redis_client:
                        await self.redis_client.set(
                            last_check_key, 
                            current_time.isoformat(),
                            ex=rule.check_interval * 2
                        )
                
                # Sleep for a short interval before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _handle_triggered_alert(self, alert: Alert, rule: AlertRule):
        """Handle a triggered alert."""
        try:
            # Check if there's already an active alert for this rule
            existing_alert = None
            for existing in self.active_alerts.values():
                if existing.rule_id == rule.rule_id and existing.status == AlertStatus.ACTIVE:
                    existing_alert = existing
                    break
            
            if existing_alert:
                # Update existing alert
                existing_alert.metric_value = alert.metric_value
                existing_alert.context = alert.context
                await self._update_alert_in_database(existing_alert)
                return
            
            # Create new alert
            await self._save_alert_to_database(alert)
            self.active_alerts[alert.alert_id] = alert
            
            # Send notifications
            results = await self.notification_service.send_notification(
                alert, rule.notification_channels, rule
            )
            
            # Record notification history
            alert.notification_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'channels': rule.notification_channels,
                'results': results
            })
            
            await self._update_alert_in_database(alert)
            
            print(f"Alert triggered: {alert.title} (ID: {alert.alert_id})")
            
        except Exception as e:
            print(f"Error handling triggered alert: {e}")
    
    async def _save_alert_to_database(self, alert: Alert):
        """Save alert to database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO active_alerts (
                    alert_id, rule_id, title, description, severity, status,
                    triggered_at, metric_value, threshold_value, context,
                    notification_history
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            alert.alert_id, alert.rule_id, alert.title, alert.description,
            alert.severity.value, alert.status.value, alert.triggered_at,
            alert.metric_value, alert.threshold_value,
            json.dumps(alert.context), json.dumps(alert.notification_history)
            )
    
    async def _update_alert_in_database(self, alert: Alert):
        """Update alert in database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE active_alerts SET
                    status = $1, acknowledged_at = $2, resolved_at = $3,
                    acknowledged_by = $4, metric_value = $5, context = $6,
                    notification_history = $7
                WHERE alert_id = $8
            """,
            alert.status.value, alert.acknowledged_at, alert.resolved_at,
            alert.acknowledged_by, alert.metric_value,
            json.dumps(alert.context), json.dumps(alert.notification_history),
            alert.alert_id
            )
    
    async def _cleanup_loop(self):
        """Clean up resolved alerts periodically."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Remove resolved alerts older than 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                resolved_alerts = []
                for alert_id, alert in self.active_alerts.items():
                    if (alert.status == AlertStatus.RESOLVED and 
                        alert.resolved_at and 
                        alert.resolved_at < cutoff_time):
                        resolved_alerts.append(alert_id)
                
                for alert_id in resolved_alerts:
                    del self.active_alerts[alert_id]
                
                # Also clean up from database
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        DELETE FROM active_alerts 
                        WHERE status = 'resolved' 
                        AND resolved_at < $1
                    """, cutoff_time)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
    
    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user_id
        
        await self._update_alert_in_database(alert)
        return True
    
    async def resolve_alert(self, alert_id: str, user_id: str) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        
        await self._update_alert_in_database(alert)
        return True
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [alert.to_dict() for alert in self.active_alerts.values()]


# Global instance
_alerting_system: Optional[AlertingSystem] = None


async def initialize_alerting_system(
    analytics_engine: AnalyticsEngine,
    db_pool: asyncpg.Pool,
    redis_client,
    settings
):
    """Initialize alerting system."""
    global _alerting_system
    _alerting_system = AlertingSystem(analytics_engine, db_pool, redis_client, settings)
    await _alerting_system.initialize()


def get_alerting_system() -> Optional[AlertingSystem]:
    """Get alerting system instance."""
    return _alerting_system


async def shutdown_alerting_system():
    """Shutdown alerting system."""
    global _alerting_system
    if _alerting_system:
        await _alerting_system.shutdown()
        _alerting_system = None 