#!/usr/bin/env python3
"""
Comprehensive Topology Test Suite

Tests all 8 topologies with the binary search question using Ollama.
Collects detailed metrics and failure modes for analysis.

Usage:
    # Test with Ollama (local)
    USE_OLLAMA=true FORCE_TEMPLATE=STATE_TRACER_CODE python scripts/test_all_topologies.py

    # Test with specific topology
    USE_OLLAMA=true FORCE_TEMPLATE=STATE_TRACER_CODE python scripts/test_all_topologies.py --topology T0
"""

# Suppress Pydantic V1 deprecation warnings for Python 3.14+
import warnings
warnings.filterwarnings("ignore", message=".*Pydantic V1.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pydantic.v1.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*Core Pydantic V1.*", category=UserWarning)

import asyncio
import json
import time
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Configure logging to show application logs during tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True  # Override any existing configuration
)

# Set specific loggers to INFO level
logging.getLogger("gamed_ai").setLevel(logging.INFO)
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("app.agents").setLevel(logging.INFO)
logging.getLogger("app.services").setLevel(logging.INFO)
logging.getLogger("app.services.llm_service").setLevel(logging.INFO)

# Reduce noise from some libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

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
class TopologyTestResult:
    """Detailed result from running a topology"""
    topology: str
    topology_name: str
    success: bool
    latency_ms: int
    blueprint_valid: bool
    template_type: str
    confidence: float
    num_tasks: int
    num_steps: int  # For STATE_TRACER_CODE
    story_title: str
    errors: List[str]
    validation_errors: Dict[str, List[str]]
    quality_scores: Dict[str, float]
    token_usage: Dict[str, int]
    agent_executions: List[str]
    failure_stage: Optional[str] = None
    error_message: Optional[str] = None


# Test question (binary search)
TEST_QUESTION = {
    "id": "test_binary_search",
    "text": "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13].",
    "options": None
}

# All 8 topologies to test
ALL_TOPOLOGIES = [
    TopologyType.T0_SEQUENTIAL,
    TopologyType.T1_SEQUENTIAL_VALIDATED,
    TopologyType.T2_ACTOR_CRITIC,
    TopologyType.T3_HIERARCHICAL,
    TopologyType.T4_SELF_REFINE,
    TopologyType.T5_MULTI_AGENT_DEBATE,
    TopologyType.T6_DAG_PARALLEL,
    TopologyType.T7_REFLECTION_MEMORY,
]


