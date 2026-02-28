# PhET Simulation Template - Complete Architecture Design

Following the LABEL_DIAGRAM pattern exactly, this document provides the complete architecture for the PHET_SIMULATION template.

---

## Overview: Agent Pipeline

```
Input Enhancer
    ↓
Domain Knowledge Retriever
    ↓
Router (→ selects PHET_SIMULATION)
    ↓
┌────────────────────────────────────────────────┐
│        PHET_SIMULATION PIPELINE                │
├────────────────────────────────────────────────┤
│                                                │
│  PhET Simulation Selector                      │
│    ↓                                           │
│  PhET Game Planner                             │
│    ↓                                           │
│  PhET Assessment Designer                      │
│    ↓                                           │
│  PhET Blueprint Generator                      │
│    ↓                                           │
│  PhET Blueprint Validator (retry loop)         │
│    ↓                                           │
│  PhET Bridge Config Generator                  │
│                                                │
└────────────────────────────────────────────────┘
    ↓
END (Blueprint Ready)
```

---

## 1. SCHEMA DEFINITION

### File: `backend/app/agents/schemas/phet_simulation.py`

```python
"""
PhET Simulation Blueprint Schema

Defines the complete structure for PHET_SIMULATION template games.
Follows the same pattern as label_diagram.py
"""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class PhetSimulationId(str, Enum):
    """Available PhET simulations"""
    PROJECTILE_MOTION = "projectile-motion"
    CIRCUIT_CONSTRUCTION_KIT_DC = "circuit-construction-kit-dc"
    STATES_OF_MATTER = "states-of-matter"
    GRAPHING_QUADRATICS = "graphing-quadratics"
    FRICTION = "friction"
    PENDULUM_LAB = "pendulum-lab"
    BUILD_AN_ATOM = "build-an-atom"
    MOLECULE_POLARITY = "molecule-polarity"
    PH_SCALE = "ph-scale"
    ENERGY_SKATE_PARK = "energy-skate-park"
    WAVES = "waves"
    GAS_PROPERTIES = "gas-properties"
    NATURAL_SELECTION = "natural-selection"
    BALANCING_CHEMICAL_EQUATIONS = "balancing-chemical-equations"
    VECTOR_ADDITION = "vector-addition"


class AssessmentType(str, Enum):
    """Types of assessments that can be created"""
    EXPLORATION = "exploration"           # Open-ended exploration with guided prompts
    PARAMETER_DISCOVERY = "parameter_discovery"  # Find relationships between parameters
    TARGET_ACHIEVEMENT = "target_achievement"    # Achieve specific outcomes
    PREDICTION_VERIFICATION = "prediction_verification"  # Predict → Test → Verify
    COMPARATIVE_ANALYSIS = "comparative_analysis"  # Compare different configurations
    OPTIMIZATION = "optimization"         # Find optimal values
    MEASUREMENT = "measurement"           # Take measurements and record data
    CONSTRUCTION = "construction"         # Build something (circuits, molecules)
    SEQUENCE_EXECUTION = "sequence_execution"  # Follow a procedure


class InteractionType(str, Enum):
    """Types of interactions users can have"""
    SLIDER_ADJUST = "slider_adjust"
    BUTTON_CLICK = "button_click"
    DRAG_DROP = "drag_drop"
    TOGGLE = "toggle"
    TEXT_INPUT = "text_input"
    SELECTION = "selection"
    MEASUREMENT = "measurement"
    DRAWING = "drawing"


class CheckpointConditionType(str, Enum):
    """Types of conditions for checkpoint evaluation"""
    PROPERTY_EQUALS = "property_equals"
    PROPERTY_RANGE = "property_range"
    PROPERTY_CHANGED = "property_changed"
    INTERACTION_OCCURRED = "interaction_occurred"
    OUTCOME_ACHIEVED = "outcome_achieved"
    TIME_SPENT = "time_spent"
    EXPLORATION_BREADTH = "exploration_breadth"
    SEQUENCE_COMPLETED = "sequence_completed"


# =============================================================================
# SIMULATION CONFIGURATION
# =============================================================================

class SimulationParameter(BaseModel):
    """A trackable parameter in the simulation"""
    model_config = ConfigDict(extra="forbid")

    phetioId: str = Field(description="PhET-iO ID for this parameter")
    name: str = Field(description="Human-readable name")
    type: Literal["number", "boolean", "string", "enum"]
    unit: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    enumValues: Optional[List[str]] = None
    defaultValue: Optional[Any] = None


class SimulationInteraction(BaseModel):
    """A trackable user interaction"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique interaction ID")
    type: InteractionType
    phetioId: str = Field(description="PhET-iO ID for the element")
    name: str = Field(description="Human-readable name")
    dataFields: Optional[List[str]] = Field(
        default=None,
        description="Data fields captured when this interaction occurs"
    )


class SimulationOutcome(BaseModel):
    """A measurable outcome from the simulation"""
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    phetioId: str
    unit: Optional[str] = None
    description: Optional[str] = None


class SimulationConfig(BaseModel):
    """Configuration for the PhET simulation"""
    model_config = ConfigDict(extra="forbid")

    simulationId: str = Field(description="PhET simulation identifier")
    version: str = Field(default="latest")
    screen: Optional[str] = Field(default=None, description="Specific screen to use")
    localPath: Optional[str] = Field(default=None, description="Path to self-hosted HTML")

    # Tracked elements (populated by PhET Bridge Config Generator)
    parameters: List[SimulationParameter] = Field(default_factory=list)
    interactions: List[SimulationInteraction] = Field(default_factory=list)
    outcomes: List[SimulationOutcome] = Field(default_factory=list)

    # Initial state
    initialState: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Initial parameter values to set on load"
    )

    # Hidden/disabled elements
    hiddenElements: Optional[List[str]] = Field(default=None)
    disabledElements: Optional[List[str]] = Field(default=None)


# =============================================================================
# ASSESSMENT & CHECKPOINTS
# =============================================================================

class CheckpointCondition(BaseModel):
    """Condition that must be met for checkpoint completion"""
    model_config = ConfigDict(extra="forbid")

    type: CheckpointConditionType

    # For property checks
    propertyId: Optional[str] = None
    operator: Optional[Literal["eq", "neq", "gt", "gte", "lt", "lte", "in_range"]] = None
    value: Optional[Any] = None
    minValue: Optional[float] = None
    maxValue: Optional[float] = None
    tolerance: Optional[float] = None

    # For interaction checks
    interactionId: Optional[str] = None
    interactionData: Optional[Dict[str, Any]] = None

    # For outcome checks
    outcomeId: Optional[str] = None

    # For time checks
    minSeconds: Optional[int] = None

    # For exploration breadth
    minUniqueValues: Optional[int] = None
    parameterIds: Optional[List[str]] = None

    # For sequence completion
    sequenceSteps: Optional[List[str]] = None


class Checkpoint(BaseModel):
    """A checkpoint that awards points when achieved"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    conditions: List[CheckpointCondition] = Field(min_length=1)
    conditionLogic: Literal["all", "any"] = Field(default="all")
    points: int = Field(ge=1, le=100)
    feedback: Optional[str] = None
    hint: Optional[str] = None

    # For sequential checkpoints
    requiresPrevious: Optional[str] = Field(
        default=None,
        description="ID of checkpoint that must be completed first"
    )


class AssessmentTask(BaseModel):
    """A task within the assessment"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: AssessmentType
    title: str = Field(min_length=1)
    instructions: str = Field(min_length=1)

    # Learning context
    learningObjective: Optional[str] = None
    bloomsLevel: Optional[Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]] = None

    # Checkpoints
    checkpoints: List[Checkpoint] = Field(min_length=1)

    # Hints (revealed progressively)
    hints: Optional[List[str]] = None

    # For prediction tasks
    prediction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Prediction question before exploration"
    )

    # For measurement tasks
    measurements: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Measurements to record"
    )

    # Task flow
    requiredToProceed: bool = True
    timeLimit: Optional[int] = Field(default=None, description="Time limit in seconds")

    # Post-task quiz
    quiz: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# SCORING
# =============================================================================

class ScoringRubric(BaseModel):
    """Scoring configuration"""
    model_config = ConfigDict(extra="forbid")

    maxScore: int = Field(ge=10, le=1000)

    # Bonuses
    explorationBonus: Optional[int] = Field(
        default=None,
        description="Bonus points for thorough exploration"
    )
    speedBonus: Optional[Dict[str, int]] = Field(
        default=None,
        description="Bonus for completing under time threshold"
    )

    # Penalties
    hintPenalty: Optional[int] = Field(default=2)
    incorrectAttemptPenalty: Optional[int] = Field(default=0)

    # Dimension weights (for multi-dimensional scoring)
    dimensions: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights for accuracy, exploration, efficiency"
    )


# =============================================================================
# ANIMATIONS & FEEDBACK
# =============================================================================

class AnimationSpec(BaseModel):
    """Animation specification"""
    model_config = ConfigDict(extra="allow")

    type: Literal["pulse", "glow", "scale", "shake", "fade", "bounce", "confetti", "highlight"]
    duration_ms: int = Field(ge=50, le=3000, default=400)
    color: Optional[str] = None
    intensity: Optional[float] = Field(default=1.0, ge=0.1, le=3.0)


class FeedbackMessages(BaseModel):
    """Feedback messages for different scenarios"""
    model_config = ConfigDict(extra="forbid")

    checkpointComplete: str = Field(default="Great job! Checkpoint completed.")
    taskComplete: str = Field(default="Task completed successfully!")
    incorrectAttempt: str = Field(default="Not quite. Try again!")
    hintUsed: str = Field(default="Here's a hint to help you.")
    gameComplete: Dict[str, str] = Field(
        default_factory=lambda: {
            "perfect": "Outstanding! You mastered this simulation!",
            "good": "Well done! You've shown good understanding.",
            "passing": "Good effort! Review the concepts and try again.",
            "retry": "Keep practicing! You'll get it!"
        }
    )


class StructuredAnimations(BaseModel):
    """Structured animation cues"""
    model_config = ConfigDict(extra="forbid")

    checkpointComplete: AnimationSpec = Field(
        default_factory=lambda: AnimationSpec(type="pulse", duration_ms=400, color="#22c55e")
    )
    incorrectAttempt: AnimationSpec = Field(
        default_factory=lambda: AnimationSpec(type="shake", duration_ms=300, color="#ef4444")
    )
    taskComplete: AnimationSpec = Field(
        default_factory=lambda: AnimationSpec(type="bounce", duration_ms=500, color="#3b82f6")
    )
    gameComplete: AnimationSpec = Field(
        default_factory=lambda: AnimationSpec(type="confetti", duration_ms=2000)
    )


# =============================================================================
# MAIN BLUEPRINT
# =============================================================================

class PhetSimulationBlueprint(BaseModel):
    """
    PHET_SIMULATION Blueprint Schema

    Defines the complete structure for a PhET simulation-based educational game.
    """
    model_config = ConfigDict(extra="forbid")

    # Template identification
    templateType: Literal["PHET_SIMULATION"]

    # Game metadata
    title: str = Field(min_length=1, max_length=100)
    narrativeIntro: str = Field(min_length=10, max_length=500)

    # Simulation configuration
    simulation: SimulationConfig

    # Assessment structure
    assessmentType: AssessmentType = Field(
        description="Primary assessment type for this game"
    )
    tasks: List[AssessmentTask] = Field(min_length=1, max_length=10)

    # Scoring
    scoring: ScoringRubric

    # Feedback & animations
    feedback: FeedbackMessages = Field(default_factory=FeedbackMessages)
    animations: StructuredAnimations = Field(default_factory=StructuredAnimations)

    # Learning context
    learningObjectives: List[str] = Field(min_length=1, max_length=5)
    targetBloomsLevel: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    estimatedMinutes: int = Field(ge=5, le=60, default=15)
    difficulty: Literal["easy", "medium", "hard"]

    # Bridge configuration (generated by PhET Bridge Config Generator)
    bridgeConfig: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for the GamED-PhET bridge module"
    )

    # Validation
    @model_validator(mode="after")
    def validate_checkpoint_references(self):
        """Ensure checkpoint dependencies are valid"""
        all_checkpoint_ids = set()
        for task in self.tasks:
            for cp in task.checkpoints:
                if cp.id in all_checkpoint_ids:
                    raise ValueError(f"Duplicate checkpoint ID: {cp.id}")
                all_checkpoint_ids.add(cp.id)

        # Validate requiresPrevious references
        for task in self.tasks:
            for cp in task.checkpoints:
                if cp.requiresPrevious and cp.requiresPrevious not in all_checkpoint_ids:
                    raise ValueError(
                        f"Checkpoint {cp.id} requires non-existent checkpoint {cp.requiresPrevious}"
                    )

        return self

    @model_validator(mode="after")
    def validate_scoring_total(self):
        """Ensure checkpoint points don't exceed maxScore"""
        total_points = sum(
            cp.points
            for task in self.tasks
            for cp in task.checkpoints
        )
        if total_points > self.scoring.maxScore:
            raise ValueError(
                f"Total checkpoint points ({total_points}) exceed maxScore ({self.scoring.maxScore})"
            )
        return self


# =============================================================================
# SIMULATION CATALOG
# =============================================================================

SIMULATION_CATALOG = {
    "projectile-motion": {
        "title": "Projectile Motion",
        "domains": ["physics"],
        "concepts": ["kinematics", "trajectory", "vectors", "gravity", "angle", "velocity"],
        "parameters": [
            {"phetioId": "projectile-motion.introScreen.model.cannonAngleProperty", "name": "Cannon Angle", "type": "number", "unit": "°", "min": 0, "max": 90},
            {"phetioId": "projectile-motion.introScreen.model.launchSpeedProperty", "name": "Launch Speed", "type": "number", "unit": "m/s", "min": 0, "max": 30},
            {"phetioId": "projectile-motion.introScreen.model.projectileMassProperty", "name": "Mass", "type": "number", "unit": "kg", "min": 1, "max": 100},
            {"phetioId": "projectile-motion.introScreen.model.gravityProperty", "name": "Gravity", "type": "number", "unit": "m/s²", "min": 1, "max": 30},
            {"phetioId": "projectile-motion.introScreen.model.airResistanceOnProperty", "name": "Air Resistance", "type": "boolean"},
        ],
        "interactions": [
            {"id": "launch", "type": "button_click", "phetioId": "projectile-motion.introScreen.view.fireButton", "name": "Fire Projectile", "dataFields": ["angle", "speed", "mass"]},
            {"id": "clear", "type": "button_click", "phetioId": "projectile-motion.introScreen.view.eraseButton", "name": "Clear Trajectories"},
        ],
        "outcomes": [
            {"id": "range", "name": "Range", "phetioId": "projectile-motion.introScreen.model.projectile.rangeProperty", "unit": "m"},
            {"id": "maxHeight", "name": "Max Height", "phetioId": "projectile-motion.introScreen.model.projectile.maxHeightProperty", "unit": "m"},
            {"id": "timeOfFlight", "name": "Time of Flight", "phetioId": "projectile-motion.introScreen.model.projectile.timeOfFlightProperty", "unit": "s"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "target_achievement", "prediction_verification", "optimization"],
        "screens": ["intro", "vectors", "drag", "lab"],
    },
    "circuit-construction-kit-dc": {
        "title": "Circuit Construction Kit: DC",
        "domains": ["physics"],
        "concepts": ["circuits", "voltage", "current", "resistance", "Ohm's law", "series", "parallel"],
        "parameters": [
            {"phetioId": "circuit-construction-kit-dc.introScreen.model.circuit.batteryVoltageProperty", "name": "Battery Voltage", "type": "number", "unit": "V", "min": 0, "max": 120},
        ],
        "interactions": [
            {"id": "addComponent", "type": "drag_drop", "phetioId": "circuit-construction-kit-dc.introScreen.view.toolbox", "name": "Add Component", "dataFields": ["componentType"]},
            {"id": "connect", "type": "drag_drop", "phetioId": "circuit-construction-kit-dc.introScreen.model.circuit", "name": "Connect Wire"},
        ],
        "outcomes": [
            {"id": "totalCurrent", "name": "Circuit Current", "phetioId": "circuit-construction-kit-dc.introScreen.model.circuit.currentProperty", "unit": "A"},
            {"id": "totalResistance", "name": "Total Resistance", "phetioId": "circuit-construction-kit-dc.introScreen.model.circuit.resistanceProperty", "unit": "Ω"},
        ],
        "assessmentTypes": ["construction", "measurement", "exploration", "comparative_analysis"],
        "screens": ["intro", "lab"],
    },
    "states-of-matter": {
        "title": "States of Matter",
        "domains": ["chemistry", "physics"],
        "concepts": ["phases", "temperature", "molecular motion", "kinetic energy", "phase transitions"],
        "parameters": [
            {"phetioId": "states-of-matter.statesScreen.model.temperatureProperty", "name": "Temperature", "type": "number", "unit": "K", "min": 0, "max": 1000},
            {"phetioId": "states-of-matter.statesScreen.model.moleculeTypeProperty", "name": "Molecule Type", "type": "enum", "enumValues": ["neon", "argon", "oxygen", "water"]},
        ],
        "interactions": [
            {"id": "heat", "type": "button_click", "phetioId": "states-of-matter.statesScreen.view.heatCoolButtons.heatButton", "name": "Add Heat"},
            {"id": "cool", "type": "button_click", "phetioId": "states-of-matter.statesScreen.view.heatCoolButtons.coolButton", "name": "Remove Heat"},
        ],
        "outcomes": [
            {"id": "phase", "name": "Current Phase", "phetioId": "states-of-matter.statesScreen.model.phaseProperty"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "prediction_verification", "sequence_execution"],
        "screens": ["states", "phase-changes"],
    },
    "graphing-quadratics": {
        "title": "Graphing Quadratics",
        "domains": ["mathematics"],
        "concepts": ["parabola", "quadratic", "vertex", "roots", "coefficients", "axis of symmetry"],
        "parameters": [
            {"phetioId": "graphing-quadratics.exploreScreen.model.aProperty", "name": "Coefficient a", "type": "number", "min": -6, "max": 6, "step": 0.25},
            {"phetioId": "graphing-quadratics.exploreScreen.model.bProperty", "name": "Coefficient b", "type": "number", "min": -6, "max": 6, "step": 0.25},
            {"phetioId": "graphing-quadratics.exploreScreen.model.cProperty", "name": "Coefficient c", "type": "number", "min": -6, "max": 6, "step": 0.25},
        ],
        "interactions": [],
        "outcomes": [
            {"id": "vertex", "name": "Vertex", "phetioId": "graphing-quadratics.exploreScreen.model.vertexProperty"},
            {"id": "roots", "name": "Roots", "phetioId": "graphing-quadratics.exploreScreen.model.rootsProperty"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "prediction_verification", "target_achievement"],
        "screens": ["explore", "standard-form", "vertex-form"],
    },
    "pendulum-lab": {
        "title": "Pendulum Lab",
        "domains": ["physics"],
        "concepts": ["pendulum", "period", "frequency", "gravity", "length", "simple harmonic motion"],
        "parameters": [
            {"phetioId": "pendulum-lab.introScreen.model.pendulum.lengthProperty", "name": "Length", "type": "number", "unit": "m", "min": 0.1, "max": 2},
            {"phetioId": "pendulum-lab.introScreen.model.pendulum.massProperty", "name": "Mass", "type": "number", "unit": "kg", "min": 0.1, "max": 1.5},
            {"phetioId": "pendulum-lab.introScreen.model.gravityProperty", "name": "Gravity", "type": "number", "unit": "m/s²", "min": 1, "max": 25},
        ],
        "interactions": [
            {"id": "release", "type": "button_click", "phetioId": "pendulum-lab.introScreen.view.playPauseButton", "name": "Start/Stop"},
        ],
        "outcomes": [
            {"id": "period", "name": "Period", "phetioId": "pendulum-lab.introScreen.model.pendulum.periodProperty", "unit": "s"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "measurement", "prediction_verification"],
        "screens": ["intro", "lab"],
    },
    "friction": {
        "title": "Friction",
        "domains": ["physics"],
        "concepts": ["friction", "static friction", "kinetic friction", "forces", "motion"],
        "parameters": [
            {"phetioId": "friction.frictionScreen.model.appliedForceProperty", "name": "Applied Force", "type": "number", "unit": "N", "min": 0, "max": 500},
        ],
        "interactions": [
            {"id": "push", "type": "slider_adjust", "phetioId": "friction.frictionScreen.view.appliedForceSlider", "name": "Adjust Force"},
        ],
        "outcomes": [
            {"id": "frictionForce", "name": "Friction Force", "phetioId": "friction.frictionScreen.model.frictionForceProperty", "unit": "N"},
            {"id": "isMoving", "name": "Object Moving", "phetioId": "friction.frictionScreen.model.isMovingProperty"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "prediction_verification"],
        "screens": ["friction"],
    },
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_phet_blueprint(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a PHET_SIMULATION blueprint"""
    errors = []
    warnings = []

    # Check template type
    if blueprint.get("templateType") != "PHET_SIMULATION":
        errors.append("templateType must be 'PHET_SIMULATION'")
        return {"valid": False, "errors": errors, "warnings": [], "validated_blueprint": None}

    # Check simulation exists in catalog
    sim_id = blueprint.get("simulation", {}).get("simulationId")
    if sim_id and sim_id not in SIMULATION_CATALOG:
        warnings.append(f"Simulation '{sim_id}' not in catalog. Verify it exists.")

    try:
        validated = PhetSimulationBlueprint.model_validate(blueprint)
        return {
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "validated_blueprint": validated.model_dump()
        }
    except Exception as e:
        errors.append(f"Schema validation failed: {str(e)}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "validated_blueprint": None
        }
```

