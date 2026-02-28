# V3 Pipeline Implementation Plan v2

> Based on: 16_master_findings_v2.md, 15 research documents, 5 code audits, mechanic redesign document.
> Date: February 11, 2026
> Priority mechanics: drag_drop, sequencing, sorting_categories, memory_match, click_to_identify, trace_path

---

## Overview

9 phases, ~370+ issues addressed. Phases 0-3 are sequential (dependency chain). Phases 4-6 can run in parallel after Phase 3. Phase 7-8 are optional/deferred.

```
Phase 0: Critical Infrastructure (image serving, retry, state)     [BLOCKING]
    ↓
Phase 1: Schema Expansion (Pydantic + TypeScript types)            [BLOCKING]
    ↓
Phase 2: Tool Implementation (generate_mechanic_content handlers)  [BLOCKING]
    ↓
Phase 3: Agent Prompt Rewrites (partially done)                    [BLOCKING]
    ↓
    ├── Phase 4: Blueprint Assembler Fixes                         [PARALLEL]
    ├── Phase 5: Frontend Schema + Zustand                         [PARALLEL]
    └── Phase 6: Frontend Component Enhancements                   [PARALLEL]

Phase 7: Hierarchical Chaining (MechanicDAG)                       [DEFERRED]
Phase 8: New Mechanics (hotspot_multi_select, cloze, etc.)         [DEFERRED]
```

**Estimated total: ~1800 lines across ~30 files for Phases 0-6.**

---

## Phase 0: Critical Infrastructure

> Fix pipeline-blocking bugs that prevent ANY game from working correctly.
> ~80 lines across ~6 files. Must be done FIRST.

### Fix 0.1: V3 Image Serving Route

**Problem:** No route serves V3-generated images. Frontend gets local file paths → broken images.
**Files:** `backend/app/routes/generate.py`

Add new route:
```python
@router.get("/assets/v3/{run_id}/{filename}")
async def serve_v3_asset(run_id: str, filename: str):
    """Serve V3-generated images."""
    asset_path = Path("pipeline_outputs/v3_assets") / run_id / filename
    if not asset_path.exists():
        raise HTTPException(404, f"Asset not found: {filename}")
    return FileResponse(asset_path)
```

In blueprint serve endpoint, rewrite ALL image URLs in `game_sequence.scenes[].diagram`:
```python
# Rewrite V3 asset URLs
if blueprint.get("game_sequence"):
    for scene in blueprint["game_sequence"].get("scenes", []):
        diagram = scene.get("diagram", {})
        for key in ("assetUrl", "cleanedUrl", "originalUrl"):
            url = diagram.get(key, "")
            if url and ("pipeline_outputs" in url or url.startswith("/")):
                filename = Path(url).name
                diagram[key] = f"/api/assets/v3/{process_id}/{filename}"
```

### Fix 0.2: Retry Count Off-by-One

**Problem:** Validators increment counter BEFORE router reads it. `>= 2` check means 1 retry, not 2.
**Files:** `backend/app/agents/graph.py`

Change in all 3 validation routers (`_v3_design_validation_router`, `_v3_scene_validation_router`, `_v3_interaction_validation_router`):
```python
# Before:
if retry_count >= 2:
# After:
if retry_count >= 3:
```

### Fix 0.3: DomainKnowledge TypedDict Mismatch

**Problem:** TypedDict version missing `query_intent`, `suggested_reveal_order`, `scene_hints`. These exist in Pydantic version but lost in state propagation.
**File:** `backend/app/agents/state.py`

Add missing fields to the DomainKnowledge TypedDict (around L321-331):
```python
query_intent: Optional[str]
suggested_reveal_order: Optional[List[str]]
scene_hints: Optional[List[str]]
```

### Fix 0.4: _build_agent_outputs for V3

**Problem:** `_build_agent_outputs()` does NOT record V3 agent outputs. Pipeline JSON lacks V3 data.
**File:** `backend/app/routes/generate.py` (around L220-273)

Add V3 agent output extraction:
```python
# V3 outputs
if final_state.get("game_design_v3"):
    agent_outputs["game_designer_v3"] = final_state["game_design_v3"]
if final_state.get("scene_specs_v3"):
    agent_outputs["scene_architect_v3"] = final_state["scene_specs_v3"]
if final_state.get("interaction_specs_v3"):
    agent_outputs["interaction_designer_v3"] = final_state["interaction_specs_v3"]
if final_state.get("generated_assets_v3"):
    agent_outputs["asset_generator_v3"] = final_state["generated_assets_v3"]
```

### Fix 0.5: Topology Metadata

**Problem:** `save_pipeline_run()` hardcodes `topology="T1"` for V3.
**File:** `backend/app/routes/generate.py`

```python
# Before:
topology="T1"
# After:
topology=pipeline_preset or "T1"
```

### Fix 0.6: Remove Bloom's from Mechanic Selection

**Problem:** `analyze_pedagogy` in game_design_v3_tools.py (L108-111) forces drag_drop baseline based on Bloom's level. Bloom's should be informational context only.
**File:** `backend/app/tools/game_design_v3_tools.py`

Remove the forced `baseline_mechanic = "drag_drop"` logic. Keep Bloom's analysis as informational text in the output but don't use it to constrain mechanic selection.

---

## Phase 1: Schema Expansion

> Expand all Pydantic schemas and TypeScript types to support rich mechanic configs.
> ~400 lines across ~6 files. Blocking for Phases 2-4.

