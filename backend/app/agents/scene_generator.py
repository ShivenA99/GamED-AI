"""
Scene Generator Agent

Plans visual assets, interactions, and scene flow for game generation.
Replaces narrative/story generation with asset-focused scene planning.

Outputs:
- Visual theme/metaphor (for asset design, minimal context)
- Required assets (images, animations, UI components)
- Asset interactions and behaviors
- Layout and visual flow
- Animation sequences
- State transitions
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState, SceneData
from app.services.llm_service import get_llm_service
from app.agents.schemas.stages import get_scene_data_schema
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.scene_generator")


SCENE_GENERATOR_PROMPT = """You are an expert game scene designer. Plan the visual assets, interactions, and scene flow for an interactive learning game.

## Question to Visualize:
{question_text}

## Answer Options:
{question_options}

## Pedagogical Context:
- Bloom's Level: {blooms_level}
- Subject: {subject}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}
- Key Concepts: {key_concepts}

## Game Template: {template_type}
## Game Mechanics: {game_mechanics}

## Few-Shot Example: STATE_TRACER_CODE for Binary Search

**Question**: "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13]."

**Scene Plan**:
```json
{{
    "visual_theme": "detective",
    "scene_title": "Binary Search Detective",
    "minimal_context": "You're a code detective tracing through a binary search algorithm to find the target number 7 in a sorted array.",
    "required_assets": [
        {{
            "id": "code_editor",
            "type": "component",
            "description": "Code editor panel showing the binary search function",
            "specifications": {{
                "width": 60,
                "height": 60,
                "features": ["syntax_highlighting", "line_numbers", "line_highlighting"],
                "position": "left"
            }}
        }},
        {{
            "id": "variable_panel",
            "type": "component",
            "description": "Panel showing current variable values (low, high, mid, arr[mid])",
            "specifications": {{
                "width": 35,
                "height": 30,
                "features": ["real_time_updates", "value_cards", "highlight_on_change"],
                "position": "right_top"
            }}
        }},
        {{
            "id": "array_visualization",
            "type": "component",
            "description": "Visual array with indices, highlighting current search range",
            "specifications": {{
                "width": 35,
                "height": 25,
                "features": ["index_labels", "range_highlighting", "target_highlighting"],
                "position": "right_middle"
            }}
        }},
        {{
            "id": "step_controls",
            "type": "component",
            "description": "Buttons: Previous Step, Next Step, Play/Pause, Reset",
            "specifications": {{
                "width": 100,
                "height": 10,
                "features": ["step_navigation", "auto_play", "reset"],
                "position": "bottom"
            }}
        }},
        {{
            "id": "line_highlight_animation",
            "type": "animation",
            "description": "Pulsing yellow glow on current executing line",
            "specifications": {{
                "duration": "500ms",
                "effect": "pulse_glow",
                "color": "#FFD700"
            }}
        }},
        {{
            "id": "variable_update_animation",
            "type": "animation",
            "description": "Variable card flips to reveal new value, old value fades",
            "specifications": {{
                "duration": "800ms",
                "effect": "flip_fade",
                "easing": "ease-in-out"
            }}
        }},
        {{
            "id": "array_range_highlight",
            "type": "animation",
            "description": "Search range (low to high) highlights with gradient",
            "specifications": {{
                "duration": "600ms",
                "effect": "gradient_highlight",
                "color_range": ["#4A90E2", "#7B68EE"]
            }}
        }}
    ],
    "asset_interactions": [
        {{
            "asset_id": "code_editor",
            "interaction_type": "line_highlight",
            "trigger": "step_execution",
            "behavior": "Current executing line pulses yellow, previous line returns to normal"
        }},
        {{
            "asset_id": "variable_panel",
            "interaction_type": "value_update",
            "trigger": "variable_change",
            "behavior": "Variable card flips, shows new value, old value fades with strikethrough"
        }},
        {{
            "asset_id": "array_visualization",
            "interaction_type": "range_update",
            "trigger": "search_space_change",
            "behavior": "Elements outside search range fade, range highlights with gradient"
        }},
        {{
            "asset_id": "step_controls",
            "interaction_type": "navigation",
            "trigger": "user_click",
            "behavior": "Advances to next step, updates all visual components, disables at end"
        }}
    ],
    "layout_specification": {{
        "layout_type": "split_panel",
        "panels": [
            {{
                "id": "main_panel",
                "type": "code_editor",
                "position": {{"x": 0, "y": 0, "width": 60, "height": 100}},
                "z_index": 1
            }},
            {{
                "id": "sidebar",
                "type": "stack",
                "position": {{"x": 60, "y": 0, "width": 40, "height": 100}},
                "children": [
                    {{"id": "variable_panel", "height": 50}},
                    {{"id": "array_visualization", "height": 50}}
                ],
                "z_index": 1
            }},
            {{
                "id": "controls",
                "type": "toolbar",
                "position": {{"x": 0, "y": 90, "width": 100, "height": 10}},
                "z_index": 10
            }}
        ],
        "responsive_breakpoints": {{
            "mobile": "stack_vertically",
            "tablet": "reduce_sidebar_width",
            "desktop": "current_layout"
        }}
    }},
    "animation_sequences": [
        {{
            "id": "step_execution",
            "sequence": [
                {{"asset": "code_editor", "action": "highlight_line", "line": "current", "duration": 300}},
                {{"asset": "variable_panel", "action": "update_values", "duration": 500}},
                {{"asset": "array_visualization", "action": "update_range", "duration": 400}},
                {{"asset": "code_editor", "action": "move_to_next_line", "duration": 200}}
            ],
            "total_duration": "1400ms"
        }},
        {{
            "id": "variable_change",
            "sequence": [
                {{"asset": "variable_panel", "action": "fade_old_value", "duration": 200}},
                {{"asset": "variable_panel", "action": "flip_card", "duration": 300}},
                {{"asset": "variable_panel", "action": "reveal_new_value", "duration": 300}}
            ],
            "total_duration": "800ms"
        }},
        {{
            "id": "search_complete",
            "sequence": [
                {{"asset": "code_editor", "action": "highlight_all_lines", "duration": 500}},
                {{"asset": "array_visualization", "action": "highlight_target", "duration": 400}},
                {{"asset": "variable_panel", "action": "celebrate_result", "duration": 600}}
            ],
            "total_duration": "1500ms"
        }}
    ],
    "state_transitions": [
        {{
            "from_state": "initial",
            "to_state": "first_step",
            "trigger": "user_clicks_next",
            "visual_changes": [
                "code_editor highlights line 2",
                "variable_panel shows low=0",
                "array_visualization shows full array"
            ]
        }},
        {{
            "from_state": "mid_calculation",
            "to_state": "comparison",
            "trigger": "step_complete",
            "visual_changes": [
                "code_editor highlights comparison line",
                "variable_panel shows mid value",
                "array_visualization highlights arr[mid]"
            ]
        }},
        {{
            "from_state": "comparison",
            "to_state": "pointer_update",
            "trigger": "comparison_result",
            "visual_changes": [
                "variable_panel updates low or high",
                "array_visualization updates search range",
                "code_editor moves to update line"
            ]
        }},
        {{
            "from_state": "searching",
            "to_state": "found",
            "trigger": "target_matched",
            "visual_changes": [
                "code_editor highlights return line",
                "array_visualization highlights target element",
                "variable_panel shows return value",
                "celebration animation plays"
            ]
        }}
    ],
    "visual_flow": [
        {{
            "step": 0,
            "description": "Initial state: Show code editor with all code visible, empty variable panel, full array visualization",
            "assets_active": ["code_editor", "array_visualization"],
            "user_action": "Click 'Next Step' to begin"
        }},
        {{
            "step": 1,
            "description": "Initialize low: Highlight line 2, show low=0 in variable panel",
            "assets_active": ["code_editor", "variable_panel"],
            "animation": "line_highlight_animation"
        }},
        {{
            "step": 2,
            "description": "Initialize high: Highlight line 3, show high=6 in variable panel",
            "assets_active": ["code_editor", "variable_panel"],
            "animation": "line_highlight_animation"
        }},
        {{
            "step": 3,
            "description": "Enter loop: Highlight while condition, show search range in array visualization",
            "assets_active": ["code_editor", "array_visualization"],
            "animation": "array_range_highlight"
        }},
        {{
            "step": 4,
            "description": "Calculate mid: Highlight calculation line, show mid=3, highlight arr[3] in array",
            "assets_active": ["code_editor", "variable_panel", "array_visualization"],
            "animation": "variable_update_animation"
        }},
        {{
            "step": 5,
            "description": "Compare: Highlight comparison line, show arr[mid]=7, compare with target",
            "assets_active": ["code_editor", "variable_panel"],
            "animation": "line_highlight_animation"
        }},
        {{
            "step": 6,
            "description": "Found: Highlight return line, show return value, celebrate",
            "assets_active": ["code_editor", "variable_panel", "array_visualization"],
            "animation": "search_complete"
        }}
    ]
}}
```

