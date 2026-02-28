# V4 Pipeline Implementation Checklist (v2 — Audit-Verified)

**Date**: 2026-02-14 (updated from audit cross-reference)
**Source audits**: 35 (consolidated), 36 (LangGraph), 37 (schemas), 38 (prompts), 39 (logical flow), 40 (new code), 41 (data flow per mechanic), 30-34 (frontend/state/components/assembler/agents)

**Decisions Locked**:
- Output schema: `InteractiveDiagramBlueprint` (existing frontend type — NOT GameSpecification)
- Graph: Sequential content/interaction + parallel assets via Send
- Scope: 8 mechanics (defer compare_contrast + hierarchical)
- Scores: Deterministic (validator computes, LLM outputs points_per_item + expected_item_count)
- ContentBrief: Structured dict (~5 fields + mechanic_specific_hints)
- Checkpointing: AsyncSqliteSaver (context manager pattern)
- Frontend: No adapter needed — assembler outputs InteractiveDiagramBlueprint directly
- Testing: TDD for validators, E2E for agents

---

## Open Discussion Items

> These items surfaced during audit cross-referencing. Note them here for resolution during implementation.

**D1: Phase 0 parallel vs sequential** (audit 39 Finding 1)
The plan says input_analyzer and dk_retriever run in parallel, but dk_retriever "reads content_structure" from input_analyzer. If run in parallel, dk_retriever falls back to generic search.
**Current decision**: Run parallel (generic search is acceptable for V4 MVP). Revisit if DK quality is poor.

**D2: Content-only scenes (no zones/diagram)** (audit 39 Finding 8)
Sequencing, sorting, memory_match, branching don't need diagrams. A scene composed entirely of these has `needs_diagram: false`, `zones: []`, `labels: []`. V3 assembler rejects no-zone scenes. Frontend completion via `placedCorrectCount >= taskLabelCount` would fire immediately (0 >= 0).
**Must handle**: Blueprint validator allows empty zones for content-only scenes. Frontend completion must use per-mechanic progress (sequencingProgress.isComplete, etc.), not label count.

**D3: Distractor scope** (audit 39 Finding 9)
Global `distractor_labels` only apply to zone-based mechanics (drag_drop). Content-only mechanics generate distractors inline (e.g., `is_distractor` on sequencing items). Blueprint assembler assigns global distractors only to scenes with zone-based mechanics.

**D4: Timed challenge modeling** (audit 39 Finding 15)
Frontend has `timed_challenge` as a separate InteractionMode. V4 treats timed as a modifier (`is_timed: true` on MechanicPlan). Blueprint assembler should set `timedChallengeWrappedMode` + `timeLimitSeconds` when `is_timed` is true. NOT a separate mechanic type.

**D5: Multi-scene transition types** (audit 39 Finding 6)
GamePlan has `SceneTransition.transition_type: "auto" | "button" | "score_gate"`. Frontend `sceneManager.ts` currently only does index arithmetic (auto-advance). Score-gated transitions won't work without frontend changes.
**Decision**: V4 MVP uses "auto" only. Defer score_gate and button transitions.

**D6: Existing frontend engine files** (uncommitted)
Files already exist at `frontend/src/components/templates/InteractiveDiagramGame/engine/`:
- `sceneManager.ts`, `sceneFlowGraph.ts`, `transitionEvaluator.ts`
- `scoringEngine.ts`, `feedbackEngine.ts`, `completionDetector.ts`
- `mechanicInitializer.ts`, `ruleSchema.ts`
- `schemas/blueprintSchema.ts`, `gameSequenceSchema.ts`, `mechanicConfigSchemas.ts`, `parseBlueprint.ts`, `caseNormalizer.ts`

These were built for a frontend engine refactor. V4 should use these where applicable (especially `parseBlueprint.ts` for Zod validation and `caseNormalizer.ts`). No frontend adapter needed IF the assembler outputs the correct shape.

**D7: Existing asset_gen service** (uncommitted)
`backend/app/services/asset_gen/` already exists with: `core.py`, `gemini_image.py`, `imagen.py`, `search.py`, `segmentation.py`, `storage.py`, `svg_gen.py`. The asset_worker should call into this service rather than reimplementing.

**D8: `mechanic_contracts.py` already exists** (uncommitted)
`backend/app/config/mechanic_contracts.py` (16KB) already has all 9 mechanic definitions. V4 contracts should import from here, not rewrite.

---

## Phase 1: Schemas & State Foundation

**Goal**: All types defined. No LLM calls, no graph wiring. Pure Pydantic + TypedDict.
**Depends on**: Nothing
**Estimated**: ~15 files, ~1200-1500 LOC

### 1.1 V4MainState TypedDict

**File**: `backend/app/v4/state.py`

```python
from typing import TypedDict, Optional, Annotated
import operator

class V4MainState(TypedDict, total=False):
    # Input (immutable)
    question_text: str
    question_id: str
    question_options: Optional[list[str]]
    _run_id: str
    _pipeline_preset: str

    # Phase 0: Context
    pedagogical_context: Optional[dict]
    domain_knowledge: Optional[dict]

    # Phase 1: Design
    game_plan: Optional[dict]           # GamePlan model dumped
    design_validation: Optional[dict]
    design_retry_count: int
    design_validation_override: bool

    # Phase 2: Content (sequential, no reducers needed)
    mechanic_contents: Optional[list[dict]]      # keyed by mechanic_id
    interaction_results: Optional[list[dict]]     # per-scene
    content_retry_count: int

    # Phase 3: Assets (Send API — needs reducers)
    generated_assets_raw: Annotated[list[dict], operator.add]  # accumulator
    generated_assets: Optional[list[dict]]        # deduped by scene_id
    zone_detection_results: Optional[dict]        # scene_id -> zones
    failed_asset_scene_ids: Annotated[list[str], operator.add]
    asset_retry_count: int

    # Phase 4: Assembly
    blueprint: Optional[dict]           # InteractiveDiagramBlueprint
    assembly_warnings: Optional[list[str]]

    # Metadata
    generation_complete: bool
    error_message: Optional[str]
    phase_errors: Annotated[list[dict], operator.add]
    is_degraded: bool
    _stage_order: int
```

- [x] Define V4MainState with all fields above
- [x] Add `Annotated[list, operator.add]` on: `generated_assets_raw`, `failed_asset_scene_ids`, `phase_errors`
- [x] No reducers on content fields (sequential processing — single node loops internally)
- [x] Ensure `_stage_order: int` for instrumentation ordering

### 1.2 GamePlan Schemas

**File**: `backend/app/v4/schemas/game_plan.py`

- [x] `GamePlan` — top-level design output
  - `title: str`
  - `subject: str`
  - `difficulty: Literal["beginner", "intermediate", "advanced"]`
  - `scenes: list[ScenePlan]`
  - `all_zone_labels: list[str]` — CANONICAL label list (all downstream refs must match these)
  - `distractor_labels: list[str] = []` — disjoint from zone_labels (validator enforces)
  - `total_max_score: int` — COMPUTED BY VALIDATOR, not LLM
- [x] `ScenePlan`
  - `scene_id: str`
  - `title: str`
  - `learning_goal: str`
  - `zone_labels: list[str]` — subset of `all_zone_labels`
  - `needs_diagram: bool`
  - `image_spec: Optional[ImageSpec]`
  - `mechanics: list[MechanicPlan]`
  - `mechanic_connections: list[MechanicConnection]` — can be empty for single-mechanic scenes
  - `scene_max_score: int` — COMPUTED
