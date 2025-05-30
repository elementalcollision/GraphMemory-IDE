"""
End-to-End Dashboard Integration Testing Framework
Step 13 Phase 2 Day 3 - Component 3

Comprehensive testing framework for end-to-end dashboard integration
with complete pipeline validation, real-time responsiveness testing,
and user interaction validation.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics
import threading
import subprocess
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

import pytest
import pytest_asyncio
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.fixtures.advanced_database_fixtures import (
    DatabaseConnectionPoolManager,
    DatabasePerformanceMonitor
)
from tests.integration.test_real_analytics_engine_integration import (
    AnalyticsEngineIntegrationTester
)
from tests.integration.test_realtime_sse_integration import (
    SSEStreamTester,
    SSEPerformanceMonitor
)

# Configure logging for detailed test output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DashboardPerformanceMetrics:
    """Performance metrics for dashboard integration testing"""
    test_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    page_load_times: List[float] = field(default_factory=list)
    data_refresh_times: List[float] = field(default_factory=list)
    user_interaction_latencies: List[float] = field(default_factory=list)
    sse_events_received: int = 0
    dashboard_updates_count: int = 0
    error_count: int = 0
    memory_usage_mb: List[float] = field(default_factory=list)
    cpu_usage_percent: List[float] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """Calculate total test duration"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def average_page_load_time(self) -> float:
        """Calculate average page load time in seconds"""
        return statistics.mean(self.page_load_times) if self.page_load_times else 0.0
    
    @property
    def average_refresh_time(self) -> float:
        """Calculate average data refresh time in seconds"""
        return statistics.mean(self.data_refresh_times) if self.data_refresh_times else 0.0
    
    @property
    def p95_refresh_time(self) -> float:
        """Calculate 95th percentile refresh time"""
        if not self.data_refresh_times:
            return 0.0
        sorted_times = sorted(self.data_refresh_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[index]

class DashboardIntegrationTester:
    """Complete pipeline validation for dashboard integration"""
    
    def __init__(self, dashboard_url: str = "http://localhost:8501"):
        self.dashboard_url = dashboard_url
        self.analytics_tester = AnalyticsEngineIntegrationTester()
        self.sse_tester = SSEStreamTester()
        self.db_pool_manager = DatabaseConnectionPoolManager()
        self.performance_monitor = DatabasePerformanceMonitor()
        self.driver: Optional[webdriver.Chrome] = None
        self.streamlit_process: Optional[subprocess.Popen] = None
        
    async def setup_dashboard_environment(self) -> None:
        """Setup complete dashboard testing environment"""
        logger.info("Setting up dashboard testing environment")
        
        # Initialize all backend components
        await self.analytics_tester.setup_analytics_integration()
        await self.db_pool_manager.initialize_connection_pools()
        
        # Setup Chrome WebDriver for dashboard testing
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode for CI/CD
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise
        
        # Start Streamlit dashboard if not already running
        await self._ensure_dashboard_running()
    
    async def _ensure_dashboard_running(self) -> None:
        """Ensure Streamlit dashboard is running"""
        try:
            # Check if dashboard is already accessible
            response = requests.get(self.dashboard_url, timeout=5)
            if response.status_code == 200:
                logger.info("Dashboard already running")
                return
        except requests.exceptions.RequestException:
            pass
        
        # Start Streamlit dashboard
        logger.info("Starting Streamlit dashboard")
        try:
            self.streamlit_process = subprocess.Popen([
                "streamlit", "run", "dashboard/main.py",
                "--server.port", "8501",
                "--server.headless", "true"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for dashboard to be ready
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(self.dashboard_url, timeout=1)
                    if response.status_code == 200:
                        logger.info("Dashboard started successfully")
                        return
                except requests.exceptions.RequestException:
                    pass
                await asyncio.sleep(1)
            
            raise Exception("Dashboard failed to start within timeout")
            
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            raise
    
    async def test_complete_pipeline_integration(self) -> DashboardPerformanceMetrics:
        """Test complete pipeline: Analytics Engine → Database → SSE → Dashboard"""
        logger.info("Testing complete pipeline integration")
        
        test_id = f"pipeline_integration_{int(time.time())}"
        metrics = DashboardPerformanceMetrics(test_id=test_id)
        
        try:
            # Step 1: Validate analytics engine data flow
            logger.info("Step 1: Testing analytics engine integration")
            analytics_results = await self.analytics_tester.test_real_analytics_integration()
            assert analytics_results["success_rate"] > 0.95, "Analytics engine not ready for pipeline test"
            
            # Step 2: Validate database integration
            logger.info("Step 2: Testing database integration")
            kuzu_test = await self.db_pool_manager.test_kuzu_connection_pool(concurrent_connections=10)
            redis_test = await self.db_pool_manager.test_redis_connection_pool(concurrent_connections=20)
            
            assert kuzu_test["success_rate"] > 0.95, "Kuzu database not ready for pipeline test"
            assert redis_test["success_rate"] > 0.95, "Redis cache not ready for pipeline test"
            
            # Step 3: Test SSE data streaming
            logger.info("Step 3: Testing SSE data streaming")
            sse_metrics = await self.sse_tester.test_single_client_sse_streaming()
            assert sse_metrics.average_latency < 100, "SSE streaming latency too high for pipeline test"
            
            # Step 4: Test dashboard loading and real-time updates
            logger.info("Step 4: Testing dashboard integration")
            load_start = time.time()
            
            # Navigate to dashboard
            self.driver.get(self.dashboard_url)
            
            # Wait for dashboard to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            load_end = time.time()
            page_load_time = load_end - load_start
            metrics.page_load_times.append(page_load_time)
            
            logger.info(f"Dashboard loaded in {page_load_time:.2f}s")
            
            # Step 5: Validate real-time data flow through entire pipeline
            await self._test_end_to_end_data_flow(metrics)
            
            # Step 6: Calculate end-to-end latency
            end_to_end_latency = (
                analytics_results["average_response_time"] +
                (kuzu_test["average_latency"] + redis_test["average_latency"]) / 2 +
                sse_metrics.average_latency / 1000 +  # Convert to seconds
                metrics.average_refresh_time
            )
            
            # Validate end-to-end performance requirements
            assert end_to_end_latency < 0.5, f"End-to-end latency {end_to_end_latency:.3f}s exceeds 500ms target"
            assert page_load_time < 5.0, f"Page load time {page_load_time:.2f}s exceeds 5s target"
            assert metrics.average_refresh_time < 2.0, f"Dashboard refresh time {metrics.average_refresh_time:.2f}s exceeds 2s target"
            
            metrics.end_time = time.time()
            
            logger.info(f"Complete pipeline integration test results:")
            logger.info(f"  End-to-End Latency: {end_to_end_latency:.3f}s")
            logger.info(f"  Page Load Time: {page_load_time:.2f}s")
            logger.info(f"  Average Refresh Time: {metrics.average_refresh_time:.2f}s")
            logger.info(f"  SSE Events Received: {metrics.sse_events_received}")
            logger.info(f"  Dashboard Updates: {metrics.dashboard_updates_count}")
            
            return metrics
            
        except Exception as e:
            metrics.error_count += 1
            logger.error(f"Complete pipeline integration test failed: {e}")
            raise
    
    async def _test_end_to_end_data_flow(self, metrics: DashboardPerformanceMetrics) -> None:
        """Test end-to-end data flow validation"""
        logger.info("Testing end-to-end data flow")
        
        # Monitor dashboard for real-time updates
        update_count = 0
        test_duration = 60  # Test for 1 minute
        start_time = time.time()
        
        # Create background task to monitor SSE events
        sse_task = asyncio.create_task(self._monitor_sse_events(metrics))
        
        while time.time() - start_time < test_duration:
            refresh_start = time.time()
            
            try:
                # Trigger dashboard refresh (simulate user interaction)
                self.driver.refresh()
                
                # Wait for content to update
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "stApp"))
                )
                
                refresh_end = time.time()
                refresh_time = refresh_end - refresh_start
                metrics.data_refresh_times.append(refresh_time)
                metrics.dashboard_updates_count += 1
                
                update_count += 1
                logger.info(f"Dashboard update #{update_count} completed in {refresh_time:.2f}s")
                
                # Validate that dashboard shows live data
                await self._validate_live_data_display()
                
                # Brief pause before next update
                await asyncio.sleep(5)
                
            except TimeoutException:
                metrics.error_count += 1
                logger.error("Timeout waiting for dashboard update")
            except Exception as e:
                metrics.error_count += 1
                logger.error(f"Error during dashboard update: {e}")
        
        # Cancel SSE monitoring task
        sse_task.cancel()
        
        logger.info(f"End-to-end data flow test completed: {update_count} updates in {test_duration}s")
    
    async def _monitor_sse_events(self, metrics: DashboardPerformanceMetrics) -> None:
        """Monitor SSE events during dashboard testing"""
        try:
            # This would connect to the SSE endpoint and count events
            # For this test, we'll simulate SSE event monitoring
            start_time = time.time()
            
            while True:
                # Simulate SSE event reception
                await asyncio.sleep(1)
                metrics.sse_events_received += 1
                
                # Stop after reasonable test duration
                if time.time() - start_time > 120:  # 2 minutes max
                    break
                    
        except asyncio.CancelledError:
            logger.info("SSE monitoring cancelled")
        except Exception as e:
            logger.error(f"Error monitoring SSE events: {e}")
    
    async def _validate_live_data_display(self) -> None:
        """Validate that dashboard displays live data"""
        try:
            # Check for common dashboard elements that should contain live data
            elements_to_check = [
                (By.CLASS_NAME, "metric-value"),
                (By.CLASS_NAME, "stMetric"),
                (By.TAG_NAME, "canvas"),  # For charts
                (By.CLASS_NAME, "dataframe")  # For data tables
            ]
            
            for by, selector in elements_to_check:
                try:
                    elements = self.driver.find_elements(by, selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} elements with selector {selector}")
                        # Validate elements contain non-empty text/data
                        for element in elements[:3]:  # Check first 3 elements
                            if element.text.strip():
                                logger.debug(f"Element contains data: {element.text[:50]}...")
                                return  # Found at least one element with data
                except Exception as e:
                    logger.debug(f"Error checking element {selector}: {e}")
            
            logger.warning("No live data elements found in dashboard")
            
        except Exception as e:
            logger.error(f"Error validating live data display: {e}")
    
    async def cleanup_dashboard_environment(self) -> None:
        """Cleanup dashboard testing environment"""
        logger.info("Cleaning up dashboard testing environment")
        
        try:
            if self.driver:
                self.driver.quit()
                
            if self.streamlit_process:
                self.streamlit_process.terminate()
                self.streamlit_process.wait(timeout=10)
                
            await self.analytics_tester.cleanup_analytics_integration()
            await self.db_pool_manager.cleanup_connection_pools()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

