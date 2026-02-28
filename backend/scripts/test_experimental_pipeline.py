#!/usr/bin/env python3
"""
Test Experimental Pipeline End-to-End

Run the complete experimental pipeline:
1. Combined label detection (EasyOCR + Hough + optional CLIP)
2. Smart inpainting (LaMa/SD/OpenCV)
3. Smart zone detection (SAM3 + CLIP labeling)

Usage:
    # For LaMa inpainting, start IOPaint first:
    iopaint start --model=lama --device=mps --port=8080

    PYTHONPATH=. python scripts/test_experimental_pipeline.py \
        --image /path/to/heart_diagram.png \
        --canonical-labels "aorta,left ventricle,right ventricle,pulmonary artery"
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_experimental_pipeline")


async def run_experimental_pipeline(image_path: str, canonical_labels: list):
    """Run the full experimental pipeline."""
    from app.agents.combined_label_detector import combined_label_detector
    from app.agents.smart_inpainter import smart_inpainter
    from app.agents.smart_zone_detector import smart_zone_detector

    # Create state with minimal required fields
    state = {
        "template_selection": {"template_type": "INTERACTIVE_DIAGRAM"},
        "diagram_image": {"local_path": image_path},
        "domain_knowledge": {"canonical_labels": canonical_labels},
        "game_plan": {"required_labels": canonical_labels},
    }

    logger.info("=" * 60)
    logger.info("EXPERIMENTAL PIPELINE TEST")
    logger.info("=" * 60)
    logger.info(f"Image: {image_path}")
    logger.info(f"Labels: {canonical_labels}")
    logger.info("=" * 60)

    # Phase 1: Detection
    logger.info("\n=== PHASE 1: COMBINED LABEL DETECTION ===")
    try:
        detection_result = await combined_label_detector(state, None)

        if detection_result.get("detection_mask_path"):
            logger.info(f"  Text boxes: {detection_result.get('text_boxes_count', 0)}")
            logger.info(f"  Lines detected: {detection_result.get('lines_detected', 0)}")
            logger.info(f"  Method: {detection_result.get('detection_method')}")
            logger.info(f"  Mask: {detection_result.get('detection_mask_path')}")

            # Update state
            state.update(detection_result)
        else:
            logger.error(f"  Detection failed: {detection_result.get('detection_error')}")
            return

    except Exception as e:
        logger.error(f"  Detection error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Phase 2: Inpainting
    logger.info("\n=== PHASE 2: SMART INPAINTING ===")
    try:
        inpaint_result = await smart_inpainter(state, None)

        if inpaint_result.get("cleaned_image_path"):
            logger.info(f"  Method: {inpaint_result.get('inpainting_method')}")
            logger.info(f"  Cleaned: {inpaint_result.get('cleaned_image_path')}")

            if inpaint_result.get("_used_fallback"):
                logger.warning(f"  Fallback: {inpaint_result.get('_fallback_reason')}")

            # Update state
            state.update(inpaint_result)
        else:
            logger.error(f"  Inpainting failed: {inpaint_result.get('inpainting_error')}")
            # Continue with original image
            state["cleaned_image_path"] = image_path

    except Exception as e:
        logger.error(f"  Inpainting error: {e}")
        import traceback
        traceback.print_exc()
        # Continue with original image
        state["cleaned_image_path"] = image_path

    # Phase 3: Zone Detection
    logger.info("\n=== PHASE 3: SMART ZONE DETECTION ===")
    try:
        zone_result = await smart_zone_detector(state, None)

        zones = zone_result.get("diagram_zones", [])
        labels = zone_result.get("diagram_labels", [])

        logger.info(f"  Method: {zone_result.get('zone_detection_method')}")
        logger.info(f"  Zones: {len(zones)}")
        logger.info(f"  Labels: {len(labels)}")

        if zone_result.get("_used_fallback"):
            logger.warning(f"  Fallback: {zone_result.get('_fallback_reason')}")

        # Print zone details
        logger.info("\n  Detected zones:")
        for zone in zones:
            logger.info(f"    - {zone.get('id')}: {zone.get('label')} "
                        f"({zone.get('confidence', 0):.0%}) at ({zone.get('x'):.1f}%, {zone.get('y'):.1f}%)")

        # Check coverage
        found_labels = {z.get("label", "").lower() for z in zones}
        expected_labels = {l.lower() for l in canonical_labels}
        missing = expected_labels - found_labels

        if missing:
            logger.warning(f"\n  Missing labels: {list(missing)}")
        else:
            logger.info("\n  All canonical labels covered!")

        # Update state
        state.update(zone_result)

    except Exception as e:
        logger.error(f"  Zone detection error: {e}")
        import traceback
        traceback.print_exc()
        return

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE!")
    logger.info("=" * 60)

    # Summary
    logger.info("\nOutput files:")
    logger.info(f"  Detection mask: {state.get('detection_mask_path')}")
    logger.info(f"  Cleaned image: {state.get('cleaned_image_path')}")

    # Return final state
    return state


async def main():
    parser = argparse.ArgumentParser(description="Test experimental pipeline")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--canonical-labels", required=True,
                        help="Comma-separated list of canonical labels")
    parser.add_argument("--inpainting-method", default=None,
                        choices=["lama", "stable_diffusion", "opencv"],
                        help="Force specific inpainting method")
    args = parser.parse_args()

    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    canonical_labels = [l.strip() for l in args.canonical_labels.split(",")]

    # Set environment variables if specified
    if args.inpainting_method:
        os.environ["INPAINTING_METHOD"] = args.inpainting_method

    # Run pipeline
    result = await run_experimental_pipeline(args.image, canonical_labels)

    if result:
        logger.info("\nPipeline succeeded!")
        sys.exit(0)
    else:
        logger.error("\nPipeline failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
