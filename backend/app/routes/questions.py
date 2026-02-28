"""Question API Routes"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import logging
import uuid

from app.db.database import get_db
from app.db.models import Question

logger = logging.getLogger("gamed_ai.routes.questions")
router = APIRouter()


@router.post("/questions/upload")
async def upload_question(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document and extract question"""
    # TODO: Implement document parsing (reuse from old codebase)
    content = await file.read()

    # For now, treat content as plain text
    question_text = content.decode("utf-8", errors="ignore")

    question = Question(
        id=str(uuid.uuid4()),
        text=question_text,
        source_file=file.filename
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "question_id": question.id,
        "text": question.text[:200] + "..." if len(question.text) > 200 else question.text,
        "source_file": question.source_file
    }


@router.get("/questions/{question_id}")
async def get_question(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get question by ID"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "id": question.id,
        "text": question.text,
        "options": question.options,
        "source_file": question.source_file,
        "created_at": question.created_at.isoformat() if question.created_at else None
    }


@router.get("/questions")
async def list_questions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all questions"""
    questions = db.query(Question).order_by(Question.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "questions": [
            {
                "id": q.id,
                "text": q.text[:100] + "..." if len(q.text) > 100 else q.text,
                "options": q.options,
                "created_at": q.created_at.isoformat() if q.created_at else None
            }
            for q in questions
        ],
        "total": db.query(Question).count()
    }
