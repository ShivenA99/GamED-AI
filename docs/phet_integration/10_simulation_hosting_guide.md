# PhET Simulation Hosting and Modification Guide

## Overview

This document details how to host PhET simulations and modify them for integration with GamED.AI v2. There are three primary approaches, each with different trade-offs.

## Hosting Approaches

### Approach 1: Direct CDN Embedding (Simplest)

**Description**: Embed PhET simulations directly from the official CDN.

**Implementation**:
```html
<iframe
  src="https://phet.colorado.edu/sims/html/projectile-motion/latest/projectile-motion_all.html"
  width="800"
  height="600"
  allowfullscreen>
</iframe>
```

**Pros**:
- No hosting required
- Always up-to-date
- Zero maintenance

**Cons**:
- No state access (cannot track student interactions)
- No customization possible
- Limited assessment integration
- Requires internet connection

**Use Case**: Preview/demo mode only. NOT suitable for production assessment.

---

### Approach 2: Self-Hosted Modified Simulations (Recommended for Free Tier)

**Description**: Clone, modify, and self-host PhET simulations with bridge module injection.

**Implementation Steps**:

#### Step 1: Clone Required Repositories
```bash
# Create working directory
mkdir phet-sims && cd phet-sims

# Clone core dependencies
git clone https://github.com/phetsims/chipper.git
git clone https://github.com/phetsims/perennial.git
git clone https://github.com/phetsims/perennial-alias.git

# Clone common libraries
git clone https://github.com/phetsims/axon.git
git clone https://github.com/phetsims/scenery.git
git clone https://github.com/phetsims/sun.git
git clone https://github.com/phetsims/joist.git
git clone https://github.com/phetsims/dot.git
git clone https://github.com/phetsims/kite.git
git clone https://github.com/phetsims/phet-core.git
git clone https://github.com/phetsims/scenery-phet.git
git clone https://github.com/phetsims/tambo.git
git clone https://github.com/phetsims/tandem.git
git clone https://github.com/phetsims/utterance-queue.git
git clone https://github.com/phetsims/brand.git
git clone https://github.com/phetsims/sherpa.git
git clone https://github.com/phetsims/assert.git
git clone https://github.com/phetsims/phetcommon.git
git clone https://github.com/phetsims/query-string-machine.git

# Clone specific simulation (example: projectile-motion)
git clone https://github.com/phetsims/projectile-motion.git
```

#### Step 2: Install Dependencies
```bash
cd chipper && npm install
cd ../perennial && npm install
cd ../projectile-motion && npm install
```

#### Step 3: Inject Bridge Module (see Bridge Module section below)

#### Step 4: Build with Custom Brand
```bash
cd projectile-motion
grunt --brands=adapted-from-phet
```

**Output**: Single HTML file at `build/adapted-from-phet/projectile-motion_all_adapted-from-phet.html`

**Pros**:
- Full state access through injected bridge
- Custom branding
- Offline capable
- CC BY 4.0 license (free for educational use)

**Cons**:
- Requires build process
- Must maintain forked versions
- Updates require manual sync

---

### Approach 3: PhET-iO Licensed Integration (Premium)

**Description**: Use PhET-iO's official API for deep simulation control.

**Requirements**:
- Commercial license from University of Colorado Boulder
- Contact: phetio@colorado.edu

**Features**:
- Full state serialization via phetioIDs
- Event streaming and logging
- Save/restore simulation state
- API stability guarantee (5 years)

**Implementation**:
```javascript
// Load PhET-iO library
const phetioClient = new phetio.PhetioClient(iframe);

// Launch simulation
await phetioClient.launchSimulation();

// Get state
const state = await phetioClient.getState();

// Set property
await phetioClient.invoke(
  'projectileMotion.introScreen.model.cannonAngleProperty',
  'setValue',
  [45]
);

// Listen to changes
phetioClient.addListener('projectileMotion.introScreen.model.cannonAngleProperty',
  (event) => {
    console.log('Angle changed:', event.value);
  }
);
```

**Pros**:
- Official API with stability guarantee
- Complete state access
- Event streaming
- Studio tool for exploration

**Cons**:
- Requires paid license
- Higher implementation complexity

---

## Bridge Module Implementation (Approach 2)

For self-hosted simulations, we inject a bridge module that exposes simulation state via postMessage.

### Bridge Module Code

