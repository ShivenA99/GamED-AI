# 06: V3 Asset Generation System Audit

## Executive Summary

The V3 asset generation system (`asset_generator_v3`) is a ReAct agent with 5 tools that handles image retrieval, diagram generation, zone detection, animation CSS, and asset submission. It works well for **drag_drop** mechanics but has significant gaps for all other mechanic types. The agent has no per-mechanic awareness: it generates images and zones but never produces mechanic-specific assets such as identification prompts, waypoints, sequence items, or functional descriptions. Validation at submission time checks only structural minimums (image exists, zones non-empty) and does not enforce per-mechanic completeness, meaning incomplete games are silently accepted.

**Key findings:**
- 1 of 5 mechanics (drag_drop) is fully supported by asset generation
- 4 of 5 mechanics are missing critical mechanic-specific assets
- Missing labels are logged as warnings, not errors -- incomplete games pass validation
- Silent coordinate fallback to (50,50) causes zones to stack at diagram center
- No per-mechanic asset spec is injected into the agent's system prompt
- Multi-scene coordination relies on heuristic tool-call ordering, not explicit scene assignment

---

## Current Flow Analysis

**Agent:** `asset_generator_v3` in `backend/app/agents/asset_generator_v3.py`
**Type:** ReAct agent (react_base.py)
**Config:** max_iterations=8, temperature=0.3, tool_timeout=120s

### Tool Inventory

| # | Tool | Purpose | Input | Output |
|---|------|---------|-------|--------|
| 1 | `search_diagram_image` | Web image retrieval | scene image_description | image_url, local_path |
| 2 | `generate_diagram_image` | AI diagram generation (Gemini Imagen) | description, style | local_path |
| 3 | `detect_zones` | Zone detection on image | image + expected_labels | zones[] with id, label, x, y, radius |
| 4 | `generate_animation_css` | CSS keyframes for feedback | animation spec | css_string |
| 5 | `submit_assets` | Validate and finalize | per-scene assets | accepted / rejected |

### Typical ReAct Loop

```
Iteration 1: search_diagram_image(scene_1 description)
Iteration 2: detect_zones(image, expected_labels)
Iteration 3: [optional] generate_animation_css(...)
Iteration 4: submit_assets(scene_1 assets)
  -- repeat for scene_2 if multi-scene --
Iteration 5-8: search/generate/detect/submit for scene_2
```

---

## Tool Deep Dive

### Tool 1: search_diagram_image

**Query construction:**
- Takes scene's `image_description`, enriches with `subject` + `domain`
- Calls `search_diagram_images_multi()` with up to 3 prioritized queries
- Scoring via `select_best_image_scored()` with educational bias

**Scoring modifiers:**

| Modifier | Score Impact |
|----------|-------------|
| Labeled diagram detected | +2.5 |
| Reliable sources (Wikimedia, Wikipedia, NIH, CDC, Khan Academy) | +3.0 |
| Stock image detected | -10.0 |
| Watermark detected | -5.0 |

**Retry behavior:**
- MAX_RETRIES=3 with exponential backoff
- Fallback: 2 generic queries if all primary queries fail
- If all retries exhausted: falls through to `generate_diagram_image`

### Tool 2: generate_diagram_image

- Uses Gemini Imagen API to generate a clean, unlabeled educational diagram
- Prompt emphasizes "NO TEXT LABELS" to produce a clean base image
- Saves output to `pipeline_outputs/v3_assets/{run_id}/`
- **No fallback if Gemini unavailable** -- returns `success=False`, cascading failure

### Tool 3: detect_zones

**Detection method priority chain:**

| Priority | Method | Output Shape | Notes |
|----------|--------|-------------|-------|
| 1 | gemini_sam3 | polygon | Best accuracy, requires SAM3 service |
| 2 | gemini | circle (x, y, radius) | Gemini vision API |
| 3 | qwen | per-label detection | **NOT in auto fallback chain** -- only reachable via explicit config |

**Post-processing:**
- `_normalize_zones_to_percent()` converts pixel coordinates to 0-100% scale
- Silent fallback to center `(50, 50)` for any missing or unparseable coordinates
- Returns zones with: `label`, `zone_id`, `x`, `y`, `radius`, `shape`, `confidence`

### Tool 4: generate_animation_css

