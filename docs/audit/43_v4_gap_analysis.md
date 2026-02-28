# V4 Pipeline — Gap Analysis: Design (Doc 16) vs Current Implementation

**Date**: 2026-02-15
**Source of truth for**: What exists, what's missing, what needs to change

---

## 1. Architecture Comparison

### Designed (Doc 16): 22 agents, 5 phases, 3-stage creative cascade

```
Phase 0: [input_analyzer, dk_retriever] → phase0_merge
Phase 1a: game_concept_designer → concept_validator → [retry|pass]
Phase 1b: Send("scene_designer") × N → scene_design_merge → graph_builder
Phase 2a: Send("content_generator") × M → content_merge
Phase 2b: Send("interaction_designer") × N → interaction_merge
Phase 3a: asset_needs_analyzer → Send("asset_art_director") × N → art_direction_merge
Phase 3b: Send("asset_chain_runner") × assets → asset_merge
Phase 4:  blueprint_assembler → blueprint_validator → END
```

### Current: 9 nodes, simplified

```
Phase 0: [input_analyzer, dk_retriever] → phase0_merge
Phase 1: game_designer → game_plan_validator → [retry|pass]
Phase 2: content_build_node (sequential loop)
Phase 3: Send("asset_worker") × N → asset_merge → [retry|pass]
Phase 4: blueprint_assembler → END
```

---

## 2. Missing Agents/Nodes

| Designed Agent | Status | What it should do |
|---|---|---|
| `game_concept_designer` | **MISSING** — collapsed into `game_designer` | Single LLM call → `GameConcept` (WHAT + WHY, not HOW) |
| `concept_validator` | **MISSING** — merged into `game_plan_validator` | Validates GameConcept structure |
| `scene_designer` (×N, parallel) | **MISSING entirely** | Per-scene LLM call → `SceneCreativeDesign` with visual_style, layout_mode, card_type, hints |
| `scene_design_validator` | **MISSING** | Per-scene creative design validation |
| `scene_design_merge` | **MISSING** | Sync barrier after parallel scene designers |
| `graph_builder` | **MISSING** | Deterministic: GameConcept + SceneCreativeDesigns → GamePlan (with creative_design embedded) |
| `content_generator` (×M, parallel) | **EXISTS but sequential** — in `content_build_node` loop | Per-mechanic LLM call → `MechanicContent` |
| `content_merge` | **MISSING** | Sync barrier after parallel content generators |
| `interaction_designer` (×N, parallel) | **EXISTS but sequential** — in `content_build_node` loop | Per-scene scoring/feedback |
| `interaction_merge` | **MISSING** | Sync barrier after parallel interaction designers |
| `asset_needs_analyzer` | **MISSING** — replaced by `asset_send_router` function | Deterministic: GamePlan + Content → AssetNeeds |
| `asset_art_director` (×N, parallel) | **MISSING entirely** | Per-scene LLM call → crafted queries, style prompts, color palettes |
| `art_direction_validator` | **MISSING** | Validates art direction completeness |
| `art_direction_merge` | **MISSING** | Sync barrier after parallel art directors |
| `asset_chain_runner` (×assets) | **MISSING** — replaced by `asset_worker` inline | Execute pre-built tool chains (diagram_with_zones, simple_image, color_palette) |
| `asset_validator` | **MISSING** | Per-scene asset coverage validation |
| `blueprint_validator` (as node) | **EXISTS but inline** — called inside `assembler_node` | Separate node in design |

---

## 3. Missing Schemas

### 3a. Phase 1a — GameConcept (designed, not implemented)

