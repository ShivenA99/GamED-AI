"""
Stage-by-Stage Pipeline Test

Runs each agent in isolation, saving outputs to test_outputs/ folder.
Feeds the output of each stage into the next to verify the full pipeline.

Usage:
    cd backend
    PYTHONPATH=. python scripts/test_stage_by_stage.py

Options:
    --start-from <agent_name>   Resume from a specific agent (loads prior state)
    --question <text>           Custom question (default: "Label the parts of the human heart")
"""

import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from copy import deepcopy

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
from dotenv import load_dotenv
load_dotenv()

from app.agents.state import create_initial_state

# Output directory
OUTPUT_DIR = Path("test_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Test question
DEFAULT_QUESTION = "Label the parts of the human heart"
DEFAULT_OPTIONS = [
    "Left ventricle", "Right ventricle", "Left atrium", "Right atrium",
    "Aorta", "Pulmonary artery", "Superior vena cava", "Inferior vena cava"
]

# Pipeline stages in order
STAGES = [
    {
        "name": "input_enhancer",
        "import": "from app.agents.input_enhancer import input_enhancer_agent",
        "func": "input_enhancer_agent",
        "description": "Analyzes question → Bloom's level, subject, difficulty, objectives",
    },
    {
        "name": "domain_knowledge_retriever",
        "import": "from app.agents.domain_knowledge_retriever import domain_knowledge_retriever_agent",
        "func": "domain_knowledge_retriever_agent",
        "description": "Web search → canonical labels, hierarchical relationships, domain knowledge",
    },
    {
        "name": "router",
        "import": "from app.agents.router import router_agent",
        "func": "router_agent",
        "description": "Selects optimal game template (INTERACTIVE_DIAGRAM, etc.)",
    },
    {
        "name": "game_designer",
        "import": "from app.agents.game_designer import game_designer_agent",
        "func": "game_designer_agent",
        "description": "Unconstrained creative game design → GameDesign with scenes",
    },
    {
        "name": "design_interpreter",
        "import": "from app.agents.design_interpreter import design_interpreter_agent",
        "func": "design_interpreter_agent",
        "description": "Maps unconstrained GameDesign → structured GamePlan with mechanics",
    },
    {
        "name": "interaction_designer",
        "import": "from app.agents.interaction_designer import interaction_designer",
        "func": "interaction_designer",
        "description": "Designs per-scene interaction patterns, modes, scoring, animations",
    },
    {
        "name": "interaction_validator",
        "import": "from app.agents.interaction_validator import interaction_validator",
        "func": "interaction_validator",
        "description": "Validates interaction design for playability and alignment",
    },
    {
        "name": "scene_stage1_structure",
        "import": "from app.agents.scene_stage1_structure import scene_stage1_structure",
        "func": "scene_stage1_structure",
        "description": "Stage 1: Generates visual theme, layout, and region definitions",
    },
    {
        "name": "scene_stage2_assets",
        "import": "from app.agents.scene_stage2_assets import scene_stage2_assets",
        "func": "scene_stage2_assets",
        "description": "Stage 2: Generates detailed asset specifications for each region",
    },
    {
        "name": "scene_stage3_interactions",
        "import": "from app.agents.scene_stage3_interactions import scene_stage3_interactions",
        "func": "scene_stage3_interactions",
        "description": "Stage 3: Generates animations, behaviors, state transitions",
    },
    {
        "name": "asset_planner",
        "import": "from app.agents.asset_planner import asset_planner",
        "func": "asset_planner",
        "description": "Plans all assets needed from scene data and zones",
    },
    {
        "name": "asset_generator_orchestrator",
        "import": "from app.agents.asset_generator_orchestrator import asset_generator_orchestrator",
        "func": "asset_generator_orchestrator",
        "description": "Executes workflow_execution_plan (labeling_diagram_workflow) or legacy asset generation",
    },
    {
        "name": "asset_validator",
        "import": "from app.agents.asset_validator import asset_validator",
        "func": "asset_validator",
        "description": "Validates all generated assets exist, have correct formats, and meet requirements",
    },
    {
        "name": "blueprint_generator",
        "import": "from app.agents.blueprint_generator import blueprint_generator_agent",
        "func": "blueprint_generator_agent",
        "description": "Creates complete game blueprint with zones, interactions, scoring",
    },
]


def save_output(stage_name: str, data: dict, stage_num: int):
    """Save stage output as JSON."""
    # Extract only the keys that changed (not the full state)
    output_file = OUTPUT_DIR / f"{stage_num:02d}_{stage_name}.json"

    # Make JSON-safe copy
    safe_data = _make_json_safe(data)

    with open(output_file, "w") as f:
        json.dump(safe_data, f, indent=2, default=str)

    return output_file


def save_state(state: dict, stage_name: str):
    """Save full accumulated state."""
    state_file = OUTPUT_DIR / f"state_after_{stage_name}.json"
    safe_state = _make_json_safe(state)
    with open(state_file, "w") as f:
        json.dump(safe_state, f, indent=2, default=str)
    return state_file


def load_state(stage_name: str) -> dict:
    """Load state from after a specific stage."""
    state_file = OUTPUT_DIR / f"state_after_{stage_name}.json"
    if not state_file.exists():
        raise FileNotFoundError(f"No saved state for stage '{stage_name}'. Run from the beginning first.")
    with open(state_file) as f:
        return json.load(f)


def _make_json_safe(obj):
    """Convert non-serializable objects."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return f"<bytes: {len(obj)} bytes>"
    elif hasattr(obj, '__dict__'):
        return str(obj)
    return obj


def print_stage_header(stage_num: int, stage_name: str, description: str):
    """Print a formatted stage header."""
    width = 80
    print("\n" + "=" * width)
    print(f"  STAGE {stage_num}: {stage_name}")
    print(f"  {description}")
    print("=" * width)


def print_stage_result(stage_name: str, output: dict, duration_ms: int, output_file: Path):
    """Print a formatted result summary."""
    # Extract interesting keys from output (not full state)
    interesting_keys = [k for k in output.keys() if k not in (
        "question_id", "question_text", "question_options",
        "current_agent", "last_updated_at"
    ) and not k.startswith("_")]

    print(f"\n  Duration: {duration_ms}ms")
    print(f"  Output saved: {output_file}")
    print(f"  Keys written: {', '.join(interesting_keys[:10])}")

    # Stage-specific summaries
    if stage_name == "input_enhancer":
        ped = output.get("pedagogical_context", {})
        if ped:
            print(f"  Bloom's: {ped.get('blooms_level')}")
            print(f"  Subject: {ped.get('subject')}")
            print(f"  Difficulty: {ped.get('difficulty')}")
            print(f"  Objectives: {ped.get('learning_objectives', [])[:3]}")

    elif stage_name == "domain_knowledge_retriever":
        dk = output.get("domain_knowledge", {})
        if dk:
            labels = dk.get("canonical_labels", [])
            print(f"  Labels ({len(labels)}): {labels[:8]}")
            rels = dk.get("hierarchical_relationships", [])
            print(f"  Relationships: {len(rels)}")
            seq = dk.get("sequence_flow_data")
            print(f"  Sequence data: {'Yes' if seq else 'No'}")

    elif stage_name == "router":
        ts = output.get("template_selection", {})
        if ts:
            print(f"  Template: {ts.get('template_type')}")
            print(f"  Confidence: {ts.get('confidence')}")
            print(f"  Reasoning: {ts.get('reasoning', '')[:100]}")

    elif stage_name == "game_designer":
        gd = output.get("game_design", {})
        if gd:
            print(f"  Title: {gd.get('title')}")
            scenes = gd.get("scenes", [])
            print(f"  Scenes: {len(scenes)}")
            for s in scenes[:3]:
                print(f"    Scene {s.get('scene_number')}: {s.get('title')} — {s.get('interaction_description', '')[:80]}")
            print(f"  Progression: {gd.get('progression_type')}")

    elif stage_name == "design_interpreter":
        gp = output.get("game_plan", {})
        if gp:
            mechanics = gp.get("game_mechanics", [])
            print(f"  Mechanics: {[m.get('type') for m in mechanics]}")
            sb = gp.get("scene_breakdown") or output.get("scene_breakdown", [])
            print(f"  Scene breakdown: {len(sb) if sb else 0} scenes")
            if sb:
                for s in sb[:3]:
                    s_mechs = [m.get("type") for m in s.get("mechanics", [])]
                    print(f"    Scene {s.get('scene_number')}: mechanics={s_mechs}")
        nm = output.get("needs_multi_scene")
        print(f"  Multi-scene: {nm}")

    elif stage_name == "interaction_designer":
        idesign = output.get("interaction_design", {})
        if idesign:
            print(f"  Primary mode: {idesign.get('primary_interaction_mode')}")
            print(f"  Zone count: {idesign.get('zone_count')}")
            scoring = idesign.get("scoring_strategy", {})
            print(f"  Scoring: {scoring.get('base_points_per_zone', '?')} pts/zone")
        idesigns = output.get("interaction_designs", [])
        if idesigns:
            print(f"  Per-scene designs: {len(idesigns)}")

    elif stage_name == "interaction_validator":
        iv = output.get("interaction_validation", {})
        if iv:
            print(f"  Valid: {iv.get('is_valid')}")
            print(f"  Score: {iv.get('quality_score')}")
            issues = iv.get("issues", [])
            if issues:
                print(f"  Issues ({len(issues)}): {issues[:3]}")

    elif stage_name == "scene_stage1_structure":
        ss = output.get("scene_structure", {})
        if ss:
            print(f"  Theme: {ss.get('visual_theme')}")
            print(f"  Layout: {ss.get('layout_type')}")
            regions = ss.get("regions", [])
            print(f"  Regions: {len(regions)}")

    elif stage_name == "scene_stage2_assets":
        sa = output.get("scene_assets", {})
        if sa:
            assets = sa.get("required_assets", [])
            print(f"  Assets: {len(assets)}")
            for a in assets[:5]:
                print(f"    {a.get('id')}: {a.get('type')} — {a.get('description', '')[:60]}")

    elif stage_name == "scene_stage3_interactions":
        si = output.get("scene_interactions", {})
        if si:
            interactions = si.get("asset_interactions", [])
            animations = si.get("animation_sequences", [])
            print(f"  Interactions: {len(interactions)}")
            print(f"  Animations: {len(animations)}")
        sd = output.get("scene_data", {})
        if sd:
            print(f"  scene_data keys: {list(sd.keys())}")

    elif stage_name == "asset_planner":
        pa = output.get("planned_assets", [])
        if pa:
            print(f"  Planned assets: {len(pa)}")
            for a in pa[:5]:
                print(f"    {a.get('id')}: {a.get('type')} (priority={a.get('priority')})")
        wep = output.get("workflow_execution_plan", {})
        if wep:
            print(f"  Workflow plan: {list(wep.keys()) if isinstance(wep, dict) else 'present'}")

    elif stage_name == "asset_generator_orchestrator":
        ga = output.get("generated_assets", {})
        if isinstance(ga, dict):
            print(f"  Generated assets: {len(ga)} (Dict mode)")
            for aid, aval in list(ga.items())[:5]:
                if isinstance(aval, dict):
                    print(f"    {aid}: status={aval.get('status')}, url={str(aval.get('url', aval.get('local_path', 'N/A')))[:80]}")
                else:
                    print(f"    {aid}: {str(aval)[:80]}")
        elif isinstance(ga, list):
            print(f"  Generated assets: {len(ga)} (List mode)")
        else:
            print(f"  Generated assets: {type(ga).__name__}")
        metrics = output.get("asset_generation_metrics", {})
        if metrics:
            print(f"  Mode: {metrics.get('mode', 'unknown')}")
            print(f"  Total: {metrics.get('total_assets', 0)}, Success: {metrics.get('successful', 0)}, Failed: {metrics.get('failed', 0)}")
            print(f"  Duration: {metrics.get('total_duration_ms', 0)}ms")
        er = output.get("entity_registry", {})
        if er:
            print(f"  Entity registry zones: {len(er.get('zones', {}))}")
            print(f"  Entity registry assets: {len(er.get('assets', {}))}")

    elif stage_name == "asset_validator":
        av = output.get("assets_valid")
        print(f"  Assets valid: {av}")
        va = output.get("validated_assets", [])
        print(f"  Validated assets: {len(va) if va else 0}")
        ve = output.get("validation_errors", [])
        if ve:
            print(f"  Validation errors ({len(ve)}):")
            for err in ve[:5]:
                print(f"    - {err}")

    elif stage_name == "blueprint_generator":
        bp = output.get("blueprint", {})
        if bp:
            print(f"  Template: {bp.get('templateType')}")
            print(f"  Title: {bp.get('title')}")
            diagram = bp.get("diagram", {})
            zones = diagram.get("zones", bp.get("zones", []))
            labels = bp.get("labels", [])
            print(f"  Zones: {len(zones)}")
            print(f"  Labels: {len(labels)}")
            if diagram.get("assetUrl"):
                print(f"  Diagram URL: {diagram['assetUrl'][:80]}")
            mechanics = bp.get("mechanics", [])
            print(f"  Mechanics: {[m.get('type') for m in mechanics]}")
            scoring = bp.get("scoringStrategy", {})
            print(f"  Max score: {scoring.get('max_score')}")
            # Check for truncation
            bp_str = json.dumps(bp, default=str)
            print(f"  Blueprint size: {len(bp_str)} chars")

    print()


async def run_stage(stage: dict, state: dict) -> dict:
    """Run a single stage and return the output dict."""
    # Dynamic import
    exec(stage["import"], globals())
    func = eval(stage["func"])

    # Run the agent
    result = await func(state, None)

    return result


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stage-by-stage pipeline test")
    parser.add_argument("--start-from", type=str, default=None, help="Resume from this agent")
    parser.add_argument("--question", type=str, default=DEFAULT_QUESTION, help="Question to test")
    parser.add_argument("--stop-after", type=str, default=None, help="Stop after this agent")
    args = parser.parse_args()

    question_text = args.question
    question_options = DEFAULT_OPTIONS if question_text == DEFAULT_QUESTION else None

    print("\n" + "=" * 80)
    print("  STAGE-BY-STAGE PIPELINE TEST")
    print(f"  Question: {question_text}")
    print(f"  Options: {question_options}")
    print(f"  Output dir: {OUTPUT_DIR.absolute()}")
    print(f"  Preset: {os.environ.get('AGENT_CONFIG_PRESET', 'balanced')}")
    print(f"  Pipeline: {os.environ.get('PIPELINE_PRESET', 'default')}")
    print("=" * 80)

    # Determine starting point
    start_idx = 0
    if args.start_from:
        found = False
        for i, stage in enumerate(STAGES):
            if stage["name"] == args.start_from:
                start_idx = i
                found = True
                break
        if not found:
            print(f"\nERROR: Unknown stage '{args.start_from}'")
            print(f"Available stages: {[s['name'] for s in STAGES]}")
            return

    # Initialize or load state
    if start_idx == 0:
        state = create_initial_state(
            question_id=f"test_{int(time.time())}",
            question_text=question_text,
            question_options=question_options,
        )
        # Set pipeline preset from env
        state["_pipeline_preset"] = os.environ.get("PIPELINE_PRESET", "default")
    else:
        prev_stage = STAGES[start_idx - 1]["name"]
        print(f"\n  Resuming from '{args.start_from}', loading state after '{prev_stage}'...")
        state = load_state(prev_stage)
        print(f"  State loaded ({len(state)} keys)")

    # Run stages
    results_summary = []

    for i in range(start_idx, len(STAGES)):
        stage = STAGES[i]
        stage_num = i + 1

        print_stage_header(stage_num, stage["name"], stage["description"])

        start_time = time.time()
        try:
            output = await run_stage(stage, state)
            duration_ms = int((time.time() - start_time) * 1000)

            # Save stage output (just the new keys)
            output_file = save_output(stage["name"], output, stage_num)

            # Merge output into accumulated state
            if isinstance(output, dict):
                state.update(output)

            # Save full accumulated state
            save_state(state, stage["name"])

            # Print summary
            print_stage_result(stage["name"], output, duration_ms, output_file)

            results_summary.append({
                "stage": stage_num,
                "name": stage["name"],
                "status": "OK",
                "duration_ms": duration_ms,
                "output_file": str(output_file),
            })

            # Check for errors in output
            errors = output.get("current_validation_errors", [])
            error_msg = output.get("error_message", "")
            if errors:
                print(f"  ⚠ Validation errors: {errors}")
            if error_msg:
                print(f"  ⚠ Error message: {error_msg}")

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            print(f"\n  FAILED after {duration_ms}ms")
            print(f"  Error: {type(e).__name__}: {e}")
            traceback.print_exc()

            # Save error info
            error_file = OUTPUT_DIR / f"{stage_num:02d}_{stage['name']}_ERROR.json"
            with open(error_file, "w") as f:
                json.dump({
                    "stage": stage["name"],
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "duration_ms": duration_ms,
                }, f, indent=2)

            results_summary.append({
                "stage": stage_num,
                "name": stage["name"],
                "status": "FAILED",
                "error": str(e),
                "duration_ms": duration_ms,
            })

            # Save state so we can resume from next stage
            save_state(state, stage["name"])

            print(f"\n  State saved. Resume with: --start-from {STAGES[i+1]['name'] if i+1 < len(STAGES) else 'END'}")
            break

        # Check stop condition
        if args.stop_after and stage["name"] == args.stop_after:
            print(f"\n  Stopping after '{args.stop_after}' as requested.")
            break

    # Print final summary
    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)

    total_ms = sum(r["duration_ms"] for r in results_summary)
    for r in results_summary:
        status_icon = "✓" if r["status"] == "OK" else "✗"
        print(f"  {status_icon} Stage {r['stage']:2d}: {r['name']:<30s} {r['status']:<8s} {r['duration_ms']:>6d}ms")

    print(f"\n  Total: {total_ms}ms ({total_ms/1000:.1f}s)")
    print(f"  Output files: {OUTPUT_DIR.absolute()}/")

    # Save summary
    summary_file = OUTPUT_DIR / "00_summary.json"
    with open(summary_file, "w") as f:
        json.dump({
            "question": question_text,
            "options": question_options,
            "preset": os.environ.get("AGENT_CONFIG_PRESET", "balanced"),
            "pipeline": os.environ.get("PIPELINE_PRESET", "default"),
            "timestamp": datetime.utcnow().isoformat(),
            "stages": results_summary,
            "total_duration_ms": total_ms,
        }, f, indent=2)

    print(f"  Summary: {summary_file}")
    print()

    # Return exit code based on results
    failed = [r for r in results_summary if r["status"] == "FAILED"]
    if failed:
        print(f"  {len(failed)} stage(s) FAILED")
        sys.exit(1)
    else:
        print(f"  All {len(results_summary)} stages PASSED")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
