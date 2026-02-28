# V4 Data Flow — Detailed Code-Level Trace with Examples

**Date**: 2026-02-17
**Companion to**: `45_v4_creative_data_flow_audit.md` (field-level summary)
**Test run data**: `backend/test_outputs/v4_stage_by_stage/` (Heart Anatomy game)

---

## How To Read This Document

Each level traces:
1. **Actual test data** — the real values from our Heart Anatomy test run
2. **Code path** — exact file:line where the transform happens
3. **What the downstream agent receives** — the actual input
4. **What it produces** — the actual output
5. **What gets dropped** — concrete values that are lost
6. **Silent fallbacks** — code that masks failures instead of surfacing them

---

## 1. GAME LEVEL

### 1.1 What game_concept_designer produced

```
Source: test_outputs/v4_stage_by_stage/01_game_concept_designer.json
```

The LLM produced a `GameConcept` with these game-level fields:

```json
{
  "title": "Heartbeat Journey",
  "subject": "Biology",
  "difficulty": "intermediate",
  "estimated_duration_minutes": 12,
  "narrative_theme": "Medical Exploration",
  "narrative_intro": "Welcome, aspiring cardiologist! Your mission is to navigate...",
  "completion_message": "Congratulations, you've mastered the heart's anatomy and function!...",
  "all_zone_labels": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle", "Veins", "Arteries"],
  "distractor_labels": ["Heart", "Blood", "Circulatory System"],
  "label_hierarchy": null,
  "scenes": [3 scenes]
}
```

### 1.2 How graph_builder transforms it

**Code path**: `graph_builder.py:132-145` — `build_game_graph()`:

```python
game_plan = GamePlan(
    title=concept.title,                           # "Heartbeat Journey" → ✅
    subject=concept.subject,                       # "Biology" → ✅
    difficulty=concept.difficulty,                  # "intermediate" → ✅
    estimated_duration_minutes=concept.estimated_duration_minutes,  # 12 → ✅
    narrative_theme=concept.narrative_theme,        # "Medical Exploration" → ✅
    narrative_intro=concept.narrative_intro,        # "Welcome, aspiring..." → ✅
    completion_message=concept.completion_message,  # "Congratulations..." → ✅
    all_zone_labels=concept.all_zone_labels,        # 6 labels → ✅
    distractor_labels=concept.distractor_labels,    # 3 distractors → ✅
    label_hierarchy=concept.label_hierarchy,        # null → ✅
    total_max_score=total_max_score,                # 295 (computed) → ✅
    scenes=scenes,                                  # 3 ScenePlans → ✅
)
```

**Result**: Graph builder is LOSSLESS at game level. Every GameConcept field makes it into GamePlan.

### 1.3 How assembler transforms GamePlan → Blueprint

**Code path**: `blueprint_assembler.py:79-127` — `assemble_blueprint()`:

```python
blueprint = {
    "templateType": "INTERACTIVE_DIAGRAM",
    "title": game_plan.get("title", ""),                        # "Heartbeat Journey" → ✅
    "narrativeIntro": _build_narrative(game_plan),              # "Welcome, aspiring..." → ✅
    "diagram": first.get("diagram", ...),                       # From scene 1 → ✅
    "labels": first.get("labels", []),                          # From scene 1 → ✅
    "distractorLabels": first.get("distractorLabels", []),      # From scene 1 → ✅
    "mechanics": all_mechanics,                                 # 4 mechanics → ✅
    "modeTransitions": all_transitions,                         # 1 transition → ✅
    "interactionMode": all_mechanics[0]["type"],                # "drag_drop" → ✅
    "scoringStrategy": {"base_points_per_zone": 10, "max_score": 295},
    "totalMaxScore": 295,                                       # → ✅
    "generation_complete": True,
}
```

**What the assembler DROPS from GamePlan (concrete values lost)**:

| Field | Value in GamePlan | Blueprint field | Status |
|---|---|---|---|
| `subject` | `"Biology"` | _(none)_ | **DROPPED** |
| `difficulty` | `"intermediate"` | _(none)_ | **DROPPED** |
| `estimated_duration_minutes` | `12` | _(none)_ | **DROPPED** |
| `narrative_theme` | `"Medical Exploration"` | _(none)_ | **DROPPED** |
| `completion_message` | `"Congratulations, you've mastered..."` | _(none)_ | **DROPPED** |
| `label_hierarchy` | `null` | _(none)_ | **DROPPED** |

### 1.4 Silent fallbacks at game level

**FB-G1**: `blueprint_assembler.py:88`
```python
"interactionMode": all_mechanics[0]["type"] if all_mechanics else "drag_drop",
```
If no mechanics exist (pipeline failure), silently defaults to `"drag_drop"`. Should raise.

**FB-G2**: `blueprint_assembler.py:91-92`
```python
"scoringStrategy": {
    "base_points_per_zone": _first_points_per_item(game_plan),  # scans for first mechanic
    "max_score": game_plan.get("total_max_score", 0),
}
```
`_first_points_per_item()` returns `10` as hardcoded default if no mechanics found. The `base_points_per_zone` name is also misleading — it's actually `points_per_item`.

