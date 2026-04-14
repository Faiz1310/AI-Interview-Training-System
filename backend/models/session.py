from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status: "active" | "completed"
    status = Column(String(20), nullable=False, default="active")

    transcript = Column(Text, nullable=False, default="")
    total_questions = Column(Integer, nullable=True)
    max_questions = Column(Integer, nullable=False, default=10)

    # Adaptive interview state
    current_difficulty = Column(Integer, nullable=False, default=2)
    new_questions_count = Column(Integer, nullable=False, default=0)
    reused_questions_count = Column(Integer, nullable=False, default=0)
    last_question_was_reused = Column(Boolean, nullable=False, default=False)
    resume_risk_flag = Column(Boolean, nullable=False, default=False)
    last_difficulty_change_turn = Column(Integer, nullable=False, default=0)

    # Aggregate scores (0-100)
    correctness_score = Column(Float, nullable=True)
    clarity_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    behavioral_confidence = Column(Float, nullable=True)

    # Coach feedback
    performance_label = Column(String(100), nullable=True)
    coach_message = Column(Text, nullable=True)

    # Soft delete tracking
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    answers = relationship(
        "InterviewAnswer",
        back_populates="session",
        cascade="all, delete",
    )
    behavior_metrics = relationship(
        "InterviewBehaviorMetric",
        back_populates="session",
        cascade="all, delete",
    )
    behavior_issues = relationship(
        "BehaviorIssue",
        back_populates="session",
        cascade="all, delete",
        lazy="select",
    )