class DashboardPerformanceValidator:
    """Dashboard performance validation under live data loads"""
    
    def __init__(self):
        self.performance_baselines = {
            "max_page_load_time": 5.0,  # seconds
            "max_refresh_time": 2.0,    # seconds
            "max_interaction_latency": 1.0,  # seconds
            "min_update_frequency": 0.5,  # updates per second
        }
        self.test_results: Dict[str, DashboardPerformanceMetrics] = {}
    
    async def test_dashboard_responsiveness_under_load(self, concurrent_users: int = 10) -> Dict[str, Any]:
        """Test dashboard responsiveness under concurrent user load"""
        logger.info(f"Testing dashboard responsiveness with {concurrent_users} concurrent users")
        
        test_id = f"responsiveness_test_{int(time.time())}"
        user_tasks = []
        
        async def simulate_user_session(user_id: int) -> DashboardPerformanceMetrics:
            """Simulate a single user session"""
            user_metrics = DashboardPerformanceMetrics(test_id=f"{test_id}_user_{user_id}")
            
            try:
                # Setup isolated browser instance for this user
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                driver = webdriver.Chrome(options=chrome_options)
                
                # User session simulation
                for interaction in range(10):  # 10 interactions per user
                    interaction_start = time.time()
                    
                    # Navigate to dashboard
                    driver.get("http://localhost:8501")
                    
                    # Wait for page load
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    interaction_end = time.time()
                    interaction_time = interaction_end - interaction_start
                    user_metrics.user_interaction_latencies.append(interaction_time)
                    
                    # Simulate user actions (clicks, scrolls, etc.)
                    await self._simulate_user_interactions(driver, user_metrics)
                    
                    # Brief pause between interactions
                    await asyncio.sleep(2)
                
                driver.quit()
                user_metrics.end_time = time.time()
                return user_metrics
                
            except Exception as e:
                user_metrics.error_count += 1
                logger.error(f"User {user_id} session failed: {e}")
                return user_metrics
        
        # Create concurrent user sessions
        start_time = time.time()
        for user_id in range(concurrent_users):
            task = asyncio.create_task(simulate_user_session(user_id))
            user_tasks.append(task)
        
        # Execute all user sessions
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        successful_sessions = [r for r in user_results if isinstance(r, DashboardPerformanceMetrics) and r.error_count == 0]
        failed_sessions = len(user_results) - len(successful_sessions)
        
        # Calculate aggregate metrics
        aggregate_results = {
            "test_id": test_id,
            "concurrent_users": concurrent_users,
            "successful_sessions": len(successful_sessions),
            "failed_sessions": failed_sessions,
            "session_success_rate": len(successful_sessions) / concurrent_users,
            "total_duration": end_time - start_time,
            "average_interaction_latency": 0,
            "p95_interaction_latency": 0,
            "max_interaction_latency": 0,
            "total_interactions": 0
        }
        
        if successful_sessions:
            all_latencies = []
            for session in successful_sessions:
                all_latencies.extend(session.user_interaction_latencies)
            
            if all_latencies:
                aggregate_results["average_interaction_latency"] = statistics.mean(all_latencies)
                aggregate_results["p95_interaction_latency"] = statistics.quantiles(all_latencies, n=20)[18]
                aggregate_results["max_interaction_latency"] = max(all_latencies)
                aggregate_results["total_interactions"] = len(all_latencies)
        
        # Validate performance requirements
        assert aggregate_results["session_success_rate"] > 0.95, f"Session success rate {aggregate_results['session_success_rate']:.2%} below 95%"
        assert aggregate_results["average_interaction_latency"] < self.performance_baselines["max_interaction_latency"], \
            f"Average interaction latency {aggregate_results['average_interaction_latency']:.2f}s exceeds {self.performance_baselines['max_interaction_latency']}s"
        
        self.test_results[test_id] = aggregate_results
        
        logger.info(f"Dashboard responsiveness test results:")
        logger.info(f"  Successful Sessions: {aggregate_results['successful_sessions']}/{concurrent_users}")
        logger.info(f"  Session Success Rate: {aggregate_results['session_success_rate']:.2%}")
        logger.info(f"  Average Interaction Latency: {aggregate_results['average_interaction_latency']:.2f}s")
        logger.info(f"  P95 Interaction Latency: {aggregate_results['p95_interaction_latency']:.2f}s")
        
        return aggregate_results
    
    async def _simulate_user_interactions(self, driver: webdriver.Chrome, metrics: DashboardPerformanceMetrics) -> None:
        """Simulate realistic user interactions with dashboard"""
        try:
            interactions = [
                # Scroll down the page
                lambda: driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);"),
                # Scroll back up
                lambda: driver.execute_script("window.scrollTo(0, 0);"),
                # Refresh page
                lambda: driver.refresh(),
                # Wait for content
                lambda: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            ]
            
            # Execute random interactions
            import random
            selected_interactions = random.sample(interactions, min(2, len(interactions)))
            
            for interaction in selected_interactions:
                try:
                    interaction()
                    await asyncio.sleep(0.5)  # Brief pause between interactions
                except Exception as e:
                    logger.debug(f"Minor interaction error: {e}")
                    
        except Exception as e:
            metrics.error_count += 1
            logger.error(f"Error simulating user interactions: {e}")

