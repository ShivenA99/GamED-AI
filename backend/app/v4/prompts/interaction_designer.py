"""Interaction Designer prompt builder.

Generates scoring rules, feedback rules, and mode transitions for a scene's
mechanics. Output maps to SceneInteractionResult schema.
"""

import json
from typing import Any, Optional

from app.v4.contracts import resolve_trigger, TRIGGER_MAP


# Per-mechanic scoring patterns for prompt injection
_SCORING_PATTERNS: dict[str, str] = {
    "drag_drop": (
        "strategy: per_correct. Points for each correctly placed label. "
        "partial_credit=true recommended."
    ),
    "click_to_identify": (
        "strategy: per_correct. Points for each correctly identified zone. "
        "partial_credit=true recommended."
    ),
    "trace_path": (
        "strategy: all_or_nothing or per_correct. "
        "all_or_nothing: full points only if entire path correct. "
        "per_correct: points per correct waypoint connection."
    ),
    "sequencing": (
        "strategy: per_correct. Points for each item in the correct position. "
        "partial_credit=true so partial orderings get credit."
    ),
    "sorting_categories": (
        "strategy: per_correct. Points for each item sorted into the correct "
        "category. partial_credit=true recommended."
    ),
    "memory_match": (
        "strategy: per_correct. Points per matched pair. "
        "partial_credit=true. No penalty for failed flips."
    ),
    "branching_scenario": (
        "strategy: weighted. Points assigned per-option in the content. "
        "Accumulates as student navigates. partial_credit=true."
    ),
    "description_matching": (
        "strategy: per_correct. Points for each correct description-zone match. "
        "partial_credit=true recommended."
    ),
}