**FB-G3**: `graph_builder.py:162-163`
```python
concept_raw = state.get("game_concept")
designs_raw = state.get("scene_creative_designs") or {}
```
If `scene_creative_designs` is missing from state, silently uses empty dict instead of failing. This means `_create_minimal_design()` fallback fires for EVERY scene.

---

## 2. SCENE LEVEL

### 2.1 What SceneConcept contains (Scene 1 example)

```
Source: 01_game_concept_designer.json → scenes[0]
```

```json
{
  "title": "Chambers of the Heart",
  "learning_goal": "Identify and describe the four chambers of the human heart.",
  "narrative_intro": "Your first task is to accurately label the heart's four main chambers...",
  "zone_labels": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle"],
  "needs_diagram": true,
  "image_description": "An anterior view diagram of the human heart, clearly showing the four chambers.",
  "mechanics": [
    {
      "mechanic_type": "drag_drop",
      "learning_purpose": "To test the learner's ability to spatially identify and label the four primary chambers...",
      "zone_labels_used": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle"],
      "expected_item_count": 4,
      "points_per_item": 10,
      "advance_trigger": "completion",
      "advance_trigger_value": null
    },
    {
      "mechanic_type": "description_matching",
      "learning_purpose": "To assess functional knowledge of each heart chamber immediately after identification...",
      "zone_labels_used": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle"],
      "expected_item_count": 4,
      "points_per_item": 15,
      "advance_trigger": "completion",
      "advance_trigger_value": null
    }
  ]
}
```

### 2.2 What scene_designer produced (Scene 1)

```
Source: 01_scene_designers.json → [0].design
```

The scene designer added these CREATIVE fields that didn't exist in the concept:

```json
{
  "visual_concept": "A clean, modern medical illustration style with a focus on clarity and anatomical accuracy...",
  "color_palette_direction": "Use a professional and calming palette with muted blues, grays, and subtle reds...",
  "spatial_layout": "The heart diagram occupies the central and primary focus of the screen...",
  "atmosphere": "Focused, educational, and precise, akin to a digital medical textbook...",
  "image_spec": {
    "description": "An anterior view, highly detailed, and anatomically accurate diagram of the human heart...",
    "must_include_structures": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle", "Superior Vena Cava", "Inferior Vena Cava", "Pulmonary Artery", "Pulmonary Veins", "Aorta"],
    "style": "clean_educational",
    "annotation_preference": "clean_unlabeled",
    "color_direction": "Use distinct, but subtle, color variations to differentiate the right (deoxygenated blood, e.g., muted blue/purple tones)...",
    "spatial_guidance": "The heart should be centrally positioned, slightly offset to the left..."
  },
  "mechanic_designs": [2 MechanicCreativeDesigns],
  "scene_narrative": "Welcome, future medical expert! Your journey into the human body begins with the heart...",
  "transition_narrative": "Excellent work! You've successfully identified the heart's chambers... Next, we'll trace the incredible journey of blood..."
}
```

### 2.3 How graph_builder copies creative into ScenePlan

**Code path**: `graph_builder.py:113-129` — `build_game_graph()`:

```python
scene_plan = ScenePlan(
    scene_id=scene_id,                       # "scene_1" (generated) → ✅
    scene_number=scene_number,               # 1 (generated) → ✅
    title=scene_concept.title,               # "Chambers of the Heart" → ✅
    learning_goal=scene_concept.learning_goal,  # "Identify and describe..." → ✅
    narrative_intro=scene_concept.narrative_intro or design.scene_narrative,
    #               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #               "Your first task is to accurately label..." (from concept)
    #               Falls back to design.scene_narrative ONLY if concept's is empty
    zone_labels=scene_concept.zone_labels,   # 4 labels → ✅
    needs_diagram=scene_concept.needs_diagram,  # true → ✅
    image_spec=design.image_spec,            # ImageSpec object → ✅
    second_image_spec=design.second_image_spec,  # null → ✅
    creative_design=design,                  # ENTIRE SceneCreativeDesign → ✅ STORED
    mechanics=mechanic_plans,                # 2 MechanicPlans → ✅
    mechanic_connections=connections,         # 1 connection (s1_m0 → s1_m1) → ✅
    starting_mechanic_id=mechanic_plans[0].mechanic_id,  # "s1_m0" → ✅
    transition_to_next=scene_transition,     # None (auto) → ✅
    scene_max_score=scene_max_score,         # 100 (40+60) → ✅
)
```

**Graph builder is LOSSLESS at scene level.** `creative_design=design` stores the ENTIRE SceneCreativeDesign.

### 2.4 How content dispatch router passes scene context to content generators

**Code path**: `routers.py:148-158` → `content_generator.py:125-183` (`build_scene_context()`):

```python
# routers.py:148-158
for scene in scenes:
    scene_context = build_scene_context(scene, dk)
    for mech in mechanics:
        send_payload = {
            "mechanic_plan": mech,       # Full MechanicPlan with creative_design
            "scene_context": scene_context,  # Reduced context (see below)
            "domain_knowledge": dk,
        }
```

**What `build_scene_context()` extracts** (`content_generator.py:125-183`):

