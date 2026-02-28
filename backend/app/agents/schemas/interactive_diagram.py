"""
Pydantic schemas for INTERACTIVE_DIAGRAM blueprint and SVG spec.
Used for guided decoding and validation.

Supports multiple interaction modes:
- drag_drop: Traditional drag labels to zones
- click_to_identify: Click on zones to identify (hotspot)
- trace_path: Trace a path through waypoints
- hierarchical: Multi-level diagrams with expandable zones
"""

from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


# Interaction mode types
# Preset 1 modes: drag_drop, click_to_identify, trace_path, hierarchical
# Preset 2 adds: description_matching, compare_contrast, sequencing, timed_challenge
# Preset 3 adds: sorting_categories, memory_match, branching_scenario
InteractionMode = Literal[
    "drag_drop",
    "click_to_identify",
    "trace_path",
    "hierarchical",
    "description_matching",  # Preset 2: Match descriptions to zones
    "compare_contrast",      # Preset 2: Side-by-side diagram comparison
    "sequencing",            # Preset 2: Order labels by property
    "timed_challenge",       # Preset 2: Speed-based labeling
    "sorting_categories",    # Preset 3: Sort items into categories
    "memory_match",          # Preset 3: Match pairs by flipping cards
    "branching_scenario",    # Preset 3: Navigate through decision points
]

# Scene progression types for multi-scene games (Preset 2)
SceneProgressionType = Literal["linear", "zoom_in", "depth_first", "branching"]
AnimationType = Literal["pulse", "glow", "scale", "shake", "fade", "bounce", "confetti", "path_draw"]
EasingType = Literal["linear", "ease-out", "ease-in-out", "bounce", "elastic"]


class AnimationSpec(BaseModel):
    """Structured animation specification for game interactions."""
    model_config = ConfigDict(extra="forbid")

    type: AnimationType
    duration_ms: int = Field(default=300, ge=50, le=3000)
    easing: EasingType = "ease-out"
    color: Optional[str] = None  # CSS color for glow/pulse effects
    intensity: Optional[float] = Field(default=1.0, ge=0.1, le=3.0)
    delay_ms: Optional[int] = Field(default=0, ge=0, le=1000)


class InteractiveDiagramZone(BaseModel):
    """A droppable/clickable zone on the diagram."""
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    # Position and size (for circle and rect shapes)
    x: Optional[float] = Field(default=None, ge=0, le=100)
    y: Optional[float] = Field(default=None, ge=0, le=100)
    radius: Optional[float] = Field(default=None, ge=1, le=50)

    # Zone shape for interactive overlay
    shape: Literal["circle", "polygon", "rect"] = "circle"

    # Polygon support (Preset 2): list of [x, y] coordinate pairs (0-100% scale)
    points: Optional[List[List[float]]] = None

    # Center point for label placement (auto-calculated for polygons)
    center: Optional[Dict[str, float]] = None

    # Unlimited hierarchy support (Preset 2)
    parentZoneId: Optional[str] = None
    hierarchyLevel: int = 1  # 1 = root, 2 = child, 3 = grandchild, etc.
    childZoneIds: Optional[List[str]] = None

    # Educational metadata
    description: Optional[str] = None
    hint: Optional[str] = None
    difficulty: int = Field(default=1, ge=1, le=5)

    # Diagram type specific metadata
    diagramType: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ZoneGroup(BaseModel):
    """Group of zones for hierarchical interactions."""
    model_config = ConfigDict(extra="forbid")

    id: str
    parentZoneId: str
    childZoneIds: List[str]
    revealTrigger: Literal["complete_parent", "click_expand", "hover_reveal"] = "complete_parent"
    label: Optional[str] = None


class InteractiveDiagramLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    correctZoneId: str


class IdentificationPrompt(BaseModel):
    """Prompt for click-to-identify mode."""
    model_config = ConfigDict(extra="forbid")

    zoneId: str
    prompt: str
    order: Optional[int] = None  # For sequential identification


class PathWaypoint(BaseModel):
    """Waypoint for path tracing mode."""
    model_config = ConfigDict(extra="forbid")

    zoneId: str
    order: int
    type: Optional[Literal["standard", "gate", "branch_point", "terminus"]] = None
    svg_path_data: Optional[str] = None


class TracePath(BaseModel):
    """Path definition for trace_path interaction mode."""
    model_config = ConfigDict(extra="forbid")

    id: str
    waypoints: List[PathWaypoint]
    description: str
    requiresOrder: bool = True


class InteractiveDiagramTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["interactive_diagram", "identify_function", "trace_path", "click_identify", "hierarchical_label"]
    questionText: str
    requiredToProceed: bool


class InteractiveDiagramHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zoneId: str
    hintText: str


class StructuredAnimations(BaseModel):
    """Structured animation specs replacing text-only cues."""
    model_config = ConfigDict(extra="forbid")

    labelDrag: Optional[AnimationSpec] = None
    correctPlacement: AnimationSpec = Field(
        default_factory=lambda: AnimationSpec(type="pulse", duration_ms=400, color="#22c55e")
    )
    incorrectPlacement: AnimationSpec = Field(
        default_factory=lambda: AnimationSpec(type="shake", duration_ms=300, color="#ef4444")
    )
    completion: Optional[AnimationSpec] = None
    zoneHover: Optional[AnimationSpec] = None
    pathProgress: Optional[AnimationSpec] = None


class InteractiveDiagramAnimationCues(BaseModel):
    """Text-based animation cues (legacy format, still supported)."""
    model_config = ConfigDict(extra="forbid")

    labelDrag: Optional[str] = None
    correctPlacement: str
    incorrectPlacement: str
    allLabeled: Optional[str] = None


