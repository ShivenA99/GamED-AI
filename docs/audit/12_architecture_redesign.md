# V3 Pipeline Architecture Redesign

**Date**: 2026-02-14
**Sources**:
- `docs/FRONTEND_BACKEND_CONTRACT.md` — Complete frontend requirements
- `docs/audit/11_v3_pipeline_stage_audit.md` — Per-stage data flow audit
- Agent 3 output — Per-mechanic requirements matrix

---

## 1. Executive Summary

The V3 pipeline has 11 stages producing a blueprint for 10 game mechanics. After auditing the frontend contract, every pipeline stage, and every mechanic end-to-end, we found **7 high-severity gaps** that prevent correct game generation:

| # | Gap | Impact |
|---|-----|--------|
| H1 | Router stage is wasted — output unused | ~3s latency wasted per run |
| H2 | Design validator validates Slim against Full schema — mechanic checks never fire | Silent validation bypass |
| H3 | Scoring/feedback overwrite for repeated mechanics across scenes | Multi-scene data loss |
| H4 | Asset generator is 100% mechanic-agnostic — no sequence/sorting/memory/branching assets | Content-only mechanics have no visual items |
| H5 | Zone matching between vision-detected zones and scene spec zones is fragile | Unmatched zones get placeholder coords |
| H6 | Flat mechanic configs at blueprint root — multi-scene same-mechanic loses per-scene config | Config collision |
| H7 | `compare_contrast` needs TWO diagrams but pipeline generates ONE | Mechanic fundamentally broken |

Additionally:
- `mechanic_contracts.py` (458 lines) is 100% dead code — never imported
- `trace_path` waypoint-zone alignment is broken
- DK retriever conditional population misses mechanics that need enrichment
- 4 dead state fields never populated by any agent

---

## 2. What the Frontend Actually Needs

### 2.1 Per-Mechanic Blueprint Requirements (Summary)

| Mechanic | Config Key | Critical Data | Diagram Needed? | Content Items |
|----------|-----------|---------------|-----------------|---------------|
| `drag_drop` | `dragDropConfig` | zones + labels + correctZoneId | YES (1 per scene) | Labels with zone mapping |
| `click_to_identify` | `clickToIdentifyConfig` + `identificationPrompts` | zones + prompts with zoneId mapping | YES | Prompts [{zoneId, prompt, order}] |
| `trace_path` | `tracePathConfig` + `paths` | zones + paths with waypoint→zone mapping | YES | Paths [{waypoints:[{zoneId,order}]}] |
| `hierarchical` | `zoneGroups` | zones + parent-child groupings | YES | ZoneGroups with reveal triggers |
| `description_matching` | `descriptionMatchingConfig` | zones + descriptions per zone | YES | Descriptions map {zoneId: text} |
| `sequencing` | `sequenceConfig` | items with text/id/order_index + correctOrder | NO | SequenceItems [{id,text,description,icon}] |
| `sorting_categories` | `sortingConfig` | items + categories + correctCategoryId mapping | NO | SortingItems + SortingCategories |
| `memory_match` | `memoryMatchConfig` | pairs with front/back content | NO | MemoryPairs [{id,front,back,explanation}] |
| `branching_scenario` | `branchingConfig` | decision tree nodes + startNodeId | NO | DecisionNodes [{id,question,options,isEndNode}] |
| `compare_contrast` | `compareConfig` | TWO diagrams (diagramA + diagramB) + expectedCategories | YES (2!) | CompareDiagrams + category mapping |

### 2.2 Universal Requirements (All Mechanics)

Every blueprint MUST have:
1. **`diagram.assetUrl`** — A valid image URL (for visual mechanics)
2. **`diagram.zones[]`** — With `id`, `label`, `shape`, and proper coordinates (`points` for polygon, `x/y/radius` for circle, `x/y/width/height` for rect)
3. **`mechanics[]`** — At least one entry with `type`, `scoring {points_per_correct, max_score}`, `feedback {on_correct, on_incorrect, on_completion}`
4. **`scoring` dict** — Keyed by mechanic_type with strategy/points
5. **`feedback` dict** — Keyed by mechanic_type with messages + misconceptions
6. **`modeTransitions[]`** — For multi-mechanic scenes: `{from_mode, to_mode, trigger, trigger_value}`

### 2.3 Multi-Scene Requirements

Multi-scene games (`is_multi_scene: true`) need:
1. **`game_sequence.scenes[]`** — Each with own `diagram`, `zones`, `labels`, `mechanics`, `tasks`
2. **Per-scene configs** — Each scene carries its own mechanic config (e.g., its own `sequenceConfig`)
3. **`game_sequence.total_max_score`** — Sum of all scene max_scores
4. **`tasks[]`** per scene — Linking mechanic_type to zone_ids/label_ids

---

## 3. Current Pipeline vs Requirements — Gap Matrix

### Stage-by-Stage: What Each Stage SHOULD Produce vs What It DOES Produce

#### Stage 1: input_enhancer ✅ NO CHANGES NEEDED
- **Produces**: `pedagogical_context` (blooms_level, subject, difficulty, misconceptions)
- **Status**: Works correctly. All downstream consumers satisfied.

