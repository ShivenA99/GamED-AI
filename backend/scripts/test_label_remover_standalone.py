#!/usr/bin/env python3
"""
Standalone test script for qwen_label_remover agent.

Extracts state from a pipeline run and tests the label remover agent
with that state, saving output images for inspection.
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
from app.agents.qwen_label_remover import qwen_label_remover_agent
from app.agents.instrumentation import InstrumentedAgentContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_label_remover(run_id: str):
    """
    Test qwen_label_remover agent with state from a specific run.
    
    Args:
        run_id: Pipeline run ID to extract state from
    """
    logger.info("=" * 80)
    logger.info(f"Testing qwen_label_remover with run ID: {run_id}")
    logger.info("=" * 80)
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Reconstruct state before qwen_label_remover stage
        logger.info("Reconstructing state before 'qwen_label_remover' stage...")
        state = await reconstruct_state_before_stage(
            run_id=run_id,
            target_stage="qwen_label_remover",
            db=db
        )
        
        if not state:
            logger.error(f"Could not reconstruct state for run {run_id}")
            return
        
        logger.info(f"State reconstructed successfully")
        logger.info(f"Template type: {state.get('template_selection', {}).get('template_type', 'unknown')}")
        logger.info(f"Question ID: {state.get('question_id', 'unknown')}")
        
        # Check if we have diagram_image
        diagram_image = state.get("diagram_image", {})
        if not diagram_image:
            logger.error("No diagram_image in state!")
            logger.info(f"Available state keys: {list(state.keys())}")
            return
        
        logger.info(f"Diagram image info: {diagram_image}")
        
        # Create output directory for test results
        question_id = state.get("question_id", "test")
        output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "test_label_remover" / question_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save input state for reference
        state_file = output_dir / "input_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)
        logger.info(f"Saved input state to {state_file}")
        
        # Run the label remover agent
        logger.info("\n" + "=" * 80)
        logger.info("Running qwen_label_remover_agent...")
        logger.info("=" * 80)
        
        # Create a context (without run_id for standalone testing)
        state["_run_id"] = None  # Disable instrumentation for standalone test
        
        result = await qwen_label_remover_agent(state, ctx=None)
        
        # Save result
        result_file = output_dir / "result.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Saved result to {result_file}")
        
        # Log results
        logger.info("\n" + "=" * 80)
        logger.info("RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Cleaned image path: {result.get('cleaned_image_path')}")
        logger.info(f"Removed annotations count: {len(result.get('removed_annotations', []))}")
        logger.info(f"Mask path: {result.get('qwen_mask_path')}")
        logger.info(f"Fallback used: {result.get('_used_fallback', False)}")
        if result.get('_fallback_reason'):
            logger.warning(f"Fallback reason: {result.get('_fallback_reason')}")
        
        # Log annotation details
        annotations = result.get("removed_annotations", [])
        if annotations:
            text_count = sum(1 for a in annotations if a.get("type") == "text")
            line_count = sum(1 for a in annotations if a.get("type") == "line")
            arrow_count = sum(1 for a in annotations if a.get("type") == "arrow")
            logger.info(f"Annotation breakdown: {text_count} text, {line_count} lines, {arrow_count} arrows")
            
            # Log first few annotations
            logger.info("\nFirst 5 annotations:")
            for i, ann in enumerate(annotations[:5]):
                logger.info(f"  {i+1}. {ann.get('type')}: {ann.get('content', 'N/A')} at {ann.get('bbox')}")
        
        # Check if output files exist
        cleaned_path = result.get("cleaned_image_path")
        if cleaned_path and Path(cleaned_path).exists():
            logger.info(f"✓ Cleaned image exists: {cleaned_path}")
        else:
            logger.warning(f"✗ Cleaned image not found: {cleaned_path}")
        
        mask_path = result.get("qwen_mask_path")
        if mask_path and Path(mask_path).exists():
            logger.info(f"✓ Mask image exists: {mask_path}")
        else:
            logger.warning(f"✗ Mask image not found: {mask_path}")
        
        # Check original image
        original_path = diagram_image.get("local_path") or (Path(__file__).parent.parent / "pipeline_outputs" / "assets" / question_id / "diagram.jpg")
        if Path(original_path).exists():
            logger.info(f"✓ Original image exists: {original_path}")
        else:
            logger.warning(f"✗ Original image not found: {original_path}")
        
        logger.info("\n" + "=" * 80)
        logger.info("Test complete! Check output images for visual inspection.")
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
    
    asyncio.run(test_label_remover(run_id))
