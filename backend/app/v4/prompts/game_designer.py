"""Game Designer prompt builder.

Constructs the prompt for the Game Designer agent that outputs a GamePlan.
Includes capability spec injection, negative constraints, handcrafted examples,
and retry section support.
"""

import json
from typing import Any, Optional

from app.v4.contracts import build_capability_spec


SYSTEM_PROMPT = """\
You are an expert educational game designer. You transform learning questions \
into interactive game plans with scenes and mechanics.

You output a GamePlan JSON that describes: which mechanics to use, how many \
scenes, what zone labels each scene needs, and brief content briefs for each \
mechanic. You do NOT produce the actual content — a downstream Content \
Generator will use your briefs as seeds.

RULES:
- Follow the capability spec precisely — only use supported mechanics.
- NEVER compute max_score fields. Leave them as 0. A deterministic validator \
  computes all scores from points_per_item * expected_item_count.
- NEVER reference zone IDs — use zone label TEXT from all_zone_labels.
- NEVER default to drag_drop — choose the mechanic that best matches the \
  learning objective.
- NEVER use compare_contrast or hierarchical — they are not yet supported.
- For content-only mechanics (sequencing, sorting_categories, memory_match, \
  branching_scenario), set needs_diagram=false and leave zone_labels empty.
- For zone-based mechanics (drag_drop, click_to_identify, trace_path, \
  description_matching), set needs_diagram=true and populate zone_labels.
- distractor_labels must NOT overlap with all_zone_labels.
- Every zone label used by a mechanic must appear in its scene's zone_labels, \
  and every scene zone_label must appear in all_zone_labels.
- mechanic_connections within a scene must form a DAG (no cycles).
"""


EXAMPLE_1 = {
    "title": "Plant Cell Parts",
    "subject": "Biology",
    "difficulty": "beginner",
    "all_zone_labels": ["Nucleus", "Cell Wall", "Mitochondria", "Chloroplast"],
    "distractor_labels": ["Ribosome", "Lysosome"],
    "scenes": [{
        "scene_id": "scene_1",
        "title": "Label the Plant Cell",
        "learning_goal": "Identify the main organelles of a plant cell",
        "zone_labels": ["Nucleus", "Cell Wall", "Mitochondria", "Chloroplast"],
        "needs_diagram": True,
        "image_spec": {
            "description": "Clean labeled diagram of a plant cell showing organelles",
            "required_elements": ["nucleus", "cell wall", "mitochondria", "chloroplast"],
            "style": "clean educational diagram",
        },
        "mechanics": [{
            "mechanic_id": "m1",
            "mechanic_type": "drag_drop",
            "zone_labels_used": ["Nucleus", "Cell Wall", "Mitochondria", "Chloroplast"],
            "instruction_text": "Drag each label to the correct organelle on the plant cell diagram.",
            "content_brief": {
                "description": "Labels for the four main organelles of a plant cell",
                "key_concepts": ["organelles", "cell structure"],
                "expected_complexity": "low",
                "dk_fields_needed": ["canonical_labels"],
            },
            "expected_item_count": 4,
            "points_per_item": 10,
            "max_score": 0,
        }],
        "mechanic_connections": [],
        "scene_max_score": 0,
    }],
    "total_max_score": 0,
}


