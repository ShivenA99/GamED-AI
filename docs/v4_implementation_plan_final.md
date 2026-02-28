# V4 Pipeline — Final Implementation Plan

**Date**: 2026-02-14
**Status**: FINAL — ready for implementation
**Scope**: Complete V4 pipeline, end-to-end, no reactive agents (add later)
**Approach**: Frontend contract first → deterministic pipeline → LLM only where creative

---

## Design Decisions (Locked)

1. **Hierarchical is a MODE on drag_drop**, not a standalone mechanic → 9 mechanics total
2. **No ReAct agents** — every LLM call is a single structured call + deterministic validator + retry loop
3. **Blueprint assembler is 100% deterministic** — pure Python, no LLM
4. **Map-Reduce via LangGraph Send API** for per-scene content + per-scene assets
5. **Cross-model validation** deferred — add critic agent later
6. **GameSpecification** = single Pydantic model = the frontend contract
7. **Per-phase state isolation** — each sub-graph has its own small TypedDict, not the 160-field monolith
8. **Mechanic contracts** drive prompt injection — no more hardcoded mechanic encyclopedias

---

## File Structure

```
backend/app/v4/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── game_specification.py      # THE contract (GameSpecification + all sub-models)
│   ├── game_plan.py               # GamePlan, ScenePlan, MechanicPlan, ContentBrief
│   ├── mechanic_configs.py        # Per-mechanic config Pydantic models (9 mechanics)
│   ├── asset_manifest.py          # AssetManifest, DiagramAssetNeed, ItemImageNeed
│   └── validation.py              # ValidationResult, ValidationIssue
├── state/
│   ├── __init__.py
│   ├── main_state.py              # V4MainState (thin orchestrator state)
│   ├── phase0_state.py            # ContextState (question, dk, pedagogical_context)
│   ├── phase1_state.py            # DesignState (game_plan, validation, retry_count)
│   ├── phase2_state.py            # ContentState (per-scene mechanic contents)
│   ├── phase3_state.py            # AssetState (per-scene assets, manifest)
│   └── phase4_state.py            # AssemblyState (blueprint, warnings)
├── contracts/
│   ├── __init__.py
│   ├── mechanic_contracts.py      # MechanicContract registry (9 entries)
│   └── capability_spec.py         # JSON capability menu injected into game_designer prompt
├── graph/
│   ├── __init__.py
│   ├── main_graph.py              # create_v4_graph() — the top-level orchestrator
│   ├── phase0_graph.py            # Context gathering sub-graph
│   ├── phase1_graph.py            # Game design sub-graph (Quality Gate pattern)
│   ├── phase2_graph.py            # Content build sub-graph (Map-Reduce per scene)
│   ├── phase3_graph.py            # Asset pipeline sub-graph (Map-Reduce per scene)
│   └── phase4_graph.py            # Assembly sub-graph (deterministic)
├── agents/
│   ├── __init__.py
│   ├── input_analyzer.py          # Phase 0: single structured LLM call
│   ├── dk_retriever.py            # Phase 0: web search (reuse existing, slim prompt)
│   ├── game_designer.py           # Phase 1: single structured LLM call → GamePlan
│   ├── content_generator.py       # Phase 2: per-mechanic content LLM call
│   ├── interaction_designer.py    # Phase 2: scoring + feedback + transitions LLM call
│   └── asset_dispatcher.py        # Phase 3: executes pre-built tool chains
├── validators/
│   ├── __init__.py
│   ├── game_plan_validator.py     # Phase 1: deterministic GamePlan checks
│   ├── content_validator.py       # Phase 2: per-mechanic content checks
│   ├── interaction_validator.py   # Phase 2: scoring + transition checks
│   ├── asset_validator.py         # Phase 3: zone matching + completeness
│   └── blueprint_validator.py     # Phase 4: final blueprint checks
├── helpers/
│   ├── __init__.py
│   ├── scene_context_builder.py   # Deterministic: builds shared scene context
│   ├── asset_orchestrator.py      # Deterministic: builds AssetManifest from plan
│   ├── blueprint_assembler.py     # Deterministic: plan + content + assets → blueprint
│   ├── zone_matcher.py            # Deterministic: detected zones ↔ expected labels
│   └── graph_builder.py           # Deterministic: design → game state graph
└── prompts/
    ├── game_designer.py           # Prompt template for game designer
    ├── content_generator.py       # Per-mechanic prompt templates
    └── interaction_designer.py    # Scoring/feedback/transition prompt
```

