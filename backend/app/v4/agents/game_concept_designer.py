"""Game Concept Designer (V4 Phase 1a).

Produces a GameConcept from the question, pedagogical context, and domain knowledge.
Focuses on WHAT scenes, WHAT mechanics, WHY — not HOW they look/feel.

State writes: game_concept, concept_validation, concept_retry_count
Model: gemini-2.5-pro (most critical creative agent)
"""

from typing import Any, Optional

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4.contracts import build_capability_spec
from app.v4.prompts.game_concept_designer import (
    SYSTEM_PROMPT,
    build_concept_designer_prompt,
)
from app.v4.schemas.game_concept import GameConcept
from app.v4.validators.concept_validator import validate_game_concept

logger = get_logger("gamed_ai.v4.game_concept_designer")


async def game_concept_designer(state: dict) -> dict:
    """Design a game concept from the question and context.

    Reads: question_text, pedagogical_context, domain_knowledge,
           concept_validation (on retry), concept_retry_count
    Writes: game_concept, concept_validation, concept_retry_count
    """
    question_text = state.get("question_text", "")
    pedagogy = state.get("pedagogical_context")
    dk = state.get("domain_knowledge")
    prev_validation = state.get("concept_validation")
    retry_count = state.get("concept_retry_count", 0)

    logger.info(
        f"Game concept designer "
        f"{'(retry {})'.format(retry_count) if retry_count > 0 else '(initial)'}: "
        f"{question_text[:80]}..."
    )

    # Build retry info if applicable
    retry_info: Optional[str] = None
    if prev_validation and not prev_validation.get("passed", True):
        issues = prev_validation.get("issues", [])
        issue_messages = [
            i.get("message", str(i)) if isinstance(i, dict) else str(i)
            for i in issues
        ]
        retry_info = "\n".join(f"- {msg}" for msg in issue_messages)

    capability_spec = build_capability_spec()

    prompt = build_concept_designer_prompt(
        question=question_text,
        pedagogy=pedagogy,
        dk=dk,
        capability_spec=capability_spec,
        retry_info=retry_info,
    )

    try:
        llm = get_llm_service()
        raw = await llm.generate_json_for_agent(
            agent_name="game_concept_designer",
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            schema_hint="GameConcept JSON with title, scenes, mechanics, narrative",
        )
        llm_metrics = raw.pop("_llm_metrics", None) if isinstance(raw, dict) else None

        # Parse through Pydantic
        try:
            concept = GameConcept(**raw)
        except Exception as parse_err:
            logger.error(f"GameConcept parse error: {parse_err}")
            # Build a clear error message listing missing fields
            raw_keys = set(raw.keys()) if isinstance(raw, dict) else set()
            required = {"title", "subject", "difficulty", "estimated_duration_minutes",
                        "narrative_theme", "narrative_intro", "completion_message",
                        "all_zone_labels", "scenes"}
            missing = required - raw_keys
            missing_msg = (
                f"Missing required fields: {', '.join(sorted(missing))}. "
                if missing else ""
            )
            hint = (
                f"{missing_msg}"
                "Your JSON MUST include: title, subject, difficulty, "
                "estimated_duration_minutes, narrative_theme, narrative_intro, "
                "completion_message, all_zone_labels (list, can be []), and "
                "scenes (list of scene objects, at least 1 scene with mechanics)."
            )
            out = {
                "game_concept": raw,
                "concept_validation": {
                    "passed": False,
                    "score": 0.0,
                    "issues": [
                        {"severity": "error", "message": hint}
                    ],
                },
                "concept_retry_count": retry_count + 1,
            }
            if llm_metrics:
                out["_llm_metrics"] = llm_metrics
            return out

        # Validate
        validation = validate_game_concept(concept)

        logger.info(
            f"Game concept validated: passed={validation.passed}, "
            f"score={validation.score}, scenes={len(concept.scenes)}"
        )

        out = {
            "game_concept": concept.model_dump(),
            "concept_validation": validation.model_dump(),
            "concept_retry_count": retry_count + 1,
        }
        if llm_metrics:
            out["_llm_metrics"] = llm_metrics
        return out

    except Exception as e:
        logger.error(f"Game concept designer failed: {e}", exc_info=True)
        return {
            "game_concept": None,
            "concept_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": f"LLM call failed: {e}"}],
            },
            "concept_retry_count": retry_count + 1,
            "error_message": f"Game concept designer failed: {e}",
        }
