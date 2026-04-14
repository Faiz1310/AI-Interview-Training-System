"""Adaptive question selection engine with deterministic behavior and fallbacks."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from ai_modules.rag import (
    generate_questions,
    build_resume_grounded_fallback_questions,
    _get_embedding_model,
)
from models.answer import InterviewAnswer
from models.resume import Resume
from models.session import InterviewSession
from services.ai_service import groq_chat
from services.text_normalization import lexical_similarity, normalize_question

MAX_CANDIDATES = 20
NEAR_DUP_THRESHOLD = 0.88
RECENT_SIMILARITY_WINDOW = 12
TOPIC_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7
COLD_START_TURNS = 3
TREND_GATE_MIN_ANSWERS = 4
TREND_DEADBAND = 3.0
EARLY_RISK_CAP_TURNS = 4

_TOPIC_CACHE: Dict[str, tuple[str, float]] = {}


@dataclass
class QuestionSelection:
    question_text: str
    normalized_question: str
    question_type: str
    difficulty_level: int
    topic: str
    is_reused: bool
    selection_reason: str
    selection_context: dict
    previous_score: Optional[float]

    def to_api(self) -> dict:
        return {
            "question": self.question_text,
            "question_text": self.question_text,
            "type": self.question_type,
            "question_type": self.question_type,
            "difficulty_level": self.difficulty_level,
            "topic": self.topic,
            "is_reused": self.is_reused,
            "selection_reason": self.selection_reason,
            "selection_context": self.selection_context,
            "previous_score": self.previous_score,
        }


def _cosine_similarities(question: str, existing_questions: Sequence[str]) -> List[float]:
    if not existing_questions:
        return []
    model = _get_embedding_model()
    vectors = model.encode([question, *existing_questions], show_progress_bar=False)
    base = vectors[0]
    base_norm = (base @ base) ** 0.5 or 1.0
    sims: List[float] = []
    for vec in vectors[1:]:
        denom = (base_norm * ((vec @ vec) ** 0.5 or 1.0))
        sims.append(float((base @ vec) / denom) if denom else 0.0)
    return sims


def _is_near_duplicate(candidate: str, compare_pool: Sequence[str]) -> bool:
    if not compare_pool:
        return False

    lexical_hits = [q for q in compare_pool if lexical_similarity(candidate, q) >= 0.60]
    if not lexical_hits:
        return False

    sims = _cosine_similarities(candidate, lexical_hits)
    return any(sim >= NEAR_DUP_THRESHOLD for sim in sims)


def _classify_topic(question_text: str) -> str:
    norm = normalize_question(question_text)
    if not norm:
        return "general"

    cached = _TOPIC_CACHE.get(norm)
    now = time.time()
    if cached and cached[1] > now:
        return cached[0]

    prompt = (
        "Classify the interview question topic and return JSON only.\n"
        "Allowed topics: Machine Learning, Data Science, Databases, DSA, Backend, Frontend, System Design, DevOps, Behavioral, General.\n"
        f"Question: {question_text}\n"
        "Return exactly: {\"topic\": \"<one topic>\"}"
    )

    topic = "general"
    try:
        raw = groq_chat(messages=[{"role": "user", "content": prompt}], temperature=0.0, max_tokens=80)
        raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            parsed = json.loads(raw[start : end + 1])
            candidate = str(parsed.get("topic", "general")).strip()
            if candidate:
                topic = candidate
    except Exception:
        topic = "general"

    _TOPIC_CACHE[norm] = (topic, now + TOPIC_CACHE_TTL_SECONDS)
    return topic


def _recent_scores(answers: Sequence[InterviewAnswer]) -> List[float]:
    return [float(a.overall or 0.0) for a in answers if a.overall is not None]


def compute_recent_trend(scores: Sequence[float], window: int = 3) -> float:
    if len(scores) < TREND_GATE_MIN_ANSWERS:
        return 0.0
    recent = scores[-window:]
    previous = scores[-2 * window : -window]
    if not previous:
        return 0.0
    recent_avg = sum(recent) / len(recent)
    prev_avg = sum(previous) / len(previous)
    delta = recent_avg - prev_avg
    if abs(delta) < TREND_DEADBAND:
        return 0.0
    return delta


def compute_next_difficulty(session: InterviewSession, answers: Sequence[InterviewAnswer]) -> int:
    current = int(session.current_difficulty or 2)
    scores = _recent_scores(answers)
    n = min(3, len(scores))
    if n < 2:
        return current

    recent_avg = sum(scores[-n:]) / n
    trend_delta = compute_recent_trend(scores)
    turn = len(scores)

    # Cooldown: avoid difficulty changes in consecutive turns
    if turn - int(session.last_difficulty_change_turn or 0) <= 1:
        return current

    target = current
    if recent_avg >= 75:
        target = min(3, current + 1)
    elif recent_avg < 50:
        target = max(1, current - 1)

    # Trend-aware bias for stable improvement.
    if trend_delta > 0 and target == current and recent_avg >= 70:
        target = min(3, current + 1)
    if trend_delta < 0 and target > current:
        target = current

    if bool(session.resume_risk_flag) and turn < EARLY_RISK_CAP_TURNS:
        target = min(2, target)

    return target


def _reuse_target(total_asked: int) -> int:
    return round(total_asked * 0.30)


def _topic_counts(answers: Sequence[InterviewAnswer]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for answer in answers:
        topic = (answer.topic or "general").strip() or "general"
        counts[topic] = counts.get(topic, 0) + 1
    return counts


def _reuse_rank(answer: InterviewAnswer, weak_topics: set[str], current_turn: int) -> float:
    prev_score = float(answer.overall or 0.0)
    low_score_component = max(0.0, 100.0 - prev_score)
    importance = 12.0 if (answer.question_type or "") in {"technical", "project"} else 8.0
    topic_bonus = 10.0 if (answer.topic or "") in weak_topics else 0.0
    spacing = min(15.0, max(0.0, current_turn - int(answer.id or 0)) * 0.5)
    return low_score_component + importance + topic_bonus + spacing


def _cold_start_diversity_filter(candidates: List[dict], answers: Sequence[InterviewAnswer]) -> List[dict]:
    if len(answers) >= COLD_START_TURNS:
        return candidates
    recent_types = {(a.question_type or "").lower() for a in answers[-2:]}
    filtered = [c for c in candidates if c.get("question_type", "").lower() not in recent_types]
    return filtered or candidates


def _default_question_fallback(resume: Resume, difficulty: int) -> List[dict]:
    return build_resume_grounded_fallback_questions(
        resume_text=resume.resume_text or "",
        jd_text=resume.jd_text or "",
        job_role=resume.job_role or "Candidate",
        difficulty_level=difficulty,
        limit=MAX_CANDIDATES,
    )


def _build_selection(
    question: dict,
    is_reused: bool,
    selection_reason: str,
    trigger_reason: str,
    previous_score: Optional[float] = None,
) -> QuestionSelection:
    question_text = str(question.get("question_text") or question.get("question") or "").strip()
    q_type = str(question.get("question_type") or question.get("type") or "technical").strip().lower() or "technical"
    difficulty_level = int(question.get("difficulty_level", 2))
    topic = str(question.get("topic") or _classify_topic(question_text)).strip() or "general"

    selection_context = {
        "difficulty": difficulty_level,
        "source": "reused" if is_reused else "new",
        "trigger_reason": trigger_reason,
    }

    return QuestionSelection(
        question_text=question_text,
        normalized_question=normalize_question(question_text),
        question_type=q_type,
        difficulty_level=max(1, min(3, difficulty_level)),
        topic=topic,
        is_reused=is_reused,
        selection_reason=selection_reason,
        selection_context=selection_context,
        previous_score=previous_score,
    )


def choose_next_question(db: Session, session: InterviewSession, resume: Resume) -> QuestionSelection:
    answers = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.session_id == session.id)
        .order_by(InterviewAnswer.id.asc())
        .all()
    )
    asked_norm = [a.normalized_question for a in answers if a.normalized_question]
    compare_pool = [a.question for a in answers[-RECENT_SIMILARITY_WINDOW:]]

    current_turn = len(answers)
    rng = random.Random(f"{session.id}:{current_turn}")
    current_difficulty = compute_next_difficulty(session, answers)
    session.current_difficulty = current_difficulty

    # Risk flag adjustment: bias fundamentals early.
    risk_trigger = bool(session.resume_risk_flag) and current_turn < EARLY_RISK_CAP_TURNS
    difficulty_for_generation = 1 if risk_trigger else current_difficulty

    # Cold start: force new-only with diversity for first turns.
    cold_start = current_turn < COLD_START_TURNS

    reuse_target = _reuse_target(current_turn)
    prefer_reuse = (
        not cold_start
        and session.reused_questions_count < reuse_target
        and not bool(session.last_question_was_reused)
    )

    # Stage 1: generate new candidates (capped), then filter duplicates.
    previous_score = float(answers[-1].overall) if answers and answers[-1].overall is not None else None

    generated = generate_questions(
        resume_id=resume.id,
        job_role=resume.job_role,
        difficulty_level=difficulty_for_generation,
        limit=MAX_CANDIDATES,
        max_candidates=MAX_CANDIDATES,
        previous_score=previous_score,
    )
    generated = _cold_start_diversity_filter(generated[:MAX_CANDIDATES], answers)

    new_candidates: List[dict] = []
    for candidate in generated:
        q_text = str(candidate.get("question_text") or candidate.get("question") or "").strip()
        if not q_text:
            continue
        norm = normalize_question(q_text)
        if not norm or norm in asked_norm:
            continue
        if _is_near_duplicate(q_text, compare_pool):
            continue
        candidate["question_text"] = q_text
        candidate["question"] = q_text
        candidate["difficulty_level"] = int(candidate.get("difficulty_level", difficulty_for_generation))
        new_candidates.append(candidate)

    rng.shuffle(new_candidates)

    # Stage 2: prepare reuse candidates.
    reuse_rows = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.resume_id == resume.id)
        .filter(InterviewAnswer.session_id != session.id)
        .order_by(InterviewAnswer.id.desc())
        .limit(80)
        .all()
    )
    weak_topics = {a.topic for a in answers if (a.overall or 100.0) < 60 and a.topic}

    reuse_candidates = []
    for row in reuse_rows:
        q_text = (row.question or "").strip()
        norm = normalize_question(q_text)
        if not q_text or not norm or norm in asked_norm:
            continue
        if _is_near_duplicate(q_text, compare_pool):
            continue
        reuse_candidates.append(
            {
                "question_text": q_text,
                "question": q_text,
                "question_type": row.question_type or "technical",
                "difficulty_level": int(row.difficulty_level or difficulty_for_generation),
                "topic": row.topic or "general",
                "row": row,
                "rank": _reuse_rank(row, weak_topics=weak_topics, current_turn=current_turn),
            }
        )

    reuse_candidates.sort(key=lambda item: item["rank"], reverse=True)
    top_reuse = reuse_candidates[:5]
    rng.shuffle(top_reuse)
    reuse_candidates = top_reuse + reuse_candidates[5:]

    # Selection policy with explicit fallback hierarchy.
    if new_candidates and not prefer_reuse:
        selected = new_candidates[0]
        return _build_selection(
            question=selected,
            is_reused=False,
            selection_reason="new_question_matching_difficulty",
            trigger_reason="difficulty_and_distribution",
        )

    if prefer_reuse and reuse_candidates:
        selected = reuse_candidates[0]
        previous_question_topic = answers[-1].topic if answers else None
        if previous_question_topic:
            topic_preferred = [c for c in reuse_candidates if c.get("topic") != previous_question_topic]
            if topic_preferred:
                selected = topic_preferred[0]
                reason = "revisit_low_score_topic"
                trigger = "reuse_distribution_prefer_different_topic"
            else:
                reason = "revisit_low_score_topic"
                trigger = "reuse_distribution"
        else:
            reason = "revisit_low_score_topic"
            trigger = "reuse_distribution"

        return _build_selection(
            question=selected,
            is_reused=True,
            selection_reason=reason,
            trigger_reason=trigger,
            previous_score=float(selected["row"].overall or 0.0),
        )

    if new_candidates:
        selected = new_candidates[0]
        return _build_selection(
            question=selected,
            is_reused=False,
            selection_reason="new_question_matching_difficulty",
            trigger_reason="fallback_to_new",
        )

    if reuse_candidates:
        selected = reuse_candidates[0]
        return _build_selection(
            question=selected,
            is_reused=True,
            selection_reason="fallback_no_new_topic_alternation",
            trigger_reason="no_new_candidates",
            previous_score=float(selected["row"].overall or 0.0),
        )

    # Final fallback: default bank must always return a question.
    fallback_candidates = _default_question_fallback(resume, difficulty_for_generation)
    selected = fallback_candidates[0] if fallback_candidates else {
        "question_text": "Explain one key concept from your resume relevant to this role.",
        "question_type": "technical",
        "difficulty_level": difficulty_for_generation,
    }
    return _build_selection(
        question=selected,
        is_reused=False,
        selection_reason="fallback_resume_grounded_bank",
        trigger_reason="rag_failure_or_no_candidates",
    )


def update_session_question_counters(session: InterviewSession, is_reused: bool) -> None:
    if is_reused:
        session.reused_questions_count = int(session.reused_questions_count or 0) + 1
    else:
        session.new_questions_count = int(session.new_questions_count or 0) + 1
    session.last_question_was_reused = bool(is_reused)


def should_complete_session(session: InterviewSession, answers: Sequence[InterviewAnswer]) -> tuple[bool, str]:
    answered = len(answers)
    hard_limit = int(session.max_questions or session.total_questions or 10)
    if answered >= hard_limit:
        return True, "max_questions_reached"

    # Adaptive early stop for consistently low performance.
    if answered >= 5:
        recent = [float(a.overall or 0.0) for a in answers[-3:]]
        if recent and (sum(recent) / len(recent)) < 35:
            return True, "early_stop_low_performance"

    # Adaptive extension for high performance (bounded).
    if hard_limit < 12 and answered == hard_limit and answered >= 6:
        recent = [float(a.overall or 0.0) for a in answers[-3:]]
        if recent and (sum(recent) / len(recent)) >= 85:
            session.max_questions = hard_limit + 1
            return False, "extended_for_high_performance"

    return False, "continue"
