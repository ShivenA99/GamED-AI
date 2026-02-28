#!/usr/bin/env python3
"""
V4 Creative Cascade — Full E2E Integration Test (with real LLM calls)

Runs the compiled V4 LangGraph through a real question and validates
that the 3-stage creative cascade produces correct output at EVERY level:

  Level 1: GameConcept has valid scenes + mechanics
  Level 2: SceneCreativeDesigns have per-mechanic MechanicCreativeDesign
  Level 3: GamePlan has correct IDs, scores, connections, creative_design copies
  Level 4: MechanicContents have visual config fields + data fields
  Level 5: InteractionResults have scoring/feedback per mechanic
  Level 6: Blueprint has all config keys, transitions, zone/label integrity

Usage:
    cd backend
    PYTHONPATH=. python scripts/test_v4_cascade_e2e.py
    PYTHONPATH=. python scripts/test_v4_cascade_e2e.py --question 2
    PYTHONPATH=. python scripts/test_v4_cascade_e2e.py --dry-run       # Graph compile only
    PYTHONPATH=. python scripts/test_v4_cascade_e2e.py --verbose
"""

import asyncio
import json
import logging
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import warnings
warnings.filterwarnings("ignore", message=".*Pydantic.*", category=UserWarning)

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("gamed_ai.test_v4_cascade")


# ── Test Questions ────────────────────────────────────────────────────

TEST_QUESTIONS = [
    {
        "id": "Q1_multi_mechanic",
        "text": "Heart anatomy: label the four chambers, trace the blood flow path through the heart, and arrange the steps of the cardiac cycle in order",
        "options": None,
        "description": "Multi-scene with zone-based + content-only mechanics (drag_drop, trace_path, sequencing)",
        "expect_min_scenes": 1,
        "expect_min_mechanics": 3,
        "expect_zone_mechanics": True,
        "expect_content_mechanics": True,
    },
    {
        "id": "Q2_sorting_memory",
        "text": "Classify these cell organelles by their function: mitochondria, ribosome, nucleus, cell membrane, golgi apparatus, endoplasmic reticulum. Then match each organelle to its description.",
        "options": None,
        "description": "Content-only mechanics (sorting_categories + memory_match or description_matching)",
        "expect_min_scenes": 1,
        "expect_min_mechanics": 2,
        "expect_zone_mechanics": False,
        "expect_content_mechanics": True,
    },
    {
        "id": "Q3_branching",
        "text": "A patient presents with chest pain. Walk through the diagnostic process step by step, making clinical decisions at each point.",
        "options": None,
        "description": "Branching scenario (decision tree mechanic)",
        "expect_min_scenes": 1,
        "expect_min_mechanics": 1,
        "expect_zone_mechanics": False,
        "expect_content_mechanics": True,
    },
]


# ── Check / Result tracking ──────────────────────────────────────────

