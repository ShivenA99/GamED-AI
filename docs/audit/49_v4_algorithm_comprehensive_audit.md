# 49. V4 Algorithm Pipeline — Comprehensive Audit

**Date**: 2026-02-25
**Branch**: `algorithm-games-template`
**Scope**: Full audit of LLM prompts, validation pipeline, retry logic, schema alignment, and frontend coverage for the V4 Algorithm Games pipeline.

**Root cause of all crashes**: The pipeline generates data via LLM with no structural validation, no Pydantic enforcement, no retry on bad content, and misaligned schemas between backend prompts and frontend expectations. Frontend normalizers and defensive defaults are band-aids — the fix must be at the source.

---

## Executive Summary

| Area | Score | Verdict |
|------|-------|---------|
| LLM Prompt Constraints | 2/10 | Types mostly open-ended; LLM hallucination frequent |
| Pydantic Schema Usage | 1/10 | Schemas exist but are NEVER used for validation |
| Content Validation | 0/10 | Validator exists but is DEAD CODE (not wired into graph) |
| Blueprint Validation | 0/10 | Validator exists but is NEVER CALLED |
| Content Retry Logic | 0/10 | No retry loop exists for content generation |
| Schema Alignment (BE↔FE) | 3/10 | Constraint types, board configs, scoring configs all mismatched |
| Frontend DS Coverage | 7/10 | 9 visualizers for 9 types; missing queue/deque/N-ary tree/trie |
| Frontend Prediction Coverage | 6/10 | 4/6 types implemented; code_completion + true_false missing |
| Frontend Board Coverage | 8/10 | All 6 board types implemented and working |
| Frontend Constraint Eval | 4/10 | 9 evaluator types, but backend prompts use different type names |

---

## Part 1: LLM Prompt Analysis

### 1.1 Game Concept Designer (`agents/game_concept_designer.py`)

**Prompt location**: Built dynamically in `_build_concept_prompt()`.

**Good**:
- `game_type` enumerated as `"state_tracer, bug_hunter, algorithm_builder, complexity_analyzer, constraint_puzzle"`. Post-LLM validation against `SUPPORTED_GAME_TYPES` with fallback.
- `difficulty` enumerated as `"beginner|intermediate|advanced"`.

**Bad — `config_hints` is completely freeform**:
- The prompt shows config_hints as comments only: `// state_tracer hints: data_structure, prediction_type, num_steps`
- NO valid values enumerated for any of these:
  - `data_structure`: Valid values are `array|graph|tree|dp_table|stack|linked_list|heap|hash_map|custom` — not mentioned
  - `prediction_type`: Valid values are `value|arrangement|multiple_choice|multi_select|code_completion|true_false` — not mentioned
  - `board_type`: Valid values are `item_selection|grid_placement|multiset_building|graph_interaction|value_assignment|sequence_building` — not mentioned
  - `fix_mode`: Valid values are `multiple_choice|free_text` — not mentioned
  - `complexity_dimension`: Valid values are `time|space|both` — not mentioned
- These hints flow verbatim to content generators, where they control critical prompt variables.

**Risk**: HIGH. Bad config_hints propagate to all downstream prompts.

### 1.2 State Tracer (`prompts/content_state_tracer.py`)

**Data structure types**: Shows 8 types in JSON comments (array, graph, tree, dp_table, stack, linked_list, heap, hash_map). But `{ds_type}` is injected from config_hints — if concept designer outputs `"priority_queue"` or `"linked list"` (with space), it passes through.

**Prediction types**: Shows only 4 types (value, arrangement, multiple_choice, multi_select). Missing `code_completion` and `true_false`.

**Critical gaps**:
1. `dataStructure.type` NOT constrained — injected as `{ds_type}` from freeform config_hints
2. Data structure sub-fields shown only as comments — LLM must infer correct schema per type
3. `prediction.type` not constrained — LLM picks from comment examples
4. **Pydantic types `dict` not union** — `ExecutionStep.dataStructure: dict` and `ExecutionStep.prediction: Optional[dict]` — no structural validation possible
5. `hints` allows 0-3 items in Pydantic but frontend expects exactly 3
6. `ArrayDataStructure.elements` is `list[Union[int, float, str]]` in Pydantic but frontend expects `number[]` — string elements crash

