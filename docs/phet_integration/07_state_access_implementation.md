# Accessing PhET Internal State for Task-Based Assessment

## The Problem

Downloaded PhET simulations run in an iframe and don't expose internal state by default. But since the source code is MIT licensed, we can modify simulations to emit state changes.

## Solution: Add PostMessage Hooks to PhET Source

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Your GamED.AI Wrapper                          │
│                                                                     │
│   window.addEventListener('message', (e) => {                       │
│     if (e.data.type === 'PHET_STATE_CHANGE') {                     │
│       updateScore(e.data.property, e.data.value);                  │
│     }                                                               │
│   });                                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ postMessage
                              │
┌─────────────────────────────────────────────────────────────────────┐
│                    Modified PhET Simulation                         │
│                                                                     │
│   // In simulation source code:                                     │
│   angleProperty.link(value => {                                     │
│     window.parent.postMessage({                                     │
│       type: 'PHET_STATE_CHANGE',                                   │
│       property: 'cannonAngle',                                      │
│       value: value                                                  │
│     }, '*');                                                        │
│   });                                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step: Modifying PhET Simulations

### Step 1: Clone the Simulation

```bash
# Setup PhET development environment
mkdir phet-custom && cd phet-custom

# Clone required repositories
git clone https://github.com/phetsims/projectile-motion.git
git clone https://github.com/phetsims/chipper.git
git clone https://github.com/phetsims/perennial.git
git clone https://github.com/phetsims/phet-core.git
git clone https://github.com/phetsims/axon.git
git clone https://github.com/phetsims/scenery.git
git clone https://github.com/phetsims/sun.git
git clone https://github.com/phetsims/joist.git
git clone https://github.com/phetsims/tandem.git
git clone https://github.com/phetsims/dot.git
git clone https://github.com/phetsims/kite.git
git clone https://github.com/phetsims/phetcommon.git
git clone https://github.com/phetsims/scenery-phet.git
git clone https://github.com/phetsims/brand.git
git clone https://github.com/phetsims/tambo.git
git clone https://github.com/phetsims/utterance-queue.git

# Install dependencies
cd chipper && npm install && cd ..
cd perennial && npm install && cd ..
cd projectile-motion && npm install
```

### Step 2: Add State Bridge Module

Create a reusable bridge module that any simulation can use:

**File: `phet-custom/phet-core/js/GamEdBridge.ts`**

```typescript
/**
 * GamED.AI Bridge - Exposes PhET simulation state to parent window
 * Add this to any PhET simulation for state tracking
 */

type PropertyValue = number | string | boolean | object;

interface StateChangeEvent {
  type: 'PHET_STATE_CHANGE';
  simulationId: string;
  property: string;
  value: PropertyValue;
  previousValue?: PropertyValue;
  timestamp: number;
}

interface UserInteractionEvent {
  type: 'PHET_USER_INTERACTION';
  simulationId: string;
  interaction: string;
  target: string;
  data?: object;
  timestamp: number;
}

interface SimulationReadyEvent {
  type: 'PHET_SIMULATION_READY';
  simulationId: string;
  availableProperties: string[];
  timestamp: number;
}

class GamEdBridge {
  private simulationId: string;
  private trackedProperties: Map<string, any> = new Map();
  private isReady: boolean = false;

  constructor(simulationId: string) {
    this.simulationId = simulationId;
    this.setupCommandListener();
  }

  /**
   * Track a Property and emit changes to parent
   */
  trackProperty(name: string, property: { link: Function; value: any }) {
    this.trackedProperties.set(name, property);

    property.link((value: PropertyValue, oldValue?: PropertyValue) => {
      this.emitStateChange(name, value, oldValue);
    });
  }

  /**
   * Track multiple properties at once
   */
  trackProperties(properties: Record<string, { link: Function; value: any }>) {
    Object.entries(properties).forEach(([name, property]) => {
      this.trackProperty(name, property);
    });
  }

  /**
   * Emit a state change to parent window
   */
  private emitStateChange(property: string, value: PropertyValue, previousValue?: PropertyValue) {
    const event: StateChangeEvent = {
      type: 'PHET_STATE_CHANGE',
      simulationId: this.simulationId,
      property,
      value,
      previousValue,
      timestamp: Date.now()
    };

    window.parent.postMessage(event, '*');
  }

  /**
   * Emit user interaction event
   */
  emitInteraction(interaction: string, target: string, data?: object) {
    const event: UserInteractionEvent = {
      type: 'PHET_USER_INTERACTION',
      simulationId: this.simulationId,
      interaction,
      target,
      data,
      timestamp: Date.now()
    };

    window.parent.postMessage(event, '*');
  }

  /**
   * Signal that simulation is ready
   */
  signalReady() {
    if (this.isReady) return;
    this.isReady = true;

    const event: SimulationReadyEvent = {
      type: 'PHET_SIMULATION_READY',
      simulationId: this.simulationId,
      availableProperties: Array.from(this.trackedProperties.keys()),
      timestamp: Date.now()
    };

    window.parent.postMessage(event, '*');
  }

  /**
   * Listen for commands from parent window
   */
  private setupCommandListener() {
    window.addEventListener('message', (event) => {
      if (event.data?.type === 'PHET_COMMAND') {
        this.handleCommand(event.data);
      }
    });
  }

  /**
   * Handle commands from parent (set values, reset, etc.)
   */
  private handleCommand(command: { action: string; property?: string; value?: any }) {
    switch (command.action) {
      case 'GET_STATE':
        this.emitFullState();
        break;
      case 'SET_VALUE':
        if (command.property && command.value !== undefined) {
          const property = this.trackedProperties.get(command.property);
          if (property && 'set' in property) {
            property.set(command.value);
          }
        }
        break;
      case 'RESET':
        // Trigger simulation reset if available
        break;
    }
  }

  /**
   * Emit current state of all tracked properties
   */
  private emitFullState() {
    const state: Record<string, any> = {};
    this.trackedProperties.forEach((property, name) => {
      state[name] = property.value;
    });

    window.parent.postMessage({
      type: 'PHET_FULL_STATE',
      simulationId: this.simulationId,
      state,
      timestamp: Date.now()
    }, '*');
  }
}

export default GamEdBridge;
export { GamEdBridge, StateChangeEvent, UserInteractionEvent };
```

