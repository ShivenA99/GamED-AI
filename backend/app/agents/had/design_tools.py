"""
Design Tools for HAD GAME_ORCHESTRATOR

Tool wrappers for game planning and scene generation stages.
These wrap existing agents (game_planner, scene_stage1/2/3) as tools
for the GAME_ORCHESTRATOR to coordinate.

Pattern: Orchestrator -> Sequential Tool Calls
(Scene stages have dependencies, so must be sequential)
"""

import asyncio
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.design_tools")


# =============================================================================
# Tool Schemas
# =============================================================================

class PlanGameInput(BaseModel):
    """Input schema for plan_game tool."""
    question_text: str = Field(description="The educational question")
    template_type: str = Field(description="Selected template (e.g., INTERACTIVE_DIAGRAM)")
    domain_knowledge: Dict[str, Any] = Field(description="Domain knowledge from retriever")
    pedagogical_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Bloom's level, subject, etc."
    )


class PlanGameOutput(BaseModel):
    """Output schema for plan_game tool."""
    success: bool
    game_plan: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DesignStructureInput(BaseModel):
    """Input schema for design_structure tool (Stage 1)."""
    game_plan: Dict[str, Any] = Field(description="Game plan from planner")
    template_type: str = Field(description="Selected template type")
    domain_knowledge: Optional[Dict[str, Any]] = Field(default=None)


class DesignStructureOutput(BaseModel):
    """Output schema for design_structure tool."""
    success: bool
    scene_structure: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DesignAssetsInput(BaseModel):
    """Input schema for design_assets tool (Stage 2)."""
    scene_structure: Dict[str, Any] = Field(description="Structure from Stage 1")
    game_plan: Dict[str, Any] = Field(description="Game plan")
    template_type: str = Field(description="Selected template type")


class DesignAssetsOutput(BaseModel):
    """Output schema for design_assets tool."""
    success: bool
    scene_assets: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DesignInteractionsInput(BaseModel):
    """Input schema for design_interactions tool (Stage 3)."""
    scene_structure: Dict[str, Any] = Field(description="Structure from Stage 1")
    scene_assets: Dict[str, Any] = Field(description="Assets from Stage 2")
    game_plan: Dict[str, Any] = Field(description="Game plan")
    template_type: str = Field(description="Selected template type")
    domain_knowledge: Optional[Dict[str, Any]] = Field(default=None)


class DesignInteractionsOutput(BaseModel):
    """Output schema for design_interactions tool."""
    success: bool
    scene_interactions: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# Tool Implementations
# =============================================================================

async def plan_game(
    question_text: str,
    template_type: str,
    domain_knowledge: Dict[str, Any],
    pedagogical_context: Optional[Dict[str, Any]] = None,
) -> PlanGameOutput:
    """
    Plan game mechanics and structure using the game_planner agent.

    This tool wraps the game_planner agent, which:
    - Defines learning objectives
    - Plans game mechanics based on template
    - Creates scoring rubric
    - Determines hierarchy info for progressive reveal
    """
    try:
        from app.agents.game_planner import game_planner_agent
        from app.agents.state import AgentState

        # Build minimal state for agent
        state: AgentState = {
            "question_id": "had_plan",
            "question_text": question_text,
            "question_options": None,
            "template_selection": {"template_type": template_type},
            "domain_knowledge": domain_knowledge,
            "pedagogical_context": pedagogical_context,
            "routing_confidence": 1.0,
            "routing_requires_human_review": False,
            # Required defaults
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
            "game_plan": None,
            "scene_data": None,
            "story_data": None,
            "blueprint": None,
            "generated_code": None,
            "asset_urls": None,
            "diagram_svg": None,
            "diagram_spec": None,
            "scene_structure": None,
            "scene_assets": None,
            "scene_interactions": None,
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
            "current_agent": "game_planner",
            "agent_history": [],
            "started_at": "",
            "last_updated_at": "",
            "_run_id": None,
            "_stage_order": 0,
            "final_visualization_id": None,
            "generation_complete": False,
            "error_message": None,
        }

        result = await game_planner_agent(state, ctx=None)

        game_plan_output = result.get("game_plan")
        if not game_plan_output:
            return PlanGameOutput(
                success=False,
                error="Game planner returned no game_plan"
            )

        return PlanGameOutput(
            success=True,
            game_plan=game_plan_output
        )

    except Exception as e:
        logger.error(f"Game planning failed: {e}", exc_info=True)
        return PlanGameOutput(
            success=False,
            error=str(e)
        )


