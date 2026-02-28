#!/usr/bin/env python3
"""
Test Script for Local Ollama Pipeline

Tests the GamED.AI pipeline with local Ollama models, specifically
focusing on JSON parsing reliability with the new repair system.

Usage:
    # Set USE_OLLAMA first
    export USE_OLLAMA=true

    # Run tests
    python scripts/test_local_pipeline.py

    # Run with specific topology
    python scripts/test_local_pipeline.py --topology T0

    # Verbose logging
    python scripts/test_local_pipeline.py --verbose

    # Test JSON repair only
    python scripts/test_local_pipeline.py --repair-only
"""

import asyncio
import json
import time
import sys
import os
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

# Suppress warnings
import warnings
warnings.filterwarnings("ignore", message=".*Pydantic.*", category=UserWarning)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    success: bool
    duration_ms: int
    json_repair_needed: bool
    json_repair_successful: bool
    retry_count: int
    template_type: str
    error_message: Optional[str] = None
    error_context: Optional[str] = None


def setup_logging(verbose: bool = False):
    """Configure logging for test output"""
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    root.handlers = []

    # Add console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Set specific loggers
    logging.getLogger("gamed_ai").setLevel(level)
    logging.getLogger("app").setLevel(level)

    # Reduce noise from HTTP libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def check_ollama_available() -> bool:
    """Check if Ollama is running"""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/version", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def check_models_available() -> Dict[str, bool]:
    """Check which Ollama models are available"""
    models = {
        "qwen2.5:7b": False,
        "llama3.2:latest": False,
        "deepseek-coder:6.7b": False
    }

    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            available = [m["name"] for m in data.get("models", [])]
            for model in list(models.keys()):
                # Check for exact match or base name match
                base_name = model.split(":")[0]
                models[model] = any(
                    m == model or m.startswith(base_name + ":")
                    for m in available
                )
    except Exception as e:
        print(f"Warning: Could not check Ollama models: {e}")

    return models


async def test_json_repair() -> List[TestResult]:
    """Test the JSON repair module directly"""
    from app.services.json_repair import repair_json, JSONRepairError

    test_cases = [
        # (input_json, expected_result, test_name)
        ('{"a": 1 "b": 2}', {"a": 1, "b": 2}, "missing_comma"),
        ('{"a": 1, "b": 2,}', {"a": 1, "b": 2}, "trailing_comma"),
        ("{'a': 1, 'b': 2}", {"a": 1, "b": 2}, "single_quotes"),
        ('{a: 1, b: 2}', {"a": 1, "b": 2}, "unquoted_keys"),
        ('{"a": 1, "b": 2', {"a": 1, "b": 2}, "missing_brace"),
        ('```json\n{"a": 1}\n```', {"a": 1}, "markdown_block"),
        ('Here is JSON: {"a": 1}', {"a": 1}, "text_prefix"),
    ]

    results = []
    for input_json, expected, test_name in test_cases:
        start = time.time()
        try:
            result, was_repaired, log = repair_json(input_json)
            duration = int((time.time() - start) * 1000)
            success = result == expected
            results.append(TestResult(
                test_name=f"repair_{test_name}",
                success=success,
                duration_ms=duration,
                json_repair_needed=was_repaired,
                json_repair_successful=success,
                retry_count=0,
                template_type="N/A",
                error_message=None if success else f"Expected {expected}, got {result}"
            ))
        except (JSONRepairError, json.JSONDecodeError) as e:
            duration = int((time.time() - start) * 1000)
            results.append(TestResult(
                test_name=f"repair_{test_name}",
                success=False,
                duration_ms=duration,
                json_repair_needed=True,
                json_repair_successful=False,
                retry_count=0,
                template_type="N/A",
                error_message=str(e)
            ))

    return results


