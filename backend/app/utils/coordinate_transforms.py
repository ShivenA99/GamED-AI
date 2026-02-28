"""
Coordinate System Standardization Utility

Provides consistent coordinate transformations between different systems used in the pipeline:
- PERCENTAGE (0-100): Used in blueprints and frontend
- NORMALIZED (0-1000): Used by Qwen VLM and some annotations
- PIXELS: Used by SAM, OpenCV, and image processing
- FRACTION (0-1): Used in some intermediate calculations

All transforms are reversible and preserve precision.
"""

from enum import Enum
from typing import Tuple, Dict, Any, List, Optional
import logging

logger = logging.getLogger("gamed_ai.utils.coordinate_transforms")


class CoordinateSystem(Enum):
    """Supported coordinate systems in the pipeline."""
    PERCENTAGE = "percentage"      # 0-100 scale (blueprint, frontend)
    NORMALIZED = "normalized"      # 0-1000 scale (Qwen VLM output)
    PIXELS = "pixels"              # Absolute pixel coordinates
    FRACTION = "fraction"          # 0-1 scale (internal)


def transform_point(
    point: Tuple[float, float],
    from_system: CoordinateSystem,
    to_system: CoordinateSystem,
    image_dimensions: Tuple[int, int]
) -> Tuple[float, float]:
    """
    Transform a single point between coordinate systems.

    Args:
        point: (x, y) coordinates in the source system
        from_system: Source coordinate system
        to_system: Target coordinate system
        image_dimensions: (width, height) in pixels

    Returns:
        (x, y) coordinates in the target system
    """
    if from_system == to_system:
        return point

    x, y = point
    width, height = image_dimensions

    # First convert to fraction (0-1 scale)
    if from_system == CoordinateSystem.PERCENTAGE:
        x_frac = x / 100.0
        y_frac = y / 100.0
    elif from_system == CoordinateSystem.NORMALIZED:
        x_frac = x / 1000.0
        y_frac = y / 1000.0
    elif from_system == CoordinateSystem.PIXELS:
        x_frac = x / width if width > 0 else 0
        y_frac = y / height if height > 0 else 0
    elif from_system == CoordinateSystem.FRACTION:
        x_frac = x
        y_frac = y
    else:
        raise ValueError(f"Unknown source coordinate system: {from_system}")

    # Then convert from fraction to target
    if to_system == CoordinateSystem.PERCENTAGE:
        return (x_frac * 100.0, y_frac * 100.0)
    elif to_system == CoordinateSystem.NORMALIZED:
        return (x_frac * 1000.0, y_frac * 1000.0)
    elif to_system == CoordinateSystem.PIXELS:
        return (x_frac * width, y_frac * height)
    elif to_system == CoordinateSystem.FRACTION:
        return (x_frac, y_frac)
    else:
        raise ValueError(f"Unknown target coordinate system: {to_system}")


def transform_bbox(
    bbox: Dict[str, float],
    from_system: CoordinateSystem,
    to_system: CoordinateSystem,
    image_dimensions: Tuple[int, int]
) -> Dict[str, float]:
    """
    Transform a bounding box between coordinate systems.

    Supports both {x, y, width, height} and {x1, y1, x2, y2} formats.

    Args:
        bbox: Bounding box dict with x, y, width, height (or x1, y1, x2, y2)
        from_system: Source coordinate system
        to_system: Target coordinate system
        image_dimensions: (width, height) in pixels

    Returns:
        Transformed bounding box dict
    """
    if from_system == to_system:
        return bbox.copy()

    # Handle x1, y1, x2, y2 format
    if "x1" in bbox:
        x1, y1 = transform_point(
            (bbox["x1"], bbox["y1"]), from_system, to_system, image_dimensions
        )
        x2, y2 = transform_point(
            (bbox["x2"], bbox["y2"]), from_system, to_system, image_dimensions
        )
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

    # Handle x, y, width, height format
    x, y = transform_point(
        (bbox["x"], bbox["y"]), from_system, to_system, image_dimensions
    )

    # Transform width and height
    width, height = image_dimensions

    if from_system == CoordinateSystem.PERCENTAGE:
        w_frac = bbox["width"] / 100.0
        h_frac = bbox["height"] / 100.0
    elif from_system == CoordinateSystem.NORMALIZED:
        w_frac = bbox["width"] / 1000.0
        h_frac = bbox["height"] / 1000.0
    elif from_system == CoordinateSystem.PIXELS:
        w_frac = bbox["width"] / width if width > 0 else 0
        h_frac = bbox["height"] / height if height > 0 else 0
    else:
        w_frac = bbox["width"]
        h_frac = bbox["height"]

    if to_system == CoordinateSystem.PERCENTAGE:
        new_w = w_frac * 100.0
        new_h = h_frac * 100.0
    elif to_system == CoordinateSystem.NORMALIZED:
        new_w = w_frac * 1000.0
        new_h = h_frac * 1000.0
    elif to_system == CoordinateSystem.PIXELS:
        new_w = w_frac * width
        new_h = h_frac * height
    else:
        new_w = w_frac
        new_h = h_frac

    return {"x": x, "y": y, "width": new_w, "height": new_h}