async def design_structure(
    game_plan: Dict[str, Any],
    template_type: str,
    domain_knowledge: Optional[Dict[str, Any]] = None,
    pedagogical_context: Optional[Dict[str, Any]] = None,
) -> DesignStructureOutput:
    """
    Design scene structure (Stage 1) using scene_stage1_structure agent.

    Stage 1 defines:
    - Visual theme and layout
    - Scene regions and their purposes
    - Basic structure for asset placement
    """
    try:
        from app.agents.scene_stage1_structure import scene_stage1_structure
        from app.agents.state import AgentState

        # Build minimal state
        state: AgentState = {
            "question_id": "had_structure",
            "question_text": game_plan.get("question_text", ""),
            "question_options": None,
            "template_selection": {"template_type": template_type},
            "domain_knowledge": domain_knowledge or {},
            "pedagogical_context": pedagogical_context or {},
            "routing_confidence": 1.0,
            "routing_requires_human_review": False,
            "game_plan": game_plan,
            # Fill other required fields with defaults
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
            "blueprint": None,
            "generated_code": None,
            "asset_urls": None,
            "diagram_svg": None,
            "diagram_spec": None,
            "scene_structure": None,
            "scene_assets": None,
            "scene_interactions": None,
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
            "current_agent": "scene_stage1_structure",
            "agent_history": [],
            "started_at": "",
            "last_updated_at": "",
            "_run_id": None,
            "_stage_order": 0,
            "final_visualization_id": None,
            "generation_complete": False,
            "error_message": None,
        }

        result = await scene_stage1_structure(state, ctx=None)

        scene_structure = result.get("scene_structure")
        if not scene_structure:
            return DesignStructureOutput(
                success=False,
                error="Stage 1 returned no scene_structure"
            )

        return DesignStructureOutput(
            success=True,
            scene_structure=scene_structure
        )

    except Exception as e:
        logger.error(f"Structure design failed: {e}", exc_info=True)
        return DesignStructureOutput(
            success=False,
            error=str(e)
        )


async def design_assets(
    scene_structure: Dict[str, Any],
    game_plan: Dict[str, Any],
    template_type: str,
    domain_knowledge: Optional[Dict[str, Any]] = None,
    diagram_zones: Optional[List[Dict[str, Any]]] = None,
) -> DesignAssetsOutput:
    """
    Design scene assets (Stage 2) using scene_stage2_assets agent.

    Stage 2 defines:
    - Visual assets for each region
    - Layout specifications
    - Asset sources and parameters
    """
    try:
        from app.agents.scene_stage2_assets import scene_stage2_assets
        from app.agents.state import AgentState

        state: AgentState = {
            "question_id": "had_assets",
            "question_text": game_plan.get("question_text", ""),
            "question_options": None,
            "template_selection": {"template_type": template_type},
            "domain_knowledge": domain_knowledge or {},
            "pedagogical_context": {},
            "routing_confidence": 1.0,
            "routing_requires_human_review": False,
            "game_plan": game_plan,
            "scene_structure": scene_structure,
            # Fill other required fields
            "diagram_image": None,
            "sam3_prompts": None,
            "diagram_segments": None,
            "diagram_zones": diagram_zones or [],
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
            "blueprint": None,
            "generated_code": None,
            "asset_urls": None,
            "diagram_svg": None,
            "diagram_spec": None,
            "scene_assets": None,
            "scene_interactions": None,
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
            "current_agent": "scene_stage2_assets",
            "agent_history": [],
            "started_at": "",
            "last_updated_at": "",
            "_run_id": None,
            "_stage_order": 0,
            "final_visualization_id": None,
            "generation_complete": False,
            "error_message": None,
        }

        result = await scene_stage2_assets(state, ctx=None)

        scene_assets = result.get("scene_assets")
        if not scene_assets:
            return DesignAssetsOutput(
                success=False,
                error="Stage 2 returned no scene_assets"
            )

        return DesignAssetsOutput(
            success=True,
            scene_assets=scene_assets
        )

    except Exception as e:
        logger.error(f"Assets design failed: {e}", exc_info=True)
        return DesignAssetsOutput(
            success=False,
            error=str(e)
        )


