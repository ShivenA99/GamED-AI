"""
Comprehensive Pydantic schemas for all game template blueprints.

Provides strict validation for each template type with:
- Required field enforcement
- Value range constraints
- Cross-reference validation (e.g., label-zone consistency)
- ID uniqueness checks

Usage:
    from app.agents.schemas.blueprint_schemas import (
        validate_blueprint,
        SequenceBuilderBlueprint,
        BucketSortBlueprint,
        ...
    )

    # Validate any blueprint
    result = validate_blueprint(blueprint_dict)
    if not result["valid"]:
        print(result["errors"])
"""

from typing import List, Optional, Literal, Dict, Any, Union, Tuple
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
import re


# =============================================================================
# BASE CLASSES
# =============================================================================

class BaseTask(BaseModel):
    """Base task model shared across templates"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    questionText: str = Field(min_length=1)
    requiredToProceed: bool = True


class BaseAnimationCues(BaseModel):
    """Base animation cues - templates extend this"""
    model_config = ConfigDict(extra="allow")  # Allow extra cues


# =============================================================================
# SEQUENCE_BUILDER SCHEMA
# =============================================================================

class SequenceStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    orderIndex: int = Field(ge=1)
    description: Optional[str] = None


class SequenceDistractor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    description: Optional[str] = None


class SequenceBuilderTask(BaseTask):
    type: Literal["sequence_order"] = "sequence_order"


class SequenceBuilderAnimationCues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stepDrag: str = Field(min_length=1)
    correctPlacement: str = Field(min_length=1)
    incorrectPlacement: str = Field(min_length=1)
    sequenceComplete: Optional[str] = None


class SequenceBuilderBlueprint(BaseModel):
    """SEQUENCE_BUILDER template: Arrange items in correct order"""
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["SEQUENCE_BUILDER"]
    title: str = Field(min_length=1)
    narrativeIntro: str = Field(min_length=1)
    steps: List[SequenceStep] = Field(min_length=2)
    distractors: Optional[List[SequenceDistractor]] = None
    tasks: List[SequenceBuilderTask] = Field(min_length=1)
    animationCues: SequenceBuilderAnimationCues

    @model_validator(mode="after")
    def validate_unique_order_indices(self):
        """Ensure no duplicate orderIndex values"""
        indices = [s.orderIndex for s in self.steps]
        if len(indices) != len(set(indices)):
            raise ValueError("Duplicate orderIndex values in steps. Each step must have a unique orderIndex.")
        return self

    @model_validator(mode="after")
    def validate_unique_step_ids(self):
        """Ensure no duplicate step IDs"""
        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate step IDs detected. Each step must have a unique ID.")
        return self


# =============================================================================
# BUCKET_SORT SCHEMA
# =============================================================================

class Bucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: Optional[str] = None


class BucketItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    correctBucketId: str = Field(min_length=1)
    description: Optional[str] = None


class BucketSortTask(BaseTask):
    type: Literal["bucket_sort"] = "bucket_sort"


class BucketSortAnimationCues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itemDrag: str = Field(min_length=1)
    correctDrop: str = Field(min_length=1)
    incorrectDrop: str = Field(min_length=1)
    bucketFull: Optional[str] = None


class BucketSortBlueprint(BaseModel):
    """BUCKET_SORT template: Sort items into correct categories"""
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["BUCKET_SORT"]
    title: str = Field(min_length=1)
    narrativeIntro: str = Field(min_length=1)
    buckets: List[Bucket] = Field(min_length=2)
    items: List[BucketItem] = Field(min_length=2)
    tasks: List[BucketSortTask] = Field(min_length=1)
    animationCues: BucketSortAnimationCues

    @model_validator(mode="after")
    def validate_item_bucket_references(self):
        """Ensure all items reference valid bucket IDs"""
        bucket_ids = {b.id for b in self.buckets}
        for item in self.items:
            if item.correctBucketId not in bucket_ids:
                raise ValueError(
                    f"Item '{item.id}' references invalid bucket '{item.correctBucketId}'. "
                    f"Valid buckets: {list(bucket_ids)}"
                )
        return self

    @model_validator(mode="after")
    def validate_unique_ids(self):
        """Ensure unique IDs for buckets and items"""
        bucket_ids = [b.id for b in self.buckets]
        item_ids = [i.id for i in self.items]

        if len(bucket_ids) != len(set(bucket_ids)):
            raise ValueError("Duplicate bucket IDs detected")
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Duplicate item IDs detected")
        return self


# =============================================================================
# PARAMETER_PLAYGROUND SCHEMA
# =============================================================================

class Parameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: Literal["slider", "input", "dropdown"]
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    defaultValue: Union[float, str]
    unit: Optional[str] = None
    options: Optional[List[str]] = None  # For dropdown type


class Visualization(BaseModel):
    model_config = ConfigDict(extra="allow")  # Allow template-specific fields

    type: Literal["chart", "graph", "diagram", "simulation"]
    description: Optional[str] = None


class ParameterPlaygroundTask(BaseTask):
    type: Literal["parameter_adjustment", "prediction"] = "parameter_adjustment"
    targetValues: Optional[Dict[str, Union[float, str]]] = None


class ParameterPlaygroundAnimationCues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameterChange: str = Field(min_length=1)
    visualizationUpdate: str = Field(min_length=1)
    targetReached: Optional[str] = None


class ParameterPlaygroundBlueprint(BaseModel):
    """PARAMETER_PLAYGROUND template: Adjust parameters to observe effects"""
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["PARAMETER_PLAYGROUND"]
    title: str = Field(min_length=1)
    narrativeIntro: str = Field(min_length=1)
    parameters: List[Parameter] = Field(min_length=1)
    visualization: Visualization
    tasks: List[ParameterPlaygroundTask] = Field(min_length=1)
    animationCues: ParameterPlaygroundAnimationCues

    @model_validator(mode="after")
    def validate_slider_ranges(self):
        """Ensure sliders have valid min/max"""
        for param in self.parameters:
            if param.type == "slider":
                if param.min is None or param.max is None:
                    raise ValueError(f"Slider parameter '{param.id}' must have min and max values")
                if param.min >= param.max:
                    raise ValueError(f"Slider parameter '{param.id}' min must be less than max")
        return self


# =============================================================================
# TIMELINE_ORDER SCHEMA
# =============================================================================

class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    timestamp: float
    description: Optional[str] = None


class Timeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    startTime: float
    endTime: float
    unit: Optional[str] = None


class TimelineOrderTask(BaseTask):
    type: Literal["timeline_order"] = "timeline_order"


class TimelineOrderAnimationCues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventPlacement: str = Field(min_length=1)
    correctOrder: str = Field(min_length=1)
    incorrectOrder: str = Field(min_length=1)


class TimelineOrderBlueprint(BaseModel):
    """TIMELINE_ORDER template: Place events in chronological order"""
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["TIMELINE_ORDER"]
    title: str = Field(min_length=1)
    narrativeIntro: str = Field(min_length=1)
    events: List[TimelineEvent] = Field(min_length=2)
    timeline: Timeline
    tasks: List[TimelineOrderTask] = Field(min_length=1)
    animationCues: TimelineOrderAnimationCues

    @model_validator(mode="after")
    def validate_event_timestamps(self):
        """Ensure events have valid timestamps within timeline range"""
        for event in self.events:
            if not (self.timeline.startTime <= event.timestamp <= self.timeline.endTime):
                raise ValueError(
                    f"Event '{event.id}' timestamp {event.timestamp} outside timeline range "
                    f"[{self.timeline.startTime}, {self.timeline.endTime}]"
                )
        return self


# =============================================================================
# MATCH_PAIRS SCHEMA
# =============================================================================

class MatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class MatchPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    leftItem: MatchItem
    rightItem: MatchItem


class MatchPairsTask(BaseTask):
    type: Literal["match_pairs"] = "match_pairs"


class MatchPairsAnimationCues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cardFlip: str = Field(min_length=1)
    cardMatch: str = Field(min_length=1)
    cardMismatch: str = Field(min_length=1)
    allMatched: Optional[str] = None


class MatchPairsBlueprint(BaseModel):
    """MATCH_PAIRS template: Match related items"""
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["MATCH_PAIRS"]
    title: str = Field(min_length=1)
    narrativeIntro: str = Field(min_length=1)
    pairs: List[MatchPair] = Field(min_length=2)
    tasks: List[MatchPairsTask] = Field(min_length=1)
    animationCues: MatchPairsAnimationCues

    @model_validator(mode="after")
    def validate_unique_ids(self):
        """Ensure unique IDs"""
        pair_ids = [p.id for p in self.pairs]
        left_ids = [p.leftItem.id for p in self.pairs]
        right_ids = [p.rightItem.id for p in self.pairs]

        if len(pair_ids) != len(set(pair_ids)):
            raise ValueError("Duplicate pair IDs detected")
        if len(left_ids) != len(set(left_ids)):
            raise ValueError("Duplicate left item IDs detected")
        if len(right_ids) != len(set(right_ids)):
            raise ValueError("Duplicate right item IDs detected")
        return self


# =============================================================================
# STATE_TRACER_CODE SCHEMA
# =============================================================================

class CodeStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    description: str = Field(min_length=1)
    expectedVariables: Dict[str, Any]
    highlightLine: Optional[int] = None


class StateTracerTask(BaseTask):
    type: Literal["variable_value", "step_analysis"] = "variable_value"
    stepIndex: Optional[int] = None
    variableName: Optional[str] = None
    correctAnswer: str


class StateTracerAnimationCues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lineHighlight: str = Field(min_length=1)
    variableUpdate: str = Field(min_length=1)
    stepComplete: str = Field(min_length=1)


class StateTracerCodeBlueprint(BaseModel):
    """STATE_TRACER_CODE template: Trace code execution and variable states"""
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["STATE_TRACER_CODE"]
    title: str = Field(min_length=1)
    narrativeIntro: str = Field(min_length=1)
    code: str = Field(min_length=1)
    initialInput: Optional[Any] = None
    steps: List[CodeStep] = Field(min_length=1)
    tasks: List[StateTracerTask] = Field(min_length=1)
    animationCues: StateTracerAnimationCues

    @model_validator(mode="after")
    def validate_step_indices(self):
        """Ensure step indices are sequential and unique"""
        indices = [s.index for s in self.steps]
        if len(indices) != len(set(indices)):
            raise ValueError("Duplicate step indices detected")
        if sorted(indices) != list(range(len(indices))):
            raise ValueError("Step indices must be sequential starting from 0")
        return self

    @model_validator(mode="after")
    def validate_task_references(self):
        """Ensure tasks reference valid step indices"""
        max_step = len(self.steps) - 1
        for task in self.tasks:
            if task.stepIndex is not None and task.stepIndex > max_step:
                raise ValueError(f"Task references invalid step index {task.stepIndex}")
        return self


# =============================================================================
# MULTI-SCENE / HETEROGENEOUS GAME SUPPORT
# =============================================================================

class SceneDiagram(BaseModel):
    """Diagram configuration for a scene."""
    model_config = ConfigDict(extra="allow")

    imageUrl: Optional[str] = None
    svgContent: Optional[str] = None
    alt_text: Optional[str] = None


class SceneZone(BaseModel):
    """Zone definition for a scene (supports heterogeneous zones per scene)."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    shape: Literal["circle", "polygon", "rectangle"] = "circle"
    coordinates: Optional[Dict[str, Any]] = None
    description: Optional[str] = None  # For description_matching mode
    parent_zone_id: Optional[str] = None  # For hierarchical mode


