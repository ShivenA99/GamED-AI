# V3 Schemas & State Field Audit

**Date:** 2026-02-11
**Scope:** All Pydantic models, AgentState fields, cross-stage validation

---

## 1. AGENT STATE V3 FIELDS (state.py:456-486)

### Core Pipeline Fields

| Field | Type | Default | Writer | Reader(s) |
|-------|------|---------|--------|-----------|
| `game_design_v3` | `Optional[Dict[str, Any]]` | `None` | game_designer_v3 | design_validator, scene_architect_v3, interaction_designer_v3, asset_generator_v3, blueprint_assembler_v3 |
| `design_validation_v3` | `Optional[Dict[str, Any]]` | `None` | design_validator | game_designer_v3 (retry) |
| `_v3_design_retries` | `Optional[int]` | `0` | design_validator | graph.py router |
| `scene_specs_v3` | `Optional[List[Dict[str, Any]]]` | `None` | scene_architect_v3 | scene_validator, interaction_designer_v3, asset_generator_v3, blueprint_assembler_v3 |
| `scene_validation_v3` | `Optional[Dict[str, Any]]` | `None` | scene_validator | scene_architect_v3 (retry) |
| `_v3_scene_retries` | `Optional[int]` | `0` | scene_validator | graph.py router |
| `interaction_specs_v3` | `Optional[List[Dict[str, Any]]]` | `None` | interaction_designer_v3 | interaction_validator, asset_generator_v3, blueprint_assembler_v3 |
| `interaction_validation_v3` | `Optional[Dict[str, Any]]` | `None` | interaction_validator | interaction_designer_v3 (retry) |
| `_v3_interaction_retries` | `Optional[int]` | `0` | interaction_validator | graph.py router |
| `generated_assets_v3` | `Optional[Dict[str, Any]]` | `None` | asset_generator_v3 | blueprint_assembler_v3 |

### Per-Mechanic Asset Fields

| Field | Type | Default | Writer | Reader |
|-------|------|---------|--------|--------|
| `sequence_item_images` | `Optional[Dict[str, str]]` | `None` | asset_generator_v3 | blueprint_assembler_v3 |
| `sorting_item_images` | `Optional[Dict[str, str]]` | `None` | asset_generator_v3 | blueprint_assembler_v3 |
| `sorting_category_icons` | `Optional[Dict[str, str]]` | `None` | asset_generator_v3 | blueprint_assembler_v3 |
| `memory_card_images` | `Optional[Dict[str, str]]` | `None` | asset_generator_v3 | blueprint_assembler_v3 |
| `diagram_crop_regions` | `Optional[Dict[str, Dict]]` | `None` | asset_generator_v3 | blueprint_assembler_v3 |

### Deprecated V3 Fields

| Field | Type | Status |
|-------|------|--------|
| `asset_graph_v3` | `Optional[Dict[str, Any]]` | Kept for backward compat, unused |
| `asset_manifest_v3` | `Optional[Dict[str, Any]]` | Kept for backward compat, unused |

---

## 2. GAME DESIGN SCHEMAS (game_design_v3.py)

### GameDesignV3 (Full — Lines 884-920)

Used by: validate_design tool, NOT used by V3 pipeline directly

