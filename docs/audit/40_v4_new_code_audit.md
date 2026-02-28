# V4 New Functions & Tools Audit

**Date**: 2026-02-14
**Scope**: Inventory all new files, functions, tools, and agents needed for V4. Identify reuse opportunities from V3. Estimate realistic LOC.
**Status**: COMPLETE -- 52 production files, ~5200-6500 LOC

---

## Executive Summary

The V4 plan estimates **~38 files, ~3300 lines**. This audit finds the realistic total is:

| Category | Plan Estimate | Audit Estimate | Delta |
|----------|---------------|----------------|-------|
| New Python files | ~38 | **50** | +12 |
| New TypeScript files | 1 | **2** | +1 |
| New Python LOC | ~3300 | **~4800-5500** | +45-67% |
| New TS LOC | ~200 | **~450** | +125% |
| Truly new logic | ~70% | **~55%** | Rest is reuse/adaptation |
| Reusable from V3 | ~30% | **~45%** | More reuse available |

---

## 1. File Inventory

### 1.1 Schema Files (`v4/schemas/`) -- 6 files, ~1000-1180 LOC

| File | LOC | Reuse | Contents |
|------|-----|-------|----------|
| `game_specification.py` | 250-300 | ~40% from `interactive_diagram.py` | GameSpecification, SceneSpec, SceneTransition, ThemeConfig, HierarchicalConfig, TimedConfig |
| `game_plan.py` | 200-250 | ~30% from `game_plan_schemas.py` | GamePlan, ScenePlan, MechanicPlan, ContentBrief, MechanicConnection, ImageSpec |
| `mechanic_configs.py` | 350-400 | ~60% from `game_design_v3.py` | 9 Pydantic models (one per mechanic) |
| `asset_manifest.py` | 120-150 | Mostly new | AssetManifest, DiagramAssetNeed, ItemImageNeed |
| `validation.py` | 60-80 | New | ValidationResult, ValidationIssue, Severity enum |
| `mechanic_content.py` | ~200 | New | 9 MechanicContent subclasses (content_generator output) |

### 1.2 State Files (`v4/state/`) -- 7 files, ~175-235 LOC

All new. V3 uses monolithic 160-field `AgentState`. V4 isolates per phase (~10-20 fields each).

**MISSING FROM PLAN**: State-to-sub-graph mapping. LangGraph sub-graphs require explicit state mapping. Needs reducers or inline logic.

### 1.3 Contract Files (`v4/contracts/`) -- 3 files, ~225-295 LOC

**CRITICAL FINDING**: `mechanic_contracts.py` already exists at `backend/app/config/mechanic_contracts.py` with all 9 mechanic definitions. V4 should import/adapt, not rewrite (~20-40 LOC vs ~200+ LOC).

| File | LOC | Contents |
|------|-----|----------|
| `mechanic_contracts.py` | 20-40 | Import + adapt existing |
| `capability_spec.py` | 200-250 | JSON menu for game_designer (9 mechanics) |
| `dk_field_resolver.py` | ~20 | DK field name mapping dict |

### 1.4 Graph Files (`v4/graph/`) -- 7 files, ~530-720 LOC

| File | LOC | Risk |
|------|-----|------|
| `main_graph.py` | 150-200 | Medium -- wires all phases |
| `phase0_graph.py` | 40-60 | Low -- fan-out/fan-in |
| `phase1_graph.py` | 80-100 | Low -- retry loop |
| `phase2_graph.py` | 150-200 | **HIGH** -- Send API (untested in codebase) |
| `phase3_graph.py` | 100-130 | **HIGH** -- Send API for assets |
| `phase4_graph.py` | 30-40 | Low -- deterministic |
| `routers.py` | 80-100 | Medium -- conditional edges |

**MAJOR RISK**: Send API has NEVER been used in this codebase. Zero `Send` imports exist. Must prototype before building full graphs.

### 1.5 Agent Files (`v4/agents/`) -- 7 files, ~790-1030 LOC

| File | LOC | Reuse | Notes |
|------|-----|-------|-------|
| `input_analyzer.py` | 60-80 | ~70% from `input_enhancer.py` | Same prompt, rewire state |
| `dk_retriever.py` | 120-160 | ~60% from `domain_knowledge_retriever.py` | Core functions reusable |
| `game_designer.py` | 150-200 | ~15% | V3 uses ReAct; V4 uses single call |
| `content_generator.py` | 200-250 | ~25% | 9 per-mechanic templates |
| `interaction_designer.py` | 100-130 | ~20% | Combined per-scene call |
| `asset_dispatcher.py` | 150-200 | ~50% from services | Deterministic tool chain |
| `blueprint_assembler.py` | 300-400 | ~50% from `blueprint_assembler_tools.py` | Pure function |

