# Recommended Architecture: PhET Integration for GamED.AI

## Executive Summary

**Recommendation:** Create a `PHET_SIMULATION` template that wraps existing PhET simulations in your game shell, with AI agents selecting and configuring simulations based on queries.

**Why this approach:**
- ✅ Leverage 85+ production-ready simulations immediately
- ✅ No need to rebuild complex physics/chemistry engines
- ✅ Full control over game layer (tasks, scoring, hints, progression)
- ✅ Fits your existing template routing architecture
- ✅ Minimal development effort for maximum educational value

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Query                                  │
│  "Create a game about projectile motion and how angle affects range"│
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Router Agent                                    │
│  Analyzes query → Determines PHET_SIMULATION is best template       │
│  (Physics + interactive exploration + parameter adjustment)          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 PhET Simulation Selector Agent                       │
│  Matches concepts to simulation catalog:                            │
│  "projectile motion" + "angle" + "range" → projectile-motion        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Game Designer Agent                               │
│  Creates learning tasks, checkpoints, scoring rubric:               │
│  - Task 1: Explore angles 30°, 45°, 60°                            │
│  - Task 2: Find optimal angle for max range                         │
│  - Task 3: Predict range for given angle/velocity                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Blueprint Generator                                │
│  Outputs PHET_SIMULATION blueprint with:                            │
│  - simulationId: "projectile-motion"                                │
│  - tasks: [{exploration}, {prediction}, {challenge}]                │
│  - scoring: {accuracy, exploration, efficiency}                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Frontend Renderer                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Game Shell (Your Code)                                      │   │
│  │  ┌─────────────────────┐  ┌────────────────────────────┐   │   │
│  │  │   Task Panel        │  │   Score Panel              │   │   │
│  │  │   - Current task    │  │   - Points: 45/100         │   │   │
│  │  │   - Instructions    │  │   - Progress: 2/3 tasks    │   │   │
│  │  │   - Hints available │  │   - Time: 5:32             │   │   │
│  │  └─────────────────────┘  └────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │                                                       │   │   │
│  │  │           PhET Simulation (iframe)                    │   │   │
│  │  │                                                       │   │   │
│  │  │    [Cannon] -----> * * * * *                         │   │   │
│  │  │       ↑                      *                        │   │   │
│  │  │    Angle: 45°                 *                       │   │   │
│  │  │    Speed: 20 m/s               *                      │   │   │
│  │  │                                 * [Impact]            │   │   │
│  │  │                                                       │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  [Hint] [Reset] [Next Task]           [Submit Answer]│   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## How Scoring Works (Without PhET-iO API)

Since we're using free PhET (not PhET-iO), we score based on **observable outcomes** rather than internal state:

### Scoring Strategy 1: Task-Based Checkpoints

```typescript
interface TaskCheckpoint {
  id: string;
  type: 'user_action' | 'observation' | 'answer';
  description: string;
  points: number;
}

// Example for Projectile Motion
const tasks = [
  {
    id: 'explore-angles',
    question: 'How does launch angle affect the projectile range?',
    checkpoints: [
      { type: 'user_action', description: 'User clicked simulation', points: 5 },
      { type: 'user_action', description: 'User spent 30+ seconds exploring', points: 10 },
      { type: 'answer', description: 'User answered reflection question', points: 15 }
    ]
  },
  {
    id: 'find-optimal',
    question: 'What angle gives maximum range?',
    checkpoints: [
      { type: 'answer', description: 'Answered 45°', expectedAnswer: '45', points: 20 }
    ]
  }
];
```

### Scoring Strategy 2: Quiz After Exploration

```typescript
// After simulation exploration, quiz the student
const postSimulationQuiz = [
  {
    question: 'At what angle did the projectile travel farthest?',
    options: ['30°', '45°', '60°', '90°'],
    correct: '45°',
    points: 20
  },
  {
    question: 'What happens to height when you increase the angle?',
    options: ['Increases', 'Decreases', 'Stays same'],
    correct: 'Increases',
    points: 15
  }
];
```

### Scoring Strategy 3: Prediction Challenges

```typescript
// Challenge: Predict before observing
const predictionTask = {
  phase1: {
    question: 'Predict: Will a 60° angle travel farther than 30°?',
    userPredicts: true, // User makes prediction
    points: 5 // Points for making prediction
  },
  phase2: {
    instruction: 'Now test your prediction in the simulation',
    explorationTime: 60 // seconds
  },
  phase3: {
    question: 'Was your prediction correct?',
    reflection: true,
    points: 10 // Points for correct reflection
  }
};
```