```
GameDesignV3(BaseModel, extra="allow")
├── title: str = ""
├── narrative_intro: str = ""
├── pedagogical_reasoning: str = ""
├── learning_objectives: List[str] = []
├── estimated_duration_minutes: int = 5
├── theme: ThemeSpec
│   ├── visual_tone: str = ""
│   ├── color_palette: Dict = {}
│   ├── background_description: str = ""
│   └── narrative_frame: str = ""
├── labels: LabelDesign
│   ├── zone_labels: List[str] = []
│   ├── group_only_labels: List[str] = []
│   ├── distractor_labels: List[DistractorLabel] = []
│   │   └── DistractorLabel: {text, explanation, appears_in_scenes?}
│   └── hierarchy: HierarchySpec
│       ├── enabled: bool = False
│       ├── strategy: str = "progressive_reveal"
│       └── groups: List[HierarchyGroup]
│           └── HierarchyGroup: {parent, children[], reveal_trigger}
├── scenes: List[SceneDesign]
│   └── SceneDesign
│       ├── scene_number: int
│       ├── title: str
│       ├── learning_goal: str
│       ├── visual: SceneVisualSpec
│       ├── zone_labels: List[str]
│       ├── zone_specs: List[ZoneSpec]
│       ├── mechanics: List[MechanicDesign]
│       │   └── MechanicDesign
│       │       ├── type: str
│       │       ├── description: str
│       │       ├── zone_labels_used: List[str]
│       │       ├── path_config: Optional[PathDesign]
│       │       ├── click_config: Optional[ClickDesign]
│       │       ├── sequence_config: Optional[SequenceDesign]
│       │       ├── sorting_config: Optional[SortingDesign]
│       │       ├── branching_config: Optional[BranchingDesign]
│       │       ├── compare_config: Optional[CompareDesign]
│       │       ├── memory_config: Optional[MemoryMatchDesign]
│       │       ├── timed_config: Optional[TimedDesign]
│       │       ├── description_match_config: Optional[DescriptionMatchDesign]
│       │       ├── scoring: MechanicScoring
│       │       ├── feedback: MechanicFeedback
│       │       └── animations: Optional[MechanicAnimations]
│       ├── mechanic_transitions: List[MechanicTransitionSpec]
│       ├── media_assets: List[MediaAssetDesign]
│       ├── sounds: List[SoundDesign]
│       ├── temporal: Optional[TemporalSpec]
│       ├── max_score: int = 100
│       └── time_limit_seconds: Optional[int]
├── scene_transitions: List[SceneTransitionSpec]
├── difficulty: DifficultySpec
├── total_max_score: int = 0
├── star_thresholds: List[float] = [0.6, 0.8, 1.0]
└── global_sounds: List[SoundDesign]
```

### GameDesignV3Slim (Lines 1079-1150)

Used by: V3 pipeline (what game_designer_v3 actually produces)

```
GameDesignV3Slim(BaseModel, extra="allow")
├── title: str = ""
├── pedagogical_reasoning: str = ""
├── learning_objectives: List[str] = []
├── estimated_duration_minutes: int = 5
├── theme: ThemeSpec
├── labels: LabelDesign
├── scenes: List[SlimSceneDesign]
│   └── SlimSceneDesign
│       ├── scene_number: int
│       ├── title: str = ""
│       ├── learning_goal: str = ""
│       ├── visual_description: str = ""
│       ├── mechanics: List[SlimMechanicRef]
│       │   └── SlimMechanicRef
│       │       ├── type: str
│       │       ├── config_hint: Dict[str, Any] = {}
│       │       └── zone_labels_used: List[str] = []
│       └── zone_labels_in_scene: List[str] = []
├── scene_transitions: List[SlimSceneTransition]
└── difficulty: DifficultySpec
```

**Key Difference:** SlimMechanicRef has `type` + `config_hint` only. Full MechanicDesign has typed config fields (path_config, click_config, etc.).

### Mechanic Config Models (used by Full only)

| Model | Key Fields |
|-------|-----------|
| `PathDesign` | waypoints, path_type, visual_style, drawing_mode, particle_theme, show_direction_arrows |
| `ClickDesign` | click_options, correct_assignments, selection_mode, prompts, highlight_on_hover, magnification_enabled |
| `SequenceDesign` | correct_order, items[], sequence_type, layout_mode, interaction_pattern, card_type, connector_style |
| `SortingDesign` | categories[], items[], sort_mode, item_card_type, container_style, submit_mode |
| `BranchingDesign` | nodes[], start_node_id, narrative_structure, show_path_taken, allow_backtrack |
| `CompareDesign` | expected_categories[], subjects[], comparison_mode, category_types |
| `MemoryMatchDesign` | pairs[], game_variant, match_type, grid_size, card_back_style, flip_duration_ms |
| `DescriptionMatchDesign` | sub_mode, descriptions[], show_connecting_lines, defer_evaluation |
| `TimedDesign` | time_limit_seconds, timer_position, timer_style, count_direction, penalty_type |

---

## 3. SCENE SPEC SCHEMA (scene_spec_v3.py)

### SceneSpecV3 (Lines 132-189)