### Fix 1.1: Expand SequenceDesign (backend)

**File:** `backend/app/agents/schemas/game_design_v3.py`

```python
class SequenceItem(BaseModel):
    id: str
    text: str
    description: Optional[str] = None
    image: Optional[str] = None           # URL/path to illustration
    icon: Optional[str] = None            # Emoji or icon identifier
    category: Optional[str] = None        # Grouping category
    is_distractor: bool = False
    order_index: Optional[int] = None     # Correct position (0-based)

class SequenceDesign(BaseModel):
    correct_order: List[str] = Field(default_factory=list)
    items: List[SequenceItem] = Field(default_factory=list)
    sequence_type: str = "linear"         # linear, cyclic, branching
    layout_mode: str = "horizontal_timeline"  # horizontal_timeline, vertical_list, circular_cycle, flowchart, insert_between
    interaction_pattern: str = "drag_reorder"  # drag_reorder, drag_to_slots, click_to_swap, number_typing
    card_type: str = "text_only"          # text_only, text_with_icon, image_with_caption, image_only
    connector_style: str = "arrow"        # arrow, line, numbered, none
    show_position_numbers: bool = True
    allow_distractors: bool = False
    instructions: str = "Arrange the items in the correct order."
```

### Fix 1.2: Expand SortingDesign (backend)

**File:** `backend/app/agents/schemas/game_design_v3.py`

```python
class SortingCategoryDesign(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class SortingItemDesign(BaseModel):
    id: str
    text: str
    correct_category_ids: List[str] = Field(default_factory=list)  # LIST not singular
    description: Optional[str] = None
    image: Optional[str] = None
    difficulty: Optional[str] = None      # easy, medium, hard

class SortingDesign(BaseModel):
    categories: List[SortingCategoryDesign] = Field(default_factory=list)
    items: List[SortingItemDesign] = Field(default_factory=list)
    sort_mode: str = "bucket"             # bucket, venn_2, venn_3, matrix, column
    item_card_type: str = "text_only"     # text_only, text_with_icon, image_with_caption
    container_style: str = "bucket"       # bucket, labeled_bin, circle, cell, column
    submit_mode: str = "batch_submit"     # batch_submit, immediate_feedback, round_based
    allow_multi_category: bool = False
    max_attempts: int = 3
    show_category_hints: bool = True
    instructions: str = "Sort each item into the correct category."
```

### Fix 1.3: Expand MemoryMatchDesign (backend)

**File:** `backend/app/agents/schemas/game_design_v3.py`

```python
class MemoryPairDesign(BaseModel):
    id: str
    term: str
    definition: str
    front_type: str = "text"              # text, image
    back_type: str = "text"
    explanation: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    zone_id: Optional[str] = None         # For diagram_region_to_label variant

class MemoryMatchDesign(BaseModel):
    pairs: List[MemoryPairDesign] = Field(default_factory=list)
    game_variant: str = "classic"         # classic, column_match, scatter, progressive, peek
    match_type: str = "term_to_definition"  # identical, term_to_definition, image_to_label, concept_to_example, diagram_region_to_label
    grid_size: Optional[str] = None       # "4x3" etc, auto if None
    card_back_style: str = "pattern"      # solid, gradient, pattern, question_mark, custom
    matched_card_behavior: str = "fade"   # fade, shrink, collect, checkmark
    show_explanation_on_match: bool = True
    mismatch_penalty: str = "none"        # none, score_decay, life_loss, time_penalty
    instructions: str = "Find all matching pairs."
```

### Fix 1.4: Expand CompareDesign (backend)

**File:** `backend/app/agents/schemas/game_design_v3.py`

```python
class CompareDesign(BaseModel):
    expected_categories: List[Dict[str, Any]] = Field(default_factory=list)
    subjects: List[str] = Field(default_factory=list)  # ["Plant Cell", "Animal Cell"]
    comparison_mode: str = "side_by_side"  # side_by_side, slider, overlay_toggle, venn, spot_difference
    category_types: List[str] = Field(default_factory=lambda: ["similar", "different", "unique_a", "unique_b"])
    exploration_enabled: bool = False
    zoom_enabled: bool = False
    instructions: str = "Compare and categorize the differences and similarities."
```

### Fix 1.5: Expand BranchingDesign (backend)

**File:** `backend/app/agents/schemas/game_design_v3.py`

```python
class BranchingChoiceDesign(BaseModel):
    text: str
    next_node_id: str
    is_correct: Optional[bool] = None
    quality: Optional[str] = None         # optimal, acceptable, suboptimal, harmful
    consequence_text: Optional[str] = None

class BranchingNodeDesign(BaseModel):
    id: str
    prompt: str
    narrative_text: Optional[str] = None
    node_type: str = "decision"           # decision, info, ending, checkpoint
    choices: List[BranchingChoiceDesign] = Field(default_factory=list)
    ending_type: Optional[str] = None     # good, neutral, bad

class BranchingDesign(BaseModel):
    nodes: List[BranchingNodeDesign] = Field(default_factory=list)
    start_node_id: str = ""
    narrative_structure: str = "linear"   # linear, branching, foldback
    instructions: str = "Make decisions to navigate the scenario."
```

### Fix 1.6: Expand SlimMechanicRef

**Problem:** `SlimMechanicRef` has ONLY `type: str`. Zero mechanic config flows through Phase 1 validation.
**File:** `backend/app/agents/schemas/game_design_v3.py`

