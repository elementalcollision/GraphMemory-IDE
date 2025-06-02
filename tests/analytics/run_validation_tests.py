#!/usr/bin/env python3
"""
Comprehensive validation test runner for Analytics Engine Phase 3.
Executes all integration tests, benchmarks, and generates detailed reports.
"""

import asyncio
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationTestRunner:
    """Comprehensive test runner for Analytics Engine validation"""
    
    def __init__(self) -> None:
        self.test_results: Dict[str, Any] = {}
        self.start_time = time.time()
        self.test_categories = [
            "gpu_acceleration",
            "performance_monitoring", 
            "concurrent_processing",
            "analytics_engine",
            "benchmarking_suite",
            "monitoring_middleware",
            "api_endpoints",
            "error_handling",
            "realtime_updates"
        ]
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests and return comprehensive results"""
        logger.info("Starting comprehensive Analytics Engine Phase 3 validation")
        
        # Run pytest integration tests
        pytest_results = await self.run_pytest_tests()
        
        # Run custom validation tests
        custom_results = await self.run_custom_validation()
        
        # Run performance benchmarks
        benchmark_results = await self.run_performance_benchmarks()
        
        # Generate comprehensive report
        final_results = {
            "validation_summary": {
                "start_time": self.start_time,
                "end_time": time.time(),
                "total_duration": time.time() - self.start_time,
                "overall_status": "PASSED",  # Will be updated based on results
                "test_categories_passed": 0,
                "test_categories_total": len(self.test_categories)
            },
            "pytest_results": pytest_results,
            "custom_validation": custom_results,
            "performance_benchmarks": benchmark_results,
            "system_info": await self.get_system_info()
        }
        
        # Determine overall status
        final_results["validation_summary"]["overall_status"] = self.determine_overall_status(final_results)
        
        return final_results
    
    async def run_pytest_tests(self) -> Dict[str, Any]:
        """Run pytest integration tests"""
        logger.info("Running pytest integration tests...")
        
        try:
            # Run pytest with detailed output
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/analytics/test_integration_suite.py",
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results.json"
            ], capture_output=True, text=True, timeout=300)
            
            pytest_results = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            # Try to load JSON report if available
            try:
                with open("test_results.json", "r") as f:
                    pytest_results["detailed_results"] = json.load(f)
            except FileNotFoundError:
                logger.warning("Pytest JSON report not found")
            
            return pytest_results
            
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "error": "Pytest tests timed out after 300 seconds",
                "success": False
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "error": f"Failed to run pytest: {e}",
                "success": False
            }
    
    async def run_custom_validation(self) -> Dict[str, Any]:
        """Run custom validation tests"""
        logger.info("Running custom validation tests...")
        
        validation_results = {}
        
        # Test GPU acceleration
        validation_results["gpu_acceleration"] = await self.validate_gpu_acceleration()
        
        # Test performance monitoring
        validation_results["performance_monitoring"] = await self.validate_performance_monitoring()
        
        # Test concurrent processing
        validation_results["concurrent_processing"] = await self.validate_concurrent_processing()
        
        # Test analytics engine
        validation_results["analytics_engine"] = await self.validate_analytics_engine()
        
        # Test API endpoints
        validation_results["api_endpoints"] = await self.validate_api_endpoints()
        
        return validation_results
    
    async def validate_gpu_acceleration(self) -> Dict[str, Any]:
        """Validate GPU acceleration functionality"""
        try:
            from server.analytics.gpu_acceleration import gpu_manager
            
            status = gpu_manager.get_acceleration_status()
            
            validation = {
                "gpu_manager_available": True,
                "gpu_hardware_detected": status.get("gpu_available", False),
                "cugraph_backend": status.get("cugraph_backend", False),
                "fallback_reason": status.get("fallback_reason"),
                "supported_algorithms": len(gpu_manager._get_supported_algorithms()) > 0,
                "methods_available": {
                    "is_gpu_available": hasattr(gpu_manager, 'is_gpu_available'),
                    "is_gpu_enabled": hasattr(gpu_manager, 'is_gpu_enabled'),
                    "get_performance_estimate": hasattr(gpu_manager, 'get_performance_estimate')
                }
            }
            
            validation["success"] = all([
                validation["gpu_manager_available"],
                validation["supported_algorithms"],
                validation["methods_available"]["is_gpu_available"],
                validation["methods_available"]["is_gpu_enabled"]
            ])
            
            return validation
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_performance_monitoring(self) -> Dict[str, Any]:
        """Validate performance monitoring functionality"""
        try:
            from server.analytics.performance_monitor import performance_monitor
            
            # Test basic functionality
            performance_monitor.record_cache_hit()
            performance_monitor.record_cache_miss()
            performance_monitor.update_graph_size(100, 200)
            
            metrics = performance_monitor.get_system_metrics()
            summary = performance_monitor.get_performance_summary()
            
            validation = {
                "performance_monitor_available": True,
                "cache_tracking": "cache_statistics" in summary,
                "system_metrics": len(metrics) > 0,
                "required_methods": {
                    "update_graph_size": hasattr(performance_monitor, 'update_graph_size'),
                    "monitor_algorithm": hasattr(performance_monitor, 'monitor_algorithm'),
                    "get_performance_summary": hasattr(performance_monitor, 'get_performance_summary')
                }
            }
            
            validation["success"] = all([
                validation["performance_monitor_available"],
                validation["cache_tracking"],
                validation["system_metrics"],
                all(validation["required_methods"].values())
            ])
            
            return validation
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_concurrent_processing(self) -> Dict[str, Any]:
        """Validate concurrent processing functionality"""
        try:
            from server.analytics.concurrent_processing import concurrent_manager
            
            await concurrent_manager.initialize()
            
            status = concurrent_manager.get_executor_status()
            health = await concurrent_manager.health_check()
            
            validation = {
                "concurrent_manager_available": True,
                "initialization_success": status.get("initialized", False),
                "thread_executor": status.get("thread_executor_available", False),
                "process_executor": status.get("process_executor_available", False),
                "health_check": health.get("status") == "healthy"
            }
            
            await concurrent_manager.shutdown()
            
            validation["success"] = all([
                validation["concurrent_manager_available"],
                validation["initialization_success"],
                validation["thread_executor"],
                validation["process_executor"]
            ])
            
            return validation
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_analytics_engine(self) -> Dict[str, Any]:
        """Validate main analytics engine functionality"""
        try:
            from unittest.mock import Mock
            from server.analytics.engine import AnalyticsEngine
            
            # Create mock connection
            mock_conn = Mock()
            mock_conn.execute.return_value = []
            
            engine = AnalyticsEngine(mock_conn, "redis://localhost:6379")
            await engine.initialize()
            
            validation = {
                "engine_initialization": engine.initialized,
                "gpu_manager_integration": engine.gpu_manager is not None,
                "performance_monitor_integration": engine.performance_monitor is not None,
                "concurrent_manager_integration": engine.concurrent_manager is not None,
                "phase3_status": True
            }
            
            # Test Phase 3 status
            try:
                status = await engine.get_phase3_status()
                validation["phase3_status"] = "gpu_acceleration" in status
            except Exception:
                validation["phase3_status"] = False
            
            await engine.shutdown()
            
            validation["success"] = all([
                validation["engine_initialization"],
                validation["gpu_manager_integration"],
                validation["performance_monitor_integration"],
                validation["concurrent_manager_integration"]
            ])
            
            return validation
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_api_endpoints(self) -> Dict[str, Any]:
        """Validate API endpoint functionality"""
        try:
            from server.analytics.gpu_acceleration import gpu_manager
            from server.analytics.performance_monitor import performance_monitor
            
            validation = {
                "gpu_status_endpoint": True,
                "performance_metrics_endpoint": True,
                "health_check_endpoint": True
            }
            
            # Test GPU status endpoint functionality
            try:
                gpu_status = gpu_manager.get_acceleration_status()
                validation["gpu_status_endpoint"] = "gpu_available" in gpu_status
            except Exception:
                validation["gpu_status_endpoint"] = False
            
            # Test performance metrics endpoint functionality
            try:
                metrics = performance_monitor.get_performance_summary()
                validation["performance_metrics_endpoint"] = "timestamp" in metrics
            except Exception:
                validation["performance_metrics_endpoint"] = False
            
            validation["success"] = all(validation.values())
            
            return validation
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks"""
        logger.info("Running performance benchmarks...")
        
        try:
            from server.analytics.benchmarks import AnalyticsBenchmarkSuite
            
            suite = AnalyticsBenchmarkSuite()
            await suite.initialize()
            
            # Run basic benchmarks
            benchmark_results = {
                "centrality_benchmarks": [],
                "gpu_vs_cpu_benchmarks": [],
                "concurrent_processing_benchmarks": []
            }
            
            # Test centrality benchmarks with small graph sizes
            try:
                centrality_results = await suite.benchmark_centrality_algorithms([10, 20])
                benchmark_results["centrality_benchmarks"] = [
                    {
                        "test_name": r.test_name,
                        "execution_time": r.execution_time,
                        "success": r.success
                    } for r in centrality_results
                ]
            except Exception as e:
                benchmark_results["centrality_benchmarks"] = {"error": str(e)}
            
            # Test GPU vs CPU benchmarks
            try:
                gpu_cpu_results = await suite.benchmark_gpu_vs_cpu()
                benchmark_results["gpu_vs_cpu_benchmarks"] = [
                    {
                        "speedup_factor": r.speedup_factor,
                        "baseline_time": r.baseline_result.execution_time,
                        "optimized_time": r.optimized_result.execution_time
                    } for r in gpu_cpu_results
                ]
            except Exception as e:
                benchmark_results["gpu_vs_cpu_benchmarks"] = {"error": str(e)}
            
            return benchmark_results
            
        except Exception as e:
            return {"error": str(e), "success": False}
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information for the report"""
        try:
            import psutil
            import platform
            
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "disk_total_gb": psutil.disk_usage('/').total / (1024**3)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def determine_overall_status(self, results: Dict[str, Any]) -> str:
        """Determine overall validation status"""
        # Check pytest results
        pytest_success = results.get("pytest_results", {}).get("success", False)
        
        # Check custom validation results
        custom_validation = results.get("custom_validation", {})
        custom_success = all(
            result.get("success", False) 
            for result in custom_validation.values()
            if isinstance(result, dict)
        )
        
        # Check benchmark results
        benchmark_success = "error" not in results.get("performance_benchmarks", {})
        
        if pytest_success and custom_success and benchmark_success:
            return "PASSED"
        elif custom_success:  # Core functionality works
            return "PARTIAL"
        else:
            return "FAILED"
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive validation report"""
        report = []
        report.append("=" * 80)
        report.append("ANALYTICS ENGINE PHASE 3 - VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        summary = results["validation_summary"]
        report.append(f"Overall Status: {summary['overall_status']}")
        report.append(f"Total Duration: {summary['total_duration']:.2f} seconds")
        report.append(f"Test Categories: {summary['test_categories_passed']}/{summary['test_categories_total']}")
        report.append("")
        
        # Pytest Results
        pytest_results = results.get("pytest_results", {})
        report.append("PYTEST INTEGRATION TESTS")
        report.append("-" * 40)
        report.append(f"Status: {'PASSED' if pytest_results.get('success') else 'FAILED'}")
        if not pytest_results.get("success"):
            report.append(f"Error: {pytest_results.get('error', 'Unknown error')}")
        report.append("")
        
        # Custom Validation
        custom_validation = results.get("custom_validation", {})
        report.append("CUSTOM VALIDATION TESTS")
        report.append("-" * 40)
        for category, result in custom_validation.items():
            if isinstance(result, dict):
                status = "PASSED" if result.get("success") else "FAILED"
                report.append(f"{category}: {status}")
                if not result.get("success") and "error" in result:
                    report.append(f"  Error: {result['error']}")
        report.append("")
        
        # Performance Benchmarks
        benchmarks = results.get("performance_benchmarks", {})
        report.append("PERFORMANCE BENCHMARKS")
        report.append("-" * 40)
        if "error" in benchmarks:
            report.append(f"Benchmark Error: {benchmarks['error']}")
        else:
            centrality_count = len(benchmarks.get("centrality_benchmarks", []))
            gpu_cpu_count = len(benchmarks.get("gpu_vs_cpu_benchmarks", []))
            report.append(f"Centrality Benchmarks: {centrality_count} tests")
            report.append(f"GPU vs CPU Benchmarks: {gpu_cpu_count} tests")
        report.append("")
        
        # System Information
        system_info = results.get("system_info", {})
        report.append("SYSTEM INFORMATION")
        report.append("-" * 40)
        for key, value in system_info.items():
            if key != "error":
                report.append(f"{key}: {value}")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)

async def main() -> None:
    """Main function to run validation tests"""
    runner = ValidationTestRunner()
    
    try:
        # Run all validation tests
        results = await runner.run_all_tests()
        
        # Generate and save report
        report = runner.generate_report(results)
        
        # Save results to files
        with open("validation_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        with open("validation_report.txt", "w") as f:
            f.write(report)
        
        # Print report to console
        print(report)
        
        # Exit with appropriate code
        overall_status = results["validation_summary"]["overall_status"]
        if overall_status == "PASSED":
            sys.exit(0)
        elif overall_status == "PARTIAL":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        print(f"VALIDATION FAILED: {e}")
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main()) 