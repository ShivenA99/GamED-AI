"""Content Generator prompt builder (Phase 2a).

Per-mechanic prompt templates that use MechanicCreativeDesign to generate
content WITH frontend visual config fields populated.

Each template generates content matching the mechanic's Pydantic schema
from mechanic_content.py, including all visual config fields.

Critical: All field names match the frontend EXACTLY. No post-mapping.
"""

import json
from typing import Any, Optional


def build_content_prompt(
    mechanic_type: str,
    creative_design: dict[str, Any],
    scene_context: dict[str, Any],
    dk: Optional[dict[str, Any]] = None,
    mechanic_plan: Optional[dict[str, Any]] = None,
) -> str:
    """Build a prompt for generating content for a specific mechanic.

    Args:
        mechanic_type: One of the supported mechanic types.
        creative_design: MechanicCreativeDesign dict from the scene designer.
        scene_context: Scene context with zone_labels, dk_subset, etc.
        dk: Full domain knowledge (optional, scene_context has dk_subset).
        mechanic_plan: Full MechanicPlan dict.

    Returns:
        Complete prompt string for LLM call.
    """
    header = _build_header(scene_context, creative_design, mechanic_plan)

    template_fn = _TEMPLATES.get(mechanic_type)
    if template_fn is None:
        return f"{header}\n\nGenerate content for mechanic type: {mechanic_type}"

    body = template_fn(creative_design, scene_context, mechanic_plan or {})
    return f"{header}\n\n{body}"


def _build_header(
    scene_context: dict[str, Any],
    creative_design: dict[str, Any],
    mechanic_plan: Optional[dict[str, Any]],
) -> str:
    """Common header with scene context and creative direction."""
    lines = [
        "You are an expert educational content generator.",
        "",
        f"## Scene: {scene_context.get('title', 'Untitled')}",
        f"- Scene ID: {scene_context.get('scene_id', 'unknown')}",
        f"- Learning Goal: {scene_context.get('learning_goal', '')}",
    ]

    # Scene-level creative context (from build_scene_context)
    if scene_context.get("visual_concept"):
        lines.append(f"- Visual Concept: {scene_context['visual_concept']}")
    if scene_context.get("atmosphere"):
        lines.append(f"- Atmosphere: {scene_context['atmosphere']}")
    if scene_context.get("color_palette_direction"):
        lines.append(f"- Color Palette: {scene_context['color_palette_direction']}")
    if scene_context.get("scene_narrative"):
        lines.append(f"- Scene Narrative: {scene_context['scene_narrative']}")

    lines.extend([
        "",
        "## Creative Direction (per-mechanic)",
        f"- Visual Style: {creative_design.get('visual_style', 'educational')}",
        f"- Generation Goal: {creative_design.get('generation_goal', '')}",
        f"- Key Concepts: {', '.join(creative_design.get('key_concepts', []))}",
        f"- Pedagogical Focus: {creative_design.get('pedagogical_focus', '')}",
        f"- Card Type: {creative_design.get('card_type', 'text_only')}",
        f"- Layout Mode: {creative_design.get('layout_mode', 'default')}",
        f"- Color Direction: {creative_design.get('color_direction', '')}",
        f"- Instruction Text: {creative_design.get('instruction_text', '')}",
        f"- Instruction Tone: {creative_design.get('instruction_tone', 'educational')}",
        f"- Narrative Hook: {creative_design.get('narrative_hook', '')}",
        f"- Difficulty Curve: {creative_design.get('difficulty_curve', 'gradual')}",
        f"- Hint Strategy: {creative_design.get('hint_strategy', 'progressive')}",
        f"- Feedback Style: {creative_design.get('feedback_style', 'encouraging')}",
    ])

    # Item image guidance
    if creative_design.get("needs_item_images"):
        lines.append(f"- Needs Item Images: YES — fill image_description for each item")
        lines.append(f"- Item Image Style: {creative_design.get('item_image_style', 'educational illustration')}")

    # Add DK subset from scene context
    dk_subset = scene_context.get("dk_subset", {})
    if dk_subset:
        lines.append("")
        lines.append("## Domain Knowledge")
        for field_name, value in dk_subset.items():
            val_str = json.dumps(value) if not isinstance(value, str) else value
            if len(val_str) > 500:
                val_str = val_str[:500] + "..."
            lines.append(f"- {field_name}: {val_str}")

    return "\n".join(lines)


