# V4 Creative Data Flow Audit — Full Field-by-Field Trace

**Date**: 2026-02-17
**Scope**: Trace every field from `GameConcept` → `SceneCreativeDesign` → `GamePlan` → `MechanicContent` → `InteractionResult` → `AssetResult` → `InteractiveDiagramBlueprint`, identifying what survives, what's consumed, and what's dropped.

---

## 1. Architecture Overview

The V4 pipeline has a **3-stage creative cascade** followed by **3 downstream consumer stages** and a **final assembler**:

```
Phase 0:  input_analyzer + dk_retriever (parallel)
Phase 1a: game_concept_designer → concept_validator → [retry loop]
Phase 1b: scene_designer ×N (parallel Send)  → scene_design_merge → [retry loop]
          graph_builder (deterministic) → game_plan_validator
Phase 2a: content_generator ×M (parallel Send) → content_merge
Phase 2b: interaction_designer ×N (parallel Send) → interaction_merge
Phase 3:  asset_worker ×N (parallel Send) → asset_merge
Phase 4:  blueprint_assembler (deterministic)
```

**Key principle**: Each stage reads upstream creative direction and transforms it into its own output. The assembler then combines all outputs into the final `InteractiveDiagramBlueprint`.

---

## 2. Level-by-Level Data Flow

### 2.1 GAME LEVEL: GameConcept → GamePlan → Blueprint

#### Source: `GameConcept` (schema: `game_concept.py`)

| Field | Type | Purpose |
|---|---|---|
| `title` | str | Game title |
| `subject` | str | Subject area |
| `difficulty` | Literal["beginner","intermediate","advanced"] | Difficulty level |
| `estimated_duration_minutes` | int (1-30) | Estimated play time |
| `narrative_theme` | str | Overall narrative theme |
| `narrative_intro` | str | Opening narrative for player |
| `completion_message` | str | End-of-game message |
| `all_zone_labels` | list[str] | All zone labels across scenes |
| `distractor_labels` | list[str] | Wrong-answer labels |
| `label_hierarchy` | dict[str, list[str]] | Parent→child label grouping |
| `scenes` | list[SceneConcept] | Scene definitions |

#### Transform: `graph_builder.py:build_game_graph()` (deterministic)

```
GameConcept field          → GamePlan field             → Status
──────────────────────────────────────────────────────────────────
title                      → title                      → ✅ COPIED
subject                    → subject                    → ✅ COPIED
difficulty                 → difficulty                  → ✅ COPIED
estimated_duration_minutes → estimated_duration_minutes  → ✅ COPIED
narrative_theme            → narrative_theme             → ✅ COPIED
narrative_intro            → narrative_intro             → ✅ COPIED
completion_message         → completion_message          → ✅ COPIED
all_zone_labels            → all_zone_labels             → ✅ COPIED
distractor_labels          → distractor_labels           → ✅ COPIED
label_hierarchy            → label_hierarchy             → ✅ COPIED
scenes                     → scenes (transformed)        → ✅ TRANSFORMED
```

**Graph builder is lossless at game level** — all GameConcept fields are copied into GamePlan.

#### Transform: `blueprint_assembler.py:assemble_blueprint()` (deterministic)

```
GamePlan field             → Blueprint field            → Status
──────────────────────────────────────────────────────────────────
title                      → title                      → ✅ COPIED
narrative_intro            → narrativeIntro              → ✅ COPIED (via _build_narrative)
narrative_theme            → (nowhere)                   → ❌ DROPPED
completion_message         → (nowhere)                   → ❌ DROPPED
subject                    → (nowhere)                   → ❌ DROPPED
difficulty                 → (nowhere)                   → ❌ DROPPED
estimated_duration_minutes → (nowhere)                   → ❌ DROPPED
all_zone_labels            → (consumed internally)       → ⚠️ CONSUMED (zone matching)
distractor_labels          → distractorLabels (1st scene)→ ✅ PROMOTED from first scene
label_hierarchy            → (nowhere)                   → ❌ DROPPED
total_max_score            → totalMaxScore               → ✅ COPIED
total_max_score            → scoringStrategy.max_score   → ✅ COPIED
scenes                     → game_sequence.scenes[]      → ✅ TRANSFORMED (multi-scene only)
```

**Game-level drops in assembler**:
1. **`narrative_theme`** — The thematic framing (e.g., "aspiring cardiologist journey"). Frontend has no field for this.
2. **`completion_message`** — End-of-game congratulations. Frontend `GameSequence` has no field for this.
3. **`subject`** — Subject area. Frontend blueprint has no field.
4. **`difficulty`** — Difficulty level. Frontend blueprint has no field.
5. **`estimated_duration_minutes`** — Play time estimate. Frontend `GameSequence` has `estimated_duration_minutes` but assembler doesn't set it.
6. **`label_hierarchy`** — Parent→child grouping. Frontend has `zoneGroups` but assembler doesn't translate.

---

### 2.2 SCENE LEVEL: SceneConcept → SceneCreativeDesign → ScenePlan → GameScene

#### Source: `SceneConcept` (game_concept_designer output)

