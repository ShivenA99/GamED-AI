"""Game Concept Designer prompt builder (Phase 1a).

Constructs the prompt for the Game Concept Designer that outputs a GameConcept.
Focuses on WHAT and WHY — scene structure, mechanic choices, narrative theme.
Does NOT include visual direction (that's the scene designer's job).
"""

import json
from typing import Any, Optional


SYSTEM_PROMPT = """\
You are an expert educational game designer. You transform learning questions \
into game concepts with scenes and mechanics.

You output a GameConcept JSON that describes: game title, narrative theme, \
which scenes to create, which mechanics each scene uses, and WHY those \
mechanics match the learning objectives.

## Core Design Principles:

1. **Match mechanic to learning objective** — drag_drop tests spatial labeling, \
trace_path tests process/flow understanding, sequencing tests temporal ordering, \
sorting_categories tests classification, description_matching tests functional knowledge, \
memory_match tests term-definition recall, branching_scenario tests decision-making.

2. **Multi-mechanic scenes for richer learning** — A scene can have multiple mechanics \
that share the same diagram. For example: first drag_drop to label parts, then \
description_matching to test functional knowledge of those same parts. The first \
mechanic's advance_trigger causes transition to the second mechanic within the scene. \
Use multiple mechanics per scene when the same diagram supports different types of \
understanding (spatial → functional → relational).

3. **advance_trigger chaining** — Within a multi-mechanic scene, each mechanic has an \
advance_trigger that determines when to move to the next mechanic:
   - "completion" = move when all items are correctly placed/answered
   - "score_threshold" = move when learner reaches advance_trigger_value percent score
   - The LAST mechanic in a scene has advance_trigger="completion" (terminal)

4. **Scene design** — Each scene should have a single diagram image. Zone-based mechanics \
(drag_drop, click_to_identify, trace_path, description_matching) share the scene's diagram \
and zones. Content-only mechanics (sequencing, sorting_categories, memory_match, \
branching_scenario) do NOT need a diagram — set needs_diagram=false and zone_labels=[].

## Rules:
- ALWAYS produce at least 1 scene with at least 1 mechanic — even for purely \
conceptual or decision-based questions. For example, a clinical decision-making \
question becomes a scene with a branching_scenario mechanic (needs_diagram=false, \
zone_labels=[]).
- ALWAYS include ALL required fields: title, subject, difficulty, \
estimated_duration_minutes, narrative_theme, narrative_intro, completion_message, \
all_zone_labels (can be []), scenes (at least 1).
- Follow the capability spec precisely — only use supported mechanics
- For content-only mechanics, set needs_diagram=false and leave zone_labels empty
- For zone-based mechanics, set needs_diagram=true and populate zone_labels
- distractor_labels must NOT overlap with all_zone_labels
- Every zone label used by a mechanic must appear in its scene's zone_labels, \
  and every scene zone_label must appear in all_zone_labels
- estimated_duration_minutes should be realistic (5-15 minutes typical)
- Focus on WHAT and WHY, not HOW — visual design comes later
"""


