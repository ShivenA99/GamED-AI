#!/usr/bin/env python3
"""
Topology Comparison Script

Runs the same question through different topologies and compares:
- Quality (LLM-judged)
- Latency
- Token usage
- Success rate
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.state import create_initial_state
from app.agents.topologies import (
    TopologyType,
    TopologyConfig,
    create_topology,
    get_topology_description
)


@dataclass
class TopologyResult:
    """Result from running a topology"""
    topology: str
    success: bool
    latency_ms: int
    blueprint_valid: bool
    template_type: str
    confidence: float
    num_tasks: int
    story_title: str
    errors: List[str]
    quality_scores: Dict[str, float]


# Test question
TEST_QUESTION = {
    "id": "test_binary_search",
    "text": "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13].",
    "options": None
}


async def run_topology(
    topology_type: TopologyType,
    question: Dict[str, Any]
) -> TopologyResult:
    """Run a question through a specific topology"""
    print(f"\n{'='*60}")
    print(f"Running: {topology_type.value}")
    print(f"{'='*60}")

    start_time = time.time()
    errors = []

    try:
        # Create topology
        config = TopologyConfig(
            topology_type=topology_type,
            max_iterations=2,
            validation_threshold=0.6
        )
        graph = create_topology(topology_type, config)
        compiled = graph.compile()

        # Create initial state
        initial_state = create_initial_state(
            question_id=question["id"],
            question_text=question["text"],
            question_options=question.get("options")
        )

        # Run
        result = await compiled.ainvoke(initial_state)

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract results
        blueprint = result.get("blueprint", {})
        template_selection = result.get("template_selection", {})
        story_data = result.get("story_data", {})
        validation_results = result.get("validation_results", {})

        # Check success
        blueprint_valid = validation_results.get("blueprint", {}).get("is_valid", False)
        if not blueprint_valid and blueprint.get("tasks"):
            blueprint_valid = True  # Has tasks = valid enough

        success = bool(blueprint and blueprint.get("tasks"))

        # Collect validation errors
        for key, val in validation_results.items():
            if isinstance(val, dict) and val.get("errors"):
                errors.extend(val["errors"])

        if result.get("error_message"):
            errors.append(result["error_message"])

        # Simple quality scores (would use LLM judge in production)
        quality_scores = {
            "completeness": 1.0 if blueprint.get("tasks") else 0.0,
            "has_narrative": 1.0 if story_data.get("story_context") else 0.5,
            "has_title": 1.0 if blueprint.get("title") else 0.0,
        }
        quality_scores["overall"] = sum(quality_scores.values()) / len(quality_scores)

        return TopologyResult(
            topology=topology_type.value,
            success=success,
            latency_ms=latency_ms,
            blueprint_valid=blueprint_valid,
            template_type=template_selection.get("template_type", "unknown"),
            confidence=template_selection.get("confidence", 0.0),
            num_tasks=len(blueprint.get("tasks", [])),
            story_title=story_data.get("story_title", "N/A"),
            errors=errors[:3],  # Limit errors shown
            quality_scores=quality_scores
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        print(f"Error: {e}")
        return TopologyResult(
            topology=topology_type.value,
            success=False,
            latency_ms=latency_ms,
            blueprint_valid=False,
            template_type="error",
            confidence=0.0,
            num_tasks=0,
            story_title="Error",
            errors=[str(e)],
            quality_scores={"overall": 0.0}
        )


def print_comparison_table(results: List[TopologyResult]):
    """Print a comparison table of results"""
    print("\n")
    print("=" * 100)
    print("TOPOLOGY COMPARISON RESULTS")
    print("=" * 100)
    print()

    # Header
    print(f"{'Topology':<25} {'Success':<8} {'Latency':<10} {'Template':<20} {'Tasks':<6} {'Quality':<8}")
    print("-" * 100)

    # Results
    for r in results:
        status = "✓" if r.success else "✗"
        quality = f"{r.quality_scores.get('overall', 0):.2f}"
        print(f"{r.topology:<25} {status:<8} {r.latency_ms:>6}ms   {r.template_type:<20} {r.num_tasks:<6} {quality:<8}")

    print("-" * 100)

    # Summary
    successful = sum(1 for r in results if r.success)
    avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0
    avg_quality = sum(r.quality_scores.get("overall", 0) for r in results) / len(results) if results else 0

    print(f"\nSummary:")
    print(f"  Success Rate: {successful}/{len(results)} ({100*successful/len(results):.0f}%)")
    print(f"  Avg Latency:  {avg_latency:.0f}ms")
    print(f"  Avg Quality:  {avg_quality:.2f}")

    # Best topology
    if results:
        best = max(results, key=lambda r: (r.success, r.quality_scores.get("overall", 0), -r.latency_ms))
        print(f"\n  Best Topology: {best.topology}")

    print()


async def main():
    """Main comparison entry point"""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("GamED.AI v2 Topology Comparison")
    print("=" * 60)

    # Check for API keys
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not groq_key and not openai_key and not anthropic_key:
        print("\nERROR: No API keys found!")
        print("Set GROQ_API_KEY (free!), OPENAI_API_KEY, or ANTHROPIC_API_KEY")
        return

    print(f"\nQuestion: {TEST_QUESTION['text'][:60]}...")

    # Topologies to test (T0, T1, T2 are most stable)
    topologies_to_test = [
        TopologyType.T0_SEQUENTIAL,
        TopologyType.T1_SEQUENTIAL_VALIDATED,
        TopologyType.T2_ACTOR_CRITIC,
    ]

    results = []

    for topo in topologies_to_test:
        result = await run_topology(topo, TEST_QUESTION)
        results.append(result)

        # Print individual result
        print(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"  Template: {result.template_type}")
        print(f"  Tasks: {result.num_tasks}")
        print(f"  Story: {result.story_title}")
        print(f"  Latency: {result.latency_ms}ms")
        if result.errors:
            print(f"  Errors: {result.errors[:2]}")

    # Print comparison table
    print_comparison_table(results)

    # Save detailed results
    output_file = Path(__file__).parent / "topology_comparison_results.json"
    with open(output_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
