"""
PhET Simulation Selector Agent

This agent analyzes pedagogical context and selects the optimal PhET simulation
for the given learning objectives. It matches question concepts with simulation
capabilities and generates customization recommendations.

Integration Point: Add after router agent when template_type == "PHET_SIMULATION"
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# These would be imported from the main codebase
# from app.agents.state import AgentState, PedagogicalContext
# from app.agents.instrumentation import InstrumentedAgentContext
# from app.services.llm_service import get_llm_service

logger = logging.getLogger("gamed_ai.agents.phet_simulation_selector")


# =============================================================================
# SIMULATION CATALOG (Expanded from blueprint schema)
# =============================================================================

PHET_SIMULATION_CATALOG = {
    "projectile-motion": {
        "title": "Projectile Motion",
        "description": "Explore projectile motion by launching various objects. Set the angle, initial speed, and mass, then measure trajectory, range, and height.",
        "domains": ["physics"],
        "concepts": [
            "kinematics", "projectile motion", "vectors", "gravity", "trajectory",
            "velocity", "acceleration", "parabolic motion", "range", "launch angle"
        ],
        "blooms_levels": ["understand", "apply", "analyze"],
        "interaction_types": ["parameter_adjustment", "measurement", "prediction"],
        "phet_io_support": "full",
        "screens": ["intro", "vectors", "drag", "lab"],
        "key_phetio_ids": [
            "projectile-motion.introScreen.model.cannonAngleProperty",
            "projectile-motion.introScreen.model.launchSpeedProperty",
            "projectile-motion.introScreen.model.selectedProjectileObjectTypeProperty"
        ],
        "difficulty": "medium",
        "grade_levels": ["9-12", "college"]
    },
    "circuit-construction-kit-dc": {
        "title": "Circuit Construction Kit: DC",
        "description": "Build circuits with batteries, resistors, light bulbs, switches, and wires. Explore Ohm's law and measure voltage, current, and resistance.",
        "domains": ["physics"],
        "concepts": [
            "circuits", "current", "voltage", "resistance", "Ohm's law",
            "series circuits", "parallel circuits", "electrical components"
        ],
        "blooms_levels": ["understand", "apply", "analyze", "create"],
        "interaction_types": ["construction", "measurement", "exploration"],
        "phet_io_support": "full",
        "screens": ["intro", "lab"],
        "key_phetio_ids": [
            "circuit-construction-kit-dc.introScreen.model.circuit.voltageProperty",
            "circuit-construction-kit-dc.introScreen.model.circuit.currentProperty"
        ],
        "difficulty": "medium",
        "grade_levels": ["6-8", "9-12"]
    },
    "states-of-matter": {
        "title": "States of Matter",
        "description": "Watch atoms and molecules as they change phase. Heat, cool, and change pressure to explore molecular behavior.",
        "domains": ["chemistry", "physics"],
        "concepts": [
            "molecular motion", "phases", "phase transitions", "temperature",
            "pressure", "kinetic theory", "solid", "liquid", "gas"
        ],
        "blooms_levels": ["understand", "apply"],
        "interaction_types": ["exploration", "parameter_adjustment"],
        "phet_io_support": "full",
        "screens": ["states", "phase-changes"],
        "key_phetio_ids": [
            "states-of-matter.statesScreen.model.temperatureProperty",
            "states-of-matter.statesScreen.model.moleculeTypeProperty"
        ],
        "difficulty": "low",
        "grade_levels": ["6-8", "9-12"]
    },
    "graphing-quadratics": {
        "title": "Graphing Quadratics",
        "description": "Explore parabolas by manipulating the coefficients of quadratic equations. Connect the equation to the graph shape.",
        "domains": ["mathematics"],
        "concepts": [
            "quadratic functions", "parabolas", "vertex", "roots", "coefficients",
            "axis of symmetry", "standard form", "vertex form"
        ],
        "blooms_levels": ["understand", "apply", "analyze"],
        "interaction_types": ["parameter_adjustment", "prediction"],
        "phet_io_support": "full",
        "screens": ["explore", "standard-form", "vertex-form"],
        "key_phetio_ids": [
            "graphing-quadratics.exploreScreen.model.quadraticProperty"
        ],
        "difficulty": "medium",
        "grade_levels": ["9-12"]
    },
    "friction": {
        "title": "Friction",
        "description": "Learn how friction affects motion. Explore static and kinetic friction with different surfaces and applied forces.",
        "domains": ["physics"],
        "concepts": [
            "friction", "static friction", "kinetic friction", "forces",
            "motion", "Newton's laws", "coefficient of friction"
        ],
        "blooms_levels": ["understand", "apply"],
        "interaction_types": ["exploration", "parameter_adjustment"],
        "phet_io_support": "full",
        "screens": ["friction"],
        "key_phetio_ids": [
            "friction.frictionScreen.model.appliedForceProperty",
            "friction.frictionScreen.model.frictionForceProperty"
        ],
        "difficulty": "low",
        "grade_levels": ["6-8", "9-12"]
    },
    "waves": {
        "title": "Waves",
        "description": "Make waves with water, sound, or light. See how amplitude, frequency, and wavelength interact.",
        "domains": ["physics"],
        "concepts": [
            "wave properties", "frequency", "amplitude", "wavelength",
            "interference", "wave speed", "transverse waves", "longitudinal waves"
        ],
        "blooms_levels": ["understand", "apply", "analyze"],
        "interaction_types": ["exploration", "parameter_adjustment", "measurement"],
        "phet_io_support": "full",
        "screens": ["waves", "interference"],
        "key_phetio_ids": [
            "waves.wavesScreen.model.frequencyProperty",
            "waves.wavesScreen.model.amplitudeProperty"
        ],
        "difficulty": "medium",
        "grade_levels": ["9-12", "college"]
    },
    "molecule-polarity": {
        "title": "Molecule Polarity",
        "description": "Explore how electronegativity differences lead to polar molecules. Build molecules and observe electron distribution.",
        "domains": ["chemistry"],
        "concepts": [
            "electronegativity", "polarity", "molecular structure", "dipole",
            "polar bonds", "nonpolar bonds", "electron distribution"
        ],
        "blooms_levels": ["understand", "apply"],
        "interaction_types": ["exploration", "construction"],
        "phet_io_support": "full",
        "screens": ["two-atoms", "three-atoms", "real-molecules"],
        "key_phetio_ids": [
            "molecule-polarity.twoAtomsScreen.model.moleculeProperty"
        ],
        "difficulty": "medium",
        "grade_levels": ["9-12", "college"]
    },
    "energy-skate-park": {
        "title": "Energy Skate Park",
        "description": "Explore energy conservation with a skater on a track. See how potential and kinetic energy transform.",
        "domains": ["physics"],
        "concepts": [
            "energy conservation", "potential energy", "kinetic energy",
            "mechanical energy", "friction", "work"
        ],
        "blooms_levels": ["understand", "apply", "analyze"],
        "interaction_types": ["exploration", "construction", "measurement"],
        "phet_io_support": "full",
        "screens": ["intro", "playground", "measure"],
        "key_phetio_ids": [
            "energy-skate-park.introScreen.model.skater.kineticEnergyProperty",
            "energy-skate-park.introScreen.model.skater.potentialEnergyProperty"
        ],
        "difficulty": "medium",
        "grade_levels": ["6-8", "9-12"]
    },
    "area-builder": {
        "title": "Area Builder",
        "description": "Build shapes and explore the concept of area. Compare areas of different shapes and find patterns.",
        "domains": ["mathematics"],
        "concepts": [
            "area", "perimeter", "geometry", "shapes", "measurement",
            "square units", "decomposition"
        ],
        "blooms_levels": ["understand", "apply"],
        "interaction_types": ["construction", "exploration"],
        "phet_io_support": "full",
        "screens": ["explore", "game"],
        "key_phetio_ids": [
            "area-builder.exploreScreen.model.areaProperty"
        ],
        "difficulty": "low",
        "grade_levels": ["3-5", "6-8"]
    },
    "pendulum-lab": {
        "title": "Pendulum Lab",
        "description": "Play with pendulum length, mass, and gravity. Explore simple harmonic motion and period relationships.",
        "domains": ["physics"],
        "concepts": [
            "pendulum", "period", "simple harmonic motion", "gravity",
            "oscillation", "length", "mass independence"
        ],
        "blooms_levels": ["understand", "apply", "analyze"],
        "interaction_types": ["exploration", "parameter_adjustment", "measurement"],
        "phet_io_support": "full",
        "screens": ["intro", "lab"],
        "key_phetio_ids": [
            "pendulum-lab.introScreen.model.pendulum.lengthProperty",
            "pendulum-lab.introScreen.model.pendulum.periodProperty"
        ],
        "difficulty": "medium",
        "grade_levels": ["9-12", "college"]
    }
}


# =============================================================================
# SELECTION PROMPT
# =============================================================================

PHET_SELECTOR_PROMPT = """You are an expert educational technology specialist selecting the optimal PhET simulation for a learning activity.

