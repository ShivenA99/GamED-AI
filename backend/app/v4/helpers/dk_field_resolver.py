"""Domain Knowledge field resolver.

The mechanic contracts reference DK field names that don't always match
the actual DomainKnowledge schema paths. This module maps contract field
names to actual DK dict dot-paths and provides projection utilities.

From audit 38 Section 4 — 12 DK field names in contracts vs actual DK schema.
"""

from typing import Any, Optional


# Contract field name -> DK dict dot-path (None = not available from DK retriever)
DK_FIELD_MAP: dict[str, Optional[str]] = {
    "canonical_labels": "canonical_labels",
    "visual_description": None,  # Derived from question text, not DK
    "key_relationships": "hierarchical_relationships",
    "functions": "label_descriptions",
    "processes": "sequence_flow_data.flow_description",
    "flow_sequences": "sequence_flow_data.sequence_items",
    "temporal_order": "sequence_flow_data.sequence_items",
    "categories": "comparison_data.sorting_categories",
    "classifications": "comparison_data.groups",
    "definitions": "label_descriptions",
    "cause_effect": None,  # Not retrieved by current DK retriever
    "misconceptions": None,  # Not retrieved by current DK retriever
    "similarities_differences": "comparison_data",
    "hierarchy": "hierarchical_relationships",
}


def resolve_dk_field(dk: dict[str, Any], field_name: str) -> Any:
    """Resolve a contract DK field name to its value in the DK dict.

    Supports dot-path traversal (e.g., "sequence_flow_data.flow_description").
    Returns None if the path doesn't exist or the field is unmapped.
    """
    dk_path = DK_FIELD_MAP.get(field_name)
    if dk_path is None:
        return None

    current = dk
    for segment in dk_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current


def project_dk_for_mechanic(
    dk: dict[str, Any],
    dk_fields_needed: list[str],
) -> dict[str, Any]:
    """Project the DK dict to only the fields needed by a mechanic's ContentBrief.

    Returns a flat dict: {field_name: resolved_value} for non-None values.
    """
    result: dict[str, Any] = {}
    for field_name in dk_fields_needed:
        value = resolve_dk_field(dk, field_name)
        if value is not None:
            result[field_name] = value
    return result
