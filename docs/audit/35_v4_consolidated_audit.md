# V4 Implementation Plan — Consolidated Audit Findings

**Date**: 2026-02-14
**Source**: 6 parallel deep-dive audits of `docs/v4_implementation_plan_final.md`
**Audits**: Data Flow Per Mechanic | LangGraph Orchestration | Schema Completeness | Prompts & Context | Logical Flow | New Functions & Tools

---

## Executive Summary

Six independent audits scrutinized the V4 implementation plan. Combined findings:

| Severity | Count | Breakdown |
|----------|-------|-----------|
| **CRITICAL** | 17 | Schema: 8, Data Flow: 6, LangGraph: 3 |
| **HIGH** | 38 | Data Flow: 20, Schema: 10, Logical: 8 |
| **MEDIUM** | 35 | Data Flow: 18, Schema: 13, Logical: 4 |
| **LOW** | 15 | Data Flow: 7, Schema: 5, Logical: 3 |
| **Total** | ~105 | (deduplicated across audits) |

**Root cause**: The plan designs a "clean" new schema (`GameSpecification`) without fully mapping against the 1200-line frontend type system (`InteractiveDiagramBlueprint`). The frontend is the immovable contract.

**Effort estimate**: ~52 production files, ~5200-6500 Python/TS LOC (new + adapted). ~55% new code, ~45% reused from V3.

---

## Critical Findings (Must Fix Before Writing ANY Code)

### C1: GameSpecification Is Incompatible with Frontend (Schema Audit)

The plan's `GameSpecification` has ~12 fields. The frontend's `InteractiveDiagramBlueprint` has 40+ fields. **24 fields the frontend reads are MISSING**, including:

- `templateType: 'INTERACTIVE_DIAGRAM'` (hard-coded check)
- `diagram: { assetPrompt, assetUrl, zones[] }` (every mechanic reads `bp.diagram.zones`)
- `labels: Label[]` with `correctZoneId` (drag_drop depends on this)
- `animationCues` (required, non-optional)
- `identificationPrompts[]` (click_to_identify reads at root, NOT inside config)
- `paths[]` (trace_path reads at root, NOT inside config)

**Fix**: Abandon `GameSpecification` as a new type. V4 output schema SHOULD BE `InteractiveDiagramBlueprint`. Reuse existing Pydantic models in `interactive_diagram.py`.

### C2: ContentBrief Type Completely Undefined (Data Flow + Schema)

The plan says `content_brief: ContentBrief` in MechanicPlan but **never defines what ContentBrief contains**. Each mechanic needs fundamentally different brief data:

| Mechanic | ContentBrief Must Include |
|----------|--------------------------|
| drag_drop | label_hints, distractor_strategy |
| click_to_identify | prompt_style, selection_mode |
| trace_path | path_count, waypoint_labels, requires_order |
| sequencing | item_count, distractor_count, is_cyclic |
| sorting_categories | category_names, items_per_category |
| memory_match | pair_count, match_type, game_variant |
| branching_scenario | node_count, narrative_structure, ending_count |
| compare_contrast | subject_a, subject_b, comparison_mode |
| description_matching | description_mode, distractor_count |

**Fix**: Define `ContentBrief` as a discriminated union (per-mechanic sub-types) or as generic dict with per-mechanic validation.

### C3: MechanicContent Output Type Undefined (Data Flow + Schema)

The plan says content_generator outputs `MechanicContent` but **never defines this type**. Need 9 per-mechanic Pydantic models matching exactly what the frontend config types require.

**Fix**: Define 9 `MechanicContent` subclasses (DragDropContent, SequencingContent, etc.) in `schemas/mechanic_content.py`.

### C4: V4MainState Never Defined (LangGraph Audit)

The plan references `V4MainState` but never defines it. Without this TypedDict, the graph cannot compile.

**Required fields (~37):**
- Input: question_text, question_id, _run_id, _pipeline_preset
- Phase 0: pedagogical_context, domain_knowledge
- Phase 1: game_plan, design_validation, design_retry_count
- Phase 2: mechanic_contents_raw (Annotated[list, operator.add]), mechanic_contents, interaction_results
- Phase 3: generated_assets_raw (Annotated[list, operator.add]), zone_coordinates
- Phase 4: game_specification, assembly_warnings
- Meta: generation_complete, phase_errors (Annotated[list, operator.add]), is_degraded

