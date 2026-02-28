#!/usr/bin/env python3
"""
V4 Stage-by-Stage Pipeline Test

Runs each V4 agent in order, calling functions directly (NOT via graph.ainvoke).
This lets you verify every stage's output before proceeding to the next.

Handles Send/fan-out patterns manually: scene_designer ×N, content_generator ×M, etc.

Usage:
    cd backend
    PYTHONPATH=. python scripts/test_v4_stage_by_stage.py
    PYTHONPATH=. python scripts/test_v4_stage_by_stage.py --start-from game_concept_designer
    PYTHONPATH=. python scripts/test_v4_stage_by_stage.py --stop-after graph_builder
    PYTHONPATH=. python scripts/test_v4_stage_by_stage.py --question "Explain photosynthesis"
"""

import asyncio
import json
import os
import sys
import time
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Output directory
OUTPUT_DIR = Path("test_outputs/v4_stage_by_stage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Defaults
DEFAULT_QUESTION = (
    "Heart anatomy: label the four chambers, trace the blood flow path "
    "through the heart, and arrange the steps of the cardiac cycle in order"
)


# ── Utility ─────────────────────────────────────────────────────────

def _json_safe(obj):
    """Make any object JSON serializable."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_json_safe(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return f"<bytes: {len(obj)} bytes>"
    elif hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "__dict__") and not isinstance(obj, type):
        return str(obj)
    return obj


def save_output(name: str, data: dict, num: int):
    fp = OUTPUT_DIR / f"{num:02d}_{name}.json"
    with open(fp, "w") as f:
        json.dump(_json_safe(data), f, indent=2, default=str)
    return fp


def save_state(state: dict, name: str):
    fp = OUTPUT_DIR / f"state_after_{name}.json"
    with open(fp, "w") as f:
        json.dump(_json_safe(state), f, indent=2, default=str)
    return fp


def load_state(name: str) -> dict:
    fp = OUTPUT_DIR / f"state_after_{name}.json"
    if not fp.exists():
        raise FileNotFoundError(f"No saved state after '{name}'. Run from start first.")
    with open(fp) as f:
        return json.load(f)


def header(num, name, desc):
    w = 80
    print("\n" + "=" * w)
    print(f"  STAGE {num}: {name}")
    print(f"  {desc}")
    print("=" * w)


def summarize(name: str, output: dict, ms: int, fp: Path):
    keys = [k for k in output if not k.startswith("_") and k not in ("question_text", "question_id", "question_options")]
    print(f"\n  Duration: {ms}ms")
    print(f"  Output saved: {fp}")
    print(f"  Keys written: {', '.join(keys[:15])}")
    return keys


# ── Stage Definitions ───────────────────────────────────────────────

STAGES = [
    # Phase 0: parallel context gathering
    {
        "name": "input_analyzer",
        "description": "LLM: Analyzes question → Bloom's level, subject, difficulty, key concepts",
        "phase": "Phase 0",
    },
    {
        "name": "dk_retriever",
        "description": "LLM+Web: Web search → canonical labels, hierarchical relationships, domain knowledge",
        "phase": "Phase 0",
    },
    {
        "name": "phase0_merge",
        "description": "Deterministic: Merge parallel outputs from input_analyzer + dk_retriever",
        "phase": "Phase 0",
    },
    # Phase 1a: concept design + validation
    {
        "name": "game_concept_designer",
        "description": "LLM: Design game concept — scenes, mechanic choices, zone labels, narrative",
        "phase": "Phase 1a",
    },
    {
        "name": "concept_validator",
        "description": "Deterministic: Validate game concept schema and content quality",
        "phase": "Phase 1a",
    },
    # Phase 1b: parallel scene design
    {
        "name": "scene_designers",
        "description": "LLM ×N: Parallel scene creative design (visual style, mechanic designs, image specs)",
        "phase": "Phase 1b",
        "fanout": True,
    },
    {
        "name": "scene_design_merge",
        "description": "Deterministic: Merge + deduplicate parallel scene designs",
        "phase": "Phase 1b",
    },
    # Graph builder
    {
        "name": "graph_builder",
        "description": "Deterministic: Build GamePlan — assign IDs, compute scores, build connections",
        "phase": "Graph Builder",
    },
    {
        "name": "game_plan_validator",
        "description": "Deterministic: Validate game plan scores and structure",
        "phase": "Graph Builder",
    },
    # Phase 2a: parallel content generation
    {
        "name": "content_generators",
        "description": "LLM ×M: Generate mechanic content — visual config, data fields, labels/items",
        "phase": "Phase 2a",
        "fanout": True,
    },
    {
        "name": "content_merge",
        "description": "Deterministic: Merge + deduplicate parallel content results",
        "phase": "Phase 2a",
    },
    # Phase 2b: parallel interaction design
    {
        "name": "interaction_designers",
        "description": "LLM ×N: Design scoring, feedback, transitions per scene",
        "phase": "Phase 2b",
        "fanout": True,
    },
    {
        "name": "interaction_merge",
        "description": "Deterministic: Merge + deduplicate parallel interaction results",
        "phase": "Phase 2b",
    },
    # Phase 3: assets
    {
        "name": "asset_workers",
        "description": "Web+Vision: Image search + zone detection per scene",
        "phase": "Phase 3",
        "fanout": True,
    },
    {
        "name": "asset_merge",
        "description": "Deterministic: Merge + deduplicate parallel asset results",
        "phase": "Phase 3",
    },
    # Phase 4: assembly
    {
        "name": "assembler",
        "description": "Deterministic: Assemble final blueprint from all upstream outputs",
        "phase": "Phase 4",
    },
]

STAGE_NAMES = [s["name"] for s in STAGES]


# ── Stage Runners ───────────────────────────────────────────────────

async def run_input_analyzer(state: dict) -> dict:
    from app.v4.agents.input_analyzer import input_analyzer
    return await input_analyzer(state)


async def run_dk_retriever(state: dict) -> dict:
    from app.v4.agents.dk_retriever import dk_retriever
    return await dk_retriever(state)


async def run_phase0_merge(state: dict) -> dict:
    from app.v4.merge_nodes import phase0_merge
    return phase0_merge(state)


async def run_game_concept_designer(state: dict) -> dict:
    from app.v4.agents.game_concept_designer import game_concept_designer
    return await game_concept_designer(state)


async def run_concept_validator(state: dict) -> dict:
    """Runs concept_validator_node from graph.py (wraps validate_game_concept)."""
    from app.v4.schemas.game_concept import GameConcept
    from app.v4.validators.concept_validator import validate_game_concept

    concept_raw = state.get("game_concept")
    if not concept_raw:
        return {"concept_validation": {"passed": False, "score": 0.0, "issues": [{"severity": "error", "message": "No game_concept"}]}}
    try:
        concept = GameConcept(**concept_raw)
        result = validate_game_concept(concept)
        return {"concept_validation": result.model_dump()}
    except Exception as e:
        return {"concept_validation": {"passed": False, "score": 0.0, "issues": [{"severity": "error", "message": str(e)}]}}


async def run_scene_designers(state: dict) -> dict:
    """Fan-out: run scene_designer for each scene in game_concept."""
    from app.v4.agents.scene_designer import scene_designer
    from app.v4.routers import scene_design_send_router

    sends = scene_design_send_router(state)
    print(f"  Dispatching {len(sends)} scene designers...")

    all_raw = []
    for i, send in enumerate(sends):
        payload = send.arg  # Send object uses .arg (singular)
        scene_idx = payload.get("scene_index", i)
        scene_title = payload.get("scene_concept", {}).get("title", f"Scene {scene_idx+1}")
        print(f"    [{i+1}/{len(sends)}] Designing scene: {scene_title}")

        t0 = time.time()
        result = await scene_designer(payload)
        ms = int((time.time() - t0) * 1000)

        raw_items = result.get("scene_creative_designs_raw", [])
        all_raw.extend(raw_items)
        status = "OK" if raw_items else "EMPTY"
        print(f"    [{i+1}/{len(sends)}] {status} ({ms}ms) — {len(raw_items)} design(s)")

    return {"scene_creative_designs_raw": all_raw}


async def run_scene_design_merge(state: dict) -> dict:
    from app.v4.merge_nodes import scene_design_merge
    return scene_design_merge(state)


async def run_graph_builder(state: dict) -> dict:
    from app.v4.graph_builder import graph_builder_node
    return graph_builder_node(state)


async def run_game_plan_validator(state: dict) -> dict:
    """Runs game_plan_validator_node from graph.py."""
    from app.v4.schemas.game_plan import GamePlan
    from app.v4.validators.game_plan_validator import validate_game_plan

    plan_raw = state.get("game_plan")
    if not plan_raw:
        return {"design_validation": {"passed": False, "score": 0.0, "issues": [{"severity": "error", "message": "No game_plan"}]}}
    try:
        plan = GamePlan(**plan_raw)
        result = validate_game_plan(plan)
        return {"game_plan": plan.model_dump(), "design_validation": result.model_dump()}
    except Exception as e:
        return {"design_validation": {"passed": False, "score": 0.0, "issues": [{"severity": "error", "message": str(e)}]}}


async def run_content_generators(state: dict) -> dict:
    """Fan-out: run content_generator for each mechanic in game_plan."""
    from app.v4.agents.content_generator import content_generator
    from app.v4.routers import content_dispatch_router

    sends = content_dispatch_router(state)
    print(f"  Dispatching {len(sends)} content generators...")

    all_raw = []
    for i, send in enumerate(sends):
        payload = send.arg
        mech = payload.get("mechanic_plan", {})
        mtype = mech.get("mechanic_type", "?")
        mid = mech.get("mechanic_id", "?")
        print(f"    [{i+1}/{len(sends)}] Generating content: {mid} ({mtype})")

        t0 = time.time()
        result = await content_generator(payload)
        ms = int((time.time() - t0) * 1000)

        raw_items = result.get("mechanic_contents_raw", [])
        all_raw.extend(raw_items)
        status_val = raw_items[0].get("status", "?") if raw_items else "EMPTY"
        print(f"    [{i+1}/{len(sends)}] {status_val} ({ms}ms)")

    return {"mechanic_contents_raw": all_raw}


async def run_content_merge(state: dict) -> dict:
    from app.v4.merge_nodes import content_merge
    return content_merge(state)


async def run_interaction_designers(state: dict) -> dict:
    """Fan-out: run interaction_designer for each scene."""
    from app.v4.agents.interaction_designer import interaction_designer
    from app.v4.routers import interaction_dispatch_router

    result = interaction_dispatch_router(state)

    # If it returns a string, no scenes to process
    if isinstance(result, str):
        print(f"  Router returned '{result}' — skipping interaction design")
        return {"interaction_results_raw": []}

    sends = result
    print(f"  Dispatching {len(sends)} interaction designers...")

    all_raw = []
    for i, send in enumerate(sends):
        payload = send.arg
        sid = payload.get("scene_plan", {}).get("scene_id", "?")
        print(f"    [{i+1}/{len(sends)}] Designing interactions: {sid}")

        t0 = time.time()
        res = await interaction_designer(payload)
        ms = int((time.time() - t0) * 1000)

        raw_items = res.get("interaction_results_raw", [])
        all_raw.extend(raw_items)
        status_val = raw_items[0].get("status", "?") if raw_items else "EMPTY"
        print(f"    [{i+1}/{len(sends)}] {status_val} ({ms}ms)")

    return {"interaction_results_raw": all_raw}


async def run_interaction_merge(state: dict) -> dict:
    from app.v4.merge_nodes import interaction_merge
    return interaction_merge(state)


async def run_asset_workers(state: dict) -> dict:
    """Fan-out: run asset_worker for each scene needing diagrams."""
    from app.v4.agents.asset_dispatcher import asset_worker
    from app.v4.routers import asset_send_router

    result = asset_send_router(state)

    if isinstance(result, str):
        print(f"  Router returned '{result}' — no scenes need diagrams")
        return {"generated_assets_raw": []}

    sends = result
    print(f"  Dispatching {len(sends)} asset workers...")

    all_raw = []
    for i, send in enumerate(sends):
        payload = send.arg
        sid = payload.get("scene_id", "?")
        labels = payload.get("zone_labels", [])
        print(f"    [{i+1}/{len(sends)}] Processing assets: {sid} ({len(labels)} labels)")

        t0 = time.time()
        res = await asset_worker(payload)
        ms = int((time.time() - t0) * 1000)

        raw_items = res.get("generated_assets_raw", [])
        all_raw.extend(raw_items)
        status_val = raw_items[0].get("status", "?") if raw_items else "EMPTY"
        zones_found = len(raw_items[0].get("zones", [])) if raw_items else 0
        print(f"    [{i+1}/{len(sends)}] {status_val} ({ms}ms) — {zones_found} zones detected")

    return {"generated_assets_raw": all_raw}


async def run_asset_merge(state: dict) -> dict:
    from app.v4.merge_nodes import asset_merge
    return asset_merge(state)


async def run_assembler(state: dict) -> dict:
    from app.v4.agents.assembler_node import assembler_node
    return assembler_node(state)


# Stage name → runner function
RUNNERS = {
    "input_analyzer": run_input_analyzer,
    "dk_retriever": run_dk_retriever,
    "phase0_merge": run_phase0_merge,
    "game_concept_designer": run_game_concept_designer,
    "concept_validator": run_concept_validator,
    "scene_designers": run_scene_designers,
    "scene_design_merge": run_scene_design_merge,
    "graph_builder": run_graph_builder,
    "game_plan_validator": run_game_plan_validator,
    "content_generators": run_content_generators,
    "content_merge": run_content_merge,
    "interaction_designers": run_interaction_designers,
    "interaction_merge": run_interaction_merge,
    "asset_workers": run_asset_workers,
    "asset_merge": run_asset_merge,
    "assembler": run_assembler,
}


# ── Pretty Printers ─────────────────────────────────────────────────

def print_stage_output(name: str, output: dict, state: dict):
    """Print stage-specific summary."""

    if name == "input_analyzer":
        ped = output.get("pedagogical_context", {})
        if ped:
            print(f"  Bloom's level: {ped.get('blooms_level')}")
            print(f"  Subject: {ped.get('subject')}")
            print(f"  Difficulty: {ped.get('difficulty')}")
            print(f"  Objectives ({len(ped.get('learning_objectives', []))}):")
            for obj in ped.get("learning_objectives", [])[:4]:
                print(f"    - {obj}")
            print(f"  Key concepts: {ped.get('key_concepts', [])[:6]}")

    elif name == "dk_retriever":
        dk = output.get("domain_knowledge", {})
        if dk:
            labels = dk.get("canonical_labels", [])
            print(f"  Canonical labels ({len(labels)}): {labels[:8]}")
            rels = dk.get("hierarchical_relationships", [])
            print(f"  Relationships: {len(rels)}")
            seq = dk.get("sequence_flow_data")
            print(f"  Sequence data: {'Yes' if seq else 'No'}")

    elif name == "phase0_merge":
        print(f"  pedagogical_context: {'present' if output.get('pedagogical_context') else 'MISSING'}")
        print(f"  domain_knowledge: {'present' if output.get('domain_knowledge') else 'MISSING'}")

    elif name == "game_concept_designer":
        gc = output.get("game_concept", {})
        if gc:
            print(f"  Title: {gc.get('title')}")
            print(f"  Narrative theme: {gc.get('narrative_theme', '')[:80]}")
            scenes = gc.get("scenes", [])
            print(f"  Scenes: {len(scenes)}")
            for s in scenes:
                mechs = s.get("mechanics", [])
                mech_types = [m.get("mechanic_type") for m in mechs]
                zone_labels = s.get("zone_labels", [])
                print(f"    {s.get('title')}: mechanics={mech_types}, zone_labels={len(zone_labels)}")
            all_labels = gc.get("all_zone_labels", [])
            print(f"  All zone labels ({len(all_labels)}): {all_labels[:10]}")
            print(f"  Distractor labels: {gc.get('distractor_labels', [])[:6]}")

    elif name == "concept_validator":
        cv = output.get("concept_validation", {})
        passed = cv.get("passed", False)
        issues = cv.get("issues", [])
        print(f"  Passed: {passed}")
        print(f"  Score: {cv.get('score', 0)}")
        if issues:
            for issue in issues[:5]:
                sev = issue.get("severity", "?")
                msg = issue.get("message", "")
                print(f"    [{sev}] {msg}")

    elif name == "scene_designers":
        raw = output.get("scene_creative_designs_raw", [])
        print(f"  Raw designs: {len(raw)}")
        for d in raw:
            sid = d.get("scene_id", "?")
            title = d.get("title", "?")
            mds = d.get("mechanic_designs", [])
            img = d.get("image_spec", {})
            print(f"    {sid}: '{title}' — {len(mds)} mechanic designs, image_spec={'yes' if img else 'no'}")
            for md in mds:
                print(f"      {md.get('mechanic_type')}: visual={md.get('visual_style', '?')[:40]}, goal={md.get('generation_goal', '?')[:40]}")

    elif name == "scene_design_merge":
        designs = output.get("scene_creative_designs", {})
        validation = output.get("scene_design_validation", {})
        print(f"  Merged designs: {len(designs)}")
        for sid, d in designs.items():
            mds = d.get("mechanic_designs", []) if isinstance(d, dict) else []
            print(f"    {sid}: {len(mds)} mechanic designs")
        print(f"  Validation: {json.dumps(validation, default=str)[:200]}")

    elif name == "graph_builder":
        gp = output.get("game_plan", {})
        if gp:
            print(f"  Title: {gp.get('title')}")
            print(f"  Total max score: {gp.get('total_max_score')}")
            scenes = gp.get("scenes", [])
            print(f"  Scenes: {len(scenes)}")
            for s in scenes:
                sid = s.get("scene_id")
                mechs = s.get("mechanics", [])
                smx = s.get("scene_max_score", 0)
                print(f"    {sid} (score={smx}):")
                for m in mechs:
                    print(f"      {m.get('mechanic_id')}: {m.get('mechanic_type')} "
                          f"(items={m.get('expected_item_count')} × {m.get('points_per_item')}pts = {m.get('max_score')})")
                    cd = m.get("creative_design", {})
                    if cd:
                        print(f"        creative_design: type={cd.get('mechanic_type')}, style={cd.get('visual_style', '?')[:40]}")
                conns = s.get("mechanic_connections", [])
                if conns:
                    print(f"    Connections: {[(c.get('from_mechanic_id'), c.get('trigger'), c.get('to_mechanic_id')) for c in conns]}")

    elif name == "game_plan_validator":
        dv = output.get("design_validation", {})
        print(f"  Passed: {dv.get('passed')}")
        print(f"  Score: {dv.get('score')}")
        issues = dv.get("issues", [])
        if issues:
            for issue in issues[:5]:
                print(f"    [{issue.get('severity')}] {issue.get('message')}")

    elif name in ("content_generators", "content_merge"):
        key = "mechanic_contents_raw" if name == "content_generators" else "mechanic_contents"
        contents = output.get(key, [])
        print(f"  Content results: {len(contents)}")
        for c in contents:
            mid = c.get("mechanic_id", "?")
            mtype = c.get("mechanic_type", "?")
            status = c.get("status", "?")
            content = c.get("content", {})
            data_keys = [k for k in content.keys() if k not in ("_llm_metrics",)] if isinstance(content, dict) else []
            print(f"    {mid} ({mtype}): {status} — content keys: {data_keys[:10]}")

    elif name in ("interaction_designers", "interaction_merge"):
        key = "interaction_results_raw" if name == "interaction_designers" else "interaction_results"
        results = output.get(key, [])
        print(f"  Interaction results: {len(results)}")
        for r in results:
            sid = r.get("scene_id", "?")
            scoring = r.get("mechanic_scoring", {})
            feedback = r.get("mechanic_feedback", {})
            print(f"    {sid}: {len(scoring)} scoring rules, {len(feedback)} feedback rules")

    elif name in ("asset_workers", "asset_merge"):
        key = "generated_assets_raw" if name == "asset_workers" else "generated_assets"
        assets = output.get(key, [])
        print(f"  Asset results: {len(assets)}")
        for a in assets:
            sid = a.get("scene_id", "?")
            status = a.get("status", "?")
            url = a.get("diagram_url", a.get("image_url", ""))
            zones = a.get("zones", [])
            print(f"    {sid}: {status} — url={url[:60] if url else 'N/A'}, zones={len(zones)}")

    elif name == "assembler":
        bp = output.get("blueprint", {})
        warnings = output.get("assembly_warnings", [])
        complete = output.get("generation_complete")
        if bp:
            print(f"  Template: {bp.get('templateType')}")
            print(f"  Title: {bp.get('title')}")
            print(f"  Total max score: {bp.get('totalMaxScore')}")
            mechanics = bp.get("mechanics", [])
            print(f"  Mechanics: {[m.get('type') for m in mechanics]}")
            diagram = bp.get("diagram", {})
            zones = diagram.get("zones", [])
            labels = bp.get("labels", [])
            print(f"  Zones: {len(zones)}")
            print(f"  Labels: {len(labels)}")
            if diagram.get("imageUrl") or diagram.get("assetUrl"):
                print(f"  Diagram URL: {(diagram.get('imageUrl') or diagram.get('assetUrl', ''))[:80]}")
            gs = bp.get("game_sequence", {})
            if gs:
                gs_scenes = gs.get("scenes", [])
                print(f"  Game sequence: {len(gs_scenes)} scenes, progression={gs.get('progression_type')}")
            bp_size = len(json.dumps(bp, default=str))
            print(f"  Blueprint size: {bp_size:,} chars")
        else:
            print(f"  Blueprint: MISSING/EMPTY")
        if warnings:
            print(f"  Warnings ({len(warnings)}):")
            for w in warnings[:5]:
                print(f"    - {w}")
        print(f"  generation_complete: {complete}")

    print()


# ── Main ────────────────────────────────────────────────────────────

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="V4 Stage-by-Stage Pipeline Test")
    parser.add_argument("--start-from", type=str, default=None, help="Resume from stage name")
    parser.add_argument("--stop-after", type=str, default=None, help="Stop after stage name")
    parser.add_argument("--question", type=str, default=DEFAULT_QUESTION)
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  V4 STAGE-BY-STAGE PIPELINE TEST")
    print(f"  Question: {args.question[:70]}...")
    print(f"  Output dir: {OUTPUT_DIR.absolute()}")
    print("=" * 80)

    # ── Prerequisite checks ──
    print("\n── Prerequisites ──")
    google_key = os.environ.get("GOOGLE_API_KEY")
    serper_key = os.environ.get("SERPER_API_KEY")
    print(f"  GOOGLE_API_KEY: {'SET' if google_key else 'NOT SET'}")
    print(f"  SERPER_API_KEY: {'SET' if serper_key else 'NOT SET'}")
    if not google_key:
        print("  ERROR: GOOGLE_API_KEY required for LLM calls")
        sys.exit(1)
    if not serper_key:
        print("  WARNING: SERPER_API_KEY not set — dk_retriever will use fallback")

    # ── Initialize state ──
    start_idx = 0
    if args.start_from:
        if args.start_from not in STAGE_NAMES:
            print(f"\nERROR: Unknown stage '{args.start_from}'")
            print(f"Available: {STAGE_NAMES}")
            return
        start_idx = STAGE_NAMES.index(args.start_from)

    if start_idx == 0:
        state = {
            "question_text": args.question,
            "question_id": f"test_v4_{int(time.time())}",
            "question_options": None,
            "_run_id": f"test_v4_{int(time.time())}",
            "_pipeline_preset": "v4",
            # Initialize reducer fields (normally done by LangGraph)
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
    else:
        prev_name = STAGE_NAMES[start_idx - 1]
        print(f"\n  Resuming from '{args.start_from}', loading state after '{prev_name}'...")
        state = load_state(prev_name)
        print(f"  State loaded ({len(state)} keys)")

    # ── Run stages ──
    results = []

    # Phase 0 special: input_analyzer and dk_retriever run in parallel
    if start_idx == 0:
        header(1, "input_analyzer + dk_retriever (PARALLEL)", "LLM: Analyze question + Web search for domain knowledge")

        t0 = time.time()
        try:
            ia_result, dk_result = await asyncio.gather(
                run_input_analyzer(state),
                run_dk_retriever(state),
            )
            ms = int((time.time() - t0) * 1000)

            # Print input_analyzer
            print("\n  ── input_analyzer ──")
            print_stage_output("input_analyzer", ia_result, state)
            save_output("input_analyzer", ia_result, 1)

            # Print dk_retriever
            print("  ── dk_retriever ──")
            print_stage_output("dk_retriever", dk_result, state)
            save_output("dk_retriever", dk_result, 2)

            # Merge into state
            state.update(ia_result)
            state.update(dk_result)
            save_state(state, "dk_retriever")

            results.append({"stage": 1, "name": "input_analyzer + dk_retriever", "status": "OK", "duration_ms": ms})
            print(f"  Total Phase 0 (parallel): {ms}ms")
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            print(f"\n  FAILED: {e}")
            traceback.print_exc()
            results.append({"stage": 1, "name": "input_analyzer + dk_retriever", "status": "FAILED", "duration_ms": ms, "error": str(e)})
            save_state(state, "dk_retriever")
            return _print_summary(results)

        # Now run phase0_merge
        header(2, "phase0_merge", "Deterministic: Merge parallel outputs")
        t0 = time.time()
        try:
            merge_result = await run_phase0_merge(state)
            ms = int((time.time() - t0) * 1000)
            print_stage_output("phase0_merge", merge_result, state)
            save_output("phase0_merge", merge_result, 3)
            state.update(merge_result)
            save_state(state, "phase0_merge")
            results.append({"stage": 2, "name": "phase0_merge", "status": "OK", "duration_ms": ms})
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            print(f"\n  FAILED: {e}")
            traceback.print_exc()
            results.append({"stage": 2, "name": "phase0_merge", "status": "FAILED", "duration_ms": ms, "error": str(e)})
            return _print_summary(results)

        # Skip to stage after phase0_merge
        start_idx = STAGE_NAMES.index("game_concept_designer")

        if args.stop_after in ("input_analyzer", "dk_retriever", "phase0_merge"):
            print(f"\n  Stopping after '{args.stop_after}' as requested.")
            return _print_summary(results)

    # Run remaining stages sequentially
    stage_num = len(results) + 1
    for i in range(start_idx, len(STAGES)):
        stage = STAGES[i]
        name = stage["name"]

        # Skip Phase 0 stages if we already ran them
        if name in ("input_analyzer", "dk_retriever", "phase0_merge"):
            continue

        header(stage_num, f"{name} [{stage['phase']}]", stage["description"])

        runner = RUNNERS.get(name)
        if not runner:
            print(f"  ERROR: No runner for '{name}'")
            continue

        t0 = time.time()
        try:
            output = await runner(state)
            ms = int((time.time() - t0) * 1000)

            fp = save_output(name, output, stage_num)
            summarize(name, output, ms, fp)
            print_stage_output(name, output, state)

            # Merge output into state
            # For reducer fields, we need to extend lists instead of replace
            for k, v in output.items():
                if k in state and isinstance(state[k], list) and isinstance(v, list) and k.endswith("_raw"):
                    state[k] = state[k] + v
                else:
                    state[k] = v

            save_state(state, name)
            results.append({"stage": stage_num, "name": name, "status": "OK", "duration_ms": ms})

            # Check for errors
            if output.get("error_message"):
                print(f"  WARNING: {output['error_message']}")

        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            print(f"\n  FAILED after {ms}ms: {type(e).__name__}: {e}")
            traceback.print_exc()
            save_state(state, name)
            results.append({"stage": stage_num, "name": name, "status": "FAILED", "duration_ms": ms, "error": str(e)})

            next_name = STAGE_NAMES[i + 1] if i + 1 < len(STAGES) else "END"
            print(f"\n  State saved. Resume with: --start-from {next_name}")
            break

        stage_num += 1

        if args.stop_after and name == args.stop_after:
            print(f"\n  Stopping after '{args.stop_after}' as requested.")
            break

    _print_summary(results)


def _print_summary(results: list[dict]):
    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)

    total_ms = sum(r["duration_ms"] for r in results)
    for r in results:
        icon = "+" if r["status"] == "OK" else "X"
        err = f" — {r.get('error', '')[:60]}" if r.get("error") else ""
        print(f"  {icon} Stage {r['stage']:2d}: {r['name']:<35s} {r['status']:<8s} {r['duration_ms']:>6d}ms{err}")

    print(f"\n  Total: {total_ms}ms ({total_ms/1000:.1f}s)")
    print(f"  Output dir: {OUTPUT_DIR.absolute()}/")

    # Save summary
    summary_fp = OUTPUT_DIR / "00_summary.json"
    with open(summary_fp, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "stages": results,
            "total_duration_ms": total_ms,
        }, f, indent=2)

    failed = [r for r in results if r["status"] == "FAILED"]
    if failed:
        print(f"\n  {len(failed)} stage(s) FAILED")
        sys.exit(1)
    else:
        print(f"\n  All {len(results)} stages PASSED")


if __name__ == "__main__":
    asyncio.run(main())
