# BASELINE 1: Infrastructure-Aware Prompt
## "Label the Parts of the Heart and Order the Flow" – Using Existing Custom Engine

**Objective:** Generate a complete, production-ready interactive game for "Label the Parts of the Heart and Order the Flow" using the existing GamifyAssessment custom React engine.

---

## PART 1: Engine Architecture Overview

You will be building a game using a custom, schema-driven game engine built in Next.js + React + TypeScript. The engine is **NOT** a generic HTML5 canvas library—it's a specialized interactive diagram game framework with multi-mechanic support, temporal constraints, and hierarchical zone management.

### Core Design Philosophy

- **Schema-First**: All game logic is driven by a TypeScript interface called `InteractiveDiagramBlueprint`. **Do not hard-code game behavior outside this schema.**
- **Multi-Mechanic**: A single game can chain multiple interaction modes (e.g., Start with dragging labels, transition to sequencing blood flow).
- **Temporal Constraints**: Zones can be revealed/hidden based on temporal logic (Petri-net inspired), not just player actions.
- **Component Reusability**: Use ONLY the existing React components listed below. **Do not introduce external libraries, external Canvas libraries, or custom SVG renderers.**

### Dependency Overview

Your frontend uses these key libraries (ONLY):
- **@dnd-kit/core** + **@dnd-kit/sortable** — For drag-and-drop, not three.js, Konva, or Fabric.js
- **framer-motion** — For animations
- **@radix-ui/react-*** — For UI primitives (dialogs, panels, etc.)
- **react-zoom-pan-pinch** — For diagram zoom/pan
- **zustand** — For state management (NOT Redux or Mobx)
- **tailwindcss** — For styling (NOT Bootstrap, Material-UI, or custom CSS modules)

---

## PART 2: Required TypeScript Interfaces (The Game Schema)

Your game output MUST conform to these exact TypeScript interfaces. These are non-negotiable contracts.

### Main Blueprint Structure

```typescript
interface InteractiveDiagramBlueprint {
  templateType: 'INTERACTIVE_DIAGRAM';  // ALWAYS this exact string
  title: string;  // "Label the Parts of the Heart and Order the Flow"
  narrativeIntro: string;  // Intro text that sets up the game
  diagram: {
    assetPrompt: string;  // Prompt for generating/retrieving the heart diagram image
    assetUrl?: string;  // URL/path to the heart SVG or PNG image
    width?: number;  // Canvas width in pixels (e.g., 800)
    height?: number;  // Canvas height in pixels (e.g., 600)
    zones: Zone[];  // Array of labeled regions on the heart (atrium, ventricle, etc.)
    overlaySpec?: InteractiveOverlaySpec;  // Optional: SVG overlay with interactive polygons
  };
  labels: Label[];  // The draggable labels (pump, oxygenated, deoxygenated, etc.)
  distractorLabels?: DistractorLabel[];  // Wrong answers (e.g., "brain", "lung")
  tasks: Task[];  // Task instructions (usually 1-2 tasks for simple games)
  animationCues: AnimationCues;  // Text-based animation cues (legacy)
  animations?: StructuredAnimations;  // Structured animation specs (preferred)
  mechanics?: Mechanic[];  // Array of interaction modes (start with drag_drop, optionally transition to sequencing)
  modeTransitions?: ModeTransition[];  // Rules for transitioning between mechanics
  sequenceConfig?: SequenceConfig;  // REQUIRED for blood flow ordering: defines the sequence of blood chambers
  dragDropConfig?: DragDropConfig;  // Configuration for drag-and-drop mechanics
  scoringStrategy?: ScoringStrategy;  // Scoring rules
  hints?: Hint[];  // Contextual hints per zone
  feedbackMessages?: FeedbackMessages;  // Generic feedback (perfect/good/retry)
}
```

### Zone Interface (Heart Anatomy)

