"""Tests for blueprint assembler."""

import pytest
from app.v4.helpers.blueprint_assembler import assemble_blueprint


class TestSingleSceneDragDrop:
    def test_basic_assembly(self, single_scene_drag_drop, drag_drop_content, interaction_result, asset_result):
        plan = single_scene_drag_drop.model_dump()
        # Compute scores (normally done by validator)
        plan["scenes"][0]["mechanics"][0]["max_score"] = 30
        plan["scenes"][0]["scene_max_score"] = 30
        plan["total_max_score"] = 30

        bp = assemble_blueprint(
            game_plan=plan,
            mechanic_contents=[drag_drop_content],
            interaction_results=[interaction_result],
            asset_results=[asset_result],
        )

        assert bp["templateType"] == "INTERACTIVE_DIAGRAM"
        assert bp["title"] == "Plant Cell Parts"
        assert bp["generation_complete"] is True
        assert bp["totalMaxScore"] == 30
        assert bp["diagram"]["assetUrl"] == "https://example.com/plant_cell.png"
        assert len(bp["diagram"]["zones"]) == 3
        assert len(bp["labels"]) == 3
        assert len(bp["distractorLabels"]) == 1
        assert bp["distractorLabels"][0]["isDistractor"] is True
        assert "dragDropConfig" in bp
        assert bp["interactionMode"] == "drag_drop"
        assert bp["animationCues"]["correctPlacement"] == "pulse-green"

    def test_labels_have_correct_zone_id(self, single_scene_drag_drop, drag_drop_content, interaction_result, asset_result):
        plan = single_scene_drag_drop.model_dump()
        plan["scenes"][0]["mechanics"][0]["max_score"] = 30
        plan["total_max_score"] = 30

        bp = assemble_blueprint(plan, [drag_drop_content], [interaction_result], [asset_result])
        for label in bp["labels"]:
            assert label["correctZoneId"], f"Label {label['text']} has no correctZoneId"


class TestContentOnlyScene:
    def test_no_diagram(self, content_only_plan, sequencing_content, sorting_content):
        plan = content_only_plan.model_dump()
        # Compute scores
        plan["scenes"][0]["mechanics"][0]["max_score"] = 40
        plan["scenes"][0]["mechanics"][1]["max_score"] = 30
        plan["scenes"][0]["scene_max_score"] = 70
        plan["total_max_score"] = 70

        bp = assemble_blueprint(
            game_plan=plan,
            mechanic_contents=[sequencing_content, sorting_content],
            interaction_results=[],
            asset_results=[],  # No assets for content-only
        )

        assert bp["templateType"] == "INTERACTIVE_DIAGRAM"
        assert bp["diagram"]["assetUrl"] is None
        assert bp["diagram"]["zones"] == []
        assert bp["labels"] == []
        assert bp["distractorLabels"] == []
        assert "sequenceConfig" in bp
        assert "sortingConfig" in bp
        assert bp["totalMaxScore"] == 70


class TestMultiScene:
    def test_multi_scene_structure(self, multi_scene_plan, drag_drop_content, trace_path_content,
                                    sequencing_content, interaction_result, asset_result):
        plan = multi_scene_plan.model_dump()
        # Compute scores
        plan["scenes"][0]["mechanics"][0]["max_score"] = 40
        plan["scenes"][0]["mechanics"][1]["max_score"] = 20
        plan["scenes"][0]["scene_max_score"] = 60
        plan["scenes"][1]["mechanics"][0]["max_score"] = 40
        plan["scenes"][1]["scene_max_score"] = 40
        plan["total_max_score"] = 100

        bp = assemble_blueprint(
            game_plan=plan,
            mechanic_contents=[drag_drop_content, trace_path_content, sequencing_content],
            interaction_results=[interaction_result],
            asset_results=[asset_result],
        )

        assert bp["is_multi_scene"] is True
        assert "game_sequence" in bp
        assert len(bp["game_sequence"]["scenes"]) == 2


class TestIdentificationPromptsAtRoot:
    def test_prompts_at_root(self, click_to_identify_content, interaction_result, asset_result):
        plan = {
            "title": "Test", "subject": "Bio", "difficulty": "beginner",
            "all_zone_labels": ["Nucleus", "Mitochondria"],
            "distractor_labels": [],
            "total_max_score": 20,
            "scenes": [{
                "scene_id": "scene_1", "title": "T", "learning_goal": "G",
                "zone_labels": ["Nucleus", "Mitochondria"],
                "needs_diagram": True, "image_spec": {"description": "Cell"},
                "mechanics": [{
                    "mechanic_id": "m1", "mechanic_type": "click_to_identify",
                    "zone_labels_used": ["Nucleus", "Mitochondria"],
                    "instruction_text": "Click", "max_score": 20,
                    "content_brief": {"description": "D", "key_concepts": ["K"]},
                    "expected_item_count": 2, "points_per_item": 10,
                }],
                "mechanic_connections": [], "scene_max_score": 20,
            }],
        }
        bp = assemble_blueprint(plan, [click_to_identify_content], [interaction_result], [asset_result])
        assert "identificationPrompts" in bp
        assert "clickToIdentifyConfig" in bp
        assert len(bp["identificationPrompts"]) == 2