- [x] `MechanicPlan`
  - `mechanic_id: str`
  - `mechanic_type: Literal["drag_drop", "click_to_identify", "trace_path", "sequencing", "sorting_categories", "memory_match", "branching_scenario", "description_matching"]`
  - `zone_labels_used: list[str]` — empty for content-only mechanics
  - `instruction_text: str`
  - `content_brief: ContentBrief`
  - `expected_item_count: int`
  - `points_per_item: int`
  - `max_score: int` — COMPUTED (validator sets this)
  - `is_timed: bool = False`
  - `time_limit_seconds: Optional[int] = None`
- [x] `ContentBrief`
  - `description: str`
  - `key_concepts: list[str]`
  - `expected_complexity: Literal["low", "medium", "high"]`
  - `mechanic_specific_hints: dict[str, Any]` — freeform per-mechanic seeds
  - `dk_fields_needed: list[str]` — DK field names to project
- [x] `MechanicConnection`
  - `from_mechanic_id: str`
  - `to_mechanic_id: str`
  - `trigger_hint: str` — one of: "completion", "score_threshold", "user_choice", "time_elapsed"
- [x] `ImageSpec`
  - `description: str`
  - `required_elements: list[str]`
  - `style: str = "clean educational diagram"`

### 1.3 MechanicContent Schemas (content_generator output)

**File**: `backend/app/v4/schemas/mechanic_content.py`

8 per-mechanic Pydantic models. Each MUST use **frontend field names directly**.

Sources for field names (from audits 32, 37, 41):

- [x] `DragDropContent`
  - `labels: list[str]` — zone label texts
  - `distractor_labels: list[str] = []`
- [x] `ClickToIdentifyContent`
  - `prompts: list[IdentificationPromptInput]` — each: `text`, `target_label`, `explanation`, `order`
  - NOTE: These become root-level `identificationPrompts[]` in blueprint (NOT inside config)
- [x] `TracePathContent`
  - `paths: list[PathInput]` — each: `label`, `description`, `color`, `requiresOrder: bool`, `waypoints: list[WaypointInput]`
  - `WaypointInput`: `label: str`, `order: int`
  - NOTE: These become root-level `paths[]` in blueprint (NOT inside tracePathConfig)
- [x] `SequencingContent`
  - `items: list[SequenceItemInput]` — each: `id`, `content`, `explanation`, `image_url: Optional[str]`
  - `correct_order: list[str]` — item IDs in correct order
  - `sequence_type: str = "ordered"` — "ordered", "cyclic", "branching"
  - `layout_mode: str = "vertical_list"` — must match frontend enum: "vertical_list" | "horizontal_list" | "grid"
- [x] `SortingContent`
  - `categories: list[SortingCategoryInput]` — each: `id`, `label` (NOT `name`), `color`, `description`
  - `items: list[SortingItemInput]` — each: `id`, `content`, `correctCategoryId`, `explanation`
- [x] `MemoryMatchContent`
  - `pairs: list[MemoryPairInput]` — each: `id`, `front` (NOT `term`), `back` (NOT `definition`), `frontType: str = "text"`, `backType: str = "text"`, `explanation`
  - `game_variant: str = "classic"` — "classic" | "column_match"
  - `gridSize: Optional[list[int]] = None` — [rows, cols] or auto-calculated
- [x] `BranchingContent`
  - `nodes: list[DecisionNodeInput]` — each: `id`, `question` (NOT `prompt`), `description`, `isEndNode: bool = False`, `endMessage: Optional[str]`
  - `DecisionNodeInput.options: list[DecisionOptionInput]` — each: `id`, `text`, `nextNodeId` (NOT `next_node_id`), `isCorrect` (NOT `is_correct`), `consequence: Optional[str]`, `points: int`
  - `startNodeId: str` (NOT `start_node_id`)
- [x] `DescriptionMatchingContent`
  - `descriptions: dict[str, str]` — zone_label -> description text
  - `mode: str = "click_zone"` — "click_zone" | "drag_description" | "multiple_choice"
  - `distractor_descriptions: Optional[list[str]] = None` — for MC distractors

**Critical field name remappings** (from audit 33 bugs B-BR1, B-MM1):
- memory_match: backend `term/definition` -> V4 must use `front/back`
- branching: backend `prompt/choices/next_node_id/is_correct` -> V4 must use `question/options/nextNodeId/isCorrect`
- sorting: backend `name` -> V4 must use `label`
- trace_path: backend `particle_speed: float` -> V4 must use `particleSpeed: "slow"|"medium"|"fast"`
- memory_match: backend `grid_size: "4x3"` -> V4 must use `gridSize: [4, 3]`

### 1.4 Interaction Schemas

**File**: `backend/app/v4/schemas/interaction.py`

- [x] `ScoringRules` — must match frontend `Mechanic.scoring`
  - `strategy: str = "per_correct"` — "per_correct" | "all_or_nothing" | "weighted"
  - `points_per_correct: int`
  - `max_score: int`
  - `partial_credit: bool = True`
- [x] `FeedbackRules` — must match frontend `Mechanic.feedback`
  - `on_correct: str`
  - `on_incorrect: str`
  - `on_completion: str`
  - `misconceptions: list[dict] = []` — each: `trigger`, `message`, `severity`
- [x] `ModeTransitionOutput` — must match frontend `ModeTransition`
  - `from_mode: str` — serialized as `from` (Python reserved word — use Field(alias="from"))
  - `to_mode: str` — serialized as `to`
  - `trigger: str` — one of 14 frontend trigger types (see TRIGGER_MAP in 2.3)
  - `trigger_value: Optional[Union[int, float, list[str]]] = None`
  - `animation: str = "fade"`
  - `message: Optional[str] = None`
- [x] `SceneInteractionResult` — wraps per-scene interaction output
  - `scene_id: str`
  - `mechanic_scoring: dict[str, ScoringRules]` — keyed by mechanic_id
  - `mechanic_feedback: dict[str, FeedbackRules]` — keyed by mechanic_id
  - `mode_transitions: list[ModeTransitionOutput]`

### 1.5 Validation Schemas

**File**: `backend/app/v4/schemas/validation.py`

- [x] `ValidationIssue` — `severity: Literal["error", "warning", "info"]`, `message: str`, `field_path: Optional[str]`, `mechanic_id: Optional[str]`
- [x] `ValidationResult` — `passed: bool`, `score: float`, `issues: list[ValidationIssue]`, `retry_allowed: bool`

### 1.6 Asset Schemas

**File**: `backend/app/v4/schemas/asset_manifest.py`

- [x] `AssetManifest` — `scene_assets: list[DiagramAssetNeed]`
- [x] `DiagramAssetNeed` — `scene_id: str`, `search_query: str`, `required_labels: list[str]`, `style: str`
- [x] `AssetResult` — `scene_id: str`, `status: Literal["success", "error"]`, `diagram_url: Optional[str]`, `zones: list[dict]`, `match_quality: Optional[float]`, `error: Optional[str]`

### 1.7 DK Field Resolver

**File**: `backend/app/v4/helpers/dk_field_resolver.py` (~30 LOC)

