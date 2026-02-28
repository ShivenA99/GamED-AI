"""
Evaluation Framework for Topology Benchmarking

This module provides tools for:
1. Running benchmark tests across topologies
2. Collecting metrics (quality, cost, latency)
3. Comparing topology performance
4. Generating evaluation reports
5. LLM-as-Judge quality assessment

Quality Dimensions:
- Pedagogical Alignment: Bloom's level, learning objectives
- Game Engagement: Interactivity, feedback, difficulty
- Technical Quality: Schema validity, completeness
- Narrative Quality: Story coherence, engagement
- Asset Quality: Visual prompts, animation cues
"""
import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.agents.topologies import (
    TopologyType,
    TopologyConfig,
    TopologyMetrics,
    StageMetrics,
    create_topology
)
from app.agents.state import create_initial_state, AgentState
from app.utils.logging_config import get_logger
from app.config.pedagogical_constants import BLOOM_LEVELS, BLOOM_COMPLEXITY

logger = get_logger("gamed_ai.evaluation")


# =============================================================================
# QUALITY RUBRIC FOR LLM-AS-JUDGE
# =============================================================================

QUALITY_RUBRIC = {
    "pedagogical_alignment": {
        "description": "How well the game content aligns with learning objectives and Bloom's taxonomy",
        "weight": 0.30,  # 30% of total score
        "levels": {
            5: {
                "label": "Excellent",
                "criteria": [
                    "Perfect Bloom's level match for the stated objective",
                    "All key concepts from the question are addressed",
                    "Misconceptions are proactively anticipated and addressed",
                    "Progressive difficulty scaffolds learning effectively",
                    "Assessment accurately measures stated learning outcomes"
                ]
            },
            4: {
                "label": "Good",
                "criteria": [
                    "Good alignment with Bloom's level (within one level)",
                    "Most key concepts are covered adequately",
                    "Some misconception handling present",
                    "Reasonable difficulty progression",
                    "Assessment mostly matches learning objectives"
                ]
            },
            3: {
                "label": "Acceptable",
                "criteria": [
                    "Bloom's level approximately correct",
                    "Core concepts addressed but gaps exist",
                    "Limited misconception awareness",
                    "Flat or inconsistent difficulty",
                    "Assessment partially aligned with objectives"
                ]
            },
            2: {
                "label": "Poor",
                "criteria": [
                    "Wrong Bloom's level (e.g., remember vs analyze)",
                    "Missing critical concepts",
                    "No misconception handling",
                    "Inappropriate difficulty (too easy/hard)",
                    "Assessment misaligned with stated goals"
                ]
            },
            1: {
                "label": "Unacceptable",
                "criteria": [
                    "No pedagogical coherence",
                    "Content doesn't relate to learning objective",
                    "Potentially teaches incorrect information",
                    "No meaningful assessment",
                    "Would confuse or mislead learners"
                ]
            }
        }
    },

    "game_engagement": {
        "description": "How interactive, engaging, and playable the game experience is",
        "weight": 0.25,  # 25% of total score
        "levels": {
            5: {
                "label": "Highly Engaging",
                "criteria": [
                    "Multiple meaningful interactions per minute",
                    "Clear, immediate feedback for all actions",
                    "Compelling narrative hooks and visual metaphors",
                    "Appropriate challenge level with hints available",
                    "Clear win/lose conditions and progress indicators"
                ]
            },
            4: {
                "label": "Engaging",
                "criteria": [
                    "Regular interaction opportunities",
                    "Good feedback for most actions",
                    "Functional narrative context",
                    "Reasonable challenge with some support",
                    "Clear objectives and progress tracking"
                ]
            },
            3: {
                "label": "Functional",
                "criteria": [
                    "Basic interaction present",
                    "Minimal feedback (correct/incorrect only)",
                    "Generic or weak narrative",
                    "Challenge may be unbalanced",
                    "Objectives present but not engaging"
                ]
            },
            2: {
                "label": "Limited",
                "criteria": [
                    "Few interaction points",
                    "Poor or missing feedback",
                    "Disconnected or absent narrative",
                    "Frustrating difficulty",
                    "Unclear what player should do"
                ]
            },
            1: {
                "label": "Non-functional",
                "criteria": [
                    "No meaningful interaction",
                    "No feedback mechanisms",
                    "No narrative coherence",
                    "Impossible or trivial",
                    "Would not function as a game"
                ]
            }
        }
    },

    "technical_quality": {
        "description": "Schema validity, completeness, and renderability of the blueprint",
        "weight": 0.25,  # 25% of total score
        "levels": {
            5: {
                "label": "Production Ready",
                "criteria": [
                    "All required schema fields present and valid",
                    "All IDs are unique and descriptive",
                    "Rich animation cues defined for all interactions",
                    "Optional fields populated where beneficial",
                    "Would render without modification"
                ]
            },
            4: {
                "label": "Minor Issues",
                "criteria": [
                    "All required fields present",
                    "Most IDs are descriptive",
                    "Basic animation cues defined",
                    "Some optional fields missing",
                    "Would render with minimal fixes"
                ]
            },
            3: {
                "label": "Needs Work",
                "criteria": [
                    "Required fields present but minimal",
                    "Generic IDs used (step_1, bucket_a)",
                    "Limited animation cues",
                    "Missing beneficial optional fields",
                    "Functional but bare-bones"
                ]
            },
            2: {
                "label": "Schema Errors",
                "criteria": [
                    "Some required fields missing",
                    "Invalid field values present",
                    "Broken references (e.g., bad correctBucketId)",
                    "Conflicting or duplicate IDs",
                    "Would not render without fixes"
                ]
            },
            1: {
                "label": "Invalid",
                "criteria": [
                    "Major schema violations",
                    "Wrong template type or structure",
                    "Cannot be parsed as valid JSON",
                    "Fundamentally broken references",
                    "Would crash the game engine"
                ]
            }
        }
    },

    "narrative_quality": {
        "description": "Story coherence, engagement, and support for learning",
        "weight": 0.15,  # 15% of total score
        "levels": {
            5: {
                "label": "Compelling",
                "criteria": [
                    "Engaging story that draws learner in",
                    "Strong visual metaphor for the concept",
                    "Memorable characters or scenarios",
                    "Narrative naturally reinforces learning",
                    "Appropriate for target audience"
                ]
            },
            4: {
                "label": "Good",
                "criteria": [
                    "Clear story context established",
                    "Functional visual metaphor",
                    "Story supports learning goals",
                    "Appropriate tone and style",
                    "Narrative flows logically"
                ]
            },
            3: {
                "label": "Basic",
                "criteria": [
                    "Simple narrative frame present",
                    "Basic context for the activity",
                    "Narrative is functional but generic",
                    "No strong connection to concept",
                    "Acceptable but forgettable"
                ]
            },
            2: {
                "label": "Weak",
                "criteria": [
                    "Minimal narrative attempt",
                    "Disconnected from learning content",
                    "Inappropriate tone or style",
                    "Confusing or illogical story",
                    "May distract from learning"
                ]
            },
            1: {
                "label": "None/Harmful",
                "criteria": [
                    "No narrative coherence",
                    "Story contradicts learning goals",
                    "Potentially offensive or inappropriate",
                    "Would confuse learners",
                    "Better to have no narrative"
                ]
            }
        }
    },

    "asset_quality": {
        "description": "Quality of visual prompts, animation cues, and multimedia specifications",
        "weight": 0.05,  # 5% of total score
        "levels": {
            5: {
                "label": "Rich",
                "criteria": [
                    "Detailed, specific asset prompts for AI generation",
                    "Animation cues for all interaction types",
                    "Sound/visual feedback specified",
                    "Consistent visual language throughout",
                    "Assets would enhance learning"
                ]
            },
            4: {
                "label": "Good",
                "criteria": [
                    "Clear asset prompts present",
                    "Most animations specified",
                    "Basic feedback mechanisms defined",
                    "Generally consistent visuals",
                    "Assets support the experience"
                ]
            },
            3: {
                "label": "Basic",
                "criteria": [
                    "Generic asset descriptions",
                    "Some animation cues present",
                    "Minimal feedback specification",
                    "Functional but unpolished",
                    "Assets are adequate"
                ]
            },
            2: {
                "label": "Minimal",
                "criteria": [
                    "Vague or missing asset prompts",
                    "Few animation cues",
                    "Unclear feedback expectations",
                    "Inconsistent visual design",
                    "Assets may not render well"
                ]
            },
            1: {
                "label": "Missing",
                "criteria": [
                    "No asset specifications",
                    "No animation cues",
                    "No feedback mechanisms",
                    "Would have no visual identity",
                    "Completely lacking polish"
                ]
            }
        }
    }
}


