"""
Qwen VLM + SAM3 Zone Detector Agent

Uses leader line endpoints for accurate zone detection:

The KEY INSIGHT: Leader lines point from text labels TO diagram structures.
The "end" point of each leader line is exactly where the anatomical structure is!

Workflow:
1. Get annotation_elements from previous step (text labels + leader lines)
2. Extract leader line endpoints (the "end" points where lines touch structures)
3. Match each endpoint to its canonical label (from the "connects_to" field)
4. Optionally use SAM3 to get precise segmentation around each point

This approach is more accurate than asking Qwen to locate structures because:
- Leader line endpoints directly indicate where structures are
- No need for Qwen to "guess" structure locations
- Works on both original and cleaned images

Inputs: annotation_elements (from qwen_annotation_detector), cleaned_image_path,
        diagram_image, domain_knowledge, game_plan
Outputs: diagram_zones, diagram_labels, zone_detection_method
"""

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import cv2
import numpy as np
from PIL import Image

from app.agents.state import (
    AgentState,
    ZoneEntity,
    EntityRegistry,
    create_empty_entity_registry,
)
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.qwen_sam_zone_detector")


# Zone size constraints (as percentage of image area)
MIN_ZONE_AREA_PERCENT = 0.5    # Minimum zone area (0.5% of image)
MAX_ZONE_AREA_PERCENT = 25.0   # Maximum zone area (25% of image)
MIN_ZONE_DIMENSION = 20        # Minimum zone dimension in pixels
MAX_ZONE_DIMENSION_RATIO = 0.4 # Maximum zone dimension as ratio of image

# Zone merging thresholds
ZONE_OVERLAP_THRESHOLD = 0.5   # IoU threshold for merging overlapping zones (raised from 0.3 to prevent aggressive merging)
ZONE_PROXIMITY_THRESHOLD = 0.05  # Distance threshold (as fraction of image size) for nearby zones


def _clamp_percentage(value: float) -> float:
    """Clamp a percentage value to 0-100 range."""
    return max(0.0, min(100.0, value))


def zones_to_entity_registry(
    zones: List[Dict],
    scene_number: int = 1,
    existing_registry: Optional[EntityRegistry] = None,
    detection_method: str = "qwen_sam",
) -> EntityRegistry:
    """
    Convert zone detection results to entity registry format.

    This creates ZoneEntity entries and populates the registry's zones dict
    and scene_zones relationship map.

    Args:
        zones: List of zone dicts from detection
        scene_number: Scene number for multi-scene games
        existing_registry: Optional existing registry to merge into
        detection_method: Source method for tracking

    Returns:
        Updated EntityRegistry with zones populated
    """
    # Start with existing registry or create new one
    registry = existing_registry or create_empty_entity_registry()

    # Ensure zones dict exists
    if registry.get("zones") is None:
        registry["zones"] = {}
    if registry.get("scene_zones") is None:
        registry["scene_zones"] = {}

    scene_zone_ids = []

    for zone in zones:
        zone_id = zone.get("id", f"zone_{len(registry['zones'])}")
        label = zone.get("label", "")

        # Determine shape and coordinates based on zone format
        shape = zone.get("shape", "circle")
        bbox = zone.get("bbox", {})

        if shape == "polygon" and zone.get("points"):
            coordinates = {
                "points": zone["points"],
                "center": zone.get("center", {"x": zone.get("x", 50), "y": zone.get("y", 50)}),
            }
        elif bbox:
            # Has bbox - can be used as rect or derive circle from it
            coordinates = {
                "x": zone.get("x", 50),
                "y": zone.get("y", 50),
                "radius": zone.get("radius", 5),
                "bbox": bbox,  # Include bbox for precise hit testing
            }
            shape = "circle"  # Qwen primarily uses circle zones
        else:
            # Default to circle
            shape = "circle"
            coordinates = {
                "x": zone.get("x", 50),
                "y": zone.get("y", 50),
                "radius": zone.get("radius", 5),
            }

        # Create ZoneEntity
        zone_entity: ZoneEntity = {
            "id": zone_id,
            "label": label,
            "shape": shape,
            "coordinates": coordinates,
            "parent_zone_id": None,  # Qwen detector doesn't handle hierarchy
            "scene_number": scene_number,
            "confidence": zone.get("confidence"),
            "source": zone.get("source", detection_method),
            "hierarchy_level": None,
            "hint": zone.get("hint"),
            "difficulty": zone.get("difficulty"),
        }

        # Add to registry
        registry["zones"][zone_id] = zone_entity
        scene_zone_ids.append(zone_id)

    # Update scene_zones relationship
    registry["scene_zones"][scene_number] = scene_zone_ids

    logger.info(
        f"Added {len(scene_zone_ids)} zones to entity registry for scene {scene_number}"
    )

    return registry


# Fallback prompt for locating a specific label in the diagram (when no leader line data)
LOCATE_LABEL_PROMPT = """Look at this educational/scientific diagram.

Find the EXACT location of "{label}" in this diagram.

"{label}" is one of the key anatomical/scientific parts. Locate the actual structure/component in the diagram, NOT the text label.

If you find "{label}", respond with:
{{
  "found": true,
  "label": "{label}",
  "center": [x, y],  // Center point of the component (0-1000 scale)
  "bbox": [x1, y1, x2, y2],  // Bounding box around the component
  "confidence": 0.95
}}

If you CANNOT find "{label}" in the diagram, respond:
{{
  "found": false,
  "label": "{label}",
  "reason": "explanation"
}}

IMPORTANT:
- Coordinates use 0-1000 normalized scale (0,0 is top-left)
- Look for the actual anatomical/scientific structure, not text
- The diagram may have had text labels removed, so focus on visual features
- Be precise with the center point - it should be inside the component

Return ONLY JSON, no other text."""


