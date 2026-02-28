# PhET Simulation Test Cases & Agent Flow Analysis

This document provides test queries for each PhET simulation and details how the agent pipeline processes them into interactive assessments.

---

## Agent Pipeline Overview

```
User Query
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. ROUTER AGENT                                                  │
│    • Analyzes query for physics/chemistry/science keywords       │
│    • Detects simulation-appropriate topics                       │
│    • Returns: template_type = "PHET_SIMULATION"                  │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. PEDAGOGICAL CONTEXT AGENT                                     │
│    • Determines Bloom's taxonomy level                           │
│    • Identifies subject area and grade level                     │
│    • Sets difficulty and learning objectives                     │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. PHET SIMULATION SELECTOR AGENT                                │
│    • Matches query to SIMULATION_CATALOG                         │
│    • Considers available parameters and outcomes                 │
│    • Returns: simulationId, confidence, reasoning                │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. PHET GAME PLANNER AGENT                                       │
│    • Selects assessment type based on Bloom's level              │
│    • Designs task sequence and learning progression              │
│    • Plans which simulation features to use                      │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. PHET ASSESSMENT DESIGNER AGENT                                │
│    • Creates specific checkpoints with conditions                │
│    • Defines measurable success criteria                         │
│    • Maps conditions to simulation properties                    │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. PHET BLUEPRINT GENERATOR AGENT                                │
│    • Assembles complete blueprint JSON                           │
│    • Adds narrative, hints, scoring rubric                       │
│    • Validates against schema                                    │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. PHET BLUEPRINT VALIDATOR AGENT                                │
│    • Validates blueprint structure                               │
│    • Checks cross-references (task IDs, checkpoint IDs)          │
│    • Retries up to 3 times if validation fails                   │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. PHET BRIDGE CONFIG GENERATOR AGENT                            │
│    • Extracts required properties from checkpoints               │
│    • Generates bridge configuration for tracking                 │
│    • Sets generation_complete = true                             │
└─────────────────────────────────────────────────────────────────┘
    ↓
Frontend: PhetSimulationGame Component
    ↓
usePhetBridge Hook ↔ PhET Simulation (postMessage)
```

---

## Test Case 1: Projectile Motion

### Test Query
```
"What factors affect how far a projectile travels? Explore the relationship between launch angle and range."
```

### Agent Flow

#### Router Agent
```json
{
  "template_type": "PHET_SIMULATION",
  "confidence": 0.95,
  "reasoning": "Query involves projectile motion physics, asks about relationships between variables - ideal for interactive simulation"
}
```

#### Pedagogical Context Agent
```json
{
  "subject": "physics",
  "topic": "kinematics",
  "blooms_level": "analyze",
  "grade_level": "high_school",
  "difficulty": "intermediate",
  "learning_objectives": [
    "Understand factors affecting projectile range",
    "Discover optimal launch angle for maximum range",
    "Analyze relationship between angle and distance"
  ]
}
```

#### PhET Simulation Selector Agent
```json
{
  "simulationId": "projectile-motion",
  "confidence": 0.98,
  "reasoning": "Projectile motion simulation directly addresses launch angle and range relationships",
  "simulationMetadata": {
    "name": "Projectile Motion",
    "parameters": ["cannonAngle", "initialSpeed", "initialHeight", "airResistance", "gravity"],
    "outcomes": ["range", "maxHeight", "timeOfFlight"]
  }
}
```

#### PhET Game Planner Agent
```json
{
  "assessmentType": "parameter_discovery",
  "learningObjectives": [
    "Discover that 45° maximizes range (no air resistance)",
    "Understand angle-range relationship is parabolic",
    "Recognize air resistance shifts optimal angle"
  ],
  "taskSequence": [
    {
      "phase": "exploration",
      "goal": "Fire projectiles at different angles, observe range"
    },
    {
      "phase": "hypothesis",
      "goal": "Predict which angle gives maximum range"
    },
    {
      "phase": "verification",
      "goal": "Find the exact optimal angle"
    },
    {
      "phase": "extension",
      "goal": "Test with air resistance enabled"
    }
  ],
  "parametersToVary": ["cannonAngle"],
  "parametersToHold": ["initialSpeed", "initialHeight"],
  "outcomesToMeasure": ["range"]
}
```

