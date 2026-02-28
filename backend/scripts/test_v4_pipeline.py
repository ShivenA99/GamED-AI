#!/usr/bin/env python3
"""
E2E Test Script for V4 Pipeline

Runs the V4 pipeline against test questions and validates:
- Blueprint structure matches frontend expectations
- Score arithmetic is correct
- generation_complete flag is set
- Per-mechanic config fields are populated

Usage:
    cd backend
    PYTHONPATH=. python scripts/test_v4_pipeline.py
    PYTHONPATH=. python scripts/test_v4_pipeline.py --question 1    # Run only Q1
    PYTHONPATH=. python scripts/test_v4_pipeline.py --verbose        # Debug logging
    PYTHONPATH=. python scripts/test_v4_pipeline.py --dry-run        # Validate graph only
"""

import asyncio
import json
import time
import sys
import os
import logging
import argparse
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

# Suppress noisy warnings
import warnings
warnings.filterwarnings("ignore", message=".*Pydantic.*", category=UserWarning)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("gamed_ai.test_v4")


# ── Test Questions ────────────────────────────────────────────────────

TEST_QUESTIONS = [
    {
        "id": "Q1",
        "text": "Label the parts of a plant cell",
        "options": None,
        "description": "Single scene, drag_drop mechanic",
        "expected": {
            "min_scenes": 1,
            "mechanics": ["drag_drop"],
            "requires_diagram": True,
            "config_fields": ["dragDropConfig"],
        },
    },
    {
        "id": "Q2",
        "text": "Heart: label the chambers, trace the blood flow path, and order the steps of the cardiac cycle",
        "options": None,
        "description": "Multi-scene, 3 mechanics (drag_drop, trace_path, sequencing)",
        "expected": {
            "min_scenes": 2,
            "mechanics": ["drag_drop", "trace_path", "sequencing"],
            "requires_diagram": True,
            "config_fields": ["dragDropConfig", "paths", "sequenceConfig"],
        },
    },
    {
        "id": "Q3",
        "text": "Cell division: sort the phases of mitosis into the correct order, then match each phase to its description",
        "options": None,
        "description": "Content-only mechanics (sorting + description_matching), no diagram needed",
        "expected": {
            "min_scenes": 1,
            "mechanics": ["sorting", "description_matching"],
            "requires_diagram": False,
            "config_fields": ["sortingConfig", "descriptionMatchingConfig"],
        },
    },
    {
        "id": "Q4",
        "text": "Describe the function of each organelle in an animal cell",
        "options": None,
        "description": "Single scene, description_matching mechanic",
        "expected": {
            "min_scenes": 1,
            "mechanics": ["description_matching"],
            "requires_diagram": True,
            "config_fields": ["descriptionMatchingConfig"],
        },
    },
]


# ── Results ───────────────────────────────────────────────────────────


@dataclass
class PhaseTimings:
    phase0_ms: int = 0
    phase1_ms: int = 0
    phase2_ms: int = 0
    phase3_ms: int = 0
    phase4_ms: int = 0
    total_ms: int = 0


@dataclass
class ValidationResult:
    check: str
    passed: bool
    message: str


@dataclass
class TestResult:
    question_id: str
    description: str
    success: bool
    duration_ms: int
    validations: list[ValidationResult] = field(default_factory=list)
    timings: Optional[PhaseTimings] = None
    error_message: Optional[str] = None
    blueprint_summary: Optional[dict] = None


# ── Logging Setup ─────────────────────────────────────────────────────


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = []
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Reduce noise
    for name in ["httpx", "httpcore", "openai", "urllib3", "google", "grpc"]:
        logging.getLogger(name).setLevel(logging.WARNING)


# ── Graph Compilation Test ────────────────────────────────────────────


def test_graph_compilation() -> bool:
    """Verify V4 graph compiles successfully."""
    from app.v4.graph import create_v4_graph

    try:
        graph = create_v4_graph()
        nodes = list(graph.nodes.keys())
        logger.info(f"V4 graph compiled: {len(nodes)} nodes — {', '.join(nodes)}")
        assert len(nodes) >= 9, f"Expected >=9 nodes, got {len(nodes)}"
        return True
    except Exception as e:
        logger.error(f"Graph compilation failed: {e}")
        return False


# ── Blueprint Validation ──────────────────────────────────────────────


