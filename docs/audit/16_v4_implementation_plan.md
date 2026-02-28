# V4 Pipeline — Complete Implementation Plan

**Date**: 2026-02-14 (updated with gap analysis fixes from 18a/18b/18c)
**Status**: IMPLEMENTATION PLAN — 3-stage creative cascade + destructured validation + corrected graph wiring
**Prerequisite docs**: `13_pipeline_v4_brainstorm.md`, `14_v4_architecture_refined.md`, `15_graph_construction.md`
**Gap analysis docs**: `18a_frontend_contract_gaps.md`, `18b_data_flow_gaps.md`, `18c_langgraph_feasibility.md`

---

## 0. Architecture Overview

### 3-Stage Creative Cascade

The V4 pipeline separates creative design into 3 focused stages, each with its own validator and scoped retry:

```
Phase 0: Understanding (parallel)
  ├── input_analyzer → PedagogicalContext + ContentStructure
  └── dk_retriever → DomainKnowledge + canonical_labels

Phase 1: Game Design
  1a. Game Concept Designer (1 LLM call)
      → Game theme, narrative arc, scene structure, mechanic choices
      → GameConcept
      └── Concept Validator → retry concept if structural issues (~4K tokens)

  1b. Scene Designers (1 LLM call per scene, parallel)
      → Deep visual/narrative/mechanic creative direction per scene
      → SceneCreativeDesign per scene
      └── Scene Design Validator (per scene) → retry only failing scene (~4K tokens)

  deterministic: Graph Builder (GameConcept + SceneCreativeDesigns → GamePlan)

Phase 2: Content Build
  2a. Content Generators (1 LLM call per mechanic, parallel)
      → Specific items/sequences/pairs/paths per mechanic
      → MechanicContent per mechanic
      └── Content Validator (per mechanic) → retry only failing mechanic (~3K tokens)

  2b. Interaction Designer (1 LLM call per scene)
      → Scoring, feedback, mode transitions
      └── Interaction Validator (per scene) → retry only failing scene (~3K tokens)

Phase 3: Asset Pipeline
  3a. Asset Art Director (1 LLM call per scene, parallel)
      → Crafted search queries, style prompts, color palettes
      → ArtDirectedManifest per scene
      └── Art Direction Validator (per scene) → retry only failing scene (~5K tokens)

  3b. Asset Chains (pre-built, parallel per asset)
      → Execute art-directed specs through tool chains
      └── Asset Validator (per scene) → retry only failing chain

Phase 4: Assembly (deterministic)
  Blueprint Assembler → Blueprint Validator → END
```

### Key Design Principles

1. **Valid by construction**: Graph builder produces valid game graphs deterministically — no LLM-generated IDs/edges
2. **Destructured validation**: Each stage has its own focused validator; retries scoped to the failing unit
3. **3-stage creative cascade**: Game concept → scene design → asset art direction — no single call carries all creative burden
4. **Parallel where possible**: Scene designers, content generators, asset art directors all fan out in parallel
5. **Pre-built asset chains**: No asset planning overhead — deterministic dispatch to tested tool chains

### Token Budget

```
                          Calls    Input    Output    Total
Phase 0 (understanding):    2      ~4K      ~2K       ~6K
Phase 1a (concept):          1      ~3K      ~1K       ~4K
Phase 1b (scene design):    N      ~2K×N    ~2K×N     ~4K×N
Phase 2a (content gen):     M      ~2K×M    ~1K×M     ~3K×M
Phase 2b (interaction):     N      ~2K×N    ~1K×N     ~3K×N
Phase 3a (art director):    N      ~3K×N    ~2K×N     ~5K×N

For 2 scenes, 3 mechanics: ~6 + 4 + 8 + 9 + 6 + 10 = ~43K tokens
For 1 scene, 2 mechanics:  ~6 + 4 + 4 + 6 + 3 + 5 = ~28K tokens
V3 baseline:               ~67K tokens
```

---

## 1. Directory Structure

```
backend/app/agents/v4/
├── __init__.py
├── schemas.py              # All V4 Pydantic schemas
├── state.py                # V4PipelineState TypedDict
├── graph.py                # create_v4_graph() — main orchestrator
├── graph_builder.py        # Deterministic GameConcept + SceneDesigns → GamePlan
├── capability_spec.py      # Mechanic capability menu for game concept designer prompt
│
├── phase0/
│   ├── __init__.py
│   ├── input_analyzer.py       # Single LLM call → PedagogicalContext + ContentStructure
│   └── dk_retriever.py         # Enhanced DK retriever (reuses V3 core)
│
├── phase1/
│   ├── __init__.py
│   ├── game_concept_designer.py    # Single LLM call → GameConcept
│   ├── concept_validator.py        # Deterministic structural validation
│   ├── scene_designer.py           # Single LLM call per scene → SceneCreativeDesign
│   └── scene_design_validator.py   # Deterministic per-scene validation
│
├── phase2/
│   ├── __init__.py
│   ├── scene_context_builder.py    # Deterministic: shared context per scene
│   ├── content_generator.py        # Single LLM call per mechanic → MechanicContent
│   ├── content_validator.py        # Per-mechanic deterministic validation
│   ├── interaction_designer.py     # Single LLM call per scene → scoring + feedback
│   └── interaction_validator.py    # Deterministic scoring arithmetic + transition checks
│
├── phase3/
│   ├── __init__.py
│   ├── asset_needs_analyzer.py     # Deterministic: GamePlan + Content → AssetNeeds
│   ├── asset_art_director.py       # LLM per scene: AssetNeeds + SceneDesign → ArtDirectedManifest
│   ├── art_direction_validator.py  # Deterministic: completeness + quality checks
│   ├── asset_chains.py             # Pre-built tool chain definitions + dispatch
│   ├── zone_matcher.py             # Deterministic + optional LLM: match zones to spec
│   └── asset_validator.py          # Deterministic: zone coverage, completeness
│
├── phase4/
│   ├── __init__.py
│   ├── blueprint_assembler.py      # Deterministic: GamePlan + content + assets → blueprint
│   └── blueprint_validator.py      # Deterministic: frontend contract compliance
│
└── prompts/
    ├── __init__.py
    ├── game_concept_designer.py    # Game concept prompt template
    ├── scene_designer.py           # Per-scene creative design prompt template
    ├── content_generators.py       # 10 per-mechanic content generation prompt templates
    ├── interaction_designer.py     # Scoring/feedback prompt template
    └── asset_art_director.py       # Asset art direction prompt template
```

**Total new files**: ~33
**No V3 files modified** — V4 is a completely separate package.

---

## 2. Reuse Matrix

### Services (100% reused, no changes)

| Service | File | Used By V4 |
|---------|------|------------|
| LLM Service | `services/llm_service.py` | All LLM calls |
| Gemini Service | `services/gemini_service.py` | Zone detection (gemini flash bbox) |
| Web Search | `services/web_search.py` | DK retriever, image search |
| Image Retrieval | `services/image_retrieval.py` | Asset chain: serper step |
| SAM3 Zone Service | `services/sam3_zone_service.py` | Asset chain: SAM3 step |
| Gemini Diagram Service | `services/gemini_diagram_service.py` | Asset chain: gemini bbox step |
| Asset Gen Core | `services/asset_gen/core.py` | Asset chain: image generation |
| Asset Gen Search | `services/asset_gen/search.py` | Asset chain: image search |
| Asset Gen Storage | `services/asset_gen/storage.py` | Asset chain: save to disk |
| Asset Gen Gemini | `services/asset_gen/gemini_image.py` | Asset chain: gemini regeneration |
| Asset Gen Imagen | `services/asset_gen/imagen.py` | Asset chain: imagen generation |
| JSON Repair | `services/json_repair.py` | Parsing LLM outputs |

### Config (mostly reused)

| Config | File | V4 Usage |
|--------|------|----------|
| Model Registry | `config/models.py` | Same models available |
| Agent Models | `config/agent_models.py` | ADD V4 model assignments (new section) |
| Pedagogical Constants | `config/pedagogical_constants.py` | Same Bloom's taxonomy, difficulty levels |
| Example Game Designs | `config/example_game_designs.py` | Adapted for V4 GameConcept format |

### V3 Code Referenced (not imported, logic patterns reused)

| V3 File | What V4 Reuses |
|---------|-------------------------------|
| `agents/input_enhancer.py` | Same pedagogical analysis logic, enhanced with content_structure |
| `agents/domain_knowledge_retriever.py` | Same web search + extraction flow |
| `tools/blueprint_assembler_tools.py` | Zone normalization, coordinate conversion, camelCase mapping |
| `agents/instrumentation.py` | Same wrapping pattern for observability |

### V3 Code NOT Used by V4

| V3 File | Why Not Used |
|---------|-------------|
| `agents/router.py` | Removed — output was never consumed |
| `agents/game_designer_v3.py` | Replaced by game_concept_designer + scene_designer |
| `agents/scene_architect_v3.py` | Replaced by per-mechanic content generators |
| `agents/interaction_designer_v3.py` | Replaced by per-scene interaction designer |
| `agents/asset_generator_v3.py` | Replaced by asset_art_director + pre-built chains |
| `agents/blueprint_assembler_v3.py` | Replaced by V4 blueprint assembler |
| `agents/react_base.py` | V4 doesn't use ReAct |
| `tools/v3_context.py` | V4 passes context explicitly, no contextvars |
| `config/mechanic_contracts.py` | Dead code (never imported) |

---