### Step 3: Modify Projectile Motion Simulation

**File: `phet-custom/projectile-motion/js/intro/model/IntroModel.ts`** (add to existing file)

```typescript
import GamEdBridge from '../../../../phet-core/js/GamEdBridge.js';

// In the constructor, after creating properties:
class IntroModel {
  constructor() {
    // ... existing code ...

    // Initialize GamED Bridge
    this.gamEdBridge = new GamEdBridge('projectile-motion');

    // Track key properties for assessment
    this.gamEdBridge.trackProperties({
      'cannonAngle': this.cannonAngleProperty,
      'launchSpeed': this.launchSpeedProperty,
      'projectileMass': this.projectileMassProperty,
      'airResistance': this.airResistanceOnProperty,
      'altitude': this.altitudeProperty,
      'gravity': this.gravityProperty
    });

    // Track projectile state
    this.projectiles.addItemAddedListener((projectile) => {
      this.gamEdBridge.emitInteraction('projectile_launched', 'cannon', {
        angle: this.cannonAngleProperty.value,
        speed: this.launchSpeedProperty.value,
        mass: this.projectileMassProperty.value
      });

      // Track when projectile lands
      projectile.dataPoints.addItemAddedListener((dataPoint) => {
        if (dataPoint.reachedGround) {
          this.gamEdBridge.emitInteraction('projectile_landed', 'ground', {
            range: dataPoint.position.x,
            maxHeight: projectile.maxHeight,
            timeOfFlight: dataPoint.time
          });
        }
      });
    });

    // Signal ready after initialization
    this.gamEdBridge.signalReady();
  }
}
```

### Step 4: Build Modified Simulation

```bash
cd projectile-motion
grunt --brands=phet --locales=en

# Output: build/phet/projectile-motion_en_phet.html
```

### Step 5: Self-Host Modified Version

```bash
cp build/phet/projectile-motion_en_phet.html /your-server/simulations/
```

---

## Frontend: Receiving State Changes

### React Hook for PhET State