---

## 2. AGENT DEFINITIONS

### Agent 1: PhET Simulation Selector

**File:** `backend/app/agents/phet_simulation_selector.py`

**Purpose:** Select the most appropriate PhET simulation based on question and pedagogical context.

**Input State Keys:**
- `question_text`: The question/topic
- `pedagogical_context`: Bloom's level, subject, concepts
- `domain_knowledge`: Retrieved domain information

**Output State Keys:**
- `phet_selection`: Selected simulation with confidence and reasoning

```python
"""
PhET Simulation Selector Agent

Selects the optimal PhET simulation for the given learning context.
"""

from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.schemas.phet_simulation import SIMULATION_CATALOG

PHET_SELECTOR_PROMPT = """You are an expert educational technology specialist. Select the optimal PhET simulation for this learning activity.

## Question/Topic:
{question_text}

## Pedagogical Context:
- Subject: {subject}
- Bloom's Level: {blooms_level}
- Key Concepts: {key_concepts}
- Difficulty: {difficulty}

## Available Simulations:

{simulation_catalog}

## Selection Criteria:
1. Concept Match (40%): How well do simulation concepts align with question concepts?
2. Bloom's Alignment (25%): Does simulation support the target cognitive level?
3. Interaction Fit (20%): Can simulation interactions address the question type?
4. Assessment Fit (15%): What assessment types work well with this simulation?

## Response (JSON only):
{{
    "simulationId": "<simulation-id>",
    "confidence": <0.0-1.0>,
    "reasoning": "<2-3 sentences>",
    "recommendedScreen": "<screen-name or null>",
    "recommendedAssessmentTypes": ["<type1>", "<type2>"],
    "keyParameters": ["<param1>", "<param2>"],
    "keyOutcomes": ["<outcome1>", "<outcome2>"],
    "alternativeSimulation": "<backup-simulation-id or null>"
}}
"""


async def phet_simulation_selector_agent(state: AgentState) -> Dict[str, Any]:
    """Select optimal PhET simulation for the learning context."""

    question_text = state.get("question_text", "")
    ped_context = state.get("pedagogical_context", {})

    # Build catalog text for prompt
    catalog_text = _build_catalog_text()

    prompt = PHET_SELECTOR_PROMPT.format(
        question_text=question_text,
        subject=ped_context.get("subject", "General"),
        blooms_level=ped_context.get("blooms_level", "understand"),
        key_concepts=", ".join(ped_context.get("key_concepts", [])),
        difficulty=ped_context.get("difficulty", "medium"),
        simulation_catalog=catalog_text
    )

    # Call LLM
    result = await llm_service.generate_json(
        agent_name="phet_simulation_selector",
        prompt=prompt
    )

    # Enrich with catalog metadata
    sim_id = result.get("simulationId")
    if sim_id in SIMULATION_CATALOG:
        result["simulationMetadata"] = SIMULATION_CATALOG[sim_id]

    return {
        **state,
        "phet_selection": result,
        "current_agent": "phet_simulation_selector"
    }


def _build_catalog_text() -> str:
    """Build formatted catalog for prompt."""
    lines = []
    for sim_id, meta in SIMULATION_CATALOG.items():
        lines.append(f"### {meta['title']} ({sim_id})")
        lines.append(f"Domains: {', '.join(meta['domains'])}")
        lines.append(f"Concepts: {', '.join(meta['concepts'][:5])}")
        lines.append(f"Assessment Types: {', '.join(meta['assessmentTypes'])}")
        lines.append(f"Parameters: {', '.join(p['name'] for p in meta['parameters'][:3])}")
        lines.append("")
    return "\n".join(lines)
```

