"""Algorithm Scene Content Generator — per-scene LLM content generation.

Runs as a parallel Send worker: one instance per scene.
Generates game-type-specific content using dedicated prompt templates.
Uses Pydantic JSON schemas for constrained decoding when available.
"""

from typing import Any

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4_algorithm.contracts import get_model_tier
from app.v4_algorithm.prompts.content_state_tracer import build_state_tracer_prompt
from app.v4_algorithm.prompts.content_bug_hunter import build_bug_hunter_prompt
from app.v4_algorithm.prompts.content_algorithm_builder import build_algorithm_builder_prompt
from app.v4_algorithm.prompts.content_complexity_analyzer import build_complexity_analyzer_prompt
from app.v4_algorithm.prompts.content_constraint_puzzle import build_constraint_puzzle_prompt
from app.v4_algorithm.schemas.algorithm_content import (
    StateTracerSceneContent,
    BugHunterSceneContent,
    AlgorithmBuilderSceneContent,
    ComplexityAnalyzerSceneContent,
    ConstraintPuzzleSceneContent,
)

logger = get_logger("gamed_ai.v4_algorithm.agents.scene_content_gen")

# Prompt builders keyed by game type
PROMPT_BUILDERS: dict[str, Any] = {
    "state_tracer": build_state_tracer_prompt,
    "bug_hunter": build_bug_hunter_prompt,
    "algorithm_builder": build_algorithm_builder_prompt,
    "complexity_analyzer": build_complexity_analyzer_prompt,
    "constraint_puzzle": build_constraint_puzzle_prompt,
}

# Schema hints for JSON extraction
SCHEMA_HINTS: dict[str, str] = {
    "state_tracer": "StateTracerSceneContent with steps array and dataStructure per step",
    "bug_hunter": "BugHunterSceneContent with rounds array, each having bugs and testCases",
    "algorithm_builder": "AlgorithmBuilderSceneContent with correct_order and distractors arrays",
    "complexity_analyzer": "ComplexityAnalyzerSceneContent with challenges array",
    "constraint_puzzle": "ConstraintPuzzleSceneContent with boardConfig and constraints",
}

# Pydantic models for JSON schema generation (constrained decoding)
GAME_TYPE_SCHEMAS: dict[str, type] = {
    "state_tracer": StateTracerSceneContent,
    "bug_hunter": BugHunterSceneContent,
    "algorithm_builder": AlgorithmBuilderSceneContent,
    "complexity_analyzer": ComplexityAnalyzerSceneContent,
    "constraint_puzzle": ConstraintPuzzleSceneContent,
}


async def algo_scene_content_gen(state: dict) -> dict:
    """Generate content for a single scene.

    Receives Send payload: {scene_plan, domain_knowledge, game_concept}
    Writes to: scene_contents_raw (reducer)
    """
    scene_plan = state.get("scene_plan") or {}
    dk = state.get("domain_knowledge") or {}
    scene_id = scene_plan.get("scene_id", "unknown")
    game_type = scene_plan.get("game_type", "state_tracer")

    logger.info(f"Scene content gen: scene={scene_id}, type={game_type}")

    prompt_builder = PROMPT_BUILDERS.get(game_type)
    if not prompt_builder:
        logger.error(f"No prompt builder for game_type '{game_type}'")
        return {
            "scene_contents_raw": [{
                "scene_id": scene_id,
                "game_type": game_type,
                "status": "failed",
                "error": f"Unsupported game_type: {game_type}",
            }],
        }

    try:
        prompt = prompt_builder(scene_plan, dk)
        schema_hint = SCHEMA_HINTS.get(game_type, "Game content JSON")

        # Get JSON schema for constrained decoding (when supported by the LLM)
        schema_cls = GAME_TYPE_SCHEMAS.get(game_type)
        json_schema = None
        if schema_cls:
            try:
                json_schema = schema_cls.model_json_schema()
            except Exception:
                logger.debug(f"Could not generate JSON schema for {game_type}, using hint only")

        # Use per-game-type model routing (pro for complex, flash for simpler)
        model_tier = get_model_tier(game_type)
        agent_name = f"v4a_scene_content_gen_{game_type}"
        logger.info(f"Content gen for {scene_id}: model_tier={model_tier}, agent={agent_name}")

        llm = get_llm_service()
        content = await llm.generate_json_for_agent(
            agent_name=agent_name,
            prompt=prompt,
            schema_hint=schema_hint,
            json_schema=json_schema,
        )

        if isinstance(content, dict):
            content.pop("_llm_metrics", None)

        if not content:
            raise ValueError("LLM returned empty content")

        # Basic validation per game type
        _validate_content(content, game_type)

        logger.info(f"Scene content gen success: scene={scene_id}, type={game_type}")

        return {
            "scene_contents_raw": [{
                "scene_id": scene_id,
                "game_type": game_type,
                "status": "success",
                "content": content,
            }],
        }

    except Exception as e:
        logger.error(f"Scene content gen failed for {scene_id}: {e}")
        return {
            "scene_contents_raw": [{
                "scene_id": scene_id,
                "game_type": game_type,
                "status": "failed",
                "error": str(e),
            }],
        }


def _validate_content(content: dict, game_type: str) -> None:
    """Basic structural validation of generated content."""
    if game_type == "state_tracer":
        if not content.get("code"):
            logger.warning("StateTracer: missing code")
        steps = content.get("steps", [])
        if len(steps) < 3:
            logger.warning(f"StateTracer: only {len(steps)} steps (expected 6+)")

    elif game_type == "bug_hunter":
        rounds = content.get("rounds", [])
        if not rounds:
            logger.warning("BugHunter: no rounds")
        for r in rounds:
            if not r.get("bugs"):
                logger.warning(f"BugHunter round '{r.get('roundId')}': no bugs")

    elif game_type == "algorithm_builder":
        blocks = content.get("correct_order", [])
        if len(blocks) < 3:
            logger.warning(f"AlgorithmBuilder: only {len(blocks)} blocks")

    elif game_type == "complexity_analyzer":
        challenges = content.get("challenges", [])
        if not challenges:
            logger.warning("ComplexityAnalyzer: no challenges")

    elif game_type == "constraint_puzzle":
        if not content.get("boardConfig"):
            logger.warning("ConstraintPuzzle: missing boardConfig")
        if not content.get("constraints"):
            logger.warning("ConstraintPuzzle: no constraints")
