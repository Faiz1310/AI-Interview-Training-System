"""Question generation routes."""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai_modules.rag import chunk_text, create_faiss_index, generate_questions, index_exists
from auth.jwt_handler import verify_token
from database import get_db
from models.resume import Resume

router = APIRouter()
security = HTTPBearer()

VECTOR_STORE_DIR = Path(__file__).resolve().parent.parent / "vector_store"


def get_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> int:
    return int(verify_token(credentials.credentials)["sub"])


class GenerateQuestionsRequest(BaseModel):
    resume_id: int
    difficulty_level: int = 2
    limit: int = 10


@router.post("/generate_questions")
def generate_questions_route(
    body: GenerateQuestionsRequest,
    user_id: Annotated[int, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    resume = db.query(Resume).filter(
        Resume.id == body.resume_id,
        Resume.user_id == user_id,
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    combined_text = f"{resume.resume_text}\n\n{resume.jd_text}"

    # Build FAISS index if not exists
    if not index_exists(body.resume_id):
        chunks = chunk_text(combined_text)
        if chunks:
            VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
            create_faiss_index(body.resume_id, chunks)

    questions = generate_questions(
        body.resume_id,
        resume.job_role,
        difficulty_level=max(1, min(3, body.difficulty_level)),
        limit=max(1, min(20, body.limit)),
    )

    return {
        "resume_id": body.resume_id,
        "job_role": resume.job_role,
        "total": len(questions),
        "questions": questions,  # list of {question: str, type: str}
    }
