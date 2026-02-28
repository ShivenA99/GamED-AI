"""Progress route - refactored to use database"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.repositories.process_repository import ProcessRepository
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.services.pipeline.orchestrator import PipelineOrchestrator
from app.db.session import get_db
from app.utils.logger import setup_logger

# Set up logging
logger = setup_logger("progress")

router = APIRouter()

@router.get("/progress/{process_id}")
async def get_progress(
    process_id: str,
    db: Session = Depends(get_db)
):
    """Get progress status for a process"""
    logger.info(f"[API] /progress/{process_id} - Request received")
    
    try:
        process = ProcessRepository.get_by_id(db, process_id)
        if not process:
            logger.warning(f"[API] Process {process_id} not found")
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Get all steps for this process
        steps = PipelineStepRepository.get_by_process_id(db, process_id)
        
        # Get visualization ID if exists - query separately to avoid relationship issues
        from app.repositories.visualization_repository import VisualizationRepository
        visualization_id = None
        try:
            visualization = VisualizationRepository.get_by_process_id(db, process_id)
            if visualization:
                visualization_id = visualization.id
                logger.debug(f"[API] Process {process_id} has visualization: {visualization_id}")
            else:
                logger.debug(f"[API] Process {process_id} has no visualization yet")
        except Exception as e:
            logger.warning(f"[API] Error loading visualization for process {process_id}: {e}")
            # Continue without visualization_id
            pass
        
        # Calculate progress - use process.progress if available, otherwise calculate from steps
        calculated_progress = process.progress if process.progress is not None else 0
        
        # Fallback: Calculate progress from steps if process.progress is 0 or None
        if calculated_progress == 0 and steps:
            # Count completed and processing steps
            completed_steps = [s for s in steps if s.status == 'completed']
            processing_steps = [s for s in steps if s.status == 'processing']
            
            # Total pipeline steps (9 steps total)
            total_steps = 9
            
            if completed_steps:
                # Progress based on completed steps
                calculated_progress = int((len(completed_steps) / total_steps) * 100)
            elif processing_steps:
                # If a step is processing, show progress at start of that step
                processing_step = processing_steps[0]
                # Progress = (step_number - 1) / total_steps * 100
                calculated_progress = int(((processing_step.step_number - 1) / total_steps) * 100)
        
        # Ensure progress is between 0 and 100
        calculated_progress = max(0, min(100, calculated_progress))
        
        logger.info(f"[API] Returning status: {process.status}, progress: {calculated_progress}%, steps: {len(steps)}, visualization_id: {visualization_id}")
        
        return {
            "process_id": process_id,
            "status": process.status,
            "progress": calculated_progress,
            "current_step": process.current_step or "Initializing",
            "visualization_id": visualization_id,
            "error_message": process.error_message,
            "steps": [
                {
                    "id": step.id,
                    "step_name": step.step_name,
                    "step_number": step.step_number,
                    "status": step.status,
                    "error_message": step.error_message,
                    "retry_count": getattr(step, 'retry_count', 0) or 0,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "validation_result": step.validation_result,
                    "cached": step.output_data.get("_cached", False) if step.output_data else False
                }
                for step in steps
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error getting progress for {process_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")

@router.get("/pipeline/steps/{process_id}")
async def get_pipeline_steps(
    process_id: str,
    db: Session = Depends(get_db)
):
    """Get all steps for a process"""
    steps = PipelineStepRepository.get_by_process_id(db, process_id)
    
    if not steps:
        raise HTTPException(status_code=404, detail="Process not found or has no steps")
    
    return {
        "process_id": process_id,
        "steps": [
            {
                "id": step.id,
                "step_name": step.step_name,
                "step_number": step.step_number,
                "status": step.status,
                "input_data": step.input_data,
                "output_data": step.output_data,
                "error_message": step.error_message,
                "validation_result": step.validation_result,
                "retry_count": step.retry_count,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None
            }
            for step in steps
        ]
    }

@router.post("/pipeline/retry/{step_id}")
async def retry_step(
    step_id: str,
    db: Session = Depends(get_db)
):
    """Retry a failed step"""
    logger.info(f"Retry request for step: {step_id}")
    
    orchestrator = PipelineOrchestrator(db)
    result = orchestrator.retry_step(step_id)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Retry failed"))
    
    return {
        "success": True,
        "step_id": step_id,
        "message": "Step retry initiated"
    }

@router.get("/pipeline/history/{question_id}")
async def get_pipeline_history(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get processing history for a question"""
    processes = ProcessRepository.get_by_question_id(db, question_id)
    
    return {
        "question_id": question_id,
        "processes": [
            {
                "id": process.id,
                "status": process.status,
                "progress": process.progress,
                "started_at": process.started_at.isoformat() if process.started_at else None,
                "completed_at": process.completed_at.isoformat() if process.completed_at else None,
                "visualization_id": process.visualization.id if hasattr(process, 'visualization') and process.visualization else None
            }
            for process in processes
        ]
    }