async def test_pipeline_topology(
    topology: str,
    question: Dict[str, Any],
    logger: logging.Logger,
    save_outputs: bool = True
) -> TestResult:
    """Run a full pipeline test with the specified topology"""
    from app.agents.state import create_initial_state
    from app.agents.topologies import TopologyType, TopologyConfig, create_topology

    topology_map = {
        "T0": TopologyType.T0_SEQUENTIAL,
        "T1": TopologyType.T1_SEQUENTIAL_VALIDATED,
    }

    topo_type = topology_map.get(topology, TopologyType.T0_SEQUENTIAL)

    start_time = time.time()
    test_name = f"{topology}_{question['id']}"
    run_id = f"{topology}_{question['id']}_{int(time.time())}"

    logger.info(f"Starting test: {test_name}")

    # Track agent outputs during execution
    agent_outputs = {}
    agent_start_times = {}

    try:
        config = TopologyConfig(
            topology_type=topo_type,
            max_iterations=3,
            validation_threshold=0.7
        )

        graph = create_topology(topo_type, config)
        compiled = graph.compile()

        initial_state = create_initial_state(
            question_id=question["id"],
            question_text=question["text"],
            question_options=question.get("options")
        )

        logger.info(f"Invoking graph for {test_name}...")

        # Use stream to capture per-agent outputs
        previous_state = initial_state.copy()
        async for event in compiled.astream(initial_state):
            # event is a dict with agent_name -> output
            for agent_name, output in event.items():
                if agent_name.startswith("_"):
                    continue

                agent_end_time = time.time()
                agent_duration = int((agent_end_time - agent_start_times.get(agent_name, start_time)) * 1000)

                # Extract the relevant output data for this agent
                agent_output_data = extract_agent_output(agent_name, output, previous_state)

                agent_outputs[agent_name] = {
                    "duration_ms": agent_duration,
                    "output": agent_output_data,
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Update previous_state
                previous_state.update(output)
                agent_start_times[agent_name] = agent_end_time

                logger.info(f"Agent '{agent_name}' completed in {agent_duration}ms")

        # Get final result
        result = previous_state
        duration_ms = int((time.time() - start_time) * 1000)

        # Analyze result
        blueprint = result.get("blueprint", {})
        template_type = result.get("template_selection", {}).get("template_type", "unknown")
        error_msg = result.get("error_message")

        # Check for success - also check for steps (used in STATE_TRACER_CODE)
        success = bool(blueprint and (blueprint.get("tasks") or blueprint.get("items") or blueprint.get("steps")))

        if success:
            logger.info(f"SUCCESS: {test_name} - template={template_type}, duration={duration_ms}ms")
        else:
            logger.error(f"FAILED: {test_name} - {error_msg}")

        # Save full pipeline run for UI visualization
        if save_outputs:
            save_pipeline_run_to_file(
                run_id=run_id,
                question_id=question["id"],
                question_text=question["text"],
                topology=topology,
                agent_outputs=agent_outputs,
                final_state=result,
                success=success,
                duration_ms=duration_ms,
                error_message=error_msg
            )
            logger.info(f"Saved pipeline outputs: {run_id}")

        return TestResult(
            test_name=test_name,
            success=success,
            duration_ms=duration_ms,
            json_repair_needed=False,  # Would need to track this in LLM service
            json_repair_successful=False,
            retry_count=0,
            template_type=template_type,
            error_message=error_msg
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"EXCEPTION in {test_name}: {e}", exc_info=True)

        # Still save outputs on failure
        if save_outputs and agent_outputs:
            save_pipeline_run_to_file(
                run_id=run_id,
                question_id=question["id"],
                question_text=question["text"],
                topology=topology,
                agent_outputs=agent_outputs,
                final_state={},
                success=False,
                duration_ms=duration_ms,
                error_message=str(e)
            )

        return TestResult(
            test_name=test_name,
            success=False,
            duration_ms=duration_ms,
            json_repair_needed=False,
            json_repair_successful=False,
            retry_count=0,
            template_type="error",
            error_message=str(e)
        )


def extract_agent_output(agent_name: str, output: dict, previous_state: dict) -> dict:
    """Extract the relevant output data from an agent's result"""
    # Map agent names to their primary output keys
    agent_output_keys = {
        "input_enhancer": ["pedagogical_context"],
        "router": ["template_selection"],
        "game_planner": ["game_plan"],
        "scene_generator": ["scene_data"],
        "blueprint_generator": ["blueprint"],
        "blueprint_validator": ["validation_results"],
        "code_generator": ["generated_code"],
        "code_verifier": ["validation_results"],
        "asset_generator": ["asset_urls", "generation_complete"],
        "human_review": ["pending_human_review"],
    }

    keys_to_extract = agent_output_keys.get(agent_name, [])

    result = {}
    for key in keys_to_extract:
        if key in output:
            result[key] = output[key]

    # If no specific keys found, return the diff from previous state
    if not result:
        for key, value in output.items():
            if key not in previous_state or previous_state.get(key) != value:
                # Skip internal state keys
                if not key.startswith("_") and key not in ["current_agent", "last_updated_at"]:
                    result[key] = value

    return result


def save_pipeline_run_to_file(
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
    """Save pipeline run data for UI visualization"""
    output_dir = Path(__file__).parent.parent / "pipeline_outputs"
    output_dir.mkdir(exist_ok=True)

    run_data = {
        "run_id": run_id,
        "question_id": question_id,
        "question_text": question_text,
        "topology": topology,
        "success": success,
        "duration_ms": duration_ms,
        "error_message": error_message,
        "timestamp": datetime.utcnow().isoformat(),
        "template_type": final_state.get("blueprint", {}).get("templateType") if final_state else None,
        "blueprint": final_state.get("blueprint") if final_state else None,
        "agent_outputs": agent_outputs
    }

    output_file = output_dir / f"{run_id}.json"
    with open(output_file, "w") as f:
        json.dump(run_data, f, indent=2, default=str)

    return str(output_file)


def print_results(results: List[TestResult]):
    """Print formatted test results"""
    print("\n" + "=" * 80)
    print("LOCAL OLLAMA PIPELINE TEST RESULTS")
    print("=" * 80 + "\n")

    print(f"{'Test Name':<35} {'Status':<10} {'Duration':<12} {'Template':<20}")
    print("-" * 77)

    for r in results:
        status = "\033[92mPASS\033[0m" if r.success else "\033[91mFAIL\033[0m"
        duration = f"{r.duration_ms}ms"
        template = r.template_type[:18] if r.template_type else "N/A"
        print(f"{r.test_name:<35} {status:<18} {duration:<12} {template:<20}")
        if r.error_message and not r.success:
            # Truncate long error messages
            error = r.error_message[:70] + "..." if len(r.error_message) > 70 else r.error_message
            print(f"  \033[93mERROR: {error}\033[0m")

    print("-" * 77)

    passed = sum(1 for r in results if r.success)
    total = len(results)
    pct = 100 * passed / total if total > 0 else 0

    color = "\033[92m" if pct >= 80 else "\033[93m" if pct >= 50 else "\033[91m"
    print(f"\nSummary: {color}{passed}/{total} tests passed ({pct:.0f}%)\033[0m")


async def main():
    parser = argparse.ArgumentParser(description="Test local Ollama pipeline")
    parser.add_argument("--topology", "-t", type=str, default="T0",
                       help="Topology to test (T0, T1)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose logging")
    parser.add_argument("--repair-only", action="store_true",
                       help="Only test JSON repair module")
    parser.add_argument("--question", "-q", type=str, default="binary_search",
                       help="Question type (binary_search, state_tracer)")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("test_local_pipeline")

    print("=" * 80)
    print("GamED.AI Local Ollama Pipeline Test")
    print("=" * 80)

    # Check Ollama
    if not check_ollama_available():
        print("\n\033[91mERROR: Ollama is not running!\033[0m")
        print("Start it with: ollama serve")
        return 1

    print("\033[92mOllama is running\033[0m")

    # Check models
    models = check_models_available()
    print("\nAvailable Models:")
    for model, available in models.items():
        status = "\033[92mOK\033[0m" if available else "\033[91mMISSING\033[0m"
        print(f"  {model}: {status}")

    if not any(models.values()):
        print("\n\033[91mERROR: No required models available!\033[0m")
        print("Install with:")
        print("  ollama pull qwen2.5:7b")
        print("  ollama pull llama3.2:latest")
        print("  ollama pull deepseek-coder:6.7b")
        return 1

    # Ensure USE_OLLAMA is set
    os.environ["USE_OLLAMA"] = "true"
    print(f"\nUSE_OLLAMA={os.environ.get('USE_OLLAMA')}")

    results = []

    # Test JSON repair
    print("\n--- JSON Repair Tests ---")
    repair_results = await test_json_repair()
    results.extend(repair_results)

    passed = sum(1 for r in repair_results if r.success)
    print(f"JSON Repair: {passed}/{len(repair_results)} tests passed")

    if not args.repair_only:
        # Test pipeline
        print(f"\n--- Pipeline Test ({args.topology}) ---")

        # Define test questions
        test_questions = {
            "binary_search": {
                "id": "binary_search_test",
                "text": "Explain how binary search works on a sorted array. Demonstrate finding the number 7 in [1, 3, 5, 7, 9, 11].",
                "options": None
            },
            "state_tracer": {
                "id": "state_tracer_test",
                "text": "Trace through this code step by step, showing how variables change:\n\ndef factorial(n):\n    result = 1\n    for i in range(1, n+1):\n        result = result * i\n    return result\n\nfactorial(4)",
                "options": None
            }
        }

        question = test_questions.get(args.question, test_questions["binary_search"])
        print(f"Question: {question['text'][:60]}...")

        pipeline_result = await test_pipeline_topology(args.topology, question, logger)
        results.append(pipeline_result)

    # Print results
    print_results(results)

    # Save results
    output_file = Path(__file__).parent / "local_pipeline_test_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "topology": args.topology,
            "results": [asdict(r) for r in results]
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Return exit code based on results
    passed = sum(1 for r in results if r.success)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
