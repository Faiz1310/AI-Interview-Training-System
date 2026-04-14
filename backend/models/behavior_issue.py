"""
Behavior Issue tracking model.

Records behavioral violations detected during interview with question context.
Stores which question had which behavioral issue for post-interview analysis.

STRICT SCHEMA:
- id: primary key
- session_id: FK to InterviewSession (CASCADE delete, INDEXED)
- question_index: which question (0-indexed)
- issue: type of violation ("face_not_present" | "looking_away" | "multiple_faces")
- severity: severity level ("low" | "medium" | "high") - ENUM enforced
- created_at: timestamp (auto UTC)
"""
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class IssueSeverity(str, enum.Enum):
    """Strictl y enforced severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IssueType(str, enum.Enum):
    """Strictly enforced issue type values."""
    FACE_NOT_PRESENT = "face_not_present"
    LOOKING_AWAY = "looking_away"
    MULTIPLE_FACES = "multiple_faces"


class BehaviorIssue(Base):
    __tablename__ = "behavior_issues"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Session context (INDEXED for fast retrieval)
    session_id = Column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Question context: which question was being answered when issue occurred (0-indexed)
    question_index = Column(Integer, nullable=False)

    # Issue type (STRICTLY ENFORCED to one of 3 values)
    issue = Column(
        SQLEnum(IssueType, native_enum=False),
        nullable=False,
        index=True,
    )

    # Severity level (STRICTLY ENFORCED to one of 3 values)
    severity = Column(
        SQLEnum(IssueSeverity, native_enum=False),
        nullable=False,
        default=IssueSeverity.MEDIUM,
    )

    # Timestamp (auto-generated UTC)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to session
    session = relationship("InterviewSession", back_populates="behavior_issues")