| Field | Type | Purpose |
|---|---|---|
| `title` | str | Scene title |
| `learning_goal` | str | Learning objective |
| `narrative_intro` | str | Per-scene narrative |
| `zone_labels` | list[str] | Labels for this scene |
| `needs_diagram` | bool | Whether scene needs an image |
| `image_description` | str | Brief image description |
| `mechanics` | list[MechanicChoice] | Mechanic selections |
| `transition_to_next` | "auto" / "score_gated" | Scene transition type |
| `transition_min_score_pct` | float? | Min score to advance |

#### Transform 1: Scene Designer (LLM) produces `SceneCreativeDesign`

The scene designer receives `SceneConcept` + `domain_knowledge` + `pedagogical_context` + `narrative_theme` and produces:

| SceneCreativeDesign field | Type | Purpose |
|---|---|---|
| `scene_id` | str | Scene identifier |
| `title` | str | Scene title |
| `visual_concept` | str | Overall visual vision for the scene |
| `color_palette_direction` | str | Color guidance |
| `spatial_layout` | str | Spatial arrangement guidance |
| `atmosphere` | str | Mood/atmosphere direction |
| `image_spec` | ImageSpec | Detailed image requirements |
| `image_spec.description` | str | Full image description |
| `image_spec.must_include_structures` | list[str] | Required structures in image |
| `image_spec.style` | str | Image style |
| `image_spec.annotation_preference` | str | Label annotation preference |
| `image_spec.color_direction` | str | Color guidance for image |
| `image_spec.spatial_guidance` | str | Spatial layout guidance for image |
| `second_image_spec` | ImageSpec? | For compare_contrast |
| `mechanic_designs` | list[MechanicCreativeDesign] | Per-mechanic creative direction |
| `scene_narrative` | str | Scene-level narrative prose |
| `transition_narrative` | str | Narrative bridge to next scene |

#### Transform 2: `graph_builder.py` copies SceneCreativeDesign into ScenePlan

```
SceneConcept field         + SceneCreativeDesign field → ScenePlan field
─────────────────────────────────────────────────────────────────────────
(SceneConcept)
title                                                  → title              ✅ COPIED
learning_goal                                          → learning_goal      ✅ COPIED
narrative_intro            || design.scene_narrative   → narrative_intro    ✅ MERGED (fallback)
zone_labels                                            → zone_labels        ✅ COPIED
needs_diagram                                          → needs_diagram      ✅ COPIED
transition_to_next/min_score_pct                       → transition_to_next ✅ COPIED

(SceneCreativeDesign)
image_spec                                             → image_spec         ✅ COPIED
second_image_spec                                      → second_image_spec  ✅ COPIED
(entire design)                                        → creative_design    ✅ STORED (full reference)
mechanic_designs[]                                     → mechanics[].creative_design  ✅ COPIED per-mechanic

(SceneConcept — not copied)
image_description                                      → (nowhere)          ⚠️ SUPERSEDED by image_spec
```

**Graph builder is lossless at scene level** — SceneCreativeDesign is stored in `ScenePlan.creative_design` and each mechanic's creative design is stored in `MechanicPlan.creative_design`.

#### Transform 3: Content dispatch router reads ScenePlan → scene_context

```python
# routers.py:content_dispatch_router → content_generator.build_scene_context()
ScenePlan field            → scene_context field        → Status
──────────────────────────────────────────────────────────────────
scene_id                   → scene_id                   → ✅ COPIED
title                      → title                      → ✅ COPIED
learning_goal              → learning_goal              → ✅ COPIED
zone_labels                → zone_labels                → ✅ COPIED
mechanics                  → other_mechanics             → ✅ COPIED (type + id only)
creative_design.visual_concept → visual_concept          → ✅ COPIED
creative_design.atmosphere     → atmosphere              → ✅ COPIED
creative_design.color_palette_direction → (nowhere)      → ❌ NOT EXTRACTED by build_scene_context
creative_design.spatial_layout          → (nowhere)      → ❌ NOT EXTRACTED by build_scene_context
creative_design.scene_narrative         → (nowhere)      → ❌ NOT EXTRACTED by build_scene_context
creative_design.transition_narrative    → (nowhere)      → ❌ NOT EXTRACTED by build_scene_context
narrative_intro            → (nowhere)                   → ❌ NOT EXTRACTED by build_scene_context
```

**Content generator gets `visual_concept` and `atmosphere` from the scene creative design**, but NOT `color_palette_direction`, `spatial_layout`, `scene_narrative`, or `transition_narrative`. These are context fields that could help the content generator produce better-themed content.

#### Transform 4: Assembler `_scene_to_game_scene()` → frontend GameScene

