"""
OUTPUT_ORCHESTRATOR - HAD Output Cluster Orchestrator

Coordinates blueprint generation, validation, and SVG rendering.
Uses tool calls with a validation retry loop for self-correction.

Architecture Pattern: Planner -> Tool Calls + Validation Loop (max 3 retries)
- generate_blueprint_tool: Creates blueprint from design data
- validate_blueprint_tool: Rule-based validation
- generate_spec_tool: Creates diagram specification
- render_svg_tool: Deterministic SVG rendering

The orchestrator handles the retry loop, passing error context to
subsequent generation attempts for self-correction.

Inputs from Design Cluster:
    - game_plan: Learning objectives, mechanics
    - scene_structure: Layout and regions
    - scene_assets: Visual assets
    - scene_interactions: Behaviors

Inputs from Vision Cluster:
    - diagram_zones: Detected zones
    - zone_groups: Hierarchical groupings

Outputs:
    - blueprint: Complete game blueprint JSON
    - diagram_spec: SVG specification (for INTERACTIVE_DIAGRAM)
    - diagram_svg: Rendered SVG content
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.had.output_tools import (
    generate_blueprint,
    validate_blueprint,
    generate_spec,
    render_svg,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.output_orchestrator")

# Configuration
MAX_BLUEPRINT_RETRIES = 3


async def output_orchestrator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    HAD Output Cluster: Orchestrates blueprint generation and validation.

    Workflow with validation loop:
    1. Generate blueprint from design data
    2. Validate blueprint (rule-based)
    3. If invalid, retry with error context (max 3 times)
    4. Generate diagram spec (INTERACTIVE_DIAGRAM only)
    5. Render SVG (deterministic)

    The retry loop passes previous errors to the generator for
    self-correction, improving output quality.
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"OUTPUT_ORCHESTRATOR starting for {question_id}, template={template_type}")

    # Extract inputs from Design and Vision clusters
    game_plan = state.get("game_plan", {})
    scene_structure = state.get("scene_structure")
    scene_assets = state.get("scene_assets")
    scene_interactions = state.get("scene_interactions")
    diagram_zones = state.get("diagram_zones", [])
    zone_groups = state.get("zone_groups", [])
    domain_knowledge = state.get("domain_knowledge", {})
    pedagogical_context = state.get("pedagogical_context", {})

    # Track timing
    start_time = datetime.utcnow()
    stage_durations = {}

    # ==========================================================================
    # Phase 1: Blueprint Generation with Validation Loop
    # ==========================================================================
    blueprint = None
    validation_result = None
    previous_errors: List[str] = []
    retry_count = 0

    for attempt in range(MAX_BLUEPRINT_RETRIES):
        logger.info(f"Blueprint generation attempt {attempt + 1}/{MAX_BLUEPRINT_RETRIES}")

        gen_start = datetime.utcnow()

        # Generate blueprint (with previous errors for retry)
        gen_result = await generate_blueprint(
            game_plan=game_plan,
            diagram_zones=diagram_zones,
            template_type=template_type,
            scene_structure=scene_structure,
            scene_assets=scene_assets,
            scene_interactions=scene_interactions,
            zone_groups=zone_groups,
            domain_knowledge=domain_knowledge,
            pedagogical_context=pedagogical_context,
            previous_errors=previous_errors if attempt > 0 else None,
        )

        stage_durations[f"generate_blueprint_attempt_{attempt + 1}"] = (
            (datetime.utcnow() - gen_start).total_seconds() * 1000
        )

        if not gen_result.success:
            logger.warning(f"Blueprint generation failed: {gen_result.error}")
            previous_errors.append(f"Generation error: {gen_result.error}")
            continue

        blueprint = gen_result.blueprint

        # Validate blueprint
        val_start = datetime.utcnow()
        validation_result = await validate_blueprint(
            blueprint=blueprint,
            template_type=template_type,
        )
        stage_durations[f"validate_blueprint_attempt_{attempt + 1}"] = (
            (datetime.utcnow() - val_start).total_seconds() * 1000
        )

        logger.info(
            f"Validation result: is_valid={validation_result.is_valid}, "
            f"score={validation_result.score:.2f}, errors={len(validation_result.errors)}"
        )

        # If valid, we're done
        if validation_result.is_valid:
            retry_count = attempt
            logger.info(f"Blueprint validated successfully on attempt {attempt + 1}")
            break

        # Collect errors for next attempt
        previous_errors = validation_result.errors
        retry_count = attempt + 1

        # Log validation errors
        for error in validation_result.errors[:5]:
            logger.warning(f"Validation error: {error}")

    # Check if we have a valid blueprint
    if blueprint is None:
        return {
            "current_agent": "output_orchestrator",
            "current_validation_errors": ["Failed to generate blueprint after max retries"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Even if validation didn't fully pass, continue with best-effort blueprint
    if validation_result and not validation_result.is_valid:
        logger.warning(
            f"Blueprint validation incomplete after {retry_count + 1} attempts, "
            f"continuing with best-effort blueprint"
        )

    # ==========================================================================
    # Phase 2: Diagram Spec Generation (INTERACTIVE_DIAGRAM only)
    # ==========================================================================
    diagram_spec = None
    if template_type == "INTERACTIVE_DIAGRAM":
        logger.info("Generating diagram specification")
        spec_start = datetime.utcnow()

        spec_result = await generate_spec(
            blueprint=blueprint,
            template_type=template_type,
        )

        stage_durations["generate_spec"] = (datetime.utcnow() - spec_start).total_seconds() * 1000

        if spec_result.success:
            diagram_spec = spec_result.diagram_spec
            logger.info("Diagram spec generated")
        else:
            logger.warning(f"Spec generation failed: {spec_result.error}")

    # ==========================================================================
    # Phase 3: SVG Rendering (deterministic, INTERACTIVE_DIAGRAM only)
    # ==========================================================================
    diagram_svg = None
    if diagram_spec:
        logger.info("Rendering SVG from diagram spec")
        svg_start = datetime.utcnow()

        svg_result = await render_svg(diagram_spec=diagram_spec)

        stage_durations["render_svg"] = (datetime.utcnow() - svg_start).total_seconds() * 1000

        if svg_result.success:
            diagram_svg = svg_result.svg_content
            logger.info(f"SVG rendered: {len(diagram_svg) if diagram_svg else 0} chars")
        else:
            logger.warning(f"SVG rendering failed: {svg_result.error}")

    # Calculate total duration
    total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model="output_orchestrator",
            latency_ms=int(total_duration_ms),
        )

    logger.info(
        f"OUTPUT_ORCHESTRATOR complete: total={total_duration_ms:.0f}ms, "
        f"retries={retry_count}, stages={len(stage_durations)}"
    )

    # Build output
    output = {
        "blueprint": blueprint,
        "current_agent": "output_orchestrator",
        "last_updated_at": datetime.utcnow().isoformat(),
        "output_metadata": {
            "total_duration_ms": total_duration_ms,
            "stage_durations_ms": stage_durations,
            "blueprint_retry_count": retry_count,
            "validation_score": validation_result.score if validation_result else 0.0,
            "validation_errors": validation_result.errors if validation_result else [],
            "validation_warnings": validation_result.warnings if validation_result else [],
            "orchestrator": "had_output_orchestrator",
            "completed_at": datetime.utcnow().isoformat(),
        },
    }

    # Add INTERACTIVE_DIAGRAM specific outputs
    if template_type == "INTERACTIVE_DIAGRAM":
        output["diagram_spec"] = diagram_spec
        output["diagram_svg"] = diagram_svg

    # Mark generation complete
    output["generation_complete"] = True

    return output


async def output_orchestrator_fast(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Fast output orchestrator that skips validation retries.

    Use this for development/testing when you want quick iterations
    without the full validation loop.
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"OUTPUT_ORCHESTRATOR (fast) starting for {question_id}")

    # Extract inputs
    game_plan = state.get("game_plan", {})
    diagram_zones = state.get("diagram_zones", [])
    zone_groups = state.get("zone_groups", [])
    domain_knowledge = state.get("domain_knowledge", {})
    pedagogical_context = state.get("pedagogical_context", {})

    # Single blueprint generation (no retry)
    gen_result = await generate_blueprint(
        game_plan=game_plan,
        diagram_zones=diagram_zones,
        template_type=template_type,
        zone_groups=zone_groups,
        domain_knowledge=domain_knowledge,
        pedagogical_context=pedagogical_context,
    )

    if not gen_result.success:
        return {
            "current_agent": "output_orchestrator",
            "current_validation_errors": [f"Blueprint generation failed: {gen_result.error}"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    output = {
        "blueprint": gen_result.blueprint,
        "generation_complete": True,
        "current_agent": "output_orchestrator",
        "last_updated_at": datetime.utcnow().isoformat(),
    }

    # Quick spec/svg for INTERACTIVE_DIAGRAM
    if template_type == "INTERACTIVE_DIAGRAM":
        spec_result = await generate_spec(
            blueprint=gen_result.blueprint,
            template_type=template_type,
        )
        if spec_result.success and spec_result.diagram_spec:
            output["diagram_spec"] = spec_result.diagram_spec

            svg_result = await render_svg(diagram_spec=spec_result.diagram_spec)
            if svg_result.success:
                output["diagram_svg"] = svg_result.svg_content

    return output


# =============================================================================
# Standalone test function
# =============================================================================

async def test_output_orchestrator():
    """Test the output_orchestrator with sample input."""
    from app.agents.state import create_initial_state

    state = create_initial_state(
        question_id="test_001",
        question_text="Label the parts of a flower"
    )

    state["template_selection"] = {
        "template_type": "INTERACTIVE_DIAGRAM",
    }

    state["domain_knowledge"] = {
        "canonical_labels": ["petal", "stamen", "pistil"],
    }

    state["game_plan"] = {
        "learning_objectives": ["Identify flower parts"],
        "game_mechanics": [{"id": "drag_drop", "type": "label_placement"}],
        "scoring_rubric": {"max_score": 100},
    }

    state["diagram_zones"] = [
        {"id": "zone_petal", "label": "petal", "x": 50, "y": 30, "radius": 8},
        {"id": "zone_stamen", "label": "stamen", "x": 50, "y": 50, "radius": 6},
        {"id": "zone_pistil", "label": "pistil", "x": 55, "y": 55, "radius": 5},
    ]

    state["zone_groups"] = []

    result = await output_orchestrator(state)

    print(f"Blueprint: {result.get('blueprint') is not None}")
    print(f"Diagram spec: {result.get('diagram_spec') is not None}")
    print(f"Diagram SVG: {len(result.get('diagram_svg', '')) if result.get('diagram_svg') else 0} chars")
    print(f"Output metadata: {result.get('output_metadata', {})}")

    return result


if __name__ == "__main__":
    asyncio.run(test_output_orchestrator())