```
SceneSpecV3(BaseModel, extra="allow")
├── scene_number: int (REQUIRED)
├── title: str = ""
├── image_description: str = ""
├── image_requirements: List[str] = []
├── image_style: str = "clean_educational"
├── zones: List[ZoneSpecV3]
│   └── ZoneSpecV3
│       ├── zone_id: str
│       ├── label: str
│       ├── position_hint: str = ""
│       ├── description: str = ""
│       ├── hint: str = ""
│       └── difficulty: int = 2
├── mechanic_configs: List[MechanicConfigV3]
│   └── MechanicConfigV3
│       ├── type: str
│       ├── zone_labels_used: List[str] = []
│       ├── config: Dict[str, Any] = {}
│       ├── path_config: Optional[PathDesign]
│       ├── click_config: Optional[ClickDesign]
│       ├── sequence_config: Optional[SequenceDesign]
│       ├── sorting_config: Optional[SortingDesign]
│       ├── branching_config: Optional[BranchingDesign]
│       ├── compare_config: Optional[CompareDesign]
│       ├── memory_config: Optional[MemoryMatchDesign]
│       ├── timed_config: Optional[TimedDesign]
│       └── description_match_config: Optional[DescriptionMatchDesign]
├── mechanic_data: Dict[str, Any] = {}
└── zone_hierarchy: List[ZoneHierarchyV3] = []
    └── ZoneHierarchyV3: {parent, children[], reveal_trigger}
```

**MechanicConfigV3._coerce_config() validator:** Promotes `config` dict contents into typed fields via `_CONFIG_FIELD_MAP`:
```python
_CONFIG_FIELD_MAP = {
    "trace_path": "path_config",
    "click_to_identify": "click_config",
    "sequencing": "sequence_config",
    ...
}
```

**MechanicConfigV3.get_typed_config():** Returns typed config object for this mechanic.

### validate_scene_specs() (Lines 191-344)

Cross-stage checks:
1. Every game_design zone_label has a zone in scene_specs
2. Scene numbers match
3. Mechanic types match per scene
4. Zones have non-empty hints/descriptions
5. Image descriptions non-empty
6. **Mechanic-specific config (Lines 270-337):**
   - trace_path: waypoints present
   - click_to_identify: prompts present
   - sequencing: items + correct_order present
   - sorting_categories: categories + items present
   - description_matching: descriptions present
   - memory_match: pairs present
   - branching_scenario: nodes + start_node_id present
   - compare_contrast: expected_categories present

---

## 4. INTERACTION SPEC SCHEMA (interaction_spec_v3.py)

### InteractionSpecV3 (Lines 126-164)

```
InteractionSpecV3(BaseModel, extra="allow")
├── scene_number: int (REQUIRED)
├── scoring: List[MechanicScoringV3]
│   └── MechanicScoringV3
│       ├── mechanic_type: str
│       ├── strategy: str = "standard"
│       ├── points_per_correct: int = 10
│       ├── max_score: int = 100
│       ├── partial_credit: bool = True
│       └── hint_penalty: float = 0.1
├── feedback: List[MechanicFeedbackV3]
│   └── MechanicFeedbackV3
│       ├── mechanic_type: str
│       ├── on_correct: str = "Correct!"
│       ├── on_incorrect: str = "Try again."
│       ├── on_completion: str = "Well done!"
│       └── misconception_feedback: List[MisconceptionFeedbackV3]
│           └── {trigger_label, trigger_zone, message}
├── distractor_feedback: List[DistractorFeedbackV3]
│   └── {distractor, feedback}
├── mode_transitions: List[ModeTransitionV3]
│   └── {from_mechanic, to_mechanic, trigger, trigger_value?, animation, message}
├── scene_completion: SceneCompletionV3
│   └── {trigger="all_zones_labeled", show_results=True, min_score_to_pass=70}
├── animations: AnimationSpecV3
│   └── {on_correct: Dict, on_incorrect: Dict, on_completion: Dict}
└── transition_to_next: Optional[SceneTransitionDetailV3]
    └── {trigger, animation, message}
```

### MECHANIC_TRIGGER_MAP (Lines 245-257)

| Mechanic | Valid Triggers |
|----------|---------------|
| drag_drop | all_zones_labeled, all_complete, percentage_complete, score_threshold |
| click_to_identify | all_complete, percentage_complete, score_threshold |
| trace_path | path_complete, all_complete, score_threshold |
| sequencing | sequence_complete, all_complete, score_threshold |
| description_matching | all_complete, percentage_complete, score_threshold |
| sorting_categories | all_complete, score_threshold |
| memory_match | all_complete, score_threshold |
| branching_scenario | all_complete, user_choice |
| compare_contrast | all_complete, score_threshold |
| hierarchical | all_complete, percentage_complete, score_threshold |
| timed_challenge | time_elapsed, all_complete, score_threshold |

