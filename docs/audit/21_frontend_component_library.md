# Frontend InteractiveDiagramGame Component Library Audit

**Date:** 2026-02-11
**Scope:** Complete component tree, types, hooks, interactions, data flow
**Total measured:** ~11,915 lines across 50+ files

---

## 1. FILE TREE & LINE COUNTS

```
InteractiveDiagramGame/
├── index.tsx                    (1142)  Entry point
├── types.ts                     (896)   Type definitions
├── MechanicRouter.tsx           (452)   Mechanic switch
├── DiagramCanvas.tsx            (386)   Image + zone rendering
├── DropZone.tsx                 (573)   Individual zone
├── DraggableLabel.tsx           (49)    Draggable label item
├── LabelTray.tsx                (43)    Label container
├── GameControls.tsx             (153)   Score + hints + reset
├── ResultsPanel.tsx             (130)   End-game results
├── ErrorBoundary.tsx            (94)    React error boundary
├── MechanicConfigError.tsx      (42)    Missing config error UI
├── Harness.tsx                  (36)    Re-export wrapper
├── SceneTransition.tsx          (326)   Scene transition animations
│
├── hooks/
│   ├── useInteractiveDiagramState.ts  (1678)  Main Zustand store
│   ├── useCommandHistory.ts           (254)   Undo/redo
│   ├── useEventLog.ts                 (336)   Analytics events
│   ├── usePersistence.ts              (271)   Save/load
│   ├── useReducedMotion.ts            (38)    A11y motion pref
│   ├── useZoneCollision.ts            (283)   Zone hit detection
│   └── index.ts                       (34)
│
├── interactions/
│   ├── HotspotManager.tsx             click_to_identify
│   ├── PathDrawer.tsx                 trace_path
│   ├── HierarchyController.tsx        hierarchical
│   ├── DescriptionMatcher.tsx         description_matching
│   ├── SequenceBuilder.tsx            sequencing
│   ├── SortingCategories.tsx          sorting_categories
│   ├── MemoryMatch.tsx                memory_match
│   ├── BranchingScenario.tsx          branching_scenario
│   ├── CompareContrast.tsx            compare_contrast
│   ├── TimedChallengeWrapper.tsx       timed_challenge (wrapper)
│   ├── GameSequenceRenderer.tsx       Multi-scene renderer
│   ├── SVGZoneRenderer.tsx            SVG zone overlay
│   ├── SceneProgressBar.tsx           Scene progress
│   ├── ModeIndicator.tsx              Current mode badge
│   ├── TemporalController.tsx         Temporal constraint mgr
│   ├── UndoRedoControls.tsx           Undo/redo UI
│   └── index.ts                       (52)
│
├── accessibility/
│   ├── KeyboardNav.tsx                (275)   Keyboard navigation
│   ├── ScreenReaderAnnouncements.tsx  (289)   ARIA live regions
│   └── index.ts                       (26)
│
├── commands/
│   ├── CommandHistory.ts              (348)   Command manager
│   ├── PlaceLabelCommand.ts           (127)   Place label cmd
│   ├── RemoveLabelCommand.ts          (125)   Remove label cmd
│   ├── types.ts                       (99)    Command types
│   └── index.ts                       (43)
│
├── events/
│   ├── GameEventLog.ts                (588)   Event logger
│   ├── types.ts                       (364)   Event types
│   └── index.ts                       (44)
│
├── animations/
│   ├── useAnimation.ts                (905)   Animation engine
│   ├── Confetti.tsx                           Celebration
│   └── index.ts                       (11)
│
├── persistence/
│   ├── GamePersistence.ts                     Save/load engine
│   └── index.ts                       (12)
│
└── utils/
    └── extractTaskConfig.ts           (55)    Config extraction
```

---

## 2. TYPE DEFINITIONS (types.ts — 896 lines)

### InteractionMode (11 values)

```typescript
type InteractionMode =
  | 'drag_drop'
  | 'click_to_identify'
  | 'trace_path'
  | 'hierarchical'
  | 'description_matching'
  | 'sequencing'
  | 'sorting_categories'
  | 'memory_match'
  | 'branching_scenario'
  | 'compare_contrast'
  | 'timed_challenge'
```

