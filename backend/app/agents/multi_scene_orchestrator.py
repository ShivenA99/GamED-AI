"""
Multi-Scene Orchestrator Agent

Orchestrates multi-scene game generation by iterating through scenes
and running the 3-stage scene generation pipeline for each scene.

This agent handles CONTENT GENERATION ONLY (structure, assets, interactions).
Image retrieval + zone detection are handled downstream by the asset pipeline:
- asset_planner creates per-scene workflow steps with scene_number
- asset_generator_orchestrator runs labeling_diagram_workflow per scene
- Each workflow handles image retrieval + SAM3 zone detection internally

Inputs:
- scene_breakdown: List of scene definitions from game planning
- game_plan: Game plan with mechanics and scoring
- domain_knowledge: Canonical labels and hierarchies
- interaction_design: Interaction mode configuration

Outputs:
- all_scene_data: Dict[int, {structure, assets, interactions, scene_data}]
- needs_multi_scene: bool
- num_scenes: int
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.multi_scene_orchestrator")


async def multi_scene_orchestrator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Orchestrates multi-scene game generation by looping scene stages per-scene.

    For each scene in scene_breakdown:
    1. Build per-scene state with scene-specific context
    2. Run scene_stage1_structure (layout, theme, regions)
    3. Run scene_stage2_assets (asset definitions)
    4. Run scene_stage3_interactions (interactions, animations)
    5. Store results in all_scene_data[scene_num]

    Image retrieval + zone detection are NOT done here — they happen downstream
    in labeling_diagram_workflow when executed by asset_generator_orchestrator.

    Args:
        state: Current pipeline state with scene_breakdown
        ctx: Optional instrumentation context

    Returns:
        State update with all_scene_data, needs_multi_scene, num_scenes
    """
    scene_breakdown = state.get("scene_breakdown") or []
    num_scenes = len(scene_breakdown)

    logger.info(
        "Multi-scene orchestrator starting",
        num_scenes=num_scenes,
        has_scene_breakdown=bool(scene_breakdown)
    )

    # Skip guard: if all_scene_data is already populated with enough scenes,
    # pass through without re-running (prevents re-execution on blueprint retries)
    existing_scene_data = state.get("all_scene_data")
    if existing_scene_data and len(existing_scene_data) >= num_scenes:
        logger.info(
            f"Skipping multi-scene orchestration — {len(existing_scene_data)} scenes "
            f"already generated (need {num_scenes})"
        )
        return {
            "all_scene_data": existing_scene_data,
            "needs_multi_scene": num_scenes > 1,
            "num_scenes": num_scenes,
            "current_agent": "multi_scene_orchestrator",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Single scene or no breakdown — should not reach here, but handle gracefully
    if num_scenes <= 1:
        logger.info("Single scene detected, passing through without multi-scene processing")
        return {
            "needs_multi_scene": False,
            "num_scenes": max(1, num_scenes),
            "all_scene_data": {},
            "current_agent": "multi_scene_orchestrator",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Import scene stage functions
    from app.agents.scene_stage1_structure import scene_stage1_structure
    from app.agents.scene_stage2_assets import scene_stage2_assets
    from app.agents.scene_stage3_interactions import scene_stage3_interactions

    logger.info(
        f"Processing {num_scenes} scenes",
        scene_titles=[s.get("title", f"Scene {i+1}") for i, s in enumerate(scene_breakdown)]
    )

    all_scene_data: Dict[int, Dict[str, Any]] = {}

    # Track processing metrics
    processing_metrics = {
        "total_scenes": num_scenes,
        "successful_scenes": 0,
        "failed_scenes": 0,
        "processing_times_ms": [],
    }

    for i, scene_def in enumerate(scene_breakdown):
        scene_num = i + 1
        scene_start = datetime.utcnow()
        scene_title = scene_def.get("title", f"Scene {scene_num}")

        logger.info(
            f"Processing scene {scene_num}/{num_scenes}: {scene_title}",
            focus_labels=scene_def.get("focus_labels", [])[:5]
        )

        try:
            # Build per-scene state with scene-specific context
            scene_state = _build_scene_state(state, scene_def, scene_num)

            # Stage 1: Structure (theme, layout, regions)
            stage1_result = await scene_stage1_structure(scene_state, ctx=None)
            # Merge stage1 output into scene_state for stage2
            scene_state.update(stage1_result)

            # Stage 2: Assets (asset definitions, layout spec)
            stage2_result = await scene_stage2_assets(scene_state, ctx=None)
            scene_state.update(stage2_result)

            # Stage 3: Interactions (interactions, animations, transitions)
            stage3_result = await scene_stage3_interactions(scene_state, ctx=None)
            scene_state.update(stage3_result)

            # Store per-scene data
            all_scene_data[scene_num] = {
                "structure": stage1_result.get("scene_structure"),
                "assets": stage2_result.get("scene_assets"),
                "interactions": stage3_result.get("scene_interactions"),
                "scene_data": stage3_result.get("scene_data"),
                "scene_def": scene_def,
            }

            processing_metrics["successful_scenes"] += 1
            logger.info(f"Scene {scene_num} complete: {scene_title}")

        except Exception as e:
            logger.error(
                f"Error processing scene {scene_num}: {e}",
                exc_info=True
            )
            processing_metrics["failed_scenes"] += 1

            # Store empty data for failed scenes so downstream can handle gracefully
            all_scene_data[scene_num] = {
                "structure": None,
                "assets": None,
                "interactions": None,
                "scene_data": None,
                "scene_def": scene_def,
                "error": str(e),
            }

        # Track timing
        scene_duration_ms = int((datetime.utcnow() - scene_start).total_seconds() * 1000)
        processing_metrics["processing_times_ms"].append(scene_duration_ms)

    # Build result
    result = {
        "all_scene_data": all_scene_data,
        "needs_multi_scene": True,
        "num_scenes": num_scenes,
        "current_scene_number": num_scenes,  # Mark as complete
        "multi_scene_metadata": {
            "processing_metrics": processing_metrics,
            "processed_at": datetime.utcnow().isoformat(),
        },
        "current_agent": "multi_scene_orchestrator",
        "last_updated_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        "Multi-scene orchestration complete",
        successful=processing_metrics["successful_scenes"],
        failed=processing_metrics["failed_scenes"],
    )

    if ctx:
        ctx.complete(result)

    return result


def _build_scene_state(
    state: AgentState,
    scene_def: Dict[str, Any],
    scene_num: int,
) -> dict:
    """
    Build per-scene state with scene-specific context overrides.

    Copies relevant state fields and overrides game_plan mechanics
    and domain_knowledge labels with scene-specific values.

    Args:
        state: Full pipeline state
        scene_def: Scene definition from scene_breakdown
        scene_num: Scene number (1-indexed)

    Returns:
        Dict with scene-specific state overrides
    """
    # Start with a shallow copy of key state fields
    scene_state = dict(state)

    # Set current scene number
    scene_state["current_scene_number"] = scene_num

    # Override domain_knowledge canonical_labels with scene's focus_labels
    focus_labels = scene_def.get("focus_labels", [])
    domain_knowledge = state.get("domain_knowledge") or {}

    if focus_labels:
        scene_state["domain_knowledge"] = {
            **domain_knowledge,
            "canonical_labels": focus_labels,
            "query": scene_def.get("topic") or scene_def.get("title", ""),
        }

    # Override game_plan mechanics with scene-specific mechanics
    game_plan = state.get("game_plan") or {}
    scene_mechanics = scene_def.get("mechanics", [])

    if scene_mechanics:
        scene_state["game_plan"] = {
            **game_plan,
            "game_mechanics": scene_mechanics,
        }

    # Override question context with scene-specific info
    scene_topic = scene_def.get("topic") or scene_def.get("description", "")
    if scene_topic:
        original_question = state.get("question_text", "")
        scene_state["question_text"] = f"{original_question} - Focus: {scene_topic}"

    return scene_state


def should_use_multi_scene(state: AgentState) -> str:
    """
    Routing function to check if multi-scene orchestration is needed.

    Used as conditional edge function in topology definition.

    Args:
        state: Current pipeline state

    Returns:
        "multi_scene" if orchestration needed, "single_scene" otherwise
    """
    scene_breakdown = state.get("scene_breakdown") or []

    if len(scene_breakdown) > 1:
        logger.info(f"Multi-scene routing: {len(scene_breakdown)} scenes detected")
        return "multi_scene"

    logger.info("Single-scene routing: no multi-scene breakdown")
    return "single_scene"