# =============================================================================
# AUTOMATED METRICS (non-LLM)
# =============================================================================

AUTOMATED_METRICS = {
    "task_completion": {
        "success_rate": "successful_runs / total_runs",
        "blueprint_validity": "valid_blueprints / total_blueprints",
        "first_pass_success": "first_pass_valid / total_runs",
        "retry_rate": "total_retries / total_runs"
    },
    "performance": {
        "latency_p50": "50th percentile execution time",
        "latency_p95": "95th percentile execution time",
        "tokens_per_run": "average tokens consumed per pipeline run",
        "cost_per_run": "estimated cost based on token usage and model prices"
    },
    "coordination": {
        "agent_agreement": "consistency between agent outputs (Cohen's kappa)",
        "context_efficiency": "useful_context_passed / total_context_size",
        "human_intervention_rate": "runs_requiring_human / total_runs"
    }
}


@dataclass
class TestCase:
    """A single test case for benchmarking"""
    id: str
    question_text: str
    question_options: Optional[List[str]] = None
    expected_template: Optional[str] = None
    blooms_level: Optional[str] = None
    subject: Optional[str] = None
    difficulty: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result of evaluating a single test case with a topology"""
    test_case_id: str
    topology_type: TopologyType
    success: bool
    quality_scores: Dict[str, float]
    total_tokens: int
    latency_ms: int
    iterations: int
    human_intervention: bool
    error_message: Optional[str] = None
    artifacts: Optional[Dict[str, Any]] = None


@dataclass
class BenchmarkReport:
    """Aggregate report for a benchmark run"""
    run_id: str
    timestamp: str
    test_cases: int
    topologies_tested: List[str]
    results: List[EvaluationResult]
    summary: Dict[str, Any] = field(default_factory=dict)


class LLMJudge:
    """
    LLM-based quality judge for generated artifacts.

    Uses the QUALITY_RUBRIC to provide consistent, detailed evaluations
    of game blueprints across multiple quality dimensions.
    """

    JUDGE_PROMPT = """You are an expert evaluator for educational game content. Your role is to assess the quality of generated game blueprints using a standardized rubric.

