"""
GameDesignV3 — Complete Game Design Document schema.

This is the single source of truth for everything downstream agents and
scripts need to build the game. The game_designer ReAct agent outputs this
schema. It captures all 14 independent dimensions of a high-quality
educational game:

1. Visual Design (per scene)
2. Zone Architecture (per scene)
3. Label Design (global + per scene)
4. Mechanic Sequence (per scene, multiple per scene)
5. Path/Flow Data (per mechanic)
6. Scoring Architecture (per mechanic)
7. Feedback Design (per zone + per mechanic)
8. Animation Specs (per event)
9. Media Assets (per scene, independent of zones)
10. Temporal Intelligence (per scene)
11. Scene Transitions
12. Difficulty & Scaffolding
13. Accessibility
14. Theme & Atmosphere
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Theme & Atmosphere (#14)
# ---------------------------------------------------------------------------

class ThemeSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    visual_tone: str = "clinical_educational"
    color_palette: Dict[str, str] = Field(default_factory=lambda: {
        "primary": "#3b82f6",
        "success": "#22c55e",
        "error": "#ef4444",
        "warning": "#f59e0b",
        "background": "#f8fafc",
        "surface": "#ffffff",
        "text_primary": "#0f172a",
        "text_secondary": "#64748b",
    })
    background_description: Optional[str] = None
    narrative_frame: Optional[str] = None


# ---------------------------------------------------------------------------
# Labels (#3)
# ---------------------------------------------------------------------------

class DistractorLabel(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str
    explanation: str  # WHY it's wrong (misconception feedback)
    appears_in_scenes: Optional[List[int]] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_distractor(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # LLM uses "label" or "name" instead of "text"
        if "text" not in data:
            data["text"] = data.pop("label", None) or data.pop("name", None) or ""
        # LLM sometimes omits explanation
        if "explanation" not in data:
            data["explanation"] = data.pop("reason", None) or data.pop("why_wrong", None) or "Incorrect option"
        return data


class HierarchyGroup(BaseModel):
    model_config = ConfigDict(extra="allow")

    parent: str
    children: List[str]
    reveal_trigger: str = "complete_parent"  # complete_parent, click_expand, hover_reveal


class HierarchySpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    strategy: str = ""  # Human-readable: "Progressive reveal from chambers to vessels"
    groups: List[HierarchyGroup] = Field(default_factory=list)


class LabelDesign(BaseModel):
    """All labels used anywhere in the game, defined globally."""
    model_config = ConfigDict(extra="allow")

    zone_labels: List[str] = Field(default_factory=list)
    group_only_labels: List[str] = Field(default_factory=list)
    distractor_labels: List[DistractorLabel] = Field(default_factory=list)
    hierarchy: Optional[HierarchySpec] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_labels(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # LLM sometimes produces zone_labels as list of dicts: [{text: "X"}, ...]
        zl = data.get("zone_labels", [])
        if zl and isinstance(zl[0], dict):
            data["zone_labels"] = [
                item.get("text") or item.get("label") or item.get("name") or str(item)
                for item in zl
            ]
        # Same for group_only_labels
        gl = data.get("group_only_labels", [])
        if gl and isinstance(gl[0], dict):
            data["group_only_labels"] = [
                item.get("text") or item.get("label") or item.get("name") or str(item)
                for item in gl
            ]
        # LLM sometimes puts distractor_labels as list of strings
        dl = data.get("distractor_labels", [])
        if dl and isinstance(dl[0], str):
            data["distractor_labels"] = [
                {"text": item, "explanation": "Incorrect option"} for item in dl
            ]
        return data


# ---------------------------------------------------------------------------
# Zone Specs (#2)
# ---------------------------------------------------------------------------

class ZoneSpec(BaseModel):
    """Optional per-zone design details for zones needing special handling."""
    model_config = ConfigDict(extra="allow")

    label: str
    zone_type: Optional[str] = None  # point, area
    difficulty: Optional[int] = None  # 1-5
    hint_progression: List[str] = Field(default_factory=list)
    description: Optional[str] = None  # For description_matching
    keyboard_shortcut: Optional[str] = None


# ---------------------------------------------------------------------------
# Visual Design (#1)
# ---------------------------------------------------------------------------

class ComparisonVisualSpec(BaseModel):
    """For compare_contrast mode — two separate images."""
    model_config = ConfigDict(extra="allow")

    diagram_a_description: str = ""
    diagram_a_required_elements: List[str] = Field(default_factory=list)
    diagram_b_description: str = ""
    diagram_b_required_elements: List[str] = Field(default_factory=list)


class SceneVisualSpec(BaseModel):
    """What image/diagram this scene needs."""
    model_config = ConfigDict(extra="allow")

    description: str = ""
    required_elements: List[str] = Field(default_factory=list)
    style: str = "clean educational, no pre-printed labels, neutral background"
    image_source: str = "search_then_generate"  # search, generate, search_then_generate
    comparison: Optional[ComparisonVisualSpec] = None


# ---------------------------------------------------------------------------
# Mechanic-specific configs (#5)
# ---------------------------------------------------------------------------

class PathDesign(BaseModel):
    """trace_path mechanic config."""
    model_config = ConfigDict(extra="allow")

    waypoints: List[str] = Field(default_factory=list)  # Ordered label texts
    path_type: str = "linear"  # linear, cyclic, branching
    visual_style: Optional[str] = None  # blue_to_red_gradient, etc.
    drawing_mode: str = "click_waypoints"  # click_waypoints, freehand
    particle_theme: str = "dots"  # dots, arrows, droplets, cells, electrons
    particle_speed: str = "medium"  # slow, medium, fast
    color_transition_enabled: bool = True
    show_direction_arrows: bool = True
    show_waypoint_labels: bool = True
    show_full_flow_on_complete: bool = True
    instruction_text: Optional[str] = None


class ClickDesign(BaseModel):
    """click_to_identify mechanic config."""
    model_config = ConfigDict(extra="allow")

    click_options: List[str] = Field(default_factory=list)
    correct_assignments: Dict[str, str] = Field(default_factory=dict)
    selection_mode: str = "any_order"  # sequential, any_order
    prompts: List[Dict[str, str]] = Field(default_factory=list)  # [{zone_label, prompt_text}]
    prompt_style: str = "naming"  # naming, functional
    highlight_on_hover: bool = True
    highlight_style: str = "subtle"  # subtle, outlined, invisible
    magnification_enabled: bool = False
    magnification_factor: float = 1.5
    explore_mode_enabled: bool = False
    explore_time_limit_seconds: Optional[int] = None
    show_zone_count: bool = True
    instruction_text: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_prompts(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # LLM sometimes produces prompts as list of strings
        prompts = data.get("prompts", [])
        if prompts and isinstance(prompts[0], str):
            data["prompts"] = [{"zone_label": "", "prompt_text": p} for p in prompts]
        return data


class SequenceItem(BaseModel):
    """An item in a sequencing activity."""
    model_config = ConfigDict(extra="allow")

    id: str
    text: str
    description: Optional[str] = None
    image: Optional[str] = None  # URL/path to illustration
    icon: Optional[str] = None  # Emoji or icon identifier
    category: Optional[str] = None  # Grouping category
    is_distractor: bool = False
    order_index: Optional[int] = None  # Correct position (0-based)

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"id": data.lower().replace(" ", "_"), "text": data}
        if not isinstance(data, dict):
            return data
        if "id" not in data and "text" in data:
            data["id"] = data["text"].lower().replace(" ", "_")[:30]
        return data


class SequenceDesign(BaseModel):
    """sequencing mechanic config."""
    model_config = ConfigDict(extra="allow")

    correct_order: List[str] = Field(default_factory=list)  # item IDs in correct order
    items: List[SequenceItem] = Field(default_factory=list)
    sequence_type: str = "linear"  # linear, cyclic, branching
    layout_mode: str = "horizontal_timeline"  # horizontal_timeline, vertical_list, circular_cycle, flowchart, insert_between
    interaction_pattern: str = "drag_reorder"  # drag_reorder, drag_to_slots, click_to_swap, number_typing
    card_type: str = "text_only"  # text_only, text_with_icon, image_with_caption, image_only
    connector_style: str = "arrow"  # arrow, line, numbered, none
    show_position_numbers: bool = True
    allow_distractors: bool = False
    instruction_text: Optional[str] = None
    instructions: Optional[str] = None  # Alias

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # items as list of strings → SequenceItem list
        items = data.get("items", [])
        if items and isinstance(items[0], str):
            data["items"] = [{"id": f"item_{i}", "text": t} for i, t in enumerate(items)]
        # instruction_text ↔ instructions alias
        if "instructions" in data and "instruction_text" not in data:
            data["instruction_text"] = data["instructions"]
        return data


class SortingCategoryDesign(BaseModel):
    """A category in a sorting activity."""
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"id": data.lower().replace(" ", "_"), "name": data}
        if not isinstance(data, dict):
            return data
        if "id" not in data and "name" in data:
            data["id"] = data["name"].lower().replace(" ", "_")[:30]
        # label → name
        if "label" in data and "name" not in data:
            data["name"] = data.pop("label")
        return data


class SortingItemDesign(BaseModel):
    """An item to be sorted into categories."""
    model_config = ConfigDict(extra="allow")

    id: str
    text: str
    correct_category_ids: List[str] = Field(default_factory=list)  # LIST — can belong to multiple
    description: Optional[str] = None
    image: Optional[str] = None
    difficulty: Optional[str] = None  # easy, medium, hard

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"id": data.lower().replace(" ", "_"), "text": data}
        if not isinstance(data, dict):
            return data
        if "id" not in data and "text" in data:
            data["id"] = data["text"].lower().replace(" ", "_")[:30]
        # correct_category (singular) → correct_category_ids (list)
        if "correct_category" in data and "correct_category_ids" not in data:
            val = data.pop("correct_category")
            data["correct_category_ids"] = [val] if isinstance(val, str) else val
        if "correct_category_id" in data and "correct_category_ids" not in data:
            val = data.pop("correct_category_id")
            data["correct_category_ids"] = [val] if isinstance(val, str) else val
        return data


class SortingDesign(BaseModel):
    """sorting_categories mechanic config."""
    model_config = ConfigDict(extra="allow")

    categories: List[SortingCategoryDesign] = Field(default_factory=list)
    items: List[SortingItemDesign] = Field(default_factory=list)
    sort_mode: str = "bucket"  # bucket, venn_2, venn_3, matrix, column
    item_card_type: str = "text_only"  # text_only, text_with_icon, image_with_caption
    container_style: str = "bucket"  # bucket, labeled_bin, circle, cell, column
    submit_mode: str = "batch_submit"  # batch_submit, immediate_feedback, round_based
    allow_multi_category: bool = False
    max_attempts: int = 3
    show_category_hints: bool = True
    instruction_text: Optional[str] = None
    instructions: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # categories as list of strings → SortingCategoryDesign list
        cats = data.get("categories", [])
        if cats and isinstance(cats[0], str):
            data["categories"] = [{"id": c.lower().replace(" ", "_"), "name": c} for c in cats]
        # items as list of strings → SortingItemDesign list
        items = data.get("items", [])
        if items and isinstance(items[0], str):
            data["items"] = [{"id": f"item_{i}", "text": t} for i, t in enumerate(items)]
        return data


class BranchingChoiceDesign(BaseModel):
    """A choice option within a branching decision node."""
    model_config = ConfigDict(extra="allow")

    text: str
    next_node_id: Optional[str] = None  # null = ending
    is_correct: Optional[bool] = None
    quality: Optional[str] = None  # optimal, acceptable, suboptimal, harmful
    consequence_text: Optional[str] = None
    points: Optional[int] = None


class BranchingNodeDesign(BaseModel):
    """A decision node in a branching scenario."""
    model_config = ConfigDict(extra="allow")

    id: str
    prompt: str
    narrative_text: Optional[str] = None
    node_type: str = "decision"  # decision, info, ending, checkpoint
    choices: List[BranchingChoiceDesign] = Field(default_factory=list)
    ending_type: Optional[str] = None  # good, neutral, bad
    image_description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # question → prompt
        if "question" in data and "prompt" not in data:
            data["prompt"] = data.pop("question")
        # options → choices
        if "options" in data and "choices" not in data:
            data["choices"] = data.pop("options")
        return data


class BranchingDesign(BaseModel):
    """branching_scenario mechanic config."""
    model_config = ConfigDict(extra="allow")

    nodes: List[BranchingNodeDesign] = Field(default_factory=list)
    start_node_id: str = ""
    narrative_structure: str = "linear"  # linear, branching, foldback
    show_path_taken: bool = True
    allow_backtrack: bool = False
    show_consequences: bool = True
    multiple_valid_endings: bool = False
    instruction_text: Optional[str] = None
    instructions: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # nodes as list of simple dicts → BranchingNodeDesign
        nodes = data.get("nodes", [])
        if nodes and isinstance(nodes[0], dict) and "id" not in nodes[0]:
            # Auto-assign IDs
            for i, n in enumerate(nodes):
                n.setdefault("id", f"node_{i}")
        return data


class CompareDesign(BaseModel):
    """compare_contrast mechanic config."""
    model_config = ConfigDict(extra="allow")

    expected_categories: List[Dict[str, Any]] = Field(default_factory=list)  # [{name, subject_a_value, subject_b_value}]
    subjects: List[str] = Field(default_factory=list)  # ["Plant Cell", "Animal Cell"]
    comparison_mode: str = "side_by_side"  # side_by_side, slider, overlay_toggle, venn, spot_difference
    category_types: List[str] = Field(default_factory=lambda: ["similar", "different", "unique_a", "unique_b"])
    highlight_matching: bool = True
    exploration_enabled: bool = False
    zoom_enabled: bool = False
    instruction_text: Optional[str] = None
    instructions: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # expected_categories as dict (old format) → list (new format)
        ec = data.get("expected_categories", {})
        if isinstance(ec, dict) and ec:
            # Old: {zone_label: "similar"/"different"} → New: [{name, category}]
            data["expected_categories"] = [
                {"name": k, "category": v} for k, v in ec.items()
            ]
        return data


class MemoryPairDesign(BaseModel):
    """A pair in a memory match game."""
    model_config = ConfigDict(extra="allow")

    id: str
    term: str
    definition: str
    front_type: str = "text"  # text, image
    back_type: str = "text"
    explanation: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    zone_id: Optional[str] = None  # For diagram_region_to_label variant

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "id" not in data:
            term = data.get("term", data.get("front", ""))
            data["id"] = f"pair_{term.lower().replace(' ', '_')[:20]}"
        # front/back → term/definition
        if "front" in data and "term" not in data:
            data["term"] = data.pop("front")
        if "back" in data and "definition" not in data:
            data["definition"] = data.pop("back")
        return data


class MemoryMatchDesign(BaseModel):
    """memory_match mechanic config."""
    model_config = ConfigDict(extra="allow")

    pairs: List[MemoryPairDesign] = Field(default_factory=list)
    game_variant: str = "classic"  # classic, column_match, scatter, progressive, peek
    match_type: str = "term_to_definition"  # identical, term_to_definition, image_to_label, concept_to_example, diagram_region_to_label
    grid_size: Optional[str] = None  # "4x3" etc, auto if None
    card_back_style: str = "pattern"  # solid, gradient, pattern, question_mark, custom
    matched_card_behavior: str = "fade"  # fade, shrink, collect, checkmark
    show_explanation_on_match: bool = True
    mismatch_penalty: str = "none"  # none, score_decay, life_loss, time_penalty
    flip_duration_ms: int = 600
    instruction_text: Optional[str] = None
    instructions: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # grid_size as list → string
        gs = data.get("grid_size")
        if isinstance(gs, list) and len(gs) == 2:
            data["grid_size"] = f"{gs[0]}x{gs[1]}"
        # pairs as list of {front, back} → MemoryPairDesign
        pairs = data.get("pairs", [])
        if pairs and isinstance(pairs[0], dict) and "front" in pairs[0] and "term" not in pairs[0]:
            for i, p in enumerate(pairs):
                p.setdefault("id", f"pair_{i}")
                if "term" not in p:
                    p["term"] = p.pop("front", "")
                if "definition" not in p:
                    p["definition"] = p.pop("back", "")
        return data


class TimedDesign(BaseModel):
    """timed_challenge wrapper config."""
    model_config = ConfigDict(extra="allow")

    wrapped_mechanic_type: Optional[str] = None
    time_limit_seconds: int = 60
    timer_warning_threshold: float = 0.3  # Fraction of time remaining


class DescriptionMatchDesign(BaseModel):
    """description_matching mechanic config."""
    model_config = ConfigDict(extra="allow")

    sub_mode: str = "click_zone"  # click_zone, drag_description, multiple_choice
    descriptions: List[Dict[str, str]] = Field(default_factory=list)  # [{zone_label, description}]
    show_connecting_lines: bool = True
    defer_evaluation: bool = False
    distractor_count: int = 0
    description_panel_position: str = "right"  # left, right, bottom
    instruction_text: Optional[str] = None
    instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# Scoring (#6)
# ---------------------------------------------------------------------------

class MechanicScoring(BaseModel):
    model_config = ConfigDict(extra="allow")

    points_per_correct: int = 10
    partial_credit: bool = True
    hint_penalty: float = 0.1  # Fraction reduction per hint used
    time_bonus: Optional[Dict[str, Any]] = None  # {enabled, max_bonus}
    streak_bonus: Optional[Dict[int, int]] = None  # {streak_count: bonus_points}
    max_score: Optional[int] = None  # Override auto-calc


# ---------------------------------------------------------------------------
# Feedback (#7)
# ---------------------------------------------------------------------------

class MisconceptionFeedback(BaseModel):
    model_config = ConfigDict(extra="allow")

    trigger: str  # Condition: "Right Ventricle placed on left side"
    message: str  # Response: "Remember, the heart's right side appears on YOUR left..."

    @model_validator(mode="before")
    @classmethod
    def _coerce_misconception(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # LLM produces rich structured feedback like:
        # {incorrect_placement: {placed_label, target_zone}, feedback_text: "..."}
        # {incorrect_step: {from_node, to_node}, feedback_text: "..."}
        if "trigger" not in data:
            # Build trigger from structured keys
            if "incorrect_placement" in data:
                placement = data["incorrect_placement"]
                if isinstance(placement, dict):
                    data["trigger"] = f"{placement.get('placed_label', '?')} placed on {placement.get('target_zone', '?')}"
                else:
                    data["trigger"] = str(placement)
            elif "incorrect_step" in data:
                step = data["incorrect_step"]
                if isinstance(step, dict):
                    data["trigger"] = f"{step.get('from_node', '?')} → {step.get('to_node', '?')}"
                else:
                    data["trigger"] = str(step)
            elif "condition" in data:
                data["trigger"] = data.pop("condition")
            else:
                # Fallback: use first string-valued key as trigger
                for k, v in data.items():
                    if isinstance(v, str) and k != "message" and k != "feedback_text":
                        data["trigger"] = f"{k}: {v}"
                        break
                else:
                    data["trigger"] = "general"
        if "message" not in data:
            data["message"] = (
                data.pop("feedback_text", None) or
                data.pop("feedback", None) or
                data.pop("response", None) or
                data.pop("explanation", None) or
                "See the correct answer."
            )
        return data


class MechanicFeedback(BaseModel):
    model_config = ConfigDict(extra="allow")

    on_correct: str = "Correct!"
    on_incorrect: str = "Try again."
    misconception_feedback: List[MisconceptionFeedback] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_feedback(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # LLM produces misconception_feedback as list of strings
        mf = data.get("misconception_feedback", [])
        if mf and isinstance(mf[0], str):
            data["misconception_feedback"] = [
                {"trigger": item.split(":")[0].strip() if ":" in item else "general",
                 "message": item.split(":", 1)[1].strip() if ":" in item else item}
                for item in mf
            ]
        return data
    completion_message: Optional[str] = None
    streak_messages: Optional[Dict[int, str]] = None  # {3: "Hat trick!", 5: "On fire!"}
    varied_correct_messages: List[str] = Field(default_factory=lambda: [
        "Correct!", "Well done!", "Exactly right!", "Perfect!"
    ])
    varied_incorrect_messages: List[str] = Field(default_factory=lambda: [
        "Try again!", "Not quite.", "Close, but not this one."
    ])


# ---------------------------------------------------------------------------
# Animations (#8)
# ---------------------------------------------------------------------------

class AnimationDesign(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "pulse"  # pulse, glow, scale, shake, fade, bounce, confetti, path_draw
    duration_ms: int = 400
    easing: str = "ease-out"
    color: Optional[str] = None
    intensity: Optional[float] = None  # 0-1
    delay_ms: int = 0
    particle_config: Optional[Dict[str, Any]] = None  # For confetti: {count, spread, colors, gravity}


class MechanicAnimations(BaseModel):
    """Per-event animation specs for a mechanic."""
    model_config = ConfigDict(extra="allow")

    on_correct: Optional[AnimationDesign] = None
    on_incorrect: Optional[AnimationDesign] = None
    on_completion: Optional[AnimationDesign] = None
    on_hover: Optional[AnimationDesign] = None
    on_drag: Optional[AnimationDesign] = None


# ---------------------------------------------------------------------------
# Media Assets (#9) — scene-level, independent of zones
# ---------------------------------------------------------------------------

class MotionPathDesign(BaseModel):
    """Keyframe animation for a media asset."""
    model_config = ConfigDict(extra="allow")

    keyframes: List[Dict[str, Any]] = Field(default_factory=list)
    trigger: str = "on_scene_enter"
    loop: bool = False
    easing: str = "ease-in-out"


class MediaAssetDesign(BaseModel):
    """A media asset in the scene — can be independent of zones."""
    model_config = ConfigDict(extra="allow")

    id: str
    description: str = ""
    asset_type: str = "image"  # image, gif, sprite, css_animation, svg, lottie, overlay
    placement: str = "decoration"  # background, overlay, zone, decoration
    layer: int = 0  # Z-order (-10 to 10)
    generation_prompt: Optional[str] = None

    # Trigger: when does this asset activate? (independent game logic)
    trigger: Optional[str] = None  # on_scene_enter, on_complete, on_correct, on_mechanic_start, always, never
    trigger_config: Dict[str, Any] = Field(default_factory=dict)

    # Animation for this asset
    motion_path: Optional[MotionPathDesign] = None

    # Dimensional hints for generation
    width: Optional[int] = None
    height: Optional[int] = None
    style: Optional[str] = None


# ---------------------------------------------------------------------------
# Sound Design
# ---------------------------------------------------------------------------

class SoundDesign(BaseModel):
    """A sound effect bound to a game event."""
    model_config = ConfigDict(extra="allow")

    event: str  # correct, incorrect, drag_start, drop, completion, hint_used, timer_warning, streak, scene_transition
    description: str = ""  # "bright chime, 200ms, satisfying"
    preset: Optional[str] = None  # Use a built-in preset instead of generating
    volume: float = 0.5


# ---------------------------------------------------------------------------
# Temporal Intelligence (#10)
# ---------------------------------------------------------------------------

class TemporalConstraintDesign(BaseModel):
    model_config = ConfigDict(extra="allow")

    zone_a: str  # label text
    zone_b: str  # label text
    constraint_type: str  # before, after, mutex, concurrent, sequence


class TemporalSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    reveal_order: List[str] = Field(default_factory=list)  # Zone labels in reveal order
    constraints: List[TemporalConstraintDesign] = Field(default_factory=list)
    stagger_delay_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# Transitions (#11)
# ---------------------------------------------------------------------------

class MechanicTransitionSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_mechanic: str  # mechanic type
    to_mechanic: str
    trigger: str = "all_complete"  # score_threshold, all_complete, all_zones_labeled, time_elapsed, user_choice
    threshold: Optional[float] = None
    animation: str = "fade"  # fade, slide, zoom, none
    message: Optional[str] = None


class SceneTransitionSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_scene: int
    to_scene: int
    trigger: str = "all_complete"
    threshold: Optional[float] = None
    animation: str = "slide_left"  # zoom_in, slide_left, slide_right, fade, reveal
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Difficulty & Scaffolding (#12)
# ---------------------------------------------------------------------------

class DifficultySpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    approach: str = ""  # "Progressive: Scene 1 tests recall, Scene 2 tests understanding..."
    initial_level: str = "medium"  # easy, medium, hard
    hint_enabled: bool = True
    scaffolding: Optional[str] = None  # "First 2 labels pre-placed as examples"
    pre_placed_labels: List[str] = Field(default_factory=list)  # Zone labels to pre-place


# ---------------------------------------------------------------------------
# Mechanic Design (combines #4, #5, #6, #7, #8)
# ---------------------------------------------------------------------------

class MechanicDesign(BaseModel):
    """One interaction mechanic within a scene."""
    model_config = ConfigDict(extra="allow")

    type: str  # drag_drop, trace_path, click_to_identify, hierarchical, sequencing, sorting_categories, memory_match, branching_scenario, compare_contrast, timed_challenge, description_matching
    description: str = ""

    # Which labels this mechanic uses (subset of scene's zone_labels)
    zone_labels_used: List[str] = Field(default_factory=list)

    # Mode-specific config (populate only the relevant one)
    path_config: Optional[PathDesign] = None
    click_config: Optional[ClickDesign] = None
    sequence_config: Optional[SequenceDesign] = None
    sorting_config: Optional[SortingDesign] = None
    branching_config: Optional[BranchingDesign] = None
    compare_config: Optional[CompareDesign] = None
    memory_config: Optional[MemoryMatchDesign] = None
    timed_config: Optional[TimedDesign] = None
    description_match_config: Optional[DescriptionMatchDesign] = None

    # Scoring
    scoring: MechanicScoring = Field(default_factory=MechanicScoring)

    # Feedback
    feedback: MechanicFeedback = Field(default_factory=MechanicFeedback)

    # Animations
    animations: Optional[MechanicAnimations] = None


# ---------------------------------------------------------------------------
# Scene Design (combines #1, #2, #4, #9, #10)
# ---------------------------------------------------------------------------

class SceneDesign(BaseModel):
    """One visual context — one primary diagram/image with N mechanics."""
    model_config = ConfigDict(extra="allow")

    scene_number: int
    title: str = ""
    learning_goal: str = ""
    narrative_intro: Optional[str] = None

    # Visual (#1)
    visual: SceneVisualSpec = Field(default_factory=SceneVisualSpec)

    @model_validator(mode="before")
    @classmethod
    def _coerce_scene(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # visual as string → SceneVisualSpec
        v = data.get("visual")
        if isinstance(v, str):
            data["visual"] = {"description": v}
        # zone_labels_in_scene → zone_labels
        if "zone_labels_in_scene" in data and "zone_labels" not in data:
            data["zone_labels"] = data.pop("zone_labels_in_scene")
        # visual_description → visual
        if "visual_description" in data and "visual" not in data:
            data["visual"] = {"description": data.pop("visual_description")}
        return data

    # Zones (#2)
    zone_labels: List[str] = Field(default_factory=list)
    zone_specs: List[ZoneSpec] = Field(default_factory=list)

    # Mechanics (#4, in order)
    mechanics: List[MechanicDesign] = Field(default_factory=list)
    mechanic_transitions: List[MechanicTransitionSpec] = Field(default_factory=list)

    # Media assets (#9, scene-level, independent of zones)
    media_assets: List[MediaAssetDesign] = Field(default_factory=list)

    # Sounds
    sounds: List[SoundDesign] = Field(default_factory=list)

    # Temporal (#10)
    temporal: Optional[TemporalSpec] = None

    # Scene-level scoring
    max_score: int = 100
    time_limit_seconds: Optional[int] = None


# ---------------------------------------------------------------------------
# GameDesignV3 (top-level, combines everything)
# ---------------------------------------------------------------------------

class GameDesignV3(BaseModel):
    """Complete Game Design Document — the single source of truth.

    Output by the game_designer ReAct agent.
    Consumed by design_validator, asset_spec_builder, blueprint_assembler.
    """
    model_config = ConfigDict(extra="allow")

    # Identity
    title: str = ""
    narrative_intro: str = ""
    pedagogical_reasoning: str = ""
    learning_objectives: List[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 5

    # Theme (#14)
    theme: ThemeSpec = Field(default_factory=ThemeSpec)

    # Labels (#3, global)
    labels: LabelDesign = Field(default_factory=LabelDesign)

    # Scenes (each is one visual context)
    scenes: List[SceneDesign] = Field(default_factory=list)

    # Scene transitions (#11)
    scene_transitions: List[SceneTransitionSpec] = Field(default_factory=list)

    # Difficulty (#12)
    difficulty: DifficultySpec = Field(default_factory=DifficultySpec)

    # Global scoring
    total_max_score: int = 0
    star_thresholds: List[float] = Field(default_factory=lambda: [0.6, 0.8, 1.0])

    # Global sounds (apply across all scenes)
    global_sounds: List[SoundDesign] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_llm_output(cls, data: Any) -> Any:
        """Coerce common LLM output patterns into the expected schema."""
        if not isinstance(data, dict):
            return data

        # LLM wraps output under a key like "game_design" or "design"
        if "game_design" in data and isinstance(data["game_design"], dict) and "title" not in data:
            data = data["game_design"]
        elif "design" in data and isinstance(data["design"], dict) and "title" not in data:
            data = data["design"]

        # theme as string → ThemeSpec
        theme = data.get("theme")
        if isinstance(theme, str):
            data["theme"] = {"visual_tone": theme}

        # difficulty as string → DifficultySpec
        difficulty = data.get("difficulty")
        if isinstance(difficulty, str):
            data["difficulty"] = {"approach": difficulty}

        # difficulty_approach as string → merge into difficulty
        if "difficulty_approach" in data and isinstance(data.get("difficulty_approach"), str):
            if not isinstance(data.get("difficulty"), dict):
                data["difficulty"] = {}
            if isinstance(data["difficulty"], dict):
                data["difficulty"]["approach"] = data.pop("difficulty_approach")

        # labels as list → LabelDesign
        labels = data.get("labels")
        if isinstance(labels, list):
            data["labels"] = {"zone_labels": labels}

        # estimated_duration_minutes as string → int
        edm = data.get("estimated_duration_minutes")
        if isinstance(edm, str):
            try:
                data["estimated_duration_minutes"] = int(edm.split()[0])
            except (ValueError, IndexError):
                data["estimated_duration_minutes"] = 5

        # scenes may have "visual_description" instead of "visual"
        for scene in data.get("scenes", []):
            if isinstance(scene, dict):
                if "visual_description" in scene and "visual" not in scene:
                    scene["visual"] = {"description": scene.pop("visual_description")}
                # interaction_mode → wrap as mechanic if mechanics empty
                if "interaction_mode" in scene and not scene.get("mechanics"):
                    mode = scene.pop("interaction_mode")
                    scene["mechanics"] = [{"type": mode}]
                # zone_labels_in_scene → zone_labels
                if "zone_labels_in_scene" in scene and "zone_labels" not in scene:
                    scene["zone_labels"] = scene.pop("zone_labels_in_scene")
                # scoring/feedback at scene level → propagate to mechanics
                scene_scoring = scene.pop("scoring", None)
                scene_feedback = scene.pop("feedback", None)
                if scene_scoring or scene_feedback:
                    for mech in scene.get("mechanics", []):
                        if isinstance(mech, dict):
                            if scene_scoring and not mech.get("scoring"):
                                mech["scoring"] = scene_scoring
                            if scene_feedback and not mech.get("feedback"):
                                mech["feedback"] = scene_feedback

        return data

    def compute_total_max_score(self) -> int:
        """Sum max_score across all scenes."""
        return sum(s.max_score for s in self.scenes)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

VALID_MECHANIC_TYPES = {
    "drag_drop", "trace_path", "click_to_identify", "hierarchical",
    "sequencing", "sorting_categories", "memory_match", "branching_scenario",
    "compare_contrast", "timed_challenge", "description_matching",
}

VALID_TRIGGERS = {
    "score_threshold", "all_complete", "all_zones_labeled",
    "time_elapsed", "user_choice", "hierarchy_level_complete",
    "path_complete", "percentage_complete", "specific_zones",
}

VALID_TRANSITION_ANIMATIONS = {
    "fade", "slide_left", "slide_right", "zoom_in", "zoom_out",
    "reveal", "none",
}

VALID_ANIMATION_TYPES = {
    "pulse", "glow", "scale", "shake", "fade", "bounce", "confetti", "path_draw",
}


# ---------------------------------------------------------------------------
# GameDesignV3Slim — Scoped-down version for the new v3 pipeline
# ---------------------------------------------------------------------------
# The game_designer_v3 in the new pipeline produces this SLIM version.
# Scoring, feedback, mechanic configs, animations → moved to scene_architect_v3
# and interaction_designer_v3 (Phases 2/3).

class SlimMechanicRef(BaseModel):
    """Mechanic type with optional config hints for downstream agents."""
    model_config = ConfigDict(extra="allow")

    type: str  # drag_drop, trace_path, click_to_identify, etc.
    config_hint: Dict[str, Any] = Field(default_factory=dict)  # Summary of key config data
    zone_labels_used: List[str] = Field(default_factory=list)  # Which labels this mechanic uses

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"type": data}
        return data


class SlimSceneDesign(BaseModel):
    """Scene in the slim design — just structure, no configs."""
    model_config = ConfigDict(extra="allow")

    scene_number: int
    title: str = ""
    learning_goal: str = ""
    visual_description: str = ""
    mechanics: List[SlimMechanicRef] = Field(default_factory=list)
    zone_labels_in_scene: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # visual → visual_description
        v = data.get("visual")
        if isinstance(v, dict):
            data.setdefault("visual_description", v.get("description", ""))
        elif isinstance(v, str):
            data.setdefault("visual_description", v)
        # zone_labels → zone_labels_in_scene
        if "zone_labels" in data and "zone_labels_in_scene" not in data:
            data["zone_labels_in_scene"] = data.pop("zone_labels")
        return data


class SlimSceneTransition(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_scene: int
    to_scene: int
    trigger: str = "all_complete"


class GameDesignV3Slim(BaseModel):
    """Scoped-down game design for the new v3 pipeline.

    Produced by game_designer_v3 Phase 1.
    Contains ONLY creative/structural decisions. Scoring, feedback,
    mechanic configs, animations are produced by downstream agents.
    """
    model_config = ConfigDict(extra="allow")

    title: str = ""
    pedagogical_reasoning: str = ""
    learning_objectives: List[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 5

    # Theme
    theme: ThemeSpec = Field(default_factory=ThemeSpec)

    # Labels (global)
    labels: LabelDesign = Field(default_factory=LabelDesign)

    # Scenes (structure only)
    scenes: List[SlimSceneDesign] = Field(default_factory=list)

    # Scene transitions (high level)
    scene_transitions: List[SlimSceneTransition] = Field(default_factory=list)

    # Difficulty
    difficulty: DifficultySpec = Field(default_factory=DifficultySpec)

    @model_validator(mode="before")
    @classmethod
    def _coerce_slim(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Unwrap nested keys
        if "game_design" in data and isinstance(data["game_design"], dict) and "title" not in data:
            data = data["game_design"]
        elif "design" in data and isinstance(data["design"], dict) and "title" not in data:
            data = data["design"]
        # theme as string
        theme = data.get("theme")
        if isinstance(theme, str):
            data["theme"] = {"visual_tone": theme}
        # difficulty as string
        difficulty = data.get("difficulty")
        if isinstance(difficulty, str):
            data["difficulty"] = {"approach": difficulty}
        # labels as list
        labels = data.get("labels")
        if isinstance(labels, list):
            data["labels"] = {"zone_labels": labels}
        # estimated_duration_minutes as string
        edm = data.get("estimated_duration_minutes")
        if isinstance(edm, str):
            try:
                data["estimated_duration_minutes"] = int(edm.split()[0])
            except (ValueError, IndexError):
                data["estimated_duration_minutes"] = 5
        return data

    def summary(self) -> str:
        """Generate structured summary for downstream agents."""
        scene_count = len(self.scenes)
        mechanic_types = sorted(set(m.type for s in self.scenes for m in s.mechanics))
        label_count = len(self.labels.zone_labels) if self.labels else 0
        distractor_count = len(self.labels.distractor_labels) if self.labels else 0
        return (
            f"{scene_count}-scene game | "
            f"mechanics: {', '.join(mechanic_types)} | "
            f"{label_count} zone labels, {distractor_count} distractors | "
            f"difficulty: {self.difficulty.approach if self.difficulty else 'N/A'}"
        )


def validate_slim_game_design(design: GameDesignV3Slim) -> List[str]:
    """Validation for slim design (Phase 1 scope only)."""
    issues: List[str] = []

    if not design.title:
        issues.append("Missing game title")
    if not design.scenes:
        issues.append("No scenes defined")
        return issues

    all_zone_labels = set(design.labels.zone_labels) if design.labels else set()

    if len(all_zone_labels) < 3:
        issues.append(f"Only {len(all_zone_labels)} zone labels (need >= 3)")

    scene_numbers = []
    for scene in design.scenes:
        scene_numbers.append(scene.scene_number)
        if not scene.mechanics:
            issues.append(f"Scene {scene.scene_number}: no mechanics")
        for mech in scene.mechanics:
            if mech.type not in VALID_MECHANIC_TYPES:
                issues.append(f"Scene {scene.scene_number}: unknown mechanic '{mech.type}'")

    # Sequential scene numbers
    if sorted(scene_numbers) != list(range(1, len(design.scenes) + 1)):
        issues.append(f"Scene numbers not sequential: {sorted(scene_numbers)}")

    # Hierarchy validation
    if design.labels and design.labels.hierarchy and design.labels.hierarchy.enabled:
        all_labels = all_zone_labels | set(design.labels.group_only_labels or [])
        for group in design.labels.hierarchy.groups:
            if group.parent not in all_labels:
                issues.append(f"Hierarchy parent '{group.parent}' not in labels")
            for child in group.children:
                if child not in all_labels:
                    issues.append(f"Hierarchy child '{child}' not in labels")

    # Scene transitions reference valid scenes
    valid_scenes = set(scene_numbers)
    for trans in design.scene_transitions:
        if trans.from_scene not in valid_scenes:
            issues.append(f"Transition from non-existent scene {trans.from_scene}")
        if trans.to_scene not in valid_scenes:
            issues.append(f"Transition to non-existent scene {trans.to_scene}")

    return issues


def validate_game_design(design: GameDesignV3) -> List[str]:
    """Rule-based validation. Returns list of issues (empty = valid)."""
    issues: List[str] = []

    if not design.title:
        issues.append("Game design must have a title")

    if not design.scenes:
        issues.append("Game design must have at least one scene")

    all_zone_labels = set(design.labels.zone_labels)
    all_group_labels = set(design.labels.group_only_labels)
    all_labels = all_zone_labels | all_group_labels

    # Validate hierarchy references
    if design.labels.hierarchy and design.labels.hierarchy.enabled:
        for group in design.labels.hierarchy.groups:
            if group.parent not in all_labels:
                issues.append(f"Hierarchy parent '{group.parent}' not in labels")
            for child in group.children:
                if child not in all_labels:
                    issues.append(f"Hierarchy child '{child}' not in labels")

    # Validate each scene
    for scene in design.scenes:
        scene_labels = set(scene.zone_labels)

        # Scene zone_labels must be subset of global labels
        unknown = scene_labels - all_labels
        if unknown:
            issues.append(f"Scene {scene.scene_number}: zone_labels {unknown} not in global labels")

        if not scene.mechanics:
            issues.append(f"Scene {scene.scene_number}: must have at least one mechanic")

        for mech in scene.mechanics:
            # Mechanic type must be valid
            if mech.type not in VALID_MECHANIC_TYPES:
                issues.append(f"Scene {scene.scene_number}: unknown mechanic type '{mech.type}'")

            # Mechanic zone_labels_used must be subset of scene zone_labels
            mech_labels = set(mech.zone_labels_used)
            unknown_mech = mech_labels - scene_labels
            if unknown_mech:
                issues.append(
                    f"Scene {scene.scene_number}, mechanic '{mech.type}': "
                    f"zone_labels_used {unknown_mech} not in scene zone_labels"
                )

            # trace_path must have path_config with waypoints
            if mech.type == "trace_path" and (not mech.path_config or not mech.path_config.waypoints):
                issues.append(f"Scene {scene.scene_number}: trace_path mechanic needs path_config.waypoints")

            # click_to_identify must have click_config
            if mech.type == "click_to_identify" and not mech.click_config:
                issues.append(f"Scene {scene.scene_number}: click_to_identify needs click_config")

            # sequencing must have sequence_config
            if mech.type == "sequencing" and not mech.sequence_config:
                issues.append(f"Scene {scene.scene_number}: sequencing needs sequence_config")

            # sorting must have sorting_config
            if mech.type == "sorting_categories" and not mech.sorting_config:
                issues.append(f"Scene {scene.scene_number}: sorting_categories needs sorting_config")

        # Validate mechanic transitions reference valid types in this scene
        scene_mech_types = {m.type for m in scene.mechanics}
        for trans in scene.mechanic_transitions:
            if trans.from_mechanic not in scene_mech_types:
                issues.append(
                    f"Scene {scene.scene_number}: transition from '{trans.from_mechanic}' "
                    f"not in scene mechanics"
                )
            if trans.to_mechanic not in scene_mech_types:
                issues.append(
                    f"Scene {scene.scene_number}: transition to '{trans.to_mechanic}' "
                    f"not in scene mechanics"
                )

    # Validate scene transitions
    scene_numbers = {s.scene_number for s in design.scenes}
    for trans in design.scene_transitions:
        if trans.from_scene not in scene_numbers:
            issues.append(f"Scene transition from non-existent scene {trans.from_scene}")
        if trans.to_scene not in scene_numbers:
            issues.append(f"Scene transition to non-existent scene {trans.to_scene}")

    return issues
