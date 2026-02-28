# 31 -- Frontend State Management Audit

**Date:** 2026-02-14
**Scope:** `useInteractiveDiagramState.ts` (Zustand store), `useMechanicDispatch.ts`, `mechanicRegistry.ts`, `engine/` modules, `index.tsx`, `GameSequenceRenderer.tsx`
**Goal:** Identify every bug preventing multi-scene, multi-mechanic games from working without exceptions.

---

## 1. Complete Store Shape

### 1.1 State Fields (Lines 90-208)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `availableLabels` | `(Label \| DistractorLabel)[]` | `[]` | Labels not yet placed |
| `placedLabels` | `PlacedLabel[]` | `[]` | Labels placed on zones |
| `score` | `number` | `0` | Current cumulative score |
| `maxScore` | `number` | `0` | Maximum possible score |
| `basePointsPerZone` | `number` | `10` | Points awarded per correct item |
| `isComplete` | `boolean` | `false` | Whether current mechanic/game is done |
| `showHints` | `boolean` | `false` | Hint overlay visibility |
| `draggingLabelId` | `string \| null` | `null` | Currently dragged label ID |
| `incorrectFeedback` | `{ labelId, message } \| null` | `null` | Feedback for wrong placement |
| `blueprint` | `InteractiveDiagramBlueprint \| null` | `null` | Current active blueprint |
| `originalBlueprint` | `InteractiveDiagramBlueprint \| null` | `null` | Blueprint stored at first init for reset |
| `interactionMode` | `InteractionMode` | `'' as InteractionMode` | Current mechanic type |
| `pathProgress` | `PathProgress \| null` | `null` | Trace path progress |
| `identificationProgress` | `IdentificationProgress \| null` | `null` | Click-to-identify progress |
| `hierarchyState` | `HierarchyState \| null` | `null` | Hierarchical mode state |
| `multiSceneState` | `MultiSceneState \| null` | `null` | Multi-scene tracking |
| `gameSequence` | `GameSequence \| null` | `null` | Full game sequence definition |
| `descriptionMatchingState` | `DescriptionMatchingState \| null` | `null` | Description matching progress |
| `temporalConstraints` | `TemporalConstraint[]` | `[]` | Zone visibility constraints |
| `motionPaths` | `MotionPath[]` | `[]` | Animation motion paths |
| `completedZoneIds` | `Set<string>` | `new Set()` | Zones correctly labeled |
| `visibleZoneIds` | `Set<string>` | `new Set()` | Currently visible zones |
| `blockedZoneIds` | `Set<string>` | `new Set()` | Zones blocked by mutex |
| `multiModeState` | `MultiModeState \| null` | `null` | Multi-mode game tracking |
| `modeTransitions` | `ModeTransition[]` | `[]` | Transition rules between modes |
| `_transitionTimerId` | `ReturnType<typeof setTimeout> \| null` | `null` | Timer for auto-transition cleanup |
| `sequencingProgress` | `SequencingProgress \| null` | `null` | Sequencing mechanic progress |
| `sortingProgress` | `SortingProgress \| null` | `null` | Sorting mechanic progress |
| `memoryMatchProgress` | `MemoryMatchProgress \| null` | `null` | Memory match progress |
| `branchingProgress` | `BranchingProgress \| null` | `null` | Branching scenario progress |
| `compareProgress` | `CompareProgress \| null` | `null` | Compare/contrast progress |
| `scoringConfig` | `ScoringConfig` | `{ basePointsPerItem: 10, ... }` | Active scoring configuration |

### 1.2 MultiSceneState Shape

```typescript
interface MultiSceneState {
  currentSceneIndex: number;       // Index into gameSequence.scenes[]
  completedSceneIds: string[];     // IDs of completed scenes
  sceneResults: SceneResult[];     // Per-scene results
  totalScore: number;              // Cumulative score across scenes
  isSequenceComplete: boolean;     // All scenes done
  currentTaskIndex: number;        // Index into current scene's tasks[]
  taskResults: TaskResult[];       // Per-task results
}
```

---

## 2. All Actions and Their Side Effects

### 2.1 Initialization Actions

| Action | Lines | Description | Side Effects |
|--------|-------|-------------|-------------|
| `initializeGame(blueprint)` | 253-361 | Initialize/reinitialize for a single blueprint | Resets score/labels/progress; sets interactionMode from mechanics[0]; computes maxScore; calls initializeMechanicProgress(); preserves originalBlueprint if first init; calls updateVisibleZones() |
| `initializeMultiSceneGame(sequence)` | 587-613 | Initialize multi-scene game | Creates MultiSceneState; calls sceneToBlueprint for first scene; calls initializeGame for first scene |
| `initializeMultiMode(mechanics, transitions)` | 1050-1069 | Initialize multi-mode state | Sets interactionMode to first mechanic; creates MultiModeState; sets modeTransitions |
| `initializeDescriptionMatching(mode)` | 663-671 | Initialize description matching | Sets descriptionMatchingState with currentIndex=0, empty matches |

### 2.2 Gameplay Actions

| Action | Lines | Description | Side Effects |
|--------|-------|-------------|-------------|
| `placeLabel(labelId, zoneId)` | 363-448 | Place a label on a zone | Returns boolean; updates score via calculateScoreDelta(); adds to completedZoneIds; checks completion; calls updateVisibleZones(); calls checkModeTransition() |
| `removeLabel(labelId)` | 450-477 | Remove a placed label | Deducts basePointsPerItem from score; removes from completedZoneIds; calls updateVisibleZones() |
| `setDraggingLabel(labelId)` | 479-481 | Set drag state | Clears incorrectFeedback |
| `toggleHints()` | 483-485 | Toggle hint visibility | Toggles showHints |
| `resetGame()` | 487-496 | Full game reset | Uses originalBlueprint; clears originalBlueprint; calls initializeGame() |
| `clearIncorrectFeedback()` | 498-500 | Clear incorrect feedback | Sets incorrectFeedback to null |

