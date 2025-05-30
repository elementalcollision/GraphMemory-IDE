#!/usr/bin/env python3

"""
GraphMemory-IDE Security Report Generator
Phase 3 Day 1: Container Orchestration & Docker Production
Comprehensive security analysis and reporting automation
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess


class SecurityReportGenerator:
    """Comprehensive security report generation and analysis."""
    
    def __init__(self, reports_dir: str = "/reports"):
        self.reports_dir = Path(reports_dir)
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.summary = {
            "scan_date": self.timestamp,
            "total_vulnerabilities": 0,
            "critical_vulnerabilities": 0,
            "high_vulnerabilities": 0,
            "medium_vulnerabilities": 0,
            "low_vulnerabilities": 0,
            "containers_scanned": [],
            "compliance_status": "UNKNOWN",
            "security_score": 0
        }
    
    def load_json_report(self, filepath: Path) -> Optional[Dict]:
        """Load and parse JSON security report."""
        try:
            if filepath.exists():
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {filepath}: {e}")
        return None
    
    def analyze_trivy_results(self) -> Dict[str, Any]:
        """Analyze Trivy vulnerability scan results."""
        trivy_results = {
            "fastapi": {"vulnerabilities": [], "total": 0},
            "streamlit": {"vulnerabilities": [], "total": 0},
            "analytics": {"vulnerabilities": [], "total": 0}
        }
        
        components = ["fastapi", "streamlit", "analytics"]
        
        for component in components:
            sarif_file = self.reports_dir / f"{component}-security.sarif"
            sarif_data = self.load_json_report(sarif_file)
            
            if sarif_data and "runs" in sarif_data:
                vulnerabilities = []
                for run in sarif_data["runs"]:
                    if "results" in run:
                        for result in run["results"]:
                            vuln = {
                                "rule_id": result.get("ruleId", "Unknown"),
                                "level": result.get("level", "unknown"),
                                "message": result.get("message", {}).get("text", ""),
                                "locations": []
                            }
                            
                            if "locations" in result:
                                for location in result["locations"]:
                                    if "physicalLocation" in location:
                                        vuln["locations"].append(
                                            location["physicalLocation"].get("artifactLocation", {}).get("uri", "")
                                        )
                            
                            vulnerabilities.append(vuln)
                            
                            # Count by severity
                            if result.get("level") == "error":
                                self.summary["critical_vulnerabilities"] += 1
                            elif result.get("level") == "warning":
                                self.summary["high_vulnerabilities"] += 1
                            else:
                                self.summary["medium_vulnerabilities"] += 1
                
                trivy_results[component]["vulnerabilities"] = vulnerabilities
                trivy_results[component]["total"] = len(vulnerabilities)
                self.summary["containers_scanned"].append(component)
        
        return trivy_results
    
    def analyze_grype_results(self) -> Dict[str, Any]:
        """Analyze Grype vulnerability scan results."""
        grype_results = {
            "fastapi": {"matches": [], "total": 0},
            "streamlit": {"matches": [], "total": 0},
            "analytics": {"matches": [], "total": 0}
        }
        
        components = ["fastapi", "streamlit", "analytics"]
        
        for component in components:
            grype_file = self.reports_dir / f"{component}-grype.json"
            grype_data = self.load_json_report(grype_file)
            
            if grype_data and "matches" in grype_data:
                matches = []
                for match in grype_data["matches"]:
                    vuln_info = match.get("vulnerability", {})
                    artifact = match.get("artifact", {})
                    
                    vuln = {
                        "id": vuln_info.get("id", "Unknown"),
                        "severity": vuln_info.get("severity", "Unknown"),
                        "description": vuln_info.get("description", ""),
                        "package": artifact.get("name", ""),
                        "version": artifact.get("version", ""),
                        "fixed_in": vuln_info.get("fix", {}).get("versions", [])
                    }
                    
                    matches.append(vuln)
                    
                    # Count by severity
                    severity = vuln_info.get("severity", "").upper()
                    if severity == "CRITICAL":
                        self.summary["critical_vulnerabilities"] += 1
                    elif severity == "HIGH":
                        self.summary["high_vulnerabilities"] += 1
                    elif severity == "MEDIUM":
                        self.summary["medium_vulnerabilities"] += 1
                    else:
                        self.summary["low_vulnerabilities"] += 1
                
                grype_results[component]["matches"] = matches
                grype_results[component]["total"] = len(matches)
        
        return grype_results
    
    def analyze_hadolint_results(self) -> Dict[str, Any]:
        """Analyze Hadolint Dockerfile linting results."""
        hadolint_results = {
            "fastapi": {"issues": [], "total": 0},
            "streamlit": {"issues": [], "total": 0},
            "analytics": {"issues": [], "total": 0}
        }
        
        components = ["fastapi", "streamlit", "analytics"]
        
        for component in components:
            hadolint_file = self.reports_dir / f"{component}-hadolint.json"
            hadolint_data = self.load_json_report(hadolint_file)
            
            if hadolint_data and isinstance(hadolint_data, list):
                issues = []
                for issue in hadolint_data:
                    issue_info = {
                        "rule": issue.get("code", "Unknown"),
                        "level": issue.get("level", "info"),
                        "message": issue.get("message", ""),
                        "line": issue.get("line", 0),
                        "column": issue.get("column", 0)
                    }
                    issues.append(issue_info)
                
                hadolint_results[component]["issues"] = issues
                hadolint_results[component]["total"] = len(issues)
        
        return hadolint_results
    
    def calculate_security_score(self, trivy_results: Dict, grype_results: Dict, hadolint_results: Dict) -> int:
        """Calculate overall security score (0-100)."""
        base_score = 100
        
        # Deduct points for vulnerabilities
        total_critical = self.summary["critical_vulnerabilities"]
        total_high = self.summary["high_vulnerabilities"]
        total_medium = self.summary["medium_vulnerabilities"]
        total_low = self.summary["low_vulnerabilities"]
        
        # Critical vulnerabilities have the highest impact
        score_deduction = (total_critical * 15) + (total_high * 8) + (total_medium * 3) + (total_low * 1)
        
        # Deduct points for Dockerfile issues
        total_dockerfile_issues = sum([
            hadolint_results[comp]["total"] for comp in hadolint_results
        ])
        score_deduction += total_dockerfile_issues * 2
        
        final_score = max(0, base_score - score_deduction)
        return final_score
    
    def determine_compliance_status(self, security_score: int) -> str:
        """Determine compliance status based on security score."""
        if security_score >= 90:
            return "EXCELLENT"
        elif security_score >= 80:
            return "GOOD"
        elif security_score >= 70:
            return "ACCEPTABLE"
        elif security_score >= 60:
            return "NEEDS_IMPROVEMENT"
        else:
            return "CRITICAL"
    
    def generate_executive_summary(self, security_score: int, compliance_status: str) -> str:
        """Generate executive summary report."""
        return f"""