EXAMPLE_2 = {
    "title": "Heart Anatomy and Blood Flow",
    "subject": "Biology",
    "difficulty": "intermediate",
    "all_zone_labels": [
        "Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle", "Aorta",
    ],
    "distractor_labels": [],
    "scenes": [
        {
            "scene_id": "scene_1",
            "title": "Label the Heart Chambers",
            "learning_goal": "Identify the four chambers and the aorta",
            "zone_labels": ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle", "Aorta"],
            "needs_diagram": True,
            "image_spec": {
                "description": "Cross-section diagram of the human heart showing chambers",
                "required_elements": ["left atrium", "right atrium", "left ventricle", "right ventricle", "aorta"],
            },
            "mechanics": [
                {
                    "mechanic_id": "m1",
                    "mechanic_type": "drag_drop",
                    "zone_labels_used": ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                    "instruction_text": "Drag the labels to the correct heart chambers.",
                    "content_brief": {
                        "description": "Label the four chambers of the heart",
                        "key_concepts": ["chambers", "atria", "ventricles"],
                        "dk_fields_needed": ["canonical_labels"],
                    },
                    "expected_item_count": 4,
                    "points_per_item": 10,
                    "max_score": 0,
                },
                {
                    "mechanic_id": "m2",
                    "mechanic_type": "trace_path",
                    "zone_labels_used": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle", "Aorta"],
                    "instruction_text": "Trace the path of blood through the heart.",
                    "content_brief": {
                        "description": "Blood flow path through heart chambers",
                        "key_concepts": ["circulation", "blood flow"],
                        "dk_fields_needed": ["flow_sequences", "canonical_labels"],
                    },
                    "expected_item_count": 1,
                    "points_per_item": 20,
                    "max_score": 0,
                },
            ],
            "mechanic_connections": [
                {"from_mechanic_id": "m1", "to_mechanic_id": "m2", "trigger_hint": "completion"},
            ],
            "scene_max_score": 0,
        },
        {
            "scene_id": "scene_2",
            "title": "Order the Cardiac Cycle",
            "learning_goal": "Sequence the phases of the cardiac cycle",
            "zone_labels": [],
            "needs_diagram": False,
            "mechanics": [{
                "mechanic_id": "m3",
                "mechanic_type": "sequencing",
                "zone_labels_used": [],
                "instruction_text": "Arrange the cardiac cycle phases in the correct order.",
                "content_brief": {
                    "description": "Cardiac cycle phases: systole, diastole, etc.",
                    "key_concepts": ["systole", "diastole", "cardiac cycle"],
                    "mechanic_specific_hints": {"sequence_type": "cyclic"},
                    "dk_fields_needed": ["flow_sequences", "temporal_order"],
                },
                "expected_item_count": 4,
                "points_per_item": 10,
                "max_score": 0,
            }],
            "mechanic_connections": [],
            "scene_max_score": 0,
        },
    ],
    "total_max_score": 0,
}


EXAMPLE_3 = {
    "title": "Cell Division Phases",
    "subject": "Biology",
    "difficulty": "intermediate",
    "all_zone_labels": [],
    "distractor_labels": [],
    "scenes": [{
        "scene_id": "scene_1",
        "title": "Mitosis Sequence and Matching",
        "learning_goal": "Understand mitosis phases and match concepts",
        "zone_labels": [],
        "needs_diagram": False,
        "mechanics": [
            {
                "mechanic_id": "m1",
                "mechanic_type": "sequencing",
                "zone_labels_used": [],
                "instruction_text": "Arrange the mitosis phases in the correct order.",
                "content_brief": {
                    "description": "The four phases of mitosis in order",
                    "key_concepts": ["prophase", "metaphase", "anaphase", "telophase"],
                    "mechanic_specific_hints": {"sequence_type": "ordered"},
                    "dk_fields_needed": ["flow_sequences"],
                },
                "expected_item_count": 4,
                "points_per_item": 10,
                "max_score": 0,
            },
            {
                "mechanic_id": "m2",
                "mechanic_type": "memory_match",
                "zone_labels_used": [],
                "instruction_text": "Match each mitosis phase with its key event.",
                "content_brief": {
                    "description": "Pairs of mitosis phase names and their key events",
                    "key_concepts": ["mitosis phases", "cell division events"],
                    "dk_fields_needed": ["definitions"],
                },
                "expected_item_count": 4,
                "points_per_item": 10,
                "max_score": 0,
            },
        ],
        "mechanic_connections": [
            {"from_mechanic_id": "m1", "to_mechanic_id": "m2", "trigger_hint": "completion"},
        ],
        "scene_max_score": 0,
    }],
    "total_max_score": 0,
}


