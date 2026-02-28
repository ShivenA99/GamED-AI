#!/usr/bin/env python3
"""
Test Detection Methods

Compare different detection methods for label and leader line detection:
1. EasyOCR only (text detection)
2. Hough lines only (line detection)
3. EasyOCR + Hough (combined)
4. EasyOCR + Hough + CLIP filter (with semantic filtering)

Usage:
    PYTHONPATH=. python scripts/test_detection_methods.py \
        --image /path/to/heart_diagram.png \
        --output-dir /tmp/detection_tests
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_detection")


def test_easyocr_only(image_path: str) -> tuple:
    """Test EasyOCR text detection only."""
    import easyocr

    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(image_path)

    # Create mask from text boxes
    image = cv2.imread(image_path)
    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    text_regions = []
    for detection in results:
        bbox_points, text, confidence = detection
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]
        x_min, x_max = int(min(xs)), int(max(xs))
        y_min, y_max = int(min(ys)), int(max(ys))

        # Add padding
        padding = 10
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(w, x_max + padding)
        y_max = min(h, y_max + padding)

        cv2.rectangle(mask, (x_min, y_min), (x_max, y_max), 255, -1)
        text_regions.append({
            "text": text,
            "bbox": {"x": x_min, "y": y_min, "width": x_max - x_min, "height": y_max - y_min}
        })

    logger.info(f"EasyOCR detected {len(results)} text regions")
    return mask, text_regions


def test_hough_only(image_path: str) -> tuple:
    """Test Hough line detection only."""
    from app.services.line_detection_service import HoughLineDetector

    detector = HoughLineDetector()
    lines = detector.detect_lines(image_path)

    image = cv2.imread(image_path)
    lines_list = list(lines) if lines is not None else []
    mask = detector.create_mask(image.shape, lines_list, thickness=8)

    logger.info(f"Hough detected {len(lines) if lines is not None else 0} lines")
    return mask, lines_list


def test_combined(image_path: str) -> tuple:
    """Test combined EasyOCR + Hough detection with proximity filtering."""
    from app.services.line_detection_service import HoughLineDetector

    # Get text regions
    _, text_regions = test_easyocr_only(image_path)

    # Detect and filter lines
    detector = HoughLineDetector()
    all_lines = detector.detect_lines(image_path)

    filtered_lines = []
    if all_lines is not None and text_regions:
        filtered_lines = detector.filter_lines_near_text(all_lines, text_regions)
        filtered_lines = detector.filter_by_length(filtered_lines, cv2.imread(image_path).shape)
        filtered_lines = detector.filter_by_angle(filtered_lines)

    # Create combined mask
    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    text_mask = np.zeros((h, w), dtype=np.uint8)
    for region in text_regions:
        bbox = region["bbox"]
        cv2.rectangle(text_mask, (bbox["x"], bbox["y"]),
                      (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]), 255, -1)

    line_mask = detector.create_mask(image.shape, filtered_lines, thickness=8)
    combined_mask = cv2.bitwise_or(text_mask, line_mask)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    combined_mask = cv2.dilate(combined_mask, kernel, iterations=2)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

    logger.info(f"Combined: {len(text_regions)} text regions + {len(filtered_lines)} lines")
    return combined_mask, (text_regions, filtered_lines)


def test_with_clip(image_path: str) -> tuple:
    """Test combined + CLIP semantic filtering."""
    from app.services.clip_filtering_service import CLIPAnnotationFilter, is_clip_filter_enabled
    from app.services.line_detection_service import HoughLineDetector

    # Get text regions
    _, text_regions = test_easyocr_only(image_path)

    # Detect lines
    detector = HoughLineDetector()
    all_lines = detector.detect_lines(image_path)

    filtered_lines = []
    if all_lines is not None and text_regions:
        filtered_lines = detector.filter_lines_near_text(all_lines, text_regions)
        filtered_lines = detector.filter_by_length(filtered_lines, cv2.imread(image_path).shape)
        filtered_lines = detector.filter_by_angle(filtered_lines)

    # Apply CLIP filtering
    try:
        clip_filter = CLIPAnnotationFilter()
        filtered_lines = clip_filter.filter_hough_lines(image_path, filtered_lines, threshold=0.6)
        logger.info(f"CLIP filtered to {len(filtered_lines)} lines")
    except Exception as e:
        logger.warning(f"CLIP filtering failed: {e}")

    # Create combined mask
    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    text_mask = np.zeros((h, w), dtype=np.uint8)
    for region in text_regions:
        bbox = region["bbox"]
        cv2.rectangle(text_mask, (bbox["x"], bbox["y"]),
                      (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]), 255, -1)

    line_mask = detector.create_mask(image.shape, filtered_lines, thickness=8)
    combined_mask = cv2.bitwise_or(text_mask, line_mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    combined_mask = cv2.dilate(combined_mask, kernel, iterations=2)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

    return combined_mask, (text_regions, filtered_lines)


def visualize_detection(image_path: str, text_regions: list, lines: list, output_path: str):
    """Create visualization of detected text and lines."""
    image = cv2.imread(image_path)

    # Draw text boxes in blue
    for region in text_regions:
        bbox = region["bbox"]
        cv2.rectangle(image, (bbox["x"], bbox["y"]),
                      (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
                      (255, 0, 0), 2)

    # Draw lines in green
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.imwrite(output_path, image)
    logger.info(f"Saved visualization to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Test detection methods")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--output-dir", default="/tmp/detection_tests", help="Output directory")
    args = parser.parse_args()

    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing detection methods on: {args.image}")
    logger.info(f"Output directory: {output}")

    # Test 1: EasyOCR only
    logger.info("\n=== Test 1: EasyOCR Only ===")
    mask1, text_regions = test_easyocr_only(args.image)
    cv2.imwrite(str(output / "1_easyocr_only_mask.png"), mask1)

    # Test 2: Hough only
    logger.info("\n=== Test 2: Hough Lines Only ===")
    mask2, all_lines = test_hough_only(args.image)
    cv2.imwrite(str(output / "2_hough_only_mask.png"), mask2)

    # Test 3: Combined
    logger.info("\n=== Test 3: EasyOCR + Hough Combined ===")
    mask3, (_, filtered_lines) = test_combined(args.image)
    cv2.imwrite(str(output / "3_combined_mask.png"), mask3)
    visualize_detection(args.image, text_regions, filtered_lines,
                        str(output / "3_combined_visualization.png"))

    # Test 4: With CLIP
    logger.info("\n=== Test 4: EasyOCR + Hough + CLIP ===")
    try:
        mask4, (_, clip_lines) = test_with_clip(args.image)
        cv2.imwrite(str(output / "4_clip_filtered_mask.png"), mask4)
        visualize_detection(args.image, text_regions, clip_lines,
                            str(output / "4_clip_visualization.png"))
    except Exception as e:
        logger.warning(f"CLIP test skipped: {e}")

    logger.info(f"\n=== Results saved to {output} ===")
    logger.info("Compare visually:")
    logger.info("  - 1_easyocr_only_mask.png (text only)")
    logger.info("  - 2_hough_only_mask.png (all lines)")
    logger.info("  - 3_combined_mask.png (text + filtered lines)")
    logger.info("  - 4_clip_filtered_mask.png (with CLIP filtering)")


if __name__ == "__main__":
    asyncio.run(main())