# GraphMemory-IDE Security Assessment - Executive Summary

**Assessment Date:** {self.timestamp}
**Overall Security Score:** {security_score}/100
**Compliance Status:** {compliance_status}

## Key Findings

### Vulnerability Summary
- **Critical Vulnerabilities:** {self.summary['critical_vulnerabilities']}
- **High Vulnerabilities:** {self.summary['high_vulnerabilities']}
- **Medium Vulnerabilities:** {self.summary['medium_vulnerabilities']}
- **Low Vulnerabilities:** {self.summary['low_vulnerabilities']}
- **Total Vulnerabilities:** {self.summary['total_vulnerabilities']}

### Containers Assessed
{', '.join(self.summary['containers_scanned'])}

## Recommendations

### Immediate Actions Required
{self._get_immediate_actions(security_score)}

### Compliance Status
{self._get_compliance_recommendations(compliance_status)}

### Next Steps
1. Review detailed technical findings in the full security report
2. Prioritize critical and high severity vulnerabilities for immediate remediation
3. Implement security scanning in CI/CD pipeline
4. Schedule regular security assessments
5. Update container base images and dependencies

---
*This report was generated automatically by GraphMemory-IDE Security Scanner*
"""
    
    def _get_immediate_actions(self, score: int) -> str:
        """Get immediate action recommendations based on score."""
        if score < 60:
            return """
- **URGENT:** Address all critical vulnerabilities immediately
- **URGENT:** Review and remediate high-severity vulnerabilities
- **URGENT:** Conduct security audit of container configurations
- **URGENT:** Implement security hardening measures"""
        elif score < 80:
            return """
- Address critical vulnerabilities within 24 hours
- Plan remediation for high-severity vulnerabilities
- Review container security configurations
- Update base images and dependencies"""
        else:
            return """
- Monitor for new vulnerabilities
- Maintain current security posture
- Consider implementing additional security measures"""
    
    def _get_compliance_recommendations(self, status: str) -> str:
        """Get compliance recommendations based on status."""
        if status in ["CRITICAL", "NEEDS_IMPROVEMENT"]:
            return "System does not meet security compliance standards. Immediate remediation required."
        elif status == "ACCEPTABLE":
            return "System meets minimum security standards but improvements recommended."
        elif status == "GOOD":
            return "System meets security compliance standards with minor improvements suggested."
        else:
            return "System exceeds security compliance standards. Maintain current practices."
    
    def generate_technical_report(self, trivy_results: Dict, grype_results: Dict, hadolint_results: Dict) -> str:
        """Generate detailed technical security report."""
        report = f"""
# GraphMemory-IDE Security Assessment - Technical Report

**Assessment Date:** {self.timestamp}
**Security Score:** {self.summary['security_score']}/100

