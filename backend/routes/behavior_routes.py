"""Behavioral metrics routes — video + audio."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from ai_modules.behavioral_confidence import (
    compute_behavioral_confidence,
    compute_multimodal_confidence,
    get_nudge,
    get_supportive_feedback,
)
from auth.jwt_handler import verify_token
from database import get_db
from models.behavior_metric import InterviewBehaviorMetric
from models.session import InterviewSession

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
WINDOW_SECONDS = 5


def get_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> int:
    return int(verify_token(credentials.credentials)["sub"])


def _clamp01(v: float) -> float:
    """Clamp value to [0.0, 1.0]."""
    return max(0.0, min(1.0, float(v)))


class SubmitBehaviorRequest(BaseModel):
    session_id: int
    eye_contact_score: float     # 0-1
    head_stability_score: float  # 0-1
    blink_rate: float            # blinks per minute
    facial_stress_index: float   # 0-1

    @field_validator("eye_contact_score", "head_stability_score", "facial_stress_index")
    @classmethod
    def clamp_zero_one(cls, v: float) -> float:
        return _clamp01(v)

    @field_validator("blink_rate")
    @classmethod
    def clamp_blink(cls, v: float) -> float:
        return max(0.0, float(v))


@router.post("/submit_behavior_metrics")
def submit_behavior_metrics(
    body: SubmitBehaviorRequest,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == body.session_id,
        InterviewSession.user_id == user_id,
        InterviewSession.is_deleted == False,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    metric = InterviewBehaviorMetric(
        session_id=body.session_id,
        eye_contact_score=body.eye_contact_score,
        head_stability_score=body.head_stability_score,
        blink_rate=body.blink_rate,
        facial_stress_index=body.facial_stress_index,
    )
    db.add(metric)
    db.flush()

    # Rolling window average
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=WINDOW_SECONDS)
    recent = (
        db.query(InterviewBehaviorMetric)
        .filter(
            InterviewBehaviorMetric.session_id == body.session_id,
            InterviewBehaviorMetric.created_at >= cutoff,
        )
        .all()
    )

    n          = max(len(recent), 1)
    avg_eye    = sum(m.eye_contact_score for m in recent) / n
    avg_head   = sum(m.head_stability_score for m in recent) / n
    avg_blink  = sum(m.blink_rate for m in recent) / n
    avg_stress = sum(m.facial_stress_index for m in recent) / n

    window_sec = WINDOW_SECONDS
    if len(recent) > 1 and recent[-1].created_at and recent[0].created_at:
        window_sec = (recent[-1].created_at - recent[0].created_at).total_seconds()

    confidence = compute_behavioral_confidence(avg_eye, avg_head, avg_blink, avg_stress)
    nudge      = get_nudge(avg_eye, avg_head, avg_blink, window_sec)
    supportive = get_supportive_feedback(confidence, avg_stress)

    session.behavioral_confidence = confidence
    db.commit()

    return {
        "behavioral_confidence": confidence,
        "nudge": nudge,
        "supportive_feedback": supportive,
        "window_metrics": {
            "avg_eye_contact":    round(avg_eye, 3),
            "avg_head_stability": round(avg_head, 3),
            "avg_blink_rate":     round(avg_blink, 2),
            "avg_stress_index":   round(avg_stress, 3),
        },
    }


# ─── Audio Analysis Endpoint ─────────────────────────────────────────────────
@router.post("/analyze_audio")
async def analyze_audio(
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
    audio_file: UploadFile = File(...),
    session_id: int = Form(...),
):
    """
    Receive audio recording and extract behavioral features.
    Returns audio confidence and features for multimodal fusion.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
        InterviewSession.is_deleted == False,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    try:
        audio_bytes = await audio_file.read()
        if len(audio_bytes) < 1000:
            return {
                "audio_confidence": 50.0,
                "audio_features": {
                    "speech_rate": 0.5,
                    "pause_duration": 0.5,
                    "pitch_variation": 0.5,
                    "energy_variation": 0.5,
                },
                "message": "Audio too short for analysis",
            }

        from ai_modules.audio_analyzer import analyze_audio_features, compute_audio_confidence

        features = analyze_audio_features(audio_bytes)
        audio_conf = compute_audio_confidence(features)

        return {
            "audio_confidence": audio_conf,
            "audio_features": features,
        }

    except Exception as e:
        logger.error(f"[AudioAnalysis] Failed: {e}")
        return {
            "audio_confidence": 50.0,
            "audio_features": {},
            "error": str(e),
        }