---

## Blueprint Schema for PHET_SIMULATION

```typescript
interface PhetSimulationBlueprint {
  templateType: 'PHET_SIMULATION';

  // Simulation Selection
  simulation: {
    id: string;                    // e.g., 'projectile-motion'
    screen?: string;               // e.g., 'intro', 'lab'
    localPath?: string;            // Path to self-hosted HTML file
  };

  // Game Metadata
  title: string;
  narrativeIntro: string;
  learningObjectives: string[];
  estimatedMinutes: number;
  difficulty: 'easy' | 'medium' | 'hard';

  // Task Sequence
  tasks: PhetTask[];

  // Scoring
  scoring: {
    maxScore: number;
    explorationBonus: number;      // Points for time spent
    hintPenalty: number;           // Deduction per hint
    timeBonusThreshold?: number;   // Seconds for time bonus
  };
}

interface PhetTask {
  id: string;
  type: 'exploration' | 'prediction' | 'quiz' | 'challenge';

  // Task Content
  title: string;
  instructions: string;
  hints?: string[];

  // For exploration tasks
  explorationPrompts?: string[];   // Guide what to explore
  minExplorationTime?: number;     // Seconds required

  // For prediction tasks
  prediction?: {
    question: string;
    options?: string[];
  };

  // For quiz tasks
  questions?: QuizQuestion[];

  // Scoring
  points: number;
  requiredToProgress: boolean;
}

interface QuizQuestion {
  question: string;
  type: 'multiple_choice' | 'numeric' | 'text';
  options?: string[];
  correctAnswer: string | number;
  tolerance?: number;              // For numeric answers
  points: number;
  explanation?: string;            // Shown after answer
}
```

---

## Example: Complete Blueprint for Projectile Motion

```json
{
  "templateType": "PHET_SIMULATION",
  "simulation": {
    "id": "projectile-motion",
    "screen": "intro",
    "localPath": "/simulations/projectile-motion.html"
  },
  "title": "Projectile Motion Explorer",
  "narrativeIntro": "You're a physics engineer designing a cannon for a medieval castle. Your goal is to understand how launch angle and speed affect where projectiles land!",
  "learningObjectives": [
    "Understand relationship between launch angle and range",
    "Identify optimal angle for maximum range",
    "Predict projectile behavior based on parameters"
  ],
  "estimatedMinutes": 12,
  "difficulty": "medium",

  "tasks": [
    {
      "id": "task-1-explore",
      "type": "exploration",
      "title": "Explore the Cannon",
      "instructions": "Fire the cannon at different angles (30°, 45°, 60°) and observe where the projectile lands. Pay attention to both height and distance.",
      "explorationPrompts": [
        "Try angle = 30° and note the range",
        "Try angle = 45° and compare",
        "Try angle = 60° and observe the difference"
      ],
      "minExplorationTime": 45,
      "hints": [
        "Use the angle slider on the left side of the cannon",
        "Click 'Fire' to launch the projectile",
        "The tape measure can help you measure distance"
      ],
      "points": 15,
      "requiredToProgress": true
    },
    {
      "id": "task-2-predict",
      "type": "prediction",
      "title": "Make a Prediction",
      "instructions": "Based on your exploration, predict which angle will give the MAXIMUM range.",
      "prediction": {
        "question": "Which angle do you think gives the farthest range?",
        "options": ["30°", "45°", "60°", "75°"]
      },
      "points": 10,
      "requiredToProgress": true
    },
    {
      "id": "task-3-verify",
      "type": "exploration",
      "title": "Test Your Prediction",
      "instructions": "Now test your prediction! Fire projectiles at your predicted angle and nearby angles to verify.",
      "minExplorationTime": 30,
      "points": 10,
      "requiredToProgress": true
    },
    {
      "id": "task-4-quiz",
      "type": "quiz",
      "title": "Check Your Understanding",
      "instructions": "Answer these questions based on what you observed.",
      "questions": [
        {
          "question": "At what angle does a projectile travel the farthest horizontal distance (ignoring air resistance)?",
          "type": "multiple_choice",
          "options": ["30°", "45°", "60°", "90°"],
          "correctAnswer": "45°",
          "points": 20,
          "explanation": "At 45°, the projectile has the optimal balance between horizontal velocity and time in the air."
        },
        {
          "question": "If you increase the angle from 45° to 60°, what happens to the maximum HEIGHT of the projectile?",
          "type": "multiple_choice",
          "options": ["Increases", "Decreases", "Stays the same"],
          "correctAnswer": "Increases",
          "points": 15,
          "explanation": "Higher angles give more vertical velocity, so the projectile goes higher but not as far."
        },
        {
          "question": "A projectile is launched at 20 m/s at 45°. Approximately how far will it travel? (Use the simulation to check!)",
          "type": "numeric",
          "correctAnswer": 40,
          "tolerance": 5,
          "points": 20,
          "explanation": "At 45° with initial velocity v, range ≈ v²/g ≈ 400/10 ≈ 40m"
        }
      ],
      "points": 55,
      "requiredToProgress": false
    },
    {
      "id": "task-5-challenge",
      "type": "challenge",
      "title": "Castle Defense Challenge",
      "instructions": "The enemy is 35 meters away! Find the angle that lands the projectile closest to 35m. You have 3 attempts.",
      "hints": [
        "You'll need an angle less than 45° to hit a closer target",
        "Try angles between 30° and 40°"
      ],
      "points": 25,
      "requiredToProgress": false
    }
  ],

  "scoring": {
    "maxScore": 115,
    "explorationBonus": 10,
    "hintPenalty": 2,
    "timeBonusThreshold": 600
  }
}
```