```typescript
interface Zone {
  id: string;  // Unique identifier (e.g., "left_atrium", "pulmonary_artery")
  label: string;  // Display name (e.g., "Left Atrium")
  x?: number;  // X position as percentage (0-100) of diagram width
  y?: number;  // Y position as percentage (0-100) of diagram height
  radius?: number;  // Radius for circular zones (in pixels or percentage)
  width?: number;  // Width for rectangular zones (0-100%)
  height?: number;  // Height for rectangular zones (0-100%)
  zone_type?: 'point' | 'area';  // 'point' = small dot, 'area' = precise boundary
  shape?: 'circle' | 'polygon' | 'rect';  // Shape type
  points?: [number, number][];  // Polygon vertices (for complex heart regions)
  parentZoneId?: string;  // For hierarchical grouping (e.g., "left_side" parent)
  hierarchyLevel?: number;  // 1=root, 2=child, 3=grandchild
  description?: string;  // "Receives blood from the lungs..."
  hint?: string;  // Contextual hint shown on hover/request
  difficulty?: number;  // 1-5 complexity scale
  metadata?: Record<string, unknown>;  // Custom data (e.g., "blood_oxygen_level": "high")
}
```

### Label Interface (Draggable Items)

```typescript
interface Label {
  id: string;  // Unique ID (e.g., "label_left_atrium")
  text: string;  // Display text (e.g., "Left Atrium")
  correctZoneId: string;  // Which zone is the CORRECT answer (e.g., "left_atrium")
}
```

### Sequence Configuration (Blood Flow Ordering)

```typescript
interface SequenceConfig {
  sequenceType: 'linear' | 'cyclic' | 'branching';  // Use 'cyclic' for blood flow loop
  items: SequenceConfigItem[];  // Chambers/vessels in sequence
  correctOrder: string[];  // Correct ordering (e.g., ["right_atrium", "right_ventricle", ...])
  instructionText: string;  // "Order the blood flow through the heart..."
  layout_mode: 'horizontal_timeline' | 'vertical_list' | 'circular_cycle' | 'flowchart' | 'insert_between';
  interaction_pattern: 'drag_reorder' | 'drag_to_slots' | 'click_to_swap' | 'number_typing';
  card_type: 'text_only' | 'text_with_icon' | 'image_with_caption';
  connector_style: 'arrow' | 'line' | 'numbered' | 'none';
  show_position_numbers?: boolean;
  allowPartialCredit?: boolean;
}

interface SequenceConfigItem {
  id: string;  // (e.g., "right_atrium_seq")
  text: string;  // "Right Atrium"
  icon?: string;  // Optional emoji or icon (e.g., "❤️")
  order_index?: number;  // Correct position (0-based)
  is_distractor?: boolean;  // False for real flow steps
}
```

### Mechanics & Transitions (Multi-Mode Support)

```typescript
interface Mechanic {
  type: InteractionMode;  // 'drag_drop' | 'sequencing' | etc.
  config?: Record<string, unknown>;  // Mode-specific config
  scoring?: {
    strategy: string;
    points_per_correct: number;
    max_score: number;
    partial_credit?: boolean;
  };
  feedback?: {
    on_correct: string;
    on_incorrect: string;
    on_completion: string;
  };
}

type InteractionMode =
  | 'drag_drop'  // Drag labels onto zones
  | 'click_to_identify'  // Click zones to identify
  | 'trace_path'  // Draw a path through the heart
  | 'hierarchical'  // Expand parent → label children
  | 'sequencing'  // Reorder items in correct sequence
  | 'description_matching'
  | 'compare_contrast'
  | 'sorting_categories'
  | 'memory_match'
  | 'branching_scenario'
  | 'timed_challenge';

interface ModeTransition {
  from: InteractionMode;  // e.g., 'drag_drop'
  to: InteractionMode;  // e.g., 'sequencing'
  trigger: 'all_zones_labeled' | 'percentage_complete' | 'time_elapsed' | 'user_choice' | ...;
  triggerValue?: number | string[];
  animation?: 'fade' | 'slide' | 'zoom' | 'none';
  message?: string;  // "Great! Now order the blood flow..."
}
```

### Drag-Drop Configuration