#### Stage 2: domain_knowledge_retriever ⚠️ NEEDS FIXES
- **Produces**: `domain_knowledge` + `canonical_labels`
- **Problems**:
  - `sequence_flow_data` only populated when keyword detection finds "sequence/order/step" — misses implicit sequence questions
  - `comparison_data` only populated when keyword detection finds "compare/difference/similar" — misses implicit comparison questions
  - `label_descriptions` only populated when keyword detection finds "describe/explain/function" — misses most questions
  - `query_intent` (internal dict with needs_labels/needs_sequence/needs_comparison) is **not persisted to state** — downstream agents can't see what DK decided
  - `comparison_data` not in TypedDict (works due to total=False but no type safety)
  - `suggested_reveal_order` and `scene_hints` — dead fields, never populated

#### Stage 3: router ❌ SHOULD BE REMOVED
- **Produces**: `template_selection` (NEVER CONSUMED by any V3 agent)
- **Wastes**: ~2-4 seconds of LLM time
- **Action**: Remove from V3 graph, wire DK retriever directly to game_designer_v3

#### Stage 4: game_designer_v3 ⚠️ NEEDS REDESIGN
- **Produces**: `GameDesignV3Slim` — title, scenes, mechanics as `{type, config_hint, zone_labels_used}`
- **Problems**:
  - `config_hint` is untyped Dict — scene architect must guess what it means
  - No mechanic-specific data at this stage — ALL mechanic content deferred to later stages
  - Scene `visual_description` is a free-text string — no structured image requirements
- **What it SHOULD produce**: For each scene, for each mechanic:
  - Mechanic type + which zones/labels it uses
  - High-level content spec (e.g., "5 sequence steps for blood flow", "3 sorting categories: arteries/veins/capillaries")
  - Image requirements (what the diagram should show, what structures to label)

#### Stage 5: design_validator ⚠️ NEEDS FIX
- **Problems**:
  - Validates Slim against Full `GameDesignV3` schema — model_validator provides defaults for all missing mechanic configs, so mechanic-specific checks NEVER fire
- **Fix**: Validate against `GameDesignV3Slim` schema directly, add explicit checks for per-mechanic content expectations

#### Stage 6: scene_architect_v3 ⚠️ KEY STAGE — NEEDS MAJOR WORK
- **Produces**: `scene_specs_v3` — zones per scene + `mechanic_configs` via `generate_mechanic_content` tool
- **Problems**:
  - Zone definitions depend heavily on what the game designer specified — if zone_labels are vague, zones will be vague
  - `generate_mechanic_content` is the ONLY place per-mechanic content is generated (sequence items, sorting categories, memory pairs, branching nodes, etc.)
  - Quality depends entirely on DK data — if DK is sparse, LLM fallback produces generic content
  - `image_description` and `image_requirements` are free text — no structured spec for asset generator
- **What it SHOULD produce**: For each scene:
  - Precise zone list with labels, shapes, spatial relationships
  - Complete mechanic content (not just config — actual items, prompts, paths, nodes, etc.)
  - Structured image requirements (style, must-include structures, annotation requirements)

#### Stage 7: scene_validator ✅ WORKS (minor improvements possible)
- Validates zone count, mechanic config presence, cross-references with game design

#### Stage 8: interaction_designer_v3 ⚠️ NEEDS FOCUS
- **Produces**: `interaction_specs_v3` — scoring, feedback, mode_transitions, misconceptions per scene
- **Problems**:
  - `mode_transitions` quality is entirely LLM-dependent — no tool validates transition correctness
  - `animations` field produced but NEVER forwarded to blueprint
  - Misconception quality depends on DK data
- **What it SHOULD produce**: Per scene, per mechanic:
  - Validated scoring config (points_per_correct * item_count = max_score)
  - Misconception feedback with specific trigger conditions
  - Mode transitions with correct trigger types and values

#### Stage 9: interaction_validator ✅ WORKS (minor improvements possible)
- Cross-validates scoring/feedback presence per mechanic

#### Stage 10: asset_generator_v3 ❌ MAJOR GAP
- **Produces**: `generated_assets_v3` — ONE diagram_image_url + detected zones per scene
- **Problems**:
  - **100% mechanic-agnostic** — only generates diagram images and detects zones
  - State fields `sequence_item_images`, `sorting_item_images`, `sorting_category_icons`, `memory_card_images` are NEVER populated
  - Zone detection quality varies — fuzzy label matching fails silently
  - `compare_contrast` needs TWO different diagrams — pipeline generates ONE
  - No SVG/flow diagram generation for `trace_path`
  - No step icons for `sequencing`
  - No card images for `memory_match`
- **What it SHOULD produce**: Per scene, per mechanic:
  - Diagram image (for visual mechanics)
  - Detected zones with confident label→zone mapping
  - Mechanic-specific visual assets (step icons, card images, node illustrations, dual diagrams)

#### Stage 11: blueprint_assembler_v3 ⚠️ ALREADY MOSTLY FIXED
- **Produces**: Final `InteractiveDiagramBlueprint` dict
- **Problems** (remaining after our Layer 3-5 fixes):
  - Scoring/feedback dict overwrite for repeated mechanics across scenes (H3)
  - Flat mechanic configs at root — multi-scene same-mechanic collision (H6)
  - Zone matching fragility (H5 — but this is really an asset generator problem)