---

### Agent 2: PhET Game Planner

**File:** `backend/app/agents/phet_game_planner.py`

**Purpose:** Design the game mechanics, assessment strategy, and learning objectives.

**Input State Keys:**
- `question_text`
- `pedagogical_context`
- `phet_selection`: Selected simulation
- `domain_knowledge`

**Output State Keys:**
- `phet_game_plan`: Complete game plan with assessment strategy

```python
"""
PhET Game Planner Agent

Designs the assessment strategy and game mechanics for a PhET simulation.
"""

PHET_GAME_PLANNER_PROMPT = """You are an expert instructional designer creating an assessment for a PhET simulation.

## Learning Context:
Question: {question_text}
Subject: {subject}
Bloom's Level: {blooms_level}
Key Concepts: {key_concepts}
Difficulty: {difficulty}

## Selected Simulation:
Simulation: {simulation_title} ({simulation_id})
Available Parameters: {parameters}
Available Outcomes: {outcomes}
Supported Assessment Types: {assessment_types}

## Your Task:
Design an effective assessment that uses this simulation to help students learn the target concepts.

## Assessment Type Guidelines:

### EXPLORATION
- Open-ended discovery with guided prompts
- Reward trying different parameter values
- Checkpoints for breadth of exploration

### PARAMETER_DISCOVERY
- Find relationships between parameters
- "What happens when X changes?"
- Checkpoints for discovering specific relationships

### TARGET_ACHIEVEMENT
- Achieve specific outcomes
- "Make the projectile land at 50 meters"
- Checkpoints for hitting targets

### PREDICTION_VERIFICATION
- Predict → Test → Verify cycle
- "Predict what will happen, then test it"
- Checkpoints for making predictions AND verifying

### OPTIMIZATION
- Find optimal values
- "Find the angle that maximizes range"
- Checkpoints for approaching optimal

### MEASUREMENT
- Take measurements and record data
- "Measure the period for 3 different lengths"
- Checkpoints for completing measurements

### COMPARATIVE_ANALYSIS
- Compare configurations
- "Compare series vs parallel circuits"
- Checkpoints for trying both configurations

### CONSTRUCTION
- Build something
- "Build a circuit with 2 bulbs in series"
- Checkpoints for assembly steps

## Response (JSON only):
{{
    "assessmentType": "<primary_assessment_type>",
    "learningObjectives": ["<objective1>", "<objective2>", "<objective3>"],
    "taskSequence": [
        {{
            "type": "<task_type>",
            "title": "<task_title>",
            "description": "<what_student_does>",
            "checkpointIdeas": ["<checkpoint1>", "<checkpoint2>"],
            "estimatedMinutes": <minutes>
        }}
    ],
    "scoringStrategy": {{
        "maxScore": <total_points>,
        "explorationWeight": <0-1>,
        "accuracyWeight": <0-1>,
        "efficiencyWeight": <0-1>
    }},
    "difficultyProgression": "<how_difficulty_increases>",
    "feedbackStrategy": "<when_and_how_to_give_feedback>",
    "keyParametersToTrack": ["<param1>", "<param2>"],
    "keyOutcomesToMeasure": ["<outcome1>", "<outcome2>"],
    "commonMisconceptions": ["<misconception1>", "<misconception2>"],
    "hintsStrategy": "<progressive_hint_approach>"
}}
"""


async def phet_game_planner_agent(state: AgentState) -> Dict[str, Any]:
    """Design game mechanics and assessment strategy."""

    phet_selection = state.get("phet_selection", {})
    sim_metadata = phet_selection.get("simulationMetadata", {})
    ped_context = state.get("pedagogical_context", {})

    prompt = PHET_GAME_PLANNER_PROMPT.format(
        question_text=state.get("question_text", ""),
        subject=ped_context.get("subject", ""),
        blooms_level=ped_context.get("blooms_level", ""),
        key_concepts=", ".join(ped_context.get("key_concepts", [])),
        difficulty=ped_context.get("difficulty", "medium"),
        simulation_title=sim_metadata.get("title", ""),
        simulation_id=phet_selection.get("simulationId", ""),
        parameters=_format_parameters(sim_metadata.get("parameters", [])),
        outcomes=_format_outcomes(sim_metadata.get("outcomes", [])),
        assessment_types=", ".join(sim_metadata.get("assessmentTypes", []))
    )

    result = await llm_service.generate_json(
        agent_name="phet_game_planner",
        prompt=prompt
    )

    return {
        **state,
        "phet_game_plan": result,
        "current_agent": "phet_game_planner"
    }
```