```typescript
interface DragDropConfig {
  interaction_mode?: 'drag_drop' | 'click_to_place' | 'reverse';
  zone_idle_animation?: 'none' | 'pulse' | 'glow' | 'breathe';
  zone_hover_effect?: 'highlight' | 'scale' | 'glow' | 'none';
  leader_line_style?: 'straight' | 'elbow' | 'curved' | 'fluid' | 'none';
  leader_line_color?: string;  // e.g., "#3b82f6"
  leader_line_width?: number;
  leader_line_animate?: boolean;
  placement_animation?: 'spring' | 'ease' | 'instant';
  incorrect_animation?: 'shake' | 'bounce_back' | 'fade_out';
  tray_position?: 'bottom' | 'right' | 'left' | 'top';
  tray_layout?: 'horizontal' | 'vertical' | 'grid' | 'grouped';
  show_distractors?: boolean;
  distractor_count?: number;
  max_attempts?: number;
  shuffle_labels?: boolean;
  zoom_enabled?: boolean;
  minimap_enabled?: boolean;
}
```

---

## PART 3: Available React Components (MUST USE ONLY THESE)

The engine provides a pre-built component library in `/frontend/src/components/templates/InteractiveDiagramGame/`. Your game MUST use these components and **NOT create new ones**.

### Core Components

#### 1. **InteractiveDiagramGame.tsx** (Main Controller)
```tsx
<InteractiveDiagramGame 
  blueprint={blueprintSchema}
  onComplete={(score) => { /* handle game completion */ }}
  sessionId="game-session-id"
/>
```
- **Props**: `blueprint: InteractiveDiagramBlueprint | MultiSceneInteractiveDiagramBlueprint`, `onComplete?: (score) => void`, `sessionId?: string`
- **Behavior**: Renders the full game using the blueprint schema. Initializes state, handles transitions.
- **Usage**: Pass your complete heart game blueprint as the `blueprint` prop.

#### 2. **MechanicRouter.tsx** (Mechanic Dispatcher)
```tsx
<MechanicRouter 
  mode="drag_drop"  // or "sequencing", "click_to_identify", etc.
  blueprint={blueprint}
  placedLabels={placedLabels}
  availableLabels={availableLabels}
  onDragStart={handleDragStart}
  onDragEnd={handleDragEnd}
  completeInteraction={handleModalTransition}
  // ... other mode-specific handlers
/>
```
- **Behavior**: Routes to the appropriate mechanic component based on `mode`.
- **Props**: Mode-specific handlers (drag handlers, click handlers, sequence handlers, etc.)
- **Do Not Hardcode Mech Logic**: The router dispatches to sub-components—do not add business logic here.

#### 3. **DiagramCanvas.tsx** (Diagram Renderer)
```tsx
<DiagramCanvas 
  diagram={blueprint.diagram}
  zones={blueprint.diagram.zones}
  scale={zoomLevel}
  onZoneClick={handleZoneClick}
  children={zoneOverlays}
/>
```
- **Props**: `diagram`, `zones`, `scale`, `onZoneClick`
- **Behavior**: Renders the heart SVG/image with zone overlays (circles, polygons, rects).
- **Styling**: Uses Tailwind CSS, no custom CSS.

#### 4. **LabelTray.tsx** (Label Container)
```tsx
<LabelTray 
  labels={availableLabels}
  position="bottom"
  layout="horizontal"
  onLabelSelect={handleDragStart}
/>
```
- **Behavior**: Displays draggable labels in a tray (bottom, right, left, top).
- **Supports**: `dragDropConfig.tray_position`, `dragDropConfig.tray_layout`.

#### 5. **DropZone.tsx** (Single Zone Interaction)
```tsx
<DropZone 
  zone={zone}
  isOver={isDragOverZone}
  placedLabel={placedLabels.find(pl => pl.zoneId === zone.id)}
  onDrop={handleDrop}
  showHints={showHints}
  hints={hints}
/>
```
- **Behavior**: Renders a single zone (circle, rect, polygon) with drop logic, animations, and hints.
- **Animations**: Handles zone_idle_animation, zone_hover_effect from dragDropConfig.

#### 6. **EnhancedDragDropGame.tsx** (Full Drag-Drop Orchestrator)
```tsx
<EnhancedDragDropGame 
  blueprint={blueprint}
  placedLabels={placedLabels}
  availableLabels={availableLabels}
  onCorrectPlacement={handleCorrectLabel}
  onIncorrectPlacement={handleIncorrectLabel}
  completeInteraction={handleComplete}
/>
```
- **Behavior**: Wraps drag-drop logic: label placement, collision detection, scoring, feedback, distractors.

