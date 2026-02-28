# =============================================================================
# DEPRECATED: This agent has been superseded by:
#   - qwen_sam_zone_detector.py (combines SAM3 segmentation + Qwen VL labeling)
#
# Kept for reference. Not included in the production pipeline graph.
# See DEPRECATED.md for details.
# =============================================================================

"""
Qwen2.5-VL Zone Detector Agent (DEPRECATED)

Uses Qwen2.5-VL vision-language model to detect and label diagram zones
using PER-LABEL detection for maximum accuracy.

Strategy: For each required label from domain_knowledge, ask "where is X?"
This is MORE ACCURATE than asking "what zones do you see?" because:
1. We already know the exact labels we need (from domain_knowledge.canonical_labels)
2. We can ask precisely about each component
3. No ambiguity in matching detected zones to required labels

This agent replaces the 3-agent pipeline:
- sam3_prompt_generator
- diagram_image_segmenter
- diagram_zone_labeler
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.qwen_vl_service import get_qwen_vl_service, QwenVLError
from app.services.vlm_service import label_zone_with_vlm, VLMError
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.qwen_zone_detector")


def _slugify(value: str) -> str:
    """Convert string to slug for zone IDs."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


async def qwen_zone_detector_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Detect and label zones in CLEANED diagram using Qwen2.5-VL per-label detection.

    This agent:
    1. Gets required labels from domain_knowledge or game_plan
    2. For EACH label, asks Qwen2.5-VL "where is {label}?"
    3. Collects precise coordinates for each required label
    4. Falls back to LLaVA if Qwen unavailable

    Inputs:
        cleaned_image_path: Path to cleaned diagram (from qwen_label_remover)
        diagram_image: Original diagram info (fallback)
        domain_knowledge: Contains canonical_labels for matching
        game_plan: Contains required_labels

    Outputs:
        diagram_zones: List of zones with id, label, x, y, radius
        diagram_labels: List of labels with id, text, correctZoneId
    """
    logger.info("=== QWEN ZONE DETECTOR STARTING ===")

    # Skip if not INTERACTIVE_DIAGRAM
    template_type = state.get("template_selection", {}).get("template_type", "")
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping zone detection: template_type={template_type}")
        return {
            "current_agent": "qwen_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    # Get image path - prefer cleaned, fall back to original
    cleaned_image_path = state.get("cleaned_image_path")
    diagram_image = state.get("diagram_image", {}) or {}
    local_path = diagram_image.get("local_path")

    image_path = cleaned_image_path or local_path
    if not image_path or not Path(image_path).exists():
        # Try to construct path from question_id
        question_id = state.get("question_id", "unknown")
        fallback_path = (
            Path(__file__).parent.parent.parent /
            "pipeline_outputs" / "assets" / question_id / "diagram.jpg"
        )
        if fallback_path.exists():
            image_path = str(fallback_path)
        else:
            logger.error("No image available for zone detection")
            return {
                "diagram_zones": [],
                "diagram_labels": [],
                "zone_detection_error": "No image available",
                "current_agent": "qwen_zone_detector",
                "last_updated_at": datetime.utcnow().isoformat()
            }

    logger.info(f"Using image for zone detection: {image_path}")

    # Get required labels from game_plan or domain_knowledge
    game_plan = state.get("game_plan", {}) or {}
    domain_knowledge = state.get("domain_knowledge", {}) or {}

    required_labels = game_plan.get("required_labels") or []
    if not required_labels:
        required_labels = domain_knowledge.get("canonical_labels", []) or []

    if not required_labels:
        logger.error("No required labels for zone detection")
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_error": "No required labels",
            "current_agent": "qwen_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    logger.info(f"Required labels ({len(required_labels)}): {required_labels}")

    start_time = time.time()
    fallback_used = False
    fallback_reason = None

    try:
        # Try Qwen2.5-VL for per-label zone detection
        qwen_service = get_qwen_vl_service()

        if await qwen_service.is_available():
            logger.info("Using Qwen2.5-VL for PER-LABEL zone detection")

            # Per-label detection: ask about each label individually
            detection_result = await qwen_service.detect_zones_per_label(
                image_path,
                required_labels,
                parallel=False  # Sequential is more reliable
            )

            detected_zones = detection_result.get("detected_zones", [])
            missing_labels = detection_result.get("missing", [])

            if ctx:
                ctx.set_llm_metrics(
                    model=detection_result.get("model", "qwen2.5vl"),
                    latency_ms=detection_result.get("latency_ms")
                )

            logger.info(
                f"Qwen per-label detection: {len(detected_zones)} found, "
                f"{len(missing_labels)} missing"
            )

        else:
            # Fall back to LLaVA-based detection
            logger.warning("Qwen VL not available, falling back to LLaVA")
            fallback_used = True
            fallback_reason = "Qwen VL model not available"

            detected_zones = await _detect_zones_with_llava(
                image_path, required_labels
            )
            missing_labels = []

            logger.info(f"LLaVA detected {len(detected_zones)} zones")

        # Convert detected zones to pipeline format
        diagram_zones, diagram_labels = _convert_zones_to_pipeline_format(
            detected_zones, image_path
        )

        # Validate coverage
        found_labels = {z["label"].lower() for z in diagram_zones}
        required_set = {l.lower() for l in required_labels}
        actual_missing = required_set - found_labels

        if actual_missing:
            logger.warning(
                f"Missing {len(actual_missing)} required labels: {list(actual_missing)}"
            )
            # Add fallback zones for missing labels
            diagram_zones, diagram_labels = _add_fallback_zones(
                diagram_zones, diagram_labels, list(actual_missing), image_path
            )

        total_latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Zone detection complete in {total_latency_ms}ms. "
            f"Final: {len(diagram_zones)} zones, {len(diagram_labels)} labels."
        )

        # Handle image search retry logic (for compatibility with existing pipeline)
        image_search_attempts = state.get("image_search_attempts", 0)
        max_image_attempts = state.get("max_image_attempts", 3)
        retry_image_search = False

        # Only retry if we're still missing labels after detection AND fallback
        final_found = {z["label"].lower() for z in diagram_zones}
        final_missing = required_set - final_found

        if final_missing and image_search_attempts < max_image_attempts - 1:
            retry_image_search = True
            image_search_attempts += 1
            logger.warning(
                f"Still missing {len(final_missing)} labels after fallback, will retry image search "
                f"(attempt {image_search_attempts + 1}/{max_image_attempts})"
            )

        result = {
            "diagram_zones": diagram_zones,
            "diagram_labels": diagram_labels,
            "retry_image_search": retry_image_search,
            "image_search_attempts": image_search_attempts,
            "current_agent": "qwen_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

        if fallback_used:
            result["_used_fallback"] = True
            result["_fallback_reason"] = fallback_reason
            if ctx:
                ctx.set_fallback_used(fallback_reason)

        return result

    except QwenVLError as e:
        logger.error(f"Qwen VL error: {e}")
        return await _fallback_to_llava(state, ctx, image_path, required_labels, str(e))

    except Exception as e:
        logger.error(f"Zone detection failed: {e}", exc_info=True)
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_error": str(e),
            "_used_fallback": True,
            "_fallback_reason": f"Zone detection failed: {e}",
            "current_agent": "qwen_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }


async def _detect_zones_with_llava(
    image_path: str,
    required_labels: List[str]
) -> List[Dict[str, Any]]:
    """
    Fallback zone detection using LLaVA via existing VLM service.

    Uses per-label detection strategy: ask about each label individually.
    """
    from PIL import Image

    # Load image dimensions
    try:
        img = Image.open(image_path)
        width, height = img.size
    except Exception:
        width, height = 800, 600

    detected_zones = []
    image_bytes = Path(image_path).read_bytes()

    for i, label in enumerate(required_labels):
        try:
            logger.info(f"LLaVA detecting {i+1}/{len(required_labels)}: '{label}'")

            prompt = (
                f"Look at this scientific/educational diagram image carefully.\n\n"
                f"Find the location of '{label}' in this diagram.\n\n"
                f"Describe the position using these terms:\n"
                f"- Vertical: top, upper, middle, lower, bottom\n"
                f"- Horizontal: left, center, right\n\n"
                f"Example response: 'The {label} is in the upper-left area of the image.'\n\n"
                f"Be specific about where '{label}' is located."
            )

            response = await label_zone_with_vlm(
                image_bytes=image_bytes,
                candidate_labels=required_labels,
                prompt=prompt
            )

            # Parse position from response
            x, y = _parse_position_from_response(response, width, height)

            # Convert to normalized coordinates (0-1000)
            center_x = int(x * 1000 / width)
            center_y = int(y * 1000 / height)

            detected_zones.append({
                "found": True,
                "label": label,
                "bbox": [center_x - 50, center_y - 50, center_x + 50, center_y + 50],
                "center": [center_x, center_y],
                "confidence": 0.7,
                "id": f"zone_{_slugify(label)}",
                "source": "llava"
            })

            logger.info(f"  Found '{label}' at ({center_x}, {center_y})")

        except (VLMError, Exception) as e:
            logger.warning(f"LLaVA detection failed for '{label}': {e}")
            # Create fallback zone for this label
            bbox = _get_default_bbox(i, len(required_labels))
            center_x = (bbox[0] + bbox[2]) // 2
            center_y = (bbox[1] + bbox[3]) // 2

            detected_zones.append({
                "found": True,
                "label": label,
                "bbox": bbox,
                "center": [center_x, center_y],
                "confidence": 0.3,
                "id": f"zone_{_slugify(label)}",
                "source": "fallback"
            })

    return detected_zones


def _parse_position_from_response(
    response: str,
    width: int,
    height: int
) -> tuple:
    """Parse approximate position from VLM response."""
    response_lower = response.lower()

    # Determine Y position (more granular)
    if "top" in response_lower and "upper" in response_lower:
        y = height * 0.15
    elif "top" in response_lower:
        y = height * 0.2
    elif "upper" in response_lower:
        y = height * 0.3
    elif "bottom" in response_lower and "lower" in response_lower:
        y = height * 0.85
    elif "bottom" in response_lower:
        y = height * 0.8
    elif "lower" in response_lower:
        y = height * 0.7
    elif "middle" in response_lower or "center" in response_lower:
        y = height * 0.5
    else:
        y = height * 0.5

    # Determine X position (more granular)
    if "far left" in response_lower:
        x = width * 0.1
    elif "left" in response_lower:
        x = width * 0.25
    elif "far right" in response_lower:
        x = width * 0.9
    elif "right" in response_lower:
        x = width * 0.75
    elif "center" in response_lower or "middle" in response_lower:
        x = width * 0.5
    else:
        x = width * 0.5

    return (x, y)


def _get_default_bbox(index: int, total: int) -> List[int]:
    """Generate default bounding box for fallback zones in a grid pattern."""
    # Use a circular arrangement for better distribution
    import math

    if total == 1:
        return [450, 450, 550, 550]  # Center

    # Arrange in a circle
    angle = (2 * math.pi * index) / total
    radius = 300  # Distance from center

    center_x = 500 + int(radius * math.cos(angle))
    center_y = 500 + int(radius * math.sin(angle))

    return [center_x - 50, center_y - 50, center_x + 50, center_y + 50]


def _convert_zones_to_pipeline_format(
    detected_zones: List[Dict[str, Any]],
    image_path: str
) -> tuple:
    """
    Convert detected zones to pipeline format (diagram_zones, diagram_labels).

    The detected_zones already have labels from per-label detection,
    so we just need to convert the format.
    """
    diagram_zones = []
    diagram_labels = []
    used_zone_ids = set()

    for zone in detected_zones:
        if not zone.get("found", True):
            continue  # Skip zones marked as not found

        label = zone.get("label", "unknown")
        bbox = zone.get("bbox", [500, 500, 600, 600])
        center = zone.get("center")

        # Convert normalized coords (0-1000) to percentage (0-100)
        if center and len(center) == 2:
            center_x = center[0] / 10  # 0-1000 → 0-100
            center_y = center[1] / 10
        else:
            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2 / 10
            center_y = (y1 + y2) / 2 / 10

        # Compute radius from bbox size
        x1, y1, x2, y2 = bbox
        w = (x2 - x1) / 10
        h = (y2 - y1) / 10
        radius = max(w, h) / 2
        radius = max(5, min(15, radius))  # Clamp to reasonable size

        # Generate unique zone ID
        base_id = _slugify(label) or f"zone_{len(diagram_zones)+1}"
        zone_id = base_id
        counter = 1
        while zone_id in used_zone_ids:
            zone_id = f"{base_id}_{counter}"
            counter += 1
        used_zone_ids.add(zone_id)

        diagram_zones.append({
            "id": zone_id,
            "label": label,
            "x": round(center_x, 2),
            "y": round(center_y, 2),
            "radius": round(radius, 2),
            "confidence": zone.get("confidence", 0.8),
            "source": zone.get("source", "qwen_vl")
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
    image_path: str
) -> tuple:
    """Add fallback zones for missing labels using grid distribution."""
    existing_count = len(diagram_zones)
    used_zone_ids = {z["id"] for z in diagram_zones}

    for i, label in enumerate(missing_labels):
        # Create zone using circular arrangement for remaining labels
        bbox = _get_default_bbox(existing_count + i, existing_count + len(missing_labels))

        center_x = (bbox[0] + bbox[2]) / 2 / 10
        center_y = (bbox[1] + bbox[3]) / 2 / 10
        radius = 5.0  # Default radius

        base_id = _slugify(label) or f"zone_{existing_count + i + 1}"
        zone_id = base_id
        counter = 1
        while zone_id in used_zone_ids:
            zone_id = f"{base_id}_{counter}"
            counter += 1
        used_zone_ids.add(zone_id)

        diagram_zones.append({
            "id": zone_id,
            "label": label,
            "x": round(center_x, 2),
            "y": round(center_y, 2),
            "radius": round(radius, 2),
            "confidence": 0.3,
            "source": "fallback"
        })

        diagram_labels.append({
            "id": f"label_{zone_id}",
            "text": label,
            "correctZoneId": zone_id
        })

        logger.warning(f"Added fallback zone for missing label: '{label}' at ({center_x:.1f}%, {center_y:.1f}%)")

    return diagram_zones, diagram_labels


async def _fallback_to_llava(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext],
    image_path: str,
    required_labels: List[str],
    error_reason: str
) -> dict:
    """Complete fallback to LLaVA when Qwen fails."""
    logger.warning(f"Complete fallback to LLaVA: {error_reason}")

    try:
        detected_zones = await _detect_zones_with_llava(image_path, required_labels)
        diagram_zones, diagram_labels = _convert_zones_to_pipeline_format(
            detected_zones, image_path
        )

        if ctx:
            ctx.set_fallback_used(f"LLaVA fallback: {error_reason}")

        return {
            "diagram_zones": diagram_zones,
            "diagram_labels": diagram_labels,
            "retry_image_search": False,
            "image_search_attempts": state.get("image_search_attempts", 0),
            "_used_fallback": True,
            "_fallback_reason": f"LLaVA fallback: {error_reason}",
            "current_agent": "qwen_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    except Exception as e2:
        logger.error(f"LLaVA fallback also failed: {e2}")
        # Last resort: create fallback zones for all labels
        diagram_zones = []
        diagram_labels = []

        for i, label in enumerate(required_labels):
            bbox = _get_default_bbox(i, len(required_labels))
            center_x = (bbox[0] + bbox[2]) / 2 / 10
            center_y = (bbox[1] + bbox[3]) / 2 / 10
            zone_id = _slugify(label) or f"zone_{i+1}"

            diagram_zones.append({
                "id": zone_id,
                "label": label,
                "x": round(center_x, 2),
                "y": round(center_y, 2),
                "radius": 5.0,
                "confidence": 0.2,
                "source": "grid_fallback"
            })

            diagram_labels.append({
                "id": f"label_{zone_id}",
                "text": label,
                "correctZoneId": zone_id
            })

        return {
            "diagram_zones": diagram_zones,
            "diagram_labels": diagram_labels,
            "zone_detection_error": f"All methods failed, using grid fallback: {error_reason}; {e2}",
            "_used_fallback": True,
            "_fallback_reason": "All methods failed - grid fallback",
            "current_agent": "qwen_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat()
        }