## 3. Schema Definitions (`backend/app/agents/v4/schemas.py`)

```python
"""
V4 Pipeline Schemas
All Pydantic models for the V4 game generation pipeline.
3-stage creative cascade: Concept → Scene Design → Art Direction
"""
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# Phase 0: Understanding
# ═══════════════════════════════════════════════════════════

class ContentStructure(BaseModel):
    """Classification of the input question's content structure."""
    primary_type: Literal["anatomical", "process", "comparative", "categorical", "hierarchical", "conceptual"]
    has_labels: bool
    has_sequence: bool
    has_comparison: bool
    has_hierarchy: bool
    has_categories: bool
    visual_needs: Literal["diagram", "flowchart", "dual_diagram", "none"]


class PedagogicalContext(BaseModel):
    """Reuses V3 PedagogicalContext structure + adds content_structure."""
    blooms_level: str
    blooms_justification: str = ""
    learning_objectives: List[str] = []
    key_concepts: List[str] = []
    difficulty: str = "intermediate"
    difficulty_justification: str = ""
    subject: str = ""
    cross_cutting_subjects: List[str] = []
    common_misconceptions: List[Dict[str, str]] = []
    prerequisites: List[str] = []
    question_intent: str = ""
    content_structure: Optional[ContentStructure] = None


# DomainKnowledge: reuse V3 schema from agents/schemas/domain_knowledge.py
# No new schema needed — same structure, enhanced population


# ═══════════════════════════════════════════════════════════
# Phase 1a: Game Concept (from Game Concept Designer)
# ═══════════════════════════════════════════════════════════

class MechanicChoice(BaseModel):
    """One mechanic chosen for a scene, with rationale."""
    mechanic_id: str = ""               # Set by graph_builder: "s{scene}_m{index}"
    mechanic_type: str
    learning_purpose: str               # WHY this mechanic for this content
    zone_labels_used: List[str] = []    # Which labels this mechanic uses
    expected_item_count: int = Field(ge=1)
    points_per_item: int = Field(default=10, ge=1)

    # Connection to next mechanic
    advance_trigger: str = "completion"  # completion | score_threshold | time_elapsed
    advance_trigger_value: Optional[float] = None

    # Modifiers
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None

    # Hierarchical children
    children: Optional[List[MechanicChoice]] = None


class SceneConcept(BaseModel):
    """One scene as conceived by the game concept designer."""
    title: str
    learning_goal: str
    narrative_intro: str = ""
    zone_labels: List[str] = []

    needs_diagram: bool
    image_description: str = ""         # Brief description for asset pipeline

    mechanics: List[MechanicChoice] = Field(min_length=1)

    transition_to_next: str = "auto"    # auto | score_gated
    transition_min_score_pct: Optional[float] = None


class GameConcept(BaseModel):
    """
    What the game concept designer LLM produces.
    High-level game structure — WHAT and WHY, not HOW.
    No graph IDs, no visual specs, no asset details.
    """
    title: str
    subject: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_duration_minutes: int = Field(ge=1, le=30)
    narrative_theme: str                 # Overall narrative concept
    narrative_intro: str
    completion_message: str

    all_zone_labels: List[str]
    distractor_labels: List[str] = []
    label_hierarchy: Optional[Dict[str, List[str]]] = None

    scenes: List[SceneConcept] = Field(min_length=1, max_length=6)


# ═══════════════════════════════════════════════════════════
# Phase 1b: Scene Creative Design (from Scene Designer)
# ═══════════════════════════════════════════════════════════

class ImageSpec(BaseModel):
    """Rich image requirements for asset pipeline."""
    description: str
    must_include_structures: List[str]
    style: str = "clean_educational"
    annotation_preference: str = "clean_unlabeled"
    color_direction: str = ""            # Color guidance for this image
    spatial_guidance: str = ""           # Layout hints

class MechanicCreativeDesign(BaseModel):
    """Rich creative direction for one mechanic, produced by scene designer."""
    mechanic_id: str = ""               # Matches MechanicChoice.mechanic_id (set by graph_builder)
    mechanic_type: str

    # Visual integration
    visual_style: str                    # How this mechanic looks in this scene
    card_type: str = "text_only"         # text_only | icon_and_text | image_card
    layout_mode: str = "default"         # vertical_list | radial | grid | spatial | etc.
    connector_style: str = "arrow"       # arrow | flowing | dotted | none
    color_direction: str = ""            # Color guidance for this mechanic

    # Narrative integration
    instruction_text: str                # Carefully crafted, scene-aware instruction
    instruction_tone: str = "educational" # exploratory | challenging | narrative | clinical
    narrative_hook: str = ""             # How this mechanic tells the scene's story

    # Interaction personality
    hint_strategy: str = "progressive"   # progressive | contextual | anatomical | none
    feedback_style: str = "encouraging"  # encouraging | clinical | narrative | gamified
    difficulty_curve: str = "gradual"    # gradual | plateau | challenging

    # Content generation guidance (replaces simple ContentBrief)
    generation_goal: str                 # What content to generate
    key_concepts: List[str] = []
    pedagogical_focus: str = ""

    # Mechanic-specific creative hints
    sequence_topic: Optional[str] = None
    category_names: Optional[List[str]] = None
    comparison_subjects: Optional[List[str]] = None
    narrative_premise: Optional[str] = None
    description_source: Optional[str] = None
    path_process: Optional[str] = None
    prompt_style: Optional[str] = None
    match_type: Optional[str] = None

    # Visual asset hints
    needs_item_images: bool = False
    item_image_style: Optional[str] = None


class SceneCreativeDesign(BaseModel):
    """Deep creative design for one scene, produced by scene designer."""
    scene_id: str                       # Matches scene index from concept
    title: str

    # Visual design
    visual_concept: str                  # Overall visual vision for the scene
    color_palette_direction: str = ""    # Color theme guidance
    spatial_layout: str = ""             # How elements are arranged
    atmosphere: str = ""                 # Mood, tone of the visual design

    # Rich image spec (replaces simple image_description)
    image_spec: Optional[ImageSpec] = None
    second_image_spec: Optional[ImageSpec] = None  # For compare_contrast

    # Per-mechanic creative designs
    mechanic_designs: List[MechanicCreativeDesign]

    # Scene-level narrative
    scene_narrative: str = ""            # How the scene unfolds as a story
    transition_narrative: str = ""       # Narrative bridge to next scene


# ═══════════════════════════════════════════════════════════
# Graph Builder Output (deterministic, not LLM-produced)
# ═══════════════════════════════════════════════════════════

class MechanicConnection(BaseModel):
    from_mechanic_id: str
    to_mechanic_id: str
    trigger: str
    trigger_value: Optional[Any] = None


class SceneTransition(BaseModel):
    transition_type: str
    min_score_pct: Optional[float] = None


class MechanicPlan(BaseModel):
    """Formal mechanic node in the game state graph."""
    mechanic_id: str
    mechanic_type: str
    zone_labels_used: List[str] = []
    instruction_text: str               # From SceneCreativeDesign
    creative_design: MechanicCreativeDesign  # Full creative direction
    expected_item_count: int
    points_per_item: int = 10
    max_score: int
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None
    parent_mechanic_id: Optional[str] = None
    is_terminal: bool = False


class ScenePlan(BaseModel):
    """Formal scene node in the game state graph."""
    scene_id: str
    scene_number: int
    title: str
    learning_goal: str
    narrative_intro: str = ""
    zone_labels: List[str] = []
    needs_diagram: bool
    image_spec: Optional[ImageSpec] = None
    second_image_spec: Optional[ImageSpec] = None
    creative_design: SceneCreativeDesign  # Full creative direction
    mechanics: List[MechanicPlan]
    mechanic_connections: List[MechanicConnection]
    starting_mechanic_id: str
    transition_to_next: Optional[SceneTransition] = None
    scene_max_score: int


class GamePlan(BaseModel):
    """The formal game state graph. Produced by graph builder, not LLM."""
    title: str
    subject: str
    difficulty: str
    estimated_duration_minutes: int
    narrative_theme: str
    narrative_intro: str
    completion_message: str
    all_zone_labels: List[str]
    distractor_labels: List[str] = []
    label_hierarchy: Optional[Dict[str, List[str]]] = None
    total_max_score: int
    scenes: List[ScenePlan]


# ═══════════════════════════════════════════════════════════
# Phase 2: Content Build
# ═══════════════════════════════════════════════════════════

class ZoneSpec(BaseModel):
    """Specification for one zone."""
    label: str
    description: str = ""
    hint: str = ""
    difficulty: int = Field(default=3, ge=1, le=5)
    parent_label: Optional[str] = None


# ── Per-Mechanic Content Types ──

class SequenceItem(BaseModel):
    id: str
    text: str
    description: str = ""
    icon: str = ""
    order_index: int
    is_distractor: bool = False
    image_description: Optional[str] = None

class SequencingContent(BaseModel):
    items: List[SequenceItem]
    correct_order: List[str]
    sequence_type: str = "linear"
    instruction_text: str = ""
    # Frontend visual config (populated by content_generator from MechanicCreativeDesign)
    layout_mode: str = "vertical_list"        # horizontal_timeline | vertical_list | circular_cycle | flowchart
    interaction_pattern: str = "drag_reorder" # drag_reorder | drag_to_slots | click_to_swap
    card_type: str = "text_only"              # text_only | text_with_icon | image_with_caption
    connector_style: str = "arrow"            # arrow | line | numbered | none
    show_position_numbers: bool = False
    allow_partial_credit: bool = True

class SortingCategory(BaseModel):
    id: str
    label: str
    description: str = ""
    color: Optional[str] = None

class SortingItem(BaseModel):
    id: str
    text: str
    correct_category_id: str
    correct_category_ids: List[str] = []
    description: str = ""
    image_description: Optional[str] = None
    difficulty: str = "medium"

class SortingContent(BaseModel):
    categories: List[SortingCategory]
    items: List[SortingItem]
    instruction_text: str = ""
    # Frontend visual config
    sort_mode: str = "bucket"                 # bucket | venn_2 | venn_3 | matrix | column
    item_card_type: str = "text_only"         # text_only | text_with_icon | image_with_caption
    container_style: str = "bucket"           # bucket | labeled_bin | circle | cell | column
    submit_mode: str = "immediate_feedback"   # batch_submit | immediate_feedback | round_based
    allow_multi_category: bool = False
    show_category_hints: bool = False
    allow_partial_credit: bool = True

class MemoryPair(BaseModel):
    id: str
    front: str
    back: str
    front_type: str = "text"
    back_type: str = "text"
    explanation: str = ""
    category: str = ""

class MemoryMatchContent(BaseModel):
    pairs: List[MemoryPair]
    match_type: str = "term_to_definition"
    game_variant: str = "classic"
    grid_size: Optional[List[int]] = None
    # Frontend visual config
    card_back_style: str = "question_mark"    # solid | gradient | pattern | question_mark
    matched_card_behavior: str = "fade"       # fade | shrink | collect | checkmark
    show_explanation_on_match: bool = True
    flip_duration_ms: int = 400
    show_attempts_counter: bool = True

class DecisionOption(BaseModel):
    id: str
    text: str
    next_node_id: Optional[str] = None
    is_correct: bool = False
    consequence: str = ""
    points: int = 0
    quality: Optional[str] = None

class DecisionNode(BaseModel):
    id: str
    question: str
    description: str = ""
    node_type: str = "decision"
    is_end_node: bool = False
    end_message: str = ""
    ending_type: Optional[str] = None
    options: List[DecisionOption] = []
    narrative_text: str = ""
    image_description: Optional[str] = None

class BranchingContent(BaseModel):
    nodes: List[DecisionNode]
    start_node_id: str
    narrative_structure: str = "branching"
    # Frontend visual config
    show_path_taken: bool = True
    allow_backtrack: bool = False
    show_consequences: bool = True
    multiple_valid_endings: bool = False

class CompareSubject(BaseModel):
    id: str                                   # "subject_a" or "subject_b"
    name: str
    description: str = ""
    zone_labels: List[str] = []
    image_spec: Optional[ImageSpec] = None    # FIX 18a: Reference to scene image spec for asset pipeline

class CompareContrastContent(BaseModel):
    subject_a: CompareSubject
    subject_b: CompareSubject
    expected_categories: Dict[str, str]  # zone_label → "similar"|"different"|"unique_a"|"unique_b"
    comparison_mode: str = "side_by_side"
    # Frontend visual config
    highlight_matching: bool = True
    category_types: List[str] = []            # ["similar", "different", "unique_a", "unique_b"]
    category_labels: Dict[str, str] = {}      # category → display label
    category_colors: Dict[str, str] = {}      # category → hex color
    exploration_enabled: bool = False
    zoom_enabled: bool = False

class ClickPrompt(BaseModel):
    zone_label: str
    prompt_text: str
    order: int

class ClickToIdentifyContent(BaseModel):
    prompts: List[ClickPrompt]
    prompt_style: str = "naming"
    selection_mode: str = "sequential"
    # Frontend visual config
    highlight_style: str = "outlined"         # subtle | outlined | invisible
    magnification_enabled: bool = False
    magnification_factor: float = 1.5
    explore_mode_enabled: bool = False
    explore_time_limit_seconds: Optional[int] = None
    show_zone_count: bool = True

class TraceWaypoint(BaseModel):
    zone_label: str
    order: int

class TracePath(BaseModel):
    id: str
    description: str = ""
    requires_order: bool = True
    waypoints: List[TraceWaypoint]

class TracePathContent(BaseModel):
    paths: List[TracePath]
    path_type: str = "linear"
    drawing_mode: str = "click_waypoints"
    # Frontend visual config
    particle_theme: str = "dots"              # dots | arrows | droplets | cells | electrons
    particle_speed: str = "medium"            # slow | medium | fast
    color_transition_enabled: bool = False
    show_direction_arrows: bool = True
    show_waypoint_labels: bool = True
    show_full_flow_on_complete: bool = True
    submit_mode: str = "immediate"            # immediate | batch

class DescriptionEntry(BaseModel):
    zone_label: str
    description: str

class DescriptionMatchingContent(BaseModel):
    descriptions: List[DescriptionEntry]      # LLM produces list; blueprint assembler converts to Dict
    mode: str = "click_zone"
    distractor_descriptions: List[str] = []
    # Frontend visual config
    show_connecting_lines: bool = True
    defer_evaluation: bool = False
    description_panel_position: str = "right" # left | right | bottom

class DragDropContent(BaseModel):
    labels: List[Dict[str, str]]  # [{text, zone_label}]
    distractor_labels: List[str] = []
    # Frontend visual config (most critical — 26/29 fields were missing per 18a)
    interaction_mode: str = "drag_drop"       # drag_drop | click_to_place | reverse
    feedback_timing: str = "immediate"        # immediate | deferred
    label_style: str = "text"                 # text | text_with_icon | text_with_thumbnail | text_with_description
    leader_line_style: str = "elbow"          # straight | elbow | curved | fluid | none
    leader_line_color: str = ""               # hex, empty = theme default
    leader_line_animate: bool = True
    pin_marker_shape: str = "circle"          # circle | diamond | arrow | none
    label_anchor_side: str = "auto"           # auto | left | right | top | bottom
    tray_position: str = "bottom"             # bottom | right | left | top
    tray_layout: str = "horizontal"           # horizontal | vertical | grid | grouped
    placement_animation: str = "spring"       # spring | ease | instant
    incorrect_animation: str = "shake"        # shake | bounce_back | fade_out
    zone_idle_animation: str = "pulse"        # none | pulse | glow | breathe
    zone_hover_effect: str = "highlight"      # highlight | scale | glow | none
    max_attempts: Optional[int] = None
    shuffle_labels: bool = True

class HierarchicalGroup(BaseModel):
    id: str = ""                              # FIX 18a: Set by blueprint assembler "zg_{scene}_{index}"
    parent_label: str
    child_labels: List[str]
    reveal_trigger: str = "complete_parent"

class HierarchicalContent(BaseModel):
    groups: List[HierarchicalGroup]


class MechanicContent(BaseModel):
    """Content for one mechanic instance. Only the relevant field is populated."""
    mechanic_id: str
    mechanic_type: str

    drag_drop: Optional[DragDropContent] = None
    click_to_identify: Optional[ClickToIdentifyContent] = None
    trace_path: Optional[TracePathContent] = None
    sequencing: Optional[SequencingContent] = None
    sorting: Optional[SortingContent] = None
    memory_match: Optional[MemoryMatchContent] = None
    branching: Optional[BranchingContent] = None
    compare_contrast: Optional[CompareContrastContent] = None
    description_matching: Optional[DescriptionMatchingContent] = None
    hierarchical: Optional[HierarchicalContent] = None


# ── Scoring & Feedback ──

class MisconceptionFeedback(BaseModel):
    misconception: str
    trigger: str
    feedback: str
    severity: str = "medium"

class MechanicScoring(BaseModel):
    mechanic_id: str
    mechanic_type: str
    strategy: str = "per_item"
    points_per_correct: int = 10
    max_score: int
    partial_credit: bool = True
    hint_penalty: float = 0.0

class MechanicFeedback(BaseModel):
    mechanic_id: str
    mechanic_type: str
    on_correct: str
    on_incorrect: str
    on_completion: str
    misconception_feedback: List[MisconceptionFeedback] = []
    distractor_feedback: Dict[str, str] = {}

class ModeTransition(BaseModel):
    from_mode: str
    to_mode: str
    trigger: str
    trigger_value: Optional[Any] = None


class SceneContent(BaseModel):
    """Complete content for one scene."""
    scene_id: str
    scene_number: int
    zone_specs: List[ZoneSpec]
    mechanic_contents: Dict[str, MechanicContent]  # mechanic_id → content
    scoring: List[MechanicScoring]
    feedback: List[MechanicFeedback]
    mode_transitions: List[ModeTransition] = []


# ═══════════════════════════════════════════════════════════
# Phase 3: Asset Pipeline
# ═══════════════════════════════════════════════════════════

# ── 3a: Asset Needs (deterministic, from asset_needs_analyzer) ──

class DiagramAssetNeed(BaseModel):
    """What diagram is needed (determined by content, not yet art-directed)."""
    asset_id: str
    scene_id: str
    expected_labels: List[str]
    image_description: str              # From scene concept
    needs_zone_detection: bool = True

class ItemImageNeed(BaseModel):
    asset_id: str
    item_id: str
    description: str
    mechanic_id: str

class NodeImageNeed(BaseModel):
    asset_id: str
    node_id: str
    description: str
    mechanic_id: str

class ColorPaletteNeed(BaseModel):
    asset_id: str
    count: int
    category_labels: List[str] = []
    mechanic_id: str

class AssetNeeds(BaseModel):
    """What assets are needed for a scene (deterministic analysis)."""
    scene_id: str
    primary_diagram: Optional[DiagramAssetNeed] = None
    second_diagram: Optional[DiagramAssetNeed] = None
    item_images: List[ItemImageNeed] = []
    node_illustrations: List[NodeImageNeed] = []
    color_palettes: List[ColorPaletteNeed] = []


# ── 3a: Art Direction (from asset_art_director LLM) ──

class ArtDirectedDiagram(BaseModel):
    """Crafted search + style for one diagram asset."""
    asset_id: str
    search_queries: List[str]           # Multiple crafted queries (primary + fallbacks)
    style_prompt: str                   # Detailed visual direction for regeneration
    spatial_guidance: str = ""          # Layout hints for zone detection
    color_direction: Dict[str, str] = {} # Named color assignments
    annotation_preference: str = "clean_unlabeled"
    negative_prompt: str = ""           # What to avoid in generation
    expected_labels: List[str]

class ArtDirectedItemImage(BaseModel):
    """Crafted search + style for item card images."""
    asset_id: str
    item_id: str
    search_query: str
    style_prompt: str                   # Visual direction matching scene aesthetic
    size_hint: str = "thumbnail"

class ArtDirectedColorPalette(BaseModel):
    """Curated color palette matching scene aesthetic."""
    asset_id: str
    theme: str                          # categorical | warm_cool | anatomical | etc.
    colors: Dict[str, str]             # label → hex color (curated, not random)
    rationale: str = ""                 # Why these colors

class ArtDirectedManifest(BaseModel):
    """Complete art direction for one scene's assets."""
    scene_id: str
    visual_theme: str                   # Overall visual cohesion statement
    primary_diagram: Optional[ArtDirectedDiagram] = None
    second_diagram: Optional[ArtDirectedDiagram] = None
    item_images: List[ArtDirectedItemImage] = []
    node_illustrations: List[ArtDirectedItemImage] = []
    color_palettes: List[ArtDirectedColorPalette] = []


# ── 3b: Asset Results (from asset chains) ──

class DetectedZone(BaseModel):
    id: str
    label: str
    shape: str  # "polygon"|"circle"|"rect"
    coordinates: Dict[str, Any]
    confidence: float = 0.0

class ZoneMatchReport(BaseModel):
    matched: List[Dict[str, Any]]       # [{spec_label, detected_label, confidence, zone_data}]
    unmatched_spec: List[str]           # Labels in spec but not detected
    unmatched_detected: List[str]       # Detected but not in spec

class DiagramAssetResult(BaseModel):
    asset_id: str
    image_url: str
    image_path: str = ""
    zones: List[DetectedZone] = []
    zone_match_report: Optional[ZoneMatchReport] = None

class ItemImageResult(BaseModel):
    asset_id: str
    item_id: str
    image_url: str

class ColorPaletteResult(BaseModel):
    asset_id: str
    colors: Dict[str, str]  # label → hex color

class SceneAssets(BaseModel):
    """Complete assets for one scene."""
    scene_id: str
    primary_diagram: Optional[DiagramAssetResult] = None
    second_diagram: Optional[DiagramAssetResult] = None
    item_images: List[ItemImageResult] = []
    color_palettes: List[ColorPaletteResult] = []


# ═══════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════

class ValidationResult(BaseModel):
    passed: bool
    score: float = 1.0
    issues: List[str] = []
    is_builder_bug: bool = False       # Structural issue in graph builder (should never happen)
    is_design_issue: bool = False      # Creative/semantic issue (triggers retry of the designer)
```