#### 7. **EnhancedSequenceBuilder.tsx** (Sequencing Mechanic)
```tsx
<EnhancedSequenceBuilder 
  config={blueprint.sequenceConfig}
  onSubmit={handleSequenceSubmit}
  allowPartialCredit={true}
/>
```
- **Props**: `config: SequenceConfig`, `onSubmit: (order: string[]) => void`, `allowPartialCredit?: boolean`
- **Behavior**: Renders a reorderable list/timeline for blood flow sequencing.
- **Supports**: `layout_mode` (timeline, circular, flowchart, etc.), `interaction_pattern` (drag, click-to-swap, etc.).

#### 8. **ResultsPanel.tsx** (Score & Feedback)
```tsx
<ResultsPanel 
  score={finalScore}
  maxScore={maxScore}
  feedback={feedbackMessages}
  placedLabels={placedLabels}
/>
```
- **Behavior**: Displays final score, feedback, and correctness summary.

#### 9. **GameControls.tsx** (Action Buttons)
```tsx
<GameControls 
  onReset={handleReset}
  onSubmit={handleSubmit}
  onHint={toggleHints}
  showHints={showHints}
  isComplete={isGameComplete}
/>
```
- **Behavior**: Reset, Submit, Hint, and other action buttons.

#### 10. **SceneTransition.tsx** & **SceneIndicator.tsx** (Multi-Scene Support)
- **SceneTransition**: Renders transition animations between scenes.
- **SceneIndicator**: Displays current scene progress (e.g., "Scene 1 of 2").
- **Usage**: Only needed if your blueprint is multi-scene (not the case for basic heart game).

#### 11. **UI Primitives** (from `src/components/ui/`)
- `Button.tsx` — `<Button>Click me</Button>`
- `Card.tsx` — `<Card><CardContent>...</CardContent></Card>`
- `Dialog.tsx` — Modal dialogs
- `Input.tsx`, `Select.tsx` — Form controls
- `Badge.tsx` — Status indicators
- Use these for auxiliary UI (titles, instructions, score displays, etc.).

#### 12. **Advanced Multimode Interactions**
```tsx
// Available in src/components/templates/InteractiveDiagramGame/interactions/:
<HierarchyController />  // For hierarchical zone expansion
<DescriptionMatcher />  // For description-matching mechanic
<CompareContrast />  // For comparing two diagrams
<BranchingScenario />  // For branching decision trees
<EnhancedMemoryMatch />  // For memory/matching games
<EnhancedSortingCategories />  // For categorization
<EnhancedPathDrawer />  // For path tracing
<TimedChallengeWrapper />  // For timed variants
```

---

## PART 4: State Management (Zustand-Based)

The game uses **zustand** for state, NOT Redux or useState everywhere.

### State Structure
```typescript
interface GameState {
  availableLabels: Label[];
  placedLabels: PlacedLabel[];
  score: number;
  isComplete: boolean;
  showHints: boolean;
  draggingLabelId: string | null;
  interactionMode: InteractionMode;
  pathProgress?: PathProgress;
  identificationProgress?: IdentificationProgress;
  hierarchyState?: HierarchyState;
  multiModeState?: MultiModeState; // For mechanic transitions
  // ... other mode-specific state
}
```

### Actions
```typescript
const useGameStore = create((set) => ({
  placeLabelAtZone: (labelId, zoneId) => set(state => ({
    placedLabels: [...state.placedLabels, { labelId, zoneId, isCorrect: true }],
    availableLabels: state.availableLabels.filter(l => l.id !== labelId),
  })),
  recordSequenceOrder: (order: string[]) => set(state => ({
    // transition to next mode if sequenceConfig defines it
    interactionMode: 'next_mode_if_defined',
  })),
  transitionMechanic: (fromMode, toMode) => set(state => ({
    interactionMode: toMode,
  })),
  // ... other actions
}));
```

---

## PART 5: How to Construct Your Heart Game

### Step 1: Define the Heart Anatomy (Zones)

Create zones for these heart parts:
- **Right Atrium** - Receives deoxygenated blood from body
- **Right Ventricle** - Pumps deoxygenated blood to lungs
- **Pulmonary Artery** - Carries blood to lungs
- **Left Atrium** - Receives oxygenated blood from lungs
- **Left Ventricle** - Pumps oxygenated blood to body
- **Pulmonary Vein** - Returns blood from lungs
- **Aorta** - Main artery to body
- **Superior/Inferior Vena Cava** - Returns blood from body

