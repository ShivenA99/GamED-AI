# V4 Logical Flow Audit

**Date**: 2026-02-14
**Scope**: Logical flow issues, edge cases, and architectural problems in the V4 pipeline implementation plan
**Files Audited**:
- `docs/v4_implementation_plan_final.md`
- `docs/v4_formal_graph_rules.html`
- `docs/audit/14_v4_architecture_refined.md`
- `backend/app/tools/blueprint_assembler_tools.py`
- `backend/app/agents/blueprint_assembler_v3.py`
- `backend/app/routes/generate.py`
- `frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts`
- `frontend/src/components/templates/InteractiveDiagramGame/types.ts`
- `frontend/src/components/templates/InteractiveDiagramGame/engine/sceneManager.ts`
- `frontend/src/components/templates/InteractiveDiagramGame/engine/schemas/blueprintSchema.ts`

---

## Summary

27 findings across 6 CRITICAL, 8 HIGH, 9 MEDIUM, 4 LOW severity levels.

| Severity | Count |
|----------|-------|
| CRITICAL | 6 |
| HIGH | 8 |
| MEDIUM | 9 |
| LOW | 4 |
| **Total** | **27** |

---

## Findings

### Finding 1: Phase 0 Parallel vs Sequential Contradiction (MEDIUM)

**Audit Question**: #11 — Phase 0 data flow (input_analyzer + dk_retriever parallel vs sequential)

**Problem**: The V4 plan says input_analyzer and dk_retriever run in parallel (architecture doc line 122-124: "PARALLEL"), but the architecture doc also says dk_retriever "reads content_structure" from input_analyzer (line 168-169: "Enhanced: reads content_structure to know what to search for"). These two statements are contradictory. If dk_retriever needs content_structure (which is output by input_analyzer), they cannot be parallel.

**Evidence**:
- `docs/audit/14_v4_architecture_refined.md` line 148: "No changes from v4 brainstorm. Two parallel stages"
- Same file line 168: "Enhanced: reads content_structure to know what to search for"
- `docs/v4_implementation_plan_final.md` line 377-378: "Two parallel nodes: input_analyzer + dk_retriever"

**Impact**: If run in parallel, dk_retriever will NOT have content_structure and will use a generic search strategy, reducing DK quality. If run sequentially, Phase 0 latency increases by ~2-5 seconds.

**Resolution**: Make them sequential: `input_analyzer -> dk_retriever`. The latency cost (~2-5s) is minimal compared to the quality loss of generic search. Alternatively, make dk_retriever work in two passes: a generic pass in parallel, then a refinement pass after content_structure is available. The plan must pick one and be consistent.

---

### Finding 2: Zone ID Chicken-and-Egg Problem (CRITICAL)

**Audit Question**: #2 — Zone labels vs zone_id mapping timing

**Problem**: Zone IDs (`zone_{scene}_{index}`) are generated during Phase 4 (blueprint assembly) via `_make_id("zone", str(scene_number), label)`. But several Phase 2 outputs reference zone IDs directly:
- trace_path waypoints need `zoneId` fields
- click_to_identify prompts need `zoneId` fields
- hierarchical zoneGroups need `parentZoneId` and `childZoneIds`
- compare_contrast `diagramA`/`diagramB` zones need `id` fields
- temporal constraints need `zone_a` and `zone_b` IDs

Phase 2 content generators produce content using **label strings** (e.g., "Right Atrium"), not zone IDs. The translation from label to zone ID happens in Phase 4 blueprint assembly. This is correct as designed. However, the plan does not explicitly document this label-to-ID translation contract, and the existing V3 code in `blueprint_assembler_tools.py` shows this translation is fragile.

**Evidence**:
- `blueprint_assembler_tools.py` lines 622-637: trace_path waypoints use `_make_id("zone", str(scene_number), wp)` where `wp` is a label string
- `blueprint_assembler_tools.py` lines 660-673: click_to_identify prompts use `zone_by_label.get(lbl, "")` with empty string fallback
- The `_make_id` function (line 28-31) generates `zone_{slug}` from label text, which is sensitive to casing, spaces, and special characters

**Impact**: If label strings in Phase 2 content do not exactly match the labels in Phase 1 GamePlan (even differing in case or whitespace), zone ID resolution will fail silently, producing empty `zoneId` fields or wrong mappings. The V3 code already has `_normalize_label` and `_build_zone_lookup` to mitigate this, but mismatches still happen.

**Resolution**:
1. The V4 plan must formalize a **label normalization contract**: all label references across all phases use the exact string from `GamePlan.all_zone_labels` (canonical form). Content validators must reject content that references labels not in the canonical list.
2. Zone ID generation must be deterministic from the canonical label, not from the content generator's rendering of that label.
3. `zone_matcher.py` (Phase 2 helper) should expose a `canonical_to_zone_id(label, scene_number) -> str` function used by the blueprint assembler. This function uses the same normalization as the zone detection matcher.

---

### Finding 3: Parallel Per-Mechanic Content Generation Ordering Problem (HIGH)

**Audit Question**: #1 — Ordering problem with parallel per-mechanic content generation

**Problem**: Phase 2 runs content generators in parallel per mechanic within a scene (via Send API). This means mechanic A's content may be generated before mechanic B's, or vice versa. For most mechanics this is fine since they are independent. But there are cases where mechanic content has implicit ordering dependencies:

1. **drag_drop + description_matching** in the same scene: description_matching generates descriptions for zones. If the labels or zone names used in the description differ from those in drag_drop, the frontend will show inconsistencies. The scene_context_builder mitigates this by providing shared zone labels, but the content generators still independently decide wording.

2. **Hierarchical mechanics**: A parent mechanic and child mechanic in the same scene share zone labels (parent has top-level, child has sub-zones). The plan uses `parent_mechanic_id` to link them, but both run in parallel. If the child's content references parent zone details that haven't been generated yet, this is a problem.

3. **Cross-mechanic score allocation**: Two mechanics in the same scene independently set their `max_score`, but the interaction_designer (Step 4) must reconcile them against the GamePlan's `scene_max_score`. If content generators change `expected_item_count` during generation, the score arithmetic may fail.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 388-393: "FOR EACH mechanic (via Send API): content_generator (LLM) -> content_validator -> [retry or pass]"
- `docs/audit/14_v4_architecture_refined.md` lines 579-600: scene-awareness mechanism provides shared context, but content generators are still parallel and independent

