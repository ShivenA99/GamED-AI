"""Repository for Process operations"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
from app.db.models import Process
from app.utils.logger import setup_logger

logger = setup_logger("process_repository")

class ProcessRepository:
    """Repository for process tracking operations"""
    
    @staticmethod
    def create(db: Session, question_id: str, initial_status: str = "pending") -> Process:
        """Create a new process"""
        process = Process(
            question_id=question_id,
            status=initial_status,
            progress=0,
            started_at=datetime.utcnow()
        )
        db.add(process)
        db.commit()
        db.refresh(process)
        logger.info(f"Created process: {process.id} for question: {question_id}")
        return process
    
    @staticmethod
    def get_by_id(db: Session, process_id: str) -> Optional[Process]:
        """Get process by ID - don't eagerly load visualization to avoid relationship issues"""
        # Don't eagerly load visualization to avoid foreign key constraint issues
        # Visualization will be loaded separately if needed
        return db.query(Process).filter(Process.id == process_id).first()
    
    @staticmethod
    def update_status(
        db: Session,
        process_id: str,
        status: str,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[Process]:
        """Update process status"""
        process = ProcessRepository.get_by_id(db, process_id)
        if not process:
            return None
        
        process.status = status
        if progress is not None:
            process.progress = progress
        if current_step is not None:
            process.current_step = current_step
        if error_message is not None:
            process.error_message = error_message
        
        if status in ["completed", "error", "cancelled"]:
            process.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(process)
        logger.info(f"Updated process {process_id}: status={status}, progress={progress}")
        return process
    
    @staticmethod
    def get_by_question_id(db: Session, question_id: str):
        """Get all processes for a question"""
        return db.query(Process).filter(Process.question_id == question_id).order_by(Process.started_at.desc()).all()
    
    @staticmethod
    def get_active_processes(db: Session):
        """Get all active processes"""
        return db.query(Process).filter(
            Process.status.in_(["pending", "processing"])
        ).all()

