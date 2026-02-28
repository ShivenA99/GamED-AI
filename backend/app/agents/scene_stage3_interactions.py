"""
Stage 3: Scene Interactions Generation
Generates interactions, animations, and behavioral flows based on assets

Inputs: game_plan, template_selection, scene_structure, scene_assets, domain_knowledge, pedagogical_context
Outputs: scene_interactions, scene_data
"""

import json
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field, validator

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.scene_stage3_interactions")


# Pydantic Schemas
class AssetInteraction(BaseModel):
    """Schema for asset interaction"""
    asset_id: str = Field(..., min_length=1, max_length=50)
    interaction_type: str = Field(..., min_length=3, max_length=30)
    trigger: str = Field(..., min_length=5, max_length=100)
    behavior: str = Field(..., min_length=10, max_length=500)


class AnimationStep(BaseModel):
    """Schema for animation step"""
    asset: str = Field(..., min_length=1, max_length=50, description="Asset ID")
    action: str = Field(..., min_length=3, max_length=50)
    duration: int = Field(..., ge=0, le=10000, description="Duration in milliseconds")


class AnimationSequence(BaseModel):
    """Schema for animation sequence"""
    id: str
    sequence: List[AnimationStep] = Field(..., min_items=1, max_items=20)
    total_duration: str = Field(..., pattern=r"^\d+ms$")

    @validator('total_duration')
    def validate_total_duration(cls, v, values):
        """Ensure total_duration matches sum of steps"""
        if 'sequence' in values:
            calculated_total = sum(step.duration for step in values['sequence'])
            declared_total = int(v.replace('ms', ''))
            if abs(calculated_total - declared_total) > 100:  # Allow 100ms tolerance
                logger.warning(
                    f"Total duration mismatch: declared={declared_total}ms, "
                    f"calculated={calculated_total}ms"
                )
        return v


class StateTransition(BaseModel):
    """Schema for state transition"""
    from_state: str
    to_state: str
    trigger: str
    visual_changes: List[str] = Field(..., min_items=1)
    # Hierarchy support fields (optional)
    affected_asset_ids: List[str] = Field(default_factory=list, description="Assets affected by this transition")
    hierarchy_level: Optional[int] = Field(None, description="Hierarchy level this transition affects")
    reveal_children: bool = Field(default=False, description="Whether this transition reveals child assets")


class VisualFlowStep(BaseModel):
    """Schema for visual flow step"""
    step: int = Field(..., ge=0)
    description: str
    assets_involved: List[str] = Field(default_factory=list)


class HierarchyRevealConfig(BaseModel):
    """Schema for hierarchy reveal configuration"""
    parent_asset_id: str = Field(..., description="Parent asset that triggers reveal")
    child_asset_ids: List[str] = Field(..., description="Child assets to reveal")
    reveal_trigger: str = Field(default="complete_parent", description="Trigger type")
    reveal_animation: str = Field(default="fade_in", description="Animation for reveal")


class ModeTransition(BaseModel):
    """Schema for mode transition within a scene"""
    from_mode: str = Field(..., description="Starting interaction mode")
    to_mode: str = Field(..., description="Target interaction mode")
    trigger: str = Field(..., description="Trigger type: all_zones_labeled, score_threshold, time_elapsed, button_click, mode_complete")
    trigger_value: Optional[Any] = Field(None, description="Value for trigger (e.g., score threshold)")
    animation: str = Field(default="fade_transition", description="Transition animation")


class InteractionsOutputSchema(BaseModel):
    """Schema for Stage 3 output"""
    asset_interactions: List[AssetInteraction] = Field(default_factory=list, max_items=50)
    animation_sequences: List[AnimationSequence] = Field(default_factory=list, max_items=30)
    state_transitions: List[StateTransition] = Field(default_factory=list, max_items=20)
    visual_flow: List[VisualFlowStep] = Field(default_factory=list, max_items=30)
    # Hierarchy support (optional)
    hierarchy_reveal_configs: List[HierarchyRevealConfig] = Field(default_factory=list, description="Configs for progressive reveal")
    # Mode transitions for multi-mechanic scenes
    mode_transitions: List[ModeTransition] = Field(default_factory=list, description="Mode transitions for multi-mechanic scenes")


