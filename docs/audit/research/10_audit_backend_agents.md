# V3 Backend Agents Audit Against Research Findings

**Date**: 2026-02-11
**Scope**: All 9 V3 pipeline agents audited against mechanic-specific research documents (01-05, 08)
**Methodology**: Full code read of each agent file, cross-referenced against research-defined requirements

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Audit Principles](#2-audit-principles)
3. [game_designer_v3.py](#3-game_designer_v3py)
4. [scene_architect_v3.py](#4-scene_architect_v3py)
5. [interaction_designer_v3.py](#5-interaction_designer_v3py)
6. [asset_generator_v3.py](#6-asset_generator_v3py)
7. [blueprint_assembler_v3.py](#7-blueprint_assembler_v3py)
8. [design_validator.py](#8-design_validatorpy)
9. [scene_validator.py](#9-scene_validatorpy)
10. [interaction_validator.py](#10-interaction_validatorpy)
11. [react_base.py](#11-react_basepy)
12. [Cross-Cutting Gaps](#12-cross-cutting-gaps)
13. [Schema Gap Matrix](#13-schema-gap-matrix)
14. [Prioritized Fix List](#14-prioritized-fix-list)

---

## 1. Executive Summary

The V3 pipeline has **5 critical cross-cutting gaps** that prevent all non-drag_drop mechanics from functioning at research-defined quality levels:

1. **Bloom's taxonomy leakage** -- game_designer_v3 injects `blooms_level` into task prompts, interaction_validator uses Bloom's mapping for learning alignment. Both violate the principle that Bloom's should NOT drive mechanic selection.

2. **drag_drop bias** -- interaction_validator `auto_fix_design` defaults unknown modes to `drag_drop` (L350). Asset generator system prompt is 100% zone-detection focused (single-image workflow), which is only relevant for drag_drop-like mechanics.

3. **Missing mechanic config schemas** -- Current `*Design` schemas have 3-5 fields per mechanic; research defines 10-25 fields per mechanic. The game designer outputs `SlimMechanicRef` with only `type: str`, so no mechanic-specific config flows through Phase 1 at all.

4. **Agent system prompts lack per-mechanic guidance** -- Scene architect system prompt covers 7/9 mechanics (missing memory_match, branching_scenario, compare_contrast config guidelines). Interaction designer system prompt is completely generic. Asset generator has zero mechanic awareness.

5. **Blueprint assembler config dropping** -- `_assemble_mechanics` (L172-209) only extracts `path_config`, `click_config`, `sequence_config` -- misses sorting, branching, compare, memory, description_match, timed configs. Legacy assembler never populates frontend-specific fields.

**Total gaps identified**: 87 across 9 agents (26 CRITICAL, 31 HIGH, 30 MEDIUM)

---

## 2. Audit Principles

These principles were mandated for this audit and govern all findings:

| Principle | Description |
|-----------|-------------|
| **No Bloom's for mechanic selection** | Bloom's taxonomy should NOT drive which mechanic is chosen. Mechanic selection should be based on content context, domain knowledge signals, and pedagogical fit -- not cognitive level mapping. |
| **Equal mechanic support** | Every mechanic must receive equal implementation effort. No drag_drop bias in defaults, fallbacks, or system prompts. |
| **Mechanic-general agents, mechanic-specific tools** | Agent system/task prompts should describe WHAT to produce generically. Per-mechanic logic (config schemas, generation strategies, validation rules) should live in tools that agents call. |

---

## 3. game_designer_v3.py

**File**: `backend/app/agents/game_designer_v3.py`
**Role**: Phase 1 -- Transforms question into multi-scene game design
**Tools**: `analyze_pedagogy`, `check_capabilities`, `get_example_designs`, `validate_design`, `submit_game_design`

### 3.1 System Prompt Gaps

| ID | Severity | Gap | Research Requirement |
|----|----------|-----|---------------------|
| GD-SP-1 | **CRITICAL** | Mechanic config requirements section (L73-87) gives superficial 1-line guidance per mechanic. No mention of layout modes, game variants, sort modes, narrative structures, comparison modes. | Research defines 10-25 configurable properties per mechanic (e.g., sequencing: `layout_mode`, `interaction_pattern`, `reveal_mode`, `connector_style`; memory_match: `game_variant`, `card_face_type`, `match_type`; sorting: `sort_mode` with venn/matrix/column; branching: `narrative_structure` with 6 types; compare: `comparison_mode` with 5 types). |
| GD-SP-2 | HIGH | States "Pedagogical First: Every mechanic choice must serve a learning objective" but gives no framework for HOW to match content characteristics to mechanics. | Research defines content-to-mechanic mapping signals: sequence_flow_data -> sequencing, label_descriptions -> description_matching, comparison_data -> compare_contrast/sorting, process_steps -> trace_path, term-definition pairs -> memory_match. |
| GD-SP-3 | HIGH | Lists only 9 mechanics. No mention of 10 new mechanics from research (predict_observe_explain, spot_the_error, cloze_fill_blank, process_builder, cause_effect_chain, annotation_drawing, measurement_reading, elimination_grid, hotspot_multi_select, claim_evidence_reasoning). | Research doc 08 defines 10 additional mechanics covering cognitive skills not tested by existing 9. |
| GD-SP-4 | MEDIUM | Line 77: "drag_drop: Default mechanic. No special config needed from you." -- Implies drag_drop is the fallback, reinforcing bias. | All mechanics should be presented as equally viable choices. |
| GD-SP-5 | MEDIUM | No guidance on multi-mechanic scene composition. Research shows specific pairing patterns (e.g., sequencing+trace_path for process flows, compare_contrast+sorting for classification tasks). | Research docs 01-05 each define recommended mechanic pairings. |

### 3.2 Task Prompt Gaps

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| GD-TP-1 | **CRITICAL** | **Bloom's level injection** -- L131: `blooms_level = state.get("blooms_level", "understand")`, L142-143: injects as `## Bloom's Level` section. This violates the principle that Bloom's should NOT drive mechanic selection. | Remove `blooms_level` from task prompt entirely. Game designer should decide mechanics based on content signals from domain knowledge, not cognitive taxonomy levels. |
| GD-TP-2 | HIGH | L217: "Each mechanic only needs a 'type' field" -- Explicitly tells the agent NOT to produce mechanic-specific config. This means no layout_mode, game_variant, sort_mode, narrative_structure, etc. flows through Phase 1. | While downstream agents can generate configs, the game designer should at least specify high-level config choices (e.g., sort_mode="venn_2" vs "matrix") since these affect the fundamental game concept. |
| GD-TP-3 | MEDIUM | Domain knowledge injection (L153-167) only extracts 4 sub-fields: `sequence_flow_data`, `label_descriptions`, `comparison_data`, `content_characteristics`. Missing: `process_steps`, `term_definitions`, `causal_relationships`, `hierarchical_data`, `spatial_data`. | DK retriever produces richer data (13+ mechanic fields in schema) but game designer only reads 4. |
| GD-TP-4 | MEDIUM | L147: Domain knowledge truncated to 2000 chars. For complex topics with many labels, sequence data, and comparison data, this loses critical information. | Consider per-section truncation instead of global truncation. |

### 3.3 State Field Gaps

| Field | Status | Issue |
|-------|--------|-------|
| `blooms_level` | READ (L131) | Should NOT be read -- violates principle |
| `domain_knowledge` | READ (L132, L154) | Only 4 sub-fields extracted; missing 9+ mechanic-relevant sub-fields |
| `game_design_v3` | WRITTEN | Output uses `GameDesignV3Slim` which restricts mechanics to `SlimMechanicRef(type: str)` only -- no config fields |
| `content_characteristics` | READ (L165) | Read but not used to drive mechanic selection logic |

### 3.4 max_iterations Assessment

**Current**: 6
**Assessment**: ADEQUATE for single-scene games (analyze -> examples -> capabilities -> validate -> fix -> submit = 6 steps). TIGHT for multi-scene multi-mechanic games where validation may fail and require multiple fix cycles.
**Recommendation**: Increase to 8 to allow 2 retry cycles after validation failure.

### 3.5 parse_final_result Gaps

| ID | Severity | Gap |
|----|----------|-----|
| GD-PR-1 | MEDIUM | L223-317: Extracts from `submit_game_design` tool result or falls back to JSON extraction. Validates against `GameDesignV3Slim` schema. Since Slim only has `type: str` for mechanics, ANY mechanic-specific config the LLM might produce is silently dropped during Pydantic validation. |

### 3.6 Output Schema Gap

**Current `SlimMechanicRef`**:
```python
class SlimMechanicRef(BaseModel):
    type: str  # That's it -- nothing else
```

**What research requires** (examples):
- Sequencing: `layout_mode`, `interaction_pattern`, `item_count`
- Memory match: `game_variant`, `match_type`, `pair_count`
- Sorting: `sort_mode`, `container_count`
- Branching: `narrative_structure`, `node_count`
- Compare/contrast: `comparison_mode`, `comparison_type`

**Recommendation**: Add a `SlimMechanicConfig` with optional high-level config choices that the game designer specifies, while leaving detailed config generation to scene_architect_v3 tools.

---

## 4. scene_architect_v3.py

**File**: `backend/app/agents/scene_architect_v3.py`
**Role**: Phase 2 -- Creates per-scene zone layouts and mechanic configurations
**Tools**: `get_zone_layout_guidance`, `get_mechanic_config_schema`, `generate_mechanic_content`, `validate_scene_spec`, `submit_scene_specs`

### 4.1 System Prompt Gaps

| ID | Severity | Gap | Research Requirement |
|----|----------|-----|---------------------|
| SA-SP-1 | **CRITICAL** | Mechanic config guidelines (L67-75) cover only 7/9 mechanics. **Missing**: `memory_match`, `branching_scenario`, `compare_contrast` config guidelines entirely. | Memory_match needs: `game_variant`, `card_face_type`, `match_type`, `pairs` with front/back content types, explanations, difficulty. Branching needs: `narrative_structure`, `nodes` with choice quality spectrum, state_variables. Compare needs: `comparison_mode`, dual-image spec, zone_pairings. |
| SA-SP-2 | **CRITICAL** | Existing config guidelines are minimal (1-line key-value examples). No guidance on WHAT to populate or WHY. E.g., L73: `sequencing: config = {sequence_type: "linear", correct_order: [...label ids...]}` -- no mention of items with descriptions, layout modes, connector styles. | Research defines per-mechanic what each config field means and when to use each option (e.g., `layout_mode: "circular"` for cyclic processes, `"flowchart"` for branching processes). |
| SA-SP-3 | HIGH | No guidance on what `generate_mechanic_content` should produce per mechanic type. The tool exists but the system prompt says only "For non-drag_drop mechanics, generate populated config content (waypoints, prompts, descriptions, categories, etc.) from domain knowledge" (L49). | Each mechanic type needs specific generation guidance: sequencing -> ordered items with descriptions + images; sorting -> categories + items with multi-category support; memory_match -> pairs with front/back content; branching -> decision tree with consequences; compare -> dual-image zone pairings. |
| SA-SP-4 | HIGH | No mention of new mechanics from research doc 08. If game_designer selects a new mechanic type, scene_architect has zero guidance on how to handle it. | 10 new mechanics need config schema definitions and generation guidance. |
| SA-SP-5 | MEDIUM | Zone ID convention (L65: snake_case label) assumes all mechanics use zones. Branching_scenario uses decision nodes, not zones. Memory_match uses card pairs, not zones. Compare_contrast uses zone_pairings across two images, not single-image zones. | Zone-centric model breaks for mechanics that don't have spatial zones on a single diagram. |
| SA-SP-6 | MEDIUM | L69: "drag_drop: config = {shuffle_labels: true, show_hints: true, max_attempts: 3}" -- puts drag_drop first and gives it the most complete example, subtly biasing toward it. | Present all mechanics with equal completeness. |

### 4.2 Task Prompt Gaps

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| SA-TP-1 | HIGH | L101-200: Passes game design summary and labels but no domain knowledge sub-fields. Scene architect cannot generate rich mechanic content (sequence items, sorting categories, memory pairs, branching nodes) without access to domain knowledge. | Task prompt should inject `sequence_flow_data`, `label_descriptions`, `comparison_data`, `process_steps`, `term_definitions` from state domain_knowledge. |
| SA-TP-2 | MEDIUM | No injection of difficulty level for mechanic config scaling. Research defines per-mechanic difficulty parameters (e.g., sequencing: item_count scales 4-8 with difficulty; memory_match: pair_count scales 4-15; sorting: container_count scales 2-6). | Pass `difficulty` from game_design_v3 into task prompt. |

### 4.3 State Field Gaps

| Field | Status | Issue |
|-------|--------|-------|
| `domain_knowledge` | NOT READ | Scene architect does not access domain knowledge -- critical for generating mechanic content |
| `scene_specs_v3` | WRITTEN | Output uses `SceneSpecV3` with `MechanicConfigV3` which has typed config fields -- but the system prompt doesn't guide the LLM to populate them |
| `difficulty` | NOT READ | Not extracted from game_design_v3 for config scaling |

### 4.4 max_iterations Assessment

**Current**: 8
**Assessment**: ADEQUATE. Workflow is: (per scene) guidance -> schema -> content -> validate -> fix -> (repeat) -> submit. 8 iterations allows for multi-scene games with 1-2 validation retries.
**Recommendation**: Keep at 8.

### 4.5 parse_final_result Gaps

| ID | Severity | Gap |
|----|----------|-----|
| SA-PR-1 | HIGH | `MechanicConfigV3` has `_coerce_config()` that promotes generic `config` dict into typed fields. If the LLM puts mechanic config in the `config` dict (as the system prompt examples suggest), coercion should work -- but only for fields that exist on the typed *Design schemas. Research-defined fields NOT in the schemas (e.g., `layout_mode`, `game_variant`, `sort_mode`) are silently lost. |

### 4.6 Tool Gaps

| Tool | Gap |
|------|-----|
| `get_mechanic_config_schema` | Returns STATIC default schemas. Does not return research-defined enriched schemas. Missing fields for all 9 mechanics. |
| `generate_mechanic_content` | Tool exists but its implementation determines output quality. Without system prompt guidance on per-mechanic output format, the LLM may produce incomplete content. |
| `validate_scene_spec` | Validates config presence (does field exist?) but not config content quality (is content complete and valid?). |

---

## 5. interaction_designer_v3.py

**File**: `backend/app/agents/interaction_designer_v3.py`
**Role**: Phase 3 -- Defines scoring, feedback, misconception handling, animations, and transitions
**Tools**: `get_scoring_templates`, `generate_misconception_feedback`, `enrich_mechanic_content`, `validate_interactions`, `submit_interaction_specs`

### 5.1 System Prompt Gaps

| ID | Severity | Gap | Research Requirement |
|----|----------|-----|---------------------|
| ID-SP-1 | **CRITICAL** | System prompt (L27-70) is entirely mechanic-generic. No per-mechanic scoring strategy guidance. Says "Scoring should use the recommended strategy from get_scoring_templates" but does not describe what strategies exist per mechanic type. | Research defines per-mechanic scoring: sequencing -> positional scoring (partial credit for items within N positions of correct), sorting -> per-item + category completion bonus, memory_match -> time-decay scoring for scatter variant + match streak bonuses, branching -> cumulative state variable scoring + ending quality rating, compare -> per-category identification scoring + exploration phase bonus. |
| ID-SP-2 | HIGH | No guidance on what `enrich_mechanic_content` should produce per mechanic type. Generic "enriched scoring, feedback, and misconception triggers" (L47). | Sequencing: ordering misconception triggers (common reversal pairs, insertion errors). Sorting: mis-categorization feedback with explanation per item. Memory_match: card-specific hints on mismatch. Branching: consequence explanations per choice quality. Compare: per-zone similarity/difference reasoning. |
| ID-SP-3 | HIGH | No guidance on mechanic-specific feedback formats. All feedback is modeled as `on_correct: str, on_incorrect: str, on_completion: str`. | Sequencing: per-position feedback ("Item X is in position Y but should be Z because..."). Sorting: per-item-in-wrong-category feedback. Memory_match: per-pair explanation on reveal. Branching: immediate/delayed/hidden consequence feedback. Compare: per-zone explanation of similarity/difference. |
| ID-SP-4 | MEDIUM | No guidance on mode_transition trigger selection per mechanic type. Just says "mode_transitions to define the order" (L66). | Research defines per-mechanic completion triggers: sequencing -> `sequence_complete`, sorting -> `all_categorized`, memory_match -> `all_matched`, branching -> `ending_reached`, compare -> `all_zones_categorized`. |
| ID-SP-5 | MEDIUM | No mention of new mechanics from research doc 08. | 10 new mechanics each need scoring strategies, feedback formats, and misconception types. |

### 5.2 Task Prompt Gaps

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| ID-TP-1 | HIGH | L95-184: Passes game design summary, labels, scene specs. No domain knowledge injection. Interaction designer cannot generate content-specific misconception feedback without domain knowledge (e.g., common sequencing errors for specific processes). | Inject `domain_knowledge` sub-fields relevant to misconception generation. |
| ID-TP-2 | MEDIUM | No injection of mechanic config details from scene_specs_v3. Interaction designer sees mechanic types but not the rich config (waypoints, categories, pairs, nodes) that scene architect produced. | The LLM needs to see what config was produced to design appropriate scoring and feedback around it. |

### 5.3 State Field Gaps

| Field | Status | Issue |
|-------|--------|-------|
| `domain_knowledge` | NOT READ | Not injected into task prompt -- needed for content-specific misconception feedback |
| `scene_specs_v3` | READ | Passed as summary but mechanic config details may be truncated |
| `interaction_specs_v3` | WRITTEN | Output uses `InteractionSpecV3` with generic scoring/feedback schemas |

### 5.4 max_iterations Assessment

**Current**: 8
**Assessment**: ADEQUATE. Same reasoning as scene_architect.
**Recommendation**: Keep at 8.

### 5.5 parse_final_result Gaps

| ID | Severity | Gap |
|----|----------|-----|
| ID-PR-1 | MEDIUM | `InteractionSpecV3` scoring uses generic `MechanicScoringV3` with `strategy`, `points_per_correct`, `partial_credit`, `hint_penalty`, `max_score`. No per-mechanic scoring fields (e.g., `time_decay_factor` for memory_match, `positional_tolerance` for sequencing, `state_variable_weights` for branching). |

---

## 6. asset_generator_v3.py

**File**: `backend/app/agents/asset_generator_v3.py`
**Role**: Phase 4 -- Generates visual assets (images, zones) per scene
**Tools**: `search_diagram_image`, `generate_diagram_image`, `detect_zones`, `generate_animation_css`, `submit_assets`

### 6.1 System Prompt Gaps

| ID | Severity | Gap | Research Requirement |
|----|----------|-----|---------------------|
| AG-SP-1 | **CRITICAL** | System prompt (L28-65) is 100% focused on single-image zone-detection workflow: search -> clean -> detect zones. This is ONLY appropriate for drag_drop and click_to_identify mechanics. | Mechanics requiring different asset types: **compare_contrast** needs DUAL images (two separate diagrams to compare). **branching_scenario** needs scene backgrounds + character sprites with 4-6 expression variants. **sequencing** needs per-item card images. **sorting** needs per-item card images + container illustrations. **memory_match** needs per-pair face images (front/back, potentially diagram closeup crops). |
| AG-SP-2 | **CRITICAL** | No dual-image pipeline. Asset generator assumes 1 image per scene. Compare_contrast fundamentally requires 2 images per scene with zone detection on BOTH. | Research 05: "Dual-image pipeline requirement: retrieve/generate TWO images per scene, detect zones on BOTH, compute zone_pairings." |
| AG-SP-3 | **CRITICAL** | No character sprite generation. Branching_scenario needs character illustrations with multiple expression variants (neutral, happy, concerned, surprised, determined, thoughtful). | Research 04: "Character sprites with 4-6 expression variants per character, scene backgrounds for each decision node." |
| AG-SP-4 | HIGH | No per-item image generation. Sequencing and sorting mechanics need individual card images for items. Memory_match needs card face images. | Research 01: "Per-item images for visual sequencing cards." Research 03: "Per-item card images for sorting items." Research 02: "Card face images, potentially diagram closeup crops." |
| AG-SP-5 | HIGH | No scene background generation for narrative mechanics. Branching_scenario needs distinct visual backgrounds for different story locations/contexts. | Research 04: "Scene backgrounds per decision node context." |
| AG-SP-6 | MEDIUM | No mention of new mechanics from research doc 08. Mechanics like annotation_drawing need canvas/overlay assets, measurement_reading needs scale/ruler overlays. | New mechanics have diverse asset requirements beyond zones. |

### 6.2 Task Prompt Gaps

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| AG-TP-1 | HIGH | L90-185: Lists per-scene image descriptions and expected zone labels. No mechanic-type-aware asset generation strategy. For compare_contrast scenes, it would try to search for a single diagram. | Task prompt should branch asset strategy based on mechanic type: single-image for drag_drop/click/trace, dual-image for compare, per-item images for sequencing/sorting/memory, character+background for branching. |
| AG-TP-2 | MEDIUM | No domain knowledge injection for asset generation guidance (e.g., what the diagram should depict, key visual elements to include). | Pass `visual_description` from game_design scenes more prominently. |

### 6.3 State Field Gaps

| Field | Status | Issue |
|-------|--------|-------|
| `generated_assets_v3` | WRITTEN | Structured as `{scene_N: {image_url, zones}}` -- single image per scene. No field for dual images, character sprites, or item card images. |
| `scene_specs_v3` | READ | Used for image descriptions and zone labels, but mechanic type not used to determine asset strategy |

### 6.4 max_iterations Assessment

**Current**: 8 (tool_timeout=120s)
**Assessment**: ADEQUATE for single-image workflow. INSUFFICIENT for multi-asset workflows (dual-image, per-item images). Each image search/generate + zone detect takes 2-3 iterations. A compare_contrast scene needs 2x that.
**Recommendation**: Increase to 12 for multi-asset support, or use Map-Reduce pattern with per-asset sub-agents.

### 6.5 Tool Gaps

| Tool | Gap |
|------|-----|
| `search_diagram_image` | Single-image search only. No "search pair of images for comparison" mode. |
| `generate_diagram_image` | Single-image generation. No character sprite generation, no item card generation, no scene background generation. |
| `detect_zones` | Single-image zone detection. No paired zone detection for compare_contrast. |
| Missing tool | No `generate_character_sprite` tool for branching_scenario assets. |
| Missing tool | No `generate_item_cards` tool for sequencing/sorting/memory per-item images. |
| Missing tool | No `crop_diagram_region` tool for memory_match card faces from diagram closeups. |

---

## 7. blueprint_assembler_v3.py

**File**: `backend/app/agents/blueprint_assembler_v3.py`
**Role**: Phase 5 -- Assembles final frontend-ready blueprint from all upstream data
**Tools**: `assemble_blueprint`, `validate_blueprint`, `repair_blueprint`, `submit_blueprint`

### 7.1 System Prompt Gaps

| ID | Severity | Gap | Research Requirement |
|----|----------|-----|---------------------|
| BA-SP-1 | HIGH | System prompt (L373-405) is generic "assemble -> validate -> repair -> submit" instructions. No guidance on how to handle per-mechanic config population into blueprint format. | Blueprint needs to populate frontend config fields: `sequencingConfig`, `sortingConfig`, `memoryMatchConfig`, `branchingConfig`, `compareConfig` at scene or blueprint level. Each has specific field requirements defined by frontend components. |
| BA-SP-2 | HIGH | No guidance on multi-asset scenes (dual images for compare, per-item images for sequencing/sorting, character sprites for branching). Blueprint must structure these assets differently than single-image scenes. | Frontend expects specific asset structures per mechanic type. |
| BA-SP-3 | MEDIUM | L394: "Zone coordinates should be in 0-100% range" -- assumes all mechanics use zones. Branching nodes, sequence items, sorting items, memory pairs are not zones. | Blueprint structure must accommodate non-zone game elements. |

### 7.2 Legacy `_assemble_mechanics` Gaps (L172-209)

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| BA-AM-1 | **CRITICAL** | Only extracts 3 of 9 mechanic-specific configs: `path_config` (L182), `click_config` (L184), `sequence_config` (L186). **Completely ignores**: `sorting_config`, `branching_config`, `compare_config`, `memory_config`, `timed_config`, `description_match_config`. | Missing 6 mechanic configs means those mechanics get empty `config: {}` in the blueprint, making them unplayable on the frontend. |
| BA-AM-2 | **CRITICAL** | Known bug: `blueprint_assembler_tools.py` drops scoring/feedback from mechanics when converting list to dict (identified in audit 07, fix 3.4). | Scoring and feedback data for all mechanics may be lost during blueprint assembly. |
| BA-AM-3 | HIGH | Does not populate frontend-specific config fields (`sequencingConfig`, `sortingConfig`, `memoryMatchConfig`, `branchingConfig`, `compareConfig`). Frontend components read these top-level fields, not the generic `config` dict inside mechanic objects. | Frontend template code expects structured config objects, not generic dicts. |

### 7.3 max_iterations Assessment

**Current**: 4
**Assessment**: **TOO LOW**. The workflow is: assemble (1) -> validate (2) -> repair (3) -> validate again (4). This leaves ZERO iterations for a second repair cycle if the first repair doesn't fix all issues.
**Recommendation**: Increase to 6 to allow assemble -> validate -> repair -> validate -> repair -> submit.

### 7.4 parse_final_result Gaps

| ID | Severity | Gap |
|----|----------|-----|
| BA-PR-1 | MEDIUM | L522-602: Multiple extraction strategies (submit_blueprint args, tool results, text JSON). Sets `generation_complete: True` which is correct. No mechanic-specific validation of blueprint completeness. |

---

## 8. design_validator.py

**File**: `backend/app/agents/design_validator.py`
**Role**: Deterministic validation of `game_design_v3` output
**Type**: Non-LLM validator (pure Python)

### 8.1 Validation Gaps

| ID | Severity | Gap | Research Requirement |
|----|----------|-----|---------------------|
| DV-1 | **CRITICAL** | All mechanic-specific validation (L109-163) is **WARNING severity (-0.05 score)**, never FATAL. A design with completely missing `sorting_config` for a sorting_categories mechanic passes with score 0.95. | Missing mechanic config should be FATAL -- the mechanic cannot function without its config. If a mechanic type is chosen, its config must be present and minimally valid. |
| DV-2 | **CRITICAL** | Validation only checks config EXISTENCE ("does sorting_config exist?") but never validates config CONTENT ("does sorting_config have >= 2 categories? >= 3 items? do items reference valid category IDs?"). | Research defines per-mechanic content requirements: sequencing: 4-8 items, each with text + order_index; sorting: 2-6 categories + 6-20 items + valid category references; memory_match: 4-15 pairs + front/back content; branching: 5-15 nodes + valid node graph + start_node_id references valid node; compare: >= 2 comparison categories. |
| DV-3 | HIGH | No validation for `compare_contrast` mechanic config. Despite being in `VALID_MECHANIC_TYPES`, there is no config check block for it (L109-163 covers trace_path, click_to_identify, sequencing, description_matching, sorting_categories, branching_scenario, memory_match -- but NOT compare_contrast). | Compare_contrast should validate: has expected_categories, at least 2 zone labels, comparison_mode specified. |
| DV-4 | HIGH | No validation for `timed_challenge` mechanic config. In `VALID_MECHANIC_TYPES` but no config check block. | Timed_challenge should validate: has wrapped_mechanic_type, time_limit_seconds > 0, wrapped mechanic type is valid. |
| DV-5 | HIGH | `VALID_MECHANIC_TYPES` (L24-28) does not include any of the 10 new mechanics from research doc 08. Any new mechanic type would immediately fail validation as FATAL. | Add new mechanic types to VALID_MECHANIC_TYPES as they are implemented. Or better: make the set dynamic, loaded from a config registry. |
| DV-6 | MEDIUM | Label coverage check (L196-204) requires 50% of zone_labels used in mechanics. This threshold is too low -- unused labels waste pipeline resources. | Increase to 80% or add a WARNING at 50% and FATAL at 30%. |
| DV-7 | MEDIUM | No validation of game duration estimate vs mechanic complexity. A 5-scene game with branching_scenario + sorting in each scene should not estimate 3 minutes. | Add duration validation: minimum 1-2 minutes per mechanic type, scaled by item/node count. |

### 8.2 Missing Validation Categories

| Category | What Should Be Validated |
|----------|------------------------|
| Mechanic config content | Per-mechanic field counts, valid references, data quality |
| Item/node graph validity | Branching nodes form valid DAG, sequencing items have unique order_indices |
| Cross-mechanic consistency | Sorting items reference labels from zone_labels, sequencing items match zone_labels |
| Difficulty scaling | Config parameters (item counts, pair counts, node counts) appropriate for stated difficulty |
| Multi-mechanic scene limits | Research suggests max 2-3 mechanics per scene for usability |

---

## 9. scene_validator.py

**File**: `backend/app/agents/scene_validator.py`
**Role**: Deterministic validation of `scene_specs_v3` output
**Type**: Non-LLM validator -- thin wrapper around `validate_scene_specs()` in `scene_spec_v3.py`

### 9.1 Validation Gaps

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| SV-1 | HIGH | The actual validation logic in `scene_spec_v3.py:validate_scene_specs()` (L191-329) only checks mechanic config **presence** (does path_config exist? does sorting_config have categories AND items?). Never validates config **content quality**. | Same as DV-2: need content validation for counts, valid references, data completeness. |
| SV-2 | HIGH | No cross-mechanic zone coverage validation. Does not check that zones referenced by mechanic configs actually exist in the scene's zone list. | If a sorting_categories config references zone labels not in the scene's zones, it will break at runtime. |
| SV-3 | HIGH | All mechanic config checks produce `issues` strings but validation result `passed` is only set to `False` when issues contains items. No severity levels -- all issues are treated equally. A missing image_description is weighted the same as a completely absent mechanic config. | Implement severity tiers (FATAL vs WARNING) like design_validator does, but with FATAL for critical mechanic config issues. |
| SV-4 | MEDIUM | No validation of image_description quality. An empty string fails, but "an image" passes. Research defines per-mechanic image requirements (dual images for compare, scene backgrounds for branching). | Validate that image_description references the correct visual content for the mechanic type. |
| SV-5 | MEDIUM | No validation for new mechanic types from research doc 08. | Unknown mechanic types pass silently through the else branch with no validation. |

### 9.2 Underlying `validate_scene_specs()` Coverage

**What it validates** (L191-329):
- Scene spec parsing (Pydantic validation)
- Cross-stage: design zone_labels have zones in specs
- Cross-stage: scene numbers match
- Cross-stage: mechanic types match per scene
- Internal: zones exist, mechanic_configs exist, image_description non-empty
- Internal: zone position_hints non-empty
- Per-mechanic: config field presence (trace_path->waypoints, click_to_identify->prompts, sequencing->correct_order, description_matching->descriptions, sorting_categories->categories+items, branching_scenario->nodes, memory_match->pairs)

**What it does NOT validate**:
- Config field content (counts, valid references, data completeness)
- Cross-mechanic zone references
- Image requirements per mechanic type
- Multi-asset scene requirements (dual images, per-item images)
- Config field values (e.g., sequence_type must be "linear"|"cyclic"|"branching")

---

## 10. interaction_validator.py

**File**: `backend/app/agents/interaction_validator.py`
**Role**: Contains BOTH legacy V1 validator AND V3 validator wrapper
**Type**: Non-LLM validator

### 10.1 Legacy Validator Gaps (Principle Violations)

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| IV-1 | **CRITICAL** | `validate_learning_alignment` (L105-171) uses `blooms_cognitive` dict mapping Bloom's levels to cognitive demands (L129-136). Checks if mechanic's cognitive demands match Bloom's level. **This directly violates the principle that Bloom's should NOT drive mechanic selection.** | This function should be removed or refactored. Learning alignment should validate that mechanics match CONTENT CHARACTERISTICS, not cognitive taxonomy levels. |
| IV-2 | **CRITICAL** | `auto_fix_design` (L334-392) defaults unknown modes to `drag_drop` (L350: `fixed["primary_interaction_mode"] = "drag_drop"`). **Direct drag_drop bias**. | Should either leave the mode as-is and report an error, or use the mechanic best suited to the content characteristics. |
| IV-3 | HIGH | `COMPATIBLE_MECHANICS` dict (L223-235) is hardcoded and incomplete. Defines pairwise compatibility based on assumptions, not research. E.g., `branching_scenario` is only compatible with `sequencing` -- research shows it can pair with `click_to_identify` (choice verification), `description_matching` (consequence evaluation). | Make compatibility dynamic based on scene context, not a static dict. Or expand based on research pairing recommendations. |
| IV-4 | HIGH | `validate_technical_feasibility` (L174-218) checks `pattern.frontend_component` and suggests "Use a fully implemented mode like 'drag_drop'" (L194). More drag_drop bias. | Suggest the nearest fully-implemented mode, not always drag_drop. |

### 10.2 V3 Validator (L622-712)

| ID | Severity | Gap | Details |
|----|----------|-----|---------|
| IV-V3-1 | HIGH | Delegates entirely to `validate_interaction_specs()` in `interaction_spec_v3.py`. The underlying validation (L185-316) checks: scoring exists per mechanic, feedback exists per mechanic, misconception count >= 2, mode_transitions for multi-mechanic scenes, valid completion triggers, generic feedback detection, total max_score range. | No per-mechanic scoring STRATEGY validation (e.g., sequencing should use positional scoring, not per-item binary). No per-mechanic feedback FORMAT validation (e.g., branching should have consequence explanations, not just "correct/incorrect"). |
| IV-V3-2 | MEDIUM | Mechanic-specific content checks (L263-309 in interaction_spec_v3.py) only cover click_to_identify (generic feedback detection), description_matching (has feedback entry), trace_path (has misconception), sequencing (has misconception). **Missing**: sorting, memory_match, branching, compare. | All 9 mechanics need content quality checks. |
| IV-V3-3 | MEDIUM | Mode transition trigger validation (L244-261 in interaction_spec_v3.py) uses `MECHANIC_TRIGGER_MAP` that covers 8 mechanic types. Missing: `compare_contrast`, `description_matching` trigger validation. | Add compare_contrast and description_matching to trigger map. |
| IV-V3-4 | MEDIUM | No validation that scoring `max_score` per mechanic is proportional to mechanic complexity. A sorting scene with 20 items should have higher max_score than one with 4 items. | Add proportional scoring validation based on item/zone/node counts from scene_specs. |

---

## 11. react_base.py

**File**: `backend/app/agents/react_base.py`
**Role**: Base class for all ReAct agents
**Type**: Infrastructure (mechanic-agnostic -- correctly so)

### 11.1 Assessment

| ID | Severity | Finding |
|----|----------|---------|
| RB-1 | OK | **Correctly mechanic-agnostic**. No mechanic-specific logic, which is the correct architecture. Per-mechanic logic should live in tools. |
| RB-2 | MEDIUM | `_serialize_trace` (L300-313) truncates observation to 500 chars. For tool results containing rich mechanic content (e.g., 20 sorting items with descriptions), important data may be lost in trace serialization. | Increase observation truncation to 1500 chars, or use structured summarization. |
| RB-3 | MEDIUM | `extract_json_from_response` (L320-420) handles JSON extraction but does not validate against expected schema. Invalid JSON that parses but doesn't match the expected schema passes through. | Add optional schema validation in extract_json_from_response. |
| RB-4 | LOW | No rate limiting or backoff for tool calls. If a tool fails (e.g., image search), the agent retries immediately. | Add exponential backoff for tool failures. |

---

## 12. Cross-Cutting Gaps

### 12.1 Bloom's Taxonomy Leakage

**Affected agents**: game_designer_v3 (reads `blooms_level`, injects into task prompt), interaction_validator (uses `blooms_cognitive` mapping)

**Impact**: Bloom's taxonomy drives mechanic selection indirectly. A question classified as "remember" level would bias toward drag_drop/click_to_identify (recall mechanics), even if the content has rich sequence_flow_data that would make sequencing a better choice.

**Fix**: Remove `blooms_level` injection from game_designer_v3 task prompt. Remove `validate_learning_alignment` Bloom's check from interaction_validator. Replace with content-characteristic-based mechanic fitness evaluation.

### 12.2 drag_drop Bias

**Locations**:
- game_designer_v3 system prompt L77: "drag_drop: Default mechanic"
- scene_architect_v3 system prompt L49: "For non-drag_drop mechanics" (implies drag_drop is the baseline)
- scene_architect_v3 system prompt L69: drag_drop listed first with most complete config example
- interaction_validator L350: `auto_fix_design` defaults to `drag_drop`
- interaction_validator L194: suggests "Use a fully implemented mode like 'drag_drop'"
- asset_generator_v3 entire system prompt: single-image zone-detection workflow optimized for drag_drop

**Fix**: Present all mechanics equally in system prompts. Remove drag_drop defaults in auto_fix. Make asset generation mechanic-aware.

### 12.3 Schema Insufficiency

**Current schemas vs research requirements**:

| Mechanic | Current Schema Fields | Research-Required Fields | Coverage |
|----------|----------------------|-------------------------|----------|
| sequencing (`SequenceDesign`) | 4 fields: `sequence_type`, `items`, `correct_order`, `instruction_text` | 12+ fields: + `layout_mode`, `interaction_pattern`, `source_area`, `reveal_mode`, `connector_style`, `slot_config`, `item_card_config`, `distractor_items` | 33% |
| memory_match (`MemoryMatchDesign`) | 4 fields: `pairs`, `grid_size`, `flip_duration_ms`, `instruction_text` | 14+ fields: + `game_variant`, `card_face_type`, `card_back_style`, `match_type`, `mismatch_penalty`, `per_pair_difficulty`, `per_pair_explanation`, `crop_region`, `card_back_image` | 29% |
| sorting (`SortingDesign`) | 4 fields: `categories`, `items`, `show_category_hints`, `instruction_text` | 12+ fields: + `sort_mode`, `item_card_type`, `container_style`, `header_type`, `pool_layout`, `submit_mode`, `allow_multi_category`, `matrix_row_axis`, `matrix_col_axis`, `venn_circle_labels` | 33% |
| branching (`BranchingDesign`) | 6 fields: `nodes`, `start_node_id`, `show_path_taken`, `allow_backtrack`, `show_consequences`, `multiple_valid_endings` | 18+ fields: + `narrative_structure`, `characters` with expressions, `state_variables` with thresholds, `decision_quality_spectrum`, `consequence_timing`, `minimap_config`, `scene_backgrounds`, `ending_types` | 33% |
| compare (`CompareDesign`) | 3 fields: `expected_categories`, `highlight_matching`, `instruction_text` | 10+ fields: + `comparison_mode`, `dual_image_spec`, `zone_pairings`, `exploration_phase`, `category_customization`, `shared_elements`, `scoring_by_category` | 30% |
| trace_path (`PathDesign`) | 3 fields: `waypoints`, `path_type`, `visual_style` | 6+ fields: + `drawing_mode`, `snap_tolerance`, `waypoint_hints` | 50% |
| click_to_identify (`ClickDesign`) | 4 fields: `click_options`, `correct_assignments`, `selection_mode`, `prompts` | 6+ fields: + `highlight_style`, `prompt_sequence`, `identification_type` | 67% |
| description_matching (`DescriptionMatchDesign`) | 3 fields: `sub_mode`, `descriptions`, `instruction_text` | 5+ fields: + `description_source`, `matching_strategy` | 60% |
| drag_drop | N/A (no schema) | Richest existing implementation | 80%+ |

### 12.4 Domain Knowledge Underutilization

**DK retriever produces** (from schema): `canonical_labels`, `label_descriptions`, `sequence_flow_data`, `comparison_data`, `process_steps`, `term_definitions`, `hierarchical_data`, `spatial_data`, `content_characteristics`, `causal_relationships`, `measurement_data`, `error_patterns`, `claim_evidence_data`

**What agents actually read**:
- game_designer_v3: `canonical_labels`, `label_descriptions`, `sequence_flow_data`, `comparison_data`, `content_characteristics` (5/13)
- scene_architect_v3: `canonical_labels` only (1/13)
- interaction_designer_v3: nothing from DK (0/13)
- asset_generator_v3: nothing from DK (0/13)
- blueprint_assembler_v3: nothing from DK (0/13)

**Total DK field utilization**: 6/65 agent-field pairs (9.2%)

### 12.5 New Mechanics Not Supported

All 10 new mechanics from research doc 08 are completely unsupported across all agents:
- Not in `VALID_MECHANIC_TYPES` (design_validator would FATAL reject)
- No system prompt guidance in any agent
- No config schemas defined
- No tool support
- No frontend components

---

## 13. Schema Gap Matrix

This matrix shows which schema fields exist vs which are needed per research requirements.

| Mechanic | Design Schema | Scene Config Schema | Interaction Schema | Blueprint Schema | Frontend Component |
|----------|:---:|:---:|:---:|:---:|:---:|
| drag_drop | N/A (implicit) | Basic config | Generic scoring/feedback | Full support | WORKING |
| click_to_identify | ClickDesign (4 fields) | click_config (4 fields) | Generic scoring/feedback | path via _assemble_mechanics | DEGRADED |
| trace_path | PathDesign (3 fields) | path_config (3 fields) | Generic scoring/feedback | path via _assemble_mechanics | DEGRADED |
| sequencing | SequenceDesign (4/12 fields) | sequence_config (4/12 fields) | Generic scoring/feedback | path via _assemble_mechanics | DEGRADED |
| sorting_categories | SortingDesign (4/12 fields) | sorting_config (4/12 fields) | Generic scoring/feedback | **DROPPED** (_assemble_mechanics ignores) | BROKEN |
| description_matching | DescriptionMatchDesign (3/5 fields) | description_match_config (3/5 fields) | Generic scoring/feedback | **DROPPED** (_assemble_mechanics ignores) | BROKEN |
| memory_match | MemoryMatchDesign (4/14 fields) | memory_config (4/14 fields) | Generic scoring/feedback | **DROPPED** (_assemble_mechanics ignores) | BROKEN |
| branching_scenario | BranchingDesign (6/18 fields) | branching_config (6/18 fields) | Generic scoring/feedback | **DROPPED** (_assemble_mechanics ignores) | BROKEN |
| compare_contrast | CompareDesign (3/10 fields) | compare_config (3/10 fields) | Generic scoring/feedback | **DROPPED** (_assemble_mechanics ignores) | BROKEN |
| timed_challenge | TimedDesign (3 fields) | timed_config (3 fields) | Generic scoring/feedback | **DROPPED** (_assemble_mechanics ignores) | BROKEN |

**Legend**: WORKING = end-to-end functional, DEGRADED = partially functional with missing features, BROKEN = config lost in pipeline, frontend cannot render

---

## 14. Prioritized Fix List

### Priority 1: CRITICAL (Blocks mechanic functionality)

| # | Fix | Agent(s) | Effort | Impact |
|---|-----|----------|--------|--------|
| 1 | **Remove Bloom's taxonomy from game_designer task prompt** (GD-TP-1) | game_designer_v3 | Small | Removes bias in mechanic selection |
| 2 | **Remove Bloom's cognitive mapping from interaction_validator** (IV-1) | interaction_validator | Small | Removes Bloom's-driven validation |
| 3 | **Fix _assemble_mechanics to extract ALL 9 mechanic configs** (BA-AM-1) | blueprint_assembler_v3 | Medium | Unblocks sorting, branching, compare, memory, description_match, timed |
| 4 | **Fix scoring/feedback drop bug** (BA-AM-2, known fix 3.4) | blueprint_assembler_tools | Medium | Restores scoring/feedback for all mechanics |
| 5 | **Make mechanic config validation FATAL in design_validator** (DV-1) | design_validator | Small | Forces valid configs, prevents broken games from proceeding |
| 6 | **Add compare_contrast and timed_challenge config validation** (DV-3, DV-4) | design_validator | Small | Currently skip validation entirely |
| 7 | **Add memory_match, branching, compare config guidelines to scene_architect system prompt** (SA-SP-1) | scene_architect_v3 | Medium | 3 mechanics have zero config guidance |
| 8 | **Remove drag_drop default in auto_fix_design** (IV-2) | interaction_validator | Small | Removes drag_drop bias |

### Priority 2: HIGH (Degrades mechanic quality)

| # | Fix | Agent(s) | Effort | Impact |
|---|-----|----------|--------|--------|
| 9 | Enrich *Design schemas to research-defined field sets | game_design_v3 schemas | Large | All 9 mechanics get rich configs |
| 10 | Add per-mechanic content validation to design_validator | design_validator | Medium | Validates config counts, references, completeness |
| 11 | Inject domain knowledge into scene_architect task prompt | scene_architect_v3 | Medium | Enables content-driven mechanic config generation |
| 12 | Inject domain knowledge into interaction_designer task prompt | interaction_designer_v3 | Medium | Enables content-specific misconception feedback |
| 13 | Add per-mechanic scoring strategy guidance to interaction_designer system prompt | interaction_designer_v3 | Medium | Currently all scoring is generic |
| 14 | Add per-mechanic feedback format guidance to interaction_designer system prompt | interaction_designer_v3 | Medium | Currently all feedback is generic strings |
| 15 | Add generate_mechanic_content per-mechanic guidance to scene_architect system prompt | scene_architect_v3 | Medium | Tool exists but LLM has no guidance on what to produce |
| 16 | Add enrich_mechanic_content per-mechanic guidance to interaction_designer system prompt | interaction_designer_v3 | Medium | Tool exists but LLM has no guidance on what to produce |
| 17 | Increase blueprint_assembler max_iterations from 4 to 6 | blueprint_assembler_v3 | Tiny | Allows repair retry cycles |
| 18 | Populate frontend config fields in blueprint assembler | blueprint_assembler_v3 | Medium | Frontend components read sequencingConfig, sortingConfig, etc. |

### Priority 3: MEDIUM (Missing features, future mechanics)

| # | Fix | Agent(s) | Effort | Impact |
|---|-----|----------|--------|--------|
| 19 | Add dual-image pipeline to asset_generator | asset_generator_v3 | Large | Enables compare_contrast visual pipeline |
| 20 | Add character sprite generation to asset_generator | asset_generator_v3 | Large | Enables branching_scenario visual pipeline |
| 21 | Add per-item image generation to asset_generator | asset_generator_v3 | Large | Enables sequencing/sorting/memory visual cards |
| 22 | Add SlimMechanicConfig to game_designer output schema | game_design_v3 schemas | Medium | High-level config choices flow through Phase 1 |
| 23 | Make VALID_MECHANIC_TYPES dynamic (loaded from config) | design_validator | Small | Easy to add new mechanics |
| 24 | Add 10 new mechanic types to pipeline | All agents | Very Large | Research doc 08 mechanics |
| 25 | Expand COMPATIBLE_MECHANICS based on research | interaction_validator | Medium | More mechanic pairings supported |
| 26 | Add cross-mechanic zone reference validation to scene_validator | scene_spec_v3.py | Medium | Validates zones referenced by configs exist |
| 27 | Increase react_base observation truncation to 1500 chars | react_base | Tiny | Better trace data for rich mechanic content |
| 28 | Increase game_designer max_iterations from 6 to 8 | game_designer_v3 | Tiny | Allows more retry cycles |
| 29 | Add per-mechanic scoring fields to InteractionSpecV3 | interaction_spec_v3.py | Medium | Mechanic-specific scoring (positional, time-decay, etc.) |
| 30 | Add content-to-mechanic fitness evaluation | game_designer_v3 tools | Medium | Replace Bloom's with content-signal-based selection |

---

## Appendix A: File Reference

| Agent | File Path | Lines |
|-------|-----------|-------|
| game_designer_v3 | `backend/app/agents/game_designer_v3.py` | ~320 |
| scene_architect_v3 | `backend/app/agents/scene_architect_v3.py` | ~200 |
| interaction_designer_v3 | `backend/app/agents/interaction_designer_v3.py` | ~185 |
| asset_generator_v3 | `backend/app/agents/asset_generator_v3.py` | ~185 |
| blueprint_assembler_v3 | `backend/app/agents/blueprint_assembler_v3.py` | ~600 |
| design_validator | `backend/app/agents/design_validator.py` | ~310 |
| scene_validator | `backend/app/agents/scene_validator.py` | ~99 |
| interaction_validator | `backend/app/agents/interaction_validator.py` | ~713 |
| react_base | `backend/app/agents/react_base.py` | ~420 |

## Appendix B: Research Documents Referenced

| Doc | File | Key Requirements Extracted |
|-----|------|--------------------------|
| 01 | `docs/audit/research/01_sequencing_games.md` | SequencingMechanicConfig (12+ fields), layout modes, item cards, connectors |
| 02 | `docs/audit/research/02_memory_match_games.md` | MemoryMatchConfig (14+ fields), game variants, card types, match types |
| 03 | `docs/audit/research/03_sorting_categorization_games.md` | SortingConfig (12+ fields), sort modes, multi-category, matrix/venn |
| 04 | `docs/audit/research/04_branching_scenario_games.md` | BranchingScenario (18+ fields), narrative structures, characters, state variables |
| 05 | `docs/audit/research/05_compare_contrast_games.md` | CompareSpec (10+ fields), comparison modes, dual-image pipeline, zone pairings |
| 08 | `docs/audit/research/08_new_mechanics_research.md` | 10 new mechanic types covering 10 cognitive skills |

## Appendix C: Severity Definitions

| Severity | Definition |
|----------|-----------|
| **CRITICAL** | Blocks mechanic functionality entirely. Config is dropped, never generated, or fails validation. Game cannot be played for this mechanic. |
| **HIGH** | Mechanic technically functions but with significantly degraded quality. Missing content, generic feedback, no per-mechanic optimization. |
| **MEDIUM** | Missing feature or enhancement. Mechanic works at basic level but does not meet research-defined quality standards. |
| **LOW** | Minor improvement. Does not affect functionality or quality significantly. |