### Core Types

| Type | Key Fields | Lines |
|------|-----------|-------|
| `Zone` | id, label, x, y, radius?, points?, shape, description, parent_zone_id?, group_only? | ~20 |
| `Label` | id, text, correctZoneId, isDistractor?, explanation? | ~10 |
| `PlacedLabel` | labelId, zoneId, isCorrect | ~5 |
| `Hint` | zoneId, text | ~5 |
| `DistractorLabel` | id, text, explanation | ~5 |
| `ZoneGroup` | parentZoneId, childZoneIds[], revealTrigger | ~5 |
| `ModeTransition` | fromMode, toMode, trigger, triggerValue?, animation, message | ~10 |

### Per-Mechanic Config Types

| Config Type | Key Fields | Required By |
|------------|-----------|------------|
| `SequenceConfig` | items[], correctOrder[], sequenceType, layoutMode, connectorStyle, showPositionNumbers | sequencing |
| `SortingConfig` | categories[], items[], sortMode, submitMode, showCategoryHints | sorting_categories |
| `MemoryMatchConfig` | pairs[], gameVariant, matchType, gridSize, cardBackStyle, flipDurationMs | memory_match |
| `BranchingConfig` | nodes[], startNodeId, showPathTaken, allowBacktrack, showConsequences | branching_scenario |
| `CompareConfig` | diagramA, diagramB, expectedCategories, comparisonMode, categoryTypes | compare_contrast |
| `DescriptionMatchConfig` | descriptions[], subMode, showConnectingLines, deferEvaluation | description_matching |
| `ClickToIdentifyConfig` | prompts[], promptStyle, highlightOnHover, selectionMode | click_to_identify |
| `TracePathConfig` | waypoints[], pathType, drawingMode, showWaypointLabels | trace_path |
| `DragDropConfig` | shuffleLabels, showHints, maxAttempts | drag_drop |

### InteractiveDiagramBlueprint (L581-666, ~86 fields)

```typescript
interface InteractiveDiagramBlueprint {
  // Core
  templateType: 'INTERACTIVE_DIAGRAM'
  title: string
  narrativeIntro?: string
  diagram: { assetUrl?, assetPrompt, width?, height?, zones? }
  labels: Label[]
  tasks?: BlueprintSceneTask[]

  // Mechanics
  mechanics?: Mechanic[]
  modeTransitions?: ModeTransition[]
  interactionMode: InteractionMode

  // Specialized configs (root-level)
  sequenceConfig?: SequenceConfig
  sortingConfig?: SortingConfig
  memoryMatchConfig?: MemoryMatchConfig
  branchingConfig?: BranchingConfig
  compareConfig?: CompareConfig
  descriptionMatchingConfig?: DescriptionMatchConfig
  clickToIdentifyConfig?: ClickToIdentifyConfig
  tracePathConfig?: TracePathConfig
  dragDropConfig?: DragDropConfig

  // Hierarchy
  zoneGroups?: ZoneGroup[]
  hierarchy?: { enabled, strategy, groups }

  // Temporal
  temporalConstraints?: TemporalConstraint[]
  motionPaths?: MotionPath[]
  revealOrder?: string[]

  // Scoring
  scoringStrategy?: { type, base_points_per_zone, time_bonus_enabled?, partial_credit?, max_score? }

  // Media
  hints?: Hint[]
  feedbackMessages?: FeedbackMessages
  mediaAssets?: MediaAsset[]
  animations?: AnimationSpec
}
```

### Multi-Scene Types

| Type | Key Fields |
|------|-----------|
| `GameScene` | sceneId, sceneNumber, title, diagram?, zones?, labels?, interactionMode, maxScore, tasks[], mechanics[] |
| `GameSequence` | sequenceId, title, scenes[], progressionType, totalMaxScore, passThreshold |
| `BlueprintSceneTask` | taskId, title, mechanicType, zoneIds[], labelIds[], instructions, scoringWeight |
| `MultiSceneInteractiveDiagramBlueprint` | is_multi_scene: true, game_sequence: GameSequence, + blueprint fields |

