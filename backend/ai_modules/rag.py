"""Resume-grounded RAG module for interview question generation.

Design goals:
- Always ground generation in resume/JD context
- Build and reuse vector index artifacts per resume
- Use FAISS when available; fall back to embedding similarity when FAISS is not operational
- Never emit generic-question fallback without resume context
"""

from __future__ import annotations

import json
import logging
import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from database import SessionLocal
from models.resume import Resume

logger = logging.getLogger(__name__)

try:
    import faiss  # type: ignore
except (ImportError, ModuleNotFoundError):
    faiss = None

FAISS_AVAILABLE = faiss is not None

BACKEND_DIR = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR = BACKEND_DIR / "vector_store"
MODEL_NAME = "all-MiniLM-L6-v2"

CHUNK_WORDS = 400
CHUNK_OVERLAP_WORDS = 80
TOP_K_DEFAULT = 5
MAX_CANDIDATES = 20

_embedding_model: Optional[SentenceTransformer] = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(MODEL_NAME)
    return _embedding_model


def clean_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.replace("\r", "\n")
    normalized = re.sub(r"[\t\f\v]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> List[str]:
    """Split text into overlapping chunks (word-based).

    Default sizing follows requested range: 300-500 words, overlap 50-100 words.
    """
    clean = clean_text(text)
    if not clean:
        return []

    chunk_size = max(300, min(500, int(chunk_size or CHUNK_WORDS)))
    overlap = max(50, min(100, int(overlap or CHUNK_OVERLAP_WORDS)))

    words = clean.split()
    if not words:
        return []

    if len(words) <= chunk_size:
        return [" ".join(words)]

    step = max(1, chunk_size - overlap)
    chunks: List[str] = []

    for start in range(0, len(words), step):
        segment = words[start : start + chunk_size]
        if not segment:
            break
        chunk = " ".join(segment).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break

    return chunks


def _resume_artifact_paths(resume_id: int) -> Dict[str, Path]:
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "index": VECTOR_STORE_DIR / f"{resume_id}.index",
        "chunks": VECTOR_STORE_DIR / f"{resume_id}_chunks.pkl",
        "embeddings": VECTOR_STORE_DIR / f"{resume_id}_embeddings.npy",
    }


def _fetch_resume_payload(resume_id: int) -> Optional[Dict[str, str]]:
    db = SessionLocal()
    try:
        rec = db.query(Resume).filter(Resume.id == resume_id).first()
        if not rec:
            return None

        resume_text = clean_text(rec.resume_text or "")
        jd_text = clean_text(rec.jd_text or "")
        role = clean_text(rec.job_role or "") or "Candidate"

        combined = clean_text(f"Resume:\n{resume_text}\n\nJob Description:\n{jd_text}")
        if not combined:
            return None

        return {
            "job_role": role,
            "resume_text": resume_text,
            "jd_text": jd_text,
            "combined_text": combined,
        }
    finally:
        db.close()


def _embed_texts(texts: List[str]) -> np.ndarray:
    model = _get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return embeddings / norms


def create_faiss_index(resume_id: int, chunks: List[str]) -> None:
    if not chunks:
        return

    paths = _resume_artifact_paths(resume_id)
    embeddings = _embed_texts(chunks)

    with open(paths["chunks"], "wb") as f:
        pickle.dump(chunks, f)
    np.save(paths["embeddings"], embeddings)

    if not FAISS_AVAILABLE:
        logger.warning(
            "FAISS backend not loaded; semantic embedding retrieval remains active for resume %s",
            resume_id,
        )
        return

    try:
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(paths["index"]))
    except Exception as exc:
        logger.error("FAISS index creation failed for resume %s: %s", resume_id, exc, exc_info=True)


