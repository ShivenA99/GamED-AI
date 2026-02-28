"""Tests for game plan validator."""

import pytest
from app.v4.schemas.game_plan import (
    GamePlan, ScenePlan, MechanicPlan, ContentBrief, MechanicConnection,
)
from app.v4.validators.game_plan_validator import validate_game_plan


class TestValidSingleScene:
    def test_valid_drag_drop(self, single_scene_drag_drop):
        result = validate_game_plan(single_scene_drag_drop)
        assert result.passed
        assert single_scene_drag_drop.scenes[0].mechanics[0].max_score == 30
        assert single_scene_drag_drop.scenes[0].scene_max_score == 30
        assert single_scene_drag_drop.total_max_score == 30

    def test_valid_content_only(self, content_only_plan):
        result = validate_game_plan(content_only_plan)
        assert result.passed
        assert content_only_plan.total_max_score == 70  # 4*10 + 6*5


class TestValidMultiScene:
    def test_valid_multi_scene(self, multi_scene_plan):
        result = validate_game_plan(multi_scene_plan)
        assert result.passed
        assert multi_scene_plan.scenes[0].scene_max_score == 60  # 4*10 + 1*20
        assert multi_scene_plan.scenes[1].scene_max_score == 40  # 4*10
        assert multi_scene_plan.total_max_score == 100


class TestZoneLabelIntegrity:
    def test_scene_label_not_in_all(self):
        plan = GamePlan(
            title="Test", subject="Test",
            all_zone_labels=["A", "B"],
            scenes=[ScenePlan(
                scene_id="s1", title="T", learning_goal="G",
                zone_labels=["A", "C"],  # C not in all_zone_labels
                mechanics=[MechanicPlan(
                    mechanic_id="m1", mechanic_type="drag_drop",
                    zone_labels_used=["A"],
                    instruction_text="T", content_brief=ContentBrief(description="D", key_concepts=["K"]),
                    expected_item_count=1, points_per_item=10,
                )],
            )],
        )
        result = validate_game_plan(plan)
        assert not result.passed
        assert any("not in all_zone_labels" in i.message for i in result.errors)

    def test_mechanic_label_not_in_scene(self):
        plan = GamePlan(
            title="Test", subject="Test",
            all_zone_labels=["A", "B", "C"],
            scenes=[ScenePlan(
                scene_id="s1", title="T", learning_goal="G",
                zone_labels=["A", "B"],
                mechanics=[MechanicPlan(
                    mechanic_id="m1", mechanic_type="drag_drop",
                    zone_labels_used=["A", "C"],  # C not in scene zone_labels
                    instruction_text="T", content_brief=ContentBrief(description="D", key_concepts=["K"]),
                    expected_item_count=2, points_per_item=10,
                )],
            )],
        )
        result = validate_game_plan(plan)
        assert not result.passed
        assert any("not in scene zone_labels" in i.message for i in result.errors)


class TestContentOnlyMechanics:
    def test_content_only_with_zone_labels_fails(self):
        plan = GamePlan(
            title="Test", subject="Test",
            all_zone_labels=["A"],
            scenes=[ScenePlan(
                scene_id="s1", title="T", learning_goal="G",
                zone_labels=["A"],
                needs_diagram=False,
                mechanics=[MechanicPlan(
                    mechanic_id="m1", mechanic_type="sequencing",
                    zone_labels_used=["A"],  # Should be empty for content-only
                    instruction_text="T", content_brief=ContentBrief(description="D", key_concepts=["K"]),
                    expected_item_count=3, points_per_item=10,
                )],
            )],
        )
        result = validate_game_plan(plan)
        assert not result.passed
        assert any("content-only mechanic" in i.message for i in result.errors)

    def test_zone_based_without_labels_fails(self):
        plan = GamePlan(
            title="Test", subject="Test",
            all_zone_labels=[],
            scenes=[ScenePlan(
                scene_id="s1", title="T", learning_goal="G",
                zone_labels=[], needs_diagram=True,
                mechanics=[MechanicPlan(
                    mechanic_id="m1", mechanic_type="drag_drop",
                    zone_labels_used=[],  # Should be non-empty for zone-based
                    instruction_text="T", content_brief=ContentBrief(description="D", key_concepts=["K"]),
                    expected_item_count=1, points_per_item=10,
                )],
            )],
        )
        result = validate_game_plan(plan)
        assert not result.passed
        assert any("zone-based mechanic" in i.message for i in result.errors)