---

## 4. State Definitions (`backend/app/agents/v4/state.py`)

```python
"""V4 Pipeline State — per-phase typed states instead of monolithic AgentState."""

from typing import Annotated, Any, Dict, List, Optional, TypedDict
from operator import add


class V4PipelineState(TypedDict, total=False):
    """
    Top-level state for the V4 pipeline.
    Each phase reads/writes specific fields.

    FIX 18c: Annotated[List, add] reducers for fields written by parallel workers.
    FIX 18b: Added validation feedback fields for retry loops.
    """

    # ── Input (set once at pipeline start) ──
    question_text: str
    question_options: Optional[List[str]]
    question_id: str
    _run_id: str
    _pipeline_preset: str

    # ── Phase 0 outputs ──
    pedagogical_context: Optional[Dict[str, Any]]
    content_structure: Optional[Dict[str, Any]]
    domain_knowledge: Optional[Dict[str, Any]]
    canonical_labels: Optional[List[str]]

    # ── Phase 1a outputs ──
    game_concept: Optional[Dict[str, Any]]           # GameConcept
    _v4_concept_retries: int
    _v4_concept_validation: Optional[Dict[str, Any]] # FIX 18b GAP#1: ValidationResult for retry feedback

    # ── Phase 1b outputs ──
    # FIX 18c: Parallel scene designers write to Annotated reducers
    scene_creative_designs: Optional[Dict[str, Any]]  # {scene_index: SceneCreativeDesign}
    _v4_scene_design_retries: Dict[str, int]          # {scene_index: retry_count}
    _v4_scene_design_validation: Dict[str, Any]       # FIX 18b GAP#2: {scene_index: ValidationResult}
    failed_scene_ids: Annotated[List[str], add]       # FIX 18c: Accumulated from parallel validators

    # ── Graph builder output ──
    game_plan: Optional[Dict[str, Any]]               # GamePlan (from graph builder)
    game_plan_validation: Optional[Dict[str, Any]]    # ValidationResult

    # ── Phase 2 outputs ──
    scene_contents: Optional[Dict[str, Any]]          # {scene_id: SceneContent}
    _v4_content_retries: Dict[str, int]               # {mechanic_id: retry_count}
    _v4_content_validation: Dict[str, Any]            # FIX 18b: {mechanic_id: ValidationResult}
    failed_mechanic_ids: Annotated[List[str], add]    # FIX 18c: Accumulated from parallel validators
    _v4_interaction_retries: Dict[str, int]            # {scene_id: retry_count}
    _v4_interaction_validation: Dict[str, Any]        # FIX 18b: {scene_id: ValidationResult}
    failed_interaction_scene_ids: Annotated[List[str], add]

    # ── Phase 3 outputs ──
    asset_needs: Optional[Dict[str, Any]]             # {scene_id: AssetNeeds}
    art_directed_manifests: Optional[Dict[str, Any]]  # {scene_id: ArtDirectedManifest}
    _v4_art_direction_retries: Dict[str, int]         # {scene_id: retry_count}
    _v4_art_direction_validation: Dict[str, Any]      # FIX 18b: {scene_id: ValidationResult}
    failed_art_direction_scene_ids: Annotated[List[str], add]
    scene_assets: Optional[Dict[str, Any]]            # {scene_id: SceneAssets}
    failed_asset_ids: Annotated[List[str], add]       # FIX 18c: Accumulated from parallel asset chains

    # ── Phase 4 outputs ──
    blueprint: Optional[Dict[str, Any]]
    template_type: str
    generation_complete: bool

    # ── Observability (same as V3) ──
    current_agent: str
    agent_outputs: Dict[str, Any]
    execution_metadata: Dict[str, Any]
```

