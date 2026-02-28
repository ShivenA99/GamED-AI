#!/usr/bin/env python3
"""
Topology Benchmark Runner

Runs comprehensive benchmarks comparing different agent topologies
on quality, cost, and latency metrics.

Usage:
    # Quick benchmark (2 test cases, T0 vs T1)
    python scripts/run_benchmark.py --quick

    # Full benchmark with all topologies
    python scripts/run_benchmark.py --full

    # Specific topologies
    python scripts/run_benchmark.py --topologies T0,T1,T2,T4

    # Custom test cases from file
    python scripts/run_benchmark.py --test-cases tests/custom_cases.json

    # With specific model preset
    AGENT_CONFIG_PRESET=cost_optimized python scripts/run_benchmark.py --full
"""

import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.evaluation import (
    TopologyBenchmark,
    TestCase,
    BenchmarkReport,
    SAMPLE_TEST_CASES,
    QUALITY_RUBRIC,
    calculate_automated_metrics
)
from app.agents.topologies import TopologyType, TopologyConfig
from app.services.llm_service import get_llm_service, LLMService


# =============================================================================
# EXTENDED TEST CASES
# =============================================================================

EXTENDED_TEST_CASES = [
    # Computer Science - Algorithms
    TestCase(
        id="algo_binary_search",
        question_text="Explain the time complexity of binary search and demonstrate how it works on a sorted array [2, 4, 6, 8, 10, 12, 14] when searching for 10.",
        expected_template="PARAMETER_PLAYGROUND",
        blooms_level="understand",
        subject="Computer Science",
        difficulty="intermediate",
        tags=["algorithm", "search", "complexity"]
    ),
    TestCase(
        id="algo_bubble_sort",
        question_text="Demonstrate the bubble sort algorithm step by step on the array [5, 2, 8, 1, 9]. Show each pass and swap.",
        expected_template="STATE_TRACER_CODE",
        blooms_level="apply",
        subject="Computer Science",
        difficulty="intermediate",
        tags=["algorithm", "sorting", "visualization"]
    ),
    TestCase(
        id="algo_stack_operations",
        question_text="Arrange the following stack operations in the order they would execute: push(5), pop(), push(3), push(7), pop(), push(2).",
        question_options=["push(5)", "pop()", "push(3)", "push(7)", "pop()", "push(2)"],
        expected_template="SEQUENCE_BUILDER",
        blooms_level="apply",
        subject="Computer Science",
        difficulty="beginner",
        tags=["data-structure", "stack"]
    ),

    # Biology
    TestCase(
        id="bio_cell_structure",
        question_text="Label the main parts of an animal cell including the nucleus, mitochondria, cell membrane, ribosomes, and endoplasmic reticulum.",
        expected_template="INTERACTIVE_DIAGRAM",
        blooms_level="remember",
        subject="Biology",
        difficulty="beginner",
        tags=["biology", "cell", "labeling"]
    ),
    TestCase(
        id="bio_classification",
        question_text="Categorize the following organisms into their correct kingdoms: Mushroom, Oak Tree, E. coli, Amoeba, Human, Influenza Virus.",
        question_options=["Mushroom", "Oak Tree", "E. coli", "Amoeba", "Human", "Influenza Virus"],
        expected_template="BUCKET_SORT",
        blooms_level="apply",
        subject="Biology",
        difficulty="intermediate",
        tags=["biology", "classification"]
    ),
    TestCase(
        id="bio_cell_division",
        question_text="Arrange the phases of mitosis in correct order: Metaphase, Anaphase, Prophase, Telophase, Cytokinesis.",
        question_options=["Metaphase", "Anaphase", "Prophase", "Telophase", "Cytokinesis"],
        expected_template="SEQUENCE_BUILDER",
        blooms_level="understand",
        subject="Biology",
        difficulty="intermediate",
        tags=["biology", "cell-division"]
    ),

    # Chemistry
    TestCase(
        id="chem_elements",
        question_text="Categorize the following elements into metals, non-metals, and metalloids: Iron, Carbon, Silicon, Gold, Oxygen, Arsenic, Copper, Sulfur.",
        question_options=["Iron", "Carbon", "Silicon", "Gold", "Oxygen", "Arsenic", "Copper", "Sulfur"],
        expected_template="BUCKET_SORT",
        blooms_level="apply",
        subject="Chemistry",
        difficulty="beginner",
        tags=["chemistry", "elements", "categorization"]
    ),
    TestCase(
        id="chem_periodic_table",
        question_text="Label the parts of the periodic table including: Alkali metals, Noble gases, Halogens, Transition metals, Lanthanides.",
        expected_template="INTERACTIVE_DIAGRAM",
        blooms_level="remember",
        subject="Chemistry",
        difficulty="beginner",
        tags=["chemistry", "periodic-table"]
    ),

    # History
    TestCase(
        id="history_revolution",
        question_text="Arrange the following events of the American Revolution in chronological order: Boston Tea Party, Declaration of Independence, Battle of Yorktown, First Continental Congress, Lexington and Concord.",
        question_options=["Boston Tea Party", "Declaration of Independence", "Battle of Yorktown", "First Continental Congress", "Lexington and Concord"],
        expected_template="TIMELINE_ORDER",
        blooms_level="understand",
        subject="History",
        difficulty="intermediate",
        tags=["history", "timeline", "sequence"]
    ),
    TestCase(
        id="history_inventions",
        question_text="Match each inventor to their invention: Edison-Light Bulb, Bell-Telephone, Wright Brothers-Airplane, Gutenberg-Printing Press.",
        question_options=["Edison", "Bell", "Wright Brothers", "Gutenberg", "Light Bulb", "Telephone", "Airplane", "Printing Press"],
        expected_template="MATCH_PAIRS",
        blooms_level="remember",
        subject="History",
        difficulty="beginner",
        tags=["history", "inventors"]
    ),

    # Physics
    TestCase(
        id="physics_projectile",
        question_text="Explore how launch angle and initial velocity affect the range of a projectile. Find the optimal angle for maximum distance.",
        expected_template="PARAMETER_PLAYGROUND",
        blooms_level="analyze",
        subject="Physics",
        difficulty="intermediate",
        tags=["physics", "projectile", "simulation"]
    ),

    # Mathematics
    TestCase(
        id="math_equation_steps",
        question_text="Arrange the steps to solve the equation 2x + 5 = 13 in correct order.",
        question_options=["Start with 2x + 5 = 13", "Subtract 5 from both sides", "Get 2x = 8", "Divide both sides by 2", "x = 4"],
        expected_template="SEQUENCE_BUILDER",
        blooms_level="apply",
        subject="Mathematics",
        difficulty="beginner",
        tags=["math", "algebra", "equations"]
    ),
]


