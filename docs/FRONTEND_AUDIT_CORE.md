# Frontend Audit: LabelDiagramGame Core Components

Hardcoded values that limit game creativity and configurability.

**Format:** `- **[SEVERITY]** file:line -- What is hardcoded -> What it should be`

---

## index.tsx

- **[MED]** `index.tsx:121-122` -- Fallback diagram dimensions `800x600` baked into `normalizeBlueprint()` -> Should come from a blueprint-level `defaults` config or theme
- **[LOW]** `index.tsx:190` -- Fallback zone position `{ x: 50, y: 50 }` when `fallbackPositions` exhausted -> Should spread evenly or use a configurable default
- **[LOW]** `index.tsx:196` -- Auto-generated zones use hardcoded `radius: 10` -> Should derive from diagram size or be a configurable default
- **[MED]** `index.tsx:313` -- Auto-save interval hardcoded to `30000` ms (30s) -> Should be configurable via blueprint or app settings
- **[MED]** `index.tsx:468` -- Incorrect feedback auto-clear timeout hardcoded to `2000` ms -> Should be configurable per blueprint (fast vs. slow learners)
- **[LOW]** `index.tsx:475-476` -- Mouse drag activation distance hardcoded to `5` px -> Should be configurable for accessibility (motor impairment needs larger threshold)
- **[LOW]** `index.tsx:480-481` -- Touch sensor delay `100` ms, tolerance `5` px hardcoded -> Should be configurable for different devices/accessibility needs
- **[MED]** `index.tsx:832-834` -- Timed challenge defaults: `wrappedMode` fallback to `'drag_drop'`, `timeLimit` fallback to `60` seconds -> Should not assume default time limit; force blueprint to specify
- **[LOW]** `index.tsx:1056-1057` -- Scene animation cue strings `'Great!'` / `'Try again!'` hardcoded in `renderScene` -> Should come from scene data or i18n
- **[HIGH]** `index.tsx:1206` -- Task instruction box uses hardcoded `bg-blue-50` / `text-blue-800` colors -> Should be themeable or use CSS custom properties

## types.ts

- **[LOW]** `types.ts:167` -- `hierarchyLevel` comment implies 1-indexed convention (1=root) -> Should be documented/enforced, not just a comment
- **[LOW]** `types.ts:173` -- `difficulty` range 1-5 described only in comment -> Should be enforced with validation or an enum
- **[LOW]** `types.ts:103` -- `TemporalConstraint.priority` range 1-100 described only in comment -> Should be enforced or documented as a configurable scale

## DiagramCanvas.tsx

- **[MED]** `DiagramCanvas.tsx:170` -- Default canvas width `800` px -> Should be responsive or blueprint-configured
- **[MED]** `DiagramCanvas.tsx:171` -- Default canvas height `600` px -> Should be responsive or blueprint-configured
- **[LOW]** `DiagramCanvas.tsx:174` -- Default title `'Interactive Diagram'` -> Should require blueprint to provide title; generic fallback hurts accessibility
- **[LOW]** `DiagramCanvas.tsx:53` -- Zone-attached media `maxWidth`/`maxHeight` uses `(zone.radius || 10) * 4` percent -> Magic multiplier `4` limits media sizing flexibility
- **[LOW]** `DiagramCanvas.tsx:33` -- Media asset base zIndex `10 + layer` -> Magic base zIndex could conflict with other overlays
- **[LOW]** `DiagramCanvas.tsx:228-247` -- Placeholder SVG icon dimensions `w-24 h-24` and gradient `from-gray-100 to-gray-200` hardcoded -> Should be themeable

## DropZone.tsx

