"""Game Designer Agent (V4).

Produces a GamePlan from the question, pedagogical context, and domain knowledge.
Uses the game_designer prompt builder and GamePlan Pydantic schema.

State writes: game_plan, design_validation
Model: gemini-2.5-pro (always — most critical agent)
"""

from typing import Any, Optional

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4.contracts import build_capability_spec
from app.v4.prompts.game_designer import SYSTEM_PROMPT, build_game_designer_prompt
from app.v4.prompts.retry import build_retry_section, condense_game_plan
from app.v4.schemas.game_plan import GamePlan
from app.v4.validators.game_plan_validator import validate_game_plan

logger = get_logger("gamed_ai.v4.game_designer")


async def game_designer(state: dict) -> dict:
    """Design a game plan from the question and context.

    Reads: question_text, pedagogical_context, domain_knowledge,
           design_validation (on retry), design_retry_count
    Writes: game_plan, design_validation

    Args:
        state: V4MainState dict.

    Returns:
        Dict to merge into state.
    """
    question_text = state.get("question_text", "")
    pedagogy = state.get("pedagogical_context")
    dk = state.get("domain_knowledge")
    prev_validation = state.get("design_validation")
    retry_count = state.get("design_retry_count", 0)

    logger.info(f"Game designer {'(retry {})'.format(retry_count) if retry_count > 0 else '(initial)'}: "
                f"{question_text[:80]}...")

    # Build retry section if retrying
    retry_info: Optional[str] = None
    if prev_validation and not prev_validation.get("passed", True):
        # Reconstruct ValidationResult for retry section
        from app.v4.schemas.validation import ValidationResult, ValidationIssue
        issues = [
            ValidationIssue(**i) if isinstance(i, dict) else i
            for i in prev_validation.get("issues", [])
        ]
        vr = ValidationResult(
            passed=False,
            score=prev_validation.get("score", 0.0),
            issues=issues,
        )
        prev_plan = state.get("game_plan", {})
        condensed = condense_game_plan(prev_plan) if prev_plan else "{}"
        retry_info = build_retry_section(vr, condensed)

    # Build capability spec
    capability_spec = build_capability_spec()

    # Build prompt
    prompt = build_game_designer_prompt(
        question=question_text,
        pedagogy=pedagogy,
        dk=dk,
        capability_spec=capability_spec,
        retry_info=retry_info,
    )

    try:
        llm = get_llm_service()
        raw = await llm.generate_json_for_agent(
            agent_name="game_designer",
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            schema_hint="GamePlan JSON with scenes, mechanics, zone_labels",
        )
        llm_metrics = None
        if isinstance(raw, dict):
            llm_metrics = raw.pop("_llm_metrics", None)

        # Parse through Pydantic for validation
        try:
            plan = GamePlan(**raw)
        except Exception as parse_err:
            logger.error(f"GamePlan parse error: {parse_err}")
            return {
                "game_plan": raw,  # Keep raw for retry
                "design_validation": {
                    "passed": False,
                    "score": 0.0,
                    "issues": [{"severity": "error", "message": f"Schema parse error: {parse_err}"}],
                },
                "design_retry_count": retry_count + 1,
            }

        # Validate (also computes scores)
        validation = validate_game_plan(plan)

        logger.info(f"Game plan validated: passed={validation.passed}, "
                    f"score={validation.score}, "
                    f"scenes={len(plan.scenes)}, "
                    f"total_max_score={plan.total_max_score}")

        out: dict = {
            "game_plan": plan.model_dump(),
            "design_validation": {
                "passed": validation.passed,
                "score": validation.score,
                "issues": [i.model_dump() for i in validation.issues],
            },
            "design_retry_count": retry_count + 1,
        }
        if llm_metrics:
            out["_llm_metrics"] = llm_metrics
        return out

    except Exception as e:
        logger.error(f"Game designer failed: {e}", exc_info=True)
        return {
            "game_plan": None,
            "design_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": f"LLM call failed: {e}"}],
            },
            "design_retry_count": retry_count + 1,
            "error_message": f"Game designer failed: {e}",
        }