```python
context = {
    "scene_id": "scene_1",              # ✅
    "title": "Chambers of the Heart",   # ✅
    "learning_goal": "Identify and describe...",  # ✅
    "zone_labels": ["Right Atrium", ...],  # ✅
    "other_mechanics": [{"mechanic_type": "drag_drop", "mechanic_id": "s1_m0"}, ...],  # ✅
    "dk_subset": {                       # ✅ Relevant DK
        "label_descriptions": {"Right Atrium": "...", ...},
        "canonical_labels": [...]
    },
    "visual_concept": "A clean, modern medical illustration style...",  # ✅ from creative_design
    "atmosphere": "Focused, educational, and precise...",               # ✅ from creative_design
}
```

**What `build_scene_context()` DROPS from ScenePlan.creative_design**:

| Field | Value | Status |
|---|---|---|
| `color_palette_direction` | `"Use a professional and calming palette with muted blues..."` | **DROPPED** — not extracted at line 178-182 |
| `spatial_layout` | `"The heart diagram occupies the central..."` | **DROPPED** — not extracted |
| `scene_narrative` | `"Welcome, future medical expert!..."` | **DROPPED** — not extracted |
| `transition_narrative` | `"Excellent work! You've successfully identified..."` | **DROPPED** — never read by anyone |
| `narrative_intro` (ScenePlan level) | `"Your first task is to accurately label..."` | **DROPPED** — not extracted |

### 2.5 How assembler converts ScenePlan → GameScene

**Code path**: `blueprint_assembler.py:588-613` — `_scene_to_game_scene()`:

```python
def _scene_to_game_scene(scene_bp: dict, index: int) -> dict:
    game_scene = {
        "scene_id": scene_bp.get("scene_id", ""),        # "scene_1" → ✅
        "title": scene_bp.get("title", ""),               # "Chambers of the Heart" → ✅
        "learning_goal": scene_bp.get("learning_goal", ""),  # "Identify and describe..." → ✅
        "diagram": scene_bp.get("diagram", {}),           # full diagram with zones → ✅
        "labels": scene_bp.get("labels", []),             # 4 labels → ✅
        "distractorLabels": scene_bp.get("distractorLabels", []),  # 3 distractors → ✅
    }
    # Copy mechanic configs
    for key in _CONFIG_KEYS:
        if key in scene_bp:
            game_scene[key] = scene_bp[key]  # dragDropConfig, descriptionMatchingConfig → ✅
    # Copy paths, identificationPrompts
    if "_transitions" in scene_bp:
        game_scene["modeTransitions"] = scene_bp["_transitions"]  # 1 transition → ✅
    return game_scene
```

**What the assembler DROPS from ScenePlan (concrete values lost)**:

| Field | Value in ScenePlan | Frontend GameScene field | Status |
|---|---|---|---|
| `scene_number` | `1` | `scene_number` (required in TS) | **DROPPED** — never set |
| `narrative_intro` | `"Your first task is to accurately label..."` | `narrative_intro` (RENDERED at GameSequenceRenderer.tsx:324) | **DROPPED** — never set |
| `scene_max_score` | `100` | `max_score` (required in TS) | **DROPPED** — never set |
| `mechanics` (built list) | `[{type:"drag_drop",...}, {type:"description_matching",...}]` | `mechanics` (expected in TS) | **DROPPED** — only stored in `_mechanics` internal key, cleaned up at line 124 |
| `starting_mechanic_id` | `"s1_m0"` | _(no field)_ | **DROPPED** |
| `creative_design.visual_concept` | `"A clean, modern medical illustration..."` | _(no field)_ | **DROPPED** |
| `creative_design.color_palette_direction` | `"Use a professional and calming palette..."` | _(no field)_ | **DROPPED** |
| `creative_design.atmosphere` | `"Focused, educational, and precise..."` | _(no field)_ | **DROPPED** |
| `creative_design.scene_narrative` | `"Welcome, future medical expert!..."` | _(no field)_ | **DROPPED** |
| `creative_design.transition_narrative` | `"Excellent work! You've successfully..."` | _(no field)_ | **DROPPED** |

**Actual blueprint scene output (what the frontend gets)**:

```json
{
  "scene_id": "scene_1",
  "title": "Chambers of the Heart",
  "learning_goal": "Identify and describe the four chambers of the human heart.",
  "diagram": { "assetUrl": "https://...", "assetPrompt": "...", "zones": [4 zones] },
  "labels": [4 labels],
  "distractorLabels": [3 distractors],
  "dragDropConfig": { ... 16 visual config fields ... },
  "descriptionMatchingConfig": { "descriptions": { "zone_right_atrium": "Receives deoxygenated blood..." }, ... },
  "modeTransitions": [{ "from": "s1_m0", "to": "s1_m1", "trigger": "all_zones_labeled" }]
}
```

**Missing** (frontend reads but gets `undefined`):
- `scene_number` — `undefined`
- `narrative_intro` — `undefined` → empty text on screen
- `max_score` — `undefined`
- `mechanics` — `undefined`
- `zones` (root-level) — `undefined` (only in `diagram.zones`)

### 2.6 Silent fallbacks at scene level