```typescript
// hooks/usePhetState.ts

import { useEffect, useState, useCallback, useRef } from 'react';

interface PhetState {
  [property: string]: any;
}

interface PhetInteraction {
  interaction: string;
  target: string;
  data?: object;
  timestamp: number;
}

interface UsePhetStateOptions {
  simulationId: string;
  onStateChange?: (property: string, value: any, previousValue?: any) => void;
  onInteraction?: (interaction: PhetInteraction) => void;
  onReady?: (availableProperties: string[]) => void;
}

export function usePhetState(options: UsePhetStateOptions) {
  const { simulationId, onStateChange, onInteraction, onReady } = options;

  const [state, setState] = useState<PhetState>({});
  const [isReady, setIsReady] = useState(false);
  const [interactions, setInteractions] = useState<PhetInteraction[]>([]);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Listen for messages from PhET simulation
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const { data } = event;

      if (data?.simulationId !== simulationId) return;

      switch (data.type) {
        case 'PHET_STATE_CHANGE':
          setState(prev => ({ ...prev, [data.property]: data.value }));
          onStateChange?.(data.property, data.value, data.previousValue);
          break;

        case 'PHET_USER_INTERACTION':
          const interaction: PhetInteraction = {
            interaction: data.interaction,
            target: data.target,
            data: data.data,
            timestamp: data.timestamp
          };
          setInteractions(prev => [...prev, interaction]);
          onInteraction?.(interaction);
          break;

        case 'PHET_SIMULATION_READY':
          setIsReady(true);
          onReady?.(data.availableProperties);
          break;

        case 'PHET_FULL_STATE':
          setState(data.state);
          break;
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [simulationId, onStateChange, onInteraction, onReady]);

  // Send command to simulation
  const sendCommand = useCallback((action: string, property?: string, value?: any) => {
    iframeRef.current?.contentWindow?.postMessage({
      type: 'PHET_COMMAND',
      action,
      property,
      value
    }, '*');
  }, []);

  // Request full state
  const requestState = useCallback(() => {
    sendCommand('GET_STATE');
  }, [sendCommand]);

  // Set a property value
  const setValue = useCallback((property: string, value: any) => {
    sendCommand('SET_VALUE', property, value);
  }, [sendCommand]);

  return {
    iframeRef,
    state,
    isReady,
    interactions,
    requestState,
    setValue,
    sendCommand
  };
}
```

### Task-Based Assessment Component

```tsx
// components/PhetAssessmentGame.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { usePhetState } from '../hooks/usePhetState';

interface AssessmentCheckpoint {
  id: string;
  description: string;
  condition: (state: any, interactions: any[]) => boolean;
  points: number;
  achieved: boolean;
}

interface AssessmentTask {
  id: string;
  title: string;
  instructions: string;
  checkpoints: AssessmentCheckpoint[];
}

interface Props {
  simulationId: string;
  simulationUrl: string;
  tasks: AssessmentTask[];
  onComplete: (results: AssessmentResults) => void;
}

export function PhetAssessmentGame({ simulationId, simulationUrl, tasks, onComplete }: Props) {
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [completedCheckpoints, setCompletedCheckpoints] = useState<Set<string>>(new Set());
  const [score, setScore] = useState(0);

  const {
    iframeRef,
    state,
    isReady,
    interactions
  } = usePhetState({
    simulationId,
    onStateChange: (property, value, previousValue) => {
      console.log(`State changed: ${property} = ${value} (was ${previousValue})`);
      checkTaskProgress();
    },
    onInteraction: (interaction) => {
      console.log('User interaction:', interaction);
      checkTaskProgress();
    }
  });

  const currentTask = tasks[currentTaskIndex];

  // Check if any checkpoints are now satisfied
  const checkTaskProgress = useCallback(() => {
    if (!currentTask) return;

    currentTask.checkpoints.forEach(checkpoint => {
      if (completedCheckpoints.has(checkpoint.id)) return;

      // Evaluate checkpoint condition
      if (checkpoint.condition(state, interactions)) {
        setCompletedCheckpoints(prev => new Set([...prev, checkpoint.id]));
        setScore(prev => prev + checkpoint.points);

        // Visual/audio feedback
        playCheckpointSound();
        showCheckpointToast(checkpoint.description);
      }
    });
  }, [currentTask, state, interactions, completedCheckpoints]);

  // Check progress whenever state or interactions change
  useEffect(() => {
    checkTaskProgress();
  }, [state, interactions, checkTaskProgress]);

  // Check if current task is complete
  const isTaskComplete = currentTask?.checkpoints.every(
    cp => completedCheckpoints.has(cp.id)
  );

  return (
    <div className="assessment-game">
      {/* Task Instructions */}
      <div className="task-panel">
        <h2>Task {currentTaskIndex + 1}: {currentTask?.title}</h2>
        <p>{currentTask?.instructions}</p>

        {/* Checkpoint Progress */}
        <div className="checkpoints">
          {currentTask?.checkpoints.map(cp => (
            <div
              key={cp.id}
              className={`checkpoint ${completedCheckpoints.has(cp.id) ? 'completed' : ''}`}
            >
              <span className="icon">
                {completedCheckpoints.has(cp.id) ? '✓' : '○'}
              </span>
              <span className="description">{cp.description}</span>
              <span className="points">{cp.points} pts</span>
            </div>
          ))}
        </div>
      </div>

      {/* PhET Simulation */}
      <div className="simulation-container">
        <iframe
          ref={iframeRef}
          src={simulationUrl}
          title={simulationId}
          className="phet-iframe"
        />

        {/* Overlay showing current state (for debugging) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="state-debug">
            <pre>{JSON.stringify(state, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Score Panel */}
      <div className="score-panel">
        <div className="score">Score: {score}</div>
        {isTaskComplete && currentTaskIndex < tasks.length - 1 && (
          <button onClick={() => setCurrentTaskIndex(i => i + 1)}>
            Next Task →
          </button>
        )}
      </div>
    </div>
  );
}
```

