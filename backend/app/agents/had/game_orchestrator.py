"""
GAME_ORCHESTRATOR - HAD Design Cluster Orchestrator (v2 with Design Tracing)

Coordinates game planning and scene design through sequential tool calls.
Uses a fixed tool workflow (not worker agents) since scene stages have
well-defined sequential dependencies.

Architecture Pattern: Planner -> Sequential Tool Calls with Trace Capture
- plan_game_tool: Wraps game_planner agent
- design_structure_tool: Wraps scene_stage1_structure agent
- design_assets_tool: Wraps scene_stage2_assets agent
- design_interactions_tool: Wraps scene_stage3_interactions agent

Key v2 Improvements:
- Captures full design_trace with reasoning steps for UI visualization
- Records decision points and context for each stage
- Tracks stage timings in trace for performance analysis

Inputs from Vision Cluster:
    - diagram_zones: Detected zones
    - zone_groups: Hierarchical groupings
    - generated_diagram_path: Image path

Inputs from Research Cluster:
    - domain_knowledge: Canonical labels, hierarchy
    - pedagogical_context: Bloom's, subject
    - template_selection: Selected template

Outputs to Output Cluster:
    - game_plan: Learning objectives, mechanics, scoring
    - scene_structure: Layout and regions
    - scene_assets: Visual assets
    - scene_interactions: Behaviors and animations
    - design_trace: Reasoning trace for UI visualization (NEW)
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.had.design_tools import (
    plan_game,
    design_structure,
    design_assets,
    design_interactions,
)
from app.agents.had.react_loop import TraceBuilder
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.game_orchestrator")


async def game_orchestrator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    HAD Design Cluster: Orchestrates game planning and scene design.

    HAD v3 Enhancements:
    - Multi-scene game design with transitions
    - Per-scene structure, assets, and interactions
    - Scene progression planning (linear, zoom_in, branching)
    - Query-intent aware game mechanics

    Sequential workflow with trace capture:
    1. Plan game mechanics and objectives
    2. Design scene structure (Stage 1)
    3. Design visual assets (Stage 2)
    4. Design interactions and behaviors (Stage 3)
    5. [NEW] Design scene transitions (if multi-scene)

    Each stage receives outputs from previous stages, ensuring proper
    context propagation through the design pipeline.
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    # HAD v3: Check for multi-scene
    needs_multi_scene = state.get("needs_multi_scene", False)

    logger.info(f"GAME_ORCHESTRATOR starting for {question_id}, template={template_type}, multi_scene={needs_multi_scene}")

    # Route to multi-scene or single-scene design
    if needs_multi_scene:
        return await _design_multi_scene_game(state, ctx)

    # Initialize trace builder for design decisions
    trace = TraceBuilder(phase="game_design")

    # Extract inputs
    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    pedagogical_context = state.get("pedagogical_context", {})
    diagram_zones = state.get("diagram_zones", [])
    zone_groups = state.get("zone_groups", [])

    # Record initial design context
    blooms_level = pedagogical_context.get("blooms_level", "understand")
    subject = pedagogical_context.get("subject", "")
    canonical_labels = domain_knowledge.get("canonical_labels", [])

    trace.thought(
        f"Starting game design for '{template_type}' template. "
        f"Subject: {subject}, Bloom's level: {blooms_level}. "
        f"Have {len(diagram_zones)} zones and {len(zone_groups)} zone groups from Vision Cluster."
    )

    # Track total duration
    start_time = datetime.utcnow()
    stage_durations = {}

    # ==========================================================================
    # Stage 1: Plan Game
    # ==========================================================================
    trace.decision(
        f"Planning game mechanics based on {blooms_level} Bloom's level and {len(canonical_labels)} labels",
        stage="plan_game",
        input_labels=len(canonical_labels)
    )
    trace.action(
        tool="plan_game",
        args={
            "template_type": template_type,
            "blooms_level": blooms_level,
            "labels_count": len(canonical_labels),
        },
        description="Creating game plan with objectives, mechanics, and scoring"
    )

    logger.info("Executing plan_game tool")
    plan_start = time.time()

    plan_result = await plan_game(
        question_text=question_text,
        template_type=template_type,
        domain_knowledge=domain_knowledge,
        pedagogical_context=pedagogical_context,
    )

    plan_duration = int((time.time() - plan_start) * 1000)
    stage_durations["plan_game"] = plan_duration

    if not plan_result.success:
        trace.error(f"Game planning failed: {plan_result.error}")
        logger.error(f"Game planning failed: {plan_result.error}")
        return {
            "current_agent": "game_orchestrator",
            "current_validation_errors": [f"Game planning failed: {plan_result.error}"],
            "design_trace": [trace.complete(success=False).to_dict()],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    game_plan = plan_result.game_plan
    objectives_count = len(game_plan.get('learning_objectives', []))
    mechanics = game_plan.get('game_mechanics', [])

    trace.observation(
        f"Game plan created: {objectives_count} objectives, mechanics: {mechanics[:3] if mechanics else 'standard'}",
        result={
            "objectives_count": objectives_count,
            "mechanics": mechanics[:3] if isinstance(mechanics, list) else mechanics,
        },
        tool="plan_game",
        duration_ms=plan_duration
    )

    logger.info(f"Game plan created: {objectives_count} objectives")

    # Enrich game plan with zone information for INTERACTIVE_DIAGRAM
    if template_type == "INTERACTIVE_DIAGRAM":
        game_plan["diagram_zones"] = diagram_zones
        game_plan["zone_groups"] = zone_groups
        trace.thought(
            f"Enriching game plan with {len(diagram_zones)} zones and {len(zone_groups)} groups for INTERACTIVE_DIAGRAM"
        )

    # ==========================================================================
    # Stage 2: Design Structure
    # ==========================================================================
    trace.action(
        tool="design_structure",
        args={
            "game_plan_objectives": objectives_count,
            "template_type": template_type,
        },
        description="Designing scene structure with layout and regions"
    )

    logger.info("Executing design_structure tool")
    structure_start = time.time()

    structure_result = await design_structure(
        game_plan=game_plan,
        template_type=template_type,
        domain_knowledge=domain_knowledge,
        pedagogical_context=pedagogical_context,
    )

    structure_duration = int((time.time() - structure_start) * 1000)
    stage_durations["design_structure"] = structure_duration

    if not structure_result.success:
        trace.error(f"Structure design failed: {structure_result.error}")
        logger.error(f"Structure design failed: {structure_result.error}")
        return {
            "game_plan": game_plan,
            "current_agent": "game_orchestrator",
            "current_validation_errors": [f"Structure design failed: {structure_result.error}"],
            "design_trace": [trace.complete(success=False).to_dict()],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    scene_structure = structure_result.scene_structure
    visual_theme = scene_structure.get('visual_theme', 'unknown')
    layout_type = scene_structure.get('layout_type', 'standard')
    regions_count = len(scene_structure.get('regions', []))

    trace.observation(
        f"Scene structure created: '{visual_theme}' theme, '{layout_type}' layout, {regions_count} regions",
        result={
            "visual_theme": visual_theme,
            "layout_type": layout_type,
            "regions_count": regions_count,
        },
        tool="design_structure",
        duration_ms=structure_duration
    )

    logger.info(f"Scene structure created: {visual_theme} theme")

    # ==========================================================================
    # Stage 3: Design Assets
    # ==========================================================================
    trace.action(
        tool="design_assets",
        args={
            "regions_count": regions_count,
            "zones_count": len(diagram_zones),
        },
        description="Populating scene with visual assets"
    )

    logger.info("Executing design_assets tool")
    assets_start = time.time()

    assets_result = await design_assets(
        scene_structure=scene_structure,
        game_plan=game_plan,
        template_type=template_type,
        domain_knowledge=domain_knowledge,
        diagram_zones=diagram_zones,
    )

    assets_duration = int((time.time() - assets_start) * 1000)
    stage_durations["design_assets"] = assets_duration

    if not assets_result.success:
        trace.error(f"Assets design failed: {assets_result.error}")
        logger.error(f"Assets design failed: {assets_result.error}")
        return {
            "game_plan": game_plan,
            "scene_structure": scene_structure,
            "current_agent": "game_orchestrator",
            "current_validation_errors": [f"Assets design failed: {assets_result.error}"],
            "design_trace": [trace.complete(success=False).to_dict()],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    scene_assets = assets_result.scene_assets
    required_assets = scene_assets.get('required_assets', [])

    trace.observation(
        f"Scene assets created: {len(required_assets)} assets defined",
        result={
            "assets_count": len(required_assets),
            "asset_types": list(set(a.get("type") for a in required_assets if isinstance(a, dict)))[:5],
        },
        tool="design_assets",
        duration_ms=assets_duration
    )

    logger.info(f"Scene assets created: {len(required_assets)} assets")

    # ==========================================================================
    # Stage 4: Design Interactions
    # ==========================================================================
    trace.action(
        tool="design_interactions",
        args={
            "assets_count": len(required_assets),
            "regions_count": regions_count,
        },
        description="Defining behaviors, animations, and state transitions"
    )

    logger.info("Executing design_interactions tool")
    interactions_start = time.time()

    interactions_result = await design_interactions(
        scene_structure=scene_structure,
        scene_assets=scene_assets,
        game_plan=game_plan,
        template_type=template_type,
        domain_knowledge=domain_knowledge,
    )

    interactions_duration = int((time.time() - interactions_start) * 1000)
    stage_durations["design_interactions"] = interactions_duration

    if not interactions_result.success:
        trace.error(f"Interactions design failed: {interactions_result.error}")
        logger.error(f"Interactions design failed: {interactions_result.error}")
        return {
            "game_plan": game_plan,
            "scene_structure": scene_structure,
            "scene_assets": scene_assets,
            "current_agent": "game_orchestrator",
            "current_validation_errors": [f"Interactions design failed: {interactions_result.error}"],
            "design_trace": [trace.complete(success=False).to_dict()],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    scene_interactions = interactions_result.scene_interactions
    asset_interactions = scene_interactions.get('asset_interactions', [])

    trace.observation(
        f"Scene interactions created: {len(asset_interactions)} interaction definitions",
        result={
            "interactions_count": len(asset_interactions),
        },
        tool="design_interactions",
        duration_ms=interactions_duration
    )

    logger.info(
        f"Scene interactions created: "
        f"{len(asset_interactions)} interactions"
    )

    # Calculate total duration
    total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    # Record final result
    trace.result(
        f"Design complete: game plan + {regions_count} regions + {len(required_assets)} assets + {len(asset_interactions)} interactions",
        result={
            "game_plan_objectives": objectives_count,
            "scene_regions": regions_count,
            "assets_count": len(required_assets),
            "interactions_count": len(asset_interactions),
            "total_duration_ms": total_duration_ms,
        }
    )

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model="game_orchestrator",
            latency_ms=int(total_duration_ms),
        )

    logger.info(
        f"GAME_ORCHESTRATOR complete: total={total_duration_ms:.0f}ms, "
        f"stages={stage_durations}"
    )

    return {
        "game_plan": game_plan,
        "scene_structure": scene_structure,
        "scene_assets": scene_assets,
        "scene_interactions": scene_interactions,
        "design_trace": [trace.complete(success=True).to_dict()],  # NEW: For UI visualization
        "design_metadata": {
            "total_duration_ms": total_duration_ms,
            "stage_durations_ms": stage_durations,
            "orchestrator": "had_game_orchestrator",
            "completed_at": datetime.utcnow().isoformat(),
        },
        "current_agent": "game_orchestrator",
        "last_updated_at": datetime.utcnow().isoformat(),
    }


async def game_orchestrator_minimal(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Minimal game orchestrator for templates that don't need full scene design.

    Only executes the game planning stage, skipping scene design stages.
    Used for simpler templates or when scene data isn't required.
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"GAME_ORCHESTRATOR (minimal) starting for {question_id}")

    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    pedagogical_context = state.get("pedagogical_context", {})

    # Only plan game
    plan_result = await plan_game(
        question_text=question_text,
        template_type=template_type,
        domain_knowledge=domain_knowledge,
        pedagogical_context=pedagogical_context,
    )

    if not plan_result.success:
        return {
            "current_agent": "game_orchestrator",
            "current_validation_errors": [f"Game planning failed: {plan_result.error}"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    return {
        "game_plan": plan_result.game_plan,
        "current_agent": "game_orchestrator",
        "last_updated_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# Standalone test function
# =============================================================================

async def test_game_orchestrator():
    """Test the game_orchestrator with sample input."""
    from app.agents.state import create_initial_state

    state = create_initial_state(
        question_id="test_001",
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
        "blooms_level": "understand",
    }

    state["template_selection"] = {
        "template_type": "INTERACTIVE_DIAGRAM",
    }

    state["diagram_zones"] = [
        {"id": "zone_petal", "label": "petal", "x": 50, "y": 30, "radius": 8},
        {"id": "zone_stamen", "label": "stamen", "x": 50, "y": 50, "radius": 6},
    ]

    result = await game_orchestrator(state)

    print(f"Game plan: {result.get('game_plan') is not None}")
    print(f"Scene structure: {result.get('scene_structure') is not None}")
    print(f"Scene assets: {result.get('scene_assets') is not None}")
    print(f"Scene interactions: {result.get('scene_interactions') is not None}")
    print(f"Design metadata: {result.get('design_metadata', {})}")

    return result


async def _design_multi_scene_game(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Design multi-scene game with transitions.

    HAD v3: Creates a game sequence with multiple scenes, each with:
    - Its own image and zones
    - Specific interaction mode
    - Transition to next scene
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"GAME_ORCHESTRATOR (multi-scene) starting for {question_id}")

    # Initialize trace builder
    trace = TraceBuilder(phase="multi_scene_game_design")

    # Extract inputs
    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    pedagogical_context = state.get("pedagogical_context", {})
    scene_breakdown = state.get("scene_breakdown", [])
    scene_zones = state.get("scene_zones", {})
    scene_images = state.get("scene_images", {})
    scene_zone_groups = state.get("scene_zone_groups", {})
    progression_type = state.get("scene_progression_type", "linear")

    num_scenes = len(scene_breakdown)

    trace.thought(
        f"Designing multi-scene game with {num_scenes} scenes. "
        f"Progression type: {progression_type}"
    )

    start_time = datetime.utcnow()
    stage_durations = {}

    # ==========================================================================
    # Stage 1: Plan overall game
    # ==========================================================================
    trace.action(
        tool="plan_game",
        args={"template_type": template_type, "num_scenes": num_scenes},
        description="Creating multi-scene game plan"
    )

    plan_start = time.time()

    plan_result = await plan_game(
        question_text=question_text,
        template_type=template_type,
        domain_knowledge=domain_knowledge,
        pedagogical_context=pedagogical_context,
    )

    plan_duration = int((time.time() - plan_start) * 1000)
    stage_durations["plan_game"] = plan_duration

    if not plan_result.success:
        trace.error(f"Game planning failed: {plan_result.error}")
        return {
            "current_agent": "game_orchestrator",
            "current_validation_errors": [f"Game planning failed: {plan_result.error}"],
            "design_trace": [trace.complete(success=False).to_dict()],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    game_plan = plan_result.game_plan

    trace.observation(
        f"Game plan created: {len(game_plan.get('learning_objectives', []))} objectives",
        result={"objectives": game_plan.get('learning_objectives', [])[:3]},
        tool="plan_game",
        duration_ms=plan_duration
    )

    # ==========================================================================
    # Stage 2: Design each scene
    # ==========================================================================
    scenes = []

    for scene_def in scene_breakdown:
        scene_num = scene_def["scene_number"]
        scene_title = scene_def.get("title", f"Scene {scene_num}")
        focus_labels = scene_def.get("focus_labels", [])
        zones = scene_zones.get(scene_num, [])
        zone_groups = scene_zone_groups.get(scene_num, [])
        image_path = scene_images.get(scene_num)

        trace.action(
            tool="design_scene",
            args={"scene_number": scene_num, "zones_count": len(zones)},
            description=f"Designing scene {scene_num}: {scene_title}"
        )

        scene_start = time.time()

        # Design scene structure
        scene_structure = await _design_scene_structure(
            scene_num=scene_num,
            scene_title=scene_title,
            zones=zones,
            zone_groups=zone_groups,
            game_plan=game_plan,
            domain_knowledge=domain_knowledge,
            pedagogical_context=pedagogical_context,
        )

        scene_duration = int((time.time() - scene_start) * 1000)
        stage_durations[f"scene_{scene_num}"] = scene_duration

        # Determine interaction mode for this scene
        interaction_mode = _determine_scene_interaction_mode(
            scene_def, zone_groups, pedagogical_context
        )

        scene = {
            "scene_id": f"scene_{scene_num}",
            "scene_number": scene_num,
            "title": scene_title,
            "narrative_intro": scene_structure.get("narrative_intro", ""),
            "diagram": {
                "type": "image",
                "imageUrl": image_path,
                "assetPrompt": f"Diagram for {scene_title}",
            },
            "zones": zones,
            "labels": [{"id": z.get("id"), "text": z.get("label")} for z in zones],
            "interaction_mode": interaction_mode,
            "max_score": len(zones) * 10,
            "zone_groups": zone_groups,
            "prerequisite_scene": f"scene_{scene_num - 1}" if scene_num > 1 else None,
            "reveal_trigger": "all_correct",
            "hints_enabled": True,
            "feedback_enabled": True,
        }

        scenes.append(scene)

        trace.observation(
            f"Scene {scene_num} designed: {len(zones)} zones, mode={interaction_mode}",
            result={"zones": len(zones), "mode": interaction_mode},
            tool="design_scene",
            duration_ms=scene_duration
        )

    # ==========================================================================
    # Stage 3: Design scene transitions
    # ==========================================================================
    trace.action(
        tool="design_transitions",
        args={"num_scenes": num_scenes, "progression_type": progression_type},
        description="Designing scene transitions"
    )

    transitions = _design_scene_transitions(scenes, progression_type)

    for i, scene in enumerate(scenes):
        if i < len(scenes) - 1:
            scene["transition_to"] = transitions.get(scene["scene_id"], {})

    trace.observation(
        f"Designed {len(transitions)} scene transitions",
        result={"transitions": list(transitions.keys())},
        tool="design_transitions"
    )

    # ==========================================================================
    # Build game sequence
    # ==========================================================================
    total_max_score = sum(s["max_score"] for s in scenes)

    game_sequence = {
        "sequence_id": f"sequence_{question_id}",
        "sequence_title": game_plan.get("game_title", question_text[:50]),
        "sequence_description": game_plan.get("narrative_intro", ""),
        "total_scenes": num_scenes,
        "scenes": scenes,
        "progression_type": progression_type,
        "total_max_score": total_max_score,
        "passing_score": int(total_max_score * 0.7),
        "bonus_for_no_hints": True,
        "require_completion": True,
        "allow_scene_skip": False,
        "allow_revisit": True,
    }

    total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    trace.result(
        f"Multi-scene game designed: {num_scenes} scenes, {total_max_score} max score",
        result={
            "num_scenes": num_scenes,
            "total_max_score": total_max_score,
            "progression_type": progression_type,
        }
    )

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model="game_orchestrator_multi_scene",
            latency_ms=int(total_duration_ms),
        )

    logger.info(
        f"GAME_ORCHESTRATOR (multi-scene) complete: {num_scenes} scenes, "
        f"total={total_duration_ms:.0f}ms"
    )

    return {
        "game_plan": game_plan,
        "game_sequence": game_sequence,
        "needs_multi_scene": True,
        "num_scenes": num_scenes,
        "scene_progression_type": progression_type,
        "design_trace": [trace.complete(success=True).to_dict()],
        "design_metadata": {
            "total_duration_ms": total_duration_ms,
            "stage_durations_ms": stage_durations,
            "orchestrator": "had_game_orchestrator_multi_scene",
            "completed_at": datetime.utcnow().isoformat(),
        },
        "current_agent": "game_orchestrator",
        "last_updated_at": datetime.utcnow().isoformat(),
    }


async def _design_scene_structure(
    scene_num: int,
    scene_title: str,
    zones: List[Dict[str, Any]],
    zone_groups: List[Dict[str, Any]],
    game_plan: Dict[str, Any],
    domain_knowledge: Dict[str, Any],
    pedagogical_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Design structure for a single scene."""
    # Generate narrative intro based on scene focus
    zone_labels = [z.get("label", "") for z in zones[:5]]
    labels_str = ", ".join(zone_labels)

    narrative_intro = (
        f"In this scene, focus on identifying: {labels_str}. "
        f"Drag each label to its correct position on the diagram."
    )

    return {
        "scene_title": scene_title,
        "narrative_intro": narrative_intro,
        "layout_type": "diagram_with_labels",
        "regions": [
            {"id": "diagram_area", "type": "image", "width": 70},
            {"id": "label_tray", "type": "labels", "width": 30},
        ],
    }


