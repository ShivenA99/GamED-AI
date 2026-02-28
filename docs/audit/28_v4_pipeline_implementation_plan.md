# V4 Pipeline Complete Implementation Plan

**Date**: 2026-02-12
**Status**: Draft — awaiting user review and iteration
**Scope**: Full pipeline rearchitecture from V3 → V4
**Approach**: Design backwards from game engine → define what frontend needs → build pipeline to produce exactly that

---

## Context

### Why This Rearchitecture Is Needed

The V3 pipeline has 5 systemic problems that cannot be patched incrementally:

1. **30% data loss** — `blueprint_assembler_v3` drops interaction_designer output (mode_transitions, animations, distractor_feedback, scene_completion, scoring strategy). Each agent produces rich data that never reaches the frontend.

2. **Pervasive label/diagram bias** — 50+ instances of `drag_drop` defaults across 10+ files. 5 of 10 mechanics (sequencing, sorting_categories, memory_match, branching_scenario, compare_contrast) don't use labels/zones at all, yet the pipeline forces them through a label-centric model.

3. **Token bloat (~54K/run)** — ReAct loops replay full tool results every iteration. Full state serialized into every task prompt. Mechanic encyclopedias injected unconditionally. Achievable: 54K → 22K.

4. **Blueprint assembler bottleneck** — Single LLM call merges 4 upstream outputs without formal guarantees. Can hallucinate, drop fields, or fail entirely.

5. **No game logic formalization** — Scoring, completion, feedback are hardcoded per-mechanic in React. Adding/improving a mechanic requires changes in 5+ files across backend and frontend.

### Design Principle

**Start from what a playable game needs. Work backwards.**

```
Frontend Game → Game Specification DSL → Pipeline Agents → Domain Knowledge
     ↑                    ↑                      ↑                ↑
  "What shape?"    "What rules?"        "How to produce?"   "What to know?"
```

---

## Phase 0: Game Specification DSL (The Frontend Contract)

**Goal**: Define the exact JSON shape each mechanic needs for a fully playable game. This becomes the single source of truth that the entire pipeline targets.

**Rationale**: Currently there's no formal contract between backend and frontend. The blueprint shape is whatever the assembler LLM produces. By defining the target first, every pipeline stage knows exactly what it needs to produce.

### 0.1 Unified Blueprint Schema (Backend Pydantic + Frontend Zod)

Create `backend/app/agents/schemas/game_specification.py` — the **single** Pydantic model that represents a complete game. This replaces the current 4 separate schemas.

```python
# backend/app/agents/schemas/game_specification.py

class GameSpecification(BaseModel):
    """The complete game specification. This is what the frontend receives.
    Built incrementally by pipeline stages. Validated at each checkpoint."""

    # ── Game-Level (written by game_designer) ──
    title: str
    subject: str
    question_text: str
    learning_objectives: list[str]
    difficulty: str  # "easy" | "medium" | "hard"
    theme: Optional[ThemeConfig] = None

    # ── Scenes (written by game_designer, enriched by later stages) ──
    scenes: list[SceneSpec]

    # ── Game Flow (written by interaction_designer) ──
    scene_transitions: list[SceneTransition] = []

    # ── Global Config ──
    hierarchical_mode: Optional[HierarchicalConfig] = None  # NOT a mechanic
    timed_mode: Optional[TimedConfig] = None  # NOT a mechanic

    # ── Metadata ──
    pipeline_version: str = "v4"
    generation_timestamp: str = ""


class SceneSpec(BaseModel):
    """A single scene in a multi-scene game."""
    scene_id: str
    title: str
    description: str

    # ── Mechanic (one primary per scene) ──
    mechanic_type: str  # REQUIRED, no default
    mechanic_config: MechanicConfig  # Union type, mechanic-specific

    # ── Visual Assets (written by asset_generator) ──
    diagram: Optional[DiagramAsset] = None

    # ── Game Rules (written by interaction_designer) ──
    scoring_rules: list[GameRule] = []
    feedback_rules: list[GameRule] = []
    completion_rules: list[GameRule] = []

    # ── Mode Transitions (if multi-mode scene) ──
    mode_transitions: list[ModeTransition] = []

    # ── Hierarchical overlay (if applicable) ──
    zone_groups: list[ZoneGroup] = []
    temporal_constraints: list[TemporalConstraint] = []
```

### 0.2 Per-Mechanic Config Shapes (Matching Frontend Exactly)

Each mechanic config must match what the frontend's `types.ts` expects. These are the **target schemas** — if the backend produces data in these shapes, the frontend will render a playable game with zero translation.

