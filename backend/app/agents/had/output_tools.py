"""
Output Tools for HAD OUTPUT_ORCHESTRATOR

Tool wrappers for blueprint generation, validation, and SVG rendering.
The OUTPUT_ORCHESTRATOR coordinates these with a validation retry loop.

Pattern: Orchestrator -> Tool Calls + Validation Loop (max 3 retries)
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.output_tools")


# =============================================================================
# Tool Schemas
# =============================================================================

class GenerateBlueprintInput(BaseModel):
    """Input schema for generate_blueprint tool."""
    game_plan: Dict[str, Any] = Field(description="Game plan from planner")
    scene_structure: Optional[Dict[str, Any]] = Field(default=None)
    scene_assets: Optional[Dict[str, Any]] = Field(default=None)
    scene_interactions: Optional[Dict[str, Any]] = Field(default=None)
    diagram_zones: List[Dict[str, Any]] = Field(description="Detected zones")
    zone_groups: Optional[List[Dict[str, Any]]] = Field(default=None)
    template_type: str = Field(description="Template type")
    domain_knowledge: Optional[Dict[str, Any]] = Field(default=None)
    previous_errors: Optional[List[str]] = Field(
        default=None,
        description="Errors from previous validation attempt (for retry)"
    )


class GenerateBlueprintOutput(BaseModel):
    """Output schema for generate_blueprint tool."""
    success: bool
    blueprint: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ValidateBlueprintInput(BaseModel):
    """Input schema for validate_blueprint tool."""
    blueprint: Dict[str, Any] = Field(description="Blueprint to validate")
    template_type: str = Field(description="Expected template type")


class ValidateBlueprintOutput(BaseModel):
    """Output schema for validate_blueprint tool."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    score: float = Field(default=0.0, description="Validation score 0.0-1.0")


class GenerateSpecInput(BaseModel):
    """Input schema for generate_spec tool."""
    blueprint: Dict[str, Any] = Field(description="Validated blueprint")
    template_type: str = Field(description="Template type")


class GenerateSpecOutput(BaseModel):
    """Output schema for generate_spec tool."""
    success: bool
    diagram_spec: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RenderSvgInput(BaseModel):
    """Input schema for render_svg tool."""
    diagram_spec: Dict[str, Any] = Field(description="Diagram spec to render")


class RenderSvgOutput(BaseModel):
    """Output schema for render_svg tool."""
    success: bool
    svg_content: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Tool Implementations
# =============================================================================

async def generate_blueprint(
    game_plan: Dict[str, Any],
    diagram_zones: List[Dict[str, Any]],
    template_type: str,
    scene_structure: Optional[Dict[str, Any]] = None,
    scene_assets: Optional[Dict[str, Any]] = None,
    scene_interactions: Optional[Dict[str, Any]] = None,
    zone_groups: Optional[List[Dict[str, Any]]] = None,
    domain_knowledge: Optional[Dict[str, Any]] = None,
    pedagogical_context: Optional[Dict[str, Any]] = None,
    previous_errors: Optional[List[str]] = None,
) -> GenerateBlueprintOutput:
    """
    Generate game blueprint using the blueprint_generator agent.

    If previous_errors are provided, the prompt is enhanced to avoid
    those specific errors (retry with error context).
    """
    try:
        from app.agents.blueprint_generator import blueprint_generator_agent
        from app.agents.state import AgentState

        # Build state with all context
        state: AgentState = {
            "question_id": "had_blueprint",
            "question_text": game_plan.get("question_text", ""),
            "question_options": None,
            "template_selection": {"template_type": template_type},
            "domain_knowledge": domain_knowledge,
            "pedagogical_context": pedagogical_context or {},
            "routing_confidence": 1.0,
            "routing_requires_human_review": False,
            "game_plan": game_plan,
            "scene_structure": scene_structure,
            "scene_assets": scene_assets,
            "scene_interactions": scene_interactions,
            "diagram_zones": diagram_zones,
            "zone_groups": zone_groups,
            # Other required fields
            "diagram_image": None,
            "sam3_prompts": None,
            "diagram_segments": None,
            "diagram_labels": None,
            "cleaned_image_path": None,
            "removed_labels": None,
            "generated_diagram_path": None,
            "annotation_elements": None,
            "image_classification": None,
            "retry_image_search": False,
            "image_search_attempts": 0,
            "max_image_attempts": 3,
            "scene_data": None,
            "story_data": None,
            "blueprint": None,
            "generated_code": None,
            "asset_urls": None,
            "diagram_svg": None,
            "diagram_spec": None,
            "needs_multi_scene": None,
            "num_scenes": None,
            "scene_progression_type": None,
            "scene_breakdown": None,
            "scene_diagrams": None,
            "scene_zones": None,
            "scene_labels": None,
            "diagram_type": None,
            "diagram_type_config": None,
            "diagram_analysis": None,
            "game_design": None,
            "planned_assets": None,
            "generated_assets": None,
            "asset_validation": None,
            "_pipeline_preset": None,
            "_ai_images_generated": 0,
            "validation_results": {},
            "current_validation_errors": previous_errors or [],
            "retry_counts": {},
            "max_retries": 3,
            "pending_human_review": None,
            "human_feedback": None,
            "human_review_completed": False,
            "current_agent": "blueprint_generator",
            "agent_history": [],
            "started_at": "",
            "last_updated_at": "",
            "_run_id": None,
            "_stage_order": 0,
            "final_visualization_id": None,
            "generation_complete": False,
            "error_message": None,
        }

        result = await blueprint_generator_agent(state, ctx=None)

        blueprint = result.get("blueprint")
        if not blueprint:
            return GenerateBlueprintOutput(
                success=False,
                error="Blueprint generator returned no blueprint"
            )

        return GenerateBlueprintOutput(
            success=True,
            blueprint=blueprint
        )

    except Exception as e:
        logger.error(f"Blueprint generation failed: {e}", exc_info=True)
        return GenerateBlueprintOutput(
            success=False,
            error=str(e)
        )


