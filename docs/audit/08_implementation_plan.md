# 08 — Detailed Implementation Plan

**Generated:** 2026-02-10
**Based on:** Audit docs 01–07 (~178 unique bugs)
**Approach:** Phase-by-phase with exact file changes, line numbers, and verification steps

---

## Phase 0: Critical One-Line Fixes — **DONE**

| Fix | Status |
|-----|--------|
| F1: canonical_labels routing | DONE |
| F2: MechanicConfigV3.config typing | DONE |
| F3: generation_complete flag | DONE |

---

## Phase 1: Frontend State & Logic Fixes (Critical Path)

### Fix 1.1: `removeLabel` — Update completedZoneIds + call updateVisibleZones (S-10, S-11)

**File:** `frontend/src/components/templates/LabelDiagramGame/hooks/useLabelDiagramState.ts`
**Lines:** 416–435

**Current code (broken):**
```ts
removeLabel: (labelId: string) => {
    const state = get();
    const { blueprint, placedLabels, availableLabels } = state;
    if (!blueprint) return;
    const placed = placedLabels.find((p) => p.labelId === labelId);
    if (!placed) return;
    const originalLabel = blueprint.labels.find((l) => l.id === labelId);
    if (!originalLabel) return;
    set({
      placedLabels: placedLabels.filter((p) => p.labelId !== labelId),
      availableLabels: [...availableLabels, originalLabel],
      score: state.score - state.basePointsPerZone,
      isComplete: false,
    });
},
```

**Bug:** When a label is removed (undo), `completedZoneIds` is NOT updated. This means:
1. Temporal constraints stay stale — children of un-completed parent remain visible
2. Mutex constraints don't re-block — partner zones stay incorrectly visible
3. `updateVisibleZones()` is never called after removal

**Fix:**
```ts
removeLabel: (labelId: string) => {
    const state = get();
    const { blueprint, placedLabels, availableLabels } = state;
    if (!blueprint) return;
    const placed = placedLabels.find((p) => p.labelId === labelId);
    if (!placed) return;
    const originalLabel = blueprint.labels.find((l) => l.id === labelId);
    if (!originalLabel) return;

    // Remove zone from completedZoneIds
    const newCompletedZoneIds = new Set(state.completedZoneIds);
    newCompletedZoneIds.delete(placed.zoneId);

    set({
      placedLabels: placedLabels.filter((p) => p.labelId !== labelId),
      availableLabels: [...availableLabels, originalLabel],
      score: Math.max(0, state.score - state.basePointsPerZone),
      isComplete: false,
      completedZoneIds: newCompletedZoneIds,
    });

    // Recalculate visible zones (may hide children, re-block mutex partners)
    get().updateVisibleZones();
},
```

**Verification:** Score cannot go negative. Undo a label on a parent zone → child zones should disappear.

---

### Fix 1.2: Score accumulation — Don't overwrite, accumulate (S-33, S-34, S-35)

**File:** `useLabelDiagramState.ts`

**Bug A — `updatePathProgress` (lines 456–466):**
```ts
// CURRENT (broken): Overwrites score
const newScore = pathProgress.visitedWaypoints.length * state.basePointsPerZone;
set({ pathProgress, score: newScore, isComplete });
```
In a multi-mechanic game (drag_drop → trace_path), the drag_drop score (e.g., 50pts) is overwritten to 0 when trace_path starts.

**Fix A:**
```ts
updatePathProgress: (pathProgress: PathProgress) => {
    const state = get();
    // Calculate delta from previous path progress
    const prevWaypoints = state.pathProgress?.visitedWaypoints.length || 0;
    const newWaypoints = pathProgress.visitedWaypoints.length;
    const delta = (newWaypoints - prevWaypoints) * state.basePointsPerZone;
    const isComplete = pathProgress.isComplete;

    set({
      pathProgress,
      score: state.score + delta,
      isComplete,
    });
},
```

**Bug B — `updateIdentificationProgress` (lines 468–483):**
Same pattern — `newScore = progress.completedZoneIds.length * pts` overwrites.

**Fix B:**
```ts
updateIdentificationProgress: (progress: IdentificationProgress) => {
    const state = get();
    const { blueprint } = state;
    if (!blueprint) return;

    const prevCompleted = state.identificationProgress?.completedZoneIds.length || 0;
    const newCompleted = progress.completedZoneIds.length;
    const delta = (newCompleted - prevCompleted) * state.basePointsPerZone;

    const totalPrompts = blueprint.identificationPrompts?.length || 0;
    const isComplete = progress.currentPromptIndex >= totalPrompts;

    set({
      identificationProgress: progress,
      score: state.score + delta,
      isComplete,
    });
},
```

**Bug C — `recordDescriptionMatch` (lines 638–660):**
Same pattern — `newScore = newMatches.filter(correct).length * pts` overwrites.

**Fix C:**
```ts
recordDescriptionMatch: (match: DescriptionMatch) => {
    const { descriptionMatchingState, blueprint } = get();
    if (!descriptionMatchingState || !blueprint) return;

    const newMatches = [...descriptionMatchingState.matches, match];
    const newIndex = descriptionMatchingState.currentIndex + 1;

    // Accumulate: only add points for this match, don't recalculate total
    const delta = match.isCorrect ? get().basePointsPerZone : 0;

    const zonesWithDescriptions = blueprint.diagram.zones.filter(z => z.description);
    const isComplete = newIndex >= zonesWithDescriptions.length;

    set({
      descriptionMatchingState: {
        ...descriptionMatchingState,
        currentIndex: newIndex,
        matches: newMatches,
      },
      score: get().score + delta,
      isComplete,
    });
},
```

**Verification:** Play a multi-mechanic game (drag_drop 5 zones → trace_path 3 waypoints). Final score should be 80pts, not 30pts.

---

### Fix 1.3: Completion detection — Per-mode label counting (S-6, S-18)

**File:** `useLabelDiagramState.ts`

**Bug in `placeLabel` (lines 363–366):**
```ts
const correctLabelsCount = blueprint.labels.length;         // ALL labels
const placedCorrectCount = newPlacedLabels.filter(p => p.isCorrect).length;
const allLabelsPlaced = placedCorrectCount >= correctLabelsCount;
```
In a multi-task game where tasks filter zone_ids/label_ids, `blueprint.labels.length` counts ALL labels across all tasks, not just the current task's labels.

**Fix:** When multiSceneState exists with tasks, count only the task's label subset:
```ts
// After line 363, replace correctLabelsCount calculation:
let correctLabelsCount = blueprint.labels.length;
// If we're in a multi-scene task, only count this task's labels
const multiScene = state.multiSceneState;
if (multiScene && state.gameSequence) {
  const scene = state.gameSequence.scenes[multiScene.currentSceneIndex];
  const task = scene?.tasks?.[multiScene.currentTaskIndex];
  if (task && task.label_ids.length > 0) {
    correctLabelsCount = task.label_ids.length;
  }
}
```

**Same bug in `checkModeTransition` (lines 794–798):**
```ts
case 'all_zones_labeled': {
  const correctPlacements = placedLabels.filter(p => p.isCorrect).length;
  const totalLabels = blueprint?.labels.length || 0;  // ALL labels
  shouldTransition = correctPlacements >= totalLabels;
```
**Fix:** Same per-task filtering logic.

**Verification:** Multi-task game: Task 1 has 3 labels, Task 2 has 4 labels. Placing 3 labels in Task 1 should mark it complete.

---

### Fix 1.4: `hasRemainingModes` arithmetic (S-7)

**File:** `useLabelDiagramState.ts`, line 368–369

**Current (broken):**
```ts
const hasRemainingModes = state.multiModeState
  && state.multiModeState.completedModes.length + 1 < state.multiModeState.availableModes.length;
```
With 3 modes [A, B, C]: After completing A (completedModes=[A]), placing last label in B:
- `completedModes.length + 1 = 2 < 3` → true (correct, C remains)
But after transitioning to C and completing it: completedModes=[A, B]:
- `completedModes.length + 1 = 3 < 3` → false (correct)

Actually the +1 accounts for current mode. But the real bug is: when in mode B with A completed:
- `completedModes.length = 1`, `+1 = 2 < 3` → true
- But this counts current mode B as "remaining" even though we're actively completing it

**Fix:** Use explicit remaining count:
```ts
const hasRemainingModes = state.multiModeState && (() => {
  const { completedModes, availableModes, currentMode } = state.multiModeState!;
  const remaining = availableModes.filter(
    m => m !== currentMode && !completedModes.includes(m)
  );
  return remaining.length > 0;
})();
```

---

### Fix 1.5: setTimeout memory leak (S-20)

**File:** `useLabelDiagramState.ts`, lines 858–860

**Bug:** `checkModeTransition` calls `setTimeout` for auto-transition but there's no cleanup. If component unmounts during the 500ms delay, the callback fires on a stale store.

**Current:**
```ts
setTimeout(() => {
  get().transitionToMode(transition.to, transition);
}, transition.animation === 'none' ? 0 : 500);
```

**Fix approach:** Store the timeout ID so it can be cleaned up. Since this is a Zustand store (not a React component), the cleanup must happen in `resetGame` and `initializeGame`.

Add to state interface (line ~137):
```ts
_transitionTimerId: ReturnType<typeof setTimeout> | null;
```

In `checkModeTransition` (line 858):
```ts
// Clear any pending transition timer
const prevTimer = get()._transitionTimerId;
if (prevTimer) clearTimeout(prevTimer);

const timerId = setTimeout(() => {
  set({ _transitionTimerId: null });
  get().transitionToMode(transition.to, transition);
}, transition.animation === 'none' ? 0 : 500);
set({ _transitionTimerId: timerId });
```

In `resetGame` (line 445) and `initializeGame` (line 310):
```ts
const prevTimer = get()._transitionTimerId;
if (prevTimer) clearTimeout(prevTimer);
```

---

### Fix 1.6: `transitionToMode` immutability violation (S-23)

**File:** `useLabelDiagramState.ts`, lines 874–878

**Bug:** Mutates `modeHistory` array in-place:
```ts
const currentModeHistory = multiModeState.modeHistory[multiModeState.modeHistory.length - 1];
if (currentModeHistory) {
  currentModeHistory.endTime = Date.now();  // MUTATION!
  currentModeHistory.score = score;          // MUTATION!
}
```

**Fix:** Create new array with updated last entry:
```ts
const updatedHistory = [...multiModeState.modeHistory];
const lastIdx = updatedHistory.length - 1;
if (lastIdx >= 0) {
  updatedHistory[lastIdx] = {
    ...updatedHistory[lastIdx],
    endTime: Date.now(),
    score,
  };
}
```
Then use `updatedHistory` in the `set()` call at line 932.

---

### Fix 1.7: Full Zustand State Integration for ALL Mechanics (IC-1 through IC-6, S-2, S-24)

**Problem:** 5 mechanics (sequencing, sorting_categories, memory_match, branching_scenario, compare_contrast) use 100% internal `useState` with ZERO Zustand integration. description_matching is partially integrated. This causes:

1. **Score invisible during play** — Store `score` stays at 0 while component calculates internally
2. **No undo/redo** — Command history can't access component's useState
3. **No persistence** — Auto-save captures nothing for these mechanics
4. **No analytics** — Event logging is blind to actions within these mechanics
5. **Mode transitions broken** — `checkModeTransition` has no triggers for sequence_complete, sorting_complete, etc.
6. **Multi-mechanic score loss** — Score overwrites on mode transition instead of accumulating

**Architecture decision: Dual-state with sync**
- Components keep internal `useState` for rendering/animation (ephemeral)
- Components call store actions at KEY MOMENTS (persistent):
  - After each meaningful state change (DnD reorder, categorization, card match)
  - On submit (validation + scoring)
  - On reset
- Store tracks the persistent/scoreable state
- Components read initial state from store on mount (for persistence restore)

This minimizes refactoring while achieving all 6 goals.

---

#### Fix 1.7a: New Types (`types.ts`)

Add after `DescriptionMatch` interface (line ~680):

```ts
// =====================================================
// PER-MECHANIC PROGRESS TYPES (Zustand-tracked)
// =====================================================

/** Sequencing mechanic progress */
export interface SequencingProgress {
  currentOrder: string[];     // Item IDs in user's current arrangement
  isSubmitted: boolean;
  correctPositions: number;
  totalPositions: number;
}

/** Sorting categories mechanic progress */
export interface SortingProgress {
  itemCategories: Record<string, string | null>;  // itemId → categoryId (null = unsorted)
  isSubmitted: boolean;
  correctCount: number;
  totalCount: number;
}

/** Memory match mechanic progress */
export interface MemoryMatchProgress {
  matchedPairIds: string[];   // IDs of successfully matched pairs
  attempts: number;           // Total flip-pair attempts
  totalPairs: number;
}

/** Branching scenario mechanic progress */
export interface BranchingProgress {
  currentNodeId: string;
  pathTaken: Array<{ nodeId: string; optionId: string; isCorrect: boolean }>;
}

/** Compare/contrast mechanic progress */
export interface CompareProgress {
  categorizations: Record<string, string>;  // zoneId → category
  isSubmitted: boolean;
  correctCount: number;
  totalCount: number;
}
```