```python
# MechanicConfig = Union of all per-mechanic configs

class DragDropConfig(BaseModel):
    zones: list[Zone]  # {id, label, x, y, width, height, description}
    labels: list[Label]  # {id, text, correct_zone_id}
    show_leader_lines: bool = False
    snap_animation: str = "spring"  # spring | ease | none
    show_info_panel_on_correct: bool = True
    max_attempts: int = 3
    shuffle_labels: bool = True
    show_hints: bool = False

class ClickToIdentifyConfig(BaseModel):
    zones: list[Zone]
    identification_prompts: list[IdentificationPrompt]  # {zone_label, prompt_text}
    prompt_style: str = "naming"  # naming | functional
    selection_mode: str = "any_order"  # sequential | any_order
    highlight_style: str = "outlined"  # subtle | outlined | invisible
    magnification_enabled: bool = False
    explore_mode_enabled: bool = False
    show_zone_count: bool = True

class TracePathConfig(BaseModel):
    zones: list[Zone]  # waypoints are zones
    paths: list[PathDefinition]  # {id, waypoints: [zone_id...], description}
    path_type: str = "linear"  # linear | branching | circular
    drawing_mode: str = "click_waypoints"  # click_waypoints | freehand
    particle_theme: str = "dots"  # dots | arrows | droplets | cells | electrons
    particle_speed: float = 1.0
    show_direction_arrows: bool = True
    show_waypoint_labels: bool = True

class SequencingConfig(BaseModel):
    items: list[SequenceItem]  # {id, text, description, image?, icon?, order_index}
    correct_order: list[str]  # ordered item IDs
    sequence_type: str = "linear"  # linear | cyclic | branching
    allow_partial_credit: bool = True
    layout_mode: str = "vertical_list"  # horizontal_timeline | vertical_list | circular_cycle | flowchart
    interaction_pattern: str = "drag_reorder"  # drag_reorder | drag_to_slots | click_to_swap
    card_type: str = "text_only"  # text_only | text_with_icon | image_with_caption
    connector_style: str = "arrow"  # arrow | line | numbered | none
    # NO zones, NO labels, NO diagram required

class SortingCategoriesConfig(BaseModel):
    items: list[SortingItem]  # {id, text, correct_category_id, description, difficulty}
    categories: list[SortingCategory]  # {id, label, description, color}
    sort_mode: str = "bucket"  # bucket | venn_2 | venn_3 | matrix | column
    submit_mode: str = "immediate_feedback"  # batch_submit | immediate_feedback | round_based
    allow_multi_category: bool = False
    show_category_hints: bool = False
    # NO zones, NO labels, NO diagram required

class DescriptionMatchingConfig(BaseModel):
    zones: list[Zone]
    descriptions: dict[str, str]  # {zone_label: functional_description}
    mode: str = "drag_description"  # click_zone | drag_description | multiple_choice
    show_connecting_lines: bool = True
    defer_evaluation: bool = False
    distractor_count: int = 0

class MemoryMatchConfig(BaseModel):
    pairs: list[MemoryPair]  # {id, front, back, front_type, back_type, explanation, category}
    grid_size: tuple[int, int] = (4, 3)
    flip_duration_ms: int = 600
    game_variant: str = "classic"  # classic | column_match | scatter | progressive | peek
    match_type: str = "term_to_definition"  # term_to_definition | image_to_label | concept_to_example
    show_explanation_on_match: bool = True
    # NO zones, NO labels — pairs are independent entities

class BranchingScenarioConfig(BaseModel):
    nodes: list[DecisionNode]  # {id, question, description, options[], is_end_node, end_message, node_type}
    start_node_id: str
    show_path_taken: bool = True
    allow_backtrack: bool = False
    show_consequences: bool = True
    narrative_structure: str = "branching"  # linear | branching | foldback
    # NO zones, NO labels — nodes are independent entities

class CompareContrastConfig(BaseModel):
    diagram_a: CompareDiagram  # {id, name, image_url, zones[]}
    diagram_b: CompareDiagram  # {id, name, image_url, zones[]}
    expected_categories: dict[str, str]  # {feature_name: "similar"|"different"|"unique_a"|"unique_b"}
    comparison_mode: str = "side_by_side"  # side_by_side | slider | overlay_toggle | venn
    highlight_matching: bool = True
    # TWO diagrams, TWO sets of zones
```

### 0.3 Game Rule Format (json-rules-engine compatible)

Each mechanic's scoring, feedback, and completion logic expressed as declarative rules:

```python
class GameRule(BaseModel):
    """A single evaluatable rule. Frontend uses json-rules-engine to execute."""
    name: str  # e.g. "correct_placement_scoring"
    conditions: dict  # json-rules-engine conditions: {"all": [...]} or {"any": [...]}
    event: GameEvent  # {type: str, params: dict}
    priority: int = 1  # higher = evaluated first

class GameEvent(BaseModel):
    type: str  # "award_points" | "show_feedback" | "complete_mechanic" | "transition_mode"
    params: dict  # {score: 10, feedback: "Correct! ...", next_mode: "..."}
```

**Per-mechanic rule templates** (what interaction_designer fills in):

| Mechanic | Scoring Rules | Feedback Rules | Completion Rules |
|---|---|---|---|
| drag_drop | correct_placement (+pts), incorrect_placement (-pts), hint_used (-pts) | per-zone feedback text, misconception targeting | all_zones_filled AND score >= threshold |
| click_to_identify | correct_click (+pts), wrong_click (-pts), explore_bonus | per-zone identification explanation | all_prompts_answered |
| trace_path | waypoint_visited (+pts), wrong_waypoint (-pts), backtrack_penalty | per-step flow explanation | all_waypoints_visited_in_order |
| sequencing | exact_position (+full), adjacent_swap (+partial), far_off (0) | ordering explanation, pair-specific hints | sequence_submitted AND score >= threshold |
| sorting_categories | correct_category (+pts), wrong_category (feedback) | category membership explanation | all_items_sorted |
| description_matching | correct_match (+pts), wrong_match (feedback) | description↔visual feature connection | all_descriptions_matched |
| memory_match | pair_found (+pts), attempt_tracked | pair explanation on match | all_pairs_found |
| branching_scenario | per_choice points (optimal/acceptable/suboptimal/harmful) | consequence explanation, reasoning | reached_end_node |
| compare_contrast | correct_categorization (+pts) | similarity/difference explanation | all_features_categorized |

### 0.4 Frontend Zod Schema (Mirror of Backend Pydantic)

Create `frontend/src/components/templates/InteractiveDiagramGame/schemas/gameSpecification.ts`:
- Zod schema that validates the GameSpecification JSON from the API
- Auto-generates TypeScript types
- Runtime validation before game initialization
- Replaces the current loose `InteractiveDiagramBlueprint` type

### 0.5 Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/agents/schemas/game_specification.py` | CREATE | Unified Pydantic GameSpecification model |
| `frontend/src/.../schemas/gameSpecification.ts` | CREATE | Zod mirror schema + TypeScript types |
| `frontend/src/.../types.ts` | MODIFY | Import from Zod-generated types instead of manual interfaces |

### 0.6 Verification
- Write a test that takes a sample GameSpecification JSON for each mechanic and validates it against both Pydantic and Zod schemas
- Verify each mechanic config shape matches what the existing frontend components consume

---

## Phase 1: Mechanic Contract Registry

**Goal**: Centralized source of truth for what each pipeline stage must produce per mechanic. Agents consult contracts instead of carrying hardcoded mechanic encyclopedias.

### 1.1 Contract Structure

Create `backend/app/config/mechanic_contracts.py`:

```python
@dataclass
class StageContract:
    guidance: str                          # Injected into agent prompt
    required_output_fields: list[str]      # Validated after generation
    dk_fields_needed: set[str]             # Which DK sub-fields to inject

@dataclass
class MechanicContract:
    needs_diagram: bool                    # Does this mechanic need an image?
    needs_zones: bool                      # Does this mechanic need zone detection?
    needs_labels: bool                     # Does this mechanic use label entities?
    entity_type: str                       # "zone_label" | "sequence_item" | "sorting_item" | "memory_pair" | "decision_node" | "compare_feature"
    game_designer: StageContract
    scene_architect: StageContract
    interaction_designer: StageContract
    asset_generator: StageContract
    frontend_config_key: str               # e.g., "sequenceConfig", "sortingConfig"
    frontend_error_if_missing: bool        # True = MechanicConfigError, False = graceful fallback
```

### 1.2 Complete Contract Table

| Mechanic | needs_diagram | needs_zones | needs_labels | entity_type | frontend_config_key |
|---|---|---|---|---|---|
| drag_drop | YES | YES | YES | zone_label | dragDropConfig |
| click_to_identify | YES | YES | NO | zone_label | clickToIdentifyConfig |
| trace_path | YES | YES | NO | zone_label | tracePathConfig |
| description_matching | YES | YES | NO | zone_label | descriptionMatchingConfig |
| sequencing | OPTIONAL | NO | NO | sequence_item | sequenceConfig |
| sorting_categories | OPTIONAL | NO | NO | sorting_item | sortingConfig |
| memory_match | OPTIONAL | NO | NO | memory_pair | memoryMatchConfig |
| branching_scenario | OPTIONAL | NO | NO | decision_node | branchingConfig |
| compare_contrast | YES (x2) | YES (x2) | NO | compare_feature | compareConfig |

**Key insight**: Only 4 of 9 mechanics (drag_drop, click_to_identify, trace_path, description_matching) need the full image→zones→labels pipeline. The other 5 need content generation, not image processing.

### 1.3 Helper Functions

```python
def get_stage_guidance(mechanic_types: set[str], stage: str) -> str
def get_required_dk_fields(mechanic_types: set[str]) -> set[str]
def get_required_output_fields(mechanic_types: set[str], stage: str) -> dict[str, list[str]]
def needs_image_pipeline(mechanic_types: set[str]) -> bool
def get_entity_types(mechanic_types: set[str]) -> set[str]
```

### 1.4 Files to Create/Modify

| File | Action |
|------|--------|
| `backend/app/config/mechanic_contracts.py` | CREATE |

### 1.5 Verification
- Unit test: every mechanic in MechanicRouter has a contract entry
- Unit test: every `frontend_config_key` maps to a real config type in `types.ts`
- Unit test: `needs_diagram=False` mechanics don't list `zones` in required_output_fields

---

## Phase 2: drag_drop Bias Eradication

**Goal**: Remove every instance where the pipeline defaults to or assumes drag_drop.

### 2.1 Catalog of All Instances

**Category A: Pydantic Schema Defaults** (remove default, make required)

| File | Line | Current | Fix |
|------|------|---------|-----|
| `schemas/scene_spec_v3.py` | MechanicConfig.type | `type: str = "drag_drop"` | `type: str` (required) |
| `schemas/interaction_spec_v3.py` | InteractionSpec.type | `type: str = "drag_drop"` | `type: str` (required) |
| `schemas/game_design_v3.py` | SceneMechanic.type | `type: str = "drag_drop"` | `type: str` (required) |
| `schemas/blueprint_schemas.py` | mechanic_type field | `default="drag_drop"` | remove default |
| `scene_stage1_structure.py` | recommended_mode | `default="drag_drop"` | remove default |

**Category B: Normalization Fallbacks** (return "" or raise, not drag_drop)

| File | Location | Current | Fix |
|------|----------|---------|-----|
| `design_interpreter.py` | `_normalize_mechanic_type()` line ~419 | Returns `"drag_drop"` for unknown | Return `""` + log warning |
| `game_planner.py` | `detect_mechanics_from_question()` line ~152 | Returns `[(DRAG_DROP, 0.5)]` for no match | Return `[]` (let game_designer decide) |
| `game_planner.py` | `_detect_hierarchical_content()` | Returns `recommended_mode: "drag_drop"` | Return `recommended_mode: ""` |
| `game_planner.py` | `_convert_game_design_to_plan()` | Defaults everything to drag_drop | Use actual mechanic from game_design |
| `interaction_designer.py` | Template default | `"drag_drop"` | Use actual mechanic from scene |
| `interaction_designer.py` | Scene mechanics default | `[{"type": "drag_drop"}]` | `[]` (require explicit) |
| `interaction_validator.py` | Suggestion text | `"Use 'drag_drop' as safe default"` | Remove suggestion |
| `diagram_type_classifier.py` | default_interaction_mode | Falls back to drag_drop | Falls back to "" |

**Category C: `.get("mechanic_type", "drag_drop")` Calls** (~25 in design_interpreter, ~8 in blueprint_assembler_tools, ~3 in asset_generator_tools)

All changed to `.get("mechanic_type", "")` or `.get("mechanic_type")` with explicit handling.

**Category D: Frontend Defaults**

| File | Location | Fix |
|------|----------|-----|
| `MechanicRouter.tsx` | default case | Log warning, show error instead of silently rendering drag_drop |
| `extractTaskConfig.ts` | Fallback logic | Don't default to drag_drop config |

### 2.2 Verification
- `grep -r "drag_drop" backend/app/agents/` should return ZERO results in schema defaults, normalizers, and fallbacks
- `grep -r '"drag_drop"' backend/app/agents/schemas/` should return zero default assignments
- Pipeline test with `question_text="Arrange the stages of mitosis in order"` should produce `mechanic_type="sequencing"` throughout, never falling back to drag_drop

---

## Phase 3: V4 Subgraph Architecture

**Goal**: Replace monolithic ReAct loops with internal LangGraph subgraphs. Each pipeline stage becomes a directed graph of deterministic + LLM nodes.

### 3.1 Why Not ReAct For Everything

Current ReAct pattern:
```
System prompt (3-5K) + Tool definitions (2-3K) + Task prompt (2-4K) + Tool history (grows each iteration)
= ~12K tokens per iteration × 3-6 iterations = 36-72K per agent
```

