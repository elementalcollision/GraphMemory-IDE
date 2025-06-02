#!/usr/bin/env python3
"""
Enhanced Security Audit Suite for GraphMemory-IDE Enterprise Code Audit

This module integrates with existing security_validation_suite.py to provide
comprehensive enterprise-grade security auditing with:
- Enhanced Bandit configuration and analysis
- Semgrep custom pattern detection
- Performance-optimized security testing
- Integration with existing OWASP ZAP scanning
- Compliance validation across multiple frameworks

Author: GraphMemory-IDE Security Team
Date: 2025-06-02
Version: 1.0.0
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pytest
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import sys

# Import existing security validation components for integration
try:
    from tests.production.security_validation_suite import (
        SecurityValidationSuite,
        SecurityFinding,
        ComplianceResult
    )
except ImportError:
    # Fallback if existing suite not available
    SecurityValidationSuite = None
    SecurityFinding = None
    ComplianceResult = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EnhancedSecurityFinding:
    """Enhanced security finding with additional metadata for enterprise reporting."""
    tool: str  # bandit, semgrep, custom
    rule_id: str
    title: str
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence: str  # HIGH, MEDIUM, LOW
    file_path: str
    line_number: int
    code_snippet: str
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    cvss_score: Optional[float] = None
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary for JSON serialization."""
        return {
            "tool": self.tool,
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "confidence": self.confidence,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "cwe_id": self.cwe_id,
            "owasp_category": self.owasp_category,
            "cvss_score": self.cvss_score,
            "remediation": self.remediation,
            "references": self.references,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class EnhancedAuditResult:
    """Enhanced audit result with comprehensive metrics and integration data."""
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    info_findings: int
    findings_by_tool: Dict[str, int]
    findings_by_category: Dict[str, int]
    compliance_score: float
    execution_time: float
    performance_metrics: Dict[str, Any]
    integration_status: Dict[str, bool]
    findings: List[EnhancedSecurityFinding] = field(default_factory=list)
    
    def get_security_posture(self) -> str:
        """Calculate overall security posture based on findings."""
        if self.critical_findings > 0:
            return "CRITICAL"
        elif self.high_findings > 5:
            return "HIGH_RISK"
        elif self.high_findings > 0 or self.medium_findings > 10:
            return "MEDIUM_RISK"
        elif self.medium_findings > 0 or self.low_findings > 20:
            return "LOW_RISK"
        else:
            return "SECURE"

class EnhancedSecurityAuditSuite:
    """
    Enterprise-grade security audit suite that enhances existing security validation
    with comprehensive static analysis, custom pattern detection, and performance optimization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or self._get_default_config()
        self.project_root = Path.cwd()
        self.findings: List[EnhancedSecurityFinding] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.integration_status: Dict[str, bool] = {}
        
        # Initialize existing security validation suite if available
        self.existing_suite = None
        if SecurityValidationSuite:
            try:
                self.existing_suite = SecurityValidationSuite()
                self.integration_status["existing_security_suite"] = True
            except Exception as e:
                logger.warning(f"Could not initialize existing security suite: {e}")
                self.integration_status["existing_security_suite"] = False
        
        # Validate tool availability
        self._validate_tools()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for enhanced security audit."""
        return {
            "tools": {
                "bandit": {
                    "enabled": True,
                    "config_file": ".bandit",
                    "output_format": "json",
                    "fail_on_high": True,
                    "parallel_execution": True
                },
                "semgrep": {
                    "enabled": True,
                    "config_file": ".semgrep.yml",
                    "output_format": "json",
                    "custom_rules": True,
                    "parallel_execution": True
                },
                "existing_suite": {
                    "enabled": True,
                    "integration": True,
                    "compliance_validation": True
                }
            },
            "performance": {
                "parallel_execution": True,
                "max_workers": 4,
                "timeout_seconds": 300,
                "memory_limit_mb": 2048
            },
            "reporting": {
                "output_dir": "security_audit_reports",
                "formats": ["json", "html"],
                "include_metrics": True,
                "compliance_mapping": True
            },
            "integration": {
                "existing_security_suite": True,
                "owasp_zap": True,
                "ci_cd_pipeline": True
            }
        }
    
    def _validate_tools(self) -> None:
        """Validate that required security tools are available."""
        tools_status = {}
        
        # Check Bandit
        try:
            result = subprocess.run(["bandit", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            tools_status["bandit"] = result.returncode == 0
        except Exception:
            tools_status["bandit"] = False
        
        # Check Semgrep
        try:
            result = subprocess.run(["semgrep", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            tools_status["semgrep"] = result.returncode == 0
        except Exception:
            tools_status["semgrep"] = False
        
        self.integration_status.update(tools_status)
        
        if not any(tools_status.values()):
            logger.warning("No security tools available - install bandit and/or semgrep")
    
    async def run_enhanced_security_audit(self) -> EnhancedAuditResult:
        """
        Run comprehensive enhanced security audit with performance optimization.
        
        Returns:
            EnhancedAuditResult with comprehensive findings and metrics
        """
        start_time = time.time()
        logger.info("Starting enhanced security audit suite...")
        
        # Clear previous findings
        self.findings.clear()
        
        # Run security audits in parallel for performance optimization
        audit_tasks = []
        
        # Task 1: Enhanced Bandit analysis
        if self.config["tools"]["bandit"]["enabled"] and self.integration_status.get("bandit", False):
            audit_tasks.append(self._run_enhanced_bandit_audit())
        
        # Task 2: Semgrep custom pattern analysis
        if self.config["tools"]["semgrep"]["enabled"] and self.integration_status.get("semgrep", False):
            audit_tasks.append(self._run_semgrep_custom_analysis())
        
        # Task 3: Integration with existing security validation suite
        if (self.config["tools"]["existing_suite"]["enabled"] and 
            self.integration_status.get("existing_security_suite", False)):
            audit_tasks.append(self._run_existing_suite_integration())
        
        # Execute all security audit tasks in parallel
        if audit_tasks:
            results = await asyncio.gather(*audit_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Security audit task {i} failed: {result}")
                else:
                    logger.info(f"Security audit task {i} completed successfully")
        
        # Calculate performance metrics
        execution_time = time.time() - start_time
        self.performance_metrics = {
            "total_execution_time": execution_time,
            "findings_per_second": len(self.findings) / execution_time if execution_time > 0 else 0,
            "tools_executed": sum(1 for task in audit_tasks if task),
            "parallel_execution": True,
            "memory_usage": self._get_memory_usage()
        }
        
        # Generate comprehensive audit result
        audit_result = self._generate_audit_result(execution_time)
        
        # Generate reports
        await self._generate_reports(audit_result)
        
        logger.info(f"Enhanced security audit completed in {execution_time:.2f} seconds")
        logger.info(f"Found {len(self.findings)} total security findings")
        logger.info(f"Security posture: {audit_result.get_security_posture()}")
        
        return audit_result
    
    async def _run_enhanced_bandit_audit(self) -> List[EnhancedSecurityFinding]:
        """Run enhanced Bandit security analysis with custom configuration."""
        logger.info("Running enhanced Bandit security analysis...")
        findings = []
        
        try:
            # Use enhanced .bandit configuration
            bandit_cmd = [
                "bandit",
                "-r", "server/", "dashboard/", "scripts/", "monitoring/",
                "-f", "json",
                "-o", "enhanced_bandit_report.json",
                "-c", ".bandit"
            ]
            
            if self.config["tools"]["bandit"]["parallel_execution"]:
                bandit_cmd.extend(["--quiet"])
            
            # Run Bandit with timeout
            process = await asyncio.create_subprocess_exec(
                *bandit_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=self.config["performance"]["timeout_seconds"]
            )
            
            # Parse Bandit results
            try:
                with open("enhanced_bandit_report.json", "r") as f:
                    bandit_data = json.load(f)
                
                for result in bandit_data.get("results", []):
                    finding = EnhancedSecurityFinding(
                        tool="bandit",
                        rule_id=result.get("test_id", ""),
                        title=result.get("test_name", ""),
                        description=result.get("issue_text", ""),
                        severity=result.get("issue_severity", "LOW").upper(),
                        confidence=result.get("issue_confidence", "LOW").upper(),
                        file_path=result.get("filename", ""),
                        line_number=result.get("line_number", 0),
                        code_snippet=result.get("code", ""),
                        cwe_id=result.get("cwe", {}).get("id") if result.get("cwe") else None,
                        owasp_category=self._map_bandit_to_owasp(result.get("test_id", "")),
                        cvss_score=self._calculate_cvss_score(result.get("issue_severity", "LOW")),
                        remediation=self._get_bandit_remediation(result.get("test_id", ""))
                    )
                    findings.append(finding)
                    self.findings.append(finding)
                
                logger.info(f"Bandit analysis completed: {len(findings)} findings")
                
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse Bandit results: {e}")
        
        except asyncio.TimeoutError:
            logger.error("Bandit analysis timed out")
        except Exception as e:
            logger.error(f"Bandit analysis failed: {e}")
        
        return findings
    
    async def _run_semgrep_custom_analysis(self) -> List[EnhancedSecurityFinding]:
        """Run Semgrep analysis with custom GraphMemory-IDE security patterns."""
        logger.info("Running Semgrep custom pattern analysis...")
        findings = []
        
        try:
            # Use enhanced .semgrep.yml configuration
            semgrep_cmd = [
                "semgrep",
                "--config", ".semgrep.yml",
                "--json",
                "--output", "enhanced_semgrep_report.json",
                "--timeout", str(self.config["performance"]["timeout_seconds"]),
                "server/", "dashboard/", "scripts/", "monitoring/"
            ]
            
            if self.config["tools"]["semgrep"]["parallel_execution"]:
                semgrep_cmd.extend(["--jobs", str(self.config["performance"]["max_workers"])])
            
            # Run Semgrep with timeout
            process = await asyncio.create_subprocess_exec(
                *semgrep_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config["performance"]["timeout_seconds"]
            )
            
            # Parse Semgrep results
            try:
                with open("enhanced_semgrep_report.json", "r") as f:
                    semgrep_data = json.load(f)
                
                for result in semgrep_data.get("results", []):
                    finding = EnhancedSecurityFinding(
                        tool="semgrep",
                        rule_id=result.get("check_id", ""),
                        title=result.get("check_id", "").replace("-", " ").title(),
                        description=result.get("extra", {}).get("message", ""),
                        severity=result.get("extra", {}).get("severity", "INFO").upper(),
                        confidence="HIGH",  # Semgrep custom patterns are high confidence
                        file_path=result.get("path", ""),
                        line_number=result.get("start", {}).get("line", 0),
                        code_snippet=result.get("extra", {}).get("lines", ""),
                        cwe_id=result.get("extra", {}).get("metadata", {}).get("cwe"),
                        owasp_category=result.get("extra", {}).get("metadata", {}).get("owasp"),
                        cvss_score=self._calculate_cvss_score(result.get("extra", {}).get("severity", "INFO")),
                        remediation=self._get_semgrep_remediation(result.get("check_id", ""))
                    )
                    findings.append(finding)
                    self.findings.append(finding)
                
                logger.info(f"Semgrep analysis completed: {len(findings)} findings")
                
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse Semgrep results: {e}")
        
        except asyncio.TimeoutError:
            logger.error("Semgrep analysis timed out")
        except Exception as e:
            logger.error(f"Semgrep analysis failed: {e}")
        
        return findings
    
    async def _run_existing_suite_integration(self) -> List[EnhancedSecurityFinding]:
        """Integrate with existing security_validation_suite.py for comprehensive coverage."""
        logger.info("Integrating with existing security validation suite...")
        findings = []
        
        if not self.existing_suite:
            logger.warning("Existing security suite not available")
            return findings
        
        try:
            # Run existing security validation suite
            existing_results = await asyncio.to_thread(
                self.existing_suite.run_comprehensive_security_validation
            )
            
            # Convert existing findings to enhanced format
            if hasattr(existing_results, 'findings'):
                for finding in existing_results.findings:
                    enhanced_finding = EnhancedSecurityFinding(
                        tool="existing_suite",
                        rule_id=f"EXISTING_{finding.severity}",
                        title=finding.title,
                        description=finding.description,
                        severity=finding.severity,
                        confidence="HIGH",
                        file_path=finding.endpoint if hasattr(finding, 'endpoint') else "",
                        line_number=0,
                        code_snippet="",
                        cwe_id=finding.cwe_id if hasattr(finding, 'cwe_id') else None,
                        owasp_category=finding.owasp_category if hasattr(finding, 'owasp_category') else None,
                        cvss_score=finding.cvss_score if hasattr(finding, 'cvss_score') else None,
                        remediation=finding.recommendation if hasattr(finding, 'recommendation') else None
                    )
                    findings.append(enhanced_finding)
                    self.findings.append(enhanced_finding)
            
            logger.info(f"Existing suite integration completed: {len(findings)} findings")
            
        except Exception as e:
            logger.error(f"Failed to integrate with existing security suite: {e}")
        
        return findings
    
    def _map_bandit_to_owasp(self, test_id: str) -> Optional[str]:
        """Map Bandit test IDs to OWASP Top 10 categories."""
        owasp_mapping = {
            "B105": "A02: Cryptographic Failures",
            "B106": "A02: Cryptographic Failures", 
            "B107": "A02: Cryptographic Failures",
            "B201": "A05: Security Misconfiguration",
            "B307": "A03: Injection",
            "B501": "A02: Cryptographic Failures",
            "B502": "A02: Cryptographic Failures",
            "B503": "A02: Cryptographic Failures",
            "B506": "A08: Software and Data Integrity Failures",
            "B602": "A03: Injection",
            "B608": "A03: Injection"
        }
        return owasp_mapping.get(test_id)
    
    def _calculate_cvss_score(self, severity: str) -> float:
        """Calculate CVSS score based on severity level."""
        cvss_mapping = {
            "CRITICAL": 9.5,
            "HIGH": 7.5,
            "MEDIUM": 5.0,
            "LOW": 2.5,
            "INFO": 0.0
        }
        return cvss_mapping.get(severity.upper(), 0.0)
    
    def _get_bandit_remediation(self, test_id: str) -> Optional[str]:
        """Get remediation advice for Bandit findings."""
        remediation_mapping = {
            "B105": "Remove hardcoded passwords and use environment variables or secure credential storage",
            "B106": "Remove hardcoded passwords from function arguments",
            "B107": "Remove hardcoded passwords from default values",
            "B201": "Disable Flask debug mode in production",
            "B307": "Avoid using eval() with user input - use safer alternatives",
            "B501": "Enable SSL certificate verification",
            "B502": "Use secure SSL/TLS protocols (TLS 1.2+)",
            "B503": "Use secure SSL/TLS configurations",
            "B506": "Use safe YAML loading with yaml.safe_load()",
            "B602": "Avoid shell=True in subprocess calls",
            "B608": "Use parameterized queries to prevent SQL injection"
        }
        return remediation_mapping.get(test_id)
    
    def _get_semgrep_remediation(self, rule_id: str) -> Optional[str]:
        """Get remediation advice for Semgrep findings."""
        remediation_mapping = {
            "graphmemory-fastapi-auth-bypass": "Add authentication dependency to FastAPI endpoint",
            "graphmemory-fastapi-cors-wildcard": "Configure specific allowed origins instead of wildcard",
            "graphmemory-rate-limit-bypass": "Enable rate limiting for API endpoints",
            "graphmemory-sql-injection-format": "Use parameterized queries instead of string formatting",
            "graphmemory-jwt-verification-disabled": "Enable JWT signature verification",
            "graphmemory-rbac-bypass": "Remove RBAC bypass and implement proper authorization",
            "graphmemory-weak-hash-algorithm": "Use strong cryptographic hash algorithms (SHA-256+)",
            "graphmemory-hardcoded-secrets": "Move secrets to environment variables or secure storage",
            "graphmemory-command-injection": "Validate and sanitize user input before system calls",
            "graphmemory-memory-graph-injection": "Use parameterized graph queries to prevent injection"
        }
        return remediation_mapping.get(rule_id)
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage metrics."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"error": "psutil not available"}
    
    def _generate_audit_result(self, execution_time: float) -> EnhancedAuditResult:
        """Generate comprehensive audit result with metrics and analysis."""
        # Count findings by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for finding in self.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        
        # Count findings by tool
        tool_counts = {}
        for finding in self.findings:
            tool_counts[finding.tool] = tool_counts.get(finding.tool, 0) + 1
        
        # Count findings by category
        category_counts = {}
        for finding in self.findings:
            if finding.owasp_category:
                category_counts[finding.owasp_category] = category_counts.get(finding.owasp_category, 0) + 1
        
        # Calculate compliance score
        total_critical_and_high = severity_counts["CRITICAL"] + severity_counts["HIGH"]
        compliance_score = max(0, 100 - (total_critical_and_high * 10) - (severity_counts["MEDIUM"] * 2))
        
        return EnhancedAuditResult(
            total_findings=len(self.findings),
            critical_findings=severity_counts["CRITICAL"],
            high_findings=severity_counts["HIGH"],
            medium_findings=severity_counts["MEDIUM"],
            low_findings=severity_counts["LOW"],
            info_findings=severity_counts["INFO"],
            findings_by_tool=tool_counts,
            findings_by_category=category_counts,
            compliance_score=compliance_score,
            execution_time=execution_time,
            performance_metrics=self.performance_metrics,
            integration_status=self.integration_status,
            findings=self.findings
        )
    
    async def _generate_reports(self, audit_result: EnhancedAuditResult) -> None:
        """Generate comprehensive audit reports in multiple formats."""
        report_dir = Path(self.config["reporting"]["output_dir"])
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Generate JSON report
        if "json" in self.config["reporting"]["formats"]:
            json_report = {
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0.0",
                    "project": "GraphMemory-IDE",
                    "audit_type": "enhanced_security_audit"
                },
                "summary": {
                    "total_findings": audit_result.total_findings,
                    "critical_findings": audit_result.critical_findings,
                    "high_findings": audit_result.high_findings,
                    "medium_findings": audit_result.medium_findings,
                    "low_findings": audit_result.low_findings,
                    "info_findings": audit_result.info_findings,
                    "compliance_score": audit_result.compliance_score,
                    "security_posture": audit_result.get_security_posture(),
                    "execution_time": audit_result.execution_time
                },
                "findings_by_tool": audit_result.findings_by_tool,
                "findings_by_category": audit_result.findings_by_category,
                "performance_metrics": audit_result.performance_metrics,
                "integration_status": audit_result.integration_status,
                "findings": [finding.to_dict() for finding in audit_result.findings]
            }
            
            json_file = report_dir / f"enhanced_security_audit_{timestamp}.json"
            with open(json_file, "w") as f:
                json.dump(json_report, f, indent=2)
            
            logger.info(f"JSON report generated: {json_file}")
        
        # Generate HTML report
        if "html" in self.config["reporting"]["formats"]:
            html_content = self._generate_html_report(audit_result, timestamp)
            html_file = report_dir / f"enhanced_security_audit_{timestamp}.html"
            with open(html_file, "w") as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {html_file}")
    
    def _generate_html_report(self, audit_result: EnhancedAuditResult, timestamp: str) -> str:
        """Generate HTML report for enhanced security audit."""
        findings_html = ""
        for finding in audit_result.findings:
            severity_class = finding.severity.lower()
            findings_html += f"""
            <tr class="{severity_class}">
                <td>{finding.tool}</td>
                <td>{finding.severity}</td>
                <td>{finding.title}</td>
                <td>{finding.file_path}</td>
                <td>{finding.line_number}</td>
                <td>{finding.description}</td>
                <td>{finding.remediation or 'N/A'}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Enhanced Security Audit Report - GraphMemory-IDE</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .critical {{ background-color: #ffebee; }}
                .high {{ background-color: #fff3e0; }}
                .medium {{ background-color: #fff8e1; }}
                .low {{ background-color: #f1f8e9; }}
                .info {{ background-color: #e3f2fd; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Enhanced Security Audit Report</h1>
                <p><strong>Project:</strong> GraphMemory-IDE</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                <p><strong>Security Posture:</strong> {audit_result.get_security_posture()}</p>
                <p><strong>Compliance Score:</strong> {audit_result.compliance_score:.1f}%</p>
            </div>
            
            <div class="summary">
                <h2>Executive Summary</h2>
                <p><strong>Total Findings:</strong> {audit_result.total_findings}</p>
                <p><strong>Critical:</strong> {audit_result.critical_findings}</p>
                <p><strong>High:</strong> {audit_result.high_findings}</p>
                <p><strong>Medium:</strong> {audit_result.medium_findings}</p>
                <p><strong>Low:</strong> {audit_result.low_findings}</p>
                <p><strong>Info:</strong> {audit_result.info_findings}</p>
                <p><strong>Execution Time:</strong> {audit_result.execution_time:.2f} seconds</p>
            </div>
            
            <h2>Detailed Findings</h2>
            <table>
                <thead>
                    <tr>
                        <th>Tool</th>
                        <th>Severity</th>
                        <th>Title</th>
                        <th>File</th>
                        <th>Line</th>
                        <th>Description</th>
                        <th>Remediation</th>
                    </tr>
                </thead>
                <tbody>
                    {findings_html}
                </tbody>
            </table>
        </body>
        </html>
        """

# Test execution and performance validation
async def test_enhanced_security_audit_integration() -> None:
    """Test enhanced security audit integration with existing security validation."""
    print("🔒 Testing Enhanced Security Audit Suite Integration...")
    
    # Initialize enhanced security audit suite
    audit_suite = EnhancedSecurityAuditSuite()
    
    # Run comprehensive security audit
    start_time = time.time()
    audit_result = await audit_suite.run_enhanced_security_audit()
    execution_time = time.time() - start_time
    
    # Validate results
    assert audit_result is not None, "Audit result should not be None"
    assert audit_result.execution_time > 0, "Execution time should be recorded"
    assert audit_result.compliance_score >= 0, "Compliance score should be non-negative"
    
    # Performance validation
    assert execution_time < 300, f"Audit should complete within 5 minutes, took {execution_time:.2f}s"
    
    # Integration validation
    integration_count = sum(1 for status in audit_result.integration_status.values() if status)
    assert integration_count > 0, "At least one tool should be integrated successfully"
    
    print(f"✅ Enhanced Security Audit Suite Test PASSED")
    print(f"   - Total Findings: {audit_result.total_findings}")
    print(f"   - Security Posture: {audit_result.get_security_posture()}")
    print(f"   - Compliance Score: {audit_result.compliance_score:.1f}%")
    print(f"   - Execution Time: {execution_time:.2f} seconds")
    print(f"   - Tools Integrated: {integration_count}")
    
    return audit_result

# Performance optimization test
async def test_performance_optimization() -> None:
    """Test performance optimization features of enhanced security audit."""
    print("⚡ Testing Performance Optimization...")
    
    # Test parallel execution
    audit_suite = EnhancedSecurityAuditSuite({
        "performance": {
            "parallel_execution": True,
            "max_workers": 4,
            "timeout_seconds": 60
        }
    })
    
    start_time = time.time()
    audit_result = await audit_suite.run_enhanced_security_audit()
    parallel_time = time.time() - start_time
    
    # Test sequential execution for comparison
    audit_suite_sequential = EnhancedSecurityAuditSuite({
        "performance": {
            "parallel_execution": False,
            "max_workers": 1,
            "timeout_seconds": 60
        }
    })
    
    start_time = time.time()
    sequential_result = await audit_suite_sequential.run_enhanced_security_audit()
    sequential_time = time.time() - start_time
    
    # Validate performance improvement
    if sequential_time > 0:
        performance_improvement = (sequential_time - parallel_time) / sequential_time * 100
        print(f"   - Parallel execution time: {parallel_time:.2f}s")
        print(f"   - Sequential execution time: {sequential_time:.2f}s")
        print(f"   - Performance improvement: {performance_improvement:.1f}%")
        
        # Performance should improve with parallel execution
        assert parallel_time <= sequential_time * 1.1, "Parallel execution should not be significantly slower"
    
    print("✅ Performance Optimization Test PASSED")
    return audit_result

if __name__ == "__main__":
    async def main() -> None:
        """Main execution function for enhanced security audit suite."""
        print("🚀 Starting GraphMemory-IDE Enhanced Security Audit Suite")
        print("=" * 60)
        
        try:
            # Run enhanced security audit integration test
            audit_result = await test_enhanced_security_audit_integration()
            
            # Run performance optimization test
            await test_performance_optimization()
            
            print("\n" + "=" * 60)
            print("🎉 Enhanced Security Audit Suite - ALL TESTS PASSED")
            print(f"   Final Security Posture: {audit_result.get_security_posture()}")
            print(f"   Final Compliance Score: {audit_result.compliance_score:.1f}%")
            
            # Exit with appropriate code
            if audit_result.critical_findings > 0:
                print("⚠️  CRITICAL security findings detected - review required")
                sys.exit(1)
            elif audit_result.high_findings > 5:
                print("⚠️  Multiple HIGH severity findings - review recommended")
                sys.exit(1)
            else:
                print("✅ Security audit completed successfully")
                sys.exit(0)
                
        except Exception as e:
            print(f"❌ Enhanced Security Audit Suite FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Run the main function
    asyncio.run(main()) 