Add new trigger types to `ModeTransitionTrigger` (line ~25):
```ts
export type ModeTransitionTrigger =
  | 'all_zones_labeled'
  | 'path_complete'
  | 'percentage_complete'
  | 'specific_zones'
  | 'time_elapsed'
  | 'user_choice'
  | 'hierarchy_level_complete'
  // NEW mechanic-specific triggers:
  | 'sequence_complete'
  | 'sorting_complete'
  | 'memory_complete'
  | 'branching_complete'
  | 'compare_complete'
  | 'description_complete';
```

---

#### Fix 1.7b: New Store State Fields (`useLabelDiagramState.ts`)

Add imports for new types (line 1):
```ts
import {
  // ... existing imports ...
  SequencingProgress,
  SortingProgress,
  MemoryMatchProgress,
  BranchingProgress,
  CompareProgress,
} from '../types';
```

Add to `LabelDiagramState` interface (after line ~127, `descriptionMatchingState`):
```ts
// Per-mechanic progress (Zustand-tracked)
sequencingProgress: SequencingProgress | null;
sortingProgress: SortingProgress | null;
memoryMatchProgress: MemoryMatchProgress | null;
branchingProgress: BranchingProgress | null;
compareProgress: CompareProgress | null;
```

Add action signatures (after `recordDescriptionMatch`, ~line 161):
```ts
// Sequencing actions
updateSequenceOrder: (itemOrder: string[]) => void;
submitSequence: () => void;

// Sorting actions
updateSortingPlacement: (itemId: string, categoryId: string | null) => void;
submitSorting: () => void;

// Memory match actions
recordMemoryMatch: (pairId: string) => void;
recordMemoryAttempt: () => void;

// Branching actions
recordBranchingChoice: (nodeId: string, optionId: string, isCorrect: boolean, nextNodeId: string | null) => void;
undoBranchingChoice: () => void;

// Compare/contrast actions
updateCompareCategorization: (zoneId: string, category: string) => void;
submitCompare: () => void;
```

Initialize defaults (after `descriptionMatchingState: null`, ~line 202):
```ts
sequencingProgress: null,
sortingProgress: null,
memoryMatchProgress: null,
branchingProgress: null,
compareProgress: null,
```

---

#### Fix 1.7c: `initializeGame` — Initialize All Mode States (lines 228–337)

After the existing trace_path/click_to_identify/hierarchical initialization blocks (~line 253), add:

```ts
let descriptionMatchingState: DescriptionMatchingState | null = null;
if (interactionMode === 'description_matching') {
  descriptionMatchingState = { currentIndex: 0, matches: [], mode: 'click_zone' };
}

let sequencingProgress: SequencingProgress | null = null;
if (interactionMode === 'sequencing' && blueprint.sequenceConfig) {
  const shuffledIds = [...blueprint.sequenceConfig.items.map(i => i.id)]
    .sort(() => Math.random() - 0.5);
  sequencingProgress = {
    currentOrder: shuffledIds,
    isSubmitted: false,
    correctPositions: 0,
    totalPositions: blueprint.sequenceConfig.correctOrder.length,
  };
}

let sortingProgress: SortingProgress | null = null;
if (interactionMode === 'sorting_categories' && blueprint.sortingConfig) {
  const initial: Record<string, string | null> = {};
  blueprint.sortingConfig.items.forEach(item => { initial[item.id] = null; });
  sortingProgress = {
    itemCategories: initial,
    isSubmitted: false,
    correctCount: 0,
    totalCount: blueprint.sortingConfig.items.length,
  };
}

let memoryMatchProgress: MemoryMatchProgress | null = null;
if (interactionMode === 'memory_match' && blueprint.memoryMatchConfig) {
  memoryMatchProgress = {
    matchedPairIds: [],
    attempts: 0,
    totalPairs: blueprint.memoryMatchConfig.pairs.length,
  };
}

let branchingProgress: BranchingProgress | null = null;
if (interactionMode === 'branching_scenario' && blueprint.branchingConfig) {
  branchingProgress = {
    currentNodeId: blueprint.branchingConfig.startNodeId,
    pathTaken: [],
  };
}

let compareProgress: CompareProgress | null = null;
if (interactionMode === 'compare_contrast' && blueprint.compareConfig) {
  compareProgress = {
    categorizations: {},
    isSubmitted: false,
    correctCount: 0,
    totalCount: Object.keys(blueprint.compareConfig.expectedCategories).length,
  };
}
```

Add ALL new fields to the `set()` call (~line 310):
```ts
set({
  // ... existing fields ...
  descriptionMatchingState,
  sequencingProgress,
  sortingProgress,
  memoryMatchProgress,
  branchingProgress,
  compareProgress,
});
```

---

#### Fix 1.7d: `transitionToMode` — Initialize Target Mode State (lines 867–943)

After the existing trace_path/click_to_identify/hierarchical initialization (~line 919), add the SAME initialization blocks as above but keyed on `newMode` instead of `interactionMode`:

```ts
let descriptionMatchingState: DescriptionMatchingState | null = null;
if (newMode === 'description_matching') {
  descriptionMatchingState = { currentIndex: 0, matches: [], mode: 'click_zone' };
}

let sequencingProgress: SequencingProgress | null = null;
if (newMode === 'sequencing' && blueprint?.sequenceConfig) {
  const shuffledIds = [...blueprint.sequenceConfig.items.map(i => i.id)]
    .sort(() => Math.random() - 0.5);
  sequencingProgress = {
    currentOrder: shuffledIds,
    isSubmitted: false,
    correctPositions: 0,
    totalPositions: blueprint.sequenceConfig.correctOrder.length,
  };
}

let sortingProgress: SortingProgress | null = null;
if (newMode === 'sorting_categories' && blueprint?.sortingConfig) {
  const initial: Record<string, string | null> = {};
  blueprint.sortingConfig.items.forEach(item => { initial[item.id] = null; });
  sortingProgress = {
    itemCategories: initial,
    isSubmitted: false,
    correctCount: 0,
    totalCount: blueprint.sortingConfig.items.length,
  };
}

let memoryMatchProgress: MemoryMatchProgress | null = null;
if (newMode === 'memory_match' && blueprint?.memoryMatchConfig) {
  memoryMatchProgress = {
    matchedPairIds: [],
    attempts: 0,
    totalPairs: blueprint.memoryMatchConfig.pairs.length,
  };
}

let branchingProgress: BranchingProgress | null = null;
if (newMode === 'branching_scenario' && blueprint?.branchingConfig) {
  branchingProgress = {
    currentNodeId: blueprint.branchingConfig.startNodeId,
    pathTaken: [],
  };
}

let compareProgress: CompareProgress | null = null;
if (newMode === 'compare_contrast' && blueprint?.compareConfig) {
  compareProgress = {
    categorizations: {},
    isSubmitted: false,
    correctCount: 0,
    totalCount: Object.keys(blueprint.compareConfig.expectedCategories).length,
  };
}
```

Add ALL to the `set()` call (~line 922):
```ts
set({
  // ... existing fields ...
  descriptionMatchingState,
  sequencingProgress,
  sortingProgress,
  memoryMatchProgress,
  branchingProgress,
  compareProgress,
});
```

---

#### Fix 1.7e: `checkModeTransition` — Add Mechanic Completion Triggers (lines 781–865)

Add new cases in the switch statement (after `time_elapsed` case, ~line 845):

```ts
case 'sequence_complete': {
  const sp = state.sequencingProgress;
  shouldTransition = sp !== null && sp.isSubmitted &&
    sp.correctPositions === sp.totalPositions;
  break;
}

case 'sorting_complete': {
  const sp = state.sortingProgress;
  shouldTransition = sp !== null && sp.isSubmitted &&
    sp.correctCount === sp.totalCount;
  break;
}

case 'memory_complete': {
  const mm = state.memoryMatchProgress;
  shouldTransition = mm !== null &&
    mm.matchedPairIds.length >= mm.totalPairs;
  break;
}

case 'branching_complete': {
  const bp = state.branchingProgress;
  if (bp && state.blueprint?.branchingConfig) {
    const currentNode = state.blueprint.branchingConfig.nodes
      .find(n => n.id === bp.currentNodeId);
    shouldTransition = currentNode?.isEndNode === true;
  }
  break;
}

case 'compare_complete': {
  const cp = state.compareProgress;
  shouldTransition = cp !== null && cp.isSubmitted &&
    cp.correctCount === cp.totalCount;
  break;
}

case 'description_complete': {
  const dm = state.descriptionMatchingState;
  if (dm && state.blueprint) {
    const totalDescriptions = state.blueprint.diagram.zones
      .filter(z => z.description).length;
    shouldTransition = dm.currentIndex >= totalDescriptions;
  }
  break;
}
```

---

#### Fix 1.7f: `completeInteraction` — Per-Mechanic maxScore (lines 489–546)

Add cases to the switch statement (after `hierarchical` case, ~line 524):

```ts
case 'sequencing': {
  const items = blueprint.sequenceConfig?.items || [];
  maxScore = items.length * pts;
  break;
}
case 'sorting_categories': {
  const sortItems = blueprint.sortingConfig?.items || [];
  maxScore = sortItems.length * pts;
  break;
}
case 'memory_match': {
  const pairs = blueprint.memoryMatchConfig?.pairs || [];
  maxScore = pairs.length * pts;
  break;
}
case 'branching_scenario': {
  const nodes = blueprint.branchingConfig?.nodes || [];
  maxScore = nodes.filter(n => !n.isEndNode).length * pts;
  break;
}
case 'compare_contrast': {
  const categories = blueprint.compareConfig?.expectedCategories || {};
  maxScore = Object.keys(categories).length * pts;
  break;
}
case 'description_matching': {
  const zonesWithDesc = blueprint.diagram.zones.filter(z => z.description);
  maxScore = zonesWithDesc.length * pts;
  break;
}
```

---

#### Fix 1.7g: New Store Action Implementations

Add after the `recordDescriptionMatch` action (~line 660):