- **What it SHOULD do**: Pure deterministic assembly — no intelligence, just format conversion. It should NOT need to synthesize missing data.

---

## 4. Proposed Architecture

### 4.1 Design Principles

1. **Each stage has a clear contract**: Input schema → Processing → Output schema, validated at boundaries
2. **Content generation happens ONCE**: Game designer creates the game plan, scene architect creates ALL content (zones, items, nodes, paths), interaction designer adds scoring/feedback. No stage should need to "fix" missing data from upstream.
3. **Asset generation is mechanic-aware**: Different mechanics need different assets — the pipeline must branch accordingly
4. **Blueprint assembly is pure translation**: No LLM calls, no gap-filling, just format conversion from internal schemas to frontend JSON
5. **Validation is structural**: Validators check data completeness and cross-references, not re-generate content
6. **DK enrichment drives quality**: The domain knowledge stage should detect ALL needed data types (descriptions, sequences, comparisons, hierarchies) regardless of keyword matching

### 4.2 Proposed Stage Flow

```
                    question_text, question_options
                              |
                    [input_enhancer]                    (unchanged)
                              |
                    pedagogical_context
                              |
                [domain_knowledge_retriever]            (enhanced intent detection)
                              |
            domain_knowledge, canonical_labels
                              |
                    [game_designer_v3]                  (richer output)
                              |
              game_design_v3 (GameDesignV3Full)
                     - per-scene mechanic specs
                     - content requirements per mechanic
                     - image requirements per scene
                              |
                    [design_validator]                  (validates against correct schema)
                              |
                   [scene_architect_v3]                 (THE key content stage)
                              |
     scene_specs_v3 (full content per scene per mechanic)
          - zones with spatial specs
          - sequence items (with text, descriptions, icons)
          - sorting items + categories (with correct mappings)
          - memory pairs (with front/back/explanation)
          - branching nodes (with question/options/consequences)
          - compare features (with expected categories)
          - trace path waypoints (with zone references)
          - click prompts (with zone references)
          - description matching entries (with zone descriptions)
          - image specs (structured, not free-text)
                              |
                    [scene_validator]                   (validates completeness)
                              |
                [interaction_designer_v3]               (scoring + feedback ONLY)
                              |
   interaction_specs_v3 (scoring, feedback, transitions)
          - per-scene per-mechanic scoring configs
          - misconception feedback with triggers
          - mode transitions with validated triggers
          - scene completion criteria
                              |
                 [interaction_validator]                (validates arithmetic + transitions)
                              |
                  [asset_generator_v3]                  (mechanic-aware)
                              |
    generated_assets_v3 (per scene per mechanic)
          - diagram images (for visual mechanics)
          - detected zones (with label confidence)
          - dual diagrams (for compare_contrast)
          - [future: step icons, card images, etc.]
                              |
                [blueprint_assembler_v3]                (pure translation)
                              |
           blueprint (InteractiveDiagramBlueprint)
```

### 4.3 Key Changes from Current Architecture

| Change | Rationale |
|--------|-----------|
| **Remove router** | Output is never consumed; saves 2-4s |
| **Enhance DK retriever intent detection** | Use LLM instead of keyword matching for intent; persist intent to state |
| **Game designer outputs richer specs** | Per-scene: mechanic content requirements + image requirements (not just type + config_hint) |
| **Design validator targets correct schema** | Validate against what game_designer actually produces |
| **Scene architect generates ALL content** | Single stage responsible for all mechanic-specific content: items, nodes, pairs, paths, prompts, descriptions |
| **Scene validator checks content completeness** | Verify every mechanic has its required content items populated |
| **Interaction designer focuses on scoring/feedback** | No content generation — only scoring strategy, feedback messages, misconceptions, mode transitions |
| **Interaction validator checks arithmetic** | Verify points_per_correct * item_count = max_score, transition triggers valid |
| **Asset generator becomes mechanic-aware** | Route to different asset strategies per mechanic type |
| **Blueprint assembler stays deterministic** | No gap-filling — if data is missing, fail loudly |

---

## 5. Per-Stage Detailed Specifications

### 5.1 Stage 1: input_enhancer (UNCHANGED)

**Input**: `question_text`, `question_options`
**Output**: `pedagogical_context`
**No changes needed.**

### 5.2 Stage 2: domain_knowledge_retriever (ENHANCED)

**Input**: `question_text`, `pedagogical_context`
**Output**: `domain_knowledge`, `canonical_labels`

**Changes**:

1. **Replace keyword-based intent detection with LLM call**:
   - Current: `_detect_query_intent()` uses keyword matching ("sequence", "order", "compare", etc.)
   - New: Single LLM call that classifies the question into needed data types:
     ```python
     intent = {
         "needs_labels": bool,         # Always true for diagram games
         "needs_descriptions": bool,    # For description_matching, click_to_identify
         "needs_sequence": bool,        # For sequencing, trace_path
         "needs_comparison": bool,      # For compare_contrast, sorting
         "needs_hierarchy": bool,       # For hierarchical
         "suggested_mechanics": [str],  # Best mechanic types for this content
         "content_domain": str,         # "anatomy"|"chemistry"|"geography"|...
     }
     ```