```
ScenePlan (via _build_scene_blueprint) → GameScene      → Status
──────────────────────────────────────────────────────────────────
scene_id                               → scene_id       → ✅ COPIED
title                                  → title          → ✅ COPIED
learning_goal                          → learning_goal  → ✅ COPIED
(asset result)                         → diagram        → ✅ FROM ASSETS
(zone matching)                        → labels         → ✅ BUILT from zone_labels
(distractor_labels)                    → distractorLabels → ✅ BUILT
(mechanic configs)                     → per-mechanic config keys → ✅ COPIED
(mechanic_connections → transitions)   → modeTransitions → ✅ BUILT
(interaction results)                  → (inside mechanics[]) → ✅ SCORING/FEEDBACK

NOT MAPPED:
scene_number                           → (nowhere)      → ❌ DROPPED (frontend expects scene_number)
narrative_intro                        → (nowhere)      → ❌ DROPPED (frontend expects narrative_intro)
scene_max_score                        → (nowhere)      → ❌ DROPPED (frontend expects max_score)
starting_mechanic_id                   → (nowhere)      → ❌ DROPPED (frontend could use this)
mechanics[]                            → (nowhere)      → ❌ DROPPED (frontend expects mechanics[])
creative_design.visual_concept         → (nowhere)      → ❌ DROPPED
creative_design.atmosphere             → (nowhere)      → ❌ DROPPED
creative_design.color_palette_direction → (nowhere)     → ❌ DROPPED
creative_design.spatial_layout         → (nowhere)      → ❌ DROPPED
creative_design.scene_narrative        → (nowhere)      → ❌ DROPPED
creative_design.transition_narrative   → (nowhere)      → ❌ DROPPED
transition_to_next                     → (nowhere)      → ❌ DROPPED
image_spec.style                       → (nowhere)      → ❌ DROPPED (consumed by asset search)
image_spec.color_direction             → (nowhere)      → ❌ DROPPED
image_spec.spatial_guidance            → (nowhere)      → ❌ DROPPED
```

**Major scene-level drops in assembler `_scene_to_game_scene()`**:
1. **`scene_number`** — Frontend `GameScene.scene_number` exists but assembler doesn't set it.
2. **`narrative_intro`** — Frontend `GameScene.narrative_intro` exists and is RENDERED by `GameSequenceRenderer.tsx:324,364`. Assembler doesn't set it.
3. **`scene_max_score` → `max_score`** — Frontend `GameScene.max_score` exists. Assembler doesn't set it.
4. **`mechanics[]`** — Frontend `GameScene.mechanics` exists. Assembler doesn't populate it from `_build_scene_blueprint`.
5. **`starting_mechanic_id`** — Not in frontend type, but useful for knowing which mechanic to start.
6. **All creative_design fields** — Dropped at assembly (visual_concept, atmosphere, etc.)
7. **`transition_to_next`** — Scene-to-scene gating. Frontend `GameSequence` has `progression_type` but assembler doesn't map it.

---

### 2.3 MECHANIC LEVEL: MechanicChoice → MechanicCreativeDesign → MechanicPlan → Content → Blueprint Config

#### Source: `MechanicChoice` (inside SceneConcept)

| Field | Type | Purpose |
|---|---|---|
| `mechanic_type` | Literal[8 types] | Mechanic type |
| `learning_purpose` | str | Why this mechanic was chosen |
| `zone_labels_used` | list[str] | Labels this mechanic uses |
| `expected_item_count` | int | How many items |
| `points_per_item` | int | Points per correct item |
| `advance_trigger` | "completion"/"score_threshold"/... | When to advance |
| `advance_trigger_value` | float? | Trigger threshold |
| `is_timed` | bool | Timed mechanic? |
| `time_limit_seconds` | int? | Time limit |

#### Transform 1: Scene Designer (LLM) produces `MechanicCreativeDesign`

| MechanicCreativeDesign field | Type | Purpose | Consumed by |
|---|---|---|---|
| `mechanic_type` | str | Mechanic type | graph_builder, content_generator, assembler |
| **Visual integration** | | | |
| `visual_style` | str | Visual style direction | content_generator prompt header |
| `card_type` | str | Card visual style | content_generator → schema → assembler |
| `layout_mode` | str | Layout direction | content_generator → schema → assembler |
| `connector_style` | str | Connector visual | content_generator → schema → assembler |
| `color_direction` | str | Color guidance | ❌ NOT CONSUMED anywhere |
| **Narrative integration** | | | |
| `instruction_text` | str | Player instruction | graph_builder → MechanicPlan | ❌ DROPPED by assembler |
| `instruction_tone` | str | Tone for instructions | ❌ NOT CONSUMED anywhere |
| `narrative_hook` | str | Narrative connection | ❌ NOT CONSUMED anywhere |
| **Interaction personality** | | | |
| `hint_strategy` | str | Hint progression | content_generator prompt header |
| `feedback_style` | str | Feedback personality | content_generator prompt header → feedback_timing |
| `difficulty_curve` | str | Difficulty progression | ❌ NOT CONSUMED anywhere |
| **Content generation guidance** | | | |
| `generation_goal` | str | What to generate | content_generator prompt header |
| `key_concepts` | list[str] | Key concepts to cover | content_generator prompt header |
| `pedagogical_focus` | str | Pedagogical emphasis | content_generator prompt header |
| **Mechanic-specific hints** | | | |
| `sequence_topic` | str? | Topic for sequencing | content_generator → _sequencing_prompt |
| `category_names` | list[str]? | Categories for sorting | content_generator → _sorting_prompt |
| `comparison_subjects` | list[str]? | Subjects for compare | content_generator → _compare_contrast_prompt |
| `narrative_premise` | str? | Premise for branching | content_generator → _branching_prompt |
| `description_source` | str? | Source for descriptions | content_generator → _description_matching_prompt |
| `path_process` | str? | Process for trace_path | content_generator → _trace_path_prompt |
| `prompt_style` | str? | Style for click_to_identify | content_generator → _click_to_identify_prompt |
| `match_type` | str? | Match type for memory | content_generator → _memory_match_prompt |
| **Visual asset hints** | | | |
| `needs_item_images` | bool | Need per-item images? | ❌ NOT CONSUMED anywhere |
| `item_image_style` | str? | Style for item images | ❌ NOT CONSUMED anywhere |