class InteractiveDiagramFeedbackMessages(BaseModel):
    model_config = ConfigDict(extra="forbid")

    perfect: str
    good: str
    retry: str


# =============================================================================
# PRESET 3 INTERACTION MODE CONFIGS
# =============================================================================

class SortingItem(BaseModel):
    """Item to be sorted into a category."""
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    correctCategoryId: str
    correct_category_ids: Optional[List[str]] = None  # Multi-category support
    description: Optional[str] = None
    image: Optional[str] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None


class SortingCategory(BaseModel):
    """Category for sorting items."""
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    description: Optional[str] = None
    color: Optional[str] = None


class SortingConfig(BaseModel):
    """Configuration for sorting_categories interaction mode."""
    model_config = ConfigDict(extra="allow")

    items: List[SortingItem]
    categories: List[SortingCategory]
    allowPartialCredit: bool = True
    showCategoryHints: bool = True
    instructions: Optional[str] = None
    sort_mode: Optional[Literal["bucket", "venn_2", "venn_3", "matrix", "column"]] = None
    item_card_type: Optional[Literal["text_only", "text_with_icon", "image_with_caption"]] = None
    container_style: Optional[Literal["bucket", "labeled_bin", "circle", "cell", "column"]] = None
    submit_mode: Optional[Literal["batch_submit", "immediate_feedback", "round_based"]] = None
    allow_multi_category: Optional[bool] = None


class MemoryMatchPair(BaseModel):
    """A pair for memory matching."""
    model_config = ConfigDict(extra="forbid")

    id: str
    front: str
    back: str
    frontType: Literal["text", "image"] = "text"
    backType: Literal["text", "image"] = "text"
    explanation: Optional[str] = None  # Shown when pair is matched
    category: Optional[str] = None  # For progressive reveal


class MemoryMatchConfig(BaseModel):
    """Configuration for memory_match interaction mode."""
    model_config = ConfigDict(extra="allow")

    pairs: List[MemoryMatchPair]
    gridSize: Optional[List[int]] = None  # [rows, cols]
    flipDurationMs: int = 300
    showAttemptsCounter: bool = True
    instructions: Optional[str] = None
    game_variant: Optional[Literal["classic", "column_match", "scatter", "progressive", "peek"]] = None
    match_type: Optional[Literal["term_to_definition", "image_to_label", "diagram_region_to_label", "concept_to_example"]] = None
    card_back_style: Optional[Literal["solid", "gradient", "pattern", "question_mark"]] = None
    matched_card_behavior: Optional[Literal["fade", "shrink", "collect", "checkmark"]] = None
    show_explanation_on_match: Optional[bool] = None


class DecisionOption(BaseModel):
    """An option in a decision node."""
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    nextNodeId: Optional[str] = None
    isCorrect: Optional[bool] = None
    consequence: Optional[str] = None
    points: int = 0
    quality: Optional[Literal["optimal", "acceptable", "suboptimal", "harmful"]] = None
    consequence_text: Optional[str] = None


class DecisionNode(BaseModel):
    """A node in a branching scenario."""
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    options: List[DecisionOption]
    isEndNode: bool = False
    endMessage: Optional[str] = None
    node_type: Optional[Literal["decision", "info", "ending", "checkpoint"]] = None
    narrative_text: Optional[str] = None
    ending_type: Optional[Literal["good", "neutral", "bad"]] = None


class BranchingConfig(BaseModel):
    """Configuration for branching_scenario interaction mode."""
    model_config = ConfigDict(extra="allow")

    nodes: List[DecisionNode]
    startNodeId: str
    showPathTaken: bool = True
    allowBacktrack: bool = True
    showConsequences: bool = True
    multipleValidEndings: bool = False
    instructions: Optional[str] = None
    narrative_structure: Optional[Literal["linear", "branching", "foldback"]] = None


class CompareDiagram(BaseModel):
    """Diagram definition for compare_contrast mode."""
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    imageUrl: str
    zones: List[Dict[str, Any]]


class CompareConfig(BaseModel):
    """Configuration for compare_contrast mode with two separate diagrams."""
    model_config = ConfigDict(extra="allow")

    diagramA: CompareDiagram
    diagramB: CompareDiagram
    expectedCategories: Dict[str, Literal["similar", "different", "unique_a", "unique_b"]]
    highlightMatching: bool = True
    instructions: Optional[str] = None
    comparison_mode: Optional[Literal["side_by_side", "slider", "overlay_toggle", "venn", "spot_difference"]] = None
    category_types: Optional[List[str]] = None
    category_labels: Optional[Dict[str, str]] = None
    category_colors: Optional[Dict[str, str]] = None
    exploration_enabled: Optional[bool] = None
    zoom_enabled: Optional[bool] = None


# =============================================================================
# PER-MECHANIC CONFIG TYPES (V4 DSL — mirrors frontend types.ts exactly)
# =============================================================================

# Literal types for DragDropConfig
LeaderLineStyle = Literal["straight", "elbow", "curved", "fluid", "none"]
PinMarkerShape = Literal["circle", "diamond", "arrow", "none"]
LabelCardStyle = Literal["text", "text_with_icon", "text_with_thumbnail", "text_with_description"]
TrayLayout = Literal["horizontal", "vertical", "grid", "grouped"]
DragDropInteractionMode = Literal["drag_drop", "click_to_place", "reverse"]