2. **Always populate ALL enrichment fields**:
   - Current: `label_descriptions`, `sequence_flow_data`, `comparison_data` are conditionally populated
   - New: Always attempt ALL enrichment. If the content doesn't naturally fit (e.g., no sequence exists), the field is `null` — not "missing because we didn't detect keywords"

3. **Persist intent to state**:
   - Add `dk_intent` field to AgentState TypedDict
   - Downstream agents can read what DK decided about the content

4. **Add `comparison_data` to TypedDict**:
   - Currently missing from `DomainKnowledge` TypedDict in state.py

5. **Remove dead fields**: `suggested_reveal_order`, `scene_hints`, `query_intent` (string form)

### 5.3 Stage 3: router — REMOVED

Remove from V3 graph. Wire `domain_knowledge_retriever → game_designer_v3` directly.

### 5.4 Stage 4: game_designer_v3 (ENHANCED OUTPUT)

**Input**: `question_text`, `pedagogical_context`, `domain_knowledge`, `canonical_labels`
**Output**: `game_design_v3` (richer schema)

**New output schema** (`GameDesignV3` — replaces `GameDesignV3Slim`):

```python
game_design_v3 = {
    "title": str,
    "total_scenes": int,        # 1-4
    "difficulty": str,
    "estimated_duration_minutes": int,
    "subject": str,
    "labels": {
        "zone_labels": [str],
        "distractor_labels": [str],
        "hierarchy": {},        # Optional parent-child
    },
    "scenes": [
        {
            "scene_number": int,
            "title": str,
            "learning_goal": str,
            "image_spec": {
                "description": str,         # What to search/generate
                "must_include": [str],      # Structures that MUST be visible
                "style": str,               # "cross-section"|"labeled"|"flowchart"|...
                "annotation_type": str,     # "none"|"numbered"|"labeled"
            },
            "zone_labels_in_scene": [str],
            "mechanics": [
                {
                    "type": str,            # MechanicType
                    "zone_labels_used": [str],
                    "content_spec": {
                        # Mechanic-specific content requirements:
                        # sequencing: {item_count, sequence_topic}
                        # sorting: {category_count, items_per_category, sorting_topic}
                        # memory_match: {pair_count, match_type}
                        # branching: {node_count, narrative_topic}
                        # compare_contrast: {subject_a, subject_b, criteria}
                        # trace_path: {path_count, process_name}
                        # click_to_identify: {prompt_style}
                        # description_matching: {description_source}
                        # drag_drop: {} (uses zones/labels directly)
                        # hierarchical: {group_count, reveal_strategy}
                    },
                }
            ],
        }
    ],
}
```

**Key difference from Slim**: Each mechanic has a `content_spec` dict that tells the scene architect exactly what content to generate — not a vague `config_hint`.

### 5.5 Stage 5: design_validator (FIXED)

**Changes**:
1. Validate against the new `GameDesignV3` schema (not Full with model_validator defaults)
2. Check that every mechanic's `content_spec` has the required fields for its type
3. Check that `image_spec.must_include` covers the `zone_labels_in_scene`
4. Check that mechanics needing diagrams have `image_spec` populated

### 5.6 Stage 6: scene_architect_v3 (THE KEY CONTENT STAGE)

**Input**: `game_design_v3`, `domain_knowledge`, `canonical_labels`
**Output**: `scene_specs_v3`

This is where ALL mechanic-specific content is generated. The `generate_mechanic_content` tool must produce complete, ready-to-assemble content.

**New output schema** (`SceneSpecV3` per scene):

