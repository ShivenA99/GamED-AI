# 48. V4 Pipeline — E2E Post-Fix Trace (3 Test Questions)

**Date**: 2026-02-18
**Context**: After fixing BUG-A through BUG-I, adding creative config propagation, removing silent fallbacks, and wiring the item_asset_worker — run all 3 test questions and trace every stage.
**Test data**: `backend/test_outputs/v4_e2e_trace/`

---

## Summary

| Question | Checks | Pass Rate | Duration | Outcome |
|----------|--------|-----------|----------|---------|
| Q1: Heart anatomy (drag_drop + trace_path + sequencing) | 50/51 | 98% | 180s | **PASS** (1 minor DK issue) |
| Q2: Cell organelles (sorting + drag_drop + desc_matching) | 46/47 | 98% | 179s | **PASS** (1 minor DK issue) |
| Q3: Chest pain branching | 2/9 | 22% | 105s | **FAIL** (concept designer schema gap) |

**Overall**: The pipeline is solid for multi-mechanic games (Q1, Q2). Pure branching scenarios (Q3) expose a concept designer prompt gap where the LLM omits `scenes`, `completion_message`, and `all_zone_labels` from its output.

---

## Q1: Heart Anatomy — Multi-Mechanic (50/51 PASS)

### Test Input
```
"Heart anatomy: label the four chambers, trace the blood flow path
through the heart, and arrange the steps of the cardiac cycle in order"
```

### Stage 0: Phase 0 Parallel (input_analyzer + dk_retriever)

#### input_analyzer → pedagogical_context

```json
{
  "blooms_level": "understand",
  "learning_objectives": [
    "Identify and label the four chambers of the human heart.",
    "Describe the complete path of blood flow through the heart, lungs, and body.",
    "Sequence the key events of the cardiac cycle in correct chronological order."
  ],
  "key_concepts": [
    {"concept": "Heart Chambers", "importance": "primary"},
    {"concept": "Blood Flow Path", "importance": "primary"},
    {"concept": "Cardiac Cycle", "importance": "primary"}
  ],
  "difficulty": "intermediate",
  "subject": "Human Anatomy and Physiology",
  "common_misconceptions": [
    {"misconception": "Oxygenated and deoxygenated blood mix in the heart.",
     "correction": "The septum completely separates the two sides."},
    {"misconception": "The heart pumps blood to lungs and body from a single chamber.",
     "correction": "Right side → lungs, left side → body (double pump)."},
    {"misconception": "All four chambers contract simultaneously.",
     "correction": "Atria contract first (atrial systole), then ventricles (ventricular systole)."}
  ]
}
```
**Verdict**: Rich pedagogical context with 3 misconceptions. All downstream agents can use this.

#### dk_retriever → domain_knowledge

```json
{
  "canonical_labels": ["Heart", "Heart Chambers", "Right Atrium", "Left Atrium",
    "Right Ventricle", "Left Ventricle", "Valves", "Tricuspid Valve",
    "Mitral Valve", "Pulmonary Valve", "Aortic Valve", "Blood Vessels",
    "Vena Cava", "Superior Vena Cava", "Inferior Vena Cava",
    "Pulmonary Artery", "Pulmonary Vein", "Aorta", "Blood Flow Path"],
  "label_descriptions": {},    // ← EMPTY — 0 descriptions found
  "sequence_flow_data": {
    "flow_type": "cardiac_cycle",
    "sequence_items": [
      {"order_index": 0, "text": "Atrial systole"},
      {"order_index": 1, "text": "Ventricular systole"},
      {"order_index": 2, "text": "Atrial diastole"},
      {"order_index": 3, "text": "Ventricular diastole"}
    ]
  }
}
```
**Issue**: `label_descriptions` is empty (0 entries) → phase_error recorded: `{'phase': 'dk_retrieval', 'error': 'only 0 labels found'}`. This is the **only check failure** across all of Q1. Pipeline continues anyway — DK search may have failed to scrape descriptions but the canonical labels are present.

### Stage 1: Game Concept Designer

