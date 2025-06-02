"""
Production Alert Rules for GraphMemory-IDE Monitoring System

This module provides comprehensive production-ready alert rules:
- SLI-based alerting for API performance and reliability
- Database health and connection monitoring with thresholds
- Resource utilization monitoring with predictive thresholds
- Business metric alerts for user activity and error patterns
- System health and availability monitoring
- Security and compliance monitoring

Implementation based on research findings from:
- Google SRE practices and SLI/SLO frameworks
- Production monitoring best practices from DataDog, NewRelic
- Modern alerting strategies and threshold optimization
- Real-world production incident patterns

Created for TASK-022 Phase 1: Enhanced Alerting & Notification System
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from server.dashboard.models.alert_models import (
    AlertRule, AlertSeverity, AlertCategory, ThresholdCondition, 
    MetricType, ComparisonOperator
)

logger = logging.getLogger(__name__)


class ProductionAlertRules:
    """Production-ready alert rules manager"""
    
    def __init__(self) -> None:
        self.alert_rules: Dict[str, AlertRule] = {}
        self._initialize_production_rules()
        
        logger.info("ProductionAlertRules initialized with comprehensive monitoring rules")
    
    def _initialize_production_rules(self) -> None:
        """Initialize all production alert rules"""
        
        # API Performance & SLI Rules
        self._create_api_performance_rules()
        
        # Database Health Rules
        self._create_database_health_rules()
        
        # System Resource Rules
        self._create_system_resource_rules()
        
        # Business Metric Rules
        self._create_business_metric_rules()
        
        # Security & Compliance Rules
        self._create_security_rules()
        
        # Application Health Rules
        self._create_application_health_rules()
        
        logger.info(f"Initialized {len(self.alert_rules)} production alert rules")
    
    def _create_api_performance_rules(self) -> None:
        """Create SLI-based API performance alert rules"""
        
        # Critical: API Response Time P95 > 5 seconds
        self.add_rule(AlertRule(
            name="API Response Time Critical",
            description="API P95 response time exceeds 5 seconds - SLI breach",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.RESPONSE_TIME,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=5.0,
                    unit="seconds",
                    description="P95 response time threshold"
                )
            ],
            evaluation_window=timedelta(minutes=2),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=10),
            max_alerts_per_hour=6,
            tags={
                "sli": "latency",
                "percentile": "p95",
                "team": "platform",
                "runbook": "https://wiki.company.com/runbooks/api-latency"
            }
        ))
        
        # High: API Response Time P95 > 2 seconds
        self.add_rule(AlertRule(
            name="API Response Time High",
            description="API P95 response time exceeds 2 seconds - performance degradation",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.RESPONSE_TIME,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=2.0,
                    unit="seconds",
                    description="P95 response time warning threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=3,
            cooldown_period=timedelta(minutes=15),
            max_alerts_per_hour=4,
            tags={
                "sli": "latency",
                "percentile": "p95",
                "team": "platform",
                "severity": "warning"
            }
        ))
        
        # Critical: API Error Rate > 5%
        self.add_rule(AlertRule(
            name="API Error Rate Critical",
            description="API error rate exceeds 5% - SLI breach affecting availability",
            category=AlertCategory.AVAILABILITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.ERROR_RATE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=5.0,
                    unit="%",
                    description="Critical error rate threshold"
                )
            ],
            evaluation_window=timedelta(minutes=3),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=10),
            max_alerts_per_hour=8,
            tags={
                "sli": "availability",
                "metric": "error_rate",
                "team": "platform",
                "priority": "p0"
            }
        ))
        
        # High: API Error Rate > 2%
        self.add_rule(AlertRule(
            name="API Error Rate High",
            description="API error rate exceeds 2% - degraded service quality",
            category=AlertCategory.AVAILABILITY,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.ERROR_RATE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=2.0,
                    unit="%",
                    description="Warning error rate threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=15),
            max_alerts_per_hour=6,
            tags={
                "sli": "availability",
                "metric": "error_rate",
                "team": "platform",
                "priority": "p1"
            }
        ))
    
    def _create_database_health_rules(self) -> None:
        """Create database health and connection monitoring rules"""
        
        # Critical: Database Connection Pool Exhausted
        self.add_rule(AlertRule(
            name="Database Connection Pool Critical",
            description="Database connection pool utilization exceeds 95% - potential service outage",
            category=AlertCategory.CAPACITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CONNECTION_COUNT,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=95.0,
                    unit="%",
                    description="Connection pool utilization threshold"
                )
            ],
            evaluation_window=timedelta(minutes=2),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=5),
            max_alerts_per_hour=12,
            tags={
                "component": "database",
                "metric": "connections",
                "team": "data",
                "priority": "p0"
            }
        ))
        
        # High: Database Connection Pool High Usage
        self.add_rule(AlertRule(
            name="Database Connection Pool High",
            description="Database connection pool utilization exceeds 80% - approaching capacity",
            category=AlertCategory.CAPACITY,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CONNECTION_COUNT,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=80.0,
                    unit="%",
                    description="Connection pool warning threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=3,
            cooldown_period=timedelta(minutes=15),
            max_alerts_per_hour=6,
            tags={
                "component": "database",
                "metric": "connections",
                "team": "data",
                "priority": "p1"
            }
        ))
        
        # Critical: Database Query Performance Degradation
        self.add_rule(AlertRule(
            name="Database Query Performance Critical",
            description="Database query P95 latency exceeds 10 seconds - severe performance impact",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.RESPONSE_TIME,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=10.0,
                    unit="seconds",
                    description="Database query P95 latency threshold"
                )
            ],
            evaluation_window=timedelta(minutes=3),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=10),
            max_alerts_per_hour=6,
            tags={
                "component": "database",
                "metric": "query_latency",
                "percentile": "p95",
                "team": "data"
            }
        ))
        
        # Medium: Cache Hit Rate Low
        self.add_rule(AlertRule(
            name="Cache Hit Rate Low",
            description="Cache hit rate below 80% - potential performance impact",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.MEDIUM,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CACHE_HIT_RATE,
                    operator=ComparisonOperator.LESS_THAN,
                    value=80.0,
                    unit="%",
                    description="Cache efficiency threshold"
                )
            ],
            evaluation_window=timedelta(minutes=10),
            consecutive_breaches=3,
            cooldown_period=timedelta(minutes=30),
            max_alerts_per_hour=3,
            tags={
                "component": "cache",
                "metric": "hit_rate",
                "team": "platform",
                "optimization": "performance"
            }
        ))
    
    def _create_system_resource_rules(self) -> None:
        """Create system resource monitoring rules with predictive thresholds"""
        
        # Critical: CPU Utilization > 95%
        self.add_rule(AlertRule(
            name="System CPU Critical",
            description="System CPU utilization exceeds 95% - immediate intervention required",
            category=AlertCategory.CAPACITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CPU_USAGE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=95.0,
                    unit="%",
                    description="Critical CPU utilization threshold"
                )
            ],
            evaluation_window=timedelta(minutes=3),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=5),
            max_alerts_per_hour=10,
            tags={
                "component": "system",
                "resource": "cpu",
                "team": "infrastructure",
                "priority": "p0"
            }
        ))
        
        # High: CPU Utilization > 85%
        self.add_rule(AlertRule(
            name="System CPU High",
            description="System CPU utilization exceeds 85% - scaling or optimization needed",
            category=AlertCategory.CAPACITY,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CPU_USAGE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=85.0,
                    unit="%",
                    description="High CPU utilization threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=3,
            cooldown_period=timedelta(minutes=15),
            max_alerts_per_hour=6,
            tags={
                "component": "system",
                "resource": "cpu",
                "team": "infrastructure",
                "priority": "p1"
            }
        ))
        
        # Critical: Memory Utilization > 95%
        self.add_rule(AlertRule(
            name="System Memory Critical",
            description="System memory utilization exceeds 95% - risk of OOM conditions",
            category=AlertCategory.CAPACITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.MEMORY_USAGE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=95.0,
                    unit="%",
                    description="Critical memory utilization threshold"
                )
            ],
            evaluation_window=timedelta(minutes=2),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=5),
            max_alerts_per_hour=12,
            tags={
                "component": "system",
                "resource": "memory",
                "team": "infrastructure",
                "risk": "oom"
            }
        ))
        
        # Critical: Disk Space > 90%
        self.add_rule(AlertRule(
            name="Disk Space Critical",
            description="Disk space utilization exceeds 90% - immediate cleanup required",
            category=AlertCategory.CAPACITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.DISK_USAGE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=90.0,
                    unit="%",
                    description="Critical disk space threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=10),
            max_alerts_per_hour=6,
            tags={
                "component": "system",
                "resource": "disk",
                "team": "infrastructure",
                "action": "cleanup_required"
            }
        ))
        
        # High: Network Latency > 500ms
        self.add_rule(AlertRule(
            name="Network Latency High",
            description="Network latency exceeds 500ms - connectivity issues detected",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.NETWORK_LATENCY,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=500.0,
                    unit="ms",
                    description="Network latency threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=3,
            cooldown_period=timedelta(minutes=15),
            max_alerts_per_hour=4,
            tags={
                "component": "network",
                "metric": "latency",
                "team": "infrastructure",
                "investigation": "connectivity"
            }
        ))
    
    def _create_business_metric_rules(self) -> None:
        """Create business metric and user activity alerts"""
        
        # Critical: User Authentication Failure Rate > 10%
        self.add_rule(AlertRule(
            name="Authentication Failure Rate Critical",
            description="User authentication failure rate exceeds 10% - potential security incident",
            category=AlertCategory.SECURITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.ERROR_RATE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=10.0,
                    unit="%",
                    description="Authentication failure rate threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=10),
            max_alerts_per_hour=8,
            tags={
                "component": "authentication",
                "security": "incident",
                "team": "security",
                "priority": "p0"
            }
        ))
        
        # High: User Onboarding Conversion Drop
        self.add_rule(AlertRule(
            name="User Onboarding Conversion Low",
            description="User onboarding completion rate below 70% - user experience issue",
            category=AlertCategory.BUSINESS,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CUSTOM,
                    operator=ComparisonOperator.LESS_THAN,
                    value=70.0,
                    unit="%",
                    description="Onboarding completion rate threshold"
                )
            ],
            evaluation_window=timedelta(hours=1),
            consecutive_breaches=2,
            cooldown_period=timedelta(hours=2),
            max_alerts_per_hour=2,
            tags={
                "component": "onboarding",
                "metric": "conversion",
                "team": "product",
                "impact": "user_experience"
            }
        ))
        
        # Medium: Queue Processing Backlog
        self.add_rule(AlertRule(
            name="Queue Processing Backlog",
            description="Message queue backlog exceeds 1000 items - processing delay detected",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.MEDIUM,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.QUEUE_SIZE,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=1000.0,
                    unit="items",
                    description="Queue backlog threshold"
                )
            ],
            evaluation_window=timedelta(minutes=10),
            consecutive_breaches=3,
            cooldown_period=timedelta(minutes=30),
            max_alerts_per_hour=3,
            tags={
                "component": "queue",
                "metric": "backlog",
                "team": "platform",
                "performance": "processing_delay"
            }
        ))
    
    def _create_security_rules(self) -> None:
        """Create security and compliance monitoring rules"""
        
        # Critical: Multiple Failed Login Attempts
        self.add_rule(AlertRule(
            name="Brute Force Attack Detection",
            description="Multiple failed login attempts detected - potential brute force attack",
            category=AlertCategory.SECURITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CUSTOM,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=50.0,
                    unit="attempts",
                    description="Failed login attempts per IP threshold"
                )
            ],
            evaluation_window=timedelta(minutes=5),
            consecutive_breaches=1,
            cooldown_period=timedelta(minutes=15),
            max_alerts_per_hour=8,
            tags={
                "security": "brute_force",
                "component": "authentication",
                "team": "security",
                "action": "block_ip"
            }
        ))
        
        # High: Unusual API Access Patterns
        self.add_rule(AlertRule(
            name="Unusual API Access Pattern",
            description="Unusual API access pattern detected - potential security anomaly",
            category=AlertCategory.SECURITY,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CUSTOM,
                    operator=ComparisonOperator.GREATER_THAN,
                    value=3.0,
                    unit="standard_deviations",
                    description="API access pattern deviation threshold"
                )
            ],
            evaluation_window=timedelta(minutes=15),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=30),
            max_alerts_per_hour=4,
            tags={
                "security": "anomaly",
                "component": "api",
                "team": "security",
                "analysis": "behavioral"
            }
        ))
    
    def _create_application_health_rules(self) -> None:
        """Create application-specific health monitoring rules"""
        
        # Critical: Application Service Down
        self.add_rule(AlertRule(
            name="Application Service Down",
            description="Application service health check failing - service unavailable",
            category=AlertCategory.AVAILABILITY,
            severity=AlertSeverity.CRITICAL,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CUSTOM,
                    operator=ComparisonOperator.EQUAL,
                    value=0.0,
                    unit="boolean",
                    description="Service health check status"
                )
            ],
            evaluation_window=timedelta(minutes=2),
            consecutive_breaches=3,
            cooldown_period=timedelta(minutes=5),
            max_alerts_per_hour=15,
            tags={
                "component": "application",
                "health": "service_down",
                "team": "platform",
                "priority": "p0"
            }
        ))
        
        # High: Circuit Breaker Open
        self.add_rule(AlertRule(
            name="Circuit Breaker Open",
            description="Circuit breaker in open state - dependency failure detected",
            category=AlertCategory.AVAILABILITY,
            severity=AlertSeverity.HIGH,
            conditions=[
                ThresholdCondition(
                    metric_type=MetricType.CUSTOM,
                    operator=ComparisonOperator.EQUAL,
                    value=1.0,
                    unit="boolean",
                    description="Circuit breaker state"
                )
            ],
            evaluation_window=timedelta(minutes=3),
            consecutive_breaches=2,
            cooldown_period=timedelta(minutes=10),
            max_alerts_per_hour=6,
            tags={
                "component": "circuit_breaker",
                "pattern": "failure",
                "team": "platform",
                "dependency": "external"
            }
        ))
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add alert rule to the registry"""
        rule_key = f"{rule.category.value}_{rule.name.lower().replace(' ', '_')}"
        self.alert_rules[rule_key] = rule
        logger.debug(f"Added alert rule: {rule.name} ({rule.severity.value})")
    
    def get_rule(self, rule_key: str) -> Optional[AlertRule]:
        """Get alert rule by key"""
        return self.alert_rules.get(rule_key)
    
    def get_rules_by_category(self, category: AlertCategory) -> List[AlertRule]:
        """Get all rules for a specific category"""
        return [
            rule for rule in self.alert_rules.values()
            if rule.category == category
        ]
    
    def get_rules_by_severity(self, severity: AlertSeverity) -> List[AlertRule]:
        """Get all rules for a specific severity"""
        return [
            rule for rule in self.alert_rules.values()
            if rule.severity == severity
        ]
    
    def get_enabled_rules(self) -> List[AlertRule]:
        """Get all enabled alert rules"""
        return [
            rule for rule in self.alert_rules.values()
            if rule.enabled
        ]
    
    def enable_rule(self, rule_key: str, enabled: bool = True) -> None:
        """Enable/disable an alert rule"""
        if rule_key in self.alert_rules:
            self.alert_rules[rule_key].enabled = enabled
            logger.info(f"{'Enabled' if enabled else 'Disabled'} alert rule: {rule_key}")
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of alert rules configuration"""
        total_rules = len(self.alert_rules)
        enabled_rules = len(self.get_enabled_rules())
        
        by_category = {}
        by_severity = {}
        
        for rule in self.alert_rules.values():
            category = rule.category.value
            severity = rule.severity.value
            
            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "by_category": by_category,
            "by_severity": by_severity,
            "categories": list(AlertCategory),
            "severities": list(AlertSeverity)
        }
    
    def export_rules_config(self) -> Dict[str, Any]:
        """Export alert rules configuration for backup or migration"""
        return {
            rule_key: {
                "name": rule.name,
                "description": rule.description,
                "category": rule.category.value,
                "severity": rule.severity.value,
                "enabled": rule.enabled,
                "conditions": [
                    {
                        "metric_type": condition.metric_type.value,
                        "operator": condition.operator.value,
                        "value": condition.value,
                        "unit": condition.unit,
                        "description": condition.description
                    }
                    for condition in rule.conditions
                ],
                "evaluation_window": rule.evaluation_window.total_seconds(),
                "consecutive_breaches": rule.consecutive_breaches,
                "cooldown_period": rule.cooldown_period.total_seconds(),
                "max_alerts_per_hour": rule.max_alerts_per_hour,
                "tags": rule.tags
            }
            for rule_key, rule in self.alert_rules.items()
        }


# Global production alert rules instance
_production_rules: Optional[ProductionAlertRules] = None


def get_production_alert_rules() -> ProductionAlertRules:
    """Get global production alert rules instance"""
    global _production_rules
    if _production_rules is None:
        _production_rules = ProductionAlertRules()
    return _production_rules 