### Per-Mechanic Progress Types

| Type | Fields |
|------|--------|
| `SequencingProgress` | currentOrder[], isSubmitted, correctPositions, totalPositions |
| `SortingProgress` | itemCategories: Map, isSubmitted, correctCount, totalCount |
| `MemoryMatchProgress` | matchedPairIds[], attempts, totalPairs |
| `BranchingProgress` | currentNodeId, pathTaken[] |
| `CompareProgress` | categorizations: Map, isSubmitted, correctCount, totalCount |

---

## 3. ZUSTAND STORE (useInteractiveDiagramState.ts — 1678 lines)

### State Fields (~50)

**Core Game State:**
- `blueprint`, `originalBlueprint` (for reset)
- `availableLabels`, `placedLabels`
- `score`, `maxScore`, `basePointsPerZone`
- `showHints`, `draggingLabelId`, `incorrectFeedback`
- `interactionMode`

**Mode-Specific State:**
- `pathProgress` (trace_path)
- `identificationProgress` (click_to_identify)
- `hierarchyState` (hierarchical)
- `descriptionMatchingState` (description_matching)

**Multi-Scene State:**
- `multiSceneState`, `gameSequence`

**Temporal Intelligence:**
- `temporalConstraints`, `motionPaths`
- `completedZoneIds`, `visibleZoneIds`, `blockedZoneIds`

**Multi-Mode (Agentic):**
- `multiModeState`, `modeTransitions`, `_transitionTimerId`

**Per-Mechanic Progress:**
- `sequencingProgress`, `sortingProgress`, `memoryMatchProgress`
- `branchingProgress`, `compareProgress`

### Actions (~35)

**Core:**
1. `initializeGame(blueprint)` — Full initialization, shuffles labels, derives mechanics
2. `placeLabel(labelId, zoneId)` — Place label on zone, check correctness
3. `removeLabel(labelId)` — Remove placed label
4. `resetGame()` — Uses originalBlueprint for proper reset
5. `toggleHints()`, `clearIncorrectFeedback()`
6. `completeInteraction()` — Finish current mechanic

**Mode-Specific:**
7. `updatePathProgress(pathProgress)`
8. `updateIdentificationProgress(progress)`
9. `updateHierarchyState(hierarchyState)`

**Description Matching:**
10. `initializeDescriptionMatching(mode)`
11. `recordDescriptionMatch(match)`

**Per-Mechanic (Fix 1.7g):**
12. `updateSequenceOrder(itemOrder)`
13. `submitSequence()`
14. `updateSortingPlacement(itemId, categoryId)`
15. `submitSorting()`
16. `recordMemoryMatch(pairId)`
17. `recordMemoryAttempt()`
18. `recordBranchingChoice(nodeId, optionId, isCorrect, nextNodeId)`
19. `undoBranchingChoice()`
20. `updateCompareCategorization(zoneId, category)`
21. `submitCompare()`

**Temporal:**
22. `updateVisibleZones()`
23. `getVisibleZones()`, `isZoneVisible(zoneId)`, `isZoneBlocked(zoneId)`

**Multi-Mode:**
24. `initializeMultiMode(mechanics, transitions)`
25. `checkModeTransition()`
26. `transitionToMode(newMode, transition)`
27. `getAvailableModes()`, `canSwitchToMode(mode)`

**Multi-Scene:**
28. `initializeMultiSceneGame(sequence)`
29. `advanceToScene(sceneIndex)`
30. `completeScene(result)`
31. `completeCurrentScene()`
32. `advanceToNextScene()`
33. `advanceToNextTask()`
34. `getCurrentTask()`

### Key Helper: _sceneToBlueprint (L39-133)

Converts `GameScene` → `InteractiveDiagramBlueprint`:
- Creates implicit task if scene has none
- Extracts per-mechanic configs from `mechanics[]` array
- Only passes config matching task mechanic type
- Forwards expanded config types (sequenceConfig, sortingConfig, etc.)
- Filters temporal constraints to task zones