V4 subgraph pattern:
```
Each node gets ONLY what it needs:
- LLM node: focused prompt (1-2K) + relevant context (1-2K) = 2-4K per LLM call
- Deterministic node: 0 tokens (pure Python)
```

### 3.2 Game Designer Subgraph

**Current**: ReAct agent with 5 tools (analyze_pedagogy, check_capabilities, get_example_designs, validate_design, submit_game_design), 3-6 iterations.

**V4 Subgraph** (`backend/app/agents/v4/game_designer.py`):

```
Node 1: extract_pedagogical_context [DETERMINISTIC]
  Reads: state.pedagogical_context, state.domain_knowledge, state.question_text
  Writes: state._gd_pedagogy_summary (compact text, <500 tokens)
  Logic: Extract Bloom's level, key concepts, misconceptions from DK

Node 2: select_mechanics [LLM — structured output]
  Reads: state._gd_pedagogy_summary, mechanic_contracts (from registry)
  Writes: state._gd_mechanic_selections [{type, rationale, scene_count}]
  Prompt: "Given this pedagogical context, select 1-3 mechanics from the contract registry. Output JSON."
  Model: Fast (Haiku/Flash) — this is classification, not creative

Node 3: design_scenes [LLM — structured output]
  Reads: state._gd_mechanic_selections, state._gd_pedagogy_summary, state.domain_knowledge (scoped by contract dk_fields)
  Writes: state.game_specification.scenes[] (skeleton: scene_id, title, mechanic_type, mechanic_config seeds)
  Prompt: "Design {n} scenes for a {mechanics} game about {topic}. Output GameSpecification.scenes JSON."
  Model: Smart (Sonnet/Gemini Pro) — this is creative design

Node 4: validate_game_design [DETERMINISTIC]
  Reads: state.game_specification.scenes[], mechanic_contracts
  Writes: state._gd_validation_result {valid, issues[]}
  Logic: For each scene, check mechanic_config has required seed fields per contract

Node 5: repair_if_needed [CONDITIONAL → LLM]
  Condition: state._gd_validation_result.valid == False
  Reads: state.game_specification.scenes[], state._gd_validation_result.issues
  Writes: state.game_specification.scenes[] (repaired)
  Max 1 repair attempt, then fail with clear error
```

**Token estimate**: ~6K total (was ~15K in ReAct)

### 3.3 Scene Architect Subgraph

**Current**: ReAct agent with 5 tools, 3-6 iterations.

**V4 Subgraph** (`backend/app/agents/v4/scene_architect.py`):

```
Node 1: classify_scenes_by_asset_needs [DETERMINISTIC]
  Reads: state.game_specification.scenes[], mechanic_contracts
  Writes: state._sa_scene_groups {needs_image: [...], no_image: [...], needs_paired_images: [...]}
  Logic: Use contract.needs_diagram to classify

Node 2: generate_zone_layouts [LLM — per image-needing scene, PARALLEL]
  Reads: Per scene: mechanic_type, mechanic_config seeds, domain_knowledge (scoped)
  Writes: Per scene: state.game_specification.scenes[i].diagram.zones[], positions, hints
  Prompt: Scoped by mechanic contract guidance
  Model: Smart — spatial reasoning needed

Node 3: generate_mechanic_content [LLM — per non-image scene, PARALLEL]
  Reads: Per scene: mechanic_type, mechanic_config seeds, domain_knowledge (scoped)
  Writes: Per scene: state.game_specification.scenes[i].mechanic_config (full)
  Prompt: "Generate {mechanic_type} content. Output {MechanicConfig} JSON."
  Example: For sequencing → generate items[], correctOrder[]. For branching → generate nodes[], startNodeId.

Node 4: validate_scene_specs [DETERMINISTIC]
  Reads: state.game_specification.scenes[], mechanic_contracts
  Writes: state._sa_validation_result
  Logic: Check each scene's mechanic_config has all required_output_fields per contract

Node 5: repair_if_needed [CONDITIONAL → LLM]
  Same pattern as game_designer repair
```

**Key change**: Scenes that need images are separated from scenes that need content generation. No more forcing every scene through zone detection.

**Token estimate**: ~8K total (was ~18K in ReAct)

### 3.4 Interaction Designer Subgraph

**Current**: ReAct agent with 5 tools, 3-6 iterations. Loses 50% of output.

**V4 Subgraph** (`backend/app/agents/v4/interaction_designer.py`):

```
Node 1: load_rule_templates [DETERMINISTIC]
  Reads: state.game_specification.scenes[].mechanic_type, rule_templates (from registry)
  Writes: state._id_templates {mechanic_type: template_rules[]}
  Logic: Load json-rules-engine rule templates per active mechanic

Node 2: generate_scoring_rules [LLM — per scene, PARALLEL]
  Reads: Per scene: mechanic_config, domain_knowledge (scoped), rule template
  Writes: Per scene: state.game_specification.scenes[i].scoring_rules[]
  Prompt: "Fill in this scoring rule template with content-specific values. Output GameRule[] JSON."
  Template provides structure; LLM provides content-specific parameters + feedback text.

Node 3: generate_feedback_rules [LLM — per scene, PARALLEL]
  Reads: Per scene: mechanic_config, domain_knowledge (label_descriptions, term_definitions)
  Writes: Per scene: state.game_specification.scenes[i].feedback_rules[]
  Prompt: "Generate educational feedback for each possible student action."

Node 4: generate_completion_and_transitions [LLM — once for whole game]
  Reads: All scenes, mechanic types, scene order
  Writes: state.game_specification.scenes[i].completion_rules[], state.game_specification.scene_transitions[]
  Prompt: "Define completion criteria per scene and transitions between scenes."

Node 5: validate_rules [DETERMINISTIC]
  Reads: All generated rules
  Writes: state._id_validation_result
  Logic: Validate rule JSON is syntactically valid for json-rules-engine. Check all referenced facts exist.

Node 6: repair_if_needed [CONDITIONAL → LLM]
```

**Key change**: Rules are generated using templates (structure guaranteed) with LLM filling parameters (content-specific). No more prose feedback that gets lost.

**Token estimate**: ~8K total (was ~20K in ReAct)

### 3.5 Asset Generator Subgraph

**Current**: ReAct agent with 5 tools, most token-heavy.

