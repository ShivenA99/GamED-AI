"""Tests for scoring helpers."""

from app.v4.helpers.scoring import (
    compute_mechanic_score, compute_scene_score, compute_total_score,
    validate_score_chain,
)


class TestBasicScoring:
    def test_mechanic_score(self):
        assert compute_mechanic_score(3, 10) == 30
        assert compute_mechanic_score(5, 5) == 25
        assert compute_mechanic_score(1, 100) == 100

    def test_scene_score(self):
        mechanics = [{"max_score": 30}, {"max_score": 20}]
        assert compute_scene_score(mechanics) == 50

    def test_total_score(self):
        scenes = [{"scene_max_score": 50}, {"scene_max_score": 40}]
        assert compute_total_score(scenes) == 90


class TestScoreChain:
    def test_valid_chain(self):
        plan = {
            "total_max_score": 70,
            "scenes": [
                {
                    "scene_max_score": 30,
                    "mechanics": [{"expected_item_count": 3, "points_per_item": 10, "max_score": 30}],
                },
                {
                    "scene_max_score": 40,
                    "mechanics": [{"expected_item_count": 4, "points_per_item": 10, "max_score": 40}],
                },
            ],
        }
        errors = validate_score_chain(plan)
        assert errors == []

    def test_mechanic_mismatch(self):
        plan = {
            "total_max_score": 50,
            "scenes": [{
                "scene_max_score": 50,
                "mechanics": [{"expected_item_count": 3, "points_per_item": 10, "max_score": 50}],  # Wrong
            }],
        }
        errors = validate_score_chain(plan)
        assert len(errors) >= 1
        assert "max_score=50" in errors[0]

    def test_total_mismatch(self):
        plan = {
            "total_max_score": 999,
            "scenes": [{
                "scene_max_score": 30,
                "mechanics": [{"expected_item_count": 3, "points_per_item": 10, "max_score": 30}],
            }],
        }
        errors = validate_score_chain(plan)
        assert any("total_max_score" in e for e in errors)
