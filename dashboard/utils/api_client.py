"""
API Client for Dashboard Data

This module provides a client for fetching data from the FastAPI SSE endpoints
and handling real-time data streaming for the dashboard.
"""

import streamlit as st
import requests
import json
from typing import Dict, Any, Optional
import logging
from .auth_utils import get_auth_headers

logger = logging.getLogger(__name__)


class DashboardAPIClient:
    """Client for fetching data from FastAPI SSE endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.timeout = 10
    
    def fetch_latest_data(self) -> Dict[str, Any]:
        """Fetch latest dashboard data (non-streaming)"""
        try:
            response = self.session.get(
                f"{self.base_url}/dashboard/latest",
                headers=get_auth_headers(),
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                st.error("🔐 Authentication required. Please log in again.")
                return {}
            else:
                st.warning(f"⚠️ API returned status code: {response.status_code}")
                return {}
        except requests.exceptions.ConnectionError:
            st.error("🔌 Cannot connect to server. Please check if the server is running.")
            return {}
        except requests.exceptions.Timeout:
            st.warning("⏱️ Request timed out. Server may be busy.")
            return {}
        except Exception as e:
            st.error(f"❌ Error fetching data: {e}")
            logger.error(f"API client error: {e}")
            return {}
    
    def fetch_analytics_data(self) -> Dict[str, Any]:
        """Fetch analytics data"""
        try:
            latest_data = self.fetch_latest_data()
            return latest_data.get('analytics', {})
        except Exception as e:
            st.error(f"❌ Error fetching analytics: {e}")
            logger.error(f"Analytics fetch error: {e}")
            return {}
    
    def fetch_memory_data(self) -> Dict[str, Any]:
        """Fetch memory insights data"""
        try:
            latest_data = self.fetch_latest_data()
            return latest_data.get('memory', {})
        except Exception as e:
            st.error(f"❌ Error fetching memory data: {e}")
            logger.error(f"Memory fetch error: {e}")
            return {}
    
    def fetch_graph_data(self) -> Dict[str, Any]:
        """Fetch graph metrics data"""
        try:
            latest_data = self.fetch_latest_data()
            return latest_data.get('graph', {})
        except Exception as e:
            st.error(f"❌ Error fetching graph data: {e}")
            logger.error(f"Graph fetch error: {e}")
            return {}
    
    def check_server_status(self) -> bool:
        """Check if the server is accessible"""
        try:
            response = self.session.get(
                f"{self.base_url}/dashboard/status",
                headers=get_auth_headers(),
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information and statistics"""
        try:
            response = self.session.get(
                f"{self.base_url}/dashboard/status",
                headers=get_auth_headers(),
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Connection info error: {e}")
            return {}


def get_api_client() -> DashboardAPIClient:
    """Get or create API client instance"""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = DashboardAPIClient()
    return st.session_state.api_client 