---

## Example: Projectile Motion Assessment Checkpoints

```typescript
const projectileMotionTasks: AssessmentTask[] = [
  {
    id: 'task-1',
    title: 'Explore Launch Angles',
    instructions: 'Fire projectiles at different angles and observe how the range changes.',
    checkpoints: [
      {
        id: 'cp-1a',
        description: 'Set angle to 30°',
        condition: (state) => Math.abs(state.cannonAngle - 30) < 2,
        points: 5,
        achieved: false
      },
      {
        id: 'cp-1b',
        description: 'Fire a projectile at 30°',
        condition: (state, interactions) =>
          interactions.some(i =>
            i.interaction === 'projectile_launched' &&
            Math.abs(i.data?.angle - 30) < 2
          ),
        points: 10,
        achieved: false
      },
      {
        id: 'cp-1c',
        description: 'Set angle to 45°',
        condition: (state) => Math.abs(state.cannonAngle - 45) < 2,
        points: 5,
        achieved: false
      },
      {
        id: 'cp-1d',
        description: 'Fire a projectile at 45°',
        condition: (state, interactions) =>
          interactions.some(i =>
            i.interaction === 'projectile_launched' &&
            Math.abs(i.data?.angle - 45) < 2
          ),
        points: 10,
        achieved: false
      },
      {
        id: 'cp-1e',
        description: 'Set angle to 60°',
        condition: (state) => Math.abs(state.cannonAngle - 60) < 2,
        points: 5,
        achieved: false
      },
      {
        id: 'cp-1f',
        description: 'Fire a projectile at 60°',
        condition: (state, interactions) =>
          interactions.some(i =>
            i.interaction === 'projectile_launched' &&
            Math.abs(i.data?.angle - 60) < 2
          ),
        points: 10,
        achieved: false
      }
    ]
  },
  {
    id: 'task-2',
    title: 'Find Maximum Range',
    instructions: 'Find the angle that makes the projectile travel the farthest.',
    checkpoints: [
      {
        id: 'cp-2a',
        description: 'Achieve range > 35 meters',
        condition: (state, interactions) =>
          interactions.some(i =>
            i.interaction === 'projectile_landed' &&
            i.data?.range > 35
          ),
        points: 15,
        achieved: false
      },
      {
        id: 'cp-2b',
        description: 'Launch at optimal angle (43°-47°)',
        condition: (state, interactions) =>
          interactions.some(i =>
            i.interaction === 'projectile_launched' &&
            i.data?.angle >= 43 && i.data?.angle <= 47
          ),
        points: 20,
        achieved: false
      },
      {
        id: 'cp-2c',
        description: 'Achieve maximum possible range (within 5%)',
        condition: (state, interactions) => {
          const maxRange = calculateMaxRange(state.launchSpeed, state.gravity);
          return interactions.some(i =>
            i.interaction === 'projectile_landed' &&
            i.data?.range >= maxRange * 0.95
          );
        },
        points: 25,
        achieved: false
      }
    ]
  },
  {
    id: 'task-3',
    title: 'Speed vs Range',
    instructions: 'Explore how launch speed affects the range.',
    checkpoints: [
      {
        id: 'cp-3a',
        description: 'Change launch speed',
        condition: (state, interactions) => {
          const speedChanges = interactions.filter(i =>
            i.interaction === 'projectile_launched'
          ).map(i => i.data?.speed);
          const uniqueSpeeds = new Set(speedChanges);
          return uniqueSpeeds.size >= 2;
        },
        points: 10,
        achieved: false
      },
      {
        id: 'cp-3b',
        description: 'Launch at low speed (< 10 m/s)',
        condition: (state, interactions) =>
          interactions.some(i =>
            i.interaction === 'projectile_launched' &&
            i.data?.speed < 10
          ),
        points: 10,
        achieved: false
      },
      {
        id: 'cp-3c',
        description: 'Launch at high speed (> 25 m/s)',
        condition: (state, interactions) =>
          interactions.some(i =>
            i.interaction === 'projectile_launched' &&
            i.data?.speed > 25
          ),
        points: 10,
        achieved: false
      }
    ]
  }
];
```