Frontend changes:
```
frontend/src/components/templates/InteractiveDiagramGame/
├── schemas/
│   └── gameSpecification.ts       # Zod mirror of GameSpecification (runtime validation)
└── (existing components — NO changes needed if blueprint shape matches)
```

---

## Implementation Phases

### Phase 1: Schemas & Contracts (Foundation)
**Files**: `schemas/`, `contracts/`, `state/`
**Depends on**: Nothing
**Effort**: ~800 lines Python + ~200 lines TypeScript

#### 1.1 GameSpecification schema (`schemas/game_specification.py`)
The single source of truth. Every field maps 1:1 to what the frontend renders.

```python
class GameSpecification(BaseModel):
    title: str
    subject: str
    question_text: str
    learning_objectives: list[str]
    difficulty: Literal["beginner", "intermediate", "advanced"]
    theme: Optional[ThemeConfig] = None
    scenes: list[SceneSpec]                    # 1-6 scenes
    scene_transitions: list[SceneTransition] = []
    hierarchical_config: Optional[HierarchicalConfig] = None  # MODE, not mechanic
    timed_config: Optional[TimedConfig] = None                # MODE, not mechanic
    total_max_score: int
    pipeline_version: str = "v4"
```

#### 1.2 Per-mechanic config models (`schemas/mechanic_configs.py`)
9 Pydantic models matching frontend types.ts exactly:
- `DragDropMechanicConfig`
- `ClickToIdentifyMechanicConfig`
- `TracePathMechanicConfig`
- `SequencingMechanicConfig`
- `SortingCategoriesMechanicConfig`
- `MemoryMatchMechanicConfig`
- `BranchingScenarioMechanicConfig`
- `CompareContrastMechanicConfig`
- `DescriptionMatchingMechanicConfig`

Each encapsulates ALL data that mechanic needs — zones, items, nodes, pairs, etc.

#### 1.3 GamePlan schema (`schemas/game_plan.py`)
What the game_designer LLM outputs. Intermediate — not the final contract.

```python
class GamePlan(BaseModel):
    title: str
    subject: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_duration_minutes: int = Field(ge=1, le=30)
    narrative_intro: str
    completion_message: str
    scenes: list[ScenePlan] = Field(min_length=1, max_length=6)
    all_zone_labels: list[str]
    distractor_labels: list[str] = []
    label_hierarchy: Optional[dict[str, list[str]]] = None  # parent → children
    total_max_score: int

class ScenePlan(BaseModel):
    scene_id: str
    scene_number: int
    title: str
    learning_goal: str
    zone_labels: list[str]
    needs_diagram: bool
    image_spec: Optional[ImageSpec] = None
    mechanics: list[MechanicPlan] = Field(min_length=1)
    mechanic_connections: list[MechanicConnection] = []
    starting_mechanic_id: str
    scene_max_score: int

class MechanicPlan(BaseModel):
    mechanic_id: str
    mechanic_type: str  # NO default — required
    zone_labels_used: list[str] = []
    instruction_text: str
    content_brief: ContentBrief
    expected_item_count: int
    points_per_item: int = 10
    max_score: int
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None
    is_terminal: bool = False
```

#### 1.4 AssetManifest schema (`schemas/asset_manifest.py`)
Deterministically derived from GamePlan + content.

