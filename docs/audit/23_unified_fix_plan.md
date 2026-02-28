# Unified V3 Pipeline Fix Plan

**Date:** 2026-02-11
**Sources:** All 19 audit documents (00-22), 43 academic papers, mechanic redesign research
**Scope:** End-to-end multi-mechanic support, graph architecture, frontend richness

---

## Executive Summary

**370+ unique issues** identified across 19 audit documents. Only **~14 fixes applied** (agent prompts + validator tweaks). **~86+ fixes remain**, spanning schemas, tools, blueprint assembly, frontend types, Zustand store, and frontend components.

**Root problem:** The entire pipeline — prompts, schemas, tools, validators, blueprint assembly, and frontend — was designed around `drag_drop` label-diagram games. All 9 other mechanics are structurally broken because no agent generates their mechanic-specific content, and no component reads it even if it existed.

**Architecture problem:** Flat 8-node graph with monolithic ReAct agents processes all scenes sequentially. Research shows Quality Gate + Map-Reduce patterns outperform monolithic ReAct for structured multi-step tasks.

---

## 1. PER-MECHANIC END-TO-END GAP MATRIX

For each mechanic, this traces what's broken at every pipeline stage.

### 1.1 drag_drop — WORKS (Polish Only)

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | OK | — |
| Game Designer | OK | — |
| Scene Architect | OK | Zones + positions generated |
| Interaction Designer | OK | Scoring + feedback generated |
| Asset Generator | OK | Image search + zone detection |
| Blueprint Assembler | OK | Zones + labels forwarded |
| Frontend Types | PARTIAL | `DragDropConfig` type exists but component doesn't read it |
| Frontend Component | WORKS | DiagramCanvas + DropZone + DraggableLabel |
| **Polish gaps** | | Leader lines, spring physics, zoom/pan, info popup on correct, star rating |

### 1.2 click_to_identify — DEGRADED

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | OK | `label_descriptions` available but unused downstream |
| Game Designer | PARTIAL | Outputs `type: "click_to_identify"` but no `click_config` data |
| Scene Architect | PARTIAL | `generate_mechanic_content` handler exists but no identification prompts generated from `label_descriptions` |
| Interaction Designer | PARTIAL | Generic scoring/feedback, no per-zone identification feedback |
| Asset Generator | OK | Same as drag_drop (zones on diagram) |
| Blueprint Assembler | BROKEN | No `clickToIdentifyConfig` forwarded to blueprint. Scoring/feedback DROPPED (L654-662 list→dict crash) |
| Frontend Types | MISSING | `ClickToIdentifyConfig` interface doesn't exist in types.ts |
| Frontend Component | PARTIAL | HotspotManager works but: leaks zone labels in `any_order` mode (L227-230), no `promptStyle`/`highlightStyle` config reading, zones always visible |
| **Zustand** | PARTIAL | `identificationProgress` exists but score OVERWRITES (L475) instead of accumulating |

### 1.3 trace_path — DEGRADED

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | OK | `sequence_flow_data` available but only partially consumed |
| Game Designer | PARTIAL | Outputs `type: "trace_path"` but no `path_config.waypoints` |
| Scene Architect | PARTIAL | `generate_mechanic_content` handler generates waypoints but no SVG paths, no particle config, no color transitions |
| Interaction Designer | PARTIAL | Generic scoring, no per-waypoint transition feedback |
| Asset Generator | PARTIAL | Image search works but no mechanic-specific image requirements (pathways/connections) |
| Blueprint Assembler | BROKEN | No `tracePathConfig` forwarded. Scoring/feedback DROPPED |
| Frontend Types | MISSING | `TracePathConfig` interface doesn't exist in types.ts |
| Frontend Component | PARTIAL | PathDrawer renders straight lines only. No curves, particles, color transitions, directional arrows, circular paths, freehand mode |
| **Zustand** | PARTIAL | `pathProgress` exists but score OVERWRITES (L458) |

### 1.4 sequencing — BROKEN

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | PARTIAL | `sequence_flow_data` has flow items but no per-item images/descriptions |
| Game Designer | PARTIAL | Outputs `type: "sequencing"` but `config_hint` has no `items[]`/`correct_order[]` |
| Scene Architect | PARTIAL | `generate_mechanic_content` handler generates items + correct_order but no images, layout mode, card type, connector style, or instructions |
| Interaction Designer | PARTIAL | Generic scoring, no Kendall tau distance scoring, no position-based feedback |
| Asset Generator | BROKEN | No per-item illustration generation. Only generates diagram images |
| Blueprint Assembler | BROKEN | Maps items but drops expanded config (layoutMode, cardType, connectorStyle). Scoring/feedback DROPPED |
| Frontend Types | PARTIAL | `SequenceConfig` exists but missing ~4 fields (layoutMode, cardType, connectorStyle, showPositionNumbers) |
| Frontend Component | PARTIAL | SequenceBuilder: text-only list, no timeline/circular layouts, no image cards, no connecting arrows, no slot placement |
| **Zustand** | PARTIAL | `sequencingProgress` + `updateSequenceOrder`/`submitSequence` exist but don't restore from storeProgress |