#### PhET Assessment Designer Agent
```json
{
  "tasks": [
    {
      "id": "task_explore",
      "title": "Explore Launch Angles",
      "description": "Fire projectiles at 5 different angles and observe how far they travel",
      "checkpoints": [
        {
          "id": "cp_varied_angles",
          "description": "Try at least 5 different angles",
          "condition": {
            "type": "exploration_breadth",
            "property": "cannonAngle",
            "minUniqueValues": 5,
            "tolerance": 5
          },
          "points": 15
        }
      ]
    },
    {
      "id": "task_find_optimal",
      "title": "Find Maximum Range",
      "description": "Discover the angle that makes the projectile travel the farthest",
      "checkpoints": [
        {
          "id": "cp_optimal_angle",
          "description": "Set angle to approximately 45 degrees",
          "condition": {
            "type": "property_range",
            "property": "cannonAngle",
            "min": 43,
            "max": 47
          },
          "points": 25
        },
        {
          "id": "cp_max_range_achieved",
          "description": "Achieve maximum possible range",
          "condition": {
            "type": "outcome_achieved",
            "outcome": "range",
            "comparison": ">=",
            "threshold": 18
          },
          "points": 20
        }
      ]
    }
  ]
}
```

#### Bridge Config Generator
```json
{
  "bridgeConfig": {
    "simulationUrl": "/simulations/projectile-motion/projectile-motion_gamed.html",
    "trackProperties": [
      { "path": "model.cannonAngleProperty", "alias": "cannonAngle" },
      { "path": "model.initialSpeedProperty", "alias": "initialSpeed" },
      { "path": "model.rangeProperty", "alias": "range" }
    ],
    "trackInteractions": ["fire", "reset", "parameterChange"],
    "trackOutcomes": ["projectileLanded"]
  }
}
```

### Frontend Interaction Flow

1. **Load**: PhetSimulationGame mounts, loads iframe with projectile-motion_gamed.html
2. **Bridge Ready**: usePhetBridge receives `bridge-ready` message
3. **Track Properties**: Sends `track-properties-batch` for cannonAngle, initialSpeed, range
4. **User Explores**: User changes angle slider → `property-changed` events received
5. **User Fires**: User clicks fire → `interaction` event with type "fire"
6. **Projectile Lands**: `property-changed` for range with final value
7. **Checkpoint Evaluation**: usePhetSimulationState evaluates:
   - Has user tried 5+ different angles? → Check exploration_breadth
   - Is current angle 43-47°? → Check property_range
   - Did range exceed 18m? → Check outcome_achieved
8. **Score Update**: Each checkpoint completion triggers score update
9. **Task Progression**: When all checkpoints complete, advance to next task

---

## Test Case 2: Circuit Construction Kit: DC

### Test Query
```
"Build a circuit with a battery and light bulb. What happens when you add more batteries in series?"
```

### Agent Flow

#### Router Agent
```json
{
  "template_type": "PHET_SIMULATION",
  "confidence": 0.96,
  "reasoning": "Electrical circuits, batteries, light bulbs - perfect for circuit construction simulation"
}
```

#### PhET Simulation Selector Agent
```json
{
  "simulationId": "circuit-construction-kit-dc",
  "confidence": 0.99,
  "reasoning": "Direct match for circuit building with batteries and light bulbs",
  "simulationMetadata": {
    "parameters": ["batteryVoltage", "resistance", "wireResistivity"],
    "interactions": ["connect", "disconnect", "addComponent", "removeComponent"],
    "outcomes": ["current", "voltage", "brightness"]
  }
}
```

#### PhET Game Planner Agent
```json
{
  "assessmentType": "construction",
  "learningObjectives": [
    "Build a complete circuit",
    "Understand series circuit behavior",
    "Observe voltage addition in series"
  ],
  "taskSequence": [
    {
      "phase": "build_basic",
      "goal": "Create circuit with 1 battery, 1 bulb"
    },
    {
      "phase": "observe",
      "goal": "Note bulb brightness"
    },
    {
      "phase": "modify",
      "goal": "Add second battery in series"
    },
    {
      "phase": "analyze",
      "goal": "Compare brightness, explain why"
    }
  ]
}
```