### 1.6 Validator Files (`v4/validators/`) -- 7 files, ~1130-1400 LOC

| File | LOC | Notes |
|------|-----|-------|
| `rules.py` | 400-500 | **MISSING FROM PLAN** -- 42+ rule functions + compatibility matrix |
| `game_plan_validator.py` | 180-220 | ~12 structural checks |
| `content_validator.py` | 250-300 | 9 per-mechanic validate functions |
| `interaction_validator.py` | 80-100 | Score/feedback/transition checks |
| `asset_validator.py` | 60-80 | Zone quality, coverage checks |
| `blueprint_validator.py` | 120-150 | Final gate running all rules |
| `rule_registry.py` | 40-50 | Registry linking rules to validators |

### 1.7 Helper Files (`v4/helpers/`) -- 9 files, ~1075-1475 LOC

| File | LOC | Reuse | Notes |
|------|-----|-------|-------|
| `blueprint_assembler.py` | 300-400 | ~50% from `blueprint_assembler_tools.py` | Main assembly logic |
| `zone_matcher.py` | 100-130 | ~40% | Label-to-zone-ID mapping |
| `graph_builder.py` | 200-250 | 0% | DAG construction, DFS, cycle detection |
| `utils.py` | 80-100 | ~60% from assembler tools | Coordinate normalization, ID generation |
| `scoring.py` | 40-50 | New | Deterministic score calculation |
| `retry.py` | 40-60 | New | Retry prompt builder |
| `context_builder.py` | 60-80 | New | Scene context injection |
| `dk_projector.py` | 40-50 | New | DK field projection per mechanic |
| `asset_utils.py` | 60-80 | ~50% | Image URL validation, serving |

### 1.8 Prompt Files (`v4/prompts/`) -- 4+ files, ~825-1055 LOC

| File | LOC | Notes |
|------|-----|-------|
| `game_designer.py` | 200-250 | System prompt + task builder + examples |
| `content_generator.py` | 500-650 | 9 per-mechanic templates |
| `interaction_designer.py` | 80-100 | Scoring/feedback prompt |
| `retry_templates.py` | 45-55 | Condensation + retry sections |

### 1.9 Frontend Files -- 2 new + modifications

| File | LOC | Notes |
|------|-----|-------|
| `schemas/gameSpecification.ts` | 250-300 | Zod runtime validation |
| `utils/v4ToBlueprint.ts` | 100-150 | **NOT IN PLAN** -- adapter function required |
| PipelineView modifications | ~50 | V4 agent metadata entries |

---

## 2. Existing Code Reuse Analysis

### High Reuse (80%+)

| Module | Reusability | Changes |
|--------|------------|---------|
| `image_retrieval.py` | ~95% as-is | None. Import directly. |
| `llm_service.py` | ~90% as-is | Register V4 agent names |
| SAM3 services | ~100% as-is | None |
| `mechanic_contracts.py` (config) | ~80% | Already exists! Import. |

### Medium Reuse (50-80%)

| Module | Reusability | Changes |
|--------|------------|---------|
| `gemini_service.py` | ~80% | Optional: add response_schema |
| `input_enhancer.py` | ~70% | Rewire state I/O |
| `domain_knowledge_retriever.py` | ~60% | Rewire state, slim output |
| `blueprint_assembler_tools.py` | ~50% | Extract utilities, rewrite main function |

### Low Reuse (<50%)

| Module | Reusability | Notes |
|--------|------------|-------|
| V3 agents (game_designer_v3, etc.) | ~15% | V3 uses ReAct; V4 uses single calls |
| V3 graph.py | ~10% | Completely different architecture |
| V3 validators | ~15% | Pattern reuse only |

### Extend (not rewrite)

| Module | Changes |
|--------|---------|
| `instrumentation.py` | Add ~10 V4 agent metadata entries |
| `agent_models.py` | Add ~6 V4 agent model assignments |
| `routes/generate.py` | Add V4 code path in pipeline routing |

---

## 3. Missing Helper Functions Not in Plan

### 3.1 Zone Coordinate Normalization (~80-100 LOC)
- `bbox_to_polygon(x, y, w, h)` -> polygon points
- `polygon_to_percentage(points, img_w, img_h)` -> percentage coords
- `normalize_zone_shape(zone_dict)` -> auto-detect polygon vs circle
- `clamp_coordinates(zone_dict)` -> ensure 0-100% range
- ~60% reusable from `blueprint_assembler_tools.py`