---

### Agent 3: PhET Assessment Designer

**File:** `backend/app/agents/phet_assessment_designer.py`

**Purpose:** Create detailed checkpoints with specific conditions based on the game plan.

**Input State Keys:**
- `phet_selection`
- `phet_game_plan`
- `pedagogical_context`

**Output State Keys:**
- `phet_assessment_design`: Detailed checkpoints and conditions

```python
"""
PhET Assessment Designer Agent

Creates detailed checkpoint conditions for assessment.
"""

PHET_ASSESSMENT_DESIGNER_PROMPT = """You are an expert assessment designer creating specific, measurable checkpoints for a PhET simulation assessment.

## Game Plan:
Assessment Type: {assessment_type}
Learning Objectives: {learning_objectives}
Task Sequence: {task_sequence}

## Simulation Capabilities:
Parameters (trackable values):
{parameters}

Outcomes (measurable results):
{outcomes}

## Checkpoint Condition Types:
- PROPERTY_EQUALS: Check if a property equals a specific value
- PROPERTY_RANGE: Check if a property is within a range
- PROPERTY_CHANGED: Check if a property was changed from default
- INTERACTION_OCCURRED: Check if user performed an interaction
- OUTCOME_ACHIEVED: Check if simulation produced specific outcome
- TIME_SPENT: Check if user spent minimum time
- EXPLORATION_BREADTH: Check if user tried multiple values
- SEQUENCE_COMPLETED: Check if steps were done in order

## Create Checkpoints:

For each task in the sequence, create 2-4 specific checkpoints with exact conditions.

Example checkpoint for "Set angle to 45°":
{{
    "id": "cp-angle-45",
    "description": "Set the cannon angle to 45 degrees",
    "conditions": [
        {{
            "type": "PROPERTY_RANGE",
            "propertyId": "cannonAngle",
            "minValue": 43,
            "maxValue": 47
        }}
    ],
    "points": 10,
    "hint": "Use the angle slider on the left side of the cannon"
}}

Example checkpoint for "Fire a projectile":
{{
    "id": "cp-fire-projectile",
    "description": "Fire a projectile",
    "conditions": [
        {{
            "type": "INTERACTION_OCCURRED",
            "interactionId": "launch"
        }}
    ],
    "points": 5
}}

Example checkpoint for "Achieve range > 40m":
{{
    "id": "cp-range-40",
    "description": "Make the projectile travel more than 40 meters",
    "conditions": [
        {{
            "type": "OUTCOME_ACHIEVED",
            "outcomeId": "range",
            "operator": "gt",
            "value": 40
        }}
    ],
    "points": 20,
    "hint": "Try using the optimal angle of 45 degrees"
}}

## Response (JSON only):
{{
    "tasks": [
        {{
            "id": "<task_id>",
            "type": "<assessment_type>",
            "title": "<title>",
            "instructions": "<detailed_instructions>",
            "learningObjective": "<specific_objective>",
            "checkpoints": [
                {{
                    "id": "<unique_id>",
                    "description": "<what_to_achieve>",
                    "conditions": [<condition_objects>],
                    "conditionLogic": "all" | "any",
                    "points": <1-50>,
                    "hint": "<helpful_hint>",
                    "feedback": "<success_message>"
                }}
            ],
            "hints": ["<hint1>", "<hint2>"],
            "prediction": null | {{ "question": "<predict_question>", "options": ["<opt1>", "<opt2>"] }},
            "quiz": null | [{{ "question": "<q>", "options": ["<o1>", "<o2>"], "correct": "<answer>" }}]
        }}
    ],
    "totalPoints": <sum_of_all_checkpoint_points>
}}
"""


async def phet_assessment_designer_agent(state: AgentState) -> Dict[str, Any]:
    """Create detailed assessment checkpoints with conditions."""

    phet_selection = state.get("phet_selection", {})
    phet_game_plan = state.get("phet_game_plan", {})
    sim_metadata = phet_selection.get("simulationMetadata", {})

    prompt = PHET_ASSESSMENT_DESIGNER_PROMPT.format(
        assessment_type=phet_game_plan.get("assessmentType", ""),
        learning_objectives="\n".join(f"- {obj}" for obj in phet_game_plan.get("learningObjectives", [])),
        task_sequence=_format_task_sequence(phet_game_plan.get("taskSequence", [])),
        parameters=_format_parameters_detailed(sim_metadata.get("parameters", [])),
        outcomes=_format_outcomes_detailed(sim_metadata.get("outcomes", []))
    )

    result = await llm_service.generate_json(
        agent_name="phet_assessment_designer",
        prompt=prompt
    )

    return {
        **state,
        "phet_assessment_design": result,
        "current_agent": "phet_assessment_designer"
    }
```

