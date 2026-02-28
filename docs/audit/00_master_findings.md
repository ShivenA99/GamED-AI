# 00 - Master Audit Findings

**Date:** 2026-02-09
**Scope:** Full V3 pipeline + frontend game engine audit
**Audit docs:** 01-06 in this directory
**Total unique gaps found:** 62

---

## Priority Tiers

### Tier 0: Structural Blockers (fix before anything else)

| # | Gap | Files | Effort | Details |
|---|---|---|:---:|---|
| F1 | `canonical_labels` not at top-level state | `domain_knowledge_retriever.py` return dict | S | Add `"canonical_labels": canonical_labels` to return dict (1 line). All V3 agents read empty list because field is nested inside `domain_knowledge` dict. |
| F2 | `MechanicConfigV3.config` is `Dict[str,Any]` everywhere | `scene_spec_v3.py`, `blueprint_schemas.py`, `types.ts` | L | Create typed config classes per mechanic (`TracePathConfig`, `SequenceConfig`, `DescriptionMatchConfig`, `ClickIdentifyConfig`). Discriminated union keyed on `type`. Apply at SceneSpecV3, IDMechanic, and frontend layers. |
| F3 | Validators have zero mechanic-specific checks | `design_validator.py`, `scene_validator.py`, `interaction_validator.py` | M | Add per-mechanic requirements: trace_path must have waypoints, sequencing must have correct_order, description_matching must have descriptions. Currently a trace_path scene with 0 waypoints passes all 3 validators. |

### Tier 1: Unblock Broken Mechanics (make trace_path + description_matching functional)

| # | Gap | Files | Effort | Details |
|---|---|---|:---:|---|
| F4 | `DescriptionMatchingState` not wired to store | `useLabelDiagramState.ts` | S | Add `MATCH_DESCRIPTION` action type, connect `DescriptionMatcher` callbacks to dispatch. Unblocks entire mechanic. |
| F5 | No `generate_functional_descriptions()` tool | New tool in `asset_generator_tools.py` | M | LLM tool: labels + domain knowledge → functional descriptions ("Pumps blood to lungs"). |
| F6 | No `generate_waypoints()` tool | New tool in `asset_generator_tools.py` | M | Vision model: locates flow items on diagram image → ordered waypoint coordinates. |
| F7 | No `generate_path_connections()` tool | New tool in `asset_generator_tools.py` | S | Deterministic for linear (i→i+1), cyclic (add last→first). |
| F8 | `PathProgress` not wired to store | `useLabelDiagramState.ts` | S | Add `UPDATE_PATH_PROGRESS` action. Wire `PathDrawer` events to dispatch. |
| F9 | `PathDrawer` canvas validation incomplete | `interactions/PathDrawer.tsx` | M | Implement waypoint proximity detection, path segment validation, scoring events. |
| F10 | No path/description data in blueprint | `blueprint_assembler_tools.py` | M | Populate `paths[]`, `descriptions[]`, `identificationPrompts[]` from typed upstream configs. Currently everything dumped into `mechanics[].config` generic dict. |

### Tier 2: Fix Data Flow (make click_to_identify + sequencing production-quality)

| # | Gap | Files | Effort | Details |
|---|---|---|:---:|---|
| F11 | Blueprint `identificationPrompts[]` not populated | `blueprint_assembler_tools.py` | M | Read click_config from game_design_v3, map to `identificationPrompts[{zoneId, prompt, order}]`. |
| F12 | No `generate_identification_prompts()` tool | New tool in `asset_generator_tools.py` | M | LLM: zone labels + subject → difficulty-graded identification questions. |
| F13 | `sequenceConfig` stored in wrong blueprint location | `blueprint_assembler_tools.py` | S | Currently inside `mechanics[].config`. Frontend `SequenceBuilder` expects `blueprint.sequenceConfig` at scene root level. |
| F14 | No `generate_sequence_items()` tool | New tool in `asset_generator_tools.py` | M | Bridge `sequence_flow_data` from domain knowledge → sequencing mechanic items. |
| F15 | Sequencing uses component-local state | `interactions/SequenceBuilder.tsx`, `useLabelDiagramState.ts` | M | Lift sequence ordering state from local `useState` into centralized Zustand store. |
| F16 | `DescriptionMatcher` uses component-local state | `interactions/DescriptionMatcher.tsx`, `useLabelDiagramState.ts` | M | Same as F15 — lift state to Zustand. |
| F17 | Mode transitions only understand drag_drop | `useLabelDiagramState.ts` `checkModeTransition()` | M | Make mechanic-aware: read `pathProgress`, `identificationProgress`, sequencing/description completion. Currently only counts `placedLabels`. |
| F18 | Multi-mechanic scoring incoherent | `useLabelDiagramState.ts` `completeInteraction()` | M | `completeInteraction()` overwrites `maxScore` each time. Need cumulative score model. |

### Tier 3: Improve Quality