def _card_type_to_label_style(card_type: str) -> str:
    """Map creative design card_type to frontend label_style enum."""
    return {
        "text_only": "text",
        "icon_and_text": "text_with_icon",
        "image_card": "text_with_thumbnail",
    }.get(card_type, "text")


def _drag_drop_prompt(
    creative: dict, context: dict, plan: dict,
) -> str:
    zone_labels = plan.get("zone_labels_used", context.get("zone_labels", []))
    layout_mode = creative.get("layout_mode", "default")
    connector = creative.get("connector_style", "arrow")
    feedback_style = creative.get("feedback_style", "encouraging")
    label_style = _card_type_to_label_style(creative.get("card_type", "text_only"))

    return f"""\
## Task: Generate Drag & Drop Content

Generate labels for these zones: {json.dumps(zone_labels)}

The creative direction specifies:
- Layout: {layout_mode}
- Connector style: {connector} → maps to leader_line_style
- Feedback: {feedback_style} → maps to feedback_timing

Return JSON matching this EXACT schema (include ALL visual config fields):
```json
{{
    "labels": {json.dumps(zone_labels)},
    "distractor_labels": ["plausible_but_wrong_1", "plausible_but_wrong_2"],
    "interaction_mode": "drag_drop",
    "feedback_timing": "{_feedback_to_timing(feedback_style)}",
    "label_style": "{label_style}",
    "leader_line_style": "{_connector_to_line(connector)}",
    "leader_line_color": "",
    "leader_line_animate": true,
    "pin_marker_shape": "circle",
    "label_anchor_side": "auto",
    "tray_position": "{_layout_to_tray(layout_mode)}",
    "tray_layout": "horizontal",
    "placement_animation": "spring",
    "incorrect_animation": "shake",
    "zone_idle_animation": "pulse",
    "zone_hover_effect": "highlight",
    "max_attempts": 3,
    "shuffle_labels": true
}}
```

Rules:
- labels MUST be EXACTLY: {json.dumps(zone_labels)}
- Generate 2-3 plausible distractor_labels
- Distractor labels must NOT overlap with zone labels
- label_style MUST be one of: "text", "text_with_icon", "text_with_thumbnail", "text_with_description"
- max_attempts MUST be a positive integer (not null)
- Include ALL visual config fields shown above
- Return ONLY the JSON object
"""


def _click_to_identify_prompt(creative: dict, context: dict, plan: dict) -> str:
    zone_labels = plan.get("zone_labels_used", context.get("zone_labels", []))
    prompt_style = creative.get("prompt_style", "naming")

    return f"""\
## Task: Generate Click-to-Identify Content

Generate identification prompts for: {json.dumps(zone_labels)}
Prompt style: {prompt_style}

Return JSON with ALL fields:
```json
{{
    "prompts": [
        {{
            "text": "Click on the structure that...",
            "target_label": "ExactZoneLabel",
            "explanation": "This is because...",
            "order": 0
        }}
    ],
    "prompt_style": "{prompt_style}",
    "selection_mode": "sequential",
    "highlight_style": "outlined",
    "magnification_enabled": false,
    "magnification_factor": 1.5,
    "explore_mode_enabled": false,
    "show_zone_count": true
}}
```

Rules:
- One prompt per zone label, in increasing difficulty
- target_label MUST be EXACT from: {json.dumps(zone_labels)}
- Text should describe function, not name the structure
- Include ALL visual config fields
"""


