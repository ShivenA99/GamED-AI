# V4 Pipeline Brainstorm — Graph-of-Graphs Architecture

**Date**: 2026-02-14
**Status**: BRAINSTORM — not yet approved for implementation

---

## 1. Design Philosophy

### 1.1 The Central Artifact: Game State Graph

Every game we generate is a **directed acyclic graph (DAG)** with three levels:

```
GameStateGraph
  ├── SceneGraph (Level 1): scene_1 → scene_2 → ... → scene_N → game_complete
  │     Each edge = scene transition (auto, button, score_gate)
  │
  ├── MechanicGraph per scene (Level 2):
  │     mechanic_A → mechanic_B → ... → scene_complete
  │     Each edge = mode transition (completion, score_threshold, user_choice)
  │     Can be:
  │       - Sequential: A → B → C
  │       - Hierarchical: A.children=[A1,A2,A3] → A.complete → B
  │       - Branching: A → (if score>80%) B : C
  │
  └── InteractionSpec per mechanic (Level 3 — frontend-handled):
        Content items, scoring rules, feedback messages
        The frontend mechanic components know how to run these
```

**If the Game State Graph is structurally valid (no dangling edges, all nodes reachable, all terminal states defined), the game is guaranteed to work.**

### 1.2 Pipeline = Progressive Graph Enrichment

Each pipeline phase adds a layer of detail to the Game State Graph:

| Phase | What it does | Graph changes |
|-------|-------------|---------------|
| Phase 0: Understanding | Analyze question, gather domain knowledge | Creates metadata context |
| Phase 1: Game Design | Design the game structure | Creates skeleton graph (scenes, mechanics, transitions) |
| Phase 2: Content Build | Generate content for each mechanic | Fills content nodes (items, prompts, descriptions) |
| Phase 3: Asset Pipeline | Generate/find visual assets | Fills asset nodes (images, zones, coordinates) |
| Phase 4: Assembly | Serialize graph to frontend format | Converts graph → InteractiveDiagramBlueprint JSON |

After each phase, a **structural validator** checks graph integrity. If invalid, the phase retries with the validator's feedback.

### 1.3 When to Use ReAct vs Single Structured Calls

| Pattern | When to use | Examples |
|---------|------------|---------|
| **Single structured call** | Input is complete, output schema is well-defined, task is bounded | Content generation, scoring design, classification |
| **ReAct loop** | Agent needs to search/retrieve before generating, or needs iterative refinement with tools | DK retrieval (web search), asset generation (image search + zone detection) |
| **Deterministic code** | Pure transformation, validation, assembly | Validators, blueprint assembler, format conversion |
| **Map-Reduce** | Same operation over multiple independent items | Content generation per mechanic, asset generation per scene |

**Rule**: Default to single structured calls. Only use ReAct where external tool access (search, vision) is genuinely needed.

---

## 2. Phase 0: Understanding (Sub-Graph)

### Purpose
Analyze the input question and gather all domain knowledge needed for game design.

### Sub-Graph Structure

```
question_text, question_options
        |
        v
  [input_analyzer]  ─────────────────────────────────────┐
  (single LLM call)                                       |
        |                                                 |
        v                                                 v
  pedagogical_context                              search_queries[]
  {blooms_level, subject,                          (derived from question)
   difficulty, learning_objectives,                        |
   misconceptions, content_structure}                      v
                                              [dk_retriever]
                                              (ReAct — web search + extraction)
                                                          |
                                                          v
                                                domain_knowledge
                                                {canonical_labels, label_descriptions,
                                                 sequence_flow_data, comparison_data,
                                                 hierarchical_relationships,
                                                 content_characteristics}
```

### Key Changes from Current

1. **input_analyzer** replaces both `input_enhancer` and `router`:
   - Outputs pedagogical context (same as before)
   - Also outputs `content_structure` classification:
     ```python
     content_structure = {
         "primary_type": "anatomical"|"process"|"comparative"|"categorical"|"hierarchical",
         "has_labels": bool,          # Are there things to label?
         "has_sequence": bool,        # Is there an order/process?
         "has_comparison": bool,      # Are there things to compare?
         "has_hierarchy": bool,       # Are there parent-child relationships?
         "has_categories": bool,      # Can things be sorted into groups?
         "visual_needs": "diagram"|"flowchart"|"dual_diagram"|"none",
     }
     ```
   - Single LLM call, ~200 tokens output
   - Model: gemini-2.5-flash (not flash-lite — this classification drives the entire pipeline)

2. **dk_retriever** stays ReAct (needs web search) but enhanced:
   - Reads `content_structure` to know what to search for
   - ALWAYS attempts label extraction, descriptions, and relevant enrichment
   - Does NOT use keyword-based intent detection — reads `content_structure` instead
   - Persists `dk_intent` to state (what it decided to search for and why)