```python
class SlimMechanicRef(BaseModel):
    type: str
    config_hint: Dict[str, Any] = Field(default_factory=dict)  # Summary of key config
    zone_labels_used: List[str] = Field(default_factory=list)
```

### Fix 1.7: Expand Frontend TypeScript Types

**File:** `frontend/src/components/templates/InteractiveDiagramGame/types.ts`

Add 3 missing config interfaces:
```typescript
export interface ClickToIdentifyConfig {
  promptStyle: 'naming' | 'functional';
  selectionMode: 'sequential' | 'any_order';
  highlightStyle: 'subtle' | 'outlined' | 'invisible';
  magnificationEnabled: boolean;
  magnificationFactor: number;
  exploreModeEnabled: boolean;
  exploreTimeLimitSeconds: number | null;
  showZoneCount: boolean;
}

export interface TracePathConfig {
  pathType: 'linear' | 'branching' | 'circular';
  drawingMode: 'click_waypoints' | 'freehand';
  particleTheme: 'dots' | 'arrows' | 'droplets' | 'cells' | 'electrons';
  particleSpeed: 'slow' | 'medium' | 'fast';
  colorTransitionEnabled: boolean;
  showDirectionArrows: boolean;
  showWaypointLabels: boolean;
  showFullFlowOnComplete: boolean;
}

export interface DragDropConfig {
  showLeaderLines: boolean;
  snapAnimation: 'spring' | 'ease' | 'none';
  showInfoPanelOnCorrect: boolean;
}
```

Extend existing interfaces with missing fields (add optional fields with defaults — backward compatible):

```typescript
// SequenceConfig additions
layout_mode?: 'horizontal_timeline' | 'vertical_list' | 'circular_cycle' | 'flowchart';
interaction_pattern?: 'drag_reorder' | 'drag_to_slots' | 'click_to_swap';
card_type?: 'text_only' | 'text_with_icon' | 'image_with_caption';
connector_style?: 'arrow' | 'line' | 'numbered' | 'none';

// SortingConfig additions
sort_mode?: 'bucket' | 'venn_2' | 'venn_3' | 'matrix' | 'column';
item_card_type?: 'text_only' | 'text_with_icon' | 'image_with_caption';
container_style?: 'bucket' | 'labeled_bin' | 'circle' | 'cell' | 'column';
submit_mode?: 'batch_submit' | 'immediate_feedback' | 'round_based';
allow_multi_category?: boolean;

// MemoryMatchConfig additions
game_variant?: 'classic' | 'column_match' | 'scatter' | 'progressive' | 'peek';
match_type?: 'term_to_definition' | 'image_to_label' | 'diagram_region_to_label';
card_back_style?: 'solid' | 'gradient' | 'pattern' | 'question_mark';
matched_card_behavior?: 'fade' | 'shrink' | 'collect' | 'checkmark';
show_explanation_on_match?: boolean;

// BranchingConfig additions
narrative_structure?: 'linear' | 'branching' | 'foldback';
// DecisionNode additions
node_type?: 'decision' | 'info' | 'ending' | 'checkpoint';
narrative_text?: string;
// DecisionOption additions
quality?: 'optimal' | 'acceptable' | 'suboptimal' | 'harmful';
consequence_text?: string;

// CompareConfig additions
comparison_mode?: 'side_by_side' | 'slider' | 'overlay_toggle' | 'venn' | 'spot_difference';
category_types?: string[];
category_labels?: Record<string, string>;
category_colors?: Record<string, string>;
exploration_enabled?: boolean;
zoom_enabled?: boolean;

// DescriptionMatchingConfig additions
show_connecting_lines?: boolean;
defer_evaluation?: boolean;
distractor_count?: number;
description_panel_position?: 'left' | 'right' | 'bottom';

// SortingItem fix
correct_category_ids?: string[];  // REPLACES singular correctCategoryId

// SequenceConfigItem additions
image?: string;
icon?: string;

// MemoryMatchPair additions
front_type?: 'text' | 'image';
back_type?: 'text' | 'image';
explanation?: string;

// PathWaypoint additions
type?: 'standard' | 'gate' | 'branch_point' | 'terminus';
svg_path_data?: string;
```

Add 3 missing blueprint-level fields:
```typescript
interface InteractiveDiagramBlueprint {
  // ... existing fields ...
  clickToIdentifyConfig?: ClickToIdentifyConfig;
  tracePathConfig?: TracePathConfig;
  dragDropConfig?: DragDropConfig;
}
```

### Fix 1.8: Add Missing State Fields

**File:** `backend/app/agents/state.py`

Add to AgentState TypedDict:
```python
# Sequencing assets
sequence_item_images: Optional[Dict[str, str]]  # item_id -> image_url

# Sorting assets
sorting_item_images: Optional[Dict[str, str]]   # item_id -> image_url
sorting_category_icons: Optional[Dict[str, str]] # category_id -> icon_url

# Memory Match assets
memory_card_images: Optional[Dict[str, str]]     # pair_id -> image_url
diagram_crop_regions: Optional[Dict[str, Dict]]  # zone_id -> {x, y, width, height}
```

(Compare/branching state fields DEFERRED — those mechanics are deferred.)

---

## Phase 2: Tool Implementation

> Make `generate_mechanic_content` and `enrich_mechanic_content` work for all 6 priority mechanics.
> ~300 lines across ~2 files. Blocking for Phase 3.

### Fix 2.1: generate_mechanic_content — Add memory_match handler