**Risk**: MEDIUM-HIGH.

### 1.3 Bug Hunter (`prompts/content_bug_hunter.py`)

**Best-constrained prompt**:
- `bugType` explicitly enumerated: `"off_by_one|wrong_operator|wrong_variable|missing_base_case|wrong_initialization|wrong_return|infinite_loop|boundary_error|logic_error"`
- `difficulty` shown as `<1|2|3>`

**Gaps**:
1. `fixMode` valid values not enumerated (injected from config_hints)
2. `bugLines` format ambiguous — could be single int instead of array
3. `fixOptions` doesn't enforce at least one `isCorrect: true`
4. `exposedBugs` IDs not cross-referenced with `bugId` values
5. `hints` allows 0-3 but frontend expects 3

**Risk**: LOW-MEDIUM.

### 1.4 Algorithm Builder (`prompts/content_algorithm_builder.py`)

**Simplest prompt**. Main gaps:
1. Block count not enforced
2. Distractor count guidance ("3-5") is text only
3. `indent_level` described as 0-7 but frontend comment says 0-3 (no runtime enforcement)
4. Code correctness unverifiable structurally
5. `hints` allows 0-3 but frontend expects 3

**Risk**: LOW.

### 1.5 Complexity Analyzer (`prompts/content_complexity_analyzer.py`)

**Critical gaps**:
1. `correctComplexity` is open-ended string (e.g., `"O(n log n)"` vs `"O(nlogn)"` vs `"O(N log N)"`). Frontend does string comparison for scoring — format inconsistency = broken scoring.
2. `complexityDimension` valid values not enumerated — LLM could output `"time_and_space"` or `"memory"`
3. `caseVariant` only shows 2 examples (`worst`, `average`) — LLM could invent others
4. `challenge.type` is `str` in Pydantic, not `Literal` — no validation
5. Prompt hardcodes 3 challenges; if `num_challenges` differs, no template for extra challenges

**Risk**: HIGH (Big-O string comparison is inherently fragile).

### 1.6 Constraint Puzzle (`prompts/content_constraint_puzzle.py`) — MOST CRITICAL

**Critical mismatches with frontend**:

| Issue | Backend Prompt | Frontend Expects |
|-------|---------------|-----------------|
| Constraint shape | `{type, params: {}, description}` | Typed fields at top level: `{type: "capacity", property: string, max: number}` |
| Constraint types | `capacity, no_conflict, sum_property, all_different, min_count, max_count, dependency, no_overlap, logical, precedence` | `capacity, exact_target, no_overlap, no_conflict, count_exact, count_range, all_different, all_assigned, connected` |
| Board config | `items[].name` | `items[].label` (field name mismatch) |
| Scoring method names | `optimality_ratio, binary, constraint_count, custom` | `sum_property, count, inverse_count, binary, ratio, weighted_sum` |
| Board type | `{board_type}` from config_hints | 6 valid types not enumerated in prompt |

**6 backend constraint types with NO frontend evaluator**: `sum_property`, `min_count`, `max_count`, `dependency`, `logical`, `precedence`

**5 frontend constraint types NEVER prompted for**: `exact_target`, `count_exact`, `count_range`, `all_assigned`, `connected`

**`category_to_puzzle` mapping** doesn't cover `multiset_building` or `value_assignment`.

**Risk**: CRITICAL. Constraint evaluation is broken at runtime.

---

## Part 2: Validation Pipeline Analysis

### 2.1 Graph Wiring (`graph.py`)

```
Phase 0: [input_analyzer, dk_retriever] → phase0_merge          ✅ Validated
Phase 1: concept_designer → concept_validator → [retry|pass]     ✅ Retry works
Phase 2: graph_builder → plan_validator → [retry|pass]           ⚠️ Retry useless (deterministic)
Phase 3: Send(content_gen) × N → content_merge                   ❌ NO VALIDATOR, NO RETRY
Phase 4: Send(asset_worker) × N → asset_merge → [retry|pass]     ✅ Retry works
Phase 5: blueprint_assembler → END                               ❌ NO VALIDATOR
```

