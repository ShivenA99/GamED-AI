# Frontend Component Audit: Current State vs Research Specifications

**Date:** 2026-02-11
**Scope:** All interactive game components in `frontend/src/components/templates/InteractiveDiagramGame/`
**Reference:** Research documents 01-07 in `docs/audit/research/`

---

## Table of Contents

1. [MechanicRouter.tsx](#1-mechanicroutertsx)
2. [SequenceBuilder.tsx](#2-sequencebuildertsx)
3. [SortingCategories.tsx](#3-sortingcategoriestsx)
4. [MemoryMatch.tsx](#4-memorymatchts)
5. [BranchingScenario.tsx](#5-branchingscenariotsx)
6. [CompareContrast.tsx](#6-comparecontrasttsx)
7. [HotspotManager.tsx](#7-hotspotmanagertsx)
8. [PathDrawer.tsx](#8-pathdrawertsx)
9. [DescriptionMatcher.tsx](#9-descriptionmatchertsx)
10. [DiagramCanvas.tsx](#10-diagramcanvastsx)
11. [types.ts](#11-typests)
12. [useInteractiveDiagramState.ts (Zustand Store)](#12-useinteractivediagramstatets)
13. [Summary Matrix](#13-summary-matrix)

---

## 1. MechanicRouter.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/MechanicRouter.tsx` (451 lines)
**Research Reference:** All research docs (central routing hub)

### Current Capabilities

- Routes to 9 interaction components based on `mode`: drag_drop, click_to_identify, trace_path, description_matching, compare_contrast, sequencing, sorting_categories, memory_match, branching_scenario
- Wraps DnD-requiring mechanics (drag_drop, sorting_categories, description_matching drag mode) in `DndContext`
- Passes per-mechanic config fields from blueprint: `sequenceConfig`, `sortingConfig`, `memoryMatchConfig`, `branchingConfig`, `compareConfig`
- Passes store progress types and callbacks for each mechanic
- Handles `timed_challenge` as a wrapper around any other mode with countdown timer
- SceneTransition overlay for pending mode transitions

### Missing Visual Components

| Component | Research Source | Description |
|-----------|---------------|-------------|
| TimedChallengeWrapper | N/A | Only renders countdown text, no progress bar or urgency styling |

### Missing Interaction Patterns

| Pattern | Research Source | Gap |
|---------|---------------|-----|
| Hierarchical routing | 07_drag_drop_richness.md | `hierarchical` mode falls through to default drag_drop, no dedicated sub-router |

### Missing Configurable Properties

| Property | Research Source | Gap |
|----------|---------------|-----|
| DnD sensors config | 07_drag_drop_richness.md | `useSensors()` hardcodes PointerSensor with 8px activation distance; no keyboard sensor, no touch sensor config |
| Collision detection strategy | 07_drag_drop_richness.md | Hardcoded `closestCenter`; no option for `pointerWithin`, `rectIntersection` |

### Props Gaps

- `descriptionMatchingConfig` is passed to DescriptionMatcher but currently typed as `{ descriptions?: Record<string,string>; mode?: string }` -- too narrow for research specs
- No `clickToIdentifyConfig` prop -- HotspotManager receives no config object, only raw blueprint fields
- No `tracePathConfig` prop -- PathDrawer receives no config object, only `paths` array
- No `dragDropConfig` prop -- DiagramCanvas receives no config object for leader lines, zoom, label style

### New Components Needed

| Component | Purpose |
|-----------|---------|
| None specific to router | Router itself is structurally sound; gaps are in child components |

### Blueprint Field Dependencies

- `blueprint.sequenceConfig` -> SequenceBuilder
- `blueprint.sortingConfig` -> SortingCategories
- `blueprint.memoryMatchConfig` -> MemoryMatch
- `blueprint.branchingConfig` -> BranchingScenario
- `blueprint.compareConfig` -> CompareContrast
- `blueprint.descriptionMatchingConfig` -> DescriptionMatcher
- `blueprint.identificationPrompts` -> HotspotManager
- `blueprint.paths` -> PathDrawer
- Missing: `blueprint.clickToIdentifyConfig`, `blueprint.tracePathConfig`, `blueprint.dragDropConfig`

---

## 2. SequenceBuilder.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/SequenceBuilder.tsx` (319 lines)
**Research Reference:** `01_sequencing_games.md`

### Current Capabilities

- Vertical sortable list using `@dnd-kit/sortable` with `verticalListSortingStrategy`
- `SortableItem` renders: text, optional description, drag handle SVG icon
- Submit button with position-based scoring (exact match per position)
- Results view: green check / red X per item, score display
- Retry support (re-shuffle on retry)
- Store integration via `storeProgress`, `onOrderChange`, `onStoreSubmit` props

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| ItemCard (image_and_text, image_only, icon_and_text, numbered_text) | SequencingMechanicConfig.item_card_config | Text-only rows with drag handle |
| Track/Lane element | SequencingMechanicConfig.layout | No track; items float in a plain div |
| ConnectorLine (arrow, dotted, solid, numbered, animated) | SequencingMechanicConfig.connector_config | No connectors between items |
| Slot placeholder (numbered/lettered) | SequencingMechanicConfig.slot_config | No visible slots; items stack vertically |
| SourceArea | SequencingMechanicConfig.source_area | No separate source area; all items are inline in the sequence |
| RevealAnimation | SequencingMechanicConfig.reveal_mode | No progressive reveal; correct answer shown immediately |
| DistractorItem | SequencingMechanicConfig.distractors | No distractors supported |
| CyclicConnector (loop arrow) | SequencingMechanicConfig.sequenceType=cyclic | No cyclic display |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| Horizontal timeline layout | layout_mode: horizontal_timeline | Only vertical list |
| Circular layout | layout_mode: circular | Not implemented |
| Flowchart layout | layout_mode: flowchart | Not implemented |
| Insert-between interaction | layout_mode: insert_between | Not implemented |
| Click-to-swap | interaction_pattern: click_to_swap | Only drag-to-reorder |
| Click-to-select ordering | interaction_pattern: click_to_select | Not implemented |
| Number-typing ordering | interaction_pattern: number_input | Not implemented |
| Drag from source area to slots | source_area + slots | Not implemented |
| Progressive reveal of correct positions | reveal_mode: progressive | Batch reveal only |
| Cascade correct animation | reveal_mode: cascade | Not implemented |
| Partial credit granularity | Kendall tau / longest subsequence | Simple position-match count |
| Micro-interactions (snap, wiggle on hover) | item_card_config.micro_interactions | No micro-interactions |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| layout_mode | 'horizontal_timeline' \| 'vertical_timeline' \| 'circular' \| 'flowchart' \| 'insert_between' | 'vertical_timeline' |
| interaction_pattern | 'drag_to_reorder' \| 'click_to_swap' \| 'click_to_select' \| 'number_input' | 'drag_to_reorder' |
| item_card_config.display_type | 'text_only' \| 'image_and_text' \| 'image_only' \| 'icon_and_text' \| 'numbered_text' | 'text_only' |
| item_card_config.show_image | boolean | false |
| item_card_config.image_url | string | undefined |
| connector_config.style | 'arrow' \| 'dotted' \| 'solid' \| 'numbered' \| 'animated' | 'arrow' |
| connector_config.show_connectors | boolean | true |
| connector_config.animation_on_correct | boolean | true |
| slot_config.show_numbers | boolean | true |
| slot_config.slot_style | 'numbered' \| 'lettered' \| 'empty' \| 'icon' | 'numbered' |
| source_area.enabled | boolean | false |
| source_area.layout | 'horizontal' \| 'vertical' \| 'grid' | 'horizontal' |
| reveal_mode | 'instant' \| 'progressive' \| 'cascade' \| 'none' | 'instant' |
| allow_distractors | boolean | false |
| distractor_items | SequenceConfigItem[] | [] |
| scoring_algorithm | 'position_match' \| 'kendall_tau' \| 'longest_subsequence' | 'position_match' |

### Props Gaps

- `items` prop only accepts `{id, text, description}` -- no image, icon, or type fields
- No `layout` or `layoutMode` prop
- No `connectorConfig` prop
- No `slotConfig` prop
- No `sourceArea` prop
- No `revealMode` prop
- No `interactionPattern` prop

### New Components Needed

| Component | Purpose |
|-----------|---------|
| SequenceItemCard | Rich item card with image, icon, description, numbered variants |
| SequenceTrack | Track/lane visual element with slot positions |
| SequenceConnector | Animated connectors between items (arrow, dotted, numbered) |
| SequenceSlot | Drop slot placeholders (numbered/lettered/empty) |
| SequenceSourceArea | Separate pool of items to drag from |
| CircularSequenceLayout | Circular arrangement with loop connector |
| FlowchartSequenceLayout | Flowchart-style with branching paths |
| SequenceRevealAnimation | Progressive/cascade reveal of correct positions |

### Blueprint Field Dependencies

- `blueprint.sequenceConfig.items[].imageUrl` -- NEW FIELD needed on SequenceConfigItem
- `blueprint.sequenceConfig.items[].iconName` -- NEW FIELD
- `blueprint.sequenceConfig.items[].displayType` -- NEW FIELD
- `blueprint.sequenceConfig.layoutMode` -- NEW FIELD
- `blueprint.sequenceConfig.interactionPattern` -- NEW FIELD
- `blueprint.sequenceConfig.connectorConfig` -- NEW FIELD
- `blueprint.sequenceConfig.slotConfig` -- NEW FIELD
- `blueprint.sequenceConfig.sourceArea` -- NEW FIELD
- `blueprint.sequenceConfig.revealMode` -- NEW FIELD
- `blueprint.sequenceConfig.distractorItems` -- NEW FIELD
- `blueprint.sequenceConfig.scoringAlgorithm` -- NEW FIELD

---

## 3. SortingCategories.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/SortingCategories.tsx` (404 lines)
**Research Reference:** `03_sorting_categorization_games.md`

### Current Capabilities

- Items in a pool, drag to category containers
- `DraggableItem`: text + optional description, basic border styling
- `DroppableCategory`: colored header, item count badge, drop highlight indicator
- Batch submit with position-based scoring
- Results view with green/red items per category
- Store integration via `storeProgress`, `onPlacement`, `onStoreSubmit`

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| VennDiagram (2-circle, 3-circle) | SortingConfig.sort_mode=venn_2/venn_3 | Only bucket mode |
| MatrixGrid | SortingConfig.sort_mode=matrix | Not implemented |
| ColumnSorter | SortingConfig.sort_mode=column | Not implemented |
| ItemCard (with image, icon) | SortingConfig.item_card_type | Text-only items |
| ContainerStyle variants | SortingConfig.container_style | Single style: colored header box |
| PoolLayout variants | SortingConfig.pool_layout | Single grid layout |
| IterativeCorrectionUI | SortingConfig.iterative_correction | No iterative correction |
| ClickToPlaceAccessibility | Accessibility alternative | DnD-only, no click fallback |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| Venn diagram drag-to-overlap | sort_mode: venn_2/venn_3 | Not implemented |
| Matrix 2D categorization | sort_mode: matrix | Not implemented |
| Column sorting (ordered within category) | sort_mode: column | Not implemented |
| Immediate feedback on place | submit_mode: immediate | Batch submit only |
| Round-based submit | submit_mode: round_based | Not implemented |
| Lock-on-place (correct items stick) | submit_mode: lock_on_place | Not implemented |
| Multi-category items | allow_multi_category: true | Single correctCategoryId per item |
| Category description tooltips | SortingCategory.description | Description field exists but never rendered |
| Iterative correction | After wrong submit, highlight wrong items | Not implemented |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| sort_mode | 'bucket' \| 'venn_2' \| 'venn_3' \| 'matrix' \| 'column' | 'bucket' |
| item_card_type | 'text_only' \| 'image_and_text' \| 'icon_and_text' | 'text_only' |
| container_style | 'card' \| 'outlined' \| 'filled' \| 'minimal' | 'card' |
| pool_layout | 'horizontal_scroll' \| 'grid' \| 'vertical_list' \| 'scattered' | 'grid' |
| submit_mode | 'batch' \| 'immediate' \| 'round_based' \| 'lock_on_place' | 'batch' |
| allow_multi_category | boolean | false |
| iterative_correction | boolean | false |
| matrix_rows | string[] | undefined |
| matrix_columns | string[] | undefined |
| venn_labels | string[] | undefined |
| show_item_count | boolean | true |
| max_items_per_category | number | undefined |

### Props Gaps

- `items` only accepts `{id, text, correctCategoryId, description}` -- no imageUrl, iconName, displayType
- No `sortMode` prop -- always bucket
- No `submitMode` prop -- always batch
- No `allowMultiCategory` prop
- No `poolLayout` prop
- No `containerStyle` prop
- No `iterativeCorrection` prop

### New Components Needed

| Component | Purpose |
|-----------|---------|
| VennDiagramContainer | 2 or 3 overlapping circles with intersection zones |
| MatrixGridContainer | 2D grid with row/column headers and cell drop targets |
| ColumnContainer | Ordered column with position-aware drop slots |
| SortingItemCard | Rich item card with image, icon, description variants |
| VennOverlapZone | Intersection area for Venn diagrams accepting multi-category items |

### Blueprint Field Dependencies

- `blueprint.sortingConfig.sortMode` -- NEW FIELD
- `blueprint.sortingConfig.submitMode` -- NEW FIELD
- `blueprint.sortingConfig.allowMultiCategory` -- NEW FIELD
- `blueprint.sortingConfig.poolLayout` -- NEW FIELD
- `blueprint.sortingConfig.containerStyle` -- NEW FIELD
- `blueprint.sortingConfig.iterativeCorrection` -- NEW FIELD
- `blueprint.sortingConfig.items[].imageUrl` -- NEW FIELD on SortingItem
- `blueprint.sortingConfig.items[].iconName` -- NEW FIELD
- `blueprint.sortingConfig.items[].correctCategoryIds` -- NEW FIELD (array for multi-category)
- `blueprint.sortingConfig.matrixConfig` -- NEW FIELD (rows, columns)
- `blueprint.sortingConfig.vennConfig` -- NEW FIELD (labels, overlap rules)

---

## 4. MemoryMatch.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/MemoryMatch.tsx` (310 lines)
**Research Reference:** `02_memory_match_games.md`

### Current Capabilities

- Card grid with opacity-based flip effect
- Card interface: `{id, pairId, content, contentType, isFlipped, isMatched}`
- Supports `text` and `image` content types on card fronts
- Score = `perfectAttempts / attempts * 100`
- Cards use CSS `transform: rotateY(180deg)` class but without proper `perspective` or `transform-style: preserve-3d` parent
- Matched cards get green border and checkmark
- Store integration via `storeProgress`, `onMatch`, `onAttempt`
- Retry support

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| True 3D FlipCard (with preserve-3d) | MemoryMatchConfig.card_face_type + flip_duration | Opacity toggle, not true 3D CSS flip |
| CardBack customization | MemoryMatchConfig.card_back_style | All cards have identical blue/gradient back |
| MatchConfirmationAnimation (green pulse, particles) | MemoryMatchConfig.match_animation | Green border only |
| MismatchAnimation (shake, red flash) | MemoryMatchConfig.mismatch_animation | No mismatch animation |
| ExplanationReveal | MemoryMatchConfig.show_explanation_on_match | No explanation shown on match |
| DiagramCloseupCard | MemoryMatchConfig.card_face_type=diagram_closeup | Not implemented |
| ColumnMatchLayout | MemoryMatchConfig.game_variant=column_match | Grid only |
| ScatterLayout | MemoryMatchConfig.game_variant=scatter | Grid only |
| ProgressiveUnlock | MemoryMatchConfig.game_variant=progressive | Not implemented |
| PeekVariant | MemoryMatchConfig.game_variant=peek | Not implemented |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| Column match (drag card from col A to col B) | game_variant: column_match | Flip-and-match only |
| Scatter layout (random positions) | game_variant: scatter | Grid only |
| Progressive unlock (match to reveal next set) | game_variant: progressive | All cards shown at once |
| Peek variant (brief peek at all, then cover) | game_variant: peek | No peek phase |
| Match type awareness (term-definition, label-description, image-name) | match_type config | All pairs treated identically |
| Mismatch penalty modes (none, time, score) | mismatch_penalty | No penalty config |
| Explanation reveal on correct match | show_explanation_on_match | Not implemented |
| Configurable matched card behavior (stay, fade, move) | matched_card_behavior | Cards stay with green border |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| game_variant | 'classic' \| 'column_match' \| 'scatter' \| 'progressive' \| 'peek' | 'classic' |
| card_face_type | 'text' \| 'image' \| 'diagram_closeup' \| 'icon' | 'text' |
| card_back_style | 'solid' \| 'pattern' \| 'gradient' \| 'image' | 'gradient' |
| card_back_color | string | '#3B82F6' |
| card_back_image | string | undefined |
| match_type | 'term_definition' \| 'label_description' \| 'image_name' \| 'function_structure' | 'term_definition' |
| flip_duration_ms | number | 600 |
| matched_card_behavior | 'stay_revealed' \| 'fade_out' \| 'move_to_side' \| 'shrink' | 'stay_revealed' |
| mismatch_penalty | 'none' \| 'time_add' \| 'score_deduct' | 'none' |
| show_explanation_on_match | boolean | false |
| max_concurrent_flips | number | 2 |
| peek_duration_ms | number | 3000 |
| progressive_batch_size | number | 4 |
| grid_columns | number | auto |

### Props Gaps

- `pairs` only accepts `{id, front, back, frontType, backType}` -- no `explanation`, `matchType`, `category`
- No `gameVariant` prop
- No `cardBackStyle` prop
- No `matchedCardBehavior` prop
- No `mismatchPenalty` prop
- No `showExplanation` prop
- `gridSize` accepts `[rows, cols]` but grid calculation ignores it (auto-calculates from pair count)

### New Components Needed

| Component | Purpose |
|-----------|---------|
| FlipCard3D | Proper CSS 3D flip with perspective, preserve-3d, front/back faces |
| ColumnMatchLayout | Two-column layout with drag-to-match between columns |
| ScatterLayout | Randomly positioned cards with collision avoidance |
| ProgressiveCardGrid | Reveals cards in batches on successful matches |
| PeekPhaseOverlay | Temporary reveal of all cards with countdown |
| ExplanationPopover | Educational explanation shown on successful match |
| MatchAnimation | Configurable animation for correct/incorrect matches |

### Blueprint Field Dependencies

- `blueprint.memoryMatchConfig.gameVariant` -- NEW FIELD
- `blueprint.memoryMatchConfig.cardBackStyle` -- NEW FIELD
- `blueprint.memoryMatchConfig.cardBackColor` -- NEW FIELD
- `blueprint.memoryMatchConfig.matchType` -- NEW FIELD
- `blueprint.memoryMatchConfig.matchedCardBehavior` -- NEW FIELD
- `blueprint.memoryMatchConfig.mismatchPenalty` -- NEW FIELD
- `blueprint.memoryMatchConfig.showExplanationOnMatch` -- NEW FIELD
- `blueprint.memoryMatchConfig.peekDurationMs` -- NEW FIELD
- `blueprint.memoryMatchConfig.progressiveBatchSize` -- NEW FIELD
- `blueprint.memoryMatchConfig.pairs[].explanation` -- NEW FIELD on MemoryMatchPair
- `blueprint.memoryMatchConfig.pairs[].matchType` -- NEW FIELD

---

## 5. BranchingScenario.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/BranchingScenario.tsx` (360 lines)
**Research Reference:** `04_branching_scenario_games.md`

### Current Capabilities

- White card-based UI with question text and description
- Decision options rendered as text buttons with hover effects
- Optional `imageUrl` per node (displayed as small image)
- Path breadcrumbs showing green (correct) / red (incorrect) choice pills
- Consequence text shown inline after selection
- Backtrack support with undo button
- End node detection with completion message
- Store integration via `storeProgress`, `onChoice`, `onUndo`
- Results panel showing path summary with correct/incorrect indicators

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| SceneBackground | BranchingConfig.scene_backgrounds | No scene backgrounds; plain white cards |
| CharacterSprite (with expressions) | BranchingConfig.characters | No character sprites |
| StateDisplay (health bar, inventory, score) | BranchingConfig.state_display | No state variable display |
| Minimap / decision tree visualization | BranchingConfig.minimap | No minimap |
| NodeTypeIndicator (decision, information, checkpoint, consequence) | DecisionNode.node_type | All nodes look identical |
| TransitionEffect (fade, slide, zoom) | BranchingConfig.transition_style | No transition effects between nodes |
| ConsequenceVisualization | BranchingConfig.consequence_visualization | Text-only consequences |
| EndingIllustration | DecisionNode.ending_illustration | No ending artwork |
| ChoiceImpactPreview | BranchingConfig.show_impact_preview | No preview of choice consequences |
| NarrativeProgressBar | BranchingConfig.narrative_structure | No story progress indicator |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| State variables tracking (health, resources, knowledge) | state_variables + initial_state | No state variable system |
| Per-choice state changes (modify variables) | DecisionOption.state_changes | Options only have points/isCorrect |
| Multiple valid endings with scoring | multipleValidEndings + ending scoring | Single "end" with binary correct/incorrect |
| Node type differentiation (info, checkpoint, consequence) | DecisionNode.node_type | All nodes are decision nodes |
| Character expression changes per choice | characters[].expression_map | No character system |
| Narrative structure (foldback, gauntlet, branch_and_bottleneck) | narrative_structure | Linear branching only |
| Time pressure per node | DecisionNode.time_limit | No time limits |
| Hidden information reveal | DecisionOption.reveals_info | Not implemented |
| Auto-advance information nodes | node_type=information | Not implemented |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| characters | Character[] (id, name, imageUrl, expression_map) | [] |
| scene_backgrounds | Record<string, string> (nodeId -> bgUrl) | {} |
| state_variables | StateVariable[] (name, type, min, max, initial) | [] |
| initial_state | Record<string, number \| string \| boolean> | {} |
| state_display | { position: string, show_variables: string[] } | undefined |
| minimap | { enabled: boolean, position: string, style: string } | { enabled: false } |
| narrative_structure | 'branch_and_bottleneck' \| 'foldback' \| 'gauntlet' \| 'full_branch' | 'full_branch' |
| transition_style | 'fade' \| 'slide' \| 'zoom' \| 'none' | 'none' |
| visual_config | { node_styles, edge_styles, theme } | undefined |
| consequence_visualization | 'text' \| 'animation' \| 'state_change' \| 'combined' | 'text' |

### Props Gaps

- `DecisionOption` has no `state_changes` field
- `DecisionNode` has no `node_type`, `time_limit`, `character_id`, `background_key` fields
- No `characters` prop on BranchingScenario
- No `stateVariables` prop
- No `narrativeStructure` prop
- No `transitionStyle` prop
- No `minimap` prop

### New Components Needed

| Component | Purpose |
|-----------|---------|
| SceneBackdrop | Full-width background image behind decision nodes |
| CharacterSprite | Animated character with expression states |
| StateVariableDisplay | HUD-like display of state variables (health, knowledge, etc.) |
| DecisionTreeMinimap | Miniature visualization of the full decision tree |
| NarrativeProgressBar | Story progress indicator with chapter/section markers |
| NodeTypeRenderer | Different visual treatments per node type |
| TransitionOverlay | Animated transitions between nodes (fade, slide, zoom) |
| ConsequenceAnimator | Visual consequence display (state changes, animations) |
| EndingScene | Rich ending display with illustration and summary |

### Blueprint Field Dependencies

- `blueprint.branchingConfig.characters` -- NEW FIELD
- `blueprint.branchingConfig.sceneBackgrounds` -- NEW FIELD
- `blueprint.branchingConfig.stateVariables` -- NEW FIELD
- `blueprint.branchingConfig.initialState` -- NEW FIELD
- `blueprint.branchingConfig.stateDisplay` -- NEW FIELD
- `blueprint.branchingConfig.minimap` -- NEW FIELD
- `blueprint.branchingConfig.narrativeStructure` -- NEW FIELD
- `blueprint.branchingConfig.transitionStyle` -- NEW FIELD
- `blueprint.branchingConfig.nodes[].nodeType` -- NEW FIELD on DecisionNode
- `blueprint.branchingConfig.nodes[].characterId` -- NEW FIELD
- `blueprint.branchingConfig.nodes[].backgroundKey` -- NEW FIELD
- `blueprint.branchingConfig.nodes[].timeLimit` -- NEW FIELD
- `blueprint.branchingConfig.nodes[].options[].stateChanges` -- NEW FIELD on DecisionOption
- `blueprint.branchingConfig.nodes[].options[].revealsInfo` -- NEW FIELD

---

## 6. CompareContrast.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/CompareContrast.tsx` (301 lines)
**Research Reference:** `05_compare_contrast_games.md`

### Current Capabilities

- Side-by-side diagrams with clickable zones
- 4 hardcoded categories: `similar`, `different`, `unique_a`, `unique_b` with fixed colors
- Click zone -> select category from buttons -> submit all
- Score based on correct category assignment
- Results display with correct/incorrect indicators per zone
- Store integration via `storeProgress`, `onCategorization`, `onStoreSubmit`

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| SliderComparison (react-compare-slider) | CompareConfig.comparisonMode=slider | Not implemented |
| OverlayTransparency (opacity toggle) | CompareConfig.comparisonMode=overlay | Not implemented |
| VennDiagramMode | CompareConfig.comparisonMode=venn | Not implemented |
| SpotTheDifference | CompareConfig.comparisonMode=spot_difference | Not implemented |
| ZonePairingLines (connecting same structures) | CompareConfig.zonePairings | No connecting lines between paired zones |
| SynchronizedZoom | CompareConfig.syncZoom | No zoom at all |
| ExplorationPhase | CompareConfig.explorationEnabled | No explore-before-categorize phase |
| ZoneDescriptionTooltip | CompareConfig.showDescriptions | No tooltips on zones |
| CategoryCustomization | CompareConfig.categoryTypes/Labels/Colors | Hardcoded 4 categories with fixed colors |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| Slider drag comparison | comparisonMode: slider | Not implemented |
| Overlay with opacity control | comparisonMode: overlay | Not implemented |
| Venn diagram categorization | comparisonMode: venn | Side-by-side click only |
| Spot-the-difference clicking | comparisonMode: spot_difference | Not implemented |
| Zone pairing (match same structures across diagrams) | zonePairings | Not implemented |
| Synchronized zoom/pan between both images | syncZoom | Not implemented |
| Exploration phase before categorization | explorationEnabled | Not implemented |
| Custom category types | categoryTypes: string[] | Hardcoded 4 categories |
| Custom category labels/colors | categoryLabels, categoryColors | Hardcoded |
| Drag-to-Venn categorization | venn + drag | Not implemented |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| comparisonMode | 'slider' \| 'side_by_side' \| 'overlay' \| 'venn' \| 'spot_difference' | 'side_by_side' |
| categoryTypes | string[] | ['similar', 'different', 'unique_a', 'unique_b'] |
| categoryLabels | Record<string, string> | Hardcoded labels |
| categoryColors | Record<string, string> | Hardcoded colors |
| explorationEnabled | boolean | false |
| explorationDurationMs | number | 30000 |
| zonePairings | Array<{zoneA: string, zoneB: string}> | [] |
| showPairingLines | boolean | false |
| syncZoom | boolean | false |
| showDescriptions | boolean | false |
| highlightMatching | boolean | false (exists in type but not rendered) |
| sliderOrientation | 'horizontal' \| 'vertical' | 'horizontal' |
| overlayBlendMode | string | 'normal' |

### Props Gaps

- No `comparisonMode` prop -- always side-by-side
- No `categoryTypes` / `categoryLabels` / `categoryColors` props -- hardcoded
- No `explorationEnabled` prop
- No `zonePairings` prop
- No `syncZoom` prop
- `highlightMatching` exists in CompareConfig type but is never read by the component

### New Components Needed

| Component | Purpose |
|-----------|---------|
| SliderComparison | Before/after slider using react-compare-slider or similar |
| OverlayComparison | Overlapping images with opacity slider |
| VennCompareContainer | Venn diagram for categorizing similarities/differences |
| SpotTheDifferenceCanvas | Click-on-differences mode with magnification |
| ZonePairingLineOverlay | SVG lines connecting paired zones across diagrams |
| SynchronizedZoomContainer | Linked zoom/pan between two image panels |
| ExplorationPhaseOverlay | Timer-based free exploration before test phase |
| CategoryPalette | Configurable category selector replacing hardcoded buttons |

### Blueprint Field Dependencies

- `blueprint.compareConfig.comparisonMode` -- NEW FIELD
- `blueprint.compareConfig.categoryTypes` -- NEW FIELD
- `blueprint.compareConfig.categoryLabels` -- NEW FIELD
- `blueprint.compareConfig.categoryColors` -- NEW FIELD
- `blueprint.compareConfig.explorationEnabled` -- NEW FIELD
- `blueprint.compareConfig.explorationDurationMs` -- NEW FIELD
- `blueprint.compareConfig.zonePairings` -- NEW FIELD
- `blueprint.compareConfig.syncZoom` -- NEW FIELD
- `blueprint.compareConfig.showDescriptions` -- NEW FIELD
- `blueprint.compareConfig.sliderOrientation` -- NEW FIELD (for slider mode)

---

## 7. HotspotManager.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/HotspotManager.tsx` (296 lines)
**Research Reference:** `06_click_trace_description_games.md`

### Current Capabilities

- Circle zones with three visual states: completed (green), target (blue pulsing), highlighted (yellow)
- Prompt text display at top
- Sequential and `any_order` selection modes
- Progress counter (X of Y)
- `useAnimation` hook for correct/incorrect feedback animations
- Click handler with zone validation
- Store integration via `storeProgress`, `onIdentify`

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| PromptBanner (naming, functional, descriptive styles) | ClickToIdentifyConfig.prompt_style | Plain text at top |
| ZoneHighlightStateMachine (5 states) | ZoneHighlight.states | 3 states only (no hover, no transitional states) |
| MagnificationLens | ClickToIdentifyConfig.magnification | Not implemented |
| ExploreTestController (two-phase) | ClickToIdentifyConfig.explore_mode | Not implemented |
| ConfigurableZoneHighlight (colors, animations) | ClickToIdentifyConfig.highlight_style | Hardcoded colors |
| InvisibleHotspot (zones hidden until hover) | Zone.visibility=hidden | Zones always visible as circles |
| SubtleHotspot (faint outline until hover) | Zone.visibility=subtle | Not implemented |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| 5-state zone highlight machine (default->hover->selected->correct->incorrect) | ZoneHighlightStateMachine | 3 states; no hover distinction |
| Prompt style variants (naming vs functional vs descriptive) | prompt_style | Plain text always |
| Magnification lens on hover/click | magnification config | Not implemented |
| Explore-then-test mode (free exploration, then test) | explore_mode | Not implemented |
| Zone visibility modes (visible, hidden, subtle) | Zone.visibility | Always visible |
| Configurable highlight colors | highlight_style | Hardcoded blue/green/yellow |
| Highlight animation config (pulse, glow, ring) | highlight_animation | Hardcoded pulse on target |
| any_order mode label leak | prompts[] | In any_order, zone labels leak into prompt text (reveals answer) |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| prompt_style | 'naming' \| 'functional' \| 'descriptive' \| 'contextual' | 'naming' |
| highlight_style | { default_color, hover_color, correct_color, incorrect_color, selected_color } | Hardcoded colors |
| highlight_animation | 'pulse' \| 'glow' \| 'ring' \| 'none' | 'pulse' |
| magnification | { enabled: boolean, zoom_level: number, lens_size: number } | { enabled: false } |
| explore_mode | { enabled: boolean, duration_ms: number, show_labels_on_hover: boolean } | { enabled: false } |
| zone_visibility | 'visible' \| 'hidden' \| 'subtle' | 'visible' |
| feedback_delay_ms | number | 500 |
| show_zone_labels_after_correct | boolean | true |

### Props Gaps

- No dedicated `clickToIdentifyConfig` object prop -- receives raw `identificationPrompts` and `selectionMode` separately
- No `promptStyle` prop
- No `highlightStyle` prop
- No `magnification` prop
- No `exploreMode` prop
- No `zoneVisibility` prop
- Zone shape is always circle; no polygon/rect hotspot support

### New Components Needed

| Component | Purpose |
|-----------|---------|
| PromptBanner | Styled prompt display with variants (naming, functional, descriptive) |
| MagnificationLens | Circular magnification overlay that follows cursor |
| ExploreTestController | Two-phase controller: free exploration timer -> test mode |
| ZoneHighlightStateMachine | 5-state highlight with configurable colors and animations |
| InvisibleHotspotOverlay | Transparent zones that reveal on hover |

### Blueprint Field Dependencies

- `blueprint.clickToIdentifyConfig` -- NEW TOP-LEVEL FIELD on InteractiveDiagramBlueprint
- `blueprint.clickToIdentifyConfig.promptStyle` -- NEW FIELD
- `blueprint.clickToIdentifyConfig.highlightStyle` -- NEW FIELD
- `blueprint.clickToIdentifyConfig.magnification` -- NEW FIELD
- `blueprint.clickToIdentifyConfig.exploreMode` -- NEW FIELD
- `blueprint.clickToIdentifyConfig.zoneVisibility` -- NEW FIELD
- `blueprint.clickToIdentifyConfig.feedbackDelayMs` -- NEW FIELD

---

## 8. PathDrawer.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/PathDrawer.tsx` (397 lines)
**Research Reference:** `06_click_trace_description_games.md`

### Current Capabilities

- Click-waypoint interaction: click zones in order to build path
- `PathVisualizer`: SVG rendering with dashed lines and arrowhead markers between visited zones
- `PathZone`: Circle zones with visited (numbered badge), next (pulsing blue), unvisited (gray) states
- Path description display at top
- Score = visited waypoints count * points per zone
- Store integration via `storeProgress`, `onProgress`

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| SVG curved paths (quadratic, cubic bezier) | TracePathConfig.path_type | Straight lines only |
| AnimatedParticleSystem | TracePathConfig.particle_theme | No particles |
| ColorTransitionEngine | TracePathConfig.color_transition | Uniform blue color |
| DirectionArrows (distributed along path) | TracePathConfig.direction_arrows | Single arrowhead at end only |
| GateWaypointType | TracePath.waypoints[].type=gate | All waypoints are simple circles |
| FreehandDrawingCanvas | TracePathConfig.drawing_mode=freehand | Click-only |
| PathPreview (ghost path) | TracePathConfig.show_preview | Not implemented |
| BranchingPathFork | TracePathConfig.path_type=branching | Linear paths only |
| CircularPathLoop | TracePathConfig.path_type=circular | Linear paths only |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| SVG curved path rendering | path_type with control points | Straight dashed lines |
| Particle animation along path | particle_theme (blood cells, electrons, etc.) | No animation |
| Color transitions along path (blue->red) | color_transition (start_color, end_color) | Uniform color |
| Gate/valve waypoint interactions | waypoint.type=gate (click to open) | All waypoints identical |
| Freehand drawing mode | drawing_mode=freehand (draw on canvas) | Click-waypoint only |
| Branching paths (choose at fork) | path_type=branching | Linear only |
| Circular/loop paths | path_type=circular | Linear only |
| Direction arrows distributed along path | direction_arrows (interval, style) | Single terminal arrowhead |
| Path thickness variation | path_style.thickness | Uniform 2px stroke |
| Path opacity gradient | path_style.opacity_gradient | Uniform opacity |
| Magnetic snap to path | snap_to_path | Not implemented |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| path_type | 'linear' \| 'branching' \| 'circular' | 'linear' |
| drawing_mode | 'click_waypoint' \| 'freehand' \| 'guided' | 'click_waypoint' |
| particle_theme | { type: string, count: number, speed: number, color: string } | undefined |
| color_transition | { enabled: boolean, start_color: string, end_color: string, mode: string } | undefined |
| direction_arrows | { show: boolean, interval: number, style: string } | { show: true } |
| path_style | { color: string, thickness: number, dash_array: string, opacity: number } | Defaults |
| waypoint_types | Record<string, { type: string, interaction: string }> | {} |
| show_preview | boolean | false |
| snap_to_path | boolean | false |
| curve_type | 'straight' \| 'quadratic' \| 'cubic' \| 'catmull_rom' | 'straight' |

### Props Gaps

- No `tracePathConfig` object prop -- receives raw `paths` array only
- No `pathType` prop
- No `drawingMode` prop
- No `particleTheme` prop
- No `colorTransition` prop
- No `directionArrows` prop
- No `pathStyle` prop
- No `curveType` prop
- `PathWaypoint` interface has only `{zoneId, order}` -- no `type`, `gateConfig`, `controlPoints`

### New Components Needed

| Component | Purpose |
|-----------|---------|
| SVGCurvedPath | Renders bezier/catmull-rom curves between waypoints |
| AnimatedParticleSystem | Particles flowing along completed path (blood, electrons, etc.) |
| ColorTransitionPath | Path with gradient color transition from start to end |
| DirectionArrowOverlay | Arrows distributed along path at intervals |
| GateWaypoint | Special waypoint with gate/valve interaction |
| FreehandCanvas | Canvas for freehand path drawing with tolerance matching |
| BranchingPathFork | Fork point UI for choosing between paths |
| PathPreviewGhost | Semi-transparent preview of expected path |

### Blueprint Field Dependencies

- `blueprint.tracePathConfig` -- NEW TOP-LEVEL FIELD on InteractiveDiagramBlueprint
- `blueprint.tracePathConfig.pathType` -- NEW FIELD
- `blueprint.tracePathConfig.drawingMode` -- NEW FIELD
- `blueprint.tracePathConfig.particleTheme` -- NEW FIELD
- `blueprint.tracePathConfig.colorTransition` -- NEW FIELD
- `blueprint.tracePathConfig.directionArrows` -- NEW FIELD
- `blueprint.tracePathConfig.pathStyle` -- NEW FIELD
- `blueprint.tracePathConfig.curveType` -- NEW FIELD
- `blueprint.paths[].waypoints[].type` -- NEW FIELD on PathWaypoint
- `blueprint.paths[].waypoints[].controlPoints` -- NEW FIELD
- `blueprint.paths[].waypoints[].gateConfig` -- NEW FIELD

---

## 9. DescriptionMatcher.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/DescriptionMatcher.tsx` (517 lines)
**Research Reference:** `06_click_trace_description_games.md`

### Current Capabilities

- Three modes: `click_zone`, `drag_description`, `multiple_choice`
- `click_zone`: Shows description text, user clicks matching zone from a button grid
- `drag_description`: Drag description cards to zone drop targets using DnD Kit
- `multiple_choice`: Zone label shown, pick correct description from 4 shuffled options
- Per-match scoring with correct/incorrect counters
- Results summary
- Store integration via `storeProgress`, `onMatch`

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| ConnectingLineRenderer | DescriptionMatchingConfig.connecting_lines | No connecting lines between matched pairs |
| ZoneProximityHighlight | DescriptionMatchingConfig.proximity_highlight | No proximity-based highlighting during drag |
| DeferredEvaluationController | DescriptionMatchingConfig.defer_evaluation | Immediate per-item feedback |
| DistractorDescriptionPool | DescriptionMatchingConfig.distractor_count | No distractor descriptions |
| DescriptionStyleVariants | DescriptionMatchingConfig.description_style | Plain text descriptions only |
| DescriptionCardStateMachine | Card states: available, dragging, placed, correct, incorrect | Basic styling only |
| MatchedPairVisualization | Visual connection between matched description-zone pairs | No visualization of completed matches |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| Connecting lines between matches | connecting_lines (animated, colored) | No visual connections |
| Zone proximity highlight during drag | proximity_highlight | No spatial feedback |
| Deferred evaluation (match all then submit) | defer_evaluation | Immediate per-item evaluation |
| Distractor descriptions | distractor_count, distractor_descriptions | No distractors |
| Description style variants (functional, structural, process, clinical) | description_style | Plain text |
| Description card state machine | states: available -> dragging -> placed -> correct/incorrect | Basic opacity changes |
| Stable MC option ordering | multiple_choice shuffle | Options re-shuffle on every render (React key issue) |
| Zone-description type pairing | match_type awareness | All matches treated identically |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| match_mode | 'click_zone' \| 'drag_description' \| 'multiple_choice' | 'click_zone' |
| connecting_lines | { enabled: boolean, style: string, color: string, animate: boolean } | { enabled: false } |
| proximity_highlight | { enabled: boolean, radius: number, color: string } | { enabled: false } |
| defer_evaluation | boolean | false |
| description_style | 'functional' \| 'structural' \| 'process' \| 'clinical' \| 'simplified' | 'functional' |
| distractor_count | number | 0 |
| distractor_descriptions | string[] | [] |
| show_zone_labels | boolean | true |
| auto_advance | boolean | true |
| feedback_delay_ms | number | 500 |

### Props Gaps

- `descriptionMatchingConfig` is typed as `{ descriptions?: Record<string,string>; mode?: string }` -- too narrow
- No `connectingLines` prop
- No `proximityHighlight` prop
- No `deferEvaluation` prop
- No `descriptionStyle` prop
- No `distractorDescriptions` prop
- `mode` prop exists but is a bare string, not validated union type

### Bug: MC Option Re-Shuffle

In `multiple_choice` mode (line ~420-450), options are generated inside the render function using `sort(() => Math.random() - 0.5)`. This means options re-shuffle on every re-render, creating an unstable UI. Options should be memoized or shuffled once per question.

### New Components Needed

| Component | Purpose |
|-----------|---------|
| ConnectingLineOverlay | SVG lines connecting matched description-zone pairs |
| ProximityHighlighter | Highlights zones near dragged description based on proximity |
| DeferredSubmitController | Collects all matches before batch evaluation |
| DescriptionCard | Rich card with state machine (available, dragging, placed, correct, incorrect) |
| DistractorManager | Manages distractor descriptions in the pool |

### Blueprint Field Dependencies

- `blueprint.descriptionMatchingConfig.connectingLines` -- NEW FIELD
- `blueprint.descriptionMatchingConfig.proximityHighlight` -- NEW FIELD
- `blueprint.descriptionMatchingConfig.deferEvaluation` -- NEW FIELD
- `blueprint.descriptionMatchingConfig.descriptionStyle` -- NEW FIELD
- `blueprint.descriptionMatchingConfig.distractorCount` -- NEW FIELD
- `blueprint.descriptionMatchingConfig.distractorDescriptions` -- NEW FIELD
- `blueprint.descriptionMatchingConfig.feedbackDelayMs` -- NEW FIELD

---

## 10. DiagramCanvas.tsx

**File:** `frontend/src/components/templates/InteractiveDiagramGame/DiagramCanvas.tsx` (386 lines)
**Research Reference:** `07_drag_drop_richness.md`

### Current Capabilities

- Image rendering with `next/image` (fill mode, object-contain)
- PolygonOverlay using SVG with Catmull-Rom smooth paths
- MediaAssetsLayer for sprite/overlay assets with layered z-index
- DropZone rendering for circle, polygon, and rect shapes
- Placed label display at zone positions
- Label removal on click (placed labels)
- Accessibility attributes (role="application", aria-labels, screen reader instructions)
- `onZoneClick` handler for click-to-identify mode
- Zone completion state display (green check overlay)

### Missing Visual Components

| Component | Research Spec | Current State |
|-----------|--------------|---------------|
| LeaderLineOverlay (straight, elbow, curved, fluid) | DragDropConfig.leader_lines | No leader lines |
| ZoomPanCanvas (react-zoom-pan-pinch) | DragDropConfig.zoom_pan | No zoom or pan |
| EnhancedLabelCard (text_with_icon, thumbnail, description) | DragDropConfig.label_style | Plain text labels |
| InfoPanel (tooltip/popover on placed labels) | DragDropConfig.info_panel | No info panel |
| PinMarker (placed label indicator style) | DragDropConfig.pin_style | Plain text overlay |
| ZoneIdleAnimation (subtle pulse/glow on unoccupied zones) | DragDropConfig.zone_idle_animation | Static zones |
| SpringPhysicsAnimation | DragDropConfig.placement_animation | No physics animation on label snap |
| ReverseMode indicator | DragDropConfig.reverse_mode | Not implemented |
| DistractorHighlight | DragDropConfig.distractor_management | Distractors not visually distinct from correct labels |

### Missing Interaction Patterns

| Pattern | Research Spec | Current State |
|---------|--------------|---------------|
| Leader lines connecting labels to zones | leader_lines (style, animate, color) | No visual connections |
| Zoom and pan on large diagrams | zoom_pan (min_zoom, max_zoom, pan_bounds) | Fixed image, no zoom/pan |
| Click-to-place (accessibility) | placement_mode: click_to_place | Drag-only placement |
| Reverse mode (zones given, guess labels) | reverse_mode | Not implemented |
| Spring physics on label snap | placement_animation: spring | Instant placement |
| Info panel on hover/click | info_panel (trigger, content, position) | No info panel |
| Pin markers at placed positions | pin_style (type, color, size) | Plain text |
| Zone idle animations | zone_idle_animation (pulse, glow, breathe) | Static |
| Distractor visual management | distractor_management (visual_hint, elimination) | All labels look same |
| Label card rich variants | label_style (text_with_icon, thumbnail, description_card) | Text-only labels |

### Missing Configurable Properties

| Property | Type | Default Needed |
|----------|------|---------------|
| leader_lines | { enabled: boolean, style: string, color: string, animate: boolean, thickness: number } | { enabled: false } |
| zoom_pan | { enabled: boolean, min_zoom: number, max_zoom: number, show_controls: boolean } | { enabled: false } |
| label_style | 'text_only' \| 'text_with_icon' \| 'thumbnail' \| 'description_card' | 'text_only' |
| placement_animation | 'none' \| 'spring' \| 'slide' \| 'fade' | 'none' |
| placement_mode | 'drag_drop' \| 'click_to_place' | 'drag_drop' |
| pin_style | { type: string, color: string, size: number } | undefined |
| info_panel | { enabled: boolean, trigger: string, position: string } | { enabled: false } |
| zone_idle_animation | 'none' \| 'pulse' \| 'glow' \| 'breathe' | 'none' |
| reverse_mode | boolean | false |
| distractor_management | { visual_hint: boolean, elimination_on_wrong: boolean } | undefined |

### Props Gaps

- No `dragDropConfig` object prop -- receives no config for leader lines, zoom, label style
- No `leaderLines` prop
- No `zoomPan` prop
- No `labelStyle` prop
- No `placementAnimation` prop
- No `placementMode` prop
- No `infoPanel` prop
- No `reverseMode` prop

### New Components Needed

| Component | Purpose |
|-----------|---------|
| LeaderLineOverlay | SVG leader lines (straight, elbow, curved, fluid) from labels to zones |
| ZoomPanWrapper | react-zoom-pan-pinch integration for large diagrams |
| EnhancedLabelCard | Rich label card variants (icon, thumbnail, description) |
| InfoPanel | Tooltip/popover with educational info on placed labels |
| PinMarker | Visual pin at placed label positions |
| SpringAnimator | Physics-based snap animation for label placement |
| ZoneIdleAnimator | Subtle animations on unoccupied zones |
| ClickToPlaceHandler | Click-to-select then click-zone alternative to drag |

### Blueprint Field Dependencies

- `blueprint.dragDropConfig` -- NEW TOP-LEVEL FIELD on InteractiveDiagramBlueprint
- `blueprint.dragDropConfig.leaderLines` -- NEW FIELD
- `blueprint.dragDropConfig.zoomPan` -- NEW FIELD
- `blueprint.dragDropConfig.labelStyle` -- NEW FIELD
- `blueprint.dragDropConfig.placementAnimation` -- NEW FIELD
- `blueprint.dragDropConfig.placementMode` -- NEW FIELD
- `blueprint.dragDropConfig.pinStyle` -- NEW FIELD
- `blueprint.dragDropConfig.infoPanel` -- NEW FIELD
- `blueprint.dragDropConfig.zoneIdleAnimation` -- NEW FIELD
- `blueprint.dragDropConfig.reverseMode` -- NEW FIELD
- `blueprint.dragDropConfig.distractorManagement` -- NEW FIELD
- `blueprint.labels[].iconName` -- NEW FIELD on Label
- `blueprint.labels[].thumbnailUrl` -- NEW FIELD
- `blueprint.labels[].description` -- NEW FIELD (for description_card style)

---

## 11. types.ts

**File:** `frontend/src/components/templates/InteractiveDiagramGame/types.ts` (765 lines)
**Research Reference:** All research documents

### Current Type Coverage

The file defines 40+ interfaces/types covering:
- `InteractionMode` union (11 modes)
- `ModeTransition`, `ModeTransitionTrigger`, `Mechanic`
- `Zone`, `Label`, `DistractorLabel`, `PlacedLabel`
- `SequenceConfig`, `SequenceConfigItem`
- `SortingConfig`, `SortingItem`, `SortingCategory`
- `MemoryMatchConfig`, `MemoryMatchPair`
- `BranchingConfig`, `DecisionNode`, `DecisionOption`
- `CompareConfig`, `CompareDiagram`
- `InteractiveDiagramBlueprint` (central blueprint type)
- `GameSequence`, `GameScene`, `MultiSceneState`, `SceneResult`
- Per-mechanic progress types: `SequencingProgress`, `SortingProgress`, `MemoryMatchProgress`, `BranchingProgress`, `CompareProgress`
- Temporal types: `TemporalConstraint`, `MotionPath`, `MotionKeyframe`
- Animation types: `AnimationSpec`, `StructuredAnimations`

### Missing Mechanic Config Interfaces

#### 11.1 ClickToIdentifyConfig (not defined)

Research spec (06_click_trace_description_games.md) requires:
```
interface ClickToIdentifyConfig {
  promptStyle: 'naming' | 'functional' | 'descriptive' | 'contextual';
  highlightStyle: {
    defaultColor: string;
    hoverColor: string;
    correctColor: string;
    incorrectColor: string;
    selectedColor: string;
  };
  highlightAnimation: 'pulse' | 'glow' | 'ring' | 'none';
  magnification: {
    enabled: boolean;
    zoomLevel: number;
    lensSize: number;
  };
  exploreMode: {
    enabled: boolean;
    durationMs: number;
    showLabelsOnHover: boolean;
  };
  zoneVisibility: 'visible' | 'hidden' | 'subtle';
  feedbackDelayMs: number;
}
```
**Status:** Not defined anywhere in types.ts.

#### 11.2 TracePathConfig (not defined)

Research spec (06_click_trace_description_games.md) requires:
```
interface TracePathConfig {
  pathType: 'linear' | 'branching' | 'circular';
  drawingMode: 'click_waypoint' | 'freehand' | 'guided';
  particleTheme: {
    type: string;
    count: number;
    speed: number;
    color: string;
  };
  colorTransition: {
    enabled: boolean;
    startColor: string;
    endColor: string;
    mode: 'gradient' | 'segment';
  };
  directionArrows: {
    show: boolean;
    interval: number;
    style: 'filled' | 'outlined' | 'animated';
  };
  pathStyle: {
    color: string;
    thickness: number;
    dashArray: string;
    opacity: number;
  };
  curveType: 'straight' | 'quadratic' | 'cubic' | 'catmull_rom';
}
```
**Status:** Not defined anywhere in types.ts.

#### 11.3 DragDropConfig (not defined)

Research spec (07_drag_drop_richness.md) requires:
```
interface DragDropConfig {
  leaderLines: {
    enabled: boolean;
    style: 'straight' | 'elbow' | 'curved' | 'fluid';
    color: string;
    animate: boolean;
    thickness: number;
  };
  zoomPan: {
    enabled: boolean;
    minZoom: number;
    maxZoom: number;
    showControls: boolean;
    panBounds: boolean;
  };
  labelStyle: 'text_only' | 'text_with_icon' | 'thumbnail' | 'description_card';
  placementAnimation: 'none' | 'spring' | 'slide' | 'fade';
  placementMode: 'drag_drop' | 'click_to_place';
  pinStyle: { type: string; color: string; size: number };
  infoPanel: {
    enabled: boolean;
    trigger: 'hover' | 'click';
    position: 'above' | 'below' | 'side';
  };
  zoneIdleAnimation: 'none' | 'pulse' | 'glow' | 'breathe';
  reverseMode: boolean;
  distractorManagement: {
    visualHint: boolean;
    eliminationOnWrong: boolean;
  };
}
```
**Status:** Not defined anywhere in types.ts.

#### 11.4 DescriptionMatchingConfig (partially defined)

Current type in InteractiveDiagramBlueprint (L533-536):
```
descriptionMatchingConfig?: {
  descriptions?: Record<string, string>;
  mode?: 'click_zone' | 'drag_description' | 'multiple_choice';
};
```

Research spec (06_click_trace_description_games.md) requires additionally:
```
connectingLines: { enabled: boolean; style: string; color: string; animate: boolean };
proximityHighlight: { enabled: boolean; radius: number; color: string };
deferEvaluation: boolean;
descriptionStyle: 'functional' | 'structural' | 'process' | 'clinical' | 'simplified';
distractorCount: number;
distractorDescriptions: string[];
feedbackDelayMs: number;
```
**Status:** Partially defined. Missing 7 fields.

### Missing Fields on Existing Config Interfaces

#### 11.5 SequenceConfig gaps

Current fields: `sequenceType`, `items`, `correctOrder`, `allowPartialCredit`, `instructionText`

Missing from research (01_sequencing_games.md):
- `layoutMode: 'horizontal_timeline' | 'vertical_timeline' | 'circular' | 'flowchart' | 'insert_between'`
- `interactionPattern: 'drag_to_reorder' | 'click_to_swap' | 'click_to_select' | 'number_input'`
- `itemCardConfig: { displayType, showImage }`
- `connectorConfig: { style, showConnectors, animationOnCorrect }`
- `slotConfig: { showNumbers, slotStyle }`
- `sourceArea: { enabled, layout }`
- `revealMode: 'instant' | 'progressive' | 'cascade' | 'none'`
- `distractorItems: SequenceConfigItem[]`
- `scoringAlgorithm: 'position_match' | 'kendall_tau' | 'longest_subsequence'`

#### 11.6 SortingConfig gaps

Current fields: `items`, `categories`, `allowPartialCredit`, `showCategoryHints`, `instructions`

Missing from research (03_sorting_categorization_games.md):
- `sortMode: 'bucket' | 'venn_2' | 'venn_3' | 'matrix' | 'column'`
- `itemCardType: 'text_only' | 'image_and_text' | 'icon_and_text'`
- `containerStyle: 'card' | 'outlined' | 'filled' | 'minimal'`
- `poolLayout: 'horizontal_scroll' | 'grid' | 'vertical_list' | 'scattered'`
- `submitMode: 'batch' | 'immediate' | 'round_based' | 'lock_on_place'`
- `allowMultiCategory: boolean`
- `iterativeCorrection: boolean`
- `matrixConfig: { rows, columns }`
- `vennConfig: { labels, overlapRules }`
- `maxItemsPerCategory: number`

#### 11.7 MemoryMatchConfig gaps

Current fields: `pairs`, `gridSize`, `flipDurationMs`, `showAttemptsCounter`, `instructions`

Missing from research (02_memory_match_games.md):
- `gameVariant: 'classic' | 'column_match' | 'scatter' | 'progressive' | 'peek'`
- `cardFaceType: 'text' | 'image' | 'diagram_closeup' | 'icon'`
- `cardBackStyle: 'solid' | 'pattern' | 'gradient' | 'image'`
- `cardBackColor: string`
- `cardBackImage: string`
- `matchType: 'term_definition' | 'label_description' | 'image_name' | 'function_structure'`
- `matchedCardBehavior: 'stay_revealed' | 'fade_out' | 'move_to_side' | 'shrink'`
- `mismatchPenalty: 'none' | 'time_add' | 'score_deduct'`
- `showExplanationOnMatch: boolean`
- `peekDurationMs: number`
- `progressiveBatchSize: number`

#### 11.8 BranchingConfig gaps

Current fields: `nodes`, `startNodeId`, `showPathTaken`, `allowBacktrack`, `showConsequences`, `multipleValidEndings`, `instructions`

Missing from research (04_branching_scenario_games.md):
- `characters: Character[]`
- `sceneBackgrounds: Record<string, string>`
- `stateVariables: StateVariable[]`
- `initialState: Record<string, number | string | boolean>`
- `stateDisplay: { position, showVariables }`
- `minimap: { enabled, position, style }`
- `narrativeStructure: 'branch_and_bottleneck' | 'foldback' | 'gauntlet' | 'full_branch'`
- `transitionStyle: 'fade' | 'slide' | 'zoom' | 'none'`
- `visualConfig: { nodeStyles, edgeStyles, theme }`
- `consequenceVisualization: 'text' | 'animation' | 'state_change' | 'combined'`

#### 11.9 CompareConfig gaps

Current fields: `diagramA`, `diagramB`, `expectedCategories`, `highlightMatching`, `instructions`

Missing from research (05_compare_contrast_games.md):
- `comparisonMode: 'slider' | 'side_by_side' | 'overlay' | 'venn' | 'spot_difference'`
- `categoryTypes: string[]`
- `categoryLabels: Record<string, string>`
- `categoryColors: Record<string, string>`
- `explorationEnabled: boolean`
- `explorationDurationMs: number`
- `zonePairings: Array<{ zoneA: string; zoneB: string }>`
- `syncZoom: boolean`
- `showDescriptions: boolean`
- `sliderOrientation: 'horizontal' | 'vertical'`

### Missing Fields on Base Types

#### 11.10 SequenceConfigItem gaps

Current: `{ id, text, description }`

Missing:
- `imageUrl: string`
- `iconName: string`
- `displayType: 'text_only' | 'image_and_text' | 'image_only' | 'icon_and_text' | 'numbered_text'`

#### 11.11 SortingItem gaps

Current: `{ id, text, correctCategoryId, description }`

Missing:
- `imageUrl: string`
- `iconName: string`
- `correctCategoryIds: string[]` (for multi-category support)

#### 11.12 MemoryMatchPair gaps

Current: `{ id, front, back, frontType, backType }`

Missing:
- `explanation: string`
- `matchType: string`
- `category: string`

#### 11.13 DecisionNode gaps

Current: `{ id, question, description, imageUrl, options, isEndNode, endMessage }`

Missing:
- `nodeType: 'decision' | 'information' | 'checkpoint' | 'consequence'`
- `characterId: string`
- `backgroundKey: string`
- `timeLimit: number`
- `endingIllustration: string`

#### 11.14 DecisionOption gaps

Current: `{ id, text, nextNodeId, isCorrect, consequence, points }`

Missing:
- `stateChanges: Record<string, number | string | boolean>`
- `revealsInfo: string`
- `requiredState: Record<string, unknown>` (conditional availability)

#### 11.15 PathWaypoint gaps

Current: `{ zoneId, order }`

Missing:
- `type: 'waypoint' | 'gate' | 'valve' | 'fork'`
- `controlPoints: [number, number][]` (for bezier curves)
- `gateConfig: { interaction, label }`

#### 11.16 Label gaps

Current: `{ id, text, correctZoneId }`

Missing:
- `iconName: string`
- `thumbnailUrl: string`
- `description: string` (for description_card label style)
- `displayType: 'text_only' | 'text_with_icon' | 'thumbnail' | 'description_card'`

### Missing Top-Level Fields on InteractiveDiagramBlueprint

Current blueprint has config fields for: `sequenceConfig`, `sortingConfig`, `memoryMatchConfig`, `branchingConfig`, `compareConfig`, `descriptionMatchingConfig`

Missing:
- `clickToIdentifyConfig: ClickToIdentifyConfig`
- `tracePathConfig: TracePathConfig`
- `dragDropConfig: DragDropConfig`

### Type Mismatches with Backend

| Field | Frontend Type | Backend Type | Issue |
|-------|--------------|-------------|-------|
| `descriptionMatchingConfig` | `{ descriptions?: Record<string,string>; mode?: string }` | Backend sends full config with connecting_lines, etc. | Frontend type is too narrow |
| `highlightMatching` on CompareConfig | `boolean` (defined but never read) | Backend may populate | Dead field |
| `SortingItem.correctCategoryId` | `string` (single) | Backend could send array for multi-category | Single vs array mismatch potential |

---

## 12. useInteractiveDiagramState.ts

**File:** `frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts` (1675 lines)
**Research Reference:** All research documents (Zustand state management)

### Current Capabilities

- Full Zustand store with 48+ state fields and 30+ actions
- Game initialization from `InteractiveDiagramBlueprint` with mode-specific progress setup
- Label placement with correct/incorrect handling and delta-based scoring (Fix 1.2)
- Per-mechanic progress tracking: `sequencingProgress`, `sortingProgress`, `memoryMatchProgress`, `branchingProgress`, `compareProgress`, `descriptionMatchingState`
- Multi-scene management: `initializeMultiSceneGame`, `advanceToScene`, `completeScene`, `advanceToNextTask`
- Multi-mode transitions: `checkModeTransition`, `transitionToMode` with 12 trigger types
- Temporal intelligence: `updateVisibleZones`, mutex constraints, parent-child zone reveal
- Scene-to-blueprint conversion: `_sceneToBlueprint()` with per-task zone/label filtering

### Missing State for New Config Features

| State Field | Research Need | Current State |
|-------------|--------------|---------------|
| zoomLevel / panOffset | 07_drag_drop_richness.md | Not tracked |
| explorationPhase (boolean) | 05, 06 | Not tracked |
| explorationTimeRemaining | 05, 06 | Not tracked |
| stateVariables (branching) | 04_branching_scenario.md | Not tracked |
| matchedPairVisualState | 02_memory_match.md | Not tracked |
| leaderLineConnections | 07_drag_drop_richness.md | Not tracked |
| peekPhaseActive | 02_memory_match.md | Not tracked |
| freehandPathData | 06_click_trace_description.md | Not tracked |
| particleAnimationState | 06_click_trace_description.md | Not tracked |

### Missing Actions

| Action | Research Need | Current State |
|--------|--------------|---------------|
| setZoomLevel(level) | 07 | Not defined |
| setPanOffset(x, y) | 07 | Not defined |
| startExplorationPhase() | 05, 06 | Not defined |
| endExplorationPhase() | 05, 06 | Not defined |
| updateStateVariable(name, value) | 04 | Not defined |
| startPeekPhase() | 02 | Not defined |
| endPeekPhase() | 02 | Not defined |
| updateFreehandPath(points) | 06 | Not defined |
| setPlacementMode(mode) | 07 | Not defined |

### Existing Issues Found During Audit

1. **`_sceneToBlueprint` missing fields**: Does not forward `clickToIdentifyConfig`, `tracePathConfig`, or `dragDropConfig` from scene to blueprint (these configs do not exist yet, but will be needed).

2. **Score reset on mode transition** (L1517): `score: 0` on every mode transition means cumulative scoring across modes is not possible. Research docs 01-07 suggest cumulative scoring across all phases of a multi-mechanic game should be supported as an option.

3. **`transitionToMode` re-initializes progress** (L1410-1459): Good behavior for mode transitions, but does not preserve any exploration state that might have been gathered during an explore-then-test phase.

4. **No persistence of new mechanic states**: `usePersistence.ts` hook exists but does not serialize/deserialize the new per-mechanic progress types (sequencingProgress, sortingProgress, etc.).

---

## 13. Summary Matrix

### Gap Severity by Component

| Component | Missing Visual Components | Missing Interactions | Missing Config Props | New Components Needed | Severity |
|-----------|--------------------------|---------------------|---------------------|-----------------------|----------|
| SequenceBuilder | 8 | 12 | 14 | 8 | CRITICAL |
| SortingCategories | 8 | 9 | 11 | 5 | CRITICAL |
| MemoryMatch | 10 | 8 | 13 | 7 | CRITICAL |
| BranchingScenario | 10 | 9 | 10 | 9 | CRITICAL |
| CompareContrast | 9 | 10 | 13 | 8 | CRITICAL |
| HotspotManager | 7 | 8 | 8 | 5 | HIGH |
| PathDrawer | 9 | 11 | 10 | 8 | CRITICAL |
| DescriptionMatcher | 7 | 8 | 10 | 5 | HIGH |
| DiagramCanvas | 9 | 10 | 10 | 8 | HIGH |
| types.ts | N/A | N/A | 60+ fields | 3 new config interfaces | CRITICAL |
| useInteractiveDiagramState | N/A | N/A | 9 state fields, 9 actions | N/A | MODERATE |

### Missing Config Interface Count by Mechanic

| Mechanic | Existing Config | Missing Fields | Missing Config Interface |
|----------|----------------|----------------|--------------------------|
| drag_drop | None | All | DragDropConfig (11 fields) |
| click_to_identify | None | All | ClickToIdentifyConfig (7 fields) |
| trace_path | None | All | TracePathConfig (8 fields) |
| sequencing | SequenceConfig (5 fields) | 9 fields | Extend existing |
| sorting_categories | SortingConfig (5 fields) | 10 fields | Extend existing |
| memory_match | MemoryMatchConfig (5 fields) | 11 fields | Extend existing |
| branching_scenario | BranchingConfig (7 fields) | 10 fields | Extend existing |
| compare_contrast | CompareConfig (4 fields) | 10 fields | Extend existing |
| description_matching | Partial (2 fields) | 7 fields | Extend existing |
| hierarchical | No config | Uses zoneGroups | Consider dedicated config |

### Total New Artifacts Required

| Category | Count |
|----------|-------|
| New config interfaces (types.ts) | 3 (ClickToIdentifyConfig, TracePathConfig, DragDropConfig) |
| Extended config interfaces | 6 (SequenceConfig, SortingConfig, MemoryMatchConfig, BranchingConfig, CompareConfig, DescriptionMatchingConfig) |
| New base type fields | 16 (on SequenceConfigItem, SortingItem, MemoryMatchPair, DecisionNode, DecisionOption, PathWaypoint, Label) |
| New blueprint top-level fields | 3 (clickToIdentifyConfig, tracePathConfig, dragDropConfig) |
| New React components total | ~63 across all mechanics |
| New Zustand state fields | 9 |
| New Zustand actions | 9 |
| New npm dependencies suggested | 2 (react-compare-slider, react-zoom-pan-pinch) |

### Priority Ranking for Implementation

1. **types.ts** -- All other work depends on correct type definitions
2. **DiagramCanvas.tsx** -- Core rendering component used by all mechanics; leader lines and zoom/pan affect every game
3. **SequenceBuilder.tsx** -- Most primitive implementation relative to research spec
4. **CompareContrast.tsx** -- Only supports 1 of 5 specified modes
5. **MemoryMatch.tsx** -- Broken 3D flip animation, missing all variants
6. **PathDrawer.tsx** -- Straight lines only, missing core SVG path features
7. **BranchingScenario.tsx** -- No visual novel elements, no state system
8. **SortingCategories.tsx** -- Only bucket mode of 5 specified
9. **HotspotManager.tsx** -- Functionally adequate but missing exploration and magnification
10. **DescriptionMatcher.tsx** -- Three modes work; needs connecting lines and deferred eval
11. **useInteractiveDiagramState.ts** -- Add new state fields as components are built
12. **MechanicRouter.tsx** -- Update props forwarding as child components gain new config props