### 1.5 sorting_categories — BROKEN

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | UNUSED | `categorization_data` field exists but never populated |
| Game Designer | PARTIAL | Outputs `type: "sorting_categories"` but no `sorting_config.categories[]`/`items[]` |
| Scene Architect | PARTIAL | Handler produces flat lists but fragile category matching, no sort_mode/Venn/item images |
| Interaction Designer | PARTIAL | Generic scoring, no per-category misconception triggers |
| Asset Generator | BROKEN | No per-item illustrations, no category icon generation |
| Blueprint Assembler | BROKEN | Drops expanded config. `correctCategoryId` must be LIST not string. Scoring/feedback DROPPED |
| Frontend Types | PARTIAL | `SortingConfig` exists but missing ~5 fields. `SortingItem.correctCategoryId` is string, should be `correct_category_ids: string[]` |
| Frontend Component | PARTIAL | SortingCategories: bucket mode only, no Venn/matrix/column, text-only items, no themed containers, no iterative correction |
| **Zustand** | PARTIAL | `sortingProgress` + actions exist but don't restore from storeProgress |

### 1.6 description_matching — BROKEN

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | UNUSED | `label_descriptions` available but V3 agents don't consume it |
| Game Designer | PARTIAL | Outputs `type: "description_matching"` but no `description_match_config.descriptions[]` |
| Scene Architect | BROKEN | Handler exists but generates appearance-based descriptions, not functional. No distractor descriptions |
| Interaction Designer | PARTIAL | Generic scoring, no per-description misconception triggers |
| Asset Generator | OK | Same as drag_drop |
| Blueprint Assembler | BROKEN | No `descriptionMatchingConfig` forwarded. Scoring/feedback DROPPED |
| Frontend Types | PARTIAL | `DescriptionMatchConfig` exists but missing ~4 fields |
| Frontend Component | HAS BUG | DescriptionMatcher: MC option reshuffle every render (~L420-450, `sort(() => Math.random() - 0.5)` in render function), no connecting lines, no defer-evaluation |
| **Zustand** | PARTIAL | `recordDescriptionMatch` exists but score OVERWRITES (L645). Also `handleDescriptionMatch` (index.tsx L760) compares `zone.id === labelId` (different namespaces) |

### 1.7 memory_match — BROKEN

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | UNUSED | `term_definition_pairs` could be derived from `label_descriptions` but never done |
| Game Designer | PARTIAL | Outputs `type: "memory_match"` but no `memory_config.pairs[]` |
| Scene Architect | BROKEN | **NO handler at all** in `generate_mechanic_content`. Uses generic fallback description |
| Interaction Designer | PARTIAL | Generic scoring, no per-pair educational explanations |
| Asset Generator | BROKEN | No per-card image generation |
| Blueprint Assembler | BROKEN | No `memoryMatchConfig` forwarded. Scoring/feedback DROPPED |
| Frontend Types | PARTIAL | `MemoryMatchConfig` exists but missing ~5 fields (matchedCardBehavior, mismatchPenalty, showExplanationOnMatch) |
| Frontend Component | HAS BUG | MemoryMatch: uses opacity-based flip (not true 3D CSS perspective), text-only cards, no themed backs, no explanation popup, no game variants |
| **Zustand** | PARTIAL | `memoryMatchProgress` + `recordMemoryMatch`/`recordMemoryAttempt` exist but don't restore from storeProgress |

### 1.8 branching_scenario — BROKEN

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | N/A | No branching data in DK schema |
| Game Designer | PARTIAL | Outputs `type: "branching_scenario"` but minimal `branching_config` |
| Scene Architect | PARTIAL | Handler exists but no visual assets, no state variables, no DAG validation |
| Interaction Designer | PARTIAL | Generic scoring, no per-decision consequence feedback |
| Asset Generator | BROKEN | Most asset-intensive mechanic. No scene backgrounds, character sprites, state variable displays |
| Blueprint Assembler | BROKEN | No `branchingConfig` forwarded properly. Scoring/feedback DROPPED |
| Frontend Types | PARTIAL | `BranchingConfig` exists but missing ~3 fields |
| Frontend Component | PARTIAL | BranchingScenario: no visual novel mode, no character art, no state displays, no minimap, no debrief |
| **Zustand** | PARTIAL | `branchingProgress` + actions exist but don't restore from storeProgress |