### validate_interaction_specs() (Lines 185-344)

Cross-stage checks:
1. Every mechanic has scoring entry
2. Every mechanic has feedback (on_correct + on_incorrect)
3. >= 2 misconception feedbacks per scene
4. Mode transitions required for multi-mechanic scenes
5. Transition triggers valid per MECHANIC_TRIGGER_MAP
6. Mechanic-specific content checks
7. Total max_score in range 50-500
8. Distractor feedback for all distractors

---

## 5. BLUEPRINT SCHEMAS (blueprint_schemas.py)

### InteractiveDiagramBlueprint (Lines 769-835)

```
InteractiveDiagramBlueprint(BaseModel, extra="allow")
├── templateType: Literal["INTERACTIVE_DIAGRAM"]
├── title: str
├── narrativeIntro: str = ""
├── theme: Optional[Dict[str, Any]]
├── global_labels: List[str] = []
├── distractor_labels: List[Dict[str, str]] = []
├── hierarchy: Optional[Dict[str, Any]]
├── scenes: List[IDScene] (min_length=1)
│   └── IDScene
│       ├── scene_id: str
│       ├── scene_number: int (>=1)
│       ├── title: str
│       ├── diagram_image_url: str
│       ├── background_url: Optional[str]
│       ├── zones: List[IDZone]
│       │   └── {id, label, shape, coordinates, description, parent_zone_id?, group_only?}
│       ├── labels: List[IDLabel]
│       │   └── {id, text, correct_zone_id, is_distractor?, explanation?}
│       ├── mechanics: List[IDMechanic]
│       │   └── {mechanic_id, mechanic_type, interaction_mode, config, zone_labels, scoring, feedback, animations}
│       ├── mechanic_transitions: List[IDMechanicTransition]
│       ├── assets: List[IDSceneAsset]
│       ├── sounds: List
│       ├── max_score: int = 100
│       ├── time_limit_seconds: Optional[int]
│       ├── narrative_intro: Optional[str]
│       └── instructions: Optional[str]
├── scene_transitions: List[IDSceneTransition] = []
├── total_max_score: int = 100
├── pass_threshold: float = 0.6
├── difficulty: Optional[Dict[str, Any]]
├── asset_graph: Optional[Dict[str, Any]]
├── learning_objectives: List[str] = []
└── estimated_duration_minutes: Optional[int]
```

### GameScene (Multi-Scene — Lines 469-521)

```
GameScene(BaseModel)
├── scene_id: str
├── scene_number: int (>=1)
├── title: str
├── diagram: Optional[SceneDiagram]
│   └── {assetUrl, assetPrompt, width?, height?, zones?}
├── zones: List[Dict[str, Any]] = []
├── labels: List[Dict[str, Any]] = []
├── interaction_mode: str = "drag_drop"
├── max_score: int = 100
├── time_limit_seconds: Optional[int]
├── prerequisite_scene: Optional[str]
├── narrative_intro: Optional[str]
├── instructions: Optional[str]
├── mode_config: Optional[Dict[str, Any]]
├── sequence_config: Optional[Dict[str, Any]]
├── tasks: List[BlueprintSceneTask] = []
└── (per-mechanic configs extracted from mechanics[])
```

---

## 6. DOMAIN KNOWLEDGE SCHEMA (domain_knowledge.py)

### DomainKnowledge (Lines 141-182)

```
DomainKnowledge(BaseModel, extra="forbid")
├── query: str (REQUIRED)
├── canonical_labels: List[str] (min_length=1)
├── acceptable_variants: Dict[str, List[str]] = {}
├── hierarchical_relationships: Optional[List[HierarchicalRelationship]]
│   └── {parent, children[], relationship_type}
├── sources: List[DomainKnowledgeSource] = []
├── query_intent: Optional[QueryIntent]
│   └── {learning_focus, depth_preference, suggested_progression[]}
├── suggested_reveal_order: Optional[List[str]]
├── scene_hints: Optional[List[SceneHint]]
│   └── {focus, reason, suggested_scope}
├── sequence_flow_data: Optional[SequenceFlowData]
│   └── {flow_type, sequence_items[], flow_description, source_url}
│       └── SequenceItem: {id, text, order_index, description, connects_to[]}
└── content_characteristics: Optional[ContentCharacteristics]
    └── {needs_labels, needs_sequence, needs_comparison, sequence_type}
```

