# 05 - V3 Pipeline Data Flow Trace

## Overview

This document traces five critical data paths through the V3 pipeline end-to-end, from the first agent that produces the data to the frontend component that renders it. Each path documents every transformation point, the state fields involved, and known issues that can cause silent data loss or incorrect behavior.

The five paths covered:

| # | Path | Origin Agent | Terminal Renderer |
|---|------|-------------|-------------------|
| 1 | Labels | domain_knowledge_retriever | DraggableLabel / DropZone |
| 2 | Zone Coordinates | asset_generator_v3 (detect_zones) | DropZone (SVG polygon/circle/rect) |
| 3 | Mechanic Config | game_designer_v3 | useLabelDiagramState scoring logic |
| 4 | Multi-Scene | game_designer_v3 | GameSequence / TaskProgressBar |
| 5 | Scoring / Feedback | interaction_designer_v3 | ResultsPanel / GameControls |

---

## Path 1: Labels Flow

### Transformation Diagram

```
domain_knowledge_retriever
  |
  |  LLM JSON guided decoding
  |  writes: domain_knowledge.canonical_labels (nested dict)
  |  writes: state.canonical_labels (top-level list)
  v
game_designer_v3  (ReAct, reads via context injection)
  |
  |  Splits into zone_labels + distractor_labels
  |  Output: GameDesignV3Slim.labels
  |  Truncation boundary: 30 labels max
  v
scene_architect_v3  (ReAct)
  |
  |  Creates zone specs: {zone_id, label, position_hint}
  |  Output: SceneSpecV3.zones[]
  v
asset_generator_v3  (ReAct, detect_zones tool)
  |
  |  Passes labels for zone detection against image
  |  Output: generated_assets_v3[scene].zones[]
  v
blueprint_assembler_v3  (ReAct)
  |
  |  Maps labels to zones -> IDLabel[] + IDZone[]
  |  Distractors get correctZoneId: null
  |  Output: blueprint.scenes[].labels, blueprint.scenes[].zones
  v
Frontend
  |
  |  Label[] -> DraggableLabel components
  |  Zone[]  -> DropZone components
  v
[Rendered Game]
```

### Issues

| ID | Severity | Description |
|----|----------|-------------|
| L1 | P0 | **canonical_labels routing gap** -- domain_knowledge_retriever writes labels into the `domain_knowledge` dict. Downstream agents read `state.canonical_labels` at the top level. If middleware or a post-step does not copy the nested value to the top-level field, downstream agents receive an empty list. Must verify that the copy happens reliably. |
| L2 | P1 | **Label truncation at 30** -- game_designer_v3 may silently drop labels beyond position 30. For complex diagrams with >30 structures, this means some correct answers are simply absent from the game. No warning is emitted. |
| L3 | P1 | **Distractor correctZoneId not validated** -- Distractor labels must have `correctZoneId: null` in the blueprint. No Pydantic validator or runtime check enforces this invariant. A malformed distractor with a valid zone ID would be scored as a correct label, breaking gameplay. |

---

## Path 2: Zone Coordinates Flow

### Transformation Diagram

```
asset_generator_v3  (detect_zones tool)
  |
  |  Raw output: pixel coords, percentages, or polygon points
  |  Format varies by detection backend (Gemini, Qwen, SAM3)
  v
_normalize_zones_to_percent()
  |
  |  Converts all formats to 0-100% scale
  |  Fallback: (50, 50) center for missing coordinates
  |  BYPASS: dict instances skip normalization (isinstance early return)
  v
generated_assets_v3[scene_number].zones[]
  |
  |  Stored as list of zone dicts with normalized coordinates
  v
blueprint_assembler_v3
  |
  |  _normalize_coordinates(): converts to IDZone coordinate format
  |  _postprocess_zones(): adds `points` field for frontend consumption
  |  Computes center for polygons
  v
blueprint.scenes[].zones[]  (IDZone format)
  |
  |  circle:  { x, y, radius }
  |  polygon: { points: [[x,y], ...], center: {x, y} }
  |  rect:    { x, y, width, height }
  v
Frontend DropZone component
  |
  |  Reads zone.points as [number, number][]
  |  Renders SVG shapes
  v
[Rendered Game]
```

### Issues

| ID | Severity | Description |
|----|----------|-------------|
| Z1 | P0 | **Silent fallback to (50, 50)** -- When coordinates are missing or unparseable, `_normalize_zones_to_percent` silently defaults to center (50, 50). This places a zone in the middle of the image with no warning, making the game unsolvable for that label. |
| Z2 | P0 | **Dict passthrough bypasses normalization** -- If zones arrive as plain dicts (not dataclass/Pydantic instances), the `isinstance` check returns early and the zone passes through without any coordinate normalization. Raw pixel values then reach the frontend as-is, placing zones at incorrect positions. |
| Z3 | P1 | **Polygon with <3 points** -- A polygon with fewer than 3 points is not detected as a polygon type. It falls through to a default handler that may misinterpret the shape, producing an invalid zone geometry. |
| Z4 | P1 | **Center computation includes invalid points** -- When computing the center of a polygon, all points are averaged including any that were defaulted to (0, 0) or (50, 50) due to upstream failures. This shifts the center away from the true geometric center. |

