"""
PhET Blueprint Generator Agent

Generates the complete PHET_SIMULATION blueprint from all upstream agent outputs.
Follows the same pattern as blueprint_generator.py for other templates.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.agents.schemas.phet_simulation import (
    SIMULATION_CATALOG,
    PhetSimulationBlueprint,
    validate_phet_blueprint,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.phet_blueprint_generator")


PHET_BLUEPRINT_GENERATOR_PROMPT = """You are generating a complete PHET_SIMULATION blueprint JSON.

## Context:
Question: {question_text}
Subject: {subject}
Bloom's Level: {blooms_level}
Difficulty: {difficulty}

## Selected Simulation:
{simulation_info}

## Game Plan:
{game_plan}

## Assessment Design:
{assessment_design}

## Previous Validation Errors (fix these):
{validation_errors}

## Blueprint Schema Requirements:

1. **templateType**: Must be exactly "PHET_SIMULATION"

2. **simulation**: SimulationConfig object
   - simulationId: Exact simulation ID from selection
   - screen: Recommended screen (or null)
   - parameters: List of SimulationParameter objects
   - interactions: List of SimulationInteraction objects
   - outcomes: List of SimulationOutcome objects
   - initialState: Optional starting parameter values

3. **assessmentType**: One of: exploration, parameter_discovery, target_achievement,
   prediction_verification, comparative_analysis, optimization, measurement,
   construction, sequence_execution

4. **tasks**: Array of AssessmentTask objects
   - Each task has: id, type, title, instructions, checkpoints
   - Each checkpoint has: id, description, conditions, conditionLogic, points
   - Conditions use: type, propertyId/interactionId/outcomeId, operator, value

5. **scoring**: ScoringRubric object
   - maxScore: Must be >= total checkpoint points
   - Optional: explorationBonus, hintPenalty, speedBonus

6. **feedback**: FeedbackMessages (can use defaults)

7. **learningObjectives**: 2-4 objectives

8. **targetBloomsLevel**: remember/understand/apply/analyze/evaluate/create

9. **estimatedMinutes**: 5-60

10. **difficulty**: easy/medium/hard

## CRITICAL VALIDATION RULES:
- All propertyId values must match parameter phetioId short names
- All interactionId values must match interaction id fields
- All outcomeId values must match outcome id fields
- Checkpoint IDs must be unique across ALL tasks
- Total checkpoint points MUST NOT exceed maxScore
- Each task must have at least 1 checkpoint