- Generates CSS `@keyframes` for feedback effects (pulse, glow, shake, etc.)
- Optional tool -- agent may skip if not needed
- No validation of CSS output correctness

### Tool 5: submit_assets

**Current validation checks:**

| Check | Behavior on Failure |
|-------|---------------------|
| Image file exists | **REJECT** |
| Zones array non-empty | **REJECT** |
| Each zone has id, label, x, y | **REJECT** |
| Expected labels not all found in zones | **WARNING only** (accepted) |
| Per-mechanic assets present | **NOT CHECKED** |
| Coordinate range validity | **NOT CHECKED** |
| Zone-label deduplication | **NOT CHECKED** |

---

## Per-Mechanic Gap Analysis

### Support Matrix

| Mechanic | Image | Zones | Mechanic-Specific Assets | Generation Status |
|----------|-------|-------|--------------------------|-------------------|
| drag_drop | Y | Y | (none needed beyond zones) | **FULLY SUPPORTED** |
| click_to_identify | Y | Y | identification_prompts, misconception_feedback | **MISSING ASSETS** |
| trace_path | Y | ~ | waypoints, path_connections, correct_path_sequence | **MISSING ASSETS** |
| sequencing | Y (optional) | N/A | steps, distractors, correct_order | **MISSING ASSETS** |
| description_matching | Y | Y | zone_descriptions, incorrect_descriptions | **MISSING ASSETS** |

### Detailed Per-Mechanic Gaps

#### drag_drop -- FULLY SUPPORTED

All required assets are produced by the existing tool chain:
- Image retrieved or generated
- Zones detected with labels, coordinates, and radii
- Zone-to-label mapping established
- No additional mechanic-specific assets needed

#### click_to_identify -- MISSING ASSETS

| Required Asset | Description | Generated? |
|----------------|-------------|------------|
| `identification_prompts` | Per-zone prompts ("Click on the Right Atrium") | NO |
| `misconception_feedback` | Per-zone wrong-answer explanations | NO |
| `selection_mode` | "sequential" or "any_order" | NO (hardcoded downstream) |

The agent produces images and zones but never generates the prompt text that drives the click-to-identify interaction. The frontend `HotspotManager` component expects `identificationPrompts[]` in the blueprint, which must contain `targetZoneId`, `promptText`, and optionally `hintText`.

#### trace_path -- MISSING ASSETS

| Required Asset | Description | Generated? |
|----------------|-------------|------------|
| `waypoints` | Ordered `[x, y]` coordinate pairs along the path | NO |
| `path_connections` | `start_zone` to `end_zone` directed edges | NO |
| `correct_path_sequence` | Ordered list of `zone_id`s for validation | NO |
| `flow_direction` | "forward", "cyclic", "branching" | NO |

The zone detector finds labeled structures but has no concept of spatial ordering or flow between zones. Trace-path requires knowledge of the biological/physical process flow (e.g., blood flow: right atrium -> right ventricle -> lungs -> left atrium -> left ventricle), which must come from domain knowledge but is never consumed by asset_generator_v3.

#### sequencing -- MISSING ASSETS

| Required Asset | Description | Generated? |
|----------------|-------------|------------|
| `steps` | `{id, text, orderIndex, description}` items | NO |
| `distractors` | Plausible-but-wrong items | NO |
| `correct_order` | Ordered list of step IDs | NO |
| `sequence_type` | "linear", "cyclic", "branching" | NO |

Sequencing mechanics may not even need zone detection. The primary assets are text-based sequence items derived from domain knowledge (`sequence_flow_data` in DomainKnowledge schema). The asset generator has no tool to transform `SequenceFlowData` into blueprint-ready sequence steps.

#### description_matching -- MISSING ASSETS

| Required Asset | Description | Generated? |
|----------------|-------------|------------|
| `zone_descriptions` | Functional educational descriptions per zone | NO |
| `incorrect_descriptions` | Plausible-but-wrong distractors | NO |
| `matching_pairs` | `{zone_id, correct_description_id}` mapping | NO |

Zones are detected but their functional descriptions (what the structure does, not just its name) are never generated. The domain knowledge retriever may have relevant information in `hierarchical_relationships` but it is not consumed by the asset generator.

---

## Failure Mode Analysis

### Failure Chain 1: Image Retrieval Cascade