def transform_zones(
    zones: List[Dict[str, Any]],
    from_system: CoordinateSystem,
    to_system: CoordinateSystem,
    image_dimensions: Tuple[int, int]
) -> List[Dict[str, Any]]:
    """
    Transform a list of zones between coordinate systems.

    Args:
        zones: List of zone dicts with x, y, and optionally radius/bbox
        from_system: Source coordinate system
        to_system: Target coordinate system
        image_dimensions: (width, height) in pixels

    Returns:
        List of transformed zone dicts
    """
    transformed = []

    for zone in zones:
        new_zone = zone.copy()

        # Transform center point
        if "x" in zone and "y" in zone:
            x, y = transform_point(
                (zone["x"], zone["y"]), from_system, to_system, image_dimensions
            )
            new_zone["x"] = x
            new_zone["y"] = y

        # Transform radius (proportional to image size)
        if "radius" in zone:
            width, height = image_dimensions
            min_dim = min(width, height)

            if from_system == CoordinateSystem.PERCENTAGE:
                r_frac = zone["radius"] / 100.0
            elif from_system == CoordinateSystem.NORMALIZED:
                r_frac = zone["radius"] / 1000.0
            elif from_system == CoordinateSystem.PIXELS:
                r_frac = zone["radius"] / min_dim if min_dim > 0 else 0
            else:
                r_frac = zone["radius"]

            if to_system == CoordinateSystem.PERCENTAGE:
                new_zone["radius"] = r_frac * 100.0
            elif to_system == CoordinateSystem.NORMALIZED:
                new_zone["radius"] = r_frac * 1000.0
            elif to_system == CoordinateSystem.PIXELS:
                new_zone["radius"] = r_frac * min_dim
            else:
                new_zone["radius"] = r_frac

        # Transform bbox if present
        if "bbox" in zone and isinstance(zone["bbox"], dict):
            new_zone["bbox"] = transform_bbox(
                zone["bbox"], from_system, to_system, image_dimensions
            )

        transformed.append(new_zone)

    return transformed


def normalize_to_percentage(
    zones: List[Dict[str, Any]],
    source_system: CoordinateSystem,
    image_dimensions: Tuple[int, int]
) -> List[Dict[str, Any]]:
    """
    Convenience function to normalize zones to percentage coordinates.

    Args:
        zones: List of zone dicts
        source_system: The current coordinate system
        image_dimensions: (width, height) in pixels

    Returns:
        Zones with percentage coordinates (0-100)
    """
    return transform_zones(zones, source_system, CoordinateSystem.PERCENTAGE, image_dimensions)


def pixels_to_percentage(
    zones: List[Dict[str, Any]],
    image_dimensions: Tuple[int, int]
) -> List[Dict[str, Any]]:
    """
    Convert pixel coordinates to percentage coordinates.

    Args:
        zones: List of zone dicts with pixel coordinates
        image_dimensions: (width, height) in pixels

    Returns:
        Zones with percentage coordinates (0-100)
    """
    return transform_zones(
        zones, CoordinateSystem.PIXELS, CoordinateSystem.PERCENTAGE, image_dimensions
    )


