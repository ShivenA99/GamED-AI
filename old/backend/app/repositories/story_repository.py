"""Repository for Story operations"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.db.models import Story
from app.utils.logger import setup_logger

logger = setup_logger("story_repository")

class StoryRepository:
    """Repository for story data operations"""
    
    @staticmethod
    def create(db: Session, question_id: str, story_data: Dict[str, Any]) -> Story:
        """Create a new story from story data"""
        story = Story(
            question_id=question_id,
            story_title=story_data.get("story_title", "Untitled"),
            story_context=story_data.get("story_context", ""),
            learning_intuition=story_data.get("learning_intuition"),
            visual_metaphor=story_data.get("visual_metaphor"),
            interaction_design=story_data.get("interaction_design"),
            visual_elements=story_data.get("visual_elements", []),
            question_flow=story_data.get("question_flow", []),
            primary_question=story_data.get("primary_question", ""),
            learning_alignment=story_data.get("learning_alignment"),
            animation_cues=story_data.get("animation_cues"),
            question_implementation_notes=story_data.get("question_implementation_notes")
        )
        db.add(story)
        db.commit()
        db.refresh(story)
        logger.info(f"Created story: {story.id} for question: {question_id}")
        return story
    
    @staticmethod
    def get_by_id(db: Session, story_id: str) -> Optional[Story]:
        """Get story by ID"""
        return db.query(Story).filter(Story.id == story_id).first()
    
    @staticmethod
    def get_by_question_id(db: Session, question_id: str) -> Optional[Story]:
        """Get story by question ID (latest)"""
        return db.query(Story).filter(Story.question_id == question_id).order_by(Story.created_at.desc()).first()
    
    @staticmethod
    def update(db: Session, story_id: str, update_data: Dict[str, Any]) -> Optional[Story]:
        """Update story"""
        story = StoryRepository.get_by_id(db, story_id)
        if not story:
            return None
        
        for key, value in update_data.items():
            if hasattr(story, key):
                setattr(story, key, value)
        
        db.commit()
        db.refresh(story)
        logger.info(f"Updated story: {story_id}")
        return story