def _trace_path_prompt(creative: dict, context: dict, plan: dict) -> str:
    zone_labels = plan.get("zone_labels_used", context.get("zone_labels", []))
    path_process = creative.get("path_process", "")

    return f"""\
## Task: Generate Trace Path Content

Generate path(s) connecting: {json.dumps(zone_labels)}
{f"Process: {path_process}" if path_process else ""}

Return JSON with ALL fields:
```json
{{
    "paths": [
        {{
            "label": "Flow Name",
            "description": "Trace the path of...",
            "color": "#E74C3C",
            "requiresOrder": true,
            "waypoints": [
                {{"label": "Zone1", "order": 0}},
                {{"label": "Zone2", "order": 1}}
            ]
        }}
    ],
    "path_type": "linear",
    "drawing_mode": "click_waypoints",
    "particleTheme": "dots",
    "particleSpeed": "medium",
    "color_transition_enabled": false,
    "show_direction_arrows": true,
    "show_waypoint_labels": true,
    "show_full_flow_on_complete": true,
    "submit_mode": "immediate"
}}
```

Rules:
- Waypoint labels MUST be from: {json.dumps(zone_labels)}
- particleSpeed MUST be "slow", "medium", or "fast" (string!)
- Include ALL visual config fields
"""


def _sequencing_prompt(creative: dict, context: dict, plan: dict) -> str:
    item_count = plan.get("expected_item_count", 4)
    seq_topic = creative.get("sequence_topic", "")
    layout_mode = creative.get("layout_mode", "vertical_list")
    card_type = creative.get("card_type", "text_only")
    connector = creative.get("connector_style", "arrow")
    needs_images = creative.get("needs_item_images", False)
    image_style = creative.get("item_image_style", "educational illustration")

    # Build example items matching the requested count
    image_field = f', "image_description": "A {image_style} showing step {{i+1}}"' if needs_images else ""
    example_items = ",\n        ".join(
        f'{{"id": "s{i+1}", "content": "Step {i+1} description", "explanation": "Why this is step {i+1}", "icon": ""{image_field}}}'
        for i in range(item_count)
    )
    example_order = ", ".join(f'"s{i+1}"' for i in range(item_count))

    image_rules = ""
    if needs_images:
        image_rules = f"""
- Each item MUST include "image_description": a detailed visual description for image generation
- Image style: {image_style}
- Descriptions should be specific enough to generate a unique, recognizable image for each step"""

    return f"""\
## Task: Generate Sequencing Content

Generate EXACTLY {item_count} items to arrange in order.
{f"Topic: {seq_topic}" if seq_topic else ""}

The response must be a JSON object with TWO top-level keys: "items" (array of objects) and "correct_order" (array of ID strings).
"correct_order" is NOT inside "items" — it is a separate sibling field.

Return this exact JSON structure:
```json
{{
    "items": [
        {example_items}
    ],
    "correct_order": [{example_order}],
    "sequence_type": "ordered",
    "layout_mode": "{layout_mode}",
    "interaction_pattern": "drag_reorder",
    "card_type": "{card_type}",
    "connector_style": "{connector}",
    "show_position_numbers": false,
    "allow_partial_credit": true
}}
```

Rules:
- "items" array contains EXACTLY {item_count} objects, each with id/content/explanation/icon
- "correct_order" is a SEPARATE top-level array (NOT inside items) listing all {item_count} item IDs in correct sequence
- Include ALL visual config fields shown above{image_rules}
"""


def _sorting_prompt(creative: dict, context: dict, plan: dict) -> str:
    item_count = plan.get("expected_item_count", 6)
    category_names = creative.get("category_names", [])
    layout_mode = creative.get("layout_mode", "default")
    card_type = creative.get("card_type", "text_only")
    needs_images = creative.get("needs_item_images", False)
    image_style = creative.get("item_image_style", "educational illustration")

    sort_mode = _layout_to_sort_mode(layout_mode)

    image_field = ""
    if needs_images:
        image_field = ', "image_description": "A visual description for image generation"'

    image_rules = ""
    if needs_images:
        image_rules = f"""
- Each item MUST include "image_description": a detailed visual description for image generation
- Image style: {image_style}
- Descriptions should be specific enough to visually distinguish items from each other"""

    return f"""\
## Task: Generate Sorting Content

Generate categories and {item_count} items to sort.
{f"Categories: {json.dumps(category_names)}" if category_names else "Generate 2-4 categories."}

Return JSON with ALL fields:
```json
{{
    "categories": [
        {{"id": "cat1", "label": "Category A", "color": "#4A90D9", "description": "..."}},
        {{"id": "cat2", "label": "Category B", "color": "#E74C3C", "description": "..."}}
    ],
    "items": [
        {{"id": "i1", "content": "Item", "correctCategoryId": "cat1", "explanation": "...", "description": "", "difficulty": "medium"{image_field}}}
    ],
    "sort_mode": "{sort_mode}",
    "item_card_type": "{card_type}",
    "container_style": "bucket",
    "submit_mode": "immediate_feedback",
    "allow_multi_category": false,
    "show_category_hints": false,
    "allow_partial_credit": true
}}
```

Rules:
- Use "label" NOT "name" for categories
- Use "correctCategoryId" (camelCase!)
- Include ALL visual config fields{image_rules}
"""


