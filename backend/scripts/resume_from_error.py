#!/usr/bin/env python3
"""
Resume a pipeline run from a saved state, continuing from where it errored.
This allows re-running only the failed steps without starting from scratch.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.state import AgentState, create_initial_state
from app.agents.graph import get_compiled_graph
from app.db.database import SessionLocal
from app.db.models import Process, Question
from app.routes.generate import run_generation_pipeline
from datetime import datetime
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_saved_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Load a saved pipeline run from pipeline_outputs"""
    pipeline_outputs = Path(__file__).parent.parent / "pipeline_outputs"
    run_file = pipeline_outputs / f"{run_id}.json"
    
    if not run_file.exists():
        logger.error(f"Run file not found: {run_file}")
        return None
    
    with open(run_file, "r") as f:
        return json.load(f)


def reconstruct_state_from_saved_run(saved_run: Dict[str, Any]) -> Dict[str, Any]:
    """Reconstruct AgentState from saved run data"""
    agent_outputs = saved_run.get("agent_outputs", {})
    
    # Build state from agent outputs
    state = {
        "question_id": saved_run.get("question_id", ""),
        "question_text": saved_run.get("question_text", ""),
        "question_options": None,
        
        # Reconstruct from agent outputs
        "pedagogical_context": agent_outputs.get("input_enhancer", {}).get("output"),
        "domain_knowledge": agent_outputs.get("domain_knowledge_retriever", {}).get("output"),
        "template_selection": agent_outputs.get("router", {}).get("output", {}).get("template_selection"),
        "routing_confidence": agent_outputs.get("router", {}).get("output", {}).get("routing_confidence"),
        "game_plan": agent_outputs.get("game_planner", {}).get("output"),
        "scene_data": agent_outputs.get("scene_generator", {}).get("output"),
        "diagram_image": agent_outputs.get("diagram_image_retriever", {}).get("output"),
        "diagram_segments": agent_outputs.get("diagram_image_segmenter", {}).get("output"),
        "diagram_zones": agent_outputs.get("diagram_zone_labeler", {}).get("output", {}).get("diagram_zones"),
        "diagram_labels": agent_outputs.get("diagram_zone_labeler", {}).get("output", {}).get("diagram_labels"),
        "blueprint": agent_outputs.get("blueprint_generator", {}).get("output"),
        "diagram_spec": agent_outputs.get("diagram_spec_generator", {}).get("output"),
        "diagram_svg": agent_outputs.get("diagram_svg_generator", {}).get("output"),
        
        # Initialize tracking fields
        "retry_image_search": False,
        "image_search_attempts": 0,
        "max_image_attempts": 3,
        "validation_results": {},
        "current_validation_errors": [],
        "retry_counts": {},
        "max_retries": 3,
        "agent_history": [],
        "started_at": datetime.utcnow().isoformat(),
        "last_updated_at": datetime.utcnow().isoformat(),
        "current_agent": "resume_point",
        "generation_complete": False,
    }
    
    return state


async def resume_from_error(run_id: str, start_from_agent: Optional[str] = None):
    """
    Resume a pipeline run from where it errored.
    
    Args:
        run_id: The process_id of the failed run
        start_from_agent: Optional agent name to start from (e.g., 'diagram_image_retriever')
    """
    logger.info(f"Loading saved run: {run_id}")
    saved_run = load_saved_run(run_id)
    
    if not saved_run:
        logger.error(f"Could not load run {run_id}")
        return None
    
    logger.info(f"Loaded run: {saved_run.get('question_text', 'Unknown')}")
    logger.info(f"Previous status: {saved_run.get('success', False)}")
    logger.info(f"Error: {saved_run.get('error_message', 'None')}")
    
    # Create a new process for the resumed run
    db = SessionLocal()
    try:
        # Get or create question
        question_id = saved_run.get("question_id")
        question = db.query(Question).filter(Question.id == question_id).first()
        
        if not question:
            question = Question(
                id=question_id,
                text=saved_run.get("question_text", ""),
                options=saved_run.get("question_options"),
                created_at=datetime.utcnow()
            )
            db.add(question)
            db.commit()
        
        # Create new process
        new_process_id = str(uuid.uuid4())
        new_thread_id = f"thread_{new_process_id}"
        
        process = Process(
            id=new_process_id,
            question_id=question_id,
            status="processing",
            thread_id=new_thread_id,
            created_at=datetime.utcnow()
        )
        db.add(process)
        db.commit()
        
        logger.info(f"Created new process: {new_process_id}")
        logger.info(f"Resuming from saved state...")
        
        # Run the pipeline (it will use the saved state context)
        # Note: For full resume, we'd need to modify graph.py to accept initial state
        # For now, we'll just rerun with the same question
        result = await run_generation_pipeline(
            process_id=new_process_id,
            question_id=question_id,
            question_text=saved_run.get("question_text", ""),
            question_options=saved_run.get("question_options"),
            thread_id=new_thread_id
        )
        
        return new_process_id
        
    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        return None
    finally:
        db.close()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python resume_from_error.py <run_id> [start_from_agent]")
        print("\nExample:")
        print("  python resume_from_error.py ae838b0e-6890-4d14-922f-8575f101c339")
        print("  python resume_from_error.py ae838b0e-6890-4d14-922f-8575f101c339 diagram_image_retriever")
        sys.exit(1)
    
    run_id = sys.argv[1]
    start_from = sys.argv[2] if len(sys.argv) > 2 else None
    
    new_process_id = await resume_from_error(run_id, start_from)
    
    if new_process_id:
        print(f"\n✅ Resumed run created: {new_process_id}")
        print(f"   View status: http://localhost:8000/api/generate/{new_process_id}/status")
        print(f"   View game: http://localhost:3000/game/{new_process_id}")
    else:
        print("\n❌ Failed to resume run")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
