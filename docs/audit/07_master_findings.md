# 07 - Master Audit Findings & Fix Plan

**Generated:** 2026-02-09 | **Updated:** 2026-02-10 (deep audit v2 integration)
**Scope:** Complete system audit consolidation — Backend (A1-A8), State/Schema (B1-B4), Frontend (C1-C9), Integration (D1-D4), Rename (E1-E3)

---

## Audit Completion Status

| Audit | Status | Key Finding |
|---|---|---|
| A1: Router | COMPLETE | INTERACTIVE_DIAGRAM already in TEMPLATE_REGISTRY. V3 bypasses router. |
| A2: Domain Knowledge | COMPLETE | canonical_labels routing bug (CC-1). Not ReAct, no per-mechanic tools. |
| A3: Game Designer V3 | COMPLETE | GameDesignV3Slim has no mechanic configs (CC-2). Only `type` field. |
| A4: Scene Architect V3 | COMPLETE | Generic mechanic handling. No mechanic-specific zone generation. |
| A5: Interaction Designer V3 | COMPLETE | Doesn't generate mechanic content (CC-3). Only scoring+feedback. |
| A6: Asset Generator V3 | COMPLETE | 5 tools, all mechanic-agnostic. Missing 5+ tools for non-drag_drop. |
| A7: Blueprint Assembler V3 | COMPLETE | Loses mechanic structure. Config flattened to Dict. |
| A8: Validators | COMPLETE | No mechanic-specific checks (CC-4). |
| B1: AgentState | COMPLETE | V3 fields are Dict not Pydantic. canonical_labels missing top-level. |
| B2: Blueprint schema | COMPLETE | IDMechanic.config is untyped Dict. Per-mechanic fields exist but unpopulated. |
| B3: SceneTask chain | COMPLETE | Backend→Blueprint→Frontend chain works. focus_labels→zone_ids conversion needed. |
| B4: Hierarchy reclassification | COMPLETE | Misclassified as mechanic. Should be cross-cutting modifier. |
| C1-C9: Frontend mechanics | COMPLETE | Only drag_drop fully wired. 5 mechanics have zero store integration. |
| D1: Type compatibility | COMPLETE | Correctly handled by blueprint_assembler. Scoring/feedback not in frontend Mechanic type. |
| D2: Asset URL resolution | COMPLETE | Frontend proxy works correctly. |
| D3: Zone coordinates | COMPLETE | 0-100% scale. Correctly flattened. No mismatch. |
| D4: Config propagation | COMPLETE | Config propagates but mechanic scoring/feedback inaccessible to frontend. |
| E1-E3: Rename scope | COMPLETE | 86 files with LABEL_DIAGRAM, 51 in component dir, 100+ total. |
| **Doc 01 Deep Audit v2** | **COMPLETE** | **77 bugs across 15 backend components. See doc 01.** |
| **Doc 02 Deep Audit v2** | **COMPLETE** | **121 bugs across 16 frontend categories. See doc 02.** |

---

## Consolidated Bug Count (Updated Feb 10)

### Deep Audit v2 Totals

| Source | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| Doc 01 v2 (Backend Pipeline) | 6 | 24 | 30 | 17 | 77 |
| Doc 02 v2 (Frontend Engine) | 7 | 33 | 48 | 33 | 121 |
| Doc 03 (Mechanic Matrix) | 13 | 16 | 15 | 8 | 52 |
| **Raw total** | **26** | **73** | **93** | **58** | **250** |
| **Deduplicated estimate** | **~18** | **~50** | **~65** | **~45** | **~178** |

Note: Significant overlap between doc 01/02 (agent-level) and doc 03 (mechanic-level). The 178 unique issues represent distinct code-level bugs with line numbers.

### Backend Top Issues (from Doc 01 v2)

| ID | Agent | Severity | Issue |
|---|---|---|---|
| A2-1 | domain_knowledge_retriever | CRITICAL | canonical_labels written nested but read top-level (always empty) — **F1 FIXED** |
| A3-1 | game_designer_v3 | CRITICAL | `check_capabilities` lies about mechanic support — claims all 10 work |
| A6-1 | asset_generator_v3 | CRITICAL | `submit_assets` converts scoring list→dict crash on `.get()` |
| A7-1 | blueprint_assembler_v3 | CRITICAL | `generation_complete` not set → route marks run as "error" — **FIXED** |
| A5-1 | interaction_designer_v3 | HIGH | Produces scoring/feedback but NO mechanic content (prompts, sequences, paths) |
| A6-2 | asset_generator_v3 | HIGH | All 5 tools are drag_drop-only. No path/sequence/description generation. |
| A7-2 | blueprint_assembler_v3 | HIGH | Typed MechanicConfigV3 schemas flattened back to Dict[str,Any] |
| A8-1 | All validators | HIGH | Zero mechanic-specific validation rules |

