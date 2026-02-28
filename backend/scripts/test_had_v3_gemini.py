#!/usr/bin/env python3
"""
HAD v3 Gemini-Only Test Script

Tests the HAD v3 implementation with:
- Gemini-only zone detection (polygon output)
- Unified game_designer (replaces 4-agent orchestrator)
- Multi-scene support
- Polygon IoU collision resolution

Generates run log documents in backend/run_logs/

Usage:
    # Run full test suite
    cd backend && source venv/bin/activate
    PYTHONPATH=. python scripts/test_had_v3_gemini.py

    # Run quick test (first case only)
    PYTHONPATH=. python scripts/test_had_v3_gemini.py --quick

    # Run academic multi-scene test
    PYTHONPATH=. python scripts/test_had_v3_gemini.py --academic

    # Custom question
    PYTHONPATH=. python scripts/test_had_v3_gemini.py --question "Label the parts of a flower"
"""

import warnings
warnings.filterwarnings("ignore", message=".*Pydantic V1.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pydantic.v1.*", category=UserWarning)

import asyncio
import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)

logger = logging.getLogger("had_v3_test")
logging.getLogger("gamed_ai").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set HAD v3 environment variables BEFORE importing graph module
# These are read at module import time
os.environ["HAD_USE_GEMINI_DIRECT"] = "true"
os.environ["HAD_USE_UNIFIED_DESIGNER"] = "true"

from app.agents.state import create_initial_state
from app.agents.graph import create_had_graph


# =============================================================================
# Token Tracking
# =============================================================================

@dataclass
class TokenUsage:
    """Track token usage per agent."""
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def estimated_cost(self) -> float:
        """Estimate cost based on Gemini pricing."""
        # Gemini pricing (per 1M tokens)
        PRICING = {
            "gemini-2.5-flash-lite": (0.10, 0.40),
            "gemini-2.5-flash": (0.30, 2.50),
            "gemini-3-flash": (0.50, 3.00),
            "gemini-3-flash-preview": (0.50, 3.00),
            "gemini-2.5-pro": (1.25, 10.00),
        }
        input_rate, output_rate = PRICING.get(self.model, (0.50, 3.00))
        return (self.input_tokens * input_rate + self.output_tokens * output_rate) / 1_000_000


class TokenTracker:
    """Accumulate token usage across agents."""

    def __init__(self, budget_tokens: int = 50000):
        self.usages: List[TokenUsage] = []
        self.budget_tokens = budget_tokens

    def add(self, agent: str, model: str, input_tokens: int, output_tokens: int, latency_ms: int):
        self.usages.append(TokenUsage(
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms
        ))

    def check_budget(self) -> bool:
        """Check if we're within token budget."""
        return self.total_tokens < self.budget_tokens

    @property
    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self.usages)

    @property
    def total_input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.usages)

    @property
    def total_output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.usages)

    @property
    def total_cost(self) -> float:
        return sum(u.estimated_cost() for u in self.usages)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "num_calls": len(self.usages),
            "budget_remaining": self.budget_tokens - self.total_tokens,
            "by_agent": {
                u.agent: {
                    "model": u.model,
                    "tokens": u.total_tokens,
                    "cost_usd": round(u.estimated_cost(), 4)
                }
                for u in self.usages
            }
        }


# =============================================================================
# Issue Tracking
# =============================================================================

@dataclass
class Issue:
    """Track an issue found during testing."""
    category: str  # "bug", "gap", "warning", "improvement"
    description: str
    severity: str  # "critical", "high", "medium", "low"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class IssueTracker:
    """Collect issues found during testing."""

    def __init__(self):
        self.issues: List[Issue] = []

    def add(self, category: str, description: str, severity: str = "medium", data: Dict = None):
        issue = Issue(
            category=category,
            description=description,
            severity=severity,
            data=data or {}
        )
        self.issues.append(issue)
        logger.warning(f"ISSUE [{severity.upper()}]: {category} - {description}")

    def get_all(self) -> List[Dict]:
        return [
            {
                "category": i.category,
                "description": i.description,
                "severity": i.severity,
                "data": i.data,
                "timestamp": i.timestamp
            }
            for i in self.issues
        ]

    def summary(self) -> str:
        if not self.issues:
            return "No issues found!"

        by_severity = {}
        for issue in self.issues:
            sev = issue.severity
            by_severity[sev] = by_severity.get(sev, 0) + 1

        lines = [f"Issues Found: {len(self.issues)}"]
        for sev in ["critical", "high", "medium", "low"]:
            if sev in by_severity:
                lines.append(f"  - {sev}: {by_severity[sev]}")
        return "\n".join(lines)

    def has_critical(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)