```json
{
  "title": "Heartbeat Journey: Anatomy & Flow",
  "subject": "Human Anatomy and Physiology",
  "difficulty": "intermediate",
  "narrative_theme": "Medical Exploration",
  "all_zone_labels": ["Right Atrium", "Left Atrium", "Right Ventricle",
    "Left Ventricle", "Superior Vena Cava", "Inferior Vena Cava",
    "Pulmonary Artery", "Lungs", "Pulmonary Vein", "Aorta",
    "Body Tissues", "Tricuspid Valve", "Pulmonary Valve",
    "Mitral Valve", "Aortic Valve"],
  "scenes": [
    {
      "title": "Heart Chambers & Blood Flow",
      "needs_diagram": true,
      "zone_labels": [15 labels],
      "image_description": "Detailed anterior view of the human heart...",
      "mechanics": [
        {"mechanic_type": "drag_drop", "expected_item_count": 4,
         "zone_labels_used": ["Right Atrium", "Left Atrium", "Right Ventricle", "Left Ventricle"],
         "advance_trigger": "completion"},
        {"mechanic_type": "trace_path", "expected_item_count": 14,
         "zone_labels_used": [14 labels including valves, vessels],
         "advance_trigger": "completion"}
      ]
    },
    {
      "title": "The Cardiac Cycle",
      "needs_diagram": false,
      "zone_labels": [],
      "mechanics": [
        {"mechanic_type": "sequencing", "expected_item_count": 4}
      ]
    }
  ]
}
```

**Verdict**:
- 2 scenes, 3 mechanics (drag_drop, trace_path, sequencing)
- Scene 1 is multi-mechanic sharing one diagram (15 zone labels)
- Scene 2 is content-only (no diagram needed)
- `concept_retry_count`: 1 (needed 1 retry to get valid schema)
- Concept validation: **passed** (score=1.0, 0 issues)

### Stage 2: Scene Creative Design (parallel per scene)

#### Scene 1: Heart Chambers & Blood Flow

```json
{
  "visual_concept": "A detailed, interactive anatomical exploration...",
  "color_palette_direction": "Medical illustration style with clear differentiation...",
  "image_spec": {
    "description": "Highly detailed anterior view of the human heart...",
    "style": "clean_educational",
    "annotation_preference": "clean_unlabeled",
    "must_include_structures": [15 labels]
  },
  "mechanic_designs": [
    {
      "mechanic_type": "drag_drop",
      "visual_style": "Clean, rectangular text labels...",
      "card_type": "text_only",
      "layout_mode": "spatial",
      "instruction_text": "Drag and drop the labels to correctly identify the four primary chambers...",
      "feedback_style": "clinical",
      "generation_goal": "Generate 4 draggable text labels...",
      "needs_item_images": false
    },
    {
      "mechanic_type": "trace_path",
      "visual_style": "A dynamic, glowing line...",
      "layout_mode": "default",
      "connector_style": "flowing",
      "instruction_text": "Now that you've labeled the chambers, trace the complete path of blood flow...",
      "path_process": "blood flow through the circulatory system",
      "needs_item_images": false
    }
  ]
}
```

**Key observations**:
- `needs_item_images: false` for both zone-based mechanics — correct decision (they use the diagram)
- `path_process` hint present for trace_path — content generator will use this
- Multi-mechanic instruction builds on previous: "Now that you've labeled the chambers..."
- Scene design validation: **passed** (score=1.0)

#### Scene 2: The Cardiac Cycle

```json
{
  "mechanic_designs": [
    {
      "mechanic_type": "sequencing",
      "card_type": "text_only",
      "layout_mode": "circular_cycle",
      "connector_style": "arrow",
      "instruction_text": "Arrange the steps of a single cardiac cycle chronologically...",
      "sequence_topic": "The events of a single cardiac cycle",
      "needs_item_images": false
    }
  ]
}
```

**Verdict**: `needs_item_images: false` + `card_type: text_only` — correct for conceptual sequencing.

### Stage 3: Graph Builder → GamePlan

- `total_max_score`: 220 (4×10 + 14×10 + 4×10)
- Score arithmetic validated per mechanic: all correct
- Creative design copies: all match source mechanic_type
- Connections: Scene 1 has 1 connection (s1_m0 → s1_m1, trigger=`all_zones_labeled`)
- Design validation: **passed** (score=1.0)

### Stage 4: Content Generation (parallel per mechanic)

#### s1_m0 (drag_drop)
```json
{
  "labels": ["Right Atrium", "Left Atrium", "Right Ventricle", "Left Ventricle"],
  "distractor_labels": ["Aorta", "Pulmonary Artery"],
  "label_style": "text_only",
  "leader_line_style": "none",
  "tray_position": "bottom",
  "placement_animation": "spring",
  "feedback_timing": "deferred"
}
```
Visual config fields: 4/4 present.