```python
scene_spec = {
    "scene_number": int,
    "title": str,
    "learning_goal": str,

    # Image specification (structured)
    "image_spec": {
        "search_query": str,          # Exact query for image search
        "generation_prompt": str,      # Prompt for AI image generation
        "must_include_labels": [str],  # Labels that must be visible in image
        "style": str,
        "dimensions": {"width": int, "height": int},
    },

    # Zone definitions
    "zones": [
        {
            "label": str,
            "description": str,        # 1-2 sentence description
            "hint": str,               # Hint text for the player
            "difficulty": int,         # 1-5
            "parent_label": str,       # For hierarchical: parent zone label (or null)
        }
    ],

    # Per-mechanic content (COMPLETE content, not config hints)
    "mechanic_content": {
        "drag_drop": {
            "labels": [{"text": str, "zone_label": str}],
            "distractor_labels": [str],
        },
        "click_to_identify": {
            "prompts": [{"zone_label": str, "prompt_text": str, "order": int}],
            "prompt_style": str,
            "selection_mode": str,
        },
        "trace_path": {
            "paths": [
                {
                    "id": str,
                    "description": str,
                    "requires_order": bool,
                    "waypoints": [{"zone_label": str, "order": int}],
                }
            ],
            "path_type": str,           # "linear"|"cyclic"|"branching"
            "drawing_mode": str,        # "click_waypoints"|"freehand"|"guided"
            "particle_theme": str,
            "particle_speed": str,      # "slow"|"medium"|"fast"
        },
        "hierarchical": {
            "groups": [
                {"parent_label": str, "child_labels": [str], "reveal_trigger": str}
            ],
        },
        "description_matching": {
            "descriptions": [{"zone_label": str, "description": str}],
            "mode": str,                # "click_zone"|"drag_description"|"multiple_choice"
            "distractor_descriptions": [str],
        },
        "sequencing": {
            "items": [
                {
                    "id": str,
                    "text": str,
                    "description": str,
                    "icon": str,         # Emoji or icon name
                    "order_index": int,  # Correct position (0-based)
                    "is_distractor": bool,
                }
            ],
            "correct_order": [str],      # Item IDs in correct order
            "sequence_type": str,        # "linear"|"cyclic"|"branching"
            "layout_mode": str,
            "instruction_text": str,
        },
        "sorting_categories": {
            "categories": [
                {"id": str, "label": str, "description": str, "color": str}
            ],
            "items": [
                {
                    "id": str,
                    "text": str,
                    "correct_category_id": str,
                    "correct_category_ids": [str],  # For multi-category
                    "description": str,
                    "difficulty": str,
                }
            ],
            "sort_mode": str,
            "instruction_text": str,
        },
        "memory_match": {
            "pairs": [
                {
                    "id": str,
                    "front": str,
                    "back": str,
                    "front_type": str,   # "text"|"image"
                    "back_type": str,
                    "explanation": str,
                    "category": str,
                }
            ],
            "match_type": str,
            "game_variant": str,
            "grid_size": [int, int],    # [cols, rows]
        },
        "branching_scenario": {
            "nodes": [
                {
                    "id": str,
                    "question": str,
                    "description": str,
                    "node_type": str,    # "decision"|"info"|"ending"|"checkpoint"
                    "is_end_node": bool,
                    "end_message": str,
                    "ending_type": str,  # "good"|"neutral"|"bad"
                    "options": [
                        {
                            "id": str,
                            "text": str,
                            "next_node_id": str,  # null for endpoints
                            "is_correct": bool,
                            "consequence": str,
                            "points": int,
                        }
                    ],
                }
            ],
            "start_node_id": str,
            "narrative_structure": str,
        },
        "compare_contrast": {
            "subject_a": {
                "name": str,
                "description": str,
                "zone_labels": [str],    # Which zones belong to subject A
            },
            "subject_b": {
                "name": str,
                "description": str,
                "zone_labels": [str],    # Which zones belong to subject B
            },
            "expected_categories": {     # zone_label -> category
                "label": "similar"|"different"|"unique_a"|"unique_b",
            },
            "comparison_mode": str,
            "needs_second_image": bool,
            "second_image_spec": {},     # Same as image_spec, for the second diagram
        },
    },
}
```

**Critical design decision**: The `mechanic_content` dict only contains entries for mechanics that appear in this scene's `mechanics[]` list. Empty mechanics are not included.

### 5.7 Stage 7: scene_validator (ENHANCED)

**New validations**:
1. For each mechanic in a scene, verify its `mechanic_content[type]` exists and has all required fields
2. Verify zone labels in mechanic content reference actual zones in the zone list
3. Verify `correct_order` IDs match item IDs (sequencing)
4. Verify `correct_category_id` references exist in categories list (sorting)
5. Verify branching graph has no orphan nodes and `start_node_id` exists
6. Verify compare_contrast has at least 2 zone_labels per subject
7. Verify trace_path waypoints reference actual zone labels

### 5.8 Stage 8: interaction_designer_v3 (FOCUSED)

**Input**: `game_design_v3`, `scene_specs_v3`, `domain_knowledge`
**Output**: `interaction_specs_v3`

This stage should ONLY handle scoring, feedback, and transitions. No content generation.

**Output schema** (per scene):

```python
interaction_spec = {
    "scene_number": int,
    "scoring": [
        {
            "mechanic_type": str,
            "strategy": str,          # "per_item"|"all_or_nothing"|"progressive"
            "points_per_correct": int,
            "max_score": int,         # MUST equal points_per_correct * item_count
            "partial_credit": bool,
            "hint_penalty": float,
        }
    ],
    "feedback": [
        {
            "mechanic_type": str,
            "on_correct": str,
            "on_incorrect": str,
            "on_completion": str,
            "misconception_feedback": [
                {
                    "misconception": str,
                    "trigger": str,        # Zone/item that triggers this
                    "feedback": str,
                    "severity": str,
                }
            ],
        }
    ],
    "mode_transitions": [
        {
            "from_mode": str,
            "to_mode": str,
            "trigger": str,           # "completion"|"score_threshold"|"time"
            "trigger_value": Any,
        }
    ],
    "scene_completion": {
        "required_score": float,
        "celebration": str,
    },
}
```

### 5.9 Stage 9: interaction_validator (ENHANCED)

**New validations**:
1. **Arithmetic check**: `points_per_correct * item_count` should equal `max_score` for each mechanic
2. **Transition validation**: Mode transitions reference valid mechanic types that exist in the scene
3. **Trigger value ranges**: `score_threshold` trigger_value must be 0.0-1.0
4. **Total max_score**: Sum across all scenes should be 50-500

### 5.10 Stage 10: asset_generator_v3 (MECHANIC-AWARE)

**Input**: `scene_specs_v3`, `game_design_v3`, `canonical_labels`
**Output**: `generated_assets_v3`

**Key change**: Route to different asset strategies based on mechanic type.

