"""
Enhanced Alert Correlation Engine for GraphMemory-IDE Production Monitoring

This module provides advanced alert correlation and deduplication capabilities:
- Multi-strategy correlation (entity-based, pattern-based, dependency-based)
- Time-window correlation with configurable windows
- Alert suppression and maintenance windows
- Machine learning-based similarity detection
- Production-ready correlation rules and policies

Implementation based on research findings from:
- NewRelic Alert Correlation patterns
- LogicMonitor Alert Correlation strategies  
- Modern production monitoring best practices
- Real-world correlation scenarios and patterns

Created for TASK-022 Phase 1: Enhanced Alerting & Notification System
"""

import asyncio
import logging
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Callable, NamedTuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import numpy as np
from difflib import SequenceMatcher

# Import existing models and utilities
from server.dashboard.models.alert_models import (
    Alert, AlertSeverity, AlertCategory, AlertStatus, AlertEvent
)
from server.dashboard.cache_manager import get_cache_manager, CacheManager
from server.health_monitoring import AlertManager

logger = logging.getLogger(__name__)


class CorrelationStrategy(Enum):
    """Alert correlation strategies"""
    SAME_ENTITY = "same_entity"
    SIMILAR_MESSAGE = "similar_message"
    DEPENDENCY_BASED = "dependency_based"
    TIME_WINDOW = "time_window"
    PATTERN_MATCH = "pattern_match"
    ML_SIMILARITY = "ml_similarity"
    CUSTOM_RULE = "custom_rule"