### 2.3 Mechanic Progress Actions

| Action | Lines | Description | Side Effects |
|--------|-------|-------------|-------------|
| `updatePathProgress(progress)` | 502-525 | Update trace path progress | Delta-based scoring for new waypoints; sets isComplete; calls checkModeTransition() on complete |
| `updateIdentificationProgress(progress)` | 527-556 | Update click-to-identify progress | Delta-based scoring; checks completion against identificationPrompts length; calls checkModeTransition() on complete |
| `updateHierarchyState(state)` | 558-560 | Update hierarchy state | Direct set, no side effects |
| `completeInteraction()` | 562-581 | Signal mechanic completion | Recalculates maxScore; checks hasRemainingModes(); if remaining modes, calls checkModeTransition() instead of marking complete |
| `recordDescriptionMatch(match)` | 673-697 | Record a description match | Delta-based scoring; checks completion against zones with descriptions |
| `updateSequenceOrder(itemOrder)` | 703-712 | Update sequence item order | Updates currentOrder in sequencingProgress |
| `submitSequence()` | 714-751 | Submit sequence for grading | Compares against correctOrder; partial credit via scoringConfig; if all correct, sets isComplete or calls checkModeTransition() |
| `updateSortingPlacement(itemId, categoryId)` | 753-765 | Place item in sorting category | Updates itemCategories map |
| `submitSorting()` | 767-802 | Submit sorting for grading | Compares against items[].correctCategoryId; partial credit; if all correct, sets isComplete or calls checkModeTransition() |
| `recordMemoryMatch(pairId)` | 804-828 | Record a memory pair match | Adds pairId to matchedPairIds; scoring delta; if all matched, sets isComplete or calls checkModeTransition() |
| `recordMemoryAttempt()` | 830-839 | Record a memory flip attempt | Increments attempts counter |
| `recordBranchingChoice(nodeId, optionId, isCorrect, nextNodeId)` | 841-875 | Record a branching decision | Scoring delta; updates currentNodeId; appends to pathTaken; if nextNodeId is null (end node), sets isComplete or calls checkModeTransition() |
| `undoBranchingChoice()` | 877-897 | Undo last branching decision | Pops from pathTaken; reverses score delta; sets currentNodeId to previous |
| `updateCompareCategorization(zoneId, category)` | 899-911 | Set compare categorization for a zone | Updates categorizations map |
| `submitCompare()` | 913-950 | Submit compare for grading | Checks against expectedCategories; partial credit; if all correct, sets isComplete or calls checkModeTransition() |

### 2.4 Temporal Intelligence Actions

| Action | Lines | Description | Side Effects |
|--------|-------|-------------|-------------|
| `updateVisibleZones()` | 956-1032 | Recalculate visible/blocked zones | Builds mutex/parent maps; Phase 1: root zones; Phase 2: children of completed parents; respects mutex constraints |
| `getVisibleZones()` | 1034-1036 | Get visible zone set | Pure getter |
| `isZoneVisible(zoneId)` | 1038-1040 | Check zone visibility | Pure getter |
| `isZoneBlocked(zoneId)` | 1042-1044 | Check zone blocked state | Pure getter |

### 2.5 Multi-Mode Actions

| Action | Lines | Description | Side Effects |
|--------|-------|-------------|-------------|
| `checkModeTransition()` | 1071-1109 | Evaluate transition rules | Builds progress map; calls evaluateTransitions(); if satisfied, sets pendingTransition; starts 500ms timer for auto-transition; clears previous timer |
| `transitionToMode(newMode, transition)` | 1112-1173 | Execute mode transition | Closes previous modeHistory entry; initializes new mechanic progress via initializeMechanicProgress(); ACCUMULATES maxScore; preserves score and completedZoneIds; calls updateVisibleZones() |
| `getAvailableModes()` | 1175-1179 | Get available modes list | Pure getter |
| `canSwitchToMode(mode)` | 1181-1197 | Check if mode switch is allowed | Checks user_choice transitions and availableModes |

### 2.6 Scene/Task Lifecycle Actions

| Action | Lines | Description | Side Effects |
|--------|-------|-------------|-------------|
| `completeCurrentScene()` | 1203-1219 | Complete the current scene with result | Calls completeScene() with current score/labels |
| `advanceToNextScene()` | 1221-1247 | Advance to next scene in sequence | Uses sceneFlowGraph for non-linear; finds next scene index; calls advanceToScene() |
| `advanceToScene(sceneIndex)` | 615-635 | Jump to specific scene | Calls sceneToBlueprint(); resets currentTaskIndex to 0; calls initializeGame() |
| `completeScene(result)` | 637-657 | Record scene result | Appends to sceneResults; recalculates totalScore; checks isSequenceComplete |
| `advanceToNextTask()` | 1253-1301 | Advance to next task in scene | Records taskResult; if more tasks, reinitializes with next task's blueprint (clears visible/completed zones); if no more tasks, calls completeCurrentScene() + advanceToNextScene() |
| `getCurrentTask()` | 1303-1310 | Get current SceneTask | Pure getter |

---

## 3. Multi-Scene State Management Flow

### 3.1 Initialization Flow