```python
generated_assets_v3 = {
    "scenes": {
        "1": {
            # ALWAYS: primary diagram
            "diagram_image_url": str,
            "diagram_image_path": str,
            "zones": [
                {
                    "id": str,
                    "label": str,
                    "shape": str,
                    "coordinates": {},
                    "confidence": float,
                }
            ],
            "zone_detection_method": str,

            # FOR compare_contrast: second diagram
            "second_diagram_image_url": str,  # Only if compare_contrast
            "second_diagram_zones": [],

            # Zone matching report
            "zone_match_report": {
                "matched": [{"spec_label": str, "detected_label": str, "confidence": float}],
                "unmatched_spec": [str],    # Labels in spec but not detected
                "unmatched_detected": [str], # Detected but not in spec
            },
        },
    },
    "metadata": {
        "source": str,
        "scene_count": int,
        "total_zones": int,
    },
}
```

**Asset generation routing**:

| Mechanic Category | Asset Strategy |
|-------------------|---------------|
| Visual mechanics (drag_drop, click_to_identify, trace_path, hierarchical, description_matching) | Search/generate diagram → detect zones → match to spec labels |
| compare_contrast | Search/generate TWO diagrams (one per subject) → detect zones on each |
| Content-only (sequencing, sorting, memory_match, branching) | NO diagram needed. Skip image search entirely. |
| Mixed scenes (visual + content) | Generate diagram for visual mechanic's zones only |

**Zone matching improvements**:
1. Use the scene_spec zone labels as the source of truth
2. After zone detection, run a matching pass that uses fuzzy string matching + vision model re-query for unmatched labels
3. Report match quality metrics so blueprint assembler can decide whether to use detected coords or generate placeholders

### 5.11 Stage 11: blueprint_assembler_v3 (PURE TRANSLATION)

**Input**: `game_design_v3`, `scene_specs_v3`, `interaction_specs_v3`, `generated_assets_v3`
**Output**: `blueprint` (InteractiveDiagramBlueprint)

**Design principle**: NO intelligence, NO gap-filling, NO LLM calls. Pure deterministic format conversion.

**Key assembly rules**:

1. **Per-scene configs** (multi-scene): Each scene in `game_sequence.scenes[]` carries its own mechanic configs
2. **Scoring/feedback**: Keyed by `{scene_number}_{mechanic_type}` to avoid overwrites for repeated mechanics
3. **Zone ID generation**: Deterministic: `zone_{scene_number}_{index}`
4. **Label ID generation**: Deterministic: `label_{scene_number}_{index}`
5. **Zone coordinate source**: Use `generated_assets_v3.scenes[n].zones` coordinates, falling back to scene_spec spatial hints
6. **CamelCase normalization**: All output keys in camelCase (frontend canonical form)
7. **Fail loudly**: If required data is missing, set a `_warnings` array on the blueprint rather than silently generating placeholder data

---

## 6. Per-Mechanic Data Flow (New Architecture)

### 6.1 drag_drop

```
Game Designer: scene.mechanics = [{type: "drag_drop", zone_labels_used: [...]}]
     ↓
Scene Architect: mechanic_content.drag_drop = {labels, distractor_labels}
     ↓
Interaction Designer: scoring[drag_drop] = {per_item, 10pts, N*10 max}
     ↓
Asset Generator: diagram image + zone detection → matched zones
     ↓
Blueprint: zones[], labels[{correctZoneId}], dragDropConfig, mechanics[{type, scoring, feedback}]
```

### 6.2 click_to_identify

```
Game Designer: scene.mechanics = [{type: "click_to_identify", content_spec: {prompt_style: "naming"}}]
     ↓
Scene Architect: mechanic_content.click_to_identify = {prompts[{zone_label, prompt_text, order}], prompt_style}
     ↓
Interaction Designer: scoring[click_to_identify] = {per_item, 10pts}
     ↓
Asset Generator: diagram image + zone detection
     ↓
Blueprint: zones[], identificationPrompts[{zoneId, prompt, order}], clickToIdentifyConfig
```

### 6.3 trace_path

```
Game Designer: scene.mechanics = [{type: "trace_path", content_spec: {path_count: 1, process_name: "blood flow"}}]
     ↓
Scene Architect: mechanic_content.trace_path = {paths[{waypoints[{zone_label, order}]}], path_type, drawing_mode}
     ↓
Interaction Designer: scoring[trace_path] = {per_item, 10pts per waypoint}
     ↓
Asset Generator: diagram image + zone detection (waypoint zones must match)
     ↓
Blueprint: zones[], paths[{waypoints[{zoneId, order}]}], tracePathConfig
```

### 6.4 sequencing (NO DIAGRAM)

```
Game Designer: scene.mechanics = [{type: "sequencing", content_spec: {item_count: 5, sequence_topic: "blood flow steps"}}]
     ↓
Scene Architect: mechanic_content.sequencing = {items[{id, text, description, order_index}], correct_order, layout_mode}
     ↓
Interaction Designer: scoring[sequencing] = {per_item, 10pts, 50 max}
     ↓
Asset Generator: SKIP (no diagram needed)
     ↓
Blueprint: sequenceConfig{items, correctOrder, sequenceType, layoutMode}
```

### 6.5 sorting_categories (NO DIAGRAM)

