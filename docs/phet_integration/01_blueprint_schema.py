"""
PhET Simulation Blueprint Schema

This module defines the Pydantic validation schema for PHET_SIMULATION template blueprints.
It extends the existing blueprint_schemas.py patterns for PhET-specific configuration.

Usage:
    from app.agents.schemas.phet_blueprint_schema import (
        PhetSimulationBlueprint,
        validate_phet_blueprint
    )
"""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator
from enum import Enum


# =============================================================================
# PHET SIMULATION CATALOG
# =============================================================================

class PhetSimulationId(str, Enum):
    """Available PhET simulations with PhET-iO support"""
    PROJECTILE_MOTION = "projectile-motion"
    CIRCUIT_CONSTRUCTION_KIT_DC = "circuit-construction-kit-dc"
    WAVES = "waves"
    STATES_OF_MATTER = "states-of-matter"
    MOLECULE_POLARITY = "molecule-polarity"
    GRAPHING_QUADRATICS = "graphing-quadratics"
    AREA_BUILDER = "area-builder"
    FRICTION = "friction"
    FORCES_AND_MOTION = "forces-and-motion"
    ENERGY_SKATE_PARK = "energy-skate-park"
    BALANCING_ACT = "balancing-act"
    GRAVITY_AND_ORBITS = "gravity-and-orbits"
    PENDULUM_LAB = "pendulum-lab"
    MASSES_AND_SPRINGS = "masses-and-springs"
    PLINKO_PROBABILITY = "plinko-probability"


SIMULATION_METADATA = {
    "projectile-motion": {
        "title": "Projectile Motion",
        "domains": ["physics"],
        "concepts": ["kinematics", "vectors", "gravity", "trajectory", "velocity", "acceleration"],
        "blooms_alignment": ["understand", "apply", "analyze"],
        "phet_io_support": "full",
        "default_screen": "intro"
    },
    "circuit-construction-kit-dc": {
        "title": "Circuit Construction Kit: DC",
        "domains": ["physics"],
        "concepts": ["circuits", "current", "voltage", "resistance", "Ohm's law"],
        "blooms_alignment": ["understand", "apply", "analyze", "create"],
        "phet_io_support": "full",
        "default_screen": "intro"
    },
    "waves": {
        "title": "Waves",
        "domains": ["physics"],
        "concepts": ["wave properties", "frequency", "amplitude", "wavelength", "interference"],
        "blooms_alignment": ["understand", "apply", "analyze"],
        "phet_io_support": "full",
        "default_screen": "waves"
    },
    "states-of-matter": {
        "title": "States of Matter",
        "domains": ["chemistry", "physics"],
        "concepts": ["molecular motion", "phases", "temperature", "pressure", "phase transitions"],
        "blooms_alignment": ["understand", "apply"],
        "phet_io_support": "full",
        "default_screen": "states"
    },
    "molecule-polarity": {
        "title": "Molecule Polarity",
        "domains": ["chemistry"],
        "concepts": ["electronegativity", "polarity", "molecular structure", "dipole"],
        "blooms_alignment": ["understand", "apply"],
        "phet_io_support": "full",
        "default_screen": "three-atoms"
    },
    "graphing-quadratics": {
        "title": "Graphing Quadratics",
        "domains": ["mathematics"],
        "concepts": ["parabolas", "quadratic functions", "vertex", "roots", "coefficients"],
        "blooms_alignment": ["understand", "apply", "analyze"],
        "phet_io_support": "full",
        "default_screen": "explore"
    },
    "friction": {
        "title": "Friction",
        "domains": ["physics"],
        "concepts": ["friction", "forces", "motion", "Newton's laws"],
        "blooms_alignment": ["understand", "apply"],
        "phet_io_support": "full",
        "default_screen": "friction"
    }
}


# =============================================================================
# CUSTOMIZATION MODELS
# =============================================================================

