"""Algorithm Blueprint Assembler — deterministic assembly of all phases.

Combines game_plan + scene_contents + scene_assets into final AlgorithmGameBlueprint.
Runs blueprint validation and sets is_degraded when issues are found.
"""

from app.utils.logging_config import get_logger
from app.v4_algorithm.schemas.algorithm_content import LearnModeConfig, TestModeConfig
from app.v4_algorithm.validators.blueprint_validator import validate_algorithm_blueprint

logger = get_logger("gamed_ai.v4_algorithm.agents.assembler")


async def algo_blueprint_assembler(state: dict) -> dict:
    """Assemble the final AlgorithmGameBlueprint.

    Reads: game_plan, game_concept, scene_contents, scene_assets, domain_knowledge
    Writes: blueprint, assembly_warnings, generation_complete
    """
    game_plan = state.get("game_plan") or {}
    game_concept = state.get("game_concept") or {}
    scene_contents = state.get("scene_contents") or {}
    scene_assets = state.get("scene_assets") or {}

    warnings: list[str] = []
    scenes_plan = game_plan.get("scenes", [])

    logger.info(
        f"Assembler: {len(scenes_plan)} scenes, "
        f"{len(scene_contents)} contents, {len(scene_assets)} assets"
    )

    # Build mode configs
    learn_config = LearnModeConfig().model_dump()
    test_config = TestModeConfig().model_dump()

    # Single-scene vs multi-scene
    is_multi_scene = len(scenes_plan) > 1

    if is_multi_scene:
        blueprint = _assemble_multi_scene(
            game_plan, game_concept, scene_contents, scene_assets,
            learn_config, test_config, warnings,
        )
    else:
        blueprint = _assemble_single_scene(
            game_plan, game_concept, scene_contents, scene_assets,
            learn_config, test_config, warnings,
        )

    # Check for degraded state: missing content or failed assets
    is_degraded = False
    failed_content = state.get("failed_content_ids") or []
    failed_assets = state.get("failed_asset_ids") or []
    if failed_content:
        is_degraded = True
        warnings.append(f"Missing content for scenes: {failed_content}")
    if failed_assets:
        is_degraded = True
        warnings.append(f"Failed assets for scenes: {failed_assets}")

    # Run blueprint validation
    validation = validate_algorithm_blueprint(blueprint)
    if not validation["passed"]:
        is_degraded = True
        for issue in validation.get("issues", []):
            warnings.append(f"Blueprint: {issue['message']}")
        logger.warning(f"Blueprint validation failed: {validation['issues']}")

    blueprint["is_degraded"] = is_degraded
    if is_degraded:
        blueprint["validation_issues"] = validation.get("issues", [])

    if warnings:
        logger.warning(f"Assembly warnings: {warnings}")

    return {
        "blueprint": blueprint,
        "assembly_warnings": warnings,
        "generation_complete": True,
        "is_degraded": is_degraded,
    }


def _assemble_single_scene(
    game_plan: dict,
    game_concept: dict,
    scene_contents: dict,
    scene_assets: dict,
    learn_config: dict,
    test_config: dict,
    warnings: list[str],
) -> dict:
    """Assemble a single-scene blueprint."""
    scenes = game_plan.get("scenes", [])
    if not scenes:
        warnings.append("No scenes in game_plan")
        return _error_blueprint(game_plan, game_concept, learn_config, test_config)

    scene = scenes[0]
    scene_id = scene.get("scene_id", "scene_1")
    game_type = scene.get("game_type", "state_tracer")

    content = scene_contents.get(scene_id, {}).get("content", {})
    if not content:
        warnings.append(f"No content for scene {scene_id}")

    asset = scene_assets.get(scene_id)
    asset_url = asset.get("image_url") if asset else None

    # Map game_type to blueprint field
    type_to_field = {
        "state_tracer": "stateTracerBlueprint",
        "bug_hunter": "bugHunterBlueprint",
        "algorithm_builder": "algorithmBuilderBlueprint",
        "complexity_analyzer": "complexityAnalyzerBlueprint",
        "constraint_puzzle": "constraintPuzzleBlueprint",
    }
    field = type_to_field.get(game_type, "stateTracerBlueprint")

    blueprint = {
        "templateType": "ALGORITHM_GAME",
        "title": game_plan.get("title", "Algorithm Game"),
        "subject": game_concept.get("algorithm_category", ""),
        "difficulty": scene.get("difficulty", "intermediate"),
        "algorithmName": game_plan.get("algorithm_name", ""),
        "algorithmCategory": game_plan.get("algorithm_category", ""),
        "narrativeIntro": game_concept.get("narrative_intro", ""),
        "totalMaxScore": game_plan.get("total_max_score", 0),
        "passThreshold": 0.6,
        "learn_config": learn_config,
        "test_config": test_config,
        "algorithmGameType": game_type,
        field: content,
        "is_multi_scene": False,
        "scene_assets": {scene_id: {"image_url": asset_url}} if asset_url else None,
    }

    return blueprint


def _assemble_multi_scene(
    game_plan: dict,
    game_concept: dict,
    scene_contents: dict,
    scene_assets: dict,
    learn_config: dict,
    test_config: dict,
    warnings: list[str],
) -> dict:
    """Assemble a multi-scene blueprint."""
    scenes_plan = game_plan.get("scenes", [])

    scene_blueprints = []
    for scene in scenes_plan:
        scene_id = scene.get("scene_id", "")
        content_entry = scene_contents.get(scene_id, {})
        content = content_entry.get("content", {})

        if not content:
            warnings.append(f"No content for scene {scene_id}")

        asset = scene_assets.get(scene_id)
        asset_url = asset.get("image_url") if asset else None

        scene_bp = {
            "scene_id": scene_id,
            "scene_number": scene.get("scene_number", 0),
            "title": scene.get("title", ""),
            "game_type": scene.get("game_type", "state_tracer"),
            "difficulty": scene.get("difficulty", "intermediate"),
            "learning_goal": scene.get("learning_goal", ""),
            "max_score": scene.get("max_score", 0),
            "content": content,
            "asset_url": asset_url,
        }
        scene_blueprints.append(scene_bp)

    blueprint = {
        "templateType": "ALGORITHM_GAME",
        "title": game_plan.get("title", "Algorithm Game"),
        "subject": game_concept.get("algorithm_category", ""),
        "difficulty": "intermediate",
        "algorithmName": game_plan.get("algorithm_name", ""),
        "algorithmCategory": game_plan.get("algorithm_category", ""),
        "narrativeIntro": game_concept.get("narrative_intro", ""),
        "totalMaxScore": game_plan.get("total_max_score", 0),
        "passThreshold": 0.6,
        "learn_config": learn_config,
        "test_config": test_config,
        "algorithmGameType": None,
        "is_multi_scene": True,
        "scenes": scene_blueprints,
        "scene_transitions": game_plan.get("scene_transitions", []),
        "scene_assets": {
            sid: scene_assets[sid]
            for sid in scene_assets
        } if scene_assets else None,
    }

    return blueprint


def _error_blueprint(
    game_plan: dict,
    game_concept: dict,
    learn_config: dict,
    test_config: dict,
) -> dict:
    """Return a minimal error blueprint."""
    return {
        "templateType": "ALGORITHM_GAME",
        "title": game_plan.get("title", "Algorithm Game"),
        "algorithmName": game_plan.get("algorithm_name", ""),
        "narrativeIntro": "Game generation encountered issues. Please try again.",
        "totalMaxScore": 0,
        "learn_config": learn_config,
        "test_config": test_config,
        "is_multi_scene": False,
    }