```
Game Designer: scene.mechanics = [{type: "sorting_categories", content_spec: {category_count: 3}}]
     ↓
Scene Architect: mechanic_content.sorting_categories = {categories[{id, label}], items[{id, text, correct_category_id}]}
     ↓
Interaction Designer: scoring[sorting] = {per_item, 10pts}
     ↓
Asset Generator: SKIP
     ↓
Blueprint: sortingConfig{categories, items, sortMode, containerStyle}
```

### 6.6 memory_match (NO DIAGRAM)

```
Game Designer: scene.mechanics = [{type: "memory_match", content_spec: {pair_count: 6, match_type: "term_to_definition"}}]
     ↓
Scene Architect: mechanic_content.memory_match = {pairs[{id, front, back, explanation}], match_type, grid_size}
     ↓
Interaction Designer: scoring[memory_match] = {per_item, 10pts per pair}
     ↓
Asset Generator: SKIP
     ↓
Blueprint: memoryMatchConfig{pairs, gridSize, gameVariant, matchType}
```

### 6.7 branching_scenario (NO DIAGRAM)

```
Game Designer: scene.mechanics = [{type: "branching_scenario", content_spec: {node_count: 5, narrative_topic: "treating a patient"}}]
     ↓
Scene Architect: mechanic_content.branching_scenario = {nodes[{id, question, options[{text, next_node_id, is_correct}]}], start_node_id}
     ↓
Interaction Designer: scoring[branching] = {per_item, 10pts per non-end node}
     ↓
Asset Generator: SKIP
     ↓
Blueprint: branchingConfig{nodes[{id, question, options[{nextNodeId, isCorrect}]}], startNodeId}
```

### 6.8 compare_contrast (DUAL DIAGRAM)

```
Game Designer: scene.mechanics = [{type: "compare_contrast", content_spec: {subject_a: "plant cell", subject_b: "animal cell"}}]
     ↓
Scene Architect: mechanic_content.compare_contrast = {subject_a{name, zone_labels}, subject_b{name, zone_labels}, expected_categories, needs_second_image: true, second_image_spec{...}}
     ↓
Interaction Designer: scoring[compare] = {per_item, 10pts per categorization}
     ↓
Asset Generator: Generate TWO diagrams (one per subject) + zone detection on each
     ↓
Blueprint: compareConfig{diagramA{id, name, imageUrl, zones}, diagramB{id, name, imageUrl, zones}, expectedCategories}
```

### 6.9 description_matching

```
Game Designer: scene.mechanics = [{type: "description_matching", content_spec: {description_source: "zone_descriptions"}}]
     ↓
Scene Architect: mechanic_content.description_matching = {descriptions[{zone_label, description}], mode, distractor_descriptions}
     ↓
Interaction Designer: scoring[description_matching] = {per_item, 10pts per match}
     ↓
Asset Generator: diagram image + zone detection
     ↓
Blueprint: descriptionMatchingConfig{descriptions: {zoneId: description}, mode}
```

### 6.10 hierarchical

```
Game Designer: scene.mechanics = [{type: "hierarchical", content_spec: {group_count: 2}}]
     ↓
Scene Architect: mechanic_content.hierarchical = {groups[{parent_label, child_labels, reveal_trigger}]}
     ↓
Interaction Designer: scoring[hierarchical] = {per_item, 10pts per zone including children}
     ↓
Asset Generator: diagram image + zone detection (must detect parent + child zones)
     ↓
Blueprint: zoneGroups[{parentZoneId, childZoneIds, revealTrigger}], zones[{parentZoneId}]
```

---

## 7. Multi-Mechanic Scenes (Mode Transitions)

When a scene has multiple mechanics, the flow is:

1. **Game designer** lists mechanics in scene order: `[{type: "drag_drop"}, {type: "click_to_identify"}]`
2. **Scene architect** generates content for EACH mechanic in the scene
3. **Interaction designer** generates:
   - Scoring/feedback per mechanic
   - Mode transitions: `[{from: "drag_drop", to: "click_to_identify", trigger: "completion"}]`
4. **Blueprint assembler** sets:
   - `mechanics[0].type` = starting mode
   - `modeTransitions[]` = transition rules
   - All mechanic-specific configs at root (or per-scene in multi-scene)

**Trigger types supported by frontend**:
- `completion` — All items correct in current mode
- `score_threshold` — Score reaches X% (trigger_value: 0.0-1.0)
- `time_elapsed` — Timer reaches N seconds
- `user_choice` — User clicks "Next" button
- `specific_zones` — Specific zones completed

---

## 8. Implementation Priority

### Phase A: Schema + Validation (Foundation)
1. Define new `GameDesignV3` output schema with `content_spec` per mechanic
2. Define new `SceneSpecV3` schema with `mechanic_content` dict
3. Fix design_validator to validate against correct schema
4. Enhance scene_validator with per-mechanic content checks
5. Enhance interaction_validator with arithmetic checks

### Phase B: DK Retriever Enhancement
6. Replace keyword-based intent detection with LLM classification
7. Always attempt all enrichment fields
8. Persist intent to state
9. Add `comparison_data` to TypedDict

### Phase C: Game Designer Enhancement
10. Update game_designer_v3 prompt to produce richer output with `content_spec`
11. Update submit_game_design tool to validate new schema
12. Remove router from graph (wire DK → game_designer directly)