def _ensure_resume_index(resume_id: int) -> Tuple[bool, Optional[Dict[str, str]]]:
    paths = _resume_artifact_paths(resume_id)
    payload = _fetch_resume_payload(resume_id)
    if not payload:
        return False, None

    chunks_exist = paths["chunks"].exists()
    embeddings_exist = paths["embeddings"].exists()
    index_exists = paths["index"].exists()

    if chunks_exist and embeddings_exist and (index_exists or not FAISS_AVAILABLE):
        return True, payload

    chunks = chunk_text(payload["combined_text"], CHUNK_WORDS, CHUNK_OVERLAP_WORDS)
    if not chunks:
        return False, payload

    create_faiss_index(resume_id, chunks)
    return True, payload


def index_exists(resume_id: int) -> bool:
    paths = _resume_artifact_paths(resume_id)
    if FAISS_AVAILABLE:
        return paths["index"].exists() and paths["chunks"].exists()
    return paths["embeddings"].exists() and paths["chunks"].exists()


def _load_index_inputs(resume_id: int) -> Tuple[List[str], Optional[np.ndarray], Optional[object]]:
    paths = _resume_artifact_paths(resume_id)

    chunks: List[str] = []
    embeddings: Optional[np.ndarray] = None
    index_obj: Optional[object] = None

    if paths["chunks"].exists():
        with open(paths["chunks"], "rb") as f:
            chunks = pickle.load(f)

    if paths["embeddings"].exists():
        embeddings = np.load(paths["embeddings"]).astype("float32")

    if FAISS_AVAILABLE and paths["index"].exists():
        try:
            index_obj = faiss.read_index(str(paths["index"]))
        except Exception as exc:
            logger.error("FAISS index read failed for resume %s: %s", resume_id, exc, exc_info=True)

    return chunks, embeddings, index_obj


def retrieve_context(resume_id: int, query: str, top_k: int = TOP_K_DEFAULT) -> List[str]:
    """Retrieve resume-grounded context chunks.

    Never returns generic placeholders; if retrieval is weak, falls back to top resume chunks.
    """
    ok, payload = _ensure_resume_index(resume_id)
    if not ok or not payload:
        return []

    chunks, embeddings, index_obj = _load_index_inputs(resume_id)
    if not chunks:
        chunks = chunk_text(payload["combined_text"], CHUNK_WORDS, CHUNK_OVERLAP_WORDS)

    if not chunks:
        return []

    k = max(3, min(5, int(top_k or TOP_K_DEFAULT)))
    k = min(k, len(chunks))

    try:
        query_vec = _embed_texts([clean_text(query) or "Generate interview question for candidate"])

        # Preferred retrieval path: FAISS
        if index_obj is not None:
            _, indices = index_obj.search(query_vec, k)
            ranked = [chunks[i] for i in indices[0].tolist() if 0 <= i < len(chunks)]
            if ranked:
                return ranked

        # Robust fallback retrieval: cosine via stored embeddings
        if embeddings is not None and len(embeddings) == len(chunks):
            scores = (embeddings @ query_vec[0]).astype("float32")
            best_idx = np.argsort(scores)[::-1][:k].tolist()
            ranked = [chunks[i] for i in best_idx if 0 <= i < len(chunks)]
            if ranked:
                return ranked
    except Exception as exc:
        logger.error("Context retrieval failed for resume %s: %s", resume_id, exc, exc_info=True)

    # Final context fallback: first chunks from actual resume/JD text.
    return chunks[:k]


def _difficulty_from_score(previous_score: Optional[float], difficulty_level: int) -> Tuple[int, str]:
    if previous_score is None:
        level = max(1, min(3, int(difficulty_level or 2)))
    elif previous_score >= 80:
        level = 3
    elif previous_score >= 50:
        level = 2
    else:
        level = 1

    label = {1: "easy", 2: "medium", 3: "hard"}.get(level, "medium")
    return level, label