---

## Path 3: Mechanic Config Flow

### Transformation Diagram

```
game_designer_v3  (ReAct)
  |
  |  MechanicDesign:
  |    type: str (e.g., "drag_drop", "sequence", "trace_path")
  |    zone_labels_used: list[str]
  |    config: Dict[str, Any]  (generic, unvalidated)
  v
scene_architect_v3  (ReAct)
  |
  |  MechanicConfig:
  |    mechanic_type: str
  |    zone_labels_used: list[str]
  |    config: detailed per-mechanic settings
  |  DEFAULT: missing mechanic_type -> "drag_drop"
  v
interaction_designer_v3  (ReAct)
  |
  |  ScoringData (as LIST):
  |    mechanic_type, points_per_correct, max_score, ...
  |  FeedbackData (as LIST):
  |    mechanic_type, correct_message, incorrect_message, hints, ...
  |  SKIP: missing mechanic_type items silently discarded
  v
blueprint_assembler_v3
  |
  |  List[ScoringData] -> Dict[mechanic_type, ScoringData]
  |  List[FeedbackData] -> Dict[mechanic_type, FeedbackData]
  |  FALLBACK: lookup miss -> use "first available" entry
  |  FILTER: custom scoring fields dropped during key filtering
  v
blueprint.scenes[].mechanics[].scoring
blueprint.scenes[].mechanics[].feedback
  |
  v
Frontend useLabelDiagramState
  |
  |  Reads scoring for point calculation
  |  Reads feedback for correct/incorrect messages
  |  DEFAULT: missing scoring -> hardcoded 10pts, 100 max
  v
[Rendered Game]
```

### Issues

| ID | Severity | Description |
|----|----------|-------------|
| M1 | P1 | **Config is generic Dict[str, Any]** -- The `config` field in MechanicDesign has no per-mechanic-type validation. A drag_drop mechanic could receive sequence-specific config keys without any error, leading to silent misconfiguration. |
| M2 | P1 | **Missing mechanic_type defaults to "drag_drop"** -- In scene_architect_v3, if the LLM omits mechanic_type, the code silently defaults to "drag_drop". This masks cases where the LLM failed to classify the mechanic, potentially applying drag-drop scoring to a sequence mechanic. |
| M3 | P0 | **Missing mechanic_type in scoring/feedback lists** -- When interaction_designer_v3 produces ScoringData or FeedbackData list items without a mechanic_type field, those items are silently discarded during the List-to-Dict conversion. This can result in a mechanic having no scoring or feedback data at all. |
| M4 | P0 | **Fallback to "first available" scoring** -- When blueprint_assembler_v3 cannot find scoring for a specific mechanic_type, it falls back to the first available entry in the dict. This means the WRONG mechanic's scoring rules get applied, producing incorrect point calculations. |
| M5 | P1 | **Key filtering drops custom fields** -- During blueprint assembly, a key-filtering step strips non-standard scoring fields. Custom scoring configurations (e.g., partial credit percentages, bonus multipliers) are silently removed. |

---

## Path 4: Multi-Scene Flow

### Transformation Diagram

```
game_designer_v3  (ReAct)
  |
  |  scenes[]: scene_number (int), description, focus_labels
  |  Scenes represent image boundaries
  |  Tasks represent mechanics/phases within a scene
  v
scene_architect_v3  (ReAct)
  |
  |  scene_specs_v3[]: indexed by scene_number (int)
  |  Each spec has zones, layout, mechanic configs
  v
asset_generator_v3  (ReAct)
  |
  |  generated_assets_v3: keyed by scene_number as STRING ("1", "2")
  |  Assignment is heuristic: based on tool call order, not explicit
  v
blueprint_assembler_v3
  |
  |  Converts string keys -> int keys
  |  Builds scenes[] list ordered by scene_number
  |  NON-SEQUENTIAL scene numbers may leave gaps
  v
blueprint.scenes[]
  |
  v
Frontend GameSequence
  |
  |  Linear navigation through scenes[]
  |  TaskProgressBar shows per-scene task progress
  v
[Rendered Game]
```

### Issues