class SceneLabel(BaseModel):
    """Label definition for a scene."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    description: Optional[str] = None


class BlueprintSceneTask(BaseModel):
    """A task (phase) within a scene. Maps game plan tasks to concrete zone/label IDs."""
    model_config = ConfigDict(extra="allow")

    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    mechanic_type: str = "drag_drop"
    zone_ids: List[str] = Field(default_factory=list)
    label_ids: List[str] = Field(default_factory=list)
    instructions: Optional[str] = None
    scoring_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    config: Optional[Dict[str, Any]] = None


class GameScene(BaseModel):
    """
    A single scene in a multi-scene game.

    Each scene is FULLY INDEPENDENT - it can have:
    - Different diagram/image
    - Different zones and labels
    - Different interaction mode
    - Different scoring
    """
    model_config = ConfigDict(extra="allow")

    scene_id: str = Field(min_length=1)
    scene_number: int = Field(ge=1)
    title: str = Field(min_length=1)

    # Scene-specific diagram (different per scene)
    diagram: Optional[SceneDiagram] = None

    # Scene-specific zones and labels (different per scene)
    zones: List[SceneZone] = Field(default_factory=list)
    labels: List[SceneLabel] = Field(default_factory=list)

    # Interaction mode (can be different per scene!)
    interaction_mode: str = Field(
        default="drag_drop",
        description="Interaction pattern for this scene"
    )

    # Scene-specific settings
    max_score: int = Field(default=100, ge=0)
    time_limit_seconds: Optional[int] = Field(default=None, ge=0)
    prerequisite_scene: Optional[str] = None

    # Optional scene narrative
    narrative_intro: Optional[str] = None
    instructions: Optional[str] = None

    # Scene-specific configuration for the interaction mode
    mode_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Mode-specific configuration (e.g., path_waypoints for trace_path)"
    )

    # Phase 0: Sequence configuration for order-based mechanics
    sequence_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Sequence configuration for order/sequence mechanics (correctOrder, items, etc.)"
    )

    # Tasks within this scene (phases using the same image but different zone subsets/mechanics)
    tasks: List[BlueprintSceneTask] = Field(default_factory=list)


class GameSequence(BaseModel):
    """
    A multi-scene game sequence.

    Supports heterogeneous scenes where each scene can have:
    - Different diagrams
    - Different zones/labels
    - Different interaction modes
    - Different scoring weights
    """
    model_config = ConfigDict(extra="allow")

    sequence_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: Optional[str] = None

    # Scenes in order
    scenes: List[GameScene] = Field(min_length=1)

    # Progression type
    progression_type: Literal["single", "linear", "zoom_in", "branching"] = "linear"

    # Total scoring
    total_max_score: int = Field(default=100, ge=0)

    # Completion requirements
    min_scenes_to_pass: Optional[int] = None
    pass_threshold: Optional[float] = Field(default=0.6, ge=0, le=1)

    @model_validator(mode="after")
    def validate_scene_numbers(self):
        """Ensure scene numbers are sequential."""
        numbers = [s.scene_number for s in self.scenes]
        expected = list(range(1, len(self.scenes) + 1))
        if sorted(numbers) != expected:
            raise ValueError(
                f"Scene numbers must be sequential starting from 1. "
                f"Got: {numbers}, expected: {expected}"
            )
        return self

    @model_validator(mode="after")
    def validate_unique_scene_ids(self):
        """Ensure unique scene IDs."""
        ids = [s.scene_id for s in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate scene_id values detected")
        return self

    @model_validator(mode="after")
    def validate_prerequisites(self):
        """Ensure prerequisite scenes exist."""
        scene_ids = {s.scene_id for s in self.scenes}
        for scene in self.scenes:
            if scene.prerequisite_scene and scene.prerequisite_scene not in scene_ids:
                raise ValueError(
                    f"Scene '{scene.scene_id}' references non-existent prerequisite "
                    f"'{scene.prerequisite_scene}'"
                )
        return self


# =============================================================================
# SEQUENCE CONFIG SCHEMAS (Phase 0: Multi-Mechanic Support)
# =============================================================================

class SequenceConfigItem(BaseModel):
    """
    A single item in a sequence configuration.

    Used for order-based game mechanics within INTERACTIVE_DIAGRAM.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Unique identifier for this item")
    text: str = Field(min_length=1, description="Display text for this item")
    description: Optional[str] = Field(default=None, description="Educational description")