## Artifact to Evaluate:
```json
{artifact}
```

## Original Question:
{question}

## Template Type: {template_type}

## Pedagogical Context:
- Bloom's Level: {blooms_level}
- Subject: {subject}

## EVALUATION RUBRIC

Evaluate each dimension on a 1-5 scale:

### 1. Pedagogical Alignment (Weight: 30%)
{pedagogical_rubric}

### 2. Game Engagement (Weight: 25%)
{engagement_rubric}

### 3. Technical Quality (Weight: 25%)
{technical_rubric}

### 4. Narrative Quality (Weight: 15%)
{narrative_rubric}

### 5. Asset Quality (Weight: 5%)
{asset_rubric}

## RESPONSE FORMAT (JSON only):
{{
    "scores": {{
        "pedagogical_alignment": {{
            "score": <1-5>,
            "level": "<Excellent/Good/Acceptable/Poor/Unacceptable>",
            "reasoning": "<specific evidence from artifact>",
            "suggestions": ["<improvement 1>", "<improvement 2>"]
        }},
        "game_engagement": {{
            "score": <1-5>,
            "level": "<label>",
            "reasoning": "<evidence>",
            "suggestions": []
        }},
        "technical_quality": {{
            "score": <1-5>,
            "level": "<label>",
            "reasoning": "<evidence>",
            "suggestions": []
        }},
        "narrative_quality": {{
            "score": <1-5>,
            "level": "<label>",
            "reasoning": "<evidence>",
            "suggestions": []
        }},
        "asset_quality": {{
            "score": <1-5>,
            "level": "<label>",
            "reasoning": "<evidence>",
            "suggestions": []
        }}
    }},
    "weighted_total": <0.0-1.0>,
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "critical_issues": ["<issue 1>", "<issue 2>"],
    "would_deploy": <true/false>,
    "deployment_blockers": ["<blocker if any>"]
}}

