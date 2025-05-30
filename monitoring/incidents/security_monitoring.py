"""
Security Monitoring and Threat Detection for GraphMemory-IDE
Comprehensive security event monitoring, threat analysis, and compliance tracking
"""

import logging
import asyncio
import json
import hashlib
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import os

import httpx

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Security threat level classification."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityEventType(Enum):
    """Types of security events."""
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_VIOLATION = "authorization_violation"
    SUSPICIOUS_API_ACTIVITY = "suspicious_api_activity"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration_attempt"
    INJECTION_ATTACK = "injection_attack"
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    MALICIOUS_FILE_UPLOAD = "malicious_file_upload"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    VULNERABILITY_EXPLOIT = "vulnerability_exploit"

@dataclass
class SecurityEvent:
    """Security event record."""
    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    timestamp: datetime
    source_ip: str
    user_agent: Optional[str]
    user_id: Optional[str]
    endpoint: str
    description: str
    indicators: Dict[str, Any] = field(default_factory=dict)
    mitigated: bool = False
    investigation_notes: str = ""

@dataclass
class SecurityPattern:
    """Security pattern for threat detection."""
    pattern_id: str
    name: str
    description: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    detection_rules: List[Dict[str, Any]]
    mitigation_actions: List[str]
    enabled: bool = True

@dataclass
class ComplianceCheck:
    """Compliance monitoring check."""
    check_id: str
    name: str
    description: str
    framework: str  # GDPR, SOC2, ISO27001, etc.
    requirement: str
    status: str  # compliant, non_compliant, warning
    last_checked: datetime
    evidence: List[str] = field(default_factory=list)