def normalized_to_percentage(
    zones: List[Dict[str, Any]],
    image_dimensions: Optional[Tuple[int, int]] = None
) -> List[Dict[str, Any]]:
    """
    Convert normalized (0-1000) coordinates to percentage (0-100).

    Note: image_dimensions not strictly needed for this conversion but
    kept for API consistency.

    Args:
        zones: List of zone dicts with normalized coordinates
        image_dimensions: (width, height) - not used but kept for consistency

    Returns:
        Zones with percentage coordinates (0-100)
    """
    # For normalized to percentage, we just divide by 10
    transformed = []
    for zone in zones:
        new_zone = zone.copy()
        if "x" in zone:
            new_zone["x"] = zone["x"] / 10.0
        if "y" in zone:
            new_zone["y"] = zone["y"] / 10.0
        if "radius" in zone:
            new_zone["radius"] = zone["radius"] / 10.0
        transformed.append(new_zone)
    return transformed


def clamp_coordinates(
    zones: List[Dict[str, Any]],
    system: CoordinateSystem
) -> List[Dict[str, Any]]:
    """
    Clamp coordinates to valid ranges for the coordinate system.

    Args:
        zones: List of zone dicts
        system: The coordinate system

    Returns:
        Zones with clamped coordinates
    """
    if system == CoordinateSystem.PERCENTAGE:
        max_val = 100.0
    elif system == CoordinateSystem.NORMALIZED:
        max_val = 1000.0
    elif system == CoordinateSystem.FRACTION:
        max_val = 1.0
    else:
        # Can't clamp pixels without knowing dimensions
        return zones

    clamped = []
    for zone in zones:
        new_zone = zone.copy()
        if "x" in zone:
            new_zone["x"] = max(0, min(max_val, zone["x"]))
        if "y" in zone:
            new_zone["y"] = max(0, min(max_val, zone["y"]))
        clamped.append(new_zone)

    return clamped


def validate_coordinates(
    zones: List[Dict[str, Any]],
    system: CoordinateSystem
) -> Tuple[bool, List[str]]:
    """
    Validate that coordinates are within valid ranges.

    Args:
        zones: List of zone dicts
        system: The expected coordinate system

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    if system == CoordinateSystem.PERCENTAGE:
        max_val = 100.0
    elif system == CoordinateSystem.NORMALIZED:
        max_val = 1000.0
    elif system == CoordinateSystem.FRACTION:
        max_val = 1.0
    else:
        # Can't validate pixels without knowing dimensions
        return True, []

    for i, zone in enumerate(zones):
        zone_id = zone.get("id", f"zone_{i}")
        x = zone.get("x", 0)
        y = zone.get("y", 0)

        if not (0 <= x <= max_val):
            errors.append(f"Zone '{zone_id}' x={x} out of range [0, {max_val}]")
        if not (0 <= y <= max_val):
            errors.append(f"Zone '{zone_id}' y={y} out of range [0, {max_val}]")

    return len(errors) == 0, errors


def detect_coordinate_system(
    zones: List[Dict[str, Any]]
) -> Optional[CoordinateSystem]:
    """
    Attempt to detect the coordinate system based on value ranges.

    Args:
        zones: List of zone dicts with x, y coordinates

    Returns:
        Detected coordinate system or None if ambiguous
    """
    if not zones:
        return None

    max_x = max(zone.get("x", 0) for zone in zones)
    max_y = max(zone.get("y", 0) for zone in zones)
    max_coord = max(max_x, max_y)

    if max_coord <= 1.0:
        return CoordinateSystem.FRACTION
    elif max_coord <= 100:
        return CoordinateSystem.PERCENTAGE
    elif max_coord <= 1000:
        return CoordinateSystem.NORMALIZED
    else:
        return CoordinateSystem.PIXELS
