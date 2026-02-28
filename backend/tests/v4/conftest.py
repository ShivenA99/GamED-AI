"""Shared test fixtures for V4 pipeline tests."""

import pytest
from app.v4.schemas.game_plan import (
    GamePlan, ScenePlan, MechanicPlan, ContentBrief, ImageSpec, MechanicConnection,
)


# ── Game Plans ───────────────────────────────────────────────────

@pytest.fixture
def single_scene_drag_drop() -> GamePlan:
    """Single scene, single mechanic: drag_drop."""
    return GamePlan(
        title="Plant Cell Parts",
        subject="Biology",
        difficulty="beginner",
        all_zone_labels=["Nucleus", "Cell Wall", "Mitochondria"],
        distractor_labels=["Ribosome"],
        scenes=[ScenePlan(
            scene_id="scene_1",
            title="Label the Plant Cell",
            learning_goal="Identify organelles",
            zone_labels=["Nucleus", "Cell Wall", "Mitochondria"],
            needs_diagram=True,
            image_spec=ImageSpec(description="Plant cell diagram"),
            mechanics=[MechanicPlan(
                mechanic_id="m1",
                mechanic_type="drag_drop",
                zone_labels_used=["Nucleus", "Cell Wall", "Mitochondria"],
                instruction_text="Drag labels to the correct organelles",
                content_brief=ContentBrief(
                    description="Label main organelles",
                    key_concepts=["organelles", "cell structure"],
                    dk_fields_needed=["canonical_labels"],
                ),
                expected_item_count=3,
                points_per_item=10,
            )],
        )],
    )


@pytest.fixture
def multi_scene_plan() -> GamePlan:
    """Multi-scene, 3 mechanics with connections."""
    return GamePlan(
        title="Heart Anatomy",
        subject="Biology",
        difficulty="intermediate",
        all_zone_labels=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle", "Aorta"],
        scenes=[
            ScenePlan(
                scene_id="scene_1",
                title="Label Heart Chambers",
                learning_goal="Identify the four chambers",
                zone_labels=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle", "Aorta"],
                needs_diagram=True,
                image_spec=ImageSpec(description="Heart diagram"),
                mechanics=[
                    MechanicPlan(
                        mechanic_id="m1", mechanic_type="drag_drop",
                        zone_labels_used=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                        instruction_text="Drag labels",
                        content_brief=ContentBrief(description="Label chambers", key_concepts=["chambers"]),
                        expected_item_count=4, points_per_item=10,
                    ),
                    MechanicPlan(
                        mechanic_id="m2", mechanic_type="trace_path",
                        zone_labels_used=["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle", "Aorta"],
                        instruction_text="Trace blood flow",
                        content_brief=ContentBrief(
                            description="Blood flow path", key_concepts=["circulation"],
                            dk_fields_needed=["flow_sequences"],
                        ),
                        expected_item_count=1, points_per_item=20,
                    ),
                ],
                mechanic_connections=[
                    MechanicConnection(from_mechanic_id="m1", to_mechanic_id="m2", trigger_hint="completion"),
                ],
            ),
            ScenePlan(
                scene_id="scene_2",
                title="Cardiac Cycle",
                learning_goal="Order the cardiac cycle phases",
                zone_labels=[],
                needs_diagram=False,
                mechanics=[MechanicPlan(
                    mechanic_id="m3", mechanic_type="sequencing",
                    zone_labels_used=[],
                    instruction_text="Order the cardiac cycle",
                    content_brief=ContentBrief(
                        description="Cardiac cycle steps", key_concepts=["systole", "diastole"],
                        mechanic_specific_hints={"sequence_type": "cyclic"},
                    ),
                    expected_item_count=4, points_per_item=10,
                )],
            ),
        ],
    )