```
initializeMultiSceneGame(sequence)
  -> Creates MultiSceneState { currentSceneIndex: 0, currentTaskIndex: 0, ... }
  -> sceneToBlueprint(firstScene, 0)      // engine/sceneManager.ts
  -> set({ multiSceneState, gameSequence })
  -> initializeGame(sceneBlueprint)        // Reinitializes all per-mechanic state
```

### 3.2 Task Advancement Flow

```
isComplete becomes true (via placeLabel/submitSequence/etc.)
  -> index.tsx useEffect (L544-569) detects isComplete + multiSceneState
  -> Checks for pending mode transition (guard against race)
  -> getSceneAction(multiSceneState, gameSequence) from engine/sceneManager.ts
  -> If 'advance_task': setTimeout(800ms) -> advanceToNextTask()
  -> If 'advance_scene': setTimeout(800ms) -> completeScene() + advanceToScene()
```

### 3.3 advanceToNextTask() Flow (L1253-1301)

```
advanceToNextTask()
  -> Records TaskResult for current task
  -> If nextIdx < tasks.length:
     -> Updates multiSceneState.currentTaskIndex = nextIdx
     -> Clears visibleZoneIds and completedZoneIds
     -> sceneToBlueprint(scene, sceneIndex, nextIdx)
     -> initializeGame(bp)               // Reinitializes score, labels, progress
  -> If no more tasks:
     -> completeCurrentScene()
     -> advanceToNextScene()
```

### 3.4 Score Handling Across Scenes

- **Per-task score**: Reset to 0 by `initializeGame()` on each task advance
- **Per-scene score**: Captured in `completeScene()` via `SceneResult.score`
- **Total score**: `multiSceneState.totalScore` accumulates from `sceneResults.reduce()`
- **Display score**: After `completeScene()`, `score` is set to `totalScore` (L654)

---

## 4. Bugs Found

### BUG-1: Double scene completion in GameSequenceRenderer (CRITICAL)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/GameSequenceRenderer.tsx:194-220`
**File:** `frontend/src/components/templates/InteractiveDiagramGame/index.tsx:544-569`

Both `GameSequenceRenderer.tsx` (L194-220) and `index.tsx` (L544-569) watch `isComplete` and `multiSceneState` to trigger scene/task advancement. This creates a race condition where both attempt to handle completion simultaneously.

In `GameSequenceRenderer.tsx:194-220`:
```typescript
useEffect(() => {
  if (!sceneIsComplete || !multiSceneState || multiSceneState.isSequenceComplete) return;
  completeCurrentScene();   // <-- fires alongside index.tsx handler
  ...
  advanceToNextScene();
}, [sceneIsComplete, multiSceneState, ...]);
```

In `index.tsx:544-569`:
```typescript
useEffect(() => {
  if (isComplete && multiSceneState && gameSequence && !multiModeState?.pendingTransition) {
    const action = getSceneAction(multiSceneState, gameSequence);
    if (action.type === 'advance_task') {
      setTimeout(() => advanceToNextTask(), 800);    // <-- also fires
    }
    ...
  }
}, [isComplete, multiSceneState, ...]);
```

**Impact:** `completeCurrentScene()` can be called twice, doubling the scene result in `sceneResults[]`, corrupting `totalScore`, and potentially calling `advanceToNextScene()` when tasks remain.

**Root Cause:** Two independent effects watching the same state trigger with no coordination.

---

### BUG-2: GameSequenceRenderer bypasses task-level advancement (CRITICAL)

**File:** `GameSequenceRenderer.tsx:194-220`

The `GameSequenceRenderer` effect calls `completeCurrentScene()` + `advanceToNextScene()` directly, completely ignoring the task system. It does not check whether there are remaining tasks in the current scene.

```typescript
// L198: Directly completes scene without checking tasks
completeCurrentScene();
// L214-218: Directly advances to next scene
advanceToNextScene();
```

**Impact:** In a multi-task scene, when the first task completes and `isComplete` becomes true, `GameSequenceRenderer` will skip remaining tasks and jump to the next scene.

---

### BUG-3: Score captured before task completion in advanceToNextTask (MEDIUM)

**File:** `useInteractiveDiagramState.ts:1254-1270`

```typescript
advanceToNextTask: () => {
  const { gameSequence, multiSceneState, score, placedLabels } = get();
  // ... captures score here ...
  const taskResult: TaskResult = {
    task_id: currentTask?.task_id || `task_${currentTaskIdx}`,
    score,                    // <-- This is per-task score (reset each task)
    max_score: get().maxScore, // <-- Per-task maxScore
    completed: true,
    matches: placedLabels.map(p => ({ ...p })),
  };
```

The `score` here reflects only the current task's score (reset at each `initializeGame()`), which is correct. However, `taskResults` accumulate per-task results but are never used to compute a cumulative display score. The user sees `score` (per-task) in the UI, not cumulative progress across tasks in a scene.

**Impact:** Score display during multi-task scenes shows only the current task's score, not the scene total. Users may think their earlier task scores are lost.

---

### BUG-4: advanceToNextTask calls both completeCurrentScene and advanceToNextScene without score accumulation (MEDIUM)

**File:** `useInteractiveDiagramState.ts:1298-1299`

```typescript
// All tasks done in this scene -- complete and advance to next scene
get().completeCurrentScene();
get().advanceToNextScene();
```

