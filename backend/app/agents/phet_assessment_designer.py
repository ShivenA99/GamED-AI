"""
PhET Assessment Designer Agent

Creates detailed checkpoint conditions for assessment based on the game plan.
Translates high-level task descriptions into specific, measurable checkpoints.
"""

import json
from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.agents.schemas.phet_simulation import (
    SIMULATION_CATALOG,
    CheckpointConditionType,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.phet_assessment_designer")


PHET_ASSESSMENT_DESIGNER_PROMPT = """You are an expert assessment designer creating specific, measurable checkpoints for a PhET simulation assessment.

## Game Plan:
Assessment Type: {assessment_type}
Assessment Reasoning: {assessment_reasoning}

Learning Objectives:
{learning_objectives}

Task Sequence:
{task_sequence}

## Simulation Capabilities:

Parameters (trackable values that students can change):
{parameters}

Outcomes (measurable results from the simulation):
{outcomes}

Interactions (actions students can perform):
{interactions}

## Checkpoint Condition Types:

### PROPERTY_EQUALS
Check if a property equals a specific value (with optional tolerance)
Example: Student set angle to 45 degrees
```json
{{"type": "property_equals", "propertyId": "cannonAngle", "value": 45, "tolerance": 2}}
```

### PROPERTY_RANGE
Check if a property is within a range
Example: Speed is between 15-20 m/s
```json
{{"type": "property_range", "propertyId": "launchSpeed", "minValue": 15, "maxValue": 20}}
```

### PROPERTY_CHANGED
Check if a property was changed from its default
Example: Student adjusted the mass
```json
{{"type": "property_changed", "propertyId": "projectileMass"}}
```

### INTERACTION_OCCURRED
Check if user performed an interaction
Example: Student clicked Fire button
```json
{{"type": "interaction_occurred", "interactionId": "launch"}}
```

### OUTCOME_ACHIEVED
Check if simulation produced specific outcome
Example: Projectile traveled more than 40 meters
```json
{{"type": "outcome_achieved", "outcomeId": "range", "operator": "gt", "value": 40}}
```
Operators: eq, neq, gt, gte, lt, lte

### TIME_SPENT
Check if user spent minimum time exploring
Example: Spent at least 60 seconds
```json
{{"type": "time_spent", "minSeconds": 60}}
```

### EXPLORATION_BREADTH
Check if user tried multiple parameter values
Example: Tried at least 3 different angles
```json
{{"type": "exploration_breadth", "parameterIds": ["cannonAngle"], "minUniqueValues": 3}}
```

### SEQUENCE_COMPLETED
Check if steps were completed in order
Example: Completed setup steps in sequence
```json
{{"type": "sequence_completed", "sequenceSteps": ["step1", "step2", "step3"]}}
```

## Your Task:

For each task in the sequence, create 2-4 specific checkpoints with exact conditions.
Use the actual parameter names, outcome names, and interaction IDs from the simulation capabilities above.

## Response (JSON only):
{{
    "tasks": [
        {{
            "id": "<task-id>",
            "type": "<assessment_type>",
            "title": "<title>",
            "instructions": "<detailed_instructions_2-3_sentences>",
            "learningObjective": "<specific_objective>",
            "bloomsLevel": "<bloom_level>",
            "checkpoints": [
                {{
                    "id": "<unique-checkpoint-id>",
                    "description": "<what_to_achieve>",
                    "conditions": [
                        {{
                            "type": "<condition_type>",
                            ... condition-specific fields ...
                        }}
                    ],
                    "conditionLogic": "all",
                    "points": <1-30>,
                    "hint": "<helpful_hint>",
                    "feedback": "<success_message>"
                }}
            ],
            "hints": ["<progressive_hint_1>", "<progressive_hint_2>"],
            "prediction": null,
            "quiz": null
        }}
    ],
    "totalPoints": <sum_of_all_checkpoint_points>
}}

IMPORTANT:
- Use actual parameter/outcome/interaction names from the simulation capabilities
- Make checkpoint IDs unique (e.g., "task1-cp1", "task1-cp2")
- Points should reflect difficulty (easy: 5-10, medium: 10-20, hard: 20-30)
- Include helpful hints for each checkpoint
- Use conditionLogic "all" when ALL conditions must be met, "any" when ANY condition works

Respond with ONLY valid JSON."""


def _format_parameters_detailed(parameters: List[Dict]) -> str:
    """Format parameters with full details for prompt."""
    if not parameters:
        return "No adjustable parameters available"

    lines = []
    for p in parameters:
        line = f"- ID: {_to_short_name(p['phetioId'])} | Name: {p['name']} | Type: {p['type']}"
        if p.get('unit'):
            line += f" | Unit: {p['unit']}"
        if p.get('min') is not None and p.get('max') is not None:
            line += f" | Range: {p['min']}-{p['max']}"
        if p.get('defaultValue') is not None:
            line += f" | Default: {p['defaultValue']}"
        lines.append(line)
    return "\n".join(lines)


def _format_outcomes_detailed(outcomes: List[Dict]) -> str:
    """Format outcomes with full details for prompt."""
    if not outcomes:
        return "No measurable outcomes available"

    lines = []
    for o in outcomes:
        line = f"- ID: {o['id']} | Name: {o['name']}"
        if o.get('unit'):
            line += f" | Unit: {o['unit']}"
        if o.get('description'):
            line += f" | {o['description']}"
        lines.append(line)
    return "\n".join(lines)


def _format_interactions_detailed(interactions: List[Dict]) -> str:
    """Format interactions with full details for prompt."""
    if not interactions:
        return "Standard simulation interactions (drag, click, adjust)"

    lines = []
    for i in interactions:
        line = f"- ID: {i['id']} | Name: {i['name']} | Type: {i['type']}"
        if i.get('dataFields'):
            line += f" | Captures: {', '.join(i['dataFields'])}"
        lines.append(line)
    return "\n".join(lines)


def _format_task_sequence(task_sequence: List[Dict]) -> str:
    """Format task sequence for prompt."""
    lines = []
    for i, task in enumerate(task_sequence, 1):
        lines.append(f"Task {i}: {task.get('title', 'Untitled')}")
        lines.append(f"  Type: {task.get('type', 'exploration')}")
        lines.append(f"  Description: {task.get('description', '')}")
        ideas = task.get('checkpointIdeas', [])
        if ideas:
            lines.append(f"  Checkpoint Ideas: {', '.join(ideas)}")
        lines.append(f"  Bloom's Level: {task.get('bloomsLevel', 'understand')}")
        lines.append(f"  Estimated: {task.get('estimatedMinutes', 5)} minutes")
        lines.append("")
    return "\n".join(lines)


def _to_short_name(phetio_id: str) -> str:
    """Extract short name from PhET-iO ID."""
    # e.g., "projectile-motion.introScreen.model.cannonAngleProperty" -> "cannonAngle"
    parts = phetio_id.split(".")
    last_part = parts[-1] if parts else phetio_id
    # Remove "Property" suffix if present
    if last_part.endswith("Property"):
        last_part = last_part[:-8]
    return last_part


def _get_fallback_assessment_design(
    phet_selection: Dict[str, Any],
    phet_game_plan: Dict[str, Any]
) -> Dict[str, Any]:
    """Create fallback assessment design when LLM fails."""
    sim_metadata = phet_selection.get("simulationMetadata", {})
    task_sequence = phet_game_plan.get("taskSequence", [])
    assessment_type = phet_game_plan.get("assessmentType", "exploration")

    # Get simulation capabilities
    params = sim_metadata.get("parameters", [])
    outcomes = sim_metadata.get("outcomes", [])
    interactions = sim_metadata.get("interactions", [])

    tasks = []
    checkpoint_id_counter = 1

    for i, task_plan in enumerate(task_sequence, 1):
        task = {
            "id": f"task-{i}",
            "type": task_plan.get("type", assessment_type),
            "title": task_plan.get("title", f"Task {i}"),
            "instructions": task_plan.get("description", "Complete this task"),
            "learningObjective": f"Complete task {i} successfully",
            "bloomsLevel": task_plan.get("bloomsLevel", "understand"),
            "checkpoints": [],
            "hints": ["Take your time to explore", "Try different values"],
            "prediction": None,
            "quiz": None
        }

        # Create basic checkpoints based on assessment type
        if assessment_type == "exploration" or task_plan.get("type") == "exploration":
            # Exploration: check time spent and parameter changes
            if params:
                task["checkpoints"].append({
                    "id": f"cp-{checkpoint_id_counter}",
                    "description": f"Explore different {params[0]['name']} values",
                    "conditions": [{
                        "type": "exploration_breadth",
                        "parameterIds": [_to_short_name(params[0]['phetioId'])],
                        "minUniqueValues": 3
                    }],
                    "conditionLogic": "all",
                    "points": 15,
                    "hint": f"Try at least 3 different {params[0]['name']} values",
                    "feedback": "Great exploration!"
                })
                checkpoint_id_counter += 1

            task["checkpoints"].append({
                "id": f"cp-{checkpoint_id_counter}",
                "description": "Spend time exploring the simulation",
                "conditions": [{"type": "time_spent", "minSeconds": 30}],
                "conditionLogic": "all",
                "points": 10,
                "hint": "Take at least 30 seconds to explore",
                "feedback": "Good exploration time!"
            })
            checkpoint_id_counter += 1

        elif assessment_type in ["target_achievement", "optimization"]:
            # Target: check outcome achievement
            if outcomes:
                task["checkpoints"].append({
                    "id": f"cp-{checkpoint_id_counter}",
                    "description": f"Achieve the target {outcomes[0]['name']}",
                    "conditions": [{
                        "type": "outcome_achieved",
                        "outcomeId": outcomes[0]['id'],
                        "operator": "gte",
                        "value": 10  # Generic target
                    }],
                    "conditionLogic": "all",
                    "points": 20,
                    "hint": f"Adjust parameters to achieve the target {outcomes[0]['name']}",
                    "feedback": "Target achieved!"
                })
                checkpoint_id_counter += 1

        elif assessment_type == "parameter_discovery":
            # Discovery: check parameter changes and observations
            if params and len(params) >= 2:
                task["checkpoints"].append({
                    "id": f"cp-{checkpoint_id_counter}",
                    "description": f"Change the {params[0]['name']}",
                    "conditions": [{"type": "property_changed", "propertyId": _to_short_name(params[0]['phetioId'])}],
                    "conditionLogic": "all",
                    "points": 10,
                    "hint": f"Use the slider to adjust {params[0]['name']}",
                    "feedback": "Parameter changed!"
                })
                checkpoint_id_counter += 1

        # Add interaction checkpoint if available
        if interactions:
            task["checkpoints"].append({
                "id": f"cp-{checkpoint_id_counter}",
                "description": f"Perform: {interactions[0]['name']}",
                "conditions": [{"type": "interaction_occurred", "interactionId": interactions[0]['id']}],
                "conditionLogic": "all",
                "points": 10,
                "hint": f"Click the button to {interactions[0]['name'].lower()}",
                "feedback": "Action completed!"
            })
            checkpoint_id_counter += 1

        # Ensure at least one checkpoint per task
        if not task["checkpoints"]:
            task["checkpoints"].append({
                "id": f"cp-{checkpoint_id_counter}",
                "description": "Complete the task",
                "conditions": [{"type": "time_spent", "minSeconds": 20}],
                "conditionLogic": "all",
                "points": 10,
                "hint": "Spend some time completing the task",
                "feedback": "Task completed!"
            })
            checkpoint_id_counter += 1

        tasks.append(task)

    total_points = sum(cp["points"] for task in tasks for cp in task["checkpoints"])

    return {
        "tasks": tasks,
        "totalPoints": total_points
    }


async def phet_assessment_designer_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> Dict[str, Any]:
    """
    Create detailed assessment checkpoints with conditions.

    Args:
        state: Current agent state with phet_selection and phet_game_plan
        ctx: Optional instrumentation context

    Returns:
        Updated state with phet_assessment_design
    """
    logger.info("PhET Assessment Designer: Creating detailed checkpoints")

    phet_selection = state.get("phet_selection", {})
    phet_game_plan = state.get("phet_game_plan", {})

    if not phet_game_plan.get("assessmentType"):
        logger.error("PhET Assessment Designer: No game plan available")
        return {
            **state,
            "current_agent": "phet_assessment_designer",
            "error_message": "No game plan for assessment design"
        }

    sim_metadata = phet_selection.get("simulationMetadata", {})
    sim_id = phet_selection.get("simulationId")

    # Ensure metadata
    if not sim_metadata and sim_id in SIMULATION_CATALOG:
        sim_metadata = SIMULATION_CATALOG[sim_id]

    prompt = PHET_ASSESSMENT_DESIGNER_PROMPT.format(
        assessment_type=phet_game_plan.get("assessmentType", "exploration"),
        assessment_reasoning=phet_game_plan.get("assessmentTypeReasoning", ""),
        learning_objectives="\n".join(
            f"- {obj}" for obj in phet_game_plan.get("learningObjectives", [])
        ),
        task_sequence=_format_task_sequence(phet_game_plan.get("taskSequence", [])),
        parameters=_format_parameters_detailed(sim_metadata.get("parameters", [])),
        outcomes=_format_outcomes_detailed(sim_metadata.get("outcomes", [])),
        interactions=_format_interactions_detailed(sim_metadata.get("interactions", []))
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json_for_agent(
            agent_name="phet_assessment_designer",
            prompt=prompt,
            schema_hint="Assessment design with tasks array containing checkpoints"
        )

        # Validate and fix checkpoint structure
        tasks = result.get("tasks", [])
        total_points = 0

        for task in tasks:
            for checkpoint in task.get("checkpoints", []):
                # Ensure required fields
                if "conditionLogic" not in checkpoint:
                    checkpoint["conditionLogic"] = "all"
                if "points" not in checkpoint:
                    checkpoint["points"] = 10
                if "conditions" not in checkpoint or not checkpoint["conditions"]:
                    checkpoint["conditions"] = [{"type": "time_spent", "minSeconds": 10}]

                # Normalize condition types
                for cond in checkpoint.get("conditions", []):
                    cond_type = cond.get("type", "").lower().replace("-", "_")
                    cond["type"] = cond_type

                total_points += checkpoint.get("points", 0)

        result["totalPoints"] = total_points

        logger.info(
            f"PhET Assessment Designer: Created {len(tasks)} tasks "
            f"with {sum(len(t.get('checkpoints', [])) for t in tasks)} checkpoints "
            f"totaling {total_points} points"
        )

        if ctx:
            ctx.complete({
                "phet_assessment_design": result,
                "current_agent": "phet_assessment_designer"
            })

        return {
            **state,
            "phet_assessment_design": result,
            "current_agent": "phet_assessment_designer"
        }

    except Exception as e:
        logger.error(f"PhET Assessment Designer: LLM call failed: {e}", exc_info=True)

        # Use fallback
        fallback = _get_fallback_assessment_design(phet_selection, phet_game_plan)

        return {
            **state,
            "phet_assessment_design": fallback,
            "current_agent": "phet_assessment_designer",
            "error_message": f"PhET Assessment Designer fallback: {str(e)}"
        }
