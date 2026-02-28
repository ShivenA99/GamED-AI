#!/usr/bin/env python3
"""
Test Zone Detection from Leader Line Endpoints

This script tests the improved zone detection approach:
1. Detect annotations (text + leader lines) using hybrid approach
2. Extract zone locations from leader line endpoints
3. Verify zones match canonical labels

Usage:
    PYTHONPATH=. python scripts/test_zone_from_leader_lines.py \
        --image /path/to/diagram.jpg \
        --output-dir /tmp/zone_test
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_zone_from_leader_lines")


async def test_zone_detection(image_path: str, output_dir: Path):
    """Test the full annotation -> zone detection pipeline."""
    from app.agents.qwen_annotation_detector import QwenAnnotationDetector
    from app.agents.qwen_sam_zone_detector import QwenSAMZoneDetector, extract_zones_from_leader_lines

    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Could not load image: {image_path}")
        return

    h, w = img.shape[:2]

    # Canonical labels for the flower diagram
    canonical_labels = [
        "Pistil", "Stigma", "Style", "Ovary", "Ovule",
        "Stamen", "Anther", "Filament",
        "Petal", "Sepal", "Receptacle"
    ]

    logger.info("=" * 60)
    logger.info("STEP 1: DETECT ANNOTATIONS")
    logger.info("=" * 60)

    # Step 1: Detect annotations using hybrid approach
    detector = QwenAnnotationDetector()
    annotation_result = await detector.detect_annotations(image_path, use_hybrid=True)

    annotations = annotation_result.get("annotations", [])
    text_labels = [a for a in annotations if a.get("type") == "text"]
    leader_lines = [a for a in annotations if a.get("type") == "line"]

    logger.info(f"Detected {len(text_labels)} text labels, {len(leader_lines)} leader lines")

    # Log leader lines with their endpoints
    logger.info("\nLEADER LINES:")
    for line in leader_lines:
        connects_to = line.get("connects_to", "?")
        start = line.get("start", [])
        end = line.get("end", [])
        direction = line.get("direction", "?")
        logger.info(f"  '{connects_to}': direction={direction}, start={start}, end={end}")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: EXTRACT ZONES FROM LEADER LINE ENDPOINTS")
    logger.info("=" * 60)

    # Step 2: Extract zones from leader line endpoints
    zones, missing = extract_zones_from_leader_lines(
        annotations, canonical_labels, w, h
    )

    logger.info(f"Extracted {len(zones)} zones, {len(missing)} labels missing")

    logger.info("\nEXTRACTED ZONES:")
    for zone in zones:
        logger.info(f"  {zone['label']}: ({zone['x']:.1f}%, {zone['y']:.1f}%) - source: {zone['source']}")

    if missing:
        logger.info(f"\nMISSING LABELS: {missing}")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: CREATE VISUALIZATION")
    logger.info("=" * 60)

    # Create visualization
    vis = img.copy()

    # Draw leader lines
    for line in leader_lines:
        start = line.get("start", [])
        end = line.get("end", [])
        if len(start) == 2 and len(end) == 2:
            pt1 = (int(start[0] * w / 1000), int(start[1] * h / 1000))
            pt2 = (int(end[0] * w / 1000), int(end[1] * h / 1000))
            cv2.line(vis, pt1, pt2, (255, 0, 0), 2)  # Blue line
            cv2.circle(vis, pt2, 8, (0, 0, 255), -1)  # Red dot at endpoint

    # Draw zones
    for zone in zones:
        # Draw center point
        cx = int(zone["x"] * w / 100)
        cy = int(zone["y"] * h / 100)
        cv2.circle(vis, (cx, cy), 10, (0, 255, 0), 3)  # Green circle

        # Draw bbox if available
        bbox = zone.get("bbox", {})
        if bbox:
            x1 = int(bbox.get("x", 0))
            y1 = int(bbox.get("y", 0))
            x2 = x1 + int(bbox.get("width", 50))
            y2 = y1 + int(bbox.get("height", 50))
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Add label
        cv2.putText(vis, zone["label"], (cx - 40, cy - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    vis_path = str(output_dir / "zone_visualization.png")
    cv2.imwrite(vis_path, vis)
    logger.info(f"Saved visualization to {vis_path}")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: FULL DETECTOR TEST")
    logger.info("=" * 60)

    # Step 4: Test full detector
    zone_detector = QwenSAMZoneDetector()
    result = await zone_detector.detect_zones(
        image_path,
        canonical_labels,
        annotation_elements=annotations
    )

    logger.info(f"Zone detector result: {len(result['zones'])} zones, method={result['method']}")

    for zone in result['zones']:
        logger.info(f"  {zone['label']}: ({zone['x']:.1f}%, {zone['y']:.1f}%) "
                   f"confidence={zone['confidence']:.2f} source={zone['source']}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Canonical labels: {len(canonical_labels)}")
    logger.info(f"Text labels detected: {len(text_labels)}")
    logger.info(f"Leader lines detected: {len(leader_lines)}")
    logger.info(f"Zones extracted: {len(zones)}")
    logger.info(f"Labels matched: {len(zones)} / {len(canonical_labels)}")
    logger.info(f"Detection method: {result['method']}")

    coverage = len(zones) / len(canonical_labels) * 100
    logger.info(f"Coverage: {coverage:.1f}%")

    if coverage >= 80:
        logger.info("SUCCESS: Good zone coverage from leader line endpoints!")
    elif coverage >= 50:
        logger.info("PARTIAL: Some zones detected, but missing several labels")
    else:
        logger.info("WARNING: Low coverage - may need to improve leader line detection")

    return result


async def main():
    parser = argparse.ArgumentParser(description="Test zone detection from leader lines")
    parser.add_argument("--image", default="pipeline_outputs/assets/test_integration/diagram.jpg",
                        help="Path to test image")
    parser.add_argument("--output-dir", default="/tmp/zone_test", help="Output directory")
    args = parser.parse_args()

    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing zone detection")
    logger.info(f"Image: {args.image}")
    logger.info(f"Output: {output_dir}")

    await test_zone_detection(args.image, output_dir)


if __name__ == "__main__":
    asyncio.run(main())