class SecurityPatternEngine:
    """
    Security pattern detection engine.
    
    Analyzes incoming events and applies security patterns
    to detect threats and anomalous behavior.
    """
    
    def __init__(self):
        self.patterns = self._load_default_patterns()
        self.pattern_statistics = {}
        
        # Rate limiting for pattern detection
        self.detection_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _load_default_patterns(self) -> List[SecurityPattern]:
        """Load default security detection patterns."""
        return [
            SecurityPattern(
                pattern_id="auth_bruteforce",
                name="Authentication Brute Force",
                description="Multiple failed authentication attempts from same IP",
                event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                threat_level=ThreatLevel.HIGH,
                detection_rules=[
                    {
                        "condition": "failed_auth_count >= 5",
                        "timeframe": 300,  # 5 minutes
                        "group_by": "source_ip"
                    }
                ],
                mitigation_actions=[
                    "block_ip_temporary",
                    "require_additional_auth",
                    "notify_security_team"
                ]
            ),
            SecurityPattern(
                pattern_id="api_rate_anomaly",
                name="Suspicious API Rate",
                description="Unusually high API request rate from single source",
                event_type=SecurityEventType.SUSPICIOUS_API_ACTIVITY,
                threat_level=ThreatLevel.MEDIUM,
                detection_rules=[
                    {
                        "condition": "request_rate > normal_rate * 10",
                        "timeframe": 60,  # 1 minute
                        "baseline_required": True
                    }
                ],
                mitigation_actions=[
                    "rate_limit_increase",
                    "monitor_closely",
                    "log_detailed_activity"
                ]
            ),
            SecurityPattern(
                pattern_id="injection_attempt",
                name="SQL/NoSQL Injection Attempt",
                description="Potential injection attack in request parameters",
                event_type=SecurityEventType.INJECTION_ATTACK,
                threat_level=ThreatLevel.HIGH,
                detection_rules=[
                    {
                        "condition": "contains_injection_pattern",
                        "parameters": ["query_params", "request_body"],
                        "patterns": [
                            r"(?i)(union|select|insert|delete|drop|exec|script)",
                            r"(?i)(\$where|\$ne|\$gt|\$lt)",  # NoSQL injection
                            r"(;|'|\"|\\)"
                        ]
                    }
                ],
                mitigation_actions=[
                    "block_request",
                    "sanitize_input",
                    "alert_immediate"
                ]
            ),
            SecurityPattern(
                pattern_id="privilege_escalation",
                name="Privilege Escalation Attempt",
                description="User attempting to access higher privilege resources",
                event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                threat_level=ThreatLevel.CRITICAL,
                detection_rules=[
                    {
                        "condition": "access_denied_privilege_required",
                        "consecutive_attempts": 3,
                        "timeframe": 600  # 10 minutes
                    }
                ],
                mitigation_actions=[
                    "lock_user_account",
                    "notify_security_team",
                    "audit_user_permissions"
                ]
            ),
            SecurityPattern(
                pattern_id="data_exfiltration",
                name="Data Exfiltration Attempt",
                description="Large volume data download or suspicious export patterns",
                event_type=SecurityEventType.DATA_EXFILTRATION_ATTEMPT,
                threat_level=ThreatLevel.CRITICAL,
                detection_rules=[
                    {
                        "condition": "download_size > threshold_mb",
                        "threshold_mb": 100,
                        "timeframe": 300,
                        "unusual_hours": True
                    }
                ],
                mitigation_actions=[
                    "throttle_downloads",
                    "require_additional_auth",
                    "alert_immediate",
                    "log_detailed_activity"
                ]
            )
        ]
    
    async def analyze_event(self, event_data: Dict[str, Any]) -> List[SecurityEvent]:
        """Analyze event data against security patterns."""
        detected_events = []
        
        for pattern in self.patterns:
            if not pattern.enabled:
                continue
            
            try:
                if await self._match_pattern(pattern, event_data):
                    security_event = await self._create_security_event(pattern, event_data)
                    detected_events.append(security_event)
                    
                    # Update pattern statistics
                    self.pattern_statistics[pattern.pattern_id] = self.pattern_statistics.get(pattern.pattern_id, 0) + 1
                    
            except Exception as e:
                logger.error(f"Error analyzing pattern {pattern.pattern_id}: {e}")
        
        return detected_events
    
    async def _match_pattern(self, pattern: SecurityPattern, event_data: Dict[str, Any]) -> bool:
        """Check if event data matches security pattern."""
        for rule in pattern.detection_rules:
            if await self._evaluate_rule(rule, event_data):
                return True
        return False
    
    async def _evaluate_rule(self, rule: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Evaluate a single detection rule."""
        condition = rule.get("condition", "")
        
        # Simple condition evaluation (in production, use a proper rule engine)
        if condition == "failed_auth_count >= 5":
            return await self._check_failed_auth_pattern(rule, event_data)
        elif condition == "request_rate > normal_rate * 10":
            return await self._check_rate_anomaly(rule, event_data)
        elif condition == "contains_injection_pattern":
            return await self._check_injection_patterns(rule, event_data)
        elif condition == "access_denied_privilege_required":
            return await self._check_privilege_escalation(rule, event_data)
        elif condition == "download_size > threshold_mb":
            return await self._check_data_exfiltration(rule, event_data)
        
        return False
    
    async def _check_failed_auth_pattern(self, rule: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check for brute force authentication pattern."""
        source_ip = event_data.get("source_ip", "")
        if not source_ip:
            return False
        
        cache_key = f"failed_auth:{source_ip}"
        current_time = datetime.now()
        
        # Check cache for recent failed attempts
        if cache_key in self.detection_cache:
            attempts, first_attempt = self.detection_cache[cache_key]
            
            # If within timeframe, increment counter
            if (current_time - first_attempt).total_seconds() <= rule.get("timeframe", 300):
                attempts += 1
                self.detection_cache[cache_key] = (attempts, first_attempt)
                return attempts >= 5
            else:
                # Reset counter if outside timeframe
                self.detection_cache[cache_key] = (1, current_time)
        else:
            # First attempt
            self.detection_cache[cache_key] = (1, current_time)
        
        return False
    
    async def _check_rate_anomaly(self, rule: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check for suspicious API rate patterns."""
        source_ip = event_data.get("source_ip", "")
        endpoint = event_data.get("endpoint", "")
        
        cache_key = f"api_rate:{source_ip}:{endpoint}"
        current_time = datetime.now()
        
        if cache_key in self.detection_cache:
            request_count, window_start = self.detection_cache[cache_key]
            
            # Check if within time window
            if (current_time - window_start).total_seconds() <= rule.get("timeframe", 60):
                request_count += 1
                self.detection_cache[cache_key] = (request_count, window_start)
                
                # Check if rate exceeds threshold (simplified baseline: 10 requests/minute)
                normal_rate = 10
                return request_count > normal_rate * 10
            else:
                # Reset window
                self.detection_cache[cache_key] = (1, current_time)
        else:
            self.detection_cache[cache_key] = (1, current_time)
        
        return False
    
    async def _check_injection_patterns(self, rule: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check for injection attack patterns."""
        patterns = rule.get("patterns", [])
        parameters = rule.get("parameters", [])
        
        for param in parameters:
            content = event_data.get(param, "")
            if isinstance(content, dict):
                content = json.dumps(content)
            
            for pattern in patterns:
                if re.search(pattern, str(content)):
                    return True
        
        return False
    
    async def _check_privilege_escalation(self, rule: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check for privilege escalation patterns."""
        user_id = event_data.get("user_id", "")
        status_code = event_data.get("status_code", 200)
        
        # Check for 403 (Forbidden) responses indicating privilege issues
        if status_code == 403 and user_id:
            cache_key = f"privilege_denied:{user_id}"
            current_time = datetime.now()
            
            if cache_key in self.detection_cache:
                attempt_count, first_attempt = self.detection_cache[cache_key]
                
                if (current_time - first_attempt).total_seconds() <= rule.get("timeframe", 600):
                    attempt_count += 1
                    self.detection_cache[cache_key] = (attempt_count, first_attempt)
                    return attempt_count >= rule.get("consecutive_attempts", 3)
                else:
                    self.detection_cache[cache_key] = (1, current_time)
            else:
                self.detection_cache[cache_key] = (1, current_time)
        
        return False
    
    async def _check_data_exfiltration(self, rule: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check for data exfiltration patterns."""
        response_size = event_data.get("response_size_bytes", 0)
        threshold_bytes = rule.get("threshold_mb", 100) * 1024 * 1024  # Convert MB to bytes
        
        # Check if download size exceeds threshold
        if response_size > threshold_bytes:
            # Additional check for unusual hours if specified
            if rule.get("unusual_hours", False):
                current_hour = datetime.now().hour
                # Define business hours (9 AM to 6 PM)
                if 9 <= current_hour <= 18:
                    return False  # Normal business hours, less suspicious
            
            return True
        
        return False
    
    async def _create_security_event(self, pattern: SecurityPattern, event_data: Dict[str, Any]) -> SecurityEvent:
        """Create security event from matched pattern."""
        event_id = hashlib.md5(
            f"{pattern.pattern_id}:{event_data.get('source_ip', '')}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        return SecurityEvent(
            event_id=event_id,
            event_type=pattern.event_type,
            threat_level=pattern.threat_level,
            timestamp=datetime.now(),
            source_ip=event_data.get("source_ip", "unknown"),
            user_agent=event_data.get("user_agent"),
            user_id=event_data.get("user_id"),
            endpoint=event_data.get("endpoint", "unknown"),
            description=f"{pattern.name}: {pattern.description}",
            indicators={
                "pattern_id": pattern.pattern_id,
                "matched_rules": pattern.detection_rules,
                "event_data": event_data
            }
        )

class ComplianceMonitor:
    """
    Compliance monitoring system.
    
    Monitors system compliance with various security frameworks
    and regulatory requirements.
    """
    
    def __init__(self):
        self.compliance_checks = self._load_compliance_checks()
        self.compliance_history: List[ComplianceCheck] = []
    
    def _load_compliance_checks(self) -> List[ComplianceCheck]:
        """Load compliance monitoring checks."""
        return [
            ComplianceCheck(
                check_id="gdpr_data_retention",
                name="GDPR Data Retention Policy",
                description="Ensure user data is not retained beyond legal requirements",
                framework="GDPR",
                requirement="Article 5(1)(e) - Storage Limitation",
                status="compliant",
                last_checked=datetime.now()
            ),
            ComplianceCheck(
                check_id="soc2_access_control",
                name="SOC2 Access Control",
                description="Verify proper access controls and user authentication",
                framework="SOC2",
                requirement="CC6.1 - Logical and Physical Access Controls",
                status="compliant",
                last_checked=datetime.now()
            ),
            ComplianceCheck(
                check_id="iso27001_encryption",
                name="ISO27001 Data Encryption",
                description="Ensure sensitive data is properly encrypted",
                framework="ISO27001",
                requirement="A.10.1 - Cryptographic Controls",
                status="compliant",
                last_checked=datetime.now()
            ),
            ComplianceCheck(
                check_id="pci_dss_logging",
                name="PCI DSS Security Logging",
                description="Maintain comprehensive security logs",
                framework="PCI DSS",
                requirement="10.1 - Audit Trails",
                status="compliant",
                last_checked=datetime.now()
            )
        ]
    
    async def run_compliance_checks(self) -> Dict[str, Any]:
        """Run all compliance checks."""
        results = {
            "overall_status": "compliant",
            "framework_status": {},
            "failed_checks": [],
            "warnings": [],
            "last_checked": datetime.now().isoformat()
        }
        
        framework_stats = {}
        
        for check in self.compliance_checks:
            try:
                # Run the actual check (simplified for demo)
                check_result = await self._execute_compliance_check(check)
                check.status = check_result["status"]
                check.last_checked = datetime.now()
                check.evidence = check_result.get("evidence", [])
                
                # Update framework statistics
                framework = check.framework
                if framework not in framework_stats:
                    framework_stats[framework] = {"total": 0, "compliant": 0, "warnings": 0, "failed": 0}
                
                framework_stats[framework]["total"] += 1
                
                if check.status == "compliant":
                    framework_stats[framework]["compliant"] += 1
                elif check.status == "warning":
                    framework_stats[framework]["warnings"] += 1
                    results["warnings"].append({
                        "check_id": check.check_id,
                        "name": check.name,
                        "framework": check.framework
                    })
                else:  # non_compliant
                    framework_stats[framework]["failed"] += 1
                    results["failed_checks"].append({
                        "check_id": check.check_id,
                        "name": check.name,
                        "framework": check.framework,
                        "requirement": check.requirement
                    })
                
            except Exception as e:
                logger.error(f"Error running compliance check {check.check_id}: {e}")
                framework_stats.setdefault(check.framework, {"total": 0, "compliant": 0, "warnings": 0, "failed": 0})["failed"] += 1
        
        # Calculate framework status
        for framework, stats in framework_stats.items():
            if stats["failed"] > 0:
                results["framework_status"][framework] = "non_compliant"
                results["overall_status"] = "non_compliant"
            elif stats["warnings"] > 0:
                results["framework_status"][framework] = "warning"
                if results["overall_status"] == "compliant":
                    results["overall_status"] = "warning"
            else:
                results["framework_status"][framework] = "compliant"
        
        return results
    
    async def _execute_compliance_check(self, check: ComplianceCheck) -> Dict[str, Any]:
        """Execute a specific compliance check."""
        # This would implement actual compliance checking logic
        # For demo purposes, we'll simulate the checks
        
        if check.check_id == "gdpr_data_retention":
            # Check if data retention policies are in place
            return {
                "status": "compliant",
                "evidence": ["Data retention policy configured", "Automated deletion enabled"]
            }
        elif check.check_id == "soc2_access_control":
            # Check access control implementation
            return {
                "status": "compliant",
                "evidence": ["MFA enabled", "Role-based access control", "Session management"]
            }
        elif check.check_id == "iso27001_encryption":
            # Check encryption implementation
            return {
                "status": "compliant",
                "evidence": ["TLS 1.3 enabled", "Database encryption", "API encryption"]
            }
        elif check.check_id == "pci_dss_logging":
            # Check logging compliance
            return {
                "status": "compliant",
                "evidence": ["Comprehensive audit logs", "Log retention policy", "Log monitoring"]
            }
        
        return {"status": "compliant", "evidence": []}

class SecurityMonitoringEngine:
    """
    Main security monitoring engine.
    
    Orchestrates threat detection, compliance monitoring,
    and security event response.
    """
    
    def __init__(self):
        self.pattern_engine = SecurityPatternEngine()
        self.compliance_monitor = ComplianceMonitor()
        
        # Security monitoring state
        self.security_events: List[SecurityEvent] = []
        self.active_threats: List[SecurityEvent] = []
        
        # Monitoring configuration
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.check_interval = 60  # 1 minute
        
        # Threat response
        self.auto_mitigation_enabled = True
        self.threat_response_actions = {
            ThreatLevel.CRITICAL: ["block_ip", "notify_security_team", "escalate"],
            ThreatLevel.HIGH: ["rate_limit", "notify_security_team", "monitor_closely"],
            ThreatLevel.MEDIUM: ["log_detailed", "monitor_closely"],
            ThreatLevel.LOW: ["log_standard"],
            ThreatLevel.INFO: ["log_info"]
        }
    
    async def start_monitoring(self) -> None:
        """Start security monitoring."""
        if self.is_monitoring:
            logger.warning("Security monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started security monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop security monitoring."""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped security monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main security monitoring loop."""
        while self.is_monitoring:
            try:
                # Run compliance checks periodically (every hour)
                current_time = datetime.now()
                if current_time.minute == 0:  # Top of the hour
                    await self._run_periodic_compliance_check()
                
                # Clean up old events and cache
                await self._cleanup_old_data()
                
                # Update threat assessment
                await self._update_threat_assessment()
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in security monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def process_security_event(self, event_data: Dict[str, Any]) -> List[SecurityEvent]:
        """Process incoming event for security analysis."""
        security_events = await self.pattern_engine.analyze_event(event_data)
        
        for event in security_events:
            self.security_events.append(event)
            
            # Check if it's an active threat
            if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                self.active_threats.append(event)
                
                # Trigger automatic mitigation if enabled
                if self.auto_mitigation_enabled:
                    await self._trigger_mitigation(event)
            
            # Log security event
            logger.warning(f"SECURITY EVENT ({event.threat_level.value}): {event.description}")
        
        return security_events
    
    async def _run_periodic_compliance_check(self) -> None:
        """Run periodic compliance monitoring."""
        try:
            compliance_results = await self.compliance_monitor.run_compliance_checks()
            
            if compliance_results["overall_status"] != "compliant":
                await self._send_compliance_alert(compliance_results)
                
        except Exception as e:
            logger.error(f"Error running compliance checks: {e}")
    
    async def _trigger_mitigation(self, event: SecurityEvent) -> None:
        """Trigger automatic mitigation for security threat."""
        actions = self.threat_response_actions.get(event.threat_level, [])
        
        for action in actions:
            try:
                await self._execute_mitigation_action(action, event)
            except Exception as e:
                logger.error(f"Error executing mitigation action {action}: {e}")
    
    async def _execute_mitigation_action(self, action: str, event: SecurityEvent) -> None:
        """Execute a specific mitigation action."""
        if action == "block_ip":
            logger.warning(f"Would block IP {event.source_ip} for event {event.event_id}")
            # In production, this would integrate with firewall/WAF
        elif action == "rate_limit":
            logger.warning(f"Would apply rate limiting to {event.source_ip}")
            # In production, this would configure rate limiting
        elif action == "notify_security_team":
            logger.warning(f"Would notify security team about event {event.event_id}")
            # In production, this would send notifications
        elif action == "escalate":
            logger.warning(f"Would escalate event {event.event_id} to security team")
            # In production, this would create incident tickets
        
        # Mark event as mitigated
        event.mitigated = True
    
    async def _update_threat_assessment(self) -> None:
        """Update overall threat assessment."""
        # Remove resolved threats
        self.active_threats = [
            threat for threat in self.active_threats
            if not threat.mitigated and 
               (datetime.now() - threat.timestamp).total_seconds() < 3600  # 1 hour
        ]
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old security data."""
        # Keep only last 1000 events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-500:]
        
        # Clean pattern engine cache
        current_time = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp) in self.pattern_engine.detection_cache.items():
            if (current_time - timestamp).total_seconds() > self.pattern_engine.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.pattern_engine.detection_cache[key]
    
    async def _send_compliance_alert(self, compliance_results: Dict[str, Any]) -> None:
        """Send compliance violation alert."""
        alert = {
            "type": "compliance_alert",
            "severity": "high" if compliance_results["overall_status"] == "non_compliant" else "medium",
            "message": f"Compliance status: {compliance_results['overall_status']}",
            "details": {
                "failed_checks": compliance_results["failed_checks"],
                "warnings": compliance_results["warnings"],
                "framework_status": compliance_results["framework_status"]
            },
            "timestamp": datetime.now().isoformat(),
            "source": "security_monitoring"
        }
        
        logger.warning(f"COMPLIANCE ALERT: {alert['message']}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security monitoring statistics."""
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        recent_events = [
            event for event in self.security_events
            if event.timestamp >= twenty_four_hours_ago
        ]
        
        threat_level_counts = {}
        event_type_counts = {}
        
        for event in recent_events:
            threat_level_counts[event.threat_level.value] = threat_level_counts.get(event.threat_level.value, 0) + 1
            event_type_counts[event.event_type.value] = event_type_counts.get(event.event_type.value, 0) + 1
        
        return {
            "monitoring_enabled": self.is_monitoring,
            "total_events_24h": len(recent_events),
            "active_threats": len(self.active_threats),
            "threat_level_distribution": threat_level_counts,
            "event_type_distribution": event_type_counts,
            "auto_mitigation_enabled": self.auto_mitigation_enabled,
            "pattern_detection_stats": self.pattern_engine.pattern_statistics,
            "compliance_frameworks": [check.framework for check in self.compliance_monitor.compliance_checks]
        }

# Global security monitoring
_security_monitor = None

def get_security_monitor() -> Optional[SecurityMonitoringEngine]:
    """Get global security monitoring instance."""
    return _security_monitor

async def initialize_security_monitoring() -> SecurityMonitoringEngine:
    """Initialize security monitoring system."""
    global _security_monitor
    
    _security_monitor = SecurityMonitoringEngine()
    
    await _security_monitor.start_monitoring()
    
    logger.info("Security monitoring initialized successfully")
    return _security_monitor 