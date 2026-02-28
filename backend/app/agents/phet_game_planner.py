"""
PhET Game Planner Agent

Designs the assessment strategy and game mechanics for a PhET simulation.
Dynamically selects assessment type based on Bloom's level and question patterns.
"""

import json
from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.agents.schemas.phet_simulation import (
    SIMULATION_CATALOG,
    ASSESSMENT_TYPE_RULES,
    QUESTION_PATTERN_RULES,
    select_assessment_type,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.phet_game_planner")


PHET_GAME_PLANNER_PROMPT = """You are an expert instructional designer creating an assessment for a PhET simulation.

## Learning Context:
Question: {question_text}
Subject: {subject}
Bloom's Level: {blooms_level}
Key Concepts: {key_concepts}
Difficulty: {difficulty}

## Selected Simulation:
Simulation: {simulation_title} ({simulation_id})
Recommended Screen: {recommended_screen}

Available Parameters (what students can adjust):
{parameters}

Available Outcomes (what can be measured):
{outcomes}

Available Interactions (what students can do):
{interactions}

Supported Assessment Types: {assessment_types}

## Assessment Type Guidelines:

### EXPLORATION
- Open-ended discovery with guided prompts
- Reward trying different parameter values
- Checkpoints for breadth of exploration
- Best for: Introduction to concepts, remember/understand levels

### PARAMETER_DISCOVERY
- Find relationships between parameters
- "What happens when X changes?"
- Checkpoints for discovering specific relationships
- Best for: Understanding cause-effect, analyze level

### TARGET_ACHIEVEMENT
- Achieve specific outcomes
- "Make the projectile land at 50 meters"
- Checkpoints for hitting targets
- Best for: Apply level, goal-oriented tasks

### PREDICTION_VERIFICATION
- Predict → Test → Verify cycle
- "Predict what will happen, then test it"
- Checkpoints for making predictions AND verifying
- Best for: Scientific method, analyze/evaluate levels

### OPTIMIZATION
- Find optimal values
- "Find the angle that maximizes range"
- Checkpoints for approaching optimal
- Best for: Problem solving, evaluate level

### MEASUREMENT
- Take measurements and record data
- "Measure the period for 3 different lengths"
- Checkpoints for completing measurements
- Best for: Data collection, apply level

### COMPARATIVE_ANALYSIS
- Compare configurations
- "Compare series vs parallel circuits"
- Checkpoints for trying both configurations
- Best for: Understanding differences, analyze level

### CONSTRUCTION
- Build something
- "Build a circuit with 2 bulbs in series"
- Checkpoints for assembly steps
- Best for: Create level, hands-on building

### SEQUENCE_EXECUTION
- Follow a procedure in order
- "First do X, then Y, then Z"
- Checkpoints for completing steps in sequence
- Best for: Procedural knowledge

## Your Task:
Design an effective assessment that uses this simulation to help students learn the target concepts.
Consider the Bloom's level to choose appropriate assessment type and task complexity.

## Response (JSON only):
{{
    "assessmentType": "<primary_assessment_type>",
    "assessmentTypeReasoning": "<1-2 sentences explaining why this type fits>",
    "learningObjectives": ["<objective1>", "<objective2>", "<objective3>"],
    "taskSequence": [
        {{
            "type": "<task_type>",
            "title": "<short_task_title>",
            "description": "<what_student_does>",
            "checkpointIdeas": ["<what_to_check_1>", "<what_to_check_2>"],
            "estimatedMinutes": <minutes>,
            "bloomsLevel": "<bloom_level_for_task>"
        }}
    ],
    "scoringStrategy": {{
        "maxScore": <total_points_50-150>,
        "explorationWeight": <0-1>,
        "accuracyWeight": <0-1>,
        "efficiencyWeight": <0-1>
    }},
    "difficultyProgression": "<how_difficulty_increases_across_tasks>",
    "feedbackStrategy": "<when_and_how_to_give_feedback>",
    "keyParametersToTrack": ["<param_name_1>", "<param_name_2>"],
    "keyOutcomesToMeasure": ["<outcome_name_1>", "<outcome_name_2>"],
    "commonMisconceptions": ["<misconception1>", "<misconception2>"],
    "hintsStrategy": "<progressive_hint_approach>",
    "estimatedTotalMinutes": <total_minutes>
}}

Respond with ONLY valid JSON."""


def _format_parameters(parameters: List[Dict]) -> str:
    """Format parameters for prompt."""
    if not parameters:
        return "No adjustable parameters"

    lines = []
    for p in parameters:
        parts = [f"- {p['name']}"]
        if p.get('type'):
            parts.append(f"({p['type']})")
        if p.get('unit'):
            parts.append(f"[{p['unit']}]")
        if p.get('min') is not None and p.get('max') is not None:
            parts.append(f"range: {p['min']}-{p['max']}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _format_outcomes(outcomes: List[Dict]) -> str:
    """Format outcomes for prompt."""
    if not outcomes:
        return "No measurable outcomes"

    lines = []
    for o in outcomes:
        parts = [f"- {o['name']}"]
        if o.get('unit'):
            parts.append(f"[{o['unit']}]")
        if o.get('description'):
            parts.append(f": {o['description']}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _format_interactions(interactions: List[Dict]) -> str:
    """Format interactions for prompt."""
    if not interactions:
        return "Standard simulation interactions"

    lines = []
    for i in interactions:
        parts = [f"- {i['name']} ({i['type']})"]
        if i.get('dataFields'):
            parts.append(f"captures: {', '.join(i['dataFields'])}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _get_fallback_game_plan(
    phet_selection: Dict[str, Any],
    ped_context: Dict[str, Any],
    question_text: str
) -> Dict[str, Any]:
    """Create fallback game plan when LLM fails."""
    sim_metadata = phet_selection.get("simulationMetadata", {})
    sim_types = sim_metadata.get("assessmentTypes", ["exploration"])
    blooms_level = ped_context.get("blooms_level", "understand")

    # Select assessment type
    assessment_type = select_assessment_type(blooms_level, question_text, sim_types)

    # Get key parameters and outcomes
    params = sim_metadata.get("parameters", [])
    outcomes = sim_metadata.get("outcomes", [])

    return {
        "assessmentType": assessment_type,
        "assessmentTypeReasoning": f"Selected based on Bloom's level ({blooms_level}) and question pattern",
        "learningObjectives": [
            f"Understand the relationship between simulation parameters",
            f"Apply knowledge to achieve specific outcomes",
            f"Analyze results and draw conclusions"
        ],
        "taskSequence": [
            {
                "type": "exploration",
                "title": "Explore the Simulation",
                "description": "Familiarize yourself with the simulation controls and observe basic behaviors",
                "checkpointIdeas": ["Try at least 3 different parameter values", "Observe the outcomes"],
                "estimatedMinutes": 3,
                "bloomsLevel": "understand"
            },
            {
                "type": assessment_type,
                "title": "Complete the Challenge",
                "description": "Use what you learned to complete the main assessment task",
                "checkpointIdeas": ["Achieve the target outcome", "Demonstrate understanding"],
                "estimatedMinutes": 5,
                "bloomsLevel": blooms_level
            }
        ],
        "scoringStrategy": {
            "maxScore": 100,
            "explorationWeight": 0.3,
            "accuracyWeight": 0.5,
            "efficiencyWeight": 0.2
        },
        "difficultyProgression": "Starts with exploration, builds to targeted application",
        "feedbackStrategy": "Immediate feedback on checkpoint completion",
        "keyParametersToTrack": [p["name"] for p in params[:3]],
        "keyOutcomesToMeasure": [o["name"] for o in outcomes[:3]],
        "commonMisconceptions": [],
        "hintsStrategy": "Progressive hints after 2 minutes without progress",
        "estimatedTotalMinutes": 10
    }


async def phet_game_planner_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> Dict[str, Any]:
    """
    Design game mechanics and assessment strategy.

    Args:
        state: Current agent state with phet_selection and pedagogical_context
        ctx: Optional instrumentation context

    Returns:
        Updated state with phet_game_plan
    """
    logger.info("PhET Game Planner: Designing assessment strategy")

    phet_selection = state.get("phet_selection", {})
    ped_context = state.get("pedagogical_context", {})
    question_text = state.get("question_text", "")

    if not phet_selection.get("simulationId"):
        logger.error("PhET Game Planner: No simulation selected")
        return {
            **state,
            "current_agent": "phet_game_planner",
            "error_message": "No simulation selected for game planning"
        }

    sim_metadata = phet_selection.get("simulationMetadata", {})
    sim_id = phet_selection.get("simulationId")

    # If metadata not in selection, get from catalog
    if not sim_metadata and sim_id in SIMULATION_CATALOG:
        sim_metadata = SIMULATION_CATALOG[sim_id]
        phet_selection["simulationMetadata"] = sim_metadata

    prompt = PHET_GAME_PLANNER_PROMPT.format(
        question_text=question_text,
        subject=ped_context.get("subject", "Science"),
        blooms_level=ped_context.get("blooms_level", "understand"),
        key_concepts=", ".join(ped_context.get("key_concepts", [])),
        difficulty=ped_context.get("difficulty", "medium"),
        simulation_title=sim_metadata.get("title", sim_id),
        simulation_id=sim_id,
        recommended_screen=phet_selection.get("recommendedScreen", "default"),
        parameters=_format_parameters(sim_metadata.get("parameters", [])),
        outcomes=_format_outcomes(sim_metadata.get("outcomes", [])),
        interactions=_format_interactions(sim_metadata.get("interactions", [])),
        assessment_types=", ".join(sim_metadata.get("assessmentTypes", ["exploration"]))
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json_for_agent(
            agent_name="phet_game_planner",
            prompt=prompt,
            schema_hint="Game plan with assessmentType, learningObjectives, taskSequence"
        )

        # Validate assessment type
        valid_types = sim_metadata.get("assessmentTypes", ["exploration"])
        if result.get("assessmentType") not in valid_types:
            logger.warning(
                f"PhET Game Planner: Invalid assessment type {result.get('assessmentType')}, "
                f"falling back to {valid_types[0]}"
            )
            result["assessmentType"] = select_assessment_type(
                ped_context.get("blooms_level", "understand"),
                question_text,
                valid_types
            )

        # Ensure required fields
        if not result.get("taskSequence"):
            result["taskSequence"] = [
                {
                    "type": result.get("assessmentType", "exploration"),
                    "title": "Main Task",
                    "description": "Complete the assessment task",
                    "checkpointIdeas": ["Complete the objective"],
                    "estimatedMinutes": 5,
                    "bloomsLevel": ped_context.get("blooms_level", "understand")
                }
            ]

        if not result.get("scoringStrategy"):
            result["scoringStrategy"] = {
                "maxScore": 100,
                "explorationWeight": 0.3,
                "accuracyWeight": 0.5,
                "efficiencyWeight": 0.2
            }

        logger.info(
            f"PhET Game Planner: Designed {result['assessmentType']} assessment "
            f"with {len(result['taskSequence'])} tasks"
        )

        if ctx:
            ctx.complete({
                "phet_game_plan": result,
                "current_agent": "phet_game_planner"
            })

        return {
            **state,
            "phet_game_plan": result,
            "current_agent": "phet_game_planner"
        }

    except Exception as e:
        logger.error(f"PhET Game Planner: LLM call failed: {e}", exc_info=True)

        # Use fallback
        fallback = _get_fallback_game_plan(phet_selection, ped_context, question_text)

        return {
            **state,
            "phet_game_plan": fallback,
            "current_agent": "phet_game_planner",
            "error_message": f"PhET Game Planner fallback: {str(e)}"
        }


def suggest_assessment_type(
    blooms_level: str,
    question_text: str,
    available_types: List[str]
) -> Dict[str, Any]:
    """
    Suggest assessment type with reasoning.

    Args:
        blooms_level: Target Bloom's level
        question_text: The question text
        available_types: Assessment types supported by simulation

    Returns:
        Dict with suggested type and reasoning
    """
    question_lower = question_text.lower()

    # Check question patterns first
    for pattern, types in QUESTION_PATTERN_RULES.items():
        if pattern in question_lower:
            for t in types:
                if t in available_types:
                    return {
                        "type": t,
                        "reasoning": f"Question pattern '{pattern}' suggests {t} assessment",
                        "confidence": 0.8
                    }

    # Fall back to Bloom's level
    blooms_types = ASSESSMENT_TYPE_RULES.get(blooms_level, ["exploration"])
    for t in blooms_types:
        if t in available_types:
            return {
                "type": t,
                "reasoning": f"Bloom's level '{blooms_level}' aligns with {t} assessment",
                "confidence": 0.7
            }

    # Default
    return {
        "type": available_types[0] if available_types else "exploration",
        "reasoning": "Default assessment type for this simulation",
        "confidence": 0.5
    }
