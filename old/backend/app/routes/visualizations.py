"""Visualization routes - Blueprint and visualization endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.repositories.visualization_repository import VisualizationRepository
from app.repositories.game_blueprint_repository import GameBlueprintRepository
from app.db.session import get_db
from app.utils.logger import setup_logger

logger = setup_logger("visualizations")

router = APIRouter()

@router.get("/blueprint/{blueprint_id}")
async def get_blueprint(
    blueprint_id: str,
    db: Session = Depends(get_db)
):
    """Get blueprint by ID"""
    logger.info(f"[API] /blueprint/{blueprint_id} - Request received")
    
    try:
        blueprint = GameBlueprintRepository.get_by_id(db, blueprint_id)
        
        if not blueprint:
            logger.warning(f"[API] Blueprint {blueprint_id} not found")
            raise HTTPException(status_code=404, detail="Blueprint not found")
        
        logger.info(f"[API] Returning blueprint {blueprint_id}")
        
        # Ensure blueprint_json is not None
        blueprint_json = blueprint.blueprint_json
        if blueprint_json is None:
            logger.error(f"[API] Blueprint {blueprint_id} has None blueprint_json - this should not happen")
            blueprint_json = {}
        
        return {
            "id": blueprint.id,
            "question_id": blueprint.question_id,
            "template_type": blueprint.template_type,
            "blueprint": blueprint_json,
            "assets": blueprint.assets_json or {},
            "created_at": blueprint.created_at.isoformat() if blueprint.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error getting blueprint {blueprint_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting blueprint: {str(e)}")

@router.get("/visualization/{visualization_id}")
async def get_visualization(
    visualization_id: str,
    db: Session = Depends(get_db)
):
    """Get visualization (blueprint or HTML)"""
    logger.info(f"[API] /visualization/{visualization_id} - Request received")
    
    try:
        visualization = VisualizationRepository.get_by_id(db, visualization_id)
        
        if not visualization:
            logger.warning(f"[API] Visualization {visualization_id} not found")
            raise HTTPException(status_code=404, detail="Visualization not found")
        
        # Get story data from story_data_json (return as question_data for frontend compatibility)
        question_data = visualization.story_data_json if visualization.story_data_json else None
        if question_data:
            logger.debug(f"[API] Found story data for visualization {visualization_id}")
        else:
            logger.warning(f"[API] Visualization {visualization_id} has no story data")
        
        # Get blueprint if available
        blueprint_data = None
        if visualization.blueprint_id:
            blueprint = GameBlueprintRepository.get_by_id(db, visualization.blueprint_id)
            if blueprint:
                # Ensure blueprint_json is not None
                blueprint_json = blueprint.blueprint_json
                if blueprint_json is None:
                    logger.error(f"[API] Blueprint {blueprint.id} has None blueprint_json - this should not happen")
                    blueprint_json = {}
                
                blueprint_data = {
                    "id": blueprint.id,
                    "template_type": blueprint.template_type,
                    "blueprint": blueprint_json,
                    "assets": blueprint.assets_json or {}
                }
                logger.info(f"[API] Found blueprint for visualization {visualization_id}")
        
        # Return blueprint if available, otherwise HTML
        if blueprint_data:
            logger.info(f"[API] Returning blueprint for visualization {visualization_id}")
            return {
                "id": visualization.id,
                "type": "blueprint",
                "blueprint": blueprint_data,
                "question_data": question_data
            }
        else:
            logger.info(f"[API] Returning HTML for visualization {visualization_id}, HTML length: {len(visualization.html_content or '')} chars")
            return {
                "id": visualization.id,
                "type": "html",
                "html": visualization.html_content or "",
                "question_data": question_data
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error getting visualization {visualization_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting visualization: {str(e)}")

