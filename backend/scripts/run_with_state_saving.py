#!/usr/bin/env python3
"""
Run a pipeline with intermediate state saving at each agent step.
This allows resuming from any point if an error occurs.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.state import create_initial_state
from app.agents.graph import get_compiled_graph
from app.db.database import SessionLocal
from app.db.models import Process, Question
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATE_SAVE_DIR = Path(__file__).parent.parent / "pipeline_outputs" / "intermediate_states"
STATE_SAVE_DIR.mkdir(parents=True, exist_ok=True)


def save_intermediate_state(process_id: str, agent_name: str, state: Dict[str, Any]):
    """Save intermediate state after each agent execution"""
    state_file = STATE_SAVE_DIR / f"{process_id}_{agent_name}.json"
    
    # Extract relevant state (remove large binary data)
    saveable_state = {
        "process_id": process_id,
        "agent_name": agent_name,
        "timestamp": datetime.utcnow().isoformat(),
        "current_agent": state.get("current_agent"),
        "question_id": state.get("question_id"),
        "question_text": state.get("question_text"),
        "template_selection": state.get("template_selection"),
        "domain_knowledge": state.get("domain_knowledge"),
        "game_plan": state.get("game_plan"),
        "scene_data": state.get("scene_data"),
        "diagram_image": state.get("diagram_image"),
        "diagram_segments": state.get("diagram_segments"),
        "diagram_zones": state.get("diagram_zones"),
        "diagram_labels": state.get("diagram_labels"),
        "cleaned_image_path": state.get("cleaned_image_path"),
        "blueprint": state.get("blueprint"),
        "diagram_spec": state.get("diagram_spec"),
        "diagram_svg": state.get("diagram_svg"),
        "generation_complete": state.get("generation_complete", False),
        "error_message": state.get("error_message"),
        "agent_history": state.get("agent_history", [])[-10:],  # Last 10 agents
    }
    
    with open(state_file, "w") as f:
        json.dump(saveable_state, f, indent=2, default=str)
    
    logger.info(f"💾 Saved intermediate state: {state_file.name}")


async def run_with_state_saving(question_text: str, question_options: list = None):
    """Run pipeline with state saving at each step"""
    db = SessionLocal()
    
    try:
        # Create question
        question_id = str(uuid.uuid4())
        question = Question(
            id=question_id,
            text=question_text,
            options=question_options,
            created_at=datetime.utcnow()
        )
        db.add(question)
        db.commit()
        
        # Create process
        process_id = str(uuid.uuid4())
        thread_id = f"thread_{process_id}"
        
        process = Process(
            id=process_id,
            question_id=question_id,
            status="processing",
            thread_id=thread_id,
            created_at=datetime.utcnow()
        )
        db.add(process)
        db.commit()
        
        logger.info(f"🚀 Starting pipeline with state saving")
        logger.info(f"   Process ID: {process_id}")
        logger.info(f"   Question: {question_text[:100]}...")
        
        # Create initial state
        initial_state = create_initial_state(
            question_id=question_id,
            question_text=question_text,
            question_options=question_options
        )
        
        # Get graph
        graph = get_compiled_graph()
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run with streaming to capture intermediate states
        final_state = None
        async for event in graph.astream(initial_state, config):
            # Save state after each agent
            for node_name, node_state in event.items():
                if node_state and isinstance(node_state, dict):
                    try:
                        save_intermediate_state(process_id, node_name, node_state)
                        final_state = node_state
                        logger.info(f"✅ Completed: {node_name}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to save state for {node_name}: {e}")
        
        # Final state save
        if final_state:
            save_intermediate_state(process_id, "final", final_state)
            
            # Update process
            is_complete = final_state.get("generation_complete", False)
            process.status = "completed" if is_complete else "error"
            process.current_agent = final_state.get("current_agent")
            process.error_message = final_state.get("error_message")
            process.progress_percent = 100 if is_complete else process.progress_percent
            process.completed_at = datetime.utcnow() if is_complete else None
            db.commit()
            
            logger.info(f"✅ Pipeline completed: {process_id}")
            logger.info(f"   Status: {process.status}")
            logger.info(f"   View: http://localhost:3000/game/{process_id}")
            
            return process_id, final_state
        else:
            logger.error("No final state received")
            return None, None
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        if 'process' in locals():
            process.status = "error"
            process.error_message = str(e)
            db.commit()
        return None, None
    finally:
        db.close()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_with_state_saving.py '<question_text>'")
        print("\nExample:")
        print('  python run_with_state_saving.py "Label the parts of a flower"')
        sys.exit(1)
    
    question_text = sys.argv[1]
    question_options = sys.argv[2:] if len(sys.argv) > 2 else None
    
    process_id, final_state = await run_with_state_saving(question_text, question_options)
    
    if process_id:
        print(f"\n✅ Process ID: {process_id}")
        print(f"   View game: http://localhost:3000/game/{process_id}")
        print(f"   Intermediate states saved to: pipeline_outputs/intermediate_states/")
    else:
        print("\n❌ Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
