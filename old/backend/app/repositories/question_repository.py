"""Repository for Question operations"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.db.models import Question
from app.utils.logger import setup_logger

logger = setup_logger("question_repository")

class QuestionRepository:
    """Repository for question CRUD operations"""
    
    @staticmethod
    def create(db: Session, question_data: Dict[str, Any]) -> Question:
        """Create a new question"""
        question = Question(
            text=question_data["text"],
            options=question_data.get("options"),
            file_type=question_data.get("file_type"),
            full_text=question_data.get("full_text", question_data.get("text"))
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        logger.info(f"Created question: {question.id}")
        return question
    
    @staticmethod
    def get_by_id(db: Session, question_id: str) -> Optional[Question]:
        """Get question by ID"""
        return db.query(Question).filter(Question.id == question_id).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100):
        """Get all questions with pagination"""
        return db.query(Question).offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, question_id: str, update_data: Dict[str, Any]) -> Optional[Question]:
        """Update question"""
        question = QuestionRepository.get_by_id(db, question_id)
        if not question:
            return None
        
        for key, value in update_data.items():
            if hasattr(question, key):
                setattr(question, key, value)
        
        db.commit()
        db.refresh(question)
        logger.info(f"Updated question: {question_id}")
        return question
    
    @staticmethod
    def delete(db: Session, question_id: str) -> bool:
        """Delete question"""
        question = QuestionRepository.get_by_id(db, question_id)
        if not question:
            return False
        
        db.delete(question)
        db.commit()
        logger.info(f"Deleted question: {question_id}")
        return True