def fuzzy_match_label(detected_text: str, canonical_labels: List[str]) -> Optional[str]:
    """
    Match detected OCR text to canonical labels with fuzzy matching.

    Handles common OCR errors like:
    - Missing letters: "Stgma" -> "Stigma", "Stle" -> "Style"
    - Extra characters: "Anther-" -> "Anther"
    - Substitutions: "Filanent" -> "Filament"

    Args:
        detected_text: Text from OCR (may have errors)
        canonical_labels: List of correct canonical labels

    Returns:
        Matched canonical label or None
    """
    if not detected_text:
        return None

    # Clean detected text
    detected = detected_text.lower().strip().rstrip('-').rstrip(':')

    for canonical in canonical_labels:
        canonical_lower = canonical.lower().strip()

        # Exact match
        if detected == canonical_lower:
            return canonical

        # One contains the other
        if detected in canonical_lower or canonical_lower in detected:
            return canonical

        # Remove common suffixes/prefixes
        detected_clean = detected.replace(" ", "").replace("-", "").replace("_", "")
        canonical_clean = canonical_lower.replace(" ", "").replace("-", "").replace("_", "")

        if detected_clean == canonical_clean:
            return canonical

        # Calculate edit distance (simple Levenshtein)
        # Allow up to 2 character differences for short words, 3 for longer
        max_dist = 2 if len(canonical_lower) <= 6 else 3
        dist = _levenshtein_distance(detected_clean, canonical_clean)

        if dist <= max_dist:
            # Verify it's a reasonable match (first letter should match or be close)
            if detected_clean and canonical_clean:
                if (detected_clean[0] == canonical_clean[0] or
                    abs(ord(detected_clean[0]) - ord(canonical_clean[0])) <= 2):
                    return canonical

    return None


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Insertions, deletions, substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def extract_zones_from_leader_lines(
    annotations: List[Dict[str, Any]],
    canonical_labels: List[str],
    image_width: int,
    image_height: int
) -> Tuple[List[Dict], List[str]]:
    """
    Extract zone locations from leader line endpoints.

    The "end" point of each leader line is where the anatomical structure is.
    This is much more accurate than asking a VLM to locate structures.

    Args:
        annotations: List of annotation elements (text + lines)
        canonical_labels: Expected labels to find
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        Tuple of (zones list, missing labels list)
    """
    zones = []
    found_labels = set()

    # Build lookup of text labels and their positions
    text_annotations = [a for a in annotations if a.get("type") == "text"]
    line_annotations = [a for a in annotations if a.get("type") == "line"]

    logger.info(f"Extracting zones from {len(line_annotations)} leader lines")

    # Process each leader line
    for i, line in enumerate(line_annotations):
        connects_to = line.get("connects_to", "")
        end_point = line.get("end", [])
        direction = line.get("direction", "")

        if not connects_to or len(end_point) != 2:
            continue

        # Find matching canonical label using fuzzy matching
        matched_label = fuzzy_match_label(connects_to, canonical_labels)

        if matched_label:
            logger.debug(f"Fuzzy matched '{connects_to}' -> '{matched_label}'")

        if matched_label and matched_label not in found_labels:
            # The "end" point is in normalized 0-1000 coordinates
            # Convert to percentage (0-100) for zone format
            end_x = end_point[0] / 10  # 0-1000 -> 0-100%
            end_y = end_point[1] / 10

            # Convert to pixel coordinates for bbox
            end_px = int(end_point[0] * image_width / 1000)
            end_py = int(end_point[1] * image_height / 1000)

            # Create a small bbox around the endpoint
            # Leader line endpoints are typically at the edge of structures
            bbox_size_x = int(image_width * 0.08)  # 8% of image width
            bbox_size_y = int(image_height * 0.08)  # 8% of image height

            # Adjust bbox based on line direction
            if direction == "right":
                # Line came from left, so structure is to the right of endpoint
                bbox_x = end_px
                bbox_y = end_py - bbox_size_y // 2
            elif direction == "left":
                # Line came from right, so structure is to the left of endpoint
                bbox_x = end_px - bbox_size_x
                bbox_y = end_py - bbox_size_y // 2
            else:
                # Center the bbox on the endpoint
                bbox_x = end_px - bbox_size_x // 2
                bbox_y = end_py - bbox_size_y // 2

            # Clamp to image bounds
            bbox_x = max(0, min(bbox_x, image_width - bbox_size_x))
            bbox_y = max(0, min(bbox_y, image_height - bbox_size_y))

            # Calculate radius from bbox (use smaller dimension / 2, max 50)
            radius = min(min(bbox_size_x, bbox_size_y) / 2, 50)

            zones.append({
                "id": f"zone_{matched_label.lower().replace(' ', '_')}",  # Semantic ID like zone_pistil
                "label": matched_label,
                "x": _clamp_percentage(end_x),
                "y": _clamp_percentage(end_y),
                "radius": radius,  # Add radius for click detection
                "bbox": {
                    "x": bbox_x,
                    "y": bbox_y,
                    "width": bbox_size_x,
                    "height": bbox_size_y
                },
                "endpoint_px": [end_px, end_py],
                "confidence": 0.9,  # High confidence - direct from leader line
                "source": "leader_line_endpoint"
            })
            found_labels.add(matched_label)

            logger.debug(f"Zone from leader line: '{matched_label}' at ({end_x:.1f}%, {end_y:.1f}%)")

    # Find missing labels
    missing = [l for l in canonical_labels if l not in found_labels]

    logger.info(f"Extracted {len(zones)} zones from leader lines, {len(missing)} labels missing")

    return zones, missing