#### 1.5 Per-phase state TypedDicts (`state/`)
Each ~10-20 fields. No 160-field monolith.

#### 1.6 Mechanic contracts (`contracts/mechanic_contracts.py`)
9 entries. Each specifies: needs_diagram, needs_zones, needs_labels, entity_type, per-stage guidance, required_output_fields, frontend_config_key.

#### 1.7 Capability spec (`contracts/capability_spec.py`)
JSON menu injected into game_designer prompt. Lists all 9 mechanics with description, needs_diagram, content_needs, best_for, scoring pattern, connection patterns, scene rules.

#### 1.8 Frontend Zod schema (`schemas/gameSpecification.ts`)
Mirror of GameSpecification. Runtime validation before game init.

---

### Phase 2: Deterministic Helpers (No LLM)
**Files**: `helpers/`
**Depends on**: Phase 1 (schemas)
**Effort**: ~600 lines Python

#### 2.1 `scene_context_builder.py`
Builds shared context for all mechanics in a scene:
- Extracts relevant DK fields per mechanic type (via contracts)
- Collects zone labels used by all mechanics in scene
- Notes which other mechanics exist (for cross-mechanic awareness)
- Outputs `SceneContext` dict for injection into content_generator prompts

#### 2.2 `asset_orchestrator.py`
Deterministically builds `AssetManifest` from `GamePlan` + mechanic contents:
- Diagram needs → `DiagramAssetNeed` (search query, expected labels, style)
- Compare contrast → dual `DiagramAssetNeed` (parallel)
- Item images → `ItemImageNeed` per item (sequencing, sorting, memory with images)
- Node illustrations → `NodeImageNeed` per branching node (optional)
- Color palettes → `ColorPaletteNeed` for sorting/compare categories

#### 2.3 `blueprint_assembler.py`
Pure Python transform: `GamePlan + SceneContents + SceneAssets → GameSpecification`
- Zone ID generation: `zone_{scene_number}_{index}`
- Label ID generation: `label_{scene_number}_{index}`
- correctZoneId matching via zone_matcher
- Mode transitions from mechanic_connections
- Score rollup: per-mechanic → per-scene → total
- Hierarchical mode: zoneGroups from label_hierarchy
- Per-mechanic config population from content

#### 2.4 `zone_matcher.py`
Matches detected zones (from vision model) to expected labels:
- Exact match → substring match → fuzzy match
- Reports match_quality score
- Returns matched zone list with IDs

#### 2.5 `graph_builder.py`
Converts GamePlan into validated game state graph:
- Scene graph (DAG with transitions)
- Per-scene mechanic graph (DAG with connections)
- Branching decision tree validation (connectivity, reachability, end nodes)
- Path graph validation (waypoint zone references)
- Uses FOL rules from `v4_formal_graph_rules.html`

---

### Phase 3: Validators (No LLM)
**Files**: `validators/`
**Depends on**: Phase 1 (schemas)
**Effort**: ~500 lines Python

#### 3.1 `game_plan_validator.py`
Checks GamePlan after game_designer LLM call:
- Scene number sequentiality
- Mechanic graph connectivity (reachable from starting_mechanic_id)
- Terminal node existence per scene
- Zone label referential integrity
- Diagram requirement consistency (visual mechanics → needs_diagram)
- Score arithmetic (mechanic sum = scene sum = total)
- Content brief completeness per mechanic type
- Timed wrapper validity
- Hierarchical parent validity
- Compare contrast dual-subject requirement

Returns `ValidationResult` with specific per-issue feedback for retry.

#### 3.2 `content_validator.py`
Per-mechanic content validation (9 validator functions):
- sequencing: items ≥ 3, correctOrder IDs match items, order_index present
- sorting: categories ≥ 2, items reference valid category IDs
- memory_match: pairs ≥ 3, front+back non-empty, unique IDs
- branching: startNodeId valid, end node exists, graph connected, no orphans
- compare: both subjects present, zone labels present, expected_categories non-empty
- trace_path: waypoints reference valid zone labels, ≥ 2 waypoints
- click_to_identify: prompts present, targetZoneId references valid zone labels
- drag_drop: labels present, correctZoneId will resolve
- description_matching: zones have descriptions

