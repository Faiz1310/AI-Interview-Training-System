"""
Feedback Routes - API endpoints for interview feedback and analysis.

Endpoints:
- GET /session/{session_id}/feedback - Get structured feedback for completed session
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from database import get_db
from auth.jwt_handler import verify_token
from services.feedback_service import generate_feedback_report
from models.session import InterviewSession
from models.user import User

router = APIRouter(prefix="/session", tags=["feedback"])
security = HTTPBearer()


def get_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> int:
    return int(verify_token(credentials.credentials)["sub"])


@router.get("/{session_id}/feedback")
async def get_session_feedback(
    session_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user_id: Annotated[int, Depends(get_user_id)] = None,
):
    """
    Get structured feedback for a completed interview session.
    
    Returns:
    {
        "session_id": int,
        "overall_score": float (0-100),
        "performance_label": string,
        "strengths": [
            {
                "area": string,
                "confidence_level": string (high/medium/low),
                "evidence": string,
                "count": int
            }
        ],
        "weaknesses": [
            {
                "area": string,
                "severity": string (high/medium/low),
                "evidence": string,
                "explanation": string,
                "count": int
            }
        ],
        "behavior_feedback": [
            {
                "observation": string,
                "severity": string,
                "frequency": string,
                "impact": string,
                "recommendation": string
            }
        ],
        "final_recommendation": string,
        "total_questions": int,
        "avg_correctness": float,
        "avg_clarity": float,
        "avg_confidence": float,
        "behavioral_issues_detected": int,
        "generated_at": string (ISO format)
    }
    """
    # Verify session exists and is not deleted
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.is_deleted == False,
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify user owns the session
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Verify session is completed
    if session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be completed to generate feedback. Current status: " + session.status
        )
    
    # Generate feedback
    feedback = generate_feedback_report(session_id, db)
    
    if "error" in feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=feedback["error"]
        )
    
    return feedback