**Impact**: Mostly mitigated by scene_context_builder (shared labels, DK). The interaction_designer runs AFTER all content generators complete (Step 4), which handles cross-mechanic reconciliation. However, hierarchical parent/child content should ideally be sequenced (parent first, then child), and content generators should not be allowed to change `expected_item_count` from the GamePlan.

**Resolution**:
1. Add a validator rule: content generator output `len(items)` must equal `ContentBrief.expected_item_count`. If the LLM generates a different count, the content_validator rejects it with feedback.
2. For hierarchical parent/child mechanics, the plan should either (a) sequence them (parent first) or (b) ensure the child's prompt includes the parent's zone labels from GamePlan (already available in scene_context), not the parent's generated content.

---

### Finding 4: Compare Contrast Dual-Image Flow Gap (CRITICAL)

**Audit Question**: #3 — Compare contrast dual-image flow

**Problem**: Compare contrast requires TWO diagram images (`diagramA` and `diagramB`) with independent zone detection. The plan addresses this in Phase 3 with dual `DiagramAssetNeed` entries that run in parallel. However, there are several gaps:

1. **Second image spec origin**: The `second_image_spec` is generated by the compare_contrast content generator in Phase 2 (lines 651-668 of architecture doc). This means the image search query and expected labels for the second diagram are LLM-generated, not deterministically derived from the GamePlan. If the content generator produces a poor `second_image_spec`, the entire second diagram fails.

2. **Zone allocation**: Compare contrast needs distinct zone sets for each diagram. The GamePlan's `ScenePlan.zone_labels` is a flat list. There is no explicit partition telling which labels belong to diagram A vs diagram B. The content generator must produce this partition (`subject_a.zone_labels` and `subject_b.zone_labels`), but the plan does not validate that these partition the scene's zone_labels correctly.

3. **Existing V3 hack**: `blueprint_assembler_tools.py` lines 910-928 synthesizes diagramA/diagramB by splitting zones in half when upstream data is missing. This is incorrect for real compare_contrast and must be eliminated in V4.

4. **Asset manifest construction**: `docs/audit/14_v4_architecture_refined.md` lines 869-880 show the second diagram using `cc.second_image_spec`, but the `expected_labels` come from `second_image_spec.must_include_structures`. This must match `subject_b.zone_labels` exactly.

**Evidence**:
- Architecture doc lines 651-668: content generator prompt for compare_contrast includes `second_image_spec`
- Architecture doc lines 869-880: asset orchestrator builds `second_diagram` from `cc.second_image_spec`
- `blueprint_assembler_tools.py` lines 910-928: V3 synthesizes by splitting zones in half
- FOL rules (v4_formal_graph_rules.html): `diagramA != null && diagramB != null` with zones having `x/y/w/h`

**Impact**: Without explicit validation of the zone partition and second_image_spec quality, compare_contrast will fail in most cases. The zone detection for diagram B may not find the expected labels, and the blueprint assembler has no way to recover.

**Resolution**:
1. Add `zone_labels_a: list[str]` and `zone_labels_b: list[str]` fields to `MechanicPlan` for compare_contrast (or to ContentBrief).
2. `game_plan_validator` must check that `zone_labels_a + zone_labels_b` covers `zone_labels_used` and that they are disjoint.
3. `content_validator` for compare_contrast must check that `subject_a.zone_labels == zone_labels_a` and `subject_b.zone_labels == zone_labels_b`.
4. `second_image_spec.must_include_structures` must equal `zone_labels_b`.
5. Blueprint assembler must use explicit diagramA/diagramB from assets, never the V3 "split in half" fallback.

---

### Finding 5: Hierarchical Mode Composability Undefined (HIGH)

**Audit Question**: #4 — Hierarchical mode + mechanic composability

**Problem**: The plan states "hierarchical is a MODE on drag_drop, not a standalone mechanic" (line 12). But the architecture shows hierarchical as a connection pattern between mechanics (parent_mechanic_id linking), not as a property of drag_drop. These are two different things:

1. **Hierarchical as MODE**: frontend `types.ts` has `'hierarchical'` as an InteractionMode. The Zustand store has `hierarchyState: HierarchyState | null` for zone reveal logic. The blueprint has `zoneGroups[]` with `parentZoneId` and `childZoneIds`.

2. **Hierarchical as CONNECTION PATTERN**: The GamePlan uses `parent_mechanic_id` on MechanicPlan and `trigger: "parent_completion"` on MechanicConnection. This is a graph wiring concept, not a UI mode.

The plan conflates these. When the game designer creates a hierarchical game, it creates two separate mechanics (parent drag_drop + child click_to_identify) connected by `parent_completion`. But the frontend expects `interactionMode: 'hierarchical'` and `zoneGroups[]`, which is a SINGLE-mechanic UI concept (one drag_drop mode with progressive zone reveal).

**Evidence**:
- `docs/v4_implementation_plan_final.md` line 12: "Hierarchical is a MODE on drag_drop"
- `docs/audit/14_v4_architecture_refined.md` lines 1001-1025: hierarchical example uses two mechanics connected by parent_completion
- `frontend/types.ts` line 9: `'hierarchical'` is an InteractionMode
- `frontend/hooks/useInteractiveDiagramState.ts` lines 119-120: hierarchyState for progressive zone reveal
- FOL rules: R4.1-R4.8 validate hierarchy tree structure

**Impact**: The blueprint assembler must decide: does hierarchical generate `interactionMode: 'hierarchical'` (single-mode progressive reveal) OR `modeTransitions: [{from: 'drag_drop', to: 'click_to_identify', trigger: 'parent_completion'}]` (multi-mode sequential)? These produce different frontend behavior.

**Resolution**: Clarify the two interpretations:
1. **Intra-mechanic hierarchy** (MODE): Parent zones reveal child zones within the SAME drag_drop interaction. Produces `interactionMode: 'hierarchical'`, `zoneGroups[]`. No mode transition needed. This is what `label_hierarchy` in GamePlan maps to.
2. **Inter-mechanic hierarchy** (CONNECTION): Completing one mechanic unlocks another. Produces `modeTransitions` with `trigger: 'parent_completion'`. Uses `parent_mechanic_id`.

Both must be supported. The plan should explicitly state which `label_hierarchy` maps to (option 1) and which `parent_mechanic_id` maps to (option 2), and how they compose when both are present.

---

### Finding 6: Multi-Scene Transition Trigger Formalization (HIGH)

**Audit Question**: #5 — Multi-scene transitions (who generates triggers, are they formalized)

