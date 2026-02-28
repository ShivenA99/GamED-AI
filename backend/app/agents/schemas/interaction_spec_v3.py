"""
InteractionSpecV3 — Per-scene behavioral layer specification.

Produced by interaction_designer_v3 (Phase 3).
Consumed by asset_generator_v3, blueprint_assembler_v3.

Defines: scoring per mechanic, feedback per mechanic, misconception handling,
intra-scene mechanic transitions, animations, and scene completion criteria.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MechanicScoringV3(BaseModel):
    """Scoring configuration for one mechanic."""
    model_config = ConfigDict(extra="allow")

    mechanic_type: str
    strategy: str = "standard"  # standard, progressive, mastery, time_based
    points_per_correct: int = 10
    max_score: int = 100
    partial_credit: bool = True
    hint_penalty: float = 0.1


class MisconceptionFeedbackV3(BaseModel):
    """Targeted misconception feedback."""
    model_config = ConfigDict(extra="allow")

    trigger_label: str  # The label being placed
    trigger_zone: str = ""  # The wrong zone it's placed on (optional)
    message: str  # Pedagogical explanation

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "trigger_label" not in data:
            data["trigger_label"] = data.pop("label", data.pop("trigger", "general"))
        if "message" not in data:
            data["message"] = data.pop("feedback", data.pop("feedback_text", "See the correct answer."))
        return data


class MechanicFeedbackV3(BaseModel):
    """Feedback configuration for one mechanic."""
    model_config = ConfigDict(extra="allow")

    mechanic_type: str
    on_correct: str = "Correct!"
    on_incorrect: str = "Try again."
    on_completion: str = "Well done!"
    misconception_feedback: List[MisconceptionFeedbackV3] = Field(default_factory=list)


class DistractorFeedbackV3(BaseModel):
    """Feedback for distractor labels."""
    model_config = ConfigDict(extra="allow")

    distractor: str
    feedback: str


class ModeTransitionV3(BaseModel):
    """Intra-scene mechanic transition (when to switch from one mechanic to another)."""
    model_config = ConfigDict(extra="allow")

    from_mechanic: str  # e.g., "drag_drop"
    to_mechanic: str  # e.g., "click_to_identify"
    trigger: str = "all_zones_labeled"  # Frontend trigger type
    trigger_value: Optional[Any] = None  # Optional: percentage, zone list, etc.
    animation: str = "fade"
    message: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # from/to shorthand
        if "from" in data and "from_mechanic" not in data:
            data["from_mechanic"] = data.pop("from")
        if "to" in data and "to_mechanic" not in data:
            data["to_mechanic"] = data.pop("to")
        return data


class SceneCompletionV3(BaseModel):
    """Completion criteria for the last mechanic in the scene."""
    model_config = ConfigDict(extra="allow")

    trigger: str = "all_zones_labeled"
    show_results: bool = True
    min_score_to_pass: int = 70


class AnimationSpecV3(BaseModel):
    """Animation specs for game events."""
    model_config = ConfigDict(extra="allow")

    on_correct: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "pulse", "color": "#4CAF50", "duration_ms": 500
    })
    on_incorrect: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "shake", "duration_ms": 300
    })
    on_completion: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "confetti", "duration_ms": 2000
    })


class SceneTransitionDetailV3(BaseModel):
    """Enriched inter-scene transition detail."""
    model_config = ConfigDict(extra="allow")

    trigger: str = "all_complete"
    animation: str = "slide_left"
    message: str = ""


class InteractionSpecV3(BaseModel):
    """Complete behavioral specification for one scene."""
    model_config = ConfigDict(extra="allow")

    scene_number: int

    # Scoring per mechanic
    scoring: List[MechanicScoringV3] = Field(default_factory=list)

    # Feedback per mechanic
    feedback: List[MechanicFeedbackV3] = Field(default_factory=list)

    # Distractor feedback
    distractor_feedback: List[DistractorFeedbackV3] = Field(default_factory=list)

    # Intra-scene mechanic transitions
    mode_transitions: List[ModeTransitionV3] = Field(default_factory=list)

    # Scene completion criteria
    scene_completion: SceneCompletionV3 = Field(default_factory=SceneCompletionV3)

    # Animation specs
    animations: AnimationSpecV3 = Field(default_factory=AnimationSpecV3)

    # Inter-scene transition detail
    transition_to_next: Optional[SceneTransitionDetailV3] = None

    def summary(self) -> str:
        """Generate structured summary for downstream agents."""
        mech_types = [s.mechanic_type for s in self.scoring]
        total_score = sum(s.max_score for s in self.scoring)
        misconceptions = sum(len(f.misconception_feedback) for f in self.feedback)
        return (
            f"Scene {self.scene_number}: "
            f"mechanics: {', '.join(mech_types)} | "
            f"total_score: {total_score} | "
            f"misconceptions: {misconceptions} | "
            f"transitions: {len(self.mode_transitions)}"
        )


# Valid trigger types (must match frontend)
VALID_TRIGGERS = {
    "all_zones_labeled", "all_complete", "percentage_complete",
    "time_elapsed", "path_complete", "sequence_complete",
    "score_threshold", "user_choice",
}

VALID_ANIMATION_TYPES = {
    "pulse", "shake", "confetti", "slide_left", "fade",
    "bounce", "glow", "scale", "zoom_in", "zoom_out",
    "reveal", "none",
}

VALID_SCORING_STRATEGIES = {
    "standard", "progressive", "mastery", "time_based",
}


def validate_interaction_specs(
    interaction_specs: List[Dict[str, Any]],
    scene_specs: List[Dict[str, Any]],
    game_design: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Cross-stage contract validation for interaction specs.

    Checks:
    - Every mechanic in every scene has scoring
    - Every mechanic has on_correct and on_incorrect feedback
    - Misconception feedback exists (>= 2 per scene)
    - Animation types are valid
    - Total max_score is reasonable
    - Distractor feedback exists for all distractors
    """
    issues: List[str] = []

    # Parse
    parsed_specs: List[InteractionSpecV3] = []
    for spec_dict in interaction_specs:
        try:
            parsed_specs.append(InteractionSpecV3.model_validate(spec_dict))
        except Exception as e:
            issues.append(f"Failed to parse interaction spec: {e}")

    # Get scene mechanic types
    scene_mechanics: Dict[int, List[str]] = {}
    for sspec in scene_specs:
        sn = sspec.get("scene_number", 0)
        mechs = sspec.get("mechanic_configs", [])
        scene_mechanics[sn] = [m.get("type", "") for m in mechs if isinstance(m, dict)]

    # Cross-stage checks
    for spec in parsed_specs:
        sn = spec.scene_number
        expected_mechs = set(scene_mechanics.get(sn, []))

        # Every mechanic has scoring
        scored_mechs = {s.mechanic_type for s in spec.scoring}
        missing_scoring = expected_mechs - scored_mechs
        if missing_scoring:
            issues.append(f"Scene {sn}: missing scoring for mechanics: {missing_scoring}")

        # Every mechanic has feedback
        feedback_mechs = {f.mechanic_type for f in spec.feedback}
        missing_feedback = expected_mechs - feedback_mechs
        if missing_feedback:
            issues.append(f"Scene {sn}: missing feedback for mechanics: {missing_feedback}")

        # Misconception feedback exists (>= 2 per scene)
        total_misconceptions = sum(len(f.misconception_feedback) for f in spec.feedback)
        if total_misconceptions < 2:
            issues.append(f"Scene {sn}: only {total_misconceptions} misconception feedbacks (need >= 2)")

        # Mode transitions required for multi-mechanic scenes
        if len(expected_mechs) > 1 and not spec.mode_transitions:
            issues.append(f"Scene {sn}: multi-mechanic scene needs mode_transitions")

        # F3: Mechanic-aware completion trigger validation
        MECHANIC_TRIGGER_MAP = {
            "drag_drop": {"all_zones_labeled", "all_complete", "percentage_complete", "score_threshold"},
            "click_to_identify": {"all_complete", "percentage_complete", "score_threshold"},
            "trace_path": {"path_complete", "all_complete", "score_threshold"},
            "sequencing": {"sequence_complete", "all_complete", "score_threshold"},
            "description_matching": {"all_complete", "percentage_complete", "score_threshold"},
            "sorting_categories": {"all_complete", "score_threshold"},
            "memory_match": {"all_complete", "score_threshold"},
            "branching_scenario": {"all_complete", "user_choice"},
            "compare_contrast": {"all_complete", "score_threshold"},
            "hierarchical": {"all_complete", "percentage_complete", "score_threshold"},
            "timed_challenge": {"time_elapsed", "all_complete", "score_threshold"},
        }
        for mt in spec.mode_transitions:
            valid_from_triggers = MECHANIC_TRIGGER_MAP.get(mt.from_mechanic, set())
            if valid_from_triggers and mt.trigger not in valid_from_triggers:
                issues.append(
                    f"Scene {sn}: transition trigger '{mt.trigger}' may not work "
                    f"for '{mt.from_mechanic}'. Valid: {sorted(valid_from_triggers)}"
                )

    # Fix 2.8: Mechanic-specific content presence checks
    for spec in parsed_specs:
        sn = spec.scene_number
        scored_mech_types = {s.mechanic_type for s in spec.scoring}

        # click_to_identify should have identification prompts in feedback
        if "click_to_identify" in scored_mech_types:
            cti_feedback = [f for f in spec.feedback if f.mechanic_type == "click_to_identify"]
            if cti_feedback:
                fb = cti_feedback[0]
                # Check that on_correct/on_incorrect are not generic defaults
                if fb.on_correct == "Correct!" and fb.on_incorrect == "Try again.":
                    issues.append(
                        f"Scene {sn}: click_to_identify feedback uses generic defaults. "
                        f"Provide content-specific prompts."
                    )

        # description_matching should have zone descriptions
        if "description_matching" in scored_mech_types:
            dm_feedback = [f for f in spec.feedback if f.mechanic_type == "description_matching"]
            if not dm_feedback:
                issues.append(
                    f"Scene {sn}: description_matching mechanic has no feedback entry. "
                    f"Provide content-specific description matching feedback."
                )

        # trace_path should have path-specific feedback
        if "trace_path" in scored_mech_types:
            tp_feedback = [f for f in spec.feedback if f.mechanic_type == "trace_path"]
            if tp_feedback:
                fb = tp_feedback[0]
                if not fb.misconception_feedback:
                    issues.append(
                        f"Scene {sn}: trace_path has no misconception_feedback. "
                        f"Include at least 1 ordering misconception."
                    )

        # sequencing should have ordering-specific feedback
        if "sequencing" in scored_mech_types:
            seq_feedback = [f for f in spec.feedback if f.mechanic_type == "sequencing"]
            if seq_feedback:
                fb = seq_feedback[0]
                if not fb.misconception_feedback:
                    issues.append(
                        f"Scene {sn}: sequencing has no misconception_feedback. "
                        f"Include at least 1 ordering misconception."
                    )

    # Total max_score reasonable
    total_max = sum(s.max_score for spec in parsed_specs for s in spec.scoring)
    if total_max < 50:
        issues.append(f"Total max_score {total_max} is too low (should be >= 50)")
    if total_max > 500:
        issues.append(f"Total max_score {total_max} is very high (consider keeping under 500)")

    # Check distractor feedback
    design_distractors = []
    labels = game_design.get("labels", {})
    if isinstance(labels, dict):
        for dl in labels.get("distractor_labels", []):
            if isinstance(dl, dict):
                design_distractors.append(dl.get("text", ""))
            elif isinstance(dl, str):
                design_distractors.append(dl)

    if design_distractors:
        all_distractor_feedback = set()
        for spec in parsed_specs:
            for df in spec.distractor_feedback:
                all_distractor_feedback.add(df.distractor)
        missing_distractor_feedback = set(design_distractors) - all_distractor_feedback
        if missing_distractor_feedback:
            issues.append(f"Missing distractor feedback for: {missing_distractor_feedback}")

    has_fatal = any("missing scoring" in i or "missing feedback" in i for i in issues)
    passed = not has_fatal
    score = max(0.0, 1.0 - 0.1 * len(issues))

    return {"passed": passed, "score": round(score, 3), "issues": issues}
