"""
DigitalOcean Cloud Environment Testing Suite
Comprehensive validation for cloud deployment, health checks, and API endpoints.
"""

import os
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import pytest
import httpx
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from tests.conftest import async_client
from tests.load_testing.test_concurrent_user_simulation import (
    ConcurrentUserSimulator,
    GraphMemoryWorkflowSimulator,
    LoadTestMetrics
)


@dataclass
class CloudEnvironment:
    """Production cloud environment configuration."""
    name: str
    base_url: str
    app_name: str
    region: str
    environment_type: str
    health_check_endpoint: str = "/health"
    deployment_timeout: int = 600


class DigitalOceanDeploymentValidator:
    """Comprehensive deployment validation for DigitalOcean App Platform."""
    
    def __init__(self, environment: CloudEnvironment):
        self.environment = environment
        self.deployment_logs: List[Dict[str, Any]] = []
    
    async def validate_deployment_health(self, timeout: int = 120) -> Dict[str, Any]:
        """Validate deployment health with comprehensive checks."""
        print(f"🔍 Validating deployment health for {self.environment.name}")
        
        health_result = {
            "deployment_healthy": False,
            "response_time": None,
            "status_code": None,
            "error": None,
            "timestamp": time.time(),
            "environment": self.environment.name,
            "attempts": 0
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for attempt in range(timeout // 5):
                    health_result["attempts"] = attempt + 1
                    
                    try:
                        health_url = f"{self.environment.base_url}{self.environment.health_check_endpoint}"
                        response = await client.get(health_url)
                        
                        health_result["status_code"] = response.status_code
                        health_result["response_time"] = time.time() - start_time
                        
                        if response.status_code == 200:
                            health_result["deployment_healthy"] = True
                            print(f"✅ Deployment healthy in {health_result['response_time']:.1f}s (attempt {attempt + 1})")
                            break
                        else:
                            print(f"⏳ Deployment not ready (attempt {attempt + 1}): {response.status_code}")
                            
                    except Exception as e:
                        print(f"⏳ Health check failed (attempt {attempt + 1}): {str(e)}")
                        if attempt == 0:
                            health_result["error"] = str(e)
                        
                    await asyncio.sleep(5)
                
                if not health_result["deployment_healthy"]:
                    if not health_result["error"]:
                        health_result["error"] = f"Deployment failed to become healthy within {timeout}s timeout"
                    
        except Exception as e:
            health_result["error"] = str(e)
            print(f"❌ Deployment validation failed: {e}")
        
        self.deployment_logs.append(health_result)
        return health_result
    
    async def validate_api_endpoints(self) -> Dict[str, Any]:
        """Validate critical API endpoints accessibility."""
        print(f"🔗 Validating API endpoints for {self.environment.name}")
        
        endpoints = [
            {"path": "/", "method": "GET", "expected_status": 200, "description": "Root endpoint"},
            {"path": "/docs", "method": "GET", "expected_status": 200, "description": "API documentation"},
            {"path": "/openapi.json", "method": "GET", "expected_status": 200, "description": "OpenAPI specification"},
            {"path": "/health", "method": "GET", "expected_status": 200, "description": "Health check"},
            {"path": "/api/memory/graph", "method": "GET", "expected_status": 200, "description": "Memory graph endpoint"},
            {"path": "/api/analytics/dashboard", "method": "GET", "expected_status": 200, "description": "Analytics dashboard"}
        ]
        
        results = {
            "total_endpoints": len(endpoints),
            "successful_endpoints": 0,
            "failed_endpoints": [],
            "endpoint_results": [],
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in endpoints:
                endpoint_result = {
                    "path": endpoint["path"],
                    "method": endpoint["method"],
                    "description": endpoint["description"],
                    "expected_status": endpoint["expected_status"],
                    "actual_status": None,
                    "response_time": None,
                    "success": False,
                    "error": None,
                    "response_size": 0
                }
                
                try:
                    start_time = time.time()
                    url = f"{self.environment.base_url}{endpoint['path']}"
                    
                    if endpoint["method"] == "GET":
                        response = await client.get(url)
                    else:
                        # For future POST/PUT endpoints
                        continue
                    
                    endpoint_result["actual_status"] = response.status_code
                    endpoint_result["response_time"] = time.time() - start_time
                    endpoint_result["response_size"] = len(response.content) if response.content else 0
                    endpoint_result["success"] = response.status_code == endpoint["expected_status"]
                    
                    if endpoint_result["success"]:
                        results["successful_endpoints"] += 1
                        print(f"✅ {endpoint['description']}: {response.status_code} ({endpoint_result['response_time']:.3f}s)")
                    else:
                        results["failed_endpoints"].append({
                            "path": endpoint["path"],
                            "expected": endpoint["expected_status"],
                            "actual": response.status_code
                        })
                        print(f"❌ {endpoint['description']}: expected {endpoint['expected_status']}, got {response.status_code}")
                        
                except Exception as e:
                    endpoint_result["error"] = str(e)
                    results["failed_endpoints"].append({
                        "path": endpoint["path"],
                        "error": str(e)
                    })
                    print(f"❌ {endpoint['description']}: {str(e)}")
                
                results["endpoint_results"].append(endpoint_result)
        
        results["success_rate"] = (results["successful_endpoints"] / results["total_endpoints"]) * 100
        results["end_time"] = datetime.now(timezone.utc).isoformat()
        
        print(f"📊 API Validation: {results['success_rate']:.1f}% success rate ({results['successful_endpoints']}/{results['total_endpoints']})")
        return results
    
    async def validate_database_connectivity(self) -> Dict[str, Any]:
        """Validate database connectivity through API endpoints."""
        print(f"🗄️  Validating database connectivity for {self.environment.name}")
        
        db_result = {
            "database_accessible": False,
            "response_time": None,
            "error": None,
            "test_operations": []
        }
        
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                # Test database connectivity through memory endpoints
                start_time = time.time()
                
                # Try to get memory graph (should work even with empty database)
                response = await client.get(
                    f"{self.environment.base_url}/api/memory/graph",
                    timeout=30.0
                )
                
                db_result["response_time"] = time.time() - start_time
                
                if response.status_code == 200:
                    db_result["database_accessible"] = True
                    db_result["test_operations"].append({
                        "operation": "memory_graph_access",
                        "success": True,
                        "response_time": db_result["response_time"]
                    })
                    print(f"✅ Database accessible via memory graph ({db_result['response_time']:.3f}s)")
                else:
                    db_result["error"] = f"Memory graph endpoint returned {response.status_code}"
                    db_result["test_operations"].append({
                        "operation": "memory_graph_access",
                        "success": False,
                        "error": db_result["error"]
                    })
                    print(f"❌ Database connectivity test failed: {response.status_code}")
                
        except Exception as e:
            db_result["error"] = str(e)
            print(f"❌ Database connectivity validation failed: {e}")
        
        return db_result
    
    async def run_comprehensive_cloud_validation(self) -> Dict[str, Any]:
        """Run complete cloud deployment validation suite."""
        print(f"🚀 Running comprehensive cloud validation for {self.environment.name}")
        
        validation_start = time.time()
        
        # Run all validations
        health_result = await self.validate_deployment_health()
        api_results = await self.validate_api_endpoints()
        db_result = await self.validate_database_connectivity()
        
        # Compile comprehensive results
        comprehensive_result = {
            "environment": self.environment.name,
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_validation_time": time.time() - validation_start,
            "overall_health": {
                "deployment_healthy": health_result["deployment_healthy"],
                "api_success_rate": api_results["success_rate"],
                "database_accessible": db_result["database_accessible"]
            },
            "detailed_results": {
                "health_check": health_result,
                "api_endpoints": api_results,
                "database_connectivity": db_result
            },
            "summary": {
                "total_tests": 3,
                "passed_tests": 0,
                "failed_tests": 0
            }
        }
        
        # Calculate pass/fail summary
        if health_result["deployment_healthy"]:
            comprehensive_result["summary"]["passed_tests"] += 1
        else:
            comprehensive_result["summary"]["failed_tests"] += 1
            
        if api_results["success_rate"] >= 80.0:
            comprehensive_result["summary"]["passed_tests"] += 1
        else:
            comprehensive_result["summary"]["failed_tests"] += 1
            
        if db_result["database_accessible"]:
            comprehensive_result["summary"]["passed_tests"] += 1
        else:
            comprehensive_result["summary"]["failed_tests"] += 1
        
        comprehensive_result["overall_success"] = comprehensive_result["summary"]["failed_tests"] == 0
        
        print(f"📊 Comprehensive validation completed: {comprehensive_result['summary']['passed_tests']}/3 tests passed")
        
        return comprehensive_result


class TestDigitalOceanDeployment:
    """Comprehensive DigitalOcean deployment testing."""
    
    @pytest.mark.asyncio
    async def test_production_deployment_validation(self):
        """Test complete production deployment validation pipeline."""
        # Load environment from env vars
        production_url = os.getenv("DO_PRODUCTION_URL")
        if not production_url:
            pytest.skip("No DigitalOcean production environment configured (DO_PRODUCTION_URL not set)")
        
        environment = CloudEnvironment(
            name="production",
            base_url=production_url,
            app_name="graphmemory-ide",
            region=os.getenv("DO_REGION", "nyc3"),
            environment_type="production"
        )
        
        validator = DigitalOceanDeploymentValidator(environment)
        
        # Run comprehensive validation
        results = await validator.run_comprehensive_cloud_validation()
        
        # Assert production requirements
        assert results["overall_success"], f"Production deployment validation failed: {results['summary']}"
        assert results["overall_health"]["deployment_healthy"], "Production deployment not healthy"
        assert results["overall_health"]["api_success_rate"] >= 95.0, f"Production API success rate too low: {results['overall_health']['api_success_rate']}%"
        assert results["overall_health"]["database_accessible"], "Production database not accessible"
        
        print("✅ Production deployment validation passed")
    
    @pytest.mark.asyncio
    async def test_staging_deployment_validation(self):
        """Test staging deployment validation with relaxed requirements."""
        staging_url = os.getenv("DO_STAGING_URL")
        if not staging_url:
            pytest.skip("No DigitalOcean staging environment configured (DO_STAGING_URL not set)")
        
        environment = CloudEnvironment(
            name="staging",
            base_url=staging_url,
            app_name="graphmemory-ide-staging",
            region=os.getenv("DO_REGION", "nyc3"),
            environment_type="staging"
        )
        
        validator = DigitalOceanDeploymentValidator(environment)
        
        # Run comprehensive validation
        results = await validator.run_comprehensive_cloud_validation()
        
        # Assert staging requirements (more lenient)
        assert results["overall_health"]["deployment_healthy"], "Staging deployment not healthy"
        assert results["overall_health"]["api_success_rate"] >= 80.0, f"Staging API success rate too low: {results['overall_health']['api_success_rate']}%"
        
        print("✅ Staging deployment validation passed")
    
    @pytest.mark.asyncio
    async def test_deployment_performance_benchmarks(self):
        """Test deployment performance meets benchmarks."""
        base_url = os.getenv("DO_PRODUCTION_URL") or os.getenv("DO_STAGING_URL")
        if not base_url:
            pytest.skip("No DigitalOcean environment configured for performance testing")
        
        environment = CloudEnvironment(
            name="performance_test",
            base_url=base_url,
            app_name="graphmemory-ide",
            region=os.getenv("DO_REGION", "nyc3"),
            environment_type="production"
        )
        
        validator = DigitalOceanDeploymentValidator(environment)
        
        # Validate performance benchmarks
        api_results = await validator.validate_api_endpoints()
        
        # Check performance requirements
        avg_response_time = sum(
            r["response_time"] for r in api_results["endpoint_results"] 
            if r["response_time"] is not None
        ) / len([r for r in api_results["endpoint_results"] if r["response_time"] is not None])
        
        max_response_time = max(
            r["response_time"] for r in api_results["endpoint_results"] 
            if r["response_time"] is not None
        )
        
        # Performance assertions
        assert avg_response_time <= 2.0, f"Average response time too high: {avg_response_time:.3f}s"
        assert max_response_time <= 10.0, f"Max response time too high: {max_response_time:.3f}s"
        
        print(f"✅ Performance benchmarks passed: avg={avg_response_time:.3f}s, max={max_response_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_cloud_deployment_recovery(self):
        """Test deployment recovery and error handling."""
        base_url = os.getenv("DO_STAGING_URL", "http://localhost:8000")
        
        environment = CloudEnvironment(
            name="recovery_test",
            base_url=base_url,
            app_name="graphmemory-ide",
            region=os.getenv("DO_REGION", "nyc3"),
            environment_type="staging"
        )
        
        validator = DigitalOceanDeploymentValidator(environment)
        
        # Test invalid endpoint handling
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{base_url}/invalid/endpoint/path")
                
                # Should get proper error response, not crash
                assert response.status_code in [404, 422], f"Unexpected error response: {response.status_code}"
                print(f"✅ Error handling working: {response.status_code} for invalid endpoint")
                
            except Exception as e:
                pytest.fail(f"Application crashed on invalid endpoint: {e}")
        
        print("✅ Cloud deployment recovery test passed")


if __name__ == "__main__":
    # Run cloud tests directly for development
    import asyncio
    
    async def main():
        env_manager = DigitalOceanEnvironmentManager()
        
        if env_manager.environments:
            print("🌐 Running DigitalOcean environment validation...")
            results = await env_manager.validate_all_environments()
            
            print(f"\n📊 Validation Summary:")
            for env, result in results.items():
                status = "✅ HEALTHY" if result["overall_healthy"] else "❌ UNHEALTHY"
                print(f"   {env}: {status}")
        else:
            print("❌ No DigitalOcean environments configured")
            print("Set environment variables: DO_PRODUCTION_URL, DO_STAGING_URL, DO_REVIEW_URL")
    
    asyncio.run(main()) 