---

## 5. Phase-by-Phase Implementation

### 5.1 Phase 0: Understanding

#### `phase0/input_analyzer.py`

```
Reuses: V3 input_enhancer.py logic (pedagogical analysis)
Adds: content_structure classification

Implementation:
- Single LLM call via llm_service.generate_json()
- Model: gemini-2.5-flash
- Temp: 0.3
- Output schema: PedagogicalContext (with content_structure field)
- Fallback: _create_fallback_context() from V3 with content_structure defaults

State writes:
  - pedagogical_context
  - content_structure
  - current_agent = "v4_input_analyzer"
```

#### `phase0/dk_retriever.py`

```
Reuses: V3 domain_knowledge_retriever.py (web search loop, label extraction)
Changes:
  - Reads content_structure for intent detection
  - Always attempts ALL enrichment types
  - Keep the iterative web search loop (genuinely needs iteration)

Implementation approach:
  - Import and reuse V3's DK retriever functions where possible
  - Override _detect_query_intent() to read content_structure

State writes:
  - domain_knowledge
  - canonical_labels
  - current_agent = "v4_dk_retriever"

Note: input_analyzer and dk_retriever run in PARALLEL.
```

### 5.2 Phase 1a: Game Concept

#### `phase1/game_concept_designer.py`

```
Completely new. Single structured LLM call.

Implementation:
- Model: gemini-2.5-pro
- Temp: 0.7
- Prompt: (from prompts/game_concept_designer.py)
    - Injects: question_text, pedagogical_context, domain_knowledge summary,
      canonical_labels, capability_spec
    - On retry: appends concept_validator feedback
- Output schema: GameConcept
- Focus: WHAT scenes, WHAT mechanics, WHY — not HOW they look/feel

State writes:
  - game_concept
  - current_agent = "v4_game_concept_designer"
```

#### `phase1/concept_validator.py`

```
Deterministic.

Validates:
  - At least 1 scene, max 6
  - Every scene has at least 1 mechanic
  - All mechanic_types are valid (in our 10 supported types)
  - No orphan mechanics (all connected within scene)
  - Zone labels in mechanic.zone_labels_used exist in scene.zone_labels
  - All scene zone_labels exist in all_zone_labels
  - Visual mechanics (drag_drop, click_to_identify, trace_path, description_matching, hierarchical)
    have needs_diagram=True
  - expected_item_count > 0 for all mechanics
  - compare_contrast has comparison_subjects with 2+ entries (via category_names in creative hints later)
  - advance_trigger values in valid set
  - Timed mechanics have time_limit_seconds > 0

On failure: retry game_concept_designer with specific feedback (max 2)

State writes:
  - _v4_concept_retries (incremented)
  - _v4_concept_validation (ValidationResult with issues[] for retry prompt injection)
```