class PhetLaunchParams(BaseModel):
    """PhET-iO launch parameters for simulation customization"""
    model_config = ConfigDict(extra="allow")

    phetioEmitStates: bool = False
    phetioEmitDeltas: bool = False
    phetioDebug: bool = False
    screen: Optional[str] = None


class PhetElementVisibility(BaseModel):
    """Control visibility of PhET-iO elements"""
    phetioID: str = Field(min_length=1, description="Full phetioID path")
    visible: bool = True


class PhetInitialState(BaseModel):
    """Initial state configuration for simulation"""
    model_config = ConfigDict(extra="allow")

    phetioID: str = Field(min_length=1)
    value: Any


class PhetCustomization(BaseModel):
    """Complete customization configuration for PhET simulation"""
    model_config = ConfigDict(extra="forbid")

    launchParams: Optional[PhetLaunchParams] = None
    initialStates: Optional[List[PhetInitialState]] = None
    hiddenElements: Optional[List[str]] = Field(
        default=None,
        description="List of phetioIDs to hide in the simulation"
    )
    enabledElements: Optional[List[str]] = Field(
        default=None,
        description="List of phetioIDs to enable (others may be disabled)"
    )


# =============================================================================
# TASK MODELS
# =============================================================================

class PhetInteractionType(str, Enum):
    """Types of interactions expected in PhET tasks"""
    EXPLORATION = "exploration"
    PREDICTION = "prediction"
    MEASUREMENT = "measurement"
    CONSTRUCTION = "construction"
    ANALYSIS = "analysis"


class PhetCheckpoint(BaseModel):
    """Checkpoint for validating student progress"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    phetioID: str = Field(min_length=1, description="phetioID to monitor")
    expectedValue: Optional[Any] = None
    expectedRange: Optional[Dict[str, float]] = Field(
        default=None,
        description="Range validation with 'min' and 'max' keys"
    )
    points: int = Field(ge=1, default=10)


class PhetScoringCriteria(BaseModel):
    """Scoring criteria mapped to PhET-iO events"""
    model_config = ConfigDict(extra="forbid")

    accuracy: Optional[List[PhetCheckpoint]] = None
    efficiency: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Time-based or interaction-count efficiency metrics"
    )
    exploration: Optional[Dict[str, int]] = Field(
        default=None,
        description="Points for exploring different parameters/states"
    )


class PhetSimulationTask(BaseModel):
    """A learning task within a PhET simulation game"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    questionText: str = Field(min_length=1)
    interactionType: PhetInteractionType
    instructions: Optional[str] = None
    hints: Optional[List[str]] = None
    checkpoints: List[PhetCheckpoint] = Field(min_length=1)
    scoringCriteria: Optional[PhetScoringCriteria] = None
    requiredToProceed: bool = True


# =============================================================================
# EVENT SUBSCRIPTION MODELS
# =============================================================================

class PhetEventSubscription(BaseModel):
    """Subscription for PhET-iO events for analytics and scoring"""
    model_config = ConfigDict(extra="forbid")

    phetioIDPattern: str = Field(
        min_length=1,
        description="Pattern to match phetioIDs (supports * wildcard)"
    )
    eventTypes: List[str] = Field(
        min_length=1,
        description="Event types to capture: propertyValueChange, methodInvoked, etc."
    )
    scoreMapping: Optional[Dict[str, int]] = Field(
        default=None,
        description="Map specific values/events to score points"
    )


# =============================================================================
# ANIMATION CUES
# =============================================================================

class PhetAnimationCues(BaseModel):
    """Animation cues for PhET simulation feedback"""
    model_config = ConfigDict(extra="forbid")

    taskStart: str = Field(default="simulation loads with guided highlight")
    checkpointReached: str = Field(default="subtle confirmation with score update")
    taskComplete: str = Field(default="celebration animation and next task prompt")
    incorrectAttempt: str = Field(default="gentle shake with hint suggestion")


# =============================================================================
# MAIN BLUEPRINT SCHEMA
# =============================================================================