def _build_mechanic_specific_context(
    game_mechanics: List[Dict],
    interaction_design: Dict[str, Any],
    domain_knowledge: Dict[str, Any]
) -> str:
    """Build mechanic-specific context for the prompt to ensure ALL mechanics are implemented."""
    if not game_mechanics:
        return ""

    context_parts = []

    # Check for sequence/order mechanics
    sequence_mechanics = [m for m in game_mechanics if m.get("type", "").lower() in ("order", "sequence", "ordering", "sequencing")]
    drag_drop_mechanics = [m for m in game_mechanics if m.get("type", "").lower() in ("drag_drop", "drag-drop", "label", "labeling")]

    if sequence_mechanics:
        context_parts.append("""
## SEQUENCE/ORDER MECHANIC REQUIRED:
This game includes a SEQUENCE or ORDER mechanic. You MUST include interactions for:

### Sequence Interactions:
1. **Sequence items** - Create draggable items that represent steps in the sequence
2. **Sequence slots** - Create numbered drop zones (1, 2, 3...) for ordering
3. **Order validation** - Check if items are in correct order

### Required Sequence Interactions:
```json
{
    "asset_id": "sequence_slot_1",
    "interaction_type": "drop",
    "trigger": "item_dropped_on_slot",
    "behavior": "Accepts sequence item, validates position, shows number indicator"
}
```

### Sequence State Transitions:
- initial → sequencing: User starts arranging items
- sequencing → sequence_complete: All items in correct order
- sequence_complete → celebration: Show flow animation

### Sequence Animation:
Include an animation that shows the correct flow path when sequence is complete:
```json
{
    "id": "flow_path_animation",
    "sequence": [
        {"asset": "sequence_slot_1", "action": "highlight_flow", "duration": 500},
        {"asset": "flow_arrow_1", "action": "draw_path", "duration": 600},
        {"asset": "sequence_slot_2", "action": "highlight_flow", "duration": 500}
    ],
    "total_duration": "1600ms"
}
```
""")

    # Include animation_config from interaction_design
    animation_config = interaction_design.get("animation_config", {})
    if animation_config:
        context_parts.append(f"""
## DESIGNED ANIMATION CONFIG (from interaction_designer):
Use these animations for feedback:
- On correct: {animation_config.get('on_correct', 'glow')}
- On incorrect: {animation_config.get('on_incorrect', 'shake')}
- On complete: {animation_config.get('on_complete', 'confetti')}
- On hint: {animation_config.get('on_hint', 'pulse')}
""")

    # Include scoring strategy
    scoring_strategy = interaction_design.get("scoring_strategy", {})
    if scoring_strategy:
        context_parts.append(f"""
## DESIGNED SCORING STRATEGY:
- Base points per zone: {scoring_strategy.get('base_points_per_zone', 10)}
- Partial credit: {scoring_strategy.get('partial_credit', True)}
- Hint penalty: {scoring_strategy.get('hint_penalty', 20)}
- Max score: {scoring_strategy.get('max_score', 100)}
""")

    return "\n".join(context_parts)


def _build_domain_context(
    template_type: str,
    canonical_labels: List[str],
    learning_objectives: List[str],
    common_misconceptions: List[str]
) -> str:
    """Build domain-specific context for the prompt."""
    context_parts = []

    if canonical_labels:
        context_parts.append(f"""
## Domain-Specific Context:
- Labels/terms being taught: {', '.join(canonical_labels[:6])}
- Use actual label names in feedback messages (e.g., "Correct! That's the {canonical_labels[0] if canonical_labels else 'part'}")
- Reference specific structures in hint text
""")

    if learning_objectives:
        context_parts.append(f"""
## Learning Objectives to Reference in Feedback:
{json.dumps(learning_objectives[:3], indent=2)}
""")

    if common_misconceptions:
        context_parts.append(f"""
## Common Misconceptions to Address:
When students make errors, provide feedback that addresses these misconceptions:
{json.dumps(common_misconceptions[:3], indent=2)}
""")

    context_parts.append("""
## Interaction Text Guidelines:
- Use actual label names (not generic "correct part")
- Reference learning objectives in hint text
- Address misconceptions in incorrect placement feedback
""")

    return "\n".join(context_parts)


def _generate_hierarchy_reveal_configs(
    hierarchy_info: Dict[str, Any],
    asset_groups: List[Dict]
) -> List[Dict]:
    """Generate hierarchy reveal configs from hierarchy_info when LLM doesn't provide them."""
    if not hierarchy_info or not hierarchy_info.get("is_hierarchical"):
        return []

    reveal_trigger = hierarchy_info.get("reveal_trigger", "complete_parent")

    # If we have asset_groups from Stage 2, use them directly
    if asset_groups:
        return [
            {
                "parent_asset_id": group.get("parent_asset_id"),
                "child_asset_ids": group.get("child_asset_ids", []),
                "reveal_trigger": group.get("reveal_trigger", reveal_trigger),
                "reveal_animation": "fade_in"
            }
            for group in asset_groups
            if group.get("parent_asset_id") and group.get("child_asset_ids")
        ]

    # Otherwise, generate from parent_children mapping
    parent_children = hierarchy_info.get("parent_children", {})
    configs = []

    for parent, children in parent_children.items():
        parent_asset_id = f"label_target_{parent.lower().replace(' ', '_')}"
        child_asset_ids = [f"label_target_{c.lower().replace(' ', '_')}" for c in children]

        configs.append({
            "parent_asset_id": parent_asset_id,
            "child_asset_ids": child_asset_ids,
            "reveal_trigger": reveal_trigger,
            "reveal_animation": "fade_in"
        })

    return configs


