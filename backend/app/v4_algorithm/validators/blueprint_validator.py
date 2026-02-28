"""Blueprint validator — final validation of the assembled blueprint."""

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4_algorithm.validators.blueprint")

VALID_GAME_TYPES = {"state_tracer", "bug_hunter", "algorithm_builder", "complexity_analyzer", "constraint_puzzle"}
TYPE_TO_FIELD = {
    "state_tracer": "stateTracerBlueprint",
    "bug_hunter": "bugHunterBlueprint",
    "algorithm_builder": "algorithmBuilderBlueprint",
    "complexity_analyzer": "complexityAnalyzerBlueprint",
    "constraint_puzzle": "constraintPuzzleBlueprint",
}


def validate_algorithm_blueprint(blueprint: dict) -> dict:
    """Validate the final AlgorithmGameBlueprint.

    Returns: {passed: bool, score: float, issues: list}
    """
    issues = []

    if not blueprint:
        return {"passed": False, "score": 0.0, "issues": [{"severity": "error", "message": "Empty blueprint"}]}

    # Check required fields
    if blueprint.get("templateType") != "ALGORITHM_GAME":
        issues.append({"severity": "error", "message": f"Wrong templateType: {blueprint.get('templateType')}"})

    if not blueprint.get("title"):
        issues.append({"severity": "warning", "message": "Missing title"})

    if not blueprint.get("algorithmName"):
        issues.append({"severity": "warning", "message": "Missing algorithmName"})

    # Single-scene validation
    if not blueprint.get("is_multi_scene"):
        game_type = blueprint.get("algorithmGameType")
        if game_type not in VALID_GAME_TYPES:
            issues.append({"severity": "error", "message": f"Invalid algorithmGameType: {game_type}"})
        else:
            field = TYPE_TO_FIELD.get(game_type)
            content = blueprint.get(field)
            if not content:
                issues.append({"severity": "error", "message": f"Missing content for {game_type} ({field})"})

    # Multi-scene validation
    else:
        scenes = blueprint.get("scenes") or []
        if not scenes:
            issues.append({"severity": "error", "message": "Multi-scene but no scenes array"})

        for i, scene in enumerate(scenes):
            if not scene.get("content"):
                issues.append({"severity": "warning", "message": f"Scene {i+1}: empty content"})
            if not scene.get("game_type"):
                issues.append({"severity": "warning", "message": f"Scene {i+1}: missing game_type"})

    # Mode configs
    if not blueprint.get("learn_config"):
        issues.append({"severity": "warning", "message": "Missing learn_config"})
    if not blueprint.get("test_config"):
        issues.append({"severity": "warning", "message": "Missing test_config"})

    errors = [i for i in issues if i["severity"] == "error"]
    passed = len(errors) == 0
    score = max(0.0, 1.0 - len(errors) * 0.25)

    return {"passed": passed, "score": score, "issues": issues}
