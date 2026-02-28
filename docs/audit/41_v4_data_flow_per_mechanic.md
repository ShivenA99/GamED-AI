# V4 Data Flow Per-Mechanic Audit

**Date**: 2026-02-14
**Scope**: Trace the complete data flow for each of 9 mechanics through the V4 pipeline (GamePlan → content_generator → interaction_designer → asset_pipeline → blueprint_assembler → frontend component). Identify gaps and mismatches.
**Status**: COMPLETE -- 51 gaps (6 CRITICAL, 20 HIGH, 18 MEDIUM, 7 LOW)

---

## Methodology

For each mechanic, trace:
1. What `game_designer` must output in `GamePlan.MechanicPlan`
2. What `content_generator` must produce
3. What `interaction_designer` must produce
4. What assets are needed
5. What `blueprint_assembler` must produce
6. What the **frontend component ACTUALLY reads** (source of truth)

Frontend sources examined:
- `types.ts` -- TypeScript interfaces
- `mechanicRegistry.ts` -- `extractProps()` per mechanic
- Individual component files (9 interaction components)
- `sceneManager.ts` -- `sceneToBlueprint()`
- `extractTaskConfig.ts` -- config resolution priority

---

## 1. drag_drop

### Frontend Reads
- `bp.diagram.zones[]` -- zone positions (x, y, radius/points)
- `bp.diagram.assetUrl` -- background image
- `bp.labels[]` -- each with `id`, `text`, `correctZoneId`
- `bp.distractorLabels[]` -- separate array
- `bp.dragDropConfig` -- 28+ optional fields (interactionMode, leaderLines, etc.)
- `bp.animationCues` -- required (correctPlacement, incorrectPlacement)
- `bp.mechanics[]` -- mechanic entry with scoring/feedback

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| DD-1 | ContentBrief for drag_drop undefined | HIGH |
| DD-2 | DragDropConfig has 28+ fields with no field-level mapping to pipeline stages | HIGH |
| DD-3 | Leader line anchor generation unspecified | MEDIUM |
| DD-4 | EnhancedLabel/EnhancedDistractorLabel extended fields not addressed | MEDIUM |
| DD-M1 | `interactionMode` required vs optional mismatch | LOW |

---

## 2. click_to_identify

### Frontend Reads
- `bp.identificationPrompts[]` -- **at blueprint ROOT, NOT inside config**
- Each prompt: `id`, `text`, `targetZoneId`, `targetLabelId`, `explanation`, `order`
- `bp.clickToIdentifyConfig` -- `selectionMode`, `showExplanation`, etc.
- `bp.diagram.zones[]`, `bp.diagram.assetUrl`

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| CI-1 | ContentBrief undefined | HIGH |
| CI-2 | Prompt-to-zone ID mapping logic not described | HIGH |
| CI-3 | Polygon vs circle zone detection strategy not specified | MEDIUM |
| CI-M1 | `IdentificationPrompt.order` must be required for sequential mode | MEDIUM |

---

## 3. trace_path

### Frontend Reads
- `bp.paths[]` -- **at blueprint ROOT, NOT inside tracePathConfig**
- Each path: `id`, `label`, `color`, `waypoints[]` (each with `id`, `label`, `zoneId`, `order`)
- `bp.tracePathConfig` -- `showLabels`, `allowFreeform`, `snapToWaypoints`, etc.
- Component uses `TracePathProgress` (NOT `PathProgress` -- different type!)

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| TP-1 | ContentBrief undefined | HIGH |
| TP-2 | Waypoint zoneId resolution not described | HIGH |
| TP-M1 | Store initialization uses wrong type (PathProgress vs TracePathProgress) | HIGH |
| TP-4 | Waypoint type (gate/branch_point/terminus) population not specified | MEDIUM |
| TP-5 | submitMode (batch vs immediate) not specified | MEDIUM |
| TP-3 | svg_path_data generation optional (component auto-generates) | LOW |

---

## 4. sequencing

