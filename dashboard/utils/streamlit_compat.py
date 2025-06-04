"""
Streamlit Compatibility Layer

This module provides compatibility functions for newer Streamlit features
that may not be available in older versions.
"""

import streamlit as st
from typing import Any, Dict, Optional, List
import pandas as pd

def st_rerun() -> None:
    """
    Compatibility function for st.rerun()
    Falls back to st.experimental_rerun() for older versions
    """
    # Check for rerun method existence at runtime
    if hasattr(st, 'rerun') and callable(getattr(st, 'rerun')):
        getattr(st, 'rerun')()
    elif hasattr(st, 'experimental_rerun') and callable(getattr(st, 'experimental_rerun')):
        getattr(st, 'experimental_rerun')()
    else:
        # For very old versions, refresh the entire app
        st.stop()

def st_data_editor(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Compatibility function for st.data_editor()
    Falls back to st.dataframe() for older versions
    """
    # Check for data_editor method existence at runtime
    if hasattr(st, 'data_editor') and callable(getattr(st, 'data_editor')):
        return getattr(st, 'data_editor')(data, **kwargs)
    else:
        # Fallback to read-only dataframe
        st.dataframe(data)
        return data

class ColumnConfig:
    """Mock column configuration for older Streamlit versions"""
    
    @staticmethod
    def CheckboxColumn(label: str, **kwargs: Any) -> Dict[str, Any]:
        return {"type": "checkbox", "label": label, **kwargs}
    
    @staticmethod
    def TextColumn(label: str, **kwargs: Any) -> Dict[str, Any]:
        return {"type": "text", "label": label, **kwargs}
    
    @staticmethod
    def NumberColumn(label: str, **kwargs: Any) -> Dict[str, Any]:
        return {"type": "number", "label": label, **kwargs}

def get_column_config() -> ColumnConfig:
    """
    Get column configuration object
    Returns real st.column_config if available, otherwise mock
    """
    # Check for column_config attribute existence at runtime
    if hasattr(st, 'column_config'):
        return getattr(st, 'column_config')
    else:
        return ColumnConfig()

# Monkey patch Streamlit if needed - use setattr for safety
if not hasattr(st, 'rerun'):
    setattr(st, 'rerun', st_rerun)

if not hasattr(st, 'data_editor'):
    setattr(st, 'data_editor', st_data_editor)

if not hasattr(st, 'column_config'):
    setattr(st, 'column_config', get_column_config()) 