class SequenceConfig(BaseModel):
    """
    Sequence configuration for order-based mechanics in INTERACTIVE_DIAGRAM games.

    Enables games that include both labeling AND sequencing mechanics,
    e.g., "Label the heart AND show the order of blood flow".
    """
    model_config = ConfigDict(extra="forbid")

    sequenceType: Literal["linear", "cyclic", "branching"] = Field(
        default="linear",
        description="Type of sequence: linear (A→B→C), cyclic (loop), branching (A→B or C)"
    )
    items: List[SequenceConfigItem] = Field(
        default_factory=list,
        description="Items available for sequencing"
    )
    correctOrder: List[str] = Field(
        default_factory=list,
        description="Ordered list of item IDs in the correct sequence"
    )
    allowPartialCredit: bool = Field(
        default=True,
        description="Whether to give partial credit for partially correct sequences"
    )
    instructionText: Optional[str] = Field(
        default=None,
        description="Instruction text for the sequencing task"
    )

    @model_validator(mode="after")
    def validate_correct_order_references(self):
        """Ensure correctOrder references valid item IDs."""
        item_ids = {item.id for item in self.items}
        for item_id in self.correctOrder:
            if item_id not in item_ids:
                raise ValueError(
                    f"correctOrder references invalid item ID '{item_id}'. "
                    f"Valid IDs: {list(item_ids)}"
                )
        return self