Each zone should be:
- A circle (shape: 'circle') or polygon on the diagram
- Positioned by analyzing the heart image (x%, y%)
- Named clearly (e.g., "right_atrium")

Example:
```json
"zones": [
  {
    "id": "right_atrium",
    "label": "Right Atrium",
    "x": 25,
    "y": 30,
    "radius": 25,
    "shape": "circle",
    "zone_type": "area",
    "description": "Receives deoxygenated blood from the body",
    "hint": "Upper right chamber of the heart",
    "difficulty": 2
  },
  {
    "id": "right_ventricle",
    "label": "Right Ventricle",
    "x": 25,
    "y": 65,
    "radius": 30,
    "shape": "circle",
    "zone_type": "area",
    "description": "Pumps deoxygenated blood to the lungs",
    "difficulty": 2
  },
  // ... repeat for all 8 chambers/vessels
]
```

### Step 2: Create Labels (Draggable Items)

```json
"labels": [
  {
    "id": "label_right_atrium",
    "text": "Right Atrium",
    "correctZoneId": "right_atrium"
  },
  {
    "id": "label_right_ventricle",
    "text": "Right Ventricle",
    "correctZoneId": "right_ventricle"
  },
  // ... repeat for all chambers/vessels
]
```

Add 2-3 distractor labels:
```json
"distractorLabels": [
  {
    "id": "distractor_brain",
    "text": "Brain",
    "explanation": "The brain is not part of the heart, though it receives blood from the heart."
  },
  {
    "id": "distractor_lung",
    "text": "Lung Tissue",
    "explanation": "The lungs are connected to the heart via the pulmonary artery and vein, but are not part of the heart itself."
  }
]
```

### Step 3: Define the Mechanics (Start with Drag-Drop)

```json
"mechanics": [
  {
    "type": "drag_drop",
    "config": {
      // optional mode-specific settings
    },
    "scoring": {
      "strategy": "per_zone",
      "points_per_correct": 10,
      "max_score": 80,  // 8 zones * 10 points
      "partial_credit": false
    },
    "feedback": {
      "on_correct": "Correct! {{label}} goes in the {{zone}}.",
      "on_incorrect": "Not quite. {{label}} belongs in a different location.",
      "on_completion": "Great job! You've labeled all the parts of the heart!"
    }
  }
]
```

### Step 4: Configure Drag-Drop Behavior

```json
"dragDropConfig": {
  "interaction_mode": "drag_drop",
  "zone_idle_animation": "glow",
  "zone_hover_effect": "scale",
  "leader_line_style": "curved",
  "leader_line_color": "#ef4444",
  "leader_line_animate": true,
  "placement_animation": "spring",
  "incorrect_animation": "shake",
  "tray_position": "bottom",
  "tray_layout": "horizontal",
  "show_distractors": true,
  "distractor_count": 2,
  "max_attempts": 3,
  "shuffle_labels": true,
  "zoom_enabled": true,
  "minimap_enabled": false
}
```

### Step 5: Define Blood Flow Sequencing (Second Mechanic)