---

## Simulation-to-Concept Mapping

The agent uses this mapping to select simulations:

```typescript
const SIMULATION_CONCEPT_MAP = {
  'projectile-motion': {
    concepts: ['projectile', 'trajectory', 'parabola', 'angle', 'velocity', 'range', 'kinematics', 'gravity'],
    subjects: ['physics'],
    blooms: ['understand', 'apply', 'analyze'],
    questionPatterns: [
      /projectile/i, /launch/i, /trajectory/i, /angle.*range/i, /throw/i, /cannon/i
    ]
  },
  'circuit-construction-kit-dc': {
    concepts: ['circuit', 'voltage', 'current', 'resistance', 'ohm', 'battery', 'resistor', 'series', 'parallel'],
    subjects: ['physics'],
    blooms: ['understand', 'apply', 'create'],
    questionPatterns: [
      /circuit/i, /voltage/i, /current/i, /ohm/i, /resistor/i, /battery/i
    ]
  },
  'states-of-matter': {
    concepts: ['solid', 'liquid', 'gas', 'phase', 'temperature', 'molecules', 'kinetic', 'heat'],
    subjects: ['chemistry', 'physics'],
    blooms: ['understand', 'apply'],
    questionPatterns: [
      /state.*matter/i, /solid.*liquid.*gas/i, /phase/i, /molecule.*move/i, /heat.*particles/i
    ]
  },
  'graphing-quadratics': {
    concepts: ['parabola', 'quadratic', 'vertex', 'roots', 'coefficient', 'graph'],
    subjects: ['mathematics'],
    blooms: ['understand', 'apply', 'analyze'],
    questionPatterns: [
      /quadratic/i, /parabola/i, /vertex/i, /y\s*=\s*ax/i, /graph.*equation/i
    ]
  },
  'molecule-polarity': {
    concepts: ['polar', 'nonpolar', 'electronegativity', 'dipole', 'bond', 'molecule'],
    subjects: ['chemistry'],
    blooms: ['understand', 'apply'],
    questionPatterns: [
      /polar/i, /electronegativity/i, /dipole/i, /bond.*polarity/i
    ]
  },
  'friction': {
    concepts: ['friction', 'static', 'kinetic', 'force', 'surface', 'motion'],
    subjects: ['physics'],
    blooms: ['understand', 'apply'],
    questionPatterns: [
      /friction/i, /static.*kinetic/i, /slide/i, /rough.*surface/i
    ]
  },
  'pendulum-lab': {
    concepts: ['pendulum', 'period', 'frequency', 'oscillation', 'gravity', 'length'],
    subjects: ['physics'],
    blooms: ['understand', 'apply', 'analyze'],
    questionPatterns: [
      /pendulum/i, /period/i, /swing/i, /oscillat/i
    ]
  },
  'build-an-atom': {
    concepts: ['proton', 'neutron', 'electron', 'atom', 'element', 'isotope', 'ion'],
    subjects: ['chemistry'],
    blooms: ['remember', 'understand'],
    questionPatterns: [
      /atom/i, /proton/i, /neutron/i, /electron/i, /element/i, /isotope/i
    ]
  },
  'natural-selection': {
    concepts: ['evolution', 'mutation', 'selection', 'adaptation', 'trait', 'population'],
    subjects: ['biology'],
    blooms: ['understand', 'apply', 'analyze'],
    questionPatterns: [
      /natural selection/i, /evolution/i, /mutation/i, /adapt/i, /survival/i
    ]
  },
  'ph-scale': {
    concepts: ['pH', 'acid', 'base', 'neutral', 'concentration', 'hydrogen'],
    subjects: ['chemistry'],
    blooms: ['understand', 'apply'],
    questionPatterns: [
      /pH/i, /acid/i, /base/i, /alkaline/i
    ]
  }
};
```

