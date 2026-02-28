"""Content Build Node (V4).

Single node that loops through all scenes and mechanics sequentially:
1. For each scene → for each mechanic: generate content, validate, retry once
2. For each scene: design interactions (scoring, feedback, transitions)

State writes: mechanic_contents, interaction_results
"""

import json
import time
from typing import Any, Optional

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4.contracts import MODEL_ROUTING, CONTENT_ONLY_MECHANICS
from app.v4.helpers.dk_field_resolver import project_dk_for_mechanic
from app.v4.prompts.content_generator import build_content_prompt
from app.v4.prompts.interaction_designer import build_interaction_prompt
from app.v4.prompts.retry import condense_mechanic_content
from app.v4.schemas.mechanic_content import get_content_model
from app.v4.schemas.game_plan import MechanicPlan
from app.v4.validators.content_validator import validate_mechanic_content

logger = get_logger("gamed_ai.v4.content_builder")


async def content_build_node(state: dict) -> dict:
    """Generate content for all mechanics and interaction designs for all scenes.

    Reads: game_plan, domain_knowledge, pedagogical_context
    Writes: mechanic_contents, interaction_results, is_degraded

    This node is sequential — no parallelism. Content for each mechanic
    is generated one at a time, validated, and retried once on failure.
    """
    game_plan = state.get("game_plan")
    dk = state.get("domain_knowledge") or {}
    pedagogy = state.get("pedagogical_context")

    if not game_plan:
        logger.error("No game plan available")
        return {
            "mechanic_contents": [],
            "interaction_results": [],
            "error_message": "Content builder: no game plan",
        }

    scenes = game_plan.get("scenes", [])
    distractor_labels = game_plan.get("distractor_labels", [])
    all_mechanic_contents: list[dict[str, Any]] = []
    all_interaction_results: list[dict[str, Any]] = []
    sub_stages: list[dict[str, Any]] = []
    is_degraded = False

    llm = get_llm_service()

    for scene in scenes:
        scene_id = scene.get("scene_id", "unknown")
        scene_context = {
            "scene_id": scene_id,
            "title": scene.get("title", ""),
            "learning_goal": scene.get("learning_goal", ""),
        }
        zone_labels = scene.get("zone_labels", [])
        mechanics = scene.get("mechanics", [])

        logger.info(f"Processing scene {scene_id}: {len(mechanics)} mechanics")

        scene_contents: list[dict[str, Any]] = []

        # Phase 1: Generate content for each mechanic
        for mech in mechanics:
            mechanic_id = mech.get("mechanic_id", "unknown")
            mechanic_type = mech.get("mechanic_type", "unknown")
            content_brief = mech.get("content_brief", {})
            mech_zone_labels = mech.get("zone_labels_used", [])

            logger.info(f"  Generating content for {mechanic_id} ({mechanic_type})")

            # Project DK fields for this mechanic
            dk_fields_needed = content_brief.get("dk_fields_needed", [])
            dk_subset = project_dk_for_mechanic(dk, dk_fields_needed)

            # Build prompt
            prompt = build_content_prompt(
                mechanic_type=mechanic_type,
                content_brief=content_brief,
                scene_context=scene_context,
                dk_subset=dk_subset,
                zone_labels=mech_zone_labels,
                distractor_labels=distractor_labels if mechanic_type == "drag_drop" else None,
            )

            # Generate content (with one retry on validation failure)
            sub_stage_id = f"content_{mechanic_type}_{scene_id}"
            t0 = time.time()
            content_result, attempt_records = await _generate_and_validate(
                llm=llm,
                mechanic_type=mechanic_type,
                mechanic_id=mechanic_id,
                mechanic_plan=mech,
                prompt=prompt,
                scene_context=scene_context,
                dk_subset=dk_subset,
                zone_labels=mech_zone_labels,
                distractor_labels=distractor_labels,
            )
            elapsed_ms = int((time.time() - t0) * 1000)

            # Record sub-stage for observability
            model_tier = MODEL_ROUTING.get(mechanic_type, "flash")
            sub_stages.append({
                "id": sub_stage_id,
                "name": f"Generate {mechanic_type} content ({scene_id})",
                "type": "content_generation",
                "mechanic_type": mechanic_type,
                "scene_id": scene_id,
                "status": "success" if content_result is not None else "failed",
                "duration_ms": elapsed_ms,
                "model": f"content_builder_{model_tier}",
                "attempt": len(attempt_records),
                "validation_passed": content_result is not None,
                "error": attempt_records[-1].get("error") if attempt_records and content_result is None else None,
                "input_summary": {
                    "zone_labels": mech_zone_labels,
                    "mechanic_type": mechanic_type,
                    "scene_title": scene_context.get("title", ""),
                    "learning_goal": scene_context.get("learning_goal", ""),
                    "content_brief": {k: v for k, v in content_brief.items() if k != "dk_fields_needed"},
                },
                "output_summary": content_result if content_result else {},
                "attempts": attempt_records,
            })

            if content_result is None:
                # Failed after retry — mark as degraded
                logger.warning(f"  Content generation FAILED for {mechanic_id}")
                all_mechanic_contents.append({
                    "mechanic_id": mechanic_id,
                    "scene_id": scene_id,
                    "mechanic_type": mechanic_type,
                    "status": "failed",
                    "content": {},
                })
                is_degraded = True
            else:
                all_mechanic_contents.append({
                    "mechanic_id": mechanic_id,
                    "scene_id": scene_id,
                    "mechanic_type": mechanic_type,
                    "status": "success",
                    "content": content_result,
                })
                scene_contents.append({
                    "mechanic_id": mechanic_id,
                    "scene_id": scene_id,
                    "mechanic_type": mechanic_type,
                    "content": content_result,
                })

        # Phase 2: Design interactions for this scene
        if scene_contents:
            t0_interaction = time.time()
            interaction_result = await _generate_interaction(
                llm=llm,
                scene_plan=scene,
                mechanic_contents=scene_contents,
                pedagogy=pedagogy,
            )
            interaction_ms = int((time.time() - t0_interaction) * 1000)

            sub_stages.append({
                "id": f"interaction_{scene_id}",
                "name": f"Design interactions ({scene_id})",
                "type": "interaction_design",
                "mechanic_type": "multi",
                "scene_id": scene_id,
                "status": "success" if interaction_result else "failed",
                "duration_ms": interaction_ms,
                "model": "interaction_designer",
                "attempt": 1,
                "validation_passed": interaction_result is not None,
                "error": None,
                "input_summary": {
                    "mechanic_count": len(scene_contents),
                    "mechanic_types": [c.get("mechanic_type") for c in scene_contents],
                    "scene_title": scene.get("title", ""),
                },
                "output_summary": interaction_result if interaction_result else {},
            })

            if interaction_result:
                all_interaction_results.append(interaction_result)
        else:
            logger.warning(f"  No successful contents for scene {scene_id}, skipping interaction")

    logger.info(f"Content build complete: {len(all_mechanic_contents)} mechanics, "
                f"{len(all_interaction_results)} interaction results, "
                f"degraded={is_degraded}")

    result: dict[str, Any] = {
        "mechanic_contents": all_mechanic_contents,
        "interaction_results": all_interaction_results,
        "_sub_stages": sub_stages,
    }
    if is_degraded:
        result["is_degraded"] = True

    return result