From audit 38 Section 4 — 12 DK field names in contracts don't match DomainKnowledge schema:

- [x] `DK_FIELD_MAP` dict:
  ```python
  DK_FIELD_MAP = {
      "canonical_labels": "canonical_labels",
      "visual_description": None,  # derived from question
      "key_relationships": "hierarchical_relationships",
      "functions": "label_descriptions",
      "processes": "sequence_flow_data.flow_description",
      "flow_sequences": "sequence_flow_data.sequence_items",
      "temporal_order": "sequence_flow_data.sequence_items",
      "categories": "comparison_data.sorting_categories",
      "classifications": "comparison_data.groups",
      "definitions": "label_descriptions",
      "cause_effect": None,  # not retrieved by DK
      "misconceptions": None,  # not retrieved by DK
      "similarities_differences": "comparison_data",
      "hierarchy": "hierarchical_relationships",
  }
  ```
- [x] `resolve_dk_field(dk: dict, field_name: str) -> Any` — dot-path traversal
- [x] `project_dk_for_mechanic(dk: dict, dk_fields_needed: list[str]) -> dict` — returns subset

### 1.8 Mechanic Contracts Import

**File**: `backend/app/v4/contracts.py` (~50 LOC)

- [x] Import existing contracts from `backend/app/config/mechanic_contracts.py` (already exists, 16KB)
- [x] `SUPPORTED_MECHANICS: set[str]` — 8 types
- [x] `CONTENT_ONLY_MECHANICS: set[str]` — `{"sequencing", "sorting_categories", "memory_match", "branching_scenario"}`
- [x] `ZONE_BASED_MECHANICS: set[str]` — `{"drag_drop", "click_to_identify", "trace_path", "description_matching"}`
- [x] `MODEL_ROUTING: dict[str, str]` — mechanic_type -> "pro" | "flash" (from audit 38):
  - Pro: branching_scenario, sorting_categories, sequencing, trace_path
  - Flash: drag_drop, click_to_identify, memory_match, description_matching
- [x] `build_capability_spec() -> dict` — generate from contracts (not hardcoded — audit 39 Finding 26)
- [x] `TRIGGER_MAP: dict[tuple[str, str], str]` — (trigger_hint, mechanic_type) -> frontend trigger (audit 39 Finding 13):
  ```python
  TRIGGER_MAP = {
      ("completion", "drag_drop"): "all_zones_labeled",
      ("completion", "trace_path"): "path_complete",
      ("completion", "click_to_identify"): "identification_complete",
      ("completion", "sequencing"): "sequence_complete",
      ("completion", "sorting_categories"): "sorting_complete",
      ("completion", "memory_match"): "memory_complete",
      ("completion", "branching_scenario"): "branching_complete",
      ("completion", "description_matching"): "description_complete",
      ("score_threshold", "*"): "percentage_complete",
      ("time_elapsed", "*"): "time_elapsed",
      ("user_choice", "*"): "user_choice",
  }
  ```

### Phase 1 Verification

- [x] All Pydantic models validate with sample data
- [x] `python -c "from app.v4.state import V4MainState"` works
- [x] `python -c "from app.v4.schemas.game_plan import GamePlan"` works
- [x] `python -c "from app.v4.schemas.mechanic_content import *"` works
- [x] `python -c "from app.v4.contracts import SUPPORTED_MECHANICS, TRIGGER_MAP"` works
- [x] Field name mismatches from audit 33 are all addressed in MechanicContent schemas

---

## Phase 2: Validators & Deterministic Helpers

**Goal**: All deterministic logic works and is tested. No LLM calls yet.
**Depends on**: Phase 1
**Estimated**: ~14 files, ~1800-2200 LOC (including tests)

### 2.1 Game Plan Validator

**File**: `backend/app/v4/validators/game_plan_validator.py`

- [x] `validate_game_plan(plan: GamePlan) -> ValidationResult`
- [x] Check: all mechanic_types in SUPPORTED_MECHANICS (8 types)
- [x] Check: zone_labels referential integrity (all_zone_labels ⊇ scene.zone_labels ⊇ mechanic.zone_labels_used)
- [x] Check: content-only mechanics have empty zone_labels_used
- [x] Check: zone-based mechanics have zone_labels_used non-empty
- [x] Check: needs_diagram=true for scenes with zone-based mechanics
- [x] Check: needs_diagram=false is allowed for content-only scenes (D2)
- [x] Check: mechanic_connections reference valid mechanic_ids within same scene
- [x] Check: no cycles in mechanic_connections within a scene (DFS)
- [x] Check: at least 1 scene, at least 1 mechanic per scene
- [x] Check: distractor_labels disjoint from all_zone_labels (FOL R6.3 — audit 39 Finding 9)
- [ ] Check: mechanic compatibility matrix (audit 39 Finding 18 — move here from interaction_validator)
- [x] Check: ContentBrief completeness per mechanic (audit 39 Finding 14):
  - sequencing: `mechanic_specific_hints` should have sequence guidance
  - branching: should have narrative structure hints
  - sorting: should have category hint
- [x] Compute: `max_score = points_per_item * expected_item_count` per mechanic
- [x] Compute: `scene_max_score = sum(mechanic.max_score)` per scene
- [x] Compute: `total_max_score = sum(scene.max_score)`
- [ ] Increment `design_retry_count` in returned state update

### 2.2 Content Validator

**File**: `backend/app/v4/validators/content_validator.py`

- [x] `validate_mechanic_content(content, mechanic_plan: MechanicPlan) -> ValidationResult`
- [x] **Strict**: `len(items) == expected_item_count` (audit 39 Finding 7 — strict enforcement, retry if different)
- [x] **Strict**: All zone_label references must be in `mechanic_plan.zone_labels_used` (canonical — audit 39 Finding 2)
- [x] Per-mechanic validation:
  - [x] drag_drop: labels non-empty, no duplicates, all in canonical zone_labels
  - [x] click_to_identify: prompts non-empty, each has target_label in zone_labels, explanation non-empty
  - [x] trace_path: paths non-empty, each has >= 2 waypoints with valid labels, waypoints ordered
  - [x] sequencing: items non-empty, correct_order matches item IDs, no duplicates, sequence_type valid
  - [x] sorting: categories >= 2, each item has valid correctCategoryId, no orphan categories
  - [x] memory_match: pairs >= 3, unique IDs, front/back non-empty, frontType/backType valid
  - [x] branching: startNodeId exists in nodes, all non-end nodes have options, all nextNodeId valid or null for end, all end nodes reachable from start (DFS), no orphan nodes
  - [x] description_matching: descriptions non-empty, all keys in zone_labels, descriptions are distinct

### 2.3 Blueprint Assembler (Deterministic)

**File**: `backend/app/v4/helpers/blueprint_assembler.py`

This is the most complex helper. Transforms all upstream outputs into `InteractiveDiagramBlueprint` shape.

Key sources: audit 33 (current assembler analysis), audit 37 (schema gaps), audit 41 (per-mechanic data flow).

- [x] `assemble_blueprint(game_plan, mechanic_contents, interaction_results, assets, zone_data) -> dict`
- [x] Set `templateType: "INTERACTIVE_DIAGRAM"`
- [x] Set `title` from game_plan
- [x] Set `narrativeIntro` from game_plan.title + scene learning_goals
- [x] Build `diagram` object: `{assetUrl, assetPrompt, zones[]}` from assets
  - [x] For content-only scenes: `diagram.assetUrl = null`, `diagram.zones = []` (D2)