#### PhET Assessment Designer Agent
```json
{
  "tasks": [
    {
      "id": "task_basic_circuit",
      "title": "Build a Simple Circuit",
      "description": "Connect a battery to a light bulb to make it light up",
      "checkpoints": [
        {
          "id": "cp_circuit_complete",
          "description": "Create a complete circuit with current flowing",
          "condition": {
            "type": "property_range",
            "property": "current",
            "min": 0.1,
            "max": 100
          },
          "points": 20
        },
        {
          "id": "cp_bulb_lit",
          "description": "Light bulb is glowing",
          "condition": {
            "type": "outcome_achieved",
            "outcome": "bulbBrightness",
            "comparison": ">",
            "threshold": 0
          },
          "points": 15
        }
      ]
    },
    {
      "id": "task_series_batteries",
      "title": "Add Batteries in Series",
      "description": "Add a second battery in series and observe what happens to the light bulb",
      "checkpoints": [
        {
          "id": "cp_two_batteries",
          "description": "Circuit has two batteries",
          "condition": {
            "type": "property_equals",
            "property": "batteryCount",
            "value": 2
          },
          "points": 15
        },
        {
          "id": "cp_increased_brightness",
          "description": "Bulb is brighter than before",
          "condition": {
            "type": "property_range",
            "property": "bulbBrightness",
            "min": 0.7,
            "max": 1.0
          },
          "points": 20
        }
      ]
    }
  ]
}
```

### Bridge Interactions
```javascript
// Track component counts and circuit state
trackProperties: [
  { path: "model.circuit.circuitElements.length", alias: "componentCount" },
  { path: "model.circuit.currentProperty", alias: "current" },
  { path: "model.circuit.batteries.length", alias: "batteryCount" }
]

// Track construction interactions
trackInteractions: ["componentAdded", "componentRemoved", "connectionMade"]
```

---

## Test Case 3: States of Matter

### Test Query
```
"What happens to water molecules when you heat ice? Explore how temperature affects the state of matter."
```

### Agent Flow

#### PhET Simulation Selector Agent
```json
{
  "simulationId": "states-of-matter",
  "confidence": 0.97,
  "reasoning": "Phase transitions with temperature control, molecular visualization"
}
```

#### PhET Game Planner Agent
```json
{
  "assessmentType": "exploration",
  "learningObjectives": [
    "Observe molecular behavior in different phases",
    "Identify melting and boiling points",
    "Understand energy and phase relationships"
  ],
  "taskSequence": [
    {
      "phase": "solid",
      "goal": "Observe ice at low temperature"
    },
    {
      "phase": "melting",
      "goal": "Heat to melting point, observe transition"
    },
    {
      "phase": "liquid",
      "goal": "Observe liquid water molecules"
    },
    {
      "phase": "boiling",
      "goal": "Heat to boiling, observe gas phase"
    }
  ]
}
```

#### Assessment Designer Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_start_solid",
      "condition": {
        "type": "property_equals",
        "property": "phase",
        "value": "solid"
      }
    },
    {
      "id": "cp_reach_melting",
      "condition": {
        "type": "property_range",
        "property": "temperature",
        "min": 270,
        "max": 280
      }
    },
    {
      "id": "cp_observe_liquid",
      "condition": {
        "type": "property_equals",
        "property": "phase",
        "value": "liquid"
      }
    },
    {
      "id": "cp_reach_boiling",
      "condition": {
        "type": "property_range",
        "property": "temperature",
        "min": 370,
        "max": 380
      }
    },
    {
      "id": "cp_observe_gas",
      "condition": {
        "type": "property_equals",
        "property": "phase",
        "value": "gas"
      }
    }
  ]
}
```

---

## Test Case 4: Energy Skate Park

### Test Query
```
"How does a skateboarder's energy change as they move along a half-pipe? Explore kinetic and potential energy."
```

### Agent Flow

#### PhET Simulation Selector
```json
{
  "simulationId": "energy-skate-park",
  "confidence": 0.99,
  "reasoning": "Perfect match for energy transformation visualization"
}
```

#### Game Planner
```json
{
  "assessmentType": "exploration",
  "learningObjectives": [
    "Understand KE/PE relationship",
    "Observe energy conservation",
    "Analyze energy at different track positions"
  ]
}
```

#### Assessment Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_max_height",
      "description": "Position skater at maximum height",
      "condition": {
        "type": "property_range",
        "property": "potentialEnergy",
        "min": 900,
        "max": 1100
      }
    },
    {
      "id": "cp_max_speed",
      "description": "Observe skater at bottom (max kinetic energy)",
      "condition": {
        "type": "property_range",
        "property": "kineticEnergy",
        "min": 900,
        "max": 1100
      }
    },
    {
      "id": "cp_energy_conserved",
      "description": "Total energy remains constant",
      "condition": {
        "type": "property_range",
        "property": "totalEnergy",
        "min": 950,
        "max": 1050
      }
    }
  ]
}
```