### 5.3 Phase 1b: Scene Design

#### `phase1/scene_designer.py`

```
Completely new. Single structured LLM call PER SCENE.

Implementation:
- Receives: SceneConcept (from GameConcept), domain_knowledge, pedagogical_context
- Model: gemini-2.5-pro
- Temp: 0.7
- Prompt: (from prompts/scene_designer.py)
    - Scene concept (title, learning_goal, mechanics, zone_labels)
    - Relevant DK data
    - Overall game narrative theme
    - On retry: appends scene_design_validator feedback
- Output schema: SceneCreativeDesign
- Focus: HOW the scene looks/feels, per-mechanic creative direction

All scene designers run in PARALLEL (independent).

FIX 18b GAP#3: Scene designer MUST set scene_id = f"s{scene_index}" explicitly.

State writes:
  - scene_creative_designs[scene_index]
  - current_agent = "v4_scene_designer"
```

#### `phase1/scene_design_validator.py`

```
Deterministic. Per scene.

Validates:
  - FIX 18b GAP#4: Mechanic alignment — len(mechanics) == len(mechanic_designs)
    AND mechanic_types match in order (guards against LLM reordering/omission)
  - Every mechanic in scene has a MechanicCreativeDesign
  - instruction_text non-empty and >20 chars for each mechanic
  - visual_style non-empty for each mechanic
  - layout_mode valid for mechanic_type:
      drag_drop: default, radial, grid, spatial
      sequencing: vertical_list, horizontal_list, radial
      sorting: bucket, column, grid
      trace_path: freehand_guided, click_waypoints, connect_dots
      memory_match: grid, scattered
      click_to_identify: spatial (always)
      description_matching: spatial, list
      branching: tree, flowchart
      compare_contrast: side_by_side, overlay
      hierarchical: tree, nested
  - card_type valid: text_only, icon_and_text, image_card
  - If needs_diagram: image_spec exists with description >20 chars
  - If compare_contrast: second_image_spec exists
  - generation_goal non-empty for each mechanic

On failure: retry ONLY this scene's design with specific feedback (max 2)

State writes:
  - _v4_scene_design_retries[scene_index]
  - _v4_scene_design_validation[scene_index] (ValidationResult for retry prompt)
  - failed_scene_ids (append scene_id if failed)
```

#### `graph_builder.py`

```
Deterministic. ~250 lines.

Input: GameConcept + Dict[int, SceneCreativeDesign]
Output: GamePlan

Implementation:
- build_game_graph(concept, scene_designs) → GamePlan
- _build_mechanic_graph() recursive helper for hierarchy
- All IDs generated: s{scene}_m{counter}
- Connections from list order + advance_trigger
- Scores computed: expected_item_count × points_per_item
- Terminal flags on last top-level mechanic per scene
- MechanicPlan.creative_design populated from SceneCreativeDesign
- MechanicPlan.instruction_text from SceneCreativeDesign
- ScenePlan.creative_design from SceneCreativeDesign
- ScenePlan.image_spec from SceneCreativeDesign

State writes:
  - game_plan
```

### 5.4 Phase 2: Content Build

#### `phase2/scene_context_builder.py`

```
Deterministic HELPER FUNCTION — NOT a graph node.
FIX 18b GAP#5: Called by content dispatch router, not run as separate node.

Input: ScenePlan (from GamePlan) + domain_knowledge
Output: dict with:
  - zone_labels and their DK descriptions
  - relevant DK data (sequence_flow_data, comparison_data, etc.)
  - list of other mechanics in this scene (for awareness)
  - shared terminology reference
  - scene creative vision (from ScenePlan.creative_design)

No LLM call. Pure data assembly.

Usage (inside content dispatch router):
  scene_context = build_scene_context(scene_plan, domain_knowledge)
  # Then pass scene_context in each Send() payload
```

#### `phase2/content_generator.py`

```
Single LLM call per mechanic.

Implementation:
- Receives: MechanicPlan (with creative_design), scene_context, domain_knowledge
- Selects prompt template based on mechanic_type (from prompts/content_generators.py)
- Model: gemini-2.5-pro for branching/compare/sequencing, flash for others
- Temp: 0.5
- Output schema: MechanicContent (with only the relevant sub-field populated)
- On retry: appends content_validator feedback

10 prompt templates, each receives:
  - MechanicCreativeDesign (rich creative direction)
  - Scene context (shared zone labels, DK, other mechanics)
  - On retry: specific validation feedback
```

#### `phase2/content_validator.py`

```
Deterministic. One validator function per mechanic type.

Validates:
  sequencing: items >= 2, correct_order matches item IDs, order_index contiguous
  sorting: categories >= 2, all items have valid correct_category_id
  memory_match: pairs >= 3, all have non-empty front/back
  branching: graph connectivity, start_node exists, end nodes reachable, at least 1 good ending
  compare_contrast: both subjects have zone_labels, expected_categories populated
  trace_path: waypoint zone_labels in scene's zone_labels, orders contiguous
  click_to_identify: prompt zone_labels in scene's zone_labels
  description_matching: description zone_labels in scene's zone_labels
  drag_drop: label zone_labels in scene's zone_labels
  hierarchical: parent/child labels valid, no circular refs

On failure: retry ONLY this mechanic's content_generator (max 2)
```

#### `phase2/interaction_designer.py`

```
Single LLM call per scene.

Implementation:
- Receives: all MechanicContent for scene + MechanicPlans + pedagogical_context + DK
- Model: gemini-2.5-flash
- Temp: 0.4
- Output: {zone_specs: [], scoring: [], feedback: [], mode_transitions: []}

FIX 18b GAP#6/7: Interaction designer produces zone_specs (with LLM-generated hints),
NOT content_merge_node. DK provides base descriptions; interaction designer adds
mechanic-aware, pedagogically-tuned hints.

Key rules:
  - zone_specs: one per zone label in scene, with rich hint text
  - scoring.max_score MUST equal mechanic.max_score from GamePlan
  - scoring.points_per_correct MUST equal mechanic.points_per_item
  - feedback.on_correct/on_incorrect/on_completion must be non-empty
  - at least 1 misconception_feedback per mechanic
```

#### `phase2/interaction_validator.py`

```
Deterministic. Per scene.

Validates:
  - Score arithmetic: scoring.max_score == game_plan mechanic.max_score
  - scoring.points_per_correct == mechanic.points_per_item
  - All mechanics have scoring + feedback entries
  - Mode transitions reference valid mechanic types in this scene
  - Trigger values in valid ranges
  - At least 1 misconception feedback per mechanic

On failure: retry interaction_designer with specific feedback (max 1)
```

### 5.5 Phase 3: Asset Pipeline

#### `phase3/asset_needs_analyzer.py`

```
Deterministic. Builds AssetNeeds per scene.

Input: ScenePlan + SceneContent
Output: AssetNeeds

Logic:
  1. If scene.needs_diagram → add primary_diagram need
  2. If compare_contrast content → add second_diagram need
  3. If any content items have image_description → add item_image needs
  4. If branching nodes have image_description → add node_illustration needs
  5. If sorting categories exist → add color_palette need
  6. If compare_contrast → add color_palette need (similar/different/unique)

Pure analysis — WHAT is needed, not HOW it should look.
```

#### `phase3/asset_art_director.py`

```
Single LLM call per scene. NEW creative stage.

Implementation:
- Receives: AssetNeeds + SceneCreativeDesign + SceneContent + pedagogical_context
- Model: gemini-2.5-flash
- Temp: 0.5
- Prompt: (from prompts/asset_art_director.py)
    - Scene creative vision (visual_concept, color_palette_direction, atmosphere)
    - What assets are needed (from AssetNeeds)
    - What content exists (mechanic items, sequences, etc.)
    - On retry: appends art_direction_validator feedback
- Output schema: ArtDirectedManifest

Translates creative vision + actual content into precise asset specifications:
  - Crafted search queries (not just "heart diagram")
  - Style prompts incorporating scene's color direction
  - Color palettes matching scene aesthetic
  - Item image styles matching visual theme
  - Spatial guidance for zone detection

All art directors run in PARALLEL (one per scene, independent).

State writes:
  - art_directed_manifests[scene_id]
  - current_agent = "v4_asset_art_director"
```

#### `phase3/art_direction_validator.py`

```
Deterministic. Per scene.

Validates:
  - Primary diagram has search_queries (at least 2) if needed
  - Style prompts non-empty and >30 chars
  - Color palette has enough colors for categories
  - All item images have non-empty search_query and style_prompt
  - Color direction keys match category labels
  - No duplicate asset_ids

On failure: retry ONLY this scene's art director (max 1)
```

#### `phase3/asset_chains.py`

