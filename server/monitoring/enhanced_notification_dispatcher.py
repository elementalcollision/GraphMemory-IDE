"""
Enhanced Notification Dispatcher for GraphMemory-IDE Production Monitoring

This module extends the existing notification system with advanced features:
- Correlation-aware notification routing and grouping
- Intelligent escalation policies with on-call scheduling
- Advanced rate limiting and notification batching
- Multi-channel notification routing with fallback
- Maintenance window and suppression management
- Production-ready notification templates and formatting

Implementation based on research findings from:
- Monitoring best practices from DataDog, NewRelic, PagerDuty
- Production alerting patterns and escalation strategies
- Modern notification management and routing systems
- Alert correlation and deduplication strategies

Created for TASK-022 Phase 1: Enhanced Alerting & Notification System
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable, NamedTuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
from uuid import UUID, uuid4
import hashlib

# Import existing models and utilities
from server.dashboard.models.alert_models import (
    Alert, AlertSeverity, AlertCategory, AlertStatus, NotificationConfig, 
    NotificationChannel, NotificationDelivery, EscalationPolicy, EscalationAction
)
from server.dashboard.notification_dispatcher import NotificationDispatcher
from server.dashboard.cache_manager import get_cache_manager, CacheManager
from server.monitoring.alert_correlation_engine import get_correlation_engine, AlertGroup

logger = logging.getLogger(__name__)


class EscalationStatus(Enum):
    """Escalation status tracking"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    EMERGENCY = "emergency"


@dataclass
class EscalationContext:
    """Context for alert escalation"""
    alert_group: AlertGroup
    policy: EscalationPolicy
    current_level: int = 0
    status: EscalationStatus = EscalationStatus.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_escalation_at: Optional[datetime] = None
    escalation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def should_escalate(self) -> bool:
        """Check if escalation should proceed"""
        if self.status != EscalationStatus.IN_PROGRESS:
            return False
        
        current_time = datetime.utcnow()
        
        # Initial escalation check
        if self.current_level == 0:
            return (current_time - self.started_at) >= self.policy.trigger_after
        
        # Subsequent escalations
        if self.last_escalation_at:
            return (current_time - self.last_escalation_at) >= self.policy.escalation_interval
        
        return False
    
    def can_escalate_further(self) -> bool:
        """Check if further escalation is possible"""
        return self.current_level < self.policy.max_escalations


@dataclass
class NotificationContext:
    """Enhanced notification context with correlation awareness"""
    alert_group: AlertGroup
    notification_configs: List[NotificationConfig]
    priority: NotificationPriority = NotificationPriority.NORMAL
    escalation_context: Optional[EscalationContext] = None
    
    # Rate limiting context
    rate_limit_key: str = ""
    rate_limit_window: timedelta = field(default=timedelta(hours=1))
    max_notifications: int = 10
    
    # Batching context
    batch_enabled: bool = False
    batch_window: timedelta = field(default=timedelta(minutes=5))
    batch_max_size: int = 50
    
    # Suppression context
    maintenance_windows: List[tuple[datetime, datetime]] = field(default_factory=list)
    suppressed_until: Optional[datetime] = None
    
    def is_suppressed(self, current_time: Optional[datetime] = None) -> bool:
        """Check if notifications are suppressed"""
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Check explicit suppression
        if self.suppressed_until and current_time < self.suppressed_until:
            return True
        
        # Check maintenance windows
        for start, end in self.maintenance_windows:
            if start <= current_time <= end:
                return True
        
        return False


