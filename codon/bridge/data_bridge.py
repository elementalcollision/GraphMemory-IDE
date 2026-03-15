"""
Data Processing Bridge
======================
Provides Python-callable wrappers for Codon-compiled data processing modules.
Falls back to numpy/scipy implementations when Codon is unavailable.
"""

import logging
from typing import List, Tuple, Optional

from codon.bridge import CODON_ENABLED

logger = logging.getLogger(__name__)

# --- Attempt to load Codon compiled modules ---
CODON_DATA_AVAILABLE = False

if CODON_ENABLED:
    try:
        from codon.lib.similarity import (
            cosine_similarity as _codon_cosine,
            batch_cosine_similarity as _codon_batch_cosine,
            topk_similar as _codon_topk,
            euclidean_distance as _codon_euclidean,
        )
        from codon.lib.vector_ops import (
            normalize_vector as _codon_normalize,
            batch_normalize as _codon_batch_normalize,
            centroid as _codon_centroid,
            pairwise_distances as _codon_pairwise,
        )
        from codon.lib.hash_utils import (
            hash_params as _codon_hash_params,
        )
        CODON_DATA_AVAILABLE = True
        logger.info("Codon data processing kernels loaded successfully")
    except ImportError as e:
        logger.info(f"Codon data processing not available, using Python fallback: {e}")


# --- Public API ---

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if CODON_DATA_AVAILABLE:
        return _codon_cosine(a, b)

    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def batch_cosine_similarity(query: List[float], vectors: List[List[float]]) -> List[float]:
    """Compute cosine similarity between query and batch of vectors."""
    if CODON_DATA_AVAILABLE:
        return _codon_batch_cosine(query, vectors)

    return [cosine_similarity(query, v) for v in vectors]


def topk_similar(
    query: List[float],
    vectors: List[List[float]],
    k: int
) -> List[Tuple[int, float]]:
    """Find top-k most similar vectors to query."""
    if CODON_DATA_AVAILABLE:
        return _codon_topk(query, vectors, k)

    scores = batch_cosine_similarity(query, vectors)
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(idx, score) for idx, score in indexed[:k]]


def normalize_vector(v: List[float]) -> List[float]:
    """L2 normalize a vector."""
    if CODON_DATA_AVAILABLE:
        return _codon_normalize(v)

    import math
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return v
    return [x / norm for x in v]


def hash_cache_key(analytics_type: str, param_str: str) -> str:
    """Generate cache key using fast native hashing."""
    if CODON_DATA_AVAILABLE:
        return _codon_hash_params(analytics_type, param_str)

    import hashlib
    param_hash = hashlib.md5(param_str.encode()).hexdigest()
    return f"analytics:{analytics_type}:{param_hash}"