**Critical**: Fields accumulating from parallel Send workers MUST have `Annotated[list, operator.add]` reducers. Without this, `InvalidUpdateError` crashes the pipeline.

### C5: Nested Send API Does Not Work (LangGraph Audit)

The plan describes nested Send: per-scene dispatch, then per-mechanic dispatch within each scene. **LangGraph does not support nested Send**.

**Fix**: Flatten to single-level Send. Dispatch ALL mechanics across ALL scenes at once:
```
content_dispatch_router -> Send(content_generator, {scene_s1, mech_m1})
                        -> Send(content_generator, {scene_s1, mech_m2})
                        -> Send(content_generator, {scene_s2, mech_m1})
                        -> content_merge_node
```

### C6: SqliteSaver Instantiation Is Wrong (LangGraph Audit)

Plan shows `SqliteSaver.from_conn_string(checkpoint_db)` which returns a context manager, not a SqliteSaver instance.

Also: `SqliteSaver` doesn't support async. FastAPI needs `AsyncSqliteSaver`:
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
async with AsyncSqliteSaver.from_conn_string("v4_checkpoints.db") as memory:
    graph = builder.compile(checkpointer=memory)
```

### C7: Compare-Contrast Dual Diagram Pipeline Not Addressed (Data Flow)

Compare_contrast needs TWO separate diagrams with independent zone detection. The plan only describes single-diagram generation. This affects 5 data flow gaps:
- Dual `DiagramAssetNeed` entries
- Independent zone detection per diagram
- Rect-based zones (x,y,w,h) vs standard circle zones (x,y,r)
- Cross-diagram zone correspondence
- imageUrl population for both diagrams

### C8: Zone ID Chicken-and-Egg Problem (Logical Flow + Data Flow)

Content_generator runs BEFORE asset pipeline (zone detection). So content outputs zone LABELS (text), not zone IDs. But multiple mechanics reference zone IDs:
- `label.correctZoneId` (drag_drop)
- `prompt.zoneId` (click_to_identify)
- `waypoint.zoneId` (trace_path)
- `descriptions[zoneId]` (description_matching)

**Fix**: Blueprint assembler must perform label-to-ID mapping for ALL mechanics uniformly. Add `_translate_labels_to_zone_ids()` function.

### C9: Score Arithmetic Must Be Deterministic (Prompts Audit)

LLMs cannot do arithmetic reliably. V3 had constant score mismatch bugs.

**Fix**: Remove `max_score` from GamePlan LLM output. LLM outputs `points_per_item` + `expected_item_count`. Validator computes `max_score = points_per_item * expected_item_count`. Assembler computes `scene_max_score = sum(mechanic.max_score)`. Assembler computes `total_max_score = sum(scene.max_score)`.

---

## High-Priority Findings

### H1: Per-Mechanic Config Models Have Zero Fields (Schema)
All 9 mechanic config names are listed but fields are empty. Must reuse existing models from `interactive_diagram.py` or define all fields.

### H2: Field Name Mismatches Between Backend and Frontend (Schema + Data Flow)

| Mechanic | Backend | Frontend | Impact |
|----------|---------|----------|--------|
| memory_match | term/definition | front/back | Pairs won't render |
| branching | prompt/choices/next_node_id | question/options/nextNodeId | Nodes won't render |
| sorting | name | label | Categories won't display |

**Fix**: V4 models output frontend-compatible field names directly, or assembler normalizes.

### H3: ScoringRules, FeedbackRules, CompletionRules Undefined (Schema)
interaction_designer outputs these but they have no schema. Must match frontend `Mechanic.scoring` and `Mechanic.feedback`.

**Drop CompletionRules** — frontend handles completion via `mechanicRegistry.isComplete()`.

### H4: Hierarchical Mode vs Mechanic Inconsistency (Schema + Logical)
Plan says "hierarchical is a MODE, not a mechanic." But frontend registers `hierarchical` as a full mechanic with `HierarchyController` component.

**Fix**: Keep `hierarchical` as valid mechanic type the pipeline can emit.

### H5: Retry Counter Increment Location Unspecified (LangGraph)
If retry counter is in router logic but never written to state, it resets every time (infinite loop risk).

**Fix**: Validators increment counter. Routers only read it.

### H6: Error Propagation Granularity Missing (LangGraph)
If one Send worker raises exception, entire superstep fails (all parallel workers killed).

**Fix**: Catch errors within workers, return error status in state. Merge node separates successes from failures.

### H7: No Streaming/Observability Architecture (LangGraph)
Plan says nothing about frontend progress updates. V3 uses polling.

**Fix**: Implement SSE endpoint using `graph.astream_events(version="v2")` from the start.

### H8: Route Integration Doesn't Handle V4 State (Logical)
`routes/generate.py` expects V3 fields (`blueprint`, `template_selection`, `generation_complete`). V4 uses different names.

**Fix**: Add V4 code path in `run_generation_pipeline()` or normalize V4 output to V3 field names.

### H9: Store Initialization Type Mismatch for trace_path (Data Flow)
Registry's `initializeProgress` returns `PathProgress` but component reads `TracePathProgress` (different structure).

### H10: interaction_designer Output-to-Blueprint Mapping Undefined (Data Flow + Logical)
Plan says interaction_designer outputs ScoringRules/FeedbackRules/ModeTransitions per scene but doesn't detail how they map to blueprint fields.

---

## Medium-Priority Findings

### Architecture & Design
- **M1**: Phase 0 parallelism: gap analysis doc 18 incorrectly claims multiple START edges don't work. **They DO work in LangGraph 1.0.6**.
- **M2**: `scene_context_builder` as a graph node is wasteful (~0ms computation). Should be inline helper.
- **M3**: Inconsistent state naming: `V4MainState` vs `V4PipelineState` across docs.
- **M4**: Per-phase state isolation creates data transfer overhead at phase boundaries.
- **M5**: Content-only mechanics (branching, sequencing, sorting, memory) shouldn't have zone_labels validation.

### Per-Mechanic Data Flow
- **M6**: Leader line anchor generation unspecified for drag_drop.
- **M7**: Click_to_identify polygon vs circle zone detection strategy not specified.
- **M8**: Trace_path waypoint type (gate/branch_point/terminus) population not specified.
- **M9**: Sequencing layout_mode values don't match between backend and frontend (vertical_list vs vertical_timeline).
- **M10**: Memory_match ColumnMatchMode variant rendering requirements not addressed.
- **M11**: Description_matching has two description sources with unclear priority.
- **M12**: MC distractor descriptions generation unspecified for description_matching.
- **M13**: animationCues required field population not specified by any pipeline stage.
- **M14**: Multi-scene per-mechanic config forwarding needs camelCase/snake_case duality.
- **M15**: MechanicConnection trigger types limited (5 generic) vs frontend's 14 mechanic-specific triggers.
- **M16**: timed_challenge treated inconsistently (mode vs mechanic).
- **M17**: Blueprint validator doesn't run content-level checks (assembler bugs escape).

### Prompts & Context
- **M18**: DK field names don't match mechanic contracts. Need mapping layer.
- **M19**: Retry prompt includes full previous output, nearly doubling token cost. Use condensed version.
- **M20**: Gemini Flash truncates complex structured output. Route branching/compare/sorting/sequencing to Pro.

---

## Effort Analysis (New Functions & Tools Audit)

### File Inventory: 52 Production Files

| Category | Files | New LOC | Reused LOC |
|----------|-------|---------|------------|
| Schemas (`v4/schemas/`) | 6 | 700-850 | 300-350 |
| State (`v4/state/`) | 7 | 175-235 | 0 |
| Contracts (`v4/contracts/`) | 3 | 125-190 | 100-110 |
| Graph (`v4/graph/`) | 7 | 530-720 | 0 |
| Agents (`v4/agents/`) | 7 | 470-620 | 320-410 |
| Validators (`v4/validators/`) | 7 | 1030-1300 | 100 |
| Helpers (`v4/helpers/`) | 9 | 685-925 | 390-490 |
| Prompts (`v4/prompts/`) | 4 | 750-975 | 75-80 |
| Frontend | 2 | 350-450 | 0 |
| Route modifications | 1 | 90-120 | 0 |
| **Total** | **~52** | **~5200-6500** | **~1285-1540** |

### Plan vs Reality

| Metric | Plan Estimate | Audit Finding | Delta |
|--------|--------------|---------------|-------|
| Python files | ~38 | ~50 | +32% |
| Python LOC | ~3300 | ~4855-6055 | +47-83% |
| TypeScript files | 1 | 2 | +100% |
| Missing schemas | 0 | 12 | +12 schemas needed |
| Missing helpers | 0 | 5 files | ~290-390 LOC |
| Test infrastructure | 0 | ~12 files, ~3250 LOC | Not in plan at all |

### Key Reuse Opportunities

| Module | % Reusable from V3 |
|--------|--------------------|
| image_retrieval.py | ~95% as-is |
| llm_service.py | ~90% as-is |
| SAM3 services | ~100% as-is |
| gemini_service.py | ~80% |
| input_enhancer.py | ~70% |
| domain_knowledge_retriever.py | ~60% |
| blueprint_assembler_tools.py | ~50% (utility functions) |
| mechanic_contracts.py | ~80% |

### Missing Utility Functions Not in Plan

1. **v4/helpers/utils.py**: Zone coordinate normalization, label dedup, image URL validation, ID generation (~210 LOC)
2. **v4/helpers/scoring.py**: Deterministic score calculation, arithmetic validation (~50 LOC)
3. **v4/helpers/retry.py**: Retry prompt builder, validation feedback formatter (~50 LOC)

---

## Prompt Engineering Analysis

### Token Budget Per Run

| Phase | Agent | Input Tokens | Notes |
|-------|-------|-------------|-------|
| Phase 0 | input_analyzer | ~100 | Question only |
| Phase 0 | dk_retriever | ~500 | Question + search |
| Phase 1 | game_designer | ~5500-8000 | Capability spec + examples + DK |
| Phase 2 | content_generator (x3) | ~700-2500 each | ContentBrief + SceneContext + DK |
| Phase 2 | interaction_designer (x2) | ~2750-4350 each | Mechanic contents + pedagogy |
| Phase 3 | asset_dispatcher | ~200-500 each | AssetManifest entry |
| **Total** | | **~15K-25K input** | Down from V3's ~54K |

### Model Routing (Critical for Success)

| Agent | Model | Rationale |
|-------|-------|-----------|
| game_designer | gemini-2.5-pro (always) | Complex structured output, most critical |
| content_generator (branching, compare, sorting, sequencing) | gemini-2.5-pro | Flash fails on complex schemas |
| content_generator (drag_drop, click, trace, description, memory) | gemini-2.5-flash | Simpler output, cost savings |
| interaction_designer | gemini-2.5-flash | Simpler output per scene |
| input_analyzer | gemini-2.5-flash | Classification task |
| dk_retriever | gemini-2.5-flash | Extraction task |

### Key Prompt Design Decisions (P0 — Must Decide First)

1. **Score computation**: DETERMINISTIC (not LLM). LLM outputs points_per_item + count.
2. **ContentBrief**: STRUCTURED (not freeform). ~5 fields per mechanic.
3. **DK field reconciliation**: MAPPING LAYER (20-line dict mapping contract names to DK paths).
4. **Capability spec format**: STRUCTURED JSON per mechanic (~1550 tokens).
5. **Retry prompts**: CONDENSED previous output (~500 tokens, not ~3000 full output).
6. **Pydantic response_format**: PERMISSIVE (`extra="allow"`) for LLM schemas. Strict validation in deterministic validators.

---

## Corrected Phase 2 Architecture

Original plan's nested Send must be restructured:

```
game_plan_validator (passed)
    |