**FB-S1**: `graph_builder.py:55-66` — Missing design fallback
```python
design = scene_designs.get(scene_id)
if design is None:
    design = scene_designs.get(str(scene_idx))     # Try "0", "1"
    if design is None:
        design = scene_designs.get(f"s{scene_idx}")  # Try "s0", "s1"
if design is None:
    logger.warning(f"No creative design for {scene_id}, creating minimal design")
    design = _create_minimal_design(scene_id, scene_concept)
```
Three silent retries with alternate key formats, then creates a bare-bones design with:
- `visual_concept = "Clean educational layout"`
- `instruction_text = "Complete the drag_drop activity."`

This should FAIL, not silently generate a placeholder.

**FB-S2**: `graph_builder.py:182-185` — Invalid scene design skipped
```python
try:
    scene_designs[key] = SceneCreativeDesign(**design_raw)
except Exception as e:
    logger.warning(f"Failed to parse scene design {key}: {e}")
    # Silently skipped! design_raw not added, triggers FB-S1 later
```

**FB-S3**: `blueprint_assembler.py:217-226` — `_build_scene_blueprint()` wraps empty defaults
```python
result = {
    "scene_id": scene.get("scene_id", ""),
    "title": scene.get("title", ""),
    "learning_goal": scene.get("learning_goal", ""),
    ...
}
```
Every `.get(field, "")` silently defaults to empty string. If the scene is malformed, you get an empty scene that renders blank — no error.

---

## 3. MECHANIC LEVEL

### 3.1 What MechanicChoice contains (Scene 1, mechanic 0)

```
Source: 01_game_concept_designer.json → scenes[0].mechanics[0]
```

```json
{
  "mechanic_type": "drag_drop",
  "learning_purpose": "To test the learner's ability to spatially identify and label the four primary chambers of the heart on a diagram.",
  "zone_labels_used": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle"],
  "expected_item_count": 4,
  "points_per_item": 10,
  "advance_trigger": "completion",
  "advance_trigger_value": null,
  "is_timed": false,
  "time_limit_seconds": null
}
```

### 3.2 What scene_designer produced (MechanicCreativeDesign for drag_drop)

```
Source: 01_scene_designers.json → [0].design.mechanic_designs[0]
```

```json
{
  "mechanic_type": "drag_drop",
  "visual_style": "Draggable labels appear as clean, rectangular text boxes with a subtle shadow...",
  "card_type": "text_only",
  "layout_mode": "spatial",
  "connector_style": "none",
  "color_direction": "",
  "instruction_text": "Your first task: Accurately drag and drop the labels to identify each of the four main chambers of the human heart on the diagram.",
  "instruction_tone": "educational",
  "narrative_hook": "",
  "hint_strategy": "contextual",
  "feedback_style": "clinical",
  "difficulty_curve": "gradual",
  "generation_goal": "Generate four draggable text labels: 'Right Atrium', 'Right Ventricle', 'Left Atrium', 'Left Ventricle'...",
  "key_concepts": ["Heart Chambers", "Anatomy", "Spatial Identification"],
  "pedagogical_focus": "",
  "needs_item_images": false,
  "item_image_style": null
}
```

### 3.3 How graph_builder copies creative into MechanicPlan

**Code path**: `graph_builder.py:72-96`:

```python
creative = _find_mechanic_design(design, mech_idx, mech_choice)
plan = MechanicPlan(
    mechanic_id=mechanic_id,                  # "s1_m0" (generated)
    mechanic_type=mech_choice.mechanic_type,  # "drag_drop"
    zone_labels_used=mech_choice.zone_labels_used,  # 4 labels
    instruction_text=creative.instruction_text,      # "Your first task: Accurately drag and drop..."
    creative_design=creative,                 # ENTIRE MechanicCreativeDesign → ✅ STORED
    expected_item_count=mech_choice.expected_item_count,  # 4
    points_per_item=mech_choice.points_per_item,  # 10
    max_score=max_score,                      # 40 (4 × 10)
    is_timed=mech_choice.is_timed,            # false
    time_limit_seconds=mech_choice.time_limit_seconds,  # null
    is_terminal=(mech_idx == len(scene_concept.mechanics) - 1),  # false (not last)
    advance_trigger=mech_choice.advance_trigger,  # "completion"
)
```

**What graph_builder DROPS from MechanicChoice**:

| Field | Value | Status |
|---|---|---|
| `learning_purpose` | `"To test the learner's ability to spatially identify..."` | **DROPPED** — not copied to MechanicPlan |
| `advance_trigger_value` | `null` (but would be `0.8` for score_threshold triggers) | **DROPPED** — not in MechanicPlan schema, not in MechanicConnection.trigger_value |

### 3.4 How content_generator_prompt reads creative_design

**Code path**: `content_generator.py:48-55` sends full `mechanic_plan` to `build_content_prompt()`.

**Code path**: `prompts/content_generator.py:45-80` — `_build_header()`:

```python
lines = [
    "You are an expert educational content generator.",
    "",
    f"## Scene: {scene_context.get('title', 'Untitled')}",         # "Chambers of the Heart"
    f"- Scene ID: {scene_context.get('scene_id', 'unknown')}",     # "scene_1"
    f"- Learning Goal: {scene_context.get('learning_goal', '')}",   # "Identify and describe..."
    "",
    "## Creative Direction",
    f"- Visual Style: {creative_design.get('visual_style', 'educational')}",  # ✅ "Draggable labels appear..."
    f"- Generation Goal: {creative_design.get('generation_goal', '')}",       # ✅ "Generate four draggable..."
    f"- Key Concepts: {', '.join(creative_design.get('key_concepts', []))}",  # ✅ "Heart Chambers, Anatomy..."
    f"- Pedagogical Focus: {creative_design.get('pedagogical_focus', '')}",   # ✅ "" (empty)
    f"- Card Type: {creative_design.get('card_type', 'text_only')}",          # ✅ "text_only"
    f"- Layout Mode: {creative_design.get('layout_mode', 'default')}",        # ✅ "spatial"
    f"- Hint Strategy: {creative_design.get('hint_strategy', 'progressive')}",  # ✅ "contextual"
    f"- Feedback Style: {creative_design.get('feedback_style', 'encouraging')}",  # ✅ "clinical"
]
```

**What the content prompt header DROPS from MechanicCreativeDesign**:

| Field | Value | Why it matters |
|---|---|---|
| `color_direction` | `""` (empty this time, but could be rich) | Unused — no line in header reads it |
| `instruction_text` | `"Your first task: Accurately drag and drop..."` | NOT in content prompt at all. Content generator doesn't know what the player will be told. |
| `instruction_tone` | `"educational"` | NOT in prompt — tone guidance for content lost |
| `narrative_hook` | `""` | NOT in prompt |
| `difficulty_curve` | `"gradual"` | NOT in prompt — should influence item difficulty ordering |
| `connector_style` | `"none"` | Read by `_drag_drop_prompt()` but NOT by header |
| `needs_item_images` | `false` | NOT in prompt |

**Then the per-mechanic template** (`_drag_drop_prompt()`, line 83-131) reads:
- `creative.get("layout_mode")` → "spatial" → maps to `tray_position: "bottom"` via `_layout_to_tray()`
- `creative.get("connector_style")` → "none" → maps to `leader_line_style: "none"` via `_connector_to_line()`
- `creative.get("feedback_style")` → "clinical" → maps to `feedback_timing: "deferred"` via `_feedback_to_timing()`
- `creative.get("card_type")` → "text_only" → maps to `label_style: "text_only"`

### 3.5 What content_generator produced

```
Source: 01_content_generators.json → mechanic_contents[0] (s1_m0 drag_drop)
```

```json
{
  "labels": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle"],
  "distractor_labels": ["Aorta", "Pulmonary Artery"],
  "interaction_mode": "drag_drop",
  "feedback_timing": "deferred",
  "label_style": "text_only",
  "leader_line_style": "none",
  "leader_line_color": "",
  "leader_line_animate": true,
  "pin_marker_shape": "circle",
  "label_anchor_side": "auto",
  "tray_position": "bottom",
  "tray_layout": "horizontal",
  "placement_animation": "spring",
  "incorrect_animation": "shake",
  "zone_idle_animation": "pulse",
  "zone_hover_effect": "highlight",
  "max_attempts": null,
  "shuffle_labels": true
}
```

### 3.6 How assembler maps content → blueprint config

**Code path**: `blueprint_assembler.py:263-287`:

```python
if mtype == "drag_drop":
    config = {"leader_line_style": "curved", "tray_position": "bottom", "placement_animation": "snap"}
    # ^^^ HARDCODED DEFAULTS that get overwritten below
    for key in _DRAG_DROP_CONFIG_KEYS:
        if key in content:
            config[key] = content[key]
    scene_bp["dragDropConfig"] = config
```

**Actual blueprint dragDropConfig output**:

```json
{
  "leader_line_style": "none",        // From content (overrode "curved" default)
  "tray_position": "bottom",          // From content
  "placement_animation": "spring",    // From content (overrode "snap" default)
  "incorrect_animation": "shake",     // From content
  "max_attempts": null,               // From content
  "leader_line_color": "",            // From content
  "zone_hover_effect": "highlight",   // From content
  "leader_line_animate": true,        // From content
  "label_style": "text_only",         // From content
  "feedback_timing": "deferred",      // From content (driven by creative.feedback_style="clinical")
  "label_anchor_side": "auto",        // From content
  "zone_idle_animation": "pulse",     // From content
  "tray_layout": "horizontal",        // From content
  "shuffle_labels": true,             // From content
  "interaction_mode": "drag_drop",    // From content
  "pin_marker_shape": "circle"        // From content
}
```

**All 16 visual config fields flow through.** The content → assembler → blueprint path is COMPLETE for mechanic configs.

### 3.7 What mechanics[] in blueprint DOESN'T include

**Code path**: `blueprint_assembler.py:193-209`:

```python
mechanic_entry = {
    "type": mtype,           # "drag_drop"
    "config": {},            # ALWAYS EMPTY — configs go to dragDropConfig etc.
    "scoring": scoring_by_mech.get(mid, {...fallback...}),
    "feedback": feedback_by_mech.get(mid, {...fallback...}),
}
```

**What's missing from each mechanic entry**:

| Field | Available in MechanicPlan | Frontend Mechanic interface | Status |
|---|---|---|---|
| `instruction_text` | `"Your first task: Accurately drag and drop..."` | No direct field, but SequenceConfig has `instructionText` | **DROPPED** |
| `mechanic_id` | `"s1_m0"` | Not in interface | **DROPPED** (but could be useful for debugging) |

### 3.8 Silent fallbacks at mechanic level

**FB-M1**: `graph_builder.py:229-250` — Missing mechanic design
```python
def _find_mechanic_design(scene_design, mech_idx, mech_choice):
    designs = scene_design.mechanic_designs
    if mech_idx < len(designs):
        design = designs[mech_idx]
        if design.mechanic_type == mech_choice.mechanic_type:
            return design
    for design in designs:
        if design.mechanic_type == mech_choice.mechanic_type:
            return design
    # FALLBACK: creates bare-bones MechanicCreativeDesign
    logger.warning(f"No creative design for {mech_choice.mechanic_type}...")
    return MechanicCreativeDesign(
        mechanic_type=mech_choice.mechanic_type,
        visual_style="clean educational",
        instruction_text=f"Complete the {mech_choice.mechanic_type.replace('_', ' ')} activity.",
        generation_goal=f"Generate {mech_choice.mechanic_type} content for the learning activity.",
    )
```
This means a GENERIC instruction like "Complete the drag_drop activity." replaces the scene designer's carefully crafted one. Should FAIL.

**FB-M2**: `blueprint_assembler.py:196-208` — Missing scoring/feedback
```python
"scoring": scoring_by_mech.get(mid, {
    "strategy": "per_correct",          # HARDCODED
    "points_per_correct": mp.get("points_per_item", 10),  # 10 HARDCODED default
    "max_score": mp.get("max_score", 0),
    "partial_credit": True,             # HARDCODED
}),
"feedback": feedback_by_mech.get(mid, {
    "on_correct": "Correct!",           # HARDCODED
    "on_incorrect": "Try again.",        # HARDCODED
    "on_completion": "Well done!",       # HARDCODED
    "misconceptions": [],               # HARDCODED
}),
```
If interaction_designer fails or doesn't produce scoring for this mechanic_id, you get hardcoded generic text with zero misconception awareness.

**FB-M3**: `blueprint_assembler.py:265-270` — Hardcoded config defaults before content override
```python
config = {
    "leader_line_style": "curved",    # Overwritten if content has it
    "tray_position": "bottom",        # Overwritten if content has it
    "placement_animation": "snap",    # Overwritten if content has it
}
```
These defaults are unnecessary — if content is missing entirely, the whole dragDropConfig should be absent, not silently filled with defaults.

**FB-M4**: `interaction_designer.py:85-117` — LLM failure fallback
```python
except Exception as e:
    logger.error(f"Interaction design failed for {scene_id}: {e}")
    fallback_scoring = {}
    fallback_feedback = {}
    for mp in mechanics:
        mid = mp.get("mechanic_id")
        fallback_scoring[mid] = {
            "strategy": "per_correct",         # HARDCODED
            "points_per_correct": mp.get("points_per_item", 10),  # 10 HARDCODED
            "max_score": mp.get("max_score", 0),
            "partial_credit": True,            # HARDCODED
        }
        fallback_feedback[mid] = {
            "on_correct": "Correct!",          # HARDCODED GENERIC
            "on_incorrect": "Try again.",       # HARDCODED GENERIC
            "on_completion": "Well done!",      # HARDCODED GENERIC
            "misconceptions": [],              # EMPTY — no misconception awareness
        }
    return {"interaction_results_raw": [{..., "status": "degraded"}]}
```
When LLM fails, misconceptions are completely lost and feedback is generic. The game works but provides zero educational value from feedback.

**FB-M5**: `content_generator.py:71-87` — Pydantic parse failure
```python
try:
    parsed = content_model(**raw)
except Exception as parse_err:
    return {"mechanic_contents_raw": [{..., "status": "failed", "content": {}}]}
```
Failed content parse returns empty dict. The assembler then creates a mechanic with empty config. The game will render with no content.

---

## 4. ASSET LEVEL

### 4.1 What asset_worker receives

**Code path**: `routers.py:227-242` — `asset_send_router()`:

```python
send_payload = {
    "scene_id": "scene_1",
    "image_spec": {
        "description": "An anterior view, highly detailed, and anatomically accurate diagram...",
        "must_include_structures": ["Right Atrium", "Right Ventricle", ...9 items],
        "style": "clean_educational",
        "annotation_preference": "clean_unlabeled",
        "color_direction": "Use distinct, but subtle, color variations...",
        "spatial_guidance": "The heart should be centrally positioned..."
    },
    "zone_labels": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle"],
    "question_text": "Heart anatomy: label the four chambers..."
}
```

### 4.2 What asset_worker uses from image_spec

**Code path**: `asset_dispatcher.py:177-199` — `_search_image()`:

```python
description = image_spec.get("description", "")         # ✅ USED in search query
required = image_spec.get("must_include_structures", []) # ✅ USED (appended to query, first 5)
# Build search queries
search_query = question_text or description
if required:
    search_query += " " + " ".join(required[:5])
```

**What asset_worker DROPS from image_spec**:

