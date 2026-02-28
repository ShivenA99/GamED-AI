"""Learning Session API Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging
import uuid

from app.db.database import get_db
from app.db.models import LearningSession, AttemptRecord, Visualization

logger = logging.getLogger("gamed_ai.routes.sessions")
router = APIRouter()


@router.post("/sessions")
async def create_session(
    visualization_id: str,
    question_id: str,
    user_identifier: Optional[str] = None,
    total_questions: int = 1,
    db: Session = Depends(get_db)
):
    """Create a new learning session"""
    # Verify visualization exists
    visualization = db.query(Visualization).filter(
        Visualization.id == visualization_id
    ).first()
    if not visualization:
        raise HTTPException(status_code=404, detail="Visualization not found")

    session = LearningSession(
        id=str(uuid.uuid4()),
        question_id=question_id,
        visualization_id=visualization_id,
        user_identifier=user_identifier,
        total_questions=total_questions,
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"Created session {session.id} for visualization {visualization_id}")

    return {
        "session_id": session.id,
        "visualization_id": visualization_id,
        "status": "active"
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get session details with all attempts"""
    session = db.query(LearningSession).filter(
        LearningSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    attempts = db.query(AttemptRecord).filter(
        AttemptRecord.session_id == session_id
    ).order_by(AttemptRecord.created_at).all()

    return {
        "id": session.id,
        "visualization_id": session.visualization_id,
        "question_id": session.question_id,
        "user_identifier": session.user_identifier,
        "status": session.status,
        "time": {
            "session_start": session.session_start.isoformat() if session.session_start else None,
            "session_end": session.session_end.isoformat() if session.session_end else None,
            "total_seconds": session.total_time_seconds,
            "active_seconds": session.active_time_seconds
        },
        "progress": {
            "current_question": session.current_question_index,
            "total_questions": session.total_questions,
            "hints_used": session.hints_used
        },
        "score": {
            "accuracy": session.score_accuracy,
            "efficiency": session.score_efficiency,
            "mastery": session.score_mastery,
            "raw": session.raw_score,
            "max": session.max_score
        },
        "analytics": {
            "blooms_level": session.blooms_level_achieved,
            "concepts_mastered": session.concepts_mastered,
            "concepts_struggling": session.concepts_struggling
        },
        "attempts": [
            {
                "question_index": a.question_index,
                "attempt_number": a.attempt_number,
                "selected_answer": a.selected_answer,
                "is_correct": a.is_correct,
                "time_taken_seconds": a.time_taken_seconds,
                "hints_viewed": a.hints_viewed,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in attempts
        ]
    }


@router.post("/sessions/{session_id}/attempts")
async def record_attempts(
    session_id: str,
    attempts: List[dict],
    score: Optional[dict] = None,
    total_active_time: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Record one or more attempts for a session"""
    session = db.query(LearningSession).filter(
        LearningSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Record each attempt
    for attempt_data in attempts:
        attempt = AttemptRecord(
            id=str(uuid.uuid4()),
            session_id=session_id,
            question_index=attempt_data.get("questionIndex", 0),
            attempt_number=attempt_data.get("attemptNumber", 1),
            selected_answer=attempt_data.get("selectedAnswer", ""),
            is_correct=attempt_data.get("isCorrect", False),
            time_taken_seconds=attempt_data.get("timeTakenSeconds", 0),
            hints_viewed=attempt_data.get("hintsViewed", 0),
            feedback_shown=attempt_data.get("feedbackShown")
        )
        db.add(attempt)

    # Update session scores if provided
    if score:
        session.score_accuracy = score.get("accuracy", session.score_accuracy)
        session.score_efficiency = score.get("efficiency", session.score_efficiency)
        session.score_mastery = score.get("mastery", session.score_mastery)
        session.raw_score = score.get("raw", session.raw_score)
        session.max_score = score.get("max", session.max_score)

    if total_active_time:
        session.active_time_seconds = total_active_time

    session.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Recorded {len(attempts)} attempts for session {session_id}")

    return {
        "status": "recorded",
        "attempts_count": len(attempts)
    }


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    total_active_time: Optional[int] = None,
    final_score: Optional[dict] = None,
    blooms_assessment: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """End a learning session with final analytics"""
    session = db.query(LearningSession).filter(
        LearningSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "completed"
    session.session_end = datetime.utcnow()

    if total_active_time:
        session.active_time_seconds = total_active_time
        session.total_time_seconds = int(
            (session.session_end - session.session_start).total_seconds()
        )

    if final_score:
        session.score_accuracy = final_score.get("accuracy", session.score_accuracy)
        session.score_efficiency = final_score.get("efficiency", session.score_efficiency)
        session.score_mastery = final_score.get("mastery", session.score_mastery)
        session.raw_score = final_score.get("raw", session.raw_score)
        session.max_score = final_score.get("max", session.max_score)

    if blooms_assessment:
        session.blooms_level_achieved = blooms_assessment.get("level")
        session.concepts_mastered = blooms_assessment.get("conceptsMastered")
        session.concepts_struggling = blooms_assessment.get("conceptsStruggling")

    db.commit()

    logger.info(f"Session {session_id} ended with score {session.raw_score}/{session.max_score}")

    return {
        "status": "completed",
        "session_id": session_id,
        "final_score": {
            "accuracy": session.score_accuracy,
            "efficiency": session.score_efficiency,
            "mastery": session.score_mastery,
            "raw": session.raw_score,
            "max": session.max_score
        },
        "blooms_level": session.blooms_level_achieved
    }


@router.get("/sessions/user/{user_identifier}")
async def get_user_sessions(
    user_identifier: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get all sessions for a user"""
    sessions = db.query(LearningSession).filter(
        LearningSession.user_identifier == user_identifier
    ).order_by(LearningSession.created_at.desc()).limit(limit).all()

    return {
        "user_identifier": user_identifier,
        "sessions": [
            {
                "id": s.id,
                "visualization_id": s.visualization_id,
                "status": s.status,
                "score_accuracy": s.score_accuracy,
                "score_mastery": s.score_mastery,
                "blooms_level": s.blooms_level_achieved,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in sessions
        ],
        "total": len(sessions)
    }
