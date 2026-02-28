"""Repository for Visualization operations"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.db.models import Visualization
from app.utils.logger import setup_logger

logger = setup_logger("visualization_repository")

class VisualizationRepository:
    """Repository for visualization operations"""
    
    @staticmethod
    def create(
        db: Session,
        process_id: str,
        question_id: str,
        html_content: str,
        story_data_json: Dict[str, Any]
    ) -> Visualization:
        """Create a new visualization"""
        visualization = Visualization(
            process_id=process_id,
            question_id=question_id,
            html_content=html_content,
            story_data_json=story_data_json
        )
        db.add(visualization)
        db.commit()
        db.refresh(visualization)
        logger.info(f"Created visualization: {visualization.id} for process: {process_id}")
        return visualization
    
    @staticmethod
    def get_by_id(db: Session, visualization_id: str) -> Optional[Visualization]:
        """Get visualization by ID"""
        return db.query(Visualization).filter(Visualization.id == visualization_id).first()
    
    @staticmethod
    def get_by_process_id(db: Session, process_id: str) -> Optional[Visualization]:
        """Get visualization by process ID"""
        return db.query(Visualization).filter(Visualization.process_id == process_id).first()
    
    @staticmethod
    def get_by_question_id(db: Session, question_id: str):
        """Get all visualizations for a question"""
        return db.query(Visualization).filter(Visualization.question_id == question_id).order_by(Visualization.created_at.desc()).all()


