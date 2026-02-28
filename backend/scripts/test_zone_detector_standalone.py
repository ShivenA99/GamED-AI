#!/usr/bin/env python3
"""
Standalone test script for qwen_zone_detector agent.

Tests the zone detector with a cleaned image from the label remover,
or reconstructs state from a pipeline run.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.routes.observability import reconstruct_state_before_stage
from app.agents.qwen_zone_detector import qwen_zone_detector_agent
from app.agents.instrumentation import InstrumentedAgentContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_zone_detector(run_id: str):
    """
    Test qwen_zone_detector agent with state from a specific run.
    
    Args:
        run_id: Pipeline run ID to extract state from
    """
    logger.info("=" * 80)
    logger.info(f"Testing qwen_zone_detector with run ID: {run_id}")
    logger.info("=" * 80)
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Reconstruct state before qwen_zone_detector stage
        # This should include cleaned_image_path from qwen_label_remover
        logger.info("Reconstructing state before 'qwen_zone_detector' stage...")
        state = await reconstruct_state_before_stage(
            run_id=run_id,
            target_stage="qwen_zone_detector",
            db=db
        )
        
        if not state:
            logger.error(f"Could not reconstruct state for run {run_id}")
            return
        
        logger.info(f"State reconstructed successfully")
        logger.info(f"Template type: {state.get('template_selection', {}).get('template_type', 'unknown')}")
        logger.info(f"Question ID: {state.get('question_id', 'unknown')}")
        
        # Check for cleaned image
        cleaned_image_path = state.get("cleaned_image_path")
        diagram_image = state.get("diagram_image", {})
        
        if not cleaned_image_path:
            logger.warning("No cleaned_image_path in state, will use original diagram_image")
            if not diagram_image:
                logger.error("No diagram_image in state either!")
                return
        
        logger.info(f"Cleaned image path: {cleaned_image_path}")
        logger.info(f"Diagram image info: {diagram_image}")
        
        # Check required labels
        game_plan = state.get("game_plan", {}) or {}
        domain_knowledge = state.get("domain_knowledge", {}) or {}
        required_labels = game_plan.get("required_labels") or domain_knowledge.get("canonical_labels", [])
        
        if not required_labels:
            logger.warning("No required labels found in state")
            logger.info(f"Game plan: {game_plan}")
            logger.info(f"Domain knowledge keys: {list(domain_knowledge.keys())}")
        else:
            logger.info(f"Required labels ({len(required_labels)}): {required_labels}")
        
        # Create output directory for test results
        question_id = state.get("question_id", "test")
        output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "test_zone_detector" / question_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save input state for reference
        state_file = output_dir / "input_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)
        logger.info(f"Saved input state to {state_file}")
        
        # Run the zone detector agent
        logger.info("\n" + "=" * 80)
        logger.info("Running qwen_zone_detector_agent...")
        logger.info("=" * 80)
        
        # Create a context (without run_id for standalone testing)
        state["_run_id"] = None  # Disable instrumentation for standalone test
        
        result = await qwen_zone_detector_agent(state, ctx=None)
        
        # Save result
        result_file = output_dir / "result.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Saved result to {result_file}")
        
        # Log results
        logger.info("\n" + "=" * 80)
        logger.info("RESULTS:")
        logger.info("=" * 80)
        
        diagram_zones = result.get("diagram_zones", [])
        diagram_labels = result.get("diagram_labels", [])
        
        logger.info(f"Detected zones: {len(diagram_zones)}")
        logger.info(f"Detected labels: {len(diagram_labels)}")
        logger.info(f"Fallback used: {result.get('_used_fallback', False)}")
        if result.get('_fallback_reason'):
            logger.warning(f"Fallback reason: {result.get('_fallback_reason')}")
        
        # Log zone details
        if diagram_zones:
            logger.info("\nDetected zones:")
            for i, zone in enumerate(diagram_zones[:10]):  # First 10
                logger.info(
                    f"  {i+1}. {zone.get('label', 'unknown')} "
                    f"at ({zone.get('x', 0):.1f}%, {zone.get('y', 0):.1f}%) "
                    f"radius={zone.get('radius', 0):.1f}% "
                    f"confidence={zone.get('confidence', 0):.2f}"
                )
            if len(diagram_zones) > 10:
                logger.info(f"  ... and {len(diagram_zones) - 10} more zones")
        
        # Validate against required labels
        if required_labels:
            found_labels = {z.get("label", "").lower() for z in diagram_zones}
            required_set = {l.lower() for l in required_labels}
            missing = required_set - found_labels
            found = required_set & found_labels
            
            logger.info(f"\nLabel coverage:")
            logger.info(f"  Required: {len(required_labels)}")
            logger.info(f"  Found: {len(found)}")
            logger.info(f"  Missing: {len(missing)}")
            
            if missing:
                logger.warning(f"  Missing labels: {list(missing)}")
            if found:
                logger.info(f"  Found labels: {list(found)}")
        
        # Check for errors
        if result.get("zone_detection_error"):
            logger.error(f"Zone detection error: {result.get('zone_detection_error')}")
        
        logger.info("\n" + "=" * 80)
        logger.info("Test complete! Check output for zone detection results.")
        logger.info(f"Output directory: {output_dir}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    # Default run ID from the plan
    run_id = "3120da4a-97e5-47a3-b50c-9ae11077e7ce"
    
    # Allow override via command line
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
    
    asyncio.run(test_zone_detector(run_id))