**File:** `backend/app/tools/scene_architect_tools.py`

Add handler that uses LLM to generate term-definition pairs from domain knowledge + question context:
```python
elif mechanic_type == "memory_match":
    # Generate pairs from canonical labels + descriptions
    pairs = []
    for label in zone_labels[:12]:  # Max 12 pairs for 6x4 grid
        desc = label_descriptions.get(label, "")
        pairs.append({
            "id": f"pair_{label.lower().replace(' ', '_')}",
            "term": label,
            "definition": desc or f"Key component in {subject}",
            "front_type": "text",
            "back_type": "text",
            "explanation": f"Learning about {label}: {desc}",
        })
    # Use LLM to enrich if descriptions are empty
    if not any(p["definition"] for p in pairs):
        enriched = await llm.generate_json(prompt=..., schema=...)
        pairs = enriched.get("pairs", pairs)
    result["pairs"] = pairs
    result["game_variant"] = "classic"
    result["match_type"] = "term_to_definition"
    result["grid_size"] = _compute_grid_size(len(pairs))
```

### Fix 2.2: generate_mechanic_content — Improve description_matching handler

**File:** `backend/app/tools/scene_architect_tools.py`

Replace current handler with LLM-powered functional description generation:
```python
elif mechanic_type == "description_matching":
    # Generate functional descriptions (NOT appearance-based)
    descriptions_prompt = f"""Generate functional descriptions for each structure.
    Subject: {subject}
    Labels: {zone_labels}
    For each label, write a 15-30 word functional description that describes
    WHAT IT DOES, not what it looks like. Example:
    - "Left Ventricle" -> "Pumps oxygenated blood through the aorta to the body"
    """
    descriptions = await llm.generate_json(prompt=descriptions_prompt, ...)
    result["descriptions"] = descriptions
    result["match_mode"] = "drag_to_zone"
    result["show_connecting_lines"] = True
    # Generate 2-3 distractor descriptions
    distractor_prompt = f"Generate 2-3 plausible but incorrect descriptions..."
    result["distractor_descriptions"] = await llm.generate_json(...)
```

### Fix 2.3: generate_mechanic_content — Improve sequencing handler

**File:** `backend/app/tools/scene_architect_tools.py`

Enhance to produce proper items with correct_order + layout config:
```python
elif mechanic_type == "sequencing":
    items_prompt = f"""Generate a sequence of {len(zone_labels)} items for ordering.
    Subject: {subject}
    Context labels: {zone_labels}
    For each item: id, text (concise name), description (1-2 sentences explaining order),
    order_index (correct position, 0-based)
    """
    items_data = await llm.generate_json(prompt=items_prompt, ...)
    result["items"] = items_data.get("items", [])
    result["correct_order"] = [item["id"] for item in sorted(result["items"], key=lambda x: x.get("order_index", 0))]
    result["sequence_type"] = "linear"
    result["layout_mode"] = "horizontal_timeline"
    result["instructions"] = f"Arrange the stages of {subject} in the correct order."
```

### Fix 2.4: generate_mechanic_content — Improve sorting handler

**File:** `backend/app/tools/scene_architect_tools.py`

Enhance category and item generation:
```python
elif mechanic_type == "sorting_categories":
    sort_prompt = f"""Design a sorting activity for {subject}.
    Available labels: {zone_labels}
    Generate 2-4 categories and assign each label to a category.
    Each category: id, name, description, color suggestion.
    Each item: id, text, correct_category_ids (as list), explanation.
    """
    sort_data = await llm.generate_json(prompt=sort_prompt, ...)
    result["categories"] = sort_data.get("categories", [])
    result["items"] = sort_data.get("items", [])
    result["sort_mode"] = "bucket"
    result["submit_mode"] = "batch_submit"
```

### Fix 2.5: generate_mechanic_content — Improve click_to_identify handler

**File:** `backend/app/tools/scene_architect_tools.py`

Generate identification prompts per zone:
```python
elif mechanic_type == "click_to_identify":
    prompts = []
    for label in zone_labels:
        desc = label_descriptions.get(label, "")
        prompts.append({
            "zone_label": label,
            "prompt_text": desc or f"Click on the {label}",
            "functional_prompt": f"Click on the structure that {desc}" if desc else None,
        })
    result["prompts"] = prompts
    result["prompt_style"] = "functional" if all(p.get("functional_prompt") for p in prompts) else "naming"
    result["highlight_style"] = "subtle"
    result["selection_mode"] = "sequential"
```

### Fix 2.6: generate_mechanic_content — Improve trace_path handler

**File:** `backend/app/tools/scene_architect_tools.py`

Generate ordered waypoints with path description:
```python
elif mechanic_type == "trace_path":
    path_prompt = f"""Define a trace path for {subject}.
    Available labels: {zone_labels}
    What is the correct order to trace? Generate ordered waypoints.
    Each waypoint: zone_label, order (1-based), description (why this comes next).
    Also provide: path description, path type (linear/circular).
    """
    path_data = await llm.generate_json(prompt=path_prompt, ...)
    result["waypoints"] = path_data.get("waypoints", [])
    result["path_type"] = path_data.get("path_type", "linear")
    result["path_description"] = path_data.get("path_description", "")
    result["show_direction_arrows"] = True
    result["particle_theme"] = "dots"
```

### Fix 2.7: enrich_mechanic_content — Add per-mechanic handlers

**File:** `backend/app/tools/interaction_designer_tools.py`