### 1.9 compare_contrast — BROKEN

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | UNUSED | `comparison_data` available but only read by `check_capabilities` |
| Game Designer | PARTIAL | Outputs `type: "compare_contrast"` but minimal `compare_config` |
| Scene Architect | BROKEN | No LLM fallback for comparison categories. Architecture supports only 1 image per scene — compare needs 2 |
| Interaction Designer | PARTIAL | Generic scoring |
| Asset Generator | BROKEN | **CRITICAL**: No dual-image generation pipeline. Only generates single diagram per scene |
| Blueprint Assembler | BROKEN | No `compareConfig` forwarded. Scoring/feedback DROPPED |
| Frontend Types | PARTIAL | `CompareConfig` exists but missing ~6 fields |
| Frontend Component | PARTIAL | CompareContrast: basic side-by-side only, no slider/overlay/Venn/spot-difference, no synchronized zoom, dead `highlightMatching` field |
| **Zustand** | PARTIAL | `compareProgress` + actions exist but don't restore from storeProgress |

### 1.10 hierarchical — DEGRADED

| Stage | Status | Gap |
|-------|--------|-----|
| DK Retriever | OK | `hierarchical_relationships` available |
| Game Designer | OK | `labels.hierarchy` with groups |
| Scene Architect | OK | `zone_hierarchy` populated |
| Interaction Designer | PARTIAL | Generic scoring |
| Asset Generator | OK | Same as drag_drop |
| Blueprint Assembler | PARTIAL | `zoneGroups` forwarded but no expanded config |
| Frontend Types | OK | `ZoneGroup` type exists |
| Frontend Component | PARTIAL | HierarchyController works for basic reveal but no deep nesting, no animated transitions |
| **Zustand** | OK | `hierarchyState` exists |

---

## 2. CRITICAL ROOT CAUSES (15)

| # | Root Cause | Impact | Severity | Fix Phase |
|---|-----------|--------|----------|-----------|
| RC-1 | Agent prompts don't mandate mechanic-specific tool calls | ALL non-drag_drop get empty configs | CRITICAL | **APPLIED** (prompts rewritten) |
| RC-2 | No per-item image generation capability | sequencing, sorting, memory_match | HIGH | Phase 2 tools |
| RC-3 | No scene/character image generation for branching | branching_scenario | HIGH | DEFERRED |
| RC-4 | No dual-image generation for compare_contrast | compare_contrast | HIGH | DEFERRED |
| RC-5 | No functional description generation from label_descriptions | click_to_identify, description_matching | HIGH | Phase 2 tools |
| RC-6 | No pair/tree/category generation for memory/branching/sorting | 3 mechanics | HIGH | Phase 2 tools |
| RC-7 | Single ReAct agent handles all scenes sequentially | ALL multi-scene | CRITICAL | Graph redesign |
| RC-8 | Asset generator is 100% diagram-centric | ALL non-diagram mechanics | CRITICAL | Phase 2 tools |
| RC-9 | GameDesignV3Slim has only `type: str` — zero mechanic config flows through Phase 1 | ALL | CRITICAL | Phase 1 schemas |
| RC-10 | Blueprint assembler drops scoring/feedback for 6/9 mechanics at L654-662 | 6 mechanics | CRITICAL | Phase 4 |
| RC-11 | V3 image serving broken — no routes, ID mismatch (routes use question_id, V3 saves by run_id) | ALL | CRITICAL | Phase 0 |
| RC-12 | Retry count off-by-one — "max 2 retries" = 1 actual retry | ALL | HIGH | Phase 0 |
| RC-13 | DomainKnowledge TypedDict <-> Pydantic mismatch — 3 fields lost | ALL | HIGH | Phase 0 |
| RC-14 | Bloom's taxonomy drives mechanic selection — forces drag_drop baseline | ALL non-drag_drop | HIGH | Phase 0 |
| RC-15 | Validators too lenient — missing mechanic configs = -0.05 WARNING, not FATAL | ALL | HIGH | **APPLIED** (penalties increased) |

---

## 3. WHAT'S BEEN APPLIED vs REMAINING

### Applied (~14 fixes)

