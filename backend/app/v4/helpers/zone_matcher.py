"""Zone Matcher — maps canonical label texts to detected zone IDs.

Content runs before assets (zone IDs don't exist yet during content generation).
Labels reference zone labels by TEXT. This module translates text -> zone_id
during assembly, after zone detection completes.

Matching priority: exact > case-insensitive > normalized > substring > fuzzy.
"""

import logging
from difflib import SequenceMatcher
from typing import Any

from app.v4.helpers.utils import generate_zone_id, normalize_label_text

logger = logging.getLogger("gamed_ai.v4.zone_matcher")


def match_labels_to_zones(
    canonical_labels: list[str],
    detected_zones: list[dict[str, Any]],
    scene_number: int = 1,
) -> dict[str, str]:
    """Match canonical label texts to detected zone IDs.

    Returns mapping: label_text -> zone_id.
    If a zone already has a matching ID, uses it. Otherwise generates one.
    Unmatched labels get a generated zone_id with a warning.
    """
    result: dict[str, str] = {}

    # Build lookup from zone label/name to zone
    zone_lookup: dict[str, dict[str, Any]] = {}
    for zone in detected_zones:
        zone_label = zone.get("label") or zone.get("name") or ""
        if zone_label:
            zone_lookup[zone_label] = zone

    # Normalized lookup
    norm_zone_lookup: dict[str, tuple[str, dict[str, Any]]] = {}
    for label_text, zone in zone_lookup.items():
        norm_zone_lookup[normalize_label_text(label_text)] = (label_text, zone)

    unmatched_zones = list(detected_zones)

    for label in canonical_labels:
        zone_id = _find_match(label, zone_lookup, norm_zone_lookup, unmatched_zones, scene_number)
        result[label] = zone_id

    return result


def _find_match(
    label: str,
    zone_lookup: dict[str, dict[str, Any]],
    norm_zone_lookup: dict[str, tuple[str, dict[str, Any]]],
    unmatched_zones: list[dict[str, Any]],
    scene_number: int,
) -> str:
    """Find best zone match for a label. Returns zone_id."""
    norm_label = normalize_label_text(label)

    # 1. Exact match
    if label in zone_lookup:
        zone = zone_lookup[label]
        _remove_zone(unmatched_zones, zone)
        return zone.get("id") or generate_zone_id(scene_number, label)

    # 2. Case-insensitive match
    for zone_label, zone in zone_lookup.items():
        if zone_label.lower() == label.lower():
            _remove_zone(unmatched_zones, zone)
            return zone.get("id") or generate_zone_id(scene_number, label)

    # 3. Normalized match
    if norm_label in norm_zone_lookup:
        _, zone = norm_zone_lookup[norm_label]
        _remove_zone(unmatched_zones, zone)
        return zone.get("id") or generate_zone_id(scene_number, label)

    # 4. Substring match (label contained in zone label or vice versa)
    for zone_label, zone in zone_lookup.items():
        if norm_label in normalize_label_text(zone_label) or normalize_label_text(zone_label) in norm_label:
            _remove_zone(unmatched_zones, zone)
            return zone.get("id") or generate_zone_id(scene_number, label)

    # 5. Fuzzy match (>0.7 similarity)
    best_score = 0.0
    best_zone = None
    for zone_label, zone in zone_lookup.items():
        score = SequenceMatcher(None, norm_label, normalize_label_text(zone_label)).ratio()
        if score > best_score and score > 0.7:
            best_score = score
            best_zone = zone

    if best_zone is not None:
        _remove_zone(unmatched_zones, best_zone)
        return best_zone.get("id") or generate_zone_id(scene_number, label)

    # 6. No match — generate zone_id, log warning
    logger.warning(f"No zone match for label '{label}' — generating synthetic zone_id")
    return generate_zone_id(scene_number, label)


def _remove_zone(zones: list[dict[str, Any]], zone: dict[str, Any]) -> None:
    """Remove a zone from the unmatched list (by identity)."""
    try:
        zones.remove(zone)
    except ValueError:
        pass


def canonical_to_zone_id(label: str, scene_number: int) -> str:
    """Generate a deterministic zone ID from a canonical label."""
    return generate_zone_id(scene_number, label)