Respond with ONLY the JSON, no additional text."""

    def __init__(self, llm_service: Any):
        self.llm_service = llm_service

    def _format_rubric_level(self, dimension: str) -> str:
        """Format rubric criteria for a dimension into prompt text"""
        rubric = QUALITY_RUBRIC.get(dimension, {})
        levels = rubric.get("levels", {})

        lines = []
        for score in sorted(levels.keys(), reverse=True):
            level_info = levels[score]
            criteria = "\n   - ".join(level_info["criteria"])
            lines.append(f"**{score} ({level_info['label']}):**\n   - {criteria}")

        return "\n".join(lines)

    async def evaluate(
        self,
        artifact: Dict[str, Any],
        question: str,
        template_type: str,
        blooms_level: str = "unknown",
        subject: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Evaluate an artifact and return detailed quality scores.

        Args:
            artifact: The blueprint or game artifact to evaluate
            question: The original question/prompt
            template_type: Expected template type
            blooms_level: Target Bloom's taxonomy level
            subject: Subject area

        Returns:
            Dict with scores, reasoning, and deployment recommendation
        """
        # Build the comprehensive prompt with rubric details
        prompt = self.JUDGE_PROMPT.format(
            artifact=json.dumps(artifact, indent=2)[:6000],  # Increased limit
            question=question,
            template_type=template_type,
            blooms_level=blooms_level,
            subject=subject,
            pedagogical_rubric=self._format_rubric_level("pedagogical_alignment"),
            engagement_rubric=self._format_rubric_level("game_engagement"),
            technical_rubric=self._format_rubric_level("technical_quality"),
            narrative_rubric=self._format_rubric_level("narrative_quality"),
            asset_rubric=self._format_rubric_level("asset_quality")
        )

        try:
            # Use agent-specific generation if available
            if hasattr(self.llm_service, 'generate_for_agent'):
                response = await self.llm_service.generate_for_agent(
                    agent_name="judge",
                    prompt=prompt
                )
                response_text = response.content
            else:
                response = await self.llm_service.generate(prompt)
                response_text = response if isinstance(response, str) else response.content

            # Parse JSON response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                result = json.loads(response_text[start:end])

                # Extract scores and normalize to 0-1 scale
                scores = result.get("scores", {})

                return {
                    "pedagogical": scores.get("pedagogical_alignment", {}).get("score", 3) / 5,
                    "engagement": scores.get("game_engagement", {}).get("score", 3) / 5,
                    "technical": scores.get("technical_quality", {}).get("score", 3) / 5,
                    "narrative": scores.get("narrative_quality", {}).get("score", 3) / 5,
                    "asset": scores.get("asset_quality", {}).get("score", 3) / 5,
                    "overall": result.get("weighted_total", 0.5),
                    "would_deploy": result.get("would_deploy", False),
                    "strengths": result.get("strengths", []),
                    "critical_issues": result.get("critical_issues", []),
                    "deployment_blockers": result.get("deployment_blockers", []),
                    "detailed_scores": scores  # Keep full detail for analysis
                }

        except Exception as e:
            logger.warning(f"LLM Judge evaluation failed: {e}")

        # Default scores on failure
        return {
            "pedagogical": 0.5,
            "engagement": 0.5,
            "technical": 0.5,
            "narrative": 0.5,
            "asset": 0.5,
            "overall": 0.5,
            "would_deploy": False,
            "strengths": [],
            "critical_issues": ["Evaluation failed"],
            "deployment_blockers": ["Could not evaluate"],
            "detailed_scores": {}
        }

    async def evaluate_batch(
        self,
        artifacts: List[Dict[str, Any]],
        questions: List[str],
        template_types: List[str]
    ) -> List[Dict[str, Any]]:
        """Evaluate multiple artifacts (for benchmarking)"""
        results = []
        for artifact, question, template in zip(artifacts, questions, template_types):
            result = await self.evaluate(artifact, question, template)
            results.append(result)
        return results

    def compute_weighted_score(self, scores: Dict[str, float]) -> float:
        """Compute weighted total from individual dimension scores"""
        weighted = 0.0
        for dim, info in QUALITY_RUBRIC.items():
            dim_key = dim.replace("_alignment", "").replace("_quality", "")
            if dim_key in scores:
                weighted += scores[dim_key] * info["weight"]
        return weighted