**V4 Subgraph** (`backend/app/agents/v4/asset_generator.py`):

```
Node 1: plan_asset_requirements [DETERMINISTIC]
  Reads: state.game_specification.scenes[], mechanic_contracts
  Writes: state._ag_asset_plan [{scene_id, needs: "single_image"|"paired_images"|"icons_only"|"none", search_queries, style_hints}]
  Logic: Per-mechanic asset requirements from contract

Node 2: acquire_images [PARALLEL — per scene that needs images]
  Sub-nodes per scene:
    2a: search_image [TOOL — Serper API]
    2b: generate_if_search_fails [TOOL — Imagen API]
    2c: detect_zones [TOOL — SAM3/Gemini]
  Writes: state.game_specification.scenes[i].diagram {image_url, local_path, zones[].coordinates}

Node 3: acquire_paired_images [PARALLEL — for compare_contrast scenes]
  Two parallel image acquisitions (subject_a, subject_b)
  Zone detection on each separately
  Writes: state.game_specification.scenes[i].mechanic_config.diagram_a, diagram_b

Node 4: generate_supplementary_assets [PARALLEL — icons, card images, etc.]
  For sequencing: generate step icons if card_type includes images
  For memory_match: generate card face images if match_type is image_to_label
  For branching: generate scene-relevant background images per node

Node 5: validate_assets [DETERMINISTIC]
  Check every scene that needs_diagram has one
  Check zone coordinates are within image bounds
  Check paired images exist for compare_contrast
```

**Token estimate**: ~4K total (was ~15K in ReAct) — most work is tool calls, not LLM reasoning

### 3.6 Blueprint Assembler → ELIMINATED

No blueprint assembler. The GameSpecification IS the output. A simple deterministic function `to_frontend_json()` converts Pydantic → JSON for the API response.

```python
# In the final graph node (deterministic):
def finalize_output(state: AgentState) -> dict:
    """Convert GameSpecification to frontend-consumable JSON."""
    spec = state["game_specification"]
    # Deterministic conversion — no LLM, no data loss
    return spec.model_dump(exclude_none=True)
```

### 3.7 Subgraph Registration in graph.py

```python
# backend/app/agents/graph.py — V4 pipeline

def build_v4_pipeline() -> StateGraph:
    graph = StateGraph(AgentState)

    # Shared stages (unchanged)
    graph.add_node("input_enhancer", input_enhancer)
    graph.add_node("domain_knowledge_retriever", domain_knowledge_retriever)

    # V4 subgraph stages
    graph.add_node("game_designer_v4", game_designer_v4_subgraph)
    graph.add_node("scene_architect_v4", scene_architect_v4_subgraph)
    graph.add_node("interaction_designer_v4", interaction_designer_v4_subgraph)
    graph.add_node("asset_generator_v4", asset_generator_v4_subgraph)
    graph.add_node("finalize_output", finalize_output)

    # Linear flow — no blueprint assembler
    graph.add_edge("input_enhancer", "domain_knowledge_retriever")
    graph.add_edge("domain_knowledge_retriever", "game_designer_v4")
    graph.add_edge("game_designer_v4", "scene_architect_v4")
    graph.add_edge("scene_architect_v4", "interaction_designer_v4")
    graph.add_edge("interaction_designer_v4", "asset_generator_v4")
    graph.add_edge("asset_generator_v4", "finalize_output")
    graph.add_edge("finalize_output", END)

    return graph
```

### 3.8 Files to Create/Modify

| File | Action |
|------|--------|
| `backend/app/agents/v4/game_designer.py` | CREATE |
| `backend/app/agents/v4/scene_architect.py` | CREATE |
| `backend/app/agents/v4/interaction_designer.py` | CREATE |
| `backend/app/agents/v4/asset_generator.py` | CREATE |
| `backend/app/agents/v4/__init__.py` | CREATE |
| `backend/app/agents/graph.py` | MODIFY — add V4 pipeline builder |
| `backend/app/config/presets/` | MODIFY — add `v4` preset |

### 3.9 Verification
- Each subgraph stage independently testable: provide input state, verify output state fields
- Token counter on each LLM node call — verify total < 25K per full pipeline run
- Pipeline completes for all 9 mechanic types without falling back to drag_drop

---

## Phase 4: Incremental GameState

**Goal**: Each pipeline stage writes directly to a shared `GameSpecification` in `AgentState`. No separate schemas, no assembly step.

### 4.1 AgentState Changes

```python
# Add to AgentState TypedDict:
class AgentState(TypedDict):
    # ... existing fields ...

    # V4: Incremental game specification
    game_specification: Optional[GameSpecification]  # Built incrementally

    # V4: Per-stage internal state (prefixed with stage abbreviation)
    _gd_pedagogy_summary: str
    _gd_mechanic_selections: list[dict]
    _gd_validation_result: dict
    _sa_scene_groups: dict
    _sa_validation_result: dict
    _id_templates: dict
    _id_validation_result: dict
    _ag_asset_plan: list[dict]
```

### 4.2 Stage Writing Protocol

