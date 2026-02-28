"""
PhET Simulation Blueprint Schema

Defines the complete structure for PHET_SIMULATION template games.
Follows the same pattern as interactive_diagram.py

Supports:
- Multiple assessment types (exploration, parameter_discovery, target_achievement, etc.)
- Checkpoint-based scoring with various condition types
- Bridge configuration for PhET-GamED communication
- Multi-dimensional scoring
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
    AREA_BUILDER = "area-builder"
    GRAVITY_FORCE_LAB = "gravity-force-lab"
    COULOMBS_LAW = "coulombs-law"


class AssessmentType(str, Enum):
    """Types of assessments that can be created"""
    EXPLORATION = "exploration"                          # Open-ended exploration with guided prompts
    PARAMETER_DISCOVERY = "parameter_discovery"          # Find relationships between parameters
    TARGET_ACHIEVEMENT = "target_achievement"            # Achieve specific outcomes
    PREDICTION_VERIFICATION = "prediction_verification"  # Predict → Test → Verify
    COMPARATIVE_ANALYSIS = "comparative_analysis"        # Compare different configurations
    OPTIMIZATION = "optimization"                        # Find optimal values
    MEASUREMENT = "measurement"                          # Take measurements and record data
    CONSTRUCTION = "construction"                        # Build something (circuits, molecules)
    SEQUENCE_EXECUTION = "sequence_execution"            # Follow a procedure


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


class PredictionQuestion(BaseModel):
    """Prediction question for prediction_verification tasks"""
    model_config = ConfigDict(extra="forbid")

    question: str
    options: List[str]
    correctOption: Optional[str] = None


class QuizQuestion(BaseModel):
    """Post-task quiz question"""
    model_config = ConfigDict(extra="forbid")

    question: str
    options: List[str]
    correct: str
    points: int = Field(ge=1, le=20, default=5)
    explanation: Optional[str] = None


class MeasurementTask(BaseModel):
    """Measurement to record during assessment"""
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    outcomeId: str
    unit: Optional[str] = None
    expectedValue: Optional[float] = None
    tolerance: Optional[float] = None


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
    prediction: Optional[PredictionQuestion] = Field(
        default=None,
        description="Prediction question before exploration"
    )

    # For measurement tasks
    measurements: Optional[List[MeasurementTask]] = Field(
        default=None,
        description="Measurements to record"
    )

    # Task flow
    requiredToProceed: bool = True
    timeLimit: Optional[int] = Field(default=None, description="Time limit in seconds")

    # Post-task quiz
    quiz: Optional[List[QuizQuestion]] = None


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
    "energy-skate-park": {
        "title": "Energy Skate Park",
        "domains": ["physics"],
        "concepts": ["kinetic energy", "potential energy", "conservation of energy", "friction", "thermal energy"],
        "parameters": [
            {"phetioId": "energy-skate-park.introScreen.model.skater.massProperty", "name": "Skater Mass", "type": "number", "unit": "kg", "min": 10, "max": 100},
            {"phetioId": "energy-skate-park.introScreen.model.frictionProperty", "name": "Friction", "type": "number", "min": 0, "max": 1},
        ],
        "interactions": [
            {"id": "placeSkater", "type": "drag_drop", "phetioId": "energy-skate-park.introScreen.view.skaterNode", "name": "Place Skater"},
            {"id": "playPause", "type": "button_click", "phetioId": "energy-skate-park.introScreen.view.playPauseButton", "name": "Play/Pause"},
        ],
        "outcomes": [
            {"id": "kineticEnergy", "name": "Kinetic Energy", "phetioId": "energy-skate-park.introScreen.model.skater.kineticEnergyProperty", "unit": "J"},
            {"id": "potentialEnergy", "name": "Potential Energy", "phetioId": "energy-skate-park.introScreen.model.skater.potentialEnergyProperty", "unit": "J"},
            {"id": "totalEnergy", "name": "Total Energy", "phetioId": "energy-skate-park.introScreen.model.skater.totalEnergyProperty", "unit": "J"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "prediction_verification", "comparative_analysis"],
        "screens": ["intro", "playground", "graphs"],
    },
    "waves": {
        "title": "Waves",
        "domains": ["physics"],
        "concepts": ["amplitude", "frequency", "wavelength", "wave speed", "interference"],
        "parameters": [
            {"phetioId": "waves.waveOnAStringScreen.model.frequencyProperty", "name": "Frequency", "type": "number", "unit": "Hz", "min": 0.1, "max": 3},
            {"phetioId": "waves.waveOnAStringScreen.model.amplitudeProperty", "name": "Amplitude", "type": "number", "unit": "cm", "min": 0, "max": 2},
            {"phetioId": "waves.waveOnAStringScreen.model.tensionProperty", "name": "Tension", "type": "number", "min": 0, "max": 1},
            {"phetioId": "waves.waveOnAStringScreen.model.dampingProperty", "name": "Damping", "type": "number", "min": 0, "max": 1},
        ],
        "interactions": [
            {"id": "playPause", "type": "button_click", "phetioId": "waves.waveOnAStringScreen.view.playPauseButton", "name": "Play/Pause"},
            {"id": "manualWave", "type": "drag_drop", "phetioId": "waves.waveOnAStringScreen.view.wrench", "name": "Manual Wave"},
        ],
        "outcomes": [
            {"id": "wavelength", "name": "Wavelength", "phetioId": "waves.waveOnAStringScreen.model.wavelengthProperty", "unit": "cm"},
            {"id": "waveSpeed", "name": "Wave Speed", "phetioId": "waves.waveOnAStringScreen.model.waveSpeedProperty", "unit": "cm/s"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "measurement", "prediction_verification"],
        "screens": ["wave-on-a-string", "interference"],
    },
    "build-an-atom": {
        "title": "Build an Atom",
        "domains": ["chemistry", "physics"],
        "concepts": ["atomic structure", "protons", "neutrons", "electrons", "isotopes", "ions"],
        "parameters": [
            {"phetioId": "build-an-atom.buildAnAtomScreen.model.particleAtom.protonCountProperty", "name": "Proton Count", "type": "number", "min": 0, "max": 10},
            {"phetioId": "build-an-atom.buildAnAtomScreen.model.particleAtom.neutronCountProperty", "name": "Neutron Count", "type": "number", "min": 0, "max": 12},
            {"phetioId": "build-an-atom.buildAnAtomScreen.model.particleAtom.electronCountProperty", "name": "Electron Count", "type": "number", "min": 0, "max": 10},
        ],
        "interactions": [
            {"id": "addProton", "type": "drag_drop", "phetioId": "build-an-atom.buildAnAtomScreen.view.protonBucket", "name": "Add Proton"},
            {"id": "addNeutron", "type": "drag_drop", "phetioId": "build-an-atom.buildAnAtomScreen.view.neutronBucket", "name": "Add Neutron"},
            {"id": "addElectron", "type": "drag_drop", "phetioId": "build-an-atom.buildAnAtomScreen.view.electronBucket", "name": "Add Electron"},
        ],
        "outcomes": [
            {"id": "elementName", "name": "Element", "phetioId": "build-an-atom.buildAnAtomScreen.model.particleAtom.elementNameProperty"},
            {"id": "massNumber", "name": "Mass Number", "phetioId": "build-an-atom.buildAnAtomScreen.model.particleAtom.massNumberProperty"},
            {"id": "charge", "name": "Charge", "phetioId": "build-an-atom.buildAnAtomScreen.model.particleAtom.chargeProperty"},
        ],
        "assessmentTypes": ["construction", "target_achievement", "exploration"],
        "screens": ["build-an-atom", "symbol", "game"],
    },
    "molecule-polarity": {
        "title": "Molecule Polarity",
        "domains": ["chemistry"],
        "concepts": ["electronegativity", "polarity", "dipole", "molecular geometry", "bonds"],
        "parameters": [
            {"phetioId": "molecule-polarity.twoAtomsScreen.model.electronegativityAProperty", "name": "Electronegativity A", "type": "number", "min": 1, "max": 4},
            {"phetioId": "molecule-polarity.twoAtomsScreen.model.electronegativityBProperty", "name": "Electronegativity B", "type": "number", "min": 1, "max": 4},
        ],
        "interactions": [
            {"id": "adjustElectronegativity", "type": "slider_adjust", "phetioId": "molecule-polarity.twoAtomsScreen.view.electronegativitySlider", "name": "Adjust Electronegativity"},
        ],
        "outcomes": [
            {"id": "bondPolarity", "name": "Bond Polarity", "phetioId": "molecule-polarity.twoAtomsScreen.model.bondPolarityProperty"},
            {"id": "moleculeDipole", "name": "Molecule Dipole", "phetioId": "molecule-polarity.twoAtomsScreen.model.moleculeDipoleProperty"},
        ],
        "assessmentTypes": ["exploration", "parameter_discovery", "prediction_verification"],
        "screens": ["two-atoms", "three-atoms", "real-molecules"],
    },
    "area-builder": {
        "title": "Area Builder",
        "domains": ["mathematics"],
        "concepts": ["area", "perimeter", "geometry", "shapes", "measurement"],
        "parameters": [],
        "interactions": [
            {"id": "placeShape", "type": "drag_drop", "phetioId": "area-builder.exploreScreen.view.shapesPanel", "name": "Place Shape"},
            {"id": "removeShape", "type": "button_click", "phetioId": "area-builder.exploreScreen.view.eraseButton", "name": "Remove Shape"},
        ],
        "outcomes": [
            {"id": "totalArea", "name": "Total Area", "phetioId": "area-builder.exploreScreen.model.areaProperty", "unit": "sq units"},
            {"id": "totalPerimeter", "name": "Total Perimeter", "phetioId": "area-builder.exploreScreen.model.perimeterProperty", "unit": "units"},
        ],
        "assessmentTypes": ["construction", "target_achievement", "exploration"],
        "screens": ["explore", "build-a-shape", "game"],
    },
}


# =============================================================================
# ASSESSMENT TYPE SELECTION RULES
# =============================================================================

ASSESSMENT_TYPE_RULES = {
    # Bloom's level mapping
    "remember": ["exploration"],
    "understand": ["exploration", "parameter_discovery"],
    "apply": ["target_achievement", "measurement", "construction"],
    "analyze": ["parameter_discovery", "comparative_analysis", "prediction_verification"],
    "evaluate": ["optimization", "prediction_verification"],
    "create": ["construction", "optimization"],
}

QUESTION_PATTERN_RULES = {
    # Question pattern mapping
    "what happens when": ["parameter_discovery", "exploration"],
    "find the": ["target_achievement", "optimization"],
    "compare": ["comparative_analysis"],
    "predict": ["prediction_verification"],
    "build": ["construction"],
    "construct": ["construction"],
    "measure": ["measurement"],
    "explore": ["exploration"],
    "discover": ["parameter_discovery"],
    "optimize": ["optimization"],
    "maximize": ["optimization"],
    "minimize": ["optimization"],
    "how does": ["parameter_discovery"],
    "why does": ["prediction_verification"],
    "what is the relationship": ["parameter_discovery"],
    "design": ["construction"],
    "create": ["construction"],
}


def select_assessment_type(
    blooms_level: str,
    question_text: str,
    simulation_types: List[str]
) -> str:
    """
    Select the best assessment type based on Bloom's level and question patterns.

    Args:
        blooms_level: Target Bloom's taxonomy level
        question_text: The question or topic text
        simulation_types: Assessment types supported by the selected simulation

    Returns:
        Selected assessment type string
    """
    question_lower = question_text.lower()

    # First check question patterns (more specific)
    for pattern, types in QUESTION_PATTERN_RULES.items():
        if pattern in question_lower:
            for t in types:
                if t in simulation_types:
                    return t

    # Fall back to Bloom's level mapping
    blooms_types = ASSESSMENT_TYPE_RULES.get(blooms_level, ["exploration"])
    for t in blooms_types:
        if t in simulation_types:
            return t

    # Default fallback
    return simulation_types[0] if simulation_types else "exploration"


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


def get_phet_simulation_blueprint_schema() -> Dict[str, Any]:
    """Get JSON schema for LLM guided generation"""
    return PhetSimulationBlueprint.model_json_schema()


def get_simulation_metadata(simulation_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific simulation"""
    return SIMULATION_CATALOG.get(simulation_id)


def get_all_simulations() -> Dict[str, Dict[str, Any]]:
    """Get all available simulations"""
    return SIMULATION_CATALOG.copy()


def get_simulations_by_domain(domain: str) -> List[str]:
    """Get simulation IDs that match a domain"""
    return [
        sim_id
        for sim_id, meta in SIMULATION_CATALOG.items()
        if domain.lower() in [d.lower() for d in meta.get("domains", [])]
    ]


def get_simulations_by_concept(concept: str) -> List[str]:
    """Get simulation IDs that cover a concept"""
    concept_lower = concept.lower()
    return [
        sim_id
        for sim_id, meta in SIMULATION_CATALOG.items()
        if any(concept_lower in c.lower() for c in meta.get("concepts", []))
    ]
