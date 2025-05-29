"""
Incident Management System - Convert correlated alerts into actionable incidents.

This module provides the IncidentManager that:
- Converts correlated alerts into incidents automatically
- Manages incident lifecycle (Open → Investigating → Resolved → Closed)
- Provides incident escalation separate from alert escalation
- Supports incident merge/split operations
- Integrates with external ticketing systems
- Provides comprehensive incident analytics and reporting

Created as part of Step 8 Phase 4: Advanced Incident Management System
Research foundation: Exa + Context7 + Sequential Thinking analysis
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from uuid import UUID, uuid4
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import aiosqlite
from pathlib import Path

from .models.alert_models import Alert, AlertSeverity, AlertCategory, AlertStatus
from .alert_correlator import (
    AlertCorrelator, CorrelationResult, CorrelationConfidence, 
    get_alert_correlator
)
from .alert_manager import get_alert_manager, AlertManager
from .notification_dispatcher import NotificationDispatcher
from .cache_manager import get_cache_manager, CacheManager

# Configure logging
logger = logging.getLogger(__name__)


class IncidentStatus(str, Enum):
    """Incident lifecycle status"""
    OPEN = "open"                   # New incident, not yet investigated
    INVESTIGATING = "investigating" # Actively being investigated
    RESOLVED = "resolved"          # Root cause found and resolved
    CLOSED = "closed"              # Resolved and validated, no further action
    REOPENED = "reopened"          # Previously resolved but recurred


class IncidentPriority(str, Enum):
    """Incident priority levels"""
    P1_CRITICAL = "p1_critical"    # Business-critical impact
    P2_HIGH = "p2_high"            # High impact, needs immediate attention
    P3_MEDIUM = "p3_medium"        # Medium impact, normal timeline
    P4_LOW = "p4_low"              # Low impact, when time permits
    P5_INFO = "p5_info"            # Informational, no action required


class IncidentCategory(str, Enum):
    """Incident categories for classification"""
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    SECURITY = "security"
    DATA_INTEGRITY = "data_integrity"
    CAPACITY = "capacity"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    OTHER = "other"


@dataclass
class IncidentEscalationRule:
    """Escalation rules for incidents"""
    priority: IncidentPriority
    time_to_acknowledge: timedelta
    time_to_investigate: timedelta
    time_to_resolve: timedelta
    escalation_targets: List[str]
    auto_escalate: bool = True
    max_escalations: int = 3


@dataclass
class Incident:
    """Core incident data model"""
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    status: IncidentStatus = IncidentStatus.OPEN
    priority: IncidentPriority = IncidentPriority.P3_MEDIUM
    category: IncidentCategory = IncidentCategory.OTHER
    
    # Timing information
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    investigation_started_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Assignment information
    assigned_to: Optional[str] = None
    assigned_team: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    
    # Related data
    correlation_id: Optional[UUID] = None
    alert_ids: Set[UUID] = field(default_factory=set)
    parent_incident_id: Optional[UUID] = None
    child_incident_ids: Set[UUID] = field(default_factory=set)
    
    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    # External integration
    external_ticket_id: Optional[str] = None
    external_system: Optional[str] = None
    
    # Timeline tracking
    timeline_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_timeline_event(self, event_type: str, description: str, 
                          user: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Add event to incident timeline"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'description': description,
            'user': user,
            'metadata': metadata or {}
        }
        self.timeline_events.append(event)
    
    def get_duration(self) -> Optional[timedelta]:
        """Get total incident duration"""
        if self.closed_at:
            return self.closed_at - self.created_at
        return datetime.utcnow() - self.created_at
    
    def get_time_to_acknowledge(self) -> Optional[timedelta]:
        """Get time from creation to acknowledgment"""
        if self.acknowledged_at:
            return self.acknowledged_at - self.created_at
        return None
    
    def get_time_to_resolve(self) -> Optional[timedelta]:
        """Get time from creation to resolution"""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None


@dataclass
class IncidentMetrics:
    """Incident management metrics"""
    total_incidents: int = 0
    open_incidents: int = 0
    investigating_incidents: int = 0
    resolved_incidents: int = 0
    closed_incidents: int = 0
    
    # Timing metrics
    average_time_to_acknowledge: float = 0.0  # minutes
    average_time_to_resolve: float = 0.0      # minutes
    average_incident_duration: float = 0.0    # minutes
    
    # Priority distribution
    incidents_by_priority: Dict[str, int] = field(default_factory=dict)
    incidents_by_category: Dict[str, int] = field(default_factory=dict)
    incidents_by_status: Dict[str, int] = field(default_factory=dict)
    
    # Performance metrics
    sla_compliance_rate: float = 0.0
    escalation_rate: float = 0.0
    reopen_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'total_incidents': self.total_incidents,
            'open_incidents': self.open_incidents,
            'investigating_incidents': self.investigating_incidents,
            'resolved_incidents': self.resolved_incidents,
            'closed_incidents': self.closed_incidents,
            'average_time_to_acknowledge': self.average_time_to_acknowledge,
            'average_time_to_resolve': self.average_time_to_resolve,
            'average_incident_duration': self.average_incident_duration,
            'incidents_by_priority': self.incidents_by_priority,
            'incidents_by_category': self.incidents_by_category,
            'incidents_by_status': self.incidents_by_status,
            'sla_compliance_rate': self.sla_compliance_rate,
            'escalation_rate': self.escalation_rate,
            'reopen_rate': self.reopen_rate
        }


class IncidentManager:
    """
    Comprehensive incident management system that converts correlated alerts
    into actionable incidents with complete lifecycle management.
    """
    
    def __init__(
        self,
        db_path: str = "data/incidents.db",
        alert_correlator: Optional[AlertCorrelator] = None,
        alert_manager: Optional[AlertManager] = None,
        notification_dispatcher: Optional[NotificationDispatcher] = None
    ):
        self.db_path = Path(db_path)
        self.alert_correlator = alert_correlator
        self.alert_manager = alert_manager
        self.notification_dispatcher = notification_dispatcher
        
        # In-memory storage
        self.incidents: Dict[UUID, Incident] = {}
        self.correlation_to_incident: Dict[UUID, UUID] = {}
        
        # Escalation rules
        self.escalation_rules = self._create_default_escalation_rules()
        self.escalation_tracking: Dict[UUID, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = IncidentMetrics()
        self.metrics_history = deque(maxlen=1000)
        
        # Background tasks
        self.escalation_task: Optional[asyncio.Task] = None
        self.auto_close_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Event callbacks
        self.incident_callbacks: List[Callable] = []
        
        # External dependencies
        self.cache_manager: Optional[CacheManager] = None
        
        logger.info(f"IncidentManager initialized with DB: {self.db_path}")
    
    async def initialize(self):
        """Initialize the incident manager"""
        try:
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            await self._initialize_database()
            
            # Load existing incidents
            await self._load_incidents_from_database()
            
            # Get external dependencies
            if not self.alert_correlator:
                self.alert_correlator = await get_alert_correlator()
            if not self.alert_manager:
                self.alert_manager = await get_alert_manager()
            
            self.cache_manager = await get_cache_manager()
            
            # Register correlation callback
            if self.alert_correlator:
                self.alert_correlator.add_correlation_callback(self._on_correlation_created)
            
            # Start background tasks
            await self._start_background_tasks()
            
            self.running = True
            logger.info("IncidentManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize IncidentManager: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the incident manager"""
        try:
            self.running = False
            
            # Cancel background tasks
            if self.escalation_task:
                self.escalation_task.cancel()
            if self.auto_close_task:
                self.auto_close_task.cancel()
            
            # Save final state
            await self._save_all_incidents_to_database()
            
            logger.info("IncidentManager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during IncidentManager shutdown: {e}")
    
    async def create_incident_from_correlation(self, correlation: CorrelationResult) -> Incident:
        """Create incident from alert correlation"""
        try:
            # Check if incident already exists for this correlation
            if correlation.correlation_id in self.correlation_to_incident:
                incident_id = self.correlation_to_incident[correlation.correlation_id]
                return self.incidents[incident_id]
            
            # Determine incident priority from alert severities
            alert_ids = list(correlation.alert_ids)
            alerts = []
            
            if self.alert_manager:
                for alert_id in alert_ids:
                    alert = await self.alert_manager.get_alert(str(alert_id))
                    if alert:
                        alerts.append(alert)
            
            priority = self._determine_incident_priority(alerts)
            category = self._determine_incident_category(alerts, correlation)
            
            # Create incident title and description
            title = self._generate_incident_title(alerts, correlation)
            description = self._generate_incident_description(alerts, correlation)
            
            # Create incident
            incident = Incident(
                title=title,
                description=description,
                priority=priority,
                category=category,
                correlation_id=correlation.correlation_id,
                alert_ids=correlation.alert_ids
            )
            
            # Store incident
            self.incidents[incident.id] = incident
            self.correlation_to_incident[correlation.correlation_id] = incident.id
            
            # Add timeline event
            incident.add_timeline_event(
                "incident_created",
                f"Incident created from {len(alerts)} correlated alerts using {correlation.strategy.value} strategy",
                metadata={
                    'correlation_id': str(correlation.correlation_id),
                    'strategy': correlation.strategy.value,
                    'confidence': correlation.confidence.value,
                    'alert_count': len(alerts)
                }
            )
            
            # Save to database
            await self._save_incident_to_database(incident)
            
            # Update metrics
            await self._update_metrics()
            
            # Trigger callbacks
            await self._trigger_incident_callbacks("incident_created", incident)
            
            # Send notification
            if self.notification_dispatcher:
                await self._send_incident_notification(incident, "created")
            
            logger.info(f"Created incident {incident.id} from correlation {correlation.correlation_id} "
                       f"with {len(alerts)} alerts (priority: {priority.value})")
            
            return incident
            
        except Exception as e:
            logger.error(f"Failed to create incident from correlation: {e}")
            raise
    
    async def acknowledge_incident(self, incident_id: UUID, acknowledged_by: str, 
                                 notes: str = "") -> bool:
        """Acknowledge an incident"""
        try:
            if incident_id not in self.incidents:
                logger.warning(f"Incident {incident_id} not found")
                return False
            
            incident = self.incidents[incident_id]
            
            if incident.status != IncidentStatus.OPEN:
                logger.warning(f"Incident {incident_id} cannot be acknowledged in status {incident.status}")
                return False
            
            # Update incident
            incident.acknowledged_at = datetime.utcnow()
            incident.acknowledged_by = acknowledged_by
            incident.add_timeline_event(
                "incident_acknowledged",
                f"Incident acknowledged by {acknowledged_by}: {notes}",
                user=acknowledged_by,
                metadata={'notes': notes}
            )
            
            # Save to database
            await self._save_incident_to_database(incident)
            
            # Update metrics
            await self._update_metrics()
            
            # Trigger callbacks
            await self._trigger_incident_callbacks("incident_acknowledged", incident)
            
            # Send notification
            if self.notification_dispatcher:
                await self._send_incident_notification(incident, "acknowledged")
            
            logger.info(f"Acknowledged incident {incident_id} by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge incident {incident_id}: {e}")
            return False
    
    async def start_investigation(self, incident_id: UUID, investigator: str, 
                                notes: str = "") -> bool:
        """Start investigation on an incident"""
        try:
            if incident_id not in self.incidents:
                logger.warning(f"Incident {incident_id} not found")
                return False
            
            incident = self.incidents[incident_id]
            
            if incident.status not in [IncidentStatus.OPEN]:
                logger.warning(f"Incident {incident_id} cannot start investigation in status {incident.status}")
                return False
            
            # Update incident
            incident.status = IncidentStatus.INVESTIGATING
            incident.investigation_started_at = datetime.utcnow()
            incident.assigned_to = investigator
            
            incident.add_timeline_event(
                "investigation_started",
                f"Investigation started by {investigator}: {notes}",
                user=investigator,
                metadata={'notes': notes}
            )
            
            # Save to database
            await self._save_incident_to_database(incident)
            
            # Update metrics
            await self._update_metrics()
            
            # Trigger callbacks
            await self._trigger_incident_callbacks("investigation_started", incident)
            
            # Send notification
            if self.notification_dispatcher:
                await self._send_incident_notification(incident, "investigation_started")
            
            logger.info(f"Started investigation on incident {incident_id} by {investigator}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start investigation on incident {incident_id}: {e}")
            return False
    
    async def resolve_incident(self, incident_id: UUID, resolved_by: str, 
                             resolution_notes: str = "") -> bool:
        """Resolve an incident"""
        try:
            if incident_id not in self.incidents:
                logger.warning(f"Incident {incident_id} not found")
                return False
            
            incident = self.incidents[incident_id]
            
            if incident.status not in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]:
                logger.warning(f"Incident {incident_id} cannot be resolved in status {incident.status}")
                return False
            
            # Update incident
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = datetime.utcnow()
            incident.resolved_by = resolved_by
            
            incident.add_timeline_event(
                "incident_resolved",
                f"Incident resolved by {resolved_by}: {resolution_notes}",
                user=resolved_by,
                metadata={'resolution_notes': resolution_notes}
            )
            
            # Save to database
            await self._save_incident_to_database(incident)
            
            # Update metrics
            await self._update_metrics()
            
            # Trigger callbacks
            await self._trigger_incident_callbacks("incident_resolved", incident)
            
            # Send notification
            if self.notification_dispatcher:
                await self._send_incident_notification(incident, "resolved")
            
            logger.info(f"Resolved incident {incident_id} by {resolved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve incident {incident_id}: {e}")
            return False
    
    async def close_incident(self, incident_id: UUID, closed_by: str, 
                           close_notes: str = "") -> bool:
        """Close a resolved incident"""
        try:
            if incident_id not in self.incidents:
                logger.warning(f"Incident {incident_id} not found")
                return False
            
            incident = self.incidents[incident_id]
            
            if incident.status != IncidentStatus.RESOLVED:
                logger.warning(f"Incident {incident_id} cannot be closed in status {incident.status}")
                return False
            
            # Update incident
            incident.status = IncidentStatus.CLOSED
            incident.closed_at = datetime.utcnow()
            
            incident.add_timeline_event(
                "incident_closed",
                f"Incident closed by {closed_by}: {close_notes}",
                user=closed_by,
                metadata={'close_notes': close_notes}
            )
            
            # Save to database
            await self._save_incident_to_database(incident)
            
            # Update metrics
            await self._update_metrics()
            
            # Trigger callbacks
            await self._trigger_incident_callbacks("incident_closed", incident)
            
            # Send notification
            if self.notification_dispatcher:
                await self._send_incident_notification(incident, "closed")
            
            logger.info(f"Closed incident {incident_id} by {closed_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close incident {incident_id}: {e}")
            return False
    
    async def merge_incidents(self, primary_incident_id: UUID, 
                            secondary_incident_ids: List[UUID], 
                            merged_by: str, merge_reason: str = "") -> bool:
        """Merge multiple incidents into one primary incident"""
        try:
            if primary_incident_id not in self.incidents:
                logger.warning(f"Primary incident {primary_incident_id} not found")
                return False
            
            primary_incident = self.incidents[primary_incident_id]
            secondary_incidents = []
            
            # Validate all secondary incidents exist
            for sec_id in secondary_incident_ids:
                if sec_id not in self.incidents:
                    logger.warning(f"Secondary incident {sec_id} not found")
                    return False
                secondary_incidents.append(self.incidents[sec_id])
            
            # Merge alert IDs
            for sec_incident in secondary_incidents:
                primary_incident.alert_ids.update(sec_incident.alert_ids)
                primary_incident.child_incident_ids.add(sec_incident.id)
                sec_incident.parent_incident_id = primary_incident.id
            
            # Update primary incident description
            merged_info = f"\n\n--- MERGED FROM {len(secondary_incidents)} INCIDENTS ---\n"
            for sec_incident in secondary_incidents:
                merged_info += f"- {sec_incident.title} (ID: {sec_incident.id})\n"
            primary_incident.description += merged_info
            
            # Add timeline event
            primary_incident.add_timeline_event(
                "incidents_merged",
                f"Merged {len(secondary_incidents)} incidents by {merged_by}: {merge_reason}",
                user=merged_by,
                metadata={
                    'merged_incident_ids': [str(id) for id in secondary_incident_ids],
                    'merge_reason': merge_reason
                }
            )
            
            # Save all incidents
            await self._save_incident_to_database(primary_incident)
            for sec_incident in secondary_incidents:
                await self._save_incident_to_database(sec_incident)
            
            # Update metrics
            await self._update_metrics()
            
            # Trigger callbacks
            await self._trigger_incident_callbacks("incidents_merged", primary_incident)
            
            logger.info(f"Merged {len(secondary_incidents)} incidents into {primary_incident_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to merge incidents: {e}")
            return False
    
    async def get_incident(self, incident_id: UUID) -> Optional[Incident]:
        """Get incident by ID"""
        return self.incidents.get(incident_id)
    
    async def list_incidents(self, status: Optional[IncidentStatus] = None,
                           priority: Optional[IncidentPriority] = None,
                           assigned_to: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> List[Incident]:
        """List incidents with filtering"""
        incidents = list(self.incidents.values())
        
        # Apply filters
        if status:
            incidents = [i for i in incidents if i.status == status]
        if priority:
            incidents = [i for i in incidents if i.priority == priority]
        if assigned_to:
            incidents = [i for i in incidents if i.assigned_to == assigned_to]
        
        # Sort by creation time (newest first)
        incidents.sort(key=lambda i: i.created_at, reverse=True)
        
        # Apply pagination
        return incidents[offset:offset + limit]
    
    async def get_metrics(self) -> IncidentMetrics:
        """Get current incident metrics"""
        await self._update_metrics()
        return self.metrics
    
    def add_incident_callback(self, callback: Callable):
        """Add callback for incident events"""
        self.incident_callbacks.append(callback)
    
    # Private methods
    
    async def _on_correlation_created(self, correlation: CorrelationResult):
        """Handle new correlation from AlertCorrelator"""
        try:
            if correlation.is_significant():
                incident = await self.create_incident_from_correlation(correlation)
                logger.info(f"Auto-created incident {incident.id} from correlation {correlation.correlation_id}")
        except Exception as e:
            logger.error(f"Failed to create incident from correlation: {e}")
    
    def _determine_incident_priority(self, alerts: List[Alert]) -> IncidentPriority:
        """Determine incident priority based on alert severities"""
        if not alerts:
            return IncidentPriority.P3_MEDIUM
        
        # Find highest severity
        severities = [alert.severity for alert in alerts]
        if AlertSeverity.CRITICAL in severities:
            return IncidentPriority.P1_CRITICAL
        elif AlertSeverity.HIGH in severities:
            return IncidentPriority.P2_HIGH
        elif AlertSeverity.MEDIUM in severities:
            return IncidentPriority.P3_MEDIUM
        elif AlertSeverity.LOW in severities:
            return IncidentPriority.P4_LOW
        else:
            return IncidentPriority.P5_INFO
    
    def _determine_incident_category(self, alerts: List[Alert], 
                                   correlation: CorrelationResult) -> IncidentCategory:
        """Determine incident category based on alerts and correlation"""
        if not alerts:
            return IncidentCategory.OTHER
        
        # Map alert categories to incident categories
        category_map = {
            AlertCategory.PERFORMANCE: IncidentCategory.PERFORMANCE,
            AlertCategory.MEMORY: IncidentCategory.PERFORMANCE,
            AlertCategory.CPU: IncidentCategory.PERFORMANCE,
            AlertCategory.DISK: IncidentCategory.CAPACITY,
            AlertCategory.NETWORK: IncidentCategory.NETWORK,
            AlertCategory.SECURITY: IncidentCategory.SECURITY,
            AlertCategory.APPLICATION: IncidentCategory.SOFTWARE,
            AlertCategory.DATABASE: IncidentCategory.SOFTWARE,
            AlertCategory.SYSTEM: IncidentCategory.HARDWARE
        }
        
        # Find most common category
        categories = [category_map.get(alert.category, IncidentCategory.OTHER) for alert in alerts]
        category_counts = {}
        for cat in categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Return most frequent category
        return max(category_counts.items(), key=lambda x: x[1])[0]
    
    def _generate_incident_title(self, alerts: List[Alert], 
                               correlation: CorrelationResult) -> str:
        """Generate incident title from alerts and correlation"""
        if not alerts:
            return f"Incident from {correlation.strategy.value} correlation"
        
        # Use primary alert title or create composite title
        if correlation.primary_alert_id:
            primary_alert = next((a for a in alerts if a.id == correlation.primary_alert_id), None)
            if primary_alert:
                return f"{primary_alert.title} (+{len(alerts)-1} related alerts)"
        
        # Create title from common patterns
        common_components = set()
        common_categories = set()
        
        for alert in alerts:
            if alert.source_component:
                common_components.add(alert.source_component)
            common_categories.add(alert.category.value)
        
        if len(common_components) == 1:
            component = list(common_components)[0]
            return f"Multiple alerts in {component} ({len(alerts)} alerts)"
        elif len(common_categories) == 1:
            category = list(common_categories)[0]
            return f"Multiple {category} alerts ({len(alerts)} alerts)"
        else:
            return f"Correlated incident with {len(alerts)} alerts"
    
    def _generate_incident_description(self, alerts: List[Alert], 
                                     correlation: CorrelationResult) -> str:
        """Generate incident description from alerts and correlation"""
        description = f"Incident created from {len(alerts)} correlated alerts.\n\n"
        description += f"Correlation Strategy: {correlation.strategy.value}\n"
        description += f"Correlation Confidence: {correlation.confidence.value}\n"
        description += f"Correlation Score: {correlation.confidence_score:.2f}\n\n"
        
        description += "Included Alerts:\n"
        for i, alert in enumerate(alerts[:5], 1):  # Limit to first 5 alerts
            description += f"{i}. {alert.title} (Severity: {alert.severity.value})\n"
            if alert.description:
                description += f"   {alert.description[:100]}{'...' if len(alert.description) > 100 else ''}\n"
        
        if len(alerts) > 5:
            description += f"... and {len(alerts) - 5} more alerts\n"
        
        # Add correlation factors if available
        if correlation.correlation_factors:
            description += f"\nCorrelation Details:\n"
            for key, value in correlation.correlation_factors.items():
                if isinstance(value, (int, float, str, bool)):
                    description += f"- {key}: {value}\n"
        
        return description
    
    def _create_default_escalation_rules(self) -> Dict[IncidentPriority, IncidentEscalationRule]:
        """Create default escalation rules"""
        return {
            IncidentPriority.P1_CRITICAL: IncidentEscalationRule(
                priority=IncidentPriority.P1_CRITICAL,
                time_to_acknowledge=timedelta(minutes=15),
                time_to_investigate=timedelta(minutes=30),
                time_to_resolve=timedelta(hours=4),
                escalation_targets=["critical-incidents@company.com"],
                max_escalations=3
            ),
            IncidentPriority.P2_HIGH: IncidentEscalationRule(
                priority=IncidentPriority.P2_HIGH,
                time_to_acknowledge=timedelta(hours=1),
                time_to_investigate=timedelta(hours=2),
                time_to_resolve=timedelta(hours=24),
                escalation_targets=["high-incidents@company.com"],
                max_escalations=2
            ),
            IncidentPriority.P3_MEDIUM: IncidentEscalationRule(
                priority=IncidentPriority.P3_MEDIUM,
                time_to_acknowledge=timedelta(hours=4),
                time_to_investigate=timedelta(hours=8),
                time_to_resolve=timedelta(days=3),
                escalation_targets=["incidents@company.com"],
                max_escalations=1
            )
        }
    
    async def _initialize_database(self):
        """Initialize SQLite database for incidents"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    investigation_started_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    closed_at TIMESTAMP,
                    assigned_to TEXT,
                    assigned_team TEXT,
                    acknowledged_by TEXT,
                    resolved_by TEXT,
                    correlation_id TEXT,
                    alert_ids TEXT,
                    parent_incident_id TEXT,
                    child_incident_ids TEXT,
                    tags TEXT,
                    custom_fields TEXT,
                    external_ticket_id TEXT,
                    external_system TEXT,
                    timeline_events TEXT
                )
            """)
            await db.commit()
    
    async def _load_incidents_from_database(self):
        """Load incidents from database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT * FROM incidents") as cursor:
                    async for row in cursor:
                        incident_data = dict(zip([col[0] for col in cursor.description], row))
                        incident = self._incident_from_db_row(incident_data)
                        self.incidents[incident.id] = incident
                        
                        if incident.correlation_id:
                            self.correlation_to_incident[incident.correlation_id] = incident.id
            
            logger.info(f"Loaded {len(self.incidents)} incidents from database")
            
        except Exception as e:
            logger.error(f"Failed to load incidents from database: {e}")
    
    async def _save_incident_to_database(self, incident: Incident):
        """Save incident to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO incidents 
                    (id, title, description, status, priority, category,
                     created_at, acknowledged_at, investigation_started_at, resolved_at, closed_at,
                     assigned_to, assigned_team, acknowledged_by, resolved_by,
                     correlation_id, alert_ids, parent_incident_id, child_incident_ids,
                     tags, custom_fields, external_ticket_id, external_system, timeline_events)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(incident.id),
                    incident.title,
                    incident.description,
                    incident.status.value,
                    incident.priority.value,
                    incident.category.value,
                    incident.created_at.isoformat(),
                    incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                    incident.investigation_started_at.isoformat() if incident.investigation_started_at else None,
                    incident.resolved_at.isoformat() if incident.resolved_at else None,
                    incident.closed_at.isoformat() if incident.closed_at else None,
                    incident.assigned_to,
                    incident.assigned_team,
                    incident.acknowledged_by,
                    incident.resolved_by,
                    str(incident.correlation_id) if incident.correlation_id else None,
                    json.dumps([str(aid) for aid in incident.alert_ids]),
                    str(incident.parent_incident_id) if incident.parent_incident_id else None,
                    json.dumps([str(cid) for cid in incident.child_incident_ids]),
                    json.dumps(incident.tags),
                    json.dumps(incident.custom_fields),
                    incident.external_ticket_id,
                    incident.external_system,
                    json.dumps(incident.timeline_events)
                ))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save incident to database: {e}")
    
    async def _save_all_incidents_to_database(self):
        """Save all incidents to database"""
        for incident in self.incidents.values():
            await self._save_incident_to_database(incident)
    
    def _incident_from_db_row(self, row: Dict[str, Any]) -> Incident:
        """Convert database row to Incident object"""
        return Incident(
            id=UUID(row['id']),
            title=row['title'],
            description=row['description'] or "",
            status=IncidentStatus(row['status']),
            priority=IncidentPriority(row['priority']),
            category=IncidentCategory(row['category']),
            created_at=datetime.fromisoformat(row['created_at']),
            acknowledged_at=datetime.fromisoformat(row['acknowledged_at']) if row['acknowledged_at'] else None,
            investigation_started_at=datetime.fromisoformat(row['investigation_started_at']) if row['investigation_started_at'] else None,
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None,
            closed_at=datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None,
            assigned_to=row['assigned_to'],
            assigned_team=row['assigned_team'],
            acknowledged_by=row['acknowledged_by'],
            resolved_by=row['resolved_by'],
            correlation_id=UUID(row['correlation_id']) if row['correlation_id'] else None,
            alert_ids=set(UUID(aid) for aid in json.loads(row['alert_ids'] or '[]')),
            parent_incident_id=UUID(row['parent_incident_id']) if row['parent_incident_id'] else None,
            child_incident_ids=set(UUID(cid) for cid in json.loads(row['child_incident_ids'] or '[]')),
            tags=json.loads(row['tags'] or '{}'),
            custom_fields=json.loads(row['custom_fields'] or '{}'),
            external_ticket_id=row['external_ticket_id'],
            external_system=row['external_system'],
            timeline_events=json.loads(row['timeline_events'] or '[]')
        )
    
    async def _update_metrics(self):
        """Update incident metrics"""
        # Count incidents by status
        open_count = sum(1 for i in self.incidents.values() if i.status == IncidentStatus.OPEN)
        investigating_count = sum(1 for i in self.incidents.values() if i.status == IncidentStatus.INVESTIGATING)
        resolved_count = sum(1 for i in self.incidents.values() if i.status == IncidentStatus.RESOLVED)
        closed_count = sum(1 for i in self.incidents.values() if i.status == IncidentStatus.CLOSED)
        
        # Calculate timing metrics
        acknowledge_times = []
        resolve_times = []
        durations = []
        
        for incident in self.incidents.values():
            if incident.get_time_to_acknowledge():
                acknowledge_times.append(incident.get_time_to_acknowledge().total_seconds() / 60)
            if incident.get_time_to_resolve():
                resolve_times.append(incident.get_time_to_resolve().total_seconds() / 60)
            if incident.get_duration():
                durations.append(incident.get_duration().total_seconds() / 60)
        
        # Count by priority and category
        priority_counts = {}
        category_counts = {}
        status_counts = {}
        
        for incident in self.incidents.values():
            priority_counts[incident.priority.value] = priority_counts.get(incident.priority.value, 0) + 1
            category_counts[incident.category.value] = category_counts.get(incident.category.value, 0) + 1
            status_counts[incident.status.value] = status_counts.get(incident.status.value, 0) + 1
        
        # Update metrics
        self.metrics = IncidentMetrics(
            total_incidents=len(self.incidents),
            open_incidents=open_count,
            investigating_incidents=investigating_count,
            resolved_incidents=resolved_count,
            closed_incidents=closed_count,
            average_time_to_acknowledge=sum(acknowledge_times) / len(acknowledge_times) if acknowledge_times else 0,
            average_time_to_resolve=sum(resolve_times) / len(resolve_times) if resolve_times else 0,
            average_incident_duration=sum(durations) / len(durations) if durations else 0,
            incidents_by_priority=priority_counts,
            incidents_by_category=category_counts,
            incidents_by_status=status_counts
        )
        
        # Add to history
        metric_snapshot = self.metrics.to_dict()
        metric_snapshot['timestamp'] = datetime.utcnow()
        self.metrics_history.append(metric_snapshot)
    
    async def _trigger_incident_callbacks(self, event_type: str, incident: Incident):
        """Trigger incident event callbacks"""
        for callback in self.incident_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, incident)
                else:
                    callback(event_type, incident)
            except Exception as e:
                logger.error(f"Error in incident callback: {e}")
    
    async def _send_incident_notification(self, incident: Incident, event_type: str):
        """Send incident notification"""
        # Implementation depends on notification dispatcher capabilities
        pass
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        self.escalation_task = asyncio.create_task(self._escalation_monitor())
        self.auto_close_task = asyncio.create_task(self._auto_close_monitor())
    
    async def _escalation_monitor(self):
        """Monitor incidents for escalation"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = datetime.utcnow()
                
                for incident in self.incidents.values():
                    if incident.status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
                        continue
                    
                    escalation_rule = self.escalation_rules.get(incident.priority)
                    if not escalation_rule or not escalation_rule.auto_escalate:
                        continue
                    
                    # Check escalation conditions
                    # Implementation would check SLA violations and trigger escalations
                    
            except Exception as e:
                logger.error(f"Error in escalation monitor: {e}")
    
    async def _auto_close_monitor(self):
        """Monitor resolved incidents for auto-close"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                current_time = datetime.utcnow()
                auto_close_after = timedelta(days=7)  # Auto-close after 7 days
                
                for incident in self.incidents.values():
                    if (incident.status == IncidentStatus.RESOLVED and 
                        incident.resolved_at and 
                        current_time - incident.resolved_at > auto_close_after):
                        
                        await self.close_incident(incident.id, "system", "Auto-closed after 7 days")
                        
            except Exception as e:
                logger.error(f"Error in auto-close monitor: {e}")