# Supported interaction modes for multi-scene games
SUPPORTED_INTERACTION_MODES = {
    "drag_drop": "Drag labels to correct zones",
    "hierarchical": "Progressive reveal with parent-child relationships",
    "click_to_identify": "Click zones when prompted",
    "trace_path": "Draw path through connected elements",
    "description_matching": "Match descriptions to zones",
    "sequencing": "Arrange elements in correct order",
    "compare_contrast": "Identify similarities and differences",
    "sorting_categories": "Sort items into categories",
    "timed_challenge": "Time-limited version of another mode",
}


# =============================================================================
# INTERACTIVE_DIAGRAM SCHEMA (v3 — asset graph powered)
# =============================================================================

class IDSceneAsset(BaseModel):
    """A generated asset within a scene."""
    model_config = ConfigDict(extra="allow")

    asset_id: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)  # diagram, background, sprite, overlay, etc.
    url: Optional[str] = None
    path: Optional[str] = None
    position: Optional[Dict[str, Any]] = None  # {x_percent, y_percent, z_index, anchor}
    dimensions: Optional[Dict[str, Any]] = None  # {width, height, aspect_ratio}
    style: Optional[Dict[str, Any]] = None  # {transparency, visual_tone, ...}
    game_logic: Optional[Dict[str, Any]] = None  # State machine for independent asset logic


