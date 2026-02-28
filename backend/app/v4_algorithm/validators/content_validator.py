"""Content validator — checks generated scene content per game type.

Uses Pydantic schema validation when available, with fallback to manual checks.
"""

from pydantic import ValidationError

from app.utils.logging_config import get_logger
from app.v4_algorithm.schemas.algorithm_content import (
    StateTracerSceneContent,
    BugHunterSceneContent,
    AlgorithmBuilderSceneContent,
    ComplexityAnalyzerSceneContent,
    ConstraintPuzzleSceneContent,
)

logger = get_logger("gamed_ai.v4_algorithm.validators.content")

GAME_TYPE_TO_SCHEMA = {
    "state_tracer": StateTracerSceneContent,
    "bug_hunter": BugHunterSceneContent,
    "algorithm_builder": AlgorithmBuilderSceneContent,
    "complexity_analyzer": ComplexityAnalyzerSceneContent,
    "constraint_puzzle": ConstraintPuzzleSceneContent,
}


async def algo_content_validator(state: dict) -> dict:
    """Validate scene contents after content merge.

    Reads: scene_contents, content_retry_count
    Writes: content_validation
    """
    scene_contents = state.get("scene_contents") or {}
    if not scene_contents:
        return {
            "content_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": "No scene contents"}],
            },
        }

    issues = []
    for scene_id, entry in scene_contents.items():
        content = entry.get("content", {})
        game_type = entry.get("game_type", "")
        scene_issues = _validate_scene_content(scene_id, game_type, content)
        issues.extend(scene_issues)

    errors = [i for i in issues if i["severity"] == "error"]
    passed = len(errors) == 0
    score = max(0.0, 1.0 - len(errors) * 0.2)

    logger.info(f"Content validation: passed={passed}, issues={len(issues)}")

    return {
        "content_validation": {
            "passed": passed,
            "score": score,
            "issues": issues,
        },
    }


def _validate_scene_content(scene_id: str, game_type: str, content: dict) -> list[dict]:
    """Validate a single scene's content using Pydantic schemas."""
    issues = []

    if not content:
        issues.append({"severity": "error", "message": f"{scene_id}: empty content"})
        return issues

    schema_cls = GAME_TYPE_TO_SCHEMA.get(game_type)
    if not schema_cls:
        issues.append({"severity": "warning", "message": f"{scene_id}: unknown game_type '{game_type}'"})
        return issues

    try:
        schema_cls(**content)
    except ValidationError as e:
        for err in e.errors():
            field_path = " -> ".join(str(loc) for loc in err["loc"])
            issues.append({
                "severity": "error",
                "message": f"{scene_id}: {field_path} -- {err['msg']}",
            })
    except Exception as e:
        # Catch-all for unexpected issues (e.g. bad data types passed to constructor)
        issues.append({
            "severity": "error",
            "message": f"{scene_id}: validation error -- {str(e)}",
        })

    return issues
