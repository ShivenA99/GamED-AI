"""Creative Design schemas — output of the Scene Designer (Phase 1b).

Per-scene and per-mechanic creative direction: HOW it looks/feels.
This is the critical missing piece from V3 — visual style, layout, narrative integration,
interaction personality, and content generation guidance for each mechanic.

The scene designer produces SceneCreativeDesign (one per scene).
Each contains MechanicCreativeDesign entries (one per mechanic in that scene).
"""

from typing import Optional
from pydantic import BaseModel, Field


class ImageSpec(BaseModel):
    """Rich image requirements for the asset pipeline."""

    description: str
    must_include_structures: list[str] = Field(default_factory=list)
    style: str = "clean_educational"
    annotation_preference: str = "clean_unlabeled"
    color_direction: str = ""
    spatial_guidance: str = ""


class MechanicCreativeDesign(BaseModel):
    """Rich creative direction for one mechanic, produced by the scene designer.

    This replaces the thin ContentBrief from V3. Every visual config field the
    frontend reads is seeded here and flows through the content generator
    into the blueprint.
    """

    mechanic_type: str

    # Visual integration
    visual_style: str
    card_type: str = "text_only"
    layout_mode: str = "default"
    connector_style: str = "arrow"
    color_direction: str = ""

    # Narrative integration
    instruction_text: str
    instruction_tone: str = "educational"
    narrative_hook: str = ""

    # Interaction personality
    hint_strategy: str = "progressive"
    feedback_style: str = "encouraging"
    difficulty_curve: str = "gradual"

    # Content generation guidance (replaces ContentBrief)
    generation_goal: str
    key_concepts: list[str] = Field(default_factory=list)
    pedagogical_focus: str = ""

    # Mechanic-specific creative hints
    sequence_topic: Optional[str] = None
    category_names: Optional[list[str]] = None
    comparison_subjects: Optional[list[str]] = None
    narrative_premise: Optional[str] = None
    description_source: Optional[str] = None
    path_process: Optional[str] = None
    prompt_style: Optional[str] = None
    match_type: Optional[str] = None

    # Visual asset hints
    needs_item_images: bool = False
    item_image_style: Optional[str] = None


class SceneCreativeDesign(BaseModel):
    """Deep creative design for one scene, produced by the scene designer.

    Contains the visual vision, image specs, and per-mechanic creative designs.
    """

    scene_id: str
    title: str

    # Visual design
    visual_concept: str
    color_palette_direction: str = ""
    spatial_layout: str = ""
    atmosphere: str = ""

    # Rich image specs (replaces simple image_description)
    image_spec: Optional[ImageSpec] = None
    second_image_spec: Optional[ImageSpec] = None  # For compare_contrast

    # Per-mechanic creative designs
    mechanic_designs: list[MechanicCreativeDesign] = Field(min_length=1)

    # Scene-level narrative
    scene_narrative: str = ""
    transition_narrative: str = ""

    model_config = {"extra": "allow"}
