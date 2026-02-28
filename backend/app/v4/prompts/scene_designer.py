"""Scene Designer prompt builder (Phase 1b).

Constructs the prompt for per-scene creative direction.
Produces SceneCreativeDesign with MechanicCreativeDesign entries.
Focuses on HOW: visual style, layout, narrative integration.
"""

import json
from typing import Any, Optional


SYSTEM_PROMPT = """\
You are an expert educational game UX designer specializing in interactive \
learning experiences. You create detailed creative direction for game scenes.

Given a scene concept (WHAT mechanics, WHAT labels), you design HOW the scene \
should look, feel, and play. Your output guides the content generator and \
asset pipeline downstream.

## Multi-Mechanic Scenes

A scene can have multiple mechanics that share the same diagram. When designing \
a multi-mechanic scene:
- The image_spec must accommodate ALL mechanics in the scene (e.g., if drag_drop \
needs spatial zones and description_matching needs the same zones, the image must \
clearly show all structures)
- The instruction_text for the 2nd mechanic should build on what the learner did \
in the 1st (e.g., "Now that you've labeled the chambers, match each one to its \
function")
- Each mechanic_design must have its own generation_goal describing what content \
to generate for THAT mechanic specifically

## MechanicCreativeDesign Fields

For each mechanic in the scene, produce a MechanicCreativeDesign with:
- visual_style: How this mechanic looks in context
- layout_mode: Spatial arrangement (must be valid for the mechanic type)
- card_type: How items/cards appear
- connector_style: How connections between elements look
- instruction_text: Carefully crafted, scene-aware instruction (>20 chars)
- hint_strategy: How hints are provided
- feedback_style: Tone of feedback messages — use misconceptions to inform feedback
- generation_goal: What content to generate (detailed guidance for content generator). \
This must be specific enough that the content generator knows exactly what items/labels \
to produce, how many, and what each one represents.
- key_concepts: Specific concepts the content should cover
- Mechanic-specific creative hints (see below)

## Mechanic-Specific Hints (REQUIRED per type)

- drag_drop: (no extra hint field — uses zone_labels from concept)
- sequencing: "sequence_topic" — what process to sequence
- sorting_categories: "category_names" — list of category names
- trace_path: "path_process" — what flows through the path
- memory_match: "match_type" — "term_to_definition" or "condition_to_treatment"
- click_to_identify: "prompt_style" — "naming", "functional", or "descriptive"
- description_matching: "description_source" — "functional_role" or "anatomical_location"
- branching_scenario: "narrative_premise" — scenario setup text

## VALID layout_mode VALUES PER MECHANIC

- drag_drop: default, radial, grid, spatial
- sequencing: vertical_list, horizontal_list, circular_cycle, flowchart
- sorting_categories: bucket, column, grid, venn_2
- trace_path: default (uses drawing_mode instead)
- memory_match: grid, scattered
- click_to_identify: spatial
- description_matching: spatial, list
- branching_scenario: tree, flowchart
- compare_contrast: side_by_side, overlay

VALID card_type VALUES: text_only, icon_and_text, image_card

## Per-Mechanic Visual Assets (needs_item_images)

Some mechanics benefit from visual assets per item (e.g., an illustrated card showing \
a mitochondrion, a photo of a rock type). Decide for EACH mechanic whether its items \
need images:

Set "needs_item_images": true when:
- The subject involves visually distinct objects (organs, animals, rocks, tools, etc.)
- Visual recognition IS the learning goal (e.g., "identify this structure")
- card_type is "image_card" — items will render as visual cards
- The mechanic is sequencing with visual steps or branching_scenario with visual nodes

Set "needs_item_images": false when:
- The content is primarily textual/conceptual (definitions, abstract terms)
- card_type is "text_only"
- The mechanic already uses the scene diagram for visuals (zone-based mechanics: \
drag_drop, click_to_identify, trace_path, description_matching)

When "needs_item_images": true, also set:
- "item_image_style": a specific style prompt like "labeled scientific diagram", \
"realistic photograph", "flat educational illustration", "watercolor sketch", etc.

These fields drive the content generator to fill image_description per item, which \
the asset pipeline later converts to actual images.

Supported mechanics for item images:
- sequencing: each step can have an image_description
- branching_scenario: each decision node can have an image_description
- memory_match: pairs can have image fronts (use card_type: "image_card")
- sorting_categories: each item can have an image_description
- Zone-based mechanics (drag_drop, click_to_identify, etc.): typically false — they use \
the scene diagram instead
"""


