"""Resume upload, analysis, and listing routes."""
import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.jwt_handler import verify_token
from database import get_db
from models.resume import Resume
from services.text_extractor import extract_text_from_file

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    return int(verify_token(credentials.credentials)["sub"])


# ─── Upload Resume ─────────────────────────────────────────────────────────────
@router.post("/upload_resume")
def upload_resume(
    resume_file: UploadFile = File(...),
    job_role: str = Form(...),
    jd_file: Optional[UploadFile] = File(default=None),
    jd_text: Optional[str] = Form(default=None),
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    if not job_role or not job_role.strip():
        raise HTTPException(status_code=400, detail="job_role is required")

    resume_text = extract_text_from_file(resume_file)
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from resume file")

    # Build JD text
    jd_final = ""
    if jd_file and jd_file.filename:
        jd_final = extract_text_from_file(jd_file).strip()
    if jd_text:
        jd_final = (jd_final + "\n\n" + jd_text.strip()).strip()
    if not jd_final:
        raise HTTPException(status_code=400, detail="Provide a job description (file or text)")

    record = Resume(
        user_id=user_id,
        resume_text=resume_text,
        jd_text=jd_final,
        job_role=job_role.strip(),
        filename=resume_file.filename,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(f"Resume {record.id} uploaded by user {user_id} for role: {job_role}")

    return {
        "id": record.id,
        "job_role": record.job_role,
        "filename": record.filename,
        "message": "Resume uploaded successfully",
        "created_at": record.created_at.isoformat(),
    }


# ─── List User Resumes ─────────────────────────────────────────────────────────
@router.get("/resumes")
def list_resumes(user_id: int = Depends(get_user_id), db: Session = Depends(get_db)):
    """Return all resumes for the authenticated user (id, job_role, created_at)."""
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "job_role": r.job_role,
            "filename": r.filename,
            "analysis_score": r.analysis_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in resumes
    ]


# ─── Analyze Resume (Gemini) ───────────────────────────────────────────────────
class AnalyzeResumeRequest(BaseModel):
    resume_id: int
    force_refresh: bool = False


@router.post("/analyze_resume")
def analyze_resume(
    body: AnalyzeResumeRequest,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Analyze a resume using Gemini and return structured feedback.
    Results are cached — re-calling returns the stored result without re-running AI.
    """
    resume = db.query(Resume).filter(Resume.id == body.resume_id, Resume.user_id == user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Return cached result unless force_refresh is requested.
    if (
        not body.force_refresh
        and resume.analysis_score is not None
        and (resume.analysis_model_used or "") != "fallback"
    ):
        logger.info(f"Returning cached analysis for resume {body.resume_id}")
        return _build_analysis_response(resume)
    if not body.force_refresh and resume.analysis_score is not None and (resume.analysis_model_used or "") == "fallback":
        logger.info(f"Recomputing resume {body.resume_id} because previous analysis used fallback")
    if body.force_refresh:
        logger.info(f"Force re-analysis requested for resume {body.resume_id}")

    prompt = f"""You are an expert career consultant and resume reviewer.

Job Role: {resume.job_role}

Resume Content:
{resume.resume_text[:3000]}

Job Description:
{resume.jd_text[:2000]}

Analyze this resume against the job description and respond with ONLY valid JSON (no markdown, no code fences):
{{
    "analysis_score": <integer 0-100>,
  "summary": "<2-3 sentence overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>", "<strength 4>"],
  "weaknesses": ["<gap 1>", "<gap 2>", "<gap 3>"],
  "suggestions": ["<actionable suggestion 1>", "<actionable suggestion 2>", "<actionable suggestion 3>"],
  "improvement_tags": ["<tag1>", "<tag2>", "<tag3>", "<tag4>", "<tag5>"]
}}

Score guide: 90+=excellent match, 70-89=good match, 50-69=partial match, <50=significant gaps"""

    from services.ai_service import safe_resume_analysis
    data = safe_resume_analysis(prompt, temperature=0.3, timeout=20.0)

    # Persist results
    resume.analysis_score   = max(0.0, min(100.0, float(data.get("analysis_score", 50))))
    resume.analysis_model_used = data.get("model_used", "fallback")
    resume.analysis_summary = data.get("summary", "")
    resume.strengths        = json.dumps(data.get("strengths", []))
    resume.weaknesses       = json.dumps(data.get("weaknesses", []))
    resume.suggestions      = json.dumps(data.get("suggestions", []))
    db.commit()

    logger.info(f"Resume {body.resume_id} analyzed — score: {resume.analysis_score}, model: {resume.analysis_model_used}")
    return _build_analysis_response(resume)


def _build_analysis_response(resume: Resume) -> dict:
    threshold = 60.0

    def safe_json(val):
        if not val:
            return []
        try:
            return json.loads(val)
        except Exception:
            return []

    return {
        "resume_id":        resume.id,
        "job_role":         resume.job_role,
        "score":            resume.analysis_score,
        "analysis_score":   resume.analysis_score,
        "summary":          resume.analysis_summary,
        "strengths":        safe_json(resume.strengths),
        "weaknesses":       safe_json(resume.weaknesses),
        "suggestions":      safe_json(resume.suggestions),
        "model_used":       resume.analysis_model_used or "fallback",
        "risk_threshold":   threshold,
        "resume_risk_flag": (resume.analysis_score is not None and float(resume.analysis_score) < threshold),
    }
