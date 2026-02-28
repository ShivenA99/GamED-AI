"""Game concept schema — output of algo_game_concept_designer."""

from typing import Optional, Literal
from pydantic import BaseModel, Field

from app.v4_algorithm.schemas.algorithm_game_types import (
    ALGORITHM_GAME_TYPE,
    ALGORITHM_CATEGORY,
    VISUALIZATION_TYPE,
)


class AlgorithmSceneConcept(BaseModel):
    """One scene in the game concept — maps to one game mechanic."""

    title: str
    learning_goal: str
    narrative_intro: str = ""
    game_type: ALGORITHM_GAME_TYPE
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"

    # Asset specification
    needs_visualization: bool = False
    visualization_description: str = ""
    visualization_type: VISUALIZATION_TYPE = "none"

    # Game-type-specific hints (not full content — Phase 3 generates that)
    config_hints: dict = Field(default_factory=dict)


class AlgorithmGameConcept(BaseModel):
    """Full multi-scene game concept designed by LLM."""

    title: str
    algorithm_name: str
    algorithm_category: str = ""
    narrative_theme: str = ""
    narrative_intro: str = ""
    scenes: list[AlgorithmSceneConcept] = Field(min_length=1, max_length=6)
    difficulty_progression: Literal["flat", "ascending", "mixed"] = "ascending"
    estimated_duration_minutes: int = Field(default=15, ge=5, le=60)