| Fix | File | What |
|-----|------|------|
| max_iterations | 4 agent files | 8→15 for scene/interaction/asset, 4→6 for blueprint |
| System+task prompts | scene_architect_v3.py | All 10 mechanics documented, mandatory generate_mechanic_content |
| System+task prompts | interaction_designer_v3.py | Mechanic-specific scoring/feedback guidance |
| Task prompt | game_designer_v3.py | Mandate check_capabilities, per-mechanic config data |
| System+task prompt | asset_generator_v3.py | Mechanic-aware image guidance |
| Validator | design_validator.py | compare+hierarchical checks, penalties -0.05→-0.1 |
| Validator | interaction_spec_v3.py | 3 missing trigger mechanics added |
| Validator | scene_spec_v3.py | compare_contrast validation |
| Asset tools | asset_generator_tools.py | Key mismatch fix, auto-clean, mechanic-aware hints, fuzzy label matching |
| Route fix | generate.py | Multi-scene URL proxying |
| Blueprint | blueprint_assembler_tools.py | Fuzzy label matching |

### Remaining (~86+ fixes across 9 phases)

---

## 4. IMPLEMENTATION PHASES

### Phase 0: Critical Infrastructure (6 fixes, ~80 lines, ~6 files) — MUST BE FIRST

| Fix | File | Description | Severity |
|-----|------|-------------|----------|
| 0.1 | `routes/generate.py` | Add V3 image serving route `/assets/v3/{run_id}/{filename}`. Rewrite ALL image URLs in `game_sequence` scenes: pipeline_outputs → `/api/assets/v3/` | CRITICAL |
| 0.2 | `graph.py` ~L1862,1875,1888 | Fix retry count off-by-one: `>= 2` → `>= 3` in all 3 validation routers | CRITICAL |
| 0.3 | `state.py` ~L321-331 | Fix DomainKnowledge TypedDict: add `query_intent`, `suggested_reveal_order`, `scene_hints` | HIGH |
| 0.4 | `routes/generate.py` ~L220-273 | Add V3 agent output recording in `_build_agent_outputs()` | HIGH |
| 0.5 | `routes/generate.py` | Fix topology metadata: hardcoded `"T1"` → `pipeline_preset or "T1"` | MEDIUM |
| 0.6 | `game_design_v3_tools.py` L108-111 | Remove Bloom's forced `baseline_mechanic = "drag_drop"`. Let `check_capabilities` decide | HIGH |

### Phase 1: Schema Expansion (8 fixes, ~400 lines, ~6 files) — Blocks Phases 2-4

| Fix | File | Description |
|-----|------|-------------|
| 1.1 | `game_design_v3.py` | Expand `SequenceDesign`: add `SequenceItem` model (8 fields: id, text, description, image, icon, category, is_distractor, order_index). Expand to 10 fields total |
| 1.2 | `game_design_v3.py` | Expand `SortingDesign`: add `SortingCategoryDesign` (5 fields), `SortingItemDesign` (6 fields incl `correct_category_ids` as LIST). Expand to 10 fields |
| 1.3 | `game_design_v3.py` | Expand `MemoryMatchDesign`: add `MemoryPairDesign` (9 fields incl zone_id). Expand to 9 fields |
| 1.4 | `game_design_v3.py` | Expand `CompareDesign`: 7 fields (expected_categories, subjects, comparison_mode, category_types, exploration_enabled, zoom_enabled, instructions) |
| 1.5 | `game_design_v3.py` | Expand `BranchingDesign`: add `BranchingChoiceDesign` (5 fields), `BranchingNodeDesign` (6 fields). Expand to 4 fields |
| 1.6 | `game_design_v3.py` | Expand `SlimMechanicRef`: add `config_hint: Dict[str,Any]` + `zone_labels_used: List[str]` beyond just `type: str` |
| 1.7 | `types.ts` | Add `ClickToIdentifyConfig` (8 fields), `TracePathConfig` (8 fields), `DragDropConfig` (3 fields). Extend 6 existing config types. Fix `SortingItem.correctCategoryId` → `correct_category_ids: string[]` |
| 1.8 | `state.py` | Add state fields: `sequence_item_images`, `sorting_item_images`, `sorting_category_icons`, `memory_card_images`, `diagram_crop_regions` |

### Phase 2: Tool Implementation (9 fixes, ~300 lines, ~2 files) — Blocks Phase 3

