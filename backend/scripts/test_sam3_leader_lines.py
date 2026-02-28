#!/usr/bin/env python3
"""
Test SAM3 MLX for Leader Line Detection

This script tests different approaches for detecting leader lines using
the local MLX SAM3 model:

1. Direct text prompts ("leader line", "annotation line", "pointer")
2. VLM-guided prompts (use Qwen/LLaVA to describe annotations)
3. EasyOCR + SAM3 point prompts (use text locations to guide SAM3)
4. CLIP verification (filter false positives)

Usage:
    cd backend
    PYTHONPATH=. python scripts/test_sam3_leader_lines.py \
        --image /path/to/diagram.png \
        --output-dir /tmp/sam3_tests
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_sam3_leader_lines")


def test_sam3_text_prompts(image_path: str, output_dir: Path) -> dict:
    """Test SAM3 with various text prompts for leader lines."""
    logger.info("\n=== Test 1: SAM3 with Text Prompts ===")

    try:
        from app.services.mlx_sam3_segmentation import mlx_sam3_segment_image

        # Different prompts for leader lines
        prompts_to_test = [
            {"leader_line": "leader line"},
            {"annotation": "annotation"},
            {"pointer": "pointer"},
            {"line": "thin black line"},
            {"arrow": "arrow pointing"},
            # Anatomical/diagram specific
            {"label_line": "line connecting text to diagram"},
        ]

        results = {}
        image = cv2.imread(image_path)

        for prompt_dict in prompts_to_test:
            prompt_name = list(prompt_dict.keys())[0]
            prompt_text = list(prompt_dict.values())[0]

            logger.info(f"Testing prompt: '{prompt_text}'")
            start = time.time()

            try:
                segments = mlx_sam3_segment_image(
                    image_path,
                    text_prompts=prompt_dict
                )
                elapsed = time.time() - start

                logger.info(f"  Found {len(segments)} segments in {elapsed:.1f}s")
                results[prompt_name] = {
                    "segments": segments,
                    "count": len(segments),
                    "time": elapsed
                }

                # Visualize
                vis = image.copy()
                for seg in segments:
                    bbox = seg["bbox"]
                    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                    cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    center = seg["center_px"]
                    cv2.circle(vis, (int(center["x"]), int(center["y"])), 5, (0, 0, 255), -1)

                cv2.imwrite(str(output_dir / f"sam3_prompt_{prompt_name}.png"), vis)

            except Exception as e:
                logger.warning(f"  Failed: {e}")
                results[prompt_name] = {"error": str(e)}

        return results

    except ImportError as e:
        logger.error(f"MLX SAM3 not available: {e}")
        return {"error": str(e)}


def test_easyocr_guided_sam3(image_path: str, output_dir: Path) -> dict:
    """Use EasyOCR text locations to guide SAM3 point prompts."""
    logger.info("\n=== Test 2: EasyOCR-guided SAM3 ===")

    try:
        import easyocr

        # Detect text with EasyOCR
        reader = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(image_path)

        logger.info(f"EasyOCR detected {len(results)} text regions")

        # Extract likely leader line attachment points
        # Leader lines typically attach at edges of text boxes
        attachment_points = []
        for bbox, text, conf in results:
            # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            pts = np.array(bbox, dtype=np.float32)
            x_min, y_min = pts.min(axis=0)
            x_max, y_max = pts.max(axis=0)

            # Add points at box edges (where leader lines likely attach)
            center_y = (y_min + y_max) / 2

            # Left edge
            attachment_points.append({
                "x": int(x_min - 5),
                "y": int(center_y),
                "text": text,
                "side": "left"
            })
            # Right edge
            attachment_points.append({
                "x": int(x_max + 5),
                "y": int(center_y),
                "text": text,
                "side": "right"
            })

        logger.info(f"Generated {len(attachment_points)} potential attachment points")

        # TODO: Use SAM3 point prompts instead of text prompts
        # MLX SAM3 API: processor.set_point_prompt(points, labels, state)
        # For now, visualize the attachment points

        image = cv2.imread(image_path)
        vis = image.copy()

        for pt in attachment_points:
            cv2.circle(vis, (pt["x"], pt["y"]), 3, (0, 0, 255), -1)

        cv2.imwrite(str(output_dir / "sam3_attachment_points.png"), vis)

        return {
            "text_regions": len(results),
            "attachment_points": len(attachment_points),
            "points": attachment_points[:20]  # First 20 for logging
        }

    except Exception as e:
        logger.error(f"EasyOCR-guided test failed: {e}")
        return {"error": str(e)}


async def test_vlm_guided_sam3(image_path: str, output_dir: Path) -> dict:
    """Use VLM to describe annotations, then guide SAM3."""
    logger.info("\n=== Test 3: VLM-guided SAM3 ===")

    try:
        from app.services.vlm_service import label_zone_with_vlm

        # Read image bytes
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Ask VLM to describe annotation elements
        prompt = """Look at this educational diagram. Describe the annotations:
1. What text labels do you see?
2. Are there any leader lines (thin lines connecting text to diagram parts)?
3. Describe the visual appearance of these leader lines (color, style, direction).