```javascript
// gamed-bridge.js - Inject into PhET simulation

(function() {
  'use strict';

  const BRIDGE_VERSION = '1.0.0';
  const ORIGIN_WHITELIST = ['*']; // Configure for production

  // Wait for simulation to fully load
  const waitForSim = setInterval(() => {
    if (window.phet && window.phet.joist && window.phet.joist.sim) {
      clearInterval(waitForSim);
      initializeBridge();
    }
  }, 100);

  function initializeBridge() {
    const sim = window.phet.joist.sim;
    const screens = sim.screens;

    // Bridge state
    const trackedProperties = new Map();
    const interactionLog = [];

    // Send message to parent
    function sendToParent(type, data) {
      window.parent.postMessage({
        source: 'phet-gamed-bridge',
        version: BRIDGE_VERSION,
        type: type,
        data: data,
        timestamp: Date.now()
      }, '*');
    }

    // Announce bridge ready
    sendToParent('bridge-ready', {
      simName: sim.simNameProperty.value,
      screens: screens.map((s, i) => ({
        index: i,
        name: s.nameProperty ? s.nameProperty.value : `Screen ${i + 1}`
      }))
    });

    // Handle incoming messages
    window.addEventListener('message', (event) => {
      if (!event.data || event.data.target !== 'phet-gamed-bridge') return;

      const { command, params } = event.data;

      switch (command) {
        case 'get-state':
          handleGetState(params);
          break;
        case 'set-property':
          handleSetProperty(params);
          break;
        case 'track-property':
          handleTrackProperty(params);
          break;
        case 'reset':
          handleReset();
          break;
        case 'get-interactions':
          sendToParent('interactions', { log: interactionLog });
          break;
      }
    });

    function handleGetState(params) {
      const state = {};
      trackedProperties.forEach((prop, path) => {
        state[path] = prop.value;
      });
      sendToParent('state-snapshot', state);
    }

    function handleSetProperty(params) {
      const { path, value } = params;
      const prop = resolvePropertyPath(path);
      if (prop && prop.set) {
        prop.set(value);
        sendToParent('property-set', { path, value, success: true });
      } else {
        sendToParent('property-set', { path, success: false, error: 'Property not found' });
      }
    }

    function handleTrackProperty(params) {
      const { path } = params;
      const prop = resolvePropertyPath(path);

      if (prop && prop.link) {
        trackedProperties.set(path, prop);

        prop.link((value) => {
          sendToParent('property-changed', {
            path: path,
            value: value,
            timestamp: Date.now()
          });
        });

        sendToParent('track-confirmed', { path, success: true });
      } else {
        sendToParent('track-confirmed', { path, success: false });
      }
    }

    function handleReset() {
      sim.reset();
      interactionLog.length = 0;
      sendToParent('reset-complete', {});
    }

    function resolvePropertyPath(path) {
      // Path format: "screenName.model.propertyName" or "screenName.view.propertyName"
      const parts = path.split('.');
      let current = sim;

      for (const part of parts) {
        if (part === 'model' || part === 'view') {
          // Find screen by name
          const screenName = parts[0];
          const screen = screens.find(s =>
            s.tandem && s.tandem.phetioID.includes(screenName)
          ) || screens[0];
          current = part === 'model' ? screen.model : screen.view;
        } else if (current && current[part]) {
          current = current[part];
        } else if (current && current[part + 'Property']) {
          current = current[part + 'Property'];
        } else {
          return null;
        }
      }

      return current;
    }

    // Track user interactions
    function trackInteraction(type, details) {
      const interaction = {
        type: type,
        details: details,
        timestamp: Date.now()
      };
      interactionLog.push(interaction);
      sendToParent('interaction', interaction);
    }

    // Hook into scenery input system
    if (window.phet.scenery && window.phet.scenery.Display) {
      const display = sim.display;

      display.addInputListener({
        down: (event) => {
          trackInteraction('pointer-down', {
            x: event.pointer.point.x,
            y: event.pointer.point.y
          });
        },
        up: (event) => {
          trackInteraction('pointer-up', {
            x: event.pointer.point.x,
            y: event.pointer.point.y
          });
        }
      });
    }

    console.log('[GamED Bridge] Initialized for:', sim.simNameProperty.value);
  }
})();
```

### Injection Method

Add to the simulation's main HTML file before the closing `</body>` tag:

```html
<script src="gamed-bridge.js"></script>
```

Or inject dynamically during build:

```javascript
// In Gruntfile.cjs or build script
const bridgeCode = fs.readFileSync('gamed-bridge.js', 'utf8');
htmlContent = htmlContent.replace('</body>', `<script>${bridgeCode}</script></body>`);
```

---

## Simulation-Specific Integration Details

### 1. Projectile Motion

**Repository**: https://github.com/phetsims/projectile-motion

