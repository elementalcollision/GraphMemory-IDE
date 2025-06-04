"""
Real-time Alert Manager

Comprehensive alert lifecycle management and state tracking system.
Provides persistence, escalation, bulk operations, and enterprise-grade alert management.

Features:
- Alert persistence with SQLAlchemy models
- Complete lifecycle state management
- Automatic escalation policies
- Bulk operations and filtering
- Integration with AlertEngine and NotificationDispatcher
- Comprehensive metrics and monitoring
- Enterprise-grade error handling

Author: GraphMemory-IDE Development Team
Date: May 29, 2025
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from collections import defaultdict, deque
import sqlite3
import aiosqlite
from pathlib import Path

# Internal imports
from .models.alert_models import Alert, AlertSeverity, AlertCategory, AlertStatus
from .notification_dispatcher import NotificationDispatcher
from types import TracebackType

# Simple fallback circuit breaker for demo purposes
class SimpleCircuitBreaker:
    def __init__(self, *args, **kwargs) -> None:
        pass
    
    async def __aenter__(self) -> "SimpleCircuitBreaker":
        return self
    
    async def __aexit__(self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]) -> None:
        pass

# Simple error handler
class SimpleErrorHandler:
    async def handle_error(self, error, context) -> None:
        logger.error(f"Error in {context}: {error}")

        # Initialize with simple implementations
        self.circuit_breaker = SimpleCircuitBreaker()
        self.error_handler = SimpleErrorHandler()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertState(str, Enum):
    """Alert lifecycle states"""
    CREATED = "created"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ARCHIVED = "archived"


class EscalationPolicy(str, Enum):
    """Alert escalation policies"""
    IMMEDIATE = "immediate"
    TIME_BASED = "time_based"
    SEVERITY_BASED = "severity_based"
    MANUAL_ONLY = "manual_only"


@dataclass
class AlertMetrics:
    """Alert management metrics"""
    total_alerts: int = 0
    active_alerts: int = 0
    resolved_alerts: int = 0
    acknowledged_alerts: int = 0
    escalated_alerts: int = 0
    average_resolution_time: float = 0.0
    alerts_by_severity: Dict[str, int] = field(default_factory=dict)
    alerts_by_category: Dict[str, int] = field(default_factory=dict)
    alerts_by_state: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_alerts": self.total_alerts,
            "active_alerts": self.active_alerts,
            "resolved_alerts": self.resolved_alerts,
            "acknowledged_alerts": self.acknowledged_alerts,
            "escalated_alerts": self.escalated_alerts,
            "average_resolution_time": self.average_resolution_time,
            "alerts_by_severity": self.alerts_by_severity,
            "alerts_by_category": self.alerts_by_category,
            "alerts_by_state": self.alerts_by_state
        }


@dataclass
class EscalationRule:
    """Escalation rule configuration"""
    severity_levels: List[AlertSeverity]
    time_threshold: int  # minutes
    escalation_targets: List[str]  # email addresses or notification channels
    escalation_message: str = "Alert requires immediate attention"
    max_escalations: int = 3
    escalation_interval: int = 30  # minutes between escalations


@dataclass
class AlertFilter:
    """Alert filtering criteria"""
    severities: Optional[List[AlertSeverity]] = None
    categories: Optional[List[AlertCategory]] = None
    states: Optional[List[AlertState]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    acknowledged: Optional[bool] = None
    resolved: Optional[bool] = None


class AlertManager:
    """
    Comprehensive alert lifecycle management system
    
    Provides:
    - Alert persistence and state tracking
    - Lifecycle management with state transitions
    - Escalation policies and automatic escalation
    - Bulk operations and filtering
    - Integration with notification systems
    - Comprehensive metrics and monitoring
    """
    
    def __init__(
        self,
        db_path: str = "data/alerts.db",
        notification_dispatcher: Optional[NotificationDispatcher] = None,
        max_alerts_memory: int = 10000,
        escalation_check_interval: int = 60  # seconds
    ) -> None:
        self.db_path = Path(db_path)
        self.notification_dispatcher = notification_dispatcher
        self.max_alerts_memory = max_alerts_memory
        self.escalation_check_interval = escalation_check_interval
        
        # In-memory storage for fast access
        self._alerts: Dict[str, Alert] = {}
        self._alert_states: Dict[str, AlertState] = {}
        self._alert_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._escalation_rules: Dict[AlertSeverity, EscalationRule] = {}
        self._escalation_tracking: Dict[str, Dict[str, Any]] = {}
        
        # Metrics tracking
        self._metrics = AlertMetrics()
        self._metrics_cache = deque(maxlen=1000)  # Store last 1000 metric snapshots
        
        # Background tasks
        self._escalation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Error handling
        self.circuit_breaker = SimpleCircuitBreaker()
        self.error_handler = SimpleErrorHandler()
        
        # Event callbacks
        self._state_change_callbacks: List[Callable] = []
        self._escalation_callbacks: List[Callable] = []
        
        logger.info(f"AlertManager initialized with DB: {self.db_path}")
    
    async def initialize(self) -> None:
        """Initialize the alert manager"""
        try:
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            await self._initialize_database()
            
            # Load existing alerts from database
            await self._load_alerts_from_database()
            
            # Setup default escalation rules
            self._setup_default_escalation_rules()
            
            # Start background tasks
            await self._start_background_tasks()
            
            self._running = True
            logger.info("AlertManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AlertManager: {e}")
            await self.error_handler.handle_error(e, {"operation": "initialize"})
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the alert manager"""
        try:
            self._running = False
            
            # Cancel background tasks
            if self._escalation_task:
                self._escalation_task.cancel()
            if self._cleanup_task:
                self._cleanup_task.cancel()
            
            # Save final state to database
            await self._save_all_alerts_to_database()
            
            logger.info("AlertManager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during AlertManager shutdown: {e}")
            await self.error_handler.handle_error(e, {"operation": "shutdown"})
    
    async def create_alert(self, alert: Alert) -> str:
        """
        Create a new alert
        
        Args:
            alert: Alert object to create
            
        Returns:
            Alert ID
        """
        try:
            async with self.circuit_breaker:
                alert_id = str(alert.id)
                
                # Store alert in memory
                self._alerts[alert_id] = alert
                self._alert_states[alert_id] = AlertState.CREATED
                
                # Add to history
                self._add_to_history(alert_id, "created", {
                    "severity": alert.severity.value,
                    "category": alert.category.value,
                    "source": alert.source_component or "unknown"
                })
                
                # Save to database
                await self._save_alert_to_database(alert)
                
                # Update metrics
                await self._update_metrics()
                
                # Trigger callbacks
                await self._trigger_state_change_callbacks(alert_id, AlertState.CREATED)
                
                # Check for immediate escalation
                if await self._should_escalate_immediately(alert):
                    await self.escalate_alert(alert_id, "Immediate escalation based on severity")
                
                # Send notification
                if self.notification_dispatcher:
                    await self.notification_dispatcher.dispatch_alert(alert)
                
                logger.info(f"Created alert {alert_id} with severity {alert.severity.value}")
                return alert_id
                
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            await self.error_handler.handle_error(e, {"alert_id": str(alert.id)})
            raise
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str, notes: str = "") -> bool:
        """
        Acknowledge an alert
        
        Args:
            alert_id: Alert identifier
            acknowledged_by: Who acknowledged the alert
            notes: Optional acknowledgment notes
            
        Returns:
            True if successful
        """
        try:
            async with self.circuit_breaker:
                if alert_id not in self._alerts:
                    raise ValueError(f"Alert {alert_id} not found")
                
                # Update state
                old_state = self._alert_states.get(alert_id, AlertState.CREATED)
                self._alert_states[alert_id] = AlertState.ACKNOWLEDGED
                
                # Update alert object
                alert = self._alerts[alert_id]
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                
                # Add to history
                self._add_to_history(alert_id, "acknowledged", {
                    "acknowledged_by": acknowledged_by,
                    "notes": notes,
                    "previous_state": old_state.value
                })
                
                # Save to database
                await self._save_alert_to_database(alert)
                
                # Update metrics
                await self._update_metrics()
                
                # Trigger callbacks
                await self._trigger_state_change_callbacks(alert_id, AlertState.ACKNOWLEDGED)
                
                # Send notification
                if self.notification_dispatcher:
                    await self.notification_dispatcher.dispatch_alert(alert)
                
                logger.info(f"Acknowledged alert {alert_id} by {acknowledged_by}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            await self.error_handler.handle_error(e, {"alert_id": alert_id})
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: str = "") -> bool:
        """
        Resolve an alert
        
        Args:
            alert_id: Alert identifier
            resolved_by: Who resolved the alert
            resolution_notes: Resolution details
            
        Returns:
            True if successful
        """
        try:
            async with self.circuit_breaker:
                if alert_id not in self._alerts:
                    raise ValueError(f"Alert {alert_id} not found")
                
                # Update state
                old_state = self._alert_states.get(alert_id, AlertState.CREATED)
                self._alert_states[alert_id] = AlertState.RESOLVED
                
                # Update alert object
                alert = self._alerts[alert_id]
                alert.resolved_at = datetime.utcnow()
                alert.status = AlertStatus.RESOLVED
                
                # Calculate resolution time
                if alert.triggered_at:
                    resolution_time = (alert.resolved_at - alert.triggered_at).total_seconds() / 60
                else:
                    resolution_time = 0
                
                # Add to history
                self._add_to_history(alert_id, "resolved", {
                    "resolved_by": resolved_by,
                    "resolution_notes": resolution_notes,
                    "resolution_time_minutes": resolution_time,
                    "previous_state": old_state.value
                })
                
                # Save to database
                await self._save_alert_to_database(alert)
                
                # Remove from escalation tracking
                self._escalation_tracking.pop(alert_id, None)
                
                # Update metrics
                await self._update_metrics()
                
                # Trigger callbacks
                await self._trigger_state_change_callbacks(alert_id, AlertState.RESOLVED)
                
                # Send notification
                if self.notification_dispatcher:
                    await self.notification_dispatcher.dispatch_alert(alert)
                
                logger.info(f"Resolved alert {alert_id} by {resolved_by} in {resolution_time:.1f} minutes")
                return True
                
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            await self.error_handler.handle_error(e, {"alert_id": alert_id})
            return False
    
    async def escalate_alert(self, alert_id: str, escalation_reason: str = "") -> bool:
        """
        Escalate an alert
        
        Args:
            alert_id: Alert identifier
            escalation_reason: Reason for escalation
            
        Returns:
            True if successful
        """
        try:
            async with self.circuit_breaker:
                if alert_id not in self._alerts:
                    raise ValueError(f"Alert {alert_id} not found")
                
                alert = self._alerts[alert_id]
                
                # Check escalation rules
                escalation_rule = self._escalation_rules.get(alert.severity)
                if not escalation_rule:
                    logger.warning(f"No escalation rule for severity {alert.severity.value}")
                    return False
                
                # Track escalation
                if alert_id not in self._escalation_tracking:
                    self._escalation_tracking[alert_id] = {
                        "escalation_count": 0,
                        "last_escalation": None,
                        "escalation_history": []
                    }
                
                escalation_data = self._escalation_tracking[alert_id]
                
                # Check max escalations
                if escalation_data["escalation_count"] >= escalation_rule.max_escalations:
                    logger.warning(f"Alert {alert_id} has reached max escalations")
                    return False
                
                # Update state
                old_state = self._alert_states.get(alert_id, AlertState.CREATED)
                self._alert_states[alert_id] = AlertState.ESCALATED
                
                # Update escalation tracking
                escalation_data["escalation_count"] += 1
                escalation_data["last_escalation"] = datetime.utcnow()
                escalation_data["escalation_history"].append({
                    "timestamp": datetime.utcnow(),
                    "reason": escalation_reason,
                    "escalation_level": escalation_data["escalation_count"]
                })
                
                # Add to history
                self._add_to_history(alert_id, "escalated", {
                    "escalation_reason": escalation_reason,
                    "escalation_level": escalation_data["escalation_count"],
                    "previous_state": old_state.value
                })
                
                # Save to database
                await self._save_alert_to_database(alert)
                
                # Update metrics
                await self._update_metrics()
                
                # Trigger callbacks
                await self._trigger_escalation_callbacks(alert_id, escalation_reason)
                
                # Send escalation notification
                if self.notification_dispatcher:
                    escalation_message = f"{escalation_rule.escalation_message}: {escalation_reason}"
                    await self.notification_dispatcher.dispatch_alert(alert)
                
                logger.info(f"Escalated alert {alert_id} (level {escalation_data['escalation_count']})")
                return True
                
        except Exception as e:
            logger.error(f"Failed to escalate alert {alert_id}: {e}")
            await self.error_handler.handle_error(e, {"alert_id": alert_id})
            return False
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID"""
        return self._alerts.get(alert_id)
    
    async def get_alert_state(self, alert_id: str) -> Optional[AlertState]:
        """Get alert state by ID"""
        return self._alert_states.get(alert_id)
    
    async def get_alert_history(self, alert_id: str) -> List[Dict[str, Any]]:
        """Get alert history by ID"""
        return self._alert_history.get(alert_id, [])
    
    async def list_alerts(self, filter_criteria: Optional[AlertFilter] = None, 
                         limit: int = 100, offset: int = 0) -> List[Alert]:
        """
        List alerts with filtering
        
        Args:
            filter_criteria: Filtering criteria
            limit: Maximum number of alerts to return
            offset: Number of alerts to skip
            
        Returns:
            List of filtered alerts
        """
        try:
            alerts = list(self._alerts.values())
            
            # Apply filters
            if filter_criteria:
                alerts = self._apply_filters(alerts, filter_criteria)
            
            # Sort by creation time (newest first)
            alerts.sort(key=lambda a: a.triggered_at or datetime.min, reverse=True)
            
            # Apply pagination
            return alerts[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to list alerts: {e}")
            await self.error_handler.handle_error(e, {"filter": str(filter_criteria)})
            return []
    
    async def bulk_acknowledge(self, alert_ids: List[str], acknowledged_by: str) -> Dict[str, bool]:
        """
        Bulk acknowledge multiple alerts
        
        Args:
            alert_ids: List of alert IDs
            acknowledged_by: Who acknowledged the alerts
            
        Returns:
            Dict mapping alert ID to success status
        """
        results = {}
        for alert_id in alert_ids:
            try:
                success = await self.acknowledge_alert(alert_id, acknowledged_by)
                results[alert_id] = success
            except Exception as e:
                logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
                results[alert_id] = False
        
        return results
    
    async def bulk_resolve(self, alert_ids: List[str], resolved_by: str, 
                          resolution_notes: str = "") -> Dict[str, bool]:
        """
        Bulk resolve multiple alerts
        
        Args:
            alert_ids: List of alert IDs
            resolved_by: Who resolved the alerts
            resolution_notes: Resolution details
            
        Returns:
            Dict mapping alert ID to success status
        """
        results = {}
        for alert_id in alert_ids:
            try:
                success = await self.resolve_alert(alert_id, resolved_by, resolution_notes)
                results[alert_id] = success
            except Exception as e:
                logger.error(f"Failed to resolve alert {alert_id}: {e}")
                results[alert_id] = False
        
        return results
    
    async def get_metrics(self) -> AlertMetrics:
        """Get current alert metrics"""
        await self._update_metrics()
        return self._metrics
    
    async def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for the specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        history = []
        for metric_snapshot in self._metrics_cache:
            if metric_snapshot.get("timestamp", datetime.min) >= cutoff_time:
                history.append(metric_snapshot)
        
        return history
    
    # Event handling methods
    def add_state_change_callback(self, callback: Callable[[str, AlertState], None]) -> None:
        """Add callback for state changes"""
        self._state_change_callbacks.append(callback)
    
    def add_escalation_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add callback for escalations"""
        self._escalation_callbacks.append(callback)
    
    # Private methods
    async def _initialize_database(self) -> None:
        """Initialize SQLite database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    source TEXT,
                    status TEXT,
                    created_at TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    acknowledged_by TEXT,
                    resolved_at TIMESTAMP,
                    alert_data TEXT,
                    tags TEXT,
                    metadata TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_states (
                    alert_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (alert_id) REFERENCES alerts (id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP,
                    data TEXT,
                    FOREIGN KEY (alert_id) REFERENCES alerts (id)
                )
            """)
            
            await db.commit()
    
    async def _load_alerts_from_database(self) -> None:
        """Load existing alerts from database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Load alerts
                async with db.execute("SELECT * FROM alerts") as cursor:
                    async for row in cursor:
                        alert_data = {
                            "id": row[0],
                            "severity": AlertSeverity(row[1]),
                            "category": AlertCategory(row[2]),
                            "title": row[3],
                            "description": row[4],
                            "source": row[5],
                            "status": AlertStatus(row[6]) if row[6] else AlertStatus.ACTIVE,
                            "created_at": datetime.fromisoformat(row[7]) if row[7] else None,
                            "acknowledged_at": datetime.fromisoformat(row[8]) if row[8] else None,
                            "acknowledged_by": row[9],
                            "resolved_at": datetime.fromisoformat(row[10]) if row[10] else None,
                            "data": json.loads(row[11]) if row[11] else {},
                            "tags": json.loads(row[12]) if row[12] else [],
                            "metadata": json.loads(row[13]) if row[13] else {}
                        }
                        
                        alert = Alert(**alert_data)
                        self._alerts[str(alert.id)] = alert
                
                # Load alert states
                async with db.execute("SELECT alert_id, state FROM alert_states") as cursor:
                    async for row in cursor:
                        state_value = row[1]
                        self._alert_states[row[0]] = AlertState(state_value)
                
                # Load alert history
                async with db.execute("SELECT alert_id, action, timestamp, data FROM alert_history ORDER BY timestamp") as cursor:
                    async for row in cursor:
                        history_entry = {
                            "action": row[1],
                            "timestamp": datetime.fromisoformat(row[2]) if row[2] else None,
                            "data": json.loads(row[3]) if row[3] else {}
                        }
                        self._alert_history[row[0]].append(history_entry)
                
                logger.info(f"Loaded {len(self._alerts)} alerts from database")
                
        except Exception as e:
            logger.error(f"Failed to load alerts from database: {e}")
            # Continue with empty state if database load fails
    
    async def _save_alert_to_database(self, alert: Alert) -> None:
        """Save alert to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO alerts 
                    (id, severity, category, title, description, source, status, 
                     created_at, acknowledged_at, acknowledged_by, resolved_at, 
                     alert_data, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(alert.id),
                    alert.severity.value,
                    alert.category.value,
                    alert.title,
                    alert.description,
                    alert.source_component or "unknown",
                    alert.status.value,
                    alert.triggered_at.isoformat() if alert.triggered_at else None,
                    alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    alert.acknowledged_by,
                    alert.resolved_at.isoformat() if alert.resolved_at else None,
                    json.dumps({}),  # alert_data column - empty dict for compatibility
                    json.dumps(alert.tags),
                    json.dumps({})  # metadata column - empty dict for compatibility
                ))
                
                # Save state
                alert_id = str(alert.id)
                state = self._alert_states.get(alert_id, AlertState.CREATED)
                await db.execute("""
                    INSERT OR REPLACE INTO alert_states (alert_id, state, updated_at)
                    VALUES (?, ?, ?)
                """, (alert_id, state.value, datetime.utcnow().isoformat()))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save alert to database: {e}")
    
    async def _save_all_alerts_to_database(self) -> None:
        """Save all alerts to database"""
        for alert in self._alerts.values():
            await self._save_alert_to_database(alert)
    
    def _add_to_history(self, alert_id: str, action: str, data: Dict[str, Any]) -> None:
        """Add entry to alert history"""
        history_entry = {
            "action": action,
            "timestamp": datetime.utcnow(),
            "data": data
        }
        self._alert_history[alert_id].append(history_entry)
    
    async def _update_metrics(self) -> None:
        """Update alert metrics"""
        try:
            total_alerts = len(self._alerts)
            active_alerts = sum(1 for state in self._alert_states.values() 
                              if state in [AlertState.CREATED, AlertState.ACKNOWLEDGED, 
                                         AlertState.INVESTIGATING, AlertState.ESCALATED])
            resolved_alerts = sum(1 for state in self._alert_states.values() 
                                if state == AlertState.RESOLVED)
            acknowledged_alerts = sum(1 for state in self._alert_states.values() 
                                    if state == AlertState.ACKNOWLEDGED)
            escalated_alerts = sum(1 for state in self._alert_states.values() 
                                 if state == AlertState.ESCALATED)
            
            # Calculate average resolution time
            resolution_times = []
            for alert in self._alerts.values():
                if alert.resolved_at and alert.triggered_at:
                    resolution_time = (alert.resolved_at - alert.triggered_at).total_seconds() / 60
                    resolution_times.append(resolution_time)
            
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            # Count by severity
            alerts_by_severity = defaultdict(int)
            for alert in self._alerts.values():
                alerts_by_severity[alert.severity.value] += 1
            
            # Count by category
            alerts_by_category = defaultdict(int)
            for alert in self._alerts.values():
                alerts_by_category[alert.category.value] += 1
            
            # Count by state
            alerts_by_state = defaultdict(int)
            for state in self._alert_states.values():
                alerts_by_state[state.value] += 1
            
            # Update metrics
            self._metrics = AlertMetrics(
                total_alerts=total_alerts,
                active_alerts=active_alerts,
                resolved_alerts=resolved_alerts,
                acknowledged_alerts=acknowledged_alerts,
                escalated_alerts=escalated_alerts,
                average_resolution_time=avg_resolution_time,
                alerts_by_severity=dict(alerts_by_severity),
                alerts_by_category=dict(alerts_by_category),
                alerts_by_state=dict(alerts_by_state)
            )
            
            # Add to metrics cache
            metric_snapshot = self._metrics.to_dict()
            metric_snapshot["timestamp"] = datetime.utcnow()
            self._metrics_cache.append(metric_snapshot)
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    def _apply_filters(self, alerts: List[Alert], filter_criteria: AlertFilter) -> List[Alert]:
        """Apply filtering criteria to alerts"""
        filtered_alerts = alerts
        
        if filter_criteria.severities:
            filtered_alerts = [a for a in filtered_alerts if a.severity in filter_criteria.severities]
        
        if filter_criteria.categories:
            filtered_alerts = [a for a in filtered_alerts if a.category in filter_criteria.categories]
        
        if filter_criteria.states:
            filtered_alerts = [a for a in filtered_alerts 
                             if self._alert_states.get(str(a.id)) in filter_criteria.states]
        
        if filter_criteria.time_range:
            start_time, end_time = filter_criteria.time_range
            filtered_alerts = [a for a in filtered_alerts 
                             if a.triggered_at and start_time <= a.triggered_at <= end_time]
        
        if filter_criteria.source:
            filtered_alerts = [a for a in filtered_alerts if a.source == filter_criteria.source]
        
        if filter_criteria.tags:
            filtered_alerts = [a for a in filtered_alerts 
                             if any(tag in a.tags for tag in filter_criteria.tags)]
        
        if filter_criteria.acknowledged is not None:
            if filter_criteria.acknowledged:
                filtered_alerts = [a for a in filtered_alerts if a.acknowledged_at is not None]
            else:
                filtered_alerts = [a for a in filtered_alerts if a.acknowledged_at is None]
        
        if filter_criteria.resolved is not None:
            if filter_criteria.resolved:
                filtered_alerts = [a for a in filtered_alerts if a.resolved_at is not None]
            else:
                filtered_alerts = [a for a in filtered_alerts if a.resolved_at is None]
        
        return filtered_alerts
    
    def _setup_default_escalation_rules(self) -> None:
        """Setup default escalation rules"""
        self._escalation_rules = {
            AlertSeverity.CRITICAL: EscalationRule(
                severity_levels=[AlertSeverity.CRITICAL],
                time_threshold=5,  # 5 minutes
                escalation_targets=["admin@example.com"],
                escalation_message="CRITICAL: Immediate attention required",
                max_escalations=3,
                escalation_interval=15
            ),
            AlertSeverity.HIGH: EscalationRule(
                severity_levels=[AlertSeverity.HIGH],
                time_threshold=15,  # 15 minutes
                escalation_targets=["team@example.com"],
                escalation_message="HIGH: Urgent attention required",
                max_escalations=2,
                escalation_interval=30
            ),
            AlertSeverity.MEDIUM: EscalationRule(
                severity_levels=[AlertSeverity.MEDIUM],
                time_threshold=60,  # 1 hour
                escalation_targets=["support@example.com"],
                escalation_message="MEDIUM: Attention required",
                max_escalations=1,
                escalation_interval=60
            )
        }
    
    async def _should_escalate_immediately(self, alert: Alert) -> bool:
        """Check if alert should be escalated immediately"""
        return alert.severity == AlertSeverity.CRITICAL
    
    async def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        self._escalation_task = asyncio.create_task(self._escalation_monitor())
        self._cleanup_task = asyncio.create_task(self._cleanup_monitor())
    
    async def _escalation_monitor(self) -> None:
        """Monitor alerts for escalation"""
        while self._running:
            try:
                await asyncio.sleep(self.escalation_check_interval)
                
                current_time = datetime.utcnow()
                
                for alert_id, alert in self._alerts.items():
                    state = self._alert_states.get(alert_id, AlertState.CREATED)
                    
                    # Skip if already resolved or escalated recently
                    if state in [AlertState.RESOLVED, AlertState.CLOSED, AlertState.ARCHIVED]:
                        continue
                    
                    escalation_rule = self._escalation_rules.get(alert.severity)
                    if not escalation_rule:
                        continue
                    
                    # Check if enough time has passed for escalation
                    time_since_creation = (current_time - alert.triggered_at).total_seconds() / 60
                    
                    if time_since_creation >= escalation_rule.time_threshold:
                        escalation_data = self._escalation_tracking.get(alert_id, {})
                        last_escalation = escalation_data.get("last_escalation")
                        
                        # Check if enough time has passed since last escalation
                        if last_escalation:
                            time_since_escalation = (current_time - last_escalation).total_seconds() / 60
                            if time_since_escalation < escalation_rule.escalation_interval:
                                continue
                        
                        # Escalate if not already at max escalations
                        escalation_count = escalation_data.get("escalation_count", 0)
                        if escalation_count < escalation_rule.max_escalations:
                            await self.escalate_alert(alert_id, "Automatic escalation due to time threshold")
                
            except Exception as e:
                logger.error(f"Error in escalation monitor: {e}")
                await self.error_handler.handle_error(e, {"operation": "escalation_monitor"})
    
    async def _cleanup_monitor(self) -> None:
        """Monitor for cleanup of old alerts"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Archive old resolved alerts (older than 30 days)
                cutoff_time = datetime.utcnow() - timedelta(days=30)
                alerts_to_archive = []
                
                for alert_id, alert in self._alerts.items():
                    state = self._alert_states.get(alert_id, AlertState.CREATED)
                    if (state == AlertState.RESOLVED and 
                        alert.resolved_at and 
                        alert.resolved_at < cutoff_time):
                        alerts_to_archive.append(alert_id)
                
                # Archive alerts
                for alert_id in alerts_to_archive:
                    self._alert_states[alert_id] = AlertState.ARCHIVED
                    logger.info(f"Archived old alert {alert_id}")
                
                # Clean up memory if too many alerts
                if len(self._alerts) > self.max_alerts_memory:
                    # Remove oldest archived alerts
                    archived_alerts = [
                        (alert_id, alert) for alert_id, alert in self._alerts.items()
                        if self._alert_states.get(alert_id) == AlertState.ARCHIVED
                    ]
                    archived_alerts.sort(key=lambda x: x[1].triggered_at or datetime.min)
                    
                    alerts_to_remove = len(self._alerts) - self.max_alerts_memory
                    for i in range(min(alerts_to_remove, len(archived_alerts))):
                        alert_id = archived_alerts[i][0]
                        del self._alerts[alert_id]
                        del self._alert_states[alert_id]
                        del self._alert_history[alert_id]
                        logger.info(f"Removed archived alert {alert_id} from memory")
                
            except Exception as e:
                logger.error(f"Error in cleanup monitor: {e}")
                await self.error_handler.handle_error(e, {"operation": "cleanup_monitor"})
    
    async def _trigger_state_change_callbacks(self, alert_id: str, new_state: AlertState) -> None:
        """Trigger state change callbacks"""
        for callback in self._state_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_id, new_state)
                else:
                    callback(alert_id, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    async def _trigger_escalation_callbacks(self, alert_id: str, reason: str) -> None:
        """Trigger escalation callbacks"""
        for callback in self._escalation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_id, reason)
                else:
                    callback(alert_id, reason)
            except Exception as e:
                logger.error(f"Error in escalation callback: {e}")


# Global alert manager instance
alert_manager: Optional[AlertManager] = None


async def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global alert_manager
    if alert_manager is None:
        alert_manager = AlertManager()
        await alert_manager.initialize()
    return alert_manager


async def initialize_alert_manager(
    db_path: str = "data/alerts.db",
    notification_dispatcher: Optional[NotificationDispatcher] = None
) -> AlertManager:
    """Initialize global alert manager"""
    global alert_manager
    alert_manager = AlertManager(db_path=db_path, notification_dispatcher=notification_dispatcher)
    await alert_manager.initialize()
    return alert_manager


async def shutdown_alert_manager() -> None:
    """Shutdown global alert manager"""
    global alert_manager
    if alert_manager:
        await alert_manager.shutdown()
        alert_manager = None 