#### Transform 2: Graph Builder copies creative design into MechanicPlan

```
MechanicChoice + MechanicCreativeDesign → MechanicPlan    → Status
──────────────────────────────────────────────────────────────────
mechanic_type                          → mechanic_type    → ✅ COPIED
zone_labels_used                       → zone_labels_used → ✅ COPIED
creative.instruction_text              → instruction_text → ✅ COPIED
(entire creative)                      → creative_design  → ✅ STORED
expected_item_count                    → expected_item_count → ✅ COPIED
points_per_item                        → points_per_item  → ✅ COPIED
count * points                         → max_score        → ✅ COMPUTED
is_timed                               → is_timed         → ✅ COPIED
time_limit_seconds                     → time_limit_seconds → ✅ COPIED
(list position)                        → is_terminal      → ✅ COMPUTED
advance_trigger                        → advance_trigger  → ✅ COPIED
(mechanic_id assigned)                 → mechanic_id      → ✅ GENERATED

NOT MAPPED:
learning_purpose                       → (nowhere)        → ❌ DROPPED
advance_trigger_value                  → (nowhere)        → ❌ DROPPED
```

**Graph builder drops at mechanic level**:
1. **`learning_purpose`** — Why this mechanic was chosen. Could be useful for feedback context.
2. **`advance_trigger_value`** — The threshold value for `score_threshold` triggers. Only the trigger type is copied, not the value. **This is a BUG** — if a concept says "advance after 80% score", the 80% is lost.

#### Transform 3: Content Generator uses creative_design to generate content

The content_generator receives `MechanicPlan` (with `creative_design` embedded) and produces mechanic-specific content.

**What the content_generator prompt header reads from creative_design** (line 45-80 of `content_generator.py`):

```
creative_design field      → Prompt section              → Status
──────────────────────────────────────────────────────────────────
visual_style               → "## Creative Direction"     → ✅ IN PROMPT
generation_goal            → "## Creative Direction"     → ✅ IN PROMPT
key_concepts               → "## Creative Direction"     → ✅ IN PROMPT
pedagogical_focus          → "## Creative Direction"     → ✅ IN PROMPT
card_type                  → "## Creative Direction"     → ✅ IN PROMPT
layout_mode                → "## Creative Direction"     → ✅ IN PROMPT
hint_strategy              → "## Creative Direction"     → ✅ IN PROMPT
feedback_style             → "## Creative Direction"     → ✅ IN PROMPT

NOT IN PROMPT HEADER:
color_direction            → (nowhere)                   → ❌ NOT USED
instruction_text           → (nowhere)                   → ❌ NOT USED (it's in MechanicPlan but content prompt ignores it)
instruction_tone           → (nowhere)                   → ❌ NOT USED
narrative_hook             → (nowhere)                   → ❌ NOT USED
difficulty_curve           → (nowhere)                   → ❌ NOT USED
connector_style            → per-mechanic template       → ✅ USED (drag_drop, sequencing)
needs_item_images          → (nowhere)                   → ❌ NOT USED
item_image_style           → (nowhere)                   → ❌ NOT USED
```

**Per-mechanic template field usage**:

| Template | creative_design fields used | Fields NOT used |
|---|---|---|
| `_drag_drop_prompt` | layout_mode, connector_style, feedback_style, card_type | color_direction, instruction_text, narrative_hook |
| `_click_to_identify_prompt` | prompt_style | Everything else from creative |
| `_trace_path_prompt` | path_process | color_direction, connector_style |
| `_sequencing_prompt` | sequence_topic, layout_mode, card_type, connector_style | color_direction, difficulty_curve |
| `_sorting_prompt` | category_names, layout_mode, card_type | color_direction |
| `_memory_match_prompt` | match_type | color_direction, card_type |
| `_branching_prompt` | narrative_premise | color_direction, card_type |
| `_description_matching_prompt` | description_source | color_direction, layout_mode |
| `_compare_contrast_prompt` | comparison_subjects | color_direction |

**Content generator output → mechanic content schemas**:

Each mechanic produces content matching its Pydantic model. These schemas contain both **data fields** (labels, items, descriptions) and **visual config fields** (layout_mode, card_type, etc.).

The visual config fields in the content schema are **derived from creative_design** via the prompt. The LLM fills them based on the creative direction.

#### Transform 4: Assembler maps content → blueprint config

