# V3 Pipeline Comprehensive Fix Plan

> Based on 14 research/audit documents (13,000+ lines). Covers backend agents, tools, schemas, state, graph, routes, services, frontend types, components, and Zustand store.

---

## Table of Contents

1. [Strategy & Priority 6 Mechanics](#1-strategy)
2. [Game Designer Context Delivery](#2-game-designer-context)
3. [Per-Mechanic Asset Spec Architecture](#3-asset-spec-architecture)
4. [Phase 0: Infrastructure (State, Schemas, Graph, Routes)](#4-phase-0)
5. [Phase 1: Game Designer V3 + Tools](#5-phase-1)
6. [Phase 2: Scene Architect V3 + Tools](#6-phase-2)
7. [Phase 3: Interaction Designer V3 + Tools](#7-phase-3)
8. [Phase 4: Asset Generator V3 + Tools](#8-phase-4)
9. [Phase 5: Blueprint Assembler V3 + Tools](#9-phase-5)
10. [Phase 6: Validators](#10-phase-6)
11. [Phase 7: Frontend Types & Components](#11-phase-7)
12. [Phase 8: Zustand Store & Game Logic](#12-phase-8)
13. [Verification Plan](#13-verification)
14. [Fix Index (All Fixes by ID)](#14-fix-index)

---

## 1. Strategy & Priority 6 Mechanics <a id="1-strategy"></a>

### Which 6 and Why

| # | Mechanic | Current State | Why Priority | Interaction Type |
|---|----------|---------------|--------------|-----------------|
| 1 | **drag_drop** | Functional but basic | Already works — polish to premium | Spatial placement |
| 2 | **sequencing** | BROKEN (text-only list) | High educational value, ordering interaction | Temporal ordering |
| 3 | **sorting_categories** | BROKEN (bucket-only) | High educational value, classification | Classification |
| 4 | **memory_match** | BROKEN (no 3D flip) | High engagement, tests recall | Recall matching |
| 5 | **click_to_identify** | Degraded (no prompt styles) | Core assessment mechanic | Identification |
| 6 | **trace_path** | BROKEN (no SVG paths) | Key for process/flow content | Path tracing |

### Deferred Mechanics

| Mechanic | Reason for Deferral |
|----------|-------------------|
| description_matching | Close to working, lower priority than the 6 above |
| compare_contrast | Needs dual-image pipeline — highest backend cost |
| branching_scenario | Needs visual novel system (backgrounds, sprites, state) — highest total cost |

### Architecture Principles

1. **Bloom's as context, not selector** — Game designer SEES Bloom's level as informational context (Stage 1 input_enhancer still classifies it). But mechanics are NOT selected via a fixed Bloom's-to-mechanic mapping. The game designer uses content type, available data, and pedagogical fit to decide.
2. **Testing-first** — Mechanics test knowledge; no answer giveaways in test mode
3. **Spec-before-assets** — Scene architect produces asset specs → asset generator follows specs
4. **Configurable everything** — Layout modes, card styles, connector types are config fields, not hardcoded
5. **Gemini-only asset generation** — All image generation uses `gemini-2.5-flash-image` API
6. **Delta scoring** — Store actions accumulate score deltas, never overwrite
7. **ReAct self-correction** — Every phase uses ReAct planner with tools for validation and retry

### Bloom's Taxonomy Handling (Corrected)

**Keep**: `blooms_level` and `blooms_justification` in `PedagogicalContext` (state.py). Input enhancer continues to classify Bloom's level.

**Keep**: `bloom_alignment_score` in `TemplateSelection` — used by router for template selection confidence, not mechanic selection.

**Change**: Game designer system prompt explicitly says: "Bloom's level is informational context about cognitive demand. Do NOT use it as a fixed mapping to select mechanics. Choose mechanics based on content type, available data, and pedagogical fit."

**Remove**: Any hardcoded Bloom's-to-mechanic mapping in tools (e.g., analyze_pedagogy forcing drag_drop for "Remember" level).

---

## 2. Game Designer Context Delivery <a id="2-game-designer-context"></a>

### Problem

The game designer currently receives:
- Enhanced question text, subject
- Bloom's level (informational)
- Domain knowledge (truncated to 2000 chars, only 5 of 13 fields read)
- Canonical labels (first 30)
- Learning objectives, pedagogical context (truncated to 1000 chars)

DK utilization is only 9.2% (6/65 agent-field pairs). The game designer cannot make informed mechanic decisions.

### Solution: `build_mechanic_context()` function

**File:** `backend/app/tools/game_design_v3_tools.py` (new function)

Builds a structured context dict from domain knowledge showing what data is available for each mechanic:

```python
def build_mechanic_context(domain_knowledge: Dict, canonical_labels: List[str]) -> Dict:
    """Build structured context showing what mechanics are feasible."""
    dk = domain_knowledge or {}
    label_descs = dk.get("label_descriptions", {})
    seq_data = dk.get("sequence_flow_data", {})
    comp_data = dk.get("comparison_data", {})
    content_chars = dk.get("content_characteristics", {})

    feasibility = {}

    # drag_drop — always feasible with 3+ labels
    feasibility["drag_drop"] = {
        "ready": len(canonical_labels) >= 3,
        "data_available": {"label_count": len(canonical_labels)},
        "recommended_when": "Spatial identification of labeled structures on a diagram",
    }

    # sequencing — feasible with sequence data OR temporal content
    feasibility["sequencing"] = {
        "ready": bool(seq_data) or content_chars.get("needs_sequence", False),
        "data_available": {
            "sequence_items": seq_data.get("sequence_items", [])[:8],
            "flow_type": seq_data.get("flow_type", "unknown"),
        } if seq_data else {},
        "recommended_when": "Process steps, temporal ordering, stages, phases",
    }

    # trace_path — feasible with sequence data that has spatial flow
    feasibility["trace_path"] = {
        "ready": bool(seq_data) and seq_data.get("flow_type") in ("circulatory", "linear", "cyclic", "branching"),
        "data_available": {
            "waypoints": [item.get("text", "") for item in seq_data.get("sequence_items", [])[:8]],
            "flow_type": seq_data.get("flow_type", "unknown"),
        } if seq_data else {},
        "recommended_when": "Flow paths, circulation, signal pathways, processes with spatial routes",
    }

    # sorting_categories — feasible with comparison data or 6+ groupable labels
    feasibility["sorting_categories"] = {
        "ready": bool(comp_data) or content_chars.get("needs_comparison", False) or len(canonical_labels) >= 6,
        "data_available": {
            "categories": comp_data.get("sorting_categories", [])[:5],
            "groups": comp_data.get("groups", [])[:5],
        } if comp_data else {},
        "recommended_when": "Classification, grouping, categorization tasks",
    }

    # memory_match — feasible with label_descriptions or 4+ labels
    feasibility["memory_match"] = {
        "ready": len(label_descs) >= 4 or len(canonical_labels) >= 4,
        "data_available": {
            "term_definition_pairs": [
                {"term": k, "definition": v[:80]}
                for k, v in list(label_descs.items())[:6]
            ]
        } if label_descs else {},
        "recommended_when": "Term-definition recall, vocabulary, structure-function matching",
    }

    # click_to_identify — feasible with labels
    feasibility["click_to_identify"] = {
        "ready": len(canonical_labels) >= 3,
        "data_available": {"label_count": len(canonical_labels)},
        "recommended_when": "Identification, naming, pointing to specific structures",
    }

    return {
        "available_labels": len(canonical_labels),
        "label_list": canonical_labels[:30],
        "content_signals": {
            "has_sequence_data": bool(seq_data),
            "has_comparison_data": bool(comp_data),
            "has_label_descriptions": bool(label_descs),
            "has_hierarchical_data": bool(dk.get("hierarchical_relationships")),
            "needs_sequence": content_chars.get("needs_sequence", False),
            "needs_comparison": content_chars.get("needs_comparison", False),
        },
        "mechanic_feasibility": feasibility,
    }
```

### What Changes in game_designer_v3.py

**Remove:** "Each mechanic only needs 'type' field" (L217) — configs ARE needed

**Add to task prompt:** Inject mechanic_context_v3 as structured JSON. Add explicit instruction: "Only choose mechanics marked 'ready': true. Provide FULL mechanic configs, not just type."

**Keep:** blooms_level injection BUT add: "This is informational context about cognitive demand. Do not use it as a fixed mapping to choose mechanics."

---

## 3. Per-Mechanic Asset Spec Architecture <a id="3-asset-spec-architecture"></a>

### Problem

Asset generator only knows ONE asset type: `diagram_image + zones`. Different mechanics need different assets.

| Mechanic | Assets Needed | What Currently Exists | Gap |
|----------|-------------|----------------------|-----|
| drag_drop | 1 diagram + zones | Diagram + zones | NONE |
| click_to_identify | 1 diagram + zones | Diagram + zones | Magnification missing |
| trace_path | 1 diagram + zones + SVG path data | Diagram + zones | SVG paths missing |
| sequencing | 1 diagram (optional) + per-item images (optional) | Diagram only | Per-item images missing |
| sorting_categories | 1 diagram (optional) + per-item images (optional) | Diagram only | Per-item images missing |
| memory_match | per-pair card face images (optional, text-only works) | Diagram only | Card images missing |

### Solution: SceneAssetRequirement in SceneSpecV3

Scene architect generates `asset_requirements` per scene. Asset generator reads them.

```python
class SceneAssetRequirement(BaseModel):
    asset_type: str  # "diagram_image", "item_illustration", "card_face_image"
    asset_id: str
    description: str
    style: str = "clean educational illustration"
    mechanic_type: str = ""
    for_item_id: Optional[str] = None
    constraints: Dict[str, Any] = {}
    priority: str = "required"  # "required" | "optional"
```

For Phase 1 (priority 6 mechanics), only `diagram_image` is "required". Item illustrations are "optional" — mechanics work with text-only if images aren't generated.

---

## 4. Phase 0: Infrastructure <a id="4-phase-0"></a>

### Fix 0.1: State Fields (state.py)

**File:** `backend/app/agents/state.py`

**0.1a** Add V3 asset spec fields (~line 473):
```python
asset_requirements_v3: Optional[List[Dict[str, Any]]]  # Per-scene asset specs
generated_item_assets_v3: Optional[Dict[str, str]]  # asset_id → URL/path
mechanic_context_v3: Optional[Dict[str, Any]]  # Structured mechanic feasibility
```

**0.1b** Fix DomainKnowledge TypedDict mismatch (~line 321-332). Add fields that Pydantic DomainKnowledge has but TypedDict doesn't:
```python
label_descriptions: Optional[Dict[str, str]]
comparison_data: Optional[Dict[str, Any]]
query_intent: Optional[Dict[str, Any]]
suggested_reveal_order: Optional[List[str]]
scene_hints: Optional[List[Dict[str, Any]]]
```

### Fix 0.2: Game Design Schemas (game_design_v3.py)

**File:** `backend/app/agents/schemas/game_design_v3.py`

**0.2a** Expand SequenceDesign:
```python
class SequenceDesign(BaseModel):
    sequence_type: str = "linear"  # linear, cyclic, branching
    items: List[Dict[str, str]] = []
    correct_order: List[str] = []
    instruction_text: Optional[str] = None
    # NEW:
    layout_mode: str = "vertical_timeline"  # vertical_timeline, horizontal_timeline, flowchart
    item_card_type: str = "text_only"  # text_only, text_with_icon, image_and_text
    connector_style: str = "arrow"  # arrow, dashed_arrow, numbered_circles, chevron
    has_distractors: bool = False
    distractor_items: List[Dict[str, str]] = []
```

**0.2b** Expand SortingDesign:
```python
class SortingDesign(BaseModel):
    categories: List[Dict[str, Any]] = []
    items: List[Dict[str, Any]] = []
    show_category_hints: bool = False
    instruction_text: Optional[str] = None
    # NEW:
    sort_mode: str = "bucket"  # bucket, venn_2, matrix, column
    item_card_type: str = "text_only"
    container_style: str = "bucket"
    submit_mode: str = "batch_submit"  # batch_submit, immediate_feedback, lock_on_place
    allow_multi_category: bool = False
```

**0.2c** Expand MemoryMatchDesign:
```python
class MemoryMatchDesign(BaseModel):
    pairs: List[Dict[str, str]] = []
    grid_size: Optional[List[int]] = None
    flip_duration_ms: int = 600
    instruction_text: Optional[str] = None
    # NEW:
    game_variant: str = "classic"  # classic, column_match, peek
    card_face_type: str = "text_text"
    match_type: str = "term_to_definition"
    matched_card_behavior: str = "fade"
    mismatch_penalty: str = "none"
```

**0.2d** Expand ClickDesign:
```python
class ClickDesign(BaseModel):
    click_options: List[str] = []
    correct_assignments: Dict[str, str] = {}
    selection_mode: str = "sequential"
    prompts: List[str] = []
    # NEW:
    prompt_style: str = "naming"  # naming, functional
    highlight_style: str = "outlined"  # subtle, outlined, invisible
    explore_mode_enabled: bool = False
```

**0.2e** Expand PathDesign:
```python
class PathDesign(BaseModel):
    waypoints: List[str] = []
    path_type: str = "linear"  # linear, circular, branching
    requires_order: bool = True
    description: Optional[str] = None
    instruction_text: Optional[str] = None
    # NEW:
    drawing_mode: str = "click_waypoint"  # click_waypoint, freehand, guided
    curve_type: str = "straight"  # straight, quadratic, cubic, catmull_rom
    direction_arrows: bool = True
    particle_theme: Optional[str] = None  # "blood_cells", "electrons", "water", etc.
    color_transition: Optional[Dict[str, str]] = None  # {start_color, end_color}
```

### Fix 0.3: Frontend Config Schemas (interactive_diagram.py)

**File:** `backend/app/agents/schemas/interactive_diagram.py`

**0.3a** Expand SequenceConfig + SequenceConfigItem:
```python
class SequenceConfigItem(BaseModel):
    id: str
    text: str
    description: Optional[str] = None
    imageUrl: Optional[str] = None  # NEW
    iconName: Optional[str] = None  # NEW

class SequenceConfig(BaseModel):
    sequenceType: str = "linear"
    items: List[SequenceConfigItem] = []
    correctOrder: List[str] = []
    allowPartialCredit: bool = True
    instructionText: Optional[str] = None
    # NEW:
    layoutMode: str = "vertical_timeline"
    itemCardType: str = "text_only"
    connectorStyle: str = "arrow"
    hasDistractors: bool = False
    distractorItems: List[SequenceConfigItem] = []
```

**0.3b** Expand SortingConfig + SortingItem:
```python
class SortingItem(BaseModel):
    id: str
    text: str
    correctCategoryId: str
    correctCategoryIds: Optional[List[str]] = None  # NEW: for Venn
    description: Optional[str] = None
    imageUrl: Optional[str] = None  # NEW

class SortingConfig(BaseModel):
    items: List[SortingItem] = []
    categories: List[SortingCategory] = []
    allowPartialCredit: bool = True
    showCategoryHints: bool = False
    instructions: Optional[str] = None
    # NEW:
    sortMode: str = "bucket"
    itemCardType: str = "text_only"
    containerStyle: str = "bucket"
    submitMode: str = "batch_submit"
    allowMultiCategory: bool = False
```

**0.3c** Expand MemoryMatchConfig + MemoryMatchPair:
```python
class MemoryMatchPair(BaseModel):
    id: str
    front: str
    back: str
    frontType: str = "text"
    backType: str = "text"
    explanation: Optional[str] = None  # NEW
    matchType: Optional[str] = None  # NEW

class MemoryMatchConfig(BaseModel):
    pairs: List[MemoryMatchPair] = []
    gridSize: Optional[List[int]] = None
    flipDurationMs: int = 600
    showAttemptsCounter: bool = True
    instructions: Optional[str] = None
    # NEW:
    gameVariant: str = "classic"
    cardFaceType: str = "text_text"
    matchType: str = "term_to_definition"
    matchedCardBehavior: str = "fade"
    mismatchPenalty: str = "none"
```

**0.3d** Add ClickToIdentifyConfig:
```python
class ClickToIdentifyConfig(BaseModel):
    promptStyle: str = "naming"
    selectionMode: str = "sequential"
    highlightStyle: str = "outlined"
    exploreModeEnabled: bool = False
    prompts: List[Dict[str, Any]] = []  # [{zoneId, prompt, order}]
    instructions: Optional[str] = None
```

**0.3e** Add TracePathConfig:
```python
class TracePathConfig(BaseModel):
    pathType: str = "linear"  # linear, circular, branching
    drawingMode: str = "click_waypoint"  # click_waypoint, freehand, guided
    curveType: str = "straight"  # straight, quadratic, cubic, catmull_rom
    directionArrows: bool = True
    particleTheme: Optional[str] = None
    colorTransition: Optional[Dict[str, str]] = None
    pathStyle: Optional[Dict[str, Any]] = None
    instructions: Optional[str] = None
```

**0.3f** Add DragDropConfig:
```python
class DragDropConfig(BaseModel):
    placementMode: str = "drag_drop"  # drag_drop, click_to_place
    feedbackTiming: str = "immediate"
    leaderLineStyle: str = "none"  # none, straight, elbow, curved
    placementAnimation: str = "spring"  # spring, ease, instant
    zoomEnabled: bool = False
    trayPosition: str = "bottom"
    trayLayout: str = "horizontal"
    instructions: Optional[str] = None
```

### Fix 0.4: Scene Spec Schema (scene_spec_v3.py)

**File:** `backend/app/agents/schemas/scene_spec_v3.py`

Add SceneAssetRequirement class and `asset_requirements` field to SceneSpecV3.

### Fix 0.5: Interaction Spec Schema (interaction_spec_v3.py)

**File:** `backend/app/agents/schemas/interaction_spec_v3.py`

**0.5a** Add missing mechanics to MECHANIC_TRIGGER_MAP:
```python
"compare_contrast": {"all_complete", "score_threshold"},
"hierarchical": {"all_complete", "percentage_complete", "score_threshold"},
```

**0.5b** Add missing mechanic-specific validation (memory_match, branching_scenario, compare_contrast, sorting_categories content checks).

### Fix 0.6: Graph Wiring (graph.py)

**File:** `backend/app/agents/graph.py`

**0.6a** Fix retry logic — "max 2 retries" is actually max 1 retry:
```python
# Change from: if retries >= 2
# To: if retries >= 3  (allows 2 actual retries = 3 total executions)
```
Apply to `_v3_design_validation_router`, `_v3_scene_validation_router`, `_v3_interaction_validation_router`.

**0.6b** Fix topology metadata — hardcoded "T1" for V3 runs:
```python
# In save_pipeline_run() call:
topology=pipeline_preset or topology  # was hardcoded "T1"
```

### Fix 0.7: Routes (generate.py)

**File:** `backend/app/routes/generate.py`

**0.7a** Add V3 image serving route:
```python
@router.get("/assets/v3/{run_id}/{filename}")
async def serve_v3_asset(run_id: str, filename: str):
    # Serve V3-generated images from pipeline_outputs/v3_assets/{run_id}/
    # With proper filename sanitization and 404 handling
```

**0.7b** Fix multi-scene image URL proxying — currently only root-level `blueprint.diagram` is proxied. Add per-scene URL rewriting:
```python
if blueprint.get("game_sequence"):
    for scene in blueprint["game_sequence"].get("scenes", []):
        diagram = scene.get("diagram", {})
        if diagram.get("assetUrl", "").startswith("pipeline_outputs/"):
            # Rewrite to /api/assets/v3/{run_id}/{filename}
```

**0.7c** Add V3 agent output recording in `_build_agent_outputs()`:
```python
record("game_designer_v3", state.get("game_design_v3"))
record("scene_architect_v3", state.get("scene_specs_v3"))
record("interaction_designer_v3", state.get("interaction_specs_v3"))
record("asset_generator_v3", state.get("generated_assets_v3"))
record("blueprint_assembler_v3", state.get("blueprint"))
```

**0.7d** Add pipeline timeout:
```python
async with asyncio.timeout(600):  # 10 minutes
    result = await graph.ainvoke(initial_state)
```

### Fix 0.8: Model Assignments (agent_models.py)

**File:** `backend/app/config/agent_models.py`

**0.8a** Add V3 agent entries to `balanced`, `cost_optimized`, and `quality_optimized` presets (currently only `gemini_only` has them). Fallback defaults may use models that can't reliably do multi-step ReAct.

---

## 5. Phase 1: Game Designer V3 + Tools <a id="5-phase-1"></a>

### Fix 1.1: System Prompt Rewrite

**File:** `backend/app/agents/game_designer_v3.py` lines 35-102

**Changes:**
- Add Bloom's context note: "Bloom's level is informational. Choose mechanics from content type and available data."
- Add ALL 6 priority mechanics with detailed config guidance
- Replace "Each mechanic only needs 'type' field" with "Provide FULL mechanic configs"
- Add multi-scene design guidance
- Add mechanic selection rationale requirement

**New system prompt covers:**
```
## Available Mechanics (choose based on content, not Bloom's)
- drag_drop: Spatial identification. Config: zone_labels, interaction settings.
- sequencing: Temporal ordering. Config: items + correct_order + layout_mode.
- trace_path: Flow paths. Config: waypoints + path_type + particle_theme.
- sorting_categories: Classification. Config: categories + items + sort_mode.
- memory_match: Term-definition recall. Config: pairs + game_variant.
- click_to_identify: Identification prompts. Config: prompt_style + selection_mode.
```

### Fix 1.2: Task Prompt Rewrite

**File:** `backend/app/agents/game_designer_v3.py` lines 127-221

**Changes:**
- Inject `mechanic_context_v3` (structured feasibility) instead of raw DK dump
- Keep `blooms_level` but add disclaimer: "informational context only"
- Increase DK field injection (all 13 fields, not just 5)
- Inject label_descriptions, sequence_flow_data, comparison_data as structured sections
- Add: "choose from ready mechanics" instruction
- Add: "provide FULL mechanic configs" instruction with per-mechanic templates

### Fix 1.3: Max Iterations

Increase from 6 → 8.

### Fix 1.4: analyze_pedagogy Tool Fix

**File:** `backend/app/tools/game_design_v3_tools.py` lines 108-111

**Remove:** Forced `drag_drop` baseline injection.
**Remove:** Bloom's level as mechanic selector.
**Keep:** Bloom's as informational context.
**Add:** Content-signal-based recommendations using domain knowledge.

### Fix 1.5: check_capabilities Tool Fix

**File:** `backend/app/tools/game_design_v3_tools.py`

Replace static `MECHANIC_DATA_NEEDS` with dynamic `build_mechanic_context()` output.
Show actual data snippets per mechanic.
Return per-mechanic config templates.

### Fix 1.6: validate_design Tool Severity Increase

**File:** `backend/app/tools/game_design_v3_tools.py`

Validate mechanic configs have required fields (not just type).
Increase error severity for missing configs.

### Fix 1.7: Build Mechanic Context

**File:** `backend/app/tools/game_design_v3_tools.py` (new function)

Add `build_mechanic_context()` function (see Section 2).
Call it from `game_designer_v3.build_task_prompt()` using state domain_knowledge.
Store result in `state["mechanic_context_v3"]`.

---

## 6. Phase 2: Scene Architect V3 + Tools <a id="6-phase-2"></a>

### Fix 2.1: System Prompt Rewrite

**File:** `backend/app/agents/scene_architect_v3.py` lines 27-76

**Changes:**
- Add ALL 6 priority mechanics with detailed config guidance (currently missing memory_match, trace_path particle/curve config)
- Add asset_requirements generation step
- Emphasize: `generate_mechanic_content` is MANDATORY for ALL non-drag_drop mechanics
- Add per-mechanic "what zones/configs to produce" section
- Add image requirement guidance per mechanic type:
  - trace_path: "Image must show pathways/connections between structures"
  - sequencing: "Image should show stages/phases spatially separated"
  - sorting_categories: "Image should show items clearly distinguishable"

### Fix 2.2: Task Prompt Rewrite

**File:** `backend/app/agents/scene_architect_v3.py` lines 101-200

**Changes:**
- Inject mechanic types per scene from game_design
- Inject mechanic config data from game_design (sequence items, categories, etc.)
- Inject domain knowledge fields relevant to each mechanic (sequence_flow_data, comparison_data, label_descriptions)
- Add `generate_mechanic_content` step for EVERY non-drag_drop mechanic
- Add asset_requirements generation step

### Fix 2.3: Max Iterations

Increase from 8 → 15. Multi-scene multi-mechanic needs: 3 scenes × (layout + schema + mechanic_content + validate) + submit.

### Fix 2.4: generate_mechanic_content Tool Expansion

**File:** `backend/app/tools/scene_architect_tools.py`

**Per-mechanic fixes:**

**sequencing** (lines 233-271):
- Read items/correct_order from game_design mechanic config (not just DK)
- Generate `layout_mode` based on content type
- Generate `connector_style`
- Add `instruction_text` to output
- Include distractor items if game_design has them

**sorting_categories** (lines 274-325):
- Read categories/items from game_design mechanic config
- Generate `sort_mode` based on category relationships
- Generate `container_style`
- Fix fragile category matching (L282-288 case-insensitive substring)
- For Venn: mark items with multi-category assignments

**memory_match** (lines 367-380):
- Replace generic fallback description (`f"A part of the {question[:30]}..."`) with LLM-generated descriptions
- Read pairs from game_design mechanic config
- Generate `match_type` based on pair content
- Include `explanation` for each pair
- Cap at 12 pairs (not 10) for 4x3 or 3x4 grid

**click_to_identify** (lines 217-230):
- Generate prompts based on `prompt_style` (naming vs functional)
- Generate selection order based on difficulty progression

**trace_path** (lines 182-214):
- Generate `curve_type` based on path nature (circulatory=curved, linear=straight)
- Generate `particle_theme` based on content (blood=blood_cells, electrical=electrons, etc.)
- Generate `color_transition` when path has semantic meaning (venous→arterial)
- Add `direction_arrows` config
- Include `instruction_text`

**ALL mechanics**: Generate `asset_requirements` array alongside config:
```python
asset_reqs = []
if mechanic_type in ("drag_drop", "click_to_identify", "trace_path"):
    asset_reqs.append({
        "asset_type": "diagram_image",
        "asset_id": f"scene_{scene_number}_diagram",
        "description": f"Clean educational diagram of {subject}...",
        "mechanic_type": mechanic_type,
        "priority": "required"
    })
elif mechanic_type == "sequencing":
    asset_reqs.append({"asset_type": "diagram_image", ...})
    for item in items:
        asset_reqs.append({"asset_type": "item_illustration", "for_item_id": item["id"], "priority": "optional"})
```

### Fix 2.5: Domain Knowledge Injection

Scene architect currently reads ONLY canonical_labels. Expand in build_task_prompt:

```python
dk = state.get("domain_knowledge", {})
if dk.get("sequence_flow_data"):
    sections.append(f"## Sequence Flow Data\n{json.dumps(dk['sequence_flow_data'], indent=2)[:1500]}")
if dk.get("comparison_data"):
    sections.append(f"## Comparison Data\n{json.dumps(dk['comparison_data'], indent=2)[:1500]}")
if dk.get("label_descriptions"):
    sections.append(f"## Label Descriptions\n{json.dumps(dk['label_descriptions'], indent=2)[:1500]}")
```

---

## 7. Phase 3: Interaction Designer V3 + Tools <a id="7-phase-3"></a>

### Fix 3.1: System Prompt Rewrite

**File:** `backend/app/agents/interaction_designer_v3.py` lines 27-70

**Changes:**
- Add per-mechanic scoring strategy guidance (currently entirely generic)
- Add per-mechanic feedback style guidance
- Emphasize `enrich_mechanic_content` is MANDATORY for every mechanic
- Add mode_transitions guidance for multi-mechanic scenes

Per-mechanic scoring/feedback sections:
```
- drag_drop: Standard scoring. Feedback explains why label belongs at location.
- sequencing: Positional scoring with partial credit. Feedback explains ordering logic.
- trace_path: Progressive scoring with order dependency. Feedback explains path logic.
- sorting_categories: Category-based scoring. Feedback explains WHY item belongs in category.
- memory_match: Pair-based scoring + attempt efficiency. Feedback reveals term-definition connection.
- click_to_identify: Progressive scoring (harder zones worth more). Feedback names region and function.
```

### Fix 3.2: Task Prompt Rewrite

**File:** `backend/app/agents/interaction_designer_v3.py` lines 95-184

**Changes:**
- Inject mechanic types per scene from scene_specs
- Inject domain knowledge for content-specific feedback
- Add `enrich_mechanic_content` step for EVERY mechanic
- Add mode_transitions for multi-mechanic scenes

### Fix 3.3: Max Iterations

Increase from 8 → 15.

### Fix 3.4: enrich_mechanic_content Tool Expansion

**File:** `backend/app/tools/interaction_designer_tools.py` lines 218-350

Currently generic LLM enrichment. Add per-mechanic enrichment prompts:
- sequencing: "Why does step X come before step Y? What misconception leads to wrong ordering?"
- sorting: "Why does item X belong in category Y? What makes it confusable with category Z?"
- trace_path: "What happens at each waypoint? Why must the path visit them in this order?"
- memory_match: "What connects term X to definition Y? What common misconception confuses them?"
- click_to_identify: "What is the function of structure X? What other structure is it commonly confused with?"

### Fix 3.5: generate_misconception_feedback Tool Fix

**File:** `backend/app/tools/interaction_designer_tools.py` lines 113-211

Currently drag_drop-biased (trigger_label placed on wrong zone model). Add mechanic-specific misconception templates:
- sequencing: "Student thinks [step A] comes after [step B] because..."
- sorting: "Student places [item X] in [wrong category] because..."
- trace_path: "Student skips [waypoint] because..."
- memory_match: "Student confuses [term A] with [term B] because..."

### Fix 3.6: get_scoring_templates Expansion

**File:** `backend/app/tools/interaction_designer_tools.py` lines 25-106

Expand per-mechanic scoring formulas:
- sequencing: position_match count + Kendall tau coefficient option
- sorting: per-item + per-category accuracy
- memory_match: pairs_found + attempt_efficiency bonus
- click_to_identify: difficulty-weighted per-zone
- trace_path: progressive (waypoints visited * points, order bonus)

### Fix 3.7: validate_interactions Missing Checks

**File:** `backend/app/tools/interaction_designer_tools.py` lines 357-454

Add validation for:
- sorting_categories: categories matching scene_spec
- memory_match: pair explanations present
- branching_scenario: node graph validity
- compare_contrast: expected_categories coverage

---

## 8. Phase 4: Asset Generator V3 + Tools <a id="8-phase-4"></a>

### Fix 4.1: System Prompt Rewrite

**File:** `backend/app/agents/asset_generator_v3.py` lines 28-65

**Changes:**
- Read `asset_requirements` from scene_specs (new field)
- Process ALL asset types (not just diagram_image)
- Add per-mechanic visual guidance
- Support optional item illustrations
- Add mechanic-aware image generation hints

### Fix 4.2: Task Prompt Rewrite

**File:** `backend/app/agents/asset_generator_v3.py` lines 90-185

**Changes:**
- Inject `asset_requirements` from scene_specs
- Inject mechanic types per scene
- Inject mechanic-specific image requirements
- Classify assets as required vs optional
- Add fallback instructions for missing scenes

### Fix 4.3: Max Iterations

Increase from 8 → 15.

### Fix 4.4: New Tool — generate_item_illustration

**File:** `backend/app/tools/asset_generator_tools.py` (new function)

```python
async def generate_item_illustration_impl(
    item_id: str,
    description: str,
    style: str = "simple educational illustration, white background",
    size: int = 256,
) -> Dict[str, Any]:
    """Generate a small illustration for a sequence item, sorting item, or memory card."""
    from app.agents.diagram_image_generator import generate_with_gemini
    prompt = f"Create a clear {size}x{size} illustration: {description}. Style: {style}. No text."
    result = await generate_with_gemini(prompt=prompt)
    # Save to pipeline_outputs/v3_assets/{run_id}/items/{item_id}.png
    # Return {"item_id": item_id, "image_path": path}
```

Register as tool in `register_asset_generator_tools()`.

### Fix 4.5: submit_assets Scene Count Validation

**File:** `backend/app/tools/asset_generator_tools.py` ~line 928

Add warning when scene count doesn't match game_design:
```python
expected = len(game_design.get("scenes", []))
if expected > 0 and len(scenes) < expected:
    warnings.append(f"Only {len(scenes)}/{expected} scenes have assets")
```

### Fix 4.6: Mechanic-Aware Image Generation

Already partially implemented via `_MECHANIC_IMAGE_HINTS`. Verify all 6 priority mechanics have entries:
- drag_drop: "Clear structures with distinct boundaries"
- click_to_identify: "Clear structures, high contrast boundaries"
- trace_path: "MUST show pathways/connections between structures"
- sequencing: "Show stages/phases clearly separated in spatial arrangement"
- sorting_categories: "Show distinct items that can be categorized"
- memory_match: "Clear, identifiable structures for card content"

---

## 9. Phase 5: Blueprint Assembler V3 + Tools <a id="9-phase-5"></a>

### Fix 5.1: Max Iterations

**File:** `backend/app/agents/blueprint_assembler_v3.py`

Increase from 4 → 6 (need repair cycle headroom).

### Fix 5.2: Expand Per-Mechanic Config Population

**File:** `backend/app/tools/blueprint_assembler_tools.py` lines 557-763

Ensure ALL 6 priority mechanics populate EXPANDED config fields:

**sequencing** (lines 627-638):
```python
sequence_cfg = {
    "sequenceType": config.get("sequence_type", "linear"),
    "items": [...],
    "correctOrder": [...],
    "allowPartialCredit": True,
    "instructionText": config.get("instruction_text"),
    # NEW expanded:
    "layoutMode": config.get("layout_mode", "vertical_timeline"),
    "itemCardType": config.get("item_card_type", "text_only"),
    "connectorStyle": config.get("connector_style", "arrow"),
    "hasDistractors": config.get("has_distractors", False),
    "distractorItems": config.get("distractor_items", []),
}
```

**sorting_categories** (lines 674-711):
```python
sorting_cfg = {
    "items": [...],
    "categories": [...],
    "allowPartialCredit": True,
    "showCategoryHints": config.get("show_category_hints", False),
    "instructions": config.get("instruction_text"),
    # NEW expanded:
    "sortMode": config.get("sort_mode", "bucket"),
    "itemCardType": config.get("item_card_type", "text_only"),
    "containerStyle": config.get("container_style", "bucket"),
    "submitMode": config.get("submit_mode", "batch_submit"),
    "allowMultiCategory": config.get("allow_multi_category", False),
}
```

**memory_match** (lines 715-736):
```python
memory_cfg = {
    "pairs": [...],  # {id, front, back, frontType, backType, explanation, matchType}
    "gridSize": config.get("grid_size"),
    "flipDurationMs": config.get("flip_duration_ms", 600),
    "showAttemptsCounter": True,
    "instructions": config.get("instruction_text"),
    # NEW expanded:
    "gameVariant": config.get("game_variant", "classic"),
    "cardFaceType": config.get("card_face_type", "text_text"),
    "matchType": config.get("match_type", "term_to_definition"),
    "matchedCardBehavior": config.get("matched_card_behavior", "fade"),
    "mismatchPenalty": config.get("mismatch_penalty", "none"),
}
```

**trace_path** (lines 572-587):
```python
# Existing waypoint→path conversion is good. Add:
path_entry = {
    "id": ...,
    "waypoints": path_waypoints,
    "description": ...,
    "requiresOrder": ...,
}
trace_path_cfg = {
    "pathType": config.get("path_type", "linear"),
    "drawingMode": config.get("drawing_mode", "click_waypoint"),
    "curveType": config.get("curve_type", "straight"),
    "directionArrows": config.get("direction_arrows", True),
    "particleTheme": config.get("particle_theme"),
    "colorTransition": config.get("color_transition"),
    "instructions": config.get("instruction_text"),
}
blueprint["tracePathConfig"] = trace_path_cfg
```

**click_to_identify** (lines 591-623):
```python
click_cfg = {
    "promptStyle": config.get("prompt_style", "naming"),
    "selectionMode": config.get("selection_mode", "sequential"),
    "highlightStyle": config.get("highlight_style", "outlined"),
    "exploreModeEnabled": config.get("explore_mode_enabled", False),
    "prompts": [...],
    "instructions": config.get("instruction_text"),
}
blueprint["clickToIdentifyConfig"] = click_cfg
```

**drag_drop** (no specific lines — add NEW):
```python
drag_cfg = {
    "placementMode": "drag_drop",
    "feedbackTiming": "immediate",
    "leaderLineStyle": "none",
    "placementAnimation": "spring",
    "zoomEnabled": False,
    "trayPosition": "bottom",
    "trayLayout": "horizontal",
}
blueprint["dragDropConfig"] = drag_cfg
```

### Fix 5.3: Populate mechanic_type in game_sequence scenes

**File:** `backend/app/tools/blueprint_assembler_tools.py`

In scene assembly loop:
```python
if scene_mechanics:
    frontend_scene["mechanic_type"] = scene_mechanics[0].get("type", "drag_drop")
else:
    frontend_scene["mechanic_type"] = "drag_drop"
```

### Fix 5.4: Fix Scoring/Feedback List→Dict Conversion

**File:** `backend/app/tools/blueprint_assembler_tools.py` lines 654-662

Already identified. Ensure scoring_data/feedback_data list→dict conversion works for ALL mechanic types (not just first element).

### Fix 5.5: Item Asset URL Injection

When `generated_item_assets_v3` contains item illustrations, inject URLs into blueprint config:
```python
item_assets = ctx.get("generated_item_assets_v3", {}) or {}
if item_assets and blueprint.get("sequenceConfig"):
    for item in blueprint["sequenceConfig"].get("items", []):
        url = item_assets.get(item.get("id"))
        if url:
            item["imageUrl"] = url
```

### Fix 5.6: validate_blueprint Missing Mechanic Checks

**File:** `backend/app/tools/blueprint_assembler_tools.py` lines 1131-1177

Add validation for:
- memory_match: pairs present + pairs.length >= 4
- branching_scenario: nodes present + startNodeId valid
- compare_contrast: expectedCategories present
- trace_path: tracePathConfig present when mode is trace_path
- click_to_identify: clickToIdentifyConfig present when mode is click_to_identify

### Fix 5.7: repair_blueprint Missing Mechanic Repairs

**File:** `backend/app/tools/blueprint_assembler_tools.py` lines 1403-1461

Add auto-repair for:
- sequencing: generate items/correctOrder from scene_spec if missing
- sorting: generate categories/items from scene_spec if missing
- memory_match: generate pairs from scene_spec if missing
- Default scoring if missing for any mechanic

---

## 10. Phase 6: Validators <a id="10-phase-6"></a>

### Fix 6.1: Design Validator — Severity + Missing Mechanics

**File:** `backend/app/agents/design_validator.py`

**6.1a** Increase severity: WARNING (-0.05) → ERROR (-0.15) for missing mechanic configs on lines 112, 115, 120, 123, 128, 131, 136, 139, 144, 147, 152, 155, 160, 163.

**6.1b** Add missing mechanics:
```python
if mech.type == "compare_contrast":
    if not mech.compare_config:
        issues.append(f"ERROR: Scene {sn} compare_contrast missing compare_config")
        score -= 0.15

if mech.type == "hierarchical":
    if not (design.labels and design.labels.hierarchy and design.labels.hierarchy.get("enabled")):
        issues.append(f"WARNING: Scene {sn} hierarchical needs labels.hierarchy")
        score -= 0.1
```

**6.1c** Add CONTENT validation:
- sequencing: correct_order has >= 3 items
- sorting: >= 2 categories, >= 3 items
- memory_match: >= 4 pairs
- trace_path: >= 3 waypoints
- click_to_identify: prompts or click_options present

**6.1d** Remove any hardcoded Bloom's-to-mechanic mappings (if present). Keep Bloom's as informational.

### Fix 6.2: Scene Validator — Content Validation

**File:** `backend/app/agents/schemas/scene_spec_v3.py` validate_scene_specs()

Add:
- compare_contrast: expected_categories exist
- sorting: items reference valid category IDs
- sequencing: correct_order references valid item IDs
- memory_match: pairs have front AND back content
- branching: node graph connectivity (start_node reachable)

### Fix 6.3: Interaction Validator

**File:** `backend/app/agents/interaction_validator.py`

- Remove any drag_drop default fallback for unknown modes
- Remove any Bloom's cognitive mapping in validation logic
- Add per-mechanic scoring strategy validation
- Validate feedback messages are content-specific (not generic "Correct!"/"Try again")

---

## 11. Phase 7: Frontend Types & Components <a id="11-phase-7"></a>

### Fix 7.1: types.ts Expansions

**File:** `frontend/src/components/templates/InteractiveDiagramGame/types.ts`

**7.1a** Add new interfaces:
- `ClickToIdentifyConfig` (7 fields)
- `TracePathConfig` (8 fields)
- `DragDropConfig` (8 fields)

**7.1b** Expand existing interfaces:
- `SequenceConfig`: +layoutMode, itemCardType, connectorStyle, hasDistractors, distractorItems
- `SequenceConfigItem`: +imageUrl, iconName
- `SortingConfig`: +sortMode, itemCardType, containerStyle, submitMode, allowMultiCategory
- `SortingItem`: +imageUrl, correctCategoryIds (array)
- `MemoryMatchConfig`: +gameVariant, cardFaceType, matchType, matchedCardBehavior, mismatchPenalty
- `MemoryMatchPair`: +explanation, matchType
- `CompareConfig`: (exists, extend when compare_contrast is prioritized)
- `BranchingConfig`: (exists, extend when branching is prioritized)

**7.1c** Add PathWaypoint expansion: +type, controlPoints

**7.1d** Add to InteractiveDiagramBlueprint:
- `clickToIdentifyConfig?: ClickToIdentifyConfig`
- `tracePathConfig?: TracePathConfig`
- `dragDropConfig?: DragDropConfig`

### Fix 7.2: MechanicRouter.tsx Updates

**File:** `frontend/src/components/templates/InteractiveDiagramGame/MechanicRouter.tsx`

- Pass `tracePathConfig` to PathDrawer
- Pass `clickToIdentifyConfig` to HotspotManager
- Pass `dragDropConfig` to DiagramCanvas/drag_drop components

### Fix 7.3: SequenceBuilder.tsx Rewrite

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/SequenceBuilder.tsx`

**Current:** 319 lines, text-only vertical list with drag handles.

**Rewrite to support:**
- Read `layoutMode` → render horizontal_timeline or vertical_timeline
- Read `itemCardType` → render text-only or text-with-image cards
- Read `connectorStyle` → render arrow/dashed connectors between items
- Read `hasDistractors` → include distractor items in source pool
- Numbered slot positions
- Source area (unplaced items pool) → track (placement slots)
- Position-based scoring with partial credit

**New sub-components:**
- `SequenceItemCard` — Rich item card (text, optional image, drag handle)
- `SequenceConnector` — SVG arrow/line between items
- `SequenceSlot` — Drop target slot (numbered/outlined)

### Fix 7.4: SortingCategories.tsx Expansion

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/SortingCategories.tsx`

**Current:** 404 lines, bucket mode only.

**Add:**
- Read `sortMode` → switch between BucketSort (existing) and VennDiagramSort (new)
- Read `containerStyle` → styled containers
- Read `itemCardType` → text or text-with-image items
- Read `submitMode` → batch (existing) or immediate feedback
- Read `allowMultiCategory` → for Venn mode

**New sub-component:** `VennDiagramSort` — SVG 2-circle rendering with 3 drop regions (A-only, B-only, A∩B overlap)

### Fix 7.5: MemoryMatch.tsx Fix + Expansion

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/MemoryMatch.tsx`

**Current:** 310 lines, opacity-based "flip", no match/mismatch animations.

**Fix 3D Flip (CRITICAL):**
```css
.card-container { perspective: 1000px; }
.card-inner { transition: transform 0.6s; transform-style: preserve-3d; }
.card-inner.flipped { transform: rotateY(180deg); }
.card-front, .card-back { backface-visibility: hidden; position: absolute; }
.card-back { transform: rotateY(180deg); }
```

**Add:**
- Read `gameVariant` → classic (existing grid) or column_match (new two-column layout)
- Read `matchedCardBehavior` → fade/shrink/checkmark on correct match
- Read `mismatchPenalty` → score handling
- Match animation: green pulse + scale on correct
- Mismatch animation: red flash + shake on incorrect
- Read `explanation` from pairs → show explanation popover on correct match

**New sub-component:** `ColumnMatchLayout` — Two columns with click-to-match interaction

### Fix 7.6: HotspotManager.tsx Polish

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/HotspotManager.tsx`

**Current:** 296 lines, 3 zone states, basic prompts.

**Add:**
- Read `clickToIdentifyConfig` from blueprint
- Implement `promptStyle`: "naming" → "Click on the [label]", "functional" → custom prompt text
- Implement `highlightStyle`: subtle/outlined/invisible zone rendering
- Add hover state (4th state) to zone highlight machine
- Fix: in `any_order` mode, don't leak zone labels in prompt text

### Fix 7.7: PathDrawer.tsx Expansion

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/PathDrawer.tsx`

**Current:** 397 lines, straight dashed lines only, no curves or particles.

**Add:**
- Read `tracePathConfig` from blueprint
- Implement `curveType`: straight (existing) + quadratic bezier + catmull_rom
- Implement `directionArrows`: distributed arrows along path
- Implement `colorTransition`: gradient color from start_color to end_color
- Implement `particleTheme`: animated SVG particles flowing along completed path
- Implement `pathType`: linear (existing) + circular (loop connector at end)

**New sub-components:**
- `SVGCurvedPath` — Renders bezier curves between waypoints
- `AnimatedParticleSystem` — Particles flowing along completed path

### Fix 7.8: DiagramCanvas.tsx Config Reading

**File:** `frontend/src/components/templates/InteractiveDiagramGame/DiagramCanvas.tsx`

**Add:**
- Read `dragDropConfig` from blueprint
- Implement `placementAnimation`: spring (CSS cubic-bezier), ease, instant
- Implement shake animation for incorrect placement
- Add `trayLayout` config reading (horizontal/vertical/grid)

### Fix 7.9: DescriptionMatcher.tsx Bug Fix

**File:** `frontend/src/components/templates/InteractiveDiagramGame/interactions/DescriptionMatcher.tsx`

**Fix MC option re-shuffle bug** (~line 420-450): Options use `sort(() => Math.random() - 0.5)` inside render function causing re-shuffle on every render. Memoize shuffled options with `useMemo`.

---

## 12. Phase 8: Zustand Store & Game Logic <a id="12-phase-8"></a>

### Fix 8.1: Score Delta Accumulation

**File:** `frontend/src/components/templates/InteractiveDiagramGame/hooks/useInteractiveDiagramState.ts`

Fix score overwrites at lines ~458, 475, 645. All score updates must ADD deltas, never SET absolute values:
```typescript
// WRONG: set({ score: newScore })
// RIGHT: set(state => ({ score: state.score + delta }))
```

### Fix 8.2: Per-Mechanic Completion Counting

Fix at ~line 364. Count labels in CURRENT mechanic/task subset, not all blueprint labels.

### Fix 8.3: Mode Transition Timer Cleanup

Fix setTimeout leak at ~line 858. Use `useEffect` cleanup or store the timer ID and clear on unmount.

### Fix 8.4: advanceToNextTask max_score Fix

Fix at ~line 1026. Use actual max score from blueprint config, not current score (which makes percentage always 100%).

### Fix 8.5: transitionToMode Immutability Fix

Fix at ~line 874. Don't mutate `modeHistory` in-place (Zustand immutability violation). Use spread: `[...state.modeHistory, newMode]`.

### Fix 8.6: New Store Actions

```typescript
// Sequencing (extend existing)
updateSequenceOrder: (newOrder: string[]) => void
submitSequence: () => { correct: number; total: number; delta: number }

// Sorting (extend existing)
updateSortingPlacement: (itemId: string, categoryId: string) => void
submitSorting: () => { correct: number; total: number; delta: number }

// Memory Match (extend existing)
recordMemoryMatch: (pairId: string) => void
recordMemoryMismatch: () => void

// Trace Path
updatePathProgress: (waypointId: string) => void
completePath: () => { delta: number }
```

### Fix 8.7: _sceneToBlueprint Missing Fields

Forward new config fields when converting scene to blueprint:
- `tracePathConfig`
- `clickToIdentifyConfig`
- `dragDropConfig`

### Fix 8.8: resetGame Action Fix

Previously identified in audit Fix 1.11. Ensure resetGame properly resets ALL per-mechanic progress types.

---

## 13. Verification Plan <a id="13-verification"></a>

### Test Queries

| # | Query | Expected Mechanics | Scenes |
|---|-------|-------------------|--------|
| 1 | "Label the main parts of a flower" | drag_drop | 1 |
| 2 | "Arrange the stages of mitosis in order: prophase, metaphase, anaphase, telophase" | sequencing | 1 |
| 3 | "Trace the path of blood flow through the human heart from vena cava through each chamber to the aorta" | trace_path | 1 |
| 4 | "Sort these animals into vertebrates and invertebrates: cat, spider, fish, ant, frog, butterfly" | sorting_categories | 1 |
| 5 | "Match these biology terms to their definitions: mitosis, meiosis, photosynthesis, respiration, osmosis, diffusion" | memory_match | 1 |
| 6 | "Identify the parts of the human heart" | click_to_identify | 1 |
| 7 | "Label the parts of a cell and arrange organelle sizes from smallest to largest" | drag_drop + sequencing | 2 |
| 8 | "Trace the path of blood through the heart and identify each chamber" | trace_path + click_to_identify | 2 |

### Per-Test Verification Checklist

**Backend Pipeline:**
- [ ] All 11+ stages complete (no errors, no null outputs)
- [ ] game_designer chose mechanics from content (not forced drag_drop)
- [ ] game_designer provided FULL mechanic configs (not empty `{}`)
- [ ] scene_architect called generate_mechanic_content for each non-drag_drop mechanic
- [ ] scene_architect generated asset_requirements
- [ ] interaction_designer called enrich_mechanic_content for each mechanic
- [ ] asset_generator generated all "required" assets
- [ ] blueprint has expanded config fields (layoutMode, matchType, curveType, etc.)
- [ ] mechanic_type populated in game_sequence scenes
- [ ] generation_complete = True

**Frontend Rendering:**
- [ ] Correct interaction component renders (SequenceBuilder, PathDrawer, etc.)
- [ ] Component reads config from blueprint (not hardcoded defaults)
- [ ] Interaction works (drag, click, match, sequence, sort, trace)
- [ ] Scoring works (correct/incorrect tracking, delta accumulation)
- [ ] Multi-scene transition works (if applicable)
- [ ] Images load (diagram)

---

## 14. Fix Index <a id="14-fix-index"></a>

### Phase 0: Infrastructure (17 fixes)

| ID | File | Description |
|----|------|-------------|
| 0.1a | state.py | Add 3 V3 state fields (asset_requirements, item_assets, mechanic_context) |
| 0.1b | state.py | Fix DomainKnowledge TypedDict — add 5 missing fields |
| 0.2a | game_design_v3.py | Expand SequenceDesign (+5 fields) |
| 0.2b | game_design_v3.py | Expand SortingDesign (+5 fields) |
| 0.2c | game_design_v3.py | Expand MemoryMatchDesign (+5 fields) |
| 0.2d | game_design_v3.py | Expand ClickDesign (+3 fields) |
| 0.2e | game_design_v3.py | Expand PathDesign (+5 fields) |
| 0.3a | interactive_diagram.py | Expand SequenceConfig + SequenceConfigItem |
| 0.3b | interactive_diagram.py | Expand SortingConfig + SortingItem |
| 0.3c | interactive_diagram.py | Expand MemoryMatchConfig + MemoryMatchPair |
| 0.3d | interactive_diagram.py | Add ClickToIdentifyConfig |
| 0.3e | interactive_diagram.py | Add TracePathConfig |
| 0.3f | interactive_diagram.py | Add DragDropConfig |
| 0.4 | scene_spec_v3.py | Add SceneAssetRequirement + asset_requirements field |
| 0.5a | interaction_spec_v3.py | Add missing mechanics to MECHANIC_TRIGGER_MAP |
| 0.5b | interaction_spec_v3.py | Add missing mechanic validation |
| 0.6a | graph.py | Fix retry logic (>= 2 → >= 3) |
| 0.6b | graph.py | Fix topology metadata |
| 0.7a | generate.py | Add V3 image serving route |
| 0.7b | generate.py | Fix multi-scene URL proxying |
| 0.7c | generate.py | Add V3 agent output recording |
| 0.7d | generate.py | Add pipeline timeout |
| 0.8a | agent_models.py | Add V3 agents to non-gemini presets |

### Phase 1: Game Designer (7 fixes)

| ID | File | Description |
|----|------|-------------|
| 1.1 | game_designer_v3.py | System prompt rewrite (Bloom's as context, 6 mechanics) |
| 1.2 | game_designer_v3.py | Task prompt rewrite (inject mechanic_context) |
| 1.3 | game_designer_v3.py | Max iterations 6→8 |
| 1.4 | game_design_v3_tools.py | Fix analyze_pedagogy (remove drag_drop bias) |
| 1.5 | game_design_v3_tools.py | Fix check_capabilities (dynamic feasibility) |
| 1.6 | game_design_v3_tools.py | Increase validate_design severity |
| 1.7 | game_design_v3_tools.py | Add build_mechanic_context() function |

### Phase 2: Scene Architect (5 fixes)

| ID | File | Description |
|----|------|-------------|
| 2.1 | scene_architect_v3.py | System prompt rewrite (6 mechanics + asset reqs) |
| 2.2 | scene_architect_v3.py | Task prompt rewrite (inject mechanics + DK) |
| 2.3 | scene_architect_v3.py | Max iterations 8→15 |
| 2.4 | scene_architect_tools.py | Expand generate_mechanic_content (6 mechanics + asset reqs) |
| 2.5 | scene_architect_v3.py | Inject DK fields (sequence, comparison, descriptions) |

### Phase 3: Interaction Designer (7 fixes)

| ID | File | Description |
|----|------|-------------|
| 3.1 | interaction_designer_v3.py | System prompt rewrite (per-mechanic scoring/feedback) |
| 3.2 | interaction_designer_v3.py | Task prompt rewrite (inject mechanics + DK) |
| 3.3 | interaction_designer_v3.py | Max iterations 8→15 |
| 3.4 | interaction_designer_tools.py | Expand enrich_mechanic_content (per-mechanic prompts) |
| 3.5 | interaction_designer_tools.py | Fix generate_misconception_feedback (mechanic-specific) |
| 3.6 | interaction_designer_tools.py | Expand get_scoring_templates (per-mechanic formulas) |
| 3.7 | interaction_designer_tools.py | Add missing validate_interactions checks |

### Phase 4: Asset Generator (6 fixes)

| ID | File | Description |
|----|------|-------------|
| 4.1 | asset_generator_v3.py | System prompt rewrite (asset types + mechanic guidance) |
| 4.2 | asset_generator_v3.py | Task prompt rewrite (inject asset_requirements) |
| 4.3 | asset_generator_v3.py | Max iterations 8→15 |
| 4.4 | asset_generator_tools.py | New tool: generate_item_illustration |
| 4.5 | asset_generator_tools.py | submit_assets scene count validation |
| 4.6 | asset_generator_tools.py | Verify _MECHANIC_IMAGE_HINTS for all 6 |

### Phase 5: Blueprint Assembler (7 fixes)

| ID | File | Description |
|----|------|-------------|
| 5.1 | blueprint_assembler_v3.py | Max iterations 4→6 |
| 5.2 | blueprint_assembler_tools.py | Expand per-mechanic config population (6 mechanics) |
| 5.3 | blueprint_assembler_tools.py | Populate mechanic_type in game_sequence scenes |
| 5.4 | blueprint_assembler_tools.py | Fix scoring/feedback list→dict conversion |
| 5.5 | blueprint_assembler_tools.py | Item asset URL injection |
| 5.6 | blueprint_assembler_tools.py | Add missing validate_blueprint mechanic checks |
| 5.7 | blueprint_assembler_tools.py | Add missing repair_blueprint mechanic repairs |

### Phase 6: Validators (3 fixes)

| ID | File | Description |
|----|------|-------------|
| 6.1 | design_validator.py | Severity increase + missing mechanics + content validation |
| 6.2 | scene_spec_v3.py | Content validation for all mechanics |
| 6.3 | interaction_validator.py | Remove Bloom's mapping, add per-mechanic checks |

### Phase 7: Frontend (10 fixes)

| ID | File | Description |
|----|------|-------------|
| 7.1 | types.ts | Add 3 interfaces, expand 6, expand 3 base types |
| 7.2 | MechanicRouter.tsx | Pass new config props |
| 7.3 | SequenceBuilder.tsx | Rewrite (layout modes, item cards, connectors, slots) |
| 7.4 | SortingCategories.tsx | Add sortMode reading, Venn 2-circle mode |
| 7.5 | MemoryMatch.tsx | Fix 3D flip, add match/mismatch animations, config reading |
| 7.6 | HotspotManager.tsx | Add config reading, prompt styles, highlight states |
| 7.7 | PathDrawer.tsx | Add curve types, particles, color transitions, direction arrows |
| 7.8 | DiagramCanvas.tsx | Add dragDropConfig reading, snap physics |
| 7.9 | DescriptionMatcher.tsx | Fix MC option re-shuffle bug |

### Phase 8: Zustand Store (8 fixes)

| ID | File | Description |
|----|------|-------------|
| 8.1 | useInteractiveDiagramState.ts | Fix score delta accumulation (never overwrite) |
| 8.2 | useInteractiveDiagramState.ts | Fix per-mechanic completion counting |
| 8.3 | useInteractiveDiagramState.ts | Fix mode transition timer leak |
| 8.4 | useInteractiveDiagramState.ts | Fix advanceToNextTask max_score |
| 8.5 | useInteractiveDiagramState.ts | Fix transitionToMode immutability |
| 8.6 | useInteractiveDiagramState.ts | Add new store actions (sequence, sorting, memory, trace) |
| 8.7 | useInteractiveDiagramState.ts | Forward new config fields in _sceneToBlueprint |
| 8.8 | useInteractiveDiagramState.ts | Fix resetGame for all mechanics |

---

## Summary

| Phase | Files | Fixes | Description |
|-------|-------|-------|-------------|
| 0 | 8 | 23 | State, schemas, graph, routes, models |
| 1 | 2 | 7 | Game designer agent + tools |
| 2 | 2 | 5 | Scene architect agent + tools |
| 3 | 2 | 7 | Interaction designer agent + tools |
| 4 | 2 | 6 | Asset generator agent + tools |
| 5 | 2 | 7 | Blueprint assembler agent + tools |
| 6 | 3 | 3 | Validators |
| 7 | 9 | 10 | Frontend types + components |
| 8 | 1 | 8 | Zustand store |
| **Total** | **~25 files** | **76 fixes** | |

### Execution Order

1. **Phase 0** first (all other phases depend on infrastructure)
2. **Phases 1-6** can run in parallel (all depend only on Phase 0)
3. **Phase 7** depends on Phase 5 (blueprint must produce correct configs)
4. **Phase 8** depends on Phase 7 (store must match component needs)

### Estimated Lines Changed

| Phase | Estimated Lines |
|-------|----------------|
| 0 | ~300 |
| 1 | ~200 |
| 2 | ~250 |
| 3 | ~150 |
| 4 | ~200 |
| 5 | ~200 |
| 6 | ~100 |
| 7 | ~900 |
| 8 | ~200 |
| **Total** | **~2500** |
