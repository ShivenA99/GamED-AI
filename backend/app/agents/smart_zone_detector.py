# =============================================================================
# EXPERIMENTAL: This agent is not in the production pipeline.
#   - Alternative approach using SAM3 + CLIP (production uses qwen_sam_zone_detector.py)
#
# Kept for experimentation. Not included in the production pipeline graph.
# See DEPRECATED.md for details.
# =============================================================================

"""
Smart Zone Detector Agent (EXPERIMENTAL)

Detects zones in cleaned diagrams using SAM3 auto-segmentation and labels them
using CLIP with canonical labels from domain knowledge.

This approach:
1. Uses SAM3 to automatically segment the diagram into distinct regions
2. Uses CLIP to match each region to canonical labels semantically
3. Falls back to grid zones if SAM3 isn't available
4. Falls back to VLM labeling if CLIP isn't available

Inputs:
    cleaned_image_path: Path to the cleaned diagram (from smart_inpainter)
    domain_knowledge: Dict containing 'canonical_labels' list
    game_plan: Dict containing 'required_labels' (alternative source)

Outputs:
    diagram_zones: List of zones with id, label, x, y, radius, confidence
    diagram_labels: List of labels for the game template
    zone_detection_method: Method used ("sam3_clip", "sam3_vlm", "grid_clip", "grid_vlm")
"""

import os

from app.utils.logging_config import get_logger
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.sam3_zone_service import get_sam_detector, create_grid_zones
from app.services.clip_labeling_service import get_clip_labeler

logger = get_logger("gamed_ai.agents.smart_zone_detector")


def _slugify(value: str) -> str:
    """Convert string to slug for zone IDs."""
    return re.sub(r"[^a-z0-9]+", value.lower(), "_").strip("_")