### 3.2 Label Deduplication (~40-60 LOC)
- `deduplicate_labels(labels)` -> case-insensitive, plural-aware
- `match_labels_fuzzy(expected, detected)` -> fuzzy matching dict
- ~70% reusable from `blueprint_assembler_tools.py`

### 3.3 Score Calculation (~40-50 LOC)
- `calculate_mechanic_score(items_count, points_per_item)` -> int
- `validate_score_arithmetic(plan)` -> list of errors
- `rollup_scores(mechanics)` -> total

### 3.4 ID Generation (~30-40 LOC)
- `generate_zone_id(scene_number, index)` -> str
- `generate_label_id(scene_number, index)` -> str
- `generate_mechanic_id(scene_number, mechanic_type)` -> str
- ~80% reusable from `_make_id()` in assembler tools

### 3.5 Retry Utilities (~40-60 LOC)
- `build_retry_prompt(original, validation_result)` -> str
- `should_retry(result, count, max)` -> bool
- `format_validation_feedback(issues)` -> str

---

## 4. New API Endpoints

| Endpoint | Method | Status | LOC |
|----------|--------|--------|-----|
| `POST /api/generate` (preset="v4") | POST | Extend existing | ~30 |
| `GET /api/generate/{id}/status` | GET | Reuse existing | 0 |
| `GET /api/assets/v4/{run_id}/{filename}` | GET | NEW | ~20 |
| `GET /api/v4/runs/{run_id}/checkpoints` | GET | NEW | ~40 |
| `POST /api/v4/runs/{run_id}/resume` | POST | NEW | ~30 |

**Total new endpoint LOC**: ~90-120

---

## 5. Testing Infrastructure (0 in plan)

The plan provides **zero** testing infrastructure. Needed:

| Category | Files | LOC |
|----------|-------|-----|
| Unit tests (schemas, validators, rules, helpers) | 6 | ~1650 |
| Integration tests (per phase) | 6 | ~900 |
| Fixtures/mocks (game plans, content, assets) | 4 | ~700 |
| E2E test script | 1 | ~200 |
| **Total** | **17** | **~3450** |

---

## 6. Dependencies

No new packages required. All installed:
- `langgraph` 1.0.6 (Send API available)
- `langgraph-checkpoint-sqlite` 3.0.3
- `pydantic` 2.x
- `google-genai` (current)

Optional: `rapidfuzz` for zone fuzzy matching.

**Verification needed**: `from langgraph.constants import Send` -- must confirm before implementation.

---

## 7. Revised Totals

### Production Code

| Category | Files | New LOC | Reused LOC |
|----------|-------|---------|------------|
| Schemas | 6 | 700-850 | 300-350 |
| State | 7 | 175-235 | 0 |
| Contracts | 3 | 125-190 | 100-110 |
| Graph | 7 | 530-720 | 0 |
| Agents | 7 | 470-620 | 320-410 |
| Validators | 7 | 1030-1300 | 100 |
| Helpers | 9 | 685-925 | 390-490 |
| Prompts | 4 | 750-975 | 75-80 |
| Frontend | 2 | 350-450 | 0 |
| Routes | 1 | 90-120 | 0 |
| **Total** | **~52** | **~4900-6400** | **~1285-1540** |

### Code Composition

**~55% genuinely new code, ~45% reused/adapted from V3.**

---

## 8. Top 5 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LangGraph Send API never used in codebase | Phase 2-3 may not work | Prototype FIRST |
| Sub-graph state mapping non-trivial | Compile errors | Test with minimal 2-node sub-graph |
| 9 content prompts need iteration | Slow progress | Start with 3 mechanics (drag_drop, sequencing, branching) |
| 42+ formal rules = high test burden | Long testing phase | Implement incrementally, FATAL rules first |
| Frontend adapter IS required | Plan underestimates | Design with frontend compat as primary constraint |

---

## 9. Implementation Order

1. **Week 1**: Schemas + Contracts + State + Missing utilities + Send API prototype
2. **Week 2**: Validators + Rules + Helpers + Mock data generators
3. **Week 3**: LLM Agents + Prompts (start with 3 mechanics)
4. **Week 3-4**: Graph wiring (main_graph first, then sub-graphs)
5. **Week 4**: Integration + Frontend adapter + E2E test + remaining 6 mechanics

**Critical path**: Send API prototype (Week 1) gates Phase 2-3 graph construction.