**Problem**: Scene transitions are defined in GamePlan via `SceneTransition` (type, min_score_pct). But the frontend's scene flow is driven by a different mechanism: `sceneManager.ts` has `getSceneAction()` which returns `advance_task | advance_scene | complete_game` based on task/scene index arithmetic, not based on score gates or transition types.

The plan says scene transitions can be `"auto" | "button" | "score_gate"`, but:
1. The frontend `sceneManager.ts` does not check transition type or score gate.
2. The `SceneFlowGraph` (referenced in the import at line 38 of useInteractiveDiagramState.ts via `getNextSceneId`) is not shown in the plan.
3. The blueprint assembler must translate GamePlan's `SceneTransition` into a frontend-compatible representation, but the current `sceneToBlueprint` function does not read any transition config.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 398-401: `SceneTransition` schema with `transition_type` and `min_score_pct`
- `frontend/engine/sceneManager.ts` lines 26-53: `getSceneAction` uses index arithmetic only
- `frontend/hooks/useInteractiveDiagramState.ts` line 38: imports `getNextSceneId` from `sceneFlowGraph`

**Impact**: Score-gated scene transitions will not work. The frontend will always auto-advance to the next scene regardless of score. `button` transitions (user clicks "Next Scene") have no UI trigger point.

**Resolution**:
1. The plan must specify how `SceneTransition.transition_type` maps to the frontend:
   - `"auto"` -> automatic advance (current behavior)
   - `"button"` -> show "Continue to Next Scene" button in game controls
   - `"score_gate"` -> check `score >= min_score_pct * scene_max_score` before enabling advance
2. `sceneManager.ts` must be updated to accept transition rules.
3. The `SceneFlowGraph` must be formalized and either included in the blueprint or generated client-side from the scene list + transitions.

---

### Finding 7: Score Rollup Consistency (HIGH)

**Audit Question**: #6 — Score rollup consistency between design and content

**Problem**: Score arithmetic has THREE layers of truth:
1. **GamePlan** (Phase 1): `expected_item_count * points_per_item = max_score` per mechanic; `sum(mechanic.max_score) = scene_max_score`; `sum(scene_max_score) = total_max_score`.
2. **Content** (Phase 2): content generators produce actual items. The ACTUAL item count may differ from `expected_item_count`.
3. **Interaction designer** (Phase 2): produces `ScoringRules` per mechanic with `points_per_correct` and `max_score`.

The plan has three validator checks:
- `game_plan_validator` checks arithmetic within the GamePlan (Phase 1).
- `content_validator` checks item count matches brief.
- `interaction_validator` checks scoring arithmetic.

But there is no validator that checks **content item count vs GamePlan expected_item_count** and recalculates the score chain. If a content generator produces 8 items when the GamePlan says 9, the score arithmetic breaks.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 262-263: content_validator checks `items >= 3` (minimum) and `len(items) == brief.expected_item_count`
- Architecture doc line 464: game_plan_validator checks `expected * points_per_item = max_score`
- Architecture doc lines 570-571: interaction_validator checks score arithmetic

**Impact**: If content_validator enforces `len(items) == expected_item_count`, this is caught. The plan does include this check (line 262). However, the interaction_designer receives the ACTUAL content and may adjust `max_score` to match actual item count, creating a discrepancy with the GamePlan. The blueprint assembler must use the interaction_designer's scores, not the GamePlan's.

**Resolution**:
1. Content validator MUST enforce `len(items) == expected_item_count` strictly. If violated, retry.
2. If after retry the content generator still produces a different count, the interaction_designer's scores become authoritative, and the blueprint assembler must propagate those (not the GamePlan's).
3. Add a final cross-check in `blueprint_validator` that `sum(mechanic.max_score from interaction_designer) == total_max_score`. If mismatched, emit a WARNING and adjust total_max_score.

---

### Finding 8: Empty Scenes (Content-Only, No Zones) Handling (CRITICAL)

**Audit Question**: #8 — Empty scenes (no zones needed) handling

**Problem**: Several mechanics do not require diagram zones: sequencing, sorting_categories, memory_match, branching_scenario. A scene composed entirely of these mechanics would have `needs_diagram: false`, `zone_labels: []`, and NO zones in the blueprint.

But the V3 blueprint submit gate (`blueprint_assembler_tools.py` lines 2065-2069) rejects scenes with no zones:
```python
if not scene_zones:
    critical_issues.append(f"Scene {sn}: no zones")
if not scene_labels:
    critical_issues.append(f"Scene {sn}: no labels")
```

Furthermore, the frontend's `useInteractiveDiagramState.ts` uses zone/label counts for completion detection. When `taskLabelCount` is 0 (no labels), the completion check `placedCorrectCount >= taskLabelCount` would be `0 >= 0 = true`, immediately completing the scene.

**Evidence**:
- `blueprint_assembler_tools.py` lines 2065-2069: submit gate rejects no-zone scenes
- `frontend/hooks/useInteractiveDiagramState.ts` line 85: `taskLabelCount: _getTaskLabelCount(state) ?? state.blueprint?.labels.length`
- Per-mechanic asset needs matrix (architecture doc lines 108-111): sequencing, sorting, memory_match, branching have "NONE" for primary asset
- `docs/v4_implementation_plan_final.md` lines 281-282: "content_only_mechanics_dont_need_diagram: true"

**Impact**: Content-only scenes will fail at the submit gate AND at frontend completion detection. This is a fundamental gap.

**Resolution**:
1. Blueprint validator must NOT require zones/labels for content-only scenes. Check: if ALL mechanics in a scene are content-only (no `needs_diagram`), zones and labels are OPTIONAL.
2. Frontend completion detection must use **per-mechanic completion** (from `sequencingProgress.isComplete`, `sortingProgress.isComplete`, etc.), not `placedCorrectCount >= taskLabelCount`.
3. The V4 `blueprint_assembler.py` must set `diagram.assetUrl = null` (or omit diagram) for content-only scenes and provide a placeholder or no diagram UI on the frontend.
4. `sceneToBlueprint` must handle `scene.zones = []` and `scene.labels = []` gracefully.

---

### Finding 9: Distractor Labels Flow and Scope (MEDIUM)

**Audit Question**: #7 — Distractor labels usage and flow to frontend

**Problem**: Distractors are defined at the global level in `GamePlan.distractor_labels: list[str]`. But:
1. Which scenes get which distractors? The plan does not specify per-scene distractor assignment.
2. Should distractors be mechanic-specific? Sequencing has `is_distractor` on items, sorting has categories, memory_match has extra pairs. These are different from zone-based distractors.
3. FOL rule R6.3 says "Distractor disjoint" (distractors must not overlap with real labels). But this check is only at Phase 4, not Phase 1 when the GamePlan is validated.