```ts
// =============================================================================
// SEQUENCING ACTIONS
// =============================================================================

updateSequenceOrder: (itemOrder: string[]) => {
  const state = get();
  if (!state.sequencingProgress) return;
  set({
    sequencingProgress: {
      ...state.sequencingProgress,
      currentOrder: itemOrder,
    },
  });
},

submitSequence: () => {
  const state = get();
  const { sequencingProgress, blueprint, basePointsPerZone } = state;
  if (!sequencingProgress || !blueprint?.sequenceConfig) return;

  const { correctOrder } = blueprint.sequenceConfig;
  let correctPositions = 0;
  for (let i = 0; i < sequencingProgress.currentOrder.length; i++) {
    if (sequencingProgress.currentOrder[i] === correctOrder[i]) {
      correctPositions++;
    }
  }

  const scoreDelta = correctPositions * basePointsPerZone;

  set({
    sequencingProgress: {
      ...sequencingProgress,
      isSubmitted: true,
      correctPositions,
    },
    score: state.score + scoreDelta,
  });

  if (correctPositions === sequencingProgress.totalPositions) {
    get().checkModeTransition();
  }
},

// =============================================================================
// SORTING ACTIONS
// =============================================================================

updateSortingPlacement: (itemId: string, categoryId: string | null) => {
  const state = get();
  if (!state.sortingProgress) return;
  set({
    sortingProgress: {
      ...state.sortingProgress,
      itemCategories: {
        ...state.sortingProgress.itemCategories,
        [itemId]: categoryId,
      },
    },
  });
},

submitSorting: () => {
  const state = get();
  const { sortingProgress, blueprint, basePointsPerZone } = state;
  if (!sortingProgress || !blueprint?.sortingConfig) return;

  let correctCount = 0;
  for (const item of blueprint.sortingConfig.items) {
    if (sortingProgress.itemCategories[item.id] === item.correctCategoryId) {
      correctCount++;
    }
  }

  const scoreDelta = correctCount * basePointsPerZone;

  set({
    sortingProgress: {
      ...sortingProgress,
      isSubmitted: true,
      correctCount,
    },
    score: state.score + scoreDelta,
  });

  if (correctCount === sortingProgress.totalCount) {
    get().checkModeTransition();
  }
},

// =============================================================================
// MEMORY MATCH ACTIONS
// =============================================================================

recordMemoryMatch: (pairId: string) => {
  const state = get();
  if (!state.memoryMatchProgress) return;

  const newMatched = [...state.memoryMatchProgress.matchedPairIds, pairId];
  const scoreDelta = state.basePointsPerZone;

  set({
    memoryMatchProgress: {
      ...state.memoryMatchProgress,
      matchedPairIds: newMatched,
    },
    score: state.score + scoreDelta,
  });

  if (newMatched.length >= state.memoryMatchProgress.totalPairs) {
    get().checkModeTransition();
  }
},

recordMemoryAttempt: () => {
  const state = get();
  if (!state.memoryMatchProgress) return;
  set({
    memoryMatchProgress: {
      ...state.memoryMatchProgress,
      attempts: state.memoryMatchProgress.attempts + 1,
    },
  });
},

// =============================================================================
// BRANCHING ACTIONS
// =============================================================================

recordBranchingChoice: (
  nodeId: string,
  optionId: string,
  isCorrect: boolean,
  nextNodeId: string | null,
) => {
  const state = get();
  if (!state.branchingProgress) return;

  const scoreDelta = isCorrect ? state.basePointsPerZone : 0;
  const newPathTaken = [
    ...state.branchingProgress.pathTaken,
    { nodeId, optionId, isCorrect },
  ];

  set({
    branchingProgress: {
      ...state.branchingProgress,
      currentNodeId: nextNodeId || state.branchingProgress.currentNodeId,
      pathTaken: newPathTaken,
    },
    score: state.score + scoreDelta,
  });

  // End node reached
  if (nextNodeId === null) {
    get().checkModeTransition();
  }
},

undoBranchingChoice: () => {
  const state = get();
  const bp = state.branchingProgress;
  if (!bp || bp.pathTaken.length === 0) return;

  const removedStep = bp.pathTaken[bp.pathTaken.length - 1];
  const newPath = bp.pathTaken.slice(0, -1);
  const scoreDelta = removedStep.isCorrect ? -state.basePointsPerZone : 0;

  // Navigate back to the node where the removed choice was made
  const previousNodeId = removedStep.nodeId;

  set({
    branchingProgress: {
      ...bp,
      currentNodeId: previousNodeId,
      pathTaken: newPath,
    },
    score: Math.max(0, state.score + scoreDelta),
  });
},

// =============================================================================
// COMPARE/CONTRAST ACTIONS
// =============================================================================

updateCompareCategorization: (zoneId: string, category: string) => {
  const state = get();
  if (!state.compareProgress) return;
  set({
    compareProgress: {
      ...state.compareProgress,
      categorizations: {
        ...state.compareProgress.categorizations,
        [zoneId]: category,
      },
    },
  });
},

submitCompare: () => {
  const state = get();
  const { compareProgress, blueprint, basePointsPerZone } = state;
  if (!compareProgress || !blueprint?.compareConfig) return;

  let correctCount = 0;
  for (const [zoneId, expected] of Object.entries(
    blueprint.compareConfig.expectedCategories,
  )) {
    if (compareProgress.categorizations[zoneId] === expected) {
      correctCount++;
    }
  }

  const scoreDelta = correctCount * basePointsPerZone;

  set({
    compareProgress: {
      ...compareProgress,
      isSubmitted: true,
      correctCount,
    },
    score: state.score + scoreDelta,
  });

  if (correctCount === compareProgress.totalCount) {
    get().checkModeTransition();
  }
},
```

---

#### Fix 1.7h: Component Refactoring — Per-Component Wiring

Each component gets two-way sync with the store. Components keep internal `useState` for animation/visual state, but call store actions at key moments.

**Pattern for each component:**
1. Accept new optional props: `storeProgress`, `onStoreUpdate`, etc.
2. On mount: if `storeProgress` exists, use it to seed initial state (persistence restore)
3. On each meaningful change: call store action
4. On submit: call store submit action (which scores and triggers transitions)
5. On reset: call store action to re-initialize

---

**SequenceBuilder.tsx** (308 lines) — Changes:

New props:
```ts
export interface SequenceBuilderProps {
  // ... existing props
  storeProgress?: SequencingProgress | null;
  onOrderChange?: (itemOrder: string[]) => void;  // Store sync
  onStoreSubmit?: () => void;                      // Store submit
}
```

Changes:
- `useState<SequenceItem[]>` init (L140): If `storeProgress?.currentOrder` exists, use it to order items instead of random shuffle. This enables persistence restore.
- `handleDragEnd` (L154): After `setItems(...)`, call `onOrderChange?.(newOrder)` to sync to store.
- `handleSubmit` (L169): After existing logic, call `onStoreSubmit?.()` to trigger store scoring + mode transition.
- `handleReset` (L202): No store action needed (store re-init happens via `resetGame`).

**In `index.tsx`** (sequencing case, L832):
```ts
case 'sequencing': {
  const sequenceConfig = bp.sequenceConfig;
  if (sequenceConfig && sequenceConfig.items.length > 0) {
    return (
      <SequenceBuilder
        items={sequenceConfig.items.map((item, idx) => ({
          id: item.id, text: item.text, orderIndex: idx, description: item.description,
        }))}
        correctOrder={sequenceConfig.correctOrder}
        allowPartialCredit={sequenceConfig.allowPartialCredit ?? true}
        storeProgress={sequencingProgress}
        onOrderChange={updateSequenceOrder}
        onStoreSubmit={submitSequence}
        onComplete={(result) => { completeInteraction(); }}
      />
    );
  }
  // ... fallback
}
```

---

**SortingCategories.tsx** (395 lines) — Changes:

New props:
```ts
export interface SortingCategoriesProps {
  // ... existing props
  storeProgress?: SortingProgress | null;
  onPlacementChange?: (itemId: string, categoryId: string | null) => void;
  onStoreSubmit?: () => void;
}
```

Changes:
- `useState<Record<string, string | null>>` init (L166): If `storeProgress?.itemCategories` exists, use it. Enables persistence.
- `handleDragEnd` (L197): After `setItemCategories(...)`, call `onPlacementChange?.(itemId, categoryId)`.
- `handleSubmit` (L229): After existing logic, call `onStoreSubmit?.()`.

**In `index.tsx`** (sorting_categories case, L1017):
```ts
return (
  <SortingCategories
    items={config.items}
    categories={config.categories}
    storeProgress={sortingProgress}
    onPlacementChange={updateSortingPlacement}
    onStoreSubmit={submitSorting}
    onComplete={(result) => { completeInteraction(); }}
    allowPartialCredit={config.allowPartialCredit ?? true}
    showCategoryHints={config.showCategoryHints ?? true}
    instructions={config.instructions}
  />
);
```

---

**MemoryMatch.tsx** (302 lines) — Changes:

New props:
```ts
export interface MemoryMatchProps {
  // ... existing props
  storeProgress?: MemoryMatchProgress | null;
  onPairMatched?: (pairId: string) => void;
  onAttemptMade?: () => void;
}
```

Changes:
- `useState(0)` for matchedCount (L86): If `storeProgress?.matchedPairIds.length` > 0, seed from it. Mark those pairs as matched in card state.
- Match found effect (L103–114): After `setMatchedCount(...)`, call `onPairMatched?.(firstCard.pairId)`.
- 2-card flip effect (L96): After `setAttempts(...)`, call `onAttemptMade?.()`.

**In `index.tsx`** (memory_match case, L1041):
```ts
return (
  <MemoryMatch
    pairs={config.pairs}
    gridSize={config.gridSize}
    flipDurationMs={config.flipDurationMs}
    showAttemptsCounter={config.showAttemptsCounter ?? true}
    storeProgress={memoryMatchProgress}
    onPairMatched={recordMemoryMatch}
    onAttemptMade={recordMemoryAttempt}
    onComplete={(result) => { completeInteraction(); }}
    instructions={config.instructions}
  />
);
```

---

**BranchingScenario.tsx** (352 lines) — Changes:

New props:
```ts
export interface BranchingScenarioProps {
  // ... existing props
  storeProgress?: BranchingProgress | null;
  onChoiceMade?: (nodeId: string, optionId: string, isCorrect: boolean, nextNodeId: string | null) => void;
  onUndo?: () => void;
}
```

Changes:
- `useState(startNodeId)` for currentNodeId (L75): If `storeProgress?.currentNodeId`, use it. Seed `pathTaken` from `storeProgress?.pathTaken`.
- `handleConfirm` (L88): After adding to pathTaken, call `onChoiceMade?.(currentNodeId, selectedOption, isCorrect, nextNodeId)`.
- `handleBacktrack` (L143): After removing from pathTaken, call `onUndo?.()`.

**In `index.tsx`** (branching_scenario case, L1064):
```ts
return (
  <BranchingScenario
    nodes={config.nodes}
    startNodeId={config.startNodeId}
    showPathTaken={config.showPathTaken ?? true}
    allowBacktrack={config.allowBacktrack ?? true}
    showConsequences={config.showConsequences ?? true}
    multipleValidEndings={config.multipleValidEndings ?? false}
    storeProgress={branchingProgress}
    onChoiceMade={recordBranchingChoice}
    onUndo={undoBranchingChoice}
    onComplete={(result) => { completeInteraction(); }}
    instructions={config.instructions}
  />
);
```

---

**CompareContrast.tsx** (293 lines) — Changes:

New props:
```ts
export interface CompareContrastProps {
  // ... existing props
  storeProgress?: CompareProgress | null;
  onCategorizationChange?: (zoneId: string, category: string) => void;
  onStoreSubmit?: () => void;
}
```

Changes:
- `useState<Record<string, string>>` init (L69): If `storeProgress?.categorizations`, use it.
- `handleCategorySelect` (L85): After `setCategorizations(...)`, call `onCategorizationChange?.(selectedZone, category)`.
- `handleSubmit` (L98): After existing logic, call `onStoreSubmit?.()`.

**In `index.tsx`** (compare_contrast case, L875):
```ts
return (
  <CompareContrast
    diagramA={compareConfig.diagramA}
    diagramB={compareConfig.diagramB}
    expectedCategories={compareConfig.expectedCategories}
    highlightMatching={compareConfig.highlightMatching ?? true}
    instructions={compareConfig.instructions}
    storeProgress={compareProgress}
    onCategorizationChange={updateCompareCategorization}
    onStoreSubmit={submitCompare}
    onComplete={(result) => { completeInteraction(); }}
  />
);
```

---

**DescriptionMatcher.tsx** (481 lines) — Changes:

Already partially integrated via `recordDescriptionMatch`. The `drag_description` mode has separate internal state (`matchedPairs`, `matches`) that bypasses Zustand. Fix: wire `drag_description` mode to also call `recordDescriptionMatch` consistently.

---

#### Fix 1.7 Verification

After all Fix 1.7 changes:
1. `cd frontend && npx tsc --noEmit` — TypeScript compilation
2. Play a sequencing game → verify score updates in real-time in store
3. Play a multi-mechanic game (drag_drop → sequencing) → verify score accumulates
4. Verify `checkModeTransition` fires `sequence_complete` trigger after sequencing
5. Play memory_match → verify matched pairs tracked in store
6. Check console: no "null progress" errors when transitioning to any mode

---

### Fix 1.8: `advanceToNextTask` scoring (S-27)

**File:** `useLabelDiagramState.ts`, lines 1023–1029

**Bug:**
```ts
const taskResult: TaskResult = {
  task_id: currentTask?.task_id || `task_${currentTaskIdx}`,
  score,
  max_score: placedLabels.filter(p => p.isCorrect).length * (get().basePointsPerZone || 10),
  // ^^^ BUG: max_score = actual score, so percentage is always 100%
  completed: true,
  matches: placedLabels.map(p => ({ ...p })),
};
```

**Fix:** Use the blueprint's maxScore or task-specific maxScore:
```ts
const taskResult: TaskResult = {
  task_id: currentTask?.task_id || `task_${currentTaskIdx}`,
  score,
  max_score: get().maxScore,  // Use the maxScore calculated during initializeGame
  completed: true,
  matches: placedLabels.map(p => ({ ...p })),
};
```

---

### Fix 1.9: `handleDescriptionMatch` — wrong comparison (IC-9)

**File:** `index.tsx`, lines 757–764

**Bug:**
```ts
const handleDescriptionMatch = useCallback(
  (labelId: string, zoneId: string) => {
    const zone = normalizedBlueprint.diagram.zones.find((z) => z.id === zoneId);
    const isCorrect = zone ? zone.id === labelId : false;  // BUG: zone.id !== labelId (different namespaces)
    recordDescriptionMatch({ labelId, zoneId, isCorrect });
  },
```