---

## Test Case 5: Forces and Motion: Basics

### Test Query
```
"How much force is needed to move a heavy box? Explore Newton's laws of motion."
```

### Agent Flow

#### Assessment Type Selection
```json
{
  "assessmentType": "target_achievement",
  "reasoning": "Task involves achieving specific motion outcomes through force application"
}
```

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_apply_force",
      "description": "Apply force to the box",
      "condition": {
        "type": "property_range",
        "property": "appliedForce",
        "min": 1,
        "max": 500
      }
    },
    {
      "id": "cp_overcome_friction",
      "description": "Apply enough force to overcome friction",
      "condition": {
        "type": "property_range",
        "property": "velocity",
        "min": 0.1,
        "max": 50
      }
    },
    {
      "id": "cp_reach_position",
      "description": "Move box to target position",
      "condition": {
        "type": "property_range",
        "property": "position",
        "min": 5,
        "max": 10
      }
    }
  ]
}
```

---

## Test Case 6: Gravity and Orbits

### Test Query
```
"What keeps the Moon orbiting Earth? Explore gravitational forces and orbital motion."
```

### Agent Flow

#### Game Planner
```json
{
  "assessmentType": "exploration",
  "taskSequence": [
    { "phase": "observe", "goal": "Watch natural orbit" },
    { "phase": "experiment", "goal": "Change moon velocity" },
    { "phase": "analyze", "goal": "Find stable orbit parameters" }
  ]
}
```

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_observe_orbit",
      "description": "Watch moon complete one orbit",
      "condition": {
        "type": "time_spent",
        "minSeconds": 30
      }
    },
    {
      "id": "cp_stable_orbit",
      "description": "Achieve stable circular orbit",
      "condition": {
        "type": "outcome_achieved",
        "outcome": "orbitalStability",
        "comparison": ">=",
        "threshold": 0.9
      }
    },
    {
      "id": "cp_vary_velocity",
      "description": "Experiment with different velocities",
      "condition": {
        "type": "exploration_breadth",
        "property": "moonVelocity",
        "minUniqueValues": 3
      }
    }
  ]
}
```

---

## Test Case 7: Wave on a String

### Test Query
```
"How do frequency and amplitude affect a wave? Create different wave patterns on a string."
```

### Agent Flow

#### Assessment Type
```json
{
  "assessmentType": "parameter_discovery",
  "reasoning": "Discovering relationships between wave parameters"
}
```

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_create_wave",
      "description": "Generate a wave on the string",
      "condition": {
        "type": "property_range",
        "property": "amplitude",
        "min": 0.1,
        "max": 1.0
      }
    },
    {
      "id": "cp_vary_frequency",
      "description": "Try different frequencies",
      "condition": {
        "type": "exploration_breadth",
        "property": "frequency",
        "minUniqueValues": 4
      }
    },
    {
      "id": "cp_standing_wave",
      "description": "Create a standing wave pattern",
      "condition": {
        "type": "property_equals",
        "property": "endType",
        "value": "fixed"
      }
    }
  ]
}
```

---

## Test Case 8: Gas Properties

### Test Query
```
"What happens to pressure when you decrease the volume of a gas container? Explore the ideal gas law."
```

### Agent Flow

#### Assessment Type
```json
{
  "assessmentType": "parameter_discovery",
  "reasoning": "Discovering PV=NkT relationship"
}
```

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_baseline",
      "description": "Observe initial pressure at default volume",
      "condition": {
        "type": "time_spent",
        "minSeconds": 10
      }
    },
    {
      "id": "cp_decrease_volume",
      "description": "Decrease container volume",
      "condition": {
        "type": "property_range",
        "property": "volume",
        "min": 5,
        "max": 10
      }
    },
    {
      "id": "cp_pressure_increased",
      "description": "Observe pressure increase",
      "condition": {
        "type": "property_range",
        "property": "pressure",
        "min": 15,
        "max": 30
      }
    },
    {
      "id": "cp_pv_constant",
      "description": "Verify P*V remains approximately constant",
      "condition": {
        "type": "outcome_achieved",
        "outcome": "pvProduct",
        "comparison": "range",
        "min": 95,
        "max": 105
      }
    }
  ]
}
```