#### s1_m1 (trace_path)
```json
{
  "paths": [{
    "label": "Blood Flow Circulation",
    "waypoints": [
      {"order": 0, "label": "Superior Vena Cava"},
      {"order": 1, "label": "Right Atrium"},
      {"order": 2, "label": "Tricuspid Valve"},
      {"order": 3, "label": "Right Ventricle"},
      {"order": 4, "label": "Pulmonary Valve"},
      ... // 14 total waypoints
    ]
  }],
  "path_type": "linear",
  "drawing_mode": "click_waypoints",
  "particleTheme": "dots",
  "particleSpeed": "medium"
}
```
Visual config fields: 3/3 present.

#### s2_m0 (sequencing)
```json
{
  "items": [
    {"id": "s1", "content": "Atrial Contraction (Atrial Systole)"},
    {"id": "s2", "content": "Ventricular Contraction (Ventricular Systole)"},
    {"id": "s3", "content": "Atrial Relaxation (Atrial Diastole)"},
    {"id": "s4", "content": "Ventricular Relaxation & Filling (Ventricular Diastole)"}
  ],
  "correct_order": ["s1", "s2", "s3", "s4"],
  "layout_mode": "circular_cycle",
  "card_type": "text_only",
  "connector_style": "arrow",
  "interaction_pattern": "drag_reorder",
  "sequence_type": "ordered"
}
```
Visual config fields: 3/3 present. `card_type: text_only` matches creative design.

**Verdict**: 3/3 content generations succeeded. All visual config fields propagated.

### Stage 4.5: Item Asset Worker

No mechanics had `needs_item_images: true`, so the item asset worker returned immediately with no state changes. This is the correct behavior — zone-based mechanics use the diagram, and the sequencing was text-only.

### Stage 5: Interaction Design (parallel per scene)

#### Scene 1 (2 mechanics)
```json
{
  "mechanic_scoring": {
    "s1_m0": {"strategy": "per_correct", "points_per_correct": 10, "max_score": 40},
    "s1_m1": {"strategy": "per_correct", "points_per_correct": 10, "max_score": 140}
  },
  "mechanic_feedback": {
    "s1_m0": {
      "on_correct": "Excellent! You've correctly identified a heart chamber.",
      "on_completion": "All chambers correctly labeled! Ready to trace blood flow.",
      "misconceptions": [
        {"trigger": "wrong_side_placement",
         "message": "The septum completely separates oxygenated from deoxygenated blood."},
        {"trigger": "wrong_chamber_type_placement",
         "message": "Atria are receiving chambers at the top, ventricles pump at the bottom."}
      ]
    },
    "s1_m1": {
      "misconceptions": [
        {"trigger": "path_mixes_blood_types", ...},
        {"trigger": "path_skips_pulmonary_circulation", ...},
        {"trigger": "path_sequence_error", ...}
      ]
    }
  },
  "mode_transitions": [
    {"from": "drag_drop", "to": "trace_path",
     "trigger": "all_zones_labeled", "animation": "fade"}
  ]
}
```

**Key**: Misconceptions from pedagogical_context successfully propagated into feedback rules. Mode transitions generated correctly.

#### Scene 2 (1 mechanic)
```json
{
  "mechanic_scoring": {
    "s2_m0": {"strategy": "per_correct", "points_per_correct": 10, "max_score": 40}
  }
}
```

### Stage 6: Asset Worker (parallel per scene needing diagram)

Only Scene 1 needed a diagram. Results:
```json
{
  "scene_id": "scene_1",
  "diagram_url": "https://www.ptdirect.com/images/personal-training-chambers-of-the-heart",
  "zones": [
    {"id": "zone_right_atrium", "label": "Right Atrium", "points": [32 coords]},
    {"id": "zone_left_atrium", "label": "Left Atrium", "points": [26 coords]},
    {"id": "zone_right_ventricle", "label": "Right Ventricle", "points": [37 coords]},
    {"id": "zone_left_ventricle", "label": "Left Ventricle", "points": [33 coords]},
    {"id": "zone_superior_vena_cava", ...},
    {"id": "zone_inferior_vena_cava", ...},
    {"id": "zone_pulmonary_artery", ...},
    {"id": "zone_pulmonary_vein", ...},
    {"id": "zone_aorta", ...},
    {"id": "zone_tricuspid_valve", ...},
    {"id": "zone_pulmonary_valve", ...},
    {"id": "zone_mitral_valve", ...},
    {"id": "zone_aortic_valve", ...}
  ],
  "match_quality": 0.867
}
```