@pytest.fixture
def content_only_plan() -> GamePlan:
    """Content-only scene: sequencing + sorting, no diagram."""
    return GamePlan(
        title="Cell Division Phases",
        subject="Biology",
        difficulty="intermediate",
        all_zone_labels=[],
        scenes=[ScenePlan(
            scene_id="scene_1",
            title="Sort and Sequence",
            learning_goal="Understand mitosis phases",
            zone_labels=[],
            needs_diagram=False,
            mechanics=[
                MechanicPlan(
                    mechanic_id="m1", mechanic_type="sequencing",
                    zone_labels_used=[],
                    instruction_text="Order the mitosis phases",
                    content_brief=ContentBrief(
                        description="Mitosis phases", key_concepts=["prophase", "metaphase"],
                        mechanic_specific_hints={"sequence_type": "ordered"},
                    ),
                    expected_item_count=4, points_per_item=10,
                ),
                MechanicPlan(
                    mechanic_id="m2", mechanic_type="sorting_categories",
                    zone_labels_used=[],
                    instruction_text="Sort items into phases",
                    content_brief=ContentBrief(
                        description="Sort events into phases", key_concepts=["mitosis vs meiosis"],
                        mechanic_specific_hints={"categories": ["mitosis", "meiosis"]},
                    ),
                    expected_item_count=6, points_per_item=5,
                ),
            ],
            mechanic_connections=[
                MechanicConnection(from_mechanic_id="m1", to_mechanic_id="m2", trigger_hint="completion"),
            ],
        )],
    )


# ── Mechanic Contents ────────────────────────────────────────────

@pytest.fixture
def drag_drop_content() -> dict:
    return {
        "mechanic_id": "m1", "scene_id": "scene_1", "mechanic_type": "drag_drop",
        "content": {"labels": ["Nucleus", "Cell Wall", "Mitochondria"], "distractor_labels": ["Ribosome"]},
    }


@pytest.fixture
def sequencing_content() -> dict:
    return {
        "mechanic_id": "m3", "scene_id": "scene_2", "mechanic_type": "sequencing",
        "content": {
            "items": [
                {"id": "s1", "content": "Prophase", "explanation": "Chromosomes condense"},
                {"id": "s2", "content": "Metaphase", "explanation": "Align at equator"},
                {"id": "s3", "content": "Anaphase", "explanation": "Sister chromatids separate"},
                {"id": "s4", "content": "Telophase", "explanation": "Nuclear envelopes reform"},
            ],
            "correct_order": ["s1", "s2", "s3", "s4"],
            "sequence_type": "ordered",
            "layout_mode": "vertical_list",
        },
    }


@pytest.fixture
def sorting_content() -> dict:
    return {
        "mechanic_id": "m2", "scene_id": "scene_1", "mechanic_type": "sorting_categories",
        "content": {
            "categories": [
                {"id": "cat1", "label": "Mitosis", "color": "#4A90D9"},
                {"id": "cat2", "label": "Meiosis", "color": "#E74C3C"},
            ],
            "items": [
                {"id": "i1", "content": "2 daughter cells", "correctCategoryId": "cat1"},
                {"id": "i2", "content": "4 daughter cells", "correctCategoryId": "cat2"},
                {"id": "i3", "content": "Identical copies", "correctCategoryId": "cat1"},
                {"id": "i4", "content": "Genetic variation", "correctCategoryId": "cat2"},
                {"id": "i5", "content": "Growth and repair", "correctCategoryId": "cat1"},
                {"id": "i6", "content": "Gamete production", "correctCategoryId": "cat2"},
            ],
        },
    }


@pytest.fixture
def memory_match_content() -> dict:
    return {
        "mechanic_id": "m1", "scene_id": "scene_1", "mechanic_type": "memory_match",
        "content": {
            "pairs": [
                {"id": "p1", "front": "Nucleus", "back": "Control center"},
                {"id": "p2", "front": "Mitochondria", "back": "Powerhouse"},
                {"id": "p3", "front": "Cell Wall", "back": "Rigid outer layer"},
            ],
            "game_variant": "classic",
            "gridSize": [2, 3],
        },
    }