class IDZone(BaseModel):
    """Zone within a scene for the interactive diagram."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    shape: Literal["circle", "polygon", "rectangle"] = "circle"
    coordinates: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    parent_zone_id: Optional[str] = None  # For hierarchical mode
    group_only: bool = False  # If true, no label — just a grouping container


class IDLabel(BaseModel):
    """Label within a scene."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    correct_zone_id: str = Field(min_length=1)
    is_distractor: bool = False
    explanation: Optional[str] = None  # Why this distractor is wrong
    canonical_name: Optional[str] = None  # Original zone name when text is a description


class IDMechanic(BaseModel):
    """A game mechanic within a scene."""
    model_config = ConfigDict(extra="allow")

    mechanic_id: str = Field(min_length=1)
    mechanic_type: str = Field(min_length=1)  # drag_drop, trace_path, click_to_identify, etc.
    interaction_mode: str = Field(min_length=1)
    config: Optional[Dict[str, Any]] = None  # Mechanic-specific configuration
    zone_labels: List[str] = Field(default_factory=list)  # Which zone labels this mechanic operates on
    scoring: Optional[Dict[str, Any]] = None  # max_score, points_per_correct, etc.
    feedback: Optional[Dict[str, Any]] = None  # on_correct, on_incorrect, misconception_feedback
    animations: Optional[Dict[str, Any]] = None  # on_correct, on_incorrect, on_hint, etc.


