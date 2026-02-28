"""
PhET Simulation Selector Agent

Selects the optimal PhET simulation for the given learning context.
Uses the simulation catalog to match concepts, Bloom's level, and assessment types.
"""

import json
from typing import Dict, Any, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.agents.schemas.phet_simulation import (
    SIMULATION_CATALOG,
    get_simulations_by_domain,
    get_simulations_by_concept,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.phet_simulation_selector")


PHET_SELECTOR_PROMPT = """You are an expert educational technology specialist. Select the optimal PhET simulation for this learning activity.

## Question/Topic:
{question_text}

## Pedagogical Context:
- Subject: {subject}
- Bloom's Level: {blooms_level}
- Key Concepts: {key_concepts}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}

## Available Simulations:

{simulation_catalog}

## Selection Criteria:

1. **Concept Match (40%)**: How well do simulation concepts align with question concepts?
2. **Bloom's Alignment (25%)**: Does simulation support the target cognitive level?
   - remember/understand → exploration, parameter_discovery
   - apply → target_achievement, measurement, construction
   - analyze → parameter_discovery, comparative_analysis
   - evaluate/create → optimization, construction
3. **Interaction Fit (20%)**: Can simulation interactions address the question type?
4. **Assessment Fit (15%)**: What assessment types work well with this simulation?

## Response Format (JSON only):
{{
    "simulationId": "<simulation-id>",
    "confidence": <0.0-1.0>,
    "reasoning": "<2-3 sentences explaining why this simulation is the best fit>",
    "recommendedScreen": "<screen-name or null>",
    "recommendedAssessmentTypes": ["<type1>", "<type2>"],
    "keyParameters": ["<param1>", "<param2>"],
    "keyOutcomes": ["<outcome1>", "<outcome2>"],
    "alternativeSimulation": "<backup-simulation-id or null>",
    "conceptAlignment": {{
        "matched": ["<concept1>", "<concept2>"],
        "score": <0.0-1.0>
    }}
}}

Respond with ONLY valid JSON."""


def _build_catalog_text() -> str:
    """Build formatted catalog for prompt."""
    lines = []
    for sim_id, meta in SIMULATION_CATALOG.items():
        lines.append(f"### {meta['title']} ({sim_id})")
        lines.append(f"Domains: {', '.join(meta['domains'])}")
        lines.append(f"Concepts: {', '.join(meta['concepts'][:6])}")
        lines.append(f"Assessment Types: {', '.join(meta['assessmentTypes'])}")
        params = [p['name'] for p in meta.get('parameters', [])[:4]]
        if params:
            lines.append(f"Parameters: {', '.join(params)}")
        outcomes = [o['name'] for o in meta.get('outcomes', [])[:3]]
        if outcomes:
            lines.append(f"Outcomes: {', '.join(outcomes)}")
        screens = meta.get('screens', [])
        if screens:
            lines.append(f"Screens: {', '.join(screens)}")
        lines.append("")
    return "\n".join(lines)


def _get_fallback_selection(
    question_text: str,
    ped_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Create fallback selection using heuristics when LLM fails."""
    subject = ped_context.get("subject", "").lower()
    concepts = ped_context.get("key_concepts", [])
    question_lower = question_text.lower()

    # Domain-based matching
    if "physics" in subject or any(c in question_lower for c in ["motion", "force", "energy", "velocity"]):
        if "projectile" in question_lower or "trajectory" in question_lower or "angle" in question_lower:
            return _create_selection("projectile-motion", 0.7, "Fallback: matched projectile motion concepts")
        elif "circuit" in question_lower or "voltage" in question_lower or "current" in question_lower:
            return _create_selection("circuit-construction-kit-dc", 0.7, "Fallback: matched circuit concepts")
        elif "pendulum" in question_lower or "period" in question_lower or "swing" in question_lower:
            return _create_selection("pendulum-lab", 0.7, "Fallback: matched pendulum concepts")
        elif "energy" in question_lower or "kinetic" in question_lower or "potential" in question_lower:
            return _create_selection("energy-skate-park", 0.7, "Fallback: matched energy concepts")
        elif "wave" in question_lower or "frequency" in question_lower or "amplitude" in question_lower:
            return _create_selection("waves", 0.7, "Fallback: matched wave concepts")
        elif "friction" in question_lower:
            return _create_selection("friction", 0.7, "Fallback: matched friction concepts")
        else:
            return _create_selection("projectile-motion", 0.5, "Fallback: default physics simulation")

    elif "chemistry" in subject or any(c in question_lower for c in ["molecule", "atom", "element", "phase"]):
        if "state" in question_lower or "phase" in question_lower or "temperature" in question_lower:
            return _create_selection("states-of-matter", 0.7, "Fallback: matched states of matter concepts")
        elif "atom" in question_lower or "proton" in question_lower or "electron" in question_lower:
            return _create_selection("build-an-atom", 0.7, "Fallback: matched atomic structure concepts")
        elif "polar" in question_lower or "electronegativity" in question_lower or "dipole" in question_lower:
            return _create_selection("molecule-polarity", 0.7, "Fallback: matched molecular polarity concepts")
        else:
            return _create_selection("states-of-matter", 0.5, "Fallback: default chemistry simulation")

    elif "math" in subject or any(c in question_lower for c in ["parabola", "quadratic", "graph", "area"]):
        if "quadratic" in question_lower or "parabola" in question_lower or "vertex" in question_lower:
            return _create_selection("graphing-quadratics", 0.7, "Fallback: matched quadratic concepts")
        elif "area" in question_lower or "perimeter" in question_lower or "shape" in question_lower:
            return _create_selection("area-builder", 0.7, "Fallback: matched geometry concepts")
        else:
            return _create_selection("graphing-quadratics", 0.5, "Fallback: default math simulation")

    # Default fallback
    return _create_selection("projectile-motion", 0.4, "Fallback: default simulation (no specific match)")


def _create_selection(
    sim_id: str,
    confidence: float,
    reasoning: str
) -> Dict[str, Any]:
    """Create a selection result with simulation metadata."""
    meta = SIMULATION_CATALOG.get(sim_id, {})

    return {
        "simulationId": sim_id,
        "confidence": confidence,
        "reasoning": reasoning,
        "recommendedScreen": meta.get("screens", [None])[0],
        "recommendedAssessmentTypes": meta.get("assessmentTypes", [])[:2],
        "keyParameters": [p["name"] for p in meta.get("parameters", [])[:3]],
        "keyOutcomes": [o["name"] for o in meta.get("outcomes", [])[:3]],
        "alternativeSimulation": None,
        "conceptAlignment": {
            "matched": meta.get("concepts", [])[:3],
            "score": confidence
        },
        "simulationMetadata": meta
    }


async def phet_simulation_selector_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> Dict[str, Any]:
    """
    Select optimal PhET simulation for the learning context.

    Args:
        state: Current agent state with question_text and pedagogical_context
        ctx: Optional instrumentation context

    Returns:
        Updated state with phet_selection
    """
    logger.info(f"PhET Selector: Processing question {state.get('question_id', 'unknown')}")

    question_text = state.get("question_text", "")
    ped_context = state.get("pedagogical_context", {})

    if not question_text:
        logger.error("PhET Selector: No question text")
        return {
            **state,
            "current_agent": "phet_simulation_selector",
            "error_message": "No question text for PhET selection"
        }

    # Build catalog text for prompt
    catalog_text = _build_catalog_text()

    prompt = PHET_SELECTOR_PROMPT.format(
        question_text=question_text,
        subject=ped_context.get("subject", "General"),
        blooms_level=ped_context.get("blooms_level", "understand"),
        key_concepts=", ".join(ped_context.get("key_concepts", [])),
        difficulty=ped_context.get("difficulty", "medium"),
        learning_objectives=json.dumps(ped_context.get("learning_objectives", [])),
        simulation_catalog=catalog_text
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json_for_agent(
            agent_name="phet_simulation_selector",
            prompt=prompt,
            schema_hint="PhET simulation selection with simulationId, confidence, reasoning"
        )

        # Validate simulation exists
        sim_id = result.get("simulationId")
        if sim_id not in SIMULATION_CATALOG:
            logger.warning(f"PhET Selector: Unknown simulation {sim_id}, using fallback")
            result = _get_fallback_selection(question_text, ped_context)
        else:
            # Enrich with catalog metadata
            result["simulationMetadata"] = SIMULATION_CATALOG[sim_id]

        # Normalize confidence
        confidence = float(result.get("confidence", 0.7))
        result["confidence"] = max(0.0, min(1.0, confidence))

        logger.info(
            f"PhET Selector: Selected {result['simulationId']} "
            f"with confidence {result['confidence']:.2f}"
        )

        # Set metrics for instrumentation
        if ctx:
            ctx.complete({
                "phet_selection": result,
                "current_agent": "phet_simulation_selector"
            })

        return {
            **state,
            "phet_selection": result,
            "current_agent": "phet_simulation_selector"
        }

    except Exception as e:
        logger.error(f"PhET Selector: LLM call failed: {e}", exc_info=True)

        # Use fallback selection
        fallback = _get_fallback_selection(question_text, ped_context)

        return {
            **state,
            "phet_selection": fallback,
            "current_agent": "phet_simulation_selector",
            "error_message": f"PhET Selector fallback: {str(e)}"
        }


def get_simulations_for_context(
    subject: str,
    concepts: list,
    blooms_level: str
) -> list:
    """
    Get ranked list of simulations matching context.

    Args:
        subject: Subject area
        concepts: List of key concepts
        blooms_level: Target Bloom's level

    Returns:
        List of (simulation_id, score) tuples sorted by relevance
    """
    scores = {}

    # Score by domain
    domain_matches = get_simulations_by_domain(subject)
    for sim_id in domain_matches:
        scores[sim_id] = scores.get(sim_id, 0) + 0.4

    # Score by concepts
    for concept in concepts:
        concept_matches = get_simulations_by_concept(concept)
        for sim_id in concept_matches:
            scores[sim_id] = scores.get(sim_id, 0) + 0.2

    # Score by Bloom's alignment
    blooms_assessment_map = {
        "remember": ["exploration"],
        "understand": ["exploration", "parameter_discovery"],
        "apply": ["target_achievement", "measurement", "construction"],
        "analyze": ["parameter_discovery", "comparative_analysis"],
        "evaluate": ["optimization", "prediction_verification"],
        "create": ["construction", "optimization"],
    }

    preferred_types = blooms_assessment_map.get(blooms_level, ["exploration"])
    for sim_id, meta in SIMULATION_CATALOG.items():
        sim_types = meta.get("assessmentTypes", [])
        if any(t in sim_types for t in preferred_types):
            scores[sim_id] = scores.get(sim_id, 0) + 0.25

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked
