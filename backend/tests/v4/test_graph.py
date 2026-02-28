"""V4 Phase 4 Tests — Graph wiring, routers, merge nodes.

Tests:
- Graph compiles with correct topology (9 nodes, 14 edges)
- design_router: retry/pass logic with counter
- asset_send_router: Send dispatch for diagram scenes, skip for content-only
- asset_retry_router: retry failed scenes, respect retry limit
- phase0_merge: passthrough sync point
- asset_merge: deduplication by scene_id
- game_plan_validator_node: validates and computes scores
"""

import pytest

from app.v4.graph import create_v4_graph, game_plan_validator_node
from app.v4.merge_nodes import asset_merge, phase0_merge
from app.v4.routers import (
    MAX_ASSET_RETRIES,
    MAX_DESIGN_RETRIES,
    asset_retry_router,
    asset_send_router,
    design_router,
)


# ── Graph Compilation ─────────────────────────────────────────────


class TestGraphCompilation:
    def test_graph_compiles(self):
        graph = create_v4_graph()
        assert graph is not None

    def test_node_count(self):
        graph = create_v4_graph()
        # 9 real nodes + __start__ + __end__
        nodes = graph.get_graph().nodes
        real_nodes = {k for k in nodes if not k.startswith("__")}
        assert real_nodes == {
            "input_analyzer", "dk_retriever", "phase0_merge",
            "game_designer", "game_plan_validator",
            "content_build",
            "asset_worker", "asset_merge",
            "blueprint_assembler",
        }

    def test_edge_count(self):
        graph = create_v4_graph()
        assert len(graph.get_graph().edges) == 14

    def test_parallel_start(self):
        """START fans out to both input_analyzer and dk_retriever."""
        graph = create_v4_graph()
        start_targets = {
            e.target for e in graph.get_graph().edges
            if e.source == "__start__"
        }
        assert start_targets == {"input_analyzer", "dk_retriever"}

    def test_retry_loop_exists(self):
        """game_plan_validator has conditional edges to game_designer (retry) and content_build (pass)."""
        graph = create_v4_graph()
        validator_edges = [
            e for e in graph.get_graph().edges
            if e.source == "game_plan_validator"
        ]
        targets = {e.target for e in validator_edges}
        assert targets == {"game_designer", "content_build"}
        assert all(e.conditional for e in validator_edges)

    def test_asset_send_edges(self):
        """content_build routes to asset_worker or blueprint_assembler."""
        graph = create_v4_graph()
        content_edges = [
            e for e in graph.get_graph().edges
            if e.source == "content_build"
        ]
        targets = {e.target for e in content_edges}
        assert targets == {"asset_worker", "blueprint_assembler"}

    def test_asset_retry_loop(self):
        """asset_merge routes to asset_worker (retry) or blueprint_assembler."""
        graph = create_v4_graph()
        merge_edges = [
            e for e in graph.get_graph().edges
            if e.source == "asset_merge"
        ]
        targets = {e.target for e in merge_edges}
        assert targets == {"asset_worker", "blueprint_assembler"}

    def test_end_from_assembler(self):
        """blueprint_assembler connects to END."""
        graph = create_v4_graph()
        end_edges = [
            e for e in graph.get_graph().edges
            if e.source == "blueprint_assembler"
        ]
        assert len(end_edges) == 1
        assert end_edges[0].target == "__end__"


# ── Design Router ──────────────────────────────────────────────────


class TestDesignRouter:
    def test_pass_on_validation_success(self):
        state = {"design_validation": {"passed": True}, "design_retry_count": 0}
        assert design_router(state) == "pass"

    def test_retry_on_failure_within_limit(self):
        state = {"design_validation": {"passed": False}, "design_retry_count": 0}
        assert design_router(state) == "retry"

    def test_retry_at_max(self):
        state = {"design_validation": {"passed": False}, "design_retry_count": MAX_DESIGN_RETRIES}
        assert design_router(state) == "retry"

    def test_pass_on_retry_exceeded(self):
        state = {"design_validation": {"passed": False}, "design_retry_count": MAX_DESIGN_RETRIES + 1}
        assert design_router(state) == "pass"

    def test_pass_on_missing_validation(self):
        state = {"design_retry_count": 0}
        assert design_router(state) == "retry"  # no validation = not passed, retry


# ── Asset Send Router ──────────────────────────────────────────────


class TestAssetSendRouter:
    def test_send_for_diagram_scenes(self):
        state = {
            "game_plan": {
                "scenes": [
                    {"scene_id": "s1", "needs_diagram": True, "image_spec": {"description": "heart"}, "zone_labels": ["aorta"]},
                    {"scene_id": "s2", "needs_diagram": True, "image_spec": {"description": "lungs"}, "zone_labels": ["bronchi"]},
                ]
            }
        }
        result = asset_send_router(state)
        assert isinstance(result, list)
        assert len(result) == 2
        # Check Send objects
        assert result[0].node == "asset_worker"
        assert result[0].arg["scene_id"] == "s1"
        assert result[1].arg["scene_id"] == "s2"

    def test_skip_content_only_scenes(self):
        state = {
            "game_plan": {
                "scenes": [
                    {"scene_id": "s1", "needs_diagram": False},
                ]
            }
        }
        result = asset_send_router(state)
        assert result == "blueprint_assembler"

    def test_mixed_scenes(self):
        state = {
            "game_plan": {
                "scenes": [
                    {"scene_id": "s1", "needs_diagram": True, "image_spec": {}, "zone_labels": ["x"]},
                    {"scene_id": "s2", "needs_diagram": False},
                ]
            }
        }
        result = asset_send_router(state)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].arg["scene_id"] == "s1"

    def test_empty_game_plan(self):
        state = {}
        result = asset_send_router(state)
        assert result == "blueprint_assembler"