def _extract_resume_skills(text: str, limit: int = 8) -> List[str]:
    # Keep practical extraction logic: prioritize technology keywords visible in text.
    tech_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+.#-]{1,24}\b", text)
    lowered = [t.lower() for t in tech_tokens]

    allow = {
        "python", "flask", "fastapi", "django", "aws", "gcp", "azure", "docker", "kubernetes",
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sql", "pandas", "numpy", "scikit",
        "tensorflow", "pytorch", "react", "node", "typescript", "javascript", "java", "c++", "go",
        "linux", "git", "ci", "cd", "graphql", "rest", "microservices", "airflow",
    }

    selected: List[str] = []
    seen = set()
    for original, low in zip(tech_tokens, lowered):
        if low in allow and low not in seen:
            seen.add(low)
            selected.append(original)
        if len(selected) >= limit:
            break

    if selected:
        return selected

    # If no known technologies are detected, fall back to salient nouns/tokens.
    fallback = []
    for token in tech_tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        fallback.append(token)
        if len(fallback) >= limit:
            break
    return fallback


def build_resume_grounded_fallback_questions(
    resume_text: str,
    jd_text: str,
    job_role: str,
    difficulty_level: int,
    limit: int = 10,
) -> List[dict]:
    """Deterministic resume-based fallback when LLM output is invalid/unavailable."""
    level = max(1, min(3, int(difficulty_level or 2)))
    skills = _extract_resume_skills(f"{resume_text} {jd_text}", limit=10)
    if not skills:
        skills = [job_role or "your background"]

    templates = {
        1: "Based on your experience with {skill}, explain a basic implementation approach relevant to the {role} role.",
        2: "You listed {skill}. Describe a production tradeoff you handled and why your decision fit the {role} requirements.",
        3: "Using your {skill} background, design a scalable, failure-tolerant solution for a high-load {role} scenario and justify key architectural choices.",
    }

    q_type = {1: "technical", 2: "project", 3: "technical"}[level]
    output: List[dict] = []
    seen = set()

    for skill in skills:
        text = templates[level].format(skill=skill, role=job_role or "target")
        key = text.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "question_text": text,
                "question": text,
                "question_type": q_type,
                "type": q_type,
                "difficulty_level": level,
            }
        )
        if len(output) >= limit:
            break

    return output


def _build_prompt(
    context_chunks: List[str],
    previous_score: Optional[float],
    difficulty_level: int,
    difficulty_label: str,
    job_role: str,
    max_candidates: int,
) -> str:
    context_block = "\n\n".join(context_chunks)
    score_str = "N/A" if previous_score is None else f"{previous_score:.2f}"

    return (
        "You are an expert AI technical interviewer.\n\n"
        f"Candidate Resume Context:\n{context_block}\n\n"
        "Previous Performance:\n"
        f"Score: {score_str}\n\n"
        "Difficulty Level:\n"
        f"{difficulty_label} (numeric={difficulty_level})\n\n"
        "Instruction:\n"
        "Generate interview questions strictly based on the candidate resume context.\n"
        "Do NOT ask generic interview questions.\n"
        "Every question must explicitly reference at least one skill, tool, domain, or project visible in the resume context.\n"
        f"Generate exactly {max_candidates} questions for a {job_role} interview.\n"
        "Return JSON array only, no markdown, no commentary:\n"
        "["
        "{\"question_text\": \"...\", \"question_type\": \"technical|behavioral|project\", \"difficulty_level\": 1|2|3}"
        "]"
    )


