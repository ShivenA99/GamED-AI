"""ACL Demo Batch Generation Script.

Runs the V4 and V4-Algorithm pipelines for 50 pre-defined questions,
saving blueprint + metrics as static JSON for the frontend demo gallery.

Usage:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python scripts/generate_acl_demo.py [--start N] [--end N] [--ids id1,id2]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure we can import from the backend package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env BEFORE importing app modules
# so that AGENT_CONFIG_PRESET is set when agent_models.py loads
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Set agent preset BEFORE any app imports (config is loaded at import time)
os.environ["AGENT_CONFIG_PRESET"] = os.environ.get("ACL_AGENT_PRESET", "gemini_only")

from app.agents import state as agent_state
from app.agents.graph import get_compiled_graph
from app.agents.instrumentation import (
    create_pipeline_run,
    update_pipeline_run_status,
)
from app.db.database import SessionLocal
from app.db.models import Question, Process

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("acl_demo_generator")

SCRIPT_DIR = Path(__file__).resolve().parent
QUERIES_PATH = SCRIPT_DIR / "acl_demo_queries.json"
OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "src"
    / "data"
    / "acl-demo"
    / "games"
)

MAX_RETRIES = 2


def load_queries(start: int = 0, end: Optional[int] = None, ids: Optional[list] = None):
    """Load the 50-game query matrix from JSON."""
    with open(QUERIES_PATH) as f:
        queries = json.load(f)

    if ids:
        queries = [q for q in queries if q["id"] in ids]
    else:
        queries = queries[start:end]

    logger.info(f"Loaded {len(queries)} queries (total available: 50)")
    return queries


async def run_single_game(query: dict, attempt: int = 1) -> dict:
    """Run a single pipeline generation and return the result.

    Returns dict with keys: success, blueprint, metrics, error
    """
    game_id = query["id"]
    game_type = query["gameType"]
    question_text = query["question"]

    # Choose pipeline preset based on game type
    pipeline_preset = "v4_algorithm" if game_type == "algorithm" else "v4"
    topology = "T1"

    logger.info(
        f"[{game_id}] Starting generation (attempt {attempt}, preset={pipeline_preset})"
    )
    start_time = time.time()

    db = SessionLocal()
    try:
        # Create DB records
        question_id = str(uuid.uuid4())
        process_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())

        question = Question(
            id=question_id,
            text=question_text,
        )
        db.add(question)

        process = Process(
            id=process_id,
            question_id=question_id,
            status="processing",
        )
        process.thread_id = thread_id
        db.add(process)
        db.commit()

        run_id = create_pipeline_run(
            process_id=process_id,
            topology=topology,
            config_snapshot={
                "question_id": question_id,
                "question_text": question_text[:200],
                "topology": topology,
                "pipeline_preset": pipeline_preset,
                "acl_demo_id": game_id,
            },
            db=db,
        )

        # Set environment for pipeline — use gemini_only to avoid Anthropic credit issues
        os.environ["PIPELINE_PRESET"] = pipeline_preset
        os.environ["AGENT_CONFIG_PRESET"] = os.environ.get("ACL_AGENT_PRESET", "gemini_only")

        # Create initial state
        if game_type == "algorithm":
            from app.v4_algorithm.state import V4AlgorithmState

            initial_state = {
                "question_text": question_text,
                "question_id": question_id,
                "_run_id": run_id,
                "_pipeline_preset": pipeline_preset,
            }
        else:
            initial_state = agent_state.create_initial_state(
                question_id=question_id,
                question_text=question_text,
                question_options=None,
            )
            initial_state["_run_id"] = run_id
            initial_state["_pipeline_preset"] = pipeline_preset

        # Get the right graph
        graph = get_compiled_graph(topology=topology, preset=pipeline_preset)

        # Run the graph
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 80,
        }

        final_state = await graph.ainvoke(initial_state, config)

        elapsed = time.time() - start_time
        blueprint = final_state.get("blueprint")
        generation_complete = final_state.get("generation_complete", False)

        if not blueprint or not generation_complete:
            error_msg = final_state.get("error_message", "No blueprint generated")
            logger.warning(f"[{game_id}] Generation incomplete: {error_msg}")
            return {
                "success": False,
                "blueprint": None,
                "metrics": None,
                "error": error_msg,
                "elapsed": elapsed,
            }

        # Extract metrics from instrumentation
        agent_history = final_state.get("agent_history", [])
        total_tokens = sum(
            entry.get("total_tokens", 0)
            for entry in agent_history
            if isinstance(entry, dict)
        )
        total_cost = sum(
            entry.get("cost", 0)
            for entry in agent_history
            if isinstance(entry, dict)
        )
        agent_count = len(
            [e for e in agent_history if isinstance(e, dict) and e.get("agent_name")]
        )

        # Compute VPR from validation results
        validation_results = {}
        for entry in agent_history:
            if isinstance(entry, dict) and "validator" in entry.get("agent_name", ""):
                validation_results[entry["agent_name"]] = entry.get("success", False)
        vpr = (
            sum(1 for v in validation_results.values() if v) / len(validation_results)
            if validation_results
            else 1.0
        )

        metrics = {
            "runId": run_id,
            "totalTokens": total_tokens,
            "totalCost": round(total_cost, 4),
            "latencySeconds": round(elapsed, 1),
            "validationPassRate": round(vpr, 2),
            "modelUsed": "gemini-2.5-pro",
            "agentCount": agent_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Update DB status
        process.status = "completed"
        db.commit()

        update_pipeline_run_status(
            run_id=run_id,
            status="success",
            final_state_summary={"acl_demo_id": game_id},
            db=db,
        )

        logger.info(
            f"[{game_id}] SUCCESS in {elapsed:.1f}s "
            f"({total_tokens} tokens, ${total_cost:.4f})"
        )

        return {
            "success": True,
            "blueprint": blueprint,
            "metrics": metrics,
            "error": None,
            "elapsed": elapsed,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{game_id}] FAILED (attempt {attempt}): {e}", exc_info=True)
        return {
            "success": False,
            "blueprint": None,
            "metrics": None,
            "error": str(e),
            "elapsed": elapsed,
        }
    finally:
        db.close()


def _sanitize_nulls(obj):
    """Replace null values with empty strings for string-typed fields
    that the frontend Zod schemas reject as null."""
    NULL_TO_EMPTY = {"image_description", "image_url", "icon", "image"}
    if isinstance(obj, dict):
        return {
            k: ("" if v is None and k in NULL_TO_EMPTY else _sanitize_nulls(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_sanitize_nulls(item) for item in obj]
    return obj


def save_game_json(query: dict, result: dict):
    """Save a single game's blueprint + metadata as a JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    game_id = query["id"]
    output_path = OUTPUT_DIR / f"{game_id}.json"

    blueprint = _sanitize_nulls(result["blueprint"])
    if isinstance(blueprint, dict):
        # Ensure generation_complete is set (V4 algorithm pipeline doesn't set it)
        blueprint.setdefault("generation_complete", True)
        # Strip is_multi_scene/game_sequence from interactive_diagram games —
        # they use mechanics[]+modeTransitions[], not game_sequence
        if query.get("gameType") == "interactive_diagram":
            blueprint.pop("is_multi_scene", None)
            blueprint.pop("game_sequence", None)

    game_entry = {
        "id": game_id,
        "title": query["title"],
        "question": query["question"],
        "domain": query["domain"],
        "educationLevel": query["educationLevel"],
        "gameType": query["gameType"],
        "mechanic": query["mechanic"],
        "bloomsLevel": query["bloomsLevel"],
        "pipelineMetrics": result["metrics"],
        "blueprint": blueprint,
    }

    with open(output_path, "w") as f:
        json.dump(game_entry, f, indent=2, default=str)

    logger.info(f"[{game_id}] Saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Generate ACL demo games")
    parser.add_argument("--start", type=int, default=0, help="Start index (0-based)")
    parser.add_argument("--end", type=int, default=None, help="End index (exclusive)")
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated game IDs")
    parser.add_argument("--dry-run", action="store_true", help="Print queries without running")
    args = parser.parse_args()

    ids = args.ids.split(",") if args.ids else None
    queries = load_queries(start=args.start, end=args.end, ids=ids)

    if args.dry_run:
        for q in queries:
            print(f"  {q['id']:45s} {q['gameType']:20s} {q['mechanic']}")
        print(f"\nTotal: {len(queries)} games")
        return

    results_summary = {
        "total": len(queries),
        "success": 0,
        "failed": 0,
        "errors": [],
        "total_tokens": 0,
        "total_cost": 0.0,
        "total_time": 0.0,
    }

    for i, query in enumerate(queries):
        game_id = query["id"]
        logger.info(f"\n{'='*60}")
        logger.info(f"Game {i+1}/{len(queries)}: {game_id}")
        logger.info(f"{'='*60}")

        result = None
        for attempt in range(1, MAX_RETRIES + 1):
            result = await run_single_game(query, attempt=attempt)
            if result["success"]:
                break
            if attempt < MAX_RETRIES:
                logger.info(f"[{game_id}] Retrying in 5 seconds...")
                await asyncio.sleep(5)

        if result and result["success"]:
            save_game_json(query, result)
            results_summary["success"] += 1
            results_summary["total_tokens"] += result["metrics"]["totalTokens"]
            results_summary["total_cost"] += result["metrics"]["totalCost"]
        else:
            results_summary["failed"] += 1
            results_summary["errors"].append(
                {"id": game_id, "error": result["error"] if result else "Unknown"}
            )

        results_summary["total_time"] += result["elapsed"] if result else 0

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("BATCH GENERATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total:    {results_summary['total']}")
    logger.info(f"Success:  {results_summary['success']}")
    logger.info(f"Failed:   {results_summary['failed']}")
    logger.info(f"Tokens:   {results_summary['total_tokens']:,}")
    logger.info(f"Cost:     ${results_summary['total_cost']:.2f}")
    logger.info(f"Time:     {results_summary['total_time']:.0f}s ({results_summary['total_time']/60:.1f}min)")

    if results_summary["errors"]:
        logger.info("\nFailed games:")
        for err in results_summary["errors"]:
            logger.info(f"  {err['id']}: {err['error'][:100]}")

    # Save summary
    summary_path = SCRIPT_DIR / "acl_demo_results.json"
    with open(summary_path, "w") as f:
        json.dump(results_summary, f, indent=2)
    logger.info(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