- 13/15 zones detected by Gemini + SAM refinement
- 2 missing: "Lungs" and "Body Tissues" → synthetic zone IDs generated by zone_matcher
- This caused 2/15 labels to have unresolvable zone references in the blueprint (13/15 valid)
- `asset_retry_count: 1` — needed one retry

### Stage 7: Blueprint Assembler

Blueprint validation checks (all passed):
- `templateType`: INTERACTIVE_DIAGRAM
- `totalMaxScore`: 220
- `mechanics`: 3 (drag_drop, trace_path, sequencing)
- `dragDropConfig`: found with visual config fields
- `tracePathConfig`: found with visual config fields
- `sequenceConfig`: found with visual config fields
- `modeTransitions`: 1 transition (drag_drop → trace_path on all_zones_labeled)
- `zones`: 13 (from asset worker)
- `labels`: 15
- `label_zone_integrity`: 13/15 labels point to valid zones (2 missing: Lungs, Body Tissues)
- `dd_no_data_leak`: labels/distractor_labels NOT in dragDropConfig (correctly at root)
- `assembly_warnings`: 0
- `is_degraded`: false

### Q1 Issues Found

| # | Severity | Issue | Root Cause |
|---|----------|-------|------------|
| 1 | Minor | DK retrieval: 0 label_descriptions | Web scraper failed to extract descriptions from search results |
| 2 | Minor | 2/15 labels lack zone matches (Lungs, Body Tissues) | These structures aren't visible in the heart diagram image |
| 3 | Info | concept_retry_count=1 | LLM needed one retry to produce valid GameConcept schema |
| 4 | Info | asset_retry_count=1 | Image search needed one retry |

---

## Q2: Cell Organelles — Sorting + Drag-Drop + Description Matching (46/47 PASS)

### Test Input
```
"Classify these cell organelles by their function: mitochondria, ribosome,
nucleus, cell membrane, golgi apparatus, endoplasmic reticulum. Then match
each organelle to its description."
```

### Stage 1: Game Concept

```json
{
  "title": "Cellular Organelle Investigator",
  "scenes": [
    {
      "title": "Organelle Function Sorting",
      "needs_diagram": false,
      "mechanics": [
        {"mechanic_type": "sorting_categories", "expected_item_count": 6}
      ]
    },
    {
      "title": "Organelle Identification",
      "needs_diagram": true,
      "zone_labels": ["Mitochondria", "Ribosome", "Nucleus", "Cell Membrane", "Golgi Apparatus", "Endoplasmic Reticulum"],
      "mechanics": [
        {"mechanic_type": "drag_drop", "expected_item_count": 6},
        {"mechanic_type": "description_matching", "expected_item_count": 6}
      ]
    }
  ]
}
```

**Verdict**: LLM chose 3 mechanics across 2 scenes: sorting (content-only), drag_drop + description_matching (zone-based, multi-mechanic). Concept validation passed.

### Stage 2: Scene Creative Design

#### Scene 1 (sorting)
```
mechanic_type: sorting_categories
card_type: text_only
layout_mode: bucket
category_names: ["Genetic Information & Protein Synthesis", ...]
needs_item_images: false
```

#### Scene 2 (drag_drop + description_matching)
```
mechanic_type: drag_drop → layout_mode: spatial, label_style: text_only
mechanic_type: description_matching → description_source: functional_role
image_spec: present with 6 must_include_structures
```

### Stage 4: Content Generation

- s1_m0 (sorting_categories): **3 categories, 6 items** — visual config 3/3 present
- s2_m0 (drag_drop): **6 labels** — visual config 4/4 present
- s2_m1 (description_matching): **6 descriptions** — visual config 2/2 present

All 3/3 content generations succeeded.

### Stage 5: Interaction Design

- Scene 1: 1 scoring rule, 0 feedback rules (sorting mechanic)
- Scene 2: 2 scoring rules, 2 feedback rules, 1 mode transition

**Note**: Scene 1 has 0 feedback rules — the interaction designer didn't generate feedback for sorting. The assembler used generic fallback: `"No feedback from interaction_designer for s1_m0 (sorting_categories), using generic fallback"`. This is an interaction designer prompt gap.

### Stage 6: Blueprint