- [x] Build `labels[]` with `id`, `text`, `correctZoneId` (from zone_matcher)
- [x] Build `distractorLabels[]` (separate array, with `isDistractor: true`)
  - [x] Only assign global distractors to scenes with zone-based mechanics (D3)
- [x] Build `mechanics[]` array:
  - [x] Each: `{type, config: {}, scoring: ScoringRules, feedback: FeedbackRules}`
  - [x] Scoring/feedback from `interaction_results`
- [x] Build `modeTransitions[]`:
  - [x] Translate MechanicConnection to ModeTransition using:
    - `mechanic_id -> mechanic_type` lookup (audit 39 Finding 23)
    - `TRIGGER_MAP` for trigger translation (audit 39 Finding 13)
  - [x] Set `trigger_value` for score_threshold transitions
- [x] Set `interactionMode` from first mechanic type
- [x] Set `animationCues` with sensible defaults:
  ```python
  {"correctPlacement": "pulse-green", "incorrectPlacement": "shake-red"}
  ```
- [x] Populate per-mechanic config fields at **blueprint root**:
  - [x] `dragDropConfig` — from DragDropContent + defaults
  - [x] `clickToIdentifyConfig` — config fields
  - [x] `identificationPrompts[]` — **AT ROOT** (audit 37 H1 — NOT inside clickToIdentifyConfig)
  - [x] `tracePathConfig` — config fields (particleSpeed must be string enum, NOT float — audit 33 B-TP1)
  - [x] `paths[]` — **AT ROOT** (audit 37 H2 — NOT inside tracePathConfig)
  - [x] `sequenceConfig` — items + correct_order + layout_mode
  - [x] `sortingConfig` — categories (with `label` not `name`) + items (with `correctCategoryId`)
  - [x] `memoryMatchConfig` — pairs (with `front/back`) + gridSize as [int,int] (NOT string — audit 33 B-MM1)
  - [x] `branchingConfig` — nodes (with `question/options/nextNodeId/isCorrect`) + startNodeId
  - [x] `descriptionMatchingConfig` — `{descriptions: Record<zoneId, description>, mode}`
  - [x] ALSO populate `zones[].description` for description_matching (dual source — audit 41 DM-4)
- [x] Populate `scoringStrategy` at root:
  - [x] `base_points_per_zone` from first mechanic's points_per_item
  - [x] `max_score` = total_max_score
- [x] Set `totalMaxScore` at root
- [x] Handle `is_timed`:
  - [x] If any mechanic has `is_timed: true`, set `timedChallengeWrappedMode` + `timeLimitSeconds` at root (D4)
- [x] Handle multi-scene: build `game_sequence.scenes[]` array
  - [x] Each scene as `GameScene` with per-scene configs in BOTH camelCase AND snake_case (audit 37 H10, audit 33 Section 4)
  - [x] Set `is_multi_scene: true` at root
  - [x] Promote first scene's configs to root level for backward compat
- [x] Set `generation_complete: true`

### 2.4 Zone Matcher

**File**: `backend/app/v4/helpers/zone_matcher.py`

- [x] `match_labels_to_zones(canonical_labels: list[str], detected_zones: list[dict]) -> dict[str, str]`
  - Returns mapping: label_text -> zone_id
- [x] Matching priority: exact match > case-insensitive > normalized (strip whitespace/punctuation) > substring > fuzzy
- [x] Use normalized canonical label for ID generation: `canonical_to_zone_id(label, scene_number) -> str`
- [x] Handle unmatched labels: log warning, assign dummy coordinates (last resort — audit 39 Finding 21)
- [x] Used by assembler to set:
  - `label.correctZoneId` (drag_drop)
  - `prompt.targetZoneId` + `prompt.targetLabelId` (click_to_identify)
  - `waypoint.zoneId` (trace_path)
  - Re-key `descriptions` from label -> zoneId (description_matching)

### 2.5 Scoring Helpers

**File**: `backend/app/v4/helpers/scoring.py`

- [x] `compute_mechanic_score(items_count: int, points_per_item: int) -> int`
- [x] `compute_scene_score(mechanics: list) -> int`
- [x] `compute_total_score(scenes: list) -> int`
- [x] `validate_score_chain(plan: dict) -> list[str]` — check arithmetic consistency bottom-up
- [x] Cross-check: if content item count differs from plan after retry, interaction_designer scores become authoritative (audit 39 Finding 7)

### 2.6 Utility Functions

**File**: `backend/app/v4/helpers/utils.py`

Reuse heavily from `blueprint_assembler_tools.py` (`_make_id`, `_normalize_coordinates`, `_postprocess_zones`, `_clamp_coordinate`, `_normalize_label`).

- [x] `generate_zone_id(scene_number: int, label: str) -> str` — deterministic from canonical label
- [x] `generate_label_id(scene_number: int, index: int) -> str`
- [x] `generate_mechanic_id(scene_number: int, mechanic_type: str) -> str`
- [x] `normalize_zone_coordinates(zone_dict: dict) -> dict` — flatten nested `coordinates` to top-level x/y/radius or points
- [x] `clamp_coordinate(value: float, min_val: float = 0, max_val: float = 100) -> float`
- [x] `postprocess_zones(zones: list[dict]) -> list[dict]` — add `points` field for frontend polygon rendering
- [x] `normalize_label_text(label: str) -> str` — lowercase, strip, collapse whitespace
- [x] `deduplicate_labels(labels: list[str]) -> list[str]` — case-insensitive dedup

### 2.7 Blueprint Validator (Final Gate)

**File**: `backend/app/v4/validators/blueprint_validator.py`