---

## 4. MECHANIC ROUTER (MechanicRouter.tsx — 452 lines)

Switch on `interactionMode`:

| Mode | Component | Config Required | Fallback |
|------|-----------|----------------|----------|
| `drag_drop` | DiagramCanvas + LabelTray + DragOverlay | (none — default) | Always works |
| `click_to_identify` | HotspotManager | identificationPrompts | - |
| `trace_path` | PathDrawer | tracePathConfig?.waypoints | - |
| `hierarchical` | HierarchyController | zoneGroups | - |
| `description_matching` | DescriptionMatcher | descriptionMatchingConfig | - |
| `sequencing` | SequenceBuilder | sequenceConfig | Labels as items fallback |
| `sorting_categories` | SortingCategories | sortingConfig | MechanicConfigError |
| `compare_contrast` | CompareContrast | compareConfig | Legacy stub fallback |
| `memory_match` | MemoryMatch | memoryMatchConfig | MechanicConfigError |
| `branching_scenario` | BranchingScenario | branchingConfig | MechanicConfigError |
| `timed_challenge` | TimedChallengeWrapper (recursive) | temporalConstraints | Defaults to drag_drop |

### DndContext Wrapping (AC-2)

Only `drag_drop` and `hierarchical` modes get wrapped in DndContext.
Other modes handle their own interaction (click, sort, etc.).

---

## 5. INTERACTION COMPONENTS

### 5.1 HotspotManager (click_to_identify)

**Props:** zones[], prompts[], selectionMode (sequential|any_order), progress, onZoneClick, onAllComplete, animations, feedbackMessages

**How it works:** Renders clickable zones over diagram. User clicks zones to identify them. Sequential mode shows one prompt at a time.

### 5.2 PathDrawer (trace_path)

**Props:** zones[], waypoints[], onComplete, pathProgress, width, height, assetUrl

**How it works:** User clicks waypoints in order to trace a path. Shows progress along the path.

### 5.3 HierarchyController (hierarchical)

**Props:** zoneGroups[], labels[], onGroupExpand, onLabelPlace, hierarchyState

**How it works:** Shows parent zones. Clicking parent reveals children. Labels can be placed on child zones.

### 5.4 DescriptionMatcher (description_matching)

**Props:** zones[], descriptions[], onMatch, descriptionMatchingState, mode

**How it works:** User matches text descriptions to zones on the diagram.

### 5.5 SequenceBuilder (sequencing)

**Props:** items[], correctOrder[], allowPartialCredit, onComplete, storeProgress?, onOrderChange?, onStoreSubmit?

**How it works:** Drag-to-reorder items using dnd-kit sortable. Submit to check order. Partial credit for items close to correct position.

### 5.6 SortingCategories (sorting_categories)

**Props:** items[], categories[], sortMode, storeProgress?, onPlacement?, onStoreSubmit?, onComplete

**How it works:** Drag items into category containers. Sort modes: bucket, venn_2, venn_3, matrix, column.

### 5.7 MemoryMatch (memory_match)

**Props:** pairs[], gridSize, flipDurationMs, storeProgress?, onPairMatched?, onAttemptMade?, onComplete

**How it works:** Flip cards to find matching pairs. Variants: classic, column_match, scatter, progressive, peek.

### 5.8 BranchingScenario (branching_scenario)

**Props:** nodes[], startNodeId, showPathTaken, allowBacktrack, storeProgress?, onChoice?, onUndo?, onComplete

**How it works:** Navigate decision tree. Each node has prompt + choices. Choices lead to next node or end.

### 5.9 CompareContrast (compare_contrast)

**Props:** diagramA, diagramB, expectedCategories, comparisonMode, storeProgress?, onCategorize?, onStoreSubmit?, onComplete

**How it works:** Compare two diagrams. Categorize zones as similar/different/unique_a/unique_b. Modes: side_by_side, slider, overlay_toggle, venn, spot_difference.

### 5.10 TimedChallengeWrapper (timed_challenge)