**Evidence**:
- `docs/v4_implementation_plan_final.md` line 146: `distractor_labels: list[str] = []` at GamePlan level
- Architecture doc line 622: sequencing items have `is_distractor: false` per item
- FOL rules R6.3: distractor disjoint check in `blueprint_validator`
- V3 code: `blueprint_assembler_tools.py` creates `DistractorLabel` objects with `isDistractor: True`

**Impact**: Global distractors work for drag_drop (extra labels in the tray) but are meaningless for content-only mechanics. Per-mechanic distractors (e.g., distractor sequencing items) are a separate concept. The plan conflates them.

**Resolution**:
1. `game_plan_validator` should check R6.3 (distractors disjoint from zone_labels) at Phase 1, not just Phase 4.
2. Global `distractor_labels` apply ONLY to zone-based mechanics (drag_drop, click_to_identify). For content-only mechanics, distractors are generated as part of their content (e.g., `is_distractor` on sequencing items).
3. Blueprint assembler assigns global distractors to scenes that have zone-based mechanics. Content-only scenes get no global distractors.

---

### Finding 10: Retry State Cleanup Behavior (HIGH)

**Audit Question**: #9 — Retry state cleanup behavior

**Problem**: The plan specifies "fresh LLM call each time with validator feedback" for retries (max 2 per stage). But with per-phase state isolation and Map-Reduce parallelism, retry state management is complex:

1. **Phase 1 retry**: game_designer retry replaces the entire `game_plan` in DesignState. Clean.
2. **Phase 2 retry (content)**: A single mechanic's content generator fails validation. The retry must re-run ONLY that mechanic's content_generator, not all mechanics in the scene. But the Send API spawns parallel tasks. If task 2 of 4 fails, tasks 1, 3, 4 have already completed. The retry must re-run task 2 alone and merge its result with the existing results from 1, 3, 4.
3. **Phase 2 retry (interaction)**: If interaction_designer fails, it re-runs with all mechanic contents (already finalized). Clean.
4. **Phase 3 retry (assets)**: If zone detection fails for one asset, the retry must re-run that specific asset chain. Similar to #2.

The plan does not describe how partial Map-Reduce retry works. LangGraph's Send API creates independent branches. When one branch fails and retries, the reducer function must correctly merge the retried result with the previously succeeded results.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 388-393: nested Send API for per-mechanic
- `docs/v4_implementation_plan_final.md` lines 319: "Retry: validator feedback -> fresh LLM call (max 2 retries)"
- Phase 5.4: "content_generator (LLM) -> content_validator -> [retry or pass]"

**Impact**: Without proper partial retry, a failed mechanic content generator could cause the entire scene to re-run (wasting successful results) or, worse, produce a merge conflict where the reducer overwrites successful results with stale data.

**Resolution**:
1. The Quality Gate pattern (LLM -> validator -> retry) must be WITHIN each Send branch, not outside it. Each spawned mechanic task has its own retry loop: `content_gen -> validator -> if fail: retry content_gen (same branch) -> validator -> if fail: emit error for this mechanic`.
2. The reducer function must use `reduce_by_key(mechanic_id)` to merge results. If a mechanic retried, its latest result replaces the previous.
3. Explicitly state: the Send API does NOT retry the entire parallel batch. Each branch is independent and retries internally.

---

### Finding 11: v4ToBlueprint Adapter Complexity (CRITICAL)

**Audit Question**: #10 — Frontend v4ToBlueprint adapter complexity and elimination feasibility

**Problem**: The plan says "No component changes needed if blueprint shape matches InteractiveDiagramBlueprint" (line 472). But the V4 output is `GameSpecification`, and the frontend expects `InteractiveDiagramBlueprint`. These are different shapes:

| V4 GameSpecification | Frontend InteractiveDiagramBlueprint |
|---|---|
| `scenes[].mechanics[].config` (per-mechanic Pydantic) | `blueprint.sequenceConfig`, `blueprint.sortingConfig`, etc. (flat at root) |
| `scenes[].scoring_rules` (per mechanic, from interaction_designer) | `blueprint.scoringStrategy`, `blueprint.mechanics[].scoring` |
| `scene_transitions[]` (explicit transitions) | `blueprint.game_sequence.scenes[]` (implicit in order) |
| `hierarchical_config` (global mode config) | `blueprint.zoneGroups[]`, `blueprint.interactionMode: 'hierarchical'` |
| `scenes[].zones[].id` (zone IDs) | `blueprint.diagram.zones[].id` (nested under diagram) |

The `sceneToBlueprint` function in `engine/sceneManager.ts` already does scene-to-blueprint conversion, but it expects a `GameScene` object (current multi-scene format), not a `GameSpecification.SceneSpec`. The adapter would need to convert between these.

**Evidence**:
- `frontend/engine/sceneManager.ts` lines 63-146: `sceneToBlueprint` expects GameScene with specific field names
- `docs/v4_implementation_plan_final.md` lines 104-117: GameSpecification schema
- `frontend/types.ts`: InteractiveDiagramBlueprint, GameScene, Mechanic interfaces

**Impact**: Either (a) the V4 blueprint_assembler must output EXACTLY the `InteractiveDiagramBlueprint` shape (making GameSpecification a backend-only intermediate), or (b) a `v4ToBlueprint` adapter is needed on the frontend. Option (a) is better because it eliminates the adapter, but it means the blueprint_assembler must know the exact frontend shape, defeating the purpose of GameSpecification as a clean contract.

**Resolution**: The plan should take option (a): the V4 deterministic `blueprint_assembler.py` outputs the `InteractiveDiagramBlueprint` JSON directly. `GameSpecification` is a backend-only schema that the assembler reads; the output is `InteractiveDiagramBlueprint`. This eliminates the need for a frontend adapter.

To make this work:
1. `InteractiveDiagramBlueprint` becomes the actual contract (not GameSpecification).
2. The assembler translates: `GameSpecification.scenes[] -> game_sequence.scenes[]` with per-scene configs promoted to the right positions.
3. Add a Zod validator on the frontend that validates the blueprint JSON on receipt, catching any assembler bugs before game init.

---

### Finding 12: Observability Gap for V4 Agents (HIGH)

**Audit Question**: #12 — Observability gap for V4 agents