```python
# DESIGNED but does NOT exist
class ContentStructure(BaseModel):
    primary_type: Literal["anatomical", "process", "comparative", "categorical", "hierarchical", "conceptual"]
    has_labels: bool
    has_sequence: bool
    has_comparison: bool
    has_hierarchy: bool
    has_categories: bool
    visual_needs: Literal["diagram", "flowchart", "dual_diagram", "none"]

class MechanicChoice(BaseModel):
    mechanic_id: str = ""               # Set by graph_builder
    mechanic_type: str
    learning_purpose: str               # WHY this mechanic
    zone_labels_used: list[str] = []
    expected_item_count: int
    points_per_item: int = 10
    advance_trigger: str = "completion"
    advance_trigger_value: Optional[float] = None
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None
    children: Optional[list[MechanicChoice]] = None  # For hierarchical

class SceneConcept(BaseModel):
    title: str
    learning_goal: str
    narrative_intro: str = ""
    zone_labels: list[str] = []
    needs_diagram: bool
    image_description: str = ""
    mechanics: list[MechanicChoice]
    transition_to_next: str = "auto"
    transition_min_score_pct: Optional[float] = None

class GameConcept(BaseModel):
    title: str
    subject: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_duration_minutes: int
    narrative_theme: str
    narrative_intro: str
    completion_message: str
    all_zone_labels: list[str]
    distractor_labels: list[str] = []
    label_hierarchy: Optional[dict[str, list[str]]] = None
    scenes: list[SceneConcept]
```

### 3b. Phase 1b — SceneCreativeDesign (designed, not implemented)

```python
# DESIGNED but does NOT exist
class ImageSpec(BaseModel):  # Richer than current
    description: str
    must_include_structures: list[str]
    style: str = "clean_educational"
    annotation_preference: str = "clean_unlabeled"
    color_direction: str = ""
    spatial_guidance: str = ""

class MechanicCreativeDesign(BaseModel):
    mechanic_id: str = ""
    mechanic_type: str
    # Visual integration
    visual_style: str
    card_type: str = "text_only"       # text_only | icon_and_text | image_card
    layout_mode: str = "default"       # varies per mechanic
    connector_style: str = "arrow"
    color_direction: str = ""
    # Narrative
    instruction_text: str
    instruction_tone: str = "educational"
    narrative_hook: str = ""
    # Interaction personality
    hint_strategy: str = "progressive"
    feedback_style: str = "encouraging"
    difficulty_curve: str = "gradual"
    # Content generation guidance
    generation_goal: str
    key_concepts: list[str] = []
    pedagogical_focus: str = ""
    # Mechanic-specific hints
    sequence_topic: Optional[str] = None
    category_names: Optional[list[str]] = None
    comparison_subjects: Optional[list[str]] = None
    narrative_premise: Optional[str] = None
    description_source: Optional[str] = None
    path_process: Optional[str] = None
    prompt_style: Optional[str] = None
    match_type: Optional[str] = None
    needs_item_images: bool = False
    item_image_style: Optional[str] = None

class SceneCreativeDesign(BaseModel):
    scene_id: str
    title: str
    visual_concept: str
    color_palette_direction: str = ""
    spatial_layout: str = ""
    atmosphere: str = ""
    image_spec: Optional[ImageSpec] = None
    second_image_spec: Optional[ImageSpec] = None  # For compare_contrast
    mechanic_designs: list[MechanicCreativeDesign]
    scene_narrative: str = ""
    transition_narrative: str = ""
```

### 3c. Designed GamePlan.MechanicPlan should embed creative_design

```python
# DESIGNED MechanicPlan (different from current)
class MechanicPlan(BaseModel):
    mechanic_id: str
    mechanic_type: str
    zone_labels_used: list[str] = []
    instruction_text: str              # FROM SceneCreativeDesign
    creative_design: MechanicCreativeDesign  # MISSING — full creative direction
    expected_item_count: int
    points_per_item: int = 10
    max_score: int
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None
    parent_mechanic_id: Optional[str] = None  # MISSING — for hierarchical
    is_terminal: bool = False                  # MISSING

# DESIGNED ScenePlan (different from current)
class ScenePlan(BaseModel):
    scene_id: str
    scene_number: int                          # MISSING
    title: str
    learning_goal: str
    narrative_intro: str = ""                  # MISSING
    zone_labels: list[str] = []
    needs_diagram: bool
    image_spec: Optional[ImageSpec] = None
    second_image_spec: Optional[ImageSpec] = None  # MISSING
    creative_design: SceneCreativeDesign       # MISSING — full creative direction
    mechanics: list[MechanicPlan]
    mechanic_connections: list[MechanicConnection]
    starting_mechanic_id: str                  # MISSING
    transition_to_next: Optional[SceneTransition] = None  # MISSING
    scene_max_score: int
```