def _ensure_hierarchy_state_transitions(
    existing_transitions: List[Dict],
    hierarchy_info: Dict[str, Any],
    asset_groups: List[Dict]
) -> List[Dict]:
    """Ensure required hierarchy state transitions exist."""
    if not hierarchy_info or not hierarchy_info.get("is_hierarchical"):
        return existing_transitions

    reveal_trigger = hierarchy_info.get("reveal_trigger", "complete_parent")
    parent_children = hierarchy_info.get("parent_children", {})

    # Check if we already have hierarchy-related transitions
    has_parent_visible = any(
        t.get("to_state") == "parent_visible" or "parent" in t.get("to_state", "").lower()
        for t in existing_transitions
    )
    has_children_visible = any(
        t.get("reveal_children") or "children" in t.get("to_state", "").lower()
        for t in existing_transitions
    )

    # If both exist, return as-is
    if has_parent_visible and has_children_visible:
        return existing_transitions

    # Add missing hierarchy transitions
    transitions = list(existing_transitions)

    # Add initial → parent_visible if missing
    if not has_parent_visible:
        parent_asset_ids = []
        for parent in parent_children.keys():
            parent_asset_ids.append(f"label_target_{parent.lower().replace(' ', '_')}")

        transitions.insert(0, {
            "from_state": "initial",
            "to_state": "parent_visible",
            "trigger": "game_starts",
            "visual_changes": [
                "Show parent-level labels only",
                "Child labels initially hidden"
            ],
            "affected_asset_ids": parent_asset_ids,
            "hierarchy_level": 1,
            "reveal_children": False
        })

    # Add parent_complete → children_visible for each parent if missing
    if not has_children_visible:
        for parent, children in parent_children.items():
            parent_asset_id = f"label_target_{parent.lower().replace(' ', '_')}"
            child_asset_ids = [f"label_target_{c.lower().replace(' ', '_')}" for c in children]

            # Determine trigger based on reveal_trigger setting
            if reveal_trigger == "complete_parent":
                trigger_text = f"{parent.lower().replace(' ', '_')}_label_correct"
            elif reveal_trigger == "click_expand":
                trigger_text = f"expand_{parent.lower().replace(' ', '_')}_clicked"
            else:  # hover_reveal
                trigger_text = f"hover_{parent.lower().replace(' ', '_')}"

            transitions.append({
                "from_state": f"{parent.lower().replace(' ', '_')}_complete",
                "to_state": f"{parent.lower().replace(' ', '_')}_children_visible",
                "trigger": trigger_text,
                "visual_changes": [
                    f"{parent} shows completion indicator",
                    f"Child labels ({', '.join(children)}) fade in",
                    "New target zones become interactive"
                ],
                "affected_asset_ids": child_asset_ids,
                "hierarchy_level": 2,
                "reveal_children": True
            })

    return transitions


def _generate_mode_transitions(
    game_mechanics: List[Dict],
    scene_structure: Dict[str, Any]
) -> List[Dict]:
    """
    Generate mode transitions for multi-mechanic scenes.

    Common transition patterns:
    - drag_drop -> trace_path: trigger "all_zones_labeled"
    - drag_drop -> sequencing: trigger "score_threshold" (0.8)
    - any -> any: trigger "button_click"
    """
    if not game_mechanics or len(game_mechanics) < 2:
        return []

    # Extract mechanic types
    mechanic_types = []
    for m in game_mechanics:
        mtype = m.get("type", "").lower()
        # Normalize mechanic type names
        if mtype in ("drag_drop", "drag-drop", "label", "labeling"):
            mechanic_types.append("drag_drop")
        elif mtype in ("sequence", "sequencing", "order", "ordering"):
            mechanic_types.append("sequencing")
        elif mtype in ("trace", "trace_path", "tracing"):
            mechanic_types.append("trace_path")
        elif mtype in ("match", "matching"):
            mechanic_types.append("matching")
        elif mtype in ("fill_blank", "fill_in_blank", "fill"):
            mechanic_types.append("fill_blank")
        elif mtype in ("multiple_choice", "mcq"):
            mechanic_types.append("multiple_choice")
        else:
            mechanic_types.append(mtype)

    # Remove duplicates while preserving order
    seen = set()
    unique_mechanics = []
    for m in mechanic_types:
        if m and m not in seen:
            seen.add(m)
            unique_mechanics.append(m)

    if len(unique_mechanics) < 2:
        return []

    # Define transition patterns between mechanics
    transition_patterns = {
        ("drag_drop", "trace_path"): {
            "trigger": "all_zones_labeled",
            "trigger_value": None,
            "animation": "fade_transition"
        },
        ("drag_drop", "sequencing"): {
            "trigger": "score_threshold",
            "trigger_value": 0.8,
            "animation": "slide_left"
        },
        ("sequencing", "trace_path"): {
            "trigger": "mode_complete",
            "trigger_value": None,
            "animation": "fade_transition"
        },
        ("drag_drop", "matching"): {
            "trigger": "score_threshold",
            "trigger_value": 0.7,
            "animation": "fade_transition"
        },
        ("matching", "sequencing"): {
            "trigger": "mode_complete",
            "trigger_value": None,
            "animation": "slide_up"
        },
        ("drag_drop", "fill_blank"): {
            "trigger": "all_zones_labeled",
            "trigger_value": None,
            "animation": "fade_transition"
        },
        ("drag_drop", "multiple_choice"): {
            "trigger": "mode_complete",
            "trigger_value": None,
            "animation": "fade_transition"
        },
    }

    # Generate transitions between consecutive mechanics
    transitions = []
    for i in range(len(unique_mechanics) - 1):
        from_mode = unique_mechanics[i]
        to_mode = unique_mechanics[i + 1]

        # Look up pattern or use default
        pattern = transition_patterns.get((from_mode, to_mode), {
            "trigger": "button_click",
            "trigger_value": None,
            "animation": "fade_transition"
        })

        transitions.append({
            "from_mode": from_mode,
            "to_mode": to_mode,
            "trigger": pattern["trigger"],
            "trigger_value": pattern["trigger_value"],
            "animation": pattern["animation"]
        })

    return transitions


