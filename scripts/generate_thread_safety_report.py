#!/usr/bin/env python3
"""
Thread Safety Report Generator

This script generates comprehensive thread safety reports for the CI/CD pipeline,
integrating with the thread safety framework from SUBTASK-007.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ReportData(TypedDict):
    timestamp: str
    environment: Dict[str, Any]
    thread_safety_tests: Dict[str, Any]
    performance_benchmarks: Dict[str, Any]
    security_scan: Dict[str, Any]
    recommendations: List[str]

class ThreadSafetyReportGenerator:
    """
    Generates comprehensive thread safety reports for CI/CD integration.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.report_data: ReportData = {
            "timestamp": datetime.now().isoformat(),
            "environment": {},
            "thread_safety_tests": {},
            "performance_benchmarks": {},
            "security_scan": {},
            "recommendations": []
        }
    
    def validate_environment(self) -> bool:
        """Validate the development environment."""
        try:
            # Check Python version
            python_version = sys.version_info
            env_data = self.report_data["environment"]
            env_data["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
            
            # Check virtual environment
            python_executable = sys.executable
            env_data["virtual_environment"] = "codon-dev-env" in python_executable
            
            # Check Condon installation
            try:
                result = subprocess.run(["codon", "--version"], 
                                      capture_output=True, text=True, timeout=10)
                env_data["codon_installed"] = result.returncode == 0
                if result.returncode == 0:
                    env_data["codon_version"] = result.stdout.strip()
            except Exception:
                env_data["codon_installed"] = False
            
            # Check thread safety framework
            thread_safety_path = self.project_root / "tests" / "thread_safety"
            env_data["thread_safety_framework"] = thread_safety_path.exists()
            
            return True
            
        except Exception as e:
            print(f"❌ Environment validation failed: {e}")
            return False
    
    def run_thread_safety_tests(self) -> bool:
        """Run thread safety tests and collect results."""
        try:
            print("🧪 Running thread safety tests...")
            
            # Run thread safety tests
            cmd = [
                sys.executable, "-m", "pytest", 
                str(self.project_root / "tests" / "thread_safety"),
                "-v", "--tb=short", "--junitxml=thread-safety-results.xml"
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            end_time = time.time()
            
            # Parse results
            test_results = {
                "success": result.returncode == 0,
                "duration": end_time - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            self.report_data["thread_safety_tests"] = test_results
            
            # Parse JUnit XML if available
            junit_file = self.project_root / "thread-safety-results.xml"
            if junit_file.exists():
                test_results["junit_results"] = junit_file.read_text()
            
            if result.returncode == 0:
                print("✅ Thread safety tests passed")
                return True
            else:
                print("❌ Thread safety tests failed")
                return False
                
        except Exception as e:
            print(f"❌ Thread safety test error: {e}")
            if "thread_safety_tests" not in self.report_data:
                self.report_data["thread_safety_tests"] = {}
            self.report_data["thread_safety_tests"]["error"] = str(e)
            return False
    
    def run_performance_benchmarks(self) -> bool:
        """Run performance benchmarks."""
        try:
            print("📊 Running performance benchmarks...")
            
            # Run performance tests
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.project_root / "tests" / "thread_safety" / "test_thread_performance.py"),
                "-v", "--benchmark-only"
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            end_time = time.time()
            
            perf_results = {
                "success": result.returncode == 0,
                "duration": end_time - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            self.report_data["performance_benchmarks"] = perf_results
            
            if result.returncode == 0:
                print("✅ Performance benchmarks completed")
                return True
            else:
                print("❌ Performance benchmarks failed")
                return False
                
        except Exception as e:
            print(f"❌ Performance benchmark error: {e}")
            if "performance_benchmarks" not in self.report_data:
                self.report_data["performance_benchmarks"] = {}
            self.report_data["performance_benchmarks"]["error"] = str(e)
            return False
    
    def run_security_scan(self) -> bool:
        """Run security scanning."""
        try:
            print("🔒 Running security scan...")
            
            # Run Bandit security scan
            cmd = [
                sys.executable, "-m", "bandit", "-r", 
                str(self.project_root / "server"), "-f", "json"
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            end_time = time.time()
            
            security_results = {
                "success": result.returncode == 0,
                "duration": end_time - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            self.report_data["security_scan"] = security_results
            
            if result.returncode == 0:
                print("✅ Security scan completed")
                return True
            else:
                print("❌ Security scan failed")
                return False
                
        except Exception as e:
            print(f"❌ Security scan error: {e}")
            if "security_scan" not in self.report_data:
                self.report_data["security_scan"] = {}
            self.report_data["security_scan"]["error"] = str(e)
            return False
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Environment recommendations
        if not self.report_data["environment"]["virtual_environment"]:
            recommendations.append("⚠️ Not running in codon-dev-env virtual environment")
        
        if not self.report_data["environment"]["codon_installed"]:
            recommendations.append("⚠️ Condon not installed - install with: /bin/bash -c \"$(curl -fsSL https://exaloop.io/install.sh)\"")
        
        if not self.report_data["environment"]["thread_safety_framework"]:
            recommendations.append("⚠️ Thread safety framework not found")
        
        # Thread safety recommendations
        if not self.report_data["thread_safety_tests"]["success"]:
            recommendations.append("❌ Thread safety tests failed - review concurrent code")
        
        # Performance recommendations
        if not self.report_data["performance_benchmarks"]["success"]:
            recommendations.append("❌ Performance benchmarks failed - check for bottlenecks")
        
        # Security recommendations
        if not self.report_data["security_scan"]["success"]:
            recommendations.append("❌ Security scan failed - review security issues")
        
        # Positive recommendations
        if (self.report_data["thread_safety_tests"]["success"] and 
            self.report_data["performance_benchmarks"]["success"] and
            self.report_data["security_scan"]["success"]):
            recommendations.append("✅ All checks passed - ready for production deployment")
        
        return recommendations
    
    def generate_html_report(self) -> str:
        """Generate HTML report."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thread Safety Report - GraphMemory-IDE</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .success { background: #d4edda; border-color: #c3e6cb; }
        .warning { background: #fff3cd; border-color: #ffeaa7; }
        .error { background: #f8d7da; border-color: #f5c6cb; }
        .recommendation { margin: 10px 0; padding: 10px; border-radius: 3px; }
        .recommendation.success { background: #d4edda; }
        .recommendation.warning { background: #fff3cd; }
        .recommendation.error { background: #f8d7da; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧵 Thread Safety Report</h1>
        <p class="timestamp">Generated: {timestamp}</p>
        <p>GraphMemory-IDE with Condon Integration</p>
    </div>
    
    <div class="section">
        <h2>🔧 Environment Status</h2>
        <ul>
            <li>Python Version: {python_version}</li>
            <li>Virtual Environment: {virtual_env}</li>
            <li>Condon Installed: {codon_installed}</li>
            <li>Thread Safety Framework: {thread_safety_framework}</li>
        </ul>
    </div>
    
    <div class="section {thread_safety_class}">
        <h2>🧪 Thread Safety Tests</h2>
        <p>Status: {thread_safety_status}</p>
        <p>Duration: {thread_safety_duration:.2f}s</p>
        {thread_safety_output}
    </div>
    
    <div class="section {performance_class}">
        <h2>📊 Performance Benchmarks</h2>
        <p>Status: {performance_status}</p>
        <p>Duration: {performance_duration:.2f}s</p>
        {performance_output}
    </div>
    
    <div class="section {security_class}">
        <h2>🔒 Security Scan</h2>
        <p>Status: {security_status}</p>
        <p>Duration: {security_duration:.2f}s</p>
        {security_output}
    </div>
    
    <div class="section">
        <h2>💡 Recommendations</h2>
        {recommendations}
    </div>
</body>
</html>
        """
        
        # Prepare data for template
        thread_safety_success = self.report_data["thread_safety_tests"]["success"]
        performance_success = self.report_data["performance_benchmarks"]["success"]
        security_success = self.report_data["security_scan"]["success"]
        
        recommendations_html = ""
        for rec in self.report_data["recommendations"]:
            if rec.startswith("✅"):
                css_class = "success"
            elif rec.startswith("⚠️"):
                css_class = "warning"
            else:
                css_class = "error"
            recommendations_html += f'<div class="recommendation {css_class}">{rec}</div>'
        
        return html_template.format(
            timestamp=self.report_data["timestamp"],
            python_version=self.report_data["environment"].get("python_version", "Unknown"),
            virtual_env="✅ Active" if self.report_data["environment"].get("virtual_environment") else "❌ Not Active",
            codon_installed="✅ Installed" if self.report_data["environment"].get("codon_installed") else "❌ Not Installed",
            thread_safety_framework="✅ Available" if self.report_data["environment"].get("thread_safety_framework") else "❌ Missing",
            thread_safety_class="success" if thread_safety_success else "error",
            thread_safety_status="✅ PASSED" if thread_safety_success else "❌ FAILED",
            thread_safety_duration=self.report_data["thread_safety_tests"].get("duration", 0),
            thread_safety_output=f"<pre>{self.report_data['thread_safety_tests'].get('stdout', 'No output')}</pre>" if not thread_safety_success else "",
            performance_class="success" if performance_success else "error",
            performance_status="✅ PASSED" if performance_success else "❌ FAILED",
            performance_duration=self.report_data["performance_benchmarks"].get("duration", 0),
            performance_output=f"<pre>{self.report_data['performance_benchmarks'].get('stdout', 'No output')}</pre>" if not performance_success else "",
            security_class="success" if security_success else "error",
            security_status="✅ PASSED" if security_success else "❌ FAILED",
            security_duration=self.report_data["security_scan"].get("duration", 0),
            security_output=f"<pre>{self.report_data['security_scan'].get('stdout', 'No output')}</pre>" if not security_success else "",
            recommendations=recommendations_html
        )
    
    def generate_report(self) -> bool:
        """Generate comprehensive thread safety report."""
        try:
            print("📋 Generating thread safety report...")
            
            # Validate environment
            if not self.validate_environment():
                print("❌ Environment validation failed")
                return False
            
            # Run tests
            thread_safety_success = self.run_thread_safety_tests()
            performance_success = self.run_performance_benchmarks()
            security_success = self.run_security_scan()
            
            # Generate recommendations
            self.report_data["recommendations"] = self.generate_recommendations()
            
            # Generate reports
            reports_dir = self.project_root / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            # JSON report
            json_report_path = reports_dir / "thread_safety_report.json"
            with open(json_report_path, "w") as f:
                json.dump(self.report_data, f, indent=2)
            
            # HTML report
            html_report_path = reports_dir / "thread_safety_report.html"
            html_content = self.generate_html_report()
            with open(html_report_path, "w") as f:
                f.write(html_content)
            
            print(f"✅ Reports generated:")
            print(f"   📄 JSON: {json_report_path}")
            print(f"   🌐 HTML: {html_report_path}")
            
            # Print summary
            print("\n📊 Summary:")
            print(f"   🧪 Thread Safety: {'✅ PASSED' if thread_safety_success else '❌ FAILED'}")
            print(f"   📊 Performance: {'✅ PASSED' if performance_success else '❌ FAILED'}")
            print(f"   🔒 Security: {'✅ PASSED' if security_success else '❌ FAILED'}")
            
            return thread_safety_success and performance_success and security_success
            
        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            return False

def main():
    """Main function."""
    print("🚀 Thread Safety Report Generator")
    print("=" * 50)
    
    generator = ThreadSafetyReportGenerator()
    success = generator.generate_report()
    
    if success:
        print("\n✅ Thread safety report generation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Thread safety report generation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 