### 2.2 Dead Code — Validators That Are Never Called

| Validator | File | Wired Into Graph? | Called By Anyone? |
|-----------|------|-------------------|-------------------|
| `algo_content_validator` | `validators/content_validator.py` | **NO** | **NO** — orphaned function |
| `validate_algorithm_blueprint` | `validators/blueprint_validator.py` | **NO** | **NO** — never imported |

### 2.3 Pydantic Schemas — Exist But Never Instantiated

The backend has detailed Pydantic models for every game type:
- `StateTracerSceneContent`, `BugHunterSceneContent`, `AlgorithmBuilderSceneContent`, `ComplexityAnalyzerSceneContent`, `ConstraintPuzzleSceneContent`
- `AlgorithmGameConcept`, `AlgorithmGamePlan`, `AlgorithmGameBlueprint`

**None of these are ever instantiated for validation.** All validators use manual `dict.get()` checks. This means:
- `Literal` type constraints are never enforced
- Field range constraints (`ge=1, le=3`) never checked
- Required vs optional not distinguished
- Nested model validation never runs

### 2.4 Content Generator — No Structured Output

`scene_content_generator.py` calls `llm.generate_json_for_agent()` with only a `schema_hint` string. It does NOT pass:
- `json_schema` parameter (which would enable constrained decoding)
- Any Pydantic model for post-hoc validation

The `generate_json_for_agent` method supports a `json_schema` parameter that enables guided decoding. This is unused.

### 2.5 Content Generator — No Retry on Bad Content

`_validate_content()` only calls `logger.warning()`. It never raises, never retries. The content is accepted regardless. Failed LLM calls produce `status: "failed"` entries, but `failed_content_ids` is written by `algo_content_merge` and nothing reads it.

### 2.6 Plan Retry Is Ineffective

`algo_graph_builder` is deterministic — same input always produces same output. It doesn't read `plan_validation` feedback. Retry loop wastes 2 cycles doing nothing.

### 2.7 Asset Retry — Stale Accumulator Bug

`asset_retry_router` reads `scene_assets_raw` which uses an `operator.add` reducer (append-only). After retry, both old failures AND new results exist. Could cause spurious re-retries (bounded by MAX_ASSET_RETRIES).

### 2.8 Fields NEVER Validated Anywhere

