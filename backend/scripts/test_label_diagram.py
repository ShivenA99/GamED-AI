#!/usr/bin/env python3
"""
Test script for INTERACTIVE_DIAGRAM template with flower parts question.

Enhanced with comprehensive logging, progress tracking, and error monitoring.
Games are automatically saved to the database and appear in the UI.

Usage:
    FORCE_TEMPLATE=INTERACTIVE_DIAGRAM PYTHONPATH=. python scripts/test_interactive_diagram.py

    # With verbose logging
    LOG_LEVEL=DEBUG FORCE_TEMPLATE=INTERACTIVE_DIAGRAM PYTHONPATH=. python scripts/test_interactive_diagram.py

    # With file logging
    LOG_TO_FILE=true FORCE_TEMPLATE=INTERACTIVE_DIAGRAM PYTHONPATH=. python scripts/test_interactive_diagram.py

    # Disable auto-save to database (for testing without UI)
    SAVE_TO_DB=false FORCE_TEMPLATE=INTERACTIVE_DIAGRAM PYTHONPATH=. python scripts/test_interactive_diagram.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging BEFORE importing app modules
from app.utils.logging_config import setup_logging, get_logger

# Set up logging
log_level = os.getenv("LOG_LEVEL", "INFO")
log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
setup_logging(
    level=log_level,
    log_to_file=log_to_file,
    structured=False
)

# Import after logging setup
from app.agents.state import create_initial_state
from app.agents.topologies import TopologyType, create_topology

# Get logger
logger = get_logger("test_interactive_diagram")

# Test question for INTERACTIVE_DIAGRAM
TEST_QUESTION = {
    "id": "biology_flower_parts",
    "text": "Label the parts of a flower including the petal, sepal, stamen, pistil, ovary, and receptacle.",
    "options": None
}


def _resolve_topology() -> TopologyType:
    """Resolve topology from environment"""
    topology = os.environ.get("TOPOLOGY", "T1").upper()
    if topology == "T1":
        return TopologyType.T1_SEQUENTIAL_VALIDATED
    return TopologyType.T0_SEQUENTIAL


def check_ollama_running() -> bool:
    """Check if Ollama server is running"""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def print_stage_progress(stage_name: str, stage_num: int, total: int):
    """Print formatted stage progress"""
    logger.info("=" * 80)
    logger.info(f"STAGE {stage_num}/{total}: {stage_name.upper()}", stage=stage_name, stage_num=stage_num)
    logger.info("=" * 80)


async def run_test():
    """Run the INTERACTIVE_DIAGRAM test with comprehensive logging"""
    logger.info("=" * 80)
    logger.info("INTERACTIVE_DIAGRAM Template Test - Starting", question_id=TEST_QUESTION["id"])
    logger.info("=" * 80)
    
    # Print test configuration
    logger.info("Test Configuration:", metadata={
        "question": TEST_QUESTION["text"],
        "forced_template": os.environ.get("FORCE_TEMPLATE", "Not set"),
        "use_ollama": os.environ.get("USE_OLLAMA", "false"),
        "topology": os.environ.get("TOPOLOGY", "T1"),
        "log_level": log_level,
        "log_to_file": log_to_file
    })
    
    # Check Ollama if needed
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
    if use_ollama:
        if not check_ollama_running():
            logger.error("Ollama server is not running!", metadata={
                "action": "Start Ollama with: ollama serve"
            })
            return None
        else:
            logger.info("Ollama server is running", metadata={"status": "ready"})
    
    logger.info("=" * 80)
    
    # Create topology
    topology = _resolve_topology()
    logger.info(f"Using topology: {topology.value}", metadata={"topology": topology.value})
    
    graph = create_topology(topology)
    compiled = graph.compile()
    
    # Create initial state
    initial_state = create_initial_state(
        question_id=TEST_QUESTION["id"],
        question_text=TEST_QUESTION["text"],
        question_options=TEST_QUESTION.get("options")
    )
    
    logger.info("Starting pipeline execution...", question_id=TEST_QUESTION["id"])
    start_time = datetime.now()
    
    # Track execution stages
    stages_seen = []
    last_agent = None
    errors_encountered = []
    final_state = initial_state.copy()  # Track state as we go
    
    try:
        # Use astream to get state updates and monitor progress
        # This avoids executing the pipeline twice (unlike astream_events + ainvoke)
        async for state_update in compiled.astream(initial_state):
            # state_update is a dict with agent_name -> partial state update
            for agent_name, partial_state in state_update.items():
                if agent_name.startswith("_"):
                    continue
                
                # Track agent execution
                if agent_name != last_agent:
                    stages_seen.append(agent_name)
                    stage_num = len(stages_seen)
                    print_stage_progress(agent_name, stage_num, 15)  # Estimate 15 stages
                    logger.info(f"Starting agent: {agent_name}", agent_name=agent_name, stage_num=stage_num)
                    last_agent = agent_name
                
                # Merge partial state into final state
                if isinstance(partial_state, dict):
                    final_state.update(partial_state)
                    logger.info(f"Completed agent: {agent_name}", agent_name=agent_name)
                    
                    # Log key state updates
                    if partial_state.get("template_selection"):
                        ts = partial_state["template_selection"]
                        logger.info(
                            f"Template selected: {ts.get('template_type')}",
                            template_type=ts.get("template_type"),
                            confidence=ts.get("confidence", 0)
                        )
                    
                    if partial_state.get("diagram_zones"):
                        zones = partial_state["diagram_zones"]
                        logger.info(f"Created {len(zones)} diagram zones", zone_count=len(zones))
                    
                    if partial_state.get("blueprint"):
                        bp = partial_state["blueprint"]
                        logger.info(
                            f"Blueprint generated: {bp.get('title', 'N/A')}",
                            blueprint_title=bp.get("title"),
                            template_type=bp.get("templateType")
                        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("PIPELINE EXECUTION SUMMARY", question_id=TEST_QUESTION["id"])
        logger.info("=" * 80)
        logger.info(f"Total execution time: {elapsed:.1f}s", duration_seconds=elapsed)
        logger.info(f"Stages executed: {len(stages_seen)}", stage_count=len(stages_seen))
        
        if errors_encountered:
            logger.warning(f"Errors encountered: {len(errors_encountered)}", error_count=len(errors_encountered))
            for err in errors_encountered:
                logger.warning(f"  - {err['agent']}: {err['error']}")
        else:
            logger.info("No errors encountered", error_count=0)
        
        # Print execution order
        logger.info("Execution Order:")
        for i, stage in enumerate(stages_seen, 1):
            logger.info(f"  {i}. {stage}", stage_num=i, stage_name=stage)
        
        # Print results summary
        logger.info("-" * 80)
        logger.info("Results Summary:")
        
        if final_state.get("pedagogical_context"):
            ctx = final_state["pedagogical_context"]
            logger.info("Pedagogical Context:", metadata={
                "subject": ctx.get("subject"),
                "blooms_level": ctx.get("blooms_level"),
                "difficulty": ctx.get("difficulty")
            })
        
        if final_state.get("template_selection"):
            sel = final_state["template_selection"]
            logger.info("Template Selection:", metadata={
                "template_type": sel.get("template_type"),
                "confidence": sel.get("confidence", 0),
                "production_ready": sel.get("is_production_ready")
            })
        
        if final_state.get("blueprint"):
            bp = final_state["blueprint"]
            logger.info("Blueprint Generated:", metadata={
                "title": bp.get("title"),
                "template_type": bp.get("templateType"),
                "zones_count": len(bp.get("diagram", {}).get("zones", [])) if bp.get("diagram") else 0,
                "labels_count": len(bp.get("labels", [])),
                "tasks_count": len(bp.get("tasks", []))
            })
            
            # Save blueprint to file
            output_dir = Path(__file__).parent.parent / "pipeline_outputs"
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"interactive_diagram_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(output_file, "w") as f:
                json.dump({
                    "question": TEST_QUESTION,
                    "blueprint": bp,
                    "template_selection": final_state.get("template_selection"),
                    "pedagogical_context": final_state.get("pedagogical_context"),
                    "elapsed_seconds": elapsed,
                    "execution_order": stages_seen,
                    "errors": errors_encountered
                }, f, indent=2)
            
            logger.info(f"Blueprint saved to: {output_file}", output_file=str(output_file))
            
            # Auto-import to database for UI visibility (enabled by default)
            # Set SAVE_TO_DB=false to disable
            save_to_db = os.getenv("SAVE_TO_DB", "true").lower() == "true"
            if save_to_db:
                try:
                    from app.utils.db_import import import_pipeline_run_to_db
                    logger.info("Importing pipeline run to database (SAVE_TO_DB=true)...")
                    process_id = import_pipeline_run_to_db(final_state)
                    logger.info(
                        "✅ Pipeline run imported to database",
                        process_id=process_id,
                        ui_url=f"http://localhost:3000/game/{process_id}",
                        games_url="http://localhost:3000/games"
                    )
                    print("\n" + "=" * 80)
                    print(f"✅ Game imported to database!")
                    print(f"   Process ID: {process_id}")
                    print(f"   Play game: http://localhost:3000/game/{process_id}")
                    print(f"   View all games: http://localhost:3000/games")
                    print("=" * 80 + "\n")
                except Exception as e:
                    logger.error(f"Failed to import to database: {e}", exc_info=True)
                    print(f"\n⚠️  Warning: Failed to import to database: {e}")
                    print("   Game saved to JSON but won't appear in UI.")
            else:
                logger.info("Skipping database import (SAVE_TO_DB=false)")
                logger.info("   To enable database import, run without SAVE_TO_DB or with: SAVE_TO_DB=true")
            
            # Print full blueprint for inspection
            logger.info("=" * 80)
            logger.info("FULL BLUEPRINT JSON:")
            logger.info("=" * 80)
            print(json.dumps(bp, indent=2))
        else:
            logger.error("No blueprint generated!", metadata={
                "error_message": final_state.get("error_message"),
                "validation_errors": final_state.get("current_validation_errors", [])
            })
        
        logger.info("=" * 80)
        logger.info("Test completed successfully", question_id=TEST_QUESTION["id"], success=True)
        
        return final_state
    
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.critical(
            f"Test failed with exception: {str(e)}",
            exc_info=True,
            duration_seconds=elapsed,
            question_id=TEST_QUESTION["id"],
            success=False
        )
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    try:
        result = asyncio.run(run_test())
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
