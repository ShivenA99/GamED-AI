"""Scene Designer (V4 Phase 1b).

Produces a SceneCreativeDesign for a single scene. Runs in parallel
via Send API — one instance per scene.

Receives scene concept + narrative theme + DK via Send payload.
Focuses on HOW: visual style, layout, narrative integration, per-mechanic
creative direction (MechanicCreativeDesign).

State writes: scene_creative_designs_raw (reducer-accumulated)
Model: gemini-2.5-pro
"""

from typing import Any, Optional

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4.prompts.scene_designer import SYSTEM_PROMPT, build_scene_designer_prompt
from app.v4.schemas.creative_design import SceneCreativeDesign

logger = get_logger("gamed_ai.v4.scene_designer")


async def scene_designer(state: dict) -> dict:
    """Design creative direction for a single scene.

    This node receives a Send payload (NOT the full state) containing:
    - scene_index: int
    - scene_concept: dict (SceneConcept)
    - narrative_theme: str
    - domain_knowledge: dict
    - pedagogical_context: dict
    - attempt: int
    - prev_validation: dict (optional, on retry)

    Returns: scene_creative_designs_raw (list with single entry for reducer)
    """
    scene_index = state.get("scene_index", 0)
    scene_concept = state.get("scene_concept", {})
    narrative_theme = state.get("narrative_theme", "")
    dk = state.get("domain_knowledge")
    pedagogy = state.get("pedagogical_context")
    attempt = state.get("attempt", 1)
    prev_validation = state.get("prev_validation")

    scene_id = f"scene_{scene_index + 1}"
    title = scene_concept.get("title", f"Scene {scene_index + 1}")

    logger.info(
        f"Scene designer for {scene_id} ({title}), attempt {attempt}"
    )

    # Build retry info
    retry_info: Optional[str] = None
    if prev_validation and not prev_validation.get("passed", True):
        issues = prev_validation.get("issues", [])
        retry_info = "\n".join(
            f"- {i.get('message', str(i))}" if isinstance(i, dict) else f"- {i}"
            for i in issues
        )

    prompt = build_scene_designer_prompt(
        scene_concept=scene_concept,
        scene_index=scene_index,
        narrative_theme=narrative_theme,
        dk=dk,
        pedagogy=pedagogy,
        retry_info=retry_info,
    )

    try:
        llm = get_llm_service()
        raw = await llm.generate_json_for_agent(
            agent_name="scene_designer",
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            schema_hint="SceneCreativeDesign JSON with visual_concept, mechanic_designs",
        )
        llm_metrics = raw.pop("_llm_metrics", None) if isinstance(raw, dict) else None

        # Parse through Pydantic
        try:
            # Ensure scene_id is set
            raw["scene_id"] = scene_id
            design = SceneCreativeDesign(**raw)
        except Exception as parse_err:
            logger.error(f"SceneCreativeDesign parse error for {scene_id}: {parse_err}")
            return {
                "scene_creative_designs_raw": [{
                    "scene_id": scene_id,
                    "scene_index": scene_index,
                    "status": "parse_error",
                    "error": str(parse_err)[:200],
                    "raw": raw,
                }],
            }

        logger.info(
            f"Scene design for {scene_id}: "
            f"{len(design.mechanic_designs)} mechanic designs, "
            f"visual_concept={design.visual_concept[:60]}..."
        )

        out = {
            "scene_creative_designs_raw": [{
                "scene_id": scene_id,
                "scene_index": scene_index,
                "status": "success",
                "design": design.model_dump(),
            }],
        }
        if llm_metrics:
            out["_llm_metrics"] = llm_metrics
        return out

    except Exception as e:
        logger.error(f"Scene designer failed for {scene_id}: {e}", exc_info=True)
        return {
            "scene_creative_designs_raw": [{
                "scene_id": scene_id,
                "scene_index": scene_index,
                "status": "error",
                "error": str(e)[:200],
            }],
        }