```
Pre-built tool chain definitions + execution.

Chains:
  1. diagram_with_zones:
     async def run_diagram_chain(spec: ArtDirectedDiagram, game_id: str) → DiagramAssetResult:
       # Step 1: Search with crafted queries
       ref = await image_retrieval.search(spec.search_queries[0], spec.search_queries[1:])
       # Step 2: Generate/regenerate with art-directed style prompt
       if ref:
         img_bytes = await gemini_image.regenerate_from_reference(ref, spec.style_prompt)
       else:
         img_bytes = await imagen.generate(spec.style_prompt)
       # Step 3: Save
       img_url, img_path = await asset_storage.save(img_bytes, game_id, spec.asset_id)
       # Step 4: Detect zones (gemini flash bbox)
       raw_zones = await gemini_diagram_service.detect_zones(img_bytes, spec.expected_labels)
       # Step 5: Refine zones (SAM3 if available)
       refined_zones = await sam3_service.refine_zones(img_bytes, raw_zones)
       # Step 6: Match
       match_report = zone_matcher.match(refined_zones, spec.expected_labels)
       return DiagramAssetResult(...)

  2. simple_image:
     async def run_simple_image_chain(spec: ArtDirectedItemImage, game_id: str) → ItemImageResult:
       ref = await image_retrieval.search(spec.search_query)
       if ref:
         img_bytes = await gemini_image.regenerate_from_reference(ref, spec.style_prompt)
       else:
         img_bytes = await imagen.generate(spec.style_prompt)
       img_url, _ = await asset_storage.save(img_bytes, game_id, spec.asset_id)
       return ItemImageResult(asset_id=spec.asset_id, item_id=spec.item_id, image_url=img_url)

  3. color_palette:
     Already curated by art director — just pass through.
     def run_color_palette_chain(spec: ArtDirectedColorPalette) → ColorPaletteResult:
       return ColorPaletteResult(asset_id=spec.asset_id, colors=spec.colors)

All chains are async, run in parallel.
```

#### `phase3/zone_matcher.py`

```
Deterministic + optional LLM disambiguation.
Reuses logic from V3 blueprint_assembler_tools.py.

Implementation:
  def match(detected_zones, expected_labels) → ZoneMatchReport:
    # Pass 1: Exact match (case-insensitive, stripped)
    # Pass 2: Fuzzy match (Levenshtein distance < 3 or substring)
    # Pass 3: Unmatched → report

  Zone coordinate normalization:
    - Reuse _normalize_coordinates() logic from V3
    - Convert polygon coords to points: [[x,y], ...]
    - Compute center for all shapes
```

#### `phase3/asset_validator.py`

```
Deterministic. Per scene.

Validates:
  - All mandatory assets generated (primary_diagram if needs_diagram)
  - Zone match quality: at least 70% of expected labels matched
  - Image URLs are valid (non-empty)
  - Color palette count matches

On zone mismatch:
  - If < 70% matched → retry diagram chain with unmatched labels
  - If >= 70% matched → proceed, generate placeholders for unmatched
  - Max 1 retry
```

### 5.6 Phase 4: Assembly

#### `phase4/blueprint_assembler.py`

```
Deterministic. Converts GamePlan + SceneContent + SceneAssets → blueprint JSON.

Reuses V3 logic for:
  - Zone coordinate conversion (_normalize_coordinates, _compute_center)
  - CamelCase normalization (snake_case → camelCase for all frontend fields)
  - Per-mechanic config key placement

Key differences from V3:
  - Reads from V4 schemas (GamePlan, SceneContent, SceneAssets)
  - Zone IDs: zone_{scene_number}_{index}
  - Label IDs: label_{scene_number}_{index}
  - Scoring keyed by mechanic_id
  - Mode transitions from mechanic_connections
  - Timed wrapper from is_timed
  - Hierarchical from parent_mechanic_id → zoneGroups
  - HierarchicalGroup.id generated: "zg_{scene}_{index}"

FIX 18a: Blueprint assembler merge logic for per-mechanic config:
  Per-mechanic config objects (sequenceConfig, sortingConfig, etc.) are built by:
  1. COPYING all fields from MechanicContent.<type> (e.g., SequencingContent)
     → These already include frontend visual config fields (layout_mode, card_type, etc.)
  2. ADDING scoring/feedback from SceneContent.scoring/feedback (matched by mechanic_id)
  3. Converting zone_labels → zone_ids using SceneAssets zone mapping
  4. Converting image_descriptions → image URLs using SceneAssets item_images
  5. For DescriptionMatchingContent: converting List[DescriptionEntry] → Dict[str, str]
  6. For CompareContrastContent: injecting imageUrl from SceneAssets diagrams
  7. CamelCase conversion for all keys

Example merge for sequencing:
  sequenceConfig = {
      "sequenceType": content.sequencing.sequence_type,
      "items": [camelCase(item) for item in content.sequencing.items],
      "correctOrder": content.sequencing.correct_order,
      "instructionText": content.sequencing.instruction_text,
      "layoutMode": content.sequencing.layout_mode,     # FROM content schema
      "cardType": content.sequencing.card_type,          # FROM content schema
      "connectorStyle": content.sequencing.connector_style,
      "interactionPattern": content.sequencing.interaction_pattern,
      "showPositionNumbers": content.sequencing.show_position_numbers,
      "allowPartialCredit": content.sequencing.allow_partial_credit,
  }

State writes:
  - blueprint
  - template_type = "INTERACTIVE_DIAGRAM"
  - generation_complete = True
```

#### `phase4/blueprint_validator.py`

```
Deterministic. Checks against FRONTEND_BACKEND_CONTRACT.md.

Checks:
  1. diagram.assetUrl present for visual scenes
  2. Every label.correctZoneId references an existing zone.id
  3. Every zone has valid coordinates for its shape
  4. mechanics[0].type matches starting mode
  5. Per-mechanic config exists for every active mechanic
  6. sequenceConfig.correctOrder matches item IDs
  7. branchingConfig.startNodeId exists in nodes
  8. compareConfig.diagramA/B have imageUrl and zones
  9. Score arithmetic consistent
  10. Visual config fields (card_type, layout_mode, etc.) present from creative design

On failure: adds _warnings array to blueprint (no retry, assembler is deterministic)
```

---

## 6. Graph Wiring (`backend/app/agents/v4/graph.py`)

**FIX 18c: All 5 dispatch nodes REMOVED. Replaced with conditional_edges routers returning Send lists.**
**Agent count: 22 (was 27 — 5 dispatch nodes removed).**

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send  # LangGraph 1.0+ import path

def create_v4_graph() -> CompiledGraph:
    """
    V4 pipeline graph — 3-stage creative cascade with destructured validation.
    Uses Send API via conditional_edges routers for all fan-out patterns.
    """

    graph = StateGraph(V4PipelineState)

    # ── Phase 0: Understanding (parallel) ──
    graph.add_node("v4_input_analyzer", input_analyzer_node)
    graph.add_node("v4_dk_retriever", dk_retriever_node)
    graph.add_node("v4_merge_phase0", merge_phase0_node)

    graph.add_edge(START, "v4_input_analyzer")
    graph.add_edge(START, "v4_dk_retriever")
    graph.add_edge("v4_input_analyzer", "v4_merge_phase0")
    graph.add_edge("v4_dk_retriever", "v4_merge_phase0")

    # ── Phase 1a: Game Concept (single call + static retry) ──
    graph.add_node("v4_game_concept_designer", game_concept_designer_node)
    graph.add_node("v4_concept_validator", concept_validator_node)

    graph.add_edge("v4_merge_phase0", "v4_game_concept_designer")
    graph.add_edge("v4_game_concept_designer", "v4_concept_validator")
    # Static router: retry or fan-out to scene designers
    graph.add_conditional_edges(
        "v4_concept_validator",
        v4_concept_router,  # Returns "retry" OR List[Send("v4_scene_designer", {...})]
    )

    # ── Phase 1b: Scene Design (Send fan-out per scene) ──
    graph.add_node("v4_scene_designer", scene_designer_node)               # Receives Send payload
    graph.add_node("v4_scene_design_merge", scene_design_merge_node)       # Collects + validates
    graph.add_node("v4_graph_builder", graph_builder_node)

    graph.add_edge("v4_scene_designer", "v4_scene_design_merge")
    # Merge router: retry failed scenes (Send) OR proceed to graph builder (str)
    graph.add_conditional_edges(
        "v4_scene_design_merge",
        v4_scene_design_retry_router,  # Returns List[Send] for failed OR "v4_graph_builder"
    )

    # ── Phase 2a: Content Build (Send fan-out per mechanic) ──
    graph.add_node("v4_content_generator", content_generator_node)         # Receives Send payload
    graph.add_node("v4_content_merge", content_merge_node)

    # FIX 18b GAP#5: scene_context_builder is called INSIDE this router, not as a node
    graph.add_conditional_edges(
        "v4_graph_builder",
        v4_content_dispatch_router,  # Builds scene_context, returns List[Send] per mechanic
    )
    graph.add_edge("v4_content_generator", "v4_content_merge")
    graph.add_conditional_edges(
        "v4_content_merge",
        v4_content_retry_router,  # Returns List[Send] for failed OR "v4_interaction_designer"
    )

    # ── Phase 2b: Interaction Design (Send fan-out per scene) ──
    graph.add_node("v4_interaction_designer", interaction_designer_node)    # Receives Send payload
    graph.add_node("v4_interaction_merge", interaction_merge_node)

    # Dispatch from content_merge (proceed path) fans out to interaction designers
    graph.add_edge("v4_interaction_designer", "v4_interaction_merge")
    graph.add_conditional_edges(
        "v4_interaction_merge",
        v4_interaction_retry_router,  # Returns List[Send] for failed OR "v4_asset_needs_analyzer"
    )

    # ── Phase 3a: Asset Art Direction ──
    graph.add_node("v4_asset_needs_analyzer", asset_needs_analyzer_node)   # Deterministic
    graph.add_node("v4_asset_art_director", asset_art_director_node)       # Receives Send payload
    graph.add_node("v4_art_direction_merge", art_direction_merge_node)

    # FIX 18b GAP#8: Dispatch sends SceneCreativeDesign explicitly in Send payload
    graph.add_conditional_edges(
        "v4_asset_needs_analyzer",
        v4_art_direction_dispatch_router,  # Returns List[Send] per scene
    )
    graph.add_edge("v4_asset_art_director", "v4_art_direction_merge")
    graph.add_conditional_edges(
        "v4_art_direction_merge",
        v4_art_direction_retry_router,  # Returns List[Send] for failed OR fans to asset chains
    )

    # ── Phase 3b: Asset Chains (Send fan-out per asset) ──
    graph.add_node("v4_asset_chain_runner", asset_chain_runner_node)        # Receives Send payload
    graph.add_node("v4_asset_merge", asset_merge_node)

    graph.add_edge("v4_asset_chain_runner", "v4_asset_merge")

    # ── Phase 4: Assembly (deterministic) ──
    graph.add_node("v4_blueprint_assembler", blueprint_assembler_node)
    graph.add_node("v4_blueprint_validator", blueprint_validator_node)

    graph.add_edge("v4_asset_merge", "v4_blueprint_assembler")
    graph.add_edge("v4_blueprint_assembler", "v4_blueprint_validator")
    graph.add_edge("v4_blueprint_validator", END)

    return graph.compile()
