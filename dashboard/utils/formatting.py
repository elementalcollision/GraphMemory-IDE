"""
Dashboard Formatting Utilities

This module provides formatting utilities for displaying data
in the dashboard, including timestamps, durations, and severity colors.
"""

from datetime import datetime
from typing import Optional, Dict, Union
import logging

logger = logging.getLogger(__name__)


def format_timestamp(timestamp: Optional[Union[str, datetime]]) -> str:
    """Format a timestamp string for display"""
    if timestamp is None:
        return "N/A"
    
    try:
        dt: datetime
        if isinstance(timestamp, datetime):
            dt = timestamp
        elif isinstance(timestamp, str):
            # Try to parse ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            # Fallback for unknown types
            return str(timestamp)  # type: ignore[unreachable]
        
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return str(timestamp) if timestamp else "N/A"


def format_duration(start_time: Optional[Union[str, datetime]], end_time: Optional[Union[str, datetime]] = None) -> str:
    """Format duration between two timestamps"""
    if start_time is None:
        return "N/A"
    
    try:
        start_dt: datetime
        if isinstance(start_time, datetime):
            start_dt = start_time
        elif isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            return "N/A"  # type: ignore[unreachable]
        
        end_dt: datetime
        if end_time is None:
            end_dt = datetime.now()
        elif isinstance(end_time, datetime):
            end_dt = end_time
        elif isinstance(end_time, str):
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            return "N/A"  # type: ignore[unreachable]
        
        duration = end_dt - start_dt
        
        # Format duration nicely
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
            
    except (ValueError, AttributeError):
        return "N/A"


def get_severity_color(severity: str) -> str:
    """Get color code for severity level"""
    severity_colors = {
        'CRITICAL': '#dc3545',  # Red
        'HIGH': '#fd7e14',      # Orange  
        'MEDIUM': '#ffc107',    # Yellow
        'LOW': '#20c997',       # Teal
        'INFO': '#6c757d'       # Gray
    }
    
    return severity_colors.get(severity.upper(), '#6c757d')


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format"""
    if bytes_value == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(bytes_value)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a decimal value as percentage"""
    try:
        return f"{value * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with specified decimal places"""
    try:
        if value >= 1_000_000:
            return f"{value / 1_000_000:.{decimals}f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.{decimals}f}K"
        else:
            return f"{value:.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A" 