**Key Model Properties**:
| Property Path | Type | Range | Description |
|--------------|------|-------|-------------|
| `introScreen.model.cannonAngleProperty` | Number | 0-90 | Launch angle in degrees |
| `introScreen.model.initialSpeedProperty` | Number | 0-30 | Launch speed in m/s |
| `introScreen.model.initialHeightProperty` | Number | 0-15 | Launch height in meters |
| `introScreen.model.airResistanceOnProperty` | Boolean | - | Air resistance toggle |
| `introScreen.model.gravityProperty` | Number | 0-30 | Gravity in m/s² |

**Trackable Outcomes**:
- Projectile landing position
- Maximum height reached
- Time of flight
- Range achieved

**Assessment Suitability**:
- TARGET_ACHIEVEMENT: Hit specific landing zones
- PARAMETER_DISCOVERY: Find angle for maximum range
- PREDICTION_VERIFICATION: Predict trajectory outcomes

---

### 2. Circuit Construction Kit: DC

**Repository**: https://github.com/phetsims/circuit-construction-kit-dc

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `labScreen.model.circuit.circuitElements` | Array | All circuit components |
| `labScreen.model.circuit.currentProperty` | Number | Current in amperes |
| `labScreen.model.circuit.voltageProperty` | Number | Voltage in volts |

**Component Types**:
- Wire, Battery, Resistor, Light Bulb, Switch
- Each has: `resistanceProperty`, `currentProperty`, `voltageProperty`

**Assessment Suitability**:
- CONSTRUCTION: Build specific circuits
- MEASUREMENT: Measure voltage/current
- TARGET_ACHIEVEMENT: Light bulb at specific brightness

---

### 3. States of Matter

**Repository**: https://github.com/phetsims/states-of-matter

**Key Model Properties**:
| Property Path | Type | Range | Description |
|--------------|------|-------|-------------|
| `statesScreen.model.temperatureSetPointProperty` | Number | 0-500K | Target temperature |
| `statesScreen.model.pressureProperty` | Number | 0-50 atm | System pressure |
| `statesScreen.model.substanceProperty` | Enum | neon, argon, oxygen, water | Substance type |
| `statesScreen.model.phaseProperty` | Enum | solid, liquid, gas | Current phase |

**Assessment Suitability**:
- EXPLORATION: Explore phase diagram
- PARAMETER_DISCOVERY: Find melting/boiling points
- COMPARATIVE_ANALYSIS: Compare substances

---

### 4. Energy Skate Park

**Repository**: https://github.com/phetsims/energy-skate-park

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `introScreen.model.skater.positionProperty` | Vector2 | Skater position |
| `introScreen.model.skater.velocityProperty` | Vector2 | Skater velocity |
| `introScreen.model.skater.kineticEnergyProperty` | Number | KE in Joules |
| `introScreen.model.skater.potentialEnergyProperty` | Number | PE in Joules |
| `introScreen.model.skater.thermalEnergyProperty` | Number | Thermal energy |
| `introScreen.model.frictionProperty` | Number | Friction coefficient |

**Physics Equations**:
- KE = 0.5 * m * v²
- PE = m * g * h
- TE (thermal) = Ff * d
- Total = KE + PE + TE

**Assessment Suitability**:
- EXPLORATION: Explore energy transformations
- PREDICTION_VERIFICATION: Predict final position/speed
- OPTIMIZATION: Maximize height with friction

---

### 5. Forces and Motion: Basics

**Repository**: https://github.com/phetsims/forces-and-motion-basics

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `motionScreen.model.appliedForceProperty` | Number | Applied force in N |
| `motionScreen.model.frictionProperty` | Number | Friction force |
| `motionScreen.model.sumOfForcesProperty` | Number | Net force |
| `motionScreen.model.accelerationProperty` | Number | Acceleration m/s² |
| `motionScreen.model.velocityProperty` | Number | Velocity m/s |
| `motionScreen.model.positionProperty` | Number | Position in m |

**Assessment Suitability**:
- TARGET_ACHIEVEMENT: Move object to position
- PARAMETER_DISCOVERY: Find force needed
- EXPLORATION: Explore Newton's laws

---

### 6. Gravity and Orbits

**Repository**: https://github.com/phetsims/gravity-and-orbits

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `modelScreen.model.planetMoonScene.planet.massProperty` | Number | Planet mass |
| `modelScreen.model.planetMoonScene.moon.massProperty` | Number | Moon mass |
| `modelScreen.model.planetMoonScene.planetMoonDistanceProperty` | Number | Distance |
| `modelScreen.model.planetMoonScene.moon.velocityProperty` | Vector2 | Moon velocity |
| `modelScreen.model.gravityForceProperty` | Number | Gravitational force |

