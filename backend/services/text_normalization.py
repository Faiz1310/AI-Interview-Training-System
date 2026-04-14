"""Shared text normalization and lexical similarity helpers."""

import re
import string

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_question(text: str) -> str:
    """Normalize question text for cache keys and duplicate checks."""
    if not text:
        return ""
    lowered = text.lower().translate(_PUNCT_TABLE)
    collapsed = _WHITESPACE_RE.sub(" ", lowered)
    return collapsed.strip()


def lexical_similarity(a: str, b: str) -> float:
    """Simple Jaccard token overlap for low-cost duplicate prefiltering."""
    a_norm = normalize_question(a)
    b_norm = normalize_question(b)
    if not a_norm or not b_norm:
        return 0.0

    set_a = set(a_norm.split())
    set_b = set(b_norm.split())
    if not set_a or not set_b:
        return 0.0

    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return inter / union
