"""
Alert Models - Type-safe data models for the real-time alerting system.

This module provides comprehensive Pydantic models for:
- Alert definitions and states
- Threshold rules and configurations  
- Notification settings and channels
- Alert metrics and analytics

Created as part of Step 8: Real-time Alerting & Notification System
Research foundation: Exa + Context7 + Sequential Thinking
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator, root_validator


# ================================
# Enums and Constants
# ================================

class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert lifecycle states"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"


class AlertCategory(str, Enum):
    """Alert categories for organization"""
    PERFORMANCE = "performance"
    SECURITY = "security"
    AVAILABILITY = "availability"
    CAPACITY = "capacity"
    QUALITY = "quality"
    BUSINESS = "business"


class MetricType(str, Enum):
    """Types of metrics that can trigger alerts"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    DISK_USAGE = "disk_usage"
    NETWORK_LATENCY = "network_latency"
    CONNECTION_COUNT = "connection_count"
    QUEUE_SIZE = "queue_size"
    CUSTOM = "custom"


class ComparisonOperator(str, Enum):
    """Operators for threshold comparisons"""
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


class NotificationChannel(str, Enum):
    """Available notification channels"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"


class EscalationAction(str, Enum):
    """Actions for alert escalation"""
    NOTIFY_MANAGER = "notify_manager"
    CREATE_INCIDENT = "create_incident"
    INCREASE_SEVERITY = "increase_severity"
    AUTO_RESOLVE = "auto_resolve"
    EXECUTE_RUNBOOK = "execute_runbook"


# ================================
# Core Alert Models
# ================================

class ThresholdCondition(BaseModel):
    """Individual threshold condition for alerting"""
    metric_type: MetricType
    operator: ComparisonOperator
    value: float
    unit: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "metric_type": "cpu_usage",
                "operator": "gte",
                "value": 85.0,
                "unit": "%",
                "description": "CPU usage exceeds 85%"
            }
        }


class AlertRule(BaseModel):
    """Alert rule configuration with threshold conditions"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: AlertCategory
    severity: AlertSeverity
    enabled: bool = True
    
    # Threshold configuration
    conditions: List[ThresholdCondition] = Field(..., min_items=1)
    evaluation_window: timedelta = Field(default=timedelta(minutes=5))
    consecutive_breaches: int = Field(default=1)
    
    # Timing and frequency
    cooldown_period: timedelta = Field(default=timedelta(minutes=15))
    max_alerts_per_hour: int = Field(default=10)
    
    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    @validator('evaluation_window')
    def validate_evaluation_window(cls, v) -> None:
        if v.total_seconds() < 30:
            raise ValueError('Evaluation window must be at least 30 seconds')
        if v.total_seconds() > 3600:
            raise ValueError('Evaluation window cannot exceed 1 hour')
        return v
    
    @validator('cooldown_period')
    def validate_cooldown_period(cls, v) -> None:
        if v.total_seconds() < 60:
            raise ValueError('Cooldown period must be at least 1 minute')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "High CPU Usage Alert",
                "description": "Alert when CPU usage exceeds 85% for 5 minutes",
                "category": "performance",
                "severity": "high",
                "conditions": [{
                    "metric_type": "cpu_usage",
                    "operator": "gte",
                    "value": 85.0,
                    "unit": "%"
                }],
                "evaluation_window": "PT5M",
                "consecutive_breaches": 2
            }
        }