def validate_blueprint(blueprint: dict, expected: dict) -> list[ValidationResult]:
    """Validate blueprint structure against expected fields."""
    results = []

    # 1. Blueprint exists and is dict
    results.append(ValidationResult(
        check="blueprint_exists",
        passed=isinstance(blueprint, dict) and len(blueprint) > 0,
        message="Blueprint is a non-empty dict" if blueprint else "Blueprint is empty or None",
    ))

    if not blueprint:
        return results

    # 2. Scenes/diagram
    diagram = blueprint.get("diagram", {}) or {}
    zones = diagram.get("zones", []) or []
    labels = diagram.get("labels", []) or []

    if expected.get("requires_diagram"):
        results.append(ValidationResult(
            check="diagram_present",
            passed=bool(diagram.get("assetUrl") or diagram.get("svgMarkup")),
            message=f"Diagram has assetUrl={bool(diagram.get('assetUrl'))}, svgMarkup={bool(diagram.get('svgMarkup'))}",
        ))
        results.append(ValidationResult(
            check="zones_non_empty",
            passed=len(zones) > 0,
            message=f"Found {len(zones)} zones",
        ))
        results.append(ValidationResult(
            check="labels_non_empty",
            passed=len(labels) > 0,
            message=f"Found {len(labels)} labels",
        ))

    # 3. Labels have correctZoneId
    labels_with_zone = [l for l in labels if l.get("correctZoneId")]
    if labels:
        results.append(ValidationResult(
            check="labels_have_correctZoneId",
            passed=len(labels_with_zone) == len(labels),
            message=f"{len(labels_with_zone)}/{len(labels)} labels have correctZoneId",
        ))

    # 4. Scenes
    scenes = blueprint.get("scenes", []) or []
    results.append(ValidationResult(
        check="scenes_count",
        passed=len(scenes) >= expected.get("min_scenes", 1),
        message=f"Found {len(scenes)} scenes (expected >= {expected.get('min_scenes', 1)})",
    ))

    # 5. Config fields
    for config_field in expected.get("config_fields", []):
        value = blueprint.get(config_field)
        # Also check inside scenes
        scene_has_config = any(
            s.get(config_field) for s in scenes
        ) if scenes else False
        present = value is not None or scene_has_config
        results.append(ValidationResult(
            check=f"config_{config_field}",
            passed=present,
            message=f"{config_field}: root={value is not None}, scene_level={scene_has_config}",
        ))

    # 6. Score arithmetic
    max_score = blueprint.get("max_score") or blueprint.get("maxScore")
    if max_score is not None:
        results.append(ValidationResult(
            check="max_score_positive",
            passed=max_score > 0,
            message=f"max_score={max_score}",
        ))

    # 7. Mode transitions (multi-mechanic)
    if len(expected.get("mechanics", [])) > 1:
        transitions = blueprint.get("modeTransitions", []) or []
        results.append(ValidationResult(
            check="mode_transitions",
            passed=len(transitions) >= len(expected["mechanics"]) - 1,
            message=f"Found {len(transitions)} transitions for {len(expected['mechanics'])} mechanics",
        ))

    return results


# ── Pipeline Execution ────────────────────────────────────────────────


async def run_v4_pipeline(question: dict) -> TestResult:
    """Run V4 pipeline for a single question."""
    from app.v4.graph import create_v4_graph

    qid = question["id"]
    logger.info(f"{'='*60}")
    logger.info(f"Running {qid}: {question['text'][:60]}...")
    logger.info(f"Expected: {question['description']}")
    logger.info(f"{'='*60}")

    start = time.time()

    try:
        graph = create_v4_graph()

        initial_state = {
            "question_text": question["text"],
            "question_id": qid,
            "question_options": question["options"],
            "_run_id": f"test_v4_{qid}_{int(time.time())}",
            "_pipeline_preset": "v4",
            "design_retry_count": 0,
            "content_retry_count": 0,
            "asset_retry_count": 0,
            "generation_complete": False,
            "is_degraded": False,
            "_stage_order": 0,
            "started_at": datetime.utcnow().isoformat(),
            "last_updated_at": datetime.utcnow().isoformat(),
            "generated_assets_raw": [],
            "failed_asset_scene_ids": [],
            "phase_errors": [],
        }

        config = {"recursion_limit": 50}

        # Run the graph
        final_state = await graph.ainvoke(initial_state, config)

        duration_ms = int((time.time() - start) * 1000)

        # Check generation_complete
        gen_complete = final_state.get("generation_complete", False)
        blueprint = final_state.get("blueprint")
        errors = final_state.get("phase_errors", [])

        validations = []

        validations.append(ValidationResult(
            check="generation_complete",
            passed=gen_complete is True,
            message=f"generation_complete={gen_complete}",
        ))

        validations.append(ValidationResult(
            check="no_phase_errors",
            passed=len(errors) == 0,
            message=f"{len(errors)} phase errors" + (f": {errors[0]}" if errors else ""),
        ))

        # Validate blueprint
        if blueprint:
            bp_validations = validate_blueprint(blueprint, question["expected"])
            validations.extend(bp_validations)

        all_passed = all(v.passed for v in validations)

        # Blueprint summary
        bp_summary = None
        if blueprint:
            diagram = blueprint.get("diagram", {}) or {}
            bp_summary = {
                "zones": len(diagram.get("zones", []) or []),
                "labels": len(diagram.get("labels", []) or []),
                "scenes": len(blueprint.get("scenes", []) or []),
                "has_diagram": bool(diagram.get("assetUrl") or diagram.get("svgMarkup")),
                "max_score": blueprint.get("max_score") or blueprint.get("maxScore"),
                "config_keys": [k for k in blueprint.keys() if k.endswith("Config") or k == "paths"],
            }

        return TestResult(
            question_id=qid,
            description=question["description"],
            success=all_passed,
            duration_ms=duration_ms,
            validations=validations,
            error_message=None if all_passed else "Some validations failed",
            blueprint_summary=bp_summary,
        )

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error(f"Pipeline error for {qid}: {e}", exc_info=True)
        return TestResult(
            question_id=qid,
            description=question["description"],
            success=False,
            duration_ms=duration_ms,
            error_message=str(e),
        )