class DragDropConfig(BaseModel):
    """Configuration for drag_drop interaction mode — mirrors frontend DragDropConfig."""
    model_config = ConfigDict(extra="allow")

    # Interaction
    interaction_mode: Optional[DragDropInteractionMode] = None
    feedback_timing: Optional[Literal["immediate", "deferred"]] = None

    # Zone rendering
    zone_idle_animation: Optional[Literal["none", "pulse", "glow", "breathe"]] = None
    zone_hover_effect: Optional[Literal["highlight", "scale", "glow", "none"]] = None

    # Label card
    label_style: Optional[LabelCardStyle] = None

    # Placement animation
    placement_animation: Optional[Literal["spring", "ease", "instant"]] = None
    spring_stiffness: Optional[float] = None
    spring_damping: Optional[float] = None
    incorrect_animation: Optional[Literal["shake", "bounce_back", "fade_out"]] = None
    show_placement_particles: Optional[bool] = None

    # Leader lines
    leader_line_style: Optional[LeaderLineStyle] = None
    leader_line_color: Optional[str] = None
    leader_line_width: Optional[float] = None
    leader_line_animate: Optional[bool] = None
    pin_marker_shape: Optional[PinMarkerShape] = None
    label_anchor_side: Optional[Literal["auto", "left", "right", "top", "bottom"]] = None

    # Label tray
    tray_position: Optional[Literal["bottom", "right", "left", "top"]] = None
    tray_layout: Optional[TrayLayout] = None
    tray_show_remaining: Optional[bool] = None
    tray_show_categories: Optional[bool] = None

    # Distractors
    show_distractors: Optional[bool] = None
    distractor_count: Optional[int] = None
    distractor_rejection_mode: Optional[Literal["immediate", "deferred"]] = None

    # Zoom/pan
    zoom_enabled: Optional[bool] = None
    zoom_min: Optional[float] = None
    zoom_max: Optional[float] = None
    minimap_enabled: Optional[bool] = None

    # Max attempts
    max_attempts: Optional[int] = None
    shuffle_labels: Optional[bool] = None

    # Legacy compat
    showLeaderLines: Optional[bool] = None
    snapAnimation: Optional[Literal["spring", "ease", "none"]] = None
    showInfoPanelOnCorrect: Optional[bool] = None
    maxAttempts: Optional[int] = None
    shuffleLabels: Optional[bool] = None
    showHints: Optional[bool] = None


class ClickToIdentifyConfig(BaseModel):
    """Configuration for click_to_identify interaction mode."""
    model_config = ConfigDict(extra="allow")

    promptStyle: Optional[Literal["naming", "functional"]] = None
    selectionMode: Optional[Literal["sequential", "any_order"]] = None
    highlightStyle: Optional[Literal["subtle", "outlined", "invisible"]] = None
    magnificationEnabled: Optional[bool] = None
    magnificationFactor: Optional[float] = None
    exploreModeEnabled: Optional[bool] = None
    exploreTimeLimitSeconds: Optional[int] = None
    showZoneCount: Optional[bool] = None
    instructions: Optional[str] = None


class TracePathConfig(BaseModel):
    """Configuration for trace_path interaction mode."""
    model_config = ConfigDict(extra="allow")

    pathType: Optional[Literal["linear", "branching", "circular"]] = None
    drawingMode: Optional[Literal["click_waypoints", "freehand"]] = None
    particleTheme: Optional[Literal["dots", "arrows", "droplets", "cells", "electrons"]] = None
    particleSpeed: Optional[Literal["slow", "medium", "fast"]] = None
    colorTransitionEnabled: Optional[bool] = None
    showDirectionArrows: Optional[bool] = None
    showWaypointLabels: Optional[bool] = None
    showFullFlowOnComplete: Optional[bool] = None
    instructions: Optional[str] = None
    submitMode: Optional[Literal["immediate", "batch"]] = None


class DescriptionMatchingConfig(BaseModel):
    """Configuration for description_matching interaction mode."""
    model_config = ConfigDict(extra="allow")

    descriptions: Optional[Dict[str, str]] = None
    mode: Optional[Literal["click_zone", "drag_description", "multiple_choice"]] = None
    show_connecting_lines: Optional[bool] = None
    defer_evaluation: Optional[bool] = None
    distractor_count: Optional[int] = None
    description_panel_position: Optional[Literal["left", "right", "bottom"]] = None


class SequenceConfigItem(BaseModel):
    """A single item in a sequence configuration."""
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    is_distractor: Optional[bool] = None
    order_index: Optional[int] = None


class SequenceConfig(BaseModel):
    """Sequence configuration for order-based mechanics."""
    model_config = ConfigDict(extra="allow")

    sequenceType: Literal["linear", "cyclic", "branching"] = "linear"
    items: List[SequenceConfigItem] = Field(default_factory=list)
    correctOrder: List[str] = Field(default_factory=list)
    allowPartialCredit: Optional[bool] = None
    instructionText: Optional[str] = None
    layout_mode: Optional[Literal[
        "horizontal_timeline", "vertical_list", "circular_cycle", "flowchart", "insert_between"
    ]] = None
    interaction_pattern: Optional[Literal[
        "drag_reorder", "drag_to_slots", "click_to_swap", "number_typing"
    ]] = None
    card_type: Optional[Literal[
        "text_only", "text_with_icon", "image_with_caption", "image_only"
    ]] = None
    connector_style: Optional[Literal["arrow", "line", "numbered", "none"]] = None
    show_position_numbers: Optional[bool] = None


class EnhancedLabel(BaseModel):
    """Extended label with rich card data for enhanced drag_drop."""
    model_config = ConfigDict(extra="allow")

    id: str
    text: str
    correctZoneId: str
    icon: Optional[str] = None
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class EnhancedDistractorLabel(BaseModel):
    """Distractor label with confusion target and explanation."""
    model_config = ConfigDict(extra="allow")

    id: str
    text: str
    explanation: str
    confusion_target_zone_id: Optional[str] = None
    category: Optional[str] = None