```
search_diagram_image fails (3 retries)
  -> fallback generic queries fail
    -> generate_diagram_image called
      -> Gemini Imagen unavailable
        -> success=False returned
          -> Agent has NO image, remaining tools unusable
          -> Loops until max_iterations=8, wasting time
```

**Impact:** Total asset generation failure. No image means no zones, no blueprint assets.
**Frequency:** Moderate -- depends on Gemini Imagen availability.

### Failure Chain 2: Zone Detection Degradation

```
detect_zones called with 10 expected_labels
  -> gemini_sam3 finds 3 zones
  -> gemini fallback finds 1 more zone (total 4)
  -> 6 labels missing
  -> Missing labels logged as WARNING
  -> submit_assets accepts with 4/10 zones
  -> Blueprint has 40% coverage
  -> Game is incomplete but marked as success
```

**Impact:** Incomplete games presented to students. 40% zone coverage means 60% of the interaction is missing.
**Frequency:** Common -- zone detection rarely achieves 100% on complex diagrams.

### Failure Chain 3: Silent Coordinate Collapse

```
detect_zones returns some zones with unparseable coordinates
  -> _normalize_zones_to_percent hits exception
  -> Silent fallback: coordinates set to (50, 50)
  -> Multiple zones stacked at diagram center
  -> submit_assets accepts (zones have id, label, x, y)
  -> Game shows overlapping drop targets at center
```

**Impact:** Unplayable game -- zones overlap, students cannot distinguish targets.
**Frequency:** Occasional -- depends on detection method output format.

### Failure Chain 4: Confidence Masking

```
10 expected labels
  -> 1 zone found with confidence 0.9
  -> Average confidence: 0.09 (1 * 0.9 / 10)
  -> No coverage threshold check
  -> submit_assets accepts
  -> Blueprint has 1 of 10 zones
```

**Impact:** High-confidence partial results mask poor overall coverage.
**Frequency:** Occasional -- more likely with complex multi-structure diagrams.

### Failure Chain 5: Qwen Exclusion

```
gemini_sam3 service down
  -> gemini vision API rate limited
  -> Auto fallback chain exhausted (only 2 methods)
  -> qwen available but NOT in auto fallback
  -> detect_zones returns 0 zones
  -> submit_assets rejects (zones empty)
```

**Impact:** Unnecessary failure -- a working detection method exists but is not reachable.
**Frequency:** Low -- but entirely preventable.

---

## Multi-Scene Coordination Issues

### Scene Assignment is Heuristic

The agent does not explicitly declare which scene it is working on. Scene assignment is inferred from the order of tool calls:
- First `search_diagram_image` call = scene 1
- Second `search_diagram_image` call = scene 2
- If the agent searches twice for the same scene (retry), the second search is misattributed to scene 2

**Risk:** Scene-asset misalignment in multi-scene games.

### No Image Deduplication

If two scenes share the same subject (e.g., "heart diagram" in scene 1 and scene 2 with different tasks), the agent may:
- Search for the same image twice
- Generate two copies of the same AI diagram
- Waste 2 of 8 iterations on redundant work

The `_collapse_same_image_scenes()` function in `game_planner` attempts to merge scenes with identical `asset_needs` queries upstream, but the asset generator has no awareness of this optimization.

### No Per-Mechanic Awareness

The agent's system prompt tells it to generate images and detect zones for each scene, but does not specify what mechanics each scene requires. A scene needing `trace_path` gets the same treatment as a scene needing `drag_drop`: image + zones, nothing more.

---

## Validation Gaps in submit_assets

### What IS Validated

| Check | Implementation |
|-------|----------------|
| Image file exists on disk | `os.path.exists(image_path)` |
| Zones array is non-empty | `len(zones) > 0` |
| Each zone has required keys | `zone.get("id")`, `zone.get("label")`, `zone.get("x")`, `zone.get("y")` |

### What is NOT Validated

