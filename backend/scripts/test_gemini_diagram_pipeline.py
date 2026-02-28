#!/usr/bin/env python3
"""
Test script for Gemini-based diagram processing pipeline.

Tests:
1. Diagram Cleaning with Gemini 2.5 Flash Image (Nano Banana)
2. Zone Detection with Gemini Vision

Usage:
    PYTHONPATH=. python scripts/test_gemini_diagram_pipeline.py
    PYTHONPATH=. python scripts/test_gemini_diagram_pipeline.py --image path/to/diagram.jpg
    PYTHONPATH=. python scripts/test_gemini_diagram_pipeline.py --skip-cleaning  # Use existing cleaned image
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("gemini_pipeline_test")

# Load environment
from dotenv import load_dotenv
load_dotenv()


def print_banner(text: str):
    """Print a banner for visual separation."""
    width = 70
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def print_result(title: str, data: dict, indent: int = 2):
    """Pretty print a result dictionary."""
    print(f"\n{' ' * indent}{title}:")
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 3:
            print(f"{' ' * (indent + 2)}{key}: [{len(value)} items]")
            for item in value[:3]:
                print(f"{' ' * (indent + 4)}- {item}")
            if len(value) > 3:
                print(f"{' ' * (indent + 4)}... and {len(value) - 3} more")
        elif isinstance(value, str) and len(value) > 100:
            print(f"{' ' * (indent + 2)}{key}: {value[:100]}...")
        else:
            print(f"{' ' * (indent + 2)}{key}: {value}")


async def run_pipeline(image_path: str, skip_cleaning: bool = False):
    """Run the Gemini diagram pipeline."""

    # Check API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not found in environment!")
        logger.error("Please set it in backend/.env file")
        sys.exit(1)

    logger.info(f"Google API Key: {api_key[:10]}...{api_key[-4:]}")

    # Create output directory
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"pipeline_outputs/gemini_runs/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Initialize service
    from app.services.gemini_diagram_service import get_gemini_service

    try:
        service = get_gemini_service()
        logger.info("Gemini service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini service: {e}")
        sys.exit(1)

    # Save run metadata
    run_metadata = {
        "run_id": run_id,
        "input_image": image_path,
        "started_at": datetime.now().isoformat(),
        "skip_cleaning": skip_cleaning,
    }

    results = {}

    # =========================================================================
    # STAGE 1: Diagram Cleaning
    # =========================================================================
    print_banner("STAGE 1: Diagram Cleaning (Gemini 2.5 Flash Image)")

    if skip_cleaning:
        logger.info("Skipping cleaning stage (--skip-cleaning flag)")
        # Use existing cleaned image or original
        cleaned_image_path = image_path
        results["cleaning"] = {"skipped": True, "image_path": image_path}
    else:
        logger.info(f"Input image: {image_path}")
        logger.info("Sending to Gemini for cleaning (remove text + leader lines)...")

        cleaned_output_path = str(output_dir / "01_cleaned_diagram.png")

        cleaning_result = await service.clean_diagram(
            image_path=image_path,
            output_path=cleaned_output_path,
        )

        results["cleaning"] = cleaning_result

        if cleaning_result.get("success"):
            logger.info(f"[SUCCESS] Cleaning completed in {cleaning_result.get('duration_ms')}ms")
            logger.info(f"Cleaned image saved to: {cleaning_result.get('cleaned_image_path')}")
            cleaned_image_path = cleaning_result.get("cleaned_image_path")
        else:
            logger.error(f"[FAILED] Cleaning failed: {cleaning_result.get('error')}")
            # Fall back to original image
            cleaned_image_path = image_path

        print_result("Cleaning Result", cleaning_result)

    # =========================================================================
    # STAGE 2: Zone Detection
    # =========================================================================
    print_banner("STAGE 2: Zone Detection (Gemini Vision)")

    # Canonical labels for flower diagram
    canonical_labels = [
        "petal", "sepal", "stamen", "anther", "filament",
        "pistil", "stigma", "style", "ovary", "ovule",
        "receptacle", "pedicel"
    ]

    logger.info(f"Using image: {cleaned_image_path}")
    logger.info(f"Looking for {len(canonical_labels)} parts: {', '.join(canonical_labels)}")
    logger.info("Sending to Gemini Vision for zone detection...")

    zone_result = await service.detect_zones(
        image_path=cleaned_image_path,
        canonical_labels=canonical_labels,
    )

    results["zone_detection"] = zone_result

    if zone_result.get("success"):
        zones = zone_result.get("zones", [])
        logger.info(f"[SUCCESS] Zone detection completed in {zone_result.get('duration_ms')}ms")
        logger.info(f"Detected {len(zones)} zones out of {len(canonical_labels)} requested")

        print("\n  Detected Zones:")
        for zone in zones:
            logger.info(
                f"    {zone['label']:15} -> x={zone['x']:5.1f}%, y={zone['y']:5.1f}% "
                f"(confidence: {zone['confidence']:.2f})"
            )

        if zone_result.get("parts_not_found"):
            logger.warning(f"  Parts not found: {zone_result.get('parts_not_found')}")

        # Save zones for pipeline use
        zones_output_path = output_dir / "02_detected_zones.json"
        with open(zones_output_path, "w") as f:
            json.dump({
                "zones": zones,
                "labels": [z["label"] for z in zones],
                "image_description": zone_result.get("image_description"),
                "parts_not_found": zone_result.get("parts_not_found", []),
            }, f, indent=2)
        logger.info(f"Zones saved to: {zones_output_path}")

    else:
        logger.error(f"[FAILED] Zone detection failed: {zone_result.get('error')}")
        if zone_result.get("raw_response"):
            logger.error(f"Raw response: {zone_result.get('raw_response')[:500]}")

    print_result("Zone Detection Result", zone_result)

    # =========================================================================
    # Summary
    # =========================================================================
    print_banner("PIPELINE SUMMARY")

    run_metadata["completed_at"] = datetime.now().isoformat()
    run_metadata["results"] = {
        "cleaning_success": results.get("cleaning", {}).get("success", results.get("cleaning", {}).get("skipped", False)),
        "zone_detection_success": results.get("zone_detection", {}).get("success", False),
        "zones_detected": len(results.get("zone_detection", {}).get("zones", [])),
    }

    # Save run metadata
    with open(output_dir / "run_metadata.json", "w") as f:
        json.dump(run_metadata, f, indent=2)

    # Get telemetry
    call_history = service.get_call_history()
    with open(output_dir / "api_telemetry.json", "w") as f:
        json.dump(call_history, f, indent=2)

    total_duration = sum(c.get("duration_ms", 0) for c in call_history)
    total_calls = len(call_history)
    successful_calls = sum(1 for c in call_history if c.get("success"))

    print(f"""
  Run ID: {run_id}
  Output Directory: {output_dir}

  API Calls:
    Total: {total_calls}
    Successful: {successful_calls}
    Total Duration: {total_duration}ms

  Results:
    Cleaning: {'SUCCESS' if run_metadata['results']['cleaning_success'] else 'FAILED'}
    Zone Detection: {'SUCCESS' if run_metadata['results']['zone_detection_success'] else 'FAILED'}
    Zones Detected: {run_metadata['results']['zones_detected']}/{len(canonical_labels)}

  Output Files:
    - {output_dir}/run_metadata.json
    - {output_dir}/api_telemetry.json
    - {output_dir}/01_cleaned_diagram.png (if cleaning ran)
    - {output_dir}/02_detected_zones.json
""")

    return results


def main():
    parser = argparse.ArgumentParser(description="Test Gemini diagram pipeline")
    parser.add_argument(
        "--image",
        type=str,
        default="pipeline_outputs/assets/test_run/diagram.jpg",
        help="Path to input diagram image"
    )
    parser.add_argument(
        "--skip-cleaning",
        action="store_true",
        help="Skip the cleaning stage, use input image directly for zone detection"
    )

    args = parser.parse_args()

    # Check image exists
    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    # Run pipeline
    asyncio.run(run_pipeline(args.image, args.skip_cleaning))


if __name__ == "__main__":
    main()