### Phase D: Scene Architect Rewrite
13. Rewrite `generate_mechanic_content` tool for all 10 mechanics with complete content generation
14. Update scene_architect_v3 prompt to drive complete content creation
15. Update scene_validator to check new schema

### Phase E: Asset Generator Enhancement
16. Add mechanic-aware routing (skip image for content-only mechanics)
17. Add dual-diagram generation for compare_contrast
18. Improve zone matching with confidence reporting

### Phase F: Blueprint Assembler Cleanup
19. Update assembly to read new schema format
20. Add per-scene mechanic configs for multi-scene (no root-level collision)
21. Fix scoring/feedback keying for repeated mechanics
22. Remove gap-filling logic — fail loudly on missing data

---

## 9. State Field Changes

### New Fields

| Field | Type | Written By | Read By |
|-------|------|------------|---------|
| `dk_intent` | `Dict[str, Any]` | domain_knowledge_retriever | game_designer_v3, scene_architect_v3 |

### Modified Fields

| Field | Change | Reason |
|-------|--------|--------|
| `game_design_v3` | Richer schema with `content_spec` | Game designer produces structured requirements |
| `scene_specs_v3` | `mechanic_content` dict replaces flat `mechanic_configs` | Complete content per mechanic |
| `generated_assets_v3` | `zone_match_report` + `second_diagram_*` | Mechanic-aware asset generation |

### Removed Fields

| Field | Reason |
|-------|--------|
| `template_selection` | Router removed |
| `routing_confidence` | Router removed |
| `suggested_reveal_order` | Dead field, never populated |
| `scene_hints` | Dead field, never populated |
| `diagram_crop_regions` | Dead field, never populated |

### Dead Code to Remove

| File | Reason |
|------|--------|
| `backend/app/config/mechanic_contracts.py` | 458 lines, never imported by any agent/tool/service |
| Router V3 path in `router.py` | Stage removed from V3 graph |

---

## 10. Model Assignment (Proposed)

| Stage | Model | Temperature | Rationale |
|-------|-------|-------------|-----------|
| input_enhancer | gemini-2.5-flash-lite | 0.3 | Simple classification, unchanged |
| domain_knowledge_retriever | gemini-2.5-flash | 0.2 | Upgraded from flash-lite: intent detection needs better reasoning |
| game_designer_v3 | gemini-2.5-pro | 0.7 | Complex creative task, unchanged |
| design_validator | None (deterministic) | N/A | Unchanged |
| scene_architect_v3 | gemini-2.5-pro | 0.5 | Critical content generation, unchanged |
| scene_validator | None (deterministic) | N/A | Unchanged |
| interaction_designer_v3 | gemini-2.5-pro | 0.5 | Scoring/feedback design, unchanged |
| interaction_validator | None (deterministic) | N/A | Unchanged |
| asset_generator_v3 | gemini-2.5-flash | 0.3 | Image search/generation, unchanged |
| blueprint_assembler_v3 | None (deterministic) | N/A | Unchanged |

---

## 11. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Scene architect generates too much content (token limits) | Use max_iterations=20 with clear tool-per-mechanic strategy; split large scenes into multiple tool calls |
| DK retriever enrichment adds latency | Run enrichment calls in parallel; cache web search results |
| Compare_contrast dual diagram doubles asset gen time | Parallel image search for both subjects |
| New schemas break existing runs | Version the schemas; blueprint assembler handles both old and new format during transition |
| Game designer produces wrong content_spec | Design validator catches structural issues; scene architect has fallback prompts |

---

## Appendix: File Change Map

| File | Changes |
|------|---------|
| `backend/app/agents/state.py` | Add `dk_intent`, remove dead fields |
| `backend/app/agents/graph.py` | Remove router node from V3 graph, rewire |
| `backend/app/agents/schemas/game_design_v3.py` | New GameDesignV3 schema with content_spec |
| `backend/app/agents/schemas/scene_spec_v3.py` | New SceneSpecV3 schema with mechanic_content |
| `backend/app/agents/domain_knowledge_retriever.py` | LLM intent detection, always-populate, persist intent |
| `backend/app/agents/game_designer_v3.py` | Updated prompt for richer output |
| `backend/app/agents/design_validator.py` | Validate correct schema, per-mechanic checks |
| `backend/app/agents/scene_architect_v3.py` | Updated prompt for complete content generation |
| `backend/app/agents/scene_validator.py` | Per-mechanic content completeness checks |
| `backend/app/agents/interaction_designer_v3.py` | Focus on scoring/feedback only |
| `backend/app/agents/interaction_validator.py` | Arithmetic + transition validation |
| `backend/app/agents/asset_generator_v3.py` | Mechanic-aware routing, dual diagram, zone matching |
| `backend/app/tools/scene_architect_tools.py` | Rewritten generate_mechanic_content for all 10 mechanics |
| `backend/app/tools/blueprint_assembler_tools.py` | Updated assembly for new schemas, per-scene configs |
| `backend/app/tools/game_design_tools.py` | Updated validation for new schema |
| `backend/app/agents/instrumentation.py` | Remove router keys, add dk_intent |
| `frontend/src/components/pipeline/PipelineView.tsx` | Remove router from graph visualization |