def calculate_automated_metrics(results: List[EvaluationResult]) -> Dict[str, Any]:
    """
    Calculate automated metrics from evaluation results.

    Args:
        results: List of evaluation results from benchmark runs

    Returns:
        Dict with task_completion, performance, and coordination metrics
    """
    if not results:
        return {}

    total = len(results)
    successful = [r for r in results if r.success]

    # Task completion metrics
    success_rate = len(successful) / total if total > 0 else 0
    first_pass = [r for r in successful if r.iterations == 0]
    first_pass_rate = len(first_pass) / total if total > 0 else 0

    total_retries = sum(r.iterations for r in results)
    retry_rate = total_retries / total if total > 0 else 0

    # Performance metrics
    latencies = [r.latency_ms for r in successful]
    latencies.sort()

    p50_latency = latencies[len(latencies) // 2] if latencies else 0
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_idx] if latencies and p95_idx < len(latencies) else 0

    avg_tokens = sum(r.total_tokens for r in successful) / len(successful) if successful else 0

    # Coordination metrics
    human_intervention = [r for r in results if r.human_intervention]
    human_rate = len(human_intervention) / total if total > 0 else 0

    return {
        "task_completion": {
            "success_rate": success_rate,
            "first_pass_success_rate": first_pass_rate,
            "retry_rate": retry_rate,
            "total_runs": total,
            "successful_runs": len(successful)
        },
        "performance": {
            "latency_p50_ms": p50_latency,
            "latency_p95_ms": p95_latency,
            "avg_tokens_per_run": avg_tokens,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0
        },
        "coordination": {
            "human_intervention_rate": human_rate,
            "human_interventions": len(human_intervention)
        }
    }