def _memory_match_prompt(creative: dict, context: dict, plan: dict) -> str:
    item_count = plan.get("expected_item_count", 4)
    match_type = creative.get("match_type", "term_to_definition")
    needs_images = creative.get("needs_item_images", False)
    image_style = creative.get("item_image_style", "educational illustration")

    if needs_images:
        front_type = "image"
        front_example = f"A {image_style} of the term"
        pair_note = (
            f"\n\nWhen frontType is \"image\", the \"front\" field should contain a detailed "
            f"image description (style: {image_style}) that will be converted to an actual image. "
            f"The \"back\" field remains a text definition."
        )
    else:
        front_type = "text"
        front_example = "Term"
        pair_note = ""

    return f"""\
## Task: Generate Memory Match Content

Generate {item_count} pairs for matching. Type: {match_type}{pair_note}

Return JSON with ALL fields:
```json
{{
    "pairs": [
        {{
            "id": "p1", "front": "{front_example}", "back": "Definition",
            "frontType": "{front_type}", "backType": "text",
            "explanation": "Why they match", "category": ""
        }}
    ],
    "game_variant": "classic",
    "gridSize": {json.dumps(_compute_grid_size(item_count))},
    "match_type": "{match_type}",
    "card_back_style": "question_mark",
    "matched_card_behavior": "fade",
    "show_explanation_on_match": true,
    "flip_duration_ms": 400,
    "show_attempts_counter": true
}}
```

Rules:
- Use "front"/"back" NOT "term"/"definition"
- gridSize as [rows, cols] integers (NOT string!)
- EXACTLY {item_count} pairs
- Include ALL visual config fields
"""


def _branching_prompt(creative: dict, context: dict, plan: dict) -> str:
    item_count = plan.get("expected_item_count", 4)
    premise = creative.get("narrative_premise", "")
    needs_images = creative.get("needs_item_images", False)
    image_style = creative.get("item_image_style", "educational illustration")

    image_field_example = ""
    if needs_images:
        image_field_example = ',\n            "image_description": "A detailed visual description for this decision point"'

    image_rules = ""
    if needs_images:
        image_rules = f"""
- Each decision node MUST include "image_description": a detailed visual description
- Image style: {image_style}
- Descriptions should visually represent the scenario at each decision point"""

    return f"""\
## Task: Generate Branching Scenario Content

Generate a decision tree with {item_count}+ nodes.
{f"Premise: {premise}" if premise else ""}

Return JSON with ALL fields:
```json
{{
    "nodes": [
        {{
            "id": "n1", "question": "Decision question?", "description": "",
            "node_type": "decision",
            "options": [
                {{"id": "o1", "text": "Choice A", "nextNodeId": "n2", "isCorrect": true, "consequence": "Good!", "points": 10}},
                {{"id": "o2", "text": "Choice B", "nextNodeId": "n3", "isCorrect": false, "consequence": "Not ideal.", "points": 0}}
            ],
            "isEndNode": false{image_field_example}
        }},
        {{
            "id": "n3", "question": "End result", "isEndNode": true,
            "endMessage": "Summary message", "options": [],
            "ending_type": "suboptimal", "narrative_text": ""{image_field_example}
        }}
    ],
    "startNodeId": "n1",
    "narrative_structure": "branching",
    "show_path_taken": true,
    "allow_backtrack": false,
    "show_consequences": true,
    "multiple_valid_endings": false
}}
```

Rules:
- "question" NOT "prompt", "options" NOT "choices"
- camelCase: nextNodeId, isCorrect, isEndNode, endMessage, startNodeId
- REQUIRED top-level fields: "nodes", "startNodeId", "narrative_structure", \
"show_path_taken", "allow_backtrack", "show_consequences", "multiple_valid_endings"
- "startNodeId" MUST be present and set to the ID of the first node
- End nodes: isEndNode=true, options=[]
- All nextNodeId values reference valid node IDs
- Include ALL visual config fields{image_rules}
"""


