# V4 Pipeline Stage-by-Stage E2E Test Findings

**Date:** 2026-02-17
**Test question:** "Heart anatomy: label the four chambers, trace the blood flow path through the heart, and arrange the steps of the cardiac cycle in order"
**Expected mechanics:** drag_drop, trace_path, sequencing (3 scenes, 3 mechanics)
**Total pipeline time:** ~142s (50.3s Phase 0 + 92.1s remaining stages)
**Output dir:** `backend/test_outputs/v4_stage_by_stage/`

---

## Stage 1: input_analyzer (Phase 0) — PASS

**Duration:** ~8s (ran in parallel with dk_retriever, total Phase 0 = 38.6s)
**Model:** gemini-2.5-flash (442 prompt tokens, 1007 completion tokens, 8059ms latency)
**Output file:** `01_input_analyzer.json`

### Output Summary
- **Bloom's level:** apply (correct — question requires labeling, tracing, and sequencing)
- **Subject:** Biology
- **Difficulty:** intermediate
- **Learning objectives (3):**
  1. Accurately label the four chambers
  2. Trace the complete blood flow path
  3. Correctly sequence the cardiac cycle events
- **Key concepts (5):** Heart Chambers, Pulmonary Circulation, Systemic Circulation, Cardiac Cycle, Heart Valves
- **Common misconceptions (3):** All blood is oxygenated; chambers contract simultaneously; blood flows directly right-to-left
- **Prerequisites (3):** Basic circulation, anatomical terms, oxygen/CO2 function

### Assessment
- Bloom's level "apply" is appropriate — the question asks students to actively do things (label, trace, sequence), not just recall.
- All 3 learning objectives map 1:1 to the 3 sub-tasks in the question. This is ideal.
- Key concepts are relevant and well-scoped.
- Misconceptions are pedagogically sound and commonly cited in biology education.
- No fields dropped. Full output present.

### Issues
None.

---

## Stage 2: dk_retriever (Phase 0) — PASS

**Duration:** ~38s (ran in parallel, includes 3 sub-stages)
**Model:** gemini-2.5-flash (3 LLM calls + 2 web searches)
**Output file:** `02_dk_retriever.json`

### Sub-stages
| Sub-stage | Duration | Status | Details |
|-----------|----------|--------|---------|
| dk_main_extraction | 15,283ms | success | 26 canonical labels extracted |
| dk_label_descriptions | 6,822ms | success | 25 label descriptions |
| dk_sequence_flow | 6,455ms | success | 9-step cyclic flow extracted |

### Output Summary
- **Canonical labels (26):** Heart, Heart Chambers, Right Atrium, Left Atrium, Right Ventricle, Left Ventricle, Blood Flow Path, Deoxygenated Blood, Oxygenated Blood, Vena Cava, Tricuspid Valve, Pulmonary Valve, Pulmonary Artery, Lungs, Pulmonary Veins, Mitral Valve, Aortic Valve, Aorta, Body, Cardiac Cycle, Diastole, Systole, Atrial Systole, Ventricular Systole, Atrial Diastole, Ventricular Diastole
- **Acceptable variants:** Vena Cava → [Superior/Inferior Vena Cava], Mitral Valve → [Bicuspid Valve], Body → [Systemic Circulation], Systole → [Contraction], Diastole → [Relaxation]
- **Hierarchical relationships (6 parent groups):** Heart → [Chambers, Blood Flow Path, Cardiac Cycle], etc.
- **Sources (5):** Cleveland Clinic, Lumen Learning, NHLBI, Study.com — all reputable
- **Sequence flow data:** 9-step cyclic flow from Vena Cava → Right Atrium → ... → Body → back to Vena Cava
- **Label descriptions:** 25 functional descriptions (1-2 sentences each)
- **Scene hints (3):** Heart Chambers, Blood Flow Path, Cardiac Cycle — matches expected scenes

### Assessment
- Rich domain knowledge with 26 labels covering all anatomical structures needed.
- Sequence flow data is complete and correctly ordered — this feeds directly into the sequencing mechanic.
- Scene hints align with what game_concept_designer later creates.
- `content_characteristics.needs_labels=true, needs_sequence=true, needs_comparison=false` — correctly detected.

### Issues
- `Ventricular Diastole` label is in canonical_labels but missing from label_descriptions (25 descriptions for 26 labels). Minor omission, does not affect downstream.

