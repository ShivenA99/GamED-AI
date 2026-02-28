"""Repository for PipelineStep operations"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.models import PipelineStep
from app.utils.logger import setup_logger

logger = setup_logger("pipeline_step_repository")

class PipelineStepRepository:
    """Repository for pipeline step tracking operations"""
    
    @staticmethod
    def create(
        db: Session,
        process_id: str,
        step_name: str,
        step_number: int,
        input_data: Optional[Dict[str, Any]] = None
    ) -> PipelineStep:
        """Create a new pipeline step"""
        step = PipelineStep(
            process_id=process_id,
            step_name=step_name,
            step_number=step_number,
            status="pending",
            input_data=input_data,
            started_at=datetime.utcnow()
        )
        db.add(step)
        db.commit()
        db.refresh(step)
        logger.info(f"Created pipeline step: {step.id} - {step_name} (step {step_number})")
        return step
    
    @staticmethod
    def get_by_id(db: Session, step_id: str) -> Optional[PipelineStep]:
        """Get step by ID"""
        return db.query(PipelineStep).filter(PipelineStep.id == step_id).first()
    
    @staticmethod
    def get_by_process_id(db: Session, process_id: str) -> List[PipelineStep]:
        """Get all steps for a process, ordered by step number"""
        return db.query(PipelineStep).filter(
            PipelineStep.process_id == process_id
        ).order_by(PipelineStep.step_number).all()
    
    @staticmethod
    def update_status(
        db: Session,
        step_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        validation_result: Optional[Dict[str, Any]] = None
    ) -> Optional[PipelineStep]:
        """Update step status"""
        step = PipelineStepRepository.get_by_id(db, step_id)
        if not step:
            return None
        
        step.status = status
        if output_data is not None:
            step.output_data = output_data
        if error_message is not None:
            step.error_message = error_message
        if validation_result is not None:
            step.validation_result = validation_result
        
        if status == "processing" and not step.started_at:
            step.started_at = datetime.utcnow()
        elif status in ["completed", "error", "skipped"]:
            step.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(step)
        logger.info(f"Updated step {step_id}: status={status}")
        return step
    
    @staticmethod
    def increment_retry(db: Session, step_id: str) -> Optional[PipelineStep]:
        """Increment retry count for a step"""
        step = PipelineStepRepository.get_by_id(db, step_id)
        if not step:
            return None
        
        step.retry_count += 1
        step.status = "pending"  # Reset to pending for retry
        step.error_message = None
        step.completed_at = None
        db.commit()
        db.refresh(step)
        logger.info(f"Incremented retry count for step {step_id}: {step.retry_count}")
        return step
    
    @staticmethod
    def get_failed_steps(db: Session, process_id: str) -> List[PipelineStep]:
        """Get all failed steps for a process"""
        return db.query(PipelineStep).filter(
            PipelineStep.process_id == process_id,
            PipelineStep.status == "error"
        ).order_by(PipelineStep.step_number).all()
    
    @staticmethod
    def get_last_completed_step(db: Session, process_id: str) -> Optional[PipelineStep]:
        """Get the last completed step for a process"""
        return db.query(PipelineStep).filter(
            PipelineStep.process_id == process_id,
            PipelineStep.status == "completed"
        ).order_by(PipelineStep.step_number.desc()).first()