**Assessment Suitability**:
- EXPLORATION: Explore orbital mechanics
- TARGET_ACHIEVEMENT: Achieve stable orbit
- OPTIMIZATION: Find orbital parameters

---

### 7. Wave on a String

**Repository**: https://github.com/phetsims/wave-on-a-string

**Key Model Properties**:
| Property Path | Type | Range | Description |
|--------------|------|-------|-------------|
| `waveScreen.model.frequencyProperty` | Number | 0-3 Hz | Wave frequency |
| `waveScreen.model.amplitudeProperty` | Number | 0-1 | Wave amplitude |
| `waveScreen.model.tensionProperty` | Number | 0-1 | String tension |
| `waveScreen.model.dampingProperty` | Number | 0-1 | Damping factor |
| `waveScreen.model.waveModeProperty` | Enum | oscillate, pulse, manual | Wave mode |
| `waveScreen.model.endTypeProperty` | Enum | fixed, loose, none | End type |

**Relationships**:
- Wave speed = √(tension/linear density)
- wavelength = speed / frequency

**Assessment Suitability**:
- PARAMETER_DISCOVERY: Find standing wave conditions
- COMPARATIVE_ANALYSIS: Compare end types
- MEASUREMENT: Measure wavelength

---

### 8. Gas Properties

**Repository**: https://github.com/phetsims/gas-properties

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `idealScreen.model.pressureProperty` | Number | Pressure (atm) |
| `idealScreen.model.volumeProperty` | Number | Container volume |
| `idealScreen.model.temperatureProperty` | Number | Temperature (K) |
| `idealScreen.model.numberOfParticlesProperty` | Number | Particle count |
| `idealScreen.model.holdConstantProperty` | Enum | nothing, volume, temperature, pressure |

**Physics (Ideal Gas Law)**: PV = NkT

**Assessment Suitability**:
- EXPLORATION: Explore gas laws
- PARAMETER_DISCOVERY: Discover PV=NkT
- PREDICTION_VERIFICATION: Predict pressure changes

---

### 9. Pendulum Lab

**Repository**: https://github.com/phetsims/pendulum-lab

**Key Model Properties**:
| Property Path | Type | Range | Description |
|--------------|------|-------|-------------|
| `labScreen.model.pendulum1.lengthProperty` | Number | 0.1-1 m | Pendulum length |
| `labScreen.model.pendulum1.massProperty` | Number | 0.1-1.5 kg | Bob mass |
| `labScreen.model.pendulum1.angleProperty` | Number | -180-180° | Current angle |
| `labScreen.model.gravityProperty` | Number | 0-25 m/s² | Gravity |
| `labScreen.model.frictionProperty` | Number | 0-1 | Damping |

**Physics**:
- Period T ≈ 2π√(L/g) for small angles
- θ'' + (g/L)sin(θ) = 0

**Assessment Suitability**:
- PARAMETER_DISCOVERY: Find period dependence
- MEASUREMENT: Measure period
- COMPARATIVE_ANALYSIS: Compare different parameters

---

### 10. Masses and Springs

**Repository**: https://github.com/phetsims/masses-and-springs

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `introScreen.model.spring1.springConstantProperty` | Number | Spring constant k |
| `introScreen.model.spring1.naturalRestingLengthProperty` | Number | Rest length |
| `introScreen.model.spring1.displacementProperty` | Number | Displacement |
| `introScreen.model.mass1.massProperty` | Number | Mass value |
| `introScreen.model.gravityProperty` | Number | Gravity |
| `introScreen.model.dampingProperty` | Number | Damping coefficient |