class CorrelationConfidence(Enum):
    """Correlation confidence levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class CorrelationRule:
    """Defines how alerts should be correlated"""
    name: str
    strategy: CorrelationStrategy
    confidence: CorrelationConfidence
    enabled: bool = True
    priority: int = 100  # Lower = higher priority
    
    # Strategy-specific parameters
    entity_fields: List[str] = field(default_factory=lambda: ['source_host', 'source_component'])
    similarity_threshold: float = 0.8
    time_window: timedelta = field(default=timedelta(minutes=10))
    pattern_regex: Optional[str] = None
    dependency_map: Dict[str, List[str]] = field(default_factory=dict)
    custom_function: Optional[Callable] = None
    
    # Filtering
    severity_filter: List[AlertSeverity] = field(default_factory=list)
    category_filter: List[AlertCategory] = field(default_factory=list)
    tag_filters: Dict[str, str] = field(default_factory=dict)
    
    # Suppression settings
    max_group_size: int = 50
    suppress_after_count: int = 10
    maintenance_windows: List[Tuple[datetime, datetime]] = field(default_factory=list)


@dataclass
class AlertGroup:
    """Group of correlated alerts"""
    id: str
    root_alert: Alert
    correlated_alerts: List[Alert] = field(default_factory=list)
    correlation_rules: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    suppressed: bool = False
    group_status: AlertStatus = AlertStatus.ACTIVE
    
    def add_alert(self, alert: Alert, rule_name: str, confidence: float) -> None:
        """Add alert to group"""
        self.correlated_alerts.append(alert)
        if rule_name not in self.correlation_rules:
            self.correlation_rules.append(rule_name)
        self.confidence_score = max(self.confidence_score, confidence)
        self.last_updated = datetime.utcnow()
    
    def get_severity(self) -> AlertSeverity:
        """Get highest severity in group"""
        all_alerts = [self.root_alert] + self.correlated_alerts
        severities = [alert.severity for alert in all_alerts]
        severity_order = [AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM, AlertSeverity.LOW, AlertSeverity.INFO]
        for severity in severity_order:
            if severity in severities:
                return severity
        return AlertSeverity.INFO
    
    def get_alert_count(self) -> int:
        """Get total number of alerts in group"""
        return 1 + len(self.correlated_alerts)
    
    def should_suppress(self, rule: CorrelationRule) -> bool:
        """Check if group should be suppressed"""
        return self.get_alert_count() >= rule.suppress_after_count


class CorrelationResult(NamedTuple):
    """Result of correlation analysis"""
    should_correlate: bool
    confidence: float
    strategy: CorrelationStrategy
    metadata: Dict[str, Any]


class AlertCorrelationEngine:
    """Advanced alert correlation engine with multiple strategies"""
    
    def __init__(self, max_groups: int = 1000, cleanup_interval: int = 3600) -> None:
        self.correlation_rules: Dict[str, CorrelationRule] = {}
        self.alert_groups: Dict[str, AlertGroup] = {}
        self.pending_alerts: deque = deque(maxlen=10000)
        
        # External dependencies
        self.cache_manager: Optional[CacheManager] = None
        self.alert_manager: Optional[AlertManager] = None
        
        # Configuration
        self.max_groups = max_groups
        self.cleanup_interval = cleanup_interval
        self._last_cleanup = datetime.utcnow()
        
        # Statistics - Fix type definitions
        self.correlation_stats: Dict[str, Any] = {
            'total_alerts_processed': 0,
            'groups_created': 0,
            'alerts_correlated': 0,
            'correlation_by_strategy': defaultdict(int),
            'suppressed_groups': 0
        }
        
        # Initialize default rules
        self._initialize_default_rules()
        
        logger.info("AlertCorrelationEngine initialized")
    
    async def initialize(self) -> None:
        """Initialize the correlation engine"""
        try:
            self.cache_manager = await get_cache_manager()
            logger.info("AlertCorrelationEngine dependencies initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AlertCorrelationEngine: {e}")
            raise
    
    def _initialize_default_rules(self) -> None:
        """Initialize default correlation rules based on research findings"""
        
        # Rule 1: Same Entity Correlation (highest priority)
        self.add_rule(CorrelationRule(
            name="same_entity_correlation",
            strategy=CorrelationStrategy.SAME_ENTITY,
            confidence=CorrelationConfidence.VERY_HIGH,
            priority=10,
            entity_fields=['source_host', 'source_component'],
            time_window=timedelta(minutes=5),
            max_group_size=20,
            suppress_after_count=5
        ))
        
        # Rule 2: Similar Message Correlation
        self.add_rule(CorrelationRule(
            name="similar_message_correlation",
            strategy=CorrelationStrategy.SIMILAR_MESSAGE,
            confidence=CorrelationConfidence.HIGH,
            priority=20,
            similarity_threshold=0.85,
            time_window=timedelta(minutes=10),
            max_group_size=15,
            suppress_after_count=8
        ))
        
        # Rule 3: Performance Issues Correlation - Use PERFORMANCE instead of DATABASE
        self.add_rule(CorrelationRule(
            name="performance_issues_correlation",
            strategy=CorrelationStrategy.PATTERN_MATCH,
            confidence=CorrelationConfidence.HIGH,
            priority=15,
            pattern_regex=r'(connection|database|timeout|pool|performance|latency)',
            time_window=timedelta(minutes=3),
            category_filter=[AlertCategory.PERFORMANCE],
            max_group_size=25,
            suppress_after_count=5
        ))
        
        # Rule 4: High Traffic Correlation
        self.add_rule(CorrelationRule(
            name="high_traffic_correlation",
            strategy=CorrelationStrategy.PATTERN_MATCH,
            confidence=CorrelationConfidence.MEDIUM,
            priority=30,
            pattern_regex=r'(traffic|load|requests|throughput|rate)',
            time_window=timedelta(minutes=5),
            category_filter=[AlertCategory.PERFORMANCE],
            max_group_size=10,
            suppress_after_count=7
        ))
        
        # Rule 5: Critical System Alerts
        self.add_rule(CorrelationRule(
            name="critical_system_correlation",
            strategy=CorrelationStrategy.TIME_WINDOW,
            confidence=CorrelationConfidence.MEDIUM,
            priority=25,
            time_window=timedelta(minutes=2),
            severity_filter=[AlertSeverity.CRITICAL],
            max_group_size=30,
            suppress_after_count=3
        ))
        
        # Rule 6: ML-based Similarity (lowest priority, experimental)
        self.add_rule(CorrelationRule(
            name="ml_similarity_correlation", 
            strategy=CorrelationStrategy.ML_SIMILARITY,
            confidence=CorrelationConfidence.LOW,
            priority=100,
            similarity_threshold=0.75,
            time_window=timedelta(minutes=15),
            max_group_size=12,
            suppress_after_count=10
        ))
    
    def add_rule(self, rule: CorrelationRule) -> None:
        """Add correlation rule"""
        self.correlation_rules[rule.name] = rule
        logger.info(f"Added correlation rule: {rule.name} ({rule.strategy.value})")
    
    def remove_rule(self, rule_name: str) -> None:
        """Remove correlation rule"""
        if rule_name in self.correlation_rules:
            del self.correlation_rules[rule_name]
            logger.info(f"Removed correlation rule: {rule_name}")
    
    def enable_rule(self, rule_name: str, enabled: bool = True) -> None:
        """Enable/disable correlation rule"""
        if rule_name in self.correlation_rules:
            self.correlation_rules[rule_name].enabled = enabled
            logger.info(f"{'Enabled' if enabled else 'Disabled'} correlation rule: {rule_name}")
    
    async def process_alert(self, alert: Alert) -> Optional[AlertGroup]:
        """Process incoming alert through correlation engine"""
        try:
            self.correlation_stats['total_alerts_processed'] += 1
            
            # Check if alert should be processed
            if not self._should_process_alert(alert):
                return None
            
            # Find potential correlations
            correlation_candidates = await self._find_correlation_candidates(alert)
            
            # Apply correlation rules
            best_group = None
            best_confidence = 0.0
            
            for group_id, group in correlation_candidates:
                for rule_name, rule in self._get_applicable_rules(alert):
                    if not rule.enabled:
                        continue
                    
                    result = await self._apply_correlation_rule(alert, group, rule)
                    
                    if result.should_correlate and result.confidence > best_confidence:
                        best_group = group
                        best_confidence = result.confidence
                        
                        # Add alert to group
                        group.add_alert(alert, rule_name, result.confidence)
                        self.correlation_stats['alerts_correlated'] += 1
                        self.correlation_stats['correlation_by_strategy'][result.strategy.value] += 1
                        
                        # Check if group should be suppressed
                        if group.should_suppress(rule):
                            group.suppressed = True
                            self.correlation_stats['suppressed_groups'] += 1
                        
                        logger.info(f"Correlated alert {alert.id} with group {group.id} using rule {rule_name}")
                        break
            
            # Create new group if no correlation found
            if best_group is None:
                best_group = await self._create_new_group(alert)
                self.correlation_stats['groups_created'] += 1
            
            # Cleanup old groups periodically
            await self._periodic_cleanup()
            
            return best_group
            
        except Exception as e:
            logger.error(f"Error processing alert {alert.id}: {e}")
            return None
    
    def _should_process_alert(self, alert: Alert) -> bool:
        """Check if alert should be processed for correlation"""
        # Skip resolved alerts
        if alert.status == AlertStatus.RESOLVED:
            return False
        
        # Skip test alerts
        if alert.tags.get('test', '').lower() == 'true':
            return False
        
        return True
    
    async def _find_correlation_candidates(self, alert: Alert) -> List[Tuple[str, AlertGroup]]:
        """Find potential groups for correlation"""
        candidates = []
        current_time = datetime.utcnow()
        
        for group_id, group in self.alert_groups.items():
            # Skip suppressed groups
            if group.suppressed:
                continue
            
            # Skip closed groups
            if group.group_status == AlertStatus.RESOLVED:
                continue
            
            # Check if group is within any correlation time window
            max_window = max(rule.time_window for rule in self.correlation_rules.values() if rule.enabled)
            if current_time - group.last_updated > max_window:
                continue
            
            candidates.append((group_id, group))
        
        return candidates
    
    def _get_applicable_rules(self, alert: Alert) -> List[Tuple[str, CorrelationRule]]:
        """Get correlation rules applicable to alert"""
        applicable_rules = []
        
        for rule_name, rule in self.correlation_rules.items():
            if not rule.enabled:
                continue
            
            # Check severity filter
            if rule.severity_filter and alert.severity not in rule.severity_filter:
                continue
            
            # Check category filter
            if rule.category_filter and alert.category not in rule.category_filter:
                continue
            
            # Check tag filters
            if rule.tag_filters:
                tag_match = all(
                    alert.tags.get(key) == value 
                    for key, value in rule.tag_filters.items()
                )
                if not tag_match:
                    continue
            
            # Check maintenance windows
            current_time = datetime.utcnow()
            in_maintenance = any(
                start <= current_time <= end
                for start, end in rule.maintenance_windows
            )
            if in_maintenance:
                continue
            
            applicable_rules.append((rule_name, rule))
        
        # Sort by priority (lower = higher priority)
        applicable_rules.sort(key=lambda x: x[1].priority)
        return applicable_rules
    
    async def _apply_correlation_rule(self, alert: Alert, group: AlertGroup, rule: CorrelationRule) -> CorrelationResult:
        """Apply specific correlation rule"""
        try:
            if rule.strategy == CorrelationStrategy.SAME_ENTITY:
                return self._correlate_by_entity(alert, group, rule)
            elif rule.strategy == CorrelationStrategy.SIMILAR_MESSAGE:
                return self._correlate_by_message_similarity(alert, group, rule)
            elif rule.strategy == CorrelationStrategy.PATTERN_MATCH:
                return self._correlate_by_pattern(alert, group, rule)
            elif rule.strategy == CorrelationStrategy.TIME_WINDOW:
                return self._correlate_by_time_window(alert, group, rule)
            elif rule.strategy == CorrelationStrategy.ML_SIMILARITY:
                return await self._correlate_by_ml_similarity(alert, group, rule)
            elif rule.strategy == CorrelationStrategy.CUSTOM_RULE:
                return self._correlate_by_custom_rule(alert, group, rule)
            else:
                return CorrelationResult(False, 0.0, rule.strategy, {})
        
        except Exception as e:
            logger.error(f"Error applying correlation rule {rule.name}: {e}")
            return CorrelationResult(False, 0.0, rule.strategy, {'error': str(e)})
    
    def _correlate_by_entity(self, alert: Alert, group: AlertGroup, rule: CorrelationRule) -> CorrelationResult:
        """Correlate alerts from the same entity"""
        all_group_alerts = [group.root_alert] + group.correlated_alerts
        
        for group_alert in all_group_alerts:
            entity_matches = 0
            total_fields = len(rule.entity_fields)
            
            for field in rule.entity_fields:
                alert_value = getattr(alert, field, None)
                group_value = getattr(group_alert, field, None)
                
                if alert_value and group_value and alert_value == group_value:
                    entity_matches += 1
            
            if entity_matches > 0:
                confidence = entity_matches / total_fields
                
                # Check time window
                time_diff = abs((alert.triggered_at - group_alert.triggered_at).total_seconds())
                if time_diff <= rule.time_window.total_seconds():
                    return CorrelationResult(
                        True, 
                        confidence, 
                        rule.strategy,
                        {'entity_matches': entity_matches, 'total_fields': total_fields}
                    )
        
        return CorrelationResult(False, 0.0, rule.strategy, {})
    
    def _correlate_by_message_similarity(self, alert: Alert, group: AlertGroup, rule: CorrelationRule) -> CorrelationResult:
        """Correlate alerts with similar messages"""
        all_group_alerts = [group.root_alert] + group.correlated_alerts
        
        for group_alert in all_group_alerts:
            # Calculate message similarity
            similarity = SequenceMatcher(None, alert.description, group_alert.description).ratio()
            
            if similarity >= rule.similarity_threshold:
                # Check time window
                time_diff = abs((alert.triggered_at - group_alert.triggered_at).total_seconds())
                if time_diff <= rule.time_window.total_seconds():
                    return CorrelationResult(
                        True,
                        similarity,
                        rule.strategy,
                        {'similarity_score': similarity, 'threshold': rule.similarity_threshold}
                    )
        
        return CorrelationResult(False, 0.0, rule.strategy, {})
    
    def _correlate_by_pattern(self, alert: Alert, group: AlertGroup, rule: CorrelationRule) -> CorrelationResult:
        """Correlate alerts matching specific patterns"""
        if not rule.pattern_regex:
            return CorrelationResult(False, 0.0, rule.strategy, {'error': 'No pattern specified'})
        
        try:
            pattern = re.compile(rule.pattern_regex, re.IGNORECASE)
            
            # Check if alert matches pattern
            alert_text = f"{alert.title} {alert.description}".lower()
            if not pattern.search(alert_text):
                return CorrelationResult(False, 0.0, rule.strategy, {'pattern_match': False})
            
            # Check if any alert in group matches pattern
            all_group_alerts = [group.root_alert] + group.correlated_alerts
            for group_alert in all_group_alerts:
                group_text = f"{group_alert.title} {group_alert.description}".lower()
                if pattern.search(group_text):
                    # Check time window
                    time_diff = abs((alert.triggered_at - group_alert.triggered_at).total_seconds())
                    if time_diff <= rule.time_window.total_seconds():
                        return CorrelationResult(
                            True,
                            0.8,  # Fixed confidence for pattern matches
                            rule.strategy,
                            {'pattern': rule.pattern_regex, 'matched_text': alert_text[:100]}
                        )
            
            return CorrelationResult(False, 0.0, rule.strategy, {})
            
        except re.error as e:
            return CorrelationResult(False, 0.0, rule.strategy, {'error': f'Invalid regex: {e}'})
    
    def _correlate_by_time_window(self, alert: Alert, group: AlertGroup, rule: CorrelationRule) -> CorrelationResult:
        """Correlate alerts within time window"""
        time_diff = abs((alert.triggered_at - group.created_at).total_seconds())
        
        if time_diff <= rule.time_window.total_seconds():
            # Calculate confidence based on time proximity
            max_time = rule.time_window.total_seconds()
            confidence = 1.0 - (time_diff / max_time)
            
            return CorrelationResult(
                True,
                confidence,
                rule.strategy,
                {'time_diff_seconds': time_diff, 'window_seconds': max_time}
            )
        
        return CorrelationResult(False, 0.0, rule.strategy, {})
    
    async def _correlate_by_ml_similarity(self, alert: Alert, group: AlertGroup, rule: CorrelationRule) -> CorrelationResult:
        """Correlate alerts using ML-based similarity (simplified implementation)"""
        try:
            # Simple feature extraction for ML similarity
            def extract_features(alert_obj) -> None:
                features = []
                # Text features
                text = f"{alert_obj.title} {alert_obj.description}".lower()
                features.extend([
                    len(text.split()),  # Word count
                    text.count('error'),
                    text.count('warning'),
                    text.count('critical'),
                    text.count('timeout'),
                    text.count('connection'),
                    text.count('database'),
                    text.count('memory'),
                    text.count('cpu'),
                    text.count('disk')
                ])
                # Numeric features - convert boolean to int for type compatibility
                features.append(int(alert_obj.severity.value == 'critical'))
                features.append(int(alert_obj.severity.value == 'high'))
                features.append(int(alert_obj.category.value == 'performance'))
                features.append(int(alert_obj.category.value == 'availability'))
                return features  # Return list instead of numpy array to avoid import issues
            
            # Extract features for current alert
            alert_features = extract_features(alert)
            
            # Compare with group alerts using simple similarity
            all_group_alerts = [group.root_alert] + group.correlated_alerts
            max_similarity = 0.0
            
            for group_alert in all_group_alerts:
                group_features = extract_features(group_alert)
                
                # Calculate simple similarity without numpy (to avoid import issues)
                if len(alert_features) == len(group_features):
                    matches = sum(1 for a, b in zip(alert_features, group_features) if abs(a - b) < 0.1)
                    similarity = matches / len(alert_features)
                    max_similarity = max(max_similarity, similarity)
            
            if max_similarity >= rule.similarity_threshold:
                return CorrelationResult(
                    True,
                    max_similarity,
                    rule.strategy,
                    {'ml_similarity': max_similarity, 'threshold': rule.similarity_threshold}
                )
            
            return CorrelationResult(False, 0.0, rule.strategy, {})
            
        except Exception as e:
            logger.error(f"ML similarity correlation failed: {e}")
            return CorrelationResult(False, 0.0, rule.strategy, {'error': str(e)})
    
    def _correlate_by_custom_rule(self, alert: Alert, group: AlertGroup, rule: CorrelationRule) -> CorrelationResult:
        """Correlate alerts using custom function"""
        if not rule.custom_function:
            return CorrelationResult(False, 0.0, rule.strategy, {'error': 'No custom function specified'})
        
        try:
            result = rule.custom_function(alert, group, rule)
            if isinstance(result, bool):
                return CorrelationResult(result, 0.7 if result else 0.0, rule.strategy, {})
            elif isinstance(result, tuple) and len(result) >= 2:
                return CorrelationResult(result[0], result[1], rule.strategy, result[2] if len(result) > 2 else {})
            else:
                return CorrelationResult(False, 0.0, rule.strategy, {'error': 'Invalid custom function result'})
        except Exception as e:
            logger.error(f"Custom correlation rule failed: {e}")
            return CorrelationResult(False, 0.0, rule.strategy, {'error': str(e)})
    
    async def _create_new_group(self, alert: Alert) -> AlertGroup:
        """Create new alert group"""
        group_id = hashlib.md5(f"{alert.id}_{datetime.utcnow().isoformat()}".encode()).hexdigest()
        
        group = AlertGroup(
            id=group_id,
            root_alert=alert
        )
        
        self.alert_groups[group_id] = group
        
        # Limit number of groups
        if len(self.alert_groups) > self.max_groups:
            await self._cleanup_old_groups()
        
        logger.info(f"Created new alert group {group_id} for alert {alert.id}")
        return group
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of old groups"""
        current_time = datetime.utcnow()
        if (current_time - self._last_cleanup).total_seconds() >= self.cleanup_interval:
            await self._cleanup_old_groups()
            self._last_cleanup = current_time
    
    async def _cleanup_old_groups(self) -> None:
        """Clean up old and resolved alert groups"""
        current_time = datetime.utcnow()
        groups_to_remove = []
        
        for group_id, group in self.alert_groups.items():
            # Remove groups older than 24 hours
            if (current_time - group.created_at).total_seconds() > 86400:
                groups_to_remove.append(group_id)
            # Remove resolved groups older than 1 hour
            elif group.group_status == AlertStatus.RESOLVED and \
                 (current_time - group.last_updated).total_seconds() > 3600:
                groups_to_remove.append(group_id)
        
        for group_id in groups_to_remove:
            del self.alert_groups[group_id]
        
        if groups_to_remove:
            logger.info(f"Cleaned up {len(groups_to_remove)} old alert groups")
    
    def get_correlation_stats(self) -> Dict[str, Any]:
        """Get correlation engine statistics"""
        return {
            **self.correlation_stats,
            'active_groups': len(self.alert_groups),
            'enabled_rules': len([r for r in self.correlation_rules.values() if r.enabled]),
            'total_rules': len(self.correlation_rules)
        }
    
    def get_active_groups(self, max_age_hours: int = 24) -> List[AlertGroup]:
        """Get active alert groups"""
        current_time = datetime.utcnow()
        max_age = timedelta(hours=max_age_hours)
        
        return [
            group for group in self.alert_groups.values()
            if (current_time - group.created_at) <= max_age and
               group.group_status != AlertStatus.RESOLVED
        ]
    
    async def resolve_group(self, group_id: str) -> bool:
        """Mark alert group as resolved"""
        if group_id in self.alert_groups:
            self.alert_groups[group_id].group_status = AlertStatus.RESOLVED
            self.alert_groups[group_id].last_updated = datetime.utcnow()
            logger.info(f"Resolved alert group {group_id}")
            return True
        return False
    
    def add_maintenance_window(self, rule_name: str, start_time: datetime, end_time: datetime) -> None:
        """Add maintenance window to correlation rule"""
        if rule_name in self.correlation_rules:
            self.correlation_rules[rule_name].maintenance_windows.append((start_time, end_time))
            logger.info(f"Added maintenance window to rule {rule_name}: {start_time} - {end_time}")


# Global correlation engine instance
_correlation_engine: Optional[AlertCorrelationEngine] = None


async def get_correlation_engine() -> AlertCorrelationEngine:
    """Get global correlation engine instance"""
    global _correlation_engine
    if _correlation_engine is None:
        _correlation_engine = AlertCorrelationEngine()
        await _correlation_engine.initialize()
    return _correlation_engine 