def _description_matching_prompt(creative: dict, context: dict, plan: dict) -> str:
    zone_labels = plan.get("zone_labels_used", context.get("zone_labels", []))
    description_source = creative.get("description_source", "functional_role")

    return f"""\
## Task: Generate Description Matching Content

Generate descriptions for: {json.dumps(zone_labels)}
Description source: {description_source}
{f"Focus descriptions on the {description_source} of each structure." if description_source else ""}

Return JSON with ALL fields:
```json
{{
    "descriptions": {{
        "ZoneLabel": "Description of this structure's function and role"
    }},
    "mode": "click_zone",
    "distractor_descriptions": ["A plausible but incorrect description"],
    "show_connecting_lines": true,
    "defer_evaluation": false,
    "description_panel_position": "right"
}}
```

Rules:
- Keys MUST be EXACT zone labels: {json.dumps(zone_labels)}
- Descriptions should focus on {description_source} — describe function, not name
- Include ALL visual config fields
"""


def _compare_contrast_prompt(creative: dict, context: dict, plan: dict) -> str:
    subjects = creative.get("comparison_subjects", [])
    return f"""\
## Task: Generate Compare & Contrast Content

Generate comparison content for subjects: {json.dumps(subjects)}

Return JSON with ALL fields:
```json
{{
    "subject_a": {{"id": "subject_a", "name": "Subject A Name", "description": "...", "zone_labels": []}},
    "subject_b": {{"id": "subject_b", "name": "Subject B Name", "description": "...", "zone_labels": []}},
    "expected_categories": {{"label": "similar|different|unique_a|unique_b"}},
    "comparison_mode": "side_by_side",
    "highlight_matching": true,
    "category_types": ["similar", "different", "unique_a", "unique_b"],
    "category_labels": {{"similar": "Shared", "different": "Different"}},
    "category_colors": {{"similar": "#4CAF50", "different": "#F44336"}},
    "exploration_enabled": false,
    "zoom_enabled": false
}}
```

Rules:
- Include ALL visual config fields
- expected_categories maps zone labels to categories
"""


# ── Template registry ──────────────────────────────────────────

_TEMPLATES: dict[str, Any] = {
    "drag_drop": _drag_drop_prompt,
    "click_to_identify": _click_to_identify_prompt,
    "trace_path": _trace_path_prompt,
    "sequencing": _sequencing_prompt,
    "sorting_categories": _sorting_prompt,
    "memory_match": _memory_match_prompt,
    "branching_scenario": _branching_prompt,
    "description_matching": _description_matching_prompt,
    "compare_contrast": _compare_contrast_prompt,
}


# ── Helper mappers ────────────────────────────────────────────

def _feedback_to_timing(feedback_style: str) -> str:
    return "deferred" if feedback_style == "clinical" else "immediate"

def _connector_to_line(connector: str) -> str:
    mapping = {"arrow": "elbow", "flowing": "curved", "dotted": "straight", "none": "none"}
    return mapping.get(connector, "elbow")

def _layout_to_tray(layout_mode: str) -> str:
    mapping = {"radial": "bottom", "grid": "left", "spatial": "bottom"}
    return mapping.get(layout_mode, "bottom")

def _layout_to_sort_mode(layout_mode: str) -> str:
    mapping = {"bucket": "bucket", "column": "column", "grid": "bucket", "venn_2": "venn_2"}
    return mapping.get(layout_mode, "bucket")

def _compute_grid_size(pair_count: int) -> list[int]:
    total_cards = pair_count * 2
    if total_cards <= 6:
        return [2, 3]
    if total_cards <= 8:
        return [2, 4]
    if total_cards <= 12:
        return [3, 4]
    return [4, 4]
