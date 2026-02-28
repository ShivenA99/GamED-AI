# PhET Interactive Simulations Integration

This directory contains the design documentation and proof-of-concept code for integrating PhET Interactive Simulations into the GamED.AI v2 platform.

## Overview

PhET (Physics Education Technology) provides free, interactive simulations for science and mathematics education. This integration enables GamED.AI agents to select, customize, and deploy PhET simulations as a new game template type, complete with scoring, state management, and learning analytics.

## Directory Contents

```
phet_integration/
├── README.md                              # This file
├── 01_blueprint_schema.py                 # Pydantic schema for PHET_SIMULATION blueprints
├── 02_phet_simulation_selector_agent.py   # Agent for selecting optimal simulation
├── 03_PhetSimulationGame.tsx              # React component for game player
└── PhET_Integration_Research_Report.docx  # Comprehensive research document
```

## Quick Start Integration Guide

### Phase 1: Backend Integration

1. **Add Blueprint Schema** (`backend/app/agents/schemas/`)

   Copy `01_blueprint_schema.py` to `backend/app/agents/schemas/phet_blueprint_schema.py` and add to `blueprint_schemas.py`:

   ```python
   from app.agents.schemas.phet_blueprint_schema import (
       PhetSimulationBlueprint,
       validate_phet_blueprint
   )

   TEMPLATE_SCHEMA_MAP["PHET_SIMULATION"] = PhetSimulationBlueprint
   ```

2. **Register Template in Router** (`backend/app/agents/router.py`)

   Add to `TEMPLATE_REGISTRY`:

   ```python
   "PHET_SIMULATION": {
       "description": "Embed and customize PhET interactive simulations",
       "best_for": [
           "Physics experiments and exploration",
           "Chemistry molecular visualization",
           "Mathematics concept visualization",
           "Interactive science labs"
       ],
       "blooms_alignment": ["understand", "apply", "analyze", "evaluate"],
       "domains": ["physics", "chemistry", "biology", "mathematics", "earth_science"],
       "interaction_type": "simulation",
       "complexity": "high",
       "production_ready": False  # Set to True after testing
   }
   ```

3. **Add PhET Selector Agent** (`backend/app/agents/`)

   Copy `02_phet_simulation_selector_agent.py` to `backend/app/agents/phet_simulation_selector.py`.

4. **Extend Graph Pipeline** (`backend/app/agents/graph.py`)

   Add conditional routing for PHET_SIMULATION:

   ```python
   def check_phet_template(state: AgentState) -> Literal["phet", "default"]:
       template = state.get("template_selection", {}).get("template_type")
       return "phet" if template == "PHET_SIMULATION" else "default"

   # After router node:
   graph.add_conditional_edges(
       "router",
       check_phet_template,
       {
           "phet": "phet_simulation_selector",
           "default": "game_planner"
       }
   )

   graph.add_node("phet_simulation_selector", phet_simulation_selector_agent)
   graph.add_edge("phet_simulation_selector", "game_planner")
   ```

### Phase 2: Frontend Integration

1. **Add Game Component** (`frontend/src/components/templates/`)

   Create directory `PhetSimulationGame/` and copy `03_PhetSimulationGame.tsx` as `index.tsx`.

2. **Update Game Router** (`frontend/src/app/game/[id]/page.tsx`)

   Add case for PHET_SIMULATION:

   ```tsx
   import { PhetSimulationGame } from "@/components/templates/PhetSimulationGame";

   // In template switch:
   case "PHET_SIMULATION":
     return <PhetSimulationGame blueprint={blueprint} onComplete={handleComplete} />;
   ```

3. **Update Types** (`frontend/src/types/`)

   Add PhetBlueprint types to the type definitions.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GamED.AI Backend                             │