### Frontend Reads
- `bp.sequenceConfig.items[]` -- each: `id`, `content`, `position`, `explanation`, `image_url`
- `bp.sequenceConfig.correct_order` -- array of item IDs
- `bp.sequenceConfig.sequence_type`, `layout_mode`, `instructions`
- Component has extra fields: `card_type`, `show_position_numbers`

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| SQ-1 | ContentBrief undefined | HIGH |
| SQ-2 | layout_mode value remapping fragile (vertical_list vs vertical_timeline) | MEDIUM |
| SQ-3 | Component has extra config fields backend never produces | MEDIUM |
| SQ-4 | Item image generation for image card types unspecified | MEDIUM |
| SQ-M1 | layout_mode enum values don't match between backend and component | MEDIUM |

---

## 5. sorting_categories

### Frontend Reads
- `bp.sortingConfig.categories[]` -- each: `id`, `label`, `color`, `description`
- `bp.sortingConfig.items[]` -- each: `id`, `content`, `correctCategoryId`, `explanation`
- Note: frontend reads `label`, backend design uses `name`

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| SO-1 | ContentBrief undefined | HIGH |
| SO-M1 | Backend `name` vs frontend `label` field mismatch | MEDIUM |
| SO-2 | Category color generation source unspecified | LOW |

---

## 6. memory_match

### Frontend Reads
- `bp.memoryMatchConfig.pairs[]` -- each: `id`, `front`, `back`, `frontType`, `backType`, `explanation`
- Note: frontend reads `front`/`back`, backend design uses `term`/`definition`
- `bp.memoryMatchConfig.gridSize` -- `[rows, cols]` tuple
- `game_variant` routes to `ColumnMatchMode` if 'column_match'

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| MM-1 | ContentBrief undefined | HIGH |
| MM-2 | Image pair generation for image-type pairs unspecified | HIGH |
| MM-4 | ColumnMatchMode variant requirements not addressed | MEDIUM |
| MM-3 | gridSize auto-calculation source unspecified | LOW |
| MM-M1 | gridSize list vs tuple typing | LOW |

---

## 7. branching_scenario

### Frontend Reads
- `bp.branchingConfig.nodes[]` -- each: `id`, `question`, `description`, `imageUrl`, `options[]`
- Each option: `id`, `text`, `nextNodeId`, `isCorrect`, `consequence`, `points`
- Note: frontend reads `question`/`options`/`nextNodeId`, backend uses `prompt`/`choices`/`next_node_id`
- `bp.branchingConfig.startNodeId`, `showPathTaken`, `allowBacktrack`

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| BR-1 | ContentBrief undefined | HIGH |
| BR-2 | Graph construction guidance for LLM not specified | HIGH |
| BR-3 | Option points: content_generator vs interaction_designer responsibility | MEDIUM |
| BR-4 | Node image generation unspecified | LOW |
| BR-5 | pointsPerDecision and timingConfig undocumented component props | LOW |

---

## 8. compare_contrast

### Frontend Reads
- `bp.compareConfig.diagramA` -- `{id, name, imageUrl, zones[]}`
- `bp.compareConfig.diagramB` -- same structure
- Each zone: `id`, `label`, `x`, `y`, `width`, `height` (rect format, NOT circle)
- `bp.compareConfig.expectedCategories` -- `Record<string, 'similar' | 'different' | 'unique_a' | 'unique_b'>`

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| CC-2 | **Dual diagram asset pipeline not addressed** -- need TWO parallel searches | CRITICAL |
| CC-3 | **Zone detection for compare uses rect (x,y,w,h) vs standard circle (x,y,r)** | CRITICAL |
| CC-4 | **Cross-diagram zone correspondence undefined** | CRITICAL |
| CC-5 | **imageUrl population for both diagrams not described** | CRITICAL |
| CC-1 | ContentBrief undefined | HIGH |
| CC-M1 | Backend CompareDiagram.zones uses loose Dict typing | HIGH |
| CC-M2 | Zone shape difference (circle vs rect) | MEDIUM |

**Most problematic mechanic**: 4 CRITICAL + 2 HIGH gaps. Requires fundamentally different asset pipeline path.

---

## 9. description_matching

### Frontend Reads
- `bp.diagram.zones[]` with `description` field populated
- `bp.descriptionMatchingConfig.descriptions` -- `Record<zoneId, description>` (takes priority)
- `bp.labels[]` -- used to build MC options
- `mode`: 'click_zone' | 'drag_description' | 'multiple_choice'

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| DM-1 | ContentBrief undefined | HIGH |
| DM-4 | Completion breaks if descriptions only in config map (not on zones) | HIGH |
| DM-2 | Two description sources, priority unclear | MEDIUM |
| DM-3 | MC distractor descriptions generation unspecified | MEDIUM |

