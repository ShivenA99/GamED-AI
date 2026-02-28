"""Tests for content validator."""

import pytest
from app.v4.schemas.game_plan import MechanicPlan, ContentBrief
from app.v4.validators.content_validator import validate_mechanic_content


def _make_plan(mtype: str, labels: list[str] = None, count: int = 3) -> MechanicPlan:
    return MechanicPlan(
        mechanic_id="m1", mechanic_type=mtype,
        zone_labels_used=labels or [],
        instruction_text="Test",
        content_brief=ContentBrief(description="D", key_concepts=["K"]),
        expected_item_count=count, points_per_item=10,
    )


class TestDragDrop:
    def test_valid(self):
        plan = _make_plan("drag_drop", ["A", "B", "C"])
        content = {"labels": ["A", "B", "C"]}
        result = validate_mechanic_content(content, plan)
        assert result.passed

    def test_wrong_count(self):
        plan = _make_plan("drag_drop", ["A", "B", "C"])
        content = {"labels": ["A", "B"]}
        result = validate_mechanic_content(content, plan)
        assert not result.passed

    def test_label_not_in_canonical(self):
        plan = _make_plan("drag_drop", ["A", "B", "C"])
        content = {"labels": ["A", "B", "X"]}
        result = validate_mechanic_content(content, plan)
        assert not result.passed


class TestSequencing:
    def test_valid(self):
        plan = _make_plan("sequencing", count=3)
        content = {
            "items": [{"id": "a", "content": "X"}, {"id": "b", "content": "Y"}, {"id": "c", "content": "Z"}],
            "correct_order": ["a", "b", "c"],
        }
        result = validate_mechanic_content(content, plan)
        assert result.passed

    def test_order_mismatch(self):
        plan = _make_plan("sequencing", count=3)
        content = {
            "items": [{"id": "a", "content": "X"}, {"id": "b", "content": "Y"}, {"id": "c", "content": "Z"}],
            "correct_order": ["a", "b"],  # Missing c
        }
        result = validate_mechanic_content(content, plan)
        assert not result.passed

    def test_item_count_mismatch(self):
        plan = _make_plan("sequencing", count=4)
        content = {
            "items": [{"id": "a", "content": "X"}, {"id": "b", "content": "Y"}, {"id": "c", "content": "Z"}],
            "correct_order": ["a", "b", "c"],
        }
        result = validate_mechanic_content(content, plan)
        assert not result.passed


class TestSorting:
    def test_valid(self):
        plan = _make_plan("sorting_categories", count=4)
        content = {
            "categories": [{"id": "c1", "label": "A"}, {"id": "c2", "label": "B"}],
            "items": [
                {"id": "i1", "content": "X", "correctCategoryId": "c1"},
                {"id": "i2", "content": "Y", "correctCategoryId": "c2"},
                {"id": "i3", "content": "Z", "correctCategoryId": "c1"},
                {"id": "i4", "content": "W", "correctCategoryId": "c2"},
            ],
        }
        result = validate_mechanic_content(content, plan)
        assert result.passed

    def test_invalid_category_ref(self):
        plan = _make_plan("sorting_categories", count=2)
        content = {
            "categories": [{"id": "c1", "label": "A"}, {"id": "c2", "label": "B"}],
            "items": [
                {"id": "i1", "content": "X", "correctCategoryId": "c1"},
                {"id": "i2", "content": "Y", "correctCategoryId": "c99"},  # Invalid
            ],
        }
        result = validate_mechanic_content(content, plan)
        assert not result.passed

    def test_orphan_categories_warning(self):
        plan = _make_plan("sorting_categories", count=2)
        content = {
            "categories": [{"id": "c1", "label": "A"}, {"id": "c2", "label": "B"}, {"id": "c3", "label": "C"}],
            "items": [
                {"id": "i1", "content": "X", "correctCategoryId": "c1"},
                {"id": "i2", "content": "Y", "correctCategoryId": "c2"},
            ],
        }
        result = validate_mechanic_content(content, plan)
        assert result.passed  # Orphan is only a warning
        assert any("Orphan" in i.message for i in result.warnings)