def _build_mode_transition_context(game_mechanics: List[Dict]) -> str:
    """Build context for mode transitions in multi-mechanic scenes."""
    if not game_mechanics or len(game_mechanics) < 2:
        return ""

    mechanic_names = [m.get("type", "unknown") for m in game_mechanics]

    return f"""
## MODE TRANSITIONS (Multi-Mechanic Scene):
This scene has multiple mechanics: {', '.join(mechanic_names)}

You MUST define mode_transitions to switch between these mechanics within the scene.

### Mode Transition Schema:
```json
{{
    "from_mode": "drag_drop",
    "to_mode": "sequencing",
    "trigger": "all_zones_labeled",
    "trigger_value": null,
    "animation": "fade_transition"
}}
```

### Available Triggers:
- **all_zones_labeled**: All drop zones have been filled
- **score_threshold**: Score reaches a value (e.g., 0.8 for 80%)
- **time_elapsed**: After N seconds
- **button_click**: User clicks a "Continue" or "Next Mode" button
- **mode_complete**: Current mode's objective is complete

### Example Mode Transitions:
```json
{{
    "mode_transitions": [
        {{
            "from_mode": "drag_drop",
            "to_mode": "trace_path",
            "trigger": "all_zones_labeled",
            "trigger_value": null,
            "animation": "fade_transition"
        }},
        {{
            "from_mode": "trace_path",
            "to_mode": "sequencing",
            "trigger": "score_threshold",
            "trigger_value": 0.8,
            "animation": "slide_left"
        }}
    ]
}}
```

### Requirements:
- Create a transition for EACH pair of consecutive mechanics
- Choose appropriate triggers based on mechanic type
- Use smooth animations for good UX
"""


def _build_hierarchy_interaction_context(
    hierarchy_info: Optional[Dict[str, Any]],
    asset_groups: List[Dict]
) -> str:
    """Build hierarchy-specific context for interaction generation."""
    if not hierarchy_info or not hierarchy_info.get("is_hierarchical"):
        return ""

    parent_children = hierarchy_info.get("parent_children", {})
    reveal_trigger = hierarchy_info.get("reveal_trigger", "complete_parent")

    # Format asset groups if available
    groups_info = ""
    if asset_groups:
        groups_lines = []
        for group in asset_groups:
            groups_lines.append(f"  - {group.get('group_id')}: parent={group.get('parent_asset_id')}, children={group.get('child_asset_ids')}")
        groups_info = f"""
### Asset Groups from Stage 2:
{chr(10).join(groups_lines)}
"""

    # Map reveal trigger to state transition guidance
    trigger_guidance = {
        "complete_parent": """When the parent label is correctly placed:
  1. Transition from "parent_visible" to "children_visible" state
  2. Reveal child assets with fade-in animation
  3. Update feedback to indicate new targets available""",
        "click_expand": """When user clicks expand button on completed parent:
  1. Toggle children visibility
  2. Use expand/collapse animation
  3. Allow re-collapsing""",
        "hover_reveal": """When user hovers over completed parent:
  1. Temporarily show children
  2. Use quick fade animation
  3. Hide on mouse leave"""
    }

    return f"""
## HIERARCHICAL STATE TRANSITIONS:
This content has parent-child relationships requiring progressive reveal.

### Parent-Children Relationships:
{json.dumps(parent_children, indent=2)}

### Reveal Trigger: {reveal_trigger}
{trigger_guidance.get(reveal_trigger, trigger_guidance["complete_parent"])}
{groups_info}
### Required State Transitions for Hierarchy:

1. **initial → parent_visible**
   - trigger: "game_starts"
   - visual_changes: Show only parent-level assets (hierarchy_level=1)
   - Children start hidden (initially_visible=false)

2. **parent_visible → parent_labeling**
   - trigger: "user_starts_labeling_parent"
   - visual_changes: Parent targets become interactive

3. **parent_labeling → parent_complete**
   - trigger: "parent_label_correct"
   - visual_changes: Parent shows correct indicator
   - reveal_children: true

4. **parent_complete → children_visible**
   - trigger: "{reveal_trigger}"
   - visual_changes: Child assets fade in, become interactive
   - affected_asset_ids: [child asset IDs]
   - hierarchy_level: 2

5. **children_visible → children_labeling**
   - trigger: "user_labels_child"
   - visual_changes: Child targets accept labels

6. **children_labeling → group_complete**
   - trigger: "all_children_correct"
   - visual_changes: Group shows completion indicator

### Hierarchy Reveal Configuration:
For each parent-children group, create a hierarchy_reveal_config:
```json
{{
    "parent_asset_id": "label_target_parent",
    "child_asset_ids": ["label_target_child1", "label_target_child2"],
    "reveal_trigger": "{reveal_trigger}",
    "reveal_animation": "fade_in"
}}
```

### Example Hierarchical State Transitions (Cell with Organelles):
```json
{{
    "state_transitions": [
        {{
            "from_state": "initial",
            "to_state": "parent_visible",
            "trigger": "game_starts",
            "visual_changes": ["Show Cell, Nucleus labels only", "Hide Nucleolus, Chromatin labels"],
            "affected_asset_ids": ["label_target_cell", "label_target_nucleus"],
            "hierarchy_level": 1,
            "reveal_children": false
        }},
        {{
            "from_state": "parent_visible",
            "to_state": "nucleus_children_visible",
            "trigger": "nucleus_label_correct",
            "visual_changes": ["Nucleus shows checkmark", "Nucleolus and Chromatin targets fade in"],
            "affected_asset_ids": ["label_target_nucleolus", "label_target_chromatin"],
            "hierarchy_level": 2,
            "reveal_children": true
        }}
    ],
    "hierarchy_reveal_configs": [
        {{
            "parent_asset_id": "label_target_nucleus",
            "child_asset_ids": ["label_target_nucleolus", "label_target_chromatin"],
            "reveal_trigger": "complete_parent",
            "reveal_animation": "fade_in"
        }}
    ]
}}
```
"""