# =============================================================================
# TOPOLOGY CONFIGURATIONS
# =============================================================================

TOPOLOGY_CONFIGS = {
    TopologyType.T0_SEQUENTIAL: TopologyConfig(
        max_retries=0,
        confidence_threshold=0.0,
        human_review_enabled=False
    ),
    TopologyType.T1_SEQUENTIAL_VALIDATED: TopologyConfig(
        max_retries=3,
        confidence_threshold=0.7,
        human_review_enabled=True
    ),
    TopologyType.T2_ACTOR_CRITIC: TopologyConfig(
        max_retries=3,
        confidence_threshold=0.8
    ),
    TopologyType.T4_SELF_REFINE: TopologyConfig(
        max_iterations=3,
        improvement_threshold=0.1
    ),
}


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

async def run_benchmark(
    test_cases: List[TestCase],
    topologies: List[TopologyType],
    output_dir: Path,
    llm_service: Optional[LLMService] = None
) -> BenchmarkReport:
    """Run the benchmark and return results"""
    print("\n" + "=" * 70)
    print("GAMED.AI TOPOLOGY BENCHMARK")
    print("=" * 70)
    print(f"\nTest Cases: {len(test_cases)}")
    print(f"Topologies: {[t.value for t in topologies]}")
    print(f"Output Dir: {output_dir}")
    print("\n" + "-" * 70)

    # Initialize benchmark runner
    benchmark = TopologyBenchmark(
        llm_service=llm_service,
        output_dir=output_dir
    )

    # Run benchmark
    report = await benchmark.run_benchmark(
        test_cases=test_cases,
        topologies=topologies,
        configs=TOPOLOGY_CONFIGS
    )

    return report


def print_report(report: BenchmarkReport):
    """Print formatted benchmark report"""
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    print(f"\nRun ID: {report.run_id}")
    print(f"Timestamp: {report.timestamp}")
    print(f"Test Cases: {report.test_cases}")
    print(f"Topologies: {', '.join(report.topologies_tested)}")

    # Per-topology summary
    print("\n" + "-" * 70)
    print("PER-TOPOLOGY METRICS")
    print("-" * 70)

    for topology, stats in report.summary.items():
        if topology == "rankings":
            continue

        print(f"\n{topology.upper()}:")
        print(f"  Success Rate:     {stats.get('success_rate', 0):.1%}")
        print(f"  Avg Latency:      {stats.get('avg_latency_ms', 0):.0f}ms")
        print(f"  Avg Iterations:   {stats.get('avg_iterations', 0):.1f}")
        print(f"  Human Intervention: {stats.get('human_intervention_rate', 0):.1%}")

        quality = stats.get('avg_quality_scores', {})
        if quality:
            print(f"  Quality Scores:")
            print(f"    - Pedagogical:  {quality.get('pedagogical', 0):.2f}")
            print(f"    - Engagement:   {quality.get('engagement', 0):.2f}")
            print(f"    - Technical:    {quality.get('technical', 0):.2f}")
            print(f"    - Narrative:    {quality.get('narrative', 0):.2f}")
            print(f"    - Overall:      {quality.get('overall', 0):.2f}")

    # Rankings
    rankings = report.summary.get("rankings", {})
    if rankings:
        print("\n" + "-" * 70)
        print("RANKINGS")
        print("-" * 70)

        if rankings.get("by_success_rate"):
            print(f"\nBy Success Rate: {' > '.join(rankings['by_success_rate'][:3])}")
        if rankings.get("by_quality"):
            print(f"By Quality:      {' > '.join(rankings['by_quality'][:3])}")
        if rankings.get("by_latency"):
            print(f"By Latency:      {' > '.join(rankings['by_latency'][:3])}")

    # Failed tests
    failures = [r for r in report.results if not r.success]
    if failures:
        print("\n" + "-" * 70)
        print(f"FAILURES ({len(failures)})")
        print("-" * 70)
        for f in failures[:5]:  # Show first 5
            print(f"\n  [{f.topology_type.value}] {f.test_case_id}")
            print(f"    Error: {f.error_message[:100] if f.error_message else 'Unknown'}")

    print("\n" + "=" * 70)
    print(f"Full report saved to: {report.run_id}")
    print("=" * 70 + "\n")


