"""
Multi-Scene Image Orchestrator Agent (Preset 2 Only)

Orchestrates image retrieval/generation and zone detection for multi-scene games.
This agent is ONLY used when PIPELINE_PRESET=advanced_interactive_diagram and
needs_multi_scene=True.

For each scene in scene_breakdown:
1. Determines if we need a different image (based on scope/focus_labels)
2. Either retrieves a specific image or generates one using diagram_image_generator
3. Detects zones using gemini_zone_detector
4. Stores results in per-scene state fields

Inputs:
- scene_breakdown: List of scene definitions from scene_sequencer
- needs_multi_scene: Whether multi-scene is needed
- question_text: The original question
- domain_knowledge: Canonical labels and hierarchies

Outputs:
- scene_diagrams: Dict[int, diagram_info] - Diagram per scene
- scene_zones: Dict[int, List[zone]] - Zones per scene
- scene_labels: Dict[int, List[label]] - Labels per scene
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.multi_scene_image_orchestrator")


async def multi_scene_image_orchestrator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Multi-Scene Image Orchestrator Agent.

    Orchestrates per-scene image generation and zone detection for multi-scene games.

    ONLY used when:
    - PIPELINE_PRESET=advanced_interactive_diagram
    - needs_multi_scene=True

    For single-scene games, this agent is skipped.
    """
    # Check preset - only run for Preset 2
    preset = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")
    if preset != "advanced_interactive_diagram":
        logger.info(f"Skipping multi_scene_image_orchestrator - preset is '{preset}'")
        return {}

    # Check if multi-scene is needed
    needs_multi_scene = state.get("needs_multi_scene", False)
    if not needs_multi_scene:
        logger.info("Skipping multi_scene_image_orchestrator - single scene game")
        return {}

    scene_breakdown = state.get("scene_breakdown", [])
    if not scene_breakdown or len(scene_breakdown) <= 1:
        logger.info("Skipping multi_scene_image_orchestrator - no multi-scene breakdown")
        return {}

    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {})
    game_design = state.get("game_design", {})

    logger.info(
        "Starting multi-scene image orchestration",
        num_scenes=len(scene_breakdown),
        scenes=[s.get("title") for s in scene_breakdown]
    )

    # Initialize per-scene storage
    scene_diagrams: Dict[int, Dict[str, Any]] = {}
    scene_zones: Dict[int, List[Dict[str, Any]]] = {}
    scene_labels: Dict[int, List[Dict[str, Any]]] = {}

    # Process each scene
    for scene in scene_breakdown:
        scene_number = scene.get("scene_number", 1)
        scene_title = scene.get("title", f"Scene {scene_number}")
        scene_scope = scene.get("scope", "")
        focus_labels = scene.get("focus_labels", [])

        logger.info(
            f"Processing scene {scene_number}: {scene_title}",
            scope=scene_scope,
            focus_labels=focus_labels[:5]
        )

        try:
            # Generate or retrieve image for this scene
            # Pass parent's run_id and ctx for proper instrumentation tracking
            parent_run_id = state.get("_run_id")
            scene_diagram = await _generate_scene_diagram(
                scene_number=scene_number,
                scene_title=scene_title,
                scene_scope=scene_scope,
                focus_labels=focus_labels,
                question_text=question_text,
                domain_knowledge=domain_knowledge,
                game_design=game_design,
                parent_run_id=parent_run_id,
                ctx=ctx
            )

            if scene_diagram:
                scene_diagrams[scene_number] = scene_diagram

                # Detect zones for this scene
                zones, labels = await _detect_scene_zones(
                    scene_number=scene_number,
                    diagram_info=scene_diagram,
                    focus_labels=focus_labels,
                    domain_knowledge=domain_knowledge,
                    parent_run_id=parent_run_id,
                    ctx=ctx
                )

                scene_zones[scene_number] = zones
                scene_labels[scene_number] = labels

                logger.info(
                    f"Scene {scene_number} complete",
                    diagram_path=scene_diagram.get("generated_path", "N/A")[:50],
                    zones_count=len(zones),
                    labels_count=len(labels)
                )
            else:
                logger.warning(f"Failed to generate diagram for scene {scene_number}")

        except Exception as e:
            logger.error(
                f"Error processing scene {scene_number}",
                error=str(e),
                exc_info=True
            )
            # Continue with other scenes

    result = {
        "scene_diagrams": scene_diagrams,
        "scene_zones": scene_zones,
        "scene_labels": scene_labels,
        "current_agent": "multi_scene_image_orchestrator"
    }

    logger.info(
        "Multi-scene image orchestration complete",
        scenes_processed=len(scene_diagrams),
        total_zones=sum(len(z) for z in scene_zones.values())
    )

    if ctx:
        ctx.complete(result)

    return result