- **[HIGH]** `DropZone.tsx:85` -- Collision gap between zones hardcoded to `2`% -> Should be configurable per diagram density (tight diagrams need less gap)
- **[MED]** `DropZone.tsx:101-102` -- Zone offset clamped to `[-10, 10]`% range -> Limit should be configurable; dense diagrams may need larger offsets
- **[MED]** `DropZone.tsx:174` -- Default zone size `(zone.radius ?? 5) * 2` with fallback radius `5` -> Hardcoded fallback radius limits small/large zone flexibility
- **[HIGH]** `DropZone.tsx:190` -- Point zone threshold: `(zone.radius ?? 5) > 6` determines area vs point -> Magic number `6` is not configurable and misclassifies zones
- **[LOW]** `DropZone.tsx:336` -- Point zone dot size clamped `Math.max(3, Math.min(radius, 5)) * 2` -> Hardcoded min/max dot size limits visual variety
- **[MED]** `DropZone.tsx:351` -- Point zone `minWidth: '24px'`, `minHeight: '24px'` hardcoded -> Should scale with diagram or be configurable
- **[MED]** `DropZone.tsx:433` -- Rect zone `minWidth: '40px'`, `minHeight: '30px'` hardcoded -> Should scale with diagram or be configurable
- **[MED]** `DropZone.tsx:510` -- Circle zone `minWidth: '60px'`, `minHeight: '36px'` hardcoded -> Should scale with diagram or be configurable
- **[HIGH]** `DropZone.tsx:204-213` -- Hierarchy level colors hardcoded (blue-400, purple-400, teal-400, gray-400) with only 3 levels + default -> Should support unlimited levels via configurable color palette
- **[HIGH]** `DropZone.tsx:218-226` -- Stroke colors hardcoded per hierarchy level (green-500, primary, blue-400, etc.) -> Should come from theme or blueprint color config
- **[LOW]** `DropZone.tsx:310` -- Hint tooltip `max-w-[200px]` hardcoded -> Should be responsive or configurable for long hint text
- **[LOW]** `DropZone.tsx:278` -- Polygon stroke dash array `'4 2'` hardcoded -> Should be configurable for visual distinction between zone types
- **[LOW]** `DropZone.tsx:544` -- Empty zone placeholder text hardcoded to `'?'` -> Should be configurable (could be a number, icon, or hidden)

## DraggableLabel.tsx

- **[LOW]** `DraggableLabel.tsx:25` -- Drag opacity hardcoded to `0.5` -> Should be configurable for visual accessibility
- **[MED]** `DraggableLabel.tsx:34-43` -- Label styling (colors, border, shadow, padding) entirely hardcoded in className -> Should support blueprint-level label styling or theming

## GameControls.tsx

- **[MED]** `GameControls.tsx:32` -- Progress bar width hardcoded to `w-32` (128px) -> Should be responsive or configurable
- **[LOW]** `GameControls.tsx:69` -- Hint button text hardcoded `'Hide Hints'` / `'Show Hints'` -> Should support i18n / custom text from blueprint
- **[LOW]** `GameControls.tsx:91` -- Reset button text hardcoded `'Reset'` -> Should support i18n / custom text from blueprint
- **[LOW]** `GameControls.tsx:25` -- Score label `'Score:'` hardcoded -> Should support i18n / custom text

## ResultsPanel.tsx

- **[HIGH]** `ResultsPanel.tsx:29` -- Confetti threshold hardcoded to `>= 70`% -> Should be configurable per blueprint (some games may want confetti at 50%)
- **[HIGH]** `ResultsPanel.tsx:35-41` -- Feedback tier thresholds hardcoded: `100` = perfect, `>= 70` = good, else retry -> Should be configurable per blueprint's `feedbackMessages` with custom thresholds
- **[MED]** `ResultsPanel.tsx:55-56` -- Confetti duration hardcoded: `4000` ms (perfect) / `2500` ms (good) -> Should be configurable or use animation spec from blueprint
- **[MED]** `ResultsPanel.tsx:56` -- Confetti particle count hardcoded: `80` (perfect) / `40` (good) -> Should be configurable or use animation spec
- **[LOW]** `ResultsPanel.tsx:44-48` -- Result emojis hardcoded (party, clap, muscle) -> Should be configurable per blueprint theme
- **[LOW]** `ResultsPanel.tsx:102` -- Completion title `'Congratulations!'` / `'Game Complete!'` hardcoded -> Should support i18n / custom text from blueprint
- **[MED]** `ResultsPanel.tsx:36-40` -- Default feedback messages hardcoded (`'Perfect! You labeled...'`, `'Great job!...'`, `'Keep practicing!...'`) -> These are fallbacks but prevent per-game tone customization
- **[LOW]** `ResultsPanel.tsx:61` -- Score circle dimensions `w-32 h-32` (128x128px) hardcoded -> Should be responsive
- **[LOW]** `ResultsPanel.tsx:83` -- Score ring circumference `351.86` hardcoded -> Derived from `r=56`, but ties to fixed SVG size; should compute dynamically

