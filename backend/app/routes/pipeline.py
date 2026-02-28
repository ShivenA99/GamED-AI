"""Pipeline Visualization API Routes

Exposes agent outputs and allows topology comparison for debugging and analysis.
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Optional, List
import json
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("gamed_ai.routes.pipeline")

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Directory for storing pipeline run outputs
PIPELINE_OUTPUTS_DIR = Path(__file__).parent.parent.parent / "pipeline_outputs"
PIPELINE_OUTPUTS_DIR.mkdir(exist_ok=True)


@router.get("/runs")
async def list_pipeline_runs(
    limit: int = 20,
    topology: Optional[str] = None
):
    """List all saved pipeline runs"""
    runs = []

    if not PIPELINE_OUTPUTS_DIR.exists():
        return {"runs": [], "total": 0}

    for run_file in sorted(PIPELINE_OUTPUTS_DIR.glob("*.json"), reverse=True):
        try:
            with open(run_file, "r") as f:
                data = json.load(f)
                run_info = {
                    "id": run_file.stem,
                    "question_id": data.get("question_id"),
                    "question_text": data.get("question_text", "")[:100],
                    "topology": data.get("topology"),
                    "template_type": data.get("template_type"),
                    "success": data.get("success"),
                    "duration_ms": data.get("duration_ms"),
                    "timestamp": data.get("timestamp"),
                    "agent_count": len(data.get("agent_outputs", {}))
                }

                # Filter by topology if specified
                if topology and run_info["topology"] != topology:
                    continue

                runs.append(run_info)

                if len(runs) >= limit:
                    break
        except Exception as e:
            continue

    return {"runs": runs, "total": len(runs)}


@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: str):
    """Get full details of a pipeline run including all agent outputs"""
    run_file = PIPELINE_OUTPUTS_DIR / f"{run_id}.json"

    if not run_file.exists():
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    try:
        with open(run_file, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading run data: {str(e)}")


@router.get("/runs/{run_id}/agent/{agent_name}")
async def get_agent_output(run_id: str, agent_name: str):
    """Get output from a specific agent in a pipeline run"""
    run_file = PIPELINE_OUTPUTS_DIR / f"{run_id}.json"

    if not run_file.exists():
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    try:
        with open(run_file, "r") as f:
            data = json.load(f)

        agent_outputs = data.get("agent_outputs", {})
        if agent_name not in agent_outputs:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found in this run")

        return {
            "run_id": run_id,
            "agent_name": agent_name,
            "output": agent_outputs[agent_name]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading agent data: {str(e)}")


@router.get("/compare")
async def compare_topologies(
    question_text: Optional[str] = None,
    run_ids: Optional[str] = None  # Comma-separated list of run IDs
):
    """Compare pipeline runs across topologies"""
    runs_to_compare = []

    if run_ids:
        # Load specific runs
        for run_id in run_ids.split(","):
            run_file = PIPELINE_OUTPUTS_DIR / f"{run_id.strip()}.json"
            if run_file.exists():
                with open(run_file, "r") as f:
                    runs_to_compare.append(json.load(f))
    else:
        # Find latest runs for each topology with matching question
        topology_runs = {}
        for run_file in sorted(PIPELINE_OUTPUTS_DIR.glob("*.json"), reverse=True):
            try:
                with open(run_file, "r") as f:
                    data = json.load(f)

                topo = data.get("topology")
                if topo not in topology_runs:
                    if not question_text or question_text.lower() in data.get("question_text", "").lower():
                        topology_runs[topo] = data
            except (json.JSONDecodeError, IOError, KeyError) as e:
                logger.debug(f"Skipping invalid run file {run_file}: {e}")
                continue

        runs_to_compare = list(topology_runs.values())

    if not runs_to_compare:
        return {"comparison": [], "message": "No matching runs found"}

    # Build comparison structure
    comparison = {
        "runs": [],
        "agents": [],
        "summary": {}
    }

    # Get all unique agents across all runs
    all_agents = set()
    for run in runs_to_compare:
        all_agents.update(run.get("agent_outputs", {}).keys())
    comparison["agents"] = sorted(all_agents)

    # Add each run's data
    for run in runs_to_compare:
        run_summary = {
            "id": run.get("run_id"),
            "topology": run.get("topology"),
            "success": run.get("success"),
            "duration_ms": run.get("duration_ms"),
            "template_type": run.get("template_type"),
            "blueprint": run.get("blueprint"),
            "agent_outputs": {}
        }

        # Include agent outputs with timing
        for agent in comparison["agents"]:
            agent_data = run.get("agent_outputs", {}).get(agent, {})
            run_summary["agent_outputs"][agent] = {
                "executed": agent in run.get("agent_outputs", {}),
                "duration_ms": agent_data.get("duration_ms", 0),
                "output_preview": _get_output_preview(agent_data.get("output", {})),
                "full_output": agent_data.get("output", {})
            }

        comparison["runs"].append(run_summary)

    return comparison


def _get_output_preview(output: dict) -> str:
    """Get a short preview of agent output"""
    if not output:
        return "(empty)"

    # For different agent types, show relevant preview
    if "template_type" in output:
        return f"Template: {output['template_type']}, Confidence: {output.get('confidence', 'N/A')}"
    elif "blooms_level" in output:
        return f"Bloom's: {output['blooms_level']}, Subject: {output.get('subject_area', 'N/A')}"
    elif "game_mechanics" in output:
        return f"Mechanics: {len(output.get('game_mechanics', []))}, Duration: {output.get('estimated_duration_min', 'N/A')}min"
    elif "visual_theme" in output:
        return f"Theme: {output['visual_theme']}, Assets: {len(output.get('required_assets', []))}"
    elif "templateType" in output:
        return f"Blueprint: {output['templateType']}, Tasks: {len(output.get('tasks', output.get('steps', [])))}"

    # Default: show first few keys
    keys = list(output.keys())[:3]
    return f"Keys: {', '.join(keys)}"


def save_pipeline_run(
    run_id: str,
    question_id: str,
    question_text: str,
    topology: str,
    agent_outputs: dict,
    final_state: dict,
    success: bool,
    duration_ms: int,
    error_message: Optional[str] = None
):
    """Save a pipeline run for later visualization"""

    run_data = {
        "run_id": run_id,
        "question_id": question_id,
        "question_text": question_text,
        "topology": topology,
        "success": success,
        "duration_ms": duration_ms,
        "error_message": error_message,
        "timestamp": datetime.utcnow().isoformat(),
        "template_type": (final_state.get("blueprint") or {}).get("templateType"),
        "blueprint": final_state.get("blueprint"),
        "agent_outputs": agent_outputs
    }

    PIPELINE_OUTPUTS_DIR.mkdir(exist_ok=True)
    output_file = PIPELINE_OUTPUTS_DIR / f"{run_id}.json"

    with open(output_file, "w") as f:
        json.dump(run_data, f, indent=2, default=str)

    return str(output_file)