def build_scene_designer_prompt(
    scene_concept: dict[str, Any],
    scene_index: int,
    narrative_theme: str,
    dk: Optional[dict[str, Any]] = None,
    pedagogy: Optional[dict[str, Any]] = None,
    retry_info: Optional[str] = None,
) -> str:
    """Build the prompt for the scene designer."""
    sections = []

    scene_id = f"scene_{scene_index + 1}"

    # 1. Scene concept
    concept_lines = [
        f"- Scene ID: {scene_id}",
        f"- Title: {scene_concept.get('title', 'Untitled')}",
        f"- Learning Goal: {scene_concept.get('learning_goal', '')}",
        f"- Needs Diagram: {scene_concept.get('needs_diagram', True)}",
        f"- Image Description: {scene_concept.get('image_description', '')}",
        f"- Zone Labels: {json.dumps(scene_concept.get('zone_labels', []))}",
    ]
    narrative_intro = scene_concept.get("narrative_intro", "")
    if narrative_intro:
        concept_lines.append(f"- Scene Narrative Intro: {narrative_intro}")
    sections.append("## Scene Concept\n" + "\n".join(concept_lines))

    # 2. Mechanics in this scene
    mechanics = scene_concept.get("mechanics", [])
    mech_lines = []
    is_multi_mechanic = len(mechanics) > 1
    for i, m in enumerate(mechanics):
        advance = m.get("advance_trigger", "completion")
        mech_lines.append(
            f"  {i+1}. {m.get('mechanic_type', 'unknown')} — "
            f"purpose: {m.get('learning_purpose', 'N/A')}, "
            f"items: {m.get('expected_item_count', 0)}, "
            f"labels: {json.dumps(m.get('zone_labels_used', []))}, "
            f"advance_trigger: {advance}"
        )
    header_note = ""
    if is_multi_mechanic:
        header_note = (
            f"\n(Multi-mechanic scene: {len(mechanics)} mechanics share the same diagram. "
            "Design the image_spec to serve ALL mechanics. "
            "The 2nd mechanic's instruction should reference the 1st mechanic's activity.)"
        )
    sections.append("## Mechanics" + header_note + "\n" + "\n".join(mech_lines))

    # 3. Game narrative
    sections.append(f"## Game Narrative Theme\n{narrative_theme}")

    # 4. Domain knowledge — pass full descriptions for labels used in this scene
    if dk:
        dk_lines = []
        scene_labels = set(scene_concept.get("zone_labels", []))
        descs = dk.get("label_descriptions")
        if descs and isinstance(descs, dict):
            # Show full descriptions for labels used in this scene first
            for label in scene_concept.get("zone_labels", []):
                desc = descs.get(label, "")
                if desc:
                    dk_lines.append(f"- {label}: {desc}")
            # Then show remaining labels briefly
            remaining = [l for l in dk.get("canonical_labels", []) if l not in scene_labels]
            if remaining:
                dk_lines.append(f"- Other labels in domain: {', '.join(remaining[:10])}")
        elif dk.get("canonical_labels"):
            dk_lines.append(f"- Labels: {', '.join(dk['canonical_labels'][:15])}")

        # Show sequence flow data if this scene uses sequencing
        has_sequencing = any(m.get("mechanic_type") == "sequencing" for m in mechanics)
        seq = dk.get("sequence_flow_data")
        if has_sequencing and seq:
            seq_items = seq.get("sequence_items", [])
            dk_lines.append(
                f"- Sequence Flow ({seq.get('flow_type', 'unknown')}, "
                f"{len(seq_items)} steps):"
            )
            for item in seq_items[:10]:
                dk_lines.append(
                    f"  - Step {item.get('order_index', '?')}: {item.get('text', '')}"
                )

        if dk_lines:
            sections.append("## Domain Knowledge\n" + "\n".join(dk_lines))

    # 5. Pedagogical context — pass richer info
    if pedagogy:
        ped_lines = [
            f"- Bloom's: {pedagogy.get('blooms_level', 'unknown')}",
            f"- Difficulty: {pedagogy.get('difficulty', 'intermediate')}",
        ]
        # Pass learning objectives
        objectives = pedagogy.get("learning_objectives", [])
        if objectives:
            ped_lines.append("- Learning Objectives:")
            for obj in objectives[:4]:
                ped_lines.append(f"  - {obj}")
        # Pass misconceptions for feedback design
        misconceptions = pedagogy.get("common_misconceptions", [])
        if misconceptions:
            ped_lines.append("- Common Misconceptions (use these to inform feedback_style and hint_strategy):")
            for m in misconceptions[:3]:
                if isinstance(m, dict):
                    ped_lines.append(f"  - Misconception: {m.get('misconception', '')}")
                    ped_lines.append(f"    Correction: {m.get('correction', '')}")
                elif isinstance(m, str):
                    ped_lines.append(f"  - {m}")
        sections.append("## Pedagogical Context\n" + "\n".join(ped_lines))

    # 6. Output format
    sections.append(
        "## Output Format\n"
        "Return a JSON object matching SceneCreativeDesign:\n"
        "```\n"
        "{\n"
        f'  "scene_id": "{scene_id}",\n'
        f'  "title": "{scene_concept.get("title", "")}",\n'
        '  "visual_concept": "Overall visual vision for the scene",\n'
        '  "color_palette_direction": "Color theme guidance",\n'
        '  "spatial_layout": "How elements are arranged",\n'
        '  "atmosphere": "Mood/tone",\n'
        '  "image_spec": {  // if needs_diagram\n'
        '    "description": "Detailed image description (>20 chars)",\n'
        '    "must_include_structures": [...],\n'
        '    "style": "clean_educational",\n'
        '    "annotation_preference": "clean_unlabeled",\n'
        '    "color_direction": "...",\n'
        '    "spatial_guidance": "..."\n'
        "  },\n"
        '  "mechanic_designs": [\n'
        "    // One MechanicCreativeDesign per mechanic:\n"
        "    {\n"
        '      "mechanic_type": "...",\n'
        '      "visual_style": "...",\n'
        '      "card_type": "text_only|icon_and_text|image_card",\n'
        '      "layout_mode": "valid_for_type",\n'
        '      "connector_style": "arrow|flowing|dotted|none",\n'
        '      "instruction_text": "Detailed instruction (>20 chars)",\n'
        '      "hint_strategy": "progressive|contextual|none",\n'
        '      "feedback_style": "encouraging|clinical|narrative",\n'
        '      "generation_goal": "What content to generate",\n'
        '      "key_concepts": ["...", "..."],\n'
        '      "needs_item_images": false,  // true if items need visual assets\n'
        '      "item_image_style": null,  // e.g. "labeled scientific diagram" (when needs_item_images=true)\n'
        '      // Include mechanic-specific hints based on type:\n'
        '      // sequencing: "sequence_topic": "what process to sequence"\n'
        '      // sorting_categories: "category_names": ["Cat A", "Cat B"]\n'
        '      // branching_scenario: "narrative_premise": "scenario setup"\n'
        '      // trace_path: "path_process": "what flows through the path"\n'
        '      // memory_match: "match_type": "term_to_definition|condition_to_treatment"\n'
        '      // click_to_identify: "prompt_style": "naming|functional|descriptive"\n'
        '      // description_matching: "description_source": "functional_role|anatomical_location"\n'
        "    }\n"
        "  ],\n"
        '  "scene_narrative": "How the scene unfolds",\n'
        '  "transition_narrative": "Bridge to next scene"\n'
        "}\n"
        "```\n"
        "IMPORTANT:\n"
        "- Produce exactly one mechanic_design per mechanic, in the same order.\n"
        "- For each mechanic, include its mechanic-specific hint field (listed above).\n"
        "  These hints are CRITICAL for content generation downstream.\n"
        "- For each mechanic, decide needs_item_images based on whether visual assets\n"
        "  enhance learning (see Per-Mechanic Visual Assets section).\n"
        "- When card_type is 'image_card', needs_item_images MUST be true."
    )

    # 7. Retry
    if retry_info:
        sections.append(
            "## RETRY — Previous Attempt Had Issues\n"
            f"{retry_info}"
        )

    return "\n\n".join(sections)
