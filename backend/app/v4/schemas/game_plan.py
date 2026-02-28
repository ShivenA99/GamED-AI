"""Game Plan schemas — output of the deterministic Graph Builder.

GamePlan is the formal game state graph produced by the graph builder from
GameConcept + SceneCreativeDesigns. The graph builder assigns IDs, computes
scores, copies creative designs, and builds mechanic connections.

This is NOT LLM-produced — it's 100% deterministic.
"""

from typing import Literal, Optional, Any
from pydantic import BaseModel, Field

from app.v4.schemas.creative_design import (
    ImageSpec,
    MechanicCreativeDesign,
    SceneCreativeDesign,
)


SUPPORTED_MECHANIC_TYPES = Literal[
    "drag_drop",
    "click_to_identify",
    "trace_path",
    "sequencing",
    "sorting_categories",
    "memory_match",
    "branching_scenario",
    "description_matching",
]


class MechanicConnection(BaseModel):
    """Transition between mechanics within a scene."""

    from_mechanic_id: str
    to_mechanic_id: str
    trigger: str  # Resolved frontend trigger string (from TRIGGER_MAP)
    trigger_value: Optional[Any] = None


class SceneTransition(BaseModel):
    """Transition between scenes."""

    transition_type: Literal["auto", "score_gated"] = "auto"
    min_score_pct: Optional[float] = None


class MechanicPlan(BaseModel):
    """Formal mechanic node in the game state graph.

    Contains everything needed by downstream agents: creative design for
    content generation, scoring params, zone labels, timing.
    """

    mechanic_id: str  # Generated: "s{scene}_m{index}"
    mechanic_type: SUPPORTED_MECHANIC_TYPES
    zone_labels_used: list[str] = Field(default_factory=list)
    instruction_text: str  # From SceneCreativeDesign
    creative_design: MechanicCreativeDesign  # Full creative direction
    expected_item_count: int = Field(ge=1)
    points_per_item: int = Field(default=10, ge=1)
    max_score: int = 0  # Computed: expected_item_count * points_per_item
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None
    parent_mechanic_id: Optional[str] = None
    is_terminal: bool = False
    advance_trigger: str = "completion"
    advance_trigger_value: Optional[float] = None


class ScenePlan(BaseModel):
    """Formal scene node in the game state graph.

    Contains the full creative design, image specs, mechanics with connections,
    and computed scoring.
    """

    scene_id: str  # "scene_1", "scene_2", etc.
    scene_number: int  # 1-indexed
    title: str
    learning_goal: str
    narrative_intro: str = ""
    zone_labels: list[str] = Field(default_factory=list)
    needs_diagram: bool = True
    image_spec: Optional[ImageSpec] = None
    second_image_spec: Optional[ImageSpec] = None  # For compare_contrast
    creative_design: SceneCreativeDesign  # Full creative direction
    mechanics: list[MechanicPlan] = Field(min_length=1)
    mechanic_connections: list[MechanicConnection] = Field(default_factory=list)
    starting_mechanic_id: str = ""
    transition_to_next: Optional[SceneTransition] = None
    scene_max_score: int = 0  # Computed: sum of mechanic max_scores


class GamePlan(BaseModel):
    """The formal game state graph. Produced by graph builder, NOT by LLM.

    All IDs are formulaic, all scores are computed, all connections are
    derived from list order + advance_triggers. Creative designs are
    copied from SceneCreativeDesign.
    """

    title: str
    subject: str
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    estimated_duration_minutes: int = Field(default=10, ge=1, le=30)
    narrative_theme: str = ""
    narrative_intro: str = ""
    completion_message: str = ""
    all_zone_labels: list[str] = Field(default_factory=list)
    distractor_labels: list[str] = Field(default_factory=list)
    label_hierarchy: Optional[dict[str, list[str]]] = None
    total_max_score: int = 0  # Computed: sum of scene_max_scores
    scenes: list[ScenePlan] = Field(min_length=1)

    model_config = {"extra": "allow"}
