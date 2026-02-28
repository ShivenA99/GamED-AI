"""Plan validator — deterministic checks on AlgorithmGamePlan."""

from app.utils.logging_config import get_logger
from app.v4_algorithm.contracts import SUPPORTED_GAME_TYPES

logger = get_logger("gamed_ai.v4_algorithm.validators.plan")


async def algo_plan_validator(state: dict) -> dict:
    """Validate game plan after algo_graph_builder.

    Reads: game_plan
    Writes: plan_validation
    """
    game_plan = state.get("game_plan")
    if not game_plan:
        return {
            "plan_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": "No game_plan in state"}],
            },
        }

    issues = []
    scenes = game_plan.get("scenes", [])

    if not scenes:
        issues.append({"severity": "error", "message": "No scenes in game plan"})

    # Check scene IDs are unique
    scene_ids = [s.get("scene_id") for s in scenes]
    if len(scene_ids) != len(set(scene_ids)):
        issues.append({"severity": "error", "message": "Duplicate scene_ids"})

    # Check each scene
    for i, scene in enumerate(scenes):
        if not scene.get("scene_id"):
            issues.append({"severity": "error", "message": f"Scene {i+1}: missing scene_id"})

        game_type = scene.get("game_type", "")
        if game_type not in SUPPORTED_GAME_TYPES:
            issues.append({"severity": "error", "message": f"Scene {i+1}: invalid game_type '{game_type}'"})

        if scene.get("max_score", 0) <= 0:
            issues.append({"severity": "warning", "message": f"Scene {i+1}: max_score <= 0"})

    # Check total score
    total = game_plan.get("total_max_score", 0)
    expected = sum(s.get("max_score", 0) for s in scenes)
    if total != expected:
        issues.append({
            "severity": "warning",
            "message": f"total_max_score mismatch: {total} != sum({expected})",
        })

    # Check transitions
    transitions = game_plan.get("scene_transitions", [])
    for t in transitions:
        if t.get("from_scene") not in scene_ids:
            issues.append({"severity": "warning", "message": f"Transition from unknown scene: {t.get('from_scene')}"})
        if t.get("to_scene") not in scene_ids:
            issues.append({"severity": "warning", "message": f"Transition to unknown scene: {t.get('to_scene')}"})

    errors = [i for i in issues if i["severity"] == "error"]
    passed = len(errors) == 0
    score = max(0.0, 1.0 - len(errors) * 0.25 - len(issues) * 0.05)

    logger.info(f"Plan validation: passed={passed}, issues={len(issues)}")

    return {
        "plan_validation": {
            "passed": passed,
            "score": score,
            "issues": issues,
        },
    }