def _determine_scene_interaction_mode(
    scene_def: Dict[str, Any],
    zone_groups: List[Dict[str, Any]],
    pedagogical_context: Dict[str, Any],
) -> str:
    """Determine the best interaction mode for a scene."""
    # If scene has zone groups, use hierarchical mode
    if zone_groups and len(zone_groups) > 0:
        return "hierarchical"

    # Check Bloom's level
    blooms_level = pedagogical_context.get("blooms_level", "understand")

    if blooms_level in ("remember", "understand"):
        return "drag_drop"
    elif blooms_level == "apply":
        return "click_to_identify"
    elif blooms_level in ("analyze", "evaluate"):
        return "description_matching"

    return "drag_drop"


def _design_scene_transitions(
    scenes: List[Dict[str, Any]],
    progression_type: str,
) -> Dict[str, Dict[str, Any]]:
    """Design transitions between scenes."""
    transitions = {}

    for i, scene in enumerate(scenes[:-1]):
        next_scene = scenes[i + 1]
        scene_id = scene["scene_id"]
        next_id = next_scene["scene_id"]

        # Choose animation based on progression type
        if progression_type == "zoom_in":
            animation = "zoom_in"
        elif progression_type == "branching":
            animation = "fade"
        else:
            animation = "slide_left"

        transitions[scene_id] = {
            "next_scene": next_id,
            "trigger": "all_correct",
            "animation": animation,
            "delay_ms": 500,
        }

    return transitions


if __name__ == "__main__":
    asyncio.run(test_game_orchestrator())