| ID | Severity | Description |
|----|----------|-------------|
| S1 | P1 | **Heuristic scene assignment** -- asset_generator_v3 assigns assets to scenes based on the order of tool calls during its ReAct loop, not based on an explicit scene_number in the tool output. If the LLM calls tools in a different order than expected, assets end up associated with the wrong scene. |
| S2 | P1 | **String-to-int key conversion** -- asset_generator_v3 stores scene numbers as string keys ("1", "2") while other agents use integer keys. The conversion in blueprint_assembler_v3 assumes all keys are numeric strings. A non-numeric key (e.g., "scene_1") would cause a crash. |
| S3 | P1 | **Non-sequential scene numbers** -- If game_designer_v3 produces scene numbers [1, 3, 5], the blueprint scenes list will have gaps or require re-indexing. The frontend navigates linearly through the array, so gaps cause either empty scenes or index mismatches. |

---

## Path 5: Scoring / Feedback Flow

### Transformation Diagram

```
interaction_designer_v3  (ReAct)
  |
  |  scoring: List[ScoringData]
  |    Each: { mechanic_type, points_per_correct, max_score, penalty, ... }
  |  feedback: List[FeedbackData]
  |    Each: { mechanic_type, correct_message, incorrect_message, hints[], ... }
  v
blueprint_assembler_v3
  |
  |  List[ScoringData] -> Dict[str, ScoringData]  (keyed by mechanic_type)
  |  List[FeedbackData] -> Dict[str, FeedbackData] (keyed by mechanic_type)
  |
  |  OVERWRITE: duplicate mechanic_type -> last entry wins
  |  DISCARD:   missing mechanic_type -> entry silently dropped
  |  EMBED:     per-mechanic scoring/feedback into scenes[].mechanics[]
  v
blueprint.scenes[].mechanics[].scoring
blueprint.scenes[].mechanics[].feedback
  |
  v
Frontend useLabelDiagramState
  |
  |  scoring -> point calculation per label placement
  |  feedback -> correct/incorrect toast messages, hint display
  |  DEFAULT: missing scoring -> { points_per_correct: 10, max_score: 100 }
  v
ResultsPanel (final score, summary)
GameControls (live feedback, hints)
  |
  v
[Rendered Game]
```

### Issues

| ID | Severity | Description |
|----|----------|-------------|
| F1 | P0 | **Duplicate mechanic_type overwrites** -- When multiple ScoringData entries share the same mechanic_type, the List-to-Dict conversion keeps only the last entry. Earlier entries are silently discarded. In a multi-task scene where two tasks use the same mechanic type but need different scoring, only the last task's scoring survives. |
| F2 | P0 | **Missing mechanic_type silently discards entry** -- Same root cause as M3. Scoring/feedback entries without a mechanic_type field are dropped during conversion. No error is logged. |
| F3 | P1 | **Hardcoded frontend defaults** -- When scoring data is absent from the blueprint, the frontend falls back to `points_per_correct: 10, max_score: 100`. These defaults may not match the intended difficulty or scale of the game, producing misleading scores. |

---

## Cross-Cutting Issues

These issues affect multiple data paths and represent systemic patterns rather than isolated bugs.

| ID | Paths Affected | Description |
|----|---------------|-------------|
| X-A | 1, 3, 5 | **canonical_labels routing** -- domain_knowledge_retriever writes to `domain_knowledge.canonical_labels` (nested). Downstream agents read `state.canonical_labels` (top-level). If the copy from nested to top-level fails or is skipped, labels are empty for all downstream consumers. This is the single most impactful failure mode in the pipeline. |
| X-B | 3, 5 | **List-to-Dict conversions require mechanic_type key** -- Three separate conversion points (scoring, feedback, mechanic config) all key by `mechanic_type`. Missing keys cause silent data loss at every conversion. This is a recurring pattern that should be solved once with a shared utility that logs warnings. |
| X-C | 2 | **Coordinate normalization hazards** -- Silent defaults to (0, 0) or (50, 50) for unparseable coordinates create zones that appear valid but are positioned incorrectly. Combined with the dict passthrough bypass, raw pixel values can reach the frontend, rendering zones off-screen or at pixel coordinates interpreted as percentages. |
| X-D | 1 | **Distractor label validation gap** -- No point in the pipeline validates that distractor labels lack a `correctZoneId`. If a distractor is accidentally assigned a zone, it becomes a "correct" answer that the player cannot distinguish from real labels. |
| X-E | 4 | **Scene number sequentiality** -- No agent enforces that scene numbers are sequential starting from 1. Gaps in scene numbering propagate through the pipeline and cause frontend rendering issues when scenes are accessed by array index. |

---

## Consolidated Issue Tracker

All issues from the five paths collected in one place for triage.

