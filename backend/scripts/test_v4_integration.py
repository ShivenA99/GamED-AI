"""V4 Pipeline Integration Test — Stage-by-Stage Verification.

Tests each V4 cascade stage independently with seed data,
verifying that each produces non-empty, meaningful output.

Usage:
    cd backend
    PYTHONPATH=. python scripts/test_v4_integration.py
"""

import asyncio
import json
import sys
import time
from typing import Any

# ── Seed data (minimal valid inputs for each stage) ──────────────────

SEED_QUESTION = (
    "Label the parts of the human heart including: "
    "left atrium, right atrium, left ventricle, right ventricle, "
    "aorta, pulmonary artery, superior vena cava, inferior vena cava"
)

SEED_PEDAGOGICAL_CONTEXT = {
    "bloom_level": "understand",
    "difficulty": "medium",
    "key_concepts": ["heart anatomy", "blood flow", "chambers", "vessels"],
    "learning_objectives": ["Identify the four chambers of the heart", "Label major blood vessels"],
    "question_type": "labeling",
}

SEED_DOMAIN_KNOWLEDGE = {
    "canonical_labels": [
        "Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle",
        "Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava",
    ],
    "acceptable_variants": {
        "Left Atrium": ["LA", "left atrium"],
        "Right Atrium": ["RA", "right atrium"],
    },
    "label_descriptions": {
        "Left Atrium": "Upper-left chamber that receives oxygenated blood from the lungs",
        "Right Atrium": "Upper-right chamber that receives deoxygenated blood from the body",
        "Left Ventricle": "Lower-left chamber that pumps oxygenated blood to the body via the aorta",
        "Right Ventricle": "Lower-right chamber that pumps deoxygenated blood to the lungs",
        "Aorta": "Largest artery carrying oxygenated blood from the left ventricle",
        "Pulmonary Artery": "Artery carrying deoxygenated blood from the right ventricle to the lungs",
        "Superior Vena Cava": "Large vein returning deoxygenated blood from the upper body",
        "Inferior Vena Cava": "Large vein returning deoxygenated blood from the lower body",
    },
    "sources": ["anatomy textbook"],
    "retrieved_at": "2026-01-01T00:00:00",
}

SEED_GAME_CONCEPT = {
    "title": "Heart Anatomy Explorer",
    "subject": "Human heart anatomy",
    "difficulty": "intermediate",
    "estimated_duration_minutes": 10,
    "narrative_theme": "Journey through the human heart",
    "narrative_intro": "Welcome to the heart anatomy explorer!",
    "completion_message": "Great job identifying all heart parts!",
    "all_zone_labels": SEED_DOMAIN_KNOWLEDGE["canonical_labels"],
    "distractor_labels": ["Mitral Valve", "Tricuspid Valve"],
    "scenes": [
        {
            "scene_id": "scene_1",
            "title": "Chambers of the Heart",
            "learning_goal": "Identify the four chambers of the heart",
            "needs_diagram": True,
            "zone_labels": ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
            "mechanics": [
                {
                    "mechanic_type": "drag_drop",
                    "learning_purpose": "Test knowledge of heart chamber locations",
                    "zone_labels_used": ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                    "expected_item_count": 4,
                    "points_per_item": 10,
                    "is_timed": False,
                }
            ],
        },
        {
            "scene_id": "scene_2",
            "title": "Major Blood Vessels",
            "learning_goal": "Identify major blood vessels connected to the heart",
            "needs_diagram": True,
            "zone_labels": ["Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava"],
            "mechanics": [
                {
                    "mechanic_type": "drag_drop",
                    "learning_purpose": "Test knowledge of blood vessel locations",
                    "zone_labels_used": ["Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava"],
                    "expected_item_count": 4,
                    "points_per_item": 10,
                    "is_timed": False,
                }
            ],
        },
    ],
}

def _mechanic_creative_design(mtype: str = "drag_drop") -> dict:
    """Build a minimal valid MechanicCreativeDesign dict."""
    return {
        "mechanic_type": mtype,
        "visual_style": "clean educational",
        "instruction_text": f"Complete the {mtype} task",
        "generation_goal": f"Test knowledge via {mtype}",
    }


def _scene_creative_design(scene_id: str, title: str, mechanic_types: list[str]) -> dict:
    """Build a minimal valid SceneCreativeDesign dict."""
    return {
        "scene_id": scene_id,
        "title": title,
        "visual_concept": f"Educational diagram for {title}",
        "mechanic_designs": [_mechanic_creative_design(mt) for mt in mechanic_types],
    }


# Full game plan seed with all required fields for GamePlan/ScenePlan/MechanicPlan
SEED_GAME_PLAN = {
    "title": "Heart Anatomy Explorer",
    "subject": "Human heart anatomy",
    "difficulty": "intermediate",
    "estimated_duration_minutes": 10,
    "narrative_theme": "Journey through the human heart",
    "narrative_intro": "Welcome to the heart anatomy explorer!",
    "completion_message": "Great job!",
    "all_zone_labels": SEED_DOMAIN_KNOWLEDGE["canonical_labels"],
    "distractor_labels": ["Mitral Valve", "Tricuspid Valve"],
    "total_max_score": 0,
    "scenes": [
        {
            "scene_id": "scene_1",
            "scene_number": 1,
            "title": "Chambers of the Heart",
            "learning_goal": "Identify the four chambers",
            "needs_diagram": True,
            "zone_labels": ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
            "creative_design": _scene_creative_design("scene_1", "Chambers of the Heart", ["drag_drop"]),
            "mechanics": [
                {
                    "mechanic_id": "s1_m0",
                    "mechanic_type": "drag_drop",
                    "instruction_text": "Drag labels to the correct chambers",
                    "creative_design": _mechanic_creative_design("drag_drop"),
                    "zone_labels_used": ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                    "expected_item_count": 4,
                    "points_per_item": 10,
                }
            ],
        },
        {
            "scene_id": "scene_2",
            "scene_number": 2,
            "title": "Major Blood Vessels",
            "learning_goal": "Identify major blood vessels",
            "needs_diagram": True,
            "zone_labels": ["Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava"],
            "creative_design": _scene_creative_design("scene_2", "Major Blood Vessels", ["drag_drop"]),
            "mechanics": [
                {
                    "mechanic_id": "s2_m0",
                    "mechanic_type": "drag_drop",
                    "instruction_text": "Drag labels to the correct vessels",
                    "creative_design": _mechanic_creative_design("drag_drop"),
                    "zone_labels_used": ["Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava"],
                    "expected_item_count": 4,
                    "points_per_item": 10,
                }
            ],
        },
    ],
}


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: str | None = None
        self.output_keys: list[str] = []
        self.duration_ms = 0
        self.details: dict[str, Any] = {}

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        duration = f" ({self.duration_ms}ms)" if self.duration_ms else ""
        error = f" — {self.error}" if self.error else ""
        keys = f" keys={self.output_keys}" if self.output_keys else ""
        return f"  [{status}] {self.name}{duration}{keys}{error}"


# ── Individual stage tests ───────────────────────────────────────────

async def test_phase0_merge() -> TestResult:
    """Test that phase0_merge returns pedagogical_context and domain_knowledge."""
    result = TestResult("phase0_merge")
    t0 = time.time()
    try:
        from app.v4.merge_nodes import phase0_merge

        state = {
            "pedagogical_context": SEED_PEDAGOGICAL_CONTEXT,
            "domain_knowledge": SEED_DOMAIN_KNOWLEDGE,
        }
        out = phase0_merge(state)
        result.duration_ms = int((time.time() - t0) * 1000)
        result.output_keys = list(out.keys())

        if "pedagogical_context" not in out:
            result.error = "Missing pedagogical_context in output"
            return result
        if "domain_knowledge" not in out:
            result.error = "Missing domain_knowledge in output"
            return result

        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_concept_validator_pass() -> TestResult:
    """Test that concept_validator passes a valid concept."""
    result = TestResult("concept_validator (valid)")
    t0 = time.time()
    try:
        from app.v4.schemas.game_concept import GameConcept
        from app.v4.validators.concept_validator import validate_game_concept

        concept = GameConcept(**SEED_GAME_CONCEPT)
        validation = validate_game_concept(concept)
        result.duration_ms = int((time.time() - t0) * 1000)
        result.details = {"passed": validation.passed, "score": validation.score, "issues": len(validation.issues)}

        if not validation.passed:
            issues = [i.message for i in validation.issues if i.severity == "error"]
            result.error = f"Validation failed: {issues}"
            return result

        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_concept_validator_reject_empty() -> TestResult:
    """Test that empty concepts are rejected (by Pydantic schema min_length=1 or validator)."""
    result = TestResult("concept_validator (empty)")
    t0 = time.time()
    try:
        from app.v4.schemas.game_concept import GameConcept
        from pydantic import ValidationError

        empty_concept_data = {
            **SEED_GAME_CONCEPT,
            "scenes": [],
        }
        try:
            GameConcept(**empty_concept_data)
            result.error = "Should have rejected empty concept but Pydantic accepted it"
            return result
        except ValidationError:
            # Expected — Pydantic rejects scenes=[] due to min_length=1
            result.passed = True

        result.duration_ms = int((time.time() - t0) * 1000)
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_game_plan_validator() -> TestResult:
    """Test that game_plan_validator validates and computes scores."""
    result = TestResult("game_plan_validator")
    t0 = time.time()
    try:
        from app.v4.schemas.game_plan import GamePlan
        from app.v4.validators.game_plan_validator import validate_game_plan

        plan = GamePlan(**SEED_GAME_PLAN)
        validation = validate_game_plan(plan)
        result.duration_ms = int((time.time() - t0) * 1000)
        result.details = {
            "passed": validation.passed,
            "score": validation.score,
            "total_max_score": plan.total_max_score,
            "issues": len(validation.issues),
        }

        if not validation.passed:
            issues = [i.message for i in validation.issues if i.severity == "error"]
            result.error = f"Validation failed: {issues}"
            return result

        if plan.total_max_score <= 0:
            result.error = f"total_max_score not computed: {plan.total_max_score}"
            return result

        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_game_plan_validator_reject_empty() -> TestResult:
    """Test that empty game plans are rejected (by Pydantic schema min_length=1 or validator)."""
    result = TestResult("game_plan_validator (empty)")
    t0 = time.time()
    try:
        from app.v4.schemas.game_plan import GamePlan
        from pydantic import ValidationError

        empty_plan_data = {
            **SEED_GAME_PLAN,
            "scenes": [],
        }
        try:
            GamePlan(**empty_plan_data)
            result.error = "Should have rejected empty plan but Pydantic accepted it"
            return result
        except ValidationError:
            # Expected — Pydantic rejects scenes=[] due to min_length=1
            result.passed = True

        result.duration_ms = int((time.time() - t0) * 1000)
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_scene_design_merge() -> TestResult:
    """Test that scene_design_merge deduplicates and validates."""
    result = TestResult("scene_design_merge")
    t0 = time.time()
    try:
        from app.v4.merge_nodes import scene_design_merge

        state = {
            "scene_creative_designs_raw": [
                {
                    "scene_id": "scene_1",
                    "scene_index": 0,
                    "status": "success",
                    "design": _scene_creative_design("scene_1", "Chambers of the Heart", ["drag_drop"]),
                },
                {
                    "scene_id": "scene_2",
                    "scene_index": 1,
                    "status": "success",
                    "design": _scene_creative_design("scene_2", "Major Blood Vessels", ["drag_drop"]),
                },
            ],
            "game_concept": SEED_GAME_CONCEPT,
        }
        out = scene_design_merge(state)
        result.duration_ms = int((time.time() - t0) * 1000)
        result.output_keys = list(out.keys())

        designs = out.get("scene_creative_designs", {})
        if not designs:
            result.error = "No scene_creative_designs in output"
            return result

        result.details = {"design_count": len(designs)}
        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_content_merge() -> TestResult:
    """Test that content_merge deduplicates mechanic contents."""
    result = TestResult("content_merge")
    t0 = time.time()
    try:
        from app.v4.merge_nodes import content_merge

        state = {
            "mechanic_contents_raw": [
                {
                    "mechanic_id": "mech_dd_1",
                    "scene_id": "scene_1",
                    "mechanic_type": "drag_drop",
                    "status": "success",
                    "content": {"items": [{"label": "Left Atrium", "zone_id": "z1"}]},
                },
                {
                    "mechanic_id": "mech_dd_2",
                    "scene_id": "scene_2",
                    "mechanic_type": "drag_drop",
                    "status": "success",
                    "content": {"items": [{"label": "Aorta", "zone_id": "z5"}]},
                },
            ],
        }
        out = content_merge(state)
        result.duration_ms = int((time.time() - t0) * 1000)
        result.output_keys = list(out.keys())

        contents = out.get("mechanic_contents", [])
        if not contents:
            result.error = "No mechanic_contents in output"
            return result

        result.details = {"content_count": len(contents)}
        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_interaction_merge() -> TestResult:
    """Test that interaction_merge deduplicates by scene_id."""
    result = TestResult("interaction_merge")
    t0 = time.time()
    try:
        from app.v4.merge_nodes import interaction_merge

        state = {
            "interaction_results_raw": [
                {"scene_id": "scene_1", "status": "success", "scoring": {}},
                {"scene_id": "scene_2", "status": "success", "scoring": {}},
            ],
        }
        out = interaction_merge(state)
        result.duration_ms = int((time.time() - t0) * 1000)
        result.output_keys = list(out.keys())

        results = out.get("interaction_results", [])
        if not results:
            result.error = "No interaction_results in output"
            return result

        result.details = {"result_count": len(results)}
        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_asset_merge() -> TestResult:
    """Test that asset_merge deduplicates and increments retry count."""
    result = TestResult("asset_merge")
    t0 = time.time()
    try:
        from app.v4.merge_nodes import asset_merge

        state = {
            "generated_assets_raw": [
                {"scene_id": "scene_1", "status": "success", "diagram_url": "https://example.com/heart1.png", "zones": [{"id": "z1"}]},
                {"scene_id": "scene_2", "status": "error", "error": "No image found"},
            ],
            "asset_retry_count": 0,
        }
        out = asset_merge(state)
        result.duration_ms = int((time.time() - t0) * 1000)
        result.output_keys = list(out.keys())

        assets = out.get("generated_assets", [])
        retry_count = out.get("asset_retry_count", 0)

        if retry_count != 1:
            result.error = f"Expected retry_count=1, got {retry_count}"
            return result

        if len(assets) != 2:
            result.error = f"Expected 2 assets, got {len(assets)}"
            return result

        result.details = {"asset_count": len(assets), "retry_count": retry_count}
        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


