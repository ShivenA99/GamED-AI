# Frontend Audit: LabelDiagramGame Interaction Components

**Date:** 2026-02-07
**Scope:** 15 files in `frontend/src/components/templates/LabelDiagramGame/interactions/` and `hooks/`
**Focus:** Hardcoded values limiting game creativity, capability gaps

---

## Hardcoded Values by File

### 1. ModeIndicator.tsx

- **MED** `ModeIndicator.tsx:7-63` — All 11 mode names, icons, and descriptions are hardcoded in `MODE_INFO` constant -> should be data-driven from blueprint or theme config
- **LOW** `ModeIndicator.tsx:114` — Transition notification uses hardcoded `animate-pulse` animation -> should respect animation config / reduced motion
- **LOW** `ModeIndicator.tsx:116` — Fallback transition message `"Transitioning to ..."` is hardcoded English -> should be i18n-aware or blueprint-configurable
- **LOW** `ModeIndicator.tsx:185` — Active mode text `"Active"` is hardcoded English -> should be configurable
- **LOW** `ModeIndicator.tsx:182` — Completed checkmark `"✓"` hardcoded -> should support custom completion indicators

### 2. GameSequenceRenderer.tsx

- **HIGH** `GameSequenceRenderer.tsx:217` — Scene transition delay hardcoded to `1000ms` -> should be configurable per sequence or theme
- **MED** `GameSequenceRenderer.tsx:359-360` — Transition overlay message `"Great job!"` is hardcoded English -> should come from blueprint `narrative_intro` or be configurable
- **MED** `GameSequenceRenderer.tsx:363` — Transition text `"Moving to closer view"` / `"next scene"` hardcoded -> should be data-driven from progression type config
- **MED** `GameSequenceRenderer.tsx:252-254` — Progression type labels `"Zoom Level:"`, `"Exploration Path:"`, `"Available Paths:"` hardcoded -> should be configurable
- **MED** `GameSequenceRenderer.tsx:399` — Completion title `"Sequence Complete!"` hardcoded -> should be blueprint-configurable
- **LOW** `GameSequenceRenderer.tsx:331` — Branch selector title `"Choose Your Path"` and subtitle hardcoded English -> should be configurable
- **LOW** `GameSequenceRenderer.tsx:257` — Navigation hint `"Click to navigate"` hardcoded -> should be configurable

### 3. HotspotManager.tsx

- **HIGH** `HotspotManager.tsx:165` — Correct feedback message hardcoded to `"Correct!"` -> should come from blueprint feedback config
- **HIGH** `HotspotManager.tsx:184` — Incorrect feedback message hardcoded to `"Try again!"` -> should come from blueprint feedback config
- **HIGH** `HotspotManager.tsx:189` — Feedback display duration hardcoded to `1500ms` -> should be configurable
- **MED** `HotspotManager.tsx:55-56` — Hotspot minimum size hardcoded to `50px` -> should be configurable per diagram scale
- **MED** `HotspotManager.tsx:240` — All-complete text hardcoded to `"All identified!"` -> should come from blueprint
- **MED** `HotspotManager.tsx:236` — Any-order prompt template `"Click on any of: ..."` hardcoded -> should be configurable
- **LOW** `HotspotManager.tsx:104-105` — Default dimensions `width=800, height=600` hardcoded -> should be derived from image or blueprint

### 4. PathDrawer.tsx

- **HIGH** `PathDrawer.tsx:240` — Correct path feedback `"Path complete!"` hardcoded -> should come from blueprint
- **HIGH** `PathDrawer.tsx:248,253` — Path transition and completion delays both hardcoded to `1500ms` -> should be configurable
- **HIGH** `PathDrawer.tsx:255` — Mid-path feedback `"Good! Continue tracing..."` hardcoded -> should be configurable
- **HIGH** `PathDrawer.tsx:256` — Mid-path feedback timeout hardcoded to `1000ms` -> should be configurable
- **HIGH** `PathDrawer.tsx:267-269` — Wrong-order feedback messages hardcoded (`"Wrong order! Follow the path sequence."` / `"This point is already visited..."`) -> should come from blueprint
- **HIGH** `PathDrawer.tsx:271` — Wrong-answer feedback timeout hardcoded to `2000ms` -> should be configurable
- **MED** `PathDrawer.tsx:70` — Arrow polygon color hardcoded to `#22c55e` (green-500) -> should be theme-configurable
- **MED** `PathDrawer.tsx:80` — Path line color hardcoded to `#22c55e`, strokeWidth `3`, strokeDasharray `"8,4"` -> should be configurable
- **MED** `PathDrawer.tsx:86` — Path draw animation duration hardcoded to `0.5s` -> should be configurable
- **MED** `PathDrawer.tsx:127-128` — PathZone minimum size hardcoded to `50px` -> should be configurable
- **LOW** `PathDrawer.tsx:151` — Unvisited waypoint indicator `"?"` hardcoded -> should be configurable

