"""Mechanic Content schemas — output of the Content Generator (Phase 2a).

Each mechanic type has its own Pydantic model with:
1. Core content fields (items, pairs, nodes, etc.)
2. Frontend visual config fields (populated from MechanicCreativeDesign)

Field names MUST match the frontend's expected field names EXACTLY.

Critical remappings from V3 (audit 33):
- memory_match: front/back (NOT term/definition)
- branching: question/options/nextNodeId/isCorrect (camelCase)
- sorting: label (NOT name)
- trace_path: particleSpeed as string enum (NOT float)
- memory_match: gridSize as [int, int] (NOT string "4x3")
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Drag & Drop ──────────────────────────────────────────────────

class DragDropContent(BaseModel):
    """Content for drag_drop mechanic. Zone-based."""

    labels: list[str] = Field(min_length=1)
    distractor_labels: list[str] = Field(default_factory=list)

    # Frontend visual config (from MechanicCreativeDesign)
    interaction_mode: str = "drag_drop"
    feedback_timing: str = "immediate"
    label_style: Literal["text", "text_with_icon", "text_with_thumbnail", "text_with_description"] = "text"
    leader_line_style: str = "elbow"
    leader_line_color: str = ""
    leader_line_animate: bool = True
    pin_marker_shape: str = "circle"
    label_anchor_side: str = "auto"
    tray_position: str = "bottom"
    tray_layout: str = "horizontal"
    placement_animation: str = "spring"
    incorrect_animation: str = "shake"
    zone_idle_animation: str = "pulse"
    zone_hover_effect: str = "highlight"
    max_attempts: int = 3
    shuffle_labels: bool = True


# ── Click to Identify ────────────────────────────────────────────

class IdentificationPromptInput(BaseModel):
    """Single identification prompt. Becomes root-level identificationPrompts[]."""

    text: str
    target_label: str
    explanation: str = ""
    order: int = 0


class ClickToIdentifyContent(BaseModel):
    """Content for click_to_identify. Zone-based.
    Prompts become root-level identificationPrompts[] in blueprint.
    """

    prompts: list[IdentificationPromptInput] = Field(min_length=1)

    # Frontend visual config
    prompt_style: str = "naming"
    selection_mode: str = "sequential"
    highlight_style: str = "outlined"
    magnification_enabled: bool = False
    magnification_factor: float = 1.5
    explore_mode_enabled: bool = False
    show_zone_count: bool = True


# ── Trace Path ───────────────────────────────────────────────────

class WaypointInput(BaseModel):
    """Single waypoint on a trace path."""

    label: str
    order: int


class PathInput(BaseModel):
    """Single path definition. Becomes root-level paths[] in blueprint."""

    label: str
    description: str = ""
    color: str = "#4A90D9"
    requiresOrder: bool = True
    waypoints: list[WaypointInput] = Field(min_length=2)


class TracePathContent(BaseModel):
    """Content for trace_path. Zone-based.
    Paths become root-level paths[] in blueprint.
    """

    paths: list[PathInput] = Field(min_length=1)

    # Frontend visual config
    path_type: str = "linear"
    drawing_mode: str = "click_waypoints"
    particleTheme: str = "dots"
    particleSpeed: Literal["slow", "medium", "fast"] = "medium"
    color_transition_enabled: bool = False
    show_direction_arrows: bool = True
    show_waypoint_labels: bool = True
    show_full_flow_on_complete: bool = True
    submit_mode: str = "immediate"


# ── Sequencing ───────────────────────────────────────────────────

class SequenceItemInput(BaseModel):
    """Single item in a sequence."""

    id: str
    content: str
    explanation: str = ""
    icon: str = ""
    image_url: Optional[str] = None
    image_description: Optional[str] = None


class SequencingContent(BaseModel):
    """Content for sequencing. Content-only (no zones)."""

    items: list[SequenceItemInput] = Field(min_length=2)
    correct_order: list[str]
    sequence_type: Literal["ordered", "cyclic", "branching"] = "ordered"

    # Frontend visual config
    layout_mode: str = "vertical_list"
    interaction_pattern: str = "drag_reorder"
    card_type: str = "text_only"
    connector_style: str = "arrow"
    show_position_numbers: bool = False
    allow_partial_credit: bool = True


# ── Sorting Categories ───────────────────────────────────────────

class SortingCategoryInput(BaseModel):
    """Single sorting category. Uses 'label' NOT 'name'."""

    id: str
    label: str
    color: str = "#4A90D9"
    description: str = ""


class SortingItemInput(BaseModel):
    """Single item to be sorted into a category."""

    id: str
    content: str
    correctCategoryId: str
    correct_category_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    description: str = ""
    difficulty: str = "medium"
    image: Optional[str] = None
    image_description: Optional[str] = None


class SortingContent(BaseModel):
    """Content for sorting_categories. Content-only (no zones)."""

    categories: list[SortingCategoryInput] = Field(min_length=2)
    items: list[SortingItemInput] = Field(min_length=2)

    # Frontend visual config
    sort_mode: str = "bucket"
    item_card_type: str = "text_only"
    container_style: str = "bucket"
    submit_mode: str = "immediate_feedback"
    allow_multi_category: bool = False
    show_category_hints: bool = False
    allow_partial_credit: bool = True


# ── Memory Match ─────────────────────────────────────────────────

class MemoryPairInput(BaseModel):
    """Single memory pair. Uses 'front/back' NOT 'term/definition'."""

    id: str
    front: str
    back: str
    frontType: Literal["text", "image"] = "text"
    backType: Literal["text", "image"] = "text"
    explanation: str = ""
    category: str = ""


class MemoryMatchContent(BaseModel):
    """Content for memory_match. Content-only (no zones)."""

    pairs: list[MemoryPairInput] = Field(min_length=3)
    game_variant: Literal["classic", "column_match"] = "classic"
    gridSize: Optional[list[int]] = None

    # Frontend visual config
    match_type: str = "term_to_definition"
    card_back_style: str = "question_mark"
    matched_card_behavior: str = "fade"
    show_explanation_on_match: bool = True
    flip_duration_ms: int = 400
    show_attempts_counter: bool = True


# ── Branching Scenario ───────────────────────────────────────────

class DecisionOptionInput(BaseModel):
    """Single option in a decision node. Uses camelCase field names."""

    id: str
    text: str
    nextNodeId: Optional[str] = None
    isCorrect: bool = False
    consequence: Optional[str] = None
    points: int = 0
    quality: Optional[str] = None


class DecisionNodeInput(BaseModel):
    """Single node in a branching scenario. Uses 'question' NOT 'prompt'."""

    id: str
    question: str
    description: str = ""
    node_type: str = "decision"
    options: list[DecisionOptionInput] = Field(default_factory=list)
    isEndNode: bool = False
    endMessage: Optional[str] = None
    ending_type: Optional[str] = None
    narrative_text: str = ""
    image_description: Optional[str] = None


class BranchingContent(BaseModel):
    """Content for branching_scenario. Content-only (no zones)."""

    nodes: list[DecisionNodeInput] = Field(min_length=2)
    startNodeId: str
    narrative_structure: str = "branching"

    # Frontend visual config
    show_path_taken: bool = True
    allow_backtrack: bool = False
    show_consequences: bool = True
    multiple_valid_endings: bool = False


# ── Compare & Contrast ──────────────────────────────────────────

class CompareSubject(BaseModel):
    """One subject in a comparison."""

    id: str
    name: str
    description: str = ""
    zone_labels: list[str] = Field(default_factory=list)


class CompareContrastContent(BaseModel):
    """Content for compare_contrast. Dual-diagram mechanic."""

    subject_a: CompareSubject
    subject_b: CompareSubject
    expected_categories: dict[str, str] = Field(default_factory=dict)
    comparison_mode: str = "side_by_side"

    # Frontend visual config
    highlight_matching: bool = True
    category_types: list[str] = Field(default_factory=list)
    category_labels: dict[str, str] = Field(default_factory=dict)
    category_colors: dict[str, str] = Field(default_factory=dict)
    exploration_enabled: bool = False
    zoom_enabled: bool = False


# ── Description Matching ─────────────────────────────────────────

class DescriptionMatchingContent(BaseModel):
    """Content for description_matching. Zone-based."""

    descriptions: dict[str, str]  # zone_label -> description
    mode: Literal["click_zone", "drag_description", "multiple_choice"] = "click_zone"
    distractor_descriptions: Optional[list[str]] = None

    # Frontend visual config
    show_connecting_lines: bool = True
    defer_evaluation: bool = False
    description_panel_position: str = "right"


# ── Hierarchical ────────────────────────────────────────────────

class HierarchicalGroupInput(BaseModel):
    """Single hierarchical group definition."""

    parent_label: str
    child_labels: list[str]
    reveal_trigger: str = "complete_parent"


class HierarchicalContent(BaseModel):
    """Content for hierarchical mechanic. Zone-based."""

    groups: list[HierarchicalGroupInput] = Field(min_length=1)


# ── Union wrapper ────────────────────────────────────────────────

MECHANIC_CONTENT_MODELS: dict[str, type[BaseModel]] = {
    "drag_drop": DragDropContent,
    "click_to_identify": ClickToIdentifyContent,
    "trace_path": TracePathContent,
    "sequencing": SequencingContent,
    "sorting_categories": SortingContent,
    "memory_match": MemoryMatchContent,
    "branching_scenario": BranchingContent,
    "description_matching": DescriptionMatchingContent,
    "compare_contrast": CompareContrastContent,
    "hierarchical": HierarchicalContent,
}


def get_content_model(mechanic_type: str) -> type[BaseModel]:
    """Get the Pydantic content model for a mechanic type."""
    model = MECHANIC_CONTENT_MODELS.get(mechanic_type)
    if model is None:
        raise ValueError(f"No content model for mechanic type: {mechanic_type}")
    return model
