# =============================================================================
# EXPERIMENTAL: This agent is not in the production pipeline.
#   - Alternative approach using EasyOCR + Hough Transform
#   - Production uses qwen_annotation_detector.py instead
#
# Kept for experimentation. Not included in the production pipeline graph.
# See DEPRECATED.md for details.
# =============================================================================

"""
Combined Label Detector Agent (EXPERIMENTAL)

Combines EasyOCR (text detection) + Hough Transform (line detection) + optional
CLIP filtering for comprehensive detection of labels and leader lines in
educational diagrams.

This agent replaces the Qwen-based detection approach which suffered from
timeouts and incomplete line detection. The new approach:
1. Uses EasyOCR for fast, reliable text detection
2. Uses Hough Transform for geometric line detection
3. Filters lines by proximity to text boxes (leader lines connect labels)
4. Optionally uses CLIP to filter false positives (annotation vs. diagram content)
5. Applies morphological cleanup to create a clean combined mask

Inputs:
    diagram_image: Dict with 'local_path' to the diagram image

Outputs:
    detection_mask_path: Path to the combined binary mask
    text_boxes_count: Number of text regions detected
    lines_detected: Number of leader lines detected
    detection_method: Method used ("easyocr_hough" or "easyocr_hough_clip")
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.line_detection_service import get_line_detector, HoughLineDetector
from app.services.clip_filtering_service import get_clip_filter, is_clip_filter_enabled
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.combined_label_detector")


def _get_easyocr_service():
    """Get EasyOCR service (lazy import to avoid loading if not needed)."""
    try:
        import easyocr
        return easyocr.Reader(['en'], gpu=False)
    except ImportError:
        logger.error("EasyOCR not installed. Install with: pip install easyocr")
        raise


def _detect_text_regions(image_path: str) -> List[Dict[str, Any]]:
    """
    Detect text regions using EasyOCR.

    Returns list of text regions with bbox and content.
    """
    reader = _get_easyocr_service()

    results = reader.readtext(image_path)

    text_regions = []
    for detection in results:
        bbox_points, text, confidence = detection

        # Convert polygon to bounding box
        # bbox_points is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
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
            },
            "polygon": bbox_points
        })

    logger.info(f"EasyOCR detected {len(text_regions)} text regions")
    return text_regions


def _create_text_mask(
    image_shape: tuple,
    text_regions: List[Dict[str, Any]],
    padding: int = 10
) -> np.ndarray:
    """Create binary mask from text bounding boxes."""
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    for region in text_regions:
        bbox = region["bbox"]
        x = max(0, bbox["x"] - padding)
        y = max(0, bbox["y"] - padding)
        x2 = min(w, bbox["x"] + bbox["width"] + padding)
        y2 = min(h, bbox["y"] + bbox["height"] + padding)

        cv2.rectangle(mask, (x, y), (x2, y2), 255, -1)

    return mask


def _combine_masks(
    text_mask: np.ndarray,
    line_mask: np.ndarray,
    kernel_size: int = 5,
    dilate_iterations: int = 2
) -> np.ndarray:
    """
    Combine text and line masks with morphological cleanup.

    The cleanup:
    1. Union the masks
    2. Dilate to connect nearby segments
    3. Morphological closing to fill small gaps
    """
    # Combine masks
    combined = cv2.bitwise_or(text_mask, line_mask)

    # Dilate to connect nearby segments
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    combined = cv2.dilate(combined, kernel, iterations=dilate_iterations)

    # Morphological close to fill gaps
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

    return combined


def _save_mask(mask: np.ndarray, image_path: str, suffix: str = "_detection_mask") -> str:
    """Save mask to file next to the original image."""
    image_path = Path(image_path)
    mask_path = image_path.parent / f"{image_path.stem}{suffix}.png"
    cv2.imwrite(str(mask_path), mask)
    logger.info(f"Saved detection mask to {mask_path}")
    return str(mask_path)


async def combined_label_detector(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Detect text labels and leader lines in a diagram using combined approach.

    This agent combines:
    - EasyOCR for text detection (fast, reliable)
    - Hough Transform for line detection (geometric, no timeout)
    - Optional CLIP filtering (semantic, removes false positives)

    The output mask is used by the inpainting agent to remove annotations.
    """
    logger.info("=== COMBINED LABEL DETECTOR STARTING ===")
    start_time = time.time()

    # Skip if not INTERACTIVE_DIAGRAM template
    template_type = state.get("template_selection", {}).get("template_type", "")
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping detection: template_type={template_type}")
        return {
            "current_agent": "combined_label_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    # Get image path
    diagram_image = state.get("diagram_image", {}) or {}
    image_path = diagram_image.get("local_path")

    if not image_path or not Path(image_path).exists():
        logger.error(f"No image available for detection: {image_path}")
        return {
            "detection_mask_path": None,
            "text_boxes_count": 0,
            "lines_detected": 0,
            "detection_error": "No image available",
            "current_agent": "combined_label_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    logger.info(f"Processing image: {image_path}")

    # Load image for dimensions
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Could not load image: {image_path}")
        return {
            "detection_mask_path": None,
            "detection_error": f"Could not load image: {image_path}",
            "current_agent": "combined_label_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    image_shape = image.shape

    # Step 1: Detect text with EasyOCR
    try:
        text_regions = _detect_text_regions(image_path)
    except Exception as e:
        logger.error(f"EasyOCR failed: {e}")
        text_regions = []

    text_count = len(text_regions)
    logger.info(f"Step 1: Detected {text_count} text regions")

    # Step 2: Create text mask
    padding = int(os.getenv("TEXT_MASK_PADDING", "10"))
    text_mask = _create_text_mask(image_shape, text_regions, padding=padding)

    # Step 3: Detect lines with Hough Transform
    line_detector = get_line_detector()
    all_lines = line_detector.detect_lines(image_path)

    # Step 4: Filter lines by proximity to text (leader lines are near text)
    if all_lines is not None and len(text_regions) > 0:
        filtered_lines = line_detector.filter_lines_near_text(all_lines, text_regions)

        # Additional filtering by length and angle
        filtered_lines = line_detector.filter_by_length(filtered_lines, image_shape)
        filtered_lines = line_detector.filter_by_angle(filtered_lines)
    else:
        filtered_lines = []

    logger.info(f"Step 3-4: Detected {len(all_lines) if all_lines is not None else 0} total lines, "
                f"filtered to {len(filtered_lines)} leader lines")

    # Step 5: Optional CLIP filtering
    detection_method = "easyocr_hough"
    if is_clip_filter_enabled() and filtered_lines:
        try:
            clip_filter = get_clip_filter()
            threshold = float(os.getenv("CLIP_FILTER_THRESHOLD", "0.6"))
            filtered_lines = clip_filter.filter_hough_lines(
                image_path, filtered_lines, threshold=threshold
            )
            detection_method = "easyocr_hough_clip"
            logger.info(f"Step 5: CLIP filtered to {len(filtered_lines)} lines")
        except Exception as e:
            logger.warning(f"CLIP filtering failed (continuing without): {e}")

    lines_count = len(filtered_lines)

    # Step 6: Create line mask
    line_thickness = int(os.getenv("LINE_MASK_THICKNESS", "8"))
    line_mask = line_detector.create_mask(image_shape, filtered_lines, thickness=line_thickness)

    # Step 7: Combine masks with morphological cleanup
    combined_mask = _combine_masks(text_mask, line_mask)

    # Step 8: Save mask
    mask_path = _save_mask(combined_mask, image_path)

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"Combined detection complete in {latency_ms}ms: "
        f"{text_count} text regions, {lines_count} leader lines"
    )

    # Track metrics if context available
    if ctx:
        ctx.set_llm_metrics(
            model="easyocr+hough",
            latency_ms=latency_ms
        )

    return {
        "detection_mask_path": mask_path,
        "text_boxes_count": text_count,
        "lines_detected": lines_count,
        "text_regions": text_regions,  # Pass through for downstream use
        "detection_method": detection_method,
        "current_agent": "combined_label_detector",
        "last_updated_at": datetime.utcnow().isoformat()
    }