```
MechanicContent field      → Blueprint field             → Status
──────────────────────────────────────────────────────────────────

DRAG_DROP:
labels                     → labels[] (scene-level)      → ✅ (built from zone_labels, not content)
distractor_labels          → distractorLabels[]          → ✅ MAPPED
interaction_mode           → dragDropConfig.interaction_mode → ✅ MAPPED
feedback_timing            → dragDropConfig.feedback_timing → ✅ MAPPED
label_style                → dragDropConfig.label_style  → ✅ MAPPED
leader_line_style          → dragDropConfig.leader_line_style → ✅ MAPPED
leader_line_color          → dragDropConfig.leader_line_color → ✅ MAPPED
leader_line_animate        → dragDropConfig.leader_line_animate → ✅ MAPPED
pin_marker_shape           → dragDropConfig.pin_marker_shape → ✅ MAPPED
label_anchor_side          → dragDropConfig.label_anchor_side → ✅ MAPPED
tray_position              → dragDropConfig.tray_position → ✅ MAPPED
tray_layout                → dragDropConfig.tray_layout  → ✅ MAPPED
placement_animation        → dragDropConfig.placement_animation → ✅ MAPPED
incorrect_animation        → dragDropConfig.incorrect_animation → ✅ MAPPED
zone_idle_animation        → dragDropConfig.zone_idle_animation → ✅ MAPPED
zone_hover_effect          → dragDropConfig.zone_hover_effect → ✅ MAPPED
max_attempts               → dragDropConfig.max_attempts → ✅ MAPPED
shuffle_labels             → dragDropConfig.shuffle_labels → ✅ MAPPED

DESCRIPTION_MATCHING:
descriptions (label→desc)  → descriptionMatchingConfig.descriptions (zoneId→desc) → ✅ RE-KEYED
mode                       → descriptionMatchingConfig.mode → ✅ MAPPED
distractor_descriptions    → descriptionMatchingConfig.distractor_descriptions → ✅ MAPPED
show_connecting_lines      → descriptionMatchingConfig.show_connecting_lines → ✅ MAPPED
defer_evaluation           → descriptionMatchingConfig.defer_evaluation → ✅ MAPPED
description_panel_position → descriptionMatchingConfig.description_panel_position → ✅ MAPPED

TRACE_PATH:
paths[].label/desc/color/waypoints → paths[] (root-level) → ✅ MAPPED (with zone_id resolution)
path_type                  → tracePathConfig.path_type   → ✅ MAPPED
drawing_mode               → tracePathConfig.drawing_mode → ✅ MAPPED
particleTheme              → tracePathConfig.particleTheme → ✅ MAPPED
particleSpeed              → tracePathConfig.particleSpeed → ✅ MAPPED
color_transition_enabled   → tracePathConfig.color_transition_enabled → ✅ MAPPED
show_direction_arrows      → tracePathConfig.show_direction_arrows → ✅ MAPPED
show_waypoint_labels       → tracePathConfig.show_waypoint_labels → ✅ MAPPED
show_full_flow_on_complete → tracePathConfig.show_full_flow_on_complete → ✅ MAPPED
submit_mode                → tracePathConfig.submit_mode → ✅ MAPPED

SEQUENCING:
items                      → sequenceConfig.items        → ✅ MAPPED
correct_order              → sequenceConfig.correct_order → ✅ MAPPED
sequence_type              → sequenceConfig.sequence_type → ✅ MAPPED
layout_mode                → sequenceConfig.layout_mode  → ✅ MAPPED
interaction_pattern        → sequenceConfig.interaction_pattern → ✅ MAPPED
card_type                  → sequenceConfig.card_type    → ✅ MAPPED
connector_style            → sequenceConfig.connector_style → ✅ MAPPED
show_position_numbers      → sequenceConfig.show_position_numbers → ✅ MAPPED
allow_partial_credit       → sequenceConfig.allow_partial_credit → ✅ MAPPED

SORTING_CATEGORIES:
categories                 → sortingConfig.categories    → ✅ MAPPED
items                      → sortingConfig.items         → ✅ MAPPED
sort_mode                  → sortingConfig.sort_mode     → ✅ MAPPED
item_card_type             → sortingConfig.item_card_type → ✅ MAPPED
container_style            → sortingConfig.container_style → ✅ MAPPED
submit_mode                → sortingConfig.submit_mode   → ✅ MAPPED
allow_multi_category       → sortingConfig.allow_multi_category → ✅ MAPPED
show_category_hints        → sortingConfig.show_category_hints → ✅ MAPPED
allow_partial_credit       → sortingConfig.allow_partial_credit → ✅ MAPPED

MEMORY_MATCH:
pairs                      → memoryMatchConfig.pairs     → ✅ MAPPED
game_variant               → memoryMatchConfig.game_variant → ✅ MAPPED
gridSize                   → memoryMatchConfig.gridSize  → ✅ MAPPED
match_type                 → memoryMatchConfig.match_type → ✅ MAPPED
card_back_style            → memoryMatchConfig.card_back_style → ✅ MAPPED
matched_card_behavior      → memoryMatchConfig.matched_card_behavior → ✅ MAPPED
show_explanation_on_match  → memoryMatchConfig.show_explanation_on_match → ✅ MAPPED
flip_duration_ms           → memoryMatchConfig.flip_duration_ms → ✅ MAPPED
show_attempts_counter      → memoryMatchConfig.show_attempts_counter → ✅ MAPPED

BRANCHING_SCENARIO:
nodes                      → branchingConfig.nodes       → ✅ MAPPED
startNodeId                → branchingConfig.startNodeId → ✅ MAPPED
narrative_structure        → branchingConfig.narrative_structure → ✅ MAPPED
show_path_taken            → branchingConfig.show_path_taken → ✅ MAPPED
allow_backtrack            → branchingConfig.allow_backtrack → ✅ MAPPED
show_consequences          → branchingConfig.show_consequences → ✅ MAPPED
multiple_valid_endings     → branchingConfig.multiple_valid_endings → ✅ MAPPED

CLICK_TO_IDENTIFY:
prompts                    → identificationPrompts[] (root) → ✅ MAPPED (with zone_id resolution)
prompt_style               → clickToIdentifyConfig.prompt_style → ✅ MAPPED
selection_mode             → clickToIdentifyConfig.selection_mode → ✅ MAPPED
highlight_style            → clickToIdentifyConfig.highlight_style → ✅ MAPPED
magnification_enabled      → clickToIdentifyConfig.magnification_enabled → ✅ MAPPED
magnification_factor       → clickToIdentifyConfig.magnification_factor → ✅ MAPPED
explore_mode_enabled       → clickToIdentifyConfig.explore_mode_enabled → ✅ MAPPED
show_zone_count            → clickToIdentifyConfig.show_zone_count → ✅ MAPPED
```