**Fix:** Check if the label's correctZoneId matches the zoneId:
```ts
const handleDescriptionMatch = useCallback(
  (labelId: string, zoneId: string) => {
    const label = normalizedBlueprint.labels.find((l) => l.id === labelId);
    const isCorrect = label ? label.correctZoneId === zoneId : false;
    recordDescriptionMatch({ labelId, zoneId, isCorrect });
  },
  [normalizedBlueprint.labels, recordDescriptionMatch]
);
```

---

### ~~Fix 1.10~~ — MERGED INTO Fix 1.7

All mode initialization is now covered comprehensively in Fix 1.7c (initializeGame) and Fix 1.7d (transitionToMode). Every mechanic gets proper Zustand state initialization.

---

### Fix 1.11: `resetGame` — Clear all new progress states

**File:** `useLabelDiagramState.ts`, `resetGame` action (~line 445)

**Bug:** `resetGame` only clears drag_drop fields (placedLabels, availableLabels, score, etc.) and the existing mode states (pathProgress, identificationProgress, hierarchyState, descriptionMatchingState). After Fix 1.7b adds 5 new progress states, they will NOT be reset.

**Fix:** Add to `resetGame`:
```ts
resetGame: () => {
    const prevTimer = get()._transitionTimerId;
    if (prevTimer) clearTimeout(prevTimer);
    set({
      // ... existing resets ...
      // NEW: Clear all mechanic progress states
      sequencingProgress: null,
      sortingProgress: null,
      memoryMatchProgress: null,
      branchingProgress: null,
      compareProgress: null,
      _transitionTimerId: null,
    });
},
```

---

### Fix 1.12: `renderInteractionContent` — Destructure new store actions

**File:** `index.tsx`, lines 286–328

**Bug:** The store destructuring in `LabelDiagramGameInner` only includes existing actions. After Fix 1.7g adds 12 new actions, they need to be destructured for use in `renderInteractionContent`.

**Fix:** Add to store destructuring:
```ts
const {
  // ... existing ...
  // NEW mechanic actions
  sequencingProgress,
  sortingProgress,
  memoryMatchProgress,
  branchingProgress,
  compareProgress,
  updateSequenceOrder,
  submitSequence,
  updateSortingPlacement,
  submitSorting,
  recordMemoryMatch,
  recordMemoryAttempt,
  recordBranchingChoice,
  undoBranchingChoice,
  updateCompareCategorization,
  submitCompare,
} = useLabelDiagramState();
```

And update `renderInteractionContent` cases (Fix 1.7h) to pass these to components.

---

### Phase 1 Verification

After all Phase 1 fixes:
1. `cd frontend && npx tsc --noEmit` — TypeScript compilation
2. Play a drag_drop game → verify undo removes child zones
3. Play a multi-mechanic game (drag_drop → sequencing) → verify score accumulates across mechanics
4. Play a multi-task game → verify per-task completion
5. Play each mechanic individually → verify score updates in real-time (not just on completion)
6. Verify mode transitions fire for: sequence_complete, sorting_complete, memory_complete, branching_complete, compare_complete
7. Check no console errors or null progress states for any mechanic
8. Verify `resetGame` clears all mechanic progress states (not just drag_drop)

### Phase 1 Summary

| Fix | Description | Files | Lines (est) |
|-----|-------------|-------|-------------|
| 1.1 | removeLabel completedZoneIds | useLabelDiagramState.ts | ~10 |
| 1.2 | Score accumulation (3 actions) | useLabelDiagramState.ts | ~30 |
| 1.3 | Per-mode label counting | useLabelDiagramState.ts | ~15 |
| 1.4 | hasRemainingModes arithmetic | useLabelDiagramState.ts | ~8 |
| 1.5 | setTimeout memory leak | useLabelDiagramState.ts | ~12 |
| 1.6 | transitionToMode immutability | useLabelDiagramState.ts | ~8 |
| 1.7a | New types | types.ts | ~50 |
| 1.7b | New store state fields | useLabelDiagramState.ts | ~30 |
| 1.7c | initializeGame all modes | useLabelDiagramState.ts | ~60 |
| 1.7d | transitionToMode all modes | useLabelDiagramState.ts | ~60 |
| 1.7e | checkModeTransition triggers | useLabelDiagramState.ts | ~50 |
| 1.7f | completeInteraction maxScore | useLabelDiagramState.ts | ~30 |
| 1.7g | 12 new store actions | useLabelDiagramState.ts | ~230 |
| 1.7h | Component refactoring (6 components + index.tsx) | 7 files | ~120 |
| 1.8 | advanceToNextTask scoring | useLabelDiagramState.ts | ~5 |
| 1.9 | handleDescriptionMatch comparison | index.tsx | ~5 |
| 1.11 | resetGame clear all states | useLabelDiagramState.ts | ~8 |
| 1.12 | Destructure new actions | index.tsx | ~15 |
| **Total** | | **~9 files** | **~746 lines** |

---

## Phase 2: Backend — Full Mechanic Pipeline (All 12 V3 Agents)

### Root Cause Analysis

**Why only drag_drop works end-to-end:**

drag_drop's config consists of generic booleans (`shuffle_labels`, `show_hints`, `max_attempts`) that don't require per-scene content data. Every other mechanic requires **content-dependent data** generated per scene:
- trace_path: ordered waypoints mapped to spatial coordinates
- click_to_identify: identification prompts per zone
- sequencing: items in correct order with descriptions
- description_matching: functional descriptions per zone
- sorting_categories: categories + items + correct assignments
- memory_match: card pairs + grid config
- branching_scenario: decision tree nodes + edges
- compare_contrast: expected categorizations per zone

**No agent in the current V3 pipeline generates this data.** The schemas exist (GameDesignV3 has PathDesign, ClickDesign, SequenceDesign, etc.) but no agent populates them. The pipeline is architecturally sound but content-empty for 9 of 10 mechanics.

### Agent-by-Agent Gap Summary

| Agent | Current Status | Per-Mechanic Support | Critical Gap |
|-------|---------------|---------------------|--------------|
| domain_knowledge_retriever | Retrieves labels + partial sequence data | 2 of 9 (sequence, trace_path via flow data) | No descriptions, comparisons, categories |
| game_designer_v3 | Outputs GameDesignV3Slim (type-only) | 0 of 9 (no configs produced) | Slim schema has no mechanic configs |
| design_validator | Has mechanic checks (L109-164) | 9 of 9 (checks exist) | Schema mismatch: expects GameDesignV3, gets Slim → checks never fire |
| scene_architect_v3 | Prompt has mechanic guidelines (L66-74) | LLM-dependent (unreliable) | get_mechanic_config_schema returns static defaults, not populated data |
| scene_validator | Delegates to validate_scene_specs() | 9 of 9 (F3 checks exist) | Catches missing data but LLM can't fix it on retry (no generation tools) |
| interaction_designer_v3 | Produces scoring + feedback | 0 of 9 (no mechanic content) | No tool generates prompts, descriptions, sequences |
| interaction_validator | Has MECHANIC_TRIGGER_MAP | Validates triggers only | No content validation |
| asset_generator_v3 | Generates diagram images + zones | 0 of 9 (zones only) | 100% mechanic-agnostic, no waypoints/items/descriptions |
| blueprint_assembler_v3 | Flattens all configs to Dict[str,Any] | 0 of 9 (loses typed structure) | Frontend expects root-level sequenceConfig, sortingConfig, etc. |

### Fix Ordering Strategy

Fixes follow the pipeline flow (upstream first → downstream). Each fix enables the next:
1. DK retriever provides richer data → game designer can make informed decisions
2. Game designer produces full configs → scene architect can validate and enrich
3. Scene architect generates spatial data → interaction designer adds behavioral content
4. All configs flow through → blueprint assembler maps them to frontend format

---

### Fix 2.1: V3 Context — Expose mechanic-relevant state fields

**File:** `backend/app/tools/v3_context.py`, lines 27-43

**Current:** Context exposes `domain_knowledge` as opaque dict. Mechanic-relevant fields (sequence_flow_data, content_characteristics, hierarchical_relationships) are buried inside and inaccessible to tools.

**Fix:** Add explicit fields:
```python
def set_v3_tool_context(state: Dict[str, Any]) -> None:
    dk = state.get("domain_knowledge", {})
    if isinstance(dk, str):
        dk = {}
    _v3_context.set({
        # ... existing fields ...
        "domain_knowledge": dk,
        # NEW: Promote mechanic-relevant DK fields to top level
        "sequence_flow_data": dk.get("sequence_flow_data") if isinstance(dk, dict) else None,
        "content_characteristics": dk.get("content_characteristics") if isinstance(dk, dict) else None,
        "hierarchical_relationships": dk.get("hierarchical_relationships") if isinstance(dk, dict) else None,
    })
```

**Files:** `v3_context.py` (3 new lines)

---

### Fix 2.2: Domain Knowledge Retriever — Add per-mechanic data retrieval

**File:** `backend/app/agents/domain_knowledge_retriever.py`

**Current:** Only retrieves canonical_labels + sequence_flow_data (if "order/sequence/trace" keywords detected). Misses 5+ mechanic data types.

**Gap analysis:**

| Mechanic | Needed DK Data | Currently Retrieved | Fix |
|----------|---------------|-------------------|-----|
| trace_path | Waypoint order, path type | sequence_flow_data (partial) | Reuse flow data, add path_type mapping |
| click_to_identify | Zone functional roles | canonical_labels only | No new retrieval needed — game_designer generates prompts from labels |
| sequencing | Items, correct order | sequence_flow_data ✓ | Already works via game_planner |
| description_matching | Functional descriptions per label | **MISSING** | Add `_search_for_descriptions()` |
| sorting_categories | Categories, item assignments | **MISSING** | Add `_search_for_categories()` |
| memory_match | Matching term pairs | **MISSING** | Derive from labels + descriptions at game_designer level |
| branching_scenario | Decision nodes, consequences | sequence_flow_data.connects_to (partial) | Enhance branching extraction |
| compare_contrast | Comparison dimensions | content_characteristics.needs_comparison flag only | Add `_search_for_comparisons()` |

**New functions (add after `_search_for_sequence`, ~line 205):**

```python
async def _search_for_descriptions(
    question: str,
    labels: List[str],
    subject: str,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> Optional[List[Dict[str, str]]]:
    """Search for functional descriptions of each label.
    Returns: [{label: str, description: str}, ...]
    """
    # LLM call: "For each label, provide a functional description
    # (what it does/is, not just its name)"
    ...

async def _search_for_categories(
    question: str,
    labels: List[str],
    subject: str,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> Optional[Dict[str, Any]]:
    """Search for sorting categories for the given labels.
    Returns: {categories: [{id, name}], assignments: {label: category_id}}
    """
    ...
```

**Trigger logic (in main retrieval function, ~line 460):**
```python
# Existing:
if content_characteristics.get("needs_sequence"):
    sequence_flow_data = await _search_for_sequence(...)

# NEW:
if content_characteristics.get("needs_comparison"):
    comparison_data = await _search_for_comparisons(...)

# Always attempt description retrieval (useful for description_matching AND general quality)
label_descriptions = await _search_for_descriptions(
    question, canonical_labels, subject, ctx
)
```

**State return (add to domain_knowledge dict):**
```python
"domain_knowledge": {
    **knowledge,
    "sequence_flow_data": sequence_flow_data,
    "content_characteristics": content_characteristics,
    "label_descriptions": label_descriptions,      # NEW
    "comparison_data": comparison_data,             # NEW
}
```

**Files:** `domain_knowledge_retriever.py` (~60 new lines), `schemas/domain_knowledge.py` (2 new models)

---

### Fix 2.3: Game Designer V3 — Output full mechanic configs (not Slim)

**Files:**
- `backend/app/agents/game_designer_v3.py`
- `backend/app/tools/game_design_v3_tools.py`
- `backend/app/agents/schemas/game_design_v3.py`

**Current:** game_designer_v3 outputs `GameDesignV3Slim` which has `SlimMechanicRef` with ONLY `type: str` (no configs). The full `GameDesignV3` schema has `MechanicDesign` with typed config fields (PathDesign, ClickDesign, SequenceDesign, etc.) but nobody populates them.

**Root cause:** `submit_game_design` tool (game_design_v3_tools.py) validates against `GameDesignV3Slim`, not `GameDesignV3`. The LLM was never asked to produce configs.

**Fix approach:** Enhance the game designer to produce mechanic configs using domain knowledge:

**(a) Update system prompt** (`game_designer_v3.py`, L35-86):

