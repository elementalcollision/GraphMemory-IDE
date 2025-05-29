"""
Alert Engine - Core alerting logic with threshold monitoring and rule evaluation.

This module provides the central AlertEngine class that:
- Monitors performance metrics from the Performance Manager
- Evaluates alert rules and threshold conditions
- Generates alerts with deduplication logic
- Integrates with notification and caching systems

Created as part of Step 8: Real-time Alerting & Notification System
Research foundation: Exa + Context7 + Sequential Thinking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from uuid import UUID, uuid4
from collections import defaultdict, deque

from server.dashboard.models.alert_models import (
    Alert, AlertRule, AlertSeverity, AlertStatus, AlertCategory, 
    MetricType, ComparisonOperator, ThresholdCondition, AlertMetrics,
    AlertSystemConfig, AlertEvent
)
from server.dashboard.performance_manager import get_performance_manager, PerformanceManager
from server.dashboard.cache_manager import get_cache_manager, CacheManager
from server.dashboard.enhanced_circuit_breaker import get_circuit_breaker_manager, CircuitBreakerManager
from server.dashboard.notification_dispatcher import get_notification_dispatcher, NotificationDispatcher

# Configure logging
logger = logging.getLogger(__name__)


class MetricEvaluator:
    """Evaluates metrics against defined thresholds"""
    
    def __init__(self):
        self.evaluation_cache = {}
        self.last_cleanup = datetime.utcnow()
    
    def evaluate_condition(self, condition: ThresholdCondition, metric_value: float) -> bool:
        """Evaluate a single threshold condition"""
        try:
            if condition.operator == ComparisonOperator.GREATER_THAN:
                return metric_value > condition.value
            elif condition.operator == ComparisonOperator.GREATER_EQUAL:
                return metric_value >= condition.value
            elif condition.operator == ComparisonOperator.LESS_THAN:
                return metric_value < condition.value
            elif condition.operator == ComparisonOperator.LESS_EQUAL:
                return metric_value <= condition.value
            elif condition.operator == ComparisonOperator.EQUAL:
                return abs(metric_value - condition.value) < 0.001  # Float comparison
            elif condition.operator == ComparisonOperator.NOT_EQUAL:
                return abs(metric_value - condition.value) >= 0.001
            else:
                logger.warning(f"Unknown comparison operator: {condition.operator}")
                return False
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def evaluate_rule(self, rule: AlertRule, metric_values: Dict[str, float]) -> Tuple[bool, Dict[str, float]]:
        """Evaluate all conditions in an alert rule"""
        if not rule.enabled:
            return False, {}
        
        relevant_metrics = {}
        all_conditions_met = True
        
        for condition in rule.conditions:
            metric_key = condition.metric_type.value
            if metric_key not in metric_values:
                logger.debug(f"Metric {metric_key} not found in metric values")
                all_conditions_met = False
                continue
            
            metric_value = metric_values[metric_key]
            relevant_metrics[metric_key] = metric_value
            
            condition_met = self.evaluate_condition(condition, metric_value)
            if not condition_met:
                all_conditions_met = False
                break
        
        return all_conditions_met, relevant_metrics
    
    def cleanup_cache(self):
        """Clean up old evaluation cache entries"""
        now = datetime.utcnow()
        if (now - self.last_cleanup).total_seconds() > 300:  # Cleanup every 5 minutes
            # Keep only recent entries (last hour)
            cutoff = now - timedelta(hours=1)
            self.evaluation_cache = {
                k: v for k, v in self.evaluation_cache.items() 
                if v.get('timestamp', cutoff) > cutoff
            }
            self.last_cleanup = now


class AlertGenerator:
    """Generates alerts with deduplication logic"""
    
    def __init__(self, config: AlertSystemConfig):
        self.config = config
        self.active_alerts: Dict[UUID, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.breach_tracking: Dict[UUID, List[datetime]] = defaultdict(list)
    
    def should_generate_alert(self, rule: AlertRule, metric_values: Dict[str, float]) -> bool:
        """Check if an alert should be generated based on breach tracking"""
        rule_id = rule.id
        now = datetime.utcnow()
        
        # Track this breach
        breaches = self.breach_tracking[rule_id]
        breaches.append(now)
        
        # Remove old breaches outside evaluation window
        cutoff = now - rule.evaluation_window
        breaches[:] = [breach for breach in breaches if breach > cutoff]
        
        # Check if we have enough consecutive breaches
        return len(breaches) >= rule.consecutive_breaches
    
    def check_alert_cooldown(self, rule: AlertRule) -> bool:
        """Check if alert is in cooldown period"""
        rule_id = rule.id
        
        # Check if there's an active alert for this rule
        for alert in self.active_alerts.values():
            if alert.rule_id == rule_id and alert.status == AlertStatus.ACTIVE:
                time_since_triggered = datetime.utcnow() - alert.triggered_at
                if time_since_triggered < rule.cooldown_period:
                    return True
        
        # Check recent resolved alerts
        cutoff = datetime.utcnow() - rule.cooldown_period
        recent_alerts = [
            alert for alert in self.alert_history 
            if (alert.get('rule_id') == rule_id and 
                alert.get('resolved_at', datetime.min) > cutoff)
        ]
        return len(recent_alerts) > 0
    
    def check_rate_limit(self, rule: AlertRule) -> bool:
        """Check if alert generation rate limit is exceeded"""
        rule_id = rule.id
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=1)
        
        # Count alerts for this rule in the last hour
        alert_count = sum(1 for alert in self.alert_history 
                         if (alert.get('rule_id') == rule_id and 
                             alert.get('triggered_at', datetime.min) > cutoff))
        
        return alert_count >= rule.max_alerts_per_hour
    
    def generate_alert(self, rule: AlertRule, metric_values: Dict[str, float], 
                      relevant_metrics: Dict[str, float]) -> Optional[Alert]:
        """Generate a new alert from rule and metrics"""
        try:
            # Find the main threshold that was breached
            primary_condition = rule.conditions[0]  # Use first condition as primary
            primary_metric = primary_condition.metric_type.value
            threshold_value = primary_condition.value
            actual_value = relevant_metrics.get(primary_metric, 0.0)
            
            # Create alert
            alert = Alert(
                rule_id=rule.id,
                rule_name=rule.name,
                title=f"{rule.name} - {rule.severity.value.upper()}",
                description=self._generate_alert_description(rule, relevant_metrics),
                category=rule.category,
                severity=rule.severity,
                metric_values=relevant_metrics,
                threshold_breached=threshold_value,
                actual_value=actual_value,
                tags=rule.tags.copy()
            )
            
            # Store in active alerts
            self.active_alerts[alert.id] = alert
            
            # Add to history
            self.alert_history.append({
                'id': alert.id,
                'rule_id': rule.id,
                'triggered_at': alert.triggered_at,
                'severity': alert.severity,
                'resolved_at': None
            })
            
            logger.info(f"Generated alert: {alert.title} (ID: {alert.id})")
            return alert
            
        except Exception as e:
            logger.error(f"Error generating alert for rule {rule.name}: {e}")
            return None
    
    def _generate_alert_description(self, rule: AlertRule, metrics: Dict[str, float]) -> str:
        """Generate alert description based on rule and metrics"""
        if rule.description:
            base_description = rule.description
        else:
            base_description = f"Alert triggered for {rule.name}"
        
        # Add metric details
        metric_details = []
        for condition in rule.conditions:
            metric_key = condition.metric_type.value
            if metric_key in metrics:
                value = metrics[metric_key]
                unit = condition.unit or ""
                metric_details.append(f"{metric_key}: {value:.2f}{unit}")
        
        if metric_details:
            return f"{base_description}\n\nCurrent values:\n" + "\n".join(metric_details)
        
        return base_description
    
    def resolve_alert(self, alert_id: UUID, user: str = "system", note: Optional[str] = None):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolve(user, note)
            
            # Update history
            for hist_alert in self.alert_history:
                if hist_alert.get('id') == alert_id:
                    hist_alert['resolved_at'] = alert.resolved_at
                    break
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            logger.info(f"Resolved alert: {alert.title} (ID: {alert_id})")
    
    def cleanup_expired_alerts(self):
        """Clean up old alerts and tracking data"""
        now = datetime.utcnow()
        
        # Clean up breach tracking (keep only recent data)
        for rule_id, breaches in list(self.breach_tracking.items()):
            cutoff = now - timedelta(hours=2)
            breaches[:] = [breach for breach in breaches if breach > cutoff]
            if not breaches:
                del self.breach_tracking[rule_id]


class AlertEngine:
    """Main alerting engine with threshold monitoring"""
    
    def __init__(self, config: Optional[AlertSystemConfig] = None):
        self.config = config or AlertSystemConfig()
        self.is_running = False
        self.evaluation_task: Optional[asyncio.Task] = None
        
        # Components
        self.evaluator = MetricEvaluator()
        self.generator = AlertGenerator(self.config)
        
        # External dependencies
        self.performance_manager: Optional[PerformanceManager] = None
        self.cache_manager: Optional[CacheManager] = None
        self.circuit_breaker_manager: Optional[CircuitBreakerManager] = None
        self.notification_dispatcher: Optional[NotificationDispatcher] = None
        
        # Alert rules storage
        self.alert_rules: Dict[UUID, AlertRule] = {}
        
        # Metrics and monitoring
        self.metrics = AlertMetrics()
        self.last_metrics_update = datetime.utcnow()
        
        # Event callbacks
        self.alert_callbacks: List[Callable] = []
        
        logger.info("AlertEngine initialized")
    
    async def initialize(self):
        """Initialize the alert engine with dependencies"""
        try:
            # Get external dependencies
            self.performance_manager = await get_performance_manager()
            self.cache_manager = await get_cache_manager()
            self.circuit_breaker_manager = get_circuit_breaker_manager()
            self.notification_dispatcher = await get_notification_dispatcher()
            
            # Load default alert rules
            await self._load_default_rules()
            
            logger.info("AlertEngine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AlertEngine: {e}")
            raise
    
    async def start(self):
        """Start the alert engine evaluation loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())
        logger.info("AlertEngine started")
    
    async def stop(self):
        """Stop the alert engine"""
        self.is_running = False
        
        if self.evaluation_task and not self.evaluation_task.done():
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("AlertEngine stopped")
    
    async def _evaluation_loop(self):
        """Main evaluation loop that checks metrics and generates alerts"""
        logger.info("Starting alert evaluation loop")
        
        while self.is_running:
            try:
                # Get current metrics from performance manager
                metrics = await self._get_current_metrics()
                
                if metrics:
                    # Evaluate all enabled rules
                    await self._evaluate_rules(metrics)
                
                # Update system metrics
                await self._update_system_metrics()
                
                # Cleanup old data
                self._cleanup()
                
                # Wait for next evaluation
                await asyncio.sleep(self.config.evaluation_interval.total_seconds())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _get_current_metrics(self) -> Dict[str, float]:
        """Get current metrics from performance manager"""
        try:
            if not self.performance_manager:
                return {}
            
            # Get current metrics from performance manager
            resource_metrics = self.performance_manager.get_current_metrics()
            
            # Convert to flat metric dictionary
            metrics = {}
            
            # System metrics from performance manager
            if resource_metrics:
                if hasattr(resource_metrics, 'cpu_usage_percent'):
                    metrics['cpu_usage'] = resource_metrics.cpu_usage_percent
                if hasattr(resource_metrics, 'memory_usage_percent'):
                    metrics['memory_usage'] = resource_metrics.memory_usage_percent
                if hasattr(resource_metrics, 'memory_used_mb'):
                    # Calculate memory percentage if not directly available
                    if hasattr(resource_metrics, 'memory_total_mb') and resource_metrics.memory_total_mb > 0:
                        metrics['memory_usage'] = (resource_metrics.memory_used_mb / resource_metrics.memory_total_mb) * 100
                
                # Connection metrics
                if hasattr(resource_metrics, 'active_connections'):
                    metrics['connection_count'] = resource_metrics.active_connections
            
            # Performance metrics from cache manager
            if self.cache_manager:
                cache_metrics = await self.cache_manager.get_metrics()
                if hasattr(cache_metrics, 'get_hit_rate'):
                    metrics['cache_hit_rate'] = cache_metrics.get_hit_rate() * 100  # Convert to percentage
                elif 'hit_rate' in cache_metrics:
                    # If it's a dict response
                    metrics['cache_hit_rate'] = cache_metrics['hit_rate'] * 100
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {}
    
    async def _evaluate_rules(self, metrics: Dict[str, float]):
        """Evaluate all alert rules against current metrics"""
        alerts_generated = 0
        
        for rule in self.alert_rules.values():
            try:
                if not rule.enabled:
                    continue
                
                # Check if rule applies to current metrics
                conditions_met, relevant_metrics = self.evaluator.evaluate_rule(rule, metrics)
                
                if conditions_met:
                    # Check if we should generate an alert
                    if self.generator.should_generate_alert(rule, metrics):
                        # Check cooldowns and rate limits
                        if (self.generator.check_alert_cooldown(rule) or 
                            self.generator.check_rate_limit(rule)):
                            continue
                        
                        # Generate alert
                        alert = self.generator.generate_alert(rule, metrics, relevant_metrics)
                        if alert:
                            alerts_generated += 1
                            await self._handle_new_alert(alert)
                
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
        
        if alerts_generated > 0:
            logger.info(f"Generated {alerts_generated} new alerts")
    
    async def _handle_new_alert(self, alert: Alert):
        """Handle a newly generated alert"""
        try:
            # Cache the alert
            if self.cache_manager:
                cache_key = f"alert:{alert.id}"
                await self.cache_manager.set(cache_key, alert.dict(), ttl=3600)
            
            # Dispatch notifications
            if self.notification_dispatcher:
                deliveries = await self.notification_dispatcher.dispatch_alert(alert)
                logger.info(f"Alert {alert.id} dispatched to {len(deliveries)} notification channels")
            
            # Create alert event
            event = AlertEvent(
                event_type="alert_created",
                alert=alert,
                timestamp=alert.triggered_at
            )
            
            # Notify callbacks
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
        except Exception as e:
            logger.error(f"Error handling new alert: {e}")
    
    async def _update_system_metrics(self):
        """Update alert system metrics"""
        try:
            now = datetime.utcnow()
            
            # Update basic counts
            self.metrics.active_alerts = len(self.generator.active_alerts)
            self.metrics.total_alerts = len(self.generator.alert_history)
            
            # Calculate counts by severity
            severity_counts = defaultdict(int)
            for alert in self.generator.active_alerts.values():
                severity_counts[alert.severity] += 1
            
            self.metrics.critical_alerts = severity_counts[AlertSeverity.CRITICAL]
            self.metrics.high_alerts = severity_counts[AlertSeverity.HIGH]
            self.metrics.medium_alerts = severity_counts[AlertSeverity.MEDIUM]
            self.metrics.low_alerts = severity_counts[AlertSeverity.LOW]
            
            # Calculate alert rate
            if self.last_metrics_update:
                time_diff = (now - self.last_metrics_update).total_seconds() / 3600  # hours
                if time_diff > 0:
                    new_alerts = sum(1 for alert in self.generator.alert_history 
                                   if alert.get('triggered_at', datetime.min) > self.last_metrics_update)
                    self.metrics.alert_rate_per_hour = new_alerts / time_diff
            
            # System health
            self.metrics.alert_engine_health = 100.0 if self.is_running else 0.0
            
            self.metrics.timestamp = now
            self.last_metrics_update = now
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def _cleanup(self):
        """Cleanup old data and maintain system health"""
        try:
            self.evaluator.cleanup_cache()
            self.generator.cleanup_expired_alerts()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _load_default_rules(self):
        """Load default alert rules"""
        try:
            # High CPU usage alert
            cpu_rule = AlertRule(
                name="High CPU Usage",
                description="Alert when CPU usage exceeds 85%",
                category=AlertCategory.PERFORMANCE,
                severity=AlertSeverity.HIGH,
                conditions=[
                    ThresholdCondition(
                        metric_type=MetricType.CPU_USAGE,
                        operator=ComparisonOperator.GREATER_EQUAL,
                        value=85.0,
                        unit="%",
                        description="CPU usage >= 85%"
                    )
                ],
                evaluation_window=timedelta(minutes=5),
                consecutive_breaches=2
            )
            
            # High memory usage alert
            memory_rule = AlertRule(
                name="High Memory Usage",
                description="Alert when memory usage exceeds 90%",
                category=AlertCategory.PERFORMANCE,
                severity=AlertSeverity.HIGH,
                conditions=[
                    ThresholdCondition(
                        metric_type=MetricType.MEMORY_USAGE,
                        operator=ComparisonOperator.GREATER_EQUAL,
                        value=90.0,
                        unit="%",
                        description="Memory usage >= 90%"
                    )
                ],
                evaluation_window=timedelta(minutes=3),
                consecutive_breaches=3
            )
            
            # Low cache hit rate alert
            cache_rule = AlertRule(
                name="Low Cache Hit Rate",
                description="Alert when cache hit rate falls below 70%",
                category=AlertCategory.PERFORMANCE,
                severity=AlertSeverity.MEDIUM,
                conditions=[
                    ThresholdCondition(
                        metric_type=MetricType.CACHE_HIT_RATE,
                        operator=ComparisonOperator.LESS_THAN,
                        value=70.0,
                        unit="%",
                        description="Cache hit rate < 70%"
                    )
                ],
                evaluation_window=timedelta(minutes=10),
                consecutive_breaches=2
            )
            
            # Store rules
            self.alert_rules[cpu_rule.id] = cpu_rule
            self.alert_rules[memory_rule.id] = memory_rule
            self.alert_rules[cache_rule.id] = cache_rule
            
            logger.info(f"Loaded {len(self.alert_rules)} default alert rules")
            
        except Exception as e:
            logger.error(f"Error loading default rules: {e}")
    
    # Public API methods
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for alert events"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable):
        """Remove alert callback"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def add_rule(self, rule: AlertRule) -> bool:
        """Add a new alert rule"""
        try:
            self.alert_rules[rule.id] = rule
            
            # Cache the rule
            if self.cache_manager:
                cache_key = f"alert_rule:{rule.id}"
                await self.cache_manager.set(cache_key, rule.dict(), ttl=7200)
            
            logger.info(f"Added alert rule: {rule.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding alert rule: {e}")
            return False
    
    async def remove_rule(self, rule_id: UUID) -> bool:
        """Remove an alert rule"""
        try:
            if rule_id in self.alert_rules:
                rule = self.alert_rules[rule_id]
                del self.alert_rules[rule_id]
                
                # Remove from cache
                if self.cache_manager:
                    cache_key = f"alert_rule:{rule_id}"
                    await self.cache_manager.delete(cache_key)
                
                logger.info(f"Removed alert rule: {rule.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing alert rule: {e}")
            return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.generator.active_alerts.values())
    
    def get_alert_by_id(self, alert_id: UUID) -> Optional[Alert]:
        """Get alert by ID"""
        return self.generator.active_alerts.get(alert_id)
    
    async def acknowledge_alert(self, alert_id: UUID, user: str, note: Optional[str] = None) -> bool:
        """Acknowledge an alert"""
        try:
            alert = self.generator.active_alerts.get(alert_id)
            if alert:
                alert.acknowledge(user, note)
                
                # Update cache
                if self.cache_manager:
                    cache_key = f"alert:{alert_id}"
                    await self.cache_manager.set(cache_key, alert.dict(), ttl=3600)
                
                # Create event
                event = AlertEvent(
                    event_type="alert_acknowledged",
                    alert=alert,
                    user_id=user
                )
                
                # Notify callbacks
                for callback in self.alert_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    async def resolve_alert(self, alert_id: UUID, user: str, note: Optional[str] = None) -> bool:
        """Resolve an alert"""
        try:
            alert = self.generator.active_alerts.get(alert_id)
            if alert:
                self.generator.resolve_alert(alert_id, user, note)
                
                # Update cache
                if self.cache_manager:
                    cache_key = f"alert:{alert_id}"
                    await self.cache_manager.set(cache_key, alert.dict(), ttl=3600)
                
                # Create event
                event = AlertEvent(
                    event_type="alert_resolved",
                    alert=alert,
                    user_id=user
                )
                
                # Notify callbacks
                for callback in self.alert_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_metrics(self) -> AlertMetrics:
        """Get current alert system metrics"""
        return self.metrics
    
    def get_rules(self) -> List[AlertRule]:
        """Get all alert rules"""
        return list(self.alert_rules.values())


# Global alert engine instance
_alert_engine: Optional[AlertEngine] = None


async def get_alert_engine() -> AlertEngine:
    """Get the global alert engine instance"""
    global _alert_engine
    
    if _alert_engine is None:
        _alert_engine = AlertEngine()
        await _alert_engine.initialize()
    
    return _alert_engine


async def initialize_alert_engine(config: Optional[AlertSystemConfig] = None) -> AlertEngine:
    """Initialize the global alert engine"""
    global _alert_engine
    
    if _alert_engine is not None:
        await _alert_engine.stop()
    
    _alert_engine = AlertEngine(config)
    await _alert_engine.initialize()
    await _alert_engine.start()
    
    return _alert_engine


async def shutdown_alert_engine():
    """Shutdown the global alert engine"""
    global _alert_engine
    
    if _alert_engine is not None:
        await _alert_engine.stop()
        _alert_engine = None


# Export main classes and functions
__all__ = [
    'AlertEngine',
    'MetricEvaluator', 
    'AlertGenerator',
    'get_alert_engine',
    'initialize_alert_engine',
    'shutdown_alert_engine'
] 