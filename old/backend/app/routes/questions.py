"""Questions route - refactored to use database"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.repositories.question_repository import QuestionRepository
from app.repositories.story_repository import StoryRepository
from app.db.session import get_db
from app.utils.logger import setup_logger

# Set up logging
logger = setup_logger("questions")

router = APIRouter()

@router.get("/questions/{question_id}")
async def get_question(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get question details by ID"""
    logger.info(f"Get question request - ID: {question_id}")
    
    question = QuestionRepository.get_by_id(db, question_id)
    if not question:
        logger.warning(f"Question not found: {question_id}")
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Get analysis if exists (using relationship)
    analysis = None
    # Query analysis separately since relationship might not be loaded
    from app.db.models import QuestionAnalysis
    question_analysis = db.query(QuestionAnalysis).filter(
        QuestionAnalysis.question_id == question_id
    ).first()
    
    if question_analysis:
        analysis = {
            "question_type": question_analysis.question_type,
            "subject": question_analysis.subject,
            "difficulty": question_analysis.difficulty,
            "key_concepts": question_analysis.key_concepts,
            "intent": question_analysis.intent
        }
    
    # Get story if exists
    story = None
    latest_story = StoryRepository.get_by_question_id(db, question_id)
    if latest_story:
        story = {
            "story_title": latest_story.story_title,
            "story_context": latest_story.story_context,
            "question_flow": latest_story.question_flow
        }
    
    logger.debug(f"Question retrieved - Has analysis: {analysis is not None}, Has story: {story is not None}")
    
    response = {
        "id": question.id,
        "text": question.text,
        "options": question.options,
    }
    
    if analysis:
        response["analysis"] = analysis
    if story:
        response["story"] = story
    
    return response
