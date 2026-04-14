"""Dashboard analytics routes."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from auth.jwt_handler import verify_token
from database import get_db
from models.answer import InterviewAnswer
from models.resume import Resume
from models.session import InterviewSession

router = APIRouter()
security = HTTPBearer()


def get_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> int:
    return int(verify_token(credentials.credentials)["sub"])


def _cr(v) -> float:
    if v is None: return 0.0
    return round(max(0.0, min(100.0, float(v))), 2)


@router.get("/dashboard")
def get_dashboard(
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
    resume_id: Optional[int] = None,
):
    selected_resume_id = resume_id
    if selected_resume_id is None:
        latest_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .first()
        )
        selected_resume_id = latest_resume.id if latest_resume else None

    if selected_resume_id is not None:
        owned_resume = db.query(Resume).filter(Resume.id == selected_resume_id, Resume.user_id == user_id).first()
        if not owned_resume:
            raise HTTPException(status_code=404, detail="Resume not found")

    query = (
        db.query(InterviewSession, Resume.job_role)
        .join(Resume, InterviewSession.resume_id == Resume.id)
        .options(joinedload(InterviewSession.answers))
        .filter(InterviewSession.user_id == user_id)
        .filter(InterviewSession.is_deleted == False)
        .filter(InterviewSession.status == "completed")
        .filter(InterviewSession.overall_score.isnot(None))
    )
    if selected_resume_id is not None:
        query = query.filter(InterviewSession.resume_id == selected_resume_id)
    rows = query.order_by(InterviewSession.created_at.asc()).all()

    session_summary, progress_trend = [], []
    correctness_list, clarity_list, confidence_list = [], [], []

    for session, job_role in rows:
        session_summary.append({
            "session_id": session.id,
            "resume_id": session.resume_id,
            "job_role": job_role,
            "questions_answered": len(session.answers),
            "overall_score": _cr(session.overall_score),
            "correctness_score": _cr(session.correctness_score),
            "clarity_score": _cr(session.clarity_score),
            "confidence_score": _cr(session.confidence_score),
            "performance_label": session.performance_label,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        })
        progress_trend.append({
            "session_id": session.id,
            "overall_score": _cr(session.overall_score),
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "job_role": job_role,
        })
        if session.correctness_score: correctness_list.append(session.correctness_score)
        if session.clarity_score: clarity_list.append(session.clarity_score)
        if session.confidence_score: confidence_list.append(session.confidence_score)

    def avg(lst): return round(sum(lst) / len(lst), 2) if lst else 0.0

    return {
        "selected_resume_id": selected_resume_id,
        "session_summary": session_summary,
        "progress_trend": progress_trend,
        "skill_breakdown_average": {
            "correctness": avg(correctness_list),
            "clarity": avg(clarity_list),
            "confidence": avg(confidence_list),
        },
        "total_completed": len(rows),
    }


@router.get("/session/{session_id}")
def get_session_detail(
    session_id: int,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    result = (
        db.query(InterviewSession, Resume.job_role)
        .join(Resume, InterviewSession.resume_id == Resume.id)
        .options(joinedload(InterviewSession.answers))
        .filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    session, job_role = result
    answers = sorted(session.answers, key=lambda a: a.created_at or 0)

    return {
        "session_info": {
            "session_id": session.id,
            "resume_id": session.resume_id,
            "job_role": job_role,
            "status": session.status,
            "overall_score": _cr(session.overall_score),
            "correctness_score": _cr(session.correctness_score),
            "clarity_score": _cr(session.clarity_score),
            "confidence_score": _cr(session.confidence_score),
            "performance_label": session.performance_label,
            "coach_message": session.coach_message,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        },
        "answers": [
            {
                "answer_id": a.id,
                "question": a.question,
                "normalized_question": a.normalized_question,
                "question_type": a.question_type,
                "difficulty_level": a.difficulty_level,
                "topic": a.topic,
                "is_reused": a.is_reused,
                "selection_reason": a.selection_reason,
                "selection_context": a.selection_context,
                "previous_score": a.previous_score,
                "answer": a.answer,
                "correctness": _cr(a.correctness),
                "clarity": _cr(a.clarity),
                "confidence": _cr(a.confidence),
                "overall": _cr(a.overall),
                "correctness_explanation": a.correctness_explanation,
                "clarity_explanation": a.clarity_explanation,
                "improvement_tip": a.improvement_tip,
                "sub_scores": {
                    "llm": a.llm_score,
                    "cosine": a.cosine_score,
                    "keyword": a.keyword_score,
                },
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in answers
        ],
    }