## Your Task:
Plan a scene that:
1. Identifies all visual assets needed for the template
2. Specifies how assets interact with user actions
3. Defines layout and positioning
4. Plans animation sequences for smooth transitions
5. Maps state transitions during gameplay
6. Creates visual flow that guides learners step-by-step
7. Uses visual_theme for minimal context (1-2 sentences), NOT full narrative

## Numeric Constraints (IMPORTANT)
- All size/position values must be numbers (no strings).
- Use 0-100 numeric scale for width/height/x/y values.
- DO NOT use `%`, `px`, or `calc(...)` anywhere in JSON.

## Response Format (JSON):
{{
    "visual_theme": "<theme for asset design, e.g., detective, laboratory, space>",
    "scene_title": "<descriptive title>",
    "minimal_context": "<1-2 sentences setting visual context, no story>",
    "required_assets": [
        {{
            "id": "<asset_id>",
            "type": "<component|animation|image|ui_element>",
            "description": "<what this asset is>",
            "specifications": {{
                "width": <number 0-100>,
                "height": <number 0-100>,
                "features": ["<feature1>", "<feature2>"],
                "position": "<where it goes>"
            }}
        }}
    ],
    "asset_interactions": [
        {{
            "asset_id": "<which asset>",
            "interaction_type": "<click|hover|step|auto>",
            "trigger": "<what causes interaction>",
            "behavior": "<what happens>"
        }}
    ],
    "layout_specification": {{
        "layout_type": "<split_panel|grid|stack|custom>",
        "panels": [
            {{
                "id": "<panel_id>",
                "type": "<component_type>",
                "position": {{"x": <number 0-100>, "y": <number 0-100>, "width": <number 0-100>, "height": <number 0-100>}},
                "z_index": <number>
            }}
        ]
    }},
    "animation_sequences": [
        {{
            "id": "<sequence_id>",
            "sequence": [
                {{"asset": "<asset_id>", "action": "<action>", "duration": <ms>}}
            ],
            "total_duration": "<duration>"
        }}
    ],
    "state_transitions": [
        {{
            "from_state": "<state_name>",
            "to_state": "<state_name>",
            "trigger": "<what triggers transition>",
            "visual_changes": ["<change1>", "<change2>"]
        }}
    ],
    "visual_flow": [
        {{
            "step": <number>,
            "description": "<what happens visually>",
            "assets_active": ["<asset1>", "<asset2>"],
            "animation": "<animation_id>"
        }}
    ]
}}