### Frontend Top Issues (from Doc 02 v2)

| ID | Component | Severity | Issue |
|---|---|---|---|
| S-10 | useLabelDiagramState | CRITICAL | `removeLabel` doesn't update `completedZoneIds` — temporal state stale |
| S-2+S-24 | useLabelDiagramState | CRITICAL | Only 3 of 11 modes initialized on transition. 5 modes have no store wiring. |
| N-3 | normalizeBlueprint | CRITICAL | Phantom zones at grid positions for orphan labels |
| IC-1+IC-2 | sequencing, sorting | CRITICAL | Zero store integration. Score always 0. |
| S-6+S-18 | placeLabel, checkModeTransition | HIGH | Completion/transition checks count ALL labels, not per-mode |
| S-33+S-34 | updatePathProgress, updateIdentificationProgress | MEDIUM | Score overwrites instead of accumulates in multi-mechanic |
| S-20 | checkModeTransition | HIGH | setTimeout memory leak on unmount |
| S-19 | checkModeTransition | HIGH | `time_elapsed` trigger defined but not implemented |

---

## NEW Findings Not in Doc 03

### From State/Schema Audit (B1-B3)

| ID | Gap | Severity | Details |
|---|---|---|---|
| B-1 | V3 state fields typed as `Dict[str, Any]` not Pydantic models | HIGH | `scene_specs_v3: Optional[List[Dict[str, Any]]]` instead of `Optional[List[SceneSpecV3]]`. No type-safe access. |
| B-2 | IDMechanic.interaction_mode redundant with mechanic_type | MEDIUM | Both fields exist. Unclear which frontend uses. |
| B-3 | Backend IDMechanic has scoring/feedback fields, frontend Mechanic doesn't | HIGH | Blueprint assembler includes them but frontend Mechanic type ignores them. |
| B-4 | GameScene.tasks optional in frontend | HIGH | Should be required (always create 1 implicit task for single-mechanic). |
| B-5 | Zone-to-mechanic mapping missing | HIGH | No field indicating which zones participate in which mechanics. |
| B-6 | IDLabel.is_distractor not in frontend Label type | MEDIUM | Frontend has separate DistractorLabel interface. |
| B-7 | focus_labels (texts) → zone_ids + label_ids conversion undocumented | MEDIUM | Blueprint assembler must map label texts to IDs. |

### From Frontend Deep Audit (Doc 02 v2 — Selected New Findings)

| ID | Gap | Severity | Details |
|---|---|---|---|
| S-10 | removeLabel doesn't update completedZoneIds or visibleZoneIds | CRITICAL | Temporal constraints become stale after undo. |
| S-7 | hasRemainingModes logic wrong for 3+ mechanics | HIGH | `completedModes.length + 1 < availableModes.length` miscounts. |
| S-14 | Mutex constraints not transitive | HIGH | A↔B↔C allows A and C visible simultaneously. |
| S-23 | transitionToMode mutates modeHistory in-place | HIGH | Violates Zustand immutability, may miss re-renders. |
| S-27 | advanceToNextTask TaskResult.max_score = actual score | HIGH | Percentage always 100% regardless of performance. |
| N-1 | normalizeBlueprint queue system produces wrong label→zone mappings | HIGH | FIFO queue, not semantic matching. |
| PS-2 | Save exists but restore broken — onLoad doesn't feed state back to store | MEDIUM | Persistence feature non-functional. |
| IC-9 | handleDescriptionMatch compares zone.id to labelId | MEDIUM | Always incorrect — different namespaces. |

### From Integration Audit (D1-D4)

| ID | Gap | Severity | Details |
|---|---|---|---|
| D-1 | Mechanic scoring/feedback not in frontend Mechanic type | HIGH | Blueprint has it, frontend ignores it. |
| D-2 | group_only field on IDZone not in frontend Zone | MEDIUM | Frontend has no concept of group-only zones. |
| D-3 | IDScene.sounds and IDScene.assets not in frontend GameScene | LOW | Not used yet. |

---

## Rename Scope Summary (E1-E3)

**LABEL_DIAGRAM → INTERACTIVE_DIAGRAM**
**LabelDiagramGame → InteractiveDiagramGame**

