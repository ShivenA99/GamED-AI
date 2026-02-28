"""
Zone Collision Resolver for HAD v3

Detects and resolves zone overlaps based on hierarchical relationship types.
This module is critical for preventing visual zone overlap in the frontend.

HAD v3 Enhancements:
- Shapely-based polygon IoU for precise overlap detection
- Center-inside-polygon validation
- Polygon-aware bounding calculations

Resolution Strategies:
- LAYERED: Allow overlap for composed_of/subdivided_into (parent-child layers)
- DISCRETE: Separate zones with minimum gap for contains/has_part
- AUTO: Determine from relationship_type automatically

Key Functions:
- detect_overlaps: Calculate IoU between all zone pairs (polygon-aware)
- resolve_overlaps: Apply resolution strategy based on relationships
- validate_hierarchy_containment: Ensure children are within parent bounds
- validate_center_inside_polygon: Ensure zone centers are inside their polygons
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

# HAD v3: Try to import Shapely for polygon-aware IoU
try:
    from shapely.geometry import Polygon, Point
    from shapely.validation import make_valid
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

logger = get_logger("gamed_ai.agents.had.zone_collision_resolver")


@dataclass
class OverlapPair:
    """Represents an overlapping pair of zones."""
    zone_a_id: str
    zone_b_id: str
    iou: float  # Intersection over Union
    intersection_area: float
    relationship_type: Optional[str] = None
    is_parent_child: bool = False


@dataclass
class ZoneBounds:
    """Bounding box representation of a zone."""
    zone_id: str
    label: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    center_x: float
    center_y: float
    area: float


class CollisionValidationResult(BaseModel):
    """Result of collision validation."""
    is_valid: bool = Field(description="Whether zones pass collision checks")
    overlapping_pairs: List[Dict[str, Any]] = Field(default_factory=list)
    containment_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    resolution_applied: bool = False
    resolution_strategy: Optional[str] = None


# =============================================================================
# HAD v3: Polygon-Aware IoU and Validation Functions
# =============================================================================

def calculate_polygon_iou(
    zone_a: Dict[str, Any],
    zone_b: Dict[str, Any],
) -> Tuple[float, float]:
    """
    Calculate Intersection over Union (IoU) for polygon zones using Shapely.

    Falls back to bounding box IoU if Shapely is not available.

    Args:
        zone_a: Zone with 'points' (polygon) or x,y,radius (circle)
        zone_b: Zone with 'points' (polygon) or x,y,radius (circle)

    Returns:
        Tuple of (iou, intersection_area)
    """
    if not SHAPELY_AVAILABLE:
        # Fall back to bounding box IoU
        return _calculate_bbox_iou(zone_a, zone_b)

    try:
        poly_a = _zone_to_shapely_polygon(zone_a)
        poly_b = _zone_to_shapely_polygon(zone_b)

        if poly_a is None or poly_b is None:
            return 0.0, 0.0

        if not poly_a.is_valid:
            poly_a = make_valid(poly_a)
        if not poly_b.is_valid:
            poly_b = make_valid(poly_b)

        intersection = poly_a.intersection(poly_b).area
        union = poly_a.union(poly_b).area

        if union <= 0:
            return 0.0, intersection

        iou = intersection / union
        return iou, intersection

    except Exception as e:
        logger.warning(f"Shapely IoU calculation failed: {e}, falling back to bbox")
        return _calculate_bbox_iou(zone_a, zone_b)


def _zone_to_shapely_polygon(zone: Dict[str, Any]) -> Optional["Polygon"]:
    """Convert zone to Shapely Polygon."""
    if not SHAPELY_AVAILABLE:
        return None

    points = zone.get("points")
    if points and isinstance(points, list) and len(points) >= 3:
        # Polygon zone
        try:
            return Polygon(points)
        except Exception:
            return None

    # Circle or rect zone - convert to polygon approximation
    x = zone.get("x")
    y = zone.get("y")
    radius = zone.get("radius")

    if x is not None and y is not None and radius:
        # Create circle approximation with 16 points
        num_points = 16
        circle_points = [
            (
                x + radius * math.cos(2 * math.pi * i / num_points),
                y + radius * math.sin(2 * math.pi * i / num_points)
            )
            for i in range(num_points)
        ]
        return Polygon(circle_points)

    # Rect zone
    width = zone.get("width")
    height = zone.get("height")
    if x is not None and y is not None and width and height:
        half_w = width / 2
        half_h = height / 2
        return Polygon([
            (x - half_w, y - half_h),
            (x + half_w, y - half_h),
            (x + half_w, y + half_h),
            (x - half_w, y + half_h),
        ])

    return None


def _calculate_bbox_iou(
    zone_a: Dict[str, Any],
    zone_b: Dict[str, Any],
) -> Tuple[float, float]:
    """Calculate bounding box IoU (fallback when Shapely not available)."""
    a_bounds = _get_zone_bbox(zone_a)
    b_bounds = _get_zone_bbox(zone_b)

    # Calculate intersection
    inter_min_x = max(a_bounds[0], b_bounds[0])
    inter_max_x = min(a_bounds[2], b_bounds[2])
    inter_min_y = max(a_bounds[1], b_bounds[1])
    inter_max_y = min(a_bounds[3], b_bounds[3])

    if inter_min_x >= inter_max_x or inter_min_y >= inter_max_y:
        return 0.0, 0.0

    intersection = (inter_max_x - inter_min_x) * (inter_max_y - inter_min_y)

    a_area = (a_bounds[2] - a_bounds[0]) * (a_bounds[3] - a_bounds[1])
    b_area = (b_bounds[2] - b_bounds[0]) * (b_bounds[3] - b_bounds[1])
    union = a_area + b_area - intersection

    if union <= 0:
        return 0.0, intersection

    return intersection / union, intersection


def _get_zone_bbox(zone: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """Get bounding box (min_x, min_y, max_x, max_y) for a zone."""
    points = zone.get("points")
    if points and isinstance(points, list) and len(points) >= 3:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)

    x = zone.get("x", 50)
    y = zone.get("y", 50)
    radius = zone.get("radius", 5)
    width = zone.get("width", radius * 2)
    height = zone.get("height", radius * 2)

    return x - width / 2, y - height / 2, x + width / 2, y + height / 2


def validate_center_inside_polygon(zone: Dict[str, Any]) -> bool:
    """
    Validate that the zone's center is geometrically inside its polygon.

    For polygon zones, this ensures the center point is actually within
    the polygon boundary (important for concave shapes).

    Args:
        zone: Zone with 'points' and optionally 'center'

    Returns:
        True if center is inside polygon, False otherwise
    """
    points = zone.get("points")
    if not points or len(points) < 3:
        # Not a polygon zone, assume valid
        return True

    # Get center coordinates
    center = zone.get("center", {})
    center_x = center.get("x") if center else None
    center_y = center.get("y") if center else None

    if center_x is None or center_y is None:
        # Calculate centroid
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)

    if SHAPELY_AVAILABLE:
        try:
            poly = Polygon(points)
            if not poly.is_valid:
                poly = make_valid(poly)
            point = Point(center_x, center_y)
            return poly.contains(point) or poly.boundary.contains(point)
        except Exception:
            pass

    # Fallback: ray casting algorithm
    return _point_in_polygon(center_x, center_y, points)


def _point_in_polygon(x: float, y: float, polygon: List[List[float]]) -> bool:
    """Check if point is inside polygon using ray casting algorithm."""
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def validate_all_centers_inside(zones: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that all polygon zone centers are inside their polygons.

    Returns:
        Dict with 'valid' bool and 'invalid_zones' list
    """
    invalid_zones = []

    for zone in zones:
        if zone.get("points"):  # Only check polygon zones
            if not validate_center_inside_polygon(zone):
                invalid_zones.append({
                    "zone_id": zone.get("id"),
                    "label": zone.get("label"),
                    "center": zone.get("center"),
                })

    return {
        "valid": len(invalid_zones) == 0,
        "invalid_zones": invalid_zones,
        "total_polygons": sum(1 for z in zones if z.get("points")),
        "invalid_count": len(invalid_zones),
    }


