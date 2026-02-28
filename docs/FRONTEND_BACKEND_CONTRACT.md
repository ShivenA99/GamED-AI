# Frontend-Backend Blueprint Contract

**Version:** 1.0
**Date:** 2026-02-14
**Scope:** Complete specification of the JSON blueprint the backend must produce for the frontend `InteractiveDiagramGame` to render a game.

---

## Table of Contents

1. [Blueprint Dispatch: Single-Scene vs Multi-Scene](#1-blueprint-dispatch)
2. [Single-Scene Blueprint (`InteractiveDiagramBlueprint`)](#2-single-scene-blueprint)
3. [Multi-Scene Blueprint (`MultiSceneInteractiveDiagramBlueprint`)](#3-multi-scene-blueprint)
4. [Shared Sub-Structures](#4-shared-sub-structures)
5. [Per-Mechanic Contracts (10 Mechanics)](#5-per-mechanic-contracts)
6. [Scoring Contract](#6-scoring-contract)
7. [Feedback Contract](#7-feedback-contract)
8. [Mode Transitions Contract](#8-mode-transitions-contract)
9. [Temporal Intelligence Contract](#9-temporal-intelligence-contract)
10. [Case Normalization Rules](#10-case-normalization-rules)
11. [Zod Validation Defaults](#11-zod-validation-defaults)
12. [Common Failure Modes](#12-common-failure-modes)

---

## 1. Blueprint Dispatch

The frontend detects the blueprint type by checking `is_multi_scene`:

```
if raw.is_multi_scene === true  -->  MultiSceneInteractiveDiagramBlueprint
else                            -->  InteractiveDiagramBlueprint (single-scene)
```

Both types are validated through Zod schemas. Unknown fields are tolerated (`.passthrough()`). Missing required fields are filled with defaults where possible.

---

## 2. Single-Scene Blueprint

### Root Structure: `InteractiveDiagramBlueprint`

Every field is listed below. **REQUIRED** means Zod will error or the game will break without it. **DEFAULT** means Zod fills it. **OPTIONAL** means the frontend gracefully handles absence.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `templateType` | `string` | DEFAULT | `"INTERACTIVE_DIAGRAM"` | Must be `"INTERACTIVE_DIAGRAM"` |
| `title` | `string` | DEFAULT | `"Untitled Game"` | Game title shown in header |
| `narrativeIntro` | `string` | DEFAULT | `""` | Introductory text shown before gameplay |
| `diagram` | `Diagram` | **REQUIRED** | -- | The diagram image and zone definitions |
| `labels` | `Label[]` | DEFAULT | `[]` | Draggable label items |
| `distractorLabels` | `DistractorLabel[]` | OPTIONAL | -- | Incorrect labels to confuse player |
| `tasks` | `Task[]` | DEFAULT | `[]` | Legacy task definitions |
| `animationCues` | `AnimationCues` | DEFAULT | see below | Text-based animation cue messages |
| `animations` | `StructuredAnimations` | OPTIONAL | -- | Structured animation specs |
| `mechanics` | `Mechanic[]` | OPTIONAL | -- | Flat list of game mechanics. `mechanics[0].type` is the starting mode |
| `modeTransitions` | `ModeTransition[]` | OPTIONAL | -- | Transition rules between mechanics |
| `interactionMode` | `InteractionMode` | OPTIONAL | -- | Starting mode shorthand (derived from `mechanics[0].type` if omitted) |
| `zoneGroups` | `ZoneGroup[]` | OPTIONAL | -- | Hierarchical zone groupings |
| `identificationPrompts` | `IdentificationPrompt[]` | OPTIONAL | -- | Prompts for click_to_identify mode |
| `selectionMode` | `"sequential" \| "any_order"` | OPTIONAL | -- | Order of identification prompts |
| `paths` | `TracePath[]` | OPTIONAL | -- | Path definitions for trace_path mode |
| `mediaAssets` | `MediaAsset[]` | OPTIONAL | -- | Additional media assets |
| `temporalConstraints` | `TemporalConstraint[]` | OPTIONAL | -- | Petri Net-style zone ordering constraints |
| `motionPaths` | `MotionPath[]` | OPTIONAL | -- | Animation keyframes for assets |
| `revealOrder` | `string[]` | OPTIONAL | -- | Suggested zone reveal order |
| `scoringStrategy` | `ScoringStrategy` | OPTIONAL | -- | Global scoring configuration |
| `hints` | `Hint[]` | OPTIONAL | -- | Per-zone hint text |
| `feedbackMessages` | `FeedbackMessages` | OPTIONAL | -- | Score-based feedback strings |
| `sequenceConfig` | `SequenceConfig` | OPTIONAL | -- | Config for `sequencing` mechanic |
| `sortingConfig` | `SortingConfig` | OPTIONAL | -- | Config for `sorting_categories` mechanic |
| `memoryMatchConfig` | `MemoryMatchConfig` | OPTIONAL | -- | Config for `memory_match` mechanic |
| `branchingConfig` | `BranchingConfig` | OPTIONAL | -- | Config for `branching_scenario` mechanic |
| `compareConfig` | `CompareConfig` | OPTIONAL | -- | Config for `compare_contrast` mechanic |
| `descriptionMatchingConfig` | `DescriptionMatchingConfig` | OPTIONAL | -- | Config for `description_matching` mechanic |
| `clickToIdentifyConfig` | `ClickToIdentifyConfig` | OPTIONAL | -- | Config for `click_to_identify` mechanic |
| `tracePathConfig` | `TracePathConfig` | OPTIONAL | -- | Config for `trace_path` mechanic |
| `dragDropConfig` | `DragDropConfig` | OPTIONAL | -- | Config for `drag_drop` mechanic |
| `timedChallengeWrappedMode` | `InteractionMode` | OPTIONAL | -- | Which mechanic to wrap with timer |
| `timeLimitSeconds` | `number` | OPTIONAL | -- | Time limit for timed_challenge |

---

## 3. Multi-Scene Blueprint

### Root Structure: `MultiSceneInteractiveDiagramBlueprint`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `templateType` | `string` | DEFAULT | `"INTERACTIVE_DIAGRAM"` | |
| `title` | `string` | DEFAULT | `"Untitled Game"` | |
| `narrativeIntro` | `string` | DEFAULT | `""` | |
| `is_multi_scene` | `true` (literal) | **REQUIRED** | -- | Discriminator flag. Must be `true`. |
| `game_sequence` | `GameSequence` | **REQUIRED** | -- | The sequence of scenes |
| `animationCues` | `AnimationCues` | DEFAULT | see below | |
| `animations` | unknown | OPTIONAL | -- | |
| `feedbackMessages` | `FeedbackMessages` | OPTIONAL | -- | |
| `global_hints` | `Hint[]` | OPTIONAL | -- | |
| `mediaAssets` | unknown | OPTIONAL | -- | |
| `temporalConstraints` | `TemporalConstraint[]` | OPTIONAL | -- | |
| `motionPaths` | `MotionPath[]` | OPTIONAL | -- | |

### `GameSequence`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `sequence_id` | `string` | **REQUIRED** | -- | Unique sequence identifier |
| `sequence_title` | `string` | DEFAULT | `""` | |
| `sequence_description` | `string` | OPTIONAL | -- | |
| `total_scenes` | `number` | DEFAULT | `0` | Total scene count |
| `scenes` | `GameScene[]` | DEFAULT | `[]` | Ordered list of scenes |
| `progression_type` | `"linear" \| "zoom_in" \| "depth_first" \| "branching"` | DEFAULT | `"linear"` | How scenes progress |
| `total_max_score` | `number` | DEFAULT | `0` | Sum of all scene max scores |
| `passing_score` | `number` | OPTIONAL | -- | Minimum score to pass |
| `bonus_for_no_hints` | `boolean` | OPTIONAL | -- | |
| `require_completion` | `boolean` | OPTIONAL | -- | |
| `allow_scene_skip` | `boolean` | OPTIONAL | -- | |
| `allow_revisit` | `boolean` | OPTIONAL | -- | |
| `estimated_duration_minutes` | `number` | OPTIONAL | -- | |
| `difficulty_level` | `"beginner" \| "intermediate" \| "advanced"` | OPTIONAL | -- | |

### `GameScene`

Each scene is self-contained. It has its own diagram, zones, labels, and mechanic configs. The frontend converts each scene into an `InteractiveDiagramBlueprint` via `sceneToBlueprint()`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `scene_id` | `string` | **REQUIRED** | -- | Unique scene identifier |
| `scene_number` | `number` | DEFAULT | `1` | Display order number |
| `title` | `string` | DEFAULT | `""` | Scene title |
| `narrative_intro` | `string` | DEFAULT | `""` | Scene intro text |
| `diagram` | `SceneDiagram` | **REQUIRED** | -- | `{ type?, assetUrl?, svgContent?, assetPrompt? }` |
| `zones` | `Zone[]` | DEFAULT | `[]` | Zone definitions for this scene |
| `labels` | `Label[]` | DEFAULT | `[]` | Label definitions for this scene |
| `max_score` | `number` | DEFAULT | `0` | Max achievable score for this scene |
| `prerequisite_scene` | `string \| null` | OPTIONAL | -- | scene_id that must complete first |
| `child_scenes` | `string[]` | OPTIONAL | -- | Scene IDs that branch from this |
| `reveal_trigger` | `"all_correct" \| "percentage" \| "specific_zones" \| "manual"` | OPTIONAL | -- | When to unlock next scene |
| `reveal_threshold` | `number` | OPTIONAL | -- | Percentage for "percentage" trigger |
| `time_limit_seconds` | `number` | OPTIONAL | -- | |
| `hints_enabled` | `boolean` | OPTIONAL | -- | |
| `feedback_enabled` | `boolean` | OPTIONAL | -- | |
| `tasks` | `SceneTask[]` | DEFAULT | `[]` | Tasks (phases) within this scene |
| `mechanics` | `Mechanic[]` | OPTIONAL | -- | Mechanic list for this scene |
| `interaction_mode` | `InteractionMode` | OPTIONAL | -- | Starting mode shorthand |
| `mode_transitions` | `ModeTransition[]` | OPTIONAL | -- | |
| `zoneGroups` | `ZoneGroup[]` | OPTIONAL | -- | |
| `paths` | `TracePath[]` | OPTIONAL | -- | |
| `hints` | `Hint[]` | OPTIONAL | -- | |
| `distractor_labels` | `DistractorLabel[]` | OPTIONAL | -- | |
| Per-mechanic configs (camelCase) | see below | OPTIONAL | -- | `sequenceConfig`, `sortingConfig`, etc. |
| Per-mechanic configs (snake_case) | see below | OPTIONAL | -- | `sequence_config`, `sorting_config`, etc. (auto-normalized) |
| `identificationPrompts` / `identification_prompts` | `IdentificationPrompt[]` | OPTIONAL | -- | |
| `temporalConstraints` / `temporal_constraints` | `TemporalConstraint[]` | OPTIONAL | -- | |
| `motionPaths` / `motion_paths` | `MotionPath[]` | OPTIONAL | -- | |
| `scoringStrategy` / `scoring_strategy` | `ScoringStrategy` | OPTIONAL | -- | |

### `SceneTask`

Tasks are phases within a single scene. Each task activates a subset of zones/labels with a specific mechanic. The same diagram image is used for all tasks in a scene.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `task_id` | `string` | **REQUIRED** | -- | Unique task identifier |
| `title` | `string` | DEFAULT | `""` | Task title |
| `mechanic_type` | `InteractionMode` | **REQUIRED** | -- | Which mechanic this task uses |
| `zone_ids` | `string[]` | DEFAULT | `[]` | Zone IDs active in this task. Empty = all zones. |
| `label_ids` | `string[]` | DEFAULT | `[]` | Label IDs active in this task. Empty = all labels. |
| `instructions` | `string` | OPTIONAL | -- | Task-specific instruction text |
| `scoring_weight` | `number` | DEFAULT | `1` | Relative weight for scoring |
| `config` | `Record<string, unknown>` | OPTIONAL | -- | Task-specific config override |

---

## 4. Shared Sub-Structures

### `Diagram` (single-scene root)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `assetPrompt` | `string` | DEFAULT | `""` | AI generation prompt for the image |
| `assetUrl` | `string` | OPTIONAL | -- | **URL to the diagram image. CRITICAL for rendering.** |
| `width` | `number` | OPTIONAL | -- | Image width in pixels. Frontend defaults to 800 if missing. |
| `height` | `number` | OPTIONAL | -- | Image height in pixels. Frontend defaults to 600 if missing. |
| `zones` | `Zone[]` | DEFAULT | `[]` | Zone overlay definitions |
| `overlaySpec` | `InteractiveOverlaySpec` | OPTIONAL | -- | Full overlay specification |

**IMPORTANT:** `assetUrl` is essential. Without it, the game has no background image. `width` and `height` are coerced from string (e.g. `"800px"`) to number automatically. Zones use 0-100 percentage coordinates, which are scaled to the actual image dimensions.

### `Zone`

Zones are interactive regions on the diagram image. Coordinates use a **0-100 percentage** coordinate system.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **REQUIRED** | -- | Unique zone identifier |
| `label` | `string` | **REQUIRED** | -- | Display name of the zone (used for matching, UI display) |
| `x` | `number` | OPTIONAL | -- | X position (0-100%). Required for circle/rect shapes. |
| `y` | `number` | OPTIONAL | -- | Y position (0-100%). Required for circle/rect shapes. |
| `radius` | `number` | OPTIONAL | -- | Radius for circle shapes (0-100% scale) |
| `width` | `number` | OPTIONAL | -- | Width for rect shapes (0-100% scale) |
| `height` | `number` | OPTIONAL | -- | Height for rect shapes (0-100% scale) |
| `zone_type` | `"point" \| "area"` | OPTIONAL | -- | `"point"` = small dot indicator, `"area"` = precise boundary |
| `shape` | `"circle" \| "polygon" \| "rect"` | OPTIONAL | -- | Shape of the interactive overlay |
| `points` | `[number, number][]` | OPTIONAL | -- | Polygon vertices as `[x, y]` pairs (0-100% each). **Required for polygon shapes.** |
| `center` | `{ x: number, y: number }` | OPTIONAL | -- | Center point for label placement (auto-calculated for polygons) |
| `parentZoneId` | `string` | OPTIONAL | -- | ID of parent zone (for hierarchical) |
| `hierarchyLevel` | `number` | OPTIONAL | -- | 1 = root, 2 = child, 3 = grandchild |
| `childZoneIds` | `string[]` | OPTIONAL | -- | IDs of child zones |
| `description` | `string` | OPTIONAL | -- | Educational description. **Used by `description_matching` mechanic.** |
| `hint` | `string` | OPTIONAL | -- | Hint text for this zone |
| `difficulty` | `number` | OPTIONAL | -- | 1-5 difficulty rating |
| `focusOrder` | `number` | OPTIONAL | -- | Tab index for keyboard navigation |
| `pronunciationGuide` | `string` | OPTIONAL | -- | Phonetic guide for screen readers |
| `keyboardShortcut` | `string` | OPTIONAL | -- | Custom keyboard shortcut |
| `diagramType` | `string` | OPTIONAL | -- | |
| `metadata` | `Record<string, unknown>` | OPTIONAL | -- | Arbitrary metadata |

**Zone shape resolution:**
- If `shape === "polygon"` then `points` must be an array of `[x, y]` tuples
- If `shape === "circle"` then `x`, `y`, `radius` must be set
- If `shape === "rect"` then `x`, `y`, `width`, `height` must be set
- If no shape is specified, the frontend uses `x`, `y` as a point position

### Enhanced Zone fields (for `drag_drop` with leader lines)

| Field | Type | Description |
|-------|------|-------------|
| `pin_anchor` | `{ x: number, y: number }` | Pin position for leader line anchor |
| `label_position` | `{ x: number, y: number }` | Label card position |
| `category` | `string` | Zone category for grouped tray layout |
| `function` | `string` | Functional description |

### `Label`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **REQUIRED** | -- | Unique label identifier |
| `text` | `string` | **REQUIRED** | -- | Display text of the label |
| `correctZoneId` | `string` | **REQUIRED** | -- | ID of the zone this label belongs to |

**CRITICAL:** `correctZoneId` must match an actual `zone.id`. The frontend attempts text-matching fallback if the zone ID is not found, but this is fragile.

### Enhanced Label fields (for `drag_drop`)

| Field | Type | Description |
|-------|------|-------------|
| `icon` | `string` | Emoji or icon identifier |
| `thumbnail_url` | `string` | URL to thumbnail image |
| `description` | `string` | Longer description for label card |
| `category` | `string` | Category for grouped tray layout |

### `DistractorLabel`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Unique distractor identifier |
| `text` | `string` | **REQUIRED** | Display text |
| `explanation` | `string` | **REQUIRED** | Why this is wrong (shown as feedback) |

Enhanced distractor fields:

| Field | Type | Description |
|-------|------|-------------|
| `confusion_target_zone_id` | `string` | Which zone this distractor is designed to confuse |
| `category` | `string` | Category for grouped display |

### `Mechanic`

Each entry in the `mechanics` array defines a game mechanic with optional per-mechanic scoring and feedback.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `InteractionMode` | **REQUIRED** | One of the 11 mode strings |
| `config` | `Record<string, unknown>` | OPTIONAL | Generic config override |
| `scoring` | `MechanicScoring` | OPTIONAL | Per-mechanic scoring config |
| `feedback` | `MechanicFeedback` | OPTIONAL | Per-mechanic feedback messages |

### `MechanicScoring`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strategy` | `string` | -- | Scoring strategy name |
| `points_per_correct` | `number` | `10` | Points awarded per correct action |
| `max_score` | `number` | -- | Cap on total mechanic score |
| `partial_credit` | `boolean` | -- | Allow partial credit |

### `MechanicFeedback`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `on_correct` | `string` | `"Correct!"` | Message on correct action |
| `on_incorrect` | `string` | `"Try again!"` | Message on incorrect action |
| `on_completion` | `string` | `"Well done!"` | Message on mechanic completion |
| `misconceptions` | `Array<{ trigger_label: string, message: string }>` | -- | Misconception-specific feedback |

**Misconceptions normalization:** The backend may send misconceptions as either:
- Array format: `[{ "trigger_label": "chloroplast", "message": "..." }]` (preferred)
- Dict format: `{ "chloroplast": "..." }` (auto-converted by frontend)

### `AnimationCues`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labelDrag` | `string` | -- | Message during drag |
| `correctPlacement` | `string` | `"Correct!"` | Message on correct placement |
| `incorrectPlacement` | `string` | `"Try again!"` | Message on incorrect placement |
| `allLabeled` | `string` | -- | Message when all labels placed |

### `FeedbackMessages`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `perfect` | `string` | `"Perfect score!"` | 100% score feedback |
| `good` | `string` | `"Good job!"` | Passing score feedback |
| `retry` | `string` | `"Try again!"` | Failing score feedback |

### `ScoringStrategy`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `string` | **REQUIRED** | Strategy identifier |
| `base_points_per_zone` | `number` | `10` | Points per correct answer |
| `time_bonus_enabled` | `boolean` | -- | Enable time-based bonus |
| `partial_credit` | `boolean` | -- | Allow partial credit |
| `max_score` | `number` | -- | Score cap |

### `Hint`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `zoneId` | `string` | **REQUIRED** | Zone this hint applies to |
| `hintText` | `string` | **REQUIRED** | Hint text content |

### `ModeTransition`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | `InteractionMode` | **REQUIRED** | Source mechanic mode |
| `to` | `InteractionMode` | **REQUIRED** | Target mechanic mode |
| `trigger` | `ModeTransitionTrigger` | **REQUIRED** | When to trigger |
| `triggerValue` | `number \| string[]` | OPTIONAL | Percentage threshold or zone IDs |
| `animation` | `"fade" \| "slide" \| "zoom" \| "none"` | OPTIONAL | Transition animation |
| `message` | `string` | OPTIONAL | Message shown during transition |

### `ModeTransitionTrigger` values

| Trigger | Description | triggerValue |
|---------|-------------|-------------|
| `all_zones_labeled` | All zones correctly labeled | -- |
| `path_complete` | All paths traced | -- |
| `percentage_complete` | X% of zones correct | `number` (percentage) |
| `specific_zones` | Specific zone IDs completed | `string[]` (zone IDs) |
| `time_elapsed` | After X seconds | `number` (seconds) |
| `user_choice` | Manual mode switch | -- |
| `hierarchy_level_complete` | Hierarchy level done | -- |
| `identification_complete` | All prompts answered | -- |
| `sequence_complete` | Sequence correctly ordered | -- |
| `sorting_complete` | All items sorted correctly | -- |
| `memory_complete` | All pairs matched | -- |
| `branching_complete` | Reached end node | -- |
| `compare_complete` | All comparisons categorized | -- |
| `description_complete` | All descriptions matched | -- |

---

## 5. Per-Mechanic Contracts

Each mechanic has a `configKey` in the registry that maps to a specific field on the blueprint root. When the frontend initializes a mechanic, it reads from that field.

### Interaction Modes

| InteractionMode | configKey on blueprint | Needs DnD Context |
|----------------|------------------------|-------------------|
| `drag_drop` | `dragDropConfig` | YES |
| `click_to_identify` | `clickToIdentifyConfig` | NO |
| `trace_path` | `tracePathConfig` | NO |
| `hierarchical` | (none - uses zoneGroups) | YES |
| `description_matching` | `descriptionMatchingConfig` | NO |
| `compare_contrast` | `compareConfig` | NO |
| `sequencing` | `sequenceConfig` | NO |
| `timed_challenge` | (wraps another mechanic) | depends on wrapped |
| `sorting_categories` | `sortingConfig` | NO |
| `memory_match` | `memoryMatchConfig` | NO |
| `branching_scenario` | `branchingConfig` | NO |

---

### 5.1 `drag_drop`

**Blueprint config key:** `dragDropConfig`

**Required blueprint data:**
- `labels[]` with at least 1 entry (each with `id`, `text`, `correctZoneId`)
- `diagram.zones[]` with at least 1 entry (each with `id`, `label`, position data)
- `diagram.assetUrl` (the background image)

**Config (`DragDropConfig`):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `interaction_mode` | `"drag_drop" \| "click_to_place" \| "reverse"` | -- | Interaction variant |
| `feedback_timing` | `"immediate" \| "deferred"` | -- | When to show feedback |
| `zone_idle_animation` | `"none" \| "pulse" \| "glow" \| "breathe"` | -- | Zone idle visual |
| `zone_hover_effect` | `"highlight" \| "scale" \| "glow" \| "none"` | -- | Zone hover visual |
| `label_style` | `"text" \| "text_with_icon" \| "text_with_thumbnail" \| "text_with_description"` | -- | Label card style |
| `placement_animation` | `"spring" \| "ease" \| "instant"` | -- | Drop animation |
| `spring_stiffness` | `number` | -- | Spring physics |
| `spring_damping` | `number` | -- | Spring physics |
| `incorrect_animation` | `"shake" \| "bounce_back" \| "fade_out"` | -- | Wrong answer animation |
| `show_placement_particles` | `boolean` | -- | Particle effects on drop |
| `leader_line_style` | `"straight" \| "elbow" \| "curved" \| "fluid" \| "none"` | -- | Connection line style |
| `leader_line_color` | `string` | -- | Line color |
| `leader_line_width` | `number` | -- | Line width |
| `leader_line_animate` | `boolean` | -- | Animate line drawing |
| `pin_marker_shape` | `"circle" \| "diamond" \| "arrow" \| "none"` | -- | Pin marker shape |
| `label_anchor_side` | `"auto" \| "left" \| "right" \| "top" \| "bottom"` | -- | Label placement side |
| `tray_position` | `"bottom" \| "right" \| "left" \| "top"` | -- | Label tray position |
| `tray_layout` | `"horizontal" \| "vertical" \| "grid" \| "grouped"` | -- | Tray layout mode |
| `tray_show_remaining` | `boolean` | -- | Show remaining count |
| `tray_show_categories` | `boolean` | -- | Group labels by category |
| `show_distractors` | `boolean` | -- | Include distractor labels |
| `distractor_count` | `number` | -- | Number of distractors |
| `distractor_rejection_mode` | `"immediate" \| "deferred"` | -- | When to reject distractors |
| `zoom_enabled` | `boolean` | -- | Enable zoom/pan |
| `zoom_min` / `zoom_max` | `number` | -- | Zoom limits |
| `minimap_enabled` | `boolean` | -- | Show minimap when zoomed |
| `max_attempts` | `number` | -- | Max wrong attempts |
| `shuffle_labels` | `boolean` | -- | Randomize label order |

**Legacy aliases:** `showLeaderLines`, `snapAnimation`, `showInfoPanelOnCorrect`, `maxAttempts`, `shuffleLabels`, `showHints`

**Max score:** `labels.length * points_per_correct`

**Completion:** All labels placed correctly.

---

### 5.2 `click_to_identify`

**Blueprint config key:** `clickToIdentifyConfig`

**Required blueprint data:**
- `identificationPrompts[]` with at least 1 entry
- `diagram.zones[]` (zones referenced by prompts)
- `diagram.assetUrl`, `diagram.width`, `diagram.height`

**`IdentificationPrompt`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `zoneId` | `string` | **REQUIRED** | Zone the player must click |
| `prompt` | `string` | **REQUIRED** | Question text shown to player |
| `order` | `number` | OPTIONAL | Display order |

**Config (`ClickToIdentifyConfig`):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `promptStyle` | `"naming" \| "functional"` | `"naming"` | Prompt display style |
| `selectionMode` | `"sequential" \| "any_order"` | `"sequential"` | Prompt ordering |
| `highlightStyle` | `"subtle" \| "outlined" \| "invisible"` | `"subtle"` | Zone highlight style |
| `magnificationEnabled` | `boolean` | -- | Enable zoom on hover |
| `magnificationFactor` | `number` | -- | Zoom factor |
| `exploreModeEnabled` | `boolean` | -- | Allow free exploration first |
| `exploreTimeLimitSeconds` | `number \| null` | -- | Time limit for explore mode |
| `showZoneCount` | `boolean` | -- | Show remaining zone count |
| `instructions` | `string` | -- | Instruction text |

**Max score:** `identificationPrompts.length * points_per_correct`

**Completion:** `currentPromptIndex >= totalPrompts`

---

### 5.3 `trace_path`

**Blueprint config key:** `tracePathConfig`

**Required blueprint data:**
- `paths[]` with at least 1 `TracePath`
- `diagram.zones[]` (zones referenced as waypoints)
- `diagram.assetUrl`, `diagram.width`, `diagram.height`

**`TracePath`:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **REQUIRED** | -- | Path identifier |
| `waypoints` | `PathWaypoint[]` | DEFAULT | `[]` | Ordered waypoints |
| `description` | `string` | DEFAULT | `""` | Path description text |
| `requiresOrder` | `boolean` | DEFAULT | `true` | Must visit in order? |

**`PathWaypoint`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `zoneId` | `string` | **REQUIRED** | Zone at this waypoint |
| `order` | `number` | **REQUIRED** | Position in path (0-based) |
| `type` | `"standard" \| "gate" \| "branch_point" \| "terminus"` | OPTIONAL | Waypoint behavior type |
| `svg_path_data` | `string` | OPTIONAL | Custom SVG path segment |

**Config (`TracePathConfig`):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pathType` | `"linear" \| "branching" \| "circular"` | `"linear"` | Path topology |
| `drawingMode` | `"click_waypoints" \| "freehand"` | `"click_waypoints"` | Input method |
| `particleTheme` | `"dots" \| "arrows" \| "droplets" \| "cells" \| "electrons"` | `"dots"` | Particle visual |
| `particleSpeed` | `"slow" \| "medium" \| "fast"` | `"medium"` | Animation speed |
| `colorTransitionEnabled` | `boolean` | -- | Color change along path |
| `showDirectionArrows` | `boolean` | -- | Show direction arrows |
| `showWaypointLabels` | `boolean` | -- | Show labels at waypoints |
| `showFullFlowOnComplete` | `boolean` | -- | Animate full path on complete |
| `instructions` | `string` | -- | |
| `submitMode` | `"immediate" \| "batch"` | -- | Validation timing |

**Max score:** `sum(all waypoints across all paths) * points_per_correct`

**Completion:** All paths have `isComplete === true`

---

### 5.4 `hierarchical`

**Blueprint config key:** none (uses `zoneGroups`)

**Required blueprint data:**
- `zoneGroups[]` with at least 1 group
- `labels[]` for dragging
- `diagram.zones[]` with `parentZoneId` and `hierarchyLevel` set
- `diagram.assetUrl`, `diagram.width`, `diagram.height`

**`ZoneGroup`:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **REQUIRED** | -- | Group identifier |
| `parentZoneId` | `string` | **REQUIRED** | -- | Parent zone that reveals children |
| `childZoneIds` | `string[]` | DEFAULT | `[]` | Child zones in this group |
| `revealTrigger` | `"complete_parent" \| "click_expand" \| "hover_reveal"` | DEFAULT | `"complete_parent"` | How children are revealed |
| `label` | `string` | OPTIONAL | -- | Group display label |

**Max score:** `(labels.length + sum(all childZoneIds)) * points_per_correct`

**Completion:** All labels at all hierarchy levels placed correctly.

---

### 5.5 `sequencing`

**Blueprint config key:** `sequenceConfig`

**Required blueprint data:**
- `sequenceConfig` with `items[]` and `correctOrder[]`

**Config (`SequenceConfig`):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `sequenceType` | `"linear" \| "cyclic" \| "branching"` | DEFAULT | `"linear"` | Sequence topology |
| `items` | `SequenceConfigItem[]` | DEFAULT | `[]` | Items to sequence |
| `correctOrder` | `string[]` | DEFAULT | `[]` | Correct item ID order |
| `allowPartialCredit` | `boolean` | OPTIONAL | -- | |
| `instructionText` | `string` | OPTIONAL | -- | Instruction text |
| `layout_mode` | `"horizontal_timeline" \| "vertical_list" \| "circular_cycle" \| "flowchart" \| "insert_between"` | OPTIONAL | -- | Visual layout |
| `interaction_pattern` | `"drag_reorder" \| "drag_to_slots" \| "click_to_swap" \| "number_typing"` | OPTIONAL | -- | Input method |
| `card_type` | `"text_only" \| "text_with_icon" \| "image_with_caption" \| "image_only"` | OPTIONAL | -- | Card visual style |
| `connector_style` | `"arrow" \| "line" \| "numbered" \| "none"` | OPTIONAL | -- | Connection visual |
| `show_position_numbers` | `boolean` | OPTIONAL | -- | Show slot numbers |

**`SequenceConfigItem`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Item identifier |
| `text` | `string` | **REQUIRED** | Display text |
| `description` | `string` | OPTIONAL | Longer description |
| `image` | `string` | OPTIONAL | Image URL |
| `icon` | `string` | OPTIONAL | Emoji/icon |
| `category` | `string` | OPTIONAL | Grouping category |
| `is_distractor` | `boolean` | OPTIONAL | Is this a distractor item? |
| `order_index` | `number` | OPTIONAL | Correct position (0-based) |

**Max score:** `items.length * points_per_correct`

**Completion:** Submitted AND all positions correct (`correctPositions === totalPositions`)

**Initialization:** Items are Fisher-Yates shuffled on load. `correctOrder` must contain the IDs in the expected sequence.

---

### 5.6 `sorting_categories`

**Blueprint config key:** `sortingConfig`

**Required blueprint data:**
- `sortingConfig` with `items[]` and `categories[]`

**Config (`SortingConfig`):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `items` | `SortingItem[]` | DEFAULT | `[]` | Items to sort |
| `categories` | `SortingCategory[]` | DEFAULT | `[]` | Categories to sort into |
| `allowPartialCredit` | `boolean` | OPTIONAL | -- | |
| `showCategoryHints` | `boolean` | OPTIONAL | -- | Show category descriptions |
| `instructions` | `string` | OPTIONAL | -- | |
| `sort_mode` | `"bucket" \| "venn_2" \| "venn_3" \| "matrix" \| "column"` | OPTIONAL | -- | Layout mode |
| `item_card_type` | `"text_only" \| "text_with_icon" \| "image_with_caption"` | OPTIONAL | -- | Card style |
| `container_style` | `"bucket" \| "labeled_bin" \| "circle" \| "cell" \| "column"` | OPTIONAL | -- | Container style |
| `submit_mode` | `"batch_submit" \| "immediate_feedback" \| "round_based"` | OPTIONAL | -- | When to evaluate |
| `allow_multi_category` | `boolean` | OPTIONAL | -- | Items can belong to multiple categories |

**`SortingItem`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Item identifier |
| `text` | `string` | **REQUIRED** | Display text |
| `correctCategoryId` | `string` | **REQUIRED** | Primary correct category ID |
| `correct_category_ids` | `string[]` | OPTIONAL | Multi-category: all valid category IDs |
| `description` | `string` | OPTIONAL | |
| `image` | `string` | OPTIONAL | Image URL |
| `difficulty` | `"easy" \| "medium" \| "hard"` | OPTIONAL | |

**`SortingCategory`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Category identifier |
| `label` | `string` | **REQUIRED** | Display name |
| `description` | `string` | OPTIONAL | |
| `color` | `string` | OPTIONAL | CSS color |

**Max score:** `items.length * points_per_correct`

**Completion:** Submitted AND all items sorted correctly (`correctCount === totalCount`)

---

### 5.7 `memory_match`

**Blueprint config key:** `memoryMatchConfig`

**Required blueprint data:**
- `memoryMatchConfig` with `pairs[]`

**Config (`MemoryMatchConfig`):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pairs` | `MemoryMatchPair[]` | DEFAULT | `[]` | Pairs to match |
| `gridSize` | `[number, number]` | OPTIONAL | -- | Grid dimensions [rows, cols] |
| `flipDurationMs` | `number` | OPTIONAL | -- | Card flip animation duration |
| `showAttemptsCounter` | `boolean` | OPTIONAL | -- | Show attempt counter |
| `instructions` | `string` | OPTIONAL | -- | |
| `game_variant` | `"classic" \| "column_match" \| "scatter" \| "progressive" \| "peek"` | OPTIONAL | -- | Game variant |
| `match_type` | `"term_to_definition" \| "image_to_label" \| "diagram_region_to_label" \| "concept_to_example"` | OPTIONAL | -- | Content pairing type |
| `card_back_style` | `"solid" \| "gradient" \| "pattern" \| "question_mark"` | OPTIONAL | -- | Card back visual |
| `matched_card_behavior` | `"fade" \| "shrink" \| "collect" \| "checkmark"` | OPTIONAL | -- | What happens to matched cards |
| `show_explanation_on_match` | `boolean` | OPTIONAL | -- | Show explanation popup |

**`MemoryMatchPair`:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **REQUIRED** | -- | Pair identifier |
| `front` | `string` | **REQUIRED** | -- | Front card content (text or image URL) |
| `back` | `string` | **REQUIRED** | -- | Back card content (text or image URL) |
| `frontType` | `"text" \| "image"` | DEFAULT | `"text"` | Front content type |
| `backType` | `"text" \| "image"` | DEFAULT | `"text"` | Back content type |
| `explanation` | `string` | OPTIONAL | -- | Pedagogical explanation on match |
| `category` | `string` | OPTIONAL | -- | For progressive reveal grouping |

**Max score:** `pairs.length * points_per_correct`

**Completion:** `matchedPairIds.length >= totalPairs`

---

### 5.8 `branching_scenario`

**Blueprint config key:** `branchingConfig`

**Required blueprint data:**
- `branchingConfig` with `nodes[]` and `startNodeId`

**Config (`BranchingConfig`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nodes` | `DecisionNode[]` | DEFAULT (`[]`) | Decision tree nodes |
| `startNodeId` | `string` | **REQUIRED** | ID of the first node |
| `showPathTaken` | `boolean` | OPTIONAL | Show breadcrumb of past choices |
| `allowBacktrack` | `boolean` | OPTIONAL | Allow undoing choices |
| `showConsequences` | `boolean` | OPTIONAL | Show consequence text |
| `multipleValidEndings` | `boolean` | OPTIONAL | Multiple good endings? |
| `instructions` | `string` | OPTIONAL | |
| `narrative_structure` | `"linear" \| "branching" \| "foldback"` | OPTIONAL | Story structure type |

**`DecisionNode`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Node identifier |
| `question` | `string` | **REQUIRED** | Question/prompt text |
| `description` | `string` | OPTIONAL | Context text |
| `imageUrl` | `string` | OPTIONAL | Node illustration |
| `options` | `DecisionOption[]` | DEFAULT (`[]`) | Available choices |
| `isEndNode` | `boolean` | OPTIONAL | Is this a terminal node? |
| `endMessage` | `string` | OPTIONAL | Message shown at end |
| `node_type` | `"decision" \| "info" \| "ending" \| "checkpoint"` | OPTIONAL | UI treatment |
| `narrative_text` | `string` | OPTIONAL | Narrative before prompt |
| `ending_type` | `"good" \| "neutral" \| "bad"` | OPTIONAL | Quality of ending |

**`DecisionOption`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Option identifier |
| `text` | `string` | **REQUIRED** | Option display text |
| `nextNodeId` | `string \| null` | **REQUIRED** | Next node ID (null = end) |
| `isCorrect` | `boolean` | OPTIONAL | Is this the right choice? |
| `consequence` | `string` | OPTIONAL | Consequence text |
| `points` | `number` | OPTIONAL | Points for this choice |
| `quality` | `"optimal" \| "acceptable" \| "suboptimal" \| "harmful"` | OPTIONAL | Quality level |
| `consequence_text` | `string` | OPTIONAL | Detailed consequence |

**Max score:** `(non-end nodes count) * points_per_correct`

**Completion:** Current node has `isEndNode === true`

---

### 5.9 `compare_contrast`

**Blueprint config key:** `compareConfig`

**Required blueprint data:**
- `compareConfig` with `diagramA`, `diagramB`, `expectedCategories`

**Config (`CompareConfig`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `diagramA` | `CompareDiagram` | **REQUIRED** | First diagram |
| `diagramB` | `CompareDiagram` | **REQUIRED** | Second diagram |
| `expectedCategories` | `Record<string, "similar" \| "different" \| "unique_a" \| "unique_b">` | **REQUIRED** | Expected categorization per zone |
| `highlightMatching` | `boolean` | OPTIONAL | Highlight matching zones |
| `instructions` | `string` | OPTIONAL | |
| `comparison_mode` | `"side_by_side" \| "slider" \| "overlay_toggle" \| "venn" \| "spot_difference"` | OPTIONAL | Visual comparison mode |
| `category_types` | `string[]` | OPTIONAL | Custom category type list |
| `category_labels` | `Record<string, string>` | OPTIONAL | Custom labels for categories |
| `category_colors` | `Record<string, string>` | OPTIONAL | Custom colors for categories |
| `exploration_enabled` | `boolean` | OPTIONAL | Free exploration before quiz |
| `zoom_enabled` | `boolean` | OPTIONAL | |

**`CompareDiagram`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Diagram identifier |
| `name` | `string` | **REQUIRED** | Display name |
| `imageUrl` | `string` | **REQUIRED** | Image URL |
| `zones` | `CompareZone[]` | DEFAULT (`[]`) | Zone definitions |

**`CompareZone` (within CompareDiagram):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **REQUIRED** | Zone identifier |
| `label` | `string` | **REQUIRED** | Zone label |
| `x` | `number` | **REQUIRED** | X position |
| `y` | `number` | **REQUIRED** | Y position |
| `width` | `number` | **REQUIRED** | Zone width |
| `height` | `number` | **REQUIRED** | Zone height |

**Max score:** `Object.keys(expectedCategories).length * points_per_correct`

**Completion:** Submitted AND all categorizations correct

---

### 5.10 `description_matching`

**Blueprint config key:** `descriptionMatchingConfig`

**Required blueprint data:**
- `diagram.zones[]` where zones have `description` field set
- `labels[]` (for display)
- The mechanic counts zones with descriptions to determine total items

**Config (`DescriptionMatchingConfig`):**

| Field | Type | Description |
|-------|------|-------------|
| `descriptions` | `Record<string, string>` | Map of zone/label IDs to description text. If absent, uses `zone.description`. |
| `mode` | `"click_zone" \| "drag_description" \| "multiple_choice"` | Interaction variant |
| `show_connecting_lines` | `boolean` | Draw lines between matches |
| `defer_evaluation` | `boolean` | Defer correctness check |
| `distractor_count` | `number` | Number of distractor descriptions |
| `description_panel_position` | `"left" \| "right" \| "bottom"` | Panel position |

**Max score:** `zones_with_description.length * points_per_correct`

**Completion:** `currentIndex >= total_descriptions`

---

### 5.11 `timed_challenge`

**No dedicated config key.** Uses the wrapped mechanic's config.

**Required blueprint data:**
- `timedChallengeWrappedMode`: which mechanic to wrap (defaults to `drag_drop`)
- `timeLimitSeconds`: time limit in seconds
- All data required by the wrapped mechanic

---

## 6. Scoring Contract

The scoring engine reads configuration in this priority order:

1. **Mechanic-level scoring** (`mechanics[].scoring.points_per_correct`) -- highest priority
2. **Blueprint-level scoring strategy** (`scoringStrategy.base_points_per_zone`)
3. **Default** (`10` points per correct action)

### How max score is computed per mechanic:

| Mechanic | Max Score Formula |
|----------|------------------|
| `drag_drop` | `labels.length * pts` |
| `click_to_identify` | `identificationPrompts.length * pts` |
| `trace_path` | `sum(all waypoints) * pts` |
| `hierarchical` | `(labels.length + sum(childZoneIds)) * pts` |
| `sequencing` | `sequenceConfig.items.length * pts` |
| `sorting_categories` | `sortingConfig.items.length * pts` |
| `memory_match` | `memoryMatchConfig.pairs.length * pts` |
| `branching_scenario` | `non-end-nodes.length * pts` |
| `compare_contrast` | `Object.keys(expectedCategories).length * pts` |
| `description_matching` | `zones_with_description.length * pts` |

Where `pts` = `mechanic.scoring.points_per_correct` or `scoringStrategy.base_points_per_zone` or `10`.

For **multi-mode games**, the cumulative max score is the sum across all active mechanics.

---

## 7. Feedback Contract

The feedback engine resolves messages in this order:

1. **Misconception match** -- if event is `incorrect` and `mechanic.feedback.misconceptions` has a matching `trigger_label`, return that misconception message with type `"misconception"` and severity `"warning"`
2. **Mechanic-level feedback** -- `mechanic.feedback.on_correct`, `on_incorrect`, `on_completion`
3. **AnimationCues fallback** -- `animationCues.correctPlacement`, `incorrectPlacement`, `allLabeled`
4. **Hardcoded defaults** -- `"Correct!"`, `"Try again!"`, `"Well done!"`

Score-based end-of-game feedback uses `feedbackMessages`:
- 100% score: `feedbackMessages.perfect`
- Passing: `feedbackMessages.good`
- Failing: `feedbackMessages.retry`

---

## 8. Mode Transitions Contract

For multi-mode games (games with `mechanics.length > 1` and `modeTransitions[]`):

1. `mechanics[0].type` is the starting mode
2. When a trigger condition is satisfied, the engine checks `modeTransitions[]` for applicable transitions from the current mode
3. The first matching transition fires
4. Each mechanic's progress is initialized fresh on transition

The transition evaluator checks:
- Registry's `checkTrigger()` for the current mode first (mechanic-specific logic)
- Then generic triggers (`percentage_complete`, `specific_zones`, `time_elapsed`, `user_choice`)

---

## 9. Temporal Intelligence Contract

### `TemporalConstraint`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `zone_a` | `string` | **REQUIRED** | -- | First zone |
| `zone_b` | `string` | **REQUIRED** | -- | Second zone |
| `constraint_type` | `"before" \| "after" \| "mutex" \| "concurrent" \| "sequence"` | **REQUIRED** | -- | Constraint type |
| `reason` | `string` | DEFAULT | `""` | Why this constraint exists |
| `priority` | `number` | DEFAULT | `50` | 1-100, higher = more important |

### `MotionPath`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `asset_id` | `string` | **REQUIRED** | -- | Asset to animate |
| `keyframes` | `MotionKeyframe[]` | DEFAULT | `[]` | Animation keyframes |
| `easing` | `string` | DEFAULT | `"linear"` | Easing function |
| `trigger` | `"on_reveal" \| "on_complete" \| "on_hover" \| "on_scene_enter" \| "on_incorrect"` | **REQUIRED** | -- | When to trigger |
| `stagger_delay_ms` | `number` | OPTIONAL | -- | Stagger delay |
| `loop` | `boolean` | OPTIONAL | -- | Loop animation |

### `MotionKeyframe`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `time_ms` | `number` | **REQUIRED** | Time in milliseconds |
| `x` | `number` | OPTIONAL | X position |
| `y` | `number` | OPTIONAL | Y position |
| `scale` | `number` | OPTIONAL | Scale factor |
| `rotation` | `number` | OPTIONAL | Rotation degrees |
| `opacity` | `number` | OPTIONAL | 0-1 opacity |
| `backgroundColor` | `string` | OPTIONAL | CSS color |
| `transform` | `string` | OPTIONAL | CSS transform |

---

## 10. Case Normalization Rules

The frontend automatically normalizes snake_case to camelCase for these fields. The backend may send either form:

| snake_case (accepted) | camelCase (canonical) |
|------------------------|----------------------|
| `sequence_config` | `sequenceConfig` |
| `sorting_config` | `sortingConfig` |
| `memory_match_config` | `memoryMatchConfig` |
| `branching_config` | `branchingConfig` |
| `compare_config` | `compareConfig` |
| `click_to_identify_config` | `clickToIdentifyConfig` |
| `trace_path_config` | `tracePathConfig` |
| `drag_drop_config` | `dragDropConfig` |
| `description_matching_config` | `descriptionMatchingConfig` |
| `temporal_constraints` | `temporalConstraints` |
| `motion_paths` | `motionPaths` |
| `scoring_strategy` | `scoringStrategy` |
| `identification_prompts` | `identificationPrompts` |
| `distractor_labels` | `distractorLabels` |
| `interaction_mode` | `interactionMode` |
| `mode_transitions` | `modeTransitions` |
| `narrative_intro` | `narrativeIntro` |

The normalizer only copies the snake_case value if the camelCase key is not already present. **CamelCase takes precedence.**

Misconceptions are also normalized from dict format `{ "label": "message" }` to array format `[{ trigger_label, message }]`.

---

## 11. Zod Validation Defaults

When the backend omits fields, these defaults are applied by the Zod schema:

| Field | Default |
|-------|---------|
| `templateType` | `"INTERACTIVE_DIAGRAM"` |
| `title` | `"Untitled Game"` |
| `narrativeIntro` | `""` |
| `diagram.assetPrompt` | `""` |
| `diagram.zones` | `[]` |
| `labels` | `[]` |
| `tasks` | `[]` |
| `animationCues.correctPlacement` | `"Correct!"` |
| `animationCues.incorrectPlacement` | `"Try again!"` |
| `feedbackMessages.perfect` | `"Perfect score!"` |
| `feedbackMessages.good` | `"Good job!"` |
| `feedbackMessages.retry` | `"Try again!"` |
| `scoringStrategy.base_points_per_zone` | `10` |
| `sequenceConfig.sequenceType` | `"linear"` |
| `clickToIdentifyConfig.promptStyle` | `"naming"` |
| `clickToIdentifyConfig.selectionMode` | `"sequential"` |
| `clickToIdentifyConfig.highlightStyle` | `"subtle"` |
| `tracePathConfig.pathType` | `"linear"` |
| `tracePathConfig.drawingMode` | `"click_waypoints"` |
| `tracePathConfig.particleTheme` | `"dots"` |
| `tracePathConfig.particleSpeed` | `"medium"` |
| `memoryMatchPair.frontType` | `"text"` |
| `memoryMatchPair.backType` | `"text"` |
| `tracePath.requiresOrder` | `true` |
| `zoneGroup.revealTrigger` | `"complete_parent"` |
| `temporalConstraint.reason` | `""` |
| `temporalConstraint.priority` | `50` |
| `task.questionText` | `""` |
| `task.requiredToProceed` | `true` |

---

## 12. Common Failure Modes

These are the blueprint problems that cause the frontend to break or degrade:

| Problem | Effect | Backend Fix |
|---------|--------|-------------|
| Missing `diagram.assetUrl` | No background image, game is blank | Always provide a valid image URL |
| `label.correctZoneId` references non-existent zone | Frontend tries text-matching fallback, may fail | Ensure every label's `correctZoneId` matches a `zone.id` |
| `mechanics` array is empty or missing | Falls back to `interactionMode` or `drag_drop` | Always set `mechanics[0].type` |
| Mechanic active but config missing (e.g. `sequencing` without `sequenceConfig`) | Validation warning, mechanic renders empty | Populate the config key for every active mechanic |
| `sequenceConfig.items` empty | No items to sequence | Ensure at least 2 items |
| `branchingConfig.startNodeId` missing | No starting node found | Always set `startNodeId` to match a node `id` |
| `compareConfig.diagramA/B` missing | Falls back to using main diagram for both | Provide both diagrams with zones |
| `identificationPrompts` empty for `click_to_identify` | No prompts to show | Provide at least 1 prompt |
| `paths` empty for `trace_path` | No paths to trace | Provide at least 1 path with waypoints |
| Zone `x`/`y` missing for circle/rect shape | Zone won't render at correct position | Always set position for non-polygon zones |
| Polygon zone missing `points` | Cannot render polygon overlay | Provide `points` array for polygon shapes |
| Duplicate zone/label IDs | Frontend auto-deduplicates but may mismap | Use unique IDs |
| `diagram.width`/`height` missing | Defaults to 800x600, may misalign zones | Always provide actual image dimensions |
| Misconceptions as dict instead of array | Auto-normalized but fragile | Prefer array format |
| Multi-scene with `is_multi_scene` missing | Treated as single-scene, game_sequence ignored | Always set `is_multi_scene: true` |
| Scene without `diagram.assetUrl` | Merged as task into previous scene via migration | Each scene should have its own image URL |

---

## Appendix: Complete `InteractionMode` Values

```
"drag_drop"
"click_to_identify"
"trace_path"
"hierarchical"
"description_matching"
"compare_contrast"
"sequencing"
"timed_challenge"
"sorting_categories"
"memory_match"
"branching_scenario"
```

---

## Appendix: Minimal Valid Blueprint (drag_drop)

```json
{
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Label the Heart",
  "narrativeIntro": "Drag each label to the correct part of the heart.",
  "diagram": {
    "assetPrompt": "anatomical diagram of a human heart",
    "assetUrl": "https://example.com/heart.png",
    "width": 800,
    "height": 600,
    "zones": [
      { "id": "zone_1", "label": "Left Ventricle", "x": 60, "y": 55, "radius": 8, "shape": "circle" },
      { "id": "zone_2", "label": "Right Atrium", "x": 35, "y": 30, "radius": 8, "shape": "circle" }
    ]
  },
  "labels": [
    { "id": "label_1", "text": "Left Ventricle", "correctZoneId": "zone_1" },
    { "id": "label_2", "text": "Right Atrium", "correctZoneId": "zone_2" }
  ],
  "animationCues": {
    "correctPlacement": "Correct!",
    "incorrectPlacement": "Try again!"
  },
  "mechanics": [
    {
      "type": "drag_drop",
      "scoring": {
        "points_per_correct": 10,
        "max_score": 20
      },
      "feedback": {
        "on_correct": "Well done!",
        "on_incorrect": "That's not quite right.",
        "on_completion": "You labeled all parts correctly!"
      }
    }
  ]
}
```

## Appendix: Minimal Valid Multi-Scene Blueprint

```json
{
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Heart Anatomy Explorer",
  "narrativeIntro": "Explore the heart in multiple stages.",
  "is_multi_scene": true,
  "animationCues": {
    "correctPlacement": "Correct!",
    "incorrectPlacement": "Try again!"
  },
  "game_sequence": {
    "sequence_id": "seq_heart",
    "sequence_title": "Heart Anatomy",
    "total_scenes": 2,
    "progression_type": "linear",
    "total_max_score": 40,
    "scenes": [
      {
        "scene_id": "scene_1",
        "scene_number": 1,
        "title": "Label the Chambers",
        "narrative_intro": "Identify the four chambers of the heart.",
        "diagram": {
          "assetUrl": "https://example.com/heart.png",
          "assetPrompt": "heart chambers"
        },
        "zones": [
          { "id": "z1", "label": "Left Ventricle", "x": 60, "y": 55, "radius": 8, "shape": "circle" }
        ],
        "labels": [
          { "id": "l1", "text": "Left Ventricle", "correctZoneId": "z1" }
        ],
        "max_score": 10,
        "tasks": [
          {
            "task_id": "task_1",
            "title": "Label Chambers",
            "mechanic_type": "drag_drop",
            "zone_ids": ["z1"],
            "label_ids": ["l1"],
            "scoring_weight": 1
          }
        ],
        "mechanics": [{ "type": "drag_drop" }]
      },
      {
        "scene_id": "scene_2",
        "scene_number": 2,
        "title": "Trace Blood Flow",
        "narrative_intro": "Trace the path of blood through the heart.",
        "diagram": {
          "assetUrl": "https://example.com/heart_flow.png",
          "assetPrompt": "heart blood flow"
        },
        "zones": [
          { "id": "z2", "label": "Right Atrium", "x": 35, "y": 30, "radius": 8, "shape": "circle" },
          { "id": "z3", "label": "Right Ventricle", "x": 35, "y": 55, "radius": 8, "shape": "circle" }
        ],
        "labels": [],
        "max_score": 20,
        "tasks": [
          {
            "task_id": "task_2",
            "title": "Trace Blood Flow",
            "mechanic_type": "trace_path",
            "zone_ids": ["z2", "z3"],
            "label_ids": [],
            "scoring_weight": 1
          }
        ],
        "mechanics": [{ "type": "trace_path" }],
        "paths": [
          {
            "id": "path_1",
            "description": "Blood flow through right side",
            "requiresOrder": true,
            "waypoints": [
              { "zoneId": "z2", "order": 0 },
              { "zoneId": "z3", "order": 1 }
            ]
          }
        ],
        "tracePathConfig": {
          "pathType": "linear",
          "drawingMode": "click_waypoints",
          "particleTheme": "droplets",
          "particleSpeed": "medium"
        }
      }
    ]
  }
}
```
