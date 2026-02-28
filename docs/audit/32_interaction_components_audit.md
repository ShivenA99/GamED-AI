# Audit 32: Interaction Components Deep Audit

**Date:** 2026-02-14
**Scope:** All 9 interaction components in InteractiveDiagramGame
**Goal:** Identify every crash/exception path and document exact data contracts for multi-scene, multi-mechanic games

---

## Table of Contents

1. [Component 1: EnhancedDragDropGame (drag_drop)](#1-enhanceddragdropgame-drag_drop)
2. [Component 2: EnhancedSequenceBuilder (sequencing)](#2-enhancedsequencebuilder-sequencing)
3. [Component 3: EnhancedSortingCategories (sorting_categories)](#3-enhancedsortingcategories-sorting_categories)
4. [Component 4: EnhancedMemoryMatch (memory_match)](#4-enhancedmemorymatch-memory_match)
5. [Component 5: EnhancedHotspotManager (click_to_identify)](#5-enhancedhotspotmanager-click_to_identify)
6. [Component 6: EnhancedPathDrawer (trace_path)](#6-enhancedpathdrawer-trace_path)
7. [Component 7: DescriptionMatcher (description_matching)](#7-descriptionmatcher-description_matching)
8. [Component 8: BranchingScenario (branching_scenario)](#8-branchingscenario-branching_scenario)
9. [Component 9: CompareContrast (compare_contrast)](#9-comparecontrast-compare_contrast)
10. [Cross-Component Pattern Analysis](#10-cross-component-pattern-analysis)
11. [Gap Analysis: Backend vs Frontend Contracts](#11-gap-analysis-backend-vs-frontend-contracts)
12. [Complete Crash Path Catalog](#12-complete-crash-path-catalog)
13. [Proposed Fixes](#13-proposed-fixes)

---

## 1. EnhancedDragDropGame (drag_drop)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/EnhancedDragDropGame.tsx`
**Registry key:** `drag_drop`
**Config key:** `dragDropConfig`
**Needs DndContext:** YES (wrapped externally by MechanicRouter)

### Props Interface

```typescript
interface EnhancedDragDropGameProps {
  blueprint: InteractiveDiagramBlueprint;           // REQUIRED
  placedLabels: PlacedLabel[];                       // REQUIRED
  availableLabels: (Label | DistractorLabel)[];      // REQUIRED
  draggingLabelId: string | null;                    // REQUIRED
  incorrectFeedback: { labelId: string; message: string } | null; // REQUIRED
  showHints: boolean;                                // REQUIRED
  sensors: SensorDescriptor<SensorOptions>[];        // REQUIRED
  onDragStart: (e: DragStartEvent) => void;          // REQUIRED
  onDragEnd: (e: DragEndEvent) => void;              // REQUIRED
  onDragCancel: () => void;                          // REQUIRED
  onPlace?: (labelId: string, zoneId: string) => boolean; // OPTIONAL (click-to-place mode only)
  onAction?: (action: MechanicAction) => ActionResult | null; // OPTIONAL
}
```

### Data Shape Expected from Blueprint

| Field | Path | Required | Default | Crash if missing |
|-------|------|----------|---------|-----------------|
| `diagram.zones` | `bp.diagram.zones` | YES | N/A | YES - `.map()` on undefined |
| `diagram.assetUrl` | `bp.diagram.assetUrl` | NO | renders without image | No |
| `diagram.assetPrompt` | `bp.diagram.assetPrompt` | NO | N/A | No |
| `diagram.width` | `bp.diagram.width` | NO | `800` | No |
| `diagram.height` | `bp.diagram.height` | NO | `600` | No |
| `labels` | `bp.labels` | YES | N/A | YES - `.length` on undefined in `renderTrayAndDiagram` L283 |
| `distractorLabels` | `bp.distractorLabels` | NO | `[]` via `?.` | No |
| `dragDropConfig` | `bp.dragDropConfig` | NO | All defaults via `getConfig()` | No |
| `hints` | `bp.hints` | NO | `undefined` | No |
| `zoneGroups` | `bp.zoneGroups` | NO | `undefined` | No |
| `mediaAssets` | `bp.mediaAssets` | NO | `undefined` | No |
| `title` | `bp.title` | NO | `undefined` | No |

### Config Object (DragDropConfig)

All fields optional. `getConfig()` at L45-78 provides comprehensive defaults:
- `interaction_mode`: `'drag_drop'`
- `feedback_timing`: `'immediate'`
- `zone_idle_animation`: `'none'`
- `zone_hover_effect`: `'highlight'`
- `label_style`: `'text'`
- `placement_animation`: `'spring'`
- `leader_line_style`: `'none'`
- `tray_position`: `'bottom'`
- `tray_layout`: `'horizontal'`
- `show_distractors`: based on distractorLabels presence
- `zoom_enabled`: `false`
- `max_attempts`: `0`
- `shuffle_labels`: `true`

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| DD-1 | L170: `bp.diagram.zones.find()` | If `bp.diagram` is undefined | FATAL - TypeError |
| DD-2 | L183: `enrichLabels(..., bp.diagram.zones)` | If `bp.diagram.zones` is undefined | FATAL - `.map()` on undefined |
| DD-3 | L191: `bp.labels` in `generateDefaultAnchors` | If `bp.labels` is undefined | FATAL - passed to function |
| DD-4 | L283: `bp.labels.length` | If `bp.labels` is undefined | FATAL - TypeError |

### Score/Completion Reporting

This component does NOT report score or completion directly. It is a pure UI component -- the parent (via DndContext + onDragEnd handler) controls placement. The `onAction` prop is optional and used for logging only.

### Image Handling

- Uses `bp.diagram.assetUrl` passed to `DiagramCanvas`
- Falls back gracefully if missing (diagram renders without background)

### Multi-Scene Compatibility

GOOD -- Component is stateless with respect to game logic. All state (`placedLabels`, `availableLabels`, etc.) is passed as props. Can be mounted/unmounted between scenes cleanly. No `useEffect` cleanup issues except a single `setTimeout` at L176 for particles (cosmetic, non-fatal if unmounted).

---

## 2. EnhancedSequenceBuilder (sequencing)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/EnhancedSequenceBuilder.tsx`
**Registry key:** `sequencing`
**Config key:** `sequenceConfig`
**Needs DndContext:** NO (manages its own DndContext internally)

### Props Interface

```typescript
interface EnhancedSequenceBuilderProps {
  items: SequenceConfigItem[];                       // REQUIRED
  correctOrder: string[];                            // REQUIRED
  allowPartialCredit?: boolean;                      // OPTIONAL, default true
  config?: SequencingMechanicConfig;                 // OPTIONAL, all fields default
  storeProgress?: { currentOrder: string[]; isSubmitted: boolean; correctPositions: number; totalPositions: number } | null; // OPTIONAL
  onAction: (action: MechanicAction) => ActionResult | null; // REQUIRED
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `items` | `sequenceConfig.items` mapped by registry | YES | N/A | YES - empty renders fine but `.filter()` on undefined crashes |
| `correctOrder` | `sequenceConfig.correctOrder` | YES | N/A | YES - used in `handleSubmit` L407 and `getItemCorrectness` L425 |
| `items[].id` | Each item | YES | N/A | YES - DnD key |
| `items[].text` | Each item | YES | N/A | No (renders empty) |
| `items[].description` | Each item | NO | `undefined` | No |
| `items[].image` | Each item | NO | `undefined` | No |
| `items[].icon` | Each item | NO | `undefined` | No |
| `items[].category` | Each item | NO | `undefined` | No |
| `items[].is_distractor` | Each item | NO | `false` | No |

### Config Object (SequencingMechanicConfig)

All fields optional. Defaults applied at L329-346:
- `layout_mode`: `'horizontal_timeline'`
- `interaction_pattern`: `'drag_to_reorder'`
- `direction`: `'left_to_right'`
- `card_type`: `'text_only'`
- `card_size`: `'medium'`
- `show_description`: `true`
- `connector_style`: `'arrow'`
- `show_position_numbers`: `true`
- `show_endpoints`: `false`
- `is_cyclic`: `false`
- `instruction_text`: `'Arrange the steps in the correct order.'`

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| SQ-1 | L354-363: useState initializer | If `validItems` is empty AND `storeProgress.currentOrder` is empty, `shuffleArray([])` returns `[]`. Renders empty. | LOW - no crash but UX confusion |
| SQ-2 | L396: `onAction({ type: 'reorder', ... })` | If `onAction` returns null | LOW - null handled at L406 with `??` |
| SQ-3 | L455: `result.correctPositions / result.totalPositions` | If `totalPositions` is 0 (empty items) | FATAL - Division by zero renders NaN% |
| SQ-4 | Registry L250: `sequenceConfig.items.map()` | If `sequenceConfig` is defined but `items` is undefined/null | FATAL - `.map()` on undefined |

### Score/Completion Reporting

- Dispatches `{ type: 'submit_sequence', mechanic: 'sequencing' }` action via `onAction`
- Uses `ActionResult.data.correctPositions` / `ActionResult.data.totalPositions` for visual feedback
- Completion detected by store via `isSubmitted && correctPositions === totalPositions`

### Image Handling

- Supports `item.image` for `image_and_text`/`image_only` card types
- No crash if image URL missing -- simply doesn't render image section

### Multi-Scene Compatibility

MODERATE -- Contains internal `useState` for `items` (shuffled order), `isSubmitted`, `result`, `activeId`. These reset on remount but the `items` state initializer at L354 uses closure over `validItems` which comes from props. If props change without remount (same component instance, different scene data), the internal state will be STALE. Fix: Add `key` prop on parent to force remount.

---

## 3. EnhancedSortingCategories (sorting_categories)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/EnhancedSortingCategories.tsx`
**Registry key:** `sorting_categories`
**Config key:** `sortingConfig`
**Needs DndContext:** NO (manages its own DndContext internally)

### Props Interface

```typescript
interface EnhancedSortingProps {
  items: SortingItem[];                              // REQUIRED
  categories: SortingCategory[];                     // REQUIRED
  config?: SortingConfig;                            // OPTIONAL
  storeProgress?: { itemCategories: Record<string, string | null>; isSubmitted: boolean; correctCount: number; totalCount: number } | null; // OPTIONAL
  onAction: (action: MechanicAction) => ActionResult | null; // REQUIRED
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `items` | `sortingConfig.items` | YES | `[]` via registry | No crash but empty game |
| `categories` | `sortingConfig.categories` | YES | `[]` via registry | No crash but no drop targets |
| `items[].id` | Each item | YES | N/A | YES - DnD key |
| `items[].text` | Each item | YES | N/A | No (renders empty) |
| `items[].correctCategoryId` | Each item | YES | N/A | YES - used in `correctItemIds` computation L347-349 |
| `items[].correct_category_ids` | Each item | NO | falls back to `[item.correctCategoryId]` | No |
| `categories[].id` | Each category | YES | N/A | YES - used as droppable ID |
| `categories[].label` | Each category | YES | N/A | No (renders empty) |

### Config Object (SortingConfig)

Key fields read directly from `config` prop:
- `sort_mode`: `'bucket'` (also supports `'venn_2'`)
- `item_card_type`: `'text_only'`
- `submit_mode`: `'batch_submit'`
- `instructions`: `'Sort the items into the correct categories.'`

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| SC-1 | L324: `Object.fromEntries(allItems.map(...))` | If `allItems` is undefined/null | FATAL - `.map()` on null |
| SC-2 | L347: `allItems.forEach(item => { const correctCats = item.correct_category_ids || [item.correctCategoryId]; ... })` | If item has neither `correct_category_ids` nor `correctCategoryId` | LOW - `correctCats` becomes `[undefined]`, `.includes()` never matches |
| SC-3 | L435: `categories.length >= 2` in Venn check | If `categories` is `[]` and `sort_mode` is `'venn_2'` | LOW - No crash, falls through to empty bucket grid |
| SC-4 | L218: `VennDiagram2` destructures `const [cat1, cat2] = categories` | If `categories.slice(0, 2)` has < 2 items | FATAL - cat1/cat2 undefined, `getCategoryColor(cat1, 0)` crashes |
| SC-5 | L482: `correctItemIds.size === allItems.length` | If `allItems` is empty | LOW - Shows "All items sorted correctly!" for empty game |

### Score/Completion Reporting

- Dispatches `{ type: 'sort', mechanic: 'sorting_categories', itemId, categoryId }` on each drag
- Dispatches `{ type: 'submit_sorting', mechanic: 'sorting_categories' }` on submit
- Local visual feedback via `correctItemIds` set (computed from placements vs correct categories)

### Multi-Scene Compatibility

MODERATE -- Same issue as sequencing: internal useState for `placements`, `isSubmitted`, `activeId`. If props change without remount, internal state is stale. The `placements` initializer at L324 uses closure over `allItems`. Needs `key` prop on parent for clean scene transitions.

---

## 4. EnhancedMemoryMatch (memory_match)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/EnhancedMemoryMatch.tsx`
**Registry key:** `memory_match`
**Config key:** `memoryMatchConfig`
**Needs DndContext:** NO

### Props Interface

```typescript
interface EnhancedMemoryMatchProps {
  config: MemoryMatchConfig;                         // REQUIRED (not optional!)
  storeProgress?: { matchedPairIds: string[]; attempts: number; totalPairs: number } | null; // OPTIONAL
  onAction?: (action: MechanicAction) => ActionResult | null; // OPTIONAL
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `config` | `memoryMatchConfig` | YES | N/A | FATAL - destructured at L520-530 |
| `config.pairs` | `memoryMatchConfig.pairs` | YES | N/A | FATAL - `.forEach()` at L547 |
| `config.pairs[].id` | Each pair | YES | N/A | YES - used as card `pairId` |
| `config.pairs[].front` | Each pair | YES | N/A | YES - card content |
| `config.pairs[].back` | Each pair | YES | N/A | YES - card content |
| `config.pairs[].frontType` | Each pair | YES | N/A | YES - determines text vs image rendering |
| `config.pairs[].backType` | Each pair | YES | N/A | YES - determines text vs image rendering |
| `config.pairs[].explanation` | Each pair | NO | `undefined` | No |
| `config.gridSize` | Optional | NO | auto-calculated from pair count | No |
| `config.flipDurationMs` | Optional | NO | `400` | No |
| `config.instructions` | Optional | NO | `'Find all matching pairs by flipping cards.'` | No |
| `config.game_variant` | Optional | NO | classic grid mode | No |

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| MM-1 | L520: `const { pairs, ... } = config` | If `config` is undefined/null | FATAL - destructuring null |
| MM-2 | L547: `pairs.forEach((pair) => { ... })` | If `pairs` is undefined/null | FATAL - `.forEach()` on null |
| MM-3 | L597: `gridSize[0], gridSize[1]` | If `gridSize` is defined but not a 2-element array | MEDIUM - undefined values |
| MM-4 | L253: `pairs.map(p => ...)` in ColumnMatchMode | If `pairs` is empty | LOW - renders empty columns |
| MM-5 | Registry L368: `ctx.blueprint.memoryMatchConfig ?? { pairs: [] }` | Fallback provides `{ pairs: [] }` which is safe for destructuring but yields empty game | LOW |
| MM-6 | L308: `leftPairId === rightPairId` comparison in ColumnMatchMode | Assumes `pairId` on left items matches `pairId` on right items for correctness | No crash but semantic assumption |

### Score/Completion Reporting

- Dispatches `{ type: 'memory_attempt', mechanic: 'memory_match' }` on each flip-pair attempt
- Dispatches `{ type: 'match_pair', mechanic: 'memory_match', pairId }` on successful match
- Completion detected locally at L703: `matchedPairIds.size === pairs.length`
- ColumnMatchMode dispatches `match_pair` per correct connection at L313

### Image Handling

- `pair.frontType === 'image'` renders `<img src={pair.front}>` -- crashes silently if URL invalid (broken image icon)
- Same for `pair.backType === 'image'` with `pair.back`

### Multi-Scene Compatibility

MODERATE -- Heavy internal state: `cardStates`, `flippedCards`, `matchedPairIds`, `attempts`, `showParticles`, `currentExplanation`. All initialized from `storeProgress` on mount (L574-591). But the `cards` memo at L545 uses `pairs` from config -- if config changes without remount, cards will update but `cardStates` won't match new `instanceId`s. Needs `key` prop.

**Critical Issue:** `isCheckingRef` (L593) is never reset on unmount. If component is unmounted during a check timeout, the timeout callback will fire on a stale closure. The `setTimeout` at L625/L645 will fire after unmount -- no crash (React handles gracefully) but potential memory leak.

---

## 5. EnhancedHotspotManager (click_to_identify)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/EnhancedHotspotManager.tsx`
**Registry key:** `click_to_identify`
**Config key:** `clickToIdentifyConfig`
**Needs DndContext:** NO

### Props Interface

```typescript
interface EnhancedHotspotManagerProps {
  zones: Zone[];                                     // REQUIRED
  prompts: IdentificationPrompt[];                   // REQUIRED
  config?: ClickToIdentifyConfig;                    // OPTIONAL
  assetUrl?: string;                                 // OPTIONAL
  width?: number;                                    // OPTIONAL, default 800
  height?: number;                                   // OPTIONAL, default 600
  progress?: { currentPromptIndex: number; completedZoneIds: string[]; incorrectAttempts: number } | null; // OPTIONAL
  onAction: (action: MechanicAction) => ActionResult | null; // REQUIRED
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `zones` | `blueprint.diagram.zones` | YES | N/A | YES - `.map()` at L362 |
| `prompts` | `blueprint.identificationPrompts` | YES (semantic) | `[]` via registry | No crash but no prompts |
| `prompts[].zoneId` | Each prompt | YES | N/A | No crash (just no zone match) |
| `prompts[].prompt` | Each prompt | YES | N/A | Renders undefined text |
| `prompts[].order` | Each prompt | NO | `0` | No |
| `config` | `clickToIdentifyConfig` | NO | defaults via destructuring L225-233 | No |
| `assetUrl` | `blueprint.diagram.assetUrl` | NO | No image rendered | No |
| `progress` | External store | NO | defaults to index 0, empty completed | No |
| `zones[].shape` | Each zone | NO | defaults to circle | No |
| `zones[].points` | Each zone (polygon) | Only if `shape === 'polygon'` | N/A | No crash (skips polygon rendering) |
| `zones[].x`, `zones[].y` | Each zone | NO | `50` fallback | No |

### Config Object (ClickToIdentifyConfig)

All fields optional, defaults at L225-233:
- `promptStyle`: `'naming'`
- `selectionMode`: `'sequential'`
- `highlightStyle`: `'subtle'`
- `magnificationEnabled`: `false`
- `magnificationFactor`: `2.5`
- `showZoneCount`: `true`
- `instructions`: `undefined`

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| CI-1 | L362: `zones.map(zone => ...)` | If `zones` is undefined | FATAL - `.map()` on undefined |
| CI-2 | L253: `[...prompts].sort(...)` | If `prompts` is undefined | FATAL - spread on undefined |
| CI-3 | L257: `sortedPrompts[currentPromptIndex]` | If `currentPromptIndex >= sortedPrompts.length` | LOW - `currentPrompt` is undefined, PromptBanner not rendered |
| CI-4 | L282: `findZoneAtPoint(pctX, pctY, zones)` | If zones have no position data | LOW - findZoneAtPoint returns null |
| CI-5 | L258: `completedZoneIds.size >= sortedPrompts.length` | If `sortedPrompts` is empty | LOW - Immediately shows completion |

### Score/Completion Reporting

- Dispatches `{ type: 'identify', mechanic: 'click_to_identify', zoneId }` on zone click
- Uses `ActionResult.isCorrect` for transient visual feedback (incorrect flash)
- Completion derived from progress: `completedZoneIds.size >= sortedPrompts.length`
- Component is FULLY externally driven -- all persistent state comes from `progress` prop

### Multi-Scene Compatibility

EXCELLENT -- The cleanest component. All persistent state (`completedZoneIds`, `currentPromptIndex`) comes from the `progress` prop (source of truth). Internal state is purely transient (hover, incorrect flash, cursor position). Can be mounted/unmounted freely between scenes.

---

## 6. EnhancedPathDrawer (trace_path)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/EnhancedPathDrawer.tsx`
**Registry key:** `trace_path`
**Config key:** `tracePathConfig`
**Needs DndContext:** NO

### Props Interface

```typescript
interface EnhancedPathDrawerProps {
  zones: Zone[];                                     // REQUIRED
  paths: TracePath[];                                // REQUIRED
  config?: TracePathConfig;                          // OPTIONAL
  assetUrl?: string;                                 // OPTIONAL
  width?: number;                                    // OPTIONAL, default 800
  height?: number;                                   // OPTIONAL, default 600
  traceProgress?: TracePathProgress | null;          // OPTIONAL
  onAction: (action: MechanicAction) => ActionResult | null; // REQUIRED
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `zones` | `blueprint.diagram.zones` | YES | N/A | YES - `.find()` in many places |
| `paths` | `blueprint.paths` | YES | `[]` via registry | No crash but empty game |
| `paths[].id` | Each path | YES | N/A | YES - key for pathProgressMap |
| `paths[].waypoints` | Each path | YES | N/A | YES - `.sort()` at L698 |
| `paths[].waypoints[].zoneId` | Each waypoint | YES | N/A | YES - zone lookup |
| `paths[].waypoints[].order` | Each waypoint | YES | N/A | YES - sorting |
| `paths[].description` | Each path | YES | N/A | Renders undefined text |
| `paths[].requiresOrder` | Each path | YES | N/A | Falls back to falsy (any-order) |
| `traceProgress` | External store | NO | defaults to index 0, empty visited | No |
| `zones[].x`, `zones[].y` | Each zone | NO | `50` fallback | No |

### Config Object (TracePathConfig)

All optional, defaults at L654-665:
- `pathType`: `'linear'`
- `drawingMode`: `'click_waypoints'`
- `particleTheme`: `'dots'`
- `particleSpeed`: `'medium'`
- `colorTransitionEnabled`: `false`
- `showDirectionArrows`: `true`
- `showWaypointLabels`: `true`
- `showFullFlowOnComplete`: `true`
- `submitMode`: `'immediate'`

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| TP-1 | L698: `[...currentPath.waypoints].sort(...)` | If `currentPath.waypoints` is undefined | FATAL - spread on undefined |
| TP-2 | L891: `zones.find(z => z.id === prevWp.zoneId)` | If zones is undefined | FATAL - `.find()` on undefined |
| TP-3 | L693: `currentPath = paths[currentPathIndex]` | If `currentPathIndex >= paths.length` | LOW - `currentPath` is undefined, most sections skip |
| TP-4 | L675: `paths.forEach(p => { base[p.id] = ... })` | If `paths` is undefined | FATAL |
| TP-5 | L1065: `paths.every(p => pathProgressMap[p.id]?.complete)` | If `pathProgressMap` is missing a path ID | LOW - `?.complete` handles undefined |
| TP-6 | L826: `isVisited(zoneId)` via `currentProgress?.visited.includes(zoneId)` | If `visited` is undefined inside progress | MEDIUM - `.includes()` on undefined |
| TP-7 | FlowingParticles L441-476: `requestAnimationFrame` loop | Never cancelled if paths change while mounted | LOW - memory leak, no crash |

### Score/Completion Reporting

- Immediate mode: dispatches `{ type: 'visit_waypoint', mechanic: 'trace_path', pathId, zoneId }` per click
- Batch mode: dispatches `{ type: 'submit_path', mechanic: 'trace_path', pathId, selectedZoneIds }` on submit
- Completion: `paths.every(p => pathProgressMap[p.id]?.complete)`

### Multi-Scene Compatibility

MODERATE -- Transient state (`feedbackMessage`, `showCompletionFlow`, batch selection state) is local. Persistent state comes from `traceProgress` prop. However, `FlowingParticles` starts a `requestAnimationFrame` loop that references `pathPoints` from zones. If zones change without remount, particles animate on stale positions. Needs `key` prop.

---

## 7. DescriptionMatcher (description_matching)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/DescriptionMatcher.tsx`
**Registry key:** `description_matching`
**Config key:** `descriptionMatchingConfig`
**Needs DndContext:** NO (manages own DndContext for drag_description mode)

### Props Interface

```typescript
interface DescriptionMatcherProps {
  zones: Zone[];                                     // REQUIRED
  labels: Label[];                                   // REQUIRED
  descriptions?: Record<string, string>;             // OPTIONAL
  mode?: 'click_zone' | 'drag_description' | 'multiple_choice'; // OPTIONAL, default 'click_zone'
  showHints?: boolean;                               // OPTIONAL, default false
  storeProgress?: { currentIndex: number; matches: MatchResult[]; mode: string } | null; // OPTIONAL
  onAction?: (action: MechanicAction) => ActionResult | null; // OPTIONAL
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `zones` | `blueprint.diagram.zones` | YES | N/A | YES - used in all 3 modes |
| `labels` | `blueprint.labels` | YES | N/A | Not used in most modes (only registry passes it) |
| `zones[].id` | Each zone | YES | N/A | YES - comparison key |
| `zones[].label` | Each zone | YES | N/A | Renders empty text |
| `zones[].description` | Each zone | YES (semantic) | filtered out if missing | No crash but empty game |
| `zones[].hint` | Each zone | NO | `undefined` | No |
| `descriptions` | `descriptionMatchingConfig.descriptions` | NO | Falls back to zone.description | No |
| `zones[].x`, `zones[].y` | Each zone | Only for drag_description mode | `50` fallback in DroppableZone L415-416 | No |
| `zones[].radius` | Each zone | Only for drag_description mode | `30` fallback in DroppableZone L416-419 | No |

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| DM-1 | L74-83: `zonesWithDescriptions` | If `zones` is undefined | FATAL - `.filter()` on undefined |
| DM-2 | L98: `currentZone = shuffledZones[currentIndex]` | If `currentIndex >= shuffledZones.length` (all zones exhausted) | LOW - `currentZone` is undefined |
| DM-3 | L101: `if (!currentZone) return` in handleZoneClick | Safely handled | No crash |
| DM-4 | L228-238: `useMemo` for MC options | `zones.filter(z => z.id !== correct.id && z.description)` -- if zones have no descriptions, only 1 option (the correct one) | LOW - poor UX |
| DM-5 | L229: `if (!currentZone) return []` | Safe guard | No crash |
| DM-6 | L415: DroppableZone uses `zone.x`, `zone.y`, `zone.radius` as pixel positions | These are PERCENTAGE values in the Zone type (0-100) but treated as pixel offsets in `style={{ left: (zone.x ?? 50) - (zone.radius || 30) }}` | BUG - zones render at wrong positions in drag mode |
| DM-7 | L304: `matchedPairs` state used in drag_description mode | Defined OUTSIDE the mode branch (unconditional `useState`) but only used in drag mode | LOW - wasted state but no crash |

### Score/Completion Reporting

- Dispatches `{ type: 'description_match', mechanic: 'description_matching', labelId: currentZone.id, zoneId }` for each attempt
- Uses `ActionResult.isCorrect` to determine local feedback
- Completion: detected by store when `currentIndex >= totalDescriptions`

### Multi-Scene Compatibility

POOR -- Heavy internal state: `currentIndex`, `matches`, `feedback`, `selectedZone`, `matchedPairs`, `dragFeedback`, `activeDragId`. The `shuffleOrderRef` at L87 persists across re-renders but is NOT reset on prop changes. If zones change without remount, `shuffleOrderRef` may reference stale zone IDs. Needs `key` prop.

**Bug DM-6 is critical:** In `drag_description` mode, `DroppableZone` renders zones using `zone.x` and `zone.y` as pixel-like offsets in CSS `left`/`top`, but these are 0-100 percentage values in the `Zone` type. This makes drag-mode zones render at completely wrong positions. Other components (EnhancedHotspotManager, EnhancedPathDrawer) correctly use `${zoneX}%` with percentage units.

---

## 8. BranchingScenario (branching_scenario)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/BranchingScenario.tsx`
**Registry key:** `branching_scenario`
**Config key:** `branchingConfig`
**Needs DndContext:** NO

### Props Interface

```typescript
interface BranchingScenarioProps {
  nodes: DecisionNode[];                             // REQUIRED
  startNodeId: string;                               // REQUIRED
  showPathTaken?: boolean;                           // OPTIONAL, default true
  allowBacktrack?: boolean;                          // OPTIONAL, default true
  showConsequences?: boolean;                        // OPTIONAL, default true
  multipleValidEndings?: boolean;                    // OPTIONAL, default false
  instructions?: string;                             // OPTIONAL
  pointsPerDecision?: number;                        // OPTIONAL, default 10
  timingConfig?: { consequenceDisplayMs?: number; quickTransitionMs?: number }; // OPTIONAL
  storeProgress?: { currentNodeId: string; pathTaken: Array<{ nodeId: string; optionId: string; isCorrect: boolean }> } | null; // OPTIONAL
  onAction?: (action: MechanicAction) => ActionResult | null; // OPTIONAL
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `nodes` | `branchingConfig.nodes` | YES | `[]` via registry | No crash but `currentNode` is undefined |
| `startNodeId` | `branchingConfig.startNodeId` | YES | `''` via registry | No crash but node not found |
| `nodes[].id` | Each node | YES | N/A | YES - `.find()` comparison |
| `nodes[].question` | Each node | YES | N/A | Renders undefined |
| `nodes[].options` | Each node | YES | N/A | YES - `.map()` at L241 |
| `nodes[].options[].id` | Each option | YES | N/A | YES - key and selection |
| `nodes[].options[].text` | Each option | YES | N/A | Renders undefined |
| `nodes[].options[].nextNodeId` | Each option | PARTIAL | `null` for end nodes | No crash |
| `nodes[].options[].isCorrect` | Each option | NO | `true` via `?? true` at L107 | No |
| `nodes[].options[].consequence` | Each option | NO | `undefined` | No |
| `nodes[].isEndNode` | Each node | NO | `false` | No |
| `nodes[].endMessage` | Each node | NO | `undefined` | No |
| `nodes[].imageUrl` | Each node | NO | `undefined` | No |

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| BR-1 | L87: `nodes.find((n) => n.id === currentNodeId)` | If `nodes` is undefined | FATAL - `.find()` on undefined |
| BR-2 | L163: `if (!currentNode)` guard | Returns error paragraph | HANDLED - graceful degradation |
| BR-3 | L97: `currentNode.options.find((o) => o.id === selectedOption)` | If `currentNode.options` is undefined | FATAL - `.find()` on undefined |
| BR-4 | L120-121: `nodes.find(n => n.id === option.nextNodeId)` | If `option.nextNodeId` is invalid string (not null, but no matching node) | LOW - `targetNode` is undefined, `reachedEnd` falls through |
| BR-5 | L147: `pathTaken[pathTaken.length - 1]` in handleBacktrack | If `pathTaken` was just sliced to empty | SAFE - guarded by `newPath.length === 0` check |
| BR-6 | Registry L405: `config?.nodes ?? []` | If `branchingConfig` is undefined, `nodes` is `[]` | LOW - empty nodes, "Node not found" error message |
| BR-7 | Registry L406: `config?.startNodeId ?? ''` | Empty string won't match any node | LOW - shows "Node not found" error |

### Score/Completion Reporting

- Dispatches `{ type: 'branching_choice', mechanic: 'branching_scenario', nodeId, optionId, isCorrect, nextNodeId }` per choice
- Dispatches `{ type: 'branching_undo', mechanic: 'branching_scenario' }` on backtrack
- Local completion: `isComplete` state set when `nextNodeId === null` or `isEndNode === true`

### Multi-Scene Compatibility

MODERATE -- Internal state: `currentNodeId`, `pathTaken`, `selectedOption`, `showFeedback`, `isComplete`. Initialized from `storeProgress` on mount. Props-driven `startNodeId` is used in `handleReset` but the initial mount reads `storeProgress?.currentNodeId ?? startNodeId`. Needs `key` prop for clean scene transitions.

---

## 9. CompareContrast (compare_contrast)

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/CompareContrast.tsx`
**Registry key:** `compare_contrast`
**Config key:** `compareConfig`
**Needs DndContext:** NO

### Props Interface

```typescript
interface CompareContrastProps {
  diagramA: ComparableDiagram;                       // REQUIRED
  diagramB: ComparableDiagram;                       // REQUIRED
  expectedCategories: Record<string, 'similar' | 'different' | 'unique_a' | 'unique_b'>; // REQUIRED
  highlightMatching?: boolean;                       // OPTIONAL, default true
  instructions?: string;                             // OPTIONAL
  storeProgress?: { categorizations: Record<string, string>; isSubmitted: boolean; correctCount: number; totalCount: number } | null; // OPTIONAL
  onAction?: (action: MechanicAction) => ActionResult | null; // OPTIONAL
}
```

### Data Shape Expected

| Field | Source | Required | Default | Crash if missing |
|-------|--------|----------|---------|-----------------|
| `diagramA` | `compareConfig.diagramA` | YES | N/A | YES - `.zones.map()` at L145 |
| `diagramB` | `compareConfig.diagramB` | YES | N/A | YES - same as above |
| `diagramA.id` | Required | YES | N/A | No crash |
| `diagramA.name` | Required | YES | N/A | Renders empty |
| `diagramA.imageUrl` | Required | YES | N/A | Broken image |
| `diagramA.zones` | Required | YES | N/A | YES - `.map()` at L145 |
| `diagramA.zones[].id` | Each zone | YES | N/A | YES - categorization key |
| `diagramA.zones[].label` | Each zone | YES | N/A | Renders empty |
| `diagramA.zones[].x` | Each zone | YES | N/A | Zone at wrong position |
| `diagramA.zones[].y` | Each zone | YES | N/A | Zone at wrong position |
| `diagramA.zones[].width` | Each zone | YES | N/A | Zone invisible (0px) |
| `diagramA.zones[].height` | Each zone | YES | N/A | Zone invisible (0px) |
| `expectedCategories` | `compareConfig.expectedCategories` | YES | N/A | YES - used in submit and rendering |

### Crash Points

| # | Location | Condition | Severity |
|---|----------|-----------|----------|
| CC-1 | L83-86: `allZones = [...diagramA.zones.map(...), ...diagramB.zones.map(...)]` | If `diagramA.zones` or `diagramB.zones` is undefined | FATAL - `.map()` on undefined |
| CC-2 | L145: `diagram.zones.map((zone) => ...)` | If `diagram.zones` is undefined | FATAL |
| CC-3 | L184: `Object.keys(expectedCategories).length` | If `expectedCategories` is undefined | FATAL - `Object.keys()` on undefined |
| CC-4 | L261: `result.score` displayed as percentage | `result.score` is always `0` (hardcoded at L118) | BUG - shows "0%" always |
| CC-5 | Registry L452: `config.diagramA` check | If compareConfig exists but `diagramA` is null | Falls through to legacy stub, which fabricates data from diagram zones | HANDLED |
| CC-6 | Registry L464-487: Legacy stub | Creates fake diagramA/B from blueprint zones. Zone `width`/`height` computed as `(z.radius || 5) * 2` but radius is in 0-100 percentage units, not pixels. May produce zones with width/height of 60+ percent. | BUG - oversized zones |

### Score/Completion Reporting

- Dispatches `{ type: 'categorize', mechanic: 'compare_contrast', zoneId, category }` per categorization
- Dispatches `{ type: 'submit_compare', mechanic: 'compare_contrast' }` on submit
- Uses `ActionResult.data.correctCount` and `ActionResult.data.totalCount` for visual feedback
- **BUG CC-4:** `result.score` is hardcoded to `0` at L118, so the percentage display always shows "0%"

### Image Handling

- Requires `diagramA.imageUrl` and `diagramB.imageUrl` -- renders broken images if missing
- No fallback for missing images

### Multi-Scene Compatibility

MODERATE -- Internal state: `categorizations`, `selectedZone`, `isSubmitted`, `result`. Initialized from `storeProgress` on mount. Needs `key` prop for scene transitions.

---

## 10. Cross-Component Pattern Analysis

### Shared Patterns

| Pattern | Components Using | Description |
|---------|-----------------|-------------|
| `onAction` dispatch | ALL 9 | V4 unified action dispatch. Returns `ActionResult | null`. |
| `storeProgress` prop | 8 of 9 (all except drag_drop) | External source-of-truth for restoring state on mount. |
| Internal DndContext | Sequencing, Sorting, DescriptionMatcher (drag mode) | These create their own `DndContext` despite MechanicRouter's external wrapper. |
| External DndContext | DragDrop, Hierarchical | Wrapped by MechanicRouter's `DndContext`. |
| Progress-driven state | Hotspot, PathDrawer | ALL persistent state derives from `progress`/`traceProgress` prop. Best pattern. |
| State-initialized-from-progress | Sequencing, Sorting, MemoryMatch, Branching, Compare | Internal `useState` seeded from `storeProgress` on mount, then local state takes over. |

### Divergent Interfaces

| Aspect | DragDrop | Others |
|--------|----------|--------|
| Config location | `blueprint.dragDropConfig` at blueprint root | Various `Config` objects |
| State management | Fully external (props-driven) | Internal state initialized from storeProgress |
| Score reporting | None (parent handles) | Via `onAction` dispatch |
| DndContext | External (from MechanicRouter) | Internal or none |

### Action Type Map

| Component | Action Types Emitted |
|-----------|---------------------|
| DragDrop | `place`, `remove` (emitted by parent, not component) |
| Sequencing | `reorder`, `submit_sequence` |
| Sorting | `sort`, `unsort`, `submit_sorting` |
| MemoryMatch | `memory_attempt`, `match_pair` |
| Hotspot | `identify` |
| PathDrawer | `visit_waypoint`, `submit_path` |
| DescriptionMatcher | `description_match` |
| Branching | `branching_choice`, `branching_undo` |
| CompareContrast | `categorize`, `submit_compare` |

---

## 11. Gap Analysis: Backend vs Frontend Contracts

### What the Backend MUST Provide per Mechanic

#### drag_drop
- `blueprint.diagram.zones[]` with `id`, `label`, `x`, `y` (required)
- `blueprint.labels[]` with `id`, `text`, `correctZoneId` (required)
- `blueprint.dragDropConfig` (optional, all defaults exist)
- `blueprint.diagram.assetUrl` (optional but expected)
- `blueprint.distractorLabels[]` (optional)

#### sequencing
- `blueprint.sequenceConfig.items[]` with `id`, `text` (required)
- `blueprint.sequenceConfig.correctOrder: string[]` with matching item IDs (required)
- `blueprint.sequenceConfig.items` must NOT be empty or undefined
- Items can optionally have: `description`, `image`, `icon`, `category`, `is_distractor`
- Config: `layout_mode`, `card_type`, `connector_style`, etc. (all optional)

#### sorting_categories
- `blueprint.sortingConfig.items[]` with `id`, `text`, `correctCategoryId` (required)
- `blueprint.sortingConfig.categories[]` with `id`, `label` (required)
- Items can optionally have: `correct_category_ids`, `description`, `image`, `difficulty`
- Categories can optionally have: `description`, `color`
- Both arrays must NOT be empty if mechanic is active

#### memory_match
- `blueprint.memoryMatchConfig.pairs[]` with `id`, `front`, `back`, `frontType`, `backType` (ALL required)
- `frontType`/`backType` must be `'text'` or `'image'`
- Pairs can optionally have: `explanation`, `category`
- Config optional: `gridSize`, `flipDurationMs`, `game_variant`, etc.
- If `game_variant === 'column_match'`, different UI renders (two columns instead of grid)

#### click_to_identify
- `blueprint.diagram.zones[]` with `id`, `label` (required)
- `blueprint.identificationPrompts[]` with `zoneId`, `prompt` (required, must not be empty)
- `blueprint.diagram.assetUrl` (optional but expected for the diagram)
- `blueprint.clickToIdentifyConfig` (optional, all defaults exist)
- Zones need `shape`, `points` (if polygon), `x`/`y`/`radius` (if circle) for hit detection

#### trace_path
- `blueprint.diagram.zones[]` with `id`, `label`, `x`, `y` (required for waypoint rendering)
- `blueprint.paths[]` with `id`, `waypoints[]`, `description`, `requiresOrder` (required)
- Each waypoint needs `zoneId` (must match a zone.id) and `order` (integer for sorting)
- `blueprint.tracePathConfig` (optional, all defaults exist)
- `blueprint.diagram.assetUrl` (optional but expected)

#### description_matching
- `blueprint.diagram.zones[]` with `id`, `label`, `description` (description REQUIRED for zones to appear)
- Zones WITHOUT descriptions are silently filtered out
- `blueprint.descriptionMatchingConfig.descriptions` (optional override map: `Record<string, string>`)
- `blueprint.descriptionMatchingConfig.mode` (optional, default `'click_zone'`)
- For `drag_description` mode: zones need `x`, `y`, `radius` -- but **BUG DM-6** means they render wrong

#### branching_scenario
- `blueprint.branchingConfig.nodes[]` with `id`, `question`, `options[]` (required)
- `blueprint.branchingConfig.startNodeId` matching a node ID (required)
- Each option needs: `id`, `text`, `nextNodeId` (null for ending options)
- Options can optionally have: `isCorrect`, `consequence`, `points`
- At least one node must have `isEndNode: true` or an option with `nextNodeId: null`

#### compare_contrast
- `blueprint.compareConfig.diagramA` with `id`, `name`, `imageUrl`, `zones[]` (required)
- `blueprint.compareConfig.diagramB` with same structure (required)
- `blueprint.compareConfig.expectedCategories: Record<string, category>` (required)
- Each zone needs: `id`, `label`, `x`, `y`, `width`, `height` (ALL required for rendering)
- Zone positions are percentages (0-100) used in CSS `${zone.x}%`

### Current Backend Output Gaps

Based on the blueprint_assembler_tools.py grep results, the backend builds configs for all mechanics. However, common failure modes include:

1. **Empty arrays:** Backend may set `items: []` or `pairs: []` when agent doesn't generate content
2. **Missing required fields:** Backend repair functions (`_repair_blueprint`) may not catch all cases
3. **Type mismatches:** Backend uses `frontType`/`backType` which must be exactly `'text'` or `'image'`
4. **Missing zone cross-references:** Waypoint `zoneId` must exactly match a zone ID in `diagram.zones`
5. **Empty `startNodeId`:** Registry fallback is `''` which won't match any node

---

## 12. Complete Crash Path Catalog

### FATAL Crashes (TypeError/ReferenceError)

| ID | Component | File:Line | Condition | Fix Required |
|----|-----------|-----------|-----------|-------------|
| DD-1 | DragDrop | EnhancedDragDropGame.tsx:170 | `bp.diagram` undefined | Guard check |
| DD-2 | DragDrop | EnhancedDragDropGame.tsx:183 | `bp.diagram.zones` undefined | Guard check |
| DD-4 | DragDrop | EnhancedDragDropGame.tsx:283 | `bp.labels` undefined | Guard check |
| SQ-4 | Sequencing | mechanicRegistry.ts:250 | `sequenceConfig.items` undefined | Registry guard |
| SC-1 | Sorting | EnhancedSortingCategories.tsx:324 | `allItems` (items prop) undefined | Props guard |
| SC-4 | Sorting | EnhancedSortingCategories.tsx:218 | Venn mode with < 2 categories | Category count check |
| MM-1 | MemoryMatch | EnhancedMemoryMatch.tsx:520 | `config` prop undefined | Props guard |
| MM-2 | MemoryMatch | EnhancedMemoryMatch.tsx:547 | `config.pairs` undefined | Config guard |
| CI-1 | Hotspot | EnhancedHotspotManager.tsx:362 | `zones` prop undefined | Props guard |
| CI-2 | Hotspot | EnhancedHotspotManager.tsx:253 | `prompts` prop undefined | Props guard |
| TP-1 | PathDrawer | EnhancedPathDrawer.tsx:698 | `currentPath.waypoints` undefined | Path guard |
| TP-4 | PathDrawer | EnhancedPathDrawer.tsx:675 | `paths` prop undefined | Props guard |
| DM-1 | DescMatcher | DescriptionMatcher.tsx:74 | `zones` prop undefined | Props guard |
| BR-1 | Branching | BranchingScenario.tsx:87 | `nodes` prop undefined | Props guard |
| BR-3 | Branching | BranchingScenario.tsx:97 | `currentNode.options` undefined | Options guard |
| CC-1 | Compare | CompareContrast.tsx:83 | `diagramA.zones` undefined | Props guard |
| CC-3 | Compare | CompareContrast.tsx:184 | `expectedCategories` undefined | Props guard |

### Logic Bugs (Wrong behavior, no crash)

| ID | Component | File:Line | Description |
|----|-----------|-----------|-------------|
| SQ-3 | Sequencing | :455 | Division by zero when `totalPositions === 0` renders NaN% |
| SC-5 | Sorting | :482 | Empty items shows "All items sorted correctly!" |
| DM-6 | DescMatcher | :415-419 | Zone positions in drag mode use percentage values as pixel offsets |
| CC-4 | Compare | :118 | `result.score` hardcoded to `0`, percentage display always shows "0%" |
| CC-6 | Compare | mechanicRegistry.ts:464-487 | Legacy stub creates zones with width/height from radius*2, producing oversized zones |

### Memory Leaks / Timer Issues

| ID | Component | File:Line | Description |
|----|-----------|-----------|-------------|
| MM-LEAK | MemoryMatch | :625,645 | `setTimeout` callbacks fire after unmount |
| TP-LEAK | PathDrawer | :441-476 | `requestAnimationFrame` loop not properly cleaned on prop change |

---

## 13. Proposed Fixes

### Fix 32.1: Add null-safe guards at MechanicRouter/Registry level

**Rationale:** Instead of fixing each component individually, guard at the registry `extractProps` level so components never receive undefined arrays.

**Files:**
- `mechanicRegistry.ts`

**Changes:**
- L167: `zones: ctx.blueprint.diagram?.zones ?? []` (click_to_identify)
- L168: `prompts: ctx.blueprint.identificationPrompts ?? []` (already done, confirmed safe)
- L207: `zones: ctx.blueprint.diagram?.zones ?? []` (trace_path)
- L208: `paths: ctx.blueprint.paths ?? []` (already done, confirmed safe)
- L327: `items: config?.items ?? []` (already done for sorting)
- L328: `categories: config?.categories ?? []` (already done for sorting)
- L368: `config: ctx.blueprint.memoryMatchConfig ?? { pairs: [] }` (already done for memory match)
- L405: `nodes: config?.nodes ?? []` (already done for branching)

**Remaining to fix:**
- DragDrop `extractProps` L128: No guard on `blueprint.diagram` existing
- Sequencing `extractProps` L250: Add `if (sequenceConfig && sequenceConfig.items?.length > 0)` (add `?.`)
- Add `blueprint.labels ?? []` fallback where `bp.labels.length` is used at EnhancedDragDropGame.tsx:283

### Fix 32.2: Division by zero in Sequencing

**File:** `EnhancedSequenceBuilder.tsx`
**Line:** 455
**Change:** `Math.round((result.correctPositions / Math.max(result.totalPositions, 1)) * 100)` (use `Math.max`)
**Same fix at:** L462 (progress bar width)

### Fix 32.3: Venn diagram crash with < 2 categories

**File:** `EnhancedSortingCategories.tsx`
**Line:** 435
**Change:** `{sortMode === 'venn_2' && categories.length >= 2 ? (` -- already correct guard but `VennDiagram2` internally still destructures without checking. Add guard inside `VennDiagram2`:
```typescript
if (categories.length < 2) return null;
const [cat1, cat2] = categories;
```

### Fix 32.4: DescriptionMatcher drag mode zone positioning

**File:** `DescriptionMatcher.tsx`
**Lines:** 415-419
**Current:**
```typescript
style={{
  left: (zone.x ?? 50) - (zone.radius || 30),
  top: (zone.y ?? 50) - (zone.radius || 30),
  width: (zone.radius || 30) * 2,
  height: (zone.radius || 30) * 2,
}}
```
**Fixed:**
```typescript
style={{
  left: `${zone.x ?? 50}%`,
  top: `${zone.y ?? 50}%`,
  width: `${(zone.radius || 4) * 2}%`,
  height: `${(zone.radius || 4) * 2}%`,
  transform: 'translate(-50%, -50%)',
}}
```

### Fix 32.5: CompareContrast score display

**File:** `CompareContrast.tsx`
**Line:** 118
**Current:** `score: 0,`
**Fixed:** `score: totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0,`

### Fix 32.6: Add `key` prop for multi-scene remount

**File:** `MechanicRouter.tsx` or parent `index.tsx`
**Change:** When rendering any mechanic component for a scene/task, add a `key` prop that includes the scene ID and task index to force remount:
```tsx
<MechanicRouter key={`${sceneId}-${taskIndex}-${mode}`} ... />
```
This ensures internal `useState` initializers re-run with new data.

### Fix 32.7: Guard MemoryMatch config destructuring

**File:** `EnhancedMemoryMatch.tsx`
**Line:** 520
**Change:** Add early return if config is empty:
```typescript
const {
  pairs = [],
  gridSize,
  flipDurationMs = 400,
  // ... rest
} = config || { pairs: [] };

if (pairs.length === 0) {
  return <div className="text-center p-8 text-gray-500">No memory match pairs configured.</div>;
}
```

### Fix 32.8: Guard DragDrop blueprint access

**File:** `EnhancedDragDropGame.tsx`
**Lines:** 170, 183, 283
**Change:** Add early return if essential data missing:
```typescript
if (!bp.diagram?.zones?.length || !bp.labels?.length) {
  return <div className="text-center p-8 text-gray-500">No diagram data available.</div>;
}
```

### Fix 32.9: Cleanup timers on MemoryMatch unmount

**File:** `EnhancedMemoryMatch.tsx`
**Lines:** 625, 645
**Change:** Store timeout IDs in refs and clear on unmount:
```typescript
const matchTimeoutRef = useRef<NodeJS.Timeout>();
const mismatchTimeoutRef = useRef<NodeJS.Timeout>();

useEffect(() => {
  return () => {
    if (matchTimeoutRef.current) clearTimeout(matchTimeoutRef.current);
    if (mismatchTimeoutRef.current) clearTimeout(mismatchTimeoutRef.current);
  };
}, []);
```

### Fix 32.10: PathDrawer FlowingParticles cleanup on prop change

**File:** `EnhancedPathDrawer.tsx`
**Lines:** 441-476
**Change:** The `useEffect` return function already calls `cancelAnimationFrame(animRef.current)`. Verify `lastTimeRef` is reset when `pathPoints` change (currently it is not, which causes a large `dt` jump on first frame after change):
```typescript
useEffect(() => {
  lastTimeRef.current = 0; // Reset on dependency change
  // ... rest of animation setup
}, [pathPoints, speedFactor]);
```

### Fix 32.11: BranchingScenario guard options array

**File:** `BranchingScenario.tsx`
**Line:** 97
**Change:** Guard `currentNode.options`:
```typescript
const option = currentNode.options?.find((o) => o.id === selectedOption);
if (!option) return;
```

### Fix 32.12: Backend validation for required fields

**File:** `backend/app/tools/blueprint_assembler_tools.py` (in `_repair_blueprint` function)
**Change:** Add validation checks:
- `sequenceConfig.items` is non-empty array when mechanic is `sequencing`
- `memoryMatchConfig.pairs` is non-empty array with `front`, `back`, `frontType`, `backType` fields
- `branchingConfig.startNodeId` matches an actual node ID
- `compareConfig.diagramA.zones` and `diagramB.zones` are non-empty arrays with `x`, `y`, `width`, `height`
- `identificationPrompts` is non-empty when mechanic is `click_to_identify`
- `paths[].waypoints[].zoneId` references exist in `diagram.zones`

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total components audited | 9 |
| FATAL crash paths | 17 |
| Logic bugs | 5 |
| Memory leak issues | 2 |
| Proposed fixes | 12 |
| Components with clean multi-scene support | 1 (EnhancedHotspotManager) |
| Components needing `key` prop for multi-scene | 7 |
| Components with internal DndContext | 3 |

### Risk Priority Matrix

| Priority | Issue | Impact |
|----------|-------|--------|
| P0 | MM-1/MM-2: MemoryMatch crashes if config/pairs missing | Game unplayable |
| P0 | CC-1: CompareContrast crashes if diagram zones missing | Game unplayable |
| P0 | DD-2/DD-4: DragDrop crashes if zones/labels missing | Game unplayable |
| P1 | DM-6: DescriptionMatcher drag mode renders zones at wrong positions | Mechanic unusable |
| P1 | CC-4: CompareContrast always shows "0%" score | Confusing UX |
| P1 | Multi-scene remount (Fix 32.6) | Stale data between scenes |
| P2 | SQ-3: Division by zero NaN% | Cosmetic bug |
| P2 | SC-4: Venn crash with < 2 categories | Edge case crash |
| P2 | Timer/animation leaks | Performance degradation |
| P3 | SC-5: Empty sorting shows success | Edge case UX |
| P3 | CC-6: Legacy stub oversized zones | Edge case visual bug |