def build_concept_designer_prompt(
    question: str,
    pedagogy: Optional[dict[str, Any]] = None,
    dk: Optional[dict[str, Any]] = None,
    capability_spec: Optional[dict[str, Any]] = None,
    retry_info: Optional[str] = None,
) -> str:
    """Build the user prompt for the Game Concept Designer.

    Args:
        question: The user's learning question.
        pedagogy: PedagogicalContext dict.
        dk: DomainKnowledge dict.
        capability_spec: Mechanic capabilities specification.
        retry_info: Previous validation issues for retry.

    Returns:
        Complete prompt string.
    """
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
            ped_lines.append("- Learning Objectives:")
            for obj in objectives[:4]:
                ped_lines.append(f"  - {obj}")
        key_concepts = pedagogy.get("key_concepts", [])
        if key_concepts:
            ped_lines.append("- Key Concepts:")
            for kc in key_concepts[:6]:
                if isinstance(kc, dict):
                    ped_lines.append(
                        f"  - {kc.get('concept', '')} ({kc.get('importance', '')}): "
                        f"{kc.get('description', '')}"
                    )
                else:
                    ped_lines.append(f"  - {kc}")
        misconceptions = pedagogy.get("common_misconceptions", [])
        if misconceptions:
            ped_lines.append("- Common Misconceptions:")
            for m in misconceptions[:3]:
                if isinstance(m, dict):
                    ped_lines.append(f"  - Misconception: {m.get('misconception', '')}")
                    ped_lines.append(f"    Correction: {m.get('correction', '')}")
                else:
                    ped_lines.append(f"  - {m}")
        question_intent = pedagogy.get("question_intent", "")
        if question_intent:
            ped_lines.append(f"- Question Intent: {question_intent}")
        sections.append("## Pedagogical Context\n" + "\n".join(ped_lines))

    # 3. Domain Knowledge
    if dk:
        dk_lines = []
        labels = dk.get("canonical_labels", [])
        if labels:
            dk_lines.append(f"- Canonical Labels ({len(labels)}): {', '.join(labels[:25])}")

        # Show actual label descriptions so the designer knows what each part does
        descs = dk.get("label_descriptions")
        if descs and isinstance(descs, dict):
            dk_lines.append("- Label Descriptions:")
            for label, desc in list(descs.items())[:15]:
                dk_lines.append(f"  - {label}: {desc}")

        # Show actual sequence items so the designer can plan sequencing mechanics
        seq = dk.get("sequence_flow_data")
        if seq:
            seq_items = seq.get("sequence_items", [])
            dk_lines.append(
                f"- Sequence Flow ({seq.get('flow_type', 'unknown')}, "
                f"{len(seq_items)} steps):"
            )
            for item in seq_items[:10]:
                dk_lines.append(f"  - Step {item.get('order_index', '?')}: {item.get('text', '')}")

        # Show comparison data
        comp = dk.get("comparison_data")
        if comp:
            dk_lines.append(
                f"- Comparison Data: {comp.get('comparison_type', 'unknown')} "
                f"({len(comp.get('groups', []))} groups)"
            )
            for group in comp.get("groups", [])[:4]:
                dk_lines.append(
                    f"  - {group.get('group_name', '')}: {', '.join(group.get('members', []))}"
                )

        # Show scene hints from DK retriever (may be list of dicts/strings, or a dict keyed by scene name)
        scene_hints_raw = dk.get("scene_hints", [])
        if isinstance(scene_hints_raw, dict):
            # Convert dict format {"Scene 1": "desc", ...} to list
            scene_hints = [{"scene_name": k, "focus": v} if isinstance(v, str) else v for k, v in list(scene_hints_raw.items())[:4]]
        else:
            scene_hints = list(scene_hints_raw)[:4] if scene_hints_raw else []
        if scene_hints:
            dk_lines.append("- Scene Hints (from domain analysis):")
            for hint in scene_hints:
                if isinstance(hint, dict):
                    dk_lines.append(
                        f"  - {hint.get('scene_name', '')}: {hint.get('focus', '')} "
                        f"(labels: {', '.join(hint.get('labels', [])[:6])})"
                    )
                elif isinstance(hint, str):
                    dk_lines.append(f"  - {hint}")

        intent = dk.get("content_characteristics", {})
        if intent:
            dk_lines.append(f"- Content Needs: "
                            f"labels={intent.get('needs_labels', False)}, "
                            f"sequence={intent.get('needs_sequence', False)}, "
                            f"comparison={intent.get('needs_comparison', False)}")
        if dk_lines:
            sections.append("## Domain Knowledge\n" + "\n".join(dk_lines))

    # 4. Capability Spec
    if capability_spec:
        sections.append(
            "## Mechanic Capabilities\n"
            "Use ONLY these supported mechanics:\n"
            f"```json\n{json.dumps(capability_spec, indent=2)}\n```"
        )

    # 5. Output format with multi-mechanic example
    sections.append(
        "## Output Format\n"
        "Return a single JSON object matching the GameConcept schema.\n\n"
        "Example showing a multi-mechanic scene (2 mechanics sharing one diagram) "
        "followed by a content-only scene:\n"
        "```json\n"
        "{\n"
        '  "title": "Cell Explorer",\n'
        '  "subject": "Biology",\n'
        '  "difficulty": "intermediate",\n'
        '  "estimated_duration_minutes": 10,\n'
        '  "narrative_theme": "Lab Discovery",\n'
        '  "narrative_intro": "Welcome to the lab...",\n'
        '  "completion_message": "Great work!",\n'
        '  "all_zone_labels": ["Nucleus", "Mitochondria", "Cell Membrane"],\n'
        '  "distractor_labels": ["Flagellum"],\n'
        '  "scenes": [\n'
        "    {\n"
        '      "title": "Cell Structure",\n'
        '      "learning_goal": "Label and describe cell organelles",\n'
        '      "narrative_intro": "First, identify the parts...",\n'
        '      "zone_labels": ["Nucleus", "Mitochondria", "Cell Membrane"],\n'
        '      "needs_diagram": true,\n'
        '      "image_description": "Labeled animal cell diagram",\n'
        '      "mechanics": [\n'
        "        {\n"
        '          "mechanic_type": "drag_drop",\n'
        '          "learning_purpose": "Test spatial identification of organelles",\n'
        '          "zone_labels_used": ["Nucleus", "Mitochondria", "Cell Membrane"],\n'
        '          "expected_item_count": 3,\n'
        '          "points_per_item": 10,\n'
        '          "advance_trigger": "completion"\n'
        "        },\n"
        "        {\n"
        '          "mechanic_type": "description_matching",\n'
        '          "learning_purpose": "Test functional knowledge after spatial identification",\n'
        '          "zone_labels_used": ["Nucleus", "Mitochondria", "Cell Membrane"],\n'
        '          "expected_item_count": 3,\n'
        '          "points_per_item": 10,\n'
        '          "advance_trigger": "completion"\n'
        "        }\n"
        "      ],\n"
        '      "transition_to_next": "auto"\n'
        "    },\n"
        "    {\n"
        '      "title": "Cell Division",\n'
        '      "learning_goal": "Sequence the phases of mitosis",\n'
        '      "narrative_intro": "Now arrange the phases...",\n'
        '      "zone_labels": [],\n'
        '      "needs_diagram": false,\n'
        '      "image_description": "",\n'
        '      "mechanics": [\n'
        "        {\n"
        '          "mechanic_type": "sequencing",\n'
        '          "learning_purpose": "Test temporal ordering of mitosis phases",\n'
        '          "zone_labels_used": [],\n'
        '          "expected_item_count": 4,\n'
        '          "points_per_item": 10,\n'
        '          "advance_trigger": "completion"\n'
        "        }\n"
        "      ],\n"
        '      "transition_to_next": "auto"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n\n"
        "Key rules:\n"
        "- A scene can have 1-3 mechanics. Use multiple mechanics when the same diagram "
        "supports testing different depths of knowledge (e.g., label → describe → trace).\n"
        "- Zone-based mechanics in the same scene share the same zone_labels and diagram.\n"
        "- Content-only scenes (sequencing, sorting, branching_scenario, memory_match) must "
        "have needs_diagram=false and zone_labels=[].\n"
        "- expected_item_count must match the actual number of items the mechanic operates on.\n"
        "- mechanic_type must be exactly one of the supported mechanics from the capability spec.\n"
        "- EVERY concept must have scenes, completion_message, and all_zone_labels. "
        "For games with no zone-based mechanics, set all_zone_labels=[].\n\n"
        "Example of a content-only game (no diagrams, no zone labels):\n"
        "```json\n"
        "{\n"
        '  "title": "Clinical Challenge",\n'
        '  "subject": "Medicine",\n'
        '  "difficulty": "advanced",\n'
        '  "estimated_duration_minutes": 10,\n'
        '  "narrative_theme": "Emergency Room",\n'
        '  "narrative_intro": "A patient arrives...",\n'
        '  "completion_message": "Well done, Doctor!",\n'
        '  "all_zone_labels": [],\n'
        '  "distractor_labels": [],\n'
        '  "scenes": [\n'
        "    {\n"
        '      "title": "Diagnostic Decision",\n'
        '      "learning_goal": "Apply diagnostic reasoning",\n'
        '      "zone_labels": [],\n'
        '      "needs_diagram": false,\n'
        '      "image_description": "",\n'
        '      "mechanics": [\n'
        "        {\n"
        '          "mechanic_type": "branching_scenario",\n'
        '          "learning_purpose": "Test clinical decision-making",\n'
        '          "zone_labels_used": [],\n'
        '          "expected_item_count": 5,\n'
        '          "points_per_item": 10,\n'
        '          "advance_trigger": "completion"\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```"
    )

    # 6. Retry section
    if retry_info:
        sections.append(
            "## RETRY — Previous Attempt Had Issues\n"
            "Fix these issues in your response:\n"
            f"{retry_info}"
        )

    return "\n\n".join(sections)