content_dispatch_router
    |--Send--> content_generator (s1_m1)
    |--Send--> content_generator (s1_m2)
    |--Send--> content_generator (s2_m1)
    |--Send--> content_generator (s2_m3)
    v
content_merge_node (deduplicates)
    |
content_retry_router
    |--Send--> content_generator (failed only)   [retry]
    |--string--> interaction_dispatch_router      [pass]
    v
interaction_dispatch_router
    |--Send--> interaction_designer (scene s1)
    |--Send--> interaction_designer (scene s2)
    v
interaction_merge_node
    |
interaction_retry_router
    |--Send--> interaction_designer (failed only) [retry]
    |--string--> phase3_asset_orchestrator        [pass]
```

Key changes: Single-level Send, flat mechanic parallelism, scene_context computed in dispatch router (not a separate node).

---

## Implementation Order Recommendation

### Pre-Implementation (Critical Path)
1. **Prototype LangGraph Send API** in isolation — gates entire Phase 2/3 architecture
2. **Decide GameSpecification vs InteractiveDiagramBlueprint** — gates all schema work
3. **Design compare_contrast dual-image architecture** — most complex mechanic

### Phase 1: Schemas & State (~Week 1)
4. Define V4MainState with all reducer annotations
5. Define ContentBrief (per-mechanic union)
6. Define 9 MechanicContent subclasses
7. Define ScoringRules, FeedbackRules, ModeTransitionOutput
8. Define 6 other missing schemas (SceneContext, ImageSpec, SceneTransition, etc.)

### Phase 2: Validators & Helpers (~Week 2)
9. Implement game_plan_validator with FOL rules
10. Implement content_validator per-mechanic
11. Implement zone_matcher (label-to-ID translation)
12. Implement blueprint_assembler (deterministic)
13. Implement scoring helpers (deterministic arithmetic)

### Phase 3: Prompts (~Week 2-3)
14. Write game_designer prompt + capability spec + 3 examples
15. Write 9 per-mechanic content_generator prompt templates
16. Write interaction_designer prompt template
17. Write retry prompt templates

### Phase 4: Graph Wiring (~Week 3)
18. Implement Phase 0 parallel fan-out (START -> input_analyzer + dk_retriever -> merge)
19. Implement Phase 1 retry loop (game_designer -> validator -> retry)
20. Implement Phase 2 Send dispatch + merge + retry
21. Implement Phase 3 Send dispatch + merge + retry
22. Implement Phase 4 deterministic assembly
23. Wire main_graph.py connecting all phases
24. Add AsyncSqliteSaver checkpointing

### Phase 5: Integration (~Week 4)
25. Add V4 code path in routes/generate.py
26. Add V4 agent metadata in instrumentation.py
27. Write v4ToBlueprint adapter (frontend) OR normalize output
28. Implement SSE streaming endpoint
29. E2E test with real LLM calls

---

## 12 Missing Schemas Referenced But Never Defined

| Schema | Purpose | Define In |
|--------|---------|-----------|
| ContentBrief | Content_generator input per mechanic | schemas/game_plan.py |
| MechanicContent (x9) | Content_generator output per mechanic | schemas/mechanic_content.py |
| ScoringRules | interaction_designer output | schemas/interaction.py |
| FeedbackRules | interaction_designer output | schemas/interaction.py |
| MechanicConnection | Scene-level mechanic wiring | schemas/game_plan.py |
| ModeTransitionOutput | interaction_designer transition output | schemas/interaction.py |
| SceneContext | Content_generator context injection | helpers/context.py |
| ImageSpec | Asset requirements in ScenePlan | schemas/game_plan.py |
| SceneTransition | Multi-scene navigation | schemas/game_plan.py |
| ThemeConfig | Visual theme configuration | schemas/game_specification.py |
| TimedConfig | Timed challenge configuration | schemas/game_specification.py |
| HierarchicalConfig | Hierarchy tree configuration | schemas/game_specification.py |

---

## Audit Source Details

Each audit produced a comprehensive report. Key source files examined:

| Audit | Files Read | Primary Sources |
|-------|-----------|-----------------|
| Data Flow | 14 | types.ts, mechanicRegistry.ts, all 9 interaction components |
| LangGraph | 8 | graph.py, state.py, 18c feasibility, 18 gap analysis |
| Schema | 10 | types.ts, interactive_diagram.py, blueprint_assembler_tools.py |
| Prompts | 12 | game_designer_v3.py, domain_knowledge_retriever.py, v3_context.py |
| Logical | 11 | v4_implementation_plan_final.md, v4_formal_graph_rules.html |
| New Code | 15 | All V3 services, agents, routes, configs |

---

## Key Corrections to Existing Documentation

1. **docs/audit/18_v4_gap_analysis_langgraph.md is WRONG** about multiple START edges. They DO work in LangGraph 1.0.6 via `add_edge(START, ...)`.
2. **Plan line 416-423**: `SqliteSaver.from_conn_string()` returns a generator, not an instance. Must use context manager or direct constructor.
3. **Plan line 114**: "hierarchical is a MODE" contradicts frontend registry where it's a full mechanic.
4. **Plan Phase 2**: Nested Send API is not supported. Must flatten to single-level dispatch.

---

**END OF CONSOLIDATED AUDIT**