---

## 10. Cross-Cutting Gaps

These affect ALL or MULTIPLE mechanics:

| # | Gap | Severity | Description |
|---|-----|----------|-------------|
| CG-1 | **ContentBrief type completely undefined** | CRITICAL | Each mechanic needs different brief data. Must be discriminated union or per-mechanic validation. |
| CG-2 | **MechanicContent output type undefined** | CRITICAL | Content_generator has no output contract. Need 9 per-mechanic Pydantic models. |
| CG-3 | interaction_designer output-to-blueprint mapping undefined | HIGH | ScoringRules, FeedbackRules, ModeTransitions must map to specific blueprint fields. |
| CG-4 | Zone ID generation timing | HIGH | Content runs before assets. Label-to-ID mapping needed for ALL mechanics uniformly. |
| CG-5 | animationCues required field population | MEDIUM | Required non-optional, but no pipeline stage produces it. |
| CG-6 | Multi-scene per-mechanic config forwarding | MEDIUM | camelCase/snake_case duality at scene level. |
| CG-7 | Store initialization type mismatch for trace_path | HIGH | PathProgress vs TracePathProgress in mechanicRegistry. |
| CG-8 | Score arithmetic consistency | MEDIUM | Item count drift between game_designer and content_generator. |

---

## 11. Summary

### By Severity

| Severity | Count |
|----------|-------|
| CRITICAL | 6 (CG-1, CG-2, CC-2, CC-3, CC-4, CC-5) |
| HIGH | 20 |
| MEDIUM | 18 |
| LOW | 7 |
| **Total** | **51** |

### By Mechanic

| Mechanic | CRITICAL | HIGH | MEDIUM | LOW | Total |
|----------|----------|------|--------|-----|-------|
| drag_drop | 0 | 2 | 2 | 1 | 5 |
| click_to_identify | 0 | 2 | 2 | 0 | 4 |
| trace_path | 0 | 3 | 2 | 1 | 6 |
| sequencing | 0 | 1 | 4 | 0 | 5 |
| sorting_categories | 0 | 1 | 1 | 1 | 3 |
| memory_match | 0 | 2 | 1 | 2 | 5 |
| branching_scenario | 0 | 2 | 1 | 2 | 5 |
| compare_contrast | 4 | 2 | 1 | 0 | 7 |
| description_matching | 0 | 2 | 2 | 0 | 4 |
| Cross-cutting | 2 | 3 | 3 | 0 | 8 |

### Most Problematic

1. **compare_contrast** (7 gaps, 4 CRITICAL) -- needs entirely different asset pipeline
2. **trace_path** (6 gaps) -- store initialization mismatch + waypoint resolution
3. **drag_drop** (5 gaps) -- most fields, most complexity in config

---

## 12. Recommendations

### Before Writing Code

1. **Define ContentBrief as per-mechanic discriminated union** in `schemas/game_plan.py`
2. **Define MechanicContent as 9 per-mechanic Pydantic models** in `schemas/mechanic_content.py`
3. **Add zone-label-to-ID mapping step** to blueprint_assembler for ALL mechanics
4. **Fix trace_path store initialization** to use `TracePathProgress`
5. **Design compare_contrast dual-diagram pipeline** explicitly

### Schema-Level

6. **Unify layout_mode values** between backend and frontend
7. **Strict-type CompareDiagram.zones** to match frontend
8. **Document description_matching dual-source behavior**

### Pipeline-Level

9. **Add per-mechanic prompt templates** with exact field requirements
10. **Add image generation triggers** for memory pairs, sequencing items, branching nodes

---

## Key Files Referenced

- `frontend/src/components/templates/InteractiveDiagramGame/types.ts`
- `frontend/src/components/templates/InteractiveDiagramGame/mechanicRegistry.ts`
- `frontend/src/components/templates/InteractiveDiagramGame/engine/sceneManager.ts`
- All 9 interaction component files in `interactions/`
- `backend/app/tools/blueprint_assembler_tools.py`
- `backend/app/agents/schemas/interactive_diagram.py`
- `backend/app/agents/schemas/game_design_v3.py`
- `docs/v4_implementation_plan_final.md`
- `docs/v4_formal_graph_rules.html`