**The content → assembler mapping for per-mechanic content is actually COMPLETE.** All content schema fields are mapped to their corresponding blueprint config fields.

#### Transform 5: Interaction Designer → Blueprint mechanics[]

```
SceneInteractionResult field → Blueprint                 → Status
──────────────────────────────────────────────────────────────────
mechanic_scoring[mid]      → mechanics[].scoring         → ✅ MAPPED
mechanic_feedback[mid]     → mechanics[].feedback        → ✅ MAPPED
mode_transitions[]         → modeTransitions[]           → ✅ MAPPED

Fields inside feedback:
on_correct                 → feedback.on_correct         → ✅ MAPPED
on_incorrect               → feedback.on_incorrect       → ✅ MAPPED
on_completion              → feedback.on_completion      → ✅ MAPPED
misconceptions[].trigger   → misconceptions[].trigger    → ✅ MAPPED
misconceptions[].message   → misconceptions[].message    → ✅ MAPPED
misconceptions[].severity  → (nowhere)                   → ❌ DROPPED

Fields inside mode_transitions:
from_mode                  → from                        → ✅ MAPPED (alias)
to_mode                    → to                          → ✅ MAPPED (alias)
trigger                    → trigger                     → ✅ MAPPED
trigger_value              → trigger_value               → ✅ MAPPED
animation                  → animation                   → ✅ (hardcoded "fade" in _build_transitions fallback)
message                    → message                     → ✅ (null in _build_transitions fallback)
```

**Minor drop**: `misconceptions[].severity` is produced by interaction_designer but not passed to blueprint. Frontend `Mechanic.feedback.misconceptions` expects `trigger_label` + `message` (no severity).

---

### 2.4 ASSET LEVEL: ImageSpec → Search → Zones → Blueprint Diagram

#### Source: `ImageSpec` (from SceneCreativeDesign)

| Field | Used by | Status |
|---|---|---|
| `description` | asset_dispatcher._search_image() query | ✅ CONSUMED |
| `must_include_structures` | asset_dispatcher._search_image() query (appended) | ✅ CONSUMED |
| `style` | (nowhere) | ❌ NOT USED in search |
| `annotation_preference` | (nowhere) | ❌ NOT USED in search |
| `color_direction` | (nowhere) | ❌ NOT USED in search |
| `spatial_guidance` | (nowhere) | ❌ NOT USED in search |

**Asset search only uses `description` and `must_include_structures`**. The remaining ImageSpec fields (`style`, `annotation_preference`, `color_direction`, `spatial_guidance`) are generated by the scene designer but never consumed.

**These fields would be relevant for image generation** (DALL-E, Flux) but are currently unused since we search existing images.

#### Asset Pipeline Output → Blueprint

```
Asset result field         → Blueprint field             → Status
──────────────────────────────────────────────────────────────────
diagram_url                → diagram.assetUrl            → ✅ MAPPED
(image_spec.description)   → diagram.assetPrompt         → ✅ MAPPED
zones[].id                 → diagram.zones[].id          → ✅ MAPPED
zones[].label              → diagram.zones[].label       → ✅ MAPPED
zones[].points             → diagram.zones[].points      → ✅ MAPPED
zones[].x/y/radius/w/h    → diagram.zones[].x/y/...     → ✅ MAPPED (fallback geometry)
match_quality              → (nowhere)                   → ❌ DROPPED (logged only)
```

---

## 3. What's Dropped and What's Wrong: Consolidated Findings

### CRITICAL: Fields the frontend reads but assembler doesn't provide

| # | Field | Frontend reads from | Assembler sets? | Impact |
|---|---|---|---|---|
| C-1 | `GameScene.narrative_intro` | `GameSequenceRenderer.tsx:324,364` — displayed as scene intro text | **NO** | Players see empty scene introductions |
| C-2 | `GameScene.scene_number` | `GameScene.scene_number` (required field in TS type) | **NO** | Frontend may show undefined scene numbers |
| C-3 | `GameScene.max_score` | `GameScene.max_score` (required field in TS type) | **NO** | Score display broken for per-scene scoring |
| C-4 | `GameScene.mechanics[]` | `GameScene.mechanics` — starting mode derivation | **NO** | Frontend must derive from config keys instead |
| C-5 | `GameScene.zones` | `GameScene.zones` (required field in TS type) | **NO** — assembler puts zones inside `diagram.zones` but GameScene type has `zones` at root level | Zones may not render in multi-scene mode |