#### 3.3 `interaction_validator.py`
- Score arithmetic per mechanic
- Transition trigger-mechanic compatibility (from formal graph rules)
- No duplicate transitions
- All mechanics reachable from starting mode

#### 3.4 `asset_validator.py`
- Zone detection coverage (detected ≥ 80% of expected labels)
- Coordinate bounds (0-100%)
- Image URL accessibility
- Manifest completeness (all required assets generated)

#### 3.5 `blueprint_validator.py`
Final gate — runs all formal graph rules:
- templateType correct
- Zone/label ID uniqueness
- correctZoneId referential integrity
- Per-mechanic config presence for active mechanics
- Branching graph connectivity
- Hierarchy tree no cycles
- Score consistency
- Coordinate validity

---

### Phase 4: LLM Agents (3 agents, single-call each)
**Files**: `agents/`
**Depends on**: Phase 1 (schemas), Phase 3 (validators)
**Effort**: ~400 lines Python + prompts

#### 4.1 `input_analyzer.py`
- Model: gemini-2.5-flash
- Input: question_text
- Output: `PedagogicalContext` (content_structure, has_labels, has_sequence, has_comparison, has_hierarchy, visual_needs, bloom_level, difficulty_estimate)
- Single structured call, no retry

#### 4.2 `dk_retriever.py`
- Reuse existing dk_retriever logic (web search via serper)
- Slim the prompt — only inject relevant DK fields per mechanic type (via contracts)
- Output: `DomainKnowledge` with canonical_labels, sequence_flow, comparison_data, etc.
- Internal retry (search fails → alternate queries)

#### 4.3 `game_designer.py`
- Model: gemini-2.5-pro (or claude-sonnet-4-5)
- Input: question + PedagogicalContext + DomainKnowledge + CapabilitySpec + examples
- Output: `GamePlan` (Pydantic structured output)
- Prompt includes: capability spec (the menu), 2-3 example game plans, explicit "mechanic_type is REQUIRED, no defaults"
- Retry: validator feedback → fresh LLM call (max 2 retries)

#### 4.4 `content_generator.py`
- Model: gemini-2.5-pro (complex mechanics) or gemini-2.5-flash (simple)
- Input: ContentBrief + SceneContext + DomainKnowledge subset
- Output: `MechanicContent` (per-mechanic Pydantic model)
- Per-mechanic prompt templates (from `prompts/content_generator.py`)
- Retry: content_validator feedback → fresh call (max 2 retries)
- **Runs per-mechanic via Send API** (parallel within scene)

#### 4.5 `interaction_designer.py`
- Model: gemini-2.5-flash
- Input: all mechanic contents for a scene + pedagogical context
- Output: per-mechanic `ScoringRules`, `FeedbackRules`, `CompletionRules`, `ModeTransitions`
- Single call per scene
- Retry: interaction_validator feedback → fresh call (max 1 retry)

#### 4.6 `asset_dispatcher.py`
- Executes pre-built tool chains (not LLM decisions):
  - `diagram_with_zones`: serper → gemini_regen → gemini_flash_bbox → SAM3 → zone_matcher
  - `simple_image`: serper → gemini_regen → save
  - `color_palette`: deterministic HSL rotation
- Input: `AssetManifest` entry
- Output: asset URL + zone coordinates (if diagram)
- Retry: zone detection fails → retry with specific labels as guidance

---

### Phase 5: LangGraph Wiring
**Files**: `graph/`
**Depends on**: Phase 1-4
**Effort**: ~400 lines Python

#### 5.1 `main_graph.py` — `create_v4_graph()`
Top-level orchestrator. 5 phase nodes, each a compiled sub-graph.