| Category | Files Affected |
|---|---|
| Backend `.py` with `LABEL_DIAGRAM` literal | 77 |
| Frontend `.ts/.tsx` with `LABEL_DIAGRAM` | 9 |
| Component directory (LabelDiagramGame/) | 51 |
| Backend with `label_diagram` in paths/vars | 33 |
| Backend prompts | 2 |
| Backend presets | 2 |
| **Total unique files** | **~100+** |

**Critical rename files (must update together):**
1. `backend/app/agents/router.py` — TEMPLATE_REGISTRY key (line 75)
2. `backend/app/agents/schemas/blueprint_schemas.py` — validation (line 900)
3. `backend/app/tools/blueprint_assembler_tools.py` — templateType output (lines 721, 737)
4. `frontend/src/app/game/[id]/page.tsx` — conditional rendering (line 328)
5. `frontend/src/components/templates/LabelDiagramGame/` — entire directory rename

---

## Recommended Fix Order (Revised Feb 10)

### Phase 0: Critical One-Line Fixes (**DONE**)

1. ~~**Fix canonical_labels routing** (CC-1)~~ — **DONE (F1)**
2. ~~**Fix generation_complete** flag~~ — **DONE**
3. ~~**Type MechanicConfigV3.config**~~ — **DONE (F2)** (auto-promotion validator added to SceneSpecV3)

### Phase 1: Frontend State & Logic Fixes (~746 lines across ~9 files)

4. **Fix removeLabel** — Update completedZoneIds, call updateVisibleZones() (S-10, S-11) — Fix 1.1
5. **Fix score accumulation** — Delta-based scoring for updatePathProgress, updateIdentificationProgress, recordDescriptionMatch (S-33, S-34, S-35) — Fix 1.2
6. **Fix completion detection** — Per-mode label counting in placeLabel and checkModeTransition (S-6, S-18) — Fix 1.3
7. **Fix hasRemainingModes** — Explicit remaining count for 3+ mechanics (S-7) — Fix 1.4
8. **Fix setTimeout leak** — Store timer ID, clean up on reset/init (S-20) — Fix 1.5
9. **Fix transitionToMode immutability** — Don't mutate modeHistory in-place (S-23) — Fix 1.6
10. **Full Zustand integration for ALL 6 non-drag_drop mechanics** (IC-1 through IC-6, S-2, S-24) — Fix 1.7a-1.7h:
    - New types: SequencingProgress, SortingProgress, MemoryMatchProgress, BranchingProgress, CompareProgress (1.7a)
    - New store state fields + 12 new actions (1.7b, 1.7g)
    - Initialize all mode states in `initializeGame` and `transitionToMode` (1.7c, 1.7d)
    - Add 6 new transition triggers (1.7e)
    - Per-mechanic maxScore calculation in `completeInteraction` (1.7f)
    - Refactor 6 interaction components to sync with store via props (dual-state pattern) (1.7h)
11. **Fix advanceToNextTask scoring** — Use maxScore, not actual score for TaskResult.max_score (S-27) — Fix 1.8
12. **Fix handleDescriptionMatch** — Compare label.correctZoneId to zoneId, not zone.id to labelId (IC-9) — Fix 1.9
13. **resetGame clear all states** — Clear sequencingProgress, sortingProgress, etc. on reset — Fix 1.11
14. **Destructure new store actions** — Add 12 new actions + 5 progress fields to index.tsx destructuring — Fix 1.12

### Phase 2: Backend — Full Mechanic Pipeline (12 fixes, ~635 lines across ~10 files)

15. **V3 Context** — Expose sequence_flow_data, content_characteristics, hierarchical_relationships to tool layer (Fix 2.1)
16. **DK Retriever** — Add per-mechanic data retrieval: `_search_for_descriptions()`, `_search_for_categories()` (Fix 2.2)
17. **Game Designer V3** — Output full GameDesignV3 (not Slim) with per-mechanic configs populated from DK data (Fix 2.3)
18. **Design Validator** — Auto-fixed by Fix 2.3 (schema mismatch resolved, existing checks L109-164 will fire) (Fix 2.4)
19. **Scene Architect V3** — New `generate_mechanic_content` tool: produce waypoints, prompts, items, descriptions per scene (Fix 2.5)
20. **Scene Validator** — Already has F3 checks (no changes needed) (Fix 2.6)
21. **Interaction Designer V3** — New `enrich_mechanic_content` tool: pedagogical prompt ordering, rich descriptions, step explanations (Fix 2.7)
22. **Interaction Validator** — Content presence checks (prompts, descriptions) (Fix 2.8)
23. **Asset Generator V3** — Mechanic-aware zone validation in submit_assets (Fix 2.9)
24. **Blueprint Assembler V3** — Populate per-mechanic config fields at blueprint + scene level (sequenceConfig, paths, identificationPrompts, etc.) (Fix 2.10)
25. **Blueprint Validator + Repair** — Mechanic-specific checks + auto-repair (generate prompts from zones) (Fix 2.11)
26. **check_capabilities** — Update status to reflect actual support levels (Fix 2.12)