Each stage follows the same pattern:
1. Read `state["game_specification"]`
2. Validate it has what this stage needs (previous stage's output)
3. Write new fields to it
4. Run contract-based validation on what was just written
5. Write updated `game_specification` back to state

### 4.3 Contract-Based Checkpoints

After each stage, a deterministic validator checks:

```python
def validate_after_stage(spec: GameSpecification, stage: str, contracts: dict) -> tuple[bool, list[str]]:
    """Validate GameSpecification has all required fields for the completed stage."""
    issues = []
    for scene in spec.scenes:
        contract = contracts.get(scene.mechanic_type)
        if not contract:
            issues.append(f"Scene {scene.scene_id}: unknown mechanic {scene.mechanic_type}")
            continue
        stage_contract = getattr(contract, stage)
        for field_path in stage_contract.required_output_fields:
            if not has_field(scene, field_path):
                issues.append(f"Scene {scene.scene_id}: missing {field_path}")
    return (len(issues) == 0, issues)
```

### 4.4 Frontend API Compatibility

The `/api/status/{id}` endpoint currently returns a blueprint JSON. With V4:

```python
# backend/app/routes/generate.py
@router.get("/api/status/{process_id}")
async def get_status(process_id: str):
    state = get_pipeline_state(process_id)
    if state.get("status") == "complete":
        spec = state["game_specification"]
        # Convert to frontend-compatible format
        blueprint = spec.to_frontend_blueprint()
        return {"status": "complete", "blueprint": blueprint}
```

The `to_frontend_blueprint()` method maps GameSpecification fields to the current `InteractiveDiagramBlueprint` shape, ensuring backward compatibility with existing frontend components.

### 4.5 Verification
- After game_designer: `game_specification.scenes` populated with mechanic_types and config seeds
- After scene_architect: each scene's `mechanic_config` is complete
- After interaction_designer: each scene has `scoring_rules`, `feedback_rules`, `completion_rules`
- After asset_generator: each scene that needs_diagram has `diagram.image_url` and `diagram.zones`
- End-to-end: `to_frontend_blueprint()` output validates against frontend Zod schema

---

## Phase 5: Game Rule Engine (Frontend)

**Goal**: Frontend evaluates declarative JSON rules instead of hardcoded per-mechanic logic.

### 5.1 Install json-rules-engine

```bash
cd frontend && npm install json-rules-engine
```

### 5.2 Custom Operators Registry

Create `frontend/src/components/templates/InteractiveDiagramGame/rules/operatorRegistry.ts`:

```typescript
// Custom operators needed across mechanics
const operators = {
  // Sequencing
  isExactSequence: (actual: string[], expected: string[]) =>
    JSON.stringify(actual) === JSON.stringify(expected),
  correctPairCount: (actual: string[], expected: string[]) =>
    actual.filter((v, i) => v === expected[i]).length,

  // Sorting
  isInCategory: (item: {id: string, categoryId: string}, expected: {itemId: string, categoryId: string}) =>
    item.id === expected.itemId && item.categoryId === expected.categoryId,

  // Memory Match
  isPairMatch: (revealed: string[], pairs: {front: string, back: string}[]) =>
    pairs.some(p => revealed.includes(p.front) && revealed.includes(p.back)),

  // Trace Path
  isValidNextWaypoint: (clicked: string, expected: string) => clicked === expected,

  // General
  percentageAbove: (score: number, threshold: number) => (score / threshold) >= 1,
  lengthEquals: (arr: any[], expected: number) => arr.length === expected,
}
```

### 5.3 Rule Evaluator Hook

Create `frontend/src/components/templates/InteractiveDiagramGame/hooks/useRuleEvaluator.ts`:

```typescript
function useRuleEvaluator(rules: GameRule[], zustandState: GameState) {
  // Build fact provider from Zustand state
  // Initialize json-rules-engine with custom operators
  // On state change, evaluate rules and dispatch events
  // Events trigger Zustand actions (award_points, show_feedback, etc.)
}
```

### 5.4 Integration with Zustand Store

The Zustand store remains the source of truth for game state. json-rules-engine evaluates rules against Zustand state as "facts". Rule events trigger Zustand actions.

```
User action → Zustand state update → Rule evaluation → Events → Zustand action dispatch
```

### 5.5 Migration Strategy

Phase 5 runs in parallel with Phase 3. Initially, the frontend uses BOTH:
- Existing hardcoded logic (for backward compatibility with V3 blueprints)
- Rule evaluator (for V4 GameSpecification blueprints)

Detection: `if (blueprint.pipeline_version === "v4") useRuleEvaluator() else useExistingLogic()`

### 5.6 Per-Mechanic Rule Templates (Backend)

Create `backend/app/config/rule_templates/` with one template file per mechanic. These are the structural templates that interaction_designer_v4 fills with content-specific values.

Example `drag_drop_rules.json`:
```json
{
  "scoring": [
    {
      "name": "correct_placement",
      "conditions": {"all": [
        {"fact": "lastPlacement", "operator": "equal", "value": {"zone": "{{zone_id}}", "label": "{{label_id}}"}}
      ]},
      "event": {"type": "award_points", "params": {"score": "{{points}}", "feedback": "{{feedback_text}}"}}
    }
  ],
  "completion": [
    {
      "name": "all_placed",
      "conditions": {"all": [
        {"fact": "placedCount", "operator": "greaterThanInclusive", "value": "{{total_zones}}"}
      ]},
      "event": {"type": "complete_mechanic"}
    }
  ]
}
```

The LLM fills `{{placeholders}}` with content-specific values. Structure is guaranteed by template; content quality is the LLM's job.

### 5.7 Files to Create/Modify

| File | Action |
|------|--------|
| `frontend/.../rules/operatorRegistry.ts` | CREATE |
| `frontend/.../rules/ruleEvaluator.ts` | CREATE |
| `frontend/.../hooks/useRuleEvaluator.ts` | CREATE |
| `backend/app/config/rule_templates/*.json` | CREATE (one per mechanic) |
| `frontend/.../hooks/useInteractiveDiagramState.ts` | MODIFY — wire rule evaluator |

### 5.8 Verification
- Unit test: load each mechanic's rule template, fill with sample values, run through json-rules-engine, verify expected events fire
- Integration test: render each mechanic component, simulate user actions, verify scoring/feedback matches rule definitions
- Regression: V3 blueprints still work via existing logic path

---

## Phase 6: Custom Asset Tools/Workflows Per Mechanic

**Goal**: Each mechanic gets exactly the assets it needs, generated through mechanic-aware tools.

### 6.1 Asset Requirements by Mechanic

| Mechanic | Primary Asset | Secondary Assets | Generation Tool |
|---|---|---|---|
| drag_drop | Diagram image (1) | Zone overlays | search_diagram → detect_zones |
| click_to_identify | Diagram image (1) | Highlight regions | search_diagram → detect_zones |
| trace_path | Diagram with pathways (1) | Flow arrows | search_diagram (pathways required) → detect_zones |
| description_matching | Diagram image (1) | Description cards | search_diagram → detect_zones |
| sequencing | OPTIONAL step icons | Step illustrations | generate_step_icons (Imagen) |
| sorting_categories | OPTIONAL category images | Item illustrations | generate_category_images (Imagen) |
| memory_match | Card face images (optional) | Pair illustrations | generate_card_images (Imagen) |
| branching_scenario | Scene background images | Per-node illustrations | generate_scene_image (Imagen) |
| compare_contrast | TWO diagram images | Zone overlays per image | search_paired_images → detect_zones (×2) |

### 6.2 New Asset Tools

Create in `backend/app/tools/v4_asset_tools.py`:

```python
# Tool 1: search_paired_images (for compare_contrast)
async def search_paired_images(subject_a: str, subject_b: str, style_hints: str) -> dict:
    """Search for TWO separate diagram images."""

# Tool 2: generate_step_icons (for sequencing)
async def generate_step_icons(steps: list[dict], style: str) -> dict:
    """Generate small icon images for sequence steps."""

# Tool 3: generate_card_images (for memory_match)
async def generate_card_images(pairs: list[dict], style: str) -> dict:
    """Generate card face images for memory match pairs."""

# Tool 4: generate_scene_images (for branching_scenario)
async def generate_scene_images(nodes: list[dict], style: str) -> dict:
    """Generate background/context images per decision node."""
```

### 6.3 Parallel Asset Generation

The asset_generator_v4 subgraph runs image acquisitions in parallel per scene:

```python
# In asset_generator_v4 subgraph:
async def acquire_all_assets(state: AgentState) -> AgentState:
    plan = state["_ag_asset_plan"]
    tasks = []
    for item in plan:
        if item["needs"] == "single_image":
            tasks.append(acquire_single_image(item))
        elif item["needs"] == "paired_images":
            tasks.append(acquire_paired_images(item))
        elif item["needs"] == "icons_only":
            tasks.append(generate_icons(item))
        # "none" → skip
    results = await asyncio.gather(*tasks)
    # Write results back to game_specification
```

### 6.4 Files to Create/Modify

| File | Action |
|------|--------|
| `backend/app/tools/v4_asset_tools.py` | CREATE |
| `backend/app/agents/v4/asset_generator.py` | Uses these tools |

### 6.5 Verification
- Test compare_contrast: verify two different images acquired with separate zone sets
- Test sequencing: verify step icons generated (or gracefully skipped if generation fails)
- Test branching_scenario: verify per-node images generated
- Test drag_drop: verify single image + zone detection still works (regression)

---

## Phase 7: Hierarchical as Composable Mode

**Goal**: Convert `hierarchical` from a standalone InteractionMode to a composable wrapper.

### 7.1 Frontend Changes

```typescript
// Remove 'hierarchical' from InteractionMode type
type InteractionMode = 'drag_drop' | 'click_to_identify' | 'trace_path' |
  'description_matching' | 'compare_contrast' | 'sequencing' |
  'sorting_categories' | 'memory_match' | 'branching_scenario';

// Add hierarchical as a property on blueprint
interface InteractiveDiagramBlueprint {
  // ... existing fields ...
  hierarchical_mode?: {
    enabled: boolean;
    zone_groups: ZoneGroup[];
  }
}

// MechanicRouter.tsx — wrap any mechanic with hierarchy
function MechanicRouter({ mode, blueprint, ... }) {
  const mechanicContent = renderMechanic(mode, blueprint, ...);

  if (blueprint.hierarchical_mode?.enabled) {
    return <HierarchicalWrapper zoneGroups={blueprint.hierarchical_mode.zone_groups}>
      {mechanicContent}
    </HierarchicalWrapper>;
  }
  return mechanicContent;
}
```

### 7.2 Backend Changes

- `game_designer_v4`: outputs `hierarchical_mode: {enabled: true, zone_groups: [...]}` as a game-level property, NOT as a mechanic_type
- `scene_architect_v4`: if hierarchical_mode enabled, generates zone_groups with parent-child relationships
- Contract: hierarchical is NOT in MECHANIC_CONTRACTS — it's an orthogonal modifier

### 7.3 Extract HierarchicalWrapper HOC

From existing `HierarchyController` in `frontend/src/components/templates/InteractiveDiagramGame/interactions/`:
- Extract zone visibility management (expand/collapse)
- Extract zoom-to-group animation
- Keep temporal constraint evaluation (already generic via `updateVisibleZones`)
- Remove DndContext ownership (delegated to underlying mechanic)

### 7.4 Files to Modify

| File | Action |
|------|--------|
| `frontend/src/.../types.ts` | MODIFY — remove 'hierarchical' from InteractionMode, add hierarchical_mode property |
| `frontend/src/.../MechanicRouter.tsx` | MODIFY — remove hierarchical case, add wrapper logic |
| `frontend/src/.../interactions/HierarchyController.tsx` | REFACTOR → HierarchicalWrapper.tsx |
| `backend/app/agents/schemas/game_specification.py` | hierarchical_mode on GameSpecification |

### 7.5 Verification
- Test: drag_drop + hierarchical_mode=true → zones reveal progressively
- Test: sequencing + hierarchical_mode=true → sequence items appear in layers
- Test: any mechanic + hierarchical_mode=false → no hierarchy behavior
- Regression: existing hierarchical games still render correctly

---

## Phase 8: Token Optimization

**Goal**: Reduce pipeline token usage from ~54K to ~22K.

### 8.1 Inherent Savings from V4 Architecture

The subgraph architecture provides most savings automatically:

| Technique | Savings | How V4 Achieves It |
|---|---|---|
| No ReAct observation replay | ~10K | Subgraph nodes don't accumulate tool history |
| State projection (per-node) | ~9K | Each node reads only its needed fields |
| No tool schema overhead | ~5K | Deterministic nodes have no tool definitions |
| Scoped mechanic guidance | ~4K | Contract-based, only active mechanics |
| Scoped DK injection | ~3K | Contract dk_fields, only needed sub-fields |
| **Total inherent** | **~31K** | **54K → ~23K** |

### 8.2 Additional Optimizations

**Prompt caching** (for the LLM nodes that remain):
- Structure system prompts as stable prefixes
- Place cache breakpoints after system prompt and after context

**Context deduplication**:
- Remove v3_context.py contextvars injection (replaced by direct state access in subgraph)
- Each LLM node builds its own focused prompt from state — no redundant injection

**Model routing**:
- Node 2 (select_mechanics) in game_designer → Haiku/Flash (classification task)
- Validation/repair nodes → Haiku/Flash
- Creative design nodes → Sonnet/Gemini Pro

### 8.3 Verification
- Instrument token counting on every LLM call in the pipeline
- Target: total input tokens < 25K per full pipeline run
- Target: total cost < $0.05 per pipeline run (at current Sonnet pricing)

---

## Implementation Order

Phases have dependencies. Recommended execution order:

```
Phase 0 (Game Spec DSL)          ← Foundation, everything depends on this
  ↓
Phase 1 (Contracts)              ← Needed by all V4 agents
  ↓
Phase 2 (Bias Removal)           ← Can be done in parallel with Phase 1
  ↓
Phase 3 (V4 Subgraphs)          ← Core architecture change
  ↓
Phase 4 (Incremental GameState)  ← Uses Phase 3 subgraphs + Phase 0 schema
  ↓
Phase 5 (Rule Engine)            ← Can start in parallel with Phase 3
  ↓
Phase 6 (Asset Tools)            ← Plugs into Phase 3 asset_generator subgraph
  ↓
Phase 7 (Hierarchical Mode)      ← Independent, can be done anytime after Phase 0
  ↓
Phase 8 (Token Optimization)     ← Mostly inherent from Phase 3, polish at end
```

**Parallelizable**: Phase 1 + Phase 2. Phase 5 + Phase 6 + Phase 7.

---

## End-to-End Verification Plan

After all phases complete, verify with these test cases:

### Test 1: drag_drop (regression)
```bash
curl -X POST http://localhost:8000/api/generate \
  -d '{"question_text": "Label the main parts of a flower", "pipeline_preset": "v4"}'
```
Verify: V4 pipeline, single image, zones detected, drag_drop config, scoring rules, playable game.

### Test 2: sequencing (non-label mechanic)
```bash
curl -X POST http://localhost:8000/api/generate \
  -d '{"question_text": "Arrange the stages of mitosis in order", "pipeline_preset": "v4"}'
```
Verify: No diagram image generated (optional icons only), sequenceConfig populated, correct_order matches biology, scoring rules evaluate sequence correctness. **No drag_drop fallback anywhere in the pipeline.**

### Test 3: branching_scenario (no-image mechanic)
```bash
curl -X POST http://localhost:8000/api/generate \
  -d '{"question_text": "Make clinical decisions for a patient presenting with chest pain", "pipeline_preset": "v4"}'
```
Verify: Decision nodes generated, branching tree navigable, consequence feedback per choice, scoring by decision quality.

### Test 4: compare_contrast (dual-image)
```bash
curl -X POST http://localhost:8000/api/generate \
  -d '{"question_text": "Compare and contrast plant cells and animal cells", "pipeline_preset": "v4"}'
```
Verify: TWO different images acquired, separate zone sets, compareConfig.diagramA and diagramB populated, expected_categories generated.

### Test 5: multi-mechanic multi-scene
```bash
curl -X POST http://localhost:8000/api/generate \
  -d '{"question_text": "Teach the structure and function of the human heart including blood flow path", "pipeline_preset": "v4"}'
```
Verify: Multiple scenes generated (e.g., scene 1: drag_drop for structure labeling, scene 2: trace_path for blood flow), scene transitions defined, mode transitions work.

### Test 6: hierarchical mode
```bash
curl -X POST http://localhost:8000/api/generate \
  -d '{"question_text": "Explore the hierarchical organization of the nervous system from brain regions to individual neurons", "pipeline_preset": "v4"}'
```
Verify: hierarchical_mode.enabled = true, zone_groups with parent-child relationships, progressive reveal works, underlying mechanic (drag_drop or click_to_identify) renders correctly within hierarchy.

### Token Budget Verification
For each test, log total input tokens. All should be < 25K. Compare against V3 baseline (~54K).

---

## Key Files Summary

### New Files (CREATE)
| File | Phase |
|------|-------|
| `backend/app/agents/schemas/game_specification.py` | 0 |
| `backend/app/config/mechanic_contracts.py` | 1 |
| `backend/app/agents/v4/__init__.py` | 3 |
| `backend/app/agents/v4/game_designer.py` | 3 |
| `backend/app/agents/v4/scene_architect.py` | 3 |
| `backend/app/agents/v4/interaction_designer.py` | 3 |
| `backend/app/agents/v4/asset_generator.py` | 3 |
| `backend/app/config/rule_templates/*.json` | 5 |
| `backend/app/tools/v4_asset_tools.py` | 6 |
| `frontend/src/.../schemas/gameSpecification.ts` | 0 |
| `frontend/src/.../rules/operatorRegistry.ts` | 5 |
| `frontend/src/.../rules/ruleEvaluator.ts` | 5 |
| `frontend/src/.../hooks/useRuleEvaluator.ts` | 5 |

### Modified Files
| File | Phases |
|------|--------|
| `backend/app/agents/graph.py` | 3 |
| `backend/app/agents/state.py` | 4 |
| `backend/app/routes/generate.py` | 4 |
| `frontend/src/.../types.ts` | 0, 7 |
| `frontend/src/.../MechanicRouter.tsx` | 7 |
| `frontend/src/.../hooks/useInteractiveDiagramState.ts` | 5 |
| `frontend/src/.../interactions/HierarchyController.tsx` | 7 |
| `backend/app/agents/schemas/*.py` (multiple) | 2 |
| `backend/app/agents/design_interpreter.py` | 2 |
| `backend/app/agents/game_planner.py` | 2 |
| `backend/app/agents/interaction_designer.py` | 2 |

### Files That Can Be Deprecated (after V4 is stable)
| File | Reason |
|------|--------|
| `backend/app/agents/blueprint_assembler_v3.py` | Replaced by incremental GameState |
| `backend/app/tools/blueprint_assembler_tools.py` | No longer needed |
| `backend/app/agents/game_designer_v3.py` | Replaced by v4/game_designer.py |
| `backend/app/agents/scene_architect_v3.py` | Replaced by v4/scene_architect.py |
| `backend/app/agents/interaction_designer_v3.py` | Replaced by v4/interaction_designer.py |
| `backend/app/agents/asset_generator_v3.py` | Replaced by v4/asset_generator.py |
| `backend/app/tools/v3_context.py` | Replaced by direct state access |
