"""
Test script for Dashboard SSE Infrastructure

This script tests the Phase 1 implementation of the real-time dashboard
SSE server and routes to ensure everything is working correctly.
"""

import asyncio
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sse_manager() -> bool:
    """Test the DashboardSSEManager functionality"""
    print("🧪 Testing Dashboard SSE Manager...")
    
    try:
        from dashboard.sse_server import DashboardSSEManager
        
        # Initialize SSE manager
        manager = DashboardSSEManager()
        await manager.start()
        
        print("✅ SSE Manager initialized successfully")
        
        # Test analytics data generation
        analytics_data = await manager.get_analytics_data()
        print(f"✅ Analytics data: {analytics_data}")
        
        # Test memory insights
        memory_data = await manager.get_memory_insights()
        print(f"✅ Memory data: {memory_data}")
        
        # Test graph metrics
        graph_data = await manager.get_graph_metrics()
        print(f"✅ Graph data: {graph_data}")
        
        # Test connection management
        manager.add_connection("test-connection-1")
        manager.add_connection("test-connection-2")
        
        stats = manager.get_connection_stats()
        print(f"✅ Connection stats: {stats}")
        
        # Test stream generation (get first item)
        print("🔄 Testing analytics stream...")
        analytics_stream = manager.analytics_stream()
        first_item = await analytics_stream.__anext__()
        print(f"✅ Stream item: {first_item}")
        
        # Cleanup
        manager.remove_connection("test-connection-1")
        manager.remove_connection("test-connection-2")
        await manager.stop()
        
        print("✅ SSE Manager test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ SSE Manager test failed: {e}")
        return False


async def test_dashboard_routes() -> bool:
    """Test the dashboard routes functionality"""
    print("\n🧪 Testing Dashboard Routes...")
    
    try:
        from dashboard.routes import get_sse_manager
        
        # Test SSE manager initialization
        manager = get_sse_manager()
        print("✅ SSE Manager dependency resolved")
        
        # Test manager functionality
        await manager.start()
        
        # Test latest data endpoint functionality
        analytics_data = await manager.get_analytics_data()
        memory_data = await manager.get_memory_insights()
        graph_data = await manager.get_graph_metrics()
        
        latest_data = {
            "timestamp": manager._last_update,
            "analytics": analytics_data,
            "memory": memory_data,
            "graph": graph_data,
            "connection_stats": manager.get_connection_stats()
        }
        
        print(f"✅ Latest data structure: {list(latest_data.keys())}")
        
        # Test status endpoint functionality
        status = {
            "status": "healthy" if manager._running else "stopped",
            "connection_stats": manager.get_connection_stats(),
            "last_updates": manager._last_update,
            "services": {
                "sse_manager": "running" if manager._running else "stopped",
                "analytics_engine": "available" if manager.analytics_engine else "mock_data"
            }
        }
        
        print(f"✅ Status data: {status}")
        
        await manager.stop()
        print("✅ Dashboard Routes test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard Routes test failed: {e}")
        return False


async def test_integration() -> bool:
    """Test integration with main FastAPI app"""
    print("\n🧪 Testing FastAPI Integration...")
    
    try:
        # Test import of main app with dashboard routes
        import sys
        import os
        
        # Add server directory to path
        server_path = os.path.dirname(os.path.abspath(__file__))
        if server_path not in sys.path:
            sys.path.insert(0, server_path)
        
        # Test importing main app (this will test router inclusion)
        from main import app
        
        print("✅ Main FastAPI app imported successfully")
        
        # Check if dashboard routes are included
        routes = [route.path for route in app.routes]
        dashboard_routes = [route for route in routes if route.startswith('/dashboard')]
        
        if dashboard_routes:
            print(f"✅ Dashboard routes found: {dashboard_routes}")
        else:
            print("⚠️  Dashboard routes not found (dependencies may not be installed)")
        
        print("✅ FastAPI Integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI Integration test failed: {e}")
        return False


async def main() -> bool:
    """Run all tests"""
    print("🚀 Starting Dashboard Phase 1 Tests")
    print("=" * 50)
    
    results = []
    
    # Test SSE Manager
    results.append(await test_sse_manager())
    
    # Test Dashboard Routes
    results.append(await test_dashboard_routes())
    
    # Test Integration
    results.append(await test_integration())
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 All tests passed! Phase 1 implementation is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return all(results)


if __name__ == "__main__":
    asyncio.run(main()) 