class LeaderLineAnchor(BaseModel):
    """Leader line anchor points per zone."""
    model_config = ConfigDict(extra="forbid")

    zone_id: str
    pin_x: float = Field(ge=0, le=100)
    pin_y: float = Field(ge=0, le=100)
    label_x: float = Field(ge=0, le=100)
    label_y: float = Field(ge=0, le=100)
    preferred_style: Optional[LeaderLineStyle] = None


class MechanicScoring(BaseModel):
    """Scoring configuration for a mechanic."""
    model_config = ConfigDict(extra="allow")

    strategy: str = "per_correct"
    points_per_correct: int = 10
    max_score: int = 100
    partial_credit: Optional[bool] = None


class MechanicFeedback(BaseModel):
    """Feedback configuration for a mechanic."""
    model_config = ConfigDict(extra="allow")

    on_correct: str = "Correct!"
    on_incorrect: str = "Try again"
    on_completion: str = "Well done!"
    misconceptions: Optional[List[Dict[str, str]]] = None


class Mechanic(BaseModel):
    """A single game mechanic with its type and optional configuration."""
    model_config = ConfigDict(extra="allow")

    type: InteractionMode
    config: Optional[Dict[str, Any]] = None
    scoring: Optional[MechanicScoring] = None
    feedback: Optional[MechanicFeedback] = None


class BlueprintModeTransition(BaseModel):
    """Defines a transition between interaction modes in the blueprint."""
    model_config = ConfigDict(extra="allow")

    from_mode: InteractionMode = Field(alias="from")
    to: InteractionMode
    trigger: str  # ModeTransitionTrigger
    triggerValue: Optional[Any] = None
    animation: Optional[Literal["fade", "slide", "zoom", "none"]] = None
    message: Optional[str] = None


class ScoringStrategy(BaseModel):
    """Scoring strategy for the game."""
    model_config = ConfigDict(extra="allow")

    type: str = "per_correct"
    base_points_per_zone: int = 10
    time_bonus_enabled: Optional[bool] = None
    partial_credit: Optional[bool] = None
    max_score: Optional[int] = None


class MediaAsset(BaseModel):
    """Media asset definition for rich game visuals."""
    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["image", "gif", "video", "sprite", "css_animation"]
    url: Optional[str] = None
    generationPrompt: Optional[str] = None
    placement: Literal["background", "overlay", "zone", "decoration"] = "overlay"
    zoneId: Optional[str] = None  # For zone-specific assets
    layer: int = Field(default=0, ge=-10, le=10)  # Z-index ordering


class InteractiveOverlayZone(BaseModel):
    """Zone specification for interactive overlay rendering."""
    model_config = ConfigDict(extra="forbid")

    id: str
    shape: Literal["circle", "polygon", "rect"] = "circle"
    coordinates: Dict[str, float]  # x, y, radius for circle; points for polygon
    interactions: Dict[str, str] = Field(default_factory=dict)  # onClick, onDrop, onHover handlers
    styles: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # default, hover, correct, incorrect CSS


class InteractiveOverlaySpec(BaseModel):
    """Specification for rendering interactive overlays on diagram images."""
    model_config = ConfigDict(extra="forbid")

    canvas: Dict[str, int]  # width, height
    zones: List[InteractiveOverlayZone]
    animations: List[Dict[str, Any]] = Field(default_factory=list)  # CSS keyframe definitions


# =============================================================================
# TEMPORAL CONSTRAINT SCHEMAS (Petri Net-inspired)
# =============================================================================

TemporalConstraintType = Literal[
    "before",      # zone_a must be completed before zone_b appears
    "after",       # zone_a appears after zone_b is completed
    "mutex",       # zone_a and zone_b cannot be visible simultaneously
    "concurrent",  # zone_a and zone_b can appear together (same hierarchy)
    "sequence",    # zone_a → zone_b in strict order (for motion paths)
]


class TemporalConstraint(BaseModel):
    """
    A constraint between two zones defining their temporal relationship.

    Used to prevent visual clutter by ensuring overlapping zones from
    different hierarchies never appear at the same time.

    Priority levels:
    - 100: Scene boundaries (zones in different scenes)
    - 50:  Hierarchy rules (parent-child always concurrent)
    - 10:  Spatial overlap (mutex for different-hierarchy overlaps)
    - 1:   Pedagogical hints (from agent, lowest priority)
    """
    model_config = ConfigDict(extra="forbid")

    zone_a: str = Field(description="First zone ID in the constraint")
    zone_b: str = Field(description="Second zone ID in the constraint")
    constraint_type: TemporalConstraintType = Field(
        description="Type of temporal relationship between zones"
    )
    reason: str = Field(
        description="Why this constraint exists (e.g., 'spatial_overlap_different_hierarchy')"
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Higher priority constraints take precedence"
    )


class MotionKeyframe(BaseModel):
    """
    A keyframe in a motion path animation.

    Supports position, scale, rotation, and opacity changes over time.
    All position values are in percentage (0-100) relative to container.
    """
    model_config = ConfigDict(extra="forbid")

    time_ms: int = Field(ge=0, description="Time offset in milliseconds")
    x: Optional[float] = Field(default=None, ge=0, le=100, description="X position (0-100%)")
    y: Optional[float] = Field(default=None, ge=0, le=100, description="Y position (0-100%)")
    scale: Optional[float] = Field(default=1.0, ge=0.1, le=5.0, description="Scale factor")
    rotation: Optional[float] = Field(default=0.0, ge=-360, le=360, description="Rotation in degrees")
    opacity: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Opacity (0-1)")
    # Extended properties
    backgroundColor: Optional[str] = Field(default=None, description="CSS background color")
    transform: Optional[str] = Field(default=None, description="Additional CSS transform")


MotionTrigger = Literal[
    "on_reveal",        # When zone becomes visible
    "on_complete",      # When zone is correctly labeled
    "on_hover",         # When user hovers over zone
    "on_scene_enter",   # When entering a new scene
    "on_incorrect",     # When incorrect placement attempt
]