`completeCurrentScene()` (L1203-1219) calls `completeScene()` with `score` (the current task's score, not the sum of all task scores in this scene). This means the `SceneResult.score` only captures the last task's score, not the cumulative score across all tasks.

**Impact:** Multi-task scene scores are undercounted. Only the final task's score contributes to the scene result.

---

### BUG-5: canSwitchToMode always returns true for any available mode (LOW)

**File:** `useInteractiveDiagramState.ts:1181-1197`

```typescript
canSwitchToMode: (mode: InteractionMode) => {
  // ...
  return hasUserChoiceTransition || multiModeState.availableModes.includes(mode);
```

The last condition `multiModeState.availableModes.includes(mode)` always returns true if the mode is in the list, regardless of whether a `user_choice` transition exists. This means any mode can be switched to manually, even if transitions require automatic triggers only.

**Impact:** Users can skip mandatory transition triggers (e.g., `all_zones_labeled`) by manually switching modes.

---

### BUG-6: completedSceneIds mapping in SceneIndicator is wrong (LOW)

**File:** `index.tsx:1006-1007`

```typescript
<SceneIndicator
  totalScenes={sequence.total_scenes}
  currentScene={currentSceneIndex + 1}
  completedScenes={completedSceneIds.map((_, i) => i + 1)}  // <-- Bug
/>
```

`completedSceneIds` is an array of scene ID strings (e.g., `["scene_heart_1", "scene_heart_2"]`). The mapping `(_, i) => i + 1` produces `[1, 2, ...]` which is the completion ORDER, not the scene NUMBER. If scenes are completed out of order (branching/zoom_in progression), the indicator shows wrong scenes as completed.

**Impact:** Visual-only bug, but misleading in non-linear progression types.

---

### BUG-7: undoBranchingChoice score reversal is asymmetric with scoring engine (MEDIUM)

**File:** `useInteractiveDiagramState.ts:884-896`

```typescript
undoBranchingChoice: () => {
  // ...
  const reverseDelta = removedStep.isCorrect
    ? -state.scoringConfig.basePointsPerItem
    : state.scoringConfig.attemptPenalty;
```

When scoring a correct choice, `recordBranchingChoice` uses `calculateScoreDelta(config, { isCorrect: true })` which applies streakMultiplier. But `undoBranchingChoice` reverses with flat `basePointsPerItem`, not the actual delta that was applied. If `streakMultiplier > 1`, the undo will deduct less than what was added.

Similarly, for incorrect choices, `calculateScoreDelta(config, { isCorrect: false })` returns `-attemptPenalty` (negative), but the reversal code adds `attemptPenalty` (positive). So the sign is correct, but the magnitude is only correct if attemptPenalty is symmetric with what was deducted.

**Impact:** Score desync when streakMultiplier > 1 (default is 1, so currently dormant).

---

### BUG-8: submitSequence does not account for already-accumulated score from reorder operations (LOW)

**File:** `useInteractiveDiagramState.ts:733-740`

```typescript
submitSequence: () => {
  // ...
  set({
    sequencingProgress: { ...sequencingProgress, isSubmitted: true, correctPositions },
    score: state.score + scoreDelta,
  });
```

The `updateSequenceOrder` action (L703-712) does not modify the score -- only `submitSequence` does. This is actually correct behavior (batch scoring on submit). However, if `submitSequence` is called multiple times (no guard against re-submission), the score would be added again.

**Impact:** Low risk. `isSubmitted` is set to true, but nothing prevents calling `submitSequence()` again since the guard only checks `!sequencingProgress` (L717), not `sequencingProgress.isSubmitted`.

---

### BUG-9: submitSorting, submitCompare have same re-submission vulnerability (LOW)

**File:** `useInteractiveDiagramState.ts:767-802` (submitSorting), `913-950` (submitCompare)

Same issue as BUG-8. The `isSubmitted` flag is set but never checked as a guard condition. Calling `submitSorting()` or `submitCompare()` multiple times would add the score again.

---

### BUG-10: initializeGame preserves originalBlueprint only on first init (MEDIUM)

**File:** `useInteractiveDiagramState.ts:329, 343`

```typescript
const existingOriginal = get().originalBlueprint;
set({
  ...
  originalBlueprint: existingOriginal || blueprint,
  ...
});
```

In multi-scene games, `initializeGame()` is called for each scene/task. The first scene's blueprint becomes `originalBlueprint`. When `resetGame()` fires, it reinitializes with the FIRST scene's blueprint, not the overall game. This is intentional per the `QW-8` comment, but it means:

- In multi-scene mode, `resetGame()` restarts from the first scene
- In multi-task mode, `resetGame()` restarts from the first task of the first scene
- There is no way to reset just the current scene/task

**Impact:** Reset behavior may confuse users who expect to restart only the current scene. Works correctly for single-scene games.

---

### BUG-11: _transitionTimerId not cleaned up on unmount (LOW)

**File:** `useInteractiveDiagramState.ts:1104-1108`

```typescript
const timerId = setTimeout(() => {
  set({ _transitionTimerId: null });
  get().transitionToMode(transition.to, transition);
}, transition.animation === 'none' ? 0 : 500);
set({ _transitionTimerId: timerId });
```

The timer is cleaned up when a new transition starts (L1100-1101), but there is no cleanup when the component unmounts. If the game component unmounts during a pending transition, the setTimeout callback will fire on a stale store.

**Impact:** Zustand stores are global singletons, so the callback would modify global state after the component is gone. Low impact because the store persists anyway, but could cause unexpected state if a new game initializes during the timeout window.

---

### BUG-12: Set<string> serialization for persistence (MEDIUM)

**File:** `useInteractiveDiagramState.ts:232-234`

```typescript
completedZoneIds: new Set(),
visibleZoneIds: new Set(),
blockedZoneIds: new Set(),
```

Zustand stores with `Set` objects cannot be directly serialized to JSON for persistence. `JSON.stringify(new Set(['a', 'b']))` produces `{}`. The `usePersistence` hook (referenced in index.tsx:400-413) would lose these fields on save/load.

**Impact:** After restoring a saved game, all zone visibility state is lost. Temporal constraints would malfunction because `completedZoneIds` is empty, causing zones to not reveal properly.

---

### BUG-13: completeScene sets top-level score to totalScore (SEMANTICS)

**File:** `useInteractiveDiagramState.ts:654`

```typescript
set({
  multiSceneState: { ...multiSceneState, ... },
  score: newTotalScore,     // <-- Overrides per-task score with cumulative total
  isComplete: isSequenceComplete,
});
```

After `completeScene()`, the top-level `score` is set to the cumulative `totalScore`. But then `advanceToScene()` calls `initializeGame()` which resets `score` to 0. This creates a brief flicker: score goes to totalScore, then immediately to 0.

**Impact:** If any code reads `score` between `completeScene()` and `initializeGame()` (e.g., a render cycle), it would see the cumulative total briefly, then 0. Generally harmless due to React batching, but could cause visual flicker.

---

### BUG-14: interactionMode initialized to empty string (LOW)

**File:** `useInteractiveDiagramState.ts:222`

```typescript
interactionMode: '' as InteractionMode,
```

Before `initializeGame()` is called, `interactionMode` is an empty string cast to `InteractionMode`. Any code that reads this before initialization (e.g., registry lookups) would get `undefined` from `MECHANIC_REGISTRY['']`.

**Impact:** Only a problem if the store is read before initialization, which could happen during the first render. The `MechanicRouter` would show `MechanicConfigError` for mode `''`.

---

### BUG-15: Sorting correctness check ignores multi-category support (MEDIUM)

**File:** `useInteractiveDiagramState.ts:772-777`

```typescript
for (const item of blueprint.sortingConfig.items) {
  if (sortingProgress.itemCategories[item.id] === item.correctCategoryId) {
    correctCount++;
  }
}
```

`SortingItem` has both `correctCategoryId: string` and `correct_category_ids?: string[]` for multi-category support. The `submitSorting()` action only checks against `correctCategoryId`, ignoring `correct_category_ids`.

**Impact:** Items that can belong to multiple correct categories will only be counted correct if placed in the single `correctCategoryId`.

---

### BUG-16: advanceToNextTask score not accumulated across tasks (CRITICAL)

**File:** `useInteractiveDiagramState.ts:1253-1301`

When advancing from task 1 to task 2 within a scene:

1. Task 1 completes with score = 30 (stored in taskResult)
2. `initializeGame(bp)` resets score to 0 for task 2
3. Task 2 plays and gets score = 20
4. When all tasks done, `completeCurrentScene()` captures `score` = 20 (only last task)
5. `completeScene()` adds this to `totalScore`

The per-task scores stored in `taskResults` are never summed to form the scene score. The cumulative scene score should be the sum of all task scores, not just the last task's score.

This is the same as BUG-4 but stated more precisely with the data flow.

**Impact:** In a 3-task scene where the user scores 30, 20, 10, the scene result would record score=10 instead of 60.

---

### BUG-17: No guard against advancing past the last scene (LOW)

**File:** `useInteractiveDiagramState.ts:1221-1247`

`advanceToNextScene()` calls `getNextSceneId()` which can return `null` (game complete). When `null`, the function silently does nothing. But the caller in `advanceToNextTask()` (L1298-1299) calls both `completeCurrentScene()` and `advanceToNextScene()` without checking whether `advanceToNextScene()` actually advances. The game just sits there because `isSequenceComplete` was already set by `completeScene()`.

**Impact:** Not a crash, but the completion flow is unclear. The game relies on `isComplete && isSequenceComplete` being checked in index.tsx to show results.

---

### BUG-18: Multiple useMemo/useCallback have stale dependency arrays in index.tsx (LOW)

**File:** `index.tsx:928`

```typescript
}, [buildMechanicRouterProps, interactionMode, placedLabels, availableLabels, ...]);
// eslint-disable-next-line react-hooks/exhaustive-deps
```

The `renderScene` callback has an `eslint-disable-next-line` comment suppressing the exhaustive-deps warning. This means there may be stale closures in the render callback.

**Impact:** Potential stale data in scene rendering. Low risk because most state is read from the Zustand store directly.

---

## 5. Score Handling Per Mechanic Type

### 5.1 Score Flow Summary

| Mechanic | Score Event | Score Calculation | Accumulation |
|----------|-----------|-------------------|--------------|
| `drag_drop` | `placeLabel()` correct | `calculateScoreDelta(config, { isCorrect: true })` | Additive per placement |
| `drag_drop` | `placeLabel()` incorrect | `calculateScoreDelta(config, { isCorrect: false })` = `-attemptPenalty` | Deducted (clamped to 0) |
| `drag_drop` | `removeLabel()` | `-scoringConfig.basePointsPerItem` | Direct deduction |
| `click_to_identify` | `updateIdentificationProgress()` | Delta = (new - prev completed) * `calculateScoreDelta()` | Additive per new completion |
| `trace_path` | `updatePathProgress()` | Delta = (new - prev waypoints) * `calculateScoreDelta()` | Additive per new waypoint |
| `sequencing` | `submitSequence()` | If partialCredit: correctPositions * basePointsPerItem. Else: all-or-nothing | One-time on submit |
| `sorting_categories` | `submitSorting()` | If partialCredit: correctCount * basePointsPerItem. Else: all-or-nothing | One-time on submit |
| `memory_match` | `recordMemoryMatch()` | `calculateScoreDelta(config, { isCorrect: true })` | Additive per match |
| `branching_scenario` | `recordBranchingChoice()` | `calculateScoreDelta(config, { isCorrect })` | Additive/deductive per choice |
| `compare_contrast` | `submitCompare()` | If partialCredit: correctCount * basePointsPerItem. Else: all-or-nothing | One-time on submit |
| `description_matching` | `recordDescriptionMatch()` | `calculateScoreDelta(config, { isCorrect: match.isCorrect })` | Additive per match |

### 5.2 maxScore Calculation

- **Initial**: `blueprint.scoringStrategy.max_score` if present, else `getMaxScore(mode, blueprint, basePointsPerZone)` from registry
- **Mode transitions**: `transitionToMode()` ACCUMULATES by adding `getMaxScore(newMode, ...)` to existing maxScore (L1141)
- **Task transitions**: `advanceToNextTask()` calls `initializeGame()` which recalculates from scratch for the new task
- **Scene transitions**: `advanceToScene()` calls `initializeGame()` which recalculates from scratch

### 5.3 Score Across Mode Transitions

Score is PRESERVED across mode transitions (L1149: `score: get().score`). This is correct -- a multi-mode game accumulates score across all mechanics.

### 5.4 Score Across Task Transitions

Score is RESET to 0 by `initializeGame()` at each task transition. Task scores are captured in `taskResults[]` but never summed for the scene result. See BUG-4/BUG-16.

---

## 6. Completion and Transition Logic Per Mechanic

### 6.1 drag_drop

- **Completion**: `placedCorrectCount >= taskLabelCount` where taskLabelCount comes from `_getTaskLabelCount()` (task-aware) or `blueprint.labels.length`
- **Transition trigger**: `all_zones_labeled` -> checks `correctPlacements >= totalLabels`
- **isComplete guard**: Also checks `!hasRemainingModes(multiModeState)` before setting `isComplete = true`

### 6.2 click_to_identify

- **Completion**: `progress.currentPromptIndex >= totalPrompts` where totalPrompts = `blueprint.identificationPrompts.length`
- **Transition trigger**: `identification_complete` -> same check
- **isComplete**: Set directly in `updateIdentificationProgress()`

### 6.3 trace_path

- **Completion**: `pathProgress.isComplete` (set externally by component/dispatch)
- **Transition trigger**: `path_complete` -> checks all paths in `pathProgressMap` are complete
- **Note**: The store's `PathProgress` is single-path, while the registry expects `TracePathProgress` with multi-path support. `_buildProgressMap()` wraps single into multi.

### 6.4 sequencing

- **Completion**: `isSubmitted && correctPositions === totalPositions`
- **Transition trigger**: `sequence_complete` -> same check
- **isComplete**: Set in `submitSequence()` only if no modeTransitions exist

### 6.5 sorting_categories

- **Completion**: `isSubmitted && correctCount === totalCount`
- **Transition trigger**: `sorting_complete` -> same check
- **isComplete**: Set in `submitSorting()` only if no modeTransitions exist

### 6.6 memory_match

- **Completion**: `matchedPairIds.length >= totalPairs`
- **Transition trigger**: `memory_complete` -> same check
- **isComplete**: Set in `recordMemoryMatch()` only if no modeTransitions exist

### 6.7 branching_scenario

- **Completion**: Current node has `isEndNode === true`
- **Transition trigger**: `branching_complete` -> same check
- **isComplete**: Set in `recordBranchingChoice()` when `nextNodeId === null`

### 6.8 compare_contrast

- **Completion**: `isSubmitted && correctCount === totalCount`
- **Transition trigger**: `compare_complete` -> same check
- **isComplete**: Set in `submitCompare()` only if no modeTransitions exist

### 6.9 description_matching

- **Completion**: `currentIndex >= zonesWithDescriptions.length`
- **Transition trigger**: `description_complete` -> same check
- **isComplete**: Set directly in `recordDescriptionMatch()`

### 6.10 hierarchical

- **Completion**: `placedCorrect >= totalLabels + childZones` (best-effort check in registry)
- **Transition trigger**: `hierarchy_level_complete` -> checks all zones at current level are placed
- **isComplete**: Relies on `completeInteraction()` being called by the HierarchyController component

---

## 7. Proposed Fixes

### FIX-1: Eliminate double completion handler (BUG-1, BUG-2)

**Problem:** Both `GameSequenceRenderer.tsx` and `index.tsx` handle scene/task completion.

**Proposed Fix:** Remove the `useEffect` in `GameSequenceRenderer.tsx:194-220` entirely. The advancement logic already exists in `index.tsx:544-569` and is more sophisticated (checks `getSceneAction()`, handles both `advance_task` and `advance_scene`).

```
File: frontend/src/components/templates/InteractiveDiagramGame/interactions/GameSequenceRenderer.tsx
Lines: 194-220
Action: Remove the entire useEffect block. GameSequenceRenderer should be a pure renderer
        that delegates lifecycle to the parent (index.tsx).
```

### FIX-2: Accumulate task scores for scene result (BUG-4, BUG-16)

**Problem:** `completeCurrentScene()` captures only the last task's score.

**Proposed Fix:** In `completeCurrentScene()` (L1203-1219), sum all task results plus the current task's score to form the scene score.

```
File: frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts
Lines: 1203-1219
Change: Replace `score` with accumulated task score:

  const previousTaskScore = multiSceneState.taskResults.reduce(
    (sum, tr) => sum + tr.score, 0
  );
  const sceneScore = previousTaskScore + score;  // current task's score + previous tasks

  get().completeScene({
    scene_id: currentScene.scene_id,
    score: sceneScore,
    max_score: ...,
    ...
  });
```

### FIX-3: Guard against double submission (BUG-8, BUG-9)

**Problem:** `submitSequence()`, `submitSorting()`, `submitCompare()` can be called multiple times.

**Proposed Fix:** Add `isSubmitted` guard at the top of each submit action.

```
File: frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts

For submitSequence (L714):
  Add: if (sequencingProgress.isSubmitted) return;

For submitSorting (L767):
  Add: if (sortingProgress.isSubmitted) return;

For submitCompare (L913):
  Add: if (compareProgress.isSubmitted) return;
```

### FIX-4: Fix canSwitchToMode permissiveness (BUG-5)

**Problem:** Any available mode can be switched to regardless of transition type.

**Proposed Fix:** Only allow switch if a `user_choice` transition exists from current mode to target mode.

```
File: frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts
Lines: 1181-1197
Change: Remove the fallback `|| multiModeState.availableModes.includes(mode)`.
        Return only `hasUserChoiceTransition`.
```

### FIX-5: Fix Set serialization for persistence (BUG-12)

**Problem:** `Set<string>` fields are not JSON-serializable.

**Proposed Fix:** Either:
(a) Convert Sets to arrays before saving and back on load in `usePersistence`, OR
(b) Use arrays instead of Sets in the store (with `.includes()` checks).

Option (a) is less invasive:
```
File: Wherever usePersistence serializes/deserializes state
Change: Add serialization transform:
  - On save: completedZoneIds -> Array.from(completedZoneIds)
  - On load: completedZoneIds -> new Set(savedArray)
  - Same for visibleZoneIds, blockedZoneIds
```

### FIX-6: Fix undoBranchingChoice score reversal (BUG-7)

**Problem:** Reversal uses flat `basePointsPerItem` instead of actual scored delta.

**Proposed Fix:** Store the actual delta in each pathTaken entry so undo can reverse exactly.

```
File: frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts

In recordBranchingChoice (L841-875):
  Change pathTaken entry to include actual delta:
    { nodeId, optionId, isCorrect, scoreDelta }

In undoBranchingChoice (L877-897):
  Use stored delta:
    const reverseDelta = -removedStep.scoreDelta;
```

This requires extending the `BranchingProgress.pathTaken` type to include `scoreDelta: number`.

### FIX-7: Fix completedSceneIds mapping in SceneIndicator (BUG-6)

**File:** `index.tsx:1006-1007`

```
Change:
  completedScenes={completedSceneIds.map((_, i) => i + 1)}
To:
  completedScenes={completedSceneIds.map(id => {
    const scene = sequence.scenes.find(s => s.scene_id === id);
    return scene ? scene.scene_number : 0;
  }).filter(n => n > 0)}
```

### FIX-8: Support multi-category sorting (BUG-15)

**File:** `useInteractiveDiagramState.ts:772-777`

```
Change correctness check to:
  const correctCategoryIds = item.correct_category_ids || [item.correctCategoryId];
  if (correctCategoryIds.includes(sortingProgress.itemCategories[item.id])) {
    correctCount++;
  }
```

### FIX-9: Clean up transition timer on store reset (BUG-11)

**File:** `useInteractiveDiagramState.ts:487-496`

```
In resetGame(), before calling initializeGame():
  const timerId = get()._transitionTimerId;
  if (timerId) clearTimeout(timerId);
```

### FIX-10: Display cumulative score during multi-task scenes (BUG-3)

This is a UI/UX decision rather than a bug fix. Options:
(a) Show per-task score (current behavior) -- simpler but potentially confusing
(b) Show cumulative scene score by summing `taskResults[].score + score`

If option (b):
```
File: index.tsx or GameControls
Change: Instead of passing raw `score`, pass:
  const displayScore = multiSceneState
    ? multiSceneState.taskResults.reduce((s, r) => s + r.score, 0) + score
    : score;
```

---

## 8. Engine Module Assessment

### 8.1 scoringEngine.ts -- SOUND

- `getScoringConfig()` correctly reads mechanic-level scoring, falls back to blueprint strategy, then defaults
- `calculateScoreDelta()` handles positive/negative correctly
- `getMaxScore()` delegates to registry, with fallback to labels.length * points

### 8.2 completionDetector.ts -- SOUND

- `isMechanicComplete()` correctly delegates to registry
- `hasRemainingModes()` correctly filters current + completed from available
- `isGameComplete()` combines mechanic completion + remaining modes check

### 8.3 transitionEvaluator.ts -- SOUND

- Correctly delegates to registry `checkTrigger()` first
- Handles generic triggers (`percentage_complete`, `specific_zones`, `time_elapsed`, `user_choice`)
- Returns first matching transition (priority is insertion order)

### 8.4 sceneManager.ts -- SOUND

- `sceneToBlueprint()` correctly filters zones/labels to task subset
- Handles camelCase/snake_case config fallbacks
- Filters temporal constraints to task zones
- `getSceneAction()` correctly determines advance_task vs advance_scene vs complete_game

### 8.5 mechanicInitializer.ts -- SOUND

- Correctly nulls all progress fields, then merges registry's `initializeProgress()` output
- Ensures clean state for each mechanic transition

### 8.6 feedbackEngine.ts -- SOUND

- Correctly checks mechanic-level feedback, then misconception matches, then animationCues fallback

### 8.7 correctnessEvaluator.ts -- SOUND

- `evaluateIdentification()` correctly compares zone against current prompt
- `evaluateDescriptionMatch()` correctly checks label.correctZoneId === zoneId

### 8.8 sceneFlowGraph.ts -- SOUND

- Falls back to linear progression when no flow graph exists
- Handles conditional edges (score_threshold, completion)

---

## 9. useMechanicDispatch.ts Assessment

### 9.1 Action Coverage

All 11 mechanic types are handled:
- `identify` (click_to_identify)
- `visit_waypoint`, `submit_path` (trace_path)
- `reorder`, `submit_sequence` (sequencing)
- `sort`, `unsort`, `submit_sorting` (sorting_categories)
- `match_pair`, `memory_attempt` (memory_match)
- `branching_choice`, `branching_undo` (branching_scenario)
- `categorize`, `submit_compare` (compare_contrast)
- `description_match` (description_matching)
- `place`, `remove` (drag_drop)

### 9.2 Correctness Evaluation

The dispatch hook evaluates correctness for `identify` and `description_match` using `evaluateIdentification()` and `evaluateDescriptionMatch()` from the engine. For other mechanics, correctness is evaluated within the store actions themselves.

### 9.3 Potential Issue: Direct Store Access in Callbacks

**File:** `useMechanicDispatch.ts:142, 162, 202`

```typescript
const sp = useInteractiveDiagramState.getState().sequencingProgress;
```

The dispatch hook accesses the store directly via `getState()` inside `useCallback`. This is valid because Zustand's `set()` is synchronous, so `getState()` reflects the post-update state. No bug here.

---

## 10. mechanicRegistry.ts Assessment

### 10.1 Registry Coverage

All 11 mechanic modes have registry entries with:
- `component` reference
- `needsDndContext` flag
- `configKey` for blueprint config lookup
- `extractProps()` for component props
- `getMaxScore()` for max score calculation
- `isComplete()` for completion detection
- `checkTrigger()` for transition trigger evaluation

### 10.2 Missing validateConfig

The following mechanics lack `validateConfig`:
- `compare_contrast` -- no validateConfig, but has complex legacy fallback in extractProps
- `hierarchical` -- no validateConfig, relies on zoneGroups being present

**Impact:** Low. The game will render with fallback/empty data rather than showing an error.

### 10.3 timed_challenge Not in Registry

`timed_challenge` is not a registry entry -- it's handled as a special wrapper in `MechanicRouter.tsx:54-68`. This is correct since it wraps another mechanic rather than being one itself.

---

## 11. Summary of Critical Bugs

| Priority | Bug | Impact | Fix Complexity |
|----------|-----|--------|---------------|
| P0 (CRITICAL) | BUG-1/BUG-2: Double completion handler | Corrupted scores, skipped tasks | Medium (remove one handler) |
| P0 (CRITICAL) | BUG-4/BUG-16: Task scores not accumulated for scene | Undercounted scene scores | Low (sum taskResults) |
| P1 (MEDIUM) | BUG-12: Set serialization for persistence | Lost zone state on restore | Medium (serialization transform) |
| P1 (MEDIUM) | BUG-15: Multi-category sorting ignored | Incorrect grading | Low (extend check) |
| P1 (MEDIUM) | BUG-7: Undo score reversal asymmetric | Score desync (dormant) | Low (store actual delta) |
| P1 (MEDIUM) | BUG-10: Reset restarts from first scene | Unexpected UX | Design decision |
| P2 (LOW) | BUG-8/BUG-9: Double submission adds score | Exploitable | Low (guard check) |
| P2 (LOW) | BUG-5: canSwitchToMode too permissive | Skip triggers | Low (remove fallback) |
| P2 (LOW) | BUG-6: SceneIndicator mapping wrong | Visual only | Low (fix mapping) |
| P2 (LOW) | BUG-11: Timer not cleaned on unmount | Stale callbacks | Low (add cleanup) |
| P2 (LOW) | BUG-14: Empty string interactionMode | Brief error flash | Low (default to drag_drop) |
| P2 (LOW) | BUG-3: Per-task score display | UX confusion | Design decision |
| P2 (LOW) | BUG-13: Score flicker between scenes | Visual only | Negligible |
| P2 (LOW) | BUG-17: Silent no-op after last scene | No crash | Already handled |
| P2 (LOW) | BUG-18: Stale closure in renderScene | Potential stale data | Low risk |

**Total: 18 bugs found (2 critical, 5 medium, 11 low)**

---

## 12. Architecture Strengths

1. **Registry-driven design**: `mechanicRegistry.ts` centralizes per-mechanic logic (maxScore, completion, triggers, initialization). Adding a new mechanic requires only a registry entry and a component.

2. **Engine separation**: All pure logic (scoring, completion, transitions, scene management) is in `engine/` modules with no React/Zustand dependencies. This is testable and composable.

3. **Unified action dispatch**: `useMechanicDispatch.ts` provides a single `onAction()` entry point for all mechanics, enabling consistent logging, analytics, and command history.

4. **Delta-based scoring**: All scoring uses `calculateScoreDelta()` from the scoring engine, preventing the score overwrite bugs that were present in earlier versions.

5. **Temporal intelligence**: The zone visibility system with mutex/parent constraints is well-implemented and correctly recalculated after each state change.

6. **Zustand immutability**: All `set()` calls use spread operators and new object creation. The earlier modeHistory mutation bug has been fixed (L1118-1127). No remaining in-place mutations found.
