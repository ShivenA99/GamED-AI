"""
GAME_DESIGNER - HAD v3 Unified Game Design Agent

Replaces the 4-stage game_orchestrator with a single Gemini vision call.
Uses visual context (diagram image) during design for unified reasoning.

Old Architecture (4 sequential LLM calls):
  game_orchestrator
  ├─ plan_game_tool → game_planner agent
  ├─ design_structure_tool → scene_stage1_structure agent
  ├─ design_assets_tool → scene_stage2_assets agent
  └─ design_interactions_tool → scene_stage3_interactions agent

New Architecture (1 unified LLM call):
  game_designer
  └─ Single Gemini call with image context
     Returns: game_plan + structure + assets + interactions

Benefits:
- 75% fewer LLM calls (1 vs 4)
- Visual context during design (sees the actual diagram)
- Unified reasoning (no context loss between stages)
- ~50% faster than sequential approach
- Better coherence across design elements

Inputs from Vision Cluster:
    - diagram_zones: Detected zones with polygon/circle bounds
    - zone_groups: Hierarchical groupings
    - generated_diagram_path: Image path for visual context

Inputs from Research Cluster:
    - domain_knowledge: Canonical labels, hierarchy
    - pedagogical_context: Bloom's level, subject
    - template_selection: Selected template

Outputs to Output Cluster:
    - game_plan: Learning objectives, mechanics, scoring
    - scene_structure: Layout and regions
    - scene_assets: Visual assets
    - scene_interactions: Behaviors and animations
    - game_sequence: Multi-scene progression (if needed)
    - design_trace: Reasoning trace for UI visualization
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.had.react_loop import TraceBuilder
from app.services.gemini_service import (
    get_gemini_service,
    GeminiModel,
    Zone,
    ZoneGroup,
    ZoneShape,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.game_designer")

# Prompt template path
PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "had" / "unified_game_design.txt"


async def game_designer(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    HAD v3 Unified Game Design Agent.

    Single Gemini vision call with image context that returns complete game design:
    - game_plan: Game mechanics and objectives
    - scene_structure: Layout and regions
    - scene_assets: Visual asset specifications
    - scene_interactions: Behaviors and animations
    - game_sequence: Multi-scene progression (if multi-scene)

    This replaces the 4-stage sequential approach in game_orchestrator.
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")
    needs_multi_scene = state.get("needs_multi_scene", False)

    logger.info(
        f"GAME_DESIGNER starting for {question_id}, "
        f"template={template_type}, multi_scene={needs_multi_scene}"
    )

    # Initialize trace builder
    trace = TraceBuilder(phase="unified_game_design")

    start_time = datetime.utcnow()

    # Extract inputs
    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    pedagogical_context = state.get("pedagogical_context", {})
    diagram_zones = state.get("diagram_zones", [])
    zone_groups = state.get("zone_groups", [])
    generated_diagram_path = state.get("generated_diagram_path")
    query_intent = state.get("query_intent", {})

    # Convert diagram_zones to Zone objects
    zones = _convert_to_zones(diagram_zones)
    groups = _convert_to_zone_groups(zone_groups)

    blooms_level = pedagogical_context.get("blooms_level", "UNDERSTAND")
    subject = pedagogical_context.get("subject", "Biology")
    canonical_labels = domain_knowledge.get("canonical_labels", [])

    trace.thought(
        f"Starting unified game design for '{template_type}' template. "
        f"Subject: {subject}, Bloom's level: {blooms_level}. "
        f"Have {len(zones)} zones and {len(groups)} zone groups. "
        f"Image path: {generated_diagram_path}. "
        f"Multi-scene required: {needs_multi_scene}."
    )

    # Check for image path
    logger.info(f"game_designer: Looking for image, generated_diagram_path={generated_diagram_path}")
    if not generated_diagram_path or not Path(generated_diagram_path).exists():
        # Try fallback paths
        fallback_paths = [
            state.get("cleaned_image_path"),
            state.get("diagram_image"),
        ]
        logger.info(f"game_designer: Trying fallback paths: {fallback_paths}")
        for path in fallback_paths:
            if path and Path(path).exists():
                generated_diagram_path = path
                logger.info(f"game_designer: Using fallback path: {path}")
                break

    if not generated_diagram_path or not Path(generated_diagram_path).exists():
        logger.warning(f"No diagram image found (path={generated_diagram_path}), using text-only design")
        trace.thought("No diagram image available, proceeding with text-only design")
        return await _fallback_text_only_design(state, ctx, trace, start_time)

    trace.action(
        tool="gemini_game_designer",
        args={
            "model": "gemini-3-flash",
            "zones_count": len(zones),
            "groups_count": len(groups),
            "blooms_level": blooms_level,
            "multi_scene": needs_multi_scene,
        },
        description="Single Gemini vision call for complete game design"
    )

    try:
        # Get Gemini service
        gemini_service = get_gemini_service()

        call_start = time.time()

        # Single unified call
        result = await gemini_service.design_game(
            image_path=generated_diagram_path,
            zones=zones,
            zone_groups=groups,
            pedagogical_context=pedagogical_context,
            domain_knowledge=domain_knowledge,
            needs_multi_scene=needs_multi_scene,
            model=GeminiModel.FLASH_3,
        )

        call_duration_ms = int((time.time() - call_start) * 1000)

        trace.observation(
            f"Unified game design complete in {call_duration_ms}ms",
            result={
                "has_game_plan": result.game_plan is not None,
                "has_scene_structure": result.scene_structure is not None,
                "has_scene_assets": result.scene_assets is not None,
                "has_scene_interactions": result.scene_interactions is not None,
                "is_multi_scene": result.is_multi_scene,
            },
            tool="gemini_game_designer",
            duration_ms=call_duration_ms
        )

        # Enrich game plan with zone data for INTERACTIVE_DIAGRAM
        game_plan = result.game_plan or {}
        if template_type == "INTERACTIVE_DIAGRAM":
            game_plan["diagram_zones"] = diagram_zones
            game_plan["zone_groups"] = zone_groups

        total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        trace.result(
            f"Unified design complete in {total_duration_ms:.0f}ms (single LLM call)",
            result={
                "call_duration_ms": call_duration_ms,
                "total_duration_ms": total_duration_ms,
                "is_multi_scene": result.is_multi_scene,
            }
        )

        # Track LLM metrics
        if ctx:
            # Get metrics from service
            token_summary = gemini_service.get_token_summary()
            ctx.set_llm_metrics(
                model="gemini-3-flash",
                prompt_tokens=token_summary.get("total_input_tokens", 0),
                completion_tokens=token_summary.get("total_output_tokens", 0),
                latency_ms=call_duration_ms,
            )

        logger.info(
            f"GAME_DESIGNER complete: unified call={call_duration_ms}ms, "
            f"total={total_duration_ms:.0f}ms"
        )

        # Debug: Log that we're about to create the output dict
        logger.info("GAME_DESIGNER: Creating output dict with design_metadata")

        # Debug: Check trace object
        logger.info(f"GAME_DESIGNER: trace object type: {type(trace)}")
        completed_trace = trace.complete(success=True)
        logger.info(f"GAME_DESIGNER: completed_trace type: {type(completed_trace)}")
        trace_dict = completed_trace.to_dict() if completed_trace else {}
        logger.info(f"GAME_DESIGNER: trace_dict keys: {list(trace_dict.keys()) if trace_dict else 'None'}")

        output = {
            "game_plan": game_plan,
            "scene_structure": result.scene_structure or {},
            "scene_assets": result.scene_assets or {},
            "scene_interactions": result.scene_interactions or {},
            "design_trace": [trace_dict],
            "design_metadata": {
                "total_duration_ms": total_duration_ms,
                "call_duration_ms": call_duration_ms,
                "designer": "had_v3_game_designer",
                "model": "gemini-3-flash",
                "unified_call": True,
                "completed_at": datetime.utcnow().isoformat(),
            },
            "current_agent": "game_designer",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

        # Add multi-scene sequence if applicable
        if result.is_multi_scene and result.game_sequence:
            output["game_sequence"] = result.game_sequence
            output["needs_multi_scene"] = True
            output["num_scenes"] = len(result.game_sequence.get("scenes", []))
            output["scene_progression_type"] = result.game_sequence.get("progression_type", "linear")

        # Debug: Log output keys before return
        logger.info(f"GAME_DESIGNER: Returning output with keys: {list(output.keys())}")
        logger.info(f"GAME_DESIGNER: design_metadata = {output.get('design_metadata')}")

        return output

    except Exception as e:
        import traceback
        logger.error(f"Unified game design failed: {e}")
        logger.error(f"Exception traceback:\n{traceback.format_exc()}")
        trace.error(f"Unified game design failed: {str(e)}")

        # Fallback to text-only design
        logger.info("Falling back to text-only design after exception")
        return await _fallback_text_only_design(state, ctx, trace, start_time, error=str(e))


async def _fallback_text_only_design(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext],
    trace: TraceBuilder,
    start_time: datetime,
    error: Optional[str] = None,
) -> dict:
    """
    Fallback to text-only design when image is not available or Gemini call fails.

    Uses the existing game_orchestrator sequential approach.
    """
    from app.agents.had.game_orchestrator import game_orchestrator

    trace.thought(
        f"Falling back to sequential game design. "
        f"Reason: {error or 'No image available'}"
    )

    # Call the original game_orchestrator
    result = await game_orchestrator(state, ctx)

    # Mark as fallback
    result["design_metadata"] = result.get("design_metadata", {})
    result["design_metadata"]["fallback"] = True
    result["design_metadata"]["fallback_reason"] = error or "No image available"
    result["design_metadata"]["designer"] = "game_orchestrator_fallback"

    # Set fallback flag for instrumentation
    if ctx:
        ctx.set_fallback_used(f"Unified design fallback: {error or 'No image'}")

    return result


def _convert_to_zones(diagram_zones: List[Dict[str, Any]]) -> List[Zone]:
    """Convert raw zone dicts to Zone objects."""
    zones = []
    for z in diagram_zones:
        # Determine shape
        if z.get("points"):
            shape = ZoneShape.POLYGON
        elif z.get("radius"):
            shape = ZoneShape.CIRCLE
        else:
            shape = ZoneShape.RECT

        zone = Zone(
            id=z.get("id", f"zone_{z.get('label', 'unknown')}"),
            label=z.get("label", ""),
            shape=shape,
            points=z.get("points"),
            x=z.get("x"),
            y=z.get("y"),
            radius=z.get("radius"),
            width=z.get("width"),
            height=z.get("height"),
            center=z.get("center"),
            hierarchy_level=z.get("hierarchy_level", z.get("hierarchyLevel", 1)),
            parent_zone_id=z.get("parent_zone_id", z.get("parentZoneId")),
            confidence=z.get("confidence", 0.9),
            hint=z.get("hint"),
            visible=z.get("visible", True),
        )

        # Compute center for polygon if not present
        if zone.shape == ZoneShape.POLYGON and zone.points and not zone.center:
            xs = [p[0] for p in zone.points]
            ys = [p[1] for p in zone.points]
            zone.center = {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys)}

        zones.append(zone)

    return zones


def _convert_to_zone_groups(zone_groups: List[Dict[str, Any]]) -> List[ZoneGroup]:
    """Convert raw zone group dicts to ZoneGroup objects."""
    groups = []
    for g in zone_groups:
        groups.append(ZoneGroup(
            parent_zone_id=g.get("parent_zone_id", g.get("parentZoneId", "")),
            child_zone_ids=g.get("child_zone_ids", g.get("childZoneIds", [])),
            relationship_type=g.get("relationship_type", g.get("relationshipType", "contains")),
        ))
    return groups


# =============================================================================
# Standalone test function
# =============================================================================

async def test_game_designer():
    """Test the game_designer with sample input."""
    from app.agents.state import create_initial_state

    state = create_initial_state(
        question_id="test_designer_001",
        question_text="Label the parts of a flower"
    )

    state["domain_knowledge"] = {
        "canonical_labels": ["petal", "stamen", "pistil", "sepal", "stem"],
        "hierarchical_relationships": [
            {
                "parent": "stamen",
                "children": ["anther", "filament"],
                "relationship_type": "composed_of"
            }
        ],
    }

    state["pedagogical_context"] = {
        "subject": "Biology - Botany",
        "blooms_level": "UNDERSTAND",
    }

    state["template_selection"] = {
        "template_type": "INTERACTIVE_DIAGRAM",
    }

    state["diagram_zones"] = [
        {
            "id": "zone_petal",
            "label": "petal",
            "shape": "polygon",
            "points": [[40, 20], [60, 20], [65, 40], [50, 50], [35, 40]],
            "confidence": 0.95,
        },
        {
            "id": "zone_stamen",
            "label": "stamen",
            "shape": "circle",
            "x": 50,
            "y": 50,
            "radius": 6,
            "confidence": 0.92,
        },
    ]

    state["zone_groups"] = [
        {
            "parent_zone_id": "zone_stamen",
            "child_zone_ids": ["zone_anther", "zone_filament"],
            "relationship_type": "composed_of",
        }
    ]

    # Note: This test will use fallback since no image exists
    result = await game_designer(state)

    print(f"Game plan: {result.get('game_plan') is not None}")
    print(f"Scene structure: {result.get('scene_structure') is not None}")
    print(f"Scene assets: {result.get('scene_assets') is not None}")
    print(f"Scene interactions: {result.get('scene_interactions') is not None}")
    print(f"Design metadata: {result.get('design_metadata', {})}")

    return result


if __name__ == "__main__":
    asyncio.run(test_game_designer())
