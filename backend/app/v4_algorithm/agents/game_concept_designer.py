"""Algorithm Game Concept Designer — LLM-powered multi-scene game concept.

Designs a multi-scene game with appropriate game types based on the algorithm,
domain knowledge, and Bloom's taxonomy progression.
"""

import json
from typing import Any

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.v4_algorithm.contracts import SUPPORTED_GAME_TYPES, build_capability_spec

logger = get_logger("gamed_ai.v4_algorithm.agents.game_concept_designer")


def _build_concept_prompt(
    question_text: str,
    dk: dict,
    validation_feedback: str = "",
) -> str:
    """Build the LLM prompt for game concept design."""
    algorithm_name = dk.get("algorithm_name", "Unknown")
    category = dk.get("algorithm_category", "")
    complexity = dk.get("time_complexity", {})
    ds_used = dk.get("data_structures_used", [])
    bugs = dk.get("common_bugs", [])
    capabilities = build_capability_spec()

    retry_section = ""
    if validation_feedback:
        retry_section = f"""
## PREVIOUS ATTEMPT FAILED — FIX THESE ISSUES:
{validation_feedback}
"""

    return f"""You are an expert educational game designer specializing in algorithm pedagogy.

## Task
Design an interactive multi-scene game that teaches the algorithm through progressive challenges.

## Question: {question_text}
## Algorithm: {algorithm_name}
## Category: {category}
## Time Complexity: {json.dumps(complexity)}
## Data Structures Used: {json.dumps(ds_used)}
## Known Common Bugs: {len(bugs)} bugs available
{retry_section}
## Available Game Types:
{json.dumps(capabilities, indent=2)}

- **state_tracer**: Students predict algorithm execution step by step (data structure state, variable values, next operations). Best for: understanding HOW an algorithm works.
- **bug_hunter**: Students find and fix bugs in algorithm implementations. Best for: debugging skills, understanding common mistakes.
- **algorithm_builder**: Parsons problems — drag code blocks into correct order. Best for: learning algorithm STRUCTURE.
- **complexity_analyzer**: Students analyze time/space complexity from code or growth data. Best for: understanding WHY an algorithm is efficient.
- **constraint_puzzle**: Optimization puzzles that mirror algorithm problems (knapsack, scheduling). Best for: understanding the PROBLEM the algorithm solves.

## Design Guidelines
1. Use 2-4 scenes with DIFFERENT game types for variety
2. Follow Bloom's taxonomy progression: Remember → Understand → Apply → Analyze → Create
3. Match game types to the algorithm's strengths:
   - Sorting algorithms → state_tracer (see swaps) + bug_hunter (off-by-one errors) + complexity_analyzer
   - Graph algorithms → state_tracer (BFS/DFS traversal) + algorithm_builder + complexity_analyzer
   - DP algorithms → state_tracer (table filling) + constraint_puzzle (optimization problem)
   - Greedy → constraint_puzzle + complexity_analyzer + bug_hunter
4. Difficulty should progress: beginner → intermediate → advanced

Return JSON:
{{
    "title": "<catchy game title>",
    "algorithm_name": "{algorithm_name}",
    "algorithm_category": "{category}",
    "narrative_theme": "<theme tying scenes together>",
    "narrative_intro": "<1-2 sentence hook for the student>",
    "scenes": [
        {{
            "title": "<scene title>",
            "learning_goal": "<what student learns>",
            "narrative_intro": "<scene-level intro text>",
            "game_type": "<one of: state_tracer, bug_hunter, algorithm_builder, complexity_analyzer, constraint_puzzle>",
            "difficulty": "<beginner|intermediate|advanced>",
            "needs_visualization": <true|false>,
            "visualization_description": "<what the image should show, or empty>",
            "visualization_type": "<data_structure|flowchart|comparison_chart|board_layout|none>",
            "config_hints": {{
                // state_tracer hints:
                //   "data_structure" MUST be one of: array, graph, tree, dp_table, stack, linked_list, heap, hash_map, custom
                //   "prediction_type": value, arrangement, multiple_choice, multi_select
                //   "num_steps": integer (6-12)
                // bug_hunter hints:
                //   "num_rounds": integer (2-5)
                //   "fix_mode" MUST be one of: multiple_choice, free_text
                // algorithm_builder hints:
                //   "num_blocks": integer (6-15)
                //   "include_distractors": boolean
                // complexity_analyzer hints:
                //   "num_challenges": integer (2-5)
                //   "complexity_dimension" MUST be one of: time, space, both
                // constraint_puzzle hints:
                //   "puzzle_type": string (descriptive)
                //   "board_type" MUST be one of: item_selection, grid_placement, multiset_building, graph_interaction, value_assignment, sequence_building
            }}
        }}
    ],
    "difficulty_progression": "<flat|ascending|mixed>",
    "estimated_duration_minutes": <10-30>
}}
"""