```python
def create_v4_graph():
    builder = StateGraph(V4MainState)

    # Phase nodes (each is a compiled sub-graph)
    builder.add_node("phase0_context", create_phase0_graph())
    builder.add_node("phase1_design", create_phase1_graph())
    builder.add_node("phase2_content", create_phase2_graph())
    builder.add_node("phase3_assets", create_phase3_graph())
    builder.add_node("phase4_assembly", create_phase4_graph())

    # Linear flow
    builder.add_edge(START, "phase0_context")
    builder.add_edge("phase0_context", "phase1_design")
    builder.add_edge("phase1_design", "phase2_content")
    builder.add_edge("phase2_content", "phase3_assets")
    builder.add_edge("phase3_assets", "phase4_assembly")
    builder.add_edge("phase4_assembly", END)

    return builder.compile()
```

#### 5.2 `phase0_graph.py` — Context Gathering
Two parallel nodes: input_analyzer + dk_retriever

#### 5.3 `phase1_graph.py` — Quality Gate Pattern
```
context_gatherer → game_designer (LLM) → game_plan_validator → [retry or pass]
```
Max 2 retries. Fresh LLM call each time with validator feedback.

#### 5.4 `phase2_graph.py` — Map-Reduce per Scene
```
FOR EACH scene (via Send API):
    scene_context_builder (deterministic)
    → FOR EACH mechanic (via Send API):
        content_generator (LLM) → content_validator → [retry or pass]
    → scene_content_merger (deterministic)
    → interaction_designer (LLM) → interaction_validator → [retry or pass]
```

#### 5.5 `phase3_graph.py` — Map-Reduce per Scene
```
asset_orchestrator (deterministic — builds manifest)
→ FOR EACH scene (via Send API):
    FOR EACH asset_need (parallel):
        asset_dispatcher (tool chain)
    → asset_validator → [retry specific assets or pass]
```

#### 5.6 `phase4_graph.py` — Deterministic Assembly
```
blueprint_assembler (deterministic) → blueprint_validator → emit warnings
```
No retry — assembler is deterministic. Validator issues = upstream problems.

#### 5.7 Checkpointing (`main_graph.py`)

LangGraph SQLite checkpointer at phase boundaries. Enables resume-from-checkpoint on failure.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

def create_v4_graph(checkpoint_db: str = "v4_checkpoints.db"):
    memory = SqliteSaver.from_conn_string(checkpoint_db)
    builder = StateGraph(V4MainState)
    # ... (phase nodes as above)
    return builder.compile(checkpointer=memory)
```

**What gets checkpointed** (automatic — LangGraph snapshots full state after each node):

| Phase Boundary | State Snapshot Contains | Resume Benefit |
|----------------|------------------------|----------------|
| After Phase 0 | `pedagogical_context`, `domain_knowledge` | Skip 15-30s DK retrieval |
| After Phase 1 | + `game_plan` (validated) | Skip design LLM call ($0.10) |
| After Phase 2 | + per-scene `mechanic_contents`, `scoring_rules`, `transitions` | Skip 2-4 content LLM calls ($0.15) |
| After Phase 3 | + `asset_manifest`, per-scene `assets`, `zone_coordinates` | Skip image gen/detection (60-120s) |
| After Phase 4 | + `game_specification` (final blueprint) | Full result cached |

**Resume-from-checkpoint on failure:**
```python
# In routes/generate.py — resume a failed run
config = {"configurable": {"thread_id": run_id}}
# LangGraph automatically resumes from last successful checkpoint
result = await graph.ainvoke(None, config)
```

**Checkpoint cleanup policy:**
- Retain checkpoints for 24 hours (configurable)
- Delete on successful pipeline completion (final blueprint saved to DB)
- Expose `GET /api/v4/runs/{run_id}/checkpoints` for observability

**Cost savings:** A Phase 3 failure (asset gen) resumes from Phase 2 checkpoint → saves ~$0.25 and ~90s per retry.

---

### Phase 6: Integration & Registration
**Files**: `graph.py`, `routes/generate.py`, instrumentation, frontend
**Depends on**: Phase 5
**Effort**: ~200 lines

#### 6.1 Register V4 preset
- Add `"v4"` to preset selection in `graph.py`
- Route to `create_v4_graph()` when `pipeline_preset="v4"`

#### 6.2 Route integration
- `routes/generate.py`: accept `pipeline_preset: "v4"`, invoke V4 graph
- State mapping: V4MainState → response format (same as V3)

#### 6.3 Instrumentation
- Add V4 agent metadata to `instrumentation.py`
- Input/output keys for each V4 agent
- Frontend PipelineView metadata for V4 topology

#### 6.4 Frontend
- Add Zod schema validation in game init path
- No component changes needed if blueprint shape matches InteractiveDiagramBlueprint
- If GameSpecification differs from current blueprint shape, add a `v4ToBlueprint()` adapter

---

## Dependency Graph

```
Phase 1 (Schemas & Contracts)
    ↓
