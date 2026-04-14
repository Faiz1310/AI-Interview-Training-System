from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Core content
    resume_text = Column(Text, nullable=False)
    jd_text = Column(Text, nullable=False)
    job_role = Column(String(255), nullable=False)
    filename = Column(String(500), nullable=True)

    # AI Analysis results (populated by /analyze_resume)
    analysis_score = Column(Float, nullable=True)
    analysis_model_used = Column(String(20), nullable=True)
    strengths = Column(Text, nullable=True)       # JSON array stored as text
    weaknesses = Column(Text, nullable=True)      # JSON array stored as text
    suggestions = Column(Text, nullable=True)     # JSON array stored as text
    improvement_tags = Column(Text, nullable=True)  # JSON array stored as text
    analysis_summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
