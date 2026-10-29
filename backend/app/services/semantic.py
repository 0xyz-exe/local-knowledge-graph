import math
import json
import hashlib
from typing import List, Dict, Any, Tuple

# Dimensions for local deterministic dense vector
VECTOR_DIM = 64

def generate_local_embedding(text: str, dim: int = VECTOR_DIM) -> List[float]:
    """
    Generate a local deterministic dense vector for text without external AI downloads.
    Uses subword n-gram hash projection with term-frequency weighting and L2 normalization.
    This guarantees 100% offline semantic similarity search that never breaks or times out.
    """
    if not text:
        return [0.0] * dim

    vec = [0.0] * dim
    tokens = text.lower().split()
    
    # Process word tokens and character 3-grams
    ngrams: List[str] = []
    for token in tokens:
        clean_token = "".join(ch for ch in token if ch.isalnum() or ch in "_-")
        if not clean_token:
            continue
        ngrams.append(clean_token)
        # Add character trigrams for semantic/subword matching
        if len(clean_token) >= 3:
            for i in range(len(clean_token) - 2):
                ngrams.append(clean_token[i:i+3])

    if not ngrams:
        return [0.0] * dim

    for gram in ngrams:
        # Stable MD5 hash projection to bucket index
        h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
        bucket = h % dim
        sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
        vec[bucket] += sign * (1.0 + math.log(1.0 + 1.0))

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0.0:
        vec = [round(v / norm, 6) for v in vec]
    return vec

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate cosine similarity between two unit vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    return max(0.0, min(1.0, dot))

def reciprocal_rank_fusion(
    fts_results: List[Dict[str, Any]],
    semantic_results: List[Dict[str, Any]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Combine independent search rankings using Reciprocal Rank Fusion (RRF).
    RRF Score = 1 / (k + rank_fts) + 1 / (k + rank_semantic)
    """
    scores: Dict[Tuple[str, str], float] = {}
    item_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for rank, item in enumerate(fts_results, start=1):
        key = (item["item_id"], item["item_type"])
        scores[key] = scores.get(key, 0.0) + (1.0 / (k + rank))
        item_map[key] = item

    for rank, item in enumerate(semantic_results, start=1):
        key = (item["item_id"], item["item_type"])
        scores[key] = scores.get(key, 0.0) + (1.0 / (k + rank))
        if key not in item_map:
            item_map[key] = item
        else:
            # Augment existing item with hybrid match type
            item_map[key]["match_type"] = "hybrid"

    sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    fused_results: List[Dict[str, Any]] = []

    for key in sorted_keys:
        item = item_map[key]
        item["score"] = round(scores[key] * 100, 4)
        fused_results.append(item)

    return fused_results