## Vulnerability Analysis

### Container Vulnerability Scan Results (Trivy)
"""
        
        for component, results in trivy_results.items():
            report += f"""
#### {component.upper()} Container
- **Total Vulnerabilities:** {results['total']}
"""
            if results['vulnerabilities']:
                report += "- **Top Vulnerabilities:**\n"
                for vuln in results['vulnerabilities'][:5]:  # Top 5
                    report += f"  - {vuln['rule_id']}: {vuln['message'][:100]}...\n"
        
        report += """
### Package Vulnerability Analysis (Grype)
"""
        
        for component, results in grype_results.items():
            report += f"""
#### {component.upper()} Packages
- **Total Vulnerable Packages:** {results['total']}
"""
            if results['matches']:
                report += "- **Critical Packages:**\n"
                critical_matches = [m for m in results['matches'] if m['severity'] == 'Critical']
                for match in critical_matches[:5]:  # Top 5 critical
                    report += f"  - {match['package']} {match['version']}: {match['id']}\n"
        
        report += """
### Dockerfile Security Analysis (Hadolint)
"""
        
        for component, results in hadolint_results.items():
            report += f"""
#### {component.upper()} Dockerfile
- **Total Issues:** {results['total']}
"""
            if results['issues']:
                report += "- **Key Issues:**\n"
                for issue in results['issues'][:5]:  # Top 5
                    report += f"  - Line {issue['line']}: {issue['rule']} - {issue['message']}\n"
        
        report += """
## Security Recommendations

### Container Hardening
1. Update base images to latest security patches
2. Implement non-root user execution (✓ Already implemented)
3. Minimize attack surface by removing unnecessary packages
4. Implement resource limits and security contexts

### Vulnerability Management
1. Implement automated vulnerability scanning in CI/CD
2. Establish vulnerability remediation SLAs
3. Monitor security advisories for used packages
4. Implement dependency management policies

### Configuration Security
1. Follow CIS Docker Benchmark guidelines
2. Implement secrets management
3. Enable container image signing
4. Implement runtime security monitoring

---
*Detailed findings available in individual scan reports*
"""
        
        return report
    
    def generate_summary_file(self) -> None:
        """Generate concise summary file."""
        summary_content = f"""GraphMemory-IDE Security Scan Summary
========================================
Scan Date: {self.timestamp}
Security Score: {self.summary['security_score']}/100
Compliance Status: {self.summary['compliance_status']}

Vulnerability Counts:
- Critical: {self.summary['critical_vulnerabilities']}
- High: {self.summary['high_vulnerabilities']}
- Medium: {self.summary['medium_vulnerabilities']}
- Low: {self.summary['low_vulnerabilities']}
- Total: {self.summary['total_vulnerabilities']}

Containers Scanned: {', '.join(self.summary['containers_scanned'])}

Status: {'PASS' if self.summary['security_score'] >= 70 else 'FAIL'}
"""
        
        with open(self.reports_dir / "security-summary.txt", "w") as f:
            f.write(summary_content)
    
    def run_security_analysis(self) -> None:
        """Run complete security analysis and generate reports."""
        print("Starting comprehensive security analysis...")
        
        # Analyze results from all scanners
        trivy_results = self.analyze_trivy_results()
        grype_results = self.analyze_grype_results()
        hadolint_results = self.analyze_hadolint_results()
        
        # Calculate security metrics
        self.summary["total_vulnerabilities"] = (
            self.summary["critical_vulnerabilities"] +
            self.summary["high_vulnerabilities"] +
            self.summary["medium_vulnerabilities"] +
            self.summary["low_vulnerabilities"]
        )
        
        security_score = self.calculate_security_score(trivy_results, grype_results, hadolint_results)
        compliance_status = self.determine_compliance_status(security_score)
        
        self.summary["security_score"] = security_score
        self.summary["compliance_status"] = compliance_status
        
        # Generate reports
        executive_summary = self.generate_executive_summary(security_score, compliance_status)
        technical_report = self.generate_technical_report(trivy_results, grype_results, hadolint_results)
        
        # Write reports to files
        with open(self.reports_dir / "security-executive-summary.md", "w") as f:
            f.write(executive_summary)
        
        with open(self.reports_dir / "security-technical-report.md", "w") as f:
            f.write(technical_report)
        
        # Generate summary
        self.generate_summary_file()
        
        # Write JSON summary for automation
        with open(self.reports_dir / "security-summary.json", "w") as f:
            json.dump(self.summary, f, indent=2)
        
        print(f"Security analysis completed. Score: {security_score}/100")
        print(f"Compliance Status: {compliance_status}")
        print(f"Reports generated in {self.reports_dir}")


def main():
    """Main execution function."""
    try:
        generator = SecurityReportGenerator()
        generator.run_security_analysis()
        return 0
    except Exception as e:
        print(f"Error generating security report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 