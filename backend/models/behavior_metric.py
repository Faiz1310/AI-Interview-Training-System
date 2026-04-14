from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from models.session import InterviewSession


class InterviewBehaviorMetric(Base):
    __tablename__ = "interview_behavior_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # All values 0.0 - 1.0 (normalized)
    eye_contact_score = Column(Float, nullable=False)
    head_stability_score = Column(Float, nullable=False)
    blink_rate = Column(Float, nullable=False)        # blinks per minute
    facial_stress_index = Column(Float, nullable=False)
    
    # Audio behavioral features (0.0 - 1.0)
    speech_rate_stability = Column(Float, nullable=True, default=0.5)
    pause_hesitation = Column(Float, nullable=True, default=0.5)  # Lower is better (less hesitation)
    pitch_variation = Column(Float, nullable=True, default=0.5)   # Higher is better (more expressive)
    vocal_energy = Column(Float, nullable=True, default=0.5)      # Higher is better (more confident)
    
    # Composite behavior scores (0-100)
    attention_score = Column(Float, nullable=True)        # Eye contact + head stability
    presence_score = Column(Float, nullable=True)         # Head stability + facial composure
    vocal_confidence_score = Column(Float, nullable=True) # Speech rate + energy + pitch
    overall_behavior_score = Column(Float, nullable=True) # Composite of all behaviors (0-100)
    
    # Issues detected
    looking_away_count = Column(Integer, nullable=True, default=0)
    multiple_faces_detected = Column(Integer, nullable=True, default=0)
    face_absent_count = Column(Integer, nullable=True, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship(InterviewSession, back_populates="behavior_metrics")