```json
"mechanics": [
  { "type": "drag_drop", ... },
  {
    "type": "sequencing",
    "config": {},
    "scoring": {
      "strategy": "sequence",
      "max_score": 20,
      "partial_credit": true
    },
    "feedback": {
      "on_correct": "Perfect blood flow order!",
      "on_incorrect": "The blood doesn't flow in that order. Try again.",
      "on_completion": "You've mastered the circulatory path!"
    }
  }
],

"modeTransitions": [
  {
    "from": "drag_drop",
    "to": "sequencing",
    "trigger": "all_zones_labeled",
    "animation": "fade",
    "message": "Great! Now let's trace the blood flow through the heart..."
  }
],

"sequenceConfig": {
  "sequenceType": "cyclic",
  "items": [
    { "id": "seq_body", "text": "Body", "order_index": 0 },
    { "id": "seq_vena_cava", "text": "Superior/Inferior Vena Cava", "order_index": 1 },
    { "id": "seq_right_atrium", "text": "Right Atrium", "order_index": 2 },
    { "id": "seq_right_ventricle", "text": "Right Ventricle", "order_index": 3 },
    { "id": "seq_pulmonary_artery", "text": "Pulmonary Artery", "order_index": 4 },
    { "id": "seq_lungs", "text": "Lungs", "order_index": 5 },
    { "id": "seq_pulmonary_vein", "text": "Pulmonary Vein", "order_index": 6 },
    { "id": "seq_left_atrium", "text": "Left Atrium", "order_index": 7 },
    { "id": "seq_left_ventricle", "text": "Left Ventricle", "order_index": 8 },
    { "id": "seq_aorta", "text": "Aorta", "order_index": 9 }
  ],
  "correctOrder": [
    "seq_body", "seq_vena_cava", "seq_right_atrium", "seq_right_ventricle",
    "seq_pulmonary_artery", "seq_lungs", "seq_pulmonary_vein", "seq_left_atrium",
    "seq_left_ventricle", "seq_aorta"
  ],
  "instructionText": "Order the path of blood flow through the heart and body.",
  "layout_mode": "horizontal_timeline",
  "interaction_pattern": "drag_reorder",
  "card_type": "text_only",
  "connector_style": "arrow",
  "show_position_numbers": true,
  "allowPartialCredit": true
}
```

### Step 6: Complete Blueprint Object

```json
{
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Label the Parts of the Heart and Order the Flow",
  "narrativeIntro": "The human heart is a powerful muscular organ that pumps oxygen-rich blood throughout your body. Let's explore its structure and trace the path of blood as it flows through each chamber and vessel.",
  "diagram": {
    "assetPrompt": "A detailed, anatomically accurate cross-section of the human heart showing all four chambers, major blood vessels (aorta, pulmonary artery, vena cava, pulmonary vein), and color-coded blood flow (red for oxygenated, blue for deoxygenated). Style: medical illustration with clear zone boundaries.",
    "assetUrl": "https://example.com/heart-diagram.svg",  // or path to local asset
    "width": 800,
    "height": 600,
    "zones": [ /* 8 zones as defined in Step 1 */ ]
  },
  "labels": [ /* 8 labels as defined in Step 2 */ ],
  "distractorLabels": [ /* 2-3 distractors as defined in Step 2 */ ],
  "tasks": [
    {
      "id": "task_label_parts",
      "type": "label_diagram",
      "questionText": "Drag each label to the correct part of the heart.",
      "requiredToProceed": true
    },
    {
      "id": "task_sequence_flow",
      "type": "trace_path",
      "questionText": "Order the blood flow through the heart and lungs.",
      "requiredToProceed": false
    }
  ],
  "animationCues": {
    "correctPlacement": "Great! That's {{label}}!",
    "incorrectPlacement": "Try again. {{label}} goes in a different chamber.",
    "allLabeled": "Perfect! You've labeled the heart correctly!"
  },
  "animations": {
    "correctPlacement": {
      "type": "pulse",
      "duration_ms": 600,
      "easing": "ease-out",
      "color": "#10b981"
    },
    "incorrectPlacement": {
      "type": "shake",
      "duration_ms": 400,
      "easing": "ease-in-out",
      "intensity": 2
    }
  },
  "mechanics": [ /* As defined in Step 3 */ ],
  "modeTransitions": [ /* As defined in Step 5 */ ],
  "dragDropConfig": { /* As defined in Step 4 */ },
  "sequenceConfig": { /* As defined in Step 5 */ },
  "scoringStrategy": {
    "type": "combined",
    "base_points_per_zone": 10,
    "time_bonus_enabled": false,
    "partial_credit": true,
    "max_score": 100  // 80 for labels + 20 for sequence
  },
  "hints": [
    { "zoneId": "right_atrium", "hintText": "The chamber that receives blood from the body." },
    { "zoneId": "left_ventricle", "hintText": "The strongest chamber; it pumps blood to the entire body." }
    // ... more hints
  ],
  "feedbackMessages": {
    "perfect": "Excellent work! You've mastered the heart's anatomy and blood flow!",
    "good": "Good job! You've correctly labeled most of the heart.",
    "retry": "Not quite. Review the hint and try again."
  }
}
```