class TopologyBenchmark:
    """Benchmark runner for comparing topologies"""

    def __init__(
        self,
        llm_service: Any = None,
        output_dir: Optional[Path] = None
    ):
        self.llm_service = llm_service
        self.judge = LLMJudge(llm_service) if llm_service else None
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(exist_ok=True)

    async def run_single_test(
        self,
        test_case: TestCase,
        topology_type: TopologyType,
        config: Optional[TopologyConfig] = None
    ) -> EvaluationResult:
        """Run a single test case with a topology"""
        logger.info(f"Running test {test_case.id} with {topology_type.value}")

        start_time = time.time()
        tokens_used = 0
        iterations = 0

        try:
            # Create topology and initial state
            graph = create_topology(topology_type, config)
            compiled = graph.compile()

            initial_state = create_initial_state(
                question_id=test_case.id,
                question_text=test_case.question_text,
                question_options=test_case.question_options
            )

            # Run the graph
            final_state = await compiled.ainvoke(initial_state)

            # Calculate metrics
            latency_ms = int((time.time() - start_time) * 1000)

            # Count iterations from retry counts
            retry_counts = final_state.get("retry_counts", {})
            iterations = sum(retry_counts.values())

            # Check success
            success = final_state.get("generation_complete", False)
            error_message = final_state.get("error_message")

            # Get quality scores
            quality_scores = {}
            if success and self.judge:
                blueprint = final_state.get("blueprint")
                if blueprint:
                    quality_scores = await self.judge.evaluate(
                        blueprint,
                        test_case.question_text,
                        final_state.get("template_selection", {}).get("template_type", "")
                    )

            # Check for human intervention
            human_intervention = final_state.get("pending_human_review") is not None

            return EvaluationResult(
                test_case_id=test_case.id,
                topology_type=topology_type,
                success=success,
                quality_scores=quality_scores,
                total_tokens=tokens_used,  # TODO: Track actual tokens
                latency_ms=latency_ms,
                iterations=iterations,
                human_intervention=human_intervention,
                error_message=error_message,
                artifacts={
                    "blueprint": final_state.get("blueprint"),
                    "template_type": final_state.get("template_selection", {}).get("template_type")
                }
            )

        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            return EvaluationResult(
                test_case_id=test_case.id,
                topology_type=topology_type,
                success=False,
                quality_scores={},
                total_tokens=0,
                latency_ms=int((time.time() - start_time) * 1000),
                iterations=iterations,
                human_intervention=False,
                error_message=str(e)
            )

    async def run_benchmark(
        self,
        test_cases: List[TestCase],
        topologies: List[TopologyType],
        configs: Optional[Dict[TopologyType, TopologyConfig]] = None
    ) -> BenchmarkReport:
        """Run full benchmark across test cases and topologies"""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Starting benchmark run {run_id}")
        logger.info(f"Test cases: {len(test_cases)}, Topologies: {len(topologies)}")

        results = []

        for topology in topologies:
            config = configs.get(topology) if configs else None

            for test_case in test_cases:
                result = await self.run_single_test(test_case, topology, config)
                results.append(result)

                # Log progress
                logger.info(
                    f"[{topology.value}] {test_case.id}: "
                    f"{'SUCCESS' if result.success else 'FAILED'} "
                    f"({result.latency_ms}ms, {result.iterations} iterations)"
                )

        # Generate summary
        summary = self._generate_summary(results, topologies)

        report = BenchmarkReport(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            test_cases=len(test_cases),
            topologies_tested=[t.value for t in topologies],
            results=results,
            summary=summary
        )

        # Save report
        self._save_report(report)

        return report

    def _generate_summary(
        self,
        results: List[EvaluationResult],
        topologies: List[TopologyType]
    ) -> Dict[str, Any]:
        """Generate summary statistics for the benchmark"""
        summary = {}

        for topology in topologies:
            topology_results = [r for r in results if r.topology_type == topology]

            if not topology_results:
                continue

            success_count = sum(1 for r in topology_results if r.success)
            total_count = len(topology_results)

            # Calculate averages
            successful_results = [r for r in topology_results if r.success]

            avg_latency = (
                sum(r.latency_ms for r in successful_results) / len(successful_results)
                if successful_results else 0
            )

            avg_iterations = (
                sum(r.iterations for r in successful_results) / len(successful_results)
                if successful_results else 0
            )

            avg_quality = {}
            if successful_results:
                quality_keys = set()
                for r in successful_results:
                    quality_keys.update(r.quality_scores.keys())

                for key in quality_keys:
                    scores = [r.quality_scores.get(key, 0) for r in successful_results if key in r.quality_scores]
                    avg_quality[key] = sum(scores) / len(scores) if scores else 0

            human_intervention_rate = (
                sum(1 for r in topology_results if r.human_intervention) / total_count
            )

            summary[topology.value] = {
                "success_rate": success_count / total_count,
                "avg_latency_ms": avg_latency,
                "avg_iterations": avg_iterations,
                "avg_quality_scores": avg_quality,
                "human_intervention_rate": human_intervention_rate,
                "total_tests": total_count,
                "successful_tests": success_count
            }

        # Add comparison rankings
        if len(topologies) > 1:
            summary["rankings"] = {
                "by_success_rate": sorted(
                    summary.keys(),
                    key=lambda t: summary[t].get("success_rate", 0) if t != "rankings" else 0,
                    reverse=True
                ),
                "by_quality": sorted(
                    [t for t in summary.keys() if t != "rankings"],
                    key=lambda t: summary[t].get("avg_quality_scores", {}).get("overall", 0),
                    reverse=True
                ),
                "by_latency": sorted(
                    [t for t in summary.keys() if t != "rankings"],
                    key=lambda t: summary[t].get("avg_latency_ms", float("inf"))
                )
            }

        return summary

    def _save_report(self, report: BenchmarkReport):
        """Save benchmark report to file"""
        report_file = self.output_dir / f"benchmark_{report.run_id}.json"

        # Convert to serializable format
        report_dict = {
            "run_id": report.run_id,
            "timestamp": report.timestamp,
            "test_cases": report.test_cases,
            "topologies_tested": report.topologies_tested,
            "results": [
                {
                    "test_case_id": r.test_case_id,
                    "topology_type": r.topology_type.value,
                    "success": r.success,
                    "quality_scores": r.quality_scores,
                    "total_tokens": r.total_tokens,
                    "latency_ms": r.latency_ms,
                    "iterations": r.iterations,
                    "human_intervention": r.human_intervention,
                    "error_message": r.error_message
                }
                for r in report.results
            ],
            "summary": report.summary
        }

        with open(report_file, "w") as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Benchmark report saved to {report_file}")