**Physics**:
- F = -kx (Hooke's Law)
- Period T = 2π√(m/k)
- ms² + bs + k = 0 (damped oscillator)

**Assessment Suitability**:
- MEASUREMENT: Measure spring constant
- PARAMETER_DISCOVERY: Find mass from oscillation
- PREDICTION_VERIFICATION: Predict equilibrium position

---

### 11. Faraday's Law

**Repository**: https://github.com/phetsims/faradays-law

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `screen.model.magnetModel.positionProperty` | Vector2 | Magnet position |
| `screen.model.magnetModel.fluxProperty` | Number | Magnetic flux |
| `screen.model.voltmeterModel.voltageProperty` | Number | Induced EMF |
| `screen.model.coilModel.numberOfLoopsProperty` | Number | Coil loops |

**Physics**: EMF = -dΦ/dt (Faraday's Law)

**Assessment Suitability**:
- EXPLORATION: Explore electromagnetic induction
- PARAMETER_DISCOVERY: Find factors affecting EMF
- MEASUREMENT: Measure induced voltage

---

### 12. Balancing Act

**Repository**: https://github.com/phetsims/balancing-act

**Key Model Properties**:
| Property Path | Type | Description |
|--------------|------|-------------|
| `balanceLabScreen.model.plank.tiltAngleProperty` | Number | Plank tilt angle |
| `balanceLabScreen.model.masses` | Array | Masses on plank |
| `balanceLabScreen.model.isBalancedProperty` | Boolean | Balance state |

**Physics**: τ = r × F (Torque), Balance when Σ(m*d) = 0

**Assessment Suitability**:
- TARGET_ACHIEVEMENT: Achieve balance
- PREDICTION_VERIFICATION: Predict balance position
- CONSTRUCTION: Place masses to balance

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GamED.AI Frontend                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            PhetSimulationGame Component               │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │              usePhetBridge Hook                 │  │  │
│  │  │         (postMessage communication)             │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                         │                              │  │
│  │                         │ postMessage                  │  │
│  │                         ▼                              │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │              <iframe>                           │  │  │
│  │  │    ┌─────────────────────────────────────────┐  │  │  │
│  │  │    │     Modified PhET Simulation           │  │  │  │
│  │  │    │  ┌───────────────────────────────────┐ │  │  │  │
│  │  │    │  │       GamED Bridge Module        │ │  │  │  │
│  │  │    │  │   (injected during build)        │ │  │  │  │
│  │  │    │  └───────────────────────────────────┘ │  │  │  │
│  │  │    └─────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Load simulation
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Self-Hosted Simulation Server                   │
│  /simulations/                                               │
│    ├── projectile-motion/                                   │
│    │   └── projectile-motion_all_gamed.html                 │
│    ├── circuit-construction-kit-dc/                         │
│    │   └── circuit-construction-kit-dc_all_gamed.html       │
│    ├── states-of-matter/                                    │
│    │   └── states-of-matter_all_gamed.html                  │
│    └── ... (other simulations)                              │
└─────────────────────────────────────────────────────────────┘
```

## Licensing Requirements

### CC BY 4.0 (Free PhET Simulations)
- Can modify and redistribute
- Must provide attribution
- Must indicate changes made
- Cannot use PhET trademark for marketing

**Required Attribution**:
```
Based on PhET Interactive Simulations
University of Colorado Boulder
https://phet.colorado.edu
Licensed under CC BY 4.0
```

### PhET-iO (Commercial License)
- Contact: phetio@colorado.edu
- Required for full state API access
- Annual licensing fee applies

## Build Automation Script

```bash
#!/bin/bash
# build-phet-sims.sh - Build all simulations for GamED.AI

SIMS=(
  "projectile-motion"
  "circuit-construction-kit-dc"
  "states-of-matter"
  "energy-skate-park"
  "forces-and-motion-basics"
  "gravity-and-orbits"
  "wave-on-a-string"
  "gas-properties"
  "pendulum-lab"
  "masses-and-springs"
  "faradays-law"
  "balancing-act"
)

BRIDGE_JS="./gamed-bridge.js"
OUTPUT_DIR="./dist/simulations"

for sim in "${SIMS[@]}"; do
  echo "Building $sim..."
  cd "$sim"

  # Build with adapted-from-phet brand
  grunt --brands=adapted-from-phet

  # Inject bridge module
  OUTPUT_FILE="build/adapted-from-phet/${sim}_all_adapted-from-phet.html"
  BRIDGE_CODE=$(cat "$BRIDGE_JS")
  sed -i "s|</body>|<script>${BRIDGE_CODE}</script></body>|" "$OUTPUT_FILE"

  # Copy to output directory
  mkdir -p "$OUTPUT_DIR/$sim"
  cp "$OUTPUT_FILE" "$OUTPUT_DIR/$sim/${sim}_all_gamed.html"

  cd ..
done

echo "Build complete! Simulations available in $OUTPUT_DIR"
```

## Sources

- [PhET Interactive Simulations](https://phet.colorado.edu/)
- [PhET GitHub Organization](https://github.com/phetsims)
- [PhET Development Overview](https://github.com/phetsims/phet-info/blob/main/doc/phet-development-overview.md)
- [PhET-iO Developer Guide](https://phet-io.colorado.edu/devguide/)
- [Axon Property Documentation](https://github.com/phetsims/axon)
- [PhET Source Code](https://phet.colorado.edu/en/about/source-code)
- [PhET Licensing](https://phet.colorado.edu/en/licensing/html)