Phase 2 (Helpers) ←── Phase 3 (Validators)
    ↓                      ↓
Phase 4 (LLM Agents) ─────┘
    ↓
Phase 5 (Graph Wiring)
    ↓
Phase 6 (Integration)
```

Phases 2 and 3 can run in parallel (both depend only on Phase 1).
Phase 4 depends on both 2 and 3.

---

## Model Assignment

| Agent | Model | Rationale |
|-------|-------|-----------|
| input_analyzer | gemini-2.5-flash | Simple classification, cheap |
| dk_retriever | gemini-2.5-flash | Tool-calling for search |
| game_designer | gemini-2.5-pro | Creative design, instruction following |
| content_generator (complex) | gemini-2.5-pro | sequencing, branching, compare need pro |
| content_generator (simple) | gemini-2.5-flash | drag_drop labels, description_matching |
| interaction_designer | gemini-2.5-flash | Structured scoring/feedback |
| asset_dispatcher | gemini-2.5-flash | Image search + zone detection |

Total estimated cost per run: ~$0.40-0.60 (down from ~$1.50 in V3)
Total estimated tokens: ~80K in, ~30K out (down from ~54K out in V3)

---

## Token Optimization

| Optimization | Savings | How |
|-------------|---------|-----|
| No ReAct replay | ~15K/run | Single structured calls, no tool result replay |
| Per-mechanic DK injection | ~8K/run | Only inject DK fields needed per mechanic type |
| No mechanic encyclopedia | ~5K/run | Capability spec is ~2K vs encyclopedias at ~7K |
| Per-phase state isolation | ~10K/run | Each agent sees 10-20 fields, not 160 |
| No state serialization in prompts | ~8K/run | Pass only relevant fields, not full state |
| **Total** | **~46K/run** | **54K → ~8K output tokens** |

---

## Formal Graph Rules Integration

The FOL rules from `docs/v4_formal_graph_rules.html` are the single source of truth for what makes a game valid. Here is exactly how they are codified and enforced at each validation stage.

### Rule Codification Strategy

Each FOL rule becomes a Python function that returns `(passed: bool, message: str)`. Rules are grouped by graph layer and registered in a `RULE_REGISTRY` dict so validators can run all rules for their layer.

```python
# validators/rules.py — shared rule registry
from typing import Callable, NamedTuple

class RuleResult(NamedTuple):
    passed: bool
    rule_id: str
    message: str

