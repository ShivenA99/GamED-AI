"""Content Generator (V4 Phase 2a).

Produces MechanicContent for a single mechanic. Runs in parallel
via Send API — one instance per mechanic.

Receives mechanic plan (with creative_design) + scene context via Send payload.
Uses the creative design to populate both content data AND frontend visual config fields.

State writes: mechanic_contents_raw (reducer-accumulated)
"""

import time
from typing import Any, Optional

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4.contracts import MODEL_ROUTING
from app.v4.prompts.content_generator import build_content_prompt
from app.v4.schemas.mechanic_content import get_content_model

logger = get_logger("gamed_ai.v4.content_generator")


async def content_generator(state: dict) -> dict:
    """Generate content for a single mechanic.

    This node receives a Send payload containing:
    - mechanic_plan: dict (MechanicPlan with creative_design)
    - scene_context: dict (shared context for the scene)
    - domain_knowledge: dict
    - attempt: int

    Returns: mechanic_contents_raw (list with single entry for reducer)
    """
    mechanic_plan = state.get("mechanic_plan", {})
    scene_context = state.get("scene_context", {})
    dk = state.get("domain_knowledge")
    attempt = state.get("attempt", 1)

    mechanic_id = mechanic_plan.get("mechanic_id", "unknown")
    mechanic_type = mechanic_plan.get("mechanic_type", "unknown")
    creative_design = mechanic_plan.get("creative_design", {})

    logger.info(f"Content generator for {mechanic_id} ({mechanic_type}), attempt {attempt}")

    t0 = time.time()

    # Build prompt using creative design
    prompt = build_content_prompt(
        mechanic_type=mechanic_type,
        creative_design=creative_design,
        scene_context=scene_context,
        dk=dk,
        mechanic_plan=mechanic_plan,
    )

    try:
        llm = get_llm_service()
        model_tier = MODEL_ROUTING.get(mechanic_type, "flash")
        agent_name = f"content_generator_{model_tier}"

        raw = await llm.generate_json_for_agent(
            agent_name=agent_name,
            prompt=prompt,
            schema_hint=f"{mechanic_type} content JSON",
        )
        llm_metrics = raw.pop("_llm_metrics", None) if isinstance(raw, dict) else None

        # Auto-fix common LLM omissions before Pydantic validation
        if isinstance(raw, dict) and mechanic_type == "branching_scenario":
            nodes = raw.get("nodes", [])
            if nodes and not raw.get("startNodeId"):
                raw["startNodeId"] = nodes[0].get("id", "n1") if isinstance(nodes[0], dict) else "n1"
                logger.info(f"Auto-filled missing startNodeId='{raw['startNodeId']}' for {mechanic_id}")

        # Parse through Pydantic
        content_model = get_content_model(mechanic_type)
        try:
            parsed = content_model(**raw)
            content_dict = parsed.model_dump()
        except Exception as parse_err:
            elapsed_ms = int((time.time() - t0) * 1000)
            logger.warning(f"Content parse error for {mechanic_id}: {parse_err}")
            return {
                "mechanic_contents_raw": [{
                    "mechanic_id": mechanic_id,
                    "scene_id": scene_context.get("scene_id", "unknown"),
                    "mechanic_type": mechanic_type,
                    "status": "failed",
                    "error": str(parse_err)[:200],
                    "duration_ms": elapsed_ms,
                    "content": {},
                }],
            }

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(
            f"Content generated for {mechanic_id} ({mechanic_type}) "
            f"in {elapsed_ms}ms"
        )

        out = {
            "mechanic_contents_raw": [{
                "mechanic_id": mechanic_id,
                "scene_id": scene_context.get("scene_id", "unknown"),
                "mechanic_type": mechanic_type,
                "status": "success",
                "content": content_dict,
                "duration_ms": elapsed_ms,
            }],
        }
        if llm_metrics:
            out["_llm_metrics"] = llm_metrics
        return out

    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.error(f"Content generation failed for {mechanic_id}: {e}", exc_info=True)
        return {
            "mechanic_contents_raw": [{
                "mechanic_id": mechanic_id,
                "scene_id": scene_context.get("scene_id", "unknown"),
                "mechanic_type": mechanic_type,
                "status": "failed",
                "error": str(e)[:200],
                "duration_ms": elapsed_ms,
                "content": {},
            }],
        }


def build_scene_context(
    scene_plan: dict,
    domain_knowledge: Optional[dict],
) -> dict:
    """Build shared context for content generators in a scene.

    This is a deterministic helper called by the content dispatch router,
    NOT a graph node.
    """
    scene_id = scene_plan.get("scene_id", "unknown")
    zone_labels = scene_plan.get("zone_labels", [])
    mechanics = scene_plan.get("mechanics", [])

    # Extract relevant DK
    dk_subset: dict[str, Any] = {}
    if domain_knowledge:
        # Include label descriptions for this scene's labels
        label_descs = domain_knowledge.get("label_descriptions", {})
        if label_descs:
            dk_subset["label_descriptions"] = {
                label: desc
                for label, desc in label_descs.items()
                if label in zone_labels
            }

        # Include sequence data if any mechanic needs it
        mechanic_types = {m.get("mechanic_type") for m in mechanics}
        if "sequencing" in mechanic_types or "trace_path" in mechanic_types:
            seq = domain_knowledge.get("sequence_flow_data")
            if seq:
                dk_subset["sequence_flow_data"] = seq

        if "sorting_categories" in mechanic_types or "compare_contrast" in mechanic_types:
            comp = domain_knowledge.get("comparison_data")
            if comp:
                dk_subset["comparison_data"] = comp

        # Always include canonical labels
        dk_subset["canonical_labels"] = domain_knowledge.get("canonical_labels", [])

    context = {
        "scene_id": scene_id,
        "title": scene_plan.get("title", ""),
        "learning_goal": scene_plan.get("learning_goal", ""),
        "zone_labels": zone_labels,
        "other_mechanics": [
            {"mechanic_type": m.get("mechanic_type"), "mechanic_id": m.get("mechanic_id")}
            for m in mechanics
        ],
        "dk_subset": dk_subset,
    }

    # Add scene-level creative design context
    creative = scene_plan.get("creative_design", {})
    if creative:
        context["visual_concept"] = creative.get("visual_concept", "")
        context["atmosphere"] = creative.get("atmosphere", "")
        context["color_palette_direction"] = creative.get("color_palette_direction", "")
        context["spatial_layout"] = creative.get("spatial_layout", "")
        context["scene_narrative"] = creative.get("scene_narrative", "")
        context["transition_narrative"] = creative.get("transition_narrative", "")

    return context