## Question/Learning Context:
{question_text}

## Answer Options (if any):
{question_options}

## Pedagogical Context:
- Bloom's Level: {blooms_level}
- Subject/Domain: {subject}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}
- Key Concepts: {key_concepts}
- Target Grade Level: {grade_level}

## Available PhET Simulations:

{simulation_catalog}

## Selection Criteria:

1. **Concept Alignment** (40%): How well do the simulation's concepts match the learning objectives?
2. **Bloom's Level Match** (25%): Does the simulation support the target cognitive level?
3. **Interaction Fit** (20%): Can the simulation's interactions address the question type?
4. **Difficulty Appropriateness** (15%): Is the simulation suitable for the target audience?

## Response Format (JSON):
{{
    "selected_simulation": "<simulation-id>",
    "confidence": <0.0-1.0>,
    "reasoning": "<2-3 sentences explaining why this simulation is optimal>",
    "concept_alignment_score": <0.0-1.0>,
    "blooms_alignment_score": <0.0-1.0>,
    "interaction_fit_score": <0.0-1.0>,
    "difficulty_fit_score": <0.0-1.0>,
    "recommended_screen": "<screen-name or null>",
    "customization_suggestions": [
        "<suggestion 1>",
        "<suggestion 2>"
    ],
    "alternative_simulations": [
        {{
            "simulation_id": "<alternative-id>",
            "reason": "<why this could also work>"
        }}
    ]
}}