class TestMemoryMatch:
    def test_valid(self):
        plan = _make_plan("memory_match", count=3)
        content = {
            "pairs": [
                {"id": "p1", "front": "A", "back": "1"},
                {"id": "p2", "front": "B", "back": "2"},
                {"id": "p3", "front": "C", "back": "3"},
            ],
        }
        result = validate_mechanic_content(content, plan)
        assert result.passed

    def test_duplicate_ids(self):
        plan = _make_plan("memory_match", count=3)
        content = {
            "pairs": [
                {"id": "p1", "front": "A", "back": "1"},
                {"id": "p1", "front": "B", "back": "2"},  # Duplicate
                {"id": "p3", "front": "C", "back": "3"},
            ],
        }
        result = validate_mechanic_content(content, plan)
        assert not result.passed


class TestBranching:
    def test_valid(self):
        plan = _make_plan("branching_scenario", count=4)
        content = {
            "nodes": [
                {"id": "n1", "question": "Q1", "options": [
                    {"id": "o1", "text": "A", "nextNodeId": "n2", "isCorrect": True},
                    {"id": "o2", "text": "B", "nextNodeId": "n3", "isCorrect": False},
                ]},
                {"id": "n2", "question": "Q2", "options": [
                    {"id": "o3", "text": "C", "nextNodeId": "n4", "isCorrect": True},
                ]},
                {"id": "n3", "question": "End1", "isEndNode": True},
                {"id": "n4", "question": "End2", "isEndNode": True},
            ],
            "startNodeId": "n1",
        }
        result = validate_mechanic_content(content, plan)
        assert result.passed

    def test_unreachable_end_node(self):
        plan = _make_plan("branching_scenario", count=3)
        content = {
            "nodes": [
                {"id": "n1", "question": "Q1", "options": [
                    {"id": "o1", "text": "A", "nextNodeId": "n2", "isCorrect": True},
                ]},
                {"id": "n2", "question": "End", "isEndNode": True},
                {"id": "n3", "question": "Orphan End", "isEndNode": True},  # Unreachable
            ],
            "startNodeId": "n1",
        }
        result = validate_mechanic_content(content, plan)
        assert not result.passed
        assert any("unreachable" in i.message.lower() for i in result.errors)

    def test_invalid_start_node(self):
        plan = _make_plan("branching_scenario", count=2)
        content = {
            "nodes": [
                {"id": "n1", "question": "Q1", "options": [{"id": "o1", "text": "A", "nextNodeId": "n2"}]},
                {"id": "n2", "question": "End", "isEndNode": True},
            ],
            "startNodeId": "n99",  # Doesn't exist
        }
        result = validate_mechanic_content(content, plan)
        assert not result.passed


class TestClickToIdentify:
    def test_valid(self):
        plan = _make_plan("click_to_identify", ["Nucleus", "Mito"], count=2)
        content = {
            "prompts": [
                {"text": "Click the control center", "target_label": "Nucleus", "explanation": "It controls"},
                {"text": "Click the powerhouse", "target_label": "Mito", "explanation": "ATP production"},
            ],
        }
        result = validate_mechanic_content(content, plan)
        assert result.passed


class TestDescriptionMatching:
    def test_valid(self):
        plan = _make_plan("description_matching", ["Nucleus", "Mito", "Wall"], count=3)
        content = {
            "descriptions": {"Nucleus": "Control center", "Mito": "Powerhouse", "Wall": "Protection"},
        }
        result = validate_mechanic_content(content, plan)
        assert result.passed

    def test_label_not_in_canonical(self):
        plan = _make_plan("description_matching", ["Nucleus", "Mito"], count=2)
        content = {
            "descriptions": {"Nucleus": "Control center", "Unknown": "Something"},
        }
        result = validate_mechanic_content(content, plan)
        assert not result.passed