---

## PART 6: Advanced Features (Optional, But Recommended for High Quality)

### 6.1 Hierarchical Zone Grouping
Group left/right sides or atrium/ventricle pairs:

```json
"zoneGroups": [
  {
    "id": "right_side",
    "parentZoneId": null,
    "childZoneIds": ["right_atrium", "right_ventricle"],
    "revealTrigger": "complete_parent",
    "label": "Right Side (Deoxygenated Blood)"
  },
  {
    "id": "left_side",
    "parentZoneId": null,
    "childZoneIds": ["left_atrium", "left_ventricle"],
    "revealTrigger": "complete_parent",
    "label": "Left Side (Oxygenated Blood)"
  }
]
```

Then update zones:
```json
{
  "id": "right_atrium",
  "parentZoneId": "right_side",
  "hierarchyLevel": 2,
  ...
}
```

### 6.2 Temporal Constraints (Advanced Zone Reveal)
Reveal vessels only after chambers are labeled:

```json
"temporalConstraints": [
  {
    "zone_a": "right_atrium",
    "zone_b": "pulmonary_artery",
    "constraint_type": "before",
    "reason": "Chamber must be understood before introducing the vessel that leaves it.",
    "priority": 80
  }
]
```

### 6.3 Enhanced Drag-Drop Animations
Configure spring physics, particle effects, and easing:

```json
"dragDropConfig": {
  "spring_stiffness": 150,
  "spring_damping": 20,
  "show_placement_particles": true,
  "leader_line_width": 3,
  "pin_marker_shape": "arrow"
}
```

### 6.4 Multi-Scene Support (If Extended)
For a more complex game with multiple diagnosis scenarios, wrap in:

```typescript
interface MultiSceneInteractiveDiagramBlueprint {
  is_multi_scene: true;
  scenes: GameScene[];
}

interface GameScene {
  scene_id: string;
  scene_number: number;
  title: string;
  // ... inherits all InteractiveDiagramBlueprint properties
}
```

---

## PART 7: Validation & Testing Checklist

Before submitting your game blueprint:

- [ ] **Schema Compliance**: Every field matches one of the TypeScript interfaces exactly (no typos, no extra properties).
- [ ] **Zone Geometry**: All zones have realistic x, y, radius/width/height values (0-100% for percentage, actual pixels for absolute).
- [ ] **Labels Match Zones**: Each `Label.correctZoneId` references an existing `Zone.id`.
- [ ] **Consistent IDs**: All `id` fields are unique and use snake_case (e.g., "left_atrium", not "LeftAtrium").
- [ ] **Distractor Clarity**: Distractors are plausible but clearly wrong (not random nonsense).
- [ ] **Sequence Correctness**: The `correctOrder` in `sequenceConfig` accurately reflects blood flow (consult medical references).
- [ ] **Scoring Logic**: Max score = sum of all point distributions; high partial_credit for learning.
- [ ] **Animation Specs**: All animation durations are in milliseconds (e.g., 600 for 0.6s), easing is valid.
- [ ] **Images**: If using assetUrl, ensure URL is publicly accessible; if using assetPrompt, it should be detailed enough for AI generation.
- [ ] **Feedback Personalization**: Feedback messages use `{{label}}` and `{{zone}}` template variables where applicable.
- [ ] **Accessibility**: Every zone has a hint or description; difficult zones have lower difficulty ratings (1-2).
- [ ] **Mechanics Logical Flow**: Transitions make sense (e.g., drag_drop → sequencing, not sequencing → drag_drop).

---

## PART 8: Implementation Constraints & Limitations

### MUST DO:
1. **Use ONLY the provided components** — Do not create new React components outside `/components/templates/InteractiveDiagramGame/`.
2. **Conform to the schema strictly** — No ad-hoc fields; use the exact interface structure.
3. **Leverage zustand for state** — Do not use useState for game-critical state.
4. **Use Tailwind CSS exclusively** — No custom CSS modules, no styled-components, no CSS-in-JS.
5. **Respect component props** — Do not reverse-engineer component internals; use the documented props API.

