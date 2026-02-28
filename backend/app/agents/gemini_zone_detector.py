"""
Gemini Zone Detector Agent

Detects clickable zones in educational diagrams using Google Gemini vision API.
Also creates hierarchical zone groupings from domain knowledge.

This agent is part of the hierarchical label diagram preset pipeline:
- Receives generated or cleaned diagram image
- Uses Gemini vision to detect zone positions for each canonical label
- Creates zoneGroups from hierarchical_relationships
- Outputs zones, labels, and groupings for blueprint generation

Inputs:
    - generated_diagram_path OR cleaned_image_path OR diagram_image
    - canonical_labels: From domain_knowledge
    - hierarchical_relationships: From domain_knowledge

Outputs:
    - diagram_zones: List of zones with x, y, radius
    - diagram_labels: Matching labels for zones
    - zone_groups: Hierarchical groupings for progressive reveal
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from PIL import Image

from app.agents.state import (
    AgentState,
    ZoneEntity,
    EntityRegistry,
    create_empty_entity_registry,
)
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.interactive_diagram import normalize_zones, create_labels_from_zones
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.gemini_zone_detector")

# Output directory for zone detection results
OUTPUT_DIR = Path("pipeline_outputs/gemini_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def zones_to_entity_registry(
    zones: List[Dict],
    scene_number: int = 1,
    existing_registry: Optional[EntityRegistry] = None,
) -> EntityRegistry:
    """
    Convert zone detection results to entity registry format.

    This creates ZoneEntity entries and populates the registry's zones dict
    and scene_zones relationship map.

    Args:
        zones: List of zone dicts from detection
        scene_number: Scene number for multi-scene games
        existing_registry: Optional existing registry to merge into

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
        if shape == "polygon" and zone.get("points"):
            coordinates = {
                "points": zone["points"],
                "center": zone.get("center", {"x": zone.get("x", 50), "y": zone.get("y", 50)}),
            }
        elif shape == "rect" and zone.get("bbox"):
            bbox = zone["bbox"]
            coordinates = {
                "x": bbox.get("x", 0),
                "y": bbox.get("y", 0),
                "width": bbox.get("width", 0),
                "height": bbox.get("height", 0),
            }
        else:
            # Default to circle
            shape = "circle"
            coordinates = {
                "x": zone.get("x", 50),
                "y": zone.get("y", 50),
                "radius": zone.get("radius", 5),
            }

        # Determine parent zone ID from parentLabel or parentZoneId
        parent_zone_id = zone.get("parentZoneId")
        if not parent_zone_id and zone.get("parentLabel"):
            parent_label = zone["parentLabel"].lower().replace(" ", "_")
            parent_zone_id = f"zone_{parent_label}"

        # Create ZoneEntity
        zone_entity: ZoneEntity = {
            "id": zone_id,
            "label": label,
            "shape": shape,
            "coordinates": coordinates,
            "parent_zone_id": parent_zone_id,
            "scene_number": scene_number,
            "confidence": zone.get("confidence"),
            "source": zone.get("source", "gemini_vlm"),
            "hierarchy_level": zone.get("hierarchyLevel") or zone.get("hierarchy_level"),
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


def validate_zone_spatial_coherence(
    zones: List[Dict],
    hierarchical_relationships: Optional[List[Dict]],
) -> Tuple[bool, List[str]]:
    """
    Validate that detected zones are spatially coherent with hierarchical relationships.

    For LAYERED relationships (composed_of, subdivided_into):
    - Child zones should be WITHIN the parent zone's bounding area
    - Child zones may overlap (they're layers)

    For DISCRETE relationships (contains, has_part):
    - Child zones should be within parent bounds
    - Child zones should be at distinct positions

    Args:
        zones: List of detected zones with x, y, radius
        hierarchical_relationships: List of relationship dicts

    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    if not hierarchical_relationships:
        return True, []

    errors = []

    # Build label -> zone mapping
    label_to_zone = {}
    for zone in zones:
        label = zone.get("label", "").lower()
        if label:
            label_to_zone[label] = zone

    for rel in hierarchical_relationships:
        parent = rel.get("parent", "")
        children = rel.get("children", [])
        rel_type = rel.get("relationship_type", "contains")

        if not parent or not children:
            continue

        parent_zone = label_to_zone.get(parent.lower())
        if not parent_zone:
            errors.append(f"Parent zone '{parent}' not found in detected zones")
            continue

        # Get parent bounds (approximation using center + radius)
        parent_x = parent_zone.get("x", 50)
        parent_y = parent_zone.get("y", 50)
        parent_r = parent_zone.get("radius", 10)

        # For layered structures, calculate the outer boundary
        parent_min_x = parent_x - parent_r * 2
        parent_max_x = parent_x + parent_r * 2
        parent_min_y = parent_y - parent_r * 2
        parent_max_y = parent_y + parent_r * 2

        is_layered = rel_type in ("composed_of", "subdivided_into")

        child_positions = []
        for child in children:
            child_zone = label_to_zone.get(child.lower())
            if not child_zone:
                errors.append(f"Child zone '{child}' of parent '{parent}' not found")
                continue

            child_x = child_zone.get("x", 50)
            child_y = child_zone.get("y", 50)
            child_positions.append((child, child_x, child_y))

            # Check if child is reasonably close to parent for layered structures
            if is_layered:
                # For layered structures, children should be close to parent center
                distance = ((child_x - parent_x) ** 2 + (child_y - parent_y) ** 2) ** 0.5
                # Allow generous tolerance (30% of image) for layers
                if distance > 30:
                    errors.append(
                        f"LAYERED ERROR: '{child}' (child of '{parent}') is too far from parent "
                        f"(distance={distance:.1f}%). Layers should be at similar positions."
                    )

        # For layered structures, check if children are clustered together
        if is_layered and len(child_positions) > 1:
            xs = [p[1] for p in child_positions]
            ys = [p[2] for p in child_positions]
            x_spread = max(xs) - min(xs)
            y_spread = max(ys) - min(ys)

            # Layers should have similar positions (small spread)
            if x_spread > 40 or y_spread > 40:
                children_str = ", ".join([p[0] for p in child_positions])
                errors.append(
                    f"LAYERED WARNING: Children of '{parent}' ({children_str}) have large spread "
                    f"(x_spread={x_spread:.1f}, y_spread={y_spread:.1f}). "
                    f"Layers should be at similar positions, not scattered."
                )

    is_valid = len([e for e in errors if "ERROR" in e]) == 0
    return is_valid, errors


def _build_hierarchy_context(hierarchical_relationships: List[Dict]) -> str:
    """
    Build hierarchical context instructions for the zone detection prompt.

    This is CRITICAL for proper zone detection - it tells the VLM how to spatially
    interpret parent-child relationships based on relationship_type:

    - composed_of / subdivided_into: LAYERED structures (e.g., Heart Wall layers)
      → Children are LAYERS within the parent boundary (concentric/overlapping)
      → Detect parent boundary first, then children WITHIN that boundary

    - contains / has_part: DISCRETE structures (e.g., Flower contains petals)
      → Children are separate structures within the parent
      → Detect each independently, validate they're within parent bounds

    Args:
        hierarchical_relationships: List of relationship dicts with parent, children, relationship_type

    Returns:
        Context string to inject into the detection prompt
    """
    if not hierarchical_relationships:
        return ""

    context_lines = [
        "\n\nCRITICAL HIERARCHICAL STRUCTURE INFORMATION:",
        "The following parent-child relationships MUST inform your zone detection strategy:",
        ""
    ]

    layered_groups = []
    discrete_groups = []

    for rel in hierarchical_relationships:
        parent = rel.get("parent", "")
        children = rel.get("children", [])
        rel_type = rel.get("relationship_type", "contains")

        if not parent or not children:
            continue

        children_str = ", ".join(children)

        if rel_type in ("composed_of", "subdivided_into"):
            layered_groups.append({
                "parent": parent,
                "children": children,
                "children_str": children_str
            })
        else:
            discrete_groups.append({
                "parent": parent,
                "children": children,
                "children_str": children_str
            })

    # Add LAYERED relationship instructions
    if layered_groups:
        context_lines.append("=== LAYERED STRUCTURES (composed_of/subdivided_into) ===")
        context_lines.append("These are LAYERS or STRATA within a parent structure.")
        context_lines.append("DETECTION STRATEGY: Detect the parent's OUTER BOUNDARY, then detect")
        context_lines.append("each child as a LAYER WITHIN that boundary. Layers often share edges")
        context_lines.append("or overlap - they are NOT separate discrete regions.")
        context_lines.append("")

        for group in layered_groups:
            context_lines.append(f"• {group['parent']} is composed of these LAYERS: {group['children_str']}")
            context_lines.append(f"  → {group['children_str']} should be detected as CONCENTRIC or OVERLAPPING")
            context_lines.append(f"     zones WITHIN the '{group['parent']}' boundary, NOT as scattered points.")
            context_lines.append(f"  → Example: If '{group['parent']}' spans x=20-80, y=30-70, then ALL children")
            context_lines.append(f"     ({group['children_str']}) must have coordinates within that range.")
            context_lines.append("")

    # Add DISCRETE relationship instructions
    if discrete_groups:
        context_lines.append("=== DISCRETE STRUCTURES (contains/has_part) ===")
        context_lines.append("These are separate components that happen to be within a parent.")
        context_lines.append("DETECTION STRATEGY: Detect each structure at its actual position.")
        context_lines.append("Children should be within parent bounds but do NOT need to overlap.")
        context_lines.append("")

        for group in discrete_groups:
            context_lines.append(f"• {group['parent']} contains: {group['children_str']}")
            context_lines.append("")

    # Add spatial validation reminder
    context_lines.append("=== SPATIAL VALIDATION RULES ===")
    context_lines.append("Before returning zones, verify:")
    context_lines.append("1. For LAYERED relationships: All child zones are WITHIN the parent's bounding box")
    context_lines.append("2. For LAYERED relationships: Children may share similar coordinates (they're layers)")
    context_lines.append("3. For DISCRETE relationships: Children are within parent but at distinct positions")
    context_lines.append("4. Do NOT cluster all children in one corner - distribute based on actual anatomy")
    context_lines.append("")

    # HAD v3: Add zone precision requirements
    context_lines.append("=== ZONE PRECISION REQUIREMENTS (HAD v3) ===")
    context_lines.append("")
    context_lines.append("### Avoid Overlap Rules:")
    context_lines.append("1. For DISCRETE relationships (contains, has_part):")
    context_lines.append("   - Zones must NOT overlap")
    context_lines.append("   - Minimum 3% gap between zone edges")
    context_lines.append("   - If structures are adjacent in image, create smaller zones that don't touch")
    context_lines.append("")
    context_lines.append("2. For LAYERED relationships (composed_of, subdivided_into):")
    context_lines.append("   - Parent zone encompasses all children")
    context_lines.append("   - Children zones may overlap (they are layers)")
    context_lines.append("   - Detect parent OUTER BOUNDARY first")
    context_lines.append("")
    context_lines.append("### Zone Boundary Accuracy:")
    context_lines.append("- Use POLYGON for irregular biological structures")
    context_lines.append("- Polygon should trace the actual structure boundary, not just a bounding box")
    context_lines.append("- Minimum 6 points for complex shapes")
    context_lines.append("- Ensure center point is inside the polygon")
    context_lines.append("")

    return "\n".join(context_lines)


def _build_reveal_order_context(reveal_order: List[str]) -> str:
    """
    Build progressive reveal order context for zone detection.

    HAD v3: This helps the VLM understand which zones are primary vs secondary.
    """
    if not reveal_order:
        return ""

    lines = [
        "\n\n### PROGRESSIVE REVEAL ORDER:",
        "Labels should be detected and presented in this pedagogical order:",
        ""
    ]

    for i, label in enumerate(reveal_order, 1):
        level = 1 if i <= 3 else (2 if i <= 7 else 3)
        lines.append(f"{i}. {label} (hierarchyLevel={level})")

    lines.append("")
    lines.append("For each zone, set hierarchyLevel based on this order:")
    lines.append("- Level 1: First 3 labels (main structures)")
    lines.append("- Level 2: Labels 4-7 (major components)")
    lines.append("- Level 3+: Remaining labels (sub-components)")
    lines.append("")

    return "\n".join(lines)


def build_zone_detection_prompt(
    canonical_labels: List[str],
    subject: str = "",
    difficulty_hints: bool = True,
    use_polygon_zones: bool = False,
    hierarchy_depth: int = 2,
    hierarchical_relationships: Optional[List[Dict]] = None,
    reveal_order: Optional[List[str]] = None,
    intelligent_zone_types: bool = False,
) -> str:
    """
    Build a prompt for zone detection using Gemini vision.

    Args:
        canonical_labels: List of part names to locate
        subject: Subject matter for context
        difficulty_hints: Whether to include difficulty ratings
        use_polygon_zones: Whether to request polygon shapes (Preset 2)
        hierarchy_depth: Maximum hierarchy depth to detect (Preset 2)
        hierarchical_relationships: List of parent-child relationships with relationship_type
            e.g., [{"parent": "Heart Wall", "children": ["Epicardium", "Myocardium"], "relationship_type": "composed_of"}]

    Returns:
        Detection prompt string
    """
    labels_str = ", ".join(canonical_labels)

    # Build hierarchical context section if relationships are provided
    hierarchy_context = ""
    if hierarchical_relationships:
        hierarchy_context = _build_hierarchy_context(hierarchical_relationships)

    # HAD v3: Build reveal order context if provided
    reveal_order_context = ""
    if reveal_order:
        reveal_order_context = _build_reveal_order_context(reveal_order)

    # Base prompt differs based on polygon mode
    if use_polygon_zones:
        # Preset 2: Polygon zone detection with hierarchy support
        # Intelligent zone types: model decides point vs area per-label
        zone_type_instructions = ""
        if intelligent_zone_types:
            zone_type_instructions = """
11. zone_type: "point" for small/simple structures, "area" for large/complex ones (REQUIRED)

ZONE TYPE DECISION (apply PER LABEL):
Decide the appropriate zone type for EACH structure:

Use zone_type="point" with small dot indicator (radius=3-5) for:
- Small anatomical features that would be cluttered with polygon overlay
- Simple, roughly circular structures
- Features where a precise dot indicator is sufficient
- Structures smaller than ~10% of image dimensions

Use zone_type="area" with precise polygon boundary for:
- Large/prominent structures that dominate a region
- Complex shapes requiring boundary definition for educational clarity
- Structures where the area coverage matters pedagogically
- Multi-part structures or regions that span significant image area

When zone_type="point", use shape="circle" with small radius (3-5).
When zone_type="area", use shape="polygon" with precise boundary tracing."""

        prompt = f"""Analyze this educational diagram and outline each labeled part with precision.

TASK: Find and outline the exact shape of these parts in the image:
{labels_str}

For EACH part, provide:
1. label: The part name (exactly as listed above)
2. shape: "polygon" for irregular shapes, "circle" for roughly circular parts
3. If polygon: points as list of [x, y] coordinate pairs tracing the outline (5-12 points typically)
4. If circle: x, y (center), radius
5. All coordinates as percentage (0=left/top edge, 100=right/bottom edge)
6. center: The visual center point {{x, y}} for label placement
7. confidence: Your confidence level (0.0-1.0)
8. visible: Whether the part is clearly visible (true/false)
9. hierarchyLevel: 1 for main structures, 2 for sub-parts, 3+ for deeper components
10. parentLabel: The label of the parent structure (null if top-level){zone_type_instructions}"""

        if difficulty_hints:
            prompt += """
11. difficulty: How easy to identify (1=very obvious, 2=moderate, 3=tricky)
12. hint: A short educational hint about this part (1 sentence max)
13. description: A 1-2 sentence functional description of this part"""

        prompt += f"""

POLYGON REQUIREMENTS:
- Trace the visible boundary of each structure with polygon points
- Use 5-12 points for smooth outlines (more for complex shapes)
- Points should be in clockwise or counter-clockwise order
- The polygon should tightly fit the structure's visible edge
- For very simple/circular parts, use shape="circle" with x, y, radius

HIERARCHY DETECTION:
- Identify parent-child relationships between structures
- hierarchyLevel=1: Main/outer structures (e.g., "heart", "cell")
- hierarchyLevel=2: Major components (e.g., "left ventricle", "nucleus")
- hierarchyLevel=3+: Sub-components (e.g., "valve leaflet", "nucleolus")
- Maximum hierarchy depth: {hierarchy_depth}
{hierarchy_context}{reveal_order_context}
OUTPUT FORMAT (JSON only, no markdown code blocks):
{{
  "zones": [
    {{
      "label": "left ventricle",
      "zone_type": "area",
      "shape": "polygon",
      "points": [[30.2, 45.1], [35.0, 40.0], [40.5, 45.5], [38.0, 55.0], [32.0, 52.0]],
      "center": {{"x": 35.5, "y": 47.5}},
      "confidence": 0.95,
      "visible": true,
      "hierarchyLevel": 2,
      "parentLabel": "heart",
      "difficulty": 2,
      "hint": "Pumps oxygenated blood to the body",
      "description": "The left ventricle is the main pumping chamber, pushing oxygenated blood through the aorta to the systemic circulation."
    }},
    {{
      "label": "aorta",
      "zone_type": "point",
      "shape": "circle",
      "x": 45.5,
      "y": 28.0,
      "radius": 4.0,
      "center": {{"x": 45.5, "y": 28.0}},
      "confidence": 0.92,
      "visible": true,
      "hierarchyLevel": 2,
      "parentLabel": "heart",
      "difficulty": 1,
      "hint": "The largest artery in the body"
    }}
  ],
  "image_analysis": {{
    "subject": "Description of what the diagram shows",
    "quality": "good/fair/poor",
    "orientation": "Description of diagram orientation/view"
  }},
  "hierarchy_summary": {{
    "max_depth_found": 2,
    "parent_child_relationships": [
      {{"parent": "heart", "children": ["left ventricle", "aorta"]}}
    ]
  }},
  "parts_not_found": ["list of parts that could not be located"]
}}"""
    else:
        # Preset 1: Standard circular zone detection
        prompt = f"""Analyze this educational diagram and locate each labeled part precisely.

TASK: Find the exact center position of these parts in the image:
{labels_str}

For EACH part, provide:
1. label: The part name (exactly as listed above)
2. x: Center X position as percentage (0=left edge, 100=right edge)
3. y: Center Y position as percentage (0=top edge, 100=bottom edge)
4. radius: Suggested clickable radius as percentage of image width (typically 3-8%)
5. confidence: Your confidence level (0.0-1.0)
6. visible: Whether the part is clearly visible (true/false)"""

        if difficulty_hints:
            prompt += """
7. difficulty: How easy to identify (1=very obvious, 2=moderate, 3=tricky)
8. hint: A short educational hint about this part (1 sentence max)"""

        prompt += f"""

PRECISION REQUIREMENTS:
- Coordinates must point to the EXACT visual center of each structure
- This data will be used for click-target zones in an educational game
- Be as accurate as possible - students will click on these locations
- If a part appears multiple times, choose the most prominent/clear instance

IMPORTANT NOTES:
- Only include parts that are actually visible in the image
- If a part is not visible, still include it with visible=false and approximate position
- Use percentage coordinates (0-100), not pixel coordinates
{hierarchy_context}{reveal_order_context}
OUTPUT FORMAT (JSON only, no markdown code blocks):
{{
  "zones": [
    {{
      "label": "petal",
      "x": 45.5,
      "y": 28.0,
      "radius": 5.0,
      "confidence": 0.95,
      "visible": true,
      "difficulty": 1,
      "hint": "Colorful structures that attract pollinators"
    }}
  ],
  "image_analysis": {{
    "subject": "Description of what the diagram shows",
    "quality": "good/fair/poor",
    "orientation": "Description of diagram orientation/view"
  }},
  "parts_not_found": ["list of parts that could not be located"]
}}"""

    return prompt


def create_zone_groups(
    hierarchical_relationships: Optional[Union[Dict, List]],
    zones: List[Dict],
) -> List[Dict]:
    """
    Create zone groups for hierarchical progressive reveal.

    Args:
        hierarchical_relationships: Hierarchical groupings from domain knowledge
            Supports two formats:
            1. List of {'parent': str, 'children': [str], 'relationship_type': str}
            2. Dict with 'groups' key containing list of {'name', 'members', 'parent'}

    Returns:
        List of zone groups matching ZoneGroup schema:
        {'id', 'parentZoneId', 'childZoneIds', 'revealTrigger', 'label'}
    """
    if not hierarchical_relationships:
        return []

    # Handle both list and dict formats
    if isinstance(hierarchical_relationships, list):
        groups = hierarchical_relationships
    elif isinstance(hierarchical_relationships, dict):
        groups = hierarchical_relationships.get("groups", [])
    else:
        return []

    if not groups:
        return []

    # Build a mapping from label to zone ID
    label_to_zone = {}
    for zone in zones:
        label = zone.get("label", "").lower()
        zone_id = zone.get("id") or f"zone_{label.replace(' ', '_')}"
        label_to_zone[label] = zone_id

    def find_zone_id(label_text: str) -> Optional[str]:
        """Find zone ID for a label, with fuzzy matching."""
        if not label_text:
            return None
        label_lower = label_text.lower()
        # Exact match
        if label_lower in label_to_zone:
            return label_to_zone[label_lower]
        # Partial match
        for label, zone_id in label_to_zone.items():
            if label_lower in label or label in label_lower:
                return zone_id
        return None

    zone_groups = []
    for idx, group in enumerate(groups):
        # Handle both formats:
        # Format 1: {'parent': 'stamen', 'children': ['anther', 'filament']}
        # Format 2: {'name': '...', 'members': [...], 'parent': '...'}
        parent_label = group.get("parent", "")
        children = group.get("children") or group.get("members", [])
        relationship_type = group.get("relationship_type", "composed_of")
        group_name = group.get("name") or group.get("label") or f"{parent_label} components"

        # Find parent zone ID
        parent_zone_id = find_zone_id(parent_label)
        if not parent_zone_id:
            logger.warning(f"Parent zone not found for '{parent_label}', skipping group")
            continue

        # Find child zone IDs
        child_zone_ids = []
        for child in children:
            child_zone_id = find_zone_id(child)
            if child_zone_id:
                child_zone_ids.append(child_zone_id)
            else:
                logger.warning(f"Child zone not found for '{child}'")

        if child_zone_ids:
            # Determine revealTrigger based on relationship_type:
            # - Layered structures (composed_of, subdivided_into): hover reveals layers
            # - Discrete structures (contains, has_part): click expands to show children
            if relationship_type in ("composed_of", "subdivided_into"):
                # Layered/strata structures - hover to reveal layers within parent
                reveal_trigger = "hover_reveal"
            elif relationship_type in ("contains", "has_part"):
                # Discrete structures - click to expand and show children
                reveal_trigger = "click_expand"
            else:
                # Default fallback
                reveal_trigger = "complete_parent"

            zone_group = {
                "id": f"group_{parent_label.lower().replace(' ', '_')}",
                "parentZoneId": parent_zone_id,
                "childZoneIds": child_zone_ids,
                "revealTrigger": reveal_trigger,
                "relationshipType": relationship_type,  # Include for downstream use
                "label": group_name,
            }
            zone_groups.append(zone_group)
            logger.info(f"Created zone group: {parent_label} -> {children} (trigger={reveal_trigger}, type={relationship_type})")

    logger.info(f"Created {len(zone_groups)} zone groups from hierarchical relationships")
    return zone_groups


async def detect_zones_with_gemini_masks(
    image_path: str,
    canonical_labels: List[str],
    subject: str = "",
    hierarchical_relationships: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Detect zones using Gemini's native segmentation mask API.

    Instead of asking Gemini to guess polygon coordinates as text, this uses
    Gemini's native image segmentation capability which returns:
    - box_2d: bounding box in [y0, x0, y1, x1] format (0-1000 scale)
    - mask: base64-encoded PNG segmentation mask

    The mask is then converted to a precise polygon using OpenCV findContours,
    giving pixel-precise boundaries without needing SAM.

    Args:
        image_path: Path to diagram image
        canonical_labels: Labels to detect
        subject: Subject for context
        hierarchical_relationships: Parent-child relationships

    Returns:
        Dict with zones, metadata, and status (same format as detect_zones_with_gemini)
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("OpenCV not available for mask-based detection")
        return {"success": False, "error": "OpenCV (cv2) not available"}

    try:
        from google import genai
        from google.genai import types
        import base64
        import io

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return {"success": False, "error": "GOOGLE_API_KEY not set"}

        client = genai.Client(api_key=api_key)

        # Load image
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image not found: {image_path}"}

        img = Image.open(image_path)
        img_width, img_height = img.size

        labels_str = ", ".join(canonical_labels)

        # Build prompt requesting segmentation masks
        prompt = f"""Give the segmentation masks for each of these parts in this {subject or 'educational'} diagram: {labels_str}

For each part, return a JSON object with:
- "label": the part name (exactly as listed)
- "box_2d": bounding box as [y_min, x_min, y_max, x_max] in 0-1000 scale
- "mask": the segmentation mask for this part

Output a JSON list of objects."""

        logger.info(f"Detecting zones with Gemini masks for {len(canonical_labels)} labels")
        start_time = time.time()

        model = "gemini-2.5-flash"

        response = client.models.generate_content(
            model=model,
            contents=[prompt, img],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Parse response
        response_text = response.text if hasattr(response, "text") else str(response)
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.split("\n")
            if lines[-1].strip() == "```":
                cleaned_text = "\n".join(lines[1:-1])
            else:
                cleaned_text = "\n".join(lines[1:])

        entries = json.loads(cleaned_text)
        if isinstance(entries, dict):
            entries = entries.get("parts", entries.get("zones", [entries]))

        zones = []
        parts_not_found = []

        for entry in entries:
            label = entry.get("label", "")
            if not label:
                continue

            box_2d = entry.get("box_2d")
            mask_data = entry.get("mask")

            if not box_2d or not mask_data:
                logger.warning(f"Missing box_2d or mask for '{label}', skipping")
                parts_not_found.append(label)
                continue

            try:
                # box_2d is [y_min, x_min, y_max, x_max] in 0-1000 scale
                y0, x0, y1, x1 = box_2d
                # Convert to pixel coordinates
                px0 = int(x0 * img_width / 1000)
                py0 = int(y0 * img_height / 1000)
                px1 = int(x1 * img_width / 1000)
                py1 = int(y1 * img_height / 1000)

                box_w = max(px1 - px0, 1)
                box_h = max(py1 - py0, 1)

                # Decode base64 mask PNG
                if isinstance(mask_data, str):
                    mask_bytes = base64.b64decode(mask_data)
                else:
                    logger.warning(f"Unexpected mask type for '{label}': {type(mask_data)}")
                    parts_not_found.append(label)
                    continue

                mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")
                # Resize mask to bounding box dimensions
                mask_resized = mask_img.resize((box_w, box_h), Image.NEAREST)
                mask_array = np.array(mask_resized)

                # Place mask in full-image canvas
                full_mask = np.zeros((img_height, img_width), dtype=np.uint8)
                # Clamp coordinates to image bounds
                paste_y0 = max(0, py0)
                paste_x0 = max(0, px0)
                paste_y1 = min(img_height, py0 + box_h)
                paste_x1 = min(img_width, px0 + box_w)
                src_y0 = paste_y0 - py0
                src_x0 = paste_x0 - px0
                src_y1 = src_y0 + (paste_y1 - paste_y0)
                src_x1 = src_x0 + (paste_x1 - paste_x0)
                full_mask[paste_y0:paste_y1, paste_x0:paste_x1] = mask_array[src_y0:src_y1, src_x0:src_x1]

                # Binarize at threshold 127
                _, binary_mask = cv2.threshold(full_mask, 127, 255, cv2.THRESH_BINARY)

                # Find contours
                contours, _ = cv2.findContours(
                    binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                if not contours:
                    logger.warning(f"No contours found for '{label}'")
                    parts_not_found.append(label)
                    continue

                # Get largest contour
                largest_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest_contour) < 100:
                    logger.warning(f"Contour too small for '{label}'")
                    parts_not_found.append(label)
                    continue

                # Simplify with Douglas-Peucker
                perimeter = cv2.arcLength(largest_contour, True)
                epsilon = 0.005 * perimeter
                simplified = cv2.approxPolyDP(largest_contour, epsilon, True)

                # Ensure reasonable point count
                while len(simplified) > 80 and epsilon < perimeter / 10:
                    epsilon *= 1.5
                    simplified = cv2.approxPolyDP(largest_contour, epsilon, True)

                # Convert to percentage coordinates (0-100)
                polygon = []
                for pt in simplified:
                    x_pct = round(float(pt[0][0]) / img_width * 100, 1)
                    y_pct = round(float(pt[0][1]) / img_height * 100, 1)
                    polygon.append([x_pct, y_pct])

                if len(polygon) < 3:
                    logger.warning(f"Polygon too few points for '{label}'")
                    parts_not_found.append(label)
                    continue

                # Calculate centroid
                cx = round(sum(p[0] for p in polygon) / len(polygon), 1)
                cy = round(sum(p[1] for p in polygon) / len(polygon), 1)

                zone = {
                    "id": f"zone_{label.lower().replace(' ', '_').replace('-', '_')}",
                    "label": label,
                    "zone_type": "area",
                    "shape": "polygon",
                    "points": polygon,
                    "center": {"x": cx, "y": cy},
                    "x": cx,
                    "y": cy,
                    "confidence": 0.92,
                    "visible": True,
                    "source": "gemini_native_mask",
                }

                zones.append(zone)
                logger.info(f"Mask→polygon for '{label}': {len(polygon)} points")

            except Exception as e:
                logger.warning(f"Mask processing failed for '{label}': {e}")
                parts_not_found.append(label)
                continue

        if not zones:
            return {
                "success": False,
                "error": "No zones extracted from masks",
                "parts_not_found": parts_not_found,
            }

        # Add hierarchy metadata if provided
        if hierarchical_relationships:
            from app.agents.gemini_sam3_zone_detector import (
                _add_hierarchy_to_zones,
                _subtract_child_polygons,
            )
            zones = _add_hierarchy_to_zones(zones, hierarchical_relationships)
            zones = _subtract_child_polygons(zones)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"mask_zones_{timestamp}.json"
        output_data = {
            "zones": zones,
            "parts_not_found": parts_not_found,
            "canonical_labels": canonical_labels,
            "duration_ms": duration_ms,
            "model": f"{model}-mask",
            "image_dimensions": {"width": img_width, "height": img_height},
        }
        try:
            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)
        except Exception:
            pass

        logger.info(
            f"Gemini mask detection: {len(zones)}/{len(canonical_labels)} zones, "
            f"{len(parts_not_found)} missing, {duration_ms}ms"
        )

        return {
            "success": True,
            "zones": zones,
            "parts_not_found": parts_not_found,
            "duration_ms": duration_ms,
            "model": f"{model}-mask",
            "output_file": str(output_file),
            "use_polygon_zones": True,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini mask response: {e}")
        return {"success": False, "error": f"JSON parse error: {e}"}
    except Exception as e:
        logger.error(f"Gemini mask detection failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def detect_zones_with_gemini(
    image_path: str,
    canonical_labels: List[str],
    subject: str = "",
    use_polygon_zones: bool = False,
    hierarchy_depth: int = 2,
    hierarchical_relationships: Optional[List[Dict]] = None,
    preferred_zone_types: Optional[List[str]] = None,
    reveal_order: Optional[List[str]] = None,
    intelligent_zone_types: bool = False,
) -> Dict[str, Any]:
    """
    Detect zone positions using Gemini vision API.

    Args:
        image_path: Path to the diagram image
        canonical_labels: Labels to locate
        subject: Subject matter for context
        use_polygon_zones: Whether to request polygon shapes (Preset 2)
        hierarchy_depth: Maximum hierarchy depth to detect (Preset 2)
        hierarchical_relationships: Parent-child relationships from domain knowledge
            Used for spatial reasoning about layered vs discrete structures
        preferred_zone_types: List of preferred zone types to detect
            Options: polygon, bounding_box, ellipse, circle, path
            If provided, overrides use_polygon_zones

    Returns:
        Dict with zones, analysis, and metadata
    """
    # Handle preferred_zone_types to maintain backward compatibility
    if preferred_zone_types:
        use_polygon_zones = "polygon" in preferred_zone_types or "path" in preferred_zone_types
    try:
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "GOOGLE_API_KEY not set",
            }

        client = genai.Client(api_key=api_key)

        # Load image
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image not found: {image_path}",
            }

        img = Image.open(image_path)
        img_width, img_height = img.size

        # Build prompt with polygon/hierarchy options and hierarchical relationships
        prompt = build_zone_detection_prompt(
            canonical_labels,
            subject,
            use_polygon_zones=use_polygon_zones,
            hierarchy_depth=hierarchy_depth,
            hierarchical_relationships=hierarchical_relationships,
            reveal_order=reveal_order,  # HAD v3: Pass reveal order
            intelligent_zone_types=intelligent_zone_types,  # HAD v3: Per-label zone type decision
        )

        logger.info(f"Detecting zones with Gemini for {len(canonical_labels)} labels")
        start_time = time.time()

        # Use Gemini 3 Flash Preview for best vision accuracy (same as POC)
        model = os.getenv("GEMINI_VISION_MODEL", "gemini-3-flash-preview")

        response = client.models.generate_content(
            model=model,
            contents=[prompt, img],
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Extract response text
        response_text = response.text if hasattr(response, 'text') else str(response)

        # Parse JSON from response
        try:
            # Clean up response (remove markdown code blocks if present)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                lines = cleaned_text.split("\n")
                # Remove first line (```json) and last line (```)
                if lines[-1].strip() == "```":
                    cleaned_text = "\n".join(lines[1:-1])
                else:
                    cleaned_text = "\n".join(lines[1:])

            result = json.loads(cleaned_text)

            # Validate and normalize zones
            raw_zones = result.get("zones", [])
            validated_zones = []

            for zone in raw_zones:
                if "label" not in zone:
                    continue

                label = zone["label"]
                zone_id = f"zone_{label.lower().replace(' ', '_')}"

                # Determine shape type
                shape = zone.get("shape", "circle")
                if shape not in ["circle", "polygon", "rect"]:
                    shape = "circle"

                # Determine zone_type from model response or infer from shape/radius
                zone_type = zone.get("zone_type")
                if not zone_type:
                    # Infer zone_type: if polygon or large radius, it's "area"; otherwise "point"
                    if shape == "polygon":
                        zone_type = "area"
                    elif float(zone.get("radius", 5)) > 6:
                        zone_type = "area"
                    else:
                        zone_type = "point"

                validated_zone = {
                    "id": zone_id,
                    "label": label,
                    "zone_type": zone_type,  # "point" or "area"
                    "shape": shape,
                    "confidence": float(zone.get("confidence", 0.8)),
                    "visible": zone.get("visible", True),
                    "source": "gemini_vision",
                }

                # Handle polygon zones (Preset 2)
                if shape == "polygon" and zone.get("points"):
                    points = zone.get("points", [])
                    if isinstance(points, list) and len(points) >= 3:
                        # Validate and normalize polygon points
                        normalized_points = []
                        for point in points:
                            if isinstance(point, (list, tuple)) and len(point) >= 2:
                                px = max(0, min(100, float(point[0])))
                                py = max(0, min(100, float(point[1])))
                                normalized_points.append([round(px, 1), round(py, 1)])
                        validated_zone["points"] = normalized_points

                        # Use provided center or calculate from points
                        if zone.get("center"):
                            center = zone["center"]
                            validated_zone["center"] = {
                                "x": max(0, min(100, float(center.get("x", 50)))),
                                "y": max(0, min(100, float(center.get("y", 50))))
                            }
                        elif normalized_points:
                            center_x = sum(p[0] for p in normalized_points) / len(normalized_points)
                            center_y = sum(p[1] for p in normalized_points) / len(normalized_points)
                            validated_zone["center"] = {"x": round(center_x, 1), "y": round(center_y, 1)}

                        # Also set x, y for compatibility
                        if validated_zone.get("center"):
                            validated_zone["x"] = validated_zone["center"]["x"]
                            validated_zone["y"] = validated_zone["center"]["y"]
                    else:
                        # Invalid polygon, fall back to circle
                        validated_zone["shape"] = "circle"
                        validated_zone["x"] = max(0, min(100, float(zone.get("x", 50))))
                        validated_zone["y"] = max(0, min(100, float(zone.get("y", 50))))
                        validated_zone["radius"] = max(2, min(15, float(zone.get("radius", 5))))
                elif shape == "rect":
                    # Rectangle shape with width/height
                    # Check for bounding_box format [y0, x0, y1, x1] (Gemini format)
                    if zone.get("bounding_box"):
                        bbox = zone["bounding_box"]
                        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                            y0, x0, y1, x1 = bbox[:4]
                            # Convert to normalized 0-100 format
                            validated_zone["x"] = max(0, min(100, (float(x0) + float(x1)) / 20))
                            validated_zone["y"] = max(0, min(100, (float(y0) + float(y1)) / 20))
                            validated_zone["width"] = max(2, min(50, abs(float(x1) - float(x0)) / 10))
                            validated_zone["height"] = max(2, min(50, abs(float(y1) - float(y0)) / 10))
                        else:
                            # Fallback to center with width/height
                            validated_zone["x"] = max(0, min(100, float(zone.get("x", 50))))
                            validated_zone["y"] = max(0, min(100, float(zone.get("y", 50))))
                            validated_zone["width"] = max(2, min(50, float(zone.get("width", 10))))
                            validated_zone["height"] = max(2, min(50, float(zone.get("height", 10))))
                    else:
                        # Use explicit width/height or convert from radius
                        validated_zone["x"] = max(0, min(100, float(zone.get("x", 50))))
                        validated_zone["y"] = max(0, min(100, float(zone.get("y", 50))))
                        radius = float(zone.get("radius", 5))
                        validated_zone["width"] = max(2, min(50, float(zone.get("width", radius * 2))))
                        validated_zone["height"] = max(2, min(50, float(zone.get("height", radius * 2))))
                else:
                    # Circle shape (default)
                    validated_zone["x"] = max(0, min(100, float(zone.get("x", 50))))
                    validated_zone["y"] = max(0, min(100, float(zone.get("y", 50))))
                    validated_zone["radius"] = max(2, min(15, float(zone.get("radius", 5))))

                # Hierarchy support (Preset 2)
                if zone.get("hierarchyLevel"):
                    validated_zone["hierarchyLevel"] = max(1, min(10, int(zone.get("hierarchyLevel", 1))))
                if zone.get("parentLabel"):
                    validated_zone["parentLabel"] = zone["parentLabel"]

                # Include optional fields
                if "difficulty" in zone:
                    validated_zone["difficulty"] = int(zone["difficulty"])
                if "hint" in zone:
                    validated_zone["hint"] = zone["hint"]
                if "description" in zone:
                    validated_zone["description"] = zone["description"]

                validated_zones.append(validated_zone)

            # Post-process: Link parent zones by parentLabel
            label_to_id = {z["label"].lower(): z["id"] for z in validated_zones}
            for zone in validated_zones:
                if zone.get("parentLabel"):
                    parent_label = zone["parentLabel"].lower()
                    if parent_label in label_to_id:
                        zone["parentZoneId"] = label_to_id[parent_label]
                    del zone["parentLabel"]  # Remove temporary field

            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = OUTPUT_DIR / f"zones_{timestamp}.json"

            output_data = {
                "zones": validated_zones,
                "image_analysis": result.get("image_analysis", {}),
                "parts_not_found": result.get("parts_not_found", []),
                "canonical_labels": canonical_labels,
                "duration_ms": duration_ms,
                "model": model,
                "image_dimensions": {"width": img_width, "height": img_height},
                "use_polygon_zones": use_polygon_zones,
                "hierarchy_summary": result.get("hierarchy_summary", {}),
            }

            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)

            return {
                "success": True,
                "zones": validated_zones,
                "image_analysis": result.get("image_analysis", {}),
                "parts_not_found": result.get("parts_not_found", []),
                "hierarchy_summary": result.get("hierarchy_summary", {}),
                "output_file": str(output_file),
                "duration_ms": duration_ms,
                "model": model,
                "use_polygon_zones": use_polygon_zones,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")

            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "raw_response": response_text[:1000],
            }

    except Exception as e:
        logger.error(f"Gemini zone detection failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def gemini_zone_detector(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Detect zones using Gemini vision with hierarchical grouping support.

    This agent is used in the hierarchical label diagram preset pipeline.
    It detects zone positions using Gemini vision and creates hierarchical
    zone groups from domain knowledge.

    Inputs from state:
        - generated_diagram_path OR cleaned_image_path OR diagram_image
        - canonical_labels (from domain_knowledge)
        - hierarchical_relationships (from domain_knowledge)

    Outputs to state:
        - diagram_zones: List of zones with x, y, radius
        - diagram_labels: Matching labels for zones
        - zone_groups: Hierarchical groupings for progressive reveal
        - zone_detection_method: "gemini_vlm"
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"Starting Gemini zone detection for {question_id}")

    # Check if this is a INTERACTIVE_DIAGRAM template
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.warning(f"gemini_zone_detector called for non-INTERACTIVE_DIAGRAM template: {template_type}")
        return {
            "current_agent": "gemini_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Determine which image to use (priority: generated > cleaned > diagram_image)
    image_path = state.get("generated_diagram_path")
    if not image_path or not os.path.exists(image_path):
        image_path = state.get("cleaned_image_path")
    if not image_path or not os.path.exists(image_path):
        # Try to get from diagram_image
        diagram_image = state.get("diagram_image", {})
        image_path = diagram_image.get("generated_path") or diagram_image.get("local_path")

    if not image_path or not os.path.exists(image_path):
        logger.error("No valid image path found for zone detection")
        return {
            "current_agent": "gemini_zone_detector",
            "current_validation_errors": ["No valid image path found for zone detection"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    logger.info(f"Using image for zone detection: {image_path}")

    # Get domain knowledge
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    canonical_labels = list(domain_knowledge.get("canonical_labels", []) or [])
    hierarchical_relationships = domain_knowledge.get("hierarchical_relationships")

    if not canonical_labels:
        logger.warning("No canonical labels found, using question for label extraction")
        question_text = state.get("question_text", "")
        # Extract subject from question
        subject = question_text.replace("Label the parts of ", "").replace("Label ", "").strip()
        if subject.endswith("?"):
            subject = subject[:-1]
    else:
        subject = state.get("pedagogical_context", {}).get("subject", "")

    logger.info(f"Detecting zones for labels: {canonical_labels}")

    # Check if using advanced preset with polygon zones
    from app.config.presets import get_preset_feature
    preset_name = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")

    use_polygon_zones = get_preset_feature(preset_name, "use_polygon_zones", False)
    unlimited_hierarchy = get_preset_feature(preset_name, "unlimited_hierarchy_depth", False)
    intelligent_zone_types = get_preset_feature(preset_name, "intelligent_zone_types", False)

    # Determine hierarchy depth
    hierarchy_depth = 10 if unlimited_hierarchy else 2

    # Convert hierarchical_relationships to list of dicts if needed
    hierarchy_list = None
    if hierarchical_relationships:
        if isinstance(hierarchical_relationships, list):
            hierarchy_list = hierarchical_relationships
        elif isinstance(hierarchical_relationships, dict):
            hierarchy_list = hierarchical_relationships.get("groups", [])

    # Extract suggested_reveal_order from domain_knowledge for progressive disclosure
    reveal_order = domain_knowledge.get("suggested_reveal_order")
    if not reveal_order:
        # Fallback: try query_intent.suggested_progression
        query_intent = domain_knowledge.get("query_intent", {})
        reveal_order = query_intent.get("suggested_progression") if query_intent else None

    logger.info(
        f"Zone detection mode: polygon={use_polygon_zones}, intelligent_zone_types={intelligent_zone_types}, "
        f"hierarchy_depth={hierarchy_depth}, hierarchical_groups={len(hierarchy_list) if hierarchy_list else 0}, "
        f"reveal_order_count={len(reveal_order) if reveal_order else 0}",
    )

    # Detect zones with Gemini, including hierarchical context for spatial reasoning
    result = await detect_zones_with_gemini(
        image_path=image_path,
        canonical_labels=canonical_labels,
        subject=subject,
        use_polygon_zones=use_polygon_zones,
        hierarchy_depth=hierarchy_depth,
        hierarchical_relationships=hierarchy_list,
        reveal_order=reveal_order,  # Pass reveal order for progressive disclosure
        intelligent_zone_types=intelligent_zone_types,
    )

    if not result.get("success"):
        error_msg = result.get("error", "Zone detection failed")
        logger.error(f"Gemini zone detection failed: {error_msg}")

        if ctx:
            ctx.set_fallback_used(f"Gemini detection failed: {error_msg}")

        return {
            "current_agent": "gemini_zone_detector",
            "current_validation_errors": [f"Zone detection failed: {error_msg}"],
            "last_updated_at": datetime.utcnow().isoformat(),
            "_used_fallback": True,
            "_fallback_reason": error_msg,
        }

    raw_zones = result.get("zones", [])
    logger.info(f"Detected {len(raw_zones)} zones")

    # Normalize zones to canonical format
    zones = normalize_zones(raw_zones)

    # Create properly formatted labels from zones
    diagram_labels = create_labels_from_zones(zones)

    # Create zone groups from hierarchical relationships
    zone_groups = create_zone_groups(hierarchical_relationships, zones)
    logger.info(f"Created {len(zone_groups)} zone groups")

    # Validate spatial coherence of zones with hierarchical relationships
    spatial_valid, spatial_errors = validate_zone_spatial_coherence(zones, hierarchy_list)
    if not spatial_valid:
        logger.warning(f"Zone spatial validation errors: {spatial_errors}")
    elif spatial_errors:
        # Warnings only
        logger.info(f"Zone spatial validation warnings: {spatial_errors}")

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model=result.get("model", "gemini-3-flash-preview"),
            latency_ms=result.get("duration_ms", 0),
        )

    # Check for missing labels
    parts_not_found = result.get("parts_not_found", [])
    if parts_not_found:
        logger.warning(f"Parts not found in image: {parts_not_found}")

    # ==========================================================================
    # ENTITY REGISTRY POPULATION (Phase 3)
    # ==========================================================================
    # Convert zones to entity registry format for normalized entity relationships
    current_scene = state.get("current_scene_number", 1) or 1
    existing_registry = state.get("entity_registry")

    entity_registry = zones_to_entity_registry(
        zones=zones,
        scene_number=current_scene,
        existing_registry=existing_registry,
    )

    logger.info(
        f"Entity registry populated with {len(entity_registry.get('zones', {}))} zones"
    )

    return {
        "diagram_zones": zones,
        "diagram_labels": diagram_labels,
        "zone_groups": zone_groups,
        "zone_detection_method": "gemini_vlm",
        "entity_registry": entity_registry,  # Phase 3: Entity Registry
        "zone_detection_metadata": {
            "model": result.get("model"),
            "duration_ms": result.get("duration_ms"),
            "image_analysis": result.get("image_analysis", {}),
            "parts_not_found": parts_not_found,
            "hierarchy_summary": result.get("hierarchy_summary", {}),
            "output_file": result.get("output_file"),
            "detected_at": datetime.utcnow().isoformat(),
            "use_polygon_zones": use_polygon_zones,
            "intelligent_zone_types": intelligent_zone_types,
            "hierarchy_depth": hierarchy_depth,
            "hierarchical_groups_used": len(hierarchy_list) if hierarchy_list else 0,
            "spatial_validation": {
                "is_valid": spatial_valid,
                "errors": spatial_errors,
            },
            "entity_registry_zones_count": len(entity_registry.get("zones", {})),
        },
        "current_agent": "gemini_zone_detector",
        "last_updated_at": datetime.utcnow().isoformat(),
    }
