"""
Authentication Components

This module provides Streamlit components for user authentication,
including login forms and authentication state management.
"""

import streamlit as st
import requests
from typing import Optional
import logging
from utils.auth_utils import store_token, clear_auth_session, is_authenticated

logger = logging.getLogger(__name__)


def check_authentication() -> bool:
    """Check if user is authenticated, show login if not"""
    if not is_authenticated():
        render_login_page()
        return False
    return True


def render_login_page():
    """Render the complete login page"""
    st.set_page_config(
        page_title="GraphMemory-IDE Login",
        page_icon="🔐",
        layout="centered"
    )
    
    # Load custom CSS
    try:
        with open('assets/styles.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass  # CSS file not found, continue without custom styles
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="login-container">
        """, unsafe_allow_html=True)
        
        st.title("🧠 GraphMemory-IDE")
        st.subheader("🔐 Dashboard Login")
        st.markdown("---")
        
        render_login_form()
        
        st.markdown("""
        </div>
        """, unsafe_allow_html=True)
        
        # Additional info
        with st.expander("ℹ️ About GraphMemory-IDE"):
            st.markdown("""
            **GraphMemory-IDE** is a real-time analytics dashboard for monitoring
            your graph memory system performance, including:
            
            - 📊 **Real-time Analytics**: Live system performance metrics
            - 🧠 **Memory Insights**: Memory distribution and growth tracking  
            - 🔗 **Graph Metrics**: Network topology and connectivity analysis
            - 🔄 **Live Updates**: Auto-refreshing data streams
            """)


def render_login_form():
    """Render the login form"""
    with st.form("login_form", clear_on_submit=False):
        st.markdown("### Enter your credentials")
        
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            help="Your GraphMemory-IDE username"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            help="Your GraphMemory-IDE password"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button(
                "🚀 Login",
                use_container_width=True,
                type="primary"
            )
        
        if submit:
            if not username or not password:
                st.error("❌ Please enter both username and password")
                return
            
            with st.spinner("🔐 Authenticating..."):
                if authenticate_user(username, password):
                    st.success("✅ Login successful! Redirecting...")
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with FastAPI backend"""
    try:
        # Prepare login data
        login_data = {
            "username": username,
            "password": password
        }
        
        # Make authentication request
        response = requests.post(
            "http://localhost:8000/auth/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if access_token:
                store_token(access_token)
                logger.info(f"User {username} authenticated successfully")
                return True
            else:
                logger.error("No access token in response")
                return False
                
        elif response.status_code == 401:
            logger.warning(f"Authentication failed for user {username}")
            return False
        else:
            logger.error(f"Authentication error: HTTP {response.status_code}")
            st.error(f"Server error: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to authentication server. Please check if the server is running.")
        logger.error("Connection error during authentication")
        return False
    except requests.exceptions.Timeout:
        st.error("⏱️ Authentication request timed out. Please try again.")
        logger.error("Timeout during authentication")
        return False
    except Exception as e:
        st.error(f"❌ Authentication error: {str(e)}")
        logger.error(f"Unexpected authentication error: {e}")
        return False


def render_logout_button():
    """Render logout button in sidebar"""
    if st.button("🚪 Logout", key="logout_btn"):
        clear_auth_session()
        st.success("👋 Logged out successfully!")
        st.rerun()


def render_user_info():
    """Render user information in sidebar"""
    from utils.auth_utils import get_user_info
    
    user_info = get_user_info()
    if user_info:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 User Info")
        st.sidebar.markdown(f"**Username:** {user_info.get('username', 'Unknown')}")
        
        # Token expiry info
        if user_info.get('expires'):
            from datetime import datetime, timezone
            exp_time = datetime.fromtimestamp(user_info['expires'], tz=timezone.utc)
            st.sidebar.markdown(f"**Session expires:** {exp_time.strftime('%H:%M:%S')}")


def require_authentication(func):
    """Decorator to require authentication for a function"""
    def wrapper(*args, **kwargs):
        if not check_authentication():
            return None
        return func(*args, **kwargs)
    return wrapper 