# Audit Doc 02: Frontend Game Engine — Exhaustive Deep Audit v2

> **Generated:** 2026-02-10 | **Status:** Complete | **Scope:** Full line-by-line audit of all frontend game engine components
> **Files Audited:** 45 files | **LOC Reviewed:** ~9,000 | **Total Issues:** 115 bugs + 6 missing features

---

## Table of Contents

1. [Component Hierarchy](#1-component-hierarchy)
2. [Type System (types.ts)](#2-type-system)
3. [Blueprint Normalization (index.tsx)](#3-blueprint-normalization)
4. [State Management (useLabelDiagramState.ts)](#4-state-management)
5. [Core Display Components](#5-core-display-components)
6. [Interaction Components](#6-interaction-components)
7. [Supporting Hooks](#7-supporting-hooks)
8. [Multi-Scene System](#8-multi-scene-system)
9. [Mode Transition System](#9-mode-transition-system)
10. [Data Flow Mismatches](#10-data-flow-mismatches)
11. [Silent Failure Catalog](#11-silent-failure-catalog)
12. [Accessibility Gaps](#12-accessibility-gaps)
13. [Performance Issues](#13-performance-issues)
14. [Missing Features](#14-missing-features)
15. [Consolidated Bug Count](#15-consolidated-bug-count)

---

## 1. Component Hierarchy

**Base path:** `frontend/src/components/templates/LabelDiagramGame/`

```
LabelDiagramGame (index.tsx — main export, to be renamed InteractiveDiagramGame)
├── GameErrorBoundary (ErrorBoundary.tsx)
├── AnnouncementProvider (accessibility/)
├── KeyboardNav (accessibility/)
└── LabelDiagramGameInner (index.tsx:281)
    ├── DndContext (@dnd-kit drag-drop system)
    │   ├── DiagramCanvas (DiagramCanvas.tsx)
    │   │   ├── PolygonOverlay (DiagramCanvas.tsx:44 — single full-canvas SVG)
    │   │   ├── MediaAssetsLayer (DiagramCanvas.tsx)
    │   │   └── DropZone[] (DropZone.tsx — per-zone targets)
    │   ├── LabelTray (LabelTray.tsx — draggable label pool)
    │   │   └── DraggableLabel[] (DraggableLabel.tsx)
    │   ├── DragOverlay (index.tsx:1124 — smooth drag ghost)
    │   ├── GameControls (GameControls.tsx — hints, reset, score, progress)
    │   │   └── TaskProgressBar (GameControls.tsx:11 — multi-task indicator)
    │   └── Interaction Components (mode-specific, index.tsx:767-1131):
    │       ├── HotspotManager (click_to_identify)
    │       ├── PathDrawer (trace_path)
    │       ├── HierarchyController (hierarchical)
    │       ├── DescriptionMatcher (description_matching)
    │       ├── SequenceBuilder (sequencing)
    │       ├── CompareContrast (compare_contrast)
    │       ├── SortingCategories (sorting_categories)
    │       ├── MemoryMatch (memory_match)
    │       ├── BranchingScenario (branching_scenario)
    │       ├── TimedChallengeWrapper (timed_challenge)
    │       ├── GameSequenceRenderer (multi-scene)
    │       ├── ModeIndicator (multi-mode switching)
    │       └── UndoRedoControls
    ├── SceneTransition (SceneTransition.tsx — transition animations)
    ├── SceneIndicator (SceneTransition.tsx — progress dots)
    ├── ResultsPanel (ResultsPanel.tsx — completion screen)
    └── Restore prompt (index.tsx:391-434 — saved game recovery)
```

**Key directories:**
- `hooks/` — State management (useLabelDiagramState, useCommandHistory, useEventLog, usePersistence, useReducedMotion, useZoneCollision)
- `interactions/` — Per-mechanic components (11 modules)
- `animations/` — Animation system (Confetti, etc.)
- `accessibility/` — A11y providers (AnnouncementProvider, KeyboardNav)
- `commands/` — Command pattern for undo/redo
- `events/` — Event logging
- `persistence/` — Save/load

---

## 2. Type System

**File:** `types.ts` (700 lines)

### InteractionMode (11 types)

```typescript
type InteractionMode =
  | 'drag_drop'            // Place labels on zones
  | 'click_to_identify'    // Click zones when prompted
  | 'trace_path'           // Follow waypoint order
  | 'hierarchical'         // Progressive reveal (SHOULD BE MODIFIER, NOT MODE)
  | 'description_matching' // Match descriptions to zones
  | 'compare_contrast'     // Compare two diagrams
  | 'sequencing'           // Order items chronologically
  | 'timed_challenge'      // Race against clock (wrapper)
  | 'sorting_categories'   // Bin items into categories
  | 'memory_match'         // Flip card pairs
  | 'branching_scenario'   // Decision tree
```

### Bug Table: types.ts

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| T-1 | 9 | HIGH | `hierarchical` is an InteractionMode instead of cross-cutting modifier | Architecture: prevents hierarchical+drag_drop, hierarchical+trace_path combos. Must be a config field on SceneTask, not a mode. |
| T-2 | 51-54 | HIGH | `Mechanic.config` typed as `Record<string, unknown>` | No type safety for per-mechanic configs. SequenceConfig, SortingConfig etc. must be accessed via optional blueprint-level fields instead. |
| T-3 | 193-197 | MEDIUM | `Label` has no `is_distractor` field — detection via `'correctZoneId' in label` runtime check | Fragile type narrowing. If someone adds correctZoneId to DistractorLabel, detection breaks. |
| T-4 | 232-241 | MEDIUM | `SceneTask.config` typed as `Record<string, unknown>` | Same untyped config issue as Mechanic.config. Per-task mechanic config inaccessible without casting. |
| T-5 | 440 | HIGH | `LabelDiagramBlueprint.templateType` hardcoded to `'LABEL_DIAGRAM'` | Must be updated to `'INTERACTIVE_DIAGRAM'` or made a union. All consumers check this literal. |
| T-6 | 580-623 | MEDIUM | `GameScene.tasks` is optional (`tasks?: SceneTask[]`) | Should be required (always at least 1 implicit task). Every consumer must null-check. |
| T-7 | 580-623 | LOW | `GameScene` duplicates all config fields from `LabelDiagramBlueprint` (paths, sequenceConfig, etc.) | DRY violation. Scene→Blueprint conversion (`_sceneToBlueprint`) manually copies 15+ fields. |
| T-8 | 51-54 | MEDIUM | `Mechanic` type has no `scoring`, `feedback`, or `misconception_feedback` fields | Backend IDMechanic includes these but frontend Mechanic ignores them. Scoring/feedback data lost in type boundary. |

---

## 3. Blueprint Normalization

**File:** `index.tsx` (lines 111-204)

### `normalizeBlueprint()` — O(n^2) zone/label reconciliation

**Flow:** Deduplicate zone IDs → Deduplicate label IDs → Map labels to zones via queue system → Create phantom zones for orphan labels.

### Bug Table: normalizeBlueprint

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| N-1 | 117-133 | HIGH | Zone ID queue system can produce incorrect label→zone mappings when multiple labels reference the same original zone ID | If zone `z1` is duplicated to `z1` and `z1_2`, labels are assigned by FIFO queue order, not by semantic correctness. Label "Mitochondrion" could get mapped to `z1_2` instead of `z1`. |
| N-2 | 152-168 | HIGH | `assignedZoneIds` prevents two labels from mapping to the same zone, but creates synthetic zone IDs (`mappedZoneId_1`) that don't exist in the zone list | These phantom zone IDs pass through but have no matching DropZone — label can never be placed correctly. |
| N-3 | 180-192 | CRITICAL | Fallback zone creation for orphan labels places zones in a grid pattern unrelated to the diagram | If a label's `correctZoneId` doesn't match any zone, a new zone is created at a generated grid position (e.g., x:33%, y:33%). This produces unplayable games where zones appear at random positions. |
| N-4 | 111-204 | HIGH | `normalizeBlueprint` runs inside `useMemo` but performs O(n^2) work (zone collision, label mapping) | With 100 zones, this is 10,000 operations every time `blueprint` reference changes. No caching of intermediate results. |
| N-5 | 119-133 | LOW | Zone deduplication appends `_2`, `_3` suffixes without updating references in `parentZoneId`, `childZoneIds`, temporal constraints, or zone groups | Hierarchy relationships break when parent zone ID gets renamed. |
| N-6 | 72-85 | LOW | `coerceDimension` accepts pixel strings like `"800px"` but not percentage strings `"100%"` | Backend could theoretically send percentage-based dimensions, which would fall through to the fallback. |

### `migrateMultiSceneBlueprint()` — index.tsx:210-275

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| N-7 | 216 | MEDIUM | Migration skipped if ANY scene already has tasks, even if only some do | Partial migration not handled. If scene 1 has tasks but scene 3 doesn't, the imageless scene 3 won't get merged. |
| N-8 | 248-255 | MEDIUM | Zone/label dedup during merge uses ID matching, but IDs could collide across scenes | If scene 1 and scene 3 both have a zone `z1`, the merge keeps scene 1's version and drops scene 3's. |

---

## 4. State Management

**File:** `hooks/useLabelDiagramState.ts` (1066 lines, Zustand store)

### Core State Fields

| Field | Type | Purpose | Issues |
|-------|------|---------|--------|
| `availableLabels` | `(Label\|DistractorLabel)[]` | Labels in tray | Union type requires runtime `'correctZoneId' in label` checks |
| `placedLabels` | `PlacedLabel[]` | Placed labels | Only tracks drag_drop. No tracking for sequencing, sorting, etc. |
| `score` / `maxScore` | `number` | Scoring | Single score for all modes. Multi-mode scores not separated. |
| `basePointsPerZone` | `number` | Points per correct | Fixed value, not per-mechanic |
| `interactionMode` | `InteractionMode` | Active mechanic | Single mode, no composite modes |
| `pathProgress` | `PathProgress \| null` | trace_path state | Only initialized if starting mode is trace_path |
| `identificationProgress` | `IdentificationProgress \| null` | click_to_identify state | Only initialized if starting mode is click_to_identify |
| `hierarchyState` | `HierarchyState \| null` | hierarchy state | Only initialized if starting mode is hierarchical |
| `multiModeState` | `MultiModeState \| null` | Multi-mechanic tracking | Initialized only if >1 mechanic. Score history always 0. |
| `completedZoneIds` | `Set<string>` | Completed zones | Not updated on `removeLabel` — zone remains "completed" |
| `visibleZoneIds` | `Set<string>` | Visible zones | Not recalculated on `removeLabel` |
| `blockedZoneIds` | `Set<string>` | Mutex-blocked zones | No transitive mutex support |

### Bug Table: initializeGame (lines 214-338)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-1 | 222 | LOW | `Math.random() - 0.5` shuffle is biased (not Fisher-Yates) | Label order has slight bias toward original positions. Not random uniform. |
| S-2 | 228-253 | CRITICAL | Mode-specific state only initialized for the STARTING mode. If game starts as drag_drop but transitions to trace_path, pathProgress is null when transitionToMode runs. | Transition target modes have null state until `transitionToMode` initializes them, but `transitionToMode` only initializes 3 modes (trace_path, click_to_identify, hierarchical). sequencing/sorting/memory/branching never initialized. |
| S-3 | 278-294 | MEDIUM | `multiModeState` only created if `allModes.length > 1 || modeTransitions.length > 0` | Single-mechanic games with manual mode switching (`user_choice` transitions) won't have multiModeState. |
| S-4 | 307 | MEDIUM | `basePointsPerZone` from `blueprint.scoringStrategy?.base_points_per_zone` is a single value for all modes | Multi-mechanic games should support different point values per mechanic. |

### Bug Table: placeLabel (lines 340-413)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-5 | 351 | MEDIUM | Distractor detection via `!('correctZoneId' in label)` | Fragile runtime type check. Any label with a `correctZoneId` property (even if undefined) passes the check incorrectly. |
| S-6 | 364-370 | HIGH | Completion check: `placedCorrectCount >= correctLabelsCount` counts ALL blueprint labels, not just current-mode labels | In multi-mechanic game where drag_drop has 5 labels and the game has 10 total, drag_drop can never trigger completion because 5 < 10. |
| S-7 | 368-370 | HIGH | `hasRemainingModes` logic: `completedModes.length + 1 < availableModes.length` — the `+1` is wrong | This counts the current mode as already completed. If 2 modes total and 0 completed, `0 + 1 < 2` = true (correct). But if 3 modes and 1 completed, `1 + 1 < 3` = true (should be false if current is being completed). Edge case: game never ends with 3+ mechanics. |
| S-8 | 379 | MEDIUM | Score increments by fixed `basePointsPerZone` regardless of zone difficulty or mechanic type | Zone difficulty field (1-5) is defined in types.ts but never used in scoring. |
| S-9 | 390-392 | LOW | `checkModeTransition()` called even on non-multi-mode games (when `allLabelsPlaced || !isComplete`) | The function handles `!multiModeState` with early return, but unnecessary call overhead on every correct placement. |

### Bug Table: removeLabel (lines 416-435)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-10 | 416-435 | CRITICAL | `removeLabel` does NOT update `completedZoneIds` | Zone remains "completed" even after its label is removed. Children zones stay visible, mutex constraints stay unblocked — temporal intelligence state is stale. |
| S-11 | 416-435 | HIGH | `removeLabel` does NOT call `updateVisibleZones()` | After removing a label, child zones that were revealed by the parent completion remain visible when they should hide. |
| S-12 | 432 | MEDIUM | Score decremented by `basePointsPerZone` but no floor check | Score can go negative if `removeLabel` is called on a label whose placement didn't actually add points (e.g., distractor). |
| S-13 | 426-427 | LOW | Only looks up label in `blueprint.labels`, not `blueprint.distractorLabels` | If a distractor label is somehow placed and then removed, it won't be found and the function returns early. |

### Bug Table: updateVisibleZones (lines 666-742)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-14 | 699-709 | HIGH | Mutex constraint only handles direct relationships, not transitive | If A mutex B and B mutex C, zones A and C can both be visible simultaneously. No transitive closure computed. |
| S-15 | 673-674 | MEDIUM | `visible` and `blocked` sets rebuilt from scratch on every call | No diffing — if 50 zones are visible, all 50 are re-evaluated. Not incremental. |
| S-16 | 713 | LOW | `zone.hierarchyLevel === 1 || !zone.hierarchyLevel` — treats missing hierarchyLevel as root | Correct behavior, but undocumented assumption. Backend could send `hierarchyLevel: 0` which would be treated as non-root (falsy). |
| S-17 | 722-736 | LOW | Child reveal only looks at direct parent completion, not ancestor chain | Grandchildren require parent (not grandparent) to be completed. This is correct hierarchical behavior but means two separate completions are needed. |

### Bug Table: checkModeTransition (lines 781-865)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-18 | 794-799 | HIGH | `all_zones_labeled` trigger counts ALL labels against ALL blueprint labels | In a multi-mechanic game, completing drag_drop's 5 labels doesn't trigger transition because blueprint has 10 labels total (including other mechanic zones). |
| S-19 | 843-845 | HIGH | `time_elapsed` trigger has comment "handled by timer in component" but NO component implements it | Time-based mode transitions defined in InteractionSpecV3 but never functional in frontend. Dead feature. |
| S-20 | 858-860 | HIGH | `setTimeout` for mode transition never cleaned up on component unmount | Memory leak: if player navigates away during the 500ms transition delay, the timeout fires on unmounted state. |
| S-21 | 810-813 | MEDIUM | `percentage_complete` uses hardcoded `50` as default threshold if `triggerValue` not provided | Should use a more meaningful default or require triggerValue. |
| S-22 | 817-821 | LOW | `specific_zones` trigger assumes `triggerValue` is `string[]` with no type check | If backend sends a number or string, `.every()` call fails silently. |

### Bug Table: transitionToMode (lines 867-943)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-23 | 875-877 | HIGH | Mutates `currentModeHistory` object directly instead of creating new copy | `modeHistory` array element is mutated in-place, violating Zustand immutability expectations. Could cause missed re-renders. |
| S-24 | 889-919 | CRITICAL | Only 3 modes initialized on transition: trace_path, click_to_identify, hierarchical | Transitioning to sequencing, sorting_categories, memory_match, branching_scenario, description_matching, or compare_contrast produces null state for the target mode. Those components must manage their own state (they do, locally), but completion detection from the centralized store never fires. |
| S-25 | 937 | HIGH | New mode's `modeHistory` entry starts with `score: 0` | The accumulated score from the previous mode is preserved in `state.score`, but the per-mode history entry always shows 0. Cumulative score display correct; per-mode breakdown wrong. |
| S-26 | 921-942 | MEDIUM | `isComplete` reset to `false` on transition, but `placedLabels` and `availableLabels` not reset | Next mode starts with the previous mode's placed labels still in state. If the new mode is sequencing, the drag_drop placedLabels persist. |

### Bug Table: advanceToNextTask (lines 1012-1055)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-27 | 1026 | HIGH | `max_score` in TaskResult calculated as `placedLabels.filter(p => p.isCorrect).length * basePointsPerZone` | This computes actual score, not max possible score. Should be `state.maxScore` or zone count * points. A perfect game records `max_score = score`, making percentage always 100% regardless of actual performance. |
| S-28 | 1042-1043 | MEDIUM | `initializeGame(bp)` called for next task, which resets ALL state including score | UI flickers as labels re-shuffle. Score resets to 0 for the new task. Total score across tasks not accumulated until `completeCurrentScene`. |
| S-29 | 1052-1053 | MEDIUM | `completeCurrentScene()` then `advanceToNextScene()` called sequentially | Two separate state updates cause two re-renders. The first sets scene result, the second navigates. Could cause brief intermediate state. |
| S-30 | 1012-1014 | LOW | Silent return if `!gameSequence || !multiSceneState` | No warning logged. If called on a single-scene game by mistake, silently does nothing. |

### Bug Table: completeInteraction (lines 489-546)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-31 | 501-527 | MEDIUM | `maxScore` recalculated per mode in switch statement, overwriting blueprint max_score | Blueprint may have a validated max_score from backend, but this function replaces it based on local zone/label/waypoint counts. |
| S-32 | 530-540 | MEDIUM | Multi-mode remaining check triggers `checkModeTransition()` without setting score first | The `set()` that updates `isComplete` and `maxScore` (line 542) only runs after the remaining mode check. If `checkModeTransition` reads score, it gets stale value. |

### Bug Table: updatePathProgress / updateIdentificationProgress

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-33 | 456-466 | MEDIUM | `updatePathProgress` overwrites global `score` with path-only score | In a multi-mechanic game where drag_drop scored 50pts and then trace_path starts, the first waypoint click resets score to `1 * basePointsPerZone` (10), losing the 50. |
| S-34 | 468-483 | MEDIUM | `updateIdentificationProgress` same issue — overwrites global score | Same as S-33. Should add to existing score, not replace. |

### Bug Table: recordDescriptionMatch (lines 638-660)

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| S-35 | 645 | MEDIUM | Score calculated from matches only, same overwrite issue | Same pattern as S-33/S-34. Multi-mechanic score accumulation broken. |
| S-36 | 648 | LOW | Completion check: `zonesWithDescriptions` counts zones with `description` field | If backend doesn't populate zone descriptions (common — see audit doc 01 gap A6b), this array is empty and game completes immediately on first match. |

---

## 5. Core Display Components

### DiagramCanvas.tsx

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| DC-1 | 66 | MEDIUM | PolygonOverlay uses `preserveAspectRatio="none"` on SVG viewBox `"0 0 100 100"` | On non-square images, polygon zones stretch to fill, distorting their positions. Zones designed for an 800x600 image appear at wrong positions on a 600x600 viewport. |
| DC-2 | 56 | LOW | Polygon zone filter: `z.shape === 'polygon' && z.points && z.points.length >= 3` doesn't validate coordinate values | Points array could contain NaN or negative values. No sanity check on point data. |
| DC-3 | 79 | LOW | `smoothPolygonPath` casts `zone.points as [number, number][]` without validation | If points are `[string, string][]` from a loose backend, Catmull-Rom math produces NaN. |

### DropZone.tsx

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| DZ-1 | 53-100 | MEDIUM | `calculateZoneOffset` collision detection only handles circle zones (uses `zone.radius`) | Polygon and rect zones have no collision avoidance. Overlapping polygon zones stack on top of each other. |
| DZ-2 | 60-64 | MEDIUM | `isLayeredChild` check only looks at `zoneGroups[].childZoneIds` — doesn't check if the zone IS a parent | Parent zones still get offset pushed away from their children, breaking the layered visual. |
| DZ-3 | 10-18 | LOW | `polygonPointsToSvgPath` creates straight-line polygon (M/L/Z) while DiagramCanvas uses smooth Catmull-Rom curves | Visual mismatch: DropZone's hit area is a polygon, but the overlay SVG is a smooth curve. Clicks near curved edges may miss. |
| DZ-4 | — | MEDIUM | Zone focus order: `zone.focusOrder ?? (zoneIndex \|\| 0)` — fallback to index only works if zones are ordered correctly | If zones are shuffled or filtered by task, index-based focus order doesn't match visual layout. |
| DZ-5 | — | LOW | Hierarchy color array hardcoded: `['#60a5fa', '#a78bfa', '#2dd4bf']` | Not configurable, not responsive to dark mode. Blue on dark background may have low contrast. |

### DraggableLabel.tsx

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| DL-1 | 25 | LOW | `opacity: 0.5` during drag — label remains visible in tray as ghost | Visual confusion: label appears both in tray (50% opacity) and as drag overlay. Should hide from tray. |
| DL-2 | 41 | LOW | References `animate-shake` CSS class that may not be defined in project styles | If tailwind config doesn't include this keyframe, no shake animation plays on incorrect. Only red border shows. |

### GameControls.tsx

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| GC-1 | 12 | LOW | `TaskProgressBar` hidden if `tasks.length <= 1` | Single-task scenes show no progress indicator. User doesn't know they're in a scene-based game. |
| GC-2 | 73 | LOW | Task progress only shown when `taskProgress.tasks.length > 1` | Redundant with GC-1 but shows the intent is to hide single-task scenes from progress display. |

### ResultsPanel.tsx

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| RP-1 | 34 | LOW | Confetti triggers at `greatThreshold` (70% default), not just perfect | Design choice, but 70% accuracy games get confetti which may feel unearned. |
| RP-2 | 50-52 | LOW | Hardcoded emojis may not render on all systems | Minor: emoji rendering is browser-dependent. |
| RP-3 | — | MEDIUM | No "exit game" button — only "Play Again" and optional "New Game" | If `onNewGame` not provided, player cannot leave the results screen without navigating away. |

---

## 6. Interaction Components

### Per-Mechanic Store Integration Status

| Mechanic | Component | Store Actions | Completion Detection | Score Tracking | Undo/Redo |
|----------|-----------|---------------|---------------------|----------------|-----------|
| drag_drop | DiagramCanvas + DropZone + LabelTray | `placeLabel`, `removeLabel` | `placedLabels` count vs `labels.length` | `basePointsPerZone` per correct | YES (PlaceLabelCommand) |
| click_to_identify | HotspotManager | `updateIdentificationProgress` | `currentPromptIndex >= prompts.length` | `completedZoneIds.length * basePointsPerZone` | NO |
| trace_path | PathDrawer | `updatePathProgress` | `pathProgress.isComplete` | `visitedWaypoints.length * basePointsPerZone` | NO |
| hierarchical | HierarchyController | `updateHierarchyState`, `placeLabel` | via drag_drop completion | via drag_drop scoring | Partial (drag_drop only) |
| description_matching | DescriptionMatcher | `recordDescriptionMatch` | `currentIndex >= zonesWithDescriptions.length` | `matches.filter(correct).length * basePointsPerZone` | NO |
| sequencing | SequenceBuilder | **NONE** — fully local state | Local `isCorrect` callback | Local only, not in store | NO |
| sorting_categories | SortingCategories | **NONE** — fully local state | Local `isCorrect` callback | Local only, not in store | NO |
| memory_match | MemoryMatch | **NONE** — fully local state | Local `isComplete` callback | Local only, not in store | NO |
| branching_scenario | BranchingScenario | **NONE** — fully local state | Local `isComplete` callback | Local only, not in store | NO |
| compare_contrast | CompareContrast | **NONE** — fully local state | Local callback | Local only, not in store | NO |
| timed_challenge | TimedChallengeWrapper | **NONE** — wrapper only | `onTimeUp` callback | Delegates to wrapped mode | NO |

### Bug Table: Interaction Component Integration

| # | Component | Severity | Issue | Impact |
|---|-----------|----------|-------|--------|
| IC-1 | sequencing | CRITICAL | Zero store integration. State is entirely local. `completeInteraction()` is called but score stays at 0. | Sequencing games show 0 score on ResultsPanel. advanceToNextTask records 0 score TaskResult. |
| IC-2 | sorting_categories | CRITICAL | Zero store integration. Same as IC-1. | Score lost. Multi-task/multi-scene accumulation broken. |
| IC-3 | memory_match | HIGH | Zero store integration. Same pattern. | Score lost on completion. |
| IC-4 | branching_scenario | HIGH | Zero store integration. Same pattern. | Score lost on completion. |
| IC-5 | compare_contrast | HIGH | Zero store integration. Same pattern. | Score lost on completion. |
| IC-6 | All 5 above | HIGH | `advanceToNextTask()` checks `placedLabels` for completion detection | Non-drag_drop mechanics don't populate `placedLabels`. Task never detected as complete. Multi-task games hang after first non-drag_drop task. |
| IC-7 | index.tsx:1085 | LOW | Missing semicolon after BranchingScenario return (has `)` without `;`) | Not actually a bug — JS ASI handles this. But inconsistent with other case blocks that have semicolons. |
| IC-8 | index.tsx:1022 | MEDIUM | sorting_categories, memory_match, branching_scenario all fall back to `drag_drop` when config is missing | User sees drag_drop instead of an error message. Confusing UX — game appears to "work" but with wrong mechanic. |
| IC-9 | index.tsx:760 | MEDIUM | `handleDescriptionMatch` determines correctness via `zone.id === labelId` | This compares a zone ID to a label ID, which are different namespaces. Should match zone.label to label.text or use a mapping. |

### Per-Component Issues

#### HotspotManager (click_to_identify)

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| HM-1 | HIGH | Component renders but receives empty `prompts` array when backend doesn't generate `identificationPrompts` | No prompts shown. User sees zones but has no instruction what to click. Game is unplayable. |
| HM-2 | MEDIUM | Maintains internal state (click highlights, prompt display) even when external `identificationProgress` updates | Dual state source can cause visual inconsistencies between store progress and component display. |

#### PathDrawer (trace_path)

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| PD-1 | HIGH | Component renders but receives empty `paths` array when backend doesn't generate path/waypoint data | No paths shown. User sees diagram but can't interact. |
| PD-2 | MEDIUM | `handlePathWaypointClick` (index.tsx:700-722) doesn't validate waypoint order — any waypoint click adds to visited | User can click waypoints out of order on a `requiresOrder: true` path. |

#### SequenceBuilder (sequencing)

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| SB-1 | HIGH | Component receives `items` from `bp.sequenceConfig` but backend rarely populates this field | Falls back to labels (index.tsx:854-871), which makes labels the "sequence items" — semantically wrong. |
| SB-2 | MEDIUM | `onComplete` callback passes result to `completeInteraction()` but score is not propagated to store | Store score stays at 0. Only `isComplete` gets set via `completeInteraction()`. |

#### DescriptionMatcher (description_matching)

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| DM-1 | HIGH | Requires zones with `description` field populated. Backend asset gen doesn't generate functional descriptions. | Zones have anatomical names but no functional descriptions. Game falls back to label-text matching, which is trivially easy. |
| DM-2 | MEDIUM | `handleDescriptionMatch` correctness check (index.tsx:760) is broken — compares zone.id to labelId | Always incorrect unless IDs happen to match. |

---

## 7. Supporting Hooks

### useCommandHistory.ts

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| CH-1 | MEDIUM | Single CommandHistory instance per hook — shared across games if multiple mount | If two game instances exist (unlikely but possible in testing), undo in one affects the other. |
| CH-2 | MEDIUM | Keyboard shortcuts (`Ctrl+Z`, `Ctrl+Y`) always active on `window` | If game is in background or multiple games exist, wrong game's undo triggers. |
| CH-3 | LOW | Only tracks `PlaceLabelCommand` — no command types for path drawing, sequencing, or other mechanics | Undo/redo exclusively for drag_drop. All other modes have no undo support. |

### usePersistence.ts

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| PS-1 | MEDIUM | Saves game progress state but not the blueprint itself | Restoring requires blueprint to be re-fetched from API. If blueprint changes between save and load, state is inconsistent. |
| PS-2 | MEDIUM | `onLoad` callback announces "progress restored" but doesn't actually restore state to the store | The callback receives `SavedGameState` but there's no mechanism to feed it back into `useLabelDiagramState`. Save exists but restore is broken. |
| PS-3 | LOW | `hasSavedGame()` loads the full save file just to check existence | Performance: every mount does a full localStorage read. Should have a metadata-only check. |
| PS-4 | LOW | No auto-save between task transitions | If player crashes during multi-task game, progress since last auto-save (30s interval) is lost. |

### useEventLog.ts

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| EL-1 | MEDIUM | Zone reveal tracking runs on every `visibleZoneIds` change — fires duplicates if `updateVisibleZones()` runs multiple times per action | Multiple "zone revealed" events logged for the same zone in quick succession. |
| EL-2 | MEDIUM | Event log instance not preserved in ref — unmount/remount creates new instance, old events lost | If component remounts (e.g., during task transition), event history resets. |
| EL-3 | LOW | Only logs the starting mode, not all mechanics in a multi-mechanic game | Analytics for mode transitions and multi-mechanic usage incomplete. |

---

## 8. Multi-Scene System

**Components:** `_sceneToBlueprint()` (useLabelDiagramState.ts:33-90), `initializeMultiSceneGame` (line 552), `GameSequenceRenderer` (interactions/)

### Bug Table: Multi-Scene

| # | Location | Severity | Issue | Impact |
|---|----------|----------|-------|--------|
| MS-1 | useLabelDiagramState.ts:54 | HIGH | `_sceneToBlueprint` hardcodes `templateType: 'LABEL_DIAGRAM'` | Every scene blueprint is stamped as LABEL_DIAGRAM regardless of actual template. Must update to INTERACTIVE_DIAGRAM. |
| MS-2 | useLabelDiagramState.ts:33-90 | MEDIUM | `_sceneToBlueprint` manually copies 15+ config fields from GameScene to LabelDiagramBlueprint | Fragile: if a new field is added to GameScene, it must also be added to this function. No type safety forces the update. |
| MS-3 | index.tsx:492 | MEDIUM | `useEffect` for game initialization has many dependencies including `normalizedBlueprint` and `initializeGame` | Re-initialization fires on any blueprint reference change. Zustand `initializeGame` is a new reference each render via `get()`, but `create()` stabilizes it. Still, dependency array is fragile. |
| MS-4 | index.tsx:496-509 | MEDIUM | Task auto-advancement via `useEffect` on `isComplete` fires after 800ms delay | If player completes two tasks rapidly (< 800ms between), the second effect may read stale `multiSceneState` from closure. |
| MS-5 | useLabelDiagramState.ts:573 | LOW | `maxScore` set to `sequence.total_max_score` in multi-scene init | If backend's `total_max_score` doesn't match the sum of scene max_scores, score percentage will be wrong. |
| MS-6 | — | MEDIUM | No auto-save between scene transitions | Progress lost if crash occurs between scenes. Persistence only auto-saves on 30s interval. |

### GameSequenceRenderer

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| GS-1 | MEDIUM | `getNextScene()` doesn't validate that `prerequisite_scene` IDs exist in scenes array | If `prerequisite_scene = "invalid_id"`, the scene is forever locked. No error shown. |
| GS-2 | MEDIUM | Completed scene set rebuilt on every render (`new Set(completedSceneIds)`) without `useMemo` | O(n) allocation per render. Minor perf issue but poor practice. |
| GS-3 | LOW | No visual indication of locked scenes in linear mode | User doesn't know why some scene buttons are disabled. |

---

## 9. Mode Transition System

**Full flow:**
1. Blueprint specifies `mechanics[]` (flat list, first = starting mode)
2. `modeTransitions[]` define graph edges (from → to with trigger)
3. After each action, `checkModeTransition()` evaluates all applicable transitions
4. If triggered: `pendingTransition` set, 500ms setTimeout → `transitionToMode()`

### Transition Triggers — Implementation Status

| Trigger | Defined | Implemented | Notes |
|---------|---------|-------------|-------|
| `all_zones_labeled` | YES | BUGGY | Counts all labels, not per-mode labels (S-18) |
| `path_complete` | YES | YES | Works if pathProgress populated |
| `percentage_complete` | YES | YES | Hardcoded 50% default (S-21) |
| `specific_zones` | YES | YES | No type validation on triggerValue (S-22) |
| `hierarchy_level_complete` | YES | YES | Works with hierarchyState |
| `time_elapsed` | YES | **NOT IMPLEMENTED** | Comment says "handled by timer" but no timer exists (S-19) |
| `user_choice` | YES | PARTIAL | Manual switch via `canSwitchToMode`, but no UI button for it |

### Missing Transition Triggers (needed for non-drag_drop mechanics)

| Trigger | Needed For | Status |
|---------|-----------|--------|
| `sequence_complete` | sequencing → next mechanic | NOT DEFINED |
| `sorting_complete` | sorting_categories → next mechanic | NOT DEFINED |
| `memory_complete` | memory_match → next mechanic | NOT DEFINED |
| `branching_complete` | branching_scenario → next mechanic | NOT DEFINED |
| `description_complete` | description_matching → next mechanic | NOT DEFINED |

---

## 10. Data Flow Mismatches

### Backend → Frontend Type Boundaries

| Data | Backend Type | Frontend Type | Mismatch | Severity |
|------|-------------|---------------|----------|----------|
| Zone coordinates | `Dict[str, Any]` with `{x, y}` dicts | `zone.points: [number, number][]` | Backend sends `coordinates`, frontend expects `points` | HIGH |
| Mechanic config | `MechanicConfigV3.config: Dict[str,Any]` | `Mechanic.config: Record<string, unknown>` | Both untyped — correct data passes through but no validation | MEDIUM |
| Scoring data | `MechanicScoringV3` (typed Pydantic) | Not in frontend `Mechanic` type | Scoring data in blueprint's flat `scoringStrategy` only | HIGH |
| Feedback data | `MechanicFeedbackV3` (typed Pydantic) | `feedbackMessages: FeedbackMessages` (3 strings only) | Per-mechanic feedback with misconception handling lost | HIGH |
| Zone group_only | `IDZone.group_only: bool` | Not in frontend `Zone` type | Backend concept has no frontend representation | LOW |
| Zone mechanic_roles | Not in backend either | Not in frontend | No way to know which zones belong to which mechanic | HIGH |
| templateType | `"LABEL_DIAGRAM"` or `"INTERACTIVE_DIAGRAM"` | `'LABEL_DIAGRAM'` literal | Must be updated in sync | MEDIUM |
| Blueprint IDMechanic | Has scoring, feedback, identificationPrompts, paths, etc. | Frontend Mechanic has `type` + `config: Record<string,unknown>` | Most mechanic-specific fields lost at type boundary | HIGH |

### Coordinate Normalization Gap

**Backend sends:**
```python
# From blueprint_assembler_v3 / detect_zones
zone = {"id": "z1", "coordinates": {"x": 45.2, "y": 32.1}, "shape": "circle", "radius": 5}
```

**Frontend expects:**
```typescript
// Zone type in types.ts
zone = { id: "z1", x: 45.2, y: 32.1, shape: "circle", radius: 5, points?: [number, number][] }
```

**Gap:** Backend `coordinates` dict must be flattened to top-level `x`, `y` fields. The `_normalize_coordinates()` function referenced in MEMORY.md exists in `backend/app/agents/schemas/blueprint_schemas.py` (`IDZone._normalize_coordinates`), but polygon zones specifically need `points` field populated. If the backend sends `coordinates: [{x:10,y:20}, {x:30,y:40}, ...]` for a polygon, the frontend expects `points: [[10,20], [30,40], ...]`.

---

## 11. Silent Failure Catalog

| # | Scenario | What Happens | User Sees | Root Cause |
|---|----------|-------------|-----------|------------|
| SF-1 | Multi-mechanic game, second mechanic is sequencing | `transitionToMode('sequencing')` runs, but SequenceBuilder manages own state. Store score stays 0. `advanceToNextTask` checks `placedLabels` which is empty. | Game transitions to sequencing, player completes it, but nothing happens. Game appears stuck. | IC-1 + S-24: no store integration, no completion trigger |
| SF-2 | removeLabel called → temporal constraints stale | `completedZoneIds` still contains the zone. Children remain visible. | Removing a label doesn't hide child zones that should no longer be visible. | S-10 + S-11 |
| SF-3 | Blueprint with missing zones array | `normalizeBlueprint` creates phantom zones at grid positions | Labels map to random positions on the diagram. Game appears broken. | N-3 |
| SF-4 | Multi-mechanic drag_drop → trace_path, 5 labels + 10 total | `all_zones_labeled` trigger checks 5 placed vs 10 total | Drag-drop phase never triggers transition to trace_path. Player places all 5 labels but nothing happens. | S-18 + S-6 |
| SF-5 | Game with circular zone dependencies (A parent of B, B parent of A) | `updateVisibleZones` processes A first (has parent B, not completed → hidden), then B (has parent A, not completed → hidden) | No zones visible. Blank diagram. | No cycle detection in hierarchy. |
| SF-6 | Score overwrite on mode transition | drag_drop scores 50, then trace_path starts. First waypoint click sets score to 10. | Score drops from 50 to 10 when starting trace_path phase. | S-33 + S-34 |
| SF-7 | Task without matching zone_ids | `_sceneToBlueprint` filters `scene.zones.filter(z => task.zone_ids.includes(z.id))` → empty array | No zones rendered. Blank diagram with no drop targets. | No validation that task zone_ids exist in scene zones. |
| SF-8 | Time-based mode transition configured | `checkModeTransition` hits `time_elapsed` case, does nothing | Mode transition never fires. Game stays on first mechanic indefinitely. | S-19 |
| SF-9 | Mode transition to undefined mode string | `transitionToMode('nonexistent')` sets `interactionMode: 'nonexistent'` | `renderInteractionContent` switch hits `default` case → renders drag_drop | No validation that target mode exists in switch statement. |

---

## 12. Accessibility Gaps

| # | Component | Severity | Issue | Impact |
|---|-----------|----------|-------|--------|
| A-1 | DropZone | MEDIUM | Zones have `tabIndex` and `aria-label` but no visible focus ring styling | Keyboard-navigating users can't see which zone is focused. |
| A-2 | DropZone | MEDIUM | Zone ID used in HTML `id` attribute without sanitization | Zone IDs with special characters (e.g., `zone:1/2`) produce invalid HTML IDs, breaking `aria-describedby` references. |
| A-3 | DiagramCanvas | MEDIUM | Correct zone color is green only — no pattern/icon for colorblind users | The checkmark (✓) only appears on the label inside the zone. Zone border color is the only zone-level indicator. |
| A-4 | index.tsx | LOW | Screen reader announcements sparse — zone completion not always announced | `announceGameAction` called on correct placement but not on mode transitions, task completions, or scene changes. |
| A-5 | SequenceBuilder et al. | MEDIUM | 5 interaction components (sequencing, sorting, memory, branching, compare) have unknown accessibility status | These components are in `interactions/` directory but not audited for keyboard nav, ARIA labels, or screen reader support. |
| A-6 | ResultsPanel | LOW | Emoji characters have no alt text | Screen readers may read "party popper" or may skip. |

---

## 13. Performance Issues

| # | Location | Severity | Issue | Impact |
|---|----------|----------|-------|--------|
| P-1 | index.tsx:111-204 | HIGH | `normalizeBlueprint` is O(n^2) and runs in `useMemo` | With 100 zones, creates 10,000 comparisons. Runs on every blueprint reference change. |
| P-2 | useLabelDiagramState.ts:666-742 | MEDIUM | `updateVisibleZones` rebuilds entire visible/blocked sets from scratch | Called after every `placeLabel`. With 100 zones and 50 constraints, does 5,000 set operations per placement. |
| P-3 | index.tsx:578-589 | LOW | `useSensor` creates new sensor config objects on every render | `MouseSensor` and `TouchSensor` configs recreated each render. Should be outside component or in `useMemo`. |
| P-4 | GameSequenceRenderer | LOW | `getNextScene()` recalculated on every render without memoization | O(scenes) per render for scene navigation logic. |
| P-5 | — | LOW | No virtualization for large zone counts | If a game has 100+ zones, all 100+ DropZone components render simultaneously. |

---

## 14. Missing Features

| # | Feature | Current State | Impact |
|---|---------|--------------|--------|
| MF-1 | Undo/redo for non-drag_drop modes | Only `PlaceLabelCommand` exists | Users can undo drag_drop actions but not sequencing, path drawing, etc. |
| MF-2 | Time bonus scoring | `scoringStrategy.time_bonus_enabled` defined but never implemented | Feature appears in blueprint schema but has no runtime effect. |
| MF-3 | Hint system for non-drag_drop | Hints only shown in drag_drop mode (zone.hint + blueprint.hints) | Other modes have no hint support. |
| MF-4 | Progress auto-save between tasks/scenes | 30s interval auto-save only. No save on task/scene completion. | Multi-task games lose progress on crash between save intervals. |
| MF-5 | Network retry for images | Single fetch, no retry logic | Slow/flaky network → blank diagram, no recovery. |
| MF-6 | Blueprint input validation | Blueprint not validated against schema on load | Bad data from backend passes through silently until a runtime error occurs. |

---

## 15. Consolidated Bug Count

### By Severity

| Severity | Count | Examples |
|----------|-------|---------|
| CRITICAL | 7 | N-3 (phantom zones), S-2 (mode init), S-10 (removeLabel), S-24 (5 modes no init), IC-1 (sequencing), IC-2 (sorting), S-6 (completion check) |
| HIGH | 31 | T-1 (hierarchy is mode), T-5 (templateType), N-1 (queue mapping), S-7 (hasRemainingModes), S-18 (all_zones_labeled), S-19 (time_elapsed), S-20 (setTimeout leak), S-23 (mutable history), S-25 (score 0), S-27 (TaskResult max_score), IC-3..IC-6 (5 mechanics no store), all data flow mismatches |
| MEDIUM | 44 | T-3, T-6, T-8, N-7, N-8, S-3..S-5, S-8, S-12, S-15, S-21, S-26, S-28..S-35, DC-1, DZ-1..DZ-4, DM-2, HM-2, IC-8, IC-9, MS-2..MS-6, GS-1, GS-2, CH-1, CH-2, PS-1, PS-2, EL-1, EL-2, A-1..A-3, A-5, RP-3, P-2 |
| LOW | 27 | S-1, S-9, S-13, S-16, S-17, S-22, S-30, S-36, N-5, N-6, T-7, DC-2, DC-3, DZ-3, DZ-5, DL-1, DL-2, GC-1, GC-2, RP-1, RP-2, A-4, A-6, PS-3, PS-4, EL-3, P-3..P-5 |

### By Component/File

| File | CRITICAL | HIGH | MEDIUM | LOW | Total |
|------|----------|------|--------|-----|-------|
| types.ts | 0 | 3 | 4 | 1 | 8 |
| index.tsx (normalization) | 1 | 2 | 2 | 2 | 7 |
| index.tsx (rendering) | 0 | 1 | 3 | 1 | 5 |
| useLabelDiagramState.ts | 4 | 11 | 14 | 7 | 36 |
| DiagramCanvas.tsx | 0 | 0 | 1 | 2 | 3 |
| DropZone.tsx | 0 | 0 | 3 | 2 | 5 |
| DraggableLabel.tsx | 0 | 0 | 0 | 2 | 2 |
| GameControls.tsx | 0 | 0 | 0 | 2 | 2 |
| ResultsPanel.tsx | 0 | 0 | 1 | 2 | 3 |
| Interaction components | 2 | 6 | 3 | 1 | 12 |
| Hooks (3 files) | 0 | 0 | 5 | 3 | 8 |
| Multi-scene system | 0 | 1 | 4 | 1 | 6 |
| Mode transition system | 0 | 4 | 1 | 1 | 6 |
| Data flow mismatches | 0 | 4 | 2 | 1 | 7 |
| Accessibility | 0 | 0 | 4 | 2 | 6 |
| Performance | 0 | 1 | 1 | 3 | 5 |
| **TOTAL** | **7** | **33** | **48** | **33** | **121** |

### By Category

| Category | Count | Key Issues |
|----------|-------|------------|
| State management logic | 36 | removeLabel stale state, score overwrites, completion detection, mode transition |
| Store integration | 12 | 5 mechanics with zero store wiring, advanceToNextTask uses placedLabels only |
| Type safety | 15 | Untyped configs, fragile runtime checks, missing fields at type boundaries |
| Data flow | 7 | Coordinate format, scoring/feedback lost, templateType |
| Normalization | 7 | Phantom zones, queue mapping, migration edge cases |
| UI/UX | 10 | Fallback to drag_drop, missing progress indicators, no exit button |
| Accessibility | 6 | Focus rings, color-only feedback, unsanitized IDs |
| Performance | 5 | O(n^2) normalize, full set rebuild, no memoization |
| Missing features | 6 | Undo for non-drag_drop, time bonus, hints, auto-save, retry, validation |
| Multi-scene | 6 | Hardcoded templateType, fragile scene→blueprint copy, no save between transitions |
| Mode transition | 6 | Unimplemented triggers, setTimeout leak, wrong label count |
| Silent failures | 9 | Documented in Section 11 |

---

## Priority Fix Recommendations

### Must Fix (Blocking — Game Broken)

1. **S-10 + S-11:** Fix `removeLabel` to update `completedZoneIds` and call `updateVisibleZones()`
2. **S-2 + S-24:** Initialize ALL mechanic-specific states on game init, not just starting mode. Also handle transition to 5 non-initialized modes.
3. **IC-1 through IC-6:** Wire sequencing, sorting, memory, branching, compare to centralized store. Add generic completion mechanism beyond `placedLabels`.
4. **N-3:** Replace phantom zone fallback with validation error + user-friendly message
5. **S-6 + S-18:** Per-mode label/zone counting for completion detection and transition triggers

### Should Fix (Major Impact)

6. **S-33 + S-34 + S-35:** Fix score accumulation — `updatePathProgress` et al. should ADD to score, not overwrite
7. **S-23:** Use immutable history update in `transitionToMode`
8. **S-20:** Clean up `setTimeout` in `checkModeTransition` on unmount
9. **S-27:** Fix `advanceToNextTask` TaskResult max_score calculation
10. **T-1:** Reclassify `hierarchical` from InteractionMode to cross-cutting config
11. **T-5 + MS-1:** Update `templateType` to `'INTERACTIVE_DIAGRAM'` everywhere
12. **S-19:** Implement `time_elapsed` transition trigger or remove from type definitions

### Nice to Have (Polish)

13. Fix accessibility gaps (A-1 through A-6)
14. Add blueprint input validation (MF-6)
15. Performance optimizations (P-1 through P-5)
16. Complete undo/redo for all modes (MF-1)
17. Add hint system for non-drag_drop modes (MF-3)