async def algo_game_concept_designer(state: dict) -> dict:
    """Design a multi-scene algorithm game concept.

    Reads: question_text, domain_knowledge, pedagogical_context, concept_validation (on retry)
    Writes: game_concept, concept_retry_count
    """
    question_text = state.get("question_text", "")
    dk = state.get("domain_knowledge") or {}
    retry_count = state.get("concept_retry_count", 0)
    validation = state.get("concept_validation") or {}

    algorithm_name = dk.get("algorithm_name", "Unknown Algorithm")

    # Build retry feedback if this is a retry
    validation_feedback = ""
    if retry_count > 0 and not validation.get("passed", True):
        issues = validation.get("issues", [])
        validation_feedback = "\n".join(
            f"- [{i.get('severity', 'error')}] {i.get('message', '')}"
            for i in issues
        )

    logger.info(
        f"Game concept designer: algorithm='{algorithm_name}', "
        f"retry={retry_count}"
    )

    prompt = _build_concept_prompt(question_text, dk, validation_feedback)

    try:
        llm = get_llm_service()
        concept = await llm.generate_json_for_agent(
            agent_name="v4a_game_concept_designer",
            prompt=prompt,
            schema_hint="AlgorithmGameConcept with scenes array",
        )

        if isinstance(concept, dict):
            concept.pop("_llm_metrics", None)
        else:
            concept = None

    except Exception as e:
        logger.error(f"Game concept designer failed: {e}")
        concept = None

    if not concept:
        concept = _fallback_concept(algorithm_name, dk)

    # Validate game types
    scenes = concept.get("scenes", [])
    for scene in scenes:
        gt = scene.get("game_type", "")
        if gt not in SUPPORTED_GAME_TYPES:
            logger.warning(f"Fixing invalid game_type '{gt}' → 'state_tracer'")
            scene["game_type"] = "state_tracer"

    logger.info(
        f"Concept designed: '{concept.get('title')}', "
        f"{len(scenes)} scenes: {[s.get('game_type') for s in scenes]}"
    )

    return {
        "game_concept": concept,
        "concept_retry_count": retry_count + 1,
    }


def _fallback_concept(algorithm_name: str, dk: dict) -> dict:
    """Generate a reasonable fallback concept when LLM fails."""
    return {
        "title": f"Master {algorithm_name}",
        "algorithm_name": algorithm_name,
        "algorithm_category": dk.get("algorithm_category", ""),
        "narrative_theme": f"Interactive {algorithm_name} challenge",
        "narrative_intro": f"Learn how {algorithm_name} works through interactive challenges.",
        "scenes": [
            {
                "title": f"Trace {algorithm_name}",
                "learning_goal": f"Understand step-by-step execution of {algorithm_name}",
                "narrative_intro": f"Predict what happens at each step of {algorithm_name}.",
                "game_type": "state_tracer",
                "difficulty": "beginner",
                "needs_visualization": True,
                "visualization_description": f"{algorithm_name} data structure visualization",
                "visualization_type": "data_structure",
                "config_hints": {"data_structure": "array", "prediction_type": "value", "num_steps": 8},
            },
            {
                "title": f"Debug {algorithm_name}",
                "learning_goal": f"Identify common bugs in {algorithm_name}",
                "narrative_intro": f"Find and fix bugs in this {algorithm_name} implementation.",
                "game_type": "bug_hunter",
                "difficulty": "intermediate",
                "needs_visualization": False,
                "visualization_description": "",
                "visualization_type": "none",
                "config_hints": {"num_rounds": 3, "fix_mode": "multiple_choice"},
            },
        ],
        "difficulty_progression": "ascending",
        "estimated_duration_minutes": 15,
    }
