"""Deterministic Graph Builder — GameConcept + SceneCreativeDesigns → GamePlan.

100% deterministic. No LLM calls.

Responsibilities:
1. Assign formulaic IDs (scene_1, s1_m0, s1_m1, ...)
2. Compute scores (expected_item_count × points_per_item)
3. Copy creative designs from SceneCreativeDesign → MechanicPlan
4. Build mechanic connections from list order + advance_triggers
5. Resolve triggers via TRIGGER_MAP
6. Set terminal flags on last mechanic per scene
"""

from typing import Any, Optional

from app.utils.logging_config import get_logger
from app.v4.contracts import resolve_trigger
from app.v4.schemas.creative_design import (
    MechanicCreativeDesign,
    SceneCreativeDesign,
)
from app.v4.schemas.game_concept import GameConcept, MechanicChoice, SceneConcept
from app.v4.schemas.game_plan import (
    GamePlan,
    MechanicConnection,
    MechanicPlan,
    ScenePlan,
    SceneTransition,
)

logger = get_logger("gamed_ai.v4.graph_builder")


def build_game_graph(
    concept: GameConcept,
    scene_designs: dict[str, SceneCreativeDesign],
) -> GamePlan:
    """Build a formal GamePlan from a GameConcept and SceneCreativeDesigns.

    Args:
        concept: The high-level game concept (WHAT and WHY).
        scene_designs: Per-scene creative designs keyed by scene_id (HOW).

    Returns:
        GamePlan with all IDs assigned, scores computed, connections built.
    """
    scenes: list[ScenePlan] = []
    total_max_score = 0

    for scene_idx, scene_concept in enumerate(concept.scenes):
        scene_number = scene_idx + 1
        scene_id = f"scene_{scene_number}"

        # Find matching creative design
        design = scene_designs.get(scene_id)
        if design is None:
            # Try alternate key formats
            design = scene_designs.get(str(scene_idx))
            if design is None:
                design = scene_designs.get(f"s{scene_idx}")

        if design is None:
            logger.warning(
                f"No creative design for {scene_id}, creating minimal design"
            )
            design = _create_minimal_design(scene_id, scene_concept)

        # Build mechanic plans
        mechanic_plans: list[MechanicPlan] = []
        mechanic_counter = 0

        for mech_idx, mech_choice in enumerate(scene_concept.mechanics):
            mechanic_id = f"s{scene_number}_m{mechanic_counter}"
            mechanic_counter += 1

            # Find matching creative design for this mechanic
            creative = _find_mechanic_design(design, mech_idx, mech_choice)

            # Compute score
            max_score = mech_choice.expected_item_count * mech_choice.points_per_item

            plan = MechanicPlan(
                mechanic_id=mechanic_id,
                mechanic_type=mech_choice.mechanic_type,
                zone_labels_used=mech_choice.zone_labels_used,
                instruction_text=creative.instruction_text,
                creative_design=creative,
                expected_item_count=mech_choice.expected_item_count,
                points_per_item=mech_choice.points_per_item,
                max_score=max_score,
                is_timed=mech_choice.is_timed,
                time_limit_seconds=mech_choice.time_limit_seconds,
                is_terminal=(mech_idx == len(scene_concept.mechanics) - 1),
                advance_trigger=mech_choice.advance_trigger,
                advance_trigger_value=mech_choice.advance_trigger_value,
            )
            mechanic_plans.append(plan)

        # Build mechanic connections from list order
        connections = _build_connections(mechanic_plans)

        # Compute scene score
        scene_max_score = sum(m.max_score for m in mechanic_plans)
        total_max_score += scene_max_score

        # Build scene transition
        scene_transition = None
        if scene_concept.transition_to_next != "auto" or scene_concept.transition_min_score_pct:
            scene_transition = SceneTransition(
                transition_type=scene_concept.transition_to_next,
                min_score_pct=scene_concept.transition_min_score_pct,
            )

        scene_plan = ScenePlan(
            scene_id=scene_id,
            scene_number=scene_number,
            title=scene_concept.title,
            learning_goal=scene_concept.learning_goal,
            narrative_intro=scene_concept.narrative_intro or design.scene_narrative,
            zone_labels=scene_concept.zone_labels,
            needs_diagram=scene_concept.needs_diagram,
            image_spec=design.image_spec,
            second_image_spec=design.second_image_spec,
            creative_design=design,
            mechanics=mechanic_plans,
            mechanic_connections=connections,
            starting_mechanic_id=mechanic_plans[0].mechanic_id if mechanic_plans else "",
            transition_to_next=scene_transition,
            scene_max_score=scene_max_score,
        )
        scenes.append(scene_plan)

    game_plan = GamePlan(
        title=concept.title,
        subject=concept.subject,
        difficulty=concept.difficulty,
        estimated_duration_minutes=concept.estimated_duration_minutes,
        narrative_theme=concept.narrative_theme,
        narrative_intro=concept.narrative_intro,
        completion_message=concept.completion_message,
        all_zone_labels=concept.all_zone_labels,
        distractor_labels=concept.distractor_labels,
        label_hierarchy=concept.label_hierarchy,
        total_max_score=total_max_score,
        scenes=scenes,
    )

    logger.info(
        f"Graph built: {len(scenes)} scenes, "
        f"{sum(len(s.mechanics) for s in scenes)} mechanics, "
        f"total_max_score={total_max_score}"
    )

    return game_plan