- [x] `validate_blueprint(blueprint: dict) -> ValidationResult`
- [x] Check: `templateType == "INTERACTIVE_DIAGRAM"`
- [x] Check: `diagram` exists
- [x] Check: For scenes with zone-based mechanics: `diagram.zones[]` non-empty
- [x] Check: For content-only scenes: zones/labels CAN be empty (D2)
- [x] Check: `labels[]` all have `correctZoneId` referencing valid zone ID
- [x] Check: `mechanics[]` non-empty
- [x] Check: per-mechanic config present at root for each mechanic type in `mechanics[]`
- [x] Check: `identificationPrompts[]` exists at root if click_to_identify present
- [x] Check: `paths[]` exists at root if trace_path present
- [x] Check: score arithmetic: per-mechanic → scene → total matches
- [x] Check: modeTransitions reference valid trigger types (from frontend's 14 triggers)
- [x] Check: `animationCues` present
- [x] Check: branching config graph connectivity (all end nodes reachable)
- [x] Check: sorting items all reference valid category IDs
- [x] Check: memory pairs have unique IDs

### 2.8 Tests for Phase 2

**File**: `backend/tests/v4/`

- [x] `conftest.py` — shared fixtures:
  - Sample GamePlan (single scene, drag_drop)
  - Sample GamePlan (multi-scene, 3 mechanics with connections)
  - Sample GamePlan (content-only scene: sequencing + sorting)
  - Sample MechanicContent per mechanic type (8 total)
  - Sample InteractionResult
  - Sample AssetResult with zone data
- [x] `test_game_plan_validator.py` — 10+ test cases:
  - Valid single-scene plan
  - Valid multi-scene plan
  - Missing zone_labels referential integrity
  - Cycle in mechanic_connections
  - Unsupported mechanic type
  - Content-only scene with needs_diagram=false (should pass)
  - Content-only mechanic with zone_labels_used (should fail)
  - Score computation correctness
  - Distractor overlap with zone_labels (should fail)
- [x] `test_content_validator.py` — 8 tests (one per mechanic) + edge cases:
  - Item count mismatch
  - Branching unreachable end nodes
  - Sorting with orphan categories
- [x] `test_blueprint_assembler.py` — 8+ tests:
  - Single scene drag_drop
  - Multi-scene with transitions
  - Content-only scene (no diagram)
  - identificationPrompts at root (not inside config)
  - paths at root (not inside config)
  - Field name normalization (front/back, question/options, label not name)
  - Timed mechanic produces timedChallengeWrappedMode
  - Score rollup correctness
- [x] `test_zone_matcher.py` — 5 tests (exact, case insensitive, normalized, fuzzy, unmatched)
- [x] `test_scoring.py` — 3 tests (basic, rollup, mismatch detection)

### Phase 2 Verification

- [x] All validator tests pass: `PYTHONPATH=. pytest tests/v4/ -v` — **51/51 passed**
- [x] `assemble_blueprint()` produces valid output with mock data
- [x] Zone matcher handles edge cases without crashing
- [x] Score computation is correct for sample plans
- [x] Blueprint passes blueprint_validator for all test cases
- [x] Content-only scene assembles correctly with empty zones

---

## Phase 3: Prompts & Agent Functions

**Goal**: All LLM-calling functions work standalone (callable without graph). Tested via E2E script.
**Depends on**: Phase 1, Phase 2
**Estimated**: ~10 files, ~1500-2000 LOC

### 3.1 Game Designer Prompt

**File**: `backend/app/v4/prompts/game_designer.py`

- [x] System prompt (~300 tokens): role, scope, DO/DON'T from V3
- [x] `build_game_designer_prompt(question, pedagogy, dk, capability_spec, examples, retry_info) -> str`
- [x] Capability spec injection: generated by `build_capability_spec()` from contracts
- [x] Negative constraints:
  - "NEVER default to drag_drop — choose the best mechanic for the learning objective"
  - "NEVER compute max_score — leave it as 0, the validator will compute it"
  - "NEVER use compare_contrast or hierarchical — they are not yet supported"
  - "NEVER reference zone IDs — use zone label TEXT from all_zone_labels"
- [x] Output format docs (brief field descriptions — schema enforced via response_format)
- [x] 3 handcrafted example GamePlans:
  - [x] Example 1: Single-scene drag_drop — "Label parts of a plant cell" (~300 tokens)
  - [x] Example 2: Multi-scene, 3 mechanics — "Heart anatomy" with drag_drop → trace_path → sequencing (~700 tokens)
  - [x] Example 3: Content-only mechanics — "Cell division" with sequencing + memory_match, no diagram (~500 tokens)
  - [x] Examples show `"max_score": 0` with comment "COMPUTED_BY_VALIDATOR"
- [x] Retry section template: validator issues as bullets + condensed previous output (~500 tokens, not full)

### 3.2 Content Generator Prompts

**File**: `backend/app/v4/prompts/content_generator.py`

8 per-mechanic prompt templates (~500 tokens each):

- [x] `build_content_prompt(mechanic_type, content_brief, scene_context, dk_subset, zone_labels) -> str`
- [x] Template: drag_drop — "Generate labels for these zones: {zone_labels}. Also generate {distractor_count} distractors."
- [x] Template: click_to_identify — "Generate identification prompts. Each must reference a zone by label TEXT."
- [x] Template: trace_path — "Generate paths with waypoints. Each waypoint references a zone label TEXT. Waypoints must be ordered."
- [x] Template: sequencing — "Generate {item_count} sequence items with explanations and correct ordering."
- [x] Template: sorting_categories — "Generate categories with `label` field and items with `correctCategoryId`."
- [x] Template: memory_match — "Generate pairs with `front`/`back` fields (NOT term/definition)."
- [x] Template: branching_scenario — "Generate a decision tree. Use `question` (NOT prompt), `options` (NOT choices), `nextNodeId` (camelCase). Ensure all end nodes reachable from startNodeId."
- [x] Template: description_matching — "Generate descriptions for each zone label. Each key is a zone label TEXT."
- [x] Each template includes:
  - Context header with scene info
  - DK injection slot (with fallback: "If no domain knowledge provided, generate from the question context")
  - Quality criteria
  - Schema via `response_format` (Pydantic model with `extra="allow"`)
  - Explicit "use THESE EXACT zone labels: {zone_labels}" constraint

### 3.3 Interaction Designer Prompt

**File**: `backend/app/v4/prompts/interaction_designer.py`

- [x] `build_interaction_prompt(scene_plan, mechanic_contents, pedagogy) -> str`
- [x] Per-mechanic scoring pattern guidance (dynamic — only inject for this scene's mechanics)
- [x] Transition rules scoped to scene's mechanic types + compatibility matrix
- [x] Output: ScoringRules + FeedbackRules per mechanic_id, ModeTransitions for scene
- [x] Misconception feedback templates per mechanic type (carry from V3)

### 3.4 Retry Templates

**File**: `backend/app/v4/prompts/retry.py`

- [x] `build_retry_section(validation_result: ValidationResult, previous_output_condensed: str) -> str`
- [x] `condense_game_plan(plan: dict) -> str` — structure + types only, no ContentBriefs (~500 tokens)
- [x] `condense_mechanic_content(content: dict) -> str` — full content (small enough)
- [x] Max retry budget per agent: game_designer=2, content_generator=1 (inline), interaction_designer=1

### 3.5 Input Analyzer Agent

**File**: `backend/app/v4/agents/input_analyzer.py`

- [x] `async def input_analyzer(state: V4MainState) -> dict`
- [x] Reuse ~70% from `input_enhancer.py`
- [x] Output: `pedagogical_context` (bloom_level, subject, topic, difficulty, grade_level)
- [x] Model: gemini-2.5-flash

### 3.6 DK Retriever Agent

**File**: `backend/app/v4/agents/dk_retriever.py`

- [x] `async def dk_retriever(state: V4MainState) -> dict`
- [x] Reuse ~60% from `domain_knowledge_retriever.py`
- [x] Core reusable functions: `_detect_query_intent()`, `_search_for_sequence()`, `_generate_label_descriptions()`, `_generate_comparison_data()`
- [x] Output: `domain_knowledge` dict (canonical_labels, label_descriptions, sequence_flow_data, comparison_data, hierarchical_relationships)
- [x] DK truncation: hard char limit 4000 chars per field (V3 pattern)
- [x] Empty DK: Only drag_drop is FATAL if canonical_labels empty. All others are DEGRADED (audit 38 Section 4)
- [x] Model: gemini-2.5-flash

### 3.7 Game Designer Agent

**File**: `backend/app/v4/agents/game_designer.py`

- [x] `async def game_designer(state: V4MainState) -> dict`
- [x] Build prompt using `build_game_designer_prompt()`
- [x] Call LLM with `response_format` = GamePlan schema (Pydantic with `extra="allow"`)
- [x] Handle retry: read `design_validation` from state, build retry section
- [x] Output: `game_plan` (dict — model_dump of validated GamePlan)
- [x] Model: gemini-2.5-pro (always — most critical agent)

### 3.8 Content Build Node (Sequential)

**File**: `backend/app/v4/agents/content_builder.py`

Single node that loops through all scenes and mechanics sequentially.

- [x] `async def content_build_node(state: V4MainState) -> dict`
- [x] For each scene in game_plan.scenes:
  - [x] Build scene_context (inline helper: scene title, learning_goal, zone_labels)
  - [x] Project DK fields per mechanic using `project_dk_for_mechanic()`
  - [x] For each mechanic in scene.mechanics:
    - [x] Select model: Pro or Flash based on `MODEL_ROUTING[mechanic_type]`
    - [x] Build prompt using `build_content_prompt()`
    - [x] Call LLM with response_format = per-mechanic MechanicContent Pydantic model
    - [x] Validate using `validate_mechanic_content()`
    - [x] Retry ONCE if validation fails (inline — same node, same call)
    - [x] Append `{mechanic_id, scene_id, mechanic_type, content: dict}` to mechanic_contents
  - [x] Build interaction prompt for this scene using `build_interaction_prompt()`
  - [x] Call LLM for interaction design (scoring/feedback/transitions)
  - [x] Validate interaction output (score arithmetic check)
  - [x] Append to interaction_results
- [x] Output: `mechanic_contents: list[dict]`, `interaction_results: list[dict]`
- [x] On mechanic content failure after retry: append to mechanic_contents with `status: "failed"`, set `is_degraded: true`

### 3.9 Asset Dispatcher (Send Worker)

**File**: `backend/app/v4/agents/asset_dispatcher.py`

- [x] `async def asset_worker(state: dict) -> dict`
  - Receives via Send: `{scene_id, image_spec, zone_labels}`
  - [x] Step 1: Search for diagram image
    - Use `backend/app/services/asset_gen/search.py` or `image_retrieval.search_diagram_images()` (D7)
  - [x] Step 2: Zone detection via `gemini_service.detect_zones_with_polygons()`
  - [x] Step 3: Quality validation (detected zone count vs expected labels count)
  - [ ] Step 4: Optional SAM3 refinement if available (deferred — SAM3 integration is optional)
  - [x] Return: `AssetResult` dict: `{scene_id, status: "success"|"error", diagram_url, zones, match_quality}`
  - [x] On error: **catch exception**, return `{scene_id, status: "error", error: str}` (audit 39 Finding 17 — NEVER raise, always return status)
- [x] Fallback chain: search → regenerate query → placeholder_image (audit 39 Finding 21)
- [x] Model: gemini-2.5-flash for zone detection

### 3.10 Blueprint Assembler Node

**File**: `backend/app/v4/agents/assembler_node.py`

- [x] `def assembler_node(state: V4MainState) -> dict`
- [x] Filter out failed mechanic_contents (status: "failed") — handle gracefully
- [x] Call `assemble_blueprint()` from Phase 2
- [x] Call `validate_blueprint()` — final gate
- [x] If validation fails: log warnings, attempt repair (remove invalid mechanics), re-validate
- [x] Set `generation_complete = True` (**critical** — without this, routes/generate.py marks run as "error")
- [x] Set `blueprint` in state
- [x] 100% deterministic — no LLM

### Phase 3 Verification

- [x] Each agent function callable standalone with mock state dict
- [ ] `input_analyzer` returns valid pedagogical_context (requires LLM — verified import + structure)
- [ ] `dk_retriever` returns valid domain_knowledge (requires LLM + Serper — verified import + structure)
- [ ] `game_designer` produces valid GamePlan for test question (requires LLM — verified import + structure)
- [ ] `content_build_node` produces valid contents for mock GamePlan with 2 mechanics (requires LLM — verified import)
- [ ] `asset_worker` returns valid result for test image query (requires Serper + Gemini — verified import)
- [x] `assembler_node` produces valid blueprint from mock inputs (tested — PASS)
- [x] Blueprint from assembler_node passes blueprint_validator (tested — PASS)
- [x] All prompt builders tested: game_designer (12K chars), content_generator (8 templates), interaction_designer, retry
- [x] All Phase 3 imports verified: 10 files, all import successfully
- [x] Phase 2 tests still pass: 51/51 in 0.03s

---

## Phase 4: Graph Wiring

**Goal**: Full LangGraph pipeline compiles, runs, checkpoints.
**Depends on**: Phase 1, 2, 3
**Estimated**: ~5 files, ~400-500 LOC

### 4.1 Main Graph

**File**: `backend/app/v4/graph.py`

```python
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

builder = StateGraph(V4MainState)

# Phase 0: Parallel context (multiple START edges work in LangGraph 1.0.6)
builder.add_node("input_analyzer", input_analyzer)
builder.add_node("dk_retriever", dk_retriever)
builder.add_node("phase0_merge", phase0_merge)
builder.add_edge(START, "input_analyzer")
builder.add_edge(START, "dk_retriever")
builder.add_edge("input_analyzer", "phase0_merge")
builder.add_edge("dk_retriever", "phase0_merge")

# Phase 1: Design with retry loop
builder.add_node("game_designer", game_designer)
builder.add_node("game_plan_validator", game_plan_validator_node)
builder.add_edge("phase0_merge", "game_designer")
builder.add_edge("game_designer", "game_plan_validator")
builder.add_conditional_edges("game_plan_validator", design_router,
    {"retry": "game_designer", "pass": "content_build"})

# Phase 2: Sequential content
builder.add_node("content_build", content_build_node)

# Phase 3: Parallel assets via Send
builder.add_node("asset_worker", asset_worker)
builder.add_node("asset_merge", asset_merge)
builder.add_conditional_edges("content_build", asset_send_router)
builder.add_edge("asset_worker", "asset_merge")
builder.add_conditional_edges("asset_merge", asset_retry_router,
    {"retry_assets": ..., "assemble": "blueprint_assembler"})

# Phase 4: Assembly
builder.add_node("blueprint_assembler", assembler_node)
builder.add_node("blueprint_validator_node", blueprint_validator_node)
builder.add_edge("blueprint_assembler", "blueprint_validator_node")
builder.add_edge("blueprint_validator_node", END)
```

- [x] Register all nodes with `builder.add_node()`
- [x] Wire Phase 0 fan-out from START (parallel input_analyzer + dk_retriever)
- [x] Wire Phase 0 merge node
- [x] Wire Phase 1 retry loop (game_designer → validator → design_router)
- [x] Wire Phase 2 content_build_node
- [x] Wire Phase 3 asset Send dispatch:
  - [x] `asset_send_router()` returns `[Send("asset_worker", {...}) for scene_needing_diagram]`
  - [x] Skip content-only scenes (needs_diagram=False)
  - [x] If NO scenes need diagrams: route directly to assembler
  - [x] `asset_merge()` deduplicates by scene_id, separates successes from failures
  - [x] `asset_retry_router()` returns Send for failed scenes (max 1 retry) or routes to assembler
- [x] Wire Phase 4 assembly (assembler → END, validator embedded in assembler)
- [x] Wire END

### 4.2 Router Functions

**File**: `backend/app/v4/routers.py`

- [x] `design_router(state) -> str` — "retry" or "pass"
  - Read `design_validation.passed` and `design_retry_count`
  - Max 2 retries, then proceed with override
- [x] `asset_send_router(state) -> Union[str, list[Send]]`
  - Build Send per scene from game_plan where `needs_diagram == True`
  - If no scenes need diagram: return `"blueprint_assembler"` (string, not Send)
- [x] `asset_retry_router(state) -> Union[str, list[Send]]`
  - Reads `generated_assets` (deduped by merge), not `failed_asset_scene_ids` (reducer accumulates)
  - If failures and `asset_retry_count <= 1`: return `[Send("asset_worker", {...}) for failed]`
  - Else: return `"blueprint_assembler"`

### 4.3 Merge Nodes

**File**: `backend/app/v4/merge_nodes.py`

- [x] `phase0_merge(state) -> dict`
  - Returns `{}` — pure sync barrier (outputs already in state from parallel edges)
- [x] `asset_merge(state) -> dict`
  - Deduplicate `generated_assets_raw` by scene_id (keep latest — handles retry accumulation)
  - Returns `{generated_assets, asset_retry_count}` (NOT failed_asset_scene_ids — that's a reducer)

### 4.4 Checkpointing

- [ ] Use `AsyncSqliteSaver` with FastAPI lifespan (DEFERRED — needs integration test)
- [ ] Thread ID = `_run_id` from GenerateRequest
- [ ] Add cleanup: delete checkpoints for successful runs after 24h

### 4.5 Graph Compilation

- [x] `create_v4_graph(checkpointer=None) -> CompiledGraph`
- [x] Wrap all agent nodes with `wrap_agent_with_instrumentation()` via `_v4_wrap()`
- [x] Register V4 agent names in `instrumentation.py` (input/output keys)
- [x] Register V4 agent model assignments in `agent_models.py` (model, temperature, max_tokens)
- [x] Register V4 agent timeouts in `graph.py` `AGENT_TIMEOUTS`
- [x] Register "v4" preset in `get_compiled_graph()`

### Phase 4 Verification

- [x] `create_v4_graph()` compiles without error (9 nodes, 14 edges)
- [x] Topology verified: parallel START fan-out, design retry loop, Send dispatch + retry, assembler → END
- [x] **Send API tested**: 2 scenes dispatch 2 Send objects, mixed scenes filter correctly
- [x] **Retry loop tested**: design_router retries within limit, passes on exceeded
- [x] **Asset retry tested**: failed scenes trigger retry Send, limit respected
- [x] Content-only game plan routes directly to assembler (no Send)
- [x] game_plan_validator_node: validates plan, computes scores, handles missing/invalid plans
- [x] asset_merge: deduplicates by scene_id, increments retry_count
- [ ] Checkpointing: DEFERRED — needs integration test with real pipeline run

---

## Phase 5: Integration & E2E

**Goal**: V4 pipeline accessible via API, observable in frontend, produces playable games.
**Depends on**: Phase 1, 2, 3, 4
**Estimated**: ~5 files modified, ~300 LOC

### 5.1 Route Integration

**File**: `backend/app/routes/generate.py` (modify)

- [x] Add `"v4"` to pipeline preset routing in `get_compiled_graph()` and `presets_needing_full_graph`
- [x] V4 state extraction compatible — uses same `generation_complete` + `blueprint` pattern as V3:
  ```python
  if pipeline_preset == "v4":
      blueprint = final_state.get("blueprint")
      is_complete = final_state.get("generation_complete", False)
  ```
- [x] Add V4 agent output recording in `_build_agent_outputs()` (audit 39 Finding 12 — hardcoded V3 agent names)
- [ ] Add V4 asset serving route if assets stored locally: `GET /api/assets/v4/{run_id}/{filename}`

### 5.2 Instrumentation

**File**: `backend/app/agents/instrumentation.py` (modify)

- [x] Add ~10 entries to `AGENT_METADATA_REGISTRY` for V4 agents (done: all 10)
- [x] Add input/output key mappings in `extract_input_keys()` and `extract_output_keys()`
- [ ] For Send workers: include `scene_id` in metadata for per-scene timeline display

### 5.3 Config

**File**: `backend/app/config/agent_models.py` (modify)

- [x] Add V4 agent model assignments (done in Phase 4.5 — model, temperature, max_tokens)

### 5.4 Pipeline View

**File**: `frontend/src/components/pipeline/PipelineView.tsx` (modify)

- [x] Add V4 agent metadata entries in `AGENT_METADATA` (done: 9 entries)
- [x] Add V4 graph layout (V4_GRAPH_LAYOUT — 8 columns with parallel phase0)
- [x] V4 topology: 10 nodes (9 + __start__), auto-detect + preset detection in both useMemos

### 5.5 E2E Test Script

**File**: `backend/scripts/test_v4_pipeline.py`

- [x] Test Q1: "Label the parts of a plant cell" (single scene, drag_drop)
  - Validate: blueprint.diagram.zones non-empty, labels with correctZoneId, dragDropConfig present
- [x] Test Q2: "Heart: label chambers, trace blood flow, order cardiac cycle" (multi-scene, 3 mechanics)
  - Validate: 3 scenes, modeTransitions present, paths[] at root, sequenceConfig present
- [x] Test Q3: "Cell division: sort phases, match terms" (content-only mechanics, no diagram)
  - Validate: diagram.assetUrl null or absent, sortingConfig present, memoryMatchConfig present
- [x] Test Q4: "Describe the function of each organelle" (single scene, description_matching)
  - Validate: descriptionMatchingConfig.descriptions non-empty, zones[].description populated
- [x] Each test validates:
  - Blueprint passes blueprint_validator
  - All fields match frontend type expectations
  - Score arithmetic correct
  - generation_complete == true
- [x] Report: timing per phase, token usage, success/failure per stage
- [x] Dry-run (graph compilation only) mode verified

### Phase 5 Verification

- [ ] `curl -X POST localhost:8000/api/generate -d '{"question": "...", "config": {"pipeline_preset": "v4"}}'` starts pipeline
- [ ] Pipeline completes successfully for test Q1 (drag_drop)
- [ ] Pipeline completes successfully for test Q3 (content-only — no diagram)
- [ ] Blueprint loads in frontend game view without console errors
- [ ] Game is playable (labels draggable, zones highlighted, scoring works)
- [ ] Pipeline observability shows V4 stages in PipelineView
- [ ] Multi-scene game works (scene transitions, per-scene configs)

---

## Dependency Graph

```
Phase 1 (Schemas & State)
    ↓
Phase 2 (Validators + Helpers + Tests)  ←── TDD: write tests first
    ↓
Phase 3 (Prompts + Agent Functions)     ←── test each standalone
    ↓
Phase 4 (Graph Wiring)                  ←── Send API prototype can start during Phase 2
    ↓
Phase 5 (Integration + E2E)
```

**Critical path items:**
1. **Send API prototype** (start during Phase 2) — if it fails, Phase 4 needs redesign to sequential
2. **Blueprint assembler** (Phase 2.3) — most complex deterministic logic, most field-name gotchas
3. **Game designer prompt** (Phase 3.1) — determines quality of all downstream
4. **Content-only scene handling** (Phase 2.1 + 2.3 + 2.7) — new pattern not in V3

---

## Deferred Items

| Item | Why Deferred | When to Add |
|------|-------------|-------------|
| compare_contrast mechanic | 4 CRITICAL gaps: dual-diagram pipeline, rect zones, cross-diagram correspondence (audit 41) | After V4 ships for 8 mechanics |
| hierarchical mechanic | Separate mode with HierarchyController, zoneGroups (audit 39 Finding 5) | After V4 ships |
| Score-gated scene transitions | Frontend sceneManager needs changes (D5) | After V4 MVP |
| SSE streaming endpoint | Nice-to-have for progress (audit 36 S6) | After E2E works |
| PostgreSQL checkpointer | Production scaling (audit 36) | Before production deploy |
| DSPy prompt optimization | Needs 50+ training runs (audit 38 P3-17) | After collecting data |
| Frontend Zod validation | Runtime safety — `engine/schemas/` already exists (D6) | Wire in during Phase 5 |
| Rate limiting for parallel Send | Gemini API limits (audit 39 Finding 27) | Add `max_concurrency` param |
| Checkpoint schema versioning | Dev-time schema changes invalidate checkpoints (audit 39 Finding 20) | Add `schema_version` field |

---

## V3 Bugs to NOT Repeat (from audits 33, 34)

These are bugs in the V3 assembler that V4 must avoid:

| Bug | V3 Source | V4 Fix |
|-----|-----------|--------|
| B-BR1: branching nodes use `prompt/choices/next_node_id` instead of `question/options/nextNodeId` | assembler_tools L809 | V4 MechanicContent uses frontend names directly |
| B-MM1: `gridSize` is string "4x3" instead of array [4,3] | assembler_tools L794 | V4 schema uses `list[int]` |
| B-TP1: `particleSpeed` is float instead of string enum | assembler_tools L607 | V4 schema uses Literal["slow","medium","fast"] |
| B-SC1: `containerStyle` default "card" is not valid | assembler_tools L770 | V4 uses valid enum values only |
| B-CC1: diagramA/diagramB never populated | assembler_tools L824-840 | Deferred (compare_contrast deferred) |
| B-DM1: description_matching zone lookup is case-sensitive | assembler_tools L698 | V4 zone_matcher uses normalized matching |
| B-HI1: zoneGroups never built from hierarchy | assembler_tools L251 | Deferred (hierarchical deferred) |
| B-TC1: timed_challenge never handled | assembler_tools (absent) | V4 handles via is_timed modifier (D4) |
| Scores/feedback silently dropped | assembler_tools L654-662 | V4 propagates from interaction_results explicitly |

---

## File Summary

| Phase | New Files | Modified Files | LOC |
|-------|-----------|---------------|-----|
| 1 | 8 | 0 | ~1200-1500 |
| 2 | 12 (incl tests) | 0 | ~1800-2200 |
| 3 | 10 | 0 | ~1500-2000 |
| 4 | 3 | 2 | ~400-500 |
| 5 | 1 | 5 | ~300 |
| **Total** | **34** | **7** | **~5200-6500** |

---

## Audit Cross-Reference

Every finding from audits 35-41 is accounted for below. Items marked ✓ are in the checklist. Items marked DEFERRED are in the deferred table.

| Audit | Finding | Status |
|-------|---------|--------|
| 35 C1 | GameSpecification incompatible | ✓ Decision: use InteractiveDiagramBlueprint |
| 35 C2 | ContentBrief undefined | ✓ Phase 1.2 |
| 35 C3 | MechanicContent undefined | ✓ Phase 1.3 |
| 35 C4 | V4MainState undefined | ✓ Phase 1.1 |
| 35 C5 | Nested Send doesn't work | ✓ Decision: sequential content, Send for assets only |
| 35 C6 | SqliteSaver wrong | ✓ Phase 4.4 AsyncSqliteSaver |
| 35 C7 | compare_contrast gaps | DEFERRED |
| 35 C8 | Zone ID chicken-and-egg | ✓ Phase 2.4 zone_matcher |
| 35 C9 | Score arithmetic | ✓ Phase 2.5 deterministic scoring |
| 36 C1 | V4MainState | ✓ Phase 1.1 |
| 36 C2 | Nested Send | ✓ Sequential content decision |
| 36 C3 | SqliteSaver | ✓ Phase 4.4 |
| 36 S1 | Retry counter location | ✓ Phase 2.1 (validators increment) |
| 36 S2 | Max retries behavior | ✓ Phase 4.2 (proceed with override) |
| 36 S4 | One failure kills all | ✓ Phase 3.9 (catch exception, return status) |
| 36 S5 | Error state schema | ✓ Phase 1.1 (phase_errors, is_degraded) |
| 36 S6 | No streaming | DEFERRED (SSE) |
| 37 C1-C8 | Schema gaps | ✓ Phase 1.2-1.4, Phase 2.3 |
| 37 H1 | identificationPrompts at root | ✓ Phase 2.3 |
| 37 H2 | paths at root | ✓ Phase 2.3 |
| 37 H3 | ScoringRules/FeedbackRules | ✓ Phase 1.4 |
| 37 H4 | MechanicConnection | ✓ Phase 1.2 |
| 37 H5 | front/back | ✓ Phase 1.3 |
| 37 H6 | question/options | ✓ Phase 1.3 |
| 37 H7 | Zone coordinate format | ✓ Phase 2.6 |
| 37 H8 | hierarchical | DEFERRED |
| 38 all | Prompt decisions | ✓ Phase 3.1-3.4 |
| 39 F1 | Phase 0 parallel | ✓ D1 discussion item |
| 39 F2 | Zone ID timing | ✓ Phase 2.4 |
| 39 F4 | Compare contrast | DEFERRED |
| 39 F5 | Hierarchical | DEFERRED |
| 39 F6 | Scene transitions | ✓ D5 (MVP: auto only) |
| 39 F7 | Score rollup | ✓ Phase 2.5 |
| 39 F8 | Empty scenes | ✓ D2, Phase 2.1, 2.3, 2.7 |
| 39 F9 | Distractors | ✓ D3, Phase 2.3 |
| 39 F10 | Retry cleanup | ✓ Phase 4.3 (dedup in merge) |
| 39 F11 | Adapter | ✓ Decision: no adapter, output blueprint directly |
| 39 F12 | Observability | ✓ Phase 5.2 |
| 39 F13 | Trigger mismatch | ✓ Phase 1.8 TRIGGER_MAP |
| 39 F14 | ContentBrief completeness | ✓ Phase 2.1 |
| 39 F15 | Timed wrapper | ✓ D4 |
| 39 F17 | Send error propagation | ✓ Phase 3.9 |
| 39 F18 | Compatibility matrix | ✓ Phase 2.1 |
| 39 F21 | Asset fallback | ✓ Phase 3.9 |
| 39 F22 | Model routing | ✓ Phase 1.8 MODEL_ROUTING |
| 39 F23 | Mode transition translation | ✓ Phase 2.3 |
| 39 F26 | Capability spec drift | ✓ Phase 1.8 build_capability_spec() |
| 39 F27 | Rate limiting | DEFERRED |
| 40 all | File inventory | ✓ File summary table updated |
| 41 all | Per-mechanic data flow | ✓ Phase 1.3 field names, Phase 2.3 config assembly |
