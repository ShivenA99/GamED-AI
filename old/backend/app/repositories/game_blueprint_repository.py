"""Repository for GameBlueprint operations"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from app.db.models import GameBlueprint
from app.utils.logger import setup_logger

logger = setup_logger("game_blueprint_repository")

class GameBlueprintRepository:
    """Repository for game blueprint operations"""
    
    @staticmethod
    def create(
        db: Session,
        question_id: str,
        template_type: str,
        blueprint_json: Dict[str, Any],
        assets_json: Optional[Dict[str, Any]] = None
    ) -> GameBlueprint:
        """Create a new game blueprint"""
        blueprint = GameBlueprint(
            question_id=question_id,
            template_type=template_type,
            blueprint_json=blueprint_json,
            assets_json=assets_json or {}
        )
        db.add(blueprint)
        db.commit()
        db.refresh(blueprint)
        logger.info(f"Created game blueprint: {blueprint.id} for question: {question_id}, template: {template_type}")
        return blueprint
    
    @staticmethod
    def get_by_id(db: Session, blueprint_id: str) -> Optional[GameBlueprint]:
        """Get blueprint by ID"""
        return db.query(GameBlueprint).filter(GameBlueprint.id == blueprint_id).first()
    
    @staticmethod
    def get_by_question_id(db: Session, question_id: str) -> List[GameBlueprint]:
        """Get all blueprints for a question"""
        return db.query(GameBlueprint).filter(
            GameBlueprint.question_id == question_id
        ).order_by(GameBlueprint.created_at.desc()).all()
    
    @staticmethod
    def update_assets(
        db: Session,
        blueprint_id: str,
        assets_json: Dict[str, Any]
    ) -> Optional[GameBlueprint]:
        """Update assets for a blueprint"""
        blueprint = GameBlueprintRepository.get_by_id(db, blueprint_id)
        if not blueprint:
            return None
        
        blueprint.assets_json = assets_json
        db.commit()
        db.refresh(blueprint)
        logger.info(f"Updated assets for blueprint: {blueprint_id}")
        return blueprint
    
    @staticmethod
    def get_latest_by_question_id(db: Session, question_id: str) -> Optional[GameBlueprint]:
        """Get the latest blueprint for a question"""
        return db.query(GameBlueprint).filter(
            GameBlueprint.question_id == question_id
        ).order_by(GameBlueprint.created_at.desc()).first()

