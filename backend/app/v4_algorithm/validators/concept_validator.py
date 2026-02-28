"""Concept validator — deterministic checks on AlgorithmGameConcept."""

from app.utils.logging_config import get_logger
from app.v4_algorithm.contracts import SUPPORTED_GAME_TYPES

logger = get_logger("gamed_ai.v4_algorithm.validators.concept")

VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


async def algo_concept_validator(state: dict) -> dict:
    """Validate game concept after algo_game_concept_designer.

    Reads: game_concept
    Writes: concept_validation
    """
    concept = state.get("game_concept")
    if not concept:
        return {
            "concept_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": "No game_concept in state"}],
            },
        }

    issues = []

    # Check scenes
    scenes = concept.get("scenes", [])
    if not scenes:
        issues.append({"severity": "error", "message": "No scenes in game concept"})
    elif len(scenes) > 6:
        issues.append({"severity": "error", "message": f"Too many scenes ({len(scenes)}), max 6"})

    # Check each scene
    for i, scene in enumerate(scenes):
        game_type = scene.get("game_type", "")
        if game_type not in SUPPORTED_GAME_TYPES:
            issues.append({
                "severity": "error",
                "message": f"Scene {i+1}: invalid game_type '{game_type}'",
            })

        if not scene.get("title"):
            issues.append({
                "severity": "warning",
                "message": f"Scene {i+1}: missing title",
            })

        if not scene.get("learning_goal"):
            issues.append({
                "severity": "warning",
                "message": f"Scene {i+1}: missing learning_goal",
            })

        difficulty = scene.get("difficulty", "")
        if difficulty and difficulty not in VALID_DIFFICULTIES:
            issues.append({
                "severity": "warning",
                "message": f"Scene {i+1}: invalid difficulty '{difficulty}'",
            })

    # Check algorithm name
    if not concept.get("algorithm_name"):
        issues.append({"severity": "error", "message": "Missing algorithm_name"})

    # Check title
    if not concept.get("title"):
        issues.append({"severity": "warning", "message": "Missing game title"})

    # Determine pass/fail
    errors = [i for i in issues if i["severity"] == "error"]
    passed = len(errors) == 0
    score = max(0.0, 1.0 - len(errors) * 0.25 - len(issues) * 0.05)

    logger.info(f"Concept validation: passed={passed}, issues={len(issues)}")

    return {
        "concept_validation": {
            "passed": passed,
            "score": score,
            "issues": issues,
        },
    }