---

### Agent 4: PhET Blueprint Generator

**File:** `backend/app/agents/phet_blueprint_generator.py`

**Purpose:** Generate the complete blueprint JSON from all upstream agent outputs.

**Input State Keys:**
- `question_text`
- `pedagogical_context`
- `phet_selection`
- `phet_game_plan`
- `phet_assessment_design`
- `current_validation_errors` (for retries)

**Output State Keys:**
- `blueprint`: Complete PhetSimulationBlueprint

```python
"""
PhET Blueprint Generator Agent

Generates the complete PHET_SIMULATION blueprint.
"""

PHET_BLUEPRINT_GENERATOR_PROMPT = """You are generating a complete PHET_SIMULATION blueprint.

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

1. templateType: Must be "PHET_SIMULATION"

2. simulation: SimulationConfig
   - simulationId: From selection
   - screen: Recommended screen
   - parameters: List of trackable parameters
   - interactions: List of trackable interactions
   - outcomes: List of measurable outcomes
   - initialState: Optional starting values

3. tasks: Array of AssessmentTask
   - Each task has id, type, title, instructions
   - Each task has checkpoints with conditions
   - Conditions must use valid propertyId/interactionId/outcomeId

4. scoring: ScoringRubric
   - maxScore: Sum of all checkpoint points
   - Optional bonuses and penalties

5. feedback & animations: Use defaults or customize

## CRITICAL RULES:
- All propertyId values must exist in simulation.parameters
- All interactionId values must exist in simulation.interactions
- All outcomeId values must exist in simulation.outcomes
- Checkpoint IDs must be unique across all tasks
- Total checkpoint points must not exceed maxScore
- Use exact phetioId values from the simulation catalog

## Response: Output ONLY valid JSON matching PhetSimulationBlueprint schema.
"""


async def phet_blueprint_generator_agent(state: AgentState) -> Dict[str, Any]:
    """Generate complete PhET blueprint."""

    phet_selection = state.get("phet_selection", {})
    phet_game_plan = state.get("phet_game_plan", {})
    phet_assessment_design = state.get("phet_assessment_design", {})
    validation_errors = state.get("current_validation_errors", [])
    ped_context = state.get("pedagogical_context", {})

    prompt = PHET_BLUEPRINT_GENERATOR_PROMPT.format(
        question_text=state.get("question_text", ""),
        subject=ped_context.get("subject", ""),
        blooms_level=ped_context.get("blooms_level", ""),
        difficulty=ped_context.get("difficulty", ""),
        simulation_info=_format_simulation_info(phet_selection),
        game_plan=json.dumps(phet_game_plan, indent=2),
        assessment_design=json.dumps(phet_assessment_design, indent=2),
        validation_errors="\n".join(f"- {e}" for e in validation_errors) if validation_errors else "None"
    )

    result = await llm_service.generate_json(
        agent_name="phet_blueprint_generator",
        prompt=prompt,
        schema_hint="PhetSimulationBlueprint"
    )

    # Ensure templateType is set
    result["templateType"] = "PHET_SIMULATION"

    return {
        **state,
        "blueprint": result,
        "current_agent": "phet_blueprint_generator"
    }
```

---

### Agent 5: PhET Blueprint Validator

**File:** `backend/app/agents/phet_blueprint_validator.py`

**Purpose:** Validate blueprint against schema and semantic rules.

```python
"""
PhET Blueprint Validator Agent
"""

from app.agents.schemas.phet_simulation import validate_phet_blueprint, SIMULATION_CATALOG


async def phet_blueprint_validator_agent(state: AgentState) -> Dict[str, Any]:
    """Validate PhET blueprint."""

    blueprint = state.get("blueprint", {})
    retry_counts = state.get("retry_counts", {})

    # Schema validation
    result = validate_phet_blueprint(blueprint)

    if not result["valid"]:
        # Increment retry count
        current_retries = retry_counts.get("phet_blueprint_generator", 0)

        if current_retries < 3:
            return {
                **state,
                "validation_results": {"phet_blueprint": result},
                "current_validation_errors": result["errors"],
                "retry_counts": {
                    **retry_counts,
                    "phet_blueprint_generator": current_retries + 1
                },
                "current_agent": "phet_blueprint_validator",
                "_route_to": "phet_blueprint_generator"  # Retry
            }
        else:
            # Max retries, use fallback
            fallback_blueprint = _create_fallback_blueprint(state)
            return {
                **state,
                "blueprint": fallback_blueprint,
                "validation_results": {"phet_blueprint": {"valid": True, "used_fallback": True}},
                "current_agent": "phet_blueprint_validator"
            }

    # Semantic validation
    semantic_errors = _validate_semantics(blueprint)
    if semantic_errors:
        result["errors"].extend(semantic_errors)
        result["valid"] = False

        current_retries = retry_counts.get("phet_blueprint_generator", 0)
        if current_retries < 3:
            return {
                **state,
                "validation_results": {"phet_blueprint": result},
                "current_validation_errors": semantic_errors,
                "retry_counts": {
                    **retry_counts,
                    "phet_blueprint_generator": current_retries + 1
                },
                "current_agent": "phet_blueprint_validator",
                "_route_to": "phet_blueprint_generator"
            }

    return {
        **state,
        "validation_results": {"phet_blueprint": result},
        "current_validation_errors": [],
        "current_agent": "phet_blueprint_validator"
    }


def _validate_semantics(blueprint: Dict) -> List[str]:
    """Additional semantic validation beyond schema."""
    errors = []

    sim_config = blueprint.get("simulation", {})
    sim_id = sim_config.get("simulationId")

    if sim_id not in SIMULATION_CATALOG:
        return errors  # Can't validate against unknown simulation

    catalog_entry = SIMULATION_CATALOG[sim_id]
    valid_param_ids = {p["phetioId"] for p in catalog_entry.get("parameters", [])}
    valid_outcome_ids = {o["phetioId"] for o in catalog_entry.get("outcomes", [])}
    valid_interaction_ids = {i["id"] for i in catalog_entry.get("interactions", [])}

    # Check all checkpoint conditions reference valid IDs
    for task in blueprint.get("tasks", []):
        for checkpoint in task.get("checkpoints", []):
            for condition in checkpoint.get("conditions", []):
                cond_type = condition.get("type")

                if cond_type in ["PROPERTY_EQUALS", "PROPERTY_RANGE", "PROPERTY_CHANGED"]:
                    prop_id = condition.get("propertyId")
                    # Allow short names that match parameter names
                    if prop_id and not any(prop_id in pid for pid in valid_param_ids):
                        errors.append(f"Checkpoint {checkpoint['id']}: Unknown propertyId '{prop_id}'")

                elif cond_type == "INTERACTION_OCCURRED":
                    int_id = condition.get("interactionId")
                    if int_id and int_id not in valid_interaction_ids:
                        errors.append(f"Checkpoint {checkpoint['id']}: Unknown interactionId '{int_id}'")

                elif cond_type == "OUTCOME_ACHIEVED":
                    out_id = condition.get("outcomeId")
                    if out_id and not any(out_id in oid for oid in valid_outcome_ids):
                        errors.append(f"Checkpoint {checkpoint['id']}: Unknown outcomeId '{out_id}'")

    return errors
```

