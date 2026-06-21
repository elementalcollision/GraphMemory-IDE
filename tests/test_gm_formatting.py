"""
Tests for dashboard/utils/formatting.py pure formatting helpers.

These tests cover format_bytes, format_percentage, and get_severity_color.
Functions that call datetime.now() (like format_duration) are not tested here.
"""

import os
import sys

# Make the repo root importable so dashboard.utils.formatting (a stdlib-only
# module) resolves under pytest regardless of import mode / cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.utils.formatting import (
    format_bytes,
    format_percentage,
    get_severity_color,
)


class TestFormatBytes:
    """Test format_bytes boundary conditions."""
    
    def test_zero_bytes(self):
        assert format_bytes(0) == "0 B"
    
    def test_bytes_below_kb_threshold(self):
        # 1023 bytes should stay as bytes
        assert format_bytes(1023) == "1023.0 B"
    
    def test_exact_kb_threshold(self):
        # 1024 bytes = 1.0 KB
        assert format_bytes(1024) == "1.0 KB"
    
    def test_exact_mb_threshold(self):
        # 1024^2 bytes = 1.0 MB
        assert format_bytes(1024**2) == "1.0 MB"
    
    def test_exact_gb_threshold(self):
        # 1024^3 bytes = 1.0 GB
        assert format_bytes(1024**3) == "1.0 GB"


class TestFormatPercentage:
    """Test format_percentage decimal formatting."""
    
    def test_basic_percentage(self):
        assert format_percentage(0.5) == "50.0%"
    
    def test_zero_percentage(self):
        assert format_percentage(0.0) == "0.0%"
    
    def test_full_percentage(self):
        assert format_percentage(1.0) == "100.0%"
    
    def test_custom_decimals(self):
        assert format_percentage(0.12345, decimals=3) == "12.345%"


class TestGetSeverityColor:
    """Test get_severity_color mapping."""
    
    def test_critical_severity(self):
        assert get_severity_color('CRITICAL') == '#dc3545'
    
    def test_high_severity(self):
        assert get_severity_color('HIGH') == '#fd7e14'
    
    def test_medium_severity(self):
        assert get_severity_color('MEDIUM') == '#ffc107'
    
    def test_low_severity(self):
        assert get_severity_color('LOW') == '#20c997'
    
    def test_info_severity(self):
        assert get_severity_color('INFO') == '#6c757d'
    
    def test_case_insensitive(self):
        assert get_severity_color('critical') == '#dc3545'
        assert get_severity_color('High') == '#fd7e14'
    
    def test_unknown_severity(self):
        # Unknown severity should return default gray
        assert get_severity_color('UNKNOWN') == '#6c757d'