class IDMechanicTransition(BaseModel):
    """Transition between mechanics within a scene."""
    model_config = ConfigDict(extra="allow")

    from_mechanic: str = Field(min_length=1)
    to_mechanic: str = Field(min_length=1)
    trigger: str = Field(min_length=1)  # score_threshold, all_complete, manual
    trigger_value: Optional[Any] = None
    animation: str = "fade"
    message: Optional[str] = None


class IDScene(BaseModel):
    """A scene in the interactive diagram game."""
    model_config = ConfigDict(extra="allow")

    scene_id: str = Field(min_length=1)
    scene_number: int = Field(ge=1)
    title: str = Field(min_length=1)

    # Visual
    diagram_image_url: Optional[str] = None
    background_url: Optional[str] = None

    # Scene content
    zones: List[IDZone] = Field(default_factory=list)
    labels: List[IDLabel] = Field(default_factory=list)
    mechanics: List[IDMechanic] = Field(default_factory=list)
    mechanic_transitions: List[IDMechanicTransition] = Field(default_factory=list)

    # Scene-level assets (independent of zones)
    assets: List[IDSceneAsset] = Field(default_factory=list)

    # Scene-level sounds
    sounds: Optional[Dict[str, Any]] = None  # {background_music, correct_sound, etc.}

    # Scene metadata
    max_score: int = Field(default=100, ge=0)
    time_limit_seconds: Optional[int] = None
    narrative_intro: Optional[str] = None
    instructions: Optional[str] = None


class IDSceneTransition(BaseModel):
    """Transition between scenes."""
    model_config = ConfigDict(extra="allow")

    from_scene: int = Field(ge=1)
    to_scene: int = Field(ge=1)
    trigger: str = "score_threshold"  # score_threshold, all_complete, manual
    trigger_value: Optional[Any] = None
    animation: str = "slide_left"


class InteractiveDiagramBlueprint(BaseModel):
    """
    INTERACTIVE_DIAGRAM template blueprint (v3).

    Powered by AssetGraph + GameDesignV3. Supports:
    - Multiple scenes with different images and mechanics
    - Multiple mechanics per scene (drag_drop, trace_path, click_to_identify, etc.)
    - Rich assets per scene (sprites, overlays, animations, sounds)
    - Per-asset game logic (state machines, event triggers)
    - Hierarchical zone architecture
    """
    model_config = ConfigDict(extra="allow")

    templateType: Literal["INTERACTIVE_DIAGRAM"]
    title: str = Field(min_length=1)
    narrativeIntro: str = ""

    # Theme
    theme: Optional[Dict[str, Any]] = None  # {primary_color, mood, style_prompt_suffix}

    # Global labels (canonical list)
    global_labels: List[str] = Field(default_factory=list)
    distractor_labels: List[Dict[str, str]] = Field(default_factory=list)  # [{text, explanation}]

    # Hierarchy (global)
    hierarchy: Optional[Dict[str, Any]] = None  # {enabled, strategy, groups}

    # Scenes
    scenes: List[IDScene] = Field(min_length=1)
    scene_transitions: List[IDSceneTransition] = Field(default_factory=list)

    # Global scoring
    total_max_score: int = Field(default=100, ge=0)
    pass_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    # Difficulty
    difficulty: Optional[Dict[str, Any]] = None  # {base_level, adaptive, scaffolding}

    # Asset graph (serialized for engine traversal)
    asset_graph: Optional[Dict[str, Any]] = None

    # Learning metadata
    learning_objectives: List[str] = Field(default_factory=list)
    estimated_duration_minutes: Optional[int] = None

    @model_validator(mode="after")
    def validate_scene_numbers(self):
        """Ensure scene numbers are sequential starting from 1."""
        numbers = sorted(s.scene_number for s in self.scenes)
        expected = list(range(1, len(self.scenes) + 1))
        if numbers != expected:
            raise ValueError(
                f"Scene numbers must be sequential from 1. Got: {numbers}, expected: {expected}"
            )
        return self

    @model_validator(mode="after")
    def validate_scene_transitions(self):
        """Ensure transitions reference valid scene numbers."""
        valid_numbers = {s.scene_number for s in self.scenes}
        for t in self.scene_transitions:
            if t.from_scene not in valid_numbers:
                raise ValueError(f"Transition references invalid from_scene: {t.from_scene}")
            if t.to_scene not in valid_numbers:
                raise ValueError(f"Transition references invalid to_scene: {t.to_scene}")
        return self


