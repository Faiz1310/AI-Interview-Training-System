"""
Hierarchical score computation.
Weights match the project specification exactly:
  Correctness: 50%
  Clarity:     30%
  Confidence:  20%
"""

WEIGHT_CORRECTNESS = 0.50
WEIGHT_CLARITY     = 0.30
WEIGHT_CONFIDENCE  = 0.20


def compute_overall(correctness: float, clarity: float, confidence: float) -> float:
    """
    Compute weighted overall score (0-100).
    overall = 0.50 * correctness + 0.30 * clarity + 0.20 * confidence
    """
    return (
        WEIGHT_CORRECTNESS * correctness
        + WEIGHT_CLARITY   * clarity
        + WEIGHT_CONFIDENCE * confidence
    )