# ── Asset Retry Router ─────────────────────────────────────────────


class TestAssetRetryRouter:
    def test_all_success_routes_to_assembler(self):
        state = {
            "generated_assets": [
                {"scene_id": "s1", "status": "success"},
            ],
            "asset_retry_count": 1,
            "game_plan": {"scenes": [{"scene_id": "s1"}]},
        }
        assert asset_retry_router(state) == "blueprint_assembler"

    def test_failure_triggers_retry(self):
        state = {
            "generated_assets": [
                {"scene_id": "s1", "status": "error"},
            ],
            "asset_retry_count": 0,
            "game_plan": {"scenes": [{"scene_id": "s1", "image_spec": {}, "zone_labels": ["x"]}]},
        }
        result = asset_retry_router(state)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].node == "asset_worker"
        assert result[0].arg["scene_id"] == "s1"

    def test_retry_limit_exceeded(self):
        state = {
            "generated_assets": [
                {"scene_id": "s1", "status": "error"},
            ],
            "asset_retry_count": MAX_ASSET_RETRIES + 1,
            "game_plan": {"scenes": [{"scene_id": "s1"}]},
        }
        assert asset_retry_router(state) == "blueprint_assembler"


# ── Merge Nodes ────────────────────────────────────────────────────


class TestPhase0Merge:
    def test_returns_empty(self):
        state = {"pedagogical_context": {"level": "apply"}, "domain_knowledge": {"labels": []}}
        result = phase0_merge(state)
        assert result == {}


class TestAssetMerge:
    def test_deduplicates_by_scene_id(self):
        state = {
            "generated_assets_raw": [
                {"scene_id": "s1", "status": "error", "error": "timeout"},
                {"scene_id": "s1", "status": "success", "diagram_url": "http://ok"},
            ],
            "asset_retry_count": 0,
        }
        result = asset_merge(state)
        assets = result["generated_assets"]
        assert len(assets) == 1
        assert assets[0]["status"] == "success"  # latest wins
        assert result["asset_retry_count"] == 1

    def test_separates_success_and_failure(self):
        state = {
            "generated_assets_raw": [
                {"scene_id": "s1", "status": "success"},
                {"scene_id": "s2", "status": "error"},
            ],
            "asset_retry_count": 0,
        }
        result = asset_merge(state)
        assert len(result["generated_assets"]) == 2

    def test_empty_raw(self):
        state = {"generated_assets_raw": [], "asset_retry_count": 0}
        result = asset_merge(state)
        assert result["generated_assets"] == []
        assert result["asset_retry_count"] == 1

    def test_increments_retry_count(self):
        state = {
            "generated_assets_raw": [{"scene_id": "s1", "status": "success"}],
            "asset_retry_count": 2,
        }
        result = asset_merge(state)
        assert result["asset_retry_count"] == 3


# ── Game Plan Validator Node ───────────────────────────────────────


class TestGamePlanValidatorNode:
    @pytest.mark.asyncio
    async def test_valid_plan(self):
        plan = {
            "title": "Test",
            "subject": "Biology",
            "all_zone_labels": ["A", "B"],
            "distractor_labels": ["X"],
            "scenes": [{
                "scene_id": "s1",
                "title": "Scene 1",
                "learning_goal": "Goal",
                "zone_labels": ["A", "B"],
                "needs_diagram": True,
                "image_spec": {"description": "test"},
                "mechanics": [{
                    "mechanic_id": "m1",
                    "mechanic_type": "drag_drop",
                    "zone_labels_used": ["A", "B"],
                    "instruction_text": "Drag labels to the correct zones",
                    "expected_item_count": 2,
                    "points_per_item": 10,
                    "content_brief": {
                        "description": "Label diagram parts",
                        "key_concepts": ["anatomy"],
                        "dk_fields_needed": [],
                    },
                }],
                "mechanic_connections": [],
            }],
        }
        result = await game_plan_validator_node({"game_plan": plan})
        assert result["design_validation"]["passed"] is True
        # Score should be computed
        assert result["game_plan"]["scenes"][0]["mechanics"][0]["max_score"] == 20
        assert result["game_plan"]["total_max_score"] == 20

    @pytest.mark.asyncio
    async def test_no_game_plan(self):
        result = await game_plan_validator_node({})
        assert result["design_validation"]["passed"] is False

    @pytest.mark.asyncio
    async def test_invalid_plan(self):
        plan = {
            "title": "Test",
            "learning_goal": "Learn",
            "all_zone_labels": [],
            "distractor_labels": [],
            "scenes": [],  # No scenes — should fail
        }
        result = await game_plan_validator_node({"game_plan": plan})
        assert result["design_validation"]["passed"] is False