---

## Stage 3: phase0_merge (Phase 0) — PASS

**Duration:** 7ms
**Output file:** `03_phase0_merge.json`

### Output Summary
- `pedagogical_context`: present (passed through from input_analyzer)
- `domain_knowledge`: present (passed through from dk_retriever)

### Assessment
- Merge barrier works correctly. Both parallel branches' outputs are available for downstream stages.

### Issues
None.

---

## Stage 4: game_concept_designer (Phase 1a) — PASS

**Duration:** 11,620ms
**Model:** gemini-2.5-flash (2110 prompt tokens, 1389 completion tokens)
**Output file:** `03_game_concept_designer.json`

### Output Summary
- **Title:** "Heartbeat Hero: A Cardiovascular Journey"
- **Subject:** Biology, **Difficulty:** intermediate, **Duration:** 12 min
- **Narrative theme:** "A medical exploration mission inside the human body."
- **Narrative intro:** Present (engaging, mission-themed)
- **Completion message:** Present

**Scenes (3):**

| Scene | Title | Mechanic | Zone Labels | needs_diagram | items | points |
|-------|-------|----------|-------------|---------------|-------|--------|
| 1 | Chamber Identification | drag_drop | 4 (RA, LA, RV, LV) | true | 4 | 10/item |
| 2 | Blood Flow Blueprint | trace_path | 14 (full flow path) | true | 14 | 10/item |
| 3 | Cardiac Cycle Chronology | sequencing | 0 | false | 5 | 10/item |

- **all_zone_labels (14):** Right Atrium, Left Atrium, Right Ventricle, Left Ventricle, Vena Cava, Tricuspid Valve, Pulmonary Valve, Pulmonary Artery, Lungs, Pulmonary Veins, Mitral Valve, Aortic Valve, Aorta, Body
- **distractor_labels (3):** Septum, Pericardium, Diaphragm
- **concept_validation:** passed=true, score=1.0, issues=[]
- **concept_retry_count:** 1 (passed on first attempt)

### Assessment
- Excellent 1:1 mapping between question sub-tasks and scenes.
- Mechanic choices are appropriate: drag_drop for labeling, trace_path for blood flow tracing, sequencing for cardiac cycle ordering.
- Scene 3 correctly has `needs_diagram=false` since sequencing is content-only.
- Zone labels are well-distributed: 4 for scene 1, 14 for scene 2, 0 for scene 3.
- Distractors (Septum, Pericardium, Diaphragm) are plausible but incorrect — good pedagogy.
- `label_hierarchy` is null — this field is optional, not a problem.
- Each mechanic has `learning_purpose` explaining why that mechanic was chosen.

### Issues
- `label_hierarchy` is null. Could be useful for the graph builder but not required.
- `advance_trigger_value` is null for all mechanics. This is fine since `advance_trigger="completion"` doesn't need a value.

---

## Stage 5: concept_validator (Phase 1a) — PASS

**Duration:** 0ms (instant — Pydantic validation only)
**Output file:** `04_concept_validator.json`

### Output Summary
- **passed:** true
- **score:** 1.0
- **issues:** [] (no issues)

### Assessment
- Game concept passed all validation checks on first attempt.

### Issues
None.

---

## Stage 6: scene_designers ×3 (Phase 1b) — PASS

**Duration:** 36,084ms total (sequential: 11.5s + 15.6s + 8.7s)
**Model:** gemini-2.5-flash
**Output file:** `01_scene_designers.json`

### Output Summary

**Scene 1 (Chamber Identification / drag_drop):**
- visual_concept: "High-tech medical scanner interface, holographic heart projection"
- image_spec: Detailed anterior view heart diagram, holographic style, 9 must_include_structures
- mechanic_designs[0]: drag_drop — visual_style describes glowing translucent labels, pulsing drop targets
- generation_goal: "Generate four distinct draggable text labels"
- key_concepts: [Right Atrium, Left Atrium, Right Ventricle, Left Ventricle]
- scene_narrative + transition_narrative: Present

**Scene 2 (Blood Flow Blueprint / trace_path):**
- visual_concept: "High-tech holographic medical scan interface"
- image_spec: Heart + major arteries + veins + lungs + body representation, 14 must_include_structures
- mechanic_designs[0]: trace_path — visual_style describes glowing trace lines (blue for deoxy, red for oxy)
- path_process: "Complete circulation of a red blood cell through the human heart"
- generation_goal: "Generate a precise, sequential path connecting all 14 specified anatomical structures"