# =============================================================================
# UNION TYPE FOR ALL BLUEPRINTS
# =============================================================================

BlueprintUnion = Union[
    SequenceBuilderBlueprint,
    BucketSortBlueprint,
    ParameterPlaygroundBlueprint,
    TimelineOrderBlueprint,
    MatchPairsBlueprint,
    StateTracerCodeBlueprint,
    InteractiveDiagramBlueprint,
]

TEMPLATE_SCHEMA_MAP = {
    "SEQUENCE_BUILDER": SequenceBuilderBlueprint,
    "BUCKET_SORT": BucketSortBlueprint,
    "PARAMETER_PLAYGROUND": ParameterPlaygroundBlueprint,
    "TIMELINE_ORDER": TimelineOrderBlueprint,
    "MATCH_PAIRS": MatchPairsBlueprint,
    "STATE_TRACER_CODE": StateTracerCodeBlueprint,
    "INTERACTIVE_DIAGRAM": InteractiveDiagramBlueprint,
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_blueprint(
    blueprint: Dict[str, Any],
    template_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate a blueprint against its Pydantic schema.

    Args:
        blueprint: Blueprint dictionary to validate
        template_type: Optional override for template type (uses blueprint's templateType if not provided)

    Returns:
        Dict with 'valid' bool, 'errors' list, 'warnings' list, and 'validated_blueprint'
    """
    errors = []
    warnings = []

    # Determine template type
    if template_type is None:
        template_type = blueprint.get("templateType")

    if not template_type:
        return {
            "valid": False,
            "errors": ["Missing templateType field"],
            "warnings": [],
            "validated_blueprint": None
        }

    # Backward compatibility: accept legacy name
    if template_type == "LABEL_DIAGRAM":
        template_type = "INTERACTIVE_DIAGRAM"

    # Get schema class
    schema_class = TEMPLATE_SCHEMA_MAP.get(template_type)

    if not schema_class:
        # INTERACTIVE_DIAGRAM uses its own schema in interactive_diagram.py
        if template_type == "INTERACTIVE_DIAGRAM":
            return {
                "valid": True,  # Defer to interactive_diagram.py validation
                "errors": [],
                "warnings": ["INTERACTIVE_DIAGRAM validation deferred to interactive_diagram.py schema"],
                "validated_blueprint": blueprint
            }
        # PHET_SIMULATION uses its own schema in phet_simulation.py
        if template_type == "PHET_SIMULATION":
            from app.agents.schemas.phet_simulation import validate_phet_blueprint
            return validate_phet_blueprint(blueprint)
        return {
            "valid": False,
            "errors": [f"Unknown template type: {template_type}"],
            "warnings": [],
            "validated_blueprint": None
        }

    # Validate against schema
    try:
        validated = schema_class.model_validate(blueprint)
        return {
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "validated_blueprint": validated.model_dump()
        }
    except Exception as e:
        error_msg = str(e)
        # Parse Pydantic validation errors for better messages
        if "validation error" in error_msg.lower():
            errors.append(f"Schema validation failed: {error_msg}")
        else:
            errors.append(f"Validation error: {error_msg}")

        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "validated_blueprint": None
        }


def get_schema_for_template(template_type: str) -> Optional[Dict[str, Any]]:
    """Get JSON schema for a template type (for LLM guided generation)"""
    schema_class = TEMPLATE_SCHEMA_MAP.get(template_type)
    if schema_class:
        return schema_class.model_json_schema()
    return None