---

## Test Case 9: Pendulum Lab

### Test Query
```
"What affects how fast a pendulum swings? Investigate the period of a simple pendulum."
```

### Agent Flow

#### Assessment Type
```json
{
  "assessmentType": "measurement",
  "reasoning": "Measuring period and finding relationships"
}
```

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_measure_period",
      "description": "Use period timer to measure one swing",
      "condition": {
        "type": "interaction_occurred",
        "interaction": "periodTimerUsed"
      }
    },
    {
      "id": "cp_vary_length",
      "description": "Try different pendulum lengths",
      "condition": {
        "type": "exploration_breadth",
        "property": "length",
        "minUniqueValues": 4
      }
    },
    {
      "id": "cp_vary_mass",
      "description": "Try different masses (should not affect period)",
      "condition": {
        "type": "exploration_breadth",
        "property": "mass",
        "minUniqueValues": 3
      }
    },
    {
      "id": "cp_discover_relationship",
      "description": "Find that only length affects period",
      "condition": {
        "type": "time_spent",
        "minSeconds": 120
      }
    }
  ]
}
```

---

## Test Case 10: Masses and Springs

### Test Query
```
"How does the spring constant affect oscillation? Hang different masses and observe the motion."
```

### Agent Flow

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_attach_mass",
      "description": "Attach a mass to the spring",
      "condition": {
        "type": "property_range",
        "property": "displacement",
        "min": 0.01,
        "max": 1.0
      }
    },
    {
      "id": "cp_observe_oscillation",
      "description": "Watch the mass oscillate",
      "condition": {
        "type": "time_spent",
        "minSeconds": 15
      }
    },
    {
      "id": "cp_vary_mass",
      "description": "Try different masses",
      "condition": {
        "type": "exploration_breadth",
        "property": "mass",
        "minUniqueValues": 3
      }
    },
    {
      "id": "cp_vary_spring",
      "description": "Adjust spring constant",
      "condition": {
        "type": "exploration_breadth",
        "property": "springConstant",
        "minUniqueValues": 3
      }
    }
  ]
}
```

---

## Test Case 11: Faraday's Law

### Test Query
```
"How can you generate electricity with a magnet? Explore electromagnetic induction."
```

### Agent Flow