def graph_builder_node(state: dict) -> dict:
    """LangGraph node wrapper for the graph builder.

    Reads: game_concept, scene_creative_designs
    Writes: game_plan
    """
    concept_raw = state.get("game_concept")
    designs_raw = state.get("scene_creative_designs") or {}

    if not concept_raw:
        logger.error("No game concept available for graph builder")
        return {
            "error_message": "Graph builder: no game concept",
        }

    try:
        concept = GameConcept(**concept_raw)
    except Exception as e:
        logger.error(f"Failed to parse game concept: {e}")
        return {
            "error_message": f"Graph builder: invalid game concept: {e}",
        }

    # Parse scene designs
    scene_designs: dict[str, SceneCreativeDesign] = {}
    for key, design_raw in designs_raw.items():
        try:
            scene_designs[key] = SceneCreativeDesign(**design_raw)
        except Exception as e:
            logger.warning(f"Failed to parse scene design {key}: {e}")

    game_plan = build_game_graph(concept, scene_designs)

    return {
        "game_plan": game_plan.model_dump(),
    }


def _build_connections(mechanics: list[MechanicPlan]) -> list[MechanicConnection]:
    """Build mechanic connections from sequential list order.

    Each mechanic connects to the next one. The trigger is resolved from
    the mechanic's advance_trigger using TRIGGER_MAP.
    """
    connections = []
    for i in range(len(mechanics) - 1):
        current = mechanics[i]
        next_mech = mechanics[i + 1]

        trigger = resolve_trigger(current.advance_trigger, current.mechanic_type)

        conn = MechanicConnection(
            from_mechanic_id=current.mechanic_id,
            to_mechanic_id=next_mech.mechanic_id,
            trigger=trigger,
            trigger_value=current.advance_trigger_value,
        )
        connections.append(conn)

    return connections


def _find_mechanic_design(
    scene_design: SceneCreativeDesign,
    mech_idx: int,
    mech_choice: MechanicChoice,
) -> MechanicCreativeDesign:
    """Find the matching MechanicCreativeDesign for a mechanic choice.

    Tries index match first, then type match.
    Falls back to creating a minimal design.
    """
    designs = scene_design.mechanic_designs

    # Try index match
    if mech_idx < len(designs):
        design = designs[mech_idx]
        if design.mechanic_type == mech_choice.mechanic_type:
            return design

    # Try type match
    for design in designs:
        if design.mechanic_type == mech_choice.mechanic_type:
            return design

    # Fallback: create minimal design
    logger.warning(
        f"No creative design for {mech_choice.mechanic_type} at index {mech_idx}, "
        f"creating minimal design"
    )
    return MechanicCreativeDesign(
        mechanic_type=mech_choice.mechanic_type,
        visual_style="clean educational",
        instruction_text=f"Complete the {mech_choice.mechanic_type.replace('_', ' ')} activity.",
        generation_goal=f"Generate {mech_choice.mechanic_type} content for the learning activity.",
    )


def _create_minimal_design(
    scene_id: str, scene_concept: SceneConcept
) -> SceneCreativeDesign:
    """Create a minimal SceneCreativeDesign when none is provided."""
    mechanic_designs = []
    for mech in scene_concept.mechanics:
        mechanic_designs.append(
            MechanicCreativeDesign(
                mechanic_type=mech.mechanic_type,
                visual_style="clean educational",
                instruction_text=f"Complete the {mech.mechanic_type.replace('_', ' ')} activity.",
                generation_goal=f"Generate {mech.mechanic_type} content.",
            )
        )

    return SceneCreativeDesign(
        scene_id=scene_id,
        title=scene_concept.title,
        visual_concept="Clean educational layout",
        mechanic_designs=mechanic_designs,
        scene_narrative=scene_concept.narrative_intro,
    )