### 3d. Missing Content Schemas (visual config fields)

Current `mechanic_content.py` has bare-minimum fields. Doc 16 designed rich visual config per mechanic:

| Mechanic | Current fields | Designed additional fields (MISSING) |
|---|---|---|
| `DragDropContent` | `labels, distractor_labels` | `interaction_mode, feedback_timing, label_style, leader_line_style, leader_line_color, leader_line_animate, pin_marker_shape, label_anchor_side, tray_position, tray_layout, placement_animation, incorrect_animation, zone_idle_animation, zone_hover_effect, max_attempts, shuffle_labels` |
| `SequencingContent` | `items, correct_order, sequence_type, layout_mode` | `interaction_pattern, card_type, connector_style, show_position_numbers, allow_partial_credit` |
| `SortingContent` | `categories, items` | `sort_mode, item_card_type, container_style, submit_mode, allow_multi_category, show_category_hints, allow_partial_credit` |
| `MemoryMatchContent` | `pairs, game_variant, gridSize` | `card_back_style, matched_card_behavior, show_explanation_on_match, flip_duration_ms, show_attempts_counter` |
| `BranchingContent` | `nodes, startNodeId` | `narrative_structure, show_path_taken, allow_backtrack, show_consequences, multiple_valid_endings` |
| `TracePathContent` | `paths, particleSpeed` | `path_type, drawing_mode, particle_theme, color_transition_enabled, show_direction_arrows, show_waypoint_labels, show_full_flow_on_complete, submit_mode` |
| `ClickToIdentifyContent` | `prompts` | `prompt_style, selection_mode, highlight_style, magnification_enabled, magnification_factor, explore_mode_enabled, explore_time_limit_seconds, show_zone_count` |
| `DescriptionMatchingContent` | `descriptions, mode, distractor_descriptions` | `show_connecting_lines, defer_evaluation, description_panel_position` |
| `CompareContrastContent` | **MISSING entirely** | `subject_a, subject_b, expected_categories, comparison_mode, highlight_matching, category_types, category_labels, category_colors, exploration_enabled, zoom_enabled` |
| `HierarchicalContent` | **MISSING entirely** | `groups: list[HierarchicalGroup]` with `parent_label, child_labels, reveal_trigger` |

### 3e. Missing Asset Schemas

```python
# DESIGNED but does NOT exist (partially in asset_manifest.py)
class ItemImageNeed(BaseModel):
    asset_id: str
    item_id: str
    mechanic_id: str
    description: str
    style_prompt: str = ""

class NodeIllustrationNeed(BaseModel):
    asset_id: str
    node_id: str
    mechanic_id: str
    scene_description: str
    mood: str = ""

class ColorPaletteNeed(BaseModel):
    scene_id: str
    count: int
    theme: str = ""

class AssetNeeds(BaseModel):
    diagrams: list[DiagramAssetNeed]
    item_images: list[ItemImageNeed] = []
    node_illustrations: list[NodeIllustrationNeed] = []
    color_palettes: list[ColorPaletteNeed] = []

class ArtDirectedManifest(BaseModel):  # MISSING entirely
    scene_id: str
    diagram_queries: list[str]          # Crafted search queries
    diagram_style_prompt: str           # >30 chars
    color_palette: dict[str, str]       # label → hex
    item_image_specs: list[dict] = []
    spatial_guidance: str = ""
```

---

## 4. Missing State Fields

