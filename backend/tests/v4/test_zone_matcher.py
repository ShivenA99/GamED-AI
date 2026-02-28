"""Tests for zone matcher."""

from app.v4.helpers.zone_matcher import match_labels_to_zones, canonical_to_zone_id


class TestExactMatch:
    def test_exact_labels(self):
        zones = [
            {"id": "z1", "label": "Nucleus"},
            {"id": "z2", "label": "Cell Wall"},
        ]
        result = match_labels_to_zones(["Nucleus", "Cell Wall"], zones)
        assert result["Nucleus"] == "z1"
        assert result["Cell Wall"] == "z2"


class TestCaseInsensitive:
    def test_different_case(self):
        zones = [
            {"id": "z1", "label": "nucleus"},
            {"id": "z2", "label": "CELL WALL"},
        ]
        result = match_labels_to_zones(["Nucleus", "Cell Wall"], zones)
        assert result["Nucleus"] == "z1"
        assert result["Cell Wall"] == "z2"


class TestNormalized:
    def test_whitespace_differences(self):
        zones = [
            {"id": "z1", "label": "  Nucleus  "},
            {"id": "z2", "label": "Cell  Wall"},
        ]
        result = match_labels_to_zones(["Nucleus", "Cell Wall"], zones)
        assert result["Nucleus"] == "z1"
        assert result["Cell Wall"] == "z2"


class TestFuzzyMatch:
    def test_similar_labels(self):
        zones = [
            {"id": "z1", "label": "Nukleus"},  # Typo
        ]
        result = match_labels_to_zones(["Nucleus"], zones)
        # Fuzzy match should catch this (similarity > 0.7)
        assert result["Nucleus"] == "z1"


class TestUnmatched:
    def test_no_matching_zone(self):
        zones = [{"id": "z1", "label": "Something Else"}]
        result = match_labels_to_zones(["Nucleus"], zones)
        # Should get a generated zone_id
        assert result["Nucleus"].startswith("zone_s1_")
        assert "nucleus" in result["Nucleus"]


class TestCanonicalToZoneId:
    def test_deterministic(self):
        zid = canonical_to_zone_id("Cell Wall", 1)
        assert zid == "zone_s1_cell_wall"
        # Same input -> same output
        assert canonical_to_zone_id("Cell Wall", 1) == zid