Rule = Callable[..., RuleResult]
RULE_REGISTRY: dict[str, list[Rule]] = {
    "scene_graph": [],       # Layer 1: R1.1-R1.7
    "mechanic_graph": [],    # Layer 2: R2.1-R2.7
    "branching_graph": [],   # Layer 3: R3.1-R3.9
    "hierarchy_tree": [],    # Layer 4: R4.1-R4.8
    "path_graph": [],        # Layer 5: R5.1-R5.5
    "cross_layer": [],       # Layer 6: R6.1-R6.6
}
```

### Rule → Validator Mapping

| FOL Rule | Layer | Enforced By | Stage |
|----------|-------|-------------|-------|
| R1.1 Sequential scene numbers | Scene | `game_plan_validator` | After Phase 1 |
| R1.2 Transition endpoint validity | Scene | `game_plan_validator` | After Phase 1 |
| R1.3 No self-transitions | Scene | `game_plan_validator` | After Phase 1 |
| R1.4 Reachability | Scene | `game_plan_validator` | After Phase 1 |
| R1.5 Each scene has mechanics | Scene | `game_plan_validator` | After Phase 1 |
| R1.6 Scene labels ⊆ global | Scene | `game_plan_validator` | After Phase 1 |
| R1.7 Single-scene optimization | Scene | `game_plan_validator` | After Phase 1 |
| R2.1 Transition endpoints exist | Mechanic | `interaction_validator` | After Phase 2 |
| R2.2 No self-transitions | Mechanic | `interaction_validator` | After Phase 2 |
| R2.3 Valid trigger types | Mechanic | `interaction_validator` | After Phase 2 |
| R2.4 Trigger-mechanic compatibility | Mechanic | `interaction_validator` | After Phase 2 |
| R2.5 Starting mechanic = [0] | Mechanic | `game_plan_validator` | After Phase 1 |
| R2.6 DAG property | Mechanic | `interaction_validator` | After Phase 2 |
| R2.7 DnD context singleton | Mechanic | `blueprint_validator` | After Phase 4 |
| R3.1-R3.9 Branching graph | Branching | `content_validator` (branching) | After Phase 2 |
| R4.1-R4.8 Hierarchy tree | Hierarchy | `game_plan_validator` (structure) + `blueprint_validator` (zone IDs) | Phase 1 + 4 |
| R5.1-R5.5 Path graph | Path | `content_validator` (trace_path) + `blueprint_validator` (zone refs) | Phase 2 + 4 |
| R6.1 Label-Zone bijection | Cross | `blueprint_validator` | After Phase 4 |
| R6.2 Mechanic zone_labels ⊆ scene | Cross | `game_plan_validator` | After Phase 1 |
| R6.3 Distractor disjoint | Cross | `blueprint_validator` | After Phase 4 |
| R6.4 Score consistency | Cross | `game_plan_validator` (plan) + `blueprint_validator` (final) | Phase 1 + 4 |
| R6.5 Temporal constraint zones | Cross | `blueprint_validator` | After Phase 4 |
| R6.6 ID uniqueness | Cross | `blueprint_validator` | After Phase 4 |

### Per-Mechanic Frontend Constraints → Validators

The "Per-Mechanic Config Requirements" table from the formal rules maps directly to `content_validator.py`:

| Mechanic | validateConfig Rule | Codified In |
|----------|-------------------|-------------|
| drag_drop | `labels.length > 0` | `content_validator._validate_drag_drop()` |
| click_to_identify | `identificationPrompts.length > 0` | `content_validator._validate_click_to_identify()` |
| trace_path | `paths.length > 0 AND waypoints resolve to zones with x/y` | `content_validator._validate_trace_path()` + `blueprint_validator` |
| sequencing | `items.length > 0` | `content_validator._validate_sequencing()` |
| sorting | `items AND categories exist` | `content_validator._validate_sorting()` |
| memory_match | `config ≠ null AND pairs ≠ null AND pairs.length > 0` | `content_validator._validate_memory_match()` |
| branching | `nodes AND startNodeId exist AND find(startNodeId) ≠ null` | `content_validator._validate_branching()` |
| compare | `diagramA ≠ null AND diagramB ≠ null AND zones have x/y/w/h` | `content_validator._validate_compare()` |
| description | `zones with descriptions` | `content_validator._validate_description_matching()` |

### Compatibility Matrix Enforcement

The 9×9 mechanic compatibility matrix is codified as a `dict[str, set[str]]` in `validators/rules.py`:
- `COMPATIBLE_TRANSITIONS["drag_drop"] = {"click_to_identify", "trace_path", ...}` (all 8)
- `COMPATIBLE_TRANSITIONS["branching_scenario"] = {"compare_contrast"}` (terminal — almost nothing follows)
- `interaction_validator` checks every mode transition against this matrix
- Violations are `WARNING` severity (unusual but not fatal) for "O" entries, `ERROR` for "N" entries

### graph_builder.py — Runtime Graph Construction

`graph_builder.py` constructs the in-memory game graph from `GamePlan` and validates structural properties:

1. **Scene DAG**: Builds adjacency list from `scene_transitions`, checks reachability (R1.4), acyclicity
2. **Mechanic DAG per scene**: Builds from `mechanic_connections`, checks DAG property (R2.6), terminal existence
3. **Branching tree**: DFS from `startNodeId`, checks connectivity (R3.6), end node reachability (R3.5)
4. **Path graph**: Validates waypoint zone references exist (R5.1), sequential order (R5.2)
5. **Hierarchy tree**: Validates no cycles (R4.1), parent/child existence (R4.2-R4.3), single-parent constraint (R4.4)

The output is a validated graph structure passed to `blueprint_assembler.py` which uses it to wire `modeTransitions[]` and `zoneGroups[]`.

### Blueprint Validator — Final Gate

`blueprint_validator.py` runs ALL formal graph rules as a final gate before the blueprint reaches the frontend. It imports the full `RULE_REGISTRY` and runs every rule against the assembled `GameSpecification`. Any FATAL violation = pipeline error (not warning).

---

## Success Criteria

1. **All 9 mechanics produce playable games** — run each mechanic end-to-end
2. **Blueprint passes all formal graph rules** from `v4_formal_graph_rules.html`
3. **No drag_drop defaults anywhere** — grep confirms zero fallback-to-drag_drop
4. **Score arithmetic is always consistent** — validator catches 100%
5. **Multi-scene games work** — test 2-scene game with different mechanics per scene
6. **Zone matching ≥ 80%** for visual mechanics
7. **Total pipeline time < 5 min** for single-scene game (down from ~9 min in V3)
8. **Cost < $0.60/run** average

---

## What's Deferred

| Feature | Why Deferred | When to Add |
|---------|-------------|-------------|
| Critic agent (cross-model validation) | Get basics working first | After 10+ successful runs, analyze failure patterns |
| DSPy prompt optimization | Need training data from runs | After 50+ runs with scoring data |
| Speculative execution (Sherlock pattern) | Complexity, marginal latency gain | After pipeline is stable |
| ~~Checkpointing~~ | **INCLUDED** — see Phase 5.7 | Integrated into Phase 5 |
| Multi-model routing (RouteLLM) | Need baseline metrics first | After cost analysis of 20+ runs |
| New mechanic types | 9 is plenty for now | User demand driven |
| Reactive agent wrapper | May not be needed | After assessing game_designer quality |

---

## Estimated Total Effort

| Phase | Files | Lines (est.) | Description |
|-------|-------|-------------|-------------|
| Phase 1 | ~12 | ~1000 | Schemas, contracts, state, Zod |
| Phase 2 | ~5 | ~600 | Deterministic helpers |
| Phase 3 | ~5 | ~500 | Validators |
| Phase 4 | ~6 + prompts | ~600 | LLM agents + prompt templates |
| Phase 5 | ~6 | ~400 | LangGraph sub-graphs |
| Phase 6 | ~4 | ~200 | Integration, registration |
| **Total** | **~38** | **~3300** | Full V4 pipeline |

All new files in `backend/app/v4/` — zero modifications to existing V3 code.
V3 continues to work. V4 is a parallel pipeline selected by `pipeline_preset="v4"`.
