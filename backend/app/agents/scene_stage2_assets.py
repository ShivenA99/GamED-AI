"""
Stage 2: Scene Assets Generation
Generates detailed assets and layout based on Stage 1 structure

Inputs: question_text, question_options, game_plan, template_selection, scene_structure, domain_knowledge, diagram_zones
Outputs: scene_assets
"""

import json
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field, validator

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.workflows.types import MECHANIC_TO_WORKFLOW
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.scene_stage2_assets")


# Pydantic Schemas
class AssetSpecifications(BaseModel):
    """Schema for asset specifications"""
    width: int = Field(..., ge=0, le=100, description="Width as percentage 0-100")
    height: int = Field(..., ge=0, le=100, description="Height as percentage 0-100")
    position: str = Field(..., min_length=3, max_length=30)
    features: List[str] = Field(default_factory=list, max_items=20)


class AssetSchema(BaseModel):
    """Schema for an individual asset"""
    id: str = Field(..., min_length=1, max_length=50)
    type: str = Field(..., pattern="^(component|animation|image|ui_element)$")
    description: str = Field(..., min_length=10, max_length=200)
    for_region: str = Field(..., min_length=1, max_length=50, description="Must match Stage 1 region ID")
    specifications: AssetSpecifications
    # Hierarchy support fields (optional)
    parent_asset_id: Optional[str] = Field(None, description="Parent asset ID for hierarchical grouping")
    hierarchy_level: int = Field(default=1, ge=1, le=5, description="Nesting level (1=top-level)")
    child_asset_ids: List[str] = Field(default_factory=list, description="IDs of child assets")
    initially_visible: bool = Field(default=True, description="Whether asset is visible on load (for progressive reveal)")

    @validator('id')
    def validate_id(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Asset ID must be alphanumeric with underscores')
        return v


class LayoutPanel(BaseModel):
    """Schema for layout panel"""
    id: str
    type: str
    position: Dict[str, Any]  # x, y, width, height
    z_index: int = Field(..., ge=0, le=100)


class LayoutSpecification(BaseModel):
    """Schema for layout specification"""
    layout_type: str = Field(..., pattern="^(center_focus|split_panel|grid|stack)$")
    panels: List[LayoutPanel] = Field(default_factory=list, max_items=20)


class AssetGroupSchema(BaseModel):
    """Schema for hierarchical asset grouping"""
    group_id: str = Field(..., description="Unique group identifier")
    parent_label: str = Field(..., description="The parent label this group represents")
    parent_asset_id: str = Field(..., description="The parent asset in this group")
    child_asset_ids: List[str] = Field(default_factory=list, description="Child assets in this group")
    reveal_trigger: str = Field(default="complete_parent", description="How children are revealed")


class MechanicAssetRequirement(BaseModel):
    """Asset requirement for a specific mechanic"""
    mechanic_type: str = Field(..., description="Mechanic type: drag_drop, trace_path, sequencing, sorting, etc.")
    required_assets: List[str] = Field(..., description="Asset IDs required for this mechanic")
    optional_assets: List[str] = Field(default_factory=list, description="Optional asset IDs that enhance this mechanic")
    workflow: str = Field(..., description="Workflow to generate these assets: labeling_diagram, trace_path, sequence_items, etc.")


class AssetsOutputSchema(BaseModel):
    """Schema for Stage 2 output"""
    required_assets: List[AssetSchema] = Field(..., min_items=1, max_items=50)
    layout_specification: LayoutSpecification
    # Hierarchy support (optional)
    asset_groups: List[AssetGroupSchema] = Field(default_factory=list, description="Hierarchical asset groups")
    # Mechanic-specific asset requirements
    asset_requirements_per_mechanic: List[MechanicAssetRequirement] = Field(
        default_factory=list,
        description="Asset requirements grouped by mechanic type"
    )

    @validator('required_assets')
    def validate_unique_asset_ids(cls, v):
        ids = [a.id for a in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Asset IDs must be unique')
        return v


def _build_interactive_diagram_context(
    template_type: str,
    required_labels: List[str],
    diagram_zones: List[Dict]
) -> str:
    """Build INTERACTIVE_DIAGRAM specific context for the prompt."""
    if template_type != "INTERACTIVE_DIAGRAM" or not required_labels:
        return ""

    # Generate expected asset IDs for each label
    label_asset_ids = [f"label_target_{label.lower().replace(' ', '_')}" for label in required_labels[:8]]

    # Format zone positions if available
    zone_info = ""
    if diagram_zones:
        zone_positions = json.dumps(
            [{"label": z.get("label"), "x": z.get("x"), "y": z.get("y")} for z in diagram_zones[:8]],
            indent=2
        )
        zone_info = f"""
## Diagram Zone Positions (from zone detection):
These coordinates can help position label targets:
{zone_positions}
"""
    else:
        zone_info = "\n## Diagram Zone Positions: Not yet detected\n"

    return f"""
## INTERACTIVE_DIAGRAM Specific Requirements:
The following labels MUST have corresponding label_target_* assets:
{json.dumps(required_labels[:8], indent=2)}

Create ONE `label_target_*` asset for EACH label above.
Expected asset IDs: {', '.join(label_asset_ids)}
{zone_info}"""


def _generate_asset_groups_from_hierarchy(
    hierarchy_info: Dict[str, Any],
    assets: List[Dict]
) -> List[Dict]:
    """Generate asset groups from hierarchy_info when LLM doesn't provide them."""
    if not hierarchy_info or not hierarchy_info.get("is_hierarchical"):
        return []

    parent_children = hierarchy_info.get("parent_children", {})
    reveal_trigger = hierarchy_info.get("reveal_trigger", "complete_parent")

    # Build lookup from label to asset ID
    asset_lookup = {}
    for asset in assets:
        asset_id = asset.get("id", "")
        if asset_id.startswith("label_target_"):
            # Extract label from asset ID (e.g., "label_target_nucleus" -> "nucleus")
            label_lower = asset_id.replace("label_target_", "").replace("_", " ")
            asset_lookup[label_lower] = asset_id

    groups = []
    for parent, children in parent_children.items():
        parent_lower = parent.lower()
        parent_asset_id = asset_lookup.get(parent_lower)

        if not parent_asset_id:
            # Try alternative matching
            for key in asset_lookup:
                if parent_lower in key or key in parent_lower:
                    parent_asset_id = asset_lookup[key]
                    break

        if not parent_asset_id:
            continue

        child_asset_ids = []
        for child in children:
            child_lower = child.lower()
            child_asset_id = asset_lookup.get(child_lower)
            if not child_asset_id:
                # Try alternative matching
                for key in asset_lookup:
                    if child_lower in key or key in child_lower:
                        child_asset_id = asset_lookup[key]
                        break
            if child_asset_id:
                child_asset_ids.append(child_asset_id)

        if child_asset_ids:
            groups.append({
                "group_id": f"{parent_lower.replace(' ', '_')}_group",
                "parent_label": parent,
                "parent_asset_id": parent_asset_id,
                "child_asset_ids": child_asset_ids,
                "reveal_trigger": reveal_trigger
            })

    return groups


# Use canonical mapping from workflows.types, plus legacy aliases
MECHANIC_TO_WORKFLOW_MAP: Dict[str, str] = {
    **MECHANIC_TO_WORKFLOW,
    # Legacy/alternative names not in canonical map
    "order": "sequence_items",
    "sequence": "sequence_items",
    "match": "memory_match",
}

# Asset patterns required for each mechanic type
MECHANIC_ASSET_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "drag_drop": {
        "required_patterns": ["label_target_", "diagram", "label_options"],
        "optional_patterns": ["feedback", "hint_button", "check_button", "reset_button"],
    },
    "trace_path": {
        "required_patterns": ["path_", "diagram", "start_point", "end_point"],
        "optional_patterns": ["waypoint_", "path_animation", "trace_hint"],
    },
    "sequencing": {
        "required_patterns": ["sequence_item_", "sequence_slot_"],
        "optional_patterns": ["timeline", "sequence_hint", "order_indicator"],
    },
    "sorting": {
        "required_patterns": ["sort_item_", "bucket_", "category_"],
        "optional_patterns": ["sort_hint", "category_label"],
    },
    "comparison": {
        "required_patterns": ["diagram_left", "diagram_right", "comparison_point_"],
        "optional_patterns": ["similarity_indicator", "difference_indicator"],
    },
    "click_to_identify": {
        "required_patterns": ["clickable_", "hotspot_", "diagram"],
        "optional_patterns": ["info_popup", "highlight_overlay"],
    },
    "reveal": {
        "required_patterns": ["hidden_", "reveal_trigger_", "diagram"],
        "optional_patterns": ["reveal_animation", "progressive_hint"],
    },
    "hotspot": {
        "required_patterns": ["hotspot_", "diagram"],
        "optional_patterns": ["tooltip_", "info_panel"],
    },
    "memory_match": {
        "required_patterns": ["card_", "match_pair_"],
        "optional_patterns": ["flip_animation", "match_indicator"],
    },
    "branching_scenario": {
        "required_patterns": ["decision_point_", "branch_", "scenario_"],
        "optional_patterns": ["consequence_", "path_indicator"],
    },
}


def _build_mechanic_asset_requirements(
    mechanics: List[Dict[str, Any]],
    assets: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build asset requirements for each mechanic type.

    Groups assets by mechanic type based on the mechanics defined in game_plan
    and the assets generated.

    Args:
        mechanics: List of mechanic specs from game_plan.game_mechanics or scene_breakdown.mechanics
        assets: List of generated asset dictionaries

    Returns:
        List of MechanicAssetRequirement-compatible dictionaries
    """
    if not mechanics or not assets:
        return []

    # Create a lookup of asset IDs
    asset_ids = [a.get("id", "") for a in assets]

    mechanic_requirements: List[Dict[str, Any]] = []

    for mechanic in mechanics:
        mechanic_type = (mechanic.get("type") or "").lower()
        mechanic_id = mechanic.get("id", mechanic_type)

        # Get workflow for this mechanic
        workflow = MECHANIC_TO_WORKFLOW_MAP.get(mechanic_type, "labeling_diagram")

        # Get asset patterns for this mechanic
        patterns = MECHANIC_ASSET_PATTERNS.get(mechanic_type, {
            "required_patterns": [],
            "optional_patterns": []
        })

        required_assets: List[str] = []
        optional_assets: List[str] = []

        # Match assets to required patterns
        for asset_id in asset_ids:
            asset_id_lower = asset_id.lower()

            # Check required patterns
            for pattern in patterns.get("required_patterns", []):
                if pattern.lower() in asset_id_lower:
                    if asset_id not in required_assets:
                        required_assets.append(asset_id)
                    break

            # Check optional patterns
            for pattern in patterns.get("optional_patterns", []):
                if pattern.lower() in asset_id_lower:
                    if asset_id not in optional_assets and asset_id not in required_assets:
                        optional_assets.append(asset_id)
                    break

        # For drag_drop specifically, include all label_target_ assets
        if mechanic_type == "drag_drop":
            for asset_id in asset_ids:
                if "label_target_" in asset_id.lower() and asset_id not in required_assets:
                    required_assets.append(asset_id)

        # For trace_path, include all path_ assets
        if mechanic_type == "trace_path":
            for asset_id in asset_ids:
                if "path_" in asset_id.lower() and asset_id not in required_assets:
                    required_assets.append(asset_id)

        # For sequencing, include all sequence_ assets
        if mechanic_type in ("sequencing", "sequence", "order"):
            for asset_id in asset_ids:
                if any(p in asset_id.lower() for p in ["sequence_", "order_", "step_"]):
                    if asset_id not in required_assets:
                        required_assets.append(asset_id)

        # Only add if we found some assets for this mechanic
        if required_assets:
            mechanic_requirements.append({
                "mechanic_type": mechanic_type,
                "required_assets": required_assets,
                "optional_assets": optional_assets,
                "workflow": workflow
            })

    return mechanic_requirements


def _build_hierarchy_asset_context(hierarchy_info: Optional[Dict[str, Any]]) -> str:
    """Build hierarchy-specific context for asset generation."""
    if not hierarchy_info or not hierarchy_info.get("is_hierarchical"):
        return ""

    parent_children = hierarchy_info.get("parent_children", {})
    reveal_trigger = hierarchy_info.get("reveal_trigger", "complete_parent")

    # Format parent-children relationships
    hierarchy_lines = []
    for parent, children in parent_children.items():
        parent_asset_id = f"label_target_{parent.lower().replace(' ', '_')}"
        child_asset_ids = [f"label_target_{c.lower().replace(' ', '_')}" for c in children]
        hierarchy_lines.append(f"  - Parent: {parent_asset_id}")
        hierarchy_lines.append(f"    Children: {', '.join(child_asset_ids)}")

    return f"""
## HIERARCHICAL ASSET GROUPING:
This content has parent-child relationships. Create assets with proper hierarchy metadata.

### Parent-Children Asset Relationships:
{chr(10).join(hierarchy_lines)}

### Reveal Trigger: {reveal_trigger}

### Asset Hierarchy Requirements:
1. Parent assets: Set hierarchy_level=1, initially_visible=true
2. Child assets: Set hierarchy_level=2, initially_visible=false, parent_asset_id=<parent>
3. Include child_asset_ids array on parent assets
4. Create asset_groups array to define the groupings

### Hierarchical Asset Example:
For a cell with organelles (nucleus as parent, nucleolus as child):
```json
{{
    "required_assets": [
        {{
            "id": "label_target_nucleus",
            "type": "component",
            "description": "Target zone for Nucleus label",
            "for_region": "diagram_region",
            "specifications": {{"width": 10, "height": 10, "position": "center", "features": ["drop_zone"]}},
            "parent_asset_id": null,
            "hierarchy_level": 1,
            "child_asset_ids": ["label_target_nucleolus"],
            "initially_visible": true
        }},
        {{
            "id": "label_target_nucleolus",
            "type": "component",
            "description": "Target zone for Nucleolus label (child of Nucleus)",
            "for_region": "diagram_region",
            "specifications": {{"width": 5, "height": 5, "position": "center", "features": ["drop_zone", "initially_hidden"]}},
            "parent_asset_id": "label_target_nucleus",
            "hierarchy_level": 2,
            "child_asset_ids": [],
            "initially_visible": false
        }}
    ],
    "asset_groups": [
        {{
            "group_id": "nucleus_group",
            "parent_label": "Nucleus",
            "parent_asset_id": "label_target_nucleus",
            "child_asset_ids": ["label_target_nucleolus"],
            "reveal_trigger": "{reveal_trigger}"
        }}
    ]
}}
```
"""


async def scene_stage2_assets(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Stage 2: Generate detailed assets based on structure.

    Inputs: question_text, question_options, game_plan, template_selection, scene_structure, domain_knowledge, diagram_zones
    Outputs: scene_assets

    Returns state update with scene_assets.
    """
    logger.info("Stage 2: Generating scene assets")

    # Extract inputs from state
    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    game_plan = state.get("game_plan", {})
    template_type = state.get("template_selection", {}).get("template_type", "")

    # Extract hierarchy_info from game_plan
    hierarchy_info = game_plan.get("hierarchy_info")

    # Extract domain knowledge for content-aware asset generation
    domain_knowledge = state.get("domain_knowledge", {})
    canonical_labels = domain_knowledge.get("canonical_labels", [])
    # Use required_labels from game_plan if available, otherwise fall back to canonical_labels
    required_labels = game_plan.get("required_labels", canonical_labels)
    diagram_zones = state.get("diagram_zones", [])

    # Get structure from Stage 1 output
    structure = state.get("scene_structure", {})

    # Extract structure info
    regions = structure.get("regions", [])
    visual_theme = structure.get("visual_theme", "educational")
    layout_type = structure.get("layout_type", "center_focus")

    # Format regions for prompt
    regions_json = json.dumps(regions, indent=2)

    # Format game mechanics
    mechanics = game_plan.get("game_mechanics", [])
    mechanics_json = json.dumps(mechanics, indent=2)

    # Format answer options
    options_str = ""
    if question_options:
        options_str = "\n## Answer Options:\n" + "\n".join(f"- {opt}" for opt in question_options)

    # Build prompt for Stage 2
    prompt = f"""Create detailed ASSETS and LAYOUT for the game scene.

## Question Context:
{question_text}{options_str}

## Template Type: {template_type}

## Structure from Stage 1:
- Visual Theme: {visual_theme}
- Layout Type: {layout_type}
- Regions Defined:
{regions_json}

## Game Mechanics to Support:
{mechanics_json}
{_build_interactive_diagram_context(template_type, required_labels, diagram_zones)}{_build_hierarchy_asset_context(hierarchy_info)}
## Your Task (Stage 2 - Assets & Layout ONLY):

For EACH region from Stage 1, specify the exact components needed:

### Component Specifications:
- **id**: Unique identifier (snake_case, e.g., "flower_diagram", "label_petal")
- **type**: "component", "animation", "image", or "ui_element"
- **description**: What this asset does (10-200 characters)
- **for_region**: Which region ID this belongs to (MUST match a region from Stage 1)
- **specifications**: Object with:
  - width: Numeric value 0-100 (percentage)
  - height: Numeric value 0-100 (percentage)
  - position: "left", "right", "top", "bottom", "center", etc.
  - features: Array of feature strings
- **parent_asset_id**: (optional) ID of parent asset for hierarchy
- **hierarchy_level**: (optional) 1 for top-level, 2 for children
- **child_asset_ids**: (optional) Array of child asset IDs
- **initially_visible**: (optional) true/false for progressive reveal

### Layout Specification:
- **layout_type**: Must match Stage 1 ({layout_type})
- **panels**: Array of panel objects with exact positions (numeric 0-100 for x, y, width, height)

### Asset Groups (for hierarchical content):
- **group_id**: Unique group identifier
- **parent_label**: The parent label name
- **parent_asset_id**: The parent asset in this group
- **child_asset_ids**: Array of child assets
- **reveal_trigger**: "complete_parent", "click_expand", or "hover_reveal"

## Example 1: INTERACTIVE_DIAGRAM Assets (Flower Parts)

```json
{{
    "required_assets": [
        {{
            "id": "flower_diagram",
            "type": "image",
            "description": "Detailed botanical illustration of a flower with unlabeled parts",
            "for_region": "diagram_region",
            "specifications": {{
                "width": 90,
                "height": 85,
                "position": "center",
                "features": ["high_resolution", "labeled_zones", "svg_format"]
            }}
        }},
        {{
            "id": "label_target_petal",
            "type": "component",
            "description": "Target zone on flower diagram where 'Petal' label should be placed",
            "for_region": "diagram_region",
            "specifications": {{
                "width": 8,
                "height": 8,
                "position": "top_left_relative",
                "features": ["drop_zone", "highlight_on_hover", "snap_to_position"]
            }}
        }},
        {{
            "id": "label_target_stamen",
            "type": "component",
            "description": "Target zone for 'Stamen' label",
            "for_region": "diagram_region",
            "specifications": {{
                "width": 8,
                "height": 8,
                "position": "center_relative",
                "features": ["drop_zone", "highlight_on_hover"]
            }}
        }},
        {{
            "id": "label_target_pistil",
            "type": "component",
            "description": "Target zone for 'Pistil' label",
            "for_region": "diagram_region",
            "specifications": {{
                "width": 8,
                "height": 8,
                "position": "center_relative",
                "features": ["drop_zone", "highlight_on_hover"]
            }}
        }},
        {{
            "id": "label_target_sepal",
            "type": "component",
            "description": "Target zone for 'Sepal' label",
            "for_region": "diagram_region",
            "specifications": {{
                "width": 8,
                "height": 8,
                "position": "bottom_relative",
                "features": ["drop_zone", "highlight_on_hover"]
            }}
        }},
        {{
            "id": "label_options_container",
            "type": "component",
            "description": "Container holding draggable label options (Petal, Stamen, Pistil, Sepal)",
            "for_region": "label_options_region",
            "specifications": {{
                "width": 90,
                "height": 80,
                "position": "center",
                "features": ["draggable_items", "grid_layout", "4_items"]
            }}
        }},
        {{
            "id": "feedback_message",
            "type": "component",
            "description": "Text area displaying success/error messages and score",
            "for_region": "feedback_region",
            "specifications": {{
                "width": 95,
                "height": 80,
                "position": "center",
                "features": ["dynamic_text", "color_coding", "icon_support"]
            }}
        }},
        {{
            "id": "check_answer_button",
            "type": "component",
            "description": "Button to validate label placements",
            "for_region": "controls_region",
            "specifications": {{
                "width": 15,
                "height": 60,
                "position": "left",
                "features": ["primary_action", "enabled_state_toggle"]
            }}
        }},
        {{
            "id": "hint_button",
            "type": "component",
            "description": "Button to reveal hint for next label",
            "for_region": "controls_region",
            "specifications": {{
                "width": 10,
                "height": 60,
                "position": "center",
                "features": ["secondary_action", "hint_counter"]
            }}
        }},
        {{
            "id": "reset_button",
            "type": "component",
            "description": "Button to reset all labels to starting position",
            "for_region": "controls_region",
            "specifications": {{
                "width": 10,
                "height": 60,
                "position": "right",
                "features": ["tertiary_action", "confirm_dialog"]
            }}
        }}
    ],
    "layout_specification": {{
        "layout_type": "center_focus",
        "panels": [
            {{
                "id": "main_diagram_panel",
                "type": "diagram_container",
                "position": {{"x": 5, "y": 10, "width": 60, "height": 70}},
                "z_index": 1
            }},
            {{
                "id": "labels_sidebar",
                "type": "stack",
                "position": {{"x": 68, "y": 10, "width": 28, "height": 70}},
                "z_index": 1
            }},
            {{
                "id": "feedback_bar",
                "type": "horizontal_container",
                "position": {{"x": 0, "y": 82, "width": 100, "height": 13}},
                "z_index": 2
            }},
            {{
                "id": "controls_bar",
                "type": "toolbar",
                "position": {{"x": 75, "y": 2, "width": 23, "height": 6}},
                "z_index": 10
            }}
        ]
    }}
}}
```

## Example 2: STATE_TRACER_CODE Assets (Binary Search)

```json
{{
    "required_assets": [
        {{
            "id": "code_editor",
            "type": "component",
            "description": "Code editor showing binary search function with syntax highlighting",
            "for_region": "code_region",
            "specifications": {{
                "width": 95,
                "height": 90,
                "position": "center",
                "features": ["syntax_highlighting", "line_numbers", "line_highlighting"]
            }}
        }},
        {{
            "id": "variable_panel",
            "type": "component",
            "description": "Panel displaying current variable values",
            "for_region": "data_region",
            "specifications": {{
                "width": 90,
                "height": 40,
                "position": "top",
                "features": ["value_cards", "real_time_updates"]
            }}
        }},
        {{
            "id": "step_controls",
            "type": "component",
            "description": "Navigation buttons: Previous, Next, Play, Reset",
            "for_region": "controls_region",
            "specifications": {{
                "width": 100,
                "height": 80,
                "position": "center",
                "features": ["step_navigation", "auto_play"]
            }}
        }}
    ],
    "layout_specification": {{
        "layout_type": "split_panel",
        "panels": [
            {{
                "id": "code_panel",
                "type": "editor",
                "position": {{"x": 0, "y": 0, "width": 60, "height": 90}},
                "z_index": 1
            }},
            {{
                "id": "data_panel",
                "type": "stack",
                "position": {{"x": 60, "y": 0, "width": 40, "height": 90}},
                "z_index": 1
            }},
            {{
                "id": "controls",
                "type": "toolbar",
                "position": {{"x": 0, "y": 90, "width": 100, "height": 10}},
                "z_index": 10
            }}
        ]
    }}
}}
```

CRITICAL RULES:
- Create assets for ALL regions from Stage 1
- Every asset MUST reference a valid region ID from Stage 1
- For INTERACTIVE_DIAGRAM: Create label target zones for EACH answer option
- For INTERACTIVE_DIAGRAM: Include the diagram image and label options container
- All width/height/x/y values must be NUMBERS (0-100), not strings with % or px
- NO overlapping components
- Match the visual theme ({visual_theme})
{"- For HIERARCHICAL content: Set parent_asset_id, hierarchy_level, child_asset_ids, initially_visible correctly" if hierarchy_info and hierarchy_info.get("is_hierarchical") else ""}
{"- Create asset_groups array for parent-child relationships" if hierarchy_info and hierarchy_info.get("is_hierarchical") else ""}

Return ONLY valid JSON with:
- required_assets (array with hierarchy fields if applicable)
- layout_specification (object)
- asset_groups (array of group objects, empty if not hierarchical)
"""

    # Call LLM for Stage 2
    llm = get_llm_service()
    used_fallback = False

    try:
        result = await llm.generate_json_for_agent(
            agent_name="scene_stage2_assets",
            prompt=prompt,
            schema_hint="JSON with required_assets[], layout_specification, asset_groups[]"
        )

        # Ensure assets have hierarchy fields with defaults
        for asset in result.get("required_assets", []):
            if "parent_asset_id" not in asset:
                asset["parent_asset_id"] = None
            if "hierarchy_level" not in asset:
                asset["hierarchy_level"] = 1
            if "child_asset_ids" not in asset:
                asset["child_asset_ids"] = []
            if "initially_visible" not in asset:
                asset["initially_visible"] = True

        # Ensure asset_groups exists
        if "asset_groups" not in result:
            result["asset_groups"] = []

        # If hierarchy_info was provided but LLM didn't create asset_groups, generate them
        if hierarchy_info and hierarchy_info.get("is_hierarchical") and not result.get("asset_groups"):
            result["asset_groups"] = _generate_asset_groups_from_hierarchy(
                hierarchy_info, result.get("required_assets", [])
            )

        # Ensure asset_requirements_per_mechanic exists
        if "asset_requirements_per_mechanic" not in result:
            result["asset_requirements_per_mechanic"] = []

        # Build mechanic-specific asset requirements from game_plan mechanics
        if mechanics and result.get("required_assets"):
            # Convert mechanics JSON to list of dicts if needed
            mechanics_list = mechanics if isinstance(mechanics, list) else []
            result["asset_requirements_per_mechanic"] = _build_mechanic_asset_requirements(
                mechanics_list, result.get("required_assets", [])
            )
            logger.info(
                f"Built asset requirements for {len(result['asset_requirements_per_mechanic'])} mechanics",
                mechanic_types=[m.get("mechanic_type") for m in result["asset_requirements_per_mechanic"]]
            )

        # =====================================================================
        # CRITICAL FIX: Ensure ALL required_labels have corresponding assets
        # The LLM sometimes creates generic assets instead of individual label assets
        # =====================================================================
        if template_type == "INTERACTIVE_DIAGRAM" and required_labels:
            existing_assets = result.get("required_assets", [])
            existing_asset_ids = {a.get("id", "") for a in existing_assets}

            # Find the diagram region for label targets
            diagram_region_id = "diagram_region"
            for asset in existing_assets:
                if "diagram" in asset.get("id", "").lower() and asset.get("for_region"):
                    diagram_region_id = asset.get("for_region")
                    break

            # Count existing label_target assets
            label_target_count = sum(1 for aid in existing_asset_ids if "label_target_" in aid or "label_" in aid)

            # If we have fewer label targets than required_labels, add missing ones
            if label_target_count < len(required_labels):
                logger.info(f"Adding missing label assets: have {label_target_count}, need {len(required_labels)}")

                for i, label in enumerate(required_labels):
                    label_slug = label.lower().replace(" ", "_").replace("-", "_")
                    label_asset_id = f"label_target_{label_slug}"

                    # Check if this label already has an asset
                    has_asset = any(
                        label_slug in aid.lower() or aid == label_asset_id
                        for aid in existing_asset_ids
                    )

                    if not has_asset:
                        # Add the missing label asset
                        new_asset = {
                            "id": label_asset_id,
                            "type": "component",
                            "description": f"Target zone for '{label}' label drop zone",
                            "for_region": diagram_region_id,
                            "specifications": {
                                "width": 8,
                                "height": 8,
                                "position": "relative",
                                "features": ["drop_zone", "highlight_on_hover", "snap_to_position"]
                            },
                            "parent_asset_id": None,
                            "hierarchy_level": 1,
                            "child_asset_ids": [],
                            "initially_visible": True
                        }

                        # Check if this label is a child in hierarchy_info
                        if hierarchy_info and hierarchy_info.get("parent_children"):
                            for parent, children in hierarchy_info.get("parent_children", {}).items():
                                if label in children or label.lower() in [c.lower() for c in children]:
                                    parent_slug = parent.lower().replace(" ", "_").replace("-", "_")
                                    new_asset["parent_asset_id"] = f"label_target_{parent_slug}"
                                    new_asset["hierarchy_level"] = 2
                                    new_asset["initially_visible"] = False
                                    break

                        result["required_assets"].append(new_asset)
                        existing_asset_ids.add(label_asset_id)
                        logger.info(f"Added missing label asset: {label_asset_id}")

        # Validate LLM output against Pydantic schema
        try:
            AssetsOutputSchema(**result)
        except Exception as val_err:
            logger.warning(f"Stage 2 Pydantic validation warning: {val_err}")

        logger.info(f"Stage 2 complete: {len(result.get('required_assets', []))} assets defined, {len(result.get('asset_groups', []))} groups")

    except Exception as e:
        logger.error(f"Stage 2 failed: {e}")
        used_fallback = True
        # Return minimal assets with hierarchy fields
        result = {
            "required_assets": [
                {
                    "id": "main_component",
                    "type": "component",
                    "description": "Main interactive component",
                    "for_region": structure.get('regions', [{}])[0].get('id', 'main_region'),
                    "specifications": {
                        "width": 90,
                        "height": 80,
                        "position": "center",
                        "features": []
                    },
                    "parent_asset_id": None,
                    "hierarchy_level": 1,
                    "child_asset_ids": [],
                    "initially_visible": True
                }
            ],
            "layout_specification": {
                "layout_type": layout_type,
                "panels": []
            },
            "asset_groups": [],
            "asset_requirements_per_mechanic": []
        }

    # Track metrics if instrumentation context available
    if ctx:
        if used_fallback:
            ctx.set_fallback_used("LLM generation failed, using fallback assets")

    return {
        "scene_assets": result
    }


async def validate_assets(
    assets: Dict[str, Any],
    structure: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate Stage 2 assets output against Stage 1 structure.

    Progressive validation: Ensures assets reference valid regions from Stage 1.

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "validated_assets": Dict (if valid)
        }
    """
    logger.info("Validating Stage 2 assets")

    errors = []
    warnings = []

    try:
        # 1. Pydantic validation
        validated = AssetsOutputSchema(**assets)

        # 2. Progressive validation: Check assets reference valid regions
        valid_region_ids = {r['id'] for r in structure.get('regions', [])}

        for asset in assets.get('required_assets', []):
            for_region = asset.get('for_region', '')

            if for_region not in valid_region_ids:
                errors.append(
                    f"Asset '{asset.get('id')}' references invalid region '{for_region}'. "
                    f"Valid regions: {', '.join(valid_region_ids)}"
                )

        # 3. Check layout_type matches Stage 1
        structure_layout = structure.get('layout_type', '')
        assets_layout = assets.get('layout_specification', {}).get('layout_type', '')

        if structure_layout != assets_layout:
            errors.append(
                f"Layout mismatch: Stage 1 = '{structure_layout}', Stage 2 = '{assets_layout}'"
            )

        # 4. Check for overlapping components (spatial validation)
        positions = {}
        for asset in assets.get('required_assets', []):
            specs = asset.get('specifications', {})
            pos_key = (specs.get('position'), asset.get('for_region'))
            if pos_key in positions and pos_key != (None, None):
                warnings.append(
                    f"Potential overlap: '{asset.get('id')}' and '{positions[pos_key]}' "
                    f"both at position '{pos_key[0]}' in region '{pos_key[1]}'"
                )
            positions[pos_key] = asset.get('id')

        # 5. Template-specific validation
        template_type = structure.get('template_type', '')
        if template_type == 'INTERACTIVE_DIAGRAM':
            asset_ids = [a.get('id', '') for a in assets.get('required_assets', [])]
            label_targets = [aid for aid in asset_ids if aid.startswith('label_target_')]

            if not label_targets:
                warnings.append(
                    "INTERACTIVE_DIAGRAM should have 'label_target_*' assets for drop zones. "
                    "Consider adding assets like 'label_target_1', 'label_target_2', etc."
                )
            elif len(label_targets) < 3:
                warnings.append(
                    f"Only {len(label_targets)} label targets found. "
                    "Most label diagrams need 4+ targets."
                )

        # 6. Warnings for potential issues
        asset_count = len(assets.get('required_assets', []))
        if asset_count < 3:
            warnings.append(f"Only {asset_count} assets generated, might be insufficient")

        if asset_count > 30:
            warnings.append(f"{asset_count} assets is a lot, might be overcomplicated")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_assets": assets if len(errors) == 0 else None
        }

    except Exception as e:
        logger.error(f"Assets validation failed: {e}")
        errors.append(f"Validation error: {str(e)}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "validated_assets": None
        }


def create_fallback_assets(
    structure: Dict[str, Any],
    template_type: str,
    hierarchy_info: Optional[Dict[str, Any]] = None,
    mechanics: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Create minimal valid assets when Stage 2 fails"""

    layout_type = structure.get('layout_type', 'center_focus')

    assets = [
        {
            "id": "main_component",
            "type": "component",
            "description": "Main interactive component",
            "for_region": structure.get('regions', [{}])[0].get('id', 'main_region'),
            "specifications": {
                "width": 90,
                "height": 80,
                "position": "center",
                "features": []
            },
            "parent_asset_id": None,
            "hierarchy_level": 1,
            "child_asset_ids": [],
            "initially_visible": True
        }
    ]

    # Build mechanic requirements if mechanics provided
    asset_requirements_per_mechanic = []
    if mechanics:
        asset_requirements_per_mechanic = _build_mechanic_asset_requirements(mechanics, assets)

    return {
        "required_assets": assets,
        "layout_specification": {
            "layout_type": layout_type,
            "panels": []
        },
        "asset_groups": [],
        "asset_requirements_per_mechanic": asset_requirements_per_mechanic
    }