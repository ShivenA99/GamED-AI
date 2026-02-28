"""
Extended Game Plan schemas for multi-scene, multi-mechanic support.

The game_planner agent is the BRAIN that decides:
- How many scenes (n)
- Which mechanics per scene (m[i])
- What assets each scene needs
- How mechanics and scenes connect
"""
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class MechanicType(str, Enum):
    DRAG_DROP = "drag_drop"
    TRACE_PATH = "trace_path"
    SEQUENCING = "sequencing"
    SORTING = "sorting"
    MEMORY_MATCH = "memory_match"
    COMPARISON = "comparison"
    BRANCHING_SCENARIO = "branching_scenario"
    CLICK_TO_IDENTIFY = "click_to_identify"
    REVEAL = "reveal"
    HOTSPOT = "hotspot"


class WorkflowType(str, Enum):
    LABELING_DIAGRAM = "labeling_diagram"
    TRACE_PATH = "trace_path"
    SEQUENCE_ITEMS = "sequence_items"
    COMPARISON_DIAGRAMS = "comparison_diagrams"
    SORTING = "sorting"
    MEMORY_MATCH = "memory_match"
    BRANCHING_SCENARIO = "branching_scenario"


class ProgressionType(str, Enum):
    LINEAR = "linear"
    ZOOM_IN = "zoom_in"
    BRANCHING = "branching"


class TransitionTrigger(str, Enum):
    ALL_ZONES_LABELED = "all_zones_labeled"
    SCORE_THRESHOLD = "score_threshold"
    TIME_ELAPSED = "time_elapsed"
    USER_ACTION = "user_action"
    MODE_SEQUENCE_COMPLETE = "mode_sequence_complete"
    SPECIFIC_ZONE_COMPLETE = "specific_zone_complete"


class MechanicSpec(BaseModel):
    type: MechanicType
    scoring_weight: float = Field(ge=0.0, le=1.0, default=1.0)
    completion_criteria: str = "all_complete"
    trigger: Optional[str] = None
    trigger_value: Optional[Union[int, float, str]] = None
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AssetNeed(BaseModel):
    query: Optional[str] = None
    type: Optional[str] = None
    workflow: WorkflowType
    depends_on: List[str] = Field(default_factory=list)
    concept: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ModeTransition(BaseModel):
    from_mode: MechanicType
    to_mode: MechanicType
    trigger: TransitionTrigger
    trigger_value: Optional[Union[int, float, str]] = None
    animation: str = "fade"

    class Config:
        use_enum_values = True


class SceneTask(BaseModel):
    """A task (phase) within a scene. Each task uses the same image but may
    activate a different subset of zones/labels with a different mechanic."""
    task_id: str
    title: str
    description: Optional[str] = None
    mechanic: MechanicType
    focus_labels: List[str] = Field(default_factory=list)
    scoring_weight: float = Field(ge=0.0, le=1.0, default=1.0)
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class SceneBreakdown(BaseModel):
    scene_number: int = Field(ge=1)
    title: str
    description: Optional[str] = None
    mechanics: List[MechanicSpec]
    asset_needs: Dict[str, AssetNeed]
    mode_transitions: List[ModeTransition] = Field(default_factory=list)
    completion_criteria: Optional[str] = None
    tasks: List[SceneTask] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class SceneTransition(BaseModel):
    from_scene: int = Field(ge=1)
    to_scene: int = Field(ge=1)
    trigger: TransitionTrigger
    trigger_value: Optional[Union[int, float, str]] = None
    animation: str = "slide"

    class Config:
        use_enum_values = True


class ScoringRubric(BaseModel):
    max_score: int = 100
    passing_score: int = 70
    points_per_correct: int = 10
    penalty_per_incorrect: int = 0
    time_bonus: bool = False
    scene_weights: Optional[Dict[int, float]] = None


class ExtendedGamePlan(BaseModel):
    """Extended game plan with multi-scene, multi-mechanic support."""
    title: str
    total_scenes: int = Field(ge=1)
    progression_type: ProgressionType = ProgressionType.LINEAR
    scene_breakdown: List[SceneBreakdown]
    scene_transitions: List[SceneTransition] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    scoring_rubric: Optional[ScoringRubric] = None
    difficulty_progression: Optional[Dict[str, Any]] = None
    feedback_strategy: Optional[Dict[str, Any]] = None
    required_labels: Optional[List[str]] = None
    hierarchy_info: Optional[Dict[str, Any]] = None
    estimated_duration_minutes: Optional[int] = None

    class Config:
        use_enum_values = True
        extra = "allow"


def create_single_scene_plan(
    title: str,
    mechanic: MechanicType,
    asset_workflow: WorkflowType,
    query: Optional[str] = None,
    learning_objectives: Optional[List[str]] = None
) -> ExtendedGamePlan:
    """Create a simple single-scene game plan for backward compatibility."""
    return ExtendedGamePlan(
        title=title,
        total_scenes=1,
        progression_type=ProgressionType.LINEAR,
        scene_breakdown=[
            SceneBreakdown(
                scene_number=1,
                title=title,
                mechanics=[MechanicSpec(type=mechanic, scoring_weight=1.0, completion_criteria="all_complete")],
                asset_needs={"primary": AssetNeed(query=query, workflow=asset_workflow)}
            )
        ],
        learning_objectives=learning_objectives or []
    )


# =============================================================================
# UNCONSTRAINED GAME DESIGN SCHEMAS (for game_designer agent)
# =============================================================================
# These schemas allow the game_designer to express creative intent freely.
# The design_interpreter agent maps these to structured GamePlan downstream.

class SceneDesign(BaseModel):
    """Unconstrained scene design — describes WHAT, not HOW."""
    scene_number: int = Field(ge=1)
    title: str
    description: str  # What happens in this scene
    learning_goal: str  # What the learner should achieve
    interaction_description: str  # Free text: "students drag labels", "trace blood flow", etc.
    visual_needs: List[str] = Field(default_factory=list)  # What visuals are needed
    scoring_approach: str = "standard"  # How to score this scene
    builds_on: Optional[str] = None  # Title of prerequisite scene, if any

    class Config:
        extra = "allow"  # Allow LLM creativity


class GameDesign(BaseModel):
    """
    Unconstrained game design output from game_designer agent.

    This is the CREATIVE output — no MechanicType enums, no WorkflowType constraints.
    The design_interpreter agent maps this to structured GamePlan downstream.
    """
    title: str
    learning_objectives: List[str] = Field(default_factory=list)
    pedagogical_reasoning: str = ""  # Why this design approach
    scenes: List[SceneDesign] = Field(default_factory=list)
    progression_type: str = "linear"  # linear, zoom_in, branching, single
    estimated_duration_minutes: int = 10
    difficulty_approach: str = ""  # How difficulty is managed

    class Config:
        extra = "allow"  # Allow LLM creativity
