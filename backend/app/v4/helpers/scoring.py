"""Deterministic scoring helpers.

All score computation is done here — LLMs output points_per_item and
expected_item_count, validators compute everything else.
"""

from typing import Any


def compute_mechanic_score(items_count: int, points_per_item: int) -> int:
    """Compute max_score for a single mechanic."""
    return items_count * points_per_item


def compute_scene_score(mechanics: list[dict[str, Any]]) -> int:
    """Compute scene_max_score as sum of mechanic max_scores."""
    return sum(m.get("max_score", 0) for m in mechanics)


def compute_total_score(scenes: list[dict[str, Any]]) -> int:
    """Compute total_max_score as sum of scene_max_scores."""
    return sum(s.get("scene_max_score", 0) for s in scenes)


def validate_score_chain(plan: dict[str, Any]) -> list[str]:
    """Check arithmetic consistency bottom-up. Returns list of error messages."""
    errors: list[str] = []

    expected_total = 0
    for si, scene in enumerate(plan.get("scenes", [])):
        expected_scene = 0
        for mi, mech in enumerate(scene.get("mechanics", [])):
            expected_mech = mech.get("expected_item_count", 0) * mech.get("points_per_item", 0)
            actual_mech = mech.get("max_score", 0)
            if actual_mech != expected_mech:
                errors.append(
                    f"Scene {si} mechanic {mi}: max_score={actual_mech} "
                    f"but expected_item_count*points_per_item={expected_mech}"
                )
            expected_scene += expected_mech

        actual_scene = scene.get("scene_max_score", 0)
        if actual_scene != expected_scene:
            errors.append(
                f"Scene {si}: scene_max_score={actual_scene} "
                f"but sum of mechanics={expected_scene}"
            )
        expected_total += expected_scene

    actual_total = plan.get("total_max_score", 0)
    if actual_total != expected_total:
        errors.append(
            f"total_max_score={actual_total} but sum of scenes={expected_total}"
        )

    return errors