Focus on VISUAL ASSETS and INTERACTIONS, not narrative. Respond with ONLY valid JSON."""


async def scene_generator_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> AgentState:
    """
    Scene Generator Agent

    Plans visual assets, interactions, and scene flow based on
    game plan and template selection.

    Args:
        state: Current agent state with game_plan and template_selection

    Returns:
        Updated state with scene_data populated
    """
    logger.info(f"SceneGenerator: Processing question {state.get('question_id', 'unknown')}")

    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    ped_context = state.get("pedagogical_context", {})
    game_plan = state.get("game_plan", {})
    template_selection = state.get("template_selection", {})

    template_type = template_selection.get("template_type", "STATE_TRACER_CODE")

    if not question_text:
        logger.error("SceneGenerator: No question text")
        return {
            **state,
            "current_agent": "scene_generator",
            "error_message": "No question text for scene planning"
        }

    # Build prompt
    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"
    game_mechanics_str = json.dumps(game_plan.get("game_mechanics", []), indent=2)

    prev_errors = state.get("current_validation_errors", [])
    error_context = "\n".join(f"- {err}" for err in prev_errors) if prev_errors else "None"
    prompt = SCENE_GENERATOR_PROMPT.format(
        question_text=question_text,
        question_options=options_str,
        blooms_level=ped_context.get("blooms_level", "understand"),
        subject=ped_context.get("subject", "General"),
        difficulty=ped_context.get("difficulty", "intermediate"),
        learning_objectives=json.dumps(ped_context.get("learning_objectives", [])),
        key_concepts=json.dumps(ped_context.get("key_concepts", [])),
        template_type=template_type,
        game_mechanics=game_mechanics_str
    )
    if prev_errors:
        prompt += f"\n\n## Previous Validation Errors (fix these):\n{error_context}"

    try:
        llm = get_llm_service()
        # Use agent-specific model configuration
        result = await llm.generate_json_for_agent(
            agent_name="scene_generator",
            prompt=prompt,
            schema_hint="SceneData JSON with required_assets, asset_interactions, layout_specification, animation_sequences",
            json_schema=get_scene_data_schema()
        )

        # Extract LLM metrics from the result for instrumentation
        llm_metrics = result.pop("_llm_metrics", None) if isinstance(result, dict) else None
        if llm_metrics and ctx:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms")
            )

        # Normalize and validate result
        scene_data = _normalize_scene_data(result, template_type)

        logger.info(
            f"SceneGenerator: Created scene '{scene_data['scene_title']}' "
            f"with {len(scene_data['required_assets'])} assets, "
            f"{len(scene_data['animation_sequences'])} animation sequences"
        )

        return {
            **state,
            "scene_data": scene_data,
            "current_agent": "scene_generator"
        }

    except Exception as e:
        logger.error(f"SceneGenerator: LLM call failed: {e}", exc_info=True)

        # Return fallback scene
        fallback_scene = _create_fallback_scene(template_type, game_plan, ped_context)

        return {
            **state,
            "scene_data": fallback_scene,
            "current_agent": "scene_generator",
            "error_message": f"SceneGenerator fallback: {str(e)}"
        }


def _normalize_scene_data(result: Dict[str, Any], template_type: str) -> SceneData:
    """Normalize and validate the LLM response into SceneData"""

    # Ensure required fields
    visual_theme = result.get("visual_theme", "educational")
    scene_title = result.get("scene_title", "Interactive Learning Scene")
    minimal_context = result.get("minimal_context", "")

    # Normalize assets
    required_assets = result.get("required_assets", [])
    if not required_assets:
        # Create default assets based on template
        required_assets = _get_default_assets(template_type)

    # Normalize interactions
    asset_interactions = result.get("asset_interactions", [])

    # Normalize layout
    layout_specification = result.get("layout_specification", {
        "layout_type": "split_panel",
        "panels": []
    })

    # Normalize animations
    animation_sequences = result.get("animation_sequences", [])

    # Normalize state transitions
    state_transitions = result.get("state_transitions", [])

    # Normalize visual flow
    visual_flow = result.get("visual_flow", [])

    return {
        "visual_theme": visual_theme,
        "scene_title": scene_title,
        "minimal_context": minimal_context,
        "required_assets": required_assets,
        "asset_interactions": asset_interactions,
        "layout_specification": layout_specification,
        "animation_sequences": animation_sequences,
        "state_transitions": state_transitions,
        "visual_flow": visual_flow
    }


def _get_default_assets(template_type: str) -> List[Dict[str, Any]]:
    """Get default assets for a template type"""
    if template_type == "STATE_TRACER_CODE":
        return [
            {
                "id": "code_editor",
                "type": "component",
                "description": "Code editor with syntax highlighting",
                "specifications": {"width": "60%", "height": "400px"}
            },
            {
                "id": "variable_panel",
                "type": "component",
                "description": "Variable value tracker",
                "specifications": {"width": "35%", "height": "200px"}
            },
            {
                "id": "step_controls",
                "type": "component",
                "description": "Step navigation buttons",
                "specifications": {"width": "100%", "height": "50px"}
            }
        ]
    else:
        return [
            {
                "id": "main_canvas",
                "type": "component",
                "description": "Main interactive canvas",
                "specifications": {"width": "100%", "height": "500px"}
            }
        ]


def _create_fallback_scene(
    template_type: str,
    game_plan: Dict[str, Any],
    ped_context: Dict[str, Any]
) -> SceneData:
    """Create a fallback scene when LLM fails"""

    subject = ped_context.get("subject", "General").lower()
    
    # Choose theme based on subject
    if "computer" in subject or "programming" in subject:
        visual_theme = "detective"
        minimal_context = "Trace through the code step-by-step to understand how it works."
    elif "science" in subject:
        visual_theme = "laboratory"
        minimal_context = "Explore the concept through interactive experimentation."
    else:
        visual_theme = "educational"
        minimal_context = "Learn through interactive exploration."

    return {
        "visual_theme": visual_theme,
        "scene_title": f"Interactive {template_type} Scene",
        "minimal_context": minimal_context,
        "required_assets": _get_default_assets(template_type),
        "asset_interactions": [],
        "layout_specification": {
            "layout_type": "split_panel",
            "panels": []
        },
        "animation_sequences": [],
        "state_transitions": [],
        "visual_flow": []
    }


# Validator for scene data
async def validate_scene_data(scene: SceneData) -> Dict[str, Any]:
    """
    Validate the scene data.

    Returns:
        Dict with 'valid' bool and 'errors' list
    """
    errors = []

    # Required fields
    if not scene.get("visual_theme"):
        errors.append("Missing visual_theme")

    if not scene.get("required_assets"):
        errors.append("Missing required_assets")

    if not scene.get("layout_specification"):
        errors.append("Missing layout_specification")

    # Validate assets have required fields
    for i, asset in enumerate(scene.get("required_assets", [])):
        if not asset.get("id"):
            errors.append(f"Asset {i} missing id")
        if not asset.get("type"):
            errors.append(f"Asset {i} missing type")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "scene": scene
    }