def build_game_designer_prompt(
    question: str,
    pedagogy: Optional[dict[str, Any]] = None,
    dk: Optional[dict[str, Any]] = None,
    capability_spec: Optional[dict[str, Any]] = None,
    retry_info: Optional[str] = None,
) -> str:
    """Build the full user prompt for the Game Designer agent.

    Args:
        question: The user's learning question.
        pedagogy: PedagogicalContext dict (from input_analyzer).
        dk: DomainKnowledge dict (from dk_retriever).
        capability_spec: Output of build_capability_spec(). Auto-generated if None.
        retry_info: Retry section string from build_retry_section() if retrying.

    Returns:
        Complete prompt string for LLM call.
    """
    if capability_spec is None:
        capability_spec = build_capability_spec()

    sections = []

    # 1. Question
    sections.append(f"## Question\n{question}")

    # 2. Pedagogical Context
    if pedagogy:
        ped_lines = [
            f"- Bloom's Level: {pedagogy.get('blooms_level', 'unknown')}",
            f"- Subject: {pedagogy.get('subject', 'unknown')}",
            f"- Difficulty: {pedagogy.get('difficulty', 'intermediate')}",
        ]
        objectives = pedagogy.get("learning_objectives", [])
        if objectives:
            ped_lines.append(f"- Learning Objectives: {', '.join(objectives[:4])}")
        misconceptions = pedagogy.get("common_misconceptions", [])
        if misconceptions:
            mis_texts = [m.get("misconception", str(m)) if isinstance(m, dict) else str(m)
                         for m in misconceptions[:3]]
            ped_lines.append(f"- Common Misconceptions: {'; '.join(mis_texts)}")
        sections.append("## Pedagogical Context\n" + "\n".join(ped_lines))

    # 3. Domain Knowledge
    if dk:
        dk_lines = []
        labels = dk.get("canonical_labels", [])
        if labels:
            dk_lines.append(f"- Canonical Labels ({len(labels)}): {', '.join(labels[:20])}")
        descs = dk.get("label_descriptions")
        if descs and isinstance(descs, dict):
            dk_lines.append(f"- Label Descriptions available for: {', '.join(list(descs.keys())[:10])}")
        seq = dk.get("sequence_flow_data")
        if seq:
            dk_lines.append(f"- Sequence Flow: {seq.get('flow_type', 'unknown')} "
                            f"({len(seq.get('sequence_items', []))} items)")
        comp = dk.get("comparison_data")
        if comp:
            dk_lines.append(f"- Comparison Data: {comp.get('comparison_type', 'unknown')} "
                            f"({len(comp.get('groups', []))} groups)")
        intent = dk.get("content_characteristics", {})
        if intent:
            dk_lines.append(f"- Needs Sequence: {intent.get('needs_sequence', False)}")
            dk_lines.append(f"- Needs Comparison: {intent.get('needs_comparison', False)}")
        if dk_lines:
            sections.append("## Domain Knowledge\n" + "\n".join(dk_lines))

    # 4. Capability Spec (always included)
    sections.append(
        "## Mechanic Capabilities\n"
        "Use ONLY these supported mechanics:\n"
        f"```json\n{json.dumps(capability_spec, indent=2)}\n```"
    )

    # 5. Examples
    sections.append(
        "## Examples\n"
        "### Example 1: Single-scene drag_drop\n"
        f"```json\n{json.dumps(EXAMPLE_1, indent=2)}\n```\n\n"
        "### Example 2: Multi-scene with drag_drop → trace_path → sequencing\n"
        f"```json\n{json.dumps(EXAMPLE_2, indent=2)}\n```\n\n"
        "### Example 3: Content-only (sequencing + memory_match, no diagram)\n"
        f"```json\n{json.dumps(EXAMPLE_3, indent=2)}\n```"
    )

    # 6. Output format reminder
    sections.append(
        "## Output Format\n"
        "Return a single JSON object matching the GamePlan schema.\n"
        "- Leave all max_score / scene_max_score / total_max_score as 0.\n"
        "- Use mechanic_id format: m1, m2, m3, ...\n"
        "- Use scene_id format: scene_1, scene_2, ...\n"
        "- Choose the best mechanic for each learning goal, not just drag_drop.\n"
        "- Multi-scene is OK when content naturally divides into separate diagrams."
    )

    # 7. Retry section (if retrying)
    if retry_info:
        sections.append(f"## Previous Attempt Issues\n{retry_info}")

    return "\n\n".join(sections)
