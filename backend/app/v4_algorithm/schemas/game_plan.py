"""Game plan schema — output of algo_graph_builder (deterministic)."""

from typing import Optional
from pydantic import BaseModel, Field

from app.v4_algorithm.schemas.algorithm_game_types import ALGORITHM_GAME_TYPE


class AlgorithmAssetSpec(BaseModel):
    """Specification for visual asset generation (Phase 4)."""

    scene_id: str
    asset_type: str = "algorithm_illustration"  # algorithm_illustration, flowchart, growth_chart, board_illustration
    search_queries: list[str] = Field(default_factory=list)
    generation_prompt: str = ""
    style: str = "clean_educational"
    must_include: list[str] = Field(default_factory=list)


class SceneTransition(BaseModel):
    """Transition between scenes."""

    from_scene: str
    to_scene: str
    trigger: str = "completion"  # completion, score_threshold, user_choice
    threshold: Optional[float] = None  # for score_threshold


class AlgorithmScenePlan(BaseModel):
    """One scene in the game plan — includes IDs and computed scores."""

    scene_id: str
    scene_number: int
    title: str
    game_type: ALGORITHM_GAME_TYPE
    difficulty: str = "intermediate"
    learning_goal: str = ""
    narrative_intro: str = ""
    max_score: int = 0
    config_hints: dict = Field(default_factory=dict)
    needs_asset: bool = False
    asset_spec: Optional[AlgorithmAssetSpec] = None


class AlgorithmGamePlan(BaseModel):
    """Full game plan with computed IDs and scores."""

    title: str
    algorithm_name: str
    algorithm_category: str = ""
    total_max_score: int = 0
    scenes: list[AlgorithmScenePlan] = Field(min_length=1)
    scene_transitions: list[SceneTransition] = Field(default_factory=list)