---

## Agent Pipeline for PHET_SIMULATION

```
Question: "What factors affect where a thrown ball lands?"
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 1. Input Enhancer                               │
│    - Bloom's: Apply                             │
│    - Subject: Physics                           │
│    - Concepts: [projectile, trajectory, land]   │
│    - Intent: Exploration + Understanding        │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 2. Router                                       │
│    Score templates:                             │
│    - PHET_SIMULATION: 0.92 ✓ (best match)      │
│    - PARAMETER_PLAYGROUND: 0.78                 │
│    - LABEL_DIAGRAM: 0.31                        │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 3. PhET Simulation Selector                     │
│    Match concepts to catalog:                   │
│    - "thrown ball" → projectile-motion (0.95)   │
│    - "lands" → trajectory (0.88)                │
│    Selected: projectile-motion                  │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 4. Game Planner                                 │
│    Design learning sequence:                    │
│    - Task 1: Free exploration (understand)      │
│    - Task 2: Guided exploration (apply)         │
│    - Task 3: Prediction challenge (analyze)     │
│    - Task 4: Quiz (assess)                      │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 5. Blueprint Generator                          │
│    Generate PHET_SIMULATION blueprint JSON      │
│    with tasks, scoring, hints                   │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 6. Blueprint Validator                          │
│    - Schema validation ✓                        │
│    - Simulation exists ✓                        │
│    - Tasks are coherent ✓                       │
└─────────────────────────────────────────────────┘
                    │
                    ▼
                Blueprint Ready for Frontend
```

---

## Frontend Component Structure

```
frontend/src/components/templates/PhetSimulationGame/
├── index.tsx                    # Main game component
├── PhetSimulationFrame.tsx      # Iframe wrapper for PhET
├── TaskPanel.tsx                # Shows current task & instructions
├── ScorePanel.tsx               # Score display
├── QuizModal.tsx                # Quiz questions overlay
├── PredictionModal.tsx          # Prediction interface
├── HintButton.tsx               # Hint system
├── ExplorationTimer.tsx         # Track exploration time
├── hooks/
│   ├── usePhetSimulation.ts     # Simulation state management
│   ├── useGameProgress.ts       # Task progression
│   └── useScoring.ts            # Score calculation
└── types.ts                     # TypeScript interfaces
```

---

## Why This Approach is Best

| Aspect | Embedding PhET | Building Custom | Hybrid (Recommended) |
|--------|---------------|-----------------|----------------------|
| **Time to market** | 1-2 weeks | 3-6 months | 2-4 weeks |
| **Simulation quality** | Excellent (10+ years) | Variable | Excellent |
| **Customization** | Limited | Full | Good (game layer) |
| **Scoring integration** | Moderate | Full | Good |
| **Maintenance** | PhET handles | You handle | Shared |
| **Educational validity** | Research-backed | Needs validation | Research-backed |
| **Coverage** | 85+ simulations | What you build | 85+ + extensible |

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Add PHET_SIMULATION to template registry
- [ ] Create blueprint schema
- [ ] Download & self-host 10 key simulations
- [ ] Build basic iframe wrapper component

### Phase 2: Agent Pipeline (Week 3-4)
- [ ] Build PhET Simulation Selector agent
- [ ] Create concept-to-simulation mapping
- [ ] Implement task generation prompts
- [ ] Add validation rules

### Phase 3: Game Shell (Week 5-6)
- [ ] Build TaskPanel component
- [ ] Implement scoring system
- [ ] Add quiz/prediction modals
- [ ] Create exploration timer

### Phase 4: Polish & Testing (Week 7-8)
- [ ] End-to-end testing
- [ ] Add more simulations
- [ ] Refine agent prompts
- [ ] Performance optimization

---

## Success Metrics

1. **Route Accuracy:** 90%+ of physics/chemistry queries correctly route to PHET_SIMULATION
2. **Simulation Match:** 85%+ appropriate simulation selected for query
3. **Task Quality:** Tasks align with learning objectives (human review)
4. **Engagement:** Average exploration time > minimum threshold
5. **Learning:** Quiz accuracy > 70% after exploration