### 5. HierarchyController.tsx

- **HIGH** `HierarchyController.tsx:469-470` — Incorrect placement feedback `"Try again!"` with `1500ms` timeout hardcoded -> should be blueprint-configurable
- **HIGH** `HierarchyController.tsx:396-397` — Expand-blocked feedback `"Complete this label first to reveal sub-parts!"` with `2000ms` timeout hardcoded -> should be configurable
- **MED** `HierarchyController.tsx:72-83` — Hierarchy stroke colors hardcoded per level (blue-400, purple-400, teal-400, gray-400) -> should be theme-driven
- **MED** `HierarchyController.tsx:122-129` — Fill colors for placed/hover/parent states hardcoded as RGBA values -> should be theme-configurable
- **MED** `HierarchyController.tsx:157` — SVG strokeWidth hardcoded to `1.5` -> should be configurable
- **MED** `HierarchyController.tsx:233` — Circle/rect zone `minWidth: 40px, minHeight: 24px` hardcoded -> should be configurable
- **MED** `HierarchyController.tsx:178` — Sub-parts indicator text `"Has sub-parts"` hardcoded English -> should be configurable
- **LOW** `HierarchyController.tsx:305` — Default `assetPrompt = 'Diagram'` hardcoded -> minor, but should fall through from blueprint
- **LOW** `HierarchyController.tsx:306-307` — Default `width=800, height=600` hardcoded -> should be derived from image

### 6. SequenceBuilder.tsx

- **HIGH** `SequenceBuilder.tsx:181-185` — Scoring formula: partial credit = `Math.round((correctPositions / total) * 100)`, all-or-nothing = `100` or `0`, maxScore always `100` -> scoring formula should be blueprint-configurable
- **MED** `SequenceBuilder.tsx:138` — Default instructions `"Drag the items to arrange them in the correct order."` hardcoded -> should come from blueprint
- **MED** `SequenceBuilder.tsx:269` — Perfect order text `"Perfect! All items are in the correct order."` hardcoded English -> should be configurable
- **MED** `SequenceBuilder.tsx:243` — Sortable list `min-h-[200px]` hardcoded -> should scale with item count
- **LOW** `SequenceBuilder.tsx:227-229` — Position hint text `"First"` / `"Last"` hardcoded English -> should be configurable
- **LOW** `SequenceBuilder.tsx:293` — Button text `"Check Order"` / `"Try Again"` hardcoded -> should be configurable

### 7. CompareContrast.tsx

- **HIGH** `CompareContrast.tsx:110` — Score formula: `Math.round((correctCount / totalCount) * 100)`, maxScore always `100` -> should be blueprint-configurable
- **MED** `CompareContrast.tsx:47-52` — Category colors hardcoded (green/red/blue/purple for similar/different/unique_a/unique_b) -> should be theme-configurable
- **MED** `CompareContrast.tsx:54-59` — Category display labels hardcoded English (`"Similar in Both"`, `"Different"`, `"Unique to A"`, `"Unique to B"`) -> should come from blueprint
- **MED** `CompareContrast.tsx:67` — Default instructions hardcoded -> should come from blueprint
- **MED** `CompareContrast.tsx:253-255` — Result messages hardcoded English (`"Perfect! All structures categorized correctly."`) -> should be configurable
- **LOW** `CompareContrast.tsx:198` — Grid hardcoded to `grid-cols-2` for diagrams -> should support N-way comparison

### 8. SortingCategories.tsx

- **HIGH** `SortingCategories.tsx:235-239` — Score formula identical pattern: `Math.round((correctCount / totalCount) * 100)`, maxScore `100` -> should be blueprint-configurable
- **MED** `SortingCategories.tsx:152` — Default instructions `"Drag each item to the correct category."` hardcoded -> should come from blueprint
- **MED** `SortingCategories.tsx:307` — Grid column count capped at 4 via `Math.min(categories.length, 4)` -> should be configurable or responsive
- **MED** `SortingCategories.tsx:115` — DroppableCategory min height hardcoded to `150px` -> should scale with content
- **MED** `SortingCategories.tsx:344-346` — Result messages hardcoded English (`"Perfect! All items sorted correctly."`) -> should be configurable
- **LOW** `SortingCategories.tsx:138-139` — Empty category placeholder `"Drop items here"` hardcoded -> should be configurable

### 9. MemoryMatch.tsx

