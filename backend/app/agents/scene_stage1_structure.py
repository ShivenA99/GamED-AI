"""
Stage 1: Scene Structure Generation
Generates high-level scene structure: theme, layout, regions

Inputs: question_text, question_options, game_plan, pedagogical_context, template_selection, domain_knowledge
Outputs: scene_structure
"""

import json
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field, validator, root_validator

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.config.pedagogical_constants import BLOOM_LEVELS

logger = get_logger("gamed_ai.agents.scene_stage1_structure")


# Pydantic Schemas for Validation
class RegionSchema(BaseModel):
    """Schema for a region in the scene structure"""
    id: str = Field(..., min_length=1, max_length=50, description="Region identifier")
    purpose: str = Field(..., min_length=10, max_length=200, description="What this region does")
    suggested_size: str = Field(..., min_length=3, max_length=50, description="Size suggestion")
    position: str = Field(..., min_length=3, max_length=30, description="Spatial position")
    # Hierarchy support fields (optional)
    parent_region_id: Optional[str] = Field(None, description="Parent region ID for nested regions")
    hierarchy_level: int = Field(default=1, ge=1, le=5, description="Nesting level (1=top-level)")
    child_region_ids: List[str] = Field(default_factory=list, description="IDs of child regions")

    @validator('id')
    def validate_id(cls, v):
        """Ensure ID is snake_case and reasonable"""
        if not v.replace('_', '').isalnum():
            raise ValueError('Region ID must be alphanumeric with underscores')
        if not v.islower():
            raise ValueError('Region ID must be lowercase')
        return v

    @validator('position')
    def validate_position(cls, v):
        """Ensure position is from valid set"""
        valid_positions = ['left', 'right', 'top', 'bottom', 'center',
                          'top_left', 'top_right', 'bottom_left', 'bottom_right']
        if v not in valid_positions:
            logger.warning(f"Position '{v}' not in standard set, but allowing")
        return v


class HierarchyMetadata(BaseModel):
    """Schema for hierarchy metadata in scene structure"""
    is_hierarchical: bool = Field(default=False, description="Whether the scene has hierarchical content")
    parent_children: Dict[str, List[str]] = Field(default_factory=dict, description="Parent to children mapping")
    reveal_trigger: str = Field(default="complete_parent", description="How children are revealed")
    recommended_mode: str = Field(default="drag_drop", description="Recommended interaction mode")


