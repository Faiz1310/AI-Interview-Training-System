"""
Hybrid correctness evaluation:
  - Groq LLaMA 3.3 70B  → raw LLM score (0-100)   weight: 60%
  - SBERT cosine sim     → semantic relevance        weight: 25%
  - Keyword coverage     → domain term matching      weight: 15%

Final = 0.60 * llm + 0.25 * cosine + 0.15 * keyword
Gemini 1.5 Flash → rich explanation + improvement tip (separate call)

All external calls are wrapped with try/except. Fallback values are
returned on failure — the server never crashes from AI unavailability.
"""
import json
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# ─── SBERT model (lazy-loaded once; warm-loaded at startup via main.py) ────────
_sbert_model = None


def _get_sbert():
    global _sbert_model
    if _sbert_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SBERT model all-MiniLM-L6-v2...")
        _sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sbert_model


def _cosine_similarity(a, b) -> float:
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _cosine_score(question: str, answer: str) -> float:
    try:
        model = _get_sbert()
        embeddings = model.encode([question, answer])
        sim = _cosine_similarity(embeddings[0], embeddings[1])
        # sim in [-1, 1] → scale to [0, 100]
        return max(0.0, min(100.0, (sim + 1) / 2 * 100))
    except Exception as e:
        logger.warning(f"[SBERT cosine] failed: {e}")
        return 60.0  # neutral fallback


def _keyword_score(question: str, answer: str) -> float:
    """Check coverage of important words from the question in the answer."""
    STOP = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "what", "how", "why", "when", "where",
        "which", "who", "that", "this", "these", "those", "and", "or", "but",
        "in", "on", "at", "to", "for", "of", "with", "by", "from",
    }
    q_words = set(re.findall(r'\b\w+\b', question.lower())) - STOP
    a_words = set(re.findall(r'\b\w+\b', answer.lower()))
    if not q_words:
        return 70.0
    covered = q_words & a_words
    return min(100.0, (len(covered) / len(q_words)) * 100)


def _length_factor(answer: str) -> float:
    """Normalize by answer length — penalize very short, reward adequate depth."""
    words = len(answer.strip().split())
    if words < 10:  return 0.5
    if words < 25:  return 0.75
    if words < 300: return 1.0
    return 0.95  # slight penalty for excessive rambling


def _groq_score(question: str, answer: str) -> Tuple[float, str]:
    """
    Call Groq LLaMA 3.3 to score the answer 0-100 with brief reason.
    Returns (score, reason). Never raises — falls back to (60, "estimated").
    """
    from services.ai_service import groq_chat_safe

    prompt = f"""You are an expert technical interviewer. Evaluate the candidate's answer.

Question: {question}

Answer: {answer}

Respond ONLY with valid JSON — no markdown, no extra text:
{{
  "score": <integer 0-100>,
  "reason": "<one sentence why>"
}}

Scoring guide:
- 90-100: Complete, accurate, well-structured answer
- 70-89:  Mostly correct, minor gaps
- 50-69:  Partially correct, significant gaps
- 30-49:  Vague or mostly incorrect
- 0-29:   Irrelevant or no attempt"""

    fallback = {"score": 60, "reason": "Score estimated (LLM unavailable)"}
    raw = groq_chat_safe(
        messages=[{"role": "user", "content": prompt}],
        fallback=fallback,
        temperature=0.1,
        max_tokens=200,
    )

    try:
        raw = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        score  = max(0.0, min(100.0, float(data.get("score", 60))))
        reason = data.get("reason", "")
        return score, reason
    except Exception as e:
        logger.warning(f"[Groq score parse] failed: {e}")
        return 60.0, "Score estimated (parse error)"


def _gemini_explanation(question: str, answer: str, score: float) -> Tuple[str, str]:
    """
    Call Gemini Flash for a rich explanation and a specific improvement tip.
    Never raises — falls back to sensible defaults.
    """
    from services.ai_service import gemini_generate_safe

    prompt = f"""You are a professional interview coach. A candidate answered an interview question and received a score of {score:.0f}/100.

Question: {question}
Answer: {answer}
Score: {score:.0f}/100

Provide feedback in this exact JSON format (no markdown):
{{
  "explanation": "<2-3 sentences explaining what was good and what was lacking>",
  "improvement_tip": "<one specific, actionable tip the candidate should apply next time>"
}}"""

    fallback = {
        "explanation": f"Score: {score:.0f}/100. Keep practicing structured answers.",
        "improvement_tip": "Use the STAR method: Situation, Task, Action, Result.",
    }
    raw = gemini_generate_safe(prompt, fallback=fallback, temperature=0.4)

    try:
        raw  = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        return (
            data.get("explanation", fallback["explanation"]),
            data.get("improvement_tip", fallback["improvement_tip"]),
        )
    except Exception as e:
        logger.warning(f"[Gemini explanation parse] failed: {e}")
        return fallback["explanation"], fallback["improvement_tip"]


def evaluate_correctness(question: str, answer: str) -> Tuple[float, str, str, dict]:
    """
    Full hybrid evaluation.

    Returns:
        final_score  (float 0-100)
        explanation  (str) — Gemini rich feedback
        improvement_tip (str) — Gemini specific tip
        sub_scores   (dict) — {llm, cosine, keyword} for transparency
    """
    answer = answer.strip()
    if not answer or len(answer.split()) < 3:
        return (
            10.0,
            "Answer is too short to evaluate.",
            "Please provide a complete answer with at least a few sentences.",
            {"llm": 10, "cosine": 0, "keyword": 0},
        )

    # ── Compute all three sub-scores ─────────────────────────────────────────
    llm_score,   llm_reason  = _groq_score(question, answer)
    cosine_raw               = _cosine_score(question, answer)
    keyword_raw              = _keyword_score(question, answer)
    length_f                 = _length_factor(answer)

    # ── Weighted blend (preserving hybrid architecture) ───────────────────────
    raw_final = (
        0.60 * llm_score  +
        0.25 * cosine_raw +
        0.15 * keyword_raw
    ) * length_f

    final_score = max(0.0, min(100.0, raw_final))

    # ── Gemini explanation ────────────────────────────────────────────────────
    explanation, improvement_tip = _gemini_explanation(question, answer, final_score)

    sub_scores = {
        "llm":     round(llm_score, 1),
        "cosine":  round(cosine_raw, 1),
        "keyword": round(keyword_raw, 1),
    }

    return round(final_score, 2), explanation, improvement_tip, sub_scores