def _calculate_iou(bbox1: Dict, bbox2: Dict) -> float:
    """
    Calculate Intersection over Union for two bounding boxes.

    Args:
        bbox1: First bbox dict with x, y, width, height
        bbox2: Second bbox dict with x, y, width, height

    Returns:
        IoU value between 0 and 1
    """
    x1 = max(bbox1["x"], bbox2["x"])
    y1 = max(bbox1["y"], bbox2["y"])
    x2 = min(bbox1["x"] + bbox1["width"], bbox2["x"] + bbox2["width"])
    y2 = min(bbox1["y"] + bbox1["height"], bbox2["y"] + bbox2["height"])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = bbox1["width"] * bbox1["height"]
    area2 = bbox2["width"] * bbox2["height"]
    union = area1 + area2 - intersection

    if union == 0:
        return 0.0
    return intersection / union


def _merge_bboxes(bbox1: Dict, bbox2: Dict) -> Dict:
    """
    Merge two bounding boxes into their union.

    Args:
        bbox1: First bbox dict
        bbox2: Second bbox dict

    Returns:
        Merged bbox dict
    """
    x = min(bbox1["x"], bbox2["x"])
    y = min(bbox1["y"], bbox2["y"])
    x2 = max(bbox1["x"] + bbox1["width"], bbox2["x"] + bbox2["width"])
    y2 = max(bbox1["y"] + bbox1["height"], bbox2["y"] + bbox2["height"])

    return {
        "x": x,
        "y": y,
        "width": x2 - x,
        "height": y2 - y
    }


def _validate_zone_size(
    zone: Dict[str, Any],
    image_width: int,
    image_height: int
) -> Tuple[bool, str]:
    """
    Validate that a zone meets size constraints.

    Args:
        zone: Zone dict with bbox
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        Tuple of (is_valid, reason if invalid)
    """
    bbox = zone.get("bbox", {})
    zone_width = bbox.get("width", 0)
    zone_height = bbox.get("height", 0)
    zone_area = zone_width * zone_height
    image_area = image_width * image_height

    if image_area == 0:
        return True, ""

    area_percent = (zone_area / image_area) * 100

    # Check minimum size
    if zone_width < MIN_ZONE_DIMENSION or zone_height < MIN_ZONE_DIMENSION:
        return False, f"Zone too small: {zone_width}x{zone_height}px"

    if area_percent < MIN_ZONE_AREA_PERCENT:
        return False, f"Zone area {area_percent:.2f}% below minimum {MIN_ZONE_AREA_PERCENT}%"

    # Check maximum size
    if zone_width > image_width * MAX_ZONE_DIMENSION_RATIO:
        return False, f"Zone width {zone_width}px exceeds {MAX_ZONE_DIMENSION_RATIO*100}% of image"

    if zone_height > image_height * MAX_ZONE_DIMENSION_RATIO:
        return False, f"Zone height {zone_height}px exceeds {MAX_ZONE_DIMENSION_RATIO*100}% of image"

    if area_percent > MAX_ZONE_AREA_PERCENT:
        return False, f"Zone area {area_percent:.2f}% exceeds maximum {MAX_ZONE_AREA_PERCENT}%"

    return True, ""


def _merge_overlapping_zones(
    zones: List[Dict[str, Any]],
    image_width: int,
    image_height: int
) -> List[Dict[str, Any]]:
    """
    Merge overlapping zones to avoid over-segmentation.

    Zones with IoU above threshold are merged, keeping the label with higher confidence.

    Args:
        zones: List of zone dicts
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        List of merged zones
    """
    if len(zones) <= 1:
        return zones

    merged = []
    used = set()

    # Sort by confidence (descending) to prefer higher confidence zones
    sorted_zones = sorted(zones, key=lambda z: z.get("confidence", 0), reverse=True)

    for i, zone1 in enumerate(sorted_zones):
        if i in used:
            continue

        current_zone = zone1.copy()
        current_bbox = current_zone.get("bbox", {})

        # Find overlapping zones
        for j, zone2 in enumerate(sorted_zones[i + 1:], start=i + 1):
            if j in used:
                continue

            bbox2 = zone2.get("bbox", {})
            if not current_bbox or not bbox2:
                continue

            iou = _calculate_iou(current_bbox, bbox2)

            if iou > ZONE_OVERLAP_THRESHOLD:
                # Merge zones
                logger.debug(
                    f"Merging zones '{current_zone.get('label')}' and "
                    f"'{zone2.get('label')}' (IoU={iou:.2f})"
                )

                # Merge bboxes
                current_bbox = _merge_bboxes(current_bbox, bbox2)
                current_zone["bbox"] = current_bbox

                # Update center to merged bbox center (clamp to 0-100 range)
                center_x = (current_bbox["x"] + current_bbox["width"] / 2) * 100 / image_width
                center_y = (current_bbox["y"] + current_bbox["height"] / 2) * 100 / image_height
                current_zone["x"] = _clamp_percentage(center_x)
                current_zone["y"] = _clamp_percentage(center_y)

                # Keep higher confidence label
                if zone2.get("confidence", 0) > current_zone.get("confidence", 0):
                    current_zone["label"] = zone2.get("label")
                    current_zone["confidence"] = zone2.get("confidence")

                used.add(j)

        merged.append(current_zone)
        used.add(i)

    logger.info(f"Zone merging: {len(zones)} zones -> {len(merged)} merged zones")
    return merged


