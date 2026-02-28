"""Utility functions for V4 pipeline.

Deterministic helpers for ID generation, coordinate normalization,
and label processing. Reuses patterns from V3 blueprint_assembler_tools.py.
"""

import re
import unicodedata
from typing import Any


def generate_zone_id(scene_number: int, label: str) -> str:
    """Generate deterministic zone ID from canonical label.

    Format: zone_s{scene}_{normalized_label}
    """
    normalized = normalize_label_text(label)
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return f"zone_s{scene_number}_{slug}"


def generate_label_id(scene_number: int, index: int) -> str:
    """Generate label ID. Format: label_s{scene}_{index}"""
    return f"label_s{scene_number}_{index}"


def generate_mechanic_id(scene_number: int, mechanic_type: str) -> str:
    """Generate mechanic ID. Format: mech_s{scene}_{type}"""
    return f"mech_s{scene_number}_{mechanic_type}"


def normalize_zone_coordinates(zone_dict: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested coordinates to top-level fields.

    Zone detection may return coordinates as a nested dict or list of {x, y}.
    This normalizes to the format the frontend expects.
    """
    result = dict(zone_dict)
    coords = result.pop("coordinates", None)

    if coords is None:
        return result

    # List of {x, y} points -> polygon points
    if isinstance(coords, list):
        points: list[list[float]] = []
        for pt in coords:
            if isinstance(pt, dict) and "x" in pt and "y" in pt:
                points.append([
                    clamp_coordinate(float(pt["x"])),
                    clamp_coordinate(float(pt["y"])),
                ])
        if points:
            result["points"] = points
        return result

    # Dict with x, y, radius or width/height
    if isinstance(coords, dict):
        for key in ("x", "y", "radius", "width", "height"):
            if key in coords:
                result[key] = clamp_coordinate(float(coords[key]))
        return result

    return result


def clamp_coordinate(value: float, min_val: float = 0, max_val: float = 100) -> float:
    """Clamp a coordinate value to valid range (percentage-based)."""
    return max(min_val, min(max_val, value))


def postprocess_zones(zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add `points` field for frontend polygon rendering.

    Frontend reads zone.points as [number, number][].
    If zone has x/y/radius (circle), convert to approximate polygon.
    If zone already has points, pass through.
    """
    result = []
    for zone in zones:
        z = normalize_zone_coordinates(zone)

        # Already has points
        if "points" in z and z["points"]:
            result.append(z)
            continue

        # Circle -> approximate polygon (8 points)
        if "x" in z and "y" in z and "radius" in z:
            import math
            cx, cy, r = float(z["x"]), float(z["y"]), float(z["radius"])
            pts = []
            for i in range(8):
                angle = 2 * math.pi * i / 8
                pts.append([
                    clamp_coordinate(cx + r * math.cos(angle)),
                    clamp_coordinate(cy + r * math.sin(angle)),
                ])
            z["points"] = pts
            result.append(z)
            continue

        # Rectangle -> 4 points
        if "x" in z and "y" in z and "width" in z and "height" in z:
            x, y = float(z["x"]), float(z["y"])
            w, h = float(z["width"]), float(z["height"])
            z["points"] = [
                [clamp_coordinate(x), clamp_coordinate(y)],
                [clamp_coordinate(x + w), clamp_coordinate(y)],
                [clamp_coordinate(x + w), clamp_coordinate(y + h)],
                [clamp_coordinate(x), clamp_coordinate(y + h)],
            ]
            result.append(z)
            continue

        # No coordinate data — pass through as-is
        result.append(z)

    return result


def normalize_label_text(label: str) -> str:
    """Lowercase, strip, collapse whitespace, remove diacritics."""
    text = label.strip().lower()
    # Remove diacritics
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def deduplicate_labels(labels: list[str]) -> list[str]:
    """Case-insensitive deduplication preserving first occurrence order."""
    seen: set[str] = set()
    result: list[str] = []
    for label in labels:
        key = normalize_label_text(label)
        if key not in seen:
            seen.add(key)
            result.append(label)
    return result