Currently generic LLM enrichment. Add mechanic-specific enrichment logic:

```python
async def enrich_mechanic_content(mechanic_type, scene_spec, ...):
    if mechanic_type == "sequencing":
        # Add ordering-specific misconception triggers
        # Add partial credit scoring (Kendall tau distance)
        # Add "swap these two" feedback hints
        ...
    elif mechanic_type == "sorting_categories":
        # Add per-category misconception triggers
        # Add "this item is often confused with category X" feedback
        # Add iterative correction config
        ...
    elif mechanic_type == "memory_match":
        # Add per-pair educational explanations
        # Add streak multiplier config
        # Add difficulty progression
        ...
    elif mechanic_type == "click_to_identify":
        # Add progressive difficulty ordering
        # Add per-zone identification feedback
        ...
    elif mechanic_type == "trace_path":
        # Add per-waypoint transition feedback
        # Add ordering misconception triggers
        ...
    elif mechanic_type == "description_matching":
        # Add per-description misconception triggers
        # Add connecting line feedback config
        ...
```

### Fix 2.8: generate_misconception_feedback — Remove drag_drop bias

**File:** `backend/app/tools/interaction_designer_tools.py` (around L140-170)

Current model uses `trigger_label + trigger_zone` which is drag_drop-specific. Make generic:

```python
# Support different misconception models per mechanic
if mechanic_type in ("drag_drop", "description_matching"):
    # Label-zone pairing misconceptions
    feedback_model = "label_zone_pairing"
elif mechanic_type in ("sequencing", "trace_path"):
    # Ordering misconceptions
    feedback_model = "ordering"
elif mechanic_type == "sorting_categories":
    # Category assignment misconceptions
    feedback_model = "category_assignment"
elif mechanic_type == "memory_match":
    # Association misconceptions
    feedback_model = "association"
elif mechanic_type == "click_to_identify":
    # Identification misconceptions
    feedback_model = "identification"
```

### Fix 2.9: validate_interactions — Add content checks

**File:** `backend/app/tools/interaction_designer_tools.py` (around L357-454)

Add content validation for all mechanics:
```python
# memory_match: check pairs have non-empty definitions
# sorting: check items have valid category references
# sequencing: check correct_order matches item ids
# branching: check all next_node_ids are valid
# trace_path: check waypoints reference valid zones
```

---

## Phase 3: Agent Prompt Refinements

> Fine-tune prompts based on tool changes from Phase 2.
> ~50 lines across ~4 files. Most of this was ALREADY APPLIED in the previous session.

### Fix 3.1: (ALREADY APPLIED) scene_architect_v3.py system+task prompt

Full rewrite with all 10 mechanic types, mandatory generate_mechanic_content.

### Fix 3.2: (ALREADY APPLIED) interaction_designer_v3.py system+task prompt

Full rewrite with mechanic-specific scoring/feedback guidance.

### Fix 3.3: (ALREADY APPLIED) game_designer_v3.py task prompt

Mandate check_capabilities, require per-mechanic config data.

### Fix 3.4: (ALREADY APPLIED) asset_generator_v3.py system+task prompt

Mechanic-aware image guidance, per-scene mechanic type injection.

### Fix 3.5: Update game_designer_v3 to use expanded schemas

**File:** `backend/app/agents/game_designer_v3.py`

Ensure the submit_game_design tool validates against the expanded SequenceDesign, SortingDesign, etc. from Phase 1. The game designer must now produce richer configs.

### Fix 3.6: Update check_capabilities to reflect actual tool readiness

**File:** `backend/app/tools/game_design_v3_tools.py`

After Phase 2 tools are implemented, update `check_capabilities` to accurately reflect which mechanics have working `generate_mechanic_content` handlers:
```python
ready_types = ["drag_drop", "sequencing", "sorting_categories", "memory_match",
               "click_to_identify", "trace_path", "description_matching"]
```

---

## Phase 4: Blueprint Assembler Fixes

> Wire upstream data through to final blueprint for all 6 priority mechanics.
> ~120 lines across ~2 files. Can run in parallel with Phases 5-6 after Phase 3.

### Fix 4.1: Fix scoring/feedback data drop

**Problem:** `blueprint_assembler_tools.py` L654-662 DROPS scoring/feedback for 6/9 mechanics. Lists crash on `.get()`.
**File:** `backend/app/tools/blueprint_assembler_tools.py`

Convert scoring and feedback from lists to dicts keyed by mechanic_type:
```python
# Convert scoring list → dict
scoring_data = {}
raw_scoring = interaction_spec.get("scoring", [])
if isinstance(raw_scoring, list):
    for s in raw_scoring:
        if isinstance(s, dict) and "mechanic_type" in s:
            scoring_data[s["mechanic_type"]] = s
elif isinstance(raw_scoring, dict):
    scoring_data = raw_scoring

# Same for feedback
feedback_data = {}
raw_feedback = interaction_spec.get("feedback", [])
if isinstance(raw_feedback, list):
    for f in raw_feedback:
        if isinstance(f, dict) and "mechanic_type" in f:
            feedback_data[f["mechanic_type"]] = f
elif isinstance(raw_feedback, dict):
    feedback_data = raw_feedback
```

### Fix 4.2: Forward mode_transitions and tasks

**Problem:** Blueprint assembler doesn't forward `mechanic_transitions[]` and `tasks[]` for multi-mechanic scenes.
**File:** `backend/app/tools/blueprint_assembler_tools.py`