| Field | Value | Status |
|---|---|---|
| `style` | `"clean_educational"` | **DROPPED** — not used in search |
| `annotation_preference` | `"clean_unlabeled"` | **DROPPED** — not used |
| `color_direction` | `"Use distinct, but subtle, color variations..."` | **DROPPED** — not used |
| `spatial_guidance` | `"The heart should be centrally positioned..."` | **DROPPED** — not used |

These would be relevant for image generation (DALL-E/Flux) but are wasted in search mode.

### 4.3 Asset pipeline stages (Scene 1)

1. **Image search**: Serper API → found `https://www.ptdirect.com/images/...`
2. **Zone detection**: Gemini Flash → 4 bounding boxes (Right Atrium, Right Ventricle, Left Atrium, Left Ventricle)
3. **SAM3 refinement**: Gemini boxes as guide → 4 pixel-precise polygons (33, 34, 35, 21 points)
4. **Quality validation**: 4/4 labels matched → match_quality = 1.0

### 4.4 What assembler uses from asset result

**Code path**: `blueprint_assembler.py:149-165`:

```python
if asset and asset.get("status") == "success" and asset.get("zones"):
    detected_zones = postprocess_zones(asset["zones"])                    # ✅ zones[]
    label_to_zone_id = match_labels_to_zones(zone_labels, detected_zones) # ✅ label→zoneId mapping
    zones = _build_zones(detected_zones, label_to_zone_id, ...)           # ✅ blueprint zones

diagram = {
    "assetUrl": asset.get("diagram_url"),      # ✅ "https://www.ptdirect.com/..."
    "assetPrompt": scene.get("image_spec", {}).get("description", ""),  # ✅ image_spec.description
    "zones": zones,                             # ✅ 4 zones with SAM3 polygons
}
```

**What assembler DROPS from asset result**:

| Field | Value | Status |
|---|---|---|
| `match_quality` | `1.0` | **DROPPED** — logged only, not in blueprint |

### 4.5 Silent fallbacks at asset level

**FB-A1**: `asset_dispatcher.py:62-85` — No image found, try fallback
```python
if not diagram_url:
    logger.warning(f"No image found for scene {scene_id}, trying fallback")
    diagram_url = await _fallback_image_search(image_spec)
if not diagram_url:
    result = _error_result(scene_id, "No diagram image found after search + fallback")
    return result
```
Two search attempts before reporting error. The fallback uses a simplified query (`description + "labeled diagram"`). This is acceptable but the first failure should be surfaced as a sub_stage status.

**FB-A2**: `asset_dispatcher.py:106-109` — No zones detected
```python
if not zones:
    result = _error_result(scene_id, "Zone detection returned no zones")
    return result
```
Returns error status — good. But the overall asset_worker wraps this in `generated_assets_raw` with `"status": "error"`, and then the assembler creates synthetic empty zones (line 154-158):

```python
elif has_zone_mechanic:
    for label in zone_labels:
        zid = generate_zone_id(scene_number, label)
        label_to_zone_id[label] = zid
    zones = [{"id": zid, "label": label, "points": []} for label, zid in label_to_zone_id.items()]
```
This creates zones with EMPTY `points: []` — the game renders clickable regions with no visible area. Should surface as a warning.

**FB-A3**: `asset_dispatcher.py:370-377` — SAM3 failure
```python
except Exception as e:
    logger.warning(f"SAM3 refinement failed, keeping Gemini zones: {e}")
    return gemini_zones
```
Falls back to Gemini boxes silently. The sub_stage status shows "degraded" but the parent status stays "success".

**FB-A4**: `asset_dispatcher.py:138-139` — Low match quality
```python
if match_quality < 0.3:
    logger.warning(f"Low match quality for {scene_id}: {match_quality:.2f}")
```
Warns but still returns `"status": "success"`. A game with 30% zone match will render with most zones misaligned. Should be "degraded".

---

## 5. MODE TRANSITIONS (Cross-mechanic wiring)

### 5.1 How advance_trigger flows through

```
MechanicChoice.advance_trigger = "completion"
                ↓ (graph_builder.py:94)
MechanicPlan.advance_trigger = "completion"
                ↓ (graph_builder.py:205 — _build_connections)
resolve_trigger("completion", "drag_drop")  →  "all_zones_labeled"
                ↓
MechanicConnection.trigger = "all_zones_labeled"
                ↓ (interaction_designer or assembler._build_transitions)
ModeTransition.trigger = "all_zones_labeled"
```

**BUG**: `MechanicChoice.advance_trigger_value` (e.g. `0.8` for score_threshold) is NEVER copied:
- Not in `MechanicPlan` schema (no field for it)
- Not in `_build_connections()` → `MechanicConnection.trigger_value` stays `None`
- Blueprint gets `"trigger_value": null`

### 5.2 Actual modeTransition in blueprint

```json
{
  "from": "s1_m0",
  "to": "s1_m1",
  "trigger": "all_zones_labeled",
  "trigger_value": null,
  "animation": "fade",
  "message": null
}
```

**BUG**: `from`/`to` use mechanic IDs (`"s1_m0"`, `"s1_m1"`) but frontend `ModeTransition.from`/`to` expects `InteractionMode` types (`"drag_drop"`, `"description_matching"`).