# =============================================================================
# Test Cases
# =============================================================================

TEST_CASES = [
    # Single scene, anatomical diagram (some overlap expected between central structures)
    {
        "id": "flower_parts",
        "question": "Label the parts of a flower including petal, sepal, stamen, and pistil",
        "expected": {
            "needs_multi_scene": False,
            "min_zones": 4,
            # Note: Flower diagrams naturally have overlapping structures in the center
            # (stamen, pistil, style, ovary occupy overlapping areas)
            "discrete_overlaps_allowed": 6,
            "relationship_types": ["contains", "has_part", "composed_of"]
        }
    },
    # Single scene, layered zones (overlap OK)
    {
        "id": "heart_wall_layers",
        "question": "Identify the three layers of the heart wall: epicardium, myocardium, and endocardium",
        "expected": {
            "needs_multi_scene": False,
            "min_zones": 4,  # Heart Wall + 3 layers
            "layered_overlaps_allowed": True,
            "relationship_types": ["composed_of"]
        }
    },
    # Multi-scene test (>12 labels)
    {
        "id": "animal_cell_full",
        "question": "Label all organelles in an animal cell including nucleus, mitochondria, ribosomes, endoplasmic reticulum, golgi apparatus, lysosomes, cell membrane, cytoplasm, centrioles, vacuoles, nucleolus, chromatin, and nuclear envelope",
        "expected": {
            "needs_multi_scene": True,
            "min_scenes": 2,
            "min_zones_scene1": 6,
            "progression_types": ["linear", "zoom_in", "branching"]
        }
    },
]

# Academic test case (AP Biology - Multi-Scene)
ACADEMIC_TEST_CASE = {
    "id": "animal_cell_academic",
    "question": """Label the complete structure of a eukaryotic animal cell, including:
- Cell membrane with phospholipid bilayer
- Nucleus with nucleolus, chromatin, and nuclear envelope
- Mitochondria with outer membrane, inner membrane, cristae, and matrix
- Endoplasmic reticulum (rough and smooth)
- Golgi apparatus with cis and trans faces
- Ribosomes, lysosomes, and peroxisomes
- Cytoskeleton components (microtubules, microfilaments, intermediate filaments)
- Centrioles and centrosome""",
    "expected": {
        "needs_multi_scene": True,
        "min_scenes": 2,
        "min_zones_scene1": 6,
        "hierarchy_depth": 3,
        "progression_types": ["linear", "zoom_in", "branching"]
    }
}


# =============================================================================
# Validation Functions
# =============================================================================

async def validate_zone_planner_output(
    output: Dict,
    expected: Dict,
    issue_tracker: IssueTracker
):
    """Validate zone_planner output against expected values."""
    zones = output.get("diagram_zones", [])
    needs_multi_scene = output.get("needs_multi_scene", False)
    collision_metadata = output.get("zone_collision_metadata", {})

    # Check zone count
    min_zones = expected.get("min_zones", 0)
    if len(zones) < min_zones:
        issue_tracker.add(
            "gap",
            f"Expected at least {min_zones} zones, got {len(zones)}",
            severity="high",
            data={"expected": min_zones, "actual": len(zones)}
        )

    # Check polygon zones (HAD v3 target: >80% polygon)
    polygon_count = sum(1 for z in zones if z.get("points") or z.get("shape") == "polygon")
    polygon_pct = (polygon_count / len(zones) * 100) if zones else 0
    if polygon_pct < 80:
        issue_tracker.add(
            "warning",
            f"Polygon zones: {polygon_pct:.0f}% (target: >80%)",
            severity="medium",
            data={"polygon_count": polygon_count, "total_zones": len(zones)}
        )

    # Check multi-scene detection
    expected_multi_scene = expected.get("needs_multi_scene", False)
    if needs_multi_scene != expected_multi_scene:
        issue_tracker.add(
            "gap",
            f"Multi-scene detection mismatch: expected {expected_multi_scene}, got {needs_multi_scene}",
            severity="high"
        )

    # Check discrete overlaps
    if not expected.get("layered_overlaps_allowed", False):
        discrete_overlaps_data = collision_metadata.get("after", {}).get("discrete_overlaps", [])
        # Handle both list and int formats
        discrete_overlaps = len(discrete_overlaps_data) if isinstance(discrete_overlaps_data, list) else discrete_overlaps_data
        allowed = expected.get("discrete_overlaps_allowed", 0)
        if discrete_overlaps > allowed:
            issue_tracker.add(
                "bug",
                f"Discrete zone overlaps: {discrete_overlaps} (max allowed: {allowed})",
                severity="high",
                data=collision_metadata
            )