async def validate_blueprint(
    blueprint: Dict[str, Any],
    template_type: str,
) -> ValidateBlueprintOutput:
    """
    Validate blueprint using rule-based validation.

    Returns detailed errors and warnings for the orchestrator
    to reason about and potentially retry generation.
    """
    try:
        from app.agents.playability_validator import validate_playability

        is_valid, score, message = await validate_playability(
            blueprint=blueprint,
            template_type=template_type,
        )

        # Parse message into errors/warnings
        errors = []
        warnings = []

        if not is_valid:
            # Split message by common delimiters
            parts = message.replace("; ", "\n").split("\n")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if "warning" in part.lower():
                    warnings.append(part)
                else:
                    errors.append(part)

        return ValidateBlueprintOutput(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            score=score
        )

    except Exception as e:
        logger.error(f"Blueprint validation failed: {e}")
        return ValidateBlueprintOutput(
            is_valid=False,
            errors=[f"Validation error: {str(e)}"],
            score=0.0
        )


async def generate_spec(
    blueprint: Dict[str, Any],
    template_type: str,
) -> GenerateSpecOutput:
    """
    Generate diagram specification from validated blueprint.

    Uses diagram_spec_generator for INTERACTIVE_DIAGRAM templates.
    """
    try:
        if template_type != "INTERACTIVE_DIAGRAM":
            # Only INTERACTIVE_DIAGRAM needs diagram spec
            return GenerateSpecOutput(
                success=True,
                diagram_spec=None
            )

        from app.agents.diagram_spec_generator import diagram_spec_generator
        from app.agents.state import AgentState

        state: AgentState = {
            "question_id": "had_spec",
            "question_text": "",
            "question_options": None,
            "template_selection": {"template_type": template_type},
            "domain_knowledge": None,
            "pedagogical_context": None,
            "routing_confidence": 1.0,
            "routing_requires_human_review": False,
            "game_plan": None,
            "blueprint": blueprint,
            "diagram_zones": blueprint.get("zones", []),
            "diagram_labels": blueprint.get("labels", []),
            "zone_groups": blueprint.get("zoneGroups", []),
            # Other fields
            "diagram_image": None,
            "sam3_prompts": None,
            "diagram_segments": None,
            "cleaned_image_path": None,
            "removed_labels": None,
            "generated_diagram_path": None,
            "annotation_elements": None,
            "image_classification": None,
            "retry_image_search": False,
            "image_search_attempts": 0,
            "max_image_attempts": 3,
            "scene_data": None,
            "story_data": None,
            "scene_structure": None,
            "scene_assets": None,
            "scene_interactions": None,
            "generated_code": None,
            "asset_urls": None,
            "diagram_svg": None,
            "diagram_spec": None,
            "needs_multi_scene": None,
            "num_scenes": None,
            "scene_progression_type": None,
            "scene_breakdown": None,
            "scene_diagrams": None,
            "scene_zones": None,
            "scene_labels": None,
            "diagram_type": None,
            "diagram_type_config": None,
            "diagram_analysis": None,
            "game_design": None,
            "planned_assets": None,
            "generated_assets": None,
            "asset_validation": None,
            "_pipeline_preset": None,
            "_ai_images_generated": 0,
            "validation_results": {},
            "current_validation_errors": [],
            "retry_counts": {},
            "max_retries": 3,
            "pending_human_review": None,
            "human_feedback": None,
            "human_review_completed": False,
            "current_agent": "diagram_spec_generator",
            "agent_history": [],
            "started_at": "",
            "last_updated_at": "",
            "_run_id": None,
            "_stage_order": 0,
            "final_visualization_id": None,
            "generation_complete": False,
            "error_message": None,
        }

        result = await diagram_spec_generator(state, ctx=None)

        diagram_spec = result.get("diagram_spec")
        return GenerateSpecOutput(
            success=True,
            diagram_spec=diagram_spec
        )

    except Exception as e:
        logger.error(f"Spec generation failed: {e}", exc_info=True)
        return GenerateSpecOutput(
            success=False,
            error=str(e)
        )