---

### Agent 6: PhET Bridge Config Generator

**File:** `backend/app/agents/phet_bridge_config_generator.py`

**Purpose:** Generate the configuration for the GamED-PhET bridge module.

**Input State Keys:**
- `blueprint`

**Output State Keys:**
- `blueprint.bridgeConfig`: Bridge configuration added to blueprint

```python
"""
PhET Bridge Config Generator Agent

Generates the bridge configuration for PhET-GamED communication.
"""

async def phet_bridge_config_generator_agent(state: AgentState) -> Dict[str, Any]:
    """Generate bridge configuration from blueprint."""

    blueprint = state.get("blueprint", {})
    sim_config = blueprint.get("simulation", {})
    sim_id = sim_config.get("simulationId")

    # Get catalog entry for phetioIds
    catalog_entry = SIMULATION_CATALOG.get(sim_id, {})

    # Build list of properties to track
    properties_to_track = []
    for param in catalog_entry.get("parameters", []):
        properties_to_track.append({
            "name": _to_short_name(param["phetioId"]),
            "phetioId": param["phetioId"],
            "type": param.get("type", "number")
        })

    # Build list of interactions to track
    interactions_to_track = []
    for interaction in catalog_entry.get("interactions", []):
        interactions_to_track.append({
            "id": interaction["id"],
            "phetioId": interaction["phetioId"],
            "type": interaction["type"],
            "dataFields": interaction.get("dataFields", [])
        })

    # Build list of outcomes to track
    outcomes_to_track = []
    for outcome in catalog_entry.get("outcomes", []):
        outcomes_to_track.append({
            "id": outcome["id"],
            "phetioId": outcome["phetioId"],
            "name": outcome["name"]
        })

    # Extract checkpoint conditions to determine what to monitor
    checkpoint_properties = set()
    checkpoint_interactions = set()
    checkpoint_outcomes = set()

    for task in blueprint.get("tasks", []):
        for checkpoint in task.get("checkpoints", []):
            for condition in checkpoint.get("conditions", []):
                if condition.get("propertyId"):
                    checkpoint_properties.add(condition["propertyId"])
                if condition.get("interactionId"):
                    checkpoint_interactions.add(condition["interactionId"])
                if condition.get("outcomeId"):
                    checkpoint_outcomes.add(condition["outcomeId"])

    bridge_config = {
        "simulationId": sim_id,
        "version": sim_config.get("version", "latest"),
        "localPath": sim_config.get("localPath"),

        # What to track
        "trackProperties": properties_to_track,
        "trackInteractions": interactions_to_track,
        "trackOutcomes": outcomes_to_track,

        # What checkpoints need
        "requiredProperties": list(checkpoint_properties),
        "requiredInteractions": list(checkpoint_interactions),
        "requiredOutcomes": list(checkpoint_outcomes),

        # Initial state
        "initialState": sim_config.get("initialState", {}),

        # Hidden/disabled elements
        "hiddenElements": sim_config.get("hiddenElements", []),
        "disabledElements": sim_config.get("disabledElements", []),

        # Communication config
        "messagePrefix": "PHET_",
        "debounceMs": 100,
        "batchUpdates": True
    }

    # Add bridge config to blueprint
    updated_blueprint = {**blueprint, "bridgeConfig": bridge_config}

    return {
        **state,
        "blueprint": updated_blueprint,
        "current_agent": "phet_bridge_config_generator",
        "generation_complete": True
    }
```

---

## 3. GRAPH DEFINITION

### File: `backend/app/agents/graph.py` (additions)

```python
# Add to existing graph definition

from app.agents.phet_simulation_selector import phet_simulation_selector_agent
from app.agents.phet_game_planner import phet_game_planner_agent
from app.agents.phet_assessment_designer import phet_assessment_designer_agent
from app.agents.phet_blueprint_generator import phet_blueprint_generator_agent
from app.agents.phet_blueprint_validator import phet_blueprint_validator_agent
from app.agents.phet_bridge_config_generator import phet_bridge_config_generator_agent


def route_after_router(state: AgentState) -> str:
    """Route to template-specific pipeline after router."""
    template = state.get("template_selection", {}).get("template_type")

    if template == "PHET_SIMULATION":
        return "phet_simulation_selector"
    elif template == "LABEL_DIAGRAM":
        return "label_diagram_pipeline"
    else:
        return "game_planner"


def route_after_phet_validator(state: AgentState) -> str:
    """Route after PhET blueprint validation."""
    route_to = state.get("_route_to")
    if route_to == "phet_blueprint_generator":
        return "phet_blueprint_generator"  # Retry
    return "phet_bridge_config_generator"  # Success


# Add nodes
graph.add_node("phet_simulation_selector", phet_simulation_selector_agent)
graph.add_node("phet_game_planner", phet_game_planner_agent)
graph.add_node("phet_assessment_designer", phet_assessment_designer_agent)
graph.add_node("phet_blueprint_generator", phet_blueprint_generator_agent)
graph.add_node("phet_blueprint_validator", phet_blueprint_validator_agent)
graph.add_node("phet_bridge_config_generator", phet_bridge_config_generator_agent)

# Add edges for PHET_SIMULATION pipeline
graph.add_conditional_edges("router", route_after_router, {
    "phet_simulation_selector": "phet_simulation_selector",
    "label_diagram_pipeline": "label_diagram_start",
    "game_planner": "game_planner"
})

graph.add_edge("phet_simulation_selector", "phet_game_planner")
graph.add_edge("phet_game_planner", "phet_assessment_designer")
graph.add_edge("phet_assessment_designer", "phet_blueprint_generator")
graph.add_edge("phet_blueprint_generator", "phet_blueprint_validator")

graph.add_conditional_edges("phet_blueprint_validator", route_after_phet_validator, {
    "phet_blueprint_generator": "phet_blueprint_generator",  # Retry
    "phet_bridge_config_generator": "phet_bridge_config_generator"
})

graph.add_edge("phet_bridge_config_generator", END)
```

---

## 4. PROMPTS

### File: `backend/prompts/blueprint_phet_simulation.txt`