class TestCycleDetection:
    def test_cycle_in_connections(self):
        plan = GamePlan(
            title="Test", subject="Test", all_zone_labels=[],
            scenes=[ScenePlan(
                scene_id="s1", title="T", learning_goal="G",
                zone_labels=[], needs_diagram=False,
                mechanics=[
                    MechanicPlan(mechanic_id="m1", mechanic_type="sequencing", instruction_text="T",
                                 content_brief=ContentBrief(description="D", key_concepts=["K"],
                                                            mechanic_specific_hints={"x": 1}),
                                 expected_item_count=3, points_per_item=10),
                    MechanicPlan(mechanic_id="m2", mechanic_type="sorting_categories", instruction_text="T",
                                 content_brief=ContentBrief(description="D", key_concepts=["K"],
                                                            mechanic_specific_hints={"x": 1}),
                                 expected_item_count=4, points_per_item=5),
                ],
                mechanic_connections=[
                    MechanicConnection(from_mechanic_id="m1", to_mechanic_id="m2"),
                    MechanicConnection(from_mechanic_id="m2", to_mechanic_id="m1"),  # Cycle!
                ],
            )],
        )
        result = validate_game_plan(plan)
        assert not result.passed
        assert any("cycle" in i.message for i in result.errors)


class TestUnsupportedMechanic:
    def test_unknown_mechanic_type_rejected_by_schema(self):
        """Pydantic's Literal type rejects unsupported mechanic types at parse time."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="literal_error"):
            MechanicPlan(
                mechanic_id="m1", mechanic_type="compare_contrast",
                instruction_text="T", content_brief=ContentBrief(description="D", key_concepts=["K"]),
                expected_item_count=1, points_per_item=10,
            )


class TestDistractors:
    def test_distractor_overlap_fails(self):
        plan = GamePlan(
            title="Test", subject="Test",
            all_zone_labels=["A", "B"],
            distractor_labels=["B", "C"],  # B overlaps with all_zone_labels
            scenes=[ScenePlan(
                scene_id="s1", title="T", learning_goal="G",
                zone_labels=["A", "B"],
                mechanics=[MechanicPlan(
                    mechanic_id="m1", mechanic_type="drag_drop",
                    zone_labels_used=["A", "B"],
                    instruction_text="T", content_brief=ContentBrief(description="D", key_concepts=["K"]),
                    expected_item_count=2, points_per_item=10,
                )],
            )],
        )
        result = validate_game_plan(plan)
        assert not result.passed
        assert any("distractor_labels overlap" in i.message for i in result.errors)


class TestScoreComputation:
    def test_scores_computed_correctly(self, single_scene_drag_drop):
        result = validate_game_plan(single_scene_drag_drop)
        assert result.passed
        mech = single_scene_drag_drop.scenes[0].mechanics[0]
        assert mech.max_score == 30  # 3 * 10
        assert single_scene_drag_drop.scenes[0].scene_max_score == 30
        assert single_scene_drag_drop.total_max_score == 30


class TestNeedsDiagram:
    def test_zone_mechanic_without_diagram_fails(self):
        plan = GamePlan(
            title="Test", subject="Test",
            all_zone_labels=["A"],
            scenes=[ScenePlan(
                scene_id="s1", title="T", learning_goal="G",
                zone_labels=["A"],
                needs_diagram=False,  # Wrong — has zone-based mechanic
                mechanics=[MechanicPlan(
                    mechanic_id="m1", mechanic_type="drag_drop",
                    zone_labels_used=["A"],
                    instruction_text="T", content_brief=ContentBrief(description="D", key_concepts=["K"]),
                    expected_item_count=1, points_per_item=10,
                )],
            )],
        )
        result = validate_game_plan(plan)
        assert not result.passed
        assert any("needs_diagram=false" in i.message for i in result.errors)