class Check:
    def __init__(self, name: str, passed: bool, message: str, level: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.level = level

    def __repr__(self):
        icon = "✓" if self.passed else "✗"
        return f"  {icon} [{self.level}] {self.name}: {self.message}"


# ── Logging Setup ─────────────────────────────────────────────────────

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = logging.Formatter("%(asctime)s [%(levelname)-7s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = []
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    root.addHandler(ch)
    for noisy in ["httpx", "httpcore", "openai", "urllib3", "google", "grpc", "PIL"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Deep Validation ───────────────────────────────────────────────────

ZONE_BASED = {"drag_drop", "click_to_identify", "trace_path", "description_matching"}
CONTENT_ONLY = {"sequencing", "sorting_categories", "memory_match", "branching_scenario"}

CONFIG_KEY_MAP = {
    "drag_drop": "dragDropConfig",
    "click_to_identify": "clickToIdentifyConfig",
    "trace_path": "tracePathConfig",
    "sequencing": "sequenceConfig",
    "sorting_categories": "sortingConfig",
    "memory_match": "memoryMatchConfig",
    "branching_scenario": "branchingConfig",
    "description_matching": "descriptionMatchingConfig",
}

VISUAL_CONFIG_FIELDS = {
    "drag_drop": ["leader_line_style", "tray_position", "placement_animation", "feedback_timing"],
    "click_to_identify": ["prompt_style", "selection_mode", "highlight_style"],
    "trace_path": ["path_type", "drawing_mode", "particleSpeed"],
    "sequencing": ["layout_mode", "card_type", "connector_style"],
    "sorting_categories": ["sort_mode", "item_card_type", "container_style"],
    "memory_match": ["match_type", "card_back_style", "matched_card_behavior"],
    "branching_scenario": ["show_path_taken", "allow_backtrack", "show_consequences"],
    "description_matching": ["show_connecting_lines", "defer_evaluation"],
}

CREATIVE_HINTS = {
    "sequencing": "sequence_topic",
    "branching_scenario": "narrative_premise",
    "sorting_categories": "category_names",
    "trace_path": "path_process",
    "memory_match": "match_type",
    "click_to_identify": "prompt_style",
    "description_matching": "description_source",
}


def validate_state_deep(state: dict, question: dict) -> list[Check]:
    """Deep validation of the final state across all cascade levels."""
    checks: list[Check] = []

    # ── Level 0: Pipeline metadata ──

    checks.append(Check(
        "generation_complete", state.get("generation_complete") is True,
        f"generation_complete={state.get('generation_complete')}", "L0"
    ))

    phase_errors = state.get("phase_errors", [])
    checks.append(Check(
        "no_phase_errors", len(phase_errors) == 0,
        f"{len(phase_errors)} errors" + (f": {phase_errors[0]}" if phase_errors else ""), "L0"
    ))

    # ── Level 1: GameConcept ──

    concept = state.get("game_concept")
    checks.append(Check("game_concept_exists", concept is not None, "present" if concept else "MISSING", "L1"))
    if not concept:
        return checks

    scenes = concept.get("scenes", [])
    checks.append(Check(
        "concept_scenes", len(scenes) >= question["expect_min_scenes"],
        f"{len(scenes)} scenes (need >= {question['expect_min_scenes']})", "L1"
    ))

    all_mechanics = []
    for scene in scenes:
        for mech in scene.get("mechanics", []):
            all_mechanics.append(mech)

    checks.append(Check(
        "concept_mechanics", len(all_mechanics) >= question["expect_min_mechanics"],
        f"{len(all_mechanics)} mechanics (need >= {question['expect_min_mechanics']})", "L1"
    ))

    mech_types = {m.get("mechanic_type") for m in all_mechanics}
    checks.append(Check(
        "concept_mechanic_types", len(mech_types) > 0,
        f"types: {sorted(mech_types)}", "L1"
    ))

    all_zone_labels = concept.get("all_zone_labels", [])
    if question["expect_zone_mechanics"]:
        checks.append(Check(
            "concept_zone_labels", len(all_zone_labels) >= 2,
            f"{len(all_zone_labels)} zone labels", "L1"
        ))

    # ── Level 1.5: Concept validation ──

    cv = state.get("concept_validation", {})
    checks.append(Check(
        "concept_validation_passed", cv.get("passed", False),
        f"passed={cv.get('passed')}, issues={len(cv.get('issues', []))}", "L1"
    ))

    # ── Level 2: SceneCreativeDesigns ──

    designs = state.get("scene_creative_designs") or {}
    checks.append(Check(
        "creative_designs_exist", len(designs) > 0,
        f"{len(designs)} scene designs", "L2"
    ))

    for sid, design in designs.items():
        md = design.get("mechanic_designs", [])
        checks.append(Check(
            f"creative_{sid}_mechanic_designs", len(md) > 0,
            f"{sid}: {len(md)} mechanic designs", "L2"
        ))

        # Check each mechanic design has key fields
        for i, mcd in enumerate(md):
            mtype = mcd.get("mechanic_type", "?")
            has_visual = bool(mcd.get("visual_style"))
            has_instruction = bool(mcd.get("instruction_text"))
            has_goal = bool(mcd.get("generation_goal"))
            checks.append(Check(
                f"creative_{sid}_m{i}_fields",
                has_visual and has_instruction and has_goal,
                f"{mtype}: visual={has_visual}, instruction={has_instruction}, goal={has_goal}", "L2"
            ))

            # Check mechanic-specific hints
            hint_field = CREATIVE_HINTS.get(mtype)
            if hint_field:
                hint_val = mcd.get(hint_field)
                has_hint = hint_val is not None and hint_val != "" and hint_val != []
                checks.append(Check(
                    f"creative_{sid}_m{i}_{hint_field}",
                    has_hint,
                    f"{mtype}.{hint_field}={'present' if has_hint else 'MISSING'} ({repr(hint_val)[:40] if hint_val else 'None'})", "L2"
                ))

        # Check image_spec for zone-based scenes
        has_zone_mech = any(m.get("mechanic_type") in ZONE_BASED for m in md)
        if has_zone_mech:
            img_spec = design.get("image_spec")
            checks.append(Check(
                f"creative_{sid}_image_spec",
                img_spec is not None and bool(img_spec.get("description")),
                f"image_spec={'present' if img_spec else 'MISSING'}", "L2"
            ))

    # ── Level 3: GamePlan ──

    plan = state.get("game_plan")
    checks.append(Check("game_plan_exists", plan is not None, "present" if plan else "MISSING", "L3"))
    if not plan:
        return checks

    plan_scenes = plan.get("scenes", [])
    total_score = plan.get("total_max_score", 0)
    checks.append(Check("plan_total_score", total_score > 0, f"total_max_score={total_score}", "L3"))

    for si, scene in enumerate(plan_scenes):
        sid = scene.get("scene_id", f"scene_{si+1}")
        mechanics = scene.get("mechanics", [])

        for mi, mech in enumerate(mechanics):
            mid = mech.get("mechanic_id", "?")
            mtype = mech.get("mechanic_type", "?")

            # Score computed
            max_score = mech.get("max_score", 0)
            expected = mech.get("expected_item_count", 0) * mech.get("points_per_item", 0)
            checks.append(Check(
                f"plan_{mid}_score",
                max_score == expected and max_score > 0,
                f"max_score={max_score} (expected={expected})", "L3"
            ))

            # Creative design copied
            cd = mech.get("creative_design")
            checks.append(Check(
                f"plan_{mid}_creative_design",
                cd is not None and cd.get("mechanic_type") == mtype,
                f"creative_design type={'match' if cd and cd.get('mechanic_type') == mtype else 'MISMATCH'}", "L3"
            ))

        # Connections
        conns = scene.get("mechanic_connections", [])
        if len(mechanics) > 1:
            checks.append(Check(
                f"plan_{sid}_connections",
                len(conns) == len(mechanics) - 1,
                f"{len(conns)} connections for {len(mechanics)} mechanics", "L3"
            ))
            for conn in conns:
                trigger = conn.get("trigger", "")
                checks.append(Check(
                    f"plan_{sid}_trigger_{conn.get('from_mechanic_id', '?')}",
                    trigger != "" and trigger != "completion",  # Should be resolved
                    f"trigger={trigger}", "L3"
                ))

    # ── Level 3.5: Design validation ──

    dv = state.get("design_validation", {})
    checks.append(Check(
        "design_validation_passed", dv.get("passed", False),
        f"passed={dv.get('passed')}, issues={len(dv.get('issues', []))}", "L3"
    ))

    # ── Level 4: MechanicContents ──

    contents = state.get("mechanic_contents") or []
    checks.append(Check(
        "mechanic_contents_exist", len(contents) > 0,
        f"{len(contents)} content results", "L4"
    ))

    successful_contents = [c for c in contents if c.get("status") == "success"]
    failed_contents = [c for c in contents if c.get("status") != "success"]
    checks.append(Check(
        "mechanic_contents_success_rate",
        len(successful_contents) >= len(contents) * 0.5,  # At least 50% success
        f"{len(successful_contents)}/{len(contents)} succeeded, {len(failed_contents)} failed", "L4"
    ))

    for content_result in successful_contents:
        mid = content_result.get("mechanic_id", "?")
        mtype = content_result.get("mechanic_type", "?")
        content = content_result.get("content", {})

        # Check visual config fields
        expected_fields = VISUAL_CONFIG_FIELDS.get(mtype, [])
        present_fields = [f for f in expected_fields if f in content]
        checks.append(Check(
            f"content_{mid}_visual_fields",
            len(present_fields) == len(expected_fields),
            f"{len(present_fields)}/{len(expected_fields)} visual fields ({', '.join(present_fields)})", "L4"
        ))

        # Check key data fields
        if mtype == "drag_drop":
            checks.append(Check(f"content_{mid}_labels", bool(content.get("labels")),
                f"labels={len(content.get('labels', []))}", "L4"))
        elif mtype == "sequencing":
            checks.append(Check(f"content_{mid}_items", bool(content.get("items")),
                f"items={len(content.get('items', []))}", "L4"))
        elif mtype == "branching_scenario":
            checks.append(Check(f"content_{mid}_nodes", bool(content.get("nodes")),
                f"nodes={len(content.get('nodes', []))}", "L4"))
        elif mtype == "sorting_categories":
            checks.append(Check(f"content_{mid}_categories", bool(content.get("categories")),
                f"categories={len(content.get('categories', []))}", "L4"))
        elif mtype == "memory_match":
            checks.append(Check(f"content_{mid}_pairs", bool(content.get("pairs")),
                f"pairs={len(content.get('pairs', []))}", "L4"))
        elif mtype == "trace_path":
            checks.append(Check(f"content_{mid}_paths", bool(content.get("paths")),
                f"paths={len(content.get('paths', []))}", "L4"))
        elif mtype == "click_to_identify":
            checks.append(Check(f"content_{mid}_prompts", bool(content.get("prompts")),
                f"prompts={len(content.get('prompts', []))}", "L4"))
        elif mtype == "description_matching":
            checks.append(Check(f"content_{mid}_descriptions", bool(content.get("descriptions")),
                f"descriptions={len(content.get('descriptions', {}))}", "L4"))

    # ── Level 5: InteractionResults ──

    interactions = state.get("interaction_results") or []
    checks.append(Check(
        "interaction_results_exist", len(interactions) > 0,
        f"{len(interactions)} interaction results", "L5"
    ))

    for ir in interactions:
        sid = ir.get("scene_id", "?")
        scoring = ir.get("mechanic_scoring", {})
        feedback = ir.get("mechanic_feedback", {})
        checks.append(Check(
            f"interaction_{sid}_scoring",
            len(scoring) > 0,
            f"{len(scoring)} scoring rules, {len(feedback)} feedback rules", "L5"
        ))

    # ── Level 6: Blueprint ──

    blueprint = state.get("blueprint")
    checks.append(Check("blueprint_exists", blueprint is not None, "present" if blueprint else "MISSING", "L6"))
    if not blueprint:
        return checks

    checks.append(Check(
        "blueprint_type", blueprint.get("templateType") == "INTERACTIVE_DIAGRAM",
        f"templateType={blueprint.get('templateType')}", "L6"
    ))

    bp_score = blueprint.get("totalMaxScore", 0)
    checks.append(Check("blueprint_score", bp_score > 0, f"totalMaxScore={bp_score}", "L6"))

    bp_mechanics = blueprint.get("mechanics", [])
    checks.append(Check(
        "blueprint_mechanics", len(bp_mechanics) >= question["expect_min_mechanics"],
        f"{len(bp_mechanics)} mechanics in blueprint", "L6"
    ))

    # Check config keys
    found_configs = []
    # Check root and game_sequence scenes
    search_locations = [blueprint]
    for gs in blueprint.get("game_sequence", {}).get("scenes", []):
        search_locations.append(gs)

    for mtype in mech_types:
        config_key = CONFIG_KEY_MAP.get(mtype)
        if config_key:
            found = any(loc.get(config_key) for loc in search_locations)
            found_configs.append(config_key if found else None)
            checks.append(Check(
                f"blueprint_{config_key}", found,
                f"{config_key}={'found' if found else 'MISSING'}", "L6"
            ))

    # Mode transitions — only expected when any scene has >1 mechanic
    transitions = blueprint.get("modeTransitions", [])
    any_multi_mech_scene = any(
        len(s.get("mechanics", [])) > 1
        for s in (plan or {}).get("scenes", [])
    )
    if any_multi_mech_scene:
        checks.append(Check(
            "blueprint_transitions", len(transitions) > 0,
            f"{len(transitions)} mode transitions", "L6"
        ))
    else:
        checks.append(Check(
            "blueprint_transitions", True,
            f"{len(transitions)} transitions (none expected — each scene has 1 mechanic)", "L6"
        ))

    # Diagram integrity for zone-based
    if question["expect_zone_mechanics"]:
        diagram = blueprint.get("diagram", {})
        zones = diagram.get("zones", [])
        labels = blueprint.get("labels", [])
        checks.append(Check("blueprint_zones", len(zones) > 0, f"{len(zones)} zones", "L6"))
        checks.append(Check("blueprint_labels", len(labels) > 0, f"{len(labels)} labels", "L6"))

        if zones and labels:
            zone_ids = {z.get("id") for z in zones}
            labels_with_valid_zone = [l for l in labels if l.get("correctZoneId") in zone_ids]
            checks.append(Check(
                "blueprint_label_zone_integrity",
                len(labels_with_valid_zone) > 0,
                f"{len(labels_with_valid_zone)}/{len(labels)} labels point to valid zones", "L6"
            ))

    # Data leak check for drag_drop
    dd_config = None
    for loc in search_locations:
        if loc.get("dragDropConfig"):
            dd_config = loc["dragDropConfig"]
            break
    if dd_config:
        has_labels_leak = "labels" in dd_config
        has_distractor_leak = "distractor_labels" in dd_config
        checks.append(Check(
            "blueprint_dd_no_data_leak",
            not has_labels_leak and not has_distractor_leak,
            f"labels_in_config={has_labels_leak}, distractor_in_config={has_distractor_leak}", "L6"
        ))

    return checks


# ── Pipeline Execution ────────────────────────────────────────────────

async def run_cascade_test(question: dict) -> tuple[list[Check], dict, float]:
    """Run the V4 cascade pipeline and return (checks, final_state, duration_s)."""
    from app.v4.graph import create_v4_graph

    qid = question["id"]
    print(f"\n{'='*70}")
    print(f"  {qid}: {question['text'][:70]}...")
    print(f"  Expected: {question['description']}")
    print(f"{'='*70}")

    graph = create_v4_graph()

    initial_state = {
        "question_text": question["text"],
        "question_id": qid,
        "question_options": question["options"],
        "_run_id": f"test_{qid}_{int(time.time())}",
        "_pipeline_preset": "v4",
        # Initialize reducer fields
        "scene_creative_designs_raw": [],
        "failed_scene_design_ids": [],
        "mechanic_contents_raw": [],
        "failed_content_ids": [],
        "interaction_results_raw": [],
        "failed_interaction_ids": [],
        "art_directed_manifests_raw": [],
        "failed_art_direction_ids": [],
        "generated_assets_raw": [],
        "failed_asset_scene_ids": [],
        "phase_errors": [],
        # Initialize counters
        "concept_retry_count": 0,
        "design_retry_count": 0,
        "content_retry_count": 0,
        "asset_retry_count": 0,
        "generation_complete": False,
        "is_degraded": False,
        "_stage_order": 0,
        "started_at": datetime.utcnow().isoformat(),
        "last_updated_at": datetime.utcnow().isoformat(),
    }

    t0 = time.time()
    try:
        final_state = await graph.ainvoke(initial_state, {"recursion_limit": 60})
        duration = time.time() - t0
        checks = validate_state_deep(final_state, question)
        return checks, final_state, duration
    except Exception as e:
        duration = time.time() - t0
        logger.error(f"Pipeline error for {qid}: {e}", exc_info=True)
        checks = [Check("pipeline_execution", False, f"EXCEPTION: {e}", "L0")]
        return checks, {}, duration


# ── Report ────────────────────────────────────────────────────────────

def print_checks(checks: list[Check], state: dict, duration: float):
    """Print detailed check results grouped by level."""
    levels = {}
    for c in checks:
        levels.setdefault(c.level, []).append(c)

    level_names = {
        "L0": "Pipeline Metadata",
        "L1": "GameConcept (WHAT/WHY)",
        "L2": "SceneCreativeDesign (HOW)",
        "L3": "GamePlan (Graph Builder)",
        "L4": "MechanicContents (Content Generator)",
        "L5": "InteractionResults (Interaction Designer)",
        "L6": "Blueprint (Assembler)",
    }

    total_passed = 0
    total_checks = 0

    for level in ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]:
        level_checks = levels.get(level, [])
        if not level_checks:
            continue

        passed = sum(1 for c in level_checks if c.passed)
        failed = sum(1 for c in level_checks if not c.passed)
        total_passed += passed
        total_checks += len(level_checks)

        status = "PASS" if failed == 0 else "FAIL"
        print(f"\n  ── {level}: {level_names.get(level, level)} [{status}] ({passed}/{len(level_checks)}) ──")

        for c in level_checks:
            icon = "✓" if c.passed else "✗"
            print(f"    {icon} {c.name}: {c.message}")

    # Summary
    all_pass = total_passed == total_checks
    print(f"\n  Duration: {duration:.1f}s")
    print(f"  Checks: {total_passed}/{total_checks} passed")

    # Quick state summary
    if state:
        concept = state.get("game_concept", {})
        plan = state.get("game_plan", {})
        contents = state.get("mechanic_contents", [])
        blueprint = state.get("blueprint", {})

        concept_scenes = len(concept.get("scenes", [])) if concept else 0
        plan_mechanics = sum(len(s.get("mechanics", [])) for s in (plan.get("scenes", []) if plan else []))
        content_ok = sum(1 for c in (contents or []) if c.get("status") == "success")
        bp_mechanics = len((blueprint or {}).get("mechanics", []))

        print(f"\n  Pipeline flow: {concept_scenes} concept scenes → {plan_mechanics} plan mechanics "
              f"→ {content_ok}/{len(contents or [])} contents → {bp_mechanics} blueprint mechanics")

    return all_pass


# ── Main ──────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="V4 Creative Cascade E2E Test")
    parser.add_argument("--question", "-q", type=int, help="Run only question N (1-based)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Only compile graph")
    parser.add_argument("--output", "-o", type=str, help="Save state to JSON")
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Load env
    from dotenv import load_dotenv
    load_dotenv()

    print("\n" + "=" * 70)
    print("V4 CREATIVE CASCADE — E2E INTEGRATION TEST")
    print("=" * 70)

    # Graph compilation check
    print("\n── Graph Compilation ──")
    from app.v4.graph import create_v4_graph
    try:
        graph = create_v4_graph()
        nodes = list(graph.nodes.keys())
        print(f"  ✓ Compiled: {len(nodes)} nodes")
    except Exception as e:
        print(f"  ✗ FATAL: {e}")
        sys.exit(1)

    if args.dry_run:
        print("\nDry run complete.")
        return

    # Select questions
    questions = TEST_QUESTIONS
    if args.question:
        idx = args.question - 1
        if 0 <= idx < len(TEST_QUESTIONS):
            questions = [TEST_QUESTIONS[idx]]
        else:
            print(f"Invalid question (1-{len(TEST_QUESTIONS)})")
            sys.exit(1)

    # Run
    results = []
    for q in questions:
        checks, state, duration = await run_cascade_test(q)
        passed = print_checks(checks, state, duration)
        results.append((q["id"], passed, duration))

        # Save state if requested
        if args.output and state:
            fname = f"{args.output}_{q['id']}.json"
            # Truncate large fields for readability
            save_state = {}
            for k, v in state.items():
                if isinstance(v, dict) and len(json.dumps(v, default=str)) > 10000:
                    save_state[k] = {"_truncated": True, "_keys": list(v.keys()) if isinstance(v, dict) else "large"}
                elif isinstance(v, list) and len(v) > 20:
                    save_state[k] = v[:5] + [{"_truncated": f"{len(v)} items total"}]
                else:
                    save_state[k] = v
            with open(fname, "w") as f:
                json.dump(save_state, f, indent=2, default=str)
            print(f"  State saved to {fname}")

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    all_pass = True
    for qid, passed, dur in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {qid} ({dur:.1f}s)")
        if not passed:
            all_pass = False

    total_time = sum(d for _, _, d in results)
    print(f"\n  Overall: {'ALL PASSED' if all_pass else 'SOME FAILED'} ({total_time:.1f}s)")
    print(f"{'='*70}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