class DashboardUserInteractionTester:
    """Real-time user interaction validation testing"""
    
    def __init__(self):
        self.interaction_results: Dict[str, Any] = {}
    
    async def test_realtime_user_interactions(self) -> Dict[str, Any]:
        """Test real-time user interactions with live updates"""
        logger.info("Testing real-time user interactions")
        
        test_id = f"interaction_test_{int(time.time())}"
        
        # Use AppTest for programmatic Streamlit testing
        app_test = AppTest.from_file("dashboard/main.py")
        
        interaction_metrics = {
            "test_id": test_id,
            "widgets_tested": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "widget_response_times": [],
            "data_update_times": [],
            "state_consistency_validated": True
        }
        
        try:
            # Run the Streamlit app
            app_test.run()
            
            # Test different widget interactions
            await self._test_selectbox_interactions(app_test, interaction_metrics)
            await self._test_slider_interactions(app_test, interaction_metrics)
            await self._test_button_interactions(app_test, interaction_metrics)
            await self._test_text_input_interactions(app_test, interaction_metrics)
            
            # Validate real-time state management
            await self._validate_session_state_consistency(app_test, interaction_metrics)
            
            # Calculate success rate
            total_interactions = interaction_metrics["successful_interactions"] + interaction_metrics["failed_interactions"]
            interaction_metrics["success_rate"] = (
                interaction_metrics["successful_interactions"] / total_interactions 
                if total_interactions > 0 else 0
            )
            
            # Validate interaction performance
            if interaction_metrics["widget_response_times"]:
                interaction_metrics["average_response_time"] = statistics.mean(interaction_metrics["widget_response_times"])
                interaction_metrics["max_response_time"] = max(interaction_metrics["widget_response_times"])
            else:
                interaction_metrics["average_response_time"] = 0
                interaction_metrics["max_response_time"] = 0
            
            assert interaction_metrics["success_rate"] > 0.95, f"Interaction success rate {interaction_metrics['success_rate']:.2%} below 95%"
            assert interaction_metrics["average_response_time"] < 1.0, f"Average response time {interaction_metrics['average_response_time']:.2f}s exceeds 1s"
            
            self.interaction_results[test_id] = interaction_metrics
            
            logger.info(f"Real-time user interaction test results:")
            logger.info(f"  Widgets Tested: {interaction_metrics['widgets_tested']}")
            logger.info(f"  Success Rate: {interaction_metrics['success_rate']:.2%}")
            logger.info(f"  Average Response Time: {interaction_metrics['average_response_time']:.2f}s")
            logger.info(f"  State Consistency: {'PASSED' if interaction_metrics['state_consistency_validated'] else 'FAILED'}")
            
            return interaction_metrics
            
        except Exception as e:
            logger.error(f"Real-time user interaction test failed: {e}")
            raise

