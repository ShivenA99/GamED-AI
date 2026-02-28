"""Algorithm game blueprint — final output assembled from all phases."""

from typing import Optional
from pydantic import BaseModel, Field

from app.v4_algorithm.schemas.algorithm_content import (
    LearnModeConfig,
    TestModeConfig,
)
from app.v4_algorithm.schemas.game_plan import SceneTransition


class AlgorithmSceneBlueprint(BaseModel):
    """One scene in a multi-scene blueprint."""
    scene_id: str
    scene_number: int
    title: str
    game_type: str
    difficulty: str = "intermediate"
    learning_goal: str = ""
    max_score: int = 0
    content: dict = Field(default_factory=dict)
    asset_url: Optional[str] = None


class AlgorithmGameBlueprint(BaseModel):
    """Final blueprint consumed by the frontend.

    Field names match frontend TypeScript types.
    """
    templateType: str = "ALGORITHM_GAME"
    title: str
    subject: str = ""
    difficulty: str = "intermediate"
    algorithmName: str
    algorithmCategory: str = ""
    narrativeIntro: str = ""
    totalMaxScore: int = 0
    passThreshold: float = 0.6

    # Mode configs
    learn_config: LearnModeConfig = Field(default_factory=LearnModeConfig)
    test_config: TestModeConfig = Field(default_factory=TestModeConfig)

    # Single-scene: route based on algorithmGameType
    algorithmGameType: Optional[str] = None

    # Per-type content (only one populated for single-scene)
    stateTracerBlueprint: Optional[dict] = None
    bugHunterBlueprint: Optional[dict] = None
    algorithmBuilderBlueprint: Optional[dict] = None
    complexityAnalyzerBlueprint: Optional[dict] = None
    constraintPuzzleBlueprint: Optional[dict] = None

    # Multi-scene support
    is_multi_scene: bool = False
    scenes: Optional[list[AlgorithmSceneBlueprint]] = None
    scene_transitions: Optional[list[SceneTransition]] = None

    # Visual assets
    scene_assets: Optional[dict] = None  # {scene_id: {image_url, ...}}