```text
# PhET Simulation Blueprint Generation Guide

You are generating a PHET_SIMULATION blueprint for an interactive physics/chemistry/math assessment.

## Template Purpose

PHET_SIMULATION embeds a PhET Interactive Simulation (from University of Colorado Boulder)
and wraps it with assessment tasks, checkpoints, and scoring. Students interact with
the simulation while the system tracks their progress toward learning objectives.

## Assessment Types (Choose One Primary)

### EXPLORATION
Best for: Introduction to concepts, open-ended discovery
Structure:
- Multiple guided prompts
- Checkpoints for trying different values
- Reward breadth of exploration
Example: "Explore how different angles affect projectile range"

### PARAMETER_DISCOVERY
Best for: Finding relationships, Bloom's Apply/Analyze
Structure:
- Specific parameters to vary
- Checkpoints for discovering relationships
- Questions about what was observed
Example: "Discover what affects pendulum period"

### TARGET_ACHIEVEMENT
Best for: Goal-oriented challenges, Bloom's Apply
Structure:
- Clear targets to hit
- Checkpoints for achieving outcomes
- Multiple attempts allowed
Example: "Make the projectile land at exactly 50 meters"

### PREDICTION_VERIFICATION
Best for: Scientific method, Bloom's Analyze/Evaluate
Structure:
- Prediction question first
- Exploration to test
- Verification checkpoint
Example: "Predict which angle gives max range, then test it"

### OPTIMIZATION
Best for: Problem solving, Bloom's Analyze
Structure:
- Optimization goal
- Checkpoints for improving
- Final checkpoint for optimal value
Example: "Find the angle that maximizes range"

### MEASUREMENT
Best for: Data collection, Bloom's Apply
Structure:
- Specific measurements to take
- Recording requirements
- Data analysis
Example: "Measure period for 5 different pendulum lengths"

### COMPARATIVE_ANALYSIS
Best for: Understanding differences, Bloom's Analyze
Structure:
- Multiple configurations to try
- Comparison checkpoints
- Synthesis question
Example: "Compare series vs parallel circuit brightness"

### CONSTRUCTION
Best for: Building understanding, Bloom's Create
Structure:
- Assembly steps
- Checkpoints for each component
- Final working system
Example: "Build a circuit with battery, switch, and bulb"

## Schema Structure

```json
{
  "templateType": "PHET_SIMULATION",
  "title": "Short descriptive title",
  "narrativeIntro": "1-3 sentence engaging introduction",

  "simulation": {
    "simulationId": "exact-phet-id",
    "version": "latest",
    "screen": "screen-name-or-null",
    "parameters": [...],    // From catalog
    "interactions": [...],  // From catalog
    "outcomes": [...],      // From catalog
    "initialState": {       // Optional starting values
      "cannonAngle": 45
    }
  },

  "assessmentType": "parameter_discovery",

  "tasks": [
    {
      "id": "task-1",
      "type": "exploration",
      "title": "Task Title",
      "instructions": "Detailed instructions for what to do",
      "learningObjective": "Specific learning goal",
      "bloomsLevel": "apply",

      "checkpoints": [
        {
          "id": "cp-1",
          "description": "Human-readable description",
          "conditions": [
            {
              "type": "PROPERTY_RANGE",
              "propertyId": "cannonAngle",
              "minValue": 43,
              "maxValue": 47
            }
          ],
          "conditionLogic": "all",
          "points": 10,
          "hint": "Helpful hint text",
          "feedback": "Success message"
        }
      ],

      "hints": ["Progressive hint 1", "Progressive hint 2"],
      "prediction": null,  // or prediction question
      "quiz": null,        // or post-task quiz
      "requiredToProceed": true
    }
  ],

  "scoring": {
    "maxScore": 100,
    "explorationBonus": 10,
    "hintPenalty": 2
  },

  "learningObjectives": [
    "Understand X",
    "Apply Y",
    "Analyze Z"
  ],
  "targetBloomsLevel": "apply",
  "estimatedMinutes": 15,
  "difficulty": "medium"
}
```

## Checkpoint Condition Types

### PROPERTY_EQUALS
```json
{
  "type": "PROPERTY_EQUALS",
  "propertyId": "cannonAngle",
  "value": 45,
  "tolerance": 2
}
```

### PROPERTY_RANGE
```json
{
  "type": "PROPERTY_RANGE",
  "propertyId": "launchSpeed",
  "minValue": 15,
  "maxValue": 20
}
```

### PROPERTY_CHANGED
```json
{
  "type": "PROPERTY_CHANGED",
  "propertyId": "cannonAngle"
}
```

### INTERACTION_OCCURRED
```json
{
  "type": "INTERACTION_OCCURRED",
  "interactionId": "launch"
}
```

### OUTCOME_ACHIEVED
```json
{
  "type": "OUTCOME_ACHIEVED",
  "outcomeId": "range",
  "operator": "gt",
  "value": 40
}
```

### TIME_SPENT
```json
{
  "type": "TIME_SPENT",
  "minSeconds": 60
}
```

### EXPLORATION_BREADTH
```json
{
  "type": "EXPLORATION_BREADTH",
  "parameterIds": ["cannonAngle"],
  "minUniqueValues": 3
}
```

## Examples

### Example 1: Projectile Motion - Parameter Discovery

```json
{
  "templateType": "PHET_SIMULATION",
  "title": "Discovering the Optimal Launch Angle",
  "narrativeIntro": "You're a medieval engineer designing a catapult. Your mission: find the angle that launches projectiles the farthest!",

  "simulation": {
    "simulationId": "projectile-motion",
    "screen": "intro",
    "initialState": {
      "cannonAngle": 30,
      "launchSpeed": 18
    }
  },

  "assessmentType": "parameter_discovery",

  "tasks": [
    {
      "id": "task-explore",
      "type": "exploration",
      "title": "Explore Different Angles",
      "instructions": "Fire projectiles at angles of 30°, 45°, and 60°. Observe how far each one travels.",
      "learningObjective": "Observe how launch angle affects projectile range",
      "bloomsLevel": "understand",
      "checkpoints": [
        {
          "id": "cp-angle-30",
          "description": "Fire at 30°",
          "conditions": [
            {"type": "PROPERTY_RANGE", "propertyId": "cannonAngle", "minValue": 28, "maxValue": 32},
            {"type": "INTERACTION_OCCURRED", "interactionId": "launch"}
          ],
          "conditionLogic": "all",
          "points": 10
        },
        {
          "id": "cp-angle-45",
          "description": "Fire at 45°",
          "conditions": [
            {"type": "PROPERTY_RANGE", "propertyId": "cannonAngle", "minValue": 43, "maxValue": 47},
            {"type": "INTERACTION_OCCURRED", "interactionId": "launch"}
          ],
          "points": 10
        },
        {
          "id": "cp-angle-60",
          "description": "Fire at 60°",
          "conditions": [
            {"type": "PROPERTY_RANGE", "propertyId": "cannonAngle", "minValue": 58, "maxValue": 62},
            {"type": "INTERACTION_OCCURRED", "interactionId": "launch"}
          ],
          "points": 10
        }
      ],
      "hints": ["The angle slider is on the left", "Try clicking Fire after each angle change"],
      "requiredToProceed": true
    },
    {
      "id": "task-discover",
      "type": "optimization",
      "title": "Find the Optimal Angle",
      "instructions": "Based on your observations, find the angle that makes the projectile travel the farthest.",
      "learningObjective": "Discover that 45° maximizes range",
      "bloomsLevel": "apply",
      "checkpoints": [
        {
          "id": "cp-optimal",
          "description": "Set angle to optimal value (45°)",
          "conditions": [
            {"type": "PROPERTY_RANGE", "propertyId": "cannonAngle", "minValue": 44, "maxValue": 46}
          ],
          "points": 15,
          "hint": "The optimal angle is between 40° and 50°"
        },
        {
          "id": "cp-max-range",
          "description": "Achieve maximum range",
          "conditions": [
            {"type": "OUTCOME_ACHIEVED", "outcomeId": "range", "operator": "gte", "value": 32}
          ],
          "points": 15
        }
      ],
      "quiz": [
        {
          "question": "Why does 45° give the maximum range?",
          "options": [
            "It balances horizontal speed and time in air",
            "It has the most gravity",
            "It makes the projectile heavier"
          ],
          "correct": "It balances horizontal speed and time in air",
          "points": 10
        }
      ]
    }
  ],

  "scoring": {
    "maxScore": 70,
    "explorationBonus": 5,
    "hintPenalty": 2
  },

  "learningObjectives": [
    "Understand how launch angle affects projectile range",
    "Discover the optimal angle for maximum range",
    "Explain why 45° maximizes range"
  ],
  "targetBloomsLevel": "apply",
  "estimatedMinutes": 12,
  "difficulty": "medium"
}
```

## Critical Rules

1. **Use exact simulation IDs** from the catalog
2. **Use valid propertyId/interactionId/outcomeId** from simulation metadata
3. **Checkpoint IDs must be unique** across all tasks
4. **Total checkpoint points ≤ maxScore**
5. **Include at least 2 checkpoints per task**
6. **Provide helpful hints** for each task
7. **Include quiz questions** for Bloom's levels ≥ Apply
8. **Set appropriate difficulty** based on checkpoint conditions

## Output

Respond with ONLY valid JSON matching the PhetSimulationBlueprint schema. No explanations.
```

---

## 5. FRONTEND COMPONENTS

### File: `frontend/src/components/templates/PhetSimulationGame/index.tsx`