| Missing Check | Impact |
|---------------|--------|
| Per-mechanic asset completeness | Games missing prompts/waypoints/steps silently accepted |
| Zone-label consistency (duplicates) | Multiple zones with same label cause scoring errors |
| Zone-label consistency (non-canonical) | Labels not matching domain knowledge pass through |
| Coordinate range (0-100) | Out-of-range coordinates cause off-screen zones |
| Radius sanity | Extremely large radii cause overlapping hit areas |
| Polygon validity | Self-intersecting polygons from SAM3 not detected |
| Multi-scene consistency | Scene 1 with 10 zones, scene 2 with 0 zones both accepted |
| Non-contiguous scene numbering | Gaps in scene numbers (1, 3, 4) not detected |
| Domain knowledge alignment | Zones not checked against canonical_labels from DomainKnowledge |
| Coverage threshold | 1/10 labels found at high confidence still accepted |

---

## Critical Bugs

### Bug 1: Missing Labels = Warnings, Not Errors

**Location:** `submit_assets` validation in `asset_generator_tools.py`
**Behavior:** When expected labels from the scene spec are not found in detected zones, the tool logs a warning but returns `status: "accepted"`.
**Impact:** Games with 30-40% label coverage are marked as successfully generated.
**Fix:** Add a configurable coverage threshold (e.g., 70% of expected labels must be present). Below threshold = rejection with actionable feedback.

### Bug 2: Silent Coordinate Fallback to Center

**Location:** `_normalize_zones_to_percent()` in zone detection post-processing
**Behavior:** When coordinate parsing fails for a zone, coordinates are silently set to `(50, 50)`.
**Impact:** Multiple zones collapse to the center of the diagram, making the game unplayable. No error is surfaced to the agent or the user.
**Fix:** Flag zones with fallback coordinates. If more than 1 zone falls back, reject the detection result and retry with a different method.

### Bug 3: Confidence Masking

**Behavior:** Finding 1 of 10 labels at 0.9 confidence looks like a high-quality result on a per-zone basis, but represents only 10% coverage.
**Impact:** The agent may stop searching for better results because the found zones appear confident.
**Fix:** Track both per-zone confidence AND coverage ratio (found/expected). Surface coverage ratio in submit_assets validation.

### Bug 4: No Per-Mechanic Asset Spec in System Prompt

**Behavior:** The agent's system prompt describes tools for image retrieval and zone detection but never mentions mechanic-specific assets (prompts, waypoints, steps, descriptions).
**Impact:** The agent literally does not know it should generate these assets. Even a highly capable model cannot produce outputs it was never asked for.
**Fix:** Inject per-mechanic asset requirements into the system prompt based on the scene's assigned mechanics.

---

## Proposed Per-Mechanic Asset Workflows

### drag_drop (current -- no changes needed)

```
search_diagram_image(scene.image_description)
  -> generate_diagram_image(description)       [fallback]
  -> detect_zones(image, expected_labels)
  -> submit_assets(image, zones)
```

### click_to_identify (NEW tools needed)

```
search_diagram_image(scene.image_description)
  -> detect_zones(image, expected_labels)
  -> [NEW] generate_identification_prompts(zones, domain_knowledge)
       Output: [{targetZoneId, promptText, hintText, misconceptionFeedback}]
  -> [NEW] validate_prompt_coverage(prompts, zones)
  -> submit_assets(image, zones, identification_prompts)
```

### trace_path (NEW tools needed)

```
search_diagram_image(scene.image_description)
  -> detect_zones(image, expected_labels)        [for waypoint anchors]
  -> [NEW] generate_waypoints(zones, sequence_flow_data)
       Output: ordered [{x, y, zone_id}] coordinates
  -> [NEW] generate_path_connections(waypoints)
       Output: [{start_zone, end_zone, path_type}] edges
  -> [NEW] validate_path_traversability(waypoints, connections)
       Checks: connected graph, no dead ends, matches flow_type
  -> submit_assets(image, zones, waypoints, path_connections, correct_path_sequence)
```

### sequencing (NEW tools needed)

```
[optional] search_diagram_image(scene.image_description)
  -> [NEW] generate_sequence_items(domain_knowledge.sequence_flow_data, scene_spec)
       Output: [{id, text, orderIndex, description}]
  -> [NEW] generate_distractors(sequence_items, domain_knowledge)
       Output: [{id, text, description, reason_incorrect}]
  -> [NEW] validate_sequence_completeness(items, distractors, correct_order)
  -> submit_assets(image?, sequence_items, distractors, correct_order)
```

### description_matching (NEW tools needed)