**Problem**: V4 uses sub-graphs (phase0_graph, phase1_graph, etc.) compiled as separate StateGraphs and embedded in the main graph. The current observability system (`instrumentation.py`, `PipelineView.tsx`) is designed for flat graph topologies with named agent nodes. Sub-graph nodes appear as a single node in the parent graph.

Specifically:
1. `instrumentation.py` registers agents by name. V4's nested content_generators (spawned via Send) all have the same name but different inputs. The instrumentation must differentiate "content_generator for scene_1/sequencing" from "content_generator for scene_1/sorting".
2. `PipelineView.tsx` has hardcoded `AGENT_METADATA` and `GRAPH_LAYOUT` for V3 agents. V4 needs new metadata and layout.
3. `routes/generate.py` line 220-279: `_build_agent_outputs()` hardcodes V3 agent names. V4 agent names will be different.
4. LangGraph's `astream_events` for nested sub-graphs emits events with namespaced names (e.g., `phase2_content:content_generator`), not flat names.

**Evidence**:
- `backend/app/routes/generate.py` lines 220-279: hardcoded V3 agent names
- `docs/v4_implementation_plan_final.md` lines 465-468: instrumentation briefly mentioned but not detailed
- Frontend PipelineView uses `AGENT_METADATA` dict keyed by agent name

**Impact**: Without proper instrumentation, V4 runs will appear as a black box: no per-agent timing, no token tracking, no cost breakdown, no ReAct trace display.

**Resolution**:
1. Use LangGraph's hierarchical event naming: `phase2_content:scene_1:content_generator_sequencing`. Register these compound names in instrumentation.
2. Add a `V4_AGENT_METADATA` map in `PipelineView.tsx` with the V4 topology layout.
3. `routes/generate.py` must have a V4-specific `_build_agent_outputs()` function that understands sub-graph naming.
4. For Map-Reduce spawned nodes, include `mechanic_id` and `scene_id` in the instrumentation metadata so the frontend can display per-mechanic timelines.

---

### Finding 13: MechanicConnection Trigger Type Mismatch (HIGH)

**Audit Question**: Additional finding from cross-referencing schemas

**Problem**: The V4 GamePlan's `MechanicConnection.trigger` supports 5 values: `"completion" | "score_threshold" | "user_choice" | "time_elapsed" | "parent_completion"`. But the frontend's `ModeTransitionTrigger` type has 14 values (see `types.ts` lines 25-40). The V4 plan does not specify how the 5 backend triggers map to the 14 frontend triggers.

**Evidence**:
- `docs/v4_implementation_plan_final.md` line 394: MechanicConnection trigger has 5 options
- `frontend/types.ts` lines 25-40: ModeTransitionTrigger has 14 options including `all_zones_labeled`, `path_complete`, `percentage_complete`, `specific_zones`, `identification_complete`, `sequence_complete`, `sorting_complete`, `memory_complete`, `branching_complete`, `compare_complete`, `description_complete`

**Impact**: The blueprint assembler must translate 5 generic triggers into 14 specific triggers based on the mechanic type. For example, `completion` on a sequencing mechanic becomes `sequence_complete`, `completion` on drag_drop becomes `all_zones_labeled`. Without this mapping, the frontend's `evaluateTransitions` function will never fire.

**Resolution**: Define an explicit mapping in the blueprint assembler:
```python
TRIGGER_MAP = {
    ("completion", "drag_drop"): "all_zones_labeled",
    ("completion", "trace_path"): "path_complete",
    ("completion", "click_to_identify"): "identification_complete",
    ("completion", "sequencing"): "sequence_complete",
    ("completion", "sorting_categories"): "sorting_complete",
    ("completion", "memory_match"): "memory_complete",
    ("completion", "branching_scenario"): "branching_complete",
    ("completion", "compare_contrast"): "compare_complete",
    ("completion", "description_matching"): "description_complete",
    ("score_threshold", ANY): "percentage_complete",  # with triggerValue
    ("time_elapsed", ANY): "time_elapsed",
    ("user_choice", ANY): "user_choice",
    ("parent_completion", ANY): "hierarchy_level_complete",
}
```

---

### Finding 14: ContentBrief Lacks Mechanic-Specific Required Fields (MEDIUM)

**Audit Question**: Additional finding from schema analysis

**Problem**: `ContentBrief` has optional mechanic-specific hints (`sequence_topic`, `category_names`, `comparison_subjects`, `narrative_premise`, etc.). But these are ALL optional. The content_validator per-mechanic checks (lines 262-270 of the plan) validate the OUTPUT, not the INPUT. If the game_designer produces a sequencing mechanic without `sequence_topic` in the ContentBrief, the content_generator has no guidance and may produce poor content.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 362-388: ContentBrief schema, all mechanic-specific fields Optional
- `docs/audit/14_v4_architecture_refined.md` lines 469-471: `check_content_brief(mech, issues)` mentioned but not detailed

**Impact**: The `game_plan_validator` should check that mechanic-specific ContentBrief fields are populated. E.g., sequencing must have `sequence_topic`, branching must have `narrative_premise`, compare_contrast must have `comparison_subjects`.

**Resolution**: Add ContentBrief completeness checks to `game_plan_validator`:
- sequencing: `sequence_topic` required
- branching: `narrative_premise` required
- compare_contrast: `comparison_subjects` required, `len >= 2`
- sorting: `category_names` required, `len >= 2`
- description_matching: `description_source` required

These are already hinted at in the plan (line 253: "Content brief completeness per mechanic type") but the schema does not enforce them. Use Pydantic `model_validator` or explicit checks in the validator.

---

### Finding 15: Timed Wrapper Not Modeled as Separate Mechanic (MEDIUM)

**Audit Question**: Additional finding from architecture analysis

**Problem**: Timed challenge (`is_timed: true` on MechanicPlan) is a modifier on an existing mechanic, not a separate mechanic. But the frontend has `timed_challenge` as a separate InteractionMode (types.ts line 13). The V3 blueprint assembler creates a separate mechanic entry for timed_challenge (lines 964-968). The V4 plan says timed is a wrapper (architecture doc lines 1027-1040), but doesn't specify whether the blueprint should have `interactionMode: "timed_challenge"` (separate mode) or `interactionMode: "drag_drop"` with timer properties (modifier).

