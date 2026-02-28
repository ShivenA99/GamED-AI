#!/usr/bin/env python3
"""
Run a single topology test and save the full blueprint to a JSON file.
"""

import warnings
warnings.filterwarnings("ignore", message=".*Pydantic V1.*", category=UserWarning)

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.state import create_initial_state
from app.agents.topologies import (
    TopologyType,
    TopologyConfig,
    create_topology,
)


async def run_and_save(topology_name: str, question_text: str, output_dir: str):
    """Run topology and save the full result"""

    topology_map = {
        "T0": TopologyType.T0_SEQUENTIAL,
        "T1": TopologyType.T1_SEQUENTIAL_VALIDATED,
    }

    topology_type = topology_map.get(topology_name.upper())
    if not topology_type:
        print(f"Unknown topology: {topology_name}")
        return None

    print(f"\n{'='*60}")
    print(f"Running {topology_name} for STATE_TRACER_CODE")
    print(f"{'='*60}")

    # Create topology
    config = TopologyConfig(
        topology_type=topology_type,
        max_iterations=3,
        validation_threshold=0.7
    )
    graph = create_topology(topology_type, config)
    compiled = graph.compile()

    # Create initial state
    initial_state = create_initial_state(
        question_id=f"{topology_name.lower()}_binary_search",
        question_text=question_text,
        question_options=None
    )

    # Run
    print("Executing pipeline...")
    result = await compiled.ainvoke(initial_state)

    if result and result.get("blueprint"):
        # Save full result
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{topology_name}_state_tracer_{timestamp}.json"
        filepath = output_path / filename

        output_data = {
            "topology": topology_name,
            "question": question_text,
            "timestamp": datetime.now().isoformat(),
            "blueprint": result.get("blueprint"),
            "scene_data": result.get("scene_data"),
            "game_plan": result.get("game_plan"),
            "template_selection": result.get("template_selection"),
        }

        with open(filepath, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"\n✓ Blueprint saved to: {filepath}")
        print(f"  Title: {result['blueprint'].get('title')}")
        print(f"  Tasks: {len(result['blueprint'].get('tasks', []))}")
        print(f"  Steps: {len(result['blueprint'].get('steps', []))}")

        return filepath
    else:
        print("✗ Failed to generate blueprint")
        return None


async def main():
    question = "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13]."
    output_dir = Path(__file__).parent.parent / "pipeline_outputs"

    # Run both topologies
    results = {}
    for topo in ["T0", "T1"]:
        filepath = await run_and_save(topo, question, str(output_dir))
        if filepath:
            results[topo] = str(filepath)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for topo, path in results.items():
        print(f"  {topo}: {path}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
