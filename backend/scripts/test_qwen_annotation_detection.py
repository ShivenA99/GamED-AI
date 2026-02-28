#!/usr/bin/env python3
"""
Test Qwen VLM Annotation Detection

Compares:
1. EasyOCR + Hough (current) - detects ALL lines including diagram structure
2. Qwen VLM (new) - detects ONLY annotation elements (text + leader lines)

Usage:
    PYTHONPATH=. python scripts/test_qwen_annotation_detection.py \
        --image /path/to/diagram.jpg \
        --output-dir /tmp/annotation_test
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
logger = logging.getLogger("test_qwen_annotation")


async def test_qwen_detection(image_path: str, output_dir: Path):
    """Test Qwen VLM annotation detection."""
    from app.agents.qwen_annotation_detector import QwenAnnotationDetector

    logger.info("\n=== QWEN VLM ANNOTATION DETECTION ===")

    detector = QwenAnnotationDetector()

    if not await detector.is_available():
        logger.warning("Qwen VL not available - skipping")
        return None

    result = await detector.detect_annotations(image_path)

    annotations = result.get("annotations", [])
    text_count = sum(1 for a in annotations if a.get("type") == "text")
    line_count = sum(1 for a in annotations if a.get("type") == "line")

    logger.info(f"Detected {text_count} text labels, {line_count} leader lines")

    # Log details
    logger.info("\nTEXT LABELS:")
    for ann in annotations:
        if ann.get("type") == "text":
            logger.info(f"  - '{ann.get('content')}' at {ann.get('bbox')}")

    logger.info("\nLEADER LINES:")
    for ann in annotations:
        if ann.get("type") == "line":
            logger.info(f"  - connects to '{ann.get('connects_to')}': start={ann.get('start')}, end={ann.get('end')}")

    # Create visualization
    img = cv2.imread(image_path)
    h, w = img.shape[:2]

    for ann in annotations:
        bbox = ann.get("bbox", [])
        if len(bbox) != 4:
            continue

        x1 = int(bbox[0] * w / 1000)
        y1 = int(bbox[1] * h / 1000)
        x2 = int(bbox[2] * w / 1000)
        y2 = int(bbox[3] * h / 1000)

        if ann.get("type") == "text":
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green for text
        elif ann.get("type") == "line":
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)  # Blue for lines

            # Draw line itself if endpoints available
            start = ann.get("start", [])
            end = ann.get("end", [])
            if len(start) == 2 and len(end) == 2:
                pt1 = (int(start[0] * w / 1000), int(start[1] * h / 1000))
                pt2 = (int(end[0] * w / 1000), int(end[1] * h / 1000))
                cv2.line(img, pt1, pt2, (0, 0, 255), 3)  # Red line

    vis_path = str(output_dir / "qwen_detection_vis.png")
    cv2.imwrite(vis_path, img)
    logger.info(f"Saved visualization to {vis_path}")

    # Copy mask if exists
    mask_path = result.get("detection_mask_path")
    if mask_path and Path(mask_path).exists():
        import shutil
        dest = str(output_dir / "qwen_mask.png")
        shutil.copy(mask_path, dest)
        logger.info(f"Saved mask to {dest}")

    return result


async def test_hough_detection(image_path: str, output_dir: Path):
    """Test Hough line detection for comparison."""
    import easyocr
    from app.services.line_detection_service import HoughLineDetector

    logger.info("\n=== HOUGH LINE DETECTION (CURRENT APPROACH) ===")

    # EasyOCR text detection
    reader = easyocr.Reader(['en'], gpu=False)
    ocr_results = reader.readtext(image_path)

    img = cv2.imread(image_path)
    h, w = img.shape[:2]

    text_boxes = []
    for detection in ocr_results:
        bbox_points, text, confidence = detection
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]
        x1, y1 = int(min(xs)), int(min(ys))
        x2, y2 = int(max(xs)), int(max(ys))
        text_boxes.append({
            "bbox": {"x": x1, "y": y1, "width": x2-x1, "height": y2-y1},
            "text": text,
            "confidence": confidence
        })

    logger.info(f"EasyOCR detected {len(text_boxes)} text regions")

    # Hough line detection
    detector = HoughLineDetector(min_line_length=30, max_line_gap=10, proximity_threshold=50)
    all_lines = detector.detect_lines(image_path)
    filtered_lines = detector.filter_lines_near_text(all_lines, text_boxes)

    logger.info(f"Hough detected {len(all_lines) if all_lines is not None else 0} total lines")
    logger.info(f"Filtered to {len(filtered_lines)} lines near text")

    # Create visualization
    vis_img = img.copy()

    # Draw text boxes
    for box in text_boxes:
        b = box["bbox"]
        cv2.rectangle(vis_img, (b["x"], b["y"]), (b["x"]+b["width"], b["y"]+b["height"]), (0, 255, 0), 2)

    # Draw ALL Hough lines (to show the problem)
    if all_lines is not None:
        for line in all_lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(vis_img, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red for all lines

    vis_path = str(output_dir / "hough_all_lines_vis.png")
    cv2.imwrite(vis_path, vis_img)
    logger.info(f"Saved all lines visualization to {vis_path}")

    # Filtered lines visualization
    vis_filtered = img.copy()
    for box in text_boxes:
        b = box["bbox"]
        cv2.rectangle(vis_filtered, (b["x"], b["y"]), (b["x"]+b["width"], b["y"]+b["height"]), (0, 255, 0), 2)
    for line in filtered_lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(vis_filtered, (x1, y1), (x2, y2), (255, 165, 0), 2)  # Orange for filtered

    vis_path = str(output_dir / "hough_filtered_lines_vis.png")
    cv2.imwrite(vis_path, vis_filtered)
    logger.info(f"Saved filtered lines visualization to {vis_path}")

    # Create mask
    mask = detector.create_mask(img.shape, filtered_lines, thickness=8)

    # Add text boxes to mask
    for box in text_boxes:
        b = box["bbox"]
        padding = 10
        x1 = max(0, b["x"] - padding)
        y1 = max(0, b["y"] - padding)
        x2 = min(w, b["x"] + b["width"] + padding)
        y2 = min(h, b["y"] + b["height"] + padding)
        mask[y1:y2, x1:x2] = 255

    mask_path = str(output_dir / "hough_mask.png")
    cv2.imwrite(mask_path, mask)
    logger.info(f"Saved mask to {mask_path}")

    return {
        "text_boxes": text_boxes,
        "all_lines_count": len(all_lines) if all_lines is not None else 0,
        "filtered_lines_count": len(filtered_lines),
        "mask_path": mask_path
    }


async def main():
    parser = argparse.ArgumentParser(description="Test Qwen VLM annotation detection")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--output-dir", default="/tmp/annotation_test", help="Output directory")
    args = parser.parse_args()

    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("ANNOTATION DETECTION COMPARISON")
    logger.info("=" * 60)
    logger.info(f"Image: {args.image}")
    logger.info(f"Output: {output_dir}")

    # Test Hough (current approach)
    hough_result = await test_hough_detection(args.image, output_dir)

    # Test Qwen VLM (new approach)
    qwen_result = await test_qwen_detection(args.image, output_dir)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("COMPARISON SUMMARY")
    logger.info("=" * 60)

    logger.info("\nHOUGH APPROACH (current):")
    logger.info(f"  - Text boxes: {len(hough_result['text_boxes'])}")
    logger.info(f"  - All lines detected: {hough_result['all_lines_count']}")
    logger.info(f"  - Filtered lines (near text): {hough_result['filtered_lines_count']}")
    logger.info(f"  - PROBLEM: Many diagram structure lines still included!")

    if qwen_result:
        annotations = qwen_result.get("annotations", [])
        text_count = sum(1 for a in annotations if a.get("type") == "text")
        line_count = sum(1 for a in annotations if a.get("type") == "line")
        logger.info("\nQWEN VLM APPROACH (new):")
        logger.info(f"  - Text labels: {text_count}")
        logger.info(f"  - Leader lines: {line_count}")
        logger.info(f"  - BENEFIT: Only annotation elements, no diagram structure!")

    logger.info(f"\nOutput files saved to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
