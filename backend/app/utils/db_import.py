"""
Database Import Utility

Functions to import completed pipeline runs into the database
so they appear in the UI. Used by test scripts and import tools.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from app.db.models import Question, Process, Visualization
from app.db.database import SessionLocal

logger = logging.getLogger("gamed_ai.utils.db_import")


def import_pipeline_run_to_db(
    final_state: Dict[str, Any],
    db: Optional[Session] = None
) -> str:
    """
    Import a completed pipeline run into the database.
    
    Creates Question, Process, and Visualization entries so the game
    appears in the UI at /games and is playable at /game/{process_id}.
    
    Args:
        final_state: Dict containing pipeline state. Can be:
            - Direct final_state from pipeline execution
            - Test JSON structure with keys: question, blueprint, template_selection, etc.
        db: Optional database session. If None, creates a new session.
    
    Returns:
        process_id: The created process ID for UI access
    
    Example:
        # From test script
        process_id = import_pipeline_run_to_db(final_state)
        print(f"Game available at: http://localhost:3000/game/{process_id}")
        
        # From test JSON file
        import json
        test_data = json.load(open("pipeline_outputs/test.json"))
        final_state = {
            "question_id": test_data["question"]["id"],
            "question_text": test_data["question"]["text"],
            "question_options": test_data["question"].get("options"),
            "blueprint": test_data["blueprint"],
            "template_selection": test_data.get("template_selection"),
            "pedagogical_context": test_data.get("pedagogical_context"),
            "game_plan": test_data.get("game_plan"),
            "story_data": test_data.get("story_data"),
        }
        process_id = import_pipeline_run_to_db(final_state)
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True
    
    try:
        # Extract data from final_state (handle both formats)
        # Format 1: Direct final_state from pipeline
        question_id = final_state.get("question_id")
        question_text = final_state.get("question_text")
        question_options = final_state.get("question_options")
        blueprint = final_state.get("blueprint")
        template_selection = final_state.get("template_selection")
        
        # Format 2: Test JSON structure
        if not question_id and "question" in final_state:
            question_data = final_state["question"]
            question_id = question_data.get("id")
            question_text = question_data.get("text")
            question_options = question_data.get("options")
        
        if not blueprint and "blueprint" in final_state:
            blueprint = final_state["blueprint"]
        
        if not template_selection and "template_selection" in final_state:
            template_selection = final_state["template_selection"]
        
        # Validate required data
        if not question_text:
            raise ValueError("question_text is required in final_state")
        
        if not blueprint:
            raise ValueError("blueprint is required in final_state")

        # Try to get external image URL from agent_outputs
        agent_outputs = final_state.get("agent_outputs", {})
        external_image_url = None
        if agent_outputs:
            diagram_retriever_output = agent_outputs.get("diagram_image_retriever", {}).get("output", {})
            external_image_url = diagram_retriever_output.get("image_url") or diagram_retriever_output.get("original_url")

        # Update blueprint diagram assetUrl if we have an external URL and local doesn't exist
        if external_image_url and isinstance(blueprint, dict):
            import urllib.parse
            diagram = blueprint.get("diagram", {})
            if isinstance(diagram, dict):
                current_url = diagram.get("assetUrl", "")
                # If current URL is a local asset path, replace with proxied external URL
                if current_url.startswith("/api/assets/"):
                    encoded_url = urllib.parse.quote(external_image_url, safe="")
                    diagram["assetUrl"] = f"/api/proxy/image?url={encoded_url}"
                    logger.info(f"Updated blueprint assetUrl to use proxied external URL")

        # Get template_type from blueprint or template_selection
        template_type = None
        if isinstance(blueprint, dict):
            template_type = blueprint.get("templateType")
        if not template_type and isinstance(template_selection, dict):
            template_type = template_selection.get("template_type")
        if not template_type:
            template_type = "UNKNOWN"
        
        logger.info(
            f"Importing pipeline run to database: question_id={question_id}, "
            f"question_text={question_text[:50] + '...' if len(question_text) > 50 else question_text}, "
            f"template_type={template_type}"
        )
        
        # Create Question entry
        # Use provided question_id if available, otherwise generate new one
        if question_id:
            # Check if question already exists
            existing_question = db.query(Question).filter(Question.id == question_id).first()
            if existing_question:
                question = existing_question
                logger.info(f"Using existing question: {question_id}")
            else:
                question = Question(
                    id=question_id,
                    text=question_text,
                    options=question_options
                )
                db.add(question)
                db.commit()
                db.refresh(question)
                logger.info(f"Created new question: {question_id}")
        else:
            # Generate new question_id
            question = Question(
                id=str(uuid.uuid4()),
                text=question_text,
                options=question_options
            )
            db.add(question)
            db.commit()
            db.refresh(question)
            logger.info(f"Created new question with generated ID: {question.id}")
        
        # Create Process entry
        process = Process(
            id=str(uuid.uuid4()),
            question_id=question.id,
            status="completed",
            thread_id=str(uuid.uuid4()),  # LangGraph thread ID (not used for completed runs)
            progress_percent=100,
            completed_at=datetime.utcnow()
        )
        db.add(process)
        db.commit()
        db.refresh(process)
        logger.info(f"Created process: {process.id}")
        
        # Create Visualization entry
        visualization = Visualization(
            id=str(uuid.uuid4()),
            process_id=process.id,
            template_type=template_type,
            blueprint=blueprint,
            asset_urls=final_state.get("asset_urls"),
            pedagogical_context=final_state.get("pedagogical_context"),
            game_plan=final_state.get("game_plan"),
            story_data=final_state.get("story_data")
        )
        db.add(visualization)
        db.commit()
        logger.info(f"Created visualization: {visualization.id}")
        
        logger.info(
            f"Pipeline run imported successfully: process_id={process.id}, "
            f"question_id={question.id}, template_type={template_type}, "
            f"ui_url=http://localhost:3000/game/{process.id}"
        )
        
        return process.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import pipeline run to database: {e}", exc_info=True)
        raise
    finally:
        if should_close_db:
            db.close()