| Fix | File | Description | Mechanic |
|-----|------|-------------|----------|
| 2.1 | `scene_architect_tools.py` | **ADD** `generate_mechanic_content` handler for `memory_match`: generate term-definition pairs from canonical_labels + label_descriptions via LLM | memory_match |
| 2.2 | `scene_architect_tools.py` | **FIX** `description_matching` handler: LLM-powered *functional* description generation (NOT appearance-based), generate 2-3 distractor descriptions | description_matching |
| 2.3 | `scene_architect_tools.py` | **IMPROVE** `sequencing` handler: LLM generates items with id/text/description/order_index, derive correct_order, set layout_mode, add instructions | sequencing |
| 2.4 | `scene_architect_tools.py` | **IMPROVE** `sorting_categories` handler: LLM generates categories (id/name/description/color) + items (id/text/correct_category_ids as list/explanation) | sorting_categories |
| 2.5 | `scene_architect_tools.py` | **IMPROVE** `click_to_identify` handler: generate per-zone functional prompts from label_descriptions, set prompt_style/highlight_style/selection_mode | click_to_identify |
| 2.6 | `scene_architect_tools.py` | **IMPROVE** `trace_path` handler: LLM generates ordered waypoints with descriptions, path_type, show_direction_arrows, particle_theme | trace_path |
| 2.7 | `interaction_designer_tools.py` | **ADD** per-mechanic `enrich_mechanic_content` handlers: sequencing (Kendall tau), sorting (per-category misconceptions), memory (per-pair explanations), click (progressive difficulty), trace (per-waypoint feedback), description (connecting line feedback) | ALL |
| 2.8 | `interaction_designer_tools.py` ~L140-170 | **FIX** `generate_misconception_feedback`: remove drag_drop-biased model (trigger_label + trigger_zone). Add mechanic-specific models: ordering, category_assignment, association, identification | ALL non-drag_drop |
| 2.9 | `interaction_designer_tools.py` ~L357-454 | **ADD** `validate_interactions` content checks for all mechanics | ALL |

### Phase 3: Remaining Prompt Refinements (2 fixes, ~30 lines, ~2 files)

| Fix | File | Description |
|-----|------|-------------|
| 3.5 | `game_designer_v3.py` | Update `submit_game_design` to validate against expanded schemas from Phase 1 |
| 3.6 | `game_design_v3_tools.py` | Update `check_capabilities` to reflect actual tool readiness after Phase 2 |

### Phase 4: Blueprint Assembler Fixes (5 fixes, ~120 lines, ~1 file) — Parallel after Phase 3

| Fix | File | Description | Severity |
|-----|------|-------------|----------|
| 4.1 | `blueprint_assembler_tools.py` L654-662 | **CRITICAL**: Fix scoring/feedback data drop. Convert lists to dicts keyed by mechanic_type | CRITICAL |
| 4.2 | `blueprint_assembler_tools.py` | Forward `mode_transitions[]` and `tasks[]` from interaction specs to blueprint | HIGH |
| 4.3 | `blueprint_assembler_tools.py` | Populate expanded mechanic configs in camelCase: sequencing (layoutMode, cardType, connectorStyle), sorting (sortMode, submitMode), memory (gameVariant, matchType, gridSize, cardBackStyle, showExplanationOnMatch), click (prompts, promptStyle, selectionMode, highlightStyle), trace (waypoints, pathType, drawingMode, particleTheme, showDirectionArrows) | HIGH |
| 4.4 | `blueprint_assembler_tools.py` | Add `validate_blueprint` mechanic-specific config completeness checks | MEDIUM |
| 4.5 | `blueprint_assembler_tools.py` | Add `repair_blueprint` repairs for sequencing, sorting, memory, description_matching | MEDIUM |

### Phase 5: Frontend Schema + Zustand (8 fixes, ~200 lines, ~2 files) — Parallel after Phase 3

| Fix | File | Description | Severity |
|-----|------|-------------|----------|
| 5.1 | `types.ts` | Apply type additions from Fix 1.7 (3 new config types + 6 extensions) | HIGH |
| 5.2 | `types.ts` + `SortingCategories.tsx` | Fix `SortingItem.correctCategoryId` → `correct_category_ids: string[]` (backward compat) | HIGH |
| 5.3 | `useInteractiveDiagramState.ts` ~L1517 | **CRITICAL**: Fix score reset on mode transition: `score: 0` → `score: get().score` | CRITICAL |
| 5.4 | `useInteractiveDiagramState.ts` | Fix `_sceneToBlueprint`: forward `clickToIdentifyConfig`, `tracePathConfig`, `dragDropConfig` | HIGH |
| 5.5 | `useInteractiveDiagramState.ts` ~L458,475,645 | Fix score OVERWRITES in `updatePathProgress`/`updateIdentificationProgress`/`recordDescriptionMatch`: must ADD deltas, never SET | CRITICAL |
| 5.6 | `useInteractiveDiagramState.ts` ~L858 | Fix mode transition `setTimeout` leak: timer never cleaned up | MEDIUM |
| 5.7 | `useInteractiveDiagramState.ts` ~L874 | Fix `transitionToMode`: mutates `modeHistory` in-place (Zustand immutability violation) | MEDIUM |
| 5.8 | `useInteractiveDiagramState.ts` ~L1026 | Fix `advanceToNextTask`: `max_score = actual score` → percentage always 100% | HIGH |