def _parse_questions(raw: str, desired_level: int) -> List[dict]:
    cleaned = re.sub(r"```json|```", "", raw or "").strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        return []

    try:
        parsed = json.loads(cleaned[start : end + 1])
    except Exception:
        return []

    output: List[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue

        question_text = clean_text(str(item.get("question_text") or item.get("question") or ""))
        if not question_text:
            continue

        q_type = str(item.get("question_type") or item.get("type") or "technical").strip().lower()
        if q_type not in {"technical", "behavioral", "project"}:
            q_type = "technical"

        try:
            q_level = int(item.get("difficulty_level", desired_level))
        except Exception:
            q_level = desired_level

        q_level = max(1, min(3, q_level))

        output.append(
            {
                "question_text": question_text,
                "question": question_text,
                "question_type": q_type,
                "type": q_type,
                "difficulty_level": q_level,
            }
        )

    return output


def _is_resume_grounded(question_text: str, context_text: str) -> bool:
    q = question_text.lower()
    # Block common generic patterns.
    generic_markers = [
        "tell me about yourself",
        "greatest strength",
        "greatest weakness",
        "why should we hire you",
        "where do you see yourself",
    ]
    if any(marker in q for marker in generic_markers):
        return False

    skills = _extract_resume_skills(context_text, limit=12)
    if not skills:
        return len(question_text.split()) >= 8

    return any(skill.lower() in q for skill in skills)


def _dedupe_questions(items: List[dict], limit: int) -> List[dict]:
    out: List[dict] = []
    seen = set()
    for item in items:
        key = clean_text(str(item.get("question_text", ""))).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def get_default_questions(difficulty_level: int = 2, limit: int = 10) -> List[dict]:
    """Backward-compatible deterministic questions.

    Kept for compatibility with existing imports. This path avoids classic generic prompts.
    """
    return build_resume_grounded_fallback_questions(
        resume_text="core experience",
        jd_text="role requirements",
        job_role="target role",
        difficulty_level=difficulty_level,
        limit=limit,
    )


def generate_questions(
    resume_id: int,
    job_role: str,
    difficulty_level: int = 2,
    limit: int = 10,
    max_candidates: int = MAX_CANDIDATES,
    previous_score: Optional[float] = None,
) -> List[dict]:
    """Generate resume-grounded interview questions.

    No generic fallback path: on retrieval/LLM failure, emits deterministic resume-grounded questions.
    """
    payload = _fetch_resume_payload(resume_id)
    if not payload:
        logger.error("Resume %s not found for question generation", resume_id)
        return []

    level, label = _difficulty_from_score(previous_score, difficulty_level)
    effective_role = clean_text(job_role or payload.get("job_role") or "Candidate")

    query = "Generate interview question for candidate"
    context_chunks = retrieve_context(resume_id=resume_id, query=query, top_k=TOP_K_DEFAULT)
    if not context_chunks:
        context_chunks = chunk_text(payload["combined_text"], CHUNK_WORDS, CHUNK_OVERLAP_WORDS)[:TOP_K_DEFAULT]

    if not context_chunks:
        logger.error("No resume context available for resume %s", resume_id)
        return []

    prompt = _build_prompt(
        context_chunks=context_chunks,
        previous_score=previous_score,
        difficulty_level=level,
        difficulty_label=label,
        job_role=effective_role,
        max_candidates=max(5, min(MAX_CANDIDATES, int(max_candidates or MAX_CANDIDATES))),
    )

    context_text = "\n".join(context_chunks)

    parsed_questions: List[dict] = []
    try:
        from services.ai_service import groq_chat

        raw = groq_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
            max_tokens=1400,
            timeout=20.0,
        )
        parsed_questions = _parse_questions(raw, desired_level=level)
    except Exception as exc:
        logger.error("Groq question generation failed for resume %s: %s", resume_id, exc, exc_info=True)

    grounded = [q for q in parsed_questions if _is_resume_grounded(q["question_text"], context_text)]
    grounded = _dedupe_questions(grounded, limit=max(1, min(20, int(limit or 10))))

    if grounded:
        return grounded

    logger.warning("Using deterministic resume-grounded fallback for resume %s", resume_id)
    fallback = build_resume_grounded_fallback_questions(
        resume_text=payload.get("resume_text", ""),
        jd_text=payload.get("jd_text", ""),
        job_role=effective_role,
        difficulty_level=level,
        limit=max(1, min(20, int(limit or 10))),
    )
    return _dedupe_questions(fallback, limit=max(1, min(20, int(limit or 10))))
