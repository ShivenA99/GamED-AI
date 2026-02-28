"""Utility modules for GamED.AI v2"""

from app.utils.coordinate_transforms import (
    CoordinateSystem,
    transform_point,
    transform_bbox,
    transform_zones,
    normalize_to_percentage,
    pixels_to_percentage,
    normalized_to_percentage,
    clamp_coordinates,
    validate_coordinates,
    detect_coordinate_system,
)

__all__ = [
    "CoordinateSystem",
    "transform_point",
    "transform_bbox",
    "transform_zones",
    "normalize_to_percentage",
    "pixels_to_percentage",
    "normalized_to_percentage",
    "clamp_coordinates",
    "validate_coordinates",
    "detect_coordinate_system",
]
