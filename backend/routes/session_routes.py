"""Interview session and scoring routes."""
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy.orm import Session

from ai_modules.clarity import evaluate_clarity
from ai_modules.correctness import evaluate_correctness
from ai_modules.hierarchical import compute_overall
from ai_modules.behavioral_confidence import compute_multimodal_confidence
from ai_modules.audio_analyzer import analyze_text_hesitation
from ai_modules.audio_transcriber import (
    transcribe_audio, get_temp_audio_path, 
    MAX_AUDIO_SIZE_MB, SUPPORTED_AUDIO_FORMATS
)
from ai_modules.feedback_generator import generate_answer_feedback, generate_session_summary
from auth.jwt_handler import verify_token
from database import get_db
from models.answer import InterviewAnswer
from models.behavior_issue import BehaviorIssue
from models.behavior_metric import InterviewBehaviorMetric
from models.resume import Resume
from models.session import InterviewSession
from services.adaptive_question_service import (
    choose_next_question,
    should_complete_session,
    update_session_question_counters,
)
from services.text_normalization import normalize_question

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

SUPPORTED_UPLOAD_AUDIO_FORMATS = {".wav", ".mp3"}

MAX_ANSWER_LENGTH = 2000
MIN_ANSWER_WORDS  = 3
RESUME_RISK_THRESHOLD = 60.0

# REFINEMENT 4: Request Safety - Submission locks per session
# Prevents concurrent submissions to same session
_submission_locks = {}  # session_id -> Lock
_submission_active = {} # session_id -> bool


def get_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> int:
    return int(verify_token(credentials.credentials)["sub"])


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, float(v)))


def _perf_label(score: float) -> str:
    if score >= 85: return "Strong Candidate"
    if score >= 70: return "Good Performance"
    if score >= 50: return "Needs Improvement"
    return "Critical Improvement Needed"


def _coach_message(label: str, weakness: str) -> str:
    msgs = {
        "Strong Candidate": "Excellent work! You demonstrate strong command of the subject. Focus on polishing advanced communication skills.",
        "Good Performance": f"Good overall performance. Your main area to improve is {weakness.lower()}. Practice will close this gap quickly.",
        "Needs Improvement": f"There is clear room for growth, especially in {weakness.lower()}. Consider practicing with structured answer frameworks like STAR.",
        "Critical Improvement Needed": "Significant improvement needed across all areas. Start by reviewing fundamentals and practice daily mock interviews.",
    }
    return msgs.get(label, "Keep practicing!")


# ─── List All Sessions ─────────────────────────────────────────────────────────
@router.get("/sessions")
def list_sessions(
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """List all active (non-deleted) sessions for the user"""
    sessions = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id,
        InterviewSession.is_deleted == False
    ).order_by(InterviewSession.created_at.desc()).all()
    
    return [
        {
            "id": s.id,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "overall_score": s.overall_score,
            "performance_label": s.performance_label,
        }
        for s in sessions
    ]


# ─── Start Session ─────────────────────────────────────────────────────────────
class StartSessionRequest(BaseModel):
    resume_id: int
    total_questions: int = 10


