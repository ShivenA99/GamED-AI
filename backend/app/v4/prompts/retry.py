"""Retry prompt templates.

Builds retry sections for agents that support validation-retry loops.
Condenses previous output to save tokens while providing full error context.
"""

import json
from typing import Any

from app.v4.schemas.validation import ValidationResult


# Max retry budgets per agent
MAX_RETRIES = {
    "game_designer": 2,
    "content_generator": 1,
    "interaction_designer": 1,
}


def build_retry_section(
    validation_result: ValidationResult,
    previous_output_condensed: str,
) -> str:
    """Build a retry section for an agent prompt.

    Args:
        validation_result: The failed validation result with issues.
        previous_output_condensed: Condensed version of the previous output.

    Returns:
        Retry section string to append to the prompt.
    """
    lines = [
        "YOUR PREVIOUS ATTEMPT FAILED VALIDATION. Fix the issues below.",
        "",
        "## Validation Issues",
    ]

    for issue in validation_result.issues:
        prefix = "ERROR" if issue.severity == "error" else "WARNING"
        field_info = f" (field: {issue.field_path})" if issue.field_path else ""
        mech_info = f" [mechanic: {issue.mechanic_id}]" if issue.mechanic_id else ""
        lines.append(f"- [{prefix}]{mech_info}{field_info}: {issue.message}")

    lines.append("")
    lines.append("## Your Previous Output (condensed)")
    lines.append(previous_output_condensed)
    lines.append("")
    lines.append("Fix ALL errors and return a corrected JSON. "
                 "Warnings can be ignored if intentional.")

    return "\n".join(lines)


def condense_game_plan(plan: dict[str, Any]) -> str:
    """Condense a GamePlan to structure + types only (no ContentBriefs).

    Keeps the structure visible for error diagnosis while saving tokens.
    Target: ~500 tokens.
    """
    condensed = {
        "title": plan.get("title"),
        "subject": plan.get("subject"),
        "difficulty": plan.get("difficulty"),
        "all_zone_labels": plan.get("all_zone_labels", []),
        "distractor_labels": plan.get("distractor_labels", []),
        "scenes": [],
    }

    for scene in plan.get("scenes", []):
        s = {
            "scene_id": scene.get("scene_id"),
            "title": scene.get("title"),
            "zone_labels": scene.get("zone_labels", []),
            "needs_diagram": scene.get("needs_diagram"),
            "mechanics": [],
        }
        for mech in scene.get("mechanics", []):
            s["mechanics"].append({
                "mechanic_id": mech.get("mechanic_id"),
                "mechanic_type": mech.get("mechanic_type"),
                "zone_labels_used": mech.get("zone_labels_used", []),
                "expected_item_count": mech.get("expected_item_count"),
                "points_per_item": mech.get("points_per_item"),
                # Omit content_brief — too large
            })
        s["mechanic_connections"] = scene.get("mechanic_connections", [])
        condensed["scenes"].append(s)

    return json.dumps(condensed, indent=2)


def condense_mechanic_content(content: dict[str, Any]) -> str:
    """Condense mechanic content for retry context.

    Mechanic content is usually small enough to include in full.
    """
    return json.dumps(content, indent=2)
