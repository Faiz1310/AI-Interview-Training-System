"""
Clarity evaluation — improved rule-based.
Evaluates: length adequacy, repetition, structure, filler word usage.
Returns (score 0-100, explanation string).
"""
import re
from typing import Tuple

MIN_WORDS = 20
IDEAL_MIN_WORDS = 40

FILLER_WORDS = {
    "um", "uh", "like", "you know", "basically", "literally",
    "actually", "honestly", "sort of", "kind of", "i mean", "right",
}


def _count_repeated_phrases(text: str) -> int:
    words = text.lower().split()
    if len(words) < 2:
        return 0
    phrases = [" ".join(words[i:i+2]) for i in range(len(words) - 1)]
    seen = {}
    repeats = 0
    for p in phrases:
        seen[p] = seen.get(p, 0) + 1
        if seen[p] == 2:
            repeats += 1
    return repeats


def _count_filler_words(text: str) -> int:
    text_lower = text.lower()
    count = 0
    for filler in FILLER_WORDS:
        count += len(re.findall(r'\b' + re.escape(filler) + r'\b', text_lower))
    return count


def _has_broken_structure(text: str) -> bool:
    sentences = re.split(r'[.!?]+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return True
    very_short = sum(1 for s in sentences if len(s.split()) < 3)
    if len(sentences) > 1 and very_short >= len(sentences):
        return True
    if len(text.strip()) > 50 and not re.search(r'[.!?]$', text.strip()):
        return True
    return False


def evaluate_clarity(question: str, answer: str) -> Tuple[float, str]:
    answer = answer.strip()
    words = answer.split()
    word_count = len(words)
    score = 100.0
    reasons = []

    # Length penalty — smooth curve instead of cliff
    if word_count < 5:
        score -= 50
        reasons.append(f"Answer is too short ({word_count} words)")
    elif word_count < MIN_WORDS:
        penalty = (MIN_WORDS - word_count) * 1.5
        score -= min(30, penalty)
        reasons.append(f"Answer is brief ({word_count} words; aim for {IDEAL_MIN_WORDS}+)")
    elif word_count < IDEAL_MIN_WORDS:
        penalty = (IDEAL_MIN_WORDS - word_count) * 0.5
        score -= min(10, penalty)

    # Repetition penalty
    repeats = _count_repeated_phrases(answer)
    if repeats > 0:
        penalty = min(20, repeats * 5)
        score -= penalty
        reasons.append(f"Repeated phrases detected ({repeats}×)")

    # Filler words
    fillers = _count_filler_words(answer)
    if fillers > 3:
        penalty = min(15, (fillers - 3) * 3)
        score -= penalty
        reasons.append(f"Excessive filler words ({fillers})")

    # Structure
    if _has_broken_structure(answer):
        score -= 10
        reasons.append("Answer has fragmented or incomplete sentences")

    score = max(0.0, min(100.0, score))
    explanation = "; ".join(reasons) if reasons else "Answer demonstrates good clarity and structure."
    return round(score, 2), explanation