async def validate_game_designer_output(
    output: Dict,
    expected: Dict,
    issue_tracker: IssueTracker
):
    """Validate game_designer/game_orchestrator output."""
    game_plan = output.get("game_plan", {})
    game_sequence = output.get("game_sequence", {})
    design_metadata = output.get("design_metadata", {})

    if not game_plan:
        issue_tracker.add(
            "gap",
            "game_plan is empty",
            severity="medium"
        )

    # Check if unified design was used
    if design_metadata.get("unified_call"):
        logger.info("Using HAD v3 unified game_designer")
    else:
        issue_tracker.add(
            "warning",
            "Not using unified game_designer (falling back to sequential)",
            severity="low",
            data=design_metadata
        )

    # Check multi-scene structure
    if expected.get("needs_multi_scene", False):
        scenes = game_sequence.get("scenes", [])
        min_scenes = expected.get("min_scenes", 2)
        if len(scenes) < min_scenes:
            issue_tracker.add(
                "gap",
                f"Expected at least {min_scenes} scenes, got {len(scenes)}",
                severity="high"
            )

        progression = game_sequence.get("progression_type")
        allowed = expected.get("progression_types", [])
        if progression and allowed and progression not in allowed:
            issue_tracker.add(
                "warning",
                f"Unexpected progression type: {progression} (expected one of {allowed})",
                severity="low"
            )


# =============================================================================
# Run Log Generation
# =============================================================================