**Props:** wrappedMode, timeLimit, onTimeUp, children

**How it works:** Wraps another mechanic with a countdown timer.

---

## 6. SUPPORTING SYSTEMS

### 6.1 Accessibility (590 lines)

- **KeyboardNav:** Tab navigation between zones, Enter to select, Escape to cancel
- **ScreenReaderAnnouncements:** ARIA live regions for game events (label placed, zone completed, etc.)

### 6.2 Commands (742 lines)

- **CommandHistory:** Undo/redo stack with max depth
- **PlaceLabelCommand:** Undoable label placement
- **RemoveLabelCommand:** Undoable label removal
- Only covers drag_drop operations (not other mechanics)

### 6.3 Events (996 lines)

- **GameEventLog:** Analytics event logging
- Event types: drag, placement, mode change, game lifecycle, hints, undo/redo, temporal
- Serializable for replay

### 6.4 Animations (905+ lines)

- **useAnimation:** Core animation engine
- Types: pulse, glow, scale, shake, fade, bounce, confetti, path_draw
- Easing: linear, ease-out, ease-in-out, bounce, elastic
- Respects prefers-reduced-motion

### 6.5 Persistence

- **GamePersistence:** Save/load to localStorage/IndexedDB
- Session-based saves
- Auto-restore on page reload

### 6.6 Utils

- **extractTaskConfig.ts:**
  - `extractMechanicConfig(blueprint, mode)` — Gets config for mechanic type
  - `mechanicNeedsDndContext(mode)` — Returns true for drag_drop + hierarchical only

---

## 7. BLUEPRINT FIELD REQUIREMENTS PER MECHANIC

This maps what each interaction component **actually reads** from the blueprint:

| Mechanic | Required Blueprint Fields | Config Field |
|----------|--------------------------|-------------|
| `drag_drop` | `diagram`, `labels`, `zones` (from diagram) | `dragDropConfig` (optional) |
| `click_to_identify` | `diagram`, `zones`, `clickToIdentifyConfig.prompts` | `clickToIdentifyConfig` |
| `trace_path` | `diagram`, `zones`, `tracePathConfig.waypoints` | `tracePathConfig` |
| `hierarchical` | `diagram`, `zones`, `zoneGroups` | (uses zoneGroups) |
| `description_matching` | `diagram`, `zones`, `descriptionMatchingConfig.descriptions` | `descriptionMatchingConfig` |
| `sequencing` | `sequenceConfig.items`, `sequenceConfig.correctOrder` | `sequenceConfig` |
| `sorting_categories` | `sortingConfig.categories`, `sortingConfig.items` | `sortingConfig` |
| `memory_match` | `memoryMatchConfig.pairs` | `memoryMatchConfig` |
| `branching_scenario` | `branchingConfig.nodes`, `branchingConfig.startNodeId` | `branchingConfig` |
| `compare_contrast` | `compareConfig.diagramA`, `compareConfig.diagramB`, `compareConfig.expectedCategories` | `compareConfig` |
| `timed_challenge` | `temporalConstraints` + inner mechanic's fields | (wraps inner) |

### Where Config Comes From

In the blueprint, mechanic configs can live in two places:
1. **Root-level fields:** `blueprint.sequenceConfig`, `blueprint.sortingConfig`, etc.
2. **mechanics[] array:** `blueprint.mechanics[i].config` (requires extraction)

`_sceneToBlueprint()` extracts from `mechanics[]` to root-level fields.
`extractMechanicConfig()` in utils checks root first, then `mechanics[]`.

---

## 8. DATA FLOW: Backend Blueprint → Frontend Game