async def _generate_and_validate(
    llm: Any,
    mechanic_type: str,
    mechanic_id: str,
    mechanic_plan: dict,
    prompt: str,
    scene_context: dict,
    dk_subset: dict,
    zone_labels: list[str],
    distractor_labels: list[str],
    max_retries: int = 1,
) -> tuple[Optional[dict], list[dict]]:
    """Generate mechanic content with validation and retry.

    Returns (validated_content_dict_or_None, attempt_records).
    """
    content_model = get_content_model(mechanic_type)
    attempt_records: list[dict] = []

    for attempt in range(max_retries + 1):
        t_attempt = time.time()
        try:
            # Select model based on mechanic routing
            model_tier = MODEL_ROUTING.get(mechanic_type, "flash")
            agent_name = f"content_builder_{model_tier}"

            raw = await llm.generate_json_for_agent(
                agent_name=agent_name,
                prompt=prompt,
                schema_hint=f"{content_model.__name__} JSON",
            )
            # Extract LLM metrics (includes prompt/response previews for observability)
            llm_call_metrics = raw.pop("_llm_metrics", {}) if isinstance(raw, dict) else {}

            # Parse through Pydantic
            try:
                parsed = content_model(**raw)
                content_dict = parsed.model_dump()
            except Exception as parse_err:
                attempt_ms = int((time.time() - t_attempt) * 1000)
                attempt_records.append({
                    "attempt": attempt + 1, "duration_ms": attempt_ms,
                    "model": agent_name, "status": "parse_error",
                    "error": str(parse_err)[:200],
                    "prompt_preview": llm_call_metrics.get("prompt_preview"),
                    "response_preview": llm_call_metrics.get("response_preview"),
                })
                logger.warning(f"  Parse error (attempt {attempt + 1}): {parse_err}")
                if attempt < max_retries:
                    # Rebuild prompt with error
                    prompt = _add_retry_context(prompt, str(parse_err), raw)
                    continue
                return None, attempt_records

            # Validate content against mechanic plan
            # mechanic_plan is a plain dict from game_plan JSON — convert to Pydantic
            mech_plan_obj = MechanicPlan(**mechanic_plan)
            validation = validate_mechanic_content(content_dict, mech_plan_obj)

            if validation.passed:
                attempt_ms = int((time.time() - t_attempt) * 1000)
                attempt_records.append({
                    "attempt": attempt + 1, "duration_ms": attempt_ms,
                    "model": agent_name, "status": "success",
                    "prompt_preview": llm_call_metrics.get("prompt_preview"),
                    "response_preview": llm_call_metrics.get("response_preview"),
                })
                logger.info(f"  Content valid for {mechanic_id} (attempt {attempt + 1})")
                return content_dict, attempt_records

            # Validation failed
            errors_str = "; ".join(i.message for i in validation.errors)
            attempt_ms = int((time.time() - t_attempt) * 1000)
            attempt_records.append({
                "attempt": attempt + 1, "duration_ms": attempt_ms,
                "model": agent_name, "status": "validation_failed",
                "error": errors_str[:200],
                "prompt_preview": llm_call_metrics.get("prompt_preview"),
                "response_preview": llm_call_metrics.get("response_preview"),
            })
            logger.warning(f"  Validation failed (attempt {attempt + 1}): {errors_str}")

            if attempt < max_retries:
                prompt = _add_retry_context(prompt, errors_str, raw)
                continue

            # Last attempt failed — return content anyway with warning
            logger.warning(f"  Returning content despite validation failures for {mechanic_id}")
            return content_dict, attempt_records

        except Exception as e:
            attempt_ms = int((time.time() - t_attempt) * 1000)
            attempt_records.append({
                "attempt": attempt + 1, "duration_ms": attempt_ms,
                "model": f"content_builder_{MODEL_ROUTING.get(mechanic_type, 'flash')}",
                "status": "error", "error": str(e)[:200],
            })
            logger.error(f"  Content generation error (attempt {attempt + 1}): {e}")
            if attempt >= max_retries:
                return None, attempt_records

    return None, attempt_records