class Alert(BaseModel):
    """Core alert data model"""
    id: UUID = Field(default_factory=uuid4)
    rule_id: UUID
    rule_name: str
    
    # Alert content
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    category: AlertCategory
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    
    # Context and data
    metric_values: Dict[str, float] = Field(default_factory=dict)
    threshold_breached: float
    actual_value: float
    source_host: Optional[str] = None
    source_component: Optional[str] = None
    
    # Timing
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # User actions
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    assigned_to: Optional[str] = None
    
    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    escalation_level: int = Field(default=0, ge=0, le=5)
    
    @property
    def is_active(self) -> bool:
        """Check if alert is in active state"""
        return self.status == AlertStatus.ACTIVE
    
    @property
    def duration(self) -> timedelta:
        """Calculate alert duration"""
        end_time = self.resolved_at or datetime.utcnow()
        return end_time - self.triggered_at
    
    @property
    def age_minutes(self) -> float:
        """Get alert age in minutes"""
        return self.duration.total_seconds() / 60
    
    def acknowledge(self, user: str, note: Optional[str] = None) -> None:
        """Acknowledge the alert"""
        if self.status == AlertStatus.ACTIVE:
            self.status = AlertStatus.ACKNOWLEDGED
            self.acknowledged_at = datetime.utcnow()
            self.acknowledged_by = user
            self.last_updated = datetime.utcnow()
            if note:
                self.notes.append(f"Acknowledged by {user}: {note}")
    
    def resolve(self, user: str, note: Optional[str] = None) -> None:
        """Resolve the alert"""
        if self.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            self.status = AlertStatus.RESOLVED
            self.resolved_at = datetime.utcnow()
            self.resolved_by = user
            self.last_updated = datetime.utcnow()
            if note:
                self.notes.append(f"Resolved by {user}: {note}")
    
    class Config:
        schema_extra = {
            "example": {
                "rule_name": "High CPU Usage Alert",
                "title": "CPU Usage Critical",
                "description": "CPU usage has exceeded 85% threshold",
                "category": "performance",
                "severity": "high",
                "metric_values": {"cpu_usage": 92.5},
                "threshold_breached": 85.0,
                "actual_value": 92.5,
                "source_host": "server-01"
            }
        }


# ================================
# Notification Models
# ================================

class NotificationTemplate(BaseModel):
    """Template for notification formatting"""
    channel: NotificationChannel
    subject_template: str
    body_template: str
    html_template: Optional[str] = None
    
    # Channel-specific settings
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    email_template_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "channel": "email",
                "subject_template": "Alert: {alert.title} - {alert.severity}",
                "body_template": "Alert triggered: {alert.description}\nValue: {alert.actual_value}\nThreshold: {alert.threshold_breached}"
            }
        }


class NotificationConfig(BaseModel):
    """Notification channel configuration"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    channel: NotificationChannel
    enabled: bool = True
    
    # Channel-specific configuration
    email_addresses: List[str] = Field(default_factory=list)
    webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    
    # Filtering
    severity_filter: List[AlertSeverity] = Field(default_factory=list)
    category_filter: List[AlertCategory] = Field(default_factory=list)
    tag_filters: Dict[str, str] = Field(default_factory=dict)
    
    # Rate limiting
    max_notifications_per_hour: int = Field(default=60, ge=1, le=1000)
    batch_notifications: bool = False
    batch_window: timedelta = Field(default=timedelta(minutes=5))
    
    # Template
    template: Optional[NotificationTemplate] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v, values) -> None:
        if values.get('channel') == NotificationChannel.WEBHOOK and not v:
            raise ValueError('Webhook URL required for webhook notifications')
        return v
    
    @validator('email_addresses')
    def validate_email_addresses(cls, v, values) -> None:
        if values.get('channel') == NotificationChannel.EMAIL and not v:
            raise ValueError('Email addresses required for email notifications')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "DevOps Team Email",
                "channel": "email",
                "email_addresses": ["devops@company.com", "alerts@company.com"],
                "severity_filter": ["critical", "high"],
                "max_notifications_per_hour": 30
            }
        }


class NotificationDelivery(BaseModel):
    """Record of notification delivery attempt"""
    id: UUID = Field(default_factory=uuid4)
    alert_id: UUID
    config_id: UUID
    channel: NotificationChannel
    
    # Delivery details
    status: str = Field(..., pattern=r'^(pending|sent|failed|retrying)$')
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Content
    subject: str
    body: str
    recipients: List[str] = Field(default_factory=list)
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    next_retry_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_successful(self) -> bool:
        """Check if delivery was successful"""
        return self.status == "sent" and self.delivered_at is not None
    
    @property
    def should_retry(self) -> bool:
        """Check if delivery should be retried"""
        return (self.status in ["failed", "retrying"] and 
                self.retry_count < self.max_retries)


# ================================
# Escalation Models
# ================================

class EscalationPolicy(BaseModel):
    """Alert escalation policy configuration"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    enabled: bool = True
    
    # Escalation conditions
    trigger_after: timedelta = Field(default=timedelta(minutes=30))
    severity_levels: List[AlertSeverity] = Field(default_factory=list)
    categories: List[AlertCategory] = Field(default_factory=list)
    
    # Escalation actions
    actions: List[EscalationAction] = Field(..., min_items=1)
    notification_configs: List[UUID] = Field(default_factory=list)
    
    # Advanced settings
    max_escalations: int = Field(default=3, ge=1, le=10)
    escalation_interval: timedelta = Field(default=timedelta(minutes=60))
    auto_resolve_after: Optional[timedelta] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Critical Alert Escalation",
                "trigger_after": "PT30M",
                "severity_levels": ["critical"],
                "actions": ["notify_manager", "create_incident"],
                "escalation_interval": "PT60M"
            }
        }