# =============================================================================
# SAMPLE TEST CASES
# =============================================================================

SAMPLE_TEST_CASES = [
    TestCase(
        id="algo_binary_search",
        question_text="Explain the time complexity of binary search and demonstrate how it works on a sorted array.",
        expected_template="PARAMETER_PLAYGROUND",
        blooms_level="understand",
        subject="Computer Science",
        difficulty="intermediate",
        tags=["algorithm", "search", "complexity"]
    ),
    TestCase(
        id="bio_cell_structure",
        question_text="Label the main parts of an animal cell including the nucleus, mitochondria, and cell membrane.",
        expected_template="INTERACTIVE_DIAGRAM",
        blooms_level="remember",
        subject="Biology",
        difficulty="beginner",
        tags=["biology", "cell", "labeling"]
    ),
    TestCase(
        id="history_timeline",
        question_text="Arrange the following events of the American Revolution in chronological order: Boston Tea Party, Declaration of Independence, Battle of Yorktown, First Continental Congress.",
        question_options=["Boston Tea Party", "Declaration of Independence", "Battle of Yorktown", "First Continental Congress"],
        expected_template="TIMELINE_ORDER",
        blooms_level="understand",
        subject="History",
        difficulty="intermediate",
        tags=["history", "timeline", "sequence"]
    ),
    TestCase(
        id="math_sorting",
        question_text="Demonstrate the bubble sort algorithm step by step on the array [5, 2, 8, 1, 9].",
        expected_template="STATE_TRACER_CODE",
        blooms_level="apply",
        subject="Computer Science",
        difficulty="intermediate",
        tags=["algorithm", "sorting", "visualization"]
    ),
    TestCase(
        id="chem_categorize",
        question_text="Categorize the following elements into metals, non-metals, and metalloids: Iron, Carbon, Silicon, Gold, Oxygen, Arsenic.",
        question_options=["Iron", "Carbon", "Silicon", "Gold", "Oxygen", "Arsenic"],
        expected_template="BUCKET_SORT",
        blooms_level="apply",
        subject="Chemistry",
        difficulty="beginner",
        tags=["chemistry", "elements", "categorization"]
    ),
]


async def run_quick_benchmark():
    """Run a quick benchmark with sample test cases"""
    benchmark = TopologyBenchmark()

    topologies = [
        TopologyType.T0_SEQUENTIAL,
        TopologyType.T1_SEQUENTIAL_VALIDATED,
    ]

    report = await benchmark.run_benchmark(
        test_cases=SAMPLE_TEST_CASES[:2],  # Quick test with 2 cases
        topologies=topologies
    )

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    for topology, stats in report.summary.items():
        if topology == "rankings":
            continue
        print(f"\n{topology}:")
        print(f"  Success Rate: {stats['success_rate']:.1%}")
        print(f"  Avg Latency: {stats['avg_latency_ms']:.0f}ms")
        print(f"  Avg Iterations: {stats['avg_iterations']:.1f}")
        if stats.get('avg_quality_scores'):
            print(f"  Avg Quality: {stats['avg_quality_scores'].get('overall', 0):.2f}")

    return report