Be specific about locations and visual characteristics."""

        logger.info("Asking VLM to describe annotations...")
        start = time.time()

        response = await label_zone_with_vlm(
            image_bytes=image_bytes,
            candidate_labels=[],
            prompt=prompt
        )
        elapsed = time.time() - start

        logger.info(f"VLM response ({elapsed:.1f}s):\n{response[:500]}...")

        # Save VLM analysis
        with open(output_dir / "vlm_analysis.txt", "w") as f:
            f.write(response)

        return {
            "vlm_analysis": response,
            "time": elapsed
        }

    except Exception as e:
        logger.error(f"VLM-guided test failed: {e}")
        return {"error": str(e)}


def test_hough_comparison(image_path: str, output_dir: Path) -> dict:
    """Compare with Hough line detection for baseline."""
    logger.info("\n=== Test 4: Hough Line Detection (Baseline) ===")

    try:
        from app.services.line_detection_service import HoughLineDetector

        detector = HoughLineDetector(
            min_line_length=30,
            max_line_gap=10,
            proximity_threshold=50
        )

        start = time.time()
        lines = detector.detect_lines(image_path)
        elapsed = time.time() - start

        lines_count = len(lines) if lines is not None else 0
        logger.info(f"Hough detected {lines_count} lines in {elapsed:.3f}s")

        # Visualize
        image = cv2.imread(image_path)
        vis = image.copy()

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imwrite(str(output_dir / "hough_all_lines.png"), vis)

        return {
            "lines_detected": lines_count,
            "time": elapsed
        }

    except Exception as e:
        logger.error(f"Hough comparison failed: {e}")
        return {"error": str(e)}


def test_combined_approach(image_path: str, output_dir: Path) -> dict:
    """Test combined EasyOCR + Hough (current best approach)."""
    logger.info("\n=== Test 5: Combined EasyOCR + Hough ===")

    try:
        import easyocr
        from app.services.line_detection_service import HoughLineDetector

        # 1. EasyOCR for text
        reader = easyocr.Reader(['en'], gpu=False)
        text_results = reader.readtext(image_path)

        text_boxes = []
        for bbox, text, conf in text_results:
            pts = np.array(bbox, dtype=np.float32)
            x_min, y_min = pts.min(axis=0)
            x_max, y_max = pts.max(axis=0)
            text_boxes.append({
                "x": int(x_min),
                "y": int(y_min),
                "width": int(x_max - x_min),
                "height": int(y_max - y_min),
                "text": text
            })

        # 2. Hough for lines
        detector = HoughLineDetector(
            min_line_length=30,
            max_line_gap=10,
            proximity_threshold=50
        )
        all_lines = detector.detect_lines(image_path)

        # 3. Filter lines near text
        filtered_lines = detector.filter_lines_near_text(
            list(all_lines) if all_lines is not None else [],
            text_boxes,
            max_distance=60
        )

        logger.info(f"Text regions: {len(text_boxes)}")
        logger.info(f"All Hough lines: {len(all_lines) if all_lines is not None else 0}")
        logger.info(f"Filtered lines: {len(filtered_lines)}")

        # Visualize
        image = cv2.imread(image_path)
        vis = image.copy()

        # Draw text boxes in blue
        for box in text_boxes:
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]
            cv2.rectangle(vis, (x, y), (x+w, y+h), (255, 0, 0), 2)

        # Draw filtered lines in green
        for line in filtered_lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imwrite(str(output_dir / "combined_detection.png"), vis)

        return {
            "text_regions": len(text_boxes),
            "total_lines": len(all_lines) if all_lines is not None else 0,
            "filtered_lines": len(filtered_lines)
        }

    except Exception as e:
        logger.error(f"Combined approach failed: {e}")
        return {"error": str(e)}


async def main():
    parser = argparse.ArgumentParser(description="Test SAM3 for leader line detection")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--output-dir", default="/tmp/sam3_tests", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing on: {args.image}")
    logger.info(f"Output dir: {output_dir}")

    # Run all tests
    results = {}

    # Test 1: SAM3 text prompts
    results["sam3_text"] = test_sam3_text_prompts(args.image, output_dir)

    # Test 2: EasyOCR-guided
    results["easyocr_guided"] = test_easyocr_guided_sam3(args.image, output_dir)

    # Test 3: VLM-guided
    results["vlm_guided"] = await test_vlm_guided_sam3(args.image, output_dir)

    # Test 4: Hough baseline
    results["hough"] = test_hough_comparison(args.image, output_dir)

    # Test 5: Combined approach
    results["combined"] = test_combined_approach(args.image, output_dir)

    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)

    for test_name, test_results in results.items():
        if "error" in test_results:
            logger.info(f"{test_name}: FAILED - {test_results['error']}")
        else:
            logger.info(f"{test_name}: {test_results}")

    logger.info(f"\nResults saved to: {output_dir}")
    logger.info("Open images to compare detection quality:")
    for f in output_dir.glob("*.png"):
        logger.info(f"  - {f.name}")


if __name__ == "__main__":
    asyncio.run(main())
