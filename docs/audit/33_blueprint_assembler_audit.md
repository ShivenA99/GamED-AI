# Audit 33: Blueprint Assembler Layer — Deep Audit

**Date:** 2026-02-14
**Scope:** `blueprint_assembler_v3.py`, `blueprint_assembler_tools.py`, upstream schemas, frontend contracts
**Goal:** Make multi-scene, multi-mechanic games work without exceptions

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Complete Data Flow](#2-complete-data-flow)
3. [Per-Mechanic Config Assembly (All 10 Types)](#3-per-mechanic-config-assembly)
4. [Multi-Scene Assembly](#4-multi-scene-assembly)
5. [Known Data Loss Points](#5-known-data-loss-points)
6. [Zone/Label Format Conversion](#6-zonelabel-format-conversion)
7. [Gap Analysis: Frontend Expects vs Assembler Produces](#7-gap-analysis)
8. [mechanic_contracts.py Usage](#8-mechanic-contracts-usage)
9. [Bug Registry (All Bugs Found)](#9-bug-registry)
10. [Proposed Fixes with Priority](#10-proposed-fixes)

---

## 1. Executive Summary

The blueprint assembler is the FINAL pipeline stage before frontend rendering. It reads 4 upstream state fields (`game_design_v3`, `scene_specs_v3`, `interaction_specs_v3`, `generated_assets_v3`) and produces a single `blueprint` dict that the frontend consumes.

There are **two assembly paths**:
1. **Deterministic path** (`deterministic_blueprint_assembler_agent` in `blueprint_assembler_v3.py:658`): Calls `assemble_blueprint_impl()` directly, then validate/repair loop. **No LLM overhead.** This is the preferred path.
2. **ReAct path** (`blueprint_assembler_v3_agent` in `blueprint_assembler_v3.py:620`): Uses `BlueprintAssemblerV3` ReAct agent that calls the same 4 tools (`assemble_blueprint`, `validate_blueprint`, `repair_blueprint`, `submit_blueprint`).

Both paths ultimately call the same implementation functions in `blueprint_assembler_tools.py`.

**Critical finding:** The assembler does NOT use `mechanic_contracts.py` at all. All mechanic-specific logic is hardcoded in 10 `elif` blocks within `assemble_blueprint_impl()` (lines 586-860) and duplicated in `repair_blueprint_impl()` (lines 1618-1840). This is the opposite of what the contracts registry was designed to eliminate.

### Key Stats
- **26 bugs found** (8 critical, 10 high, 8 medium)
- **~600 lines of duplicated logic** between assembly and repair
- **3 distinct field naming conventions** collide (backend snake_case, frontend camelCase, legacy mix)
- **2 parallel schema hierarchies** (`blueprint_schemas.py` IDScene/IDZone vs `interactive_diagram.py` InteractiveDiagramBlueprint)

---

## 2. Complete Data Flow

### 2.1 Upstream Inputs

| State Field | Source Agent | Type | Description |
|---|---|---|---|
| `game_design_v3` | `game_designer_v3` | `GameDesignV3` or `GameDesignV3Slim` (dict or Pydantic) | Full game design with scenes, mechanics, labels |
| `scene_specs_v3` | `scene_architect_v3` | `List[Dict]` | Per-scene zones, mechanic_configs, position hints |
| `interaction_specs_v3` | `interaction_designer_v3` | `List[Dict]` | Per-scene scoring, feedback, mode_transitions, misconceptions |
| `generated_assets_v3` | `asset_generator_v3` | `Dict` | `{scenes: {scene_num: {diagram_image_url, zones: [...]}}}` |

### 2.2 Assembly Pipeline (inside `assemble_blueprint_impl()`)

```
Step 1: Parse game_design_v3 (dict or Pydantic → dict)
Step 2: Index scene_specs and interaction_specs by scene_number
Step 3: Extract global design fields (title, theme, labels, distractors, hierarchy)
Step 4: For each scene in design.scenes:
  4a: Get scene zone labels (scene_design.zone_labels || global_labels)
  4b: Get asset data for scene (detected zones + diagram_image_url)
  4c: Get scene spec (mechanic_configs, spec zones)
  4d: Get interaction spec (scoring, feedback, misconceptions)
  4e: Build zones (merge detected zones + spec zones + design labels)
  4f: Build labels (from zones, non-distractor only)
  4g: Build mechanics (merge design mechanics + scene_spec configs + interaction scoring/feedback)
  4h: Populate per-mechanic config keys (trace_path→paths+tracePathConfig, etc.)
  4i: Post-process zones (flatten coordinates → x/y/points/center)
Step 5: Build scene transitions
Step 6: Convert scenes to frontend format (GameScene objects)
Step 7: For multi-scene: wrap in game_sequence; for single: flatten to root
Step 8: Promote first scene's mechanic configs to root level for backward compat
```

### 2.3 Output Blueprint Shape

**Single-scene** (flat):
```json
{
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "...",
  "narrativeIntro": "...",
  "diagram": { "assetUrl": "...", "zones": [...] },
  "zones": [...],
  "labels": [...],
  "distractorLabels": [...],
  "mechanics": [{ "type": "...", "config": {...}, "scoring": {...}, "feedback": {...} }],
  "animationCues": {...},
  "theme": {...},
  "hierarchy": {...},
  "totalMaxScore": 100,
  "sequenceConfig": {...},    // promoted from first mechanic
  "sortingConfig": {...},      // promoted from first mechanic
  ... etc
}
```

**Multi-scene** (`is_multi_scene: true`):
```json
{
  "templateType": "INTERACTIVE_DIAGRAM",
  "is_multi_scene": true,
  "game_sequence": {
    "scenes": [GameScene, GameScene, ...],
    "total_max_score": 200,
    ...
  },
  // Root-level fields from first scene for backward compat
  "diagram": {...},
  "zones": [...],
  "labels": [...],
  "mechanics": [...],
  ...
}
```

---

## 3. Per-Mechanic Config Assembly

For each of the 10 mechanic types, here is what the assembler populates, what frontend expects, and gaps.

### 3.1 drag_drop

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `dragDropConfig` | Yes (L843-857) | Defaults + `mech_cfg` | Always populated for drag_drop type |
| `zones` | Yes | Merged from assets + specs | Core data |
| `labels` | Yes | Built from zones | Core data |
| `distractorLabels` | Yes | From design.distractor_labels | Separate list |
| `leaderLineAnchors` | **NO** | - | Frontend `DragDropConfig` has anchor fields but assembler never creates LeaderLineAnchor entries |

**Bug B-DD1:** `dragDropConfig` uses `if mech_type == "drag_drop":` (line 843) instead of `elif`, meaning it runs AFTER the `elif` chain for other mechanics. If a scene has both drag_drop AND another mechanic, the drag_drop block always runs for the drag_drop mechanic. This is correct but subtle - it's the only mechanic using `if` instead of `elif`.

### 3.2 click_to_identify

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `clickToIdentifyConfig` | Yes (L651-659) | Defaults + `mech_cfg` | |
| `identificationPrompts` | Yes (L618-649) | From config prompts or auto-generated | Correctly generates `{zoneId, prompt, order}` |

**Gap:** `clickToIdentifyConfig` backend uses `highlightOnHover` (camelCase, L653) but frontend `ClickToIdentifyConfig` type does NOT have `highlightOnHover` - it has `magnificationEnabled`, `exploreModeEnabled`, etc. The `highlightOnHover` field is silently dropped.

### 3.3 trace_path

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `tracePathConfig` | Yes (L603-613) | From config or defaults | |
| `paths` | Yes (L588-601) | Built from waypoints | Correctly produces `{id, waypoints: [{zoneId, order}], description, requiresOrder}` |

**Bug B-TP1:** `tracePathConfig.particleSpeed` is set to `mech_cfg.get("particle_speed", 1.0)` (line 607) - a float. But the frontend `TracePathConfig.particleSpeed` expects `'slow' | 'medium' | 'fast'` - a string enum. **Type mismatch will cause rendering issues.**

### 3.4 sequencing

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `sequenceConfig` | Yes (L663-680) | From config items + correct_order | |

Frontend reads: `sequenceConfig.items` (SequenceConfigItem[]), `sequenceConfig.correctOrder` (string[]).

**Gap:** Backend `SequenceDesign.items` are `SequenceItem` objects with `{id, text, description, image, icon, category, is_distractor, order_index}`. The assembler passes them through RAW via `mech_cfg.get("items", [])` (L664). These arrive as dicts with snake_case fields. Frontend `SequenceConfigItem` expects `order_index` (matching), `is_distractor` (matching). No conversion needed for core fields. **OK for now but fragile.**

### 3.5 description_matching

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `descriptionMatchingConfig` | Yes (L684-717) | From config descriptions converted to `{zoneId: description}` dict | |

**Bug B-DM1:** The `descriptions` dict uses zone IDs as keys (L700-701). But `zone_by_label` maps label TEXT to zone ID (L428). If the upstream `desc_item` has `label: "Petal"` and the zone ID is `zone_1_petal`, the mapping works. But if the label text doesn't exactly match (case, plural), the zone_id lookup via `zone_by_label.get(lbl, "")` (L698) may silently fail, producing an empty key. The descriptions then get dropped because the `if z_id and desc_text:` check (L700) filters them out.

**Note:** The assembler uses `_build_zone_lookup` for zone matching but does NOT use this normalized lookup when building description_matching descriptions. It uses the simpler `zone_by_label` dict which is case-sensitive.

### 3.6 sorting_categories

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `sortingConfig` | Yes (L721-772) | Categories + items normalized | |

Frontend expects: `SortingItem.correctCategoryId` (string, required), `SortingItem.correct_category_ids` (string[], optional).

**The assembler correctly normalizes both fields** (L742-756), supporting both singular and list forms.

**Gap:** Backend `SortingCategoryDesign` has `name` field, assembler maps it to `label` (L731). Frontend `SortingCategory` expects `label`. This mapping is correct.

**Bug B-SC1:** The `containerStyle` default is `"card"` (L770) but frontend `SortingConfig.container_style` expects `'bucket' | 'labeled_bin' | 'circle' | 'cell' | 'column'`. `"card"` is not a valid value. It will be silently ignored by strict frontend code but could cause fallback issues.

### 3.7 memory_match

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `memoryMatchConfig` | Yes (L776-805) | Pairs normalized to `{id, front, back, frontType, backType, explanation, category}` | |

Frontend expects: `MemoryMatchPair.front` (string), `MemoryMatchPair.back` (string).

Backend `MemoryPairDesign` has `term` and `definition`. The assembler correctly maps `term → front`, `definition → back` (L784-785).

**Bug B-MM1:** `gridSize` is passed through as-is from `mech_cfg.get("grid_size")` (L794). Backend `MemoryMatchDesign.grid_size` is a string like `"4x3"`, but frontend `MemoryMatchConfig.gridSize` expects `[number, number]` (a 2-element array). **Type mismatch will crash the frontend if it tries to destructure gridSize.**

### 3.8 branching_scenario

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `branchingConfig` | Yes (L808-821) | Nodes passed through + config fields | |

Frontend expects: `DecisionNode.question` (string), `DecisionOption.nextNodeId` (string|null).

Backend `BranchingNodeDesign` has `prompt` (not `question`), `choices` (not `options`). The backend schema coerces `question → prompt` and `options → choices` via `_coerce()`.

**Bug B-BR1:** The assembler passes `nodes` through directly from `mech_cfg.get("nodes", [])` (L809). These nodes come from `BranchingNodeDesign` which uses `prompt` (not `question`), `choices` (not `options`), and `BranchingChoiceDesign` which uses `text`, `next_node_id` (snake_case, not camelCase `nextNodeId`), `is_correct` (not `isCorrect`). Frontend `DecisionNode` expects `question`, `options` (with `nextNodeId`, `isCorrect`). **No field name conversion happens.** The branching nodes arrive at the frontend with wrong field names.

**This is a CRITICAL bug.** The frontend `BranchingScenario` component (via registry `extractProps`) reads `config.nodes` and expects `node.question` and `option.nextNodeId`. If the backend sends `node.prompt` and `choice.next_node_id`, the component will see `undefined` for those fields.

### 3.9 compare_contrast

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `compareConfig` | Yes (L824-840) | Expected categories + config fields | |

Frontend expects: `CompareConfig.diagramA` (CompareDiagram), `CompareConfig.diagramB` (CompareDiagram), `CompareConfig.expectedCategories` (Record<string, category>).

**Bug B-CC1:** The assembler does NOT build `diagramA` and `diagramB` objects. It only sets `expectedCategories`, `highlightMatching`, `instructions`, and misc config fields (L825-840). The frontend `CompareConfig` requires `diagramA: CompareDiagram` and `diagramB: CompareDiagram` as mandatory fields (the interface definition at `types.ts:493-496` makes them required). The frontend registry's `extractProps` (mechanicRegistry.ts:452) checks `if (config && config.diagramA && config.diagramB)` and falls back to a stub if missing. **The assembler NEVER populates diagramA/diagramB, so compare_contrast ALWAYS falls through to the legacy stub fallback.** This stub uses the same diagram for both A and B, which defeats the purpose.

### 3.10 timed_challenge

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `timedChallengeWrappedMode` | **NO** | - | Never populated |
| `timeLimitSeconds` | **NO** | - | Never populated |

**Bug B-TC1:** The assembler has NO `elif mech_type == "timed_challenge":` block. There is no handling of `timed_challenge` at all. The frontend expects `timedChallengeWrappedMode` and `timeLimitSeconds` on the blueprint. Neither is ever set.

### 3.11 hierarchical

| Field | Populated? | Source | Notes |
|---|---|---|---|
| `hierarchy` | Yes (L251-265) | From design.labels.hierarchy | Set at blueprint root level |
| `zoneGroups` | **NO** | - | Never built from hierarchy data |

**Bug B-HI1:** Frontend `InteractiveDiagramBlueprint.zoneGroups?: ZoneGroup[]` is what the hierarchical mechanic component reads (mechanicRegistry.ts:555). The assembler builds `hierarchy` dict with `{enabled, strategy, groups}` but NEVER converts it to `ZoneGroup[]` format (`{id, parentZoneId, childZoneIds, revealTrigger}`). The frontend component will see `zoneGroups: undefined` and produce an empty array.

---

## 4. Multi-Scene Assembly

### 4.1 Scene Indexing

Scenes are indexed by `scene_number` (1-based integer from `SceneDesign.scene_number`). The assembler:
1. Iterates `design.scenes` in order
2. Looks up `scene_specs_map[scene_number]` and `interaction_specs_map[scene_number]`
3. Looks up `asset_scenes[scene_number]` from `generated_assets_v3.scenes`
4. Builds `game_scenes` list (0-indexed by iteration order)

**Bug B-MS1:** Scene number is used as `int(sn_key)` from the generated_assets dict (L283). If the asset generator produces string keys like `"scene_1"` instead of `"1"`, `int("scene_1")` will raise `ValueError`. The code catches this (L284), but the scene's assets will be silently lost.

### 4.2 Per-Scene Config Propagation

Per-mechanic config keys are promoted in two places:
1. **Scene level** (L1052-1060): Each mechanic's config keys are promoted to the scene dict (first one wins)
2. **Root level** (L1095-1103 for multi, L1132-1141 for single): First scene's first mechanic's config keys are promoted to blueprint root

This means:
- For **multi-scene games**, each GameScene has its own config keys. The frontend `sceneToBlueprint()` (sceneManager.ts:131-140) reads these per-scene configs correctly.
- The **root-level** configs only reflect the FIRST scene's FIRST mechanic. If scene 2 has a different mechanic type, its config is NOT at root level.

**This design is correct for multi-scene** because the frontend uses `sceneToBlueprint()` to extract per-scene configs when advancing scenes. However, it breaks if the game is single-scene with multiple mechanics (multi-mode) because only the FIRST mechanic's config is at root level.

### 4.3 Missing `tasks` Field on GameScene

**Bug B-MS2:** The frontend `GameScene` interface (`types.ts:841`) requires `tasks: SceneTask[]`. The assembler NEVER creates `tasks` on game_scene objects. The `sceneToBlueprint()` function (sceneManager.ts:69) handles this by creating an implicit task if `scene.tasks` is empty/undefined, so this works but means tasks are always implicit. If the upstream design has explicit tasks with different zone subsets, they are lost.

### 4.4 Diagram Object Construction

The assembler constructs `diagram` objects (L980-988) as:
```json
{
  "assetUrl": "diagram_image_url",
  "width": 800,
  "height": 600,
  "zones": [zone_dicts...]
}
```

**Bug B-DG1:** The frontend `InteractiveDiagramBlueprint.diagram` requires `assetPrompt: string` (types.ts:675). The assembler never sets `assetPrompt` on the diagram object. The frontend `sceneToBlueprint()` uses `scene.diagram.assetPrompt || scene.title` as fallback (sceneManager.ts:110), so it degrades gracefully. But Pydantic validation on `InteractiveDiagramDiagram` (interactive_diagram.py:807) will fail if this dict is ever validated against the model since `assetPrompt` is required.

---

## 5. Known Data Loss Points

### 5.1 Scoring Data

**Flow:** `interaction_specs_v3[scene].scoring` (list of per-mechanic dicts) → `scoring_by_type` lookup → `mech_entry["scoring"]` → `fe_mech["scoring"]` → `game_scene.mechanics[].scoring`

The current flow correctly indexes scoring by `mechanic_type` (L466-479). The known lists-vs-dicts issue was previously fixed.

**Remaining bug B-SC2:** When NO scoring data is found for a mechanic type AND the design mechanic also has no scoring, `mech_scoring` remains `None` (L521-524). The mechanic dict has `"scoring": None`. The repair step later adds default scoring (L1842-1861), but ONLY if `repair_blueprint_impl` is called. In the ReAct path, this depends on the LLM calling repair. **Scoring can be permanently None for mechanics that neither the interaction_designer nor the design supplied scoring for.**

### 5.2 Feedback Data

Same flow as scoring. Same issue: feedback can be permanently None.

### 5.3 Mechanic Animations

`MechanicDesign.animations` (`MechanicAnimations` model with `on_correct`, `on_incorrect`, `on_completion`, `on_hover`, `on_drag`) is NEVER read during assembly. The assembler checks for `mech.get("animations")` (L1006-1007) on the `fe_mech` being built, but the input `mech` from `scene_design.mechanics` is never queried for its `animations` field.

**Bug B-AN1:** Mechanic-level animations from `MechanicDesign.animations` are completely dropped. Only the global `animationCues` from interaction_specs are preserved.

### 5.4 Zone Hints and Descriptions

`ZoneSpec.hint_progression` (list of progressive hints) is read from scene_spec zones and stored on zone dicts (L398-399). But the frontend `Zone` interface has `hint?: string` (singular), not `hint_progression: string[]`. The backend puts a list where the frontend expects a string.

**Bug B-ZH1:** `zone_entry["hint_progression"]` is a `List[str]` but frontend `Zone.hint` expects a single string. These hints are silently lost because the frontend reads `zone.hint` (which is never set) rather than `zone.hint_progression`.

### 5.5 Zone `group_only` and `parent_zone_id` Fields

The assembler sets `group_only: True/False` and `parent_zone_id` on zone dicts (L342-343, L390-391). The frontend `Zone` interface does NOT have `group_only` or `parent_zone_id` fields. It has `parentZoneId` (camelCase). The post-processing step `_postprocess_zones()` does NOT convert `parent_zone_id` to `parentZoneId`.

**Bug B-ZP1:** `parent_zone_id` (snake_case) is never converted to `parentZoneId` (camelCase) that the frontend expects. Hierarchical parent-child relationships are broken in the output.

### 5.6 Scene `narrative_intro` and `learning_goal`

These are set on game_scene dicts (L883-886) but as snake_case. Frontend `GameScene` has `narrative_intro` (snake_case), so this matches.

---

## 6. Zone/Label Format Conversion

### 6.1 Zone Coordinate Pipeline

```
Raw Zone Detection Output (various formats)
    ↓ _normalize_coordinates() → {points: [[x,y],...]} or {x, y, radius}
    ↓ stored as zone["coordinates"]
    ↓ _postprocess_zones() → flattens to zone["points"], zone["x"], zone["y"], zone["center"]
    ↓ Frontend reads zone.points, zone.x, zone.y, zone.center, zone.shape
```

The `_postprocess_zones()` function (L100-150) correctly:
- Extracts `points` from `coordinates.points`
- Extracts `x`, `y`, `radius` from `coordinates`
- Auto-detects `shape` as "polygon" when 3+ points exist
- Computes `center` from polygon centroid
- Falls back: derives `x`/`y` from `center` if missing

**This part is solid.** The coordinate conversion handles all known formats correctly.

### 6.2 Zone Shape Auto-Detection

**Bug B-ZS1:** At L124-127, if `points` has 3+ entries, shape is forced to `"polygon"`. But there's no check for the `"rect"` shape. If the upstream provides `shape: "rect"`, it gets overwritten to `"polygon"` if any points are present. This is likely OK since rect zones are rare, but it's worth noting.

### 6.3 Label Format

Labels are built at L427-435 with `{id, text, correctZoneId}`. This matches frontend `Label` interface exactly. Distractor labels are built separately at L438-447 with `{id, text, explanation}`. This matches frontend `DistractorLabel`.

**Label format is correct.**

### 6.4 Mechanic Key Field Names (Backend → Frontend)

The assembler produces mechanic dicts with fields like:
- `mechanicId` (camelCase, L562) but frontend `Mechanic` does NOT have mechanicId
- `mechanicType` (camelCase, L563) → frontend reads `type` (L995)
- `interactionMode` (camelCase, L564) → frontend doesn't read this
- `zoneLabels` (camelCase, L566) → frontend doesn't have this on Mechanic

The conversion at L992-1015 correctly extracts `type` from `mechanicType`, and forwards `config`, `scoring`, `feedback`, `animations`, and all per-mechanic config keys.

---

## 7. Gap Analysis: Frontend Expects vs Assembler Produces

### 7.1 InteractiveDiagramBlueprint (Single Scene)

| Frontend Field | Required | Assembler Sets | Status |
|---|---|---|---|
| `templateType` | Yes | Yes (L1106/1144) | OK |
| `title` | Yes | Yes | OK |
| `narrativeIntro` | Yes | Yes | OK |
| `diagram` | Yes | Yes | OK (but missing `assetPrompt` - see B-DG1) |
| `labels` | Yes | Yes | OK |
| `distractorLabels` | Optional | Yes | OK |
| `tasks` | Yes | **NO** | **BUG B-TK1** |
| `animationCues` | Yes | Yes | OK |
| `mechanics` | Optional | Yes | OK |
| `interactionMode` | Optional | Multi only (L1117) | Partial |
| `modeTransitions` | Optional | **NO** | **BUG B-MT1** - mode_transitions from interaction_spec are on scenes but not promoted to root for single-scene |
| `zoneGroups` | Optional | **NO** | **BUG B-HI1** (see above) |
| `identificationPrompts` | Optional | Via promoted config | OK |
| `paths` | Optional | Via promoted config | OK |
| `sequenceConfig` | Optional | Via promoted config | OK |
| `sortingConfig` | Optional | Via promoted config | OK |
| `memoryMatchConfig` | Optional | Via promoted config | OK |
| `branchingConfig` | Optional | Via promoted config | OK |
| `compareConfig` | Optional | Via promoted config | **INCOMPLETE (B-CC1)** |
| `descriptionMatchingConfig` | Optional | Via promoted config | OK |
| `clickToIdentifyConfig` | Optional | Via promoted config | OK |
| `tracePathConfig` | Optional | Via promoted config | OK |
| `dragDropConfig` | Optional | Via promoted config | OK |
| `timedChallengeWrappedMode` | Optional | **NO** | **BUG B-TC1** |
| `timeLimitSeconds` | Optional | **NO** | **BUG B-TC1** |
| `scoringStrategy` | Optional | `"standard"` (string) for single (L1156) | **BUG B-SS1** - frontend expects object `{type, base_points_per_zone, ...}` but assembler sets string |
| `hints` | Optional | **NO** | Not assembled |
| `feedbackMessages` | Optional | **NO** | Not assembled |
| `temporalConstraints` | Optional | **NO** | Not assembled from design.temporal |
| `motionPaths` | Optional | **NO** | Not assembled |
| `revealOrder` | Optional | **NO** | Not assembled |
| `leaderLineAnchors` | Optional | **NO** | Not assembled |

### 7.2 GameScene (Multi-Scene)

| Frontend Field | Required | Assembler Sets | Status |
|---|---|---|---|
| `scene_id` | Yes | Yes | OK |
| `scene_number` | Yes | Yes | OK |
| `title` | Yes | Yes | OK |
| `narrative_intro` | Yes | Yes | OK |
| `diagram` | Yes | Yes | OK |
| `zones` | Yes | Yes | OK |
| `labels` | Yes | Yes | OK |
| `max_score` | Yes | Yes (computed L1018-1027) | OK |
| `tasks` | Yes | **NO** | **BUG B-MS2** |
| `mechanics` | Optional | Yes | OK |
| `interaction_mode` | Optional | Yes (L1045) | OK |
| `mode_transitions` | Optional | Yes (L1046) | OK |
| `distractor_labels` | Optional | Yes (L1047) | OK |
| Per-mechanic configs | Optional | Yes (promoted from mechanics, L1052-1060) | OK |

### 7.3 Key Missing Fields Summary

**BUG B-TK1:** `tasks` is a required field on `InteractiveDiagramBlueprint` (types.ts:684). The assembler NEVER creates a `tasks` array. The Pydantic schema `InteractiveDiagramBlueprint` (interactive_diagram.py:831) also lists `tasks: List[InteractiveDiagramTask]` as required. For single-scene games, this will fail Pydantic validation. The frontend code doesn't seem to READ `blueprint.tasks` directly (it uses mechanics/zones/labels instead), so this is a schema violation that doesn't crash the frontend but would fail any strict validation.

**BUG B-MT1:** For single-scene games, `modeTransitions` is never set at blueprint root level. The mode_transitions from interaction_spec are stored on scene dicts (L878) and propagated to game_scene (L1046), but NOT promoted to root level for single-scene blueprints (L1143-1160). Frontend multi-mode transition logic reads `blueprint.modeTransitions`.

**BUG B-SS1:** `scoringStrategy` is set to the string `"standard"` (L1156) for single-scene blueprints. Frontend `InteractiveDiagramBlueprint.scoringStrategy` expects an object `{type: string; base_points_per_zone: number; ...}`. String value will cause runtime errors if any code accesses `.type` on it.

---

## 8. mechanic_contracts.py Usage

**mechanic_contracts.py is COMPLETELY UNUSED by the blueprint assembler.**

Grep confirms zero imports of `mechanic_contracts` in either `blueprint_assembler_v3.py` or `blueprint_assembler_tools.py`. The file was found only referenced in a planning document (`2026-02-12-this-session-is-being-continued-from-a-previous-co.txt`).

The contracts registry defines:
- `frontend_config_key`: e.g., `"dragDropConfig"`, `"sequenceConfig"`, etc.
- `blueprint_assembler.required_output_fields`: What each mechanic needs in the blueprint

This information is currently hardcoded in the assembler via 10 `elif` blocks (assembly) and 10 more `if` blocks (repair). The contracts registry was designed to replace these hardcoded blocks but was never integrated.

**Impact:** Any new mechanic type requires modifying 3 places: `assemble_blueprint_impl()`, `repair_blueprint_impl()`, and `validate_blueprint_impl()`, instead of just adding a contract entry.

---

## 9. Bug Registry

### Critical (will cause exceptions or broken games)

| ID | File:Line | Description |
|---|---|---|
| **B-BR1** | `blueprint_assembler_tools.py:809` | Branching nodes pass through with backend field names (`prompt`, `choices`, `next_node_id`, `is_correct`) instead of frontend field names (`question`, `options`, `nextNodeId`, `isCorrect`). Frontend will see `undefined` for question text and option links. |
| **B-CC1** | `blueprint_assembler_tools.py:824-840` | `compareConfig` never includes `diagramA`/`diagramB` objects. Frontend requires them. Always falls through to broken legacy stub. |
| **B-MM1** | `blueprint_assembler_tools.py:794` | `gridSize` passed as string `"4x3"` but frontend expects `[number, number]` array. Will crash on destructure. |
| **B-TP1** | `blueprint_assembler_tools.py:607` | `particleSpeed` set as float `1.0` but frontend expects string enum `'slow'|'medium'|'fast'`. |
| **B-SS1** | `blueprint_assembler_tools.py:1156` | `scoringStrategy` set to string `"standard"` but frontend expects object `{type, base_points_per_zone, ...}`. |
| **B-TC1** | `blueprint_assembler_tools.py` (missing) | No handling for `timed_challenge` mechanic. `timedChallengeWrappedMode` and `timeLimitSeconds` never set. |
| **B-HI1** | `blueprint_assembler_tools.py` (missing) | Hierarchy data never converted to `zoneGroups: ZoneGroup[]` format that frontend hierarchical component reads. |
| **B-ZP1** | `blueprint_assembler_tools.py:342,391` | `parent_zone_id` (snake_case) never converted to `parentZoneId` (camelCase). Hierarchical parent-child relationships broken. |

### High (data loss or degraded functionality)

| ID | File:Line | Description |
|---|---|---|
| **B-AN1** | `blueprint_assembler_tools.py:482-569` | `MechanicDesign.animations` (per-mechanic animation specs) are never read. Only global `animationCues` preserved. |
| **B-TK1** | `blueprint_assembler_tools.py:1143` | `tasks` field never created. Required by both Pydantic schema and frontend TS type. |
| **B-MT1** | `blueprint_assembler_tools.py:1143-1160` | `modeTransitions` never promoted to root for single-scene blueprints. Multi-mode transitions won't fire. |
| **B-DG1** | `blueprint_assembler_tools.py:981-988` | `diagram.assetPrompt` never set. Required by Pydantic InteractiveDiagramDiagram. |
| **B-MS2** | `blueprint_assembler_tools.py:1034-1048` | `GameScene.tasks` never populated. Frontend creates implicit tasks, losing any explicit task design from upstream. |
| **B-ZH1** | `blueprint_assembler_tools.py:398-399` | `hint_progression` (list) stored but frontend expects `hint` (string). Hints silently lost. |
| **B-SC2** | `blueprint_assembler_tools.py:510-524` | Scoring can remain `None` for mechanics without upstream scoring data, unless repair is called. |
| **B-SC1** | `blueprint_assembler_tools.py:770` | `containerStyle` default `"card"` is not a valid frontend enum value. Should be `"bucket"`. |
| **B-DM1** | `blueprint_assembler_tools.py:696-701` | Description matching zone lookup uses case-sensitive `zone_by_label` instead of fuzzy `_build_zone_lookup`. Descriptions may be silently dropped. |
| **B-SUBMIT1** | `blueprint_assembler_tools.py:1920-1922` | `submit_blueprint_impl` reads `blueprint.get("scenes", [])` for validation but multi-scene blueprints store scenes at `game_sequence.scenes`, not `blueprint.scenes`. Submit validation skips all scenes for multi-scene games. |

### Medium (cosmetic or edge cases)

| ID | File:Line | Description |
|---|---|---|
| **B-DUP1** | `blueprint_assembler_tools.py:586-860 & 1618-1840` | ~600 lines of duplicated mechanic config assembly logic between `assemble_blueprint_impl` and `repair_blueprint_impl`. Drift risk high. |
| **B-TMPL1** | `blueprint_assembler_tools.py:1971` | `templateType` check compares to both `"INTERACTIVE_DIAGRAM"` and `"INTERACTIVE_DIAGRAM"` (same value twice). Dead code. |
| **B-TOT1** | `blueprint_assembler_tools.py:1122-1123` | `totalMaxScore` (camelCase) used as key. Frontend expects `total_max_score` (snake_case) in some places and `totalMaxScore` in others. Inconsistent. |
| **B-LEGACY1** | `blueprint_assembler_v3.py:42-366` | Legacy `assemble_blueprint()` function is a full parallel assembler with different logic than `assemble_blueprint_impl()`. Used by non-V3 paths. The two will drift. |
| **B-IDL1** | `blueprint_assembler_v3.py:153-157` | Legacy assembler uses `correct_zone_id` (snake_case) for labels via `IDLabel` schema (blueprint_schemas.py:696). But frontend `Label` expects `correctZoneId` (camelCase). |
| **B-INST1** | `blueprint_assembler_v3.py:610-617` | `_agent_instance` is a module-level global singleton. If `model` parameter changes between runs, the old model is kept because the instance already exists. |
| **B-ZS1** | `blueprint_assembler_tools.py:124-127` | Polygon shape auto-detection overwrites `"rect"` shapes. Minor since rect is uncommon. |
| **B-SCORE1** | `blueprint_assembler_tools.py:1877-1890` | Score recalculation in repair reads from `blueprint.get("scenes", [])` (wrong path for multi-scene). Falls through to label-count fallback, which reads from `scenes` too. For multi-scene, total_max_score is never recalculated from actual mechanic scores. |

---

## 10. Proposed Fixes with Priority

### Priority 1: Critical (blocks entire mechanic types)

**Fix 1 — B-BR1: Branching node field name conversion** (Est: ~40 lines)
- File: `blueprint_assembler_tools.py`, ~line 808
- Add conversion: `prompt → question`, `choices → options`, `next_node_id → nextNodeId`, `is_correct → isCorrect`, `consequence_text → consequence`
- Must recurse into `choices/options` list to convert each choice's fields
- Also needed in `repair_blueprint_impl` branching block (~L1794)

**Fix 2 — B-CC1: Build diagramA/diagramB for compare_contrast** (Est: ~30 lines)
- File: `blueprint_assembler_tools.py`, ~line 824
- Read `mech_cfg.get("subjects", [])` for diagram names
- Read scene visual spec's `comparison` field for diagram descriptions
- Build `diagramA: {id, name, imageUrl, zones: [...]}` and `diagramB` objects
- Source zone lists from `mech_cfg.get("diagram_a_zones", [])` and `diagram_b_zones`
- Source image URLs from asset data (if asset generator supports dual images)

**Fix 3 — B-MM1: Convert gridSize format** (Est: ~5 lines)
- File: `blueprint_assembler_tools.py`, line 794
- Convert string `"4x3"` to `[4, 3]` array: `gridSize = [int(x) for x in grid_str.split("x")]`

**Fix 4 — B-TP1: Fix particleSpeed type** (Est: ~3 lines)
- File: `blueprint_assembler_tools.py`, line 607
- Map float/string to valid enum: `particleSpeed = mech_cfg.get("particle_speed", "medium")`
- Ensure it's one of `"slow"`, `"medium"`, `"fast"`

**Fix 5 — B-SS1: Fix scoringStrategy type** (Est: ~10 lines)
- File: `blueprint_assembler_tools.py`, line 1156
- Replace string `"standard"` with proper object:
  ```python
  "scoringStrategy": {"type": "per_correct", "base_points_per_zone": 10, "max_score": total_max_score}
  ```

**Fix 6 — B-TC1: Add timed_challenge handling** (Est: ~15 lines)
- File: `blueprint_assembler_tools.py`, after line 840
- Read `timed_config.wrapped_mechanic_type` and `timed_config.time_limit_seconds`
- Set `timedChallengeWrappedMode` and `timeLimitSeconds` on mechanic entry
- Promote to blueprint root

**Fix 7 — B-HI1 + B-ZP1: Build zoneGroups + fix parentZoneId** (Est: ~25 lines)
- File: `blueprint_assembler_tools.py`, after zone building
- Convert `hierarchy.groups` to `ZoneGroup[]` format
- Convert `parent_zone_id` → `parentZoneId` on all zone dicts during `_postprocess_zones()`

### Priority 2: High (data loss, degraded features)

**Fix 8 — B-SUBMIT1: Fix multi-scene submit validation** (Est: ~5 lines)
- File: `blueprint_assembler_tools.py`, line 1920
- Add: `if not scenes and blueprint.get("is_multi_scene"): scenes = blueprint.get("game_sequence", {}).get("scenes", [])`

**Fix 9 — B-MT1: Promote modeTransitions for single-scene** (Est: ~5 lines)
- File: `blueprint_assembler_tools.py`, ~line 1143
- Add `"modeTransitions": single.get("mode_transitions", [])` to single-scene blueprint

**Fix 10 — B-TK1: Create tasks array** (Est: ~15 lines)
- File: `blueprint_assembler_tools.py`, in both single and multi-scene branches
- Build `tasks: [{id, type: "label_diagram", questionText: narrativeIntro, requiredToProceed: true}]`

**Fix 11 — B-DG1: Set diagram.assetPrompt** (Est: ~3 lines)
- File: `blueprint_assembler_tools.py`, line 982
- Add `diagram_obj["assetPrompt"] = scene_design.get("visual", {}).get("description", scene_title)`

**Fix 12 — B-AN1: Forward mechanic animations** (Est: ~10 lines)
- File: `blueprint_assembler_tools.py`, ~line 500
- Read `mech.get("animations")` from design mechanic and forward to mech_entry

**Fix 13 — B-ZH1: Convert hint_progression to hint** (Est: ~5 lines)
- File: `blueprint_assembler_tools.py`, line 398
- Add: `if hint_list: zone_entry["hint"] = hint_list[0]` (use first hint)

**Fix 14 — B-DM1: Use fuzzy zone lookup for descriptions** (Est: ~5 lines)
- File: `blueprint_assembler_tools.py`, ~line 696
- Replace `zone_by_label.get(lbl, "")` with fuzzy lookup: `detected_zone_map.get(_normalize_label(lbl), {}).get("id", "")`

**Fix 15 — B-SC1: Fix containerStyle default** (Est: ~1 line)
- File: `blueprint_assembler_tools.py`, line 770
- Change `"card"` to `"bucket"`

### Priority 3: Architecture (reduces maintenance burden)

**Fix 16 — Integrate mechanic_contracts.py** (Est: ~200 lines)
- File: `blueprint_assembler_tools.py`
- Replace 10 `elif` blocks with a loop over `MECHANIC_CONTRACTS`
- Use `contract.frontend_config_key` to determine output field name
- Use `contract.blueprint_assembler.required_output_fields` for validation
- Eliminate duplication between assembly and repair

**Fix 17 — B-DUP1: Extract shared config builder** (Est: ~100 lines)
- File: `blueprint_assembler_tools.py`
- Create `_build_mechanic_frontend_config(mech_type, mech_cfg, ...)` shared function
- Call from both `assemble_blueprint_impl` and `repair_blueprint_impl`

**Fix 18 — B-SCORE1: Fix multi-scene score recalculation in repair** (Est: ~10 lines)
- File: `blueprint_assembler_tools.py`, line 1877
- Handle `game_sequence.scenes` path in score recalculation

---

## Appendix A: File Reference

| File | Path | Lines | Purpose |
|---|---|---|---|
| Blueprint Assembler V3 | `backend/app/agents/blueprint_assembler_v3.py` | 768 | ReAct agent + deterministic agent wrapper |
| Blueprint Assembler Tools | `backend/app/tools/blueprint_assembler_tools.py` | 2099 | 4 tools: assemble, validate, repair, submit |
| Interactive Diagram Schema | `backend/app/agents/schemas/interactive_diagram.py` | 1495 | Frontend-facing Pydantic blueprint schema |
| Game Design V3 Schema | `backend/app/agents/schemas/game_design_v3.py` | 1290 | Upstream design schema (14 dimensions) |
| Blueprint Schemas | `backend/app/agents/schemas/blueprint_schemas.py` | ~800 | IDScene/IDZone/IDLabel/IDMechanic Pydantic models |
| Mechanic Contracts | `backend/app/config/mechanic_contracts.py` | 458 | Contract registry (UNUSED by assembler) |
| Blueprint Generator | `backend/app/agents/blueprint_generator.py` | 900+ | Non-V3 LLM-based blueprint generator |
| Frontend Types | `frontend/src/components/templates/InteractiveDiagramGame/types.ts` | 1169 | TypeScript type definitions |
| Mechanic Registry | `frontend/src/components/templates/InteractiveDiagramGame/mechanicRegistry.ts` | 616 | Frontend component registry |
| Scene Manager | `frontend/src/components/templates/InteractiveDiagramGame/engine/sceneManager.ts` | 146 | `sceneToBlueprint()` conversion |
| Extract Task Config | `frontend/src/components/templates/InteractiveDiagramGame/utils/extractTaskConfig.ts` | 44 | `extractMechanicConfig()` utility |

## Appendix B: Two Parallel Schema Hierarchies

The codebase has TWO different schema hierarchies for the same blueprint data:

**Hierarchy 1: `blueprint_schemas.py`** (used by legacy assembler in `blueprint_assembler_v3.py`)
- `InteractiveDiagramBlueprint` → `IDScene` → `IDZone`, `IDLabel`, `IDMechanic`
- Uses `snake_case` fields: `correct_zone_id`, `mechanic_type`, `parent_zone_id`
- `IDLabel.correct_zone_id` (not `correctZoneId`)

**Hierarchy 2: `interactive_diagram.py`** (used for Pydantic validation, matches frontend)
- `InteractiveDiagramBlueprint` → `InteractiveDiagramZone`, `InteractiveDiagramLabel`, `Mechanic`
- Uses `camelCase` fields: `correctZoneId`, `parentZoneId`
- Has all per-mechanic config types: `SequenceConfig`, `SortingConfig`, etc.

The V3 assembler tools (`blueprint_assembler_tools.py`) use NEITHER schema for output. They build raw dicts with a MIX of both conventions. This is the root cause of many field-naming bugs.

**Recommendation:** The assembler should validate its output against `interactive_diagram.py:InteractiveDiagramBlueprint` (hierarchy 2) before returning. This would catch all camelCase/snake_case mismatches at assembly time rather than at frontend render time.