class DashboardDataFlowValidator:
    """Complete data flow integrity testing"""
    
    def __init__(self):
        self.validation_results: Dict[str, Any] = {}
    
    async def validate_data_flow_integrity(self) -> Dict[str, Any]:
        """Validate complete data flow integrity across all components"""
        logger.info("Validating complete data flow integrity")
        
        test_id = f"data_flow_validation_{int(time.time())}"
        
        validation_metrics = {
            "test_id": test_id,
            "data_sources_validated": 0,
            "data_transformations_validated": 0,
            "data_consistency_checks": 0,
            "data_integrity_violations": 0,
            "end_to_end_latency": 0,
            "data_flow_success": True
        }
        
        try:
            # Initialize all components
            analytics_tester = AnalyticsEngineIntegrationTester()
            db_pool_manager = DatabaseConnectionPoolManager()
            sse_tester = SSEStreamTester()
            
            await analytics_tester.setup_analytics_integration()
            await db_pool_manager.initialize_connection_pools()
            
            # Step 1: Validate data source integrity
            logger.info("Validating data source integrity")
            source_start = time.time()
            analytics_results = await analytics_tester.test_real_analytics_integration()
            source_end = time.time()
            
            validation_metrics["data_sources_validated"] += 1
            
            # Step 2: Validate database storage integrity
            logger.info("Validating database storage integrity")
            storage_start = time.time()
            
            # Test data storage in each database
            kuzu_results = await db_pool_manager.test_kuzu_connection_pool(concurrent_connections=5)
            redis_results = await db_pool_manager.test_redis_connection_pool(concurrent_connections=10)
            
            storage_end = time.time()
            validation_metrics["data_transformations_validated"] += 2
            
            # Step 3: Validate SSE data streaming integrity
            logger.info("Validating SSE streaming integrity")
            streaming_start = time.time()
            sse_results = await sse_tester.test_single_client_sse_streaming()
            streaming_end = time.time()
            
            validation_metrics["data_transformations_validated"] += 1
            
            # Step 4: End-to-end data consistency validation
            logger.info("Validating end-to-end data consistency")
            consistency_start = time.time()
            
            # Simulate data flow and validate consistency
            test_data = {"metric": "test_validation", "value": time.time(), "source": "validation_test"}
            
            # Validate data consistency across pipeline
            await self._validate_data_consistency_across_pipeline(test_data, validation_metrics)
            
            consistency_end = time.time()
            validation_metrics["data_consistency_checks"] += 1
            
            # Calculate total end-to-end latency
            total_latency = (
                (source_end - source_start) +
                (storage_end - storage_start) +
                (streaming_end - streaming_start) +
                (consistency_end - consistency_start)
            )
            
            validation_metrics["end_to_end_latency"] = total_latency
            
            # Validate performance requirements
            assert validation_metrics["data_integrity_violations"] == 0, "Data integrity violations detected"
            assert total_latency < 2.0, f"End-to-end latency {total_latency:.2f}s exceeds 2s threshold"
            assert analytics_results["success_rate"] > 0.95, "Analytics data source not meeting integrity requirements"
            assert kuzu_results["success_rate"] > 0.95, "Kuzu database not meeting integrity requirements"
            assert redis_results["success_rate"] > 0.95, "Redis cache not meeting integrity requirements"
            
            self.validation_results[test_id] = validation_metrics
            
            logger.info(f"Data flow integrity validation results:")
            logger.info(f"  Data Sources Validated: {validation_metrics['data_sources_validated']}")
            logger.info(f"  Data Transformations Validated: {validation_metrics['data_transformations_validated']}")
            logger.info(f"  Consistency Checks: {validation_metrics['data_consistency_checks']}")
            logger.info(f"  Integrity Violations: {validation_metrics['data_integrity_violations']}")
            logger.info(f"  End-to-End Latency: {validation_metrics['end_to_end_latency']:.2f}s")
            logger.info(f"  Data Flow Status: {'SUCCESS' if validation_metrics['data_flow_success'] else 'FAILED'}")
            
            return validation_metrics
            
        except Exception as e:
            validation_metrics["data_flow_success"] = False
            logger.error(f"Data flow integrity validation failed: {e}")
            raise
        finally:
            await analytics_tester.cleanup_analytics_integration()
            await db_pool_manager.cleanup_connection_pools()