**Evidence**:
- `frontend/types.ts` line 13: `'timed_challenge'` as InteractionMode
- Architecture doc lines 1027-1040: timed wrapper example
- `blueprint_assembler_tools.py` lines 964-968: creates separate timed_challenge mechanic entry
- `docs/v4_implementation_plan_final.md` line 114: `timed_config: Optional[TimedConfig] = None`

**Impact**: The frontend timed_challenge mode wraps another mode. But if the backend emits `interactionMode: "timed_challenge"`, the frontend needs to know WHICH mode is being timed. This is currently done via `timedChallengeWrappedMode` (line 967 of V3 assembler).

**Resolution**: V4 should use the modifier approach:
1. The mechanic keeps its original type (e.g., `drag_drop`).
2. Add `is_timed: true`, `time_limit_seconds: 60` as properties on the mechanic.
3. The frontend initializes a timer overlay when `is_timed` is true, regardless of the mechanic type.
4. Remove `timed_challenge` as a separate InteractionMode on the frontend (or keep it for backward compat but prefer the modifier approach).

---

### Finding 16: graph_builder.py Validation Timing (MEDIUM)

**Audit Question**: Additional finding from architecture analysis

**Problem**: `graph_builder.py` constructs and validates the game state graph from GamePlan. The plan places this in `helpers/` (Phase 2) and says it is used by blueprint_assembler (Phase 4). But the graph validation should happen BEFORE content generation (Phase 2), because content generators depend on a valid mechanic graph. If the graph has connectivity issues (unreachable mechanics), content would be generated for mechanics that will never be played.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 230-236: graph_builder in helpers (Phase 2 implementation)
- Phase 2 graph runs per-mechanic content generators based on GamePlan.mechanics list
- Phase 1 game_plan_validator already checks graph connectivity (lines 424-429)

**Impact**: Low. The game_plan_validator (Phase 1) already checks graph connectivity. But `graph_builder.py` does additional validation (DFS, branching tree connectivity, path graph validation) that goes beyond what the validator checks. This deeper validation should also run after Phase 1.

**Resolution**: Run `graph_builder.py` as the last step of Phase 1 (after game_plan_validator passes). This validates the graph structure thoroughly before Phase 2 starts. The built graph object can be stored in DesignState for use by Phase 4's blueprint_assembler.

---

### Finding 17: Missing Error Propagation from Send API Branches (CRITICAL)

**Audit Question**: Additional finding from LangGraph architecture analysis

**Problem**: When using LangGraph's Send API for Map-Reduce, if a spawned branch raises an exception (e.g., content generator fails after max retries), that exception must propagate to the parent graph. The plan does not describe error handling for Map-Reduce branches.

Possible failure scenarios:
1. One content generator fails after 2 retries -> what happens to the scene? The other mechanics succeeded.
2. One asset chain fails (image search finds nothing) -> should the scene be retried? Assembled without that asset?
3. Multiple mechanics in a scene fail -> is the entire scene dropped?

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 388-393: Send API per-mechanic, no error handling described
- LangGraph Send API: spawned branches that raise exceptions cause the parent to raise

**Impact**: Without explicit error handling, a single mechanic failure will crash the entire pipeline. With proper handling, the pipeline could (a) skip the failed mechanic, (b) use fallback content, or (c) report partial failure.

**Resolution**:
1. Each Send branch must wrap its work in try/except and return a result with `status: "success" | "failed"` and `error_message: str | None`.
2. The reducer function (`scene_content_merger`) must check statuses. If a non-essential mechanic fails (e.g., a secondary mechanic in a multi-mechanic scene), it can be dropped with a warning. If the starting mechanic fails, the scene fails.
3. Add a `partial_failure_policy` config: `"strict"` (any failure = pipeline error) or `"graceful"` (drop failed mechanics, warn).

---

### Finding 18: Mechanic Compatibility Matrix Not Used in GamePlan Validator (MEDIUM)

**Audit Question**: Additional finding from FOL rules analysis

**Problem**: The FOL rules include a 9x9 mechanic compatibility matrix (which mechanics can follow which). The plan says `interaction_validator` checks this (line 603: "checks every mode transition against this matrix"). But this check happens in Phase 2 (after content generation), when the mechanic graph was already set in Phase 1. If incompatible mechanics are connected, content would be generated for both before the error is caught.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 600-604: compatibility matrix in interaction_validator (Phase 2)
- Architecture doc lines 424-429: game_plan_validator checks connectivity but NOT compatibility

**Impact**: Wasted LLM calls generating content for mechanics whose connection will be rejected by the interaction_validator.

**Resolution**: Move compatibility matrix checking to `game_plan_validator` (Phase 1). The interaction_validator can still re-check, but the first line of defense should be Phase 1 before any content is generated.

---

### Finding 19: SceneSpec vs GameScene Type Mismatch (MEDIUM)

**Audit Question**: Additional finding from frontend analysis

**Problem**: The V4 plan defines `SceneSpec` as part of `GameSpecification`. The frontend has `GameScene` in `types.ts`. These types may differ in field naming conventions (snake_case vs camelCase) and structure. The `sceneToBlueprint` function already handles dual-casing (`scene.sequenceConfig || scene.sequence_config`), but this is a maintenance burden.

**Evidence**:
- `frontend/engine/sceneManager.ts` lines 131-140: dual-casing support
- `docs/v4_implementation_plan_final.md` lines 104-117: GameSpecification uses Python naming
- `frontend/types.ts`: GameScene uses mixed naming

**Impact**: Every new field added to SceneSpec must have dual-casing support in sceneToBlueprint. This is error-prone.

**Resolution**: The V4 blueprint assembler must output camelCase JSON (matching the frontend convention) OR the frontend must use a single normalization layer. The cleanest approach: the assembler outputs camelCase. Use Pydantic's `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)` on all V4 schemas that become part of the blueprint output.

---

### Finding 20: Checkpoint Resume Does Not Handle Schema Migrations (LOW)

**Audit Question**: Additional finding from Phase 5 analysis

**Problem**: The plan uses LangGraph SQLite checkpointing to resume from the last successful phase. But if the V4 schemas change between the checkpoint save and the resume (e.g., during development or A/B testing), the deserialized checkpoint may have stale or incompatible data.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 411-447: checkpointing with SQLite

**Impact**: Low during production, higher during development. A schema change would invalidate all existing checkpoints.

**Resolution**: Add a `schema_version: str` field to V4MainState. On checkpoint resume, compare the stored version with the current version. If mismatched, discard the checkpoint and re-run from scratch. Also respect the 24-hour cleanup policy.

---

### Finding 21: No Fallback for Failed Asset Generation (HIGH)