In scene assembly:
```python
# Forward mode transitions
if interaction_spec.get("mode_transitions"):
    game_scene["modeTransitions"] = interaction_spec["mode_transitions"]

# Forward tasks
scene_tasks = scene_spec.get("tasks", [])
if scene_tasks:
    game_scene["tasks"] = scene_tasks
```

### Fix 4.3: Populate expanded mechanic configs in blueprint

**File:** `backend/app/tools/blueprint_assembler_tools.py`

For each priority mechanic, ensure the expanded config fields from Phase 1 are mapped into the blueprint:

```python
# sequencing
if mech_type == "sequencing":
    seq_config = mech_config.get("sequence_config") or mech_config.get("config", {})
    mechanic_entry["config"] = {
        "items": seq_config.get("items", []),
        "correctOrder": seq_config.get("correct_order", []),
        "layoutMode": seq_config.get("layout_mode", "horizontal_timeline"),
        "interactionPattern": seq_config.get("interaction_pattern", "drag_reorder"),
        "cardType": seq_config.get("card_type", "text_only"),
        "connectorStyle": seq_config.get("connector_style", "arrow"),
        "instructions": seq_config.get("instructions", ""),
    }

# sorting_categories
if mech_type == "sorting_categories":
    sort_config = mech_config.get("sorting_config") or mech_config.get("config", {})
    mechanic_entry["config"] = {
        "categories": sort_config.get("categories", []),
        "items": sort_config.get("items", []),
        "sortMode": sort_config.get("sort_mode", "bucket"),
        "submitMode": sort_config.get("submit_mode", "batch_submit"),
        "instructions": sort_config.get("instructions", ""),
    }

# memory_match
if mech_type == "memory_match":
    mem_config = mech_config.get("memory_config") or mech_config.get("config", {})
    mechanic_entry["config"] = {
        "pairs": mem_config.get("pairs", []),
        "gameVariant": mem_config.get("game_variant", "classic"),
        "matchType": mem_config.get("match_type", "term_to_definition"),
        "gridSize": mem_config.get("grid_size"),
        "cardBackStyle": mem_config.get("card_back_style", "pattern"),
        "showExplanationOnMatch": mem_config.get("show_explanation_on_match", True),
        "instructions": mem_config.get("instructions", ""),
    }

# click_to_identify
if mech_type == "click_to_identify":
    click_config = mech_config.get("click_config") or mech_config.get("config", {})
    mechanic_entry["config"] = {
        "prompts": click_config.get("prompts", []),
        "promptStyle": click_config.get("prompt_style", "naming"),
        "selectionMode": click_config.get("selection_mode", "sequential"),
        "highlightStyle": click_config.get("highlight_style", "subtle"),
    }

# trace_path
if mech_type == "trace_path":
    path_config = mech_config.get("path_config") or mech_config.get("config", {})
    mechanic_entry["config"] = {
        "waypoints": path_config.get("waypoints", []),
        "pathType": path_config.get("path_type", "linear"),
        "drawingMode": path_config.get("drawing_mode", "click_waypoints"),
        "particleTheme": path_config.get("particle_theme", "dots"),
        "showDirectionArrows": path_config.get("show_direction_arrows", True),
    }
```

### Fix 4.4: validate_blueprint — Add mechanic checks

**File:** `backend/app/tools/blueprint_assembler_tools.py`

Add validation for all priority mechanics in validate_blueprint:
```python
# Check mechanic-specific config completeness
for mechanic in scene.get("mechanics", []):
    mtype = mechanic.get("type", "")
    config = mechanic.get("config", {})
    if mtype == "sequencing" and not config.get("items"):
        issues.append(f"Scene {sn}: sequencing has no items")
    if mtype == "sorting_categories" and not config.get("categories"):
        issues.append(f"Scene {sn}: sorting has no categories")
    if mtype == "memory_match" and not config.get("pairs"):
        issues.append(f"Scene {sn}: memory_match has no pairs")
    if mtype == "trace_path" and not config.get("waypoints"):
        issues.append(f"Scene {sn}: trace_path has no waypoints")
```

### Fix 4.5: repair_blueprint — Add repairs for all mechanics

**File:** `backend/app/tools/blueprint_assembler_tools.py`

Currently only repairs click_to_identify and trace_path. Add repairs for sequencing, sorting, memory, description_matching.

---

## Phase 5: Frontend Schema + Zustand

> Update TypeScript types and Zustand store to consume expanded configs.
> ~150 lines across ~3 files. Can run in parallel with Phases 4, 6 after Phase 3.

### Fix 5.1: (From Fix 1.7) Apply TypeScript type changes

Apply all the type additions from Fix 1.7 to `types.ts`.

### Fix 5.2: Fix SortingItem correctCategoryId → correct_category_ids

**File:** `frontend/src/components/templates/InteractiveDiagramGame/types.ts`

```typescript
// Before:
correctCategoryId: string;
// After (backward compatible):
correctCategoryId?: string;        // Legacy
correct_category_ids?: string[];   // New
```

Update SortingCategories.tsx to check `item.correct_category_ids?.[0] || item.correctCategoryId`.

### Fix 5.3: Fix score reset on mode transition

**File:** `frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts`

Around L1517, change:
```typescript
// Before:
score: 0,
// After:
score: get().score,  // Preserve cumulative score
```

### Fix 5.4: Fix _sceneToBlueprint config forwarding

**File:** `frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts`