async def render_svg(
    diagram_spec: Dict[str, Any],
) -> RenderSvgOutput:
    """
    Render SVG from diagram specification.

    This is a deterministic operation - no LLM needed.
    """
    try:
        from app.agents.diagram_svg_generator import diagram_svg_generator
        from app.agents.state import AgentState

        state: AgentState = {
            "question_id": "had_svg",
            "question_text": "",
            "question_options": None,
            "template_selection": {"template_type": "INTERACTIVE_DIAGRAM"},
            "domain_knowledge": None,
            "pedagogical_context": None,
            "routing_confidence": 1.0,
            "routing_requires_human_review": False,
            "game_plan": None,
            "blueprint": None,
            "diagram_spec": diagram_spec,
            # Other fields
            "diagram_image": None,
            "sam3_prompts": None,
            "diagram_segments": None,
            "diagram_zones": None,
            "diagram_labels": None,
            "zone_groups": None,
            "cleaned_image_path": None,
            "removed_labels": None,
            "generated_diagram_path": None,
            "annotation_elements": None,
            "image_classification": None,
            "retry_image_search": False,
            "image_search_attempts": 0,
            "max_image_attempts": 3,
            "scene_data": None,
            "story_data": None,
            "scene_structure": None,
            "scene_assets": None,
            "scene_interactions": None,
            "generated_code": None,
            "asset_urls": None,
            "diagram_svg": None,
            "needs_multi_scene": None,
            "num_scenes": None,
            "scene_progression_type": None,
            "scene_breakdown": None,
            "scene_diagrams": None,
            "scene_zones": None,
            "scene_labels": None,
            "diagram_type": None,
            "diagram_type_config": None,
            "diagram_analysis": None,
            "game_design": None,
            "planned_assets": None,
            "generated_assets": None,
            "asset_validation": None,
            "_pipeline_preset": None,
            "_ai_images_generated": 0,
            "validation_results": {},
            "current_validation_errors": [],
            "retry_counts": {},
            "max_retries": 3,
            "pending_human_review": None,
            "human_feedback": None,
            "human_review_completed": False,
            "current_agent": "diagram_svg_generator",
            "agent_history": [],
            "started_at": "",
            "last_updated_at": "",
            "_run_id": None,
            "_stage_order": 0,
            "final_visualization_id": None,
            "generation_complete": False,
            "error_message": None,
        }

        result = await diagram_svg_generator(state, ctx=None)

        svg_content = result.get("diagram_svg")
        return RenderSvgOutput(
            success=True,
            svg_content=svg_content
        )

    except Exception as e:
        logger.error(f"SVG rendering failed: {e}", exc_info=True)
        return RenderSvgOutput(
            success=False,
            error=str(e)
        )


# =============================================================================
# Tool Registry for HAD
# =============================================================================

OUTPUT_TOOLS = {
    "generate_blueprint": {
        "function": generate_blueprint,
        "input_schema": GenerateBlueprintInput,
        "output_schema": GenerateBlueprintOutput,
        "description": "Generate game blueprint from plan and zones",
    },
    "validate_blueprint": {
        "function": validate_blueprint,
        "input_schema": ValidateBlueprintInput,
        "output_schema": ValidateBlueprintOutput,
        "description": "Validate blueprint structure and content",
    },
    "generate_spec": {
        "function": generate_spec,
        "input_schema": GenerateSpecInput,
        "output_schema": GenerateSpecOutput,
        "description": "Generate diagram specification from blueprint",
    },
    "render_svg": {
        "function": render_svg,
        "input_schema": RenderSvgInput,
        "output_schema": RenderSvgOutput,
        "description": "Render SVG from diagram specification",
    },
}