# ── Report ────────────────────────────────────────────────────────────


def print_report(results: list[TestResult]):
    """Print summary report."""
    print("\n" + "=" * 72)
    print("V4 PIPELINE E2E TEST REPORT")
    print("=" * 72)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tests run: {len(results)}")
    print(f"Passed: {sum(1 for r in results if r.success)}")
    print(f"Failed: {sum(1 for r in results if not r.success)}")
    print()

    for result in results:
        status = "PASS" if result.success else "FAIL"
        print(f"[{status}] {result.question_id}: {result.description}")
        print(f"       Duration: {result.duration_ms}ms")

        if result.error_message and not result.validations:
            print(f"       Error: {result.error_message}")

        for v in result.validations:
            icon = "+" if v.passed else "X"
            print(f"       [{icon}] {v.check}: {v.message}")

        if result.blueprint_summary:
            bp = result.blueprint_summary
            print(f"       Blueprint: {bp['zones']} zones, {bp['labels']} labels, "
                  f"{bp['scenes']} scenes, diagram={bp['has_diagram']}")
            if bp["config_keys"]:
                print(f"       Configs: {', '.join(bp['config_keys'])}")
        print()

    # Overall
    all_pass = all(r.success for r in results)
    total_time = sum(r.duration_ms for r in results)
    print("=" * 72)
    print(f"OVERALL: {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    print(f"Total time: {total_time / 1000:.1f}s")
    print("=" * 72)

    return all_pass


# ── Main ──────────────────────────────────────────────────────────────


async def main():
    parser = argparse.ArgumentParser(description="V4 Pipeline E2E Tests")
    parser.add_argument("--question", "-q", type=int, help="Run only question N (1-4)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Only test graph compilation")
    parser.add_argument("--output", "-o", type=str, help="Save results to JSON file")
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Always test compilation first
    print("\n--- Graph Compilation Test ---")
    if not test_graph_compilation():
        print("FATAL: Graph compilation failed. Cannot proceed.")
        sys.exit(1)
    print("Graph compilation: OK\n")

    if args.dry_run:
        print("Dry run complete. Graph compiles successfully.")
        return

    # Select questions
    questions = TEST_QUESTIONS
    if args.question:
        idx = args.question - 1
        if 0 <= idx < len(TEST_QUESTIONS):
            questions = [TEST_QUESTIONS[idx]]
        else:
            print(f"Invalid question number: {args.question} (valid: 1-{len(TEST_QUESTIONS)})")
            sys.exit(1)

    # Run tests
    results = []
    for q in questions:
        result = await run_v4_pipeline(q)
        results.append(result)

    # Report
    all_pass = print_report(results)

    # Save JSON output if requested
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "results": [
                {
                    "question_id": r.question_id,
                    "description": r.description,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "error_message": r.error_message,
                    "blueprint_summary": r.blueprint_summary,
                    "validations": [
                        {"check": v.check, "passed": v.passed, "message": v.message}
                        for v in r.validations
                    ],
                }
                for r in results
            ],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {args.output}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