Add after existing guidelines (~L75):
```
## Mechanic Configuration Requirements

For each mechanic in each scene, you MUST populate the appropriate config:
- drag_drop: config = {shuffle_labels: true, show_hints: true, max_attempts: 3}
- click_to_identify: config = {prompts: ["Click on the X", ...], selection_mode: "sequential"}
- trace_path: config = {waypoints: [...ordered label texts...], path_type: "linear"|"cyclic"|"branching"}
- sequencing: config = {items: [{id, text, description}], correct_order: [...ids...]}
- description_matching: config = {descriptions: [{zone_label, description}], mode: "click_zone"|"drag_description"}
- sorting_categories: config = {categories: [{id, name}], items: [{id, text, correct_category}]}
- memory_match: config = {pairs: [{front, back}], grid_size: 4}
- branching_scenario: config = {nodes: [{id, prompt, options: [{id, text, isCorrect, nextNodeId}]}], start_node_id: "..."}
- compare_contrast: config = {expected_categories: {zone_id: "similar"|"different"|"unique_a"|"unique_b"}}

Use domain knowledge (labels, sequences, descriptions) to populate these accurately.
```

**(b) Update submit_game_design tool** (`game_design_v3_tools.py`):

Change validation from `GameDesignV3Slim` to `GameDesignV3` (the full schema). The full schema already has coercion validators that will handle LLM output variations.

```python
# In submit_game_design_impl:
# OLD: validated = GameDesignV3Slim.model_validate(design_data)
# NEW:
from app.agents.schemas.game_design_v3 import GameDesignV3
validated = GameDesignV3.model_validate(design_data)
```

**(c) Inject DK data into task prompt** (`game_designer_v3.py`, `build_task_prompt()`, ~L129):

After canonical_labels section, add:
```python
dk = state.get("domain_knowledge", {})
if isinstance(dk, dict):
    seq_data = dk.get("sequence_flow_data")
    if seq_data:
        sections.append(f"## Sequence/Flow Data\n{json.dumps(seq_data, indent=2)[:1000]}")

    label_descs = dk.get("label_descriptions")
    if label_descs:
        sections.append(f"## Label Descriptions\n{json.dumps(label_descs, indent=2)[:1000]}")

    comparison = dk.get("comparison_data")
    if comparison:
        sections.append(f"## Comparison Data\n{json.dumps(comparison, indent=2)[:1000]}")
```

**Files:** `game_designer_v3.py` (~25 new lines), `game_design_v3_tools.py` (~5 changed lines)

---

### Fix 2.4: Design Validator — Fix schema mismatch

**File:** `backend/app/agents/design_validator.py`

**Current:** Has mechanic-specific validation (L109-164) that checks for PathDesign, ClickDesign, SequenceDesign, etc. BUT it validates against `GameDesignV3` while receiving output from game_designer_v3 which outputs `GameDesignV3Slim`. The mechanic config checks (L128-164) NEVER FIRE because Slim has no config fields.

**Fix:** After Fix 2.3, game_designer_v3 will output full `GameDesignV3` configs. The validator already handles this correctly — **no code changes needed** once Fix 2.3 is applied. The existing validation at L109-164 will start working automatically.

**Verification:** After Fix 2.3, run a pipeline with trace_path → design_validator should check `path_config.waypoints` presence (L133-137).

---

### Fix 2.5: Scene Architect V3 — Add mechanic content generation tool

**Files:**
- `backend/app/agents/scene_architect_v3.py`
- `backend/app/tools/scene_architect_tools.py`

**Current:** Has 4 tools. `get_mechanic_config_schema` returns static defaults from `INTERACTION_PATTERNS` (booleans/strings), NOT populated instances with actual waypoints/prompts/items.

**The LLM is told to produce mechanic configs (system prompt L66-74)** but has no tool to generate content data. It must hallucinate waypoints, prompts, etc. from thin air.

**Fix approach:** Add a new tool that generates mechanic content from game design + domain knowledge:

**(a) New tool: `generate_mechanic_content`** (add to `scene_architect_tools.py`):

```python
async def generate_mechanic_content_impl(
    mechanic_type: str,
    scene_number: int,
    zone_labels: List[str],
) -> Dict[str, Any]:
    """
    Generate populated mechanic config content for a scene.

    Uses game_design_v3 mechanic configs + domain_knowledge to produce
    the actual content data (waypoints, prompts, items, descriptions, etc.)
    that scene_spec MechanicConfigV3 requires.
    """
    ctx = get_v3_tool_context()
    game_design = ctx.get("game_design_v3") or {}
    dk = ctx.get("domain_knowledge") or {}
    seq_data = ctx.get("sequence_flow_data")

    # Find the mechanic config from game_design for this scene
    scenes = game_design.get("scenes", [])
    scene = next((s for s in scenes if s.get("scene_number") == scene_number), None)
    if not scene:
        return {"error": f"Scene {scene_number} not found in game_design_v3"}

    existing_config = None
    for mech in scene.get("mechanics", []):
        if mech.get("type") == mechanic_type:
            # Extract typed config (path_config, click_config, etc.)
            for key in ("path_config", "click_config", "sequence_config",
                        "sorting_config", "branching_config", "compare_config",
                        "memory_config", "description_match_config", "config"):
                cfg = mech.get(key)
                if cfg:
                    existing_config = cfg if isinstance(cfg, dict) else cfg
                    break
            break

    if mechanic_type == "trace_path":
        # Use sequence_flow_data if available, else use game_design waypoints
        waypoints = []
        if existing_config and existing_config.get("waypoints"):
            waypoints = existing_config["waypoints"]
        elif seq_data and seq_data.get("sequence_items"):
            waypoints = [item.get("text", "") for item in
                        sorted(seq_data["sequence_items"],
                               key=lambda x: x.get("order_index", 0))]
        return {
            "mechanic_type": mechanic_type,
            "config": {
                "waypoints": waypoints or zone_labels,  # fallback to zone_labels in order
                "path_type": (seq_data or {}).get("flow_type", "linear"),
                "drawing_mode": "click_waypoints",
            }
        }

    elif mechanic_type == "click_to_identify":
        prompts = []
        if existing_config and existing_config.get("prompts"):
            prompts = existing_config["prompts"]
        else:
            # Generate prompts from zone labels
            prompts = [f"Click on the {label}" for label in zone_labels]
        return {
            "mechanic_type": mechanic_type,
            "config": {
                "prompts": prompts,
                "selection_mode": "sequential",
                "highlight_on_hover": True,
            }
        }

    elif mechanic_type == "sequencing":
        items = []
        correct_order = []
        if existing_config:
            items = existing_config.get("items", [])
            correct_order = existing_config.get("correct_order", [])
        if not items and seq_data and seq_data.get("sequence_items"):
            si = sorted(seq_data["sequence_items"], key=lambda x: x.get("order_index", 0))
            items = [{"id": item.get("id", f"item_{i}"), "text": item.get("text", ""),
                      "description": item.get("description", "")} for i, item in enumerate(si)]
            correct_order = [item["id"] for item in items]
        return {
            "mechanic_type": mechanic_type,
            "config": {
                "items": items,
                "correct_order": correct_order,
                "sequence_type": (seq_data or {}).get("flow_type", "linear"),
            }
        }

    elif mechanic_type == "description_matching":
        descriptions = []
        if existing_config and existing_config.get("descriptions"):
            descriptions = existing_config["descriptions"]
        else:
            label_descs = dk.get("label_descriptions", []) if isinstance(dk, dict) else []
            if label_descs:
                descriptions = [{"zone_label": d.get("label", ""), "description": d.get("description", "")}
                               for d in label_descs]
            else:
                descriptions = [{"zone_label": lbl, "description": f"Function of {lbl}"}
                               for lbl in zone_labels]
        return {
            "mechanic_type": mechanic_type,
            "config": {
                "descriptions": descriptions,
                "mode": "click_zone",
            }
        }

    elif mechanic_type == "sorting_categories":
        return {
            "mechanic_type": mechanic_type,
            "config": existing_config or {
                "categories": [],
                "items": [],
                "show_category_hints": True,
            }
        }

    elif mechanic_type == "memory_match":
        return {
            "mechanic_type": mechanic_type,
            "config": existing_config or {
                "pairs": [{"front": lbl, "back": f"Definition of {lbl}"} for lbl in zone_labels[:8]],
                "grid_size": min(4, len(zone_labels)),
            }
        }

    elif mechanic_type == "branching_scenario":
        return {
            "mechanic_type": mechanic_type,
            "config": existing_config or {"nodes": [], "start_node_id": ""},
        }

    elif mechanic_type == "compare_contrast":
        return {
            "mechanic_type": mechanic_type,
            "config": existing_config or {"expected_categories": {}, "highlight_matching": True},
        }

    # Fallback: drag_drop or unknown
    return {
        "mechanic_type": mechanic_type,
        "config": existing_config or {"shuffle_labels": True, "show_hints": True, "max_attempts": 3},
    }
```

**(b) Register tool** in `scene_architect_tools.py` `register_scene_architect_v3_tools()`:
```python
tools.append(StructuredTool.from_function(
    func=generate_mechanic_content_impl,
    name="generate_mechanic_content",
    description="Generate populated mechanic config content (waypoints, prompts, items, descriptions) for a specific mechanic type in a scene. Call this for EACH non-drag_drop mechanic.",
))
```

**(c) Update system prompt** (`scene_architect_v3.py`, ~L75):
```
## Tool Usage Strategy

For each scene with non-drag_drop mechanics:
1. Call get_zone_layout_guidance for spatial layout
2. Call get_mechanic_config_schema for the config template
3. Call generate_mechanic_content to get populated config with actual content
4. Include the generated config in the MechanicConfigV3.config field
5. Call validate_scene_spec before submit
```

**(d) Update get_tool_names()** to include new tool.

**Files:** `scene_architect_tools.py` (~120 new lines), `scene_architect_v3.py` (~15 changed lines)

---

### Fix 2.6: Scene Validator — No changes needed

**File:** `backend/app/agents/scene_validator.py`

**Current:** Delegates to `validate_scene_specs()` in `schemas/scene_spec_v3.py`. That function already has F3 mechanic-specific checks (L270-329):
- trace_path needs path_config with waypoints
- click_to_identify needs click_config with prompts or click_options
- sequencing needs sequence_config with correct_order
- description_matching needs description_match_config with descriptions