This is because `_build_transitions()` (line 552-585) uses mechanic_type:
```python
transitions.append({
    "from": from_type,     # "drag_drop"
    "to": to_type,         # "description_matching"
    ...
})
```

But when interaction_designer produces transitions (the preferred path), the `ModeTransitionOutput` schema uses `from_mode`/`to_mode` which the interaction_designer sets to mechanic_ids not mechanic_types. The interaction_designer prompt shows `"from_mode": "drag_drop"` in the example but the LLM may produce mechanic_ids.

In our test, the interaction_designer produced:
```json
{ "from_mode": "s1_m0", "to_mode": "s1_m1", "trigger": "all_zones_labeled" }
```

The assembler prefers the interaction_designer output (line 212-213):
```python
transitions = interaction.get("mode_transitions", [])
if not transitions:
    transitions = _build_transitions(scene, mechanics_plans)  # Fallback
```

So the blueprint gets `"from": "s1_m0"` instead of `"from": "drag_drop"`. **This is a BUG** — the frontend expects mechanic types, not IDs.

---

## 6. SILENT FALLBACK INVENTORY (Remove-or-Surface Plan)

### Category 1: REMOVE — Replace with explicit failure

| ID | Location | Current behavior | Proposed |
|---|---|---|---|
| FB-G1 | `blueprint_assembler.py:88` | No mechanics → default "drag_drop" | Raise AssemblyError("No mechanics in game plan") |
| FB-S1 | `graph_builder.py:55-66` | No design → _create_minimal_design | Raise ValueError(f"No creative design for {scene_id}") |
| FB-M1 | `graph_builder.py:229-250` | No mechanic design → minimal | Raise ValueError(f"No creative design for {mechanic_type}") |
| FB-M3 | `blueprint_assembler.py:265-270` | Hardcoded config defaults | Remove defaults dict, start from {} |
| FB-G2 | `blueprint_assembler.py:91-92` | _first_points_per_item returns 10 | Read from game_plan.scenes[0].mechanics[0] or raise |

### Category 2: SURFACE — Set status to "degraded" and include warnings

| ID | Location | Current behavior | Proposed |
|---|---|---|---|
| FB-S2 | `graph_builder.py:182-185` | Invalid design silently skipped | Add to `assembly_warnings`, set `is_degraded=True` |
| FB-S3 | `blueprint_assembler.py:217-226` | Empty defaults for missing scene fields | Add warning: "Scene {id} missing {field}" |
| FB-M2 | `blueprint_assembler.py:196-208` | Hardcoded scoring/feedback fallback | Set mechanic status "degraded", add warning |
| FB-M4 | `interaction_designer.py:85-117` | Hardcoded fallback on LLM failure | Already returns `"status": "degraded"` — good. Add `assembly_warnings` |
| FB-M5 | `content_generator.py:71-87` | Empty content on parse failure | Already returns `"status": "failed"` — good. Assembler should skip this mechanic and warn |
| FB-A2 | `blueprint_assembler.py:154-158` | Synthetic empty zones | Add warning: "Scene {id} has empty zone polygons" |
| FB-A3 | `asset_dispatcher.py:370-377` | SAM3 failure → keep Gemini zones | Already reports "degraded" sub_stage — good |
| FB-A4 | `asset_dispatcher.py:138-139` | Low match quality → "success" | Change to "degraded" when match_quality < 0.5 |

### Category 3: KEEP — Acceptable graceful degradation

| ID | Location | Rationale |
|---|---|---|
| FB-A1 | `asset_dispatcher.py:62-85` | Fallback image search is a valid second attempt, both recorded as sub_stages |
| FB-A3 | `asset_dispatcher.py:370-377` | SAM3 is optional refinement; Gemini zones are valid |
| All `state.get(field) or {}` in routers | `routers.py` various | State may legitimately be empty on first pass of reducer; these prevent AttributeError during routing |

---

## 7. BUG SUMMARY

| # | Bug | Location | Impact |
|---|---|---|---|
| BUG-A | `advance_trigger_value` dropped | `graph_builder.py:82-95` — not in MechanicPlan | Score-threshold triggers have no threshold |
| BUG-B | `modeTransition.from/to` uses mechanic IDs not types | `interaction_designer` output + assembler passthrough | Frontend can't match transition triggers to mechanic types |
| BUG-C | `GameScene.narrative_intro` not set | `blueprint_assembler.py:588-613` | Empty scene intro text |
| BUG-D | `GameScene.scene_number` not set | `blueprint_assembler.py:588-613` | Undefined scene numbers |
| BUG-E | `GameScene.max_score` not set | `blueprint_assembler.py:588-613` | Undefined per-scene scoring |
| BUG-F | `GameScene.mechanics[]` not set | `blueprint_assembler.py:588-613` | Frontend can't derive starting mode per scene |
| BUG-G | `instruction_text` dropped at assembler | `blueprint_assembler.py:193-209` | Player sees no instructions |
| BUG-H | `completion_message` dropped at assembler | `blueprint_assembler.py:79-127` | No end-of-game message |
| BUG-I | `GameScene.zones` not at root level | `blueprint_assembler.py:588-613` | Only in `diagram.zones`, TS type expects root `zones` |