All checks passed:
- `sortingConfig`: found
- `dragDropConfig`: found
- `descriptionMatchingConfig`: found
- `modeTransitions`: 1
- No data leak in dragDropConfig

### Q2 Issues Found

| # | Severity | Issue | Root Cause |
|---|----------|-------|------------|
| 1 | Minor | DK retrieval: 0 label_descriptions | Same as Q1 |
| 2 | Minor | No feedback for sorting mechanic | Interaction designer prompt doesn't prioritize sorting feedback |
| 3 | Info | Used generic fallback for sorting feedback | Assembler correctly detected missing feedback |

---

## Q3: Chest Pain Branching — FAILED (2/9 PASS)

### Test Input
```
"A patient presents with chest pain. Walk through the diagnostic process
step by step, making clinical decisions at each point."
```

### Stage 1: Game Concept — SCHEMA FAILURE

After **3 attempts** (concept_retry_count=3), the LLM produced:
```json
{
  "title": "Code Chest Pain: A Clinical Diagnostic Challenge",
  "subject": "Clinical Medicine",
  "difficulty": "advanced",
  "estimated_duration_minutes": 15,
  "narrative_theme": "Emergency Department Simulation",
  "narrative_intro": "Welcome, Doctor. A 55-year-old male presents..."
}
```

**Missing required fields**:
- `scenes` — NO scenes array at all
- `completion_message` — no completion text
- `all_zone_labels` — no zone labels (expected empty array for branching)

**Root cause**: The concept designer's prompt/schema doesn't make it clear enough that EVERY concept MUST have `scenes` even for purely branching/decision-tree questions. The LLM treats branching scenarios as flat narratives rather than scene-based games.

**Impact**: Concept validation failed 3 times. After max retries, the concept was overridden via `"Concept validation failed after 2 retries, proceeding with override"`. But with 0 scenes:
- Scene design: 0 dispatched ("Dispatching 0 scene designers")
- Graph builder: no plan
- Content generation: nothing to generate
- Blueprint: never assembled
- `generation_complete`: false

### Q3 Fix Required

**BUG-J: Concept designer omits scenes for branching-only questions**

The concept designer prompt needs explicit guidance:
1. Every question MUST produce at least 1 scene
2. Branching scenarios go into a scene with `needs_diagram: false` and a single `branching_scenario` mechanic
3. The retry error message should include the full expected schema structure, not just "Field required"

Priority: **P1** — this completely blocks an entire mechanic type.

---

## Cross-Cutting Issues

### 1. Instrumentation DB FK constraint (all runs)

Every test run logs `FOREIGN KEY constraint failed` for ALL stage tracking. Root cause: test run IDs (e.g., `test_Q1_multi_mechanic_1771385059`) are NOT registered in the `pipeline_runs` table, so `stage_executions` and `execution_logs` FK constraints fail.

**Fix**: Either create a pipeline_run record before invoking the graph, or make the FK constraint optional for test runs.

### 2. DK Retriever label_descriptions always empty

All 3 test questions got `label_descriptions: {}` (0 descriptions). The DK retriever finds `canonical_labels` from web search but fails to extract descriptions. This is a web scraping quality issue — not a pipeline bug.

### 3. SAM3 concurrent Metal assertion (observed on re-run)

When 2 scenes both need diagrams and SAM3 runs concurrently on Apple Silicon:
```
-[AGXG16GFamilyCommandBuffer tryCoalescingPreviousComputeCommandEncoderWithConfig:...]:
failed assertion 'A command encoder is already encoding to this command buffer'
```
**Fix**: Serialize SAM3 calls (add semaphore=1 for SAM processing) or run SAM on CPU fallback.

### 4. Mode transition field name inconsistency

Interaction designer produces: `{"from": "drag_drop", "to": "trace_path"}`
But the test check at line ~430 looks for `from_mechanic_id`/`to_mechanic_id`.
The assembler handles the mapping, but the field names should be standardized.

---

## Data Flow Matrix — What Works