| Designed Field | In current state.py? | Written by |
|---|---|---|
| `content_structure` | NO | input_analyzer |
| `game_concept` | NO | game_concept_designer |
| `scene_creative_designs` | NO | scene_designers (dict[int, SceneCreativeDesign]) |
| `failed_scene_ids` | NO | scene_design_validator (Annotated[list, add]) |
| `_v4_concept_retries` | NO | concept_validator |
| `_v4_concept_validation` | NO | concept_validator |
| `_v4_scene_design_retries` | NO | scene_design_validator (dict[int, int]) |
| `_v4_scene_design_validation` | NO | scene_design_validator (dict[int, ValidationResult]) |
| `asset_needs` | NO | asset_needs_analyzer |
| `art_directed_manifests` | NO | asset_art_directors (dict[str, ArtDirectedManifest]) |
| `scene_number` in ScenePlan | NO | graph_builder |
| `starting_mechanic_id` in ScenePlan | NO | graph_builder |
| `narrative_intro` in ScenePlan | NO | graph_builder (from SceneConcept) |
| `creative_design` in MechanicPlan | NO | graph_builder (from SceneCreativeDesign) |
| `creative_design` in ScenePlan | NO | graph_builder (from SceneCreativeDesign) |
| `parent_mechanic_id` in MechanicPlan | NO | graph_builder (for hierarchical) |
| `is_terminal` in MechanicPlan | NO | graph_builder |
| `template_type` | NO | blueprint_assembler |

---

## 5. Missing Validators

| Designed Validator | Exists? | What it checks |
|---|---|---|
| `concept_validator` | NO | Scene count 1-6, mechanic types valid, zone label integrity, advance_trigger valid, timed+time_limit, compare_contrast has comparison_subjects |
| `scene_design_validator` | NO | mechanic count matches concept, instruction_text >20 chars, layout_mode valid per mechanic_type, card_type valid, image_spec present if needs_diagram, generation_goal non-empty |
| `interaction_validator` (as node) | NO — inline in content_build_node | Transition endpoints exist, no self-transitions, valid trigger types, trigger-mechanic compatibility, DAG property |
| `art_direction_validator` | NO | Crafted queries non-empty, style_prompt >30 chars, color_palette completeness |
| `asset_validator` | NO | Zone coverage %, label matching, coordinate validity |

---

## 6. Missing Prompts

| Designed Prompt | Exists? | Purpose |
|---|---|---|
| `game_concept_designer.py` | NO — current `game_designer.py` outputs GamePlan directly | GameConcept output (lighter, WHAT+WHY) |
| `scene_designer.py` | NO | Per-scene SceneCreativeDesign (HOW it looks/feels) |
| `asset_art_director.py` | NO | Crafted search queries, style prompts, color palettes |

---

## 7. Missing Helpers

| Designed Helper | Exists? | Purpose |
|---|---|---|
| `graph_builder.py` | NO | Deterministic: GameConcept + SceneCreativeDesigns → GamePlan |
| `scene_context_builder.py` | NO | Deterministic: shared context per scene for content generators |
| `asset_chains.py` | NO | Pre-built tool chain definitions (diagram_with_zones, simple_image, color_palette, svg_particles) |
| `asset_needs_analyzer.py` | NO | Deterministic: GamePlan + Content → AssetNeeds |

---

## 8. Graph Wiring Differences

| Edge/Pattern | Designed | Current | Gap |
|---|---|---|---|
| Phase 1a → 1b | concept_validator → Send("scene_designer") × N | game_plan_validator → content_build | Missing entire Phase 1b |
| Phase 1b → graph_builder | scene_design_merge → graph_builder | N/A | graph_builder doesn't exist |
| Phase 2 fan-out | Send("content_generator") × M per mechanic | Sequential loop in content_build_node | No parallelism |
| Phase 2 merge | content_merge node | N/A | No merge node needed (sequential) |
| Phase 2b fan-out | Send("interaction_designer") × N per scene | Sequential in content_build_node | No parallelism |
| Phase 3a art direction | Send("asset_art_director") × N | N/A | Entire stage missing |
| Phase 3b asset chains | Send("asset_chain_runner") per asset | asset_worker does search+detect+SAM3 inline | No pre-built chains |
| Send payload `_run_id` | Not specified | Fixed today | OK now |