| # | Gap | Files | Effort | Details |
|---|---|---|:---:|---|
| F19 | Hierarchy misclassified as mechanic | `game_design_v3.py`, `types.ts`, `interaction_patterns.py` | M | Remove `hierarchical` from `VALID_MECHANIC_TYPES` and `InteractionMode`. Make it `hierarchy_config` field on SceneTask. |
| F20 | Game designer prompt doesn't enumerate mechanics | `game_designer_v3.py` system prompt | S | List 5 mechanics explicitly. Warn about PARTIAL status of trace_path, description_matching. |
| F21 | Misconception feedback is mechanic-agnostic | `interaction_designer_tools.py` `generate_misconception_feedback()` | S | Parameterize by `mechanic_type`. trace_path needs ordering misconceptions, not placement misconceptions. |
| F22 | Model enforcement not guaranteed | `scene_architect_v3.py`, `interaction_designer_v3.py` | S | Default to gemini-2.5-pro if `_model_override` is not set. Flash fails multi-tool workflows. |
| F23 | Zone containment not enforced for hierarchy | `asset_generator_tools.py` `submit_assets` | S | After detect_zones, validate parent-child spatial containment. |
| F24 | Task config not propagated to blueprint | `index.tsx` `_sceneToBlueprint()` | S | Read `task.config` and apply to blueprint per-task overrides. |
| F25 | Scoring/feedback lost in mechanic handoff | `blueprint_assembler_tools.py` conversion | M | Frontend `Mechanic` type only has `type` + `config`. Per-mechanic scoring/feedback fields stripped during conversion. |
| F26 | Task results not aggregated to total score | `useLabelDiagramState.ts` | S | `taskResults[]` saved but never summed into `totalScore`. Only `sceneResults` are summed. |

### Tier 4: Rename (do after all mechanics work)

| # | Gap | Files | Effort | Details |
|---|---|---|:---:|---|
| F27 | LABEL_DIAGRAM → INTERACTIVE_DIAGRAM | ~120 files | XL | Backend template type strings, agent names, schema files, config presets, routes, tests, documentation. |
| F28 | LabelDiagramGame/ → InteractiveDiagramGame/ | ~35 frontend files | L | Directory rename, component names, hook names, all imports. |
| F29 | useLabelDiagramState → useInteractiveDiagramState | `hooks/useLabelDiagramState.ts` + imports | M | Function rename + update all 20+ import sites. |

---

## Effort Key

| Size | Meaning |
|---|---|
| S | < 1 hour, < 50 lines changed, 1-2 files |
| M | 1-4 hours, 50-200 lines, 3-10 files |
| L | 4-8 hours, 200-500 lines, 10-20 files |
| XL | 8+ hours, 500+ lines, 20+ files |

---

## Execution Order

### Phase A: Structural fixes (F1-F3)
1. F1 — canonical_labels routing (5 min)
2. F3 — mechanic-specific validation rules in 3 validators (2-4 hours)
3. F2 — typed mechanic configs at all layers (4-8 hours) — can be done incrementally

### Phase B: Unblock broken mechanics (F4-F10)
4. F4 — wire description_matching state (1 hour)
5. F8 — wire PathProgress to store (1 hour)
6. F5 — generate_functional_descriptions tool (2-3 hours)
7. F6+F7 — generate_waypoints + path_connections tools (3-4 hours)
8. F9 — PathDrawer canvas validation (3-4 hours)
9. F10 — populate mechanic-specific blueprint fields (2-3 hours)

### Phase C: Fix data flow (F11-F18)
10. F13 — fix sequenceConfig location (30 min)
11. F11 — populate identificationPrompts (1-2 hours)
12. F12 — generate_identification_prompts tool (2-3 hours)
13. F14 — generate_sequence_items tool (2-3 hours)
14. F15+F16 — lift sequencing + description_matching state (3-4 hours)
15. F17 — mechanic-aware mode transitions (2-3 hours)
16. F18 — cumulative scoring model (1-2 hours)

### Phase D: Quality improvements (F19-F26)
17. F20 — update game designer prompt (30 min)
18. F21 — mechanic-specific misconceptions (1 hour)
19. F22 — model enforcement (30 min)
20. F19 — reclassify hierarchy (2-3 hours)
21. F23-F26 — remaining quality fixes (2-3 hours)

### Phase E: Rename (F27-F29)
22. F27+F28+F29 — full rename (~120 files, 8+ hours)

---

## Cross-Reference to Audit Documents

| Finding | Audit Doc | Section |
|---|---|---|
| F1 (canonical_labels) | 03, 05 | CC1, Path 1 |
| F2 (untyped config) | 03, State audit | CC2, Issue #2 |
| F3 (validators) | 03 | CC3 |
| F4-F9 (trace_path + desc_matching) | 03 | Per-mechanic deep dives |
| F10-F14 (asset gen tools) | 06 | Proposed tools |
| F15-F18 (frontend state) | 02, Frontend audit | Per-mechanic components |
| F19-F26 (quality) | 03, 04 | Recommendations |
| F27-F29 (rename) | Integration audit | E1-E3 |

---

## Per-Mechanic Readiness After Full Fix

| Mechanic | Current | After Tier 0-1 | After Tier 0-2 | After Tier 0-3 |
|---|---|---|---|---|
| drag_drop | **FULL** | FULL | FULL | FULL |
| click_to_identify | DEGRADED | DEGRADED | **FULL** | FULL |
| sequencing | DEGRADED | DEGRADED | **FULL** | FULL |
| trace_path | BROKEN | **FUNCTIONAL** | FUNCTIONAL | FULL |
| description_matching | BROKEN | **FUNCTIONAL** | FUNCTIONAL | FULL |
| hierarchy (modifier) | FUNCTIONAL | FUNCTIONAL | FUNCTIONAL | **FULL** |
