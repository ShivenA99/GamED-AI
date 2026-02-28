"""
Spatial Validator for HAD Zone Detection

Provides detailed spatial validation for zone positions against
hierarchical relationships. This enables the ZONE_PLANNER to reason
about detection quality and trigger retries with corrective prompts.

Validation Rules by Relationship Type:
- composed_of: Children are LAYERS (concentric/overlapping positions)
- subdivided_into: Same as composed_of
- contains: Children are WITHIN parent bounds (discrete positions)
- has_part: Same as contains
"""

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.spatial_validator")


class SpatialValidationResult(BaseModel):
    """Result of spatial validation analysis."""
    is_valid: bool = Field(description="Whether zones pass validation")
    overall_score: float = Field(description="Score from 0.0 to 1.0")
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    group_scores: Dict[str, float] = Field(default_factory=dict)
    analysis: Dict[str, Any] = Field(default_factory=dict)


class ZoneAnalysis(BaseModel):
    """Analysis of a single zone."""
    label: str
    x: float
    y: float
    radius: float
    bounding_box: Dict[str, float]  # min_x, max_x, min_y, max_y


def analyze_zone(zone: Dict[str, Any]) -> ZoneAnalysis:
    """Extract analysis data from a zone."""
    x = zone.get("x", 50)
    y = zone.get("y", 50)
    radius = zone.get("radius", 5)

    return ZoneAnalysis(
        label=zone.get("label", "unknown"),
        x=x,
        y=y,
        radius=radius,
        bounding_box={
            "min_x": x - radius,
            "max_x": x + radius,
            "min_y": y - radius,
            "max_y": y + radius,
        }
    )


def validate_hierarchical_spatial_coherence(
    zones: List[Dict[str, Any]],
    hierarchical_relationships: List[Dict[str, Any]],
) -> SpatialValidationResult:
    """
    Comprehensive spatial validation of zones against hierarchical relationships.

    This function provides detailed analysis for the ZONE_PLANNER to understand
    what went wrong and how to fix it.

    Args:
        zones: List of detected zones with x, y, radius
        hierarchical_relationships: List of relationship dicts with
            parent, children, relationship_type

    Returns:
        SpatialValidationResult with detailed analysis
    """
    if not hierarchical_relationships:
        return SpatialValidationResult(
            is_valid=True,
            overall_score=1.0,
            analysis={"note": "No hierarchical relationships to validate"}
        )

    errors = []
    warnings = []
    suggestions = []
    group_scores = {}
    analysis = {}

    # Build label -> zone mapping
    label_to_zone = {}
    for zone in zones:
        label = zone.get("label", "").lower()
        if label:
            label_to_zone[label] = analyze_zone(zone)

    total_score = 0.0
    num_groups = 0

    for rel in hierarchical_relationships:
        parent = rel.get("parent", "")
        children = rel.get("children", [])
        rel_type = rel.get("relationship_type", "contains")

        if not parent or not children:
            continue

        num_groups += 1
        group_key = f"{parent.lower()}_group"

        # Get parent zone
        parent_zone = label_to_zone.get(parent.lower())
        if not parent_zone:
            errors.append(f"Parent zone '{parent}' not found in detected zones")
            group_scores[group_key] = 0.0
            continue

        # Analyze children
        child_zones = []
        missing_children = []
        for child in children:
            child_zone = label_to_zone.get(child.lower())
            if child_zone:
                child_zones.append(child_zone)
            else:
                missing_children.append(child)

        if missing_children:
            warnings.append(
                f"Children not found for '{parent}': {', '.join(missing_children)}"
            )

        if not child_zones:
            errors.append(f"No child zones found for parent '{parent}'")
            group_scores[group_key] = 0.0
            continue

        # Validate based on relationship type
        is_layered = rel_type in ("composed_of", "subdivided_into")

        if is_layered:
            score, group_errors, group_warnings, group_suggestions = (
                _validate_layered_relationship(parent, parent_zone, children, child_zones)
            )
        else:
            score, group_errors, group_warnings, group_suggestions = (
                _validate_discrete_relationship(parent, parent_zone, children, child_zones)
            )

        group_scores[group_key] = score
        total_score += score
        errors.extend(group_errors)
        warnings.extend(group_warnings)
        suggestions.extend(group_suggestions)

        # Record analysis
        analysis[group_key] = {
            "parent": parent,
            "children": [z.label for z in child_zones],
            "relationship_type": rel_type,
            "score": score,
            "parent_position": {"x": parent_zone.x, "y": parent_zone.y},
            "child_positions": [{"label": z.label, "x": z.x, "y": z.y} for z in child_zones],
        }

    # Calculate overall score
    overall_score = total_score / num_groups if num_groups > 0 else 1.0

    # Determine validity (no critical errors)
    is_valid = len([e for e in errors if "CRITICAL" in e or "ERROR" in e]) == 0 and overall_score >= 0.5

    return SpatialValidationResult(
        is_valid=is_valid,
        overall_score=overall_score,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
        group_scores=group_scores,
        analysis=analysis,
    )