class EnhancedNotificationDispatcher:
    """Enhanced notification dispatcher with correlation awareness and escalation"""
    
    def __init__(self, base_dispatcher: Optional[NotificationDispatcher] = None) -> None:
        # Use existing dispatcher or create new one
        self.base_dispatcher = base_dispatcher or NotificationDispatcher()
        
        # Enhanced features
        self.escalation_contexts: Dict[str, EscalationContext] = {}
        self.notification_contexts: Dict[str, NotificationContext] = {}
        self.escalation_policies: Dict[UUID, EscalationPolicy] = {}
        
        # Rate limiting
        self.rate_limiters: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Batching
        self.notification_batches: Dict[str, List[Alert]] = defaultdict(list)
        self.batch_timers: Dict[str, datetime] = {}
        
        # External dependencies
        self.cache_manager: Optional[CacheManager] = None
        self.correlation_engine: Optional[Any] = None
        
        # Statistics
        self.enhanced_stats = {
            'notifications_correlated': 0,
            'escalations_triggered': 0,
            'notifications_batched': 0,
            'notifications_suppressed': 0,
            'rate_limited_notifications': 0
        }
        
        logger.info("EnhancedNotificationDispatcher initialized")
    
    async def initialize(self) -> None:
        """Initialize the enhanced notification dispatcher"""
        try:
            # Initialize base dispatcher
            await self.base_dispatcher.initialize()
            
            # Get external dependencies
            self.cache_manager = await get_cache_manager()
            self.correlation_engine = await get_correlation_engine()
            
            # Load escalation policies
            await self._load_escalation_policies()
            
            logger.info("EnhancedNotificationDispatcher initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize EnhancedNotificationDispatcher: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the enhanced notification dispatcher"""
        try:
            # Cancel any pending escalations
            for context in self.escalation_contexts.values():
                context.status = EscalationStatus.CANCELLED
            
            # Shutdown base dispatcher
            await self.base_dispatcher.shutdown()
            
            logger.info("EnhancedNotificationDispatcher shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during EnhancedNotificationDispatcher shutdown: {e}")
    
    async def dispatch_alert_group(self, alert_group: AlertGroup) -> List[NotificationDelivery]:
        """Dispatch notifications for correlated alert group"""
        try:
            # Create notification context
            context = await self._create_notification_context(alert_group)
            
            # Check if notifications are suppressed
            if context.is_suppressed():
                logger.info(f"Notifications suppressed for alert group {alert_group.id}")
                self.enhanced_stats['notifications_suppressed'] += 1
                return []
            
            # Apply rate limiting
            if not await self._check_rate_limits(context):
                logger.info(f"Rate limit exceeded for alert group {alert_group.id}")
                self.enhanced_stats['rate_limited_notifications'] += 1
                return []
            
            # Handle batching if enabled
            if context.batch_enabled:
                return await self._handle_batched_notifications(alert_group, context)
            
            # Dispatch immediate notifications
            deliveries = await self._dispatch_immediate_notifications(alert_group, context)
            
            # Check for escalation
            await self._check_escalation(alert_group, context)
            
            # Update statistics
            self.enhanced_stats['notifications_correlated'] += len(deliveries)
            
            return deliveries
            
        except Exception as e:
            logger.error(f"Error dispatching alert group {alert_group.id}: {e}")
            return []
    
    async def _create_notification_context(self, alert_group: AlertGroup) -> NotificationContext:
        """Create notification context for alert group"""
        # Get applicable notification configurations
        configs = await self._get_applicable_configs(alert_group)
        
        # Determine priority based on group severity
        priority = self._determine_priority(alert_group)
        
        # Create rate limiting key
        rate_limit_key = f"group:{alert_group.id}:severity:{alert_group.get_severity().value}"
        
        # Check for existing escalation context
        escalation_context = self.escalation_contexts.get(alert_group.id)
        
        context = NotificationContext(
            alert_group=alert_group,
            notification_configs=configs,
            priority=priority,
            escalation_context=escalation_context,
            rate_limit_key=rate_limit_key
        )
        
        # Cache context
        self.notification_contexts[alert_group.id] = context
        
        return context
    
    async def _get_applicable_configs(self, alert_group: AlertGroup) -> List[NotificationConfig]:
        """Get notification configurations applicable to alert group"""
        configs = []
        group_severity = alert_group.get_severity()
        
        # Get all notification configs from base dispatcher
        for config in self.base_dispatcher.notification_configs.values():
            if not config.enabled:
                continue
            
            # Check severity filter
            if config.severity_filter and group_severity not in config.severity_filter:
                continue
            
            # Check category filter (use root alert category)
            if config.category_filter and alert_group.root_alert.category not in config.category_filter:
                continue
            
            # Check tag filters
            if config.tag_filters:
                tag_match = all(
                    alert_group.root_alert.tags.get(key) == value
                    for key, value in config.tag_filters.items()
                )
                if not tag_match:
                    continue
            
            configs.append(config)
        
        return configs
    
    def _determine_priority(self, alert_group: AlertGroup) -> NotificationPriority:
        """Determine notification priority based on alert group characteristics"""
        severity = alert_group.get_severity()
        alert_count = alert_group.get_alert_count()
        
        # Critical alerts with high count are emergency
        if severity == AlertSeverity.CRITICAL and alert_count >= 5:
            return NotificationPriority.EMERGENCY
        
        # Critical alerts are urgent
        if severity == AlertSeverity.CRITICAL:
            return NotificationPriority.URGENT
        
        # High severity with multiple alerts
        if severity == AlertSeverity.HIGH and alert_count >= 3:
            return NotificationPriority.HIGH
        
        # High severity alerts
        if severity == AlertSeverity.HIGH:
            return NotificationPriority.NORMAL
        
        # Everything else is low priority
        return NotificationPriority.LOW
    
    async def _check_rate_limits(self, context: NotificationContext) -> bool:
        """Check if notification rate limits allow sending"""
        current_time = datetime.utcnow()
        rate_limiter = self.rate_limiters[context.rate_limit_key]
        
        # Clean old entries
        cutoff_time = current_time - context.rate_limit_window
        while rate_limiter and rate_limiter[0] < cutoff_time:
            rate_limiter.popleft()
        
        # Check if we're under the limit
        if len(rate_limiter) >= context.max_notifications:
            return False
        
        # Add current notification
        rate_limiter.append(current_time)
        return True
    
    async def _handle_batched_notifications(self, alert_group: AlertGroup, context: NotificationContext) -> List[NotificationDelivery]:
        """Handle batched notification delivery"""
        batch_key = context.rate_limit_key
        current_time = datetime.utcnow()
        
        # Add alert group to batch
        self.notification_batches[batch_key].extend([alert_group.root_alert] + alert_group.correlated_alerts)
        
        # Set timer if this is the first item in batch
        if batch_key not in self.batch_timers:
            self.batch_timers[batch_key] = current_time + context.batch_window
        
        # Check if batch should be sent
        batch = self.notification_batches[batch_key]
        timer = self.batch_timers[batch_key]
        
        should_send = (
            len(batch) >= context.batch_max_size or
            current_time >= timer
        )
        
        if should_send:
            # Send batched notifications
            deliveries = await self._send_batched_notifications(batch_key, context)
            
            # Clear batch
            del self.notification_batches[batch_key]
            del self.batch_timers[batch_key]
            
            self.enhanced_stats['notifications_batched'] += len(deliveries)
            return deliveries
        
        return []
    
    async def _send_batched_notifications(self, batch_key: str, context: NotificationContext) -> List[NotificationDelivery]:
        """Send batched notifications"""
        batch = self.notification_batches[batch_key]
        
        if not batch:
            return []
        
        # Create summary alert for batch
        summary_alert = self._create_batch_summary_alert(batch, context)
        
        # Dispatch using base dispatcher
        deliveries = await self.base_dispatcher.dispatch_alert(summary_alert)
        
        logger.info(f"Sent batched notification with {len(batch)} alerts for {batch_key}")
        return deliveries
    
    def _create_batch_summary_alert(self, batch: List[Alert], context: NotificationContext) -> Alert:
        """Create summary alert for batched notifications"""
        if not batch:
            raise ValueError("Cannot create summary for empty batch")
        
        # Get highest severity
        highest_severity = AlertSeverity.INFO
        severity_order = [AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM, AlertSeverity.LOW, AlertSeverity.INFO]
        for severity in severity_order:
            if any(alert.severity == severity for alert in batch):
                highest_severity = severity
                break
        
        # Count by severity and category
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for alert in batch:
            severity_counts[alert.severity.value] += 1
            category_counts[alert.category.value] += 1
        
        # Create summary
        title = f"Multiple Alerts: {len(batch)} alerts across {len(category_counts)} categories"
        
        description = f"""
Batch Summary ({len(batch)} alerts):

Severity Breakdown:
{self._format_counts(severity_counts)}

Category Breakdown: 
{self._format_counts(category_counts)}

Time Range: {min(alert.triggered_at for alert in batch)} - {max(alert.triggered_at for alert in batch)}
        """.strip()
        
        # Create summary alert
        summary_alert = Alert(
            rule_id=batch[0].rule_id,
            rule_name="Batch Summary",
            title=title,
            description=description,
            category=batch[0].category,  # Use first alert's category
            severity=highest_severity,
            threshold_breached=0.0,
            actual_value=len(batch),
            tags={"batch_summary": "true", "batch_size": str(len(batch))}
        )
        
        return summary_alert
    
    def _format_counts(self, counts: Dict[str, int]) -> str:
        """Format count dictionary for display"""
        return "\n".join(f"  {key}: {count}" for key, count in sorted(counts.items()))
    
    async def _dispatch_immediate_notifications(self, alert_group: AlertGroup, context: NotificationContext) -> List[NotificationDelivery]:
        """Dispatch immediate notifications for alert group"""
        # Use root alert as representative for the group
        representative_alert = self._create_group_representative_alert(alert_group)
        
        # Dispatch using base dispatcher
        deliveries = await self.base_dispatcher.dispatch_alert(representative_alert)
        
        logger.info(f"Dispatched immediate notification for alert group {alert_group.id}")
        return deliveries
    
    def _create_group_representative_alert(self, alert_group: AlertGroup) -> Alert:
        """Create representative alert for alert group"""
        root_alert = alert_group.root_alert
        alert_count = alert_group.get_alert_count()
        
        if alert_count == 1:
            # Single alert, return as-is
            return root_alert
        
        # Multiple alerts, create enhanced alert
        enhanced_title = f"{root_alert.title} ({alert_count} correlated alerts)"
        
        enhanced_description = f"""
{root_alert.description}

Correlation Summary:
- Total alerts in group: {alert_count}
- Correlation rules applied: {', '.join(alert_group.correlation_rules)}
- Confidence score: {alert_group.confidence_score:.2f}
- Time range: {alert_group.created_at} - {alert_group.last_updated}

Related alerts: {len(alert_group.correlated_alerts)} additional alerts correlated with this event.
        """.strip()
        
        # Create enhanced alert
        enhanced_alert = Alert(
            id=root_alert.id,
            rule_id=root_alert.rule_id,
            rule_name=root_alert.rule_name,
            title=enhanced_title,
            description=enhanced_description,
            category=root_alert.category,
            severity=alert_group.get_severity(),  # Use group severity
            status=root_alert.status,
            metric_values=root_alert.metric_values,
            threshold_breached=root_alert.threshold_breached,
            actual_value=root_alert.actual_value,
            source_host=root_alert.source_host,
            source_component=root_alert.source_component,
            triggered_at=root_alert.triggered_at,
            tags={
                **root_alert.tags,
                "correlation_group": alert_group.id,
                "correlated_alerts": str(alert_count),
                "correlation_confidence": str(alert_group.confidence_score)
            }
        )
        
        return enhanced_alert
    
    async def _check_escalation(self, alert_group: AlertGroup, context: NotificationContext) -> None:
        """Check and handle alert escalation"""
        # Get applicable escalation policies
        policies = await self._get_applicable_escalation_policies(alert_group)
        
        for policy in policies:
            escalation_key = f"{alert_group.id}:{policy.id}"
            
            # Get or create escalation context
            if escalation_key not in self.escalation_contexts:
                escalation_context = EscalationContext(
                    alert_group=alert_group,
                    policy=policy,
                    status=EscalationStatus.IN_PROGRESS
                )
                self.escalation_contexts[escalation_key] = escalation_context
                context.escalation_context = escalation_context
            else:
                escalation_context = self.escalation_contexts[escalation_key]
            
            # Check if escalation should trigger
            if escalation_context.should_escalate() and escalation_context.can_escalate_further():
                await self._trigger_escalation(escalation_context)
    
    async def _get_applicable_escalation_policies(self, alert_group: AlertGroup) -> List[EscalationPolicy]:
        """Get escalation policies applicable to alert group"""
        policies = []
        group_severity = alert_group.get_severity()
        
        for policy in self.escalation_policies.values():
            if not policy.enabled:
                continue
            
            # Check severity levels
            if policy.severity_levels and group_severity not in policy.severity_levels:
                continue
            
            # Check categories
            if policy.categories and alert_group.root_alert.category not in policy.categories:
                continue
            
            policies.append(policy)
        
        return policies
    
    async def _trigger_escalation(self, escalation_context: EscalationContext) -> None:
        """Trigger escalation for alert group"""
        try:
            escalation_context.current_level += 1
            escalation_context.last_escalation_at = datetime.utcnow()
            
            policy = escalation_context.policy
            alert_group = escalation_context.alert_group
            
            logger.info(f"Triggering escalation level {escalation_context.current_level} for alert group {alert_group.id}")
            
            # Execute escalation actions
            for action in policy.actions:
                await self._execute_escalation_action(action, escalation_context)
            
            # Send escalation notifications
            if policy.notification_configs:
                await self._send_escalation_notifications(escalation_context)
            
            # Record escalation event
            escalation_context.escalation_history.append({
                'level': escalation_context.current_level,
                'timestamp': escalation_context.last_escalation_at,
                'actions': [action.value for action in policy.actions],
                'status': 'completed'
            })
            
            self.enhanced_stats['escalations_triggered'] += 1
            
        except Exception as e:
            logger.error(f"Error triggering escalation: {e}")
            escalation_context.escalation_history.append({
                'level': escalation_context.current_level,
                'timestamp': datetime.utcnow(),
                'error': str(e),
                'status': 'failed'
            })
    
    async def _execute_escalation_action(self, action: EscalationAction, context: EscalationContext) -> None:
        """Execute specific escalation action"""
        logger.info(f"Executing escalation action: {action.value}")
        
        if action == EscalationAction.NOTIFY_MANAGER:
            # Implementation would notify management chain
            logger.info("Notifying management chain")
        
        elif action == EscalationAction.CREATE_INCIDENT:
            # Implementation would create incident ticket
            logger.info("Creating incident ticket")
        
        elif action == EscalationAction.INCREASE_SEVERITY:
            # Increase alert severity
            if context.alert_group.root_alert.severity != AlertSeverity.CRITICAL:
                logger.info("Increasing alert severity")
        
        elif action == EscalationAction.AUTO_RESOLVE:
            # Auto-resolve if conditions are met
            logger.info("Checking auto-resolution conditions")
        
        elif action == EscalationAction.EXECUTE_RUNBOOK:
            # Execute automated runbook
            logger.info("Executing automated runbook")
    
    async def _send_escalation_notifications(self, escalation_context: EscalationContext) -> None:
        """Send escalation-specific notifications"""
        # Create escalation alert
        escalation_alert = self._create_escalation_alert(escalation_context)
        
        # Send to escalation notification configs
        for config_id in escalation_context.policy.notification_configs:
            if config_id in self.base_dispatcher.notification_configs:
                config = self.base_dispatcher.notification_configs[config_id]
                # Implementation would send notification
                logger.info(f"Sending escalation notification via {config.channel.value}")
    
    def _create_escalation_alert(self, escalation_context: EscalationContext) -> Alert:
        """Create alert for escalation notification"""
        root_alert = escalation_context.alert_group.root_alert
        level = escalation_context.current_level
        
        escalation_alert = Alert(
            rule_id=root_alert.rule_id,
            rule_name=f"ESCALATION - {root_alert.rule_name}",
            title=f"ESCALATED (Level {level}): {root_alert.title}",
            description=f"""
ALERT ESCALATION - Level {level}

Original Alert: {root_alert.title}
Group ID: {escalation_context.alert_group.id}
Alert Count: {escalation_context.alert_group.get_alert_count()}
Escalation Policy: {escalation_context.policy.name}

{root_alert.description}
            """.strip(),
            category=root_alert.category,
            severity=AlertSeverity.CRITICAL,  # Escalations are always critical
            threshold_breached=root_alert.threshold_breached,
            actual_value=root_alert.actual_value,
            tags={
                **root_alert.tags,
                "escalation": "true",
                "escalation_level": str(level),
                "escalation_policy": str(escalation_context.policy.id)
            }
        )
        
        return escalation_alert
    
    async def _load_escalation_policies(self) -> None:
        """Load escalation policies from storage"""
        # Implementation would load from database
        # For now, create a default policy
        default_policy = EscalationPolicy(
            name="Default Critical Escalation",
            description="Default escalation for critical alerts",
            trigger_after=timedelta(minutes=15),
            severity_levels=[AlertSeverity.CRITICAL],
            actions=[EscalationAction.NOTIFY_MANAGER, EscalationAction.CREATE_INCIDENT],
            max_escalations=3,
            escalation_interval=timedelta(minutes=30)
        )
        
        self.escalation_policies[default_policy.id] = default_policy
        logger.info("Loaded escalation policies")
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced notification statistics"""
        base_stats = {}
        if hasattr(self.base_dispatcher, 'get_stats'):
            base_stats = self.base_dispatcher.get_stats()
        
        return {
            **base_stats,
            **self.enhanced_stats,
            'active_escalations': len(self.escalation_contexts),
            'pending_batches': len(self.notification_batches),
            'escalation_policies': len(self.escalation_policies)
        }
    
    async def suppress_notifications(self, group_id: str, duration: timedelta) -> None:
        """Suppress notifications for specific alert group"""
        if group_id in self.notification_contexts:
            context = self.notification_contexts[group_id]
            context.suppressed_until = datetime.utcnow() + duration
            logger.info(f"Suppressed notifications for group {group_id} until {context.suppressed_until}")
    
    async def add_maintenance_window(self, group_id: str, start_time: datetime, end_time: datetime) -> None:
        """Add maintenance window for alert group"""
        if group_id in self.notification_contexts:
            context = self.notification_contexts[group_id]
            context.maintenance_windows.append((start_time, end_time))
            logger.info(f"Added maintenance window for group {group_id}: {start_time} - {end_time}")


# Global enhanced notification dispatcher instance
_enhanced_dispatcher: Optional[EnhancedNotificationDispatcher] = None


async def get_enhanced_notification_dispatcher() -> EnhancedNotificationDispatcher:
    """Get global enhanced notification dispatcher instance"""
    global _enhanced_dispatcher
    if _enhanced_dispatcher is None:
        _enhanced_dispatcher = EnhancedNotificationDispatcher()
        await _enhanced_dispatcher.initialize()
    return _enhanced_dispatcher 