@pytest.fixture
def branching_content() -> dict:
    return {
        "mechanic_id": "m1", "scene_id": "scene_1", "mechanic_type": "branching_scenario",
        "content": {
            "nodes": [
                {
                    "id": "n1", "question": "A patient has chest pain. What do you check first?",
                    "options": [
                        {"id": "o1", "text": "Blood pressure", "nextNodeId": "n2", "isCorrect": True, "points": 10},
                        {"id": "o2", "text": "Temperature", "nextNodeId": "n3", "isCorrect": False, "points": 0},
                    ],
                },
                {
                    "id": "n2", "question": "BP is elevated. Next step?",
                    "options": [
                        {"id": "o3", "text": "ECG", "nextNodeId": "n4", "isCorrect": True, "points": 10},
                    ],
                },
                {"id": "n3", "question": "Temperature is normal.", "isEndNode": True, "endMessage": "Wrong path"},
                {"id": "n4", "question": "ECG shows abnormality.", "isEndNode": True, "endMessage": "Correct path!"},
            ],
            "startNodeId": "n1",
        },
    }


@pytest.fixture
def click_to_identify_content() -> dict:
    return {
        "mechanic_id": "m1", "scene_id": "scene_1", "mechanic_type": "click_to_identify",
        "content": {
            "prompts": [
                {"text": "Click the part that controls the cell", "target_label": "Nucleus", "explanation": "The nucleus is the control center", "order": 0},
                {"text": "Click the energy producer", "target_label": "Mitochondria", "explanation": "Mitochondria produce ATP", "order": 1},
            ],
        },
    }


@pytest.fixture
def trace_path_content() -> dict:
    return {
        "mechanic_id": "m2", "scene_id": "scene_1", "mechanic_type": "trace_path",
        "content": {
            "paths": [{
                "label": "Blood Flow",
                "description": "Trace the path of blood through the heart",
                "color": "#E74C3C",
                "requiresOrder": True,
                "waypoints": [
                    {"label": "Right Atrium", "order": 0},
                    {"label": "Right Ventricle", "order": 1},
                    {"label": "Left Atrium", "order": 2},
                    {"label": "Left Ventricle", "order": 3},
                    {"label": "Aorta", "order": 4},
                ],
            }],
            "particleSpeed": "medium",
        },
    }


@pytest.fixture
def description_matching_content() -> dict:
    return {
        "mechanic_id": "m1", "scene_id": "scene_1", "mechanic_type": "description_matching",
        "content": {
            "descriptions": {
                "Nucleus": "Control center of the cell",
                "Mitochondria": "Generates energy through cellular respiration",
                "Cell Wall": "Provides structural support and protection",
            },
            "mode": "click_zone",
        },
    }


# ── Interaction Results ──────────────────────────────────────────

@pytest.fixture
def interaction_result() -> dict:
    return {
        "scene_id": "scene_1",
        "mechanic_scoring": {
            "m1": {"strategy": "per_correct", "points_per_correct": 10, "max_score": 30, "partial_credit": True},
        },
        "mechanic_feedback": {
            "m1": {"on_correct": "Great!", "on_incorrect": "Try again", "on_completion": "Well done!", "misconceptions": []},
        },
        "mode_transitions": [],
    }


# ── Asset Results ────────────────────────────────────────────────

@pytest.fixture
def asset_result() -> dict:
    return {
        "scene_id": "scene_1",
        "status": "success",
        "diagram_url": "https://example.com/plant_cell.png",
        "zones": [
            {"id": "z1", "label": "Nucleus", "points": [[30, 40], [40, 40], [40, 50], [30, 50]]},
            {"id": "z2", "label": "Cell Wall", "points": [[5, 5], [95, 5], [95, 95], [5, 95]]},
            {"id": "z3", "label": "Mitochondria", "points": [[60, 60], [70, 60], [70, 70], [60, 70]]},
        ],
        "match_quality": 0.95,
    }