**Audit Question**: Additional finding from asset pipeline analysis

**Problem**: The asset pipeline uses tool chains (serper -> gemini_regen -> gemini_bbox -> SAM3). Each step can fail: no search results, image regeneration fails, zone detection misses labels, SAM segmentation errors. The plan mentions "retry zone detection with specific labels as guidance" (architecture doc line 778-779), but does not describe fallbacks when retry also fails.

**Evidence**:
- Architecture doc lines 775-781: asset_validator retries zone detection but no deeper fallback
- `docs/v4_implementation_plan_final.md` line 343: "Retry: zone detection fails -> retry with specific labels as guidance"
- V3 code: when zone detection fails completely, zones get dummy coordinates (lines 443-449 of blueprint_assembler_tools.py)

**Impact**: If image search returns nothing, the entire scene has no diagram. Visual mechanics (drag_drop, click_to_identify, trace_path) cannot function without a diagram.

**Resolution**:
1. Define a fallback chain: `serper_search -> serper_fallback_query -> imagen_generate_from_description -> placeholder_image`.
2. If zone detection fails after retry, use `gemini_flash_bbox` only (without SAM) for approximate zones.
3. If ALL image generation fails, the scene can still work if ONLY content-only mechanics are present. If visual mechanics are present and all image attempts fail, mark the scene as degraded and emit a pipeline warning.
4. Blueprint assembler assigns dummy coordinates to undetected zones (existing V3 behavior, lines 443-449) as a last resort.

---

### Finding 22: Content Generator Model Routing Unclear (MEDIUM)

**Audit Question**: Additional finding from model assignment analysis

**Problem**: The plan says "content_generator (complex): gemini-2.5-pro" and "content_generator (simple): gemini-2.5-flash" (lines 503-504). But the plan does not define which mechanics are "complex" vs "simple" or how the routing decision is made.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 503-504: model assignment table
- Architecture doc line 543: "Model: pro for complex, flash for simple"
- Mechanic contract should specify model routing

**Impact**: Without explicit routing, either all mechanics use pro (expensive) or the routing is ad-hoc.

**Resolution**: Define model routing in mechanic contracts:
- **gemini-2.5-pro**: branching_scenario (complex narrative), compare_contrast (dual subjects), trace_path (spatial reasoning)
- **gemini-2.5-flash**: drag_drop (simple labels), click_to_identify (prompts), sequencing (ordered items), sorting_categories (categorization), memory_match (pairs), description_matching (descriptions)

Add this as a `model_tier: Literal["pro", "flash"]` field to each mechanic contract.

---

### Finding 23: Mode Transition from GamePlan to Blueprint (MEDIUM)

**Audit Question**: Additional finding from blueprint assembly analysis

**Problem**: GamePlan uses `MechanicConnection` with `from_mechanic_id` and `to_mechanic_id`. The frontend uses `ModeTransition` with `from: InteractionMode` and `to: InteractionMode`. The translation requires looking up each mechanic's type from its ID. But the plan does not describe this translation step in the blueprint assembler.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 390-395: MechanicConnection schema uses mechanic IDs
- `frontend/types.ts` lines 45-52: ModeTransition uses InteractionMode types
- Architecture doc lines 986-997: sequential example shows the mapping

**Impact**: The blueprint assembler must maintain a `mechanic_id -> mechanic_type` lookup and translate MechanicConnections to ModeTransitions. This is straightforward but must be documented.

**Resolution**: In `blueprint_assembler.py`:
1. Build a lookup: `{mech.mechanic_id: mech.mechanic_type for mech in scene.mechanics}`
2. For each `MechanicConnection`, translate:
   - `from_mechanic_id` -> `from: lookup[from_mechanic_id].mechanic_type`
   - `to_mechanic_id` -> `to: lookup[to_mechanic_id].mechanic_type`
   - `trigger` -> mapped via Finding 13's TRIGGER_MAP
   - `trigger_value` -> pass through
3. Filter out `"scene_start"` and `"scene_end"` pseudo-connections (these are structural, not mode transitions).

---

### Finding 24: FOL Rule R2.7 (DnD Context Singleton) Ambiguous (LOW)

**Audit Question**: Additional finding from FOL rules analysis

**Problem**: FOL rule R2.7 says "DnD context singleton" and is enforced by `blueprint_validator` at Phase 4. But the formal graph rules document does not clearly define what "DnD context singleton" means. It likely means "only one drag_drop mechanic per scene can have the DnD context (diagram zones, label tray)", but this is not explicit.

**Evidence**:
- `docs/v4_implementation_plan_final.md` line 571: R2.7 in blueprint_validator

**Impact**: Low. If the rule is "max one drag_drop per scene", this is overly restrictive. Multiple drag_drop mechanics in the same scene are valid (e.g., different zone subsets).

**Resolution**: Clarify R2.7: it likely means "only one set of zones and labels is active at a time in the drag_drop context". This is already enforced by the mode transition system (only one mode active at a time). The rule should be rephrased as: "At any moment, at most one mechanic's zones/labels are rendered on the diagram."

---

### Finding 25: Compare Contrast Zone Coordinate System (CRITICAL)

**Audit Question**: Additional finding from cross-referencing FOL rules with frontend

**Problem**: Compare contrast has two diagrams with their own zone sets. The FOL rules require zones to have `x/y/w/h` coordinates. But these coordinates are relative to their diagram image. In the blueprint, `diagramA.zones[].x` and `diagramB.zones[].x` are both in the 0-100% space of their respective images. The frontend renders two images side-by-side (or overlaid in venn mode), so zone coordinates must be transformed to the composite viewport.

The V4 blueprint assembler must handle this coordinate transformation, but the plan does not describe it.

**Evidence**:
- FOL rules: compare_contrast zones need `x/y/w/h`
- `blueprint_assembler_tools.py` lines 921-922: V3 uses raw coordinates without transformation
- Frontend `CompareContrast.tsx` component (not read, but referenced in mechanic registry)

**Impact**: If both diagrams' zones use 0-100% coordinates relative to their own images, the frontend must know which diagram each zone belongs to and render accordingly. The `compareConfig.diagramA.zones` and `compareConfig.diagramB.zones` already separate them, which is correct. But the blueprint assembler must ensure zones are not mixed into the global `diagram.zones` array.