## Response: Output ONLY valid JSON matching PhetSimulationBlueprint schema.
Do NOT include any explanation, just the JSON object."""


def _format_simulation_info(phet_selection: Dict[str, Any]) -> str:
    """Format simulation info for prompt."""
    sim_id = phet_selection.get("simulationId", "unknown")
    meta = phet_selection.get("simulationMetadata", {})

    lines = [
        f"ID: {sim_id}",
        f"Title: {meta.get('title', sim_id)}",
        f"Confidence: {phet_selection.get('confidence', 0):.2f}",
        f"Reasoning: {phet_selection.get('reasoning', '')}",
        f"Recommended Screen: {phet_selection.get('recommendedScreen', 'default')}",
        f"Recommended Assessment Types: {', '.join(phet_selection.get('recommendedAssessmentTypes', []))}",
        "",
        "Parameters:",
    ]

    for p in meta.get("parameters", []):
        parts = [f"  - {p['name']}"]
        parts.append(f"(phetioId: {p['phetioId']})")
        if p.get('unit'):
            parts.append(f"[{p['unit']}]")
        if p.get('min') is not None:
            parts.append(f"range: {p['min']}-{p['max']}")
        lines.append(" ".join(parts))

    lines.append("\nInteractions:")
    for i in meta.get("interactions", []):
        lines.append(f"  - {i['name']} (id: {i['id']}, type: {i['type']})")

    lines.append("\nOutcomes:")
    for o in meta.get("outcomes", []):
        parts = [f"  - {o['name']} (id: {o['id']})"]
        if o.get('unit'):
            parts.append(f"[{o['unit']}]")
        lines.append(" ".join(parts))

    return "\n".join(lines)


def _to_short_name(phetio_id: str) -> str:
    """Extract short name from PhET-iO ID."""
    parts = phetio_id.split(".")
    last_part = parts[-1] if parts else phetio_id
    if last_part.endswith("Property"):
        last_part = last_part[:-8]
    return last_part


def _build_blueprint_from_state(
    state: AgentState,
    previous_errors: List[str] = None
) -> Dict[str, Any]:
    """Build blueprint directly from state without LLM when possible."""
    phet_selection = state.get("phet_selection", {})
    phet_game_plan = state.get("phet_game_plan", {})
    phet_assessment = state.get("phet_assessment_design", {})
    ped_context = state.get("pedagogical_context", {})

    sim_id = phet_selection.get("simulationId", "projectile-motion")
    sim_metadata = phet_selection.get("simulationMetadata", SIMULATION_CATALOG.get(sim_id, {}))

    # Build simulation config
    simulation = {
        "simulationId": sim_id,
        "version": "latest",
        "screen": phet_selection.get("recommendedScreen"),
        "parameters": [],
        "interactions": [],
        "outcomes": [],
        "initialState": None
    }

    # Map parameters
    for p in sim_metadata.get("parameters", []):
        simulation["parameters"].append({
            "phetioId": p["phetioId"],
            "name": p["name"],
            "type": p.get("type", "number"),
            "unit": p.get("unit"),
            "min": p.get("min"),
            "max": p.get("max"),
            "step": p.get("step"),
            "defaultValue": p.get("defaultValue")
        })

    # Map interactions
    for i in sim_metadata.get("interactions", []):
        simulation["interactions"].append({
            "id": i["id"],
            "type": i.get("type", "button_click"),
            "phetioId": i.get("phetioId", ""),
            "name": i["name"],
            "dataFields": i.get("dataFields")
        })

    # Map outcomes
    for o in sim_metadata.get("outcomes", []):
        simulation["outcomes"].append({
            "id": o["id"],
            "name": o["name"],
            "phetioId": o.get("phetioId", ""),
            "unit": o.get("unit")
        })

    # Get tasks from assessment design
    tasks = phet_assessment.get("tasks", [])

    # Calculate total points
    total_points = sum(
        cp.get("points", 0)
        for task in tasks
        for cp in task.get("checkpoints", [])
    )

    # Calculate max score with buffer
    max_score = max(total_points + 20, 100)  # At least 100 or total + 20

    blueprint = {
        "templateType": "PHET_SIMULATION",
        "title": f"{sim_metadata.get('title', 'PhET')} Challenge: {state.get('question_text', 'Learning Activity')[:50]}",
        "narrativeIntro": phet_game_plan.get(
            "assessmentTypeReasoning",
            f"Explore {sim_metadata.get('title', 'this simulation')} to learn key concepts."
        ),
        "simulation": simulation,
        "assessmentType": phet_game_plan.get("assessmentType", "exploration"),
        "tasks": tasks,
        "scoring": {
            "maxScore": max_score,
            "explorationBonus": 10 if phet_game_plan.get("assessmentType") == "exploration" else None,
            "hintPenalty": 2
        },
        "feedback": {
            "checkpointComplete": "Great job! Checkpoint completed.",
            "taskComplete": "Task completed successfully!",
            "incorrectAttempt": "Not quite. Try again!",
            "hintUsed": "Here's a hint to help you.",
            "gameComplete": {
                "perfect": "Outstanding! You mastered this simulation!",
                "good": "Well done! You've shown good understanding.",
                "passing": "Good effort! Review the concepts and try again.",
                "retry": "Keep practicing! You'll get it!"
            }
        },
        "animations": {
            "checkpointComplete": {"type": "pulse", "duration_ms": 400, "color": "#22c55e"},
            "incorrectAttempt": {"type": "shake", "duration_ms": 300, "color": "#ef4444"},
            "taskComplete": {"type": "bounce", "duration_ms": 500, "color": "#3b82f6"},
            "gameComplete": {"type": "confetti", "duration_ms": 2000}
        },
        "learningObjectives": phet_game_plan.get("learningObjectives", [
            f"Understand key concepts in {sim_metadata.get('title', 'the simulation')}",
            "Apply knowledge to achieve learning objectives",
            "Analyze results and draw conclusions"
        ])[:4],
        "targetBloomsLevel": ped_context.get("blooms_level", "understand"),
        "estimatedMinutes": phet_game_plan.get("estimatedTotalMinutes", 15),
        "difficulty": ped_context.get("difficulty", "medium")
    }

    return blueprint


async def phet_blueprint_generator_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> Dict[str, Any]:
    """
    Generate complete PhET blueprint.

    Args:
        state: Current agent state with all upstream outputs
        ctx: Optional instrumentation context

    Returns:
        Updated state with blueprint
    """
    logger.info("PhET Blueprint Generator: Generating complete blueprint")

    phet_selection = state.get("phet_selection", {})
    phet_game_plan = state.get("phet_game_plan", {})
    phet_assessment = state.get("phet_assessment_design", {})
    ped_context = state.get("pedagogical_context", {})
    validation_errors = state.get("current_validation_errors", [])

    if not phet_selection.get("simulationId"):
        logger.error("PhET Blueprint Generator: No simulation selected")
        return {
            **state,
            "current_agent": "phet_blueprint_generator",
            "error_message": "No simulation selected"
        }

    # First try to build directly from state (more reliable)
    blueprint = _build_blueprint_from_state(state, validation_errors)

    # Validate the built blueprint
    validation_result = validate_phet_blueprint(blueprint)

    if validation_result["valid"]:
        logger.info("PhET Blueprint Generator: Direct build successful")

        if ctx:
            ctx.complete({
                "blueprint": blueprint,
                "current_agent": "phet_blueprint_generator"
            })

        return {
            **state,
            "blueprint": blueprint,
            "current_agent": "phet_blueprint_generator"
        }

    # If direct build failed, try LLM refinement
    logger.warning(
        f"PhET Blueprint Generator: Direct build failed with errors: "
        f"{validation_result['errors']}, trying LLM refinement"
    )

    prompt = PHET_BLUEPRINT_GENERATOR_PROMPT.format(
        question_text=state.get("question_text", ""),
        subject=ped_context.get("subject", "Science"),
        blooms_level=ped_context.get("blooms_level", "understand"),
        difficulty=ped_context.get("difficulty", "medium"),
        simulation_info=_format_simulation_info(phet_selection),
        game_plan=json.dumps(phet_game_plan, indent=2),
        assessment_design=json.dumps(phet_assessment, indent=2),
        validation_errors="\n".join(f"- {e}" for e in validation_errors + validation_result["errors"]) or "None"
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json_for_agent(
            agent_name="phet_blueprint_generator",
            prompt=prompt,
            schema_hint="PhetSimulationBlueprint"
        )

        # Ensure templateType
        result["templateType"] = "PHET_SIMULATION"

        # Validate LLM result
        llm_validation = validate_phet_blueprint(result)

        if llm_validation["valid"]:
            logger.info("PhET Blueprint Generator: LLM refinement successful")
            blueprint = result
        else:
            logger.warning(
                f"PhET Blueprint Generator: LLM result also invalid: "
                f"{llm_validation['errors']}, using direct build with fixes"
            )
            # Use direct build and try to fix issues
            blueprint = _fix_blueprint_issues(blueprint, llm_validation["errors"])

    except Exception as e:
        logger.error(f"PhET Blueprint Generator: LLM call failed: {e}", exc_info=True)
        # Use direct build
        blueprint = _fix_blueprint_issues(blueprint, validation_result["errors"])

    if ctx:
        ctx.complete({
            "blueprint": blueprint,
            "current_agent": "phet_blueprint_generator"
        })

    return {
        **state,
        "blueprint": blueprint,
        "current_agent": "phet_blueprint_generator"
    }


def _fix_blueprint_issues(blueprint: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
    """Attempt to fix common blueprint issues."""
    fixed = blueprint.copy()

    # Fix scoring total issue
    if any("exceed maxScore" in e for e in errors):
        total_points = sum(
            cp.get("points", 0)
            for task in fixed.get("tasks", [])
            for cp in task.get("checkpoints", [])
        )
        fixed["scoring"]["maxScore"] = total_points + 30

    # Fix duplicate checkpoint IDs
    if any("Duplicate checkpoint" in e for e in errors):
        seen_ids = set()
        for task in fixed.get("tasks", []):
            for i, cp in enumerate(task.get("checkpoints", [])):
                if cp["id"] in seen_ids:
                    cp["id"] = f"{task['id']}-cp-{i+1}"
                seen_ids.add(cp["id"])

    # Ensure minimum structure
    if not fixed.get("tasks") or len(fixed.get("tasks", [])) == 0:
        fixed["tasks"] = [{
            "id": "task-1",
            "type": fixed.get("assessmentType", "exploration"),
            "title": "Complete the Task",
            "instructions": "Follow the instructions to complete this assessment.",
            "checkpoints": [{
                "id": "cp-1",
                "description": "Complete the task",
                "conditions": [{"type": "time_spent", "minSeconds": 30}],
                "conditionLogic": "all",
                "points": 10,
                "hint": "Take your time",
                "feedback": "Well done!"
            }],
            "hints": ["Take your time to explore"]
        }]

    return fixed


async def validate_and_fix_phet_blueprint(
    blueprint: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate blueprint and return validation result with optional fixes.

    Args:
        blueprint: The blueprint to validate
        context: Context information for validation

    Returns:
        Validation result with errors, warnings, and optionally fixed blueprint
    """
    result = validate_phet_blueprint(blueprint)

    if not result["valid"]:
        # Try to fix
        fixed = _fix_blueprint_issues(blueprint, result["errors"])
        revalidation = validate_phet_blueprint(fixed)

        if revalidation["valid"]:
            result["fixed_blueprint"] = fixed
            result["auto_fixed"] = True

    return result