def _convert_zones_to_pipeline_format(
    zones: List[Dict[str, Any]],
    image_shape: Tuple[int, int]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Convert detected zones to the pipeline's expected format.

    The pipeline expects:
    - diagram_zones: List of {id, label, x, y, radius, confidence}
    - diagram_labels: List of {id, text, correctZoneId}

    Where x, y are percentages (0-100) of image dimensions.
    """
    h, w = image_shape
    diagram_zones = []
    diagram_labels = []
    used_ids = set()

    for zone in zones:
        bbox = zone.get("bbox", {})
        label = zone.get("label", "unknown")

        # Calculate center as percentage
        center_x = (bbox.get("x", 0) + bbox.get("width", 0) / 2) / w * 100
        center_y = (bbox.get("y", 0) + bbox.get("height", 0) / 2) / h * 100

        # Calculate radius from bbox
        radius = max(bbox.get("width", 0), bbox.get("height", 0)) / max(w, h) * 50
        radius = max(5, min(15, radius))  # Clamp to reasonable size

        # Generate unique ID
        base_id = _slugify(label) or f"zone_{len(diagram_zones)+1}"
        zone_id = base_id
        counter = 1
        while zone_id in used_ids:
            zone_id = f"{base_id}_{counter}"
            counter += 1
        used_ids.add(zone_id)

        diagram_zones.append({
            "id": zone_id,
            "label": label,
            "x": round(center_x, 2),
            "y": round(center_y, 2),
            "radius": round(radius, 2),
            "confidence": zone.get("label_confidence", zone.get("confidence", 0.8)),
            "source": zone.get("source", "sam3_clip")
        })

        diagram_labels.append({
            "id": f"label_{zone_id}",
            "text": label,
            "correctZoneId": zone_id
        })

    return diagram_zones, diagram_labels


def _add_fallback_zones(
    diagram_zones: List[Dict],
    diagram_labels: List[Dict],
    missing_labels: List[str],
    image_shape: Tuple[int, int]
) -> Tuple[List[Dict], List[Dict]]:
    """Add fallback zones for missing labels using circular arrangement."""
    import math

    existing_count = len(diagram_zones)
    used_ids = {z["id"] for z in diagram_zones}
    total = existing_count + len(missing_labels)

    for i, label in enumerate(missing_labels):
        # Arrange in a circle
        if total == 1:
            center_x, center_y = 50, 50
        else:
            angle = (2 * math.pi * (existing_count + i)) / total
            radius = 30  # Distance from center as percentage
            center_x = 50 + radius * math.cos(angle)
            center_y = 50 + radius * math.sin(angle)

        base_id = _slugify(label) or f"zone_{existing_count + i + 1}"
        zone_id = base_id
        counter = 1
        while zone_id in used_ids:
            zone_id = f"{base_id}_{counter}"
            counter += 1
        used_ids.add(zone_id)

        diagram_zones.append({
            "id": zone_id,
            "label": label,
            "x": round(center_x, 2),
            "y": round(center_y, 2),
            "radius": 5.0,
            "confidence": 0.3,
            "source": "fallback"
        })

        diagram_labels.append({
            "id": f"label_{zone_id}",
            "text": label,
            "correctZoneId": zone_id
        })

        logger.warning(f"Added fallback zone for missing label: '{label}'")

    return diagram_zones, diagram_labels


async def smart_zone_detector(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Detect and label zones in a cleaned diagram.

    Uses SAM3 for zone detection and CLIP for labeling with canonical labels.
    Falls back to grid zones and/or VLM labeling if needed.
    """
    logger.info("=== SMART ZONE DETECTOR STARTING ===")
    start_time = time.time()

    # Skip if not INTERACTIVE_DIAGRAM template
    template_type = state.get("template_selection", {}).get("template_type", "")
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping zone detection: template_type={template_type}")
        return {
            "current_agent": "smart_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    # Get image path - prefer cleaned, fall back to original
    cleaned_path = state.get("cleaned_image_path")
    diagram_image = state.get("diagram_image", {}) or {}
    original_path = diagram_image.get("local_path")

    image_path = cleaned_path or original_path

    if not image_path or not Path(image_path).exists():
        logger.error(f"No image available for zone detection: {image_path}")
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_error": "No image available",
            "current_agent": "smart_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    logger.info(f"Detecting zones in: {image_path}")

    # Get canonical labels from domain knowledge or game plan
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    game_plan = state.get("game_plan", {}) or {}

    canonical_labels = game_plan.get("required_labels") or []
    if not canonical_labels:
        canonical_labels = domain_knowledge.get("canonical_labels", []) or []

    if not canonical_labels:
        logger.warning("No canonical labels available - zones will be unlabeled")

    logger.info(f"Canonical labels ({len(canonical_labels)}): {canonical_labels}")

    # Load image
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        logger.error(f"Could not load image: {image_path}")
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_error": f"Could not load image: {image_path}",
            "current_agent": "smart_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)
    image_shape = image_bgr.shape[:2]

    fallback_used = False
    fallback_reason = None
    detection_method = "sam3_clip"

    # Step 1: Detect zones using SAM3 or grid fallback
    sam_detector = get_sam_detector()
    zones = []

    try:
        if await sam_detector.is_available():
            logger.info("Using SAM3 for zone detection")
            zones = sam_detector.detect_zones(image_rgb)

            # Filter by size (exclude very small and very large zones)
            zones = sam_detector.filter_by_size(zones, image_shape)

            logger.info(f"SAM3 detected {len(zones)} zones")
        else:
            raise RuntimeError("SAM3 model not available")

    except Exception as e:
        logger.warning(f"SAM3 zone detection failed: {e}")
        logger.info("Falling back to grid zones")

        # Create grid zones
        rows = int(os.getenv("GRID_ZONE_ROWS", "3"))
        cols = int(os.getenv("GRID_ZONE_COLS", "3"))
        zones = create_grid_zones(image_shape, rows=rows, cols=cols)

        detection_method = detection_method.replace("sam3", "grid")
        fallback_used = True
        fallback_reason = f"SAM3 failed: {e}"

    if not zones:
        # Last resort: create grid zones
        zones = create_grid_zones(image_shape)
        detection_method = detection_method.replace("sam3", "grid")

    # Step 2: Label zones using CLIP or VLM
    if canonical_labels:
        try:
            clip_labeler = get_clip_labeler()

            if await clip_labeler.is_available():
                logger.info("Using CLIP for zone labeling")

                labeled_zones, missing = clip_labeler.label_zones_with_fallback(
                    pil_image, zones, canonical_labels
                )

                zones = labeled_zones
                logger.info(f"CLIP labeled {len(zones)} zones, {len(missing)} missing")

            else:
                raise RuntimeError("CLIP model not available")

        except Exception as e:
            logger.warning(f"CLIP labeling failed: {e}")
            logger.info("Falling back to VLM labeling")

            # Try VLM-based labeling
            try:
                zones = await _label_zones_with_vlm(image_path, zones, canonical_labels)
                detection_method = detection_method.replace("clip", "vlm")
            except Exception as vlm_error:
                logger.warning(f"VLM labeling also failed: {vlm_error}")
                # Zones will remain unlabeled
                for zone in zones:
                    zone["label"] = "unknown"
                    zone["label_confidence"] = 0.0

            if not fallback_used:
                fallback_used = True
                fallback_reason = f"CLIP failed: {e}"

    # Step 3: Convert to pipeline format
    diagram_zones, diagram_labels = _convert_zones_to_pipeline_format(zones, image_shape)

    # Step 4: Check for missing labels and add fallback zones
    if canonical_labels:
        found_labels = {z["label"].lower() for z in diagram_zones}
        required_set = {l.lower() for l in canonical_labels}
        missing_labels = [l for l in canonical_labels if l.lower() not in found_labels]

        if missing_labels:
            logger.warning(f"Missing {len(missing_labels)} labels: {missing_labels}")
            diagram_zones, diagram_labels = _add_fallback_zones(
                diagram_zones, diagram_labels, missing_labels, image_shape
            )

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"Zone detection complete in {latency_ms}ms using {detection_method}: "
        f"{len(diagram_zones)} zones, {len(diagram_labels)} labels"
    )

    # Track metrics if context available
    if ctx:
        ctx.set_llm_metrics(
            model=detection_method,
            latency_ms=latency_ms
        )
        if fallback_used:
            ctx.set_fallback_used(fallback_reason)

    result = {
        "diagram_zones": diagram_zones,
        "diagram_labels": diagram_labels,
        "zone_detection_method": detection_method,
        "retry_image_search": False,
        "image_search_attempts": state.get("image_search_attempts", 0),
        "current_agent": "smart_zone_detector",
        "last_updated_at": datetime.utcnow().isoformat()
    }

    if fallback_used:
        result["_used_fallback"] = True
        result["_fallback_reason"] = fallback_reason

    return result


async def _label_zones_with_vlm(
    image_path: str,
    zones: List[Dict[str, Any]],
    canonical_labels: List[str]
) -> List[Dict[str, Any]]:
    """
    Label zones using VLM (LLaVA) as fallback when CLIP isn't available.

    This is slower but can work without the CLIP model.
    """
    from app.services.vlm_service import label_zone_with_vlm

    image_bytes = Path(image_path).read_bytes()

    labeled_zones = []
    for zone in zones:
        try:
            prompt = (
                f"Look at this region of a scientific diagram. "
                f"Which of these labels best describes it: {', '.join(canonical_labels)}? "
                f"Reply with just the label name."
            )

            response = await label_zone_with_vlm(
                image_bytes=image_bytes,
                candidate_labels=canonical_labels,
                prompt=prompt
            )

            # Find best matching label from response
            response_lower = response.lower()
            best_label = None
            best_match_len = 0

            for label in canonical_labels:
                if label.lower() in response_lower:
                    if len(label) > best_match_len:
                        best_label = label
                        best_match_len = len(label)

            labeled_zone = zone.copy()
            labeled_zone["label"] = best_label or "unknown"
            labeled_zone["label_confidence"] = 0.7 if best_label else 0.3
            labeled_zones.append(labeled_zone)

        except Exception as e:
            logger.warning(f"VLM labeling failed for zone {zone.get('id')}: {e}")
            labeled_zone = zone.copy()
            labeled_zone["label"] = "unknown"
            labeled_zone["label_confidence"] = 0.0
            labeled_zones.append(labeled_zone)

    return labeled_zones