class StructureOutputSchema(BaseModel):
    """Schema for Stage 1 output"""
    visual_theme: str = Field(..., min_length=3, max_length=50)
    scene_title: str = Field(..., min_length=5, max_length=100)
    minimal_context: str = Field(..., min_length=10, max_length=500)
    layout_type: str = Field(..., pattern="^(center_focus|split_panel|grid|stack)$")
    regions: List[RegionSchema] = Field(..., min_items=1, max_items=10)
    # Hierarchy metadata (optional)
    hierarchy_metadata: Optional[HierarchyMetadata] = Field(None, description="Hierarchy information if applicable")

    @validator('regions')
    def validate_unique_region_ids(cls, v):
        """Ensure all region IDs are unique"""
        ids = [r.id for r in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Region IDs must be unique')
        return v


def _build_hierarchy_context(hierarchy_info: Optional[Dict[str, Any]]) -> str:
    """Build hierarchy-specific context for the prompt."""
    if not hierarchy_info or not hierarchy_info.get("is_hierarchical"):
        return ""

    parent_children = hierarchy_info.get("parent_children", {})
    reveal_trigger = hierarchy_info.get("reveal_trigger", "complete_parent")
    recommended_mode = hierarchy_info.get("recommended_mode", "hierarchical")

    # Format parent-children relationships
    hierarchy_lines = []
    for parent, children in parent_children.items():
        hierarchy_lines.append(f"  - {parent}: {', '.join(children)}")

    return f"""
## HIERARCHICAL CONTENT DETECTED:
This content has parent-child relationships that require nested region structure.

### Parent-Children Relationships:
{chr(10).join(hierarchy_lines)}

### Reveal Trigger: {reveal_trigger}
- "complete_parent": Children revealed after parent is correctly labeled
- "click_expand": Children revealed when user clicks to expand parent
- "hover_reveal": Children revealed on hover

### Recommended Interaction Mode: {recommended_mode}

### Region Nesting Requirements:
1. Create PARENT regions at hierarchy_level=1 for top-level labels
2. Create CHILD regions at hierarchy_level=2 nested within parent regions
3. Set parent_region_id on child regions to link them to their parent
4. Include child_region_ids array on parent regions

### Example Hierarchical Region Structure:
For a cell with organelles (nucleus, mitochondria as children):
```json
[
    {{
        "id": "cell_region",
        "purpose": "Container for the entire cell with nested organelle regions",
        "suggested_size": "50% width, 60% height",
        "position": "center",
        "parent_region_id": null,
        "hierarchy_level": 1,
        "child_region_ids": ["nucleus_region", "mitochondria_region"]
    }},
    {{
        "id": "nucleus_region",
        "purpose": "Nested region for nucleus within cell, initially hidden",
        "suggested_size": "20% width, 20% height",
        "position": "center",
        "parent_region_id": "cell_region",
        "hierarchy_level": 2,
        "child_region_ids": []
    }},
    {{
        "id": "mitochondria_region",
        "purpose": "Nested region for mitochondria within cell, initially hidden",
        "suggested_size": "15% width, 15% height",
        "position": "right",
        "parent_region_id": "cell_region",
        "hierarchy_level": 2,
        "child_region_ids": []
    }}
]
```
"""


async def scene_stage1_structure(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Stage 1: Generate high-level scene structure.

    Inputs: question_text, question_options, game_plan, pedagogical_context, template_selection, domain_knowledge
    Outputs: scene_structure

    Returns state update with scene_structure.
    """
    logger.info("Stage 1: Generating scene structure")

    # Extract context from state
    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    game_plan = state.get("game_plan", {})
    ped_context = state.get("pedagogical_context", {})
    template_selection = state.get("template_selection", {})

    # Extract hierarchy_info from game_plan
    hierarchy_info = game_plan.get("hierarchy_info")

    # Extract interaction_design from state (from interaction_designer agent)
    # Use 'or {}' pattern because state.get returns None if key exists with None value
    interaction_design = state.get("interaction_design") or {}
    reveal_strategy = interaction_design.get("reveal_strategy", {})
    zone_behavior = interaction_design.get("zone_behavior_strategy", {})

    # Extract domain knowledge for content-aware structure design
    domain_knowledge = state.get("domain_knowledge", {})
    canonical_labels = domain_knowledge.get("canonical_labels", [])

    template_type = template_selection.get("template_type", "INTERACTIVE_DIAGRAM")
    subject = ped_context.get("subject", "General")
    blooms_level = ped_context.get("blooms_level", "remember")

    # Build mechanics summary
    mechanics = game_plan.get("game_mechanics", [])
    mechanics_summary = "\n".join([
        f"- {m.get('type', 'interact')}: {m.get('description', '')}"
        for m in mechanics
    ])

    # Format answer options if available
    options_str = ""
    if question_options:
        options_str = "\n## Answer Options:\n" + "\n".join(f"- {opt}" for opt in question_options)

    # Build focused prompt for Stage 1
    prompt = f"""Design the high-level STRUCTURE for an interactive learning game scene.

## Question to Visualize:
{question_text}{options_str}

## Template Type: {template_type}

## Game Mechanics Needed:
{mechanics_summary}

## Educational Context:
- Subject: {subject}
- Bloom's Taxonomy Level: {blooms_level}
- Difficulty: {ped_context.get('difficulty', 'intermediate')}
{f'''
## Content-Specific Context (for INTERACTIVE_DIAGRAM):
- Labels to be placed: {', '.join(canonical_labels[:8]) if canonical_labels else 'Not yet determined'}
- Number of interactive elements needed: {len(canonical_labels) if canonical_labels else 'Variable'}
- Plan regions with enough space for {len(canonical_labels)} label targets
''' if template_type == 'INTERACTIVE_DIAGRAM' and canonical_labels else ''}{_build_hierarchy_context(hierarchy_info)}{f'''
## Interaction Design (from interaction_designer agent):
- Primary Mode: {interaction_design.get('primary_interaction_mode', 'drag_drop')}
- Reveal Strategy: {reveal_strategy.get('type', 'flat')} (trigger: {reveal_strategy.get('trigger', 'all_at_once')})
- Zone Behavior: default={zone_behavior.get('default_zone_type', 'circle')}
''' if interaction_design else ''}
## Your Task (Stage 1 - Structure ONLY):

Design ONLY the conceptual structure. Focus on:

1. **Visual Theme**: What metaphor/aesthetic fits this subject and template?
   - For biology/anatomy (INTERACTIVE_DIAGRAM): "botanical_explorer", "anatomy_lab", "naturalist"
   - For CS/programming (STATE_TRACER_CODE): "detective", "architect"
   - For science experiments: "laboratory", "explorer"
   - For math: "puzzle_solver", "pattern_hunter"

2. **Layout Type**: What spatial arrangement works best for the template?
   - "center_focus": Main diagram/image in center with labels around (BEST for INTERACTIVE_DIAGRAM)
   - "split_panel": Content on one side, interaction on other (good for code tracing)
   - "grid": Multiple equal sections (good for comparisons)
   - "stack": Vertical progression (good for sequences)

3. **Major Regions**: What functional areas are needed?
   - For INTERACTIVE_DIAGRAM: diagram_region (center), label_options_region, feedback_region, controls_region
   - For STATE_TRACER_CODE: code_region, data_region, controls_region
   - Each region has: id, purpose, suggested_size, position

DO NOT specify:
- ✗ Exact components (that's Stage 2)
- ✗ Pixel dimensions (that's Stage 2)
- ✗ Animations or interactions (that's Stage 3)

## Example 1: INTERACTIVE_DIAGRAM for Flower Parts (Non-Hierarchical)

```json
{{
    "visual_theme": "botanical_explorer",
    "scene_title": "Flower Anatomy Explorer",
    "minimal_context": "You're a botanist identifying the different parts of a flowering plant.",
    "layout_type": "center_focus",
    "regions": [
        {{
            "id": "diagram_region",
            "purpose": "Display the flower diagram with label target zones",
            "suggested_size": "60% width, 70% height",
            "position": "center",
            "hierarchy_level": 1,
            "parent_region_id": null,
            "child_region_ids": []
        }},
        {{
            "id": "label_options_region",
            "purpose": "Show draggable/clickable label options for students to choose from",
            "suggested_size": "30% width, 70% height",
            "position": "right",
            "hierarchy_level": 1,
            "parent_region_id": null,
            "child_region_ids": []
        }},
        {{
            "id": "feedback_region",
            "purpose": "Display feedback messages (correct/incorrect) and progress",
            "suggested_size": "100% width, 15% height",
            "position": "bottom",
            "hierarchy_level": 1,
            "parent_region_id": null,
            "child_region_ids": []
        }},
        {{
            "id": "controls_region",
            "purpose": "Action buttons: Check Answer, Hint, Reset",
            "suggested_size": "100% width, 50px",
            "position": "top_right",
            "hierarchy_level": 1,
            "parent_region_id": null,
            "child_region_ids": []
        }}
    ],
    "hierarchy_metadata": null
}}
```

## Example 2: STATE_TRACER_CODE for Algorithm

```json
{{
    "visual_theme": "detective",
    "scene_title": "Binary Search Detective",
    "minimal_context": "You're a code detective investigating how binary search finds the target.",
    "layout_type": "split_panel",
    "regions": [
        {{
            "id": "code_region",
            "purpose": "Display code with line-by-line highlighting",
            "suggested_size": "60% width",
            "position": "left"
        }},
        {{
            "id": "data_region",
            "purpose": "Show variable values and data visualization",
            "suggested_size": "35% width",
            "position": "right"
        }},
        {{
            "id": "controls_region",
            "purpose": "Step navigation controls",
            "suggested_size": "100% width, 50px",
            "position": "bottom"
        }}
    ]
}}
```

Based on the template type "{template_type}", choose the appropriate structure.
{"If hierarchical content was detected above, create nested regions with proper parent_region_id and child_region_ids." if hierarchy_info and hierarchy_info.get("is_hierarchical") else ""}

Return ONLY valid JSON with these exact fields:
- visual_theme (string)
- scene_title (string)
- minimal_context (string, 1-2 sentences)
- layout_type (string: center_focus, split_panel, grid, or stack)
- regions (array of objects with id, purpose, suggested_size, position, hierarchy_level, parent_region_id, child_region_ids)
- hierarchy_metadata (object with is_hierarchical, parent_children, reveal_trigger, recommended_mode - or null if not hierarchical)
"""

    # Call LLM for Stage 1
    llm = get_llm_service()
    used_fallback = False

    try:
        result = await llm.generate_json_for_agent(
            agent_name="scene_stage1_structure",
            prompt=prompt,
            schema_hint="JSON with visual_theme, scene_title, minimal_context, layout_type, regions[], hierarchy_metadata"
        )

        # If hierarchy_info was provided but LLM didn't include hierarchy_metadata, add it
        if hierarchy_info and hierarchy_info.get("is_hierarchical") and not result.get("hierarchy_metadata"):
            result["hierarchy_metadata"] = {
                "is_hierarchical": True,
                "parent_children": hierarchy_info.get("parent_children", {}),
                "reveal_trigger": hierarchy_info.get("reveal_trigger", "complete_parent"),
                "recommended_mode": hierarchy_info.get("recommended_mode", "hierarchical")
            }
            logger.info("Added hierarchy_metadata from game_plan to scene structure")

        # Ensure regions have hierarchy fields with defaults
        for region in result.get("regions", []):
            if "hierarchy_level" not in region:
                region["hierarchy_level"] = 1
            if "parent_region_id" not in region:
                region["parent_region_id"] = None
            if "child_region_ids" not in region:
                region["child_region_ids"] = []

        # Validate LLM output against Pydantic schema
        try:
            StructureOutputSchema(**result)
        except Exception as val_err:
            logger.warning(f"Stage 1 Pydantic validation warning: {val_err}")

        logger.info(f"Stage 1 complete: '{result.get('scene_title', 'Untitled')}' with {len(result.get('regions', []))} regions")

    except Exception as e:
        logger.error(f"Stage 1 failed: {e}")
        used_fallback = True
        # Return minimal structure for fallback with hierarchy fields
        result = {
            "visual_theme": "educational",
            "scene_title": f"Interactive {template_type} Scene",
            "minimal_context": "Learn through interactive exploration.",
            "layout_type": "center_focus",
            "regions": [
                {
                    "id": "main_region",
                    "purpose": "Main content",
                    "suggested_size": "100%",
                    "position": "center",
                    "hierarchy_level": 1,
                    "parent_region_id": None,
                    "child_region_ids": []
                }
            ],
            "hierarchy_metadata": {
                "is_hierarchical": hierarchy_info.get("is_hierarchical", False) if hierarchy_info else False,
                "parent_children": hierarchy_info.get("parent_children", {}) if hierarchy_info else {},
                "reveal_trigger": hierarchy_info.get("reveal_trigger", "complete_parent") if hierarchy_info else "complete_parent",
                "recommended_mode": hierarchy_info.get("recommended_mode", "drag_drop") if hierarchy_info else "drag_drop"
            } if hierarchy_info and hierarchy_info.get("is_hierarchical") else None
        }

    # Track metrics if instrumentation context available
    if ctx:
        if used_fallback:
            ctx.set_fallback_used("LLM generation failed, using fallback structure")
        # Note: LLM metrics are tracked by llm_service internally

    return {
        "scene_structure": result,
        "current_agent": "scene_stage1_structure"
    }


async def validate_structure(structure: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Stage 1 structure output.

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "validated_structure": Dict (if valid)
        }
    """
    logger.info("Validating Stage 1 structure")

    errors = []
    warnings = []

    try:
        # 1. Pydantic validation
        validated = StructureOutputSchema(**structure)

        # 2. Business logic validation
        regions = structure.get('regions', [])

        # Check: At least one region
        if len(regions) < 1:
            errors.append("Must have at least 1 region")

        # Check: Recommended minimum regions for certain templates
        layout_type = structure.get('layout_type', '')
        if layout_type == 'center_focus' and len(regions) < 2:
            warnings.append("center_focus layout typically needs 2+ regions (diagram + controls)")

        if layout_type == 'split_panel' and len(regions) < 2:
            warnings.append("split_panel layout typically needs 2+ regions")

        # Check: Region purposes are descriptive
        for region in regions:
            if len(region.get('purpose', '')) < 15:
                warnings.append(f"Region '{region.get('id')}' has very brief purpose")

        # 3. Template-specific validation
        template_type = structure.get('template_type', '')
        region_ids = {r.get('id') for r in regions}

        if template_type == 'INTERACTIVE_DIAGRAM':
            if 'diagram_region' not in region_ids:
                errors.append("INTERACTIVE_DIAGRAM requires a 'diagram_region' for the main diagram")
            if 'label_options_region' not in region_ids:
                warnings.append("INTERACTIVE_DIAGRAM typically has 'label_options_region' for draggable labels")

        elif template_type == 'STATE_TRACER_CODE':
            if 'code_region' not in region_ids:
                errors.append("STATE_TRACER_CODE requires a 'code_region' for code display")
            if 'trace_region' not in region_ids:
                warnings.append("STATE_TRACER_CODE typically has 'trace_region' for state tracking")

        elif template_type == 'SEQUENCE_BUILDER':
            if 'sequence_region' not in region_ids:
                warnings.append("SEQUENCE_BUILDER typically has 'sequence_region' for ordering")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_structure": structure if len(errors) == 0 else None
        }

    except Exception as e:
        logger.error(f"Structure validation failed: {e}")
        errors.append(f"Validation error: {str(e)}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "validated_structure": None
        }


def create_fallback_structure(
    template_type: str,
    subject: str,
    hierarchy_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create minimal valid structure when Stage 1 fails"""

    # Build hierarchy_metadata if applicable
    hierarchy_metadata = None
    if hierarchy_info and hierarchy_info.get("is_hierarchical"):
        hierarchy_metadata = {
            "is_hierarchical": True,
            "parent_children": hierarchy_info.get("parent_children", {}),
            "reveal_trigger": hierarchy_info.get("reveal_trigger", "complete_parent"),
            "recommended_mode": hierarchy_info.get("recommended_mode", "hierarchical")
        }

    if template_type == "INTERACTIVE_DIAGRAM":
        return {
            "visual_theme": "educational",
            "scene_title": "Interactive Labeling Activity",
            "minimal_context": "Label the parts of the diagram.",
            "layout_type": "center_focus",
            "regions": [
                {
                    "id": "diagram_region",
                    "purpose": "Display the main diagram to be labeled",
                    "suggested_size": "60% width, 70% height",
                    "position": "center",
                    "hierarchy_level": 1,
                    "parent_region_id": None,
                    "child_region_ids": []
                },
                {
                    "id": "label_options_region",
                    "purpose": "Container for draggable label options",
                    "suggested_size": "30% width",
                    "position": "right",
                    "hierarchy_level": 1,
                    "parent_region_id": None,
                    "child_region_ids": []
                }
            ],
            "hierarchy_metadata": hierarchy_metadata
        }
    else:  # STATE_TRACER_CODE or other
        return {
            "visual_theme": "detective" if "comput" in subject.lower() else "educational",
            "scene_title": f"Interactive {template_type} Scene",
            "minimal_context": "Explore the concept through interaction.",
            "layout_type": "split_panel",
            "regions": [
                {
                    "id": "main_region",
                    "purpose": "Main content display area",
                    "suggested_size": "100%",
                    "position": "center",
                    "hierarchy_level": 1,
                    "parent_region_id": None,
                    "child_region_ids": []
                }
            ],
            "hierarchy_metadata": hierarchy_metadata
        }