# Global incident manager instance
_incident_manager: Optional[IncidentManager] = None


async def get_incident_manager() -> IncidentManager:
    """Get the global incident manager instance"""
    global _incident_manager
    
    if _incident_manager is None:
        _incident_manager = IncidentManager()
        await _incident_manager.initialize()
    
    return _incident_manager


async def initialize_incident_manager(
    db_path: str = "data/incidents.db",
    alert_correlator: Optional[AlertCorrelator] = None,
    alert_manager: Optional[AlertManager] = None,
    notification_dispatcher: Optional[NotificationDispatcher] = None
) -> IncidentManager:
    """Initialize the global incident manager"""
    global _incident_manager
    
    _incident_manager = IncidentManager(
        db_path=db_path,
        alert_correlator=alert_correlator,
        alert_manager=alert_manager,
        notification_dispatcher=notification_dispatcher
    )
    await _incident_manager.initialize()
    
    return _incident_manager


async def shutdown_incident_manager():
    """Shutdown the global incident manager"""
    global _incident_manager
    
    if _incident_manager is not None:
        await _incident_manager.shutdown()
        _incident_manager = None


# Export main classes and functions
__all__ = [
    'IncidentManager',
    'Incident',
    'IncidentStatus',
    'IncidentPriority',
    'IncidentCategory',
    'IncidentEscalationRule',
    'IncidentMetrics',
    'get_incident_manager',
    'initialize_incident_manager',
    'shutdown_incident_manager'
] 