```tsx
/**
 * PhET Simulation Game Component
 *
 * Main component that renders PhET simulations with assessment wrapper.
 * Follows the same pattern as LabelDiagramGame.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { PhetSimulationBlueprint, GameState, CheckpointStatus } from './types';
import { usePhetSimulationState } from './hooks/usePhetSimulationState';
import { usePhetBridge } from './hooks/usePhetBridge';
import { TaskPanel } from './TaskPanel';
import { ScorePanel } from './ScorePanel';
import { CheckpointProgress } from './CheckpointProgress';
import { ResultsPanel } from './ResultsPanel';
import { PhetFrame } from './PhetFrame';

interface Props {
  blueprint: PhetSimulationBlueprint;
  onComplete?: (results: GameResults) => void;
  onProgress?: (progress: GameProgress) => void;
}

export function PhetSimulationGame({ blueprint, onComplete, onProgress }: Props) {
  // Normalize and validate blueprint
  const normalizedBlueprint = normalizeBlueprint(blueprint);

  // Game state management
  const {
    gameState,
    currentTaskIndex,
    currentTask,
    completedCheckpoints,
    score,
    maxScore,
    hintsUsed,
    isComplete,
    completeCheckpoint,
    useHint,
    nextTask,
    resetGame
  } = usePhetSimulationState(normalizedBlueprint);

  // PhET bridge for simulation communication
  const {
    iframeRef,
    isReady,
    simulationState,
    interactions,
    sendCommand
  } = usePhetBridge({
    bridgeConfig: normalizedBlueprint.bridgeConfig,
    onStateChange: handleStateChange,
    onInteraction: handleInteraction
  });

  // Evaluate checkpoints when state/interactions change
  useEffect(() => {
    if (!currentTask || !isReady) return;

    currentTask.checkpoints.forEach(checkpoint => {
      if (completedCheckpoints.has(checkpoint.id)) return;

      const isSatisfied = evaluateCheckpoint(
        checkpoint,
        simulationState,
        interactions,
        gameState
      );

      if (isSatisfied) {
        completeCheckpoint(checkpoint.id, checkpoint.points);
      }
    });
  }, [simulationState, interactions, currentTask, completedCheckpoints]);

  // Report progress
  useEffect(() => {
    onProgress?.({
      currentTaskIndex,
      totalTasks: normalizedBlueprint.tasks.length,
      completedCheckpoints: Array.from(completedCheckpoints),
      score,
      maxScore
    });
  }, [currentTaskIndex, completedCheckpoints, score]);

  // Handle completion
  useEffect(() => {
    if (isComplete) {
      onComplete?.({
        finalScore: score,
        maxScore,
        completedCheckpoints: Array.from(completedCheckpoints),
        hintsUsed,
        timeSpentSeconds: Math.floor((Date.now() - gameState.startTime) / 1000)
      });
    }
  }, [isComplete]);

  function handleStateChange(property: string, value: any) {
    // State change is automatically tracked by usePhetBridge
  }

  function handleInteraction(interaction: PhetInteraction) {
    // Interaction is automatically tracked by usePhetBridge
  }

  if (isComplete) {
    return (
      <ResultsPanel
        score={score}
        maxScore={maxScore}
        feedback={normalizedBlueprint.feedback}
        onRestart={resetGame}
      />
    );
  }

  return (
    <div className="phet-game-container flex flex-col lg:flex-row gap-4 h-full p-4 bg-gray-100">
      {/* Simulation Panel */}
      <div className="flex-1 flex flex-col">
        <PhetFrame
          ref={iframeRef}
          simulationId={normalizedBlueprint.simulation.simulationId}
          localPath={normalizedBlueprint.simulation.localPath}
          isReady={isReady}
        />
      </div>

      {/* Assessment Panel */}
      <div className="w-full lg:w-80 flex flex-col gap-4">
        <ScorePanel
          score={score}
          maxScore={maxScore}
          currentTask={currentTaskIndex + 1}
          totalTasks={normalizedBlueprint.tasks.length}
        />

        {currentTask && (
          <TaskPanel
            task={currentTask}
            completedCheckpoints={completedCheckpoints}
            hintsUsed={hintsUsed}
            onUseHint={useHint}
          />
        )}

        <CheckpointProgress
          checkpoints={currentTask?.checkpoints || []}
          completedCheckpoints={completedCheckpoints}
        />

        {/* Next Task Button */}
        {currentTask && isTaskComplete(currentTask, completedCheckpoints) &&
         currentTaskIndex < normalizedBlueprint.tasks.length - 1 && (
          <button
            onClick={nextTask}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg"
          >
            Continue to Next Task →
          </button>
        )}
      </div>
    </div>
  );
}

function normalizeBlueprint(blueprint: any): PhetSimulationBlueprint {
  // Validation and normalization logic
  return blueprint as PhetSimulationBlueprint;
}

function evaluateCheckpoint(
  checkpoint: Checkpoint,
  state: Record<string, any>,
  interactions: PhetInteraction[],
  gameState: GameState
): boolean {
  const results = checkpoint.conditions.map(condition =>
    evaluateCondition(condition, state, interactions, gameState)
  );

  if (checkpoint.conditionLogic === 'any') {
    return results.some(r => r);
  }
  return results.every(r => r);
}

function evaluateCondition(
  condition: CheckpointCondition,
  state: Record<string, any>,
  interactions: PhetInteraction[],
  gameState: GameState
): boolean {
  switch (condition.type) {
    case 'PROPERTY_EQUALS': {
      const value = state[condition.propertyId!];
      const tolerance = condition.tolerance || 0;
      return Math.abs(value - condition.value) <= tolerance;
    }

    case 'PROPERTY_RANGE': {
      const value = state[condition.propertyId!];
      return value >= condition.minValue! && value <= condition.maxValue!;
    }

    case 'PROPERTY_CHANGED': {
      // Check if property was changed from initial value
      return gameState.changedProperties.has(condition.propertyId!);
    }

    case 'INTERACTION_OCCURRED': {
      return interactions.some(i => i.id === condition.interactionId);
    }

    case 'OUTCOME_ACHIEVED': {
      const value = state[condition.outcomeId!];
      const target = condition.value;
      switch (condition.operator) {
        case 'eq': return value === target;
        case 'gt': return value > target;
        case 'gte': return value >= target;
        case 'lt': return value < target;
        case 'lte': return value <= target;
        default: return false;
      }
    }

    case 'TIME_SPENT': {
      const elapsed = (Date.now() - gameState.startTime) / 1000;
      return elapsed >= condition.minSeconds!;
    }

    case 'EXPLORATION_BREADTH': {
      const paramId = condition.parameterIds![0];
      const uniqueValues = gameState.exploredValues.get(paramId) || new Set();
      return uniqueValues.size >= condition.minUniqueValues!;
    }

    default:
      return false;
  }
}
```

---

## 6. Summary: Agent Roles

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Router** | Select template type | question, context | `template_selection` |
| **PhET Simulation Selector** | Choose simulation | context, concepts | `phet_selection` |
| **PhET Game Planner** | Design assessment strategy | selection, context | `phet_game_plan` |
| **PhET Assessment Designer** | Create checkpoints | plan, metadata | `phet_assessment_design` |
| **PhET Blueprint Generator** | Generate full blueprint | all upstream | `blueprint` |
| **PhET Blueprint Validator** | Validate & retry | blueprint | validation result |
| **PhET Bridge Config Generator** | Create bridge config | blueprint | `blueprint.bridgeConfig` |

---

## 7. Assessment Type Selection Logic

The **PhET Game Planner** selects assessment type based on:

```python
ASSESSMENT_TYPE_RULES = {
    # Bloom's level mapping
    "remember": ["exploration"],
    "understand": ["exploration", "parameter_discovery"],
    "apply": ["target_achievement", "measurement", "construction"],
    "analyze": ["parameter_discovery", "comparative_analysis", "prediction_verification"],
    "evaluate": ["optimization", "prediction_verification"],
    "create": ["construction", "optimization"],

    # Question pattern mapping
    "what happens when": ["parameter_discovery", "exploration"],
    "find the": ["target_achievement", "optimization"],
    "compare": ["comparative_analysis"],
    "predict": ["prediction_verification"],
    "build": ["construction"],
    "measure": ["measurement"],
    "explore": ["exploration"],
    "discover": ["parameter_discovery"],
    "optimize": ["optimization"],
    "maximize": ["optimization"],
    "minimize": ["optimization"],
}
```

This allows the agent to dynamically select the best assessment type rather than using predetermined templates!
