"""
Codon Bridge Layer
==================
Provides a seamless interface between CPython application code and
Codon-compiled native modules. Each bridge module tries to load the
compiled .so/.dylib and falls back to pure Python implementations.

Usage:
    from codon.bridge.graph_bridge import betweenness_centrality, CODON_AVAILABLE
"""

import os
import logging

logger = logging.getLogger(__name__)

# Path to compiled Codon shared libraries
CODON_LIB_PATH = os.environ.get(
    "CODON_LIB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
)

CODON_ENABLED = os.environ.get("CODON_ENABLED", "true").lower() == "true"
CODON_FALLBACK = os.environ.get("CODON_FALLBACK", "true").lower() == "true"

# Minimum graph size to route through Codon (conversion overhead threshold)
CODON_MIN_GRAPH_SIZE = int(os.environ.get("CODON_MIN_GRAPH_SIZE", "100"))