async def scene_stage3_interactions(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Stage 3: Generate interactions based on assets.

    Inputs: game_plan, template_selection, scene_structure, scene_assets, domain_knowledge, pedagogical_context
    Outputs: scene_interactions, scene_data

    Returns state update with scene_interactions and combined scene_data.
    """
    logger.info("Stage 3: Generating scene interactions")

    # Extract inputs from state
    game_plan = state.get("game_plan", {})
    template_type = state.get("template_selection", {}).get("template_type", "")

    # Extract hierarchy_info from game_plan
    hierarchy_info = game_plan.get("hierarchy_info")

    # Extract domain knowledge for domain-specific interactions
    domain_knowledge = state.get("domain_knowledge", {})
    canonical_labels = domain_knowledge.get("canonical_labels", [])
    pedagogical_context = state.get("pedagogical_context", {})
    learning_objectives = pedagogical_context.get("learning_objectives", [])
    common_misconceptions = pedagogical_context.get("common_misconceptions", [])

    # Extract interaction_design from state (from interaction_designer agent)
    interaction_design = state.get("interaction_design") or {}
    scoring_strategy = interaction_design.get("scoring_strategy", {})
    animation_config = interaction_design.get("animation_config", {})
    feedback_strategy = interaction_design.get("feedback_strategy", {})

    # Get outputs from previous stages
    structure = state.get("scene_structure", {})
    assets = state.get("scene_assets", {})

    # Extract asset_groups from Stage 2 for hierarchy context
    asset_groups = assets.get("asset_groups", [])

    # Extract asset IDs for validation
    required_assets = assets.get("required_assets", [])
    asset_ids = [a.get("id", "") for a in required_assets]
    valid_asset_ids = ", ".join(asset_ids)

    # Build assets summary
    assets_summary = "\n".join([
        f"- {a.get('id', 'unknown')} ({a.get('type', 'component')}): {a.get('description', '')}"
        for a in required_assets
    ])

    # Format game mechanics and feedback
    mechanics_json = json.dumps(game_plan.get("game_mechanics", []), indent=2)
    feedback_json = json.dumps(game_plan.get("feedback_strategy", {}), indent=2)

    # Build prompt for Stage 3
    prompt = f"""Define INTERACTIONS and ANIMATIONS for the scene assets.

## Template Type: {template_type}

## Available Assets from Stage 2:
{assets_summary}

## VALID ASSET IDs (ONLY use these):
{valid_asset_ids}

## Game Mechanics:
{mechanics_json}

## Feedback Strategy:
{feedback_json}
{_build_domain_context(template_type, canonical_labels, learning_objectives, common_misconceptions)}{_build_mechanic_specific_context(game_plan.get("game_mechanics", []), interaction_design, domain_knowledge)}{_build_hierarchy_interaction_context(hierarchy_info, asset_groups)}{_build_mode_transition_context(game_plan.get("game_mechanics", []))}
## Your Task (Stage 3 - Interactions & Animations ONLY):

Define how the assets interact and animate:

### 1. Asset Interactions
How each asset responds to triggers:
- **asset_id**: MUST be from the list above
- **interaction_type**: "click", "drag", "drop", "hover", "input", "highlight", "update"
- **trigger**: When this interaction happens
- **behavior**: Describe the visual response

### 2. Animation Sequences
Coordinated animations that play together:
- **id**: Sequence identifier
- **sequence**: Array of steps (asset, action, duration in ms)
- **total_duration**: Sum with "ms"

### 3. State Transitions
How the game progresses:
- **from_state**: Starting state
- **to_state**: Ending state
- **trigger**: What causes transition
- **visual_changes**: Array of visual changes
- **affected_asset_ids**: (optional) Assets affected by this transition
- **hierarchy_level**: (optional) Which hierarchy level is affected (1 or 2)
- **reveal_children**: (optional) true if this transition reveals child assets

### 4. Visual Flow
Step-by-step progression:
- **step**: Step number
- **description**: What happens
- **assets_involved**: Array of asset IDs

## Example 1: INTERACTIVE_DIAGRAM Interactions (Flower Parts)

```json
{{
    "asset_interactions": [
        {{
            "asset_id": "label_options_container",
            "interaction_type": "drag",
            "trigger": "user_starts_drag",
            "behavior": "Label becomes semi-transparent, follows cursor, highlights compatible drop zones"
        }},
        {{
            "asset_id": "label_target_petal",
            "interaction_type": "drop",
            "trigger": "label_dropped_on_target",
            "behavior": "If correct label: snaps to position, displays checkmark. If wrong: bounces back to origin, shakes"
        }},
        {{
            "asset_id": "label_target_stamen",
            "interaction_type": "drop",
            "trigger": "label_dropped_on_target",
            "behavior": "Validates label correctness, provides immediate visual feedback"
        }},
        {{
            "asset_id": "label_target_pistil",
            "interaction_type": "drop",
            "trigger": "label_dropped_on_target",
            "behavior": "Validates label correctness, provides immediate visual feedback"
        }},
        {{
            "asset_id": "label_target_sepal",
            "interaction_type": "drop",
            "trigger": "label_dropped_on_target",
            "behavior": "Validates label correctness, provides immediate visual feedback"
        }},
        {{
            "asset_id": "check_answer_button",
            "interaction_type": "click",
            "trigger": "user_clicks_check",
            "behavior": "Validates all placements, shows overall feedback, updates score"
        }},
        {{
            "asset_id": "hint_button",
            "interaction_type": "click",
            "trigger": "user_requests_hint",
            "behavior": "Highlights next unlabeled target zone, pulses gently, decrements hint counter"
        }},
        {{
            "asset_id": "reset_button",
            "interaction_type": "click",
            "trigger": "user_resets_game",
            "behavior": "All labels return to starting positions, score resets, confirmation dialog appears"
        }},
        {{
            "asset_id": "feedback_message",
            "interaction_type": "update",
            "trigger": "validation_complete",
            "behavior": "Displays colored message (green for correct, red for incorrect), shows score and completion percentage"
        }}
    ],
    "animation_sequences": [
        {{
            "id": "correct_label_placement",
            "sequence": [
                {{"asset": "label_target_petal", "action": "highlight_green", "duration": 200}},
                {{"asset": "label_target_petal", "action": "scale_pulse", "duration": 300}},
                {{"asset": "feedback_message", "action": "show_checkmark", "duration": 400}}
            ],
            "total_duration": "900ms"
        }},
        {{
            "id": "incorrect_label_placement",
            "sequence": [
                {{"asset": "label_target_petal", "action": "shake_horizontal", "duration": 300}},
                {{"asset": "label_options_container", "action": "return_label", "duration": 400}},
                {{"asset": "feedback_message", "action": "show_error", "duration": 300}}
            ],
            "total_duration": "1000ms"
        }},
        {{
            "id": "hint_reveal",
            "sequence": [
                {{"asset": "label_target_stamen", "action": "pulse_glow", "duration": 500}},
                {{"asset": "label_target_stamen", "action": "draw_arrow", "duration": 600}}
            ],
            "total_duration": "1100ms"
        }},
        {{
            "id": "all_correct_celebration",
            "sequence": [
                {{"asset": "flower_diagram", "action": "glow_border", "duration": 500}},
                {{"asset": "feedback_message", "action": "show_success_banner", "duration": 600}},
                {{"asset": "label_target_petal", "action": "sparkle", "duration": 400}},
                {{"asset": "label_target_stamen", "action": "sparkle", "duration": 400}},
                {{"asset": "label_target_pistil", "action": "sparkle", "duration": 400}},
                {{"asset": "label_target_sepal", "action": "sparkle", "duration": 400}}
            ],
            "total_duration": "2200ms"
        }}
    ],
    "state_transitions": [
        {{
            "from_state": "initial",
            "to_state": "labeling",
            "trigger": "game_starts",
            "visual_changes": [
                "flower_diagram displays with empty target zones",
                "label_options_container shows all available labels",
                "feedback_message shows instructions"
            ]
        }},
        {{
            "from_state": "labeling",
            "to_state": "partial_complete",
            "trigger": "first_correct_placement",
            "visual_changes": [
                "label snaps to target zone",
                "target zone shows checkmark",
                "feedback_message updates progress"
            ]
        }},
        {{
            "from_state": "partial_complete",
            "to_state": "validation",
            "trigger": "user_clicks_check_answer",
            "visual_changes": [
                "all placements highlighted (green/red)",
                "feedback_message shows detailed results",
                "score updates in feedback_region"
            ]
        }},
        {{
            "from_state": "validation",
            "to_state": "complete",
            "trigger": "all_labels_correct",
            "visual_changes": [
                "celebration animation plays",
                "feedback_message shows completion banner",
                "check_answer_button disabled"
            ]
        }},
        {{
            "from_state": "validation",
            "to_state": "labeling",
            "trigger": "incorrect_placements_exist",
            "visual_changes": [
                "incorrect labels return to origin",
                "feedback_message shows retry message",
                "target zones pulse for unlabeled parts"
            ]
        }}
    ],
    "visual_flow": [
        {{
            "step": 1,
            "description": "Student sees flower diagram with 4 empty label zones and 4 label options on the side",
            "assets_involved": ["flower_diagram", "label_options_container"]
        }},
        {{
            "step": 2,
            "description": "Student drags 'Petal' label toward flower, target zones highlight",
            "assets_involved": ["label_options_container", "label_target_petal", "label_target_stamen", "label_target_pistil", "label_target_sepal"]
        }},
        {{
            "step": 3,
            "description": "Student drops 'Petal' on correct zone, label snaps into place with green checkmark",
            "assets_involved": ["label_target_petal", "feedback_message"]
        }},
        {{
            "step": 4,
            "description": "Student continues labeling other parts (Stamen, Pistil, Sepal)",
            "assets_involved": ["label_target_stamen", "label_target_pistil", "label_target_sepal"]
        }},
        {{
            "step": 5,
            "description": "Student clicks 'Check Answer' button to validate all placements",
            "assets_involved": ["check_answer_button", "feedback_message"]
        }},
        {{
            "step": 6,
            "description": "All correct: celebration animation plays, success message displays",
            "assets_involved": ["flower_diagram", "feedback_message", "label_target_petal", "label_target_stamen", "label_target_pistil", "label_target_sepal"]
        }}
    ]
}}
```

## Example 2: STATE_TRACER_CODE Interactions

```json
{{
    "asset_interactions": [
        {{
            "asset_id": "code_editor",
            "interaction_type": "line_highlight",
            "trigger": "step_execution",
            "behavior": "Current line pulses yellow, previous line returns to normal"
        }},
        {{
            "asset_id": "variable_panel",
            "interaction_type": "value_update",
            "trigger": "variable_change",
            "behavior": "Variable card flips, shows new value"
        }},
        {{
            "asset_id": "step_controls",
            "interaction_type": "click",
            "trigger": "user_clicks_next",
            "behavior": "Advances to next step, updates visuals"
        }}
    ],
    "animation_sequences": [
        {{
            "id": "step_execution",
            "sequence": [
                {{"asset": "code_editor", "action": "highlight_line", "duration": 300}},
                {{"asset": "variable_panel", "action": "update_values", "duration": 500}}
            ],
            "total_duration": "800ms"
        }}
    ],
    "state_transitions": [
        {{
            "from_state": "initial",
            "to_state": "first_step",
            "trigger": "user_clicks_next",
            "visual_changes": ["code highlights line 1", "variables appear"]
        }}
    ],
    "visual_flow": [
        {{
            "step": 1,
            "description": "User sees code and clicks Next",
            "assets_involved": ["code_editor", "step_controls"]
        }}
    ]
}}
```

CRITICAL RULES:
- ONLY reference asset IDs from this list: {valid_asset_ids}
- For INTERACTIVE_DIAGRAM: Focus on drag-drop interactions, label validation, feedback
- For STATE_TRACER_CODE: Focus on step navigation, code highlighting, variable updates
- All durations must be numbers (milliseconds)
- State transitions must be logical and sequential
{"- For HIERARCHICAL content: Include state transitions for progressive reveal (parent_visible → children_visible)" if hierarchy_info and hierarchy_info.get("is_hierarchical") else ""}
{"- Create hierarchy_reveal_configs for each parent-children group" if hierarchy_info and hierarchy_info.get("is_hierarchical") else ""}
{"- For MULTI-MECHANIC scenes: Include mode_transitions to define how mechanics switch within the scene" if len(game_plan.get("game_mechanics", [])) > 1 else ""}

Return ONLY valid JSON with:
- asset_interactions (array)
- animation_sequences (array)
- state_transitions (array with hierarchy fields if applicable)
- visual_flow (array)
- hierarchy_reveal_configs (array of reveal configs, empty if not hierarchical)
- mode_transitions (array of mode transitions for multi-mechanic scenes, empty if single mechanic)
"""

    # Extract game mechanics for mode transition generation
    game_mechanics = game_plan.get("game_mechanics", [])

    # Call LLM for Stage 3
    llm = get_llm_service()
    used_fallback = False

    try:
        result = await llm.generate_json_for_agent(
            agent_name="scene_stage3_interactions",
            prompt=prompt,
            schema_hint="JSON with asset_interactions[], animation_sequences[], state_transitions[], visual_flow[], hierarchy_reveal_configs[], mode_transitions[]"
        )

        # Ensure state_transitions have hierarchy fields with defaults
        for transition in result.get("state_transitions", []):
            if "affected_asset_ids" not in transition:
                transition["affected_asset_ids"] = []
            if "hierarchy_level" not in transition:
                transition["hierarchy_level"] = None
            if "reveal_children" not in transition:
                transition["reveal_children"] = False

        # Ensure hierarchy_reveal_configs exists
        if "hierarchy_reveal_configs" not in result:
            result["hierarchy_reveal_configs"] = []

        # If hierarchy_info was provided but LLM didn't create hierarchy_reveal_configs, generate them
        if hierarchy_info and hierarchy_info.get("is_hierarchical") and not result.get("hierarchy_reveal_configs"):
            result["hierarchy_reveal_configs"] = _generate_hierarchy_reveal_configs(
                hierarchy_info, asset_groups
            )

        # If hierarchical, ensure we have appropriate state transitions
        if hierarchy_info and hierarchy_info.get("is_hierarchical"):
            result["state_transitions"] = _ensure_hierarchy_state_transitions(
                result.get("state_transitions", []),
                hierarchy_info,
                asset_groups
            )

        # Ensure mode_transitions exists
        if "mode_transitions" not in result:
            result["mode_transitions"] = []

        # If multi-mechanic but LLM didn't create mode_transitions, generate them
        if len(game_mechanics) > 1 and not result.get("mode_transitions"):
            result["mode_transitions"] = _generate_mode_transitions(
                game_mechanics, structure
            )

        # Validate LLM output against Pydantic schema
        try:
            InteractionsOutputSchema(**result)
        except Exception as val_err:
            logger.warning(f"Stage 3 Pydantic validation warning: {val_err}")

        logger.info(
            f"Stage 3 complete: {len(result.get('asset_interactions', []))} interactions, "
            f"{len(result.get('animation_sequences', []))} animations, "
            f"{len(result.get('hierarchy_reveal_configs', []))} reveal configs, "
            f"{len(result.get('mode_transitions', []))} mode transitions"
        )

    except Exception as e:
        logger.error(f"Stage 3 failed: {e}")
        used_fallback = True
        # Return minimal interactions with hierarchy and mode transition support
        result = {
            "asset_interactions": [],
            "animation_sequences": [],
            "state_transitions": [],
            "visual_flow": [],
            "hierarchy_reveal_configs": [],
            "mode_transitions": []
        }

        # If hierarchical, add basic hierarchy transitions and configs even in fallback
        if hierarchy_info and hierarchy_info.get("is_hierarchical"):
            result["hierarchy_reveal_configs"] = _generate_hierarchy_reveal_configs(
                hierarchy_info, asset_groups
            )
            result["state_transitions"] = _ensure_hierarchy_state_transitions(
                [], hierarchy_info, asset_groups
            )

        # If multi-mechanic, add mode transitions even in fallback
        if len(game_mechanics) > 1:
            result["mode_transitions"] = _generate_mode_transitions(
                game_mechanics, structure
            )

    # Track metrics if instrumentation context available
    if ctx:
        if used_fallback:
            ctx.set_fallback_used("LLM generation failed, using fallback interactions")

    # Combine all three stages into scene_data for compatibility with existing pipeline
    scene_data = {
        "structure": structure,
        "assets": assets,
        "interactions": result,
        # Include direct fields for backward compatibility
        "visual_theme": structure.get("visual_theme", "educational"),
        "scene_title": structure.get("scene_title", "Interactive Scene"),
        "layout_type": structure.get("layout_type", "center_focus"),
        "regions": structure.get("regions", []),
        "required_assets": assets.get("required_assets", []),
        "layout_specification": assets.get("layout_specification", {}),
        "asset_groups": assets.get("asset_groups", []),
        "asset_interactions": result.get("asset_interactions", []),
        "animation_sequences": result.get("animation_sequences", []),
        "state_transitions": result.get("state_transitions", []),
        "visual_flow": result.get("visual_flow", []),
        "hierarchy_reveal_configs": result.get("hierarchy_reveal_configs", []),
        "mode_transitions": result.get("mode_transitions", []),
        # Include hierarchy metadata from structure
        "hierarchy_metadata": structure.get("hierarchy_metadata")
    }

    return {
        "scene_interactions": result,
        "scene_data": scene_data
    }


async def validate_interactions(
    interactions: Dict[str, Any],
    assets: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate Stage 3 interactions output against Stage 2 assets.

    Progressive validation: Ensures all asset_id references are valid.

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "validated_interactions": Dict (if valid)
        }
    """
    logger.info("Validating Stage 3 interactions")

    errors = []
    warnings = []

    try:
        # 1. Pydantic validation
        validated = InteractionsOutputSchema(**interactions)

        # 2. Progressive validation: Check all asset IDs are valid
        valid_asset_ids = {a['id'] for a in assets.get('required_assets', [])}

        # Check asset_interactions
        for interaction in interactions.get('asset_interactions', []):
            asset_id = interaction.get('asset_id', '')
            if asset_id not in valid_asset_ids:
                errors.append(
                    f"Interaction references invalid asset '{asset_id}'. "
                    f"Valid assets: {', '.join(sorted(valid_asset_ids))}"
                )

        # Check animation_sequences
        for sequence in interactions.get('animation_sequences', []):
            for step in sequence.get('sequence', []):
                asset_id = step.get('asset', '')
                if asset_id not in valid_asset_ids:
                    errors.append(
                        f"Animation '{sequence.get('id')}' references invalid asset '{asset_id}'"
                    )

        # Check visual_flow
        for flow_step in interactions.get('visual_flow', []):
            for asset_id in flow_step.get('assets_involved', []):
                if asset_id not in valid_asset_ids:
                    errors.append(
                        f"Visual flow step {flow_step.get('step')} references invalid asset '{asset_id}'"
                    )

        # 3. Ghost component detection (hallucinated assets)
        all_referenced_assets = set()

        for interaction in interactions.get('asset_interactions', []):
            all_referenced_assets.add(interaction.get('asset_id', ''))

        for sequence in interactions.get('animation_sequences', []):
            for step in sequence.get('sequence', []):
                all_referenced_assets.add(step.get('asset', ''))

        ghost_assets = all_referenced_assets - valid_asset_ids
        if ghost_assets:
            errors.append(
                f"Ghost components detected (hallucinated assets): {', '.join(ghost_assets)}"
            )

        # 4. Warnings
        if len(interactions.get('asset_interactions', [])) == 0:
            warnings.append("No asset interactions defined")

        if len(interactions.get('animation_sequences', [])) == 0:
            warnings.append("No animation sequences defined")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_interactions": interactions if len(errors) == 0 else None
        }

    except Exception as e:
        logger.error(f"Interactions validation failed: {e}")
        errors.append(f"Validation error: {str(e)}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "validated_interactions": None
        }


def create_fallback_interactions(
    hierarchy_info: Optional[Dict[str, Any]] = None,
    asset_groups: Optional[List[Dict]] = None,
    game_mechanics: Optional[List[Dict]] = None,
    scene_structure: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create minimal valid interactions when Stage 3 fails"""

    result = {
        "asset_interactions": [],
        "animation_sequences": [],
        "state_transitions": [],
        "visual_flow": [],
        "hierarchy_reveal_configs": [],
        "mode_transitions": []
    }

    # If hierarchical, add basic hierarchy transitions and configs
    if hierarchy_info and hierarchy_info.get("is_hierarchical"):
        result["hierarchy_reveal_configs"] = _generate_hierarchy_reveal_configs(
            hierarchy_info, asset_groups or []
        )
        result["state_transitions"] = _ensure_hierarchy_state_transitions(
            [], hierarchy_info, asset_groups or []
        )

    # If multi-mechanic, add mode transitions
    if game_mechanics and len(game_mechanics) > 1:
        result["mode_transitions"] = _generate_mode_transitions(
            game_mechanics, scene_structure or {}
        )

    return result