"""Step logger for pipeline execution"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.utils.logger import setup_logger

logger = setup_logger("step_logger")

class StepLogger:
    """Logs pipeline step execution to database"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_step_start(
        self,
        process_id: str,
        step_name: str,
        step_number: int,
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log step start and return step ID"""
        step = PipelineStepRepository.create(
            self.db,
            process_id,
            step_name,
            step_number,
            input_data
        )
        logger.info(f"Step {step_number} started: {step_name} (ID: {step.id})")
        return step.id
    
    def log_step_progress(
        self,
        step_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        validation_result: Optional[Dict[str, Any]] = None
    ):
        """Log step progress"""
        PipelineStepRepository.update_status(
            self.db,
            step_id,
            status,
            output_data=output_data,
            validation_result=validation_result
        )
        logger.debug(f"Step {step_id} updated: {status}")
    
    def log_step_error(
        self,
        step_id: str,
        error_message: str
    ):
        """Log step error"""
        PipelineStepRepository.update_status(
            self.db,
            step_id,
            "error",
            error_message=error_message
        )
        logger.error(f"Step {step_id} failed: {error_message}")
    
    def log_step_complete(
        self,
        step_id: str,
        output_data: Optional[Dict[str, Any]] = None,
        validation_result: Optional[Dict[str, Any]] = None
    ):
        """Log step completion"""
        PipelineStepRepository.update_status(
            self.db,
            step_id,
            "completed",
            output_data=output_data,
            validation_result=validation_result
        )
        logger.info(f"Step {step_id} completed successfully")