Respond with ONLY valid JSON."""


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================

@dataclass
class PhetSelectionResult:
    """Result of PhET simulation selection"""
    simulation_id: str
    simulation_metadata: Dict[str, Any]
    confidence: float
    reasoning: str
    concept_alignment_score: float
    blooms_alignment_score: float
    interaction_fit_score: float
    difficulty_fit_score: float
    recommended_screen: Optional[str]
    customization_suggestions: List[str]
    alternative_simulations: List[Dict[str, str]]


def _build_simulation_catalog_text() -> str:
    """Build formatted catalog text for the prompt"""
    lines = []
    for sim_id, meta in PHET_SIMULATION_CATALOG.items():
        lines.append(f"### {meta['title']} ({sim_id})")
        lines.append(f"Description: {meta['description']}")
        lines.append(f"Concepts: {', '.join(meta['concepts'][:5])}...")
        lines.append(f"Bloom's: {', '.join(meta['blooms_levels'])}")
        lines.append(f"Interactions: {', '.join(meta['interaction_types'])}")
        lines.append(f"Difficulty: {meta['difficulty']}")
        lines.append(f"Grade Levels: {', '.join(meta['grade_levels'])}")
        lines.append("")
    return "\n".join(lines)


def _match_concepts_heuristic(
    key_concepts: List[str],
    target_concepts: List[str]
) -> float:
    """Simple heuristic for concept matching"""
    if not key_concepts or not target_concepts:
        return 0.5

    key_lower = [c.lower() for c in key_concepts]
    target_lower = [c.lower() for c in target_concepts]

    matches = 0
    for concept in key_lower:
        for target in target_lower:
            if concept in target or target in concept:
                matches += 1
                break

    return min(1.0, matches / len(key_lower)) if key_lower else 0.5


def _find_best_simulation_heuristic(
    ped_context: Dict[str, Any]
) -> PhetSelectionResult:
    """Fallback heuristic selection when LLM is unavailable"""
    key_concepts = ped_context.get("key_concepts", [])
    subject = ped_context.get("subject", "").lower()
    blooms = ped_context.get("blooms_level", "understand")

    best_sim = None
    best_score = 0.0

    for sim_id, meta in PHET_SIMULATION_CATALOG.items():
        # Calculate composite score
        concept_score = _match_concepts_heuristic(key_concepts, meta["concepts"])

        blooms_score = 1.0 if blooms in meta["blooms_levels"] else 0.5

        domain_score = 1.0 if any(
            d.lower() in subject for d in meta["domains"]
        ) else 0.5

        composite = (
            concept_score * 0.4 +
            blooms_score * 0.3 +
            domain_score * 0.3
        )

        if composite > best_score:
            best_score = composite
            best_sim = sim_id

    # Default to projectile-motion if nothing matches well
    if best_sim is None:
        best_sim = "projectile-motion"
        best_score = 0.5

    return PhetSelectionResult(
        simulation_id=best_sim,
        simulation_metadata=PHET_SIMULATION_CATALOG[best_sim],
        confidence=best_score,
        reasoning="Heuristic selection based on concept and domain matching",
        concept_alignment_score=best_score,
        blooms_alignment_score=0.7,
        interaction_fit_score=0.7,
        difficulty_fit_score=0.7,
        recommended_screen=PHET_SIMULATION_CATALOG[best_sim]["screens"][0],
        customization_suggestions=[],
        alternative_simulations=[]
    )


async def phet_simulation_selector_agent(
    state: Dict[str, Any],
    ctx: Optional[Any] = None
) -> Dict[str, Any]:
    """
    PhET Simulation Selector Agent

    Analyzes pedagogical context to select the optimal PhET simulation
    for the learning activity.

    Args:
        state: Current agent state with question and pedagogical_context
        ctx: Optional instrumentation context

    Returns:
        Updated state with phet_selection containing simulation details
    """
    logger.info(f"PhET Selector: Processing question {state.get('question_id', 'unknown')}")

    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    ped_context = state.get("pedagogical_context", {})

    if not question_text:
        logger.error("PhET Selector: No question text")
        return {
            **state,
            "current_agent": "phet_simulation_selector",
            "error_message": "No question text for PhET selection"
        }

    # Build prompt
    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"

    prompt = PHET_SELECTOR_PROMPT.format(
        question_text=question_text,
        question_options=options_str,
        blooms_level=ped_context.get("blooms_level", "understand"),
        subject=ped_context.get("subject", "General"),
        difficulty=ped_context.get("difficulty", "intermediate"),
        learning_objectives=json.dumps(ped_context.get("learning_objectives", [])),
        key_concepts=json.dumps(ped_context.get("key_concepts", [])),
        grade_level=ped_context.get("grade_level", "9-12"),
        simulation_catalog=_build_simulation_catalog_text()
    )

    try:
        # In production, use LLM service
        # llm = get_llm_service()
        # result = await llm.generate_json_for_agent(
        #     agent_name="phet_simulation_selector",
        #     prompt=prompt,
        #     schema_hint="PhetSelection JSON with selected_simulation, confidence, reasoning"
        # )

        # For now, use heuristic fallback
        logger.info("PhET Selector: Using heuristic selection (LLM not connected)")
        selection = _find_best_simulation_heuristic(ped_context)

        result = {
            "selected_simulation": selection.simulation_id,
            "confidence": selection.confidence,
            "reasoning": selection.reasoning,
            "concept_alignment_score": selection.concept_alignment_score,
            "blooms_alignment_score": selection.blooms_alignment_score,
            "interaction_fit_score": selection.interaction_fit_score,
            "difficulty_fit_score": selection.difficulty_fit_score,
            "recommended_screen": selection.recommended_screen,
            "customization_suggestions": selection.customization_suggestions,
            "alternative_simulations": selection.alternative_simulations
        }

        logger.info(
            f"PhET Selector: Selected {result['selected_simulation']} "
            f"with confidence {result['confidence']:.2f}"
        )

        return {
            **state,
            "phet_selection": {
                **result,
                "simulation_metadata": PHET_SIMULATION_CATALOG.get(
                    result["selected_simulation"], {}
                )
            },
            "current_agent": "phet_simulation_selector"
        }

    except Exception as e:
        logger.error(f"PhET Selector: Error: {e}", exc_info=True)

        # Use heuristic fallback
        selection = _find_best_simulation_heuristic(ped_context)

        return {
            **state,
            "phet_selection": {
                "selected_simulation": selection.simulation_id,
                "simulation_metadata": selection.simulation_metadata,
                "confidence": selection.confidence,
                "reasoning": f"Fallback selection: {selection.reasoning}",
                "recommended_screen": selection.recommended_screen
            },
            "current_agent": "phet_simulation_selector",
            "error_message": f"PhET Selector fallback: {str(e)}"
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_simulation_by_concept(concept: str) -> List[str]:
    """Find simulations that cover a specific concept"""
    concept_lower = concept.lower()
    matches = []

    for sim_id, meta in PHET_SIMULATION_CATALOG.items():
        for sim_concept in meta["concepts"]:
            if concept_lower in sim_concept.lower():
                matches.append(sim_id)
                break

    return matches


def get_simulation_by_domain(domain: str) -> List[str]:
    """Find simulations in a specific domain"""
    domain_lower = domain.lower()
    return [
        sim_id for sim_id, meta in PHET_SIMULATION_CATALOG.items()
        if domain_lower in [d.lower() for d in meta["domains"]]
    ]


def get_simulation_phetio_ids(simulation_id: str) -> List[str]:
    """Get key phetioIDs for a simulation"""
    meta = PHET_SIMULATION_CATALOG.get(simulation_id, {})
    return meta.get("key_phetio_ids", [])


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio

    # Test with sample input
    test_state = {
        "question_id": "test-001",
        "question_text": "What factors affect the trajectory of a projectile? How does changing the launch angle impact the range?",
        "question_options": [],
        "pedagogical_context": {
            "blooms_level": "apply",
            "subject": "Physics",
            "difficulty": "intermediate",
            "learning_objectives": [
                "Understand projectile motion",
                "Analyze the effect of launch angle on range"
            ],
            "key_concepts": ["projectile", "trajectory", "angle", "range", "gravity"],
            "grade_level": "9-12"
        }
    }

    async def test():
        result = await phet_simulation_selector_agent(test_state)
        print(f"Selected: {result['phet_selection']['selected_simulation']}")
        print(f"Confidence: {result['phet_selection']['confidence']:.2f}")
        print(f"Reasoning: {result['phet_selection']['reasoning']}")

    asyncio.run(test())