**Scene 3 (Cardiac Cycle / sequencing):**
- visual_concept: "Holographic diagnostic interface within translucent heart"
- image_spec: null (correct — sequencing doesn't need a diagram)
- mechanic_designs[0]: sequencing — visual_style "Holographic display elements with glowing borders"
- sequence_topic: "Major Events of the Cardiac Cycle"
- generation_goal: "Generate 5 distinct, sequential phases of the cardiac cycle"
- layout_mode: "circular_cycle" — creative choice for a cyclic process

### Assessment
- All 3 scene designs are rich and creative with consistent "medical explorer" theme.
- image_spec is present for scenes 1 and 2 (which need diagrams), null for scene 3 (which doesn't).
- Each mechanic_design has visual_style, instruction_text, and generation_goal filled.
- Mechanic-specific hint fields populated: `path_process` for trace_path, `sequence_topic` for sequencing.
- Scene narratives and transition narratives provide continuity.

### Issues
- The raw output shows `title: '?'` and `mechanic_designs: 0` in the console printout. This is because the raw list wrapper adds scene_id/status/design at the top level, and the print code was reading wrong keys. The actual `design` nested object has all the data. This is a test script display bug, not a pipeline issue.

---

## Stage 7: scene_design_merge (Phase 1b) — PASS

**Duration:** 4ms
**Output file:** `02_scene_design_merge.json`

### Output Summary
- **Merged designs:** 3 (scene_1, scene_2, scene_3)
- **Validation:** All 3 passed (score=1.0, no issues)
- **scene_1:** 1 mechanic design (drag_drop)
- **scene_2:** 1 mechanic design (trace_path)
- **scene_3:** 1 mechanic design (sequencing)

### Assessment
- Deduplication worked correctly (3 raw → 3 merged, no duplicates).
- All designs validated successfully.

### Issues
None.

---

## Stage 8: graph_builder (Graph Builder) — PASS

**Duration:** 8ms
**Output file:** `03_graph_builder.json`

### Output Summary
- **Title:** "Heartbeat Hero: A Cardiovascular Journey"
- **total_max_score:** 230

**Scene Plans:**

| Scene | Mechanic ID | Type | Items | Points/Item | Max Score | is_terminal | creative_design |
|-------|------------|------|-------|-------------|-----------|-------------|-----------------|
| scene_1 | s1_m0 | drag_drop | 4 | 10 | 40 | true | type=drag_drop, style present |
| scene_2 | s2_m0 | trace_path | 14 | 10 | 140 | true | type=trace_path, style present |
| scene_3 | s3_m0 | sequencing | 5 | 10 | 50 | true | type=sequencing, style present |

- **Score arithmetic:** 40 + 140 + 50 = 230 (matches total_max_score)
- **Mechanic connections:** None (each scene has only 1 mechanic, so no intra-scene connections needed)
- **creative_design copied:** Yes — each MechanicPlan has a creative_design with matching mechanic_type
- **image_spec propagated:** Yes — scene_1 and scene_2 have image_spec from creative designs

### Assessment
- All IDs correctly assigned: scene_1/scene_2/scene_3 and s1_m0/s2_m0/s3_m0.
- Score computation is correct: expected_item_count × points_per_item = max_score.
- creative_design is properly copied from SceneCreativeDesign → MechanicPlan.
- Since each scene has only 1 mechanic, there are no mechanic_connections (correct behavior).
- all_zone_labels and distractor_labels propagated from concept.

### Issues
None. This is a deterministic stage and it's working correctly.

---

## Stage 9: game_plan_validator (Graph Builder) — PASS

**Duration:** 1ms
**Output file:** `04_game_plan_validator.json`

### Output Summary
- **passed:** true
- **score:** 1.0
- **issues:** []

### Assessment
- Game plan passed all validation checks.

### Issues
None.

---

## Stage 10: content_generators ×3 (Phase 2a) — PARTIAL PASS (2/3)

**Duration:** 26,409ms total
**Output file:** `05_content_generators.json`

### Results per mechanic:

**s1_m0 (drag_drop) — SUCCESS (3,459ms):**
- labels: ["Right Atrium", "Left Atrium", "Right Ventricle", "Left Ventricle"]
- distractor_labels: ["Aorta", "Pulmonary Artery", "Vena Cava"]
- Visual config fields present: interaction_mode, feedback_timing, label_style, leader_line_style, leader_line_color, leader_line_animate, pin_marker_shape, label_anchor_side, tray_position, tray_layout, placement_animation, incorrect_animation, zone_idle_animation, zone_hover_effect, max_attempts, shuffle_labels

**s2_m0 (trace_path) — SUCCESS (18,080ms):**
- paths: 2 paths (Deoxygenated Blood Flow: 7 waypoints, Oxygenated Blood Flow: 8 waypoints)
- Visual config fields present: path_type, drawing_mode, particleTheme, particleSpeed, color_transition_enabled, show_direction_arrows, show_waypoint_labels, show_full_flow_on_complete, submit_mode
- Path 1 (blue, #0000FF): Vena Cava → Right Atrium → Tricuspid Valve → Right Ventricle → Pulmonary Valve → Pulmonary Artery → Lungs
- Path 2 (red, #FF0000): Lungs → Pulmonary Veins → Left Atrium → Mitral Valve → Left Ventricle → Aortic Valve → Aorta → Body
- **Note:** All 14 zone labels are covered across the 2 paths (7 + 8 = 15 waypoints, with Lungs appearing in both as the transition point).

**s3_m0 (sequencing) — FAILED (4,860ms):**
- Error: `2 validation errors for SequencingContent`
  - `items.5: Input should be a valid dictionary or instance of SequenceItemInput [type=model_type, input_value='correct_order', input_type=str]`
  - `correct_order: Field required [type=missing]`
- Root cause: The LLM returned a JSON structure where the `items` array contained an extra string entry `'correct_order'` at index 5, and the `correct_order` field was missing as a separate top-level key. The LLM confused the field structure.

### Assessment
- drag_drop content is excellent: correct labels, reasonable distractors, complete visual config.
- trace_path content is excellent: two paths correctly split at the oxygenation point (lungs), waypoints labeled and ordered, visual config complete.
- sequencing content failed due to LLM JSON structure error — the Pydantic schema expects `{items: [...], correct_order: [...]}` but the LLM embedded `correct_order` inside the items array.

### Issues

**BUG-1 (CRITICAL): Sequencing content generation Pydantic parse failure**
- **File:** `backend/app/v4/agents/content_generator.py`
- **Root cause:** LLM returned malformed JSON for SequencingContent. The `items` array contained an extra string entry `'correct_order'` instead of having `correct_order` as a separate top-level field.
- **Impact:** Scene 3 has no content. sequenceConfig in blueprint is empty. The sequencing mechanic is non-functional.
- **Fix options:**
  1. Add JSON repair logic in content_generator to detect and fix this pattern (move misplaced keys out of items array)
  2. Add a more explicit schema hint in the prompt showing exact expected structure
  3. Add retry logic: if SequencingContent parse fails, retry with the error message

---

## Stage 11: content_merge (Phase 2a) — PASS

**Duration:** 0ms
**Output file:** `06_content_merge.json`

### Output Summary
- **Merged contents:** 3 (s1_m0: success, s2_m0: success, s3_m0: failed)
- **failed_content_ids:** ["s3_m0"]
- **is_degraded:** true (set because of the failure)

### Assessment
- Merge correctly preserved both successful and failed results.
- `is_degraded` flag correctly set due to content failure.

### Issues
None (merge is working correctly; the issue is upstream in content generation).

---

## Stage 12: interaction_designers ×2 (Phase 2b) — PASS

**Duration:** 24,171ms total (14,986ms + 9,181ms)
**Output file:** `07_interaction_designers.json`

### Results per scene:

**scene_1 (drag_drop) — SUCCESS (14,986ms):**
- mechanic_scoring.s1_m0: strategy=per_correct, points_per_correct=10, max_score=40, partial_credit=true
- mechanic_feedback.s1_m0: on_correct, on_incorrect, on_completion messages present
- misconceptions (3): right_left_blood_type_confusion, atrium_ventricle_role_confusion, pulmonary_circulation_bypass_confusion — directly sourced from input_analyzer's common_misconceptions
- mode_transitions: [{from: drag_drop, to: trace_path, trigger: all_zones_labeled}] — this transition links scene 1 to scene 2's mechanic

**scene_2 (trace_path) — SUCCESS (9,181ms):**
- mechanic_scoring.s2_m0: strategy=per_correct, points_per_correct=10, max_score=140, partial_credit=true
- mechanic_feedback.s2_m0: on_correct, on_incorrect, on_completion messages present
- misconceptions (2): path_error_deoxygenated_to_left_heart, path_error_bypass_pulmonary_circulation
- mode_transitions: [] (no transitions from trace_path — it's the last mechanic in scene 2)

### Assessment
- Scoring rules match the game plan: 10 pts/correct for both mechanics.
- Misconception-based feedback is well-targeted — uses the pedagogical context effectively.
- Mode transitions correctly connect scene 1's drag_drop to scene 2's trace_path.
- **Note:** Scene 3 (sequencing) was not dispatched because its content generation failed. The interaction_dispatch_router correctly skipped it (no successful contents for scene 3).

### Issues
- Scene 3 has no interaction design because content generation failed. This is expected behavior (graceful degradation), but means the sequencing mechanic has no scoring/feedback rules in the blueprint.

---

## Stage 13: interaction_merge (Phase 2b) — PASS

**Duration:** 0ms
**Output file:** `08_interaction_merge.json`

### Output Summary
- **Merged results:** 2 (scene_1: success, scene_2: success)

### Assessment
- Correctly merged 2 interaction results. Scene 3 was never dispatched.

### Issues
None.

---

## Stage 14: asset_workers ×2 (Phase 3) — FAIL

**Duration:** 5,465ms (2,998ms + 2,466ms)
**Output file:** `09_asset_workers.json`

### Results per scene:

**scene_1 — ERROR:**
- error: "Zone detection returned no zones"
- diagram_url: null
- zones: []
- match_quality: 0.0

**scene_2 — ERROR:**
- error: "Zone detection returned no zones"
- diagram_url: null
- zones: []
- match_quality: 0.0

### Root Cause Analysis
From the stderr output during the test run:
```
Zone detection failed: [Errno 2] No such file or directory: 'https://www.ptdirect.com/images/personal-training-chambers-of-the-heart'
Zone detection failed: [Errno 2] No such file or directory: 'https://dr282zn36sxxg.cloudfront.net/datastreams/...'
```

The asset_worker's zone detection is treating the image URL as a local file path. The `_detect_zones()` function in `asset_dispatcher.py` passes the URL string directly to the Gemini vision API or local file reader, but the underlying service expects a downloaded file path or base64 data, not a raw URL.

**The image search worked** (it found URLs), but **zone detection failed** because the image wasn't downloaded before being passed to the vision model.

### Assessment
- Image search sub-stage is finding relevant images.
- Zone detection sub-stage fails because it tries to open a URL as a local file.
- This is a service-layer issue in the image retrieval → Gemini vision pipeline.

### Issues

**BUG-2 (CRITICAL): Asset worker doesn't download images before zone detection**
- **File:** `backend/app/v4/agents/asset_dispatcher.py` (or `backend/app/services/image_retrieval.py`)
- **Root cause:** Image URL from Serper search is passed directly to zone detection, which tries to open it as a local file path (`[Errno 2] No such file or directory`).
- **Impact:** No zones detected for any scene. All zone `points` arrays are empty in the blueprint. Drag-drop has no clickable regions. Trace path has no waypoint coordinates.
- **Fix:** Download the image to a temp file (or convert to base64) before passing to Gemini vision zone detection.

---

## Stage 15: asset_merge (Phase 3) — PASS

**Duration:** 0ms
**Output file:** `10_asset_merge.json`

### Output Summary
- **Merged assets:** 2 (scene_1: error, scene_2: error)
- **asset_retry_count:** 1

### Assessment
- Correctly merged the 2 error results. Retry count incremented but not retried (test script runs each stage once).

### Issues
None (merge is working; the issue is in asset_worker).

---

## Stage 16: assembler (Phase 4) — PASS (DEGRADED)

**Duration:** 4ms
**Output file:** `11_assembler.json`

### Blueprint Output Summary
- **templateType:** INTERACTIVE_DIAGRAM
- **title:** "Heartbeat Hero: A Cardiovascular Journey"
- **totalMaxScore:** 230
- **generation_complete:** true
- **is_degraded:** true
- **Blueprint size:** 14,101 chars (~14KB)

**Root-level fields:**
- `diagram.assetUrl`: null (no image because asset workers failed)
- `diagram.assetPrompt`: present (image description for future generation)
- `diagram.zones`: 4 zones (Right Atrium, Left Atrium, Right Ventricle, Left Ventricle) — all with `points: []`
- `labels`: 4 labels with correct `correctZoneId` references
- `distractorLabels`: 3 (Septum, Pericardium, Diaphragm)
- `mechanics`: 3 entries (drag_drop, trace_path, sequencing)
- `dragDropConfig`: PRESENT with full visual config (16 fields)
- `interactionMode`: "drag_drop"
- `scoringStrategy`: {base_points_per_zone: 10, max_score: 230}
- `modeTransitions`: [] (should have transitions but empty)

**game_sequence (multi-scene):**
- `is_multi_scene`: true
- `game_sequence.scenes`: 3 scenes

**Per-scene breakdown:**

| Scene | diagram.assetUrl | zones | labels | Config keys | paths |
|-------|-----------------|-------|--------|-------------|-------|
| scene_1 | null | 4 (empty points) | 4 | dragDropConfig (16 fields) | - |
| scene_2 | null | 14 (empty points) | 14 | tracePathConfig (11 fields) | 2 paths (15 waypoints, zoneId mapped) |
| scene_3 | null | 0 | 0 | sequenceConfig (empty items/correct_order) | - |

### Assembly Sub-stages
| Sub-stage | Status | Details |
|-----------|--------|---------|
| assembler_assemble | success | Built 3 scenes, 2 mechanic configs |
| assembler_validate | **failed** | 3 errors (see below) |
| assembler_repair | skipped | No applicable repairs found |

### Validation Errors
1. "Missing sequenceConfig for mechanic 'sequencing'" — because content generation failed for s3_m0
2. "Missing tracePathConfig for mechanic 'trace_path'" — config exists in scene_2 but validator checks root level
3. "paths[] must be at root for trace_path" — paths are in scene_2 but validator checks root level

### Assembly Warnings (8)
1. `1 mechanic(s) failed content generation`
2. `Missing assets for scenes: scene_1, scene_2`
3. `Missing sequenceConfig for mechanic 'sequencing'`
4. `Missing tracePathConfig for mechanic 'trace_path'`
5. `paths[] must be at root for trace_path`
6. `Blueprint has no diagram image URL`
7. `Zones with empty points: Right Atrium, Left Atrium, Right Ventricle, Left Ventricle`
8. `Game is degraded — some mechanics may not work`

### Assessment
- The assembler correctly built a multi-scene blueprint with game_sequence.
- dragDropConfig is correctly populated at both root and scene level (scene_1).
- tracePathConfig IS present in scene_2 — the validator is checking root level only. This is a **validator false positive**.
- paths[] ARE present in scene_2 with zoneId-mapped waypoints — another validator false positive.
- sequenceConfig is genuinely empty because content generation failed.
- Zone-to-label referential integrity is correct: each label's correctZoneId matches a zone ID.
- The `modeTransitions` array is empty at root level, even though interaction_designer produced a transition from drag_drop → trace_path. This may be a field placement issue in the assembler.

### Issues

**BUG-3 (MEDIUM): Blueprint validator checks root level instead of per-scene for tracePathConfig and paths[]**
- **File:** `backend/app/v4/validators/blueprint_validator.py`
- **Root cause:** The validator looks for `tracePathConfig` and `paths` at the blueprint root, but in multi-scene blueprints these are per-scene fields inside `game_sequence.scenes[N]`.
- **Impact:** False positive validation errors. The data IS there in scene_2, just not at root.
- **Fix:** Validator should check both root level (single-scene) AND per-scene level (multi-scene).

**BUG-4 (MEDIUM): modeTransitions empty despite interaction_designer producing them**
- **File:** `backend/app/v4/helpers/blueprint_assembler.py`
- **Root cause:** The interaction_designer for scene_1 produced `mode_transitions: [{from: drag_drop, to: trace_path, trigger: all_zones_labeled}]` but the assembler produced `modeTransitions: []` at root.
- **Impact:** Cross-scene transitions may not work in the frontend renderer.
- **Fix:** Assembler should collect mode_transitions from interaction_results and place them in the blueprint.

**BUG-5 (LOW): scene_2 has duplicate config keys (camelCase AND snake_case)**
- Both `tracePathConfig` and `trace_path_config` exist in scene_2. Similarly scene_1 has both `dragDropConfig` and `drag_drop_config`.
- **Impact:** Extra data, potential confusion in frontend. Not breaking but wasteful.
- **Fix:** Pick one convention (camelCase for frontend) and remove the snake_case duplicates.

---

## Overall Data Flow Verification

### Fields propagated correctly through all stages:

| Field | Written by | Read by | Status |
|-------|-----------|---------|--------|
| pedagogical_context | input_analyzer | game_concept_designer, interaction_dispatch_router | OK |
| domain_knowledge | dk_retriever | game_concept_designer, scene_design_send_router, content_dispatch_router | OK |
| game_concept | game_concept_designer | concept_validator, scene_design_send_router, graph_builder | OK |
| concept_validation | concept_validator | concept_router | OK |
| scene_creative_designs_raw | scene_designer ×3 | scene_design_merge | OK |
| scene_creative_designs | scene_design_merge | graph_builder, asset_send_router | OK |
| game_plan | graph_builder | game_plan_validator, content_dispatch_router, interaction_dispatch_router, asset_send_router, assembler | OK |
| design_validation | game_plan_validator | design_router | OK |
| mechanic_contents_raw | content_generator ×3 | content_merge | OK |
| mechanic_contents | content_merge | interaction_dispatch_router, assembler | OK |
| interaction_results_raw | interaction_designer ×2 | interaction_merge | OK |
| interaction_results | interaction_merge | assembler | OK |
| generated_assets_raw | asset_worker ×2 | asset_merge | OK |
| generated_assets | asset_merge | assembler | OK |
| blueprint | assembler | (terminal) | OK |
| generation_complete | assembler | route/generate.py | OK (true) |

**Verdict: Data flow is healthy.** Every stage reads from the correct upstream fields and writes to the correct output fields. No fields are dropped between stages.

---

## Bug Summary

| ID | Severity | Stage | Description | File |
|----|----------|-------|-------------|------|
| BUG-1 | CRITICAL | content_generators | Sequencing content Pydantic parse failure — LLM returns malformed JSON with `correct_order` embedded in `items` array | `content_generator.py` |
| BUG-2 | CRITICAL | asset_workers | Image URL treated as local file path — zone detection fails with `[Errno 2]` | `asset_dispatcher.py` / `image_retrieval.py` |
| BUG-3 | MEDIUM | assembler | Blueprint validator checks root-only for tracePathConfig/paths, misses per-scene placement | `blueprint_validator.py` |
| BUG-4 | MEDIUM | assembler | modeTransitions empty despite interaction_designer producing transitions | `blueprint_assembler.py` |
| BUG-5 | LOW | assembler | Duplicate config keys in both camelCase and snake_case per scene | `blueprint_assembler.py` |

---

## What Works End-to-End

1. **3-stage creative cascade architecture** — GameConcept → SceneCreativeDesigns → GamePlan flow is solid
2. **Parallel fan-out** — scene_designer ×3, content_generator ×3, interaction_designer ×2 all dispatch and merge correctly
3. **Score arithmetic** — 4×10 + 14×10 + 5×10 = 230, verified at concept, graph_builder, and blueprint levels
4. **Creative design propagation** — MechanicCreativeDesign flows from scene_designer → graph_builder → content_generator
5. **Pedagogical context integration** — Misconceptions from input_analyzer appear in interaction_designer's feedback
6. **Graceful degradation** — When sequencing content fails, the pipeline continues and produces a partial blueprint
7. **Multi-scene blueprint** — game_sequence with 3 scenes, each with per-scene configs
8. **Zone/label referential integrity** — Every label.correctZoneId references a valid zone.id

## What Needs Fixing

1. **Content generator robustness** — Add JSON repair/retry for sequencing schema mismatches
2. **Image download pipeline** — Download images before passing to Gemini vision
3. **Blueprint validator scope** — Check per-scene configs in multi-scene blueprints
4. **Mode transition propagation** — Assembler should collect and place transitions from interaction_results
5. **Config key deduplication** — Remove snake_case duplicates, keep camelCase only