│  ┌─────────────┐  ┌─────────────────┐  ┌────────────────────────┐  │
│  │   Router    │→ │ PhET Simulator  │→ │  Blueprint Generator   │  │
│  │   Agent     │  │ Selector Agent  │  │  (PHET_SIMULATION)     │  │
│  └─────────────┘  └─────────────────┘  └────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ Blueprint JSON
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        GamED.AI Frontend                            │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              PhetSimulationGame Component                       │ │
│  │  ┌──────────────┐  ┌────────────────┐  ┌───────────────────┐  │ │
│  │  │  Task Panel  │  │  Score Panel   │  │  Simulation Frame │  │ │
│  │  └──────────────┘  └────────────────┘  └─────────┬─────────┘  │ │
│  │                                                   │            │ │
│  │                     PhET Bridge Service ←─────────┘            │ │
│  │                     (postMessage API)                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ postMessage
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     PhET Simulation (iframe)                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  PhET-iO Layer (Tandem, phetioIDs, state serialization)        │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │ │
│  │  │   Model     │  │    View     │  │  Event Emission         │ │ │
│  │  │  (Axon)     │  │  (Scenery)  │  │  (propertyValueChange)  │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Available PhET Simulations (Initial Catalog)

| Simulation | Domain | Key Concepts | PhET-iO Support |
|------------|--------|--------------|-----------------|
| projectile-motion | Physics | Kinematics, vectors, gravity | Full |
| circuit-construction-kit-dc | Physics | Circuits, Ohm's law | Full |
| states-of-matter | Chemistry | Phases, molecular motion | Full |
| graphing-quadratics | Math | Parabolas, coefficients | Full |
| friction | Physics | Forces, Newton's laws | Full |
| waves | Physics | Wave properties | Full |
| molecule-polarity | Chemistry | Electronegativity | Full |
| energy-skate-park | Physics | Energy conservation | Full |
| pendulum-lab | Physics | Simple harmonic motion | Full |
| area-builder | Math | Geometry, area | Full |

## Example Blueprint

```json
{
  "templateType": "PHET_SIMULATION",
  "title": "Exploring Projectile Motion",
  "narrativeIntro": "Launch projectiles and discover how angle and speed affect trajectory!",
  "simulationId": "projectile-motion",
  "simulationVersion": "latest",
  "customization": {
    "launchParams": { "screen": "intro" },
    "hiddenElements": ["projectile-motion.introScreen.view.airResistancePanel"]
  },
  "tasks": [
    {
      "id": "task-1",
      "questionText": "What happens when you increase the launch angle?",
      "interactionType": "exploration",
      "checkpoints": [
        {
          "id": "cp-1",
          "description": "Launch at 30 degrees",
          "phetioID": "projectile-motion.introScreen.model.cannonAngleProperty",
          "expectedValue": 30,
          "points": 10
        }
      ]
    }
  ]
}
```

## PhET-iO API Reference

### Key Concepts

- **phetioID**: Unique identifier for simulation elements (e.g., `projectile-motion.introScreen.model.cannonAngleProperty`)
- **State**: JSON serialization of all phetioID values
- **Events**: Real-time notifications of property changes

### Common phetioID Patterns

```
{simName}.{screenName}.model.{propertyName}Property     # Model properties
{simName}.{screenName}.view.{componentName}.visibleProperty  # Visibility
{simName}.{screenName}.model.{objectName}               # Model objects
```

### PostMessage API

```javascript
// Set value
iframe.contentWindow.postMessage({
  type: 'invoke',
  phetioID: 'sim.screen.model.property',
  method: 'setValue',
  args: [newValue]
}, '*');

// Listen for changes
window.addEventListener('message', (event) => {
  if (event.data.type === 'propertyValueChange') {
    console.log(event.data.phetioID, event.data.data.newValue);
  }
});
```

## Scoring Integration

The integration maps PhET-iO events to GamED.AI's multi-dimensional scoring:

| Score Dimension | PhET-iO Source |
|-----------------|----------------|
| Accuracy | Checkpoint value matching |
| Efficiency | Time to complete tasks |
| Exploration | Unique parameters adjusted |
| Mastery | Bloom's level achievement |

## Licensing

- **PhET Simulations**: Creative Commons Attribution 4.0 (CC BY 4.0)
- **PhET Source Code**: MIT License
- **PhET-iO Enhanced**: Individual licensing (contact PhET for enterprise)

## Resources

- [PhET Website](https://phet.colorado.edu/)
- [PhET GitHub](https://github.com/phetsims)
- [PhET-iO DevGuide](https://phet-io.colorado.edu/devguide/)
- [PhET-iO API Overview](https://phet-io.colorado.edu/devguide/api_overview.html)

## Next Steps

1. Complete Phase 1 backend integration
2. Test with Projectile Motion simulation
3. Expand simulation catalog
4. Implement advanced customization options
5. Add learning analytics dashboard