```
search_diagram_image(scene.image_description)
  -> detect_zones(image, expected_labels)
  -> [NEW] generate_functional_descriptions(zones, domain_knowledge)
       Output: [{zone_id, description, is_correct: true}]
  -> [NEW] generate_incorrect_descriptions(zones, domain_knowledge)
       Output: [{zone_id, description, is_correct: false, why_wrong}]
  -> [NEW] validate_description_quality(descriptions, zones)
       Checks: each zone has 1 correct + N incorrect, no duplicates
  -> submit_assets(image, zones, descriptions)
```

### New Tool Summary

| New Tool | Used By | Input | Output |
|----------|---------|-------|--------|
| `generate_identification_prompts` | click_to_identify | zones, domain_knowledge | prompts[] |
| `validate_prompt_coverage` | click_to_identify | prompts, zones | pass/fail |
| `generate_waypoints` | trace_path | zones, sequence_flow_data | waypoints[] |
| `generate_path_connections` | trace_path | waypoints | edges[] |
| `validate_path_traversability` | trace_path | waypoints, connections | pass/fail |
| `generate_sequence_items` | sequencing | sequence_flow_data, scene_spec | items[] |
| `generate_distractors` | sequencing | items, domain_knowledge | distractors[] |
| `validate_sequence_completeness` | sequencing | items, distractors, order | pass/fail |
| `generate_functional_descriptions` | description_matching | zones, domain_knowledge | descriptions[] |
| `generate_incorrect_descriptions` | description_matching | zones, domain_knowledge | distractors[] |
| `validate_description_quality` | description_matching | descriptions, zones | pass/fail |

**Total: 11 new tools** (4 generation + 4 validation + 3 shared utilities)

---

## Priority Recommendations

### Critical (blocks game quality)

| # | Recommendation | Effort | Impact |
|---|----------------|--------|--------|
| C1 | Convert missing-label warnings to errors with configurable coverage threshold (default 70%) | Low | Prevents incomplete games from being accepted |
| C2 | Add per-mechanic asset completeness validation to `submit_assets` | Medium | Rejects games missing required mechanic-specific assets |
| C3 | Inject per-mechanic asset requirements into agent system prompt | Low | Agent becomes aware of what each mechanic needs |
| C4 | Fix silent coordinate fallback -- flag or reject zones at (50,50) | Low | Prevents unplayable overlapping zones |

### High (improves reliability)

| # | Recommendation | Effort | Impact |
|---|----------------|--------|--------|
| H1 | Add explicit `scene_number` parameter to all tools | Medium | Eliminates heuristic scene assignment |
| H2 | Add coverage ratio metric (found_labels / expected_labels) to validation | Low | Surfaces incomplete detection |
| H3 | Add mechanic checklist to system prompt so agent plans tool usage per mechanic | Low | Agent generates correct tool call sequence |
| H4 | Fix coordinate range validation (0-100 for percentages) | Low | Catches out-of-range zones before submission |
| H5 | Enable qwen in auto fallback chain for zone detection | Low | Adds a third fallback when gemini methods fail |

### Medium (improves efficiency and completeness)

| # | Recommendation | Effort | Impact |
|---|----------------|--------|--------|
| M1 | Add image deduplication across scenes (hash-based) | Medium | Prevents redundant image retrieval |
| M2 | Validate zone-label matching against `canonical_labels` from DomainKnowledge | Medium | Ensures zone labels are educationally correct |
| M3 | Implement the 11 new per-mechanic tools (phased rollout) | High | Enables full multi-mechanic asset generation |
| M4 | Add polygon validity checking for SAM3 outputs | Low | Prevents self-intersecting zone polygons |
| M5 | Add multi-scene consistency validation (zone count parity, scene numbering) | Medium | Catches cross-scene imbalances |

### Implementation Order

```
Phase 1 (immediate): C1, C3, C4, H2, H4, H5
  -- Validation hardening, no new tools needed

Phase 2 (short-term): C2, H1, H3, M2
  -- Per-mechanic awareness, explicit scene control

Phase 3 (medium-term): M1, M3 (drag_drop already done, add click_to_identify + description_matching)
  -- First new tool implementations for simpler mechanics

Phase 4 (longer-term): M3 (trace_path + sequencing), M4, M5
  -- Complex new tools requiring domain knowledge integration
```
