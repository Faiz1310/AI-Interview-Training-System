from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    normalized_question = Column(Text, nullable=True, index=True)
    question_type = Column(String(50), nullable=True)  # skill_alignment | gap_based | project_based
    difficulty_level = Column(Integer, nullable=True)
    topic = Column(String(100), nullable=True)
    is_reused = Column(Boolean, nullable=False, default=False)
    selection_reason = Column(String(200), nullable=True)
    selection_context = Column(Text, nullable=True)
    previous_score = Column(Float, nullable=True)
    answer = Column(Text, nullable=False)
    
    # Transcription from speech-to-text (Whisper) if audio provided
    # Nullable for backward compatibility: typed answers have null transcription
    transcription = Column(Text, nullable=True)

    # Scores (0-100)
    correctness = Column(Float, nullable=False)
    clarity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    overall = Column(Float, nullable=False)

    # LLM-generated explanations (stored, not discarded)
    correctness_explanation = Column(Text, nullable=True)
    clarity_explanation = Column(Text, nullable=True)
    improvement_tip = Column(Text, nullable=True)

    # Sub-scores for transparency
    llm_score = Column(Float, nullable=True)
    cosine_score = Column(Float, nullable=True)
    keyword_score = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="answers")