These checks will now CATCH missing data (previously they caught it but LLM couldn't fix it on retry). With Fix 2.5 providing `generate_mechanic_content`, the LLM can now populate missing configs on retry.

**No code changes needed.**

---

### Fix 2.7: Interaction Designer V3 — Add mechanic content enrichment tool

**Files:**
- `backend/app/agents/interaction_designer_v3.py`
- `backend/app/tools/interaction_designer_tools.py`

**Current:** Has 4 tools (get_scoring_templates, generate_misconception_feedback, validate_interactions, submit_interaction_specs). Produces scoring + feedback per mechanic but NO mechanic content (prompts, descriptions, sequences).

**The interaction_designer is the RIGHT place for behavioral content** (prompt text, description wording, pedagogical sequencing of items). Scene_architect handles spatial structure; interaction_designer handles behavioral content.

**New tool: `enrich_mechanic_content`** (add to `interaction_designer_tools.py`):

```python
async def enrich_mechanic_content_impl(
    mechanic_type: str,
    scene_number: int,
) -> Dict[str, Any]:
    """
    Enrich mechanic content with pedagogically sound behavioral details.

    Uses scene_specs_v3 mechanic configs + domain knowledge to add:
    - click_to_identify: pedagogical prompt ordering (easy→hard)
    - trace_path: step-by-step waypoint descriptions for learning
    - sequencing: per-step educational explanations
    - description_matching: rich functional descriptions (not just names)

    Returns enriched content to include in interaction_specs_v3.
    """
    ctx = get_v3_tool_context()
    scene_specs = ctx.get("scene_specs_v3") or []
    dk = ctx.get("domain_knowledge") or {}

    # Find scene spec
    scene_spec = None
    for ss in scene_specs:
        if isinstance(ss, dict) and ss.get("scene_number") == scene_number:
            scene_spec = ss
            break

    if not scene_spec:
        return {"error": f"Scene {scene_number} not found in scene_specs_v3"}

    # Find mechanic config for this type
    mechanic_config = None
    for mc in scene_spec.get("mechanic_configs", []):
        if isinstance(mc, dict) and mc.get("type") == mechanic_type:
            mechanic_config = mc
            break

    # Use LLM to enrich content based on mechanic type
    llm = LLMService()
    subject = ctx.get("subject", "")
    question = ctx.get("question", "")

    if mechanic_type == "click_to_identify":
        zone_labels = mechanic_config.get("zone_labels_used", []) if mechanic_config else []
        existing_prompts = (mechanic_config or {}).get("config", {}).get("prompts", [])
        if not existing_prompts:
            existing_prompts = [f"Click on the {lbl}" for lbl in zone_labels]

        prompt = f"""Given these identification prompts for a {subject} diagram:
{json.dumps(existing_prompts)}

Reorder them from easiest to hardest for a student learning about: {question}
Also improve the wording to be pedagogically clear.
Return JSON: {{"ordered_prompts": ["...", ...]}}"""

        result = await llm.generate_json(prompt=prompt, model="gemini-2.0-flash")
        return {
            "mechanic_type": mechanic_type,
            "enriched_content": {
                "identification_prompts": result.get("ordered_prompts", existing_prompts),
            }
        }

    elif mechanic_type == "description_matching":
        zone_labels = mechanic_config.get("zone_labels_used", []) if mechanic_config else []
        descriptions = (mechanic_config or {}).get("config", {}).get("descriptions", [])

        if not descriptions or all(d.get("description", "").startswith("Function of") for d in descriptions):
            prompt = f"""For a {subject} educational diagram about: {question}

Generate a functional description for each of these parts:
{json.dumps(zone_labels)}

Each description should explain WHAT the part DOES (not what it IS).
Return JSON: {{"descriptions": [{{"zone_label": "...", "description": "..."}}]}}"""

            result = await llm.generate_json(prompt=prompt, model="gemini-2.0-flash")
            descriptions = result.get("descriptions", descriptions)

        return {
            "mechanic_type": mechanic_type,
            "enriched_content": {
                "descriptions": descriptions,
            }
        }

    elif mechanic_type == "sequencing":
        items = (mechanic_config or {}).get("config", {}).get("items", [])
        if items:
            prompt = f"""For a {subject} educational sequence about: {question}

These steps have been identified:
{json.dumps(items)}

Add a brief educational explanation for each step (why this step matters).
Return JSON: {{"items": [{{"id": "...", "text": "...", "description": "educational explanation"}}]}}"""

            result = await llm.generate_json(prompt=prompt, model="gemini-2.0-flash")
            items = result.get("items", items)

        return {
            "mechanic_type": mechanic_type,
            "enriched_content": {"items": items},
        }

    return {"mechanic_type": mechanic_type, "enriched_content": {}}
```

**Register in tools file + update interaction_designer_v3 system prompt** to call this tool for non-drag_drop mechanics.

**Also update `submit_interaction_specs`** to include enriched_content in the output so blueprint_assembler can access it.

**Files:** `interaction_designer_tools.py` (~100 new lines), `interaction_designer_v3.py` (~10 changed lines)

---

### Fix 2.8: Interaction Validator — Enhance content validation

**File:** `backend/app/agents/schemas/interaction_spec_v3.py`

**Current:** `validate_interaction_specs()` has MECHANIC_TRIGGER_MAP for trigger validation. But no content validation (doesn't check if enriched content was actually produced).

**Fix:** Add content presence checks after existing trigger validation (after L261):

```python
# Check mechanic content presence (enriched by interaction_designer)
for spec in parsed_specs:
    sn = spec.scene_number
    expected_mechs = scene_mechanics.get(sn, [])
    for mtype in expected_mechs:
        if mtype == "click_to_identify":
            # Check that identification prompts exist somewhere
            has_prompts = False
            for mt in spec.mode_transitions:
                if mt.from_mechanic == "click_to_identify":
                    has_prompts = True
            # Also check scene_specs for prompts
            scene_spec = next((s for s in scene_specs if s.get("scene_number") == sn), None)
            if scene_spec:
                for mc in scene_spec.get("mechanic_configs", []):
                    if mc.get("type") == "click_to_identify" and mc.get("config", {}).get("prompts"):
                        has_prompts = True
            if not has_prompts:
                issues.append(f"Scene {sn}: click_to_identify should have identification prompts")

        elif mtype == "description_matching":
            scene_spec = next((s for s in scene_specs if s.get("scene_number") == sn), None)
            if scene_spec:
                for mc in scene_spec.get("mechanic_configs", []):
                    if mc.get("type") == "description_matching":
                        descs = mc.get("config", {}).get("descriptions", [])
                        if len(descs) < 2:
                            issues.append(f"Scene {sn}: description_matching needs >= 2 descriptions")
```

**Files:** `interaction_spec_v3.py` (~30 new lines)

---

### Fix 2.9: Asset Generator V3 — Add mechanic-aware submit validation

**Files:**
- `backend/app/agents/asset_generator_v3.py`
- `backend/app/tools/asset_generator_tools.py`

**Current:** 100% mechanic-agnostic. All 5 tools generate only diagram images + zones. `submit_assets` validates zones but never checks mechanic-specific requirements.

**Fix approach:** The asset generator's PRIMARY job is visual assets (images + zones). Mechanic content is handled upstream by game_designer + scene_architect + interaction_designer. However, `submit_assets` should validate that mechanic-relevant zone data is sufficient:

**(a) Update `submit_assets_impl`** (`asset_generator_tools.py`, ~L798):

After existing zone validation, add mechanic-aware zone checks:

```python
# After existing zone validation (~line 839):

# Mechanic-aware zone validation
scene_specs = ctx.get("scene_specs_v3") or []
for scene_spec in scene_specs:
    if not isinstance(scene_spec, dict):
        continue
    sn = scene_spec.get("scene_number", 0)
    scene_key = f"scene_{sn}"
    scene_data = scenes.get(scene_key, {})
    zones = scene_data.get("zones", [])

    for mc in scene_spec.get("mechanic_configs", []):
        mtype = mc.get("type", "")
        zone_labels_used = mc.get("zone_labels_used", [])

        if mtype == "trace_path":
            # Verify waypoints have corresponding zones
            waypoints = mc.get("config", {}).get("waypoints", [])
            zone_label_set = {z.get("label", "").lower() for z in zones}
            missing_wp = [wp for wp in waypoints if wp.lower() not in zone_label_set]
            if missing_wp:
                warnings.append(f"Scene {sn}: trace_path waypoints {missing_wp} don't match any zones")

        elif mtype == "click_to_identify":
            # Verify enough zones for prompts
            prompts = mc.get("config", {}).get("prompts", [])
            if prompts and len(zones) < len(prompts):
                warnings.append(f"Scene {sn}: {len(prompts)} prompts but only {len(zones)} zones")
```

**Files:** `asset_generator_tools.py` (~30 new lines)

---

### Fix 2.10: Blueprint Assembler V3 — Populate per-mechanic config fields

**Files:**
- `backend/app/tools/blueprint_assembler_tools.py`

**Current:** `assemble_blueprint_impl()` (L414-534) flattens ALL mechanic configs to a single `config: Dict[str, Any]` per mechanic. The frontend expects root-level fields (`sequenceConfig`, `sortingConfig`, `paths`, `identificationPrompts`, etc.) that are NEVER populated.

**This is the CRITICAL fix** — it connects all upstream mechanic data to the frontend format.

**(a) Add per-mechanic blueprint population** (in `assemble_blueprint_impl`, after mechanic assembly ~L534):

```python
# After assembling mechanics list, populate blueprint-level mechanic configs
# These map to frontend's LabelDiagramBlueprint type expectations

# Per-scene mechanic config extraction
for scene_dict in id_scenes:
    scene_mechs = scene_dict.get("mechanics", [])
    for mech in scene_mechs:
        mtype = mech.get("mechanicType", "")
        config = mech.get("config") or {}

        if mtype == "trace_path" and config.get("waypoints"):
            # Map waypoints to zones for frontend TracePath format
            waypoints = config["waypoints"]
            zone_list = scene_dict.get("zones", [])
            zone_by_label = {z.get("label", "").lower(): z for z in zone_list}
            path_points = []
            for wp_label in waypoints:
                zone = zone_by_label.get(wp_label.lower())
                if zone:
                    path_points.append({"x": zone.get("x", 50), "y": zone.get("y", 50), "label": wp_label})

            scene_dict.setdefault("paths", []).append({
                "id": f"path_{scene_dict.get('scene_id', 'default')}",
                "points": path_points,
                "pathType": config.get("path_type", "linear"),
            })

        elif mtype == "click_to_identify" and config.get("prompts"):
            zone_list = scene_dict.get("zones", [])
            prompts = config["prompts"]
            id_prompts = []
            for i, prompt_text in enumerate(prompts):
                # Try to match prompt to a zone
                target_zone = zone_list[i] if i < len(zone_list) else None
                id_prompts.append({
                    "id": f"prompt_{i}",
                    "text": prompt_text,
                    "targetZoneId": target_zone.get("id", "") if target_zone else "",
                    "orderIndex": i,
                })
            scene_dict["identificationPrompts"] = id_prompts

        elif mtype == "sequencing" and config.get("items"):
            scene_dict["sequence_config"] = {
                "items": config["items"],
                "correctOrder": config.get("correct_order", []),
                "sequenceType": config.get("sequence_type", "linear"),
                "allowPartialCredit": True,
            }

        elif mtype == "description_matching" and config.get("descriptions"):
            scene_dict["description_matching_config"] = {
                "descriptions": config["descriptions"],
                "mode": config.get("mode", "click_zone"),
            }

        elif mtype == "sorting_categories" and config.get("categories"):
            scene_dict["sorting_config"] = {
                "categories": config["categories"],
                "items": config.get("items", []),
                "showCategoryHints": config.get("show_category_hints", True),
            }

        elif mtype == "memory_match" and config.get("pairs"):
            scene_dict["memory_match_config"] = {
                "pairs": config["pairs"],
                "gridSize": config.get("grid_size", 4),
                "flipDurationMs": config.get("flip_duration_ms", 600),
            }

        elif mtype == "branching_scenario" and config.get("nodes"):
            scene_dict["branching_config"] = {
                "nodes": config["nodes"],
                "startNodeId": config.get("start_node_id", ""),
                "showPathTaken": True,
                "allowBacktrack": True,
            }

        elif mtype == "compare_contrast" and config.get("expected_categories"):
            scene_dict["compare_config"] = {
                "expectedCategories": config["expected_categories"],
                "highlightMatching": config.get("highlight_matching", True),
            }
```

**(b) Also populate blueprint-level configs** (for backwards compat with single-scene games):

```python
# At blueprint root level (for first scene, backwards compat)
if id_scenes:
    first_scene = id_scenes[0]
    if first_scene.get("paths"):
        blueprint["paths"] = first_scene["paths"]
    if first_scene.get("identificationPrompts"):
        blueprint["identificationPrompts"] = first_scene["identificationPrompts"]
    if first_scene.get("sequence_config"):
        blueprint["sequenceConfig"] = first_scene["sequence_config"]
    if first_scene.get("sorting_config"):
        blueprint["sortingConfig"] = first_scene["sorting_config"]
    if first_scene.get("memory_match_config"):
        blueprint["memoryMatchConfig"] = first_scene["memory_match_config"]
    if first_scene.get("branching_config"):
        blueprint["branchingConfig"] = first_scene["branching_config"]
    if first_scene.get("compare_config"):
        blueprint["compareConfig"] = first_scene["compare_config"]
```

**Files:** `blueprint_assembler_tools.py` (~100 new lines)

---

### Fix 2.11: Blueprint Validator + Repair — Add mechanic-specific checks

**File:** `backend/app/tools/blueprint_assembler_tools.py`

**Current:** `validate_blueprint_impl()` (L777-901) has zero mechanic-specific checks. `repair_blueprint_impl()` (L908-1128) can't fix mechanic issues.

**(a) Add to `validate_blueprint_impl`** (~L895):

```python
# Mechanic-specific validation
for scene in blueprint.get("scenes", []):
    mechanics = scene.get("mechanics", [])
    for mech in mechanics:
        mtype = mech.get("mechanicType", "")
        config = mech.get("config") or {}

        if mtype == "trace_path" and not config.get("waypoints"):
            issues.append(f"Scene {scene.get('scene_id')}: trace_path missing waypoints in config")
            fixable_issues.append("trace_path_missing_waypoints")

        elif mtype == "click_to_identify" and not config.get("prompts"):
            if not scene.get("identificationPrompts"):
                issues.append(f"Scene {scene.get('scene_id')}: click_to_identify missing prompts")
                fixable_issues.append("click_to_identify_missing_prompts")

        elif mtype == "sequencing":
            seq_cfg = scene.get("sequence_config") or config
            if not seq_cfg.get("items") and not seq_cfg.get("correct_order"):
                issues.append(f"Scene {scene.get('scene_id')}: sequencing missing items/correct_order")

        elif mtype == "description_matching":
            dm_cfg = scene.get("description_matching_config") or config
            if not dm_cfg.get("descriptions"):
                issues.append(f"Scene {scene.get('scene_id')}: description_matching missing descriptions")
```

**(b) Add to `repair_blueprint_impl`** — Auto-generate missing prompts/descriptions from zone data:

```python
# After existing repairs (~L1123):

# Auto-generate click_to_identify prompts from zones
if "click_to_identify_missing_prompts" in fixable:
    for scene in blueprint.get("scenes", []):
        zones = scene.get("zones", [])
        for mech in scene.get("mechanics", []):
            if mech.get("mechanicType") == "click_to_identify" and not scene.get("identificationPrompts"):
                scene["identificationPrompts"] = [
                    {"id": f"prompt_{i}", "text": f"Click on the {z.get('label', '')}",
                     "targetZoneId": z.get("id", ""), "orderIndex": i}
                    for i, z in enumerate(zones)
                ]
                repairs.append(f"Generated {len(zones)} identification prompts from zones")
```

**Files:** `blueprint_assembler_tools.py` (~50 new lines)

---

### Fix 2.12: Fix `check_capabilities` accuracy (A3-1)

**File:** `backend/app/tools/game_design_v3_tools.py`, `check_capabilities_impl` (~line 158)

**Current:** Returns status from `INTERACTION_PATTERNS` which may overstate support.

**Fix:** After all Phase 2 fixes are applied, update status to reflect actual pipeline support. This should be the LAST Phase 2 fix since all other fixes improve support levels:

```python
# After getting pattern data from INTERACTION_PATTERNS:
ACTUAL_STATUS = {
    "drag_drop": "COMPLETE",
    "click_to_identify": "COMPLETE",       # After Fix 2.5, 2.7, 2.10
    "trace_path": "COMPLETE",              # After Fix 2.5, 2.10
    "sequencing": "COMPLETE",              # After Fix 2.5, 2.10
    "description_matching": "COMPLETE",    # After Fix 2.5, 2.7, 2.10
    "sorting_categories": "PARTIAL",       # Config structure exists, LLM must populate categories
    "memory_match": "PARTIAL",             # Config structure exists, LLM must populate pairs
    "branching_scenario": "PARTIAL",       # Config structure exists, LLM must populate nodes
    "compare_contrast": "PARTIAL",         # Config structure exists, needs dual diagrams
    "timed_challenge": "WRAPPER",          # Wraps another mechanic with timer
    "hierarchical": "MODIFIER",            # Cross-cutting, not a mechanic
}
for mech_id, entry in mechanics.items():
    entry["status"] = ACTUAL_STATUS.get(mech_id, "UNKNOWN")
```

**Files:** `game_design_v3_tools.py` (~15 changed lines)

---

### Phase 2 Verification

After all Phase 2 fixes:

1. **Schema import check:**
   ```bash
   cd backend && PYTHONPATH=. python -c "from app.agents.schemas.game_design_v3 import GameDesignV3; print('OK')"
   ```

2. **Tool registration check:**
   ```bash
   cd backend && PYTHONPATH=. python -c "
   from app.tools.scene_architect_tools import register_scene_architect_v3_tools
   from app.tools.interaction_designer_tools import register_interaction_designer_v3_tools
   tools_sa = register_scene_architect_v3_tools()
   tools_id = register_interaction_designer_v3_tools()
   print(f'Scene architect tools: {len(tools_sa)}')
   print(f'Interaction designer tools: {len(tools_id)}')
   assert len(tools_sa) >= 5, 'Missing scene architect tool'
   assert len(tools_id) >= 5, 'Missing interaction designer tool'
   print('OK')
   "
   ```

3. **Pipeline run with trace_path:**
   ```
   Question: "Trace the path of blood flow through the heart"
   Expected: Pipeline produces trace_path mechanic with waypoints, blueprint has paths field
   ```

4. **Pipeline run with click_to_identify:**
   ```
   Question: "Identify the parts of the human heart"
   Expected: Pipeline produces click_to_identify with prompts, blueprint has identificationPrompts
   ```

5. **Pipeline run with sequencing:**
   ```
   Question: "Put the stages of mitosis in order"
   Expected: Pipeline produces sequencing with items + correct_order, blueprint has sequenceConfig
   ```

6. **Multi-mechanic pipeline run:**
   ```
   Question: "Label the heart diagram, then trace blood flow, then identify each chamber's function"
   Expected: 3 mechanics per scene with configs, mode transitions between them
   ```

---

### Phase 2 Estimated Changes

| Fix | Files | Lines Changed (est) |
|-----|-------|-------------------|
| 2.1 V3 Context | 1 | ~5 |
| 2.2 DK Retriever | 2 | ~80 |
| 2.3 Game Designer V3 | 2 | ~35 |
| 2.4 Design Validator | 0 | 0 (works after 2.3) |
| 2.5 Scene Architect V3 | 2 | ~140 |
| 2.6 Scene Validator | 0 | 0 (already works) |
| 2.7 Interaction Designer V3 | 2 | ~120 |
| 2.8 Interaction Validator | 1 | ~30 |
| 2.9 Asset Generator V3 | 1 | ~30 |
| 2.10 Blueprint Assembler V3 | 1 | ~120 |
| 2.11 Blueprint Validator+Repair | 1 | ~60 |
| 2.12 check_capabilities | 1 | ~15 |
| **Total** | **~10 files** | **~635 lines** |

---

## Phase 3: Data Flow & Type Safety

### Fix 3.1: Type frontend `Mechanic` interface (B-3, D-1)

**File:** `frontend/src/components/templates/LabelDiagramGame/types.ts`, line 51–54

**Current:**
```ts
export interface Mechanic {
  type: InteractionMode;
  config?: Record<string, unknown>;
}
```

**Fix:** Add scoring/feedback fields from backend IDMechanic:
```ts
export interface Mechanic {
  type: InteractionMode;
  config?: Record<string, unknown>;
  // From backend IDMechanic (populated by blueprint_assembler_v3)
  scoring?: {
    strategy: string;
    points_per_correct: number;
    max_score: number;
    partial_credit?: boolean;
  };
  feedback?: {
    on_correct: string;
    on_incorrect: string;
    on_completion: string;
    misconceptions?: Array<{ trigger_label: string; message: string }>;
  };
}
```

---

### Fix 3.2: Make `GameScene.tasks` required (B-4)

**File:** `types.ts`, line 603

**Current:** `tasks?: SceneTask[];`

**Fix:** `tasks: SceneTask[];` — and update `migrateMultiSceneBlueprint` and `_sceneToBlueprint` to always ensure at least 1 implicit task.

In `_sceneToBlueprint` (line 34), if no tasks exist, create an implicit one:
```ts
const task = scene.tasks?.[taskIndex] ?? {
  task_id: `task_${sceneIndex + 1}_implicit`,
  title: scene.title,
  mechanic_type: (scene.mechanics?.[0]?.type || 'drag_drop') as InteractionMode,
  zone_ids: scene.zones.map(z => z.id),
  label_ids: scene.labels.map(l => l.id),
  scoring_weight: 1,
};
```

---

### Fix 3.3: Fix `normalizeBlueprint` phantom zones (N-3)

**File:** `index.tsx`, lines 180–192

**Bug:** When a label's `correctZoneId` doesn't match any zone, a phantom zone is created at grid position:
```ts
normalizedZones.push({
  id: label.correctZoneId,
  label: label.text,
  x: position.x,
  y: position.y,
  radius: 10,
});
```

**Fix:** Log a warning but don't create phantom zones. Instead, try to match label text to zone label:
```ts
normalizedLabels.forEach((label) => {
  if (!zoneIdSet.has(label.correctZoneId)) {
    // Try to find a zone by matching label text to zone label
    const matchingZone = normalizedZones.find(
      z => z.label.toLowerCase() === label.text.toLowerCase() && !assignedZoneIds.has(z.id)
    );
    if (matchingZone) {
      label.correctZoneId = matchingZone.id;
      assignedZoneIds.add(matchingZone.id);
    } else {
      console.warn(
        `[normalizeBlueprint] Label "${label.text}" references non-existent zone "${label.correctZoneId}". No matching zone found.`
      );
    }
  }
});
```

---

### Fix 3.4: Forward mechanic scoring/feedback to frontend (F1, D-1)

**File:** `backend/app/tools/blueprint_assembler_tools.py`, lines 654–662

**Bug:** When converting mechanics to frontend format, only `type` and `config` are forwarded. `scoring`, `feedback`, and `animations` are DROPPED:
```python
fe_mech: Dict[str, Any] = {
    "type": m.get("mechanicType") or m.get("type", "drag_drop"),
}
if m.get("config"):
    fe_mech["config"] = m["config"]
fe_mechanics.append(fe_mech)
```

The backend `IDMechanic` has `scoring`, `feedback`, `animations` fields (populated from `interaction_specs_v3`), but the frontend never receives them.

**Fix:**
```python
fe_mech: Dict[str, Any] = {
    "type": m.get("mechanicType") or m.get("type", "drag_drop"),
}
if m.get("config"):
    fe_mech["config"] = m["config"]
if m.get("scoring"):
    fe_mech["scoring"] = m["scoring"]
if m.get("feedback"):
    fe_mech["feedback"] = m["feedback"]
if m.get("animations"):
    fe_mech["animations"] = m["animations"]
fe_mechanics.append(fe_mech)
```

**Depends on:** Fix 3.1 (frontend Mechanic type needs scoring/feedback fields to receive this data).

---

### Fix 3.5: Fix normalizeBlueprint label→zone queue mapping (N-1)

**File:** `index.tsx`, lines 135–176

**Bug:** `normalizeBlueprint` uses a FIFO queue to assign labels to zones when multiple labels share a `correctZoneId`. This can produce wrong mappings because it distributes sequentially rather than by semantic match.

**Current logic:**
```ts
const zoneQueue: Record<string, string[]> = {};
// ... builds queue of zone IDs for labels that share zones
// Then assigns round-robin from queue
```

**Fix:** Instead of FIFO queue, match labels to zones by text similarity:
```ts
normalizedLabels.forEach((label) => {
  if (!zoneIdSet.has(label.correctZoneId)) {
    // First: try exact zone.label === label.text match
    const exactMatch = normalizedZones.find(
      z => z.label.toLowerCase().trim() === label.text.toLowerCase().trim()
        && !assignedZoneIds.has(z.id)
    );
    if (exactMatch) {
      label.correctZoneId = exactMatch.id;
      assignedZoneIds.add(exactMatch.id);
    } else {
      // Second: try substring match
      const partialMatch = normalizedZones.find(
        z => (z.label.toLowerCase().includes(label.text.toLowerCase())
           || label.text.toLowerCase().includes(z.label.toLowerCase()))
          && !assignedZoneIds.has(z.id)
      );
      if (partialMatch) {
        label.correctZoneId = partialMatch.id;
        assignedZoneIds.add(partialMatch.id);
      }
    }
  }
});
```

**Files:** `index.tsx` (~20 changed lines)

---

### Phase 3 Summary

| Fix | Description | Files | Lines (est) |
|-----|-------------|-------|-------------|
| 3.1 | Type frontend Mechanic (add scoring/feedback) | types.ts | ~15 |
| 3.2 | Make GameScene.tasks required | types.ts, index.tsx | ~10 |
| 3.3 | Fix normalizeBlueprint phantom zones | index.tsx | ~15 |
| 3.4 | Forward mechanic scoring/feedback to frontend | blueprint_assembler_tools.py | ~8 |
| 3.5 | Fix normalizeBlueprint label→zone mapping | index.tsx | ~20 |
| **Total** | | **~3 files** | **~68 lines** |

---

## Phase 4: Architecture & Quality

### Fix 4.1: Reclassify `hierarchical` as cross-cutting modifier (T-1, B-4)

**Scope:** This is an architectural change that touches multiple files.

**Approach:**
1. Keep `hierarchical` in `InteractionMode` for backward compatibility (don't break existing blueprints)
2. Add `hierarchy_config` to `Mechanic` interface:
   ```ts
   export interface HierarchyConfig {
     enabled: boolean;
     reveal_trigger: 'complete_parent' | 'click_expand' | 'hover_reveal';
     max_depth?: number;
   }

   export interface Mechanic {
     type: InteractionMode;
     config?: Record<string, unknown>;
     hierarchy_config?: HierarchyConfig;
   }
   ```
3. When `interactionMode === 'hierarchical'`, treat as `drag_drop` + hierarchy enabled
4. `HierarchyController` becomes a wrapper that enhances any mechanic

**Files affected:**
- `types.ts` — Add HierarchyConfig
- `useLabelDiagramState.ts` — initializeGame, transitionToMode
- `index.tsx` — renderInteractionContent hierarchy case

**This is a DEFERRED change** — it works today for drag_drop + hierarchy. Only becomes critical when we need hierarchy + trace_path or hierarchy + click_to_identify.

---

### Fix 4.2: Fix persistence restore (PS-2)

**File:** `index.tsx`, lines 384–387

**Bug:** `onLoad` callback receives saved state but doesn't feed it back to the Zustand store:
```ts
onLoad: (savedState) => {
  announceGameAction({ type: 'custom', message: 'Previous game progress restored', priority: 'polite' });
  // BUG: savedState is never applied to the store!
},
```

**Fix:** Apply saved state to the store. This requires `usePersistence` to save/restore the right subset of state:
```ts
onLoad: (savedState) => {
  if (savedState) {
    // Apply saved state back to store
    set({
      placedLabels: savedState.placedLabels || [],
      availableLabels: savedState.availableLabels || [],
      score: savedState.score || 0,
      isComplete: savedState.isComplete || false,
      completedZoneIds: new Set(savedState.completedZoneIds || []),
      // ... other restorable fields
    });
    get().updateVisibleZones();
  }
  announceGameAction({ type: 'custom', message: 'Previous game progress restored', priority: 'polite' });
},
```

**Audit note (Feb 10):** `usePersistence.ts` currently saves: `placedLabels`, `score`, `completedZoneIds`, `visibleZoneIds`, `multiSceneState`. Missing (marked TODO): `hintsUsed`, `incorrectAttempts`, `elapsedTimeMs`. After Phase 1 adds new mechanic progress states, the save function must also persist: `sequencingProgress`, `sortingProgress`, `memoryMatchProgress`, `branchingProgress`, `compareProgress`.

**Changes needed in `usePersistence.ts`:**
1. Update `SavedGameState` type to include new mechanic progress fields
2. Update save function (~line 103-114) to include `sequencingProgress`, `sortingProgress`, etc.
3. Update `onLoad` callback to restore all fields
4. Serialize `Set` fields (`completedZoneIds`, `visibleZoneIds`) as `Array` for JSON storage, deserialize back on load

---

### Fix 4.3: Mutex constraint transitivity (S-14, DEFERRED)

**Status:** DEFERRED — Non-critical for MVP.

**Bug:** Mutex constraints are bidirectional but not transitive. A↔B and B↔C does NOT make A and C blocked simultaneously.

**Why deferred:** Current mutex behavior is intentional for simple two-way exclusions (e.g., "show heart OR lungs, not both"). Transitive closure would create complex cascading blocks that are harder to reason about. If needed later, the fix is: compute transitive closure in `updateVisibleZones()` before evaluating mutex constraints.

---

### Fix 4.4: time_elapsed trigger (S-19)

**File:** `useLabelDiagramState.ts`, checkModeTransition (~line 843-845)

**Current:** `time_elapsed` case is a no-op comment:
```ts
case 'time_elapsed':
    // Time-based transitions would need to be handled by a timer in the component
    break;
```

**Fix approach:** Either implement or remove. Since `time_elapsed` is defined in `ModeTransitionTrigger` type and `InteractionSpecV3.VALID_TRIGGERS`, implement a basic version:

```ts
case 'time_elapsed': {
  // time_elapsed requires a timer value in trigger_value (seconds)
  const trigger = applicable?.trigger_value;
  if (typeof trigger === 'number' && state.multiModeState?.modeHistory) {
    const currentModeEntry = state.multiModeState.modeHistory
      .find(h => h.mode === state.interactionMode && !h.endTime);
    if (currentModeEntry) {
      const elapsed = (Date.now() - currentModeEntry.startTime) / 1000;
      shouldTransition = elapsed >= trigger;
    }
  }
  break;
}
```

**Note:** This evaluates on demand (when `checkModeTransition` is called). For real-time auto-transition, a `setInterval` timer would be needed — deferred to Phase 6.

---

### Phase 4 Summary

| Fix | Description | Files | Lines (est) | Status |
|-----|-------------|-------|-------------|--------|
| 4.1 | Reclassify hierarchy as modifier | types.ts, useLabelDiagramState.ts, index.tsx | ~25 | DEFERRED |
| 4.2 | Fix persistence restore | index.tsx, usePersistence.ts | ~30 | Active |
| 4.3 | Mutex transitivity | useLabelDiagramState.ts | 0 | DEFERRED |
| 4.4 | time_elapsed trigger | useLabelDiagramState.ts | ~15 | Active |
| **Total active** | | **~3 files** | **~45 lines** | |

---

## Phase 5: Rename (LABEL_DIAGRAM → INTERACTIVE_DIAGRAM)

### Updated Scope (from Re-Audit Feb 10)

Actual file counts (larger than originally estimated):

| Search Term | Files Found |
|-------------|------------|
| `LABEL_DIAGRAM` (upper case literal) | ~135 |
| `label_diagram` (lower case) | ~76 |
| `LabelDiagramGame` | ~24 |
| **Total unique files estimated** | **~150+** |

### Critical Files (must update atomically)

| File | What to Change | Notes |
|------|---------------|-------|
| `backend/app/agents/router.py` (L75-90) | TEMPLATE_REGISTRY key | `"LABEL_DIAGRAM"` → `"INTERACTIVE_DIAGRAM"` |
| `backend/app/agents/schemas/blueprint_schemas.py` (L899-906) | Schema validation dispatch | `template_type == "LABEL_DIAGRAM"` check |
| `backend/app/tools/blueprint_assembler_tools.py` | templateType output | All references to "LABEL_DIAGRAM" |
| `frontend/src/app/game/[id]/page.tsx` (L328) | Conditional rendering | Template type check |
| `frontend/src/components/templates/LabelDiagramGame/` | Directory rename | All 51 files inside |
| `backend/app/agents/schemas/label_diagram.py` | File rename | → `interactive_diagram.py` |
| `backend/prompts/blueprint_label_diagram.txt` | File rename | → `blueprint_interactive_diagram.txt` |
| `backend/app/config/presets/label_diagram_hierarchical.py` | File rename | → `interactive_diagram_hierarchical.py` |
| `backend/app/config/presets/advanced_label_diagram.py` | File rename | → `advanced_interactive_diagram.py` |

### Steps

1. **Directory rename:**
   ```bash
   git mv frontend/src/components/templates/LabelDiagramGame frontend/src/components/templates/InteractiveDiagramGame
   ```

2. **Backend file renames:**
   ```bash
   git mv backend/app/agents/schemas/label_diagram.py backend/app/agents/schemas/interactive_diagram.py
   git mv backend/prompts/blueprint_label_diagram.txt backend/prompts/blueprint_interactive_diagram.txt
   git mv backend/app/config/presets/label_diagram_hierarchical.py backend/app/config/presets/interactive_diagram_hierarchical.py
   git mv backend/app/config/presets/advanced_label_diagram.py backend/app/config/presets/advanced_interactive_diagram.py
   ```

3. **Global find-and-replace (in order):**
   - `LabelDiagramGame` → `InteractiveDiagramGame` in `.ts`, `.tsx`
   - `LabelDiagramBlueprint` → `InteractiveDiagramBlueprint` in `.ts`, `.tsx`
   - `LabelDiagramState` → `InteractiveDiagramState` in `.ts`, `.tsx`
   - `useLabelDiagramState` → `useInteractiveDiagramState` in `.ts`, `.tsx`
   - `LABEL_DIAGRAM` → `INTERACTIVE_DIAGRAM` in `.py`, `.ts`, `.tsx`
   - `label_diagram` → `interactive_diagram` in `.py`, `.ts`, `.tsx` (careful: not partial matches)
   - `LabelDiagram` → `InteractiveDiagram` in component/type names (remaining)

4. **Verify compilation:**
   ```bash
   cd frontend && npx tsc --noEmit
   cd backend && PYTHONPATH=. python -c "from app.agents.graph import *; from app.agents.schemas import *; print('OK')"
   ```

### Backward Compatibility

1. **Database:** Existing games stored with `template_type = "LABEL_DIAGRAM"` must still render.
   - `frontend/src/app/game/[id]/page.tsx` — Accept BOTH:
     ```ts
     if (templateType === 'INTERACTIVE_DIAGRAM' || templateType === 'LABEL_DIAGRAM') {
       return <InteractiveDiagramGame ... />;
     }
     ```
   - `backend/app/agents/schemas/blueprint_schemas.py` — Accept BOTH in validation dispatch.

2. **API:** Backend router can emit `"INTERACTIVE_DIAGRAM"` for new runs. Old runs keep `"LABEL_DIAGRAM"`.

3. **Prompt file:** `blueprint_assembler_v3` reads prompt by template name. Update path lookup to handle both.

4. **Config presets:** Preset names used in `pipeline_preset` field. Keep old names as aliases pointing to new files.

### Verification Script

```bash
#!/bin/bash
# Verify no stale LABEL_DIAGRAM references remain
echo "Checking for stale references..."
STALE_PY=$(grep -r "LABEL_DIAGRAM" backend/ --include="*.py" -l | grep -v __pycache__ | grep -v ".pyc")
STALE_TS=$(grep -r "LABEL_DIAGRAM" frontend/ --include="*.ts" --include="*.tsx" -l | grep -v node_modules)
STALE_DIR=$(find frontend/src/components/templates/LabelDiagramGame 2>/dev/null)

if [ -z "$STALE_PY" ] && [ -z "$STALE_TS" ] && [ -z "$STALE_DIR" ]; then
  echo "✓ No stale references found"
else
  echo "✗ Stale references:"
  echo "$STALE_PY"
  echo "$STALE_TS"
  echo "$STALE_DIR"
  exit 1
fi

# Compilation check
echo "Checking TypeScript..."
cd frontend && npx tsc --noEmit && echo "✓ TypeScript OK"
echo "Checking Python imports..."
cd ../backend && PYTHONPATH=. python -c "from app.agents.graph import *; print('✓ Python OK')"
```

---

## Phase 6: Polish

Lower priority items, to be planned after Phases 1-5 are complete:

| # | Item | Severity |
|---|------|----------|
| 6.1 | Accessibility gaps (ARIA labels for non-drag_drop mechanics) | MEDIUM |
| 6.2 | Performance: normalizeBlueprint O(n²) → O(n) | LOW |
| 6.3 | Complete undo/redo for all modes (currently drag_drop only) | MEDIUM |
| 6.4 | Blueprint input validation on frontend load | LOW |
| 6.5 | Real-time time_elapsed auto-transition (setInterval timer) | LOW |
| 6.6 | usePersistence: implement hintsUsed, incorrectAttempts, elapsedTimeMs tracking | LOW |
| 6.7 | Per-mechanic feedback rendering (use scoring/feedback from Mechanic type) | MEDIUM |
| 6.8 | Asset workflow integration (mechanic-specific asset generation sub-workflows) | LOW |

---

## Dependencies Between Fixes

```
Phase 0 (DONE)
  ↓
Phase 1 (Frontend) ←→ Phase 2 (Backend) [can run in parallel]
  ↓                       ↓
Phase 3 (Data Flow) — requires Phase 1 + Phase 2
  ↓
Phase 4 (Architecture) — requires Phase 3
  ↓
Phase 5 (Rename) — independent, but do after code is stable
  ↓
Phase 6 (Polish)
```

**Phase 1 and Phase 2 are independent** — frontend state fixes don't depend on backend tool additions, and vice versa. They can be executed in parallel.

**Phase 2 internal dependencies (must be sequential):**
```
Fix 2.1 (V3 Context) — prerequisite for all tool fixes
  ↓
Fix 2.2 (DK Retriever) — richer data for downstream agents
  ↓
Fix 2.3 (Game Designer V3) → Fix 2.4 (Design Validator auto-fixed)
  ↓
Fix 2.5 (Scene Architect V3) → Fix 2.6 (Scene Validator auto-fixed)
  ↓
Fix 2.7 (Interaction Designer V3) → Fix 2.8 (Interaction Validator)
  ↓
Fix 2.9 (Asset Generator V3) — mechanic-aware zone validation
  ↓
Fix 2.10 (Blueprint Assembler V3) — maps all configs to frontend format
  ↓
Fix 2.11 (Blueprint Validator+Repair) — catches/fixes missing configs
  ↓
Fix 2.12 (check_capabilities) — update status LAST after all fixes
```

---

## Estimated Change Counts

| Phase | Files Modified | Lines Changed (est) |
|-------|---------------|-------------------|
| Phase 1 | 9 (types.ts, useLabelDiagramState.ts, index.tsx, + 6 interaction components) | ~600 |
| Phase 2 | ~10 (v3_context, DK retriever, game_designer_v3, scene_architect_v3, interaction_designer_v3, asset_generator_v3, blueprint_assembler_v3, validators) | ~635 |
| Phase 3 | 3 (types.ts, index.tsx, useLabelDiagramState.ts) | ~100 |
| Phase 4 | 4 (types.ts, state.ts, index.tsx, persistence) | ~150 |
| Phase 5 | ~100 (automated rename) | ~500 |
| Phase 6 | TBD | TBD |

**Phases 1 and 2 are both large** (~600 lines each). Phase 1 covers frontend Zustand integration for all mechanics. Phase 2 covers the full backend pipeline from domain knowledge → blueprint assembly for all mechanics.