class PhetSimulationBlueprint(BaseModel):
    """
    PHET_SIMULATION template: Embed and customize PhET interactive simulations

    This blueprint defines how to configure a PhET simulation for educational gaming,
    including customization, learning tasks, scoring, and event subscriptions.
    """
    model_config = ConfigDict(extra="forbid")

    templateType: Literal["PHET_SIMULATION"]
    title: str = Field(min_length=1)
    narrativeIntro: str = Field(min_length=1, max_length=500)

    # Simulation configuration
    simulationId: str = Field(
        min_length=1,
        description="PhET simulation identifier (e.g., 'projectile-motion')"
    )
    simulationVersion: str = Field(
        default="latest",
        description="Version to use: 'latest' or specific version number"
    )

    # Customization
    customization: Optional[PhetCustomization] = None

    # Learning tasks
    tasks: List[PhetSimulationTask] = Field(min_length=1)

    # Event subscriptions for analytics and scoring
    eventSubscriptions: Optional[List[PhetEventSubscription]] = None

    # Animation cues
    animationCues: PhetAnimationCues = Field(default_factory=PhetAnimationCues)

    # Learning context
    learningObjectives: Optional[List[str]] = None
    targetBloomsLevel: Optional[str] = None
    estimatedDurationMinutes: Optional[int] = Field(default=15, ge=5, le=60)

    @model_validator(mode="after")
    def validate_simulation_exists(self):
        """Ensure simulation ID is in our supported catalog"""
        if self.simulationId not in SIMULATION_METADATA:
            # Allow unknown simulations but log warning
            pass  # In production, could add warning to validation result
        return self

    @model_validator(mode="after")
    def validate_task_ids_unique(self):
        """Ensure all task IDs are unique"""
        task_ids = [t.id for t in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Duplicate task IDs detected. Each task must have a unique ID.")
        return self

    @model_validator(mode="after")
    def validate_checkpoint_ids_unique(self):
        """Ensure all checkpoint IDs are unique across all tasks"""
        all_checkpoint_ids = []
        for task in self.tasks:
            for cp in task.checkpoints:
                all_checkpoint_ids.append(cp.id)
        if len(all_checkpoint_ids) != len(set(all_checkpoint_ids)):
            raise ValueError("Duplicate checkpoint IDs detected across tasks.")
        return self


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_phet_blueprint(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a PHET_SIMULATION blueprint against the Pydantic schema.

    Args:
        blueprint: Blueprint dictionary to validate

    Returns:
        Dict with 'valid' bool, 'errors' list, 'warnings' list, and 'validated_blueprint'
    """
    errors = []
    warnings = []

    # Check template type
    if blueprint.get("templateType") != "PHET_SIMULATION":
        return {
            "valid": False,
            "errors": ["templateType must be 'PHET_SIMULATION'"],
            "warnings": [],
            "validated_blueprint": None
        }

    # Check if simulation is in catalog
    sim_id = blueprint.get("simulationId", "")
    if sim_id and sim_id not in SIMULATION_METADATA:
        warnings.append(f"Simulation '{sim_id}' not in known catalog. Verify PhET-iO support.")

    try:
        validated = PhetSimulationBlueprint.model_validate(blueprint)
        return {
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "validated_blueprint": validated.model_dump(),
            "simulation_metadata": SIMULATION_METADATA.get(sim_id, {})
        }
    except Exception as e:
        error_msg = str(e)
        if "validation error" in error_msg.lower():
            errors.append(f"Schema validation failed: {error_msg}")
        else:
            errors.append(f"Validation error: {error_msg}")

        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "validated_blueprint": None
        }


def get_simulation_metadata(simulation_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a simulation from the catalog"""
    return SIMULATION_METADATA.get(simulation_id)


def get_available_simulations() -> List[str]:
    """Get list of all available simulation IDs"""
    return list(SIMULATION_METADATA.keys())


def get_simulations_by_domain(domain: str) -> List[str]:
    """Get simulations that cover a specific domain"""
    return [
        sim_id for sim_id, meta in SIMULATION_METADATA.items()
        if domain.lower() in [d.lower() for d in meta.get("domains", [])]
    ]


def get_simulations_by_concept(concept: str) -> List[str]:
    """Get simulations that cover a specific concept"""
    concept_lower = concept.lower()
    return [
        sim_id for sim_id, meta in SIMULATION_METADATA.items()
        if any(concept_lower in c.lower() for c in meta.get("concepts", []))
    ]


# =============================================================================
# EXAMPLE BLUEPRINT
# =============================================================================

EXAMPLE_BLUEPRINT = {
    "templateType": "PHET_SIMULATION",
    "title": "Exploring Projectile Motion",
    "narrativeIntro": "Launch projectiles and explore how angle, speed, and gravity affect their trajectory. Discover the physics of motion!",
    "simulationId": "projectile-motion",
    "simulationVersion": "latest",
    "customization": {
        "launchParams": {
            "screen": "intro"
        },
        "hiddenElements": [
            "projectile-motion.introScreen.view.airResistancePanel"
        ],
        "initialStates": [
            {
                "phetioID": "projectile-motion.introScreen.model.cannonAngleProperty",
                "value": 45
            }
        ]
    },
    "tasks": [
        {
            "id": "task-1",
            "questionText": "What happens to the range when you increase the launch angle from 30° to 60°?",
            "interactionType": "exploration",
            "instructions": "Use the angle slider to adjust the cannon angle. Fire multiple projectiles and observe the landing positions.",
            "hints": [
                "Try angles of 30°, 45°, and 60°",
                "Notice the height vs. distance trade-off"
            ],
            "checkpoints": [
                {
                    "id": "cp-1a",
                    "description": "Launch at 30 degrees",
                    "phetioID": "projectile-motion.introScreen.model.cannonAngleProperty",
                    "expectedValue": 30,
                    "points": 10
                },
                {
                    "id": "cp-1b",
                    "description": "Launch at 60 degrees",
                    "phetioID": "projectile-motion.introScreen.model.cannonAngleProperty",
                    "expectedValue": 60,
                    "points": 10
                }
            ],
            "requiredToProceed": True
        },
        {
            "id": "task-2",
            "questionText": "Predict: At what angle will the projectile travel the farthest distance?",
            "interactionType": "prediction",
            "instructions": "Based on your exploration, find the angle that maximizes horizontal range.",
            "checkpoints": [
                {
                    "id": "cp-2a",
                    "description": "Find optimal angle (45°)",
                    "phetioID": "projectile-motion.introScreen.model.cannonAngleProperty",
                    "expectedRange": {"min": 44, "max": 46},
                    "points": 20
                }
            ],
            "requiredToProceed": True
        }
    ],
    "eventSubscriptions": [
        {
            "phetioIDPattern": "projectile-motion.introScreen.model.*Property",
            "eventTypes": ["propertyValueChange"],
            "scoreMapping": {
                "exploration_bonus": 5
            }
        }
    ],
    "animationCues": {
        "taskStart": "cannon highlights with instructional overlay",
        "checkpointReached": "green checkmark appears with point increment",
        "taskComplete": "confetti animation and summary display",
        "incorrectAttempt": "gentle hint prompt appears"
    },
    "learningObjectives": [
        "Understand the relationship between launch angle and projectile range",
        "Identify the optimal angle for maximum range",
        "Predict projectile behavior based on parameter changes"
    ],
    "targetBloomsLevel": "apply",
    "estimatedDurationMinutes": 15
}


if __name__ == "__main__":
    # Validate example blueprint
    result = validate_phet_blueprint(EXAMPLE_BLUEPRINT)
    print(f"Validation result: {result['valid']}")
    if result['errors']:
        print(f"Errors: {result['errors']}")
    if result['warnings']:
        print(f"Warnings: {result['warnings']}")