```

### Router Function Patterns

**Initial Dispatch Router** (concept_validator → scene designers):
```python
def v4_concept_router(state: V4PipelineState):
    """After concept validation: retry concept OR fan-out to scene designers."""
    validation = state.get("_v4_concept_validation", {})
    if not validation.get("passed", False):
        retries = state.get("_v4_concept_retries", 0)
        if retries < 2:
            return "v4_game_concept_designer"  # Simple retry (single node)
    # Fan out to scene designers
    concept = state["game_concept"]
    return [
        Send("v4_scene_designer", {
            "scene_index": i,
            "scene_concept": scene,
            "narrative_theme": concept["narrative_theme"],
            "domain_knowledge": state["domain_knowledge"],
            "pedagogical_context": state["pedagogical_context"],
            "attempt": 1,
        })
        for i, scene in enumerate(concept["scenes"])
    ]
```

**Selective Retry Router** (scene_design_merge → retry failed OR proceed):
```python
def v4_scene_design_retry_router(state: V4PipelineState):
    """After merge: retry ONLY failed scenes (Send) OR proceed to graph builder."""
    failed = state.get("failed_scene_ids", [])
    retries = state.get("_v4_scene_design_retries", {})
    concept = state["game_concept"]

    retryable = [sid for sid in failed if retries.get(sid, 0) < 2]
    if retryable:
        return [
            Send("v4_scene_designer", {
                "scene_index": int(sid.replace("s", "")),
                "scene_concept": concept["scenes"][int(sid.replace("s", ""))],
                "narrative_theme": concept["narrative_theme"],
                "domain_knowledge": state["domain_knowledge"],
                "pedagogical_context": state["pedagogical_context"],
                "attempt": retries.get(sid, 0) + 1,
                "validation_feedback": state.get("_v4_scene_design_validation", {}).get(sid, ""),
            })
            for sid in retryable
        ]
    return "v4_graph_builder"
```

**Content Dispatch Router** (graph_builder → content generators):
```python
def v4_content_dispatch_router(state: V4PipelineState):
    """After graph builder: build scene contexts, fan out to content generators.
    FIX 18b GAP#5: scene_context_builder called here as helper, not graph node.
    """
    from .phase2.scene_context_builder import build_scene_context
    game_plan = GamePlan(**state["game_plan"])
    dk = state["domain_knowledge"]

    sends = []
    for scene in game_plan.scenes:
        scene_context = build_scene_context(scene, dk)  # Deterministic helper
        for mechanic in scene.mechanics:
            sends.append(Send("v4_content_generator", {
                "mechanic_plan": mechanic.dict(),
                "scene_context": scene_context,
                "domain_knowledge": dk,
                "attempt": 1,
            }))
    return sends
```

**Art Direction Dispatch Router** (asset_needs_analyzer → art directors):
```python
def v4_art_direction_dispatch_router(state: V4PipelineState):
    """FIX 18b GAP#8: Send SceneCreativeDesign explicitly in payload."""
    game_plan = GamePlan(**state["game_plan"])
    asset_needs = state["asset_needs"]
    scene_contents = state["scene_contents"]

    return [
        Send("v4_asset_art_director", {
            "scene_id": scene.scene_id,
            "asset_needs": asset_needs[scene.scene_id],
            "creative_design": scene.creative_design.dict(),  # From ScenePlan
            "scene_content": scene_contents[scene.scene_id],
            "pedagogical_context": state["pedagogical_context"],
            "attempt": 1,
        })
        for scene in game_plan.scenes
    ]
```

**Note on LangGraph parallelism**: Phase 0 parallel execution uses parallel edges from START. All fan-out patterns use LangGraph's `Send` API via conditional_edges routers. LangGraph 1.0.6 fully supports both patterns — no fallback needed.

---

## 7. Destructured Validation Map

Each stage has a focused validator with scoped retries:

```
Stage → Validator → Retry Scope → Retry Cost

Game Concept → concept_validator
  → Retry: game_concept_designer only (~4K tokens)

Scene Design (per scene) → scene_design_validator
  → Retry: ONLY failing scene's scene_designer (~4K tokens)

Content (per mechanic) → content_validator
  → Retry: ONLY failing mechanic's content_generator (~3K tokens)

Interaction (per scene) → interaction_validator
  → Retry: ONLY failing scene's interaction_designer (~3K tokens)

Art Direction (per scene) → art_direction_validator
  → Retry: ONLY failing scene's asset_art_director (~5K tokens)

Asset Chains (per asset) → asset_validator
  → Retry: ONLY failing asset chain (~2K tokens + API call)

Blueprint → blueprint_validator
  → No retry (assembler is deterministic) → adds _warnings
```

Each validator returns `ValidationResult` with specific `issues[]` messages that are injected into the retry prompt, e.g.:
- "Scene 2 mechanic 'trace_path' has layout_mode='grid' — valid options for trace_path: freehand_guided, click_waypoints, connect_dots"
- "Sequencing content has 1 item — minimum is 2"
- "Sorting item 'mitochondria' has correct_category_id='cat_3' which doesn't match any category"

---

## 8. Integration Points

### `routes/generate.py`

```
Add V4 support:

if pipeline_preset == "v4":
    from app.agents.v4.graph import create_v4_graph
    graph = create_v4_graph()
    result = await graph.ainvoke(initial_state)
    blueprint = result.get("blueprint")
    # Same DB save pattern as V3