async def test_instrumentation_registry() -> TestResult:
    """Test that all V4 cascade agents are in the instrumentation registry."""
    result = TestResult("instrumentation_registry")
    t0 = time.time()
    try:
        from app.agents.instrumentation import extract_input_keys, extract_output_keys, get_agent_metadata

        expected_agents = [
            "v4_input_analyzer", "v4_dk_retriever", "v4_phase0_merge",
            "v4_game_concept_designer", "v4_concept_validator",
            "v4_scene_design_send", "v4_scene_designer", "v4_scene_design_merge",
            "v4_graph_builder", "v4_game_plan_validator",
            "v4_content_dispatch", "v4_content_generator", "v4_content_merge",
            "v4_interaction_designer", "v4_interaction_merge",
            "v4_asset_worker", "v4_asset_merge", "v4_assembler",
        ]

        missing_metadata = []

        dummy_state: dict[str, Any] = {}
        for agent in expected_agents:
            # extract_input_keys(state, agent_name) and extract_output_keys(result, agent_name)
            # Both return [] for unknown agents — we test that metadata exists
            input_keys = extract_input_keys(dummy_state, agent)
            output_keys = extract_output_keys({}, agent)

            meta = get_agent_metadata(agent)
            if not meta or not meta.get("name"):
                missing_metadata.append(agent)

        result.duration_ms = int((time.time() - t0) * 1000)

        if missing_metadata:
            result.error = f"Missing metadata: {missing_metadata}"
            return result

        result.details = {"agents_checked": len(expected_agents)}
        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.duration_ms = int((time.time() - t0) * 1000)
    return result


# ── Runner ───────────────────────────────────────────────────────────

async def run_all_tests() -> list[TestResult]:
    """Run all integration tests."""
    tests = [
        test_phase0_merge,
        test_concept_validator_pass,
        test_concept_validator_reject_empty,
        test_game_plan_validator,
        test_game_plan_validator_reject_empty,
        test_scene_design_merge,
        test_content_merge,
        test_interaction_merge,
        test_asset_merge,
        test_instrumentation_registry,
    ]

    results: list[TestResult] = []
    for test_fn in tests:
        try:
            result = await test_fn()
        except Exception as e:
            result = TestResult(test_fn.__name__)
            result.error = f"Unhandled: {e}"
        results.append(result)

    return results


def main():
    print("=" * 60)
    print("V4 Pipeline Integration Tests")
    print("=" * 60)

    results = asyncio.run(run_all_tests())

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    print()
    for r in results:
        print(str(r))

    print()
    print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
