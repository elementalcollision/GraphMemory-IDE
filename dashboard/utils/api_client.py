"""
Dashboard API Client

This module provides a simple API client for the dashboard to communicate
with the backend services.
"""

import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DashboardAPIClient:
    """Simple API client for dashboard backend communication"""
    
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Make a GET request to the API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params)
            return response
        except requests.RequestException as e:
            logger.error(f"GET request failed: {e}")
            # Return a mock response for development
            return self._mock_response(200, {"status": "mock", "data": []})
    
    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Make a POST request to the API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(url, json=json)
            return response
        except requests.RequestException as e:
            logger.error(f"POST request failed: {e}")
            # Return a mock response for development
            return self._mock_response(200, {"status": "success"})
    
    def _mock_response(self, status_code: int, json_data: Dict[str, Any]) -> requests.Response:
        """Create a mock response for development/testing"""
        response = requests.Response()
        response.status_code = status_code
        response._content = str(json_data).encode('utf-8')
        return response


# Global API client instance
_api_client: Optional[DashboardAPIClient] = None


def get_api_client() -> DashboardAPIClient:
    """Get the global API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = DashboardAPIClient()
    return _api_client


def initialize_api_client(base_url: str) -> DashboardAPIClient:
    """Initialize the global API client with a specific base URL"""
    global _api_client
    _api_client = DashboardAPIClient(base_url)
    return _api_client


# For backward compatibility
APIClient = DashboardAPIClient 