**Resolution**:
1. Compare contrast zones go ONLY in `compareConfig.diagramA.zones` and `compareConfig.diagramB.zones`, NOT in the top-level `diagram.zones`.
2. The top-level `diagram.zones` should be empty (or contain only zones from other mechanics in the same scene).
3. The frontend's CompareContrast component reads zones from `compareConfig`, not from `blueprint.diagram.zones`.
4. Add this rule to `blueprint_validator`: if a scene has compare_contrast mechanic, compare zones must be in compareConfig, not in diagram.zones.

---

### Finding 26: Capability Spec Version Drift (LOW)

**Audit Question**: Additional finding from prompt engineering analysis

**Problem**: The capability spec (injected into game_designer prompt) lists available mechanics with descriptions, scoring patterns, and connection patterns. If mechanics are added or modified, the capability spec must be updated manually. The plan mentions this file (`contracts/capability_spec.py`) but does not describe how it stays in sync with mechanic contracts.

**Evidence**:
- `docs/v4_implementation_plan_final.md` line 187: capability_spec.py
- Architecture doc lines 222-283: capability spec JSON structure

**Impact**: Low if development is disciplined. Risk of capability spec describing mechanics that don't exist, or missing newly added mechanics.

**Resolution**: Generate the capability spec JSON from the mechanic contracts registry at runtime. `capability_spec.py` should have a `build_capability_spec()` function that reads `MechanicContract` registry and produces the JSON. This ensures zero drift.

---

### Finding 27: No Rate Limiting or Concurrency Control for Parallel Send (LOW)

**Audit Question**: Additional finding from operational analysis

**Problem**: Phase 2 and Phase 3 use parallel Send API for per-mechanic and per-asset work. A scene with 4 mechanics and 4 asset needs could spawn 8+ parallel LLM/API calls. Gemini API has rate limits. The plan does not describe concurrency control.

**Evidence**:
- `docs/v4_implementation_plan_final.md` lines 388-393: nested Send API
- Architecture doc lines 755-782: per-asset parallel Send

**Impact**: Rate limit errors from Gemini/Serper/SAM3 could cause cascading failures.

**Resolution**:
1. Use LangGraph's built-in concurrency control: `Send(..., max_concurrency=3)` to limit parallel branches.
2. Add exponential backoff to API calls within asset_dispatcher.
3. For LLM calls, use the existing `LLMService` which should have retry/rate-limit logic.

---

## Summary Table

| # | Finding | Severity | Audit Question |
|---|---------|----------|----------------|
| 1 | Phase 0 parallel vs sequential contradiction | MEDIUM | #11 |
| 2 | Zone ID chicken-and-egg problem | CRITICAL | #2 |
| 3 | Parallel per-mechanic content ordering | HIGH | #1 |
| 4 | Compare contrast dual-image flow gap | CRITICAL | #3 |
| 5 | Hierarchical mode composability undefined | HIGH | #4 |
| 6 | Multi-scene transition trigger formalization | HIGH | #5 |
| 7 | Score rollup consistency | HIGH | #6 |
| 8 | Empty scenes (content-only, no zones) | CRITICAL | #8 |
| 9 | Distractor labels flow and scope | MEDIUM | #7 |
| 10 | Retry state cleanup behavior | HIGH | #9 |
| 11 | v4ToBlueprint adapter complexity | CRITICAL | #10 |
| 12 | Observability gap for V4 agents | HIGH | #12 |
| 13 | MechanicConnection trigger type mismatch | HIGH | Additional |
| 14 | ContentBrief lacks mechanic-specific required fields | MEDIUM | Additional |
| 15 | Timed wrapper not modeled as separate mechanic | MEDIUM | Additional |
| 16 | graph_builder.py validation timing | MEDIUM | Additional |
| 17 | Missing error propagation from Send API branches | CRITICAL | Additional |
| 18 | Mechanic compatibility matrix not in GamePlan validator | MEDIUM | Additional |
| 19 | SceneSpec vs GameScene type mismatch | MEDIUM | Additional |
| 20 | Checkpoint resume schema migrations | LOW | Additional |
| 21 | No fallback for failed asset generation | HIGH | Additional |
| 22 | Content generator model routing unclear | MEDIUM | Additional |
| 23 | Mode transition ID-to-type translation | MEDIUM | Additional |
| 24 | FOL rule R2.7 ambiguous | LOW | Additional |
| 25 | Compare contrast zone coordinate system | CRITICAL | Additional |
| 26 | Capability spec version drift | LOW | Additional |
| 27 | No rate limiting for parallel Send | LOW | Additional |

---

## Recommended Implementation Order

### Before Implementation Begins (Address in Plan)

1. **Finding 1**: Resolve Phase 0 parallel vs sequential decision
2. **Finding 5**: Clarify hierarchical MODE vs CONNECTION distinction
3. **Finding 11**: Decide on adapter vs direct blueprint output
4. **Finding 15**: Decide timed wrapper modeling approach

### Phase 1: Schemas & Contracts

5. **Finding 2**: Add label normalization contract to schemas
6. **Finding 4**: Add `zone_labels_a`/`zone_labels_b` to MechanicPlan for compare_contrast
7. **Finding 9**: Clarify distractor scope (global vs per-mechanic)
8. **Finding 13**: Add TRIGGER_MAP to mechanic contracts
9. **Finding 14**: Add ContentBrief completeness requirements per mechanic
10. **Finding 19**: Use Pydantic alias_generator for camelCase output
11. **Finding 20**: Add `schema_version` to V4MainState
12. **Finding 22**: Add `model_tier` to mechanic contracts
13. **Finding 26**: Generate capability spec from mechanic contracts

### Phase 2: Helpers

14. **Finding 16**: Run graph_builder after Phase 1 validator
15. **Finding 23**: Document mechanic_id-to-type translation in assembler

### Phase 3: Validators

16. **Finding 7**: Add content item count strict enforcement
17. **Finding 18**: Move compatibility matrix to game_plan_validator
18. **Finding 8**: Handle content-only scenes (no zones required)
19. **Finding 25**: Add compare contrast zone isolation rule

### Phase 4: LLM Agents

20. **Finding 3**: Enforce expected_item_count in content generator output
21. **Finding 10**: Define Quality Gate within each Send branch
22. **Finding 17**: Add error handling for Send branch failures

### Phase 5: Graph Wiring

23. **Finding 6**: Formalize scene transition in sceneManager
24. **Finding 21**: Add asset fallback chains
25. **Finding 27**: Add concurrency control for parallel Send

### Phase 6: Integration

26. **Finding 12**: Add V4 instrumentation and PipelineView metadata
27. **Finding 24**: Clarify R2.7 rule documentation