class MotionPath(BaseModel):
    """
    Motion/animation path for an asset.

    Defines keyframe-based animations that can be triggered by game events.
    Uses Web Animations API compatible format for smooth playback.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(description="ID of the asset/zone to animate")
    keyframes: List[MotionKeyframe] = Field(
        min_length=1,
        description="List of keyframes defining the motion"
    )
    easing: str = Field(
        default="ease-in-out",
        description="CSS easing function (linear, ease-in-out, spring, etc.)"
    )
    trigger: MotionTrigger = Field(
        default="on_reveal",
        description="Event that triggers this animation"
    )
    # Optional metadata
    stagger_delay_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Delay between each element when animating multiple"
    )
    loop: Optional[bool] = Field(default=False, description="Whether animation should loop")


class TemporalState(BaseModel):
    """
    Current state of zone visibility based on temporal constraints.

    Used by the frontend TemporalController to track game progress.
    """
    model_config = ConfigDict(extra="forbid")

    active_zones: List[str] = Field(
        default_factory=list,
        description="Currently visible zones"
    )
    completed_zones: List[str] = Field(
        default_factory=list,
        description="Correctly labeled zones"
    )
    blocked_zones: List[str] = Field(
        default_factory=list,
        description="Zones blocked by mutex constraints"
    )
    pending_zones: List[str] = Field(
        default_factory=list,
        description="Zones waiting for prerequisites"
    )


# =============================================================================
# ACCESSIBILITY SCHEMAS (WCAG 2.2 Level AA)
# =============================================================================

class AccessibilitySpec(BaseModel):
    """
    Accessibility specification for a zone.

    Provides WCAG 2.2 Level AA compliance information for screen readers,
    keyboard navigation, and assistive technologies.
    """
    model_config = ConfigDict(extra="forbid")

    zone_id: str = Field(description="ID of the zone this spec applies to")
    alt_text: str = Field(description="Alternative text for screen readers")
    screen_reader_hint: Optional[str] = Field(
        default=None,
        description="Additional hint for screen reader users"
    )
    keyboard_shortcut: Optional[str] = Field(
        default=None,
        description="Keyboard shortcut to focus this zone (e.g., 'Alt+1')"
    )
    aria_label: Optional[str] = Field(
        default=None,
        description="ARIA label override"
    )
    pronunciation_guide: Optional[str] = Field(
        default=None,
        description="Phonetic pronunciation for screen readers"
    )


class EventTrackingConfig(BaseModel):
    """
    Configuration for event sourcing and analytics tracking.

    Enables comprehensive logging of game events for learning analytics.
    """
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable event recording")
    event_types: List[str] = Field(
        default_factory=lambda: [
            "label_placed", "label_removed", "hint_requested",
            "zone_revealed", "scene_completed", "undo_action", "redo_action"
        ],
        description="Event types to track"
    )
    include_timestamps: bool = Field(default=True, description="Include timestamps in events")
    include_coordinates: bool = Field(default=False, description="Track mouse/touch coordinates")


class UndoRedoConfig(BaseModel):
    """
    Configuration for undo/redo functionality using Command Pattern.
    """
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable undo/redo")
    max_undo_depth: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of actions that can be undone"
    )
    keyboard_shortcuts: bool = Field(
        default=True,
        description="Enable Ctrl+Z/Ctrl+Y keyboard shortcuts"
    )


class InteractiveDiagramDiagram(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assetPrompt: str
    assetUrl: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    zones: List[InteractiveDiagramZone]
    # NEW: Interactive overlay spec for rich interactions
    overlaySpec: Optional[InteractiveOverlaySpec] = None


class InteractiveDiagramBlueprint(BaseModel):
    """
    Enhanced INTERACTIVE_DIAGRAM blueprint with support for multiple interaction modes,
    structured animations, hierarchical zones, and media assets.

    V4 DSL: All per-mechanic config fields mirror frontend types.ts exactly.
    """
    model_config = ConfigDict(extra="allow")

    templateType: Literal["INTERACTIVE_DIAGRAM"]
    title: str
    narrativeIntro: str
    diagram: InteractiveDiagramDiagram
    labels: List[InteractiveDiagramLabel]
    distractorLabels: Optional[List[Dict[str, Any]]] = None
    tasks: List[InteractiveDiagramTask]

    # Animation cues (legacy text-based format)
    animationCues: InteractiveDiagramAnimationCues

    # NEW: Structured animations (preferred over text-based)
    animations: Optional[StructuredAnimations] = None

    # Interaction mode — required from pipeline, no implicit default
    interactionMode: InteractionMode

    # NEW: Hierarchical zone groups
    zoneGroups: Optional[List[ZoneGroup]] = None

    # NEW: Click-to-identify prompts (for click_to_identify mode)
    identificationPrompts: Optional[List[IdentificationPrompt]] = None
    selectionMode: Literal["sequential", "any_order"] = "any_order"

    # NEW: Path definitions (for trace_path mode)
    paths: Optional[List[TracePath]] = None

    # NEW: Media assets
    mediaAssets: Optional[List[MediaAsset]] = None

    # NEW: Temporal intelligence (Petri Net-inspired constraints)
    temporalConstraints: Optional[List[TemporalConstraint]] = None
    motionPaths: Optional[List[MotionPath]] = None
    revealOrder: Optional[List[str]] = None  # Suggested zone reveal order

    # NEW: Event tracking for analytics (Phase 2)
    eventTracking: Optional[EventTrackingConfig] = None

    # NEW: Undo/Redo configuration (Phase 2)
    undoRedo: Optional[UndoRedoConfig] = None

    # NEW: Accessibility specifications (Phase 3 - WCAG 2.2 Level AA)
    accessibilitySpecs: Optional[List[AccessibilitySpec]] = None
    keyboardControls: Optional[Dict[str, str]] = None  # key → action mapping
    focusOrder: Optional[List[str]] = None  # Tab order for zones

    # Game mechanics — flat list, first entry is the starting mode.
    mechanics: Optional[List[Mechanic]] = None
    modeTransitions: Optional[List[BlueprintModeTransition]] = None

    # Scoring configuration
    scoringStrategy: Optional[ScoringStrategy] = None

    # Existing optional fields
    hints: Optional[List[InteractiveDiagramHint]] = None
    feedbackMessages: Optional[InteractiveDiagramFeedbackMessages] = None

    # Per-mechanic configurations (V4 DSL — mirrors frontend types.ts)
    sequenceConfig: Optional[SequenceConfig] = None
    sortingConfig: Optional[SortingConfig] = None
    memoryMatchConfig: Optional[MemoryMatchConfig] = None
    branchingConfig: Optional[BranchingConfig] = None
    compareConfig: Optional[CompareConfig] = None
    descriptionMatchingConfig: Optional[DescriptionMatchingConfig] = None
    clickToIdentifyConfig: Optional[ClickToIdentifyConfig] = None
    tracePathConfig: Optional[TracePathConfig] = None
    dragDropConfig: Optional[DragDropConfig] = None

    # Leader line anchors for drag_drop
    leaderLineAnchors: Optional[List[LeaderLineAnchor]] = None

    # Timed challenge configuration
    timedChallengeWrappedMode: Optional[InteractionMode] = None
    timeLimitSeconds: Optional[int] = None


# =============================================================================
# MULTI-SCENE GAME SCHEMAS (Preset 2)
# =============================================================================

class GameScene(BaseModel):
    """
    Single scene in a multi-scene game (Preset 2).

    Each scene has its own diagram, zones, and labels, allowing for
    zoom-in progressions, depth-first exploration, or linear sequences.
    """
    model_config = ConfigDict(extra="forbid")

    scene_id: str
    scene_number: int = Field(ge=1, le=10)
    title: str
    narrative_intro: str

    # Scene content
    diagram: InteractiveDiagramDiagram
    zones: List[InteractiveDiagramZone]
    labels: List[InteractiveDiagramLabel]

    # Interaction configuration
    interaction_mode: InteractionMode = "drag_drop"
    max_score: int = Field(default=100, ge=10, le=1000)

    # Scene relationships
    prerequisite_scene: Optional[str] = None  # scene_id of prerequisite
    child_scenes: Optional[List[str]] = None  # scene_ids that can be unlocked
    reveal_trigger: Literal[
        "all_correct", "percentage", "specific_zones", "manual"
    ] = "all_correct"
    reveal_threshold: Optional[float] = None  # For percentage trigger

    # Scene-specific settings
    time_limit_seconds: Optional[int] = None  # For timed_challenge mode
    hints_enabled: bool = True
    feedback_enabled: bool = True


class GameSequence(BaseModel):
    """
    Multi-scene game container (Preset 2).

    Wraps multiple GameScene objects into a coherent sequence with
    progression tracking and overall scoring.
    """
    model_config = ConfigDict(extra="forbid")

    sequence_id: str
    sequence_title: str
    sequence_description: Optional[str] = None

    # Scene configuration
    total_scenes: int = Field(ge=1, le=10)
    scenes: List[GameScene]
    progression_type: Literal["linear", "zoom_in", "depth_first", "branching"] = "linear"

    # Scoring
    total_max_score: int = Field(ge=10)
    passing_score: Optional[int] = None
    bonus_for_no_hints: bool = True

    # Progression rules
    require_completion: bool = True  # Must complete all scenes
    allow_scene_skip: bool = False
    allow_revisit: bool = True

    # Metadata
    estimated_duration_minutes: Optional[int] = None
    difficulty_level: Literal["beginner", "intermediate", "advanced"] = "intermediate"


class MultiSceneInteractiveDiagramBlueprint(BaseModel):
    """
    Extended INTERACTIVE_DIAGRAM blueprint with multi-scene support (Preset 2).

    This extends the base InteractiveDiagramBlueprint with support for
    multiple scenes, each with its own diagram and zones.
    """
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["INTERACTIVE_DIAGRAM"]
    title: str
    narrativeIntro: str

    # Multi-scene mode flag
    is_multi_scene: bool = True

    # Game sequence (contains all scenes)
    game_sequence: GameSequence

    # Shared settings across all scenes
    animationCues: InteractiveDiagramAnimationCues
    animations: Optional[StructuredAnimations] = None
    feedbackMessages: Optional[InteractiveDiagramFeedbackMessages] = None

    # Global hints (scene-specific hints are in each GameScene)
    global_hints: Optional[List[InteractiveDiagramHint]] = None

    # Media assets shared across scenes
    mediaAssets: Optional[List[MediaAsset]] = None

    # Temporal intelligence (Petri Net-inspired constraints)
    temporalConstraints: Optional[List[TemporalConstraint]] = None
    motionPaths: Optional[List[MotionPath]] = None

    # NEW: Event tracking for analytics (Phase 2)
    eventTracking: Optional[EventTrackingConfig] = None

    # NEW: Undo/Redo configuration (Phase 2)
    undoRedo: Optional[UndoRedoConfig] = None

    # NEW: Accessibility specifications (Phase 3 - WCAG 2.2 Level AA)
    accessibilitySpecs: Optional[List[AccessibilitySpec]] = None
    keyboardControls: Optional[Dict[str, str]] = None
    focusOrder: Optional[List[str]] = None


class DiagramSpecCanvas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int
    height: int


class DiagramSpecBackground(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: Literal["grid", "plain"]
    primary: str
    secondary: str


class DiagramSpecLegendItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    color: str


class DiagramSpecLegend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    items: List[DiagramSpecLegendItem]


class DiagramSpecZone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    radius: float = Field(ge=1, le=50)
    color: str
    markerShape: Literal["circle", "square", "pin"] = "circle"


class DiagramSpecDecoration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text", "shape", "path"]
    props: Dict[str, Any]


class DiagramSvgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canvas: DiagramSpecCanvas
    background: DiagramSpecBackground
    showLabels: bool = False
    legend: DiagramSpecLegend
    zones: List[DiagramSpecZone]
    decorations: List[DiagramSpecDecoration]


def get_interactive_diagram_blueprint_schema() -> Dict[str, Any]:
    return InteractiveDiagramBlueprint.model_json_schema()


def get_diagram_svg_spec_schema() -> Dict[str, Any]:
    return DiagramSvgSpec.model_json_schema()


# =============================================================================
# STANDARDIZED FORMAT NORMALIZERS
# =============================================================================
# Use these functions to convert any label/zone format to the canonical format.
# This prevents mismatches between agents that produce different formats.

import re
import logging

_normalizer_logger = logging.getLogger("gamed_ai.schemas.interactive_diagram")


def _slugify(value: str) -> str:
    """Convert a string to a URL-safe slug."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def normalize_label(
    label: Union[str, Dict[str, Any]],
    index: int = 0,
    zones: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Normalize any label format to the canonical InteractiveDiagramLabel format.

    Accepts:
    - str: "Petal" → {"id": "label_petal", "text": "Petal", "correctZoneId": "zone_petal"}
    - dict with 'text': {"text": "Petal"} → adds id and correctZoneId
    - dict with 'label': {"label": "Petal"} → converts to text field
    - dict with 'name': {"name": "Petal"} → converts to text field
    - Full dict: passes through with validation

    Args:
        label: The label in any format
        index: Index for generating unique IDs if needed
        zones: Optional list of zones to match correctZoneId

    Returns:
        Normalized label dict with id, text, correctZoneId
    """
    if isinstance(label, str):
        text = label.strip()
        slug = _slugify(text) or f"label_{index}"
        zone_id = _find_matching_zone_id(text, zones) or f"zone_{slug}"
        return {
            "id": f"label_{slug}",
            "text": text,
            "correctZoneId": zone_id
        }

    if not isinstance(label, dict):
        _normalizer_logger.warning(f"Invalid label type: {type(label)}, using fallback")
        return {
            "id": f"label_{index}",
            "text": f"Label {index + 1}",
            "correctZoneId": f"zone_{index}"
        }

    # Extract text from various possible keys
    text = (
        label.get("text") or
        label.get("label") or
        label.get("name") or
        label.get("value") or
        ""
    ).strip()

    if not text:
        text = f"Label {index + 1}"

    slug = _slugify(text) or f"label_{index}"

    # Get or generate ID
    label_id = label.get("id") or label.get("labelId") or f"label_{slug}"

    # Get or find correctZoneId
    zone_id = (
        label.get("correctZoneId") or
        label.get("zoneId") or
        label.get("zone_id") or
        _find_matching_zone_id(text, zones) or
        f"zone_{slug}"
    )

    return {
        "id": label_id,
        "text": text,
        "correctZoneId": zone_id
    }


def normalize_zone(
    zone: Union[str, Dict[str, Any]],
    index: int = 0,
    default_positions: Optional[List[tuple]] = None
) -> Dict[str, Any]:
    """
    Normalize any zone format to the canonical InteractiveDiagramZone format.

    Accepts:
    - str: "Petal" → {"id": "zone_petal", "label": "Petal", "x": ..., "y": ..., "radius": 10}
    - dict with various formats

    Args:
        zone: The zone in any format
        index: Index for positioning and ID generation
        default_positions: List of (x, y) tuples for positioning

    Returns:
        Normalized zone dict
    """
    # Default position if not provided
    if default_positions and index < len(default_positions):
        default_x, default_y = default_positions[index]
    else:
        # Grid layout fallback
        cols = 4
        default_x = ((index % cols) + 1) * (100 / (cols + 1))
        default_y = ((index // cols) + 1) * 25

    if isinstance(zone, str):
        text = zone.strip()
        slug = _slugify(text) or f"zone_{index}"
        return {
            "id": f"zone_{slug}",
            "label": text,
            "x": round(default_x, 1),
            "y": round(default_y, 1),
            "radius": 10
        }

    if not isinstance(zone, dict):
        _normalizer_logger.warning(f"Invalid zone type: {type(zone)}, using fallback")
        return {
            "id": f"zone_{index}",
            "label": f"Zone {index + 1}",
            "x": round(default_x, 1),
            "y": round(default_y, 1),
            "radius": 10
        }

    # Extract label from various possible keys
    label = (
        zone.get("label") or
        zone.get("text") or
        zone.get("name") or
        ""
    ).strip()

    if not label:
        label = f"Zone {index + 1}"

    slug = _slugify(label) or f"zone_{index}"

    # Get or generate ID
    zone_id = zone.get("id") or zone.get("zoneId") or f"zone_{slug}"

    # Get coordinates with fallbacks
    x = zone.get("x")
    y = zone.get("y")

    # Handle various coordinate formats
    if x is None and "center_x" in zone:
        x = zone["center_x"]
    if y is None and "center_y" in zone:
        y = zone["center_y"]
    if x is None and "cx" in zone:
        x = zone["cx"]
    if y is None and "cy" in zone:
        y = zone["cy"]

    # Convert to float and clamp to 0-100
    try:
        x = float(x) if x is not None else default_x
        y = float(y) if y is not None else default_y
        x = max(0, min(100, x))
        y = max(0, min(100, y))
    except (ValueError, TypeError):
        x, y = default_x, default_y

    # Get radius
    radius = zone.get("radius") or zone.get("r") or 10
    try:
        radius = float(radius)
        radius = max(1, min(50, radius))
    except (ValueError, TypeError):
        radius = 10

    # Determine shape type
    shape = zone.get("shape", "circle")
    if shape not in ["circle", "polygon", "rect"]:
        shape = "circle"

    result = {
        "id": zone_id,
        "label": label,
        "shape": shape,
    }

    # Handle polygon zones (Preset 2)
    if shape == "polygon" and zone.get("points"):
        points = zone.get("points", [])
        # Validate and normalize points
        if isinstance(points, list) and len(points) >= 3:
            normalized_points = []
            for point in points:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    px = max(0, min(100, float(point[0])))
                    py = max(0, min(100, float(point[1])))
                    normalized_points.append([round(px, 1), round(py, 1)])
            result["points"] = normalized_points

            # Calculate center from polygon points
            if normalized_points:
                center_x = sum(p[0] for p in normalized_points) / len(normalized_points)
                center_y = sum(p[1] for p in normalized_points) / len(normalized_points)
                result["center"] = {"x": round(center_x, 1), "y": round(center_y, 1)}
                # Also set x, y for compatibility
                result["x"] = round(center_x, 1)
                result["y"] = round(center_y, 1)
        else:
            # Invalid polygon, fall back to circle
            result["shape"] = "circle"
            result["x"] = round(x, 1)
            result["y"] = round(y, 1)
            result["radius"] = round(radius, 1)
    else:
        # Circle or rect shape
        result["x"] = round(x, 1)
        result["y"] = round(y, 1)
        result["radius"] = round(radius, 1)

    # Handle center point if provided
    if zone.get("center"):
        center = zone.get("center")
        if isinstance(center, dict):
            result["center"] = {
                "x": round(float(center.get("x", x)), 1),
                "y": round(float(center.get("y", y)), 1)
            }

    # Preserve optional fields
    if zone.get("description"):
        result["description"] = zone["description"]
    if zone.get("parentZoneId"):
        result["parentZoneId"] = zone["parentZoneId"]

    # Preset 2: Unlimited hierarchy support
    if zone.get("hierarchyLevel"):
        result["hierarchyLevel"] = max(1, int(zone.get("hierarchyLevel", 1)))
    if zone.get("childZoneIds"):
        result["childZoneIds"] = zone.get("childZoneIds")

    # Preset 2: Additional metadata
    if zone.get("hint"):
        result["hint"] = zone["hint"]
    if zone.get("difficulty"):
        result["difficulty"] = max(1, min(5, int(zone.get("difficulty", 1))))
    if zone.get("diagramType"):
        result["diagramType"] = zone["diagramType"]
    if zone.get("metadata"):
        result["metadata"] = zone["metadata"]

    return result


def normalize_labels(
    labels: List[Any],
    zones: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Normalize a list of labels to canonical format.

    Args:
        labels: List of labels in any format
        zones: Optional zones to match correctZoneId

    Returns:
        List of normalized label dicts
    """
    if not labels:
        return []

    normalized = []
    seen_ids = set()

    for i, label in enumerate(labels):
        norm = normalize_label(label, i, zones)

        # Ensure unique IDs
        base_id = norm["id"]
        unique_id = base_id
        suffix = 1
        while unique_id in seen_ids:
            unique_id = f"{base_id}_{suffix}"
            suffix += 1
        norm["id"] = unique_id
        seen_ids.add(unique_id)

        normalized.append(norm)

    return normalized