#### Assessment Type
```json
{
  "assessmentType": "exploration",
  "reasoning": "Exploring electromagnetic induction through interaction"
}
```

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_move_magnet",
      "description": "Move the magnet near the coil",
      "condition": {
        "type": "property_changed",
        "property": "magnetPosition"
      }
    },
    {
      "id": "cp_generate_voltage",
      "description": "Induce a voltage in the coil",
      "condition": {
        "type": "property_range",
        "property": "voltage",
        "min": 0.1,
        "max": 100
      }
    },
    {
      "id": "cp_reverse_direction",
      "description": "Move magnet in opposite direction",
      "condition": {
        "type": "interaction_occurred",
        "interaction": "magnetDirectionReversed"
      }
    },
    {
      "id": "cp_max_voltage",
      "description": "Achieve maximum voltage by moving quickly",
      "condition": {
        "type": "property_range",
        "property": "voltage",
        "min": 5,
        "max": 20
      }
    }
  ]
}
```

---

## Test Case 12: Balancing Act

### Test Query
```
"How do you balance a seesaw? Place masses to make the plank level."
```

### Agent Flow

#### Assessment Type
```json
{
  "assessmentType": "target_achievement",
  "reasoning": "Goal is to achieve balance state"
}
```

#### Checkpoints
```json
{
  "checkpoints": [
    {
      "id": "cp_place_mass",
      "description": "Place a mass on the plank",
      "condition": {
        "type": "property_range",
        "property": "massCount",
        "min": 1,
        "max": 10
      }
    },
    {
      "id": "cp_both_sides",
      "description": "Place masses on both sides",
      "condition": {
        "type": "property_range",
        "property": "leftSideMassCount",
        "min": 1,
        "max": 10
      }
    },
    {
      "id": "cp_achieve_balance",
      "description": "Balance the plank",
      "condition": {
        "type": "property_equals",
        "property": "isBalanced",
        "value": true
      }
    },
    {
      "id": "cp_predict_balance",
      "description": "Predict where to place mass before testing",
      "condition": {
        "type": "interaction_occurred",
        "interaction": "predictionMade"
      }
    }
  ]
}
```

---

## Summary: Test Queries Quick Reference

| Simulation | Test Query | Assessment Type |
|------------|------------|-----------------|
| **Projectile Motion** | "What factors affect how far a projectile travels? Explore the relationship between launch angle and range." | parameter_discovery |
| **Circuit Construction Kit** | "Build a circuit with a battery and light bulb. What happens when you add more batteries in series?" | construction |
| **States of Matter** | "What happens to water molecules when you heat ice? Explore how temperature affects the state of matter." | exploration |
| **Energy Skate Park** | "How does a skateboarder's energy change as they move along a half-pipe?" | exploration |
| **Forces and Motion** | "How much force is needed to move a heavy box? Explore Newton's laws." | target_achievement |
| **Gravity and Orbits** | "What keeps the Moon orbiting Earth? Explore gravitational forces." | exploration |
| **Wave on a String** | "How do frequency and amplitude affect a wave? Create different wave patterns." | parameter_discovery |
| **Gas Properties** | "What happens to pressure when you decrease the volume? Explore the ideal gas law." | parameter_discovery |
| **Pendulum Lab** | "What affects how fast a pendulum swings? Investigate the period." | measurement |
| **Masses and Springs** | "How does the spring constant affect oscillation?" | parameter_discovery |
| **Faraday's Law** | "How can you generate electricity with a magnet?" | exploration |
| **Balancing Act** | "How do you balance a seesaw? Place masses to make the plank level." | target_achievement |

---

## Frontend-Bridge Interaction Patterns

### Pattern 1: Property Tracking for Checkpoints

```javascript
// Frontend sends track request
iframe.contentWindow.postMessage({
  target: 'phet-gamed-bridge',
  command: 'track-properties-batch',
  params: {
    properties: [
      { path: 'model.cannonAngleProperty', alias: 'angle' },
      { path: 'model.rangeProperty', alias: 'range' }
    ]
  }
}, '*');

// Bridge responds with initial values
// { type: 'track-batch-confirmed', results: [...] }

// Bridge sends updates when values change
// { type: 'property-changed', data: { path: 'angle', value: 45 } }

// Frontend evaluates checkpoint
function evaluateCheckpoint(checkpoint, simulationState) {
  const { type, property, min, max, value } = checkpoint.condition;
  const currentValue = simulationState[property];

  switch (type) {
    case 'property_range':
      return currentValue >= min && currentValue <= max;
    case 'property_equals':
      return currentValue === value;
    // ... other condition types
  }
}
```

### Pattern 2: Interaction Logging for Exploration

```javascript
// Bridge automatically logs interactions
// { type: 'interaction', data: { type: 'pointer-down', details: {...} } }

// Frontend tracks unique values for exploration_breadth
const exploredValues = new Set();

window.addEventListener('message', (event) => {
  if (event.data.type === 'property-changed') {
    const { path, value } = event.data.data;
    if (path === 'cannonAngle') {
      exploredValues.add(Math.round(value / 5) * 5); // Group by 5-degree increments
    }
  }
});

// Evaluate exploration checkpoint
if (checkpoint.condition.type === 'exploration_breadth') {
  return exploredValues.size >= checkpoint.condition.minUniqueValues;
}
```

### Pattern 3: Time-Based Checkpoints

```javascript
// Track time spent in simulation
const startTime = Date.now();
let activeTime = 0;
let lastActivityTime = Date.now();

window.addEventListener('message', (event) => {
  if (event.data.source === 'phet-gamed-bridge') {
    lastActivityTime = Date.now();
  }
});

// Periodically update active time
setInterval(() => {
  if (Date.now() - lastActivityTime < 5000) { // Active if interaction within 5s
    activeTime = (Date.now() - startTime) / 1000;
  }
}, 1000);

// Evaluate time checkpoint
if (checkpoint.condition.type === 'time_spent') {
  return activeTime >= checkpoint.condition.minSeconds;
}
```