def _constrain_zone_size(
    zone: Dict[str, Any],
    image_width: int,
    image_height: int
) -> Dict[str, Any]:
    """
    Constrain a zone's size to be within valid bounds.

    Args:
        zone: Zone dict with bbox
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        Zone with constrained bbox
    """
    bbox = zone.get("bbox", {})
    if not bbox:
        return zone

    constrained = zone.copy()
    constrained_bbox = bbox.copy()

    # Enforce minimum size
    if constrained_bbox["width"] < MIN_ZONE_DIMENSION:
        # Expand width while keeping center
        center_x = constrained_bbox["x"] + constrained_bbox["width"] / 2
        constrained_bbox["width"] = MIN_ZONE_DIMENSION
        constrained_bbox["x"] = max(0, center_x - MIN_ZONE_DIMENSION / 2)

    if constrained_bbox["height"] < MIN_ZONE_DIMENSION:
        # Expand height while keeping center
        center_y = constrained_bbox["y"] + constrained_bbox["height"] / 2
        constrained_bbox["height"] = MIN_ZONE_DIMENSION
        constrained_bbox["y"] = max(0, center_y - MIN_ZONE_DIMENSION / 2)

    # Enforce maximum size
    max_width = image_width * MAX_ZONE_DIMENSION_RATIO
    max_height = image_height * MAX_ZONE_DIMENSION_RATIO

    if constrained_bbox["width"] > max_width:
        # Shrink width while keeping center
        center_x = constrained_bbox["x"] + constrained_bbox["width"] / 2
        constrained_bbox["width"] = max_width
        constrained_bbox["x"] = max(0, center_x - max_width / 2)

    if constrained_bbox["height"] > max_height:
        # Shrink height while keeping center
        center_y = constrained_bbox["y"] + constrained_bbox["height"] / 2
        constrained_bbox["height"] = max_height
        constrained_bbox["y"] = max(0, center_y - max_height / 2)

    # Ensure bbox stays within image bounds
    constrained_bbox["x"] = max(0, min(constrained_bbox["x"], image_width - constrained_bbox["width"]))
    constrained_bbox["y"] = max(0, min(constrained_bbox["y"], image_height - constrained_bbox["height"]))

    constrained["bbox"] = constrained_bbox

    # Update radius based on constrained bbox
    constrained["radius"] = min(
        min(constrained_bbox["width"], constrained_bbox["height"]) / 2,
        50  # Max radius
    )

    return constrained