def load_test_cases_from_file(filepath: str) -> List[TestCase]:
    """Load test cases from JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)

    cases = []
    for item in data:
        cases.append(TestCase(
            id=item["id"],
            question_text=item["question_text"],
            question_options=item.get("question_options"),
            expected_template=item.get("expected_template"),
            blooms_level=item.get("blooms_level"),
            subject=item.get("subject"),
            difficulty=item.get("difficulty"),
            tags=item.get("tags", [])
        ))
    return cases


def parse_topologies(topology_str: str) -> List[TopologyType]:
    """Parse comma-separated topology string"""
    topology_map = {
        "T0": TopologyType.T0_SEQUENTIAL,
        "T1": TopologyType.T1_SEQUENTIAL_VALIDATED,
        "T2": TopologyType.T2_ACTOR_CRITIC,
        "T3": TopologyType.T3_HIERARCHICAL,
        "T4": TopologyType.T4_SELF_REFINE,
        "T5": TopologyType.T5_DEBATE,
        "T6": TopologyType.T6_DAG_PARALLEL,
        "T7": TopologyType.T7_REFLECTION_MEMORY,
    }

    topologies = []
    for t in topology_str.split(","):
        t = t.strip().upper()
        if t in topology_map:
            topologies.append(topology_map[t])
        else:
            print(f"Warning: Unknown topology '{t}', skipping")

    return topologies


async def main():
    parser = argparse.ArgumentParser(description="Run topology benchmarks")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick benchmark (2 test cases, T0 vs T1)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full benchmark with all implemented topologies"
    )
    parser.add_argument(
        "--topologies",
        type=str,
        default="T0,T1",
        help="Comma-separated list of topologies (e.g., T0,T1,T2,T4)"
    )
    parser.add_argument(
        "--test-cases",
        type=str,
        help="Path to JSON file with test cases"
    )
    parser.add_argument(
        "--num-cases",
        type=int,
        default=5,
        help="Number of test cases to run (default: 5)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="Skip LLM-based quality evaluation"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Determine topologies
    if args.quick:
        topologies = [TopologyType.T0_SEQUENTIAL, TopologyType.T1_SEQUENTIAL_VALIDATED]
        num_cases = 2
    elif args.full:
        topologies = [
            TopologyType.T0_SEQUENTIAL,
            TopologyType.T1_SEQUENTIAL_VALIDATED,
            TopologyType.T2_ACTOR_CRITIC,
            TopologyType.T4_SELF_REFINE,
        ]
        num_cases = args.num_cases
    else:
        topologies = parse_topologies(args.topologies)
        num_cases = args.num_cases

    if not topologies:
        print("Error: No valid topologies specified")
        sys.exit(1)

    # Determine test cases
    if args.test_cases:
        test_cases = load_test_cases_from_file(args.test_cases)
    else:
        test_cases = EXTENDED_TEST_CASES[:num_cases]

    # Setup output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Initialize LLM service for judge (optional)
    llm_service = None
    if not args.no_llm_judge:
        try:
            llm_service = get_llm_service()
            print("LLM Judge enabled")
        except Exception as e:
            print(f"Warning: Could not initialize LLM service: {e}")
            print("Running without LLM-based quality evaluation")

    # Run benchmark
    report = await run_benchmark(
        test_cases=test_cases,
        topologies=topologies,
        output_dir=output_dir,
        llm_service=llm_service
    )

    # Print results
    print_report(report)

    # Calculate and display automated metrics
    automated = calculate_automated_metrics(report.results)
    if automated:
        print("\nAUTOMATED METRICS (aggregate):")
        print(json.dumps(automated, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
