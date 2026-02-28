"""
Scene Validator -- Deterministic validator for scene_specs_v3.

No LLM calls. Reads scene_specs_v3 and game_design_v3 from state,
runs validate_scene_specs() cross-stage contract checks, and writes
scene_validation_v3 = {passed, score, issues}.

Increments _v3_scene_retries on each invocation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.scene_spec_v3 import validate_scene_specs
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.scene_validator")


async def scene_validator_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Scene Validator Agent -- deterministic validation of scene_specs_v3.

    Reads: scene_specs_v3, game_design_v3
    Writes: scene_validation_v3, _v3_scene_retries
    """
    logger.info("SceneValidator: Starting scene spec validation")

    scene_specs = state.get("scene_specs_v3")
    game_design = state.get("game_design_v3") or {}
    retry_count = state.get("_v3_scene_retries", 0)

    # Guard: no scene specs to validate
    if not scene_specs:
        logger.warning("SceneValidator: No scene_specs_v3 in state")
        validation = {
            "passed": False,
            "score": 0.0,
            "issues": ["No scene_specs_v3 found in state. scene_architect_v3 may have failed."],
        }
        return {
            **state,
            "current_agent": "scene_validator",
            "scene_validation_v3": validation,
            "_v3_scene_retries": retry_count + 1,
        }

    # Ensure scene_specs is a list of dicts
    if not isinstance(scene_specs, list):
        logger.warning(f"SceneValidator: scene_specs_v3 is not a list, got {type(scene_specs)}")
        validation = {
            "passed": False,
            "score": 0.0,
            "issues": [f"scene_specs_v3 must be a list, got {type(scene_specs).__name__}"],
        }
        return {
            **state,
            "current_agent": "scene_validator",
            "scene_validation_v3": validation,
            "_v3_scene_retries": retry_count + 1,
        }

    # Run cross-stage validation
    try:
        validation = validate_scene_specs(scene_specs, game_design)
    except Exception as e:
        logger.error(f"SceneValidator: validate_scene_specs raised: {e}", exc_info=True)
        validation = {
            "passed": False,
            "score": 0.0,
            "issues": [f"Validation function error: {str(e)[:500]}"],
        }

    passed = validation.get("passed", False)
    score = validation.get("score", 0.0)
    issues = validation.get("issues", [])

    logger.info(
        f"SceneValidator: passed={passed}, score={score:.3f}, "
        f"issues={len(issues)}, retry={retry_count}"
    )

    if issues:
        for issue in issues[:5]:
            logger.info(f"  Issue: {issue}")

    return {
        **state,
        "current_agent": "scene_validator",
        "scene_validation_v3": validation,
        "_v3_scene_retries": retry_count + 1,
    }