| ID | Path | Severity | Summary |
|----|------|----------|---------|
| L1 | Labels | P0 | canonical_labels routing gap (nested vs top-level) |
| L2 | Labels | P1 | Label truncation at 30 with no warning |
| L3 | Labels | P1 | Distractor correctZoneId not validated |
| Z1 | Zones | P0 | Silent fallback to (50, 50) for missing coordinates |
| Z2 | Zones | P0 | Dict passthrough bypasses normalization |
| Z3 | Zones | P1 | Polygon with <3 points not rejected |
| Z4 | Zones | P1 | Center computation includes invalid points |
| M1 | Mechanic | P1 | Config is generic Dict with no per-type validation |
| M2 | Mechanic | P1 | Missing mechanic_type silently defaults to drag_drop |
| M3 | Mechanic | P0 | Missing mechanic_type in scoring/feedback lists causes silent discard |
| M4 | Mechanic | P0 | Fallback to first-available scoring applies wrong rules |
| M5 | Mechanic | P1 | Key filtering drops custom scoring fields |
| S1 | Scenes | P1 | Heuristic scene assignment by tool call order |
| S2 | Scenes | P1 | String-to-int key conversion assumes numeric strings |
| S3 | Scenes | P1 | Non-sequential scene numbers cause gaps |
| F1 | Scoring | P0 | Duplicate mechanic_type overwrites earlier entries |
| F2 | Scoring | P0 | Missing mechanic_type silently discards entry |
| F3 | Scoring | P1 | Hardcoded frontend defaults (10pts, 100 max) |
| X-A | Cross | P0 | canonical_labels nested-to-top-level routing |
| X-B | Cross | P0 | List-to-Dict conversions need mechanic_type key (3 places) |
| X-C | Cross | P0 | Coordinate normalization silent defaults |
| X-D | Cross | P1 | Distractor label validation gap |
| X-E | Cross | P1 | Scene number sequentiality not enforced |

**Totals:** 8 P0, 12 P1, 3 cross-cutting (P0+P1)

---

## Priority Recommendations

### P0 -- Must Fix (Data Correctness at Risk)

1. **Verify canonical_labels routing (X-A, L1)** -- Audit the state propagation between domain_knowledge_retriever and game_designer_v3. Ensure middleware or a post-step reliably copies `domain_knowledge.canonical_labels` to `state.canonical_labels`. Add a runtime assertion or warning log if the top-level field is empty when the nested field is populated.

2. **Validate mechanic_type in scoring/feedback (X-B, M3, F1, F2)** -- Add a Pydantic validator to ScoringData and FeedbackData that requires `mechanic_type` to be non-empty. In the List-to-Dict conversion, log a warning when entries are discarded or overwritten. Consider using a dict-of-lists to handle duplicate mechanic_type keys across tasks.

3. **Fix coordinate normalization (X-C, Z1, Z2)** -- Remove the silent fallback to (50, 50). Instead, log an error and mark the zone as invalid so the blueprint assembler can exclude it or request re-detection. Fix the dict passthrough by normalizing all zone formats uniformly regardless of Python type.

4. **Remove fallback-to-first scoring (M4)** -- When scoring lookup fails for a mechanic_type, raise an error or use explicit defaults rather than silently applying the wrong mechanic's scoring rules.

### P1 -- Should Fix (Robustness)

5. **Add Pydantic validators for mechanic config (M1)** -- Create per-mechanic-type config schemas (DragDropConfig, SequenceConfig, TracePathConfig) and validate at the MechanicDesign level. This catches misconfiguration at the earliest possible point.

6. **Enforce sequential scene numbers (X-E, S3)** -- Add a post-processing step in blueprint_assembler_v3 that re-indexes scenes to be sequential (1, 2, 3, ...) regardless of the original numbering. Log a warning when re-indexing occurs.

7. **Fix heuristic scene assignment (S1)** -- Require asset_generator_v3 tools to include an explicit `scene_number` in their output. Parse this field rather than relying on tool call order.

8. **Handle duplicate mechanic_type in scoring (F1)** -- When multiple scoring entries share a mechanic_type, either merge them (if the entries are for different tasks) or keep the first and warn (if they are true duplicates).

### P2 -- Nice to Have (Observability and Safety)

9. **Document label truncation (L2)** -- Add a log warning when labels exceed the 30-item limit in game_designer_v3. Include the count of dropped labels so pipeline operators can identify affected runs.

10. **Add coordinate logging (Z1, Z4)** -- Log raw and normalized coordinates at each transformation point. This creates an audit trail for diagnosing zone placement issues without requiring a full pipeline re-run.

11. **Validate distractor labels (L3, X-D)** -- Add a blueprint post-processing check that verifies all labels marked as distractors have `correctZoneId: null`. Flag violations as warnings in the pipeline output.

12. **Polygon point count validation (Z3)** -- Reject or warn on polygons with fewer than 3 points during zone normalization. Fall back to a bounding-box rectangle if the polygon is degenerate.