---

## 9. Config/Model Assignments Differences

### Designed (doc 16 §12):
```python
V4_AGENT_MODELS = {
    "v4_input_analyzer": {"model": "gemini-2.5-flash", "temperature": 0.3},
    "v4_dk_retriever": {"model": "gemini-2.5-flash", "temperature": 0.2},
    "v4_game_concept_designer": {"model": "gemini-2.5-pro", "temperature": 0.7},
    "v4_scene_designer": {"model": "gemini-2.5-pro", "temperature": 0.7},
    "v4_content_generator_branching": {"model": "gemini-2.5-pro", "temperature": 0.5},
    "v4_content_generator_compare": {"model": "gemini-2.5-pro", "temperature": 0.5},
    "v4_content_generator_sequencing": {"model": "gemini-2.5-pro", "temperature": 0.5},
    "v4_content_generator_default": {"model": "gemini-2.5-flash", "temperature": 0.5},
    "v4_interaction_designer": {"model": "gemini-2.5-flash", "temperature": 0.4},
    "v4_asset_art_director": {"model": "gemini-2.5-flash", "temperature": 0.5},
}
```

### Current:
- Uses `agent_name` strings like `"game_designer"`, `"content_builder_pro"`, `"content_builder_flash"`, `"interaction_designer"`, `"input_analyzer"`, `"dk_retriever"` — resolved by `agent_models.py` registry
- Missing: `v4_game_concept_designer`, `v4_scene_designer`, `v4_asset_art_director`

---

## 10. What currently works vs what should work

### Currently works:
- Phase 0: input_analyzer + dk_retriever (parallel) ✓
- Phase 0: phase0_merge sync barrier ✓
- Phase 1: game_designer → game_plan_validator → retry loop ✓
- Phase 3: asset_worker via Send API (parallel per scene) ✓
- Phase 3: asset_merge with deduplication ✓
- Phase 3: asset retry router ✓
- Phase 4: assembler + validator + repair ✓
- Observability: sub_stages tracking, StagePanel renderers ✓

### Currently broken:
- Phase 2: content_builder crashes on `MechanicPlan` dict vs Pydantic (fix applied, not tested)
- Phase 3: zone detection returns 0 zones (image quality or search query issue)
- Run status: marked "success" even when everything fails
- asset_worker: not instrumented (no `_run_id` in Send payload — fix applied, not tested)

### Missing entirely (from design):
- Phase 1a/1b split: GameConcept → SceneCreativeDesign → graph_builder
- SceneCreativeDesign with rich visual/narrative direction
- All MechanicCreativeDesign fields (visual_style, layout_mode, card_type, etc.)
- Content visual config fields (16 drag_drop fields, 5 sequencing fields, etc.)
- Asset art direction LLM stage
- Pre-built asset chains
- compare_contrast mechanic support
- hierarchical mechanic support
- ContentStructure classification in input_analyzer
- Interaction validator as separate node
- Checkpointing

---

## 11. Implementation Priority

### Must-have for working pipeline:
1. Fix content_builder validation crash (done)
2. Fix asset_worker instrumentation (done)
3. Fix run status when degraded
4. Fix zone detection quality

### Must-have for doc 16 architecture:
5. Split Phase 1: game_concept_designer + concept_validator
6. Add Phase 1b: scene_designer + scene_design_validator + scene_design_merge
7. Add graph_builder (deterministic)
8. Add new schemas: GameConcept, SceneCreativeDesign, MechanicCreativeDesign
9. Update state.py with missing fields
10. Parallelize Phase 2: content_generator per mechanic via Send
11. Add asset art direction: asset_needs_analyzer + asset_art_director
12. Enrich content schemas with visual config fields
13. Update graph.py with all new nodes and edges
14. Update prompts for concept designer and scene designer
15. Update blueprint assembler to read creative_design
16. Add compare_contrast + hierarchical support
17. Update frontend PipelineView with new layout
18. Update StagePanel with new agent renderers