### Phase 6: Frontend Component Enhancements (9 fixes, ~400 lines, ~8 files) — Parallel after Phase 3

| Fix | File | Mechanic | Key Changes |
|-----|------|----------|-------------|
| 6.1 | `SequenceBuilder.tsx` | sequencing | Read `layoutMode`, `cardType`, `connectorStyle` from config. Render image+text cards. Add connecting arrows SVG. Show position numbers. Instructions banner |
| 6.2 | `SortingCategories.tsx` | sorting_categories | Read `sortMode` (bucket/Venn/matrix/column), `submitMode`, `containerStyle`. Category containers: icon, color header, item count. Iterative correction: incorrect items bounce back |
| 6.3 | `MemoryMatch.tsx` | memory_match | Fix CSS flip (opacity → true 3D perspective + rotateY + backface-visibility). Read `gameVariant`, `matchType`, `showExplanationOnMatch`, `cardBackStyle`, `matchedCardBehavior` |
| 6.4 | `HotspotManager.tsx` | click_to_identify | Fix L227-230 zone label leak. Read `clickToIdentifyConfig` (promptStyle, highlightStyle, selectionMode). Info popup on correct. Show zone count |
| 6.5 | `PathDrawer.tsx` | trace_path | Read `tracePathConfig` (pathType, particleTheme, showWaypointLabels). Directional arrows SVG markers. Waypoint info tooltip |
| 6.6 | `DescriptionMatcher.tsx` | description_matching | Fix MC option reshuffle (wrap with `useMemo`). Read `showConnectingLines`, `deferEvaluation`, `descriptionPanelPosition` |
| 6.7 | `DiagramCanvas.tsx` | drag_drop | Read `dragDropConfig` (showLeaderLines, showInfoPanelOnCorrect). Add SVG leader lines |
| 6.8 | `MechanicRouter.tsx` | ALL | Pass new config types to components: `tracePathConfig`, `clickToIdentifyConfig`, `dragDropConfig` |
| 6.9 | Various | Multiple | Fix bugs: MC reshuffle, zone label leak, CSS flip, CompareContrast dead `highlightMatching` field |

### Phase 7: Graph Architecture Redesign (DEFERRED — Large Workstream)

Based on doc 09 (agentic frameworks research, 43 papers):

| Change | Current | Proposed | Research Backing |
|--------|---------|----------|-----------------|
| Graph structure | Flat 8 nodes | Hierarchical 6 sub-graphs | AgentOrchestra (GAIA 89%), HALO |
| Agent pattern | Monolithic ReAct (4-5 tools) | Quality Gate (single-purpose nodes) | AlphaCodium, Brittle Foundations |
| State | 1 TypedDict, 160+ fields | Per-phase types, 10-20 fields | QSAF (cognitive degradation) |
| Asset generation | Sequential ReAct | Parallel Map-Reduce (Send API) | Azure Architecture (~36% latency reduction) |
| Retry | Same agent + temp | Fresh LLM call with feedback summary | Yes-Man Loop prevention |
| Validation | Deterministic only | Deterministic + Cross-model Critic | RouteLLM, ChatEval |
| Model routing | All gemini-2.5-pro | Multi-model (Pro for creative, Flash for execution) | RouteLLM (85% cost reduction) |

**Proposed architecture:**
```
MAIN GRAPH ("Studio")
├── Phase 0: Context (sub-graph) — input_enhancer → DK retriever → router
├── Phase 1: Design (Quality Gate sub-graph) — context_gatherer → designer(LLM) → validator(code) → [retry/submit]
├── Phase 2: Scene (Quality Gate sub-graph) — same pattern, per-scene Map-Reduce inside
├── Phase 3: Interaction (Quality Gate sub-graph) — same pattern
├── Phase 4: Assets (Map-Reduce sub-graph) — asset_planner → Send(per-scene) → collector
└── Phase 5: Blueprint (Quality Gate + Critic sub-graph) — assembler → schema_validator → critic(different model) → [repair/submit]
```

**Migration strategy (incremental, each phase independently testable):**
1. Phase A: Wrap existing agents in sub-graphs with state mapping
2. Phase B: Decompose ReAct agents into Quality Gate patterns
3. Phase C: Add Map-Reduce for asset generation
4. Phase D: Add Critic agent
5. Phase E: Multi-model routing
6. Phase F: Checkpointing at phase boundaries

### Phase 8: New Mechanics (DEFERRED)