def build_interaction_prompt(
    scene_plan: dict[str, Any],
    mechanic_contents: list[dict[str, Any]],
    pedagogy: Optional[dict[str, Any]] = None,
) -> str:
    """Build the prompt for the Interaction Designer.

    Args:
        scene_plan: Single ScenePlan dict from the GamePlan.
        mechanic_contents: List of mechanic content dicts for this scene.
        pedagogy: PedagogicalContext for misconception guidance.

    Returns:
        Complete prompt string for LLM call.
    """
    mechanics = scene_plan.get("mechanics", [])
    mechanic_types = [m["mechanic_type"] for m in mechanics]
    connections = scene_plan.get("mechanic_connections", [])

    sections = []

    # Header
    sections.append(
        "You are an expert educational interaction designer.\n"
        "Design scoring rules, feedback messages, and mode transitions "
        "for the mechanics in this scene."
    )

    # Scene context
    sections.append(
        f"## Scene: {scene_plan.get('title', 'Untitled')}\n"
        f"- Scene ID: {scene_plan.get('scene_id')}\n"
        f"- Learning Goal: {scene_plan.get('learning_goal')}\n"
        f"- Mechanics: {', '.join(mechanic_types)}"
    )

    # Per-mechanic scoring guidance (only for mechanics in this scene)
    scoring_lines = ["## Scoring Patterns"]
    for mech in mechanics:
        mtype = mech["mechanic_type"]
        mid = mech["mechanic_id"]
        pattern = _SCORING_PATTERNS.get(mtype, "strategy: per_correct")
        pts = mech.get("points_per_item", 10)
        count = mech.get("expected_item_count", 1)
        max_score = pts * count
        scoring_lines.append(
            f"### {mid} ({mtype})\n"
            f"- {pattern}\n"
            f"- points_per_correct: {pts}\n"
            f"- max_score: {max_score}"
        )
    sections.append("\n".join(scoring_lines))

    # Mechanic content summary
    if mechanic_contents:
        content_lines = ["## Mechanic Content (for feedback context)"]
        for mc in mechanic_contents:
            mid = mc.get("mechanic_id", "unknown")
            mtype = mc.get("mechanic_type", "unknown")
            content = mc.get("content", {})
            # Provide a brief summary, not the full content
            content_str = json.dumps(content)
            if len(content_str) > 400:
                content_str = content_str[:400] + "..."
            content_lines.append(f"### {mid} ({mtype})\n```json\n{content_str}\n```")
        sections.append("\n".join(content_lines))

    # Per-mechanic feedback examples
    feedback_lines = ["## Feedback Design Guide"]
    feedback_lines.append(
        "For EVERY mechanic, design specific feedback. Examples by type:"
    )
    for mech in mechanics:
        mtype = mech["mechanic_type"]
        mid = mech["mechanic_id"]
        if mtype == "drag_drop":
            feedback_lines.append(
                f"### {mid} (drag_drop)\n"
                "- on_correct: Confirm correct label placement\n"
                "- on_incorrect: Guide toward the right zone\n"
                "- on_completion: Celebrate all labels placed"
            )
        elif mtype == "sorting_categories":
            feedback_lines.append(
                f"### {mid} (sorting_categories)\n"
                "- on_correct: Confirm correct category placement\n"
                "- on_incorrect: Explain why the item belongs elsewhere\n"
                "- on_completion: Celebrate all items sorted correctly"
            )
        elif mtype == "sequencing":
            feedback_lines.append(
                f"### {mid} (sequencing)\n"
                "- on_correct: Confirm step is in right position\n"
                "- on_incorrect: Hint about what comes before/after\n"
                "- on_completion: Celebrate correct ordering"
            )
        elif mtype == "memory_match":
            feedback_lines.append(
                f"### {mid} (memory_match)\n"
                "- on_correct: Confirm matching pair found\n"
                "- on_incorrect: Encourage to keep trying\n"
                "- on_completion: Celebrate all pairs matched"
            )
        elif mtype == "branching_scenario":
            feedback_lines.append(
                f"### {mid} (branching_scenario)\n"
                "- on_correct: Affirm the clinical/logical reasoning\n"
                "- on_incorrect: Explain why another option is better\n"
                "- on_completion: Summarize the decision path"
            )
        elif mtype == "trace_path":
            feedback_lines.append(
                f"### {mid} (trace_path)\n"
                "- on_correct: Confirm correct waypoint\n"
                "- on_incorrect: Hint about the correct next step\n"
                "- on_completion: Celebrate full path traced"
            )
        elif mtype == "description_matching":
            feedback_lines.append(
                f"### {mid} (description_matching)\n"
                "- on_correct: Confirm correct match\n"
                "- on_incorrect: Clarify the distinction\n"
                "- on_completion: Celebrate all descriptions matched"
            )
        else:
            feedback_lines.append(
                f"### {mid} ({mtype})\n"
                "- on_correct: Confirm correct action\n"
                "- on_incorrect: Guide toward the right answer\n"
                "- on_completion: Celebrate completion"
            )
    sections.append("\n".join(feedback_lines))

    # Misconception guidance
    if pedagogy:
        misconceptions = pedagogy.get("common_misconceptions", [])
        if misconceptions:
            mis_lines = ["## Misconception Feedback Guidance"]
            for m in misconceptions[:5]:
                if isinstance(m, dict):
                    mis_lines.append(
                        f"- When student thinks: \"{m.get('misconception', '')}\"\n"
                        f"  Correct with: \"{m.get('correction', '')}\""
                    )
            sections.append("\n".join(mis_lines))

    # Transition rules
    if len(mechanics) > 1:
        trans_lines = ["## Mode Transitions"]
        trans_lines.append(
            "Design transitions between mechanics in this scene. "
            "Each transition specifies when to switch from one mechanic to the next."
        )
        if connections:
            trans_lines.append("\nPlanned connections:")
            for conn in connections:
                from_id = conn.get("from_mechanic_id")
                to_id = conn.get("to_mechanic_id")
                hint = conn.get("trigger_hint", "completion")
                from_mech = next((m for m in mechanics if m["mechanic_id"] == from_id), None)
                from_type = from_mech["mechanic_type"] if from_mech else "unknown"
                trigger = resolve_trigger(hint, from_type)
                trans_lines.append(
                    f"- {from_id} → {to_id}: trigger={trigger} (hint: {hint})"
                )
        sections.append("\n".join(trans_lines))

    # Output format
    sections.append(
        "## Output Format\n"
        "Return a single JSON object:\n"
        "```json\n"
        "{\n"
        '  "scene_id": "<scene_id>",\n'
        '  "mechanic_scoring": {\n'
        '    "<mechanic_id>": {\n'
        '      "strategy": "per_correct",\n'
        '      "points_per_correct": 10,\n'
        '      "max_score": 30,\n'
        '      "partial_credit": true\n'
        "    }\n"
        "  },\n"
        '  "mechanic_feedback": {\n'
        '    "<mechanic_id>": {\n'
        '      "on_correct": "Great job!",\n'
        '      "on_incorrect": "Not quite. Try again.",\n'
        '      "on_completion": "Well done!",\n'
        '      "misconceptions": [\n'
        '        {"trigger_label": "wrong_zone_Nucleus", "message": "...","severity": "medium"}\n'
        "      ]\n"
        "    }\n"
        "  },\n"
        '  "mode_transitions": [\n'
        '    {"from_mode": "drag_drop", "to_mode": "trace_path", "trigger": "all_zones_labeled"}\n'
        "  ]\n"
        "}\n"
        "```\n\n"
        "Rules:\n"
        "- EXACTLY one scoring entry AND one feedback entry per mechanic_id — "
        "EVERY mechanic MUST have both scoring and feedback\n"
        "- max_score = points_per_correct * item_count (must match the game plan)\n"
        "- Feedback should be encouraging and educational\n"
        "- on_correct, on_incorrect, on_completion: all three required per mechanic\n"
        "- misconceptions: specific triggers for common mistakes\n"
        "- mode_transitions: only if scene has multiple mechanics with connections"
    )

    return "\n\n".join(sections)