### HIGH: Creative fields generated but dropped at assembly

| # | Field | Generated by | Consumed by | Dropped at | Impact |
|---|---|---|---|---|---|
| H-1 | `instruction_text` | scene_designer per mechanic | graph_builder copies to MechanicPlan | **assembler** — never put in blueprint | Players see no per-mechanic instructions |
| H-2 | `completion_message` | game_concept_designer | graph_builder copies to GamePlan | **assembler** — never put in blueprint | No end-of-game message |
| H-3 | `transition_narrative` | scene_designer | (nobody) | **Never consumed after scene_designer** | Between-scene narrative bridges lost |
| H-4 | `advance_trigger_value` | game_concept_designer | (nobody) | **graph_builder** — only copies trigger type, not value | Score-threshold triggers have no threshold |

### MEDIUM: Context fields not passed to downstream agents

| # | Field | Generated by | Should be consumed by | Impact |
|---|---|---|---|---|
| M-1 | `color_direction` (MechanicCreativeDesign) | scene_designer | content_generator (not in prompt) | Color guidance from creative direction lost |
| M-2 | `difficulty_curve` | scene_designer | content_generator / interaction_designer | Difficulty progression guidance lost |
| M-3 | `instruction_tone` | scene_designer | content_generator | Tone guidance lost |
| M-4 | `narrative_hook` | scene_designer | content_generator | Narrative integration lost |
| M-5 | `learning_purpose` (MechanicChoice) | game_concept_designer | content_generator / interaction_designer | Pedagogical rationale for mechanic choice lost |
| M-6 | `color_palette_direction` (scene-level) | scene_designer | build_scene_context() | Scene color theme not in content prompt |
| M-7 | `spatial_layout` (scene-level) | scene_designer | build_scene_context() | Scene spatial arrangement not in content prompt |

### LOW: Image spec fields unused (relevant only for future image generation)

| # | Field | Generated by | Status |
|---|---|---|---|
| L-1 | `ImageSpec.style` | scene_designer | ❌ Not used in image search |
| L-2 | `ImageSpec.annotation_preference` | scene_designer | ❌ Not used |
| L-3 | `ImageSpec.color_direction` | scene_designer | ❌ Not used |
| L-4 | `ImageSpec.spatial_guidance` | scene_designer | ❌ Not used |
| L-5 | `needs_item_images` | scene_designer | ❌ Not consumed |
| L-6 | `item_image_style` | scene_designer | ❌ Not consumed |
| L-7 | `match_quality` (asset result) | asset_dispatcher | ❌ Logged but not in blueprint |

### INFO: Fields that are consumed-then-discarded (acceptable)

| Field | Consumed by | Discarded after | Acceptable? |
|---|---|---|---|
| `visual_style` | content_generator prompt header | Content generated | ✅ Yes — it guided content generation |
| `generation_goal` | content_generator prompt | Content generated | ✅ Yes |
| `key_concepts` | content_generator prompt | Content generated | ✅ Yes |
| `pedagogical_focus` | content_generator prompt | Content generated | ✅ Yes |
| `hint_strategy` | content_generator prompt | Content generated | ✅ Yes |
| `feedback_style` | content_generator → feedback_timing | Config generated | ✅ Yes |
| `sequence_topic` | content_generator prompt | Content generated | ✅ Yes |
| `category_names` | content_generator prompt | Content generated | ✅ Yes |
| `description_source` | content_generator prompt | Content generated | ✅ Yes |
| `path_process` | content_generator prompt | Content generated | ✅ Yes |
| `prompt_style` | content_generator prompt | Content generated | ✅ Yes |
| `match_type` | content_generator prompt | Content generated | ✅ Yes |
| `narrative_premise` | content_generator prompt | Content generated | ✅ Yes |
| `comparison_subjects` | content_generator prompt | Content generated | ✅ Yes |
| `visual_concept` | build_scene_context() | In content prompt | ✅ Yes |
| `atmosphere` | build_scene_context() | In content prompt | ✅ Yes |

---

## 4. Root Cause Summary

The drops fall into 3 categories:

### Category A: Assembler doesn't map GamePlan/ScenePlan fields to existing frontend fields

The assembler was written to produce a minimal blueprint. But `GameScene` in the frontend has fields for `narrative_intro`, `scene_number`, `max_score`, `mechanics[]`, `zones[]` (at root), `distractorLabels` that the assembler's `_scene_to_game_scene()` doesn't populate.

**Fix**: Update `_scene_to_game_scene()` to map these fields. The data IS available in the ScenePlan — it just isn't being extracted.

### Category B: Creative fields never reach downstream prompts

`color_direction`, `difficulty_curve`, `instruction_tone`, `narrative_hook`, `learning_purpose` are generated by the scene designer but the content_generator prompt header and the interaction_designer prompt don't read them.

**Fix**: Add these to `_build_header()` in `content_generator.py` and `build_interaction_prompt()` in `interaction_designer.py`.

### Category C: Graph builder drops advance_trigger_value