```
Backend blueprint_assembler_tools.py:assemble_blueprint()
  │
  ├─ Builds InteractiveDiagramBlueprint with:
  │   ├─ scenes[] (IDScene with zones, labels, mechanics)
  │   ├─ scene_transitions[]
  │   ├─ total_max_score, pass_threshold
  │   └─ Per-scene: diagram_image_url, zones, labels, mechanics
  │
  ▼
Frontend game/[id]/page.tsx
  │
  ├─ Fetches blueprint from API
  ├─ Checks is_multi_scene
  │
  ▼
InteractiveDiagramGame/index.tsx
  │
  ├─ normalizeBlueprint() — Converts backend format to frontend types
  ├─ isMultiSceneBlueprint() check
  │
  ├─ IF multi-scene:
  │   ├─ initializeMultiSceneGame(game_sequence)
  │   ├─ _sceneToBlueprint(scene, idx, taskIdx) for current task
  │   └─ initializeGame(taskBlueprint)
  │
  ├─ IF single-scene:
  │   └─ initializeGame(blueprint)
  │
  ▼
useInteractiveDiagramState.initializeGame(blueprint)
  │
  ├─ Shuffles labels (regular + distractors)
  ├─ Derives mechanics list from blueprint.mechanics[]
  ├─ Sets interactionMode from first mechanic (or blueprint.interactionMode)
  ├─ Initializes mode-specific state
  ├─ Calculates maxScore from scoringStrategy
  │
  ▼
MechanicRouter (switch on interactionMode)
  │
  ├─ Renders appropriate interaction component
  ├─ Passes blueprint fields as props
  └─ Component reports score/completion back to store
```

---

## 9. IDENTIFIED GAPS & ISSUES

### 9.1 Config Type Mismatches (camelCase vs snake_case)

Backend blueprint uses snake_case keys in mechanic configs:
```json
{"type": "sequencing", "config": {"correct_order": [...], "items": [...]}}
```

Frontend types expect camelCase:
```typescript
interface SequenceConfig {
  correctOrder: string[];
  items: SequenceItem[];
}
```

`_sceneToBlueprint()` attempts to bridge this but doesn't do full key transformation.

### 9.2 Three Config Types Defined But Never Read

- `dragDropConfig` — DropZone component doesn't read it
- `clickToIdentifyConfig` — HotspotManager reads `identificationPrompts` from blueprint root, not config
- `tracePathConfig` — PathDrawer reads `waypoints` from blueprint root, not config

These config types exist in types.ts but the components read from different fields.

### 9.3 Six Components Exist But Not Wired Into Main Flow

- `TemporalController` — Created but not integrated into game loop
- `SVGZoneRenderer` — Alternative zone renderer, not used by default
- `SceneProgressBar` — Exists in interactions/ but not rendered in any parent
- `ModeIndicator` — Badge component, not rendered in game UI
- `UndoRedoControls` — Visual component exists but not connected to game flow
- `Confetti` — Used by ResultsPanel only

### 9.4 Store Integration Gaps

5 of 6 non-drag_drop mechanics accept `storeProgress` prop but NEVER restore state from it:
- `SequenceBuilder`: Accepts storeProgress but always starts fresh
- `SortingCategories`: Same
- `MemoryMatch`: Same
- `BranchingScenario`: Same
- `CompareContrast`: Same

Only `DescriptionMatcher` does proper store-driven resume.

### 9.5 MechanicConfigError Coverage

Only 3 mechanics show MechanicConfigError when config is missing:
- `sorting_categories` ✓
- `memory_match` ✓
- `branching_scenario` ✓

Other mechanics silently render with empty/default data:
- `sequencing` falls back to using labels as items
- `compare_contrast` falls back to stub diagrams
- `click_to_identify`, `trace_path`, `description_matching` may crash or show nothing

### 9.6 Known Bugs (from previous audit, may or may not be fixed)

1. `advanceToNextTask`: max_score = actual score → percentage always 100%
2. Persistence: hintsUsed/incorrectAttempts/elapsedTimeMs always saved as 0
3. Command system only covers drag_drop (PlaceLabelCommand/RemoveLabelCommand)
4. Score calculation differs per mechanic (some delta-based, some absolute)

### 9.7 Multi-Scene Zone Filtering

- `visibleZoneIds` not always cleared on task transition (SB-FIX-3)
- `temporalConstraints` not always filtered to current task zones (SB-FIX-4)
- Can cause phantom zones or blocked zones from previous task