3. **These two run in PARALLEL** (input_analyzer doesn't need DK, DK only needs question_text):
   - input_analyzer can run on flash (fast, cheap)
   - dk_retriever can start web search immediately
   - We merge results after both complete

### Token Budget
- input_analyzer: ~500 input + ~200 output = ~700 tokens
- dk_retriever: ~3000 input + ~2000 output (across multiple turns) = ~5000 tokens
- **Total Phase 0: ~5700 tokens** (vs current ~8000 with router overhead)

---

## 3. Phase 1: Game Design (Sub-Graph)

### Purpose
Design a complete, structurally valid game as a Game State Graph.

### Sub-Graph Structure

```
pedagogical_context + domain_knowledge + canonical_labels
        |
        v
  [game_designer]
  (single structured LLM call — NOT ReAct)
  (model: gemini-2.5-pro, temp: 0.7)
        |
        v
  game_plan (GameStateGraph skeleton)
        |
        v
  [game_plan_validator]
  (deterministic — checks graph structure)
        |
       / \
      /   \
  [pass]  [fail]
    |       |
    v       v → feedback → [game_designer] (retry, max 2)
  game_plan (validated)
```

### Why NOT ReAct for Game Designer

Current game_designer_v3 is ReAct with 5 tools (analyze_pedagogy, check_capabilities, get_example_designs, validate_design, submit_game_design). This wastes tokens because:

1. `analyze_pedagogy` just reads pedagogical_context — we can inject this into the prompt directly
2. `check_capabilities` returns a static list — we can inject this into the prompt directly
3. `get_example_designs` returns static examples — we can inject relevant examples into the prompt based on content_structure
4. `validate_design` is just Pydantic parsing — the graph validator does this better
5. `submit_game_design` is just "return the output" — unnecessary with structured output

**Instead**: One well-crafted prompt with all context injected, using Gemini's structured output (function calling) to produce the Game State Graph directly.

### Game State Graph Output Schema

```python
@dataclass
class GamePlan:
    """The complete game design as a validated graph."""

    title: str
    subject: str
    difficulty: str  # "beginner"|"intermediate"|"advanced"
    estimated_duration_minutes: int
    narrative_intro: str
    completion_message: str

    # Level 1: Scene Graph
    scenes: List[ScenePlan]
    scene_transitions: List[SceneTransition]  # How scenes connect

    # Global
    total_max_score: int  # Sum of all scene max_scores
    labels: LabelPlan     # zone_labels, distractor_labels, hierarchy

@dataclass
class ScenePlan:
    """One scene in the game."""

    scene_id: str         # "scene_1", "scene_2", ...
    scene_number: int
    title: str
    learning_goal: str
    narrative_intro: str

    # What this scene needs visually
    needs_diagram: bool
    image_spec: Optional[ImageSpec]  # null for content-only scenes

    # Which zone labels appear in this scene
    zone_labels: List[str]

    # Level 2: Mechanic Graph
    mechanics: List[MechanicNode]
    mechanic_transitions: List[MechanicTransition]
    starting_mechanic_id: str

    # Scene-level scoring
    max_score: int  # Sum of all mechanic max_scores in this scene

@dataclass
class ImageSpec:
    """Structured image requirements for asset generation."""
    description: str              # "cross-section of human heart showing chambers"
    must_include_structures: List[str]  # Labels that MUST be visible
    style: str                    # "anatomical_diagram"|"flowchart"|"comparison"|...
    annotation_preference: str    # "clean_unlabeled"|"lightly_labeled"|"fully_labeled"

@dataclass
class MechanicNode:
    """One mechanic within a scene's mechanic graph."""

    mechanic_id: str              # "mech_1_1", "mech_1_2", ...
    mechanic_type: str            # MechanicType enum
    zone_labels_used: List[str]   # Which zones this mechanic interacts with
    is_terminal: bool             # Is this the last mechanic in the scene?

    # Content requirements — tells Phase 2 EXACTLY what to generate
    content_requirements: ContentRequirements

    # Scoring expectation
    expected_item_count: int      # How many scoreable items
    points_per_item: int          # Points per correct action (default 10)
    max_score: int                # expected_item_count * points_per_item

@dataclass
class ContentRequirements:
    """What content Phase 2 must generate for this mechanic."""

    # Universal
    instruction_text: str         # What to tell the player

    # Mechanic-specific (only the relevant one is populated)
    drag_drop: Optional[DragDropReq]
    click_to_identify: Optional[ClickToIdentifyReq]
    trace_path: Optional[TracePathReq]
    sequencing: Optional[SequencingReq]
    sorting: Optional[SortingReq]
    memory_match: Optional[MemoryMatchReq]
    branching: Optional[BranchingReq]
    compare_contrast: Optional[CompareContrastReq]
    description_matching: Optional[DescriptionMatchingReq]
    hierarchical: Optional[HierarchicalReq]

# Example mechanic-specific requirements:

@dataclass
class SequencingReq:
    """What the scene architect must generate for a sequencing mechanic."""
    item_count: int               # How many items in the sequence
    sequence_topic: str           # "steps of mitosis", "blood flow through heart"
    include_distractors: bool     # Whether to add distractor items
    layout_mode: str              # "horizontal_timeline"|"vertical_list"|"circular_cycle"

@dataclass
class SortingReq:
    """What the scene architect must generate for a sorting mechanic."""
    category_count: int           # How many categories
    items_per_category: int       # Target items per category
    sorting_topic: str            # "classify blood cells by type"
    sort_mode: str                # "bucket"|"venn_2"|"column"

@dataclass
class CompareContrastReq:
    """What the scene architect must generate for a compare_contrast mechanic."""
    subject_a: str                # "plant cell"
    subject_b: str                # "animal cell"
    comparison_criteria: List[str] # What to compare on
    needs_second_diagram: bool    # True — always for compare_contrast
    comparison_mode: str          # "side_by_side"|"venn"|"spot_difference"

@dataclass
class BranchingReq:
    """What the scene architect must generate for a branching_scenario mechanic."""
    node_count: int               # 4-8 nodes
    narrative_topic: str          # "diagnosing a patient with chest pain"
    narrative_structure: str      # "linear"|"branching"|"foldback"
    has_multiple_endings: bool

@dataclass
class TracePathReq:
    """What the scene architect must generate for a trace_path mechanic."""
    path_count: int               # How many paths
    process_name: str             # "blood flow through circulatory system"
    path_type: str                # "linear"|"cyclic"|"branching"
    drawing_mode: str             # "click_waypoints"|"freehand"

@dataclass
class ClickToIdentifyReq:
    prompt_style: str             # "naming"|"function"|"location"
    selection_mode: str           # "sequential"|"any_order"

@dataclass
class DescriptionMatchingReq:
    mode: str                     # "click_zone"|"drag_description"|"multiple_choice"
    include_distractors: bool
    distractor_count: int

@dataclass
class DragDropReq:
    include_distractors: bool
    leader_line_style: str        # "straight"|"curved"|"none"

@dataclass
class HierarchicalReq:
    group_count: int
    reveal_strategy: str          # "complete_parent"|"progressive"|"all_at_once"

@dataclass
class MechanicTransition:
    """Edge in the mechanic graph within a scene."""
    from_mechanic_id: str         # or "scene_start"
    to_mechanic_id: str           # or "scene_end"
    trigger: str                  # "completion"|"score_threshold"|"user_choice"|"time_elapsed"
    trigger_value: Optional[Any]  # e.g., 0.8 for score_threshold

@dataclass
class SceneTransition:
    """Edge in the scene graph."""
    from_scene_id: str            # or "game_start"
    to_scene_id: str              # or "game_end"
    transition_type: str          # "auto"|"button"|"score_gate"
    condition: Optional[Dict]     # e.g., {"min_score_pct": 0.6}
```

### Game Plan Validator (Deterministic)

Checks:
1. **Graph connectivity**: Every mechanic node is reachable from `starting_mechanic_id`
2. **Terminal nodes**: At least one mechanic has `is_terminal=True`
3. **No orphan nodes**: Every mechanic is either the start node or has an incoming transition
4. **No orphan labels**: Every `zone_labels_used` is in the scene's `zone_labels`
5. **Score arithmetic**: `scene.max_score == sum(mechanic.max_score for m in scene.mechanics)`
6. **Content requirements present**: Every mechanic has its type-specific requirements populated
7. **Scene transitions**: Every scene except the last has a transition to the next
8. **Image spec consistency**: If `needs_diagram=True`, `image_spec` is populated; if mechanic needs zones, scene needs a diagram
9. **Mechanic compatibility**: If compare_contrast, `needs_second_diagram=True` in its requirements
10. **Label coverage**: Every zone_label appears in at least one mechanic's `zone_labels_used`

### Token Budget
- game_designer prompt: ~2000 tokens (pedagogical context + DK summary + capability list + examples)
- game_designer output: ~1500 tokens (structured JSON)
- validator: 0 tokens (deterministic)
- retry (if needed): +3500 tokens
- **Total Phase 1: ~3500-7000 tokens** (vs current ~15000+ with ReAct overhead)

---

## 4. Phase 2: Content Build (Sub-Graph)

### Purpose
For each scene, for each mechanic, generate complete content ready for assembly.

### Sub-Graph Structure

```
game_plan + domain_knowledge
        |
        v
  [FOR EACH SCENE — parallelizable via LangGraph Send API]
        |
        v
  ┌─────────────────────────────────────────────────────┐
  │  Scene Content Sub-Graph                             │
  │                                                      │
  │  [FOR EACH MECHANIC in scene — parallelizable]       │
  │        |                                              │
  │        v                                              │
  │  [mechanic_content_generator]                         │
  │  (single structured LLM call per mechanic)            │
  │  (model: gemini-2.5-pro for complex, flash for simple)│
  │        |                                              │
  │        v                                              │
  │  [mechanic_content_validator]                         │
  │  (deterministic — checks completeness)                │
  │        |                                              │
  │       / \                                             │
  │   [pass] [fail] → retry with feedback                 │
  │     |                                                 │
  │     v                                                 │
  │  mechanic_content (validated)                         │
  │                                                      │
  │  [after all mechanics complete]                       │
  │        |                                              │
  │        v                                              │
  │  [scoring_feedback_generator]                         │
  │  (single structured LLM call — all mechanics at once) │
  │  (model: gemini-2.5-flash)                           │
  │        |                                              │
  │        v                                              │
  │  [scene_validator]                                    │
  │  (deterministic — cross-mechanic checks)              │
  │        |                                              │
  │        v                                              │
  │  scene_content (complete, validated)                  │
  └─────────────────────────────────────────────────────┘
```

### Why Single Calls, Not ReAct

The game_plan's `ContentRequirements` tells the content generator EXACTLY what to produce. There's no ambiguity:

```
For sequencing mechanic with requirements:
  item_count: 5
  sequence_topic: "stages of mitosis"
  include_distractors: true

The LLM call is:
  "Generate 5 sequence items for the stages of mitosis, plus 2 distractor items.
   Use domain knowledge: {dk.sequence_flow_data}
   Each item needs: id, text, description, icon, order_index, is_distractor."
```

This is a **bounded generation task** — one call, one output. No tools needed.

### Model Selection Per Mechanic

| Mechanic | Model | Rationale |
|----------|-------|-----------|
| drag_drop | gemini-2.5-flash | Simple label generation |
| click_to_identify | gemini-2.5-flash | Prompt text generation |
| trace_path | gemini-2.5-flash | Waypoint ordering |
| description_matching | gemini-2.5-flash | Description text generation |
| sequencing | gemini-2.5-pro | Needs accurate domain knowledge for correct ordering |
| sorting_categories | gemini-2.5-pro | Needs accurate categorization logic |
| memory_match | gemini-2.5-flash | Pair generation (term/definition) |
| branching_scenario | gemini-2.5-pro | Complex narrative with consistent graph structure |
| compare_contrast | gemini-2.5-pro | Accurate similarity/difference analysis |
| hierarchical | gemini-2.5-flash | Parent-child assignment from DK data |

### Scoring/Feedback Generator

After all mechanic content is generated for a scene, one call generates:
- Scoring config per mechanic (strategy, points, max_score — validated against item counts)
- Feedback messages (on_correct, on_incorrect, on_completion)
- Misconception feedback (using pedagogical_context.common_misconceptions + DK data)
- Mode transition details (if multi-mechanic scene)

This is one flash call because scoring/feedback is formulaic and benefits from seeing all mechanics together.

### Content Output Schema

```python
@dataclass
class SceneContent:
    """Complete content for one scene, ready for assembly."""

    scene_id: str
    scene_number: int

    # Zone descriptions (for all visual mechanics in this scene)
    zone_specs: List[ZoneSpec]

    # Per-mechanic content
    mechanic_contents: Dict[str, MechanicContent]  # mechanic_id → content

    # Scoring and feedback (covers all mechanics in this scene)
    scoring: List[MechanicScoring]
    feedback: List[MechanicFeedback]
    mode_transitions: List[ModeTransition]

@dataclass
class ZoneSpec:
    """Specification for one zone in the diagram."""
    label: str
    description: str          # 1-2 sentence description
    hint: str                 # Hint for the player
    difficulty: int           # 1-5
    parent_label: Optional[str]  # For hierarchical

@dataclass
class MechanicContent:
    """Content for one mechanic instance."""
    mechanic_id: str
    mechanic_type: str

    # Only the relevant one is populated:
    drag_drop: Optional[DragDropContent]
    click_to_identify: Optional[ClickToIdentifyContent]
    trace_path: Optional[TracePathContent]
    sequencing: Optional[SequencingContent]
    sorting: Optional[SortingContent]
    memory_match: Optional[MemoryMatchContent]
    branching: Optional[BranchingContent]
    compare_contrast: Optional[CompareContrastContent]
    description_matching: Optional[DescriptionMatchingContent]
    hierarchical: Optional[HierarchicalContent]

# Example content types:

@dataclass
class SequencingContent:
    items: List[SequenceItem]     # id, text, description, icon, order_index, is_distractor
    correct_order: List[str]      # Item IDs in correct order
    sequence_type: str
    layout_mode: str
    instruction_text: str
    card_type: str

@dataclass
class BranchingContent:
    nodes: List[DecisionNode]     # id, question, options, is_end_node, etc.
    start_node_id: str
    narrative_structure: str

@dataclass
class CompareContrastContent:
    subject_a: CompareSubject     # name, description, zone_labels
    subject_b: CompareSubject
    expected_categories: Dict[str, str]  # label → "similar"|"different"|...
    comparison_mode: str
    second_image_spec: ImageSpec  # For the second diagram

@dataclass
class MechanicScoring:
    mechanic_id: str
    mechanic_type: str
    strategy: str                 # "per_item"|"all_or_nothing"|"progressive"
    points_per_correct: int
    max_score: int                # MUST = points_per_correct * item_count
    partial_credit: bool
    hint_penalty: float

@dataclass
class MechanicFeedback:
    mechanic_id: str
    mechanic_type: str
    on_correct: str
    on_incorrect: str
    on_completion: str
    misconception_feedback: List[MisconceptionFeedback]
    distractor_feedback: Dict[str, str]  # label → feedback message
```

### Content Validators (Deterministic)

Per-mechanic validators:
- **sequencing**: `len(items) >= 2`, `correct_order` contains all non-distractor item IDs, `order_index` values are contiguous
- **sorting**: Every item has `correct_category_id` that exists in categories, `len(categories) >= 2`
- **memory_match**: Every pair has `front` and `back` non-empty, `len(pairs) >= 3`
- **branching**: Graph connectivity check (all nodes reachable from start, all paths lead to an end node), `start_node_id` exists, at least one end node
- **compare_contrast**: `subject_a.zone_labels` and `subject_b.zone_labels` are non-empty and non-overlapping, `expected_categories` covers all zones
- **trace_path**: All waypoint zone_labels exist in scene's zone_labels, waypoints have contiguous order values
- **click_to_identify**: All prompt zone_labels exist in scene's zone_labels, `len(prompts) >= 1`
- **description_matching**: All description zone_labels exist in scene's zone_labels
- **drag_drop**: All label zone_labels exist in scene's zone_labels
- **hierarchical**: All parent/child labels exist in scene's zone_labels, no circular references

Cross-mechanic validator:
- **Score arithmetic**: `scoring.max_score == scoring.points_per_correct * mechanic.expected_item_count`
- **Transition validity**: All `from_mechanic_id` and `to_mechanic_id` reference real mechanic IDs
- **Zone label consistency**: All zone_labels referenced by any mechanic exist in `zone_specs`

### Token Budget (Per Scene)
- mechanic_content_generator: ~800 input + ~600 output per mechanic
- scoring_feedback_generator: ~1000 input + ~500 output
- validators: 0 tokens
- **Per scene: ~3000-5000 tokens** (for 2 mechanics)
- **Total Phase 2 (2 scenes): ~6000-10000 tokens** (vs current ~25000+ with ReAct overhead across scene_architect + interaction_designer)

### Parallelism Gains
- 2 scenes × 2 mechanics = 4 content generators running in parallel
- In LangGraph: `Send("mechanic_content_generator", {scene_id, mechanic_id, requirements, dk})` per mechanic
- After all Send operations complete: merge → validate → scoring

---

## 5. Phase 3: Asset Pipeline (Sub-Graph)

### Purpose
For each scene that needs visual assets, generate/find images and detect zones.

### Sub-Graph Structure

```
game_plan.scenes (filtered to needs_diagram=True) + scene_contents
        |
        v
  [FOR EACH SCENE needing assets — parallelizable via Send API]
        |
        v
  ┌─────────────────────────────────────────────────────┐
  │  Asset Generation Sub-Graph                          │
  │                                                      │
  │  image_spec + zone_specs                             │
  │        |                                              │
  │        v                                              │
  │  [image_search]                                       │
  │  (API call — search for reference diagram)            │
  │        |                                              │
  │       / \                                             │
  │   [found] [not found]                                 │
  │     |       |                                         │
  │     v       v                                         │
  │  [gemini_regenerate]  [imagen_generate]               │
  │  (API call)            (API call)                     │
  │     |                    |                            │
  │     └───────┬────────────┘                            │
  │             v                                         │
  │  diagram_image (URL + bytes)                          │
  │             |                                         │
  │             v                                         │
  │  [zone_detector]                                      │
  │  (vision model — detect zones in image)               │
  │             |                                         │
  │             v                                         │
  │  detected_zones[]                                     │
  │             |                                         │
  │             v                                         │
  │  [zone_matcher]                                       │
  │  (deterministic + optional LLM disambiguation)        │
  │  (matches detected zones to zone_specs by label)      │
  │             |                                         │
  │             v                                         │
  │  zone_match_report                                    │
  │  {matched, unmatched_spec, unmatched_detected}        │
  │             |                                         │
  │            / \                                        │
  │    [all matched] [gaps exist]                         │
  │         |            |                                │
  │         |            v                                │
  │         |    [zone_retry] (re-detect with prompts     │
  │         |     for missing labels, or generate         │
  │         |     placeholder coordinates)                │
  │         |            |                                │
  │         └────────────┘                                │
  │             |                                         │
  │             v                                         │
  │  [IF compare_contrast mechanic]                       │
  │     → Run same pipeline for second_image_spec         │
  │                                                      │
  │             v                                         │
  │  scene_assets (complete)                              │
  └─────────────────────────────────────────────────────┘
```

### Key Changes

1. **Mechanic-aware routing**: Content-only scenes (sequencing, sorting, memory_match, branching) SKIP the asset pipeline entirely
2. **Dual diagram for compare_contrast**: Two full image+zone pipelines, one per subject
3. **Zone matching is explicit**: Instead of silently assigning placeholders, the matcher reports what matched and what didn't
4. **No ReAct**: The asset pipeline is a deterministic graph of API calls. Each step has a clear input and output. No LLM "reasoning" needed.

### Zone Matcher Algorithm

```python
def match_zones(detected_zones, zone_specs):
    """Match detected zones to spec labels using fuzzy string matching."""
    matched = []
    unmatched_spec = list(zone_specs)
    unmatched_detected = list(detected_zones)

    # Pass 1: Exact match (case-insensitive)
    for spec in zone_specs:
        for det in detected_zones:
            if normalize(spec.label) == normalize(det.label):
                matched.append((spec, det))
                unmatched_spec.remove(spec)
                unmatched_detected.remove(det)
                break

    # Pass 2: Fuzzy match (Levenshtein distance < 3, or substring match)
    for spec in list(unmatched_spec):
        best_match = None
        best_score = 0
        for det in unmatched_detected:
            score = fuzzy_score(spec.label, det.label)
            if score > best_score and score > 0.7:
                best_match = det
                best_score = score
        if best_match:
            matched.append((spec, best_match))
            unmatched_spec.remove(spec)
            unmatched_detected.remove(best_match)

    # Pass 3: For remaining unmatched specs, generate placeholder coordinates
    # (evenly distributed across image, with warning)

    return ZoneMatchReport(matched, unmatched_spec, unmatched_detected)
```

### Token Budget (Per Scene)
- image_search: 0 LLM tokens (API call)
- gemini_regenerate: ~500 tokens (image + prompt)
- zone_detector: ~1000 tokens (image + prompt)
- zone_matcher: ~500 tokens (only if LLM disambiguation needed)
- **Per scene: ~1000-2000 tokens** (mostly vision model)
- **Total Phase 3 (2 scenes): ~2000-4000 tokens** (plus API call latency)

### Parallelism Gains
- Multiple scenes can run in parallel
- compare_contrast's two diagrams can run in parallel
- Image search + generation can overlap with other scenes' processing

---

## 6. Phase 4: Assembly (Sub-Graph)

### Purpose
Convert the enriched Game State Graph into the frontend's `InteractiveDiagramBlueprint` JSON.

### Sub-Graph Structure

```
game_plan + scene_contents + scene_assets
        |
        v
  [blueprint_assembler]
  (100% deterministic — NO LLM calls)
        |
        v
  blueprint (raw)
        |
        v
  [blueprint_validator]
  (deterministic — checks against FRONTEND_BACKEND_CONTRACT.md)
        |
       / \
  [pass]  [fail: _warnings array]
    |       |
    v       v
  blueprint  [blueprint_repair]
  (final)   (deterministic — fix known patterns)
              |
              v
           blueprint (repaired)
```

### Assembly Rules

1. **Single-scene vs multi-scene**: Determined by `game_plan.scenes.length`
2. **Zone ID generation**: `zone_{scene_number}_{index}` — deterministic
3. **Label ID generation**: `label_{scene_number}_{index}` — deterministic
4. **Zone coordinates**: From `scene_assets.zones[matched_spec_label].coordinates`
5. **Per-mechanic config keys**: Placed at scene level (in game_sequence.scenes[]) for multi-scene, at root for single-scene
6. **Scoring/feedback**: Keyed by `mechanic_id` (not mechanic_type) to avoid collisions
7. **CamelCase**: All output keys in camelCase
8. **Mode transitions**: Directly from game_plan's mechanic_transitions
9. **Scene transitions**: Directly from game_plan's scene_transitions

### Blueprint Validator Checks

From `FRONTEND_BACKEND_CONTRACT.md`:
1. `diagram.assetUrl` is non-empty for visual scenes
2. Every `label.correctZoneId` references an existing `zone.id`
3. Every zone has valid coordinates for its shape
4. `mechanics[0].type` matches `interactionMode` or starting_mechanic
5. Per-mechanic config exists for every active mechanic
6. `sequenceConfig.correctOrder` matches item IDs
7. `branchingConfig.startNodeId` exists in nodes
8. `compareConfig.diagramA/B` have imageUrl and zones
9. Score arithmetic: per-mechanic max_score values are consistent
10. Mode transitions reference valid mechanic types

### Token Budget
- assembler: 0 tokens (deterministic)
- validator: 0 tokens (deterministic)
- repair: 0 tokens (deterministic — pattern-based fixes)
- **Total Phase 4: 0 LLM tokens**

---

## 7. Complete Token Budget Comparison

### Current V3 Pipeline

| Stage | Tokens (est.) | Model |
|-------|--------------|-------|
| input_enhancer | ~700 | flash-lite |
| dk_retriever | ~5000 | flash-lite |
| router | ~1500 | flash-lite |
| game_designer_v3 (ReAct) | ~15000 | pro |
| design_validator | 0 | deterministic |
| scene_architect_v3 (ReAct) | ~20000 | pro |
| scene_validator | 0 | deterministic |
| interaction_designer_v3 (ReAct) | ~15000 | pro |
| interaction_validator | 0 | deterministic |
| asset_generator_v3 (ReAct) | ~10000 | flash |
| blueprint_assembler_v3 | 0 | deterministic |
| **TOTAL** | **~67,200** | |

### Proposed V4 Pipeline

| Phase | Stage | Tokens (est.) | Model |
|-------|-------|--------------|-------|
| 0 | input_analyzer | ~700 | flash |
| 0 | dk_retriever (ReAct) | ~5000 | flash |
| 1 | game_designer (single call) | ~3500 | pro |
| 1 | game_plan_validator | 0 | deterministic |
| 2 | mechanic_content_gen × N | ~1400/mech | pro or flash |
| 2 | scoring_feedback_gen × S | ~1500/scene | flash |
| 2 | content_validator × N | 0 | deterministic |
| 3 | image_search + generate | ~500/scene | vision |
| 3 | zone_detect + match | ~1500/scene | vision |
| 4 | blueprint_assembler | 0 | deterministic |
| 4 | blueprint_validator | 0 | deterministic |
| **TOTAL (2 scenes, 3 mechs)** | | **~17,800** | |

**~73% token reduction**, primarily from:
- Removing ReAct overhead from game_designer (-11,500)
- Removing ReAct overhead from scene_architect (-14,000)
- Removing ReAct overhead from interaction_designer (-13,500)
- Removing router entirely (-1,500)
- Using targeted single calls instead of iterative tool-use loops

### Latency Comparison

| Pipeline | Sequential Stages | Parallelism | Est. Total Time |
|----------|------------------|-------------|-----------------|
| Current V3 | 11 stages, all sequential | None | ~120-180s |
| Proposed V4 | 4 phases | Phase 0 parallel, Phase 2 map-reduce, Phase 3 map-reduce | ~45-75s |

Key latency savings:
- Phase 0: input_analyzer ∥ dk_retriever (saves ~5s)
- Phase 2: All mechanic content generators run in parallel (saves ~15-30s)
- Phase 3: All scene asset pipelines run in parallel (saves ~10-20s)
- Fewer LLM calls overall (fewer round-trips)

---

## 8. Addressing the FOL / Correctness Guarantee

### How do we ensure the game is not buggy, broken, or underspecified?

The answer is **defense in depth** — four layers of validation:

#### Layer 1: Schema Validation (Pydantic)
Every data structure has a Pydantic model with:
- Required fields (no Optional where data is needed)
- Type constraints (str, int, List[str])
- Value constraints (min/max, enums, regex patterns)
- Cross-field validators (e.g., `max_score == points_per_correct * expected_item_count`)

#### Layer 2: Graph Validation (Deterministic)
The Game State Graph is validated as a graph:
- Connectivity: All nodes reachable from start
- Termination: All paths lead to a terminal state
- No orphans: Every node has at least one incoming or outgoing edge
- Consistency: Zone labels referenced by mechanics exist in zones

#### Layer 3: Content Validation (Deterministic)
Per-mechanic content is validated:
- Referential integrity: IDs cross-reference correctly (correctOrder IDs match item IDs)
- Completeness: All required fields populated with non-empty values
- Logical consistency: Branching graph has no unreachable nodes, sorting items have valid categories

#### Layer 4: Blueprint Contract Validation (Deterministic)
The final blueprint is validated against `FRONTEND_BACKEND_CONTRACT.md`:
- All required fields present
- All zone coordinates within image bounds
- All mechanic configs have their required sub-fields
- Score totals are consistent

### What makes this different from the current approach?

**Current**: Validation happens AFTER generation. If the content is wrong, we retry the entire ReAct loop.

**Proposed**: Validation is **structural** (graph shape) and happens at EVERY boundary. Content generation is guided by explicit requirements (ContentRequirements), not free-form exploration. The game designer can't produce an invalid graph — the schema enforces it.

Think of it like a compiler:
1. **Parser** (Phase 1): Produces an AST (Game State Graph) that is syntactically valid
2. **Semantic analysis** (Phase 2): Fills in the content, checked for semantic correctness
3. **Code generation** (Phase 3+4): Produces the executable output (blueprint)

If the AST is valid and the semantic analysis passes, the generated code is correct by construction.

---

## 9. Handling Edge Cases

### 9.1 What if the question doesn't fit any mechanic well?

The input_analyzer classifies content_structure. The game_designer uses this + DK data to pick appropriate mechanics. If the content is simple (e.g., "label parts of a flower"), it defaults to `drag_drop` — the most robust mechanic.

**Fallback chain**: drag_drop > click_to_identify > description_matching > sequencing > sorting > memory_match > branching > compare_contrast > trace_path

### 9.2 What if DK retrieval fails?

The dk_retriever has a fallback that extracts labels from the question text itself. Even with empty DK, the game_designer can produce a valid game plan with `drag_drop` as the primary mechanic and question-derived labels.

### 9.3 What if image search returns nothing?

The asset pipeline has three fallback levels:
1. Web search for reference → Gemini regenerate
2. Imagen generate from scratch
3. Placeholder image (solid color with text overlay)

Even with a placeholder image, the game can work if zone coordinates are set to a grid layout.

### 9.4 What if zone detection misses labels?

The zone_matcher reports unmatched labels. For critical labels (those used by the active mechanic), the blueprint_assembler generates evenly-spaced placeholder zones with a `_warning` flag.

### 9.5 What about multi-scene games where scenes share labels?

The game_plan's `labels.zone_labels` is the global label list. Each scene's `zone_labels` is a subset. Labels can appear in multiple scenes. Zone IDs are scene-scoped (`zone_1_0`, `zone_2_0`) even if the label text is the same.

---

## 10. LangGraph Implementation Strategy

### 10.1 Graph Structure

```python
# Main orchestrator graph
main_graph = StateGraph(PipelineState)

# Phase 0: Understanding (sub-graph)
understanding_graph = StateGraph(Phase0State)
understanding_graph.add_node("input_analyzer", input_analyzer_node)
understanding_graph.add_node("dk_retriever", dk_retriever_node)
# Both start from START, merge at a join node
understanding_graph.add_edge(START, "input_analyzer")
understanding_graph.add_edge(START, "dk_retriever")
understanding_graph.add_node("merge_phase0", merge_phase0_node)
understanding_graph.add_edge("input_analyzer", "merge_phase0")
understanding_graph.add_edge("dk_retriever", "merge_phase0")
understanding_graph.add_edge("merge_phase0", END)

# Phase 1: Game Design (sub-graph)
game_design_graph = StateGraph(Phase1State)
game_design_graph.add_node("game_designer", game_designer_node)
game_design_graph.add_node("game_plan_validator", validator_node)
game_design_graph.add_conditional_edges("game_plan_validator", retry_or_proceed)

# Phase 2: Content Build (sub-graph with dynamic parallelism)
content_build_graph = StateGraph(Phase2State)
content_build_graph.add_node("dispatch_scenes", dispatch_scenes_node)  # Send() per scene
content_build_graph.add_node("scene_content_builder", scene_content_node)  # Receives Send
content_build_graph.add_node("merge_scenes", merge_scenes_node)  # Collects results

# Phase 3: Asset Pipeline (sub-graph with dynamic parallelism)
asset_graph = StateGraph(Phase3State)
asset_graph.add_node("dispatch_visual_scenes", dispatch_visual_node)  # Send() per visual scene
asset_graph.add_node("scene_asset_builder", scene_asset_node)
asset_graph.add_node("merge_assets", merge_assets_node)

# Phase 4: Assembly (sub-graph)
assembly_graph = StateGraph(Phase4State)
assembly_graph.add_node("blueprint_assembler", assembler_node)
assembly_graph.add_node("blueprint_validator", blueprint_validator_node)
assembly_graph.add_node("blueprint_repair", repair_node)

# Wire phases together
main_graph.add_node("phase0_understanding", understanding_graph.compile())
main_graph.add_node("phase1_game_design", game_design_graph.compile())
main_graph.add_node("phase2_content_build", content_build_graph.compile())
main_graph.add_node("phase3_asset_pipeline", asset_graph.compile())
main_graph.add_node("phase4_assembly", assembly_graph.compile())
main_graph.add_edge(START, "phase0_understanding")
main_graph.add_edge("phase0_understanding", "phase1_game_design")
main_graph.add_edge("phase1_game_design", "phase2_content_build")
main_graph.add_edge("phase2_content_build", "phase3_asset_pipeline")
main_graph.add_edge("phase3_asset_pipeline", "phase4_assembly")
main_graph.add_edge("phase4_assembly", END)
```

### 10.2 Dynamic Parallelism with Send API

```python
def dispatch_scenes_node(state: Phase2State):
    """Dispatch parallel content generation per scene."""
    game_plan = state["game_plan"]
    sends = []
    for scene in game_plan.scenes:
        for mechanic in scene.mechanics:
            sends.append(
                Send("mechanic_content_generator", {
                    "scene_id": scene.scene_id,
                    "mechanic_id": mechanic.mechanic_id,
                    "mechanic_type": mechanic.mechanic_type,
                    "content_requirements": mechanic.content_requirements,
                    "zone_specs": scene.zone_labels,
                    "domain_knowledge": state["domain_knowledge"],
                })
            )
    return sends
```

### 10.3 State Management

Each phase has its own state type (not the monolithic 160+ field AgentState):

```python
class Phase0State(TypedDict):
    question_text: str
    question_options: Optional[List[str]]
    pedagogical_context: Optional[PedagogicalContext]
    domain_knowledge: Optional[DomainKnowledge]
    canonical_labels: Optional[List[str]]

class Phase1State(TypedDict):
    pedagogical_context: PedagogicalContext
    domain_knowledge: DomainKnowledge
    canonical_labels: List[str]
    game_plan: Optional[GamePlan]
    validation_feedback: Optional[str]
    retry_count: int

class Phase2State(TypedDict):
    game_plan: GamePlan
    domain_knowledge: DomainKnowledge
    scene_contents: Dict[str, SceneContent]  # scene_id → content

class Phase3State(TypedDict):
    game_plan: GamePlan
    scene_contents: Dict[str, SceneContent]
    scene_assets: Dict[str, SceneAssets]  # scene_id → assets

class Phase4State(TypedDict):
    game_plan: GamePlan
    scene_contents: Dict[str, SceneContent]
    scene_assets: Dict[str, SceneAssets]
    blueprint: Optional[Dict[str, Any]]
```

Benefits:
- Each phase only sees the data it needs (less confusion, better type safety)
- The monolithic AgentState is eliminated
- State transitions between phases are explicit

---

## 11. Migration Strategy

### What to Keep
- `input_enhancer.py` — Minor enhancement (add content_structure)
- `domain_knowledge_retriever.py` — Keep ReAct loop, enhance intent detection
- `blueprint_assembler_tools.py` — Keep deterministic assembly, update schemas
- All frontend code — No changes needed (same blueprint format)
- `state.py` — Replace with per-phase typed states

### What to Rewrite
- `game_designer_v3.py` → New single-call game planner with GamePlan schema
- `scene_architect_v3.py` → New per-mechanic content generators
- `interaction_designer_v3.py` → New scoring/feedback generator
- `asset_generator_v3.py` → New asset pipeline sub-graph
- `graph.py` → New graph-of-graphs structure
- All validators → Enhanced with graph validation logic

### What to Remove
- `router.py` (V3 path)
- `mechanic_contracts.py` (dead code)
- ReAct overhead in game_designer, scene_architect, interaction_designer
- Monolithic AgentState (replaced by per-phase states)

### Implementation Order
1. **Define schemas first** — GamePlan, SceneContent, SceneAssets, Blueprint
2. **Build validators** — Graph validator, content validators, blueprint validator
3. **Build Phase 1** — Game designer (single call) + validator
4. **Build Phase 2** — Content generators (per mechanic) + scoring + validators
5. **Build Phase 4** — Blueprint assembler (update for new schemas)
6. **Build Phase 3** — Asset pipeline (can test Phase 1+2+4 with mock assets first)
7. **Build Phase 0** — Enhanced input_analyzer + DK retriever
8. **Wire main graph** — Connect all phases with proper state transitions
9. **E2E test** — Full pipeline run with real questions

---

## 12. Open Questions

1. **Should game_designer use Gemini structured output (tool/function calling) or a submit-tool pattern?**
   - Structured output: Cleaner, one call, but requires the model to produce valid JSON in one shot
   - Submit tool: ReAct-like but with only one tool, gives the model more freedom to reason
   - Recommendation: Structured output with Gemini's response_schema, plus retry if schema validation fails

2. **Should Phase 2 content generation be one call per mechanic or one call per scene?**
   - Per mechanic: Better parallelism, smaller prompts, easier to retry individual mechanics
   - Per scene: Mechanics can reference each other (e.g., sequencing items come from the same zones as drag_drop labels)
   - Recommendation: Per mechanic, but inject shared zone_specs into each call so mechanics can be consistent

3. **How to handle the DK retriever for content-only mechanics?**
   - Current: DK retriever runs once for the whole question
   - Option: DK retriever takes `game_plan` as input and does targeted searches per mechanic
   - Recommendation: Keep single DK retriever in Phase 0 (it already gets canonical labels and descriptions). Phase 2 content generators use DK data as context.

4. **Should we support branching scene graphs (not just linear)?**
   - Current: Scenes are always linear (scene_1 → scene_2 → ...)
   - Option: Scene transitions could be branching (if score > 80% go to scene_2a, else scene_2b)
   - Recommendation: Defer. Linear scene order covers 95% of use cases. The mechanic graph within scenes already supports branching.

5. **How to handle `timed_challenge` wrapper mechanic?**
   - It wraps another mechanic with a timer. Not a separate content type.
   - Recommendation: Game designer specifies `timed_challenge` as a wrapper property on a mechanic node, not as a separate mechanic. Blueprint adds `timeLimitSeconds` and `timedChallengeWrappedMode` to the blueprint.

6. **How to handle existing games in the database?**
   - V3 blueprints in the database use the old format
   - Recommendation: Blueprint assembler outputs the same frontend format. The frontend doesn't need to change. Only the internal pipeline data structures change.