Update `_sceneToBlueprint` to forward new config types:
```typescript
clickToIdentifyConfig: scene.clickToIdentifyConfig,
tracePathConfig: scene.tracePathConfig,
dragDropConfig: scene.dragDropConfig,
```

### Fix 5.5: Add missing Zustand state fields and actions

**File:** `frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts`

Add state fields and actions for new mechanic features (from research):
```typescript
// State
explorationPhase: boolean;
explorationTimeRemaining: number | null;

// Actions
startExplorationPhase: () => void;
endExplorationPhase: () => void;
```

---

## Phase 6: Frontend Component Enhancements

> Polish the 6 priority mechanic components with research-backed features.
> ~400 lines across ~8 files. Can run in parallel with Phases 4-5 after Phase 3.
> Prioritized by P0 (critical), P1 (high), P2 (deferred).

### Fix 6.1: SequenceBuilder P0 Enhancements

**File:** `frontend/.../interactions/SequenceBuilder.tsx`

- Read `layout_mode` from config (default: horizontal_timeline)
- Read `card_type` from config (default: text_only)
- If item has `image`, render image+text card layout
- Add connecting arrows between items (SVG line with arrowhead)
- Read `instructions` from config and display as banner
- Add `connector_style` support (arrow/line/numbered/none)
- Show position numbers on correct placement

### Fix 6.2: SortingCategories P0 Enhancements

**File:** `frontend/.../interactions/SortingCategories.tsx`

- Read `sort_mode` from config (default: bucket)
- Read `submit_mode` from config
- Read `container_style` from config
- If item has `image`, render image card
- Category containers: show icon, color header, item count badge
- Add iterative correction: on batch submit, incorrect items bounce back to pool
- Read `instructions` from config and display as banner

### Fix 6.3: MemoryMatch P0 Enhancements

**File:** `frontend/.../interactions/MemoryMatch.tsx`

- Fix CSS flip: replace opacity toggle with true 3D perspective:
  ```css
  .card { perspective: 1000px; }
  .card-inner { transform-style: preserve-3d; transition: transform 0.6s; }
  .card-inner.flipped { transform: rotateY(180deg); }
  .card-front, .card-back { backface-visibility: hidden; }
  .card-back { transform: rotateY(180deg); }
  ```
- Read `game_variant` from config
- Read `match_type` from config
- Read `show_explanation_on_match` — show educational popup on pair match
- Read `card_back_style` from config
- Read `matched_card_behavior` from config (fade/shrink/collect/checkmark)
- Read `instructions` from config

### Fix 6.4: HotspotManager P0 Enhancements (click_to_identify)

**File:** `frontend/.../interactions/HotspotManager.tsx`

- Fix L227-230: Don't leak zone labels in `any_order` mode prompt
- Read `prompt_style` from clickToIdentifyConfig
- Read `highlight_style` from config — make zones nearly invisible in test mode
- Read `selection_mode` from config
- Show information popup on correct identification
- Add `show_zone_count` config — display "3 of 8 identified"

### Fix 6.5: PathDrawer P0 Enhancements (trace_path)

**File:** `frontend/.../interactions/PathDrawer.tsx`

- Read `path_type` from tracePathConfig
- Read `particle_theme` from config
- Add directional arrows along path segments (SVG markers at regular intervals)
- Read `show_waypoint_labels` from config
- Show waypoint information tooltip on hover/correct click
- Read `instructions` from config

### Fix 6.6: DescriptionMatcher P0 Enhancements

**File:** `frontend/.../interactions/DescriptionMatcher.tsx`

- Fix MC option reshuffle: memoize shuffled options with `useMemo`
- Read `show_connecting_lines` from config — add SVG lines between matched pairs
- Read `defer_evaluation` from config — "Submit All" button
- Read `description_panel_position` from config
- Read `instructions` from config

### Fix 6.7: DiagramCanvas P0 Enhancements (drag_drop)

**File:** `frontend/.../DiagramCanvas.tsx`

- Read `showLeaderLines` from dragDropConfig
- Add SVG leader lines from placed label to zone center
- Read `showInfoPanelOnCorrect` — tooltip with educational info on correct placement

### Fix 6.8: Fix Common Bugs

**Files:** Various

- DescriptionMatcher MC reshuffle (Fix 6.6 above)
- HotspotManager zone label leak (Fix 6.4 above)
- MemoryMatch CSS flip (Fix 6.3 above)
- Score reset on mode transition (Fix 5.3 above)
- CompareContrast dead `highlightMatching` field — remove from types

---

## Phase 7: Hierarchical Chaining (DEFERRED)

> Upgrade from linear ModeTransition[] to MechanicDAG.
> ~500+ lines across ~10 files. Separate workstream.

### 7.1 Foundation
- Add `MechanicDAG`, `MechanicDAGNode`, `MechanicDAGEdge` Pydantic schemas
- Add `mechanic_graph` field to blueprint
- Implement `modeTransitionsToDAG()` desugaring (Python + TypeScript)
- Update blueprint_assembler_v3 to output mechanic_graph
- Frontend: check `mechanicGraph` first, fall back to `modeTransitions`

### 7.2 DAG Engine
- Add `HierarchicalGameState` to Zustand
- NavigationStack (push/pop/replace)
- `computeNodeScore()` recursive aggregation
- DAG traversal: `getAvailableNodes()`, `isNodeUnlocked()`, `evaluateGate()`
- BreadcrumbNav component
- ProgressMiniMap component