async def design_interactions(
    scene_structure: Dict[str, Any],
    scene_assets: Dict[str, Any],
    game_plan: Dict[str, Any],
    template_type: str,
    domain_knowledge: Optional[Dict[str, Any]] = None,
) -> DesignInteractionsOutput:
    """
    Design scene interactions (Stage 3) using scene_stage3_interactions agent.

    Stage 3 defines:
    - User interactions and behaviors
    - Animation sequences
    - Feedback mechanisms
    - State transitions
    """
    try:
        from app.agents.scene_stage3_interactions import scene_stage3_interactions
        from app.agents.state import AgentState

        state: AgentState = {
            "question_id": "had_interactions",
            "question_text": game_plan.get("question_text", ""),
            "question_options": None,
            "template_selection": {"template_type": template_type},
            "domain_knowledge": domain_knowledge,
            "pedagogical_context": {},
            "routing_confidence": 1.0,
            "routing_requires_human_review": False,
            "game_plan": game_plan,
            "scene_structure": scene_structure,
            "scene_assets": scene_assets,
            # Fill other required fields
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
            "blueprint": None,
            "generated_code": None,
            "asset_urls": None,
            "diagram_svg": None,
            "diagram_spec": None,
            "scene_interactions": None,
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
            "current_agent": "scene_stage3_interactions",
            "agent_history": [],
            "started_at": "",
            "last_updated_at": "",
            "_run_id": None,
            "_stage_order": 0,
            "final_visualization_id": None,
            "generation_complete": False,
            "error_message": None,
        }

        result = await scene_stage3_interactions(state, ctx=None)

        scene_interactions = result.get("scene_interactions")
        if not scene_interactions:
            return DesignInteractionsOutput(
                success=False,
                error="Stage 3 returned no scene_interactions"
            )

        return DesignInteractionsOutput(
            success=True,
            scene_interactions=scene_interactions
        )

    except Exception as e:
        logger.error(f"Interactions design failed: {e}", exc_info=True)
        return DesignInteractionsOutput(
            success=False,
            error=str(e)
        )


# =============================================================================
# Tool Registry for HAD
# =============================================================================

DESIGN_TOOLS = {
    "plan_game": {
        "function": plan_game,
        "input_schema": PlanGameInput,
        "output_schema": PlanGameOutput,
        "description": "Plan game mechanics, learning objectives, and scoring",
    },
    "design_structure": {
        "function": design_structure,
        "input_schema": DesignStructureInput,
        "output_schema": DesignStructureOutput,
        "description": "Design scene structure and layout (Stage 1)",
    },
    "design_assets": {
        "function": design_assets,
        "input_schema": DesignAssetsInput,
        "output_schema": DesignAssetsOutput,
        "description": "Design visual assets for scene (Stage 2)",
    },
    "design_interactions": {
        "function": design_interactions,
        "input_schema": DesignInteractionsInput,
        "output_schema": DesignInteractionsOutput,
        "description": "Design interactions and animations (Stage 3)",
    },
}