```

### `config/agent_models.py`

```
V4_AGENT_MODELS = {
    "v4_input_analyzer": {"model": "gemini-2.5-flash", "temperature": 0.3},
    "v4_dk_retriever": {"model": "gemini-2.5-flash", "temperature": 0.2},
    "v4_game_concept_designer": {"model": "gemini-2.5-pro", "temperature": 0.7},
    "v4_scene_designer": {"model": "gemini-2.5-pro", "temperature": 0.7},
    "v4_content_generator_branching": {"model": "gemini-2.5-pro", "temperature": 0.5},
    "v4_content_generator_compare": {"model": "gemini-2.5-pro", "temperature": 0.5},
    "v4_content_generator_sequencing": {"model": "gemini-2.5-pro", "temperature": 0.5},
    "v4_content_generator_default": {"model": "gemini-2.5-flash", "temperature": 0.5},
    "v4_interaction_designer": {"model": "gemini-2.5-flash", "temperature": 0.4},
    "v4_asset_art_director": {"model": "gemini-2.5-flash", "temperature": 0.5},
}
```

### `agents/instrumentation.py`

```
V4_AGENTS = [
    # FIX 18c: 5 dispatch nodes removed (22 agents, was 27)
    "v4_input_analyzer", "v4_dk_retriever",
    "v4_game_concept_designer", "v4_concept_validator",
    "v4_scene_designer", "v4_scene_design_merge",
    "v4_graph_builder",
    "v4_content_generator", "v4_content_merge",
    "v4_interaction_designer", "v4_interaction_merge",
    "v4_asset_needs_analyzer",
    "v4_asset_art_director", "v4_art_direction_merge",
    "v4_asset_chain_runner", "v4_asset_merge",
    "v4_blueprint_assembler", "v4_blueprint_validator",
]
```

---

## 9. Implementation Order

### Wave 1: Foundation (no LLM calls)

| Step | File | What | Depends On |
|------|------|------|------------|
| 1.1 | `v4/schemas.py` | All Pydantic models | Nothing |
| 1.2 | `v4/state.py` | V4PipelineState TypedDict | 1.1 |
| 1.3 | `v4/graph_builder.py` | Deterministic concept + designs → GamePlan | 1.1 |
| 1.4 | `v4/capability_spec.py` | Static capability menu | Nothing |
| 1.5 | `v4/phase1/concept_validator.py` | Structural validation of GameConcept | 1.1 |
| 1.6 | `v4/phase1/scene_design_validator.py` | Per-scene creative design validation | 1.1 |
| 1.7 | `v4/phase2/scene_context_builder.py` | Deterministic scene context builder | 1.1 |
| 1.8 | `v4/phase2/content_validator.py` | Per-mechanic content validation (10 types) | 1.1 |
| 1.9 | `v4/phase2/interaction_validator.py` | Scoring arithmetic + transition checks | 1.1 |
| 1.10 | `v4/phase3/asset_needs_analyzer.py` | Deterministic asset needs analysis | 1.1 |
| 1.11 | `v4/phase3/art_direction_validator.py` | Art direction completeness checks | 1.1 |
| 1.12 | `v4/phase3/zone_matcher.py` | Zone matching algorithm | 1.1 |
| 1.13 | `v4/phase3/asset_validator.py` | Asset completeness checks | 1.1 |
| 1.14 | `v4/phase4/blueprint_validator.py` | Blueprint contract checks | 1.1 |

**Testable**: Unit tests for graph builder, all validators, zone matcher, asset needs analyzer.

### Wave 2: LLM-Calling Stages

| Step | File | What | Depends On |
|------|------|------|------------|
| 2.1 | `v4/prompts/game_concept_designer.py` | Concept designer prompt | 1.4 |
| 2.2 | `v4/prompts/scene_designer.py` | Scene designer prompt | 1.1 |
| 2.3 | `v4/prompts/content_generators.py` | 10 content gen prompts | 1.1 |
| 2.4 | `v4/prompts/interaction_designer.py` | Scoring/feedback prompt | 1.1 |
| 2.5 | `v4/prompts/asset_art_director.py` | Art direction prompt | 1.1 |
| 2.6 | `v4/phase0/input_analyzer.py` | Input analysis agent | 1.1 |
| 2.7 | `v4/phase0/dk_retriever.py` | Enhanced DK retriever | 1.1 |
| 2.8 | `v4/phase1/game_concept_designer.py` | Concept designer agent | 2.1, 1.5 |
| 2.9 | `v4/phase1/scene_designer.py` | Scene designer agent | 2.2, 1.6 |
| 2.10 | `v4/phase2/content_generator.py` | Content gen agent | 2.3, 1.7, 1.8 |
| 2.11 | `v4/phase2/interaction_designer.py` | Interaction design agent | 2.4, 1.9 |
| 2.12 | `v4/phase3/asset_art_director.py` | Art direction agent | 2.5, 1.11 |

### Wave 3: Asset Pipeline

| Step | File | What | Depends On |
|------|------|------|------------|
| 3.1 | `v4/phase3/asset_chains.py` | Pre-built chain implementations | 1.10, 1.12 |
| 3.2 | Test asset chains | End-to-end chain tests | 3.1 |

### Wave 4: Assembly + Wiring

| Step | File | What | Depends On |
|------|------|------|------------|
| 4.1 | `v4/phase4/blueprint_assembler.py` | Blueprint assembly | 1.1, 1.14 |
| 4.2 | `v4/graph.py` | Main graph wiring | All above |
| 4.3 | `routes/generate.py` | V4 preset support | 4.2 |
| 4.4 | `config/agent_models.py` | V4 model assignments | Nothing |
| 4.5 | `agents/instrumentation.py` | V4 agent metadata | 4.2 |

### Wave 5: Testing + Polish

| Step | What | Depends On |
|------|------|------------|
| 5.1 | Unit tests for all validators | Wave 1 |
| 5.2 | Unit tests for graph builder | Wave 1 |
| 5.3 | Integration test: Phase 0 + 1 | Wave 2 |
| 5.4 | Integration test: Phase 2 | Wave 2 |
| 5.5 | Integration test: Phase 3 | Wave 3 |
| 5.6 | E2E test: Full V4 pipeline | Wave 4 |
| 5.7 | Frontend PipelineView.tsx update | Wave 4 |

---

## 10. File Count Summary

| Category | Files | Lines (est.) |
|----------|-------|-------------|
| Schemas | 1 | ~800 (expanded with frontend visual config fields) |
| State | 1 | ~90 (expanded with validation + Annotated fields) |
| Graph builder | 1 | ~250 |
| Capability spec | 1 | ~150 |
| Phase 0 agents | 2 | ~300 |
| Phase 1 agents + validators | 4 | ~400 |
| Phase 2 agents + validators | 5 | ~550 |
| Phase 3 orchestrator + art dir + chains + validators | 6 | ~750 |
| Phase 4 assembler + validator | 2 | ~500 |
| Prompts | 5 | ~500 |
| Graph wiring + routers | 1 | ~350 (expanded with router functions) |
| `__init__.py` files | 7 | ~20 |
| **Total new** | **~33** | **~4,800** |

Plus modifications to:
- `routes/generate.py` (~20 lines)
- `config/agent_models.py` (~15 lines)
- `agents/instrumentation.py` (~30 lines)

---

## 11. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LangGraph Send API issues | Verified: LangGraph 1.0.6 fully supports Send API (tested) |
| Parallel edges from START issues | Verified: LangGraph 1.0.6 fully supports parallel START edges (tested) |
| Game concept produces invalid JSON | json_repair + Pydantic validation + retry with feedback |
| Scene design misses mechanics | scene_design_validator catches → retry only that scene |
| Content gen produces wrong content | Per-mechanic validator → retry only that mechanic |
| Art direction too vague | art_direction_validator checks specificity → retry |
| Asset chain fails (nothing found) | 3-level fallback: serper → imagen → placeholder |
| Zone detection misses labels | Zone matcher reports gaps → retry chain with specific prompts |
| Blueprint doesn't match frontend | Blueprint validator catches → _warnings array |
| V4 breaks existing V3 games | V4 is separate preset — V3 unchanged |

---

## 12. Success Criteria

| Metric | V3 Baseline | V4 Target |
|--------|------------|-----------|
| Token usage | ~67,000 | < 35,000 |
| Latency (2 scenes, 3 mechs) | ~120-180s | < 60s |
| Success rate (valid blueprint) | ~60% | > 90% |
| Mechanic correctness | 1/10 fully working | 10/10 |
| Retry rate | ~50% (graph structure) | < 15% (semantic only) |
| Score arithmetic correct | ~70% | 100% (computed, not LLM) |
| Game feels custom-designed | generic/boilerplate | unique per query |
| Visual cohesion within scene | none | art-directed |
| Retry cost per failure | ~15K tokens | ~3-5K tokens |

---

## 13. Gap Analysis Fixes Applied (from 18a/18b/18c)

### Summary of Changes

| Doc | Gap | Fix Applied | Section |
|-----|-----|-------------|---------|
| 18c | 5 dispatch nodes use static edges (will crash) | Removed all dispatch nodes, replaced with conditional_edges routers returning Send lists | §6 |
| 18c | Retry routes to dispatch nodes (selective retry broken) | Retry routers return Send lists directly for failed units | §6 |
| 18c | asyncio.gather() fallback note misleading | Replaced with accurate note: LangGraph 1.0.6 fully supports all patterns | §6, §11 |
| 18c | Missing Annotated reducers for parallel writes | Added `Annotated[List[str], add]` for all `failed_*_ids` fields | §4 |
| 18b #1 | Missing `_v4_concept_validation` state field | Added to V4PipelineState | §4 |
| 18b #2 | Missing `_v4_scene_design_validation` state field | Added to V4PipelineState | §4 |
| 18b #3 | scene_id assignment unclear | Documented: scene_designer sets `scene_id = f"s{scene_index}"` | §5.3 |
| 18b #4 | Mechanic matching fragile (index-based) | Added `mechanic_id` to MechanicChoice + MechanicCreativeDesign + alignment validator | §3, §5.3 |
| 18b #5 | scene_context_builder never runs as graph node | Made helper called inside content_dispatch_router | §5.4, §6 |
| 18b #6 | zone_specs ownership unclear | Assigned to interaction_designer (LLM-generated hints) | §5.4 |
| 18b #7 | Zone hints source unclear | Decided: interaction_designer generates mechanic-aware hints | §5.4 |
| 18b #8 | Art director needs SceneCreativeDesign | Sent explicitly in art_direction_dispatch_router payload | §6 |
| 18a | MechanicCreativeDesign ≠ frontend config | Moved visual config fields INTO per-mechanic content schemas | §3 |
| 18a | DragDropConfig 26/29 fields missing | Added 16 frontend visual fields to DragDropContent | §3 |
| 18a | CompareContrastContent missing image data | Added `CompareSubject.id` and `CompareSubject.image_spec` | §3 |
| 18a | DescriptionMatchingContent type mismatch | Documented: List in schema, blueprint assembler converts to Dict | §3 |
| 18a | HierarchicalGroup lacks id | Added `HierarchicalGroup.id` (set by blueprint assembler) | §3 |
| 18a | Blueprint assembler merge logic undefined | Documented exact merge rules per mechanic type | §5.6 |
| 18a | Agent count wrong (27) | Corrected to 22 (5 dispatch nodes removed) | §6, §8 |

### Remaining Items (Deferred)

| Item | Why Deferred | When |
|------|-------------|------|
| Temporal intelligence (temporalConstraints, motionPaths) | No V4 agent produces these; optional frontend feature | V4.1+ |
| Frontend type reduction | Simplify 78 missing frontend fields by accepting defaults | V4.1+ |
| Schema-driven rendering | Frontend reads MechanicCreativeDesign directly | V4.2+ |
| Multi-scene persistence | Frontend useLabelDiagramState persistence across scenes | V4.1+ |