### EnhancedDomainKnowledge (Lines 184-274)

Extends DomainKnowledge with:
- `get_hierarchy_depth()` — Max hierarchy depth via BFS
- `needs_multi_scene()` — True if scene hints, depth > 2, or label count > 12
- `get_labels_by_level()` — Groups labels by hierarchy level

---

## 7. CROSS-SCHEMA FIELD FLOW

```
DomainKnowledge
  canonical_labels ─────────────────► game_designer_v3, scene_architect_v3
  sequence_flow_data ───────────────► game_designer_v3 (check_capabilities)
  content_characteristics ──────────► game_designer_v3 (analyze_pedagogy)
  hierarchical_relationships ───────► game_designer_v3 (hierarchy config)
  comparison_data ──────────────────► game_designer_v3 (compare mechanic)

GameDesignV3Slim
  title ────────────────────────────► scene_architect_v3, blueprint
  labels.zone_labels ───────────────► scene_architect_v3, interaction_designer_v3
  labels.distractor_labels ─────────► interaction_designer_v3, blueprint
  labels.hierarchy ─────────────────► scene_architect_v3, blueprint
  scenes[].mechanics[].type ────────► scene_architect_v3, interaction_designer_v3
  scenes[].visual_description ──────► asset_generator_v3
  difficulty ───────────────────────► interaction_designer_v3

SceneSpecV3
  zones[].label ────────────────────► interaction_designer_v3, asset_generator_v3, blueprint
  zones[].zone_id ──────────────────► blueprint (zone mapping)
  mechanic_configs[].type ──────────► interaction_designer_v3
  mechanic_configs[].config ────────► blueprint (per-mechanic config forwarding)
  image_description ────────────────► asset_generator_v3

InteractionSpecV3
  scoring[].mechanic_type ──────────► blueprint (scoring data)
  scoring[].max_score ──────────────► blueprint (total_max_score calculation)
  feedback[].on_correct/incorrect ──► blueprint (feedbackMessages)
  mode_transitions[] ───────────────► blueprint (modeTransitions)

GeneratedAssetsV3
  scenes["1"].diagram_image_url ────► blueprint (diagram.assetUrl)
  scenes["1"].zones[] ──────────────► blueprint (zone coordinates)

Blueprint
  scenes[].zones[] ─────────────────► Frontend Zone[]
  scenes[].labels[] ────────────────► Frontend Label[]
  scenes[].mechanics[] ─────────────► Frontend Mechanic[] → per-mechanic configs
  total_max_score ──────────────────► Frontend maxScore
  scene_transitions ────────────────► Frontend scene navigation
```

---

## 8. KEY OBSERVATIONS

### Dual-Track Design
- `GameDesignV3` (full) vs `GameDesignV3Slim` (structural only)
- V3 pipeline uses Slim — per-mechanic configs are in `config_hint` dict, NOT typed fields
- Design validator checks typed fields on Full model → may miss issues in Slim

### Schema Coercion
- Every model has `_coerce_*` validators (mode="before") for LLM output normalization
- Handles: nested keys, type coercion, field aliases, list-to-dict conversion

### Per-Mechanic Config Promotion
- `MechanicConfigV3._coerce_config()` promotes `config` dict → typed fields
- E.g., `config: {waypoints: [...]}` → `path_config: PathDesign(waypoints=[...])`
- Downstream code should use `get_typed_config()` not raw `config` dict

### Cross-Stage Validation Coverage

| Mechanic | Design Validator | Scene Validator | Interaction Validator |
|----------|-----------------|-----------------|----------------------|
| drag_drop | (no special check) | (no special check) | scoring + feedback |
| click_to_identify | click_config check | prompts check | scoring + feedback + prompts |
| trace_path | path_config check | waypoints check | scoring + feedback + ordering |
| sequencing | sequence_config check | items + order check | scoring + feedback + ordering |
| sorting_categories | sorting_config check | categories + items check | scoring + feedback |
| description_matching | desc_match_config check | descriptions check | scoring + feedback + descriptions |
| memory_match | memory_config check | pairs check | scoring + feedback |
| branching_scenario | branching_config check | nodes + start check | scoring + feedback |
| compare_contrast | compare_config check | expected_categories check | scoring + feedback |
| hierarchical | hierarchy check | (zone_hierarchy) | scoring + feedback |