`MechanicChoice.advance_trigger_value` (e.g., 0.8 for "80% score") is not copied to `MechanicPlan` or `MechanicConnection.trigger_value`.

**Fix**: Add `advance_trigger_value` to `MechanicPlan` schema and copy it in `graph_builder._build_connections()`.

---

## 5. Recommended Fixes (Priority Order)

### Fix 1 — Assembler: Map scene fields to GameScene [CRITICAL]

In `_scene_to_game_scene()`:
```python
game_scene["scene_number"] = index + 1
game_scene["narrative_intro"] = scene_bp.get("narrative_intro", "")  # need to pass through from ScenePlan
game_scene["max_score"] = scene_bp.get("scene_max_score", 0)
game_scene["mechanics"] = scene_bp.get("_mechanics", [])
game_scene["zones"] = scene_bp.get("diagram", {}).get("zones", [])
```

In `_build_scene_blueprint()`, preserve narrative_intro and scene_max_score:
```python
result["narrative_intro"] = scene.get("narrative_intro", "")
result["scene_max_score"] = scene.get("scene_max_score", 0)
```

### Fix 2 — Assembler: Add instruction_text and completion_message [HIGH]

At blueprint root:
```python
blueprint["completionMessage"] = game_plan.get("completion_message", "")
```

Per-mechanic in mechanics[]:
```python
mechanic_entry["instructionText"] = mp.get("instruction_text", "")
```

Or in sequenceConfig (which has `instructionText` in frontend type):
```python
config["instructionText"] = mp.get("instruction_text", "")
```

### Fix 3 — Graph builder: Copy advance_trigger_value [HIGH]

In `MechanicPlan` schema, it already has no field for this.
In `_build_connections()`, copy `trigger_value`:
```python
conn = MechanicConnection(
    from_mechanic_id=current.mechanic_id,
    to_mechanic_id=next_mech.mechanic_id,
    trigger=trigger,
    trigger_value=current.advance_trigger_value,  # NEW
)
```

### Fix 4 — Content generator: Add missing creative fields to prompt [MEDIUM]

In `_build_header()`:
```python
f"- Color Direction: {creative_design.get('color_direction', '')}",
f"- Difficulty Curve: {creative_design.get('difficulty_curve', 'gradual')}",
f"- Instruction Tone: {creative_design.get('instruction_tone', 'educational')}",
f"- Narrative Hook: {creative_design.get('narrative_hook', '')}",
```

### Fix 5 — Content generator: Add missing scene context fields [MEDIUM]

In `build_scene_context()`:
```python
context["color_palette_direction"] = creative.get("color_palette_direction", "")
context["spatial_layout"] = creative.get("spatial_layout", "")
context["narrative_intro"] = scene_plan.get("narrative_intro", "")
```

### Fix 6 — Assembler: Add game-level metadata [LOW]

```python
blueprint["subject"] = game_plan.get("subject", "")
blueprint["difficulty"] = game_plan.get("difficulty", "intermediate")
blueprint["narrativeTheme"] = game_plan.get("narrative_theme", "")
blueprint["estimatedDurationMinutes"] = game_plan.get("estimated_duration_minutes", 10)
```

These require frontend type additions but provide useful metadata.

---

## 6. Fields Summary Matrix

| Field | GameConcept | GraphBuilder | ContentGen Prompt | InteractionDesigner | Assembler Blueprint | Frontend Reads |
|---|---|---|---|---|---|---|
| title | ✅ | ✅ | - | - | ✅ | ✅ |
| narrative_intro | ✅ | ✅ | ❌ | - | ✅ (root only) | ✅ |
| narrative_theme | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ no field |
| completion_message | ✅ | ✅ | - | - | ❌ | ❌ no field |
| subject | ✅ | ✅ | - | - | ❌ | ❌ no field |
| difficulty | ✅ | ✅ | - | - | ❌ | ❌ no field |
| scene.narrative_intro | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ RENDERED |
| scene.scene_number | - | ✅ | - | - | ❌ | ✅ required |
| scene.max_score | - | ✅ | - | - | ❌ | ✅ required |
| scene.mechanics[] | - | ✅ | - | - | ❌ | ✅ expected |
| scene.zones[] (root) | - | - | - | - | ❌ (in diagram) | ✅ required |
| instruction_text | - | ✅ | ❌ | ❌ | ❌ | ✅ (sequenceConfig) |
| advance_trigger_value | ✅ | ❌ DROPPED | - | - | ❌ | ✅ (triggerValue) |
| visual_concept | - | ✅ | ✅ | ❌ | ❌ | ❌ no field |
| atmosphere | - | ✅ | ✅ | ❌ | ❌ | ❌ no field |
| color_direction | - | ✅ | ❌ | ❌ | ❌ | ❌ no field |
| difficulty_curve | - | ✅ | ❌ | ❌ | ❌ | ❌ no field |
| instruction_tone | - | ✅ | ❌ | ❌ | ❌ | ❌ no field |
| narrative_hook | - | ✅ | ❌ | ❌ | ❌ | ❌ no field |
| transition_narrative | - | ✅ | ❌ | ❌ | ❌ | ❌ no field |
| learning_purpose | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ no field |
| match_quality | - | - | - | - | ❌ | ❌ no field |