class ZoneCollisionResolver:
    """
    Resolves zone overlaps based on relationship types.

    For LAYERED relationships (composed_of, subdivided_into):
    - Overlaps are ALLOWED and expected
    - Children should be within parent bounds

    For DISCRETE relationships (contains, has_part):
    - Overlaps should be PREVENTED
    - Zones should have minimum gaps
    """

    # Minimum gap between discrete zones as percentage of image
    MIN_DISCRETE_GAP_PERCENT = 3.0

    # Maximum allowed IoU for discrete zones
    MAX_DISCRETE_IOU = 0.05

    # Parent-child containment tolerance
    CONTAINMENT_TOLERANCE_PERCENT = 5.0

    def __init__(self):
        self.resolution_log = []

    def resolve_overlaps(
        self,
        zones: List[Dict[str, Any]],
        relationships: Optional[List[Dict[str, Any]]] = None,
        strategy: str = "auto"
    ) -> List[Dict[str, Any]]:
        """
        Resolve zone overlaps based on relationship types.

        Args:
            zones: List of zone definitions with x, y, radius or polygon points
            relationships: List of hierarchical relationships with parent, children, relationship_type
            strategy: Resolution strategy - 'layered', 'discrete', or 'auto'

        Returns:
            List of zones with adjusted positions to prevent unwanted overlaps
        """
        if not zones or len(zones) < 2:
            return zones

        # Build relationship lookup for fast access
        relationship_lookup = self._build_relationship_lookup(relationships or [])

        # Detect all overlaps
        overlapping_pairs = self._detect_overlaps(zones)

        if not overlapping_pairs:
            logger.info("No overlapping zones detected")
            return zones

        logger.info(f"Detected {len(overlapping_pairs)} overlapping zone pairs")

        # Classify overlaps
        for pair in overlapping_pairs:
            pair.relationship_type, pair.is_parent_child = self._classify_overlap(
                pair, relationship_lookup
            )

        # Determine strategy for each pair
        if strategy == "auto":
            # Separate overlaps into layered (allowed) and discrete (need resolution)
            discrete_overlaps = [
                p for p in overlapping_pairs
                if not p.is_parent_child and p.relationship_type not in ("composed_of", "subdivided_into")
            ]
            layered_overlaps = [
                p for p in overlapping_pairs
                if p.is_parent_child or p.relationship_type in ("composed_of", "subdivided_into")
            ]

            logger.info(f"Classified: {len(layered_overlaps)} layered (allowed), {len(discrete_overlaps)} discrete (need resolution)")

            # Only resolve discrete overlaps
            if discrete_overlaps:
                zones = self._separate_discrete_zones(zones, discrete_overlaps)
        elif strategy == "discrete":
            zones = self._separate_discrete_zones(zones, overlapping_pairs)
        # For "layered" strategy, we allow all overlaps

        return zones

    def _detect_overlaps(self, zones: List[Dict[str, Any]]) -> List[OverlapPair]:
        """
        Calculate overlap (IoU) between all zone pairs.

        HAD v3: Uses Shapely polygon IoU for polygon zones when available.

        Returns list of OverlapPair for zones with IoU > 0.
        """
        overlaps = []

        # HAD v3: Use polygon-aware IoU for polygon zones
        use_polygon_iou = SHAPELY_AVAILABLE and any(z.get("points") for z in zones)

        if use_polygon_iou:
            # Use polygon IoU for precise overlap detection
            for i, zone_a in enumerate(zones):
                for j, zone_b in enumerate(zones[i + 1:], start=i + 1):
                    iou, intersection = calculate_polygon_iou(zone_a, zone_b)
                    if iou > 0:
                        overlaps.append(OverlapPair(
                            zone_a_id=zone_a.get("id", f"zone_{i}"),
                            zone_b_id=zone_b.get("id", f"zone_{j}"),
                            iou=iou,
                            intersection_area=intersection,
                        ))
        else:
            # Fall back to bounding box IoU
            zone_bounds = [self._get_zone_bounds(z) for z in zones]

            for i, bounds_a in enumerate(zone_bounds):
                for j, bounds_b in enumerate(zone_bounds[i + 1:], start=i + 1):
                    iou, intersection = self._calculate_iou(bounds_a, bounds_b)
                    if iou > 0:
                        overlaps.append(OverlapPair(
                            zone_a_id=bounds_a.zone_id,
                            zone_b_id=bounds_b.zone_id,
                            iou=iou,
                            intersection_area=intersection,
                        ))

        return overlaps

    def _get_zone_center(self, zone: Dict[str, Any]) -> Optional[Tuple[float, float]]:
        """
        Get the center coordinates of a zone.
        Handles both polygon and circle zones.

        Returns:
            Tuple of (x, y) center coordinates, or None if not determinable
        """
        # Check for explicit center
        center = zone.get("center")
        if center:
            x = center.get("x")
            y = center.get("y")
            if x is not None and y is not None:
                return (x, y)

        # Calculate from polygon points
        points = zone.get("points")
        if points and isinstance(points, list) and len(points) >= 3:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            return (sum(xs) / len(xs), sum(ys) / len(ys))

        # Circle zone
        x = zone.get("x")
        y = zone.get("y")
        if x is not None and y is not None:
            return (x, y)

        return None

    def _get_zone_bounds(self, zone: Dict[str, Any]) -> ZoneBounds:
        """
        Calculate bounding box for a zone.
        Handles both circle (x, y, radius) and polygon (points) zones.
        """
        zone_id = zone.get("id", "unknown")
        label = zone.get("label", "")

        # Check for polygon zone
        points = zone.get("points")
        if points and isinstance(points, list) and len(points) >= 3:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            center_x = sum(xs) / len(xs)
            center_y = sum(ys) / len(ys)
            # Approximate area using bounding box
            area = (max_x - min_x) * (max_y - min_y)
        else:
            # Circle zone
            x = zone.get("x", 50)
            y = zone.get("y", 50)
            radius = zone.get("radius", 5)
            min_x = x - radius
            max_x = x + radius
            min_y = y - radius
            max_y = y + radius
            center_x = x
            center_y = y
            # Circular area approximation
            area = math.pi * radius * radius

        return ZoneBounds(
            zone_id=zone_id,
            label=label,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            center_x=center_x,
            center_y=center_y,
            area=area,
        )

    def _calculate_iou(self, a: ZoneBounds, b: ZoneBounds) -> Tuple[float, float]:
        """
        Calculate Intersection over Union (IoU) between two bounding boxes.

        Returns: (iou, intersection_area)
        """
        # Calculate intersection
        inter_min_x = max(a.min_x, b.min_x)
        inter_max_x = min(a.max_x, b.max_x)
        inter_min_y = max(a.min_y, b.min_y)
        inter_max_y = min(a.max_y, b.max_y)

        if inter_min_x >= inter_max_x or inter_min_y >= inter_max_y:
            return 0.0, 0.0

        intersection = (inter_max_x - inter_min_x) * (inter_max_y - inter_min_y)
        union = a.area + b.area - intersection

        if union <= 0:
            return 0.0, intersection

        iou = intersection / union
        return iou, intersection

    def _build_relationship_lookup(
        self, relationships: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build a lookup dictionary for fast relationship queries.

        Returns dict mapping (parent_label, child_label) -> relationship_info
        """
        lookup = {}

        for rel in relationships:
            parent = rel.get("parent", "").lower()
            children = rel.get("children", [])
            rel_type = rel.get("relationship_type", "contains")

            for child in children:
                child_lower = child.lower()
                lookup[(parent, child_lower)] = {
                    "relationship_type": rel_type,
                    "parent": parent,
                    "child": child_lower,
                }
                # Also store reverse for lookup
                lookup[child_lower] = {
                    "parent": parent,
                    "relationship_type": rel_type,
                }

        return lookup

    def _classify_overlap(
        self,
        pair: OverlapPair,
        relationship_lookup: Dict[str, Dict[str, Any]]
    ) -> Tuple[Optional[str], bool]:
        """
        Determine if an overlap is between parent-child and get relationship type.

        Returns: (relationship_type, is_parent_child)
        """
        # Get labels for both zones (normalize to lowercase)
        a_label = pair.zone_a_id.replace("zone_", "").replace("_", " ").lower()
        b_label = pair.zone_b_id.replace("zone_", "").replace("_", " ").lower()

        # Check if (a, b) or (b, a) is a parent-child pair
        if (a_label, b_label) in relationship_lookup:
            rel = relationship_lookup[(a_label, b_label)]
            return rel["relationship_type"], True
        elif (b_label, a_label) in relationship_lookup:
            rel = relationship_lookup[(b_label, a_label)]
            return rel["relationship_type"], True

        # Check if both have the same parent (siblings)
        a_parent = relationship_lookup.get(a_label, {}).get("parent")
        b_parent = relationship_lookup.get(b_label, {}).get("parent")

        if a_parent and a_parent == b_parent:
            # Siblings - use parent's relationship type
            parent_rel = relationship_lookup.get((a_parent, a_label))
            if parent_rel:
                return parent_rel["relationship_type"], False

        return None, False

    def _separate_discrete_zones(
        self,
        zones: List[Dict[str, Any]],
        overlapping_pairs: List[OverlapPair],
        min_gap_percent: float = None
    ) -> List[Dict[str, Any]]:
        """
        Push overlapping discrete zones apart using repulsion algorithm.

        Uses iterative repulsion to achieve minimum gap.
        """
        if min_gap_percent is None:
            min_gap_percent = self.MIN_DISCRETE_GAP_PERCENT

        # Create mutable copy of zones
        zones_copy = [dict(z) for z in zones]

        # Build zone lookup by ID
        zone_by_id = {z.get("id"): z for z in zones_copy}

        # Iterative repulsion
        max_iterations = 10
        for iteration in range(max_iterations):
            moved = False

            for pair in overlapping_pairs:
                zone_a = zone_by_id.get(pair.zone_a_id)
                zone_b = zone_by_id.get(pair.zone_b_id)

                if not zone_a or not zone_b:
                    continue

                # Get zone centers - handle both circle and polygon zones
                a_center = self._get_zone_center(zone_a)
                b_center = self._get_zone_center(zone_b)

                if not a_center or not b_center:
                    logger.debug(f"Could not get centers for zones, skipping separation")
                    continue

                a_x, a_y = a_center
                b_x, b_y = b_center

                # Approximate radius from bounding box
                a_bbox = _get_zone_bbox(zone_a)
                b_bbox = _get_zone_bbox(zone_b)
                a_r = max(a_bbox[2] - a_bbox[0], a_bbox[3] - a_bbox[1]) / 2
                b_r = max(b_bbox[2] - b_bbox[0], b_bbox[3] - b_bbox[1]) / 2

                # Calculate distance and required separation
                dx = b_x - a_x
                dy = b_y - a_y
                distance = math.sqrt(dx * dx + dy * dy)
                min_distance = a_r + b_r + min_gap_percent

                if distance < min_distance and distance > 0:
                    # Calculate repulsion vector
                    overlap = min_distance - distance
                    repulsion = overlap / 2.0 + 0.5  # Push each zone by half + a little extra

                    # Normalize direction
                    nx = dx / distance
                    ny = dy / distance

                    # Apply repulsion - shift the zone center for polygon zones
                    shift_a = (nx * repulsion, ny * repulsion)
                    shift_b = (-nx * repulsion, -ny * repulsion)

                    if zone_a.get("points"):
                        # Shift polygon points
                        zone_a["points"] = [
                            [p[0] - shift_a[0], p[1] - shift_a[1]]
                            for p in zone_a["points"]
                        ]
                        if zone_a.get("center"):
                            zone_a["center"]["x"] = zone_a["center"]["x"] - shift_a[0]
                            zone_a["center"]["y"] = zone_a["center"]["y"] - shift_a[1]
                    else:
                        zone_a["x"] = max(5, min(95, a_x - shift_a[0]))
                        zone_a["y"] = max(5, min(95, a_y - shift_a[1]))

                    if zone_b.get("points"):
                        # Shift polygon points
                        zone_b["points"] = [
                            [p[0] - shift_b[0], p[1] - shift_b[1]]
                            for p in zone_b["points"]
                        ]
                        if zone_b.get("center"):
                            zone_b["center"]["x"] = zone_b["center"]["x"] - shift_b[0]
                            zone_b["center"]["y"] = zone_b["center"]["y"] - shift_b[1]
                    else:
                        zone_b["x"] = max(5, min(95, b_x - shift_b[0]))
                        zone_b["y"] = max(5, min(95, b_y - shift_b[1]))

                    moved = True
                    logger.debug(
                        f"Separated zones '{pair.zone_a_id}' and '{pair.zone_b_id}' by {repulsion:.1f}%"
                    )

            if not moved:
                break

        self.resolution_log.append({
            "action": "separate_discrete_zones",
            "pairs_resolved": len(overlapping_pairs),
            "iterations": iteration + 1,
        })

        return zones_copy

    def validate_hierarchy_containment(
        self,
        zones: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> CollisionValidationResult:
        """
        Ensure children zones are within parent bounds.

        For layered relationships (composed_of, subdivided_into), children
        should be positioned within the parent's bounding area.
        """
        errors = []
        warnings = []

        # Build zone lookup by label
        zone_by_label = {}
        for z in zones:
            label = z.get("label", "").lower()
            zone_by_label[label] = self._get_zone_bounds(z)

        for rel in relationships:
            parent = rel.get("parent", "").lower()
            children = rel.get("children", [])
            rel_type = rel.get("relationship_type", "contains")

            parent_bounds = zone_by_label.get(parent)
            if not parent_bounds:
                continue

            # Expand parent bounds by tolerance
            tolerance = self.CONTAINMENT_TOLERANCE_PERCENT
            parent_min_x = parent_bounds.min_x - tolerance
            parent_max_x = parent_bounds.max_x + tolerance
            parent_min_y = parent_bounds.min_y - tolerance
            parent_max_y = parent_bounds.max_y + tolerance

            for child in children:
                child_lower = child.lower()
                child_bounds = zone_by_label.get(child_lower)
                if not child_bounds:
                    continue

                # Check if child center is within parent bounds
                is_contained = (
                    parent_min_x <= child_bounds.center_x <= parent_max_x and
                    parent_min_y <= child_bounds.center_y <= parent_max_y
                )

                if not is_contained:
                    if rel_type in ("composed_of", "subdivided_into"):
                        errors.append(
                            f"LAYERED CONTAINMENT ERROR: '{child}' (child of '{parent}') "
                            f"is outside parent bounds. Layers should be within parent."
                        )
                    else:
                        warnings.append(
                            f"CONTAINMENT WARNING: '{child}' (part of '{parent}') "
                            f"may be outside expected bounds."
                        )

        is_valid = len(errors) == 0

        return CollisionValidationResult(
            is_valid=is_valid,
            containment_errors=errors,
            warnings=warnings,
        )

    def get_overlap_summary(
        self,
        zones: List[Dict[str, Any]],
        relationships: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of zone overlaps for debugging and visualization.
        """
        overlaps = self._detect_overlaps(zones)
        relationship_lookup = self._build_relationship_lookup(relationships or [])

        layered_overlaps = []
        discrete_overlaps = []

        for pair in overlaps:
            pair.relationship_type, pair.is_parent_child = self._classify_overlap(
                pair, relationship_lookup
            )

            overlap_info = {
                "zone_a": pair.zone_a_id,
                "zone_b": pair.zone_b_id,
                "iou": round(pair.iou, 3),
                "relationship_type": pair.relationship_type,
                "is_parent_child": pair.is_parent_child,
            }

            if pair.is_parent_child or pair.relationship_type in ("composed_of", "subdivided_into"):
                layered_overlaps.append(overlap_info)
            else:
                discrete_overlaps.append(overlap_info)

        return {
            "total_overlaps": len(overlaps),
            "layered_overlaps": layered_overlaps,
            "discrete_overlaps": discrete_overlaps,
            "needs_resolution": len(discrete_overlaps) > 0,
        }


def resolve_zone_overlaps(
    zones: List[Dict[str, Any]],
    relationships: Optional[List[Dict[str, Any]]] = None,
    strategy: str = "auto"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to resolve zone overlaps.

    Args:
        zones: List of zone definitions
        relationships: List of hierarchical relationships
        strategy: Resolution strategy - 'layered', 'discrete', or 'auto'

    Returns:
        Tuple of (resolved_zones, resolution_metadata)
    """
    resolver = ZoneCollisionResolver()

    # Get overlap summary before resolution
    summary_before = resolver.get_overlap_summary(zones, relationships)

    # Resolve overlaps
    resolved_zones = resolver.resolve_overlaps(zones, relationships, strategy)

    # Get overlap summary after resolution
    summary_after = resolver.get_overlap_summary(resolved_zones, relationships)

    # Validate containment
    validation = resolver.validate_hierarchy_containment(resolved_zones, relationships or [])

    metadata = {
        "before": summary_before,
        "after": summary_after,
        "containment_validation": validation.model_dump(),
        "resolution_log": resolver.resolution_log,
        "strategy_used": strategy,
    }

    return resolved_zones, metadata


def resolve_zone_overlaps_with_temporal_constraints(
    zones: List[Dict[str, Any]],
    zone_groups: Optional[List[Dict[str, Any]]] = None,
    relationships: Optional[List[Dict[str, Any]]] = None,
    strategy: str = "auto"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Resolve zone overlaps and generate temporal constraints.

    This is the main entry point for the temporal intelligence system.
    It combines zone collision resolution with Petri Net-inspired
    temporal constraint generation.

    Args:
        zones: List of zone definitions
        zone_groups: List of hierarchical zone groups
        relationships: List of hierarchical relationships
        strategy: Resolution strategy - 'layered', 'discrete', or 'auto'

    Returns:
        Tuple of (resolved_zones, resolution_metadata, temporal_constraints)
    """
    from app.agents.had.temporal_resolver import (
        generate_temporal_constraints,
        constraints_to_dict_list,
    )

    resolver = ZoneCollisionResolver()

    # Get overlap summary before resolution
    summary_before = resolver.get_overlap_summary(zones, relationships)

    # Resolve overlaps (physical separation)
    resolved_zones = resolver.resolve_overlaps(zones, relationships, strategy)

    # Get overlap summary after resolution
    summary_after = resolver.get_overlap_summary(resolved_zones, relationships)

    # Validate containment
    validation = resolver.validate_hierarchy_containment(resolved_zones, relationships or [])

    # Build collision metadata for temporal constraint generation
    collision_metadata = {
        "before": summary_before,
        "after": summary_after,
        "overlapping_pairs": [
            {
                "zone_a": overlap.get("zone_a"),
                "zone_b": overlap.get("zone_b"),
                "iou": overlap.get("iou", 0),
                "relationship_type": overlap.get("relationship_type"),
                "is_parent_child": overlap.get("is_parent_child", False),
            }
            for overlap in summary_before.get("layered_overlaps", [])
            + summary_before.get("discrete_overlaps", [])
        ],
    }

    # Generate temporal constraints using the temporal resolver
    temporal_constraints = generate_temporal_constraints(
        zones=resolved_zones,
        zone_groups=zone_groups,
        collision_metadata=collision_metadata,
    )

    # Convert to dict format for JSON serialization
    temporal_constraints_dict = constraints_to_dict_list(temporal_constraints)

    # Build resolution metadata
    metadata = {
        "before": summary_before,
        "after": summary_after,
        "containment_validation": validation.model_dump(),
        "resolution_log": resolver.resolution_log,
        "strategy_used": strategy,
        # Add temporal constraint summary
        "temporal_constraints_summary": {
            "total": len(temporal_constraints),
            "mutex_count": sum(1 for c in temporal_constraints if c.constraint_type == "mutex"),
            "concurrent_count": sum(1 for c in temporal_constraints if c.constraint_type == "concurrent"),
            "before_count": sum(1 for c in temporal_constraints if c.constraint_type == "before"),
        },
    }

    logger.info(
        f"Zone collision resolution complete: "
        f"{len(resolved_zones)} zones, "
        f"{len(temporal_constraints)} temporal constraints "
        f"({metadata['temporal_constraints_summary']['mutex_count']} mutex, "
        f"{metadata['temporal_constraints_summary']['concurrent_count']} concurrent)"
    )

    return resolved_zones, metadata, temporal_constraints_dict