| Priority | Mechanic | Cost | Reuses Existing? |
|----------|----------|------|-----------------|
| HIGH | `hotspot_multi_select` | LOW | Extends click_to_identify |
| HIGH | `cloze_fill_blank` | MEDIUM | Uses zone infra + text input |
| HIGH | `spot_the_error` | MEDIUM | Modified diagram comparison |
| HIGH | `predict_observe_explain` | MEDIUM-HIGH | Multi-phase wrapper |
| MEDIUM | `cause_effect_chain` | MEDIUM-HIGH | DAG builder |
| MEDIUM | `process_builder` | HIGH | Full graph editor |
| MEDIUM | `annotation_drawing` | HIGH | Freehand drawing (new) |

---

## 5. DEPENDENCY GRAPH

```
Phase 0 (Infrastructure)
    │
    ▼
Phase 1 (Schemas)
    │
    ▼
Phase 2 (Tools)
    │
    ▼
Phase 3 (Prompts)
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 4 (Blueprint)    Phase 5 (Frontend Types + Zustand)
    │                      │
    │                      ▼
    │              Phase 6 (Frontend Components)
    │                      │
    └──────────┬───────────┘
               ▼
         E2E Testing
               │
               ▼
    Phase 7 (Graph Redesign)  ←── Independent workstream
               │
               ▼
    Phase 8 (New Mechanics)   ←── After Phase 7
```

**Phases 4, 5, 6 can run in PARALLEL** after Phase 3.

---

## 6. DOMAIN KNOWLEDGE UTILIZATION

**Current: 9.2%** (6/65 agent-field pairs consumed)

DK retriever produces rich data that downstream agents ignore:

| DK Field | Available? | Consumed By | Should Be Consumed By |
|----------|-----------|-------------|----------------------|
| `canonical_labels` | YES | game_designer, scene_architect | ✓ Already used |
| `label_descriptions` | YES | NOBODY | click_to_identify (prompts), description_matching (descriptions), memory_match (definitions) |
| `sequence_flow_data` | YES | game_designer (check_capabilities only) | scene_architect (sequencing items), trace_path (waypoints) |
| `content_characteristics` | YES | game_designer (analyze_pedagogy only) | All agents (content type context) |
| `hierarchical_relationships` | YES | game_designer (hierarchy groups only) | scene_architect (zone_hierarchy), blueprint (zoneGroups) |
| `comparison_data` | YES | game_designer (check_capabilities only) | scene_architect (compare categories), compare_contrast config |
| `categorization_data` | NO (not in schema) | — | sorting_categories (items+categories) |
| `term_definition_pairs` | NO (derivable) | — | memory_match (pairs) |
| `process_sequences` | NO (not in schema) | — | sequencing (items), trace_path (waypoints) |
| `causal_relationships` | NO (not in schema) | — | branching_scenario (decision consequences) |
| `suggested_reveal_order` | YES | NOBODY | hierarchical (reveal sequence) |
| `scene_hints` | YES | NOBODY | game_designer (multi-scene planning) |
| `query_intent` | YES | NOBODY | game_designer (depth, progression) |

**Fix (Phase 2):** Update `v3_context.py` to inject `label_descriptions`, `sequence_flow_data`, `comparison_data` into tool context. Update tool handlers to consume them.

---

## 7. SCHEMA FIELD GAP COUNTS

### Backend (~124 field gaps)

| Schema | Existing Fields | Required Fields | Gap |
|--------|----------------|-----------------|-----|
| SequenceDesign | 4 | ~25 | ~21 |
| SortingDesign | 4 | ~25 | ~21 |
| BranchingDesign | 6 | ~40+ | ~34 |
| CompareDesign | 3 | ~20+ | ~17 |
| MemoryMatchDesign | 4 | ~30+ | ~26 |
| SlimMechanicRef | 1 (type only) | ~3 | ~2 |
| DomainKnowledge TypedDict | missing 3 | — | 3 |

### Frontend (~94 field gaps)

| Interface | Gap |
|-----------|-----|
| SequenceConfig | ~9 new fields |
| SortingConfig | ~10 new fields |
| MemoryMatchConfig | ~11 new fields |
| BranchingConfig | ~10 new fields |
| CompareConfig | ~10 new fields |
| DescriptionMatchingConfig | ~7 new fields |
| ClickToIdentifyConfig | ENTIRE TYPE MISSING (~8 fields) |
| TracePathConfig | ENTIRE TYPE MISSING (~10 fields) |
| DragDropConfig | ENTIRE TYPE MISSING (~3 fields) |
| Base type fields | ~16 |

---

## 8. CRITICAL FRONTEND BUGS (6)

