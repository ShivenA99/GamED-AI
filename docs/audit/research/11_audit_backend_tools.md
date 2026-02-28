# Audit 11: V3 Pipeline Backend Tools -- Full Mechanic Coverage Analysis

**Date:** 2026-02-11
**Scope:** All 5 V3 backend tool files, audited against 9 game mechanics
**Method:** Line-by-line code reading of actual tool implementations

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [File 1: game_design_v3_tools.py](#2-game_design_v3_toolspy)
3. [File 2: scene_architect_tools.py](#3-scene_architect_toolspy)
4. [File 3: interaction_designer_tools.py](#4-interaction_designer_toolspy)
5. [File 4: asset_generator_tools.py](#5-asset_generator_toolspy)
6. [File 5: blueprint_assembler_tools.py](#6-blueprint_assembler_toolspy)
7. [Cross-Tool Data Flow Analysis](#7-cross-tool-data-flow-analysis)
8. [Master Coverage Matrix](#8-master-coverage-matrix)
9. [Missing Tools Needed](#9-missing-tools-needed)
10. [Priority Fix List](#10-priority-fix-list)

---

## 1. Executive Summary

The V3 pipeline has **22 tools across 5 files**. After line-by-line audit:

- **drag_drop**: FULLY SUPPORTED end-to-end
- **click_to_identify**: MOSTLY SUPPORTED (prompts generated, config assembled, but no magnification/highlight config)
- **trace_path**: MOSTLY SUPPORTED (waypoints generated, paths assembled, but no SVG path definitions, animated particles, or color transitions)
- **sequencing**: MOSTLY SUPPORTED (items/correct_order generated, sequenceConfig assembled, but no per-item illustrations or layout config)
- **description_matching**: MOSTLY SUPPORTED (descriptions generated from DK, config assembled, but no distractor descriptions generated)
- **sorting_categories**: MOSTLY SUPPORTED (categories/items generated, sortingConfig assembled, but no per-item illustrations, sort mode config missing (bucket/venn/matrix))
- **memory_match**: PARTIALLY SUPPORTED (pairs generated from labels+descriptions, memoryMatchConfig assembled, but no per-card images, no flip animation config beyond duration)
- **branching_scenario**: PARTIALLY SUPPORTED (decision nodes generated via LLM, branchingConfig assembled, but no scene backgrounds, character sprites, or state variables)
- **compare_contrast**: WEAKLY SUPPORTED (expected_categories generated if comparison_data exists, compareConfig assembled, but NO dual-diagram generation, no zone pairings, no matched diagrams)

**Critical gap**: The asset_generator_tools.py is 100% single-diagram-focused. No tool generates per-item illustrations, card images, dual diagrams, scene backgrounds, or character sprites. All non-diagram assets are absent.

---

## 2. game_design_v3_tools.py

### Tool Function Inventory

| # | Tool | Type | What It Does |
|---|------|------|--------------|
| 1 | `analyze_pedagogy` | Deterministic + context | Content-type detection, Bloom's alignment, recommended patterns, DK injection |
| 2 | `check_capabilities` | Deterministic + context | Full capability matrix of all 9 mechanics with data availability |
| 3 | `get_example_designs` | Deterministic | Few-shot exemplar designs by content type |
| 4 | `validate_design` | Deterministic | Schema + rule validation of GameDesignV3Slim |
| 5 | `submit_game_design` | Pydantic gate | Final submission with GameDesignV3 or Slim validation |

### Per-Mechanic Audit

#### analyze_pedagogy (Lines 29-151)

**Bias issue**: Line 108-111 -- `drag_drop` is ALWAYS force-inserted as a baseline recommendation:
```python
if "drag_drop" not in recommended_patterns:
    recommended_patterns.insert(0, "drag_drop")
    pattern_reasons["drag_drop"] = "baseline interaction mode"
```
This means every game design will have drag_drop recommended even when it is pedagogically inappropriate (e.g., for a branching scenario question or a pure comparison question).

**Content type detection** (lines 63-76): Maps keywords to 7 content types, BUT:
- `"comparison"` correctly identified for compare_contrast
- `"process"` correctly identified for trace_path/sequencing
- No explicit detection for: "scenario/decision/branching", "memory/recall/flashcard", "sorting/classify/categorize" (relies on the more generic "hierarchy" type)
- "functional_reasoning" maps well to description_matching

**Scoring strategy** (lines 121-127): Only maps `content_type`, not `mechanic_type`. Misses mechanic-specific strategies (e.g., memory_match should recommend time_based regardless of content type).

#### check_capabilities (Lines 158-295)

**Well-implemented**: All 9 mechanics have entries in `MECHANIC_DATA_NEEDS` (lines 184-245) with:
- `required_data` / `optional_data` arrays
- `data_available` boolean checking context
- `readiness_note` with current availability status

**Gap**: `data_available` for `branching_scenario` is hardcoded `True` (line 237) but it actually needs LLM generation (no upstream data feeds it). Same for `compare_contrast` (line 242) -- `True` but comparison_data may not exist.

#### validate_design (Lines 371-481)

**Issue**: Validates against `GameDesignV3Slim` which has `SlimMechanicRef` -- this is just `{type: str}` with no config fields. The validation (lines 437-444) only checks:
- Mechanic types exist and are valid
- Mechanic diversity across scenes
- Label count >= 3

**Missing**: No per-mechanic config completeness checks because Slim schema intentionally defers configs to Phase 2/3. This is architecturally correct but means the game_designer gets no feedback on whether it chose a mechanic that is feasible given the available data.

#### submit_game_design (Lines 488-553)

**Good**: Tries full `GameDesignV3` first (with per-mechanic config fields), falls back to Slim. When full schema validates, it catches mechanic-specific issues via `validate_game_design()` (which checks trace_path needs path_config.waypoints, sequencing needs sequence_config, etc.).

**Issue**: The fallback to Slim means most submissions will succeed without per-mechanic config validation, since the game_designer LLM typically produces Slim output.

### Mechanic Coverage Summary

| Mechanic | Recommended? | Feasibility Check? | Config Validated? |
|----------|-------------|-------------------|------------------|
| drag_drop | ALWAYS (forced baseline) | Yes | N/A (no config in Slim) |
| click_to_identify | If content matches | Yes | N/A |
| trace_path | If "process" content | Yes | N/A |
| sequencing | If "process" content | Yes | N/A |
| description_matching | If label_descriptions available | Yes (warns if no DK) | N/A |
| sorting_categories | If content matches | Yes | N/A |
| memory_match | If content matches | Yes | N/A |
| branching_scenario | If content matches | Misleading (says ready) | N/A |
| compare_contrast | If "comparison" content | Misleading (says ready) | N/A |

---

## 3. scene_architect_tools.py

### Tool Function Inventory

| # | Tool | Type | What It Does |
|---|------|------|--------------|
| 1 | `get_zone_layout_guidance` | LLM | Spatial position hints per label |
| 2 | `get_mechanic_config_schema` | Deterministic | Returns INTERACTION_PATTERNS config for a mechanic type |
| 3 | `generate_mechanic_content` | LLM + DK | **Key tool**: generates per-mechanic config data |
| 4 | `validate_scene_spec` | Deterministic | SceneSpecV3 validation + cross-check vs game_design |
| 5 | `submit_scene_specs` | Pydantic gate | Final submission with SceneSpecV3 validation |

### generate_mechanic_content -- Per-Mechanic Audit (Lines 149-461)

This is the most critical tool for mechanic support. Here is what each mechanic gets:

#### drag_drop (Lines 444-450)
```python
result["config"] = {
    "shuffle_labels": True,
    "show_hints": True,
    "max_attempts": 3,
}
```
**Assessment**: ADEQUATE. Drag-drop is simple -- it only needs zone coordinates and labels, which come from assets. The config is minimal by design.

**MISSING**: No leader line config, no zone shape preferences, no label styles, no snap animation config. These are all frontend presentation concerns but the game_design schema (GameDesignV3.MechanicDesign) has no fields for them. The frontend hardcodes them.

#### click_to_identify (Lines 217-230)
```python
prompts = []
for label in zone_labels:
    desc = label_descriptions.get(label, "")
    if desc:
        prompts.append(f"Click on the structure that {desc.lower().rstrip('.')}")
    else:
        prompts.append(f"Click on the {label}")
result["config"] = {
    "prompt_style": "description" if label_descriptions else "name",
    "highlight_on_hover": True,
    "prompts": prompts,
}
```
**Assessment**: FUNCTIONAL but limited.

**GOOD**: Uses label_descriptions to generate functional prompts (not just "Click on X").
**MISSING**:
- No magnification config (zoom level, viewport behavior on hover)
- No zone highlight styles (color, opacity, border type)
- No selection_mode config (sequential vs any_order -- the ClickDesign schema has this but it's not populated)
- No correct_assignments mapping (which prompt maps to which zone)
- Prompts are string[] but frontend IdentificationPrompt expects `{zoneId, prompt, order}` -- this is fixed in blueprint_assembler but the raw config is incomplete

#### trace_path (Lines 182-214)
**Two paths**:
1. If `sequence_flow_data` exists: uses `sequence_items` for waypoints
2. LLM fallback: generates waypoints from zone labels

```python
result["config"] = {
    "waypoints": waypoints,
    "path_type": ...,  # linear|cyclic|branching
    "drawing_mode": "click_waypoints",
}
```
**Assessment**: PARTIALLY FUNCTIONAL.

**GOOD**: Waypoints are generated, path_type detected.
**MISSING**:
- No SVG path definitions (curve data, control points)
- No animated particle config (speed, size, color)
- No color transition config (e.g., blue-to-red gradient along path)
- No visual_style field (the PathDesign schema has it but it's not populated)
- `drawing_mode` is set to "click_waypoints" but the frontend TracePath component expects different interaction modes and this value may not be consumed
- No waypoint descriptions or labels for educational context along the path

#### sequencing (Lines 233-271)
**Two paths**:
1. If `sequence_flow_data` exists: uses items with id/text/description + correct_order
2. LLM fallback: generates items from zone labels

```python
result["config"] = {
    "sequence_type": "linear",
    "items": items,  # [{id, text, description}]
    "correct_order": correct_order,  # [id1, id2, ...]
}
```
**Assessment**: FUNCTIONAL but incomplete.

**GOOD**: Items and correct_order generated with descriptions.
**MISSING**:
- No per-item illustrations/images (the schema allows it but no tool generates them)
- No layout config (vertical list? horizontal? grid? drag-to-reorder?)
- No `instruction_text` (the SequenceDesign schema has it but it's not populated by this tool)
- No visual indicators for step connections

#### sorting_categories (Lines 274-325)
**Two paths**:
1. If `comparison_data.sorting_categories` exists: maps groups to categories + items
2. LLM fallback: generates categories + items from zone labels

```python
result["config"] = {
    "categories": categories,  # [{id, name, ...}]
    "items": items,  # [{id, text, correct_category}]
    "show_category_hints": True,
}
```
**Assessment**: FUNCTIONAL but incomplete.

**GOOD**: Categories and items generated with correct mappings.
**MISSING**:
- No category icons/colors/illustrations
- No per-item illustrations
- No sort mode config (bucket/venn/matrix -- the frontend supports multiple but config doesn't specify)
- No `instruction_text`
- Category matching logic (lines 282-288) is fragile -- uses case-insensitive substring matching which can fail on multi-word category names

#### description_matching (Lines 328-364)
**Two paths**:
1. If `label_descriptions` exists: builds `[{zone_label, description}]` from DK
2. LLM fallback: generates functional descriptions per label

```python
result["config"] = {
    "mode": "match_to_zone",
    "descriptions": descriptions,  # [{zone_label, description}]
}
```
**Assessment**: FUNCTIONAL but incomplete.

**GOOD**: Uses real label descriptions from domain knowledge.
**MISSING**:
- No distractor descriptions (false descriptions that don't match any zone)
- No matching modes config (click_zone, drag_description, multiple_choice -- the DescriptionMatchDesign schema supports these via `sub_mode` but this tool only outputs "match_to_zone")
- No `instruction_text`

#### memory_match (Lines 367-380)
```python
pairs = []
for label in zone_labels[:10]:
    desc = label_descriptions.get(label, f"A part of the {question[:30]}...")
    pairs.append({"front": label, "back": desc})
# ...
result["config"] = {
    "pairs": pairs,  # [{front, back}]
    "grid_size": [rows, cols],
    "flip_duration_ms": 600,
}
```
**Assessment**: MINIMAL.

**GOOD**: Pairs generated from labels+descriptions, grid calculated.
**MISSING**:
- No per-card images (front or back could be images -- MemoryMatchDesign allows `front_type`/`back_type` but only text is generated)
- No image generation for card faces
- Fallback description is generic: `f"A part of the {question[:30]}..."` -- useless for actual memory matching
- No difficulty variation (e.g., easier pairs revealed first)
- No `instruction_text`
- No card styling config

#### compare_contrast (Lines 383-396)
```python
if comparison_data:
    expected_categories = {}
    for group in comparison_data.get("groups", []):
        group_name = group.get("group_name", "")
        for member in group.get("members", []):
            expected_categories[member] = group_name
    result["config"] = {
        "expected_categories": expected_categories,
        "highlight_matching": True,
        "similarities": comparison_data.get("similarities", []),
        "differences": comparison_data.get("differences", []),
    }
```
**Assessment**: WEAK. Only works if comparison_data exists.

**GOOD**: Uses real comparison data when available.
**CRITICAL MISSING**:
- **No dual-diagram generation**. The CompareDesign schema has `diagram_a_description` / `diagram_b_description` fields but this tool doesn't generate them. The asset_generator only handles single diagrams.
- No zone pairings (which zone on diagram A corresponds to which zone on diagram B)
- No LLM fallback (unlike all other mechanics, if comparison_data is missing, this mechanic produces nothing -- `result["generated"]` stays False)
- No `instruction_text`

#### branching_scenario (Lines 399-441)
```python
# LLM-only generation (no upstream data)
llm_result = await llm.generate_json(prompt, ...)
result["config"] = {
    "nodes": llm_result["nodes"],
    "startNodeId": llm_result.get("startNodeId", "start"),
    "show_path_taken": True,
    "allow_backtrack": True,
}
```
**Assessment**: PARTIALLY FUNCTIONAL.

**GOOD**: LLM generates a decision tree with nodes, options, consequences.
**MISSING**:
- No scene backgrounds for each decision node
- No character sprites
- No state variables (the BranchingDesign schema has `state_variables` concept but nothing generates them)
- No validation that generated nodes form a valid DAG (could have cycles or orphaned nodes)
- No `show_consequences` forwarded from BranchingDesign schema
- No `multiple_valid_endings` config

### Cross-validation (validate_scene_spec, submit_scene_specs)

**Good**: The `validate_scene_specs()` function in `scene_spec_v3.py` (lines 270-330) checks per-mechanic data requirements:
- trace_path needs path_config.waypoints
- click_to_identify needs click_config with prompts or click_options
- sequencing needs sequence_config.correct_order
- description_matching needs description_match_config.descriptions
- sorting_categories needs sorting_config with categories AND items
- branching_scenario needs branching_config.nodes
- memory_match needs memory_config.pairs

**Gap**: No validation for compare_contrast needing dual diagrams or zone pairings.

---

## 4. interaction_designer_tools.py

### Tool Function Inventory

| # | Tool | Type | What It Does |
|---|------|------|--------------|
| 1 | `get_scoring_templates` | Deterministic | Scoring strategy per mechanic + difficulty |
| 2 | `generate_misconception_feedback` | LLM | Per-label misconception triggers with messages |
| 3 | `enrich_mechanic_content` | LLM | Scoring rationale, feedback, misconceptions per mechanic |
| 4 | `validate_interactions` | Deterministic | InteractionSpecV3 validation + cross-check |
| 5 | `submit_interaction_specs` | Pydantic gate | Final submission |

### Per-Mechanic Audit

#### get_scoring_templates (Lines 25-106)

**Well-implemented**: `mechanic_strategy_map` (lines 75-87) maps all 9 mechanics + hierarchical + timed to scoring strategies:

| Mechanic | Strategy |
|----------|----------|
| drag_drop | standard |
| click_to_identify | standard |
| trace_path | progressive |
| sequencing | progressive |
| sorting_categories | standard |
| memory_match | time_based |
| branching_scenario | mastery |
| compare_contrast | mastery |
| description_matching | standard |

**Assessment**: COMPLETE for all 9 mechanics. No gaps.

#### generate_misconception_feedback (Lines 113-211)

**Good**: LLM generates per-label misconception triggers. Deterministic fallback generates basic confusability feedback.

**Gap**: This is drag_drop/click_to_identify-focused (trigger_label placed on wrong zone). For other mechanics:
- **sequencing**: Misconceptions should be about ORDER (step A comes before step B), not placement
- **sorting_categories**: Misconceptions should be about CATEGORIZATION (item X belongs in category Y, not Z)
- **branching_scenario**: Misconceptions should be about DECISION consequences
- **memory_match**: Misconceptions about ASSOCIATION (why term X matches definition Y)
- **compare_contrast**: Misconceptions about SIMILARITY/DIFFERENCE classification

The tool produces generic misconceptions that may not fit the mechanic's interaction model.

#### enrich_mechanic_content (Lines 218-350)

**Assessment**: Generic LLM enrichment that works for all mechanics but has no mechanic-specific prompting beyond a brief hint in lines 308:
```python
f"For {mechanic_type}, consider: {'the order of steps...' if mechanic_type in ('sequencing', 'trace_path') else ...}"
```

**Gap**: The enrichment is purely about scoring/feedback/misconceptions. It does NOT enrich the mechanic's structural content (e.g., it won't add SVG paths for trace_path, or grid layout for memory_match, or sort mode for sorting). This tool adds behavioral layer but NOT structural layer.

#### validate_interactions (Lines 357-454)

**Good cross-checks**:
- Every mechanic has scoring (line 419)
- Every mechanic has feedback (line 425)
- Multi-mechanic scenes need mode_transitions (line 429)
- Distractor feedback if design has distractors (line 443)

**Gap**: No validation of mechanic-specific interaction content. Only checks presence, not correctness.

#### Mechanic-Aware Validation (interaction_spec_v3.py, Lines 243-309)

The `validate_interaction_specs()` function has mechanic-aware trigger validation (lines 245-261) and content presence checks (lines 263-309):
- click_to_identify: checks feedback is not generic defaults
- description_matching: checks feedback entry exists
- trace_path: checks misconception_feedback exists
- sequencing: checks misconception_feedback exists

**Missing checks**:
- memory_match: no content checks
- branching_scenario: no content checks
- compare_contrast: no content checks
- sorting_categories: no content checks

---

## 5. asset_generator_tools.py

### Tool Function Inventory

| # | Tool | Type | What It Does |
|---|------|------|--------------|
| 1 | `search_diagram_image` | Web search + Gemini | Searches web for diagram, auto-generates clean version |
| 2 | `generate_diagram_image` | Gemini Imagen | Generates diagram image with mechanic-aware prompts |
| 3 | `detect_zones` | Gemini/SAM3/Qwen | Detects interactive zones in diagram image |
| 4 | `generate_animation_css` | Deterministic | CSS keyframe animations (pulse, shake, confetti, etc.) |
| 5 | `submit_assets` | Validation gate | Validates per-scene asset bundles |

### Critical Architecture Analysis

**This entire file is 100% single-diagram-focused.** Every tool assumes:
- One diagram per scene
- Zones are regions ON that diagram
- Assets = diagram image + zone coordinates

### What Each Mechanic Actually Needs (vs. What This File Provides)

| Mechanic | Assets Needed | What This File Provides | Gap |
|----------|-------------|----------------------|-----|
| drag_drop | Diagram + zones | Diagram + zones | NONE |
| click_to_identify | Diagram + zones (+ magnification viewport) | Diagram + zones | Magnification missing |
| trace_path | Diagram + zones + SVG path overlays | Diagram + zones | SVG paths missing |
| sequencing | Per-item illustrations + diagram (optional) | Diagram only | Per-item illustrations missing |
| description_matching | Diagram + zones | Diagram + zones | NONE (descriptions come from DK) |
| sorting_categories | Per-item illustrations + category icons | Diagram only | Per-item illustrations + icons missing |
| memory_match | Per-card images (front & back) + card grid | Diagram only | Card images missing entirely |
| branching_scenario | Scene backgrounds + character sprites | Diagram only | Scene backgrounds + sprites missing |
| compare_contrast | TWO matched diagrams + zones on BOTH | Single diagram only | **CRITICAL: dual-diagram missing** |

### Mechanic-Aware Image Generation (Lines 229-281)

**Good feature**: `_MECHANIC_IMAGE_HINTS` dict provides per-mechanic prompt additions for image generation. All 9 mechanics + hierarchical have entries. These hints tell Gemini Imagen HOW to render the diagram for each mechanic.

**But**: The hints only affect the SINGLE diagram's visual style. They don't cause generation of additional assets (item illustrations, card faces, scene backgrounds, dual diagrams).

### submit_assets Validation (Lines 879-1050)

**Good**: Has mechanic-aware warnings (lines 978-1029):
- trace_path: checks waypoint labels exist in zones
- click_to_identify: checks for overlapping zones (clickability)
- sorting_categories: checks categories defined

**Missing validations**:
- No check for compare_contrast needing two diagrams
- No check for memory_match needing card images
- No check for branching_scenario needing scene backgrounds
- No check for sequencing needing per-item assets

### Missing Tools Needed in asset_generator_tools.py

1. **`generate_item_illustration`** -- Generate small illustration for a sequencing step, sorting item, or memory card. Should use Gemini Imagen with size constraints (e.g., 256x256). Input: item text, context. Output: image path.

2. **`generate_dual_diagram`** -- Generate two matched diagrams for compare_contrast. Input: descriptions for diagram A and B, required elements for each. Output: two image paths.

3. **`generate_scene_background`** -- Generate a background scene for branching_scenario nodes. Input: scenario description, mood. Output: image path.

4. **`generate_card_image`** -- Generate an image for a memory_match card face. Input: term/concept, style. Output: image path.

5. **`generate_category_icon`** -- Generate a small icon for a sorting category. Input: category name. Output: image path/SVG.

---

## 6. blueprint_assembler_tools.py

### Tool Function Inventory

| # | Tool | Type | What It Does |
|---|------|------|--------------|
| 1 | `assemble_blueprint` | Deterministic + context | Assembles full blueprint from all upstream state |
| 2 | `validate_blueprint` | Deterministic | Frontend compatibility checks |
| 3 | `repair_blueprint` | Deterministic | Auto-repair common issues |
| 4 | `submit_blueprint` | Validation gate | Final submission with essential checks |

### assemble_blueprint -- Per-Mechanic Config Assembly (Lines 557-763)

This is where mechanic configs are transformed from backend format to frontend format. Here is what each mechanic gets:

#### drag_drop
No special config assembly. Uses zones + labels + scoring/feedback. **COMPLETE**.

#### trace_path (Lines 572-587)
```python
if mech_type == "trace_path":
    waypoints = mech_cfg.get("waypoints", [])
    if waypoints:
        path_waypoints = []
        for idx, wp in enumerate(waypoints):
            wp_zone_id = _make_id("zone", str(scene_number), wp)
            path_waypoints.append({"zoneId": wp_zone_id, "order": idx})
        mech_entry["paths"] = [{
            "id": _make_id("path", str(scene_number)),
            "waypoints": path_waypoints,
            "description": mech_cfg.get("description", "Trace the path through the structures"),
            "requiresOrder": mech_cfg.get("requires_order", True),
        }]
```
**Assessment**: Waypoints converted to `{zoneId, order}` format. Frontend path object has `id`, `waypoints`, `description`, `requiresOrder`.

**MISSING**: No SVG path data (curves, control points). No animated particle config. No color transition config. The frontend TracePath component likely needs more than just waypoint zone IDs to render a visual path.

#### click_to_identify (Lines 591-623)
```python
elif mech_type == "click_to_identify":
    # Converts string prompts to [{zoneId, prompt, order}]
    # Matches prompts to zones by label substring matching
```
**Assessment**: GOOD. Normalizes prompts to frontend `IdentificationPrompt` format with zoneId matching.

**MISSING**: No magnification/zoom config forwarded. No highlight style config.

#### sequencing (Lines 627-638)
```python
elif mech_type == "sequencing":
    mech_entry["sequenceConfig"] = {
        "sequenceType": mech_cfg.get("sequence_type", "linear"),
        "items": items,
        "correctOrder": correct_order,
        "instructionText": instr_text,
        "instructions": instr_text,  # Dual key for compat
    }
```
**Assessment**: FUNCTIONAL. Correct shape for frontend.

**MISSING**: No per-item image URLs. No layout mode config. Items are `{id, text, description}` but frontend may need `{id, text, description, imageUrl}`.

#### description_matching (Lines 642-670)
```python
elif mech_type == "description_matching":
    # Converts [{zone_label, description}] list to {zoneId: description} dict
    mech_entry["descriptionMatchingConfig"] = {
        "mode": mode,  # click_zone|drag_description|multiple_choice
        "descriptions": descriptions_dict,  # {zoneId: description}
        "instructions": instr_text,
    }
```
**Assessment**: GOOD. Properly converts label-keyed descriptions to zoneId-keyed. Validates mode against valid enum.

**MISSING**: No distractor descriptions in config. The frontend likely needs some false descriptions to make matching non-trivial.

#### sorting_categories (Lines 674-711)
```python
elif mech_type == "sorting_categories":
    # Normalizes categories: {id, label, description, color}
    # Normalizes items: {id, text, correctCategoryId, description}
    mech_entry["sortingConfig"] = {
        "categories": norm_categories,
        "items": norm_items,
        "showCategoryHints": ...,
        "allowPartialCredit": ...,
        "instructionText": instr_text,
        "instructions": instr_text,
    }
```
**Assessment**: GOOD. Proper normalization of categories and items.

**MISSING**: No sort mode (bucket/venn/matrix). No category icons/images. No per-item illustrations.

#### memory_match (Lines 715-736)
```python
elif mech_type == "memory_match":
    # Normalizes pairs: {id, front, back, frontType, backType}
    mech_entry["memoryMatchConfig"] = {
        "pairs": norm_pairs,
        "gridSize": mech_cfg.get("grid_size"),
        "flipDurationMs": ...,
        "showAttemptsCounter": ...,
        "instructionText": instr_text,
        "instructions": instr_text,
    }
```
**Assessment**: FUNCTIONAL. Good normalization with frontType/backType support.

**MISSING**: frontType/backType will always be "text" because no tool generates card images. The schema supports `"image"` type but no upstream tool produces image URLs for cards.

#### branching_scenario (Lines 739-750)
```python
elif mech_type == "branching_scenario":
    mech_entry["branchingConfig"] = {
        "nodes": nodes,
        "startNodeId": ...,
        "showPathTaken": ...,
        "allowBacktrack": ...,
        "showConsequences": ...,
        "instructions": instr_text,
    }
```
**Assessment**: FUNCTIONAL. Forwards LLM-generated decision tree.

**MISSING**: No scene background images per node. No character sprite URLs. No state variables. Node structure depends entirely on LLM output quality.

#### compare_contrast (Lines 753-761)
```python
elif mech_type == "compare_contrast":
    mech_entry["compareConfig"] = {
        "expectedCategories": expected,  # {zone_label: category}
        "highlightMatching": ...,
        "instructions": instr_text,
    }
```
**Assessment**: MINIMAL.

**CRITICAL MISSING**:
- No dual diagram references (diagramA, diagramB)
- No zone pairings (which zone on A matches which zone on B)
- Only `expectedCategories` is forwarded -- this tells the frontend which category each zone belongs to, but the frontend needs two separate sets of zones on two separate diagrams

### validate_blueprint -- Mechanic-Specific Checks (Lines 1131-1177)

**Checks implemented**:
- trace_path: warns if no `paths` or `waypoints`
- click_to_identify: warns if no `identificationPrompts`
- sequencing: ERROR if no `correctOrder`
- description_matching: warns if no `descriptions`
- sorting_categories: ERROR if no `categories`
- All mechanics: warns if no `scoring`

**Missing checks**:
- memory_match: no check for pairs
- branching_scenario: no check for nodes
- compare_contrast: no check for dual diagrams or zone pairings

### repair_blueprint -- Mechanic-Specific Repairs (Lines 1403-1461)

**Repairs implemented**:
- click_to_identify: generates prompts if missing
- trace_path: builds paths from waypoints if missing
- All mechanics: adds default scoring if missing

**Missing repairs**:
- sequencing: no repair for missing items/correctOrder
- description_matching: no repair for missing descriptions
- sorting_categories: no repair for missing categories/items
- memory_match: no repair for missing pairs
- branching_scenario: no repair for missing nodes
- compare_contrast: no repair at all

---

## 7. Cross-Tool Data Flow Analysis

### Data Flow Per Mechanic

```
DomainKnowledgeRetriever
  |-- canonical_labels          --> ALL mechanics
  |-- label_descriptions        --> click_to_identify, description_matching, memory_match
  |-- sequence_flow_data        --> trace_path, sequencing
  |-- comparison_data           --> sorting_categories, compare_contrast
  |-- hierarchical_relationships --> hierarchy (modifier)

v3_context.py promotes these 5 fields for tool access.

game_design_v3_tools:
  analyze_pedagogy -> recommended_patterns (biased toward drag_drop)
  check_capabilities -> data availability per mechanic

scene_architect_tools:
  generate_mechanic_content -> per-mechanic config
    - trace_path: waypoints, path_type
    - click_to_identify: prompts, prompt_style
    - sequencing: items, correct_order
    - sorting_categories: categories, items
    - description_matching: descriptions, mode
    - memory_match: pairs, grid_size
    - compare_contrast: expected_categories (IF comparison_data exists)
    - branching_scenario: nodes, startNodeId (LLM-only)
    - drag_drop: shuffle_labels, show_hints

interaction_designer_tools:
  get_scoring_templates -> scoring strategy per mechanic
  generate_misconception_feedback -> misconception triggers (drag_drop-biased)
  enrich_mechanic_content -> scoring rationale, feedback, misconceptions

asset_generator_tools:
  search_diagram_image -> single diagram (for ALL mechanics)
  generate_diagram_image -> single diagram (mechanic-aware prompts)
  detect_zones -> zone coordinates
  NO per-item/per-card/dual-diagram generation

blueprint_assembler_tools:
  assemble_blueprint -> transforms configs to frontend format
    - All 9 mechanics have config assembly code
    - BUT relies on upstream tools having generated the data
```

### Critical Data Flow Gaps

1. **compare_contrast has no dual-diagram path**: There is no tool that generates two matched diagrams. The asset_generator only generates one. The blueprint_assembler's compareConfig has no diagram references.

2. **memory_match has no image path**: The memory_match config supports `frontType: "image"` and `backType: "image"` but no tool generates card images. All pairs are text-only.

3. **branching_scenario has no visual assets**: Decision nodes are text-only. No scene backgrounds, no character illustrations. The frontend branching component may render as a text adventure with no visual context.

4. **sequencing has no item illustrations**: Items are `{id, text, description}` only. No images for visual steps.

5. **sorting_categories has no category/item visuals**: No icons for categories, no illustrations for items. Pure text sorting.

6. **comparison_data generation is conditional**: The DomainKnowledgeRetriever only generates comparison_data if the question contains comparison keywords. For a question like "Classify these elements", comparison_data may be empty, leaving sorting_categories and compare_contrast without upstream data.

7. **sequence_flow_data generation is conditional**: Only generated if the question contains process/flow keywords. Sequencing and trace_path fall back to LLM generation.

---

## 8. Master Coverage Matrix

### Per-Stage Coverage (What Each Tool File Actually Generates Per Mechanic)

| Mechanic | Game Design | Scene Architect | Interaction Designer | Asset Generator | Blueprint Assembler |
|----------|------------|-----------------|---------------------|----------------|-------------------|
| **drag_drop** | Recommends (forced) | Config: shuffle, hints | Scoring: standard | Diagram + zones | Labels + zones assembled |
| **click_to_identify** | Recommends if match | Config: prompts | Scoring: standard | Diagram + zones | identificationPrompts assembled |
| **trace_path** | Recommends if process | Config: waypoints, path_type | Scoring: progressive | Diagram + zones | paths[] assembled |
| **sequencing** | Recommends if process | Config: items, correct_order | Scoring: progressive | Diagram + zones | sequenceConfig assembled |
| **description_matching** | Recommends if DK | Config: descriptions, mode | Scoring: standard | Diagram + zones | descriptionMatchingConfig assembled |
| **sorting_categories** | Recommends if match | Config: categories, items | Scoring: standard | Diagram + zones | sortingConfig assembled |
| **memory_match** | Recommends if match | Config: pairs, grid_size | Scoring: time_based | Diagram + zones | memoryMatchConfig assembled |
| **branching_scenario** | Recommends if match | Config: nodes (LLM) | Scoring: mastery | Diagram + zones | branchingConfig assembled |
| **compare_contrast** | Recommends if comparison | Config: expected_categories (IF data) | Scoring: mastery | Diagram + zones (SINGLE) | compareConfig assembled (NO dual diagram) |

### Missing Data Per Mechanic

| Mechanic | Missing From Pipeline |
|----------|----------------------|
| drag_drop | Leader lines, zone shapes, snap animation config |
| click_to_identify | Magnification config, zone highlight styles, selection_mode |
| trace_path | SVG path definitions, waypoint animations, color transitions, animated particles |
| sequencing | Per-item illustrations, layout config (vertical/horizontal/grid) |
| description_matching | Distractor descriptions, multiple matching modes |
| sorting_categories | Category icons, per-item illustrations, sort mode (bucket/venn/matrix) |
| memory_match | Per-card images, card styling, difficulty progression |
| branching_scenario | Scene backgrounds, character sprites, state variables, DAG validation |
| compare_contrast | **DUAL DIAGRAMS**, zone pairings, matched zone highlighting |

---

## 9. Missing Tools Needed

### Priority 1: Critical for mechanic functionality

| Tool | File | Purpose | Mechanic(s) |
|------|------|---------|-------------|
| `generate_dual_diagram` | asset_generator_tools.py | Generate two matched diagrams for comparison | compare_contrast |
| `generate_item_illustration` | asset_generator_tools.py | Generate small illustration for a content item | sequencing, sorting_categories, memory_match |
| `generate_card_image` | asset_generator_tools.py | Generate image for memory card face | memory_match |

### Priority 2: Improves mechanic quality

| Tool | File | Purpose | Mechanic(s) |
|------|------|---------|-------------|
| `generate_svg_path` | scene_architect_tools.py or asset_generator_tools.py | Generate SVG path data (curves, control points) between waypoints | trace_path |
| `generate_distractor_descriptions` | scene_architect_tools.py | Generate false descriptions that don't match any zone | description_matching |
| `generate_scene_background` | asset_generator_tools.py | Generate contextual background image for branching node | branching_scenario |
| `validate_decision_tree` | scene_architect_tools.py | Validate branching nodes form a valid DAG with reachable endings | branching_scenario |

### Priority 3: Polish

| Tool | File | Purpose | Mechanic(s) |
|------|------|---------|-------------|
| `generate_category_icon` | asset_generator_tools.py | Generate small icon/badge for sorting category | sorting_categories |
| `generate_zone_highlight_style` | scene_architect_tools.py | Generate per-zone highlight colors/styles | click_to_identify |
| `generate_path_animation_config` | scene_architect_tools.py | Generate animated particle config for path traversal | trace_path |

---

## 10. Priority Fix List

### Tier 1: Breaking Issues (mechanic will not function correctly)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| T1-1 | compare_contrast has NO dual-diagram support anywhere in asset pipeline | asset_generator_tools.py | entire file | Add `generate_dual_diagram` tool; update `submit_assets` to validate two diagrams per scene for compare_contrast |
| T1-2 | compare_contrast LLM fallback missing -- if no comparison_data, mechanic generates NOTHING | scene_architect_tools.py | 383-396 | Add LLM fallback like all other mechanics |
| T1-3 | analyze_pedagogy forces drag_drop as baseline for EVERY game | game_design_v3_tools.py | 108-111 | Remove force-insertion; let agent decide |
| T1-4 | misconception feedback is drag_drop-biased (trigger_label + trigger_zone model) | interaction_designer_tools.py | 140-170 | Add mechanic-specific misconception prompt templates |

### Tier 2: Degraded Experience (mechanic works but with poor quality)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| T2-1 | memory_match pairs use generic fallback description when no label_descriptions | scene_architect_tools.py | 370 | Use LLM to generate meaningful descriptions for each label |
| T2-2 | trace_path has no SVG path data -- frontend can only show waypoint dots, not curves | scene_architect_tools.py | 182-214 | Add SVG path generation (cubic bezier between zone centers) |
| T2-3 | description_matching has no distractor descriptions | scene_architect_tools.py | 328-364 | Generate 2-3 false descriptions via LLM |
| T2-4 | sorting_categories has no sort mode config (defaults to generic) | scene_architect_tools.py | 274-325 | Detect appropriate sort mode from content type |
| T2-5 | branching_scenario nodes not validated as valid DAG | scene_architect_tools.py | 399-441 | Add post-generation validation (reachability, no orphans) |
| T2-6 | sequencing has no instruction_text from generate_mechanic_content | scene_architect_tools.py | 233-271 | Add `instruction_text` to config output |
| T2-7 | validate_blueprint missing checks for memory_match pairs and branching nodes | blueprint_assembler_tools.py | 1131-1177 | Add validation for these mechanics |
| T2-8 | repair_blueprint has no repairs for sequencing/memory_match/branching/sorting | blueprint_assembler_tools.py | 1403-1461 | Add auto-repair using scene_spec data |
| T2-9 | check_capabilities says branching_scenario is "ready" but it needs complex LLM gen | game_design_v3_tools.py | 237 | Update readiness_note to reflect LLM dependency |

### Tier 3: Missing Visual Assets (mechanic works but text-only)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| T3-1 | No per-item illustration generation for sequencing/sorting items | asset_generator_tools.py | N/A | New tool: `generate_item_illustration` using Gemini Imagen |
| T3-2 | No card image generation for memory_match | asset_generator_tools.py | N/A | New tool: `generate_card_image` using Gemini Imagen |
| T3-3 | No scene background generation for branching_scenario | asset_generator_tools.py | N/A | New tool: `generate_scene_background` using Gemini Imagen |
| T3-4 | No category icon generation for sorting_categories | asset_generator_tools.py | N/A | New tool: `generate_category_icon` (could be SVG or Gemini) |

### Tier 4: Configuration Gaps (cosmetic/interaction quality)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| T4-1 | click_to_identify has no magnification/zoom config | scene_architect_tools.py | 217-230 | Add magnification_enabled, zoom_level to config |
| T4-2 | trace_path has no color transition or particle animation config | scene_architect_tools.py | 182-214 | Add visual_style, particle_config to output |
| T4-3 | drag_drop has no leader line or label style config | scene_architect_tools.py | 444-450 | Add leader_lines, label_style to config |
| T4-4 | memory_match has no card styling or flip animation config beyond duration | scene_architect_tools.py | 367-380 | Add card_style, flip_animation to config |
| T4-5 | sequencing has no layout mode config (vertical/horizontal/grid) | scene_architect_tools.py | 233-271 | Add layout_mode to config |

---

## Appendix: File Paths Audited

1. `/Users/shivenagarwal/GamifyAssessment/backend/app/tools/game_design_v3_tools.py` (717 lines)
2. `/Users/shivenagarwal/GamifyAssessment/backend/app/tools/scene_architect_tools.py` (768 lines)
3. `/Users/shivenagarwal/GamifyAssessment/backend/app/tools/interaction_designer_tools.py` (691 lines)
4. `/Users/shivenagarwal/GamifyAssessment/backend/app/tools/asset_generator_tools.py` (1241 lines)
5. `/Users/shivenagarwal/GamifyAssessment/backend/app/tools/blueprint_assembler_tools.py` (1698 lines)
6. `/Users/shivenagarwal/GamifyAssessment/backend/app/tools/v3_context.py` (56 lines)
7. `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/game_design_v3.py` (1001 lines)
8. `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/scene_spec_v3.py` (336 lines)
9. `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/interaction_spec_v3.py` (342 lines)