### Phase 3: Data Flow & Type Safety (~68 lines across ~3 files)

27. **Type frontend Mechanic** — Add scoring, feedback fields to match backend IDMechanic (B-3, D-1) — Fix 3.1
28. **Make GameScene.tasks required** — Always create 1 implicit task (B-4, T-6) — Fix 3.2
29. **Fix normalizeBlueprint phantom zones** — Replace with semantic zone label matching (N-3) — Fix 3.3
30. **Forward mechanic scoring/feedback to frontend** — Blueprint assembler currently drops scoring/feedback at L654-662; forward them (F1, D-1) — Fix 3.4
31. **Fix normalizeBlueprint label→zone queue** — Replace FIFO queue with semantic text matching (N-1) — Fix 3.5

### Phase 4: Architecture & Quality (~45 lines across ~3 files)

32. **Reclassify hierarchy** — Add HierarchyConfig to Mechanic, make cross-cutting modifier (T-1, B-4) — Fix 4.1 **DEFERRED**
33. **Fix persistence restore** — Wire onLoad to restore state to store, update save to include all mechanic progress (PS-2) — Fix 4.2
34. **Mutex transitivity** — S-14 — Fix 4.3 **DEFERRED**
35. **Implement time_elapsed trigger** — Basic implementation in checkModeTransition (S-19) — Fix 4.4

### Phase 5: Rename (~150+ files)

36. **LABEL_DIAGRAM → INTERACTIVE_DIAGRAM** across ~135 backend + ~24 frontend files
37. **LabelDiagramGame/ → InteractiveDiagramGame/** directory rename (51 files)
38. **Backend file renames** — label_diagram.py, blueprint_label_diagram.txt, preset configs
39. **Database backward compat** — Accept both LABEL_DIAGRAM and INTERACTIVE_DIAGRAM
40. **Verification script** — Automated check for stale references + compilation

### Phase 6: Polish

41. Fix accessibility gaps (ARIA labels for non-drag_drop mechanics)
42. Performance optimizations (normalizeBlueprint O(n²), updateVisibleZones)
43. Complete undo/redo for all modes
44. Blueprint input validation on frontend load
45. Per-mechanic feedback rendering (use scoring/feedback from Mechanic type)
46. Asset workflow integration (mechanic-specific asset generation sub-workflows)
47. usePersistence: implement hintsUsed, incorrectAttempts, elapsedTimeMs tracking

---

## What's Working Today (No Changes Needed)

- drag_drop end-to-end on V3 pipeline (single-mechanic only)
- Multi-scene game progression (scenes + task advancement for drag_drop)
- Zone coordinate normalization and flattening (backend IDZone._normalize_coordinates)
- Asset URL resolution (frontend proxy)
- Temporal constraints for hierarchy (parent-child reveal, mutex)
- Blueprint assembly for drag_drop (zones, labels, scoring, feedback)
- Frontend DnD system (@dnd-kit integration)
- Accessibility layer (ARIA, keyboard nav, screen reader — for drag_drop)
- Undo/redo for drag_drop
- Observability pipeline UI (timeline, token charts, ReAct trace)

---

## Cross-Reference: Audit Documents

| Doc | File | Content | Bug Count |
|---|---|---|---|
| 01 | `docs/audit/01_v3_pipeline_map.md` | Backend agent-by-agent deep audit with line numbers | 77 |
| 02 | `docs/audit/02_frontend_engine_map.md` | Frontend component-by-component deep audit with line numbers | 121 |
| 03 | `docs/audit/03_mechanic_support_matrix.md` | Per-mechanic gap analysis across full pipeline | 52 |
| 04 | `docs/audit/04_domain_knowledge_audit.md` | Domain knowledge retriever schema and per-mechanic data needs | — |
| 05 | `docs/audit/05_data_flow_trace.md` | State field propagation: agent→state→agent→blueprint→frontend | — |
| 06 | `docs/audit/06_asset_generation_audit.md` | Per-scene, per-mechanic asset generation gaps | — |
| 07 | `docs/audit/07_master_findings.md` | **This document** — consolidated findings and fix plan | ~178 unique |
| **08** | **`docs/audit/08_implementation_plan.md`** | **Detailed implementation plan with exact code changes per phase** | — |