def normalize_zones(
    zones: List[Any],
    default_positions: Optional[List[tuple]] = None
) -> List[Dict[str, Any]]:
    """
    Normalize a list of zones to canonical format.

    Args:
        zones: List of zones in any format
        default_positions: Optional list of (x, y) positions

    Returns:
        List of normalized zone dicts
    """
    if not zones:
        return []

    normalized = []
    seen_ids = set()

    for i, zone in enumerate(zones):
        norm = normalize_zone(zone, i, default_positions)

        # Ensure unique IDs
        base_id = norm["id"]
        unique_id = base_id
        suffix = 1
        while unique_id in seen_ids:
            unique_id = f"{base_id}_{suffix}"
            suffix += 1
        norm["id"] = unique_id
        seen_ids.add(unique_id)

        normalized.append(norm)

    return normalized


def _find_matching_zone_id(
    label_text: str,
    zones: Optional[List[Dict[str, Any]]]
) -> Optional[str]:
    """Find a zone ID that matches the label text."""
    if not zones or not label_text:
        return None

    label_lower = label_text.strip().lower()
    label_slug = _slugify(label_text)

    for zone in zones:
        if not isinstance(zone, dict):
            continue

        zone_label = (zone.get("label") or "").strip().lower()
        zone_id = zone.get("id") or ""

        # Exact match
        if zone_label == label_lower:
            return zone_id

        # Slug match
        if _slugify(zone_label) == label_slug:
            return zone_id

        # ID contains label slug
        if label_slug and label_slug in zone_id.lower():
            return zone_id

    return None


def create_labels_from_zones(zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create a matching set of labels from zones.
    Useful when zones are detected but labels need to be generated.

    Args:
        zones: List of normalized zone dicts

    Returns:
        List of label dicts that match the zones
    """
    labels = []
    for zone in zones:
        if not isinstance(zone, dict):
            continue

        zone_id = zone.get("id", "")
        zone_label = zone.get("label", "")

        if not zone_label:
            continue

        slug = _slugify(zone_label)
        labels.append({
            "id": f"label_{slug}",
            "text": zone_label,
            "correctZoneId": zone_id
        })

    return labels