| Bug | File | Line | Issue | Mechanic |
|-----|------|------|-------|----------|
| MC option reshuffle | DescriptionMatcher.tsx | ~L420-450 | `sort(() => Math.random() - 0.5)` in render = re-shuffle every re-render | description_matching |
| Zone label leak | HotspotManager.tsx | L227-230 | `any_order` mode leaks zone labels in prompt display | click_to_identify |
| Score reset on transition | useInteractiveDiagramState.ts | L1517 | `score: 0` on mode transition prevents cumulative scoring | Multi-mechanic |
| CSS flip not 3D | MemoryMatch.tsx | — | Uses opacity toggle, not perspective + transform-style: preserve-3d | memory_match |
| Score overwrites | useInteractiveDiagramState.ts | L458,475,645 | 3 actions REPLACE score instead of accumulating deltas | trace_path, click, description |
| advanceToNextTask | useInteractiveDiagramState.ts | L1026 | max_score = actual score → percentage always 100% | Multi-scene |

---

## 9. VERIFICATION PLAN

### E2E Test Prompts

```bash
# Test 1: drag_drop (regression)
"Label the main parts of a flower"

# Test 2: sequencing
"Arrange the stages of mitosis in order: prophase, metaphase, anaphase, telophase"

# Test 3: sorting_categories
"Classify these animals as vertebrates or invertebrates: eagle, spider, salmon, jellyfish, frog, ant"

# Test 4: memory_match
"Match these cell organelles with their functions"

# Test 5: click_to_identify
"Identify each chamber and valve of the human heart"

# Test 6: trace_path
"Trace the path of blood flow through the human heart"

# Test 7: description_matching
"Match descriptions to the parts of the digestive system"

# Test 8: multi-mechanic
"Create a comprehensive game about the human digestive system"
```

### Per-Run Checklist

1. All pipeline stages complete (no errors)
2. `game_designer` produces mechanic-specific configs (not just type)
3. `scene_architect` calls `generate_mechanic_content` for every non-drag_drop mechanic
4. `interaction_designer` calls `enrich_mechanic_content` for every mechanic
5. Blueprint has populated mechanic configs (not empty dicts)
6. Blueprint has scoring AND feedback per mechanic (not generic "Correct!/Try again")
7. Game page renders correct interaction component
8. Component reads config (items, categories, pairs, waypoints, etc.)
9. Scoring works (correct actions add score, don't overwrite)
10. Mode transitions work for multi-mechanic scenes
11. Scene transitions work for multi-scene games

---

## 10. SUMMARY

| Phase | Files | Est. Lines | Status | Dependency |
|-------|-------|-----------|--------|------------|
| 0: Critical Infrastructure | ~6 | ~80 | TODO | None (FIRST) |
| 1: Schema Expansion | ~6 | ~400 | TODO | Phase 0 |
| 2: Tool Implementation | ~2 | ~300 | TODO | Phase 1 |
| 3: Prompt Refinements | ~2 | ~30 | TODO (2 remaining) | Phase 2 |
| 4: Blueprint Assembler | ~1 | ~120 | TODO | Phase 3 |
| 5: Frontend Schema+Zustand | ~2 | ~200 | TODO | Phase 3 |
| 6: Frontend Components | ~8 | ~400 | TODO | Phase 3 |
| 7: Graph Architecture | ~10 | ~500+ | DEFERRED | Phase 6 |
| 8: New Mechanics | ~15+ | ~1000+ | DEFERRED | Phase 7 |
| **Total (Phases 0-6)** | **~27** | **~1530** | | |

### Key Files Touched

| File | Phases |
|------|--------|
| `backend/app/routes/generate.py` | 0 |
| `backend/app/agents/graph.py` | 0 |
| `backend/app/agents/state.py` | 0, 1 |
| `backend/app/tools/game_design_v3_tools.py` | 0, 3 |
| `backend/app/agents/schemas/game_design_v3.py` | 1 |
| `backend/app/tools/scene_architect_tools.py` | 2 |
| `backend/app/tools/interaction_designer_tools.py` | 2 |
| `backend/app/tools/blueprint_assembler_tools.py` | 4 |
| `frontend/.../types.ts` | 1, 5 |
| `frontend/.../hooks/useInteractiveDiagramState.ts` | 5 |
| `frontend/.../interactions/SequenceBuilder.tsx` | 6 |
| `frontend/.../interactions/SortingCategories.tsx` | 6 |
| `frontend/.../interactions/MemoryMatch.tsx` | 6 |
| `frontend/.../interactions/HotspotManager.tsx` | 6 |
| `frontend/.../interactions/PathDrawer.tsx` | 6 |
| `frontend/.../interactions/DescriptionMatcher.tsx` | 6 |
| `frontend/.../DiagramCanvas.tsx` | 6 |
| `frontend/.../MechanicRouter.tsx` | 6 |

---

*Cross-referenced from: docs/audit/00-22 (19 documents), 43 academic papers, 15 research docs*
*Applied fixes: ~14. Remaining: ~86+. Grand total unique issues: ~370+*
