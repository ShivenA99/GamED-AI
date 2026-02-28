#!/usr/bin/env python3
"""
Integration test for label remover + zone detector agents.

Tests both agents in sequence to verify end-to-end flow.
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
from app.agents.qwen_zone_detector import qwen_zone_detector_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_integration(run_id: str):
    """
    Test both agents in sequence.
    
    Args:
        run_id: Pipeline run ID to extract initial state from
    """
    logger.info("=" * 80)
    logger.info(f"Integration Test: Label Remover + Zone Detector")
    logger.info(f"Using run ID: {run_id}")
    logger.info("=" * 80)
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Step 1: Get initial state (before label remover)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Reconstructing state before label remover...")
        logger.info("=" * 80)
        
        state = await reconstruct_state_before_stage(
            run_id=run_id,
            target_stage="qwen_label_remover",
            db=db
        )
        
        if not state:
            logger.error(f"Could not reconstruct state for run {run_id}")
            return
        
        question_id = state.get("question_id", "test")
        logger.info(f"Question ID: {question_id}")
        logger.info(f"Template: {state.get('template_selection', {}).get('template_type', 'unknown')}")
        
        # Step 2: Run label remover
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Running qwen_label_remover_agent...")
        logger.info("=" * 80)
        
        state["_run_id"] = None  # Disable instrumentation
        label_remover_result = await qwen_label_remover_agent(state, ctx=None)
        
        # Update state with label remover results
        state.update(label_remover_result)
        
        logger.info(f"✓ Label remover completed")
        logger.info(f"  Cleaned image: {label_remover_result.get('cleaned_image_path')}")
        logger.info(f"  Annotations removed: {len(label_remover_result.get('removed_annotations', []))}")
        logger.info(f"  Fallback used: {label_remover_result.get('_used_fallback', False)}")
        
        if label_remover_result.get('_used_fallback'):
            logger.warning(f"  ⚠️  Fallback reason: {label_remover_result.get('_fallback_reason')}")
        else:
            logger.info("  ✓ No fallback - Qwen VL worked successfully!")
        
        # Step 3: Run zone detector
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Running qwen_zone_detector_agent...")
        logger.info("=" * 80)
        
        zone_detector_result = await qwen_zone_detector_agent(state, ctx=None)
        
        # Update state with zone detector results
        state.update(zone_detector_result)
        
        logger.info(f"✓ Zone detector completed")
        diagram_zones = zone_detector_result.get("diagram_zones", [])
        diagram_labels = zone_detector_result.get("diagram_labels", [])
        logger.info(f"  Zones detected: {len(diagram_zones)}")
        logger.info(f"  Labels detected: {len(diagram_labels)}")
        logger.info(f"  Fallback used: {zone_detector_result.get('_used_fallback', False)}")
        
        if zone_detector_result.get('_used_fallback'):
            logger.warning(f"  ⚠️  Fallback reason: {zone_detector_result.get('_fallback_reason')}")
        else:
            logger.info("  ✓ No fallback - Qwen VL worked successfully!")
        
        # Step 4: Summary
        logger.info("\n" + "=" * 80)
        logger.info("INTEGRATION TEST SUMMARY")
        logger.info("=" * 80)
        
        # Check required labels
        game_plan = state.get("game_plan", {}) or {}
        domain_knowledge = state.get("domain_knowledge", {}) or {}
        required_labels = game_plan.get("required_labels") or domain_knowledge.get("canonical_labels", [])
        
        if required_labels:
            found_labels = {z.get("label", "").lower() for z in diagram_zones}
            required_set = {l.lower() for l in required_labels}
            coverage = len(found_labels & required_set) / len(required_set) * 100
            
            logger.info(f"Label Coverage: {coverage:.1f}% ({len(found_labels & required_set)}/{len(required_set)})")
            
            missing = required_set - found_labels
            if missing:
                logger.warning(f"Missing labels: {list(missing)}")
        
        # Save final state
        output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "test_integration" / question_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / "final_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"\n✓ Integration test complete!")
        logger.info(f"  Output directory: {output_dir}")
        logger.info("=" * 80)
        
        # Final validation
        success = True
        if label_remover_result.get('_used_fallback'):
            logger.warning("⚠️  Label remover used fallback")
            success = False
        if zone_detector_result.get('_used_fallback'):
            logger.warning("⚠️  Zone detector used fallback")
            success = False
        if not diagram_zones:
            logger.error("✗ No zones detected")
            success = False
        
        if success:
            logger.info("✓ All checks passed - integration test successful!")
        else:
            logger.warning("⚠️  Some issues detected - check logs above")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    # Default run ID from the plan
    run_id = "3120da4a-97e5-47a3-b50c-9ae11077e7ce"
    
    # Allow override via command line
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
    
    asyncio.run(test_integration(run_id))
