"""Game Concept schemas — output of the Game Concept Designer (Phase 1a).

High-level game structure: WHAT scenes, WHAT mechanics, WHY — not HOW they look/feel.
No graph IDs, no visual specs, no asset details.

The 3-stage creative cascade:
  Phase 1a: GameConcept (this file) — WHAT and WHY
  Phase 1b: SceneCreativeDesign (creative_design.py) — HOW it looks/feels
  Graph Builder: GamePlan (game_plan.py) — formal graph with IDs/scores
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class MechanicChoice(BaseModel):
    """One mechanic chosen for a scene, with rationale."""

    mechanic_type: Literal[
        "drag_drop",
        "click_to_identify",
        "trace_path",
        "sequencing",
        "sorting_categories",
        "memory_match",
        "branching_scenario",
        "description_matching",
    ]
    learning_purpose: str
    zone_labels_used: list[str] = Field(default_factory=list)
    expected_item_count: int = Field(ge=1)
    points_per_item: int = Field(default=10, ge=1)

    # Transition to next mechanic
    advance_trigger: Literal[
        "completion", "score_threshold", "time_elapsed", "user_choice"
    ] = "completion"
    advance_trigger_value: Optional[float] = None

    # Timing
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None


class SceneConcept(BaseModel):
    """One scene as conceived by the game concept designer."""

    title: str
    learning_goal: str
    narrative_intro: str = ""
    zone_labels: list[str] = Field(default_factory=list)

    needs_diagram: bool
    image_description: str = ""

    mechanics: list[MechanicChoice] = Field(min_length=1)

    transition_to_next: Literal["auto", "score_gated"] = "auto"
    transition_min_score_pct: Optional[float] = None


class GameConcept(BaseModel):
    """Output of the game concept designer LLM.

    High-level game structure — WHAT and WHY, not HOW.
    No graph IDs, no visual specs, no asset details.
    """

    title: str
    subject: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_duration_minutes: int = Field(ge=1, le=30)
    narrative_theme: str
    narrative_intro: str
    completion_message: str

    all_zone_labels: list[str]
    distractor_labels: list[str] = Field(default_factory=list)
    label_hierarchy: Optional[dict[str, list[str]]] = None

    scenes: list[SceneConcept] = Field(min_length=1, max_length=6)

    model_config = {"extra": "allow"}
