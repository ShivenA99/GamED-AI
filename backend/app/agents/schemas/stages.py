"""Pydantic JSON schemas for core pipeline stages."""

from pydantic import TypeAdapter

from app.agents.state import (
    PedagogicalContext,
    TemplateSelection,
    GamePlan,
    SceneData,
    StoryData
)


def get_pedagogical_context_schema():
    return TypeAdapter(PedagogicalContext).json_schema()


def get_template_selection_schema():
    return TypeAdapter(TemplateSelection).json_schema()


def get_game_plan_schema():
    return TypeAdapter(GamePlan).json_schema()


def get_scene_data_schema():
    return TypeAdapter(SceneData).json_schema()


def get_story_data_schema():
    return TypeAdapter(StoryData).json_schema()