def _validate_layered_relationship(
    parent: str,
    parent_zone: ZoneAnalysis,
    children: List[str],
    child_zones: List[ZoneAnalysis],
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Validate a LAYERED relationship (composed_of, subdivided_into).

    For layers:
    - Children should be at similar positions (they're layers, not scattered parts)
    - Children should be close to parent center
    - Children may overlap - this is EXPECTED for layers
    """
    errors = []
    warnings = []
    suggestions = []

    # Calculate child position statistics
    child_xs = [z.x for z in child_zones]
    child_ys = [z.y for z in child_zones]

    mean_x = sum(child_xs) / len(child_xs)
    mean_y = sum(child_ys) / len(child_ys)

    x_spread = max(child_xs) - min(child_xs)
    y_spread = max(child_ys) - min(child_ys)

    # Check 1: Are children close to each other? (they're layers)
    max_allowed_spread = 25  # % of image
    spread_score = 1.0

    if x_spread > max_allowed_spread or y_spread > max_allowed_spread:
        spread_score = max(0, 1 - (max(x_spread, y_spread) - max_allowed_spread) / 50)
        errors.append(
            f"LAYERED ERROR: Children of '{parent}' ({', '.join([z.label for z in child_zones])}) "
            f"have excessive spread (x={x_spread:.1f}%, y={y_spread:.1f}%). "
            f"Layers should be at similar positions, not scattered."
        )
        suggestions.append(
            f"Re-detect zones for '{parent}' children with explicit instruction that "
            f"they are LAYERS/STRATA within the parent boundary, meaning they should "
            f"have similar x,y coordinates (overlapping/concentric), not spread apart."
        )

    # Check 2: Are children close to parent center?
    parent_distance_score = 1.0
    distance_to_parent = ((mean_x - parent_zone.x) ** 2 + (mean_y - parent_zone.y) ** 2) ** 0.5
    max_parent_distance = 30  # % of image

    if distance_to_parent > max_parent_distance:
        parent_distance_score = max(0, 1 - (distance_to_parent - max_parent_distance) / 40)
        warnings.append(
            f"LAYERED WARNING: Children of '{parent}' are far from parent center "
            f"(distance={distance_to_parent:.1f}%). Expected: within {max_parent_distance}%."
        )

    # Check 3: Clustering detection (are they bunched in one corner?)
    corner_score = 1.0
    corner_margin = 15  # % from edge

    # Check if all children are in same corner
    all_in_corner = (
        (all(z.x < corner_margin for z in child_zones) or all(z.x > 100 - corner_margin for z in child_zones)) and
        (all(z.y < corner_margin for z in child_zones) or all(z.y > 100 - corner_margin for z in child_zones))
    )

    if all_in_corner and x_spread < 10 and y_spread < 10:
        corner_score = 0.3
        errors.append(
            f"CRITICAL: Children of '{parent}' appear clustered in a corner "
            f"(all near x={mean_x:.1f}, y={mean_y:.1f}). This is incorrect for layers."
        )
        suggestions.append(
            f"The zone detection failed to properly locate layer positions. "
            f"Re-detect with explicit instruction that '{parent}' LAYERS should be "
            f"positioned at the ACTUAL anatomical location of '{parent}' in the diagram, "
            f"not clustered in a corner."
        )

    # Calculate overall score
    score = (spread_score * 0.4 + parent_distance_score * 0.3 + corner_score * 0.3)

    return score, errors, warnings, suggestions


def _validate_discrete_relationship(
    parent: str,
    parent_zone: ZoneAnalysis,
    children: List[str],
    child_zones: List[ZoneAnalysis],
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Validate a DISCRETE relationship (contains, has_part).

    For discrete parts:
    - Children should be within parent bounds (approximately)
    - Children should be at distinct positions (not overlapping)
    """
    errors = []
    warnings = []
    suggestions = []

    # Expand parent bounds generously for "contains" check
    parent_bounds = {
        "min_x": max(0, parent_zone.x - parent_zone.radius * 3),
        "max_x": min(100, parent_zone.x + parent_zone.radius * 3),
        "min_y": max(0, parent_zone.y - parent_zone.radius * 3),
        "max_y": min(100, parent_zone.y + parent_zone.radius * 3),
    }

    # Check 1: Are children within expanded parent bounds?
    containment_score = 1.0
    outside_children = []

    for child_zone in child_zones:
        if (child_zone.x < parent_bounds["min_x"] or
            child_zone.x > parent_bounds["max_x"] or
            child_zone.y < parent_bounds["min_y"] or
            child_zone.y > parent_bounds["max_y"]):
            outside_children.append(child_zone.label)

    if outside_children:
        containment_score = 1 - (len(outside_children) / len(child_zones))
        warnings.append(
            f"DISCRETE WARNING: Some children of '{parent}' appear outside parent bounds: "
            f"{', '.join(outside_children)}"
        )

    # Check 2: Are children at distinct positions? (not all overlapping)
    distinction_score = 1.0
    overlap_threshold = 5  # % - zones closer than this are considered overlapping

    overlapping_pairs = []
    for i, z1 in enumerate(child_zones):
        for z2 in child_zones[i + 1:]:
            distance = ((z1.x - z2.x) ** 2 + (z1.y - z2.y) ** 2) ** 0.5
            if distance < overlap_threshold:
                overlapping_pairs.append((z1.label, z2.label))

    if overlapping_pairs:
        distinction_score = 1 - (len(overlapping_pairs) / (len(child_zones) * (len(child_zones) - 1) / 2 + 0.001))
        warnings.append(
            f"DISCRETE WARNING: Some children of '{parent}' appear at nearly identical positions: "
            f"{overlapping_pairs}"
        )

    # Calculate overall score
    score = (containment_score * 0.6 + distinction_score * 0.4)

    return score, errors, warnings, suggestions


def generate_corrective_prompt(
    validation_result: SpatialValidationResult,
    hierarchical_relationships: List[Dict[str, Any]],
) -> str:
    """
    Generate a corrective prompt for re-detection based on validation errors.

    This is used by the ZONE_PLANNER to retry detection with specific guidance.
    """
    if validation_result.is_valid:
        return ""

    lines = [
        "IMPORTANT CORRECTIONS NEEDED:",
        "Previous detection had the following issues:",
        ""
    ]

    for error in validation_result.errors[:5]:  # Limit to top 5 errors
        lines.append(f"- {error}")

    lines.append("")
    lines.append("CORRECTIVE INSTRUCTIONS:")

    for suggestion in validation_result.suggestions[:3]:  # Top 3 suggestions
        lines.append(f"- {suggestion}")

    lines.append("")
    lines.append("Please re-detect zones with these corrections in mind.")

    return "\n".join(lines)