- **HIGH** `MemoryMatch.tsx:51` — Default flip duration hardcoded to `600ms` -> configurable via prop but default is arbitrary
- **HIGH** `MemoryMatch.tsx:123` — Unmatched flip-back delay is `flipDurationMs * 1.5` (hardcoded multiplier) -> multiplier should be configurable
- **HIGH** `MemoryMatch.tsx:132-135` — Scoring formula `Math.round(100 * (perfectAttempts / attempts))` capped at 100 -> scoring strategy should be configurable (e.g., time-based, moves-based)
- **MED** `MemoryMatch.tsx:232` — Card aspect ratio hardcoded to `4/3` -> should be configurable per game theme
- **MED** `MemoryMatch.tsx:249` — Card back gradient hardcoded to `from-blue-500 to-purple-600` -> should be theme-configurable
- **MED** `MemoryMatch.tsx:253` — Card back symbol hardcoded to `"?"` in 3xl font -> should support custom card backs (icons, images)
- **MED** `MemoryMatch.tsx:54` — Default instructions `"Click cards to find matching pairs."` hardcoded -> should come from blueprint
- **MED** `MemoryMatch.tsx:287-289` — Completion message `"Congratulations! All pairs matched!"` hardcoded English -> should be configurable
- **LOW** `MemoryMatch.tsx:88-89` — Grid auto-sizing uses `Math.ceil(Math.sqrt(totalCards))` -> reasonable default but should accept override

### 10. BranchingScenario.tsx

- **HIGH** `BranchingScenario.tsx:108-109` — Points per decision hardcoded to `10` -> should come from blueprint per-node `points` field
- **HIGH** `BranchingScenario.tsx:132` — Feedback-to-advance delay: `2000ms` with consequence, `500ms` without -> should be configurable
- **MED** `BranchingScenario.tsx:66` — Default instructions `"Navigate through the scenario by making decisions."` hardcoded -> should come from blueprint
- **MED** `BranchingScenario.tsx:218` — Scenario image height hardcoded to `h-48` (192px) -> should be configurable or responsive
- **MED** `BranchingScenario.tsx:332-333` — Completion summary `"Scenario Complete!"` and optimal choices text hardcoded English -> should be configurable
- **LOW** `BranchingScenario.tsx:322` — Processing button text `"Processing..."` / `"Confirm Choice"` hardcoded -> should be configurable

### 11. TimedChallengeWrapper.tsx

- **HIGH** `TimedChallengeWrapper.tsx:135-137` — Timer color thresholds hardcoded: red at <=10s, amber at <=30s, blue otherwise -> should be configurable relative to `timeLimitSeconds`
- **HIGH** `TimedChallengeWrapper.tsx:142` — Time bonus formula hardcoded to `Math.round((timeRemaining / timeLimitSeconds) * 20)` (max 20% bonus) -> multiplier and max should be configurable
- **MED** `TimedChallengeWrapper.tsx:256` — Time's up message `"Time's Up!"` and `"Your answers have been submitted."` hardcoded English -> should be configurable
- **MED** `TimedChallengeWrapper.tsx:241` — Paused overlay message `"Paused"` hardcoded English -> should be configurable
- **MED** `TimedChallengeWrapper.tsx:227-229` — Progress bar color thresholds repeat the same 10s/30s hardcoded values -> should use same config as timer display

### 12. SceneProgressBar.tsx

- **MED** `SceneProgressBar.tsx:69-74` — Progression type labels hardcoded: `"Zoom In"`, `"Explore Deep"`, `"Choose Path"`, `"Linear"` -> should come from sequence config
- **LOW** `SceneProgressBar.tsx:104` — Progress bar gradient hardcoded to `from-blue-500 to-indigo-500` -> should be theme-configurable
- **LOW** `SceneProgressBar.tsx:148` — Completion percentage text format `"X% complete"` hardcoded English -> should be i18n-aware

### 13. useEventLog.ts

- **LOW** `useEventLog.ts:79` — Fallback title `'unknown'` when blueprint title is missing -> minor, informational only
- **LOW** `useEventLog.ts:84` — `hasTimedChallenge` always passed as `false` -> should detect TimedChallengeWrapper presence

### 14. usePersistence.ts

- **MED** `usePersistence.ts:57` — Auto-save interval hardcoded to `30000ms` (30 seconds) -> configurable via prop but default may not suit all game types
- **MED** `usePersistence.ts:70-78` — Default `UserSettings` hardcoded (`fontSize: 'medium'`, `colorBlindMode: 'none'`, `soundEnabled: true`) -> should merge with blueprint accessibility config
- **LOW** `usePersistence.ts:109-112` — `hintsUsed`, `incorrectAttempts`, `elapsedTimeMs` all hardcoded to `0` with TODO comments -> tracking not implemented

### 15. useReducedMotion.ts

- **No findings.** This hook is clean -- it correctly reads the OS-level `prefers-reduced-motion` media query. No hardcoded values.

---

## Summary Statistics


| Severity  | Count  |
| --------- | ------ |
| HIGH      | 21     |
| MED       | 38     |
| LOW       | 19     |
| **Total** | **78** |


