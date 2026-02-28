"""Analyze route - refactored to use database"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.pipeline.layer2_classification import ClassificationOrchestrator
from app.repositories.question_repository import QuestionRepository
from app.db.session import get_db
from app.utils.logger import setup_logger

# Set up logging
logger = setup_logger("analyze")

router = APIRouter()

@router.post("/analyze/{question_id}")
async def analyze_question(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Analyze question and select appropriate prompt template"""
    logger.info(f"[API] /analyze/{question_id} - Request received")
    
    question = QuestionRepository.get_by_id(db, question_id)
    if not question:
        logger.error(f"[API] Question {question_id} not found")
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        # Use classification orchestrator
        classifier = ClassificationOrchestrator()
        result = classifier.analyze_question(question.text, question.options)
        analysis_data = result["data"]
        
        # Store analysis in database
        from app.db.models import QuestionAnalysis
        analysis = QuestionAnalysis(
            question_id=question_id,
            question_type=analysis_data["question_type"],
            subject=analysis_data["subject"],
            difficulty=analysis_data["difficulty"],
            key_concepts=analysis_data.get("key_concepts", []),
            intent=analysis_data.get("intent", "")
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        logger.info(f"[API] Analysis stored successfully for question_id={question_id}")
        return {
            "question_id": question_id,
            "analysis": {
                "question_type": analysis.question_type,
                "subject": analysis.subject,
                "difficulty": analysis.difficulty,
                "key_concepts": analysis.key_concepts,
                "intent": analysis.intent
            },
            "prompt_selected": True
        }
    except Exception as e:
        logger.error(f"[API] Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