def _add_retry_context(prompt: str, error: str, previous_output: Any) -> str:
    """Add retry context to a prompt."""
    condensed = condense_mechanic_content(previous_output) if previous_output else "{}"
    return (
        f"{prompt}\n\n"
        f"## RETRY — Previous Attempt Failed\n"
        f"Error: {error}\n\n"
        f"Previous output:\n{condensed}\n\n"
        f"Fix the errors and return corrected JSON."
    )


async def _generate_interaction(
    llm: Any,
    scene_plan: dict,
    mechanic_contents: list[dict],
    pedagogy: Optional[dict],
) -> Optional[dict]:
    """Generate interaction design (scoring, feedback, transitions) for a scene."""
    scene_id = scene_plan.get("scene_id", "unknown")
    logger.info(f"  Generating interaction design for scene {scene_id}")

    prompt = build_interaction_prompt(
        scene_plan=scene_plan,
        mechanic_contents=mechanic_contents,
        pedagogy=pedagogy,
    )

    try:
        raw = await llm.generate_json_for_agent(
            agent_name="interaction_designer",
            prompt=prompt,
            schema_hint="SceneInteractionResult with mechanic_scoring, mechanic_feedback, mode_transitions",
        )
        if isinstance(raw, dict):
            raw.pop("_llm_metrics", None)  # Metrics tracked by instrumentation wrapper

        # Validate score arithmetic
        mechanics = scene_plan.get("mechanics", [])
        for mech in mechanics:
            mid = mech.get("mechanic_id")
            scoring = (raw.get("mechanic_scoring") or {}).get(mid)
            if scoring:
                expected_max = mech.get("points_per_item", 10) * mech.get("expected_item_count", 1)
                actual_max = scoring.get("max_score", 0)
                if actual_max != expected_max:
                    logger.warning(
                        f"  Score mismatch for {mid}: expected {expected_max}, got {actual_max}. Fixing."
                    )
                    scoring["max_score"] = expected_max
                    scoring["points_per_correct"] = mech.get("points_per_item", 10)

        # Ensure scene_id is set
        raw["scene_id"] = scene_id

        logger.info(f"  Interaction design generated for scene {scene_id}")
        return raw

    except Exception as e:
        logger.error(f"  Interaction design failed for {scene_id}: {e}")
        # Generate fallback interaction result
        return _fallback_interaction(scene_plan)


def _fallback_interaction(scene_plan: dict) -> dict:
    """Generate a minimal fallback interaction result."""
    scene_id = scene_plan.get("scene_id", "unknown")
    mechanics = scene_plan.get("mechanics", [])

    scoring = {}
    feedback = {}
    for mech in mechanics:
        mid = mech.get("mechanic_id")
        pts = mech.get("points_per_item", 10)
        count = mech.get("expected_item_count", 1)
        scoring[mid] = {
            "strategy": "per_correct",
            "points_per_correct": pts,
            "max_score": pts * count,
            "partial_credit": True,
        }
        feedback[mid] = {
            "on_correct": "Correct!",
            "on_incorrect": "Not quite. Try again.",
            "on_completion": "Well done!",
            "misconceptions": [],
        }

    return {
        "scene_id": scene_id,
        "mechanic_scoring": scoring,
        "mechanic_feedback": feedback,
        "mode_transitions": [],
    }