@router.post("/start_session")
def start_session(
    body: StartSessionRequest,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    resume = db.query(Resume).filter(Resume.id == body.resume_id, Resume.user_id == user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_score = float(resume.analysis_score or 0.0)
    resume_risk_flag = resume.analysis_score is not None and resume_score < RESUME_RISK_THRESHOLD
    initial_difficulty = 1 if resume_risk_flag else 2

    session = InterviewSession(
        user_id=user_id,
        resume_id=body.resume_id,
        status="active",
        total_questions=body.total_questions,
        max_questions=body.total_questions,
        transcript="",
        current_difficulty=initial_difficulty,
        resume_risk_flag=resume_risk_flag,
        new_questions_count=0,
        reused_questions_count=0,
        last_question_was_reused=False,
        last_difficulty_change_turn=0,
    )
    db.add(session)
    db.flush()

    next_question = choose_next_question(db, session, resume)
    update_session_question_counters(session, next_question.is_reused)

    db.commit()
    db.refresh(session)
    logger.info(f"Session {session.id} started for user {user_id}")
    return {
        "session_id": session.id,
        "status": session.status,
        "resume_risk_flag": session.resume_risk_flag,
        "max_questions": session.max_questions,
        "next_question": next_question.to_api(),
    }


# ─── Submit Answer ─────────────────────────────────────────────────────────────
class SubmitAnswerRequest(BaseModel):
    session_id: int
    question: str | None = None
    question_id: str | None = None
    answer: Optional[str] = None
    question_type: str = "general"
    difficulty_level: int = 2
    topic: str = "general"
    is_reused: bool = False
    selection_reason: str = ""
    selection_context: dict = Field(default_factory=dict)
    previous_score: float | None = None
    audio_confidence: float = 0.0  # from frontend audio analysis

    @model_validator(mode="after")
    def map_question_id(self):
        # Backward-compat: accept question_id when question is not provided.
        if (not self.question or not self.question.strip()) and self.question_id:
            self.question = self.question_id
        if not self.question or not self.question.strip():
            raise ValueError("question is required")
        return self

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("Answer cannot be empty")
        if len(stripped) > MAX_ANSWER_LENGTH:
            raise ValueError(f"Answer exceeds {MAX_ANSWER_LENGTH} characters (got {len(stripped)})")
        if len(stripped.split()) < MIN_ANSWER_WORDS:
            raise ValueError(f"Answer must contain at least {MIN_ANSWER_WORDS} words")
        return stripped


@router.post("/submit_answer")
async def submit_answer(
    request: Request,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Submit answer for current interview question.
    Supports both JSON and multipart/form-data requests.
    
    Behavior:
    - If audio provided: validate size/duration, transcribe and use for evaluation
    - If only typed answer: use typed answer
    - If both provided: audio takes precedence
    - If transcription fails: fallback to typed answer (if available)
    - Transcript only updated with non-empty evaluation text
    
    Validation:
    - Audio file max 5MB (rejected before processing)
    - Audio duration max 60 seconds (validated during transcription)
    - Evaluation text must be non-empty (prevents empty transcript entries)
    
    REFINEMENT 4: Request Safety - Only one active submission per session at a time
    """
    
    lock: Optional[Lock] = None
    session_id: Optional[int] = None

    try:
        # ── Parse request payload (JSON or multipart/form-data) ─────────────────
        content_type = (request.headers.get("content-type") or "").lower()
        audio_file: Optional[UploadFile] = None

        if "application/json" in content_type:
            try:
                payload = await request.json()
                body = SubmitAnswerRequest.model_validate(payload)
            except ValidationError as e:
                raise HTTPException(status_code=422, detail=str(e))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON body")
        elif "multipart/form-data" in content_type:
            form = await request.form()
            form_audio = form.get("audio_file")
            if form_audio is not None and hasattr(form_audio, "file"):
                audio_file = form_audio

            raw_selection_context = form.get("selection_context")
            parsed_selection_context = {}
            if raw_selection_context:
                try:
                    parsed_selection_context = json.loads(str(raw_selection_context))
                except Exception:
                    parsed_selection_context = {}

            form_payload = {
                "session_id": form.get("session_id"),
                "question": form.get("question"),
                "question_id": form.get("question_id"),
                "answer": form.get("answer") or None,
                "question_type": form.get("question_type") or "general",
                "difficulty_level": form.get("difficulty_level") or 2,
                "topic": form.get("topic") or "general",
                "is_reused": str(form.get("is_reused") or "false").lower() in ("1", "true", "yes", "on"),
                "selection_reason": form.get("selection_reason") or "",
                "selection_context": parsed_selection_context,
                "previous_score": form.get("previous_score"),
                "audio_confidence": form.get("audio_confidence") or 0.0,
            }

            try:
                body = SubmitAnswerRequest.model_validate(form_payload)
            except ValidationError as e:
                raise HTTPException(status_code=422, detail=str(e))
        else:
            raise HTTPException(status_code=415, detail="Unsupported content type")

        # REFINEMENT 4: Submission Lock - Prevent concurrent submissions to same session
        session_id = body.session_id
        if session_id not in _submission_locks:
            _submission_locks[session_id] = Lock()

        lock = _submission_locks[session_id]
        if not lock.acquire(blocking=False):
            logger.warning(f"[session={session_id}] Concurrent submission attempt blocked")
            raise HTTPException(
                status_code=409,
                detail="Another submission is currently in progress for this session. Please wait."
            )

        # ── Audio Processing (if provided) ──────────────────────────────────────
        transcription_text = ""
        evaluation_text = body.answer  # Default: use typed answer
        audio_source = None  # Track: "typed", "transcribed", or None
        question_index = getattr(body, 'question_index', None)  # May not be provided
        
        if audio_file:
            temp_file_path = None
            try:
                # Pre-validation: Check file size before reading entire file
                file_size = 0
                file_size_limit = MAX_AUDIO_SIZE_MB * 1024 * 1024  # Convert MB to bytes
                
                try:
                    # Pre-validate: Check file type from filename
                    filename = audio_file.filename or ""
                    file_ext = Path(filename).suffix.lower()
                    if file_ext and file_ext not in SUPPORTED_UPLOAD_AUDIO_FORMATS:
                        logger.error(f"[session={session_id}] Unsupported audio format: {file_ext}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported audio format. Supported: {', '.join(sorted(SUPPORTED_UPLOAD_AUDIO_FORMATS))}"
                        )
                    
                    # Get file size from headers if available
                    if audio_file.size:
                        file_size = audio_file.size
                        
                        if file_size > file_size_limit:
                            logger.warning(f"[session={session_id}] Audio rejected (size): {file_size / (1024*1024):.2f}MB")
                            raise HTTPException(
                                status_code=413,
                                detail=f"Audio too large. Maximum allowed size is {MAX_AUDIO_SIZE_MB}MB."
                            )
                except HTTPException:
                    raise
                except AttributeError:
                    logger.debug(f"[session={session_id}] Content-Length not available; will validate during read")
                
                # Get unique temp file path using original extension for accurate validation/decoding
                temp_file_path = get_temp_audio_path(suffix=file_ext or ".wav")
                
                # Write uploaded audio to temp file
                contents = audio_file.file.read()
                file_size = len(contents)

                if file_size == 0:
                    logger.error(f"[session={session_id}] Empty audio payload")
                    raise HTTPException(status_code=400, detail="Audio file is empty")
                
                # Double-check after reading
                if file_size > file_size_limit:
                    logger.warning(f"[session={session_id}] Audio rejected after read: {file_size / (1024*1024):.2f}MB")
                    raise HTTPException(
                        status_code=413,
                        detail=f"Audio too large. Maximum allowed size is {MAX_AUDIO_SIZE_MB}MB."
                    )
                
                logger.info(f"[session={session_id}] Audio received: {file_size / (1024*1024):.2f}MB ({file_ext})")
                
                # Write to temp file
                with open(temp_file_path, 'wb') as tmp:
                    tmp.write(contents)

                temp_path_obj = Path(temp_file_path)
                if not temp_path_obj.exists():
                    logger.error(f"[session={session_id}] Temp audio file missing before transcription: {temp_file_path}")
                    raise HTTPException(status_code=500, detail="Audio save failed before transcription")

                disk_size = temp_path_obj.stat().st_size
                logger.info(
                    "[session=%s] Temp audio saved path=%s size_bytes=%s ext=%s",
                    session_id,
                    temp_file_path,
                    disk_size,
                    file_ext or temp_path_obj.suffix.lower(),
                )
                if disk_size == 0:
                    logger.error(f"[session={session_id}] Temp audio file is zero bytes: {temp_file_path}")
                    raise HTTPException(status_code=400, detail="Audio file has no data")

                transcribe_ext = temp_path_obj.suffix.lower()
                if transcribe_ext not in SUPPORTED_AUDIO_FORMATS:
                    logger.error(f"[session={session_id}] Temp audio extension not supported for whisper: {transcribe_ext}")
                    raise HTTPException(status_code=400, detail=f"Unsupported audio format for transcription: {transcribe_ext}")
                
                # REFINEMENT 2: Transcribe with logging context (session_id, question_index)
                logger.debug(f"[session={session_id}, q={question_index}] Starting transcription: {file_size / (1024*1024):.2f}MB")
                transcription_text, error_msg = transcribe_audio(temp_file_path)
                
                if error_msg:
                    logger.error(f"[session={session_id}] Transcription error: {error_msg}")
                    raise HTTPException(
                        status_code=422,
                        detail=f"Audio transcription failed: {error_msg}"
                    )
                else:
                    # Use transcription for evaluation
                    if transcription_text and transcription_text.strip():
                        evaluation_text = transcription_text
                        audio_source = "transcribed"
                        logger.info(f"[session={session_id}, q={question_index}] Transcription success: {len(transcription_text)} chars, {len(transcription_text.split())} words")
                    else:
                        logger.error(f"[session={session_id}] Transcription produced no text")
                        raise HTTPException(
                            status_code=422,
                            detail="Audio transcription produced no text"
                        )
            except HTTPException:
                # Re-raise HTTP exceptions (file type, size validation)
                raise
            except Exception as e:
                logger.error(f"[session={session_id}] Audio processing error: {type(e).__name__}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Audio processing failed before transcription"
                )
            
            finally:
                # Guaranteed cleanup of temp file (prevents resource leaks)
                if temp_file_path:
                    try:
                        if Path(temp_file_path).exists():
                            Path(temp_file_path).unlink()
                            logger.debug(f"[session={session_id}] Temp audio file cleaned path={temp_file_path}")
                    except Exception as e:
                        logger.warning(f"[session={session_id}] Temp cleanup error: {e}")
        else:
            audio_source = "typed"  # No audio file, use typed answer
        
        # ── Ownership + status guard ──────────────────────────────────────────────
        session = db.query(InterviewSession).filter(
            InterviewSession.id == body.session_id,
            InterviewSession.user_id == user_id,
            InterviewSession.is_deleted == False,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.status != "active":
            raise HTTPException(status_code=400, detail="Session is not active — answers can only be submitted to active sessions")
    
        # ── Duplicate question guard ──────────────────────────────────────────────
        duplicate = db.query(InterviewAnswer).filter(
            InterviewAnswer.session_id == body.session_id,
            InterviewAnswer.normalized_question == normalize_question(body.question),
        ).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="This question has already been answered in this session")
    
        # Append to transcript (using evaluation_text, not raw body.answer)
        # SAFETY: Only append if evaluation_text is non-empty
        if evaluation_text and evaluation_text.strip():
            session.transcript += f"Q: {body.question}\nA: {evaluation_text}\n\n"
            logger.debug(f"[session={session_id}] Transcript updated: Q+A ({len(evaluation_text)} chars), source={audio_source}")
        else:
            logger.error(f"[session={session_id}] CRITICAL: evaluation_text is empty after audio processing; transcript NOT appended")
            raise HTTPException(status_code=400, detail="Evaluation text is empty; cannot process answer")
    
        # ── Hybrid correctness (Groq + SBERT + keyword) ───────────────────────────
        correctness, explanation, improvement_tip, sub_scores = evaluate_correctness(
            body.question, evaluation_text
        )
    
        # ── Rule-based clarity ────────────────────────────────────────────────────
        clarity_score, clarity_explanation = evaluate_clarity(body.question, evaluation_text)
    
        # ── Multimodal confidence fusion ──────────────────────────────────────────
        # Video confidence from behavioral metrics (rolling window)
        video_conf = session.behavioral_confidence or 70.0
    
        # Audio confidence (sent from frontend after analysis)
        audio_conf = body.audio_confidence if body.audio_confidence > 0 else None
    
        # Text hesitation analysis
        hesitation = analyze_text_hesitation(evaluation_text)
        text_hesitation = hesitation.get("hesitation_score", None)
        # hesitation_score is 1.0 = no hesitation, convert to match fusion expectation
        # In fusion, text_hesitation_score is 0-1 where 0 = confident, 1 = hesitant
        text_hesitation_for_fusion = 1.0 - text_hesitation if text_hesitation is not None else None
    
        confidence = _clamp(compute_multimodal_confidence(
            video_confidence=video_conf,
            audio_confidence=audio_conf,
            text_hesitation_score=text_hesitation_for_fusion,
        ))
    
        # ── Overall weighted 50/30/20 (spec) ─────────────────────────────────────
        overall = _clamp(compute_overall(correctness, clarity_score, confidence))
    
        # ── Generate structured feedback ──────────────────────────────────────────
        feedback = generate_answer_feedback(
            correctness=correctness,
            clarity=clarity_score,
            confidence=confidence,
            overall=overall,
            correctness_explanation=explanation,
            clarity_explanation=clarity_explanation,
            improvement_tip=improvement_tip,
        )
        if session.resume_risk_flag and confidence < 85:
            feedback["coaching_tip"] = (
                "You're building momentum. Focus on fundamentals, explain step by step, "
                "and prioritize clear examples from your projects."
            )
    
        # ── Persist answer ────────────────────────────────────────────────────────
        answer_row = InterviewAnswer(
            session_id=session.id,
            resume_id=session.resume_id,
            question=body.question,
            normalized_question=normalize_question(body.question),
            question_type=body.question_type,
            difficulty_level=body.difficulty_level,
            topic=body.topic or "general",
            is_reused=body.is_reused,
            selection_reason=body.selection_reason,
            selection_context=json.dumps(body.selection_context or {}),
            previous_score=body.previous_score,
            answer=evaluation_text,
            transcription=transcription_text if transcription_text else None,  # NEW: Store transcription if audio provided
            correctness=_clamp(correctness),
            clarity=_clamp(clarity_score),
            confidence=_clamp(confidence),
            overall=_clamp(overall),
            correctness_explanation=explanation,
            clarity_explanation=clarity_explanation,
            improvement_tip=improvement_tip,
            llm_score=sub_scores.get("llm"),
            cosine_score=sub_scores.get("cosine"),
            keyword_score=sub_scores.get("keyword"),
        )
        db.add(answer_row)
        db.flush()
    
        # ── Recalculate session averages ──────────────────────────────────────────
        answers = db.query(InterviewAnswer).filter(InterviewAnswer.session_id == session.id).all()
        n = len(answers)
        avg_c  = sum(a.correctness for a in answers) / n
        avg_cl = sum(a.clarity for a in answers) / n
        avg_cf = sum(a.confidence for a in answers) / n
        avg_overall = _clamp(compute_overall(avg_c, avg_cl, avg_cf))
    
        session.correctness_score = round(avg_c, 2)
        session.clarity_score     = round(avg_cl, 2)
        session.confidence_score  = round(avg_cf, 2)
        session.overall_score     = round(avg_overall, 2)
    
        # Adaptive completion + next question.
        should_complete, reason = should_complete_session(session, answers)
    
        next_question_payload = None
        summary_payload = None
        if should_complete:
            session.status = "completed"
            session.ended_at = datetime.now(timezone.utc)
            answers_data = [
                {"overall": a.overall, "correctness": a.correctness, "clarity": a.clarity, "confidence": a.confidence}
                for a in answers
            ]
            summary = generate_session_summary(
                overall_score=avg_overall,
                correctness_score=avg_c,
                clarity_score=avg_cl,
                confidence_score=avg_cf,
                total_questions=len(answers),
                answers_data=answers_data,
            )
            session.performance_label = summary["performance_label"]
            session.coach_message = summary["coach_message"]
            summary_payload = {
                "performance_label": summary["performance_label"],
                "coach_message": summary["coach_message"],
                "strongest_area": summary["strongest_area"],
                "weakest_area": summary["weakest_area"],
                "recommendations": summary["recommendations"],
                "trend_insight": summary["trend_insight"],
            }
        else:
            resume = db.query(Resume).filter(Resume.id == session.resume_id, Resume.user_id == user_id).first()
            if not resume:
                raise HTTPException(status_code=404, detail="Resume not found for session")
    
            previous_difficulty = int(session.current_difficulty or 2)
            next_question = choose_next_question(db, session, resume)
            update_session_question_counters(session, next_question.is_reused)
            if int(session.current_difficulty or 2) != previous_difficulty:
                session.last_difficulty_change_turn = len(answers)
            next_question_payload = next_question.to_api()
    
        db.commit()
    
        logger.info(
            "turn_log session=%s turn=%s diff=%s source=%s reason=%s complete=%s",
            session.id,
            len(answers),
            body.difficulty_level,
            "reused" if body.is_reused else "new",
            body.selection_reason or "n/a",
            should_complete,
        )
    
        return {
            "transcription": transcription_text or None,  # NEW: Audio transcription result (or None if no audio)
            "current_answer": {
                "correctness": round(correctness, 2),
                "clarity": round(clarity_score, 2),
                "confidence": round(confidence, 2),
                "overall": round(overall, 2),
                "correctness_explanation": explanation,
                "clarity_explanation": clarity_explanation,
                "improvement_tip": improvement_tip,
                "sub_scores": sub_scores,
                "feedback": feedback,
            },
            "session_average": {
                "correctness": round(avg_c, 2),
                "clarity": round(avg_cl, 2),
                "confidence": round(avg_cf, 2),
                "overall": round(avg_overall, 2),
            },
            "questions_answered": n,
            "max_questions": int(session.max_questions or session.total_questions or 10),
            "session_completed": should_complete,
            "completion_reason": reason,
            "next_question": next_question_payload,
            "session_summary": summary_payload,
        }
    
    finally:
        # REFINEMENT 4: Release submission lock
        if lock and lock.locked():
            lock.release()
            logger.debug(f"[session={session_id}] Submission lock released")


# ─── End Session ───────────────────────────────────────────────────────────────
class EndSessionRequest(BaseModel):
    session_id: int


@router.get("/session/{session_id}/next_question")
def get_next_question(
    session_id: int,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
        InterviewSession.is_deleted == False,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    resume = db.query(Resume).filter(Resume.id == session.resume_id, Resume.user_id == user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found for session")

    next_question = choose_next_question(db, session, resume)
    update_session_question_counters(session, next_question.is_reused)
    db.commit()

    return {
        "session_id": session_id,
        "next_question": next_question.to_api(),
    }


@router.post("/end_session")
def end_session(
    body: EndSessionRequest,
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
    if session.status == "completed":
        return {"message": "Session already completed", "session_id": session.id}

    session.status   = "completed"
    session.ended_at = datetime.now(timezone.utc)

    # Final performance
    overall     = session.overall_score or 0.0
    correctness = session.correctness_score or 0.0
    clarity     = session.clarity_score or 0.0
    confidence  = session.confidence_score or 0.0

    # Generate comprehensive session summary
    answers = db.query(InterviewAnswer).filter(InterviewAnswer.session_id == session.id).all()
    answers_data = [
        {"overall": a.overall, "correctness": a.correctness, "clarity": a.clarity, "confidence": a.confidence}
        for a in answers
    ]

    summary = generate_session_summary(
        overall_score=overall,
        correctness_score=correctness,
        clarity_score=clarity,
        confidence_score=confidence,
        total_questions=len(answers),
        answers_data=answers_data,
    )

    session.performance_label = summary["performance_label"]
    session.coach_message     = summary["coach_message"]
    db.commit()

    logger.info(f"Session {session.id} ended — score {overall:.1f}, label: {summary['performance_label']}")

    return {
        "session_id":        session.id,
        "status":            "completed",
        "overall_score":     round(overall, 2),
        "correctness_score": round(correctness, 2),
        "clarity_score":     round(clarity, 2),
        "confidence_score":  round(confidence, 2),
        "performance_label": summary["performance_label"],
        "coach_message":     summary["coach_message"],
        "strongest_area":    summary["strongest_area"],
        "weakest_area":      summary["weakest_area"],
        "recommendations":   summary["recommendations"],
        "trend_insight":     summary["trend_insight"],
        "ended_at":          session.ended_at.isoformat(),
    }


# ─── Analytics Summary ─────────────────────────────────────────────────────────
@router.get("/analytics/summary")
def analytics_summary(
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
    resume_id: int | None = None,
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

    query = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id,
        InterviewSession.is_deleted == False,
        InterviewSession.status == "completed",
    )
    if selected_resume_id is not None:
        query = query.filter(InterviewSession.resume_id == selected_resume_id)

    sessions = query.order_by(InterviewSession.created_at.asc()).all()
    if not sessions:
        return {
            "total_sessions": 0, "average_overall": 0, "best_session": 0,
            "improvement_rate": 0, "performance_label": "No Data",
            "primary_weakness": "N/A", "coach_message": "Complete your first interview to see analytics.",
        }

    valid = [s for s in sessions if s.overall_score is not None]
    if not valid:
        return {"total_sessions": len(sessions), "average_overall": 0, "best_session": 0,
                "improvement_rate": 0, "performance_label": "No Data", "primary_weakness": "N/A",
                "coach_message": "No scored sessions yet."}

    avg_overall = sum(s.overall_score for s in valid) / len(valid)
    best        = max(s.overall_score for s in valid)
    improvement = valid[-1].overall_score - valid[0].overall_score if len(valid) >= 2 else 0

    avg_c  = sum(s.correctness_score or 0 for s in valid) / len(valid)
    avg_cl = sum(s.clarity_score or 0 for s in valid) / len(valid)
    avg_cf = sum(s.confidence_score or 0 for s in valid) / len(valid)
    scores   = {"Correctness": avg_c, "Clarity": avg_cl, "Confidence": avg_cf}
    weakness = min(scores, key=scores.get)
    label    = _perf_label(avg_overall)

    return {
        "selected_resume_id": selected_resume_id,
        "total_sessions":    len(sessions),
        "average_overall":   round(avg_overall, 2),
        "best_session":      round(best, 2),
        "improvement_rate":  round(improvement, 2),
        "performance_label": label,
        "primary_weakness":  weakness,
        "coach_message":     _coach_message(label, weakness),
    }


# ─── Delete Session ───────────────────────────────────────────────────────────
@router.delete("/session/{session_id}")
def delete_session(
    session_id: int,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Soft delete an interview session (mark as deleted without removing data).
    
    OWNERSHIP VALIDATION:
    - Only the session owner (by user_id) can delete
    - Returns 404 if session not found or user_id doesn't match
    
    SOFT DELETE IMPLEMENTATION:
    - Sets is_deleted = True and deleted_at = current timestamp
    - Preserves all data for audit trail and recovery
    - Client won't see deleted sessions by default
    
    CONCURRENCY SAFETY:
    - Prevents deletion while session is actively being submitted to
    - Returns 409 Conflict if concurrent submission detected
    
    RECOVERY:
    - Use POST /session/{id}/restore to undo deletion
    
    Response Format:
    - 200 OK: {"message": "...", "session_id": id, "deleted_at": timestamp}
    - 404 Not Found: Session not found or user doesn't own session
    - 400 Bad Request: Session is active (must end or abandon first)
    - 409 Conflict: Submission currently in progress (concurrent submission)
    - 500 Internal Server Error: Database error (automatic rollback)
    """
    
    # ─ CONCURRENCY SAFETY - Check for active submission ──────────────────────
    if session_id in _submission_locks:
        lock = _submission_locks[session_id]
        if not lock.acquire(blocking=False):
            logger.warning(
                f"[CONCURRENCY] Delete blocked: submission in progress "
                f"(session={session_id}, user={user_id}, timestamp={datetime.now(timezone.utc).isoformat()})"
            )
            raise HTTPException(
                status_code=409,
                detail="Cannot delete session: answer submission in progress. Please wait."
            )
        lock.release()
    
    # ─ OWNERSHIP + EXISTENCE CHECK ────────────────────────────────────────────
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()
    
    if not session:
        logger.warning(
            f"[SESSION] Delete failed: not found or unauthorized "
            f"(session={session_id}, user={user_id}, timestamp={datetime.now(timezone.utc).isoformat()})"
        )
        raise HTTPException(status_code=404, detail="Session not found")
    
    # ─ ACTIVE SESSION GUARD ──────────────────────────────────────────────────
    if session.status == "active":
        logger.warning(
            f"[SESSION] Delete blocked: session is active "
            f"(session={session_id}, user={user_id}, timestamp={datetime.now(timezone.utc).isoformat()})"
        )
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an active session. End or abandon the session first."
        )
    
    # ─ PERFORM SOFT DELETE ───────────────────────────────────────────────────
    try:
        now_utc = datetime.now(timezone.utc)
        session.is_deleted = True
        session.deleted_at = now_utc
        db.commit()
        
        timestamp_iso = now_utc.isoformat()
        logger.info(
            f"[SUCCESS] Session soft deleted | "
            f"session={session_id} | user={user_id} | timestamp={timestamp_iso}"
        )
        
        return {
            "message": "Session deleted successfully",
            "session_id": session_id,
            "deleted_at": timestamp_iso,
            "recovery_note": "This session can be restored using POST /session/{id}/restore"
        }
    
    except Exception as e:
        db.rollback()
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        logger.error(
            f"[ERROR] Session deletion failed | "
            f"session={session_id} | user={user_id} | timestamp={timestamp_iso} | "
            f"error={type(e).__name__}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to delete session. Please try again."
        )


# ─── Restore Deleted Session ──────────────────────────────────────────────────
@router.post("/session/{session_id}/restore")
def restore_session(
    session_id: int,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Restore a soft-deleted interview session.
    
    OWNERSHIP VALIDATION:
    - Only the session owner can restore their sessions
    
    RESTORATION:
    - Sets is_deleted = False and deleted_at = null
    - Session becomes visible in dashboard again
    
    Response Format:
    - 200 OK: {"message": "Session restored", "session_id": id, "restored_at": timestamp}
    - 404 Not Found: Session not found or not owned by user
    - 400 Bad Request: Session is not deleted (already active)
    """
    
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.is_deleted:
        raise HTTPException(
            status_code=400,
            detail="Session is not deleted"
        )
    
    try:
        now_utc = datetime.now(timezone.utc)
        session.is_deleted = False
        session.deleted_at = None
        db.commit()
        
        timestamp_iso = now_utc.isoformat()
        logger.info(
            f"[SUCCESS] Session restored | "
            f"session={session_id} | user={user_id} | timestamp={timestamp_iso}"
        )
        
        return {
            "message": "Session restored successfully",
            "session_id": session_id,
            "restored_at": timestamp_iso
        }
    
    except Exception as e:
        db.rollback()
        logger.error(
            f"[ERROR] Session restoration failed | "
            f"session={session_id} | user={user_id} | error={type(e).__name__}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to restore session. Please try again."
        )


# ─── Get Deleted Sessions (Recycle Bin) ────────────────────────────────────────
@router.get("/sessions/deleted")
def get_deleted_sessions(
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Retrieve all soft-deleted sessions for the current user (recycle bin).
    
    Response contains:
    - session_id
    - resume_id
    - deleted_at: Timestamp when session was deleted
    - overall_score: Final score before deletion
    - created_at: When session was created
    - job_role: Job role from associated resume
    
    Useful for:
    - Reviewing deleted sessions
    - Permanent deletion of old deleted sessions
    - Recovery if user accidentally deleted something
    """
    
    deleted_sessions = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id,
        InterviewSession.is_deleted == True
    ).order_by(InterviewSession.deleted_at.desc()).all()
    
    result = []
    for session in deleted_sessions:
        resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
        result.append({
            "session_id": session.id,
            "resume_id": session.resume_id,
            "job_role": resume.job_role if resume else "Unknown",
            "overall_score": round(session.overall_score, 2) if session.overall_score else None,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "deleted_at": session.deleted_at.isoformat() if session.deleted_at else None,
            "can_restore": True
        })
    
    return {
        "deleted_sessions_count": len(result),
        "deleted_sessions": result
    }
