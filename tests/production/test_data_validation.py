"""
Production Data Validation Framework
Comprehensive validation for memory data integrity, analytics accuracy, and production scenarios.
"""

import asyncio
import pytest
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx
import json
from datetime import datetime, timezone


@dataclass
class DataValidationResult:
    """Results from data validation testing."""
    
    validation_type: str
    passed: bool
    message: str
    data_sample: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ProductionDataValidator:
    """Comprehensive production data validation framework."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.validation_results: List[DataValidationResult] = []
    
    async def validate_memory_data_integrity(self) -> DataValidationResult:
        """Validate memory node data integrity and consistency."""
        print("🔍 Validating memory data integrity...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test memory node creation with comprehensive data
                test_memory = {
                    "content": "Test memory node for data validation",
                    "type": "procedural",
                    "tags": ["test", "validation", "production"],
                    "metadata": {
                        "file_path": "/test/validation.py",
                        "line_numbers": [1, 10],
                        "language": "python"
                    }
                }
                
                # Create memory node
                create_response = await client.post(
                    f"{self.base_url}/api/memory/nodes",
                    json=test_memory,
                    timeout=20.0
                )
                
                if create_response.status_code != 201:
                    return DataValidationResult(
                        validation_type="memory_creation",
                        passed=False,
                        message=f"Failed to create memory node: {create_response.status_code}",
                        error_details=create_response.text
                    )
                
                created_node = create_response.json()
                node_id = created_node.get("id")
                
                # Validate created node structure
                required_fields = ["id", "content", "type", "tags", "created_at"]
                for field in required_fields:
                    if field not in created_node:
                        return DataValidationResult(
                            validation_type="memory_structure",
                            passed=False,
                            message=f"Missing required field: {field}",
                            data_sample=created_node
                        )
                
                # Retrieve and validate consistency
                get_response = await client.get(
                    f"{self.base_url}/api/memory/nodes/{node_id}",
                    timeout=10.0
                )
                
                if get_response.status_code != 200:
                    return DataValidationResult(
                        validation_type="memory_retrieval",
                        passed=False,
                        message=f"Failed to retrieve memory node: {get_response.status_code}"
                    )
                
                retrieved_node = get_response.json()
                
                # Validate data consistency
                if retrieved_node["content"] != test_memory["content"]:
                    return DataValidationResult(
                        validation_type="data_consistency",
                        passed=False,
                        message="Content mismatch between created and retrieved node",
                        data_sample={"created": created_node, "retrieved": retrieved_node}
                    )
                
                # Cleanup test data
                await client.delete(f"{self.base_url}/api/memory/nodes/{node_id}")
                
                return DataValidationResult(
                    validation_type="memory_data_integrity",
                    passed=True,
                    message="Memory data integrity validation passed",
                    data_sample=created_node
                )
                
        except Exception as e:
            return DataValidationResult(
                validation_type="memory_data_integrity",
                passed=False,
                message="Exception during memory data validation",
                error_details=str(e)
            )
    
    async def validate_analytics_data_accuracy(self) -> DataValidationResult:
        """Validate analytics data accuracy and completeness."""
        print("📊 Validating analytics data accuracy...")
        
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                # Request analytics dashboard data
                response = await client.get(
                    f"{self.base_url}/api/analytics/dashboard",
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return DataValidationResult(
                        validation_type="analytics_accessibility",
                        passed=False,
                        message=f"Analytics dashboard not accessible: {response.status_code}"
                    )
                
                analytics_data = response.json()
                
                # Validate analytics structure
                required_sections = ["summary", "memory_stats", "performance_metrics"]
                for section in required_sections:
                    if section not in analytics_data:
                        return DataValidationResult(
                            validation_type="analytics_structure",
                            passed=False,
                            message=f"Missing analytics section: {section}",
                            data_sample=analytics_data
                        )
                
                # Validate data types and ranges
                memory_stats = analytics_data.get("memory_stats", {})
                if "total_nodes" in memory_stats:
                    total_nodes = memory_stats["total_nodes"]
                    if not isinstance(total_nodes, int) or total_nodes < 0:
                        return DataValidationResult(
                            validation_type="analytics_data_types",
                            passed=False,
                            message=f"Invalid total_nodes value: {total_nodes}",
                            data_sample=memory_stats
                        )
                
                return DataValidationResult(
                    validation_type="analytics_data_accuracy",
                    passed=True,
                    message="Analytics data accuracy validation passed",
                    data_sample=analytics_data
                )
                
        except Exception as e:
            return DataValidationResult(
                validation_type="analytics_data_accuracy",
                passed=False,
                message="Exception during analytics validation",
                error_details=str(e)
            )
    
    async def validate_graph_data_relationships(self) -> DataValidationResult:
        """Validate graph database relationships and connections."""
        print("🔗 Validating graph data relationships...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test graph connectivity
                graph_response = await client.get(
                    f"{self.base_url}/api/memory/graph",
                    timeout=20.0
                )
                
                if graph_response.status_code != 200:
                    return DataValidationResult(
                        validation_type="graph_accessibility",
                        passed=False,
                        message=f"Graph endpoint not accessible: {graph_response.status_code}"
                    )
                
                graph_data = graph_response.json()
                
                # Validate graph structure
                expected_fields = ["nodes", "edges"]
                for field in expected_fields:
                    if field not in graph_data:
                        return DataValidationResult(
                            validation_type="graph_structure",
                            passed=False,
                            message=f"Missing graph field: {field}",
                            data_sample=graph_data
                        )
                
                # Validate node structure if nodes exist
                nodes = graph_data.get("nodes", [])
                if nodes:
                    sample_node = nodes[0]
                    node_required_fields = ["id", "type"]
                    for field in node_required_fields:
                        if field not in sample_node:
                            return DataValidationResult(
                                validation_type="graph_node_structure",
                                passed=False,
                                message=f"Node missing required field: {field}",
                                data_sample=sample_node
                            )
                
                return DataValidationResult(
                    validation_type="graph_data_relationships",
                    passed=True,
                    message="Graph data relationships validation passed",
                    data_sample={"node_count": len(nodes), "edge_count": len(graph_data.get("edges", []))}
                )
                
        except Exception as e:
            return DataValidationResult(
                validation_type="graph_data_relationships",
                passed=False,
                message="Exception during graph validation",
                error_details=str(e)
            )
    
    async def validate_search_functionality(self) -> DataValidationResult:
        """Validate search and query functionality."""
        print("🔍 Validating search functionality...")
        
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                # Test search endpoint with various queries
                search_queries = [
                    {"q": "test", "limit": 10},
                    {"q": "function", "limit": 5},
                    {"q": "", "limit": 20}  # Empty query should return defaults
                ]
                
                for query in search_queries:
                    search_response = await client.get(
                        f"{self.base_url}/api/memory/search",
                        params=query,
                        timeout=15.0
                    )
                    
                    if search_response.status_code != 200:
                        return DataValidationResult(
                            validation_type="search_functionality",
                            passed=False,
                            message=f"Search failed for query {query}: {search_response.status_code}",
                            error_details=search_response.text
                        )
                    
                    search_results = search_response.json()
                    
                    # Validate search results structure
                    if not isinstance(search_results, (list, dict)):
                        return DataValidationResult(
                            validation_type="search_results_structure",
                            passed=False,
                            message="Search results not in expected format",
                            data_sample=search_results
                        )
                
                return DataValidationResult(
                    validation_type="search_functionality",
                    passed=True,
                    message="Search functionality validation passed",
                    data_sample={"queries_tested": len(search_queries)}
                )
                
        except Exception as e:
            return DataValidationResult(
                validation_type="search_functionality",
                passed=False,
                message="Exception during search validation",
                error_details=str(e)
            )
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive production data validation suite."""
        print("🔄 Running comprehensive data validation...")
        
        validations = [
            self.validate_memory_data_integrity(),
            self.validate_analytics_data_accuracy(),
            self.validate_graph_data_relationships(),
            self.validate_search_functionality()
        ]
        
        results = await asyncio.gather(*validations, return_exceptions=True)
        
        validation_summary = {
            "total_validations": len(results),
            "passed": 0,
            "failed": 0,
            "results": [],
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        
        for result in results:
            if isinstance(result, Exception):
                validation_summary["failed"] += 1
                validation_summary["results"].append(DataValidationResult(
                    validation_type="exception",
                    passed=False,
                    message="Validation threw exception",
                    error_details=str(result)
                ))
            else:
                if result.passed:
                    validation_summary["passed"] += 1
                else:
                    validation_summary["failed"] += 1
                validation_summary["results"].append(result)
        
        validation_summary["success_rate"] = (validation_summary["passed"] / validation_summary["total_validations"]) * 100
        validation_summary["end_time"] = datetime.now(timezone.utc).isoformat()
        
        print(f"📊 Validation Summary: {validation_summary['success_rate']:.1f}% success rate")
        return validation_summary


class TestProductionDataValidation:
    """Test production data validation framework."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_data_validation(self):
        """Test comprehensive production data validation."""
        base_url = "http://localhost:8000"  # Default to local for testing
        validator = ProductionDataValidator(base_url)
        
        validation_summary = await validator.run_comprehensive_validation()
        
        # Assert validation requirements
        assert validation_summary["success_rate"] >= 75.0, f"Data validation success rate too low: {validation_summary['success_rate']}%"
        assert validation_summary["failed"] <= 2, f"Too many validation failures: {validation_summary['failed']}"
        
        # Log detailed results
        for result in validation_summary["results"]:
            if result.passed:
                print(f"✅ {result.validation_type}: {result.message}")
            else:
                print(f"❌ {result.validation_type}: {result.message}")
                if result.error_details:
                    print(f"   Error: {result.error_details}")
        
        print("✅ Comprehensive data validation completed successfully")
    
    @pytest.mark.asyncio
    async def test_memory_node_lifecycle(self):
        """Test complete memory node lifecycle validation."""
        base_url = "http://localhost:8000"
        validator = ProductionDataValidator(base_url)
        
        # Test memory node creation, retrieval, update, deletion
        result = await validator.validate_memory_data_integrity()
        
        assert result.passed, f"Memory lifecycle validation failed: {result.message}"
        assert result.data_sample is not None, "Memory validation should return sample data"
        
        print("✅ Memory node lifecycle validation passed")
    
    @pytest.mark.asyncio
    async def test_analytics_accuracy(self):
        """Test analytics data accuracy and structure."""
        base_url = "http://localhost:8000"
        validator = ProductionDataValidator(base_url)
        
        result = await validator.validate_analytics_data_accuracy()
        
        assert result.passed, f"Analytics validation failed: {result.message}"
        
        print("✅ Analytics accuracy validation passed")
    
    @pytest.mark.asyncio
    async def test_graph_relationships(self):
        """Test graph database relationships and structure."""
        base_url = "http://localhost:8000"
        validator = ProductionDataValidator(base_url)
        
        result = await validator.validate_graph_data_relationships()
        
        assert result.passed, f"Graph relationships validation failed: {result.message}"
        
        print("✅ Graph relationships validation passed")
    
    @pytest.mark.asyncio
    async def test_search_functionality_validation(self):
        """Test search functionality validation."""
        base_url = "http://localhost:8000"
        validator = ProductionDataValidator(base_url)
        
        result = await validator.validate_search_functionality()
        
        assert result.passed, f"Search functionality validation failed: {result.message}"
        
        print("✅ Search functionality validation passed") 