### Top Categories


| Category                    | Count | Examples                                                                          |
| --------------------------- | ----- | --------------------------------------------------------------------------------- |
| Feedback messages (English) | 18    | "Correct!", "Try again!", "Great job!", "Sequence Complete!"                      |
| Scoring formulas            | 7     | All use `(correct/total)*100`, maxScore=100, points-per-decision=10               |
| Timing / delays             | 12    | 1000ms transition, 1500ms feedback, 2000ms consequence, 600ms flip                |
| Colors / theming            | 8     | Path arrow #22c55e, hierarchy stroke levels, card-back gradient, timer thresholds |
| UI dimensions               | 6     | min-width 50px, min-h 200px, h-48 images, grid-cols-4 cap, 4/3 aspect ratio       |
| Mode/type labels            | 5     | MODE_INFO names, progression type labels, category labels                         |
| Animation params            | 4     | 0.5s path draw, flipDuration*1.5 multiplier, animate-pulse                        |
| Instructions text           | 6     | Default instruction strings across all interaction types                          |


---

## Capability Gaps

Things the interaction engine **cannot** currently do:


| Gap                                      | Status          | Impact                                                                                                                                                                                                                                                                |
| ---------------------------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Audio feedback**                       | Not implemented | No sound on correct/incorrect, no ambient audio, no narration. `soundEnabled` exists in settings but is never consumed by any interaction component.                                                                                                                  |
| **Custom animations**                    | Partial         | Components accept `AnimationSpec` via props for correct/incorrect placement, but most interactions (Sequence, Sorting, Memory, Branching, Compare) have zero animation hook integration. Only HotspotManager, PathDrawer, and HierarchyController use `useAnimation`. |
| **Particle effects**                     | Not implemented | No confetti, sparkle, or celebration effects on completion or correct answers.                                                                                                                                                                                        |
| **Drawing / freeform tools**             | Not implemented | PathDrawer only supports waypoint clicking, not actual freeform path drawing. No pen, brush, or annotation tools.                                                                                                                                                     |
| **Video content**                        | Not implemented | No support for video-based questions, video zones, or video feedback. BranchingScenario supports images but not video.                                                                                                                                                |
| **Collaborative / multiplayer**          | Not implemented | All state is single-player, single-session. No WebSocket, no shared state, no turn-based multiplayer.                                                                                                                                                                 |
| **Internationalization (i18n)**          | Not implemented | All UI strings are hardcoded English. No translation layer, no RTL support.                                                                                                                                                                                           |
| **Accessibility narration**              | Minimal         | `useReducedMotion` exists but is not consumed by most components. No screen reader announcements (aria-live), no keyboard navigation for card flipping, no focus management in SequenceBuilder sorting.                                                               |
| **Hint system per interaction**          | Not implemented | Event log supports `logHintRequested` but no interaction component exposes a hint UI (only the main LabelDiagramGame does for drag-drop).                                                                                                                             |
| **Adaptive difficulty**                  | Not implemented | No mechanism to adjust time limits, reduce options, or provide scaffolding based on incorrect attempts.                                                                                                                                                               |
| **Custom scoring strategies**            | Not implemented | Every component uses `(correct/total)*100` or variant. No support for weighted scoring, negative points, streak bonuses, or difficulty multipliers.                                                                                                                   |
| **Theming / skinning**                   | Not implemented | All colors are hardcoded Tailwind classes. No theme provider, no dark mode awareness in interaction components (only ModeIndicator has dark mode classes).                                                                                                            |
| **Progress persistence per interaction** | Partial         | `usePersistence` saves global game state but individual interaction components (SequenceBuilder, SortingCategories, etc.) manage state locally and lose it on unmount.                                                                                                |
| **Timer integration per interaction**    | Wrapper only    | `TimedChallengeWrapper` wraps children but has no callback integration with child component submission -- it relies on the child calling `onComplete` independently.                                                                                                  |
| **Undo/redo per interaction**            | Not implemented | Only the main drag-drop mode has command history. SequenceBuilder, SortingCategories, CompareContrast have no undo support.                                                                                                                                           |
| **Custom card backs / skins**            | Not implemented | MemoryMatch card backs are a hardcoded blue-purple gradient with "?". No support for themed card designs.                                                                                                                                                             |
| **Multi-diagram comparison**             | Limited         | CompareContrast is hardcoded to exactly 2 diagrams side-by-side. No 3-way or N-way comparison.                                                                                                                                                                        |
| **Branching visualization**              | Not implemented | BranchingScenario shows a linear path trace but no tree/graph visualization of the decision tree.                                                                                                                                                                     |
| **Response time analytics**              | Partial         | Events are logged with timestamps but no per-interaction response-time metrics are surfaced to the user or used for scoring.                                                                                                                                          |