## SceneTransition.tsx

- **[MED]** `SceneTransition.tsx:77` -- Default transition duration hardcoded to `500` ms -> Should come from blueprint `animations` config
- **[LOW]** `SceneTransition.tsx:78` -- Default transition delay hardcoded to `0` ms -> Should be configurable per scene
- **[LOW]** `SceneTransition.tsx:236` -- Zoom focus indicator size `w-24 h-24` hardcoded -> Should scale with diagram or be configurable
- **[LOW]** `SceneTransition.tsx:319` -- Scene indicator dot size `w-3 h-3` hardcoded -> Should be configurable for accessibility (larger dots for visibility)
- **[LOW]** `SceneTransition.tsx:248-259` -- Default animation mapping (linear->slide_left, zoom_in->zoom_in, etc.) hardcoded -> Should be overridable from blueprint

## hooks/useLabelDiagramState.ts

- **[HIGH]** `useLabelDiagramState.ts:279-280` -- Default scoring: `base_points_per_zone` fallback `10`, `maxScore` fallback `labels.length * 10` -> Hardcoded `10` points per zone prevents custom scoring
- **[HIGH]** `useLabelDiagramState.ts:334` -- Correct placement always awards `+10` points (line 334: `state.score + 10`) -> Ignores `scoringStrategy.base_points_per_zone` calculated on line 350; double scoring logic
- **[HIGH]** `useLabelDiagramState.ts:408` -- `removeLabel` decrements score by hardcoded `10` -> Should use `base_points_per_zone` from scoring strategy to match award amount
- **[HIGH]** `useLabelDiagramState.ts:434` -- Path waypoint scoring: `visitedWaypoints.length * 10` hardcoded -> Should use `scoringStrategy.base_points_per_zone`
- **[HIGH]** `useLabelDiagramState.ts:451` -- Identification scoring: `completedZoneIds.length * 10` hardcoded -> Should use `scoringStrategy.base_points_per_zone`
- **[HIGH]** `useLabelDiagramState.ts:482-500` -- `completeInteraction` recalculates maxScore with hardcoded `* 10` for every mode -> Should use blueprint's `scoringStrategy` consistently
- **[HIGH]** `useLabelDiagramState.ts:617` -- Description match scoring: `correct.length * 10` hardcoded -> Should use `scoringStrategy.base_points_per_zone`
- **[MED]** `useLabelDiagramState.ts:49-51` -- Scene animation cues `'Great!'` / `'Try again!'` hardcoded in `_sceneToBlueprint` -> Should come from scene data or blueprint defaults
- **[MED]** `useLabelDiagramState.ts:832` -- Mode transition auto-delay hardcoded to `500` ms (or `0` for `'none'`) -> Should be configurable per transition
- **[LOW]** `useLabelDiagramState.ts:783` -- `percentage_complete` default threshold fallback `50`% -> Should not assume 50%; require explicit value or use from triggerValue

## hooks/useZoneCollision.ts

- **[MED]** `useZoneCollision.ts:200-201` -- `findClosestZone` default max distance hardcoded to `20`% -> Should be configurable for near-miss sensitivity per game
- **[LOW]** `useZoneCollision.ts:87` -- Rect zone collision uses `radius` as half-size for both width and height -> Ignores `zone.width`/`zone.height` if present; should use them for accuracy

---

## Summary

| Severity | Count |
|----------|-------|
| HIGH     | 12    |
| MED      | 18    |
| LOW      | 27    |
| **Total**| **57** |

### Top Priority Fixes

1. **Scoring system** (7 HIGH findings): Points-per-zone hardcoded to `10` in 7 places across `useLabelDiagramState.ts`. The `scoringStrategy.base_points_per_zone` field exists on the blueprint but is ignored in most score calculations. This is the single biggest creativity blocker.

2. **Feedback thresholds** (2 HIGH): The 70%/100% tier boundaries in `ResultsPanel.tsx` are hardcoded and cannot be customized per game. A quiz game may want stricter thresholds; a kindergarten game may want celebration at 50%.

3. **Zone rendering defaults** (3 HIGH): The point-vs-area threshold (`radius > 6`), hierarchy color palette (3 levels), and collision gap (`2%`) are all hardcoded in `DropZone.tsx`, limiting diagram variety.