### MUST NOT:
1. **Introduce external libraries** — No Konva, Fabric.js, Three.js, Pixi.js, EaselJS, paper.js, etc.
2. **Hard-code game logic** — All game mechanics are defined in the schema; no god components.
3. **Use external SVG generators** — Use native React SVG or the assetUrl/assetPrompt fields in the schema.
4. **Modify the types.ts file** — Do not alter existing TypeScript interfaces; extend via new properties if needed.
5. **Create custom animations** — Use framer-motion and the built-in animation specs; no requestAnimationFrame loops.
6. **Hard-code dimensions** — All dimensions should come from the blueprint or be responsive via Tailwind.

### Limitations to Expect:
1. **No 3D rendering** — The engine is 2D only (SVG + Canvas overlay).
2. **No physics simulation** — The drag-drop is kinetic + spring-based, not full-body physics.
3. **No WebGL** — Use SVG and HTML5 Canvas for visuals, not WebGL.
4. **No video playback** — Assets can be images (PNG, SVG, GIF) but not video (yet).
5. **No multiplayer** — All games are single-player, no socket.io or WebSocket orchestration.

---

## PART 9: Example Output JSON (Simplified)

```json
{
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Label the Parts of the Heart and Order the Flow",
  "narrativeIntro": "Discover the chambers and vessels of the heart...",
  "diagram": {
    "assetPrompt": "Detailed medical illustration of the human heart cross-section...",
    "width": 800,
    "height": 600,
    "zones": [
      {
        "id": "right_atrium",
        "label": "Right Atrium",
        "x": 25,
        "y": 30,
        "radius": 25,
        "shape": "circle",
        "description": "Receives deoxygenated blood from the body"
      },
      // ... 7 more zones
    ]
  },
  "labels": [
    { "id": "label_right_atrium", "text": "Right Atrium", "correctZoneId": "right_atrium" },
    // ... 7 more labels
  ],
  "tasks": [
    {
      "id": "task_1",
      "type": "label_diagram",
      "questionText": "Label the heart parts.",
      "requiredToProceed": true
    }
  ],
  "mechanics": [
    {
      "type": "drag_drop",
      "scoring": { "strategy": "per_zone", "points_per_correct": 10, "max_score": 80 },
      "feedback": { "on_correct": "Correct!", "on_incorrect": "Try again.", "on_completion": "Done!" }
    },
    {
      "type": "sequencing",
      "scoring": { "strategy": "sequence", "max_score": 20 },
      "feedback": { "on_correct": "Perfect order!", "on_incorrect": "Wrong order.", "on_completion": "Great!" }
    }
  ],
  "modeTransitions": [
    {
      "from": "drag_drop",
      "to": "sequencing",
      "trigger": "all_zones_labeled",
      "message": "Now order the blood flow..."
    }
  ],
  "dragDropConfig": {
    "zone_idle_animation": "glow",
    "leader_line_style": "curved",
    "tray_position": "bottom",
    "shuffle_labels": true
  },
  "sequenceConfig": {
    "sequenceType": "cyclic",
    "items": [
      { "id": "seq_1", "text": "Right Atrium", "order_index": 0 },
      // ... 9 more items
    ],
    "correctOrder": ["seq_1", "seq_2", ...],
    "layout_mode": "horizontal_timeline",
    "interaction_pattern": "drag_reorder"
  },
  "feedbackMessages": {
    "perfect": "Excellent work!",
    "good": "Good job!",
    "retry": "Try again."
  }
}
```

---

## Summary

You now have:
1. **Complete TypeScript schema** — The exact contract for the game.
2. **Available components** — Pre-built, production-ready React components to use.
3. **State management pattern** — Zustand-based state with specific actions.
4. **Example heart game** — Detailed step-by-step instructions for this specific game.
5. **Validation checklist** — How to verify your output is correct.
6. **Constraints & limitations** —What you CAN and CANNOT do.

**Your task**: Generate a production-ready `InteractiveDiagramBlueprint` object (as valid JSON or TypeScript) that, when passed to the `<InteractiveDiagramGame>` component, renders a fully functional "Label the Parts of the Heart and Order the Flow" game using ONLY the existing engine infrastructure.

**Success Metric**: The blueprint should be so detailed and technically complete that a single `<InteractiveDiagramGame blueprint={yourBlueprint} />` component renders a perfect game with no additional code.
