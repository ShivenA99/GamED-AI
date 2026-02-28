"""Interaction schemas — output of the Interaction Designer.

Defines scoring rules, feedback rules, and mode transitions that map
directly to frontend types (Mechanic.scoring, Mechanic.feedback, ModeTransition).
"""

from typing import Optional, Union
from pydantic import BaseModel, Field


class ScoringRules(BaseModel):
    """Scoring configuration for a single mechanic.
    Must match frontend Mechanic.scoring shape.
    """
    strategy: str = "per_correct"  # "per_correct" | "all_or_nothing" | "weighted"
    points_per_correct: int = Field(ge=0)
    max_score: int = Field(ge=0)
    partial_credit: bool = True


class MisconceptionFeedback(BaseModel):
    """A single misconception feedback entry."""
    trigger_label: str    # What student action triggers this (matches frontend schema)
    message: str          # Corrective feedback message
    severity: str = "low" # "low" | "medium" | "high"


class FeedbackRules(BaseModel):
    """Feedback configuration for a single mechanic.
    Must match frontend Mechanic.feedback shape.
    """
    on_correct: str = "Correct!"
    on_incorrect: str = "Try again."
    on_completion: str = "Well done! You completed this activity."
    misconceptions: list[MisconceptionFeedback] = Field(default_factory=list)


class ModeTransitionOutput(BaseModel):
    """A transition between interaction modes within a scene.

    Maps to frontend ModeTransition type. Uses Field(alias=) for 'from'
    since it's a Python reserved word.
    """
    from_mode: str = Field(serialization_alias="from")
    to_mode: str = Field(serialization_alias="to")
    trigger: str  # One of ~14 frontend trigger types (see TRIGGER_MAP in contracts)
    trigger_value: Optional[Union[int, float, list[str]]] = None
    animation: str = "fade"
    message: Optional[str] = None

    class Config:
        populate_by_name = True


class SceneInteractionResult(BaseModel):
    """Wraps all interaction design output for one scene."""
    scene_id: str
    mechanic_scoring: dict[str, ScoringRules]   # keyed by mechanic_id
    mechanic_feedback: dict[str, FeedbackRules]  # keyed by mechanic_id
    mode_transitions: list[ModeTransitionOutput] = Field(default_factory=list)