async def _generate_scene_diagram(
    scene_number: int,
    scene_title: str,
    scene_scope: str,
    focus_labels: List[str],
    question_text: str,
    domain_knowledge: Dict[str, Any],
    game_design: Dict[str, Any],
    parent_run_id: Optional[str] = None,
    ctx: Optional[InstrumentedAgentContext] = None
) -> Optional[Dict[str, Any]]:
    """
    Generate or retrieve a diagram for a specific scene.

    Uses diagram_image_generator with scene-specific prompts.
    Inherits parent's run_id for proper instrumentation tracking.
    """
    from app.agents.diagram_image_generator import diagram_image_generator
    from app.agents.state import AgentState

    # Build scene-specific prompt
    canonical_labels = domain_knowledge.get("canonical_labels", [])

    # Use focus_labels if provided, otherwise use canonical labels
    labels_for_scene = focus_labels if focus_labels else canonical_labels[:8]

    # Create a mini-state for the diagram generator
    scene_state = AgentState(
        question_id=f"scene_{scene_number}",
        question_text=f"{question_text} - Focus: {scene_scope}",
        question_options=None,
        pedagogical_context=None,
        template_selection={"template_type": "INTERACTIVE_DIAGRAM"},
        routing_confidence=1.0,
        routing_requires_human_review=False,
        domain_knowledge={
            "canonical_labels": labels_for_scene,
            "query": scene_scope
        },
        diagram_image=None,
        diagram_segments=None,
        sam3_prompts=None,
        diagram_zones=None,
        diagram_labels=None,
        zone_groups=None,
        cleaned_image_path=None,
        removed_labels=None,
        generated_diagram_path=None,
        annotation_elements=None,
        image_classification=None,
        retry_image_search=False,
        image_search_attempts=0,
        max_image_attempts=3,
        game_plan=None,
        scene_data=None,
        story_data=None,
        blueprint=None,
        generated_code=None,
        asset_urls=None,
        diagram_svg=None,
        diagram_spec=None,
        scene_structure=None,
        scene_assets=None,
        scene_interactions=None,
        needs_multi_scene=None,
        num_scenes=None,
        scene_progression_type=None,
        scene_breakdown=None,
        scene_diagrams=None,
        scene_zones=None,
        scene_labels=None,
        # Agentic Preset 2 fields
        diagram_type=None,
        diagram_type_config=None,
        diagram_analysis=None,
        game_design=None,
        # Asset pipeline fields
        planned_assets=None,
        generated_assets=None,
        asset_validation=None,
        # Runtime context
        _pipeline_preset=None,
        _ai_images_generated=0,
        validation_results={},
        current_validation_errors=[],
        retry_counts={},
        max_retries=3,
        pending_human_review=None,
        human_feedback=None,
        human_review_completed=False,
        current_agent="multi_scene_image_orchestrator",
        agent_history=[],
        started_at="",
        last_updated_at="",
        _run_id=parent_run_id,  # Inherit parent's run_id for instrumentation
        _stage_order=0,
        final_visualization_id=None,
        generation_complete=False,
        error_message=None
    )

    try:
        # Call diagram_image_generator with parent context for instrumentation
        result = await diagram_image_generator(scene_state, ctx=ctx)

        generated_path = result.get("generated_diagram_path")
        diagram_image = result.get("diagram_image")

        if generated_path or diagram_image:
            return {
                "scene_number": scene_number,
                "generated_path": generated_path,
                "diagram_image": diagram_image,
                "focus_labels": labels_for_scene,
                "scope": scene_scope
            }
        return None

    except Exception as e:
        logger.error(f"Diagram generation failed for scene {scene_number}: {e}")
        return None