class EscalationEvent(BaseModel):
    """Record of escalation event"""
    id: UUID = Field(default_factory=uuid4)
    alert_id: UUID
    policy_id: UUID
    escalation_level: int = Field(..., ge=1)
    
    action: EscalationAction
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    
    # Results
    success: bool = False
    error_message: Optional[str] = None
    notification_ids: List[UUID] = Field(default_factory=list)
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)


# ================================
# Metrics and Analytics Models
# ================================

class AlertMetrics(BaseModel):
    """Alert system performance metrics"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Alert counts
    total_alerts: int = Field(default=0, ge=0)
    active_alerts: int = Field(default=0, ge=0)
    resolved_alerts: int = Field(default=0, ge=0)
    acknowledged_alerts: int = Field(default=0, ge=0)
    
    # Performance metrics
    avg_resolution_time: Optional[float] = None  # minutes
    avg_acknowledgment_time: Optional[float] = None  # minutes
    alert_rate_per_hour: float = Field(default=0.0, ge=0)
    
    # Severity breakdown
    critical_alerts: int = Field(default=0, ge=0)
    high_alerts: int = Field(default=0, ge=0)
    medium_alerts: int = Field(default=0, ge=0)
    low_alerts: int = Field(default=0, ge=0)
    
    # Notification metrics
    notifications_sent: int = Field(default=0, ge=0)
    notification_failures: int = Field(default=0, ge=0)
    notification_success_rate: float = Field(default=0.0, ge=0, le=100)
    
    # System health
    alert_engine_health: float = Field(default=100.0, ge=0, le=100)
    notification_system_health: float = Field(default=100.0, ge=0, le=100)
    
    class Config:
        schema_extra = {
            "example": {
                "total_alerts": 45,
                "active_alerts": 3,
                "resolved_alerts": 42,
                "avg_resolution_time": 24.5,
                "alert_rate_per_hour": 2.3,
                "critical_alerts": 2,
                "high_alerts": 8,
                "notifications_sent": 127,
                "notification_success_rate": 98.4
            }
        }


class AlertSummary(BaseModel):
    """Summary of alerts for reporting"""
    period_start: datetime
    period_end: datetime
    
    # Alert statistics
    total_alerts: int
    alerts_by_severity: Dict[AlertSeverity, int]
    alerts_by_category: Dict[AlertCategory, int]
    alerts_by_status: Dict[AlertStatus, int]
    
    # Top issues
    top_alert_rules: List[Dict[str, Union[str, int]]]
    top_affected_hosts: List[Dict[str, Union[str, int]]]
    
    # Performance metrics
    avg_resolution_time: Optional[float]
    avg_acknowledgment_time: Optional[float]
    escalation_rate: float
    
    # Trends
    trend_comparison: Optional[Dict[str, float]] = None
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ================================
# API Response Models
# ================================

class AlertListResponse(BaseModel):
    """Response model for alert list endpoints"""
    alerts: List[Alert]
    total_count: int
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_previous: bool = False


class AlertRuleListResponse(BaseModel):
    """Response model for alert rule list endpoints"""
    rules: List[AlertRule]
    total_count: int
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_previous: bool = False


class NotificationConfigListResponse(BaseModel):
    """Response model for notification config list endpoints"""
    configs: List[NotificationConfig]
    total_count: int
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_previous: bool = False


class AlertSystemHealth(BaseModel):
    """Alert system health status"""
    overall_health: float = Field(..., ge=0, le=100)
    components: Dict[str, float] = Field(default_factory=dict)
    
    # Component status
    alert_engine_status: str = "healthy"
    notification_system_status: str = "healthy"
    queue_processor_status: str = "healthy"
    websocket_handler_status: str = "healthy"
    
    # Recent activity
    alerts_last_hour: int = 0
    notifications_last_hour: int = 0
    error_rate_last_hour: float = 0.0
    
    # System metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    queue_size: int = 0
    active_connections: int = 0
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ================================
# WebSocket/SSE Models
# ================================

class AlertEvent(BaseModel):
    """Real-time alert event for WebSocket/SSE streaming"""
    event_type: str = Field(..., pattern=r'^(alert_created|alert_updated|alert_resolved|alert_acknowledged|system_health)$')
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event data
    alert: Optional[Alert] = None
    alert_id: Optional[UUID] = None
    health_data: Optional[AlertSystemHealth] = None
    metrics: Optional[AlertMetrics] = None
    
    # Context
    user_id: Optional[str] = None
    source_component: str = "alert_system"
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "alert_created",
                "alert": {
                    "title": "High CPU Usage",
                    "severity": "high",
                    "status": "active"
                },
                "source_component": "alert_engine"
            }
        }


# ================================
# Configuration Models
# ================================

class AlertSystemConfig(BaseModel):
    """Global alert system configuration"""
    # Engine settings
    evaluation_interval: timedelta = Field(default=timedelta(seconds=30))
    max_concurrent_evaluations: int = Field(default=100, ge=1, le=1000)
    
    # Notification settings
    default_notification_timeout: timedelta = Field(default=timedelta(seconds=30))
    max_notification_retries: int = Field(default=3, ge=0, le=10)
    notification_batch_size: int = Field(default=50, ge=1, le=500)
    
    # Queue settings
    queue_max_size: int = Field(default=10000, ge=100, le=100000)
    queue_worker_count: int = Field(default=5, ge=1, le=50)
    
    # WebSocket settings
    websocket_max_connections: int = Field(default=1000, ge=1, le=10000)
    websocket_heartbeat_interval: timedelta = Field(default=timedelta(seconds=30))
    
    # Cleanup settings
    resolved_alert_retention: timedelta = Field(default=timedelta(days=30))
    notification_log_retention: timedelta = Field(default=timedelta(days=7))
    
    # Feature flags
    enable_alert_deduplication: bool = True
    enable_auto_resolution: bool = True
    enable_escalation_policies: bool = True
    enable_notification_batching: bool = False
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


# Export all models for easy importing
__all__ = [
    # Enums
    'AlertSeverity', 'AlertStatus', 'AlertCategory', 'MetricType', 
    'ComparisonOperator', 'NotificationChannel', 'EscalationAction',
    
    # Core models
    'ThresholdCondition', 'AlertRule', 'Alert',
    
    # Notification models
    'NotificationTemplate', 'NotificationConfig', 'NotificationDelivery',
    
    # Escalation models
    'EscalationPolicy', 'EscalationEvent',
    
    # Metrics models
    'AlertMetrics', 'AlertSummary', 'AlertSystemHealth',
    
    # API models
    'AlertListResponse', 'AlertRuleListResponse', 'NotificationConfigListResponse',
    
    # Real-time models
    'AlertEvent',
    
    # Configuration models
    'AlertSystemConfig'
] 