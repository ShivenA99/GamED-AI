#!/usr/bin/env python3
"""
Compare Qwen VLM vs Hough line detection to understand which lines are being detected.

This script:
1. Runs EasyOCR text detection
2. Runs Hough line detection (current approach)
3. Runs Qwen VLM text+line detection (smarter approach)
4. Visualizes the differences

Usage:
    PYTHONPATH=. python scripts/test_qwen_vs_hough_detection.py \
        --image /path/to/diagram.jpg \
        --output-dir /tmp/detection_comparison
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_detection_comparison")


def test_easyocr_detection(image_path: str) -> tuple:
    """Test EasyOCR text detection only."""
    import easyocr

    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(image_path)

    image = cv2.imread(image_path)
    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    text_regions = []
    for detection in results:
        bbox_points, text, confidence = detection
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]
        x1, y1 = int(min(xs)), int(min(ys))
        x2, y2 = int(max(xs)), int(max(ys))

        # Add padding
        padding = 10
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)

        mask[y1:y2, x1:x2] = 255
        text_regions.append({
            "text": text,
            "bbox": [x1, y1, x2, y2],
            "confidence": confidence
        })

    logger.info(f"EasyOCR detected {len(text_regions)} text regions")
    for r in text_regions:
        logger.info(f"  - '{r['text']}' at {r['bbox']} ({r['confidence']:.2f})")

    return mask, text_regions


def test_hough_detection(image_path: str, text_boxes: list) -> tuple:
    """Test Hough line detection with proximity filtering."""
    from app.services.line_detection_service import HoughLineDetector

    detector = HoughLineDetector(
        min_line_length=30,
        max_line_gap=10,
        proximity_threshold=50
    )

    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    # Detect all lines
    all_lines = detector.detect_lines(image_path)
    logger.info(f"Hough detected {len(all_lines) if all_lines is not None else 0} total lines")

    # Filter by proximity to text
    filtered_lines = detector.filter_lines_near_text(all_lines, text_boxes)
    logger.info(f"Filtered to {len(filtered_lines)} lines near text")

    # Create visualization
    vis_all = image.copy()
    vis_filtered = image.copy()

    if all_lines is not None:
        for line in all_lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(vis_all, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red for all lines

    for line in filtered_lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(vis_filtered, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green for filtered

    # Create mask from filtered lines
    mask = detector.create_mask(image.shape, filtered_lines, thickness=8)

    return mask, vis_all, vis_filtered, all_lines, filtered_lines


async def test_qwen_detection(image_path: str) -> tuple:
    """Test Qwen VLM text+line detection."""
    from app.services.qwen_vl_service import get_qwen_vl_service

    service = get_qwen_vl_service()

    if not await service.is_available():
        logger.warning("Qwen VL not available - skipping")
        return None, None, []

    # Use per-word detection (more accurate)
    logger.info("Running Qwen VL per-word detection...")
    result = await service.detect_labels_and_lines_per_word(image_path)

    annotations = result.get("annotations", [])
    mask_path = result.get("mask_path")

    text_count = sum(1 for a in annotations if a.get("type") == "text")
    line_count = sum(1 for a in annotations if a.get("type") == "line")

    logger.info(f"Qwen VL detected {text_count} text labels, {line_count} leader lines")

    # Log details
    for ann in annotations:
        if ann.get("type") == "text":
            logger.info(f"  TEXT: '{ann.get('content')}' at {ann.get('bbox')}")
        elif ann.get("type") == "line":
            logger.info(f"  LINE: for '{ann.get('text_label')}' - start={ann.get('start')}, end={ann.get('end')}")

    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE) if mask_path else None

    return mask, mask_path, annotations


def create_comparison_visualization(
    image_path: str,
    easyocr_mask: np.ndarray,
    hough_mask: np.ndarray,
    qwen_mask: np.ndarray,
    output_dir: str
):
    """Create side-by-side comparison of detection methods."""
    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    # Create colored overlays
    def create_overlay(img, mask, color):
        if mask is None:
            return img.copy()
        overlay = img.copy()
        colored = np.zeros_like(img)
        colored[mask > 0] = color
        return cv2.addWeighted(overlay, 0.7, colored, 0.3, 0)

    easyocr_vis = create_overlay(image, easyocr_mask, (255, 0, 0))  # Blue
    hough_vis = create_overlay(image, hough_mask, (0, 0, 255))  # Red
    qwen_vis = create_overlay(image, qwen_mask, (0, 255, 0)) if qwen_mask is not None else image.copy()

    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(easyocr_vis, "EasyOCR (text only)", (10, 30), font, 0.7, (255, 255, 255), 2)
    cv2.putText(hough_vis, "Hough (all lines filtered)", (10, 30), font, 0.7, (255, 255, 255), 2)
    cv2.putText(qwen_vis, "Qwen VL (text+lines)", (10, 30), font, 0.7, (255, 255, 255), 2)

    # Create combined comparison
    top_row = np.hstack([easyocr_vis, hough_vis])
    bottom_row = np.hstack([qwen_vis, image])

    # Resize if too large
    max_width = 1920
    if top_row.shape[1] > max_width:
        scale = max_width / top_row.shape[1]
        top_row = cv2.resize(top_row, None, fx=scale, fy=scale)
        bottom_row = cv2.resize(bottom_row, None, fx=scale, fy=scale)

    comparison = np.vstack([top_row, bottom_row])

    output_path = Path(output_dir) / "detection_comparison.png"
    cv2.imwrite(str(output_path), comparison)
    logger.info(f"Saved comparison to {output_path}")

    return str(output_path)


async def analyze_line_types(image_path: str, all_lines: list, text_boxes: list):
    """Analyze which lines are likely leader lines vs diagram structure."""
    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    logger.info("\n=== LINE ANALYSIS ===")

    if all_lines is None:
        logger.info("No lines detected")
        return

    leader_line_candidates = []
    diagram_structure_candidates = []

    for i, line in enumerate(all_lines):
        x1, y1, x2, y2 = line[0]

        # Calculate line properties
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        angle = np.arctan2(y2-y1, x2-x1) * 180 / np.pi

        # Check if near text
        near_text = False
        for box in text_boxes:
            bx1, by1, bx2, by2 = box["bbox"]
            # Check if either endpoint is within 50px of text box
            dist_start = min(
                abs(x1 - bx1), abs(x1 - bx2),
                abs(y1 - by1), abs(y1 - by2)
            )
            dist_end = min(
                abs(x2 - bx1), abs(x2 - bx2),
                abs(y2 - by1), abs(y2 - by2)
            )
            if dist_start < 50 or dist_end < 50:
                near_text = True
                break

        # Classify
        # Leader lines are typically:
        # - Short to medium length (30-200 px)
        # - Near text boxes
        # - Often horizontal or diagonal

        is_leader = near_text and length < 200

        line_info = {
            "idx": i,
            "start": (x1, y1),
            "end": (x2, y2),
            "length": length,
            "angle": angle,
            "near_text": near_text,
            "classified_as": "leader" if is_leader else "diagram"
        }

        if is_leader:
            leader_line_candidates.append(line_info)
        else:
            diagram_structure_candidates.append(line_info)

    logger.info(f"\nLeader line candidates: {len(leader_line_candidates)}")
    for l in leader_line_candidates[:10]:
        logger.info(f"  Line {l['idx']}: length={l['length']:.0f}px, angle={l['angle']:.1f}°, near_text={l['near_text']}")

    logger.info(f"\nDiagram structure candidates: {len(diagram_structure_candidates)}")
    for l in diagram_structure_candidates[:10]:
        logger.info(f"  Line {l['idx']}: length={l['length']:.0f}px, angle={l['angle']:.1f}°, near_text={l['near_text']}")

    return leader_line_candidates, diagram_structure_candidates


async def main():
    parser = argparse.ArgumentParser(description="Compare Qwen VLM vs Hough line detection")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--output-dir", default="/tmp/detection_comparison", help="Output directory")
    args = parser.parse_args()

    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("DETECTION METHOD COMPARISON")
    logger.info("=" * 60)
    logger.info(f"Image: {args.image}")
    logger.info(f"Output: {output_dir}")

    # 1. EasyOCR detection
    logger.info("\n=== STEP 1: EasyOCR Text Detection ===")
    easyocr_mask, text_regions = test_easyocr_detection(args.image)
    cv2.imwrite(str(output_dir / "1_easyocr_mask.png"), easyocr_mask)

    # Convert text_regions to bbox format for Hough filtering
    # Line detection expects: {"bbox": {"x": x1, "y": y1, "width": w, "height": h}}
    text_boxes = []
    for r in text_regions:
        x1, y1, x2, y2 = r["bbox"]
        text_boxes.append({
            "bbox": {
                "x": x1,
                "y": y1,
                "width": x2 - x1,
                "height": y2 - y1
            }
        })

    # 2. Hough line detection
    logger.info("\n=== STEP 2: Hough Line Detection ===")
    hough_mask, vis_all, vis_filtered, all_lines, filtered_lines = test_hough_detection(
        args.image, text_boxes
    )
    cv2.imwrite(str(output_dir / "2_hough_all_lines.png"), vis_all)
    cv2.imwrite(str(output_dir / "2_hough_filtered_lines.png"), vis_filtered)
    cv2.imwrite(str(output_dir / "2_hough_mask.png"), hough_mask)

    # 3. Analyze line types
    await analyze_line_types(args.image, all_lines, text_boxes)

    # 4. Qwen VLM detection
    logger.info("\n=== STEP 3: Qwen VLM Detection ===")
    qwen_mask, qwen_mask_path, qwen_annotations = await test_qwen_detection(args.image)
    if qwen_mask is not None:
        cv2.imwrite(str(output_dir / "3_qwen_mask.png"), qwen_mask)

    # 5. Create comparison
    logger.info("\n=== CREATING COMPARISON ===")
    comparison_path = create_comparison_visualization(
        args.image, easyocr_mask, hough_mask, qwen_mask, str(output_dir)
    )

    logger.info("\n" + "=" * 60)
    logger.info("COMPARISON COMPLETE")
    logger.info("=" * 60)
    logger.info(f"\nOutput files:")
    logger.info(f"  1_easyocr_mask.png - Text boxes only")
    logger.info(f"  2_hough_all_lines.png - All Hough lines (RED)")
    logger.info(f"  2_hough_filtered_lines.png - Filtered lines (GREEN)")
    logger.info(f"  2_hough_mask.png - Combined Hough mask")
    logger.info(f"  3_qwen_mask.png - Qwen VL detected mask")
    logger.info(f"  detection_comparison.png - Side-by-side comparison")


if __name__ == "__main__":
    asyncio.run(main())