| Field | Expected Values | Validated By |
|-------|----------------|-------------|
| `dataStructure.type` | array, graph, tree, dp_table, stack, linked_list, heap, hash_map, custom | **Nobody** |
| `prediction.type` | arrangement, value, multiple_choice, multi_select, code_completion, true_false | **Nobody** |
| `boardType` | item_selection, grid_placement, multiset_building, graph_interaction, value_assignment, sequence_building | **Nobody** |
| `constraints[].type` | (backend and frontend lists don't even match) | **Nobody** |
| `scoringConfig.method` | (backend and frontend names don't match) | **Nobody** |
| `bugType` | off_by_one, wrong_operator, etc. | **Nobody** |
| `fixMode` | multiple_choice, free_text | **Nobody** |
| `challenge.type` | identify_from_code, infer_from_growth, find_bottleneck | **Nobody** |
| `complexityDimension` | time, space, both | **Nobody** |
| `caseVariant` | worst, best, average, amortized | **Nobody** |
| `indent_level` | 0-7 | **Nobody** |
| `hints` length | exactly 3 | **Nobody** |

### 2.9 Additional Bugs

- **`get_model_tier()` is dead code** — imported by content generator but never called. Per-game-type model routing (`MODEL_ROUTING`) is never applied.
- **`is_degraded` flag** — state field exists, no agent ever sets it. Pipeline doesn't self-report when content/assets fail.

---

## Part 3: Frontend Coverage Analysis

### 3.1 Data Structure Visualizers

| DS Type | Backend Schema | Frontend Type | Visualizer | Status |
|---------|---------------|--------------|-----------|--------|
| `array` | `ArrayDataStructure` | `ArrayDataStructure` | `ArrayVisualizer.tsx` | **FULL** |
| `graph` | `GraphDataStructure` | `GraphDataStructure` | `GraphVisualizer.tsx` | **FULL** |
| `tree` | `TreeDataStructure` | `TreeDataStructure` | `TreeVisualizer.tsx` | **Binary only** |
| `dp_table` | `DPTableDataStructure` | `DPTableDataStructure` | `DPTableVisualizer.tsx` | **FULL** |
| `stack` | `StackDataStructure` | `StackDataStructure` | `StackVisualizer.tsx` | **FULL** |
| `linked_list` | `LinkedListDataStructure` | `LinkedListDataStructure` | `LinkedListVisualizer.tsx` | **FULL** |
| `heap` | `HeapDataStructure` | `HeapDataStructure` | `HeapVisualizer.tsx` | **FULL** |
| `hash_map` | `HashMapDataStructure` | `HashMapDataStructure` | `HashMapVisualizer.tsx` | **FULL** |
| `custom` | `CustomObjectDataStructure` | `CustomObjectDataStructure` | `CustomObjectVisualizer.tsx` | **FULL** (fallback) |

**Missing visualizer types** (algorithms that need them):
| Type | Use Case | Current Workaround |
|------|----------|-------------------|
| **Queue/Deque** | BFS, sliding window | LLM falls to `custom` or `stack` — confusing for students |
| **N-ary Tree** | Tries, file systems, B-trees | `TreeVisualizer` crashes on `children[]` (expects `left`/`right`) |
| **Trie** | String algorithms | Falls to `custom` — loses character-labeled edge visualization |
| **String/CharArray** | Two-pointer, sliding window | Falls to `array` — no pointer visualization |

**Existing normalizations** (`normalizeType()`):
- `sorted_array` → `array`, `matrix/table` → `dp_table`, `linkedlist` → `linked_list`
- `priority_queue` → `heap`, `dict` → `hash_map`
- Compound types (`['a', 'b']`) → `custom`

### 3.2 Prediction Types

| Type | Backend Schema | Frontend Type | Renderer | Status |
|------|---------------|--------------|---------|--------|
| `arrangement` | `ArrangementPrediction` | `ArrangementPrediction` | Drag-to-sort | **FULL** |
| `value` | `ValuePrediction` | `ValuePrediction` | Text input | **FULL** |
| `multiple_choice` | `MultipleChoicePrediction` | `MultipleChoicePrediction` | Radio buttons | **FULL** |
| `multi_select` | `MultiSelectPrediction` | `MultiSelectPrediction` | Checkboxes | **FULL** |
| `code_completion` | `CodeCompletionPrediction` | `CodeCompletionPrediction` (type only) | **NONE** | Missing renderer |
| `true_false` | `TrueFalsePrediction` | `TrueFalsePrediction` (type only) | **NONE** | Missing renderer |

Note: `PredictionPanel` prop type is `Prediction` (4-type union), not `ExtendedPrediction` (6-type). The LLM prompt also only mentions the 4 base types.

### 3.3 Constraint Puzzle — Board Types

All 6 board types have full implementations:
| Board Type | Component | Status |
|-----------|-----------|--------|
| `item_selection` | `ItemSelectionBoard.tsx` | **FULL** |
| `grid_placement` | `GridPlacementBoard.tsx` | **FULL** |
| `multiset_building` | `MultisetBuildingBoard.tsx` | **FULL** |
| `graph_interaction` | `GraphInteractionBoard.tsx` | **FULL** |
| `value_assignment` | `ValueAssignmentBoard.tsx` | **FULL** |
| `sequence_building` | `SequenceBuildingBoard.tsx` | **FULL** |

`normalizeBoardType()` handles LLM creative variants. The **real problem** is at the prompt level, not the frontend.

### 3.4 Constraint Types — Critical Schema Mismatch

**Backend prompt tells LLM to generate**:
```json
{"type": "capacity", "params": {"property": "weight", "max": 15}, "description": "..."}
```

**Frontend evaluator expects**:
```typescript
{type: "capacity", property: "weight", max: 15}
```

Fields are inside `params` dict in backend but at top level in frontend. **Constraint evaluation is broken.**

**Type name mapping needed**:
| Backend Prompt Type | Frontend Evaluator Type | Action Needed |
|--------------------|------------------------|---------------|
| `capacity` | `capacity` | Flatten `params` → top level |
| `no_conflict` | `no_conflict` | Flatten `params` → top level |
| `no_overlap` | `no_overlap` | Flatten `params` → top level |
| `all_different` | `all_different` | Flatten `params` → top level |
| `sum_property` | *none* | Map to `exact_target` or `capacity` |
| `min_count` | *none* | Map to `count_range` with `{min: N}` |
| `max_count` | *none* | Map to `count_range` with `{max: N}` |
| `dependency` | *none* | New evaluator needed OR remove from prompt |
| `logical` | *none* | New evaluator needed OR remove from prompt |
| `precedence` | *none* | New evaluator needed OR remove from prompt |
| `custom` | *none* | Generic pass-through OR remove from prompt |
| *not prompted* | `exact_target` | Add to prompt |
| *not prompted* | `count_exact` | Add to prompt |
| *not prompted* | `count_range` | Add to prompt |
| *not prompted* | `all_assigned` | Add to prompt |
| *not prompted* | `connected` | Add to prompt |

### 3.5 Scoring Config — Name Mismatches

| Backend Method | Frontend Method | Match? |
|---------------|----------------|--------|
| `optimality_ratio` | `ratio` | **Name mismatch** |
| `binary` | `binary` | Shape mismatch (`params` vs `successValue`) |
| `constraint_count` | `count` | **Name mismatch** |
| `custom` | *none* | Missing |
| *not prompted* | `sum_property` | Never generated |
| *not prompted* | `inverse_count` | Never generated |
| *not prompted* | `weighted_sum` | Never generated |

---

## Part 4: Fix Plan

### Phase A: Fix LLM Prompts (Backend) — Constrain Output

**Goal**: Tell the LLM exactly what to generate. Enumerate every valid value.

**A1. Game Concept Designer — Enumerate config_hints values**
- File: `agents/game_concept_designer.py`
- Add explicit enum lists in the prompt for:
  - `data_structure`: `"MUST be one of: array, graph, tree, dp_table, stack, linked_list, heap, hash_map, custom"`
  - `prediction_type`: `"MUST be one of: value, arrangement, multiple_choice, multi_select"`
  - `board_type`: `"MUST be one of: item_selection, grid_placement, multiset_building, graph_interaction, value_assignment, sequence_building"`
  - `fix_mode`: `"MUST be one of: multiple_choice, free_text"`
  - `complexity_dimension`: `"MUST be one of: time, space, both"`

**A2. State Tracer Prompt — Lock data structure type**
- File: `prompts/content_state_tracer.py`
- Replace comment-based DS schemas with explicit conditional: `"For type '{ds_type}', the dataStructure object MUST have these exact fields: ..."` — show only the matching sub-schema, not all 8
- Add: `"prediction.type MUST be one of: value, arrangement, multiple_choice, multi_select"`
- Add: `"hints MUST be an array of exactly 3 strings"`
- Add: `"elements in array type MUST be numbers, not strings"`

**A3. Bug Hunter Prompt — Minor tightening**
- File: `prompts/content_bug_hunter.py`
- Add: `"fixMode MUST be one of: multiple_choice, free_text"`
- Add: `"fixOptions MUST have exactly one option with isCorrect: true"`
- Add: `"hints MUST be an array of exactly 3 strings"`
- Add: `"bugLines MUST be an array of integers, not a single integer"`

**A4. Complexity Analyzer Prompt — Standardize Big-O format**
- File: `prompts/content_complexity_analyzer.py`
- Add: `"correctComplexity and options MUST use EXACT format: O(1), O(log n), O(n), O(n log n), O(n^2), O(n^3), O(2^n), O(n!)"`
- Add: `"complexityDimension MUST be one of: time, space, both"`
- Add: `"caseVariant MUST be one of: worst, best, average, amortized"`
- Add: `"challenge.type MUST be one of: identify_from_code, infer_from_growth, find_bottleneck"`

**A5. Constraint Puzzle Prompt — Align with frontend contract** (CRITICAL)
- File: `prompts/content_constraint_puzzle.py`
- Replace constraint schema with frontend-aligned format:
  ```json
  {"type": "capacity", "property": "weight", "max": 15, "description": "..."}
  ```
  NOT:
  ```json
  {"type": "capacity", "params": {"property": "weight", "max": 15}, "description": "..."}
  ```
- Replace constraint type list with frontend's 9 types: `capacity, exact_target, no_overlap, no_conflict, count_exact, count_range, all_different, all_assigned, connected`
- Show per-constraint-type required fields
- Replace scoring method names: `optimality_ratio` → `ratio`, `constraint_count` → `count`
- Fix item field: `name` → `label`
- Enumerate `boardType` explicitly in prompt
- Add `showConstraintsVisually: true, allowUndo: true` to output schema

**A6. Algorithm Builder Prompt — Add hints constraint**
- File: `prompts/content_algorithm_builder.py`
- Add: `"hints MUST be an array of exactly 3 strings"`

### Phase B: Add Pydantic Validation + Retry (Backend)

**Goal**: Validate LLM output against Pydantic schemas. Retry on failure.

**B1. Wire content validator into graph**
- File: `graph.py`
- Add `algo_content_validator` node after `algo_content_merge`
- Add `content_retry_router` that re-dispatches `Send` for failed scenes
- Wire: `algo_content_merge` → `algo_content_validator` → `content_retry_router` → [retry `Send` | pass to asset_dispatch]
- Max retries: 1 (avoid infinite loops)

**B2. Use Pydantic for content validation**
- File: `validators/content_validator.py`
- Replace manual dict checks with Pydantic model instantiation:
  ```python
  try:
      StateTracerSceneContent(**content)
  except ValidationError as e:
      issues.extend(format_pydantic_errors(e))
  ```
- Do this for all 5 game types
- On failure, inject validation errors into retry prompt context

**B3. Wire blueprint validator**
- File: `agents/assembler_node.py`
- Call `validate_algorithm_blueprint(blueprint)` before returning
- If validation fails: attempt repair (fill defaults) or set `is_degraded: True`

**B4. Use Pydantic for blueprint validation**
- File: `validators/blueprint_validator.py`
- Replace manual dict checks with `AlgorithmGameBlueprint(**blueprint)` instantiation

**B5. Pass json_schema to LLM**
- File: `agents/scene_content_generator.py`
- For each game type, pass the Pydantic model's `.model_json_schema()` as the `json_schema` parameter to `generate_json_for_agent()`
- This enables constrained decoding when available

**B6. Fix plan retry (or remove it)**
- Option A: Route plan failures back to concept designer (so the concept gets regenerated)
- Option B: Remove the plan retry loop entirely (it's useless for a deterministic builder)

**B7. Fix asset retry accumulator**
- File: `routers.py`
- In `asset_retry_router`, filter `scene_assets_raw` by latest round only (or use `scene_assets` dict instead of raw list)

**B8. Wire model routing per game type**
- File: `agents/scene_content_generator.py`
- Call `get_model_tier(game_type)` to select the right model (pro for complex types, flash for simple)

### Phase C: Expand Frontend Coverage

**Goal**: Support all data structures and prediction types the backend can generate.

**C1. Add QueueVisualizer**
- New file: `components/visualizers/QueueVisualizer.tsx`
- Horizontal FIFO display with front/back pointers
- Add `queue` and `deque` to `normalizeType()` mapping
- Add Pydantic schema: `QueueDataStructure`

**C2. Extend TreeVisualizer for N-ary trees**
- File: `components/visualizers/TreeVisualizer.tsx`
- Support `children: string[]` in addition to `left`/`right`
- Update `TreeNode` type in both backend and frontend

**C3. Add CodeCompletionInput to PredictionPanel**
- File: `components/PredictionPanel.tsx`
- Code editor with template pre-fill, syntax highlighting, submit
- Update prop type from `Prediction` to `ExtendedPrediction`

**C4. Add TrueFalseInput to PredictionPanel**
- File: `components/PredictionPanel.tsx`
- Simple True/False button pair
- Update prop type from `Prediction` to `ExtendedPrediction`

**C5. Add constraint normalization layer**
- File: new `constraintPuzzle/normalizeConstraints.ts`
- Maps backend constraint format to frontend format
- Flattens `params` to top level
- Maps type names: `sum_property` → `capacity`/`exact_target`, `min_count`/`max_count` → `count_range`
- Called by `ConstraintPuzzleGame.tsx` on blueprint load

**C6. Add scoring config normalization**
- Map `optimality_ratio` → `ratio`, `constraint_count` → `count`
- Flatten `params` to top level

**C7. Add error boundary for all game components**
- New file: `components/GameErrorBoundary.tsx`
- Catches React errors, shows fallback UI with skip/retry options
- Wrap each game scene component

### Phase D: Tighten Pydantic Schemas (Backend)

**Goal**: Make schemas strict enough that Pydantic catches all bad data.

**D1. Change `dict` fields to discriminated unions**
- `ExecutionStep.dataStructure: dict` → `Union[ArrayDataStructure, GraphDataStructure, ...]` with discriminator on `type`
- `ExecutionStep.prediction: Optional[dict]` → `Optional[Union[ArrangementPrediction, ...]]` with discriminator
- `Constraint.params: dict` → flatten params into typed constraint models with discriminator

**D2. Add Literal constraints to unconstrained strings**
- `ComplexityChallenge.type: str` → `Literal["identify_from_code", "infer_from_growth", "find_bottleneck"]`
- `ComplexityChallenge.complexityDimension: str` → `Literal["time", "space", "both"]`
- `ComplexityChallenge.caseVariant: str` → `Literal["worst", "best", "average", "amortized"]`
- `BugHunterConfig.fixMode: str` → `Literal["multiple_choice", "free_text"]`
- `BoardConfig.boardType: str` → `Literal["item_selection", "grid_placement", ...]`

**D3. Enforce hints length**
- All `hints: list[str]` fields → `hints: list[str] = Field(min_length=3, max_length=3)`
- Or add `@field_validator` that pads to 3 with empty strings

**D4. Add cross-field validators**
- `BugHunterRound`: validate `fixOptions` has exactly one `isCorrect: true`
- `BugHunterTestCase`: validate `exposedBugs` reference valid `bugId` values
- `ComplexityChallenge`: validate `correctComplexity` is in `options` list

---

## Part 5: Priority Order

| Priority | Phase | Items | Impact | Effort |
|----------|-------|-------|--------|--------|
| **P0** | A5 | Constraint puzzle prompt alignment | Fixes broken constraint evaluation | Medium |
| **P0** | B1-B2 | Wire content validator + Pydantic | Catches all bad LLM output | Medium |
| **P1** | A1-A4, A6 | Constrain all prompts | Prevents hallucination at source | Low-Medium |
| **P1** | B3-B4 | Wire blueprint validator | Last-line defense before frontend | Low |
| **P1** | C5-C6 | Constraint + scoring normalization | Fixes runtime eval crashes | Medium |
| **P2** | D1-D4 | Tighten Pydantic schemas | Enables structural enforcement | Medium |
| **P2** | B5 | Pass json_schema to LLM | Constrained decoding | Low |
| **P2** | C7 | Error boundary | Graceful fallback on unexpected data | Low |
| **P3** | C1-C2 | Queue visualizer + N-ary tree | Broader algorithm coverage | Medium |
| **P3** | C3-C4 | code_completion + true_false prediction | Richer prediction types | Low |
| **P3** | B6-B8 | Fix plan retry, asset accumulator, model routing | Polish | Low |

---

## Part 6: Estimated Scope

| Phase | Files Modified | Lines Changed (est.) |
|-------|---------------|---------------------|
| A (Prompts) | 6 prompt/agent files | ~300 lines |
| B (Validation + Retry) | 5 backend files (graph, validators, generator, assembler) | ~400 lines |
| C (Frontend) | 8 frontend files (new visualizers, prediction, normalization, error boundary) | ~600 lines |
| D (Schemas) | 1 schema file + validators | ~200 lines |
| **Total** | ~20 files | ~1500 lines |