### 7.3 Hub-and-Spoke
- HubDiagram component
- Zoom transitions
- Game planner prompt for hub structure

### 7.4 Conditional Branching
- BRANCH node evaluation
- Score-based routing UI

---

## Phase 8: New Mechanics (DEFERRED)

> Add new mechanic types beyond the existing 9.
> Separate workstream, dependent on Phases 0-6 completion.

### Quick Wins (Phase 8a)
- `hotspot_multi_select` — extends click_to_identify, ~LOW cost
- `cloze_fill_blank` — text input on zones, ~MEDIUM cost

### High Impact (Phase 8b)
- `spot_the_error` — modified diagram with errors to find
- `predict_observe_explain` — multi-phase (predict → observe → explain)

### Advanced (Phase 8c)
- `cause_effect_chain` — DAG builder
- `process_builder` — full graph editor
- `annotation_drawing` — freehand drawing assessment

---

## Verification Plan

### Per-Phase Verification

| Phase | Verification |
|-------|-------------|
| 0 | `curl /api/assets/v3/{run_id}/test.png` returns 200; retry count = 2 actual retries |
| 1 | `python3 -c "from app.agents.schemas.game_design_v3 import SequenceDesign; SequenceDesign(correct_order=['a'])"` |
| 2 | Run V3 pipeline with sequencing question; verify generate_mechanic_content produces items+correct_order |
| 3 | Verify prompts reference correct tool names in agent system prompts |
| 4 | Run V3 pipeline; verify blueprint has populated mechanic configs for all mechanics |
| 5 | `npx tsc --noEmit` — zero TypeScript errors |
| 6 | Load game page; verify each mechanic component reads config and renders accordingly |

### E2E Test Prompts

```bash
# Test 1: drag_drop (regression)
"Label the main parts of a flower"

# Test 2: sequencing
"Arrange the stages of mitosis in order"

# Test 3: sorting_categories
"Classify these animals as vertebrates or invertebrates: eagle, spider, salmon, jellyfish, frog, ant"

# Test 4: memory_match
"Match these cell organelles with their functions"

# Test 5: click_to_identify
"Identify each chamber and valve of the human heart"

# Test 6: trace_path
"Trace the path of blood flow through the human heart"

# Test 7: multi-mechanic
"Create a comprehensive game about the human digestive system"
```

### Per-Run Verification Checklist

1. All stages complete (no errors in pipeline run)
2. game_designer produces mechanic-specific configs (not just type)
3. scene_architect calls generate_mechanic_content for every non-drag_drop mechanic
4. interaction_designer calls enrich_mechanic_content for every mechanic
5. Blueprint has populated mechanic configs (not empty dicts)
6. Blueprint has scoring and feedback per mechanic
7. Game page renders correct interaction component
8. Mechanic component reads config (items, categories, pairs, waypoints, etc.)
9. Scoring works (correct placements add score)
10. Mode transitions work (multi-mechanic scenes)

---

## Summary

| Phase | Files | Lines | Status | Dependency |
|-------|-------|-------|--------|-----------|
| 0: Critical Infrastructure | ~6 | ~80 | TODO | None (FIRST) |
| 1: Schema Expansion | ~6 | ~400 | TODO | Phase 0 |
| 2: Tool Implementation | ~2 | ~300 | TODO | Phase 1 |
| 3: Prompt Refinements | ~4 | ~50 | MOSTLY DONE | Phase 2 |
| 4: Blueprint Assembler | ~2 | ~120 | TODO | Phase 3 |
| 5: Frontend Schema+Zustand | ~3 | ~150 | TODO | Phase 3 |
| 6: Frontend Components | ~8 | ~400 | TODO | Phase 3 |
| 7: Hierarchical Chaining | ~10 | ~500+ | DEFERRED | Phase 6 |
| 8: New Mechanics | ~15+ | ~1000+ | DEFERRED | Phase 6 |
| **Total (Phases 0-6)** | **~31** | **~1500** | | |

### Key Files Touched

| File | Phases |
|------|--------|
| `backend/app/routes/generate.py` | 0 |
| `backend/app/agents/graph.py` | 0 |
| `backend/app/agents/state.py` | 0, 1 |
| `backend/app/tools/game_design_v3_tools.py` | 0, 3 |
| `backend/app/agents/schemas/game_design_v3.py` | 1 |
| `backend/app/tools/scene_architect_tools.py` | 2 |
| `backend/app/tools/interaction_designer_tools.py` | 2 |
| `backend/app/agents/game_designer_v3.py` | 3 (DONE) |
| `backend/app/agents/scene_architect_v3.py` | 3 (DONE) |
| `backend/app/agents/interaction_designer_v3.py` | 3 (DONE) |
| `backend/app/agents/asset_generator_v3.py` | 3 (DONE) |
| `backend/app/tools/blueprint_assembler_tools.py` | 4 |
| `frontend/.../types.ts` | 1, 5 |
| `frontend/.../hooks/useInteractiveDiagramState.ts` | 5 |
| `frontend/.../interactions/SequenceBuilder.tsx` | 6 |
| `frontend/.../interactions/SortingCategories.tsx` | 6 |
| `frontend/.../interactions/MemoryMatch.tsx` | 6 |
| `frontend/.../interactions/HotspotManager.tsx` | 6 |
| `frontend/.../interactions/PathDrawer.tsx` | 6 |
| `frontend/.../interactions/DescriptionMatcher.tsx` | 6 |
| `frontend/.../DiagramCanvas.tsx` | 6 |