---

## Checkpoint Condition Patterns

### 1. Property Value Check
```typescript
// User set angle to specific value
condition: (state) => Math.abs(state.cannonAngle - 45) < 2
```

### 2. Property Range Check
```typescript
// User set speed within range
condition: (state) => state.launchSpeed >= 15 && state.launchSpeed <= 20
```

### 3. Interaction Occurred
```typescript
// User launched a projectile
condition: (state, interactions) =>
  interactions.some(i => i.interaction === 'projectile_launched')
```

### 4. Interaction with Condition
```typescript
// User launched projectile at specific angle
condition: (state, interactions) =>
  interactions.some(i =>
    i.interaction === 'projectile_launched' &&
    Math.abs(i.data?.angle - 45) < 2
  )
```

### 5. Multiple Interactions (Exploration)
```typescript
// User tried at least 3 different angles
condition: (state, interactions) => {
  const angles = interactions
    .filter(i => i.interaction === 'projectile_launched')
    .map(i => Math.round(i.data?.angle / 5) * 5); // Round to nearest 5
  return new Set(angles).size >= 3;
}
```

### 6. Outcome Achievement
```typescript
// User achieved range > 40 meters
condition: (state, interactions) =>
  interactions.some(i =>
    i.interaction === 'projectile_landed' &&
    i.data?.range > 40
  )
```

### 7. Time-Based
```typescript
// User explored for at least 60 seconds
condition: (state, interactions) => {
  if (interactions.length < 2) return false;
  const first = interactions[0].timestamp;
  const last = interactions[interactions.length - 1].timestamp;
  return (last - first) >= 60000;
}
```

### 8. Sequence Check
```typescript
// User fired low, then high angle (comparison exploration)
condition: (state, interactions) => {
  const launches = interactions
    .filter(i => i.interaction === 'projectile_launched')
    .map(i => i.data?.angle);

  for (let i = 1; i < launches.length; i++) {
    if (launches[i-1] < 40 && launches[i] > 50) return true;
  }
  return false;
}
```

---

## Build Automation Script

```bash
#!/bin/bash
# build_custom_phet.sh - Build modified PhET simulations with GamED bridge

SIMULATIONS=("projectile-motion" "circuit-construction-kit-dc" "states-of-matter")
OUTPUT_DIR="./custom-simulations"

mkdir -p $OUTPUT_DIR

for sim in "${SIMULATIONS[@]}"; do
  echo "Building $sim..."
  cd $sim
  grunt --brands=phet --locales=en
  cp "build/phet/${sim}_en_phet.html" "../$OUTPUT_DIR/${sim}.html"
  cd ..
  echo "✓ Built $sim"
done

echo "All simulations built to $OUTPUT_DIR/"
```

---

## Summary: Full State Access Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GamED.AI Assessment System                   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   usePhetState Hook                      │   │
│  │  • Receives state changes                               │   │
│  │  • Tracks interactions                                   │   │
│  │  • Evaluates checkpoints                                │   │
│  │  • Updates scores                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ postMessage                      │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Modified PhET Simulation                    │   │
│  │                                                         │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │              GamEdBridge Module                  │   │   │
│  │  │  • Tracks all Property changes                   │   │   │
│  │  │  • Emits user interactions                       │   │   │
│  │  │  • Responds to commands                          │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │  Properties tracked:                                    │   │
│  │  • cannonAngle, launchSpeed, projectileMass           │   │
│  │  • airResistance, gravity, altitude                    │   │
│  │                                                         │   │
│  │  Interactions tracked:                                  │   │
│  │  • projectile_launched (with angle, speed, mass)       │   │
│  │  • projectile_landed (with range, height, time)        │   │
│  │  • parameter_changed (with property, old, new)         │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

This gives you **FULL ACCESS** to:
- ✅ All property values in real-time
- ✅ All user interactions with context
- ✅ Bidirectional communication (set values from parent)
- ✅ Task-based assessment with flexible conditions
- ✅ No external API dependency
