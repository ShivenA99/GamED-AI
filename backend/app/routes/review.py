"""Human Review API Routes"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging
import asyncio

from app.db.database import get_db
from app.db.models import HumanReview, Process

logger = logging.getLogger("gamed_ai.routes.review")
router = APIRouter()

# WebSocket connections for real-time notifications
connected_reviewers: List[WebSocket] = []


@router.get("/review/pending")
async def get_pending_reviews(
    db: Session = Depends(get_db)
):
    """Get all pending human reviews"""
    reviews = db.query(HumanReview).filter(
        HumanReview.status == "pending"
    ).order_by(HumanReview.created_at).all()

    return {
        "reviews": [
            {
                "id": r.id,
                "process_id": r.process_id,
                "review_type": r.review_type,
                "artifact_type": r.artifact_type,
                "artifact_preview": _get_preview(r.artifact_data),
                "reason": r.reason,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reviews
        ],
        "total": len(reviews)
    }


@router.get("/review/{review_id}")
async def get_review(
    review_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific review with full artifact data"""
    review = db.query(HumanReview).filter(HumanReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return {
        "id": review.id,
        "process_id": review.process_id,
        "review_type": review.review_type,
        "artifact_type": review.artifact_type,
        "artifact_data": review.artifact_data,
        "reason": review.reason,
        "status": review.status,
        "reviewer_feedback": review.reviewer_feedback,
        "modified_data": review.modified_data,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None
    }


@router.post("/review/{review_id}/approve")
async def approve_review(
    review_id: str,
    feedback: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Approve a pending review"""
    review = db.query(HumanReview).filter(HumanReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Review is already {review.status}"
        )

    review.status = "approved"
    review.reviewer_feedback = feedback
    review.reviewed_at = datetime.utcnow()
    db.commit()

    # Update the associated process
    process = db.query(Process).filter(Process.id == review.process_id).first()
    if process and process.status == "human_review":
        process.status = "processing"
        db.commit()

    # Notify connected WebSocket clients
    await notify_review_update(review_id, "approved")

    logger.info(f"Review {review_id} approved")

    return {
        "status": "approved",
        "review_id": review_id,
        "message": "Review approved, generation will resume"
    }


@router.post("/review/{review_id}/reject")
async def reject_review(
    review_id: str,
    feedback: str,
    db: Session = Depends(get_db)
):
    """Reject a pending review"""
    if not feedback:
        raise HTTPException(
            status_code=400,
            detail="Feedback is required when rejecting a review"
        )

    review = db.query(HumanReview).filter(HumanReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Review is already {review.status}"
        )

    review.status = "rejected"
    review.reviewer_feedback = feedback
    review.reviewed_at = datetime.utcnow()
    db.commit()

    # Update the associated process to error
    process = db.query(Process).filter(Process.id == review.process_id).first()
    if process:
        process.status = "error"
        process.error_message = f"Review rejected: {feedback}"
        db.commit()

    await notify_review_update(review_id, "rejected")

    logger.info(f"Review {review_id} rejected")

    return {
        "status": "rejected",
        "review_id": review_id,
        "message": "Review rejected"
    }


@router.post("/review/{review_id}/modify")
async def modify_and_approve_review(
    review_id: str,
    modified_data: dict,
    feedback: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Modify artifact data and approve review"""
    review = db.query(HumanReview).filter(HumanReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Review is already {review.status}"
        )

    review.status = "modified"
    review.modified_data = modified_data
    review.reviewer_feedback = feedback
    review.reviewed_at = datetime.utcnow()
    db.commit()

    # Update the associated process
    process = db.query(Process).filter(Process.id == review.process_id).first()
    if process and process.status == "human_review":
        process.status = "processing"
        db.commit()

    await notify_review_update(review_id, "modified")

    logger.info(f"Review {review_id} modified and approved")

    return {
        "status": "modified",
        "review_id": review_id,
        "message": "Review modified and approved, generation will resume with changes"
    }


@router.websocket("/review/ws")
async def review_websocket(websocket: WebSocket):
    """WebSocket for real-time review notifications"""
    await websocket.accept()
    connected_reviewers.append(websocket)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text(f"received: {data}")
    except WebSocketDisconnect:
        connected_reviewers.remove(websocket)
        logger.info("WebSocket client disconnected")


async def notify_review_update(review_id: str, status: str):
    """Notify all connected clients of review status change"""
    message = {"type": "review_update", "review_id": review_id, "status": status}

    disconnected = []
    for ws in connected_reviewers:
        try:
            await ws.send_json(message)
        except (ConnectionError, RuntimeError, Exception) as e:
            logger.debug(f"WebSocket send failed, marking for disconnect: {e}")
            disconnected.append(ws)

    for ws in disconnected:
        connected_reviewers.remove(ws)


async def notify_new_review(review: HumanReview):
    """Notify all connected clients of new review"""
    message = {
        "type": "new_review",
        "review": {
            "id": review.id,
            "process_id": review.process_id,
            "review_type": review.review_type,
            "artifact_type": review.artifact_type
        }
    }

    disconnected = []
    for ws in connected_reviewers:
        try:
            await ws.send_json(message)
        except (ConnectionError, RuntimeError, Exception) as e:
            logger.debug(f"WebSocket send failed for new review notification: {e}")
            disconnected.append(ws)

    for ws in disconnected:
        connected_reviewers.remove(ws)


def _get_preview(artifact_data: dict) -> str:
    """Get a short preview of artifact data"""
    if not artifact_data:
        return "No data"

    artifact_type = artifact_data.get("type", "unknown")

    if artifact_type == "template_selection":
        return f"Template: {artifact_data.get('template_type', 'unknown')} (confidence: {artifact_data.get('confidence', 0):.2f})"
    elif artifact_type == "blueprint":
        return f"Blueprint for {artifact_data.get('templateType', 'unknown')}"
    elif artifact_type == "code":
        code = artifact_data.get("code", "")
        return f"Code: {len(code)} characters"
    else:
        return f"{artifact_type}: {str(artifact_data)[:100]}..."