class TestPathsAtRoot:
    def test_paths_at_root(self, trace_path_content, interaction_result, asset_result):
        plan = {
            "title": "Test", "subject": "Bio",
            "all_zone_labels": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle", "Aorta"],
            "distractor_labels": [], "total_max_score": 20,
            "scenes": [{
                "scene_id": "scene_1", "title": "T", "learning_goal": "G",
                "zone_labels": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle", "Aorta"],
                "needs_diagram": True, "image_spec": {"description": "Heart"},
                "mechanics": [{
                    "mechanic_id": "m2", "mechanic_type": "trace_path",
                    "zone_labels_used": ["Right Atrium", "Right Ventricle", "Left Atrium", "Left Ventricle", "Aorta"],
                    "instruction_text": "Trace",
                    "content_brief": {"description": "D", "key_concepts": ["K"]},
                    "expected_item_count": 1, "points_per_item": 20, "max_score": 20,
                }],
                "mechanic_connections": [], "scene_max_score": 20,
            }],
        }
        bp = assemble_blueprint(plan, [trace_path_content], [interaction_result], [asset_result])
        assert "paths" in bp
        assert "tracePathConfig" in bp
        assert bp["tracePathConfig"]["particleSpeed"] == "medium"
        assert len(bp["paths"]) == 1
        assert len(bp["paths"][0]["waypoints"]) == 5


class TestFieldNames:
    def test_memory_match_front_back(self, memory_match_content):
        plan = {
            "title": "Test", "subject": "Bio", "all_zone_labels": [],
            "distractor_labels": [], "total_max_score": 30,
            "scenes": [{
                "scene_id": "scene_1", "title": "T", "learning_goal": "G",
                "zone_labels": [], "needs_diagram": False,
                "mechanics": [{
                    "mechanic_id": "m1", "mechanic_type": "memory_match",
                    "zone_labels_used": [], "instruction_text": "Match",
                    "content_brief": {"description": "D", "key_concepts": ["K"]},
                    "expected_item_count": 3, "points_per_item": 10, "max_score": 30,
                }],
                "mechanic_connections": [], "scene_max_score": 30,
            }],
        }
        bp = assemble_blueprint(plan, [memory_match_content], [], [])
        config = bp["memoryMatchConfig"]
        assert config["pairs"][0]["front"] == "Nucleus"
        assert config["pairs"][0]["back"] == "Control center"
        assert config["gridSize"] == [2, 3]

    def test_branching_question_options(self, branching_content):
        plan = {
            "title": "Test", "subject": "Bio", "all_zone_labels": [],
            "distractor_labels": [], "total_max_score": 40,
            "scenes": [{
                "scene_id": "scene_1", "title": "T", "learning_goal": "G",
                "zone_labels": [], "needs_diagram": False,
                "mechanics": [{
                    "mechanic_id": "m1", "mechanic_type": "branching_scenario",
                    "zone_labels_used": [], "instruction_text": "Decide",
                    "content_brief": {"description": "D", "key_concepts": ["K"]},
                    "expected_item_count": 4, "points_per_item": 10, "max_score": 40,
                }],
                "mechanic_connections": [], "scene_max_score": 40,
            }],
        }
        bp = assemble_blueprint(plan, [branching_content], [], [])
        config = bp["branchingConfig"]
        assert config["startNodeId"] == "n1"
        node = config["nodes"][0]
        assert "question" in node
        assert "options" in node
        assert node["options"][0]["nextNodeId"] == "n2"
        assert node["options"][0]["isCorrect"] is True


class TestTimedMechanic:
    def test_timed_sets_root_fields(self):
        plan = {
            "title": "Test", "subject": "Bio", "all_zone_labels": ["A"],
            "distractor_labels": [], "total_max_score": 10,
            "scenes": [{
                "scene_id": "scene_1", "title": "T", "learning_goal": "G",
                "zone_labels": ["A"], "needs_diagram": True,
                "image_spec": {"description": "D"},
                "mechanics": [{
                    "mechanic_id": "m1", "mechanic_type": "drag_drop",
                    "zone_labels_used": ["A"], "instruction_text": "Drag",
                    "content_brief": {"description": "D", "key_concepts": ["K"]},
                    "expected_item_count": 1, "points_per_item": 10, "max_score": 10,
                    "is_timed": True, "time_limit_seconds": 30,
                }],
                "mechanic_connections": [], "scene_max_score": 10,
            }],
        }
        content = {"mechanic_id": "m1", "scene_id": "scene_1", "mechanic_type": "drag_drop",
                    "content": {"labels": ["A"]}}
        bp = assemble_blueprint(plan, [content], [], [])
        assert bp["timedChallengeWrappedMode"] == "drag_drop"
        assert bp["timeLimitSeconds"] == 30


class TestScoreRollup:
    def test_total_max_score(self, single_scene_drag_drop, drag_drop_content, interaction_result, asset_result):
        plan = single_scene_drag_drop.model_dump()
        plan["scenes"][0]["mechanics"][0]["max_score"] = 30
        plan["total_max_score"] = 30

        bp = assemble_blueprint(plan, [drag_drop_content], [interaction_result], [asset_result])
        assert bp["totalMaxScore"] == 30
        assert bp["scoringStrategy"]["max_score"] == 30
