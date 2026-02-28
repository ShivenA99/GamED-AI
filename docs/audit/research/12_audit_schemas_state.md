# Audit: V3 Pipeline Schemas & State Definitions vs. Research Requirements

**Date**: 2026-02-11
**Scope**: Exhaustive comparison of every Pydantic model, TypedDict, and state field against the mechanic-specific data models defined in the research documents (01-05). Covers `state.py`, `game_design_v3.py`, `scene_spec_v3.py`, `interaction_spec_v3.py`, `blueprint_schemas.py`, `interactive_diagram.py`, and `domain_knowledge.py`.

**Methodology**: For each file, list what exists, then enumerate every gap relative to what the research documents say the pipeline must produce. Gaps are categorized as MISSING (field does not exist), INADEQUATE (field exists but wrong type/scope), or MISMATCH (field exists but semantics differ from research).

---

## Table of Contents

1. [state.py — AgentState TypedDict](#1-statepy--agentstate-typeddict)
2. [game_design_v3.py — Design Schemas](#2-game_design_v3py--design-schemas)
3. [scene_spec_v3.py — Scene Architecture](#3-scene_spec_v3py--scene-architecture)
4. [interaction_spec_v3.py — Behavioral Layer](#4-interaction_spec_v3py--behavioral-layer)
5. [blueprint_schemas.py — Blueprint Output](#5-blueprint_schemaspy--blueprint-output)
6. [interactive_diagram.py — Frontend Config Schemas](#6-interactive_diagrampy--frontend-config-schemas)
7. [domain_knowledge.py — Domain Knowledge](#7-domain_knowledgepy--domain-knowledge)
8. [Cross-Cutting: Bloom's Taxonomy References](#8-cross-cutting-blooms-taxonomy-references)
9. [Cross-Cutting: New Asset Type State Fields](#9-cross-cutting-new-asset-type-state-fields)
10. [Summary: Gap Count by Mechanic](#10-summary-gap-count-by-mechanic)
11. [Prioritized Action Items](#11-prioritized-action-items)

---

## 1. state.py -- AgentState TypedDict

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/state.py`

### 1.1 What Exists

The AgentState TypedDict has ~90 fields organized into sections:

| Section | Fields | Count |
|---------|--------|-------|
| Input | question_id, question_text, question_options | 3 |
| Enhanced Input | pedagogical_context | 1 |
| Routing | template_selection, routing_confidence, routing_requires_human_review | 3 |
| Domain Knowledge | domain_knowledge | 1 |
| Diagram/Segmentation | diagram_image, sam3_prompts, diagram_segments, diagram_zones, diagram_labels, zone_groups | 6 |
| Image Cleaning | cleaned_image_path, removed_labels | 2 |
| Generated Diagram | generated_diagram_path | 1 |
| Annotation Detection | annotation_elements | 1 |
| Image Classification | image_classification | 1 |
| Image Search Retry | retry_image_search, image_search_attempts, max_image_attempts | 3 |
| Generation Artifacts | game_plan, scene_data, story_data, blueprint, generated_code, asset_urls, diagram_svg, diagram_spec | 8 |
| Hierarchical Scene | scene_structure, scene_assets, scene_interactions | 3 |
| Multi-Scene | needs_multi_scene, num_scenes, scene_progression_type, scene_breakdown, game_sequence, scene_diagrams, scene_zones, scene_labels | 8 |
| Multi-Scene Orchestrator | all_scene_data | 1 |
| HAD v3 | scene_images, scene_zone_groups, current_scene_number, zone_collision_metadata, query_intent, suggested_reveal_order, temporal_constraints, motion_paths | 8 |
| Agentic Preset 2 | diagram_type, diagram_type_config, diagram_analysis, game_design, interaction_designs, interaction_design, interaction_validation, design_metadata, design_trace | 9 |
| V3 Pipeline | game_design_v3, design_validation_v3, _v3_design_retries, scene_specs_v3, scene_validation_v3, _v3_scene_retries, interaction_specs_v3, interaction_validation_v3, _v3_interaction_retries, generated_assets_v3, asset_graph_v3, asset_manifest_v3 | 12 |
| Asset Pipeline | planned_assets, generated_assets, asset_validation, assets_valid, validated_assets, validation_errors | 6 |
| Entity Registry | entity_registry | 1 |
| Workflow | workflow_execution_plan, workflow_generated_assets | 2 |
| Runtime | _pipeline_preset, _ai_images_generated, validation_results, current_validation_errors, retry_counts, max_retries | 6 |
| Human-in-Loop | pending_human_review, human_feedback, human_review_completed | 3 |
| Execution | current_agent, agent_history, started_at, last_updated_at, _run_id, _stage_order | 6 |
| Routing Flags | _needs_diagram_spec, _needs_asset_generation, _skip_asset_pipeline | 3 |
| Final Output | final_visualization_id, generation_complete, error_message, output_metadata | 4 |

**Supporting TypedDicts**: ZoneEntity, AssetEntity, InteractionEntity, EntityRegistry, PedagogicalContext, TemplateSelection, SequenceItemData, GameMechanic, ScoringRubric, HierarchyInfo, GamePlan, SceneData, StoryData, ValidationResult, HumanReviewRequest, AgentExecution, HierarchicalRelationship, SequenceFlowDataState, ContentCharacteristicsState, DomainKnowledge (TypedDict version).

### 1.2 Missing State Fields for New Mechanics

#### 1.2.1 Compare & Contrast (Research Doc 05)

| Missing Field | Type | Purpose | Priority |
|---------------|------|---------|----------|
| `diagram_image_b` | `Optional[Dict[str, Any]]` | Second diagram image for compare mode | P0 |
| `diagram_image_b_url` | `Optional[str]` | URL of second diagram | P0 |
| `zones_b` | `Optional[List[Dict[str, Any]]]` | Zone detection results for Diagram B | P0 |
| `zone_pairings` | `Optional[List[Dict[str, Any]]]` | Cross-diagram zone correspondences `[{zone_a_id, zone_b_id}]` | P0 |
| `comparison_visual_spec` | `Optional[Dict[str, Any]]` | ComparisonVisualSpec from game designer | P1 |
| `is_comparison_mode` | `Optional[bool]` | Flag to trigger dual-image pipeline | P0 |

The entire compare_contrast mechanic requires a parallel image pipeline (two images, two zone detections, then zone pairing). None of the state fields exist to carry this data through the pipeline.

#### 1.2.2 Branching Scenario (Research Doc 04)

| Missing Field | Type | Purpose | Priority |
|---------------|------|---------|----------|
| `scene_backgrounds` | `Optional[List[Dict[str, Any]]]` | Generated scene background images (3-6 per scenario) | P0 |
| `character_sprites` | `Optional[Dict[str, Dict[str, str]]]` | character_id -> {expression: image_url} | P0 |
| `ending_illustrations` | `Optional[List[Dict[str, Any]]]` | Generated ending-specific illustrations (2-4) | P1 |
| `branching_state_variables` | `Optional[List[Dict[str, Any]]]` | StateVariable definitions for the scenario | P0 |

The branching mechanic requires entirely new asset types (backgrounds, sprites with expressions, endings) that the current pipeline has no concept of. No state fields exist to carry these through the generation pipeline.

#### 1.2.3 Sequencing (Research Doc 01)

| Missing Field | Type | Purpose | Priority |
|---------------|------|---------|----------|
| `sequence_item_images` | `Optional[Dict[str, str]]` | Per-item illustration URLs for image card types | P1 |

The research defines 5 card types (image_and_text, image_only, text_only, icon_and_text, numbered_text). For image-bearing card types, the pipeline must generate per-item illustrations. No state field carries these.

#### 1.2.4 Sorting/Categorization (Research Doc 03)

| Missing Field | Type | Purpose | Priority |
|---------------|------|---------|----------|
| `sorting_item_images` | `Optional[Dict[str, str]]` | Per-item illustration URLs | P1 |
| `sorting_category_icons` | `Optional[Dict[str, str]]` | Per-category icon/header image URLs | P2 |

Research specifies `image_with_caption` and `rich_card` item types requiring per-item illustrations. No state field carries these.

#### 1.2.5 Memory Match (Research Doc 02)

| Missing Field | Type | Purpose | Priority |
|---------------|------|---------|----------|
| `memory_card_images` | `Optional[Dict[str, str]]` | Per-pair image URLs (for image-type faces) | P1 |
| `diagram_crop_regions` | `Optional[List[Dict[str, Any]]]` | Crop regions for diagram_closeup card faces | P2 |

Research defines `diagram_closeup` face type requiring computed crop regions from zone coordinates. No state field exists.

### 1.3 PedagogicalContext -- Bloom's Taxonomy

```python
class PedagogicalContext(TypedDict, total=False):
    blooms_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    blooms_justification: str
    ...
```

**FLAG**: `blooms_level` and `blooms_justification` are Bloom's taxonomy references. These may need to be evaluated for removal or replacement with a simpler difficulty/cognitive-demand model, depending on project direction. The field is set by the `input_enhancer` agent and read by the `router` agent. See Section 8 for full Bloom's audit.

### 1.4 TemplateSelection -- Bloom's Taxonomy

```python
class TemplateSelection(TypedDict, total=False):
    bloom_alignment_score: float
    subject_fit_score: float
    interaction_fit_score: float
    ...
```

**FLAG**: `bloom_alignment_score` is a Bloom's reference used in routing scoring.

### 1.5 GameMechanic TypedDict

```python
class GameMechanic(TypedDict, total=False):
    sequence_items: Optional[List[SequenceItemData]]
    sequence_type: Optional[str]
    correct_order: Optional[List[str]]
```

**INADEQUATE**: `SequenceItemData` has `id`, `text`, `order_index`, `description`, `connects_to`. Research requires additionally: `image` (with prompt, alt_text, image_type), `icon`, `category`, `is_distractor`. These are all missing.

### 1.6 DomainKnowledge TypedDict (in state.py)

```python
class DomainKnowledge(TypedDict, total=False):
    canonical_labels: List[str]
    acceptable_variants: Dict[str, List[str]]
    hierarchical_relationships: Optional[List[HierarchicalRelationship]]
    sequence_flow_data: Optional[SequenceFlowDataState]
    content_characteristics: Optional[ContentCharacteristicsState]
```

**INADEQUATE**: This is the state-level TypedDict version. It mirrors the Pydantic DomainKnowledge but as a TypedDict. Missing: `query_intent`, `suggested_reveal_order`, `scene_hints`. These exist in the Pydantic version but NOT in this TypedDict, creating a mismatch -- agents reading from state will not see these fields.

---

## 2. game_design_v3.py -- Design Schemas

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/game_design_v3.py`

### 2.1 What Exists

**Top-level models**: GameDesignV3, GameDesignV3Slim

**Per-mechanic config models** (11 total):
- `PathDesign` -- waypoints, path_type, visual_style
- `ClickDesign` -- click_options, correct_assignments, selection_mode, prompts
- `SequenceDesign` -- sequence_type, items `[{id, text, description}]`, correct_order, instruction_text
- `SortingDesign` -- categories `[{id, name, color, hint}]`, items `[{id, text, correct_category}]`, show_category_hints, instruction_text
- `BranchingDesign` -- nodes `[Dict]`, start_node_id, show_path_taken, allow_backtrack, show_consequences, multiple_valid_endings
- `CompareDesign` -- expected_categories, highlight_matching, instruction_text
- `MemoryMatchDesign` -- pairs `[{front, back}]`, grid_size, flip_duration_ms, instruction_text
- `TimedDesign` -- wrapped_mechanic_type, time_limit_seconds, timer_warning_threshold
- `DescriptionMatchDesign` -- sub_mode, descriptions `[{zone_label, description}]`, instruction_text

**Supporting models**: ThemeSpec, DistractorLabel, HierarchyGroup, HierarchySpec, LabelDesign, ZoneSpec, ComparisonVisualSpec, SceneVisualSpec, MechanicScoring, MisconceptionFeedback, MechanicFeedback, AnimationDesign, MechanicAnimations, MotionPathDesign, MediaAssetDesign, SoundDesign, TemporalConstraintDesign, TemporalSpec, MechanicTransitionSpec, SceneTransitionSpec, DifficultySpec, MechanicDesign, SceneDesign.

**Slim versions**: SlimMechanicRef (just `type: str`), SlimSceneDesign, SlimSceneTransition, GameDesignV3Slim.

### 2.2 Gap Analysis: SequenceDesign vs. Research (Doc 01)

| Research Requirement | Current State | Gap Type |
|---------------------|---------------|----------|
| `items[].image` with prompt/alt_text/image_type | Not present. Items are `[{id, text, description}]` | MISSING |
| `items[].icon` for icon_and_text card type | Not present | MISSING |
| `items[].category` for grouping/color-coding | Not present | MISSING |
| `items[].is_distractor` flag | Not present | MISSING |
| `items[].order_index` (correct position) | Not present -- only `correct_order` list exists | MISSING (partial -- `correct_order` is a workaround but items don't carry their own position) |
| `layout_mode` (horizontal_timeline, vertical_timeline, circular, flowchart, insert_between) | Not present | MISSING |
| `interaction_pattern` (drag_to_reorder, drag_to_slots, insert_between, click_to_place) | Not present | MISSING |
| `source_area` (card_tray, card_stack, scattered_pool, sidebar_column) | Not present | MISSING |
| `reveal_mode` (all_at_once, progressive, timed_reveal, category_groups) | Not present | MISSING |
| `card_type` (image_and_text, image_only, text_only, icon_and_text, numbered_text) | Not present | MISSING |
| `card_size`, `card_style`, `image_aspect_ratio` | Not present | MISSING |
| `connector_style`, `connector_color`, `animate_connectors` | Not present | MISSING |
| `slot_style`, `slot_labels`, `show_position_numbers` | Not present | MISSING |
| `is_cyclic` boolean | Not present (only `sequence_type` = "cyclic" exists) | INADEQUATE -- boolean flag is more ergonomic for frontend |
| `sequence_type_label` (display label like "Timeline") | Not present | MISSING |
| `track_theme` | Not present | MISSING |
| `distractor_count`, `has_distractors` | Not present | MISSING |

**Verdict**: SequenceDesign has 4 fields. Research requires ~25+ configurable properties. SequenceDesign captures only the raw data (items + order) but none of the visual/interaction configuration.

### 2.3 Gap Analysis: SortingDesign vs. Research (Doc 03)

| Research Requirement | Current State | Gap Type |
|---------------------|---------------|----------|
| `sort_mode` (bucket, venn_2, venn_3, matrix, column) | Not present -- only implicit bucket mode | MISSING |
| `item_card_type` (text_only, text_with_icon, image_with_caption, image_only, rich_card) | Not present | MISSING |
| `container_style` (bucket, labeled_bin, circle, cell, column, funnel, themed) | Not present | MISSING |
| `header_type` (text_only, text_with_icon, image_banner, color_band) | Not present | MISSING |
| `pool_layout` (horizontal_tray, wrapped_grid, scattered, stacked_deck) | Not present | MISSING |
| `submit_mode` (batch_submit, immediate_feedback, round_based, lock_on_place) | Not present | MISSING |
| `allow_multi_category` boolean (for Venn modes) | Not present | MISSING |
| `max_attempts` | Not present | MISSING |
| `categories[].icon`, `categories[].header_image`, `categories[].row_value`, `categories[].column_value` | categories are `[{id, name, color, hint}]` -- missing icon, header_image, row/column | MISSING |
| `items[].image` | Not present | MISSING |
| `items[].correct_category_ids` (LIST for Venn) | Items have `correct_category` (singular string) | INADEQUATE -- must be list for Venn |
| `items[].explanation` | Not present | MISSING |
| `items[].difficulty` | Not present | MISSING |
| Matrix-specific: `row_axis_label`, `column_axis_label`, `row_values`, `column_values` | Not present | MISSING |
| Venn-specific: `show_region_labels`, `show_outside_region`, `circle_labels` | Not present | MISSING |

**Verdict**: SortingDesign has 4 fields. Research requires ~25+ configurable properties. Only bucket mode is implicitly supported. Venn (2-circle, 3-circle), matrix, and column modes are entirely unrepresented.

### 2.4 Gap Analysis: BranchingDesign vs. Research (Doc 04)

| Research Requirement | Current State | Gap Type |
|---------------------|---------------|----------|
| `nodes[].type` (decision, information, dialogue, state_check, event, end) | nodes are `List[Dict]` -- untyped | MISSING (no node type field) |
| `nodes[].narrative_text` | Not present | MISSING |
| `nodes[].scene_background_id` | Not present | MISSING |
| `nodes[].characters_present` | Not present | MISSING |
| `nodes[].state_changes_on_enter` | Not present | MISSING |
| `nodes[].is_bottleneck` | Not present | MISSING |
| `nodes[].ending_type` (optimal, acceptable, suboptimal, failure) | Not present | MISSING |
| `nodes[].ending_illustration_id` | Not present | MISSING |
| `nodes[].estimated_difficulty` | Not present | MISSING |
| `choices[].quality` (optimal, acceptable, suboptimal, harmful) | Not present | MISSING |
| `choices[].consequence_text` | Not present | MISSING |
| `choices[].consequence_timing` (immediate, delayed, hidden) | Not present | MISSING |
| `choices[].state_changes` | Not present | MISSING |
| `choices[].character_reactions` | Not present | MISSING |
| `narrative_structure` type (branch_and_bottleneck, foldback, gauntlet, etc.) | Not present | MISSING |
| `characters` array with expressions | Not present | MISSING |
| `scene_backgrounds` array | Not present | MISSING |
| `ending_illustrations` array | Not present | MISSING |
| `state_variables` array with thresholds | Not present | MISSING |
| `initial_state` record | Not present | MISSING |
| `visual_config` (visual_style, color_palette, layout, dialogue_box_style) | Not present | MISSING |
| `interaction_config` (allow_backtrack depth, choice_style, minimap config, etc.) | Partial: allow_backtrack exists as boolean. No depth, choice_style, minimap | INADEQUATE |
| `state_display_config` | Not present | MISSING |
| `narrative_config` (tone, narrator_voice, ending_count) | Not present | MISSING |

**Verdict**: BranchingDesign has 6 fields. Research requires ~40+ fields across node definitions, choice definitions, character/scene assets, state system, and visual configuration. The current schema is a skeletal placeholder with untyped `nodes: List[Dict]`.

### 2.5 Gap Analysis: CompareDesign vs. Research (Doc 05)

| Research Requirement | Current State | Gap Type |
|---------------------|---------------|----------|
| `comparison_mode` (slider, side_by_side, overlay, venn, spot_difference) | Not present | MISSING |
| `category_types` custom list | Not present -- hardcoded to `similar/different/unique_a/unique_b` | MISSING |
| `category_labels` and `category_colors` | Not present | MISSING |
| `exploration_enabled` and `min_explore_time_seconds` | Not present | MISSING |
| `zone_pairings` list of `{zone_a_id, zone_b_id}` | Not present | MISSING |
| `zone_pairing_display` and `zone_pairing_mode` | Not present | MISSING |
| `zoom_enabled`, `zoom_sync_panels` | Not present | MISSING |
| Slider-specific: `slider_orientation`, `slider_initial_position` | Not present | MISSING |
| Overlay-specific: `overlay_initial_opacity`, `overlay_color_coding` | Not present | MISSING |
| Venn-specific: `venn_circle_count`, `venn_show_outside` | Not present | MISSING |
| Spot-difference: `spot_diff_count`, `difference_zones`, `spot_diff_penalty_on_miss` | Not present | MISSING |

**Verdict**: CompareDesign has 3 fields. Research requires ~20+ configurable properties. Only side-by-side mode with basic expected_categories is supported. 4 other comparison modes are unrepresented.

**ComparisonVisualSpec** also needs expansion:
- MISSING: `diagram_a_title`, `diagram_b_title`
- MISSING: `shared_elements: List[str]`
- MISSING: `style_consistency` (matched vs independent)
- MISSING: `spatial_alignment` (aligned vs free)

### 2.6 Gap Analysis: MemoryMatchDesign vs. Research (Doc 02)

| Research Requirement | Current State | Gap Type |
|---------------------|---------------|----------|
| `pairs[].pair_id` | Not present -- pairs are `[{front, back}]` untyped dicts | MISSING |
| `pairs[].front_type` and `back_type` (text, image, equation, audio) | Not present | MISSING |
| `pairs[].front_label`, `back_label` (accessibility) | Not present | MISSING |
| `pairs[].explanation` | Not present | MISSING |
| `pairs[].category` | Not present | MISSING |
| `pairs[].difficulty` | Not present | MISSING |
| `pairs[].zone_id` | Not present | MISSING |
| `pairs[].crop_region` (for diagram_closeup) | Not present | MISSING |
| `game_variant` (classic, column_match, scatter, progressive, peek) | Not present | MISSING |
| `card_face_type` (text_text, text_image, image_image, etc.) | Not present | MISSING |
| `card_back_style` and `card_back_config` | Not present | MISSING |
| `match_type` (identical, term_to_definition, image_to_label, etc.) | Not present | MISSING |
| `card_aspect_ratio` | Not present | MISSING |
| `matched_card_behavior` (fade, shrink, collect, checkmark) | Not present | MISSING |
| `mismatch_penalty` (none, score_decay, life_loss, time_penalty) | Not present | MISSING |
| `lives` | Not present | MISSING |
| `time_limit_seconds` | Not present | MISSING |
| `show_explanation_on_match` and `explanation_display_ms` | Not present | MISSING |
| Progressive config: `initial_pairs`, `pairs_per_round`, `unlock_animation` | Not present | MISSING |
| Column match config: `left_label`, `right_label`, `shuffle_sides`, `connection_style` | Not present | MISSING |
| Scatter config: `scatter_mode`, `card_overlap_allowed`, `drag_snap_distance` | Not present | MISSING |

**Verdict**: MemoryMatchDesign has 4 fields. Research requires ~30+ configurable properties. Only classic concentration with text pairs is representable. 4 other game variants (column_match, scatter, progressive, peek) are unrepresented.

### 2.7 GameDesignV3Slim -- The Structural Problem

`GameDesignV3Slim` is the actual output schema of the V3 game_designer_v3 agent. It uses `SlimMechanicRef` which has ONLY `type: str`. No mechanic-specific config is included at all.

This means:
- The game designer outputs ZERO mechanic configuration.
- All mechanic config must come from downstream agents (scene_architect_v3, interaction_designer_v3).
- But those downstream agents need guidance from the game designer about WHAT kind of configuration is appropriate (e.g., which `comparison_mode`, which `game_variant`).
- **Research says**: Game Planner should decide `sequence_type`, `item_count`, `has_distractors` (sequencing); Game Designer should decide visual style and high-level config.

**Gap**: `SlimMechanicRef` should carry at least a high-level config hint (e.g., `{type: "sequencing", layout_hint: "horizontal_timeline", item_count: 6}`) so downstream agents know what to generate.

---

## 3. scene_spec_v3.py -- Scene Architecture

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/scene_spec_v3.py`

### 3.1 What Exists

- `ZoneSpecV3`: zone_id, label, position_hint, description, hint, difficulty
- `MechanicConfigV3`: type, zone_labels_used, config (Dict), + typed optional fields (path_config, click_config, sequence_config, sorting_config, branching_config, compare_config, memory_config, timed_config, description_match_config)
- `ZoneHierarchyV3`: parent, children, reveal_trigger
- `SceneSpecV3`: scene_number, title, image_description, image_requirements, image_style, zones, mechanic_configs, mechanic_data, zone_hierarchy

### 3.2 Gap Analysis

`MechanicConfigV3` correctly promotes config dicts into typed fields (PathDesign, ClickDesign, etc.) via `_coerce_config`. However, since the underlying typed schemas (SequenceDesign, SortingDesign, etc.) are themselves inadequate (see Section 2), the scene spec inherits all those gaps.

**Additional scene_spec gaps**:

| Gap | Description |
|-----|-------------|
| No dual-image support | `image_description` is singular. For compare_contrast, the scene needs `image_description_a` + `image_description_b` or the ComparisonVisualSpec needs to be embedded |
| No asset generation specs for non-diagram assets | Branching needs scene_backgrounds, character_sprites -- SceneSpecV3 has no fields for these |
| `mechanic_data: Dict[str, Any]` is untyped | This catch-all dict has no schema enforcement, making it impossible to validate mechanic-specific data at the spec stage |
| No per-item image generation specs | For sequencing/sorting/memory items that need illustrations, there is no field to specify image generation prompts |
| No comparison zone pairing data | For compare_contrast, the scene spec should carry zone pairings from the scene architect |

### 3.3 Validation Function Gaps

`validate_scene_specs()` checks:
- trace_path has waypoints
- click_to_identify has prompts or click_options
- sequencing has correct_order
- description_matching has descriptions
- sorting_categories has categories and items
- branching_scenario has nodes
- memory_match has pairs

**Missing validation checks** (based on research):
- `compare_contrast`: No validation that `expected_categories` exist
- `sorting_categories`: No validation that items reference valid category IDs
- `sequencing`: No validation that correct_order references valid item IDs
- `memory_match`: No validation of pair structure (front_type/back_type)
- `branching_scenario`: No validation of node graph connectivity (start_node reachable, all paths terminate)

---

## 4. interaction_spec_v3.py -- Behavioral Layer

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/interaction_spec_v3.py`

### 4.1 What Exists

- `MechanicScoringV3`: mechanic_type, strategy, points_per_correct, max_score, partial_credit, hint_penalty
- `MisconceptionFeedbackV3`: trigger_label, trigger_zone, message
- `MechanicFeedbackV3`: mechanic_type, on_correct, on_incorrect, on_completion, misconception_feedback
- `DistractorFeedbackV3`: distractor, feedback
- `ModeTransitionV3`: from_mechanic, to_mechanic, trigger, trigger_value, animation, message
- `SceneCompletionV3`: trigger, show_results, min_score_to_pass
- `AnimationSpecV3`: on_correct, on_incorrect, on_completion
- `SceneTransitionDetailV3`: trigger, animation, message
- `InteractionSpecV3`: scene_number, scoring, feedback, distractor_feedback, mode_transitions, scene_completion, animations, transition_to_next

### 4.2 Gap Analysis

InteractionSpecV3 is mechanic-agnostic -- it provides scoring, feedback, and transitions per mechanic type. This is the correct level of abstraction. However:

| Gap | Description |
|-----|-------------|
| No mechanic-specific scoring strategies | Research defines per-mechanic scoring: memory_match has `mismatch_penalty` (score_decay/life_loss/time_penalty), sorting has `round_based` correction, branching has `quality` levels (optimal/acceptable/suboptimal/harmful). `MechanicScoringV3.strategy` exists but has only 4 generic values (standard, progressive, mastery, time_based). No mechanic-specific scoring fields. |
| No mechanic-specific completion triggers | `VALID_TRIGGERS` includes `sequence_complete`, `path_complete`, `all_complete` etc. but no `sorting_complete`, `memory_complete`, `branching_complete`, `compare_complete` for the new mechanics. These are needed for mode transitions. |
| AnimationSpecV3 is too generic | Only has on_correct, on_incorrect, on_completion. Research defines per-mechanic animations: memory_match needs `flip_duration_ms`, `mismatch_flip_delay_ms`, `matched_card_behavior`; sorting needs `snap_in`, `container_pulse`; branching needs `scene_transition`, `character_expression_change`. |
| No per-mechanic interaction config | The interaction spec layer should carry mechanic-specific interaction configuration (e.g., `confirm_required` for branching, `submit_mode` for sorting). Currently this is expected to come from scene_spec but the scene_spec schemas are also inadequate. |

### 4.3 Validation Function Gaps

`validate_interaction_specs()` has mechanic-aware checks for click_to_identify, description_matching, trace_path, sequencing. Missing:

- No check that sorting_categories has categories matching those in scene_spec
- No check that memory_match pairs have explanations
- No check that branching nodes form a valid graph
- No check that compare_contrast has expected_categories for all zones

---

## 5. blueprint_schemas.py -- Blueprint Output

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/blueprint_schemas.py`

### 5.1 What Exists

**Standalone template blueprints**: SequenceBuilderBlueprint, BucketSortBlueprint, ParameterPlaygroundBlueprint, TimelineOrderBlueprint, MatchPairsBlueprint, StateTracerCodeBlueprint.

**Multi-scene support**: SceneDiagram, SceneZone, SceneLabel, BlueprintSceneTask, GameScene, GameSequence.

**Sequence config**: SequenceConfigItem, SequenceConfig.

**Interactive Diagram (v3)**: IDSceneAsset, IDZone, IDLabel, IDMechanic, IDMechanicTransition, IDScene, IDSceneTransition, InteractiveDiagramBlueprint.

### 5.2 Gap Analysis

#### IDMechanic
```python
class IDMechanic(BaseModel):
    mechanic_id: str
    mechanic_type: str
    interaction_mode: str
    config: Optional[Dict[str, Any]] = None  # Untyped
    zone_labels: List[str]
    scoring: Optional[Dict[str, Any]] = None  # Untyped
    feedback: Optional[Dict[str, Any]] = None  # Untyped
    animations: Optional[Dict[str, Any]] = None  # Untyped
```

**INADEQUATE**: `config`, `scoring`, `feedback`, `animations` are all untyped `Dict[str, Any]`. There is no schema enforcement at the blueprint level for any mechanic. The frontend must parse arbitrary dicts. This is the root cause of many frontend bugs.

#### InteractiveDiagramBlueprint (v3)

The blueprint has per-scene `IDScene` objects with `mechanics: List[IDMechanic]`. However:

| Gap | Description |
|-----|-------------|
| No per-mechanic typed config at blueprint level | IDMechanic.config is `Dict[str, Any]` -- no SequencingConfig, SortingConfig, etc. |
| No dual-diagram support | IDScene has `diagram_image_url` (singular). Compare mode needs two diagram URLs + two zone lists per scene. |
| No character/sprite references | Branching scenario needs character sprites at scene level. IDScene has no character fields. |
| No state variable system | Branching needs state_variables at blueprint level. Not present. |
| No ending illustrations | Not present |

#### GameScene (legacy multi-scene)

```python
class GameScene(BaseModel):
    sequence_config: Optional[Dict[str, Any]] = None
    mode_config: Optional[Dict[str, Any]] = None
```

Both are untyped dicts. The `SequenceConfig` schema exists but is never used as a typed field -- it is referenced via `Optional[Any]` in `interactive_diagram.py`.

#### SequenceConfig (in blueprint_schemas.py)

This is a STANDALONE template concept (SequenceBuilderBlueprint). It has `SequenceConfigItem(id, text, description)` and `SequenceConfig(sequenceType, items, correctOrder, allowPartialCredit, instructionText)`. This is the legacy schema.

**MISMATCH with research**: SequenceConfigItem has no `image`, `icon`, `category`, `is_distractor`, `order_index`. The research's `SequenceItem` has all of these. The legacy SequenceConfig also lacks all layout/interaction/connector configuration.

---

## 6. interactive_diagram.py -- Frontend Config Schemas

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/interactive_diagram.py`

### 6.1 What Exists

**Sorting**: SortingItem (id, text, correctCategoryId, description), SortingCategory (id, label, description, color), SortingConfig (items, categories, allowPartialCredit, showCategoryHints, instructions).

**Memory Match**: MemoryMatchPair (id, front, back, frontType, backType), MemoryMatchConfig (pairs, gridSize, flipDurationMs, showAttemptsCounter, instructions).

**Branching**: DecisionOption (id, text, nextNodeId, isCorrect, consequence, points), DecisionNode (id, question, description, imageUrl, options, isEndNode, endMessage), BranchingConfig (nodes, startNodeId, showPathTaken, allowBacktrack, showConsequences, multipleValidEndings, instructions).

**Compare**: CompareDiagram (id, name, imageUrl, zones), CompareConfig (diagramA, diagramB, expectedCategories, highlightMatching, instructions).

### 6.2 Gap Analysis: SortingConfig vs. Research (Doc 03)

| Research Field | Current | Gap |
|---------------|---------|-----|
| `sort_mode` | MISSING | Only implicit bucket mode |
| `item_card_type` | MISSING | All items are text-only |
| `container_style` | MISSING | |
| `header_type` | MISSING | |
| `pool_layout` | MISSING | |
| `submit_mode` | MISSING | |
| `allow_multi_category` | MISSING | Items have `correctCategoryId` (singular) not list |
| `max_attempts` | MISSING | |
| `show_category_count` | MISSING | |
| `show_pool_count` | MISSING | |
| `allow_reorder_within` | MISSING | |
| `shuffle_items` | MISSING | |
| SortingCategory.icon | MISSING | |
| SortingCategory.header_image | MISSING | |
| SortingCategory.row_value/column_value | MISSING | |
| SortingItem.image | MISSING | |
| SortingItem.correct_category_ids (list) | `correctCategoryId` singular | INADEQUATE |
| SortingItem.explanation | MISSING | |
| SortingItem.difficulty | MISSING | |
| Matrix config (row_axis_label, etc.) | MISSING | |
| Venn config (show_region_labels, etc.) | MISSING | |

**Total: 23 missing fields, 1 inadequate field.**

### 6.3 Gap Analysis: MemoryMatchConfig vs. Research (Doc 02)

| Research Field | Current | Gap |
|---------------|---------|-----|
| `game_variant` | MISSING | Only classic concentration |
| `card_face_type` | MISSING | |
| `card_back_style` + config | MISSING | |
| `match_type` | MISSING | |
| `card_aspect_ratio` | MISSING | |
| `card_gap_px` | MISSING | |
| `max_grid_width_px` | MISSING | |
| `flip_axis` | MISSING | |
| `mismatch_delay_ms` | MISSING | |
| `matched_card_behavior` | MISSING | |
| `show_match_particles` | MISSING | |
| `mismatch_penalty` | MISSING | |
| `lives` | MISSING | |
| `time_limit_seconds` | MISSING | |
| `show_explanation_on_match` + display_ms | MISSING | |
| Progressive config | MISSING | |
| Column match config | MISSING | |
| Scatter config | MISSING | |
| MemoryMatchPair.pair_id | id exists but no explanation, category, difficulty, zone_id, crop_region | INADEQUATE |
| MemoryMatchPair.explanation | MISSING | |
| MemoryMatchPair.category | MISSING | |
| MemoryMatchPair.difficulty | MISSING | |
| MemoryMatchPair.zone_id | MISSING | |
| MemoryMatchPair.crop_region | MISSING | |

**Total: 24 missing fields, 1 inadequate field.**

### 6.4 Gap Analysis: BranchingConfig vs. Research (Doc 04)

| Research Field | Current | Gap |
|---------------|---------|-----|
| DecisionNode.type (decision/info/dialogue/etc.) | MISSING | |
| DecisionNode.narrative_text | MISSING (has `question` + `description` but not narrative_text) | |
| DecisionNode.scene_background_id | MISSING | |
| DecisionNode.characters_present | MISSING | |
| DecisionNode.state_changes_on_enter | MISSING | |
| DecisionNode.is_bottleneck | MISSING | |
| DecisionNode.ending_type | MISSING | |
| DecisionNode.ending_illustration_id | MISSING | |
| DecisionOption.quality (optimal/acceptable/etc.) | MISSING (has `isCorrect` boolean -- binary, not quality spectrum) | INADEQUATE |
| DecisionOption.consequence_text | Has `consequence` string | OK (naming difference only) |
| DecisionOption.consequence_timing | MISSING | |
| DecisionOption.state_changes | MISSING | |
| DecisionOption.character_reactions | MISSING | |
| BranchingConfig.characters | MISSING | |
| BranchingConfig.scene_backgrounds | MISSING | |
| BranchingConfig.ending_illustrations | MISSING | |
| BranchingConfig.state_variables | MISSING | |
| BranchingConfig.initial_state | MISSING | |
| BranchingConfig.state_display | MISSING | |
| BranchingConfig.minimap config | MISSING | |
| BranchingConfig.visual_config | MISSING | |
| BranchingConfig.narrative_structure | MISSING | |
| BranchingConfig.backtrack_depth | MISSING (has boolean allowBacktrack but no depth) | INADEQUATE |
| BranchingConfig.choice_style | MISSING | |
| BranchingConfig.transition_style + duration | MISSING | |

**Total: 22 missing fields, 2 inadequate fields.**

### 6.5 Gap Analysis: CompareConfig vs. Research (Doc 05)

| Research Field | Current | Gap |
|---------------|---------|-----|
| `comparisonMode` | MISSING | Only side-by-side implicit |
| `categoryTypes` | MISSING | |
| `categoryLabels` | MISSING | |
| `categoryColors` | MISSING | |
| `explorationEnabled` | MISSING | |
| `minExploreTimeSeconds` | MISSING | |
| `zonePairings` | MISSING | |
| `zonePairingDisplay` | MISSING | |
| `zonePairingMode` | MISSING | |
| `zoomEnabled` | MISSING | |
| `zoomSyncPanels` | MISSING | |
| `zoomMaxScale` | MISSING | |
| `zoomShowMinimap` | MISSING | |
| Slider-specific fields | MISSING | |
| Overlay-specific fields | MISSING | |
| Venn-specific fields | MISSING | |
| Spot-difference fields | MISSING | |
| `differenceZones` | MISSING | |
| CompareDiagram.zones[].description | Zones are `List[Dict[str, Any]]` -- untyped | INADEQUATE |

**Total: 18 missing fields, 1 inadequate field.**

---

## 7. domain_knowledge.py -- Domain Knowledge

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/schemas/domain_knowledge.py`

### 7.1 What Exists

- `SequenceItem`: id, text, order_index, description, connects_to
- `SequenceFlowData`: flow_type, sequence_items, flow_description, source_url
- `ContentCharacteristics`: needs_labels, needs_sequence, needs_comparison, sequence_type
- `DomainKnowledgeSource`: url, title, snippet
- `HierarchicalRelationship`: parent, children, relationship_type
- `QueryIntent`: learning_focus, depth_preference, suggested_progression
- `SceneHint`: focus, reason, suggested_scope
- `DomainKnowledge` (Pydantic): query, canonical_labels, acceptable_variants, hierarchical_relationships, sources, query_intent, suggested_reveal_order, scene_hints, sequence_flow_data, content_characteristics
- `EnhancedDomainKnowledge`: extends DomainKnowledge with utility methods

### 7.2 Gap Analysis

| Gap | Description |
|-----|-------------|
| No sorting/categorization knowledge | Research (Doc 03) shows DK should provide category definitions, item-to-category mappings, and multi-property analysis for matrix/Venn modes. ContentCharacteristics has no `needs_categorization` flag. |
| No branching/scenario knowledge | Research (Doc 04) shows DK should provide decision points, consequences, state variables for the subject domain. ContentCharacteristics has no `needs_branching` or `needs_state_system` flag. |
| No memory match knowledge | Research (Doc 02) shows DK should provide term-definition pairs, concept-example pairs, common misconceptions for pair generation. No flag for this. |
| No compare-contrast knowledge | ContentCharacteristics.needs_comparison exists but there are no fields for `shared_elements`, `unique_to_a`, `unique_to_b` lists that the game designer needs to create ComparisonVisualSpec. |
| SequenceItem lacks image/icon fields | Research (Doc 01) shows items need image prompts for visual card types. SequenceItem has only text fields. |

### 7.3 State TypedDict Mismatch

The `DomainKnowledge` TypedDict in `state.py` (lines 321-331) is a SUBSET of the Pydantic `DomainKnowledge` in `domain_knowledge.py`:

**TypedDict version (state.py)**:
- query, canonical_labels, acceptable_variants, hierarchical_relationships, sources, retrieved_at, sequence_flow_data, content_characteristics

**Pydantic version (domain_knowledge.py)**:
- All of the above PLUS: query_intent, suggested_reveal_order, scene_hints

**MISMATCH**: `query_intent`, `suggested_reveal_order`, and `scene_hints` exist in the Pydantic schema but NOT in the state TypedDict. The domain_knowledge_retriever agent likely produces these fields, but downstream agents reading from `state["domain_knowledge"]` will not see them unless the TypedDict is updated. This is a classic state field propagation bug (Debugging Checklist #1).

---

## 8. Cross-Cutting: Bloom's Taxonomy References

All locations where Bloom's taxonomy is referenced in the audited files:

| File | Location | Field | Purpose |
|------|----------|-------|---------|
| state.py | PedagogicalContext | `blooms_level` | Literal with 6 Bloom levels |
| state.py | PedagogicalContext | `blooms_justification` | String justification |
| state.py | TemplateSelection | `bloom_alignment_score` | Float score used in routing |

**Analysis**: Bloom's taxonomy appears only in the `input_enhancer` output (PedagogicalContext) and the `router` output (TemplateSelection). It does NOT appear in any downstream schemas (game_design_v3, scene_spec_v3, interaction_spec_v3, blueprint_schemas, interactive_diagram). The downstream pipeline does not use Bloom's levels at all.

**Recommendation**: If Bloom's taxonomy should be removed from the system, only `state.py` needs modification (PedagogicalContext and TemplateSelection). Additionally, the `input_enhancer` agent prompt and the `router` agent prompt would need updating to stop generating/consuming these fields. No downstream schemas are affected.

---

## 9. Cross-Cutting: New Asset Type State Fields

Research identifies 5 new asset types that the pipeline must generate but that have no representation in state:

| Asset Type | Needed By | Description | State Fields Needed |
|-----------|-----------|-------------|-------------------|
| **Item illustrations** | Sequencing (Doc 01), Sorting (Doc 03) | Per-item card images for image_and_text, image_only card types | `item_illustrations: Optional[Dict[str, str]]` (item_id -> image_url) |
| **Card content images** | Memory Match (Doc 02) | Per-card-face images for image/diagram_closeup face types | `card_face_images: Optional[Dict[str, str]]` (pair_id -> image_url) |
| **Scene backgrounds** | Branching (Doc 04) | Full-screen background images for scenario locations | `scene_background_images: Optional[Dict[str, str]]` (bg_id -> image_url) |
| **Character sprites** | Branching (Doc 04) | Per-character per-expression transparent PNGs | `character_sprite_images: Optional[Dict[str, Dict[str, str]]]` (char_id -> {expression: url}) |
| **Dual diagrams** | Compare (Doc 05) | Two matched diagram images with zones on both | `diagram_image_b`, `zones_b`, `zone_pairings` (see Section 1.2.1) |

None of these exist in AgentState. The current pipeline only generates ONE diagram image and detects zones on it. All 5 new asset types require:
1. New state fields to carry the generated assets
2. New asset generation tools/workflows
3. New blueprint assembler logic to pack them into the frontend config

---

## 10. Summary: Gap Count by Mechanic

| Mechanic | game_design_v3 Gaps | interactive_diagram Gaps | State Gaps | Blueprint Gaps | Total |
|----------|-------------------|------------------------|-----------|---------------|-------|
| **Sequencing** | 17 missing fields | N/A (no frontend schema) | 1 state field | Legacy schema inadequate | ~18 |
| **Sorting** | 15 missing fields | 24 missing fields | 2 state fields | No typed config | ~41 |
| **Branching** | 24 missing fields | 24 missing fields | 4 state fields | No typed config | ~52 |
| **Compare** | 11 missing fields | 19 missing fields | 6 state fields | No typed config | ~36 |
| **Memory Match** | 21 missing fields | 25 missing fields | 2 state fields | No typed config | ~48 |
| **Cross-cutting** | - | - | ~11 state fields | Untyped IDMechanic.config | ~11 |
| **TOTAL** | **~88** | **~92** | **~26** | **~5 structural** | **~206** |

---

## 11. Prioritized Action Items

### P0 -- Pipeline-Blocking (Must fix before any mechanic works)

1. **Fix DomainKnowledge TypedDict <-> Pydantic mismatch** (state.py L321-331): Add `query_intent`, `suggested_reveal_order`, `scene_hints` to the TypedDict.

2. **Add compare_contrast dual-image state fields** (state.py): `diagram_image_b`, `zones_b`, `zone_pairings`, `is_comparison_mode`, `comparison_visual_spec`.

3. **Add branching asset state fields** (state.py): `scene_background_images`, `character_sprite_images`, `ending_illustration_images`, `branching_state_variables`.

4. **Expand ComparisonVisualSpec** (game_design_v3.py): Add `diagram_a_title`, `diagram_b_title`, `shared_elements`, `style_consistency`, `spatial_alignment`.

### P1 -- Mechanic Config Expansion (Required for each mechanic to generate correctly)

5. **Rewrite SequenceDesign** with full layout/interaction/card/connector/slot config from research Doc 01 Section 4.

6. **Rewrite SortingDesign** with sort_mode, item_card_type, container_style, submit_mode, allow_multi_category, matrix/venn-specific fields from research Doc 03 Section 5-6.

7. **Rewrite BranchingDesign** with typed node schema, choice quality levels, state system, character/scene references from research Doc 04 Section 7.

8. **Rewrite CompareDesign** with comparison_mode, exploration config, zone pairing config, zoom config, mode-specific settings from research Doc 05 Section 5-6.

9. **Rewrite MemoryMatchDesign** with game_variant, card_face_type, match_type, card_back config, mismatch_penalty, variant-specific configs from research Doc 02 Section 4.

10. **Mirror all design schema changes in interactive_diagram.py** frontend config schemas (SortingConfig, MemoryMatchConfig, BranchingConfig, CompareConfig).

### P2 -- Blueprint & Validation (Required for frontend to consume correctly)

11. **Type IDMechanic.config** (blueprint_schemas.py): Replace `Dict[str, Any]` with a union of typed per-mechanic config schemas, or add typed optional fields like MechanicConfigV3 does.

12. **Add dual-diagram support to IDScene** (blueprint_schemas.py): Add `diagram_image_b_url`, `zones_b`, `zone_pairings` fields.

13. **Add character/sprite/background support to IDScene** (blueprint_schemas.py): Add `characters`, `scene_backgrounds`, `ending_illustrations` fields for branching.

14. **Add per-item image fields to state** (state.py): `item_illustrations`, `card_face_images` for sequencing/sorting/memory mechanics.

15. **Expand validation functions** (scene_spec_v3.py, interaction_spec_v3.py): Add mechanic-specific validation for sorting (category references), memory (pair structure), branching (graph connectivity), compare (expected_categories coverage).

### P3 -- Slim Schema Enhancement

16. **Expand SlimMechanicRef** (game_design_v3.py): Add optional `config_hint: Dict[str, Any]` so the game designer can pass high-level configuration guidance to downstream agents (e.g., `{layout_mode: "horizontal_timeline"}` for sequencing, `{comparison_mode: "slider"}` for compare).

### P4 -- Bloom's Taxonomy (If removal is desired)

17. **Remove blooms_level and blooms_justification** from PedagogicalContext in state.py.
18. **Remove bloom_alignment_score** from TemplateSelection in state.py.
19. **Update input_enhancer agent prompt** to stop generating Bloom's fields.
20. **Update router agent prompt** to stop consuming bloom_alignment_score.

---

## Appendix A: Field-by-Field Schema Comparison Tables

### A.1 SequenceDesign (Current) vs. SequencingMechanicConfig (Research)

```
CURRENT (4 fields)                     RESEARCH (25+ fields)
------------------------------         ----------------------------------------
sequence_type: str                     layout.layout_mode: 5 options
items: List[Dict[str, str]]            layout.interaction_pattern: 4 options
correct_order: List[str]               layout.source_area: 4 options
instruction_text: Optional[str]        layout.reveal_mode: 4 options
                                       layout.direction: 4 options
                                       layout.scrollable: bool
                                       item_card.card_type: 5 options
                                       item_card.card_size: 3 options
                                       item_card.card_style: 4 options
                                       item_card.show_category_accent: bool
                                       item_card.image_aspect_ratio: 4 options
                                       item_card.show_description: bool
                                       connector.connector_style: 6 options
                                       connector.connector_color: str
                                       connector.animate_connectors: bool
                                       connector.connector_size: 3 options
                                       slot.slot_style: 6 options
                                       slot.slot_labels: List[str]
                                       slot.show_position_numbers: bool
                                       slot.show_endpoints: bool
                                       slot.start_label/end_label: str
                                       instruction_text: str
                                       is_cyclic: bool
                                       sequence_type_label: str
                                       track_theme: 5 options
```

### A.2 SortingDesign (Current) vs. SortingConfig (Research)

```
CURRENT (4 fields)                     RESEARCH (30+ fields)
------------------------------         ----------------------------------------
categories: List[Dict]                 sort_mode: 5 modes (bucket/venn_2/venn_3/matrix/column)
items: List[Dict]                      item_card_type: 5 types
show_category_hints: bool              container_style: 7 styles
instruction_text: Optional[str]        header_type: 4 types
                                       pool_layout: 4 layouts
                                       submit_mode: 4 modes
                                       allow_multi_category: bool
                                       max_attempts: int
                                       show_category_count: bool
                                       show_pool_count: bool
                                       allow_reorder_within: bool
                                       shuffle_items: bool
                                       instructions: str
                                       --- Matrix-specific ---
                                       row_axis_label: str
                                       column_axis_label: str
                                       row_values: List[str]
                                       column_values: List[str]
                                       --- Venn-specific ---
                                       show_region_labels: bool
                                       show_outside_region: bool
                                       circle_labels: List[str]
                                       --- Category fields ---
                                       icon: str
                                       header_image: str
                                       row_value/column_value: str
                                       --- Item fields ---
                                       image: str
                                       correct_category_ids: List[str]  (not singular!)
                                       explanation: str
                                       difficulty: str
```

### A.3 MemoryMatchDesign (Current) vs. MemoryMatchConfig (Research)

```
CURRENT (4 fields)                     RESEARCH (35+ fields)
------------------------------         ----------------------------------------
pairs: List[Dict[str, str]]            game_variant: 5 variants
grid_size: Optional[List[int]]         card_face_type: 6 types
flip_duration_ms: int                  card_back_style: 6 styles + config
instruction_text: Optional[str]        match_type: 7 types
                                       card_aspect_ratio: 3 options
                                       card_gap_px: int
                                       max_grid_width_px: int
                                       flip_axis: Y | X
                                       mismatch_delay_ms: int
                                       matched_card_behavior: 4 behaviors
                                       show_match_particles: bool
                                       mismatch_penalty: 4 types
                                       lives: int | null
                                       time_limit_seconds: int | null
                                       show_attempts_counter: bool
                                       show_explanation_on_match: bool
                                       explanation_display_ms: int
                                       --- Progressive config ---
                                       initial_pairs: int
                                       pairs_per_round: int
                                       unlock_animation: 3 options
                                       --- Column match config ---
                                       left_label: str
                                       right_label: str
                                       shuffle_sides: 3 options
                                       connection_style: 3 options
                                       --- Scatter config ---
                                       scatter_mode: 3 options
                                       card_overlap_allowed: bool
                                       drag_snap_distance: int
                                       --- Per-pair fields ---
                                       pair_id: str
                                       front_type/back_type: 4 types
                                       explanation: str
                                       category: str
                                       difficulty: 1-5
                                       zone_id: str
                                       crop_region: object
```

### A.4 BranchingDesign (Current) vs. PipelineBranchingScenario (Research)

```
CURRENT (6 fields)                     RESEARCH (50+ fields)
------------------------------         ----------------------------------------
nodes: List[Dict]                      scenario_title: str
start_node_id: str                     narrative_structure: 6 types
show_path_taken: bool                  start_node_id: str
allow_backtrack: bool                  nodes: PipelineDecisionNode[]
show_consequences: bool                characters: CharacterSprite[]
multiple_valid_endings: bool           scene_backgrounds: SceneBackground[]
                                       ending_illustrations: array
                                       state_variables: StateVariable[]
                                       initial_state: Record
                                       visual_config: BranchingVisualConfig
                                       interaction_config: BranchingInteractionConfig
                                       state_display_config: StateDisplayConfig
                                       narrative_config: NarrativeConfig
                                       --- Per-node fields ---
                                       type: 6 node types
                                       narrative_text: str
                                       scene_background_id: str
                                       characters_present: array
                                       state_changes_on_enter: array
                                       is_bottleneck: bool
                                       ending_type: 4 types
                                       ending_illustration_id: str
                                       estimated_difficulty: 3 levels
                                       --- Per-choice fields ---
                                       quality: 4 levels (not binary isCorrect!)
                                       consequence_timing: 3 types
                                       state_changes: array
                                       character_reactions: array
```

### A.5 CompareDesign (Current) vs. CompareConfig (Research)

```
CURRENT (3 fields)                     RESEARCH (25+ fields)
------------------------------         ----------------------------------------
expected_categories: Dict[str, str]    comparison_mode: 5 modes
highlight_matching: bool               category_types: custom list
instruction_text: Optional[str]        category_labels/colors: Dict
                                       exploration_enabled: bool
                                       min_explore_time_seconds: int
                                       zone_pairings: array
                                       zone_pairing_display/mode: str
                                       zoom_enabled/sync: bool
                                       --- Slider-specific ---
                                       slider_orientation: 2 options
                                       slider_initial_position: int
                                       --- Overlay-specific ---
                                       overlay_initial_opacity: float
                                       overlay_color_coding: bool
                                       --- Venn-specific ---
                                       venn_circle_count: 2 | 3
                                       venn_show_outside: bool
                                       venn_item_style: 3 options
                                       --- Spot-the-difference ---
                                       spot_diff_count: int
                                       spot_diff_penalty_on_miss: bool
                                       spot_diff_highlight_style: 3 options
                                       difference_zones: array
```

---

## Appendix B: Files Modified Summary

If all P0-P2 action items are implemented, the following files require modification:

| File | Changes |
|------|---------|
| `backend/app/agents/state.py` | Add ~15 new state fields, fix DomainKnowledge TypedDict |
| `backend/app/agents/schemas/game_design_v3.py` | Rewrite 5 mechanic design schemas, expand ComparisonVisualSpec, expand SlimMechanicRef |
| `backend/app/agents/schemas/scene_spec_v3.py` | Update validation to use new schemas, add dual-image fields |
| `backend/app/agents/schemas/interaction_spec_v3.py` | Add mechanic-specific triggers, expand validation |
| `backend/app/agents/schemas/blueprint_schemas.py` | Type IDMechanic.config, add dual-diagram/character fields to IDScene |
| `backend/app/agents/schemas/interactive_diagram.py` | Rewrite SortingConfig, MemoryMatchConfig, BranchingConfig, CompareConfig with full research fields |
| `backend/app/agents/schemas/domain_knowledge.py` | Add categorization/branching/matching knowledge flags |