def generate_run_log(
    run_id: str,
    test_id: str,
    question: str,
    results: Dict,
    token_tracker: TokenTracker,
    issue_tracker: IssueTracker,
    duration_ms: int,
    preset: str
) -> str:
    """Generate a markdown run log document."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# HAD v3 Gemini Pipeline Run Log",
        "",
        "## Run Metadata",
        f"- **Run ID:** {run_id}",
        f"- **Test ID:** {test_id}",
        f"- **Timestamp:** {timestamp}",
        f"- **Model Preset:** {preset}",
        f"- **Total Duration:** {duration_ms}ms",
        "",
        "### Query",
        "```",
        question[:500] + ("..." if len(question) > 500 else ""),
        "```",
        "",
        "## Token Usage Summary",
        "",
        "| Agent | Model | Input | Output | Cost |",
        "|-------|-------|-------|--------|------|",
    ]

    for usage in token_tracker.usages:
        lines.append(
            f"| {usage.agent} | {usage.model} | {usage.input_tokens} | "
            f"{usage.output_tokens} | ${usage.estimated_cost():.4f} |"
        )

    summary = token_tracker.summary()
    lines.extend([
        f"| **TOTAL** | - | **{summary['total_input_tokens']}** | "
        f"**{summary['total_output_tokens']}** | **${summary['total_cost_usd']:.4f}** |",
        "",
        "## Zone Detection Results",
        "",
    ])

    zones = results.get("outputs", {}).get("diagram_zones", [])
    zone_groups = results.get("outputs", {}).get("zone_groups", [])
    collision_metadata = results.get("outputs", {}).get("zone_collision_metadata", {})

    polygon_count = sum(1 for z in zones if z.get("points") or z.get("shape") == "polygon")

    lines.extend([
        f"- **Zones Detected:** {len(zones)}",
        f"- **Polygon Zones:** {polygon_count} ({polygon_count/len(zones)*100:.0f}%)" if zones else "- **Polygon Zones:** 0 (0%)",
        f"- **Zone Groups:** {len(zone_groups)}",
        f"- **Multi-scene:** {results.get('outputs', {}).get('needs_multi_scene', False)}",
        "",
    ])

    if collision_metadata:
        before = collision_metadata.get("before", {})
        after = collision_metadata.get("after", {})
        lines.extend([
            "### Collision Resolution",
            f"- Overlaps before: {before.get('discrete_overlaps', 'N/A')}",
            f"- Overlaps after: {after.get('discrete_overlaps', 'N/A')}",
            "",
        ])

    lines.extend([
        "## Game Design Results",
        "",
    ])

    game_plan = results.get("outputs", {}).get("game_plan", {})
    if game_plan:
        lines.extend([
            f"- **Learning Objectives:** {len(game_plan.get('learning_objectives', []))}",
            f"- **Game Mechanics:** {len(game_plan.get('game_mechanics', []))}",
            "",
        ])

    lines.extend([
        "## Issues Found",
        "",
    ])

    if issue_tracker.issues:
        for i, issue in enumerate(issue_tracker.issues, 1):
            lines.append(f"{i}. **[{issue.severity.upper()}]** {issue.category}: {issue.description}")
    else:
        lines.append("No issues found!")

    lines.extend([
        "",
        "## Raw Outputs",
        "",
        "<details>",
        "<summary>Zone Planner Output</summary>",
        "",
        "```json",
        json.dumps({
            "diagram_zones": results.get("outputs", {}).get("diagram_zones", [])[:3],
            "zone_groups": results.get("outputs", {}).get("zone_groups", []),
            "needs_multi_scene": results.get("outputs", {}).get("needs_multi_scene", False),
        }, indent=2),
        "```",
        "",
        "</details>",
        "",
        "<details>",
        "<summary>Game Designer Output</summary>",
        "",
        "```json",
        json.dumps({
            "game_plan": results.get("outputs", {}).get("game_plan", {}),
        }, indent=2)[:2000] + "...",
        "```",
        "",
        "</details>",
        "",
        "---",
        f"*Generated by HAD v3 Test Script at {timestamp}*",
    ])

    return "\n".join(lines)


# =============================================================================
# Main Test Runner
# =============================================================================

async def run_single_test(
    test_case: Dict,
    token_tracker: TokenTracker,
    issue_tracker: IssueTracker,
    use_unified_designer: bool = True
) -> Dict:
    """Run a single test case through HAD v3 pipeline."""

    test_id = test_case["id"]
    question = test_case["question"]
    expected = test_case["expected"]

    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: {test_id}")
    logger.info(f"Question: {question[:100]}...")
    logger.info(f"{'='*60}")

    start_time = time.time()
    result = {
        "test_id": test_id,
        "question": question,
        "success": False,
        "errors": [],
        "outputs": {},
        "duration_ms": 0
    }

    try:
        # Note: HAD v3 env vars are set at module level before import
        # The use_unified_designer param is for logging purposes only now

        # Create initial state
        initial_state = create_initial_state(
            question_id=test_id,
            question_text=question,
            question_options=None
        )

        # Create HAD graph (Hierarchical Agentic DAG)
        graph = create_had_graph()
        compiled = graph.compile()

        # Stream through pipeline with monitoring
        current_state = initial_state
        stage_count = 0

        async for state_update in compiled.astream(initial_state):
            stage_count += 1

            for agent_name, partial_state in state_update.items():
                if agent_name.startswith("_"):
                    continue

                logger.info(f"Stage {stage_count}: {agent_name}")
                logger.debug(f"  Output keys: {list(partial_state.keys())}")

                # Check token budget
                if not token_tracker.check_budget():
                    issue_tracker.add(
                        "budget",
                        f"Token budget exceeded at stage {agent_name}",
                        severity="critical"
                    )
                    raise Exception("Token budget exceeded - stopping test")

                # Merge into current state
                current_state.update(partial_state)

                # Validate specific agent outputs
                if agent_name == "zone_planner":
                    await validate_zone_planner_output(
                        partial_state, expected, issue_tracker
                    )
                elif agent_name in ("game_orchestrator", "game_designer"):
                    # Debug: Log what we received from game_designer
                    logger.info(f"  game_designer partial_state keys: {list(partial_state.keys())}")
                    logger.info(f"  game_designer design_metadata: {partial_state.get('design_metadata')}")
                    await validate_game_designer_output(
                        partial_state, expected, issue_tracker
                    )

        # Collect final outputs
        result["outputs"] = {
            "diagram_zones": current_state.get("diagram_zones", []),
            "zone_groups": current_state.get("zone_groups", []),
            "needs_multi_scene": current_state.get("needs_multi_scene", False),
            "num_scenes": current_state.get("num_scenes", 1),
            "scene_breakdown": current_state.get("scene_breakdown", []),
            "zone_collision_metadata": current_state.get("zone_collision_metadata", {}),
            "query_intent": current_state.get("query_intent", {}),
            "game_plan": current_state.get("game_plan", {}),
            "design_metadata": current_state.get("design_metadata", {}),
        }

        result["success"] = True
        logger.info(f"Test {test_id} PASSED")

    except Exception as e:
        result["errors"].append(str(e))
        issue_tracker.add(
            "error",
            f"Test {test_id} failed: {str(e)}",
            severity="critical"
        )
        logger.error(f"Test {test_id} FAILED: {e}")

    result["duration_ms"] = int((time.time() - start_time) * 1000)
    return result


async def main():
    parser = argparse.ArgumentParser(description="Test HAD v3 Gemini-only implementation")
    parser.add_argument("--question", type=str, help="Custom question to test")
    parser.add_argument("--multi-scene", action="store_true", help="Force multi-scene test")
    parser.add_argument("--quick", action="store_true", help="Run only first test case")
    parser.add_argument("--academic", action="store_true", help="Run academic (AP Biology) test")
    parser.add_argument("--legacy", action="store_true", help="Use legacy game_orchestrator instead of game_designer")
    parser.add_argument("--save-log", action="store_true", default=True, help="Save run log to file")
    args = parser.parse_args()

    # Create run_logs directory
    run_logs_dir = Path(__file__).parent.parent / "run_logs"
    run_logs_dir.mkdir(exist_ok=True)

    token_tracker = TokenTracker()
    issue_tracker = IssueTracker()

    preset = os.environ.get("AGENT_CONFIG_PRESET", "gemini_only")
    use_unified_designer = not args.legacy

    logger.info("="*60)
    logger.info("HAD v3 GEMINI-ONLY TEST SUITE")
    logger.info(f"Using preset: {preset}")
    logger.info(f"Unified designer: {use_unified_designer}")
    logger.info("="*60)

    # Determine test cases
    if args.question:
        test_cases = [{
            "id": "custom",
            "question": args.question,
            "expected": {
                "needs_multi_scene": args.multi_scene,
                "min_zones": 3
            }
        }]
    elif args.academic:
        test_cases = [ACADEMIC_TEST_CASE]
    elif args.quick:
        test_cases = TEST_CASES[:1]
    else:
        test_cases = TEST_CASES

    # Run tests
    results = []
    total_start = time.time()

    for tc in test_cases:
        result = await run_single_test(
            tc, token_tracker, issue_tracker, use_unified_designer
        )
        results.append(result)

        if not token_tracker.check_budget():
            logger.warning("Stopping tests - token budget exceeded")
            break

    total_duration_ms = int((time.time() - total_start) * 1000)

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)

    passed = sum(1 for r in results if r["success"])
    logger.info(f"Tests: {passed}/{len(results)} passed")

    logger.info(f"\nToken Usage:")
    usage = token_tracker.summary()
    logger.info(f"  Total: {usage['total_tokens']} ({usage['total_input_tokens']} in / {usage['total_output_tokens']} out)")
    logger.info(f"  Estimated Cost: ${usage['total_cost_usd']:.4f}")
    logger.info(f"  LLM Calls: {usage['num_calls']}")

    logger.info(f"\n{issue_tracker.summary()}")

    if issue_tracker.issues:
        logger.info("\nDetailed Issues:")
        for i, issue in enumerate(issue_tracker.get_all(), 1):
            logger.info(f"  {i}. [{issue['severity']}] {issue['category']}: {issue['description']}")

    # Generate run log
    if args.save_log and results:
        run_id = str(uuid.uuid4())[:8]
        first_result = results[0]

        run_log = generate_run_log(
            run_id=run_id,
            test_id=first_result["test_id"],
            question=first_result["question"],
            results=first_result,
            token_tracker=token_tracker,
            issue_tracker=issue_tracker,
            duration_ms=total_duration_ms,
            preset=preset
        )

        log_filename = f"had_v3_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        log_path = run_logs_dir / log_filename
        log_path.write_text(run_log)
        logger.info(f"\nRun log saved to: {log_path}")

    # Save JSON results
    output_path = Path(__file__).parent.parent / f"had_v3_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump({
            "results": results,
            "token_usage": usage,
            "issues": issue_tracker.get_all(),
            "preset": preset,
            "unified_designer": use_unified_designer,
            "total_duration_ms": total_duration_ms
        }, f, indent=2, default=str)
    logger.info(f"Results saved to: {output_path}")

    # Return exit code
    if issue_tracker.has_critical():
        sys.exit(1)
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