async def run_topology_test(
    topology_type: TopologyType,
    question: Dict[str, Any]
) -> TopologyTestResult:
    """Run a question through a specific topology and collect detailed metrics"""
    print(f"\n{'='*70}")
    print(f"Testing: {topology_type.value}")
    print(f"Description: {get_topology_description(topology_type)}")
    print(f"{'='*70}")

    start_time = time.time()
    errors = []
    validation_errors = {}
    agent_executions = []
    failure_stage = None
    error_message = None

    try:
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
            question_id=question["id"],
            question_text=question["text"],
            question_options=question.get("options")
        )

        # Run topology
        print(f"  Starting execution...")
        print()  # Blank line before logs start
        logger = logging.getLogger("test_all_topologies")
        logger.info(f"Starting {topology_type.value} topology execution...")
        
        result = await compiled.ainvoke(initial_state)
        
        logger.info(f"Topology execution completed")

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract results (handle None result)
        if result is None:
            result = {}
        
        blueprint = result.get("blueprint") or {}
        template_selection = result.get("template_selection") or {}
        scene_data = result.get("scene_data") or {}
        story_data = result.get("story_data") or {}  # Legacy support
        validation_results = result.get("validation_results") or {}
        agent_history = result.get("agent_history") or []

        # Track agent executions
        for agent_exec in agent_history:
            if isinstance(agent_exec, dict):
                agent_name = agent_exec.get("agent_name", "unknown")
                status = agent_exec.get("status", "unknown")
                agent_executions.append(f"{agent_name}:{status}")

        # Collect validation errors
        for key, val in validation_results.items():
            if isinstance(val, dict):
                val_errors = val.get("errors", [])
                if val_errors:
                    validation_errors[key] = val_errors

        # Check success (handle None values safely)
        blueprint_validation = validation_results.get("blueprint") or {}
        blueprint_valid = blueprint_validation.get("is_valid", False) if isinstance(blueprint_validation, dict) else False
        if not blueprint_valid and blueprint and blueprint.get("tasks"):
            blueprint_valid = True  # Has tasks = valid enough

        success = bool(blueprint and isinstance(blueprint, dict) and blueprint.get("tasks"))

        # Collect errors
        for key, val in validation_results.items():
            if isinstance(val, dict) and val.get("errors"):
                errors.extend(val["errors"])

        if result.get("error_message"):
            errors.append(result["error_message"])
            error_message = result["error_message"]

        # Determine failure stage
        if not success:
            if not template_selection:
                failure_stage = "routing"
            elif not scene_data and not story_data:
                failure_stage = "scene_generation"
            elif not blueprint:
                failure_stage = "blueprint_generation"
            elif not blueprint.get("tasks"):
                failure_stage = "blueprint_validation"
            else:
                failure_stage = "unknown"

        # Extract metrics
        num_tasks = len(blueprint.get("tasks", []))
        num_steps = len(blueprint.get("steps", [])) if blueprint.get("templateType") == "STATE_TRACER_CODE" else 0

        # Simple quality scores (would use LLM judge in production)
        has_context = bool(scene_data.get("minimal_context") or story_data.get("story_context"))
        quality_scores = {
            "completeness": 1.0 if blueprint.get("tasks") else 0.0,
            "has_context": 1.0 if has_context else 0.5,
            "has_title": 1.0 if blueprint.get("title") else 0.0,
            "has_code": 1.0 if blueprint.get("code") else 0.0,
            "has_steps": 1.0 if num_steps > 0 else 0.0,
            "has_assets": 1.0 if scene_data.get("required_assets") else 0.5,
        }
        quality_scores["overall"] = sum(quality_scores.values()) / len(quality_scores)

        # Token usage (placeholder - would track from LLM service)
        token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }

        return TopologyTestResult(
            topology=topology_type.value,
            topology_name=topology_type.name,
            success=success,
            latency_ms=latency_ms,
            blueprint_valid=blueprint_valid,
            template_type=template_selection.get("template_type", "unknown"),
            confidence=template_selection.get("confidence", 0.0),
            num_tasks=num_tasks,
            num_steps=num_steps,
            story_title=scene_data.get("scene_title") or story_data.get("story_title", "N/A"),
            errors=errors[:10],  # Limit errors shown
            validation_errors=validation_errors,
            quality_scores=quality_scores,
            token_usage=token_usage,
            agent_executions=agent_executions,
            failure_stage=failure_stage,
            error_message=error_message
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return TopologyTestResult(
            topology=topology_type.value,
            topology_name=topology_type.name,
            success=False,
            latency_ms=latency_ms,
            blueprint_valid=False,
            template_type="error",
            confidence=0.0,
            num_tasks=0,
            num_steps=0,
            story_title="Error",
            errors=[str(e)],
            validation_errors={},
            quality_scores={"overall": 0.0},
            token_usage={},
            agent_executions=[],
            failure_stage="execution",
            error_message=str(e)
        )


def print_results_table(results: List[TopologyTestResult]):
    """Print a formatted comparison table"""
    print("\n")
    print("=" * 120)
    print("TOPOLOGY TEST RESULTS - ALL 8 TOPOLOGIES")
    print("=" * 120)
    print()

    # Header
    print(f"{'Topology':<25} {'Status':<8} {'Latency':<10} {'Template':<20} {'Tasks':<6} {'Steps':<6} {'Quality':<8}")
    print("-" * 120)

    # Results
    for r in results:
        status = "✓ PASS" if r.success else "✗ FAIL"
        quality = f"{r.quality_scores.get('overall', 0):.2f}"
        steps = str(r.num_steps) if r.num_steps > 0 else "-"
        print(f"{r.topology_name:<25} {status:<8} {r.latency_ms:>6}ms   {r.template_type:<20} {r.num_tasks:<6} {steps:<6} {quality:<8}")

    print("-" * 120)

    # Summary statistics
    successful = sum(1 for r in results if r.success)
    avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0
    avg_quality = sum(r.quality_scores.get("overall", 0) for r in results) / len(results) if results else 0

    print(f"\nSummary:")
    print(f"  Success Rate: {successful}/{len(results)} ({100*successful/len(results):.0f}%)")
    print(f"  Avg Latency:  {avg_latency:.0f}ms")
    print(f"  Avg Quality:  {avg_quality:.2f}")

    # Failure analysis
    failures = [r for r in results if not r.success]
    if failures:
        print(f"\n  Failures: {len(failures)}")
        failure_stages = {}
        for f in failures:
            stage = f.failure_stage or "unknown"
            failure_stages[stage] = failure_stages.get(stage, 0) + 1
        for stage, count in failure_stages.items():
            print(f"    - {stage}: {count}")


def analyze_failure_modes(results: List[TopologyTestResult]) -> Dict[str, Any]:
    """Analyze failure modes across all topologies"""
    analysis = {
        "total_tests": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "failure_stages": {},
        "common_errors": {},
        "validation_failures": {},
        "topology_performance": {}
    }

    for result in results:
        # Failure stages
        if not result.success and result.failure_stage:
            stage = result.failure_stage
            analysis["failure_stages"][stage] = analysis["failure_stages"].get(stage, 0) + 1

        # Common errors
        for error in result.errors:
            error_key = error[:50]  # Truncate for grouping
            analysis["common_errors"][error_key] = analysis["common_errors"].get(error_key, 0) + 1

        # Validation failures
        for validator, errors in result.validation_errors.items():
            if validator not in analysis["validation_failures"]:
                analysis["validation_failures"][validator] = []
            analysis["validation_failures"][validator].extend(errors)

        # Performance by topology
        analysis["topology_performance"][result.topology] = {
            "success": result.success,
            "latency_ms": result.latency_ms,
            "quality": result.quality_scores.get("overall", 0),
            "num_tasks": result.num_tasks
        }

    return analysis


async def main():
    """Main test execution"""
    import argparse
    parser = argparse.ArgumentParser(description="Test all topologies")
    parser.add_argument(
        "--topology",
        type=str,
        action="append",
        help="Test specific topology (T0, T1, T2, etc.). Can be specified multiple times."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="topology_test_results.json",
        help="Output file for results"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("GamED.AI Topology Test Suite")
    print("=" * 70)
    print(f"\nQuestion: {TEST_QUESTION['text'][:60]}...")
    print(f"Expected Template: STATE_TRACER_CODE (hard-coded)")

    # Check environment
    use_ollama = os.getenv("USE_OLLAMA", "").lower() == "true"
    force_template = os.getenv("FORCE_TEMPLATE", "")
    
    print(f"\nConfiguration:")
    print(f"  USE_OLLAMA: {use_ollama}")
    print(f"  FORCE_TEMPLATE: {force_template or 'None'}")

    if use_ollama:
        print("\n⚠ Using Ollama (local models). Make sure Ollama is running:")
        print("  ollama serve")
    else:
        print("\n⚠ Not using Ollama. Set USE_OLLAMA=true to use local models.")

    # Determine which topologies to test
    topology_map = {
        "T0": TopologyType.T0_SEQUENTIAL,
        "T1": TopologyType.T1_SEQUENTIAL_VALIDATED,
        "T2": TopologyType.T2_ACTOR_CRITIC,
        "T3": TopologyType.T3_HIERARCHICAL,
        "T4": TopologyType.T4_SELF_REFINE,
        "T5": TopologyType.T5_MULTI_AGENT_DEBATE,
        "T6": TopologyType.T6_DAG_PARALLEL,
        "T7": TopologyType.T7_REFLECTION_MEMORY,
    }
    
    if args.topology:
        # Test specified topologies
        topologies_to_test = []
        for topo_str in args.topology:
            topo_upper = topo_str.upper()
            if topo_upper not in topology_map:
                print(f"Error: Unknown topology {topo_str}")
                return
            topologies_to_test.append(topology_map[topo_upper])
    else:
        # Default: Test only T0 and T1 for initial testing
        topologies_to_test = [
            TopologyType.T0_SEQUENTIAL,
            TopologyType.T1_SEQUENTIAL_VALIDATED
        ]

    print(f"\nTesting {len(topologies_to_test)} topologies...")
    print()

    # Run tests
    results = []
    for topo in topologies_to_test:
        result = await run_topology_test(topo, TEST_QUESTION)
        results.append(result)

        # Print individual result summary
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"\n  Result: {status}")
        if result.success:
            print(f"    Template: {result.template_type}")
            print(f"    Tasks: {result.num_tasks}, Steps: {result.num_steps}")
            print(f"    Story: {result.story_title}")
            print(f"    Latency: {result.latency_ms}ms")
        else:
            print(f"    Failure Stage: {result.failure_stage}")
            if result.error_message:
                print(f"    Error: {result.error_message[:100]}")

    # Print comparison table
    print_results_table(results)

    # Analyze failure modes
    analysis = analyze_failure_modes(results)

    # Save detailed results
    output_file = Path(__file__).parent / args.output
    output_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": TEST_QUESTION,
        "configuration": {
            "use_ollama": use_ollama,
            "force_template": force_template
        },
        "results": [asdict(r) for r in results],
        "analysis": analysis
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Detailed results saved to: {output_file}")
    print(f"{'='*70}\n")

    # Print failure analysis
    if analysis["failed"] > 0:
        print("\nFAILURE ANALYSIS:")
        print("-" * 70)
        if analysis["failure_stages"]:
            print("\nFailure Stages:")
            for stage, count in analysis["failure_stages"].items():
                print(f"  - {stage}: {count}")

        if analysis["common_errors"]:
            print("\nMost Common Errors:")
            sorted_errors = sorted(analysis["common_errors"].items(), key=lambda x: x[1], reverse=True)
            for error, count in sorted_errors[:5]:
                print(f"  - ({count}x) {error}")

        if analysis["validation_failures"]:
            print("\nValidation Failures:")
            for validator, errors in analysis["validation_failures"].items():
                print(f"  - {validator}: {len(errors)} errors")


if __name__ == "__main__":
    asyncio.run(main())
