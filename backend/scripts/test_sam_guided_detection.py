#!/usr/bin/env python3
"""
Test SAM-Guided Leader Line Detection

This script tests using SAM3 with text-derived point prompts to detect
leader lines more accurately than Hough transform.

Usage:
    # First download SAM model:
    wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth -P ~/models/

    # Then run:
    SAM3_MODEL_PATH=~/models/sam_vit_h_4b8939.pth PYTHONPATH=. python scripts/test_sam_guided_detection.py \
        --image /path/to/diagram.jpg \
        --output-dir /tmp/sam_tests
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_sam_guided")


def get_text_regions(image_path: str):
    """Detect text regions using EasyOCR."""
    import easyocr

    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(image_path)

    text_regions = []
    for detection in results:
        bbox_points, text, confidence = detection
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]
        x_min, x_max = int(min(xs)), int(max(xs))
        y_min, y_max = int(min(ys)), int(max(ys))

        text_regions.append({
            "text": text,
            "confidence": float(confidence),
            "bbox": {
                "x": x_min,
                "y": y_min,
                "width": x_max - x_min,
                "height": y_max - y_min
            }
        })

    logger.info(f"EasyOCR detected {len(text_regions)} text regions")
    return text_regions


def test_sam_guided(image_path: str, text_regions: list, output_dir: Path):
    """Test SAM-guided leader line detection."""
    from app.services.sam_guided_detection_service import SAMGuidedLineDetector

    logger.info("Testing SAM-guided detection...")

    detector = SAMGuidedLineDetector()

    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Detect leader lines
    mask, segments = detector.detect_leader_lines(image_rgb, text_regions)

    logger.info(f"SAM detected {len(segments)} leader line segments")

    # Save mask
    cv2.imwrite(str(output_dir / "sam_guided_mask.png"), mask)

    # Visualize
    vis = image.copy()
    vis[mask > 0] = [0, 255, 0]  # Green overlay for detected lines
    cv2.imwrite(str(output_dir / "sam_guided_visualization.png"), vis)

    return mask, segments


def test_sam_clip(image_path: str, text_regions: list, output_dir: Path):
    """Test SAM + CLIP combined detection."""
    from app.services.sam_guided_detection_service import SAMCLIPLineDetector

    logger.info("Testing SAM + CLIP detection...")

    detector = SAMCLIPLineDetector()

    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Detect with CLIP verification
    mask = detector.detect_leader_lines(image_rgb, text_regions)

    # Save mask
    cv2.imwrite(str(output_dir / "sam_clip_mask.png"), mask)

    # Visualize
    vis = image.copy()
    vis[mask > 0] = [0, 255, 0]
    cv2.imwrite(str(output_dir / "sam_clip_visualization.png"), vis)

    return mask


def test_hough_comparison(image_path: str, text_regions: list, output_dir: Path):
    """Test Hough detection for comparison."""
    from app.services.line_detection_service import HoughLineDetector

    logger.info("Testing Hough detection for comparison...")

    detector = HoughLineDetector()
    image = cv2.imread(image_path)

    lines = detector.detect_lines(image_path)
    filtered = detector.filter_lines_near_text(lines, text_regions) if lines is not None else []
    filtered = detector.filter_by_length(filtered, image.shape) if filtered else []
    filtered = detector.filter_by_angle(filtered) if filtered else []

    mask = detector.create_mask(image.shape, filtered, thickness=8)

    cv2.imwrite(str(output_dir / "hough_mask.png"), mask)

    logger.info(f"Hough detected {len(filtered)} lines")

    return mask


async def main():
    parser = argparse.ArgumentParser(description="Test SAM-guided detection")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--output-dir", default="/tmp/sam_tests", help="Output directory")
    args = parser.parse_args()

    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    sam_model = os.getenv("SAM3_MODEL_PATH")
    if not sam_model or not Path(sam_model).exists():
        logger.error(
            "SAM model not found. Please download it:\n"
            "  wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth -P ~/models/\n"
            "Then set SAM3_MODEL_PATH=~/models/sam_vit_h_4b8939.pth"
        )
        sys.exit(1)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing on: {args.image}")
    logger.info(f"Output: {output}")
    logger.info(f"SAM model: {sam_model}")

    # Get text regions
    text_regions = get_text_regions(args.image)

    # Test Hough (baseline)
    logger.info("\n=== Hough Detection (Baseline) ===")
    hough_mask = test_hough_comparison(args.image, text_regions, output)

    # Test SAM-guided
    logger.info("\n=== SAM-Guided Detection ===")
    try:
        sam_mask, segments = test_sam_guided(args.image, text_regions, output)
    except Exception as e:
        logger.error(f"SAM-guided detection failed: {e}")
        sam_mask = None

    # Test SAM + CLIP
    logger.info("\n=== SAM + CLIP Detection ===")
    try:
        sam_clip_mask = test_sam_clip(args.image, text_regions, output)
    except Exception as e:
        logger.error(f"SAM + CLIP detection failed: {e}")
        sam_clip_mask = None

    # Compare
    logger.info("\n=== Results ===")
    logger.info(f"Hough mask pixels: {np.sum(hough_mask > 0)}")
    if sam_mask is not None:
        logger.info(f"SAM mask pixels: {np.sum(sam_mask > 0)}")
    if sam_clip_mask is not None:
        logger.info(f"SAM+CLIP mask pixels: {np.sum(sam_clip_mask > 0)}")

    logger.info(f"\nOutputs saved to {output}")


if __name__ == "__main__":
    asyncio.run(main())