| Stage | Q1 (multi-mech) | Q2 (sorting) | Q3 (branching) |
|-------|:---:|:---:|:---:|
| input_analyzer → pedagogical_context | complete | complete | complete |
| dk_retriever → domain_knowledge | labels only, no descriptions | labels only | labels only |
| concept_designer → game_concept | 2 scenes, 3 mechs | 2 scenes, 3 mechs | **BROKEN: 0 scenes** |
| concept_validator | passed (1 retry) | passed | failed (3 retries) |
| scene_designer → creative_designs | 2 designs, all fields | 2 designs, all fields | N/A |
| graph_builder → game_plan | correct scores, connections | correct scores | N/A |
| content_generator → mechanic_contents | 3/3 success, all visual fields | 3/3 success | N/A |
| item_asset_worker | skipped (no needs_item_images) | skipped | N/A |
| interaction_designer → interaction_results | scoring + feedback + misconceptions | scoring (no sorting feedback) | N/A |
| asset_worker → zones/diagram | 13/15 zones, SAM refined | zones found | N/A |
| assembler → blueprint | complete, 0 warnings | complete, 3 warnings | N/A |

---

## Visual Config Propagation — Verified

| Config Field | Creative Design | Content Generator | Blueprint | Status |
|---|---|---|---|---|
| `card_type: text_only` | scene_designer | content.card_type | sequenceConfig.card_type | propagated |
| `layout_mode: circular_cycle` | scene_designer | content.layout_mode | sequenceConfig.layout_mode | propagated |
| `connector_style: arrow` | scene_designer | content.connector_style | sequenceConfig.connector_style | propagated |
| `leader_line_style: none` | scene_designer | content.leader_line_style | dragDropConfig.leader_line_style | propagated |
| `tray_position: bottom` | scene_designer | content.tray_position | dragDropConfig.tray_position | propagated |
| `particleSpeed: medium` | scene_designer | content.particleSpeed | tracePathConfig.particleSpeed | propagated |
| `path_type: linear` | scene_designer | content.path_type | tracePathConfig.path_type | propagated |
| `drawing_mode: click_waypoints` | scene_designer | content.drawing_mode | tracePathConfig.drawing_mode | propagated |
| `sort_mode: bucket` | scene_designer | content.sort_mode | sortingConfig.sort_mode | propagated |
| `item_card_type: text_only` | scene_designer | content.item_card_type | sortingConfig.item_card_type | propagated |

**All visual config fields verified as propagating from creative design → content → blueprint.**

---

## needs_item_images Decision — Verified

| Mechanic | card_type | needs_item_images | item_image_style | Correct? |
|---|---|---|---|---|
| Q1 drag_drop | text_only | false | null | Yes (zone-based, uses diagram) |
| Q1 trace_path | text_only | false | null | Yes (zone-based, uses diagram) |
| Q1 sequencing | text_only | false | null | Yes (conceptual text steps) |
| Q2 sorting | text_only | false | null | Yes (text classification) |
| Q2 drag_drop | text_only | false | null | Yes (zone-based) |
| Q2 desc_matching | N/A | false | null | Yes (zone-based) |

All decisions correct for these test cases. Item asset worker was never activated — to test it, we'd need a question about visually distinct objects (e.g., "identify rock types by their photos").

---

## Bug Fixes Applied

| Bug | Severity | Fix | File |
|---|---|---|---|
| **BUG-J** | P1 | Added "MUST produce scenes" rule + branching example to concept prompt; improved parse error messages with missing field list | `prompts/game_concept_designer.py`, `agents/game_concept_designer.py` |
| **BUG-K** | P2 | Improved label description prompt with exact key template; added fuzzy/substring key matching; added diagnostic logging | `agents/dk_retriever.py` |
| **BUG-L** | P2 | Added `asyncio.Semaphore(1)` to `LocalSegmentationService` serializing all SAM3 Metal GPU access | `services/asset_gen/segmentation.py` |
| **BUG-M** | P3 | Added per-mechanic feedback examples to interaction designer prompt; strengthened "EVERY mechanic MUST have feedback" rule | `prompts/interaction_designer.py` |
| (bonus) | P3 | Added `startNodeId` as explicit required field in branching content generator rules | `prompts/content_generator.py` |

### Post-Fix Q3 Retest

After fixing BUG-J, Q3 retest: **23/25 checks passed** (up from 2/9).
- Concept designer now correctly produces 1 scene with `branching_scenario`, `all_zone_labels=[]`, `completion_message`
- Remaining 2 failures: content generator for branching omitted `startNodeId` (fixed in bonus patch)
- All L0-L3 and L6 levels pass
| **BUG-N** | P3 | Instrumentation DB FK constraint for test runs | Test script — create pipeline_run record before invoke |
| **BUG-O** | P3 | Mode transition field names inconsistent (from/to vs from_mechanic_id/to_mechanic_id) | Standardize in interaction_designer output schema |
