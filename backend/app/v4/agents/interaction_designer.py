"""Interaction Designer (V4 Phase 2b).

Per-scene interaction designer. Runs in parallel via Send API — one instance
per scene. Produces scoring rules, feedback messages, and mode transitions.

Receives Send payload with scene_plan + mechanic_contents for that scene.
State writes: interaction_results_raw (reducer-accumulated)
"""

import time
from typing import Any

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4.prompts.interaction_designer import build_interaction_prompt
from app.v4.schemas.interaction import SceneInteractionResult

logger = get_logger("gamed_ai.v4.interaction_designer")


async def interaction_designer(state: dict) -> dict:
    """Design interactions for a single scene.

    Receives via Send payload:
    - scene_plan: dict (ScenePlan for this scene)
    - mechanic_contents: list[dict] (content results for this scene's mechanics)
    - pedagogical_context: dict (optional)

    Returns: interaction_results_raw (list with single entry for reducer)
    """
    scene_plan = state.get("scene_plan", {})
    mechanic_contents = state.get("mechanic_contents", [])
    pedagogy = state.get("pedagogical_context")

    scene_id = scene_plan.get("scene_id", "unknown")
    mechanics = scene_plan.get("mechanics", [])

    logger.info(
        f"Interaction designer for {scene_id}: "
        f"{len(mechanics)} mechanics, {len(mechanic_contents)} contents"
    )

    t0 = time.time()

    prompt = build_interaction_prompt(
        scene_plan=scene_plan,
        mechanic_contents=mechanic_contents,
        pedagogy=pedagogy,
    )

    try:
        llm = get_llm_service()
        raw = await llm.generate_json_for_agent(
            agent_name="interaction_designer_pro",
            prompt=prompt,
            schema_hint="SceneInteractionResult JSON with scoring, feedback, transitions",
        )
        llm_metrics = raw.pop("_llm_metrics", None) if isinstance(raw, dict) else None

        # Parse through Pydantic
        try:
            parsed = SceneInteractionResult(**raw)
            result_dict = parsed.model_dump(by_alias=True)
        except Exception as parse_err:
            elapsed_ms = int((time.time() - t0) * 1000)
            logger.warning(f"Interaction parse error for {scene_id}: {parse_err}")
            # Fall back to raw dict with scene_id
            result_dict = {**raw, "scene_id": scene_id}

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(f"Interaction design done for {scene_id} in {elapsed_ms}ms")

        out = {
            "interaction_results_raw": [{
                "scene_id": scene_id,
                "status": "success",
                "duration_ms": elapsed_ms,
                **result_dict,
            }],
        }
        if llm_metrics:
            out["_llm_metrics"] = llm_metrics
        return out

    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.error(f"Interaction design failed for {scene_id}: {e}", exc_info=True)

        # Build fallback scoring/feedback from plan
        fallback_scoring = {}
        fallback_feedback = {}
        for mp in mechanics:
            mid = mp.get("mechanic_id", "")
            fallback_scoring[mid] = {
                "strategy": "per_correct",
                "points_per_correct": mp.get("points_per_item", 10),
                "max_score": mp.get("max_score", 0),
                "partial_credit": True,
            }
            fallback_feedback[mid] = {
                "on_correct": "Correct!",
                "on_incorrect": "Try again.",
                "on_completion": "Well done!",
                "misconceptions": [],
            }

        return {
            "interaction_results_raw": [{
                "scene_id": scene_id,
                "status": "degraded",
                "error": str(e)[:200],
                "duration_ms": elapsed_ms,
                "mechanic_scoring": fallback_scoring,
                "mechanic_feedback": fallback_feedback,
                "mode_transitions": [],
            }],
        }