class QwenSAMZoneDetector:
    """
    Combines Qwen VLM + SAM3 for accurate zone detection.

    Qwen provides semantic understanding to locate each label.
    SAM3 provides precise segmentation masks.

    Includes zone merging for overlapping masks and size constraints.
    """

    def __init__(self):
        self.qwen_model = os.getenv("QWEN_VL_MODEL", "qwen2.5vl:7b")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = float(os.getenv("QWEN_VL_TIMEOUT", "180.0"))
        self._qwen_available = None
        self._sam_available = None
        self._sam_predictor = None

    async def is_qwen_available(self) -> bool:
        """Check if Qwen VL is available."""
        if self._qwen_available is not None:
            return self._qwen_available

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = [m.get("name", "") for m in response.json().get("models", [])]
                    self._qwen_available = any(self.qwen_model in m for m in models)
                    return self._qwen_available
        except Exception as e:
            logger.warning(f"Could not check Qwen VL availability: {e}")
            self._qwen_available = False
        return False

    def is_sam_available(self) -> bool:
        """Check if SAM3 is available."""
        if self._sam_available is not None:
            return self._sam_available

        sam_path = os.getenv("SAM3_MODEL_PATH", "")
        if sam_path and Path(sam_path).exists():
            try:
                from segment_anything import sam_model_registry, SamPredictor
                self._sam_available = True
            except ImportError:
                self._sam_available = False
        else:
            self._sam_available = False

        return self._sam_available

    def _get_sam_predictor(self, image: np.ndarray):
        """Initialize SAM predictor with image."""
        if self._sam_predictor is None:
            from segment_anything import sam_model_registry, SamPredictor

            sam_path = os.getenv("SAM3_MODEL_PATH")
            model_type = os.getenv("SAM3_MODEL_TYPE", "vit_h")

            sam = sam_model_registry[model_type](checkpoint=sam_path)
            self._sam_predictor = SamPredictor(sam)

        self._sam_predictor.set_image(image)
        return self._sam_predictor

    async def detect_zones(
        self,
        image_path: str,
        canonical_labels: List[str],
        annotation_elements: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Detect zones for canonical labels.

        Priority order:
        1. Leader line endpoints (most accurate - direct from annotation detection)
        2. Qwen VLM location (fallback for labels without leader lines)
        3. Grid + CLIP (fallback when Qwen not available)

        Args:
            image_path: Path to the diagram image
            canonical_labels: List of expected labels to find
            annotation_elements: Optional list from qwen_annotation_detector

        Returns:
            Dict with zones, labels, and method used
        """
        start_time = time.time()

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        zones = []
        missing_labels = []
        method = "unknown"

        # PRIORITY 1: Use leader line endpoints if available
        if annotation_elements:
            logger.info("Using leader line endpoints for zone detection (most accurate)")
            zones, missing_labels = extract_zones_from_leader_lines(
                annotation_elements, canonical_labels, w, h
            )

            if zones:
                method = "leader_line_endpoints"

                # Optionally refine with SAM3
                sam_available = self.is_sam_available()
                if sam_available:
                    logger.info("Refining zones with SAM3 segmentation")
                    zones = self._refine_zones_with_sam(zones, image_rgb, w, h)
                    method = "leader_line_sam"

        # PRIORITY 2: Qwen VLM for missing labels
        if missing_labels:
            qwen_available = await self.is_qwen_available()
            sam_available = self.is_sam_available()

            if qwen_available:
                logger.info(f"Using Qwen VLM to locate {len(missing_labels)} missing labels")
                image_data = self._encode_image(image_path)

                for label in missing_labels:
                    result = await self._locate_label(label, image_data)

                    if result.get("found", False):
                        center = result.get("center", [500, 500])
                        bbox = result.get("bbox", [0, 0, 1000, 1000])
                        confidence = result.get("confidence", 0.8)

                        # Convert to pixel coordinates
                        center_px = (int(center[0] * w / 1000), int(center[1] * h / 1000))

                        # Use SAM3 if available for precise mask
                        if sam_available:
                            try:
                                predictor = self._get_sam_predictor(image_rgb)
                                masks, scores, _ = predictor.predict(
                                    point_coords=np.array([center_px]),
                                    point_labels=np.array([1]),
                                    multimask_output=True
                                )
                                best_idx = np.argmax(scores)
                                zone_mask = masks[best_idx]

                                ys, xs = np.where(zone_mask)
                                if len(xs) > 0 and len(ys) > 0:
                                    bbox = [
                                        int(xs.min() * 1000 / w),
                                        int(ys.min() * 1000 / h),
                                        int(xs.max() * 1000 / w),
                                        int(ys.max() * 1000 / h)
                                    ]
                                    confidence = float(scores[best_idx])
                            except Exception as e:
                                logger.warning(f"SAM3 failed for '{label}': {e}")

                        bbox_width = (bbox[2] - bbox[0]) * w / 1000
                        bbox_height = (bbox[3] - bbox[1]) * h / 1000
                        zones.append({
                            "id": f"zone_{label.lower().replace(' ', '_')}",  # Semantic ID
                            "label": label,
                            "bbox": {
                                "x": bbox[0] * w / 1000,
                                "y": bbox[1] * h / 1000,
                                "width": bbox_width,
                                "height": bbox_height
                            },
                            "x": _clamp_percentage(center[0] / 10),
                            "y": _clamp_percentage(center[1] / 10),
                            "radius": min(min(bbox_width, bbox_height) / 2, 50),  # Max radius 50
                            "confidence": confidence,
                            "source": "qwen_sam" if sam_available else "qwen_vl"
                        })
                        logger.debug(f"Qwen found '{label}' at ({center[0]}, {center[1]})")
                    else:
                        logger.warning(f"Qwen could not find '{label}'")

                # Update missing list
                found_by_qwen = {z["label"] for z in zones if z.get("source") in ["qwen_vl", "qwen_sam"]}
                missing_labels = [l for l in missing_labels if l not in found_by_qwen]

                if not zones:  # No zones found at all
                    method = "qwen_sam" if sam_available else "qwen_vl"
                elif method == "unknown":
                    method = "qwen_vl_fallback"

        # PRIORITY 3: SAM3 auto-segmentation (for unlabeled diagrams)
        if not zones and self.is_sam_available():
            logger.info("Trying SAM3 auto-segmentation + Qwen labeling")
            zones, missing_labels = await self.auto_segment_with_qwen_labels(
                image_path, canonical_labels
            )
            if zones:
                method = "sam3_auto_segment"

        # PRIORITY 4: Grid fallback if still no zones
        if not zones:
            logger.warning("Using grid fallback as last resort")
            zones, missing_labels = self._create_grid_zones_with_clip(
                image_path, image_rgb, canonical_labels, w, h
            )
            method = "grid_clip"

        # Add fallback zones for any still-missing labels
        if missing_labels:
            logger.info(f"Adding fallback zones for {len(missing_labels)} missing labels")
            fallback_zones = self._create_fallback_zones(missing_labels, w, h, len(zones))
            zones.extend(fallback_zones)

        # POST-PROCESSING: Apply zone quality improvements

        # 1. Constrain zone sizes to valid bounds
        zones = [_constrain_zone_size(z, w, h) for z in zones]

        # 2. Merge overlapping zones (handles over-segmentation)
        # Skip merging for leader-line zones - they are already accurately positioned
        original_count = len(zones)
        if method not in ["leader_line_endpoints", "leader_line_sam"]:
            zones = _merge_overlapping_zones(zones, w, h)
            if len(zones) < original_count:
                logger.info(f"Zone merging reduced {original_count} zones to {len(zones)}")
        else:
            logger.info(f"Skipping zone merging for leader-line method (preserving {len(zones)} zones)")

        # 3. Validate final zones and filter invalid ones
        valid_zones = []
        for zone in zones:
            is_valid, reason = _validate_zone_size(zone, w, h)
            if is_valid:
                valid_zones.append(zone)
            else:
                logger.debug(f"Filtered invalid zone '{zone.get('label')}': {reason}")

        # If too many zones were filtered, keep some for minimum coverage
        if len(valid_zones) < len(canonical_labels) // 2 and zones:
            logger.warning(
                f"Too many zones filtered ({len(zones) - len(valid_zones)}), "
                f"keeping all zones without strict filtering"
            )
            valid_zones = zones

        zones = valid_zones

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "zones": zones,
            "labels": [z["label"] for z in zones],
            "method": method,
            "missing_count": len(missing_labels),
            "latency_ms": latency_ms,
            "zones_merged": original_count - len(zones) if original_count > len(zones) else 0
        }

    def _refine_zones_with_sam(
        self,
        zones: List[Dict],
        image_rgb: np.ndarray,
        w: int,
        h: int
    ) -> List[Dict]:
        """
        Refine zone boundaries using SAM3 segmentation.

        Uses multiple point prompts per zone for more robust segmentation:
        - Center point (primary)
        - Points offset from center (secondary)

        Also applies size constraints to avoid over-segmentation.
        """
        try:
            predictor = self._get_sam_predictor(image_rgb)

            for zone in zones:
                endpoint_px = zone.get("endpoint_px")
                if not endpoint_px:
                    # Calculate from x, y percentage
                    endpoint_px = [int(zone["x"] * w / 100), int(zone["y"] * h / 100)]

                try:
                    # Use multiple point prompts for better segmentation
                    # Center point plus offset points
                    center_x, center_y = endpoint_px
                    offset = max(10, min(w, h) // 50)  # Adaptive offset

                    point_coords = [
                        [center_x, center_y],  # Center
                    ]

                    # Add offset points if they're within image bounds
                    if center_x + offset < w:
                        point_coords.append([center_x + offset, center_y])
                    if center_x - offset >= 0:
                        point_coords.append([center_x - offset, center_y])
                    if center_y + offset < h:
                        point_coords.append([center_x, center_y + offset])
                    if center_y - offset >= 0:
                        point_coords.append([center_x, center_y - offset])

                    # All points are positive (foreground) labels
                    point_labels = [1] * len(point_coords)

                    masks, scores, _ = predictor.predict(
                        point_coords=np.array(point_coords),
                        point_labels=np.array(point_labels),
                        multimask_output=True
                    )

                    # Select best mask by score
                    best_idx = np.argmax(scores)
                    mask = masks[best_idx]

                    ys, xs = np.where(mask)
                    if len(xs) > 0 and len(ys) > 0:
                        new_bbox = {
                            "x": int(xs.min()),
                            "y": int(ys.min()),
                            "width": int(xs.max() - xs.min()),
                            "height": int(ys.max() - ys.min())
                        }

                        # Validate the new bbox meets size constraints
                        temp_zone = {"bbox": new_bbox}
                        is_valid, reason = _validate_zone_size(temp_zone, w, h)

                        if is_valid:
                            zone["bbox"] = new_bbox
                            zone["confidence"] = float(scores[best_idx])
                            zone["source"] = "leader_line_sam"
                        else:
                            # Constrain the zone if too large/small
                            logger.debug(
                                f"SAM mask for '{zone.get('label')}' invalid ({reason}), constraining"
                            )
                            temp_zone = _constrain_zone_size(temp_zone, w, h)
                            zone["bbox"] = temp_zone["bbox"]
                            zone["confidence"] = float(scores[best_idx]) * 0.8  # Lower confidence
                            zone["source"] = "leader_line_sam_constrained"

                except Exception as e:
                    logger.debug(f"SAM refinement failed for zone '{zone.get('label')}': {e}")

            return zones

        except Exception as e:
            logger.warning(f"SAM refinement failed: {e}")
            return zones

    async def _locate_label(self, label: str, image_data: str) -> Dict[str, Any]:
        """Use Qwen VLM to locate a specific label in the diagram."""
        import httpx

        prompt = LOCATE_LABEL_PROMPT.format(label=label)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.qwen_model,
                        "prompt": prompt,
                        "images": [image_data],
                        "stream": False,
                        "options": {"temperature": 0.1, "num_ctx": 4096}
                    }
                )
                response.raise_for_status()
                text = response.json().get("response", "")

                # Parse JSON
                cleaned = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
                cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
                cleaned = cleaned.strip()

                return json.loads(cleaned)

            except Exception as e:
                logger.warning(f"Failed to locate '{label}': {e}")
                return {"found": False, "label": label, "reason": str(e)}

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        import base64
        import io

        img = Image.open(image_path)

        # Resize if too large
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            if img.width > img.height:
                new_size = (max_size, int(img.height * max_size / img.width))
            else:
                new_size = (int(img.width * max_size / img.height), max_size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        if img.mode != "RGB":
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def auto_segment_with_qwen_labels(
        self,
        image_path: str,
        canonical_labels: List[str],
        min_segment_area: float = 0.01
    ) -> Tuple[List[Dict], List[str]]:
        """
        Auto-segment image with SAM3 and label segments with Qwen VL.

        This is used when no leader line data is available (unlabeled diagrams
        or when annotation detection failed).

        Args:
            image_path: Path to the cleaned diagram image
            canonical_labels: Labels to assign to segments
            min_segment_area: Minimum segment area as fraction of image (filter tiny segments)

        Returns:
            Tuple of (zones list, missing labels list)
        """
        if not self.is_sam_available():
            logger.warning("SAM3 not available for auto-segmentation")
            return [], canonical_labels

        image = cv2.imread(image_path)
        if image is None:
            return [], canonical_labels

        h, w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        min_area_pixels = int(w * h * min_segment_area)

        logger.info(f"Running SAM3 auto-segmentation on {image_path}")

        try:
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

            sam_path = os.getenv("SAM3_MODEL_PATH")
            model_type = os.getenv("SAM3_MODEL_TYPE", "vit_h")

            sam = sam_model_registry[model_type](checkpoint=sam_path)
            mask_generator = SamAutomaticMaskGenerator(
                sam,
                points_per_side=16,  # Grid density for auto-segmentation
                pred_iou_thresh=0.86,
                stability_score_thresh=0.92,
                min_mask_region_area=min_area_pixels
            )

            # Generate masks
            masks = mask_generator.generate(image_rgb)
            logger.info(f"SAM3 found {len(masks)} segments")

            # Filter and sort by area (larger segments first)
            valid_masks = [m for m in masks if m['area'] >= min_area_pixels]
            valid_masks.sort(key=lambda x: x['area'], reverse=True)

            # Limit to reasonable number (avoid over-segmentation)
            max_segments = min(len(canonical_labels) * 2, 20)
            valid_masks = valid_masks[:max_segments]

            zones = []
            used_labels = set()
            qwen_available = await self.is_qwen_available()

            for i, mask_data in enumerate(valid_masks):
                mask = mask_data['segmentation']
                ys, xs = np.where(mask)

                if len(xs) == 0:
                    continue

                # Calculate center and bbox
                center_x = int(xs.mean())
                center_y = int(ys.mean())
                bbox = {
                    "x": int(xs.min()),
                    "y": int(ys.min()),
                    "width": int(xs.max() - xs.min()),
                    "height": int(ys.max() - ys.min())
                }

                # Try to label with Qwen VL
                label = None
                confidence = 0.5

                if qwen_available:
                    # Extract segment region for Qwen
                    x1, y1 = max(0, bbox["x"] - 10), max(0, bbox["y"] - 10)
                    x2, y2 = min(w, bbox["x"] + bbox["width"] + 10), min(h, bbox["y"] + bbox["height"] + 10)

                    segment_img = image_rgb[y1:y2, x1:x2]
                    if segment_img.size > 0:
                        # Save temp image for Qwen
                        temp_path = Path(image_path).parent / f"_temp_segment_{i}.jpg"
                        Image.fromarray(segment_img).save(temp_path)

                        # Ask Qwen to identify
                        available_labels = [l for l in canonical_labels if l not in used_labels]
                        if available_labels:
                            result = await self._identify_segment(str(temp_path), available_labels)
                            if result.get("label"):
                                label = result["label"]
                                confidence = result.get("confidence", 0.7)
                                used_labels.add(label)

                        # Clean up temp file
                        temp_path.unlink(missing_ok=True)

                if not label:
                    # Assign from remaining labels
                    remaining = [l for l in canonical_labels if l not in used_labels]
                    if remaining:
                        label = remaining[0]
                        used_labels.add(label)
                        confidence = 0.3

                if label:
                    radius = min(min(bbox["width"], bbox["height"]) / 2, 50)
                    zones.append({
                        "id": f"zone_{label.lower().replace(' ', '_')}",
                        "label": label,
                        "x": _clamp_percentage(center_x * 100 / w),
                        "y": _clamp_percentage(center_y * 100 / h),
                        "radius": radius,
                        "bbox": bbox,
                        "confidence": confidence,
                        "source": "sam3_auto_qwen" if qwen_available else "sam3_auto"
                    })

            missing = [l for l in canonical_labels if l not in used_labels]
            logger.info(f"Auto-segmentation created {len(zones)} zones, {len(missing)} labels missing")

            return zones, missing

        except Exception as e:
            logger.error(f"SAM3 auto-segmentation failed: {e}")
            return [], canonical_labels

    async def _identify_segment(self, segment_path: str, candidate_labels: List[str]) -> Dict[str, Any]:
        """Use Qwen VL to identify what structure a segment shows."""
        import httpx

        labels_str = ", ".join(candidate_labels[:10])
        prompt = f"""Look at this image segment from an educational diagram.

Which of these structures does this segment show?
Options: {labels_str}

If you can identify it, respond:
{{"label": "StructureName", "confidence": 0.9}}

If you cannot identify it, respond:
{{"label": null, "reason": "explanation"}}

Return ONLY JSON."""

        image_data = self._encode_image(segment_path)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.qwen_model,
                        "prompt": prompt,
                        "images": [image_data],
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                )
                response.raise_for_status()
                text = response.json().get("response", "")

                # Parse JSON
                cleaned = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
                cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)

                result = json.loads(cleaned.strip())

                # Validate label is in candidates
                if result.get("label") and result["label"] in candidate_labels:
                    return result
                elif result.get("label"):
                    # Fuzzy match to candidates
                    matched = fuzzy_match_label(result["label"], candidate_labels)
                    if matched:
                        return {"label": matched, "confidence": result.get("confidence", 0.6)}

                return {"label": None}

            except Exception as e:
                logger.debug(f"Segment identification failed: {e}")
                return {"label": None}

    def _create_grid_zones_with_clip(
        self,
        image_path: str,
        image_rgb: np.ndarray,
        labels: List[str],
        w: int,
        h: int
    ) -> Tuple[List[Dict], List[str]]:
        """Create grid zones and label with CLIP."""
        from app.services.clip_labeling_service import CLIPZoneLabeler

        # Create 3x3 grid
        zones = []
        grid_size = 3
        cell_w = w // grid_size
        cell_h = h // grid_size

        for row in range(grid_size):
            for col in range(grid_size):
                zones.append({
                    "id": f"zone_{len(zones) + 1}",
                    "label": None,
                    "bbox": {
                        "x": col * cell_w,
                        "y": row * cell_h,
                        "width": cell_w,
                        "height": cell_h
                    },
                    "x": _clamp_percentage((col + 0.5) * 100 / grid_size),
                    "y": _clamp_percentage((row + 0.5) * 100 / grid_size),
                    "confidence": 0.5,
                    "source": "grid"
                })

        # Use CLIP to label zones
        try:
            labeler = CLIPZoneLabeler()
            pil_image = Image.fromarray(image_rgb)

            used_labels = set()

            for zone in zones:
                bbox = zone["bbox"]
                crop = pil_image.crop((
                    int(bbox["x"]),
                    int(bbox["y"]),
                    int(bbox["x"] + bbox["width"]),
                    int(bbox["y"] + bbox["height"])
                ))

                # Get available labels (not yet used)
                available = [l for l in labels if l not in used_labels]
                if not available:
                    available = labels  # Allow reuse if all used

                result = labeler.label_zone(crop, available)
                zone["label"] = result["label"]
                zone["id"] = f"zone_{result['label'].lower().replace(' ', '_')}"  # Update to semantic ID
                zone["confidence"] = result["confidence"]
                zone["radius"] = min(min(zone["bbox"]["width"], zone["bbox"]["height"]) / 2, 50)  # Max radius 50
                zone["source"] = "grid_clip"

                if result["confidence"] > 0.5:
                    used_labels.add(result["label"])

            missing = [l for l in labels if l not in used_labels]
            return zones, missing

        except Exception as e:
            logger.warning(f"CLIP labeling failed: {e}")
            # Just use labels in order
            for i, zone in enumerate(zones):
                if i < len(labels):
                    zone["label"] = labels[i]
            return zones, labels[len(zones):]

    def _create_fallback_zones(
        self,
        missing_labels: List[str],
        w: int,
        h: int,
        start_idx: int
    ) -> List[Dict]:
        """Create fallback zones for missing labels."""
        zones = []
        n = len(missing_labels)

        for i, label in enumerate(missing_labels):
            # Spread fallback zones across bottom third
            x_pct = (i + 0.5) * 100 / max(n, 1)
            y_pct = 75  # Bottom quarter

            bbox_width = w / max(n, 1)
            bbox_height = h * 0.35
            zones.append({
                "id": f"zone_{label.lower().replace(' ', '_')}",  # Semantic ID
                "label": label,
                "bbox": {
                    "x": w * i / max(n, 1),
                    "y": h * 0.6,
                    "width": bbox_width,
                    "height": bbox_height
                },
                "x": _clamp_percentage(x_pct),
                "y": _clamp_percentage(y_pct),
                "radius": min(min(bbox_width, bbox_height) / 2, 50),  # Max radius 50
                "confidence": 0.3,
                "source": "fallback"
            })

        return zones


async def qwen_sam_zone_detector(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Detect and label zones using leader line endpoints + SAM3.

    This agent uses leader line endpoints (from annotation detection) as the
    primary source of zone locations. This is more accurate than asking Qwen
    to locate structures because leader lines point directly to structures.

    Priority order:
    1. Leader line endpoints (most accurate)
    2. Qwen VLM (for labels without leader lines)
    3. Grid + CLIP (fallback)

    Inputs: annotation_elements, cleaned_image_path, diagram_image, domain_knowledge, game_plan
    Outputs: diagram_zones, diagram_labels, zone_detection_method
    """
    logger.info("=== QWEN SAM ZONE DETECTOR STARTING ===")

    # Get annotation elements from previous step
    annotation_elements = state.get("annotation_elements", [])

    if annotation_elements:
        logger.info(f"Received {len(annotation_elements)} annotation elements from previous step")
        lines = [a for a in annotation_elements if a.get("type") == "line"]
        logger.info(f"  - {len(lines)} leader lines with endpoints")
    else:
        logger.warning("No annotation_elements from previous step - will use Qwen VLM fallback")

    # Get image path (prefer original with leader lines for zone detection)
    diagram_image = state.get("diagram_image", {})
    original_path = diagram_image.get("local_path")
    cleaned_path = state.get("cleaned_image_path")

    # Use original image (with leader lines visible) for best zone detection
    # Leader lines point to structures, so they help locate zones
    image_path = original_path if original_path and Path(original_path).exists() else cleaned_path

    if not image_path or not Path(image_path).exists():
        logger.error(f"No valid image path found")
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_method": "error",
            "_error": "No valid image path"
        }

    logger.info(f"Processing: {image_path}")

    # Get canonical labels
    domain_knowledge = state.get("domain_knowledge", {})
    game_plan = state.get("game_plan", {})

    canonical_labels = (
        domain_knowledge.get("canonical_labels", []) or
        game_plan.get("required_labels", []) or
        []
    )

    if not canonical_labels:
        logger.warning("No canonical labels provided")
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_method": "no_labels",
            "_warning": "No canonical labels provided"
        }

    logger.info(f"Canonical labels ({len(canonical_labels)}): {canonical_labels}")

    # Run detection with annotation elements
    detector = QwenSAMZoneDetector()
    result = await detector.detect_zones(
        image_path,
        canonical_labels,
        annotation_elements=annotation_elements
    )

    zones = result.get("zones", [])
    labels = result.get("labels", [])
    method = result.get("method", "unknown")

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model="qwen2.5vl:7b" if "qwen" in method else "clip",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=result.get("latency_ms", 0)
        )

        if result.get("missing_count", 0) > 0:
            ctx.set_fallback_used(f"Missing {result['missing_count']} labels")

    # Convert zones to expected format
    diagram_zones = []
    diagram_labels = []

    for zone in zones:
        diagram_zones.append({
            "id": zone["id"],
            "label": zone["label"],
            "x": zone["x"],
            "y": zone["y"],
            "radius": zone.get("radius", 20),  # Include radius, default to 20 if not set
            "bbox": zone.get("bbox"),
            "confidence": zone.get("confidence", 0.8),
            "source": zone.get("source", method)
        })

        if zone["label"]:
            diagram_labels.append({
                "id": zone["id"],
                "text": zone["label"]
            })

    logger.info(f"Zone detection complete: {len(diagram_zones)} zones, method={method}")

    # ==========================================================================
    # ENTITY REGISTRY POPULATION (Phase 3)
    # ==========================================================================
    # Convert zones to entity registry format for normalized entity relationships
    current_scene = state.get("current_scene_number", 1) or 1
    existing_registry = state.get("entity_registry")

    entity_registry = zones_to_entity_registry(
        zones=diagram_zones,
        scene_number=current_scene,
        existing_registry=existing_registry,
        detection_method=method,
    )

    logger.info(
        f"Entity registry populated with {len(entity_registry.get('zones', {}))} zones"
    )

    return {
        "diagram_zones": diagram_zones,
        "diagram_labels": diagram_labels,
        "zone_detection_method": method,
        "entity_registry": entity_registry,  # Phase 3: Entity Registry
        "_used_fallback": result.get("missing_count", 0) > 0,
        "_fallback_reason": f"Missing {result.get('missing_count', 0)} labels" if result.get("missing_count", 0) > 0 else None
    }
