# Audit 30: Frontend Game Rendering Layer — Deep Analysis

**Date:** 2026-02-14
**Scope:** Multi-scene, multi-mechanic game rendering without exceptions
**Status:** RESEARCH ONLY — no code changes

---

## Table of Contents

1. [Data Flow Overview](#1-data-flow-overview)
2. [File-by-File Analysis](#2-file-by-file-analysis)
3. [Per-Mechanic Crash Analysis](#3-per-mechanic-crash-analysis)
4. [Multi-Scene Handling](#4-multi-scene-handling)
5. [Type Mismatches: Backend vs Frontend](#5-type-mismatches-backend-vs-frontend)
6. [Missing Config Guards](#6-missing-config-guards)
7. [Cross-Cutting Issues](#7-cross-cutting-issues)
8. [Proposed Fixes](#8-proposed-fixes)

---

## 1. Data Flow Overview

```
API (/api/status/:id)
  |
  v
game/[id]/page.tsx
  |-- polls /api/status/:id until completed
  |-- reads status.blueprint (GameBlueprint type with [key: string]: unknown)
  |-- if templateType === 'INTERACTIVE_DIAGRAM' || 'LABEL_DIAGRAM':
  |     |-- calls parseBlueprint(blueprint)
  |     |-- passes validatedBp to <InteractiveDiagramGame>
  |
  v
InteractiveDiagramGame (index.tsx)
  |-- detects multi-scene via is_multi_scene flag
  |-- if multi-scene: migrateMultiSceneBlueprint() -> normalizeBlueprint (stub for first scene)
  |-- if single-scene: normalizeBlueprint()
  |-- initializeGame(normalizedBlueprint) or initializeMultiSceneGame(gameSequence)
  |-- Zustand store (useInteractiveDiagramState) manages ALL game state
  |-- builds MechanicRouterProps via buildMechanicRouterProps()
  |-- for multi-scene: renderScene() converts GameScene -> InteractiveDiagramBlueprint
  |     then passes to <MechanicRouter>
  |-- for single-scene: passes to <MechanicRouter> directly
  |
  v
MechanicRouter.tsx
  |-- looks up MECHANIC_REGISTRY[mode]
  |-- calls entry.validateConfig(blueprint) for config check
  |-- calls entry.extractProps(ctx) to build component props
  |-- wraps in DndContext if needsDndContext is true
  |-- renders entry.component with extracted props
  |
  v
Interaction Components (per mechanic)
  |-- receive props from extractProps
  |-- emit MechanicAction via onAction callback
  |-- onAction routed through useMechanicDispatch hook
  |-- dispatch updates Zustand store
  |-- store updates drive re-renders and completion detection
```

### Key Observations

1. There are TWO blueprint parsing paths: `parseBlueprint()` in `game/[id]/page.tsx` (Zod validation) AND `normalizeBlueprint()` in `index.tsx` (zone/label ID deduplication). Both can silently fall back to raw data on failure.

2. The Zustand store is a singleton (`create<InteractiveDiagramState>`) shared across all scenes. When advancing scenes, `initializeGame()` is called again which resets most store fields. This means cross-scene state (like `multiSceneState`) must be set BEFORE calling `initializeGame()`, since `initializeGame` does NOT clear `multiSceneState` (it only resets game-local fields).

3. The `MECHANIC_REGISTRY` is the central routing table. It has entries for 10 of 11 InteractionMode values (`timed_challenge` is handled specially by MechanicRouter wrapping another mechanic). Any mode not in the registry gets a `MechanicConfigError` component.

---

## 2. File-by-File Analysis

### 2.1 `game/[id]/page.tsx` — Game Page

**What it does:** Polls the backend for game status, then renders the appropriate game template component based on `templateType`.

**Data shapes expected:**
- `status.blueprint` is typed as `GameBlueprint` with `[key: string]: unknown` catch-all
- For INTERACTIVE_DIAGRAM: passes raw blueprint through `parseBlueprint()` then to `<InteractiveDiagramGame>`

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| GP-1 | L329-345 | `parseBlueprint(blueprint)` is called but errors are only logged as warnings, never surfaced to user or used to prevent rendering. A blueprint with fatal Zod errors still gets passed to `InteractiveDiagramGame`. | HIGH |
| GP-2 | L331 | `parseBlueprint` returns `{ blueprint, errors }` but the code destructures `errors` as `bpErrors`. If `parseBlueprint` returns a multi-scene result, `blueprint` will be typed as `MultiSceneInteractiveDiagramBlueprint` but the page just passes it through — the `InteractiveDiagramGame` component must handle both types. This works because the component accepts a union type. | LOW |
| GP-3 | L337 | `<InteractiveDiagramGame blueprint={validatedBp}>` — `validatedBp` comes from a union of `ParseResult | MultiSceneParseResult`. The `blueprint` field's type is `InteractiveDiagramBlueprint | MultiSceneInteractiveDiagramBlueprint`. The component prop is typed identically, so this is OK. | NONE |
| GP-4 | L93-107 | `GameBlueprint` interface has loose typing with `[key: string]: unknown`. This means TypeScript cannot catch shape mismatches from the API. All mechanic-specific fields (sequenceConfig, sortingConfig, etc.) are invisible to this type. | MEDIUM |

**Multi-scene specific:** No multi-scene logic in this file. The page blindly passes whatever `parseBlueprint` returns. This is correct — all multi-scene logic is in `InteractiveDiagramGame`.

---

### 2.2 `index.tsx` — InteractiveDiagramGame (Main Component)

**What it does:** Main game orchestrator. Detects multi-scene vs single-scene, normalizes blueprint, initializes store, builds mechanic router props, handles scene transitions.

**Data shapes expected:**
- `blueprint` prop: `InteractiveDiagramBlueprint | MultiSceneInteractiveDiagramBlueprint`
- Multi-scene detection: `is_multi_scene === true` flag
- Game sequence: `MultiSceneInteractiveDiagramBlueprint.game_sequence.scenes: GameScene[]`

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| IX-1 | L502 | `const firstScene = multiBlueprint.game_sequence?.scenes?.[0]` — safe optional chaining. BUT if `game_sequence` is undefined, `firstScene` is undefined, and lines 507-510 will produce `zones: []`, `labels: []`, `assetUrl: undefined`, `interactionMode: undefined as InteractionMode`. The `interactionMode` will be `undefined`, which is NOT a valid `InteractionMode` string. When passed to `MECHANIC_REGISTRY[undefined]`, the lookup returns `undefined`, and `MechanicRouter` renders `<MechanicConfigError>`. | MEDIUM |
| IX-2 | L510 | `interactionMode: (firstScene?.mechanics?.[0]?.type || firstScene?.interaction_mode) as InteractionMode` — if the scene has no mechanics array AND no `interaction_mode`, this casts `undefined` to `InteractionMode`. Type safety hole. | HIGH |
| IX-3 | L526 | `multiBlueprint.game_sequence.scenes.reduce(...)` — if `game_sequence.scenes` is undefined, this throws `Cannot read properties of undefined (reading 'reduce')`. The `game_sequence` was validated by Zod earlier, but if Zod fell through with a best-effort cast, `scenes` could be missing. | HIGH |
| IX-4 | L863-868 | In `renderScene()`, `activeZones = scene.zones` and `activeLabels = scene.labels` — if a scene has no zones or labels (which is valid for mechanics like branching_scenario or memory_match that don't use zones/labels), these will be empty arrays. This is fine for the mechanic, but `normalizeBlueprint` in the single-scene path (not used here) would create phantom data. | LOW |
| IX-5 | L871-873 | Mode derivation: `task?.mechanic_type || scene.mechanics?.[0]?.type || scene.interaction_mode` — triple fallback is good. But if ALL three are undefined, `startingMode` is `undefined as InteractionMode`, same problem as IX-2. | HIGH |
| IX-6 | L886-922 | `sceneBlueprint` construction in `renderScene()` manually assembles an `InteractiveDiagramBlueprint` from scene data. This is DUPLICATED logic — the same conversion exists in `engine/sceneManager.ts:sceneToBlueprint()`. The two implementations can drift. Specifically, `renderScene()` adds `...mechanicConfigs` via registry loop (L877-884), while `sceneToBlueprint()` uses explicit field listing. If a new mechanic config is added to the registry but not to `sceneToBlueprint()`, multi-scene games that use the engine path (e.g., `advanceToNextTask` at L1288) will lose config, while games using `renderScene()` will work. | HIGH |
| IX-7 | L891 | `scene.diagram.assetPrompt` — `assetPrompt` is optional in `GameScene.diagram` type. Falls back to `scene.title` which is always present. Safe. | NONE |
| IX-8 | L1004-1006 | `SceneIndicator` receives `completedScenes` as `completedSceneIds.map((_, i) => i + 1)`. This maps the COMPLETED scene IDs to sequential numbers `[1, 2, 3...]` regardless of which scenes actually completed. If scenes complete out of order (e.g., in branching progression), the indicator shows wrong scenes as completed. | MEDIUM |
| IX-9 | L540 | `useEffect` dependency array includes `initializeGame` and `initializeMultiSceneGame`, which are Zustand store actions (stable references). But it also includes `normalizedBlueprint` which is a new object on every re-render because `useMemo` returns a new reference when `isMultiScene` changes. Risk of re-initialization loops if `blueprint` prop updates. | LOW |
| IX-10 | L545 | Multi-scene task/scene advancement: `isComplete && multiSceneState && gameSequence && !multiModeState?.pendingTransition` — the `isComplete` flag is shared between single-mechanic completion and overall game completion. In a multi-mode game where one mechanic completes but there are remaining modes, `isComplete` should be false (handled by `hasRemainingModes`), but if the transition check fails (e.g., no matching transition), `isComplete` stays `true` and this effect fires, advancing the task prematurely. | HIGH |

---

### 2.3 `types.ts` — TypeScript Types

**What it does:** Defines all shared TypeScript interfaces for the game rendering layer.

**Key Observations:**

| # | Issue | Severity |
|---|-------|----------|
| TY-1 | `InteractiveDiagramBlueprint.diagram.zones` is typed as `Zone[]` (required array). Backend can send `undefined` or `null`. The `normalizeBlueprint` function guards this with `Array.isArray(diagram.zones) ? ... : []`, but code that skips normalization (multi-scene path) relies on `firstScene?.zones` which is also `Zone[]` in the type but could be undefined in practice. | MEDIUM |
| TY-2 | `GameScene.tasks` is typed as `SceneTask[]` (required array). But the type does NOT have a `?` suffix, meaning TypeScript assumes it always exists. However, backend may not populate it. The `migrateMultiSceneBlueprint` function checks `scene.tasks && scene.tasks.length > 0`, so it handles the case. Other code uses `scene.tasks?.[taskIdx]` with optional chaining. The type should be `tasks?: SceneTask[]` for accuracy. | LOW |
| TY-3 | `SceneTask.mechanic_type` is typed as `InteractionMode` but the backend sends this as a string. If the backend sends a typo or an unknown mechanic type, TypeScript won't catch it at runtime. | LOW |
| TY-4 | `SortingItem.correctCategoryId` (singular) vs `SortingItem.correct_category_ids` (plural, array) — The `submitSorting` in the store checks `sortingProgress.itemCategories[item.id] === item.correctCategoryId` (singular). The plural form `correct_category_ids` is never read by any store action. If backend sends ONLY `correct_category_ids` and not `correctCategoryId`, sorting always scores 0. | HIGH |
| TY-5 | `MultiSceneInteractiveDiagramBlueprint` does NOT include per-mechanic config fields (`sequenceConfig`, `sortingConfig`, etc.) at the root level. These only exist on `GameScene`. This is correct for multi-scene games where config is per-scene. | NONE |

---

### 2.4 `utils/extractTaskConfig.ts` — Config Extraction

**What it does:** Provides `extractMechanicConfig()` to resolve per-mechanic config from blueprint using registry lookup and mechanics array fallback.

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| EC-1 | L22-26 | `blueprint[configKey]` — accesses blueprint with a dynamic key from the registry's `configKey`. If `configKey` is set but the blueprint doesn't have that field (e.g., `sequenceConfig` is undefined), this returns undefined, which is handled by the `if (rootConfig)` check. Safe. | NONE |
| EC-2 | L29-35 | `blueprint.mechanics?.find(...)` — handles both string and object mechanics. The type `Mechanic` is always an object with `type` property, but this checks for strings too (legacy compat). However, `Mechanic.config` is `Record<string, unknown> | undefined`, so `mechanic.config` could be undefined. The `if (mechanic && typeof mechanic === 'object' && 'config' in mechanic)` guard is safe. | NONE |

**Key observation:** This utility is NOT used by `MechanicRouter` or `index.tsx`. The router uses `MECHANIC_REGISTRY[mode].extractProps(ctx)` directly, which accesses `ctx.blueprint.sequenceConfig` etc. inline. `extractTaskConfig` appears to be dead code for the main rendering path.

---

### 2.5 `MechanicRouter.tsx` — Mechanic Routing

**What it does:** Registry-driven lookup of mechanic components. Validates config, extracts props, wraps in DndContext if needed.

**Data shapes expected:**
- `MechanicRouterProps.mode`: `InteractionMode` string
- `MechanicRouterProps.blueprint`: current scene/task blueprint
- `MechanicRouterProps.progress`: `MechanicProgressMap` with nullable progress per mechanic

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| MR-1 | L54-68 | `timed_challenge` handling: accesses `blueprint.timedChallengeWrappedMode`. If undefined, renders `MechanicConfigError`. Then recursively renders `<MechanicRouter>` with the wrapped mode. If the wrapped mode is ALSO `timed_challenge`, this creates infinite recursion. No guard against recursive wrapping. | LOW (unlikely) |
| MR-2 | L71-73 | `MECHANIC_REGISTRY[mode]` — if mode is not in registry (e.g., an unknown mode string from backend), returns undefined, renders `MechanicConfigError`. This is correct fallback behavior. | NONE |
| MR-3 | L77-82 | `entry.validateConfig(blueprint)` — if `validateConfig` returns a string (error), renders `MechanicConfigError`. But the error message is NOT passed to the component — the user sees a generic "unsupported mechanic" message with no detail about WHAT config is missing. | MEDIUM |
| MR-4 | L94-96 | `entry.extractProps(ctx)` can return props that reference undefined values. For example, `sequencing.extractProps` accesses `bp.sequenceConfig.items` — if `bp.sequenceConfig` is undefined (and `validateConfig` returned non-null but was not a fatal error), this throws `TypeError: Cannot read properties of undefined (reading 'items')`. However, `validateConfig` for sequencing checks `!bp.sequenceConfig?.items?.length` and returns error if missing, so `extractProps` should never be called without config. The gate is: validateConfig returns error -> render MechanicConfigError. If validateConfig returns null (valid), extractProps runs. The issue is: `validateConfig` RETURNS the error but `MechanicRouter` only checks if it's truthy. If validateConfig returns `''` (empty string = falsy), the config error is silently ignored and extractProps runs with missing config. | LOW (defensive) |
| MR-5 | L97 | `useMemo` dependency includes `props` which is the entire MechanicRouterProps object. Since `buildMechanicRouterProps` in index.tsx creates a new object every render (even if values haven't changed), this `useMemo` will re-execute every render. Performance issue but not a crash. | LOW |
| MR-6 | L100-111 | DndContext wrapping: `registryNeedsDndContext(mode) && dnd`. If `dnd` is null for a mode that needs DnD (e.g., `drag_drop` or `hierarchical`), the DndContext is skipped. The component still renders but drag operations fail silently. No error message. | MEDIUM |

---

### 2.6 `interactions/index.ts` — Exports

**What it does:** Re-exports all interaction components.

**Key Observations:**

| # | Issue | Severity |
|---|-------|----------|
| EX-1 | Exports `HotspotManager` (legacy) and `PathDrawer` (legacy), but `MechanicRouter` uses `EnhancedHotspotManager` and `EnhancedPathDrawer` imported directly in `mechanicRegistry.ts`. The legacy exports in `index.ts` are only used if someone imports from `./interactions` directly. Not a crash risk but potential confusion. | NONE |
| EX-2 | `GameSequenceRenderer` is exported here and imported in `index.tsx` from `./interactions`. Correct. | NONE |

---

### 2.7 `GameSequenceRenderer.tsx` — Multi-Scene Sequence

**What it does:** Manages multi-scene game progression. Shows scene progress bar, handles scene transitions, renders current scene via `renderScene` callback.

**Data shapes expected:**
- `sequence: GameSequence` with `scenes: GameScene[]`, `total_scenes: number`, etc.
- `renderScene: (scene: GameScene) => React.ReactNode` callback

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| GS-1 | L194-220 | `useEffect` with `sceneIsComplete` dependency calls `completeCurrentScene()` which updates store state, then immediately reads `useInteractiveDiagramState.getState()` (L201). This works because Zustand `set` is synchronous. However, this useEffect also has `multiSceneState` in its deps. When `completeScene` updates `multiSceneState`, the effect re-fires. The guard `if (multiSceneState.isSequenceComplete) return` (L195) prevents infinite loops, but between the `completeCurrentScene()` call and the store update, there's a window where `multiSceneState` is stale (from the previous render). The fresh state is read via `getState()` which is correct. | LOW |
| GS-2 | L201 | `const freshState = useInteractiveDiagramState.getState().multiSceneState` — calling `getState()` inside a React component effect is an anti-pattern but necessary here for synchronous state reads after `completeCurrentScene()`. This is fragile — if `completeCurrentScene` becomes async, this breaks. | MEDIUM |
| GS-3 | L179 | `const currentScene = sequence.scenes[currentSceneIndex]` — if `currentSceneIndex` is out of bounds (e.g., `total_scenes` was wrong), `currentScene` is undefined. Line 376 guards with `{currentScene && !isTransitioning && (...)}`, so rendering is safe. But `SceneProgressBar` at L237 still receives `currentScene: currentSceneIndex + 1` regardless. | LOW |
| GS-4 | L231 | `const progressPercent = (completedScenes.size / sequence.total_scenes) * 100` — if `total_scenes` is 0, this produces `NaN`. The progress bar would render incorrectly. | LOW |
| GS-5 | L267-278 | Hierarchy depth calculation for zoom_in: uses a while loop that can infinite-loop if scene prerequisite chains are circular (scene A requires B, B requires A). There's a `if (!current.prerequisite_scene) break` guard inside the while, but the outer `while (current.prerequisite_scene)` condition would catch undefined. However, the inner `current = sequence.scenes.find(...)` could return the same scene if prerequisites form a cycle, causing an infinite loop. | MEDIUM |
| GS-6 | L194-220 | This `useEffect` fires on `sceneIsComplete` changes. But `sceneIsComplete` is the store's `isComplete` field, which is also set by mechanic completion in single-mode games. In a multi-mode game where one mechanic completes (setting `isComplete = true` briefly before `checkModeTransition` sets it back to false), this effect could fire prematurely and call `completeCurrentScene()`. This would record a premature scene result. The guard is `!multiSceneState.isSequenceComplete`, but that doesn't prevent premature scene completion within a multi-mode scene. | HIGH |
| GS-7 | L194 | `sceneIsComplete` comes from `useInteractiveDiagramState` which is destructured at L164. But this is the GLOBAL `isComplete` flag. In a multi-scene game with multi-mode mechanics, a single mechanic's completion should NOT trigger scene completion. The store already handles this in `placeLabel` where `isComplete = allLabelsPlaced && !hasRemainingModes(state.multiModeState)`. But for non-drag-drop mechanics (sequencing, sorting, etc.), the `set({ isComplete: true })` at the end of `submitSequence`, `submitSorting`, etc. does NOT check `hasRemainingModes`. It only checks `modeTransitions.length === 0`. If a multi-mode scene has sequencing + drag_drop but NO explicit mode transitions (relying on implicit sequencing), `submitSequence` sets `isComplete = true`, and `GameSequenceRenderer` advances the scene before drag_drop runs. | CRITICAL |

---

### 2.8 `mechanicRegistry.ts` — MECHANIC_REGISTRY

**What it does:** Central registry mapping `InteractionMode` -> component, props extraction, validation, scoring, completion detection.

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| REG-1 | L122 | `MECHANIC_REGISTRY` is `Partial<Record<InteractionMode, MechanicRegistryEntry>>`. The `Partial` means any mode lookup could return `undefined`. The `MechanicRouter` checks for this. But code that accesses `MECHANIC_REGISTRY[mode]!` without null check would crash. | MEDIUM |
| REG-2 | L246-284 | `sequencing.extractProps` — L250: `if (sequenceConfig && sequenceConfig.items.length > 0)`. If `sequenceConfig.items` is undefined (backend sent config without items array), `.length` throws. Should be `sequenceConfig?.items?.length`. | HIGH |
| REG-3 | L281 | Fallback: `console.warn('Sequencing mode active but no sequenceConfig...')` then uses `bp.labels` as items and `bp.labels.map(l => l.id)` as correctOrder. If `bp.labels` is empty (legitimate for sequencing games that don't use labels), returns empty `items: []` and `correctOrder: []`. The `EnhancedSequenceBuilder` component receives empty arrays and renders nothing, with no error message to the user. | MEDIUM |
| REG-4 | L325 | `sorting_categories.extractProps`: `config?.items ?? []` and `config?.categories ?? []`. Safe fallback to empty arrays. But `EnhancedSortingCategories` with no items renders an empty sorting container with no indication of the problem. | LOW |
| REG-5 | L366-370 | `memory_match.extractProps`: passes `config: ctx.blueprint.memoryMatchConfig ?? { pairs: [] }`. The `EnhancedMemoryMatch` component expects `config.pairs` to be a non-empty array. With `pairs: []`, it renders an empty grid. Safe but useless. | LOW |
| REG-6 | L399-414 | `branching_scenario.extractProps`: `config?.nodes ?? []` and `config?.startNodeId ?? ''`. If `startNodeId` is `''`, the BranchingScenario component does `nodes.find(n => n.id === startNodeId)` which finds nothing, and `currentNode` is undefined. The component renders nothing (no crash guard documented but component likely handles it). | MEDIUM |
| REG-7 | L449-488 | `compare_contrast.extractProps`: Legacy stub fallback (L464-488) creates two identical diagrams from zones. This produces a compare game where everything is "similar" — not useful but doesn't crash. | LOW |
| REG-8 | L519-527 | `description_matching.extractProps`: `descriptions: ctx.blueprint.descriptionMatchingConfig?.descriptions`. If this is undefined, the `DescriptionMatcher` component falls back to using zone descriptions. But `mode: ctx.progress.descriptionMatching?.mode || 'click_zone'` — if `descriptionMatchingState` hasn't been initialized yet, mode defaults to 'click_zone'. This is safe. | NONE |
| REG-9 | L527 | `showHints: ctx.dnd?.showHints ?? false` — `dnd` could be null for description_matching (needsDndContext is false). The `?` handles it. | NONE |

---

### 2.9 `hooks/useMechanicDispatch.ts` — Action Dispatch

**What it does:** Translates `MechanicAction` discriminated union into Zustand store calls.

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| MD-1 | L88-89 | `case 'identify': if (!identificationProgress) return null` — safe null guard. But the `evaluateIdentification` function accesses `blueprint.identificationPrompts[progress.currentPromptIndex]`. If `identificationPrompts` is undefined, `prompts` is `[]`, and `currentPrompt` is undefined. `isCorrect` becomes `undefined === zoneId` which is `false`. Safe but silently wrong. | LOW |
| MD-2 | L107 | `case 'visit_waypoint': if (!pathProgress) return null` — safe. | NONE |
| MD-3 | L115-131 | `case 'submit_path'`: L123 `blueprint.paths?.find(p => p.id === action.pathId)` — safe optional chaining. If `paths` is undefined, `path` is undefined, `correctOrder` is `[]`, and `isPathCorrect` is `false` (since `correctOrder.length === 0` means the first condition fails). | LOW |
| MD-4 | L142-148 | `case 'submit_sequence'`: L142 `submitSequence()` calls the store action which checks `if (!sequencingProgress || !blueprint?.sequenceConfig) return`. Then L143 `useInteractiveDiagramState.getState().sequencingProgress` reads the updated state. If `submitSequence()` returned early (no progress/config), `sp` is null, and `isSeqCorrect` is `false`. Safe. | NONE |
| MD-5 | L219-222 | `case 'place'`: `placeLabel(action.labelId, action.zoneId)` — returns boolean. If store's `blueprint` is null, `placeLabel` returns false. Safe. | NONE |

---

### 2.10 `engine/sceneManager.ts` — Scene-to-Blueprint Conversion

**What it does:** Pure function to convert `GameScene` -> `InteractiveDiagramBlueprint` with task filtering.

**Crash Points:**

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| SM-1 | L69-76 | `const task = (scene.tasks && scene.tasks.length > 0) ? scene.tasks[taskIndex] : {...}` — if `taskIndex` is out of bounds (e.g., `taskIndex = 2` but only 1 task), `scene.tasks[taskIndex]` is undefined. The code continues with `task = undefined`. Then L82 `if (task && task.zone_ids.length > 0)` — `task` is undefined, so filters don't apply, and ALL zones/labels are active. This is actually CORRECT fallback behavior — but only if the caller doesn't depend on task-specific filtering. | LOW |
| SM-2 | L91-92 | Mode derivation: same triple fallback as IX-5. If all three are undefined, `startingMode` is `undefined as InteractionMode`. | HIGH |
| SM-3 | L105-146 | Blueprint construction: Lists all mechanic config fields explicitly (e.g., L131-144). This is the DUPLICATE of `renderScene()` in index.tsx (IX-6). If a new config field is added to `InteractiveDiagramBlueprint` but not here, it's silently dropped. | HIGH |

---

## 3. Per-Mechanic Crash Analysis

For each of the 10 mechanic types (excluding `timed_challenge` which is a wrapper), here is what can go wrong:

### 3.1 `drag_drop`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| DD-1 | Works correctly. Most tested mechanic. | - | NONE |
| DD-2 | If `blueprint.labels` is empty, `validateConfig` returns error, MechanicConfigError rendered. | registry L140 | NONE |
| DD-3 | `EnhancedDragDropGame` accesses `blueprint.diagram.zones` which is always `[]` minimum after normalization. | component | NONE |

### 3.2 `click_to_identify`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| CI-1 | If `identificationPrompts` is undefined or empty, `validateConfig` returns error. | registry L176 | NONE |
| CI-2 | `EnhancedHotspotManager` accesses `progress?.currentPromptIndex`. If progress is null (not initialized), component renders but shows no prompt. | component L16 | MEDIUM |
| CI-3 | If `assetUrl` is undefined, the diagram canvas renders without an image. The hotspots are rendered as overlays on an empty canvas. Usable but confusing. | component | LOW |
| CI-4 | In multi-scene: config forwarding works via `sceneToBlueprint` L137 (`identificationPrompts: scene.identificationPrompts || scene.identification_prompts`). | sceneManager | NONE |

### 3.3 `trace_path`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| TP-1 | If `paths` is empty, `validateConfig` returns error. | registry L215 | NONE |
| TP-2 | `EnhancedPathDrawer` accesses `traceProgress?.pathProgressMap`. If null, path state defaults to unvisited. | component | NONE |
| TP-3 | `useMechanicDispatch` `submit_path` case validates against `blueprint.paths` — if paths are missing, scores as incorrect. Not a crash but wrong UX. | dispatch L122 | LOW |
| TP-4 | In multi-scene: `sceneToBlueprint` forwards `paths: scene.paths` (L130) but does NOT forward `tracePathConfig` explicitly. Wait — it does at L139: `tracePathConfig: scene.tracePathConfig || scene.trace_path_config`. Correct. | sceneManager | NONE |

### 3.4 `sequencing`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| SQ-1 | **CRASH**: `extractProps` L250: `sequenceConfig.items.length` — if backend sends `sequenceConfig` without `items` field (or `items: null`), this throws `TypeError`. | registry L250 | HIGH |
| SQ-2 | `validateConfig` checks `!bp.sequenceConfig?.items?.length` — returns error if items missing. This runs BEFORE extractProps in MechanicRouter. So SQ-1 should be guarded. BUT: if validateConfig returns `null` (valid) and `items` is present but empty `[]`, extractProps still runs and `items.length > 0` is false, falling through to label-based fallback. | registry L250,286 | LOW |
| SQ-3 | `initializeProgress` shuffles item IDs. If `sequenceConfig` is null (shouldn't happen after validateConfig), returns `{}`, and `sequencingProgress` stays null. `EnhancedSequenceBuilder` receives `storeProgress: null` and uses internal state. | registry L288 | LOW |
| SQ-4 | `submitSequence` in store checks `!sequencingProgress || !blueprint?.sequenceConfig` and returns early. Safe. | store L717 | NONE |
| SQ-5 | In multi-scene: `sceneToBlueprint` forwards `sequenceConfig: scene.sequenceConfig || scene.sequence_config` (L131). But `renderScene()` in index.tsx uses registry loop (L877-884) to discover `configKey: 'sequenceConfig'` and reads from scene. Potential for different values if scene has BOTH camelCase and snake_case. | index.tsx / sceneManager | LOW |

### 3.5 `sorting_categories`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| SO-1 | `validateConfig`: `!bp.sortingConfig?.items || !bp.sortingConfig?.categories` — returns error if either is missing. Safe. | registry L334 | NONE |
| SO-2 | `extractProps`: `config?.items ?? []`, `config?.categories ?? []`. Safe fallbacks. | registry L326-328 | NONE |
| SO-3 | **BUG**: `submitSorting` in store checks `item.correctCategoryId`. But type `SortingItem` has BOTH `correctCategoryId: string` (singular) AND `correct_category_ids?: string[]` (plural/snake_case). If backend sends ONLY `correct_category_ids`, `correctCategoryId` is undefined, and ALL items score as incorrect. | store L774 | HIGH |
| SO-4 | `EnhancedSortingCategories` expects `items: SortingItem[]` and `categories: SortingCategory[]`. If categories have no `color`, defaults are applied. | component | NONE |

### 3.6 `memory_match`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| MM-1 | `validateConfig`: `!bp.memoryMatchConfig?.pairs` — returns error if pairs missing. But does NOT check for empty pairs array. | registry L372 | LOW |
| MM-2 | `extractProps` passes `config: ctx.blueprint.memoryMatchConfig ?? { pairs: [] }`. If config exists but `pairs` is not an array, component could crash on `.map()`. | registry L368 | MEDIUM |
| MM-3 | `EnhancedMemoryMatch` creates card grid from `config.pairs`. If `pairs` is empty, grid is empty. If a pair has missing `front` or `back`, card content is undefined. Component does NOT guard against undefined pair fields. | component | MEDIUM |
| MM-4 | `recordMemoryMatch` in store: adds pairId to `matchedPairIds`. No guard against duplicate pairIds (matching same pair twice). | store L804 | LOW |

### 3.7 `branching_scenario`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| BR-1 | `validateConfig`: `!bp.branchingConfig?.nodes || !bp.branchingConfig?.startNodeId`. | registry L416 | NONE |
| BR-2 | **POTENTIAL CRASH**: `extractProps` passes `startNodeId: config?.startNodeId ?? ''`. If `startNodeId` is empty string, `BranchingScenario` does `nodes.find(n => n.id === '')` which returns undefined. Component would then have `currentNode = undefined` and accessing `currentNode.question` throws. | registry L406, component | HIGH |
| BR-3 | `recordBranchingChoice` in store: `nextNodeId || state.branchingProgress.currentNodeId`. If `nextNodeId` is `null` (end node), the current node stays the same. Then `if (nextNodeId === null)` sets `isComplete = true`. Correct. | store L860 | NONE |
| BR-4 | `isComplete` in registry: `currentNode?.isEndNode === true`. If branching state gets into a node that doesn't exist in `nodes` array, `currentNode` is undefined, returns false. Game is stuck — never completes. | registry L431 | MEDIUM |
| BR-5 | In multi-scene: branching games don't use zones/labels at all. `sceneToBlueprint` still creates `labels: activeLabels` and `zones: activeZones`. These are harmless empty arrays if the scene has no zones/labels. | sceneManager | NONE |

### 3.8 `compare_contrast`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| CC-1 | `extractProps`: checks `config && config.diagramA && config.diagramB`. If either diagram is missing, falls through to legacy stub. | registry L452 | LOW |
| CC-2 | **POTENTIAL CRASH**: `CompareContrast` component expects `diagramA.zones` and `diagramB.zones` as arrays. If backend sends compareConfig with diagrams that have no `zones` array, component crashes on `.map()`. | component | MEDIUM |
| CC-3 | `submitCompare` in store: iterates `blueprint.compareConfig.expectedCategories`. If `expectedCategories` is undefined/null, `Object.entries(undefined)` throws. Guard: `if (!compareProgress || !blueprint?.compareConfig) return`. But `compareConfig` could have `expectedCategories: undefined`. | store L919 | MEDIUM |
| CC-4 | In multi-scene: `sceneToBlueprint` forwards `compareConfig: scene.compareConfig || scene.compare_config` (L134). Correct. | sceneManager | NONE |

### 3.9 `description_matching`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| DM-1 | `extractProps`: passes zones, labels, descriptions from config. If `descriptionMatchingConfig` is undefined, `descriptions` is undefined. `DescriptionMatcher` falls back to zone `.description` field. | registry L519-527 | NONE |
| DM-2 | `DescriptionMatcher` uses `zones.filter(z => z.description)` to build description list. If no zones have descriptions, the game has nothing to match. Renders empty state. | component | LOW |
| DM-3 | `recordDescriptionMatch` in store: `zonesWithDescriptions.length` for completion check. If 0, `isComplete` is immediately true on first match. | store L685 | LOW |
| DM-4 | `evaluateDescriptionMatch` in correctnessEvaluator: `blueprint.labels.find(l => l.id === labelId)`. If `labelId` doesn't match any label (namespace mismatch between zones and labels), returns `isCorrect: false`. This is the old "handleDescriptionMatch compares zone.id === labelId" bug. | evaluator L49 | HIGH |

### 3.10 `hierarchical`

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| HI-1 | `extractProps`: passes `onLabelPlace: ctx.hierarchical?.onHierarchyLabelPlace`. If `hierarchical` is null, `onLabelPlace` is undefined. The `HierarchyController` component must handle undefined callback. | registry L557 | MEDIUM |
| HI-2 | `hierarchical.needsDndContext: true` — requires DndContext wrapper. If `dnd` is null (shouldn't happen for hierarchical), DndContext is skipped and drag operations fail. | router L100 | LOW |
| HI-3 | Completion relies on `HierarchyController` calling `completeInteraction` prop. If the component never calls it (bug in component), the game is stuck. | registry L575 | LOW |

---

## 4. Multi-Scene Handling

### 4.1 Scene Iteration

Multi-scene games follow this flow:

1. `InteractiveDiagramGame` detects `is_multi_scene === true`
2. `migrateMultiSceneBlueprint()` merges scenes without images into tasks of the previous scene
3. `initializeMultiSceneGame(sequence)` sets up `MultiSceneState` and calls `initializeGame(sceneToBlueprint(firstScene, 0))`
4. `GameSequenceRenderer` renders current scene via `renderScene()` callback
5. `renderScene()` converts `GameScene` to `InteractiveDiagramBlueprint` and passes to `MechanicRouter`
6. On scene completion, `getSceneAction()` determines next action (advance task, advance scene, complete game)

### 4.2 Task Advancement

**Critical finding: Two code paths exist for scene-to-blueprint conversion.**

Path A: `renderScene()` in index.tsx (L855-929) — used for the CURRENT scene render
Path B: `sceneToBlueprint()` in engine/sceneManager.ts — used by `advanceToNextTask()` at store L1288

These two paths have different config forwarding logic:
- Path A uses a registry-driven loop to discover config keys dynamically
- Path B uses an explicit field list

If they diverge, a mechanic might work in the first task but break in subsequent tasks (or vice versa).

### 4.3 Score Accumulation

**Issue SCORE-1:** Score accumulation across tasks/scenes has a subtle bug.

When `advanceToNextTask()` fires (store L1253-1301):
1. Records `taskResult` with current `score` and `maxScore`
2. Calls `initializeGame(bp)` for the next task, which RESETS `score` to 0
3. But `multiSceneState.taskResults` accumulates

When `completeCurrentScene()` fires (store L1203-1219):
1. Records `sceneResult` with current `score` — but this is the score from the LAST TASK only (since initializeGame reset it)
2. `completeScene()` reduces over all `sceneResults` to compute `totalScore`

**Result:** In a multi-task scene, only the LAST task's score is captured in the scene result. Previous tasks' scores are in `taskResults` but NOT added to the scene score. The `totalScore` in `multiSceneState` only reflects the last task of each scene.

**Issue SCORE-2:** `initializeGame` sets `maxScore` from the blueprint's scoring strategy or registry calculation. But for multi-scene games, `initializeMultiSceneGame` also sets `maxScore: sequence.total_max_score` (store L608). Then `initializeGame` for the first scene OVERWRITES `maxScore` with the scene's max score. The overall game maxScore is lost from the store. It's only preserved in `gameSequence.total_max_score` and referenced directly in `GameSequenceRenderer`.

### 4.4 Scene Transition Timing

**Issue TIMING-1:** There are TWO independent scene-completion handlers:

1. `GameSequenceRenderer` useEffect (L194-220): fires on `sceneIsComplete`, calls `completeCurrentScene()` then `advanceToNextScene()`
2. `InteractiveDiagramGame` useEffect (L544-569): fires on `isComplete`, calls `getSceneAction()` then `advanceToNextTask()` or `completeScene()`/`advanceToScene()`

Both react to `isComplete` changes. Both can fire for the same completion event. This creates a race condition where:
- Handler 1 calls `completeCurrentScene()` which calls `completeScene()` which updates `multiSceneState`
- Handler 2 also calls `completeScene()` and `advanceToScene()` independently

**Result:** Scene results may be duplicated in `sceneResults` array, and score may be double-counted.

**Mitigation:** Handler 2 (index.tsx L544) has a guard `if (isComplete && multiSceneState && gameSequence && !multiModeState?.pendingTransition)`, while Handler 1 (GameSequenceRenderer L195) has `if (!sceneIsComplete || !multiSceneState || multiSceneState.isSequenceComplete) return`. These guards are not mutually exclusive — both can pass simultaneously.

---

## 5. Type Mismatches: Backend vs Frontend

### 5.1 Snake_case vs CamelCase

The backend V3 pipeline generates blueprint data in **snake_case**. The frontend types use **camelCase**. Normalization happens in two places:

1. `parseBlueprint.ts` -> `normalizeSceneKeys()` from `caseNormalizer.ts` — transforms snake_case root keys for single-scene blueprints
2. `sceneToBlueprint()` in sceneManager.ts — explicitly maps both camelCase and snake_case: `scene.sequenceConfig || scene.sequence_config`

**Gap:** `renderScene()` in index.tsx uses a registry loop to find config keys (L877-884) and tries both camelCase and snake_case. But it accesses the scene as `Record<string, unknown>` which loses type safety.

### 5.2 Missing/Mismatched Fields

| Backend Field | Frontend Expects | Issue |
|--------------|------------------|-------|
| `scoring_data` (list of dicts) | `mechanic.scoring` (single dict per mechanic) | `blueprint_assembler_tools.py` converts list to dict keyed by mechanic_type. If the mechanic_type doesn't match, scoring is missing. |
| `feedback_data` (list of dicts) | `mechanic.feedback` (single dict per mechanic) | Same issue as scoring_data. |
| `correct_category_ids` (array) | `correctCategoryId` (string) | SortingItem: backend may send plural form, frontend store checks singular. |
| `sorting_config.items[].correct_category_id` | `SortingItem.correctCategoryId` | snake_case vs camelCase |
| `memory_match_config.pairs[].front_type` | `MemoryMatchPair.frontType` | snake_case vs camelCase in nested objects. `normalizeSceneKeys` may not recurse deep enough. |
| `branching_config.start_node_id` | `BranchingConfig.startNodeId` | snake_case vs camelCase |
| `compare_config.diagram_a` | `CompareConfig.diagramA` | snake_case vs camelCase |

### 5.3 Blueprint Double-Parsing

`game/[id]/page.tsx` calls `parseBlueprint(blueprint)` with Zod validation, then passes the result to `InteractiveDiagramGame`. Inside `InteractiveDiagramGame`, `parseBlueprint(blueprint)` is called AGAIN (L462-482) via the `useMemo`. This means every blueprint is parsed and validated TWICE. The second parse may produce different warnings/errors if the first parse transformed the data.

---

## 6. Missing Config Guards

### What happens when config is undefined for each mechanic:

| Mechanic | Config Field | validateConfig Check | What Happens if Undefined |
|----------|-------------|---------------------|---------------------------|
| sequencing | `sequenceConfig` | `!bp.sequenceConfig?.items?.length` -> error | MechanicConfigError shown. Game unplayable but no crash. |
| sorting_categories | `sortingConfig` | `!bp.sortingConfig?.items || !bp.sortingConfig?.categories` -> error | MechanicConfigError shown. |
| memory_match | `memoryMatchConfig` | `!bp.memoryMatchConfig?.pairs` -> error | MechanicConfigError shown. |
| branching_scenario | `branchingConfig` | `!bp.branchingConfig?.nodes || !bp.branchingConfig?.startNodeId` -> error | MechanicConfigError shown. |
| compare_contrast | `compareConfig` | **No validateConfig defined** | Legacy fallback creates two identical diagrams from zones. Playable but wrong. |
| click_to_identify | `identificationPrompts` (not a config, but prompts array) | `!bp.identificationPrompts?.length` -> error | MechanicConfigError shown. |
| trace_path | `paths` (not a config) | `!bp.paths?.length` -> error | MechanicConfigError shown. |
| drag_drop | `labels` (not a config) | `!bp.labels?.length` -> error | MechanicConfigError shown. |
| description_matching | `descriptionMatchingConfig` | **No validateConfig defined** | Falls back to zone descriptions. May show empty game if no descriptions exist. |
| hierarchical | `zoneGroups` | **No validateConfig defined** | HierarchyController renders with empty groups. |

**Key gap:** `compare_contrast`, `description_matching`, and `hierarchical` have NO `validateConfig` function. This means invalid/missing config reaches the component, which must handle it internally or crash.

---

## 7. Cross-Cutting Issues

### CC-1: Singleton Zustand Store

The `useInteractiveDiagramState` store is a SINGLETON. If two `InteractiveDiagramGame` components are mounted simultaneously (e.g., during Next.js navigation transitions), they share the same store. The second component's `initializeGame()` overwrites the first component's state. This is unlikely in normal use but possible with prefetching or concurrent features.

### CC-2: Store Reset on Scene Advance

When `advanceToScene()` calls `initializeGame()`, it resets:
- `availableLabels`, `placedLabels`, `score`, `isComplete`, `showHints`, `draggingLabelId`, `incorrectFeedback`
- All per-mechanic progress (via `initializeMechanicProgress`)
- `temporalConstraints`, `motionPaths`, `completedZoneIds`, `visibleZoneIds`, `blockedZoneIds`
- `multiModeState`, `modeTransitions`

It does NOT reset:
- `multiSceneState` (set separately before `initializeGame`)
- `gameSequence` (set separately)

This is correct, but the reset of `multiModeState` means multi-mode state from the previous scene is lost. If both scenes have multi-mode, each gets a fresh multi-mode state. Correct behavior.

### CC-3: Timing of Completion Detection

The completion flow for non-drag-drop mechanics is:
1. Component emits `MechanicAction` via `onAction`
2. `useMechanicDispatch` translates to store calls
3. Store action (e.g., `submitSequence`) updates progress and sets `isComplete = true`
4. React re-renders
5. `GameSequenceRenderer` useEffect detects `isComplete` change
6. Calls `completeCurrentScene()` and `advanceToNextScene()`

Between step 3 and step 6, the `checkModeTransition()` call may also fire (step 3.5), which could set `isComplete = false` and trigger a mode transition instead. The timing is:
- `submitSequence` sets `isComplete = true`
- Same synchronous call chain: `checkModeTransition()` evaluates transitions
- If a transition is found: sets `pendingTransition` and starts a setTimeout
- React re-renders with `isComplete = true` AND `pendingTransition` defined
- `InteractiveDiagramGame` useEffect L544: `!multiModeState?.pendingTransition` is FALSE, so it does NOT advance
- After timeout fires: `transitionToMode()` sets `isComplete = false`

This sequence is CORRECT as long as the useEffect guards hold. But there's a race between the timeout firing and React rendering. If React renders before the timeout fires, `isComplete = true` and `pendingTransition = undefined` is visible for one frame, potentially triggering premature scene advancement.

### CC-4: MechanicConfigError UX

When a mechanic's config validation fails, `MechanicRouter` renders `MechanicConfigError`. This component shows a generic error message with the mechanic name. The user cannot proceed — the game is stuck. There is no:
- Retry mechanism
- Fallback to a simpler mechanic (e.g., drag_drop)
- Skip-scene option
- Error detail for debugging

In a multi-scene game, if ONE scene's config is bad, the entire game sequence is stuck at that scene.

### CC-5: `renderScene` vs `sceneToBlueprint` Divergence

As documented in IX-6 and SM-3, there are two independent implementations of GameScene -> InteractiveDiagramBlueprint conversion. They must stay in sync. Current differences:

`renderScene()` in index.tsx:
- Uses registry loop for mechanic config keys (dynamic discovery)
- Spreads `...mechanicConfigs` into blueprint
- Manually sets `temporalConstraints`, `motionPaths`, `hints`, `scoringStrategy`, `identificationPrompts`

`sceneToBlueprint()` in sceneManager.ts:
- Explicitly lists each config field
- Handles temporal constraint filtering per-task
- Does NOT use registry for config discovery

If a new mechanic type is added with a new config key:
- `renderScene` will auto-discover it via registry configKey
- `sceneToBlueprint` will NOT include it unless manually added

This means the first render of a scene works (via renderScene), but task advancement (via sceneToBlueprint) loses the config.

---

## 8. Proposed Fixes

### Priority 1: CRITICAL (prevents game from being playable)

| Fix | File:Line | Description |
|-----|-----------|-------------|
| F30-1 | `mechanicRegistry.ts:250` | Guard `sequenceConfig.items.length` with optional chaining: `sequenceConfig?.items?.length ?? 0 > 0`. Prevents crash when items is undefined. |
| F30-2 | `GameSequenceRenderer.tsx:194-220` + `index.tsx:544-569` | **Eliminate dual completion handlers.** Remove the scene-completion useEffect from `GameSequenceRenderer` and consolidate all completion logic in `index.tsx`. `GameSequenceRenderer` should be purely presentational. |
| F30-3 | `useInteractiveDiagramState.ts:714-750` (submitSequence) + L767-801 (submitSorting) + L804-828 (recordMemoryMatch) + L841-874 (recordBranchingChoice) + L913-950 (submitCompare) | Before setting `isComplete = true`, check `hasRemainingModes(state.multiModeState)`. Currently only `placeLabel` (drag_drop) does this check. All other mechanics blindly set `isComplete = true` if no mode transitions exist, which prematurely completes multi-task scenes. |
| F30-4 | `useInteractiveDiagramState.ts:774` (submitSorting) | Support both `correctCategoryId` and `correct_category_ids`. Check `item.correctCategoryId || item.correct_category_ids?.[0]` for backward compatibility with backend field naming. |

### Priority 2: HIGH (can cause exceptions or wrong behavior for specific mechanics)

| Fix | File:Line | Description |
|-----|-----------|-------------|
| F30-5 | `index.tsx:510` | Default `interactionMode` to `'drag_drop'` instead of `undefined as InteractionMode` when no mechanics or interaction_mode are specified on a scene. |
| F30-6 | `index.tsx:871-873` + `sceneManager.ts:90-92` | Same as F30-5 but for `startingMode` in renderScene and sceneToBlueprint. |
| F30-7 | `sceneManager.ts:63-146` | Consolidate with `renderScene()` in index.tsx. Make `sceneToBlueprint` the single source of truth. Have `renderScene()` call `sceneToBlueprint()` instead of duplicating the conversion logic. |
| F30-8 | `mechanicRegistry.ts:406` | Guard `startNodeId` for branching_scenario: if empty string, either return MechanicConfigError or default to the first node's ID. |
| F30-9 | `correctnessEvaluator.ts:44-53` (evaluateDescriptionMatch) | `description_matching` correctness check compares `label.correctZoneId === zoneId`. But in description_matching, the user is matching descriptions to zones, not labels to zones. The label and zone may have different ID namespaces. Need to verify the `labelId` parameter semantics. |
| F30-10 | `index.tsx:526` | Guard `multiBlueprint.game_sequence.scenes` against undefined: `(multiBlueprint.game_sequence?.scenes ?? []).reduce(...)`. |

### Priority 3: MEDIUM (degraded UX but no crash)

| Fix | File:Line | Description |
|-----|-----------|-------------|
| F30-11 | `MechanicRouter.tsx:78-81` | Pass the validateConfig error message to `MechanicConfigError` so users/developers can see what's wrong. |
| F30-12 | `mechanicRegistry.ts:L445-513` (compare_contrast) | Add `validateConfig`: `!bp.compareConfig?.diagramA || !bp.compareConfig?.diagramB ? 'Missing diagrams for compare_contrast' : null`. |
| F30-13 | `mechanicRegistry.ts:L515-547` (description_matching) | Add `validateConfig`: check that at least some zones have descriptions or that `descriptionMatchingConfig.descriptions` is non-empty. |
| F30-14 | `GameSequenceRenderer.tsx:267-278` | Add cycle detection for zoom_in hierarchy depth calculation to prevent infinite loops. |
| F30-15 | `index.tsx:1004-1006` | Fix `SceneIndicator` `completedScenes` mapping to use actual completed scene indices, not sequential `[1, 2, 3...]`. |
| F30-16 | `useInteractiveDiagramState.ts:1253-1301` (advanceToNextTask) | Score accumulation: save `score` into `taskResult` BEFORE `initializeGame` resets it. Currently this works because `get().score` is read before the set, but the flow is fragile. |
| F30-17 | `MechanicRouter.tsx:100` | When `dnd` is null for a mode that needs DndContext, render a warning message instead of silently failing. |

### Priority 4: LOW (minor issues)

| Fix | File:Line | Description |
|-----|-----------|-------------|
| F30-18 | `game/[id]/page.tsx:329-345` | Remove double-parse: `InteractiveDiagramGame` already calls `parseBlueprint` internally. Either parse in the page OR in the component, not both. |
| F30-19 | `types.ts:842` | Change `tasks: SceneTask[]` to `tasks?: SceneTask[]` in `GameScene` to match actual data. |
| F30-20 | `GameSequenceRenderer.tsx:231` | Guard against `total_scenes === 0` division. |
| F30-21 | `mechanicRegistry.ts:372` | Strengthen memory_match validateConfig: `!bp.memoryMatchConfig?.pairs?.length` (check for empty array too). |
| F30-22 | `utils/extractTaskConfig.ts` | Remove or document as dead code. The main rendering path does not use this file. |

---

## Summary of Risk by Mechanic

| Mechanic | Risk Level | Key Issues |
|----------|-----------|------------|
| drag_drop | LOW | Well-tested, main path |
| click_to_identify | MEDIUM | Progress null check needed (CI-2) |
| trace_path | LOW | Config forwarding works |
| sequencing | HIGH | items.length crash (SQ-1), multi-task completion (F30-3) |
| sorting_categories | HIGH | correctCategoryId mismatch (SO-3), multi-task completion (F30-3) |
| memory_match | MEDIUM | Empty pairs render (MM-2,3), multi-task completion (F30-3) |
| branching_scenario | HIGH | Empty startNodeId crash (BR-2), multi-task completion (F30-3) |
| compare_contrast | MEDIUM | No validateConfig (CC-1), expectedCategories crash (CC-3) |
| description_matching | HIGH | Correctness namespace mismatch (DM-4) |
| hierarchical | MEDIUM | Null callback (HI-1) |

## Summary of Risk by Feature

| Feature | Risk Level | Key Issues |
|---------|-----------|------------|
| Single-scene, single-mechanic | LOW | Only drag_drop is fully tested |
| Single-scene, multi-mechanic | HIGH | F30-3 (premature completion for non-drag-drop mechanics) |
| Multi-scene, single-mechanic per scene | HIGH | F30-2 (dual completion handlers), score accumulation |
| Multi-scene, multi-mechanic per scene | CRITICAL | F30-2 + F30-3 + F30-7 (dual handlers + premature completion + config divergence) |
| Multi-scene, multi-task per scene | CRITICAL | F30-7 (sceneToBlueprint divergence), score accumulation across tasks |

---

**End of audit. 22 proposed fixes, 4 critical, 6 high, 7 medium, 5 low.**