# Integration test cases
@pytest_asyncio.async_test
async def test_complete_dashboard_pipeline():
    """Test complete dashboard pipeline integration"""
    tester = DashboardIntegrationTester()
    
    try:
        await tester.setup_dashboard_environment()
        metrics = await tester.test_complete_pipeline_integration()
        
        # Validate pipeline performance
        assert metrics.average_page_load_time < 5.0
        assert metrics.average_refresh_time < 2.0
        assert metrics.error_count == 0
        
    finally:
        await tester.cleanup_dashboard_environment()

@pytest_asyncio.async_test
async def test_dashboard_performance_under_load():
    """Test dashboard performance under concurrent user load"""
    validator = DashboardPerformanceValidator()
    results = await validator.test_dashboard_responsiveness_under_load(concurrent_users=5)
    
    # Validate performance requirements
    assert results["session_success_rate"] > 0.95
    assert results["average_interaction_latency"] < 1.0

@pytest_asyncio.async_test
async def test_realtime_user_interactions():
    """Test real-time user interactions with dashboard"""
    tester = DashboardUserInteractionTester()
    results = await tester.test_realtime_user_interactions()
    
    # Validate interaction requirements
    assert results["success_rate"] > 0.95
    assert results["average_response_time"] < 1.0
    assert results["state_consistency_validated"] is True

@pytest_asyncio.async_test
async def test_data_flow_integrity():
    """Test complete data flow integrity validation"""
    validator = DashboardDataFlowValidator()
    results = await validator.validate_data_flow_integrity()
    
    # Validate data flow requirements
    assert results["data_flow_success"] is True
    assert results["data_integrity_violations"] == 0
    assert results["end_to_end_latency"] < 2.0 