async def _detect_scene_zones(
    scene_number: int,
    diagram_info: Dict[str, Any],
    focus_labels: List[str],
    domain_knowledge: Dict[str, Any],
    parent_run_id: Optional[str] = None,
    ctx: Optional[InstrumentedAgentContext] = None
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Detect zones in a scene-specific diagram.

    Uses gemini_zone_detector for zone detection.
    Inherits parent's run_id for proper instrumentation tracking.
    """
    from app.agents.gemini_zone_detector import gemini_zone_detector
    from app.agents.state import AgentState

    generated_path = diagram_info.get("generated_path")
    if not generated_path:
        logger.warning(f"No diagram path for scene {scene_number}")
        return [], []

    # Create mini-state for zone detector
    scene_state = AgentState(
        question_id=f"scene_{scene_number}",
        question_text="",
        question_options=None,
        pedagogical_context=None,
        template_selection={"template_type": "INTERACTIVE_DIAGRAM"},
        routing_confidence=1.0,
        routing_requires_human_review=False,
        domain_knowledge={
            "canonical_labels": focus_labels or domain_knowledge.get("canonical_labels", []),
            "acceptable_variants": domain_knowledge.get("acceptable_variants", {}),
            "hierarchical_relationships": domain_knowledge.get("hierarchical_relationships", [])
        },
        diagram_image=diagram_info.get("diagram_image"),
        diagram_segments=None,
        sam3_prompts=None,
        diagram_zones=None,
        diagram_labels=None,
        zone_groups=None,
        cleaned_image_path=None,
        removed_labels=None,
        generated_diagram_path=generated_path,
        annotation_elements=None,
        image_classification=None,
        retry_image_search=False,
        image_search_attempts=0,
        max_image_attempts=3,
        game_plan=None,
        scene_data=None,
        story_data=None,
        blueprint=None,
        generated_code=None,
        asset_urls=None,
        diagram_svg=None,
        diagram_spec=None,
        scene_structure=None,
        scene_assets=None,
        scene_interactions=None,
        needs_multi_scene=None,
        num_scenes=None,
        scene_progression_type=None,
        scene_breakdown=None,
        scene_diagrams=None,
        scene_zones=None,
        scene_labels=None,
        # Agentic Preset 2 fields
        diagram_type=None,
        diagram_type_config=None,
        diagram_analysis=None,
        game_design=None,
        # Asset pipeline fields
        planned_assets=None,
        generated_assets=None,
        asset_validation=None,
        # Runtime context
        _pipeline_preset=None,
        _ai_images_generated=0,
        validation_results={},
        current_validation_errors=[],
        retry_counts={},
        max_retries=3,
        pending_human_review=None,
        human_feedback=None,
        human_review_completed=False,
        current_agent="multi_scene_image_orchestrator",
        agent_history=[],
        started_at="",
        last_updated_at="",
        _run_id=parent_run_id,  # Inherit parent's run_id for instrumentation
        _stage_order=0,
        final_visualization_id=None,
        generation_complete=False,
        error_message=None
    )

    try:
        # Pass parent context for instrumentation tracking
        result = await gemini_zone_detector(scene_state, ctx=ctx)

        zones = result.get("diagram_zones", [])
        labels = result.get("diagram_labels", [])

        return zones, labels

    except Exception as e:
        logger.error(f"Zone detection failed for scene {scene_number}: {e}")
        return [], []
